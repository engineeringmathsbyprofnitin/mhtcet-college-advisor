# Stage 10a - which cutoff cells apply to which student

## What the documents prove (read from the real files)
- Official legend (printed on every State list): first letter G = General, L = Ladies; last letter H = Home University, O = Other than Home University, S = State Level. "Cut Off indicates State General Merit No.; figures in brackets indicate merit percentile."
- Seven sections exist. Seat code ends match the section: State Level -> S (also I/N for orphan/minority codes); the four home-university sections -> H or O; Minority -> MI; "Maharashtra State seats to All India candidates" -> S.
- Autonomous institutes (132 colleges) have State Level cells only; no H/O cells.
- Inside one round the key (course, section, seat code, stage) is unique: 0 repeated rows in all 7 lists.
- Stage labels I, II, VII, MH, I-Non PWD, I-Non Defence are NOT defined anywhere in the documents (searched the Round IV PDF and the web). VII exists from round II onward, never in round I. When two stages exist for the same seat, the later stage has the higher percentile in 854 of 1,133 cases.
- 1,847 seat cells appear in two sections in the same round (e.g. State Level and the All India-candidate section share one merit number): they are different candidate groups, not duplicates.

## Rules built (ingestion/eligibility.py, 12 tests)
For a Maharashtra-candidature student (home university, gender, category + flags EWS, TFWS, PWD, Defence, Orphan):
- State Level: applies to every Maharashtra student. Home University -> Home University and OHU -> HU sections: only if the student's home university equals the college's. OHU -> OHU and HU -> OHU sections: only if it differs. Autonomous institutes: State Level only. All India section: not for Maharashtra students.
- G seats: everyone. L seats: female only. OPEN seats: everyone. Category seats: only that category.
- EWS / TFWS / PWD / Defence / Orphan seats: only if the student says so.
- UNKNOWN (never matched automatically, reported): variant letters R, I, N, 2 on PWD/Defence/Orphan codes; Minority (MI) seats; any new section or seat code.

## Closing figure (provisional rule, owner may change)
Several stages can exist for one seat in a round. We keep every stage and take as the closing figure the LOWEST percentile over the stages present, with its stage recorded. Reason: the stage meanings are undefined and this is the lowest percentile at which the documents show the seat allotted.

## Assumptions to confirm
1. Reserved-category students may also use OPEN seats (already assumed earlier).
2. Lowest-percentile closing rule above.
3. Variants R/I/N and minority seats stay out of automatic matching for now.

## NOT verified
Meaning of stages; how the CET Cell treats the variant letters; whether All India (AI) candidates need a separate rule set (planned 10c).
