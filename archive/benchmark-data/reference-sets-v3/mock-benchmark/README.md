# Mock benchmark, 23 October 2026

A dry run of the scoring protocol on the saved development runs (JRC and StatDCAT-AP, discussion v6 to v11), scored only on atoms that the staged raw inputs support. Machine-made: two blind Claude reviewers and a Claude adjudicator, no people. Not a test result.

- `SUMMARY.md`: results. `METHOD.md`: runs, selection, pair labels, scores.
- `runs.json`: the run outputs read from the workbench API (hash-checked).
- `judge/`: the reviewers' protocol, the packets they saw and their outputs. The packets were built on 22 October from v3 at `pre-adjudication-snapshot`; `build_pools.py` refuses to overwrite them without `--force`.
- `out/`: results computed against v3 at `adjudicated-snapshot` (with the 23 October adjudication).

Rerun from this folder: `python3 score.py && python3 verify.py && RQ1_REF_COMMIT='commit adjudicated-snapshot' python3 make_report.py`.
