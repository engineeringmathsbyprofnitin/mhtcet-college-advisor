"""Stage 11b: choose the vacancy documents from the archive manifest, read them, write small tables.

Rule (owner): vacancy comes ONLY from the CAP Round IV vacancy position ("seats open going into Round IV"), else Round III
("going into Round III"). One round per admission year, never mixed, never Round I/II, never the ACAP after-CAP list or
court-order lists, never the seat matrix. Seat intake (SI) is stored in its own column and is never vacancy.

Commands:
  python -m ingestion.read_vacancy needed --manifest M            -> lines  tag|asset|sha  of the files to download
  python -m ingestion.read_vacancy read --manifest M --files DIR --out DIR
Exit code 1 (and nothing written) unless every selected file was read completely with no problem.
"""
import argparse, csv, gzip, json, os, sys
from ingestion import archive, parse_vacancy

ACCEPT = ("IV", "III")          # in order of preference


def select(manifest):
    """-> ({year: document}, notes, blocked). Round IV is preferred, else Round III. If the preferred round's file exists in the
    manifest but is not stored yet, the year is BLOCKED (reported as a problem) - we never fall back to an older round then."""
    by_year, notes = {}, []
    for d in manifest["documents"].values():
        if d.get("doc_type") != "vacancy_position":
            if d.get("doc_type") == "vacancy_after_cap": notes.append("ignored (ACAP after-CAP list): %s" % d.get("file_name"))
            continue
        year, rnd = d.get("portal_year"), d.get("cap_round")
        if not year or not d.get("current_sha256"): notes.append("ignored (no year or no file yet): %s" % d.get("file_name")); continue
        if rnd not in ACCEPT: notes.append("ignored (round %s is never used): %s" % (rnd, d.get("file_name"))); continue
        by_year.setdefault(year, {})[rnd] = d
    chosen, blocked = {}, []
    for year, rounds in by_year.items():
        for r in ACCEPT:
            if r in rounds:
                d = rounds[r]; f = manifest["files"].get(d["current_sha256"])
                if f and f.get("uploaded"): chosen[year] = d
                else: blocked.append("%s: Round %s file %s is not archived yet; not falling back to an older round" % (year, r, d.get("file_name")))
                for r2, d2 in rounds.items():
                    if r2 != r: notes.append("%s: Round %s file not used because Round %s exists" % (year, r2, r))
                break
    return chosen, notes, blocked


def needed(manifest):
    chosen, _, _ = select(manifest)
    out = set()
    for d in chosen.values():
        f = manifest["files"][d["current_sha256"]]
        out.add((f["release_tag"], f["asset_name"], f["sha256"]))
    return sorted(out)


COLUMNS = ["portal_year", "cap_round", "source_file", "source_sha256", "institute_code", "institute_name", "institute_kind",
           "choice_code", "course_name", "intake_si", "ms_seats", "minority_seats", "all_india_seats", "institute_seats",
           "orphan_inst_seats", "orphan_non_inst_seats", "vacant_cap_seats", "state_level_total", "hu_total", "ohu_total",
           "pwd_total", "def_total", "pwd_common", "def_common", "ews_seats", "tfws_choice_code", "tfws_seats", "grid_json"]


def rows_for(doc, sha, blocks):
    for b in blocks:
        r = b["rows"]
        yield [doc["portal_year"], doc["cap_round"], doc["file_name"], sha, b["inst_code"], b["inst_name"], b["kind"],
               b["code"], b["course"], b["si"], b["ms"], b["minority"], b["all_india"], b["institute"], b["orphan_i"], b["orphan_n"],
               b["vacant"], r.get("State Level", {}).get("total", ""), r.get("HU", {}).get("total", ""), r.get("OHU", {}).get("total", ""),
               b["pwd"]["total"], b["defence"]["total"], b["pwd_common"], b["def_common"], b["ews"], b["tfws_code"], b["tfws"],
               json.dumps({k: v["cells"] for k, v in r.items()}, separators=(",", ":"))]


def read_all(manifest, files_dir, out_dir):
    chosen, notes, blocked = select(manifest)
    report = dict(files=[], notes=notes, problems=list(blocked), ok=False)
    if not chosen and not blocked:
        report["problems"].append("no vacancy file for Round IV or Round III is archived")
    os.makedirs(out_dir, exist_ok=True)
    for year in sorted(chosen):
        d = chosen[year]; f = manifest["files"][d["current_sha256"]]
        path = os.path.join(files_dir, f["asset_name"])
        if not os.path.exists(path):
            report["problems"].append("%s: file %s was not downloaded" % (year, f["asset_name"])); continue
        res = parse_vacancy.parse_pdf(path)
        info = dict(year=year, round=d["cap_round"], file=d["file_name"], sha256=f["sha256"], blocks=len(res["blocks"]), ghosts=res["ghosts"],
                    pages=list(res["pages"]), problems=res["problems"][:50], unrecognised=res["unrecognised"][:50],
                    institutes=len({b["inst_code"] for b in res["blocks"]}),
                    totals={k: sum(b[k] for b in res["blocks"]) for k in ("si", "ms", "minority", "all_india", "institute", "vacant")})
        report["files"].append(info)
        if res["problems"] or res["unrecognised"] or not res["blocks"]:
            report["problems"].append("%s Round %s: %d problems, %d unrecognised lines" % (year, d["cap_round"], len(res["problems"]), len(res["unrecognised"])))
            continue
        name = "%s_round-%s_vacancy.csv.gz" % (year, d["cap_round"])
        with gzip.open(os.path.join(out_dir, name), "wt", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh); w.writerow(COLUMNS)
            for row in rows_for(d, f["sha256"], res["blocks"]): w.writerow(row)
        info["written"] = name
    report["ok"] = not report["problems"]
    with open(os.path.join(out_dir, "vacancy_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("needed"); a.add_argument("--manifest", required=True)
    b = sub.add_parser("read"); b.add_argument("--manifest", required=True); b.add_argument("--files", required=True); b.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    m = archive.load_manifest(args.manifest)
    if args.cmd == "needed":
        for t in needed(m): print("|".join(t))
        return 0
    rep = read_all(m, args.files, args.out)
    for i in rep["files"]: print("Round %s %s: %d blocks, %d institutes, pages %s, vacant %d, written=%s" % (i["round"], i["year"], i["blocks"], i["institutes"], i["pages"], i["totals"]["vacant"], i.get("written")))
    for n in rep["notes"]: print("note:", n)
    for p in rep["problems"]: print("FAIL:", p)
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
