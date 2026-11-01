#!/usr/bin/env python3
"""Recount v3/counts.json from the five case files (spec 4.4, 5.2).

    python3 tools/trace/recount.py           # check: counts.json and every case's counts block
    python3 tools/trace/recount.py --write   # rewrite counts.json and the case counts blocks

The count rules are those of the build that wrote counts.json (history/build-scripts/v3/build_v3.py,
counts() and evidence_counts(), as amended by the 23 Oct adjudication), restated here so that the
counts can be recomputed after a review round. Check mode exits non-zero unless counts.json is
reproduced byte for byte and every case's counts block equals its recount.
"""
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CASES, ROOT, V3  # noqa: E402

COUNTS = V3 + 'counts.json'


def _ev(a, kind, ok):
    ie = a.get('input_evidence')
    if not isinstance(ie, dict) or not ie.get(kind):
        return False
    b = ie[kind]
    return b['label'] in ok and b.get('quotes_verified', False)


def evidence_counts(atoms):
    scored = [a for a in atoms if a['scored_by_default']]
    labelled = [a for a in atoms if isinstance(a.get('input_evidence'), dict)]
    out = {'atoms_with_evidence_labels': len(labelled)}
    if not labelled:
        return out
    for kind in ('raw', 'consolidation'):
        if not any(a['input_evidence'].get(kind) for a in labelled):
            continue
        out[f'{kind}_evidence_labels'] = dict(collections.Counter(a['input_evidence'][kind]['label'] for a in labelled if a['input_evidence'].get(kind)))
        out[f'scored_by_default_{kind}_supported'] = sum(1 for a in scored if _ev(a, kind, ('supported',)))
        out[f'scored_by_default_{kind}_supported_or_partial'] = sum(1 for a in scored if _ev(a, kind, ('supported', 'partial')))
    return out


def counts(rows, atoms):
    c = collections.Counter
    content = [a for a in atoms if a['scored_by_default']]
    return {
        'rows': len(rows), 'rows_by_added_in': dict(c(r['added_in'] for r in rows)),
        'atoms': len(atoms), 'atoms_by_stratum': dict(c(a['stratum'] for a in atoms)),
        'atoms_by_status': dict(c(a['status_in_source'] for a in atoms)),
        'atoms_by_relation_to_base': dict(c(a['relation_to_base'] for a in atoms)),
        'atoms_by_found_by': dict(c(a['provenance']['found_by'] for a in atoms)),
        'scored_by_default': len(content),
        'scored_by_default_without_dcat_ap_restatements': sum(1 for a in content if not a['restates_dcat_ap']),
        'scored_by_default_without_rq2_rules': sum(1 for a in content if not a['reuse_or_alignment_rule']),
        'scored_by_default_requirement_status_only': sum(1 for a in content if a['status_in_source'] == 'requirement'),
        'atoms_merged_for_scoring': sum(1 for a in atoms if a.get('merged_into')),
        'umbrella_atoms_not_scored': sum(1 for a in atoms if a.get('umbrella_of')),
        'atoms_provisionally_adjudicated': sum(1 for a in atoms if a.get('adjudication')),
        'atoms_with_source_flags': sum(1 for a in atoms if a['source_flags']),
        **evidence_counts(atoms),
        'atoms_with_overlaps': sum(1 for a in atoms if a['overlaps']),
    }


def recount():
    """counts per case, in the order of counts.json."""
    summary = {}
    for case in CASES:
        d = json.loads((ROOT / f'{V3}{case}.json').read_text(encoding='utf-8'))
        summary[case] = counts(d['requirements'], d['atoms'])
    return summary


def render(summary):
    return json.dumps(summary, indent=1)  # as the build wrote it: indent 1, no trailing newline


def main():
    summary = recount()
    if '--write' in sys.argv:
        (ROOT / COUNTS).write_text(render(summary), encoding='utf-8')
        for case in CASES:
            p = ROOT / f'{V3}{case}.json'
            d = json.loads(p.read_text(encoding='utf-8'))
            if d['counts'] != summary[case]:
                raise SystemExit(f'{case}: the counts block differs from its recount; a review apply must update it')
        print('wrote', COUNTS)
        return
    problems = []
    if (ROOT / COUNTS).read_text(encoding='utf-8') != render(summary):
        problems.append('counts.json is not reproduced byte for byte')
    for case in CASES:
        block = json.loads((ROOT / f'{V3}{case}.json').read_text(encoding='utf-8'))['counts']
        if block != summary[case]:
            problems.append(f'{case}: counts block differs from its recount')
    print('recount:', 'reproduces counts.json and every case counts block' if not problems else problems)
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
