# Upstream GitHub issue draft — vistalab/PRFmodel

`prfanalyze-aprf` (and likely other MATLAB-based `prfanalyze-*` siblings) is unrunnable on hosts with kernel 6.x / glibc 2.39 even after the scipy-ABI fix from the parallel PR is applied. Filing this so future people search-hit the explanation.

## Title

`prfanalyze-aprf: MCR R2020b libjvm.so crashes "pure virtual method called" on modern Linux (kernel 6.x / glibc 2.39 / apptainer 1.4)`

## Body draft

> **Where**
>
> Sciencecluster (UZH s3it), u24 stack:
> - Linux kernel 6.x
> - glibc 2.39
> - apptainer 1.4.1 (replaces singularityce on this cluster)
>
> Container under test: `garikoitz/prfanalyze-aprf:2.1.5_3.1.1` (current latest, April 2023).
>
> **Symptom**
>
> The BIDS-app exits in ~7 s with `Failed to exec /solve.sh script!` and produces no output. Running `/solve.sh` (or the MCR launcher `/compiled/run_prfanalyze_aprf.sh`) directly inside the container surfaces the actual failure:
>
> ```
> Setting up environment variables
> ---
> LD_LIBRARY_PATH is .:/opt/mcr/v99/runtime/glnxa64:/opt/mcr/v99/bin/glnxa64:/opt/mcr/v99/sys/os/glnxa64:/opt/mcr/v99/sys/opengl/lib/glnxa64
> Opening log file:  /home/gdehol/java.log.NNNN
> pure virtual method called
> terminate called without an active exception
>
> --------------------------------------------------------------------------------
>                  abort() detected at <DATE>
> --------------------------------------------------------------------------------
>
> Configuration:
>   GNU C Library            : 2.23 stable      (container)
>   MATLAB Architecture      : glnxa64
>   MATLAB Root              : /opt/mcr/v99
>   MATLAB Version           : 9.9.0.1718557 (R2020b) Update 6
>
> Stack (selected):
>   /opt/mcr/v99/sys/java/jre/glnxa64/jre/lib/amd64/server/libjvm.so+11350671
>   /opt/mcr/v99/sys/java/jre/glnxa64/jre/lib/amd64/server/libjvm.so+09537941  JVM_handle_linux_signal
> ```
>
> The crash originates inside `libjvm.so`'s C++ runtime during MCR's JVM init (before any user code runs). It is reproducible regardless of:
> - `--cleanenv` / `--containall` / `--writable-tmpfs`
> - JVM heap caps via `JAVA_TOOL_OPTIONS=-Xmx2g -Xms256m`
> - ASLR disable via `setarch x86_64 -R`
> - `ulimit -v unlimited`
> - Replacement of `/opt/mcr/v99/sys/java/jre/` with Temurin 8u432 (same major as MCR's bundled 8u202)
>
> **Diagnosis**
>
> The MCR R2020b launcher (`prfanalyze_aprf`) is linked against the libjvm.so export ABI as built by JDK 1.8.0_202 from early 2019. The C++ destructor / vtable layout for some libjvm internals appears to have drifted relative to what newer glibc / kernel 6.x ASLR mappings produce, manifesting as `pure virtual method called` (a libstdc++ runtime error reported when a partially-destructed object's vtable slot points at a pure-virtual slot). The new JRE swap doesn't help because the launcher is linked against the *old* libjvm's specific export shape.
>
> Effectively, MCR R2020b is no longer compatible with modern Linux hosts. This is a MathWorks issue, not a `vistalab/PRFmodel` issue per se — but downstream users will encounter it here first.
>
> **Independent fix in the same family**
>
> An adjacent scipy / GLIBCXX ABI bug (see #PR-XXXX, "pin scipy<1.9 in scientific.yml") fixes the *Python-side* failure that previously masked the MCR crash — without that fix the BIDS app dies during `scipy` import before it ever reaches `/solve.sh`. So that PR is still valuable: it unblocks anyone on an older Linux host where the MCR libjvm issue doesn't yet bite.
>
> **Suggested workarounds**
>
> 1. **Pin host kernel / glibc**: run on a host with Linux 5.x and glibc ≤ 2.31. Confirmed working on the previous u20 sciencecluster generation.
> 2. **Recompile aPRF from source** against MCR R2024a or later (matching MathWorks's modern Linux support).
> 3. **Skip the BIDS-app container, run the upstream `.m` files** directly under a real MATLAB R2024+ via `module load matlab`.
>
> Mid-term I think (2) is the right path for this repo if it's still being maintained — a fresh MCR base + recompile gives a clean working image for users on modern clusters.
>
> Happy to help with PR (3) if there's interest — we have a Linux + apptainer-friendly setup for the recompile.

## How to file

```bash
gh issue create -R vistalab/PRFmodel \
    --title "prfanalyze-aprf: MCR R2020b libjvm.so crashes 'pure virtual method called' on modern Linux (kernel 6.x / glibc 2.39 / apptainer 1.4)" \
    --body-file pipeline/04_fit/_container_fix/UPSTREAM_ISSUE.md
```

(Strip the top header and the "How to file" section before pasting if doing it through the web UI.)
