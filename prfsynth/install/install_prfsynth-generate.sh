#!/bin/bash
#SBATCH --job-name=pull_prfsynth          # Job name
#SBATCH --output=logs/pull_prfsynth_%j.out    # Standard output log (%j will be replaced by the job ID)
#SBATCH --time=1:00:00                   # Time limit (hh:mm:ss)
#SBATCH --nodes=16                       # Number of nodes
#SBATCH --ntasks=16                      # Number of tasks (1 per node by default)
#SBATCH --cpus-per-task=1                # CPUs per task
#SBATCH --mem=64G                         # Memory allocation

# Load Singularity module (adjust as needed for your system)
module load singularityce

# Define default target directory for Singularity image
DEFAULT_TARGET_DIR=/shares/zne.uzh/containers
IMAGE_NAME=synthprf.sif
DOCKER_IMAGE=docker://garikoitz/synthprf:1.0.0

# Allow TARGET_DIR to be set via a command line argument
TARGET_DIR=${1:-$DEFAULT_TARGET_DIR}

# Ensure the target directory exists
mkdir -p "$TARGET_DIR"

# Change to the target directory
cd "$TARGET_DIR"

# Pull the Singularity image
srun singularity pull "$IMAGE_NAME" "$DOCKER_IMAGE"

# Check if the image was successfully pulled
echo "Finished pulling the image. Checking..."
if [[ -f "$TARGET_DIR/$IMAGE_NAME" ]]; then
    echo "Singularity image pulled successfully: $TARGET_DIR/$IMAGE_NAME"
else
    echo "Failed to pull Singularity image."
    exit 1
fi