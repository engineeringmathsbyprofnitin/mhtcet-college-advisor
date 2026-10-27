"""A careful, polite web client for official sources (standard library only).

Rules it enforces (all testable without a network):
  * only talks to an allow-list of official hosts; redirects to other hosts are NOT followed (e.g. to a login server)
  * reads robots.txt first and obeys it; if robots.txt cannot be read because of a server error it assumes 'not allowed'
  * waits between requests to the same host, keeps a hard cap on the total number of requests
  * retries only temporary failures (timeouts, 429, 5xx), at most twice, honouring Retry-After
  * never tries to get past CAPTCHAs, logins or passwords (that is decided by the caller, which stops)
"""
import re
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse, urljoin
from urllib import robotparser

USER_AGENT = "MHTCETCollegeAdvisorBot/0.1 (educational project; reads public CAP documents; contact via the project's GitHub repository)"
ALLOWED_HOST_PATTERNS = [r"^([a-z0-9-]+\.)*mahacet\.org$", r"^([a-z0-9-]+\.)*mahacet\.org\.in$", r"^cappublicdocs\d{4}\.blob\.core\.windows\.net$"]
TRANSIENT = {429, 500, 502, 503, 504}


def host_allowed(host):
    host = (host or "").lower().split(":")[0]
    return any(re.match(p, host) for p in ALLOWED_HOST_PATTERNS)


class Response:
    def __init__(self, url, status=None, headers=None, body=b"", error=None, blocked=None):
        self.url, self.status, self.headers = url, status, {k.lower(): v for k, v in (headers or {}).items()}
        self.body, self.error, self.blocked = body, error, blocked      # blocked: why we did not/could not fetch
    @property
    def ok(self): return self.status is not None and 200 <= self.status < 300
    @property
    def text(self): return self.body.decode("utf-8", "replace")


class BudgetExceeded(Exception):
    pass


class UrllibTransport:
    """The only part that touches the network. Never follows redirects by itself."""
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k): return None

    def __init__(self, timeout=25):
        self.timeout = timeout
        self.opener = urllib.request.build_opener(self._NoRedirect)

    def send(self, method, url, headers, max_bytes):
        req = urllib.request.Request(url, method=method, headers=headers)
        try:
            with self.opener.open(req, timeout=self.timeout) as r:
                body = r.read(max_bytes) if method != "HEAD" else b""
                return r.status, dict(r.headers.items()), body
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers.items()) if e.headers else {}, (e.read(2000) if method != "HEAD" else b"")


class PoliteFetcher:
    def __init__(self, transport=None, min_delay=1.0, max_requests=150, sleep=time.sleep, clock=time.monotonic, user_agent=USER_AGENT, max_retries=2):
        self.transport = transport or UrllibTransport()
        self.min_delay, self.max_requests, self.sleep, self.clock = min_delay, max_requests, sleep, clock
        self.user_agent, self.max_retries = user_agent, max_retries
        self.log, self.count, self.last = [], 0, {}
        self.robots = {}          # host -> (RobotFileParser | None, state)
        self.robots_state = {}    # host -> "allowed_all" | "rules" | "unreadable"
        self.head_unreliable = set()   # hosts that answer HEAD wrongly (seen live: fe2026.mahacet.org answers 404 to HEAD for PDFs that exist)

    # ---- low level
    def _wait(self, host):
        t = self.last.get(host)
        if t is not None:
            gap = self.clock() - t
            if gap < self.min_delay: self.sleep(self.min_delay - gap)

    def _send(self, method, url, headers=None, max_bytes=2_000_000):
        host = urlparse(url).netloc.lower()
        h = {"User-Agent": self.user_agent, "Accept": "*/*"}
        h.update(headers or {})
        for attempt in range(self.max_retries + 1):
            if self.count >= self.max_requests: raise BudgetExceeded("request budget of %d used up" % self.max_requests)
            self._wait(host)
            self.count += 1; t0 = self.clock()
            try:
                status, rh, body = self.transport.send(method, url, h, max_bytes)
                err = None
            except Exception as e:                               # timeouts, DNS, connection resets
                status, rh, body, err = None, {}, b"", "%s: %s" % (type(e).__name__, e)
            self.last[host] = self.clock()
            self.log.append({"method": method, "url": url, "status": status, "error": err, "ms": int((self.last[host] - t0) * 1000)})
            transient = status in TRANSIENT or (status is None)
            if transient and attempt < self.max_retries:
                ra = {k.lower(): v for k, v in rh.items()}.get("retry-after", "")
                self.sleep(min(30.0, float(ra)) if ra.replace(".", "", 1).isdigit() else 2.0 * (attempt + 1))
                continue
            return Response(url, status, rh, body, err)
        return Response(url, None, error="gave up")

    # ---- robots.txt
    def _robots_for(self, scheme, host):
        if host in self.robots_state: return
        r = self._send("GET", "%s://%s/robots.txt" % (scheme, host), max_bytes=200_000)
        if r.status is not None and 200 <= r.status < 300:
            rp = robotparser.RobotFileParser(); rp.parse(r.text.splitlines()); self.robots[host] = rp; self.robots_state[host] = "rules"
        elif r.status is not None and 400 <= r.status < 500:
            self.robots_state[host] = "allowed_all"                # no robots.txt: nothing is disallowed
        else:
            self.robots_state[host] = "unreadable"                 # cannot tell: be careful and do not crawl this host

    def allowed_by_robots(self, url):
        p = urlparse(url)
        self._robots_for(p.scheme, p.netloc.lower())
        s = self.robots_state[p.netloc.lower()]
        if s == "allowed_all": return True
        if s == "unreadable": return False
        return self.robots[p.netloc.lower()].can_fetch(self.user_agent, url)

    # ---- public
    def fetch(self, url, method="GET", headers=None, max_redirects=3, max_bytes=2_000_000):
        for _ in range(max_redirects + 1):
            p = urlparse(url)
            if p.scheme not in ("http", "https"): return Response(url, blocked="not_http")
            if not host_allowed(p.netloc): return Response(url, blocked="host_not_allowed")
            if not self.allowed_by_robots(url): return Response(url, blocked="robots_disallow_or_unreadable")
            r = self._send(method, url, headers, max_bytes)
            if r.status in (301, 302, 303, 307, 308) and r.headers.get("location"):
                url = urljoin(url, r.headers["location"]); continue
            r.url = url
            return r
        return Response(url, blocked="too_many_redirects")

    def head_check(self, url):
        """Is the file reachable? Tries HEAD first. If HEAD is refused or answered 'not found', asks for just the first byte with a
        normal GET (nothing else is downloaded). A host whose HEAD answers proved wrong is remembered, so later checks go straight to GET."""
        host = urlparse(url).netloc.lower()
        if host not in self.head_unreliable:
            r = self.fetch(url, "HEAD")
            if r.blocked or r.ok: return r
            if r.status is None or r.status not in (400, 401, 403, 404, 405, 501): return r      # server trouble: do not guess
        r2 = self.fetch(url, "GET", headers={"Range": "bytes=0-0"}, max_bytes=1)
        if host not in self.head_unreliable and r2.status in (200, 206): self.head_unreliable.add(host)
        return r2
