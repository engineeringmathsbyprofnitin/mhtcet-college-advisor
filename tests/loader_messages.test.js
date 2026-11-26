// Stage 15b: what a student reads when the data cannot be loaded. No file names, no raw status text, always what to do next.
const test = require("node:test"), assert = require("node:assert/strict"), fs = require("fs"), path = require("path");
const L = require("../frontend/dataloader.js"), R = require("../frontend/engine.js");
const DIR = path.join(__dirname, "..", "frontend", "data");
const good = async (url) => { const p = path.join(DIR, url.replace(/^data\//, "")); if (!fs.existsSync(p)) return { ok: false, status: 404, arrayBuffer: async () => new ArrayBuffer(0) }; const b = fs.readFileSync(p); return { ok: true, status: 200, arrayBuffer: async () => b.buffer.slice(b.byteOffset, b.byteOffset + b.length) }; };
const input = { percentile: 90, admissionYear: "auto", candidateType: "Maharashtra State candidate", category: "Open", gender: "Male", extraEligibility: [], branches: ["Computer Engineering"], districts: ["ANY"], maxAnnualFeeINR: 1000000, feeBasis: "total", priorities: ["balanced"] };
const fail = async (fetchFn) => { try { await L.recommend(input, { baseUrl: "data/", fetchFn, Recommender: R }); } catch (e) { return e; } assert.fail("no error"); };
const resp = (status, bytes) => ({ ok: status === 200, status, arrayBuffer: async () => bytes || new ArrayBuffer(0) });

test("a 404 on a data file says the data was updated and to reload", async () => {
  const e = await fail(async (u) => /cutoffs\//.test(u) ? resp(404) : good(u));
  assert.equal(e.code, "NETWORK"); assert.equal(e.message, "The data was updated a moment ago. Please reload the page."); assert.match(e.url, /cutoffs\//);
});
test("a server error says to try again later, without file names", async () => {
  const e = await fail(async () => resp(500)); assert.equal(e.message, "The data server did not answer properly (status 500). Please try again in a few minutes."); assert.doesNotMatch(e.message, /\.json/);
});
test("being offline says to check the connection", async () => {
  const e = await fail(async () => { throw new TypeError("Failed to fetch"); }); assert.equal(e.code, "NETWORK"); assert.equal(e.message, "Could not load the data. Please check your internet connection and try again."); assert.doesNotMatch(e.message, /\.json/);
});
test("a Wi-Fi sign-in page instead of the data is recognised and explained", async () => {
  const e = await fail(async (u) => /manifest/.test(u) ? resp(200, Buffer.from("<html>Sign in to Wi-Fi</html>").buffer) : good(u));
  assert.equal(e.code, "BAD_FILE"); assert.match(e.message, /^What came back was not the data \(a Wi-Fi sign-in page can cause this\)\. Please check your connection and reload the page\.$/); assert.doesNotMatch(e.message, /\.json/);
});
test("a damaged data file still reports its fingerprint problem and says to reload", async () => {
  const e = await fail(async (u) => { const r = await good(u); if (!/base\./.test(u)) return r; const b = Buffer.from(await r.arrayBuffer()); b[50] ^= 0xFF; return resp(200, b.buffer.slice(b.byteOffset, b.byteOffset + b.length)); });
  assert.equal(e.code, "HASH_MISMATCH"); assert.match(e.message, /did not match its fingerprint\. Please reload the page\./);
});
test("a flaky first request is retried and succeeds", async () => {
  let n = 0; const r = await L.recommend(input, { baseUrl: "data/", fetchFn: async (u) => { if (n++ === 0) throw new TypeError("blip"); return good(u); }, Recommender: R }); assert.equal(r.ok, true);
});
