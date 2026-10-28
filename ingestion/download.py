"""Stage 8: download the documents the project needs, check them, and record them in the archive manifest.

Reads the discovery report (Stage 7), asks ingestion.policy which documents are needed, and for each one:
  * skips it if it is unchanged since the last archived version (same size and same server validators);
  * otherwise downloads it politely (robots.txt obeyed, about 1 request per second, size limits);
  * rejects anything that does not look like a complete document (web page instead of PDF, cut off, empty, too big);
  * fingerprints it (SHA-256), stores it by content, and records a new version if the content changed.
A failed or rejected download never removes or replaces an earlier good version.
Nothing here reads the inside of the documents yet (that is Stage 9).

Run from the repository root:  python -m ingestion.download --report data/raw/discovery/latest.json
"""
import argparse, json, os, sys
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote

from .archive import (load_manifest, save_manifest, sha256_bytes, asset_name, release_tag, current_version, safe_name)
from .http_client import PoliteFetcher, BudgetExceeded
from .policy import select_documents, DEFAULT_POLICY


def check_content(url, body, headers):
    """Returns a reason string if the bytes are not a complete, plausible document; otherwise None."""
    ext = os.path.splitext(urlparse(url).path.lower())[1]
    ct = (headers.get("content-type") or "").lower()
    if not body: return "empty response"
    head = body[:300].lstrip().lower()
    if "text/html" in ct or head.startswith((b"<!doctype html", b"<html", b"<?xml")): return "a web page was returned instead of a document"
    cl = headers.get("content-length")
    if cl and cl.isdigit() and int(cl) != len(body): return "incomplete download (%d of %s bytes)" % (len(body), cl)
    if ext == ".pdf":
        if not body.startswith(b"%PDF-"): return "not a PDF (wrong file signature)"
        if b"%%EOF" not in body[-4096:]: return "PDF looks cut off (no end marker)"
    elif ext in (".xlsx", ".zip"):
        if body[:4] != b"PK\x03\x04": return "not a valid %s file" % ext[1:]
    elif ext == ".xls":
        if body[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1": return "not a valid xls file"
    return None


def _validators(headers):
    return {"etag": headers.get("etag"), "last_modified": headers.get("last-modified")}


def unchanged_since_archive(entry, disc):
    """True only when we are sure: same size and at least one server validator (ETag / Last-Modified) that matches."""
    v = current_version(entry) if entry else None
    if not v or not disc: return False
    if disc.get("size_bytes") is not None and v["size_bytes"] != disc["size_bytes"]: return False
    seen = False
    for mine, theirs in ((v.get("etag"), disc.get("etag")), (v.get("last_modified"), disc.get("last_modified"))):
        if mine and theirs:
            seen = True
            if mine != theirs: return False
    return seen


def run_download(report, manifest, fetcher, files_dir, now, force=False, policy=None):
    pol = dict(DEFAULT_POLICY, **(policy or {}))
    selected, deferred = select_documents(report, pol)
    res = {"generated_at": now, "selected": len(selected), "deferred": len(deferred), "results": [], "bytes_downloaded": 0, "problems": []}
    os.makedirs(files_dir, exist_ok=True)

    def record(d, status, size=None, note=None):
        res["results"].append({"id": d["id"], "url": d["url"], "year_label": d["year_label"], "doc_type": d["doc_type"], "cap_round": d["cap_round"],
                               "scope": d["scope"], "why": d["why"], "status": status, "size_bytes": size, "note": note})

    for d in selected:
        entry = manifest["documents"].setdefault(d["id"], {"id": d["id"], "url": d["url"], "versions": [], "current_sha256": None, "first_seen": now})
        entry.update({"url": d["url"], "file_name": safe_name(os.path.basename(unquote(urlparse(d["url"]).path))), "year_label": d["year_label"], "doc_type": d["doc_type"],
                      "cap_round": d["cap_round"], "scope": d["scope"], "qualifiers": d["qualifiers"], "link_text": d["link_text"], "source_page": d["source_page"],
                      "portal_year": d["portal_year"], "confidence": d["confidence"], "selected_because": d["why"]})
        entry["last_checked"] = now
        disc = (d.get("verification") or {})
        fcur = manifest["files"].get(entry.get("current_sha256"))
        needs_local = bool(fcur) and not fcur.get("uploaded") and not os.path.exists(os.path.join(files_dir, fcur["asset_name"]))   # an earlier upload failed: fetch again so it can be stored
        if not force and not needs_local and unchanged_since_archive(entry, disc):
            entry["last_result"], entry["last_error"] = "unchanged", None
            record(d, "unchanged", current_version(entry)["size_bytes"]); continue
        if res["bytes_downloaded"] >= pol["max_total_bytes"]:
            entry["last_result"], entry["last_error"] = "skipped", "total download limit reached"; record(d, "skipped", note="total download limit reached"); continue
        cur = current_version(entry); hdr = {}
        if cur and not force and not needs_local:
            if cur.get("etag"): hdr["If-None-Match"] = cur["etag"]
            if cur.get("last_modified"): hdr["If-Modified-Since"] = cur["last_modified"]
        try:
            r = fetcher.fetch(d["url"], "GET", headers=hdr, max_bytes=pol["max_file_bytes"] + 1)
        except BudgetExceeded as e:
            entry["last_result"], entry["last_error"] = "skipped", str(e); record(d, "skipped", note=str(e)); res["problems"].append(str(e)); break
        err = None
        if r.blocked: err = "not fetched: %s" % r.blocked
        elif r.status == 304 and cur:
            entry["last_result"], entry["last_error"] = "unchanged", None; record(d, "unchanged", cur["size_bytes"]); continue
        elif not r.ok: err = "HTTP %s%s" % (r.status, (" (%s)" % r.error) if r.error else "")
        elif len(r.body) > pol["max_file_bytes"]: err = "file is larger than the %d MB limit" % (pol["max_file_bytes"] // 1048576)
        else: err = check_content(d["url"], r.body, r.headers)
        if err:
            entry["last_result"], entry["last_error"] = "failed", err
            record(d, "failed", note=err); continue
        sha = sha256_bytes(r.body); res["bytes_downloaded"] += len(r.body)
        f = manifest["files"].get(sha)
        if f is None:
            name = asset_name(sha, entry["file_name"])
            path = os.path.join(files_dir, name); tmp = path + ".tmp"
            with open(tmp, "wb") as fh: fh.write(r.body)
            os.replace(tmp, path)
            f = manifest["files"][sha] = {"sha256": sha, "size_bytes": len(r.body), "asset_name": name, "release_tag": release_tag(d["year_label"]),
                                          "extension": os.path.splitext(name)[1], "uploaded": False, "uploaded_at": None, "urls": []}
            dup = False
        else:
            dup = True
            if not os.path.exists(os.path.join(files_dir, f["asset_name"])):          # same content known already; keep a local copy for this run
                with open(os.path.join(files_dir, f["asset_name"]), "wb") as fh: fh.write(r.body)
        if d["url"] not in f["urls"]: f["urls"].append(d["url"]); f["urls"].sort()
        ver = dict(sha256=sha, size_bytes=len(r.body), retrieved_at=now, http_status=r.status, content_type=r.headers.get("content-type"), **_validators(r.headers))
        ver["etag"] = ver["etag"] or disc.get("etag"); ver["last_modified"] = ver["last_modified"] or disc.get("last_modified")
        if cur and cur["sha256"] == sha:
            cur.update({k: ver[k] for k in ("etag", "last_modified")}); status = "unchanged"            # same bytes; validators refreshed
        else:
            entry["versions"].append(ver)
            status = "new" if not cur else "changed"
            if status == "new" and dup: status = "duplicate_content"
            if status == "changed": res["problems"].append("CHANGED: %s now has different content (was %s..., now %s...). Anything built from the old version must be re-read." % (d["url"], cur["sha256"][:12], sha[:12]))
        entry["current_sha256"] = sha; entry["last_result"], entry["last_error"] = status, None
        entry["last_success"] = now
        record(d, status, len(r.body), None if status != "duplicate_content" else "same content as another document")
    missing = [x for x in res["results"] if x["status"] in ("failed", "skipped") and not manifest["documents"][x["id"]].get("current_sha256")]
    res["required_missing"] = [{"url": x["url"], "why": x["why"], "reason": x["note"]} for x in missing]
    res["counts"] = {}
    for x in res["results"]: res["counts"][x["status"]] = res["counts"].get(x["status"], 0) + 1
    res["total_archived_bytes"] = sum(f["size_bytes"] for f in manifest["files"].values())
    return res


def render_markdown(res):
    L = ["## Document archive report", "Selected: %d. Not needed yet: %d. Downloaded this run: %.1f MB." % (res["selected"], res["deferred"], res["bytes_downloaded"] / 1048576), ""]
    L.append("Results: " + ", ".join("%s %d" % (k, v) for k, v in sorted(res["counts"].items())) + ".")
    L.append(""); L.append("| Year | Document | Result | Size (MB) |"); L.append("|---|---|---|---|")
    for x in res["results"]:
        nm = "%s%s%s" % (x["doc_type"].replace("_", " "), (" round " + x["cap_round"]) if x["cap_round"] else "", (" " + x["scope"]) if x["scope"] else "")
        L.append("| %s | %s | %s%s | %s |" % (x["year_label"], nm, x["status"], (" - " + x["note"]) if x["note"] else "", ("%.1f" % (x["size_bytes"] / 1048576)) if x["size_bytes"] else ""))
    for p in res["problems"]: L.append("- PROBLEM: " + p)
    for m in res["required_missing"]: L.append("- MISSING (needed, never archived): %s (%s)" % (m["url"], m["reason"]))
    L.append("\nTotal archived so far: %.1f MB." % (res["total_archived_bytes"] / 1048576))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", default="data/raw/discovery/latest.json"); ap.add_argument("--manifest", default="data/raw/manifest.json")
    ap.add_argument("--files", default="data/raw/files"); ap.add_argument("--out", default="data/raw/download_report.json")
    ap.add_argument("--force", action="store_true", help="download everything again, even unchanged files")
    ap.add_argument("--max-requests", type=int, default=120); ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--github-summary", action="store_true"); ap.add_argument("--now")
    a = ap.parse_args(argv)
    now = a.now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not os.path.exists(a.report): print("No discovery report at %s: run the discovery step first." % a.report); return 2
    with open(a.report, encoding="utf-8") as f: report = json.load(f)
    manifest = load_manifest(a.manifest)
    res = run_download(report, manifest, PoliteFetcher(min_delay=a.delay, max_requests=a.max_requests), a.files, now, force=a.force)
    save_manifest(a.manifest, manifest, now)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f: f.write(json.dumps(res, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    md = render_markdown(res); print(md)
    s = os.environ.get("GITHUB_STEP_SUMMARY") if a.github_summary else None
    if s: open(s, "a", encoding="utf-8").write(md + "\n")
    return 3 if res["required_missing"] else 0


if __name__ == "__main__":
    sys.exit(main())
