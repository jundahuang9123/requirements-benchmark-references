#!/usr/bin/env python3
"""Part C. Matching: do the paper's comparisons hold under a non-LLM matcher?

Input: the pools the reviewers saw (every distinct template-cleaned statement once; the OS pool apart) and the case's
atoms in N and X. Pairs: every statement against every atom of N when the grid is small (at most --full-grid-max
pairs), else a prefilter with a fixed sentence-embedding model: the 10 nearest atoms per statement and the 10 nearest
statements per atom (cosine; ties broken by ID). Relation from the two NLI directions (fixed):
  need => atom and atom => need: equivalent;  atom => need only: narrower;  need => atom only: broader;  else none.
Close = atoms with a need equivalent, narrower or broader; Exact = atoms with an equivalent need. No partial, no
Coverage, no Recovered together. Reading, fixed before the run: only the ordering of the conditions is read.

usage: python3 -I part_c.py --out part-c-matching/out/main [--model main|second] [--cases geo,health] [--log FILE]
"""
import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dc import atoms as A, paths, pools as P, relation as R  # noqa: E402
from dc.nli import NLI  # noqa: E402

K = 10
PAIRS = [('S', 'PM'), ('PM', 'PM-D'), ('S', 'OS'), ('S', 'CB'), ('PM', 'CB')]   # the comparisons of the spec
CONDS = ['PM', 'PM-D', 'S', 'CB', 'OS']


def embed(texts):
    from sentence_transformers import SentenceTransformer
    import torch
    torch.manual_seed(0)
    name, rev = paths.EMBED_MODEL
    m = SentenceTransformer(name, revision=rev, device='cpu')
    v = m.encode(texts, batch_size=64, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(v, dtype=np.float64)


def prefilter(stmt_ids, stmt_vecs, atom_ids, atom_vecs, k=K):
    """The candidate pairs: k nearest atoms per statement and k nearest statements per atom."""
    sims = stmt_vecs @ atom_vecs.T          # [statements, atoms]
    cands = set()
    for i, sid in enumerate(stmt_ids):
        order = sorted(range(len(atom_ids)), key=lambda j: (-round(sims[i, j], 9), atom_ids[j]))[:k]
        cands.update((atom_ids[j], sid) for j in order)
    for j, aid in enumerate(atom_ids):
        order = sorted(range(len(stmt_ids)), key=lambda i: (-round(sims[i, j], 9), stmt_ids[i]))[:k]
        cands.update((aid, stmt_ids[i]) for i in order)
    return sorted(cands)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--model', default='main', choices=['main', 'second'])
    ap.add_argument('--cases', default=','.join(paths.CASES))
    ap.add_argument('--full-grid-max', type=int, default=10000, help='full grid when statements x atoms is at most this')
    ap.add_argument('--log', default=None)
    args = ap.parse_args()
    log = open(args.log, 'a') if args.log else sys.stderr
    t0 = time.time()
    cases = args.cases.split(',')
    nli = NLI(args.model)
    files = []
    figures, separations, agreement, prefilter_report, run_rows = {}, {}, {}, {}, {}
    for case in cases:
        d, path = A.load_case(case)
        files.append(path)
        dn = A.denominators(d['atoms'])
        atom_text = {a['id']: a['statement'] for a in d['atoms']}
        atoms_n = sorted(dn['N'])
        atoms_x = set(dn['X'])
        final_fig, fs = P.final_run_figures(case)
        files += fs
        case_pairs = {}
        for pool in ('main', 'os'):
            stmts, fs = P.load_pool(case, pool)
            files += fs
            stmt_ids = sorted(stmts)
            grid = len(stmt_ids) * len(atoms_n)
            full = grid <= args.full_grid_max
            # the prefilter is always computed (for the loss report); it is the candidate set unless the grid is small
            svec = embed([stmts[s] for s in stmt_ids])
            avec = embed([atom_text[a] for a in atoms_n])
            cands_pref = prefilter(stmt_ids, svec, atoms_n, avec)
            cands = sorted((a, s) for a in atoms_n for s in stmt_ids) if full else cands_pref
            print(f'{case}/{pool}: {len(stmt_ids)} statements x {len(atoms_n)} atoms = {grid}; {"full grid" if full else "prefilter"}: {len(cands)} pairs', file=log, flush=True)
            fwd = [(stmts[s], atom_text[a]) for a, s in cands]      # need => atom
            bwd = [(atom_text[a], stmts[s]) for a, s in cands]      # atom => need
            lf, pf = nli.verdicts(fwd)
            lb, pb = nli.verdicts(bwd)
            print(f'{case}/{pool}: NLI done at {time.time() - t0:.0f}s', file=log, flush=True)
            labels, fs = P.load_labels(case, pool)
            files += fs
            recs = []
            rel = {}
            for (a, s), f1, p1, b1, p2 in zip(cands, lf, pf, lb, pb):
                r = R.relation(f1, b1)
                rel[(a, s)] = r
                recs.append({'atom_id': a, 'need_id': s, 'need_entails_atom': f1, 'atom_entails_need': b1,
                             'p_need_entails_atom': p1, 'p_atom_entails_need': p2, 'relation': r, 'final_label': labels.get((a, s), 'unrelated')})
            case_pairs[pool] = {'grid': 'full' if full else f'prefilter k={K}', 'statements': len(stmt_ids), 'atoms_N': len(atoms_n),
                                'candidate_pairs': len(cands), 'pairs': recs}
            # prefilter loss against the final labels (atoms of N only)
            cset = set(cands_pref)
            lost = {}
            for (a, s), lab in labels.items():
                if a in set(atoms_n) and lab != 'unrelated' and (a, s) not in cset:
                    lost[lab] = lost.get(lab, 0) + 1
            kept = {}
            for (a, s), lab in labels.items():
                if a in set(atoms_n) and lab != 'unrelated' and (a, s) in cset:
                    kept[lab] = kept.get(lab, 0) + 1
            prefilter_report[f'{case}/{pool}'] = {'candidate_pairs': len(cands_pref), 'grid_pairs': grid, 'used': 'full grid' if full else 'prefilter',
                                                  'related_pairs_kept': kept, 'related_pairs_lost': lost}
            # per run
            runs, fs = P.load_runs(case, pool)
            files += fs
            for key, cond, n, need_ids in runs:
                cn, en = R.run_figures(rel, need_ids, atoms_n)
                cx, ex = R.run_figures(rel, need_ids, [a for a in atoms_n if a in atoms_x])
                related = sum(1 for s in need_ids if any(rel.get((a, s), 'none') != 'none' for a in atoms_n))
                ff = final_fig.get(key, {})
                run_rows.setdefault(case, {})[key] = {
                    'condition': cond, 'run': n, 'statements': len(need_ids), 'related_share': round(related / len(need_ids), 4) if need_ids else None,
                    'nli': {'close_N': cn, 'exact_N': en, 'close_X': cx, 'exact_X': ex},
                    'final': {'close_N': ff.get('N', (None, None))[0], 'exact_N': ff.get('N', (None, None))[1],
                              'close_X': ff.get('X', (None, None))[0], 'exact_X': ff.get('X', (None, None))[1],
                              'related_share': round(ff['related'] / ff['needs'], 4) if ff.get('needs') else None}}
            # agreement on the pairs both judged
            four = [(r['relation'], r['final_label'] if r['final_label'] in R.CLOSE else 'none_or_partial') for r in recs]
            close = [('close' if a in R.CLOSE else 'not', 'close' if b in R.CLOSE else 'not') for a, b in four]
            either = [(a, b) for a, b in four if a != 'none' or b != 'none_or_partial']
            either_close = [(x, y) for (x, y), (a, b) in zip(close, four) if a != 'none' or b != 'none_or_partial']
            agreement[f'{case}/{pool}'] = {
                'pairs_judged_by_both': len(four), 'kappa_4_class': R.kappa(four), 'kappa_close': R.kappa(close),
                'agreement_4_class': sum(1 for a, b in four if a == b) / len(four) if four else None,
                'pairs_either_relates': len(either), 'kappa_4_class_either_relates': R.kappa(either), 'kappa_close_either_relates': R.kappa(either_close),
                'nli_relations': {k: sum(1 for a, _ in four if a == k) for k in ('equivalent', 'narrower', 'broader', 'none')},
                'final_labels': {k: sum(1 for _, b in four if b == k) for k in ('equivalent', 'narrower', 'broader', 'none_or_partial')},
                'confusion': confusion(four)}
        paths.jdump({'case': case, 'atoms_N': atoms_n, 'atoms_X': sorted(atoms_x), 'pools': case_pairs}, os.path.join(args.out, f'pairs-{case}.json'))
        # per condition
        figures[case] = {}
        rows = run_rows[case]
        for cond in CONDS:
            rr = [v for v in rows.values() if v['condition'] == cond]
            if not rr:
                continue
            figures[case][cond] = {m: {'nli': R.summary([v['nli'][m] for v in rr]), 'final': R.summary([v['final'][m] for v in rr if v['final'][m] is not None])}
                                   for m in ('close_N', 'exact_N', 'close_X', 'exact_X')}
            figures[case][cond]['statements'] = R.summary([v['statements'] for v in rr])
            figures[case][cond]['related_share_nli'] = R.summary([v['related_share'] for v in rr])
            figures[case][cond]['related_share_final'] = R.summary([v['final']['related_share'] for v in rr if v['final']['related_share'] is not None])
        separations[case] = {}
        for a, b in PAIRS:
            ra = [v for v in rows.values() if v['condition'] == a]
            rb = [v for v in rows.values() if v['condition'] == b]
            for m in ('close_N', 'exact_N', 'close_X', 'exact_X'):
                vn = R.separation([v['nli'][m] for v in ra], [v['nli'][m] for v in rb])
                vf = R.separation([v['final'][m] for v in ra if v['final'][m] is not None], [v['final'][m] for v in rb if v['final'][m] is not None])
                separations[case][f'{paths.CONDITION_NAMES[a]} vs {paths.CONDITION_NAMES[b]} @ {m}'] = {
                    'nli': name(vn, a, b), 'final': name(vf, a, b), 'agree': vn == vf}
        print(f'{case} done at {time.time() - t0:.0f}s', file=log, flush=True)

    agree_n = sum(1 for c in separations.values() for v in c.values() if v['agree'])
    total = sum(len(c) for c in separations.values())
    paths.jdump({'per_run': run_rows, 'per_condition': figures}, os.path.join(args.out, 'figures.json'))
    paths.jdump({'verdicts': separations, 'agreeing': agree_n, 'total': total,
                 'rule': 'separated when the ranges over the runs do not overlap; a>b when every run of a is above every run of b'},
                os.path.join(args.out, 'separation.json'))
    paths.jdump(agreement, os.path.join(args.out, 'agreement.json'))
    paths.jdump(prefilter_report, os.path.join(args.out, 'prefilter.json'))
    paths.jdump({'part': 'C', 'reading': __doc__.strip().splitlines()[2:10], 'k': K, 'full_grid_max': args.full_grid_max,
                 'nli_model': nli.record(), 'embedding_model': {'model': paths.EMBED_MODEL[0], 'revision': paths.EMBED_MODEL[1]},
                 'provenance': paths.provenance(files)}, os.path.join(args.out, 'run-record.json'))
    print(f'written to {args.out} at {time.time() - t0:.0f}s', file=log, flush=True)


def name(v, a, b):
    if v is None:
        return None
    if v == 'overlap':
        return 'overlap'
    return f'{paths.CONDITION_NAMES[a]} above' if v == 'a>b' else f'{paths.CONDITION_NAMES[b]} above'


def confusion(four):
    out = {}
    for a, b in four:
        out.setdefault(a, {})
        out[a][b] = out[a].get(b, 0) + 1
    return out


if __name__ == '__main__':
    main()
