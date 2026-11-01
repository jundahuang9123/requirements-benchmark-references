#!/usr/bin/env python3
"""Phase 1 check of the backfill (the start of validate_trace.py, spec section 5).

    python3 tools/trace/check_backfill.py

Read-only. Resolves every link of every fact and entry against the current tree (file hash, locator,
the item it names, target hash), checks statuses, gaps, indexes, manifests and the step registry, and
reruns recount.py. Outside evidence is checked against its registry only (the files stay outside).
Prints problems and counts; exits non-zero on any problem.
"""
import collections
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (BASELINE_TAG, ROOT, STATUSES, TRACE, file_bytes, load_json, sha256_bytes, sha256_file,  # noqa: E402
                    sha256_json, target_sha256, text_lines)

REGISTRY = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6a', 'R6b', 'R7', 'R8', 'R9', 'R10', 'R11a', 'R11b', 'R11c', 'R11d', 'R12', 'R13', 'D1', 'M1']
problems = []
counts = collections.Counter()


def problem(msg):
    problems.append(msg)


def check_link(where, l, outside):
    counts['links'] += 1
    kind = l.get('kind')
    if kind == 'outside_evidence':
        e = outside.get(l.get('evidence_id'))
        if not e:
            problem(f'{where}: unknown outside evidence {l.get("evidence_id")}')
        elif e.get('sha256') != l.get('sha256'):
            problem(f'{where}: outside evidence hash differs from the registry')
        counts['links_outside'] += 1
        return
    rel, ref = l.get('file'), l.get('git_ref')
    if ref and ref != BASELINE_TAG:
        problem(f'{where}: links may only pin the baseline tag, not {ref}')
        return
    try:
        data = file_bytes(rel, ref)
    except (OSError, subprocess.CalledProcessError, TypeError):
        problem(f'{where}: link target file missing: {rel}' + (f' at {ref}' if ref else ''))
        return
    if sha256_bytes(data) != l.get('file_sha256'):
        problem(f'{where}: hash mismatch for {rel}' + (f' at {ref}' if ref else ''))
        return
    if l.get('hash_time') != ('import' if ref else 'now'):
        problem(f'{where}: hash_time does not match how the link resolves')
    try:
        if target_sha256(rel, l['locator'], ref) != l.get('target_sha256'):
            problem(f'{where}: target hash mismatch in {rel} at {l["locator"]}')
    except (ValueError, KeyError, IndexError) as exc:
        problem(f'{where}: unresolved locator in {rel}: {exc}')
    counts[f'links_{kind}'] += 1
    counts['links_at_baseline' if ref else 'links_in_tree'] += 1


def main():
    outside = {e['evidence_id']: e for e in load_json(TRACE + 'backfill/outside-evidence.json')['items']}
    facts = {}
    for p in sorted((ROOT / TRACE / 'backfill').glob('R*.json')):
        if '-' in p.stem:
            continue  # re-derivation outputs
        d = json.loads(p.read_text(encoding='utf-8'))
        for f in d['facts']:
            fid = f['fact_id']
            if fid in facts:
                problem(f'duplicate fact {fid}')
            facts[fid] = f
            if f['status'] not in STATUSES:
                problem(f'{fid}: bad status {f["status"]}')
            if f['status'] == 'not_recorded' and not f.get('looked_in'):
                problem(f'{fid}: not_recorded without looked_in')
            if f.get('actor') != 'model:claude/backfill':
                problem(f'{fid}: actor is not model:claude/backfill')
            for l in f.get('links', []):
                check_link(fid, l, outside)
            for e in f.get('entries', []):
                counts['entries'] += 1
                if not e.get('links'):
                    problem(f'{e["entry_id"]}: entry without links')
                if e.get('reason_status') not in STATUSES:
                    problem(f'{e["entry_id"]}: bad reason_status')
                for l in e['links']:
                    check_link(e['entry_id'], l, outside)
            counts[f'status_{f["status"]}'] += 0 if fid.endswith('-E') else 1
    counts['facts'] = sum(1 for k in facts if not k.endswith('-E'))
    gaps = load_json(TRACE + 'backfill/gaps.json')['gaps']
    ids = [g['gap_id'] for g in gaps]
    for n in range(1, 62):
        if f'G-{n:03d}' not in ids:
            problem(f'gap G-{n:03d} of spec 2.2 missing')
    for g in gaps:
        if not g.get('looked_in'):
            problem(f'{g["gap_id"]}: no looked_in')
        for fid in g['facts']:
            if fid not in facts:
                problem(f'{g["gap_id"]}: unknown fact {fid}')
    counts['gaps'] = len(gaps)
    for name in ('independent-check', 'codex-register', 'prompts'):
        idx = load_json(TRACE + f'index/{name}.json')
        items = idx.get('items', []) + idx.get('decisions', []) + idx.get('findings_sections', []) + idx.get('register', [])
        for it in items:
            rel = it.get('file') or idx.get('file')
            if sha256_bytes(text_lines(rel, *it['lines'])) != it['lines_sha256']:
                problem(f'index {name} {it.get("index_id") or it.get("prompt_id")}: line hash mismatch')
            counts['index_items'] += 1
    present = sorted(q.stem for q in (ROOT / TRACE / 'steps').glob('*.json'))
    for step in REGISTRY + [s for s in present if s not in REGISTRY]:
        p = ROOT / TRACE / f'steps/{step}.json'
        if not p.exists():
            problem(f'step {step}: no manifest')
            continue
        m = json.loads(p.read_text(encoding='utf-8'))
        body = {k: v for k, v in m.items() if k != 'manifest_sha256'}
        if sha256_json(body) != m.get('manifest_sha256'):
            problem(f'step {step}: manifest_sha256 mismatch')
        for s in m.get('scripts', []):
            if sha256_file(s['path']) != s['sha256'] and not (step == 'D1' or step.startswith('M')):
                problem(f'step {step}: script hash changed: {s["path"]}')
        for fid in m.get('facts', []):
            if fid not in facts:
                problem(f'step {step}: unknown fact {fid}')
        counts['manifests'] += 1
    r = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/trace/recount.py')], capture_output=True, text=True)
    if r.returncode:
        problem('recount.py does not reproduce counts.json')
    print(json.dumps({'problems': len(problems), 'counts': dict(sorted(counts.items()))}, indent=1))
    for p in problems[:50]:
        print('PROBLEM', p)
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
