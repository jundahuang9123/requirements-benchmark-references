#!/usr/bin/env python3
"""Part A. Atom fidelity: is each atom what its reference passage says?

Per atom: the statement against its context (T1 content words, T2 numbers, N1 NLI context => statement) and against
`statement_before_standard` (T3 words added or dropped, N2 NLI in both directions). Fixed reading (see README):
  T1  flag when two or more content words are missing and at least half of them
  T2  flag when any number of the statement is not in the context
  T3  flag when the rewording added two or more content words, or dropped two or more
  N1  flag when the verdict context => statement is not entailment
  N2  flag when the two statements do not entail each other in both directions (either direction fails); the count
      with both directions failing is reported beside it
Sensitivity: windows of 300 and 1,500 characters (T1, T2, N1 depend on the window) and the second NLI model (N1, N2).

usage: python3 -I part_a.py --out part-a-atom-fidelity/out [--windows 300,700,1500] [--second-model] [--log FILE]
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dc import atoms as A, paths, textrules as T  # noqa: E402
from dc.nli import NLI  # noqa: E402

MAIN_WINDOW = 700


def lexical(case, atom, reqs, window):
    cx = A.context(case, atom, window, reqs)
    st, before = atom['statement'], atom.get('statement_before_standard') or ''
    return cx, {'T1': T.t1(st, cx['context']), 'T2': T.t2(st, cx['context']), 'T3': T.t3(before, st)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--windows', default='300,700,1500')
    ap.add_argument('--second-model', action='store_true')
    ap.add_argument('--log', default=None, help='timing and messages (not part of the compared outputs)')
    args = ap.parse_args()
    windows = sorted({int(w) for w in args.windows.split(',')} | {MAIN_WINDOW})
    log = open(args.log, 'a') if args.log else sys.stderr
    t0 = time.time()

    everything, files = A.all_atoms()
    files += [os.path.join(paths.REFS, 'benchmark-data', p) for p in paths.REF_PDF.values()]
    recs = []
    for case, atom, reqs in everything:
        d, _ = A.load_case(case)
        dn = A.denominators(d['atoms'])
        cx, lex = lexical(case, atom, reqs, MAIN_WINDOW)
        r = {'id': atom['id'], 'case': case, 'stratum': atom.get('stratum'), 'scored': bool(atom.get('scored_by_default')),
             'in_N': atom['id'] in dn['N'], 'in_X': atom['id'] in dn['X'], 'raw_label': A.raw_label(atom),
             'statement': atom['statement'], 'statement_before_standard': atom.get('statement_before_standard') or '',
             'anchor_quote': T.normalise(atom.get('anchor_quote') or ''), 'anchor_page': atom.get('anchor_page'),
             'context': cx, 'T1': lex['T1'], 'T2': lex['T2'], 'T3': lex['T3'], 'windows': {}}
        for w in windows:
            if w == MAIN_WINDOW:
                continue
            cxw, lexw = lexical(case, atom, reqs, w)
            r['windows'][str(w)] = {'context_chars': len(cxw['context']), 'T1': lexw['T1'], 'T2': lexw['T2'], 'context': cxw['context']}
        recs.append(r)
    print(f'{len(recs)} atoms, lexical tests done at {time.time() - t0:.0f}s', file=log, flush=True)

    models = ['main'] + (['second'] if args.second_model else [])
    model_records = {}
    for which in models:
        nli = NLI(which)
        model_records[which] = nli.record()
        # N1 at every window (main model) or at the main window only (second model); N2 once
        wins = windows if which == 'main' else [MAIN_WINDOW]
        for w in wins:
            pairs = [(r['context']['context'] if w == MAIN_WINDOW else r['windows'][str(w)]['context'], r['statement']) for r in recs]
            labs, probs = nli.verdicts(pairs)
            trunc = nli.truncated(pairs)
            for r, l, p, t in zip(recs, labs, probs, trunc):
                rec = {'verdict': l, 'probs': p, 'premise_truncated': t}
                if which == 'main' and w == MAIN_WINDOW:
                    r['N1'] = rec
                elif which == 'main':
                    r['windows'][str(w)]['N1'] = rec
                else:
                    r.setdefault('second_model', {})['N1'] = rec
            print(f'{which} N1 window {w} done at {time.time() - t0:.0f}s', file=log, flush=True)
        fwd = [(r['statement_before_standard'], r['statement']) for r in recs]
        bwd = [(r['statement'], r['statement_before_standard']) for r in recs]
        lf, pf = nli.verdicts(fwd)
        lb, pb = nli.verdicts(bwd)
        for r, a, pa, b, pb_ in zip(recs, lf, pf, lb, pb):
            rec = {'before_to_after': {'verdict': a, 'probs': pa}, 'after_to_before': {'verdict': b, 'probs': pb_},
                   'flag': not (a == 'entailment' and b == 'entailment'), 'both_fail': a != 'entailment' and b != 'entailment'}
            if which == 'main':
                r['N2'] = rec
            else:
                r['second_model']['N2'] = rec
        print(f'{which} N2 done at {time.time() - t0:.0f}s', file=log, flush=True)
        del nli

    for r in recs:
        f = {'T1': r['T1']['flag'], 'T2': r['T2']['flag'], 'T3': r['T3']['flag'],
             'N1': r['N1']['verdict'] != 'entailment', 'N2': r['N2']['flag']}
        f['lexical'] = f['T1'] or f['T2'] or f['T3']
        f['nli'] = f['N1'] or f['N2']
        f['both'] = f['lexical'] and f['nli']
        f['any'] = f['lexical'] or f['nli']
        f['contradiction'] = (r['N1']['verdict'] == 'contradiction' or 'contradiction' in
                              (r['N2']['before_to_after']['verdict'], r['N2']['after_to_before']['verdict']))
        r['flags'] = f
        for w, wr in r['windows'].items():
            wr['flags'] = {'T1': wr['T1']['flag'], 'T2': wr['T2']['flag'], 'N1': wr['N1']['verdict'] != 'entailment'}
            del wr['context']
        if 'second_model' in r:
            s = r['second_model']
            s['flags'] = {'N1': s['N1']['verdict'] != 'entailment', 'N2': s['N2']['flag']}

    counts = count(recs)
    sens = sensitivity(recs, windows, args.second_model)
    out = args.out
    paths.jdump({'atoms': recs}, os.path.join(out, 'atoms.json'))
    paths.jdump(counts, os.path.join(out, 'counts.json'))
    paths.jdump(sens, os.path.join(out, 'sensitivity.json'))
    paths.jdump({'part': 'A', 'reading': __doc__.strip().splitlines()[3:11], 'main_window': MAIN_WINDOW, 'windows': windows,
                 'nli_models': model_records, 'provenance': paths.provenance(files)}, os.path.join(out, 'run-record.json'))
    print(f'written to {out} at {time.time() - t0:.0f}s', file=log, flush=True)


FLAG_KEYS = ['T1', 'T2', 'T3', 'N1', 'N2', 'lexical', 'nli', 'both', 'any', 'contradiction']


def count(recs):
    def tally(rs):
        c = {k: sum(1 for r in rs if r['flags'][k]) for k in FLAG_KEYS}
        c['lexical_only'] = sum(1 for r in rs if r['flags']['lexical'] and not r['flags']['nli'])
        c['nli_only'] = sum(1 for r in rs if r['flags']['nli'] and not r['flags']['lexical'])
        c['N2_both_directions_fail'] = sum(1 for r in rs if r['N2']['both_fail'])
        c['N1_contradiction'] = sum(1 for r in rs if r['N1']['verdict'] == 'contradiction')
        c['N1_premise_truncated'] = sum(1 for r in rs if r['N1']['premise_truncated'])
        c['atoms'] = len(rs)
        return c
    out = {'all': tally(recs), 'scored': tally([r for r in recs if r['scored']]), 'in_N': tally([r for r in recs if r['in_N']]),
           'by_case': {}, 'by_case_and_stratum': {}, 'by_case_scored': {}, 'context_located': {}}
    for case in paths.CASES:
        rs = [r for r in recs if r['case'] == case]
        out['by_case'][case] = tally(rs)
        out['by_case_scored'][case] = tally([r for r in rs if r['scored']])
        out['context_located'][case] = {}
        for r in rs:
            k = r['context']['located']
            out['context_located'][case][k] = out['context_located'][case].get(k, 0) + 1
        for st in sorted({r['stratum'] for r in rs}):
            out['by_case_and_stratum'][f'{case}/{st}'] = tally([r for r in rs if r['stratum'] == st])
    return out


def sensitivity(recs, windows, second):
    out = {'windows': {}, 'second_model': None}
    for w in windows:
        if w == MAIN_WINDOW:
            continue
        k = str(w)
        d = {}
        for t in ('T1', 'T2', 'N1'):
            base = [r['flags'][t] for r in recs]
            alt = [r['windows'][k]['flags'][t] for r in recs]
            d[t] = {'flagged_main': sum(base), 'flagged_at_window': sum(alt),
                    'changed': sum(1 for a, b in zip(base, alt) if a != b),
                    'gained': sum(1 for a, b in zip(base, alt) if b and not a), 'lost': sum(1 for a, b in zip(base, alt) if a and not b)}
        base_any = [r['flags']['any'] for r in recs]
        alt_any = [r['windows'][k]['flags']['T1'] or r['windows'][k]['flags']['T2'] or r['flags']['T3'] or
                   r['windows'][k]['flags']['N1'] or r['flags']['N2'] for r in recs]
        d['any'] = {'flagged_main': sum(base_any), 'flagged_at_window': sum(alt_any), 'changed': sum(1 for a, b in zip(base_any, alt_any) if a != b)}
        d['note'] = 'JRC (anchor only) and Mobility (table1_text) have no window; their flags cannot change.'
        out['windows'][k] = d
    if second:
        d = {}
        for t in ('N1', 'N2'):
            base = [r['flags'][t] for r in recs]
            alt = [r['second_model']['flags'][t] for r in recs]
            d[t] = {'flagged_main': sum(base), 'flagged_second': sum(alt), 'changed': sum(1 for a, b in zip(base, alt) if a != b),
                    'gained': sum(1 for a, b in zip(base, alt) if b and not a), 'lost': sum(1 for a, b in zip(base, alt) if a and not b)}
        v1 = [r['N1']['verdict'] for r in recs]
        v2 = [r['second_model']['N1']['verdict'] for r in recs]
        d['N1_verdict_agreement'] = sum(1 for a, b in zip(v1, v2) if a == b) / len(recs)
        d['N1_contradiction_second'] = sum(1 for v in v2 if v == 'contradiction')
        out['second_model'] = d
    return out


if __name__ == '__main__':
    main()
