"""Stage 12b-3b: match NBA programs (rows of institutions linked in 12b-3a) to website branches (tables/branches.csv).

Rules (never guess):
 - 'matched' only when the canonical program name equals the canonical branch name of the SAME college (spelling-only differences are removed:
   case, '&'='and', Engg=Engineering, plural Textiles/Materials/Telecommunications, [SW]/(Sandwich Pattern) = Sandwich), or when the owner approved that
   exact name pair in data/manual/nba_program_rules.csv (columns: nba_program, branch_name, decision yes/no; names in canonical form).
 - 'unclear' when the college has a branch whose name is a close relative (one name's words are all inside the other's, e.g. Electronics Engineering /
   Electronics and Telecommunication Engineering) and the pair has no owner decision yet. The distinct pairs go to the owner as a short list.
 - 'no_branch' when the college has no related branch (the program is not a CAP branch of that college). Nothing is linked.
Output: data/normalized/nba_link/nba_program_match.csv (+ report).
"""
import csv, json, os, re, sys, collections
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
N = os.path.join(ROOT, "data", "normalized")
RULES = os.path.join(ROOT, "data", "manual", "nba_program_rules.csv")
OUT_COLS = ["nba_institution", "nba_place", "college_code", "program", "status", "choice_codes", "how", "valid_from", "valid_to", "validity_basis", "nba_status", "source_file", "source_sha256", "downloaded_on"]
SING = {"telecommunications": "telecommunication", "textiles": "textile", "materials": "material", "technologies": "technology"}


def canon(s):
    s = (s or "").lower().replace("&", " and ").replace("engg", "engineering")
    s = re.sub(r"\[sw\]|\(sw\)", " sandwich ", s); s = s.replace("sandwich pattern", "sandwich")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(SING.get(w, w) for w in s.split() if w not in ("and", "of", "the"))


def related(a, b):
    A, B = set(a.split()), set(b.split())
    return bool(A) and bool(B) and a != b and (A <= B or B <= A) and (("sandwich" in A) == ("sandwich" in B))


def load(p):
    with open(p, newline="", encoding="utf-8") as f: return list(csv.DictReader(f))


def load_rules(path=RULES):
    rules = {}
    if os.path.exists(path):
        for r in load(path): rules[(canon(r["nba_program"]), canon(r["branch_name"]))] = r["decision"].strip().lower()
    return rules


def build(base=N, rules_path=RULES, outdir=None):
    outdir = outdir or os.path.join(base, "nba_link")
    inst = {(r["nba_institution"], r["nba_place"]): r["college_code"] for r in load(os.path.join(base, "nba_link", "nba_institution_match.csv")) if r["status"] == "linked"}
    nba = load(os.path.join(base, "nba", "nba_programs.csv")); rules = load_rules(rules_path)
    br = collections.defaultdict(list)
    for b in load(os.path.join(base, "tables", "branches.csv")): br[b["college_code"]].append(b)
    rows, pairs, multi, used = [], collections.defaultdict(lambda: [0, set()]), [], set()
    for r in nba:
        cc = inst.get((r["institution_name"], r["place"]))
        if not cc: continue
        pc = canon(r["program"]); hit, how, unc = [], "", []
        for b in br[cc]:
            bc = canon(b["branch_name"])
            if bc == pc: hit.append(b); how = "exact name"
            elif related(pc, bc):
                d = rules.get((pc, bc))
                if d is not None: used.add((pc, bc))
                if d == "yes": hit.append(b); how = how or "owner approved name pair"
                elif d is None: unc.append(bc)
        if hit: status = "matched"
        elif unc: status = "unclear"
        else: status, how = "no_branch", "college has no related branch"
        if status == "unclear":
            for bc in unc: pairs[(pc, bc)][0] += 1; pairs[(pc, bc)][1].add(cc)
            how = "waiting for owner: " + "; ".join(sorted(set(unc)))
        if len(hit) > 1: multi.append([cc, r["program"], [h["choice_code"] for h in hit]])
        rows.append(dict(nba_institution=r["institution_name"], nba_place=r["place"], college_code=cc, program=r["program"], status=status,
                         choice_codes=";".join(h["choice_code"] for h in hit), how=how, valid_from=r["valid_from"], valid_to=r["valid_to"], validity_basis=r["validity_basis"],
                         nba_status=r["status"], source_file=r["source_file"], source_sha256=r["source_sha256"], downloaded_on=r["downloaded_on"]))
    cnt = collections.Counter(x["status"] for x in rows)
    rep = dict(ok=True, rows=len(rows), counts=dict(cnt), pairs_waiting=[[a, b, v[0], len(v[1])] for (a, b), v in sorted(pairs.items(), key=lambda kv: -kv[1][0])],
               multi_choice_code=multi, unused_rules=[list(k) for k in rules if k not in used], problems=[])
    for k, d in rules.items():
        if d not in ("yes", "no"): rep["problems"].append("bad rule decision for %s" % (k,))
    rep["ok"] = not rep["problems"]
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "nba_program_match.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=OUT_COLS, lineterminator="\r\n"); w.writeheader(); w.writerows(rows)
    with open(os.path.join(outdir, "nba_program_match_report.json"), "w", encoding="utf-8") as fh: json.dump(rep, fh, indent=1, ensure_ascii=False)
    return rep


def main():
    rep = build(); print("rows:", rep["rows"], "counts:", rep["counts"], "pairs waiting:", len(rep["pairs_waiting"]))
    for p in rep["pairs_waiting"]: print("PAIR:", p)
    for p in rep["problems"]: print("FAIL:", p)
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
