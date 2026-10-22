"""Regenerates SCHEMA.md from schema.json. Run: python build_schema_md.py"""
import json, os
H=os.path.dirname(os.path.abspath(__file__))
S=json.load(open(os.path.join(H,"schema.json")))["tables"]
o=["# Database schema (Stage 3 draft, v0.3)\n",
"Each table is one CSV file now and one Google Sheet tab later (Stage 5). `database/schema.json` is the machine-readable version used by `validate_data.py`; this file is generated from it.\n",
"## Golden rules built into the schema",
"- **Vacancy is separate from intake.** `seat_intake` holds sanctioned/approved seats; `vacancies` holds only genuine vacancy positions. Vacancy rows must have `cap_round` III or IV and a source document of type `vacancy_position`. A vacancy can never exceed the sanctioned intake.",
"- **Missing means missing.** No row = \"Not available\". Never write 0 for unknown data, and never treat a missing hostel row as \"no hostel\".",
"- **Hostel availability is in `hostels`; hostel cost is in `fees`** (fee_type = hostel).",
"- **Provenance on every data row:** `source_doc_id` (points to `source_documents`), `retrieved_date`, `validation_status`.",
"- **Estimates are labelled:** `quality_indicators.is_estimate` must be TRUE.",
"- **Nothing is destroyed on change:** renames go to `college_name_history`; validity dates are kept for accreditation.",
"- **Stable IDs:** `college_code`, and `choice_code` (college code + branch code). Names are never used to join records.",
"- **Years** are written like `2025-26`; **dates** like `2026-10-20`; **booleans** `TRUE`/`FALSE`.\n",
"Columns marked * are required. Every table with provenance also has: source_doc_id*, retrieved_date, validation_status*, is_synthetic* (TRUE only for test data).\n"]
for n,t in S.items():
    o.append(f"## {n}\n{t['description']}\n\nKey: `{', '.join(t['primary_key'])}`"+(f" · Must be unique together: `{', '.join(t['unique'])}`" if t.get('unique') else "")+"\n")
    o.append("| Column | Type | Notes |\n|---|---|---|")
    for c in t["columns"]:
        if c["name"] in ("source_doc_id","retrieved_date","validation_status","is_synthetic") and n not in("source_documents","refresh_status","data_version"): continue
        note=[]
        if "enum" in c: note.append("one of: "+", ".join(c["enum"]))
        if "fk" in c: note.append("links to "+c["fk"])
        o.append(f"| {c['name']}{'*' if c['required'] else ''} | {c['type']} | {'; '.join(note)} |")
    o.append("")
o.append("## Known limits of this draft\n- Seat types (category codes) are PROVISIONAL and synthetic; the real list comes from CET Cell data (Stages 7-9).\n- Fee scope, district spelling variants and college-type values are free text for now; they will be normalised once real data is seen.\n- `college_name_history` and district-name history are minimal.")
open(os.path.join(H,"SCHEMA.md"),"w").write("\n".join(o))
