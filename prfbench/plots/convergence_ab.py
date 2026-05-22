"""Plot the GD-loop convergence trajectory of ssq vs gaussian noise models.

Reads the per-cell ``*_r2history.npz`` files emitted by braincoder's
``run.py --save-cost-history`` and renders one PDF per dataset:

    x: GD iteration
    y: mean-best R² across voxels (the value the early-stop checks)

with the early-stop checkpoint and the iteration where each curve
plateaued (Δ < r2_atol over `lag` steps) annotated in-panel.

Usage::

    python -m prfbench.plots.convergence_ab \
        --history-dir notes/data/r2_history \
        --out notes/figures/fig_convergence_ab.pdf

If you have only a single dataset's npz, the figure shrinks to one panel.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .style import set_style

# r2_atol / lag mirror the defaults in ParameterFitter.fit().
R2_ATOL = 1e-6
LAG = 100

# Hand-picked colors for the two noise models. Gauss in saturated blue
# (it's the new, fast path — visual anchor); ssq in muted ink to read as
# the legacy reference. Matches PALETTE_BACKEND's blue.
COLOR_GAUSSIAN = '#3B5BA5'
COLOR_SSQ = '#7F7F7F'

# Filename pattern emitted by braincoder.<variant>.<hardware>.<backend>[.<noise>][.n<n>].seed<s>
HISTORY_RE = re.compile(
    r'sub-(?P<dataset>[^_]+)_ses-1_task-prf_r2history\.npz$'
)


def find_npz(root: Path) -> list[Path]:
    paths = sorted(root.rglob('*_r2history.npz'))
    if not paths:
        raise FileNotFoundError(
            f'No *_r2history.npz under {root}. Rsync the braincoder '
            f'derivatives back from /shares/zne.uzh/.../prfanalyze-'
            f'braincoder.full.a100.tensorflow.{{ssq,}}seed99/ to '
            f'{root}/.'
        )
    return paths


def parse_meta(p: Path) -> dict:
    """Pull (dataset, noise_model) out of the file's parent dir name.

    The directory structure ends in ``prfanalyze-braincoder.<tag>/sub-<ds>/ses-1/``.
    The tag encodes noise_model only when != 'gaussian' (the default);
    so its absence in the tag means gaussian.
    """
    sub_dir = p.parents[1].name        # sub-<dataset>
    deriv_dir = p.parents[2].name      # prfanalyze-braincoder.<tag>
    m = re.match(r'sub-(?P<dataset>.+)', sub_dir)
    dataset = m.group('dataset') if m else 'unknown'
    tag = deriv_dir.split('.', 1)[1] if '.' in deriv_dir else ''
    noise_model = 'ssq' if '.ssq.' in f'.{tag}.' else 'gaussian'
    return {'dataset': dataset, 'noise_model': noise_model, 'tag': tag}


def plateau_step(history: np.ndarray, atol: float = R2_ATOL,
                 lag: int = LAG, min_iter: int = 100) -> int | None:
    """Mirror ParameterFitter.fit()'s early-stop check.

    Returns the iteration index at which the loop would have broken,
    or None if the recorded history is short enough that the stop never
    triggered (e.g., the run hit max_n_iterations).
    """
    if history.size == 0:
        return None
    for step in range(min_iter, len(history)):
        r2_diff = history[step] - history[max(step - lag, 0)]
        if 0.0 <= r2_diff < atol:
            return step
    return None


def plot_dataset(ax, runs: list[tuple[str, np.ndarray]], dataset: str) -> None:
    """One panel: curves of two noise models on the same dataset."""
    for noise_model, history in runs:
        color = COLOR_GAUSSIAN if noise_model == 'gaussian' else COLOR_SSQ
        x = np.arange(1, len(history) + 1)
        ax.plot(x, history, color=color, linewidth=1.4,
                label=f'{noise_model} (n={len(history)})')

        stop = plateau_step(history)
        if stop is not None:
            ax.axvline(stop, color=color, linewidth=0.6,
                       linestyle=':', alpha=0.8)
            ax.annotate(
                f'Early-stop @ {stop}',
                xy=(stop, history[stop]),
                xytext=(6, -8 if noise_model == 'ssq' else 6),
                textcoords='offset points', fontsize=7, color=color)

    ax.set_xlabel('GD iteration')
    ax.set_ylabel('Mean best R² across voxels')
    ax.set_title(dataset, fontsize=10, loc='left')
    ax.legend(loc='lower right', fontsize=8)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--history-dir', type=Path,
                   default=Path(__file__).resolve().parents[2]
                   / 'notes' / 'data' / 'r2_history')
    p.add_argument('--out', type=Path,
                   default=Path(__file__).resolve().parents[2]
                   / 'notes' / 'figures' / 'fig_convergence_ab.pdf')
    args = p.parse_args()

    set_style()

    paths = find_npz(args.history_dir)

    # Group histories: {dataset: [(noise_model, gauss_gd_array), ...]}
    by_ds: dict[str, list[tuple[str, np.ndarray]]] = {}
    for path in paths:
        meta = parse_meta(path)
        npz = np.load(path, allow_pickle=True)
        # We plot the Gauss+GD trajectory; DN runs (if present) are skipped
        # here — they have a separate set of curves not relevant to the
        # ssq-vs-gaussian comparison.
        history = np.asarray(npz['gauss_gd']).astype(float)
        if history.size == 0:
            print(f'  skip empty history: {path}')
            continue
        by_ds.setdefault(meta['dataset'], []).append(
            (meta['noise_model'], history))

    if not by_ds:
        raise RuntimeError(f'All *_r2history.npz under {args.history_dir} were empty.')

    # Dataset order matches fig_speed: small → medium → large → vanes2019.
    ds_order = ['smallgrid', 'mediumgrid', 'largegrid', 'vanes2019']
    datasets = [d for d in ds_order if d in by_ds] + [d for d in by_ds if d not in ds_order]

    ncol = len(datasets)
    width = 1.9 * ncol + 0.6
    fig, axes = plt.subplots(1, ncol, figsize=(width, 2.4),
                             sharex=False, sharey=False,
                             constrained_layout=True)
    if ncol == 1:
        axes = [axes]

    for ax, ds in zip(axes, datasets):
        runs = sorted(by_ds[ds], key=lambda t: 0 if t[0] == 'gaussian' else 1)
        plot_dataset(ax, runs, ds)

    fig.suptitle(
        'Braincoder GD convergence: Gaussian NLL vs sum-of-squares (vanes2019/A100/TF, seed 99)',
        fontsize=10, x=0.01, ha='left')

    import seaborn as sns
    sns.despine(fig=fig, offset=4, trim=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out)
    print(f'wrote {args.out}')


if __name__ == '__main__':
    main()
