#!/bin/bash
# Thin wrapper that submits a single braincoder fit with the right SBATCH
# resource flags for the (hardware, dataset, variant) combo.
#
# Usage:
#   ./submit.sh <dataset> <hardware> <variant> [n_iter] [seed]
#
# n_iter defaults to "default" (use config's value).
# seed   defaults to 42.

set -euo pipefail

DATASET=${1:?dataset required}
HARDWARE=${2:?hardware required}
VARIANT=${3:?variant required}
N_ITER=${4:-default}
SEED=${5:-42}

case "$HARDWARE" in
    cpu)  GRES="";                       CPUS=32; MEM=32G ;;
    gpu)  GRES="--gres=gpu:1";           CPUS=8;  MEM=64G ;;
    a100) GRES="--gres=gpu:A100:1";      CPUS=8;  MEM=64G ;;
    *)    echo "Unknown hardware: $HARDWARE"; exit 1 ;;
esac

# Wall-time budget — generous; we want completion, not eviction
case "$DATASET-$VARIANT-$HARDWARE" in
    *-dn-*)                                   TIME=8:00:00 ;;
    largegrid-*-cpu | vanes2019-*-cpu)        TIME=8:00:00 ;;
    vanes2019-*-*)                            TIME=2:00:00 ;;
    largegrid-*-*)                            TIME=1:00:00 ;;
    *)                                        TIME=30:00   ;;
esac

JOBNAME="bc.${HARDWARE}.${VARIANT}.${DATASET}.s${SEED}"
[ "$N_ITER" != "default" ] && JOBNAME="${JOBNAME}.n${N_ITER}"

DIR="$(cd "$(dirname "$0")" && pwd)"

set -x
sbatch $GRES \
    --time="$TIME" \
    --cpus-per-task="$CPUS" \
    --mem="$MEM" \
    -J "$JOBNAME" \
    "$DIR/run.sh" "$DATASET" "$HARDWARE" "$VARIANT" "$N_ITER" "$SEED"
