"""Validates a folder of CSV tables against schema.json.
Usage: python validate_data.py <folder>      Exit code 0 = no errors."""
import csv, json, os, re, sys, datetime
HERE=os.path.dirname(os.path.abspath(__file__))
SCHEMA=json.load(open(os.path.join(HERE,"schema.json")))["tables"]
YEAR=re.compile(r"^\d{4}-\d{2}$")
def isdate(s):
    try: datetime.date.fromisoformat(s); return True
    except ValueError: return False
def check_type(v,t):
    try:
        if t=="int": return int(v)>=0 if re.fullmatch(r"-?\d+",v) else False
        if t=="float": float(v); return True
        if t=="percentile": return 0<=float(v)<=100
        if t=="score10": return 0<=float(v)<=10
        if t=="date": return isdate(v)
        if t=="bool": return v in ("TRUE","FALSE")
        if t=="year":
            if not YEAR.match(v): return False
            a,b=int(v[:4]),int(v[5:]); return (a+1)%100==b
    except ValueError: return False
    return True
def load(folder):
    data={}
    for t in SCHEMA:
        p=os.path.join(folder,t+".csv")
        if os.path.exists(p):
            with open(p,newline="") as f: data[t]=list(csv.DictReader(f)); data[t+"__hdr"]=data[t] and list(data[t][0].keys())
    return data
def validate(folder):
    E=[]; err=lambda t,i,c,m:E.append((t,i,c,m))
    data={}; headers={}
    for t,spec in SCHEMA.items():
        p=os.path.join(folder,t+".csv")
        if not os.path.exists(p): err(t,0,"MISSING_FILE",p); data[t]=[]; continue
        with open(p,newline="") as f:
            rd=csv.DictReader(f); headers[t]=rd.fieldnames; data[t]=list(rd)
        want=[c["name"] for c in spec["columns"]]
        if headers[t]!=want: err(t,0,"HEADER_MISMATCH",f"expected {want}")
    keys={}
    for t,spec in SCHEMA.items():
        seen=set(); useen=set()
        for i,r in enumerate(data[t],start=2):
            for c in spec["columns"]:
                v=(r.get(c["name"]) or "").strip()
                if v=="":
                    if c["required"]: err(t,i,"MISSING_REQUIRED",c["name"])
                    continue
                if not check_type(v,c["type"]):
                    code={"percentile":"PERCENTILE_RANGE","score10":"SCORE_RANGE"}.get(c["type"],"BAD_TYPE")
                    err(t,i,code,f"{c['name']}={v!r}")
                if "enum" in c and v not in c["enum"]: err(t,i,"BAD_ENUM",f"{c['name']}={v!r}")
            pk=tuple(r.get(k,"") for k in spec["primary_key"])
            if pk in seen: err(t,i,"DUP_PK",str(pk))
            seen.add(pk)
            if spec.get("unique"):
                u=tuple(r.get(k,"") for k in spec["unique"])
                if u in useen: err(t,i,"DUP_UNIQUE",str(u))
                useen.add(u)
        keys[t]=seen
    colvals=lambda t,c:{r.get(c,"") for r in data[t]}
    for t,spec in SCHEMA.items():
        for c in spec["columns"]:
            if "fk" in c:
                tt,cc=c["fk"].split("."); ok=colvals(tt,cc)
                for i,r in enumerate(data[t],start=2):
                    v=r.get(c["name"],"")
                    if v and v not in ok: err(t,i,"FK_MISSING",f"{c['name']}={v!r} not in {c['fk']}")
    docs={r["doc_id"]:r for r in data["source_documents"]}
    sanct={(r["choice_code"],r["academic_year"]):int(r["seats"]) for r in data["seat_intake"] if r["intake_type"]=="sanctioned" and r["seats"].isdigit()}
    seat_codes=colvals("seat_types","seat_type_code")
    for i,r in enumerate(data["vacancies"],start=2):
        d=docs.get(r["source_doc_id"])
        if d is None or d["doc_type"]!="vacancy_position": err("vacancies",i,"VACANCY_BAD_SOURCE",f"source doc type must be vacancy_position, got {d and d['doc_type']}")
        elif d["cap_round"]!=r["cap_round"]: err("vacancies",i,"VACANCY_BAD_SOURCE","round differs from source document round")
        if r["seat_type_code"]!="ALL" and r["seat_type_code"] not in seat_codes: err("vacancies",i,"FK_MISSING","seat_type_code")
        cap=sanct.get((r["choice_code"],r["admission_year"]))
        if cap is not None and r["vacancy_count"].isdigit() and int(r["vacancy_count"])>cap: err("vacancies",i,"VACANCY_EXCEEDS_INTAKE",f"{r['vacancy_count']}>{cap}")
    for t in ("historical_cutoffs","current_cutoffs"):
        for i,r in enumerate(data[t],start=2):
            d=docs.get(r["source_doc_id"])
            if d and d["doc_type"]!="cutoff": err(t,i,"CUTOFF_BAD_SOURCE",f"doc type {d['doc_type']}")
    for i,r in enumerate(data["accreditation"],start=2):
        if r["valid_from"] and r["valid_to"] and r["valid_to"]<r["valid_from"]: err("accreditation",i,"DATE_ORDER","valid_to before valid_from")
    for i,r in enumerate(data["quality_indicators"],start=2):
        if r["is_estimate"]!="TRUE": err("quality_indicators",i,"ESTIMATE_FLAG","calculated ratings must be labelled is_estimate=TRUE")
    pm={}
    for r in data["placements"]:
        if r["metric"] in ("students_placed","students_eligible"):
            try: pm.setdefault((r["college_code"],r["choice_code"],r["placement_year"],r["scope"]),{})[r["metric"]]=float(r["value"])
            except ValueError: pass
    for k,v in pm.items():
        if "students_placed" in v and "students_eligible" in v and v["students_placed"]>v["students_eligible"]: err("placements",0,"PLACED_EXCEEDS_ELIGIBLE",str(k))
    for i,r in enumerate(data["placements"],start=2):
        if r["metric"]=="placement_percent" and r["value"] and float(r["value"])>100: err("placements",i,"PERCENT_RANGE","placement_percent above 100")
    if sum(1 for r in data["data_version"] if r["is_last_known_good"]=="TRUE")!=1: err("data_version",0,"LAST_KNOWN_GOOD","exactly one version must be last-known-good")
    return E
if __name__=="__main__":
    E=validate(sys.argv[1]); [print(e) for e in E[:50]]
    print(f"{len(E)} error(s)"); sys.exit(1 if E else 0)
