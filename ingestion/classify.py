"""Decides what an official link is: cutoff list, vacancy position, seat matrix, etc.
Uses the link text, the table headings around it and the file name. Every decision lists its reasons.
Nothing is guessed silently: unknown things stay unknown (None)."""
import re
from urllib.parse import urlparse, unquote
from .admission_year import parse_year_label, label

ROUND_WORD = {"iv": "IV", "iii": "III", "ii": "II", "i": "I", "4": "IV", "3": "III", "2": "II", "1": "I"}
_R = r"(iv|iii|ii|i|[1-4])(?![a-z0-9])"
ROUND_RES = [re.compile(r"cap[\s\-_]*round[\s\-_]*" + _R), re.compile(r"round[\s\-_]*" + _R), re.compile(r"cap[\s\-_]*" + _R)]
DOC_EXT = (".pdf", ".xlsx", ".xls", ".csv", ".zip")


def _norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def _filename(href):
    return unquote(urlparse(href or "").path.rsplit("/", 1)[-1])


def _find_round(text):
    for rx in ROUND_RES:
        m = rx.search(text)
        if m:
            return ROUND_WORD[m.group(1)]
    return None


def _year_from_href(href, text_year):
    """Returns (start_year, source). File names such as 2025ENGG_CAP1_CutOff.pdf use the START year (2025 = 2025-26)."""
    p = urlparse(href or "")
    fname = _filename(href)
    for rx, src in ((r"^(20\d{2})(?!\d)", "file name"), (r"(?<![a-z0-9])fe(20\d{2})(?!\d)", "file name"),
                    (r"cappublicdocs(20\d{2})", "host name"), (r"/(20\d{2})/", "folder name")):
        target = fname.lower() if src == "file name" else (p.netloc + p.path).lower()
        m = re.search(rx, target)
        if m:
            return int(m.group(1)), src
    return None, None


def classify(text, href, context=None, portal_year=None):
    """text = link text; href = absolute URL; context = {"row_label","col_headers","heading"} (any may be missing);
    portal_year = start year of the portal page the link was found on (used only when nothing else says otherwise)."""
    ctx = context or {}
    cols = [c for c in ctx.get("col_headers", []) if c]
    fname = _filename(href)
    ftext = fname.lower().replace("_", " ")
    blob = _norm(" ".join([text or ""] + cols)).lower()
    both = blob + " | " + ftext
    reasons, qualifiers = [], []

    # ----- what kind of document
    if re.search(r"seat\s*matrix|seatmatrix|category[\s-]*wise seats", both):
        doc_type = "seat_matrix"; reasons.append("mentions seat matrix")
    elif re.search(r"vacan", both):
        if re.search(r"(after|post)[\s-]*cap|\bacap\b", both):
            doc_type = "vacancy_after_cap"; qualifiers.append("acap"); reasons.append("vacancy list AFTER the CAP rounds (ACAP): not a CAP round vacancy position")
        else:
            doc_type = "vacancy_position"; reasons.append("mentions vacancy")
    elif re.search(r"cut[\s-]*off|cutoff", both):
        doc_type = "cutoff"; reasons.append("mentions cut off")
    elif re.search(r"merit[\s-]*list|meritlist", both):
        doc_type = "merit_list"; reasons.append("mentions merit list")
    elif re.search(r"allotment", both):
        doc_type = "allotment"; reasons.append("mentions allotment")
    elif re.search(r"brochure", both):
        doc_type = "brochure"; reasons.append("mentions brochure")
    elif re.search(r"list of (the )?(colleges|institutes|off[\s-]*campus)|intake capacity", both):
        doc_type = "institute_list"; reasons.append("institute list")
    elif re.search(r"\bfees?\b", both):
        doc_type = "fee"; reasons.append("mentions fee")
    else:
        doc_type = "other"; reasons.append("no known keyword")

    # ----- CAP round
    cap_round = _find_round(both)
    if cap_round:
        reasons.append("round %s from %s" % (cap_round, "link text/headings" if _find_round(blob) else "file name"))
    # ----- candidate group
    tokens = set(re.split(r"[^a-z0-9]+", both))
    scope = None
    if "diploma" in tokens: scope = "DIPLOMA"
    elif "mh" in tokens or "maharashtra" in tokens: scope = "MH"
    elif "ai" in tokens or ("all" in tokens and "india" in tokens): scope = "AI"
    if scope: reasons.append("group %s" % scope)
    elif doc_type == "cutoff": reasons.append("candidate group not stated; to be read from the document itself")

    # ----- qualifiers
    if "provisional" in tokens: qualifiers.append("provisional")
    if re.search(r"court\s*or?de?r|courtoder", both): qualifiers.append("court_order")
    if re.search(r"new\s*institute|newinstitute", both): qualifiers.append("new_institute")
    v = re.search(r"(?<![a-z0-9])v(\d+)(?![a-z0-9])", ftext)
    if v: qualifiers.append("version_" + v.group(1))
    supplementary = "court_order" in qualifiers or "new_institute" in qualifiers

    # ----- year
    row_year = parse_year_label(ctx.get("row_label", "")) or parse_year_label(blob)
    href_year, href_src = _year_from_href(href, None)
    year, ysrc = None, None
    if row_year: year, ysrc = row_year, "table row / link text"
    elif href_year: year, ysrc = href_year, href_src
    elif portal_year: year, ysrc = portal_year, "portal page (nothing else stated)"
    if year: reasons.append("year %s from %s" % (label(year), ysrc))
    if row_year and href_year and row_year != href_year:
        reasons.append("WARNING: table says %s but file name says %s" % (label(row_year), label(href_year)))
        qualifiers.append("year_conflict")

    strong = (re.search(r"cut[\s-]*off|vacan|seat\s*matrix", blob) is not None)
    confidence = "high" if strong and (cap_round or doc_type == "seat_matrix") else ("medium" if doc_type != "other" else "low")
    return {"doc_type": doc_type, "cap_round": cap_round if doc_type in ("cutoff", "vacancy_position", "vacancy_after_cap", "allotment") else None,
            "scope": scope if doc_type == "cutoff" else None, "year": year, "year_label": label(year) if year else None,
            "qualifiers": qualifiers, "supplementary": supplementary, "confidence": confidence, "reasons": reasons,
            "is_file": fname.lower().endswith(DOC_EXT) or "blob.core.windows.net" in (urlparse(href or "").netloc)}
