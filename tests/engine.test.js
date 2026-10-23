// Stage 4 tests. They use SYNTHETIC data only. Passing proves the rules are coded as written,
// NOT that real CET Cell data is handled correctly (that is tested in later stages).
// Run from the repository root:  node --test tests/
const test = require("node:test"), assert = require("node:assert/strict");
const path = require("path");
const R = require("../recommendation/engine.js");
const { loadDir } = require("./helpers/csv.js");
const SYN = loadDir(path.join(__dirname, "..", "data", "synthetic"));
const clone = o => JSON.parse(JSON.stringify(o));
const AS_OF = { asOfDate: "2026-10-22" };
const base = () => ({ percentile: 90, admissionYear: "auto", candidateType: "Maharashtra State candidate", category: "Open", gender: null,
  extraEligibility: [], branches: ["Computer Science and Engineering", "Computer Engineering", "Information Technology"], districts: ["ANY"],
  maxAnnualFeeINR: 400000, feeBasis: "tuition", priorities: ["balanced"] });

/* ---- tiny hand-made dataset for exact rule checks ---- */
function mini(over) {
  const D = { colleges: [], branches: [], seat_types: [{ seat_type_code: "GOPENS", candidate_type: "Maharashtra State candidate", category: "Open", gender_scope: "" },
      { seat_type_code: "GSCS", candidate_type: "Maharashtra State candidate", category: "SC", gender_scope: "" },
      { seat_type_code: "LOPENS", candidate_type: "Maharashtra State candidate", category: "Open", gender_scope: "Female" }],
    historical_cutoffs: [], current_cutoffs: [], vacancies: [], fees: [], accreditation: [], placements: [], quality_indicators: [],
    source_documents: [{ doc_id: "D-VAC", doc_type: "vacancy_position", cap_round: "III", source_name: "t", source_url: "u" }, { doc_id: "D-VAC4", doc_type: "vacancy_position", cap_round: "IV", source_name: "t", source_url: "u" },
      { doc_id: "D-MAT", doc_type: "seat_matrix", source_name: "t", source_url: "u" }, { doc_id: "D-CUT", doc_type: "cutoff", source_name: "t", source_url: "u" }],
    refresh_status: [], data_version: [{ data_version: "T1", is_last_known_good: "TRUE", admission_year: "2026-27", validation_status: "validated", is_synthetic: "TRUE" }] };
  let n = 0;
  D.addCollege = (code, district, extra) => { D.colleges.push(Object.assign({ college_code: code, college_name: "C" + code, district: district || "Pune", validation_status: "validated" }, extra)); };
  D.addBranch = (code, college, name) => { D.branches.push({ choice_code: code, college_code: college, branch_code: "B", branch_name: name || "Computer Engineering", validation_status: "validated" }); };
  D.addCut = (tbl, choice, year, round, seat, val) => { D[tbl].push({ cutoff_id: "X" + (++n), choice_code: choice, admission_year: year, cap_round: round, seat_type_code: seat, cutoff_percentile: String(val), source_doc_id: "D-CUT", validation_status: "validated" }); };
  D.addVac = (choice, round, seat, count, doc) => { D.vacancies.push({ vacancy_id: "V" + (++n), choice_code: choice, admission_year: "2026-27", cap_round: round, seat_type_code: seat, vacancy_count: String(count), source_doc_id: doc || (round === "IV" ? "D-VAC4" : "D-VAC"), validation_status: "validated" }); };
  D.addFee = (college, type, amt, year) => { D.fees.push({ fee_id: "F" + (++n), college_code: college, choice_code: "", academic_year: year || "2026-27", fee_type: type, annual_fee_inr: String(amt), source_doc_id: "D-CUT", validation_status: "validated" }); };
  return D;
}
const simple = (cut) => { const D = mini(); D.addCollege("A"); D.addBranch("A-1", "A"); ["2025-26", "2024-25", "2023-24"].forEach(y => D.addCut("historical_cutoffs", "A-1", y, "IV", "GOPENS", cut)); return D; };
const stripHelpers = D => { const c = Object.assign({}, D); delete c.addCollege; delete c.addBranch; delete c.addCut; delete c.addVac; delete c.addFee; return c; };
const run = (inp, D, o) => R.recommend(inp, stripHelpers(D), Object.assign({}, AS_OF, o || {}));

/* ---- admission years ---- */
test("previous three admission years exclude the current year", () => {
  assert.deepEqual(R.previousYears("2027-28", 3), ["2026-27", "2025-26", "2024-25"]);
  assert.deepEqual(R.previousYears("2000-01", 2), ["1999-00", "1998-99"]);
  assert.throws(() => R.previousYears("2026-28", 3));
});
test("auto year comes from last-known-good data version", () => {
  const r = R.recommend(base(), SYN, AS_OF); assert.equal(r.ok, true);
  assert.equal(r.meta.currentAdmissionYear, "2026-27"); assert.deepEqual(r.meta.historicalYears, ["2025-26", "2024-25", "2023-24"]);
});
test("cannot determine year -> clear error, no results", () => {
  const D = clone(SYN); D.data_version = []; const r = R.recommend(base(), D, AS_OF);
  assert.equal(r.ok, false); assert.match(r.errors[0], /admission year/);
});
test("only the previous three years are used; older years ignored", () => {
  const D = mini(); D.addCollege("A"); D.addBranch("A-1", "A");
  D.addCut("historical_cutoffs", "A-1", "2022-23", "IV", "GOPENS", 50);   // 4 years back: must be ignored
  D.addCut("historical_cutoffs", "A-1", "2025-26", "IV", "GOPENS", 85);
  const r = run(Object.assign(base(), { percentile: 90 }), D);
  assert.equal(r.results[0].historicalCutoffs.length, 3);
  assert.deepEqual(r.results[0].historicalCutoffs.map(h => h.value), [85, null, null]);
});

/* ---- input validation ---- */
test("invalid input is rejected with errors", () => {
  for (const patch of [{ percentile: 101 }, { percentile: "90" }, { branches: [] }, { branches: ["a", "a"] }, { districts: [] }, { maxAnnualFeeINR: 0 }, { maxAnnualFeeINR: 1.5 }, { feeBasis: "x" }, { admissionYear: "2026-28" }, { priorities: ["nope"] }, { category: "" }]) {
    const r = R.recommend(Object.assign(base(), patch), SYN, AS_OF); assert.equal(r.ok, false, JSON.stringify(patch)); assert.ok(r.errors.length);
  }
});

/* ---- seat types ---- */
test("seat-type matching: category, gender, candidate type", () => {
  const st = SYN.seat_types, cfg = R.DEFAULTS;
  const mk = o => R.eligibleSeatTypes(Object.assign({ candidateType: "Maharashtra State candidate", category: "Open", gender: null }, o), st, cfg).sort();
  assert.deepEqual(mk({}), ["GOPENS"]);
  assert.deepEqual(mk({ gender: "Female" }), ["GOPENS", "LOPENS"]);
  assert.deepEqual(mk({ category: "SC" }), ["GOPENS", "GSCS"]);
  assert.deepEqual(mk({ candidateType: "All India candidate" }), []);
});
test("no matching cutoff group -> honest empty result with warning", () => {
  const r = R.recommend(Object.assign(base(), { candidateType: "All India candidate" }), SYN, AS_OF);
  assert.equal(r.ok, true); assert.equal(r.results.length, 0); assert.ok(r.meta.warnings.some(w => /No cutoff group/.test(w)));
});
test("Female student gets the more favourable (lower) of the eligible cutoffs", () => {
  const D = simple(80); D.addCut("historical_cutoffs", "A-1", "2025-26", "IV", "LOPENS", 70);
  const f = run(Object.assign(base(), { gender: "Female" }), D), m = run(base(), D);
  assert.equal(f.results[0].historicalCutoffs[0].value, 70); assert.equal(m.results[0].historicalCutoffs[0].value, 80);
});

/* ---- current cutoff round priority IV > III > II > I ---- */
test("current cutoff uses latest round: IV>III>II>I", () => {
  const D = simple(80);
  D.addCut("current_cutoffs", "A-1", "2026-27", "I", "GOPENS", 90);
  assert.equal(run(base(), D).results[0].currentCutoff.round, "I");
  D.addCut("current_cutoffs", "A-1", "2026-27", "II", "GOPENS", 89);
  assert.equal(run(base(), D).results[0].currentCutoff.round, "II");
  D.addCut("current_cutoffs", "A-1", "2026-27", "IV", "GOPENS", 87);
  D.addCut("current_cutoffs", "A-1", "2026-27", "III", "GOPENS", 88);
  const c = run(base(), D).results[0].currentCutoff; assert.equal(c.round, "IV"); assert.equal(c.value, 87);
});
test("synthetic data (rounds I-III only) reports Round III as the round used", () => {
  const r = R.recommend(base(), SYN, AS_OF); assert.ok(r.results.length > 0);
  r.results.forEach(x => { if (x.currentCutoff) assert.equal(x.currentCutoff.round, "III"); });
});

/* ---- vacancy: strictly Round IV, else Round III ---- */
test("vacancy: Round IV preferred over Round III", () => {
  const D = simple(80); D.addVac("A-1", "III", "ALL", 5); D.addVac("A-1", "IV", "ALL", 2);
  const v = run(base(), D).results[0].vacancy; assert.equal(v.round, "IV"); assert.equal(v.value, 2);
});
test("vacancy: Round III used when no Round IV exists", () => {
  const D = simple(80); D.addVac("A-1", "III", "ALL", 5);
  const v = run(base(), D).results[0].vacancy; assert.equal(v.round, "III"); assert.equal(v.value, 5);
});
test("vacancy: a choice missing from Round IV is NOT filled from Round III", () => {
  const D = simple(80); D.addCollege("B"); D.addBranch("B-1", "B");
  ["2025-26"].forEach(y => D.addCut("historical_cutoffs", "B-1", y, "IV", "GOPENS", 80));
  D.addVac("A-1", "IV", "ALL", 2); D.addVac("B-1", "III", "ALL", 9);
  const r = run(base(), D); const b = r.results.find(x => x.choiceCode === "B-1");
  assert.equal(b.vacancy.value, null); assert.equal(b.vacancy.status, "Vacancy data unavailable");
});
test("vacancy: Round I and II rows are never used", () => {
  const D = simple(80); D.vacancies.push({ vacancy_id: "Z1", choice_code: "A-1", admission_year: "2026-27", cap_round: "II", seat_type_code: "ALL", vacancy_count: "7", source_doc_id: "D-VAC", validation_status: "validated" });
  const r = run(base(), D); assert.equal(r.results[0].vacancy.status, "Vacancy data unavailable"); assert.equal(r.meta.vacancyRoundUsed, null);
});
test("vacancy: seat-matrix document is rejected as a source", () => {
  const D = simple(80); D.addVac("A-1", "III", "ALL", 50, "D-MAT");
  assert.equal(run(base(), D).results[0].vacancy.status, "Vacancy data unavailable");
});
test("vacancy: zero is shown as 0 only when genuinely reported; missing stays null", () => {
  const D = simple(80); D.addVac("A-1", "III", "ALL", 0);
  assert.equal(run(base(), D).results[0].vacancy.value, 0);
  assert.equal(run(base(), simple(80)).results[0].vacancy.value, null);
});
test("vacancy per seat type is summed over eligible seat types only", () => {
  const D = simple(80); D.addVac("A-1", "III", "GOPENS", 3); D.addVac("A-1", "III", "GSCS", 4); D.addVac("A-1", "III", "LOPENS", 10);
  assert.equal(run(base(), D).results[0].vacancy.value, 3);
  assert.equal(run(Object.assign(base(), { category: "SC" }), D).results[0].vacancy.value, 7);
});
test("synthetic data: some choices have no vacancy and say so", () => {
  const r = R.recommend(base(), SYN, AS_OF); const un = r.results.filter(x => x.vacancy.value === null);
  un.forEach(x => assert.equal(x.vacancy.status, "Vacancy data unavailable")); assert.ok(r.meta.vacancyRoundUsed === "III");
});

/* ---- branch / district filters ---- */
test("branch and district filters (incl. renamed districts and ANY)", () => {
  const D = mini(); D.addCollege("A", "Pune"); D.addCollege("B", "Chhatrapati Sambhajinagar (Aurangabad)"); D.addCollege("C", "Nagpur");
  [["A-1", "A", "Computer Engineering"], ["A-2", "A", "Civil Engineering"], ["B-1", "B", "Computer Engineering"], ["C-1", "C", "Computer Engineering"]].forEach(x => { D.addBranch(x[0], x[1], x[2]); D.addCut("historical_cutoffs", x[0], "2025-26", "IV", "GOPENS", 80); });
  const names = r => r.results.map(x => x.choiceCode).sort();
  assert.deepEqual(names(run(Object.assign(base(), { branches: ["Computer Engineering"], districts: ["ANY"] }), D)), ["A-1", "B-1", "C-1"]);
  assert.deepEqual(names(run(Object.assign(base(), { branches: ["Computer Engineering"], districts: ["Pune"] }), D)), ["A-1"]);
  assert.deepEqual(names(run(Object.assign(base(), { branches: ["Computer Engineering"], districts: ["Aurangabad"] }), D)), ["B-1"]);
  assert.deepEqual(names(run(Object.assign(base(), { branches: ["Civil Engineering"], districts: ["Nagpur", "Pune"] }), D)), ["A-2"]);
  const w = run(Object.assign(base(), { branches: ["Chemical Engineering"] }), D); assert.equal(w.results.length, 0); assert.ok(w.meta.warnings.some(x => /Chemical/.test(x)));
});
test("a higher-ranked preferred branch/district outranks otherwise-equal choices", () => {
  const D = mini(); D.addCollege("A", "Pune"); D.addCollege("B", "Nagpur");
  D.addBranch("A-1", "A", "Computer Engineering"); D.addBranch("B-1", "B", "Computer Engineering");
  ["A-1", "B-1"].forEach(c => D.addCut("historical_cutoffs", c, "2025-26", "IV", "GOPENS", 80));
  const r = run(Object.assign(base(), { branches: ["Computer Engineering"], districts: ["Nagpur", "Pune"] }), D);
  assert.deepEqual(r.results.map(x => x.choiceCode), ["B-1", "A-1"]);
});

/* ---- fees ---- */
test("fee filter: over-budget removed, unknown kept and flagged, tuition never shown as total", () => {
  const D = mini(); ["A", "B", "C"].forEach(c => { D.addCollege(c); D.addBranch(c + "-1", c); D.addCut("historical_cutoffs", c + "-1", "2025-26", "IV", "GOPENS", 80); });
  D.addFee("A", "tuition", 100000); D.addFee("B", "tuition", 300000);   // C has no fee data
  const r = run(Object.assign(base(), { maxAnnualFeeINR: 150000 }), D);
  assert.deepEqual(r.results.map(x => x.choiceCode).sort(), ["A-1", "C-1"]);
  assert.equal(r.results.find(x => x.choiceCode === "C-1").fee.status, "unavailable");
  const t = run(Object.assign(base(), { maxAnnualFeeINR: 150000, feeBasis: "total" }), D);
  const a = t.results.find(x => x.choiceCode === "A-1");
  assert.equal(a.fee.value, null); assert.equal(a.fee.status, "total_unavailable_tuition_known"); assert.equal(a.fee.tuitionLowerBound, 100000);
  assert.ok(!t.results.some(x => x.choiceCode === "B-1"));   // tuition alone already exceeds budget
});
test("latest fee year is used and stale year is flagged", () => {
  const D = simple(80); D.addFee("A", "tuition", 90000, "2025-26"); D.addFee("A", "tuition", 100000, "2024-25");
  const x = run(base(), D).results[0]; assert.equal(x.fee.value, 90000); assert.ok(x.explanation.some(l => /not 2026-27/.test(l)));
});

/* ---- suitability labels ---- */
test("suitability labels follow the documented thresholds", () => {
  const lab = (pct, cut) => run(Object.assign(base(), { percentile: pct }), simple(cut)).results[0];
  assert.equal(lab(90, 80).suitability, "Historically more suitable");      // 90 >= 80+1
  assert.equal(lab(80.5, 80).suitability, "Possible but uncertain");        // above expected but inside buffer
  assert.equal(lab(78.5, 80).suitability, "Possible but uncertain");        // margin -1.5 within -2
  assert.equal(lab(76, 80).suitability, "Ambitious choice");                // margin -4
  assert.equal(run(Object.assign(base(), { percentile: 70 }), simple(80)).results.length, 0);   // margin -10: not realistic, excluded
});
test("one data point -> Limited evidence; none -> Insufficient data (not ranked)", () => {
  const D = mini(); D.addCollege("A"); D.addBranch("A-1", "A"); D.addCollege("B"); D.addBranch("B-1", "B");
  D.addCut("historical_cutoffs", "A-1", "2025-26", "IV", "GOPENS", 70);
  const r = run(base(), D);
  assert.equal(r.results.length, 1); assert.equal(r.results[0].suitability, "Limited evidence");
  assert.equal(r.insufficientData.length, 1); assert.equal(r.insufficientData[0].choiceCode, "B-1");
});
test("rising historical cutoffs raise the expected cutoff (conservative); falling ones are not credited", () => {
  const up = mini(); up.addCollege("A"); up.addBranch("A-1", "A");
  up.addCut("historical_cutoffs", "A-1", "2023-24", "IV", "GOPENS", 70); up.addCut("historical_cutoffs", "A-1", "2024-25", "IV", "GOPENS", 75); up.addCut("historical_cutoffs", "A-1", "2025-26", "IV", "GOPENS", 80);
  const dn = mini(); dn.addCollege("A"); dn.addBranch("A-1", "A");
  dn.addCut("historical_cutoffs", "A-1", "2023-24", "IV", "GOPENS", 80); dn.addCut("historical_cutoffs", "A-1", "2024-25", "IV", "GOPENS", 75); dn.addCut("historical_cutoffs", "A-1", "2025-26", "IV", "GOPENS", 70);
  const eu = run(base(), up).results[0].expectedCutoff, ed = run(base(), dn).results[0].expectedCutoff;
  assert.ok(eu > 75 && ed < 75);
  const flat = run(base(), simple(75)).results[0].expectedCutoff; assert.equal(flat, 75);
  assert.ok(run(base(), dn).results[0].expectedCutoff >= 70);
});
test("a round-I/II/III current cutoff gets a caveat in the explanation", () => {
  const D = simple(80); D.addCut("current_cutoffs", "A-1", "2026-27", "III", "GOPENS", 82);
  assert.ok(run(base(), D).results[0].explanation.some(l => /Round III.*higher cutoffs/.test(l)));
});

/* ---- ranking under priorities ---- */
function twoColleges() {
  const D = mini(); ["A", "B"].forEach(c => { D.addCollege(c); D.addBranch(c + "-1", c); ["2025-26", "2024-25", "2023-24"].forEach(y => D.addCut("historical_cutoffs", c + "-1", y, "IV", "GOPENS", 80)); });
  D.addFee("A", "tuition", 200000); D.addFee("B", "tuition", 60000);
  D.placements.push({ placement_id: "P1", college_code: "A", choice_code: "", placement_year: "2025-26", metric: "placement_percent", value: "95", scope: "institution", source_doc_id: "D-CUT", validation_status: "validated" });
  D.placements.push({ placement_id: "P2", college_code: "B", choice_code: "", placement_year: "2025-26", metric: "placement_percent", value: "40", scope: "institution", source_doc_id: "D-CUT", validation_status: "validated" });
  return D;
}
test("priorities change the ranking as documented", () => {
  const D = twoColleges(), top = p => run(Object.assign(base(), { priorities: p, maxAnnualFeeINR: 250000 }), D).results[0].choiceCode;
  assert.equal(top(["placements"]), "A-1"); assert.equal(top(["low_fees"]), "B-1");
});
test("multiple priorities blend their weights", () => {
  const D = twoColleges(); const r = run(Object.assign(base(), { priorities: ["placements", "low_fees"], maxAnnualFeeINR: 250000 }), D);
  assert.equal(r.results.length, 2); assert.ok(r.results[0].score >= r.results[1].score);
});
test("all weight rows sum to 1", () => {
  Object.entries(R.DEFAULTS.weights).forEach(([k, w]) => assert.ok(Math.abs(Object.values(w).reduce((a, b) => a + b, 0) - 1) < 1e-9, k));
});

/* ---- missing data ---- */
test("missing quality data is null and never treated as zero", () => {
  const r = run(base(), simple(80)).results[0];
  assert.equal(r.teaching, null); assert.equal(r.infrastructure, null); assert.equal(r.placement, null); assert.equal(r.nba, null); assert.equal(r.naac, null);
  assert.equal(r.componentScores.placement, null); assert.ok(r.dataCompleteness < 1); assert.ok(r.explanation.some(l => /Not available: placement, teaching, infrastructure, accreditation/.test(l)));
});
test("a college with missing data is not scored lower than one with poor data merely for being missing", () => {
  const D = twoColleges(); D.placements = D.placements.filter(p => p.college_code === "B");   // A has no placement data
  const r = run(Object.assign(base(), { priorities: ["placements"], maxAnnualFeeINR: 250000 }), D);
  const a = r.results.find(x => x.choiceCode === "A-1"), b = r.results.find(x => x.choiceCode === "B-1");
  assert.equal(a.placement, null); assert.ok(a.score > 0 && b.score > 0);
});
test("expired or undated accreditation is flagged and not scored; NBA absent is null not 'not accredited'", () => {
  const D = simple(80);
  D.accreditation.push({ accreditation_id: "AC1", college_code: "A", choice_code: "", body: "NAAC", scope: "institution", status: "accredited", grade: "A++", valid_from: "2015-01-01", valid_to: "2020-01-01", source_doc_id: "D-CUT", validation_status: "validated" });
  const x = run(base(), D).results[0]; assert.equal(x.naac.status, "expired"); assert.equal(x.componentScores.accreditation, null); assert.equal(x.nba, null);
  D.accreditation[0].valid_to = "2030-01-01"; assert.equal(run(base(), D).results[0].componentScores.accreditation, 100);
  D.accreditation[0].valid_to = ""; assert.equal(run(base(), D).results[0].naac.status, "validity_unknown");
});
test("NBA on one program does not apply to other programs of the college", () => {
  const D = mini(); D.addCollege("A"); D.addBranch("A-1", "A"); D.addBranch("A-2", "A", "Civil Engineering");
  ["A-1", "A-2"].forEach(c => D.addCut("historical_cutoffs", c, "2025-26", "IV", "GOPENS", 80));
  D.accreditation.push({ accreditation_id: "AC2", college_code: "A", choice_code: "A-1", body: "NBA", scope: "program", status: "accredited", grade: "", valid_from: "2022-01-01", valid_to: "2030-01-01", source_doc_id: "D-CUT", validation_status: "validated" });
  const r = run(Object.assign(base(), { branches: ["Computer Engineering", "Civil Engineering"] }), D);
  assert.equal(r.results.find(x => x.choiceCode === "A-1").nba.status, "valid"); assert.equal(r.results.find(x => x.choiceCode === "A-2").nba, null);
});
test("rows that are not validated are ignored", () => {
  const D = simple(80); D.historical_cutoffs.forEach(r => r.validation_status = "pending");
  const r = run(base(), D); assert.equal(r.results.length, 0); assert.equal(r.insufficientData.length, 1);
});

/* ---- output shape / honesty ---- */
test("never returns more than 20, and says so when fewer than 5 match", () => {
  const r = R.recommend(Object.assign(base(), { percentile: 99.9, branches: ["Computer Science and Engineering"] }), SYN, AS_OF);
  assert.ok(r.results.length <= 20);
  const small = run(base(), simple(80)); assert.equal(small.results.length, 1); assert.ok(small.meta.warnings.some(w => /fewer than five/.test(w)));
});
test("ranks are 1..n, scores non-increasing, each result has sources and an explanation", () => {
  const r = R.recommend(Object.assign(base(), { percentile: 97, districts: ["Pune", "Nagpur"] }), SYN, AS_OF);
  assert.ok(r.results.length >= 5, "expected at least 5 results on synthetic data");
  r.results.forEach((x, i) => { assert.equal(x.rank, i + 1); if (i) assert.ok(r.results[i - 1].score >= x.score); assert.ok(x.explanation.length >= 5); assert.ok(x.sources.length > 0);
    assert.equal(x.historicalCutoffs.length, 3); assert.ok(["Historically more suitable", "Possible but uncertain", "Ambitious choice", "Limited evidence"].includes(x.suitability)); });
});
test("zero matches gives a clear message, not 'Only 0'", () => {
  const r = run(Object.assign(base(), { percentile: 50 }), simple(80));
  assert.equal(r.results.length, 0); assert.ok(r.meta.warnings.some(w => /No choices matched/.test(w)));
});
test("fit score: more margin never lowers fit, and is capped at 100", () => {
  const fit = pct => run(Object.assign(base(), { percentile: pct }), simple(80)).results[0].componentScores.fit;
  assert.ok(fit(78) < fit(80) && fit(80) < fit(82) && fit(82) <= fit(90)); assert.equal(fit(99), 100);
});
test("percentile gaps near the top count for more than gaps lower down", () => {
  const lab = (pct, cut) => { const r = run(Object.assign(base(), { percentile: pct }), simple(cut)).results; return r.length ? r[0].suitability : "excluded"; };
  assert.equal(lab(98.5, 99), "Ambitious choice");            // raw gap only -0.5, but at the 99th percentile that is large
  assert.equal(lab(98.9, 99), "Possible but uncertain");
  assert.equal(lab(99.4, 99), "Historically more suitable");
  assert.equal(lab(99.9, 99.5), "Historically more suitable");
  assert.equal(lab(79.5, 80), "Possible but uncertain");       // same raw gap mid-range is minor
  assert.equal(lab(47, 50), "Possible but uncertain");         // lower down, a 3-point gap counts for less
  assert.equal(lab(90, 99), "excluded");
});
test("scaled margin is reported alongside the raw margin", () => {
  const x = run(Object.assign(base(), { percentile: 98.5 }), simple(99)).results[0];
  assert.equal(x.marginVsExpected, -0.5); assert.equal(x.scaledMargin, -5);
  assert.ok(x.explanation.some(l => /small percentile gap means many ranks/.test(l)));
});
test("earlier current rounds count for less than Round IV when averaging", () => {
  const exp = round => { const D = simple(80); D.addCut("current_cutoffs", "A-1", "2026-27", round, "GOPENS", 90); return run(base(), D).results[0].expectedCutoff; };
  assert.equal(exp("IV"), 84); assert.equal(exp("III"), 83.68); assert.equal(exp("I"), 82.5);
  assert.ok(exp("IV") > exp("III") && exp("III") > exp("II") && exp("II") > exp("I"));
});
test("a college with less evidence is slightly penalised; full-data colleges are not", () => {
  const D = simple(80);
  const withPenalty = run(base(), D).results[0], without = run(base(), D, { coverage: { floor: 1 } }).results[0];
  assert.ok(withPenalty.score < without.score); assert.ok(withPenalty.dataCompleteness < 1);
  const full = twoColleges(); full.accreditation.push({ accreditation_id: "AA", college_code: "A", choice_code: "", body: "NAAC", scope: "institution", status: "accredited", grade: "A", valid_to: "2030-01-01", source_doc_id: "D-CUT", validation_status: "validated" });
  full.quality_indicators.push({ indicator_id: "q1", college_code: "A", indicator: "teaching", score_0_10: "8", is_estimate: "TRUE", method_version: "t", computed_date: "2026-01-01", source_doc_id: "D-CUT", validation_status: "validated" },
    { indicator_id: "q2", college_code: "A", indicator: "infrastructure", score_0_10: "8", is_estimate: "TRUE", method_version: "t", computed_date: "2026-01-01", source_doc_id: "D-CUT", validation_status: "validated" });
  const a = run(Object.assign(base(), { maxAnnualFeeINR: 250000 }), full).results.find(x => x.choiceCode === "A-1");
  assert.equal(a.dataCompleteness, 1);
});
test("synthetic data is flagged so the UI can warn", () => { assert.equal(R.recommend(base(), SYN, AS_OF).meta.usingSyntheticData, true); });
test("engine is deterministic", () => {
  const a = JSON.stringify(R.recommend(base(), SYN, AS_OF)), b = JSON.stringify(R.recommend(base(), SYN, AS_OF)); assert.equal(a, b);
});
test("extra eligibility claims produce an honest 'not applied' warning", () => {
  const r = R.recommend(Object.assign(base(), { extraEligibility: ["tfws"] }), SYN, AS_OF); assert.ok(r.meta.warnings.some(w => /not applied/.test(w)));
});
test("engine does not modify the data passed in", () => {
  const before = JSON.stringify(SYN); R.recommend(base(), SYN, AS_OF); assert.equal(JSON.stringify(SYN), before);
});
