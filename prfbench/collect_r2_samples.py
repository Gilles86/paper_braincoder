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


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--summary', type=Path,
                   default=repo / 'notes' / 'data' / 'r2_summary.tsv')
    p.add_argument('--out', type=Path,
                   default=repo / 'notes' / 'data' / 'r2_samples.tsv')
    p.add_argument('--n', type=int, default=500,
                   help='Voxels per cell (uniformly subsampled).')
    p.add_argument('--seed', type=int, default=0)
    args = p.parse_args()

    summary = pd.read_csv(args.summary, sep='\t')
    rng = np.random.default_rng(args.seed)
    rows = []

    for _, row in summary.iterrows():
        path = row['r2_path']
        if not path or pd.isna(path):
            continue
        # Some collect_r2 rows write "computed:<basename>" when the r2
        # was computed from modelpred; resolve to a real path by
        # finding the BIDS prefix.
        if isinstance(path, str) and path.startswith('computed:'):
            # the actual r2 was written next to the modelpred — for
            # this sampler we want the saved r2.nii.gz. Skip these
            # rows; collect_r2 already wrote summary stats for them.
            continue
        if not Path(path).is_file():
            continue

        try:
            arr = np.asanyarray(nib.load(path).dataobj).ravel().astype(np.float32)
        except Exception as e:
            print(f'  skip {path}: {e}')
            continue

        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
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

    out = pd.DataFrame(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, sep='\t', index=False)
    print(f'wrote {args.out}  ({len(out)} rows, {out.dataset.nunique()} datasets)')


if __name__ == '__main__':
    main()
