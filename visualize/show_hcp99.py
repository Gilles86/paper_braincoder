import cortex
import numpy as np
import os
from nilearn import image
from utils import get_alpha_vertex




# Define subject
subject = "hcp_999999"
r2_thr = 0.5

# Ensure the subject exists in the Pycortex database
if subject not in cortex.db.subjects:
    raise ValueError(f"Subject '{subject}' is not in the Pycortex database!")

# Use an identity transform if 'raw' transform is missing
xfm_name = "identity"
# xfm_dir = cortex.db.get_xfm_dir(subject, xfm_name)

# if not os.path.exists(xfm_dir):
#     print(f"Creating identity transform for subject '{subject}'...")
#     cortex.xfm.make_identity(subject, xfm_name, "fullhead")

# Create a dummy volume (all zeros) with the identity transform
volume_data = np.zeros(cortex.db.get_anat(subject).shape)
volume = cortex.Volume(volume_data, subject, xfm_name)

ds = {}

key_pairs = {'r2':'r2', 'x':'centerx0', 'y':'centery0', 'sd':'sigmamajor', 'amplitude':'beta', 'baseline':'baseline',
             'theta':None, 'ecc':None}

vmin_vmax = {'r2':(0.0, 1.0), 'x':(-10.0, 10.0), 'y':(-5.5, 5.5), 'sd':(1.0, 15.0),
              'amplitude':(None, None), 'baseline':(None, None),
              'theta':(0.0, np.pi), 'ecc':(0.0, np.sqrt(5.5**2+10**2)), 'hrf_delay':(None, None), 'hrf_dispersion':(None, None)}

cmaps = {'r2':'hot', 'x':'RdBu_r', 'y':'RdBu_r', 'sd':'viridis', 'amplitude':'coolwarm', 'baseline':'viridis',
             'theta':'twilight', 'ecc':'viridis', 'hrf_delay':'viridis', 'hrf_dispersion':'viridis'}

model = 'prfanalyze-braincoder.hrf.A100'
model = 'prfanalyze-braincoder.A100'
model = 'prfanalyze-braincoder.dn.A100'

if model == 'prfanalyze-braincoder.hrf.A100':
    key_pairs['hrf_delay'] = 'hrf_delay'
    key_pairs['hrf_dispersion'] = 'hrf_dispersion'

if model == 'prfanalyze-braincoder.dn.A100':
    key_pars_ = {'neural_baseline':'neural_baseline', 'surround_baseline':'surround_baseline', 'srf_size':'srf_size', 'srf_amplitude':'srf_amplitude'}
    key_pars_ = {'neural_baseline':'neural_baseline', 'surround_baseline':'surround_baseline', 'srf_size':'srf_size', 'srf_amplitude':'srf_amplitude'}
    vmin_vmax_ = {'neural_baseline':(None, None), 'surround_baseline':(None, None), 'srf_size':(0.0, 10.0), 'srf_amplitude':(None, None)}
    cmaps_ = {'neural_baseline':'viridis', 'surround_baseline':'viridis', 'srf_size':'viridis', 'srf_amplitude':'coolwarm'}

    key_pairs.update(key_pars_)
    vmin_vmax.update(vmin_vmax_)
    cmaps.update(cmaps_)

    r2_thr = 0.1


r2 = image.load_img(f'/data/ds-prfsynth/BIDS/derivatives/{model}/sub-vanes2019/ses-1/sub-vanes2019_ses-1_task-prf_r2.nii.gz').get_fdata().ravel()
x = image.load_img(f'/data/ds-prfsynth/BIDS/derivatives/{model}/sub-vanes2019/ses-1/sub-vanes2019_ses-1_task-prf_centerx0.nii.gz').get_fdata().ravel()
y = image.load_img(f'/data/ds-prfsynth/BIDS/derivatives/{model}/sub-vanes2019/ses-1/sub-vanes2019_ses-1_task-prf_centery0.nii.gz').get_fdata().ravel()

alpha = r2 > r2_thr

# Load the fitted parameters
for key, value in key_pairs.items():

    if key == 'theta':
        par = np.abs(np.arctan2(x, -y))
    elif key == 'ecc':
        par = np.sqrt(x**2 + y**2)
    elif key == 'r2':
        par = r2
    else:
        par = image.load_img(f'/data/ds-prfsynth/BIDS/derivatives/{model}/sub-vanes2019/ses-1/sub-vanes2019_ses-1_task-prf_{value}.nii.gz').get_fdata().ravel()

    ds[key] = get_alpha_vertex(par, alpha, cmap=cmaps[key], vmin=vmin_vmax[key][0], vmax=vmin_vmax[key][1], subject=subject)

# Show in browser
cortex.webgl.show(ds)
