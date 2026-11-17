# Archive

Kept for the record; not used by the paper. Moved here unchanged (same paths below `archive/`) on 15 and 17 Nov 2026.
The export (`tools/export_anonymous.py`) leaves the archive out, and no check of the kept part reads it.

| Path | What |
|---|---|
| `benchmark-data/reference-sets-v3/mock-benchmark/` | The mock benchmark of 23 October (development cases, machine reviewers); its check runs from here with `RQ1_REF` set to `benchmark-data/reference-sets-v3` (see `../README.md`) |
| `benchmark-data/epos/` | EPOS, an exploratory sixth case with no scored run; `python3 benchmark-data/validate_corpus.py --epos archive/benchmark-data/epos` checks it with the five cases |
| `docs/import/` | The import verification reports of the corpus |

`IMPORT-PROVENANCE.json` keeps the import paths of the moved files under `benchmark-data/`; the export check finds them
here, unchanged. Kept in place although the paper does not use it, because the trace checker reads it:
`benchmark-data/reference-sets-v3/CODEX-REVIEW-2026-10-23.md`. `docs/reviews/` stays because the evidence-label
adjudication cites its two tables.
