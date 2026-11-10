"""Stage 10b: validate the normalized cutoff data before it is turned into engine tables (read-only; never edits data).
Run: python -m ingestion.validate_cutoffs   -> writes data/normalized/validation_report.json and prints a summary.
Errors = data cannot be published as is. Warnings = documented oddities that are kept as printed (counted, never corrected)."""
import csv, gzip, json, os, re, sys
from collections import defaultdict, Counter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
N = os.path.join(ROOT, "data", "normalized")
from ingestion import plan as P                          # the automatic plan: which year, which rounds (never hard-coded here)
ROUND_ORDER = {"I": 1, "II": 2, "III": 3, "IV": 4}
KNOWN_STAGES = {"I", "II", "VII", "I-Non", "MH"}
PCT = re.compile(r"^\d{1,3}\.\d{7}$")

def read(path):
    with gzip.open(path, "rt", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
def read_plain(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def validate(base=N, max_examples=8, plan=None):
    plan = plan or P.make_plan(json.load(open(P.DISCOVERY))["admission_year"])
    mh_dir, ai_dir, mdir = (os.path.join(base, x) for x in ("cutoffs_mh", "cutoffs_ai", "master"))
    colleges = {r["institute_code"]: r for r in read_plain(os.path.join(mdir, "colleges.csv"))}
    courses = {r["choice_code"]: r for r in read_plain(os.path.join(mdir, "courses.csv"))}
    seats = {r["code"] for r in read_plain(os.path.join(mdir, "seat_codes.csv"))}
    unis = {r["home_university"] for r in read_plain(os.path.join(mdir, "home_universities.csv"))}
    err, warn, ex = Counter(), Counter(), defaultdict(list)
    def E(k, e=None): err[k] += 1; (e is not None and len(ex[k]) < max_examples and ex[k].append(e))
    def W(k, e=None): warn[k] += 1; (e is not None and len(ex[k]) < max_examples and ex[k].append(e))
    lists, rounds_seen, parsed = [], defaultdict(set), {"MH": set(), "AI": set()}
    printed, blank = defaultdict(set), Counter()          # per course: home-university values printed / blank rows
    for fn in sorted(os.listdir(mh_dir)):
        if not fn.endswith(".csv.gz"): continue
        rows = read(os.path.join(mh_dir, fn))
        yr, rd = rows[0]["year_label"], rows[0]["cap_round"]; rounds_seen[yr].add(rd); parsed["MH"].add((yr, rd))
        by_merit = defaultdict(set); pairs = []
        for r in rows:
            if (r["year_label"], r["cap_round"]) != (yr, rd): E("MIXED_LIST_IN_FILE", fn)
            if r["percentile"] and not PCT.match(r["percentile"]): E("BAD_PERCENTILE_FORMAT", (fn, r["percentile"]))
            elif r["percentile"] and not 0 <= float(r["percentile"]) <= 100: E("PERCENTILE_OUT_OF_RANGE", (fn, r["percentile"]))
            if r["percentile"] and PCT.match(r["percentile"]) and float(r["percentile"]) <= 0: W("PRINTED_ZERO_PERCENTILE", (fn, r["choice_code"], r["seat_code"], r["merit_no"]))
            if not r["percentile"]: E("BLANK_PERCENTILE", (fn, r["choice_code"], r["seat_code"]))
            if not r["merit_no"].isdigit(): E("BAD_MERIT_NO", (fn, r["merit_no"]))
            if r["stage"] not in KNOWN_STAGES and not r["stage"].startswith("I-Non"): W("UNLISTED_STAGE", r["stage"])
            ic = r["institute_code"]
            if r["choice_code"][:5] != ic: E("CHOICE_CODE_INSTITUTE_MISMATCH", (fn, r["choice_code"], ic))
            if ic not in colleges: E("INSTITUTE_NOT_IN_MASTER", (fn, ic))
            if r["choice_code"] not in courses: E("COURSE_NOT_IN_MASTER", (fn, r["choice_code"]))
            if r["seat_code"] not in seats: E("SEAT_CODE_NOT_IN_MASTER", (fn, r["seat_code"]))
            if r["home_university"] and r["home_university"] not in unis: E("UNKNOWN_HOME_UNIVERSITY", (fn, r["home_university"]))
            mu = colleges.get(ic, {}).get("home_university_latest", "")
            if not r["home_university"]:
                blank[r["choice_code"]] += 1; W("ROW_HOME_UNIVERSITY_BLANK")      # some lists leave it blank
            else:
                printed[r["choice_code"]].add(r["home_university"])
                if mu and r["home_university"] != mu: W("ROW_HOME_UNIVERSITY_DIFFERS_FROM_MASTER", (fn, ic, r["home_university"], mu))
            if r["merit_no"].isdigit() and r["percentile"]:
                by_merit[int(r["merit_no"])].add(r["percentile"]); pairs.append((int(r["merit_no"]), float(r["percentile"])))
        conf = {m: sorted(p) for m, p in by_merit.items() if len(p) > 1}
        for m, p in list(conf.items())[:max_examples]: ex["CONFLICTING_MERIT_PERCENTILE"].append((fn, m, p))
        warn["CONFLICTING_MERIT_PERCENTILE"] += len(conf)
        # percentile must never rise as merit number rises (ignoring the already-counted conflicting merit numbers)
        cl = {m: min(float(x) for x in p) for m, p in by_merit.items()}
        ms = sorted(cl); rises = [cl[b] - cl[a] for a, b in zip(ms, ms[1:]) if cl[b] > cl[a] + 1e-9]; inv = len(rises)
        big = sum(1 for x in rises if x > 0.5)
        if inv: W("PERCENTILE_RISES_WITH_MERIT_NO", (fn, inv, "of which over 0.5 percentile:", big, "largest:", round(max(rises), 4)))
        if big: warn["PERCENTILE_RISES_OVER_HALF_POINT"] += big
        lists.append({"file": fn, "year": yr, "round": rd, "rows": len(rows), "conflicting_merit_numbers": len(conf), "order_inversions": inv})
    res = amb = nev = 0
    for cc, n in blank.items():
        v = printed.get(cc, set())
        if len(v) == 1: res += n
        elif len(v) > 1: amb += n
        else: nev += n
    warn["BLANK_HOME_UNIVERSITY_ROWS_COURSE_PRINTS_ONE_VALUE_ELSEWHERE"] = res
    warn["BLANK_HOME_UNIVERSITY_ROWS_COURSE_PRINTS_SEVERAL_VALUES"] = amb
    warn["BLANK_HOME_UNIVERSITY_ROWS_NEVER_PRINTED_FOR_COURSE"] = nev
    for fn in sorted(os.listdir(ai_dir)):
        if not fn.endswith(".csv.gz"): continue
        rows = read(os.path.join(ai_dir, fn)); yr, rd = rows[0]["year_label"], rows[0]["cap_round"]; rounds_seen[yr].add(rd); parsed["AI"].add((yr, rd))
        for r in rows:
            if r["choice_code"][:5] != r["institute_code"]: E("AI_CHOICE_CODE_INSTITUTE_MISMATCH", (fn, r["choice_code"]))
            if r["institute_code"] not in colleges: E("AI_INSTITUTE_NOT_IN_MASTER", (fn, r["institute_code"]))
            if not r["score"]: W("AI_BLANK_SCORE_KEPT_BLANK", (fn, r["choice_code"]))
            if r["merit_exam_kind"] not in ("JEE", "NEET", "MHT-CET"): W("AI_UNLISTED_EXAM_KIND", r["merit_exam_kind"])
    # year / round rules come from the automatic plan
    if not plan.get("ok"): E("NO_PLAN", plan.get("problem"))
    need = {(x["year"], x["round"]) for x in plan.get("required_lists", [])}
    for scope in ("MH", "AI"):
        for yr, rd in sorted(need - parsed[scope]): E("PLANNED_LIST_NOT_PARSED", (scope, yr, rd))
        for yr, rd in sorted(parsed[scope] - need): W("PARSED_LIST_NOT_IN_PLAN", (scope, yr, rd))
    planned_years = {x["year"] for x in plan.get("required_lists", [])}
    for yr in rounds_seen:
        if planned_years and yr not in planned_years: E("YEAR_OUTSIDE_PLAN", yr)
    warn = Counter({k: v for k, v in warn.items() if v})
    return {"errors": dict(err), "warnings": dict(warn), "examples": {k: v for k, v in ex.items()}, "lists": lists,
            "parsed_rounds_per_year": {y: sorted(r, key=ROUND_ORDER.get) for y, r in rounds_seen.items()}, "plan": plan, "ok": not err}

if __name__ == "__main__":
    rep = validate()
    with open(os.path.join(N, "validation_report.json"), "w") as f: json.dump(rep, f, indent=1, default=list)
    print(json.dumps({k: rep[k] for k in ("ok", "errors", "warnings", "parsed_rounds_per_year")}, indent=1)); sys.exit(0 if rep["ok"] else 1)
