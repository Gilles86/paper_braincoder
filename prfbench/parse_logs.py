"""Aggregate per-cell runtime TSVs into a single tidy DataFrame.

Each cluster fit writes one tiny TSV to ``notes/data/runtime/`` with
columns:

    package, hardware, backend, variant, dataset, n_iter, seed,
    wall_seconds, internal_fit_seconds, job_id, hostname, timestamp

This module walks that directory and concatenates everything into one
``notes/data/runtime.tsv`` for downstream plotting.

Static metadata about each dataset (n voxels, T) is joined in here too,
since the per-cell TSV doesn't carry it.

Usage:

    python -m prfbench.parse_logs                    # default paths
    python -m prfbench.parse_logs --rerun
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

# Dataset metadata. Populated from a one-time inspection of
# /data/ds-prfsynth/BIDS/sub-<id>/ses-1/func/*_bold.nii.gz.
DATASET_META = {
    'smallgrid':  {'n_voxels':    490, 'n_timepoints': 200, 'kind': 'synthetic'},
    'mediumgrid': {'n_voxels':  4_900, 'n_timepoints': 200, 'kind': 'synthetic'},
    'largegrid':  {'n_voxels': 49_000, 'n_timepoints': 200, 'kind': 'synthetic'},
    'vanes2019':  {'n_voxels': 118_584, 'n_timepoints': 120, 'kind': 'real'},
}

# Expected column order for the aggregated TSV.
COLUMNS = [
    'package', 'hardware', 'backend', 'variant', 'dataset',
    'n_voxels', 'n_timepoints', 'kind',
    'n_iter', 'seed',
    'wall_seconds', 'internal_fit_seconds',
    'job_id', 'hostname', 'timestamp',
]


def parse(runtime_dir: Path) -> pd.DataFrame:
    """Read every ``*.tsv`` under runtime_dir; return a single DataFrame."""
    if not runtime_dir.is_dir():
        raise FileNotFoundError(
            f'No runtime directory at {runtime_dir}. '
            f'Run the cluster jobs first or rsync notes/data/runtime/.'
        )

    rows = []
    for tsv in sorted(runtime_dir.glob('*.tsv')):
        df = pd.read_csv(tsv, sep='\t')
        if df.empty:
            continue
        rows.append(df)

    if not rows:
        raise RuntimeError(f'No non-empty *.tsv files in {runtime_dir}.')

    df = pd.concat(rows, ignore_index=True)

    # Pre-2026-05 runs were written by the old, single-axis dispatcher;
    # they lack the `backend` column. Default missing values to tensorflow.
    if 'backend' not in df.columns:
        df['backend'] = 'tensorflow'
    df['backend'] = df['backend'].fillna('tensorflow')

    # The original `cpu` hardware label was always 32-core (-c 32 in the
    # old submit script). Rename so it merges with the new cpu32 sweep
    # rows on the same line in fig_speed.
    df.loc[df['hardware'] == 'cpu', 'hardware'] = 'cpu32'

    # Join dataset metadata.
    meta = pd.DataFrame.from_dict(DATASET_META, orient='index').reset_index().rename(
        columns={'index': 'dataset'}
    )
    df = df.merge(meta, on='dataset', how='left')

    # Numeric coercion — n_iter may come through as "default" (string).
    df['wall_seconds'] = pd.to_numeric(df['wall_seconds'], errors='coerce')
    df['internal_fit_seconds'] = pd.to_numeric(df['internal_fit_seconds'], errors='coerce')

    return df.reindex(columns=COLUMNS).sort_values(
        ['package', 'dataset', 'hardware', 'backend', 'variant', 'n_iter', 'seed'],
        kind='stable',
    ).reset_index(drop=True)


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        '--runtime-dir',
        type=Path,
        default=repo / 'notes' / 'data' / 'runtime',
        help='Directory of per-cell runtime TSVs.',
    )
    p.add_argument(
        '--out',
        type=Path,
        default=repo / 'notes' / 'data' / 'runtime.tsv',
        help='Aggregated TSV path.',
    )
    args = p.parse_args()

    df = parse(args.runtime_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, sep='\t', index=False)
    print(f'wrote {args.out}  ({len(df)} rows)')
    print(df.head().to_string())


if __name__ == '__main__':
    main()
