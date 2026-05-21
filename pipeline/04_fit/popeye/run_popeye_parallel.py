# -*- coding: utf-8 -*-
"""Drop-in parallel replacement for /scripts/run_popeye.py.

Bind-mount this file at runtime via the SLURM script:

    apptainer exec --bind run_popeye_parallel.py:/scripts/run_popeye.py ...

Upstream popeye fits voxels one at a time in a serial for-loop. Per-voxel
work is ~10 s, so on a 49k-voxel dataset the original runner takes ~7
days single-threaded. This patch wraps the loop in
`multiprocessing.Pool(POPEYE_N_JOBS)` — workers fork from the parent so
the (large) stimulus array and BOLD data are shared via copy-on-write.
On 32 CPU cores this gives ~30x speedup; vanes2019 fits in 6-8 h instead
of 10-12 days.

The serial runner had a small bug too: the final `modelpred.nii.gz`
filename was accidentally prefixed with the loop variable `k`. Fixed
inline.

Compatible with the popeye container's Python 2.7 (no f-strings, etc.).
"""
import ctypes
import json
import multiprocessing
import os
import sys

import numpy as np
import nibabel as nib
import pimms
import six

import popeye.og_hrf as og
import popeye.utilities as utils
from popeye.visual_stimulus import VisualStimulus


# CLI args from the BIDS-app spec: opts, bold, stim, stim_json, outdir.
(opts_file, bold_file, stim_file, stimjs_file, outdir) = sys.argv[1:]

with open(opts_file, 'r') as fl:
    opts = json.load(fl)
bold_im = nib.load(bold_file)
stim_im = nib.load(stim_file)
with open(stimjs_file, 'r') as fl:
    stim_json = json.load(fl)

np.random.seed(opts.get('seed', 2764932))
Ns = opts.get('grid_density', 3)

bold = np.reshape(np.asarray(bold_im.dataobj), (-1, bold_im.shape[-1]))
stim = np.squeeze(np.asarray(stim_im.dataobj))

if len(stim_json) != bold.shape[0]:
    raise ValueError(
        'BOLD Image and Stimulus JSON do not have the same number of data points'
    )

# Module-level globals visible to workers via fork(). Avoid passing the
# large stim array through Pool.map(), which would pickle a fresh copy
# per voxel.
_STIM = stim
_NS = Ns


def _fit_voxel(args):
    """Fit one voxel; called in a worker process via Pool.map.

    args = (ii, vx, js). Returns (overloaded_estimate, prediction).
    """
    ii, vx, js = args
    stdat = js['Stimulus']
    if pimms.is_list(stdat):
        stdat = stdat[0]
    height = stdat['fieldofviewVert']
    width = stdat['fieldofviewHorz']

    dist = 100  # arbitrary; stim_width parameterizes via tan(width/2)
    stim_width = 2 * dist * np.tan(np.pi / 180 * width / 2)
    stimulus = VisualStimulus(
        _STIM, dist, stim_width, 1.0, float(js['TR']), ctypes.c_int16,
    )
    model = og.GaussianModel(stimulus, utils.double_gamma_hrf)

    x_grid = (-width / 2, width / 2)
    y_grid = (-height / 2, height / 2)
    s_grid = (1 / stimulus.ppd + 0.25, 5.25)
    h_grid = (-1.0, 1.0)
    x_bound = (-width, width)
    y_bound = (-height, height)
    s_bound = (1 / stimulus.ppd, 12.0)
    b_bound = (1e-8, None)
    u_bound = (None, None)
    h_bound = (-3.0, 3.0)
    grids = (x_grid, y_grid, s_grid, h_grid)
    bounds = (x_bound, y_bound, s_bound, h_bound, b_bound, u_bound)

    fit = og.GaussianFit(
        model, vx, grids, bounds, Ns=_NS,
        voxel_index=(ii, 1, 1), auto_fit=True, verbose=0,
    )
    return fit.overloaded_estimate, fit.prediction


def main():
    n_jobs = int(os.environ.get('POPEYE_N_JOBS', multiprocessing.cpu_count()))
    n_voxels = len(bold)
    print('[run_popeye_parallel] n_voxels=%d  n_jobs=%d  Ns=%d'
          % (n_voxels, n_jobs, Ns))
    sys.stdout.flush()

    chunksize = max(1, n_voxels // (n_jobs * 4))
    args_iter = zip(range(n_voxels), bold, stim_json)

    pool = multiprocessing.Pool(n_jobs)
    try:
        results = pool.map(_fit_voxel, args_iter, chunksize=chunksize)
    finally:
        pool.close()
        pool.join()

    # Re-assemble in input order (map preserves order).
    fields = ('theta', 'rho', 'sigma', 'hrfdelay', 'beta', 'baseline')
    res = {k: [] for k in fields}
    res['pred'] = []
    for est, pred in results:
        for k, v in zip(fields, est):
            res[k].append(v)
        res['pred'].append(pred)

    # Convert to the x0/y0/sigma layout prfanalyze expects.
    rr = {
        'x0':          np.cos(res['theta']) * res['rho'],
        'y0':          np.sin(res['theta']) * res['rho'],
        'sigmamajor':  res['sigma'],
        'sigmaminor':  res['sigma'],
        'beta':        res['beta'],
        'baseline':    res['baseline'],
        'hrfdelay':    res['hrfdelay'],
    }
    for k, v in six.iteritems(rr):
        im = nib.Nifti1Image(np.reshape(v, bold_im.shape[:-1]), bold_im.affine)
        im.to_filename(os.path.join(outdir, k + '.nii.gz'))

    im = nib.Nifti1Image(np.reshape(bold, bold_im.shape), bold_im.affine)
    im.to_filename(os.path.join(outdir, 'testdata.nii.gz'))

    # Upstream bug fix: the original wrote 'modelpred.nii.gz' prefixed
    # with the trailing loop variable `k` (= 'hrfdelay'), shipping
    # 'hrfdelaymodelpred.nii.gz' instead. Fix the filename here.
    im = nib.Nifti1Image(np.reshape(res['pred'], bold_im.shape), bold_im.affine)
    im.to_filename(os.path.join(outdir, 'modelpred.nii.gz'))

    print('Popeye finished succesfully.')
    sys.exit(0)


if __name__ == '__main__':
    main()
