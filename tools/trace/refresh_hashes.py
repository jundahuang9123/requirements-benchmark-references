#!/usr/bin/env python3
"""M<n> step: refresh files_sha256 in IMPORT-PROVENANCE.json and record the refresh (spec 3.1, 3.7).

    RT_SESSION=... python3 tools/trace/refresh_hashes.py M1 "reason" [--started ISO]

Stage every new or changed file under benchmark-data/ first (git add, named files only): the refreshed
manifest covers exactly the files git tracks or has staged. The step writes its own manifest
trace/steps/<ID>.json first, listing every entry it adds, changes or removes; then it writes
IMPORT-PROVENANCE.json, including the entry for that manifest. IMPORT-PROVENANCE.json therefore cannot
carry its own hash in the manifest: the export check (tools/export_anonymous.py) verifies it instead.
The script ends by re-checking that every file under benchmark-data/ matches its entry.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BM, POLICY, ROOT, TRACE, finalize_manifest, git, now_utc, session_block, sha256_file, write_json  # noqa: E402

PROV = 'IMPORT-PROVENANCE.json'


def tracked_bm():
    files = [p for p in git('ls-files', '-z', '--cached').decode().split('\0') if p.startswith(BM)]
    deleted = set(git('ls-files', '-z', '--deleted').decode().split('\0')) - {''}
    return sorted(p for p in files if p not in deleted)


def write_provenance(prov):
    prov['files_sha256'] = dict(sorted(prov['files_sha256'].items()))
    (ROOT / PROV).write_text(json.dumps(prov, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('step_id')
    ap.add_argument('reason')
    ap.add_argument('--started')
    args = ap.parse_args()
    started = args.started or now_utc()
    own = TRACE + f'steps/{args.step_id}.json'
    prov = json.loads((ROOT / PROV).read_text(encoding='utf-8'))
    before = dict(prov['files_sha256'])
    files = [p for p in tracked_bm() if p != own]
    after = {p: sha256_file(p) for p in files}
    added = {p: h for p, h in after.items() if p not in before}
    changed = {p: h for p, h in after.items() if p in before and before[p] != h}
    removed = sorted(p for p in before if p not in after and p != own)
    manifest = {
        'trace_policy': POLICY,
        'step_id': args.step_id, 'name': 'Refresh files_sha256 in IMPORT-PROVENANCE.json',
        'time_order': 'after the step whose files it covers; see reason',
        'actors': [{'actor': f'script:tools/trace/refresh_hashes.py#{sha256_file("tools/trace/refresh_hashes.py")}'},
                   {'actor': 'model:claude/manifest-refresh', 'role': 'ran the script'}],
        'session': session_block(),
        'scripts': [{'path': 'tools/trace/refresh_hashes.py', 'sha256': sha256_file('tools/trace/refresh_hashes.py'),
                     'rerunnable': 'yes', 'postdates_step': 'no'},
                    {'path': 'tools/trace/common.py', 'sha256': sha256_file('tools/trace/common.py'),
                     'rerunnable': 'yes', 'postdates_step': 'no'}],
        'prompts': [],
        'inputs': [{'path': PROV, 'sha256': sha256_file(PROV), 'hash_time': 'step', 'stored': 'yes',
                    'count': len(before)}],
        'outputs': [{'path': PROV, 'sha256': None, 'hash_time': 'step', 'stored': 'yes', 'count': len(after) + 1,
                     'note': 'Written after this manifest and containing its hash, so its own hash cannot be '
                             'recorded here; tools/export_anonymous.py checks every entry.'}],
        'timing': {'run_started': started, 'run_ended': None, 'run_by': 'model:claude/manifest-refresh'},
        'seeds': {},
        'counts': {'in': len(before), 'out': len(after) + 1, 'changed': len(added) + len(changed) + len(removed) + 1},
        'decision_values': ['entry_added', 'entry_changed', 'entry_removed'],
        'rationale_location': 'reason below',
        'reason': args.reason,
        'entries_added': added, 'entries_changed': changed, 'entries_removed': removed,
        'own_entry': 'added to IMPORT-PROVENANCE.json after this manifest was written',
        'evidence': ['tools/export_anonymous.py:60-65'],
        'gaps': [],
    }
    manifest['timing']['run_ended'] = now_utc()
    write_json(own, finalize_manifest(manifest))
    after[own] = sha256_file(own)
    prov['files_sha256'] = after
    write_provenance(prov)
    # Re-check: every tracked or staged file under benchmark-data/, plus this manifest, matches its entry.
    final = json.loads((ROOT / PROV).read_text(encoding='utf-8'))['files_sha256']
    expected = {p: sha256_file(p) for p in set(files) | {own}}
    if final != expected:
        raise SystemExit('files_sha256 does not match the tree after the refresh')
    print(f'{args.step_id}: {len(added)} added, {len(changed)} changed, {len(removed)} removed, plus its own manifest')


if __name__ == '__main__':
    main()
