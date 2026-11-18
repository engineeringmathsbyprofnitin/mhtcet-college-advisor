"""Stage 12b-1: PROBE of the official National Board of Accreditation (NBA) accredited-programs pages (www.nbaind.org).

Seen by the owner in a browser (no login, no CAPTCHA): Accredited Programs > Engineering > UG Tier I (WA) / UG Tier II / PG / Diploma, with a search form
(State, Program, Institute Name, 'Search'), a 'Click here to Download in Excel' button, and a table: Name of the Institution, Program, Level,
Accreditation Status, Accreditation Period. The page addresses carry long coded values (ID=..&tier=..&name=..), so they must be found from the site's own links.
This probe: obeys robots.txt, stops at any login/CAPTCHA, sends at most 6 requests (robots.txt, Home, up to 2 pages to find the accredited-programs
links, the UG Tier I page) and saves what it saw in data/raw/nba-probe/ so the real reader can be written on facts. It submits no search.
"""
import json, os, re, sys
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from ingestion.http_client import PoliteFetcher
from ingestion.fra_probe import parse, script_hints, WALL

START = "https://www.nbaind.org/Home"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw", "nba-probe")


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.links, self._a = [], None
    def handle_starttag(self, t, a):
        if t == "a": self._a = [dict(a).get("href", ""), ""]
    def handle_data(self, d):
        if self._a is not None: self._a[1] += d
    def handle_endtag(self, t):
        if t == "a" and self._a is not None:
            self.links.append((self._a[0].strip(), " ".join(self._a[1].split()))); self._a = None


def links_of(html, base):
    p = Links(); p.feed(html); out, seen = [], set()
    for h, t in p.links:
        if not h or h.startswith(("#", "javascript:", "mailto:")): continue
        u = urljoin(base, h)
        if urlparse(u).netloc.lower().split(":")[0] not in ("www.nbaind.org", "nbaind.org"): continue
        if (u, t) not in seen: seen.add((u, t)); out.append((u, t))
    return out


def is_program_link(u): return "accreditationprogram" in u.lower()


def best(cands):
    for rx in (r"UG.*Tier\s*I\b.*WA|Tier\s*I\s*\(WA\)", r"Tier\s*I\b", r"UG"):
        for u, t in cands:
            if re.search(rx, t, re.I): return u, t
    return cands[0] if cands else None


def fetch_ok(f, url, rep, step, wall=False):
    r = f.fetch(url); rep["steps"].append(dict(step=step, url=url, status=r.status, blocked=r.blocked, error=r.error, bytes=len(r.body)))
    if r.blocked or not r.ok: rep["verdict"] = "STOP: %s not readable (%s %s)" % (step, r.blocked, r.status); return None
    if wall and WALL.search(r.text): rep["verdict"] = "STOP: %s mentions a login or CAPTCHA; nothing is bypassed" % step; return None
    return r


def run(fetcher=None, out_dir=OUT, start=START):
    f = fetcher or PoliteFetcher(min_delay=2.0, max_requests=8)
    os.makedirs(out_dir, exist_ok=True); rep = dict(start=start, steps=[], verdict="")
    r = fetch_ok(f, start, rep, "home")
    rep["robots"] = f.robots_state.get(urlparse(start).netloc.lower())
    if r is None: return _save(rep, out_dir)
    open(os.path.join(out_dir, "home.html"), "w", encoding="utf-8").write(r.text[:400_000])
    rep["login_words_on_home"] = bool(WALL.search(r.text))          # only noted: a login link on the home page is not a wall in front of the public list
    links = links_of(r.text, start); rep["home_links_with_accredited"] = [l for l in links if re.search(r"ccredit", l[0] + l[1], re.I)][:40]
    cands = [l for l in links if is_program_link(l[0])]
    hop = 0
    while not cands and hop < 2:
        nxt = [l for l in links if re.search(r"ccredit", l[0] + l[1], re.I) and not re.search(r"\.(pdf|xlsx?|docx?|zip)(\?|$)", l[0], re.I)]
        nxt = [l for l in nxt if l[0] not in {s["url"] for s in rep["steps"]}][:1]
        if not nxt: break
        r1 = fetch_ok(f, nxt[0][0], rep, "hop%d" % (hop + 1))
        if r1 is None: return _save(rep, out_dir)
        links = links_of(r1.text, nxt[0][0]); cands = [l for l in links if is_program_link(l[0])]; hop += 1
    rep["program_links"] = cands[:40]
    pick = best(cands)
    if not pick: rep["verdict"] = "No accredited-programs link (accreditationprogram...) found in the HTML: the menu may be built by JavaScript; see home_links_with_accredited"; return _save(rep, out_dir)
    rep["picked"] = dict(url=pick[0], text=pick[1])
    r2 = fetch_ok(f, pick[0], rep, "program_page", wall=True)     # the data page itself: a login/CAPTCHA here is a wall
    if r2 is None: return _save(rep, out_dir)
    open(os.path.join(out_dir, "program_page.html"), "w", encoding="utf-8").write(r2.text[:800_000])
    pg = parse(r2.text)
    rep["forms"] = [dict(action=fm["action"], method=fm["method"], id=fm["id"], fields=[dict(kind=x["kind"], name=x["name"], type=x.get("type", ""), options=len(x.get("options", [])) if x["kind"] == "select" else None,
                        first_options=[o["text"].strip() for o in x.get("options", [])[:6]] if x["kind"] == "select" else None) for x in fm["fields"]]) for fm in pg.forms]
    rep["script_files"] = pg.scripts; rep["script_hints"] = script_hints(pg.inline)
    rep["excel_hints"] = [ln.strip()[:240] for ln in r2.text.splitlines() if re.search(r"excel|\.xls|export", ln, re.I)][:15]
    rep["tables"] = [dict(rows=len(t), header=t[0] if t else None, first_row=t[1] if len(t) > 1 else None) for t in pg.tables[:5]]
    rep["page_links_with_accredited"] = [l for l in links_of(r2.text, pick[0]) if is_program_link(l[0])][:40]
    rep["verdict"] = "Page read: %d form(s), %d table(s), %d Excel hint(s)" % (len(pg.forms), len(pg.tables), len(rep["excel_hints"]))
    return _save(rep, out_dir)


def _save(rep, out_dir):
    with open(os.path.join(out_dir, "probe_report.json"), "w", encoding="utf-8") as fh: json.dump(rep, fh, indent=1, ensure_ascii=False)
    return rep


def main():
    try: rep = run()
    except Exception as e:                                        # always leave a report that can be read afterwards
        import traceback
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, "probe_report.json"), "w", encoding="utf-8") as fh: json.dump(dict(verdict="unexpected error: %s: %s" % (type(e).__name__, e), trace=traceback.format_exc()[-3000:]), fh, indent=1)
        print("FAIL: unexpected error: %s: %s" % (type(e).__name__, e)); return 1
    print(rep["verdict"]); print(json.dumps({k: rep.get(k) for k in ("robots", "steps", "picked", "tables")}, indent=1, ensure_ascii=False)[:3000])
    return 1 if rep["verdict"].startswith("STOP") else 0


if __name__ == "__main__":
    sys.exit(main())
