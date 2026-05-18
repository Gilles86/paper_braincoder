#!/bin/bash -l
#SBATCH --job-name=braincoder
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err
#SBATCH --ntasks=1
#SBATCH --account=zne.uzh
#
# Worker script for one braincoder fit cell.
#
# Login shell (`-l`) so /etc/profile is sourced and `module` works
# (we don't currently load any modules but downstream variants might).
# Conda is activated explicitly below, not via the (interactive-only)
# ~/.bashrc.
#
# Usage (via submit.sh, which sets the SBATCH resource flags):
#   sbatch run.sh <dataset> <hardware> <variant> <n_iter> <seed>
#
# Args:
#   dataset   smallgrid | mediumgrid | largegrid | vanes2019
#   hardware  cpu | gpu | a100
#   variant   grid | full | hrf | dn
#   n_iter    integer  or  "default" (use config's n_gd_iterations)
#   seed      integer

set -euo pipefail
source "$HOME/data/miniforge3/etc/profile.d/conda.sh"

DATASET=${1:?dataset required}
HARDWARE=${2:?hardware required}
VARIANT=${3:?variant required}
N_ITER=${4:-default}
SEED=${5:-42}

BASEDIR="/shares/zne.uzh/gdehol/ds-prfsynth"
REPO="$HOME/git/paper_braincoder"
FIT_DIR="$REPO/pipeline/04_fit/braincoder"
RESULTS_DIR="$REPO/results/runtime"

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
TAG="${VARIANT}.${HARDWARE}"
if [ "$N_ITER" != "default" ]; then TAG="${TAG}.n${N_ITER}"; fi
TAG="${TAG}.seed${SEED}"
OUTPUT_DIR="$BASEDIR/BIDS/derivatives/prfanalyze-braincoder.${TAG}"
mkdir -p "$OUTPUT_DIR"

# --- hardware-specific TF gating ---------------------------------------
if [ "$HARDWARE" = "cpu" ]; then
    export CUDA_VISIBLE_DEVICES=""
fi

# --- activate env -------------------------------------------------------
# Default env name (TF backend). The backend axis will override this
# via a future --backend flag once the three CUDA envs exist on the
# cluster.
conda activate "${BRAINCODER_ENV:-paper_braincoder_cuda}"

# --- compose CLI extras -------------------------------------------------
EXTRA_ARGS=(--seed "$SEED")
if [ "$N_ITER" != "default" ]; then
    EXTRA_ARGS+=(--n_iterations "$N_ITER")
fi

# --- run ----------------------------------------------------------------
mkdir -p logs
RUN_LOG="logs/braincoder.${TAG}-${DATASET}-${SLURM_JOB_ID:-local}"

echo "[run.sh] $(date -Is)  ${TAG}  dataset=${DATASET}  config=$(basename $CONFIG)"
echo "[run.sh] CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}"

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
mkdir -p "$RESULTS_DIR"
RUNTIME_TSV="$RESULTS_DIR/braincoder.${TAG}-${DATASET}.tsv"
{
    printf 'package\thardware\tvariant\tdataset\tn_iter\tseed\twall_seconds\tinternal_fit_seconds\tjob_id\thostname\ttimestamp\n'
    printf 'braincoder\t%s\t%s\t%s\t%s\t%s\t%d\t%s\t%s\t%s\t%s\n' \
        "$HARDWARE" "$VARIANT" "$DATASET" "$N_ITER" "$SEED" \
        "$DURATION" "$INTERNAL" "${SLURM_JOB_ID:-NA}" "$(hostname)" "$(date -Is)"
} > "$RUNTIME_TSV"

echo "[run.sh] DONE  ${TAG} / ${DATASET}  wall=${DURATION}s  internal=${INTERNAL}s  → $RUNTIME_TSV"
