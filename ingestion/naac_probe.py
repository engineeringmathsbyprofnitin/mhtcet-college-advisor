"""Stage 12c-1: PROBE of the official National Assessment and Accreditation Council (NAAC) site (www.naac.gov.in) to find the current list of accredited institutions
with their grade (CGPA, letter grade) and validity date.

Why a probe: nothing about the current NAAC files is known yet (the old Excel lists are from 2020 and 2022; third-party websites are not official). This probe obeys robots.txt,
stops at a login/CAPTCHA, sends at most 10 requests (robots.txt, home page, up to 2 pages to find the accreditation / institutions links, then only a HEAD/first-byte check of
up to 4 candidate Excel/PDF files) and saves what it saw in data/raw/naac-probe/ so the real reader can be written on facts. It downloads no list, submits no form and bypasses nothing.
If the site cannot be read from GitHub (blocked, timeout), the report says so and the owner downloads the list by hand instead.
"""
import json, os, re, sys
from urllib.parse import urljoin, urlparse
from ingestion.http_client import PoliteFetcher, host_allowed
from ingestion.fra_probe import WALL
from ingestion.nba_probe import Links

START = "https://www.naac.gov.in/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw", "naac-probe")
# Old official file addresses cited publicly (2020 and 2022 editions): only checked for existence/date, to see whether NAAC keeps lists at this kind of address.
KNOWN = ["http://naac.gov.in/images/docs/ACCREDITATION_STATUS/Institutions_accredited_by_NAAC_whose_accreditation_period_is_valid_030622nn.xls"]
FILE_RX = re.compile(r"\.(xlsx?|pdf|csv)(\?|$)", re.I)
TOPIC_RX = re.compile(r"accredit|valid|institution|outcome|result|status|grade|cgpa", re.I)


def links_of(html, base):
    p = Links(); p.feed(html); out, seen = [], set()
    for h, t in p.links:
        if not h or h.startswith(("#", "javascript:", "mailto:", "tel:")): continue
        u = urljoin(base, h).split("#")[0]
        if (u, t) not in seen: seen.add((u, t)); out.append((u, t))
    return out


def fetch_ok(f, url, rep, step, wall=False):
    r = f.fetch(url); rep["steps"].append(dict(step=step, url=url, status=r.status, blocked=r.blocked, error=r.error, bytes=len(r.body)))
    if r.blocked or not r.ok: rep["verdict"] = "STOP: %s not readable (blocked=%s status=%s error=%s)" % (step, r.blocked, r.status, r.error); return None
    if wall and WALL.search(r.text): rep["verdict"] = "STOP: %s mentions a login or CAPTCHA; nothing is bypassed" % step; return None
    return r


def is_page_link(u, t):
    return host_allowed(urlparse(u).netloc) and not FILE_RX.search(u) and bool(re.search(r"accredit|assessment|outcome|institution|status", u + " " + t, re.I))


def run(fetcher=None, out_dir=OUT, start=START):
    f = fetcher or PoliteFetcher(min_delay=2.0, max_requests=10)
    os.makedirs(out_dir, exist_ok=True); rep = dict(start=start, steps=[], verdict="", file_candidates=[], other_hosts_seen=[])
    r = fetch_ok(f, start, rep, "home"); rep["robots"] = f.robots_state.get(urlparse(start).netloc.lower())
    if r is None: return _save(rep, out_dir)
    open(os.path.join(out_dir, "home.html"), "w", encoding="utf-8").write(r.text[:400_000])
    links = links_of(r.text, start); pages = {start: links}; hop = 0
    cand = [l for l in links if is_page_link(*l)]
    rep["home_links_on_topic"] = cand[:40]
    seen_pages = {start}
    while hop < 2:
        nxt = [l for l in cand if l[0] not in seen_pages][:1]
        if not nxt: break
        seen_pages.add(nxt[0][0]); r1 = fetch_ok(f, nxt[0][0], rep, "hop%d" % (hop + 1), wall=True)
        if r1 is None:
            if "login or CAPTCHA" in rep["verdict"]: return _save(rep, out_dir)            # a wall: stop, nothing is bypassed
            rep.setdefault("notes", []).append(rep["verdict"].replace("STOP: ", "side page skipped: ")); rep["verdict"] = ""; break     # one unreadable side page does not end the probe
        open(os.path.join(out_dir, "hop%d.html" % (hop + 1)), "w", encoding="utf-8").write(r1.text[:600_000])
        ls = links_of(r1.text, nxt[0][0]); pages[nxt[0][0]] = ls; cand = [l for l in cand + [x for x in ls if is_page_link(*x)] if l[0] not in seen_pages]; hop += 1
    allp = [(u, t, src) for src, ls in pages.items() for u, t in ls]
    rep["other_hosts_seen"] = sorted({urlparse(u).netloc.lower() for u, t, s in allp if urlparse(u).scheme in ("http", "https")})[:25]
    files = []; seen = set()
    for u, t, src in allp:
        if FILE_RX.search(u) and TOPIC_RX.search(u + " " + t) and u not in seen: seen.add(u); files.append(dict(url=u, text=t, found_on=src))
    for k in KNOWN:
        if k not in seen: files.append(dict(url=k, text="(address cited publicly, 2022 edition)", found_on="known"))
    files.sort(key=lambda x: (x["found_on"] == "known", not re.search(r"valid|accredited", x["url"] + x["text"], re.I)))
    for c in files[:4]:                                              # HEAD / first byte only: nothing is downloaded
        h = f.head_check(c["url"]); c.update(status=h.status, blocked=h.blocked, content_type=h.headers.get("content-type"), content_length=h.headers.get("content-length"), last_modified=h.headers.get("last-modified"))
        rep["steps"].append(dict(step="check_file", url=c["url"], status=h.status, blocked=h.blocked, error=h.error))
    rep["file_candidates"] = files[:12]
    reachable = [c for c in files[:4] if c.get("status") and 200 <= c["status"] < 300]
    rep["verdict"] = "Site read: %d candidate file link(s), %d reachable (checked without downloading)" % (len(files), len(reachable))
    return _save(rep, out_dir)


def _save(rep, out_dir):
    with open(os.path.join(out_dir, "probe_report.json"), "w", encoding="utf-8") as fh: json.dump(rep, fh, indent=1, ensure_ascii=False)
    return rep


def main():
    try: rep = run()
    except Exception as e:                                            # always leave a report that can be read afterwards
        import traceback
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, "probe_report.json"), "w", encoding="utf-8") as fh: json.dump(dict(verdict="unexpected error: %s: %s" % (type(e).__name__, e), trace=traceback.format_exc()[-3000:]), fh, indent=1)
        print("FAIL: unexpected error: %s: %s" % (type(e).__name__, e)); return 1
    print(rep["verdict"]); print(json.dumps({k: rep.get(k) for k in ("robots", "steps", "file_candidates", "other_hosts_seen")}, indent=1, ensure_ascii=False)[:4000])
    return 1 if rep["verdict"].startswith("STOP") else 0


if __name__ == "__main__":
    sys.exit(main())
