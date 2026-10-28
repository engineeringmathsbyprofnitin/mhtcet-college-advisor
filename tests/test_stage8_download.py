"""Stage 8 tests: downloading, checking and archiving documents, against a FAKE CET Cell (simulated; no network).
Passing proves the logic; the first live GitHub Action run proves it on the real servers."""
import sys, os, json, unittest, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage8_helpers import *
from ingestion import download as DL, archive as AR
from ingestion.http_client import PoliteFetcher

def setup(docs=None, extra=None):
    docs = docs or Docs(); return docs, make_report(docs, extra)

def run(docs, report, manifest=None, files=None, extra=None, now=NOW, force=False, policy=None, **fk):
    f, tr = new_fetcher(docs, extra, **fk); manifest = manifest if manifest is not None else AR.empty_manifest(); files = files or tmpdir()
    res = DL.run_download(report, manifest, f, files, now, force=force, policy=policy)
    return res, manifest, files, tr

def body_gets(tr): return [u for m, u, h in tr.calls if m == "GET" and u.endswith(".pdf") and "Range" not in h]
def status(res): return {x["url"].rsplit("/", 1)[1]: x["status"] for x in res["results"]}

class FirstRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs, cls.report = setup(); cls.res, cls.m, cls.files, cls.tr = run(cls.docs, cls.report)
    def test_everything_needed_is_archived(self):
        self.assertEqual(self.res["counts"], {"new": 17}); self.assertEqual(len(self.m["documents"]), 17); self.assertEqual(len(self.m["files"]), 17); self.assertEqual(self.res["required_missing"], [])
        self.assertEqual(len(body_gets(self.tr)), 17)
    def test_files_are_stored_under_safe_content_based_names(self):
        for sha, f in self.m["files"].items():
            self.assertRegex(f["asset_name"], r"^[0-9a-f]{16}__[A-Za-z0-9._-]+\.pdf$"); self.assertTrue(f["asset_name"].startswith(sha[:16]))
            p = os.path.join(self.files, f["asset_name"]); self.assertEqual(AR.sha256_file(p), sha); self.assertEqual(os.path.getsize(p), f["size_bytes"])
    def test_release_tag_follows_the_documents_year(self):
        tags = {f["release_tag"] for f in self.m["files"].values()}; self.assertEqual(tags, {"raw-2026-27", "raw-2025-26", "raw-2024-25", "raw-2023-24"})
    def test_source_address_and_meaning_are_recorded(self):
        e = [x for x in self.m["documents"].values() if x["url"].endswith("2026ENGG_CAP4_MH_CutOff.pdf")][0]
        self.assertEqual((e["year_label"], e["doc_type"], e["cap_round"], e["scope"]), ("2026-27", "cutoff", "IV", "MH")); self.assertEqual(e["last_checked"], NOW); self.assertEqual(e["last_result"], "new")
        self.assertTrue(e["source_page"].startswith("https://fe2026.mahacet.org/")); v = e["versions"][0]; self.assertEqual(v["retrieved_at"], NOW); self.assertTrue(v["etag"]); self.assertEqual(e["current_sha256"], v["sha256"])
    def test_nothing_not_selected_was_downloaded(self):
        asked = " ".join(body_gets(self.tr))
        for bad in ("ACAP", "CourtOder", "Diploma", "CAP2.pdf", "2024SeatMatrix", "2025SeatMatrix"): self.assertNotIn(bad, asked)
    def test_files_are_downloaded_politely(self):
        self.assertTrue(all("MHTCETCollegeAdvisorBot" in h["User-Agent"] for m, u, h in self.tr.calls))
    def test_totals_are_reported(self):
        self.assertEqual(self.res["total_archived_bytes"], sum(f["size_bytes"] for f in self.m["files"].values())); self.assertEqual(self.res["bytes_downloaded"], self.res["total_archived_bytes"])
    def test_markdown_report_lists_every_file(self):
        md = DL.render_markdown(self.res); self.assertIn("| Year | Document | Result | Size (MB) |", md); self.assertEqual(md.count("| new |") + md.count("| new -"), 17)

class Repeat(unittest.TestCase):
    def test_unchanged_files_are_not_downloaded_again_but_are_marked_checked(self):
        docs, rep = setup(); res1, m, files, _ = run(docs, rep); res2, m2, _, tr = run(docs, make_report(docs), m, files, now="2026-11-02T09:00:00Z")
        self.assertEqual(res2["counts"], {"unchanged": 17}); self.assertEqual(body_gets(tr), []); self.assertEqual(res2["bytes_downloaded"], 0)
        e = list(m2["documents"].values())[0]; self.assertEqual(e["last_checked"], "2026-11-02T09:00:00Z"); self.assertEqual(len(e["versions"]), 1)
    def test_force_downloads_everything_again_but_adds_no_versions(self):
        docs, rep = setup(); _, m, files, _ = run(docs, rep); res, m2, _, tr = run(docs, rep, m, files, force=True)
        self.assertEqual(len(body_gets(tr)), 17); self.assertEqual(res["counts"], {"unchanged": 17}); self.assertTrue(all(len(e["versions"]) == 1 for e in m2["documents"].values()))
    def test_a_replaced_file_becomes_a_new_version_and_the_old_one_is_kept(self):
        docs, rep = setup(); _, m, files, _ = run(docs, rep)
        u = U1; docs.version[u] = 2
        res, m2, _, tr = run(docs, make_report(docs), m, files, now="2026-11-02T09:00:00Z")
        self.assertEqual(status(res)["2026ENGG_CAP4_MH_CutOff.pdf"], "changed"); self.assertEqual(res["counts"]["unchanged"], 16)
        e = [x for x in m2["documents"].values() if x["url"] == u][0]; self.assertEqual(len(e["versions"]), 2); self.assertEqual(e["current_sha256"], e["versions"][1]["sha256"]); self.assertEqual(len(m2["files"]), 18)
        old = e["versions"][0]["sha256"]; self.assertTrue(os.path.exists(os.path.join(files, m2["files"][old]["asset_name"])))
        self.assertTrue(any(p.startswith("CHANGED:") for p in res["problems"])); self.assertEqual(len(body_gets(tr)), 1)
    def test_same_content_with_new_validators_is_not_a_change(self):
        docs, rep = setup(); _, m, files, _ = run(docs, rep)
        u = U1; docs.etag_override[u] = '"new-tag"'
        res, m2, _, _ = run(docs, make_report(docs), m, files)
        self.assertEqual(status(res)[u.rsplit("/", 1)[1]], "unchanged"); e = [x for x in m2["documents"].values() if x["url"] == u][0]; self.assertEqual(len(e["versions"]), 1); self.assertEqual(e["versions"][0]["etag"], '"new-tag"')
    def test_conditional_request_gets_304_when_discovery_has_no_validators(self):
        docs, rep = setup(); _, m, files, _ = run(docs, rep)
        r2 = copy.deepcopy(rep)
        for d in r2["documents"]: d["verification"].pop("etag", None); d["verification"].pop("last_modified", None)
        res, _, _, tr = run(docs, r2, m, files)
        self.assertEqual(res["counts"], {"unchanged": 17}); self.assertEqual(res["bytes_downloaded"], 0)
        self.assertTrue(all(h.get("If-None-Match") for m_, u, h in tr.calls if m_ == "GET" and u.endswith(".pdf")))
    def test_a_file_whose_earlier_upload_failed_is_fetched_again_so_it_can_be_stored(self):
        docs, rep = setup(); _, m, files, _ = run(docs, rep)                      # nothing marked uploaded; pretend a fresh computer has no local files
        res, m2, files2, tr = run(docs, rep, m, tmpdir()); self.assertEqual(len(body_gets(tr)), 17); self.assertEqual(res["counts"], {"unchanged": 17})
        self.assertEqual(len(os.listdir(files2)), 17)
        sha = next(iter(m["files"])); AR.confirm_uploads(m, list(m["files"])); res3, _, _, tr3 = run(docs, rep, m, tmpdir()); self.assertEqual(body_gets(tr3), [])      # uploaded files are not fetched again
    def test_identical_content_at_two_addresses_is_stored_once(self):
        docs, rep = setup(); a, b = U1, U2; docs.body_override[b] = docs.body(a)
        res, m, _, _ = run(docs, rep); self.assertEqual(len(m["files"]), 16)
        st = status(res); self.assertEqual(sorted([st[a.rsplit("/", 1)[1]], st[b.rsplit("/", 1)[1]]]), ["duplicate_content", "new"])      # whichever is read second is the duplicate
        sha = AR.sha256_bytes(docs.body(a)); self.assertEqual(sorted(m["files"][sha]["urls"]), sorted([a, b]))

class BadDownloads(unittest.TestCase):
    def check(self, res_for_url, want, note=None):
        docs, rep = setup(); u = U1; res, m, files, _ = run(docs, rep, extra={("GET", u): lambda m_, url, h: res_for_url(docs, u, h)})
        self.assertEqual(status(res)[u.rsplit("/", 1)[1]], "failed"); x = [r for r in res["results"] if r["url"] == u][0]
        if note: self.assertIn(note, x["note"])
        e = m["documents"][[k for k, v in m["documents"].items() if v["url"] == u][0]]; self.assertEqual(e["versions"], []); self.assertIsNone(e["current_sha256"]); self.assertEqual(e["last_result"], "failed")
        self.assertEqual(len(m["files"]), 16); self.assertEqual(len(os.listdir(files)), 16); self.assertEqual(len(res["required_missing"]), 1)
    def test_cut_off_download(self): self.check(lambda d, u, h: (200, d.headers(u), d.body(u)[:300]) if "Range" not in h else (206, {"Content-Range": "bytes 0-0/9", "Content-Length": "1"}, b"%"), "failed", "incomplete download")
    def test_web_page_instead_of_pdf(self): self.check(lambda d, u, h: (200, {"Content-Type": "text/html"}, b"<html>Service unavailable</html>") if "Range" not in h else (206, {}, b"%"), "failed", "web page")
    def test_wrong_signature(self): self.check(lambda d, u, h: (200, {"Content-Type": "application/pdf"}, b"GIF89a....") if "Range" not in h else (206, {}, b"%"), "failed", "not a PDF")
    def test_missing_end_marker(self): self.check(lambda d, u, h: (200, {"Content-Type": "application/pdf"}, b"%PDF-1.7\n" + b"y" * 5000) if "Range" not in h else (206, {}, b"%"), "failed", "cut off")
    def test_empty_response(self): self.check(lambda d, u, h: (200, {"Content-Type": "application/pdf"}, b"") if "Range" not in h else (206, {}, b"%"), "failed", "empty")
    def test_not_found(self): self.check(lambda d, u, h: (404, {}, b"") if "Range" not in h else (206, {}, b"%"), "failed", "HTTP 404")
    def test_server_trouble_is_retried_then_reported(self):
        docs, rep = setup(); u = U1; calls = []
        def g(m_, url, h):
            if "Range" in h: return (206, {}, b"%")
            calls.append(1); return (503, {}, b"")
        res, m, _, _ = run(docs, rep, extra={("GET", u): g}); self.assertEqual(len(calls), 3); self.assertEqual(status(res)[u.rsplit("/", 1)[1]], "failed")
    def test_a_failed_refresh_never_replaces_the_earlier_good_version(self):
        docs, rep = setup(); _, m, files, _ = run(docs, rep); u = U1; sha_before = [v for v in m["documents"].values() if v["url"] == u][0]["current_sha256"]
        docs.version[u] = 2
        res, m2, _, _ = run(docs, make_report(docs), m, files, extra={("GET", u): lambda m_, url, h: (200, {"Content-Type": "text/html"}, b"<html>error</html>") if "Range" not in h else (206, {}, b"%")})
        e = [v for v in m2["documents"].values() if v["url"] == u][0]; self.assertEqual(e["current_sha256"], sha_before); self.assertEqual(len(e["versions"]), 1); self.assertEqual(e["last_result"], "failed")
        self.assertEqual(res["required_missing"], [])                       # an older good copy exists, so nothing is 'missing'
    def test_robots_disallow_stops_downloads_from_that_host(self):
        docs, rep = setup(); res, m, _, tr = run(docs, rep, extra={("GET", "https://cappublicdocs2026.blob.core.windows.net/robots.txt"): (200, {}, b"User-agent: *\nDisallow: /documents\n")})
        blob = [x for x in res["results"] if "blob.core" in x["url"]]; self.assertTrue(blob); self.assertTrue(all(x["status"] == "failed" and "robots" in x["note"] for x in blob))
        self.assertFalse([u for u in body_gets(tr) if "blob.core" in u]); self.assertTrue(len(res["required_missing"]) >= len(blob))
    def test_file_size_limit(self):
        docs, rep = setup(); res, m, _, _ = run(docs, rep, policy={"max_file_bytes": 600}); self.assertEqual(res["counts"], {"failed": 17}); self.assertIn("larger than", res["results"][0]["note"])
    def test_total_download_limit(self):
        docs, rep = setup(); res, m, _, _ = run(docs, rep, policy={"max_total_bytes": 2000})
        self.assertGreater(res["counts"]["new"], 0); self.assertGreater(res["counts"]["skipped"], 0); self.assertEqual(len(res["required_missing"]), res["counts"]["skipped"])
    def test_request_budget_stops_cleanly(self):
        docs, rep = setup(); res, m, _, tr = run(docs, rep, max_requests=6)
        self.assertLessEqual(len(tr.calls), 6); self.assertTrue(any("budget" in p for p in res["problems"])); self.assertTrue(res["required_missing"])
    def test_one_bad_file_does_not_stop_the_others(self):
        docs, rep = setup(); u = U3; docs.status[u] = (404, {}, b""); res, m, _, _ = run(docs, rep)
        self.assertEqual(res["counts"], {"new": 16, "failed": 1})

class Content(unittest.TestCase):
    def test_check_content_rules(self):
        ok = b"%PDF-1.4\nabc\n%%EOF\n"; h = {"content-type": "application/pdf"}
        self.assertIsNone(DL.check_content("https://x.mahacet.org/a.pdf", ok, h)); self.assertIsNone(DL.check_content("https://x.mahacet.org/a.pdf", ok + b"\x00" * 20, h))     # trailing padding is fine
        self.assertIn("empty", DL.check_content("https://x.mahacet.org/a.pdf", b"", h)); self.assertIn("web page", DL.check_content("https://x.mahacet.org/a.pdf", b"  <!DOCTYPE html><html>", {}))
        self.assertIn("incomplete", DL.check_content("https://x.mahacet.org/a.pdf", ok, {"content-length": "999"})); self.assertIn("not a valid xlsx", DL.check_content("https://x.mahacet.org/a.xlsx", b"abc", {}))
        self.assertIsNone(DL.check_content("https://x.mahacet.org/a.xlsx", b"PK\x03\x04rest", {})); self.assertIn("not a valid xls", DL.check_content("https://x.mahacet.org/a.xls", b"abc", {}))
    def test_unchanged_rule_needs_a_matching_validator(self):
        e = {"current_sha256": "a", "versions": [{"sha256": "a", "size_bytes": 10, "etag": '"1"', "last_modified": None}]}
        self.assertTrue(DL.unchanged_since_archive(e, {"size_bytes": 10, "etag": '"1"'})); self.assertFalse(DL.unchanged_since_archive(e, {"size_bytes": 11, "etag": '"1"'}))
        self.assertFalse(DL.unchanged_since_archive(e, {"size_bytes": 10, "etag": '"2"'})); self.assertFalse(DL.unchanged_since_archive(e, {"size_bytes": 10}))          # size alone is not proof
        self.assertFalse(DL.unchanged_since_archive(None, {"size_bytes": 10, "etag": '"1"'})); self.assertFalse(DL.unchanged_since_archive(e, None))

class Manifest(unittest.TestCase):
    def test_manifest_is_deterministic_and_round_trips(self):
        docs, rep = setup(); _, m1, _, _ = run(docs, rep); _, m2, _, _ = run(docs, rep); d = tmpdir(); p1, p2 = os.path.join(d, "a.json"), os.path.join(d, "b.json")
        AR.save_manifest(p1, m1, NOW); AR.save_manifest(p2, m2, NOW); self.assertEqual(open(p1).read(), open(p2).read()); self.assertEqual(AR.load_manifest(p1), json.loads(open(p1).read()))
        self.assertEqual([f for f in os.listdir(d) if f.endswith(".tmp")], [])
    def test_missing_manifest_starts_empty_and_unknown_version_is_refused(self):
        d = tmpdir(); self.assertEqual(AR.load_manifest(os.path.join(d, "none.json"))["documents"], {})
        p = os.path.join(d, "x.json"); open(p, "w").write('{"schema_version": 99}'); self.assertRaises(ValueError, AR.load_manifest, p)
    def test_file_names_cannot_escape_or_confuse(self):
        for raw, want in [("../../etc/passwd", "passwd"), ("a b(c)#1.pdf", "a_b_c_1.pdf"), ("", "document"), ("..", "document"), ("C:\\x\\y.pdf", "y.pdf"), ("Ünï.pdf", "n_.pdf")]:
            self.assertEqual(AR.safe_name(raw), want, raw)
        self.assertLessEqual(len(AR.safe_name("a" * 500 + ".pdf")), 100)
    def test_upload_plan_confirm_and_verify(self):
        docs, rep = setup(); _, m, files, _ = run(docs, rep)
        plan = AR.plan_uploads(m, files); self.assertEqual(len(plan), 17); self.assertTrue(all(len(t) == 3 and t[0].startswith("raw-") for t in plan))
        self.assertEqual(AR.confirm_uploads(m, [plan[0][2], plan[1][2], "unknown-sha"], "2026-10-28T10:00:00Z"), 2); self.assertEqual(len(AR.plan_uploads(m, files)), 15)
        self.assertEqual(AR.confirm_uploads(m, [plan[0][2]]), 0)                                          # idempotent
        self.assertEqual(AR.plan_uploads(m, tmpdir()), [])                                                # files that are not on this computer are never planned
        self.assertEqual(AR.verify_store(m, files), (17, []))
        p = os.path.join(files, m["files"][plan[2][2]]["asset_name"]); open(p, "ab").write(b"tampered"); checked, problems = AR.verify_store(m, files)
        self.assertEqual(len(problems), 1); self.assertIn("mismatch", problems[0]); self.assertEqual(AR.verify_store(m, tmpdir()), (0, []))

class Cli(unittest.TestCase):
    def _run(self, docs, report, d, extra=None, argv=()):
        rp = os.path.join(d, "report.json"); open(rp, "w").write(json.dumps(report))
        orig = DL.PoliteFetcher; c = Clock(); tr = FakeTransport(routes(docs, extra)); DL.PoliteFetcher = lambda **kw: PoliteFetcher(tr, sleep=c.sleep, clock=c.now, **kw)
        try: return DL.main(["--report", rp, "--manifest", os.path.join(d, "m.json"), "--files", os.path.join(d, "files"), "--out", os.path.join(d, "out.json"), "--now", NOW] + list(argv))
        finally: DL.PoliteFetcher = orig
    def test_good_run_writes_manifest_report_and_files(self):
        d = tmpdir(); docs, rep = setup(); self.assertEqual(self._run(docs, rep, d), 0)
        self.assertEqual(len(AR.load_manifest(os.path.join(d, "m.json"))["files"]), 17); self.assertEqual(json.load(open(os.path.join(d, "out.json")))["counts"], {"new": 17}); self.assertEqual(len(os.listdir(os.path.join(d, "files"))), 17)
    def test_missing_needed_document_gives_exit_code_3_but_keeps_the_rest(self):
        d = tmpdir(); docs, rep = setup(); docs.status[U1] = (404, {}, b""); self.assertEqual(self._run(docs, rep, d), 3); self.assertEqual(len(AR.load_manifest(os.path.join(d, "m.json"))["files"]), 16)
    def test_no_discovery_report_gives_exit_code_2(self):
        self.assertEqual(DL.main(["--report", os.path.join(tmpdir(), "nope.json")]), 2)
    def test_run_page_summary_only_when_asked(self):
        d = tmpdir(); sm = os.path.join(d, "s.md"); os.environ["GITHUB_STEP_SUMMARY"] = sm; docs, rep = setup()
        try: self._run(docs, rep, d); self.assertFalse(os.path.exists(sm)); self._run(docs, rep, tmpdir(), argv=["--github-summary"]); self.assertIn("Document archive report", open(sm).read())
        finally: del os.environ["GITHUB_STEP_SUMMARY"]
    def test_archive_cli_commands(self):
        d = tmpdir(); docs, rep = setup(); self._run(docs, rep, d); m, f = os.path.join(d, "m.json"), os.path.join(d, "files")
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf): self.assertEqual(AR.main(["plan", "--manifest", m, "--files", f]), 0)
        lines = [l for l in buf.getvalue().splitlines() if l]; self.assertEqual(len(lines), 17); self.assertTrue(all(l.count("|") == 2 for l in lines))
        sh = os.path.join(d, "up.txt"); open(sh, "w").write("\n".join(l.split("|")[2] for l in lines[:5]) + "\n")
        with contextlib.redirect_stdout(io.StringIO()): AR.main(["confirm", "--manifest", m, "--shas", sh, "--now", NOW])
        self.assertEqual(sum(1 for x in AR.load_manifest(m)["files"].values() if x["uploaded"]), 5)
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(AR.main(["verify", "--manifest", m, "--files", f]), 0)
if __name__ == "__main__": unittest.main()
