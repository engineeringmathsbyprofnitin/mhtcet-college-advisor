import copy, csv, gzip, json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ingestion import read_vacancy as R, parse_vacancy as P

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "vacancy_cap4_pages1-2.txt")


def doc(i, rnd, year="2026-27", typ="vacancy_position", uploaded=True, sha=None):
    sha = sha or ("%064x" % i)
    d = dict(id=str(i), doc_type=typ, cap_round=rnd, portal_year=year, file_name="v%d.pdf" % i, current_sha256=sha)
    f = dict(sha256=sha, release_tag="raw-" + year, asset_name="%s__v%d.pdf" % (sha[:16], i), uploaded=uploaded)
    return d, f


def manifest(*items):
    m = dict(documents={}, files={})
    for d, f in items:
        m["documents"][d["id"]] = d; m["files"][f["sha256"]] = f
    return m


class Select(unittest.TestCase):
    def test_round4_preferred_over_3(self):
        m = manifest(doc(1, "III"), doc(2, "IV"))
        ch, notes, bl = R.select(m)
        self.assertEqual(ch["2026-27"]["cap_round"], "IV"); self.assertEqual(bl, [])
        self.assertTrue(any("Round III file not used" in n for n in notes))

    def test_round3_when_no_round4(self):
        ch, _, _ = R.select(manifest(doc(1, "III")))
        self.assertEqual(ch["2026-27"]["cap_round"], "III")

    def test_rounds_1_2_never_used(self):
        ch, notes, _ = R.select(manifest(doc(1, "I"), doc(2, "II")))
        self.assertEqual(ch, {}); self.assertEqual(len([n for n in notes if "never used" in n]), 2)

    def test_acap_list_never_used(self):
        ch, notes, _ = R.select(manifest(doc(1, "IV", typ="vacancy_after_cap")))
        self.assertEqual(ch, {}); self.assertTrue(any("ACAP" in n for n in notes))

    def test_seat_matrix_and_cutoff_ignored(self):
        ch, _, _ = R.select(manifest(doc(1, None, typ="seat_matrix"), doc(2, "IV", typ="cutoff")))
        self.assertEqual(ch, {})

    def test_round4_not_archived_blocks_instead_of_falling_back(self):
        ch, _, bl = R.select(manifest(doc(1, "III"), doc(2, "IV", uploaded=False)))
        self.assertEqual(ch, {}); self.assertEqual(len(bl), 1); self.assertIn("not falling back", bl[0])

    def test_each_year_is_independent(self):
        ch, _, _ = R.select(manifest(doc(1, "IV", "2025-26"), doc(2, "III", "2026-27")))
        self.assertEqual((ch["2025-26"]["cap_round"], ch["2026-27"]["cap_round"]), ("IV", "III"))

    def test_needed_lists_only_selected(self):
        m = manifest(doc(1, "III"), doc(2, "IV"))
        self.assertEqual([t[1].split("__")[1] for t in R.needed(m)], ["v2.pdf"])


class ReadAll(unittest.TestCase):
    def setUp(self):
        self._orig = P.parse_pdf
        txt = open(FIX, encoding="utf-8").read().replace("of 1013", "of 2")
        txt = "\n".join(l for l in txt.split("\n") if "Vacant CAP Seats:2" not in l or "Government" not in l and "Un-Aided" not in l and "Autonomous" not in l)
        P.parse_pdf = lambda path: P.parse_text(txt)
        self.tmp = tempfile.mkdtemp()

    def tearDown(self): P.parse_pdf = self._orig

    def test_writes_table_and_report(self):
        m = manifest(doc(2, "IV"))
        d = os.path.join(self.tmp, "f"); os.makedirs(d)
        open(os.path.join(d, m["files"][m["documents"]["2"]["current_sha256"]]["asset_name"]), "wb").write(b"x")
        rep = R.read_all(m, d, os.path.join(self.tmp, "o"))
        self.assertTrue(rep["ok"], rep["problems"])
        rows = list(csv.DictReader(gzip.open(os.path.join(self.tmp, "o", "2026-27_round-IV_vacancy.csv.gz"), "rt", encoding="utf-8")))
        self.assertEqual(rows[0]["choice_code"], "0100219110"); self.assertEqual(rows[0]["intake_si"], "60"); self.assertEqual(rows[0]["vacant_cap_seats"], "1")
        self.assertEqual(rows[0]["cap_round"], "IV")
        self.assertEqual(list(json.loads(rows[0]["grid_json"]).keys()), ["State Level"])

    def test_missing_download_fails(self):
        rep = R.read_all(manifest(doc(2, "IV")), os.path.join(self.tmp, "none"), os.path.join(self.tmp, "o2"))
        self.assertFalse(rep["ok"]); self.assertTrue(any("not downloaded" in p for p in rep["problems"]))

    def test_no_files_fails(self):
        rep = R.read_all(manifest(), self.tmp, os.path.join(self.tmp, "o3"))
        self.assertFalse(rep["ok"])

    def test_parser_problem_writes_no_table(self):
        P.parse_pdf = lambda path: dict(blocks=[], problems=["x"], unrecognised=[], pages=(1, 1), ghosts=0)
        m = manifest(doc(2, "IV")); d = os.path.join(self.tmp, "f"); os.makedirs(d)
        open(os.path.join(d, m["files"][m["documents"]["2"]["current_sha256"]]["asset_name"]), "wb").write(b"x")
        rep = R.read_all(m, d, os.path.join(self.tmp, "o4"))
        self.assertFalse(rep["ok"]); self.assertFalse(any(n.endswith(".csv.gz") for n in os.listdir(os.path.join(self.tmp, "o4"))))


class RealManifest(unittest.TestCase):
    def test_real_manifest_picks_round4_only(self):
        p = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "manifest.json")
        if not os.path.exists(p): self.skipTest("no manifest")
        m = json.load(open(p)); ch, _, bl = R.select(m)
        self.assertEqual(bl, []); self.assertTrue(all(d["cap_round"] in ("IV", "III") for d in ch.values()))
        self.assertTrue(all(d["doc_type"] == "vacancy_position" for d in ch.values()))


if __name__ == "__main__":
    unittest.main()
