#!/usr/bin/env python3
"""Apply one reviewed batch of the standard form to the reference sets v3.

    python3 tools/standard_form/apply.py benchmark-data/reference-sets-v3/standard-form/batch-01.json [--check]

For every atom in the batch, the atom's current statement must equal the batch's "before" text. The
script then sets:
  statement                  the reviewed standard sentence ("after")
  statement_before_standard  the earlier statement ("before"), kept for audit
  standard_form              the fields of the sentence, the flag, and the review decision
and updates the statement column of atoms-review.csv. It changes nothing else: no label, stratum,
status, obligation, anchor or scored flag.

A batch may also carry corrections: atoms of an earlier batch standardised again after a rule decision
in this batch's review. A correction's "before" text is the atom's current standard sentence, and the
atom's current record must be the batch the correction names. It keeps statement_before_standard and
adds the replaced sentence and its batch to standard_form.replaces. Running the earlier batch again
skips the item the correction superseded.

Nothing is written if any item fails a check. Running a batch twice changes nothing the second time.
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
CONTENT_ACTOR = 'users'
CONTENT_VERBS = {'know', 'find', 'access', 'cite', 'use'}
MODALS = re.compile(r'\b(must|shall|should|may|might|ought)\b', re.I)
FIELDS = ('actor', 'verb', 'information', 'resource', 'scope', 'condition', 'hint')


def check_pattern(atom, item):
    """The sentence patterns of standard-form/README.md."""
    s, actor = item['after'], item['actor']
    problems = []
    if atom['stratum'] == 'content':
        if actor != CONTENT_ACTOR or not s.startswith('Users can '):
            problems.append('a content sentence starts with "Users can"')
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


def superseded(atom, item, record):
    """True when a later correction replaced the sentence this batch gave the atom."""
    return any(r['record'] == record and r['statement'] == item['after']
               for r in (atom.get('standard_form') or {}).get('replaces', []))


def form_of(item, batch, record):
    form = {f: item[f] for f in FIELDS}
    form.update(flag=item['flag'], proposed=item['proposed'], decision=item['decision'],
                drafted_by=batch['drafted_by']['actor'], reviewed_by=batch['reviewed_by']['actor'],
                date=batch['reviewed_by']['date'], record=record)
    return form


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('batch', type=Path)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    batch = json.loads(args.batch.read_text(encoding='utf-8'))
    record = str(args.batch.resolve().relative_to(ROOT))
    by_case = {}
    for item in batch['atoms']:
        by_case.setdefault(item['case'], []).append((item, False))
    for item in batch.get('corrections', []):
        by_case.setdefault(item['case'], []).append((item, True))
    problems, changes, skipped, docs = [], [], [], {}
    new_statement = {}
    for case, items in by_case.items():
        path = V3 / f'{case}.json'
        doc = json.loads(path.read_text(encoding='utf-8'))
        index = {a['id']: k for k, a in enumerate(doc['atoms'])}
        for item, is_correction in items:
            where = f'{case}/{item["id"]}'
            if item['id'] not in index:
                problems.append(f'{where}: no such atom')
                continue
            k = index[item['id']]
            atom = doc['atoms'][k]
            if not is_correction and superseded(atom, item, record):
                skipped.append(where)
                continue
            problems += [f'{where}: {p}' for p in check_pattern(atom, item)]
            form = form_of(item, batch, record)
            if is_correction:
                sf = atom.get('standard_form') or {}
                if atom['statement'] == item['after'] and sf.get('record') == record:
                    continue
                if atom['statement'] != item['before'] or sf.get('record') != item['replaces_record']:
                    problems.append(f'{where}: the correction does not fit the atom\'s current standard form')
                    continue
                form['replaces'] = sf.get('replaces', []) + [{'statement': item['before'], 'record': item['replaces_record']}]
                atom['statement'], atom['standard_form'] = item['after'], form
            else:
                if atom.get('statement_before_standard') == item['before'] and atom['statement'] == item['after']:
                    continue
                if atom['statement'] != item['before'] or 'statement_before_standard' in atom:
                    problems.append(f'{where}: the current statement is not the batch\'s "before" text')
                    continue
                doc['atoms'][k] = with_keys_at(atom, 'statement', {'statement': item['after'],
                                                                      'statement_before_standard': item['before'],
                                                                      'standard_form': form})
            new_statement[(case, item['id'])] = item['after']
            changes.append(where)
            docs[case] = (path, doc)
    if problems:
        raise SystemExit('\n'.join(problems))
    if changes and not args.check:
        for path, doc in docs.values():
            path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
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
    total = len(batch['atoms']) + len(batch.get('corrections', []))
    print(('would change' if args.check else 'changed'), len(changes), 'items;', total - len(changes) - len(skipped),
          'already applied;', len(skipped), 'superseded by a later correction')


if __name__ == '__main__':
    main()
