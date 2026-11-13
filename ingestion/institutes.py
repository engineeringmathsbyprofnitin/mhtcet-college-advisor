"""Stage 10d: official institute information (district, region, address, status, autonomy, minority status, and every course's university,
accreditation text, gender and intake) from the CET Cell engineering portal's public pages.
  list page   https://fe<YEAR>.mahacet.org/StaticPages/frmInstituteList                       ("List of Institutes Participating in CAP")
  one page per institute  .../StaticPages/frmInstituteSummary.aspx?InstituteCode=NNNNN         ("Institute Summary" + "Course Details")
Rules: official host only, robots.txt obeyed, about 1 request per second (ingestion/http_client.py), no login or CAPTCHA is ever bypassed (a wall stops the run),
every page's SHA-256 is recorded, the output is replaced ONLY if every institute listed was read completely (otherwise the last good files stay).
Run: python -m ingestion.institutes [--out data/normalized/institutes] [--year 2026]"""
import csv, hashlib, json, os, re, sys
from html.parser import HTMLParser
from .http_client import PoliteFetcher

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
INFO_LABELS = {"Institute Code": "institute_code", "Institute Name": "institute_name", "Institute Address": "address", "Region": "region", "District": "district",
               "Status": "status", "Autonomy Status": "autonomy_status", "Minority Status": "minority_status", "Public Remark": "public_remark"}
COURSE_COLS = {"Choice Code": "choice_code", "Course Name": "course_name", "University": "university", "Status": "status", "Autonomy Status": "autonomy_status",
               "Minority Status": "minority_status", "Shift": "shift", "Accreditation": "accreditation", "Gender": "gender", "Total Intake": "total_intake"}
CHOICE = re.compile(r"^\d{10}[A-Z]{0,3}$")
CODE = re.compile(r"^\d{5}$")


def norm(s): return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


class _Tables(HTMLParser):
    """Every <table> as a list of rows, each row a list of cell texts (nested tables are read as separate tables)."""
    def __init__(self):
        super().__init__(convert_charrefs=True); self.tables, self.stack = [], []
    def handle_starttag(self, tag, attrs):
        if tag == "table": self.stack.append({"rows": [], "row": None, "cell": None})
        elif self.stack:
            t = self.stack[-1]
            if tag == "tr": t["row"] = []
            elif tag in ("td", "th"):
                if t["row"] is None: t["row"] = []
                t["cell"] = []
            elif tag == "br" and t["cell"] is not None: t["cell"].append(" ")
    def handle_endtag(self, tag):
        if not self.stack: return
        t = self.stack[-1]
        if tag in ("td", "th") and t["cell"] is not None and t["row"] is not None: t["row"].append(norm("".join(t["cell"]))); t["cell"] = None
        elif tag == "tr" and t["row"] is not None:
            if t["row"]: t["rows"].append(t["row"])
            t["row"] = None
        elif tag == "table": self.tables.append(self.stack.pop()["rows"])
    def handle_data(self, data):
        if self.stack and self.stack[-1]["cell"] is not None: self.stack[-1]["cell"].append(data)


def tables(html):
    p = _Tables(); p.feed(html or ""); p.close(); return p.tables


def institute_codes(list_html):
    """(codes in page order, printed count). The count is the last 'Sr. No.' printed; the caller must find exactly that many codes."""
    codes, last_sr = [], 0
    for t in tables(list_html):
        for row in t:
            if len(row) >= 3 and re.match(r"^\d+\.?$", row[0]) and CODE.match(row[1]):
                if row[1] not in codes: codes.append(row[1])
                last_sr = max(last_sr, int(row[0].rstrip(".")))
    for m in re.finditer(r"InstituteCode=(\d{5})", list_html or ""):          # links, as a second witness
        if m.group(1) not in codes: codes.append(m.group(1))
    return codes, last_sr


def list_rows(list_html):
    """institute code -> {name, status, intake} as printed on the list page."""
    out = {}
    for t in tables(list_html):
        for row in t:
            if len(row) >= 5 and re.match(r"^\d+\.?$", row[0]) and CODE.match(row[1]): out[row[1]] = {"name": row[2], "status": row[3], "intake": row[4]}
    return out


def parse_summary(html, code):
    """-> (institute dict, [course dicts], [problems]). Never guesses: a label that is missing stays '' and is reported."""
    info, courses, problems = {}, [], []
    for t in tables(html):
        header = None
        for row in t:
            clean = [c.rstrip(":").strip() for c in row]
            if clean and clean[0] == "Choice Code": header = clean; continue
            if header and len(row) == len(header) and CHOICE.match(row[0]):
                rec = {COURSE_COLS[h]: row[i] for i, h in enumerate(header) if h in COURSE_COLS}; courses.append(rec); continue
            for i in range(0, len(clean) - 1, 2):
                if clean[i] in INFO_LABELS and INFO_LABELS[clean[i]] not in info: info[INFO_LABELS[clean[i]]] = row[i + 1]
    for need in ("institute_code", "institute_name", "district"):
        if not info.get(need): problems.append("missing " + need)
    if info.get("institute_code") and info["institute_code"] != code: problems.append("page is for institute %s, asked for %s" % (info["institute_code"], code))
    if not courses: problems.append("no course rows")
    for c in courses:
        if not c["choice_code"].startswith(code): problems.append("course %s does not belong to institute %s" % (c["choice_code"], code))
        if not c.get("total_intake", "").isdigit(): problems.append("intake of %s is not a number: %r" % (c["choice_code"], c.get("total_intake")))
    return info, courses, problems


class Wall(Exception): pass


def looks_like_wall(text):
    low = (text or "").lower()
    return ("captcha" in low or "password" in low and "login" in low) and "institute summary" not in low and "list of institutes" not in low


INST_COLS = ["institute_code", "institute_name", "address", "region", "district", "status", "autonomy_status", "minority_status", "public_remark",
             "total_intake", "admission_year", "source_url", "retrieved_at", "page_sha256"]
COURSE_OUT = ["choice_code", "institute_code", "course_name", "university", "status", "autonomy_status", "minority_status", "shift", "accreditation", "gender", "total_intake",
              "admission_year", "source_url", "retrieved_at"]


def run(fetcher, year, now, base=None):
    """Reads the list and every institute page. Returns (institutes, courses, report). report['complete'] is True only if nothing is missing."""
    host = base or "https://fe%d.mahacet.org" % year
    label = "%d-%02d" % (year, (year + 1) % 100)
    report = {"year": label, "problems": [], "complete": False, "requests": 0}
    lr = fetcher.fetch(host + "/StaticPages/frmInstituteList"); report["requests"] += 1
    if lr.blocked or not lr.ok: report["problems"].append("list page not read: %s" % (lr.blocked or lr.status or lr.error)); return [], [], report
    if looks_like_wall(lr.text): raise Wall("the institute list page asks for a login or CAPTCHA; stopped (nothing is bypassed)")
    codes, printed = institute_codes(lr.text)
    listed = list_rows(lr.text); report.update(codes_found=len(codes), count_printed_on_page=printed); report["warnings"] = []
    if not codes or len(codes) != printed: report["problems"].append("list page: found %d institute codes but the page prints %d" % (len(codes), printed)); return [], [], report
    insts, courses = [], []
    for code in codes:
        url = "%s/StaticPages/frmInstituteSummary.aspx?InstituteCode=%s" % (host, code)
        r = fetcher.fetch(url); report["requests"] += 1
        if r.blocked or not r.ok: report["problems"].append("%s: page not read (%s)" % (code, r.blocked or r.status or r.error)); continue
        if looks_like_wall(r.text): raise Wall("institute page %s asks for a login or CAPTCHA; stopped" % code)
        info, cs, probs = parse_summary(r.text, code)
        if probs: report["problems"] += ["%s: %s" % (code, p) for p in probs]; continue
        sha = hashlib.sha256(r.body).hexdigest()
        main_sum = sum(int(c["total_intake"]) for c in cs if c["choice_code"][-1].isdigit())          # codes with a letter suffix (e.g. 'T') are extra seats
        printed_intake = (listed.get(code) or {}).get("intake", "")
        if printed_intake.isdigit() and int(printed_intake) != main_sum: report["warnings"].append("%s: list page intake %s, course rows without a letter suffix add up to %d" % (code, printed_intake, main_sum))
        insts.append(dict(info, total_intake=printed_intake or main_sum, admission_year=label, source_url=url, retrieved_at=now, page_sha256=sha))
        courses += [dict(c, institute_code=code, admission_year=label, source_url=url, retrieved_at=now) for c in cs]
    report["institutes_read"] = len(insts); report["courses_read"] = len(courses)
    report["complete"] = not report["problems"] and len(insts) == len(codes)
    report["districts"] = {d: sum(1 for i in insts if i["district"] == d) for d in sorted({i["district"] for i in insts})}
    return insts, courses, report


def write(out, insts, courses, report):
    os.makedirs(out, exist_ok=True)
    for name, cols, rows in (("institutes.csv", INST_COLS, insts), ("institute_courses.csv", COURSE_OUT, courses)):
        with open(os.path.join(out, name), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore", lineterminator="\n"); w.writeheader(); w.writerows(rows)
    json.dump(report, open(os.path.join(out, "institutes_report.json"), "w"), indent=1)


def main(argv=None):
    import argparse
    from datetime import datetime, timezone
    from . import plan as P
    a = argparse.ArgumentParser(); a.add_argument("--out", default=os.path.join(ROOT, "data", "normalized", "institutes")); a.add_argument("--year", type=int)
    a.add_argument("--delay", type=float, default=1.0); a = a.parse_args(argv)
    year = a.year or int(P.make_plan(json.load(open(P.DISCOVERY))["admission_year"])["current_year"][:4])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try: insts, courses, rep = run(PoliteFetcher(min_delay=a.delay, max_requests=600), year, now)
    except Wall as e: print("STOPPED:", e); return 2
    print(json.dumps({k: rep.get(k) for k in ("year", "complete", "codes_found", "institutes_read", "courses_read", "requests")}))
    if not rep["complete"]:
        print("NOT COMPLETE - the previous files were kept. First problems:", rep["problems"][:10]); return 1
    write(a.out, insts, courses, rep); print("districts:", rep["districts"]); return 0

if __name__ == "__main__": sys.exit(main())
