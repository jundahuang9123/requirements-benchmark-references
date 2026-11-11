#!/usr/bin/env python3
"""The review sheet for the first author: Part A's flagged atoms (and a random sample of unflagged ones, unmarked) on the
first tab, Part B's disagreements on the second. The key (which rows are flagged by what, which are the sample) is
written to a separate file, for the person who reads the sheet back.

usage: python3 -I make_sheet.py --part-a part-a-atom-fidelity/out --part-b part-b-evidence-labels/out --out review/
"""
import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dc import paths  # noqa: E402

SAMPLE = 30
SEED = 'deterministic-checks part A review sample'
TICK = '"✓"'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--part-a', required=True)
    ap.add_argument('--part-b', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    a = paths.jload(os.path.join(args.part_a, 'atoms.json'))['atoms']
    b = paths.jload(os.path.join(args.part_b, 'atoms.json'))['atoms']
    rng = random.Random(SEED)
    flagged = [r for r in a if r['flags']['any']]
    unflagged = [r for r in a if not r['flags']['any']]
    sample = rng.sample(sorted(unflagged, key=lambda r: (r['case'], r['id'])), min(SAMPLE, len(unflagged)))
    both = sorted([r for r in flagged if r['flags']['both']], key=lambda r: (r['case'], r['id']))
    contra = sorted([r for r in flagged if r['flags']['contradiction'] and not r['flags']['both']], key=lambda r: (r['case'], r['id']))
    rest = [r for r in flagged if not r['flags']['both'] and not r['flags']['contradiction']] + sample
    rest.sort(key=lambda r: (r['case'], r['id']))
    rng.shuffle(rest)
    rows = both + contra + rest

    wb = Workbook()
    ws = wb.active
    ws.title = 'Atoms'
    head = ['Row', 'Case', 'Atom ID', 'Statement', 'Earlier statement (before the standard form)', 'Anchor quotation', 'Context',
            'Content words not in the context', 'Numbers not in the context', 'Words added by the rewording', 'Words dropped by the rewording',
            'NLI: context => statement', 'NLI: earlier => statement', 'NLI: statement => earlier',
            'Faithful', 'Adds something', 'Drops something', 'Wrong', 'Note']
    ws.append(head)
    yours = {'Faithful', 'Adds something', 'Drops something', 'Wrong', 'Note'}
    for i, h in enumerate(head, 1):
        c = ws.cell(row=1, column=i)
        c.font = Font(bold=True)
        c.fill = PatternFill('solid', fgColor='FFF2CC' if h in yours else 'DDEBF7')
        c.alignment = Alignment(wrap_text=True, vertical='top')
    key = {'tabs': {'Atoms': [], 'Evidence': []}, 'sample_size': len(sample), 'seed': SEED,
           'order': 'flagged by both (lexical and NLI) first, then contradictions, then the rest and the sample shuffled together'}
    for n, r in enumerate(rows, 1):
        ws.append([n, paths.CASE_NAME[r['case']], r['id'], r['statement'], r['statement_before_standard'], r['anchor_quote'], r['context']['context'],
                   ', '.join(r['T1']['missing']), ', '.join(r['T2']['missing']), ', '.join(r['T3']['added']), ', '.join(r['T3']['dropped']),
                   r['N1']['verdict'], r['N2']['before_to_after']['verdict'], r['N2']['after_to_before']['verdict'], '', '', '', '', ''])
        f = r['flags']
        key['tabs']['Atoms'].append({'row': n, 'atom_id': r['id'], 'case': r['case'], 'sample': not f['any'],
                                     'flagged_by': [t for t in ('T1', 'T2', 'T3', 'N1', 'N2') if f[t]],
                                     'group': 'both' if f['both'] else 'contradiction' if f['contradiction'] else 'lexical only' if f['lexical'] else 'NLI only' if f['nli'] else 'sample'})
    dv = DataValidation(type='list', formula1=TICK, allow_blank=True)
    ws.add_data_validation(dv)
    last = len(rows) + 1
    for col in ('O', 'P', 'Q', 'R'):
        dv.add(f'{col}2:{col}{last}')
    widths = [5, 14, 10, 50, 50, 40, 70, 24, 14, 20, 20, 14, 14, 14, 9, 9, 9, 9, 40]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
    for row in ws.iter_rows(min_row=2, max_row=last):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical='top')
    ws.freeze_panes = 'D2'

    ws2 = wb.create_sheet('Evidence')
    head2 = ['Row', 'Case', 'Atom ID', 'Statement', 'Adjudicated label (raw inputs)', 'Adjudication category', 'What the check expected',
             'Passages cited (one per line, with the NLI verdict passage => statement)', 'NLI: passages joined => statement',
             'Content words not in the passages', 'Label holds', 'Label wrong', 'Note']
    ws2.append(head2)
    yours2 = {'Label holds', 'Label wrong', 'Note'}
    for i, h in enumerate(head2, 1):
        c = ws2.cell(row=1, column=i)
        c.font = Font(bold=True)
        c.fill = PatternFill('solid', fgColor='FFF2CC' if h in yours2 else 'DDEBF7')
        c.alignment = Alignment(wrap_text=True, vertical='top')
    dis = sorted([r for r in b if r['result']['disagreement']], key=lambda r: (r['case'], r['id']))
    for n, r in enumerate(dis, 1):
        passages = '\n'.join(f"[{p['N1']['verdict']}] {p['quote']}" for p in r['passages'])
        ws2.append([n, paths.CASE_NAME[r['case']], r['id'], r['statement'], r['raw_label'], r['category'], r['result']['expected'], passages,
                    r['result']['joined_verdict'] or '', ', '.join(r['T1']['missing']) if r['T1'] else '', '', '', ''])
        key['tabs']['Evidence'].append({'row': n, 'atom_id': r['id'], 'case': r['case'], 'disagreement': r['result']['disagreement'],
                                        'bare_mention': r['result'].get('bare_mention', False)})
    dv2 = DataValidation(type='list', formula1=TICK, allow_blank=True)
    ws2.add_data_validation(dv2)
    for col in ('K', 'L'):
        dv2.add(f'{col}2:{col}{len(dis) + 1}')
    for i, w in enumerate([5, 14, 10, 50, 14, 20, 24, 90, 14, 24, 9, 9, 40], 1):
        ws2.column_dimensions[ws2.cell(row=1, column=i).column_letter].width = w
    for row in ws2.iter_rows(min_row=2, max_row=len(dis) + 1):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical='top')
    ws2.freeze_panes = 'D2'

    os.makedirs(args.out, exist_ok=True)
    wb.save(os.path.join(args.out, 'atom-fidelity-review.xlsx'))
    paths.jdump(key, os.path.join(args.out, 'atom-fidelity-review-key.json'))
    print(f"Atoms tab: {len(rows)} rows ({len(both)} both, {len(contra)} contradictions, {len(rest) - len(sample)} other flags, {len(sample)} sample); Evidence tab: {len(dis)} rows")


if __name__ == '__main__':
    main()
