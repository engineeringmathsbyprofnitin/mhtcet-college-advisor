"""Stage 11a: read an official CET Cell "Vacancy for CAP Round" PDF (text layout).

Facts proven on the real FE2026 Round IV file (every course block, no exceptions):
  MS Seats            = seat-grid totals (State Level, or HU + OHU) + PWD row + DEF row + OrphanI + OrphanN
  Vacant CAP Seats    = MS Seats + All India + Minority Seats      (Institute Seats are NOT included)
These are checked for every block; a block that breaks them is reported, never corrected.
Seat intake (SI) is kept as a separate number and is never used as vacancy.
Nothing is invented: missing = None. Unrecognised lines are reported.
"""
import re, subprocess

CATS = ["OPEN", "SC", "ST", "VJ/DT", "NTB", "NTC", "NTD", "OBC", "SEBC"]
GRID_LABELS = ("State Level", "HU", "OHU")

RE_INST = re.compile(r"^\s*(\d{5})\s+-\s+(.+?)\s*$")
RE_STATUS = re.compile(r"^\s*(.*?)\s*Vacant CAP Seats:\s*(\d+)\s*$")
RE_CODE = re.compile(r"^\s+(\d{10}[A-Z]{0,2})\b(.*?)((?:\s+\d+){7})\s*$")
RE_GRID = re.compile(r"^\s*(State Level|HU|OHU)\s+((?:\d+\s+){18}\d+)\s*$")
RE_RES = re.compile(r"^\s*(PWD|DEF)\s+((?:\d+\s+){9}\d+)\s*$")
RE_COMMON = re.compile(r"^\s*(PWD|DEF) Common Reserved Seats\s*:\s*(\d+)\s*$")
RE_EWS = re.compile(r"^\s*Economically Weaker Section \(EWS\) Seats:\s*(\d+)\s+Tution Fee Waiver Scheme Choice Code:\s*(\w*)\s*Seats:\s*(\d+)\s*$")
RE_PAGE = re.compile(r"Page\s+(\d+)\s+of\s+(\d+)")
KNOWN = [re.compile(p) for p in (
    r"^\s*$", r"^\s*MS\s*$", r"^\s*Seats\s*$", r"^\s*Choice Code\s+Course Name", r"^\s*Category\s+OPEN",
    r"^\s*General / Ladies", r"^\s*Government of Maharashtra", r"^\s*State Common Entrance Test Cell",
    r"^\s*Provisional Vacancy", r"^\s*Technology \(4 Years\)", r"^\s*Published Date", r"^\s*(Autonomous Institute|Non[- ]?Autonomous Institute|University Department|University Managed|Un-?Aided|Government|Minority)[A-Za-z \-/]*$",
    r"^F: Only For Female", r"^Common Reserved:", r"^OrphanI:", r"^Note:-", r"^STATE CET CELL",
)]


def pdf_to_text(pdf_path):
    return subprocess.run(["pdftotext", "-layout", pdf_path, "-"], check=True, capture_output=True).stdout.decode("utf-8", "replace")


def parse_text(text):
    """Return {'blocks': [...], 'problems': [...], 'unrecognised': [...], 'pages': (seen, declared), 'ghosts': n}."""
    lines = text.replace("\f", "\n").split("\n")
    blocks, problems, unrec, ghosts = [], [], [], 0
    inst = None
    cur = None
    pages_seen, declared = set(), None
    name_parts = {"above": [], "below": []}
    stage = None  # None | 'head' (after status line, before Category line)
    stray = None  # a page-top title line; accepted only if it is part of the next institute name

    def finish():
        nonlocal cur
        if cur is None:
            return
        if cur["code"] is None:
            cur["_ghost"] = True
        blocks.append(cur)
        cur = None

    for n, l in enumerate(lines, 1):
        mp = RE_PAGE.search(l)
        if mp:
            pages_seen.add(int(mp.group(1))); declared = int(mp.group(2)); continue
        m = RE_INST.match(l)
        if m and not RE_CODE.match(l):
            if stray is not None:
                if stray[1] not in m.group(2): unrec.append(stray)
                stray = None
            inst = [m.group(1), m.group(2)]; stage = "inst"; continue
        m = RE_STATUS.match(l)
        if m:
            finish()
            cur = dict(inst_code=inst[0] if inst else None, inst_name=inst[1] if inst else None, kind=m.group(1).strip() or None,
                       vacant=int(m.group(2)), code=None, course=None, si=None, ms=None, minority=None, all_india=None, institute=None,
                       orphan_i=None, orphan_n=None, rows={}, pwd=None, defence=None, pwd_common=None, def_common=None,
                       ews=None, tfws_code=None, tfws=None, line=n)
            stage = "head"; name_parts = {"above": [], "below": []}
            continue
        if stage == "inst" and inst and l.strip() and not RE_STATUS.match(l) and not any(k.match(l) for k in KNOWN) and not RE_INST.match(l) and not RE_CODE.match(l):
            inst[1] = inst[1] + " " + l.strip(); continue
        if cur is None:
            if not any(k.match(l) for k in KNOWN):
                if stray is not None: unrec.append(stray)
                stray = (n, l.strip()[:100])
            continue
        m = RE_CODE.match(l)
        if m and cur["code"] is None:
            nums = list(map(int, m.group(3).split()))
            cur.update(code=m.group(1), si=nums[0], ms=nums[1], minority=nums[2], all_india=nums[3], institute=nums[4], orphan_i=nums[5], orphan_n=nums[6])
            name_parts["mid"] = m.group(2).strip(); stage = "after_code"
            cur["course"] = " ".join(name_parts["above"] + ([name_parts["mid"]] if name_parts["mid"] else [])).strip() or None
            continue
        m = RE_GRID.match(l)
        if m:
            v = list(map(int, m.group(2).split()))
            cur["rows"][m.group(1)] = dict(cells=v[:18], total=v[18]); continue
        m = RE_RES.match(l)
        if m:
            v = list(map(int, m.group(2).split()))
            cur["pwd" if m.group(1) == "PWD" else "defence"] = dict(cells=v[:9], total=v[9]); continue
        m = RE_COMMON.match(l)
        if m:
            cur["pwd_common" if m.group(1) == "PWD" else "def_common"] = int(m.group(2)); continue
        m = RE_EWS.match(l)
        if m:
            cur.update(ews=int(m.group(1)), tfws_code=m.group(2) or "", tfws=int(m.group(3))); continue
        if any(k.match(l) for k in KNOWN):
            continue
        s = l.strip()
        if m is None and stage in ("head", "after_code") and re.match(r"^[A-Za-z(\[][A-Za-z0-9 ,&()\[\]./\-]*$", s) and not RE_INST.match(l):
            name_parts["above" if cur["code"] is None else "below"].append(s)
            cur["course"] = " ".join(name_parts["above"] + ([name_parts.get("mid")] if name_parts.get("mid") else []) + name_parts["below"]).strip() or None
            continue
        if stray is not None: unrec.append(stray)
        stray = (n, s[:100])
    if stray is not None: unrec.append(stray)
    finish()

    out = []
    for i, b in enumerate(blocks):
        if b.pop("_ghost", False):
            nxt = blocks[i + 1] if i + 1 < len(blocks) else None
            if nxt is not None and nxt["vacant"] == b["vacant"] and nxt["code"] is not None:
                ghosts += 1
            else:
                problems.append("line %d: header 'Vacant CAP Seats:%d' without a course block" % (b["line"], b["vacant"]))
            continue
        out.append(b)

    for b in out:
        tag = "%s (line %d)" % (b["code"], b["line"])
        grid = sum(r["total"] for r in b["rows"].values())
        for lab, r in b["rows"].items():
            if sum(r["cells"]) != r["total"]:
                problems.append("%s: row %s cells do not add up" % (tag, lab))
        if not b["rows"]: problems.append("%s: no seat-grid row" % tag)
        for k in ("pwd", "defence"):
            if b[k] is None: problems.append("%s: missing %s row" % (tag, k))
            elif sum(b[k]["cells"]) != b[k]["total"]: problems.append("%s: %s row does not add up" % (tag, k))
        for k in ("ews", "tfws", "tfws_code", "pwd_common", "def_common", "inst_code", "course"):
            if b[k] is None: problems.append("%s: missing %s" % (tag, k))
        if b["tfws_code"] == "" and b["tfws"]: problems.append("%s: TFWS seats %d but no TFWS choice code printed" % (tag, b["tfws"]))
        if None not in (b["pwd"], b["defence"]):
            ms = grid + b["pwd"]["total"] + b["defence"]["total"] + b["orphan_i"] + b["orphan_n"]
            if ms != b["ms"]: problems.append("%s: MS Seats %d != grid+PWD+DEF+orphans %d" % (tag, b["ms"], ms))
        if b["vacant"] != b["ms"] + b["all_india"] + b["minority"]:
            problems.append("%s: Vacant %d != MS+AllIndia+Minority %d" % (tag, b["vacant"], b["ms"] + b["all_india"] + b["minority"]))
        b["grid_total"] = grid
    codes = [b["code"] for b in out]
    dup = sorted({c for c in codes if codes.count(c) > 1})
    if dup: problems.append("duplicate choice codes: %s" % dup[:10])
    if declared is not None and pages_seen != set(range(1, declared + 1)):
        problems.append("pages seen %d of declared %d" % (len(pages_seen), declared))
    return dict(blocks=out, problems=problems, unrecognised=unrec, pages=(len(pages_seen), declared), ghosts=ghosts)


def parse_pdf(path):
    return parse_text(pdf_to_text(path))
