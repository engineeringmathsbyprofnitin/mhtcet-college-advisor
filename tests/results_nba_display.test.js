// Stage 12b-3c: how NBA / NAAC accreditation is drawn on the result card. Needs: npm install jsdom. Run: node --test tests/results_nba_display.test.js
const test = require("node:test"), assert = require("node:assert/strict");
let JSDOM = null; try { ({ JSDOM } = require("jsdom")); } catch (e) { }
const T = (name, fn) => test(name, { skip: !JSDOM ? "jsdom is not installed" : false }, fn);
const RV = require("../frontend/results.js");

function row(over) {
  return Object.assign({ rank: 1, collegeName: "Test College", collegeCode: "06001", district: "Pune", branchName: "Civil Engineering", branchCode: "19110", historicalCutoffs: [null, null, null],
    currentCutoff: null, vacancy: null, fee: null, infrastructure: null, teaching: null, placement: null, nba: null, naac: null, suitability: "Possible but uncertain", score: 50, explanation: ["x"], sources: [], docIds: [] }, over);
}
function draw(r, label) {
  const dom = new JSDOM("<body><div id='root'></div></body>"), root = dom.window.document.getElementById("root");
  const res = { ok: true, meta: { historicalYears: ["2023-24", "2024-25", "2025-26"], currentAdmissionYear: "2026-27", dataVersion: "T", usingSyntheticData: false, warnings: [], seatTypesUsed: [] }, results: [r], counts: { totalChoices: 1 }, insufficientData: [], sources: [] };
  RV.render(root, res, {});
  const td = Array.from(root.querySelectorAll("td")).find(x => x.getAttribute("data-label") === (label || "NBA accreditation"));
  return td;
}

T("an ended NBA period is shown in grey with a readable end date, never hidden", () => {
  const td = draw(row({ nba: { status: "expired", grade: null, validTo: "2025-06-30" } }));
  const main = td.querySelector(".cv > span"); assert.equal(main.textContent, "Ended on 30 Jun 2025"); assert.ok(main.classList.contains("acc-ended"));
  assert.match(td.textContent, /Period has ended; renewal may be pending/); assert.match(td.textContent, /This program only/); assert.doesNotMatch(td.textContent, /Expired/);
});
T("a valid NBA period is not grey; an undated one says the date is not known; none says No NBA record found", () => {
  let td = draw(row({ nba: { status: "valid", grade: null, validTo: "2028-06-30" } }));
  assert.equal(td.querySelector(".cv > span").textContent, "Accredited (until 2028-06-30)"); assert.ok(!td.querySelector(".acc-ended"));
  td = draw(row({ nba: { status: "validity_unknown", grade: null, validTo: null } })); assert.match(td.textContent, /Accredited, validity date not known/); assert.ok(!td.querySelector(".acc-ended"));
  td = draw(row({ nba: null }));
  assert.equal(td.querySelector(".cv > span").textContent, "No NBA record found"); assert.ok(td.querySelector(".acc-ended")); assert.match(td.textContent, /does not mean the program is not accredited/); assert.doesNotMatch(td.textContent, /Not available/);
});
T("an odd date is shown as printed, not as 'NaN'", () => {
  const td = draw(row({ nba: { status: "expired", grade: null, validTo: "June 2025" } })); assert.equal(td.querySelector(".cv > span").textContent, "Ended on June 2025");
});

T("NAAC: grade, CGPA, declaration date and the list date, no valid / expired label", () => {
  const td = draw(row({ naac: { status: "validity_unknown", grade: "B++", cgpa: "2.85", validFrom: "2024-07-19", validTo: null, listedAsOn: "2025-08-14" } }), "NAAC grade");
  assert.equal(td.querySelector(".cv > span").textContent, "B++ (CGPA 2.85)"); assert.match(td.textContent, /Declared 19 Jul 2024/); assert.match(td.textContent, /On NAAC's list as on 14 Aug 2025/);
  assert.doesNotMatch(td.textContent, /Accredited|Expired|Ended|until|validity/i); assert.ok(!td.querySelector(".acc-ended"));
});
T("NAAC without a record: grey 'No NAAC record found' with the not-a-verdict note; a row without CGPA or declaration date still draws", () => {
  let td = draw(row({ naac: null }), "NAAC grade");
  assert.equal(td.querySelector(".cv > span").textContent, "No NAAC record found"); assert.ok(td.querySelector(".acc-ended")); assert.match(td.textContent, /does not mean the college is not accredited/); assert.doesNotMatch(td.textContent, /Not available/);
  td = draw(row({ naac: { status: "validity_unknown", grade: "A", cgpa: null, validFrom: null, validTo: null, listedAsOn: "2025-08-14" } }), "NAAC grade");
  assert.equal(td.querySelector(".cv > span").textContent, "A"); assert.doesNotMatch(td.textContent, /Declared/); assert.match(td.textContent, /as on 14 Aug 2025/);
});

T("NAAC transition row: 'extended until <date>' (valid) or grey 'Extended validity ended on <date>', never a grade", () => {
  let td = draw(row({ naac: { status: "valid", grade: null, cgpa: null, validFrom: null, validTo: "2026-12-31", listedAsOn: "2025-08-14" } }), "NAAC grade");
  assert.equal(td.querySelector(".cv > span").textContent, "Accreditation extended until 31 Dec 2026"); assert.ok(!td.querySelector(".acc-ended")); assert.match(td.textContent, /transition list; grade not stated/); assert.match(td.textContent, /as on 14 Aug 2025/); assert.doesNotMatch(td.textContent, /CGPA|Declared/);
  td = draw(row({ naac: { status: "expired", grade: null, cgpa: null, validFrom: null, validTo: "2024-12-31", listedAsOn: "2025-08-14" } }), "NAAC grade");
  assert.equal(td.querySelector(".cv > span").textContent, "Extended validity ended on 31 Dec 2024"); assert.ok(td.querySelector(".acc-ended")); assert.match(td.textContent, /grade not stated/);
});
