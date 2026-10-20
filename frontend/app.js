/* app.js - Stage 2: builds the form, validates input, shows the request payload.
   It does NOT yet contact any server or compute recommendations. */
(function () {
  "use strict";
  var C = window.APP_CONFIG;
  var $ = function (id) { return document.getElementById(id); };

  function fillSelect(sel, items, placeholder) {
    sel.innerHTML = "";
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

  $("dataStatus").textContent = C.DATA_NOTE;

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

  $("form").addEventListener("submit", function (e) {
    e.preventDefault();
    var payload = validate();
    var res = $("results");
    if (!payload) { res.hidden = true; return; }
    $("payload").textContent = JSON.stringify(payload, null, 2);
    $("resultNote").textContent = C.API_URL
      ? "API address is set, but sending requests is added in Stage 6."
      : "Stage 2 preview: your inputs are valid, but no recommendation service is connected yet, so no colleges are shown.";
    res.hidden = false;
    res.scrollIntoView({ behavior: "smooth" });
  });

  $("form").addEventListener("reset", function () {
    setTimeout(function () {
      clearErrs(); $("results").hidden = true; balanced.checked = true;
      $("districts").querySelectorAll("select").forEach(function (s) { s.disabled = false; });
      $("addDistrict").disabled = false;
    }, 0);
  });
})();
