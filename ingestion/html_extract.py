"""Reads links out of HTML pages (standard library only), keeping the context that explains them:
which menu they sit under, the nearest heading, and for tables the row label and the column headings
(with colspan/rowspan handled). The CET Cell tables use the link text 'View' only, so context is essential."""
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urldefrag, urlparse


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


class _Cell:
    __slots__ = ("text", "colspan", "rowspan", "pos", "header")

    def __init__(self, colspan, rowspan, header):
        self.text, self.colspan, self.rowspan, self.pos, self.header = [], colspan, rowspan, None, header


def _span(v):
    try:
        return max(1, min(int(v), 50))
    except (TypeError, ValueError):
        return 1


class _Extractor(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.links = base, []
        self.skip = 0
        self.li = []
        self.a = None
        self.tables = []          # stack of {"rows": [[cell]], "links": [(link, cell)]}
        self.cell = None
        self.h = None
        self.last_heading = ""

    # -- helpers
    def _cell_for_link(self):
        return self.cell if (self.cell is not None and self.tables) else None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "noscript"): self.skip += 1; return
        if self.skip: return
        if tag == "li": self.li.append({"heading": None})
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6", "h7"): self.h = []
        elif tag == "table": self.tables.append({"rows": [], "links": []})
        elif tag == "tr" and self.tables: self.tables[-1]["rows"].append([])
        elif tag in ("td", "th") and self.tables:
            if not self.tables[-1]["rows"]: self.tables[-1]["rows"].append([])
            self.cell = _Cell(_span(a.get("colspan")), _span(a.get("rowspan")), tag == "th")
            self.tables[-1]["rows"][-1].append(self.cell)
        elif tag == "a" and a.get("href") is not None:
            self.a = {"href": a["href"], "title": a.get("title", ""), "parts": [], "alt": [],
                      "menu": [l["heading"] for l in self.li[:-1] if l["heading"]], "cell": self._cell_for_link(),
                      "table": self.tables[-1] if self.tables else None, "heading": self.last_heading}
        elif tag == "img" and self.a is not None and a.get("alt"): self.a["alt"].append(a["alt"])

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"): self.skip = max(0, self.skip - 1); return
        if self.skip: return
        if tag == "li" and self.li: self.li.pop()
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6", "h7") and self.h is not None:
            self.last_heading = norm("".join(self.h)); self.h = None
        elif tag in ("td", "th"): self.cell = None
        elif tag == "table" and self.tables: self._close_table(self.tables.pop())
        elif tag == "a" and self.a is not None:
            a, self.a = self.a, None
            text = norm("".join(a["parts"])) or norm(" ".join(a["alt"])) or norm(a["title"])
            if self.li and self.li[-1]["heading"] is None: self.li[-1]["heading"] = text
            raw = a["href"].strip()
            if raw == "" or raw.startswith("#"): return          # placeholder links such as "#" carry no document
            href, _ = urldefrag(urljoin(self.base, raw))
            if urlparse(href).scheme not in ("http", "https"): return
            link = {"href": href, "text": text, "menu_path": a["menu"], "heading": a["heading"], "table": None}
            self.links.append(link)
            if a["table"] is not None: a["table"]["links"].append((link, a["cell"]))

    def handle_data(self, data):
        if self.skip: return
        if self.h is not None: self.h.append(data)
        if self.a is not None: self.a["parts"].append(data)
        if self.cell is not None: self.cell.text.append(data)

    def _close_table(self, t):
        placed = {}
        for r, row in enumerate(t["rows"]):
            c = 0
            for cell in row:
                while (r, c) in placed: c += 1
                for dr in range(cell.rowspan):
                    for dc in range(cell.colspan):
                        placed.setdefault((r + dr, c + dc), cell)
                cell.pos = (r, c); c += cell.colspan
        nrows = len(t["rows"])
        by_row = {}
        for l, cell in t["links"]:
            if cell is not None: by_row.setdefault(cell.pos[0], []).append(cell)
        header_rows = []
        for r in range(nrows):
            if r in by_row: break
            header_rows.append(r)
        for link, cell in t["links"]:
            if cell is None: continue
            r, c = cell.pos
            heads, seen = [], set()
            for hr in header_rows:
                hc = placed.get((hr, c))
                txt = norm("".join(hc.text)) if hc is not None else ""
                if txt and txt not in seen: seen.add(txt); heads.append(txt)
            first = placed.get((r, 0))
            link["table"] = {"row_label": norm("".join(first.text)) if (first is not None and c > 0) else "", "col_headers": heads}


def extract_links(html, base_url):
    p = _Extractor(base_url)
    p.feed(html or ""); p.close()
    return p.links
