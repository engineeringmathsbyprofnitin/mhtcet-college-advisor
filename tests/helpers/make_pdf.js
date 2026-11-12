// Builds PDFs from engine results with the browser's own exporter (frontend/pdfexport.js). Used by tests/test_stage10c3e.py.
// env: REAL_DATA_DIR (optional, real package) and OUT_DIR. Writes real.pdf (and synthetic.pdf from frontend/data when REAL_DATA_DIR is absent).
const fs = require("fs"), path = require("path");
const FE = path.join(__dirname, "..", "..", "frontend");
const R = require(path.join(FE, "engine.js")), L = require(path.join(FE, "dataloader.js")), P = require(path.join(FE, "pdfexport.js"));
const mk = (dir) => async (u) => { const p = path.join(dir, u.replace(/^data(-real)?\//, "")); if (!fs.existsSync(p)) return { ok: false, status: 404, arrayBuffer: async () => new ArrayBuffer(0) };
  const b = fs.readFileSync(p); return { ok: true, status: 200, arrayBuffer: async () => b.buffer.slice(b.byteOffset, b.byteOffset + b.length) }; };
(async () => {
  const real = process.env.REAL_DATA_DIR, dir = real || path.join(FE, "data");
  const input = real ? { percentile: 92, admissionYear: "auto", candidateType: "Maharashtra State candidate", category: "OPEN", gender: "Male", extraEligibility: [], branches: ["Computer Engineering"], districts: ["ANY"],
    maxAnnualFeeINR: 1000000, feeBasis: "total", priorities: ["admission_chance"], homeUniversity: "Savitribai Phule Pune University" } : null;
  if (!input) { console.error("synthetic input not provided"); process.exit(2); }
  const res = await L.recommend(input, { baseUrl: "data/", fetchFn: mk(dir), Recommender: R, engineOptions: { asOfDate: "2026-11-10", maxResults: 20 } });
  fs.writeFileSync(path.join(process.env.OUT_DIR, "real.pdf"), Buffer.from(P.buildPdf(res)));
  fs.writeFileSync(path.join(process.env.OUT_DIR, "real.json"), JSON.stringify({ n: res.results.length, first: res.results[0] && res.results[0].collegeName, version: res.meta.dataVersion }));
})().catch(e => { console.error(e); process.exit(1); });
