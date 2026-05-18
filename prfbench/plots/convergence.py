"""Convergence figure: R² and runtime vs n_gd_iterations.

Two panels (~5" wide):

- A: median R² (and IQR band) vs n_gd_iterations, log-x.
- B: wall_seconds vs n_gd_iterations, log-log.

Picks out the "elbow" — the smallest N where R² is within 0.01 of the
maximum. That's what gets quoted in the methods.

Inputs:
    notes/data/runtime.tsv
    notes/data/r2_summary.tsv

Outputs:
    notes/figures/fig_convergence.pdf  +  .svg
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .style import set_style


# The convergence sweep runs on vanes2019, A100, TF, variant=full.
SWEEP_FILTER = {
    'package':  'braincoder',
    'dataset':  'vanes2019',
    'hardware': 'a100',
    'backend':  'tensorflow',
    'variant':  'full',
}


def _filter(df: pd.DataFrame) -> pd.DataFrame:
    mask = np.ones(len(df), dtype=bool)
    for k, v in SWEEP_FILTER.items():
        if k not in df.columns:
            continue
        mask &= (df[k] == v)
    return df[mask].copy()


def _agg(df: pd.DataFrame, value: str) -> pd.DataFrame:
    """Group by n_iter, return median / q25 / q75 of `value`."""
    df = df.copy()
    df['n_iter'] = pd.to_numeric(df['n_iter'], errors='coerce')
    df = df.dropna(subset=['n_iter'])
    g = df.groupby('n_iter')[value]
    out = g.agg(
        median='median',
        q25=lambda s: s.quantile(0.25),
        q75=lambda s: s.quantile(0.75),
        n='count',
    ).reset_index().sort_values('n_iter')
    return out


def _elbow(agg_r2: pd.DataFrame, tol: float = 0.01) -> int | None:
    """Smallest n_iter whose median R² is within `tol` of the maximum."""
    if agg_r2.empty:
        return None
    peak = agg_r2['median'].max()
    cand = agg_r2[agg_r2['median'] >= peak - tol]
    if cand.empty:
        return None
    return int(cand['n_iter'].min())


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime',  type=Path,
                   default=repo / 'notes' / 'data' / 'runtime.tsv')
    p.add_argument('--r2',       type=Path,
                   default=repo / 'notes' / 'data' / 'r2_summary.tsv')
    p.add_argument('--out',      type=Path,
                   default=repo / 'notes' / 'figures' / 'fig_convergence.pdf')
    args = p.parse_args()

    set_style()
    runtime = _filter(pd.read_csv(args.runtime, sep='\t'))
    r2 = _filter(pd.read_csv(args.r2, sep='\t'))
    if runtime.empty or r2.empty:
        raise SystemExit('Convergence sweep data missing. '
                         'Run submit_convergence.sh first.')

    agg_r2 = _agg(r2, value='r2_median')
    agg_t  = _agg(runtime, value='wall_seconds')

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(5.5, 2.8), constrained_layout=True)

    # Panel A — R² vs n_iter.
    ax_a.fill_between(agg_r2['n_iter'], agg_r2['q25'], agg_r2['q75'],
                      color='#3B5BA5', alpha=0.18, lw=0)
    ax_a.plot(agg_r2['n_iter'], agg_r2['median'], color='#3B5BA5',
              marker='o', markersize=4, markeredgecolor='white', markeredgewidth=0.5)
    elbow = _elbow(agg_r2, tol=0.01)
    if elbow is not None:
        ax_a.axvline(elbow, color='0.7', lw=0.6, ls='--', zorder=0)
        ax_a.annotate(f'Elbow ≈ {elbow}', xy=(elbow, agg_r2['median'].max()),
                      xytext=(elbow * 1.4, agg_r2['median'].max() - 0.05),
                      fontsize=7, color='0.3',
                      arrowprops=dict(arrowstyle='-', connectionstyle='arc3,rad=0.2',
                                      color='0.4', lw=0.6))
    ax_a.set_xscale('log')
    ax_a.set_xlabel('Gradient-descent iterations (log)')
    ax_a.set_ylabel('R² (median, IQR)')
    ax_a.set_title('A. Fit quality vs iterations', loc='left', fontsize=10, fontweight='bold')

    # Panel B — runtime vs n_iter.
    ax_b.fill_between(agg_t['n_iter'], agg_t['q25'], agg_t['q75'],
                      color='#C44E52', alpha=0.18, lw=0)
    ax_b.plot(agg_t['n_iter'], agg_t['median'], color='#C44E52',
              marker='o', markersize=4, markeredgecolor='white', markeredgewidth=0.5)
    if elbow is not None:
        ax_b.axvline(elbow, color='0.7', lw=0.6, ls='--', zorder=0)
    ax_b.set_xscale('log')
    ax_b.set_yscale('log')
    ax_b.set_xlabel('Gradient-descent iterations (log)')
    ax_b.set_ylabel('Wall time (s, log)')
    ax_b.set_title('B. Cost vs iterations', loc='left', fontsize=10, fontweight='bold')

    sns.despine(fig=fig, offset=5, trim=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out)
    fig.savefig(args.out.with_suffix('.svg'))
    print(f'wrote {args.out}  (elbow: {elbow})')


if __name__ == '__main__':
    main()
