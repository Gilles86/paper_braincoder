#!/bin/bash -l
#SBATCH --job-name=build_aprf_fixed_sif
#SBATCH --output=/home/gdehol/logs/%x-%j.out
#SBATCH --error=/home/gdehol/logs/%x-%j.err
#SBATCH --time=30:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --account=zne.uzh
#
# Build the patched prfanalyze-aprf container.
#
# Output: /shares/zne.uzh/containers/prfanalyze-aprf-fixed.sif
#         (or wherever $OUTPUT_DIR points)
#
# Submit as:
#   sbatch pipeline/04_fit/aprf/container/build.sh
#
# Why a SLURM job and not the login node: the final mksquashfs step
# needs ~16-32 GB RAM to pack a ~5 GB image; the login node OOMs.
set -euo pipefail

module load apptainer

# `module load apptainer` sets APPTAINER_BINDPATH=/apps,/scratch,/shares.
# That breaks `apptainer build` from a base .sif: the bootstrap image
# doesn't have /apps as a mount destination, and the build fails with
# "destination /apps doesn't exist in container".
unset APPTAINER_BINDPATH SINGULARITY_BIND

# Under sbatch, "$0" is a copy of this script in /var/spool/slurmd/
# (not where we submitted from), so dirname "$0" doesn't help. Use
# SLURM_SUBMIT_DIR when present; fall back to the script's own dir
# for interactive runs.
if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    REPO_ROOT="$SLURM_SUBMIT_DIR"
    # SLURM_SUBMIT_DIR may be the repo root or anywhere — find the def.
    if [ -f "$REPO_ROOT/pipeline/04_fit/aprf/container/prfanalyze-aprf-fixed.def" ]; then
        DIR="$REPO_ROOT/pipeline/04_fit/aprf/container"
    else
        DIR="$REPO_ROOT"
    fi
else
    DIR="$(cd "$(dirname "$0")" && pwd)"
fi
DEF="$DIR/prfanalyze-aprf-fixed.def"
OUTPUT_DIR="${OUTPUT_DIR:-/shares/zne.uzh/containers}"
SIF_OUT="$OUTPUT_DIR/prfanalyze-aprf-fixed.sif"

echo "[build] def: $DEF"
echo "[build] out: $SIF_OUT"
echo "[build] node: $(hostname)  mem: $(free -g | awk '/^Mem:/ {print $2}') GB"

# --ignore-fakeroot-command: apptainer's bundled `faked` daemon was built
# against glibc 2.33+. The bootstrap container is Ubuntu Xenial (glibc
# 2.23), so faked exits with `GLIBC_2.33 not found`. Our %post only
# writes to /opt/conda which is user-owned anyway, so root isn't needed.
apptainer build --force --ignore-fakeroot-command "$SIF_OUT" "$DEF"

echo "[build] DONE: $SIF_OUT"
ls -la "$SIF_OUT"

echo "[build] DONE: $SIF_OUT"
ls -la "$SIF_OUT"
