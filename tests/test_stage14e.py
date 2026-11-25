"""Stage 14e: the robot looks for the FRA portal of a new year itself (stub fetcher, no network)."""
import io, contextlib, json, os, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ingestion import fra_fees as FF
from ingestion.http_client import host_allowed
OLD = "https://ay26-27.mahafraportal.org/ssi_prp_25/"
OK_LIST = "<option value=''>--Select--</option><option value='ENGG'>ENGG - Bachelor of Engineering/Bachelor of Technology</option><option value='ENGGWP'>ENGGWP - Working Professional</option>"


class R:
    def __init__(self, status=200, text="", blocked=""): self.status, self.text, self.blocked = status, text, blocked; self.ok = (status == 200 and not blocked)


class Fake:
    def __init__(self, answers): self.answers, self.calls = answers, []
    def fetch(self, url, **kw):
        self.calls.append(url)
        for prefix, r in self.answers.items():
            if url.startswith(prefix):
                if isinstance(r, Exception): raise r
                return r
        return R(404)


class Candidates(unittest.TestCase):
    def test_host_follows_the_year_and_folder_numbers_count_up_from_the_newest_known(self):
        self.assertEqual(FF.candidate_sites("2027-28", {"2026-27": OLD}), ["https://ay27-28.mahafraportal.org/ssi_prp_%d/" % n for n in (25, 26, 27)])
        self.assertEqual(FF.candidate_sites("2028-29", {"2026-27": OLD, "2027-28": "https://ay27-28.mahafraportal.org/ssi_prp_26/"})[0], "https://ay28-29.mahafraportal.org/ssi_prp_26/")

    def test_no_candidates_for_a_known_or_older_year_or_without_a_known_address(self):
        self.assertEqual(FF.candidate_sites("2026-27", {"2026-27": OLD}), []); self.assertEqual(FF.candidate_sites("2027-28", {}), []); self.assertEqual(FF.candidate_sites("garbage", {"2026-27": OLD}), [])

    def test_every_candidate_is_on_an_official_host(self):
        for u in FF.candidate_sites("2027-28", {"2026-27": OLD}): self.assertTrue(host_allowed(u.split("/")[2]), u)


class Find(unittest.TestCase):
    def find(self, answers):
        f = Fake(answers); logs = []; r = FF.find_site("2027-28", {"2026-27": OLD}, f, log=logs.append); return r, f.calls, logs

    def test_the_first_candidate_that_answers_with_the_expected_list_is_taken(self):
        r, calls, logs = self.find({"https://ay27-28.mahafraportal.org/ssi_prp_26/": R(200, OK_LIST)})
        self.assertEqual(r, "https://ay27-28.mahafraportal.org/ssi_prp_26/"); self.assertEqual(len(calls), 2); self.assertTrue(any("FOUND" in l for l in logs))
        self.assertTrue(all(c.endswith("admin/reports/ajax/get_sub_type_ajax.php?val1=HT") for c in calls))      # one cheap request per candidate

    def test_an_answer_that_is_not_the_fee_portal_is_refused(self):
        r, calls, logs = self.find({"https://ay27-28": R(200, "<html>welcome</html>")}); self.assertIsNone(r); self.assertEqual(len(calls), 3)
        r, _, _ = self.find({"https://ay27-28": R(200, "<option value='ENGGWP'>ENGGWP - Working Professional</option>")}); self.assertIsNone(r)
        r, _, _ = self.find({"https://ay27-28": R(200, OK_LIST + OK_LIST)}); self.assertIsNone(r)          # two ENGG options: not trusted

    def test_nothing_published_yet_or_unreachable_host_gives_none_without_error(self):
        r, calls, _ = self.find({}); self.assertIsNone(r); self.assertEqual(len(calls), 3)
        r, calls, _ = self.find({"https://ay27-28": OSError("dns")}); self.assertIsNone(r); self.assertEqual(len(calls), 3)

    def test_walls_stop_the_search_and_are_never_bypassed(self):
        for resp in (R(403), R(429), R(401), R(0, "", "robots_disallow_or_unreadable")):
            r, calls, _ = self.find({"https://ay27-28": resp}); self.assertIsNone(r); self.assertEqual(len(calls), 1, resp.status)


class Persist(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(); self.root = FF.ROOT; FF.ROOT = self.tmp
    def tearDown(self): FF.ROOT = self.root; shutil.rmtree(self.tmp)

    def test_found_address_is_saved_and_known_afterwards(self):
        FF.save_found("2027-28", "https://ay27-28.mahafraportal.org/ssi_prp_26/")
        k = FF.known_sites(); self.assertEqual(k["2027-28"], "https://ay27-28.mahafraportal.org/ssi_prp_26/"); self.assertEqual(k["2026-27"], OLD)

    def test_malformed_or_foreign_entries_in_the_file_are_ignored(self):
        os.makedirs(os.path.dirname(FF.found_path()))
        json.dump({"2027-28": "https://evil.example.com/ssi_prp_26/", "bad": OLD, "2028-29": "http://ay28-29.mahafraportal.org/ssi_prp_26/", "2029-30": 5}, open(FF.found_path(), "w"))
        self.assertEqual(FF.known_sites(), dict(FF.FRA_SITES))
        open(FF.found_path(), "w").write("{not json"); self.assertEqual(FF.known_sites(), dict(FF.FRA_SITES))

    def test_package_uses_the_found_address_for_the_source_link(self):
        from ingestion import package_real as PR
        FF.save_found("2027-28", "https://ay27-28.mahafraportal.org/ssi_prp_26/")
        self.assertEqual(PR._fra_url("2027-28"), "https://ay27-28.mahafraportal.org/ssi_prp_26/outer.php?q=fee_search_report")


class MainFlow(unittest.TestCase):
    def run_main(self, fetcher):
        tmp = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, tmp); os.makedirs(os.path.join(tmp, "data", "normalized"))
        json.dump(dict(ok=True, current_year="2026-27", cutoff_year="2026-27", admission_year="2027-28"), open(os.path.join(tmp, "data", "normalized", "data_plan.json"), "w"))
        seen = []

        def stub(site, year, f, out_dir, raw_dir):
            seen.append((site, year)); os.makedirs(out_dir, exist_ok=True); os.makedirs(raw_dir, exist_ok=True); json.dump({}, open(os.path.join(out_dir, "fra_fees_report.json"), "w"))
            return dict(ok=True, rows=1, requests=0, how="stub", statuses={}, warnings=[], skipped_rows=[], problems=[])
        old = (FF.ROOT, FF.read, FF.PoliteFetcher); FF.ROOT = tmp; FF.read = stub; FF.PoliteFetcher = lambda **kw: fetcher
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf): code = FF.main()
        finally: FF.ROOT, FF.read, FF.PoliteFetcher = old
        return code, seen, buf.getvalue(), tmp

    def test_found_portal_is_used_and_remembered_without_any_action_by_the_owner(self):
        code, seen, out, tmp = self.run_main(Fake({"https://ay27-28.mahafraportal.org/ssi_prp_26/": R(200, OK_LIST)}))
        self.assertEqual((code, seen), (0, [("https://ay27-28.mahafraportal.org/ssi_prp_26/", "2027-28")])); self.assertIn("FOUND", out); self.assertNotIn("ACTION NEEDED", out)
        self.assertEqual(json.load(open(os.path.join(tmp, "data", "raw", "fees", "fra_sites_found.json"))), {"2027-28": "https://ay27-28.mahafraportal.org/ssi_prp_26/"})

    def test_not_found_keeps_the_old_list_says_what_to_do_and_is_not_red(self):
        code, seen, out, tmp = self.run_main(Fake({}))
        self.assertEqual((code, seen), (0, [(OLD, "2026-27")])); self.assertIn("ACTION NEEDED", out); self.assertFalse(os.path.exists(os.path.join(tmp, "data", "raw", "fees", "fra_sites_found.json")))

    def test_a_wall_means_no_bypass_and_no_save(self):
        code, seen, out, tmp = self.run_main(Fake({"https://ay27-28": R(403)}))
        self.assertEqual(seen, [(OLD, "2026-27")]); self.assertIn("a wall", out)


if __name__ == "__main__":
    unittest.main()
