# Database schema (Stage 3 draft, v0.2)

Each table is one CSV file now and one Google Sheet tab later (Stage 5). `database/schema.json` is the machine-readable version used by `validate_data.py`; this file is generated from it.

## Golden rules built into the schema
- **Vacancy is separate from intake.** `seat_intake` holds sanctioned/approved seats; `vacancies` holds only genuine vacancy positions. Vacancy rows must have `cap_round` III or IV and a source document of type `vacancy_position`. A vacancy can never exceed the sanctioned intake.
- **Missing means missing.** No row = "Not available". Never write 0 for unknown data, and never treat a missing hostel row as "no hostel".
- **Hostel availability is in `hostels`; hostel cost is in `fees`** (fee_type = hostel).
- **Provenance on every data row:** `source_doc_id` (points to `source_documents`), `retrieved_date`, `validation_status`.
- **Estimates are labelled:** `quality_indicators.is_estimate` must be TRUE.
- **Nothing is destroyed on change:** renames go to `college_name_history`; validity dates are kept for accreditation.
- **Stable IDs:** `college_code`, and `choice_code` (college code + branch code). Names are never used to join records.
- **Years** are written like `2025-26`; **dates** like `2026-10-20`; **booleans** `TRUE`/`FALSE`.

Columns marked * are required. Every table with provenance also has: source_doc_id*, retrieved_date, validation_status*, is_synthetic* (TRUE only for test data).

## colleges
One row per college, keyed by its official college code. Never merge colleges by name similarity.

Key: `college_code`

| Column | Type | Notes |
|---|---|---|
| college_code* | str |  |
| college_name* | str |  |
| district* | str |  |
| city | str |  |
| college_type | str |  |
| status* | str | one of: active, closed, renamed |
| previous_college_code | str |  |

## college_name_history
Keeps old names so renames never destroy history.

Key: `college_code, valid_from_year`

| Column | Type | Notes |
|---|---|---|
| college_code* | str | links to colleges.college_code |
| college_name* | str |  |
| valid_from_year* | year |  |
| valid_to_year | year |  |

## branches
One row per college-branch (a 'choice'). choice_code is the stable identifier used everywhere else.

Key: `choice_code`

| Column | Type | Notes |
|---|---|---|
| choice_code* | str |  |
| college_code* | str | links to colleges.college_code |
| branch_code* | str |  |
| branch_name* | str |  |
| branch_group | str |  |
| valid_from_year | year |  |
| valid_to_year | year |  |

## seat_intake
Sanctioned/approved intake. This is NOT vacancy and must never be used as vacancy.

Key: `intake_id`

| Column | Type | Notes |
|---|---|---|
| intake_id* | str |  |
| choice_code* | str | links to branches.choice_code |
| academic_year* | year |  |
| intake_type* | str | one of: sanctioned, approved |
| seats* | int |  |

## seat_types
Reference list of official seat/cutoff groups. Lets the engine match a student's category, gender and candidate type to the right cutoff list.

Key: `seat_type_code`

| Column | Type | Notes |
|---|---|---|
| seat_type_code* | str |  |
| candidate_type* | str |  |
| category* | str |  |
| gender_scope | str |  |
| seat_level | str |  |
| description | str |  |
| is_provisional* | bool |  |

## historical_cutoffs
Cutoffs of completed admission years.

Key: `cutoff_id` · Must be unique together: `choice_code, admission_year, cap_round, seat_type_code`

| Column | Type | Notes |
|---|---|---|
| cutoff_id* | str |  |
| choice_code* | str | links to branches.choice_code |
| admission_year* | year |  |
| cap_round* | str | one of: I, II, III, IV |
| seat_type_code* | str | links to seat_types.seat_type_code |
| cutoff_percentile* | percentile |  |
| cutoff_rank | int |  |
| published_date | date |  |

## current_cutoffs
Cutoffs of the current admission year, one row per published CAP round.

Key: `cutoff_id` · Must be unique together: `choice_code, admission_year, cap_round, seat_type_code`

| Column | Type | Notes |
|---|---|---|
| cutoff_id* | str |  |
| choice_code* | str | links to branches.choice_code |
| admission_year* | year |  |
| cap_round* | str | one of: I, II, III, IV |
| seat_type_code* | str | links to seat_types.seat_type_code |
| cutoff_percentile* | percentile |  |
| cutoff_rank | int |  |
| published_date | date |  |

## vacancies
Genuine vacancy positions ONLY. Round must be III or IV and the source document must be of type vacancy_position. seat_type_code may be 'ALL' for a branch total.

Key: `vacancy_id` · Must be unique together: `choice_code, admission_year, cap_round, seat_type_code`

| Column | Type | Notes |
|---|---|---|
| vacancy_id* | str |  |
| choice_code* | str | links to branches.choice_code |
| admission_year* | year |  |
| cap_round* | str | one of: III, IV |
| seat_type_code* | str |  |
| vacancy_count* | int |  |
| published_date | date |  |

## fees
Fees with an explicit type, so tuition is never presented as total cost.

Key: `fee_id`

| Column | Type | Notes |
|---|---|---|
| fee_id* | str |  |
| college_code* | str | links to colleges.college_code |
| choice_code | str | links to branches.choice_code |
| academic_year* | year |  |
| fee_type* | str | one of: tuition, total, hostel, other |
| annual_fee_inr* | int |  |
| fee_scope | str |  |

## accreditation
NBA applies per program (choice_code); NAAC per institution. Validity dates are stored so expired grades can be flagged.

Key: `accreditation_id`

| Column | Type | Notes |
|---|---|---|
| accreditation_id* | str |  |
| college_code* | str | links to colleges.college_code |
| choice_code | str | links to branches.choice_code |
| body* | str | one of: NBA, NAAC |
| scope* | str | one of: program, institution |
| status* | str | one of: accredited, not_accredited, expired, unknown |
| grade | str |  |
| valid_from | date |  |
| valid_to | date |  |

## placements
Placement facts with year, metric and scope.

Key: `placement_id`

| Column | Type | Notes |
|---|---|---|
| placement_id* | str |  |
| college_code* | str | links to colleges.college_code |
| choice_code | str | links to branches.choice_code |
| placement_year* | year |  |
| metric* | str | one of: placement_percent, median_package_lpa, average_package_lpa, highest_package_lpa, lowest_package_lpa, students_eligible, students_placed, companies_visited |
| value* | float |  |
| scope* | str | one of: institution, branch |

## hostels
Whether a college offers hostel accommodation, for whom, and capacity. The hostel FEE is stored in the fees table (fee_type = hostel).

Key: `hostel_id`

| Column | Type | Notes |
|---|---|---|
| hostel_id* | str |  |
| college_code* | str | links to colleges.college_code |
| hostel_for* | str | one of: boys, girls, both |
| availability* | str | one of: available, limited, not_available, unknown |
| hostel_type | str | one of: on_campus, off_campus |
| seat_capacity | int |  |
| notes | str |  |

## quality_indicators
System-calculated 0-10 estimates (never official). is_estimate must be TRUE and the method documented.

Key: `indicator_id`

| Column | Type | Notes |
|---|---|---|
| indicator_id* | str |  |
| college_code* | str | links to colleges.college_code |
| indicator* | str | one of: teaching, infrastructure, placement |
| score_0_10* | score10 |  |
| is_estimate* | bool |  |
| method_version* | str |  |
| evidence_summary* | str |  |
| computed_date | date |  |

## source_documents
Every downloaded/entered source file, with URL, checksum and dates.

Key: `doc_id`

| Column | Type | Notes |
|---|---|---|
| doc_id* | str |  |
| source_name* | str |  |
| source_url* | str |  |
| filename* | str |  |
| sha256 | str |  |
| admission_year | year |  |
| doc_type* | str | one of: cutoff, vacancy_position, seat_matrix, fee_notice, accreditation_list, placement_report, college_list, other |
| cap_round | str | one of: I, II, III, IV |
| published_date | date |  |
| retrieved_date | date |  |
| validation_status* | str | one of: pending, validated, rejected |
| is_synthetic* | bool |  |

## refresh_status
One row per update attempt. Used to show 'last checked' and 'last successful update'.

Key: `run_id`

| Column | Type | Notes |
|---|---|---|
| run_id* | str |  |
| started_at* | str |  |
| finished_at | str |  |
| status* | str | one of: success, failed, skipped, no_new_data |
| admission_year_detected | year |  |
| data_version_published | str |  |
| message | str |  |
| is_synthetic* | bool |  |

## data_version
Published dataset versions; exactly one is the last-known-good.

Key: `data_version`

| Column | Type | Notes |
|---|---|---|
| data_version* | str |  |
| created_at* | str |  |
| is_last_known_good* | bool |  |
| admission_year | year |  |
| row_count_summary | str |  |
| notes | str |  |
| is_synthetic* | bool |  |

## Known limits of this draft
- Seat types (category codes) are PROVISIONAL and synthetic; the real list comes from CET Cell data (Stages 7-9).
- Fee scope, district spelling variants and college-type values are free text for now; they will be normalised once real data is seen.
- `college_name_history` and district-name history are minimal.