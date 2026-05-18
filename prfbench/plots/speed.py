"""Speed comparison figure: runtime vs problem size.

Single panel, ~5.5" wide. One line per (package, hardware, variant) cell.
Color encodes package-or-hardware (braincoder lines pick up the hardware
palette; competing packages use their package color). Linestyle + marker
shape encode variant.

The y-axis uses log scale but with human-meaningful tick labels:
1 s · 10 s · 1 min · 10 min · 1 h · 8 h · 1 d. A reader skimming the
figure can read off "this fit takes about an hour" without doing math.

A speedup-over-CPU panel was prototyped but pulled — once we have proper
GPU rows, the comparison reads directly off the single panel ("look how
much the colored GPU lines drop below the CPU lines") and a ratio panel
adds confusion rather than clarity.

Inputs:  notes/data/runtime.tsv  (produced by `python -m prfbench.parse_logs`)
Outputs: notes/figures/fig_speed.{pdf,svg}
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

from .style import PALETTE_HARDWARE, PALETTE_PACKAGE, set_style


# Human-meaningful y-tick locations (in seconds) and their labels.
TIME_TICKS = [1, 10, 60, 600, 3_600, 28_800, 86_400]
TIME_TICK_LABELS = ['1 s', '10 s', '1 min', '10 min', '1 h', '8 h', '1 d']


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


def _aggregate(df: pd.DataFrame, hardware_subset: list[str] | None = None) -> pd.DataFrame:
    """Mean + SEM over seeds; one row per
    (package, hardware, backend, variant, dataset). Drops convergence-sweep
    cells (n_iter != 'default').

    If `hardware_subset` is given, restrict braincoder rows to those
    hardware tiers (non-braincoder packages always pass through). Default
    is cpu32 + every GPU type — drops the cpu8/cpu16 thread-scaling axis
    from this figure (it lives in fig_cpu_threads.py).
    """
    df = df.copy()
    # Drop convergence sweep — those belong to fig_convergence.
    df = df[df['n_iter'].isin([pd.NA, 'default']) | df['n_iter'].isna()]

    if hardware_subset is not None:
        keep = (df['package'] != 'braincoder') | df['hardware'].isin(hardware_subset)
        df = df[keep]

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
        # Hardware tier + variant only — the "braincoder/" prefix is
        # implicit given the color (red = AFNI, etc).
        return f'{hardware}, {variant}'
    # Non-braincoder fitters are CPU-only and have one variant.
    return package


def _plot_panel_runtime(ax: plt.Axes, agg: pd.DataFrame) -> None:
    """Runtime per dataset, categorical x-axis, log-y wall time."""
    # X is now categorical: 0, 1, 2, 3 = smallgrid → vanes2019.
    x_index = {ds: i for i, ds in enumerate(DATASET_ORDER)}

    label_positions = []   # (y, label, color, x) — staggered to avoid overlap
    for (pkg, hw, variant), grp in agg.groupby(
        ['package', 'hardware', 'variant'], dropna=False
    ):
        grp = grp.sort_values('dataset')
        if grp.empty:
            continue

        color = _line_color(pkg, hw)
        ls = LINESTYLE_VARIANT.get(variant, '-')
        marker = MARKER_VARIANT.get(variant, 'o')

        xs = [x_index[ds] for ds in grp['dataset']]
        ax.plot(
            xs, grp['mean'],
            color=color, linestyle=ls,
            marker=marker, markersize=5.0, markeredgecolor='white',
            markeredgewidth=0.6, zorder=2,
        )
        if grp['sem'].notna().any():
            ax.fill_between(
                xs,
                grp['mean'] - grp['sem'], grp['mean'] + grp['sem'],
                color=color, alpha=0.18, lw=0, zorder=1,
            )

        right_x = xs[-1]
        right_y = float(grp.iloc[-1]['mean'])
        label = _line_label(pkg, hw, variant)
        label_positions.append((right_y, label, color, right_x))

    # Stagger labels vertically when they would collide.
    label_positions.sort(key=lambda t: t[0])
    last_y_log = -np.inf
    min_log_gap = 0.08
    for y, label, color, x in label_positions:
        y_log = np.log10(y)
        if y_log - last_y_log < min_log_gap:
            y = 10 ** (last_y_log + min_log_gap)
        last_y_log = np.log10(y)
        ax.text(x + 0.08, y, label, color=color, fontsize=7.5,
                ha='left', va='center')

    ax.set_yscale('log')
    ax.set_xticks(list(x_index.values()))
    ax.set_xticklabels(DATASET_ORDER, rotation=20, ha='right')
    ax.set_xlim(-0.3, len(DATASET_ORDER) - 1 + 1.3)  # extra room on the right for labels

    # Snap ylim to the nearest TIME_TICKS around the data range BEFORE
    # the FixedLocator runs, so all our labels are visible.
    all_means = [v for v in agg['mean'].dropna().tolist() if v > 0]
    if all_means:
        y_lo, y_hi = min(all_means), max(all_means)
        ticks_lo = max([t for t in TIME_TICKS if t <= y_lo], default=TIME_TICKS[0])
        ticks_hi = min([t for t in TIME_TICKS if t >= y_hi], default=TIME_TICKS[-1])
        ax.set_ylim(ticks_lo * 0.5, ticks_hi * 2)

    # Human-meaningful y-ticks (1 s / 10 s / 1 min / 10 min / 1 h / 8 h / 1 d).
    ax.yaxis.set_major_locator(mticker.FixedLocator(TIME_TICKS))
    ax.yaxis.set_major_formatter(mticker.FixedFormatter(TIME_TICK_LABELS))
    ax.yaxis.set_minor_locator(mticker.NullLocator())

    # Tick labels self-explanatory; no x-axis title.
    ax.set_xlabel('')
    ax.set_ylabel('Wall time')


def _plot_panel_speedup(ax: plt.Axes, agg: pd.DataFrame) -> None:    # noqa: ARG001
    # Reserved for when GPU data lands; the function body is kept but
    # the speedup panel is no longer rendered in main() (see module
    # docstring for the rationale).
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
    p.add_argument(
        '--all-hardware', action='store_true',
        help='Include cpu8/cpu16 thread-scaling rows. Default omits them.',
    )
    args = p.parse_args()

    set_style()
    df = pd.read_csv(args.tsv, sep='\t')
    # Default hardware subset: drop cpu8/cpu16 (the thread-scaling axis
    # has its own plot). Pass `--all-hardware` to disable.
    hw_subset = None if args.all_hardware else [
        'cpu32', 'gpu', 'a100', 'h100', 'h200', 'l4', 'v100',
    ]
    agg = _aggregate(df, hardware_subset=hw_subset)
    if agg.empty:
        raise SystemExit(f'No runtimes in {args.tsv}. Run cluster jobs first.')

    fig, ax = plt.subplots(figsize=(5.5, 3.6), constrained_layout=True)
    _plot_panel_runtime(ax, agg)
    # `trim=True` clips the spine to the visible tick range, which with
    # our FixedLocator hides labels above the data extent. Keep the
    # offset but not the trim.
    sns.despine(fig=fig, offset=5, trim=False)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out)
    fig.savefig(args.out.with_suffix('.svg'))
    print(f'wrote {args.out}  ({len(agg)} line points)')


if __name__ == '__main__':
    main()
