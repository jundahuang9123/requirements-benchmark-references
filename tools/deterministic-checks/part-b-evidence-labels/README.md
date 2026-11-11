# Part B. Evidence labels: do the cited input passages state the atom?

Question: the denominators (187 atoms stated at least in part by the raw inputs, 128 stated in full; decision of 9 Nov
2026) rest on the adjudicated `input_evidence.human_review.raw_label` of each scored atom. Do the passages each label
cites support it? A check of the labels' direction only: the rule of 3 Nov (a bare mention counts as stating) is more
lenient than entailment, so some supported atoms without entailment are expected.

## What was run (`../part_b.py`)

The 196 scored atoms at `524f65b` and the 751 passages stored under `input_evidence.raw.sources` (none truncated).
For each passage: N1 with the passage as premise and the atom statement as hypothesis (the same pinned NLI model as
Part A: `cross-encoder/nli-deberta-v3-base`, revision `6c749ce3`, argmax, no threshold); also N1 with the passages joined
in stored order, and T1 (content words of the atom not in the joined passages).

| Adjudicated label | Expected (fixed before the run) | Disagreement |
|---|---|---|
| supported | entailment from at least one passage or from the passages joined | `supported_not_entailed` |
| partial | no full entailment from any passage or the joined passages | `partial_entailed` |
| unsupported | no passage | `unsupported_with_passages` |

Supported atoms the adjudication filed under "rule 2: bare mention" are counted apart. Rerun test: two runs, outputs
byte-identical.

## Results (`out/counts.json`; per atom and passage `out/atoms.json`)

| | atoms | supported | not entailed | of which bare mention | partial | entailed | unsupported | with passages | T1 flags sup / part | disagreements |
|---|---|---|---|---|---|---|---|---|---|---|
| all | 196 | 128 | 35 | 1 | 59 | 15 | 9 | 1 | 39 / 33 | 51 |
| JRC | 17 | 4 | 1 | 0 | 12 | 3 | 1 | 0 | 2 / 7 | 4 |
| Stat | 14 | 4 | 1 | 0 | 6 | 1 | 4 | 0 | 1 / 0 | 2 |
| Geo | 37 | 37 | 6 | 0 | 0 | 0 | 0 | 0 | 7 / 0 | 6 |
| Health | 89 | 53 | 20 | 1 | 32 | 9 | 4 | 1 | 23 / 19 | 30 |
| Mobility | 39 | 30 | 7 | 0 | 9 | 2 | 0 | 0 | 6 / 7 | 9 |

Six passages are read as contradicting their atom. Second model (`MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli`,
revision `b3546ea6`): 44 disagreements, 39 atoms change between the two models (`counts.json: second_model`).

How this reads:
- The model agrees with 145 of the 196 labels (74%): 93 of 128 supported atoms have an entailing passage, 44 of 59
  partial atoms have none, 8 of 9 unsupported atoms cite nothing.
- 35 supported atoms have no passage the model reads as stating them: where the denominator could be too generous.
  Only one is a "bare mention" case, so the lenient rule does not explain them; most are the model wanting the passage
  to say the whole atom in the atom's words (a passage that defines the property, e.g. `dct:title`, does not entail
  "users can know the title of every dataset" in NLI terms).
- 15 partial atoms have a passage the model reads as stating them in full: the label could be too strict. Those atoms
  are in N either way; the question is only whether they belong in X.
- 1 unsupported atom (H-45.1) cites passages.
- The two NLI models disagree on most of the flags, so this is a soft screen; the first model stays the reported one.

The 51 disagreements were shown to the curator in chat (atom, label, every passage with its verdict) on 11 Nov 2026;
he signed them off the same day: every label stands, none changed (`review-decision-2026-11-11.json`). Changes to labels are his and go through this repo's
own evidence-review process; none were made by this check.
