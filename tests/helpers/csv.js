// Minimal CSV reader (handles quotes) used only by tests.
const fs = require("fs"), path = require("path");
function parse(text) {
  const rows = []; let row = [], f = "", q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else q = false; } else f += c; }
    else if (c === '"') q = true;
    else if (c === ",") { row.push(f); f = ""; }
    else if (c === "\n") { row.push(f.replace(/\r$/, "")); rows.push(row); row = []; f = ""; }
    else f += c;
  }
  if (f || row.length) { row.push(f); rows.push(row); }
  const h = rows.shift();
  return rows.filter(r => r.length === h.length).map(r => Object.fromEntries(h.map((k, i) => [k, r[i]])));
}
function loadDir(dir) {
  const out = {};
  fs.readdirSync(dir).filter(f => f.endsWith(".csv")).forEach(f => { out[f.replace(".csv", "")] = parse(fs.readFileSync(path.join(dir, f), "utf8")); });
  return out;
}
module.exports = { parse, loadDir };
