# Fitters

Each subdirectory wraps one PRF-fitting package in the
[Lerma-Usabiaga et al. 2020](https://doi.org/10.1371/journal.pcbi.1007924)
BIDS-app interface. The `.sif` images live at
`/shares/zne.uzh/containers/` on the cluster.

| Package | Cluster (apptainer) | Local (docker) |
|---|---|---|
| **braincoder** | `slurm_jobs/run.sh` (no container; conda env) | `docker_package/` |
| **afni** | `fit_afni_slurm.sh` | — |
| **aprf** | `fit_aprf_slurm.sh` | `fit_aprf.sh` |
| **mrvista** | `fit_mrvista_slurm.sh` | `fit_mrvista.sh` |
| **popeye** | `fit_popeye_slurm.sh` | `fit_popeye.sh` |
 