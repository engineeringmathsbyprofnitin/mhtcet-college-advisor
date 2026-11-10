"""Stage 10c-3a: package the real tables as the website's static data files (staging folder, NOT the live site).
Run: python -m ingestion.package_real [out_dir]   (default: frontend/data-real)
It assembles a full 16-table folder (tables we do not have yet are header-only = 'Not available'), runs the SAME validator and exporter
as before (database/validate_data.py, database/export_static.py), so nothing is published unless it validates."""
import csv, gzip, hashlib, json, os, shutil, sys, tempfile
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "database"))
from ingestion import plan as P
import export_static as X
T = os.path.join(ROOT, "data", "normalized", "tables")
TEMPLATES = os.path.join(ROOT, "database", "templates")
REAL = ["colleges", "branches", "seat_types", "source_documents", "current_cutoffs", "historical_cutoffs"]

def assemble(folder, plan=None):
    plan = plan or P.make_plan(json.load(open(P.DISCOVERY))["admission_year"])
    for f in os.listdir(TEMPLATES):                     # header-only tables first (vacancies, fees, ... = none yet)
        shutil.copy(os.path.join(TEMPLATES, f), os.path.join(folder, f))
    for t in REAL:
        src = os.path.join(T, t + (".csv.gz" if t.endswith("cutoffs") else ".csv"))
        with (gzip.open(src, "rb") if src.endswith(".gz") else open(src, "rb")) as i, open(os.path.join(folder, t + ".csv"), "wb") as o: shutil.copyfileobj(i, o)
    h = hashlib.sha256()
    for t in REAL[-2:]:
        with open(os.path.join(folder, t + ".csv"), "rb") as f: h.update(f.read())
    ver = "REAL-%s-R%s-%s" % (plan["current_year"], plan["latest_round"], h.hexdigest()[:8])
    summary = "rounds=%s;next=%s;phase=%s" % ("+".join(plan["rounds_done"]), plan["next_round_expected"] or "none", plan["year_status"])
    with open(os.path.join(folder, "data_version.csv"), "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow("data_version,created_at,is_last_known_good,admission_year,row_count_summary,notes,is_synthetic".split(","))
        w.writerow([ver, json.load(open(P.DISCOVERY))["generated_at"], "TRUE", plan["current_year"], summary, "Real CET Cell cutoff lists; fees, vacancies, accreditation, placements not yet available", "FALSE"])
    return ver

def main(out):
    folder = tempfile.mkdtemp()
    try:
        ver = assemble(folder)
        m = X.publish(folder, out, now="1970-01-01T00:00:00Z")
        return ver, m
    finally: shutil.rmtree(folder)

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "frontend", "data-real")
    try: ver, m = main(out)
    except X.PublishError as e: print("NOT PUBLISHED:", e); sys.exit(1)
    print(ver, "files:", len(m["cutoffs"]) + 1, "bytes:", m["base"]["bytes"] + sum(c["bytes"] for c in m["cutoffs"].values()))
