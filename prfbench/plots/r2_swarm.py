"""Faceted per-voxel R² distribution by package × dataset.

Replaces the median+IQR line chart with one panel per dataset (free
y-axis so vanes2019's lower-R² regime isn't squashed by the synth
grids). Inside each panel: strip plot of subsampled per-voxel R²
across all (seed × hardware) repeats, with the seed-averaged median
overlaid as a solid bar.

Inputs:  notes/data/r2_samples.tsv  (from prfbench.collect_r2_samples)
Outputs: notes/figures/fig_r2_swarm.{pdf,svg}
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

# Variant tag → readable label. Packages with only 'default' don't get
# the variant suffix.
VARIANT_LABEL = {
    ('braincoder', 'full'): 'braincoder GD',
    ('braincoder', 'grid'): 'braincoder grid',
    # +HRF intentionally absent: it's a 7-parameter model
    # (x, y, σ, β, baseline + hrf_delay, hrf_dispersion), so not
    # comparable to the 5-param fitters in this panel.
}

# Canonical package order on x. Only 5-parameter circular Gaussian
# fitters here; +HRF / DN variants live in a separate figure.
CAT_ORDER = [
    'afni',
    'popeye',
    'mrvista',
    'braincoder grid',
    'braincoder GD',
]


def _label_row(row: pd.Series) -> str:
    if row['package'] == 'braincoder':
        return VARIANT_LABEL.get((row['package'], row['variant']),
                                  f'braincoder\n({row["variant"]})')
    return row['package']


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--samples', type=Path,
                   default=repo / 'notes' / 'data' / 'r2_samples.tsv')
    p.add_argument('--out', type=Path,
                   default=repo / 'notes' / 'figures' / 'fig_r2_swarm.pdf')
    p.add_argument('--hardware-keep', default='cpu,cpu32,a100',
                   help='Comma-separated hardware tiers to include for '
                   'braincoder (others are usually redundant repeats).')
    args = p.parse_args()

    set_style()
    df = pd.read_csv(args.samples, sep='\t')
    # Keep braincoder only on the canonical hardware tiers (a100 + cpu32);
    # other packages have only one hw each so let them through.
    hw_keep = set(s.strip() for s in args.hardware_keep.split(','))
    keep = (df['package'] != 'braincoder') | df['hardware'].isin(hw_keep)
    df = df[keep].copy()
    # For braincoder, prefer the a100 cell over cpu32 (same R² up to GD
    # noise, but a100 has more seeds in our matrix).
    bc_mask = df['package'] == 'braincoder'
    bc_a100 = df.loc[bc_mask & (df['hardware'] == 'a100')]
    if not bc_a100.empty:
        df = pd.concat([df[~bc_mask], bc_a100], ignore_index=True)

    df['cat'] = df.apply(_label_row, axis=1)
    df = df[df['cat'].isin(CAT_ORDER)]
    df['cat'] = pd.Categorical(df['cat'], categories=CAT_ORDER, ordered=True)
    df['dataset'] = pd.Categorical(df['dataset'], categories=DATASET_ORDER, ordered=True)

    palette = {
        'afni': PALETTE_PACKAGE['afni'],
        'popeye': PALETTE_PACKAGE['popeye'],
        'mrvista': PALETTE_PACKAGE['mrvista'],
        'braincoder GD':    PALETTE_PACKAGE['braincoder'],
        'braincoder grid':  '#7494C8',  # lighter blue
    }

    datasets_present = [d for d in DATASET_ORDER if (df['dataset'] == d).any()]
    ncol = len(datasets_present)
    fig, axes = plt.subplots(
        1, ncol, figsize=(2.8 * ncol + 0.8, 4.2),
        sharex=False, sharey=False, constrained_layout=True,
    )
    if ncol == 1:
        axes = [axes]

    for ax, ds in zip(axes, datasets_present):
        sub = df[df['dataset'] == ds]
        cats_here = [c for c in CAT_ORDER if (sub['cat'] == c).any()]
        sns.stripplot(
            data=sub, x='cat', y='r2', order=cats_here,
            hue='cat', hue_order=cats_here, palette=palette,
            size=1.4, alpha=0.18, jitter=0.32, linewidth=0,
            ax=ax, legend=False,
        )
        # Overlay per-package median (across all sampled voxels, all seeds).
        med = (sub.groupby('cat', observed=True)['r2']
                  .median().reindex(cats_here))
        for i, m in enumerate(med):
            if pd.isna(m):
                continue
            color = palette[cats_here[i]]
            ax.hlines(m, i - 0.35, i + 0.35,
                      colors=color, linewidth=2.2, zorder=5)

        ax.axhline(0, color='0.75', lw=0.5, ls=':', zorder=0)
        ax.set_title(ds, fontsize=10, loc='left')
        ax.set_xlabel('')
        ax.set_ylabel('R² (per voxel)' if ds == datasets_present[0] else '')
        # Tight y-limits per panel: pad a bit above/below the data range.
        lo, hi = float(sub['r2'].quantile(0.005)), float(sub['r2'].quantile(0.995))
        pad = max(0.02, 0.05 * (hi - lo))
        ax.set_ylim(min(lo - pad, -0.05), hi + pad)

    fig.suptitle(
        'Per-voxel R² distribution by package and dataset '
        '(500 voxels per cell, all seeds pooled; bar = median).',
        fontsize=9, x=0.01, ha='left',
    )
    sns.despine(fig=fig, offset=4, trim=True)

    # Rotation must be applied AFTER despine + suptitle, otherwise
    # seaborn's internal tick-label reset wipes it out.
    for ax in axes:
        plt.setp(ax.get_xticklabels(),
                 rotation=45, ha='right', rotation_mode='anchor',
                 fontsize=8)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out)
    fig.savefig(args.out.with_suffix('.svg'))
    print(f'wrote {args.out}  ({len(df)} samples, {df["cat"].nunique()} categories)')


if __name__ == '__main__':
    main()
