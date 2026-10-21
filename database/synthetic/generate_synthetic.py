"""Generates SYNTHETIC (fake) test data into data/synthetic/. Every row has is_synthetic=TRUE.
Nothing here is real CET Cell data. Run: python generate_synthetic.py"""
import csv, json, os, random
random.seed(42)
HERE=os.path.dirname(os.path.abspath(__file__))
OUT=os.path.join(HERE,"..","..","data","synthetic")
os.makedirs(OUT,exist_ok=True)
schema=json.load(open(os.path.join(HERE,"..","schema.json")))["tables"]
rows={t:[] for t in schema}
def add(t,**kw):
    r={c["name"]:"" for c in schema[t]["columns"]}; r.update(kw)
    if "is_synthetic" in r: r["is_synthetic"]="TRUE"
    if "validation_status" in r and not r["validation_status"]: r["validation_status"]="validated"
    rows[t].append(r)

HIST=["2023-24","2024-25","2025-26"]; CUR="2026-27"
docs={}
def doc(i,typ,year,rnd="",pub="2026-01-01"):
    d=f"SYN-DOC-{i:03d}"; docs[(typ,year,rnd)]=d
    add("source_documents",doc_id=d,source_name="SYNTHETIC source",source_url=f"https://example.invalid/{d}",filename=f"{d}.csv",
        admission_year=year,doc_type=typ,cap_round=rnd,published_date=pub,retrieved_date="2026-10-20",validation_status="validated")
n=1
for y in HIST: doc(n,"cutoff",y,"IV"); n+=1
for r in ["I","II","III"]: doc(n,"cutoff",CUR,r); n+=1
doc(n,"vacancy_position",CUR,"III"); n+=1
doc(n,"seat_matrix",CUR); n+=1
doc(n,"fee_notice",CUR); n+=1
doc(n,"accreditation_list",""); n+=1
doc(n,"placement_report","2025-26"); n+=1
doc(n,"college_list",CUR); n+=1
SD=lambda typ,y="",r="":docs[(typ,y,r)]

cols=[("SYN01","Pune",1.0,"Private Unaided"),("SYN02","Pune",0.9,"Autonomous"),("SYN03","Pune",0.5,"Private Unaided"),
("SYN04","Mumbai Suburban",0.95,"Autonomous"),("SYN05","Mumbai Suburban",0.6,"Private Unaided"),("SYN06","Nagpur",0.8,"Government-Aided"),
("SYN07","Nagpur",0.4,"Private Unaided"),("SYN08","Thane",0.55,"Private Unaided"),("SYN09","Nashik",0.65,"Private Unaided"),
("SYN10","Kolhapur",0.7,"Government-Aided"),("SYN11","Chhatrapati Sambhajinagar (Aurangabad)",0.45,"Private Unaided"),("SYN12","Sangli",0.5,"Government-Aided")]
BR=[("B01","Computer Science and Engineering","CSE",1.0),("B02","Computer Engineering","COMP",0.97),("B03","Information Technology","IT",0.93),
("B04","Artificial Intelligence and Data Science","AIDS",0.9),("B05","Electronics and Telecommunication Engineering","ENTC",0.8),
("B06","Mechanical Engineering","MECH",0.65),("B07","Civil Engineering","CIVIL",0.5),("B08","Electrical Engineering","ELEC",0.7)]
ST=[("GOPENS","Maharashtra State candidate","Open","","State Level",0.0),("GOBCS","Maharashtra State candidate","OBC","","State Level",-3.0),
("GSCS","Maharashtra State candidate","SC","","State Level",-12.0),("LOPENS","Maharashtra State candidate","Open","Female","State Level",-1.5)]
for code,cand,cat,g,lvl,_ in ST:
    add("seat_types",seat_type_code=code,candidate_type=cand,category=cat,gender_scope=g,seat_level=lvl,description="SYNTHETIC/provisional seat type",is_provisional="TRUE")

ids=0
def nid(p):
    global ids; ids+=1; return f"{p}{ids:05d}"
choices=[]
for i,(cc,dist,tier,typ) in enumerate(cols):
    add("colleges",college_code=cc,college_name=f"SYNTHETIC Institute of Technology {chr(65+i)}",district=dist,city=dist.split(" ")[0],college_type=typ,status="active",
        source_doc_id=SD("college_list",CUR),is_synthetic="TRUE")
    add("college_name_history",college_code=cc,college_name=f"SYNTHETIC Institute of Technology {chr(65+i)}",valid_from_year="2023-24",source_doc_id=SD("college_list",CUR))
    for j,(bc,bn,grp,pop) in enumerate(BR):
        if (i+j)%7==0 or (j>=5 and i%3==0 and j==7): continue   # not every college has every branch
        ch=f"{cc}-{bc}"; choices.append((ch,cc,tier,pop,i,j))
        add("branches",choice_code=ch,college_code=cc,branch_code=bc,branch_name=bn,branch_group=grp,valid_from_year="2023-24",source_doc_id=SD("college_list",CUR))
        add("seat_intake",intake_id=nid("INT"),choice_code=ch,academic_year=CUR,intake_type="sanctioned",seats=str(random.choice([60,120,180])),source_doc_id=SD("seat_matrix",CUR))
intake={r["choice_code"]:int(r["seats"]) for r in rows["seat_intake"]}

for (ch,cc,tier,pop,i,j) in choices:
    base=99.2-(1-tier*pop)*38+random.uniform(-2,2)          # synthetic strength
    for yi,y in enumerate(HIST+[CUR]):
        drift=random.uniform(-1.5,1.5)+yi*0.4
        for stc,_,_,_,_,off in ST:
            val=max(35,min(99.99,base+drift+off+random.uniform(-.8,.8)))
            if y in HIST and random.random()<0.05: continue    # some historical data missing on purpose
            if y==HIST[0] and j==7 and i%2==0: continue        # e.g. branch did not exist yet
            tbl="historical_cutoffs" if y in HIST else "current_cutoffs"
            rounds=["IV"] if y in HIST else ["I","II","III"]
            for ri,r in enumerate(rounds):
                v=val-(0 if y in HIST else (2-ri)*0.9)
                add(tbl,cutoff_id=nid("CUT"),choice_code=ch,admission_year=y,cap_round=r,seat_type_code=stc,cutoff_percentile=f"{max(30,v):.7f}"[:10],
                    published_date="2026-09-01",source_doc_id=SD("cutoff",y,r))
for (ch,cc,tier,pop,i,j) in choices:
    if random.random()<0.35: continue     # no vacancy data for these choices -> must show "Vacancy data unavailable"
    add("vacancies",vacancy_id=nid("VAC"),choice_code=ch,admission_year=CUR,cap_round="III",seat_type_code="ALL",
        vacancy_count=str(random.randint(0,min(40,intake[ch]))),published_date="2026-10-05",source_doc_id=SD("vacancy_position",CUR,"III"))

for i,(cc,dist,tier,typ) in enumerate(cols):
    if i!=11:   # SYN12 has no fee data on purpose
        add("fees",fee_id=nid("FEE"),college_code=cc,academic_year=CUR,fee_type="tuition",annual_fee_inr=str(int(70000+tier*130000+random.randint(0,9)*1000)),fee_scope="Open/State",source_doc_id=SD("fee_notice",CUR))
    if i in (0,3):
        add("fees",fee_id=nid("FEE"),college_code=cc,academic_year=CUR,fee_type="total",annual_fee_inr=str(int(70000+tier*130000+90000)),fee_scope="Open/State incl. hostel",source_doc_id=SD("fee_notice",CUR))
    if i<8:
        grade=["A++","A+","A","B++"][i%4]
        st,vt=("expired","2023-03-31") if i==5 else ("accredited","2028-03-31")
        add("accreditation",accreditation_id=nid("ACC"),college_code=cc,body="NAAC",scope="institution",status=st,grade=grade,valid_from="2018-04-01",valid_to=vt,source_doc_id=SD("accreditation_list"))
    if i in (0,1,3,5):
        add("accreditation",accreditation_id=nid("ACC"),college_code=cc,choice_code=[c[0] for c in choices if c[1]==cc][0],body="NBA",scope="program",status="accredited",valid_from="2022-07-01",valid_to="2028-06-30",source_doc_id=SD("accreditation_list"))
    if i%4!=3:
        add("placements",placement_id=nid("PLC"),college_code=cc,placement_year="2025-26",metric="placement_percent",value=f"{40+tier*50:.1f}",scope="institution",source_doc_id=SD("placement_report","2025-26"))
        add("placements",placement_id=nid("PLC"),college_code=cc,placement_year="2025-26",metric="median_package_lpa",value=f"{3+tier*6:.1f}",scope="institution",source_doc_id=SD("placement_report","2025-26"))
    if i<10:
        for ind in ("teaching","infrastructure"):
            add("quality_indicators",indicator_id=nid("QI"),college_code=cc,indicator=ind,score_0_10=f"{3+tier*5+random.uniform(-.5,.5):.1f}",is_estimate="TRUE",
                method_version="synthetic-v0",evidence_summary="SYNTHETIC placeholder score for testing only",computed_date="2026-10-20",source_doc_id=SD("accreditation_list"))
add("refresh_status",run_id="SYN-RUN-001",started_at="2026-10-20T10:00:00Z",finished_at="2026-10-20T10:05:00Z",status="success",admission_year_detected=CUR,data_version_published="SYN-v1",message="SYNTHETIC")
add("data_version",data_version="SYN-v1",created_at="2026-10-20T10:05:00Z",is_last_known_good="TRUE",admission_year=CUR,row_count_summary="synthetic",notes="Synthetic test dataset")
for t,rs in rows.items():
    with open(os.path.join(OUT,t+".csv"),"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=[c["name"] for c in schema[t]["columns"]]); w.writeheader(); w.writerows(rs)
print({t:len(r) for t,r in rows.items()})
