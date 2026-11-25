// Stage 14e: how the fee is drawn when its list is older than the admission year. Needs: npm install jsdom.
const test = require("node:test"), assert = require("node:assert/strict");
let JSDOM = null; try { ({ JSDOM } = require("jsdom")); } catch (e) { }
const T = (name, fn) => test(name, { skip: !JSDOM ? "jsdom is not installed" : false }, fn);
const RV = require("../frontend/results.js");
const row = (fee) => ({ rank: 1, collegeName: "Test College", collegeCode: "06001", district: "Pune", branchName: "Civil Engineering", branchCode: "19110", historicalCutoffs: [null, null, null], currentCutoff: null, vacancy: null, fee, infrastructure: null, teaching: null, placement: null, nba: null, naac: null, suitability: "Possible but uncertain", score: 50, explanation: ["x"], sources: [], docIds: [] });
function draw(fee, meta) {
  const dom = new JSDOM("<body><div id='root'></div></body>"), root = dom.window.document.getElementById("root");
  const res = { ok: true, meta: Object.assign({ historicalYears: ["2023-24", "2024-25", "2025-26"], currentAdmissionYear: "2026-27", dataVersion: "T", usingSyntheticData: false, warnings: [], seatTypesUsed: [] }, meta), results: [row(fee)], counts: { totalChoices: 1, ranked: 1 } };
  RV.render(root, res, {});
  return { td: Array.from(root.querySelectorAll("td")).find(x => x.getAttribute("data-label") === "Annual fee"), text: root.textContent };
}
const ok = { status: "ok", value: 145500, type: "total", academicYear: "2026-27" };
T("same year: the fee list year is named, no 'not published yet' remark", () => {
  const { td } = draw(ok, { admissionYear: "2026-27" });
  assert.match(td.textContent, /145,500 per year|1,45,500 per year/); assert.match(td.textContent, /\u00B7 2026-27 fee list$/); assert.doesNotMatch(td.textContent, /not published yet/);
});
T("older list than the admission year: says plainly that the new fee is not published yet", () => {
  const { td } = draw(ok, { admissionYear: "2027-28" });
  assert.match(td.textContent, /\u00B7 2026-27 fee list \(the 2027-28 fee is not published yet\)$/);
});
T("old data without the admission year behaves as before", () => {
  const { td } = draw(ok, {}); assert.match(td.textContent, /2026-27 fee list$/); assert.doesNotMatch(td.textContent, /not published yet/);
});
T("tuition-only case carries the same remark; no fee still says Not available", () => {
  let { td } = draw({ status: "total_unavailable_tuition_known", tuitionLowerBound: 90000, academicYear: "2026-27" }, { admissionYear: "2027-28" });
  assert.match(td.textContent, /Tuition alone: .*\(2026-27 fee list \(the 2027-28 fee is not published yet\)\); total will be higher/);
  ({ td } = draw(null, { admissionYear: "2027-28" })); assert.match(td.textContent, /Not available/);
});
T("the footer names the admission year and the year of the latest cutoffs when they differ", () => {
  assert.match(draw(ok, { admissionYear: "2027-28" }).text, /admission year 2027-28 \(latest cutoffs: 2026-27\)/);
  assert.match(draw(ok, { admissionYear: "2026-27" }).text, /current admission year 2026-27/);
  assert.match(draw(ok, {}).text, /current admission year 2026-27/);
});
