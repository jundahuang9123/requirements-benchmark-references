#!/usr/bin/env python3
"""Apply a base-relation adjudication record to the reference sets v3.

    python3 tools/base_relation_review/apply.py benchmark-data/reference-sets-v3/base-relation-review/adjudication-2026-11-11.json [--check]

For every item of the record, the atom must exist and be scored by default, and its relation_to_base must
equal the code the record was made from (code_before) or already equal the record's final code. The final
code must follow from the recorded decision: the review's code where the curator follows the review, the
earlier code where the curator keeps it. The script then sets, on each atom of the record,

  relation_to_base    the final code
  restates_dcat_ap    true exactly when the final code is restates_base
  relation_review     an object: status, date, the code before, the blind review's code, the kind of
                      difference, the decision and who took it, the final code and the record file

rewrites the counts block of each case file with the rules of tools/trace/recount.py, and sets the
relation_to_base and restates_dcat_ap columns of atoms-review.csv for the atoms of the record. It changes
no statement, stratum, status, anchor, evidence label or scored flag, no row, and no atom outside the
record. Run tools/trace/recount.py --write afterwards to rewrite counts.json.

Nothing is written if any item fails a check. Running the record twice changes nothing the second time.
--check reports what would change and writes nothing.
"""
import argparse
import csv
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/trace'))
from recount import counts as recount_counts  # noqa: E402

V3 = ROOT / 'benchmark-data/reference-sets-v3'
FILES = {'jrc-research': 'jrc-research.json', 'statdcat': 'statdcat.json', 'healthdcat': 'healthdcat.json',
         'geodcat': 'geodcat.json', 'mobilitydcat': 'mobilitydcat.json'}
RELATIONS = {'restates_base', 'tightens_base', 'extends_base', 'partly_base', 'beyond_base', 'not_term_level', 'unresolved'}
FOLLOWS, KEEPS = 'follows the blind review', "keeps the repository's code"


def relation_review(item, record, record_path):
    return {
        'status': 'adjudicated',
        'date': item.get('date') or record['date'],
        'code_before': item['code_before'],
        'review_claude_blind': item['review_claude_blind']['code'],
        'category': item['category'],
        'decision': item['owner_decision'],
        'final': item['final']['relation_to_base'],
        'decided_by': item.get('decided_by') or record['decided_by'],
        'record': record_path,
    }


def with_review(atom, review):
    """The atom with relation_review placed after relation_note (or replaced where it stands)."""
    if 'relation_review' in atom:
        atom['relation_review'] = review
        return atom
    out = {}
    for k, v in atom.items():
        out[k] = v
        if k == 'relation_note':
            out['relation_review'] = review
    if 'relation_review' not in out:
        out['relation_review'] = review
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('record')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    rec_path = Path(args.record).resolve()
    record = json.load(open(rec_path, encoding='utf-8'))
    rel = rec_path.relative_to(ROOT).as_posix()
    by_case = {}
    for it in record['items']:
        by_case.setdefault(it['case'], {})[it['atom_id']] = it
    unknown = set(by_case) - set(FILES)
    errors = [f'unknown case {c!r} in the record' for c in sorted(unknown)]
    code_changes, review_changes, docs = [], [], {}
    for case, fn in FILES.items():
        d = json.load(open(V3 / fn, encoding='utf-8'))
        docs[case] = d
        index = {a['id']: i for i, a in enumerate(d['atoms'])}
        for aid, it in by_case.get(case, {}).items():
            if aid not in index:
                errors.append(f'{case}: atom {aid} not found'); continue
            a = d['atoms'][index[aid]]
            if not a.get('scored_by_default'):
                errors.append(f'{case}: atom {aid} is not scored by default'); continue
            before, final, review_code = it['code_before'], it['final']['relation_to_base'], it['review_claude_blind']['code']
            for name, code in (('code_before', before), ('final', final), ('review', review_code)):
                if code not in RELATIONS:
                    errors.append(f'{case}: atom {aid} bad {name} code {code!r}')
            if it['owner_decision'] == FOLLOWS:
                if final != review_code:
                    errors.append(f'{case}: atom {aid} follows the review but its final code is not the review\'s')
            elif it['owner_decision'] == KEEPS:
                if final != before:
                    errors.append(f'{case}: atom {aid} keeps the code but its final code differs from the code before')
            else:
                errors.append(f'{case}: atom {aid} has an unknown decision {it["owner_decision"]!r}')
            if it['final']['restates_dcat_ap'] != (final == 'restates_base'):
                errors.append(f'{case}: atom {aid} final restates_dcat_ap does not follow from its final code')
            if a['relation_to_base'] not in (before, final):
                errors.append(f'{case}: atom {aid} relation_to_base is {a["relation_to_base"]!r}, record expects {before!r}')
                continue
            if a['relation_to_base'] != final or a['restates_dcat_ap'] != it['final']['restates_dcat_ap']:
                code_changes.append((case, aid, a['relation_to_base'], final))
                a['relation_to_base'] = final
                a['restates_dcat_ap'] = it['final']['restates_dcat_ap']
            new = relation_review(it, record, rel)
            if a.get('relation_review') != new:
                review_changes.append((case, aid))
                d['atoms'][index[aid]] = with_review(a, new)
        d['counts'] = recount_counts(d['requirements'], d['atoms'])

    # atoms-review.csv: the two relation columns of the atoms of the record
    csv_path = V3 / 'atoms-review.csv'
    rows = list(csv.DictReader(open(csv_path, encoding='utf-8', newline='')))
    fields = list(rows[0].keys())
    csv_changes = 0
    for row in rows:
        it = by_case.get(row['case'], {}).get(row['id'])
        if not it:
            continue
        code, flag = it['final']['relation_to_base'], str(it['final']['restates_dcat_ap'])
        if row['relation_to_base'] != code or row['restates_dcat_ap'] != flag:
            row['relation_to_base'], row['restates_dcat_ap'] = code, flag
            csv_changes += 1

    if errors:
        print('\n'.join(errors)); print(f'{len(errors)} errors; nothing written'); return 1
    print(f'{len(code_changes)} atoms change relation_to_base; {len(review_changes)} atoms get or change relation_review; '
          f'{csv_changes} rows of atoms-review.csv change')
    for case, aid, old, new in code_changes:
        print(f'  {case}: {aid}: {old} -> {new}')
    if args.check:
        return 0
    for case, fn in FILES.items():
        with open(V3 / fn, 'w', encoding='utf-8') as fh:
            json.dump(docs[case], fh, indent=1, ensure_ascii=False); fh.write('\n')
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields)  # csv's default \r\n, as atoms-review.csv is written
    w.writeheader(); w.writerows(rows)
    csv_path.write_bytes(buf.getvalue().encode('utf-8'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
