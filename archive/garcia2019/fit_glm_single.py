from glmsingle.glmsingle import GLM_single
import argparse
import os
import os.path as op
from nilearn import image
from utils import Subject
from nilearn.glm.first_level import make_first_level_design_matrix
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

def main(subject, bids_folder, smoothed=False):

    derivatives = op.join(bids_folder, 'derivatives')

    sub = Subject(subject, bids_folder=bids_folder)
    runs = sub.get_runs()
    ims = sub.get_preprocessed_bold_images()

    print(ims)

    base_dir = 'glm_stim1.denoise'

    if smoothed:
        base_dir += '.smoothed'
        ims = [image.smooth_img(im, fwhm=5.0) for im in ims]



    brain_masker = sub.get_brain_masker(smoothing_fwhm=5.0 if smoothed else None)

    data = [brain_masker.fit_transform(im).T for im in ims]
    print(data[0], data[0].shape)

    base_dir = op.join(derivatives, base_dir, f'sub-{subject}',
                       'func')

    if not op.exists(base_dir):
        os.makedirs(base_dir)


    onsets = sub.get_fmri_events()

    print(onsets)

    onsets = onsets[~onsets['stim'].isnull()]
    print(onsets)

    import re
    # reg = re.compile(_type>.+)_\d+')
    # onsets['stim'] = onsets['trial_type'].apply(lambda x: x.split('_')[0])

    tr = 2.82694

    n = 189
    frametimes = np.linspace(tr/2., (n - .5)*tr, n)
    onsets['onset'] = ((onsets['onset']+tr/2.) // tr) * tr

    dm = [make_first_level_design_matrix(frametimes, onsets.loc[run], hrf_model='fir', oversampling=100.,
                                         drift_order=0,
                                         drift_model=None).drop('constant', axis=1) for run in runs]

    dm = pd.concat(dm, keys=runs, names=['run']).fillna(0)
    dm.columns = [c.replace('_delay_0', '') for c in dm.columns]
    dm /= dm.max()

    dm = (dm > 1e-1).astype(int)

    for ix in range(10):
        print(dm.iloc[:25, ix])

    print('yoooo')
    print(dm)

    X = [dm.loc[run].values for run in runs]

    # # create a directory for saving GLMsingle outputs
    opt = dict()

    # # set important fields for completeness (but these would be enabled by default)
    opt['wantlibrary'] = 1
    opt['wantglmdenoise'] = 1
    opt['wantfracridge'] = 1

    # # for the purpose of this example we will keep the relevant outputs in memory
    # # and also save them to the disk
    opt['wantfileoutputs'] = [0, 0, 0, 1]

    print(opt)
    # # running python GLMsingle involves creating a GLM_single object
    # # and then running the procedure using the .fit() routine
    glmsingle_obj = GLM_single(opt)

    results_glmsingle = glmsingle_obj.fit(
        X,
        data,
        0.6,
        tr,
        outputdir=base_dir)

    fn_template = op.join(base_dir, 'sub-{subject}_task-task_space-T1w_desc-{desc}.nii.gz')

    betas = results_glmsingle['typed']['betasmd']

    print(f'Shape betas: {betas.shape}')
    betas = brain_masker.inverse_transform(betas.squeeze().T)
    betas1 = image.index_img(betas, slice(None, None, 2))
    betas1.to_filename(fn_template.format(subject=subject, desc='stim1_pe'))

    betas2 = image.index_img(betas, slice(1, None, 2))
    betas2.to_filename(fn_template.format(subject=subject, desc='stim2_pe'))
    
    r2 = results_glmsingle['typed']['R2']
    r2 = brain_masker.inverse_transform(r2.squeeze().T)
    r2.to_filename(fn_template.format(subject=subject, desc='r2_par'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('subject', default=None)
    parser.add_argument('--bids_folder', default='/data/ds-numrisk')
    parser.add_argument('--smoothed', action='store_true')
    args = parser.parse_args()

    main(args.subject, 
         bids_folder=args.bids_folder, smoothed=args.smoothed,)
