"""Which State-list cutoff cells apply to which Maharashtra-candidature student (Stage 10a).

Only rules proved by the official documents are applied. Everything else is reported as 'unknown' and is NOT matched
automatically. The official legend defines only: first letter G-General / L-Ladies; last letter H-Home University /
O-Other than Home University / S-State Level. The meaning of the stage labels (I, II, VII, MH, I-Non ...) and of the
variant letters R / I / N / 2 is NOT defined in the documents and is never guessed here.

A student profile is a dict:
  home_university (str, as in master/home_universities.csv), gender ('female'|'male'|'other'),
  category (OPEN|SC|ST|VJ|NT1|NT2|NT3|OBC|SEBC), ews, tfws, pwd, defence, orphan, minority (bool; default False).
"""
import csv, os

CATEGORIES = ("OPEN", "SC", "ST", "VJ", "NT1", "NT2", "NT3", "OBC", "SEBC")
AUTONOMOUS = "Autonomous Institute"
S_STATE = "State Level"
S_HU_HU = "Home University Seats Allotted to Home University Candidates"
S_HU_OHU = "Home University Seats Allotted to Other Than Home University Candidates"
S_OHU_HU = "Other Than Home University Seats Allotted to Home University Candidates"
S_OHU_OHU = "Other Than Home University Seats Allotted to Other Than Home University Candidates"
S_MINORITY = "Minority Seats Allotted to Maharashtra State Candidature Candidates"
S_AI = "Maharashtra State Seats Allotted to All India Candidature Candidates"
KNOWN_SECTIONS = (S_STATE, S_HU_HU, S_HU_OHU, S_OHU_HU, S_OHU_OHU, S_MINORITY, S_AI)


def load_seat_codes(path):
    with open(path, newline="", encoding="utf-8") as f:
        return {r["code"]: r for r in csv.DictReader(f)}


def section_ok(section, student_hu, college_hu):
    """Returns (True|False|None, reason). None = cannot decide from the documents."""
    if section not in KNOWN_SECTIONS:
        return None, "unrecognised section"
    if section == S_AI:
        return False, "seats for All India candidates"
    if section == S_MINORITY:
        return None, "minority seat: depends on the candidate's minority, not asked"
    if section == S_STATE:
        return True, "state level seat open to all Maharashtra candidates"
    if college_hu == AUTONOMOUS:
        return False, "autonomous institute has no home university"
    same = (student_hu == college_hu)
    if section in (S_HU_HU, S_OHU_HU):
        return same, "home-university candidate" if same else "needs a student of the college's home university"
    return (not same), "other-than-home-university candidate" if not same else "student belongs to this home university"


def seat_ok(code, info, p):
    """Does the seat-code family apply to this student? (True | False | None = unknown meaning)"""
    if info is None:
        return None, "unrecognised seat code"
    fam, var = info["family"], info.get("variant", "")
    if fam == "regular":
        if info["gender_scope"] == "Ladies" and p.get("gender") != "female":
            return False, "ladies seat"
        cat = info["category"]
        if cat == "OPEN" or cat == p.get("category"):
            return True, "category matches"
        return False, "other category"
    if fam == "ews":
        return bool(p.get("ews")), "EWS seat"
    if fam == "tfws":
        return bool(p.get("tfws")), "TFWS seat"
    if fam in ("pwd", "defence", "phc"):
        if var:
            return None, "variant '%s' not defined in the documents" % var
        flag = {"pwd": "pwd", "defence": "defence", "phc": "pwd"}[fam]
        if not p.get(flag):
            return False, fam + " seat"
        return (info["category"] in ("", "OPEN", p.get("category"))), fam + " seat, category check"
    if fam == "orphan":
        if var:
            return None, "variant '%s' not defined in the documents" % var
        return bool(p.get("orphan")), "orphan seat"
    if fam == "minority":
        return None, "minority seat"
    if fam == "all_india_seat":
        return False, "All India list code"
    return None, "unknown family"


def applicable(row, p, seat_codes):
    """row: one State-list record. Returns (True|False|None, reason). Requires both the section and the seat code to apply."""
    s_ok, s_why = section_ok(row["section"], p.get("home_university"), row["home_university"])
    c_ok, c_why = seat_ok(row["seat_code"], seat_codes.get(row["seat_code"]), p)
    if s_ok is False or c_ok is False:
        return False, (s_why if s_ok is False else c_why)
    if s_ok is None or c_ok is None:
        return None, (s_why if s_ok is None else c_why)
    return True, s_why + "; " + c_why


def closing_cells(rows):
    """Collapse the stages of one round to one closing figure per (round, course, section, seat code).
    Rule (provisional, owner may change): the LOWEST percentile over the stages present, because the stage meanings are
    undefined and the lowest percentile is the lowest one at which a seat is documented as allotted. Stage and the other
    stages' values are kept alongside; nothing is discarded."""
    out = {}
    for r in rows:
        k = (r["year_label"], r["cap_round"], r["choice_code"], r["section"], r["seat_code"])
        out.setdefault(k, []).append(r)
    res = []
    for k, rs in out.items():
        rs = [r for r in rs if (r.get("percentile") or "").strip()]
        if not rs:
            continue
        best = min(rs, key=lambda r: float(r["percentile"]))
        res.append({"key": k, "closing_percentile": best["percentile"], "closing_merit_no": best["merit_no"], "closing_stage": best["stage"],
                    "all_stages": {r["stage"]: r["percentile"] for r in rs}})
    return res
