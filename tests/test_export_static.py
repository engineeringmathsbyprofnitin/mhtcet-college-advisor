"""Stage 5B tests for database/export_static.py (SYNTHETIC data only).
Run from the repository root:  python -m unittest tests/test_export_static.py -v"""
import csv, hashlib, json, os, shutil, sys, tempfile, unittest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "database"))
import export_static as E
SYN = os.path.join(ROOT, "data", "synthetic")
NOW = "2026-10-25T09:00:00Z"

def tmp(): return tempfile.mkdtemp()
def copy_syn():
    d = tmp(); shutil.rmtree(d); shutil.copytree(SYN, d); return d
def edit(d, table, fn):
    p = os.path.join(d, table + ".csv")
    with open(p, newline="") as fh: rows = list(csv.DictReader(fh))
    hdr = list(rows[0].keys())
    fn(rows)
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=hdr); w.writeheader(); w.writerows(rows)
def snapshot(d):
    out = {}
    for root, _, names in os.walk(d):
        for n in names:
            p = os.path.join(root, n); out[os.path.relpath(p, d)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out
def load(out, rel): return json.load(open(os.path.join(out, rel), encoding="utf-8"))

class T(unittest.TestCase):
    def test_publish_synthetic(self):
        out = tmp(); m = E.publish(SYN, out, NOW)
        self.assertEqual(m["data_version"], "SYN-v1"); self.assertEqual(m["current_admission_year"], "2026-27"); self.assertTrue(m["is_synthetic"])
        self.assertEqual(sorted(m["cutoffs"]), ["GOBCS", "GOPENS", "GSCS", "LOPENS"])
        self.assertTrue(os.path.exists(os.path.join(out, "manifest.json")))
    def test_files_match_manifest_and_names_carry_hash(self):
        out = tmp(); m = E.publish(SYN, out, NOW)
        for f in [m["base"]] + list(m["cutoffs"].values()):
            b = open(os.path.join(out, f["file"]), "rb").read()
            self.assertEqual(hashlib.sha256(b).hexdigest(), f["sha256"]); self.assertEqual(len(b), f["bytes"]); self.assertIn(f["sha256"][:10], f["file"])
    def test_deterministic(self):
        a, b = tmp(), tmp(); E.publish(SYN, a, NOW); E.publish(SYN, b, NOW); self.assertEqual(snapshot(a), snapshot(b))
    def test_cutoff_rows_all_accounted_for(self):
        out = tmp(); m = E.publish(SYN, out, NOW)
        for t in ("historical_cutoffs", "current_cutoffs"):
            with open(os.path.join(SYN, t + ".csv")) as fh: n = len(list(csv.DictReader(fh)))
            self.assertEqual(m["row_counts"][t], n)
            self.assertEqual(sum(f["rows"][t] for f in m["cutoffs"].values()), n)
    def test_each_cutoff_file_only_holds_its_seat_type(self):
        out = tmp(); m = E.publish(SYN, out, NOW)
        for code, f in m["cutoffs"].items():
            d = load(out, f["file"]); i = d["historical_cutoffs"]["columns"].index("seat_type_code")
            self.assertTrue(all(r[i] == code for r in d["historical_cutoffs"]["rows"]))
    def test_internal_columns_not_published(self):
        out = tmp(); m = E.publish(SYN, out, NOW); d = load(out, m["cutoffs"]["GOPENS"]["file"]); b = load(out, m["base"]["file"])
        self.assertNotIn("validation_status", d["historical_cutoffs"]["columns"]); self.assertNotIn("is_synthetic", d["historical_cutoffs"]["columns"])
        self.assertNotIn("validation_status", b["colleges"]["columns"]); self.assertIn("college_website", b["colleges"]["columns"])
        self.assertNotIn("seat_intake", b)            # intake is deliberately not published (never to be mistaken for vacancy)
    def test_unvalidated_rows_not_published(self):
        d = copy_syn()
        def f(rows): rows[0]["validation_status"] = "pending"; rows[1]["validation_status"] = "rejected"
        edit(d, "current_cutoffs", f)
        out = tmp(); m = E.publish(d, out, NOW); self.assertEqual(m["row_counts"]["current_cutoffs"], 948 - 2)
    def test_invalid_data_blocks_publishing_and_old_version_survives(self):
        out = tmp(); E.publish(SYN, out, NOW); before = snapshot(out)
        bad = copy_syn(); edit(bad, "historical_cutoffs", lambda r: r[0].update(cutoff_percentile="150"))
        with self.assertRaises(E.PublishError): E.publish(bad, out, "2026-10-26T09:00:00Z")
        self.assertEqual(snapshot(out), before)       # nothing changed: last-known-good stays live
    def test_vacancy_from_seat_matrix_blocks_publishing(self):
        bad = copy_syn(); edit(bad, "vacancies", lambda r: r[0].update(source_doc_id="SYN-DOC-009"))
        with self.assertRaises(E.PublishError): E.publish(bad, tmp(), NOW)
    def test_two_last_known_good_blocks_publishing(self):
        bad = copy_syn(); edit(bad, "data_version", lambda r: r.append(dict(r[0], data_version="SYN-v2")))
        with self.assertRaises(E.PublishError): E.publish(bad, tmp(), NOW)
    def test_unsafe_seat_type_code_rejected(self):
        bad = copy_syn()
        edit(bad, "seat_types", lambda r: r.append(dict(r[0], seat_type_code="../x")))
        edit(bad, "historical_cutoffs", lambda r: r[0].update(seat_type_code="../x"))
        with self.assertRaises(E.PublishError): E.publish(bad, tmp(), NOW)
    def test_new_version_replaces_old_files_and_manifest_points_to_new(self):
        out = tmp(); m1 = E.publish(SYN, out, NOW)
        d = copy_syn(); edit(d, "historical_cutoffs", lambda r: r[0].update(cutoff_percentile="55.5000000"))
        edit(d, "data_version", lambda r: r[0].update(data_version="SYN-v2"))
        m2 = E.publish(d, out, "2026-10-26T09:00:00Z")
        self.assertEqual(load(out, "manifest.json")["data_version"], "SYN-v2")
        files = {os.path.relpath(os.path.join(r, n), out).replace(os.sep, "/") for r, _, ns in os.walk(out) for n in ns}
        expected = {"manifest.json", m2["base"]["file"]} | {c["file"] for c in m2["cutoffs"].values()}
        self.assertEqual(files, expected)             # old versions' files were cleaned up
    def test_unchanged_data_gives_unchanged_files(self):
        out = tmp(); m1 = E.publish(SYN, out, NOW); m2 = E.publish(SYN, out, "2026-10-27T09:00:00Z")
        self.assertEqual(m1["base"]["file"], m2["base"]["file"]); self.assertEqual({k: v["file"] for k, v in m1["cutoffs"].items()}, {k: v["file"] for k, v in m2["cutoffs"].items()})
    def test_compact_format_roundtrip(self):
        out = tmp(); m = E.publish(SYN, out, NOW); b = load(out, m["base"]["file"])
        cols, rows = b["colleges"]["columns"], b["colleges"]["rows"]; self.assertEqual(len(rows), 12); self.assertEqual(len(cols), len(rows[0]))
    def test_nothing_to_publish_is_refused(self):
        bad = copy_syn(); edit(bad, "colleges", lambda r: [x.update(validation_status="pending") for x in r])
        with self.assertRaises(E.PublishError): E.publish(bad, tmp(), NOW)
if __name__ == "__main__": unittest.main()
