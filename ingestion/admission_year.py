"""Works out the current admission year from EVIDENCE found on the official CET Cell portals.

A year is only treated as 'established' when real CAP cutoff documents have been found for it.
The calendar is used only to label the situation (is this year's cycle running, or are we between cycles?);
it is never used to pick the year. No January/July rule is assumed.

Observed on the official portal (23-26 Oct 2026): the CAP for admission year Y-(Y+1) is held in calendar year Y
(2023-24 ... 2026-27). That observation only decides the status label, see decide()."""
import re
from datetime import date

YEAR_RE = re.compile(r"(?<!\d)(20\d{2})\s*[-\u2013\u2014/]\s*(\d{4}|\d{2})(?!\d)")
ROUND_ORDER = ["I", "II", "III", "IV"]
ASSUMPTION = ("The CAP for admission year Y-(Y+1) is held during calendar year Y (seen for 2023-24 to 2026-27). "
              "This only affects the status label, not which year is chosen.")


def label(start):
    return "%d-%02d" % (start, (start + 1) % 100)


def parse_year_label(text):
    """'2026-27', '2026-2027', 'A.Y. 2026 \u2013 27' -> 2026. Returns None if absent or inconsistent (e.g. 2026-28)."""
    m = YEAR_RE.search(text or "")
    if not m:
        return None
    start, end = int(m.group(1)), m.group(2)
    ok = (len(end) == 4 and int(end) == start + 1) or (len(end) == 2 and int(end) == (start + 1) % 100)
    return start if ok else None


def previous_years(start, n=3):
    return [start - i for i in range(1, n + 1)]


def _rounds(docs, year, doc_type, scope=None, include_supplementary=False):
    out = set()
    for d in docs:
        if d.get("year") != year or d.get("doc_type") != doc_type or not d.get("cap_round"):
            continue
        if scope and d.get("scope") != scope:
            continue
        if d.get("supplementary") and not include_supplementary:
            continue
        out.add(d["cap_round"])
    return [r for r in ROUND_ORDER if r in out]


def decide(evidence, today=None, history=3):
    """evidence = {"menu_years": [2026, ...], "docs": [{"year":2026,"doc_type":"cutoff","cap_round":"IV","scope":"MH",
                   "reachable": True|False|None, "supplementary": False}, ...]}
    Returns a plain dict (JSON friendly)."""
    today = today or date.today()
    docs = [d for d in evidence.get("docs", [])]
    menu = sorted({y for y in evidence.get("menu_years", []) if isinstance(y, int)}, reverse=True)
    warnings = []

    def usable(d):                      # a document found but known to be unreachable does not count as evidence
        return d.get("reachable") is not False

    established = sorted({d["year"] for d in docs if d.get("year") and d.get("doc_type") == "cutoff"
                          and d.get("cap_round") and usable(d)}, reverse=True)
    result = {"today": today.isoformat(), "assumption": ASSUMPTION, "menu_years": menu,
              "established_years": established, "warnings": warnings}
    if not established:
        result.update({"current_start_year": None, "current_label": None, "status": "unknown", "previous": [],
                       "latest_cutoff_round": None, "vacancy_round": None})
        warnings.append("No published CAP cutoff documents were found, so the admission year cannot be established. "
                        "Keep the last validated data.")
        return result

    current = established[0]
    newer_listed = [y for y in menu if y > current]
    if current > today.year:
        status = "confirmed"
        warnings.append("The newest portal year (%s) is ahead of today's calendar year; check the computer clock and the portal." % label(current))
    elif current == today.year:
        status = "confirmed"
    else:
        status = "previous_cycle_latest"
        warnings.append("No cutoff documents for the %s cycle have been published yet. The latest established year is %s; "
                        "keep serving its data and flag that a new cycle has not started." % (label(today.year), label(current)))
    unopenable = sorted({d["year"] for d in docs if d.get("doc_type") == "cutoff" and d.get("year") and d.get("reachable") is False} - set(established), reverse=True)
    newer_unopenable = [y for y in unopenable if y > current]
    if newer_unopenable:
        status = "newer_documents_unreachable"
        warnings.append("Cutoff documents for %s were found on the portal but could not be opened, so that year is not adopted yet; keeping %s." % (", ".join(label(y) for y in newer_unopenable), label(current)))
    elif newer_listed:
        status = "new_cycle_announced" if current < today.year else status
        warnings.append("The menu lists %s but no cutoff documents were found for it yet." % ", ".join(label(y) for y in newer_listed))

    prev = []
    for y in previous_years(current, history):
        rounds = _rounds(docs, y, "cutoff")
        prev.append({"start_year": y, "label": label(y), "cutoff_rounds": rounds, "has_cutoffs": bool(rounds)})
        if not rounds:
            warnings.append("Previous year %s has no cutoff documents; it will show as 'Not available'." % label(y))
    cur_rounds = _rounds(docs, current, "cutoff")
    vac_rounds = _rounds(docs, current, "vacancy_position")
    vacancy_round = "IV" if "IV" in vac_rounds else ("III" if "III" in vac_rounds else None)
    if vacancy_round is None:
        warnings.append("No Round IV or Round III vacancy-position document found for %s: vacancy will show as unavailable." % label(current))
    result.update({"current_start_year": current, "current_label": label(current), "status": status, "previous": prev,
                   "current_cutoff_rounds": cur_rounds, "latest_cutoff_round": cur_rounds[-1] if cur_rounds else None,
                   "vacancy_rounds_found": vac_rounds, "vacancy_round": vacancy_round})
    return result
