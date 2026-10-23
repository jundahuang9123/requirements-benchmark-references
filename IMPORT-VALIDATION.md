# Import verification, 23 October 2026

Source PR #45 head: `0444d9c3f876202719f6edfa433edc0422f79b20`.

- All 223 imported files match the source snapshot; SHA-256 values are in `IMPORT-PROVENANCE.json`.
- v3 validation passed with Poppler: 204 local source-anchor quotes and 1,320 evidence quotes verified; 116 live-web anchor quotes are not locally verified. Full output: `IMPORT-V3-VALIDATION.json`.
- Mock benchmark independent recomputation (`mock-benchmark/verify.py`): `problems: none`.
- The older `benchmark-data/validate_corpus.py` failed. Its output is retained in `IMPORT-CORPUS-VALIDATION.json`. It reports duplicate runtime paths as single characters, three Mobility reference/context leakage flags, and an unregistered `mobilitydcat/use-cases.json`. These checks run against the exact imported source bytes; the transfer did not create or repair the findings. Treat this validator as requiring follow-up before claiming whole-corpus validation.

Passing v3 structural and quote checks is not human adjudication, a completeness guarantee, or an approval for quantitative evaluation. No imported benchmark data or scores were changed during transfer.
