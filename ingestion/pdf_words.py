"""Reads the words of a PDF together with their positions on the page (Stage 9).

Uses poppler's `pdftotext -bbox` (a program, not a Python library) and reads its output one page at a time, so even a
1,500-page file needs little memory. The position of every word is what lets the parsers tell which column a number
belongs to; plain text extraction cannot do that reliably.
"""
import html, re, shutil, subprocess
from collections import namedtuple

Word = namedtuple("Word", "x0 y0 x1 y1 text")
WORD_RE = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>')
PAGE_RE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)"')


class PdfToolMissing(RuntimeError):
    pass


def have_poppler():
    return shutil.which("pdftotext") is not None


def iter_pages(pdf_path, first=None, last=None):
    """Yields (page_number, width, height, [Word, ...]) for each page."""
    if not have_poppler():
        raise PdfToolMissing("pdftotext (poppler-utils) is not installed. On Ubuntu: sudo apt-get install -y poppler-utils")
    cmd = ["pdftotext", "-bbox"] + (["-f", str(first)] if first else []) + (["-l", str(last)] if last else []) + [pdf_path, "-"]
    n = (first or 1) - 1
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace") as p:
        words, w, h = None, 0.0, 0.0
        for line in p.stdout:
            line = line.lstrip()
            if line.startswith("<page "):
                m = PAGE_RE.match(line); w, h = (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0); words = []; n += 1
            elif words is not None:
                if line.startswith("</page>"):
                    yield n, w, h, words; words = None
                else:
                    m = WORD_RE.search(line)
                    if m: words.append(Word(float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)), html.unescape(m.group(5))))
        err = p.stderr.read()
    if p.returncode not in (0, None):
        raise RuntimeError("pdftotext failed (%s): %s" % (p.returncode, err[:300]))


def group_lines(words, tol=2.6):
    """Groups words into visual lines (by vertical position) and sorts each line left to right."""
    ws = sorted(words, key=lambda w: (w.y0 + w.y1) / 2)
    lines, cur, cy = [], [], None
    for w in ws:
        yc = (w.y0 + w.y1) / 2
        if cur and abs(yc - cy) <= tol:
            cur.append(w); cy = sum((x.y0 + x.y1) / 2 for x in cur) / len(cur)
        else:
            if cur: lines.append(sorted(cur, key=lambda x: x.x0))
            cur, cy = [w], yc
    if cur: lines.append(sorted(cur, key=lambda x: x.x0))
    return lines


def line_text(line):
    return " ".join(w.text for w in line)
