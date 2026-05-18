"""Shared matplotlib + seaborn style for paper figures.

Call ``set_style()`` at the top of every figure-generating script. The
rcParams here encode the vision-science house style — Helvetica, despined
axes, outward ticks, pdf.fonttype=42 so type stays editable in Illustrator.
"""
from __future__ import annotations

import matplotlib as mpl
import seaborn as sns


def set_style() -> None:
    """Apply the project-wide rcParams."""
    mpl.rcParams.update({
        # Typography — Helvetica is the house font.
        'font.family': 'Helvetica',
        'font.sans-serif': ['Helvetica', 'Helvetica Neue', 'TeX Gyre Heros', 'Arial'],
        'font.size': 9,
        'axes.labelsize': 10,
        'axes.titlesize': 10,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'legend.fontsize': 8,
        'mathtext.fontset': 'stixsans',

        # Axes.
        'axes.linewidth': 0.8,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.labelpad': 4,

        # Ticks: outward, short, thin.
        'xtick.direction': 'out',
        'ytick.direction': 'out',
        'xtick.major.size': 3,
        'ytick.major.size': 3,
        'xtick.minor.size': 1.5,
        'ytick.minor.size': 1.5,
        'xtick.major.width': 0.8,
        'ytick.major.width': 0.8,

        # Lines and markers.
        'lines.linewidth': 1.2,
        'lines.markersize': 4,
        'patch.linewidth': 0.5,

        # Legend.
        'legend.frameon': False,
        'legend.handlelength': 1.5,

        # Vector output: editable text.
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
        'svg.fonttype': 'none',

        # Figure.
        'figure.dpi': 150,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.02,
    })
    sns.set_context('paper')


# Hand-picked categorical palettes (don't use seaborn defaults).
# Reach for these by name; documented at point of use in each figure script.
PALETTE_HARDWARE = {
    'cpu':  '#7F7F7F',   # neutral gray — the baseline
    'gpu':  '#3B5BA5',   # blue — generic GPU
    'a100': '#C44E52',   # red — A100
    'h100': '#8172B2',   # purple — H100
    'h200': '#5D8C3F',   # green — H200
    'l4':   '#B79257',   # tan — L4 (entry-level)
    'v100': '#4FA1A8',   # teal — V100 (older)
}

PALETTE_BACKEND = {
    'tensorflow': '#FF7F50',   # TF orange-ish
    'jax':        '#3B5BA5',   # JAX blue
    'torch':      '#C44E52',   # Torch red
}

PALETTE_PACKAGE = {
    'braincoder': '#3B5BA5',
    'afni':       '#C44E52',
    'aprf':       '#5D8C3F',
    'popeye':     '#8172B2',
    'mrvista':    '#7F7F7F',
}
