# Standard form of the reference atoms

Every atom's `statement` is written in one standard form. A run's needs and the references are then compared like with like, and each atom can be checked against its source quote.

## Patterns

| Stratum | Pattern | Subject |
|---|---|---|
| content | `Users can <verb> <information> …` | users, unless the source names another actor who needs the information |
| profile | `The profile <verb> …`, present tense | the profile |
| system | `<system or role> <verb> …`, present tense; `can` only for a capability the source states | the system or role named in the source |

Content verbs: `know`, `find`, `access`, `cite`, `use`.

## Rules

- No must, shall, should or may in the sentence. The source's obligation stays in `modality`, its status in `status_in_source`.
- Only the frame changes: the information, scope and condition words come from the earlier statement and the source quote.
- Design choices and vocabulary names in content sentences move to `standard_form.hint`, unless they are the need itself.
- A rewrite that is not mechanical is flagged (`standard_form.flag`), and the owner decides it.

## Fields

- `statement`: the standard sentence.
- `statement_before_standard`: the earlier statement.
- `standard_form`: `actor`, `verb`, `information`, `resource`, `scope`, `condition`, `hint`; `flag`; `proposed` (the draft); `decision`; `drafted_by`; `reviewed_by`; `date`; `record` (the batch file).

## How a batch is made

1. Claude drafts the sentence and fields of each atom from its current statement and source quote, adding nothing.
2. A script checks the patterns.
3. The owner decides every flagged atom; the other atoms are accepted with the batch.
4. `tools/standard_form/apply.py` applies the batch record. It changes no label, anchor or scored flag, and running it twice changes nothing.

## Batches

| Batch | Cases | Atoms | Flagged | Changed in review | Status |
|---|---|---|---|---|---|
| 1 | JRC, Stat | 45 | 14 | 3 | applied |
| 2 | Health | 121 | | | drafting |
| 3 | Geo | 56 | | | |
| 4 | Mobility | 98 | | | |

The supplement and Appendix A print the statements. They are regenerated once all batches are applied.
