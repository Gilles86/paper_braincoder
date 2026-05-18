"""Speed comparison figure: runtime + speedup vs problem size.

Two panels (single double-column page width):
- A: wall_seconds vs n_voxels, log-log, lines per (hardware × fit_variant).
- B: speedup over CPU vs n_voxels, log-x.

Direct-labels at the right endpoint of each line; no legend.

Inputs:
    notes/data/runtime.tsv  (produced by `python -m prfbench.parse_logs`)

Outputs:
    notes/figures/fig_speed.pdf  +  fig_speed.svg
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .style import PALETTE_HARDWARE, set_style


# Datasets in size order; x-axis of the figure.
DATASET_ORDER = ['smallgrid', 'mediumgrid', 'largegrid', 'vanes2019']

# (hardware, variant) → line styling. Linestyle encodes variant; color
# encodes hardware. Two encodings per line means colorblind-readability
# is preserved even if printed grayscale.
LINESTYLE_VARIANT = {
    'grid': (0, (3, 2)),     # dashed — grid-only (fastest, lowest accuracy floor)
    'full': '-',             # solid — Gauss + GD (default fit)
    'hrf':  (0, (1, 1.5)),   # dotted — Gauss + GD + flexible HRF
    'dn':   (0, (4, 1, 1, 1)),  # dash-dot — DN (vanes2019 only)
}


def _aggregate(df: pd.DataFrame, package: str = 'braincoder') -> pd.DataFrame:
    """Mean ± SEM over seeds; one row per (hardware, backend, variant, dataset)."""
    df = df[df['package'] == package].copy()
    df = df[df['n_iter'].isin([pd.NA, 'default']) | df['n_iter'].isna()]

    grouped = df.groupby(
        ['hardware', 'backend', 'variant', 'dataset', 'n_voxels'],
        dropna=False,
    )['wall_seconds']
    agg = grouped.agg(
        mean='mean',
        sem=lambda s: s.std(ddof=1) / np.sqrt(len(s)) if len(s) > 1 else np.nan,
        n='count',
    ).reset_index()

    # Order dataset categorically by size so plots sort cleanly.
    agg['dataset'] = pd.Categorical(agg['dataset'], categories=DATASET_ORDER, ordered=True)
    agg = agg.sort_values(['hardware', 'variant', 'dataset']).reset_index(drop=True)
    return agg


def _plot_panel_runtime(ax: plt.Axes, agg: pd.DataFrame) -> None:
    """Panel A — runtime vs n_voxels, log-log."""
    for (hw, variant), grp in agg.groupby(['hardware', 'variant'], dropna=False):
        grp = grp.sort_values('n_voxels')
        if grp.empty:
            continue
        color = PALETTE_HARDWARE.get(hw, '0.4')
        ls = LINESTYLE_VARIANT.get(variant, '-')

        ax.plot(grp['n_voxels'], grp['mean'], color=color, linestyle=ls,
                marker='o', markersize=3.5, markeredgecolor='white',
                markeredgewidth=0.5, zorder=2)
        if grp['sem'].notna().any():
            ax.fill_between(grp['n_voxels'],
                            grp['mean'] - grp['sem'], grp['mean'] + grp['sem'],
                            color=color, alpha=0.18, lw=0, zorder=1)

        # Direct label at right endpoint.
        right = grp.iloc[-1]
        ax.text(right['n_voxels'] * 1.15, right['mean'],
                f'{hw}/{variant}',
                color=color, fontsize=7, ha='left', va='center')

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Voxels (log)')
    ax.set_ylabel('Wall time (s, log)')
    ax.set_title('A. Runtime', loc='left', fontsize=10, fontweight='bold')


def _plot_panel_speedup(ax: plt.Axes, agg: pd.DataFrame) -> None:
    """Panel B — speedup over CPU at the same (variant, dataset)."""
    cpu = agg[agg['hardware'] == 'cpu'][['variant', 'dataset', 'mean']].rename(
        columns={'mean': 'cpu_seconds'})
    gpu_rows = agg[agg['hardware'] != 'cpu'].merge(
        cpu, on=['variant', 'dataset'], how='left')
    gpu_rows['speedup'] = gpu_rows['cpu_seconds'] / gpu_rows['mean']

    for (hw, variant), grp in gpu_rows.groupby(['hardware', 'variant'], dropna=False):
        grp = grp.sort_values('n_voxels')
        if grp['speedup'].isna().all():
            continue
        color = PALETTE_HARDWARE.get(hw, '0.4')
        ls = LINESTYLE_VARIANT.get(variant, '-')
        ax.plot(grp['n_voxels'], grp['speedup'],
                color=color, linestyle=ls,
                marker='o', markersize=3.5, markeredgecolor='white',
                markeredgewidth=0.5)
        right = grp.iloc[-1]
        if pd.notna(right['speedup']):
            ax.text(right['n_voxels'] * 1.15, right['speedup'],
                    f'{hw}/{variant}',
                    color=color, fontsize=7, ha='left', va='center')

    ax.axhline(1, color='0.7', lw=0.6, ls='--', zorder=0)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Voxels (log)')
    ax.set_ylabel('Speedup over CPU')
    ax.set_title('B. Speedup', loc='left', fontsize=10, fontweight='bold')


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        '--tsv',
        type=Path,
        default=repo / 'notes' / 'data' / 'runtime.tsv',
    )
    p.add_argument(
        '--out',
        type=Path,
        default=repo / 'notes' / 'figures' / 'fig_speed.pdf',
    )
    args = p.parse_args()

    set_style()
    df = pd.read_csv(args.tsv, sep='\t')
    agg = _aggregate(df)
    if agg.empty:
        raise SystemExit(f'No braincoder runtimes in {args.tsv}. Run cluster jobs first.')

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(7.25, 3.3), constrained_layout=True)
    _plot_panel_runtime(ax_a, agg)
    _plot_panel_speedup(ax_b, agg)
    sns.despine(fig=fig, offset=5, trim=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out)
    fig.savefig(args.out.with_suffix('.svg'))
    print(f'wrote {args.out}')


if __name__ == '__main__':
    main()
