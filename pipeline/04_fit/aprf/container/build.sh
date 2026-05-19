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

# The `module load apptainer` sets APPTAINER_BINDPATH=/apps,/scratch,/shares.
# That breaks `apptainer build` from a base .sif: the bootstrap image
# doesn't have /apps as a mount destination, and the build fails with
# "destination /apps doesn't exist in container". Clear it for the build.
unset APPTAINER_BINDPATH SINGULARITY_BIND

DIR="$(cd "$(dirname "$0")" && pwd)"
DEF="$DIR/prfanalyze-aprf-fixed.def"
OUTPUT_DIR="${OUTPUT_DIR:-/shares/zne.uzh/containers}"
SIF_OUT="$OUTPUT_DIR/prfanalyze-aprf-fixed.sif"

echo "[build] def: $DEF"
echo "[build] out: $SIF_OUT"

apptainer build --force "$SIF_OUT" "$DEF"

echo "[build] DONE: $SIF_OUT"
ls -la "$SIF_OUT"
