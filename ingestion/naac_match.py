"""Stage 12c-3: for every website college (tables/colleges.csv) find its record in the NAAC list (data/normalized/naac/naac_institutions.csv).

Same strict rules as the NBA matching (nba_match.py, never guess):
 - linked automatically only when the name score is high, the best NAAC record is clearly ahead of the second best, and the place does not contradict
   (the website college's district must appear in the NAAC address, or the address names no known district at all);
 - 'doubtful' when plausible but not certain: waits for the owner in data/manual/naac_confirmations.csv (college_code, aishe_id, decision yes/no);
 - 'no_record' when no plausible NAAC record exists (the college is not on the list, which is NOT a "not accredited" verdict).
Output: data/normalized/naac_link/naac_college_match.csv (+ report). Two colleges are never linked to the same NAAC record without the owner's yes.
"""
import collections, csv, json, os, sys
from ingestion import nba_match as M
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
N = os.path.join(ROOT, "data", "normalized")
MANUAL = os.path.join(ROOT, "data", "manual", "naac_confirmations.csv")
OUT_COLS = ["college_code", "college_name", "district", "aishe_id", "naac_name", "naac_grade", "naac_cgpa", "declared_on", "status", "score", "second_best", "how"]


import re
ALIAS = [(re.compile(r"\baurangabad\b", re.I), "chhatrapati sambhajinagar"), (re.compile(r"\bosmanabad\b", re.I), "dharashiv"), (re.compile(r"\bahm[ae]dnagar\b", re.I), "ahilyanagar")]
FIELD = {"pharmacy", "pharmaceutical", "education", "arts", "commerce", "science", "law", "architecture", "management", "social", "nursing", "agriculture", "polytechnic", "medical", "ayurved", "homoeopathic", "physical", "teachers", "computer", "mba", "bca", "mca", "bba", "hospital", "hotel", "design", "fine"}
TECH = {"engineering", "technology", "technical", "technological"}
BAND_MIN, BAND_MARGIN, RAW_LEAD = 0.65, 0.20, 0.10   # same lower band as for NBA (needs the place confirmed) and the best record must also lead on the plain name score


def fix(name):
    for rx, new in ALIAS: name = rx.sub(new, name)
    return name


def name_score(naac_name, college_name, idf):
    a, b = fix(naac_name), fix(college_name); sc = M.score(a, b, idf)
    A, B = set(M.toks(a)), set(M.toks(b))
    if B & TECH and (A & FIELD) - B - {"computer"} and not (A & TECH): sc *= 0.5      # an engineering college is not the same as a pharmacy / education / arts college with a similar trust name
    return sc


def place_vs_address(college, n):
    """ok: the college's district (or its old/new spelling) is in the NAAC address; conflict: the address' district part is another known district; else unknown."""
    d = M.PLACE.get(college["district"].strip().lower(), college["district"].strip().lower())
    if d in ("", "not available"): return "unknown"
    fam = lambda x: "mumbai" if x in ("mumbai", "mumbai city", "mumbai suburban", "mumbai-city") else x           # Mumbai, Mumbai City and Mumbai Suburban are one place for addresses
    hay = " ".join(M.norm(n["address"]) + M.norm(n["name"]))
    if fam(d) == "mumbai" and "mumbai" in hay.split() and "navi" not in hay.split(): return "ok"
    dt = [t for t in M.norm(d) if len(t) >= 3]
    if dt and all(any(M.similar(t, h) for h in hay.split()) for t in dt): return "ok"
    hint = M.PLACE.get(n["district_hint"].strip().lower(), n["district_hint"].strip().lower())
    return "conflict" if hint in M.KNOWN_PLACES and fam(hint) != fam(d) else "unknown"


def load_confirmations(path=MANUAL):
    conf = {}
    if os.path.exists(path):
        for r in M.load(path): conf[r["college_code"].strip()] = (r["decision"].strip().lower(), r.get("aishe_id", "").strip())
    return conf


def build(base=N, manual=MANUAL, outdir=None):
    outdir = outdir or os.path.join(base, "naac_link")
    colleges = M.load(os.path.join(base, "tables", "colleges.csv")); naac = M.load(os.path.join(base, "naac", "naac_institutions.csv"))
    idf = M.make_idf(colleges + [dict(college_name=n["name"]) for n in naac]); by_aishe = {n["aishe_id"]: n for n in naac}; conf = load_confirmations(manual)
    rows, rep, seen_conf = [], dict(ok=False, colleges=len(colleges), naac_rows=len(naac), counts={}, problems=[], doubtful=[], unused_confirmations=[], naac_used_twice={}), set()
    pre = collections.defaultdict(set)                        # speed: a NAAC record is only scored against a college when they share a rare word (or the first 4 letters of one: spelling variants)
    for i, n in enumerate(naac):
        for t in M.toks(n["name"]):
            if len(t) >= 4: pre[t[:4]].add(i)
    for c in colleges:
        rare = [t for t in M.toks(c["college_name"]) if len(t) >= 4 and idf(t) > 3.0]
        cand = sorted(set().union(*[pre.get(t[:4], set()) for t in rare])) if rare else range(len(naac))
        ranked = sorted(((name_score(naac[i]["name"], c["college_name"], idf), place_vs_address(c, naac[i]), naac[i]) for i in cand), key=lambda x: -M.adj(x[0], x[1]))[:3]
        if len(ranked) < 2: ranked += [(0.0, "unknown", dict(aishe_id="", name="", grade="", cgpa="", declared_on="", district_hint=""))] * (2 - len(ranked))
        (s1, ps, n1), (s2, p2, n2) = ranked[0], ranked[1]
        row = dict(college_code=c["college_code"], college_name=c["college_name"], district=c["district"], aishe_id="", naac_name="", naac_grade="", naac_cgpa="", declared_on="", status="", score="%.2f" % s1, second_best="%.2f" % s2, how="")
        def link(n, how): row.update(aishe_id=n["aishe_id"], naac_name=n["name"], naac_grade=n["grade"], naac_cgpa=n["cgpa"], declared_on=n["declared_on"], status="linked", how=how)
        if c["college_code"] in conf:
            seen_conf.add(c["college_code"]); d, aid = conf[c["college_code"]]
            if d == "yes" and aid in by_aishe: link(by_aishe[aid], "owner confirmed")
            elif d == "no": row.update(status="no_record", how="owner said: no NAAC record for this college")
            else: rep["problems"].append("bad confirmation for %s" % c["college_code"]); row.update(status="doubtful", how="confirmation not understood")
        elif s1 >= M.AUTO_MIN and M.adj(s1, ps) - M.adj(s2, p2) >= M.AUTO_MARGIN and s1 - s2 >= 0.05 and ps != "conflict": link(n1, "automatic: name score %.2f, place %s" % (s1, ps))
        elif BAND_MIN <= s1 < M.AUTO_MIN and M.adj(s1, ps) - M.adj(s2, p2) >= BAND_MARGIN and s1 - s2 >= RAW_LEAD and ps == "ok": link(n1, "automatic (place confirmed): name score %.2f, clear lead" % s1)
        elif s1 >= M.DOUBT_MIN:
            row.update(status="doubtful", how="candidate %s (%.2f), place %s" % (n1["aishe_id"], s1, ps))
            rep["doubtful"].append([c["college_code"], c["college_name"][:70], c["district"], [[n["aishe_id"], n["name"][:70], n["grade"], n["district_hint"], round(s, 2)] for s, _p, n in ranked]])
        else: row.update(status="no_record", how="no plausible NAAC record (best score %.2f)" % s1)
        rows.append(row)
    rep["unused_confirmations"] = sorted(set(conf) - seen_conf)
    rep["counts"] = {k: sum(1 for r in rows if r["status"] == k) for k in ("linked", "doubtful", "no_record")}
    use = {}
    for r in rows:
        if r["status"] == "linked": use.setdefault(r["aishe_id"], []).append(r["college_code"])
    rep["naac_used_twice"] = {k: v for k, v in use.items() if len(v) > 1}
    for k, v in rep["naac_used_twice"].items():            # sister colleges of one trust: an automatic link is not safe for any of them, the owner decides
        for r in rows:
            if r["college_code"] in v and r["how"].startswith("automatic"):
                r.update(status="doubtful", how="two colleges claim the same NAAC record %s (%s)" % (k, ", ".join(v)))
                rep["doubtful"].append([r["college_code"], r["college_name"][:70], r["district"], [[r["aishe_id"], r["naac_name"][:70], r["naac_grade"], "", float(r["score"])]]]); r.update(aishe_id="", naac_name="", naac_grade="", naac_cgpa="", declared_on="")
    rep["counts"] = {k: sum(1 for r in rows if r["status"] == k) for k in ("linked", "doubtful", "no_record")}
    rep["ok"] = not rep["problems"]
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "naac_college_match.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=OUT_COLS, lineterminator="\r\n"); w.writeheader(); w.writerows(rows)
    with open(os.path.join(outdir, "naac_college_match_report.json"), "w", encoding="utf-8") as fh: json.dump(rep, fh, indent=1, ensure_ascii=False)
    return rep


def main():
    rep = build(); print("colleges:", rep["colleges"], "counts:", rep["counts"], "ok:", rep["ok"])
    for p in rep["problems"][:20]: print("FAIL:", p)
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
