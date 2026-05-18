"""Aggregate per-cell PRF parameter estimates against synthetic ground truth.

For each synthetic dataset (`smallgrid`, `mediumgrid`, `largegrid`) we have
voxel-level ground truth from prfsynth:

    BIDS/derivatives/prfsynth/sub-<ds>/ses-1/sub-<ds>_ses-1_task-prf_acq-normal_run-01_bold.json

Each fitter writes per-parameter NIfTIs into its derivative folder:

    BIDS/derivatives/prfanalyze-<pkg>/sub-<ds>/ses-1/sub-<ds>_*_<par>.nii.gz

This module joins them voxel-wise and produces a long-format parquet:

    voxel, parameter ∈ {centerx0, centery0, sigmamajor},
    true, estimated,
    dataset, package, hardware, backend, variant, n_iter, seed

vanes2019 has no ground truth (real data), so it's excluded from this output.

Usage:

    python -m prfbench.collect_params --bids-folder /shares/zne.uzh/gdehol/ds-prfsynth/BIDS
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import nibabel as nib

from .collect_r2 import parse_derivative_dir

# Synthetic datasets — the ones with ground truth.
SYNTH_DATASETS = ['smallgrid', 'mediumgrid', 'largegrid']

# Parameters we care about. Names match the BIDS-prfsynth convention.
PARAMS = ['centerx0', 'centery0', 'sigmamajor']


def load_ground_truth(bids_folder: Path, dataset: str) -> pd.DataFrame:
    """Read the prfsynth JSON for one synthetic dataset.

    Returns a DataFrame with N rows (voxels) and columns centerx0,
    centery0, sigmamajor — lowercased to match downstream NIfTI names.
    """
    fn = (bids_folder / 'derivatives' / 'prfsynth' / f'sub-{dataset}' / 'ses-1'
          / f'sub-{dataset}_ses-1_task-prf_acq-normal_run-01_bold.json')
    if not fn.is_file():
        raise FileNotFoundError(f'ground truth missing: {fn}')

    df = pd.read_json(fn)

    # prfsynth nests the RF parameters (Centerx0, Centery0, sigmaMajor, ...)
    # under an `RF` column. Flatten that out.
    rf = df['RF'].apply(pd.Series)
    rf.columns = [c.lower() for c in rf.columns]

    # The remaining columns are global (TR, signalpercentage, ...) and not
    # useful per-voxel; drop them.
    out = rf[[c for c in PARAMS if c in rf.columns]].copy()
    out.index.name = 'voxel'
    return out.reset_index()


def _estimate_path(deriv_dir: Path, dataset: str, par: str) -> Path | None:
    """Locate a per-parameter NIfTI for one (package_dir, dataset)."""
    base = deriv_dir / f'sub-{dataset}' / 'ses-1'
    if not base.is_dir():
        return None
    candidates = [
        base / f'sub-{dataset}_ses-1_task-prf_{par}.nii.gz',                          # braincoder
        base / f'sub-{dataset}_ses-1_task-prf_acq-normal_run-01_{par}.nii.gz',        # other pkgs
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def collect(bids_folder: Path, datasets: list[str] = SYNTH_DATASETS) -> pd.DataFrame:
    """Walk all derivatives, return one long DataFrame of (true, estimated)."""
    deriv_root = bids_folder / 'derivatives'
    if not deriv_root.is_dir():
        raise FileNotFoundError(f'No derivatives dir at {deriv_root}')

    blocks = []
    for dataset in datasets:
        try:
            gt = load_ground_truth(bids_folder, dataset)
        except FileNotFoundError as e:
            print(f'[collect_params] skipping {dataset}: {e}')
            continue
        gt_long = gt.melt(id_vars='voxel', value_vars=PARAMS,
                          var_name='parameter', value_name='true')

        for deriv_dir in sorted(deriv_root.iterdir()):
            axes = parse_derivative_dir(deriv_dir.name)
            if axes is None:
                continue

            # Load each parameter's estimate (if present) into a flat array.
            est_arrays = {}
            for par in PARAMS:
                p = _estimate_path(deriv_dir, dataset, par)
                if p is None:
                    continue
                est_arrays[par] = np.asarray(nib.load(str(p)).get_fdata(),
                                              dtype=np.float32).ravel()
            if not est_arrays:
                continue

            n_vox = len(gt)
            for par, arr in est_arrays.items():
                if arr.size != n_vox:
                    print(f'[collect_params] {deriv_dir.name}/{dataset}/{par}: '
                          f'size {arr.size} != ground truth {n_vox}, skipping')
                    continue
                est_df = pd.DataFrame({
                    'voxel':     np.arange(n_vox, dtype=np.int32),
                    'parameter': par,
                    'estimated': arr,
                })
                row = est_df.merge(gt_long, on=['voxel', 'parameter'], how='inner')
                for k, v in axes.items():
                    row[k] = v
                row['dataset'] = dataset
                blocks.append(row)

    if not blocks:
        raise RuntimeError('No (package × dataset × parameter) combos found.')

    out = pd.concat(blocks, ignore_index=True)
    return out


def summarize(long_df: pd.DataFrame) -> pd.DataFrame:
    """Per-(package, hardware, backend, variant, seed, dataset, parameter)
    correlation + bias + RMSE between estimated and true."""
    keys = ['dataset', 'package', 'hardware', 'backend', 'variant', 'n_iter',
            'seed', 'parameter']

    def _agg(g: pd.DataFrame) -> pd.Series:
        t = g['true'].to_numpy()
        e = g['estimated'].to_numpy()
        mask = np.isfinite(t) & np.isfinite(e)
        if mask.sum() < 10:
            return pd.Series({'r': np.nan, 'rmse': np.nan, 'bias': np.nan, 'n': mask.sum()})
        t, e = t[mask], e[mask]
        r = np.corrcoef(t, e)[0, 1] if t.std() > 0 and e.std() > 0 else np.nan
        rmse = float(np.sqrt(np.mean((e - t) ** 2)))
        bias = float(np.mean(e - t))
        return pd.Series({'r': r, 'rmse': rmse, 'bias': bias, 'n': int(mask.sum())})

    return long_df.groupby(keys, dropna=False).apply(_agg).reset_index()


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bids-folder',
                   type=Path,
                   default=Path('/shares/zne.uzh/gdehol/ds-prfsynth/BIDS'))
    p.add_argument('--datasets', nargs='+', default=SYNTH_DATASETS)
    p.add_argument('--out-dir', type=Path, default=repo / 'notes' / 'data')
    args = p.parse_args()

    print(f'[collect_params] BIDS={args.bids_folder}  datasets={args.datasets}')
    long_df = collect(args.bids_folder, args.datasets)
    summary = summarize(long_df)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    long_path = args.out_dir / 'params_recovery.parquet'
    long_df.to_parquet(long_path, compression='zstd')
    print(f'  wrote {long_path}  ({len(long_df):,} rows)')

    sum_path = args.out_dir / 'params_recovery_summary.tsv'
    summary.to_csv(sum_path, sep='\t', index=False)
    print(f'  wrote {sum_path}  ({len(summary)} rows)')


if __name__ == '__main__':
    main()
