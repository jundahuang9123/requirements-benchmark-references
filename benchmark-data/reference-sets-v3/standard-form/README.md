# Standard form of the reference atoms

Every atom's `statement` is written in one standard form. A run's needs and the references are then compared like with like, and each atom can be checked against its source quote.

## Patterns

The type of an atom (`stratum`) and how it was assigned are recorded in [ATOM-TYPES.md](../ATOM-TYPES.md).

| Stratum | Pattern | Subject |
|---|---|---|
| content | `Users can <verb> <information> …` | users, always: anyone who uses the catalogue or its metadata, people or software, aggregators included |
| profile | `The profile <verb> …`, present tense | the profile |
| system | `<system or role> <verb> …`, present tense; `can` only for a capability the source states | the system or role named in the source |

Content verbs: `know`, `find`, `access`, `cite`, `use`.

## Rules

- A content sentence always starts with `Users can`. An actor the source names as needing the information stays in a purpose clause ("…, so aggregators can validate it"). The owner decided this in the batch 2b review.
- No must, shall, should or may in the sentence. The source's obligation stays in `modality`, its status in `status_in_source`.
- Only the frame changes: the information, scope and condition words come from the earlier statement and the source quote.
- Design choices and vocabulary names in content sentences move to `standard_form.hint`, unless they are the need itself.
- A rewrite that is not mechanical is flagged (`standard_form.flag`), and the owner decides it.

## Fields

- `statement`: the standard sentence.
- `statement_before_standard`: the earlier statement.
- `standard_form`: `actor`, `verb`, `information`, `resource`, `scope`, `condition`, `hint`; `flag`; `proposed` (the draft); `decision`; `drafted_by`; `reviewed_by`; `date`; `record` (the batch file); `replaces` (only after a correction).

## How a batch is made

1. Claude drafts the sentence and fields of each atom from its current statement and source quote, adding nothing. For a system atom whose statement names no actor, Claude also reads the source text around the quote, and the flag says where the actor comes from.
2. A script checks the patterns.
3. The owner decides every flagged atom, in a spreadsheet or in chat; the other atoms are accepted with the batch. The batch record keeps the sha256 of the returned spreadsheet or of the owner's replies, which stay outside the repository.
4. `tools/standard_form/apply.py` applies the batch record. It changes no label, anchor or scored flag, and running it twice changes nothing.

## Corrections

When a review decides a rule that an earlier batch did not follow, the batch record of that review lists the affected atoms under `corrections`. `apply.py` gives each one its new sentence, keeps `statement_before_standard`, and adds the replaced sentence and its batch to `standard_form.replaces`. Running the earlier batch again skips the replaced item.

## Batches

| Batch | Cases | Atoms | Flagged | Changed in review | Status |
|---|---|---|---|---|---|
| 1 | JRC, Stat | 45 | 14 | 3 | applied |
| 2a | Health, rows H-1 to H-33 | 68 | 21 | 5 | applied |
| 2b | Health, rows H-34 to H-69 | 53 | 21 | 1 | applied |
| 3 | Geo | 56 | 2 | 0 | applied |
| 4 | Mobility | 98 | 17 | 0 | applied |

Batch 2b also corrects JRC-8.2 from batch 1 to the content rule: "Users and software agents can know …" became "Users can know …, so software agents can use it directly."

All 320 atoms are in standard form. The supplement, Appendix A and Table 2 were regenerated after batch 4 with plain `python3 make_tables.py`; Table 2 did not change.
