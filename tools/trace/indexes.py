#!/usr/bin/env python3
"""Sidecar indexes of historical files that are not edited (spec 3.1): the independent-check findings,
the Codex review's findings and register, and the subagent prompts.

    python3 tools/trace/indexes.py

Writes benchmark-data/reference-sets-v3/trace/index/{independent-check,codex-register,prompts}.json.
Each item points to a line range, with the sha256 of those lines and the IDs the lines name, so a
script can check that the item still says what the index claims. No finding text is copied.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CASES, ROOT, TRACE, V3, load_json, sha256_bytes, sha256_file, text_lines, write_json  # noqa: E402

IC = V3 + 'INDEPENDENT-CHECK.md'
CODEX = V3 + 'CODEX-REVIEW-2026-10-23.md'
IC_PROMPT = V3 + 'history/independent-check/independent-check-prompt.md'
LB_PROMPTS = V3 + 'history/labelling/labelling-prompts.md'
ID = re.compile(r'\b(?:Req|H|S|G|JRC)-\d+(?:\.(?:\d+|x))?\b')


def known_ids():
    atoms, rows = {}, {}
    for case in CASES:
        d = load_json(f'{V3}{case}.json')
        for a in d['atoms']:
            atoms[a['id']] = case
        for r in d['requirements']:
            rows[r['id']] = case
    return atoms, rows


def names_in(cell):
    """IDs named in a table cell, with 'Req-23.1/23.2' expanded to Req-23.2 and 'H-11.x' kept as a row wildcard."""
    out = []
    for m in ID.finditer(cell):
        out.append(m.group(0))
        prefix = m.group(0).split('-')[0]
        tail = cell[m.end():]
        for sm in re.finditer(r'^/(\d+\.\d+)', tail):
            out.append(f'{prefix}-{sm.group(1)}')
    return list(dict.fromkeys(out))


def resolve(names, atoms, rows):
    res = {'atoms': [], 'rows': [], 'unresolved': []}
    for n in names:
        if n in atoms:
            res['atoms'].append(n)
        elif n.endswith('.x') and n[:-2] in rows:
            res['rows'].append(n[:-2])
        elif n in rows:
            res['rows'].append(n)
        else:
            res['unresolved'].append(n)
    return res


def table_rows(rel, first, last):
    lines = (ROOT / rel).read_text(encoding='utf-8').split('\n')
    for n in range(first, last + 1):
        line = lines[n - 1]
        if line.startswith('| ') and not line.startswith('|---'):
            yield n, [c.strip() for c in line.strip().strip('|').split('|')]


def independent_check(atoms, rows):
    items = []
    for k, (n, cells) in enumerate(table_rows(IC, 24, 68), start=1):
        names = names_in(cells[1])
        items.append({'index_id': f'IC-{k:02d}', 'finding_numbers': cells[0], 'lines': [n, n],
                      'lines_sha256': sha256_bytes(text_lines(IC, n, n)), 'names': names, **resolve(names, atoms, rows)})
    decision = {'index_id': 'IC-D1', 'kind': 'framing decision', 'lines': [70, 74],
                'lines_sha256': sha256_bytes(text_lines(IC, 70, 74)), 'names': names_in(text_lines(IC, 70, 74).decode())}
    decision.update(resolve(decision['names'], atoms, rows))
    return {'file': IC, 'file_sha256': sha256_file(IC), 'table_lines': [24, 68], 'rows': len(items),
            'findings_numbered': '1-47 (rows 21-22 and 34-35 are combined)', 'severity_totals_line': 18,
            'scope_lines': [3, 11], 'items': items, 'decisions': [decision]}


def codex_register(atoms, rows):
    lines = (ROOT / CODEX).read_text(encoding='utf-8').split('\n')
    sections = []
    heads = [(i + 1, l) for i, l in enumerate(lines) if l.startswith('### P')]
    for k, (n, head) in enumerate(heads, start=1):
        end = (heads[k][0] - 1) if k < len(heads) else next(i for i in range(n, len(lines)) if lines[i].startswith('## '))
        end = end if k < len(heads) else end  # the next level-2 heading ends the last section
        while not lines[end - 1].strip():
            end -= 1
        body = text_lines(CODEX, n, end).decode()
        names = names_in(body)
        sections.append({'index_id': f'CX-{k}', 'priority': head.split()[1], 'lines': [n, end],
                         'lines_sha256': sha256_bytes(text_lines(CODEX, n, end)), 'names': names, **resolve(names, atoms, rows)})
    items = []
    for k, (n, cells) in enumerate(table_rows(CODEX, 55, 71), start=1):
        names = names_in(cells[0])
        items.append({'index_id': f'CR-{k:02d}', 'item': cells[0], 'decision': cells[1], 'lines': [n, n],
                      'lines_sha256': sha256_bytes(text_lines(CODEX, n, n)), 'names': names, **resolve(names, atoms, rows)})
    return {'file': CODEX, 'file_sha256': sha256_file(CODEX), 'reviewed_head_line': 3, 'register_lines': [51, 71],
            'findings_sections': sections, 'register': items}


def prompt_blocks(rel):
    lines = (ROOT / rel).read_text(encoding='utf-8').split('\n')
    out, title, started = [], None, None
    i = 0
    while i < len(lines):
        l = lines[i]
        if l.startswith('## ') and (rel == LB_PROMPTS or l.startswith('## Independent check')):
            title = l[3:].strip()
        m = re.match(r'Started (\S+) \(UTC\)', l)
        if m:
            started = m.group(1)
        if l.strip() == '```text':
            j = next(k for k in range(i + 1, len(lines)) if lines[k].strip() == '```')
            out.append({'title': title, 'started_at': started, 'lines': [i + 2, j],
                        'lines_sha256': sha256_bytes(text_lines(rel, i + 2, j))})
            i = j
        i += 1
    return out


def prompts():
    items = []
    for b in prompt_blocks(IC_PROMPT):
        items.append(dict(b, prompt_id='P-R9', step='R9', file=IC_PROMPT))
    for k, b in enumerate(prompt_blocks(LB_PROMPTS), start=1):
        items.append(dict(b, prompt_id=f'P-R10-{k}', step='R10', file=LB_PROMPTS))
    return {'note': 'Prompt texts as stored: verbatim except the sanitising substitutions of the second commit '
                    '(container paths to workspace/, the upstream pull-request label to "audit pass A").',
            'files': {IC_PROMPT: sha256_file(IC_PROMPT), LB_PROMPTS: sha256_file(LB_PROMPTS)}, 'items': items}


def main():
    atoms, rows = known_ids()
    write_json(TRACE + 'index/independent-check.json', independent_check(atoms, rows))
    write_json(TRACE + 'index/codex-register.json', codex_register(atoms, rows))
    write_json(TRACE + 'index/prompts.json', prompts())
    ic = json.loads((ROOT / TRACE / 'index/independent-check.json').read_text())
    cx = json.loads((ROOT / TRACE / 'index/codex-register.json').read_text())
    pr = json.loads((ROOT / TRACE / 'index/prompts.json').read_text())
    print('IC rows', ic['rows'], '| unresolved names', sorted({u for x in ic['items'] for u in x['unresolved']}))
    print('Codex sections', len(cx['findings_sections']), 'register', len(cx['register']), '| unresolved', sorted({u for x in cx['register'] for u in x['unresolved']}))
    print('prompts', [(p['prompt_id'], p['started_at'], p['lines']) for p in pr['items']])


if __name__ == '__main__':
    main()
