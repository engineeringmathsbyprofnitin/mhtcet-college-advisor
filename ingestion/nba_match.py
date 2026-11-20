"""Stage 12b-3a: match NBA institutions (data/normalized/nba/nba_programs.csv) to website colleges (tables/colleges.csv).

Rules (never guess):
 - A pair is linked automatically only when the name score is high, the best college is clearly ahead of the second best,
   and the place does not contradict (the NBA place, when printed, must appear in the college name/district or be a known spelling/old name).
 - A pair that is plausible but not certain goes to the DOUBTFUL list; the owner confirms it in data/manual/nba_institution_confirmations.csv
   (column decision = yes + college_code, or no). Nothing doubtful is ever used until confirmed.
 - An NBA institution with no plausible college (for example a university that does not take part in CAP) is reported as 'no_college'.
Output: data/normalized/nba_link/nba_institution_match.csv (+ report). NOT inside data/normalized/nba, because the "Read the NBA lists" workflow replaces that whole folder.
"""
import csv, difflib, functools, json, math, os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
N = os.path.join(ROOT, "data", "normalized")
MANUAL = os.path.join(ROOT, "data", "manual", "nba_institution_confirmations.csv")
AUTO_MIN, AUTO_MARGIN, DOUBT_MIN = 0.80, 0.15, 0.45
BAND_MIN, BAND_MARGIN = 0.65, 0.20          # lower band: allowed only when the printed place is found in the college name/district
OUT_COLS = ["nba_institution", "nba_place", "nba_rows", "college_code", "college_name", "status", "score", "second_best", "how"]
ABBR = {"engg": "engineering", "engg.": "engineering", "mgt": "management", "mgmt": "management", "tech": "technology", "technol": "technology",
        "inst": "institute", "instt": "institute", "univ": "university", "govt": "government", "dept": "department", "mah": "maharashtra",
        "sci": "science", "coll": "college", "engiineering": "engineering", "engieering": "engineering"}
STOP = set("the and of for in at an autonomous society societys education trust shikshan prasarak mandal mandals sanstha santha samstha pratishthan "
           "pratisthan charitable foundation shri smt sanchalit ltd campus faculty vikas gramin bahu uddeshiya pvt private "
           "welfare institutes educational s sansthas dr prof".split())
# place spellings/old names -> the form used in the official college list (comparison only, never shown as data)
PLACE = {"aurangabad": "chhatrapati sambhajinagar", "osmanabad": "dharashiv", "ahmednagar": "ahilyanagar", "ahmadnagar": "ahilyanagar", "sholapur": "solapur",
         "kolhpur": "kolhapur", "navi mumabi": "navi mumbai", "mumbai-city": "mumbai city", "mumbai": "mumbai", "pimpri,pune": "pune", "kondhwa, pune": "pune"}


KNOWN_PLACES = {"pune", "nagpur", "nashik", "thane", "kolhapur", "mumbai", "mumbai city", "navi mumbai", "solapur", "chhatrapati sambhajinagar", "ahilyanagar", "raigad",
                "jalgaon", "amravati", "satara", "dhule", "sangli", "buldhana", "beed", "latur", "palghar", "chandrapur", "nanded", "ratnagiri", "wardha", "yavatmal",
                "dharashiv", "bhandara", "nandurbar", "jalna", "sindhudurg", "akola", "washim", "parbhani", "gadchiroli"}


def norm(s):
    s = (s or "").lower().replace("&#39;", "'").replace("&amp;", "&").replace("&", " and ")
    s = re.sub(r"\([^)]*\)", " ", s)                                  # "(An Autonomous Institute of ...)" is not part of the name
    s = re.sub(r"[\u2019']s\b", "", s); s = re.sub(r"(?<=\b[a-z])\.(?=[a-z]\b)", "", s)   # D.Y. -> dy
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    out, run = [], []
    for t in s.split() + [""]:
        if len(t) == 1 and t.isalpha(): run.append(t); continue
        if run: out.append("".join(run)); run = []
        if t: out.append(ABBR.get(t, t))
    return out


@functools.lru_cache(maxsize=None)
def _toks(s): return tuple(t for t in norm(s) if len(t) >= 2 and t not in STOP)


def toks(s): return list(_toks(s))


def _old_toks(s): return [t for t in norm(s) if len(t) >= 2 and t not in STOP]


@functools.lru_cache(maxsize=None)
def similar(a, b): return a == b or (len(a) >= 4 and len(b) >= 4 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.84)


def load(p):
    with open(p, newline="", encoding="utf-8") as f: return list(csv.DictReader(f))


def make_idf(colleges):
    df = {}
    for c in colleges:
        for t in set(toks(c["college_name"])): df[t] = df.get(t, 0) + 1
    n = len(colleges)
    return lambda t: math.log((n + 1) / (df.get(t, 0) + 1)) + 1.0


def score(nba_name, col_name, idf):
    A, B = toks(nba_name), toks(col_name)
    if not A or not B: return 0.0
    wa = sum(idf(t) for t in A); wb = sum(idf(t) for t in B)
    ma = sum(idf(t) for t in A if any(similar(t, u) for u in B)); mb = sum(idf(u) for u in B if any(similar(u, t) for t in A))
    ca, cb = ma / wa, mb / wb
    return 0.0 if ca + cb == 0 else 2 * ca * cb / (ca + cb)       # both names must be covered by the other (F1)


def place_state(place, col):
    """'ok' place printed and found, 'conflict' printed and clearly elsewhere, 'unknown' not printed or college place unknown."""
    p = PLACE.get((place or "").strip().lower(), (place or "").strip().lower())
    if not p: return "unknown"
    ptoks = [t for t in norm(p) if len(t) >= 3]
    hay = " ".join(norm(col["college_name"]) + norm(col["district"]) + norm(col.get("city", "")))
    if ptoks and all(any(similar(t, h) for h in hay.split()) for t in ptoks): return "ok"
    if col["district"] in ("", "Not available"): return "unknown"
    known = KNOWN_PLACES | {t for c in (p,) for t in [c]}
    return "conflict" if p in KNOWN_PLACES else "unknown"       # a town (Islampur...) cannot be checked against a district: unknown, never a conflict


def adj(sc, ps): return sc + (0.15 if ps == "ok" else -0.30 if ps == "conflict" else 0)


def load_confirmations(path=MANUAL):
    conf = {}
    if os.path.exists(path):
        for r in load(path): conf[(r["nba_institution"], r["nba_place"])] = (r["decision"].strip().lower(), r.get("college_code", "").strip())
    return conf


def build(base=N, manual=MANUAL, outdir=None):
    outdir = outdir or os.path.join(base, "nba_link")
    nba = load(os.path.join(base, "nba", "nba_programs.csv")); colleges = load(os.path.join(base, "tables", "colleges.csv")); idf = make_idf(colleges)
    by_code = {c["college_code"]: c for c in colleges}; conf = load_confirmations(manual)
    insts = {}
    for r in nba: insts[(r["institution_name"], r["place"])] = insts.get((r["institution_name"], r["place"]), 0) + 1
    rows, rep = [], dict(ok=False, institutions=len(insts), counts={}, problems=[], doubtful=[], unused_confirmations=[])
    seen_conf = set()
    for (name, place), k in insts.items():
        # rank by name score, with the printed place as a tie-breaker (+0.15 found in the college, -0.30 a different known district)
        ranked = sorted(((score(name, c["college_name"], idf), place_state(place, c), c) for c in colleges), key=lambda x: -(x[0] + (0.15 if x[1] == "ok" else -0.30 if x[1] == "conflict" else 0)))
        (s1, ps, c1), (s2, _p2, c2) = ranked[0], ranked[1]
        row = dict(nba_institution=name, nba_place=place, nba_rows=k, college_code="", college_name="", status="", score="%.2f" % s1, second_best="%.2f" % s2, how="")
        key = (name, place)
        if key in conf:
            seen_conf.add(key); d, code = conf[key]
            if d == "yes" and code in by_code: row.update(college_code=code, college_name=by_code[code]["college_name"], status="linked", how="owner confirmed")
            elif d == "no": row.update(status="no_college", how="owner said: not a college on the website")
            else: rep["problems"].append("bad confirmation for %s / %s" % (name, place)); row.update(status="doubtful", how="confirmation not understood")
        elif s1 >= AUTO_MIN and adj(s1, ps) - adj(s2, _p2) >= AUTO_MARGIN and ps != "conflict":
            row.update(college_code=c1["college_code"], college_name=c1["college_name"], status="linked", how="automatic: name score %.2f, place %s" % (s1, ps))
        elif BAND_MIN <= s1 < AUTO_MIN and adj(s1, ps) - adj(s2, _p2) >= BAND_MARGIN and ps == "ok":
            row.update(college_code=c1["college_code"], college_name=c1["college_name"], status="linked", how="automatic (place confirmed): name score %.2f, clear lead" % s1)
        elif s1 >= DOUBT_MIN:
            row.update(status="doubtful", how="candidate %s %s (%s) place %s; second %s" % (c1["college_code"], c1["college_name"][:50], "%.2f" % s1, ps, c2["college_code"]))
            rep["doubtful"].append([name[:70], place, [[c["college_code"], c["college_name"][:50], c["district"], round(s, 2)] for s, _p, c in ranked[:3]]])
        else: row.update(status="no_college", how="no plausible college (best score %.2f)" % s1)
        rows.append(row)
    rep["unused_confirmations"] = [list(k) for k in conf if k not in seen_conf]
    cnt = {}
    for r in rows: cnt[r["status"]] = cnt.get(r["status"], 0) + 1
    rep["counts"] = cnt
    many = {}
    for r in rows:
        if r["status"] == "linked": many.setdefault(r["college_code"], []).append(r["nba_institution"][:40])
    rep["colleges_with_several_nba_names"] = {k: v for k, v in many.items() if len(v) > 1}
    rep["ok"] = not rep["problems"]
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "nba_institution_match.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=OUT_COLS, lineterminator="\r\n"); w.writeheader(); w.writerows(rows)
    with open(os.path.join(outdir, "nba_institution_match_report.json"), "w", encoding="utf-8") as fh: json.dump(rep, fh, indent=1, ensure_ascii=False)
    return rep


def main():
    rep = build(); print("institutions:", rep["institutions"], "counts:", rep["counts"])
    for d in rep["doubtful"]: print("DOUBTFUL:", d)
    for p in rep["problems"]: print("FAIL:", p)
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
