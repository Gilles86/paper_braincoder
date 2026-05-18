#!/bin/bash
# GPU-type benchmark — same fit across every GPU class on the cluster.
#   vanes2019 × {V100, L4, A100, H100, H200} × TF × full × 3 seeds
#   = 15 jobs
#
# Tests scaling across the cluster's GPU lineup (mostly limited by
# compute throughput at this dataset size, since vanes2019 is small in
# absolute terms). H100/H200 require CUDA 12+, which all our env YMLs
# already target (tensorflow[and-cuda]==2.20 bundles CUDA 12.5).
#
# Usage: ./submit_gpus.sh [seeds...]    (default seeds: 1 2 3)

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
SEEDS=("${@:-1 2 3}")

n=0
for hw in v100 l4 a100 h100 h200; do
    for seed in "${SEEDS[@]}"; do
        "$DIR/submit.sh" vanes2019 "$hw" full default "$seed" tensorflow
        n=$((n+1))
    done
done

echo "[gpus] submitted $n jobs"
