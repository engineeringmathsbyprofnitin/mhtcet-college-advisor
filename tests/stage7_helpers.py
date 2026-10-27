"""Shared helpers for the Stage 7 tests: a fake network that serves the HTML fixtures (modelled on the real portal pages)."""
import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "stage7")

def fixture(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f: return f.read()

class Clock:
    def __init__(self): self.t = 1000.0; self.sleeps = []
    def now(self): return self.t
    def sleep(self, s): self.sleeps.append(s); self.t += s

class FakeTransport:
    def __init__(self, routes=None):
        self.routes = dict(routes or {}); self.calls = []
    def send(self, method, url, headers, max_bytes):
        self.calls.append((method, url, dict(headers)))
        r = self.routes.get((method, url), self.routes.get(("*", url)))
        if callable(r): r = r(method, url, headers)
        if isinstance(r, Exception): raise r
        if r is None: r = (404, {}, b"")
        return r
    def urls(self, method=None): return [u for m, u, h in self.calls if method in (None, m)]

HOME = "https://cetcell.mahacet.org/"
CAP26 = "https://cetcell.mahacet.org/cap-_2026-27/"
FE26 = "https://fe2026.mahacet.org/StaticPages/HomePage"
PDF = (200, {"Content-Type": "application/pdf", "Content-Length": "123456", "Last-Modified": "Tue, 20 Oct 2026 10:00:00 GMT", "ETag": '"abc"'}, b"")

def html(s): return (200, {"Content-Type": "text/html"}, s.encode("utf-8"))

def site(over=None):
    """Routes for the whole fake site. Any entry can be overridden by key (method,url)."""
    r = {("GET", HOME): html(fixture("cetcell_home.html")), ("GET", CAP26): html(fixture("cap_2026_27.html")),
         ("GET", FE26): html(fixture("fe2026_home.html"))}
    # every document answers HEAD with 200 by default
    import re
    for m in re.finditer(r'href="(https://[^"]+\.pdf)"', fixture("fe2026_home.html")):
        u = m.group(1)
        if "://fe2026.mahacet.org/" in u:      # behaves like the real server: HEAD says 404 although the file exists; a normal request works
            r[("HEAD", u)] = (404, {"Content-Type": "text/html"}, b"not found")
            r[("GET", u)] = (206, dict(PDF[1], **{"Content-Range": "bytes 0-0/123456"}), b"%")
        else:
            r[("HEAD", u)] = PDF
    r.update(over or {})
    return r
