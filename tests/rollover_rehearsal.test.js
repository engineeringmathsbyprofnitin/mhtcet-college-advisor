// Stage 14d-2: rehearsal of the 1 January switch and of the first 2027-28 round, on PRETEND data built by tests/test_stage14d2.py.
// REHEARSAL_DIRS = JSON {"jan": folder, "jul": folder}; skipped without it (the Python test sets it).
const test = require("node:test"), assert = require("node:assert"), fs = require("fs"), path = require("path");
const DIRS = process.env.REHEARSAL_DIRS ? JSON.parse(process.env.REHEARSAL_DIRS) : null, skip = !DIRS && "REHEARSAL_DIRS not set";
const ROOT = path.join(__dirname, ".."), R = require(path.join(ROOT, "frontend", "engine.js")), L = require(path.join(ROOT, "frontend", "dataloader.js"));
const app = fs.readFileSync(path.join(ROOT, "frontend", "app.js"), "utf8");
const fn = (name) => new Function(app.match(new RegExp("  function " + name + "\\([\\s\\S]*?\\n  \\}\\n"))[0] + "; return " + name + ";")();
const phaseText = fn("phaseText"), dataStatusText = fn("dataStatusText");
const fetchFor = (dir) => async (url) => { const p = path.join(dir, url.replace(/^data\//, "")); if (!fs.existsSync(p)) return { ok: false, status: 404, arrayBuffer: async () => new ArrayBuffer(0) }; const b = fs.readFileSync(p); return { ok: true, status: 200, arrayBuffer: async () => b.buffer.slice(b.byteOffset, b.byteOffset + b.length) }; };
const run = (dir, o) => L.recommend(Object.assign({ percentile: 90, admissionYear: "auto", candidateType: "Maharashtra State candidate", category: "OPEN", gender: "Male", extraEligibility: [], branches: ["Computer Engineering"], districts: ["ANY"], maxAnnualFeeINR: 1000000, feeBasis: "total", priorities: ["balanced"], homeUniversity: "Savitribai Phule Pune University" }, o || {}), { baseUrl: "data/", fetchFn: fetchFor(dir), Recommender: R, engineOptions: { asOfDate: "2027-07-20", maxResults: 300 } });
const manifest = (dir) => JSON.parse(fs.readFileSync(path.join(dir, "manifest.json"), "utf8"));
const base = (dir) => JSON.parse(fs.readFileSync(path.join(dir, manifest(dir).base.file), "utf8"));
const summary = (dir) => { const t = base(dir).data_version, i = t.columns.indexOf("row_count_summary"); return { row_count_summary: t.rows[0][i] }; };

test("15 January 2027: admission year 2027-28, cutoffs still 2026-27 (all four rounds), no 2026-27 vacancy, fees labelled 2026-27", { skip }, async () => {
  const dir = DIRS.jan, r = await run(dir);
  assert.ok(r.results.length > 100); assert.equal(r.meta.currentAdmissionYear, "2026-27"); assert.deepEqual(r.meta.historicalYears, ["2025-26", "2024-25", "2023-24"]);
  assert.match(summary(dir).row_count_summary, /admission=2027-28$/);
  assert.match(phaseText(summary(dir), "2026-27"), /^Admission year 2027-28: its cutoff lists are published only after the CAP Round I allotment[\s\S]*cutoffs of 2026-27 \(CAP rounds I, II, III, IV\)/);
  let roundIV = 0;
  r.results.forEach(x => {
    if (x.currentCutoff) { assert.equal(x.currentCutoff.year, "2026-27"); assert.ok(["I", "II", "III", "IV"].includes(x.currentCutoff.round)); if (x.currentCutoff.round === "IV") roundIV++; }   // a few choices have no Round IV row for this student: the engine falls back to an earlier 2026-27 round
    assert.equal(x.vacancy.value, null, x.choiceCode + ": last year's vacancy shown for the new year");
    if (x.fee.value !== null) assert.equal(x.fee.academicYear, "2026-27", x.choiceCode + ": fee year");
  });
  assert.ok(roundIV > r.results.length / 2, "most choices use the Round IV figure");
  assert.ok(r.results.some(x => x.fee.value !== null), "fees are still shown, labelled with their own year");
});

test("20 July 2027: Round I of 2027-28 published: current year 2027-28 (Round I only), history shifts, still no vacancy, fees still labelled 2026-27", { skip }, async () => {
  const dir = DIRS.jul, r = await run(dir);
  assert.ok(r.results.length > 100); assert.equal(r.meta.currentAdmissionYear, "2027-28"); assert.deepEqual(r.meta.historicalYears, ["2026-27", "2025-26", "2024-25"]);
  assert.match(summary(dir).row_count_summary, /^rounds=I;next=II;phase=confirmed;admission=2027-28$/);
  assert.match(phaseText(summary(dir), "2027-28"), /Round II is expected next and is not published yet/);
  let withCur = 0;
  r.results.forEach(x => {
    if (x.currentCutoff) { withCur++; assert.equal(x.currentCutoff.year, "2027-28"); assert.equal(x.currentCutoff.round, "I"); assert.deepEqual(Object.keys(x.currentRounds).filter(k => x.currentRounds[k]), ["I"]); }
    assert.equal(x.vacancy.value, null);
    if (x.fee.value !== null) assert.notEqual(x.fee.academicYear, "2027-28");
    const years = x.historicalCutoffs.map(h => h.year); assert.deepEqual(years, ["2026-27", "2025-26", "2024-25"]);
  });
  assert.ok(withCur > 100);
  const prev = r.results.find(x => x.historicalCutoffs[0].value !== null); assert.equal(prev.historicalCutoffs[0].round, "IV");     // last year's LAST round is the first history year
});

test("the data line on the page for the rehearsal data", { skip }, () => {
  const t = dataStatusText(Object.assign({ data_version: "V", current_admission_year: "2027-28" }, { last_successful_update: "2027-07-20T03:20:00Z" }), Date.parse("2027-07-21T00:00:00Z"));
  assert.match(t, /^Data updated on 20 Jul 2027 /);
});
