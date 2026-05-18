import os.path as op
import glob
import pandas as pd
import re
import numpy as np
from nilearn.input_data import NiftiMasker

class Subject():

    def __init__(self, subject_id, bids_folder='/data/ds-numrisk'):
        self.subject_id = subject_id
        self.bids_folder = bids_folder

    def get_event_file(self, run):
        return op.join(self.bids_folder, f'sub-{self.subject_id}', 'func', f'sub-{self.subject_id}_task-numrisk_run-{run}_events.tsv')

    def get_event_files(self):
        return [self.get_event_file(run) for run in self.get_runs()]

    def get_preprocessed_bold_image(self, run):
        search_pattern = op.join(self.bids_folder, 'derivatives', 'fmriprep',
                        f'sub-{self.subject_id}', 'func', f'sub-{self.subject_id}_task-numrisk_*_run-{run}_space-T1w_desc-preproc_bold.nii.gz')
        matching_files = glob.glob(search_pattern)
        
        if len(matching_files) != 1:
            raise FileNotFoundError(f"No preprocessed BOLD file found for sub-{self.subject_id}, run-{run}:\n \
                                    {search_pattern}\n")
        
        # If multiple matches, return the first one (assuming there's only one valid file per run)
        return matching_files[0]

    def get_preprocessed_bold_images(self):

        return [self.get_preprocessed_bold_image(run) for run in self.get_runs()]

    def get_runs(self):
        if self.subject_id == '1':
            return range(2, 7)
        else:
            return range(1, 7)

    def get_fmri_events(self):
        events = pd.concat([pd.read_csv(f, sep='\t') for f in self.get_event_files()],
                         keys=self.get_runs(), names=['run'])

        stim_re = re.compile('stim(?P<stim>1|2)-(?P<n>[0-9]+)')
        events['stim'] = events['trial_type'].apply(lambda x: stim_re.match(x).group('stim') if stim_re.match(x) else np.nan)
        events['n'] = events['trial_type'].apply(lambda x: stim_re.match(x).group('n') if stim_re.match(x) else np.nan)

        return events 

    def get_brain_mask(self, epi_space=True):

        target_folder = op.join(self.bids_folder, 'derivatives', 'fmriprep', f'sub-{self.subject_id}')
        
        if epi_space:
            target_folder = op.join(target_folder, 'func')

            template_fn =  op.join(target_folder, f'sub-{self.subject_id}_task-numrisk_acq-*_run-*_space-T1w_desc-brain_mask.nii.gz')

            matching_files = sorted(glob.glob(template_fn))

            if len(matching_files) == 0:
                raise FileNotFoundError(f"No EPI space brain mask found for sub-{self.subject_id}:\n \
                                        {template_fn}\n")
            else:
                print(f'Using brain mask: {matching_files[0]}')
                return matching_files[0]
        else:
            raise not NotImplementedError("Only EPI space brain masks are currently supported")

    def get_brain_masker(self, epi_space=True, smoothing_fwhm=None):
        return NiftiMasker(mask_img=self.get_brain_mask(epi_space), smoothing_fwhm=smoothing_fwhm)