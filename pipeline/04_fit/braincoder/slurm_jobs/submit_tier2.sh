#!/bin/bash
# Tier 2 benchmark: 4 datasets × 3 hardware × 2 variants × 3 seeds  (=72 jobs)
# plus DN on vanes2019 × 3 seeds (=3 jobs).
#
# Skip combos: DN on synthetic grids (no DN ground truth there).
#
# Usage: ./submit_tier2.sh [seeds...]    (default seeds: 1 2 3)

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
SEEDS=("${@:-1 2 3}")

echo "[tier2] launching with seeds: ${SEEDS[*]}"

n=0
for ds in smallgrid mediumgrid largegrid vanes2019; do
    for hw in cpu gpu a100; do
        for variant in grid hrf; do
            for seed in "${SEEDS[@]}"; do
                "$DIR/submit.sh" "$ds" "$hw" "$variant" default "$seed"
                n=$((n+1))
            done
        done
    done
done

# DN on vanes2019 — A100 only (timing baseline; no synthetic-grid analog)
for seed in "${SEEDS[@]}"; do
    "$DIR/submit.sh" vanes2019 a100 dn default "$seed"
    n=$((n+1))
done

echo "[tier2] submitted $n jobs"
