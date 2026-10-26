/* app.js - builds the form, validates input, loads the data files and shows the ranked report (Stage 6).
   The calculation runs in the student's own browser. Nothing the student types is sent anywhere. */
(function () {
  "use strict";
  var C = window.APP_CONFIG;
  var $ = function (id) { return document.getElementById(id); };

  function fillSelect(sel, items, placeholder) {
    sel.textContent = "";
    if (placeholder !== null) {
      var p = document.createElement("option");
      p.value = ""; p.textContent = placeholder; sel.appendChild(p);
    }
    items.forEach(function (t) {
      var o = document.createElement("option");
      o.value = t; o.textContent = t; sel.appendChild(o);
    });
  }

  function yearOptions() {
    var y = new Date().getFullYear(), out = [];
    for (var i = 0; i < 4; i++) {
      var s = y - i; out.push(s + "-" + String((s + 1) % 100).padStart(2, "0"));
    }
    return out;
  }
  var yearSel = $("year");
  var auto = document.createElement("option");
  auto.value = "auto"; auto.textContent = "Automatic (recommended)"; yearSel.appendChild(auto);
  yearOptions().forEach(function (t) {
    var o = document.createElement("option"); o.value = t; o.textContent = t; yearSel.appendChild(o);
  });

  fillSelect($("candidateType"), C.candidateTypes, "Select…");
  fillSelect($("category"), C.categories, "Select…");
  fillSelect($("gender"), C.genders, "Prefer not to answer");

  function checkList(container, items, name) {
    items.forEach(function (it) {
      var l = document.createElement("label");
      var c = document.createElement("input");
      c.type = "checkbox"; c.value = it.id; c.name = name;
      l.appendChild(c); l.appendChild(document.createTextNode(" " + it.label));
      container.appendChild(l);
    });
  }
  checkList($("extras"), C.extraEligibility, "extras");
  checkList($("priorities"), C.priorities, "priorities");

  // Priorities: "Balanced" and specific priorities are mutually exclusive.
  var balanced = $("balanced");
  function prioBoxes() { return Array.prototype.slice.call(document.querySelectorAll("input[name=priorities]")); }
  prioBoxes().forEach(function (b) {
    b.addEventListener("change", function () {
      if (b.checked) balanced.checked = false;
      if (!prioBoxes().some(function (x) { return x.checked; })) balanced.checked = true;
    });
  });
  balanced.addEventListener("change", function () {
    if (balanced.checked) prioBoxes().forEach(function (b) { b.checked = false; });
    else if (!prioBoxes().some(function (x) { return x.checked; })) balanced.checked = true;
  });

  // Ranked dropdown rows
  function addRow(containerId, items, noun) {
    var box = $(containerId), n = box.children.length + 1;
    var row = document.createElement("div"); row.className = "row";
    var rank = document.createElement("span"); rank.className = "rank"; rank.textContent = n;
    rank.setAttribute("aria-hidden", "true");
    var sel = document.createElement("select");
    sel.setAttribute("aria-label", noun + " choice " + n);
    fillSelect(sel, items, "— none —");
    row.appendChild(rank); row.appendChild(sel); box.appendChild(row);
  }
  function rowValues(containerId) {
    return Array.prototype.slice.call($(containerId).querySelectorAll("select"))
      .map(function (s) { return s.value; }).filter(Boolean);
  }
  function hasDuplicates(a) { return a.some(function (v, i) { return a.indexOf(v) !== i; }); }

  for (var i = 0; i < 3; i++) { addRow("branches", C.branches, "Branch"); addRow("districts", C.districts, "District"); }
  $("addBranch").addEventListener("click", function () { addRow("branches", C.branches, "Branch"); });
  $("addDistrict").addEventListener("click", function () { addRow("districts", C.districts, "District"); });
  $("anyDistrict").addEventListener("change", function (e) {
    $("districts").querySelectorAll("select").forEach(function (s) { s.disabled = e.target.checked; });
    $("addDistrict").disabled = e.target.checked;
  });

  // ---- data header: version, admission year, freshness, synthetic warning
  function showDataHeader() {
    DataLoader.getManifest({ baseUrl: C.DATA_BASE_URL, fetchFn: timedFetch }).then(function (m) {
      var days = m.last_successful_update ? Math.floor((Date.now() - Date.parse(m.last_successful_update)) / 86400000) : null;
      var txt = "Data version " + m.data_version + " \u00B7 admission year " + m.current_admission_year + " \u00B7 last updated " + (m.last_successful_update ? m.last_successful_update.slice(0, 10) : "unknown");
      if (days !== null && !isNaN(days) && days > 14) txt += " \u00B7 this data may be out of date";
      $("dataStatus").textContent = txt;
      if (m.is_synthetic) { $("dataBanner").textContent = "TEST DATA: every college and number on this site is made up for testing. Do not use it to make decisions."; $("dataBanner").hidden = false; }
    }).catch(function () { $("dataStatus").textContent = "The data could not be loaded. Please check your internet connection and reload the page."; });
  }
  function timedFetch(url, init) {
    var ctl = typeof AbortController !== "undefined" ? new AbortController() : null, t = ctl ? setTimeout(function () { ctl.abort(); }, 20000) : null;
    return fetch(url, Object.assign({}, init || {}, ctl ? { signal: ctl.signal } : {})).then(function (r) { if (t) clearTimeout(t); return r; }, function (e) { if (t) clearTimeout(t); throw e; });
  }
  showDataHeader();

  // Validation
  function setErr(id, msg) { $(id).textContent = msg || ""; }
  function clearErrs() { ["percentile-err", "candidateType-err", "category-err", "branches-err", "districts-err", "fee-err", "form-err"].forEach(function (id) { setErr(id, ""); }); }

  function validate() {
    clearErrs();
    var ok = true, firstBad = null;
    function bad(errId, msg, focusId) { setErr(errId, msg); ok = false; if (!firstBad) firstBad = focusId; }

    var pRaw = $("percentile").value.trim();
    var p = Number(pRaw);
    if (!/^\d{1,3}(\.\d{1,7})?$/.test(pRaw) || isNaN(p) || p < 0 || p > 100)
      bad("percentile-err", "Enter a percentile between 0 and 100 (up to 7 decimals).", "percentile");

    if (!$("candidateType").value) bad("candidateType-err", "Please select your candidate type.", "candidateType");
    if (!$("category").value) bad("category-err", "Please select your category.", "category");

    var br = rowValues("branches");
    if (br.length < 1) bad("branches-err", "Choose at least one branch.", "branches");
    else if (hasDuplicates(br)) bad("branches-err", "Each branch can be chosen only once.", "branches");

    var any = $("anyDistrict").checked, ds = any ? [] : rowValues("districts");
    if (!any && ds.length < 1) bad("districts-err", "Choose at least one district, or tick “Any district”.", "districts");
    else if (hasDuplicates(ds)) bad("districts-err", "Each district can be chosen only once.", "districts");

    var feeRaw = $("maxFee").value.replace(/[, ]/g, "");
    var fee = Number(feeRaw);
    if (!/^\d+$/.test(feeRaw) || fee < 1 || fee > 5000000)
      bad("fee-err", "Enter a whole number in rupees, for example 150000.", "maxFee");

    if (!ok) {
      setErr("form-err", "Please correct the highlighted fields.");
      var f = $(firstBad); if (f) { (f.focus ? f : f.querySelector("select")).focus(); }
      return null;
    }

    function checked(name) {
      return Array.prototype.slice.call(document.querySelectorAll("input[name=" + name + "]:checked")).map(function (c) { return c.value; });
    }
    return {
      percentile: p,
      admissionYear: $("year").value,
      candidateType: $("candidateType").value,
      category: $("category").value,
      gender: $("gender").value || null,
      extraEligibility: checked("extras"),
      branches: br,
      districts: any ? ["ANY"] : ds,
      maxAnnualFeeINR: fee,
      feeBasis: $("feeBasis").value,
      priorities: balanced.checked ? ["balanced"] : checked("priorities")
    };
  }

  var busy = false;
  $("form").addEventListener("submit", function (e) {
    e.preventDefault();
    if (busy) return;
    var payload = validate(), res = $("results");
    if (!payload) { res.hidden = true; return; }
    busy = true; $("submitBtn").disabled = true; $("submitBtn").textContent = "Finding colleges\u2026";
    ResultsView.renderLoading(res); res.focus(); 
    DataLoader.recommend(payload, { baseUrl: C.DATA_BASE_URL, fetchFn: timedFetch }).then(function (r) {
      var h = ResultsView.render(res, r); if (h && h.focus) h.focus();
      if (res.scrollIntoView) res.scrollIntoView({ behavior: "smooth" });
    }).catch(function (err) {
      ResultsView.renderProblem(res, err && err.name === "LoadError" ? err.message : "Something went wrong while preparing your results. Please reload the page and try again.");
    }).then(function () { busy = false; $("submitBtn").disabled = false; $("submitBtn").textContent = "Show my recommendations"; });
  });

  $("form").addEventListener("reset", function () {
    setTimeout(function () {
      clearErrs(); $("results").hidden = true; $("results").textContent = ""; balanced.checked = true;
      $("districts").querySelectorAll("select").forEach(function (s) { s.disabled = false; });
      $("addDistrict").disabled = false;
    }, 0);
  });
})();
