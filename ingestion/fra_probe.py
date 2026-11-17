"""Stage 12a-1: PROBE of the official Fees Regulating Authority (FRA) fee search page. Reads nothing permanently; reports how the page works.

Page (public, seen by the owner in a browser, no login/CAPTCHA): https://ay26-27.mahafraportal.org/ssi_prp_25/outer.php?q=fee_search_report
Form: Institute Type (H&T) / Sub Type (ENGG - Bachelor of Engineering) / District, button 'Get Report'; table columns: Inst ID, Inst Name, District, Stream,
Status, Date of Meeting, Tuition Fee, Development Fee, Total Fee.
This probe: obeys robots.txt (official host list now includes mahafraportal.org), stops at any login/CAPTCHA (never bypasses), sends at most 3 requests
(robots.txt, the page, ONE test search for Mumbai-City) and writes what it saw to data/raw/fees-probe/ so the real reader can be written on facts.
"""
import json, os, re, sys
from html.parser import HTMLParser
from urllib.parse import urljoin, urlencode
from ingestion.http_client import PoliteFetcher

PAGE = "https://ay26-27.mahafraportal.org/ssi_prp_25/outer.php?q=fee_search_report"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw", "fees-probe")
WALL = re.compile(r"captcha|recaptcha|type=.?password|please log ?in|sign ?in to", re.I)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.forms, self.tables, self.scripts, self.inline = [], [], [], []
        self._form = self._sel = self._opt = self._tab = self._row = self._cell = self._scr = None

    def handle_starttag(self, t, a):
        a = {k: (v or "") for k, v in a}
        if t == "form": self._form = dict(action=a.get("action", ""), method=(a.get("method") or "GET").upper(), id=a.get("id", ""), fields=[]); self.forms.append(self._form)
        elif t == "input" and self._form is not None: self._form["fields"].append(dict(kind="input", name=a.get("name", ""), type=a.get("type", "text"), value=a.get("value", "")))
        elif t == "select":
            self._sel = dict(kind="select", name=a.get("name", ""), id=a.get("id", ""), options=[])
            (self._form["fields"] if self._form is not None else self.forms.append(dict(action="", method="(no form)", id="", fields=[])) or self.forms[-1]["fields"]).append(self._sel)
        elif t == "option" and self._sel is not None: self._opt = dict(value=a.get("value", ""), text="", selected="selected" in a); self._sel["options"].append(self._opt)
        elif t == "table": self._tab = []; self.tables.append(self._tab)
        elif t == "tr" and self._tab is not None: self._row = []; self._tab.append(self._row)
        elif t in ("td", "th") and self._row is not None: self._cell = []
        elif t == "script": self._scr = []; self.scripts.append(a.get("src", ""))

    def handle_endtag(self, t):
        if t == "form": self._form = None
        elif t == "select": self._sel = None
        elif t == "option": self._opt = None
        elif t in ("td", "th") and self._cell is not None and self._row is not None: self._row.append(" ".join("".join(self._cell).split())); self._cell = None
        elif t == "table": self._tab = self._row = None
        elif t == "script" and self._scr is not None:
            txt = "".join(self._scr).strip()
            if txt: self.inline.append(txt)
            self._scr = None

    def handle_data(self, d):
        if self._opt is not None: self._opt["text"] += d
        if self._cell is not None: self._cell.append(d)
        if self._scr is not None: self._scr.append(d)


def parse(html):
    p = Page(); p.feed(html); return p


def pick(select, wanted):
    for o in select["options"]:
        if wanted(o["text"].strip()): return o
    return None


def script_hints(inline):
    out = []
    for s in inline:
        for ln in s.splitlines():
            if re.search(r"ajax|fetch\(|XMLHttpRequest|\$\.(get|post)|\.php", ln, re.I): out.append(ln.strip()[:200])
    return out[:25]


def run(fetcher=None, out_dir=OUT, page_url=PAGE):
    f = fetcher or PoliteFetcher(min_delay=2.0, max_requests=6)
    os.makedirs(out_dir, exist_ok=True)
    rep = dict(page=page_url, steps=[], verdict="")
    r = f.fetch(page_url)
    rep["robots"] = f.robots_state.get(re.match(r"https?://([^/]+)", page_url).group(1).lower())
    rep["steps"].append(dict(step="page", status=r.status, blocked=r.blocked, error=r.error, bytes=len(r.body)))
    if r.blocked or not r.ok: rep["verdict"] = "STOP: page not readable (%s %s)" % (r.blocked, r.status); return _save(rep, out_dir)
    html = r.text; open(os.path.join(out_dir, "page.html"), "w", encoding="utf-8").write(html[:400_000])
    if WALL.search(html): rep["verdict"] = "STOP: the page mentions a login or CAPTCHA; nothing was submitted and nothing is bypassed"; return _save(rep, out_dir)
    pg = parse(html)
    rep["forms"] = pg.forms; rep["script_files"] = pg.scripts; rep["script_hints"] = script_hints(pg.inline); rep["tables_on_page"] = [len(t) for t in pg.tables]
    form = next((fm for fm in pg.forms if any(fl["kind"] == "select" for fl in fm["fields"])), None)
    if form is None: rep["verdict"] = "No form with selection boxes found in the HTML (the form may be built by JavaScript): see script_hints"; return _save(rep, out_dir)
    selects = [fl for fl in form["fields"] if fl["kind"] == "select"]
    payload, chosen = [], {}
    for fl in form["fields"]:
        if fl["kind"] == "input" and fl["name"] and fl["type"] not in ("submit", "button", "image", "reset"): payload.append((fl["name"], fl["value"]))
    for fl in selects:
        want = (lambda t: "H&T" in t) if any("H&T" in o["text"] for o in fl["options"]) else (lambda t: t.upper().startswith("ENGG")) if any(o["text"].upper().startswith("ENGG") for o in fl["options"]) else (lambda t: t.lower().startswith("mumbai-city")) if any(o["text"].lower().startswith("mumbai-city") for o in fl["options"]) else None
        o = pick(fl, want) if want else None
        if o is None: o = next((x for x in fl["options"] if x["selected"]), None)
        if o is not None: payload.append((fl["name"], o["value"])); chosen[fl["name"] or fl["id"]] = o["text"].strip()
    rep["test_search"] = dict(chosen=chosen, method=form["method"], action=urljoin(page_url, form["action"] or page_url), payload=payload)
    if not any("ENGG" in v.upper() for v in chosen.values()) or not any("mumbai" in v.lower() for v in chosen.values()):
        rep["verdict"] = "Form found but the Sub Type / District options are not in the HTML (probably loaded by JavaScript): no test search sent"; return _save(rep, out_dir)
    url = rep["test_search"]["action"]
    if form["method"] == "POST": r2 = f.fetch(url, "POST", headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": page_url}, data=urlencode(payload).encode())
    else: r2 = f.fetch(url + ("&" if "?" in url else "?") + urlencode(payload))
    rep["steps"].append(dict(step="test_search", status=r2.status, blocked=r2.blocked, error=r2.error, bytes=len(r2.body)))
    if r2.blocked or not r2.ok: rep["verdict"] = "Test search failed: %s %s" % (r2.blocked, r2.status); return _save(rep, out_dir)
    open(os.path.join(out_dir, "test_search.html"), "w", encoding="utf-8").write(r2.text[:600_000])
    if WALL.search(r2.text): rep["verdict"] = "STOP: the answer mentions a login or CAPTCHA"; return _save(rep, out_dir)
    pr = parse(r2.text); best = max(pr.tables, key=len, default=[])
    rep["result_table"] = dict(rows=len(best), header=best[0] if best else None, first_rows=best[1:4], last_row=best[-1] if len(best) > 1 else None)
    rep["verdict"] = "Test search answered: %d table rows" % len(best)
    return _save(rep, out_dir)


def _save(rep, out_dir):
    with open(os.path.join(out_dir, "probe_report.json"), "w", encoding="utf-8") as fh: json.dump(rep, fh, indent=1, ensure_ascii=False)
    return rep


def main():
    rep = run()
    print(rep["verdict"]); print(json.dumps({k: v for k, v in rep.items() if k in ("robots", "steps", "test_search", "result_table")}, indent=1, ensure_ascii=False)[:3500])
    return 0 if not rep["verdict"].startswith("STOP") and not rep["verdict"].startswith("Test search failed") else 1


if __name__ == "__main__":
    sys.exit(main())
