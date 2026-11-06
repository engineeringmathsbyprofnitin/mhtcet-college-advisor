"""Normalising the official codes (Stage 9).

The 2023-24 lists lost the leading zero of every code (institute 1002 instead of 01002; course 100219110 instead of
0100219110). The official 2024-25 onward lists keep it. Codes are therefore padded, and the rule 'a course code begins
with its institute code' is used to prove the padding right on every row."""
import re

INSTITUTE_RE = re.compile(r"^(\d{4,5})$")
CHOICE_RE = re.compile(r"^(\d{9,10})([A-Z]{0,3})$")


def norm_institute_code(code):
    c = (code or "").strip()
    return c.zfill(5) if INSTITUTE_RE.match(c) else None


def norm_choice_code(code):
    """'100219110' -> '0100219110'; '0302524270U' and '0303337293LK' keep their letters; anything else -> None."""
    m = CHOICE_RE.match((code or "").strip())
    return (m.group(1).zfill(10) + m.group(2)) if m else None


def choice_matches_institute(choice, institute):
    return bool(choice and institute and choice[:5] == institute)
