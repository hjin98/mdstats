---
title: "LD7 Full-Trajectory Sparse-Density Tractability Specification"
subtitle: "Deterministic spread subsampling, bounded block streaming, and exact source-group batching"
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

# LD7 — Full-Trajectory Sparse-Density Tractability

**Package target:** `mdstats 0.19.53a0`  
**Status:** normative and implemented  
**Scope:** periodic atomic, framework-vertex, and framework-edge density preparation

## 1. Objective

LD7 makes the completed single-level block-sparse density architecture practical for long, finely resolved trajectories without changing the scientific estimator.

The triggering case is a 1,300-frame, 168-atom Na-LTA trajectory. SD-controlled refinement produces logical grids as large as approximately $1121^3$. Sparse retained fields fit comfortably in memory, but two pre-LD7 algorithms did not:

1. the exact periodic-spread diagnostic evaluated every frame with a multi-start torus mean;
2. optimized sparse convolution generated arrays proportional to every source-node/stencil pair.

LD7 separates **grid estimation** from **density estimation**:

- a bounded, deterministic randomized frame subsample estimates positional spread;
- every selected trajectory frame still contributes to the final density;
- convolution and planning stream bounded source-group batches into sparse blocks.

No grid interval, bandwidth, Gaussian tail tolerance, density mass, or HDR definition is relaxed to satisfy resources.

## 2. Preserved estimator

For weighted periodic samples $(\mathbf f_s,w_s)$, the production field remains

$$
\rho = \frac{1}{\Delta V}\,G_h * C_h\!\left(\sum_s w_s\,\delta_{\mathbf f_s}\right),
$$

where $C_h$ is periodic trilinear cloud-in-cell deposition and $G_h$ is the canonical discrete periodized Gaussian stencil. The final normalization satisfies

$$
\sum_{\mathbf i}\rho_{\mathbf i}\Delta V = \sum_s w_s.
$$

LD7 changes only how the spread diagnostic and sparse convolution are executed.

## 3. Public options

### 3.1 Spread-estimation options

```python
DensityResolutionOptions(
    spread_sampling_strategy="stratified_random",  # or "all"
    spread_sample_size=128,
    spread_sample_seed=0,
)
```

These options are also exposed by `AtomicDensityOptions` and `FrameworkDensityOptions`.

Constraints:

- `spread_sample_size >= 2`;
- `spread_sample_seed` is an integer;
- `spread_sampling_strategy` is `"all"` or `"stratified_random"`;
- when the source frame count does not exceed the requested sample size, all frames are used.

### 3.2 Sparse execution options

```python
DensityOptimizationOptions(
    sparse_evaluation_mode="optimized",
    sparse_pair_chunk_size=262_144,
    sparse_group_batch_size=8,
    cache_stencil_supports=True,
)
```

`spare_group_batch_size` bounds the number of independent source groups—normally atoms, framework vertices, or framework edges—processed together.

## 4. Deterministic stratified-random spread sample

Let a trajectory contain $T$ ordered frames with normalized weights $a_t$, and let $m<T$ be the requested spread sample size. Divide the ordered frames into $m$ contiguous, equal-count temporal strata

$$
I_j = [e_j,e_{j+1}),\qquad
 e_j=\left\lfloor\frac{jT}{m}\right\rfloor.
$$

Within each stratum, draw one frame with probability proportional to its local frame weight. Assign the selected frame the complete stratum weight

$$
A_j = \sum_{t\in I_j}a_t.
$$

The expensive periodic-mean diagnostic is then evaluated on the $m$ selected frames using weights $A_j$.

This is an adaptation of standard stratified random sampling [1]. The temporal strata, deterministic NumPy generator, seed policy, and transfer of the full stratum weight to one selected frame are mdstats-specific.

### 4.1 Scientific policy

The sample is used **only** to resolve the positional-spread statistic and hence the grid/bandwidth. The density samples remain the complete requested frame collection.

For reproducibility, field metadata records:

- source and sampled frame counts;
- sample fraction;
- sampled source-frame indices;
- strategy and seed;
- resulting item SDs and selected quantile.

### 4.2 Reliability gate

For the Na-LTA acceptance trajectory, 128 stratified-random frames must reproduce the all-frame or converged-reference SD quantile closely enough that the resolved grid differs by no more than one practical refinement step. Focused synthetic tests require the sampled reference SD to agree within 2.5%.

## 5. Bounded block-streaming convolution

### 5.1 Pre-LD7 failure

The earlier optimized path generated

```python
target_flat = empty(kernel_pair_count)
pair_values = empty(kernel_pair_count)
```

before reduction. Peak memory therefore remained $O(P)$, where

$$
P=N_{\mathrm{CIC}}N_{\mathrm{stencil}}.
$$

For the 1,300-frame oxygen field, $P\approx5.6\times10^8$, making the temporary arrays larger than the runtime memory budget.

### 5.2 Two-pass block algorithm

For one source-group batch:

1. generate at most `sparse_pair_chunk_size` periodic target pairs;
2. map targets to logical block IDs;
3. mark the exact active target-block set;
4. allocate only those block-value arrays;
5. replay the same bounded pair stream;
6. reduce each chunk directly into block-local scalar slots;
7. extract positive logical nodes in deterministic global order;
8. normalize to the exact batch measure.

Peak package-owned memory is bounded by

$$
O(BV + P_c + N_s + N_k),
$$

where $B$ is the active block count, $V$ the block volume, $P_c$ the pair-chunk bound, $N_s$ the occupied CIC-node count, and $N_k$ the stencil support size. It is no longer proportional to all $P$ pairs.

### 5.3 Reduction policy

Small and reference-scale fields preserve stable `numpy.add.at` accumulation in the declared stencil-major/source-major order. Large batches may use a bounded block-local `numpy.bincount` reduction when the complete active block-slot vector is below the certified bound. The implementation choice is recorded in metadata.

## 6. Exact source-group batching

Density evaluation is linear. Partition source groups into deterministic ascending batches $S_b$:

$$
\rho = \sum_b \rho_b.
$$

Each batch:

- uses the same logical grid, cell, Gaussian support, and tail tolerance;
- carries its exact original sample weights;
- is normalized to its own measure;
- is evaluated with bounded block streaming.

The batch fields are merged by stable logical-node index reduction and corrected once to the exact total measure. Batch order is ascending source-group ID. The resulting metadata records batch count, source-group count, batch size, cumulative kernel pairs, peak batch workspace, and merge order.

Source groups are:

- selected atom index for atomic occupancy;
- framework vertex identity for vertex occupancy;
- framework edge or retained path identity for arc-length density.

## 7. Group-batched Phase-B planning

Transactional planning must predict the execution that realization will perform. LD7 therefore plans each deterministic group batch separately, unions exact target-node sets, and records:

- cumulative kernel-pair count;
- peak batch kernel-pair count;
- group count and batch count;
- final target-node and block-packing counts;
- bounded transient memory based on one batch, not all pairs.

The union is exact:

$$
\mathcal A = \bigcup_b \mathcal A_b.
$$

No scalar block values are allocated during planning.

## 8. Data and serialization contracts

`PeriodicSpreadDiagnostics` advances to

```text
mdstats.periodic-spread-diagnostic.v2
```

and adds immutable sampling provenance. `DensityOptimizationOptions` adds `sparse_group_batch_size`, with canonical JSON round trips and a default of 8.

The framework-dynamics scene schema advances to

```text
mdstats.framework-dynamics-scene.v14
```

because Phase-B plans and realized-field metadata now expose group-batched planning and spread-sampling provenance.

## 9. Resource and failure policy

The implementation must fail before unapproved allocation when any of these limits is exceeded:

- CIC contributions;
- stencil candidates;
- cumulative kernel pairs;
- pair-chunk workspace;
- active target blocks and block slots;
- planning bytes;
- retained field bytes.

Changing `sparse_group_batch_size` or `sparse_pair_chunk_size` may change performance and roundoff-scale reduction grouping, but not the logical grid, kernel, total measure, source samples, or declared density units.

## 10. Na-LTA 1,300-frame acceptance benchmark

Configuration:

- first 1,300 frames of `TRAJECTORY(3)`;
- $dt=1\ \mathrm{fs}$;
- framework-registered coordinates;
- all frames used for density;
- 128 stratified-random frames used for SD estimation;
- SD quantile 0.10;
- target artificial width/SD ratio 0.5;
- canonical discrete Gaussian, tail tolerance $10^{-3}$;
- $16^3$ blocks, eight source groups per batch;
- 4 GiB workspace limit.

Measured density-preparation results on the validation runtime:

| Species | Grid | Time | Cumulative kernel pairs | Integral |
|---|---:|---:|---:|---:|
| Na | $525^3$ | 13.74 s | 96,251,957 | 24 |
| Si | $1121^3$ | 33.42 s | 164,431,073 | 24 |
| Al | $1038^3$ | 16.56 s | 158,246,794 | 24 |
| O | $690^3$ | 60.15 s | 558,840,991 | 96 |
| **Total** | — | **125.28 s** | **977,770,815** | **168** |

The benchmark includes density preparation, not three-shell isosurface extraction or browser serialization.

## 11. Required tests

- deterministic sampled indices for a fixed seed;
- complete temporal-stratum coverage;
- all-frame fallback when $T\le m$;
- sampled SD agreement with the all-frame reference;
- exact CIC and active-node identities on reference fixtures;
- bounded scatter workspace independent of cumulative pair count;
- group-batched versus monolithic field agreement;
- group-batched planning union equal to monolithic target support;
- exact integrated measure after merging;
- deterministic source-group ordering;
- atomic, framework-vertex, and framework-edge execution;
- explicit `sampling_strategy="all"` compatibility;
- unchanged dense path and renderer contracts.

## 12. References

1. W. G. Cochran, *Sampling Techniques*, 3rd ed., Wiley, 1977. Stratified random sampling is adapted for weighted ordered trajectory frames.
2. R. W. Hockney and J. W. Eastwood, *Computer Simulation Using Particles*, Adam Hilger, 1988; reprint DOI: 10.1201/9780367806934. Periodic cloud-in-cell deposition.

The bounded block-streaming reduction, source-group batching, exact sparse merge, and transactional planning integration are original mdstats engineering designs.
