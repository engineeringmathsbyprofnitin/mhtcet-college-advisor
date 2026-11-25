"""Stage 14b: the admission year changes on 1 January (calendar rule); cutoffs stay evidence-based; vacancy/fees follow the admission year."""
import csv, contextlib, io, json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import realpkg
from test_stage12a3 import setup, frow
from ingestion import plan as P, build_fees as BF, build_vacancy as BV, fra_fees as FF, package_real as PR
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ALL = ["I", "II", "III", "IV"]


def dec(today, cur="2026-27", rounds=ALL, status="confirmed"):
    return {"current_label": cur, "status": status, "current_cutoff_rounds": rounds, "today": today,
            "previous": [{"label": "2025-26", "cutoff_rounds": ALL}, {"label": "2024-25", "cutoff_rounds": ["I", "II", "III"]}, {"label": "2023-24", "cutoff_rounds": ["I", "II", "III"]}]}


class AdmissionYear(unittest.TestCase):
    def test_changes_on_1_january_but_cutoffs_stay(self):
        for today, adm, has in (("2026-11-24", "2026-27", True), ("2026-12-31", "2026-27", True), ("2027-01-01", "2027-28", False), ("2027-07-10", "2027-28", False)):
            p = P.make_plan(dec(today, status="previous_cycle_latest" if today >= "2027" else "confirmed"))
            self.assertEqual((p["admission_year"], p["admission_year_has_cutoffs"], p["cutoff_year"], p["current_year"]), (adm, has, "2026-27", "2026-27"), today)
            self.assertEqual(p["latest_round"], "IV"); self.assertEqual([h["label"] for h in p["history"]], ["2025-26", "2024-25", "2023-24"])

    def test_new_cutoffs_move_the_cutoff_year(self):
        p = P.make_plan(dec("2027-07-20", cur="2027-28", rounds=["I"]))
        self.assertEqual((p["admission_year"], p["cutoff_year"], p["admission_year_has_cutoffs"], p["next_round_expected"]), ("2027-28", "2027-28", True, "II"))

    def test_clock_behind_the_portal_never_goes_backwards_and_missing_date_falls_back(self):
        self.assertEqual(P.make_plan(dec("2025-03-01"))["admission_year"], "2026-27")
        d = dec("x"); self.assertEqual(P.make_plan(d)["admission_year"], "2026-27")
        d = dec(None); d.pop("today"); self.assertEqual(P.make_plan(d)["admission_year"], "2026-27")


class CalendarToday(unittest.TestCase):
    def test_the_day_the_plan_is_made_wins_over_the_day_of_the_last_discovery(self):
        d = dec("2026-12-28", status="confirmed"); d["calendar_today"] = "2027-01-02"
        self.assertEqual(P.make_plan(d)["admission_year"], "2027-28")
        d["calendar_today"] = "2026-12-31"; self.assertEqual(P.make_plan(d)["admission_year"], "2026-27")


class VacancyAndFees(unittest.TestCase):
    PLAN = dict(ok=True, current_year="2026-27", cutoff_year="2026-27", admission_year="2027-28")

    def test_old_year_vacancy_is_never_shown_for_the_new_year(self):
        tmp = tempfile.mkdtemp(); base = os.path.join(tmp, "n"); out = os.path.join(base, "tables"); os.makedirs(os.path.join(base, "vacancy")); os.makedirs(out)
        open(os.path.join(out, "vacancy.csv"), "w").write("stale\n")
        rep = BV.build(base=base, plan=self.PLAN, outdir=out)
        self.assertTrue(rep["ok"]); self.assertTrue(rep["status"].startswith("unavailable")); self.assertEqual(rep["year"], "2027-28")
        self.assertFalse(os.path.exists(os.path.join(out, "vacancy.csv")))

    def test_fees_fall_back_to_the_newest_list_and_are_labelled_with_their_year(self):
        base, man = setup([frow()])
        rep = BF.build(base=base, plan=self.PLAN, manual=man)
        self.assertTrue(rep["ok"], rep); self.assertEqual((rep["year"], rep["admission_year"]), ("2026-27", "2027-28")); self.assertTrue(any("2027-28" in n for n in rep["notes"]))
        rows = list(csv.DictReader(open(os.path.join(base, "tables", "fees.csv"), encoding="utf-8")))
        self.assertTrue(rows); self.assertEqual({r["academic_year"] for r in rows}, {"2026-27"})

    def test_fee_list_of_the_admission_year_wins_when_it_exists(self):
        base, man = setup([frow()])
        src = os.path.join(base, "fees", "fra_fees_2026-27_engg.csv"); dst = os.path.join(base, "fees", "fra_fees_2027-28_engg.csv")
        open(dst, "w", encoding="utf-8", newline="").write(open(src, encoding="utf-8", newline="").read())
        rep = BF.build(base=base, plan=self.PLAN, manual=man); self.assertEqual(rep["year"], "2027-28")
        rows = list(csv.DictReader(open(os.path.join(base, "tables", "fees.csv"), encoding="utf-8"))); self.assertEqual({r["academic_year"] for r in rows}, {"2027-28"})

    def test_fees_survive_when_the_cutoff_year_has_also_moved_to_the_new_year(self):
        # found by the Stage 14d-2 rehearsal: Round I of 2027-28 published, FRA list of 2027-28 not yet
        base, man = setup([frow()]); rep = BF.build(base=base, plan=dict(ok=True, current_year="2027-28", admission_year="2027-28"), manual=man)
        self.assertTrue(rep["ok"], rep); self.assertEqual((rep["year"], rep["admission_year"]), ("2026-27", "2027-28"))
        self.assertTrue(os.path.exists(os.path.join(base, "tables", "fees.csv")))

    def test_a_later_years_list_is_never_used_for_an_earlier_admission_year(self):
        base, man = setup([frow()]); src = os.path.join(base, "fees", "fra_fees_2026-27_engg.csv")
        os.rename(src, os.path.join(base, "fees", "fra_fees_2028-29_engg.csv"))
        rep = BF.build(base=base, plan=dict(ok=True, current_year="2026-27", admission_year="2026-27"), manual=man); self.assertTrue(rep["status"].startswith("unavailable"), rep["status"]); self.assertFalse(os.path.exists(os.path.join(base, "tables", "fees.csv")))

    def test_plans_without_the_new_field_behave_as_before(self):
        base, man = setup([frow()]); rep = BF.build(base=base, plan=dict(ok=True, current_year="2026-27"), manual=man)
        self.assertEqual((rep["year"], rep["admission_year"]), ("2026-27", "2026-27")); self.assertEqual(rep["notes"], [])


class FeeReaderYear(unittest.TestCase):
    def run_main(self, sites):
        tmp = tempfile.mkdtemp(); os.makedirs(os.path.join(tmp, "data", "normalized"))
        json.dump(dict(VacancyAndFees.PLAN), open(os.path.join(tmp, "data", "normalized", "data_plan.json"), "w"))
        seen = []

        def stub(site, year, fetcher, out_dir, raw_dir):
            seen.append(year); os.makedirs(out_dir, exist_ok=True); os.makedirs(raw_dir, exist_ok=True)
            json.dump({}, open(os.path.join(out_dir, "fra_fees_report.json"), "w"))
            return dict(ok=True, rows=1, requests=0, how="stub", statuses={}, warnings=[], skipped_rows=[], problems=[])
        class Nothing:                                   # Stage 14e: the address finder must never reach the network in a test
            def fetch(self, url, **kw):
                class R: blocked = ""; status = 404; ok = False; text = ""
                return R()
        old = (FF.ROOT, FF.read, dict(FF.FRA_SITES), FF.PoliteFetcher); FF.ROOT = tmp; FF.read = stub; FF.PoliteFetcher = lambda **kw: Nothing(); FF.FRA_SITES.clear(); FF.FRA_SITES.update(sites)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf): code = FF.main()
        finally:
            FF.ROOT, FF.read, FF.PoliteFetcher = old[0], old[1], old[3]; FF.FRA_SITES.clear(); FF.FRA_SITES.update(old[2])
        return code, seen, buf.getvalue()

    def test_unknown_new_year_keeps_reading_the_old_list_and_says_what_to_do(self):
        code, seen, out = self.run_main({"2026-27": "https://ay26-27.mahafraportal.org/x/"})
        self.assertEqual((code, seen), (0, ["2026-27"])); self.assertIn("ACTION NEEDED", out); self.assertIn("2027-28", out)

    def test_known_new_year_is_read(self):
        code, seen, out = self.run_main({"2026-27": "https://ay26-27.mahafraportal.org/x/", "2027-28": "https://ay27-28.mahafraportal.org/x/"})
        self.assertEqual((code, seen), (0, ["2027-28"])); self.assertNotIn("ACTION NEEDED", out)

    def test_new_year_current_cutoff_year_also_keeps_the_old_list(self):
        t = os.path  # plan whose cutoff year has moved on as well
        VacancyAndFees.PLAN, saved = dict(VacancyAndFees.PLAN, current_year="2027-28", cutoff_year="2027-28"), VacancyAndFees.PLAN
        try: code, seen, out = self.run_main({"2026-27": "https://ay26-27.mahafraportal.org/x/"})
        finally: VacancyAndFees.PLAN = saved
        self.assertEqual((code, seen), (0, ["2026-27"])); self.assertIn("ACTION NEEDED", out)

    def test_no_address_at_all_still_fails(self):
        code, seen, out = self.run_main({}); self.assertEqual((code, seen), (1, [])); self.assertIn("FAIL", out)


class Packaging(unittest.TestCase):
    def test_the_page_is_told_the_admission_year(self):
        t = realpkg.fresh_tables(); d = tempfile.mkdtemp(); PR.main(d, tables=t)
        base = [f for f in os.listdir(d) if f.startswith("base.") and f.endswith(".json")]; self.assertEqual(len(base), 1)
        text = open(os.path.join(d, base[0]), encoding="utf-8").read()
        self.assertRegex(text, r"rounds=[IV+]+;next=\w+;phase=\w+;admission=\d{4}-\d{2}")


if __name__ == "__main__":
    unittest.main()
