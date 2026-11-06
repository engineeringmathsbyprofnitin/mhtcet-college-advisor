"""Master tables built from the normalized cutoff files (Stage 9c): colleges, courses, seat codes, home universities and name histories.

Everything here is DERIVED from the State and All India cutoff lists. Facts the lists do not contain (district, city, website, fees,
accreditation) are left blank for later stages; nothing is guessed. Seat codes are split into their printed parts; only the first letter
G/L and the last letter H/O/S are defined by the lists' own legend. Other parts (for example the R in DEFR.../PWDR..., the final letter of
ORPHAN codes, the older PHC codes) are kept as printed and not interpreted.
"""
import argparse, collections, csv, gzip, json, os, re, sys

ROUND_ORDER = {"I": 1, "II": 2, "III": 3, "IV": 4}
CATS = "OPEN|SC|ST|VJ|NT1|NT2|NT3|OBC|SEBC"
LEVEL = {"H": "Home University", "O": "Other Than Home University", "S": "State Level"}
SEAT_RES = [("regular", re.compile(r"^(?P<g>[GL])(?P<cat>%s)(?P<lvl>[HOS])$" % CATS)),
            ("defence", re.compile(r"^DEF(?P<var>R?)(?P<cat>(?:%s)?)(?P<lvl>[HOS])$" % CATS)),
            ("pwd", re.compile(r"^PWD(?P<var>R?)(?P<cat>(?:%s)?)(?P<lvl>[HOS])$" % CATS)),
            ("phc", re.compile(r"^PHC(?P<var>)(?P<cat>(?:%s)?)(?P<lvl>[HOS])$" % CATS)),
            ("tfws", re.compile(r"^TFWS$")), ("ews", re.compile(r"^EWS$")), ("minority", re.compile(r"^MI$")),
            ("orphan", re.compile(r"^ORPHAN(?P<var>[IN2]?)$")), ("all_india_seat", re.compile(r"^AI$"))]


def parse_seat_code(code):
    for fam, rx in SEAT_RES:
        m = rx.match(code)
        if m:
            d = m.groupdict()
            return {"code": code, "family": fam, "gender_scope": {"G": "General", "L": "Ladies"}.get(d.get("g"), ""), "category": d.get("cat") or "",
                    "level_letter": d.get("lvl") or "", "level_meaning": LEVEL.get(d.get("lvl") or "", ""), "variant": d.get("var") or ""}
    return {"code": code, "family": "other", "gender_scope": "", "category": "", "level_letter": "", "level_meaning": "", "variant": ""}


def _key(year, rnd): return (year, ROUND_ORDER.get(rnd, 0))
def _rname(n): return [r for r, v in ROUND_ORDER.items() if v == n][0] if n else ""


def _read(path):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh)


def _files(d, suffix):
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(suffix)) if d and os.path.isdir(d) else []


def build(mh_dir, ai_dir):
    prob = []
    inst = collections.defaultdict(lambda: {"names": {}, "status": {}, "uni": {}, "years": set(), "lists": set(), "courses": set()})
    crs = collections.defaultdict(lambda: {"inst": None, "names": {}, "status": {}, "uni": {}, "years": set(), "src": None})
    seat = collections.defaultdict(lambda: {"lists": set(), "years": set(), "cells": 0})
    for f in _files(mh_dir, "_MH.csv.gz"):
        for r in _read(f):
            k = _key(r["year_label"], r["cap_round"]); i = inst[r["institute_code"]]
            i["names"].setdefault(k, set()).add(r["institute_name"]); i["status"].setdefault(k, set()).add(r["status"]); i["uni"].setdefault(k, set()).add(r["home_university"])
            i["years"].add(r["year_label"]); i["lists"].add("MH"); i["courses"].add(r["choice_code"])
            c = crs[r["choice_code"]]; c["inst"] = r["institute_code"]; c["names"].setdefault(k, set()).add(r["course_name"]); c["status"].setdefault(k, set()).add(r["status"]); c["uni"].setdefault(k, set()).add(r["home_university"])
            c["years"].add(r["year_label"]); c["src"] = "State list"
            s = seat[r["seat_code"]]; s["lists"].add("MH"); s["years"].add(r["year_label"]); s["cells"] += 1
    ai_only = 0
    for f in _files(ai_dir, "_AI.csv.gz"):
        for r in _read(f):
            k = _key(r["year_label"], r["cap_round"])
            if r["seat_type"]:
                s = seat[r["seat_type"]]; s["lists"].add("AI"); s["years"].add(r["year_label"]); s["cells"] += 1
            if not r["choice_code"]: continue                                   # blank rows carry no course code
            i = inst[r["institute_code"]]; i["names"].setdefault(k, set()).add(r["institute_name"]); i["years"].add(r["year_label"]); i["lists"].add("AI"); i["courses"].add(r["choice_code"])
            c = crs[r["choice_code"]]
            if c["inst"] is None: c["inst"] = r["institute_code"]; c["src"] = "All India list (name may be shortened)"; ai_only += 1
            c["years"].add(r["year_label"])
            if c["src"] != "State list": c["names"].setdefault(k, set()).add(r["course_name"])
    for code, c in crs.items():
        if c["inst"] and code[:5] != c["inst"]: prob.append("course %s does not start with its institute code %s" % (code, c["inst"]))

    def latest(d): return d[max(d)] if d else set()
    colleges, chist, names_changed = [], [], 0
    for code in sorted(inst):
        i = inst[code]; per_year = {}
        for (y, rr), ns in i["names"].items(): per_year.setdefault(y, set()).update(ns)
        for k, ns in i["names"].items():
            if len(ns) > 1: prob.append("institute %s has %d different names in %s round %s: %s" % (code, len(ns), k[0], _rname(k[1]), " | ".join(sorted(ns))))
        distinct = sorted({n for ns in i["names"].values() for n in ns}); names_changed += len(distinct) > 1
        for y in sorted(per_year):
            for n in sorted(per_year[y]): chist.append({"institute_code": code, "year_label": y, "institute_name": n})
        st, un = latest(i["status"]), latest(i["uni"])
        colleges.append({"institute_code": code, "institute_name": sorted(latest(i["names"]))[0] if i["names"] else "", "status_latest": " | ".join(sorted(x for x in st if x)),
                         "home_university_latest": " | ".join(sorted(x for x in un if x)), "first_year": min(i["years"]), "last_year": max(i["years"]), "years_listed": " ".join(sorted(i["years"])),
                         "courses": len(i["courses"]), "name_changes": len(distinct) - 1, "lists": "+".join(sorted(i["lists"])), "district": "", "city": ""})
    courses, hist, cname_changed = [], [], 0
    for code in sorted(crs):
        c = crs[code]; m = re.match(r"^(\d{10})([A-Z]*)$", code); distinct = sorted({n for ns in c["names"].values() for n in ns}); cname_changed += len(distinct) > 1
        for k, ns in sorted(c["names"].items()):
            for n in sorted(ns): hist.append({"choice_code": code, "year_label": k[0], "cap_round": _rname(k[1]), "course_name": n})
        st, un = latest(c["status"]), latest(c["uni"])
        courses.append({"choice_code": code, "base_code": m.group(1) if m else code, "code_suffix": m.group(2) if m else "", "institute_code": c["inst"], "course_name": sorted(latest(c["names"]))[0] if c["names"] else "",
                        "name_source": c["src"], "status_latest": " | ".join(sorted(x for x in st if x)), "home_university_latest": " | ".join(sorted(x for x in un if x)),
                        "first_year": min(c["years"]), "last_year": max(c["years"]), "years_listed": " ".join(sorted(c["years"])), "name_changes": len(distinct) - 1})
    seats = []
    for code in sorted(seat):
        p = parse_seat_code(code); s = seat[code]
        if p["family"] == "other": prob.append("seat code %s does not fit any known pattern (kept as printed)" % code)
        seats.append(dict(p, lists="+".join(sorted(s["lists"])), first_year=min(s["years"]), last_year=max(s["years"]), cells=s["cells"]))
    unis = collections.defaultdict(lambda: {"colleges": set(), "courses": set()})
    for code, i in inst.items():
        for x in latest(i["uni"]):
            if x: unis[x]["colleges"].add(code)
    for code, c in crs.items():
        for x in latest(c["uni"]):
            if x: unis[x]["courses"].add(code)
    universities = [{"home_university": n, "kind": "autonomous-institute marker" if n == "Autonomous Institute" else "university" if "university" in n.lower() else "other", "colleges": len(v["colleges"]), "courses": len(v["courses"])} for n, v in sorted(unis.items())]
    summary = {"colleges": len(colleges), "courses": len(courses), "courses_only_in_all_india_list": ai_only, "seat_codes": len(seats), "seat_codes_not_recognised": sum(1 for s in seats if s["family"] == "other"),
               "home_universities": len(universities), "colleges_with_name_changes": names_changed, "courses_with_name_changes": cname_changed, "problems": len(prob)}
    return {"colleges": colleges, "courses": courses, "seat_codes": seats, "home_universities": universities, "college_name_history": chist, "course_name_history": hist}, summary, prob


def write(out_dir, tables, summary, prob, now=None):
    os.makedirs(out_dir, exist_ok=True)
    for name, rows in tables.items():
        with open(os.path.join(out_dir, name + ".csv"), "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["empty"], lineterminator="\n"); w.writeheader(); w.writerows(rows)
    with open(os.path.join(out_dir, "master_report.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"generated_at": now, "summary": summary, "problems": prob[:100], "problem_count": len(prob)}, indent=1, ensure_ascii=False, sort_keys=True) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the master tables from the normalized cutoff files (Stage 9c).")
    ap.add_argument("--mh-dir", default="data/normalized/cutoffs_mh"); ap.add_argument("--ai-dir", default="data/normalized/cutoffs_ai"); ap.add_argument("--out", default="data/normalized/master"); ap.add_argument("--now")
    a = ap.parse_args(argv)
    if not _files(a.mh_dir, "_MH.csv.gz"): print("No State-list files found in %s" % a.mh_dir); return 2
    tables, summary, prob = build(a.mh_dir, a.ai_dir); write(a.out, tables, summary, prob, a.now)
    print(json.dumps(summary)); [print("  PROBLEM:", p) for p in prob[:10]]
    return 0 if not prob else 4


if __name__ == "__main__":
    sys.exit(main())
