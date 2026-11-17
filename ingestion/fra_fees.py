"""Stage 12a-2: read the FRA-approved engineering fees (official source: Fees Regulating Authority, Maharashtra).

What the probe showed (data/raw/fees-probe): the public page loads its data with two plain GET calls (no login, no CAPTCHA, robots.txt allows):
  admin/reports/ajax/get_sub_type_ajax.php?val1=HT                                        -> the <option> list of sub types
  admin/reports/ajax/get_report_ajax.php?sub_type=<ENGG..>&district=all&institute=&type=HT -> the fee table
Table columns (seen by the owner): Sr. No., Inst ID, Inst Name, District, Stream, Status, Date of Meeting, Tuition Fee, Development Fee, Total Fee.
Rules: nothing is invented or corrected; a missing number stays empty (never 0); the printed total is kept even if it is not tuition + development
(flagged); anything unrecognised or incomplete makes the run FAIL and the previous data is kept. FRA code EN#### = CET Cell code 0#### (matched by name in 12a-3).
"""
import csv, datetime, json, os, re, sys
from urllib.parse import urlencode
from ingestion.http_client import PoliteFetcher
from ingestion.fra_probe import parse as parse_html

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
# The FRA portal keeps one address per academic year (the folder name changes every year). A year that is not listed is NOT read (reported).
FRA_SITES = {"2026-27": "https://ay26-27.mahafraportal.org/ssi_prp_25/"}
REQUIRED = ["sr. no.", "inst id", "inst name", "district", "stream", "status", "date of meeting", "tuition fee", "development fee", "total fee"]
OUT_COLS = ["inst_id", "cet_institute_code", "inst_name", "district", "stream", "status", "meeting_date", "tuition_fee", "development_fee", "total_fee", "total_equals_parts", "source_url", "retrieved_date"]
KNOWN_STATUS = {"Approved", "No Upward Revision", "Interim Order of High Court"}      # the last one was seen on the live list (2 institutes)


def norm(s): return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


def sub_type_options(fragment):
    return [(m.group(1).strip(), norm(re.sub(r"<[^>]+>", "", m.group(2)))) for m in re.finditer(r"<option[^>]*?value\s*=\s*['\"]?([^'\">]*)['\"]?[^>]*>(.*?)(?=</option>|<option|$)", fragment, re.I | re.S)]


def money(s):
    s = norm(s).replace(",", "").replace("\u20b9", "").replace("Rs.", "").strip()
    if s == "" or s in ("-", "--", "NA", "N/A"): return None, False
    return (int(s), False) if re.fullmatch(r"\d+", s) else (None, True)


def iso(s):
    s = norm(s)
    if not s: return "", False
    try: return datetime.datetime.strptime(s, "%d-%m-%Y").date().isoformat(), False
    except ValueError: return "", True


def parse_report(html, source_url="", retrieved=""):
    """-> dict(rows, issues, skipped). Finds the table whose header has the required columns; rows are checked one by one."""
    pg = parse_html(html); issues, skipped, rows = [], [], []
    best = None
    for t in pg.tables:
        for i, r in enumerate(t):
            h = [norm(c).lower() for c in r]
            if "inst id" in h and "total fee" in h: best = (t, i, h); break
        if best: break
    if not best: return dict(rows=[], issues=["no table with the columns 'Inst ID' and 'Total Fee' in the answer"], skipped=[])
    t, hi, h = best
    miss = [c for c in REQUIRED if c not in h]
    if miss: return dict(rows=[], issues=["columns missing in the table header: %s (found: %s)" % (miss, h)], skipped=[])
    ix = {c: h.index(c) for c in REQUIRED}
    for r in t[hi + 1:]:
        if len(r) != len(h):
            if r and any(norm(c) for c in r): skipped.append(" | ".join(norm(c) for c in r)[:120])
            continue
        g = lambda c: norm(r[ix[c]])
        row = dict(sr=g("sr. no."), inst_id=g("inst id"), inst_name=g("inst name"), district=g("district"), stream=g("stream"), status=g("status"))
        row["meeting_date"], bad = iso(g("date of meeting"))
        if bad: issues.append("%s: unreadable meeting date %r" % (row["inst_id"], g("date of meeting")))
        for k, c in (("tuition_fee", "tuition fee"), ("development_fee", "development fee"), ("total_fee", "total fee")):
            row[k], bad = money(g(c))
            if bad: issues.append("%s: unreadable %s %r" % (row["inst_id"], k, g(c)))
        rows.append(row)
    return dict(rows=rows, issues=issues, skipped=skipped)


def check_rows(rows):
    """Completeness and sanity checks. Returns (problems, warnings)."""
    problems, warnings = [], []
    if not rows: return ["the report has no rows"], warnings
    srs = [r["sr"] for r in rows]
    if not all(s.isdigit() for s in srs) or [int(s) for s in srs] != list(range(1, len(rows) + 1)): problems.append("Sr. No. is not 1..%d without gaps (first values: %s)" % (len(rows), srs[:8]))
    seen = {}
    for r in rows:
        if not re.fullmatch(r"[A-Z]{2}\d{4,5}", r["inst_id"]): problems.append("unexpected Inst ID %r" % r["inst_id"])
        elif not r["inst_id"].startswith("EN"): warnings.append("%s: not an EN (engineering institute) code, kept but not linked to a CET Cell institute code" % r["inst_id"])
        if r["stream"] != "ENGG": problems.append("%s: stream %r is not ENGG" % (r["inst_id"], r["stream"]))
        if r["status"] not in KNOWN_STATUS: warnings.append("%s: new status %r" % (r["inst_id"], r["status"]))
        if r["total_fee"] is None: warnings.append("%s: no total fee printed" % r["inst_id"])
        if r["inst_id"] in seen and seen[r["inst_id"]] != (r["tuition_fee"], r["development_fee"], r["total_fee"], r["status"]): problems.append("%s appears twice with different figures" % r["inst_id"])
        seen[r["inst_id"]] = (r["tuition_fee"], r["development_fee"], r["total_fee"], r["status"])
    return problems, warnings


def read(site, year, fetcher, out_dir, raw_dir, today=None):
    today = today or datetime.date.today().isoformat()
    rep = dict(year=year, site=site, ok=False, problems=[], warnings=[], rows=0, requests=0, how="", statuses={}, skipped_rows=[], sub_type_options=[])
    os.makedirs(out_dir, exist_ok=True); os.makedirs(raw_dir, exist_ok=True)
    st = fetcher.fetch(site + "admin/reports/ajax/get_sub_type_ajax.php?" + urlencode({"val1": "HT"}))
    if st.blocked or not st.ok: rep["problems"].append("sub type list not readable (%s %s)" % (st.blocked, st.status)); return _save(rep, out_dir)
    opts = sub_type_options(st.text); rep["sub_type_options"] = opts
    # exact code ENGG ("Bachelor of Engineering/Bachelor of Technology"). Seen on the live list: ENGGWP (Working Professional), ME, ARCH ... are NOT this one.
    eng = [o for o in opts if o[0].upper() == "ENGG"]
    if len(eng) != 1 or not eng[0][1].upper().startswith("ENGG"): rep["problems"].append("expected exactly one sub type with code 'ENGG', found %s of %s" % (len(eng), opts)); return _save(rep, out_dir)
    sub = eng[0][0]
    all_rows, url_used = [], []
    def get(district):
        u = site + "admin/reports/ajax/get_report_ajax.php?" + urlencode({"sub_type": sub, "district": district, "institute": "", "type": "HT"})
        r = fetcher.fetch(u)
        if r.blocked or not r.ok: rep["problems"].append("report for %r not readable (%s %s)" % (district, r.blocked, r.status)); return None
        if re.search(r"captcha|type=.?password", r.text, re.I): rep["problems"].append("a login or CAPTCHA appeared: stopped"); return None
        return r
    r = get("all")
    if r is None: return _save(rep, out_dir)
    open(os.path.join(raw_dir, "%s_engg_all.html" % year), "w", encoding="utf-8").write(r.text[:2_000_000])
    pr = parse_report(r.text); rep["how"] = "one request (All District)"
    if pr["rows"]: all_rows = pr["rows"]; rep["problems"] += pr["issues"]; rep["skipped_rows"] = pr["skipped"][:20]
    elif any("columns missing" in i for i in pr["issues"]):
        rep["problems"] += pr["issues"]; return _save(rep, out_dir)       # a table exists but its columns are not the expected ones: stop and report
    else:
        # fall back: district by district (the district names come from the page itself)
        pg = fetcher.fetch(site + "outer.php?q=fee_search_report")
        ds = [o["text"].strip() for fl in parse_html(pg.text).forms for f in fl["fields"] if f["kind"] == "select" and f["name"] == "district" for o in f["options"] if o["value"].strip() not in ("", "all")] if pg.ok else []
        rep["how"] = "district by district (%d districts); All District gave: %s" % (len(ds), "; ".join(pr["issues"])[:200])
        seen = set()
        for d in ds:
            rd = get(d)
            if rd is None: break
            p = parse_report(rd.text)
            if p["issues"] and not p["rows"] and "no table" in p["issues"][0]: continue          # a district without engineering colleges
            rep["problems"] += p["issues"]
            for x in p["rows"]:
                k = (x["inst_id"],)
                if k in seen: continue
                seen.add(k); x["sr"] = str(len(all_rows) + 1); all_rows.append(x)
    rep["requests"] = fetcher.count
    p, w = check_rows(all_rows)
    if not all_rows and pr["issues"]: p = ["no fee table found: " + "; ".join(pr["issues"])[:300]] + p
    rep["problems"] += p; rep["warnings"] += w
    rep["rows"] = len(all_rows)
    for x in all_rows: rep["statuses"][x["status"]] = rep["statuses"].get(x["status"], 0) + 1
    if rep["problems"]: return _save(rep, out_dir)
    out = os.path.join(out_dir, "fra_fees_%s_engg.csv" % year)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w_ = csv.DictWriter(f, fieldnames=OUT_COLS, lineterminator="\r\n"); w_.writeheader()
        for x in all_rows:
            eq = "" if None in (x["tuition_fee"], x["development_fee"], x["total_fee"]) else ("TRUE" if x["tuition_fee"] + x["development_fee"] == x["total_fee"] else "FALSE")
            if eq == "FALSE": rep["warnings"].append("%s: printed total %s != tuition %s + development %s" % (x["inst_id"], x["total_fee"], x["tuition_fee"], x["development_fee"]))
            w_.writerow(dict(inst_id=x["inst_id"], cet_institute_code=x["inst_id"][2:].zfill(5) if x["inst_id"].startswith("EN") else "", inst_name=x["inst_name"], district=x["district"], stream=x["stream"], status=x["status"],
                             meeting_date=x["meeting_date"], tuition_fee="" if x["tuition_fee"] is None else x["tuition_fee"], development_fee="" if x["development_fee"] is None else x["development_fee"],
                             total_fee="" if x["total_fee"] is None else x["total_fee"], total_equals_parts=eq, source_url=site + "outer.php?q=fee_search_report", retrieved_date=today))
    rep["ok"] = True
    return _save(rep, out_dir)


def _save(rep, out_dir):
    with open(os.path.join(out_dir, "fra_fees_report.json"), "w", encoding="utf-8") as fh: json.dump(rep, fh, indent=1, ensure_ascii=False)
    return rep


def main(argv=None):
    plan = json.load(open(os.path.join(ROOT, "data", "normalized", "data_plan.json"), encoding="utf-8"))
    year = plan["current_year"]
    if year not in FRA_SITES:
        print("FAIL: no known FRA portal address for %s (add it to FRA_SITES in ingestion/fra_fees.py)" % year); return 1
    out_dir, raw_dir = os.path.join(ROOT, "build", "normalized", "fees"), os.path.join(ROOT, "data", "raw", "fees")
    os.makedirs(os.path.join(ROOT, "data", "normalized", "fees"), exist_ok=True)     # an (empty) folder so that an older 'git add' of it cannot fail
    try:
        rep = read(FRA_SITES[year], year, PoliteFetcher(min_delay=2.0, max_requests=60), out_dir, raw_dir)
    except Exception as e:                                       # never end without a report that can be read afterwards
        import traceback
        os.makedirs(raw_dir, exist_ok=True)
        with open(os.path.join(raw_dir, "fra_fees_report.json"), "w", encoding="utf-8") as fh: json.dump(dict(ok=False, year=year, problems=["unexpected error: %s: %s" % (type(e).__name__, e)], trace=traceback.format_exc()[-3000:]), fh, indent=1)
        print("FAIL: unexpected error: %s: %s" % (type(e).__name__, e)); return 1
    import shutil
    shutil.copy(os.path.join(out_dir, "fra_fees_report.json"), os.path.join(raw_dir, "fra_fees_report.json"))   # kept even when the run fails
    print("year %s | rows %d | requests %s | %s" % (year, rep["rows"], rep["requests"], rep["how"]))
    print("statuses:", rep["statuses"]); print("warnings:", len(rep["warnings"]), rep["warnings"][:5]); print("skipped rows:", rep["skipped_rows"][:5])
    for p in rep["problems"][:20]: print("FAIL:", p)
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
