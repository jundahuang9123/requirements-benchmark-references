"""Shared helpers for the reference trace (ref-trace-v1): hashing, canonical JSON, locators, manifests.

Everything here is deterministic and reads only files inside the repository, except the session
record and the transcript, whose paths come from the environment and stay outside the repository.
"""
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BM = 'benchmark-data/'
V3 = BM + 'reference-sets-v3/'
TRACE = V3 + 'trace/'
CASES = ['mobilitydcat', 'healthdcat', 'statdcat', 'geodcat', 'jrc-research']
POLICY = 'ref-trace-v1'
BASELINE_TAG = 'ref-trace-baseline'

# Record status values (spec 3.2) and whether each counts for solidity (None: not applicable).
STATUSES = {'recorded': True, 'reconstructed': True, 'reconstructed (verified)': True, 'attested_log': True,
            'attested_memory': False, 'withheld': False, 'not_recorded': False, 'not_applicable': None,
            'row_not_found': False}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(rel):
    return sha256_bytes((ROOT / rel).read_bytes())


def canonical(obj):
    """Canonical JSON: sort_keys, no ASCII escaping, compact separators, UTF-8."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def sha256_json(obj):
    return sha256_bytes(canonical(obj))


def now_utc():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def load_json(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=True).stdout


def baseline_hashes():
    """files_sha256 as committed at the baseline tag (hash_time 'import')."""
    return json.loads(git('show', f'{BASELINE_TAG}:IMPORT-PROVENANCE.json'))['files_sha256']


# ---------------------------------------------------------------- locators (spec 3.6)
def json_pointer_get(doc, pointer):
    """Resolve an RFC 6901 JSON pointer."""
    if pointer == '':
        return doc
    if not pointer.startswith('/'):
        raise ValueError(f'bad pointer {pointer!r}')
    cur = doc
    for part in pointer[1:].split('/'):
        part = part.replace('~1', '/').replace('~0', '~')
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    return cur


def pointer_escape(key):
    return str(key).replace('~', '~0').replace('/', '~1')


_baseline_files = None


def at_baseline(rel):
    """True if the file exists in the tree of the baseline tag."""
    global _baseline_files
    if _baseline_files is None:
        _baseline_files = set(git('ls-tree', '-r', '--name-only', BASELINE_TAG).decode().split('\n'))
    return rel in _baseline_files


def file_bytes(rel, ref=None):
    """The file's bytes in the working tree, or at a git tag (never a commit ID) when ref is given."""
    if ref:
        return git('show', f'{ref}:{rel}')
    return (ROOT / rel).read_bytes()


def text_lines(rel, start, end, ref=None):
    """Bytes of lines start..end (1-based, inclusive), each with its own line ending."""
    lines = file_bytes(rel, ref).splitlines(keepends=True)
    if not 1 <= start <= end <= len(lines):
        raise ValueError(f'{rel}: lines {start}-{end} out of range (1-{len(lines)})')
    return b''.join(lines[start - 1:end])


def csv_row(rel, column, value, ref=None):
    """The single CSV row whose column equals value, as a dict; raises unless exactly one."""
    rows = [r for r in csv.DictReader(io.StringIO(file_bytes(rel, ref).decode('utf-8'))) if r.get(column) == value]
    if len(rows) != 1:
        raise ValueError(f'{rel}: {len(rows)} rows with {column}={value!r}')
    return rows[0]


def link(label, kind, rel, ref='auto', **locator):
    """A link {label, kind, file, git_ref, hash_time, file_sha256, locator, target_sha256}.

    History links resolve at the baseline tag when the file existed there (hash_time "import"), so later
    steps that change a file do not break them; files created after the baseline resolve in the working
    tree (hash_time "now")."""
    if ref == 'auto':
        ref = BASELINE_TAG if at_baseline(rel) else None
    out = {'label': label, 'kind': kind, 'file': rel}
    if ref:
        out['git_ref'] = ref
    out.update({'hash_time': 'import' if ref == BASELINE_TAG else 'now', 'file_sha256': sha256_bytes(file_bytes(rel, ref)), 'locator': locator})
    out['target_sha256'] = target_sha256(rel, locator, ref)
    return out


def target_sha256(rel, locator, ref=None):
    if 'json_pointer' in locator:
        target = json_pointer_get(json.loads(file_bytes(rel, ref)), locator['json_pointer'])
        for k, v in (locator.get('names') or {}).items():
            if not isinstance(target, dict) or target.get(k) != v:
                raise ValueError(f'{rel}{locator["json_pointer"]}: does not name {k}={v!r}')
        return sha256_json(target)
    if 'lines' in locator:
        data = text_lines(rel, *locator['lines'], ref=ref)
        for needle in locator.get('names') or []:
            if needle.encode('utf-8') not in data:
                raise ValueError(f'{rel}:{locator["lines"]}: does not name {needle!r}')
        return sha256_bytes(data)
    if 'csv_key' in locator:
        col, val = locator['csv_key']
        return sha256_json(csv_row(rel, col, val, ref))
    if locator.get('whole_file'):
        return sha256_bytes(file_bytes(rel, ref))
    raise ValueError(f'unknown locator {locator}')


# ---------------------------------------------------------------- session and manifests (spec 3.7)
def tool_versions():
    def first_line(cmd):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
            return (r.stdout or r.stderr).strip().splitlines()[0]
        except (OSError, IndexError):
            return 'not available'
    return {'python': sys.version.split()[0], 'git': first_line(['git', '--version']),
            'pdftotext': first_line(['pdftotext', '-v']), 'claude_code': first_line(['claude', '--version'])}


def session_block(extra=None):
    """Who wrote a manifest: model ID, Claude Code version, tool versions, the hashes of the hand-off prompt,
    the spec and the owner's decisions, and the sha256 of the session transcript at writing time.
    The session record (RT_SESSION) and the transcript (RT_TRANSCRIPT) stay outside the repository;
    a copy of the transcript is kept outside too (RT_TRANSCRIPT_COPIES) so that its hash stays checkable."""
    rec = json.loads(Path(os.environ['RT_SESSION']).read_text(encoding='utf-8'))
    block = {k: rec[k] for k in ('model_id', 'model_id_status', 'claude_code_version', 'handoff_prompt_sha256',
                                 'spec_working_copy_sha256', 'cleaned_spec_sha256', 'owner_decisions_sha256')}
    block['tool_versions'] = tool_versions()
    transcript = os.environ.get('RT_TRANSCRIPT')
    if transcript and Path(transcript).exists():
        data = Path(transcript).read_bytes()
        digest = sha256_bytes(data)
        copies = Path(os.environ['RT_TRANSCRIPT_COPIES'])
        copies.mkdir(parents=True, exist_ok=True)
        (copies / f'{digest}.jsonl').write_bytes(data)
        block['transcript_sha256'] = digest
        block['transcript_location'] = 'outside the repository'
    else:
        block['transcript_sha256'] = None
        block['transcript_status'] = 'not_recorded'
    block['written_at'] = now_utc()
    block.update(extra or {})
    return block


def finalize_manifest(manifest):
    """Add manifest_sha256: the sha256 of the canonical manifest without that field."""
    body = {k: v for k, v in manifest.items() if k != 'manifest_sha256'}
    manifest = dict(body, manifest_sha256=sha256_json(body))
    return manifest


def write_json(rel, obj):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


def file_entry(rel, hash_time='step', **extra):
    return dict({'path': rel, 'sha256': sha256_file(rel), 'hash_time': hash_time, 'stored': 'yes'}, **extra)


def private_path_hits(text):
    """The export's own private-path pattern (tools/export_anonymous.py)."""
    return re.findall(r'(?<![A-Za-z0-9_./:])/(?:Users|home)/[^/\s]+/', text)
