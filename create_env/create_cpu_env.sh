#!/bin/bash -l
#SBATCH --job-name=create_cpu_env
#SBATCH --output=/home/gdehol/logs/%x-%j.out
#SBATCH --error=/home/gdehol/logs/%x-%j.err
#SBATCH --time=00:45:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --account=zne.uzh
#
# Build the CPU environment on the cluster.
#
# Usage:
#   sbatch create_env/create_cpu_env.sh

set -euo pipefail
source "$HOME/data/miniforge3/etc/profile.d/conda.sh"

REPO="$HOME/git/paper_braincoder"
YML="$REPO/create_env/environment_cpu.yml"
ENV_NAME=$(grep '^name:' "$YML" | awk '{print $2}')

# Clean rebuild: `conda env update --prune` doesn't pip-uninstall extras
# that the YML dropped, so an outdated env can keep stale packages around
# (we hit this with leftover tensorflow alongside tensorflow-cpu). Just
# nuke and recreate — these envs build in <10 min anyway.
if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    echo "[create_cpu_env] $ENV_NAME exists; removing for clean rebuild"
    conda env remove -y -n "$ENV_NAME"
fi
echo "[create_cpu_env] creating $ENV_NAME"
conda env create -f "$YML"

conda activate "$ENV_NAME"
python -c "import keras; print('Keras', keras.__version__, 'backend:', keras.backend.backend())"
python -c "import braincoder; print('braincoder', getattr(braincoder, '__version__', '?'))"
echo "[create_cpu_env] done."
