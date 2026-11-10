"""Stage 10c-1: the automatic data plan. Turns the automatic admission-year decision (ingestion/admission_year.py, stored in
data/raw/discovery/latest.json) into a list of exactly which cutoff lists the website needs - nothing is hard-coded to 2026-27.
  - current year = the newest year with reachable published cutoff documents (decided from evidence, not the calendar)
  - rounds done  = the cutoff rounds published for it; next round = the one after the latest (or none after Round IV)
  - history      = the three admission years before it, each with its LAST published round
  - students may see every published round of the current year (I..latest); the newest one is the main figure.
Run: python -m ingestion.plan   -> writes data/normalized/data_plan.json"""
import json, os, sys
from ingestion.admission_year import ROUND_ORDER
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DISCOVERY = os.path.join(ROOT, "data", "raw", "discovery", "latest.json")
OUT = os.path.join(ROOT, "data", "normalized", "data_plan.json")


def make_plan(decision):
    cur = decision.get("current_label")
    if not cur or decision.get("status") in (None, "unknown"):
        return {"ok": False, "problem": "admission year not established; keep the last validated data", "required_lists": [], "years": []}
    done = [r for r in ROUND_ORDER if r in (decision.get("current_cutoff_rounds") or [])]
    latest = done[-1] if done else None
    if latest is None:
        return {"ok": False, "problem": "no cutoff round published for " + cur, "required_lists": [], "years": []}
    nxt = ROUND_ORDER[ROUND_ORDER.index(latest) + 1] if latest != ROUND_ORDER[-1] else None
    history = []
    for p in decision.get("previous", []):
        rs = [r for r in ROUND_ORDER if r in (p.get("cutoff_rounds") or [])]
        history.append({"label": p["label"], "rounds_published": rs, "round_used": rs[-1] if rs else None})
    required = [{"year": cur, "round": r, "role": "current"} for r in done]
    required += [{"year": h["label"], "round": h["round_used"], "role": "history"} for h in history if h["round_used"]]
    return {"ok": True, "current_year": cur, "year_status": decision.get("status"), "rounds_done": done, "latest_round": latest,
            "next_round_expected": nxt, "cycle_note": ("all four CAP rounds are published; later supplementary lists are not used" if nxt is None
            else "round %s is the next expected; it is not published yet" % nxt),
            "history": history, "history_years_without_cutoffs": [h["label"] for h in history if not h["round_used"]],
            "required_lists": required, "decision_warnings": decision.get("warnings", [])}


def main():
    d = json.load(open(DISCOVERY))["admission_year"]
    plan = make_plan(d)
    with open(OUT, "w") as f: json.dump(plan, f, indent=1)
    print(json.dumps({k: plan.get(k) for k in ("ok", "current_year", "rounds_done", "latest_round", "next_round_expected", "cycle_note")}, indent=1))
    return 0 if plan["ok"] else 1

if __name__ == "__main__": sys.exit(main())
