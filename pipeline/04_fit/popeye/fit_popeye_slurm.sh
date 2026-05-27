#!/bin/bash -l
#SBATCH --job-name=prfanalyze_popeye
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=32
#SBATCH --mem=0
#SBATCH --ntasks=1
#SBATCH --account=zne.uzh

set -eo pipefail
module load apptainer

IDENTIFIER=${1:?identifier required (smallgrid|mediumgrid|largegrid|vanes2019|...)}
SEED=${2:-0}
mkdir -p logs

REPO="$HOME/git/paper_braincoder"
CONFIG_FILE=$PWD/configs/prfanalyze-popeye-${IDENTIFIER}.json
OUTPUT_DIR=/shares/zne.uzh/gdehol/ds-prfsynth
SIF_IMAGE=/shares/zne.uzh/containers/prfanalyze-popeye.sif

# Upstream container's /flywheel/v0/run.sh BIDSifies outputs by
# prepending sub-X_ses-Y_task-prf_ to every .nii.gz in the output
# directory. If files from a previous rerun linger, the loop prepends
# ANOTHER copy of the prefix on top — stacking to 4/6/8-deep across
# multiple reruns and breaking collect_r2's canonical-name lookup.
# Pre-cleaning the per-cell dir prevents the stacking.
POPEYE_OUT="$OUTPUT_DIR/BIDS/derivatives/prfanalyze-popeye/sub-${IDENTIFIER}/ses-1"
if [ -d "$POPEYE_OUT" ]; then
    echo "[fit_popeye_slurm] cleaning stale outputs in $POPEYE_OUT"
    rm -rf "$POPEYE_OUT"
fi

echo "[fit_popeye_slurm] identifier=$IDENTIFIER seed=$SEED  cpus=${SLURM_CPUS_PER_TASK:-?}"

START=$SECONDS
apptainer exec --cleanenv --writable-tmpfs \
    --bind "$OUTPUT_DIR:/flywheel/v0/input" \
    --bind "$OUTPUT_DIR:/flywheel/v0/output" \
    --bind "$CONFIG_FILE:/flywheel/v0/input/config.json" \
    --bind "$REPO/pipeline/04_fit/popeye/run_popeye_parallel.py:/scripts/run_popeye.py" \
    --env POPEYE_N_JOBS=${SLURM_CPUS_PER_TASK:-32} \
    "$SIF_IMAGE" \
    /flywheel/v0/run.sh
DURATION=$((SECONDS - START))

HW="cpu${SLURM_CPUS_PER_TASK:-32}"
# This runner bind-mounts a custom multiprocessing.Pool wrapper at
# /scripts/run_popeye.py. To keep the upstream-serial popeye numbers
# distinguishable in fig_speed, tag the variant explicitly.
VARIANT="parallel${SLURM_CPUS_PER_TASK:-32}"
RESULTS_DIR="$REPO/notes/data/runtime"
mkdir -p "$RESULTS_DIR"
RUNTIME_TSV="$RESULTS_DIR/popeye.${VARIANT}.${HW}.native.seed${SEED}-${IDENTIFIER}.tsv"
{
    printf 'package\thardware\tbackend\tvariant\tdataset\tn_iter\tseed\twall_seconds\tinternal_fit_seconds\tjob_id\thostname\ttimestamp\n'
    printf 'popeye\t%s\tnative\t%s\t%s\tdefault\t%s\t%d\tNA\t%s\t%s\t%s\n' \
        "$HW" "$VARIANT" "$IDENTIFIER" "$SEED" "$DURATION" "${SLURM_JOB_ID:-NA}" "$(hostname)" "$(date -Is)"
} > "$RUNTIME_TSV"

echo "[fit_popeye_slurm] DONE in ${DURATION}s → $RUNTIME_TSV"
