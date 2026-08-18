---
title: "LD1-A Sparse CIC and Canonical-Convolution Reference Specification"
subtitle: "Deterministic flat-node aggregation, sparse stencil scatter, normalization, and HDR diagnostics"
author: "mdstats development specification"
date: "2026-07-20"
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

This specification implements architecture gate **LD1-A** for `mdstats 0.19.45a0`.
It is subordinate to the *Dynamical Framework and Density Plotting Architecture
Standard*.

The gate introduces a deliberately simple sparse numerical oracle:

$$
\text{weighted periodic samples}
\rightarrow
\text{sorted CIC node masses}
\rightarrow
\text{sparse canonical stencil scatter}
\rightarrow
\text{normalized flat-node field}.
$$

The representation stores sorted logical flat indices and positive values. It is not
the production block-sparse backend. Block packing, partial-block masks, transactional
sparse storage planning, and public backend selection belong to LD1-B and LD4.

This gate does not change the default dense backend, the default
`legacy_spectral_v1` operator, scene composition, probability-shell meshing, or
framework-edge quadrature.

# Scientific ownership and citations

Periodic trilinear cloud-in-cell assignment follows the particle-mesh construction of
Hockney and Eastwood (1988). Highest-density-region thresholds follow Hyndman (1996).
The finite-support `discrete_periodized_v1` stencil was specified and implemented in
LD0-K. The sparse flat-node representation, deterministic accumulation order,
resource policy, residual normalization, and debugging conversion limits are
project-specific mdstats definitions.

# Inputs

## Weighted samples

The only source record is the existing immutable
`PeriodicWeightedSamples3D`:

```python
PeriodicWeightedSamples3D(
    fractional_positions: float64[n_samples, 3],  # folded to [0, 1)
    weights: float64[n_samples],                  # nonnegative
    source_provenance: DensitySourceProvenance,
    total_measure: float,
    measure_kind: "occupancy" | "arc_length",
    measure_units: str,
    sample_group_ids: int64[n_samples] | None,
)
```

The weights must satisfy

$$
\left|\sum_s w_s-M\right|
\le
5\times10^{-13}\max(1,M),
$$

where $M$ is `total_measure`.

## Grid and cell

The logical shape is

$$
\mathbf N=(N_1,N_2,N_3),\qquad N_i\in\mathbb N^+.
$$

Logical node $(i,j,k)$ lies at

$$
\mathbf f_{ijk}
=
\left(\frac{i}{N_1},\frac{j}{N_2},\frac{k}{N_3}\right).
$$

The row-vector display cell $H\in\mathbb R^{3\times3}$ must be finite and
nonsingular. Its voxel volume is

$$
\Delta V=\frac{|\det H|}{N_1N_2N_3}.
$$

## Canonical kernel

LD1-A supports only `discrete_periodized_v1`. The Gaussian bandwidth obeys
$\sigma\ge0$ and the kernel-tail tolerance lies in
$[10^{-15},10^{-3}]$.

# Sparse-only canonical stencil support

LD0-K stores both a dense logical stencil and its active support. LD1-A adds
`PeriodicGaussianStencilSupport`, which stores only:

```python
PeriodicGaussianStencilSupport(
    grid_shape,
    display_cell,
    gaussian_bandwidth,
    kernel_tail_tolerance,
    cutoff_radius,
    active_flat_indices,   # sorted, unique int64
    active_weights,        # positive float64, sum exactly one within tolerance
    pre_normalization_sum,
    normalization_factor,
    periodic_image_contribution_count,
    covariance,
    metadata,
)
```

Candidate integer images are enumerated using the reciprocal-plane bounds already
specified by LD0-K. Retained image contributions are mapped to canonical periodic
flat indices and accumulated in image-enumeration order. The final origin weight
receives the residual correction

$$
g_0\leftarrow g_0+\left(1-\sum_\delta g_\delta\right).
$$

No logical dense stencil is allocated. A guarded `to_dense_values(max_nodes=...)`
helper exists only for bounded testing and debugging.

For $\sigma=0$, the support is the exact identity:

$$
\mathcal S=\{0\},\qquad g_0=1.
$$

# Deterministic sparse CIC aggregation

For one folded sample $\mathbf f_s$, define

$$
\mathbf y_s=\mathbf N\odot\mathbf f_s,
\qquad
\mathbf i_s=\lfloor\mathbf y_s\rfloor,
\qquad
\mathbf d_s=\mathbf y_s-\mathbf i_s.
$$

For $\boldsymbol\epsilon\in\{0,1\}^3$, the periodic target node is

$$
\mathbf n_{s\boldsymbol\epsilon}
=
(\mathbf i_s+\boldsymbol\epsilon)\bmod\mathbf N,
$$

with contribution

$$
m_{s\boldsymbol\epsilon}
=
w_s\prod_{a=1}^3
\begin{cases}
1-d_{sa}, & \epsilon_a=0,\\
d_{sa}, & \epsilon_a=1.
\end{cases}
$$

Contributions are generated in the fixed order

```text
(ox, oy, oz) lexicographic, then original sample order
```

and accumulated with unbuffered `float64` additions into sorted unique flat nodes.
Zero contributions are omitted. The deposited measure must satisfy

$$
\left|\sum_jm_j-M\right|
\le
5\times10^{-13}\max(1,M).
$$

The output is `SparseCICNodeMasses3D`.

# Sparse canonical convolution

Let occupied CIC nodes be $(j,m_j)$ and canonical stencil support be
$(\delta,g_\delta)$. Every pair contributes

$$
\widetilde m_{(j+\delta)\bmod\mathbf N}
\mathrel{+}=
m_jg_\delta.
$$

Pairs are generated in the fixed order

```text
stencil flat-index order, then occupied CIC flat-index order
```

so the addition order tracks the dense direct canonical convolution. Periodic target
indices are sorted only for storage; additions retain the declared pair order.

If the raw scattered measure is $M_{\mathrm{raw}}$, apply

$$
\beta=\frac{M}{M_{\mathrm{raw}}},
\qquad
m_g^{\mathrm{norm}}=\beta\widetilde m_g.
$$

A deterministic residual correction is applied to the first stored node. Density is
then

$$
\rho_g=\frac{m_g^{\mathrm{norm}}}{\Delta V}.
$$

The output is `SparseCanonicalDensityReference3D`, a flat-node reference field that
implements the backend-neutral scalar-field and periodic-node-access contracts.

# Highest-density-region details

For $0<q<1$, sort positive stored densities in descending order and choose the first
threshold $c_q$ satisfying

$$
\Delta V\sum_{\rho_g\ge c_q}\rho_g\ge qM.
$$

All exact ties at $c_q$ are included. `SparseHDRDetails` records:

- requested mass fraction;
- threshold;
- achieved mass fraction;
- selected node count;
- exact threshold-tie count;
- selected and total measures.

Implicit zero nodes do not alter a positive threshold for $q<1$.

# Public records and functions

```python
build_periodic_gaussian_stencil_support(...)
aggregate_periodic_cic_sparse(...)
scatter_periodic_stencil_sparse(...)
prepare_sparse_canonical_density_reference(...)
```

The main records are:

```python
PeriodicGaussianStencilSupport
SparseCICNodeMasses3D
SparseHDRDetails
SparseCanonicalDensityReference3D
```

All public arrays are C-contiguous defensive copies, read-only, shape-validated, and
finite. Sparse flat indices are strictly increasing and unique.

# Resource and failure policy

The reference path uses explicit hard limits:

```text
max_cic_contributions
max_stencil_candidate_contributions
max_kernel_pairs
max_workspace_bytes
max_nodes for debugging conversion
```

Before allocating contribution or pair vectors, the implementation computes a
conservative workspace bound. A request exceeding any limit raises
`GraphComplexityError` before the corresponding large allocation.

The reference path may allocate arrays proportional to the CIC contribution count or
kernel-pair count. It is therefore a correctness oracle, not the final scalable
backend. LD1-B must replace flat pair materialization with block-oriented production
storage while retaining LD1-A as a test oracle.

# Error cases

The implementation rejects:

1. nonfinite or nonfolded weighted samples;
2. negative weights or inconsistent total measure;
3. invalid logical shapes or singular cells;
4. noncanonical smoothing operators;
5. nonpositive sparse stored masses or densities;
6. mismatched CIC and stencil shapes;
7. resource-limit violations;
8. dense debugging conversion beyond `max_nodes`;
9. zero or destroyed measure after deposition or convolution.

# Validation matrix

Required fixtures are:

| Case | Required property |
|---|---|
| orthogonal off-grid samples | dense-direct agreement |
| LTA primitive cell | exact Cartesian metric and dense-direct agreement |
| face crossing | periodic continuity and dense-direct agreement |
| edge crossing | periodic continuity and dense-direct agreement |
| corner crossing | periodic continuity and dense-direct agreement |
| multiple images in support | canonical image aggregation |
| overlapping sources | deterministic duplicate aggregation |
| bimodal hopping | multimodal field and HDR agreement |
| independent ensemble | arbitrary nonnegative weights |
| $\sigma=0$ | exact identity convolution |

Acceptance against dense direct convolution of `discrete_periodized_v1` is:

```text
relative L1 field error                 <= 2e-11
relative L-infinity field error         <= 5e-11
absolute integral error                 <= 5e-13 * max(1, total_measure)
HDR threshold absolute difference       <= 5e-12 * max(1, reference maximum)
achieved HDR mass-fraction difference   <= 5e-13
```

Additional gates require:

- repeated identical inputs produce byte-identical sparse indices, values, and
  metadata;
- periodic integer translations agree within the field tolerances;
- sparse CIC agrees with dense CIC within $2\times10^{-16}$ absolute node mass;
- sparse-only stencil support agrees with the LD0-K dense stencil within
  $2\times10^{-16}$ absolute weight;
- every resource limit is exercised by a focused failure test;
- the unchanged dense legacy path remains compatible with `mdstats 0.19.44a0`.

# Non-objectives and next gate

LD1-A does not expose `grid_backend="local_sparse"` through production plotting
options. It does not pack blocks, serialize block fields, render sparse clouds, or
extract sparse meshes.

The next gate is **LD1-B**, which will implement production atomic block packing,
partial-block masks, transactional sparse preflight, public node access, structured
serialization, and the localized LTA storage benchmark.

# References

1. Hockney, R. W., and J. W. Eastwood. *Computer Simulation Using Particles*.
   Taylor & Francis, 1988. Periodic particle-mesh cloud-in-cell assignment.
2. Hyndman, R. J. "Computing and Graphing Highest Density Regions."
   *The American Statistician* **50** (1996): 120-126.
   DOI: 10.1080/00031305.1996.10474359.
