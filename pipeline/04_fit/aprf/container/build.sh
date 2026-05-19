#!/bin/bash -l
# Build the patched prfanalyze-aprf container.
#
# Output: /shares/zne.uzh/containers/prfanalyze-aprf-fixed.sif
#         (or wherever $OUTPUT_DIR points)
#
# Run on the cluster login node — no GPU needed, just apptainer.
# Takes ~5 minutes (pip reinstall of scipy + numpy + nilearn).
set -euo pipefail

module load apptainer

DIR="$(cd "$(dirname "$0")" && pwd)"
DEF="$DIR/prfanalyze-aprf-fixed.def"
OUTPUT_DIR="${OUTPUT_DIR:-/shares/zne.uzh/containers}"
SIF_OUT="$OUTPUT_DIR/prfanalyze-aprf-fixed.sif"

echo "[build] def: $DEF"
echo "[build] out: $SIF_OUT"

apptainer build --force "$SIF_OUT" "$DEF"

echo "[build] DONE: $SIF_OUT"
ls -la "$SIF_OUT"
