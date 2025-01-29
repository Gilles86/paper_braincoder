#!/bin/bash
#SBATCH --job-name=prfanalyze
#SBATCH --output=logs/%x-%j-%N-%u-%a-%t.out
#SBATCH --error=logs/%x-%j-%N-%u-%a-%t.err
#SBATCH --time=15:00
#SBATCH --cpus-per-task=32
#SBATCH --mem=0  # Use all available memory
#SBATCH --ntasks=1

# Set your variables
IDENTIFIER=$1  # Pass 'very_small', 'small', etc., as the first argument
if [ -z "$IDENTIFIER" ]; then
    echo "Error: No identifier provided!"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

CONFIG_FILE=$PWD/configs/prfanalyze-vista-${IDENTIFIER}.json
OUTPUT_DIR=/shares/zne.uzh/gdehol/ds-prfsynth
SIF_IMAGE=/shares/zne.uzh/containers/prfanalyze-vista.sif

echo "Running with identifier: $IDENTIFIER"
echo "Using config file: $CONFIG_FILE"

# Run Singularity with writable-tmpfs
singularity exec --cleanenv --writable-tmpfs \
    --bind "$OUTPUT_DIR:/flywheel/v0/input" \
    --bind "$OUTPUT_DIR:/flywheel/v0/output" \
    --bind $CONFIG_FILE:/flywheel/v0/input/config.json \
    "$SIF_IMAGE" \
    /flywheel/v0/run.sh
