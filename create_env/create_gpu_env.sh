#!/bin/bash -l
#SBATCH --job-name=create_gpu_env
#SBATCH --output=/home/gdehol/logs/%x-%j.out
#SBATCH --error=/home/gdehol/logs/%x-%j.err
#SBATCH --time=01:30:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --gres=gpu:1
#SBATCH --account=zne.uzh
#
# Build one of the CUDA environments on a GPU compute node so the
# bundled CUDA wheels link against the right NVIDIA driver.
#
# Usage:
#   sbatch create_env/create_gpu_env.sh tf      # paper_braincoder_cuda
#   sbatch create_env/create_gpu_env.sh jax     # paper_braincoder_cuda_jax
#   sbatch create_env/create_gpu_env.sh torch   # paper_braincoder_cuda_torch

set -euo pipefail
source "$HOME/data/miniforge3/etc/profile.d/conda.sh"

BACKEND=${1:?backend required: tf | jax | torch}
REPO="$HOME/git/paper_braincoder"

case "$BACKEND" in
    tf)    YML="$REPO/create_env/environment_cuda.yml"       ;;
    jax)   YML="$REPO/create_env/environment_cuda_jax.yml"   ;;
    torch) YML="$REPO/create_env/environment_cuda_torch.yml" ;;
    *) echo "Unknown backend: $BACKEND"; exit 1 ;;
esac

echo "[create_gpu_env] backend=$BACKEND yml=$YML"
echo "[create_gpu_env] node=$(hostname)  date=$(date -Is)"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv | head -3

ENV_NAME=$(grep '^name:' "$YML" | awk '{print $2}')

# Clean rebuild — see commentary in create_cpu_env.sh.
if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    echo "[create_gpu_env] $ENV_NAME exists; removing for clean rebuild"
    conda env remove -y -n "$ENV_NAME"
fi
echo "[create_gpu_env] creating $ENV_NAME"
conda env create -f "$YML"

# Sanity check the backend sees the GPU
conda activate "$ENV_NAME"
case "$BACKEND" in
    tf)
        export KERAS_BACKEND=tensorflow
        python -c "import tensorflow as tf; print('TF', tf.__version__, 'GPUs:', tf.config.list_physical_devices('GPU'))"
        ;;
    jax)
        export KERAS_BACKEND=jax
        python -c "import jax; print('JAX', jax.__version__, 'backend:', jax.default_backend(), 'devs:', jax.devices())"
        ;;
    torch)
        export KERAS_BACKEND=torch
        python -c "import torch; print('torch', torch.__version__, 'cuda:', torch.cuda.is_available(), 'devs:', torch.cuda.device_count())"
        ;;
esac
python -c "import keras; print('Keras', keras.__version__, 'backend:', keras.backend.backend())"
python -c "import braincoder; print('braincoder', getattr(braincoder, '__version__', '?'))"

echo "[create_gpu_env] done."
