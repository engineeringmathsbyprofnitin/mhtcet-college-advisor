/* Stage 10c-3e: builds a real PDF file in the browser (no libraries, no internet needed), so "Download PDF" works on phones where the
   browser's Print > Save as PDF does not. Text only: Helvetica, A4 portrait. Characters outside Latin-1 are replaced (never dropped silently: '?'). */
(function (root) {
  "use strict";
  var W = 595.28, H = 841.89, M = 40, BODY = 8.6, LEAD = 11.2;
  // Helvetica character widths (1/1000 em) for ASCII 32..126
  var HW = [278,278,355,556,556,889,667,191,333,333,389,584,278,333,278,278,556,556,556,556,556,556,556,556,556,556,278,278,584,584,584,556,1015,667,667,722,722,667,611,778,722,278,500,667,556,833,722,778,667,778,722,667,611,722,667,944,667,667,611,278,278,278,469,556,333,556,556,500,556,556,278,556,556,222,222,500,222,833,556,556,556,556,333,500,278,556,500,722,500,500,500,334,260,334,584];
  var MAP = { "\u2018": "'", "\u2019": "'", "\u201C": '"', "\u201D": '"', "\u2013": "-", "\u2014": "-", "\u00B7": "|", "\u20B9": "Rs ", "\u2026": "...", "\u2022": "-", "\u00A0": " ", "\u2192": "->" };
  function clean(s) {
    s = String(s === null || s === undefined ? "" : s); var o = "";
    for (var i = 0; i < s.length; i++) {
      var ch = s.charAt(i), c = s.charCodeAt(i);
      if (MAP[ch] !== undefined) o += MAP[ch]; else if (c === 10 || c === 13 || c === 9) o += " "; else if (c >= 32 && c <= 126) o += ch; else if (c >= 161 && c <= 255) o += ch; else o += "?";
    }
    return o;
  }
  function width(s, size, bold) { var w = 0; for (var i = 0; i < s.length; i++) { var c = s.charCodeAt(i); w += (c >= 32 && c <= 126 ? HW[c - 32] : 556); } return w * size / 1000 * (bold ? 1.06 : 1); }
  function wrap(text, size, bold, maxW) {
    var words = clean(text).split(" "), lines = [], cur = "";
    words.forEach(function (w) {
      while (width(w, size, bold) > maxW) {                       // a single very long word: cut it
        var k = w.length; while (k > 1 && width(w.slice(0, k), size, bold) > maxW) k--;
        if (cur) { lines.push(cur); cur = ""; } lines.push(w.slice(0, k)); w = w.slice(k);
      }
      var t = cur ? cur + " " + w : w;
      if (cur && width(t, size, bold) > maxW) { lines.push(cur); cur = w; } else cur = t;
    });
    if (cur || !lines.length) lines.push(cur); return lines;
  }
  function esc(s) { return s.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)"); }
  function pct(v) { if (v === null || v === undefined || v === "") return "Not available"; var s = Number(v).toFixed(7); return s.replace(/0+$/, "").replace(/\.$/, ""); }

  function model(res) {                                           // the text of the report: [{t: text, b: bold, s: size, gap: extra space before}]
    var m = res.meta || {}, L = [];
    function add(t, o) { o = o || {}; L.push({ t: t, b: !!o.b, s: o.s || BODY, gap: o.gap || 0, indent: o.indent || 0 }); }
    add("MHT-CET College Advisor - your recommended choices", { b: true, s: 14 });
    add("Data version " + (m.dataVersion || "Not available") + " | admission year " + (m.currentAdmissionYear || "Not available") + " | last successful data update: " + (m.lastSuccessfulUpdate || "Not available"), { gap: 4 });
    add("Compared with the past three admission years: " + (m.historicalYears || []).join(", ") + ". Cutoff groups used: " + ((m.seatTypesUsed || []).join(", ") || "none") + ".");
    add("This is guidance based on past cutoffs, not a prediction or a guarantee. Final eligibility, option selection and admission depend on official CET Cell rules, dates and seat availability.", { b: true, gap: 4 });
    (m.warnings || []).forEach(function (w) { add("Note: " + w, { gap: 3 }); });
    (res.results || []).forEach(function (r) {
      add("#" + r.rank + "  " + r.collegeName + " (college code " + r.collegeCode + ")", { b: true, s: 10, gap: 11 });
      add("Branch: " + r.branchName + " (branch code " + r.branchCode + ")" + (r.district && r.district !== "Not available" ? " | District: " + r.district : ""), { indent: 10 });
      add("Suitability: " + r.suitability + " (ranking score " + r.score + ")", { b: true, indent: 10 });
      var past = (r.historicalCutoffs || []).map(function (h, i) { var y = (m.historicalYears || [])[i] || ""; return y + ": " + (h && h.value !== null ? pct(h.value) + " (Round " + h.round + ", " + h.seatType + ")" : "Not available"); });
      add("Past cutoffs - " + past.join(" | "), { indent: 10 });
      var c = r.currentCutoff, cr = r.currentRounds, rr = cr ? ["I", "II", "III", "IV"].map(function (k) { return "Round " + k + ": " + (cr[k] ? pct(cr[k].value) : "-"); }).join(" | ") : "";
      add("Current year" + (c ? " " + c.year : "") + " - latest: " + (c ? pct(c.value) + " (Round " + c.round + ", " + c.seatType + ")" : "Not available") + (rr ? " | " + rr : "") + (c && c.homeUniversityUnclear ? " | home university unclear: harder figure shown" : ""), { indent: 10 });
      var v = r.vacancy, f = r.fee;
      add("Vacancy: " + (v && v.value !== null ? v.value + " seat(s) (Round " + v.round + ")" : "Vacancy data unavailable") + " | Annual fee: " + (f && f.status === "ok" ? "Rs " + Number(f.value).toLocaleString("en-IN") : "Not available"), { indent: 10 });
      (r.explanation || []).forEach(function (t) { add("- " + t, { indent: 10, s: 8 }); });
    });
    return L;
  }

  function buildPdf(res) {
    var L = model(res), pages = [], cur = [], y = H - M - 10, maxW = W - 2 * M;
    function newPage() { cur = []; pages.push(cur); y = H - M - 10; }
    newPage();
    L.forEach(function (ln) {
      var lines = wrap(ln.t, ln.s, ln.b, maxW - ln.indent), lead = ln.s * 1.3;
      y -= ln.gap; if (y - lead < M + 14 && cur.length) newPage();
      lines.forEach(function (t) {
        if (y - lead < M + 14) newPage();
        cur.push({ x: M + ln.indent, y: y, t: t, b: ln.b, s: ln.s }); y -= lead;
      });
    });
    var objs = [];                                                  // 1 catalog, 2 pages, 3 font, 4 bold font, 5 info, then (content, page) pairs
    var n = pages.length, kids = pages.map(function (_, i) { return (6 + 2 * i + 1) + " 0 R"; }).join(" ");
    objs[1] = "<< /Type /Catalog /Pages 2 0 R >>"; objs[2] = "<< /Type /Pages /Kids [" + kids + "] /Count " + n + " >>";
    objs[3] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"; objs[4] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>";
    objs[5] = "<< /Title (MHT-CET College Advisor results) /Producer (MHT-CET College Advisor) >>";
    pages.forEach(function (pg, i) {
      var s = "BT\n";
      pg.forEach(function (t) { s += "/" + (t.b ? "F2" : "F1") + " " + t.s + " Tf 1 0 0 1 " + t.x.toFixed(2) + " " + t.y.toFixed(2) + " Tm (" + esc(t.t) + ") Tj\n"; });
      s += "/F1 8 Tf 1 0 0 1 " + M + " " + (M - 6) + " Tm (" + esc("Page " + (i + 1) + " of " + n + " - guidance only; verify with the official CET Cell lists") + ") Tj\nET\n";
      objs[6 + 2 * i] = "<< /Length " + s.length + " >>\nstream\n" + s + "endstream";
      objs[7 + 2 * i] = "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 " + W + " " + H + "] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents " + (6 + 2 * i) + " 0 R >>";
    });
    var out = "%PDF-1.4\n", offs = [];
    for (var k = 1; k < objs.length; k++) { offs[k] = out.length; out += k + " 0 obj\n" + objs[k] + "\nendobj\n"; }
    var xr = out.length; out += "xref\n0 " + objs.length + "\n0000000000 65535 f \n";
    for (k = 1; k < objs.length; k++) out += ("0000000000" + offs[k]).slice(-10) + " 00000 n \n";
    out += "trailer\n<< /Size " + objs.length + " /Root 1 0 R /Info 5 0 R >>\nstartxref\n" + xr + "\n%%EOF\n";
    var bytes = new Uint8Array(out.length); for (var j = 0; j < out.length; j++) bytes[j] = out.charCodeAt(j) & 255;
    return bytes;
  }

  function download(res, doc) {                                      // saves the PDF through the browser's normal download
    doc = doc || root.document; var bytes = buildPdf(res), w = doc.defaultView || root;
    var blob = new w.Blob([bytes], { type: "application/pdf" }), url = w.URL.createObjectURL(blob);
    var a = doc.createElement("a"); a.href = url; a.download = "mhtcet-college-advisor-results.pdf"; a.style.display = "none"; doc.body.appendChild(a); a.click();
    w.setTimeout(function () { a.remove(); w.URL.revokeObjectURL(url); }, 30000);
  }
  var api = { buildPdf: buildPdf, download: download, clean: clean, wrap: wrap };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.PdfExport = api;
})(typeof window !== "undefined" ? window : this);
