"""Stage 7 tests: the whole discovery run against a FAKE network built from fixtures modelled on the real portal.
Passing proves the logic; it does NOT prove the live CET Cell site behaves the same (the GitHub Action run does that)."""
import sys, os, json, tempfile, unittest, re
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ingestion import discover as D
from ingestion.http_client import PoliteFetcher, host_allowed
from stage7_helpers import *

TODAY = date(2026, 10, 26)
def run(routes=None, today=TODAY, **kw):
    clock = Clock(); tr = FakeTransport(routes if routes is not None else site())
    f = PoliteFetcher(tr, min_delay=kw.pop("delay", 1.0), max_requests=kw.pop("max_requests", 150), sleep=clock.sleep, clock=clock.now)
    rep = D.run_discovery(f, today, now="2026-10-26T09:00:00Z", **kw)
    return rep, tr, clock

class Happy(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.rep, cls.tr, cls.clock = run()
    def test_status_and_year(self):
        a = self.rep["admission_year"]; self.assertEqual(self.rep["status"], "ok"); self.assertEqual(a["current_label"], "2026-27"); self.assertEqual(a["status"], "confirmed")
        self.assertEqual(a["latest_cutoff_round"], "IV"); self.assertEqual(a["vacancy_round"], "IV")
    def test_menu_years_and_portal_found(self):
        self.assertEqual(list(self.rep["menu"]["cap_years"]), ["2026-27", "2025-26", "2024-25", "2023-24", "2022-23"])
        p = self.rep["portals"]["2026-27"]; self.assertEqual(p["portal_url"], FE26); self.assertEqual(p["found_by"], "link text 'B.E/ B.Tech'")
    def test_document_inventory(self):
        docs = self.rep["documents"]; by = lambda t: [d for d in docs if d["doc_type"] == t]
        self.assertEqual(len(docs), 41); self.assertEqual(len(by("cutoff")), 9 + 7 + 7 + 9); self.assertEqual(len(by("vacancy_position")), 4); self.assertEqual(len(by("vacancy_after_cap")), 1); self.assertEqual(len(by("seat_matrix")), 4)
    def test_matrix_matches_the_portal(self):
        m = self.rep["matrix"]
        self.assertEqual(m["2026-27"]["cutoff"]["MH"], ["I", "II", "III", "IV"]); self.assertEqual(m["2026-27"]["cutoff"]["AI"], ["I", "II", "III", "IV"]); self.assertEqual(m["2026-27"]["cutoff"]["DIPLOMA"], ["IV"])
        self.assertEqual(m["2025-26"]["cutoff"]["MH"], ["I", "II", "III", "IV"]); self.assertEqual(m["2024-25"]["cutoff"]["MH"], ["I", "II", "III"]); self.assertEqual(m["2023-24"]["cutoff"]["DIPLOMA"], ["III"])
        self.assertEqual(m["2026-27"]["vacancy_position"], ["II", "III", "IV"]); self.assertTrue(m["2026-27"]["vacancy_after_cap"]); self.assertTrue(m["2024-25"]["seat_matrix"])
    def test_previous_three_years_are_the_three_before_current(self):
        self.assertEqual([p["label"] for p in self.rep["admission_year"]["previous"]], ["2025-26", "2024-25", "2023-24"])
        self.assertTrue(all(p["has_cutoffs"] for p in self.rep["admission_year"]["previous"]))
    def test_selection_preview_follows_the_strict_rules(self):
        s = self.rep["selection_preview"]
        self.assertEqual(s["cutoff_documents"]["MH"]["round"], "IV"); self.assertTrue(s["cutoff_documents"]["MH"]["documents"][0]["url"].endswith("2026ENGG_CAP4_MH_CutOff.pdf"))
        self.assertEqual([d["url"].rsplit("/", 1)[1] for d in s["vacancy_documents"]], ["FE2026_Vacancy_For_CAP4.pdf"])      # not the ACAP list, not the court-order list, not the seat matrix
    def test_notes_tell_the_owner_about_the_look_alike_documents(self):
        t = " ".join(self.rep["notes"]); self.assertIn("ACAP", t); self.assertIn("Supplementary", t); self.assertIn("Diploma", t)
    def test_files_are_checked_for_reachability_but_not_downloaded(self):
        self.assertTrue(all(c[0] in ("GET", "HEAD") for c in self.tr.calls))
        for m, u, h in self.tr.calls:                                        # a file is only ever probed: HEAD, or a GET asking for the first byte
            if u.endswith(".pdf") and m == "GET": self.assertEqual(h.get("Range"), "bytes=0-0", u)
        d = self.rep["documents"][0]; self.assertTrue(d["verification"]["reachable"]); self.assertEqual(d["verification"]["content_type"], "application/pdf"); self.assertEqual(d["verification"]["etag"], '"abc"')
    def test_only_discovered_official_addresses_were_requested(self):
        found = {d["url"] for d in self.rep["documents"]} | {HOME, CAP26, FE26}
        for m, u, h in self.tr.calls:
            if u.endswith("/robots.txt"): continue
            self.assertIn(u, found, u); self.assertTrue(host_allowed(re.match(r"https?://([^/]+)", u).group(1)))
        asked = " ".join(self.tr.urls()); 
        for bad in ("maharashtracet.org", "mafahrportal", "mahafraportal", "cutoff-explorer", "youtu"): self.assertNotIn(bad, asked)
    def test_older_cap_pages_are_not_fetched_when_the_current_portal_already_lists_them(self):
        self.assertNotIn("https://cetcell.mahacet.org/cap-_2025-26/", self.tr.urls())
    def test_polite_pacing_and_identification(self):
        by_host = {}
        for e in self.rep["request_log"]: pass
        self.assertGreaterEqual(len(self.clock.sleeps), 1); self.assertTrue(all(s >= 0 for s in self.clock.sleeps))
        self.assertTrue(all("MHTCETCollegeAdvisorBot" in h["User-Agent"] for m, u, h in self.tr.calls)); self.assertEqual(self.rep["requests_made"], len(self.tr.calls))
    def test_request_count_is_modest(self):
        self.assertLess(self.rep["requests_made"], 90, self.rep["requests_made"])
    def test_report_is_plain_json(self):
        json.dumps(self.rep); self.assertTrue(D.render_markdown(self.rep).startswith("## Source discovery report"))

class Pacing(unittest.TestCase):
    def test_same_host_requests_are_spaced_by_the_delay(self):
        clock = Clock(); stamps = []
        tr = FakeTransport(site()); orig = tr.send
        def spy(m, u, h, mb): stamps.append((re.match(r"https?://([^/]+)", u).group(1), clock.now())); return orig(m, u, h, mb)
        tr.send = spy; f = PoliteFetcher(tr, min_delay=1.5, sleep=clock.sleep, clock=clock.now); D.run_discovery(f, TODAY, now="x")
        last = {}
        for host, t in stamps:
            if host in last: self.assertGreaterEqual(t - last[host], 1.5 - 1e-9, host)
            last[host] = t

class Walls(unittest.TestCase):
    def test_robots_txt_disallow_is_obeyed(self):
        rep, tr, _ = run(site({("GET", "https://fe2026.mahacet.org/robots.txt"): (200, {}, b"User-agent: *\nDisallow: /StaticPages\n")}))
        self.assertNotIn(FE26, tr.urls("GET")); self.assertEqual(rep["status"], "failed"); self.assertTrue(any(o["kind"] == "robots_disallow_or_unreadable" for o in rep["obstacles"]))
        self.assertEqual(rep["robots"]["fe2026.mahacet.org"], "rules")
    def test_unreadable_robots_means_do_not_crawl_that_host(self):
        rep, tr, _ = run(site({("GET", "https://fe2026.mahacet.org/robots.txt"): (503, {}, b"")}))
        self.assertNotIn(FE26, tr.urls("GET")); self.assertEqual(rep["robots"]["fe2026.mahacet.org"], "unreadable"); self.assertEqual(rep["status"], "failed")
    def test_missing_robots_means_allowed(self):
        rep, tr, _ = run(); self.assertEqual(rep["robots"]["cetcell.mahacet.org"], "allowed_all")
    def test_captcha_page_stops_and_is_reported(self):
        rep, tr, _ = run(site({("GET", FE26): html(fixture("captcha.html"))}))
        self.assertTrue(any(o["kind"] == "captcha" for o in rep["obstacles"])); self.assertEqual(rep["status"], "failed"); self.assertEqual(rep["documents"], [])
        self.assertEqual(tr.urls("GET").count(FE26), 1)                      # no retry loop against a CAPTCHA
    def test_password_protected_page_is_reported_not_bypassed(self):
        rep, tr, _ = run(site({("GET", CAP26): html(fixture("password.html"))}))
        self.assertTrue(any(o["kind"] == "password_protected" for o in rep["obstacles"])); self.assertFalse([m for m, u, h in tr.calls if m == "POST"])
    def test_forbidden_is_not_retried(self):
        rep, tr, _ = run(site({("GET", FE26): (403, {}, b"denied")}))
        self.assertEqual(tr.urls("GET").count(FE26), 1); self.assertTrue(any(o["kind"] == "forbidden" for o in rep["obstacles"]))
    def test_temporary_errors_are_retried_at_most_twice(self):
        rep, tr, clock = run(site({("GET", FE26): (503, {"Retry-After": "3"}, b"")}))
        self.assertEqual(tr.urls("GET").count(FE26), 3); self.assertIn(3.0, clock.sleeps); self.assertTrue(any(o["kind"] == "http_error" for o in rep["obstacles"]))
    def test_network_errors_are_retried_then_reported(self):
        rep, tr, _ = run(site({("GET", FE26): TimeoutError("timed out")})); self.assertEqual(tr.urls("GET").count(FE26), 3); self.assertTrue(any(o["kind"] == "network_error" for o in rep["obstacles"]))
    def test_redirect_to_a_login_server_is_not_followed(self):
        rep, tr, _ = run(site({("GET", FE26): (302, {"Location": "https://auth.maharashtracet.org/login"}, b"")}))
        self.assertFalse([u for u in tr.urls() if "auth.maharashtracet" in u]); self.assertTrue(any(o["kind"] == "host_not_allowed" for o in rep["obstacles"]))
    def test_redirect_inside_allowed_hosts_is_followed(self):
        rep, tr, _ = run(site({("GET", FE26): (301, {"Location": "https://fe2026.mahacet.org/StaticPages/HomePage2"}, b""), ("GET", "https://fe2026.mahacet.org/StaticPages/HomePage2"): html(fixture("fe2026_home.html"))}))
        self.assertEqual(rep["status"], "ok")
    def test_request_budget_is_a_hard_limit(self):
        rep, tr, _ = run(max_requests=6); self.assertLessEqual(len(tr.calls), 6); self.assertTrue(any(o["kind"] == "request_budget_exhausted" for o in rep["obstacles"]))
    def test_home_page_down_gives_failed_report_and_unknown_year(self):
        rep, _, _ = run(site({("GET", HOME): (500, {}, b"")})); self.assertEqual(rep["status"], "failed"); self.assertIsNone(rep["admission_year"]["current_start_year"])
    def test_layout_change_is_detected(self):
        rep, _, _ = run(site({("GET", HOME): html("<html><body><a href='/x'>nothing useful</a></body></html>")}))
        self.assertEqual(rep["status"], "failed"); self.assertTrue(any(o["kind"] == "layout_changed" for o in rep["obstacles"]))
    def test_menu_moved_falls_back_with_a_warning(self):
        h = fixture("cetcell_home.html").replace(">CAP<", ">Admissions<")
        rep, _, _ = run(site({("GET", HOME): html(h)}))
        self.assertTrue(any("not found in its usual place" in w for w in rep["warnings"]))

class Reachability(unittest.TestCase):
    def test_head_refused_falls_back_to_one_byte_request(self):
        u = "https://cappublicdocs2026.blob.core.windows.net/documents/2026ENGG_CAP4_MH_CutOff.pdf"
        rep, tr, _ = run(site({("HEAD", u): (405, {}, b""), ("GET", u): (206, {"Content-Type": "application/pdf"}, b"%")}))
        d = [x for x in rep["documents"] if x["url"] == u][0]; self.assertTrue(d["verification"]["reachable"])
        g = [h for m, uu, h in tr.calls if m == "GET" and uu == u]; self.assertEqual(g[0].get("Range"), "bytes=0-0")
    def test_a_link_that_does_not_open_is_marked_unreachable(self):
        u = "https://cappublicdocs2026.blob.core.windows.net/documents/2026ENGG_CAP4_MH_CutOff.pdf"
        rep, _, _ = run(site({("HEAD", u): (404, {}, b""), ("GET", u): (404, {}, b"")}))
        d = [x for x in rep["documents"] if x["url"] == u][0]; self.assertFalse(d["verification"]["reachable"])
    def test_if_every_current_cutoff_is_unreachable_the_year_is_not_adopted(self):
        routes = site()
        for k in list(routes):
            if k[0] == "HEAD" and "2026ENGG_" in k[1]: routes[k] = (404, {}, b""); routes[("GET", k[1])] = (404, {}, b"")
        rep, _, _ = run(routes); a = rep["admission_year"]
        self.assertEqual(a["current_label"], "2025-26"); self.assertEqual(a["status"], "newer_documents_unreachable"); self.assertTrue(any("could not be opened" in w for w in a["warnings"]))
    def test_server_that_wrongly_says_404_to_HEAD_is_handled_and_remembered(self):
        # this is what the real fe2026.mahacet.org did on the first live run: HEAD 404, normal request fine
        rep, tr, _ = run()
        old = [d for d in rep["documents"] if d["year_label"] in ("2023-24", "2024-25", "2025-26")]
        self.assertEqual(len(old), 26); self.assertTrue(all(d["verification"]["reachable"] for d in old))
        heads = [u for m, u, h in tr.calls if m == "HEAD" and "://fe2026.mahacet.org/" in u]; self.assertEqual(len(heads), 1)      # learned after the first one
        self.assertEqual(rep["admission_year"]["warnings"], []); self.assertTrue(all(p["has_cutoffs"] for p in rep["admission_year"]["previous"]))
    def test_server_trouble_is_unknown_not_unreachable(self):
        u = "https://cappublicdocs2026.blob.core.windows.net/documents/2026ENGG_CAP4_MH_CutOff.pdf"
        rep, tr, _ = run(site({("HEAD", u): (503, {}, b"")}))
        d = [x for x in rep["documents"] if x["url"] == u][0]; self.assertIsNone(d["verification"]["reachable"])
        self.assertEqual(rep["matrix"]["2026-27"]["cutoff"]["MH"], ["I", "II", "III", "IV"])          # unknown still counts; only 'does not open' is dropped
        self.assertEqual([x for x in tr.calls if x[0] == "GET" and x[1] == u], [])                    # no guessing with extra requests on server trouble
    def test_listed_files_that_do_not_open_are_replaced_by_the_years_own_pages(self):
        routes = site()
        for k in list(routes):
            if "fe2026.mahacet.org/2023/" in k[1]: routes[k] = (404, {}, b"")
        cap23 = '<html><body><h2>Under Graduate Courses</h2><ul><li><a href="https://fe2023.mahacet.org/StaticPages/HomePage">B.E/ B.Tech</a></li></ul></body></html>'
        fe23 = '<html><body><ul>' + "".join('<li><a href="https://cappublicdocs2023.blob.core.windows.net/documents/2023ENGG_CAP%d_MH_CutOff.pdf">CAP Round %s MH Cut Off</a></li>' % (n, r) for n, r in ((1, "I"), (2, "II"), (3, "III"))) + '</ul></body></html>'
        routes[("GET", "https://cetcell.mahacet.org/admissions/")] = html(cap23); routes[("GET", "https://fe2023.mahacet.org/StaticPages/HomePage")] = html(fe23)
        for n in (1, 2, 3): routes[("HEAD", "https://cappublicdocs2023.blob.core.windows.net/documents/2023ENGG_CAP%d_MH_CutOff.pdf" % n)] = PDF
        rep, tr, _ = run(routes)
        self.assertIn("2023-24", rep["portals"]); self.assertEqual(rep["matrix"]["2023-24"]["cutoff"], {"MH": ["I", "II", "III"]})   # only the files that open are counted
        self.assertTrue(rep["admission_year"]["previous"][2]["has_cutoffs"]); self.assertEqual(rep["status"], "ok")
    def test_no_verify_option_makes_no_head_requests(self):
        rep, tr, _ = run(verify=False); self.assertEqual(tr.urls("HEAD"), []); self.assertIsNone(rep["documents"][0]["verification"])

class Seasons(unittest.TestCase):
    def test_between_cycles_the_year_is_kept_and_flagged(self):
        rep, _, _ = run(today=date(2027, 2, 1)); a = rep["admission_year"]; self.assertEqual(a["current_label"], "2026-27"); self.assertEqual(a["status"], "previous_cycle_latest"); self.assertEqual(rep["status"], "ok")
    def test_vacancy_falls_back_to_round_iii_then_to_nothing(self):
        for drop, want in ((["FE2026_Vacancy_For_CAP4.pdf"], "III"), (["FE2026_Vacancy_For_CAP4.pdf", "FE2026_Vacancy_For_CAP3.pdf"], None)):
            h = fixture("fe2026_home.html")
            for n in drop: h = re.sub(r'<li><a href="[^"]*%s">.*?</a></li>\n' % n, "", h)
            rep, _, _ = run(site({("GET", FE26): html(h)})); self.assertEqual(rep["admission_year"]["vacancy_round"], want, drop)
            if want is None:                                              # Round II vacancy exists but must NOT be substituted
                self.assertEqual(rep["selection_preview"]["vacancy_documents"], []); self.assertTrue(any("vacancy will show as unavailable" in w for w in rep["admission_year"]["warnings"]))
    def test_missing_previous_year_triggers_a_fetch_of_that_years_own_pages(self):
        h = re.sub(r"<tr><td>2023-24</td>.*?</tr>\n", "", fixture("fe2026_home.html"), flags=re.S)
        cap23 = '<html><body><h2>Under Graduate Courses</h2><ul><li><a href="https://fe2023.mahacet.org/StaticPages/HomePage">B.E/ B.Tech</a></li></ul></body></html>'
        fe23 = '<html><body><ul><li><a href="https://fe2023.mahacet.org/2023/2023ENGG_CAP1_CutOff.pdf">CAP Round I MH Cut Off</a></li><li><a href="https://fe2023.mahacet.org/2023/2023ENGG_CAP3_CutOff.pdf">CAP Round III MH Cut Off</a></li></ul></body></html>'
        routes = site({("GET", FE26): html(h), ("GET", "https://cetcell.mahacet.org/admissions/"): html(cap23), ("GET", "https://fe2023.mahacet.org/StaticPages/HomePage"): html(fe23),
                         ("HEAD", "https://fe2023.mahacet.org/2023/2023ENGG_CAP1_CutOff.pdf"): PDF, ("HEAD", "https://fe2023.mahacet.org/2023/2023ENGG_CAP3_CutOff.pdf"): PDF})
        rep, tr, _ = run(routes); self.assertIn("2023-24", rep["portals"]); self.assertEqual(rep["matrix"]["2023-24"]["cutoff"]["MH"], ["I", "III"]); self.assertTrue(rep["admission_year"]["previous"][2]["has_cutoffs"])
        self.assertNotIn("https://cetcell.mahacet.org/cap-_2025-26/", tr.urls())          # only the missing year was chased

class Cli(unittest.TestCase):
    def _main(self, routes, out, today="2026-10-26"):
        clock = Clock(); tr = FakeTransport(routes)
        orig = D.PoliteFetcher; D.PoliteFetcher = lambda **kw: PoliteFetcher(tr, sleep=clock.sleep, clock=clock.now, **kw)
        try: return D.main(["--out", out, "--today", today])
        finally: D.PoliteFetcher = orig
    def test_good_run_writes_latest_and_dated_report(self):
        out = tempfile.mkdtemp(); self.assertEqual(self._main(site(), out), 0)
        self.assertEqual(sorted(os.listdir(out)), ["2026-10-26.json", "latest.json"]); self.assertEqual(json.load(open(os.path.join(out, "latest.json")))["admission_year"]["current_label"], "2026-27")
    def test_failed_run_keeps_the_last_good_report(self):
        out = tempfile.mkdtemp(); self._main(site(), out); before = open(os.path.join(out, "latest.json")).read()
        self.assertEqual(self._main(site({("GET", HOME): (500, {}, b"")}), out, "2026-10-27"), 2)
        self.assertEqual(open(os.path.join(out, "latest.json")).read(), before); self.assertTrue(os.path.exists(os.path.join(out, "last_failed.json"))); self.assertFalse(os.path.exists(os.path.join(out, "2026-10-27.json")))
    def test_github_step_summary_is_written_when_available(self):
        out = tempfile.mkdtemp(); sm = os.path.join(out, "summary.md"); os.environ["GITHUB_STEP_SUMMARY"] = sm
        try: self._main(site(), out)
        finally: del os.environ["GITHUB_STEP_SUMMARY"]
        self.assertIn("Current admission year:** 2026-27", open(sm).read())
if __name__ == "__main__": unittest.main()
