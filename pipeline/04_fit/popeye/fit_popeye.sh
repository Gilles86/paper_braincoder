#!/bin/bash
IDENTIFIER=$1  # Pass 'very_small', 'small', etc., as the first argument
if [ -z "$IDENTIFIER" ]; then
    echo "Error: No identifier provided!"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

basedir=/data/ds-prfsynth
CONFIG_FILE=$PWD/configs/prfanalyze-popeye-${IDENTIFIER}.json

echo "Running with identifier: $IDENTIFIER"
echo "Using config file: $CONFIG_FILE"

# Run Singularity with writable-tmpfs

docker run --rm -it \
      -v $basedir:/flywheel/v0/input \
      -v $basedir:/flywheel/v0/output \
      -v $CONFIG_FILE:/flywheel/v0/input/config.json:ro  \
         garikoitz/prfanalyze-popeye