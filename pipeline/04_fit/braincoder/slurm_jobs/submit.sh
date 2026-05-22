#!/bin/bash
# Thin wrapper that submits a single braincoder fit with the right SBATCH
# resource flags for the (hardware, dataset, variant, backend) combo.
#
# Usage:
#   ./submit.sh <dataset> <hardware> <variant> [n_iter] [seed] [backend]
#
# n_iter  defaults to "default" (use config's value)
# seed    defaults to 42
# backend defaults to "tensorflow"  (jax | torch | tensorflow)
#
# hardware: cpu | cpu8 | cpu16 | cpu32 | gpu | a100 | h100 | h200 | l4 | v100
#   gpu = any-available; the others pin a specific type via --gres.
#   cpu8/cpu16/cpu32 = CPU run with that many cores. `cpu` aliases cpu32.

set -euo pipefail

DATASET=${1:?dataset required}
HARDWARE=${2:?hardware required}
VARIANT=${3:?variant required}
N_ITER=${4:-default}
SEED=${5:-42}
BACKEND=${6:-tensorflow}
NOISE_MODEL=${7:-gaussian}

# Translate hardware → SBATCH resources. Memory is set generously to
# cover the largest dataset (vanes2019 × DN); shrink later if queue
# pressure makes it worth it.
case "$HARDWARE" in
    cpu | cpu32)  GRES=""; CPUS=32; MEM=32G ;;
    cpu16)        GRES=""; CPUS=16; MEM=32G ;;
    cpu8)         GRES=""; CPUS=8;  MEM=32G ;;
    gpu)          GRES="--gres=gpu:1";      CPUS=8;  MEM=64G ;;
    a100)         GRES="--gres=gpu:A100:1"; CPUS=8;  MEM=64G ;;
    h100)         GRES="--gres=gpu:H100:1"; CPUS=8;  MEM=64G ;;
    h200)         GRES="--gres=gpu:H200:1"; CPUS=8;  MEM=64G ;;
    l4)           GRES="--gres=gpu:L4:1";   CPUS=8;  MEM=32G ;;
    v100)         GRES="--gres=gpu:V100:1"; CPUS=8;  MEM=32G ;;
    *) echo "Unknown hardware: $HARDWARE"; exit 1 ;;
esac

# Wall-time budget: generous; we want completion not eviction.
case "$DATASET-$VARIANT-$HARDWARE" in
    *-dn-*)                                                                   TIME=8:00:00 ;;
    largegrid-*-cpu* | vanes2019-*-cpu* | largegrid-*-cpu | vanes2019-*-cpu)  TIME=8:00:00 ;;
    vanes2019-*-*)                                                            TIME=2:00:00 ;;
    largegrid-*-*)                                                            TIME=1:00:00 ;;
    *)                                                                        TIME=30:00   ;;
esac

JOBNAME="bc.${HARDWARE}.${BACKEND}.${VARIANT}.${DATASET}.s${SEED}"
[ "$NOISE_MODEL" != "gaussian" ] && JOBNAME="${JOBNAME}.${NOISE_MODEL}"
[ "$N_ITER" != "default" ] && JOBNAME="${JOBNAME}.n${N_ITER}"

DIR="$(cd "$(dirname "$0")" && pwd)"

set -x
sbatch $GRES \
    --time="$TIME" \
    --cpus-per-task="$CPUS" \
    --mem="$MEM" \
    -J "$JOBNAME" \
    "$DIR/run.sh" "$DATASET" "$HARDWARE" "$VARIANT" "$N_ITER" "$SEED" "$BACKEND" "$NOISE_MODEL"
