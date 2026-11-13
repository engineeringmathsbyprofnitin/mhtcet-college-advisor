// Stage 10c-3b UI tests: the real index.html + scripts in jsdom, using the REAL packaged data (folder in REAL_DATA_DIR, built by tests/test_stage10c3b.py).
// Run by hand: python -m ingestion.package_real /tmp/realdata && REAL_DATA_DIR=/tmp/realdata NODE_PATH=<folder with jsdom> node --test tests/ui_real.test.js
const test = require("node:test"), assert = require("node:assert/strict");
const fs = require("fs"), path = require("path"), util = require("util");
let JSDOM = null; try { ({ JSDOM } = require("jsdom")); } catch (e) { }
const DIR = process.env.REAL_DATA_DIR, FE = path.join(__dirname, "..", "frontend");
const T = (name, fn) => test(name, { skip: !JSDOM ? "jsdom is not installed" : !DIR ? "REAL_DATA_DIR not set" : false }, fn);
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function boot(search, dir) {
  const html = fs.readFileSync(path.join(FE, "index.html"), "utf8").replace(/<script src="[^"]+"><\/script>/g, "");
  const dom = new JSDOM(html, { runScripts: "outside-only", url: "http://localhost/frontend/index.html" + (search || "") }), w = dom.window;
  w.TextDecoder = util.TextDecoder; w.HTMLElement.prototype.scrollIntoView = function () {};
  w.fetch = async (url) => { const p = path.join(dir || DIR, url.replace(/^data(-real)?\//, "")); if (!fs.existsSync(p)) return { ok: false, status: 404, arrayBuffer: async () => new ArrayBuffer(0) };
    const b = fs.readFileSync(p); return { ok: true, status: 200, arrayBuffer: async () => b.buffer.slice(b.byteOffset, b.byteOffset + b.length) }; };
  ["config.js", "engine.js", "dataloader.js", "pdfexport.js", "results.js", "app.js"].forEach(f => w.eval(fs.readFileSync(path.join(FE, f), "utf8")));
  for (let i = 0; i < 60 && document_hidden(w); i++) await sleep(50);
  return { w, d: w.document, $: id => w.document.getElementById(id) };
}
const document_hidden = w => w.document.getElementById("huField").hidden;
const opts = sel => Array.from(sel.options).map(o => o.value);

T("form lists come from the real data; home university, claims and district lock appear", async () => {
  const B = await boot();
  assert.match(B.$("dataStatus").textContent, /REAL-2026-27-RIV-/); assert.equal(B.$("dataBanner").hidden, true);
  assert.equal(B.$("phaseBanner").hidden, false); assert.match(B.$("phaseBanner").textContent, /rounds I, II, III, IV are published \(all four rounds\)/);
  assert.deepEqual(opts(B.$("candidateType")), ["", "Maharashtra State candidate", "All India candidate", "Other Than Maharashtra (OMS) candidate"]);
  assert.deepEqual(Array.from(B.$("candidateType").options).map(o => o.disabled), [false, false, true, true]);
  assert.match(B.$("candidateType").options[2].textContent, /coming soon/);
  const cats = opts(B.$("category")); assert.equal(cats[1], "OPEN"); ["SC", "ST", "VJ", "NT1", "NT2", "NT3", "OBC", "SEBC"].forEach(c => assert.ok(cats.includes(c), c));
  const hu = opts(B.$("homeUniversity")); assert.equal(hu.length, 13); assert.ok(hu.includes("Savitribai Phule Pune University"));
  const ex = Array.from(B.d.querySelectorAll("input[name=extras]")).map(x => x.value).sort(); assert.deepEqual(ex, ["defence", "ews", "orphan", "pwd", "tfws"]);
  assert.ok(opts(B.$("branches").querySelector("select")).includes("Computer Engineering"));
  assert.equal(B.$("anyDistrict").checked, true); assert.equal(B.$("anyDistrict").disabled, false); B.$("anyDistrict").click(); assert.equal(B.$("addDistrict").disabled, false); assert.equal(B.$("districtNote").hidden, false);
});
T("a student gets real results with the four round figures; no test-data banner", async () => {
  const B = await boot();
  B.$("percentile").value = "92"; B.$("candidateType").value = "Maharashtra State candidate"; B.$("category").value = "OPEN"; B.$("gender").value = "Male";
  B.$("homeUniversity").value = "Savitribai Phule Pune University"; B.$("branches").querySelector("select").value = "Computer Engineering";
  B.$("maxFee").value = "1000000"; B.$("feeBasis").value = "total";
  B.$("form").dispatchEvent(new B.w.Event("submit", { cancelable: true, bubbles: true }));
  for (let i = 0; i < 100 && !B.d.querySelector("#resultsTable"); i++) await sleep(50);
  assert.ok(B.d.querySelector("#resultsTable"), B.$("results").textContent.slice(0, 300));
  const r = B.d.querySelector("tr.result .rounds"); assert.ok(r); assert.match(r.textContent, /Round I: .*Round II: .*Round III: .*Round IV: /);
  assert.ok(!/TEST DATA/.test(B.$("results").textContent));
  assert.ok(!/did not choose a home university/.test(B.$("results").textContent));
});
T("without a home university the page warns", async () => {
  const B = await boot();
  B.$("percentile").value = "92"; B.$("candidateType").value = "Maharashtra State candidate"; B.$("category").value = "OPEN";
  B.$("branches").querySelector("select").value = "Computer Engineering"; B.$("maxFee").value = "1000000";
  B.$("form").dispatchEvent(new B.w.Event("submit", { cancelable: true, bubbles: true }));
  for (let i = 0; i < 100 && !B.d.querySelector("#resultsTable"); i++) await sleep(50);
  assert.match(B.$("results").textContent, /did not choose a home university/);
});
T("a district choice is accepted and the page explains it is not applied yet", async () => {
  const B = await boot();
  B.$("percentile").value = "92"; B.$("candidateType").value = "Maharashtra State candidate"; B.$("category").value = "OPEN";
  B.$("branches").querySelector("select").value = "Computer Engineering"; B.$("maxFee").value = "1000000"; B.$("homeUniversity").value = "Mumbai University";
  B.$("anyDistrict").click(); B.$("districts").querySelector("select").value = "Pune";   // untick "Any district", choose Pune
  B.$("form").dispatchEvent(new B.w.Event("submit", { cancelable: true, bubbles: true }));
  for (let i = 0; i < 100 && !B.d.querySelector("#resultsTable"); i++) await sleep(50);
  assert.ok(B.d.querySelector("#resultsTable"), B.$("results").textContent.slice(0, 300));
  assert.match(B.$("results").textContent, /District data is not available yet/);
});
T("preview address (?preview=1) loads data-real and shows the preview banner; the normal address does not", async () => {
  const P = await boot("?preview=1");
  assert.equal(P.$("previewBanner").hidden, false); assert.match(P.$("dataStatus").textContent, /REAL-2026-27-RIV-/);
  const N = await boot("");
  assert.equal(N.w.APP_CONFIG.DATA_BASE_URL, "data/");
});
T("the Download PDF button builds the report from the shown results (no print dialog needed)", async () => {
  const B = await boot(); let got = null;
  B.w.PdfExport.download = (res) => { got = res; };
  B.$("percentile").value = "92"; B.$("candidateType").value = "Maharashtra State candidate"; B.$("category").value = "OPEN"; B.$("homeUniversity").value = "Mumbai University";
  B.$("branches").querySelector("select").value = "Computer Engineering"; B.$("maxFee").value = "1000000";
  B.$("form").dispatchEvent(new B.w.Event("submit", { cancelable: true, bubbles: true }));
  for (let i = 0; i < 100 && !B.d.querySelector("#resultsTable"); i++) await sleep(50);
  const btn = B.d.getElementById("pdfBtn"); assert.ok(btn); assert.equal(btn.textContent, "Download PDF"); btn.click();
  assert.ok(got && got.results.length > 5);
});
T("when the data has official districts the form offers exactly those and a district choice filters", async () => {
  const D = process.env.DISTRICT_DATA_DIR; if (!D) return;
  const B = await boot("", D);
  assert.equal(B.$("anyDistrict").checked, false); assert.equal(B.$("districtNote").hidden, true);
  const ds = opts(B.$("districts").querySelector("select")); assert.ok(ds.includes("Satara") && ds.includes("Amravati")); assert.ok(!ds.includes("Not available"));
  B.$("percentile").value = "60"; B.$("candidateType").value = "Maharashtra State candidate"; B.$("category").value = "OPEN"; B.$("homeUniversity").value = "Mumbai University";
  B.$("branches").querySelector("select").value = "Computer Science and Engineering"; B.$("maxFee").value = "1000000"; B.$("districts").querySelector("select").value = "Satara";
  B.$("form").dispatchEvent(new B.w.Event("submit", { cancelable: true, bubbles: true }));
  for (let i = 0; i < 100 && !B.d.querySelector("#resultsTable") && !/No colleges/i.test(B.$("results").textContent); i++) await sleep(50);
  assert.ok(!/District data is not available yet/.test(B.$("results").textContent));
  const rows = Array.from(B.d.querySelectorAll("tr.result")); rows.forEach(r => assert.match(r.textContent, /Satara/));
});
