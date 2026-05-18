# paper_braincoder

Benchmarking scaffolding for the **braincoder** paper's "Comparison to existing visuospatial PRF packages" section. Generates the speed and accuracy figures by synthesizing PRF datasets, fitting them with several PRF packages, and aggregating the results.

This is *not* the braincoder library itself. The library lives at [`~/git/braincoder`](https://github.com/Gilles86/braincoder). This repo wires it (and competing packages) into the [Lerma-Usabiaga et al. 2020 PRF-validation framework](https://doi.org/10.1371/journal.pcbi.1007924).

## Layout

```
paper_braincoder/
├── pipeline/        # cluster-runnable stages
│   ├── 01_install/      pull synthprf .sif images
│   ├── 02_synth/        synthesize BIDS datasets from prfsynth-*.json
│   ├── 03_prepare/      build BIDS from real data (vanes2019)
│   └── 04_fit/          one folder per fitter (braincoder, aprf, popeye, afni, mrvista)
│       └── braincoder/slurm_jobs/    parameterized SLURM dispatcher
├── prfbench/        # python package — log/result aggregation + plots
│   ├── parse_logs.py    runtime.tsv from per-fit runtime files
│   ├── collect_r2.py    r2_summary.tsv from per-fit r2.nii.gz files
│   └── plots/           shared style + figure scripts
├── create_env/      # conda env builds (CPU + TF/JAX/Torch CUDA)
├── notes/           # markdown working notes (STATUS, INDEX, analyses)
│   ├── data/        TSVs rsync'd from cluster
│   └── figures/     paper-bound PDFs/SVGs
├── paper/           # manuscript draft (Word docx)
└── archive/         # off-story side-projects (garcia2019, etc.)
```

## Data location

BIDS dataset (synthesized + real):

- Local: `/data/ds-prfsynth/BIDS`
- Cluster: `/shares/zne.uzh/gdehol/ds-prfsynth/BIDS`

Datasets (each becomes the BIDS participant label):

| Identifier | Source | n voxels | T | Notes |
|---|---:|---:|---:|---|
| `smallgrid` | synthetic | 490 | 200 | Cheapest end of the size sweep |
| `mediumgrid` | synthetic | 4 900 | 200 | |
| `largegrid` | synthetic | 49 000 | 200 | Largest synthetic |
| `vanes2019` | real (Van Es 2019, sub-02, surface) | 118 584 | 120 | TR=1.5 s, the headline real-data benchmark |

## Reproduce

The end-to-end recipe lives in [CLAUDE.md](CLAUDE.md) (developer notes — environment setup, recipes, gotchas). Status of the in-flight rebuild is in [notes/STATUS.md](notes/STATUS.md).

Three-line summary:

```bash
# Cluster: build env, submit benchmark
ssh sciencecluster 'cd ~/git/paper_braincoder && \
    sbatch create_env/create_gpu_env.sh tf && \
    pipeline/04_fit/braincoder/slurm_jobs/submit_tier2.sh'

# Local: aggregate + plot once runs are done
rsync sciencecluster:~/git/paper_braincoder/notes/data/ notes/data/
python -m prfbench.plots.speed
```
