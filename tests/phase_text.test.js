// Stage 14b: the banner text of frontend/app.js (phaseText) for the calendar admission year. The function is cut out of the file and run alone.
const test = require("node:test"), assert = require("node:assert"), fs = require("fs"), path = require("path");
const src = fs.readFileSync(path.join(__dirname, "..", "frontend", "app.js"), "utf8");
const m = src.match(/  function phaseText\(dv, year\) \{[\s\S]*?\n  \}\n/);
assert.ok(m, "phaseText not found");
const phaseText = new Function(m[0] + "; return phaseText;")();
const dv = s => ({ row_count_summary: s });
test("admission year ahead of the cutoff year: Round I option-form message", () => {
  const t = phaseText(dv("rounds=I+II+III+IV;next=none;phase=previous_cycle_latest;admission=2027-28"), "2026-27");
  assert.match(t, /^Admission year 2027-28: its cutoff lists are published only after the CAP Round I allotment/);
  assert.match(t, /Round I option form/); assert.match(t, /cutoffs of 2026-27 \(CAP rounds I, II, III, IV\)/); assert.match(t, /not a prediction for 2027-28/);
});
test("same year: the normal messages are unchanged", () => {
  assert.match(phaseText(dv("rounds=I+II+III+IV;next=none;phase=confirmed;admission=2026-27"), "2026-27"), /^Admission year 2026-27: CAP rounds I, II, III, IV are published \(all four rounds\)/);
  assert.match(phaseText(dv("rounds=I;next=II;phase=confirmed;admission=2027-28"), "2027-28"), /Round II is expected next and is not published yet/);
});
test("older data without the admission field keeps the old wording", () => {
  assert.match(phaseText(dv("rounds=I+II+III+IV;next=none;phase=previous_cycle_latest"), "2026-27"), /^Cutoffs for the new admission year are not published yet/);
  assert.equal(phaseText(dv(""), "2026-27"), "");
});
