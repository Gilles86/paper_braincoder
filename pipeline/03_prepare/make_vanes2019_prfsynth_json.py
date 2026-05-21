"""Generate a fake prfsynth-format bold.json for vanes2019.

The prfanalyze-* BIDS-apps expect a per-voxel JSON file with a Stimulus
block + a placeholder RF block. For synthetic data, prfsynth creates
this with per-voxel ground truth (Centerx0, sigmaMajor, etc.). For real
data like vanes2019 we have no ground truth, so we populate the RF
block with dummy zeros — the fitters use only the Stimulus block for
geometry and do their own fitting.

Run on cluster (it writes into /shares/...).
"""
import json
import os
import sys

import nibabel as nib

BASEDIR = '/shares/zne.uzh/gdehol/ds-prfsynth'
BOLD = os.path.join(BASEDIR, 'BIDS', 'sub-vanes2019', 'ses-1', 'func',
                    'sub-vanes2019_ses-1_task-prf_acq-normal_run-01_bold.nii.gz')
APERTURE = os.path.join(BASEDIR, 'BIDS', 'stimuli',
                        'sub-vanes2019_ses-1_task-prf_apertures.nii.gz')
OUT = os.path.join(BASEDIR, 'BIDS', 'derivatives', 'prfsynth',
                   'sub-vanes2019', 'ses-1',
                   'sub-vanes2019_ses-1_task-prf_acq-normal_run-01_bold.json')

bold = nib.load(BOLD)
ap = nib.load(APERTURE)
n_voxels = int(bold.shape[0] * bold.shape[1] * bold.shape[2])
n_t = int(bold.shape[3])
# aperture stored as (Y, X, 1, T) per prepare_vanes.py
resized_vert, resized_horz = int(ap.shape[0]), int(ap.shape[1])
tr = 1.5  # vanes2019 TR

# Geometry: vanes2019 spans 20° horizontally and ~11° vertically per
# load_vanes2019 (width_degrees=20, dy=dx, height = aperture_rows * dy).
field_horz = 20.0
field_vert = float(resized_vert) * (field_horz / float(resized_horz))

stimulus = {
    'fieldofviewHorz': field_horz,
    'fieldofviewVert': field_vert,
    'expName':         'vanes2019',
    'Binary':          True,
    'Resize':          True,
    'ResizedHorz':     resized_horz,
    'ResizedVert':     resized_vert,
    'barWidth':        2,            # not strictly meaningful here
    'durationSecs':    int(n_t * tr),
    'frameduration':   tr,           # one frame per TR for our aperture
    'Shuffle':         False,
    'shuffleSeed':     0,
}

# Dummy RF block. Fitters ignore it (they fit from BOLD); the prfsynth
# round-trip just needs it present so the prfanalyze-* BIDS app's
# JSON parser doesn't choke.
rf = {
    'Centerx0':       0.0,
    'Centery0':       0.0,
    'Theta':          0.0,
    'sigmaMajor':     1.0,
    'sigmaMinor':     1.0,
    'dog_sigmaMajor': 2.0,
    'dog_sigmaMinor': 2.0,
    'dog_Theta':      0.0,
    'dog_Scale':      0.5,
    'Type':           'realdata',  # marks this as not-synthetic
}

row = {
    'TR':                  tr,
    'Type':                'realdata',
    'cssexp':              0.05,
    'signalPercentage':    'bold',
    'BOLDcontrast':        5,
    'BOLDmeanValue':       10000,
    'computeSubclasses':   False,
    'HRF':  [{'Type': 'vista_twogammas', 'Duration': 20, 'normalize': 'norm',
              'params': {'a': [6, 12], 'b': [0.9, 0.9], 'c': 0.35, 'n': 3,
                         'tau': 1.08, 'delay': 2.05, 'stimDuration': 1}}],
    'RF':                  [rf],
    'Stimulus':            [stimulus],
    'Noise':               [{'voxel': 'real', 'seed': 'na'}],
    'SNR':                 0.0,
}

data = [dict(row) for _ in range(n_voxels)]

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w') as fh:
    json.dump(data, fh)

print('Wrote %s' % OUT)
print('  n_voxels:    %d' % n_voxels)
print('  n_timepoints %d' % n_t)
print('  resized:     %dx%d (vert x horz)' % (resized_vert, resized_horz))
print('  fieldofview: %.1f x %.1f deg (vert x horz)' % (field_vert, field_horz))
