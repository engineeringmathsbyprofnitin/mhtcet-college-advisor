"""Builds database/schema.json and header-only CSV templates from one compact spec.
Run: python build_schema.py   (only needed when the schema changes)"""
import json, csv, os
Y = "year"
PROV = [("source_doc_id","str",True,{"fk":"source_documents.doc_id"}),
        ("retrieved_date","date",False,{}),
        ("validation_status","str",True,{"enum":["pending","validated","rejected"]}),
        ("is_synthetic","bool",True,{})]
def C(name,typ="str",req=False,**kw): return (name,typ,req,kw)
ROUNDS=["I","II","III","IV"]
T = {
 "colleges": dict(pk=["college_code"], cols=[C("college_code","str",True),C("college_name","str",True),C("district","str",True),C("city"),C("college_type"),
    C("status","str",True,enum=["active","closed","renamed"]),C("previous_college_code"),C("college_website","url"),C("autonomy_status","str",False,enum=["autonomous","non_autonomous","unknown"]),C("campus_area_acres","float")], prov=True,
    desc="One row per college, keyed by its official college code. Never merge colleges by name similarity."),
 "college_name_history": dict(pk=["college_code","valid_from_year"], cols=[C("college_code","str",True,fk="colleges.college_code"),C("college_name","str",True),C("valid_from_year",Y,True),C("valid_to_year",Y)], prov=True,
    desc="Keeps old names so renames never destroy history."),
 "branches": dict(pk=["choice_code"], cols=[C("choice_code","str",True),C("college_code","str",True,fk="colleges.college_code"),C("branch_code","str",True),C("branch_name","str",True),
    C("branch_group","str",False),C("valid_from_year",Y),C("valid_to_year",Y)], prov=True,
    desc="One row per college-branch (a 'choice'). choice_code is the stable identifier used everywhere else."),
 "seat_intake": dict(pk=["intake_id"], cols=[C("intake_id","str",True),C("choice_code","str",True,fk="branches.choice_code"),C("academic_year",Y,True),
    C("intake_type","str",True,enum=["sanctioned","approved"]),C("seats","int",True)], prov=True,
    desc="Sanctioned/approved intake. This is NOT vacancy and must never be used as vacancy."),
 "seat_types": dict(pk=["seat_type_code"], cols=[C("seat_type_code","str",True),C("candidate_type","str",True),C("category","str",True),C("gender_scope","str"),
    C("seat_level","str"),C("description"),C("is_provisional","bool",True)], prov=False,
    desc="Reference list of official seat/cutoff groups. Lets the engine match a student's category, gender and candidate type to the right cutoff list."),
 "historical_cutoffs": dict(pk=["cutoff_id"], unique=["choice_code","admission_year","cap_round","seat_type_code"], cols=[C("cutoff_id","str",True),C("choice_code","str",True,fk="branches.choice_code"),
    C("admission_year",Y,True),C("cap_round","str",True,enum=ROUNDS),C("seat_type_code","str",True,fk="seat_types.seat_type_code"),C("cutoff_percentile","percentile",True),C("cutoff_rank","int"),C("published_date","date")], prov=True,
    desc="Cutoffs of completed admission years."),
 "current_cutoffs": dict(pk=["cutoff_id"], unique=["choice_code","admission_year","cap_round","seat_type_code"], cols=[C("cutoff_id","str",True),C("choice_code","str",True,fk="branches.choice_code"),
    C("admission_year",Y,True),C("cap_round","str",True,enum=ROUNDS),C("seat_type_code","str",True,fk="seat_types.seat_type_code"),C("cutoff_percentile","percentile",True),C("cutoff_rank","int"),C("published_date","date")], prov=True,
    desc="Cutoffs of the current admission year, one row per published CAP round."),
 "vacancies": dict(pk=["vacancy_id"], unique=["choice_code","admission_year","cap_round","seat_type_code"], cols=[C("vacancy_id","str",True),C("choice_code","str",True,fk="branches.choice_code"),C("admission_year",Y,True),
    C("cap_round","str",True,enum=["III","IV"]),C("seat_type_code","str",True),C("vacancy_count","int",True),C("published_date","date")], prov=True,
    desc="Genuine vacancy positions ONLY. Round must be III or IV and the source document must be of type vacancy_position. seat_type_code may be 'ALL' for a branch total."),
 "fees": dict(pk=["fee_id"], cols=[C("fee_id","str",True),C("college_code","str",True,fk="colleges.college_code"),C("choice_code","str",False,fk="branches.choice_code"),C("academic_year",Y,True),
    C("fee_type","str",True,enum=["tuition","total","hostel","other"]),C("annual_fee_inr","int",True),C("fee_scope")], prov=True,
    desc="Fees with an explicit type, so tuition is never presented as total cost."),
 "accreditation": dict(pk=["accreditation_id"], cols=[C("accreditation_id","str",True),C("college_code","str",True,fk="colleges.college_code"),C("choice_code","str",False,fk="branches.choice_code"),
    C("body","str",True,enum=["NBA","NAAC"]),C("scope","str",True,enum=["program","institution"]),C("status","str",True,enum=["accredited","not_accredited","expired","unknown"]),
    C("grade"),C("valid_from","date"),C("valid_to","date")], prov=True,
    desc="NBA applies per program (choice_code); NAAC per institution. Validity dates are stored so expired grades can be flagged."),
 "placements": dict(pk=["placement_id"], cols=[C("placement_id","str",True),C("college_code","str",True,fk="colleges.college_code"),C("choice_code","str",False,fk="branches.choice_code"),
    C("placement_year",Y,True),C("metric","str",True,enum=["placement_percent","median_package_lpa","average_package_lpa","highest_package_lpa","lowest_package_lpa","students_eligible","students_placed","companies_visited"]),
    C("value","float",True),C("scope","str",True,enum=["institution","branch"])], prov=True,
    desc="Placement facts with year, metric and scope."),
 "hostels": dict(pk=["hostel_id"], cols=[C("hostel_id","str",True),C("college_code","str",True,fk="colleges.college_code"),C("hostel_for","str",True,enum=["boys","girls","both"]),
    C("availability","str",True,enum=["available","limited","not_available","unknown"]),C("hostel_type","str",False,enum=["on_campus","off_campus"]),C("seat_capacity","int"),C("notes")], prov=True,
    desc="Whether a college offers hostel accommodation, for whom, and capacity. The hostel FEE is stored in the fees table (fee_type = hostel)."),
 "quality_indicators": dict(pk=["indicator_id"], cols=[C("indicator_id","str",True),C("college_code","str",True,fk="colleges.college_code"),C("indicator","str",True,enum=["teaching","infrastructure","placement"]),
    C("score_0_10","score10",True),C("is_estimate","bool",True),C("method_version","str",True),C("evidence_summary","str",True),C("computed_date","date")], prov=True,
    desc="System-calculated 0-10 estimates (never official). is_estimate must be TRUE and the method documented."),
 "source_documents": dict(pk=["doc_id"], cols=[C("doc_id","str",True),C("source_name","str",True),C("source_url","str",True),C("filename","str",True),C("sha256"),C("admission_year",Y),
    C("doc_type","str",True,enum=["cutoff","vacancy_position","seat_matrix","fee_notice","accreditation_list","placement_report","college_list","other"]),
    C("cap_round","str",False,enum=ROUNDS),C("published_date","date"),C("retrieved_date","date"),C("validation_status","str",True,enum=["pending","validated","rejected"]),C("is_synthetic","bool",True)], prov=False,
    desc="Every downloaded/entered source file, with URL, checksum and dates."),
 "refresh_status": dict(pk=["run_id"], cols=[C("run_id","str",True),C("started_at","str",True),C("finished_at","str"),C("status","str",True,enum=["success","failed","skipped","no_new_data"]),
    C("admission_year_detected",Y),C("data_version_published","str"),C("message"),C("is_synthetic","bool",True)], prov=False,
    desc="One row per update attempt. Used to show 'last checked' and 'last successful update'."),
 "data_version": dict(pk=["data_version"], cols=[C("data_version","str",True),C("created_at","str",True),C("is_last_known_good","bool",True),C("admission_year",Y),C("row_count_summary"),C("notes"),C("is_synthetic","bool",True)], prov=False,
    desc="Published dataset versions; exactly one is the last-known-good."),
}
schema={}
for name,t in T.items():
    cols=[dict(name=n,type=ty,required=rq,**kw) for (n,ty,rq,kw) in t["cols"]]
    if t["prov"]: cols+= [dict(name=n,type=ty,required=rq,**kw) for (n,ty,rq,kw) in PROV]
    schema[name]=dict(description=t["desc"],primary_key=t["pk"],unique=t.get("unique"),columns=cols)
json.dump({"schema_version":"0.1","note":"Stage 3 draft. Enums for categories/branches will be refined from official data.","tables":schema},open("schema.json","w"),indent=1)
os.makedirs("templates",exist_ok=True)
for name,t in schema.items():
    with open(f"templates/{name}.csv","w",newline="") as f: csv.writer(f).writerow([c["name"] for c in t["columns"]])
print(len(schema),"tables")
