# Supplement and paper tables

Generated from the case files in this folder's parent by `make_tables.py` (pdfLaTeX, Springer LNCS class).

- `supplement-reference-requirements.tex` / `.pdf`: every row and atom of the five reference sets, with level, status, relation to the base, evidence labels and whether the atom is scored (21 pages). Atom statements are in the standard form of `../standard-form/README.md`; the level column's definitions still need a citation (see `../ATOM-TYPES.md`). It goes into the supplementary material: ESWC 2027 allows an optional appendix of at most 2 pages.
- `appendix-test-cases.tex`: Appendix A for the paper, the 76 scored atoms of the two test cases (about 1.9 pages with the standard-form statements, within the 2-page limit). Needs `\usepackage{longtable}`; insert it after `\bibliography{references}`.
- `table-benchmark.tex`: Table 2 for the paper, one line per case. Replace the Table 2 block with `\input{table-benchmark}`.

Regenerate with `python3 make_tables.py` (`RQ1_REF_COMMIT` sets the commit named in the files). To compile the supplement, put `llncs.cls` next to it.
