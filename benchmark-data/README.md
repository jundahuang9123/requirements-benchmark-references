# RQ1 external benchmark corpus

This folder evaluates **source evidence → metadata requirements**, and, where preserved,
**candidate requirements → consolidated requirements**. It is a new repository-root
folder beside `requirement-reuse-service/`; it does not change the application.

Acquisition snapshot: **2026-10-07**. Every corpus is **partial**. Complete coverage of a
published table is not complete reconstruction of the original elicitation process.
Published references are expert/project choices, not exhaustive truth. Curated JSON
representations are clearly labelled paraphrases and require independent review before
being used as quantitative gold.

## Cases and evaluation modes

| Case | Role | Raw evidence → requirements | Preconsolidation → consolidation | Reference scope / limitation |
| --- | --- | --- | --- | --- |
| [mobilityDCAT](mobilitydcat/README.md) | test case | Primary, partial historical reconstruction | Strongest case; preserved partner rows plus partial review/expert observations | All 40 Table 1 IDs; original report says 53 partner requirements but annex contains 60 labelled rows |
| [HealthDCAT](healthdcat/README.md) | test case | Heterogeneous-source case; partial 2023/2024 reconstruction | Partial curated TWG observation subset | 16 curated rationale requirements plus original D6.2; no complete official atomic gold list |
| [StatDCAT](statdcat/README.md) | development case | Partial standards-derived case; optional retrospective use-case variant | Not available | Seven requirement/resolution pairs; full licensed 2016 report retained |
| [GeoDCAT](geodcat/README.md) | test case | Partial standards/alignment case | Not available | Seven scoped alignment constraints; ISO documents citation-only |
| [JRC research](jrc-research/README.md) | development case | Small sanity/development case | Not available | Five explicitly enumerated core needs; private scientific stakeholder evidence missing |

The roles are those the curator stated on 12 November 2026
([`reference-sets-v3/case-roles/`](reference-sets-v3/case-roles/README.md)). EPOS, an exploratory sixth case
with no scored run, is in `../archive/benchmark-data/epos/` and is not one of the five cases.

## Structure

Each case has `input-raw/`, `reference-requirements/`, `provenance/`, and a README.
Mobility and Health additionally have `input-preconsolidation/`. Files in `provenance/citations/` are **URL/citation records,
not source-document content**. Original documents with unclear redistribution rights
are not committed; public facts may be represented by explicitly marked curator
synopses. Original copies retain their notices and are not relicensed by this repository.

- [`reference-sets-v3/`](reference-sets-v3/README.md): evaluator-only merged reference
  sets (version 3): atomic scoring units, DCAT-AP relation flags, and input-evidence labels
  for full and evidence-eligible recall. The v1 files in each case stay unchanged.
- [`runtime-inputs.json`](runtime-inputs.json): exact document allowlists for separate
  `raw` and `consolidation` runs. These are not workflow API request objects.
- [`BENCHMARK-METHODOLOGY.md`](BENCHMARK-METHODOLOGY.md): protocol, version controls,
  matching, coverage and splits.
- [`REFERENCE-COVERAGE-TEMPLATE.csv`](REFERENCE-COVERAGE-TEMPLATE.csv): pending
  independent review and evidence-coverage annotations; no support labels are assumed.
- [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md): attribution and reuse conditions,
  including NISO's noncommercial restriction.
- Each `provenance/manifest.json`: titles, original URLs, dates/versions, roles,
  explicit-input evidence, representation, limitations, licence, size and SHA-256.
- [`validate_corpus.py`](validate_corpus.py): offline inventory, role, hash and readability
  checks. [`VALIDATION-REPORT.json`](VALIDATION-REPORT.json) records the acquisition QA (of six cases, EPOS
  included).

**Never recursively import `benchmark-data/` into RAG or the workflow.** Copy only the
chosen allowlisted documents into a separate run directory. Do not expose the
allowlist itself, these READMEs, provenance, references or evaluation annotations to
extraction agents. Prior cross-domain standards (e.g. GeoDCAT as a mobility input) are
allowed where documented; the target profile and its consolidated answers are not.

## Verify locally

From the repository root:

```sh
python3 benchmark-data/validate_corpus.py
# EPOS, from the archive, as well:
python3 benchmark-data/validate_corpus.py --epos archive/benchmark-data/epos
# Full PDF parsing also requires pypdf:
python3 benchmark-data/validate_corpus.py --deep-pdf
```

The standard-library check validates JSON, UTF-8 text/HTML, SHA-256, PDF signatures
and trailers, all inventory paths and mode/role boundaries. The deep check reads every
PDF page and checks extractable text. Neither is a claim that every historical input,
every semantic paraphrase, or every inaccessible URL has been independently validated.
No evaluation run or measured workflow result is included here.
