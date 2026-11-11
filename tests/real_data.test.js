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
  for (const x of none.results) { const y = mp.get(x.choiceCode); if (y && x.currentCutoff && y.currentCutoff) { compared++; assert.ok(x.currentCutoff.value >= y.currentCutoff.value - 1e-9, x.choiceCode); } }
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
  assert.equal(x.vacancy.value, null); assert.equal(x.fee.value, null); assert.equal(x.placement, null);
});
test("real data: a district choice is accepted; it cannot be applied (no district data) so all districts are searched and a warning says so", { skip }, async () => {
  const r = await run({ districts: ["Pune"] }); assert.ok(r.results.length > 20);
  assert.ok(r.meta.warnings.some(w => /District data is not available yet/.test(w)));
  const any = await run({ districts: ["ANY"] }); assert.ok(!any.meta.warnings.some(w => /District data is not available yet/.test(w)));
});
