"""The frozen pools, runs and final labels of the run store (read-only).

Pools: `work/<case>/private/pool-key.json` (PW, PW−D, AW, CB; one need per distinct template-cleaned statement) and
`work/old-baseline/<case>/private/pool-key.json` (OS, its own need IDs). Runs: `private/runs.json` of each workspace
(`counted` = the needs that count, `before_discussion` = PW's state before the discussion). Final labels:
`out/pair-labels.csv` (`final_label`); a pair not in the file is unrelated under the protocol.
"""
import csv
import os

from . import paths

CLOSE = ('equivalent', 'narrower', 'broader')


def workspace(case, pool):
    return os.path.join(paths.WORK, case) if pool == 'main' else os.path.join(paths.WORK, 'old-baseline', case)


def load_pool(case, pool):
    """need_id -> statement, and the files read."""
    p = os.path.join(workspace(case, pool), 'private', 'pool-key.json')
    k = paths.jload(p)
    return {nid: v['statement'] for nid, v in k['needs'].items()}, [p]


def load_runs(case, pool):
    """[(run key, condition key, run number, [need ids])], PW−D as condition 'PM-D'; and the files read."""
    p = os.path.join(workspace(case, pool), 'private', 'runs.json')
    r = paths.jload(p)
    out = []
    for run in r['runs']:
        cond = 'OS' if pool == 'os' else run['condition']
        key = f"{cond}-{run['run']}"
        out.append((key, cond, run['run'], sorted({n for _, n in run['counted']})))
        if run.get('before_discussion') and run['condition'] == 'PM':
            out.append((f"PM-D-{run['run']}", 'PM-D', run['run'], sorted({n for _, n in run['before_discussion']})))
    return out, [p]


def load_labels(case, pool):
    """{(atom_id, need_id): final_label} and the file read."""
    p = os.path.join(workspace(case, pool), 'out', 'pair-labels.csv')
    out = {}
    with open(p, encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            out[(row['atom_id'], row['need_id'])] = row['final_label']
    return out, [p]


def load_final_results(case, pool):
    name = f'{case}-final-results.json'
    p = os.path.join(workspace(case, pool), 'out', name)
    return paths.jload(p), [p]


def final_run_figures(case):
    """Close and Exact per run under the final labels, over N (raw_supported_or_partial) and X (raw_supported):
    {run key: {'N': (close, exact), 'X': (close, exact)}}, PW−D as 'PM-D-<n>', OS as 'OS-<n>'. And the files read."""
    out, files = {}, []
    for pool in ('main', 'os'):
        f, fs = load_final_results(case, pool)
        files += fs
        for key, run in f['runs'].items():
            k = key.replace('CB-', 'OS-') if pool == 'os' else key
            out[k] = {'N': (run['denominators']['raw_supported_or_partial']['close'], run['denominators']['raw_supported_or_partial']['exact']),
                      'X': (run['denominators']['raw_supported']['close'], run['denominators']['raw_supported']['exact']),
                      'needs': run['counted_needs'], 'related': run['needs_related_to_an_atom']}
            bd = run.get('before_discussion')
            if pool == 'main' and isinstance(bd, dict) and 'denominators' in bd:
                out['PM-D-' + key.split('-')[1]] = {
                    'N': (bd['denominators']['raw_supported_or_partial']['close'], bd['denominators']['raw_supported_or_partial']['exact']),
                    'X': (bd['denominators']['raw_supported']['close'], bd['denominators']['raw_supported']['exact']),
                    'needs': None, 'related': None}
    return out, files
