"""Speed comparison figure: runtime + speedup vs problem size.

Two panels, double-column width.

- A: wall_seconds vs (voxels × timepoints), log-log. One line per
     (package, hardware, variant) cell. Color encodes package-or-hardware
     (braincoder lines pick up the hardware palette; competing packages
     use their package color). Linestyle encodes variant.
- B: speedup-over-CPU for the same problem size. Empty until GPU rows
     land. Shares the x-axis with panel A so the absent-data range still
     reads as "no data here yet" rather than as a different scale.

Inputs:  notes/data/runtime.tsv  (produced by `python -m prfbench.parse_logs`)
Outputs: notes/figures/fig_speed.{pdf,svg}
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .style import PALETTE_HARDWARE, PALETTE_PACKAGE, set_style


DATASET_ORDER = ['smallgrid', 'mediumgrid', 'largegrid', 'vanes2019']

# Linestyle + marker shape encode variant — both for redundancy with color
# (readable in grayscale) AND because two CPU variants picking up the same
# color need an extra visual axis to tell apart.
LINESTYLE_VARIANT = {
    'grid':    (0, (3, 2)),       # dashed
    'full':    '-',               # solid
    'hrf':     (0, (1, 1.5)),     # dotted
    'dn':      (0, (4, 1, 1, 1)), # dash-dot
    'default': '-',               # other packages have no variant axis
}
MARKER_VARIANT = {
    'grid':    'o',
    'full':    's',
    'hrf':     '^',
    'dn':      'D',
    'default': 'o',
}


def _line_color(package: str, hardware: str) -> str:
    """braincoder lines get the hardware palette; other packages get their
    package color. This keeps the cluster-comparison story (braincoder
    × hardware) visually grouped, and the cross-package story (braincoder
    vs the rest) separated by hue."""
    if package == 'braincoder':
        return PALETTE_HARDWARE.get(hardware, '0.4')
    return PALETTE_PACKAGE.get(package, '0.4')


def _aggregate(df: pd.DataFrame) -> pd.DataFrame:
    """Mean + SEM over seeds; one row per
    (package, hardware, backend, variant, dataset). Drops convergence-sweep
    cells (n_iter != 'default')."""
    df = df.copy()
    # Drop convergence sweep — those belong to fig_convergence.
    df = df[df['n_iter'].isin([pd.NA, 'default']) | df['n_iter'].isna()]
    df['problem_size'] = df['n_voxels'] * df['n_timepoints']

    grouped = df.groupby(
        ['package', 'hardware', 'backend', 'variant', 'dataset',
         'n_voxels', 'n_timepoints', 'problem_size'],
        dropna=False,
    )['wall_seconds']
    agg = grouped.agg(
        mean='mean',
        sem=lambda s: s.std(ddof=1) / np.sqrt(len(s)) if len(s) > 1 else np.nan,
        n='count',
    ).reset_index()

    agg['dataset'] = pd.Categorical(agg['dataset'], categories=DATASET_ORDER, ordered=True)
    agg = agg.sort_values(
        ['package', 'hardware', 'variant', 'problem_size']
    ).reset_index(drop=True)
    return agg


def _line_label(package: str, hardware: str, variant: str) -> str:
    """Short label for endpoint annotation."""
    if package == 'braincoder':
        return f'braincoder/{hardware}/{variant}'
    # Non-braincoder fitters are CPU-only and have one variant.
    return package


def _plot_panel_runtime(ax: plt.Axes, agg: pd.DataFrame) -> None:
    """Panel A — runtime vs problem size, log-log."""
    label_positions = []   # (y, label) — used to nudge stacked labels apart
    for (pkg, hw, variant), grp in agg.groupby(
        ['package', 'hardware', 'variant'], dropna=False
    ):
        grp = grp.sort_values('problem_size')
        if grp.empty:
            continue

        color = _line_color(pkg, hw)
        ls = LINESTYLE_VARIANT.get(variant, '-')
        marker = MARKER_VARIANT.get(variant, 'o')

        ax.plot(
            grp['problem_size'], grp['mean'],
            color=color, linestyle=ls,
            marker=marker, markersize=4.0, markeredgecolor='white',
            markeredgewidth=0.5, zorder=2,
        )
        if grp['sem'].notna().any():
            ax.fill_between(
                grp['problem_size'],
                grp['mean'] - grp['sem'], grp['mean'] + grp['sem'],
                color=color, alpha=0.18, lw=0, zorder=1,
            )

        right = grp.iloc[-1]
        label = _line_label(pkg, hw, variant)
        label_positions.append((float(right['mean']), label, color, float(right['problem_size'])))

    # Stagger labels vertically when they collide.
    label_positions.sort(key=lambda t: t[0])
    last_y_log = -np.inf
    min_log_gap = 0.07
    for y, label, color, x in label_positions:
        y_log = np.log10(y)
        if y_log - last_y_log < min_log_gap:
            y = 10 ** (last_y_log + min_log_gap)
        last_y_log = np.log10(y)
        ax.text(x * 1.15, y, label, color=color, fontsize=7, ha='left', va='center')

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Voxels × Timepoints (log)')
    ax.set_ylabel('Wall time (s, log)')
    ax.set_title('A. Runtime', loc='left', fontsize=10, fontweight='bold')


def _plot_panel_speedup(ax: plt.Axes, agg: pd.DataFrame) -> None:
    """Panel B — speedup over CPU at the same (package, variant, dataset)."""
    # Reference: each (package, variant, dataset)'s own CPU run.
    cpu = agg[agg['hardware'] == 'cpu'][
        ['package', 'variant', 'dataset', 'mean']
    ].rename(columns={'mean': 'cpu_seconds'})
    gpu_rows = agg[agg['hardware'] != 'cpu'].merge(
        cpu, on=['package', 'variant', 'dataset'], how='left',
    )
    gpu_rows['speedup'] = gpu_rows['cpu_seconds'] / gpu_rows['mean']

    plotted_any = False
    for (pkg, hw, variant), grp in gpu_rows.groupby(
        ['package', 'hardware', 'variant'], dropna=False,
    ):
        grp = grp.sort_values('problem_size')
        if grp['speedup'].isna().all():
            continue
        plotted_any = True

        color = _line_color(pkg, hw)
        ls = LINESTYLE_VARIANT.get(variant, '-')
        marker = MARKER_VARIANT.get(variant, 'o')
        ax.plot(
            grp['problem_size'], grp['speedup'],
            color=color, linestyle=ls,
            marker=marker, markersize=4.0, markeredgecolor='white',
            markeredgewidth=0.5,
        )
        right = grp.iloc[-1]
        if pd.notna(right['speedup']):
            ax.text(
                right['problem_size'] * 1.15, right['speedup'],
                _line_label(pkg, hw, variant),
                color=color, fontsize=7, ha='left', va='center',
            )

    ax.axhline(1, color='0.7', lw=0.6, ls='--', zorder=0)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Voxels × Timepoints (log)')
    ax.set_ylabel('Speedup over CPU')
    ax.set_title('B. Speedup', loc='left', fontsize=10, fontweight='bold')

    if not plotted_any:
        ax.text(0.5, 0.5, '(no non-CPU runs yet)',
                transform=ax.transAxes, ha='center', va='center',
                fontsize=8, color='0.4')


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
        raise SystemExit(f'No runtimes in {args.tsv}. Run cluster jobs first.')

    fig, (ax_a, ax_b) = plt.subplots(
        1, 2, figsize=(7.5, 3.5), constrained_layout=True, sharex=True,
    )
    _plot_panel_runtime(ax_a, agg)
    _plot_panel_speedup(ax_b, agg)

    # Match Panel A's x range on Panel B even if B has no data yet.
    ax_b.set_xlim(ax_a.get_xlim())
    sns.despine(fig=fig, offset=5, trim=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out)
    fig.savefig(args.out.with_suffix('.svg'))
    print(f'wrote {args.out}  ({len(agg)} line points)')


if __name__ == '__main__':
    main()
