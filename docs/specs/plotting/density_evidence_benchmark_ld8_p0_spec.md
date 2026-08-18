---
title: "LD8-P0 Production-Cutoff Evidence Specification"
subtitle: "Full-frame numerical baseline, occupancy profiling, and direct/FFT executor spikes"
author: "mdstats development specification"
date: "2026-07-21"
geometry: margin=0.78in
fontsize: 10pt
toc: true
toc-depth: 3
numbersections: true
colorlinks: true
header-includes:
  - |
    \usepackage{amsmath}
    \usepackage{amssymb}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{array}
    \usepackage{microtype}
    \usepackage{xcolor}
    \usepackage{enumitem}
    \usepackage{fvextra}
    \setlist{nosep}
    \setlength{\emergencystretch}{3em}
    \RecustomVerbatimEnvironment{verbatim}{Verbatim}{breaklines=true,breakanywhere=true,fontsize=\small}
---

# LD8-P0 - Production-Cutoff Evidence

**Package target:** `mdstats 0.19.54a0`  
**Status:** implemented benchmark infrastructure; production baseline evidence recorded by benchmark outputs  
**Primary script:** `benchmarks/density_ld8_p0_benchmark.py`

## Purpose

LD8-P0 is an evidence stage. It does not migrate the public density backend. It measures the real production workload before the LD8 support-atlas and hybrid-executor implementation is frozen.

The benchmark must use:

- all 1,500 trajectory frames;
- Na, Si, Al, and O channels;
- the canonical `discrete_periodized_v1` operator;
- `kernel_tail_tolerance=1e-8`;
- the effective CIC-plus-stencil broadening metric;
- the same registered display coordinates used by the saved scientific scene.

A frame subset must not be used to resolve adaptive density numerics, because shortening the trajectory changes the measured atomic-motion SD and therefore changes the scientific grid.

## Input contract

The benchmark accepts one serialized `FrameworkDynamicsScene` containing:

```text
scene.display_cell
scene.trajectory_paths.atom_indices
scene.trajectory_paths.display_positions
scene.atomic_density_fields[*].selected_atom_indices
scene.atomic_density_fields[*].field_key
scene.atomic_density_fields[*].physical_units
```

For a selected channel with $N_a$ atoms and $N_f$ frames, the benchmark reconstructs

$$
N_s=N_aN_f
$$

folded fractional samples. Each sample receives weight $1/N_f$, so the total field measure is $N_a$.

## Scientific numerical policy

The resolution policy is:

```python
DensityResolutionOptions(
    grid_interval=0.20,
    gaussian_to_grid_ratio=2.0,
    adaptive_smearing=True,
    max_smearing_to_sample_sd_ratio=0.50,
    sample_sd_quantile=0.10,
    spread_sample_size=128,
    spread_sample_seed=0,
    spread_sampling_strategy="stratified_random",
    broadening_metric="effective_cic_stencil_rms_v1",
)
```

The smoothing policy is:

```python
DensityKernelOptions(
    smoothing_operator="discrete_periodized_v1",
    kernel_tail_tolerance=1.0e-8,
)
```

The finite support is the exact retained discrete stencil produced by the existing canonical kernel builder. Its numerical support is the set of logical offsets whose Cartesian radius does not exceed

$$
r_{\mathrm{cut}}=\sigma\sqrt{F^{-1}_{\chi_3^2}(1-10^{-8})}.
$$

## Required measurements

For every channel, the benchmark records:

- resolved logical grid and node count;
- Gaussian bandwidth;
- measured motion-SD reference;
- effective CIC-plus-stencil RMS width;
- cutoff radius and retained stencil-offset count;
- occupied CIC-node count;
- estimated current-LD7 pair count;
- resolution, CIC, and stencil-construction timings;
- source-block occupancy for $8^3$, $16^3$, and $32^3$ blocks;
- connected source-block fragmentation for the $16^3$ layout;
- fixed-block and packed-positive storage estimates;
- bounded direct/FFT tile-spike timings and numerical agreement.

When `--execute-ld7` is supplied, it additionally records:

- current LD7 scientific wall time;
- packing and HDR-query wall times;
- process peak resident memory;
- final integral and storage summary;
- current LD7 execution metadata.

## Block occupancy profiles

For block edge $B$, occupied CIC nodes are mapped to

$$
\mathbf b=\left\lfloor\frac{\mathbf n}{B}\right\rfloor.
$$

The stored-block fill fraction is

$$
\phi_B=\frac{N_{\mathrm{occupied}}}{N_{\mathrm{blocks}}B^3}.
$$

The benchmark compares:

- fixed dense values within active blocks;
- one occupancy bit per local node plus packed positive `float64` values and compact block coordinates.

This estimate is evidence for LD8-S0/S1; it does not change the existing field representation.

## Executor spike

The benchmark builds a bounded dense source tile and the exact metric-aware discrete kernel. It compares linear convolution from:

```python
scipy.signal.convolve(..., method="direct")
scipy.signal.fftconvolve(...)
```

The spike is not a production executor. It provides crossover evidence only. The outputs must agree within roundoff:

$$
\frac{\lVert y_{\mathrm{direct}}-y_{\mathrm{FFT}}\rVert_1}
{\lVert y_{\mathrm{direct}}\rVert_1}
\le 5\times10^{-12}.
$$

The overlap-add production design is adapted from standard block convolution. The triclinic metric kernel, sparse tile selection, and periodic ownership are mdstats-specific.

## Resource policy

The benchmark must not allocate arrays proportional to the complete pair count merely to measure it. Existing LD7 execution remains bounded by its group-batched streaming path.

The process-memory monitor samples resident memory during the optional baseline. The reported value is empirical process RSS, not a substitute for package-owned transactional accounting.

## Outputs

The script writes:

```text
benchmarks/density_ld8_p0_benchmark.json
benchmarks/density_ld8_p0_benchmark.md
```

A full current-LD7 run may be stored separately as:

```text
benchmarks/density_ld8_p0_full_baseline.json
benchmarks/density_ld8_p0_full_baseline.md
```

The JSON schema is:

```text
mdstats.density-ld8-p0-benchmark.v1
```

## Failure conditions

The benchmark must fail explicitly when:

- the scene does not contain aligned all-atom trajectory paths;
- a selected atom index is absent from the path set;
- sample weights do not recover the selected atom count;
- the effective broadening resolver cannot meet its target;
- direct and FFT spike outputs exceed the declared tolerance;
- current LD7 execution exceeds explicit resource limits.

## Acceptance

LD8-P0 is complete only when:

- the full-frame planning result exists for all four species;
- the exact $10^{-8}$ stencil is used;
- block occupancy for 8, 16, and 32 is reported;
- direct/FFT numerical agreement passes;
- the current LD7 full baseline either completes or fails with an auditable resource record;
- the resulting evidence is reviewed before LD8-S0/S1 contracts are finalized.

## Initial evidence and implementation findings

The all-frame planning run resolves the production grids to approximately

| Channel | Grid | Retained stencil offsets | Estimated LD7 pairs |
|---|---:|---:|---:|
| Na | $540^3$ | 12,017 | 435,976,760 |
| Si | $1038^3$ | 12,017 | 657,089,560 |
| Al | $1037^3$ | 12,017 | 690,629,007 |
| O | $646^3$ | 12,017 | 2,257,044,957 |

The cumulative current-LD7 arithmetic estimate is approximately $4.04\times10^9$ source-node/stencil interactions. The bounded dense-tile spike gives direct-to-FFT speed ratios between approximately 26 and 55 while retaining relative $L^1$ agreement near $10^{-15}$. These values justify retaining both target-owned direct and tiled FFT candidates for LD8 rather than assuming the block atlas alone removes the dominant arithmetic.

The completed current-LD7 baseline measured:

| Channel | Scientific time | Packing | Three HDR queries | Peak RSS |
|---|---:|---:|---:|---:|
| Na | 41.934 s | 0.607 s | 0.720 s | 1.214 GiB |
| Si | 54.244 s | 0.563 s | 0.817 s | 1.243 GiB |
| Al | 56.022 s | 0.779 s | 0.920 s | 1.259 GiB |
| O | 187.486 s | 3.732 s | 4.831 s | 2.397 GiB |

All integrals recovered the selected atom count. The aggregate scientific time is 339.686 s, and the complete evidence script required 394.270 s. The provisional LD8-S4 gate on this host is at most 120 s aggregate scientific time, at least 3x speedup, and at most 1.5 GiB peak RSS per channel.

The optional current-LD7 execution also exposed a pre-existing normalization defect: a final negative floating residual was applied to the first sorted sparse node, which can be an arbitrarily small Gaussian-tail value. Version 0.19.54a0 applies the residual deterministically to the largest positive node in both per-batch scatter and final batch merging.

## External method attribution

The bounded FFT spike and the future tiled executor adapt the standard overlap-add organization described by A. V. Oppenheim, R. W. Schafer, and J. R. Buck, *Discrete-Time Signal Processing*, 2nd ed., Prentice Hall, 1999. The periodic triclinic metric kernel, sparse support ownership, and target-tile selection are mdstats-specific.
