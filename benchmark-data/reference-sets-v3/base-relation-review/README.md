# Base-relation review of the scored atoms

Every atom carries `relation_to_base`: how its requirement relates to the DCAT-AP release its case cites
(restates_base, tightens_base, extends_base, partly_base, beyond_base, not_term_level or unresolved).
`restates_dcat_ap` is true exactly when the code is restates_base, so that restatements of the base can be
left out at scoring time. This folder records the review of that code.

## Record: `adjudication-2026-11-11.json`

One item per adjudicated atom (18). Each item keeps the code before, the blind review's code with the base
term, obligation, quotation and rationale it cites, the kind of difference, the decision, who took it and
on what basis, how the atom's note was handled, what the independent check of 22 October 2026 records for
the atom, and the final code.

## How the codes were reviewed

1. **Earlier coding and check (22 Oct 2026).** The codes were given when the rows were split into atoms
   (trace step R7; the trace records who coded and the reasons as not recorded, and `relation_note` is
   empty). An independent source check of the same date went through all 45 atoms then coded as
   restatements and all 111 term-level content atoms, and changed or confirmed some codes
   (`../INDEPENDENT-CHECK.md`).
2. **Blind review, Claude (3–4 Nov 2026).** Eight Claude annotators (one per case, HealthDCAT-AP in three
   parts, mobilityDCAT-AP in two) coded the 196 scored atoms again from the standard-form statements, the
   source's obligation wording and status, and the pinned base text. They did not see the repository's
   code, the atoms' notes, the earlier check or the extension profile. For each atom they answered
   "restates or not" first, then gave the seven-way code, the base class and property, the base obligation
   as read, a verbatim base quotation and a rationale. According to the review's notes every quotation was
   checked by program to occur in the base text (whitespace-insensitive): 196 of 196, no failure.
3. **Comparison (4 Nov).** The review and the earlier code agree on the code for 147 of the 196 atoms and
   on "restates" for 178. Of the 49 differences, 11 change "restates" on the reading of the content, 7
   change restates_base to tightens_base because the source asks more strongly than the base or adds a
   condition, and 31 leave "restates" as it is.
4. **Decisions (11 Nov).** The 18 atoms whose answer to "restates" differs were put before the curator in
   a decision sheet: statement, both codes, the base term, obligation and quotation the review cites, and
   its rationale. The curator followed the review except for two rows the assistant had pointed to. While
   the record was being made, the assistant found that ten of the 18 atoms carry a note from the original
   curation, which neither the reviewers nor the sheet had shown. It put five of them before the curator,
   who kept the earlier code for one more atom, confirmed the review for two, and left two rows to the
   assistant, which kept the earlier code. Result: 13 follow the review, 5 keep the earlier code.

## Rules in force

1. **Obligation (B1).** An atom whose source asks more strongly than the base (a requirement where the
   base recommends or allows) or adds a condition is tightens_base, not restates_base. Six atoms change on
   this rule. For a seventh the rule does not apply, because the property stays recommended in the source.
2. **Geo obligation levels: unchanged.** The decision of 22 October 2026 stands: INSPIRE and ISO obligation
   levels are kept as fields and are not part of each Geo need. No Geo atom changes on obligation grounds;
   the three Geo atoms that change do so on the reading of the content.
3. **Scope.** Only the answer to "restates" was adjudicated. An adjudicated atom gets the review's code
   where the review is followed and keeps its earlier code otherwise.

## Result

| Case | Scored | Restate the base, before | Now | Scored without restatements, before | Now |
|---|---:|---:|---:|---:|---:|
| Mobility | 39 | 7 | 5 | 32 | 34 |
| Health | 89 | 13 | 12 | 76 | 77 |
| Stat | 14 | 6 | 4 | 8 | 10 |
| Geo | 37 | 16 | 17 | 21 | 20 |
| JRC | 17 | 4 | 3 | 13 | 14 |
| **Total** | 196 | 46 | 41 | 150 | 155 |

Nine atoms no longer restate the base and four restate it now. Thirteen codes change; five atoms keep
their code and gain only the review entry.

## Limits

One blind AI review and the curator's adjudication of the atoms on which it differs from the earlier code
on "restates"; not a human coding of each atom against the base. No second human annotator took part. Two
of the 18 rows were decided by the assistant, to which the curator left them. The findings of the
independent check of 22 October 2026 were not in the decision sheet; for two atoms that now follow the
review, that check had settled the code otherwise, and this was found only while the record was made. The
record names these four rows, and the pull request that carried the record put them to the curator. The 31
differences that do not touch "restates" are not adjudicated. The base quotations of the mobilityDCAT-AP
and HealthDCAT-AP atoms could not be re-checked when the record was made, because the repository holds no
copy of DCAT-AP 2.0.1 or 3.0.0; the eight quotations from DCAT-AP 1.1 were found again in the stored copy.
The review table (196 rows) and the decision sheets stay outside the repository; the record holds the
sheets' SHA-256 and records the table's as not recorded. Rows are not changed: row relations keep the v1
coding, and atom relations are coded per atom.

## Applying the record

```sh
python3 tools/base_relation_review/apply.py benchmark-data/reference-sets-v3/base-relation-review/adjudication-2026-11-11.json [--check]
python3 tools/trace/recount.py --write
```

The first command sets `relation_to_base`, `restates_dcat_ap` and `relation_review` on the atoms of the
record, rewrites the counts block of each case file and the two relation columns of `atoms-review.csv`,
and changes nothing else. The second rewrites `counts.json`. Run with `--check`, the first command
reports no change when the tree agrees with the record.

Appendix A and the supplement show the adjudicated codes in their Base column. The stored results of the
mock benchmark were made with the earlier codes and were not recomputed; its check now reports the one
slice of the JRC mock runs that the change touches (see the top-level README).
