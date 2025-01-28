#!/bin/bash
#SBATCH --job-name=pull_prfanalyze       # Job name
#SBATCH --output=logs/pull_prfanalyze_%j.out # Standard output log (%j will be replaced by the job ID)
#SBATCH --time=1:00:00                   # Time limit (hh:mm:ss)
#SBATCH --nodes=1                        # Number of nodes
#SBATCH --ntasks=1                       # Number of tasks
#SBATCH --cpus-per-task=16                # CPUs per task
#SBATCH --mem=32G                         # Memory allocation

# Load Singularity module (adjust as needed for your system)
module load singularityce

# Define default target directory for Singularity images
DEFAULT_TARGET_DIR=/shares/zne.uzh/containers

# Allow TARGET_DIR to be set via a command line argument
TARGET_DIR=${1:-$DEFAULT_TARGET_DIR}

# Ensure the target directory exists
mkdir -p "$TARGET_DIR"

# Change to the target directory
cd "$TARGET_DIR"

# Define images to pull
IMAGES=(
    "docker://garikoitz/prfanalyze-vista:2.3.1_3.1.2"
    "docker://garikoitz/prfanalyze-popeye:1.0.1"
    "docker://garikoitz/prfanalyze-afni:2.0.0_3.1.0"
    "docker://garikoitz/prfanalyze-aprf:2.1.5_3.1.1"
)

# Pull all images sequentially
for DOCKER_IMAGE in "${IMAGES[@]}"; do
    IMAGE_NAME=$(basename "$DOCKER_IMAGE" | sed 's/:/_/').sif
    echo "Pulling $DOCKER_IMAGE into $TARGET_DIR/$IMAGE_NAME..."
    singularity pull "$IMAGE_NAME" "$DOCKER_IMAGE"

    # Check if the image was successfully pulled
    if [[ -f "$TARGET_DIR/$IMAGE_NAME" ]]; then
        echo "Singularity image pulled successfully: $TARGET_DIR/$IMAGE_NAME"
    else
        echo "Failed to pull Singularity image: $DOCKER_IMAGE"
        exit 1
    fi
done

# Final message
echo "All images processed and installed in $TARGET_DIR."
