# Upstream pull request — vistalab/PRFmodel

When `prfanalyze-aprf-fixed.sif` is verified to work end-to-end on the
cluster, open a pull request against
[`vistalab/PRFmodel`](https://github.com/vistalab/PRFmodel) with the
build-time fix baked into `gear/prfanalyze/base/scientific.yml`.

## Diff against upstream

```diff
--- a/gear/prfanalyze/base/scientific.yml
+++ b/gear/prfanalyze/base/scientific.yml
@@ -2,9 +2,15 @@ name: scientific
 channels:
   - conda-forge
 dependencies:
   - python=3.9
-  - numpy
-  - scipy
-  - nilearn
+  # Pin numpy/scipy/nilearn to versions whose C extensions link against
+  # libstdc++ <= 6.0.25 (GLIBCXX_3.4.25). MCR R2020b ships only that
+  # version under /opt/mcr/v99/sys/os/glnxa64 and prepends it to
+  # LD_LIBRARY_PATH, so newer scipy (which needs GLIBCXX_3.4.26)
+  # ImportErrors as soon as /scripts/run.py runs. Symptom: BIDS app
+  # exits in ~7 s with "Failed to exec /solve.sh" and no estimates.json.
+  - numpy=1.21.6
+  - scipy=1.7.3
+  - nilearn=0.9.2
   - nibabel
   - pip
   - pip:
```

## PR title

`fix(prfanalyze-base): pin scipy<1.9 so MCR's bundled libstdc++ can satisfy it`

## PR body (draft)

> **The bug**
>
> `prfanalyze-aprf:2.1.5_3.1.1` (and likely other `prfanalyze-*` images
> sharing the same base) exits in ~7 seconds under modern apptainer
> 1.4 + Ubuntu 24-class hosts. Symptom in the BIDS app log:
>
> ```
> Failed to exec /solve.sh script!
> ...
> Beginning os.wait() for /solve.sh, run=01 (child pid is ...)
> No estimates.json file found.
> ```
>
> Running `/solve.sh` directly inside the container surfaces the real
> failure:
>
> ```
> ImportError: /opt/mcr/v99/sys/os/glnxa64/libstdc++.so.6:
>   version `GLIBCXX_3.4.26' not found
>   (required by .../scipy/linalg/_matfuncs_sqrtm_triu.cpython-39-...so)
> ```
>
> **Root cause**
>
> `scientific.yml` doesn't pin `scipy`. The image was built in April
> 2023, when mamba resolved scipy → ~1.10. scipy 1.9 onward depends on
> GLIBCXX_3.4.26 (a symbol added in libstdc++ 6.0.30). The MCR R2020b
> bundle ships libstdc++ 6.0.25 (GLIBCXX_3.4.25 max) at
> `/opt/mcr/v99/sys/os/glnxa64/`, and the base image's `LD_LIBRARY_PATH`
> prepends that path. So when `/scripts/run.py` imports scipy, the
> dynamic linker finds the old libstdc++ first and the ImportError
> fires.
>
> The bug only surfaces on hosts whose host libstdc++ would otherwise
> shadow MCR's; older clusters and the original CI machines had
> matching libs and the issue stayed latent.
>
> **The fix**
>
> Pin scipy, numpy and nilearn to versions whose C extensions don't
> require GLIBCXX_3.4.26: scipy 1.7.3 / numpy 1.21.6 / nilearn 0.9.2,
> which is the last self-consistent line that supports Python 3.9 (the
> env's python) and links against libstdc++ <= 6.0.25.
>
> Verified end-to-end on UZH sciencecluster (apptainer 1.4.1, Ubuntu
> 24.04 host class) with `prfanalyze-aprf` on the prfsynth `smallgrid`
> and `mediumgrid` benchmark datasets.

## What to check before opening

1. `prfanalyze-aprf-fixed.sif` produces real `r2.nii.gz`, `centerx0.nii.gz`, etc. on `smallgrid` (not just the no-op 7-s exit).
2. The same `.def` rebuilt from the upstream Dockerfile (not just bootstrapped) reproduces the same fix — i.e., the PR diff above is sufficient on its own.
3. No regression on the other `prfanalyze-*` siblings (afni/popeye/vista/mlr): scipy 1.7.3 might break one of them if they happen to depend on a 1.9+ API. Worth a smoke test on each before claiming the fix is universal.

## Communication

After the PR: also link the issue in `vistalab/PRFmodel/issues` so future
search hits land on the explanation. Title suggestion: "prfanalyze-*
containers: scipy ABI mismatch with MCR R2020b on modern hosts".
