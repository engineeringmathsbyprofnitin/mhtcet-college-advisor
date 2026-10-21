"""Stage 3 tests (use SYNTHETIC data only; they prove the schema/validator work, NOT that real CET Cell data is handled).
Run from the repository root:  python -m unittest tests/test_stage3_schema.py -v"""
import csv, os, shutil, sys, tempfile, unittest, json
ROOT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")
sys.path.insert(0,os.path.join(ROOT,"database"))
import validate_data as V
SYN=os.path.join(ROOT,"data","synthetic")

def mutate(table, fn):
    d=tempfile.mkdtemp(); shutil.rmtree(d); shutil.copytree(SYN,d)
    p=os.path.join(d,table+".csv")
    rows=list(csv.DictReader(open(p,newline=""))); hdr=list(rows[0].keys()) if rows else None
    fn(rows)
    with open(p,"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=hdr); w.writeheader(); w.writerows(rows)
    return d
def codes(d): return {e[2] for e in V.validate(d)}

class T(unittest.TestCase):
    def test_synthetic_is_clean(self): self.assertEqual(V.validate(SYN),[])
    def test_all_synthetic_flag(self):
        for t,sp in V.SCHEMA.items():
            if "is_synthetic" not in [c["name"] for c in sp["columns"]]: continue   # seat_types is a reference list
            for r in csv.DictReader(open(os.path.join(SYN,t+".csv"))): self.assertEqual(r["is_synthetic"],"TRUE")
    def test_templates_match_schema(self):
        for t,s in V.SCHEMA.items():
            hdr=next(csv.reader(open(os.path.join(ROOT,"database","templates",t+".csv"))))
            self.assertEqual(hdr,[c["name"] for c in s["columns"]])
    def test_bad_percentile(self):
        d=mutate("historical_cutoffs",lambda r:r[0].update(cutoff_percentile="101")); self.assertIn("PERCENTILE_RANGE",codes(d))
    def test_vacancy_round_I_rejected(self):
        d=mutate("vacancies",lambda r:r[0].update(cap_round="I")); self.assertIn("BAD_ENUM",codes(d))
    def test_seat_matrix_as_vacancy_source_rejected(self):
        d=mutate("vacancies",lambda r:r[0].update(source_doc_id="SYN-DOC-009")); self.assertIn("VACANCY_BAD_SOURCE",codes(d))
    def test_vacancy_exceeding_intake_rejected(self):
        d=mutate("vacancies",lambda r:r[0].update(vacancy_count="9999")); self.assertIn("VACANCY_EXCEEDS_INTAKE",codes(d))
    def test_negative_vacancy_rejected(self):
        d=mutate("vacancies",lambda r:r[0].update(vacancy_count="-3")); self.assertIn("BAD_TYPE",codes(d))
    def test_duplicate_cutoff_rejected(self):
        d=mutate("historical_cutoffs",lambda r:r.append(dict(r[0],cutoff_id="DUPX"))); self.assertIn("DUP_UNIQUE",codes(d))
    def test_duplicate_pk_rejected(self):
        d=mutate("colleges",lambda r:r.append(dict(r[0]))); self.assertIn("DUP_PK",codes(d))
    def test_unknown_college_rejected(self):
        d=mutate("branches",lambda r:r[0].update(college_code="NOPE")); self.assertIn("FK_MISSING",codes(d))
    def test_missing_required(self):
        d=mutate("colleges",lambda r:r[0].update(district="")); self.assertIn("MISSING_REQUIRED",codes(d))
    def test_unlabelled_estimate_rejected(self):
        d=mutate("quality_indicators",lambda r:r[0].update(is_estimate="FALSE")); self.assertIn("ESTIMATE_FLAG",codes(d))
    def test_accreditation_date_order(self):
        d=mutate("accreditation",lambda r:r[0].update(valid_from="2030-01-01",valid_to="2020-01-01")); self.assertIn("DATE_ORDER",codes(d))
    def test_bad_year_format(self):
        d=mutate("fees",lambda r:r[0].update(academic_year="2026-28")); self.assertIn("BAD_TYPE",codes(d))
    def test_two_last_known_good_rejected(self):
        d=mutate("data_version",lambda r:r.append(dict(r[0],data_version="SYN-v2"))); self.assertIn("LAST_KNOWN_GOOD",codes(d))
    def test_missing_data_stays_blank_not_zero(self):
        fees={r["college_code"] for r in csv.DictReader(open(os.path.join(SYN,"fees.csv")))}
        self.assertNotIn("SYN12",fees)   # no fee row exists -> must later display "Not available"
    def test_some_choices_have_no_vacancy(self):
        ch={r["choice_code"] for r in csv.DictReader(open(os.path.join(SYN,"branches.csv")))}
        vac={r["choice_code"] for r in csv.DictReader(open(os.path.join(SYN,"vacancies.csv")))}
        self.assertTrue(ch-vac)
    def test_current_year_has_no_round_IV(self):
        rounds={r["cap_round"] for r in csv.DictReader(open(os.path.join(SYN,"current_cutoffs.csv")))}
        self.assertEqual(rounds,{"I","II","III"})
if __name__=="__main__": unittest.main()
