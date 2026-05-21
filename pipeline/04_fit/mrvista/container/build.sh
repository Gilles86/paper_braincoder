#!/bin/bash -l
#SBATCH --job-name=build_vista_fixed_sif
#SBATCH --output=/home/gdehol/logs/%x-%j.out
#SBATCH --error=/home/gdehol/logs/%x-%j.err
#SBATCH --time=30:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --account=zne.uzh

set -euo pipefail
module load apptainer
unset APPTAINER_BINDPATH SINGULARITY_BIND

if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    DIR="$SLURM_SUBMIT_DIR/pipeline/04_fit/mrvista/container"
    [ -f "$DIR/prfanalyze-vista-fixed.def" ] || DIR="$SLURM_SUBMIT_DIR"
else
    DIR="$(cd "$(dirname "$0")" && pwd)"
fi
DEF="$DIR/prfanalyze-vista-fixed.def"
SIF_OUT="${OUTPUT_DIR:-/shares/zne.uzh/containers}/prfanalyze-vista-fixed.sif"

echo "[build] def: $DEF"
echo "[build] out: $SIF_OUT"

apptainer build --force --ignore-fakeroot-command "$SIF_OUT" "$DEF"
echo "[build] DONE: $SIF_OUT"
ls -la "$SIF_OUT"
