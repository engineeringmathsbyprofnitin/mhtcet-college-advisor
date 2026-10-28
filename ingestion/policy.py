"""Which of the discovered documents does the project actually need? (Stage 8)
The rules are kept in one place and each choice states WHY, so the owner can check them.

  * current admission year: cutoff lists of ALL available CAP rounds for Maharashtra State (MH) and All India (AI)
    (needed so the latest round can be used, with the strict fallback order IV > III > II > I)
  * current admission year: vacancy positions of CAP Round IV and Round III only (the strict vacancy rule; never I or II)
  * current admission year: the seat matrix (sanctioned seats; kept apart from vacancy, only used to sanity-check vacancy)
  * each of the three previous years: the FINAL available cutoff round per group (MH, AI)
Not downloaded for now (listed in the report as 'deferred'): Diploma lists, the after-CAP (ACAP) vacancy list, court-order / new-institute
vacancy lists, vacancy lists of Round I-II, earlier rounds of previous years, previous years' seat matrices."""
from .admission_year import ROUND_ORDER

DEFAULT_POLICY = {"scopes": ("MH", "AI"), "vacancy_rounds": ("III", "IV"), "max_file_bytes": 100 * 1024 * 1024, "max_total_bytes": 300 * 1024 * 1024}


def _usable(d):
    return (d.get("verification") or {}).get("reachable") is not False


def select_documents(report, policy=None):
    pol = dict(DEFAULT_POLICY, **(policy or {}))
    ay = report.get("admission_year") or {}
    cur = ay.get("current_start_year")
    if cur is None:
        return [], []
    prev = [p["start_year"] for p in ay.get("previous", [])]
    docs = [d for d in report.get("documents", []) if _usable(d) and not d.get("supplementary") and d.get("year")]
    chosen, why = {}, {}

    def pick(d, reason):
        if d["id"] not in chosen:
            chosen[d["id"]] = d; why[d["id"]] = reason

    final = {}
    for d in docs:
        if d["doc_type"] == "cutoff" and d["scope"] in pol["scopes"] and d["cap_round"]:
            k = (d["year"], d["scope"])
            if k not in final or ROUND_ORDER.index(d["cap_round"]) > ROUND_ORDER.index(final[k]): final[k] = d["cap_round"]
    for d in docs:
        t, y = d["doc_type"], d["year"]
        if y == cur and t == "cutoff" and d["scope"] in pol["scopes"] and d["cap_round"]: pick(d, "current year %s cutoff, CAP Round %s (%s)" % (d["year_label"], d["cap_round"], d["scope"]))
        elif y == cur and t == "vacancy_position" and d["cap_round"] in pol["vacancy_rounds"]: pick(d, "current year vacancy position, CAP Round %s" % d["cap_round"])
        elif y == cur and t == "seat_matrix": pick(d, "current year seat matrix (sanctioned seats, not vacancy)")
        elif y in prev and t == "cutoff" and d["scope"] in pol["scopes"] and d["cap_round"] and final.get((y, d["scope"])) == d["cap_round"]:
            pick(d, "previous year %s cutoff, final round %s (%s)" % (d["year_label"], d["cap_round"], d["scope"]))
    order = lambda d: (-d["year"], d["doc_type"], d["scope"] or "", ROUND_ORDER.index(d["cap_round"]) if d["cap_round"] else -1)
    selected = [dict(chosen[i], why=why[i]) for i in sorted(chosen, key=lambda i: order(chosen[i]))]
    deferred = [dict(id=d["id"], url=d["url"], doc_type=d["doc_type"], year_label=d["year_label"], cap_round=d["cap_round"], scope=d["scope"],
                     why="not needed yet") for d in report.get("documents", []) if d["id"] not in chosen]
    return selected, deferred
