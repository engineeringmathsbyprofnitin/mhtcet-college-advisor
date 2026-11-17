import csv, json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ingestion import fra_fees as F
from ingestion.http_client import PoliteFetcher

SITE = F.FRA_SITES["2026-27"]
SUB = "<option value=''>Select  Sub Type</option><option value='BBA'>BBA - Bachelor of Business Administration</option><option value='ENGGWP'>ENGGWP - Bachelor of Engineering (Working Professional)</option><option value='ENGG'>ENGG - Bachelor of Engineering/Bachelor of Technology</option><option value='ME'>ME - Master of Engineering/Masters of Technology</option><option value='PHARM'>PHARM - Bachelor of Pharmacy</option>"
HEAD = "<tr><th>Sr. No.</th><th>Inst ID</th><th>Inst Name</th><th>District</th><th>Stream</th><th>Status</th><th>Date of Meeting</th><th>Tuition Fee</th><th>Development Fee</th><th>Total Fee</th></tr>"


def tr(sr, iid, name="VIDYALANKAR INSTITUTE OF TECHNOLOGY, WADALA, MUMBAI.", dist="Mumbai-City", stream="ENGG", status="Approved", date="15-06-2026", t="176521", d="26479", tot="203000"):
    return "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (sr, iid, name, dist, stream, status, date, t, d, tot)


def table(*rows, head=HEAD): return "<div><table>%s%s</table></div>" % (head, "".join(rows))


GOOD = table(tr(1, "EN3139"), tr(2, "EN3182", "THADOMAL SHAHANI ENGINEERING COLLEGE, BANDRA, MUMBAI", t="189034", d="26466", tot="215500", date="05-05-2026"),
             tr(3, "EN6283", "ANNASAHEB DANGE COLLEGE", "Sangli", status="No Upward Revision", t="90000", d="13000", tot="103000", date="01-01-2026"))
PAGE = "<html><select name='district' id='district'><option value=''>Select District</option><option value='all'>All District</option><option value='Mumbai-City'>Mumbai-City</option><option value='Sangli'>Sangli</option></select></html>"


class Fake:
    def __init__(self, report=GOOD, sub=SUB, robots=(404, b""), by_district=None, status=200):
        self.report, self.sub, self.robots, self.by_district, self.status, self.calls = report, sub, robots, by_district or {}, status, []
    def send(self, method, url, headers, max_bytes, data=None):
        self.calls.append(url)
        if url.endswith("/robots.txt"): return self.robots[0], {}, self.robots[1]
        if "get_sub_type_ajax" in url: return 200, {}, self.sub.encode()
        if "get_report_ajax" in url:
            for d, body in self.by_district.items():
                if "district=%s" % d in url: return 200, {}, body.encode()
            return self.status, {}, (self.report if "district=all" in url else "").encode()
        return 200, {}, PAGE.encode()


def go(fake):
    d = tempfile.mkdtemp(); f = PoliteFetcher(transport=fake, min_delay=0, sleep=lambda s: None, max_requests=80)
    rep = F.read(SITE, "2026-27", f, os.path.join(d, "o"), os.path.join(d, "raw"), today="2026-11-17")
    return rep, d


def rows(d): return list(csv.DictReader(open(os.path.join(d, "o", "fra_fees_2026-27_engg.csv"), encoding="utf-8")))


class Good(unittest.TestCase):
    def test_reads_and_writes(self):
        rep, d = go(Fake()); self.assertTrue(rep["ok"], rep["problems"]); self.assertEqual(rep["rows"], 3)
        r = rows(d); self.assertEqual((r[0]["inst_id"], r[0]["cet_institute_code"], r[0]["tuition_fee"], r[0]["development_fee"], r[0]["total_fee"], r[0]["meeting_date"]), ("EN3139", "03139", "176521", "26479", "203000", "2026-06-15"))
        self.assertEqual((r[2]["status"], r[2]["district"], r[2]["total_equals_parts"], r[2]["retrieved_date"]), ("No Upward Revision", "Sangli", "TRUE", "2026-11-17"))
        self.assertTrue(os.path.exists(os.path.join(d, "raw", "2026-27_engg_all.html"))); self.assertEqual(rep["statuses"], {"Approved": 2, "No Upward Revision": 1})

    def test_one_request_for_all_districts(self):
        fake = Fake(); go(fake); self.assertEqual(sum("get_report_ajax" in u for u in fake.calls), 1)

    def test_total_not_equal_parts_kept_as_printed_and_warned(self):
        rep, d = go(Fake(report=table(tr(1, "EN3139", tot="203500"))))
        self.assertTrue(rep["ok"]); self.assertEqual(rows(d)[0]["total_fee"], "203500"); self.assertEqual(rows(d)[0]["total_equals_parts"], "FALSE"); self.assertTrue(any("printed total" in w for w in rep["warnings"]))

    def test_missing_number_stays_empty_not_zero(self):
        rep, d = go(Fake(report=table(tr(1, "EN3139", t="-", d="", tot="203000"))))
        self.assertTrue(rep["ok"]); r = rows(d)[0]; self.assertEqual((r["tuition_fee"], r["development_fee"], r["total_equals_parts"]), ("", "", ""))

    def test_thousand_separators(self):
        rep, d = go(Fake(report=table(tr(1, "EN3139", t="1,76,521", d="26,479", tot="2,03,000")))); self.assertEqual(rows(d)[0]["total_fee"], "203000")

    def test_new_status_is_a_warning(self):
        rep, _ = go(Fake(report=table(tr(1, "EN3139", status="Under Review")))); self.assertTrue(rep["ok"]); self.assertTrue(any("new status" in w for w in rep["warnings"]))

    def test_extra_rows_are_reported_not_hidden(self):
        rep, _ = go(Fake(report=GOOD.replace("</table>", "<tr><td>Total institutes: 3</td></tr></table>"))); self.assertTrue(rep["ok"]); self.assertEqual(rep["skipped_rows"], ["Total institutes: 3"])

    def test_layout_table_around_is_ignored(self):
        rep, _ = go(Fake(report="<table><tr><td>" + GOOD + "</td></tr></table>")); self.assertTrue(rep["ok"], rep["problems"])


class OtherCodes(unittest.TestCase):
    def test_non_en_ids_are_kept_without_cet_code_and_warned(self):
        rep, d = go(Fake(report=table(tr(1, "EN3139"), tr(2, "AR3439", "SOME ARCHITECTURE COLLEGE"), tr(3, "MB5152", "SOME MBA INSTITUTE"))))
        self.assertTrue(rep["ok"], rep["problems"]); r = rows(d)
        self.assertEqual([(x["inst_id"], x["cet_institute_code"]) for x in r], [("EN3139", "03139"), ("AR3439", ""), ("MB5152", "")])
        self.assertEqual(sum("not an EN" in w for w in rep["warnings"]), 2)

    def test_interim_order_status_kept_as_printed(self):
        rep, d = go(Fake(report=table(tr(1, "EN4142", status="Interim Order of High Court"))))
        self.assertTrue(rep["ok"]); self.assertEqual(rows(d)[0]["status"], "Interim Order of High Court"); self.assertFalse(any("new status" in w for w in rep["warnings"]))


class Bad(unittest.TestCase):
    def fails(self, fake, text):
        rep, d = go(fake); self.assertFalse(rep["ok"]); self.assertTrue(any(text in p for p in rep["problems"]), rep["problems"])
        self.assertFalse(os.path.exists(os.path.join(d, "o", "fra_fees_2026-27_engg.csv"))); return rep

    def test_gap_in_serial_numbers(self): self.fails(Fake(report=table(tr(1, "EN3139"), tr(3, "EN3182"))), "Sr. No.")
    def test_other_stream(self): self.fails(Fake(report=table(tr(1, "EN3139", stream="PHARM"))), "not ENGG")
    def test_odd_institute_id(self): self.fails(Fake(report=table(tr(1, "XX12"))), "unexpected Inst ID")
    def test_lowercase_or_numeric_id(self): self.fails(Fake(report=table(tr(1, "en3139"))), "unexpected Inst ID")
    def test_same_institute_twice_with_different_numbers(self): self.fails(Fake(report=table(tr(1, "EN3139"), tr(2, "EN3139", tot="1"))), "twice with different")
    def test_unreadable_number(self): self.fails(Fake(report=table(tr(1, "EN3139", t="abc"))), "unreadable tuition_fee")
    def test_unreadable_date(self): self.fails(Fake(report=table(tr(1, "EN3139", date="soon"))), "unreadable meeting date")
    def test_header_missing_a_column(self): self.fails(Fake(report=table(tr(1, "EN3139"), head=HEAD.replace("<th>Tuition Fee</th>", ""))), "columns missing")
    def test_no_table(self): self.fails(Fake(report="<p>No data</p>", by_district={}), "no table")
    def test_no_rows_at_all(self): self.fails(Fake(report=table()), "no rows")
    def test_no_eng_subtype(self): self.fails(Fake(sub="<option value='P'>PHARM</option>"), "exactly one sub type")
    def test_two_eng_subtypes(self): self.fails(Fake(sub=SUB + "<option value='ENGG'>ENGG - copy</option>"), "exactly one sub type")
    def test_captcha(self): self.fails(Fake(report="<div>enter captcha</div>"), "CAPTCHA")
    def test_robots_disallow(self): self.fails(Fake(robots=(200, b"User-agent: *\nDisallow: /\n")), "not readable")
    def test_server_error(self): self.fails(Fake(status=500), "not readable")


class SubType(unittest.TestCase):
    def test_working_professional_and_masters_are_not_picked(self):
        fake = Fake(); rep, _ = go(fake); self.assertTrue(rep["ok"], rep["problems"])
        self.assertTrue(any("sub_type=ENGG&" in u for u in fake.calls)); self.assertFalse(any("ENGGWP" in u or "sub_type=ME&" in u for u in fake.calls if "get_report_ajax" in u))

    def test_code_must_match_exactly(self):
        rep, _ = go(Fake(sub="<option value='ENGGWP'>ENGGWP - Working Professional</option>")); self.assertFalse(rep["ok"])


class Main(unittest.TestCase):
    def test_unexpected_error_still_leaves_a_report(self):
        import io, contextlib
        orig = F.read; F.read = lambda *a, **k: 1 / 0
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf): code = F.main()
        finally: F.read = orig
        self.assertEqual(code, 1); self.assertIn("FAIL: unexpected error", buf.getvalue()); self.assertTrue(os.path.isdir(os.path.join(F.ROOT, "data", "normalized", "fees")))
        r = json.load(open(os.path.join(F.ROOT, "data", "raw", "fees", "fra_fees_report.json"))); self.assertIn("ZeroDivisionError", r["problems"][0])
        os.remove(os.path.join(F.ROOT, "data", "raw", "fees", "fra_fees_report.json"))
        for d in (("data", "raw", "fees"), ("data", "normalized", "fees")):
            try: os.rmdir(os.path.join(F.ROOT, *d))
            except OSError: pass


class Fallback(unittest.TestCase):
    def test_district_by_district_when_all_gives_nothing(self):
        by = {"Mumbai-City": table(tr(1, "EN3139"), tr(2, "EN3182")), "Sangli": table(tr(1, "EN6283", dist="Sangli"))}
        rep, d = go(Fake(report="<p></p>", by_district=by)); self.assertTrue(rep["ok"], rep["problems"]); self.assertEqual(rep["rows"], 3)
        self.assertIn("district by district", rep["how"]); self.assertEqual([r["inst_id"] for r in rows(d)], ["EN3139", "EN3182", "EN6283"])

    def test_fallback_district_without_colleges_is_fine(self):
        by = {"Mumbai-City": table(tr(1, "EN3139")), "Sangli": "<p>No Record Found</p>"}
        rep, _ = go(Fake(report="<p></p>", by_district=by)); self.assertTrue(rep["ok"], rep["problems"]); self.assertEqual(rep["rows"], 1)

    def test_fallback_removes_duplicate_institute(self):
        by = {"Mumbai-City": table(tr(1, "EN3139")), "Sangli": table(tr(1, "EN3139"))}
        rep, _ = go(Fake(report="<p></p>", by_district=by)); self.assertEqual(rep["rows"], 1)


class Helpers(unittest.TestCase):
    def test_options(self): self.assertEqual([o for o in F.sub_type_options(SUB) if o[0] == "ENGG"], [("ENGG", "ENGG - Bachelor of Engineering/Bachelor of Technology")])
    def test_money(self): self.assertEqual((F.money("1,23,000"), F.money(""), F.money("x")), ((123000, False), (None, False), (None, True)))
    def test_unknown_year_has_no_address(self): self.assertNotIn("2031-32", F.FRA_SITES)
    def test_site_is_official_host(self):
        from ingestion.http_client import host_allowed
        self.assertTrue(all(host_allowed(u.split("/")[2]) for u in F.FRA_SITES.values()))


if __name__ == "__main__":
    unittest.main()
