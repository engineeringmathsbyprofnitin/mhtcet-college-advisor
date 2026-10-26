/* results.js - draws the ranked report. Pure display code: it never changes the engine's answer.
   Everything is built with createElement/textContent (never raw HTML strings), so text from data files cannot inject HTML.
   Works in browsers (window.ResultsView) and, with jsdom, in tests. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.ResultsView = factory();
})(this, function () {
  "use strict";
  var NA = "Not available";

  function el(doc, tag, attrs, kids) {
    var e = doc.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "text") e.textContent = attrs[k]; else if (k === "hidden") { if (attrs[k]) e.hidden = true; } else e.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (c) { if (c) e.appendChild(typeof c === "string" ? doc.createTextNode(c) : c); });
    return e;
  }
  function small(doc, text) { return el(doc, "small", { text: text, class: "sub" }); }
  function fmtPct(v) {
    if (v === null || v === undefined || v === "") return NA;
    var s = Number(v).toFixed(7); return s.replace(/0+$/, "").replace(/\.$/, "");
  }
  function inr(v) { return "\u20B9" + Number(v).toLocaleString("en-IN"); }
  function safeUrl(u) {
    try { var x = new URL(u); return (x.protocol === "https:" || x.protocol === "http:") && !/\.invalid$/i.test(x.hostname) ? x.href : null; } catch (e) { return null; }
  }
  function cell(doc, label, kids, cls) { return el(doc, "td", { "data-label": label, class: cls || "" }, kids); }
  function noteLine(doc, main, sub) { return [el(doc, "span", { text: main }), sub ? small(doc, sub) : null]; }

  function accCell(doc, label, a, withGrade) {
    if (!a) return cell(doc, label, noteLine(doc, NA));
    var s = a.status, main;
    if (s === "valid") main = (withGrade && a.grade ? a.grade + " - " : "") + "Accredited" + (a.validTo ? " (until " + a.validTo + ")" : "");
    else if (s === "expired") main = (withGrade && a.grade ? a.grade + " - " : "") + "Expired" + (a.validTo ? " (" + a.validTo + ")" : "");
    else if (s === "validity_unknown") main = (withGrade && a.grade ? a.grade + " - " : "") + "Accredited, validity date not known";
    else if (s === "not_accredited") main = "Not accredited";
    else main = NA;
    return cell(doc, label, noteLine(doc, main));
  }

  function suitClass(s) {
    return { "Historically more suitable": "s-more", "Possible but uncertain": "s-possible", "Ambitious choice": "s-ambitious", "Limited evidence": "s-limited" }[s] || "s-limited";
  }

  function sourceItem(doc, s) {
    var bits = [s.source_name || s.doc_id];
    var det = [];
    if (s.doc_type) det.push(s.doc_type.replace(/_/g, " "));
    if (s.admission_year) det.push(s.admission_year);
    if (s.cap_round) det.push("CAP Round " + s.cap_round);
    if (s.published_date) det.push("published " + s.published_date);
    if (s.retrieved_date) det.push("retrieved " + s.retrieved_date);
    var li = el(doc, "li", {}, [el(doc, "span", { text: bits[0] + (det.length ? " (" + det.join(", ") + ")" : "") + " " })]);
    var u = safeUrl(s.source_url);
    if (u) li.appendChild(el(doc, "a", { href: u, target: "_blank", rel: "noopener noreferrer", text: "Open source" }));
    else if (s.source_url) li.appendChild(small(doc, "(test link, not a real page)"));
    return li;
  }

  function resultRows(doc, r, ncols, years) {
    var tr = el(doc, "tr", { class: "result" });
    tr.appendChild(cell(doc, "Rank", [el(doc, "strong", { text: "#" + r.rank })], "rank"));
    var col = [el(doc, "strong", { text: r.collegeName }), small(doc, "College code " + r.collegeCode), small(doc, r.district)];
    if (r.autonomy === "autonomous") col.push(small(doc, "Autonomous"));
    var w = r.collegeWebsite && safeUrl(r.collegeWebsite);
    if (w) col.push(el(doc, "a", { href: w, target: "_blank", rel: "noopener noreferrer", text: "College website", class: "sub" }));
    tr.appendChild(cell(doc, "College", col));
    tr.appendChild(cell(doc, "Branch", [el(doc, "span", { text: r.branchName }), small(doc, "Branch code " + r.branchCode)]));
    for (var i = 0; i < 3; i++) {
      var h = r.historicalCutoffs[i], y = years[i] || "";
      tr.appendChild(cell(doc, "Cutoff " + y, h && h.value !== null ? [el(doc, "span", { text: fmtPct(h.value) }), small(doc, "CAP Round " + h.round + " \u00B7 " + h.seatType)] : noteLine(doc, NA)));
    }
    var c = r.currentCutoff;
    tr.appendChild(cell(doc, "Latest current cutoff", c ? [el(doc, "span", { text: fmtPct(c.value) }), small(doc, "CAP Round " + c.round + " \u00B7 " + c.year + " \u00B7 " + c.seatType)] : noteLine(doc, NA)));
    var v = r.vacancy;
    tr.appendChild(cell(doc, "Latest vacancy", v && v.value !== null ? [el(doc, "span", { text: String(v.value) + " seat(s)" }), small(doc, "CAP Round " + v.round)] : noteLine(doc, "Vacancy data unavailable")));
    var f = r.fee, fk;
    if (f && f.status === "ok") fk = [el(doc, "span", { text: inr(f.value) + " per year" }), small(doc, (f.type === "tuition" ? "Tuition fee only; excludes hostel, transport and exam charges" : "Total yearly expenses") + " \u00B7 " + f.academicYear)];
    else if (f && f.status === "total_unavailable_tuition_known") fk = [el(doc, "span", { text: "Total cost not available" }), small(doc, "Tuition alone: " + inr(f.tuitionLowerBound) + " (" + f.academicYear + "); total will be higher")];
    else fk = noteLine(doc, NA);
    tr.appendChild(cell(doc, "Annual fee", fk));
    [["Infrastructure", r.infrastructure], ["Teaching", r.teaching]].forEach(function (p) {
      var q = p[1];
      tr.appendChild(cell(doc, p[0], q ? [el(doc, "span", { text: q.score_0_10 + " / 10" }), small(doc, q.isEstimate ? "System estimate, not an official score" : "Official score")] : noteLine(doc, NA)));
    });
    var pl = r.placement;
    tr.appendChild(cell(doc, "Placement", pl ? [el(doc, "span", { text: pl.value + "% placed" }), small(doc, pl.year + " \u00B7 " + pl.scope + " level")] : noteLine(doc, NA)));
    var nba = accCell(doc, "NBA accreditation", r.nba, false); if (r.nba) nba.appendChild(small(doc, "This program only")); tr.appendChild(nba);
    tr.appendChild(accCell(doc, "NAAC grade", r.naac, true));
    tr.appendChild(cell(doc, "Suitability", [el(doc, "span", { class: "badge " + suitClass(r.suitability), text: r.suitability }), small(doc, "Ranking score " + r.score)]));

    var why = el(doc, "tr", { class: "why" });
    var td = el(doc, "td", { colspan: String(ncols) });
    var det = el(doc, "details", {}, [el(doc, "summary", { text: "Why this choice? (explanation and sources)" })]);
    var ul = el(doc, "ul", { class: "explain" }); r.explanation.forEach(function (t) { ul.appendChild(el(doc, "li", { text: t })); });
    det.appendChild(ul);
    det.appendChild(el(doc, "p", { class: "sub-h", text: "Sources" }));
    var sl = el(doc, "ul", { class: "sources" }); (r.sources || []).forEach(function (s) { sl.appendChild(sourceItem(doc, s)); }); det.appendChild(sl);
    td.appendChild(det); why.appendChild(td);
    return [tr, why];
  }

  function summaryList(doc, res) {
    var c = res.counts, m = res.meta, items = [];
    items.push("Of " + c.totalChoices + " college-branch choices in the data, " + c.afterBranch + " match your branches, " + c.afterDistrict + " of those are in your districts, and " + c.afterFee + " of those fit your budget.");
    if (c.belowRange) items.push(c.belowRange + " of those were well above your percentile range and are not shown.");
    if (c.insufficientData) items.push(c.insufficientData + " could not be assessed because there is no usable cutoff data (listed below).");
    return el(doc, "ul", { class: "funnel" }, items.map(function (t) { return el(doc, "li", { text: t }); }));
  }

  function render(rootEl, res, opts) {
    var doc = rootEl.ownerDocument; opts = opts || {};
    rootEl.textContent = ""; rootEl.hidden = false;
    var h = el(doc, "h2", { text: "Your recommended choices", tabindex: "-1", id: "resultsHeading" }); rootEl.appendChild(h);
    if (!res || !res.ok) { return renderProblem(rootEl, (res && res.errors && res.errors.join(" ")) || "Something went wrong."); }
    var m = res.meta, list = res.results;
    if (m.usingSyntheticData) rootEl.appendChild(el(doc, "p", { class: "banner danger", role: "alert", text: "TEST DATA: the colleges and numbers below are made up for testing. Do not use them to make any decision." }));
    (m.warnings || []).forEach(function (w) { rootEl.appendChild(el(doc, "p", { class: "notice", text: w })); });
    if (!list.length) {
      rootEl.appendChild(el(doc, "p", { class: "lead", text: "No choices matched your preferences with enough data to assess." }));
      rootEl.appendChild(el(doc, "p", { text: "You could add more branches or districts, raise your budget, or check that your category is supported." }));
      if (res.counts && res.counts.totalChoices) rootEl.appendChild(summaryList(doc, res));
    } else {
      rootEl.appendChild(el(doc, "p", { class: "lead", text: list.length < 5 ? "Only " + list.length + " choice(s) matched your preferences with enough data." : "Showing the " + Math.min(5, list.length) + " leading choices" + (list.length > 5 ? " of " + list.length + " suitable choices found." : ".") }));
      rootEl.appendChild(summaryList(doc, res));
      var years = m.historicalYears || [];
      var heads = ["Rank", "College", "Branch"].concat(years.map(function (y) { return "Cutoff " + y; }), ["Latest current cutoff (" + m.currentAdmissionYear + ")", "Latest vacancy", "Annual fee", "Infrastructure", "Teaching", "Placement", "NBA accreditation", "NAAC grade", "Suitability"]);
      var table = el(doc, "table", { class: "results", id: "resultsTable" }, [el(doc, "caption", { text: "Recommended choices, ranked from best match (1) downward" })]);
      var thead = el(doc, "thead", {}, [el(doc, "tr", {}, heads.map(function (t) { return el(doc, "th", { scope: "col", text: t }); }))]);
      table.appendChild(thead);
      var top = el(doc, "tbody", { id: "topRows" }), more = el(doc, "tbody", { id: "moreRows", hidden: true });
      list.forEach(function (r, i) { resultRows(doc, r, heads.length, years).forEach(function (tr) { (i < 5 ? top : more).appendChild(tr); }); });
      table.appendChild(top); if (list.length > 5) table.appendChild(more);
      rootEl.appendChild(el(doc, "div", { class: "table-scroll", tabindex: "0", role: "region", "aria-label": "Results table, scrolls sideways on small screens" }, [table]));
      if (list.length > 5) {
        var btn = el(doc, "button", { type: "button", class: "secondary", id: "toggleMore", "aria-expanded": "false", "aria-controls": "moreRows", text: "Show more suitable choices (6\u201320)" });
        btn.addEventListener("click", function () {
          var open = more.hidden; more.hidden = !open; btn.setAttribute("aria-expanded", String(open));
          btn.textContent = open ? "Show fewer choices" : "Show more suitable choices (6\u201320)";
        });
        rootEl.appendChild(btn);
      }
    }
    if (res.insufficientData && res.insufficientData.length) {
      var d = el(doc, "details", { class: "insufficient" }, [el(doc, "summary", { text: res.insufficientData.length + " matching choice(s) have no usable cutoff data" })]);
      var ul = el(doc, "ul", {}); res.insufficientData.forEach(function (x) { ul.appendChild(el(doc, "li", { text: x.collegeName + " - " + x.branchName + " (" + x.district + ")" })); });
      d.appendChild(ul); rootEl.appendChild(d);
    }
    var info = [
      "Data version " + (m.dataVersion || NA) + " \u00B7 current admission year " + m.currentAdmissionYear + " \u00B7 last successful data update: " + (m.lastSuccessfulUpdate || NA),
      "Compared with the past three admission years: " + (m.historicalYears || []).join(", ") + ". Cutoff groups used: " + ((m.seatTypesUsed || []).join(", ") || "none") + ".",
      "Vacancy figures come from CAP Round " + (m.vacancyRoundUsed || "IV or III (none available)") + " vacancy-position data only." + (m.vacancyRoundUsed ? "" : " Vacancy data unavailable.")
    ];
    rootEl.appendChild(el(doc, "div", { class: "datainfo" }, info.map(function (t) { return el(doc, "p", { text: t }); })));
    rootEl.appendChild(el(doc, "p", { class: "notice", text: "This is guidance based on past cutoffs, not a prediction or a guarantee. Final eligibility, option selection and admission depend on official CET Cell rules, the CAP process, seat availability and your verified documents." }));
    if (list.length) {
      var pb = el(doc, "button", { type: "button", class: "secondary no-print", id: "printBtn", text: "Print or save as PDF" });
      pb.addEventListener("click", function () { if (opts.print) opts.print(); else if (doc.defaultView && doc.defaultView.print) doc.defaultView.print(); });
      rootEl.appendChild(pb);
    }
    return h;
  }

  function renderProblem(rootEl, message) {
    var doc = rootEl.ownerDocument; rootEl.hidden = false;
    if (!rootEl.querySelector("#resultsHeading")) { rootEl.textContent = ""; rootEl.appendChild(el(doc, "h2", { text: "Your recommended choices", tabindex: "-1", id: "resultsHeading" })); }
    rootEl.appendChild(el(doc, "p", { class: "banner danger", role: "alert", text: message }));
    return rootEl.querySelector("#resultsHeading");
  }
  function renderLoading(rootEl) {
    var doc = rootEl.ownerDocument; rootEl.hidden = false; rootEl.textContent = "";
    rootEl.appendChild(el(doc, "h2", { text: "Your recommended choices", tabindex: "-1", id: "resultsHeading" }));
    rootEl.appendChild(el(doc, "p", { class: "notice", role: "status", text: "Finding suitable colleges for you\u2026" }));
  }
  return { render: render, renderProblem: renderProblem, renderLoading: renderLoading, fmtPct: fmtPct };
});
