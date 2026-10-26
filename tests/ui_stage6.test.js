// Stage 6 UI tests: runs the real index.html + scripts in a simulated browser (jsdom), fills the form like a student,
// and inspects what is shown. Uses SYNTHETIC data. It does not replace looking at the page on real phones.
// Needs:  npm install jsdom      Run from the repository root:  node --test tests/ui_stage6.test.js
const test = require("node:test"), assert = require("node:assert/strict");
const fs = require("fs"), path = require("path"), util = require("util");
let JSDOM = null; try { ({ JSDOM } = require("jsdom")); } catch (e) { /* jsdom not installed: tests are skipped */ }
const FE = path.join(__dirname, "..", "frontend");
const T = (name, fn) => test(name, { skip: JSDOM ? false : "jsdom is not installed (npm install jsdom)" }, fn);
const sleep = ms => new Promise(r => setTimeout(r, ms));

function boot(o) {
  o = o || {};
  const html = fs.readFileSync(path.join(FE, "index.html"), "utf8").replace(/<script src="[^"]+"><\/script>/g, "");
  const dom = new JSDOM(html, { runScripts: "outside-only", url: "http://localhost/frontend/index.html" }), w = dom.window;
  w.TextDecoder = util.TextDecoder; w.HTMLElement.prototype.scrollIntoView = function () {};
  const calls = []; w.__calls = calls;
  w.fetch = async (url) => {
    calls.push(url);
    if (o.failOn && o.failOn(url, calls)) throw new TypeError("Failed to fetch");
    const p = path.join(FE, url); let buf = fs.readFileSync(p);
    if (o.mutate) buf = o.mutate(url, buf) || buf;
    return { ok: true, status: 200, arrayBuffer: async () => buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.length) };
  };
  if (o.verify) Object.defineProperty(w, "crypto", { value: require("crypto").webcrypto, configurable: true });
  ["config.js", "engine.js", "dataloader.js", "results.js", "app.js"].forEach(f => w.eval(fs.readFileSync(path.join(FE, f), "utf8")));
  return { w, d: w.document, $: id => w.document.getElementById(id), calls };
}
function fill(B, v) {
  v = Object.assign({ percentile: "93.5", ct: "Maharashtra State candidate", cat: "OBC", gender: "Female", br: ["Computer Science and Engineering", "Information Technology", "Computer Engineering"], dist: ["Pune", "Mumbai Suburban"], any: false, fee: "200000", basis: "tuition", prio: ["placements"] }, v || {});
  B.$("percentile").value = v.percentile; B.$("candidateType").value = v.ct; B.$("category").value = v.cat; B.$("gender").value = v.gender || "";
  const bs = B.$("branches").querySelectorAll("select"); v.br.forEach((x, i) => bs[i].value = x);
  if (v.any) { B.$("anyDistrict").checked = true; B.$("anyDistrict").dispatchEvent(new B.w.Event("change")); }
  else { const ds = B.$("districts").querySelectorAll("select"); v.dist.forEach((x, i) => ds[i].value = x); }
  B.$("maxFee").value = v.fee; B.$("feeBasis").value = v.basis;
  B.$("balanced").checked = false; B.d.querySelectorAll("input[name=priorities]").forEach(c => c.checked = v.prio.indexOf(c.value) >= 0);
}
async function submit(B, v) {
  fill(B, v); B.$("form").dispatchEvent(new B.w.Event("submit", { cancelable: true, bubbles: true }));
  for (let i = 0; i < 200; i++) { await sleep(10); const r = B.$("results"); if (!r.hidden && !r.querySelector("[role=status]")) return; }
  throw new Error("results never appeared");
}
const rows = B => Array.from(B.d.querySelectorAll("#results tr.result"));
const hdrs = B => Array.from(B.d.querySelectorAll("#results thead th")).map(t => t.textContent);

T("page header shows data version, year and the test-data banner", async () => {
  const B = boot(); await sleep(50);
  assert.match(B.$("dataStatus").textContent, /Data version SYN-v1 .* admission year 2026-27 .* last updated 2026-10-20/);
  assert.equal(B.$("dataBanner").hidden, false); assert.match(B.$("dataBanner").textContent, /TEST DATA/);
});
T("empty form shows errors and loads no data files beyond the header", async () => {
  const B = boot(); await sleep(30); const n = B.calls.length;
  B.$("form").dispatchEvent(new B.w.Event("submit", { cancelable: true, bubbles: true })); await sleep(30);
  assert.equal(B.calls.length, n); assert.equal(B.$("results").hidden, true); assert.notEqual(B.$("percentile-err").textContent, "");
});
T("valid request: ranked table, 5 leading rows, 'Show more' works", async () => {
  const B = boot(); await submit(B);
  assert.equal(rows(B).length, 9); assert.equal(B.d.querySelectorAll("#topRows tr.result").length, 5); assert.equal(B.$("moreRows").hidden, true);
  assert.deepEqual(rows(B).map(r => r.querySelector("td").textContent), ["#1", "#2", "#3", "#4", "#5", "#6", "#7", "#8", "#9"]);
  const b = B.$("toggleMore"); assert.equal(b.textContent, "Show more suitable choices (6\u201320)"); assert.equal(b.getAttribute("aria-expanded"), "false");
  b.click(); assert.equal(B.$("moreRows").hidden, false); assert.equal(b.getAttribute("aria-expanded"), "true");
  b.click(); assert.equal(B.$("moreRows").hidden, true); assert.equal(b.textContent, "Show more suitable choices (6\u201320)");
});
T("all required report columns are present, with the right year headings", async () => {
  const B = boot(); await submit(B), h = hdrs(B);
  assert.deepEqual(h, ["Rank", "College", "Branch", "Cutoff 2025-26", "Cutoff 2024-25", "Cutoff 2023-24", "Latest current cutoff (2026-27)", "Latest vacancy", "Annual fee", "Infrastructure", "Teaching", "Placement", "NBA accreditation", "NAAC grade", "Suitability"]);
  rows(B).forEach(r => assert.equal(r.querySelectorAll("td").length, h.length));
  const first = rows(B)[0].textContent; assert.match(first, /College code SYN\d+/); assert.match(first, /Branch code B\d+/); assert.match(first, /CAP Round/);
});
T("missing data is shown as 'Not available' or 'Vacancy data unavailable', never as blanks, zero, null or NaN", async () => {
  const B = boot(); await submit(B);                         // default student: some choices have no vacancy figure
  let txt = B.$("results").textContent;
  assert.match(txt, /Not available/); assert.match(txt, /Vacancy data unavailable/); assert.ok(!/undefined|NaN|null|\[object/.test(txt));
  const S = boot(); await submit(S, { br: ["Mechanical Engineering", "Civil Engineering"], dist: ["Sangli"], percentile: "70", fee: "900000" });   // this college has no fee data
  txt = S.$("results").textContent; assert.ok(!/undefined|NaN|null|\[object/.test(txt));
  rows(S).forEach(r => assert.match(r.querySelector('[data-label="Annual fee"]').textContent, /Not available/));
  rows(S).forEach(r => assert.match(r.querySelector('[data-label="Latest vacancy"]').textContent, /seat\(s\)/));   // vacancy that exists is shown, not hidden
});
T("fee wording does not pass tuition off as total cost; estimates are labelled", async () => {
  const B = boot(); await submit(B); const t = B.$("results").textContent;
  assert.match(t, /Tuition fee only; excludes hostel, transport and exam charges/); assert.match(t, /System estimate, not an official score/);
  const B2 = boot(); await submit(B2, { basis: "total" }); assert.match(B2.$("results").textContent, /Total cost not available|Total yearly expenses/);
});
T("each result explains itself and lists sources; test links are not clickable", async () => {
  const B = boot(); await submit(B);
  const why = B.d.querySelectorAll("#results tr.why"); assert.equal(why.length, 9);
  why.forEach(w => { assert.match(w.querySelector("summary").textContent, /Why this choice/); assert.ok(w.querySelectorAll("ul.explain li").length >= 5); assert.ok(w.querySelectorAll("ul.sources li").length >= 1); });
  assert.equal(B.d.querySelectorAll("#results a[href*='example.invalid']").length, 0); assert.match(B.$("results").textContent, /test link, not a real page/);
});
T("synthetic banner, disclaimer, data version and vacancy round are shown in the report", async () => {
  const B = boot(); await submit(B); const t = B.$("results").textContent;
  assert.ok(B.$("results").querySelector(".banner.danger[role=alert]")); assert.match(t, /TEST DATA/);
  assert.match(t, /Data version SYN-v1/); assert.match(t, /last successful data update: 2026-10-20/); assert.match(t, /2025-26, 2024-25, 2023-24/);
  assert.match(t, /Vacancy figures come from CAP Round III/); assert.match(t, /not a prediction or a guarantee/);
});
T("few results are reported honestly; zero results give guidance", async () => {
  const B = boot(); await submit(B, { br: ["Civil Engineering"], dist: ["Kolhapur"], percentile: "90", cat: "Open", gender: "", prio: ["balanced"] });
  assert.equal(rows(B).length, 1); assert.match(B.$("results").textContent, /Only 1 choice\(s\) matched/); assert.equal(B.$("toggleMore"), null);
  const Z = boot(); await submit(Z, { br: ["Civil Engineering"], dist: ["Nashik"], percentile: "75", cat: "Open", gender: "" });
  assert.equal(rows(Z).length, 0); assert.match(Z.$("results").textContent, /No choices matched your preferences/); assert.equal(Z.d.querySelector("#results table"), null);
});
T("a category with no cutoff list shows the engine's warning", async () => {
  const B = boot(); await submit(B, { cat: "ST", gender: "" }); assert.match(B.$("results").textContent, /No cutoff data for the category "ST"/);
});
T("a candidate type with no data gets a clear explanation, not a blank page", async () => {
  const B = boot(); await submit(B, { ct: "All India candidate" }); assert.match(B.$("results").textContent, /No cutoff group in the data matches/); assert.match(B.$("results").textContent, /No choices matched/);
});
T("focus moves to the results heading and the button is usable again", async () => {
  const B = boot(); await submit(B); await sleep(20);
  assert.equal(B.d.activeElement.id, "resultsHeading"); assert.equal(B.$("submitBtn").disabled, false); assert.equal(B.$("submitBtn").textContent, "Show my recommendations");
});
T("while loading, the button is disabled, and a double submit runs only once", async () => {
  const B = boot(); fill(B); const ev = () => B.$("form").dispatchEvent(new B.w.Event("submit", { cancelable: true, bubbles: true }));
  ev(); assert.equal(B.$("submitBtn").disabled, true); ev();
  for (let i = 0; i < 200 && (B.$("results").querySelector("[role=status]") || B.$("results").hidden); i++) await sleep(10);
  assert.equal(B.calls.filter(u => /base\./.test(u)).length, 1);
});
T("a network failure shows a friendly message and the student can try again", async () => {
  let fail = true; const B = boot({ failOn: u => fail && /base\./.test(u) }); fill(B);
  B.$("form").dispatchEvent(new B.w.Event("submit", { cancelable: true, bubbles: true }));
  for (let i = 0; i < 200 && !B.$("results").querySelector(".banner"); i++) await sleep(10);
  assert.match(B.$("results").textContent, /check your internet connection/); assert.equal(B.$("submitBtn").disabled, false); assert.ok(!/TypeError|Failed to fetch|at /.test(B.$("results").textContent));
  fail = false; await submit(B); assert.equal(rows(B).length, 9);
});
T("tampered data file is refused with a clear message (fingerprint check active)", async () => {
  const B = boot({ verify: true, mutate: (u, b) => /cutoffs\/GOPENS/.test(u) ? Buffer.from(b.toString().replace("9", "8")) : b }); fill(B);
  B.$("form").dispatchEvent(new B.w.Event("submit", { cancelable: true, bubbles: true }));
  for (let i = 0; i < 300 && !B.$("results").querySelector(".banner"); i++) await sleep(10);
  assert.match(B.$("results").textContent, /did not match its fingerprint/); assert.equal(B.d.querySelectorAll("#results tr.result").length, 0);
});
T("text from data files can never inject HTML or scripts", async () => {
  const evil = '<img src=x onerror="window.__pwned=1"><script>window.__pwned=2<\/script>';
  const B = boot({ mutate: (u, b) => { if (!/base\./.test(u)) return b; const j = JSON.parse(b.toString()); const i = j.colleges.columns.indexOf("college_name"); j.colleges.rows.forEach(r => r[i] = evil); return Buffer.from(JSON.stringify(j)); } });
  await submit(B); await sleep(30);
  assert.equal(B.d.querySelectorAll("#results img, #results script").length, 0); assert.equal(B.w.__pwned, undefined); assert.ok(B.$("results").textContent.includes("<img src=x"));
});
T("the report is accessible: caption, column scopes, live region, scrollable region label", async () => {
  const B = boot(); await submit(B);
  assert.ok(B.d.querySelector("#results caption")); assert.equal(B.d.querySelectorAll("#results th[scope=col]").length, 15); assert.equal(B.$("results").getAttribute("aria-live"), "polite");
  assert.match(B.d.querySelector(".table-scroll").getAttribute("aria-label"), /scrolls sideways/); assert.ok(B.d.querySelector(".table-scroll").getAttribute("tabindex") === "0");
});
T("suitability is shown in words (not colour alone)", async () => {
  const B = boot(); await submit(B); const labels = Array.from(B.d.querySelectorAll("#results .badge")).map(b => b.textContent);
  assert.equal(labels.length, 9); labels.forEach(l => assert.ok(["Historically more suitable", "Possible but uncertain", "Ambitious choice", "Limited evidence"].includes(l)));
});
T("print button calls print; clear form removes the report", async () => {
  const B = boot(); let printed = 0; B.w.print = () => printed++; await submit(B);
  B.$("printBtn").click(); assert.equal(printed, 1);
  B.$("form").dispatchEvent(new B.w.Event("reset")); await sleep(10); assert.equal(B.$("results").hidden, true); assert.equal(B.$("results").textContent, "");
});
T("nothing the student types is sent anywhere: only data-file requests are made, and no storage is used", async () => {
  const B = boot(); await submit(B);
  assert.ok(B.calls.every(u => /^data\/(manifest\.json|base\.[0-9a-f]+\.json|cutoffs\/[A-Za-z0-9_-]+\.[0-9a-f]+\.json)$/.test(u)), B.calls.join(","));
  assert.ok(!B.calls.some(u => /93\.5|200000|Pune/i.test(u)));
});
test("source code never uses innerHTML or storage APIs", () => {
  ["app.js", "results.js", "dataloader.js"].forEach(f => { const s = fs.readFileSync(path.join(FE, f), "utf8"); assert.ok(!/innerHTML|outerHTML|insertAdjacentHTML|document\.write|localStorage|sessionStorage|eval\(/.test(s), f); });
});
