#!/bin/bash -l
# Diagnostic: slice vanes2019 BOLD to its first 49k voxels and reshape
# to a (250, 196, 1, 120) layout that matches largegrid's shape almost
# exactly. If AFNI completes on this subset (and fails on the full
# 118k-voxel reshape), we know the silent failure is a memory/scale
# issue and we can chunk vanes2019 into 3 pieces to get full coverage.
#
# Creates sub-vanes2019afni49k under the BIDS dir + a parallel
# prfsynth derivative JSON so the existing afni SLURM wrapper sees
# this as a normal subject.
#
# Usage:  bash setup_vanes2019afni_49kchunk.sh
# Then:   sbatch fit_afni_slurm.sh vanes2019afni49k 1

set -euo pipefail
BASEDIR=/shares/zne.uzh/gdehol/ds-prfsynth
BIDS="$BASEDIR/BIDS"

source ~/data/miniforge3/etc/profile.d/conda.sh
conda activate paper_braincoder_cpu

python <<'PY'
import json
import numpy as np
import nibabel as nib
from pathlib import Path

BASE = Path('/shares/zne.uzh/gdehol/ds-prfsynth')
BIDS = BASE / 'BIDS'

orig = BIDS / 'sub-vanes2019' / 'ses-1' / 'func' / 'sub-vanes2019_ses-1_task-prf_acq-normal_run-01_bold.nii.gz'
im = nib.load(str(orig))
data = np.asanyarray(im.dataobj)            # (118584, 1, 1, 120)
n_vox = data.shape[0] * data.shape[1] * data.shape[2]
n_t = data.shape[3]
assert n_vox == 118584, n_vox

# Take the first 49000 voxels = matches largegrid exactly.
# 49000 = 250 x 196 — same factorisation as largegrid (X, Y).
SUB_N = 49000
NX, NY = 250, 196
assert NX * NY == SUB_N

sub_data = data.reshape(n_vox, n_t)[:SUB_N]
sub_data = sub_data.reshape(NX, NY, 1, n_t)
print(f'sliced BOLD: {sub_data.shape}  values: min={sub_data.min():.3f} max={sub_data.max():.3f}')

func_dir = BIDS / 'sub-vanes2019afni49k' / 'ses-1' / 'func'
func_dir.mkdir(parents=True, exist_ok=True)
new_bold = func_dir / 'sub-vanes2019afni49k_ses-1_task-prf_acq-normal_run-01_bold.nii.gz'

hdr = im.header.copy()
new_im = nib.Nifti1Image(sub_data.astype(np.float32), im.affine, header=hdr)
new_im.set_data_dtype(np.float32)
new_im.header.set_slope_inter(slope=1, inter=0)
new_im.to_filename(str(new_bold))
print('wrote', new_bold)

# Mirror sidecars + events.
for sidecar in orig.parent.glob('sub-vanes2019_ses-1_task-prf*.tsv'):
    dst = func_dir / sidecar.name.replace('vanes2019', 'vanes2019afni49k')
    dst.write_bytes(sidecar.read_bytes())
for sidecar in orig.parent.glob('sub-vanes2019_ses-1_task-prf*.json'):
    dst = func_dir / sidecar.name.replace('vanes2019', 'vanes2019afni49k')
    dst.write_bytes(sidecar.read_bytes())

# Mirror stimulus apertures.
stim_src = BIDS / 'stimuli' / 'sub-vanes2019_ses-1_task-prf_apertures.nii.gz'
stim_dst = BIDS / 'stimuli' / 'sub-vanes2019afni49k_ses-1_task-prf_apertures.nii.gz'
stim_dst.write_bytes(stim_src.read_bytes())
print('mirrored stimulus + sidecars')

# prfsynth-style fake JSON so AFNI's BIDS-app accepts it as a known subject.
src_json = (BIDS / 'derivatives' / 'prfsynth' / 'sub-vanes2019' / 'ses-1'
            / 'sub-vanes2019_ses-1_task-prf_acq-normal_run-01_bold.json')
dst_json = (BIDS / 'derivatives' / 'prfsynth' / 'sub-vanes2019afni49k' / 'ses-1'
            / 'sub-vanes2019afni49k_ses-1_task-prf_acq-normal_run-01_bold.json')
dst_json.parent.mkdir(parents=True, exist_ok=True)
dst_json.write_bytes(src_json.read_bytes())
print('DONE')
PY

# AFNI config for the new subject.
CFG=~/git/paper_braincoder/pipeline/04_fit/afni/configs
[ -e "$CFG/prfanalyze-afni-vanes2019afni49k.json" ] || \
    sed 's/"vanes2019"/"vanes2019afni49k"/' \
        "$CFG/prfanalyze-afni-vanes2019.json" > "$CFG/prfanalyze-afni-vanes2019afni49k.json"

cat "$CFG/prfanalyze-afni-vanes2019afni49k.json"
echo
echo "Now: sbatch ~/git/paper_braincoder/pipeline/04_fit/afni/fit_afni_slurm.sh vanes2019afni49k 1"
