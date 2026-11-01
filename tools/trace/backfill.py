#!/usr/bin/env python3
"""Backfill of the history steps R0-R13 (spec sections 2, 3 and 7).

    RT_SESSION=... RT_EVIDENCE_DIR=... RT_EVIDENCE_MAP=... python3 tools/trace/backfill.py --written-at ISO

Writes, under benchmark-data/reference-sets-v3/trace/:
  backfill/<step>.json        history facts and per-item decision entries (3.5), with pointers and hashes
  backfill/outside-evidence.json  logs and workspace files kept outside the repository (decision 0.9)
  backfill/gaps.json          every gap of spec 2.2 (G-001..G-061) and the gaps found since
  steps/<step>.json           one manifest per registry row (3.7)
  DECISIONS.json              the owner's decisions of section 0

Every fact names its actor (model:claude/backfill), carries a status (3.2) and either links that a
script can resolve (file, locator, target_sha256) or, when it is missing, where it was looked for.
Outside evidence is referenced by sha256 only. Run it after indexes.py and rederive.py; it reads their
outputs. The output depends only on the tree, the evidence bundle and --written-at.
"""
import argparse
import collections
import csv
import io
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (BASELINE_TAG, BM, CASES, POLICY, ROOT, STATUSES, TRACE, V3, baseline_hashes,  # noqa: E402
                    finalize_manifest, git, link, load_json, session_block, sha256_bytes, sha256_file, write_json)

HB = V3 + 'history/build-scripts/'
IC = V3 + 'INDEPENDENT-CHECK.md'
CODEX = V3 + 'CODEX-REVIEW-2026-10-23.md'
README3 = V3 + 'README.md'
ADJ = HB + 'v3/adjudication_2026_10_23.py'
BUILD = HB + 'v3/build_v3.py'
METH = BM + 'BENCHMARK-METHODOLOGY.md'
V1_FILES = {'mobilitydcat': 'consolidated-requirements.json', 'healthdcat': 'curated-requirements.json',
            'statdcat': 'requirements-and-resolutions.json', 'geodcat': 'alignment-requirements.json',
            'jrc-research': 'core-requirements.json'}
V2_DIR = V3 + 'history/v2-completion/'
V2_FILES = {'healthdcat': 'curated-requirements-v2.json', 'statdcat': 'requirements-and-resolutions-v2.json',
            'geodcat': 'alignment-requirements-v2.json', 'jrc-research': 'core-requirements-v2.json'}
PLANS = [HB + 'v3/plan_health.py', HB + 'v3/plan_other.py', HB + 'v3/plan_mobility_v3.py']
BACKFILL_ACTOR = 'model:claude/backfill'
FOLLOW_UP = 'adjudication follow-up'

# Files outside the repository (decision 0.9): ID, neutral label, step. Where each file sits in the owner's
# evidence bundle is kept outside the repository too (RT_EVIDENCE_MAP), like pseudonym mappings.
OUTSIDE = [
    ('OE-01', 'R9 independent-checker subagent log (22 Oct)', 'R9'),
    ('OE-02', 'R10 labeller log: Health H-1 to H-33', 'R10'),
    ('OE-03', 'R10 labeller log: Health H-34 to H-69', 'R10'),
    ('OE-04', 'R10 labeller log: Mobility, policy inputs', 'R10'),
    ('OE-05', 'R10 labeller log: Mobility, standards inputs', 'R10'),
    ('OE-06', 'R10 labeller log: Mobility, literature inputs', 'R10'),
    ('OE-07', 'R10 labeller log: Mobility, partner (consolidation) inputs', 'R10'),
    ('OE-08', 'R10 labeller log: Geo', 'R10'),
    ('OE-09', 'R10 labeller log: Stat and JRC', 'R10'),
    ('OE-10', 'Build output of the label merge (labels-merged.json, 22 Oct)', 'R10'),
    ('OE-11', 'Build log of the R10 integration build (22 Oct)', 'R6b'),
    ('OE-12', 'Health plan table before the R9 fixes', 'R9'),
    ('OE-13', 'Stat, Geo and JRC plan table before the R9 fixes', 'R9'),
    ('OE-14', 'Mobility plan before the Table 1 re-check', 'R7'),
    ('OE-15', 'build_v3.py before the adjudication hook', 'R6b'),
    ('OE-16', 'make_readme.py before the adjudication', 'R6b'),
    ('OE-17', 'base_registry.json, the input of history/build-scripts/v2/verify.py', 'R4'),
    ('OE-18', 'pdftotext extraction used for anchors: Health D6.2', 'R8'),
    ('OE-19', 'pdftotext extraction used for anchors: Health D6.2 (raw mode)', 'R8'),
    ('OE-20', 'pdftotext extraction used for anchors: Stat', 'R8'),
    ('OE-21', 'pdftotext extraction used for anchors: Stat (raw mode)', 'R8'),
    ('OE-22', 'pdftotext extraction used for anchors: Geo', 'R8'),
    ('OE-23', 'pdftotext extraction used for anchors: Geo (raw mode)', 'R8'),
    ('OE-24', 'R9 checker sample file (the 30 sampled IDs)', 'R9'),
]
OE_FIRST_COMMIT = ('OE-25', "The repository's first commit (the import, before sanitising), parent of the baseline tag", None, 'R0')


class Ctx:
    def __init__(self, written_at, evidence_dir):
        self.written_at = written_at
        self.evid = Path(evidence_dir)
        man = {r['path']: r for r in csv.DictReader(open(self.evid / 'MANIFEST.tsv', encoding='utf-8'), delimiter='\t')}
        self.oe = {}
        where = json.loads(Path(os.environ['RT_EVIDENCE_MAP']).read_text(encoding='utf-8'))
        for oid, label, step in OUTSIDE:
            path = where[oid]
            r = man[path]
            if sha256_bytes((self.evid / path).read_bytes()) != r['sha256']:
                raise SystemExit(f'{path}: bundle file does not match its manifest')
            self.oe[oid] = {'evidence_id': oid, 'label': label, 'sha256': r['sha256'], 'bytes': int(r['bytes']),
                            'mtime_utc': r['mtime_utc'], 'step': step, '_path': path}
        oid, label, _, step = OE_FIRST_COMMIT
        self.oe[oid] = {'evidence_id': oid, 'label': label, 'sha256': None, 'step': step,
                        'reference': f'git: parent of tag {BASELINE_TAG}'}
        self.cases = {c: load_json(f'{V3}{c}.json') for c in CASES}
        self.atom_index = {c: {a['id']: i for i, a in enumerate(d['atoms'])} for c, d in self.cases.items()}
        self.row_index = {c: {r['id']: i for i, r in enumerate(d['requirements'])} for c, d in self.cases.items()}

    # ---- links
    def atom_link(self, case, aid, label='atom'):
        return link(label, 'row', f'{V3}{case}.json', json_pointer=f'/atoms/{self.atom_index[case][aid]}', names={'id': aid})

    def row_link(self, case, rid, label='parent row'):
        return link(label, 'row', f'{V3}{case}.json', json_pointer=f'/requirements/{self.row_index[case][rid]}', names={'id': rid})

    def lines(self, label, rel, a, b=None, names=None, kind='script'):
        loc = {'lines': [a, b or a]}
        if names:
            loc['names'] = names
        return link(label, kind, rel, **loc)

    def ptr(self, label, rel, pointer, names=None, kind='row'):
        loc = {'json_pointer': pointer}
        if names:
            loc['names'] = names
        return link(label, kind, rel, **loc)

    def whole(self, label, rel, kind='script'):
        return link(label, kind, rel, whole_file=True)

    def oe_link(self, oid, locator=None, label=None):
        e = self.oe[oid]
        out = {'label': label or e['label'], 'kind': 'outside_evidence', 'evidence_id': oid, 'sha256': e['sha256']}
        if e.get('reference'):
            out['reference'] = e['reference']
        if locator:
            out['locator'] = locator
        return out

    def jsonl_locators(self, oid):
        """Line numbers in an outside JSONL log: first model field, first and last timestamp."""
        lines = (self.evid / self.oe[oid]['_path']).read_text(encoding='utf-8').splitlines()
        model_line, models, ts = None, set(), []
        for n, l in enumerate(lines, start=1):
            d = json.loads(l)
            msg = d.get('message')
            if isinstance(msg, dict) and msg.get('model'):
                models.add(msg['model'])
                model_line = model_line or n
            if d.get('timestamp'):
                ts.append((n, d['timestamp']))
            ver = d.get('version')
        version = next((json.loads(l).get('version') for l in lines if json.loads(l).get('version')), None)
        return {'model_line': model_line, 'models': sorted(models), 'first': ts[0], 'last': ts[-1], 'cc_version': version}

    # ---- facts
    def fact(self, step, n, field, value, status, links=(), looked_in=None, note=None, **extra):
        if status not in STATUSES:
            raise ValueError(status)
        f = {'fact_id': f'{step}-F{n:02d}', 'step': step, 'field': field, 'value': value, 'status': status,
             'links': list(links), 'actor': BACKFILL_ACTOR, 'signoff': 'pending'}
        if status == 'not_recorded':
            if not looked_in:
                raise ValueError(f'{f["fact_id"]}: not_recorded needs looked_in')
            f['looked_in'] = looked_in
        elif looked_in:
            f['looked_in'] = looked_in
        if not f['links'] and status not in ('not_recorded', 'withheld', 'not_applicable'):
            raise ValueError(f'{f["fact_id"]}: a {status} fact needs links')
        if note:
            f['note'] = note
        f.update(extra)
        return f

    def entries(self, step, rule, items, status='reconstructed', note=None):
        return {'fact_id': f'{step}-E', 'step': step, 'field': 'entries', 'rule': rule, 'status': status,
                'count': len(items), 'entries': items, 'actor': BACKFILL_ACTOR, 'signoff': 'pending',
                **({'note': note} if note else {})}


def entry(step, case, item_id, decision, value, reason=None, reason_status='not_recorded', actors=(), links=(), k=None,
          date=None, date_status='not_recorded', script=None, prompt=None, inputs=(), outputs=()):
    eid = f'{step}:{case}:{item_id}' + (f':{k}' if k is not None else '')
    e = {'entry_id': eid, 'step': step, 'decision': decision, 'value': value, 'reason': reason,
         'reason_status': reason_status, 'actors': list(actors), 'prompt': prompt or {'status': 'not_applicable'},
         'script': script or {'status': 'not_recorded'}, 'inputs': list(inputs), 'outputs': list(outputs),
         'date': date, 'date_status': date_status, 'links': list(links)}
    if not e['links']:
        raise ValueError(f'{eid}: an entry needs at least one link')
    return e


def model_actor(role, model_status='not_recorded', model_id=None, **extra):
    return dict({'actor': f'model:claude/{role}', 'model_id': model_id, 'model_id_status': model_status}, **extra)


# ======================================================================== steps
def r0(cx):
    S = 'R0'
    base = baseline_hashes()
    now = {p: sha256_file(p) for p in base}
    changed_by_sanitising = git('diff', '--name-only', f'{BASELINE_TAG}~1', BASELINE_TAG).decode().split()
    return [
        cx.fact(S, 1, 'snapshot', f'tag {BASELINE_TAG}: the sanitised snapshot the trace starts from', 'recorded',
                [cx.whole('IMPORT-PROVENANCE.json at the baseline', 'IMPORT-PROVENANCE.json', kind='row')],
                note='The repository has two commits: an import commit and the sanitising commit by "Anonymous Curator", which the tag marks.'),
        cx.fact(S, 2, 'files_sha256 at import vs now', f'{sum(now[p] == h for p, h in base.items())} of {len(base)} files match',
                'reconstructed (verified)', [cx.whole('IMPORT-PROVENANCE.json', 'IMPORT-PROVENANCE.json', kind='row')],
                note='Rechecked on a clean clone in Phase 0 and again here; the uncommitted working tree of the audit is excluded (decision 0.3).'),
        cx.fact(S, 3, 'import commit author', None, 'withheld', looked_in=['git history: author of the first commit'],
                note='The first commit is authored under the owner\'s own account; removed for anonymity. No hash is kept.'),
        cx.fact(S, 4, 'upstream history and snapshot labels', None, 'withheld',
                [cx.lines('README.md', 'README.md', 7, kind='row'), cx.lines('ANONYMIZATION.md', 'ANONYMIZATION.md', 11, 15, kind='row')],
                note='The snapshot labels (import-snapshot, pre-adjudication-snapshot, adjudicated-snapshot, audit-snapshot) replace upstream '
                     'identifiers. The first commit still holds the unsanitised files (outside evidence OE-25, owner only).'),
        cx.fact(S, 5, 'sanitising transformations', {'files_changed': len(changed_by_sanitising), 'files': changed_by_sanitising},
                'reconstructed', [cx.ptr('transformations', 'IMPORT-PROVENANCE.json', '/transformations', kind='row'),
                                  cx.lines('IMPORT-VALIDATION.md', 'IMPORT-VALIDATION.md', 5, kind='row'), cx.oe_link('OE-25')],
                note='Derived from the difference between the two commits. Replaced: PR numbers, local paths, commit-like IDs, the owner\'s name '
                     'and handle, GitHub URLs. Stored history scripts, prompts and two packets are therefore verbatim only after sanitising.'),
        cx.fact(S, 6, 'uncommitted mock-benchmark working tree', 'left out; the trace describes the committed tree', 'recorded',
                [cx.ptr('decision 0.3', TRACE + 'DECISIONS.json', '/decisions/2', names={'id': '0.3'}, kind='row')]),
    ]


def r1(cx):
    S = 'R1'
    links, n_art, ok = [], 0, 0
    for case in ['epos'] + CASES:
        m = f'{BM}{case}/provenance/manifest.json'
        links.append(cx.whole(f'{case} provenance manifest', m, kind='row'))
        for a in load_json(m)['artifacts']:
            n_art += 1
            path = ROOT / BM / case / a['local_filename']
            ok += path.exists() and sha256_bytes(path.read_bytes()) == a['sha256']
    mob = load_json(f'{BM}mobilitydcat/provenance/manifest.json')['artifacts']
    jrc = load_json(f'{BM}jrc-research/provenance/manifest.json')['artifacts']
    nap = next(i for i, a in enumerate(mob) if a['id'] == 'napcore-report')
    pap = next(i for i, a in enumerate(jrc) if a['id'] == 'jrc-paper')
    return [
        cx.fact(S, 1, 'artifact hashes', f'{ok} of {n_art} manifest artifacts match their stored files', 'reconstructed (verified)', links),
        cx.fact(S, 2, 'acquisition snapshot date', '2026-10-07', 'recorded', [cx.lines('BM/README.md', BM + 'README.md', 7, kind='row')]),
        cx.fact(S, 3, 'NAPCORE report (Mobility Table 1)', 'citation only; redistribution rights not established, so no frozen copy (0.4a not possible)',
                'recorded', [cx.ptr('napcore-report licence', f'{BM}mobilitydcat/provenance/manifest.json', f'/artifacts/{nap}', names={'id': 'napcore-report'}, kind='source'),
                             cx.lines('THIRD-PARTY-NOTICES.md', BM + 'THIRD-PARTY-NOTICES.md', 38, 41, kind='row')]),
        cx.fact(S, 4, 'JRC paper', 'citation only; redistribution rights not established, so no frozen copy (0.4a not possible)',
                'recorded', [cx.ptr('jrc-paper licence', f'{BM}jrc-research/provenance/manifest.json', f'/artifacts/{pap}', names={'id': 'jrc-paper'}, kind='source')]),
        cx.fact(S, 5, 'web copies read on 22 Oct (NAPCORE Table 1, JRC paper)', None, 'not_recorded',
                looked_in=[f'{BM}mobilitydcat/provenance/manifest.json', f'{BM}jrc-research/provenance/manifest.json', README3 + ':39,136',
                           V3 + 'validate_v3.py:27-33', 'the build workspace and session scratch of 22-23 Oct (outside the repository)']),
        cx.fact(S, 6, "Health's scope as the curator's choice", 'scoped curator representation', 'recorded',
                [cx.lines('methodology', METH, 13, 16, kind='row')]),
    ]


def r2(cx):
    S = 'R2'
    allow = load_json(BM + 'runtime-inputs.json')['benchmarks']
    table = {c: {k: len(v) for k, v in cfg.items() if isinstance(v, list)} for c, cfg in allow.items()}
    return [
        cx.fact(S, 1, 'roles and allowlists', table, 'reconstructed', [cx.whole('runtime-inputs.json', BM + 'runtime-inputs.json', kind='row')]),
        cx.fact(S, 2, 'dated decision: development split', 'JRC and all of Stat for development (16 Oct 2026)', 'recorded',
                [cx.lines('methodology', METH, 175, 176, kind='row')],
                actor_of_decision={'actor': 'human:curator', 'status': 'attested_log', 'evidence': cx.oe_link('OE-25', {'file': METH, 'line': 175})},
                note='The sanitised text says "Curator"; the first commit shows it replaced the owner\'s name, so the actor is the human curator.'),
        cx.fact(S, 3, 'who assigned each role, and when', None, 'not_recorded',
                looked_in=[BM + 'runtime-inputs.json', BM + '*/provenance/manifest.json', METH, BM + 'README.md']),
        cx.fact(S, 4, 'corpus validator: 0 errors at acquisition, 30 at import', 'never reconciled', 'not_recorded',
                [cx.ptr('errors at import', 'IMPORT-CORPUS-VALIDATION.json', '/errors', kind='row'),
                 cx.ptr('errors at acquisition', BM + 'VALIDATION-REPORT.json', '/errors', kind='row')],
                looked_in=['IMPORT-VALIDATION.md:8', 'IMPORT-CORPUS-VALIDATION.json', BM + 'VALIDATION-REPORT.json'],
                note='30 errors: 26 duplicate-path artefacts, 3 Mobility leakage flags, 1 unregistered use-cases.json. A re-run gives the same 30.'),
        cx.fact(S, 5, 'when the allowlist check was added to validate_v3.py', None, 'not_recorded',
                [cx.lines('absent at the Codex review', CODEX, 79, kind='row'), cx.lines('present at import', V3 + 'validate_v3.py', 182, 183)],
                looked_in=[CODEX, V3 + 'validate_v3.py', V3 + 'history/'], note='Bounded: absent in the reviewed version (CODEX:79), present at import.'),
    ]


def v1_rows(cx):
    out = {}
    for case, f in V1_FILES.items():
        rel = f'{BM}{case}/reference-requirements/{f}'
        out[case] = (rel, {r['id']: i for i, r in enumerate(load_json(rel)['requirements'])})
    return out


def r3(cx):
    S = 'R3'
    v1 = v1_rows(cx)
    items = []
    for case in CASES:
        rel, idx = v1[case]
        for r in cx.cases[case]['requirements']:
            if r['added_in'] != 'v1':
                continue
            items.append(entry(S, case, r['id'], 'published_row_kept', {'statement_kind': r.get('statement_kind')},
                               actors=[{'actor': 'unresolved:curator-label', 'status': 'not_recorded'}],
                               links=[cx.ptr('v1 row', rel, f'/requirements/{idx[r["id"]]}', names={'id': r['id']}),
                                      cx.row_link(case, r['id'], 'v3 row')]))
    return [
        cx.fact(S, 1, 'actor', 'curator (role label); machine assistance not stated', 'not_recorded',
                looked_in=[BM + '*/reference-requirements/', BM + '*/provenance/manifest.json', 'ANONYMIZATION.md:5-6'],
                note='curated_by is on 0 of 75 rows. The manifests say "Curator-authored"; that label is the original wording, not a sanitised name, '
                     'so it cannot be assigned to the human or to Claude (unresolved:curator-label).'),
        cx.fact(S, 2, 'date and rule of the v1 rows', None, 'not_recorded', looked_in=[BM + 'README.md', METH, BM + '*/README.md']),
        cx.fact(S, 3, 'independent review of the v1 rows', 'required before quantitative use; not done', 'not_recorded',
                [cx.lines('requirement', BM + 'README.md', 9, 11, kind='row')], looked_in=[BM + 'README.md', METH, V3]),
        cx.entries(S, 'One entry per published v1 row: the v1 file names the row and the v3 row keeps its ID.', items),
    ]


def r4(cx):
    S = 'R4'
    return [
        cx.fact(S, 1, 'actor', 'Claude, single coder', 'recorded', [cx.lines('template', HB + 'v2/template.html', 216, names=['Single coder (Claude)'], kind='row')]),
        cx.fact(S, 2, 'model ID and prompt', None, 'not_recorded',
                looked_in=[HB + 'v2/', V3 + 'history/README.md', 'outside: the build workspace of 22 Oct (no log of this step)']),
        cx.fact(S, 3, 'codes P1-P7 (problem)', 'defined', 'recorded', [cx.lines('codes', HB + 'v2/codes.py', 7, 8, names=['P1 Discover', 'P2 Access'], kind='row')],
                note='Phase 0 correction: the spec said P1 and P2 were undefined.'),
        cx.fact(S, 4, 'meaning of conf (high, med, low)', None, 'not_recorded', looked_in=[HB + 'v2/codes.py:1-16', HB + 'v2/template.html', HB + 'v2/rows.json']),
        cx.fact(S, 5, 'base_registry.json, input of verify.py', 'kept outside the repository', 'attested_log',
                [cx.lines('verify.py reads it', HB + 'v2/verify.py', 4), cx.oe_link('OE-17')]),
        cx.fact(S, 6, 'web cross-checks of the Mobility derivations', None, 'not_recorded',
                [cx.lines('claim', HB + 'v2/codes.py', 199, kind='row')], looked_in=[HB + 'v2/', 'outside: build workspace']),
        cx.fact(S, 7, 'outputs', {'rows.json': 75, 'coding csv': 75}, 'recorded',
                [cx.whole('rows.json', HB + 'v2/rows.json', kind='row'),
                 cx.whole('coding', V3 + 'history/v1-comparison-2026-10-22/reference-requirements-coding.csv', kind='row'),
                 cx.whole('comparison page', V3 + 'history/v1-comparison-2026-10-22/reference-requirements-comparison.html', kind='row')],
                note='The note key is on all 75 rows of rows.json and non-empty on 71. R4 is traced at step level only.'),
    ]


def r5(cx):
    S = 'R5'
    review = V2_DIR + 'reference-completion-review.csv'
    items = []
    for case, f in V2_FILES.items():
        rel = f'{V2_DIR}{case}/reference-requirements/{f}'
        idx = {r['id']: i for i, r in enumerate(load_json(rel)['requirements'])}
        for r in cx.cases[case]['requirements']:
            if r['added_in'] != 'v2':
                continue
            note = r.get('note') or None
            items.append(entry(S, case, r['id'], 'row_added_in_v2', {'statement_kind': r.get('statement_kind'), 'level': r.get('level')},
                               reason=note, reason_status='recorded' if note else 'not_recorded',
                               actors=[model_actor('completion')], date='2026-10-22', date_status='recorded',
                               links=[cx.ptr('v2 row', rel, f'/requirements/{idx[r["id"]]}', names={'id': r['id']}),
                                      cx.row_link(case, r['id'], 'v3 row'), link('review row', 'row', review, csv_key=['id', r['id']])]))
    return [
        cx.fact(S, 1, 'actor', 'Claude (Anthropic), acting as curator', 'recorded',
                [cx.lines('completion.py', HB + 'v2/completion.py', 1, 2, names=['Claude, 22 Oct 2026'], kind='row')],
                note='curated_by is on 109 of 109 v2 rows. The model ID is not recorded.'),
        cx.fact(S, 2, 'model ID and prompt', None, 'not_recorded', looked_in=[HB + 'v2/', V2_DIR, 'outside: no log of this step']),
        cx.fact(S, 3, 'inclusion rule (step-level reason)', 'the source states a need or a decision of its own', 'recorded',
                [cx.lines('completion.py', HB + 'v2/completion.py', 1, 5, kind='row'), cx.lines('build_v2.py', HB + 'v2/build_v2.py', 61, 64, kind='row')]),
        cx.fact(S, 4, 'pdftotext outputs used for the completion', 'kept outside the repository', 'attested_log',
                [cx.oe_link(o) for o in ('OE-18', 'OE-19', 'OE-20', 'OE-21', 'OE-22', 'OE-23')]),
        cx.fact(S, 5, 'the delivered zip', 'hash recorded; zip not stored', 'recorded', [cx.lines('history README', V3 + 'history/README.md', 5, kind='row')]),
        cx.fact(S, 6, 'rejected candidates', '5 audit pass A items marked excluded_by_claude_rule; other rejections not recorded', 'not_recorded',
                [cx.whole('mapping', V3 + 'history/v2-vs-pr45-comparison/claude-v2-vs-pr45-mapping.csv', kind='row')],
                looked_in=[V3 + 'history/v2-vs-pr45-comparison/', V2_DIR, HB + 'v2/completion.py']),
        cx.fact(S, 7, 'v2 preservation in v3', 'all 109 v2 rows present; every field equal, renamed (overlaps_v2, atom_ids) or logged in a before-field',
                'reconstructed (verified)', [cx.lines('v2 hashes', V3 + 'history/README.md', 16, 20, kind='row')] +
                [cx.whole(f'v2 {c}', f'{V2_DIR}{c}/reference-requirements/{f}', kind='row') for c, f in V2_FILES.items()]),
        cx.fact(S, 8, 'owner decisions on the v2 rows', 'your_decision empty on 109 of 109', 'not_recorded',
                [cx.whole('review csv', review, kind='row')], looked_in=[review]),
        cx.entries(S, 'One entry per v2 row. The reason is the row note where there is one (15 rows); otherwise the step-level rule R5-F03 applies.', items),
    ]


def r6a(cx):
    S = 'R6a'
    ledger = list(csv.DictReader(io.StringIO((ROOT / V3 / 'coverage-ledger.csv').read_text(encoding='utf-8'))))
    pa = sorted({r['input_id'] for r in ledger if r['input'] == 'audit pass A'})
    return [
        cx.fact(S, 1, 'actor', 'ChatGPT/Codex (audit pass A)', 'recorded', [cx.ptr('built_from', V3 + 'healthdcat.json', '/built_from/pr45', kind='row')]),
        cx.fact(S, 2, 'model, prompt and inputs', None, 'not_recorded', [cx.lines('inputs read by the build', BUILD, 65, 67)],
                looked_in=[V3, 'outside: the build workspace (the audit inputs are not in it)']),
        cx.fact(S, 3, 'items', {'ids': len(pa), 'mobility_clauses': sum(i.startswith('MA') for i in pa), 'candidates': sum(not i.startswith('MA') for i in pa)},
                'recorded', [cx.whole('coverage ledger', V3 + 'coverage-ledger.csv', kind='row')],
                note='Every audit pass A ID resolves to an atom through the coverage ledger.'),
        cx.fact(S, 4, 'date', '2026-10-22', 'recorded', [cx.lines('audit folder name', BUILD, 38, names=['reference-audit-2026-10-22'])]),
    ]


R9_ROWS_MARK = 'independent check'


def r6b(cx):
    S = 'R6b'
    items = []
    for case in CASES:
        for r in cx.cases[case]['requirements']:
            changed = [k for k in ('statement_before_v3', 'source_locator_before_v3', 'status_in_source_before_v3') if r.get(k)]
            why = r.get('changed_in_v3') or r.get('v3_note')
            if r['added_in'] == 'v3':
                items.append(entry(S, case, r['id'], 'row_added_in_merge', {'atom_ids': r['atom_ids']}, reason=r.get('note'),
                                   reason_status='recorded' if r.get('note') else 'not_recorded', actors=[model_actor('merge')],
                                   date='2026-10-22', date_status='recorded', links=[cx.row_link(case, r['id'], 'row')]))
            elif changed or why:
                if why and R9_ROWS_MARK in why:
                    continue  # applied from the independent check: recorded under R9 (decision 0.2)
                items.append(entry(S, case, r['id'], 'row_changed' if changed else 'row_noted', {'fields': changed},
                                   reason=why, reason_status='recorded' if why else 'not_recorded', actors=[model_actor('merge')],
                                   links=[cx.row_link(case, r['id'], 'row')]))
    return [
        cx.fact(S, 1, 'actor', 'Claude (merge)', 'recorded', [cx.lines('curated_by of the merge rows', BUILD, 121, names=['Claude (Anthropic), 2026-10-22'])]),
        cx.fact(S, 2, 'model ID and prompt', None, 'not_recorded', looked_in=[BUILD, README3, 'outside: no main-session log of 22 Oct']),
        cx.fact(S, 3, 'merge rules', 'case-level merge_rules', 'recorded', [cx.ptr('merge_rules', V3 + 'healthdcat.json', '/merge_rules', kind='row'),
                                                                          cx.lines('README', README3, 61, 69, kind='row')]),
        cx.fact(S, 4, 'decisions: owner and date', 'only the Geo decision is dated (Curator, 2026-10-22)', 'not_recorded',
                [cx.ptr('decisions', V3 + 'geodcat.json', '/decisions', kind='row'), cx.lines('build', BUILD, 379, 382)],
                looked_in=[README3, BUILD, V3 + '*.json decisions'],
                actor_of_geo_decision={'actor': 'human:curator', 'status': 'attested_log', 'evidence': cx.oe_link('OE-25', {'file': BUILD, 'line': 382})}),
        cx.fact(S, 5, 'problem list of the build', 'printed to the console only; the build log of 22 Oct says problems: 0', 'attested_log',
                [cx.lines('console output', BUILD, 437, 439), cx.oe_link('OE-11')]),
        cx.fact(S, 6, 'script that ran', 'the stored build_v3.py postdates the step (imports the 23 Oct adjudication); a pre-adjudication copy exists outside',
                'not_recorded', [cx.lines('import', BUILD, 13, names=['adjudication_2026_10_23']), cx.oe_link('OE-15')],
                looked_in=[HB + 'v3/', 'outside: build workspace'],
                note='Whether the outside copy is exactly the version that ran on 22 Oct is not shown.'),
        cx.entries(S, 'One entry per row the merge added (4) or changed, except changes the row itself attributes to the independent check (under R9).', items),
    ]


def plan_definitions():
    defs = {}
    for rel in PLANS:
        for n, l in enumerate((ROOT / rel).read_text(encoding='utf-8').split('\n'), start=1):
            m = re.match(r"\s*[AM]\(\s*'([^']+)'", l)
            if m and m.group(1) not in defs:
                defs[m.group(1)] = (rel, n)
    return defs


def r7(cx):
    S = 'R7'
    defs = plan_definitions()
    items, generated = [], []
    for case in CASES:
        for a in cx.cases[case]['atoms']:
            if a['provenance'].get('added_in_adjudication') or a.get('split_from'):
                continue  # created by the 23 Oct adjudication (R11c)
            links = [cx.atom_link(case, a['id']), cx.row_link(case, a['parent_id'])]
            if a['id'] in defs:
                rel, n = defs[a['id']]
                links.append(cx.lines('plan-table definition', rel, n, names=[a['id']], kind='row'))
            else:
                generated.append(f'{case}:{a["id"]}')
            items.append(entry(S, case, a['id'], 'split_from_row',
                               {'parent_id': a['parent_id'], 'stratum': a['stratum'], 'status_in_source': a['status_in_source'],
                                'modality': a['modality'], 'relation_to_base': a['relation_to_base']},
                               actors=[{'actor': None, 'status': 'not_recorded'}], links=links))
    return [
        cx.fact(S, 1, 'actor', None, 'not_recorded',
                looked_in=PLANS + [HB + 'v3/plan_derived.py', README3, BUILD, IC, V3 + 'history/README.md', 'outside: no main-session log of 22 Oct'],
                note='No plan table names its author; build_v3.py:121 names Claude only for the 4 rows added in the merge.'),
        cx.fact(S, 2, 'plan tables', 'four files', 'recorded', [cx.whole(Path(p).name, p, kind='row') for p in PLANS + [HB + 'v3/plan_derived.py']]),
        cx.fact(S, 3, 'reasons for splits and strata', None, 'not_recorded', looked_in=PLANS,
                note='Plan-table comments are topic headings (for example "# H-1 identifiers"); they name rows but state no reason, so they are not '
                     'counted as recorded reasons (stricter than spec section 7; the owner signs off this rule). Atom notes are kept as context.'),
        cx.fact(S, 4, 'freeze of the decomposition before system outputs were viewed', None, 'not_recorded',
                [cx.lines('rule', METH, 132, 133, kind='row'), cx.lines('disclosure', README3, 137, kind='row')],
                looked_in=[METH, README3, V3 + 'mock-benchmark/METHOD.md:69-70', V3 + 'history/']),
        cx.fact(S, 5, 'Mobility Table 1 re-check (decision 0.2)', '99 clauses to 98; table1_* fields added; read via WebFetch on 22 Oct', 'recorded',
                [cx.lines('README', README3, 100, 113, kind='row'), cx.lines('plan header', HB + 'v3/plan_mobility_v3.py', 1, 3, kind='row'),
                 cx.oe_link('OE-14')], note='Actor not recorded. Recorded under R7 by decision 0.2.'),
        cx.fact(S, 6, 'atoms generated by code, not defined literally in a plan table', generated, 'recorded',
                [cx.lines('Geo element atoms', HB + 'v3/plan_other.py', 113, 124, kind='row')]),
        cx.fact(S, 7, 'atoms not from R7', 'H-46.5, H-46.6, JRC-10.3: created by the 23 Oct adjudication', 'recorded',
                [cx.atom_link('healthdcat', 'H-46.5'), cx.atom_link('healthdcat', 'H-46.6'), cx.atom_link('jrc-research', 'JRC-10.3')]),
        cx.entries(S, 'One entry per atom R7 made: the atom, its parent row and, where the atom is defined literally, its plan-table line. '
                      'Reasons are not recorded (R7-F03).', items),
    ]


def r8(cx):
    S = 'R8'
    sp = load_json(TRACE + 'backfill/R8-anchor-spans.json')
    s = sp['summary']
    return [
        cx.fact(S, 1, 'anchor check at build time', 'occurrence of the anchor in the build-time text extractions', 'recorded',
                [cx.lines('srcfind', HB + 'v3/srcfind.py', 6, 17), cx.lines('build', BUILD, 184, 189)]),
        cx.fact(S, 2, 'build-time text extractions', 'kept outside the repository', 'attested_log',
                [cx.oe_link(o) for o in ('OE-18', 'OE-19', 'OE-20', 'OE-21', 'OE-22', 'OE-23')]),
        cx.fact(S, 3, 'verbatim anchors re-found', f"{s['verbatim_found']} of {s['verbatim']}; pages equal to the stored anchor_page: {s['page_equal_to_stored']}",
                'reconstructed (verified)', [cx.whole('spans', TRACE + 'backfill/R8-anchor-spans.json', kind='row'),
                                             cx.whole('validator matching', V3 + 'validate_v3.py')],
                note=f"pdftotext: {sp['pdftotext']}. Spans give the text variant and offsets of every part, with the variant's sha256."),
        cx.fact(S, 4, 'Mobility anchors against the stored table1_text (decision 0.4b)',
                f"{s['stored_transcription_found']} of {s['stored_transcription']} found; status stored_transcription, not counted for solidity unless the owner decides so",
                'reconstructed', [cx.whole('spans', TRACE + 'backfill/R8-anchor-spans.json', kind='row')]),
        cx.fact(S, 5, 'JRC web anchors', f"{s['web_unfrozen']} unfrozen: the paper's redistribution rights are not established", 'not_recorded',
                looked_in=[f'{BM}jrc-research/provenance/manifest.json', README3 + ':39,136'], note='Known gap; --release cannot pass for these.'),
        cx.fact(S, 6, 'whether each quote supports its atom', None, 'not_recorded', looked_in=[V3 + 'validate_v3.py', IC, BUILD],
                note='R8 checks occurrence only.'),
    ]


def r9(cx):
    S = 'R9'
    ic = load_json(TRACE + 'index/independent-check.json')
    loc = cx.jsonl_locators('OE-01')
    items = []
    for it in ic['items']:
        targets = [(cx_case(cx, a), a) for a in it['atoms']]
        literal = re.findall(r'\b(?:Req|H|S|G|JRC)-\d+(?:\.(?:\d+|x))?\b', (ROOT / IC).read_text(encoding='utf-8').split('\n')[it['lines'][0] - 1])
        links = [cx.lines('finding', IC, *it['lines'], names=literal or None, kind='check_finding')]
        for case, a in targets:
            links.append(cx.atom_link(case, a, 'named atom'))
        for rid in it['rows']:
            links.append(cx.row_link(cx_row_case(cx, rid), rid, 'named row'))
        items.append(entry(S, 'all', it['index_id'], 'finding_resolved', {'finding_numbers': it['finding_numbers'], 'atoms': it['atoms'],
                                                                       'rows': it['rows'], 'names_no_longer_present': it['unresolved']},
                           reason='resolution column of the finding row', reason_status='recorded',
                           actors=[model_actor('checker', 'attested_log', loc['models'][0])], links=links,
                           date='2026-10-22', date_status='recorded',
                           prompt={'prompt_id': 'P-R9', 'status': 'recorded'}))
    for case in CASES:
        for d in cx.cases[case]['requirements']:
            why = d.get('changed_in_v3') or d.get('v3_note') or ''
            if R9_ROWS_MARK in why:
                items.append(entry(S, case, d['id'], 'row_changed_after_check', {'fields': [k for k in ('statement_before_v3',) if d.get(k)]},
                                   reason=why, reason_status='recorded', actors=[{'actor': None, 'status': 'not_recorded'}],
                                   links=[cx.row_link(case, d['id'], 'row')]))
    return [
        cx.fact(S, 1, 'actor', 'one Claude subagent', 'recorded', [cx.lines('IC', IC, 3, kind='row'), cx.lines('prompt file', V3 + 'history/independent-check/independent-check-prompt.md', 3)]),
        cx.fact(S, 2, 'model ID and Claude Code version', {'model_id': loc['models'][0], 'claude_code': loc['cc_version']}, 'attested_log',
                [cx.oe_link('OE-01', {'jsonl_line': loc['model_line'], 'key': 'message.model'})]),
        cx.fact(S, 3, 'prompt and start', 'P-R9, started 2026-10-22T18:57:25.027Z', 'recorded',
                [cx.whole('prompt index', TRACE + 'index/prompts.json', kind='row'), cx.lines('start', V3 + 'history/independent-check/independent-check-prompt.md', 7, kind='row')]),
        cx.fact(S, 4, 'end time', loc['last'][1], 'attested_log', [cx.oe_link('OE-01', {'jsonl_line': loc['last'][0], 'key': 'timestamp'})]),
        cx.fact(S, 5, 'seed and the 30 sampled IDs', 'seed 20261022 recorded; the sampled IDs are kept outside', 'attested_log',
                [cx.lines('seed', IC, 9, names=['20261022'], kind='row'), cx.oe_link('OE-24'), cx.oe_link('OE-01', {'note': 'the sampling call and its output'})]),
        cx.fact(S, 6, 'raw findings with severities', 'kept outside (the findings file as the checker wrote it); totals in IC:18', 'attested_log',
                [cx.lines('totals', IC, 18, kind='row'), cx.oe_link('OE-01', {'note': 'the Write call of the findings file'})]),
        cx.fact(S, 7, 'the scanned draft (319 atoms)', None, 'not_recorded', [cx.lines('size', IC, 10, names=['319'], kind='row')],
                looked_in=[V3, 'outside: build workspace (overwritten at 19:49:48Z with the 317-atom state)', 'outside: session scratch'],
                note='Per-case counts of the draft (Health 120, Mobility 99, Stat 27, Geo 56, JRC 17) are in the checker log (OE-01).'),
        cx.fact(S, 8, 'drop from 319 to 317 atoms', 'Mobility 99 to 98 (Table 1 re-check); Health: one merge (IC row 19), one move (IC row 41, net 0)', 'recorded',
                [cx.lines('README', README3, 113, kind='row'), cx.lines('merge', IC, 42, names=['H-33.1', 'H-33.2'], kind='check_finding'),
                 cx.lines('move', IC, 62, names=['H-30.3', 'H-69'], kind='check_finding')]),
        cx.fact(S, 9, 'what "verified the high-severity claims" involved', None, 'not_recorded', [cx.lines('claim', IC, 20, kind='row')],
                looked_in=[IC, 'outside: no main-session log of 22 Oct']),
        cx.fact(S, 10, 'applying the resolutions (decision 0.2)', 'resolution column per finding; notes block dated 22 Oct; rows citing the check', 'recorded',
                [cx.lines('notes block', HB + 'v3/plan_health.py', 396, names=['independent check'], kind='row'), cx.oe_link('OE-12'), cx.oe_link('OE-13')],
                note='Actor not recorded. Recorded under R9 by decision 0.2.'),
        cx.fact(S, 11, 'atoms scanned without a finding', 'outcome not recorded (never "passed")', 'not_recorded',
                looked_in=[IC, 'outside: the checker log OE-01 lists the draft']),
        cx.entries(S, 'One entry per finding row of the independent check (IC-01 to IC-45), linking the atoms and rows it names, and one per row the check changed.', items),
    ]


def cx_case(cx, aid):
    return next(c for c in CASES if aid in cx.atom_index[c])


def cx_row_case(cx, rid):
    return next(c for c in CASES if rid in cx.row_index[c])


def r10(cx):
    S = 'R10'
    rd = load_json(TRACE + 'backfill/R10-rederivation.json')
    logs = {o: cx.jsonl_locators(o) for o in ('OE-02', 'OE-03', 'OE-04', 'OE-05', 'OE-06', 'OE-07', 'OE-08', 'OE-09')}
    models = sorted({m for v in logs.values() for m in v['models']})
    return [
        cx.fact(S, 1, 'actors', 'eight Claude subagents, then a script', 'recorded',
                [cx.lines('README', README3, 88, kind='row'), cx.whole('prompt index', TRACE + 'index/prompts.json', kind='row')]),
        cx.fact(S, 2, 'model ID and Claude Code version', {'model_id': models, 'claude_code': sorted({v['cc_version'] for v in logs.values()})},
                'attested_log', [cx.oe_link(o, {'jsonl_line': v['model_line'], 'key': 'message.model'}) for o, v in logs.items()]),
        cx.fact(S, 3, 'start and end times', {o: [v['first'][1], v['last'][1]] for o, v in logs.items()}, 'attested_log',
                [cx.oe_link(o, {'jsonl_lines': [v['first'][0], v['last'][0]], 'key': 'timestamp'}) for o, v in logs.items()],
                note='The prompts record start times (recorded); end times come from the logs.'),
        cx.fact(S, 4, 'packets', '317 atoms (Health 119, JRC 17; the 3 later atoms were created on 23 Oct)', 'recorded',
                [cx.whole(f'packet {c}', f'{V3}history/labelling/packets/atoms-{c}.json', kind='row') for c in CASES]),
        cx.fact(S, 5, 'raw outputs', 'stored; byte-identical to the files the labellers wrote', 'attested_log',
                [cx.whole(f'raw output {n}', f'{V3}history/labelling/raw-outputs/{n}.json', kind='row') for n in sorted(rd['raw_outputs'])],
                note='The scratch copies the labellers wrote are in the outside bundle; their hashes equal these files.'),
        cx.fact(S, 6, 'merge re-run', f"equal to the case files for {rd['summary']['equal']} atoms; equal to the build's merged file", 'reconstructed (verified)',
                [cx.whole('re-derivation', TRACE + 'backfill/R10-rederivation.json', kind='row'), cx.lines('merge rule', HB + 'v3/integrate_labels.py', 39, 78),
                 cx.oe_link('OE-10')]),
        cx.fact(S, 7, 'build-time hash of the merged labels', cx.oe['OE-10']['sha256'], 'attested_log', [cx.oe_link('OE-10')]),
        cx.fact(S, 8, 'labels read from session scratch', 'path recorded in the script (accepted, decision 0.7)', 'recorded',
                [cx.lines('path', HB + 'v3/integrate_labels.py', 6)]),
        cx.fact(S, 9, 'labellers per atom', 'one', 'recorded', [cx.lines('merge rule', HB + 'v3/integrate_labels.py', 56, 63)]),
        cx.fact(S, 10, 'human review of the labels', 'pending on 320 of 320', 'recorded', [cx.whole('coverage', V3 + 'reference-coverage.csv', kind='row')]),
        cx.fact(S, 11, 'atoms whose R10 labels were replaced', 'H-46.1, H-46.3 (relabelled), and the 3 new atoms: R11d', 'recorded',
                [cx.atom_link('healthdcat', a) for a in ('H-46.1', 'H-46.3')]),
        cx.fact(S, 12, 'rationales replaced without a before value', rd['summary']['rationale_replaced_without_before_value'], 'reconstructed',
                [cx.whole('re-derivation', TRACE + 'backfill/R10-rederivation.json', kind='row'), cx.lines('replacement', ADJ, 188, 190)],
                note='R11c replaced the raw rationale of these 3 atoms without keeping the old text; the re-derivation recovers it.'),
    ]


def r11a(cx):
    S = 'R11a'
    return [
        cx.fact(S, 1, 'actor', 'ChatGPT/Codex', 'recorded', [cx.lines('title', CODEX, 1, 5, kind='row')]),
        cx.fact(S, 2, 'model and prompt', None, 'not_recorded', looked_in=[CODEX, ADJ, 'outside: no Codex history in the bundle']),
        cx.fact(S, 3, 'register and findings', '17 register items, 4 findings sections', 'recorded', [cx.whole('index', TRACE + 'index/codex-register.json', kind='row')]),
        cx.fact(S, 4, 'reviewed head', 'placeholder label pre-adjudication-snapshot', 'withheld', [cx.lines('head', CODEX, 3, kind='row')]),
        cx.fact(S, 5, 'date', '2026-10-23', 'recorded', [cx.lines('title', CODEX, 1, kind='row')]),
    ]


def r11b(cx):
    S = 'R11b'
    return [
        cx.fact(S, 1, 'actors (one case-level string)', ['human:curator', 'model:codex/review', 'model:claude/adjudication-applier'], 'recorded',
                [cx.ptr('by', V3 + 'healthdcat.json', '/adjudication/by', kind='row'), cx.lines('script', ADJ, 281)],
                curator_identity={'actor': 'human:curator', 'status': 'attested_log', 'evidence': cx.oe_link('OE-25', {'file': ADJ, 'line': 281})},
                note='The first commit shows that "Curator" in this string replaced the owner\'s name.'),
        cx.fact(S, 2, 'reason per item', 'the register gives a reason per item (CODEX:55-71)', 'recorded', [cx.lines('register', CODEX, 55, 71, kind='row')]),
        cx.fact(S, 3, 'owner of each item: the curator\'s own decision or adopted from Codex', None, 'not_recorded',
                looked_in=[CODEX, ADJ, README3 + ':50-58']),
    ]


def register_link(cx, item_label, aid):
    cxr = load_json(TRACE + 'index/codex-register.json')
    for s in cxr['findings_sections']:
        if item_label.startswith(s['priority']) and aid in s['atoms']:
            return cx.lines(f'Codex finding {s["index_id"]}', CODEX, *s['lines'], names=[aid], kind='adjudication')
    for r in cxr['register']:
        if aid in r['atoms']:
            return cx.lines(f'Codex register {r["index_id"]}', CODEX, *r['lines'], names=[aid], kind='adjudication')
    if aid.startswith('S-'):
        r = next(r for r in cxr['register'] if r['item'].startswith('Deferred Stat'))
        return cx.lines(f'Codex register {r["index_id"]} (range S-19.1 to S-21.1)', CODEX, *r['lines'], kind='adjudication')
    return None


def r11c(cx):
    S = 'R11c'
    adj_lines = (ROOT / ADJ).read_text(encoding='utf-8').split('\n')
    items = []
    for case in CASES:
        for a in cx.cases[case]['atoms']:
            for k, x in enumerate(a.get('adjudication', [])):
                links = [cx.atom_link(case, a['id'])]
                rl = register_link(cx, x['item'], a['id'])
                if rl:
                    links.append(rl)
                n = next((i + 1 for i, l in enumerate(adj_lines) if f"'{a['id']}'" in l), None)
                if n:
                    links.append(cx.lines('script line naming the atom', ADJ, n, names=[a['id']]))
                before = {f: a[f] for f in a if f.endswith('_before_adjudication')}
                for kind in ('raw', 'consolidation'):
                    b = (a.get('input_evidence') or {}).get(kind) or {}
                    if 'label_before_adjudication' in b:
                        before[f'input_evidence.{kind}.label'] = b['label_before_adjudication']
                items.append(entry(S, case, a['id'], 'adjudication_applied', {'item': x['item'], 'change': x['change'], 'before': before},
                                   reason=x['change'], reason_status='recorded', k=k, date=x['date'], date_status='recorded',
                                   actors=[{'actor': 'human:curator', 'status': 'recorded'}, {'actor': 'model:codex/review', 'status': 'recorded'},
                                           model_actor('adjudication-applier')], links=links))
            for k, o in enumerate(a.get('overlap_review', [])):
                items.append(entry(S, case, a['id'], 'overlap_reviewed', {'other': o['atom'], 'relation': o['relation'], 'decision': o.get('decision')},
                                   reason=o.get('rationale'), reason_status='recorded' if o.get('rationale') else 'not_recorded', k=f'ov{k}',
                                   date='2026-10-23', date_status='recorded', actors=[model_actor('adjudication-applier')],
                                   links=[cx.atom_link(case, a['id']), cx.atom_link(case, o['atom'], 'other atom')]))
    return [
        cx.fact(S, 1, 'script', 'adjudication_2026_10_23.py, applied by Claude', 'recorded', [cx.lines('docstring', ADJ, 1, 6, kind='row')]),
        cx.fact(S, 2, 'atoms adjudicated', sum(1 for c in CASES for a in cx.cases[c]['atoms'] if a.get('adjudication')), 'recorded',
                [cx.whole(f'{c}', f'{V3}{c}.json', kind='row') for c in CASES]),
        cx.fact(S, 3, 'atoms created', ['H-46.5', 'H-46.6', 'JRC-10.3'], 'recorded',
                [cx.atom_link('healthdcat', 'H-46.5'), cx.atom_link('healthdcat', 'H-46.6'), cx.atom_link('jrc-research', 'JRC-10.3')]),
        cx.fact(S, 4, 'before values kept', 'statement (4 atoms), status (1 atom), raw label (3 atoms); raw rationale replaced without a before value (3 atoms)',
                'recorded', [cx.lines('label replacement', ADJ, 188, 190)]),
        cx.entries(S, 'One entry per adjudication[] item, linked to its Codex finding or register row and to the script line naming the atom; '
                      'one per overlap_review pair.', items),
    ]


def r11d(cx):
    S = 'R11d'
    ids = [(c, a['id']) for c in CASES for a in cx.cases[c]['atoms'] if FOLLOW_UP in a['input_evidence'].get('labelled_by', '')]
    items = [entry(S, c, a, 'relabelled' if a in ('H-46.1', 'H-46.3') else 'labelled_new_atom', {'blind': False},
                   reason='adjudication follow-up', reason_status='recorded', actors=[model_actor('relabel')], date='2026-10-23',
                   date_status='recorded', links=[cx.atom_link(c, a)]) for c, a in ids]
    return [
        cx.fact(S, 1, 'actor', 'Claude, not blind to the reference', 'recorded', [cx.atom_link(c, a) for c, a in ids[:1]]),
        cx.fact(S, 2, 'model ID and prompt', None, 'not_recorded', looked_in=[ADJ, 'outside: no main-session log of 23 Oct']),
        cx.fact(S, 3, 'labels written by the adjudication script', '5 atoms', 'recorded', [cx.lines('H-46', ADJ, 217), cx.lines('JRC-10.3', ADJ, 252, 254)]),
        cx.entries(S, 'One entry per atom labelled by the follow-up: 2 relabelled packet atoms and 3 new atoms.', items),
    ]


def r12(cx):
    S = 'R12'
    return [
        cx.fact(S, 1, 'validate_v3.py re-run', 'passed; equal to VALIDATION.json and IMPORT-V3-VALIDATION.json', 'reconstructed (verified)',
                [cx.whole('VALIDATION.json', V3 + 'VALIDATION.json', kind='row'), cx.whole('IMPORT-V3-VALIDATION.json', 'IMPORT-V3-VALIDATION.json', kind='row')]),
        cx.fact(S, 2, 'who ran the import', None, 'withheld', looked_in=['git history: author of the first commit', 'IMPORT-VALIDATION.md'],
                note='The import commit is under the owner\'s own account.'),
        cx.fact(S, 3, 'timestamps and tool versions at import', None, 'not_recorded', looked_in=[V3 + 'VALIDATION.json', 'IMPORT-*.json', 'IMPORT-VALIDATION.md']),
        cx.fact(S, 4, 'anonymous export', 'passes on the committed tree', 'reconstructed', [cx.lines('check', 'tools/export_anonymous.py', 60, 67)]),
        cx.fact(S, 5, 'scratch paths missed by the export (decision 0.7)', '9 paths, accepted', 'recorded',
                [cx.lines('integrate_labels', HB + 'v3/integrate_labels.py', 6)] +
                [cx.lines('prompt', V3 + 'history/labelling/labelling-prompts.md', n) for n in (37, 72, 104, 137, 169, 200, 232, 269)]),
        cx.fact(S, 6, '"Curator" for two actors', 'resolvable through the first commit for the strings that replaced the owner\'s name', 'attested_log',
                [cx.lines('Claude as curator', HB + 'v2/completion.py', 1, 2, kind='row'), cx.oe_link('OE-25')]),
    ]


def r13(cx):
    S = 'R13'
    rc = load_json(TRACE + 'backfill/R13-recompute.json')
    return [
        cx.fact(S, 1, 'rule', 'content, not deferred, not merged_into, not umbrella_of', 'recorded',
                [cx.lines('build', BUILD, 78, 88), cx.lines('adjudication', ADJ, 162, 164), cx.lines('validator', V3 + 'validate_v3.py', 145, 147)]),
        cx.fact(S, 2, 'recomputation', f"{rc['summary']['scored']} of {rc['summary']['atoms']} scored; {rc['summary']['differing']} differ", 'reconstructed (verified)',
                [cx.whole('recompute', TRACE + 'backfill/R13-recompute.json', kind='row')]),
        cx.fact(S, 3, 'unsettled atoms in the selection', '50 proposed, open-issue or guidance atoms', 'recorded', [cx.lines('README', README3, 59, kind='row')]),
        cx.fact(S, 4, 'held-out cases', 'inconsistent with the disclosed exposure', 'recorded',
                [cx.lines('methodology', METH, 177, 182, kind='row'), cx.lines('Codex', CODEX, 75, 77, kind='row')]),
    ]


STEPS = [('R0', 'Repo snapshot', r0), ('R1', 'Source publication and acquisition', r1), ('R2', 'Filing by role, allowlist', r2),
         ('R3', 'v1 rows', r3), ('R4', 'v2 coding of the 75 rows', r4), ('R5', 'v2 completion', r5), ('R6a', 'Audit pass A', r6a),
         ('R6b', 'v3 merge', r6b), ('R7', 'Split rows into atoms and code them', r7), ('R8', 'Anchor checks', r8),
         ('R9', 'Independent check', r9), ('R10', 'Input-evidence labels', r10), ('R11a', 'Codex review', r11a),
         ('R11b', 'Provisional adjudication', r11b), ('R11c', 'Apply the adjudication', r11c), ('R11d', 'Non-blind relabel', r11d),
         ('R12', 'Validation, import, anonymisation', r12), ('R13', 'Scored selection', r13)]


# ======================================================================== assembly
from backfill_meta import DECISIONS, GAPS, META  # noqa: E402

ACTORS = {
    'R0': [{'actor': 'human:curator', 'status': 'withheld', 'role': 'import commit'}, {'actor': 'script:tools/export_anonymous.py', 'role': 'sanitised snapshot export (later)'}],
    'R1': [{'actor': 'org:publishers', 'role': 'the publishers named per artifact in the provenance manifests'}, {'actor': 'unresolved:curator-label', 'status': 'not_recorded', 'role': 'acquisition'}],
    'R2': [{'actor': 'unresolved:curator-label', 'status': 'not_recorded', 'role': 'roles and allowlist'}, {'actor': 'human:curator', 'status': 'attested_log', 'role': 'dev split decision of 16 Oct'}],
    'R3': [{'actor': 'unresolved:curator-label', 'status': 'not_recorded'}],
    'R4': [{'actor': 'model:claude/coder', 'model_id': None, 'model_id_status': 'not_recorded'}],
    'R5': [{'actor': 'model:claude/completion', 'model_id': None, 'model_id_status': 'not_recorded'}],
    'R6a': [{'actor': 'model:codex/audit-pass-a', 'model_id': None, 'model_id_status': 'not_recorded'}],
    'R6b': [{'actor': 'model:claude/merge', 'model_id': None, 'model_id_status': 'not_recorded'}],
    'R7': [{'actor': None, 'status': 'not_recorded', 'role': 'decomposer'}],
    'R8': [{'actor': 'script:benchmark-data/reference-sets-v3/history/build-scripts/v3/srcfind.py'}],
    'R9': [{'actor': 'model:claude/checker', 'model_id': 'claude-opus-5-5', 'model_id_status': 'attested_log'}, {'actor': None, 'status': 'not_recorded', 'role': 'verified the high-severity claims and applied the resolutions'}],
    'R10': [{'actor': f'model:claude/labeller-{k}', 'model_id': 'claude-opus-5-5', 'model_id_status': 'attested_log'} for k in range(1, 9)] +
           [{'actor': 'script:benchmark-data/reference-sets-v3/history/build-scripts/v3/integrate_labels.py'}],
    'R11a': [{'actor': 'model:codex/review', 'model_id': None, 'model_id_status': 'not_recorded'}],
    'R11b': [{'actor': 'human:curator', 'status': 'attested_log'}, {'actor': 'model:codex/review', 'model_id': None, 'model_id_status': 'not_recorded'},
             {'actor': 'model:claude/adjudication-applier', 'model_id': None, 'model_id_status': 'not_recorded'}],
    'R11c': [{'actor': 'model:claude/adjudication-applier', 'model_id': None, 'model_id_status': 'not_recorded'}, {'actor': 'script:benchmark-data/reference-sets-v3/history/build-scripts/v3/adjudication_2026_10_23.py'}],
    'R11d': [{'actor': 'model:claude/relabel', 'model_id': None, 'model_id_status': 'not_recorded'}],
    'R12': [{'actor': 'human:curator', 'status': 'withheld', 'role': 'ran the import'}, {'actor': 'script:benchmark-data/reference-sets-v3/validate_v3.py'}, {'actor': 'script:tools/export_anonymous.py'}],
    'R13': [{'actor': 'script:benchmark-data/reference-sets-v3/validate_v3.py', 'role': 'checks the rule'}],
}


def looked_in_of(fact_ids, facts_by_id):
    out = []
    for fid in fact_ids:
        f = facts_by_id[fid]
        links = f.get('links', []) or [l for e in f.get('entries', []) for l in e['links']]
        out += f.get('looked_in') or [l['file'] for l in links if l.get('file')] or [l.get('label') for l in links]
    return list(dict.fromkeys(x for x in out if x))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--written-at', required=True)
    args = ap.parse_args()
    cx = Ctx(args.written_at, os.environ['RT_EVIDENCE_DIR'])
    write_json(TRACE + 'DECISIONS.json', {
        'trace_policy': POLICY, 'date': '2026-11-01', 'actor': 'human:curator', 'status': 'recorded',
        'source': {'label': "the owner's reply in the references session, read against the session's Phase 0 recommendations",
                   'sha256': json.loads(Path(os.environ['RT_SESSION']).read_text())['owner_decisions_sha256'], 'location': 'outside the repository'},
        'decisions': [{'id': i, 'decision': d} for i, d in DECISIONS]})
    gen = {'script': 'tools/trace/backfill.py', 'script_sha256': sha256_file('tools/trace/backfill.py'),
           'meta_sha256': sha256_file('tools/trace/backfill_meta.py'), 'actor': BACKFILL_ACTOR,
           'model_id': json.loads(Path(os.environ['RT_SESSION']).read_text())['model_id'], 'written_at': args.written_at}
    all_facts = {}
    per_step = {}
    for step, name, fn in STEPS:
        facts = fn(cx)
        ids = [f['fact_id'] for f in facts]
        if len(ids) != len(set(ids)):
            raise SystemExit(f'{step}: duplicate fact IDs')
        per_step[step] = facts
        all_facts.update({f['fact_id']: f for f in facts})
        write_json(TRACE + f'backfill/{step}.json', {'trace_policy': POLICY, 'step': step, 'name': name, 'generated_by': gen, 'facts': facts})
    write_json(TRACE + 'backfill/outside-evidence.json', {
        'trace_policy': POLICY, 'decision': '0.9', 'status': 'attested_log', 'signoff': 'pending',
        'note': 'Files kept outside the repository. Only their sha256 is tracked; they contain reference content or private paths.',
        'items': [{k: v for k, v in e.items() if not k.startswith('_')} for e in cx.oe.values()]})
    gaps = []
    for gid, step, text, state, fids, note in GAPS:
        missing = [f for f in fids if f not in all_facts]
        if missing:
            raise SystemExit(f'{gid}: unknown facts {missing}')
        g = {'gap_id': gid, 'step': step, 'gap': text, 'source': 'spec 2.2' if int(gid[2:]) <= 61 else 'found in Phase 0/1',
             'state': state, 'statuses': sorted({all_facts[f]['status'] for f in fids}), 'facts': fids,
             'looked_in': looked_in_of(fids, all_facts)}
        if note:
            g['note'] = note
        if not g['looked_in']:
            raise SystemExit(f'{gid}: no looked_in')
        gaps.append(g)
    write_json(TRACE + 'backfill/gaps.json', {'trace_policy': POLICY, 'gaps': gaps,
                                              'counts': dict(collections.Counter(g['state'] for g in gaps))})
    base = baseline_hashes()
    session = session_block()
    for step, name, _ in STEPS:
        m = META[step]
        facts = per_step[step]
        entries = next((f for f in facts if f['fact_id'].endswith('-E')), None)
        manifest = {
            'trace_policy': POLICY, 'step_id': step, 'name': name, 'time_order': m['time_order'],
            'actors': [dict(a, actor=f"{a['actor']}#{sha256_file(a['actor'][7:])}") if (a.get('actor') or '').startswith('script:') and '#' not in a['actor'] else a
                       for a in ACTORS[step]],
            'session': None, 'session_note': 'historical step: no session record; the backfill session is in written_by',
            'scripts': [{'path': p, 'sha256': sha256_file(p), 'hash_time': 'import' if base.get(p) == sha256_file(p) else 'now',
                         'rerunnable': r, 'postdates_step': pd, **({'reason': why} if why else {})} for p, r, pd, why in m['scripts']],
            'prompts': m.get('prompts', []),
            'inputs': [], 'outputs': [],
            'timing': {'run_started': m['timing'][0], 'run_ended': m['timing'][1], 'timing_status': m['timing'][2], 'run_by': ACTORS[step][0].get('actor')},
            'seeds': m.get('seeds', {}),
            'counts': {'entries': entries['count'] if entries else 0, 'facts': len(facts)},
            'decision_values': m['decision_values'],
            'rationale_location': f'backfill/{step}.json (facts with reason fields); spec section 2',
            'evidence': sorted({f"{l['file']}:{l['locator']['lines'][0]}-{l['locator']['lines'][1]}" for f in facts for l in f.get('links', [])
                                if l.get('locator', {}).get('lines')}),
            'facts': [f['fact_id'] for f in facts],
            'gaps': [g['gap_id'] for g in gaps if g['step'] == re.sub(r'[a-d]$', '', step) or g['step'] == step],
            'written_by': dict(session, actor=BACKFILL_ACTOR),
        }
        for f in facts:
            for l in f.get('links', []):
                if l.get('file') and l['kind'] in ('row', 'source') and l['file'] not in [i['path'] for i in manifest['inputs']]:
                    manifest['inputs'].append({'path': l['file'], 'sha256': l['file_sha256'],
                                               'hash_time': 'import' if base.get(l['file']) == l['file_sha256'] else 'now', 'stored': 'yes'})
        write_json(TRACE + f'steps/{step}.json', finalize_manifest(manifest))
    n_entries = sum(f['count'] for fs in per_step.values() for f in fs if f['fact_id'].endswith('-E'))
    print('facts', sum(len(v) for v in per_step.values()), '| entries', n_entries, '| gaps', len(gaps),
          '| statuses', dict(collections.Counter(f['status'] for fs in per_step.values() for f in fs if not f['fact_id'].endswith('-E'))))


if __name__ == '__main__':
    main()
