"""Stage 11c: match the read vacancy rows to the website's courses and write the website vacancy table.

Run: python -m ingestion.build_vacancy  -> data/normalized/tables/vacancy.csv + vacancy_build_report.json
Rules (owner): vacancy of the CURRENT admission year only (from the automatic plan); one round dataset-wide (Round IV, else III - chosen by
ingestion/read_vacancy.py, never mixed); a vacancy table of any other year is never used as the current vacancy; intake (intake_si) is a
separate column and never vacancy; a missing value stays missing (never zero). A course is matched by its Choice Code; the institute code
of the vacancy row must agree with the master table, otherwise the build FAILS. A Choice Code that is not in the master tables is kept and
marked new_course (it has vacancy but no cutoff history). Course names printed in the vacancy file are only reported when they differ.
If there is no vacancy table for the current year the build succeeds, writes NO vacancy table and says so (the page keeps 'Vacancy data unavailable').
"""
import csv, gzip, json, os, re, sys
from ingestion import plan as P
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
N = os.path.join(ROOT, "data", "normalized")
ROUND_PREF = ("IV", "III")
OUT_COLS = ["choice_code", "admission_year", "vacancy_round", "intake_si", "vacant_cap_seats", "ms_seats", "minority_seats", "all_india_seats",
            "institute_seats", "orphan_inst_seats", "orphan_non_inst_seats", "pwd_total", "def_total", "ews_seats", "tfws_seats", "match",
            "source_doc_id", "source_url", "grid_json"]


def _name_key(s): return re.sub(r"\s+", "", s or "").lower()


def find_tables(vdir):
    out = {}
    if not os.path.isdir(vdir): return out
    for fn in sorted(os.listdir(vdir)):
        m = re.match(r"^(\d{4}-\d{2})_round-(IV|III)_vacancy\.csv\.gz$", fn)
        if m: out.setdefault(m.group(1), {})[m.group(2)] = os.path.join(vdir, fn)
    return out


def build(base=N, plan=None, outdir=None, manifest_path=None):
    plan = plan or json.load(open(os.path.join(base, "data_plan.json"), encoding="utf-8"))
    if not plan.get("ok"): raise SystemExit("no valid plan")
    year = plan.get("admission_year", plan["current_year"])      # Stage 14b: the year the student applies for; last year's vacancy is never shown as this year's
    outdir = outdir or os.path.join(base, "tables"); os.makedirs(outdir, exist_ok=True)
    rep = dict(ok=False, year=year, status="", round=None, rows=0, matched=0, new_courses=[], institute_mismatch=[], name_differences=[],
               current_courses_without_vacancy=None, old_courses_without_vacancy=None, problems=[], notes=[])
    tables = find_tables(os.path.join(base, "vacancy"))
    for y in sorted(tables):
        if y != year: rep["notes"].append("vacancy table of %s ignored: the current admission year is %s" % (y, year))
    out_csv = os.path.join(outdir, "vacancy.csv")
    if year not in tables:
        rep.update(ok=True, status="unavailable: no Round IV or Round III vacancy table for %s" % year)
        if os.path.exists(out_csv): os.remove(out_csv)
        _save(outdir, rep); return rep
    rnd = next(r for r in ROUND_PREF if r in tables[year])
    for r in tables[year]:
        if r != rnd: rep["notes"].append("Round %s table not used because Round %s exists" % (r, rnd))
    rep["round"] = rnd
    with gzip.open(tables[year][rnd], "rt", encoding="utf-8", newline="") as f: rows = list(csv.DictReader(f))
    with open(os.path.join(base, "master", "courses.csv"), newline="", encoding="utf-8") as f: courses = {c["choice_code"]: c for c in csv.DictReader(f)}
    branches = set()
    bp = os.path.join(outdir, "branches.csv")
    if os.path.exists(bp):
        with open(bp, newline="", encoding="utf-8") as f: branches = {r["choice_code"] for r in csv.DictReader(f)}
    mpath = manifest_path or os.path.join(ROOT, "data", "raw", "manifest.json")
    files = json.load(open(mpath, encoding="utf-8"))["files"] if os.path.exists(mpath) else {}
    out, seen = [], set()
    for r in rows:
        cc = r["choice_code"]
        if r["portal_year"] != year or r["cap_round"] != rnd: rep["problems"].append("%s: row says %s round %s, expected %s round %s" % (cc, r["portal_year"], r["cap_round"], year, rnd)); continue
        if cc in seen: rep["problems"].append("%s: duplicate choice code" % cc); continue
        seen.add(cc)
        c = courses.get(cc)
        if c is None:
            match = "new_course"; rep["new_courses"].append([cc, r["institute_code"], r["course_name"]])
        else:
            match = "master"; rep["matched"] += 1
            if c["institute_code"] != r["institute_code"]: rep["institute_mismatch"].append([cc, r["institute_code"], c["institute_code"]])
            if _name_key(c["course_name"]) != _name_key(r["course_name"]): rep["name_differences"].append([cc, r["course_name"], c["course_name"]])
        sha = r["source_sha256"]
        f = files.get(sha, {})
        out.append(dict(choice_code=cc, admission_year=year, vacancy_round=rnd, intake_si=r["intake_si"], vacant_cap_seats=r["vacant_cap_seats"], ms_seats=r["ms_seats"],
                        minority_seats=r["minority_seats"], all_india_seats=r["all_india_seats"], institute_seats=r["institute_seats"],
                        orphan_inst_seats=r["orphan_inst_seats"], orphan_non_inst_seats=r["orphan_non_inst_seats"], pwd_total=r["pwd_total"], def_total=r["def_total"],
                        ews_seats=r["ews_seats"], tfws_seats=r["tfws_seats"], match=match, source_doc_id="DOC-" + sha[:16],
                        source_url=(f.get("urls") or [""])[0], grid_json=r["grid_json"]))
    if rep["institute_mismatch"]: rep["problems"].append("%d choice codes belong to a different institute in the vacancy file than in the master tables" % len(rep["institute_mismatch"]))
    if not out: rep["problems"].append("the vacancy table has no usable rows")
    rep["rows"] = len(out)
    cur = set()
    cp = os.path.join(outdir, "current_cutoffs.csv.gz")
    if os.path.exists(cp):
        with gzip.open(cp, "rt", encoding="utf-8", newline="") as f: cur = {r["choice_code"] for r in csv.DictReader(f)}
        rep["current_courses_without_vacancy"] = len(cur - seen)     # these show 'Not available' (never zero)
        rep["old_courses_without_vacancy"] = len((branches - cur) - seen) if branches else None   # courses only listed in earlier years
    rep["status"] = "ok: vacancy of %s Round %s" % (year, rnd)
    if rep["problems"]:
        rep["status"] = "FAILED"
        _save(outdir, rep); return rep
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=OUT_COLS); w.writeheader(); w.writerows(out)
    rep["ok"] = True
    _save(outdir, rep); return rep


def _save(outdir, rep):
    with open(os.path.join(outdir, "vacancy_build_report.json"), "w", encoding="utf-8") as fh: json.dump(rep, fh, indent=1, ensure_ascii=False)


def main(argv=None):
    rep = build()
    print(rep["status"])
    for k in ("rows", "matched"): print(k, rep[k])
    print("new courses (no cutoff history):", len(rep["new_courses"]), "| name differences:", len(rep["name_differences"]), "| current-year courses without vacancy:", rep["current_courses_without_vacancy"], "| earlier-year-only courses without vacancy:", rep["old_courses_without_vacancy"])
    for n in rep["notes"]: print("note:", n)
    for p in rep["problems"]: print("FAIL:", p)
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
