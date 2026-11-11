"""The reference atoms and the passage each one paraphrases (read-only).

Context of an atom (Part A):
  Stat, Geo, Health: the anchor quotation located in the text of the reference PDF (pdftotext, raw order), with a
                     window of W characters on each side (W = 700 by default);
  Mobility:          the stored `table1_text` of the atom's parent row (a transcription made during curation);
  JRC:               the anchor quotation alone (the paper is not in the repo).
The anchor is located exactly in the normalised text, or else loosely (every non-alphanumeric character removed on
both sides); when it is not found at all the context is the anchor alone, and the record says so.
"""
import bisect
import os
import re
import subprocess

from . import paths
from .textrules import normalise, squash


def load_case(case):
    path = os.path.join(paths.REF_SETS, paths.CASE_FILE[case] + '.json')
    return paths.jload(path), path


def raw_label(atom):
    hr = atom.get('input_evidence', {}).get('human_review')
    return hr.get('raw_label') if isinstance(hr, dict) else None


def denominators(atoms):
    """N: scored atoms the raw inputs state at least in part; X: stated in full (decision of 9 Nov 2026)."""
    scored = [a for a in atoms if a.get('scored_by_default')]
    n = [a['id'] for a in scored if raw_label(a) in ('supported', 'partial')]
    x = [a['id'] for a in scored if raw_label(a) == 'supported']
    return {'scored': [a['id'] for a in scored], 'N': n, 'X': x}


_pdf_cache = {}


def pdf_text(case):
    """The reference PDF's text (pdftotext, raw order), normalised; cached per process."""
    if case not in _pdf_cache:
        path = os.path.join(paths.REFS, 'benchmark-data', paths.REF_PDF[case])
        out = subprocess.run(['pdftotext', path, '-'], capture_output=True, text=True, check=True).stdout
        _pdf_cache[case] = (normalise(out), path)
    return _pdf_cache[case]


class Squashed:
    """A text with every non-alphanumeric character removed, and the map back to positions in the original."""
    def __init__(self, text):
        self.text = text
        chars, pos = [], []
        low = text.lower()
        for i, ch in enumerate(low):
            if ch.isalnum():
                chars.append(ch)
                pos.append(i)
        self.sq = ''.join(chars)
        self.pos = pos

    def find(self, needle):
        q = squash(needle)
        if not q:
            return None
        i = self.sq.find(q)
        if i < 0:
            return None
        return self.pos[i], self.pos[i + len(q) - 1] + 1


_sq_cache = {}


def locate(text, anchor, key=None):
    """(start, end, how) of the anchor in the text, or (None, None, 'not_found')."""
    a = normalise(anchor)
    i = text.find(a)
    if i >= 0:
        return i, i + len(a), 'exact'
    sq = _sq_cache.get(key) if key else None
    if sq is None:
        sq = Squashed(text)
        if key:
            _sq_cache[key] = sq
    span = sq.find(a)
    if span:
        return span[0], span[1], 'loose'
    return None, None, 'not_found'


def context(case, atom, window=700, reqs=None):
    """The context of an atom, with a record of how it was made."""
    anchor = normalise(atom.get('anchor_quote') or '')
    if case == 'jrc':
        return {'context': anchor, 'source': 'anchor only (paper not in the repo)', 'located': 'n/a', 'window': None}
    if case == 'mobility':
        row = (reqs or {}).get(atom.get('parent_id'))
        t1 = normalise(row.get('table1_text') if row else '')
        if t1 and anchor and locate(t1, anchor)[2] != 'not_found':
            return {'context': t1, 'source': 'table1_text of the parent row (curation transcription)', 'located': locate(t1, anchor)[2], 'window': None}
        return {'context': anchor, 'source': 'anchor only (table1_text missing or without the anchor)', 'located': 'not_found', 'window': None}
    text, path = pdf_text(case)
    s, e, how = locate(text, anchor, key=case)
    if how == 'not_found':
        return {'context': anchor, 'source': 'anchor only (not found in the PDF text)', 'located': how, 'window': window}
    lo, hi = max(0, s - window), min(len(text), e + window)
    return {'context': text[lo:hi], 'source': f'PDF window ({os.path.basename(path)})', 'located': how, 'window': window,
            'span': [s, e], 'page_stored': atom.get('anchor_page')}


def all_atoms():
    """Every atom of every case, with its case key, and the input files read."""
    out, files = [], []
    for case in paths.CASES:
        d, path = load_case(case)
        files.append(path)
        reqs = {r['id']: r for r in d.get('requirements', [])}
        for a in d['atoms']:
            out.append((case, a, reqs))
    return out, files
