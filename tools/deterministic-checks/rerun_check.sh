#!/usr/bin/env bash
# The rerun test: run a part twice into two folders and compare the outputs byte for byte.
# usage: rerun_check.sh <part_x.py> <scratch dir> [args of the part...]
# The part's --out and --log are given by this script; everything else is passed through.
set -euo pipefail
part="$1"; scratch="$2"; shift 2
name="$(basename "${part%.py}")"
for k in 1 2; do
  d="${scratch:?}/${name}-rerun${k}"
  rm -rf "${d}"
  python3 -I "${part}" --out "${d}" --log "${scratch:?}/${name}-rerun${k}.log" "$@"
done
if diff -r "${scratch:?}/${name}-rerun1" "${scratch:?}/${name}-rerun2" > "${scratch:?}/${name}-rerun.diff"; then
  echo "${name}: the two runs are byte-identical"
  sha256sum "${scratch:?}/${name}-rerun1"/* | sed "s|${scratch}/${name}-rerun1/||"
else
  echo "${name}: THE TWO RUNS DIFFER (see ${scratch}/${name}-rerun.diff)"; exit 1
fi
