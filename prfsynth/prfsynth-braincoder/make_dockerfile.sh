#!/bin/bash

# Get the directory of the current script
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

# Remove any existing Dockerfile in the current directory
rm -f "$DIR/Dockerfile"

# Generate the Dockerfile using Neurodocker
neurodocker generate docker \
  --base-image ubuntu:20.04 \                      # Use Ubuntu 20.04 as the base image
  --pkg-manager apt \                              # Use apt as the package manager
  --install zsh wget git build-essential \         # Install essential tools
  --miniconda \                                    # Add Miniconda for Python and dependencies
    version=latest \                               # Use the latest version of Miniconda
    conda_install="python=3.7 pandas matplotlib scikit-learn seaborn ipython \
                   pytables tensorflow netcdf4 tensorflow-probability pingouin \
                   mkl-service tqdm" \            # Install Conda packages
    pip_install="https://github.com/Gilles86/braincoder/archive/refs/tags/v0.3.zip" \ # Install braincoder via pip
    env_exists=false \                             # Create a new Conda environment
    env_name="neuro" \                             # Name the Conda environment "neuro"
  > "$DIR/Dockerfile"                              # Output Dockerfile to the script directory

# Notify user of completion
echo "Dockerfile has been successfully generated in $DIR."
