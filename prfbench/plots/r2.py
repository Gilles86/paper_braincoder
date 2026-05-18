"""Cross-package R² comparison figure.

Three panels (double-column):

- A: Median R² per (package, dataset). Point + IQR bar. Datasets on x.
- B: braincoder R² vs AFNI R², voxel-wise scatter on vanes2019.
     Identity line; points colored by density.
- C: R² distribution per package on vanes2019 (violin/strip).

Inputs:
    notes/data/r2_summary.tsv      (one row per cell)
    notes/data/r2_voxelwise.parquet  (one row per voxel × cell)

Outputs:
    notes/figures/fig_r2.pdf  +  .svg
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .style import PALETTE_PACKAGE, set_style


DATASET_ORDER = ['smallgrid', 'mediumgrid', 'largegrid', 'vanes2019']
PACKAGE_ORDER = ['braincoder', 'afni', 'aprf', 'popeye', 'mrvista']


def _panel_a_per_dataset(ax: plt.Axes, summary: pd.DataFrame) -> None:
    """Median + IQR R² per (package, dataset). Datasets on x."""
    s = summary[summary['variant'].isin(['default', 'full'])].copy()
    s['dataset'] = pd.Categorical(s['dataset'], categories=DATASET_ORDER, ordered=True)
    s['package'] = pd.Categorical(s['package'], categories=PACKAGE_ORDER, ordered=True)

    for pkg, color in PALETTE_PACKAGE.items():
        sub = s[s['package'] == pkg].sort_values('dataset')
        if sub.empty:
            continue
        xs = np.arange(len(sub))
        ax.errorbar(
            xs,
            sub['r2_median'],
            yerr=[sub['r2_median'] - sub['r2_q25'], sub['r2_q75'] - sub['r2_median']],
            fmt='o', color=color, ecolor=color, elinewidth=0.8, capsize=0,
            markersize=5, markeredgecolor='white', markeredgewidth=0.5,
            label=pkg,
        )

    ax.set_xticks(np.arange(len(DATASET_ORDER)))
    ax.set_xticklabels(DATASET_ORDER, rotation=30, ha='right')
    ax.set_ylabel('R² (median, IQR)')
    ax.set_title('A. R² across packages', loc='left', fontsize=10, fontweight='bold')


def _panel_b_braincoder_vs_afni(ax: plt.Axes, vox: pd.DataFrame) -> None:
    """Voxelwise scatter on vanes2019: braincoder vs afni."""
    sub = vox[vox['dataset'] == 'vanes2019']
    bc = sub[sub['package'] == 'braincoder'].set_index('voxel')['r2']
    af = sub[sub['package'] == 'afni'].set_index('voxel')['r2']
    common = bc.index.intersection(af.index)
    if len(common) < 100:
        ax.text(0.5, 0.5, '(no overlap on vanes2019 yet)',
                ha='center', va='center', transform=ax.transAxes,
                fontsize=8, color='0.4')
        ax.set_axis_off()
        return

    bc = bc.loc[common].to_numpy()
    af = af.loc[common].to_numpy()

    # 2D density via hexbin keeps the scatter readable for ~100k voxels.
    hb = ax.hexbin(af, bc, gridsize=60, cmap='mako', mincnt=1,
                   extent=(-0.1, 1.0, -0.1, 1.0))
    ax.plot([0, 1], [0, 1], color='0.7', lw=0.6, ls='--', zorder=0)
    ax.set_xlim(-0.1, 1.0)
    ax.set_ylim(-0.1, 1.0)
    ax.set_aspect('equal')
    ax.set_xlabel('R² (AFNI)')
    ax.set_ylabel('R² (braincoder)')
    ax.set_title('B. Voxelwise R², vanes2019', loc='left', fontsize=10, fontweight='bold')


def _panel_c_distribution(ax: plt.Axes, vox: pd.DataFrame) -> None:
    """Per-package R² distribution on vanes2019."""
    sub = vox[(vox['dataset'] == 'vanes2019') & (vox['r2'].between(-0.1, 1.0))]
    if sub.empty:
        ax.text(0.5, 0.5, '(no vanes2019 R² yet)',
                ha='center', va='center', transform=ax.transAxes,
                fontsize=8, color='0.4')
        ax.set_axis_off()
        return

    sns.violinplot(
        data=sub, x='package', y='r2', order=PACKAGE_ORDER,
        palette=PALETTE_PACKAGE, inner='quartile', linewidth=0.6,
        ax=ax, cut=0,
    )
    ax.set_ylabel('R²')
    ax.set_xlabel('')
    ax.set_title('C. R² distribution, vanes2019', loc='left', fontsize=10, fontweight='bold')
    for label in ax.get_xticklabels():
        label.set_rotation(30)
        label.set_horizontalalignment('right')


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--summary',
                   type=Path,
                   default=repo / 'notes' / 'data' / 'r2_summary.tsv')
    p.add_argument('--voxelwise',
                   type=Path,
                   default=repo / 'notes' / 'data' / 'r2_voxelwise.parquet')
    p.add_argument('--out',
                   type=Path,
                   default=repo / 'notes' / 'figures' / 'fig_r2.pdf')
    args = p.parse_args()

    set_style()
    summary = pd.read_csv(args.summary, sep='\t')
    voxelwise = pd.read_parquet(args.voxelwise)

    fig, (ax_a, ax_b, ax_c) = plt.subplots(
        1, 3, figsize=(7.25, 2.8), constrained_layout=True,
        gridspec_kw={'width_ratios': [1.2, 1.0, 1.2]},
    )
    _panel_a_per_dataset(ax_a, summary)
    _panel_b_braincoder_vs_afni(ax_b, voxelwise)
    _panel_c_distribution(ax_c, voxelwise)
    sns.despine(fig=fig, offset=5, trim=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out)
    fig.savefig(args.out.with_suffix('.svg'))
    print(f'wrote {args.out}')


if __name__ == '__main__':
    main()
