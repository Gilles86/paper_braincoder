#!/bin/bash
IDENTIFIER=$1  # Pass 'very_small', 'small', etc., as the first argument
if [ -z "$IDENTIFIER" ]; then
    echo "Error: No identifier provided!"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

basedir=/data/ds-prfsynth
CONFIG_FILE=$PWD/configs/default_config.yml
LOG_RUNTIME_FILE="logs/runtime-${IDENTIFIER}.txt"

echo "Running with identifier: $IDENTIFIER"
echo "Using config file: $CONFIG_FILE"


START_TIME=$SECONDS

# Run Docker and measure execution time
{ time docker run --rm -it \
      -v $basedir/BIDS:/bids_folder \
      -v $PWD/docker_package/run.py:/run.py \
      -v $CONFIG_FILE:/config.yml:ro  \
      prfanalyze-braincoder /bids_folder /config.yml --participant_label $IDENTIFIER ; } 2> "logs/time-${IDENTIFIER}.txt"

# End timing
END_TIME=$SECONDS
DURATION=$((END_TIME - START_TIME))

# Write runtime to a log file
echo "Execution time: ${DURATION} seconds" > "$LOG_RUNTIME_FILE"
cat "logs/time-${IDENTIFIER}.txt" >> "$LOG_RUNTIME_FILE"

echo "Execution time recorded in $LOG_RUNTIME_FILE"

cp "$LOG_RUNTIME_FILE" "$basedir/BIDS/derivatives/prfanalyze-braincoder/sub-$IDENTIFIER/ses-1/sub-smallgrid_ses-1_task-prf_acq-normal_run-01_runtime.txt"