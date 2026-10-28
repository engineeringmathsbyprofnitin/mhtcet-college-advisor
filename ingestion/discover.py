"""Stage 7: discover the official engineering (B.E./B.Tech) CAP documents and decide the current admission year.

Starts at the CET Cell home page, follows only links it finds (no guessed addresses), reads the CAP menu,
finds each year's engineering portal, classifies the cutoff / vacancy / seat-matrix documents, checks that the
files are reachable (HEAD only, nothing is downloaded yet) and writes a JSON report.
Discovering a link is NOT the same as downloading and parsing the file; that is Stage 8 and 9.

Run from the repository root:   python -m ingestion.discover --out data/raw/discovery
"""
import argparse, hashlib, json, os, re, sys
from datetime import date, datetime, timezone
from urllib.parse import urlparse

from .admission_year import parse_year_label, decide, label, previous_years, ROUND_ORDER
from .classify import classify
from .html_extract import extract_links
from .http_client import PoliteFetcher, BudgetExceeded, host_allowed

START_URL = "https://cetcell.mahacet.org/"
TOOL_VERSION = "0.1"
KEEP_TYPES = {"cutoff", "vacancy_position", "vacancy_after_cap", "seat_matrix"}
BE_BTECH = re.compile(r"^\s*B\.?\s*E\.?\s*/\s*B\.?\s*Tech\.?\s*$", re.I)
CAPTCHA_WORDS = ("captcha", "recaptcha", "hcaptcha")


def _id(url): return hashlib.sha1(url.encode()).hexdigest()[:12]


def _obstacle(resp):
    """Return (kind, detail) when the page itself is a wall we must respect; otherwise None."""
    if resp.blocked: return resp.blocked, "not fetched"
    if resp.status is None: return "network_error", resp.error or "no response"
    if resp.status in (401,): return "login_required", "HTTP 401"
    if resp.status == 403: return "forbidden", "HTTP 403"
    if resp.status == 429: return "rate_limited", "HTTP 429"
    if resp.status >= 400: return "http_error", "HTTP %d" % resp.status
    return None


def _wall_in_page(html, n_useful_links):
    low = html.lower()
    if "this content is password-protected" in low: return "password_protected"
    if n_useful_links == 0 and any(w in low for w in CAPTCHA_WORDS): return "captcha"
    if n_useful_links == 0 and re.search(r"<input[^>]+type=[\"']?password", low): return "login_required"
    return None


def _cap_menu_years(links):
    out = {}
    for l in links:
        parent = l["menu_path"][-1].strip().lower() if l["menu_path"] else ""
        y = parse_year_label(l["text"])
        if parent == "cap" and y: out.setdefault(y, l["href"])
    return out


def _engineering_portal(links):
    cands = [l for l in links if BE_BTECH.match(l["text"] or "")]
    if cands: return cands[0]["href"], [c["href"] for c in cands[1:]], "link text 'B.E/ B.Tech'"
    hostm = [l for l in links if re.match(r"^fe\d{4}\.", urlparse(l["href"]).netloc.lower())]
    if hostm: return hostm[0]["href"], [], "host name fe<year> (link text not recognised)"
    return None, [], None


def run_discovery(fetcher, today=None, verify=True, history=3, start_url=START_URL, now=None):
    today = today or date.today()
    now = now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rep = {"schema_version": 1, "tool_version": TOOL_VERSION, "generated_at": now, "start_url": start_url, "status": "ok",
           "menu": {"found": False, "cap_years": {}}, "portals": {}, "documents": [], "obstacles": [], "warnings": [], "notes": []}
    docs, seen = [], set()

    def obstacle(url, kind, detail):
        rep["obstacles"].append({"url": url, "kind": kind, "detail": detail})

    def page(url):
        r = fetcher.fetch(url)
        ob = _obstacle(r)
        if ob: obstacle(url, *ob); return None, []
        links = extract_links(r.text, r.url)
        wall = _wall_in_page(r.text, len([l for l in links if host_allowed(urlparse(l["href"]).netloc)]))
        if wall: obstacle(url, wall, "page needs a password / login / CAPTCHA: stopped, nothing bypassed"); return None, []
        return r, links

    try:
        r, links = page(start_url)
        if r is None:
            rep["status"] = "failed"; rep["admission_year"] = decide({"menu_years": [], "docs": []}, today, history); return _finish(rep, fetcher)
        cap = _cap_menu_years(links)
        if not cap:                                  # menu layout changed: fall back to any link that looks like a CAP year page
            for l in links:
                y = parse_year_label(l["text"])
                if y and re.search(r"cap|admission", (l["href"] + " " + l["text"]).lower()): cap.setdefault(y, l["href"])
            if cap: rep["warnings"].append("The CAP menu was not found in its usual place; years were taken from other links. Check the site layout.")
        rep["menu"] = {"found": bool(cap), "cap_years": {label(y): u for y, u in sorted(cap.items(), reverse=True)}}
        if not cap:
            rep["status"] = "failed"; obstacle(start_url, "layout_changed", "no CAP year links found on the home page")
            rep["admission_year"] = decide({"menu_years": [], "docs": []}, today, history); return _finish(rep, fetcher)

        def read_year(y):
            """Finds the engineering portal for admission year y and collects its documents."""
            if y not in cap or label(y) in rep["portals"]: return
            cr, clinks = page(cap[y])
            if cr is None: return
            url, alts, how = _engineering_portal(clinks)
            entry = {"cap_page": cap[y], "portal_url": url, "found_by": how, "alternatives": alts}
            rep["portals"][label(y)] = entry
            if not url: rep["warnings"].append("No engineering (B.E/B.Tech) portal link found on the %s CAP page." % label(y)); return
            pr, plinks = page(url)
            if pr is None: return
            entry["fetched"] = True
            for l in plinks:
                tbl = l.get("table") or {}
                ctx = {"row_label": tbl.get("row_label", ""), "col_headers": tbl.get("col_headers", []), "heading": l.get("heading", "")}
                c = classify(l["text"], l["href"], ctx, portal_year=y)
                if c["doc_type"] not in KEEP_TYPES or not c["is_file"] or l["href"] in seen: continue
                seen.add(l["href"])
                docs.append(dict(id=_id(l["href"]), url=l["href"], link_text=l["text"], source_page=url, table=tbl or None,
                                 course="engineering", portal_year=label(y), verification=None, **c))

        years = sorted(cap, reverse=True)
        read_year(years[0])
        cur = max([d["year"] for d in docs if d["doc_type"] == "cutoff" and d["year"]] or [years[0]])
        for py in previous_years(cur, history):          # only fetch an older portal if the current one did not list that year
            if not any(d["year"] == py and d["doc_type"] == "cutoff" for d in docs): read_year(py)

        def check(d):
            if not d["is_file"] or not host_allowed(urlparse(d["url"]).netloc): return
            r = fetcher.head_check(d["url"])
            if r.blocked: d["verification"] = {"reachable": None, "note": r.blocked}; return
            st = r.status
            reach = True if (r.ok or st == 206) else (False if (st is not None and 400 <= st < 500 and st != 429) else None)   # None = could not tell (server trouble)
            cl, cr = r.headers.get("content-length"), r.headers.get("content-range", "")
            m = re.search(r"/(\d+)\s*$", cr)
            size = int(m.group(1)) if m else (int(cl) if (st == 200 and cl and cl.isdigit()) else None)    # a 206 one-byte probe reports 1 byte in Content-Length; the real size is in Content-Range
            d["verification"] = {"reachable": reach, "status": st, "content_type": r.headers.get("content-type"), "size_bytes": size, "content_length": cl,
                                 "last_modified": r.headers.get("last-modified"), "etag": r.headers.get("etag")}

        if verify:
            for d in docs: check(d)
            for py in previous_years(cur, history):      # listed files that do not open: look for the same year's own pages for another route
                mine = [d for d in docs if d["year"] == py and d["doc_type"] == "cutoff"]
                if mine and all((d["verification"] or {}).get("reachable") is False for d in mine):
                    before = len(docs); read_year(py)
                    for d in docs[before:]: check(d)
    except BudgetExceeded as e:
        obstacle("", "request_budget_exhausted", str(e)); rep["status"] = "partial"

    ev = {"menu_years": list(cap), "docs": [{"year": d["year"], "doc_type": d["doc_type"], "cap_round": d["cap_round"], "scope": d["scope"],
                                           "supplementary": d["supplementary"], "reachable": (d["verification"] or {}).get("reachable")} for d in docs]}
    rep["documents"] = docs
    rep["admission_year"] = decide(ev, today, history)
    rep["matrix"] = _matrix(docs)
    rep["selection_preview"] = _preview(docs, rep["admission_year"])
    notes = rep["notes"]
    if any(d["doc_type"] == "vacancy_after_cap" for d in docs):
        notes.append("A 'vacant seats after CAP' (ACAP) list exists. It is recorded separately and is NOT used as a CAP Round IV vacancy position. Owner to confirm this reading in Stage 11.")
    if any(d["supplementary"] for d in docs):
        notes.append("Supplementary vacancy lists (new institutes / court orders) exist. They are kept apart from the main round lists.")
    if any(d["scope"] == "DIPLOMA" for d in docs):
        notes.append("Diploma-holder cutoff lists exist. They are not used for first-year admissions unless the owner decides otherwise.")
    if rep["obstacles"] and rep["status"] == "ok": rep["status"] = "partial"
    if rep["admission_year"]["current_start_year"] is None: rep["status"] = "failed"
    return _finish(rep, fetcher)


def _finish(rep, fetcher):
    rep["requests_made"] = fetcher.count
    rep["request_log"] = fetcher.log
    rep["robots"] = dict(fetcher.robots_state)
    return rep


def _usable(d):
    return (d.get("verification") or {}).get("reachable") is not False


def _matrix(docs):
    m = {}
    for d in docs:
        if not d["year"] or not _usable(d): continue
        y = m.setdefault(d["year_label"], {"cutoff": {}, "vacancy_position": [], "vacancy_after_cap": False, "seat_matrix": False})
        if d["doc_type"] == "cutoff" and d["cap_round"]:
            rs = y["cutoff"].setdefault(d["scope"] or "unknown", [])
            if d["cap_round"] not in rs: rs.append(d["cap_round"]); rs.sort(key=ROUND_ORDER.index)
        elif d["doc_type"] == "vacancy_position" and d["cap_round"] and not d["supplementary"]:
            if d["cap_round"] not in y["vacancy_position"]: y["vacancy_position"].append(d["cap_round"]); y["vacancy_position"].sort(key=ROUND_ORDER.index)
        elif d["doc_type"] == "vacancy_after_cap": y["vacancy_after_cap"] = True
        elif d["doc_type"] == "seat_matrix": y["seat_matrix"] = True
    return dict(sorted(m.items(), reverse=True))


def _preview(docs, ay):
    """What the later stages would pick, using the strict rules (shown here so the owner can check them)."""
    cy = ay.get("current_start_year")
    if cy is None: return None
    def pick(doc_type, rnd, scope=None):
        c = [d for d in docs if _usable(d) and d["year"] == cy and d["doc_type"] == doc_type and d["cap_round"] == rnd and not d["supplementary"] and (scope is None or d["scope"] == scope)]
        return [{"url": d["url"], "scope": d["scope"], "qualifiers": d["qualifiers"]} for d in c]
    out = {"year": label(cy), "cutoff_round_used": ay.get("latest_cutoff_round"), "cutoff_documents": {}, "vacancy_round_used": ay.get("vacancy_round"), "vacancy_documents": []}
    for scope in ("MH", "AI"):
        for rnd in reversed(ROUND_ORDER):
            p = pick("cutoff", rnd, scope)
            if p: out["cutoff_documents"][scope] = {"round": rnd, "documents": p}; break
    if ay.get("vacancy_round"): out["vacancy_documents"] = pick("vacancy_position", ay["vacancy_round"])
    return out


def render_markdown(rep):
    ay, L = rep.get("admission_year", {}), []
    L.append("## Source discovery report")
    L.append("Status: **%s**. Requests made: %s." % (rep["status"], rep.get("requests_made")))
    L.append("")
    L.append("**Current admission year:** %s (%s)" % (ay.get("current_label") or "not established", ay.get("status")))
    for w in ay.get("warnings", []): L.append("- Warning: " + w)
    L.append("")
    if rep.get("matrix"):
        L.append("| Year | Cutoff rounds found | Vacancy positions | Seat matrix | ACAP list |"); L.append("|---|---|---|---|---|")
        for y, v in rep["matrix"].items():
            cut = "; ".join("%s: %s" % (s, ",".join(r)) for s, r in sorted(v["cutoff"].items())) or "none"
            L.append("| %s | %s | %s | %s | %s |" % (y, cut, ",".join(v["vacancy_position"]) or "none", "yes" if v["seat_matrix"] else "no", "yes" if v["vacancy_after_cap"] else "no"))
        L.append("")
    sp = rep.get("selection_preview")
    if sp: L.append("**Would use for %s:** cutoff round %s; vacancy round %s." % (sp["year"], sp["cutoff_round_used"], sp["vacancy_round_used"] or "none (vacancy data unavailable)"))
    unreachable = [d for d in rep.get("documents", []) if (d.get("verification") or {}).get("reachable") is False]
    L.append("Documents found: %d; unreachable: %d." % (len(rep.get("documents", [])), len(unreachable)))
    for o in rep.get("obstacles", []): L.append("- OBSTACLE %s at %s: %s" % (o["kind"], o["url"], o["detail"]))
    for n in rep.get("notes", []): L.append("- Note: " + n)
    for w in rep.get("warnings", []): L.append("- Warning: " + w)
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="data/raw/discovery"); ap.add_argument("--today"); ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--max-requests", type=int, default=150); ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--github-summary", action="store_true", help="also append the readable summary to the GitHub run page (only the real run uses this)")
    a = ap.parse_args(argv)
    today = date.fromisoformat(a.today) if a.today else date.today()
    rep = run_discovery(PoliteFetcher(min_delay=a.delay, max_requests=a.max_requests), today, verify=not a.no_verify)
    os.makedirs(a.out, exist_ok=True)
    text = json.dumps(rep, indent=1, ensure_ascii=False, sort_keys=True)
    if rep["status"] == "failed":                       # keep the last good report; store the failure separately
        open(os.path.join(a.out, "last_failed.json"), "w", encoding="utf-8").write(text)
    else:
        open(os.path.join(a.out, "latest.json"), "w", encoding="utf-8").write(text)
        open(os.path.join(a.out, "%s.json" % today.isoformat()), "w", encoding="utf-8").write(text)
    md = render_markdown(rep); print(md)
    summ = os.environ.get("GITHUB_STEP_SUMMARY") if a.github_summary else None
    if summ: open(summ, "a", encoding="utf-8").write(md + "\n")
    return 0 if rep["status"] != "failed" else 2


if __name__ == "__main__":
    sys.exit(main())
