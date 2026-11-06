"""Writes a short, readable summary of the Stage 9 reading reports (shown on the GitHub run page)."""
import json, os, sys


def _load(path):
    try:
        with open(path, encoding="utf-8") as fh: return json.load(fh)
    except (OSError, ValueError): return None


def markdown_summary(norm_dir):
    L, ok = ["## Reading the archived cutoff lists"], True
    for title, folder, report, unit, count_key in (("State (Maharashtra) lists", "cutoffs_mh", "parse_report_mh.json", "cells", "cells"), ("All India lists", "cutoffs_ai", "parse_report_ai.json", "rows", "rows")):
        r = _load(os.path.join(norm_dir, folder, report))
        if not r: L.append("- %s: report missing" % title); ok = False; continue
        L.append("\n**%s** - %s" % (title, "all complete" if r.get("all_ok") else "PROBLEMS FOUND")); ok = ok and bool(r.get("all_ok"))
        L.append("| List | %s read | Complete | Problems |" % unit.capitalize()); L.append("|---|---|---|---|")
        for e in r.get("files", []):
            L.append("| %s round %s | %s | %s | %s |" % (e["year_label"], e["cap_round"], format(e.get(count_key, 0), ","), "yes" if e.get("complete") else "NO", e.get("problem_count", e.get("error", "?"))))
    m = _load(os.path.join(norm_dir, "master", "master_report.json"))
    if m:
        s = m["summary"]; ok = ok and m.get("problem_count", 1) == 0
        L.append("\n**Master tables** - %d colleges, %d courses, %d seat codes, %d home-university values; %d problem(s)." % (s["colleges"], s["courses"], s["seat_codes"], s["home_universities"], m.get("problem_count", 0)))
        for p in m.get("problems", [])[:10]: L.append("- PROBLEM: " + p)
    else: L.append("\n- Master tables: report missing"); ok = False
    L.append("\nOverall: **%s**" % ("everything complete, no problems" if ok else "NOT OK - the previous data was kept"))
    return "\n".join(L), ok


def main(argv=None):
    d = (argv or sys.argv[1:] or ["data/normalized"])[0]; md, ok = markdown_summary(d); print(md)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s: open(s, "a", encoding="utf-8").write(md + "\n")
    return 0 if ok else 4


if __name__ == "__main__":
    sys.exit(main())
