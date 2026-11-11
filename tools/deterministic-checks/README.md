# Deterministic checks beside the model judgments (RQ1 benchmark)

Screens and robustness checks that come from no LLM family: fixed text rules and one fixed NLI model. They flag items
for a person and test whether the paper's comparisons hold under a different matcher. They never change a label, an
atom, a run or a reported figure; a flag is a lead, not a verdict. Spec: the "deterministic checks" plan of
11 Nov 2026, summarised in each part's README.

Everything here reads the references at `524f65b` and, for Part C, the frozen labels of the run store
(`reports/benchmark-tools/final-scoring/saved/label-freeze-2026-11-11.json`), and writes new files only. No LLM calls.
Parts A and B need only this repo; Part C needs the run store checked out next to it (`DC_RUNSTORE`).

| Folder | What |
|---|---|
| `dc/` | The shared code: paths and provenance (`paths.py`), the text rules (`textrules.py`), the atoms and their contexts (`atoms.py`), the pools, runs and final labels (`pools.py`), the NLI wrapper (`nli.py`), Part C's relation mapping, separation rule and kappa (`relation.py`) |
| `part_a.py` | Part A, atom fidelity: each atom against its reference passage and its pre-standard-form wording |
| `part_b.py` | Part B, evidence labels: each scored atom against the input passages its label cites |
| `part_c.py` | Part C, matching: every pool statement against the atoms of N with the NLI model; the paper's comparisons under that matcher |
| `make_sheet.py` | The review sheet for the first author (Part A flags + unmarked sample; Part B disagreements), and its key in a separate file |
| `rerun_check.sh` | The rerun test: a part twice, outputs compared byte for byte |
| `tests/` | Unit tests of the text rules and of Part C's relation mapping, on invented sentences |
| `part-*/` | Each part's outputs (`out/`) and its README: what was run and how the results read |

## Fixed before anything was run

- **NLI model:** `cross-encoder/nli-deberta-v3-base`, revision `6c749ce3425cd33b46d187e45b92bbf96ee12ec7`. CPU, `torch.manual_seed(0)`,
  4 threads, argmax over {entailment, neutral, contradiction}, no threshold; the premise is truncated first at 512 tokens.
- **Second model, sensitivity only:** `MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli`, revision `b3546ea6b0346eb6f8d5d68b13c7dc6d0376b3d7`.
  The first model is the reported one.
- **Prefilter (Part C, large cases only):** `sentence-transformers/all-mpnet-base-v2`, revision `e8c3b32edf5434bc2275fc9bab85f82640a19130`.
- Every output's `run-record.json` names the model revisions, the repo commits and the sha256 of every input file read.
- Reading of each part: in its docstring and README, written before the run.

## How to run

```bash
export HF_HOME=<cache that holds the pinned models> HF_HUB_OFFLINE=1
python3 -I -B -m pytest -q -p no:cacheprovider tests
python3 -I part_a.py --out part-a-atom-fidelity/out --second-model --log <scratch>/part-a.log
python3 -I part_b.py --out part-b-evidence-labels/out --second-model --log <scratch>/part-b.log
python3 -I part_c.py --out part-c-matching/out/main --log <scratch>/part-c.log
python3 -I part_c.py --out part-c-matching/out/second --model second --log <scratch>/part-c-second.log
python3 -I make_sheet.py --part-a part-a-atom-fidelity/out --part-b part-b-evidence-labels/out --out review
./rerun_check.sh part_a.py <scratch> --second-model      # and part_b.py, part_c.py
```

Paths: `DC_REFS` (references checkout), `DC_RUNSTORE`, `DC_PIPELINE`, `RQ1_FINAL_WORK` (the unpacked `work/`).
Python 3 with `torch` (CPU), `transformers`, `sentence-transformers`, `openpyxl`, `pytest`; Poppler's `pdftotext`.

## Separation

Count-only tables (`counts.json`, `figures.json`, `separation.json`, `agreement.json`) may go to the paper chat and the
project docs. `atoms.json`, `pairs-*.json` and the review sheet carry atom and need text with flags and labels: they stay
here and go to the first author directly, never into project docs.
