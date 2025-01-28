#!/bin/bash

# Check if a filename is provided as an argument
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <json-file>"
    exit 1
fi

# Get the full path to the script and JSON file
json_file="$1"
script_dir=$(pwd)

# Verify if the JSON file exists in the current directory
if [ ! -f "$script_dir/$json_file" ]; then
    echo "Error: JSON file '$json_file' not found in the current directory."
    exit 1
fi

# Set the base directory for the Docker volume
basedir="/data/ds-prfsynth"

# Run the Docker command
docker run --rm -it \
    -v "$script_dir/$json_file:/flywheel/v0/input/config.json" \
      -v $basedir:/flywheel/v0/input \
      -v $basedir:/flywheel/v0/output \
    garikoitz/prfanalyze-popeye

echo "Docker command executed successfully. Output is in '$basedir'."