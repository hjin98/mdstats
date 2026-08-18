---
title: "LD12 Hybrid-Aware Density Scene Admission Specification"
subtitle: "Exact support-atlas planning and mixed direct/FFT resource accounting"
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
    \setlist{nosep}
    \setlength{\emergencystretch}{3em}
---

# Status and scope

This specification defines **LD12** for `mdstats 0.19.67a0`. It corrects the
resource-admission mismatch between the LD0-R3 scene planner and the LD8-S3
production local-sparse executor.

The correction applies when

```python
DensityOptimizationOptions(sparse_realization_mode="hybrid")
```

which is the production default. The explicit `sparse_realization_mode="ld7"`
compatibility path retains its historical all-direct pair accounting.

LD12 does not alter:

- registered samples or their weights;
- cloud-in-cell deposition;
- the periodized Gaussian stencil;
- Gaussian bandwidth, grid interval, or tail tolerance;
- density normalization or HDR semantics;
- direct-tile or FFT-tile numerical kernels;
- browser mesh budgets.

The scientific scalar field is unchanged. LD12 changes which exact execution
plan is admitted before allocation.

# Problem statement

Before LD12, local-sparse Phase B built a streamed target union and reported

$$
C_i=N_{\mathrm{source},i}N_{\mathrm{stencil},i}
$$

as `kernel_pair_count` for field $i$. Phase C summed $C_i$ over all fields and
compared it with `max_density_kernel_pairs`.

That count is exact for the legacy all-direct scatter, but the production LD8-S3
executor partitions source nodes into compute tiles. A tile is evaluated either
by direct stencil accumulation or by metric-aware overlap-add FFT convolution.
Consequently, $C_i$ is a valid count of mathematical source-stencil
contributions, but it is not the number of direct pair operations executed by
the hybrid algorithm.

The old planner could therefore reject a feasible scene when

$$
\sum_i C_i > C_{\max}
$$

although the actual direct work

$$
D=\sum_i\sum_{t\in\mathcal D_i}
N_{\mathrm{source},t}N_{\mathrm{stencil},i}
$$

was below the direct-pair limit and the FFT tiles fit the wall-time and memory
budgets.

# Required planning order

For every production local-sparse candidate, Phase B must plan the same
scientific and execution structures used during realization:

1. aggregate the globally weighted periodic CIC source;
2. construct the exact finite Gaussian stencil;
3. pack the CIC source into immutable source blocks;
4. construct or reuse the source-independent block-routing template;
5. build the exact finite-support target atlas;
6. partition the packed source into deterministic compute tiles;
7. select direct or FFT execution for each tile using the runtime-calibrated
   cost model;
8. record exact direct work, FFT work, target support, retained bytes, transient
   bytes, and estimated wall time;
9. submit those values to global Phase C admission.

No floating density values or mesh arrays are allocated in Phase B.

# Data semantics

## Exact mathematical contributions

For one field,

$$
C_i=N_{\mathrm{source},i}N_{\mathrm{stencil},i}.
$$

`exact_contribution_count` records $C_i$. It is a diagnostic and numerical
identity check. It is not a direct-operation cap for the hybrid executor.

## Direct-tile work

For the direct tile set $\mathcal D_i$,

$$
D_i=\sum_{t\in\mathcal D_i}
N_{\mathrm{source},t}N_{\mathrm{stencil},i}.
$$

For a hybrid Phase-B record:

```text
kernel_pair_count == direct_pair_count == D_i
kernel_pair_semantics == "actual_direct_tile_pairs"
```

Phase C compares

$$
D_{\mathrm{scene}}=\sum_i D_i
$$

with `max_density_kernel_pairs`.

For the explicit LD7 compatibility path,

```text
kernel_pair_count == C_i
kernel_pair_semantics == "all_direct_pairs"
```

because every contribution is evaluated directly.

## FFT work

For each FFT tile $t\in\mathcal F_i$, let $M_t$ be its padded FFT-node count.
The selector estimates

$$
T_{\mathrm{FFT},t}
=
\alpha_{\mathrm{FFT}} M_t\log_2 M_t
+\beta_{\mathrm{FFT}},
$$

where the coefficients are derived from the current runtime calibration and
cannot be relaxed below the measured conservative values by serialized options.

The field execution estimate is

$$
T_i
=
\sum_{t\in\mathcal D_i}
\alpha_{\mathrm{direct}}D_t
+
\sum_{t\in\mathcal F_i}T_{\mathrm{FFT},t}.
$$

Phase C uses $T_i$ directly. FFT work is not converted into fictitious direct
pairs.

# Phase-B record

The existing `DensityPhaseBFieldPlan` schema is retained. Its numerical fields
have the following production-hybrid interpretation:

```python
nonzero_node_count_upper = support_atlas.target_support_node_count
stored_value_count = support_atlas.target_support_node_count
stored_block_count = support_atlas.target_block_count
stencil_value_count = stencil.stencil_offset_count
kernel_pair_count = hybrid_plan.direct_pair_count
retained_bytes = hybrid_plan.packed_field_bytes_upper + retained_samples
transient_bytes_upper = conservative hybrid construction peak
```

The metadata records:

```text
phase_b_execution_planner = ld8_s3_hybrid_exact_v1
phase_b_support_planner = ld8_s1_support_atlas_v1
exact_contribution_count
direct_pair_count
fft_padded_node_count
hybrid_compute_tile_count
hybrid_direct_tile_count
hybrid_fft_tile_count
hybrid_estimated_wall_seconds
hybrid_predicted_peak_bytes
hybrid_plan_identity
kernel_pair_semantics
```

`hybrid_plan_identity` is the SHA-256 identity of the exact immutable execution
plan.

# Phase-C scene admission

Let $H$ be the hybrid fields, $L$ the legacy all-direct sparse fields, and $Q$
the dense fields. Phase C computes

$$
D_{\mathrm{scene}}
=
\sum_{i\in H}D_i+
\sum_{i\in L}C_i.
$$

The direct-operation guard is

$$
D_{\mathrm{scene}}\le D_{\max}.
$$

The nominal total

$$
C_{\mathrm{scene}}=\sum_i C_i
$$

is recorded as `total_exact_contributions` but is not compared with the direct
pair limit for hybrid fields.

The preparation wall-time estimate is

$$
T_{\mathrm{scene}}
=s\left[
N_f\beta_f+
\frac{N_s}{r_s}+
\frac{N_k}{r_k}+
\sum_{i\in H}T_i+
\frac{\sum_{i\in L}C_i}{r_d}+
\frac{N_{\mathrm{dense}}}{r_{\mathrm{dense}}}
\right],
$$

where $s$ is the conservative safety multiplier, $N_f$ is the field count,
$N_s$ is the total source-sample count, and $N_k$ is the total retained stencil
count.

A scene is rejected only when its selected mixed execution plan exceeds a
memory, direct-work, or wall-time bound. The planner must not enlarge the grid
interval or Gaussian bandwidth to make the scene fit.

# Backend selection

`DensityBackendCandidateEstimate.estimated_work` uses the calibrated hybrid
wall estimate for a production sparse candidate. Dense and sparse candidates
therefore remain comparable without treating FFT tiles as all-direct work.

The field-local preference policy is unchanged:

- broad active support may prefer dense storage;
- localized support may prefer sparse storage;
- global Phase C may override field-local preferences to find a feasible scene;
- no candidate is considered feasible unless its own exact plan passes all
  runtime-derived limits.

# Failure diagnostics

When the direct-pair limit fails, the error reports:

- actual direct/legacy pair count;
- configured `max_density_kernel_pairs`;
- hybrid field count;
- nominal exact contribution count;
- total FFT padded nodes.

When wall time fails, the error also reports the raw hybrid execution estimate.
This distinguishes a genuinely expensive hybrid plan from the pre-LD12 false
rejection.

# Input constraints and edge cases

## All-direct hybrid selection

If every hybrid tile selects direct execution, then $D_i=C_i$. LD12 reduces to
the historical pair accounting and does not relax the guard.

## All-FFT hybrid selection

If every tile selects FFT execution, then $D_i=0$. The field is still bounded by
FFT padded-node limits, peak memory, and calibrated wall time.

## Mixed dense and sparse scene

Dense fields contribute dense-node work. Hybrid sparse fields contribute exact
mixed execution time. Legacy sparse fields contribute all-direct pairs. The
three paths are summed without double counting.

## Explicit LD7 compatibility mode

LD7 target-union planning still enumerates streamed source-stencil pairs. Its
pair count is real planning and execution work and remains subject to
`max_density_kernel_pairs`.

## Plan/realization mismatch

Realization recomputes immutable source, routing, atlas, and tile identities.
The resulting target-node and target-block counts are compared with the Phase-B
record. A mismatch is a planner defect, not a reason to alter numerical
resolution.

# Required tests

1. A hybrid field with `exact_contribution_count` above the direct-pair cap but
   `direct_pair_count` below it must pass Phase C.
2. A hybrid field with zero direct pairs but excessive FFT wall time must fail.
3. A forced local-sparse scene must record the exact hybrid planner and matching
   direct-pair semantics.
4. Direct and FFT tile counts must sum to the compute-tile count.
5. Scene metadata must separately record direct pairs, exact contributions, FFT
   padded nodes, and hybrid wall time.
6. The LD7 path must retain all-direct pair semantics.
7. Numerical density values must remain unchanged relative to the approved LD8
   hybrid executor.

# References

1. R. W. Hockney and J. W. Eastwood, *Computer Simulation Using Particles*,
   Taylor & Francis, 1988. Source of the standard cloud-in-cell particle-mesh
   assignment used before the project-specific packed support planning.
2. A. V. Oppenheim, R. W. Schafer, and J. R. Buck, *Discrete-Time Signal
   Processing*, 2nd ed., Prentice Hall, 1999. Source of the standard
   overlap-add convolution organization adapted by the LD8 tiled FFT executor.
3. `density_tiled_fft_ld8_s3_spec.md`, project specification for the
   project-specific metric-aware periodic direct/FFT tile selector.
4. `density_support_atlas_ld8_s1_spec.md`, project specification for exact
   packed finite-support atlas construction.
