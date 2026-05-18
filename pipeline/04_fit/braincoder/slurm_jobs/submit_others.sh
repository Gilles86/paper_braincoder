#!/bin/bash
# Submit non-braincoder fitters (AFNI / aPRF / popeye / mrVista) on all
# four datasets × 3 seeds. Fitters themselves are deterministic — seeds
# are just for cluster-jitter SEM bands.
#
# Usage: ./submit_others.sh [seeds...]   (default: 1 2 3)
#
# Lives next to the braincoder submit_*.sh scripts for convenience; the
# actual sbatch invocations dispatch to the per-package fit_*_slurm.sh
# files under their respective pipeline/04_fit/<pkg>/ directories.

set -euo pipefail
SEEDS=("${@:-1 2 3}")
REPO="$HOME/git/paper_braincoder"

n=0
for pkg in aprf popeye mrvista afni; do
    cd "$REPO/pipeline/04_fit/$pkg"
    for ds in smallgrid mediumgrid largegrid vanes2019; do
        for seed in "${SEEDS[@]}"; do
            sbatch "fit_${pkg}_slurm.sh" "$ds" "$seed" >/dev/null \
                && n=$((n+1)) || echo "  failed: $pkg/$ds/seed$seed"
        done
    done
done

echo "[others] submitted $n jobs"
