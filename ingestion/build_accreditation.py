"""Stage 12b-3b: matched NBA programs (data/normalized/nba_link/nba_program_match.csv) -> tables/accreditation.csv in the website's `accreditation` shape.

One row per (website branch choice_code, NBA validity). NBA applies per programme, so an NBA programme is attached to EVERY choice code of the matched branch at that
college (for example the regular and the second-year code of one branch). body=NBA, scope=program, grade blank. status is 'accredited' (the website itself decides
valid / expired / validity unknown from valid_to and today's date) or 'unknown' for a row the NBA list does not mark accredited.
Also writes tables/accreditation_sources.csv (one line per NBA Excel file: its SHA-256 and download date) so the packaging step can add the source document.
Nothing is invented: rows with no matched branch are not written.
"""
import csv, datetime, json, os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
N = os.path.join(ROOT, "data", "normalized")
COLS = "accreditation_id,college_code,choice_code,body,scope,status,grade,valid_from,valid_to,source_doc_id,retrieved_date,validation_status,is_synthetic".split(",")


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
        srcs[sha] = dict(source_doc_id=doc_id(sha), filename=r["source_file"], sha256=sha, retrieved_date=r["downloaded_on"])
        for cc in [c for c in r["choice_codes"].split(";") if c]:
            b = branches.get(cc)
            if b is None: problems.append("choice code %s is not a website branch" % cc); continue
            if b["college_code"] != r["college_code"]: problems.append("choice code %s belongs to college %s, not %s" % (cc, b["college_code"], r["college_code"])); continue
            status = "accredited" if r["nba_status"] == "accredited" else "unknown"
            key = (cc, r["valid_from"], r["valid_to"], status, sha)
            if key in seen: continue
            seen.add(key)
            recs.append(dict(college_code=r["college_code"], choice_code=cc, body="NBA", scope="program", status=status, grade="", valid_from=r["valid_from"], valid_to=r["valid_to"],
                             source_doc_id=doc_id(sha), retrieved_date=r["downloaded_on"], validation_status="validated", is_synthetic="FALSE"))
    recs.sort(key=lambda x: (x["choice_code"], x["valid_to"] or "9999", x["valid_from"]))
    counter = {}
    for x in recs:
        counter[x["choice_code"]] = counter.get(x["choice_code"], 0) + 1; x["accreditation_id"] = "NBA-%s-%d" % (x["choice_code"], counter[x["choice_code"]])
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "accreditation.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, lineterminator="\r\n"); w.writeheader(); w.writerows({k: x.get(k, "") for k in COLS} for x in recs)
    with open(os.path.join(outdir, "accreditation_sources.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["source_doc_id", "filename", "sha256", "retrieved_date"], lineterminator="\r\n"); w.writeheader(); w.writerows(sorted(srcs.values(), key=lambda x: x["filename"]))
    expired = sum(1 for x in recs if x["status"] == "accredited" and x["valid_to"] and x["valid_to"] < today)
    rep = dict(ok=not problems, rows=len(recs), branches=len({x["choice_code"] for x in recs}), colleges=len({x["college_code"] for x in recs}), sources=len(srcs),
               no_end_date=sum(1 for x in recs if x["status"] == "accredited" and not x["valid_to"]), expired_on_build_date=expired, build_date=today, problems=problems[:20])
    with open(os.path.join(outdir, "accreditation_build_report.json"), "w", encoding="utf-8") as fh: json.dump(rep, fh, indent=1)
    return rep


def main():
    rep = build(); print(json.dumps(rep)); return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
