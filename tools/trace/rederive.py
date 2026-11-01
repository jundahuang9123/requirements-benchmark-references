#!/usr/bin/env python3
"""Re-derivations for the backfill (spec section 7): R8 anchors, R10 evidence labels, R13 scored flags.

    python3 tools/trace/rederive.py r8|r10|r13|all [--labels-merged PATH]

Each writes benchmark-data/reference-sets-v3/trace/backfill/<step>-*.json. The outputs hold hashes,
offsets, statuses and atom IDs only, no reference text. They are deterministic for a given tree and
pdftotext version; timing and the session are recorded in the step manifests.

R8 re-runs every verbatim anchor with the validator's own matching (validate_v3.py: norm, texts,
contains) and stores, per ellipsis-separated part, the text variant and offsets where it occurs, with
the sha256 of that variant, so the spans can be checked. It also recomputes the anchor's page.
R8 also resolves the Mobility anchors against the row's stored table1_text (decision 0.4(b),
stored_transcription) and lists the JRC web anchors as gaps.

R10 re-runs the merge rule of history/build-scripts/v3/integrate_labels.py on the stored raw outputs,
with input texts extracted as history/build-scripts/v3/extract_inputs.py did, and compares the result
with the case files (the 5 atoms labelled by the 23 Oct follow-up are left out; the 3 labels the
adjudication changed are compared through label_before_adjudication). With --labels-merged it also
compares with the build's own merged file, kept outside the repository.

R13 recomputes scored_by_default with the rule of validate_v3.py:145-147.
"""
import collections
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CASES, ROOT, TRACE, V3, load_json, sha256_bytes, sha256_file, sha256_json, write_json  # noqa: E402

BF = TRACE + 'backfill/'


def validator():
    spec = importlib.util.spec_from_file_location('validate_v3', ROOT / V3 / 'validate_v3.py')
    mod = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(mod)
    return mod


def pdftotext_version():
    r = subprocess.run(['pdftotext', '-v'], capture_output=True, text=True)
    return (r.stdout or r.stderr).strip().splitlines()[0]


def atom_pointer(case, atoms, aid):
    i = next(k for k, a in enumerate(atoms) if a['id'] == aid)
    return {'file': f'{V3}{case}.json', 'json_pointer': f'/atoms/{i}', 'names': {'id': aid}}


# ---------------------------------------------------------------- R8
VARIANTS = ['-layout', '-layout paged', '-raw', '-raw paged',
            '-layout dehyphenated', '-layout paged dehyphenated', '-raw dehyphenated', '-raw paged dehyphenated']


def r8():
    V = validator()
    out = {'step': 'R8', 'method': 'validate_v3.py norm/texts/contains, pdftotext modes -layout and -raw',
           'pdftotext': pdftotext_version(), 'script_sha256': sha256_file('tools/trace/rederive.py'),
           'validator_sha256': sha256_file(V3 + 'validate_v3.py'), 'variant_names': VARIANTS,
           'variant_sha256': {}, 'verbatim': [], 'stored_transcription': [], 'web_unfrozen': []}
    for case in CASES:
        d = load_json(f'{V3}{case}.json')
        rows = {r['id']: r for r in d['requirements']}
        ref_pdf = V.CASES[case][1]
        variants = None
        if ref_pdf:
            variants = V.texts(ref_pdf, ('-layout', '-raw'))
            out['variant_sha256'][f'benchmark-data/{ref_pdf}'] = [sha256_bytes(t.encode('utf-8')) for t in variants]
            pages_by_mode = {m: [V.norm(p) for p in subprocess.run(['pdftotext', m, str(ROOT / 'benchmark-data' / ref_pdf), '-'],
                                                                     capture_output=True, text=True).stdout.split('\f')]
                             for m in ('-layout', '-raw')}
        for a in d['atoms']:
            ptr = atom_pointer(case, d['atoms'], a['id'])
            if a['anchor_check'] == 'verbatim_in_source_text':
                quote = a['anchor_quote']
                parts = [x.strip(' .') for x in re.split(r'\.\.\.|…|\[\.\.\.\]', quote) if len(x.strip(' .')) >= 12] or [quote]
                spans = []
                for p in parts:
                    q = V.norm(p)
                    hit = None
                    for vi, t in enumerate(variants):
                        for cand in (q, q.replace('- ', '-')):
                            k = t.find(cand)
                            if k >= 0:
                                hit = {'part_sha256': sha256_bytes(cand.encode('utf-8')), 'variant': vi, 'start': k, 'end': k + len(cand)}
                                break
                        if hit:
                            break
                    spans.append(hit)
                q0 = V.norm(parts[0])
                # the page comes from the pdftotext mode in which the first part was found (variants 2, 3, 6, 7 are -raw)
                pages = pages_by_mode['-raw' if spans[0] and spans[0]['variant'] in (2, 3, 6, 7) else '-layout']
                page = next((i + 1 for i, pg in enumerate(pages) if q0 in pg or q0 in pg.replace('- ', '-')), None)
                if page is None:
                    page = next((i + 1 for i in range(len(pages) - 1)
                                 if q0 in pages[i] + ' ' + pages[i + 1] or q0 in (pages[i] + ' ' + pages[i + 1]).replace('- ', '-')), None)
                out['verbatim'].append({'case': case, 'atom_id': a['id'], 'atom': ptr, 'file': f'benchmark-data/{ref_pdf}',
                                        'file_sha256': sha256_file(f'benchmark-data/{ref_pdf}'),
                                        'anchor_sha256': sha256_bytes(quote.encode('utf-8')),
                                        'result': 'found' if all(spans) and V.contains(variants, quote) else 'not_found',
                                        'spans': spans, 'page_recomputed': page, 'page_stored': a.get('anchor_page')})
            elif case == 'mobilitydcat':
                r = rows[a['parent_id']]
                i = next(k for k, x in enumerate(d['requirements']) if x['id'] == r['id'])
                text = r.get('table1_text') or ''
                v = [V.norm(text)]
                v += [x.replace('- ', '-') for x in v]
                out['stored_transcription'].append({'case': case, 'atom_id': a['id'], 'atom': ptr,
                                                    'transcription': {'file': f'{V3}{case}.json', 'json_pointer': f'/requirements/{i}/table1_text',
                                                                      'names_row': r['id'], 'sha256': sha256_json(text)},
                                                    'anchor_sha256': sha256_bytes(a['anchor_quote'].encode('utf-8')),
                                                    'result': 'found' if V.contains(v, a['anchor_quote']) else 'not_found',
                                                    'counts_for_solidity': False})
            else:
                out['web_unfrozen'].append({'case': case, 'atom_id': a['id'], 'atom': ptr, 'anchor_check': a['anchor_check'],
                                            'anchor_sha256': sha256_bytes(a['anchor_quote'].encode('utf-8'))})
    vb = out['verbatim']
    out['summary'] = {
        'verbatim': len(vb), 'verbatim_found': sum(x['result'] == 'found' for x in vb),
        'page_equal_to_stored': sum(x['page_recomputed'] == x['page_stored'] for x in vb),
        'page_differs': [f"{x['case']}:{x['atom_id']}" for x in vb if x['page_recomputed'] != x['page_stored']],
        'stored_transcription': len(out['stored_transcription']),
        'stored_transcription_found': sum(x['result'] == 'found' for x in out['stored_transcription']),
        'web_unfrozen': len(out['web_unfrozen'])}
    write_json(BF + 'R8-anchor-spans.json', out)
    print('R8', out['summary'])


# ---------------------------------------------------------------- R10
RANK = {'supported': 3, 'partial': 2, 'uncertain': 1, 'unsupported': 0}
RAW_DIR = V3 + 'history/labelling/raw-outputs/'
FOLLOW_UP = 'adjudication follow-up'


def extract(rel):
    """Input text exactly as history/build-scripts/v3/extract_inputs.py made it."""
    src = ROOT / 'benchmark-data' / rel
    if rel.endswith('.pdf'):
        txt = subprocess.run(['pdftotext', '-layout', str(src), '-'], capture_output=True, text=True).stdout
        txt = ''.join(f'\n=== [page {i}] ===\n{p}' for i, p in enumerate(txt.split('\f'), start=1) if p.strip())
    elif rel.endswith('.html'):
        import warnings
        from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
        warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)  # extract_inputs.py parsed these the same way
        soup = BeautifulSoup(src.read_text(encoding='utf-8', errors='replace'), 'lxml')
        for t in soup(['script', 'style', 'nav', 'header', 'footer']):
            t.decompose()
        txt = re.sub(r'\n\s*\n+', '\n\n', soup.get_text('\n'))
    elif rel.endswith('.json'):
        txt = json.dumps(json.loads(src.read_text(encoding='utf-8')), indent=1, ensure_ascii=False)
    else:
        txt = src.read_text(encoding='utf-8', errors='replace')
    return txt


def r10(labels_merged=None):
    V = validator()
    allow = load_json('benchmark-data/runtime-inputs.json')['benchmarks']
    texts = {}
    for case, cfg in allow.items():
        for role in ('raw', 'consolidation', 'background'):
            for rel in cfg.get(role, []) or []:
                if rel not in texts:
                    t = V.norm(extract(rel))
                    texts[rel] = (t, t.replace('- ', '-'))

    def quote_ok(path, quote):
        t, t2 = texts.get(path, (None, None))
        if not t or not quote:
            return False
        parts = [p.strip(' .') for p in re.split(r'\.\.\.|…|\[\.\.\.\]', quote) if len(p.strip(' .')) >= 12] or [quote]
        return all(V.norm(p) in t or V.norm(p) in t2 or V.norm(p).replace('- ', '-') in t2 for p in parts)

    def checked(block):
        if not block:
            return None
        srcs = []
        for s in block.get('sources') or []:
            s = dict(s)
            s['quote_check'] = 'verbatim_in_input_text' if quote_ok(s.get('path', ''), s.get('quote', '')) else 'NOT_FOUND'
            srcs.append(s)
        label = block.get('label', 'unsupported')
        return dict(label=label, sources=srcs, rationale=block.get('rationale', ''),
                    quotes_verified=any(s['quote_check'] == 'verbatim_in_input_text' for s in srcs) if srcs else (label == 'unsupported'))

    load = lambda name: json.loads((ROOT / f'{RAW_DIR}{name}.json').read_text(encoding='utf-8'))
    merged = {}
    for name in ('health-a', 'health-b', 'geo', 'stat-jrc', 'mobility-consolidation'):
        for e in load(name):
            m = merged.setdefault(e['atom_id'], {})
            for k in ('raw', 'consolidation'):
                if e.get(k):
                    m[k] = checked(e[k])
    groups = {}
    for name, tag in (('mobility-policy', 'policy and legal texts'), ('mobility-standards', 'standards and specifications'),
                      ('mobility-literature', 'literature and projects')):
        for e in load(name):
            groups.setdefault(e['atom_id'], []).append((tag, checked(e['raw'])))
    for aid, gs in groups.items():
        best = max(gs, key=lambda g: RANK[g[1]['label']])[1]['label']
        srcs, rats = [], []
        for tag, b in gs:
            if RANK[b['label']] >= 1:
                srcs += b['sources']
            rats.append(f"{tag}: {b['label']}" + (f" ({b['rationale']})" if b['rationale'] and RANK[b['label']] >= 1 else ''))
        merged.setdefault(aid, {})['raw'] = dict(label=best, sources=srcs, rationale='; '.join(rats),
                                                 quotes_verified=any(s['quote_check'] == 'verbatim_in_input_text' for s in srcs) if srcs else best == 'unsupported',
                                                 by_input_group={tag: b['label'] for tag, b in gs})
    out = {'step': 'R10', 'method': 'merge rule of history/build-scripts/v3/integrate_labels.py:39-78 on the stored raw outputs; '
                                   'input texts as history/build-scripts/v3/extract_inputs.py',
           'pdftotext': pdftotext_version(), 'script_sha256': sha256_file('tools/trace/rederive.py'),
           'raw_outputs': {n: sha256_file(f'{RAW_DIR}{n}.json') for n in sorted(p.stem for p in (ROOT / RAW_DIR).glob('*.json'))},
           'merged_sha256': sha256_json(merged), 'atoms': []}
    if labels_merged:
        build = json.loads(Path(labels_merged).read_text(encoding='utf-8'))
        out['build_labels_merged'] = {'sha256': sha256_bytes(Path(labels_merged).read_bytes()), 'location': 'outside the repository',
                                      'equal_to_rederivation': build == merged,
                                      'atoms_differing': sorted(a for a in set(build) | set(merged) if build.get(a) != merged.get(a))}
    stats = collections.Counter()
    for case in CASES:
        d = load_json(f'{V3}{case}.json')
        consolidation_case = case in ('healthdcat', 'mobilitydcat')
        for a in d['atoms']:
            ie = a['input_evidence']
            rec = {'case': case, 'atom_id': a['id'], 'atom': atom_pointer(case, d['atoms'], a['id'])}
            if FOLLOW_UP in ie.get('labelled_by', ''):
                rec['result'] = 'r11d_follow_up' if a['id'] in merged else 'r11d_follow_up_not_in_packets'
                stats[rec['result']] += 1
                out['atoms'].append(rec)
                continue
            m = merged.get(a['id'])
            if m is None:
                rec['result'] = 'row_not_found'
                stats['row_not_found'] += 1
                out['atoms'].append(rec)
                continue
            diffs = []
            for kind in ('raw', 'consolidation'):
                mine = m.get(kind) if (kind == 'raw' or consolidation_case) else None
                theirs = ie.get(kind)
                if theirs and 'label_before_adjudication' in theirs:
                    theirs = dict(theirs, label=theirs['label_before_adjudication'])
                    theirs.pop('label_before_adjudication')
                    rec.setdefault('compared_with_before_adjudication', []).append(kind)
                    if mine and theirs.get('rationale') != mine.get('rationale'):
                        rec.setdefault('replaced_without_before_value', []).append(f'{kind}.rationale')
                        theirs = dict(theirs, rationale=mine.get('rationale'))
                if mine != theirs:
                    diffs.append(kind if not (mine and theirs) else
                                 f"{kind}: " + ', '.join(sorted(k for k in set(mine) | set(theirs) if mine.get(k) != theirs.get(k))))
                rec[f'{kind}_sha256'] = sha256_json(mine) if mine else None
            rec['result'] = 'equal' if not diffs else 'differs'
            if diffs:
                rec['differences'] = diffs
            stats[rec['result']] += 1
            out['atoms'].append(rec)
    out['summary'] = dict(stats, atoms_in_raw_outputs=len(merged),
                          rationale_replaced_without_before_value=[f"{x['case']}:{x['atom_id']}" for x in out['atoms'] if x.get('replaced_without_before_value')])
    write_json(BF + 'R10-rederivation.json', out)
    print('R10', out['summary'], {k: v for k, v in out.get('build_labels_merged', {}).items() if k != 'atoms_differing'})


# ---------------------------------------------------------------- R13
def r13():
    out = {'step': 'R13', 'rule': 'stratum = content, status_in_source != deferred, not merged_into, not umbrella_of (validate_v3.py:145-147)',
           'script_sha256': sha256_file('tools/trace/rederive.py'), 'cases': {}}
    for case in CASES:
        d = load_json(f'{V3}{case}.json')
        rec = [a['stratum'] == 'content' and a['status_in_source'] != 'deferred' and not a.get('merged_into') and not a.get('umbrella_of')
               for a in d['atoms']]
        stored = [a['scored_by_default'] for a in d['atoms']]
        out['cases'][case] = {'atoms': len(stored), 'scored_stored': sum(stored), 'scored_recomputed': sum(rec),
                              'differing': [a['id'] for a, x, y in zip(d['atoms'], rec, stored) if x != y]}
    out['summary'] = {'atoms': sum(c['atoms'] for c in out['cases'].values()),
                      'scored': sum(c['scored_recomputed'] for c in out['cases'].values()),
                      'differing': sum(len(c['differing']) for c in out['cases'].values())}
    write_json(BF + 'R13-recompute.json', out)
    print('R13', out['summary'])


if __name__ == '__main__':
    which = sys.argv[1]
    lm = sys.argv[sys.argv.index('--labels-merged') + 1] if '--labels-merged' in sys.argv else None
    if which in ('r13', 'all'):
        r13()
    if which in ('r8', 'all'):
        r8()
    if which in ('r10', 'all'):
        r10(lm)
