#!/bin/bash

# Ensure an identifier is provided
IDENTIFIER="$1"
if [ -z "$IDENTIFIER" ]; then
    echo "Error: No identifier provided!"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Define paths
BASEDIR="/data/ds-prfsynth"
CONFIG_FILE="$PWD/configs/prfanalyze-aprf-${IDENTIFIER}.json"
OUTPUT_DIR="$BASEDIR/BIDS/derivatives/prfanalyze-aprf"
LOG_RUNTIME_FILE="logs/aprf-runtime-${IDENTIFIER}.txt"
PYTHON_OUTPUT_FILE="logs/aprf-output-${IDENTIFIER}.txt"

echo "Running with identifier: $IDENTIFIER"
echo "Using config file: $CONFIG_FILE"

# Start timing
START_TIME=$SECONDS

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Run Docker and capture output
docker run --rm -it \
      -v "$BASEDIR:/flywheel/v0/input" \
      -v "$BASEDIR:/flywheel/v0/output" \
      -v "$CONFIG_FILE:/flywheel/v0/input/config.json:ro" \
      garikoitz/prfanalyze-aprf > "$PYTHON_OUTPUT_FILE" 2>&1

# Compute execution time
DURATION=$((SECONDS - START_TIME))
echo "Execution time: ${DURATION} seconds" > "$LOG_RUNTIME_FILE"

echo "Execution time recorded in $LOG_RUNTIME_FILE"

# Ensure final output directory exists before copying
FINAL_OUTPUT_DIR="$OUTPUT_DIR/sub-$IDENTIFIER/ses-1"
mkdir -p "$FINAL_OUTPUT_DIR"
cp "$LOG_RUNTIME_FILE" "$FINAL_OUTPUT_DIR/sub-${IDENTIFIER}_ses-1_task-prf_runtime.txt"