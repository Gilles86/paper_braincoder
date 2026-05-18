#!/bin/bash
# Backend benchmark — TF vs JAX vs PyTorch on the same fit, same GPU.
#   {largegrid, vanes2019} × A100 × {tf, jax, torch} × full × 3 seeds
#   = 18 jobs
#
# We pick A100 as the reference because it's the most common allocation
# in our Tier 2; the GPU-type axis lives in submit_gpus.sh.
#
# Usage: ./submit_backends.sh [seeds...]    (default seeds: 1 2 3)

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
SEEDS=("${@:-1 2 3}")

n=0
for ds in largegrid vanes2019; do
    for backend in tensorflow jax torch; do
        for seed in "${SEEDS[@]}"; do
            "$DIR/submit.sh" "$ds" a100 full default "$seed" "$backend"
            n=$((n+1))
        done
    done
done

echo "[backends] submitted $n jobs"
