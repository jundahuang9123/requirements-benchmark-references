"""Where the inputs are, and the record every output carries (commits, hashes, model revisions).

Everything is read-only. Paths can be changed with environment variables:
  DC_REFS       the references repo checkout (default: the repo that holds this folder, when it has benchmark-data/,
                else ../requirements-benchmark-references next to it)
  DC_RUNSTORE   the run store checkout (default: the repo that holds this folder, else ../reqs_extract_run_store)
  DC_PIPELINE   the pipeline repo checkout (recorded only; default ../profile-requirements-extraction)
  HF_HOME       the Hugging Face cache that holds the pinned models
"""
import hashlib
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKS = os.path.dirname(HERE)                                   # deterministic-checks/


def _repo_root(start):
    d = start
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, '.git')):
            return d
        d = os.path.dirname(d)
    return None


_ROOT = _repo_root(CHECKS)
_SIBLINGS = os.path.dirname(_ROOT) if _ROOT else os.path.dirname(CHECKS)
_IN_REFS = bool(_ROOT) and os.path.isdir(os.path.join(_ROOT, 'benchmark-data', 'reference-sets-v3'))
REFS = os.environ.get('DC_REFS') or (_ROOT if _IN_REFS else os.path.join(_SIBLINGS, 'requirements-benchmark-references'))
RUNSTORE = os.environ.get('DC_RUNSTORE') or (_ROOT if _ROOT and not _IN_REFS else os.path.join(_SIBLINGS, 'reqs_extract_run_store'))
PIPELINE = os.environ.get('DC_PIPELINE') or os.path.join(_SIBLINGS, 'profile-requirements-extraction')
FINAL = os.path.join(RUNSTORE, 'reports', 'benchmark-tools', 'final-scoring')
WORK = os.environ.get('RQ1_FINAL_WORK') or os.path.join(FINAL, 'work')
REF_SETS = os.path.join(REFS, 'benchmark-data', 'reference-sets-v3')

CASES = ['jrc', 'stat', 'geo', 'health', 'mobility']
CASE_FILE = {'jrc': 'jrc-research', 'stat': 'statdcat', 'geo': 'geodcat', 'health': 'healthdcat', 'mobility': 'mobilitydcat'}
CASE_NAME = {'jrc': 'DCAT-AP-JRC', 'stat': 'StatDCAT-AP', 'geo': 'GeoDCAT-AP', 'health': 'HealthDCAT-AP', 'mobility': 'mobilityDCAT-AP'}
REF_PDF = {   # the reference document, for the context window of Part A (relative to benchmark-data/)
    'stat': 'statdcat/reference-requirements/stat-final.pdf',
    'geo': 'geodcat/reference-requirements/geo-final.pdf',
    'health': 'healthdcat/reference-requirements/d6.2-requirements-and-profile.pdf',
}

# Condition names (first author, 10 Nov 2026). Files keep the keys PM and S.
CONDITION_NAMES = {'PM': 'PW', 'PM-D': 'PW−D', 'S': 'AW', 'CB': 'CB', 'OS': 'OS'}

# The NLI models, pinned to a revision hash. The first is the reported one; the second is a sensitivity run only.
NLI_MODELS = {
    'main': ('cross-encoder/nli-deberta-v3-base', '6c749ce3425cd33b46d187e45b92bbf96ee12ec7'),
    'second': ('MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli', 'b3546ea6b0346eb6f8d5d68b13c7dc6d0376b3d7'),
}
EMBED_MODEL = ('sentence-transformers/all-mpnet-base-v2', 'e8c3b32edf5434bc2275fc9bab85f82640a19130')


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def git_head(repo):
    try:
        return subprocess.run(['git', '-C', repo, 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def provenance(inputs):
    """The record every output carries: repo commits and the sha256 of every input file read.
    `inputs` is a list of absolute paths."""
    return {
        'references_commit': git_head(REFS),
        'run_store_commit': git_head(RUNSTORE),
        'pipeline_commit': git_head(PIPELINE),
        'inputs_sha256': {rel(p): sha256_file(p) for p in sorted(set(inputs))},
    }


def rel(path):
    for root, name in ((REFS, 'refs'), (RUNSTORE, 'run-store'), (PIPELINE, 'pipeline')):
        if path.startswith(root + os.sep):
            return name + ':' + os.path.relpath(path, root)
    return path


def jdump(obj, path):
    """Deterministic JSON: sorted keys, fixed indent, newline at the end."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write('\n')


def jload(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)
