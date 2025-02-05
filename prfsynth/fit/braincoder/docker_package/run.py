import os
import os.path as op
import argparse
import braincoder
import json
from nilearn import image
from nilearn import maskers
import pandas as pd
import numpy as np
import yaml

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
# parser.add_argument('--debug', help='Whether to start the app in debug mode. Interactive terminal will be started.', action="store_true")
parser.add_argument('-v', '--version', action='version',
                    version='BIDS-App example version {}'.format(__version__))

args = parser.parse_args()
print(args)

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

mask = image.new_img_like(im, np.ones(im.shape[:-1]))

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
<<<<<<< Updated upstream

=======
>>>>>>> Stashed changes
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


if opts['fitting']['fit_hrf']:
    pars_gauss_grid = par_fitter.fit_grid(x, y, sd, baseline, amplitude, hrf_delay, hrf_dispersion, use_correlation_cost=True)
else:
    pars_gauss_grid = par_fitter.fit_grid(x, y, sd, baseline, amplitude, use_correlation_cost=True)

print(pars_gauss_grid)

# # And refine the baseline and amplitude parameters using OLS
pars_gauss_ols = par_fitter.refine_baseline_and_amplitude(pars_gauss_grid, l2_alpha=1.0, n_iterations=1)

print(pars_gauss_ols)



pars_gauss_gd = par_fitter.fit(init_pars=pars_gauss_ols, max_n_iterations=opts['fitting']['n_gd_iterations'])

print(pars_gauss_gd)
r2_gauss_gd = par_fitter.get_rsq(pars_gauss_gd)
pred = model_gauss.predict(parameters=pars_gauss_gd)


def save_as_nifti(data, masker, output_dir, filename):
    """Save array-like data to a NIfTI image."""
    os.makedirs(output_dir, exist_ok=True)
    img = masker.inverse_transform(data)
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

save_final_results(pars_gauss_gd, masker, output_dir=output_dir)
save_as_nifti(pred, masker=masker, output_dir=output_dir, filename=f'sub-{subject_id}_ses-{session}_task-prf_modelpred.nii.gz')
save_as_nifti(r2_gauss_gd, masker, output_dir=output_dir, filename=f'sub-{subject_id}_ses-{session}_task-prf_r2.nii.gz')