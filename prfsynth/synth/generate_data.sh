#!/bin/bash
#SBATCH --job-name=synthesize_data          # Job name
#SBATCH --output=logs/synthesize_data_prfsynth_%j.out    # Standard output log (%j will be replaced by the job ID)
#SBATCH --time=1:00:00                   # Time limit (hh:mm:ss)
#SBATCH --nodes=16                       # Number of nodes
#SBATCH --ntasks=16                      # Number of tasks (1 per node by default)
#SBATCH --cpus-per-task=1                # CPUs per task
#SBATCH --mem=64G                         # Memory allocation

# Load Singularity module (adjust as needed for your system)
module load singularityce

# Default base directory and script directory
DEFAULT_BASEDIR="/shares/zne.uzh/gdehol/ds-prfsynth"
SCRIPT_DIR=/home/gdehol/git/paper_braincoder/prfsynth/synth
DEFAULT_CONFIG_FILE="$SCRIPT_DIR/prfsynth-config.json"

# Allow basedir and config file to be overridden by arguments
config_file=${1:-$DEFAULT_CONFIG_FILE}
basedir=${2:-$DEFAULT_BASEDIR}

# Define the Singularity image and output directory
SIF_IMAGE="/shares/zne.uzh/containers/prfsynth_latest.sif"
OUTPUT_DIR="$basedir"

# Ensure the base directory exists
if [[ ! -d "$basedir" ]]; then
    echo "Error: Base directory $basedir does not exist."
    exit 1
fi

# Ensure the config file exists
if [[ ! -f "$config_file" ]]; then
    echo "Error: Config file $config_file does not exist."
    exit 1
fi

# Run the Singularity command
singularity exec --cleanenv \
    --bind "$config_file:/flywheel/v0/input/config.json" \
    --bind "$OUTPUT_DIR:/flywheel/v0/output" \
    "$SIF_IMAGE" /flywheel/v0/run

# Check the exit status of the Singularity command
if [[ $? -eq 0 ]]; then
    echo "Singularity command executed successfully."
else
    echo "Error: Singularity command failed."
    exit 1
fi
