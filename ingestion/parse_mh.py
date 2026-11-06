"""Reads a 'Cut Off List for Maharashtra & Minority Seats' PDF into one record per published cell (Stage 9).

Layout of the official file (seen in 2023-24 to 2026-27): for every institute and course, one or more SECTIONS
('State Level', 'Home University Seats Allotted to Home University Candidates', ...). Each section has a header row
('Stage GOPENS GVJS ...') and rows labelled by stage ('I', 'VII', 'I-Non PWD', ...). A row shows the merit numbers; the
line below shows each merit percentile in brackets. A value belongs to the column heading nearest to it on the page.

Nothing is guessed: a cell that cannot be read is reported as a problem, never dropped silently or turned into zero.
"""
import re
from .pdf_words import iter_pages, group_lines, line_text
from .codes import norm_institute_code, norm_choice_code, choice_matches_institute

INST_RE = re.compile(r"^(\d{4,5}) - (.+)$")
COURSE_RE = re.compile(r"^(\d{9,10}[A-Z]{0,3}) - (.+)$")
CODEISH_RE = re.compile(r"^\d{4,}[A-Za-z]* - ")                # anything that looks like a code heading must be recognised, never absorbed
STATUS_RE = re.compile(r"^Status:\s*(.*)$")
HOME_UNI_RE = re.compile(r"^(.*?)\s*Home University\s*:\s*(.*)$")
STAGE_LABEL_RE = re.compile(r"^(?:[IVX]+(?:-Non)?|PWD|Defence|Orphan)$")
CODE_RE = re.compile(r"^[A-Z][A-Z0-9]{1,11}$")
PCT_RE = re.compile(r"^\((\d{1,3}\.\d{1,9})\)$")
INT_RE = re.compile(r"^\d{1,8}$")
TITLE_YEAR_RE = re.compile(r"(?:A\.Y\.|Academic Year|the Year|Year)\s*(20\d\d)\s*-\s*(\d{2,4})")
TITLE_ROUND_RE = re.compile(r"CAP Round\s*-?\s*(IV|III|II|I)\b")
SKIP_RE = re.compile(r"^(Legends|\* |Page \d+ of \d+|\d+$)")
SECTION_RE = re.compile(r"^(?P<pool>.+?) Seats Allotted to (?P<to>.+?)(?: Candidates)?$")


def section_parts(title):
    t = re.sub(r"\s+", " ", title).strip()
    m = SECTION_RE.match(t)
    if m: return {"seat_pool": m.group("pool"), "allotted_to": m.group("to")}
    return {"seat_pool": t, "allotted_to": ""}


def _clean(line):
    return [w for w in line if not (w.x1 < 32 and len(w.text) == 1)]          # the vertical letters printed in the left margin


def _is_label(tok):
    return STAGE_LABEL_RE.match(tok) is not None


def parse_pdf(path, first=None, last=None, meta=None):
    """Returns {"records", "problems", "stats", "titles", "stage_labels", "file_header"}. meta (optional) = year_label / cap_round to cross-check."""
    rec, prob = [], []
    stats = {"printed_percentiles": 0, "pages": 0, "overflow_pages": 0, "institutes": set(), "courses": set(), "tables": 0, "rows": 0, "cells": 0}
    titles, labels = {}, {}
    st = {"inst_code": None, "inst_name": None, "course": None, "status": None, "uni": None, "title": [], "course_wrap": False, "table": None, "pending": None}
    header_info = {"year": None, "round": None}
    last_main = []                                           # tables of the last normal page (overflow pages refer back to them)

    def problem(page, msg): prob.append({"page": page, "problem": msg})

    def nearest(header, centre):
        best = min(header, key=lambda h: abs(h[1] - centre))
        pitch = min([abs(a[1] - b[1]) for a, b in zip(header, header[1:])] or [80.0])
        return best if abs(best[1] - centre) <= max(pitch * 0.5, 14.0) else None

    def emit(tbl, page, label, nums, pcts):
        stats["rows"] += 1
        cols = {}
        for kind, items in (("n", nums), ("p", pcts)):
            for w in items:
                h = nearest(tbl["header"], (w.x0 + w.x1) / 2)
                if h is None: problem(page, "value %s in row '%s' sits under no column heading" % (w.text, label)); continue
                if kind in cols.setdefault(h[0], {}): problem(page, "two %s values under %s in row '%s'" % ("number" if kind == "n" else "percentile", h[0], label))
                cols[h[0]][kind] = w.text
        for code, c in cols.items():
            if "n" not in c or "p" not in c:
                problem(page, "%s in row '%s' has %s but not the %s" % (code, label, "a number" if "n" in c else "a percentile", "percentile" if "n" in c else "number")); continue
            pct = PCT_RE.match(c["p"]).group(1)
            if not (0 <= float(pct) <= 100): problem(page, "percentile %s out of range" % pct); continue
            stats["cells"] += 1
            part = section_parts(" ".join(tbl["section_title"]))
            rec.append({"list_type": "MH", "institute_code": tbl["inst_code"], "institute_name": tbl["inst_name"], "choice_code": tbl["course"][0], "course_name": tbl["course"][1],
                        "status": tbl["status"], "home_university": tbl["uni"], "section": " ".join(tbl["section_title"]), "seat_pool": part["seat_pool"], "allotted_to": part["allotted_to"],
                        "stage": label, "seat_code": code, "merit_no": int(c["n"]), "percentile": pct, "page": page})

    def flush_pending(page):
        if st["pending"]:
            problem(st["pending"]["page"], "row '%s' has numbers but no percentile line" % st["pending"]["label"]); st["pending"] = None

    for page, W, H, words in iter_pages(path, first, last):
        stats["pages"] += 1; stats["printed_percentiles"] += sum(1 for w in words if PCT_RE.match(w.text))
        lines = [l for l in (_clean(x) for x in group_lines(words)) if l]
        if not lines: continue
        first_toks = [w.text for w in lines[0]]
        if all(CODE_RE.match(t) for t in first_toks) and not INST_RE.match(line_text(lines[0])):
            # ---- overflow page: the right-hand columns of the wide tables of the previous page, matched by height
            stats["overflow_pages"] += 1; tbl, pend = None, None
            for line in lines:
                toks = [w.text for w in line]; y = line[0].y0
                if all(CODE_RE.match(t) for t in toks):
                    cand = [t for t in last_main if abs(t["hdr_y"] - y) <= 6.0]
                    tbl = None
                    if not cand: problem(page, "overflow headings %s match no table of the previous page" % " ".join(toks)); continue
                    base = cand[0]
                    tbl = dict(base, header=[(w.text, (w.x0 + w.x1) / 2) for w in line])
                    if len({c for c, _ in tbl["header"]} & {c for c, _ in base["header"]}): problem(page, "overflow column(s) repeat columns already read on the previous page: %s" % " ".join(toks))
                elif tbl and all(INT_RE.match(t) for t in toks): pend = (y, line)
                elif tbl and all(PCT_RE.match(t) for t in toks) and pend:
                    row = [r for r in tbl["rows"] if abs(r[0] - pend[0]) <= 3.0]
                    if not row: problem(page, "overflow row at height %.0f matches no stage row of the previous page" % pend[0]); pend = None; continue
                    emit(tbl, page, row[0][1], pend[1], line); pend = None
                else: problem(page, "unrecognised line on overflow page: %s" % " ".join(toks)[:80])
            continue
        in_header, seen = True, 0
        tables_here = []
        for line in lines:
            text = line_text(line).strip()
            if in_header:                                       # title block at the top of every page ends with the line naming the year
                seen += 1
                m1, m2 = TITLE_YEAR_RE.search(text), TITLE_ROUND_RE.search(text)
                if m1: header_info["year"] = "%s-%s" % (m1.group(1), m1.group(2)[-2:])
                if m2 and header_info["round"] is None: header_info["round"] = m2.group(1)
                if m1: in_header = False; continue
                if seen <= 6 and not (INST_RE.match(text) or COURSE_RE.match(text)): continue
                in_header = False                               # no year line where expected: do NOT skip blindly
                problem(page, "page title block not recognised (first lines: %s)" % text[:70])
            if SKIP_RE.match(text): continue
            m = INST_RE.match(text)
            if m:
                flush_pending(page)
                code = norm_institute_code(m.group(1))
                if code != st["inst_code"]:
                    st.update(inst_code=code, inst_name=m.group(2).strip(), course=None, status=None, uni=None, title=[], table=None)
                    stats["institutes"].add(code)
                continue
            m = COURSE_RE.match(text)
            if m:
                flush_pending(page)
                code = norm_choice_code(m.group(1))
                if not choice_matches_institute(code, st["inst_code"]): problem(page, "course %s does not start with institute code %s" % (m.group(1), st["inst_code"]))
                st.update(course=(code, m.group(2).strip()), status=None, uni=None, title=[], table=None, course_wrap=True)
                stats["courses"].add(code); continue
            if CODEISH_RE.match(text):
                problem(page, "heading looks like an institute or course code but is not in a known form: %s" % text[:80]); continue
            m = STATUS_RE.match(text)
            if m:
                s_ = m.group(1); hu = HOME_UNI_RE.match(s_)
                st["status"], st["uni"] = (hu.group(1).strip(), hu.group(2).strip()) if hu else (s_.strip(), None)
                st["course_wrap"] = False; st["title"] = []; continue
            if line[0].text == "Stage":
                flush_pending(page)
                codes = line[1:]
                if not codes or not all(CODE_RE.match(w.text) for w in codes): problem(page, "unreadable column headings: %s" % text[:80]); st["table"] = None; continue
                title = list(st["title"]) or ["(no section title)"]
                st["table"] = {"hdr_y": line[0].y0, "last_hdr_y": line[0].y0, "header": [(w.text, (w.x0 + w.x1) / 2) for w in codes], "section_title": title, "rows": [], "inst_code": st["inst_code"],
                               "inst_name": st["inst_name"], "course": st["course"], "status": st["status"], "uni": st["uni"]}
                tables_here.append(st["table"]); titles[" ".join(title)] = titles.get(" ".join(title), 0) + 1
                stats["tables"] += 1; st["title"] = []; continue
            tbl = st["table"]
            if tbl and not tbl["rows"] and st["pending"] is None and all(re.fullmatch(r"[A-Z][A-Z0-9]{0,11}", w.text) for w in line) and 0 < line[0].y0 - tbl["last_hdr_y"] <= 14.0:
                for w in line:                                    # a long seat code wrapped onto a second line of the heading (PWDROBC / S)
                    cx = (w.x0 + w.x1) / 2; k = min(range(len(tbl["header"])), key=lambda i: abs(tbl["header"][i][1] - cx))
                    if abs(tbl["header"][k][1] - cx) <= 22.0: tbl["header"][k] = (tbl["header"][k][0] + w.text, tbl["header"][k][1])
                    else: problem(page, "heading fragment %s fits under no column" % w.text)
                tbl["last_hdr_y"] = line[0].y0; continue
            if tbl:
                label_words = [w for w in line if not INT_RE.match(w.text) and not PCT_RE.match(w.text)]
                num_words = [w for w in line if INT_RE.match(w.text)]
                pct_words = [w for w in line if PCT_RE.match(w.text)]
                label = " ".join(w.text for w in label_words)
                left_of_numbers = label_words and num_words and all(w.x1 <= min(n.x0 for n in num_words) for w in label_words)
                if num_words and not pct_words and left_of_numbers:        # any label printed left of the numbers is a stage label (I, VII, I-Non, MH, ...)
                    flush_pending(page); st["pending"] = {"label": label, "nums": num_words, "page": page, "y": line[0].y0, "tbl": tbl}; labels[label] = labels.get(label, 0) + 1; continue
                if pct_words and not num_words and st["pending"]:
                    pd = st["pending"]; full = (pd["label"] + (" " + label if label else "")).strip()
                    pd["tbl"]["rows"].append((pd["y"], full)); emit(pd["tbl"], pd["page"], full, pd["nums"], pct_words); st["pending"] = None; continue
            flush_pending(page)
            if st["course"] and st["course_wrap"] and st["status"] is None:     # long course names wrap onto a second line
                st["course"] = (st["course"][0], st["course"][1] + " " + text); continue
            if st["course"] and st["status"] is not None:
                if st["table"] is not None: st["table"] = None; st["title"] = []        # a new section begins after a finished table
                st["title"].append(text); continue
            if text: problem(page, "unrecognised line: %s" % text[:90])
        flush_pending(page)
        last_main = tables_here or last_main
    stats["institutes"], stats["courses"] = len(stats["institutes"]), len(stats["courses"])
    if meta:
        if header_info["year"] and meta.get("year_label") and header_info["year"][:4] != meta["year_label"][:4]: prob.append({"page": 0, "problem": "file says A.Y. %s but it was archived as %s" % (header_info["year"], meta["year_label"])})
        if header_info["round"] and meta.get("cap_round") and header_info["round"] != meta["cap_round"]: prob.append({"page": 0, "problem": "file says CAP Round %s but it was archived as %s" % (header_info["round"], meta["cap_round"])})
    return {"records": rec, "problems": prob, "stats": stats, "titles": titles, "stage_labels": labels, "file_header": header_info}


# ----------------------------------------------------------------------------------------------- command line
import argparse, csv, gzip, io, json, os, sys, collections
from .archive import load_manifest, sha256_file

COLUMNS = ["year_label", "cap_round", "list_type", "institute_code", "institute_name", "choice_code", "course_name", "status", "home_university",
           "section", "seat_pool", "allotted_to", "stage", "seat_code", "merit_no", "percentile", "page", "source_sha256"]


def write_csv_gz(path, records, meta):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    buf = io.StringIO(); w = csv.writer(buf, lineterminator="\n"); w.writerow(COLUMNS)
    for r in records: w.writerow([meta["year_label"], meta["cap_round"]] + [r[c] if r[c] is not None else "" for c in COLUMNS[2:-1]] + [meta["sha256"]])
    with open(path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz: gz.write(buf.getvalue().encode("utf-8"))      # mtime=0: identical input gives identical bytes


def merit_conflicts(records):
    seen = collections.defaultdict(set)
    for r in records: seen[(r["seat_pool"], r["allotted_to"], r["merit_no"])].add(r["percentile"])
    return sum(1 for v in seen.values() if len(v) > 1)


def run_cli(manifest_path, files_dir, out_dir, now=None):
    man = load_manifest(manifest_path); report = {"generated_at": now, "files": [], "all_ok": True}
    docs = [d for d in man["documents"].values() if d.get("doc_type") == "cutoff" and d.get("scope") == "MH"]
    for d in sorted(docs, key=lambda d: (d["year_label"], d["cap_round"])):
        f = man["files"].get(d.get("current_sha256")); entry = {"year_label": d["year_label"], "cap_round": d["cap_round"], "asset": f and f["asset_name"], "source_sha256": f and f["sha256"]}
        report["files"].append(entry)
        if not f: entry["error"] = "not archived"; report["all_ok"] = False; continue
        path = os.path.join(files_dir, f["asset_name"])
        if not os.path.exists(path): entry["error"] = "file not present in %s" % files_dir; report["all_ok"] = False; continue
        if sha256_file(path) != f["sha256"]: entry["error"] = "fingerprint mismatch: the file is not the archived one, refusing to read it"; report["all_ok"] = False; continue
        r = parse_pdf(path, meta={"year_label": d["year_label"], "cap_round": d["cap_round"]}); s = r["stats"]
        out = os.path.join(out_dir, "%s_round-%s_MH.csv.gz" % (d["year_label"], d["cap_round"]))
        write_csv_gz(out, r["records"], {"year_label": d["year_label"], "cap_round": d["cap_round"], "sha256": f["sha256"]})
        entry.update({"output": os.path.basename(out), "cells": s["cells"], "printed_percentiles": s["printed_percentiles"], "complete": s["cells"] == s["printed_percentiles"], "pages": s["pages"], "overflow_pages": s["overflow_pages"],
                      "institutes": s["institutes"], "courses": s["courses"], "tables": s["tables"], "problem_count": len(r["problems"]), "problems": r["problems"][:20], "section_titles": r["titles"],
                      "stage_labels": r["stage_labels"], "seat_codes": sorted({x["seat_code"] for x in r["records"]}), "merit_number_conflicts": merit_conflicts(r["records"])})
        if r["problems"] or not entry["complete"]: report["all_ok"] = False
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "parse_report_mh.json"), "w", encoding="utf-8") as fh: fh.write(json.dumps(report, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read the archived Maharashtra State cutoff PDFs into normalized CSV files (Stage 9a).")
    ap.add_argument("--manifest", default="data/raw/manifest.json"); ap.add_argument("--files", default="data/raw/files"); ap.add_argument("--out", default="data/normalized/cutoffs_mh"); ap.add_argument("--now")
    a = ap.parse_args(argv); rep = run_cli(a.manifest, a.files, a.out, a.now)
    for e in rep["files"]:
        print("%s round %s: %s" % (e["year_label"], e["cap_round"], e.get("error") or "%d cells, printed %d, %s, %d problem(s), %d overflow page(s)" % (e["cells"], e["printed_percentiles"], "COMPLETE" if e["complete"] else "INCOMPLETE", e["problem_count"], e["overflow_pages"])))
    return 0 if rep["all_ok"] else 4


if __name__ == "__main__":
    sys.exit(main())
