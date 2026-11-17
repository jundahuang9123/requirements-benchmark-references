#!/usr/bin/env python3
"""Write the manifest of a new step (D1, RV1-RV3, ...) when it runs (spec 3.7, forward rule).

    RT_SESSION=... python3 tools/trace/record_step.py DESCRIPTION.json

DESCRIPTION.json (kept outside the repository) names the step, its actors, scripts, inputs, outputs,
timing, counts, decision values, evidence and checks. This script adds the hashes: inputs with
hash_time "import" are taken from IMPORT-PROVENANCE.json at the baseline tag, everything else is
hashed now. It writes benchmark-data/reference-sets-v3/trace/steps/<step_id>.json.
Optional: "moves" (files moved unchanged, as given) and "scripts_changed" (path, from_sha256 and the
change; to_sha256 is the current hash). check_backfill.py accepts a pinned script whose change is recorded so.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import POLICY, TRACE, baseline_hashes, file_entry, finalize_manifest, session_block, sha256_file, write_json  # noqa: E402


def main(desc_path):
    d = json.loads(Path(desc_path).read_text(encoding='utf-8'))
    base = baseline_hashes()
    inputs = []
    for item in d['inputs']:
        if item.get('hash_time') == 'import':
            inputs.append(dict(item, sha256=base[item['path']], stored='yes'))
        else:
            inputs.append(file_entry(item['path'], **{k: v for k, v in item.items() if k != 'path'}))
    outputs = [file_entry(o['path'], **{k: v for k, v in o.items() if k != 'path'}) for o in d['outputs']]
    scripts = [dict(s, sha256=sha256_file(s['path'])) for s in d['scripts']]
    manifest = {
        'trace_policy': POLICY,
        'step_id': d['step_id'], 'name': d['name'], 'time_order': d['time_order'],
        'actors': d['actors'],
        'session': session_block(),
        'scripts': scripts,
        'prompts': d.get('prompts', []),
        'inputs': inputs, 'outputs': outputs,
        'timing': d['timing'],
        'seeds': d.get('seeds', {}),
        'counts': d['counts'],
        'decision_values': d['decision_values'],
        'rationale_location': d['rationale_location'],
        'evidence': d['evidence'],
        'checks': d.get('checks', {}),
        'gaps': d.get('gaps', []),
        'notes': d.get('notes', []),
    }
    if 'moves' in d:
        manifest['moves'] = d['moves']
    if 'scripts_changed' in d:
        manifest['scripts_changed'] = [dict(c, to_sha256=sha256_file(c['path'])) for c in d['scripts_changed']]
    out = TRACE + f'steps/{d["step_id"]}.json'
    write_json(out, finalize_manifest(manifest))
    print('wrote', out)


if __name__ == '__main__':
    main(sys.argv[1])
