# Requirements benchmark references

Curated reference requirements, source traceability, adjudication documentation and supporting source corpus for requirement-extraction benchmarks.

This standalone corpus combines independently collected requirement sets, source checks and provisional adjudication. The original `benchmark-data/` layout is retained. Curator identifiers and upstream repository identifiers have been replaced with neutral labels for later anonymous distribution. `IMPORT-PROVENANCE.json` records integrity hashes for the sanitized files.

See [anonymous export instructions](ANONYMIZATION.md) to create a history-free copy for a separate repository. The current hosting account and earlier Git commits are identifiable.

## Start here

- [Merged reference sets v3](benchmark-data/reference-sets-v3/README.md): reference sets, atomic scoring units, source anchors and evidence labels.
- [Standard form of the atom statements](benchmark-data/reference-sets-v3/standard-form/README.md) and [atom types](benchmark-data/reference-sets-v3/ATOM-TYPES.md): how every atom is worded, how its type (content, profile, system) was assigned, and the owner's review of each batch.
- [Input-label review, 1 November 2026](docs/reviews/2026-11-01-label-review.md): assistant recommendations for all 196 scored atoms, with the original labels retained. These recommendations have not been applied to benchmark labels or scores.
- [Evidence-label adjudication, 3 November 2026](benchmark-data/reference-sets-v3/evidence-review/README.md): the 22 October AI labels of the 196 scored atoms reviewed by two independent AI annotators (one blind) and adjudicated by the owner; applied as `input_evidence.human_review` and to `atoms-review.csv`. Claude's blind review table: [docs/reviews/2026-11-01-claude-blind-review.csv](docs/reviews/2026-11-01-claude-blind-review.csv).
- [Corpus guide](benchmark-data/README.md) and [methodology](benchmark-data/BENCHMARK-METHODOLOGY.md).
- [Review and provisional adjudication](benchmark-data/reference-sets-v3/CODEX-REVIEW-2026-10-23.md).
- [Supplement tables and PDF](benchmark-data/reference-sets-v3/supplement/README.md).
- [Mock benchmark](benchmark-data/reference-sets-v3/mock-benchmark/README.md): development exercise using machine reviewers.
- [Build history](benchmark-data/reference-sets-v3/history/README.md).

## Validation

Run from this repository root:

```sh
python3 benchmark-data/validate_corpus.py
python3 benchmark-data/reference-sets-v3/validate_v3.py
(cd benchmark-data/reference-sets-v3/mock-benchmark && python3 verify.py)
python3 -B tools/trace/check_backfill.py
```

See the archived [import verification](docs/import/IMPORT-VALIDATION.md): v3 and mock checks pass; the older corpus validator currently reports failures inherited from the source snapshot. These historical reports are not a current whole-corpus approval.

The trace checker requires the published `ref-trace-baseline` tag and its history. Use a full clone with tags (or `git fetch --tags` in an existing clone). Historical trace locators resolve against that baseline, even when a report has since moved. The history-free anonymous export has a more limited verification scope; see [anonymous export instructions](ANONYMIZATION.md).

Install Poppler (`pdftotext`) to verify PDF quotations. Full PDF parsing by the corpus validator also requires `pypdf` and `--deep-pdf`.

Reference sets and evaluator annotations must stay outside extraction inputs, prompts and retrieval. The corpus is partial; AI evidence labels and provisional adjudications are not independent human validation. See the linked methodology for limitations and development-case exposure.

The historical sets, raw label outputs, provisional adjudications, trace records and mock exercise are retained for reproducibility. The mock results predate the standardized statements and are a historical development exercise, not new results for the revised wording. Archived import reports live under `docs/import/`; current benchmark files and their integrity manifest retain their established paths.

## Attribution and reuse

Source documents retain their individual notices and reuse conditions. See [third-party notices](benchmark-data/THIRD-PARTY-NOTICES.md) and each case's provenance manifest. No blanket licence overrides those terms.
