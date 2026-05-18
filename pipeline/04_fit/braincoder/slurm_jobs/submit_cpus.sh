#!/bin/bash
# CPU thread-count sweep — how does braincoder's CPU runtime scale with
# core count?
#   {largegrid, vanes2019} × {cpu8, cpu16, cpu32} × {grid, hrf}
#       × tensorflow × 3 seeds
#   = 36 jobs
#
# Smaller datasets (smallgrid/mediumgrid) finish in seconds, so the
# 8/16/32 difference is dominated by startup overhead — only the large
# datasets are informative for this axis.
#
# Usage: ./submit_cpus.sh [seeds...]   (default: 1 2 3)

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
SEEDS=("$@"); [ ${#SEEDS[@]} -eq 0 ] && SEEDS=(1 2 3)

n=0
for ds in largegrid vanes2019; do
    for hw in cpu8 cpu16 cpu32; do
        for variant in grid hrf; do
            for seed in "${SEEDS[@]}"; do
                "$DIR/submit.sh" "$ds" "$hw" "$variant" default "$seed" tensorflow
                n=$((n+1))
            done
        done
    done
done

echo "[cpus] submitted $n jobs"
