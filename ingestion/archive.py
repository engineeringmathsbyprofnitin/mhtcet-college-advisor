"""The raw-document archive: a small manifest (kept in git) plus the original files (kept in GitHub Releases).

data/raw/manifest.json records, for every document: its official address, what it is, and every version ever downloaded
(SHA-256 fingerprint, size, when, server validators). Files are stored by content, so identical files are stored once.
Original files are NEVER deleted or overwritten here: a changed document becomes a new version beside the old one.

Commands (used by the GitHub Action):
  python -m ingestion.archive plan    --manifest M --files DIR      lists files still to upload:  tag|asset|sha256
  python -m ingestion.archive confirm --manifest M --shas FILE      marks those files as uploaded
  python -m ingestion.archive verify  --manifest M --files DIR      re-checks stored files against their fingerprints
"""
import argparse, hashlib, json, os, re, sys

SCHEMA_VERSION = 1


def empty_manifest():
    return {"schema_version": SCHEMA_VERSION, "updated_at": None, "documents": {}, "files": {}}


def load_manifest(path):
    if not os.path.exists(path): return empty_manifest()
    with open(path, encoding="utf-8") as f: m = json.load(f)
    if m.get("schema_version") != SCHEMA_VERSION: raise ValueError("Unknown manifest version: %r" % m.get("schema_version"))
    m.setdefault("documents", {}); m.setdefault("files", {})
    return m


def save_manifest(path, m, now=None):
    if now: m["updated_at"] = now
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: f.write(json.dumps(m, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, path)                                   # all-or-nothing: a crash never leaves a half-written manifest


def sha256_bytes(b): return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()


def safe_name(name, max_len=100):
    """A file name that cannot escape its folder or confuse GitHub: letters, digits, dot, dash, underscore only."""
    name = os.path.basename((name or "").replace("\\", "/"))
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "document"
    return name[-max_len:]


def asset_name(sha, original_name): return "%s__%s" % (sha[:16], safe_name(original_name))


def release_tag(year_label): return "raw-%s" % (year_label or "unknown-year")


def current_version(doc):
    sha = doc.get("current_sha256")
    for v in reversed(doc.get("versions", [])):
        if v["sha256"] == sha: return v
    return None


def plan_uploads(m, files_dir):
    out = []
    for sha, f in sorted(m["files"].items()):
        if not f.get("uploaded") and os.path.exists(os.path.join(files_dir, f["asset_name"])):
            out.append((f["release_tag"], f["asset_name"], sha))
    return out


def confirm_uploads(m, shas, now=None):
    n = 0
    for sha in shas:
        f = m["files"].get(sha)
        if f and not f.get("uploaded"): f["uploaded"] = True; f["uploaded_at"] = now; n += 1
    return n


def verify_store(m, files_dir):
    """Re-hash every stored file that is present locally. Returns (checked, problems)."""
    checked, problems = 0, []
    for sha, f in sorted(m["files"].items()):
        p = os.path.join(files_dir, f["asset_name"])
        if not os.path.exists(p): continue
        checked += 1
        got = sha256_file(p)
        if got != sha: problems.append("%s: fingerprint mismatch (expected %s, found %s)" % (f["asset_name"], sha[:12], got[:12]))
        elif os.path.getsize(p) != f["size_bytes"]: problems.append("%s: size differs from the manifest" % f["asset_name"])
    return checked, problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["plan", "confirm", "verify"]); ap.add_argument("--manifest", default="data/raw/manifest.json")
    ap.add_argument("--files", default="data/raw/files"); ap.add_argument("--shas"); ap.add_argument("--now")
    a = ap.parse_args(argv)
    m = load_manifest(a.manifest)
    if a.command == "plan":
        for tag, asset, sha in plan_uploads(m, a.files): print("%s|%s|%s" % (tag, asset, sha))
        return 0
    if a.command == "confirm":
        shas = [l.strip() for l in open(a.shas, encoding="utf-8")] if a.shas and os.path.exists(a.shas) else []
        n = confirm_uploads(m, [s for s in shas if s], a.now); save_manifest(a.manifest, m, a.now); print("marked %d file(s) as uploaded" % n); return 0
    checked, problems = verify_store(m, a.files)
    print("checked %d file(s); %d problem(s)" % (checked, len(problems))); [print("  " + p) for p in problems]
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
