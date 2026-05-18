#!/bin/bash -l
#SBATCH --job-name=braincoder
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err
#SBATCH --ntasks=1
#SBATCH --account=zne.uzh
#
# Worker script for one braincoder fit cell.
#
# Login shell (`-l`) so /etc/profile is sourced and `module` works.
# Conda is activated explicitly below, not via the (interactive-only)
# ~/.bashrc.
#
# Usage (via submit.sh, which sets the SBATCH resource flags):
#   sbatch run.sh <dataset> <hardware> <variant> <n_iter> <seed> <backend>
#
# Args:
#   dataset   smallgrid | mediumgrid | largegrid | vanes2019
#   hardware  cpu | gpu | a100 | h100 | h200 | l4 | v100
#   variant   grid | full | hrf | dn
#   n_iter    integer  or  "default" (use config's n_gd_iterations)
#   seed      integer
#   backend   tensorflow | jax | torch    (default: tensorflow)

set -euo pipefail
source "$HOME/data/miniforge3/etc/profile.d/conda.sh"

DATASET=${1:?dataset required}
HARDWARE=${2:?hardware required}
VARIANT=${3:?variant required}
N_ITER=${4:-default}
SEED=${5:-42}
BACKEND=${6:-tensorflow}

BASEDIR="/shares/zne.uzh/gdehol/ds-prfsynth"
REPO="$HOME/git/paper_braincoder"
FIT_DIR="$REPO/pipeline/04_fit/braincoder"

# --- pick the right YAML config -----------------------------------------
if [ "$DATASET" = "vanes2019" ]; then
    case "$VARIANT" in
        grid) CONFIG="$FIT_DIR/configs/vanes2019_config_grid.yml" ;;
        full) CONFIG="$FIT_DIR/configs/vanes2019_config.yml" ;;
        hrf)  CONFIG="$FIT_DIR/configs/vanes2019_hrf_config.yml" ;;
        dn)   CONFIG="$FIT_DIR/configs/vanes2019_dn_config.yml" ;;
        *)    echo "Unknown variant: $VARIANT"; exit 1 ;;
    esac
else
    case "$VARIANT" in
        grid) CONFIG="$FIT_DIR/configs/default_grid_config.yml" ;;
        full) CONFIG="$FIT_DIR/configs/default_config.yml" ;;
        hrf)  CONFIG="$FIT_DIR/configs/fit_hrf_config.yml" ;;
        dn)   echo "DN only supported on vanes2019 (no DN ground truth on synthetic grids)"; exit 1 ;;
        *)    echo "Unknown variant: $VARIANT"; exit 1 ;;
    esac
fi

# --- output directory keyed by all axes ---------------------------------
TAG="${VARIANT}.${HARDWARE}.${BACKEND}"
if [ "$N_ITER" != "default" ]; then TAG="${TAG}.n${N_ITER}"; fi
TAG="${TAG}.seed${SEED}"
OUTPUT_DIR="$BASEDIR/BIDS/derivatives/prfanalyze-braincoder.${TAG}"
mkdir -p "$OUTPUT_DIR"

# --- backend + env selection -------------------------------------------
# CPU env only ships with the TF backend; GPU work picks the matching
# CUDA env. JAX/torch on CPU is intentionally not supported here.
case "$HARDWARE" in
    cpu | cpu8 | cpu16 | cpu32)
        if [ "$BACKEND" != "tensorflow" ]; then
            echo "[run.sh] CPU hardware only supports backend=tensorflow (got: $BACKEND)" >&2
            exit 1
        fi
        ENV_NAME="paper_braincoder_cpu"
        export CUDA_VISIBLE_DEVICES=""
        # Pin BLAS / TF thread counts to the SLURM allocation so cpu8 != cpu32
        # purely by virtue of the env vars (not just by what SLURM gave us).
        ncpu="${SLURM_CPUS_PER_TASK:-1}"
        export OMP_NUM_THREADS="$ncpu"
        export MKL_NUM_THREADS="$ncpu"
        export TF_NUM_INTRAOP_THREADS="$ncpu"
        export TF_NUM_INTEROP_THREADS=2
        ;;
    *)
        case "$BACKEND" in
            tensorflow) ENV_NAME="paper_braincoder_cuda" ;;
            jax)        ENV_NAME="paper_braincoder_cuda_jax" ;;
            torch)      ENV_NAME="paper_braincoder_cuda_torch" ;;
            *) echo "Unknown backend: $BACKEND"; exit 1 ;;
        esac
        ;;
esac
export KERAS_BACKEND="$BACKEND"

conda activate "$ENV_NAME"

# --- compose CLI extras -------------------------------------------------
EXTRA_ARGS=(--seed "$SEED")
if [ "$N_ITER" != "default" ]; then
    EXTRA_ARGS+=(--n_iterations "$N_ITER")
fi

# --- run ----------------------------------------------------------------
mkdir -p logs
RUN_LOG="logs/braincoder.${TAG}-${DATASET}-${SLURM_JOB_ID:-local}"

echo "[run.sh] $(date -Is)  ${TAG}  dataset=${DATASET}  config=$(basename $CONFIG)"
echo "[run.sh] env=${ENV_NAME}  backend=${BACKEND}  hardware=${HARDWARE}"
echo "[run.sh] CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}"
echo "[run.sh] node=$(hostname)  nvidia-smi:"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>&1 | head -3 || true

START=$SECONDS
python "$FIT_DIR/docker_package/run.py" "$BASEDIR/BIDS" "$CONFIG" \
    --participant_label "$DATASET" \
    --output_dir "$OUTPUT_DIR" \
    "${EXTRA_ARGS[@]}" \
    > "${RUN_LOG}.out" 2>&1
DURATION=$((SECONDS - START))

# Extract braincoder's internal fit-only time from the stdout
INTERNAL=$(grep -oE 'INTERNAL_FIT_TIME: [0-9.]+' "${RUN_LOG}.out" | awk '{print $2}' | tail -1)
INTERNAL=${INTERNAL:-NA}

# --- write a tidy runtime row -------------------------------------------
RESULTS_DIR="$REPO/notes/data/runtime"
mkdir -p "$RESULTS_DIR"
RUNTIME_TSV="$RESULTS_DIR/braincoder.${TAG}-${DATASET}.tsv"
{
    printf 'package\thardware\tbackend\tvariant\tdataset\tn_iter\tseed\twall_seconds\tinternal_fit_seconds\tjob_id\thostname\ttimestamp\n'
    printf 'braincoder\t%s\t%s\t%s\t%s\t%s\t%s\t%d\t%s\t%s\t%s\t%s\n' \
        "$HARDWARE" "$BACKEND" "$VARIANT" "$DATASET" "$N_ITER" "$SEED" \
        "$DURATION" "$INTERNAL" "${SLURM_JOB_ID:-NA}" "$(hostname)" "$(date -Is)"
} > "$RUNTIME_TSV"

echo "[run.sh] DONE  ${TAG} / ${DATASET}  wall=${DURATION}s  internal=${INTERNAL}s  → $RUNTIME_TSV"
