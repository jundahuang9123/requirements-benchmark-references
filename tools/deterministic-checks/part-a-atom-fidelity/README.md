# Part A. Atom fidelity: is each atom what its reference passage says?

Question: does every atom statement state only what the passage it paraphrases states, and did the standard-form
rewording keep the meaning? A screen for the curator, not a verdict: every flagged atom goes on the review sheet, with a
random sample of unflagged ones, and the curator's reading decides. Changes to atoms are the curator's decision and go
through this repo's own process.

## What was run (`../part_a.py`)

All 320 atoms of `benchmark-data/reference-sets-v3/*.json` at commit `524f65b`. Pairs per atom:

- the statement against its **context**: the anchor quotation located in the text of the reference PDF (`pdftotext`),
  with 700 characters on each side (Stat `stat-final.pdf`, Geo `geo-final.pdf`, Health `d6.2-requirements-and-profile.pdf`);
  for Mobility the parent row's stored `table1_text` (a transcription made during curation; the NAPCORE PDF is not in
  the repo); for JRC the anchor alone (the paper is not in the repo). Every anchor was found (Health: 5 bullet-list
  anchors found only after punctuation was removed on both sides; `counts.json: context_located`);
- the statement against `statement_before_standard`.

| Test | What | Flag when (fixed before the run) |
|---|---|---|
| T1 | content words of the statement not found in the context (stop words and the template words *users, profile, can, know, find, judge, do* removed; crude suffix stemming; a word also counts as found when it occurs inside the context with all punctuation removed) | two or more missing and at least half of the content words |
| T2 | numbers in the statement not in the context | any |
| T3 | content words added or dropped by the standard-form rewording | two or more added, or two or more dropped |
| N1 | NLI, context ⇒ statement | verdict is not *entailment* |
| N2 | NLI, earlier statement ⇔ statement | either direction is not *entailment* (the count with both directions failing is given beside it) |

NLI: `cross-encoder/nli-deberta-v3-base` at revision `6c749ce3`, CPU, seed 0, argmax, no threshold, the premise
truncated first at 512 tokens (32 atoms' contexts were cut; `N1_premise_truncated`). The rules are in `../dc/textrules.py`
with unit tests on invented sentences in `../tests/`.

Reading of N2: the spec's "not entailment in both directions" was read, before the run, as *the two wordings do not entail
each other*, i.e. a flag when either direction fails; the stricter count (both directions fail) is reported too.

## Results (rerun test passed: `atoms.json`, `counts.json` and `sensitivity.json` byte-identical over two runs; `run-record.json` differed only in the checkout commits it records, the input hashes being the same)

Counts only; the per-atom record is `out/atoms.json`, the tables `out/counts.json`, the sensitivity runs `out/sensitivity.json`.

| | atoms | T1 | T2 | T3 | N1 | N2 | lexical only | NLI only | both | any | contradiction |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 320 | 27 | 0 | 45 | 189 | 130 | 7 | 185 | 61 | 253 | 19 |
| scored | 196 | 24 | 0 | 30 | 129 | 40 | 7 | 96 | 44 | 147 | 14 |
| JRC | 18 | 9 | 0 | 4 | 9 | 3 | 2 | 0 | 9 | 11 | 0 |
| Stat | 27 | 2 | 0 | 5 | 19 | 13 | 0 | 18 | 6 | 24 | 1 |
| Geo | 56 | 10 | 0 | 2 | 47 | 22 | 2 | 37 | 10 | 49 | 9 |
| Health | 121 | 3 | 0 | 32 | 99 | 43 | 0 | 77 | 34 | 111 | 8 |
| Mobility | 98 | 3 | 0 | 2 | 15 | 49 | 3 | 53 | 2 | 58 | 1 |

*lexical* = T1 or T2 or T3; *NLI* = N1 or N2; *both* = lexical and NLI; *contradiction* = the model reads a contradiction in
N1 or in either direction of N2 (N1 alone: 12). N2 with both directions failing: 4.

How this reads:
- No atom contains a number its passage lacks (T2 = 0).
- 68 atoms (51 scored) trip a word-level test; 61 trip a word-level test and the model. These head the review sheet.
- N1 on its own is not a useful screen with this model: a 1,400-character passage as premise rarely yields *entailment*,
  so it flags 59% of atoms. The JRC flags under T1 are expected: JRC has only the short anchor to compare with.
- Many Health T3 flags come from the standard form replacing verbs such as *state, give, link, classify* by
  *Users can know / access / filter*: a change of form that the curator must judge, not a finding.

Sensitivity (how many flags change against the 700-character window):
- window 300: T1 39 flags (12 changed), N1 155 (52 changed), any test 238 (23 changed);
- window 1,500: T1 21 (6 changed), N1 214 (39 changed), any 267 (22 changed); JRC and Mobility have no window;
- second model (`MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli`, revision `b3546ea6`): N1 50 flags instead of 189
  (verdict agreement with the first model 42%), N2 208 instead of 130. The two NLI models disagree widely on these
  pairs; the first model stays the reported one, as fixed before the run.

## Limits, stated not hidden

- JRC: anchor only. Mobility: compared with a transcription, not the PDF. If the JRC paper or the NAPCORE PDF can be
  staged as evaluator-only files with a hash, those cases should be rerun with a PDF window.
- The lexical rules were written from the spec's table; the earlier `atom_fidelity.py` of the project docs was not
  available, so its counts (62 of 320 flagged on 11 Nov) and these (68) come from two rule sets.

## Curator's review (11 Nov 2026)

The 61 atoms flagged by both kinds of test were shown to the curator in chat with their flagged words and NLI verdicts.
Verdict: all 61 checked and faithful; no atom changes; no review sheet needed (`review-decision-2026-11-11.json`). The
192 atoms flagged by one kind of test only were not reviewed. So the screen found no atom the curator would change, and
the miss rate of the screen was not estimated (no unflagged sample was reviewed).

## Review sheet (not used)

`../make_sheet.py` writes `review/atom-fidelity-review.xlsx`: every atom with any flag, "both" first, then
contradictions, then the rest shuffled with 30 random unflagged atoms (unmarked); the curator ticks *faithful / adds
something / drops something / wrong* and notes. The key (which rows are the sample, which test flagged each row) is
`review/atom-fidelity-review-key.json`, kept apart. After the sheet comes back: per test, how many flags the curator
confirmed, and how many sample atoms he marked.
