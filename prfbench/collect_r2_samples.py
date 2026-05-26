"""Per-voxel R² samples for swarm/strip plots.

`collect_r2.py` ships only summary stats (median, IQR) per cell — fine
for line plots but loses the shape of the per-voxel distribution.
This module reads each cell's ``*_r2.nii.gz`` and writes a long-format
TSV with one row per (cell, voxel-sample). Voxels are uniformly
subsampled (default 500 per cell) to keep the TSV small for local
plotting; the seed is fixed so re-runs produce identical samples.

Usage::

    python -m prfbench.collect_r2_samples            # default 500 voxels/cell
    python -m prfbench.collect_r2_samples --n 1000
"""
from __future__ import annotations

import argparse
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd

from prfbench.collect_r2 import _r2_from_modelpred


def _bold_path(bids_folder: Path, dataset: str) -> Path | None:
    p = (bids_folder / f'sub-{dataset}' / 'ses-1' / 'func' /
         f'sub-{dataset}_ses-1_task-prf_acq-normal_run-01_bold.nii.gz')
    return p if p.is_file() else None


def _resolve_r2_array(row: pd.Series, bids_folder: Path) -> np.ndarray | None:
    """Either load the saved r2.nii.gz, or compute R² from modelpred + BOLD
    for packages that don't write r2 directly (popeye, afni, mrvista)."""
    path = row['r2_path']
    if not isinstance(path, str) or not path:
        return None

    if path.startswith('computed:'):
        # path looks like "computed:sub-<ds>_ses-1_task-prf*_modelpred.nii.gz".
        # Find the actual modelpred file by searching the derivative dir
        # that the row's other fields imply.
        mp_name = path[len('computed:'):]
        # Walk: BIDS/derivatives/prfanalyze-<pkg>.<tag>/sub-<ds>/ses-1/<mp_name>
        # The exact derivative-dir tag isn't stored in r2_summary, so we
        # fall back to globbing for any derivative dir that owns this mp.
        deriv_root = bids_folder / 'derivatives'
        for cand in deriv_root.glob(
                f'prfanalyze-{row["package"]}*/sub-{row["dataset"]}/ses-1/{mp_name}'):
            mp = cand
            break
        else:
            return None
        bold = _bold_path(bids_folder, row['dataset'])
        if bold is None:
            return None
        try:
            return _r2_from_modelpred(mp, bold)
        except Exception as e:
            print(f'  skip computed {mp}: {e}')
            return None

    # Direct r2.nii.gz path.
    p = Path(path)
    if not p.is_file():
        return None
    try:
        return np.asanyarray(nib.load(str(p)).dataobj).ravel().astype(np.float32)
    except Exception as e:
        print(f'  skip {p}: {e}')
        return None


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--summary', type=Path,
                   default=repo / 'notes' / 'data' / 'r2_summary.tsv')
    p.add_argument('--bids-folder', type=Path,
                   default=Path('/shares/zne.uzh/gdehol/ds-prfsynth/BIDS'))
    p.add_argument('--out', type=Path,
                   default=repo / 'notes' / 'data' / 'r2_samples.tsv')
    p.add_argument('--n', type=int, default=500,
                   help='Voxels per cell (uniformly subsampled).')
    p.add_argument('--seed', type=int, default=0)
    args = p.parse_args()

    summary = pd.read_csv(args.summary, sep='\t')
    rng = np.random.default_rng(args.seed)
    rows = []
    n_skip = 0

    for _, row in summary.iterrows():
        arr = _resolve_r2_array(row, args.bids_folder)
        if arr is None:
            n_skip += 1
            continue
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            n_skip += 1
            continue

        n_take = min(args.n, arr.size)
        sample_ix = rng.choice(arr.size, size=n_take, replace=False)
        for r2_val in arr[sample_ix]:
            rows.append({
                'package':  row['package'],
                'variant':  row['variant'],
                'hardware': row['hardware'],
                'backend':  row['backend'],
                'seed':     row['seed'],
                'dataset':  row['dataset'],
                'r2':       float(r2_val),
            })

    print(f'  skipped {n_skip} rows that lacked a resolvable r2 source')

    out = pd.DataFrame(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, sep='\t', index=False)
    print(f'wrote {args.out}  ({len(out)} rows, {out.dataset.nunique()} datasets)')


if __name__ == '__main__':
    main()
