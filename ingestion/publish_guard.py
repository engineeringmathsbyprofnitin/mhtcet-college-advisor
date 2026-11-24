"""Stage 14c: has the website data REALLY changed? (daily publish run)
The published data carries three kinds of time stamps that change with every discovery run even when no document changed: data_version.created_at,
refresh_status.started_at / finished_at and manifest.last_successful_update. This guard compares the freshly built folder with the published one
IGNORING those stamps (all tables and every cutoff file are compared by content). If nothing else differs the published folder is kept as it is,
so a quiet day makes no commit and the browsers' cached copies stay valid.
Run: python -m ingestion.publish_guard <published folder> <new folder>   -> prints 'changed' or 'unchanged'; writes changed=true/false to $GITHUB_OUTPUT."""
import glob, hashlib, json, os, sys

STAMPS = {"data_version": ["created_at"], "refresh_status": ["started_at", "finished_at"]}


def _base(folder):
    files = glob.glob(os.path.join(folder, "base.*.json"))
    if len(files) != 1: raise ValueError("%s: expected one base.*.json, found %d" % (folder, len(files)))
    with open(files[0], encoding="utf-8") as f: return json.load(f)


def normalised(folder):
    """(base without time stamps, {cutoff file name: sha256}, manifest without time stamp and without file hashes of the base)."""
    base = _base(folder)
    for table, cols in STAMPS.items():
        t = base.get(table)
        if not t: continue
        idx = [t["columns"].index(c) for c in cols if c in t["columns"]]
        for row in t["rows"]:
            for i in idx: row[i] = ""
    cdir = os.path.join(folder, "cutoffs"); cut = {}
    if os.path.isdir(cdir):
        for n in sorted(os.listdir(cdir)):
            with open(os.path.join(cdir, n), "rb") as f: cut[n] = hashlib.sha256(f.read()).hexdigest()
    with open(os.path.join(folder, "manifest.json"), encoding="utf-8") as f: man = json.load(f)
    man.pop("last_successful_update", None); man.pop("base", None); man.pop("cutoffs", None)
    return base, cut, man


def changed(old, new):
    if not os.path.isdir(old) or not os.path.exists(os.path.join(old, "manifest.json")): return True
    try: return normalised(old) != normalised(new)
    except (ValueError, OSError, KeyError, json.JSONDecodeError): return True      # unreadable published data: publish the new build


def main(argv=None):
    a = argv if argv is not None else sys.argv[1:]
    if len(a) != 2: print("usage: python -m ingestion.publish_guard <published folder> <new folder>"); return 2
    c = changed(a[0], a[1]); print("changed" if c else "unchanged")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f: f.write("changed=%s\n" % ("true" if c else "false"))
    return 0

if __name__ == "__main__": sys.exit(main())
