// Stage 10c-3a tests: loader + engine on the REAL packaged data. The data folder is built by tests/test_stage10c3a.py and passed in REAL_DATA_DIR.
// Run by hand:  python -m ingestion.package_real /tmp/realdata && REAL_DATA_DIR=/tmp/realdata node --test tests/real_data.test.js
const test = require("node:test"), assert = require("node:assert/strict");
const fs = require("fs"), path = require("path");
const DIR = process.env.REAL_DATA_DIR;
const R = require("../frontend/engine.js"), L = require("../frontend/dataloader.js");
const PUNE = "Savitribai Phule Pune University", MUM = "Mumbai University";
const fetchFn = async (url) => {
  const p = path.join(DIR, url.replace(/^data\//, ""));
  if (!fs.existsSync(p)) return { ok: false, status: 404, arrayBuffer: async () => new ArrayBuffer(0) };
  const b = fs.readFileSync(p); return { ok: true, status: 200, arrayBuffer: async () => b.buffer.slice(b.byteOffset, b.byteOffset + b.length) };
};
const run = (o) => L.recommend(Object.assign({ percentile: 92, admissionYear: "auto", candidateType: "Maharashtra State candidate", category: "OPEN", gender: "Male", extraEligibility: [],
  branches: ["Computer Engineering"], districts: ["ANY"], maxAnnualFeeINR: 1000000, feeBasis: "total", priorities: ["admission_chance"], homeUniversity: PUNE }, o || {}),
  { baseUrl: "data/", fetchFn, Recommender: R, engineOptions: { asOfDate: "2026-11-10", maxResults: 200 } });
const skip = !DIR ? "REAL_DATA_DIR not set" : false;

test("real data: basic answer, years and no synthetic flag", { skip }, async () => {
  const r = await run();
  assert.equal(r.ok, true); assert.ok(r.results.length > 20);
  assert.equal(r.meta.usingSyntheticData, false); assert.equal(r.meta.currentAdmissionYear, "2026-27");
  assert.deepEqual(r.meta.historicalYears, ["2025-26", "2024-25", "2023-24"]);
  assert.match(r.meta.dataVersion, /^REAL-2026-27-RIV-/);
});
test("real data: male OPEN student uses only General OPEN/category seats, no ladies/special seats", { skip }, async () => {
  const r = await run(); const st = r.meta.seatTypesUsed;
  assert.ok(st.includes("GOPENS") && st.includes("GOPENH") && st.includes("GOPENO"));
  st.forEach(c => assert.match(c, /^G(OPEN)[HOS]$/));
});
test("real data: female student also gets ladies seats; OBC adds OBC seats", { skip }, async () => {
  const st = (await run({ gender: "Female", category: "OBC" })).meta.seatTypesUsed;
  assert.ok(st.includes("LOPENS") && st.includes("GOBCS") && st.includes("LOBCS"));
});
test("real data: special seats only with a claim; undefined variants never used", { skip }, async () => {
  const plain = (await run()).meta.seatTypesUsed;
  assert.ok(!plain.some(c => /TFWS|EWS|PWD|DEF|ORPHAN/.test(c)));
  const withClaims = (await run({ extraEligibility: ["tfws", "ews", "defence", "pwd", "orphan"] })).meta.seatTypesUsed;
  assert.ok(withClaims.includes("TFWS") && withClaims.includes("EWS"));
  assert.ok(!withClaims.some(c => /^(DEFR|PWDR|ORPHANI|ORPHANN|ORPHAN2)/.test(c)), "variant seats must not be matched");
});
test("real data: home university changes the Home University / Other Than Home University seats used", { skip }, async () => {
  const a = await run({ homeUniversity: PUNE }), b = await run({ homeUniversity: MUM });
  const names = r => r.results.map(x => x.choiceCode + "|" + (x.currentCutoff && x.currentCutoff.value)).join(";");
  assert.notEqual(names(a), names(b));
  assert.ok(!a.meta.warnings.some(w => /did not choose a home university/.test(w)));
});
test("real data: no home university chosen -> warning and the harder cutoff (never easier than with a home university)", { skip }, async () => {
  const none = await run({ homeUniversity: undefined }), pune = await run({ homeUniversity: PUNE });
  assert.ok(none.meta.warnings.some(w => /did not choose a home university/.test(w)));
  const mp = new Map(pune.results.map(x => [x.choiceCode, x]));
  let compared = 0;
  for (const x of none.results) { const y = mp.get(x.choiceCode); if (y && x.currentCutoff && y.currentCutoff && x.currentCutoff.round === y.currentCutoff.round) { compared++;   // Stage 13d: only the same CAP round is comparable (with a home university the engine may have to fall back to an earlier round)
    assert.ok(x.currentCutoff.value >= y.currentCutoff.value - 1e-9, x.choiceCode); } }
  assert.ok(compared > 10);
});
test("real data: all four rounds of the current year are available per result", { skip }, async () => {
  const r = await run(); const x = r.results.find(y => y.currentRounds && y.currentRounds.IV && y.currentRounds.I);
  assert.ok(x, "expected a result with rounds I and IV"); assert.deepEqual(Object.keys(x.currentRounds), ["I", "II", "III", "IV"]);
  r.results.forEach(y => Object.values(y.currentRounds).forEach(v => { if (v) assert.ok(v.value > 0 && v.value <= 100); }));
});
test("real data: only the needed cutoff files are downloaded and all verify", { skip }, async () => {
  const r = await run(); const m = JSON.parse(fs.readFileSync(path.join(DIR, "manifest.json"), "utf8"));
  assert.ok(r.meta.dataFiles.length < Object.keys(m.cutoffs).length + 1); assert.ok(r.meta.dataBytesDownloaded < 6e6, "bytes " + r.meta.dataBytesDownloaded);
});
test("real data: missing data is reported, not invented", { skip }, async () => {
  const r = await run(); const x = r.results[0];
  assert.ok(x.vacancy.value === null || Number.isInteger(x.vacancy.value)); assert.ok(x.fee.value === null || Number.isInteger(x.fee.value)); assert.equal(x.placement, null);
});
test("real data: a district choice filters to that district (official district data)", { skip }, async () => {
  const m = JSON.parse(fs.readFileSync(path.join(DIR, "manifest.json"), "utf8")); const any = await run({ districts: ["ANY"] });
  const sat = await run({ districts: ["Satara"], branches: ["Computer Science and Engineering"] });
  assert.ok(!sat.meta.warnings.some(w => /District data is not available yet/.test(w)));
  assert.ok(sat.results.length > 0); sat.results.forEach(x => assert.equal(x.district, "Satara"));
  assert.ok(any.results.length > 0);
});

test("real data (Stage 13): default ranking differs by percentile and puts strong colleges first for a high percentile", { skip }, async () => {
  const hi = await run({ percentile: 99.5, priorities: ["balanced"] }), mid = await run({ percentile: 92, priorities: ["balanced"] });
  const a = hi.results.slice(0, 20).map(r => r.choiceCode), b = mid.results.slice(0, 20).map(r => r.choiceCode);
  assert.ok(a.filter(c => b.includes(c)).length <= 5, "top 20 for 99.5 and 92 must be (almost) different");
  assert.ok(hi.results.slice(0, 5).every(r => r.expectedCutoff >= 90), "top 5 at 99.5 are colleges with cutoffs of 90 or more");
  const ac = await run({ percentile: 99.5, priorities: ["admission_chance"] });
  assert.equal(ac.results[0].componentScores.fit, 100);
});

test("real data (Stage 13d): the cutoff used for ranking is the same one shown for that round, and respects the student's home university", { skip }, async () => {
  const r = await run({ percentile: 92, priorities: ["balanced"] }); let n = 0;
  r.results.forEach(x => {
    if (!x.currentCutoff) return; n++;
    const shown = x.currentRounds[x.currentCutoff.round];
    assert.ok(shown && Math.abs(shown.value - x.currentCutoff.value) < 1e-9, x.choiceCode + ": used and shown figures differ");
    assert.equal(x.currentCutoff.homeUniversityUnclear, false);
  });
  assert.ok(n > 100);
  const none = await run({ percentile: 92, priorities: ["balanced"], homeUniversity: "" });
  assert.ok(none.results.some(x => x.currentCutoff && x.currentCutoff.homeUniversityUnclear), "without a home university the harder-of-two rule still applies");
});

test("real data (Stage 13d): NAAC graded colleges get the small accreditation bonus; colleges with no record are neutral", { skip }, async () => {
  const r = await run({ percentile: 92, priorities: ["balanced"] });
  const graded = r.results.filter(x => x.naac && x.naac.grade), none = r.results.filter(x => !x.naac && !x.nba);
  if (graded.length === 0) {   // the test harness packages tables without accreditation: then nothing may get a bonus
    r.results.forEach(x => { assert.equal(x.componentScores.accreditation, null); assert.ok(!x.explanation.some(l => /^Ranking: accreditation/.test(l))); }); return;
  }
  assert.ok(graded.length > 20 && none.length > 20);
  graded.forEach(x => { assert.notEqual(x.componentScores.accreditation, null); assert.ok(x.explanation.some(l => /^Ranking: accreditation gave this choice a small bonus/.test(l))); });
  none.forEach(x => { assert.equal(x.componentScores.accreditation, null); assert.ok(!x.explanation.some(l => /^Ranking: accreditation/.test(l))); });
  const off = await L.recommend({ percentile: 92, admissionYear: "auto", candidateType: "Maharashtra State candidate", category: "OPEN", gender: "Male", extraEligibility: [], branches: ["Computer Engineering"], districts: ["ANY"], maxAnnualFeeINR: 1000000, feeBasis: "total", priorities: ["balanced"], homeUniversity: PUNE }, { baseUrl: "data/", fetchFn, Recommender: R, engineOptions: { asOfDate: "2026-11-10", maxResults: 200, accreditationBonusFactor: 0 } });
  const a = r.results.slice(0, 20).map(x => x.choiceCode), b = off.results.slice(0, 20).map(x => x.choiceCode);
  assert.ok(a.filter(c => b.includes(c)).length >= 14, "the bonus is small: the top 20 stays mostly the same");
});
