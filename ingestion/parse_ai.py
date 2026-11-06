"""Reads a 'Cut Off List for All India Seats' PDF into one record per row (Stage 9b).

Unlike the State lists this is a plain table: Sr. No | All India merit number with a score in brackets | choice code |
institute | course (wraps over several lines) | merit exam | type | seat type. Column positions change from year to year, so the
boundaries are measured from each page's own headings, and anything that straddles a boundary is reported.
The bracketed score is a JEE (Main) score, a NEET score or an MHT-CET percentile depending on the row's merit exam; it is stored
as printed together with the exam, and the two are never mixed up.
"""
import argparse, collections, csv, gzip, io, json, os, re, sys
from .pdf_words import iter_pages, group_lines, line_text
from .codes import norm_institute_code, norm_choice_code, choice_matches_institute
from .archive import load_manifest, sha256_file

INT_RE = re.compile(r"^\d{1,3}(?:,\d{3})*$|^\d{1,7}$")                 # serial numbers from 1,000 upward are printed with a comma
SCORE_RE = re.compile(r"^\((\d{1,3}(?:\.\d{1,9})?)\)$")
CODE_TOKEN_RE = re.compile(r"^\d{9,10}[A-Z]{0,3}$")
INSTITUTE_RE = re.compile(r"^(\d{4,5})\s*-\s*(.+)$")
FOOTER_RE = re.compile(r"^(Cut Off Indicates|Legends|Page \d+ of \d+|\* )")
KNOWN_TYPES = {"AI to AI", "MH to AI", "MI to AI", "MH-AI"}


def _exam_kind(text):
    t = (text or "").upper()
    return "JEE" if t.startswith("JEE") else "MHT-CET" if t.startswith("MHT") else "NEET" if t.startswith("NEET") else ""


def _bounds(header_words):
    """Column boundaries from the page's own headings (see docs/STAGE9B.md)."""
    def x0(pred, default=None):
        c = [w.x0 for w in header_words if pred(w)]
        return min(c) if c else default
    allx = x0(lambda w: w.text == "All" and w.x0 < 300); choice = x0(lambda w: w.text == "Choice"); course = x0(lambda w: w.text == "Course")
    exam = x0(lambda w: w.x0 > 600 and (w.text in ("Merit", "Exam") or w.text.startswith("Exam") or w.text.startswith("MHT"))); typ = x0(lambda w: w.text == "Type" and w.x0 > 650); seat = x0(lambda w: w.text == "Seat")
    if None in (allx, choice, course, exam, typ, seat): return None
    return {"merit": allx - 25, "choice": choice - 8, "course": course - 20, "exam": exam - 6, "type": typ - 10, "seat": seat - 12}


def parse_pdf(path, first=None, last=None, meta=None):
    rec, prob = [], []
    stats = {"pages": 0, "rows": 0, "blank_rows": 0, "printed_choice_codes": 0}
    exams, types, seats = collections.Counter(), collections.Counter(), collections.Counter()
    expect = 1 if first in (None, 1) else None            # a run that starts on a later page cannot know the first serial number
    for page, W, H, words in iter_pages(path, first, last):
        stats["pages"] += 1
        lines = group_lines(words)
        hi = next((i for i, l in enumerate(lines) if line_text(l).startswith("Sr.")), None)
        if hi is None: prob.append({"page": page, "problem": "table heading not found on this page"}); continue
        fi = next((i for i, l in enumerate(lines) if i > hi and FOOTER_RE.match(line_text(l))), len(lines))
        foot_y = lines[fi][0].y0 - 2 if fi < len(lines) else H
        probe = [w for w in words if w.y0 > lines[hi][0].y0 - 3]
        hdr_end = None
        # data starts at the first number printed far left of the 'All India' heading
        allx = min([w.x0 for w in probe if w.text == "All" and w.x0 < 300 and w.y0 < lines[hi][0].y0 + 20] or [None])
        if allx is None: prob.append({"page": page, "problem": "heading 'All India' not found"}); continue
        rows0 = sorted([w for w in probe if w.x0 < allx - 25 and INT_RE.match(w.text) and w.y0 > lines[hi][0].y0 + 22 and w.y0 < foot_y], key=lambda w: w.y0)
        if not rows0: continue
        header_words = [w for w in probe if w.y0 < rows0[0].y0 - 4]
        b = _bounds(header_words)
        if b is None: prob.append({"page": page, "problem": "column headings not recognised"}); continue
        edges = [r.y0 - 6 for r in rows0] + [foot_y]
        for i, sr in enumerate(rows0):
            band = [w for w in words if edges[i] <= w.y0 < edges[i + 1] and w is not sr]
            zones = collections.defaultdict(list)
            for w in band:
                for z, key in (("seat", "seat"), ("type", "type"), ("exam", "exam"), ("course", "course"), ("inst", "choice"), ("merit", "merit")):
                    if w.x0 >= b[key]: zones[z].append(w); break
                else: zones["other"].append(w)
                if any(w.x0 < v < w.x1 - 2 for v in b.values()): prob.append({"page": page, "problem": "row %s: '%s' straddles a column boundary" % (sr.text, w.text)})
            ztext = lambda z: " ".join(line_text(l) for l in group_lines(zones[z]))
            stats["rows"] += 1; n = int(sr.text.replace(",", ""))
            if expect is not None and n != expect: prob.append({"page": page, "problem": "serial number %d where %d was expected" % (n, expect)})
            expect = n + 1
            merit = [w.text for w in zones["merit"]]; ints = [t for t in merit if INT_RE.match(t)]; scores = [SCORE_RE.match(t).group(1) for t in merit if SCORE_RE.match(t)]
            codes = [w for w in zones["inst"] if w.x0 < b["choice"] + 40 and CODE_TOKEN_RE.match(w.text)]           # the code sits a little lower than the name, so read it by shape
            m = INSTITUTE_RE.match(" ".join(line_text(l) for l in group_lines([w for w in zones["inst"] if w not in codes])))
            if not merit and m and len(codes) <= 1:                              # genuine blank in the official file: the row exists but no cutoff was printed (no allotment)
                choice = norm_choice_code(codes[0].text) if codes else ""
                if choice and not choice_matches_institute(choice, norm_institute_code(m.group(1))): prob.append({"page": page, "problem": "row %d: course code %s does not start with institute code %s" % (n, codes[0].text, m.group(1))})
                exam, typ, seat, course = ztext("exam"), ztext("type"), ztext("seat"), ztext("course"); stats["blank_rows"] += 1; stats["printed_choice_codes"] += 1
                exams[exam] += 1; types[typ] += 1; seats[seat] += 1
                rec.append({"list_type": "AI", "sr_no": n, "merit_no": "", "score": "", "choice_code": choice, "institute_code": norm_institute_code(m.group(1)), "institute_name": m.group(2).strip(), "course_name": course,
                            "merit_exam": exam, "merit_exam_kind": _exam_kind(exam), "ai_type": typ, "seat_type": seat, "page": page, "note": "no cutoff printed in the source"}); continue
            if len(codes) != 1: m = None
            if zones["other"]: prob.append({"page": page, "problem": "row %d: text left of the table: %s" % (n, ztext("other")[:40])})
            if len(ints) != 1 or len(scores) != 1: prob.append({"page": page, "problem": "row %d: merit cell not 'number (score)': %s" % (n, " ".join(merit))}); continue
            if not m: prob.append({"page": page, "problem": "row %d: choice code and institute not readable: %s" % (n, ztext("inst")[:60])}); continue
            code_text = codes[0].text
            stats["printed_choice_codes"] += 1
            choice, inst = norm_choice_code(code_text), norm_institute_code(m.group(1))
            if not choice_matches_institute(choice, inst): prob.append({"page": page, "problem": "row %d: course code %s does not start with institute code %s" % (n, code_text, m.group(1))})
            exam, typ, seat, course = ztext("exam"), ztext("type"), ztext("seat"), ztext("course")
            for name, val in (("course", course), ("merit exam", exam), ("type", typ), ("seat type", seat)):
                if not val: prob.append({"page": page, "problem": "row %d: %s is empty" % (n, name)})
            if typ and typ not in KNOWN_TYPES: prob.append({"page": page, "problem": "row %d: unknown type '%s'" % (n, typ)})
            exams[exam] += 1; types[typ] += 1; seats[seat if len(seat) > 2 else seat] += 1
            rec.append({"list_type": "AI", "sr_no": n, "merit_no": int(ints[0].replace(",", "")), "score": scores[0], "choice_code": choice, "institute_code": inst, "institute_name": m.group(2).strip(),
                        "course_name": course, "merit_exam": exam, "merit_exam_kind": _exam_kind(exam), "ai_type": typ, "seat_type": seat, "page": page, "note": ""})
    if meta and rec: pass
    return {"records": rec, "problems": prob, "stats": stats, "merit_exams": dict(exams), "types": dict(types), "seat_types": dict(seats)}


COLUMNS = ["year_label", "cap_round", "list_type", "sr_no", "merit_no", "score", "choice_code", "institute_code", "institute_name", "course_name", "merit_exam", "merit_exam_kind", "ai_type", "seat_type", "page", "note", "source_sha256"]


def write_csv_gz(path, records, meta):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    buf = io.StringIO(); w = csv.writer(buf, lineterminator="\n"); w.writerow(COLUMNS)
    for r in records: w.writerow([meta["year_label"], meta["cap_round"]] + [r[c] for c in COLUMNS[2:-1]] + [meta["sha256"]])
    with open(path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz: gz.write(buf.getvalue().encode("utf-8"))


def _norm(s): return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def load_mh_names(mh_dir, year_label):
    """choice_code -> (institute name, course name) from the State list(s) of the same year, for cross-checking."""
    names = {}
    if not mh_dir or not os.path.isdir(mh_dir): return names
    for f in sorted(os.listdir(mh_dir)):
        if f.startswith(year_label + "_") and f.endswith("_MH.csv.gz"):
            with gzip.open(os.path.join(mh_dir, f), "rt", encoding="utf-8") as fh:
                for r in csv.DictReader(fh): names.setdefault(r["choice_code"], (r["institute_name"], r["course_name"]))
    return names


def cross_check(records, names):
    """Compares every row's institute and course name with the State list's name for the same course code."""
    if not names: return None
    missing, inst_bad, course_bad, trunc, ex = 0, 0, 0, 0, []
    for r in records:
        if not r["choice_code"]: continue
        n = names.get(r["choice_code"])
        if not n: missing += 1; continue
        if _norm(n[0]) != _norm(r["institute_name"]): inst_bad += 1; ex.append(("institute", r["choice_code"], n[0][:40], r["institute_name"][:40]))
        a, b = _norm(n[1]), _norm(r["course_name"])
        if a != b:
            if a.startswith(b): trunc += 1                         # the All India table cuts long course names short: harmless
            else: course_bad += 1; ex.append(("course", r["choice_code"], n[1][:40], r["course_name"][:40]))
    return {"checked": len(records), "not_in_state_list": missing, "institute_name_differs": inst_bad, "course_name_truncated_in_ai_list": trunc, "course_name_differs": course_bad, "examples": ex[:10]}


def run_cli(manifest_path, files_dir, out_dir, mh_dir=None, now=None):
    man = load_manifest(manifest_path); report = {"generated_at": now, "files": [], "all_ok": True}
    docs = [d for d in man["documents"].values() if d.get("doc_type") == "cutoff" and d.get("scope") == "AI"]
    for d in sorted(docs, key=lambda d: (d["year_label"], d["cap_round"])):
        f = man["files"].get(d.get("current_sha256")); e = {"year_label": d["year_label"], "cap_round": d["cap_round"], "asset": f and f["asset_name"], "source_sha256": f and f["sha256"]}; report["files"].append(e)
        if not f: e["error"] = "not archived"; report["all_ok"] = False; continue
        path = os.path.join(files_dir, f["asset_name"])
        if not os.path.exists(path): e["error"] = "file not present in %s" % files_dir; report["all_ok"] = False; continue
        if sha256_file(path) != f["sha256"]: e["error"] = "fingerprint mismatch: the file is not the archived one, refusing to read it"; report["all_ok"] = False; continue
        r = parse_pdf(path); s = r["stats"]; out = os.path.join(out_dir, "%s_round-%s_AI.csv.gz" % (d["year_label"], d["cap_round"]))
        write_csv_gz(out, r["records"], {"year_label": d["year_label"], "cap_round": d["cap_round"], "sha256": f["sha256"]})
        cc = cross_check(r["records"], load_mh_names(mh_dir, d["year_label"]))
        e.update({"output": os.path.basename(out), "rows": s["rows"], "printed_choice_codes": s["printed_choice_codes"], "complete": s["rows"] == s["printed_choice_codes"] == len(r["records"]), "pages": s["pages"],
                  "problem_count": len(r["problems"]), "problems": r["problems"][:20], "blank_rows": s["blank_rows"], "merit_exams": r["merit_exams"], "types": r["types"], "seat_types": r["seat_types"], "cross_check_with_state_list": cc})
        if r["problems"] or not e["complete"]: report["all_ok"] = False
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "parse_report_ai.json"), "w", encoding="utf-8") as fh: fh.write(json.dumps(report, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read the archived All India cutoff PDFs into normalized CSV files (Stage 9b).")
    ap.add_argument("--manifest", default="data/raw/manifest.json"); ap.add_argument("--files", default="data/raw/files"); ap.add_argument("--out", default="data/normalized/cutoffs_ai")
    ap.add_argument("--mh-dir", default="data/normalized/cutoffs_mh"); ap.add_argument("--now")
    a = ap.parse_args(argv); rep = run_cli(a.manifest, a.files, a.out, a.mh_dir, a.now)
    for e in rep["files"]:
        print("%s round %s: %s" % (e["year_label"], e["cap_round"], e.get("error") or "%d rows, %s, %d problem(s)" % (e["rows"], "COMPLETE" if e["complete"] else "INCOMPLETE", e["problem_count"])))
    return 0 if rep["all_ok"] else 4


if __name__ == "__main__":
    sys.exit(main())
