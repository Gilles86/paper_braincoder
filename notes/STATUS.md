# Status

**Updated:** 2026-05-18

## What this benchmark produces

The PRF-comparison section of the braincoder paper. Three figures end up in `notes/figures/`:

1. **fig_speed.pdf** — runtime per (hardware × fit_variant × dataset), with SEM bands across 3 seeds. Plus a speedup-over-CPU panel that says how much the GPU buys you.
2. **fig_r2.pdf** — R² recovery comparison across packages (braincoder vs AFNI / aPRF / popeye / mrVista) on the same data.
3. **fig_convergence.pdf** — R² and runtime as functions of `n_gd_iterations`, sweeping `vanes2019` on A100.

A fourth figure is on the table: **fig_backend.pdf** showing braincoder runtime under TensorFlow / JAX / PyTorch backends.

## In progress

- [x] Reorg to the cogneuro-project layout (pipeline/, prfbench/, create_env/, notes/, archive/).
- [x] Generalized braincoder `run.py` with `--n_iterations`, `--seed`, dtype-safe NIfTI saves.
- [x] Parameterized SLURM dispatcher (`slurm_jobs/run.sh`, `submit.sh`, `submit_tier2.sh`, `submit_convergence.sh`).
- [ ] Three CUDA envs (TF / JAX / Torch) built on cluster GPU node.
- [ ] Non-braincoder fit scripts migrated from singularityce → apptainer.
- [ ] Backend axis (`--backend tf|jax|torch`) wired into the dispatcher.
- [ ] Tier 2 benchmark submission (72 braincoder jobs + DN + non-braincoder).
- [ ] Convergence sweep (21 jobs).
- [ ] `prfbench/parse_logs.py` and `collect_r2.py` aggregators.
- [ ] Three figures (and the optional fourth).

## Lessons logged during this rebuild

- `module: command not found` in SLURM scripts: fixed by `#!/bin/bash -l` (login shell). Old scripts that did `. "$HOME/.bashrc"` failed silently because `.bashrc` returns early non-interactively.
- Cluster migrated `singularityce` → `apptainer/1.4.1`. All non-braincoder fit scripts need this rename.
- `tf2-gpu` (the pre-existing env) is TF 2.16 / Keras 2 — too old for current braincoder (`from keras import ops`, a Keras 3 API). Hence the three new envs.
- The original `docker_package/run.py` saved NIfTIs without `set_data_dtype(float32)` / `set_slope_inter(1, 0)`. Synthetic-grid runs got away with this because they pass an all-ones mask; vanes2019 (with a binary `uint8` brain mask) would have quantized parameters. Fixed now.

## Holds and uncertainties

- DN on synthetic grids: not run (no DN ground truth). DN reported only as a timing baseline on vanes2019.
- AFNI runtime on vanes2019: never measured; the original benchmark only had AFNI on synthetic grids. Worth one cluster run to extend the cross-package R² comparison.
