// Engine check with official districts in the data: choosing Satara returns only Satara colleges. env: DISTRICT_DATA_DIR
const fs = require("fs"), path = require("path"); const FE = path.join(__dirname, "..", "..", "frontend"), DIR = process.env.DISTRICT_DATA_DIR;
const R = require(path.join(FE, "engine.js")), L = require(path.join(FE, "dataloader.js"));
const fetchFn = async (u) => { const p = path.join(DIR, u.replace(/^data(-real)?\//, "")); if (!fs.existsSync(p)) return { ok: false, status: 404, arrayBuffer: async () => new ArrayBuffer(0) };
  const b = fs.readFileSync(p); return { ok: true, status: 200, arrayBuffer: async () => b.buffer.slice(b.byteOffset, b.byteOffset + b.length) }; };
(async () => {
  const run = d => L.recommend({ percentile: 60, admissionYear: "auto", candidateType: "Maharashtra State candidate", category: "OPEN", gender: "Male", extraEligibility: [], branches: ["Computer Science and Engineering"],
    districts: d, maxAnnualFeeINR: 1000000, feeBasis: "total", priorities: ["admission_chance"], homeUniversity: "Mumbai University" }, { baseUrl: "data/", fetchFn, Recommender: R, engineOptions: { asOfDate: "2026-11-10", maxResults: 100 } });
  const sat = await run(["Satara"]), any = await run(["ANY"]);
  console.log(JSON.stringify({ satara: sat.results.map(r => r.district), anyCount: any.results.length, anyDistricts: Array.from(new Set(any.results.map(r => r.district))).sort(), warnings: sat.meta.warnings }));
})().catch(e => { console.error(e); process.exit(1); });
