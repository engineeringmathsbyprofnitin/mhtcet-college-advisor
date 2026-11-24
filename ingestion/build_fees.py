"""Stage 12a-3: link the FRA-approved fees (data/normalized/fees) to the website's colleges and write tables/fees.csv.

A fee is published for a college only when (1) the FRA code EN#### equals the CET Cell college code AND (2) the two names are similar
(fuzzy check) - or the owner confirmed the pair in data/manual/fee_name_confirmations.csv. Never linked/published (listed in the report):
codes that are not EN, colleges that are not on the website, a code match with a different-looking name (until the owner confirms it),
status 'Interim Order of High Court' (fee not final), and numbers that are 0/contradictory (a printed 0 is not a fee; blanks never become zero).
Fee rows use the website schema: fee_type 'tuition' (tuition fee) and 'total' (tuition + development fee as printed), one per college, all engineering
branches of the institute, first year, academic year of the FRA list.
"""
import csv, difflib, json, os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
N = os.path.join(ROOT, "data", "normalized")
MANUAL = os.path.join(ROOT, "data", "manual", "fee_name_confirmations.csv")
DOC_ID = "DOC-FRA-%s-ENGG"
COLS = ["fee_id", "college_code", "choice_code", "academic_year", "fee_type", "annual_fee_inr", "fee_scope", "source_doc_id", "retrieved_date", "validation_status", "is_synthetic"]
SCOPE = "FRA approved, all engineering branches of the institute, first year"
STOP = set("the and of for college engineering technology institute society education science sciences trust shikshan prasarak mandal sanstha santha pratishthan pratisthan charitable foundation shri smt dr sanchalit ltd campus faculty management sansthas vikas gramin bahu uddeshiya school polytechnic technical academy pvt private maharashtra".split())


def toks(s): return [t for t in re.findall(r"[a-z]{3,}", re.sub(r"[\u2019']", "", (s or "").lower())) if t not in STOP]


def name_score(a, b):
    A, B = toks(a), toks(b)
    if not A or not B: return 0.0
    s, l = (A, B) if len(A) <= len(B) else (B, A)
    return sum(1 for t in s if max(difflib.SequenceMatcher(None, t, u).ratio() for u in l) >= 0.8) / len(s)


def load(path):
    with open(path, newline="", encoding="utf-8") as f: return list(csv.DictReader(f))


def build(base=N, plan=None, outdir=None, manual=MANUAL):
    plan = plan or json.load(open(os.path.join(base, "data_plan.json"), encoding="utf-8"))
    adm = plan.get("admission_year", plan["current_year"]); outdir = outdir or os.path.join(base, "tables"); os.makedirs(outdir, exist_ok=True)
    year = adm   # Stage 14b: the fee list of the admission year if it exists; otherwise the newest list of an earlier year, which the cards label with its own year
    for cand in (adm, plan["current_year"]):
        if os.path.exists(os.path.join(base, "fees", "fra_fees_%s_engg.csv" % cand)): year = cand; break
    rep = dict(ok=False, year=year, admission_year=adm, status="", published_colleges=0, rows=0, tiers={}, not_published={}, problems=[], notes=[])
    if year != adm: rep["notes"].append("no fee list for the admission year %s yet; the fee list of %s is shown and labelled with its own year" % (adm, year))
    src = os.path.join(base, "fees", "fra_fees_%s_engg.csv" % year); out = os.path.join(outdir, "fees.csv")
    if not os.path.exists(src):
        rep.update(ok=True, status="unavailable: no fee list for %s" % year)
        if os.path.exists(out): os.remove(out)
        return _save(outdir, rep)
    fees = load(src); colleges = {c["college_code"]: c for c in load(os.path.join(outdir, "colleges.csv"))}
    conf = {}
    if os.path.exists(manual):
        for r in load(manual): conf[(r["inst_id"], r["cet_institute_code"])] = r.get("confirmed_note", "")
    rows, tiers, np_ = [], {}, {}
    def tier(t, x=None, extra=""):
        tiers[t] = tiers.get(t, 0) + 1
        if x is not None and not t.startswith("published"): np_.setdefault(t, []).append([x["inst_id"], x["inst_name"][:60], extra])
    for x in fees:
        code = x["cet_institute_code"]
        if not code: tier("no_cet_code (not an EN code)", x); continue
        c = colleges.get(code)
        if c is None: tier("college_not_on_website", x); continue
        sc = name_score(x["inst_name"], c["college_name"])
        if sc < 0.5 and (x["inst_id"], code) not in conf: tier("name_unverified (code matches, names differ: owner must confirm)", x, "%s | score %.2f" % (c["college_name"][:60], sc)); continue
        if x["status"] == "Interim Order of High Court": tier("interim_order (fee not final)", x); continue
        tu = int(x["tuition_fee"]) if x["tuition_fee"] != "" else None; dv = int(x["development_fee"]) if x["development_fee"] != "" else None; to = int(x["total_fee"]) if x["total_fee"] != "" else None
        made = 0
        if tu and tu > 0: rows.append(("tuition", code, tu, x)); made += 1
        if to and to > 0 and not (tu in (None, 0) and dv in (None, 0) and False): rows.append(("total", code, to, x)); made += 1
        if x["total_equals_parts"] == "FALSE" or (tu == 0):
            rep["notes"].append("%s (%s): printed total %s vs tuition %s + development %s -> tuition not published%s" % (x["inst_id"], code, to, tu, dv, ", total published as printed" if to else ""))
            rows = [r for r in rows if not (r[0] == "tuition" and r[1] == code)]; made = sum(1 for r in rows if r[1] == code)
        if not made: tier("no_usable_number", x); continue
        tier("published" + (" (owner-confirmed name)" if sc < 0.5 else ""), x)
    rep["tiers"] = tiers; rep["not_published"] = {k: v for k, v in np_.items()}
    rep["published_colleges"] = len({r[1] for r in rows}); rep["rows"] = len(rows)
    codes = [(r[0], r[1]) for r in rows]
    if len(codes) != len(set(codes)): rep["problems"].append("two fee rows for the same college and type")
    if not rows: rep["problems"].append("no fee could be linked to a website college")
    if rep["problems"]: rep["status"] = "FAILED"; return _save(outdir, rep)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, lineterminator="\r\n"); w.writeheader()
        for t, code, v, x in rows:
            w.writerow(dict(fee_id="FEE-%s-%s-%s" % (code, year, t), college_code=code, choice_code="", academic_year=year, fee_type=t, annual_fee_inr=v, fee_scope=SCOPE,
                            source_doc_id=DOC_ID % year, retrieved_date=x["retrieved_date"], validation_status="validated", is_synthetic="FALSE"))
    rep.update(ok=True, status="ok: fees of %d colleges for %s" % (rep["published_colleges"], year))
    return _save(outdir, rep)


def _save(outdir, rep):
    with open(os.path.join(outdir, "fees_build_report.json"), "w", encoding="utf-8") as fh: json.dump(rep, fh, indent=1, ensure_ascii=False)
    return rep


def main():
    rep = build(); print(rep["status"]); print("tiers:", json.dumps(rep["tiers"], indent=1))
    for k, v in rep["not_published"].items(): print("not published -", k, ":", len(v), v[:4])
    for n in rep["notes"]: print("note:", n)
    for p in rep["problems"]: print("FAIL:", p)
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
