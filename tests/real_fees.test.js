// Stage 12a-3 tests: FRA fees on the REAL packaged data, through the browser loader + engine. Built by tests/test_stage12a3.py.
// Env: REAL_DATA_DIR (packaged folder), FEES_CSV (tables/fees.csv the folder was built from).
const test = require("node:test"), assert = require("node:assert/strict");
const fs = require("fs"), path = require("path");
const DIR = process.env.REAL_DATA_DIR, CSV = process.env.FEES_CSV;
const R = require("../frontend/engine.js"), L = require("../frontend/dataloader.js");
const skip = !DIR || !CSV ? "REAL_DATA_DIR / FEES_CSV not set" : false;
const fetchFn = async (url) => {
  const p = path.join(DIR, url.replace(/^data\//, ""));
  if (!fs.existsSync(p)) return { ok: false, status: 404, arrayBuffer: async () => new ArrayBuffer(0) };
  const b = fs.readFileSync(p); return { ok: true, status: 200, arrayBuffer: async () => b.buffer.slice(b.byteOffset, b.byteOffset + b.length) };
};
const run = (o) => L.recommend(Object.assign({ percentile: 92, admissionYear: "auto", candidateType: "Maharashtra State candidate", category: "OPEN", gender: "Male", extraEligibility: [],
  branches: ["Computer Engineering"], districts: ["ANY"], maxAnnualFeeINR: 1000000, feeBasis: "total", priorities: ["admission_chance"], homeUniversity: "Savitribai Phule Pune University" }, o || {}),
  { baseUrl: "data/", fetchFn, Recommender: R, engineOptions: { asOfDate: "2026-11-10", maxResults: 300 } });
function table() {
  const lines = fs.readFileSync(CSV, "utf8").split(/\r?\n/).filter(Boolean); const h = lines[0].split(","); const out = {};
  lines.slice(1).forEach(l => { const c = l.match(/("([^"]*)"|[^,]*)(,|$)/g) && l.split(/,(?=(?:[^"]*"[^"]*")*[^"]*$)/); out[c[h.indexOf("college_code")] + "|" + c[h.indexOf("fee_type")]] = +c[h.indexOf("annual_fee_inr")]; });
  return out;
}
for (const basis of ["total", "tuition"]) {
  test("fees (" + basis + "): every shown fee equals the FRA table, for the current year", { skip }, async () => {
    const r = await run({ feeBasis: basis }); assert.equal(r.ok, true); const t = table(); let n = 0;
    r.results.forEach(x => { if (x.fee.status === "ok") { n++; assert.equal(x.fee.value, t[x.collegeCode + "|" + basis]); assert.equal(x.fee.type, basis); assert.equal(x.fee.academicYear, "2026-27"); } });
    assert.ok(n > 20, "fee shown for " + n + " results");
  });
}
test("fees: the explanation says what the total contains", { skip }, async () => {
  const r = await run({ feeBasis: "total" }); const x = r.results.find(y => y.fee.status === "ok");
  assert.ok(x.explanation.some(t => /tuition \+ development fee approved by the Fees Regulating Authority/.test(t)));
  assert.ok(x.explanation.some(t => /^Fee: Rs \d+ per year \(total, 2026-27\)/.test(t)));
});
test("fees: a budget below the fee excludes or flags the college (no silent pass)", { skip }, async () => {
  const hi = await run({ maxAnnualFeeINR: 1000000 }); const lo = await run({ maxAnnualFeeINR: 60000 });
  assert.ok(lo.results.length < hi.results.length); lo.results.forEach(x => { if (x.fee.status === "ok") assert.ok(x.fee.value <= 60000); });
});
