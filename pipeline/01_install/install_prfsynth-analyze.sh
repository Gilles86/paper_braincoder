#!/bin/bash -l
#SBATCH --job-name=pull_prfanalyze
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err
#SBATCH --time=1:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --account=zne.uzh

set -eo pipefail
module load apptainer

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
    apptainer pull "$IMAGE_NAME" "$DOCKER_IMAGE"

    if [[ -f "$TARGET_DIR/$IMAGE_NAME" ]]; then
        echo "Image pulled: $TARGET_DIR/$IMAGE_NAME"
    else
        echo "Failed to pull image: $DOCKER_IMAGE"
        exit 1
    fi
done

# Final message
echo "All images processed and installed in $TARGET_DIR."
