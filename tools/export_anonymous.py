#!/usr/bin/env python3
"""Export tracked working-tree files without Git metadata or author history."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
# These two figure images and their metadata were manually inspected.
REVIEWED_PNGS = {'benchmark-data/figures/01-benchmark-evidence-map.png': '00a93a7f3bbfe3cb2918bf3ac2503d8dabfa5c5b4e873f42cad7fc5dd978c843', 'benchmark-data/figures/02-mobility-requirement-examples.png': '601873936e1479c03988182d4c9423effb5bbac6c0ce880ead9052bafb07661b'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='New ZIP path outside this checkout')
    parser.add_argument('--deny-term', action='append', default=[],
                        help='Additional private name, email or account string to reject; repeatable')
    args = parser.parse_args()
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        parser.error('Write the export outside the checkout.')
    if output.exists():
        parser.error('Output already exists; choose a new filename.')
    paths = [Path(p.decode()) for p in subprocess.check_output(
        ['git', 'ls-files', '-z'], cwd=ROOT).split(b'\0') if p]
    payload = {}
    problems = []
    # The configuration below describes patterns, without embedding private identifiers.
    private_path = re.compile(r'(?<![A-Za-z0-9_./:])/(?:Users|home)/[^/\s]+/')
    for path in paths:
        full = ROOT / path
        if full.is_symlink() or not full.is_file() or '.git' in path.parts:
            raise SystemExit('Export refuses missing files, symlinks or Git metadata.')
        data = full.read_bytes()
        payload[path.as_posix()] = data
        if path.suffix.lower() == '.pdf':
            if not shutil.which('pdftotext') or not shutil.which('pdfinfo'):
                raise SystemExit('Install Poppler for PDF text and metadata inspection.')
            text = '\n'.join(subprocess.check_output([command, str(full)] +
                              (['-'] if command == 'pdftotext' else []),
                              stderr=subprocess.DEVNULL).decode('utf-8', errors='replace')
                              for command in ('pdftotext', 'pdfinfo'))
        elif path.as_posix() in REVIEWED_PNGS:
            if hashlib.sha256(data).hexdigest() != REVIEWED_PNGS[path.as_posix()]:
                raise SystemExit('Changed image requires manual inspection: ' + str(path))
            text = ''
        else:
            try:
                text = data.decode('utf-8')
            except UnicodeDecodeError:
                raise SystemExit('Unsupported binary file requires manual inspection: ' + str(path))
        if private_path.search(text):
            problems.append(str(path) + ': local user path')
        if any(term.casefold() in text.casefold() for term in args.deny_term):
            problems.append(str(path) + ': supplied private identifier')
    manifest = json.loads((ROOT / 'IMPORT-PROVENANCE.json').read_text())
    expected = manifest['files_sha256']
    actual = {name: hashlib.sha256(data).hexdigest() for name, data in payload.items()
              if name.startswith('benchmark-data/')}
    if expected != actual:
        problems.append('Snapshot manifest does not match the current benchmark files.')
    if problems:
        raise SystemExit('\n'.join(problems))
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(payload.items()):
            entry = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)
    print('Exported', len(payload), 'files without Git history:', output)


if __name__ == '__main__':
    main()
