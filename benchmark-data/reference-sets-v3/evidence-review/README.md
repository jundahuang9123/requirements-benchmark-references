# Evidence-label review of the scored atoms

Every atom carries `input_evidence`: whether the runtime inputs of its case (the documents the extraction
pipeline reads, `benchmark-data/runtime-inputs.json`) state the requirement. The labels were proposed by
Claude subagents on 22 October 2026 (`input_evidence.raw`, `input_evidence.consolidation`; quotations
machine-checked). This folder records their review.

## Record: `adjudication-2026-11-03.json`

One item per scored atom (196). Each item keeps the 22 October labels, the two reviews, the kind of
difference, the owner's decision and the final labels:

- `final.raw`: does the raw corpus alone state the atom;
- `final.consolidation`: does the pre-consolidation corpus alone state it (HealthDCAT-AP and
  mobilityDCAT-AP only; reviewed only where the combined label depends on it, else `not_reviewed`);
- `final.combined`: raw and consolidation together. Use this combined label only for runs that receive both corpora; raw-only runs use `final.raw`.

## How the labels were reviewed

1. **Review A, Claude, blind (1 Nov 2026).** Eight Claude annotators (one per case, HealthDCAT-AP in
   three parts, mobilityDCAT-AP in two) labelled the 196 atoms from the standard-form statements and the
   plain-text runtime inputs, raw and consolidation. They did not see the 22 October labels, the anchor
   quotes or the reference documents. Every quoted passage was checked to exist verbatim in the input
   (whitespace-insensitive): 196 of 196 atoms, no failure. Rules given: a passage must be verbatim; a bare
   mention is partial (flag `bare_mention`). Table: `docs/reviews/2026-11-01-claude-blind-review.csv`.
2. **Review B, GPT Astra, raw inputs only (1 Nov 2026).** The 22 October labels, passages and rationales
   were visible; pre-standard wording. `docs/reviews/2026-11-01-label-review.md`.
3. **Consolidation (2 Nov).** A and B agree on 155 of 196 (143 also with the 22 October raw label). The 41
   differences fall into three kinds: 7 where only the bare-mention rule separates them; 9 where A's
   support is in a consolidation input that B did not read; 25 judgment calls.
4. **Owner decisions (3 Nov), without re-reading the sources:** a bare mention suffices for supported
   (the 7); the consolidation inputs count (the 9: combined = supported, raw = B's label); of the 25,
   supported where A held against B (15), A's concessions to B accepted (10). The owner then skimmed all
   196 rows and changed nothing else.

## Rules in force

1. A passage counts only if it exists verbatim in the input text.
2. A bare mention of the information item in the inputs (a field or element name in a list or schema)
   suffices for supported.
3. No blanket rule for missing conditions or scope was adopted. The recorded per-atom decisions apply;
   three of A's concessions to partial on that ground, H-13.1, H-27.1, H-37.3, stand by the owner's
   confirmation.
4. Raw and consolidation labels are kept apart; the combined label counts support in either corpus.

## Result

| | Supported | Partial | Unsupported | Uncertain |
|---|---|---|---|---|
| Combined (raw or consolidation), 196 atoms | 137 | 50 | 9 | 0 |
| Raw corpus alone | 128 | 59 | 9 | 0 |

Cases without output-to-reference comparison during development: mobilityDCAT-AP 38 / 1 / 0, GeoDCAT-AP 37 / 0 / 0 (combined). Compared with the 22 October raw labels, 19 raw labels changed: 9 supported → partial, 8 uncertain → partial, 1 unsupported → partial and 1 uncertain → unsupported. Compared with the strongest original label across raw and consolidation, 17 combined labels changed: 9 supported → partial, 6 uncertain → partial, 1 unsupported → partial and 1 uncertain → unsupported. The combined supported count of 137 equals the original raw figure by coincidence, not by identity of the sets.

The record's `final_differs_from_2026_10_22: 17` refers to that combined-to-combined comparison, not to the raw-only labels.

## Limits

Two AI reviews and an owner adjudication, not a human annotation of each atom against the sources.
Review B was not blind. No second human annotator took part; the Claude–Astra agreement (155/196) is
the only agreement figure. The 124 atoms not scored by default keep `human_review: "pending"`.

## Applying the record

```sh
python3 tools/evidence_review/apply.py benchmark-data/reference-sets-v3/evidence-review/adjudication-2026-11-03.json [--check]
```

sets `input_evidence.human_review` of each scored atom, adds `reviewed_*` counts, fills
`your_decision` / `your_note` of `atoms-review.csv`, and changes nothing else. The review workbooks
(the consolidated workbook with the owner's decisions, and Astra's checked copy) stay outside the
repository; the record holds their SHA-256.

In the generated tables, scored atoms use the adjudicated raw label and, where explicitly reviewed, the adjudicated consolidation label. Consolidation entries marked `not_reviewed` and all 124 unscored atoms retain their original AI labels. The supplement distinguishes these scopes; it does not claim independent human source validation.
