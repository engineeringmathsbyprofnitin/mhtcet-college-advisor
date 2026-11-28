// Stage 16c-1: the feedback link in the footer of frontend/index.html.
const test = require("node:test"), assert = require("node:assert/strict"), fs = require("fs"), path = require("path");
const html = fs.readFileSync(path.join(__dirname, "..", "frontend", "index.html"), "utf8");
const FORM = "https://forms.gle/bVYF5XgabwBbMoup6", footer = html.slice(html.indexOf("<footer>"), html.indexOf("</footer>"));
test("one feedback link, to the owner's form, in the footer, opening in a new tab without leaking the page address", () => {
  const links = html.match(/<a\b[^>]*>/g) || [], ext = links.filter(a => /href="https?:/.test(a));
  assert.equal(ext.length, 1); assert.ok(ext[0].includes('href="' + FORM + '"')); assert.match(ext[0], /target="_blank"/); assert.match(ext[0], /rel="noopener noreferrer"/); assert.ok(footer.includes(FORM));
});
test("the footer tells the truth about the form: run by Google, may ask for an email address; the page itself sends nothing", () => {
  assert.match(footer, /run by Google and may ask for your email address; this page itself sends nothing/);
  assert.match(footer, /We do not ask for your name, phone or email on this page\./);
});
