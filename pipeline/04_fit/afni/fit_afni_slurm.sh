#!/bin/bash -l
#SBATCH --job-name=prfanalyze_afni
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err
#SBATCH --time=08:00:00
#SBATCH --cpus-per-task=32
#SBATCH --mem=32G
#SBATCH --ntasks=1
#SBATCH --account=zne.uzh

set -eo pipefail
module load apptainer

IDENTIFIER=${1:?identifier required (smallgrid|mediumgrid|largegrid|vanes2019|...)}
mkdir -p logs

CONFIG_FILE=$PWD/configs/prfanalyze-afni-${IDENTIFIER}.json
OUTPUT_DIR=/shares/zne.uzh/gdehol/ds-prfsynth
SIF_IMAGE=/shares/zne.uzh/containers/prfanalyze-afni.sif

echo "[fit_afni_slurm] identifier=$IDENTIFIER  config=$(basename "$CONFIG_FILE")"

LOG_RUNTIME_FILE="logs/runtime-${IDENTIFIER}.txt"
START_TIME=$SECONDS

{ time apptainer exec --cleanenv --writable-tmpfs \
    --bind "$OUTPUT_DIR:/flywheel/v0/input" \
    --bind "$OUTPUT_DIR:/flywheel/v0/output" \
    --bind "$CONFIG_FILE:/flywheel/v0/input/config.json" \
    "$SIF_IMAGE" \
    /flywheel/v0/run.sh ; } 2> "logs/time-${IDENTIFIER}.txt"

DURATION=$((SECONDS - START_TIME))
echo "Execution time: ${DURATION} seconds" > "$LOG_RUNTIME_FILE"
cat "logs/time-${IDENTIFIER}.txt" >> "$LOG_RUNTIME_FILE"

# Copy runtime alongside the derivative outputs.
DEST_DIR="$OUTPUT_DIR/BIDS/derivatives/prfanalyze-afni/sub-$IDENTIFIER/ses-1"
mkdir -p "$DEST_DIR"
cp "$LOG_RUNTIME_FILE" "$DEST_DIR/sub-${IDENTIFIER}_ses-1_task-prf_runtime.txt"

echo "[fit_afni_slurm] done; runtime ${DURATION}s; logged to $LOG_RUNTIME_FILE"
