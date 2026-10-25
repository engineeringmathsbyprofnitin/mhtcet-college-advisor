"""Publishes validated tables as small static data files for the website.

Usage:  python export_static.py <csv_folder> <output_folder> [--now 2026-10-25T10:00:00Z]

What it does
  1. Runs the full validator. If there is ANY error, nothing is published and the previous files stay untouched.
  2. Exports only rows with validation_status = validated.
  3. Writes one 'base' file (small tables) and one cutoff file per seat type, in a compact column format.
  4. File names contain a content hash, so a browser can never mix files from two different versions.
  5. Writes manifest.json LAST (it is the pointer to the new version), then deletes files no longer referenced.
The website reads manifest.json first, then only the files a given student needs."""
import csv, hashlib, json, os, re, shutil, sys, tempfile, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import validate_data as V

FORMAT = 1
BASE_TABLES = ["colleges", "branches", "seat_types", "vacancies", "fees", "accreditation", "placements", "hostels",
               "quality_indicators", "source_documents", "refresh_status", "data_version"]
CUTOFF_TABLES = ["historical_cutoffs", "current_cutoffs"]
KEEP = {  # only the columns the engine/website need (everything else stays in the database)
    "historical_cutoffs": ["choice_code", "admission_year", "cap_round", "seat_type_code", "cutoff_percentile", "source_doc_id"],
    "current_cutoffs": ["choice_code", "admission_year", "cap_round", "seat_type_code", "cutoff_percentile", "source_doc_id"],
    "vacancies": ["choice_code", "admission_year", "cap_round", "seat_type_code", "vacancy_count", "source_doc_id"],
    "fees": ["college_code", "choice_code", "academic_year", "fee_type", "annual_fee_inr", "fee_scope", "source_doc_id"],
    "branches": ["choice_code", "college_code", "branch_code", "branch_name", "branch_group"],
}
DROP_DEFAULT = {"validation_status", "retrieved_date", "is_synthetic"}
KEEP_ALL = {"data_version", "source_documents", "refresh_status", "seat_types"}   # small, shown to students or used for checks
SAFE_CODE = re.compile(r"^[A-Za-z0-9_-]{1,30}$")

class PublishError(Exception): pass

def read(folder, t):
    with open(os.path.join(folder, t + ".csv"), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def compact(rows, table, schema_cols):
    cols = [c for c in schema_cols if (c in KEEP[table] if table in KEEP else (table in KEEP_ALL or c not in DROP_DEFAULT))]
    body = sorted([[r.get(c, "") for c in cols] for r in rows])
    return {"columns": cols, "rows": body}

def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")

def sha(b): return hashlib.sha256(b).hexdigest()

def build(csv_folder, now):
    errors = V.validate(csv_folder)
    if errors:
        raise PublishError("Validation failed (%d error(s)); nothing was published. First: %s" % (len(errors), errors[0]))
    schema = V.SCHEMA
    cols = {t: [c["name"] for c in schema[t]["columns"]] for t in schema}
    def validated(t):
        rows = read(csv_folder, t)
        return [r for r in rows if r.get("validation_status", "validated") == "validated"]
    lkg = [r for r in read(csv_folder, "data_version") if r["is_last_known_good"] == "TRUE"][0]
    base = {t: compact(validated(t) if t != "seat_types" else read(csv_folder, t), t, cols[t]) for t in BASE_TABLES}
    if not base["colleges"]["rows"] or not base["branches"]["rows"]:
        raise PublishError("No colleges or branches to publish.")
    files = {}                                  # relative path -> bytes
    manifest = {"format": FORMAT, "data_version": lkg["data_version"], "current_admission_year": lkg["admission_year"],
                "is_synthetic": lkg["is_synthetic"] == "TRUE", "generated_at": now, "last_successful_update": None,
                "base": {}, "cutoffs": {}, "row_counts": {}}
    succ = sorted([r["finished_at"] for r in read(csv_folder, "refresh_status") if r["status"] == "success"])
    manifest["last_successful_update"] = succ[-1] if succ else None
    b = dumps(base); name = "base.%s.json" % sha(b)[:10]
    files[name] = b; manifest["base"] = {"file": name, "sha256": sha(b), "bytes": len(b)}
    for t in BASE_TABLES: manifest["row_counts"][t] = len(base[t]["rows"])
    # cutoffs, one file per seat type
    by_seat = {}
    for t in CUTOFF_TABLES:
        for r in validated(t):
            code = r["seat_type_code"]
            if not SAFE_CODE.match(code): raise PublishError("Unsafe seat type code: %r" % code)
            by_seat.setdefault(code, {tt: [] for tt in CUTOFF_TABLES})[t].append(r)
    for t in CUTOFF_TABLES: manifest["row_counts"][t] = sum(len(v[t]) for v in by_seat.values())
    for code in sorted(by_seat):
        payload = {"seat_type_code": code, **{t: compact(by_seat[code][t], t, cols[t]) for t in CUTOFF_TABLES}}
        b = dumps(payload); name = "cutoffs/%s.%s.json" % (code, sha(b)[:10])
        files[name] = b
        manifest["cutoffs"][code] = {"file": name, "sha256": sha(b), "bytes": len(b), "rows": {t: len(by_seat[code][t]) for t in CUTOFF_TABLES}}
    return files, manifest

def publish(csv_folder, out, now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    files, manifest = build(csv_folder, now)          # raises before touching anything if invalid
    os.makedirs(os.path.join(out, "cutoffs"), exist_ok=True)
    for rel, data in files.items():                   # 1. new data files (new names, so old version keeps working)
        p = os.path.join(out, rel)
        if not os.path.exists(p):
            tmp = p + ".tmp"
            with open(tmp, "wb") as f: f.write(data)
            os.replace(tmp, p)
    mp = os.path.join(out, "manifest.json"); tmp = mp + ".tmp"   # 2. switch over: the manifest is written last
    with open(tmp, "wb") as f: f.write(dumps(manifest))
    os.replace(tmp, mp)
    keep = set(files) | {"manifest.json"}                # 3. tidy up files of older versions
    for root, _, names in os.walk(out):
        for n in names:
            rel = os.path.relpath(os.path.join(root, n), out).replace(os.sep, "/")
            if rel not in keep and (rel.startswith("base.") or rel.startswith("cutoffs/") or rel.endswith(".tmp")):
                os.remove(os.path.join(root, n))
    return manifest

if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    now = sys.argv[sys.argv.index("--now") + 1] if "--now" in sys.argv else None
    if now and now in a: a.remove(now)
    try:
        m = publish(a[0], a[1], now)
    except PublishError as e:
        print("NOT PUBLISHED:", e); sys.exit(1)
    tot = m["base"]["bytes"] + sum(c["bytes"] for c in m["cutoffs"].values())
    print("Published data version %s (admission year %s): %d cutoff file(s), %d bytes in total" % (m["data_version"], m["current_admission_year"], len(m["cutoffs"]), tot))
