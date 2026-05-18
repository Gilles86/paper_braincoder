#!/bin/bash
# Tier 2 benchmark — the main speed/quality matrix.
#   4 datasets × {cpu, gpu (any), a100} × 2 variants × 3 seeds   (=72 jobs)
#   + DN on vanes2019 × a100 × 3 seeds                           (=3 jobs)
# Backend fixed at tensorflow here; the dedicated backend and GPU-type
# axes live in submit_backends.sh and submit_gpus.sh.
#
# Usage: ./submit_tier2.sh [seeds...]    (default seeds: 1 2 3)

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
SEEDS=("$@"); [ ${#SEEDS[@]} -eq 0 ] && SEEDS=(1 2 3)

echo "[tier2] launching with seeds: ${SEEDS[*]}"

n=0
for ds in smallgrid mediumgrid largegrid vanes2019; do
    for hw in cpu gpu a100; do
        for variant in grid hrf; do
            for seed in "${SEEDS[@]}"; do
                "$DIR/submit.sh" "$ds" "$hw" "$variant" default "$seed" tensorflow
                n=$((n+1))
            done
        done
    done
done

# DN on vanes2019 — A100 only.
for seed in "${SEEDS[@]}"; do
    "$DIR/submit.sh" vanes2019 a100 dn default "$seed" tensorflow
    n=$((n+1))
done

echo "[tier2] submitted $n jobs"
