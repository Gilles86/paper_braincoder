#!/bin/bash -l
#SBATCH --job-name=collect_r2
#SBATCH --output=/home/gdehol/logs/%x-%j.out
#SBATCH --error=/home/gdehol/logs/%x-%j.err
#SBATCH --time=20:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --account=zne.uzh

set -euo pipefail
source "$HOME/data/miniforge3/etc/profile.d/conda.sh"
conda activate paper_braincoder_cpu

REPO="${SLURM_SUBMIT_DIR:-$HOME/git/paper_braincoder}"
cd "$REPO"

python -m prfbench.collect_r2 --skip-voxelwise
