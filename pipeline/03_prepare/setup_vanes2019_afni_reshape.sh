#!/bin/bash
# 1. Cancel still-running AFNI vanes2019
# 2. Clean stale prfanalyze-afni_temp* dirs that may confuse the MATLAB binary
# 3. Build a 'reshaped' alias subject sub-vanes2019afni with BOLD in a real
#    2D layout that AFNI's MATLAB code should handle.
# 4. Resubmit AFNI on the alias subject.
set -e
BASEDIR=/shares/zne.uzh/gdehol/ds-prfsynth

echo "=== cancel running AFNI vanes2019 ==="
squeue -u gdehol --noheader -o "%i %j" 2>&1 \
    | awk '/prfanalyze_afni/ {print $1}' \
    | while read jid; do scancel "$jid" && echo "cancelled $jid"; done

echo
echo "=== clean stale AFNI temp dirs ==="
find "$BASEDIR/BIDS/derivatives" -maxdepth 1 -name "prfanalyze-afni_temp*" -exec rm -rf {} + 2>/dev/null || true
ls -d "$BASEDIR/BIDS/derivatives/prfanalyze-afni"* 2>/dev/null | head -5

echo
echo "=== build alias subject sub-vanes2019afni ==="
source ~/data/miniforge3/etc/profile.d/conda.sh
conda activate paper_braincoder_cpu
python <<'PY'
import os
import json
import numpy as np
import nibabel as nib
from pathlib import Path

BASE = Path('/shares/zne.uzh/gdehol/ds-prfsynth')
BIDS = BASE / 'BIDS'

orig_bold_path = BIDS / 'sub-vanes2019' / 'ses-1' / 'func' / 'sub-vanes2019_ses-1_task-prf_acq-normal_run-01_bold.nii.gz'
orig_im = nib.load(str(orig_bold_path))
data = np.asanyarray(orig_im.dataobj)   # shape (118584, 1, 1, 120)
n_vox = data.shape[0] * data.shape[1] * data.shape[2]
n_t = data.shape[3]
assert n_vox == 118584, n_vox

# 118584 = 486 × 244  (486 = 2*3^5, 244 = 2^2 * 61); both > 1 so no singleton dims.
NX, NY = 486, 244
assert NX * NY == n_vox
data = data.reshape(NX, NY, 1, n_t)
print('reshaped BOLD to', data.shape)

# Save under sub-vanes2019afni — a parallel BIDS subject that keeps
# the original vanes2019 intact for the other fitters.
afni_func = BIDS / 'sub-vanes2019afni' / 'ses-1' / 'func'
afni_func.mkdir(parents=True, exist_ok=True)
new_bold = afni_func / 'sub-vanes2019afni_ses-1_task-prf_acq-normal_run-01_bold.nii.gz'
hdr = orig_im.header.copy()
new_im = nib.Nifti1Image(data.astype(np.float32), orig_im.affine, header=hdr)
new_im.set_data_dtype(np.float32)
new_im.header.set_slope_inter(slope=1, inter=0)
new_im.to_filename(str(new_bold))
print('wrote', new_bold)

# Mirror the events.tsv and bold.json sidecar
for sidecar in orig_bold_path.parent.glob('sub-vanes2019_ses-1_task-prf*.tsv'):
    dest = afni_func / sidecar.name.replace('vanes2019', 'vanes2019afni')
    dest.write_bytes(sidecar.read_bytes())
for sidecar in orig_bold_path.parent.glob('sub-vanes2019_ses-1_task-prf*.json'):
    dest = afni_func / sidecar.name.replace('vanes2019', 'vanes2019afni')
    dest.write_bytes(sidecar.read_bytes())
print('mirrored sidecars')

# Mirror stimulus apertures
stim_src = BIDS / 'stimuli' / 'sub-vanes2019_ses-1_task-prf_apertures.nii.gz'
stim_dst = BIDS / 'stimuli' / 'sub-vanes2019afni_ses-1_task-prf_apertures.nii.gz'
stim_dst.write_bytes(stim_src.read_bytes())
print('mirrored stimulus')

# Build the prfsynth-style fake JSON for the new subject. Same Stimulus
# block, dummy RF, 118584 entries.
src_json = BIDS / 'derivatives' / 'prfsynth' / 'sub-vanes2019' / 'ses-1' / 'sub-vanes2019_ses-1_task-prf_acq-normal_run-01_bold.json'
dst_json = BIDS / 'derivatives' / 'prfsynth' / 'sub-vanes2019afni' / 'ses-1' / 'sub-vanes2019afni_ses-1_task-prf_acq-normal_run-01_bold.json'
dst_json.parent.mkdir(parents=True, exist_ok=True)
dst_json.write_bytes(src_json.read_bytes())
print('mirrored prfsynth json')

print('DONE')
PY

echo
echo "=== make AFNI config for vanes2019afni ==="
cp ~/git/paper_braincoder/pipeline/04_fit/afni/configs/prfanalyze-afni-vanes2019.json \
   ~/git/paper_braincoder/pipeline/04_fit/afni/configs/prfanalyze-afni-vanes2019afni.json
sed -i 's/"vanes2019"/"vanes2019afni"/' \
    ~/git/paper_braincoder/pipeline/04_fit/afni/configs/prfanalyze-afni-vanes2019afni.json
cat ~/git/paper_braincoder/pipeline/04_fit/afni/configs/prfanalyze-afni-vanes2019afni.json

echo
echo "=== resubmit AFNI on vanes2019afni × 3 seeds ==="
cd ~/git/paper_braincoder/pipeline/04_fit/afni
for s in 1 2 3; do
    J=$(sbatch --parsable fit_afni_slurm.sh vanes2019afni "$s") && echo "afni vanes2019afni s$s = $J"
done
