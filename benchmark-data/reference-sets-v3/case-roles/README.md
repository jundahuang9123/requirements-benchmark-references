# Roles of the five cases (12 November 2026)

Which cases are development cases and which are test cases, as the curator stated it on 12 November 2026. The record corrects
earlier wording in this folder that called HealthDCAT-AP a development case.

## Record: `statement-2026-11-12.json`

The curator's statement, the restriction it names, the role of each case with its basis, what the files record about each
case before the workflow was frozen, every corrected passage with its wording before and after, what was left as it was, and
the limits.

## The roles

| Case | Role | Before the workflow was frozen |
|---|---|---|
| mobilityDCAT-AP | test case | outputs were looked at, without the reference |
| GeoDCAT-AP | test case | not run |
| HealthDCAT-AP | test case | outputs were looked at under the curator's restriction; one early run was compared with the 16 rows collected by then |
| StatDCAT-AP | development case | the workflow was developed on it; outputs were compared with the reference |
| DCAT-AP-JRC | development case | the workflow was developed on it; outputs were compared with the reference |

The restriction: no reference content goes into the workflow, and nothing is implemented for a single case.

## What was corrected

- `../README.md` said under "Not done" that "Health, Stat and JRC are development cases whose outputs had been viewed before
  this version". The curator's statement: looking at HealthDCAT-AP was allowed under the restriction, so that the case does
  not become a development case. The line overstated his decision. It now names Stat and JRC as the development cases and
  keeps the fact that outputs of all three had been viewed before this version.
- The case headings of the supplement said "inspected during development: reference" for HealthDCAT-AP, as for the two
  development cases, and Table 2 gave it their dagger. The headings now say test case or development case, and the dagger
  marks the two development cases (`../supplement/make_tables.py`; files regenerated, PDF rebuilt).
- Two descriptions named mobilityDCAT-AP and GeoDCAT-AP as the cases "without output-to-reference comparison during
  development" (`../supplement/README.md`, `../evidence-review/README.md`). They now name the two cases as two of the three
  test cases. `appendix-test-cases.tex` keeps its name and its content, the scored atoms of these two cases.
- The curator had asked earlier that the cases not be sorted into development and test cases. That request was not recorded
  here; trace steps M12 and M13 record what was done on 7 November.

## What agrees and stays

`../../BENCHMARK-METHODOLOGY.md` ("Train, development and held-out use") has named DCAT-AP-JRC and StatDCAT-AP as the
development cases since 16 October 2026 and reserves HealthDCAT-AP and GeoDCAT-AP as tests. The open gap G-061 of the trace
("The held-out cases are inconsistent") is the contradiction between that section and the README line corrected here. This
record answers it; the backfill files are not edited.

## In the paper

The main analysis is over the three test cases, and the two development cases are reported apart. The curator decided this on
12 November 2026, after the results were frozen on 11 November. Their role as development cases is recorded in the methodology
since 16 October.

## Limits

- One person's statement about his own decisions; no second source.
- The dates and the runs of the inspections are not recorded in this repository. The comparison of one HealthDCAT-AP run with
  16 rows is in session notes of 19 October 2026 outside the repository.
- How the workflow changed during its development is recorded in the workflow's own repository, not here.
- A case whose outputs were looked at is not an untouched case. The record says what was seen; it does not claim that nothing
  was.
