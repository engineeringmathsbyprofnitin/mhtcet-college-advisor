"""Stage 12c-2: read the NAAC list downloaded by the site owner (data/manual/naac/*.xlsx) -> data/normalized/naac/naac_institutions.csv (Maharashtra rows only).

The file is the official NAAC list "Institutions accredited by NAAC having valid accreditation as on <date>" (sheet "Colleges": HEI Name, Track-Id, Aishe-Id, Affiliating University,
Address, Current Cycle Number, Current CGPA, Current Grade, Date Of Declaration). It does NOT contain an end date, and 400+ rows are older than five years at the list date, so no
end date is ever computed here: only the declaration date, the grade and the date of the list are kept (the website says "on NAAC's list as on <date>").
The sheet "Transition Autonomous Colleges" (extended validity, no grade) is not used.
Nothing is guessed: a row whose state cannot be read from the address, whose grade is unknown, or whose date does not parse is reported as a problem.
"""
import csv, datetime, hashlib, json, os, re, sys, zipfile
import xml.etree.ElementTree as ET
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "data", "manual", "naac")
OUT = os.path.join(ROOT, "data", "normalized", "naac")
NEED = ["HEI Name", "Track-Id", "Aishe-Id", "Affiliating University", "Address", "Current Cycle Number", "Current CGPA", "Current Grade", "Date Of Declaration"]
GRADE_BANDS = {"A++": (3.51, 4.00), "A+": (3.26, 3.50), "A": (3.01, 3.25), "B++": (2.76, 3.00), "B+": (2.51, 2.75), "B": (2.01, 2.50), "C": (1.51, 2.00)}
COLS = ["source_row", "track_id", "aishe_id", "name", "affiliating_university", "address", "locality_hint", "district_hint", "state", "pin", "cycle", "cgpa", "grade", "declared_on", "list_as_on", "source_file", "source_sha256"]


def clean(s): return re.sub(r"\s+", " ", str(s if s is not None else "")).strip()


def undouble(s):
    s = clean(s); h = len(s) // 2
    return s[:h].strip() if len(s) % 2 == 0 and h > 3 and s[:h].strip() == s[h:].strip() else s


STATES = {"andaman and nicobar", "andaman and nicobar islands", "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chandigarh", "chhattisgarh", "dadra and nagar haveli",
          "dadra and nagar haveli and daman and diu", "daman and diu", "delhi", "new delhi", "goa", "gujarat", "haryana", "himachal pradesh", "jammu and kashmir", "jharkhand", "karnataka", "kerala",
          "ladakh", "lakshadweep", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram", "nagaland", "odisha", "orissa", "puducherry", "pondicherry", "punjab", "rajasthan", "sikkim",
          "tamil nadu", "telangana", "tripura", "uttar pradesh", "uttarakhand", "uttaranchal", "west bengal"}


def split_address(a):
    """The NAAC address is free text that usually ends '..., <locality>, <district>, <State>, <PIN>' but sometimes lacks the district or the PIN. The STATE is found by scanning from the
    end for a state name (exact, all 7,566 rows are recognised); locality_hint / district_hint are only the two parts before it and can be wrong - never used as facts."""
    p = [clean(x) for x in str(a or "").replace("\n", " ").split(",")]
    for i in range(len(p) - 1, -1, -1):
        if p[i].lower() in STATES:
            return dict(locality_hint=p[i - 2] if i >= 2 else "", district_hint=p[i - 1] if i >= 1 else "", state=p[i], pin=p[i + 1] if i + 1 < len(p) and re.fullmatch(r"\d{6}", p[i + 1]) else "")
    return dict(locality_hint="", district_hint="", state="", pin="")


def list_date(filename):
    m = re.search(r"(\d{2})(\d{2})(\d{4})", filename)
    try: return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat() if m else ""
    except ValueError: return ""


NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def sheet_names(path):
    with zipfile.ZipFile(path) as z: return [x.get("name") for x in ET.fromstring(z.read("xl/workbook.xml")).iter("{%s}sheet" % NS["m"])]


def read_sheet(path, name):
    """Stdlib-only reader of ONE named worksheet -> list of rows (lists of str); no extra package is needed in GitHub Actions (same idea as the NBA reader)."""
    with zipfile.ZipFile(path) as z:
        names = z.namelist(); sst = []
        if "xl/sharedStrings.xml" in names:
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS): sst.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
        rid = None
        for sh in ET.fromstring(z.read("xl/workbook.xml")).iter("{%s}sheet" % NS["m"]):
            if sh.get("name") == name: rid = sh.get("{%s}id" % NS["r"])
        if rid is None: raise KeyError(name)
        target = None
        for rel in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")):
            if rel.get("Id") == rid: target = rel.get("Target")
        target = target.lstrip("/"); target = target if target.startswith("xl/") else "xl/" + target
        rows = []
        for r in ET.fromstring(z.read(target)).iter("{%s}row" % NS["m"]):
            cells = {}
            for c in r.findall("m:c", NS):
                col = re.match(r"[A-Z]+", c.get("r")).group(0); idx = 0
                for ch in col: idx = idx * 26 + ord(ch) - 64
                t = c.get("t"); v = c.find("m:v", NS)
                if t == "s": val = sst[int(v.text)] if v is not None and v.text is not None else ""
                elif t == "inlineStr": val = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
                else: val = v.text if v is not None and v.text is not None else ""
                cells[idx] = val
            rows.append([cells.get(i, "") for i in range(1, (max(cells) if cells else 0) + 1)])
        return rows


def read_file(path):
    try: allrows = read_sheet(path, "Colleges")
    except KeyError: return None, ["sheet 'Colleges' is missing (found: %s)" % ", ".join(sheet_names(path))]
    except (zipfile.BadZipFile, KeyError, ET.ParseError, AttributeError) as e: return None, ["the file cannot be read as an Excel file (%s)" % type(e).__name__]
    if not allrows: return None, ["sheet 'Colleges' is empty"]
    head = [clean(x) for x in allrows[0]]; miss = [c for c in NEED if c not in head]
    if miss: return None, ["column(s) missing: " + ", ".join(miss)]
    ix = {c: head.index(c) for c in head}; out = []
    for r in allrows[1:]:
        if all(v in (None, "") for v in r): continue
        out.append({c: (r[ix[c]] if ix[c] < len(r) else "") for c in head})
    return out, []


def build(src=SRC, out=OUT):
    rep = dict(ok=False, files=[], rows_read=0, rows_maharashtra=0, grades={}, problems=[], warnings=[]); os.makedirs(out, exist_ok=True)
    files = sorted(f for f in os.listdir(src) if f.lower().endswith(".xlsx") and not f.startswith("~")) if os.path.isdir(src) else []
    if not files: rep["problems"].append("no .xlsx file in " + src); return _save(rep, out, [])
    if len(files) > 1: rep["problems"].append("more than one .xlsx file in %s (%s): keep only the newest list" % (src, ", ".join(files))); return _save(rep, out, [])
    fn = files[0]; path = os.path.join(src, fn); sha = hashlib.sha256(open(path, "rb").read()).hexdigest(); asof = list_date(fn)
    if not asof: rep["problems"].append("the list date (ddmmyyyy) is not in the file name %s" % fn)
    rows, prob = read_file(path); rep["files"].append(dict(file=fn, sha256=sha, list_as_on=asof))
    if rows is None: rep["problems"] += prob; return _save(rep, out, [])
    rep["rows_read"] = len(rows); res, seen = [], {}
    for i, r in enumerate(rows, 2):
        ad = split_address(r["Address"])
        if not ad["state"]: rep["problems"].append("row %d: state not readable from address" % i); continue
        if ad["state"].lower() != "maharashtra": continue          # only Maharashtra colleges can be on the website
        g = clean(r["Current Grade"]); cg = r["Current CGPA"]
        try: cg = float(cg)
        except (TypeError, ValueError): rep["problems"].append("row %d: CGPA %r is not a number" % (i, cg)); continue
        if g not in GRADE_BANDS: rep["problems"].append("row %d: unknown grade %r" % (i, g)); continue
        lo, hi = GRADE_BANDS[g]
        if not lo - 0.005 <= cg <= hi + 0.005: rep["warnings"].append("row %d: CGPA %.2f does not fit grade %s (kept as printed)" % (i, cg, g))
        try: dec = datetime.datetime.strptime(clean(r["Date Of Declaration"]), "%d-%m-%Y").date()
        except ValueError: rep["problems"].append("row %d: date %r not dd-mm-yyyy" % (i, r["Date Of Declaration"])); continue
        if asof and dec.isoformat() > asof: rep["problems"].append("row %d: declaration date %s is after the list date %s" % (i, dec, asof)); continue
        try: cyc = int(float(r["Current Cycle Number"]))
        except (TypeError, ValueError): rep["problems"].append("row %d: cycle %r is not a number" % (i, r["Current Cycle Number"])); continue
        aid = clean(r["Aishe-Id"])
        if aid in seen: rep["problems"].append("row %d: AISHE id %s already used in row %d" % (i, aid, seen[aid])); continue
        seen[aid] = i
        res.append(dict(source_row=i, track_id=clean(r["Track-Id"]), aishe_id=aid, name=clean(r["HEI Name"]), affiliating_university=undouble(r["Affiliating University"]), address=clean(str(r["Address"])),
                        locality_hint=ad["locality_hint"], district_hint=ad["district_hint"], state="Maharashtra", pin=ad["pin"], cycle=cyc, cgpa="%.2f" % cg, grade=g, declared_on=dec.isoformat(), list_as_on=asof, source_file=fn, source_sha256=sha))
    rep["rows_maharashtra"] = len(res); rep["grades"] = {g: sum(1 for x in res if x["grade"] == g) for g in GRADE_BANDS}
    tr = {}
    for x in res: tr.setdefault(x["track_id"], []).append(x["source_row"])
    rep["warnings"] += ["Track-Id %s is used by rows %s (kept; AISHE id is the key)" % (k, v) for k, v in tr.items() if len(v) > 1]
    if asof: rep["declared_more_than_5_years_before_list"] = sum(1 for x in res if x["declared_on"] < (datetime.date.fromisoformat(asof).replace(year=datetime.date.fromisoformat(asof).year - 5)).isoformat())
    rep["ok"] = not rep["problems"] and bool(res)
    return _save(rep, out, res)


def _save(rep, out, rows):
    with open(os.path.join(out, "naac_institutions.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, lineterminator="\r\n"); w.writeheader(); w.writerows(rows)
    with open(os.path.join(out, "naac_report.json"), "w", encoding="utf-8") as fh: json.dump(rep, fh, indent=1, ensure_ascii=False)
    return rep


def main():
    rep = build(); print("ok=%s rows read=%s Maharashtra=%s grades=%s" % (rep["ok"], rep["rows_read"], rep["rows_maharashtra"], rep["grades"]))
    for p in rep["problems"][:30]: print("FAIL:", p)
    for w in rep["warnings"][:10]: print("warning:", w)
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
