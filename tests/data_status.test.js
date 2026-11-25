// Stage 14d: the "Data updated on <date>" line of frontend/app.js (dataStatusText). The function is cut out of the file and run alone.
const test = require("node:test"), assert = require("node:assert"), fs = require("fs"), path = require("path");
const src = fs.readFileSync(path.join(__dirname, "..", "frontend", "app.js"), "utf8");
const m = src.match(/  function dataStatusText\(m, now\) \{[\s\S]*?\n  \}\n/);
assert.ok(m, "dataStatusText not found");
const dataStatusText = new Function(m[0] + "; return dataStatusText;")();
const DAY = 86400000, M = (iso) => ({ last_successful_update: iso, data_version: "REAL-2026-27-RIV-abc", current_admission_year: "2026-27" });
const at = (iso, plusDays, h) => Date.parse(iso) + plusDays * DAY + (h || 0) * 3600000;
test("fresh data: date of the last real change, version and admission year, no warning", () => {
  const t = dataStatusText(M("2026-11-23T12:39:55Z"), at("2026-11-23T12:39:55Z", 1));
  assert.equal(t, "Data updated on 23 Nov 2026 \u00B7 data version REAL-2026-27-RIV-abc \u00B7 latest cutoffs 2026-27");
});
test("exactly 10 days old: no warning; 11 days: warning with the number of days", () => {
  assert.doesNotMatch(dataStatusText(M("2026-11-23T12:39:55Z"), at("2026-11-23T12:39:55Z", 10, 1)), /has not changed/);
  const t = dataStatusText(M("2026-11-23T12:39:55Z"), at("2026-11-23T12:39:55Z", 11, 1));
  assert.match(t, /The data has not changed for 11 days\. Outside the CAP season that can be normal; during CAP please also check the official CET Cell website\.$/);
});
test("missing or unreadable date is said plainly and never crashes", () => {
  assert.match(dataStatusText(M(""), Date.now()), /^Data update date unknown \u00B7 data version REAL/);
  assert.match(dataStatusText(M("not a date"), Date.now()), /^Data update date unknown/);
  assert.doesNotMatch(dataStatusText(M(undefined), Date.now()), /has not changed/);
});
test("month names and the first day of a year", () => {
  assert.match(dataStatusText(M("2027-01-01T00:00:00Z"), at("2027-01-01T00:00:00Z", 0, 1)), /^Data updated on 1 Jan 2027/);
  assert.match(dataStatusText(M("2026-12-31T23:59:59Z"), at("2026-12-31T23:59:59Z", 0, 1)), /^Data updated on 31 Dec 2026/);
});
