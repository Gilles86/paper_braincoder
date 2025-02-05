#!/bin/bash
#SBATCH --job-name=prfanalyze_afni
#SBATCH --output=logs/%x-%j-%N-%u-%a-%t.out
#SBATCH --error=logs/%x-%j-%N-%u-%a-%t.err
#SBATCH --time=08:00:00
#SBATCH --cpus-per-task=32
#SBATCH --mem=32G  # Use all available memory
#SBATCH --ntasks=1

module load singularityce

# Set your variables
IDENTIFIER=$1  # Pass 'very_small', 'small', etc., as the first argument
if [ -z "$IDENTIFIER" ]; then
    echo "Error: No identifier provided!"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

CONFIG_FILE=$PWD/configs/prfanalyze-afni-${IDENTIFIER}.json
OUTPUT_DIR=/shares/zne.uzh/gdehol/ds-prfsynth
SIF_IMAGE=/shares/zne.uzh/containers/prfanalyze-afni.sif

echo "Running with identifier: $IDENTIFIER"
echo "Using config file: $CONFIG_FILE"

# Start timing
START_TIME=$SECONDS
LOG_RUNTIME_FILE="logs/runtime-${IDENTIFIER}.txt"

# Run Singularity with writable-tmpfs and measure execution time
{ time singularity exec --cleanenv --writable-tmpfs \
    --bind "$OUTPUT_DIR:/flywheel/v0/input" \
    --bind "$OUTPUT_DIR:/flywheel/v0/output" \
    --bind "$CONFIG_FILE:/flywheel/v0/input/config.json" \
    "$SIF_IMAGE" \
    /flywheel/v0/run.sh ; } 2> "logs/time-${IDENTIFIER}.txt"

# End timing
END_TIME=$SECONDS
DURATION=$((END_TIME - START_TIME))

# Write runtime to a log file
echo "Execution time: ${DURATION} seconds" > "$LOG_RUNTIME_FILE"
cat "logs/time-${IDENTIFIER}.txt" >> "$LOG_RUNTIME_FILE"

 cp "$LOG_RUNTIME_FILE" "$OUTPUT_DIR/BIDS/derivatives/prfanalyze-afni/sub-$IDENTIFIER/ses-1/sub-smallgrid_ses-1_task-prf_acq-normal_runtime.txt"


echo "Execution time recorded in $LOG_RUNTIME_FILE"


# OUTPUT_DIR=/shares/zne.uzh/gdehol/ds-prfsynth
# for IDENTIFIER in smallgrid mediumgrid largegrid; do
#     LOG_RUNTIME_FILE="logs/runtime-${IDENTIFIER}.txt"
#     cp "$LOG_RUNTIME_FILE" "$OUTPUT_DIR/BIDS/derivatives/prfanalyze-afni/sub-$IDENTIFIER/ses-1/sub-smallgrid_ses-1_task-prf_acq-normal_runtime.txt"
# done