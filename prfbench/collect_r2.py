"""Aggregate per-cell R² NIfTIs into a summary TSV + voxelwise parquet.

Every fit (braincoder or competing) writes ``..._r2.nii.gz`` into its
BIDS derivative folder. This module walks those folders, summarizes the
R² distribution per cell, and pivots a voxelwise table that downstream
scatter / violin figures consume.

Where to run:

- On the cluster, where the NIfTIs live on /shares/zne.uzh/gdehol/ds-prfsynth/BIDS.
- Outputs go to notes/data/{r2_summary.tsv, r2_voxelwise.parquet}.
- The TSV is tiny (~few KB); rsync both back for local plotting.

Usage:

    python -m prfbench.collect_r2 --bids-folder /shares/zne.uzh/gdehol/ds-prfsynth/BIDS
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd
import nibabel as nib

# ---- derivative folder → (package, fit axes) ---------------------------

# braincoder folders are named:
#   prfanalyze-braincoder.<variant>.<hardware>.<backend>[.n<N_ITER>].seed<SEED>
# competing packages:
#   prfanalyze-{afni,aprf,popeye,vista}
_BRAINCODER_RE = re.compile(
    r'^prfanalyze-braincoder'
    r'\.(?P<variant>grid|full|hrf|dn)'
    r'\.(?P<hardware>cpu|gpu|a100|h100|h200|l4|v100)'
    r'\.(?P<backend>tensorflow|jax|torch)'
    r'(?:\.n(?P<n_iter>\d+))?'
    r'\.seed(?P<seed>\d+)$'
)

_OTHER_PACKAGES = {
    'prfanalyze-afni':    'afni',
    'prfanalyze-aprf':    'aprf',
    'prfanalyze-popeye':  'popeye',
    'prfanalyze-vista':   'mrvista',
}


def parse_derivative_dir(name: str) -> dict | None:
    """Extract (package, hardware, backend, variant, n_iter, seed) from
    a BIDS-app derivative folder name. Returns None if it's not one
    of ours."""
    m = _BRAINCODER_RE.match(name)
    if m:
        d = m.groupdict()
        return {
            'package':  'braincoder',
            'variant':  d['variant'],
            'hardware': d['hardware'],
            'backend':  d['backend'],
            'n_iter':   int(d['n_iter']) if d['n_iter'] else None,
            'seed':     int(d['seed']),
        }
    if name in _OTHER_PACKAGES:
        return {
            'package':  _OTHER_PACKAGES[name],
            'variant':  'default',
            'hardware': 'cpu',          # all the other BIDS apps are CPU
            'backend':  'native',
            'n_iter':   None,
            'seed':     0,              # no per-seed runs for competing pkgs
        }
    return None


# ---- r2 file resolution (filename varies between packages) -------------

def _r2_path(deriv_dir: Path, package: str, dataset: str) -> Path | None:
    """Return the r2.nii.gz for this (dataset, package), or None if absent."""
    base = deriv_dir / f'sub-{dataset}' / 'ses-1'
    if not base.is_dir():
        return None

    # Braincoder uses sub-<dataset>_ses-1_task-prf_r2.nii.gz.
    # Competing packages embed acq-normal_run-01 in the filename.
    candidates = [
        base / f'sub-{dataset}_ses-1_task-prf_r2.nii.gz',
        base / f'sub-{dataset}_ses-1_task-prf_acq-normal_run-01_r2.nii.gz',
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def _modelpred_path(deriv_dir: Path, dataset: str) -> Path | None:
    """Return the modelpred.nii.gz for this (dataset), or None if absent."""
    base = deriv_dir / f'sub-{dataset}' / 'ses-1'
    if not base.is_dir():
        return None
    candidates = [
        base / f'sub-{dataset}_ses-1_task-prf_modelpred.nii.gz',
        base / f'sub-{dataset}_ses-1_task-prf_acq-normal_run-01_modelpred.nii.gz',
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def _bold_path(bids_folder: Path, dataset: str) -> Path | None:
    """Return the raw BOLD NIfTI for this dataset."""
    p = (bids_folder / f'sub-{dataset}' / 'ses-1' / 'func' /
         f'sub-{dataset}_ses-1_task-prf_acq-normal_run-01_bold.nii.gz')
    return p if p.is_file() else None


def _r2_from_modelpred(modelpred_path: Path, bold_path: Path) -> np.ndarray:
    """Voxelwise R² from prediction and observed BOLD timeseries.

    R² = 1 - SS_res / SS_tot, computed per voxel across time. Returns a
    flat array, same voxel order as the input NIfTIs."""
    pred = np.asarray(nib.load(str(modelpred_path)).get_fdata(), dtype=np.float64)
    bold = np.asarray(nib.load(str(bold_path)).get_fdata(),       dtype=np.float64)

    # Both are (X, Y, Z, T) shape; reshape to (n_voxels, T).
    pred = pred.reshape(-1, pred.shape[-1])
    bold = bold.reshape(-1, bold.shape[-1])
    if pred.shape != bold.shape:
        raise ValueError(f'shape mismatch {pred.shape} vs {bold.shape}')

    resid = bold - pred
    ss_res = (resid ** 2).sum(axis=1)
    bold_mean = bold.mean(axis=1, keepdims=True)
    ss_tot = ((bold - bold_mean) ** 2).sum(axis=1)
    with np.errstate(divide='ignore', invalid='ignore'):
        r2 = 1.0 - ss_res / ss_tot
    r2[~np.isfinite(r2)] = np.nan
    return r2.astype(np.float32)


def _summarize(r2: np.ndarray) -> dict:
    """Reduce a voxelwise R² array to scalar summaries. Filters NaN."""
    arr = np.asarray(r2, dtype=np.float64).ravel()
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {'n_voxels_fit': 0, 'r2_median': np.nan, 'r2_mean': np.nan,
                'r2_q25': np.nan, 'r2_q75': np.nan, 'r2_frac_above_0_5': np.nan}
    q25, med, q75 = np.percentile(arr, [25, 50, 75])
    return {
        'n_voxels_fit':      int(arr.size),
        'r2_median':         float(med),
        'r2_mean':           float(arr.mean()),
        'r2_q25':            float(q25),
        'r2_q75':            float(q75),
        'r2_frac_above_0_5': float((arr > 0.5).mean()),
    }


# ---- main collector ----------------------------------------------------

def collect(bids_folder: Path, datasets: list[str], keep_voxelwise: bool = True
            ) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Walk derivatives, return summary DataFrame and (optional) voxelwise DataFrame.

    `keep_voxelwise=True` returns one row per (package, ..., voxel) — large.
    """
    deriv_root = bids_folder / 'derivatives'
    if not deriv_root.is_dir():
        raise FileNotFoundError(f'No derivatives dir at {deriv_root}')

    summary_rows = []
    voxel_rows = []

    for deriv_dir in sorted(deriv_root.iterdir()):
        if not deriv_dir.is_dir():
            continue
        axes = parse_derivative_dir(deriv_dir.name)
        if axes is None:
            continue

        for dataset in datasets:
            p = _r2_path(deriv_dir, axes['package'], dataset)
            if p is not None:
                r2 = nib.load(str(p)).get_fdata()
                src = str(p)
            else:
                # Compute R² from modelpred.nii.gz + raw BOLD (AFNI / popeye
                # / mrVista don't ship r2.nii.gz themselves).
                mp = _modelpred_path(deriv_dir, dataset)
                bold = _bold_path(bids_folder, dataset)
                if mp is None or bold is None:
                    continue
                try:
                    r2 = _r2_from_modelpred(mp, bold)
                except ValueError as e:
                    print(f'[collect_r2] skip {deriv_dir.name}/{dataset}: {e}')
                    continue
                src = f'computed:{mp.name}'
            row = {**axes, 'dataset': dataset, 'r2_path': src, **_summarize(r2)}
            summary_rows.append(row)

            if keep_voxelwise:
                arr = np.asarray(r2, dtype=np.float32).ravel()
                vox_df = pd.DataFrame({
                    'voxel': np.arange(arr.size, dtype=np.int32),
                    'r2': arr,
                })
                for k, v in axes.items():
                    vox_df[k] = v
                vox_df['dataset'] = dataset
                voxel_rows.append(vox_df)

    summary = pd.DataFrame(summary_rows)
    voxelwise = pd.concat(voxel_rows, ignore_index=True) if voxel_rows else None
    return summary, voxelwise


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        '--bids-folder',
        type=Path,
        default=Path('/shares/zne.uzh/gdehol/ds-prfsynth/BIDS'),
        help='BIDS root containing derivatives/.',
    )
    p.add_argument(
        '--datasets',
        nargs='+',
        default=['smallgrid', 'mediumgrid', 'largegrid', 'vanes2019'],
    )
    p.add_argument(
        '--out-dir',
        type=Path,
        default=repo / 'notes' / 'data',
    )
    p.add_argument(
        '--skip-voxelwise',
        action='store_true',
        help='Only write the per-cell summary TSV; skip the voxelwise parquet.',
    )
    args = p.parse_args()

    print(f'[collect_r2] BIDS={args.bids_folder}  datasets={args.datasets}')
    summary, voxelwise = collect(
        args.bids_folder,
        args.datasets,
        keep_voxelwise=not args.skip_voxelwise,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.out_dir / 'r2_summary.tsv'
    summary.to_csv(summary_path, sep='\t', index=False)
    print(f'  wrote {summary_path}  ({len(summary)} rows)')

    if voxelwise is not None:
        vx_path = args.out_dir / 'r2_voxelwise.parquet'
        voxelwise.to_parquet(vx_path, compression='zstd')
        print(f'  wrote {vx_path}  ({len(voxelwise):,} rows, {voxelwise["package"].nunique()} packages)')


if __name__ == '__main__':
    main()
