"""Stage 10c-2: turn the validated normalized State-list data into the website's tables (schema v0.5).
Run: python -m ingestion.build_tables  -> data/normalized/tables/  (colleges, branches, seat_types, source_documents, current_cutoffs, historical_cutoffs)
Rules: which lists are used comes from the automatic plan (ingestion/plan.py); one closing figure per (round, course, section, seat code)
= the lowest percentile over the stages present (all stages stay in the stage/merit columns of that row's source list; see docs/STAGE10A.md);
home university is resolved per row (printed | inferred from the course's single printed value | unknown | not_needed); nothing is invented:
district is 'Not available' (the lists do not print it)."""
import csv, gzip, hashlib, json, os, sys
from collections import defaultdict
from ingestion import plan as P, eligibility as EL
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
N = os.path.join(ROOT, "data", "normalized")
HU_SECTIONS = {EL.S_HU_HU, EL.S_HU_OHU, EL.S_OHU_HU, EL.S_OHU_OHU}
NA = "Not available"
CUT_COLS = ["cutoff_id", "choice_code", "admission_year", "cap_round", "seat_type_code", "cutoff_percentile", "cutoff_rank", "published_date", "source_doc_id",
            "retrieved_date", "validation_status", "is_synthetic", "section", "stage", "merit_no", "merit_exam", "home_university", "home_university_basis"]

def doc_id(sha): return "DOC-" + sha[:16]

def printed_values(rows):
    """choice_code -> set of home-university values printed anywhere in the data."""
    d = defaultdict(set)
    for r in rows:
        if r["home_university"]: d[r["choice_code"]].add(r["home_university"])
    return d

def resolve_hu(row, printed):
    """(home_university, basis). Never guesses: several printed values or none -> 'unknown' for the home-university sections."""
    if row["home_university"]: return row["home_university"], "printed"
    if row["section"] not in HU_SECTIONS: return "", "not_needed"
    v = printed.get(row["choice_code"], set())
    if len(v) == 1: return next(iter(v)), "inferred"
    return "", "unknown"

def printed_zero(r):
    """A printed percentile of 0 next to a real merit number is a placeholder, not a cutoff (e.g. merit no 5776 cannot be percentile 0):
    kept in the normalized data, excluded from the website tables, counted in the build report."""
    try: return float(r["percentile"]) <= 0
    except (ValueError, KeyError): return False

def collapse(rows, printed):
    """One closing row per (year, round, course, section, seat code); lowest percentile wins; blank percentiles are skipped (never zero)."""
    out = {}
    for r in rows:
        if not (r.get("percentile") or "").strip() or printed_zero(r): continue
        k = (r["year_label"], r["cap_round"], r["choice_code"], r["section"], r["seat_code"])
        if k not in out or float(r["percentile"]) < float(out[k]["percentile"]): out[k] = r
    res = []
    for k, r in out.items():
        hu, basis = resolve_hu(r, printed)
        cid = "CUT" + hashlib.sha1("|".join(k).encode()).hexdigest()[:12].upper()
        res.append({"cutoff_id": cid, "choice_code": r["choice_code"], "admission_year": r["year_label"], "cap_round": r["cap_round"], "seat_type_code": r["seat_code"],
                    "cutoff_percentile": r["percentile"], "cutoff_rank": "", "published_date": "", "source_doc_id": doc_id(r["source_sha256"]), "retrieved_date": "",
                    "validation_status": "validated", "is_synthetic": "FALSE", "section": r["section"], "stage": r["stage"], "merit_no": r["merit_no"],
                    "merit_exam": "MHT-CET", "home_university": hu, "home_university_basis": basis})
    res.sort(key=lambda x: (x["admission_year"], x["cap_round"], x["choice_code"], x["section"], x["seat_type_code"]))
    return res

def seat_type_rows(seat_codes):
    fam = {"regular": "regular", "ews": "EWS", "tfws": "TFWS", "pwd": "PWD", "defence": "Defence", "phc": "PHC", "orphan": "Orphan", "minority": "Minority"}
    out = []
    for c, i in sorted(seat_codes.items()):
        out.append({"seat_type_code": c, "candidate_type": "Maharashtra State candidate", "category": i["category"] or fam.get(i["family"], i["family"]),
                    "gender_scope": i.get("gender_scope", ""), "seat_level": {"H": "Home University", "O": "Other Than Home University", "S": "State Level"}.get(c[-1], ""),
                    "description": "family=%s variant=%s (official legend: first letter G/L, last letter H/O/S)" % (i["family"], i.get("variant", "")), "is_provisional": "FALSE"})
    return out

def read_gz(p):
    with gzip.open(p, "rt", newline="", encoding="utf-8") as f: return list(csv.DictReader(f))
def write_csv(path, cols, rows, gz=False):
    op = (lambda p: gzip.open(p, "wt", newline="", encoding="utf-8")) if gz else (lambda p: open(p, "w", newline="", encoding="utf-8"))
    with op(path) as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n"); w.writeheader(); w.writerows(rows)

def build(base=N, plan=None, outdir=None):
    plan = plan or P.make_plan(json.load(open(P.DISCOVERY))["admission_year"])
    if not plan["ok"]: raise SystemExit("no valid plan: " + plan["problem"])
    outdir = outdir or os.path.join(base, "tables"); os.makedirs(outdir, exist_ok=True)
    need = {(x["year"], x["round"]): x["role"] for x in plan["required_lists"]}
    allrows, sel = [], []
    for fn in sorted(os.listdir(os.path.join(base, "cutoffs_mh"))):
        if fn.endswith(".csv.gz"):
            rows = read_gz(os.path.join(base, "cutoffs_mh", fn)); allrows += rows
            if (rows[0]["year_label"], rows[0]["cap_round"]) in need: sel.append((need[(rows[0]["year_label"], rows[0]["cap_round"])], rows))
    printed = printed_values(allrows)
    zeros = sum(1 for _, rows in sel for r in rows if r["percentile"] and printed_zero(r))
    cur = collapse([r for role, rows in sel if role == "current" for r in rows], printed)
    his = collapse([r for role, rows in sel if role == "history" for r in rows], printed)
    mdir = os.path.join(base, "master")
    def rd(n):
        with open(os.path.join(mdir, n), newline="", encoding="utf-8") as f: return list(csv.DictReader(f))
    used = {r["choice_code"] for r in cur + his}
    courses = [c for c in rd("courses.csv") if c["choice_code"] in used]
    colleges = {c["institute_code"]: c for c in rd("colleges.csv")}
    ccodes = sorted({c["institute_code"] for c in courses})
    col_rows = [{"college_code": ic, "college_name": colleges[ic]["institute_name"], "district": NA, "city": "", "college_type": colleges[ic]["status_latest"],
                 "status": "active", "previous_college_code": "", "college_website": "", "autonomy_status": "autonomous" if colleges[ic]["home_university_latest"] == "Autonomous Institute" else "unknown",
                 "campus_area_acres": "", "source_doc_id": "", "retrieved_date": "", "validation_status": "validated", "is_synthetic": "FALSE"} for ic in ccodes]
    sha_of = {r["source_doc_id"] for r in cur + his}
    yr_rd = {doc_id(r["source_sha256"]): (r["year_label"], r["cap_round"]) for _, rows in sel for r in rows}
    br_rows = [{"choice_code": c["choice_code"], "college_code": c["institute_code"], "branch_code": c["choice_code"][5:], "branch_name": c["course_name"], "branch_group": "",
                "valid_from_year": c["first_year"], "valid_to_year": "", "source_doc_id": "", "retrieved_date": "", "validation_status": "validated", "is_synthetic": "FALSE"} for c in courses]
    man = json.load(open(os.path.join(ROOT, "data", "raw", "manifest.json")))["files"]
    docs = []
    for sha, m in sorted(man.items()):
        if doc_id(sha) in sha_of:
            docs.append({"doc_id": doc_id(sha), "source_name": "CET Cell Maharashtra", "source_url": m["urls"][0], "filename": m["asset_name"], "sha256": sha, "admission_year": yr_rd[doc_id(sha)][0],
                         "doc_type": "cutoff", "cap_round": yr_rd[doc_id(sha)][1], "published_date": "", "retrieved_date": "", "validation_status": "validated", "is_synthetic": "FALSE"})
    sc = EL.load_seat_codes(os.path.join(mdir, "seat_codes.csv"))
    write_csv(os.path.join(outdir, "current_cutoffs.csv.gz"), CUT_COLS, cur, gz=True)
    write_csv(os.path.join(outdir, "historical_cutoffs.csv.gz"), CUT_COLS, his, gz=True)
    write_csv(os.path.join(outdir, "colleges.csv"), list(col_rows[0]), col_rows); write_csv(os.path.join(outdir, "branches.csv"), list(br_rows[0]), br_rows)
    st = seat_type_rows(sc); write_csv(os.path.join(outdir, "seat_types.csv"), list(st[0]), st)
    write_csv(os.path.join(outdir, "source_documents.csv"), list(docs[0]), docs)
    basis = defaultdict(int)
    for r in cur + his: basis[r["home_university_basis"]] += 1
    rep = {"current_year": plan["current_year"], "current_rows": len(cur), "history_rows": len(his), "colleges": len(col_rows), "branches": len(br_rows), "seat_types": len(st),
           "source_documents": len(docs), "home_university_basis": dict(basis), "excluded_printed_zero_percentile_cells": zeros, "district": "Not available for every college (not printed in the lists)"}
    json.dump(rep, open(os.path.join(outdir, "build_report.json"), "w"), indent=1)
    return rep

if __name__ == "__main__":
    print(json.dumps(build(), indent=1))
