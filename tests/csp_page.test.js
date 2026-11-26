// Stage 15b: the Content-Security-Policy tag of frontend/index.html and the rules that keep the page working under it.
// A strict policy blocks inline scripts/styles and foreign addresses; these tests make sure the page never needs them.
const test = require("node:test"), assert = require("node:assert/strict"), fs = require("fs"), path = require("path");
const FE = path.join(__dirname, "..", "frontend"), html = fs.readFileSync(path.join(FE, "index.html"), "utf8");
const metas = html.match(/<meta[^>]*http-equiv="Content-Security-Policy"[^>]*>/gi) || [];
const policy = metas.length ? /content="([^"]*)"/.exec(metas[0])[1] : "";
const dir = (name) => (policy.split(";").map(s => s.trim()).find(s => s.split(/\s+/)[0] === name) || "").split(/\s+/).slice(1);

test("exactly one policy tag, in the head, before every stylesheet and script", () => {
  assert.equal(metas.length, 1);
  const i = html.indexOf(metas[0]); assert.ok(i < html.indexOf("</head>"));
  assert.ok(i < html.indexOf("<link"), "policy must come before the stylesheet"); assert.ok(i < html.indexOf("<script"), "policy must come before the scripts");
});
test("the policy allows only the site itself and never unsafe-inline, unsafe-eval or a wildcard", () => {
  assert.deepEqual(dir("default-src"), ["'self'"]); assert.deepEqual(dir("script-src"), ["'self'"]); assert.deepEqual(dir("style-src"), ["'self'"]); assert.deepEqual(dir("connect-src"), ["'self'"]);
  assert.deepEqual(dir("img-src"), ["'self'", "data:"]); assert.deepEqual(dir("object-src"), ["'none'"]); assert.deepEqual(dir("base-uri"), ["'none'"]); assert.deepEqual(dir("form-action"), ["'none'"]);
  assert.doesNotMatch(policy, /unsafe-inline|unsafe-eval|\*|https?:/);
});
test("the page needs nothing the policy blocks: no inline script or style, no handlers, no foreign addresses", () => {
  const body = html.replace(metas[0], "");
  const scripts = body.match(/<script\b[^>]*>[\s\S]*?<\/script>/gi) || []; assert.ok(scripts.length >= 5);
  scripts.forEach(s => { assert.match(s, /^<script src="[a-z-]+\.js"><\/script>$/, "inline or odd script: " + s.slice(0, 80)); });
  assert.doesNotMatch(body, /<style\b/i); assert.doesNotMatch(body, /\sstyle\s*=/i); assert.doesNotMatch(body, /\son[a-z]+\s*=/i); assert.doesNotMatch(body, /javascript:/i);
  (body.match(/\s(?:src|href)="[^"]*"/gi) || []).forEach(a => assert.doesNotMatch(a, /(?:https?:)?\/\//, "foreign address in the page: " + a));
  (body.match(/<link\b[^>]*>/gi) || []).forEach(l => assert.match(l, /rel="stylesheet" href="styles\.css"/));
});
test("the stylesheet has no imports or foreign addresses", () => {
  const css = fs.readFileSync(path.join(FE, "styles.css"), "utf8"); assert.doesNotMatch(css, /@import|url\(\s*['"]?(?:https?:)?\/\//i);
});
test("page scripts never write markup, set style attributes, evaluate text or call foreign addresses", () => {
  ["app.js", "dataloader.js", "engine.js", "results.js", "pdfexport.js", "config.js"].forEach(f => {
    const js = fs.readFileSync(path.join(FE, f), "utf8");
    assert.doesNotMatch(js, /innerHTML|outerHTML|insertAdjacentHTML|document\.write|\beval\(|new Function\(|setAttribute\(\s*["']style["']|cssText|\.style\s*=\s*["'`]/, f);
    assert.doesNotMatch(js.replace(/\/\/.*$/gm, "").replace(/\/\*[\s\S]*?\*\//g, ""), /["']https?:\/\//, f + ": a foreign address");
  });
});
