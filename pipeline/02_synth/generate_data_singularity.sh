#!/bin/bash -l
#SBATCH --job-name=synthesize_data
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err
#SBATCH --time=1:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --account=zne.uzh

set -eo pipefail
module load apptainer

# Default base directory
DEFAULT_BASEDIR="/shares/zne.uzh/gdehol/ds-prfsynth"
SCRIPT_DIR=/home/gdehol/git/paper_braincoder/pipeline/02_synth

# Allow basedir to be overridden by an argument
basedir=${1:-$DEFAULT_BASEDIR}

# Define the Singularity image and run command
SIF_IMAGE="/shares/zne.uzh/containers/prfsynth_latest.sif"
CONFIG_FILE="$SCRIPT_DIR/prfsynth-config.json"
OUTPUT_DIR="$basedir"

# Ensure the base directory exists
if [[ ! -d "$basedir" ]]; then
    echo "Error: Base directory $basedir does not exist."
    exit 1
fi

# Ensure the config file exists
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Error: Config file $CONFIG_FILE does not exist in $SCRIPT_DIR."
    exit 1
fi

# Run the Singularity command
apptainer exec --cleanenv \
    --bind "$CONFIG_FILE:/flywheel/v0/input/config.json" \
    --bind "$OUTPUT_DIR:/flywheel/v0/output" \
    "$SIF_IMAGE" /flywheel/v0/run

# Check the exit status of the Singularity command
if [[ $? -eq 0 ]]; then
    echo "Singularity command executed successfully."
else
    echo "Error: Singularity command failed."
    exit 1
fi
