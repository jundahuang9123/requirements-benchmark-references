#!/usr/bin/env python3
"""Apply one reviewed batch of the standard form to the reference sets v3.

    python3 tools/standard_form/apply.py benchmark-data/reference-sets-v3/standard-form/batch-01.json [--check]

For every atom in the batch, the atom's current statement must equal the batch's "before" text. The
script then sets:
  statement                  the reviewed standard sentence ("after")
  statement_before_standard  the earlier statement ("before"), kept for audit
  standard_form              the fields of the sentence, the flag, and the review decision
and updates the statement column of atoms-review.csv. It changes nothing else: no label, stratum,
status, obligation, anchor or scored flag. Running it twice changes nothing the second time.
--check reports what would change and writes nothing.
"""
import argparse
import csv
import io
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V3 = ROOT / 'benchmark-data/reference-sets-v3'
CONTENT_VERBS = {'know', 'find', 'access', 'cite', 'use'}
MODALS = re.compile(r'\b(must|shall|should|may|might|ought)\b', re.I)
FIELDS = ('actor', 'verb', 'information', 'resource', 'scope', 'condition', 'hint')


def check_pattern(atom, item):
    """The sentence patterns of standard-form/README.md."""
    s, actor = item['after'], item['actor']
    problems = []
    if atom['stratum'] == 'content':
        if not s.startswith(actor[:1].upper() + actor[1:] + ' can '):
            problems.append('a content sentence starts with its actor and "can"')
        if item['verb'] not in CONTENT_VERBS:
            problems.append(f'the verb is one of {sorted(CONTENT_VERBS)}')
    elif atom['stratum'] == 'profile':
        if not s.startswith('The profile '):
            problems.append('a profile sentence starts with "The profile"')
    elif not s.lower().startswith(actor.lower()):
        problems.append('a system sentence starts with its actor')
    if MODALS.search(s):
        problems.append('no must, shall, should or may in the sentence')
    if not s.endswith('.'):
        problems.append('the sentence ends with a full stop')
    return problems


def with_keys_at(obj, anchor, new_items):
    """A copy of obj in which new_items take the place of key anchor (keeps the file diff readable)."""
    out = {}
    for k, v in obj.items():
        if k == anchor:
            out.update(new_items)
        elif k not in new_items:
            out[k] = v
    if anchor not in obj:
        raise KeyError(anchor)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('batch', type=Path)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    batch = json.loads(args.batch.read_text(encoding='utf-8'))
    record = str(args.batch.resolve().relative_to(ROOT))
    by_case = {}
    for item in batch['atoms']:
        by_case.setdefault(item['case'], []).append(item)
    problems, changes = [], []
    new_statement = {}
    for case, items in by_case.items():
        path = V3 / f'{case}.json'
        doc = json.loads(path.read_text(encoding='utf-8'))
        index = {a['id']: k for k, a in enumerate(doc['atoms'])}
        for item in items:
            if item['id'] not in index:
                problems.append(f'{case}/{item["id"]}: no such atom')
                continue
            k = index[item['id']]
            atom = doc['atoms'][k]
            problems += [f'{case}/{item["id"]}: {p}' for p in check_pattern(atom, item)]
            done = atom.get('statement_before_standard') == item['before'] and atom['statement'] == item['after']
            if done:
                continue
            if atom['statement'] != item['before'] or 'statement_before_standard' in atom:
                problems.append(f'{case}/{item["id"]}: the current statement is not the batch\'s "before" text')
                continue
            form = {f: item[f] for f in FIELDS}
            form.update(flag=item['flag'], proposed=item['proposed'], decision=item['decision'],
                        drafted_by=batch['drafted_by']['actor'], reviewed_by=batch['reviewed_by']['actor'],
                        date=batch['reviewed_by']['date'], record=record)
            doc['atoms'][k] = with_keys_at(atom, 'statement', {'statement': item['after'],
                                                                  'statement_before_standard': item['before'],
                                                                  'standard_form': form})
            new_statement[(case, item['id'])] = item['after']
            changes.append((case, item['id']))
        if not args.check and any(c == case for c, _ in changes):
            path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    if problems:
        raise SystemExit('\n'.join(problems))
    if changes and not args.check:
        review = V3 / 'atoms-review.csv'
        rows = list(csv.DictReader(io.StringIO(review.read_text(encoding='utf-8'))))
        for r in rows:
            if (r['case'], r['id']) in new_statement:
                r['statement'] = new_statement[(r['case'], r['id'])]
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
        review.write_bytes(buf.getvalue().encode('utf-8'))
    print(('would change' if args.check else 'changed'), len(changes), 'atoms;', len(batch['atoms']) - len(changes), 'already applied')


if __name__ == '__main__':
    main()
