import argparse
import os
import os.path as op
import nibabel as nib
import numpy as np
import json
import pandas as pd
from braincoder.utils.data import load_vanes2019

def save_nifti(data, affine, hdr, filename):
    """Save NIfTI image."""
    nib.Nifti1Image(data, affine, header=hdr).to_filename(filename)
    print(f"Saved: {filename}")

def main(bids_folder='/data/ds-prfsynth'):
    print("Loading data..")
    data = load_vanes2019()
    
    # Create the stimulus file (shared across all datasets)
    # Go from (T, X, Y) to (Y, X, 1, T)
    stimulus = np.transpose(data['stimulus'], (2, 1, 0))[::-1, :, np.newaxis, :]  # Shape (Y, X, 1, T) (Flip Y)

    stimulus_fn = op.join(bids_folder, 'BIDS', 'stimuli', 'sub-vanes2019_ses-1_task-prf_apertures.nii.gz')
    hdr = nib.Nifti1Header()
    hdr.set_data_dtype(np.float32)
    hdr.set_xyzt_units('mm', 'sec')
    hdr['pixdim'][1:4] = [0.2, 0.2, 0.2]
    hdr['pixdim'][4] = 1.5
    save_nifti(stimulus, affine=None, hdr=hdr, filename=stimulus_fn)
    
    # Define data directories
    base_dir_vanes2019 = op.join(bids_folder, 'BIDS', 'sub-vanes2019', 'ses-1', 'func')
    base_dir_split = op.join(bids_folder, 'BIDS', 'sub-vanes2019split', 'ses-1', 'func')
    os.makedirs(base_dir_vanes2019, exist_ok=True)
    os.makedirs(base_dir_split, exist_ok=True)
    
    # Prepare time series data
    ts_data = np.asarray(data['ts'].T)[:, np.newaxis, np.newaxis, :]
    affine = np.eye(4)
    affine[:3, :3] *= 2.0  # Voxel size of 2mm isotropic
    hdr['dim'][1:5] = ts_data.shape
    hdr['pixdim'][1:5] = [2.0, 2.0, 2.0, 1.5]
    
    # Save full dataset (sub-vanes2019)
    full_data_fn = op.join(base_dir_vanes2019, 'sub-vanes2019_ses-1_task-prf_acq-normal_run-01_bold.nii.gz')
    save_nifti(ts_data, affine, hdr, full_data_fn)
    
    
    # Create JSON metadata
    json_data = {"RepetitionTime": data['tr'], "SliceTiming": [0], "TaskName": "prf"}
    json_fn = op.join(base_dir_vanes2019, 'sub-vanes2019_ses-1_task-prf_acq-normal_run-01_bold.json')
    with open(json_fn, "w") as json_file:
        json.dump(json_data, json_file, indent=4)
    print(f"Saved JSON: {json_fn}")
    
    
    # Create events file
    events = pd.DataFrame({
        'onset': np.arange(0, data['ts'].shape[1] * data['tr'], data['tr']),
        'duration': data['tr'],
        'stim_file': 'sub-vanes2019_ses-1_task-prf_apertures.nii.gz'
    })
    events_fn = op.join(base_dir_vanes2019, 'sub-vanes2019_ses-1_task-prf_events.tsv')
    events.to_csv(events_fn, sep='\t', index=False)
    print(f"Saved events: {events_fn}")
    

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description=__doc__)
    argparser.add_argument('-b', '--bids_folder', type=str, default='/data/ds-prfsynth', help='BIDS folder where the data will be saved')
    args = argparser.parse_args()
    main(args.bids_folder)
