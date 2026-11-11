#!/usr/bin/env python3
"""Part B. Evidence labels: do the cited input passages state the atom?

For each scored atom (196) and each stored passage of its `input_evidence.raw.sources`: N1 with the passage as premise
and the atom statement as hypothesis; also N1 with the passages joined (in stored order, separated by a space), and
T1 of the statement against the passages joined. Compared with the adjudicated `human_review.raw_label`:
  supported    expects entailment from at least one passage or from the passages joined
  partial      expects no full entailment (neither a passage nor the joined passages entail)
  unsupported  has no passage to test (an unsupported atom with passages is listed)
A disagreement is a supported atom with no entailing passage, or a partial atom that a passage entails. Supported
atoms the adjudication filed under "rule 2: bare mention" are listed apart: the rule is more lenient than entailment.

usage: python3 -I part_b.py --out part-b-evidence-labels/out [--second-model] [--log FILE]
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dc import atoms as A, paths, textrules as T  # noqa: E402
from dc.nli import NLI  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--second-model', action='store_true')
    ap.add_argument('--log', default=None)
    args = ap.parse_args()
    log = open(args.log, 'a') if args.log else sys.stderr
    t0 = time.time()

    everything, files = A.all_atoms()
    recs = []
    for case, atom, _ in everything:
        if not atom.get('scored_by_default'):
            continue
        ie = atom['input_evidence']
        raw = ie.get('raw') or {}
        hr = ie.get('human_review') if isinstance(ie.get('human_review'), dict) else {}
        srcs = raw.get('sources') or []
        passages = [T.normalise(s.get('quote') or '') for s in srcs]
        joined = ' '.join(p for p in passages if p)
        recs.append({'id': atom['id'], 'case': case, 'stratum': atom.get('stratum'), 'statement': atom['statement'],
                     'raw_label': hr.get('raw_label'), 'category': hr.get('category'), 'label_ai_2210': raw.get('label'),
                     'passages': [{'path': s.get('path'), 'locator': s.get('locator'), 'quote': p} for s, p in zip(srcs, passages)],
                     'joined_chars': len(joined), 'T1': T.t1(atom['statement'], joined) if joined else None, '_joined': joined})
    print(f'{len(recs)} scored atoms, {sum(len(r["passages"]) for r in recs)} passages', file=log, flush=True)

    models = ['main'] + (['second'] if args.second_model else [])
    model_records = {}
    for which in models:
        nli = NLI(which)
        model_records[which] = nli.record()
        pairs, where = [], []
        for i, r in enumerate(recs):
            for j, p in enumerate(r['passages']):
                pairs.append((p['quote'], r['statement']))
                where.append((i, j))
            if r['_joined']:
                pairs.append((r['_joined'], r['statement']))
                where.append((i, 'joined'))
        labs, probs = nli.verdicts(pairs)
        trunc = nli.truncated(pairs)
        key = 'N1' if which == 'main' else 'N1_second'
        for (i, j), l, p, t in zip(where, labs, probs, trunc):
            rec = {'verdict': l, 'probs': p, 'premise_truncated': t}
            if j == 'joined':
                recs[i][key + '_joined'] = rec
            else:
                recs[i]['passages'][j][key] = rec
        print(f'{which}: {len(pairs)} pairs done at {time.time() - t0:.0f}s', file=log, flush=True)
        del nli

    for r in recs:
        del r['_joined']
        for key in [k for k in ('N1', 'N1_second') if any(key_in(p, k) for p in r['passages']) or (k + '_joined') in r]:
            vs = [p[key]['verdict'] for p in r['passages']]
            jv = r.get(key + '_joined', {}).get('verdict')
            ent_any = 'entailment' in vs or jv == 'entailment'
            res = {'passages': len(vs), 'entailing_passages': vs.count('entailment'), 'contradicting_passages': vs.count('contradiction'),
                   'joined_verdict': jv, 'entailed': ent_any}
            lab = r['raw_label']
            if lab == 'supported':
                res['expected'] = 'entailment from a passage or the joined passages'
                res['disagreement'] = 'supported_not_entailed' if not ent_any else None
                res['bare_mention'] = r['category'] == 'rule 2: bare mention'
            elif lab == 'partial':
                res['expected'] = 'no full entailment'
                res['disagreement'] = 'partial_entailed' if ent_any else None
            else:
                res['expected'] = 'no passage'
                res['disagreement'] = 'unsupported_with_passages' if vs else None
            r['result' if key == 'N1' else 'result_second'] = res

    counts = count(recs)
    paths.jdump({'atoms': recs}, os.path.join(args.out, 'atoms.json'))
    paths.jdump(counts, os.path.join(args.out, 'counts.json'))
    paths.jdump({'part': 'B', 'reading': __doc__.strip().splitlines()[2:12], 'nli_models': model_records,
                 'provenance': paths.provenance(files)}, os.path.join(args.out, 'run-record.json'))
    print(f'written to {args.out} at {time.time() - t0:.0f}s', file=log, flush=True)


def key_in(p, k):
    return k in p


def count(recs):
    def tally(rs, rk='result'):
        c = {'atoms': len(rs), 'passages': sum(len(r['passages']) for r in rs)}
        for lab in ('supported', 'partial', 'unsupported'):
            sub = [r for r in rs if r['raw_label'] == lab]
            d = {'atoms': len(sub), 'with_passages': sum(1 for r in sub if r['passages']),
                 'entailed': sum(1 for r in sub if r[rk]['entailed']),
                 'T1_flagged': sum(1 for r in sub if r['T1'] and r['T1']['flag']),
                 'any_passage_contradicts': sum(1 for r in sub if r[rk]['contradicting_passages'])}
            if lab == 'supported':
                d['not_entailed'] = sum(1 for r in sub if r[rk]['disagreement'])
                d['not_entailed_bare_mention'] = sum(1 for r in sub if r[rk]['disagreement'] and r[rk]['bare_mention'])
                d['bare_mention_atoms'] = sum(1 for r in sub if r[rk]['bare_mention'])
            elif lab == 'partial':
                d['entailed_by_a_passage_or_joined'] = sum(1 for r in sub if r[rk]['disagreement'])
            else:
                d['with_passages_listed'] = sum(1 for r in sub if r[rk]['disagreement'])
            c[lab] = d
        c['disagreements'] = sum(1 for r in rs if r[rk]['disagreement'])
        c['premise_truncated'] = sum(1 for r in rs for p in r['passages'] if p['N1' if rk == 'result' else 'N1_second']['premise_truncated'])
        return c
    out = {'all': tally(recs), 'by_case': {c: tally([r for r in recs if r['case'] == c]) for c in paths.CASES}}
    if recs and 'result_second' in recs[0]:
        out['second_model'] = {'all': tally(recs, 'result_second'), 'by_case': {c: tally([r for r in recs if r['case'] == c], 'result_second') for c in paths.CASES}}
        a = [r['result']['disagreement'] for r in recs]
        b = [r['result_second']['disagreement'] for r in recs]
        out['second_model']['disagreement_changed'] = sum(1 for x, y in zip(a, b) if bool(x) != bool(y))
    return out


if __name__ == '__main__':
    main()
