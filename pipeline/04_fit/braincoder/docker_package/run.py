import os
import os.path as op
import argparse
import time
import json
import numpy as np
import pandas as pd
import yaml
from nilearn import image
from nilearn import maskers

# Keras 3 picks its backend from $KERAS_BACKEND (tensorflow / jax / torch).
# Import keras BEFORE braincoder so the backend is locked in by the time
# braincoder's models compile any tf.function / jax.jit / torch.compile.
import keras
import braincoder

__version__ = open(op.join(op.dirname(op.realpath(__file__)),
                                'version')).read()


parser = argparse.ArgumentParser()
parser.add_argument('bids_dir', help='The directory with the input dataset '
                    'formatted according to the BIDS standard.')

parser.add_argument('config_file', help='The path to the json file containing '
                    'the configuration for the fitting analysis.')
parser.add_argument('--output_dir', help='The directory where the output files '
                    'should be stored. If you are running group level analysis '
                    'this folder should be prepopulated with the results of the'
                    'participant level analysis.', nargs=1)
parser.add_argument('--participant_label', help='The label(s) of the participant(s) that should be analyzed. The label '
                    'corresponds to sub-<participant_label> from the BIDS spec '
                    '(so it does not include "sub-"). If this parameter is not '
                    'provided all subjects should be analyzed. Multiple '
                    'participants can be specified with a space separated list.',
                    nargs="+")
parser.add_argument('--data_origin', help='The name of the corresponding synthesizer. '
                    'Can either be prfsynth (default) or prfpy.', nargs=1, default='prfsynth')
parser.add_argument('--skip_bids_validator', help='Whether or not to perform BIDS dataset validation',
                    action='store_true')
parser.add_argument('-v', '--version', action='version',
                    version='BIDS-App example version {}'.format(__version__))
parser.add_argument('-d', '--debug', action='store_true', help='Use only 100th of the data for testing')
parser.add_argument('--n_iterations', type=int, default=None,
                    help='Override fitting.n_gd_iterations from the config. '
                    'Used for the convergence sweep.')
parser.add_argument('--seed', type=int, default=42,
                    help='Random seed for TF/NumPy. Used for benchmark repeats.')
parser.add_argument('--noise-model', dest='noise_model',
                    choices=['ssq', 'gaussian'], default='gaussian',
                    help='Loss function for the gradient-descent fit. '
                    'ssq = sum of squared residuals (original); gaussian = '
                    'per-voxel Gaussian negative log-likelihood with free '
                    'sigma — converges much faster on real fMRI per upstream.')
parser.add_argument('--save-cost-history', dest='save_cost_history',
                    action='store_true',
                    help='Pickle the mean-best-R² convergence trajectory '
                    '(ParameterFitter.r2_history_) next to the output NIfTIs. '
                    'Used to diagnose whether the early-stop defaults '
                    '(r2_atol=1e-6, lag=100) plateaued correctly.')
parser.add_argument('--r2-atol', dest='r2_atol', type=float, default=1e-4,
                    help='Early-stop tolerance: GD halts once mean-best R² '
                    'has improved less than this over the last LAG=100 '
                    'iterations. Braincoder default is 1e-6 but the '
                    'vanes2019 convergence A/B (see notes/figures/'
                    'fig_convergence_delta.pdf) shows the curve is still '
                    'descending at 1e-5 even after 10k iter — 1e-4 cuts '
                    '~3x wall-time at <0.001 R² cost.')

args = parser.parse_args()
print(args)
print(f'braincoder version: {getattr(braincoder, "__version__", "unknown")}')
print(f'keras version:      {keras.__version__}')
print(f'keras backend:      {keras.backend.backend()}')

keras.utils.set_random_seed(args.seed)  # seeds numpy + the active backend
np.random.seed(args.seed)               # belt + suspenders

with open(args.config_file, 'r') as f:
    opts = yaml.safe_load(f)


pars = {'x':'centerx0', 'y':'centery0', 'sd':'sigmamajor', 'amplitude':'beta', 'baseline':'baseline'}

if opts['fitting']['fit_hrf']:
    pars['hrf_delay'] = 'hrf_delay'
    pars['hrf_dispersion'] = 'hrf_dispersion'

assert(len(args.participant_label) == 1), 'Currently only one participant can be analyzed at a time.'
subject_id = args.participant_label[0]
subject_dir = op.join(args.bids_dir, f'sub-{subject_id}')

# make sure there is only one session in there and it's session 1:
sessions = [f for f in os.listdir(subject_dir) if f.startswith('ses-')]
assert(len(sessions) == 1), 'Only one session is allowed for now'
session = sessions[0][4:]

data = op.join(args.bids_dir, f'sub-{subject_id}', 'ses-1', 'func', f'sub-{subject_id}_ses-1_task-prf_acq-normal_run-01_bold.nii.gz')

im = image.load_img(data)
print(im.shape)

if args.debug:
    # Create a mask with all zeros
    mask_data = np.zeros(im.shape[:-1])

    # Randomly select 1/100th of the voxels
    num_voxels = np.prod(mask_data.shape)
    num_selected = num_voxels // 100  # 1/1000th of voxels

    # Flatten, randomly select indices, and set to 1
    indices = np.random.choice(num_voxels, num_selected, replace=False)
    mask_data.flat[indices] = 1

    print(f'***DEBUG ACTIVATED, only using {num_selected} voxels')
else:
    mask_data = np.ones(im.shape[:-1])

# Create a new image with the mask
mask = image.new_img_like(im, mask_data)

masker = maskers.NiftiMasker(mask_img=mask)

data = pd.DataFrame(masker.fit_transform(im))
data.columns.name = 'voxel'
data.index.name = 'time'

paradigm = op.join(args.bids_dir, 'stimuli', f'sub-{subject_id}_ses-1_task-prf_apertures.nii.gz')
paradigm = image.load_img(paradigm).get_fdata()

# Go from (T, 1, Y, X) to (X, Y, T)
paradigm = np.transpose(paradigm.squeeze(), (2,1,0))

print(paradigm.shape)

# Extract parameters from options and stimulus
width_degrees = opts['synth']['width']
height_degrees = opts['synth']['height']
width_pixels, height_pixels = paradigm.shape[1:]

# Calculate the degree per pixel scaling factors
dx = width_degrees / width_pixels
dy = height_degrees / height_pixels

# Generate degree arrays for x and y axes
x_degrees = np.linspace(-width_degrees / 2 + dx / 2, width_degrees / 2 - dx / 2, width_pixels)
y_degrees = np.linspace(-height_degrees / 2 + dy / 2, height_degrees / 2 - dy / 2, height_pixels)
y_mesh, x_mesh = np.meshgrid(y_degrees, x_degrees)

# Flatten the meshgrid and create a DataFrame
grid_coordinates = pd.DataFrame({'x': x_mesh.ravel(), 'y': y_mesh.ravel()}).astype(np.float32)

print(grid_coordinates)

from braincoder.models import GaussianPRF2DWithHRF
from braincoder.hrf import SPMHRFModel
hrf_model = SPMHRFModel(tr=float(opts['synth']['tr']))
model_gauss = GaussianPRF2DWithHRF(data=data, paradigm=paradigm, hrf_model=hrf_model, grid_coordinates=grid_coordinates, flexible_hrf_parameters=opts['fitting']['fit_hrf'])

from braincoder.optimize import ParameterFitter
par_fitter = ParameterFitter(model=model_gauss, data=data, paradigm=paradigm)

# Set up search grid
bounds = opts['fitting']['gauss_bounds']
x = np.linspace(bounds['mu_x']['lower'], bounds['mu_x']['upper'], bounds['mu_x']['n_steps'])
y = np.linspace(bounds['mu_y']['lower'], bounds['mu_y']['upper'], bounds['mu_y']['n_steps'])
sd = np.linspace(bounds['sd']['lower'], bounds['sd']['upper'], bounds['sd']['n_steps'])

# We start the grid search using a correlation cost, so ampltiude
# and baseline do not influence those results.
# We will optimize them later using OLS.
baseline = [1e-6]
amplitude = [1.0]
hrf_delay = [6]
hrf_dispersion = [1]

# Now we can do the grid search

print(f'x: {x}')
print(f'y: {y}')
print(f'sd: {sd}')


n_gd_iterations = args.n_iterations if args.n_iterations is not None else opts.get('fitting', {}).get('n_gd_iterations', 100)
print(f'n_gd_iterations: {n_gd_iterations}  (source: {"--n_iterations CLI" if args.n_iterations is not None else "config"})')

fit_t0 = time.time()

if opts['fitting']['fit_hrf']:
    if opts['fitting'].get('divisive_normalisation', False):
        raise NotImplementedError('Cannot fit HRF and DN right now.')

    pars_gauss_grid = par_fitter.fit_grid(x, y, sd, baseline, amplitude, hrf_delay, hrf_dispersion, use_correlation_cost=True, positive_amplitude=opts['fitting']['force_positive_amplitude'])
else:
    pars_gauss_grid = par_fitter.fit_grid(x, y, sd, baseline, amplitude, use_correlation_cost=True)

print(pars_gauss_grid)

# # And refine the baseline and amplitude parameters using OLS
pars_gauss_ols = par_fitter.refine_baseline_and_amplitude(pars_gauss_grid, l2_alpha=opts['fitting']['l2_norm'], positive_amplitude=opts['fitting']['force_positive_amplitude'])

print(pars_gauss_ols)



if opts.get('fitting', {}).get('grid_only', False):
    final_pars = pars_gauss_ols

    if opts['fitting'].get('divisive_normalisation', False):
        raise NotImplementedError('Cannot fit DN with only grid!')
else:

    if opts['fitting'].get('divisive_normalisation', False):

        pars = {'x':'centerx0', 'y':'centery0', 'sd':'sigmamajor', 'rf_amplitude':'beta', 'bold_baseline':'bold_baseline',
                'srf_amplitude':'srf_amplitude', 'srf_size':'srf_size', 'neural_baseline':'neural_baseline', 'surround_baseline':'surround_baseline'}

        pars_dn_init = pars_gauss_ols.copy()

        # NB: pd.DataFrame.rename returns a new frame and is NOT in-place
        # by default — the previous code dropped the rename silently
        # and downstream _get_parameters crashed with
        # "KeyError: ['rf_amplitude', 'bold_baseline'] not in index".
        pars_dn_init = pars_dn_init.rename(
            columns={'baseline': 'bold_baseline', 'amplitude': 'rf_amplitude'})
        pars_dn_init['srf_amplitude'] = 0.01
        pars_dn_init['srf_size'] = 2.5
        pars_dn_init['neural_baseline'] = 1.0
        pars_dn_init['surround_baseline'] = 1.0

        from braincoder.models import DivisiveNormalizationGaussianPRF2DWithHRF
        model_dn = DivisiveNormalizationGaussianPRF2DWithHRF(data=data,
                                                    paradigm=paradigm,
                                                    hrf_model=hrf_model,
                                                    grid_coordinates=grid_coordinates,
                                                    flexible_hrf_parameters=False)


        par_fitter_dn = ParameterFitter(model=model_dn, data=data, paradigm=paradigm)
        # Without HRF
        pars_dn = par_fitter_dn.fit(init_pars=pars_dn_init, max_n_iterations=n_gd_iterations,
                                     noise_model=args.noise_model, r2_atol=args.r2_atol)
        final_pars = pars_dn.copy()

    else:
        pars_gauss_gd = par_fitter.fit(init_pars=pars_gauss_ols, max_n_iterations=n_gd_iterations,
                                        noise_model=args.noise_model, r2_atol=args.r2_atol)
        final_pars = pars_gauss_gd

# Route the R² / prediction computation through the DN model+fitter
# when DN is active — final_pars has the DN column names
# (bold_baseline, rf_amplitude, srf_*, neural_baseline, ...) which
# the standard Gauss model can't index. Previously the script always
# used model_gauss/par_fitter, so DN fits ran for 30-60 min on GPU
# and then crashed in the post-fit R² step.
if opts.get('fitting', {}).get('divisive_normalisation', False):
    r2_gauss_gd = par_fitter_dn.get_rsq(final_pars)
    pred = model_dn.predict(parameters=final_pars)
else:
    r2_gauss_gd = par_fitter.get_rsq(final_pars)
    pred = model_gauss.predict(parameters=final_pars)

fit_seconds = time.time() - fit_t0
print(f'INTERNAL_FIT_TIME: {fit_seconds:.2f} seconds')

def save_as_nifti(data, masker, output_dir, filename):
    """Save array-like data to a NIfTI image. Forces float32 + slope=1/inter=0
    so binary masks (uint8) do not quantize the saved parameter values."""
    os.makedirs(output_dir, exist_ok=True)
    img = masker.inverse_transform(data)
    img.set_data_dtype(np.float32)
    img.header.set_slope_inter(slope=1, inter=0)
    img.to_filename(op.join(output_dir, filename))


def save_final_results(results, masker, output_dir):
    """Save fitted parameters to NIfTI files."""
    final_res = {}

    for source_par, target_par in pars.items():
        final_res[target_par] = results[source_par]

    for attr_name, attr_data in final_res.items():
        fn = f'sub-{subject_id}_ses-{session}_task-prf_{attr_name}.nii.gz'
        save_as_nifti(attr_data, masker, output_dir, fn)

if (args.output_dir):
    output_dir = os.path.join(args.output_dir[0], f"sub-{subject_id}/ses-{session}/")
else:
    output_dir = os.path.join(args.bids_dir, f"derivatives/prfanalyze-braincoder/sub-{subject_id}/ses-{session}/")

save_final_results(final_pars, masker, output_dir=output_dir)
save_as_nifti(pred, masker=masker, output_dir=output_dir, filename=f'sub-{subject_id}_ses-{session}_task-prf_modelpred.nii.gz')
save_as_nifti(r2_gauss_gd, masker, output_dir=output_dir, filename=f'sub-{subject_id}_ses-{session}_task-prf_r2.nii.gz')

# --- save the GD convergence trajectory --------------------------------
if args.save_cost_history:
    history = getattr(par_fitter, 'r2_history_', None)
    if opts['fitting'].get('divisive_normalisation', False):
        history_dn = getattr(par_fitter_dn, 'r2_history_', None)
    else:
        history_dn = None
    history_path = op.join(
        output_dir,
        f'sub-{subject_id}_ses-{session}_task-prf_r2history.npz')
    os.makedirs(output_dir, exist_ok=True)
    np.savez(
        history_path,
        gauss_gd=np.asarray(history) if history is not None else np.array([]),
        dn_gd=np.asarray(history_dn) if history_dn is not None else np.array([]),
        noise_model=args.noise_model,
        max_n_iterations=n_gd_iterations,
        r2_atol=args.r2_atol,
    )
    print(f'WROTE_HISTORY: {history_path}  '
          f'(gauss_gd_len={0 if history is None else len(history)}, '
          f'dn_gd_len={0 if history_dn is None else len(history_dn)})')