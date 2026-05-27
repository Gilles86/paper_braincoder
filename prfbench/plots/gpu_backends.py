"""Braincoder GPU class × backend comparison figure.

Focuses on vanes2019 (the hardest dataset; where GPU differences show
up) and braincoder/full. Each cell is one (hardware, backend) cluster
of N seeds. Strip plot inside each cluster shows per-seed wall time;
median marked with a horizontal bar.

Inputs:  notes/data/runtime.tsv
Outputs: notes/figures/fig_gpu_backends.{pdf,svg}
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

from .style import PALETTE_BACKEND, set_style
from .speed import (
    TIME_TICKS, TIME_TICK_LABELS, _format_duration,
)

HW_ORDER = ['v100', 'l4', 'a100', 'h100', 'h200']
HW_PRETTY = {
    'v100': 'V100', 'l4': 'L4',
    'a100': 'A100', 'h100': 'H100', 'h200': 'H200',
}
BACKEND_ORDER = ['tensorflow', 'jax', 'torch']
BACKEND_PRETTY = {
    'tensorflow': 'TF', 'jax': 'JAX', 'torch': 'Torch',
}


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tsv', type=Path,
                   default=repo / 'notes' / 'data' / 'runtime.tsv')
    p.add_argument('--out', type=Path,
                   default=repo / 'notes' / 'figures' / 'fig_gpu_backends.pdf')
    p.add_argument('--dataset', default='vanes2019',
                   help='Which dataset to focus on (default vanes2019).')
    p.add_argument('--since', default='2026-05-26',
                   help='Drop rows older than this date (atol-1e-4 flip).')
    args = p.parse_args()

    set_style()
    df = pd.read_csv(args.tsv, sep='\t')
    df = df[(df['package'] == 'braincoder')
            & (df['dataset'] == args.dataset)
            & (df['variant'] == 'full')
            & (df['hardware'].isin(HW_ORDER))].copy()
    if args.since:
        df = df[df['timestamp'] >= args.since]
    if df.empty:
        raise SystemExit(f'No rows for braincoder/{args.dataset}/full since {args.since}')

    df['hw_label'] = df['hardware'].map(HW_PRETTY)
    df['hw_label'] = pd.Categorical(
        df['hw_label'],
        categories=[HW_PRETTY[h] for h in HW_ORDER if h in df['hardware'].unique()],
        ordered=True,
    )
    df['backend_label'] = df['backend'].map(BACKEND_PRETTY)

    # 4.5 in tall — gives the log-y axis room without compressing
    # the V100 / L4 'failed' annotations at the top.
    fig, ax = plt.subplots(figsize=(6.5, 4.4), constrained_layout=True)

    sns.stripplot(
        data=df, x='hw_label', y='wall_seconds',
        hue='backend_label', hue_order=[BACKEND_PRETTY[b] for b in BACKEND_ORDER],
        palette={BACKEND_PRETTY[b]: PALETTE_BACKEND[b] for b in BACKEND_ORDER},
        dodge=True, size=7, alpha=0.85, linewidth=0.7, edgecolor='white',
        ax=ax,
    )

    # Median overlay: short horizontal bar at each (hw × backend) mean.
    medians = (df.groupby(['hw_label', 'backend_label'], observed=True)
                 ['wall_seconds'].median().reset_index())
    hw_pos = {lbl: i for i, lbl in enumerate(df['hw_label'].cat.categories)}
    backends_here = [BACKEND_PRETTY[b] for b in BACKEND_ORDER
                     if BACKEND_PRETTY[b] in df['backend_label'].unique()]
    n_bk = len(backends_here)
    dodge_w = 0.8 / max(n_bk, 1)
    for _, row in medians.iterrows():
        hw_i = hw_pos.get(row['hw_label'])
        if hw_i is None:
            continue
        bk_i = backends_here.index(row['backend_label'])
        x = hw_i + (bk_i - (n_bk - 1) / 2) * dodge_w
        color = {BACKEND_PRETTY[b]: PALETTE_BACKEND[b] for b in BACKEND_ORDER}[row['backend_label']]
        ax.hlines(row['wall_seconds'], x - dodge_w * 0.35, x + dodge_w * 0.35,
                  colors=color, linewidth=2.2, zorder=5)
        # Median label.
        ax.annotate(
            _format_duration(float(row['wall_seconds'])),
            xy=(x, row['wall_seconds']),
            xytext=(0, 7), textcoords='offset points',
            fontsize=8, color=color, ha='center', va='bottom',
        )

    # Annotate which (hw × backend) cells were attempted but failed —
    # otherwise the gaps in the strip plot look like "we didn't try"
    # when in fact V100/TF and L4/all failed for known reasons.
    failed = {
        ('V100', 'TF'):    'cuDNN incompat.',
        ('L4', 'TF'):      'OOM 24 GB',
        ('L4', 'JAX'):     '—',
        ('L4', 'Torch'):   '—',
    }
    for (hw, bk), reason in failed.items():
        if hw in hw_pos and reason != '—':
            hw_i = hw_pos[hw]
            bk_i = backends_here.index(bk) if bk in backends_here else 0
            x = hw_i + (bk_i - (n_bk - 1) / 2) * dodge_w
            ax.text(x, ax.get_ylim()[1] * 0.7,
                    f'✗\n{reason}', fontsize=7, color='0.4',
                    ha='center', va='top')

    ax.set_yscale('log')
    ax.yaxis.set_major_locator(mticker.FixedLocator(TIME_TICKS))
    ax.yaxis.set_major_formatter(mticker.FixedFormatter(TIME_TICK_LABELS))
    ax.yaxis.set_minor_locator(mticker.NullLocator())

    # Snap y-limits to the visible data range.
    valid_walls = df['wall_seconds'].dropna()
    if not valid_walls.empty:
        y_lo, y_hi = valid_walls.min(), valid_walls.max()
        ticks_lo = max([t for t in TIME_TICKS if t <= y_lo], default=TIME_TICKS[0])
        ticks_hi = min([t for t in TIME_TICKS if t >= y_hi], default=TIME_TICKS[-1])
        ax.set_ylim(ticks_lo * 0.5, ticks_hi * 2)

    ax.set_xlabel('GPU class', fontsize=11)
    ax.set_ylabel('Wall time (vanes2019, full GD fit)', fontsize=11)
    ax.tick_params(axis='x', labelsize=10)
    ax.tick_params(axis='y', labelsize=10)
    ax.legend(title='Backend', loc='upper right', frameon=False, fontsize=9)

    sns.despine(fig=fig, offset=5, trim=False)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out)
    fig.savefig(args.out.with_suffix('.svg'))
    print(f'wrote {args.out}  ({len(df)} cells)')


if __name__ == '__main__':
    main()
