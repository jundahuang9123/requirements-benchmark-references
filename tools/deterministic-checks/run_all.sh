#!/usr/bin/env bash
# Runs every part twice (the rerun test), then copies the first run's outputs into the part folders.
# usage: run_all.sh <scratch dir>   (HF_HOME must point at the cache with the pinned models)
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
scratch="${1:?scratch dir}"
export HF_HUB_OFFLINE=1 TRANSFORMERS_VERBOSITY=error TOKENIZERS_PARALLELISM=false
cd "${here}"
python3 -I -B -m pytest -q -p no:cacheprovider tests
./rerun_check.sh part_a.py "${scratch}" --second-model
./rerun_check.sh part_b.py "${scratch}" --second-model
./rerun_check.sh part_c.py "${scratch}"
mkdir -p part-a-atom-fidelity/out part-b-evidence-labels/out part-c-matching/out/main
cp "${scratch}"/part_a-rerun1/* part-a-atom-fidelity/out/
cp "${scratch}"/part_b-rerun1/* part-b-evidence-labels/out/
cp "${scratch}"/part_c-rerun1/* part-c-matching/out/main/
python3 -I make_sheet.py --part-a part-a-atom-fidelity/out --part-b part-b-evidence-labels/out --out review
python3 -I part_c.py --out part-c-matching/out/second --model second --log "${scratch}/part_c-second.log"
echo "ALL DONE"
