"""Stage 8 test helpers: a fake CET Cell that serves PDFs, with per-file bodies, ETags and Range/HEAD behaviour like the real servers."""
import hashlib, os, re, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage7_helpers import *
from datetime import date
from ingestion import discover as D
from ingestion.http_client import PoliteFetcher

PDF_URLS = re.findall(r'href="(https://[^"]+\.pdf)"', fixture("fe2026_home.html"))
NOW = "2026-10-28T09:00:00Z"
U1 = [x for x in PDF_URLS if x.endswith("2026ENGG_CAP4_MH_CutOff.pdf")][0]       # files that ARE selected for download
U2 = [x for x in PDF_URLS if x.endswith("2026ENGG_CAP3_AI_CutOff.pdf")][0]
U3 = [x for x in PDF_URLS if x.endswith("2026ENGG_CAP4_AI_CutOff.pdf")][0]

class Docs:
    """The 'files on the server'. Change .version[url] to simulate the CET Cell replacing a file."""
    def __init__(self): self.version, self.body_override, self.etag_override, self.status = {}, {}, {}, {}
    def v(self, u): return self.version.get(u, 1)
    def body(self, u):
        if u in self.body_override: return self.body_override[u]
        return b"%PDF-1.7\n" + ("%s#v%d" % (u, self.v(u))).encode() + b"\n" + b"x" * 700 + b"\n%%EOF\n"
    def etag(self, u): return self.etag_override.get(u) or '"%s-v%d"' % (hashlib.sha1(u.encode()).hexdigest()[:8], self.v(u))
    def headers(self, u, body=None):
        b = self.body(u) if body is None else body
        return {"Content-Type": "application/pdf", "Content-Length": str(len(self.body(u))), "ETag": self.etag(u), "Last-Modified": "Tue, 20 Oct 2026 10:00:00 GMT"}

def routes(docs, extra=None):
    r = site()
    for u in PDF_URLS:
        blob = "blob.core.windows.net" in u
        def head(m, url, h, u=u, blob=blob):
            return (200, docs.headers(u), b"") if blob else (404, {"Content-Type": "text/html"}, b"nf")
        def get(m, url, h, u=u):
            st = docs.status.get(u)
            if st: return st
            if "Range" in h: return (206, dict(docs.headers(u), **{"Content-Range": "bytes 0-0/%d" % len(docs.body(u)), "Content-Length": "1"}), b"%")
            if h.get("If-None-Match") and h["If-None-Match"] == docs.etag(u): return (304, {}, b"")
            return (200, docs.headers(u), docs.body(u))
        r[("HEAD", u)] = head; r[("GET", u)] = get
    r.update(extra or {})
    return r

def make_report(docs, extra=None, today=date(2026, 10, 28)):
    c = Clock(); f = PoliteFetcher(FakeTransport(routes(docs, extra)), sleep=c.sleep, clock=c.now)
    return D.run_discovery(f, today, now=NOW)

def new_fetcher(docs, extra=None, **kw):
    c = Clock(); tr = FakeTransport(routes(docs, extra)); return PoliteFetcher(tr, sleep=c.sleep, clock=c.now, **kw), tr

def tmpdir(): return tempfile.mkdtemp()
