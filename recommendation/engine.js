/* MHT-CET College Advisor - recommendation engine (Stage 4).
   Deterministic and rule-based. No randomness, no AI guessing, no network calls.
   Works in Node (module.exports), browsers (window.Recommender) and Google Apps Script (global Recommender).
   Rules are documented in docs/RANKING_RULES.md. The numbers in DEFAULTS are NOT statistically calibrated. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.Recommender = factory();
})(this, function () {
  "use strict";

  var DEFAULTS = {
    historyYears: 3,
    roundPriority: ["IV", "III", "II", "I"],   // current-year cutoff: latest published round wins
    vacancyRounds: ["IV", "III"],              // vacancy: ONLY these, in this order. Never I or II.
    includeOpenSeatsForReserved: true,         // ASSUMPTION to verify against official rules (Stages 7-9)
    openCategoryName: "Open",
    thresholds: { saferMargin: 1.0, uncertainTolerance: 2.0, ambitiousLimit: 6.0 },
    evidenceWeights: { current: 0.4, hist: [0.3, 0.2, 0.1] },
    trend: { weight: 0.5, maxAdjust: 3.0 },
    limitedEvidencePenalty: 0.85,
    maxResults: 20,
    topCount: 5,
    asOfDate: null,                            // YYYY-MM-DD used to judge accreditation validity
    weights: {                                 // each row sums to 1.00
      balanced:        { fit: .30, branch: .15, district: .10, placement: .12, teaching: .12, infrastructure: .10, fee: .06, accreditation: .05 },
      placements:      { fit: .30, branch: .15, district: .10, placement: .25, teaching: .08, infrastructure: .05, fee: .03, accreditation: .04 },
      teaching:        { fit: .30, branch: .15, district: .10, placement: .06, teaching: .22, infrastructure: .04, fee: .03, accreditation: .10 },
      infrastructure:  { fit: .30, branch: .15, district: .10, placement: .05, teaching: .08, infrastructure: .25, fee: .03, accreditation: .04 },
      low_fees:        { fit: .30, branch: .15, district: .10, placement: .06, teaching: .05, infrastructure: .04, fee: .27, accreditation: .03 },
      admission_chance:{ fit: .55, branch: .12, district: .08, placement: .06, teaching: .06, infrastructure: .05, fee: .04, accreditation: .04 }
    }
  };
  var GRADE_SCORE = { "A++": 100, "A+": 85, "A": 70, "B++": 55, "B+": 40, "B": 30, "C": 20 };
  var DISTRICT_ALIASES = { "ahmednagar": "ahilyanagar", "aurangabad": "chhatrapati sambhajinagar", "osmanabad": "dharashiv" };
  var COMPONENTS = ["fit", "branch", "district", "placement", "teaching", "infrastructure", "fee", "accreditation"];

  /* ---------- helpers ---------- */
  function yearStart(y) {
    var m = /^(\d{4})-(\d{2})$/.exec(y || ""); if (!m) return null;
    var a = +m[1]; return ((a + 1) % 100 === +m[2]) ? a : null;
  }
  function fmtYear(a) { return a + "-" + String((a + 1) % 100).padStart(2, "0"); }
  function previousYears(cur, n) {
    var a = yearStart(cur); if (a === null) throw new Error("Invalid admission year: " + cur);
    var out = []; for (var i = 1; i <= n; i++) out.push(fmtYear(a - i)); return out;
  }
  function normDistrict(s) {
    s = String(s || "").toLowerCase().replace(/\(.*?\)/g, "").replace(/\s+/g, " ").trim();
    return DISTRICT_ALIASES[s] || s;
  }
  function norm(s) { return String(s || "").trim().toLowerCase(); }
  function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }
  function round2(x) { return Math.round(x * 100) / 100; }
  function groupBy(rows, keyFn) {
    var m = new Map();
    rows.forEach(function (r) { var k = keyFn(r); if (!m.has(k)) m.set(k, []); m.get(k).push(r); });
    return m;
  }
  function merge(a, b) {
    var out = {}; Object.keys(a).forEach(function (k) { out[k] = a[k]; });
    Object.keys(b || {}).forEach(function (k) {
      out[k] = (b[k] && typeof b[k] === "object" && !Array.isArray(b[k]) && a[k] && typeof a[k] === "object") ? merge(a[k], b[k]) : b[k];
    });
    return out;
  }

  /* ---------- input validation ---------- */
  var PRIORITIES = ["balanced", "placements", "teaching", "infrastructure", "low_fees", "admission_chance"];
  function validateInput(inp) {
    var e = [];
    if (!inp || typeof inp !== "object") return { ok: false, errors: ["Request is missing."] };
    if (typeof inp.percentile !== "number" || !isFinite(inp.percentile) || inp.percentile < 0 || inp.percentile > 100) e.push("percentile must be a number between 0 and 100.");
    if (!inp.candidateType || typeof inp.candidateType !== "string") e.push("candidateType is required.");
    if (!inp.category || typeof inp.category !== "string") e.push("category is required.");
    if (!Array.isArray(inp.branches) || inp.branches.length < 1) e.push("Choose at least one branch.");
    else if (new Set(inp.branches).size !== inp.branches.length) e.push("Branches must not repeat.");
    if (!Array.isArray(inp.districts) || inp.districts.length < 1) e.push("Choose at least one district or ANY.");
    else if (new Set(inp.districts).size !== inp.districts.length) e.push("Districts must not repeat.");
    if (typeof inp.maxAnnualFeeINR !== "number" || !isFinite(inp.maxAnnualFeeINR) || inp.maxAnnualFeeINR < 1 || Math.floor(inp.maxAnnualFeeINR) !== inp.maxAnnualFeeINR) e.push("maxAnnualFeeINR must be a positive whole number.");
    if (inp.feeBasis !== "tuition" && inp.feeBasis !== "total") e.push("feeBasis must be 'tuition' or 'total'.");
    if (inp.admissionYear !== undefined && inp.admissionYear !== "auto" && yearStart(inp.admissionYear) === null) e.push("admissionYear must be 'auto' or like 2026-27.");
    if (inp.priorities !== undefined) {
      if (!Array.isArray(inp.priorities)) e.push("priorities must be a list.");
      else inp.priorities.forEach(function (p) { if (PRIORITIES.indexOf(p) < 0) e.push("Unknown priority: " + p); });
    }
    return { ok: e.length === 0, errors: e };
  }

  /* ---------- data preparation ---------- */
  var TABLES = ["colleges", "branches", "seat_types", "historical_cutoffs", "current_cutoffs", "vacancies", "fees",
    "accreditation", "placements", "quality_indicators", "source_documents", "refresh_status", "data_version"];
  function prepare(raw) {
    var d = {};
    TABLES.forEach(function (t) {
      var rows = (raw && raw[t]) || [];
      // only validated rows are ever used; seat_types and source_documents are lookups
      d[t] = (t === "seat_types" || t === "source_documents") ? rows : rows.filter(function (r) { return r.validation_status === undefined || r.validation_status === "validated"; });
    });
    return d;
  }

  /* ---------- seat-type matching ---------- */
  function eligibleSeatTypes(s, seatTypes, cfg) {
    return seatTypes.filter(function (st) {
      if (st.candidate_type !== s.candidateType) return false;
      var catOk = st.category === s.category || (cfg.includeOpenSeatsForReserved && st.category === cfg.openCategoryName);
      if (!catOk) return false;
      return !st.gender_scope || st.gender_scope === s.gender;
    }).map(function (st) { return st.seat_type_code; });
  }

  /* ---------- cutoff picking ---------- */
  function pickCutoff(rows, eligible, cfg) {
    if (!rows) return null;
    for (var i = 0; i < cfg.roundPriority.length; i++) {
      var rd = cfg.roundPriority[i];
      var cand = rows.filter(function (r) { return r.cap_round === rd && eligible.has(r.seat_type_code) && r.cutoff_percentile !== "" && isFinite(+r.cutoff_percentile); });
      if (cand.length) {
        cand.sort(function (a, b) { return (+a.cutoff_percentile) - (+b.cutoff_percentile) || (a.seat_type_code < b.seat_type_code ? -1 : 1); });
        return { value: +cand[0].cutoff_percentile, round: rd, seatType: cand[0].seat_type_code, docId: cand[0].source_doc_id };
      }
    }
    return null;
  }

  /* ---------- main ---------- */
  function recommend(input, rawData, userOptions) {
    var cfg = merge(DEFAULTS, userOptions || {});
    var v = validateInput(input);
    if (!v.ok) return { ok: false, errors: v.errors };
    var data = prepare(rawData), warnings = [];
    var asOf = cfg.asOfDate || new Date().toISOString().slice(0, 10);

    // current admission year
    var currentYear = input.admissionYear && input.admissionYear !== "auto" ? input.admissionYear : null;
    var lkg = data.data_version.filter(function (r) { return r.is_last_known_good === "TRUE"; })[0];
    if (!currentYear && lkg && yearStart(lkg.admission_year) !== null) currentYear = lkg.admission_year;
    if (!currentYear) return { ok: false, errors: ["Cannot determine the current admission year from the data. Please choose the admission year."] };
    var histYears = previousYears(currentYear, cfg.historyYears);

    var student = { percentile: input.percentile, candidateType: input.candidateType, category: input.category, gender: input.gender || null };
    var priorities = (input.priorities && input.priorities.length) ? input.priorities : ["balanced"];
    if (input.extraEligibility && input.extraEligibility.length) warnings.push("Extra eligibility claims (" + input.extraEligibility.join(", ") + ") are not applied yet because no matching official cutoff data is loaded.");

    var meta = {
      dataVersion: lkg ? lkg.data_version : null, currentAdmissionYear: currentYear, historicalYears: histYears,
      lastSuccessfulUpdate: null, usingSyntheticData: false, priorities: priorities, warnings: warnings
    };
    var succ = data.refresh_status.filter(function (r) { return r.status === "success"; }).sort(function (a, b) { return a.finished_at < b.finished_at ? 1 : -1; })[0];
    if (succ) meta.lastSuccessfulUpdate = succ.finished_at;
    if (lkg && lkg.is_synthetic === "TRUE") meta.usingSyntheticData = true;

    var eligibleCodes = eligibleSeatTypes(student, data.seat_types, cfg);
    var eligible = new Set(eligibleCodes);
    meta.seatTypesUsed = eligibleCodes;
    if (!eligibleCodes.length) {
      warnings.push("No cutoff group in the data matches this candidate type, category and gender, so no recommendation can be made.");
      return { ok: true, meta: meta, counts: { totalChoices: data.branches.length, ranked: 0 }, results: [], insufficientData: [] };
    }

    var docs = new Map(data.source_documents.map(function (d) { return [d.doc_id, d]; }));
    var colleges = new Map(data.colleges.map(function (c) { return [c.college_code, c]; }));
    var histBy = groupBy(data.historical_cutoffs, function (r) { return r.choice_code + "|" + r.admission_year; });
    var curBy = groupBy(data.current_cutoffs.filter(function (r) { return r.admission_year === currentYear; }), function (r) { return r.choice_code; });

    // Vacancy: pick ONE dataset-wide round (IV if any genuine IV vacancy exists, otherwise III). Never I or II.
    var vacRowsAll = data.vacancies.filter(function (r) {
      var dc = docs.get(r.source_doc_id);
      return r.admission_year === currentYear && cfg.vacancyRounds.indexOf(r.cap_round) >= 0 && dc && dc.doc_type === "vacancy_position" && /^\d+$/.test(r.vacancy_count);
    });
    var vacRound = null;
    for (var vi = 0; vi < cfg.vacancyRounds.length && !vacRound; vi++)
      if (vacRowsAll.some(function (r) { return r.cap_round === cfg.vacancyRounds[vi]; })) vacRound = cfg.vacancyRounds[vi];
    var vacBy = groupBy(vacRowsAll.filter(function (r) { return r.cap_round === vacRound; }), function (r) { return r.choice_code; });
    meta.vacancyRoundUsed = vacRound;
    if (!vacRound) warnings.push("Vacancy data unavailable: no Round IV or Round III vacancy-position data found for " + currentYear + ".");

    var feeByCollege = groupBy(data.fees, function (r) { return r.college_code; });
    var qiBy = groupBy(data.quality_indicators, function (r) { return r.college_code + "|" + r.indicator; });
    var plBy = groupBy(data.placements.filter(function (r) { return r.metric === "placement_percent"; }), function (r) { return r.college_code; });
    var accBy = groupBy(data.accreditation, function (r) { return r.college_code; });

    var branchRank = new Map(input.branches.map(function (b, i) { return [norm(b), i + 1]; }));
    var anyDistrict = input.districts.length === 1 && input.districts[0] === "ANY";
    var districtRank = new Map(anyDistrict ? [] : input.districts.map(function (d, i) { return [normDistrict(d), i + 1]; }));
    var matchedBranchNames = new Set();

    var funnel = { totalChoices: 0, afterBranch: 0, afterDistrict: 0, afterFee: 0, belowRange: 0, insufficientData: 0, ranked: 0 };
    var cands = [], insufficient = [];

    data.branches.forEach(function (b) {
      var col = colleges.get(b.college_code); if (!col) return;
      funnel.totalChoices++;
      var br = branchRank.get(norm(b.branch_name)); if (!br) return;
      matchedBranchNames.add(norm(b.branch_name)); funnel.afterBranch++;
      var dr = anyDistrict ? 0 : districtRank.get(normDistrict(col.district)); if (dr === undefined) return;
      funnel.afterDistrict++;

      // fee
      var fee = feeFor(b, feeByCollege.get(b.college_code) || [], input.feeBasis);
      if (fee.excluded(input.maxAnnualFeeINR)) return;
      funnel.afterFee++;

      // cutoffs
      var points = [], cur = pickCutoff(curBy.get(b.choice_code), eligible, cfg);
      if (cur) points.push({ label: "current", age: 0, value: cur.value, w: cfg.evidenceWeights.current });
      var hist = histYears.map(function (y, i) {
        var h = pickCutoff(histBy.get(b.choice_code + "|" + y), eligible, cfg);
        if (h) points.push({ label: "hist" + (i + 1), age: i + 1, value: h.value, w: cfg.evidenceWeights.hist[i] || 0 });
        return h ? { year: y, value: h.value, round: h.round, seatType: h.seatType, docId: h.docId } : { year: y, value: null, round: null, seatType: null, docId: null };
      });
      var base = { b: b, col: col, br: br, dr: dr, fee: fee, cur: cur, hist: hist, points: points };
      if (!points.length) { funnel.insufficientData++; insufficient.push(basicInfo(base)); return; }

      var wsum = points.reduce(function (s, p) { return s + p.w; }, 0);
      var avg = points.reduce(function (s, p) { return s + p.w * p.value; }, 0) / wsum;
      var hp = points.filter(function (p) { return p.age > 0; }).sort(function (a, c) { return c.age - a.age; });   // oldest first
      var trend = 0;
      if (hp.length >= 2) trend = (hp[hp.length - 1].value - hp[0].value) / (hp[0].age - hp[hp.length - 1].age);
      var adj = clamp(cfg.trend.weight * Math.max(trend, 0), 0, cfg.trend.maxAdjust);
      var expected = avg + adj, margin = student.percentile - expected;
      var maxCut = Math.max.apply(null, points.map(function (p) { return p.value; }));
      var t = cfg.thresholds, label;
      if (margin < -t.ambitiousLimit) { funnel.belowRange++; return; }
      if (points.length < 2) label = "Limited evidence";
      else if (student.percentile >= maxCut + t.saferMargin) label = "Historically more suitable";
      else if (margin >= -t.uncertainTolerance) label = "Possible but uncertain";
      else label = "Ambitious choice";
      base.expected = expected; base.margin = margin; base.label = label; base.trendAdj = adj; base.trend = trend; base.maxCut = maxCut;
      cands.push(base);
    });

    input.branches.forEach(function (n) { if (!matchedBranchNames.has(norm(n))) warnings.push("No branch named \"" + n + "\" exists in the data, so it was skipped."); });

    // scoring
    var wvec = {};
    COMPONENTS.forEach(function (c) { wvec[c] = 0; });
    priorities.forEach(function (p) { COMPONENTS.forEach(function (c) { wvec[c] += cfg.weights[p][c] / priorities.length; }); });

    var out = cands.map(function (c) {
      var b = c.b, col = c.col;
      var vac = vacFor(vacBy.get(b.choice_code), eligible, vacRound);
      var q = function (ind) {
        var rows = (qiBy.get(b.college_code + "|" + ind) || []).slice().sort(function (x, y) { return x.computed_date < y.computed_date ? 1 : -1; });
        return rows.length ? { score: +rows[0].score_0_10, isEstimate: rows[0].is_estimate === "TRUE", method: rows[0].method_version, docId: rows[0].source_doc_id } : null;
      };
      var teaching = q("teaching"), infra = q("infrastructure");
      var plc = placementFor(b, plBy.get(b.college_code) || []);
      var acc = accreditationFor(b, accBy.get(b.college_code) || [], asOf);

      var sc = {
        fit: clamp(70 + 6 * c.margin, 0, 100),
        branch: Math.max(40, 100 - 15 * (c.br - 1)),
        district: anyDistrict ? 70 : Math.max(40, 100 - 15 * (c.dr - 1)),
        placement: plc ? clamp(plc.value, 0, 100) : null,
        teaching: teaching ? teaching.score * 10 : null,
        infrastructure: infra ? infra.score * 10 : null,
        fee: c.fee.value !== null && c.fee.basisMatches ? clamp(100 - 70 * c.fee.value / input.maxAnnualFeeINR, 0, 100) : null,
        accreditation: acc.score
      };
      var num = 0, den = 0, have = 0;
      COMPONENTS.forEach(function (k) { if (sc[k] !== null) { num += wvec[k] * sc[k]; den += wvec[k]; have++; } });
      var score = den ? num / den : 0;
      if (c.label === "Limited evidence") score *= cfg.limitedEvidencePenalty;
      // vacancy nudges the ranking slightly; it never changes the suitability label and is never a guarantee
      var vacNote = 0;
      if (vac && vac.value > 0) vacNote = 1; else if (vac && vac.value === 0) vacNote = -1;
      score += vacNote * 1.0;

      var srcIds = new Set();
      [c.cur && c.cur.docId, vac && vac.docId, c.fee.docId, plc && plc.docId, teaching && teaching.docId, infra && infra.docId, acc.docIds].forEach(function (x) {
        (Array.isArray(x) ? x : [x]).forEach(function (y) { if (y) srcIds.add(y); });
      });
      c.hist.forEach(function (h) { if (h.docId) srcIds.add(h.docId); });
      var sources = Array.from(srcIds).sort().map(function (id) {
        var d = docs.get(id); if (d && d.is_synthetic === "TRUE") meta.usingSyntheticData = true;
        return d ? { doc_id: d.doc_id, source_name: d.source_name, source_url: d.source_url, doc_type: d.doc_type, admission_year: d.admission_year, cap_round: d.cap_round, published_date: d.published_date, retrieved_date: d.retrieved_date } : { doc_id: id };
      });

      return {
        score: round2(score), choiceCode: b.choice_code, collegeCode: col.college_code, collegeName: col.college_name,
        branchCode: b.branch_code, branchName: b.branch_name, district: col.district,
        collegeWebsite: col.college_website || null, autonomy: col.autonomy_status || null,
        historicalCutoffs: c.hist,
        currentCutoff: c.cur ? { year: currentYear, value: c.cur.value, round: c.cur.round, seatType: c.cur.seatType } : null,
        vacancy: vac ? { value: vac.value, round: vacRound, status: "ok" } : { value: null, round: null, status: "Vacancy data unavailable" },
        fee: { value: c.fee.value, type: c.fee.type, academicYear: c.fee.year, status: c.fee.status, tuitionLowerBound: c.fee.tuitionFloor },
        infrastructure: infra ? { score_0_10: infra.score, isEstimate: infra.isEstimate, method: infra.method } : null,
        teaching: teaching ? { score_0_10: teaching.score, isEstimate: teaching.isEstimate, method: teaching.method } : null,
        placement: plc ? { metric: "placement_percent", value: plc.value, year: plc.year, scope: plc.scope } : null,
        nba: acc.nba, naac: acc.naac,
        suitability: c.label, expectedCutoff: round2(c.expected), marginVsExpected: round2(c.margin),
        componentScores: sc, dataCompleteness: round2(have / COMPONENTS.length),
        explanation: explain(c, input, currentYear, vac, vacRound, plc, teaching, infra, acc, anyDistrict, sc),
        sources: sources, _tie: [c.br, c.dr]
      };
    });

    out.sort(function (a, b) {
      return b.score - a.score || a._tie[0] - b._tie[0] || a._tie[1] - b._tie[1] || (a.choiceCode < b.choiceCode ? -1 : 1);
    });
    funnel.ranked = out.length;
    var results = out.slice(0, cfg.maxResults).map(function (r, i) { r.rank = i + 1; delete r._tie; return r; });
    if (results.length === 0) warnings.push("No choices matched your criteria with enough data. Try adding branches or districts, or raising your budget.");
    else if (results.length < 5) warnings.push("Only " + results.length + " choice(s) matched your criteria with enough data; fewer than five can be shown.");
    return { ok: true, meta: meta, counts: funnel, results: results, insufficientData: insufficient };
  }

  /* ---------- sub-rules ---------- */
  function feeFor(branch, rows, basis) {
    var res = { value: null, type: basis, year: null, status: "unavailable", basisMatches: false, tuitionFloor: null, docId: null,
      excluded: function (budget) { return false; } };
    function latest(type) {
      var r = rows.filter(function (x) { return x.fee_type === type && /^\d+$/.test(x.annual_fee_inr) && (!x.choice_code || x.choice_code === branch.choice_code); });
      if (!r.length) return null;
      var yr = r.map(function (x) { return x.academic_year; }).sort().pop();
      var ry = r.filter(function (x) { return x.academic_year === yr; });
      var spec = ry.filter(function (x) { return x.choice_code === branch.choice_code; });
      var pool = spec.length ? spec : ry;
      var top = pool.slice().sort(function (a, b) { return (+b.annual_fee_inr) - (+a.annual_fee_inr); })[0];   // several scopes: use the highest (conservative)
      return { value: +top.annual_fee_inr, year: yr, docId: top.source_doc_id };
    }
    var f = latest(basis);
    if (f) { res.value = f.value; res.year = f.year; res.docId = f.docId; res.status = "ok"; res.basisMatches = true; }
    else if (basis === "total") {
      var t = latest("tuition");    // total can never be lower than tuition, so tuition is a safe lower bound
      if (t) { res.tuitionFloor = t.value; res.year = t.year; res.docId = t.docId; res.status = "total_unavailable_tuition_known"; }
    }
    res.excluded = function (budget) {
      if (res.value !== null) return res.value > budget;
      if (res.tuitionFloor !== null) return res.tuitionFloor > budget;
      return false;   // unknown fee: keep, but flag
    };
    return res;
  }
  function vacFor(rows, eligible, round) {
    if (!rows || !round) return null;
    var all = rows.filter(function (r) { return r.seat_type_code === "ALL"; });
    if (all.length) return { value: +all[0].vacancy_count, docId: all[0].source_doc_id };
    var el = rows.filter(function (r) { return eligible.has(r.seat_type_code); });
    if (!el.length) return null;
    return { value: el.reduce(function (s, r) { return s + (+r.vacancy_count); }, 0), docId: el[0].source_doc_id };
  }
  function placementFor(branch, rows) {
    var cand = rows.filter(function (r) { return isFinite(+r.value) && (r.scope === "institution" || (r.scope === "branch" && r.choice_code === branch.choice_code)); });
    if (!cand.length) return null;
    var yr = cand.map(function (r) { return r.placement_year; }).sort().pop();
    var ry = cand.filter(function (r) { return r.placement_year === yr; });
    var pick = ry.filter(function (r) { return r.scope === "branch"; })[0] || ry[0];
    return { value: +pick.value, year: yr, scope: pick.scope, docId: pick.source_doc_id };
  }
  function accStatus(row, asOf) {
    if (!row) return null;
    var o = { status: row.status, grade: row.grade || null, validTo: row.valid_to || null };
    if (row.status === "accredited") {
      if (!row.valid_to) o.status = "validity_unknown";
      else if (row.valid_to < asOf) o.status = "expired";
      else o.status = "valid";
    }
    return o;
  }
  function accreditationFor(branch, rows, asOf) {
    var pick = function (body, scope, choice) {
      var r = rows.filter(function (x) { return x.body === body && x.scope === scope && (!choice || x.choice_code === choice); })
        .sort(function (a, b) { return (a.valid_to || "") < (b.valid_to || "") ? 1 : -1; })[0];
      return r || null;
    };
    var nr = pick("NBA", "program", branch.choice_code), ar = pick("NAAC", "institution");
    var nba = accStatus(nr, asOf), naac = accStatus(ar, asOf);
    var score = null, ids = [];
    if (nr) ids.push(nr.source_doc_id); if (ar) ids.push(ar.source_doc_id);
    var naacOk = naac && naac.status === "valid" && GRADE_SCORE[naac.grade] !== undefined, nbaOk = nba && nba.status === "valid";
    if (naacOk) score = Math.min(100, GRADE_SCORE[naac.grade] + (nbaOk ? 15 : 0));
    else if (nbaOk) score = 60;
    return { nba: nba, naac: naac, score: score, docIds: ids };
  }
  function basicInfo(c) {
    return { choiceCode: c.b.choice_code, collegeName: c.col.college_name, branchName: c.b.branch_name, district: c.col.district, reason: "No usable cutoff data for your category in the last three years or the current year." };
  }
  function explain(c, input, curYear, vac, vacRound, plc, teaching, infra, acc, anyDistrict, sc) {
    var L = [], p = input.percentile;
    L.push("Matches your branch choice #" + c.br + " (" + c.b.branch_name + ").");
    L.push(anyDistrict ? "Located in " + c.col.district + " (you chose any district)." : "Located in " + c.col.district + ", your district choice #" + c.dr + ".");
    var parts = c.points.map(function (pt) { return (pt.label === "current" ? "current " + curYear : "year " + c.hist[pt.age - 1].year) + ": " + pt.value.toFixed(2); });
    L.push("Your percentile " + p + " compared with cutoffs (" + parts.join("; ") + "); expected cutoff about " + c.expected.toFixed(2) + (c.trendAdj > 0 ? " (includes +" + c.trendAdj.toFixed(2) + " because earlier cutoffs were rising)" : "") + ".");
    L.push("Assessment: " + c.label + ". This is a rule-based guide from past cutoffs, not a probability or a guarantee.");
    if (c.cur && c.cur.round !== "IV") L.push("Current-year cutoff is from CAP Round " + c.cur.round + "; earlier rounds usually show higher cutoffs than the final round, so this may look tougher than the final outcome.");
    if (c.points.length < 3) L.push("Only " + c.points.length + " cutoff data point(s) available; treat with extra caution.");
    if (vac) L.push("Latest genuine vacancy (CAP Round " + vacRound + "): " + vac.value + " seat(s). Vacancy does not guarantee admission.");
    else L.push("Vacancy data unavailable.");
    if (c.fee.status === "ok") L.push("Fee: Rs " + c.fee.value + " per year (" + c.fee.type + ", " + c.fee.year + ") against your budget of Rs " + input.maxAnnualFeeINR + ".");
    else if (c.fee.status === "total_unavailable_tuition_known") L.push("Total yearly cost is not available; tuition alone is Rs " + c.fee.tuitionFloor + " (" + c.fee.year + "), and total cost will be higher.");
    else L.push("Fee data not available; check the college before relying on your budget.");
    if (c.fee.year && c.fee.year !== curYear && c.fee.status !== "unavailable") L.push("Fee data is for " + c.fee.year + ", not " + curYear + ".");
    if (c.fee.status === "ok" && input.feeBasis === "tuition") L.push("This is a tuition fee and does not include hostel, transport or exam charges.");
    if (acc.naac) L.push("NAAC: " + (acc.naac.grade || "grade not stated") + " (" + acc.naac.status + (acc.naac.validTo ? ", until " + acc.naac.validTo : "") + ").");
    if (acc.nba) L.push("NBA for this program: " + acc.nba.status + (acc.nba.validTo ? " (until " + acc.nba.validTo + ")" : "") + ".");
    if (plc) L.push("Placement: " + plc.value + "% placed in " + plc.year + " (" + plc.scope + " level).");
    var est = []; if (teaching) est.push("teaching " + teaching.score + "/10"); if (infra) est.push("infrastructure " + infra.score + "/10");
    if (est.length) L.push("System estimates (not official scores): " + est.join(", ") + ".");
    var miss = []; if (!plc) miss.push("placement"); if (!teaching) miss.push("teaching"); if (!infra) miss.push("infrastructure"); if (!acc.naac && !acc.nba) miss.push("accreditation");
    if (miss.length) L.push("Not available: " + miss.join(", ") + ".");
    return L;
  }

  return { recommend: recommend, validateInput: validateInput, previousYears: previousYears, eligibleSeatTypes: eligibleSeatTypes,
    normDistrict: normDistrict, DEFAULTS: DEFAULTS };
});
