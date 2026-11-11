#!/usr/bin/env bash
# Runs the parts and the rerun tests in order of cost, then copies the outputs into the part folders.
# usage: run_all.sh <scratch dir>   (HF_HOME must point at the cache with the pinned models)
# Order: Part B twice; Part A a second time (compared with <scratch>/part-a-run1); Part C (main model) once on every
# case; Part C twice on the two small cases (full grid) as its rerun test; Part C with the second model.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
scratch="${1:?scratch dir}"
export HF_HUB_OFFLINE=1 TRANSFORMERS_VERBOSITY=error TOKENIZERS_PARALLELISM=false
cd "${here}"
python3 -I -B -m pytest -q -p no:cacheprovider tests
./rerun_check.sh part_b.py "${scratch}" --second-model
mkdir -p part-b-evidence-labels/out && cp "${scratch}"/part_b-rerun1/* part-b-evidence-labels/out/
if [ -d "${scratch}/part-a-run1" ]; then
  python3 -I part_a.py --out "${scratch}/part-a-run2" --second-model --log "${scratch}/part-a-run2.log"
  diff -r "${scratch}/part-a-run1" "${scratch}/part-a-run2" && echo "part_a: the two runs are byte-identical" || echo "part_a: THE TWO RUNS DIFFER"
else
  ./rerun_check.sh part_a.py "${scratch}" --second-model
fi
python3 -I part_c.py --out "${scratch}/part_c-main" --log "${scratch}/part_c-main.log"
mkdir -p part-c-matching/out/main && cp "${scratch}"/part_c-main/* part-c-matching/out/main/
./rerun_check.sh part_c.py "${scratch}" --cases jrc,stat
python3 -I part_c.py --out "${scratch}/part_c-second" --model second --log "${scratch}/part_c-second.log"
mkdir -p part-c-matching/out/second && cp "${scratch}"/part_c-second/* part-c-matching/out/second/
echo "ALL DONE"
