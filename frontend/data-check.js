(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var BASE = (window.APP_CONFIG && window.APP_CONFIG.DATA_BASE_URL) || "data/";
  function show(el, text) { el.textContent = text; }   // text only, never HTML
  fetch(BASE + "manifest.json", { cache: "no-cache" }).then(function (r) {
    if (!r.ok) throw new Error("manifest.json not found (status " + r.status + ")");
    return r.json();
  }).then(function (m) {
    var total = m.base.bytes; Object.keys(m.cutoffs).forEach(function (k) { total += m.cutoffs[k].bytes; });
    show($("status"), "OK - data version " + m.data_version + ", admission year " + m.current_admission_year +
      (m.is_synthetic ? "  (SYNTHETIC test data, not real)" : "") + ". " + Object.keys(m.cutoffs).length + " cutoff files, " + Math.round(total / 1024) + " KB in all.");
    show($("manifest"), JSON.stringify({ data_version: m.data_version, generated_at: m.generated_at, last_successful_update: m.last_successful_update,
      base_file: m.base.file, cutoff_files: Object.keys(m.cutoffs).map(function (k) { return m.cutoffs[k].file + "  (" + m.cutoffs[k].bytes + " bytes)"; }), row_counts: m.row_counts }, null, 2));
  }).catch(function (e) { show($("status"), "PROBLEM: " + e.message); });

  $("run").addEventListener("click", function () {
    show($("runStatus"), "Loading…"); show($("out"), "");
    var input = { percentile: 93.5, admissionYear: "auto", candidateType: "Maharashtra State candidate", category: "OBC", gender: "Female", extraEligibility: [],
      branches: ["Computer Science and Engineering", "Information Technology", "Computer Engineering"], districts: ["Pune", "Mumbai Suburban"],
      maxAnnualFeeINR: 200000, feeBasis: "tuition", priorities: ["placements"] };
    var t0 = performance.now();
    DataLoader.recommend(input, { baseUrl: BASE }).then(function (r) {
      var ms = Math.round(performance.now() - t0);
      if (!r.ok) { show($("runStatus"), "The engine said: " + r.errors.join(" ")); return; }
      show($("runStatus"), "Done in " + ms + " ms. Downloaded " + Math.round(r.meta.dataBytesDownloaded / 1024) + " KB from " + r.meta.dataFiles.length + " file(s). " + r.results.length + " results" + (r.meta.usingSyntheticData ? " (synthetic data)" : "") + ".");
      show($("out"), r.results.slice(0, 5).map(function (x) {
        return "#" + x.rank + "  " + x.collegeName + " - " + x.branchName + "\n     " + x.district + " | " + x.suitability + " | score " + x.score +
          " | vacancy: " + (x.vacancy.value === null ? x.vacancy.status : x.vacancy.value + " (round " + x.vacancy.round + ")");
      }).join("\n\n"));
    }).catch(function (e) { show($("runStatus"), "PROBLEM (" + (e.code || "error") + "): " + e.message); });
  });
})();
