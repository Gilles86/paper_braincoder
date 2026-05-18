# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Companion / benchmarking scaffolding for the **braincoder** paper (de Hollander et al., draft at `paper/Braincoder paper.docx`). Generates the "Comparison to existing visuospatial PRF packages" section by synthesizing PRF datasets, fitting them with several PRF packages, and aggregating the results into runtime / R² / convergence figures.

Architecture follows the **Lerma-Usabiaga et al. 2020** PRF-validation framework (PLoS Comp Biol). Each fitter is a `prfanalyze-{pkg}` BIDS-app that writes per-parameter NIfTIs into `BIDS/derivatives/`. Braincoder is the in-house fitter; the others are upstream containers.

## Layout

```
pipeline/                cluster-runnable stages (singular ownership per stage)
├── 01_install/              pull synthprf + prfanalyze .sif images
├── 02_synth/                synthesize BIDS datasets (synthprf container)
├── 03_prepare/              build BIDS from real data (vanes2019)
└── 04_fit/                  one folder per fitter (braincoder, aprf, popeye, afni, mrvista)
    └── braincoder/
        ├── docker_package/run.py    the actual braincoder fitter
        ├── configs/                 YAML for each (variant, dataset)
        └── slurm_jobs/              parameterized SLURM dispatcher
prfbench/                 importable python package
├── parse_logs.py            aggregate runtime TSVs → notes/data/runtime.tsv
├── collect_r2.py            aggregate r2.nii.gz → notes/data/r2_*.tsv|parquet
└── plots/                   shared style + figure scripts
    ├── style.py             rcParams + palettes
    ├── speed.py             fig_speed.pdf
    ├── r2.py                fig_r2.pdf
    └── convergence.py       fig_convergence.pdf
create_env/               conda env builds (cpu + TF/JAX/torch CUDA)
notes/                    markdown-first project docs
├── INDEX.md, STATUS.md
├── data/                    TSVs/parquet rsync'd from cluster
└── figures/                 paper-bound PDFs/SVGs
paper/                    manuscript draft (untracked .docx)
archive/                  off-story side dirs (garcia2019, legacy notebooks)
```

## Data location

BIDS root:
- Local:   `/data/ds-prfsynth/BIDS`
- Cluster: `/shares/zne.uzh/gdehol/ds-prfsynth/BIDS`

Datasets (each becomes the BIDS participant label):

| Identifier | Source | n voxels | T | TR (s) |
|---|---:|---:|---:|---:|
| `smallgrid` | synthetic | 490 | 200 | 1.0 |
| `mediumgrid` | synthetic | 4 900 | 200 | 1.0 |
| `largegrid` | synthetic | 49 000 | 200 | 1.0 |
| `vanes2019` | real (Van Es 2019, sub-02 cortical surface) | 118 584 | 120 | 1.5 |

DN model is only fit on `vanes2019` (synthetic ground truth is plain Gauss).

## Benchmark axes

| Axis | Values |
|---|---|
| **dataset** | smallgrid / mediumgrid / largegrid / vanes2019 |
| **hardware** | cpu / gpu / a100 / h100 / h200 / l4 / v100 |
| **backend** | tensorflow / jax / torch (Keras 3 multi-backend) |
| **variant** | grid (no GD) / full (Gauss+GD) / hrf (+flexible HRF) / dn |
| **n_iter** | int (used by convergence sweep); else `default` |
| **seed** | 1 / 2 / 3 typically |

CPU only runs the TF backend (single env). GPU envs are split per-backend because TF/JAX/Torch's CUDA stacks conflict in one env.

## Cluster envs

| Env | Built by | Purpose |
|---|---|---|
| `paper_braincoder_cpu` | `sbatch create_env/create_cpu_env.sh` | CPU baseline (TF backend) |
| `paper_braincoder_cuda` | `sbatch create_env/create_gpu_env.sh tf` | GPU + TF backend |
| `paper_braincoder_cuda_jax` | `sbatch create_env/create_gpu_env.sh jax` | GPU + JAX backend |
| `paper_braincoder_cuda_torch` | `sbatch create_env/create_gpu_env.sh torch` | GPU + Torch backend |

All envs are Python 3.12 + Keras 3.13+ + braincoder `keras-backend` branch. CUDA 12.x throughout (works on H100 / H200, not just A100). The `create_*_env.sh` scripts wipe the env before recreating — `conda env update --prune` leaves stale pip extras.

## Running the benchmark

After pushing changes and `git pull` on cluster:

```bash
# Submit the full matrix
ssh sciencecluster 'cd ~/git/paper_braincoder/pipeline/04_fit/braincoder/slurm_jobs && \
    ./submit_tier2.sh           # speed/quality, 4 ds × 3 hw × 2 variants × 3 seeds (=72)
    ./submit_backends.sh        # TF/JAX/Torch on largegrid + vanes2019 (=18)
    ./submit_gpus.sh            # 5 GPU types on vanes2019 (=15)
    ./submit_convergence.sh     # n_iter sweep on vanes2019/A100 (=21)
'

# Aggregate (run on cluster — NIfTIs are big)
ssh sciencecluster 'cd ~/git/paper_braincoder && \
    python -m prfbench.parse_logs && \
    python -m prfbench.collect_r2'

# Pull aggregated TSVs/parquet back and plot locally
rsync sciencecluster:~/git/paper_braincoder/notes/data/ notes/data/
python -m prfbench.plots.speed
python -m prfbench.plots.r2
python -m prfbench.plots.convergence
```

`submit_tier2.sh` and friends call `submit.sh dataset hardware variant n_iter seed backend` per cell; `submit.sh` translates `hardware` to the right `--gres`. Each cell writes a single-row TSV to `notes/data/runtime/` plus standard BIDS-derivative NIfTIs.

## Implementation gotchas (load-bearing)

- **SLURM scripts use `#!/bin/bash -l`.** Plain `#!/bin/bash` is non-login non-interactive — sources nothing, so `module` and `MODULEPATH` aren't set. The old `. "$HOME/.bashrc"` workaround silently returns early because `.bashrc` starts with `case $- in *i*) ;; *) return ;; esac`. See the sciencecluster skill.
- **Cluster migrated `singularityce` → `apptainer/1.4.1`.** All container scripts now use `module load apptainer` and `apptainer exec`. `.sif` images at `/shares/zne.uzh/containers/` are unchanged.
- **Env conflicts: don't add `tensorflow-probability` or `tf_keras` to the env YMLs.** TFP pulls in `tensorflow` (latest), which collides namespace-wise with `tensorflow-cpu==2.20.*` (gives `undefined symbol: Wrapped_PyInit__pywrap_*`). braincoder gates its TFP-using modules behind `try: ... except ImportError`, and the PRF benchmark path doesn't need them.
- **dtype-safe NIfTI writes.** `docker_package/run.py` calls `set_data_dtype(np.float32) + set_slope_inter(slope=1, inter=0)` on every output. Without this, parameters can quantize through a uint8 mask's `scl_slope`. See global ~/.claude/CLAUDE.md.
- **`run.py` imports `keras` before `braincoder`** so the active backend (set via `$KERAS_BACKEND`) is locked in before braincoder compiles any tf.function / jit. CPU env only ships TF backend; GPU envs are one per backend.
- **Stimulus aperture Y-flip in `prepare_vanes.py`.** The aperture NIfTI is built with `[::-1, :, np.newaxis, :]` on the Y axis to match braincoder's coordinate convention. If you regenerate apertures, replicate the flip or fits will land mirrored.
- **Single-subject / single-session.** `run.py` asserts `len(participant_label) == 1` and `len(sessions) == 1` — pass one identifier per invocation.
- **Parameter-name translation.** `run.py`'s `pars` dict maps internal names (`x`, `y`, `sd`, `amplitude`, `baseline`) to BIDS-prfsynth derivative names (`centerx0`, `centery0`, `sigmamajor`, `beta`, `baseline`). Downstream code keys off the BIDS-side names — don't change one without the other.

## What's *not* in this repo

- `~/git/braincoder` — the actual library. Pinned in the env YMLs; override with `pip install -e libs/braincoder` for editable dev (no `libs/` submodule today, but a future need).
- The fmriprep / paradigm side — paper_braincoder doesn't run any subject-level fMRI; it consumes the publicly-shipped `vanes2019` dataset via `braincoder.utils.data.load_vanes2019` (figshare).
- Cluster credentials, IRB-restricted data — none of that lives here.

## Side dirs

- `archive/garcia2019/` — separate GLMsingle fit on `/data/ds-numrisk`; unrelated to prfsynth.
- `archive/analyze_legacy/notebooks/` — superseded jupyter notebooks; their aggregation logic is now in `prfbench/`.
- `pipeline/visualize/show_hcp99.py` — pycortex flatmap viewer for vanes2019 derivatives. Hard-coded to `subject = "hcp_999999"` and `prfanalyze-braincoder.A100` (old folder name — would need updating against the new variant.hardware.backend.seed naming).
