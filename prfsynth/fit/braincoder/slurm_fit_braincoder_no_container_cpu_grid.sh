#!/bin/bash
#SBATCH --job-name=prfanalyze-braincoder-cpu
#SBATCH --output=logs/%x-%j-%N-%u-%j.out
#SBATCH --error=logs/%x-%j-%N-%u-%j.err
#SBATCH --time=1:00:00
#SBATCH --cpus-per-task=32
#SBATCH --mem=32G
#SBATCH --ntasks=1

set -e  # Exit immediately if a command fails

# Load user environment
. "$HOME/.bashrc"

# Ensure an identifier is provided
IDENTIFIER="$1"
if [ -z "$IDENTIFIER" ]; then
    echo "Error: No identifier provided!"
    exit 1
fi

# Ensure logs directory exists
mkdir -p logs

# Define paths
BASEDIR="/shares/zne.uzh/gdehol/ds-prfsynth"
SIF_IMAGE="/shares/zne.uzh/containers/prfanalyze-aprf.sif"
OUTPUT_DIR="$BASEDIR/BIDS/derivatives/prfanalyze-braincoder.cpu"
LOG_RUNTIME_FILE="logs/braincoder.grid.cpu-runtime-${IDENTIFIER}.txt"
PYTHON_OUTPUT_FILE="logs/braincoder.grid.cpu-output-${IDENTIFIER}.txt"

# Choose the appropriate config file
if [ "$IDENTIFIER" == "vanes2019" ]; then
    CONFIG_FILE="$PWD/configs/vanes2019_config_grid.yml"
else
    CONFIG_FILE="$PWD/configs/default_grid_config.yml"
fi

echo "Running with identifier: $IDENTIFIER"
echo "Using config file: $CONFIG_FILE"

# Activate Conda environment
conda activate tf2-gpu

# Start timing
START_TIME=$SECONDS

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Run the analysis and capture output separately
python "$PWD/docker_package/run.py" "$BASEDIR/BIDS" "$CONFIG_FILE" \
 --participant_label "$IDENTIFIER" --output_dir "$OUTPUT_DIR" \
 > "$PYTHON_OUTPUT_FILE" 2>&1

# Compute execution time
DURATION=$((SECONDS - START_TIME))
echo "Execution time: ${DURATION} seconds" > "$LOG_RUNTIME_FILE"

echo "Execution time recorded in $LOG_RUNTIME_FILE"

# Ensure final output directory exists before copying
FINAL_OUTPUT_DIR="$OUTPUT_DIR/sub-$IDENTIFIER/ses-1"
mkdir -p "$FINAL_OUTPUT_DIR"
cp "$LOG_RUNTIME_FILE" "$FINAL_OUTPUT_DIR/sub-${IDENTIFIER}_ses-1_task-prf_runtime.txt"