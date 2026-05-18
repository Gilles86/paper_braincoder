"""Parameter-recovery figure on synthetic data.

Inputs:
    notes/data/params_recovery.parquet           (voxelwise long format)
    notes/data/params_recovery_summary.tsv       (per-cell r/rmse/bias)

Two panels (~7" wide):

- A: estimated vs true scatter on `largegrid`, faceted by parameter
     (centerx0, centery0, sigmamajor), points colored by package.
     Identity line; equal aspect.
- B: per-package Pearson r per parameter (pointplot, x=parameter, y=r).
     Across packages: does braincoder recover ground truth as well as
     the slower fitters?
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .style import PALETTE_PACKAGE, set_style


PARAMS = ['centerx0', 'centery0', 'sigmamajor']
PACKAGE_ORDER = ['braincoder', 'afni', 'aprf', 'popeye', 'mrvista']


# For braincoder, restrict to one (hardware, backend, variant) cell when
# the matrix has many — otherwise scatter is overplotted. Default: A100,
# TF, full Gauss+GD, seed=1.
DEFAULT_BC_FILTER = {
    'hardware': 'a100',
    'backend':  'tensorflow',
    'variant':  'full',
    'seed':     1,
}


def _filter_braincoder(df: pd.DataFrame, sel: dict) -> pd.DataFrame:
    bc_mask = df['package'] == 'braincoder'
    bc = df[bc_mask].copy()
    for k, v in sel.items():
        if k in bc.columns:
            bc = bc[bc[k] == v]
    other = df[~bc_mask]
    return pd.concat([bc, other], ignore_index=True)


def _panel_a_scatter(axes: list[plt.Axes], long_df: pd.DataFrame,
                     dataset: str = 'largegrid') -> None:
    """One subplot per parameter."""
    sub = long_df[long_df['dataset'] == dataset]
    if sub.empty:
        for ax in axes:
            ax.text(0.5, 0.5, f'(no {dataset} recovery data)',
                    transform=ax.transAxes, ha='center', va='center',
                    fontsize=8, color='0.4')
            ax.set_axis_off()
        return

    for ax, par in zip(axes, PARAMS):
        pdf = sub[sub['parameter'] == par]
        if pdf.empty:
            ax.set_axis_off()
            continue

        for pkg in PACKAGE_ORDER:
            pp = pdf[pdf['package'] == pkg]
            if pp.empty:
                continue
            ax.scatter(pp['true'], pp['estimated'],
                       s=4, alpha=0.25, color=PALETTE_PACKAGE[pkg],
                       edgecolors='none', label=pkg, rasterized=True)

        # Identity line.
        lo = float(min(pdf['true'].min(), pdf['estimated'].min()))
        hi = float(max(pdf['true'].max(), pdf['estimated'].max()))
        ax.plot([lo, hi], [lo, hi], color='0.7', lw=0.6, ls='--', zorder=0)
        ax.set_aspect('equal', adjustable='box')

        nice = {'centerx0': 'x₀', 'centery0': 'y₀', 'sigmamajor': 'σ'}[par]
        ax.set_xlabel(f'True {nice}')
        ax.set_ylabel(f'Estimated {nice}')
        ax.set_title(f'{nice} ({dataset})', loc='left', fontsize=9, fontweight='bold')


def _panel_b_corr(ax: plt.Axes, summary: pd.DataFrame,
                  dataset: str = 'largegrid') -> None:
    """Per-package Pearson r per parameter."""
    sub = summary[summary['dataset'] == dataset]
    if sub.empty:
        ax.set_axis_off()
        return

    sns.pointplot(
        data=sub, x='parameter', y='r', hue='package', order=PARAMS,
        hue_order=PACKAGE_ORDER, palette=PALETTE_PACKAGE,
        errorbar=('ci', 95), markers='o', linestyles='-', dodge=0.3,
        ax=ax,
    )
    ax.axhline(1, color='0.7', lw=0.6, ls='--', zorder=0)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel('')
    ax.set_ylabel('Pearson r (estimated vs true)')
    ax.set_title(f'Per-package recovery, {dataset}',
                 loc='left', fontsize=9, fontweight='bold')
    ax.legend(loc='lower right', frameon=False, ncol=2, fontsize=7)


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--long',
                   type=Path,
                   default=repo / 'notes' / 'data' / 'params_recovery.parquet')
    p.add_argument('--summary',
                   type=Path,
                   default=repo / 'notes' / 'data' / 'params_recovery_summary.tsv')
    p.add_argument('--dataset',
                   default='largegrid',
                   choices=['smallgrid', 'mediumgrid', 'largegrid'])
    p.add_argument('--out',
                   type=Path,
                   default=repo / 'notes' / 'figures' / 'fig_recovery.pdf')
    args = p.parse_args()

    set_style()
    long_df = pd.read_parquet(args.long)
    summary = pd.read_csv(args.summary, sep='\t')

    # For the scatter panel we want one braincoder cell. Summary panel
    # keeps all of them (CI bars span the matrix).
    long_filt = _filter_braincoder(long_df, DEFAULT_BC_FILTER)

    fig, axes = plt.subplots(
        1, 4,
        figsize=(7.25, 2.4),
        constrained_layout=True,
        gridspec_kw={'width_ratios': [1, 1, 1, 1.3]},
    )
    _panel_a_scatter(axes[:3], long_filt, dataset=args.dataset)
    _panel_b_corr(axes[3], summary, dataset=args.dataset)
    sns.despine(fig=fig, offset=5, trim=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out)
    fig.savefig(args.out.with_suffix('.svg'))
    print(f'wrote {args.out}')


if __name__ == '__main__':
    main()
