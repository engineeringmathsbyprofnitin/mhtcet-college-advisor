// Stage 16a: the "How to read these results" section of frontend/index.html says only what the engine really does.
const test = require("node:test"), assert = require("node:assert/strict"), fs = require("fs"), path = require("path");
const html = fs.readFileSync(path.join(__dirname, "..", "frontend", "index.html"), "utf8"), engine = fs.readFileSync(path.join(__dirname, "..", "frontend", "engine.js"), "utf8");
const help = /<details class="help" id="help">([\s\S]*?)<\/details>/.exec(html)[1], text = help.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
test("the section exists once, is closed by default and sits before the footer", () => {
  assert.equal((html.match(/<details/g) || []).length, 1); assert.doesNotMatch(html, /<details[^>]*\bopen\b/); assert.ok(html.indexOf('<details class="help"') < html.indexOf("<footer>"));
  assert.match(help, /<summary>How to read these results<\/summary>/);
});
test("every label the engine can show is explained, and nothing else is announced as a label", () => {
  ["Historically more suitable", "Possible but uncertain", "Ambitious choice", "Limited evidence"].forEach(l => { assert.ok(engine.includes('"' + l + '"'), l + " is not an engine label"); assert.match(help, new RegExp("<strong>" + l + "</strong>")); });
  assert.equal((help.match(/<li><strong>/g) || []).length, 4);
});
test("the claims match the engine's settings", () => {
  const R = require("../frontend/engine.js"), d = R.DEFAULTS;
  assert.equal(d.evidenceWeights.hist.length, 3); assert.match(text, /three earlier years/);            // three earlier years
  assert.deepEqual(d.vacancyRounds, ["IV", "III"]);
  assert.ok(d.weights.balanced.placement > 0 && d.weights.balanced.teaching > 0); assert.match(text, /no data yet on placements, teaching quality or infrastructure/);
  assert.ok(d.weights.balanced.strength > 0); assert.match(text, /higher past cutoffs come first/);
});
test("it points to the official site, says it is not a prediction, and has no numbers that could go stale", () => {
  assert.match(text, /official CET Cell website/); assert.match(text, /does not predict this year's cutoffs/);
  assert.doesNotMatch(text, /\d{4}|\d+%|\d+ (?:percentile|colleges|rows)/);
});
