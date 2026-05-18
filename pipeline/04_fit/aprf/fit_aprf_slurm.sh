#!/bin/bash -l
#SBATCH --job-name=prfanalyze_aprf
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err
#SBATCH --time=15:00
#SBATCH --cpus-per-task=32
#SBATCH --mem=0  # Use all available memory
#SBATCH --ntasks=1
#SBATCH --account=zne.uzh

set -eo pipefail
module load apptainer

IDENTIFIER=${1:?identifier required (smallgrid|mediumgrid|largegrid|vanes2019|...)}
mkdir -p logs

CONFIG_FILE=$PWD/configs/prfanalyze-aprf-${IDENTIFIER}.json
OUTPUT_DIR=/shares/zne.uzh/gdehol/ds-prfsynth
SIF_IMAGE=/shares/zne.uzh/containers/prfanalyze-aprf.sif

echo "[fit_aprf_slurm] identifier=$IDENTIFIER  config=$(basename "$CONFIG_FILE")"

apptainer exec --cleanenv --writable-tmpfs \
    --bind "$OUTPUT_DIR:/flywheel/v0/input" \
    --bind "$OUTPUT_DIR:/flywheel/v0/output" \
    --bind "$CONFIG_FILE:/flywheel/v0/input/config.json" \
    "$SIF_IMAGE" \
    /flywheel/v0/run.sh
