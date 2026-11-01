#!/usr/bin/env python3
"""Gap view for the owner's sign-off of the backfill (spec sections 6 and 7), plus a sign-off template.

    python3 tools/trace/gap_view.py OUT_DIR

Writes OUT_DIR/gap-view.html and OUT_DIR/signoff-template.csv. OUT_DIR must be outside the checkout:
views are never tracked. The page carries the generator's sha256, the sha256 of gaps.json and the date
of the backfill, so regenerating it from the same tree gives the same bytes.
"""
import csv
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, TRACE, load_json, sha256_file  # noqa: E402

STATE_ORDER = ['open', 'partly_resolved', 'resolved', 'corrected']


def esc(x):
    return html.escape('' if x is None else (x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)))


def short_links(f):
    out = []
    for l in f.get('links', []):
        if l['kind'] == 'outside_evidence':
            out.append(f"{l['evidence_id']} (outside)")
        else:
            loc = l['locator']
            where = f":{loc['lines'][0]}-{loc['lines'][1]}" if 'lines' in loc else (loc.get('json_pointer') or ('row ' + loc['csv_key'][1] if 'csv_key' in loc else ''))
            out.append(f"{l['file'].replace('benchmark-data/reference-sets-v3/', 'v3/')}{where}")
    return out


def main(out_dir):
    out = Path(out_dir).resolve()
    if out == ROOT or ROOT in out.parents:
        raise SystemExit('Write views outside the checkout.')
    out.mkdir(parents=True, exist_ok=True)
    gaps = load_json(TRACE + 'backfill/gaps.json')['gaps']
    outside = load_json(TRACE + 'backfill/outside-evidence.json')['items']
    steps = []
    for p in sorted((ROOT / TRACE / 'backfill').glob('R*.json'), key=lambda p: (len(p.stem.split('-')[0]), p.stem)):
        if '-' not in p.stem:
            steps.append(json.loads(p.read_text(encoding='utf-8')))
    order = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6a', 'R6b', 'R7', 'R8', 'R9', 'R10', 'R11a', 'R11b', 'R11c', 'R11d', 'R12', 'R13']
    steps.sort(key=lambda d: order.index(d['step']))
    written_at = steps[0]['facts'][0].get('written_at') or steps[0]['generated_by']['written_at']
    head = (f'generator sha256 {sha256_file("tools/trace/gap_view.py")} · gaps.json sha256 {sha256_file(TRACE + "backfill/gaps.json")} · '
            f'backfill written {written_at}')
    rows = []
    for g in sorted(gaps, key=lambda g: (STATE_ORDER.index(g['state']), g['gap_id'])):
        rows.append(f"<tr class='{g['state']}'><td>{g['gap_id']}</td><td>{g['step']}</td><td>{esc(g['gap'])}</td><td><b>{g['state'].replace('_', ' ')}</b><br>"
                    f"<small>{esc(', '.join(g['statuses']))}</small></td><td>{esc(', '.join(g['facts']))}</td><td><small>{esc('; '.join(g['looked_in'][:6]))}</small></td>"
                    f"<td>{esc(g.get('note'))}</td></tr>")
    sections, sign = [], []
    for d in steps:
        trs = []
        for f in d['facts']:
            if f['fact_id'].endswith('-E'):
                ex = f['entries'][:2]
                trs.append(f"<tr><td>{f['fact_id']}</td><td>per-item entries ({f['count']})</td><td colspan=2>{esc(f['rule'])}<br><small>"
                           f"e.g. {esc(', '.join(e['entry_id'] for e in ex))}</small></td><td>{f['status']}</td><td></td></tr>")
                sign.append((f['fact_id'], d['step'], f"entries ({f['count']})", f['status']))
                continue
            val = f.get('value')
            trs.append(f"<tr class='st-{f['status'].split()[0]}'><td>{f['fact_id']}</td><td>{esc(f['field'])}</td><td>{esc(val)}"
                       f"{'<br><small>' + esc(f.get('note')) + '</small>' if f.get('note') else ''}</td>"
                       f"<td><small>{esc('; '.join(short_links(f)))}{'<br>looked in: ' + esc('; '.join(f['looked_in'])) if f.get('looked_in') else ''}</small></td>"
                       f"<td><b>{f['status']}</b></td><td>{f['actor']}</td></tr>")
            sign.append((f['fact_id'], d['step'], f['field'], f['status']))
        sections.append(f"<h3>{d['step']} · {esc(d['name'])}</h3><table><tr><th>Fact</th><th>Field</th><th>Value</th><th>Pointers</th>"
                        f"<th>Status</th><th>Actor</th></tr>{''.join(trs)}</table>")
    oe = ''.join(f"<tr><td>{e['evidence_id']}</td><td>{esc(e['label'])}</td><td><small>{esc(e.get('sha256') or e.get('reference'))}</small></td>"
                 f"<td>{esc(e.get('mtime_utc'))}</td></tr>" for e in outside)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Backfill gap view</title><style>
:root{{--bg:#f6f7f9;--fg:#15181d;--mut:#5b6472;--rule:#d9dee6;--open:#fff1e6;--part:#fff9db;--ok:#e9f7ef;--cor:#eef2ff}}
@media (prefers-color-scheme:dark){{:root{{--bg:#111318;--fg:#e9ecf1;--mut:#9aa3b2;--rule:#2b313b;--open:#3a2a1d;--part:#36321b;--ok:#1d3326;--cor:#232a45}}}}
body{{background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,sans-serif;margin:0;padding:16px}}main{{max-width:1200px;margin:auto}}
table{{border-collapse:collapse;width:100%;margin:8px 0 24px}}th,td{{border-bottom:1px solid var(--rule);padding:5px 7px;text-align:left;vertical-align:top}}
th{{font-size:12px;color:var(--mut)}}small{{color:var(--mut)}}tr.open{{background:var(--open)}}tr.partly_resolved{{background:var(--part)}}
tr.resolved{{background:var(--ok)}}tr.corrected{{background:var(--cor)}}.meta{{color:var(--mut);font-size:12px;overflow-wrap:anywhere}}
.wrap{{overflow-x:auto}}</style></head><body><main>
<h1>Backfill gap view: Reference trace v1, Phase 1</h1>
<p class="meta">{esc(head)}</p>
<p>For the owner's sign-off. Every fact names its actor (<code>model:claude/backfill</code>), a status from spec 3.2, and pointers a script has
checked (0 problems) or the places where a missing fact was looked for. Sign off by fact ID in <code>signoff-template.csv</code>: put
<code>sign</code>, <code>reject</code> or <code>amend</code> in the decision column, with a note where needed. Facts with status
<code>attested_log</code> rest on the outside evidence below and need your explicit sign-off. R7-F03 states a stricter rule than spec section 7
(plan-table comments are headings, not reasons); signing it accepts that rule.</p>
<h2>Gaps ({len(gaps)})</h2><div class="wrap"><table><tr><th>ID</th><th>Step</th><th>Gap</th><th>State</th><th>Facts</th><th>Looked in</th><th>Note</th></tr>{''.join(rows)}</table></div>
<h2>Facts by step</h2><div class="wrap">{''.join(sections)}</div>
<h2>Outside evidence (decision 0.9)</h2><div class="wrap"><table><tr><th>ID</th><th>What</th><th>sha256</th><th>File time (UTC)</th></tr>{oe}</table></div>
</main></body></html>
"""
    (out / 'gap-view.html').write_text(page, encoding='utf-8')
    with open(out / 'signoff-template.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['fact_id', 'step', 'field', 'status', 'decision', 'note'])
        for row in sign:
            w.writerow(list(row) + ['', ''])
        for e in outside:
            w.writerow([e['evidence_id'], e['step'], 'outside evidence: ' + e['label'], 'attested_log', '', ''])
    print('wrote', out / 'gap-view.html', 'and', out / 'signoff-template.csv', '|', len(sign), 'facts,', len(outside), 'outside items')


if __name__ == '__main__':
    main(sys.argv[1])
