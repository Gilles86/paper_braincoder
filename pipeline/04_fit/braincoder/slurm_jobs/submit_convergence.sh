#!/bin/bash
# Convergence sweep: vanes2019, A100, full Gauss+GD, n_gd_iterations
# swept over a log grid × 3 seeds. Answers: how many iterations do we need?
#
# Usage: ./submit_convergence.sh [seeds...]   (default: 1 2 3)

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
SEEDS=("${@:-1 2 3}")

N_ITERS=(10 30 100 300 1000 3000 10000)

echo "[convergence] launching with seeds: ${SEEDS[*]}  n_iter values: ${N_ITERS[*]}"

n=0
for n_iter in "${N_ITERS[@]}"; do
    for seed in "${SEEDS[@]}"; do
        "$DIR/submit.sh" vanes2019 a100 full "$n_iter" "$seed"
        n=$((n+1))
    done
done

echo "[convergence] submitted $n jobs"
