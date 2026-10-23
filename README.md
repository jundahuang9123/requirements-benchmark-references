# Requirements benchmark references

Curated reference requirements, source traceability, adjudication documentation and supporting source corpus for requirement-extraction benchmarks.

Imported from [PR #45](https://github.com/jundahuang9123/profile-requirements-extraction/pull/45) of `jundahuang9123/profile-requirements-extraction` on 23 October 2026, at source commit [`0444d9c3f876202719f6edfa433edc0422f79b20`](https://github.com/jundahuang9123/profile-requirements-extraction/commit/0444d9c3f876202719f6edfa433edc0422f79b20). The original `benchmark-data/` layout and all imported file bytes are preserved. `IMPORT-PROVENANCE.json` records the source and SHA-256 of every imported file. This repository starts with a snapshot; earlier source history remains in the linked repository.

## Start here

- [Merged reference sets v3](benchmark-data/reference-sets-v3/README.md): reference sets, atomic scoring units, source anchors and evidence labels.
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
```

See [import verification](IMPORT-VALIDATION.md): v3 and mock checks pass; the older corpus validator currently reports failures inherited from the source snapshot.

Install Poppler (`pdftotext`) to verify PDF quotations. Full PDF parsing by the corpus validator also requires `pypdf` and `--deep-pdf`.

Reference sets and evaluator annotations must stay outside extraction inputs, prompts and retrieval. The corpus is partial; AI evidence labels and provisional adjudications are not independent human validation. See the linked methodology for limitations and development-case exposure.

## Attribution and reuse

Source documents retain their individual notices and reuse conditions. See [third-party notices](benchmark-data/THIRD-PARTY-NOTICES.md) and each case's provenance manifest. No blanket licence overrides those terms.
