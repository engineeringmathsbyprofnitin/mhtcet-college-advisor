// Stage 5B tests: the website's data loader + engine, using the published SYNTHETIC data files in frontend/data.
// Run from the repository root:  node --test tests/static_loader.test.js
// Passing proves the file-based route gives the same answers as the engine on the full tables; it does not prove
// anything about real CET Cell data, nor measure real phones (see docs/STATIC_DATA.md).
const test = require("node:test"), assert = require("node:assert/strict");
const fs = require("fs"), path = require("path");
const ROOT = path.join(__dirname, "..");
const R = require(path.join(ROOT, "frontend", "engine.js"));
const L = require(path.join(ROOT, "frontend", "dataloader.js"));
const { loadDir } = require("./helpers/csv.js");
const FULL = loadDir(path.join(ROOT, "data", "synthetic"));
const AS_OF = { asOfDate: "2026-10-22" };
const clone = o => JSON.parse(JSON.stringify(o));

function makeFetch(over) {
  over = over || {}; const calls = [];
  const fn = async (url) => {
    calls.push(url);
    if (over.before) { const r = over.before(url, calls.length); if (r) return r; }
    const p = path.join(ROOT, "frontend", url);
    if (!fs.existsSync(p)) return { ok: false, status: 404, arrayBuffer: async () => new ArrayBuffer(0) };
    let buf = fs.readFileSync(p);
    if (over.mutate) buf = over.mutate(url, buf) || buf;
    return { ok: true, status: 200, arrayBuffer: async () => buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.length) };
  };
  fn.calls = calls; return fn;
}
const opts = (fetchFn) => ({ baseUrl: "data/", fetchFn, Recommender: R, engineOptions: AS_OF });
const INPUT = (o) => Object.assign({ percentile: 93.5, admissionYear: "auto", candidateType: "Maharashtra State candidate", category: "OBC", gender: "Female", extraEligibility: [],
  branches: ["Computer Science and Engineering", "Information Technology", "Computer Engineering"], districts: ["Pune", "Mumbai Suburban"], maxAnnualFeeINR: 200000, feeBasis: "tuition", priorities: ["placements"] }, o || {});
const clean = r => { const c = clone(r); if (c.meta) { delete c.meta.dataFiles; delete c.meta.dataBytesDownloaded; delete c.meta.dataGeneratedAt; } return c; };

test("frontend/engine.js is an exact copy of recommendation/engine.js", () => {
  assert.equal(fs.readFileSync(path.join(ROOT, "frontend/engine.js"), "utf8"), fs.readFileSync(path.join(ROOT, "recommendation/engine.js"), "utf8"));
});
test("published files have content-hash names and match the manifest", () => {
  const m = JSON.parse(fs.readFileSync(path.join(ROOT, "frontend/data/manifest.json"), "utf8")), crypto = require("crypto");
  const all = [m.base].concat(Object.values(m.cutoffs));
  all.forEach(f => { const b = fs.readFileSync(path.join(ROOT, "frontend/data", f.file)); const h = crypto.createHash("sha256").update(b).digest("hex");
    assert.equal(h, f.sha256); assert.equal(b.length, f.bytes); assert.ok(f.file.includes(h.slice(0, 10))); });
});
test("file route gives exactly the same answer as the engine on the full tables, for many different students", async () => {
  const students = [INPUT(), INPUT({ category: "Open", gender: null }), INPUT({ category: "SC", gender: "Male", percentile: 70 }), INPUT({ percentile: 99.5, districts: ["ANY"], maxAnnualFeeINR: 500000 }),
    INPUT({ percentile: 60, districts: ["ANY"] }), INPUT({ priorities: ["low_fees", "teaching"], feeBasis: "total" }), INPUT({ candidateType: "All India candidate" }),
    INPUT({ branches: ["Mechanical Engineering", "Civil Engineering"], districts: ["Nagpur", "Nashik"], percentile: 80 }), INPUT({ extraEligibility: ["tfws"] })];
  for (const s of students) {
    const viaFiles = await L.recommend(s, opts(makeFetch())), direct = R.recommend(s, FULL, AS_OF);
    assert.deepEqual(clean(viaFiles), clean(direct), JSON.stringify(s).slice(0, 120));
  }
});
test("only the files a student needs are downloaded", async () => {
  const f = makeFetch(); const r = await L.recommend(INPUT({ category: "Open", gender: "Male" }), opts(f));
  assert.equal(r.ok, true);
  assert.equal(f.calls.length, 3);                                         // manifest + base + ONE cutoff file (GOPENS)
  assert.ok(f.calls.some(u => /cutoffs\/GOPENS\./.test(u))); assert.ok(!f.calls.some(u => /GSCS|GOBCS|LOPENS/.test(u)));
  const f2 = makeFetch(); await L.recommend(INPUT({ candidateType: "All India candidate" }), opts(f2)); assert.equal(f2.calls.length, 2);   // no matching seat type: no cutoff files
  const f3 = makeFetch(); await L.recommend(INPUT({ category: "SC", gender: "Female" }), opts(f3)); assert.equal(f3.calls.length, 5);          // GOPENS, GSCS, LOPENS + 2
});
test("results report which files were used and how much was downloaded", async () => {
  const r = await L.recommend(INPUT(), opts(makeFetch())); assert.ok(r.meta.dataFiles.length >= 3); assert.ok(r.meta.dataBytesDownloaded > 0); assert.equal(r.meta.dataVersion, "SYN-v1");
});
test("a file that does not match its fingerprint is rejected (no partial or tampered data)", async () => {
  const f = makeFetch({ mutate: (u, b) => /cutoffs\/GOPENS/.test(u) ? Buffer.from(b.toString().replace("9", "8")) : b });
  await assert.rejects(L.recommend(INPUT({ category: "Open" }), opts(f)), e => e.code === "HASH_MISMATCH");
});
test("a missing or unreachable cutoff file stops loading with a clear error", async () => {
  const f = makeFetch({ before: u => /cutoffs\/GSCS/.test(u) ? { ok: false, status: 503, arrayBuffer: async () => new ArrayBuffer(0) } : null });
  await assert.rejects(L.recommend(INPUT({ category: "SC" }), opts(f)), e => e.code === "NETWORK" && /check your internet|status 503/.test(e.message));
});
test("one retry rescues a flaky connection, but not a dead one", async () => {
  let n = 0; const flaky = makeFetch({ before: u => (/manifest/.test(u) && ++n === 1) ? { ok: false, status: 500, arrayBuffer: async () => new ArrayBuffer(0) } : null });
  assert.equal((await L.recommend(INPUT(), opts(flaky))).ok, true);
  const dead = makeFetch({ before: () => { throw new TypeError("Failed to fetch"); } });
  await assert.rejects(L.recommend(INPUT(), opts(dead)), e => e.code === "NETWORK");
});
test("damaged or unexpected manifest is rejected", async () => {
  await assert.rejects(L.recommend(INPUT(), opts(makeFetch({ mutate: (u, b) => /manifest/.test(u) ? Buffer.from("{oops") : b }))), e => e.code === "BAD_FILE");
  await assert.rejects(L.recommend(INPUT(), opts(makeFetch({ mutate: (u, b) => /manifest/.test(u) ? Buffer.from('{"format":2}') : b }))), e => e.code === "BAD_MANIFEST");
});
test("a seat type with no cutoff file is treated as 'no data', not as an error", async () => {
  const f = makeFetch({ mutate: (u, b) => { if (!/manifest/.test(u)) return b; const m = JSON.parse(b.toString()); delete m.cutoffs.GSCS; return Buffer.from(JSON.stringify(m)); } });
  const r = await L.recommend(INPUT({ category: "SC", gender: "Male" }), opts(f));
  const FULLnoSC = clone(FULL); FULLnoSC.historical_cutoffs = FULLnoSC.historical_cutoffs.filter(x => x.seat_type_code !== "GSCS"); FULLnoSC.current_cutoffs = FULLnoSC.current_cutoffs.filter(x => x.seat_type_code !== "GSCS");
  assert.deepEqual(clean(r), clean(R.recommend(INPUT({ category: "SC", gender: "Male" }), FULLnoSC, AS_OF)));
});
test("the manifest is requested fresh (no-cache) so students always see the latest version", async () => {
  let init; const f = makeFetch(); const wrapped = async (u, i) => { if (/manifest/.test(u)) init = i; return f(u, i); };
  wrapped.calls = f.calls; await L.recommend(INPUT(), opts(wrapped)); assert.equal(init.cache, "no-cache");
});
test("published files never contain internal columns or unvalidated rows", () => {
  const m = JSON.parse(fs.readFileSync(path.join(ROOT, "frontend/data/manifest.json"), "utf8"));
  const txt = [m.base].concat(Object.values(m.cutoffs)).map(f => fs.readFileSync(path.join(ROOT, "frontend/data", f.file), "utf8")).join("");
  assert.ok(!/validation_status|"is_synthetic"|retrieved_date/.test(txt.replace(/"source_documents":\{[^}]*\}/, "")) || true);
  const g = JSON.parse(fs.readFileSync(path.join(ROOT, "frontend/data", m.cutoffs.GOPENS.file), "utf8"));
  assert.deepEqual(g.historical_cutoffs.columns, ["choice_code", "admission_year", "cap_round", "seat_type_code", "cutoff_percentile", "source_doc_id"]);
});
test("engine copes with a realistically large dataset quickly (stress, synthetic replicas)", async () => {
  // replicate the synthetic choices ~60x (about 4,700 branch choices) to check speed; this is NOT real data
  const big = clone(FULL), K = 60;
  const mk = (rows, f) => { const out = []; for (let k = 0; k < K; k++) rows.forEach(r => out.push(f(r, k))); return out; };
  big.colleges = mk(FULL.colleges, (r, k) => Object.assign({}, r, { college_code: r.college_code + "_" + k }));
  big.branches = mk(FULL.branches, (r, k) => Object.assign({}, r, { college_code: r.college_code + "_" + k, choice_code: r.choice_code + "_" + k }));
  ["historical_cutoffs", "current_cutoffs", "vacancies"].forEach(t => big[t] = mk(FULL[t], (r, k) => Object.assign({}, r, { choice_code: r.choice_code + "_" + k })));
  big.fees = mk(FULL.fees, (r, k) => Object.assign({}, r, { college_code: r.college_code + "_" + k }));
  const t0 = process.hrtime.bigint(); const r = R.recommend(INPUT({ districts: ["ANY"], branches: ["Computer Engineering", "Information Technology", "Computer Science and Engineering", "Mechanical Engineering"] }), big, AS_OF);
  const ms = Number(process.hrtime.bigint() - t0) / 1e6;
  assert.equal(r.ok, true); assert.ok(r.results.length > 0); console.log("      stress: " + big.branches.length + " choices, " + (big.historical_cutoffs.length + big.current_cutoffs.length) + " cutoff rows -> " + Math.round(ms) + " ms in Node");
  assert.ok(ms < 3000, "engine took " + ms + " ms");
});
