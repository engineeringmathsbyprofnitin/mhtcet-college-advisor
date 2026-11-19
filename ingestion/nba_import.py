"""Stage 12b-2: read the NBA accredited-programs lists that the SITE OWNER downloaded from www.nbaind.org (button "Click here to Download in Excel").

Why by hand: the NBA site answers our GitHub robot with HTTP 403, so nothing is fetched automatically (and nothing is bypassed). The owner downloads the
official Excel files in his own browser and puts them in data/manual/nba/ with one line each in data/manual/nba/sources.csv (file, tier, downloaded_on, note).
Rules: nothing invented or corrected; the printed period text is always kept; a date is derived ONLY when it is printed (an 'upto DD/MM/YYYY' date or a
long-form date range); 'N YEARS W.E.F. <date>' gives start = the printed date and end = start + N years - 1 day, labelled as computed; an unreadable period is reported, not guessed;
an unknown status is stored as 'unknown', never as 'not accredited'. Older and newer entries of the same program are both kept (the newest is used when matching).
NBA accredits PROGRAMS, not colleges. Output: data/normalized/nba/nba_programs.csv + nba_report.json (replaced only if every listed file was read without problem).
"""
import csv, datetime, hashlib, json, os, re, sys, zipfile
import xml.etree.ElementTree as ET
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
MANUAL = os.path.join(ROOT, "data", "manual", "nba")
EXPECTED = ["Name of the Institution", "Program", "Level", "Accreditation Status", "Accreditation Period"]
LEVELS = {"UNDER GRADUATE": "Under Graduate", "UG": "Under Graduate"}
OUT_COLS = ["tier", "institution_raw", "institution_name", "place", "program", "level", "status", "period_text", "valid_from", "valid_to", "validity_basis", "source_file", "source_sha256", "downloaded_on"]
MONTHS = {m: i + 1 for i, m in enumerate("january february march april may june july august september october november december".split())}
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read_xlsx(path):
    """Stdlib-only reader for the first worksheet -> list of rows (lists of str). No extra package is needed in GitHub Actions."""
    with zipfile.ZipFile(path) as z:
        sst = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS): sst.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
        names = sorted(n for n in z.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
        if not names: raise ValueError("no worksheet in the file")
        rows = []
        for r in ET.fromstring(z.read(names[0])).iter("{%s}row" % NS["m"]):
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


def norm(s): return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


def split_name(raw):
    """'Name (Place)' -> (name, place); a place of '--Select--' is unknown (empty). Repeated apostrophes are an export artefact."""
    s = re.sub(r"'{2,}", "'", norm(raw)); m = re.search(r"\(([^()]*)\)\s*$", s)
    if not m: return s, ""
    place = norm(m.group(1)); place = "" if place.startswith("--") else place
    return norm(s[:m.start()]), place


def _d(d, m, y):
    try: return datetime.date(int(y), int(m), int(d))
    except ValueError: return None


DATE = r"(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4})"


def _add_years(d, n):
    try: return d.replace(year=d.year + n)
    except ValueError: return d.replace(year=d.year + n, day=28)          # 29 February -> 28 February


def parse_period(text):
    """-> (valid_from, valid_to, basis, problem). Only printed facts are used.
    1. a printed end date: 'upto DD/MM/YYYY', 'i.e. DD-MM-YYYY' or a long-form date range -> the latest date printed;
    2. 'N YEARS W.E.F. <date>' (many spellings) -> start = the printed date, end = start + N years - 1 day (computed, and labelled as computed);
    3. anything else -> no dates (reported), never guessed. Impossible calendar dates are a problem; an implausible start year (a typo such as 2202) is a warning."""
    t = norm(text)
    upto = [_d(*x) for x in re.findall(r"(?:up\s*to|i\s*\.?\s*e\s*\.?\s*,?)\s*" + DATE, t, re.I)]
    longd = [_d(d, MONTHS[mo.lower()], y) for d, mo, y in re.findall(r"(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(m.capitalize() for m in MONTHS) + r")\s+(\d{4})", t, re.I)]
    wef = re.search(r"(\d+)\s*(?:years?|yrs?)[^0-9]{0,30}?w\s*\.?\s*e\s*\.?\s*f\s*\.?\s*" + DATE, t, re.I)
    if None in upto or None in longd: return "", "", "unparsed", "impossible calendar date in %r" % t[:80]
    ends = upto + longd
    if ends:
        vt = max(ends); vf = ""
        if re.match(r"^(Accredited for )?(Academic Years? )?\d{1,2}(st|nd|rd|th)? ", t, re.I) and longd and not upto: vf = min(longd)
        if vf and vf > vt: return "", "", "unparsed", "start after end in %r" % t[:80]
        if not (2012 <= vt.year <= 2040): return "", "", "unparsed", "end year %d out of range in %r" % (vt.year, t[:80])
        return (vf.isoformat() if vf else ""), vt.isoformat(), "printed 'upto' date" if upto else "printed date range", ""
    if wef:
        n = int(wef.group(1)); d = _d(wef.group(2), wef.group(3), wef.group(4))
        if d is None: return "", "", "unparsed", "impossible calendar date in %r" % t[:80]
        if not (1990 <= d.year <= 2035): return "", "", "unparsed", "implausible start year %d in %r (not guessed)" % (d.year, t[:80])
        if not 1 <= n <= 10: return "", "", "unparsed", "implausible duration %d years in %r" % (n, t[:80])
        end = _add_years(d, n) - datetime.timedelta(days=1)
        return d.isoformat(), end.isoformat(), "computed: %d years from the printed w.e.f. date (end date not printed)" % n, ""
    return "", "", "unparsed", "no date found in %r" % t[:80]


def read_source(path, tier, downloaded_on, name):
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    rows = read_xlsx(path); problems, warnings, out = [], [], []
    if not rows or [norm(c) for c in rows[0][:5]] != EXPECTED or len(rows[0]) != 5: return [], ["%s: unexpected header %s" % (name, rows[0] if rows else None)], warnings, sha
    seen = set()
    for i, r in enumerate(rows[1:], 2):
        if len(r) != 5 or any(not norm(c) for c in r): problems.append("%s row %d: not 5 filled cells: %s" % (name, i, r)); continue
        inst, prog, level, status, period = [norm(c) for c in r]
        lv = LEVELS.get(level.upper())
        if lv is None: problems.append("%s row %d: unknown level %r" % (name, i, level)); continue
        st = "accredited" if status.upper() == "ACCREDITED" else "unknown"
        if st == "unknown": warnings.append("%s row %d: status %r stored as unknown" % (name, i, status))
        vf, vt, basis, prob = parse_period(period)
        if prob and basis == "unparsed" and ("out of range" in prob or "impossible" in prob or "start after end" in prob): problems.append("%s row %d: %s" % (name, i, prob)); continue
        if prob and basis == "unparsed": warnings.append("%s row %d (%s / %s): %s" % (name, i, inst[:40], prog, prob))
        key = (inst, prog, period)
        if key in seen: warnings.append("%s row %d: identical repeated row dropped (%s / %s)" % (name, i, inst[:40], prog)); continue
        seen.add(key); n, place = split_name(inst)
        out.append(dict(tier=tier, institution_raw=inst, institution_name=n, place=place, program=prog, level=lv, status=st, period_text=period, valid_from=vf, valid_to=vt, validity_basis=basis, source_file=name, source_sha256=sha, downloaded_on=downloaded_on))
    return out, problems, warnings, sha


def build(manual=MANUAL, out_dir=None):
    out_dir = out_dir or os.path.join(ROOT, "build", "normalized", "nba"); os.makedirs(out_dir, exist_ok=True)
    rep = dict(ok=False, files=[], rows=0, institutions=0, programs=0, no_end_date=0, problems=[], warnings=[])
    sp = os.path.join(manual, "sources.csv"); allrows = []
    if not os.path.exists(sp): rep["problems"].append("data/manual/nba/sources.csv is missing"); return _save(out_dir, rep)
    with open(sp, newline="", encoding="utf-8") as f: srcs = list(csv.DictReader(f))
    if not srcs: rep["problems"].append("sources.csv lists no file")
    for s in srcs:
        p = os.path.join(manual, s["file"])
        if not os.path.exists(p): rep["problems"].append("listed file %s is missing" % s["file"]); continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s["downloaded_on"]) or not s["tier"].strip(): rep["problems"].append("%s: tier or downloaded_on missing/invalid in sources.csv" % s["file"]); continue
        try: rows, pr, wa, sha = read_source(p, s["tier"].strip(), s["downloaded_on"], s["file"])
        except Exception as e: rep["problems"].append("%s: cannot be read (%s: %s)" % (s["file"], type(e).__name__, e)); continue
        rep["problems"] += pr; rep["warnings"] += wa; allrows += rows
        rep["files"].append(dict(file=s["file"], tier=s["tier"], downloaded_on=s["downloaded_on"], rows=len(rows), sha256=sha))
    rep["rows"] = len(allrows); rep["institutions"] = len({r["institution_raw"] for r in allrows}); rep["programs"] = len({r["program"] for r in allrows})
    rep["no_end_date"] = sum(1 for r in allrows if not r["valid_to"])
    if not allrows and not rep["problems"]: rep["problems"].append("no rows read")
    if rep["problems"]: return _save(out_dir, rep)
    with open(os.path.join(out_dir, "nba_programs.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=OUT_COLS, lineterminator="\r\n"); w.writeheader(); w.writerows(allrows)
    rep["ok"] = True; return _save(out_dir, rep)


def _save(out_dir, rep):
    with open(os.path.join(out_dir, "nba_report.json"), "w", encoding="utf-8") as fh: json.dump(rep, fh, indent=1, ensure_ascii=False)
    return rep


def main():
    rep = build()
    print("files:", [(f["file"], f["rows"]) for f in rep["files"]], "| rows", rep["rows"], "| institutions", rep["institutions"], "| programs", rep["programs"], "| rows without an end date:", rep["no_end_date"])
    print("warnings:", len(rep["warnings"]), rep["warnings"][:6])
    for p in rep["problems"][:20]: print("FAIL:", p)
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
