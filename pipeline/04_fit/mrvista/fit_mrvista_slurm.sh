#!/bin/bash -l
#SBATCH --job-name=prfanalyze_vista
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err
#SBATCH --time=8:00:00
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
CONFIG_FILE=$PWD/configs/prfanalyze-vista-${IDENTIFIER}.json
OUTPUT_DIR=/shares/zne.uzh/gdehol/ds-prfsynth
SIF_IMAGE=/shares/zne.uzh/containers/prfanalyze-vista-fixed.sif

echo "[fit_mrvista_slurm] identifier=$IDENTIFIER seed=$SEED  cpus=${SLURM_CPUS_PER_TASK:-?}"

START=$SECONDS
# Bind-mount our patched /scripts/run.py over the container's. The
# upstream copy has an undefined ``opts_file`` on the isPRFSynthData
# path that triggers a misleading "Failed to exec /solve.sh script!"
# message and produces no output. See upstream_patch/run.py for the
# fix + comment.
PATCHED_RUN_PY="$PWD/upstream_patch/run.py"

apptainer exec --cleanenv --writable-tmpfs \
    --bind "$OUTPUT_DIR:/flywheel/v0/input" \
    --bind "$OUTPUT_DIR:/flywheel/v0/output" \
    --bind "$CONFIG_FILE:/flywheel/v0/input/config.json" \
    --bind "$PATCHED_RUN_PY:/scripts/run.py" \
    "$SIF_IMAGE" \
    /flywheel/v0/run.sh
DURATION=$((SECONDS - START))

HW="cpu${SLURM_CPUS_PER_TASK:-32}"
RESULTS_DIR="$REPO/notes/data/runtime"
mkdir -p "$RESULTS_DIR"
RUNTIME_TSV="$RESULTS_DIR/mrvista.default.${HW}.native.seed${SEED}-${IDENTIFIER}.tsv"
{
    printf 'package\thardware\tbackend\tvariant\tdataset\tn_iter\tseed\twall_seconds\tinternal_fit_seconds\tjob_id\thostname\ttimestamp\n'
    printf 'mrvista\t%s\tnative\tdefault\t%s\tdefault\t%s\t%d\tNA\t%s\t%s\t%s\n' \
        "$HW" "$IDENTIFIER" "$SEED" "$DURATION" "${SLURM_JOB_ID:-NA}" "$(hostname)" "$(date -Is)"
} > "$RUNTIME_TSV"

echo "[fit_mrvista_slurm] DONE in ${DURATION}s → $RUNTIME_TSV"
