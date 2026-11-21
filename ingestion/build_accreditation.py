"""Stage 12b-3b / 12c-4: matched NBA programs (data/normalized/nba_link/nba_program_match.csv) -> tables/accreditation.csv in the website's `accreditation` shape.

One row per (website branch choice_code, NBA validity). NBA applies per programme, so an NBA programme is attached to EVERY choice code of the matched branch at that
college (for example the regular and the second-year code of one branch). body=NBA, scope=program, grade blank. status is 'accredited' (the website itself decides
valid / expired / validity unknown from valid_to and today's date) or 'unknown' for a row the NBA list does not mark accredited.
Also writes tables/accreditation_sources.csv (one line per NBA Excel file: its SHA-256 and download date) so the packaging step can add the source document.
Stage 12c-4: NAAC rows are added too, one per website college linked to a NAAC record (data/normalized/naac_link/naac_college_match.csv): body=NAAC, scope=institution, no choice_code,
grade and cgpa as NAAC printed them, valid_from = the date of declaration, valid_to EMPTY (the NAAC list has no end date and none is computed), listed_as_on = the date of the NAAC list.
Nothing is invented: rows with no matched branch / no NAAC record are not written.
"""
import csv, datetime, json, os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
N = os.path.join(ROOT, "data", "normalized")
COLS = "accreditation_id,college_code,choice_code,body,scope,status,grade,cgpa,valid_from,valid_to,listed_as_on,source_doc_id,retrieved_date,validation_status,is_synthetic".split(",")
SRC_COLS = ["source_doc_id", "body", "filename", "sha256", "retrieved_date", "published_date", "source_name", "source_url"]
NBA_SRC = dict(body="NBA", source_name="National Board of Accreditation (NBA), India - accredited engineering programmes, Maharashtra", source_url="https://www.nbaind.org/", published_date="")


def load(p):
    with open(p, newline="", encoding="utf-8") as f: return list(csv.DictReader(f))


def doc_id(sha): return "DOC-" + sha[:16]


def build(base=N, outdir=None, today=None):
    outdir = outdir or os.path.join(base, "tables"); today = today or datetime.date.today().isoformat()
    match = [r for r in load(os.path.join(base, "nba_link", "nba_program_match.csv")) if r["status"] == "matched"]
    branches = {b["choice_code"]: b for b in load(os.path.join(base, "tables", "branches.csv"))}
    seen, recs, srcs, problems = set(), [], {}, []
    for r in match:
        sha = r["source_sha256"]
        if not sha: problems.append("row without source file: %s / %s" % (r["nba_institution"][:40], r["program"])); continue
        srcs[sha] = dict(NBA_SRC, source_doc_id=doc_id(sha), filename=r["source_file"], sha256=sha, retrieved_date=r["downloaded_on"])
        for cc in [c for c in r["choice_codes"].split(";") if c]:
            b = branches.get(cc)
            if b is None: problems.append("choice code %s is not a website branch" % cc); continue
            if b["college_code"] != r["college_code"]: problems.append("choice code %s belongs to college %s, not %s" % (cc, b["college_code"], r["college_code"])); continue
            status = "accredited" if r["nba_status"] == "accredited" else "unknown"
            key = (cc, r["valid_from"], r["valid_to"], status, sha)
            if key in seen: continue
            seen.add(key)
            recs.append(dict(college_code=r["college_code"], choice_code=cc, body="NBA", scope="program", status=status, grade="", cgpa="", listed_as_on="", valid_from=r["valid_from"], valid_to=r["valid_to"],
                             source_doc_id=doc_id(sha), retrieved_date=r["downloaded_on"], validation_status="validated", is_synthetic="FALSE"))
    naac_n = 0; nm = os.path.join(base, "naac_link", "naac_college_match.csv")
    if os.path.exists(nm):
        ni = {r["aishe_id"]: r for r in load(os.path.join(base, "naac", "naac_institutions.csv"))}; colleges = {c["college_code"] for c in load(os.path.join(base, "tables", "colleges.csv"))}
        for r in load(nm):
            if r["status"] != "linked": continue
            n = ni.get(r["aishe_id"])
            if n is None: problems.append("NAAC record %s of college %s is not in naac_institutions.csv" % (r["aishe_id"], r["college_code"])); continue
            if r["college_code"] not in colleges: problems.append("college %s is not a website college" % r["college_code"]); continue
            sha = n["source_sha256"]; srcs[sha] = dict(source_doc_id=doc_id(sha), body="NAAC", filename=n["source_file"], sha256=sha, retrieved_date="", published_date=n["list_as_on"],
                                                         source_name="National Assessment and Accreditation Council (NAAC), India - institutions with valid accreditation (list as on %s)" % n["list_as_on"], source_url="https://www.naac.gov.in/")
            recs.append(dict(college_code=r["college_code"], choice_code="", body="NAAC", scope="institution", status="accredited", grade=n["grade"], cgpa=n["cgpa"], valid_from=n["declared_on"], valid_to="",
                             listed_as_on=n["list_as_on"], source_doc_id=doc_id(sha), retrieved_date="", validation_status="validated", is_synthetic="FALSE")); naac_n += 1
    recs.sort(key=lambda x: (x["body"] != "NBA", x["college_code"], x["choice_code"], x["valid_to"] or "9999", x["valid_from"]))
    counter = {}
    for x in recs:
        key = x["choice_code"] or x["college_code"]; counter[key] = counter.get(key, 0) + 1; x["accreditation_id"] = "%s-%s-%d" % (x["body"], key, counter[key])
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "accreditation.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, lineterminator="\r\n"); w.writeheader(); w.writerows({k: x.get(k, "") for k in COLS} for x in recs)
    with open(os.path.join(outdir, "accreditation_sources.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SRC_COLS, lineterminator="\r\n"); w.writeheader(); w.writerows(sorted(srcs.values(), key=lambda x: (x["body"], x["filename"])))
    expired = sum(1 for x in recs if x["body"] == "NBA" and x["status"] == "accredited" and x["valid_to"] and x["valid_to"] < today)
    rep = dict(ok=not problems, rows=len(recs), nba_rows=len(recs) - naac_n, naac_rows=naac_n, branches=len({x["choice_code"] for x in recs if x["choice_code"]}), colleges=len({x["college_code"] for x in recs}), sources=len(srcs),
               no_end_date=sum(1 for x in recs if x["body"] == "NBA" and x["status"] == "accredited" and not x["valid_to"]), expired_on_build_date=expired, build_date=today, problems=problems[:20])
    with open(os.path.join(outdir, "accreditation_build_report.json"), "w", encoding="utf-8") as fh: json.dump(rep, fh, indent=1)
    return rep


def main():
    rep = build(); print(json.dumps(rep)); return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
