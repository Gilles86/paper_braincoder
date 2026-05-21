#!/bin/bash -l
#SBATCH --job-name=build_prfanalyze_fixed_sif
#SBATCH --output=/home/gdehol/logs/%x-%j.out
#SBATCH --error=/home/gdehol/logs/%x-%j.err
#SBATCH --time=30:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --account=zne.uzh
#
# Build a `prfanalyze-<pkg>-fixed.sif` from the upstream image by
# applying the shared scipy<1.9 pin (see pin-scipy-for-mcr.def).
#
# Usage:
#   sbatch pipeline/04_fit/_container_fix/build.sh aprf
#   sbatch pipeline/04_fit/_container_fix/build.sh vista
#
# Output: /shares/zne.uzh/containers/prfanalyze-<pkg>-fixed.sif

set -euo pipefail

PKG=${1:?package required: aprf | vista | popeye | afni}

module load apptainer
unset APPTAINER_BINDPATH SINGULARITY_BIND

if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    DEF="$SLURM_SUBMIT_DIR/pipeline/04_fit/_container_fix/pin-scipy-for-mcr.def"
else
    DEF="$(cd "$(dirname "$0")" && pwd)/pin-scipy-for-mcr.def"
fi

CONTAINER_DIR="${OUTPUT_DIR:-/shares/zne.uzh/containers}"
UPSTREAM_SIF="$CONTAINER_DIR/prfanalyze-${PKG}.sif"
SIF_OUT="$CONTAINER_DIR/prfanalyze-${PKG}-fixed.sif"

[ -f "$UPSTREAM_SIF" ] || { echo "[build] upstream missing: $UPSTREAM_SIF" >&2; exit 1; }

echo "[build] pkg=$PKG  def=$DEF"
echo "[build] upstream: $UPSTREAM_SIF"
echo "[build] out:      $SIF_OUT"

apptainer build --force --ignore-fakeroot-command \
    --build-arg "UPSTREAM_SIF=$UPSTREAM_SIF" \
    "$SIF_OUT" "$DEF"

echo "[build] DONE: $SIF_OUT"
ls -la "$SIF_OUT"
