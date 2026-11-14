// Stage 11d tests: the vacancy on the REAL packaged data, run through the browser loader + engine. Built by tests/test_stage11d.py.
// Env: REAL_DATA_DIR (packaged folder), VACANCY_CSV (tables/vacancy.csv the folder was built from).
const test = require("node:test"), assert = require("node:assert/strict");
const fs = require("fs"), path = require("path");
const DIR = process.env.REAL_DATA_DIR, CSV = process.env.VACANCY_CSV;
const R = require("../frontend/engine.js"), L = require("../frontend/dataloader.js");
const skip = !DIR || !CSV ? "REAL_DATA_DIR / VACANCY_CSV not set" : false;
const fetchFn = async (url) => {
  const p = path.join(DIR, url.replace(/^data\//, ""));
  if (!fs.existsSync(p)) return { ok: false, status: 404, arrayBuffer: async () => new ArrayBuffer(0) };
  const b = fs.readFileSync(p); return { ok: true, status: 200, arrayBuffer: async () => b.buffer.slice(b.byteOffset, b.byteOffset + b.length) };
};
const run = (o) => L.recommend(Object.assign({ percentile: 92, admissionYear: "auto", candidateType: "Maharashtra State candidate", category: "OPEN", gender: "Male", extraEligibility: [],
  branches: ["Computer Engineering"], districts: ["ANY"], maxAnnualFeeINR: 1000000, feeBasis: "total", priorities: ["admission_chance"], homeUniversity: "Savitribai Phule Pune University" }, o || {}),
  { baseUrl: "data/", fetchFn, Recommender: R, engineOptions: { asOfDate: "2026-11-10", maxResults: 200 } });
function table() {
  const lines = fs.readFileSync(CSV, "utf8").split(/\r?\n/).filter(Boolean); const head = lines[0].split(",");
  const out = {}; lines.slice(1).forEach(l => { const c = l.split(","); out[c[head.indexOf("choice_code")]] = +c[head.indexOf("vacant_cap_seats")]; }); return out;
}
test("vacancy: every shown figure equals the published vacancy table (Round IV, current year only)", { skip }, async () => {
  const r = await run(); assert.equal(r.ok, true); const t = table();
  assert.equal(r.meta.vacancyRoundUsed, "IV");
  assert.ok(!r.meta.warnings.some(w => /Vacancy data unavailable/.test(w)));
  let n = 0; r.results.forEach(x => { if (x.vacancy.value !== null) { n++; assert.equal(x.vacancy.value, t[x.choiceCode]); assert.equal(x.vacancy.round, "IV"); } });
  assert.ok(n > 20, "vacancy shown for " + n + " results");
});
test("vacancy: zero is a real printed zero, and the explanation uses the agreed wording", { skip }, async () => {
  const r = await run(); const z = r.results.find(x => x.vacancy.value === 0);
  const some = r.results.find(x => x.vacancy.value !== null);
  assert.ok(some.explanation.some(t => /^Seats open going into Round IV: \d+ seat\(s\), the total for the course/.test(t)));
  if (z) assert.ok(z.explanation.some(t => /Seats open going into Round IV: 0 seat\(s\)/.test(t)));
});
