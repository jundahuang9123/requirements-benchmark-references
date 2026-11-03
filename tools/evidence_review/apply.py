#!/usr/bin/env python3
"""Apply an evidence-review adjudication record to the reference sets v3.

    python3 tools/evidence_review/apply.py benchmark-data/reference-sets-v3/evidence-review/adjudication-2026-11-03.json [--check]

For every item of the record, the atom must exist, be scored by default, and its 22 Oct AI labels
(input_evidence.raw / .consolidation) must equal the labels the record was made from. The script then sets

  input_evidence.human_review   an object: status, date, the two reviews' labels, the category of the
                                difference, the owner's decision, the final labels (raw, consolidation,
                                combined) and the record file
  counts.reviewed_*             counts of the final labels over the scored atoms (the 22 Oct count keys
                                are left as they are, so the history stays readable)

and fills your_decision / your_note of atoms-review.csv for the scored atoms. It changes no AI label, quote,
statement, stratum, status, anchor or scored flag. Atoms not in the record keep human_review = "pending".

Nothing is written if any item fails a check. Running the record twice changes nothing the second time.
--check reports what would change and writes nothing.
"""
import argparse
import csv
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V3 = ROOT / 'benchmark-data/reference-sets-v3'
FILES = {'jrc-research': 'jrc-research.json', 'statdcat': 'statdcat.json', 'healthdcat': 'healthdcat.json',
         'geodcat': 'geodcat.json', 'mobilitydcat': 'mobilitydcat.json'}
LABELS = {'supported', 'partial', 'unsupported', 'uncertain'}


def human_review(item, record_path):
    return {
        'status': 'adjudicated',
        'date': item.get('date') or '2026-11-03',
        'label': item['final']['combined'],
        'raw_label': item['final']['raw'],
        'consolidation_label': item['final']['consolidation'],
        'review_claude_blind': item['review_claude_blind']['label'],
        'review_astra_raw': item['review_astra_raw']['label'],
        'category': item['category'],
        'decision': item['owner_decision'],
        'decided_by': 'human:curator',
        'record': record_path,
    }


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

    errors, changes = [], []
    docs = {}
    for case, fn in FILES.items():
        d = json.load(open(V3 / fn, encoding='utf-8'))
        docs[case] = d
        atoms = {a['id']: a for a in d['atoms']}
        for aid, it in by_case.get(case, {}).items():
            a = atoms.get(aid)
            if a is None:
                errors.append(f'{case}: atom {aid} not found'); continue
            if not a.get('scored_by_default'):
                errors.append(f'{case}: atom {aid} is not scored by default'); continue
            ie = a.get('input_evidence') or {}
            for kind in ('raw', 'consolidation'):
                have = (ie.get(kind) or {}).get('label')
                want = it['ai_label_2026_10_22'].get(kind)
                if have != want:
                    errors.append(f'{case}: atom {aid} 22 Oct {kind} label is {have!r}, record expects {want!r}')
            for k in ('raw', 'combined'):
                if it['final'][k] not in LABELS:
                    errors.append(f'{case}: atom {aid} bad final {k} label {it["final"][k]!r}')
            new = human_review(it, rel)
            if ie.get('human_review') != new:
                changes.append((case, aid))
                ie['human_review'] = new
        # counts over the scored atoms
        scored = [a for a in d['atoms'] if a['scored_by_default']]
        hr = [a['input_evidence']['human_review'] for a in scored if isinstance(a['input_evidence'].get('human_review'), dict)]
        if hr:
            c = d['counts']
            c['reviewed_evidence_labels'] = {k: sum(h['label'] == k for h in hr) for k in ('supported', 'partial', 'unsupported', 'uncertain')}
            c['reviewed_raw_evidence_labels'] = {k: sum(h['raw_label'] == k for h in hr) for k in ('supported', 'partial', 'unsupported', 'uncertain')}
            c['scored_by_default_reviewed'] = len(hr)
            c['scored_by_default_reviewed_supported'] = sum(h['label'] == 'supported' for h in hr)
            c['scored_by_default_reviewed_supported_or_partial'] = sum(h['label'] in ('supported', 'partial') for h in hr)
            c['scored_by_default_reviewed_raw_supported'] = sum(h['raw_label'] == 'supported' for h in hr)
            c['scored_by_default_reviewed_raw_supported_or_partial'] = sum(h['raw_label'] in ('supported', 'partial') for h in hr)

    # atoms-review.csv
    csv_path = V3 / 'atoms-review.csv'
    rows = list(csv.DictReader(open(csv_path, encoding='utf-8', newline='')))
    fields = rows[0].keys()
    csv_changes = 0
    for row in rows:
        it = by_case.get(row['case'], {}).get(row['id'])
        if not it:
            continue
        dec = it['final']['combined']
        note = f"evidence review {record['date']}: {it['category']}; raw {it['final']['raw']}" + \
               (f", consolidation {it['final']['consolidation']}" if isinstance(it['final']['consolidation'], str) else '')
        if row['your_decision'] != dec or row['your_note'] != note:
            row['your_decision'], row['your_note'] = dec, note
            csv_changes += 1

    if errors:
        print('\n'.join(errors)); print(f'{len(errors)} errors; nothing written'); return 1
    print(f'{len(changes)} atoms change human_review; {csv_changes} rows of atoms-review.csv change')
    if args.check:
        return 0
    for case, fn in FILES.items():
        with open(V3 / fn, 'w', encoding='utf-8') as fh:
            json.dump(docs[case], fh, indent=1, ensure_ascii=False); fh.write('\n')
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(fields))  # csv's default \r\n, as atoms-review.csv is written
    w.writeheader(); w.writerows(rows)
    csv_path.write_bytes(buf.getvalue().encode('utf-8'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
