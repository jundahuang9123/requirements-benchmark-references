# Import verification, 23 October 2026

Source snapshot: `import-snapshot` (upstream identifiers withheld).

- The initial import matched all 223 source files. After sanitization, `IMPORT-PROVENANCE.json` records hashes of the sanitized files.
- v3 validation passed with Poppler: 204 local source-anchor quotes and 1,320 evidence quotes verified; 116 live-web anchor quotes are not locally verified. Full output: `IMPORT-V3-VALIDATION.json`.
- Mock benchmark independent recomputation (`mock-benchmark/verify.py`): `problems: none`.
- The older `benchmark-data/validate_corpus.py` failed. Its output is retained in `IMPORT-CORPUS-VALIDATION.json`. It reports duplicate runtime paths as single characters, three Mobility reference/context leakage flags, and an unregistered `mobilitydcat/use-cases.json`. This result records the original import; the transfer did not create or repair the findings. Treat this validator as requiring follow-up before claiming whole-corpus validation.

Passing v3 structural and quote checks is not human adjudication, a completeness guarantee, or an approval for quantitative evaluation. Anonymization changes attribution and provenance metadata; requirement statements, source evidence and numeric scores are preserved.
