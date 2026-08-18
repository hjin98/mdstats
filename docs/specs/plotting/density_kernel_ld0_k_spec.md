---
title: "LD0-K Canonical Discrete Density-Kernel Specification"
subtitle: "One periodized node stencil for exact dense direct and FFT convolution"
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

This specification implements architecture gate **LD0-K** for `mdstats 0.19.43a0`.
It is subordinate to the *Dynamical Framework and Atomic Density Architecture
Standard*.

The gate introduces the canonical smoothing operator
`discrete_periodized_v1` alongside the unchanged compatibility operator
`legacy_spectral_v1`.

This gate changes no default. Existing calls continue to use
`legacy_spectral_v1` unless the canonical operator is selected explicitly.

This gate does not implement:

- the effective CIC-plus-stencil broadening policy owned by LD0-B;
- local-sparse storage or sparse convolution;
- automatic backend selection;
- framework-edge quadrature refinement;
- mesh or HDR algorithm changes.

# Motivation

The previous dense estimator deposits weighted samples by periodic trilinear
cloud-in-cell assignment and smooths the node masses with a finite-mode spectral
Gaussian multiplier. A future sparse backend cannot apply that globally supported
finite spectral operator locally without approximation.

LD0-K therefore defines one finite-support discrete periodized node stencil. The
dense reference backend can apply this stencil either by direct circular convolution
or by FFT circular convolution. A later sparse backend will scatter the same stored
weights from occupied CIC nodes. The estimator boundary is then explicit and testable.

# Scientific operator

Let the row-vector display cell be

$$
H=\begin{bmatrix}\mathbf a_1\\\mathbf a_2\\\mathbf a_3\end{bmatrix},
$$

and let the logical grid shape be

$$
\mathbf N=(N_1,N_2,N_3).
$$

For an integer grid-image vector $\mathbf q\in\mathbb Z^3$, define

$$
\Delta\mathbf x_{\mathbf q}
=
\left(\frac{q_1}{N_1},\frac{q_2}{N_2},\frac{q_3}{N_3}\right)H.
$$

The voxel volume is

$$
\Delta V=\frac{|\det H|}{N_1N_2N_3}.
$$

For $\sigma>0$, the unnormalized retained contribution is

$$
a_{\mathbf q}
=
\Delta V\frac{1}{(2\pi\sigma^2)^{3/2}}
\exp\left(-\frac{\|\Delta\mathbf x_{\mathbf q}\|_2^2}{2\sigma^2}\right)
\mathbf 1\!\left[\|\Delta\mathbf x_{\mathbf q}\|_2\le r_{\mathrm{cut}}\right].
$$

The cutoff is selected from the radial mass of a three-dimensional isotropic
Gaussian. Since $r^2/\sigma^2\sim\chi_3^2$,

$$
r_{\mathrm{cut}}
=
\sigma\sqrt{F^{-1}_{\chi_3^2}(1-\varepsilon)},
$$

where

$$
10^{-15}\le\varepsilon\le10^{-3}.
$$

Each $\mathbf q$ is mapped to the canonical periodic node offset

$$
\boldsymbol\delta=\mathbf q\bmod\mathbf N.
$$

All retained image contributions mapping to the same canonical offset are summed:

$$
A_{\boldsymbol\delta}
=
\sum_{\mathbf q\equiv\boldsymbol\delta\ (\mathrm{mod}\ \mathbf N)}a_{\mathbf q}.
$$

With

$$
S_A=\sum_{\boldsymbol\delta}A_{\boldsymbol\delta},
$$

the canonical stencil is

$$
g_{\boldsymbol\delta}=\frac{A_{\boldsymbol\delta}}{S_A}.
$$

Thus

$$
g_{\boldsymbol\delta}\ge0,
\qquad
\sum_{\boldsymbol\delta}g_{\boldsymbol\delta}=1.
$$

For deposited node masses $m_j$, the smoothed node masses are

$$
\widetilde m_g
=
\sum_jm_jg_{g-j}.
$$

The density is

$$
\rho_g=\frac{\widetilde m_g}{\Delta V}.
$$

For $\sigma=0$, the operator is exactly the identity:

$$
g_{\mathbf 0}=1,
\qquad
g_{\boldsymbol\delta\ne\mathbf 0}=0.
$$

# Conservative support enumeration

The implementation enumerates integer vectors $\mathbf q$, not separate canonical
offsets and image vectors. This guarantees that every retained periodic image
contribution is counted exactly once.

From

$$
\mathbf f=\Delta\mathbf x H^{-1},
$$

and $\|\Delta\mathbf x\|_2\le r_{\mathrm{cut}}$, a conservative coordinate bound is

$$
|f_i|\le r_{\mathrm{cut}}\|H^{-1}_{:,i}\|_2.
$$

Therefore

$$
|q_i|
\le
B_i
=
\left\lceil
N_i r_{\mathrm{cut}}\|H^{-1}_{:,i}\|_2
\right\rceil.
$$

The rectangular integer box $[-B_1,B_1]\times[-B_2,B_2]\times[-B_3,B_3]$
is scanned in deterministic lexicographic order and filtered by the exact Cartesian
metric. Enumeration is chunked so that temporary arrays are bounded independently of
the total candidate count.

# Data structures

## `PeriodicGaussianStencil`

```python
@dataclass(frozen=True, slots=True)
class PeriodicGaussianStencil:
    grid_shape: tuple[int, int, int]
    display_cell: NDArray[np.float64]
    gaussian_bandwidth: float
    kernel_tail_tolerance: float
    cutoff_radius: float
    values: NDArray[np.float64]
    active_flat_indices: NDArray[np.int64]
    active_weights: NDArray[np.float64]
    pre_normalization_sum: float
    normalization_factor: float
    periodic_image_contribution_count: int
    covariance: NDArray[np.float64]
    metadata: FrozenJSONMapping
    schema_version: str
```

All arrays are C-contiguous, defensive, read-only copies. `values` has exactly the
logical grid shape. `active_flat_indices` are strictly increasing C-order flat
indices of positive canonical stencil entries. `active_weights` are aligned with
those indices.

The covariance is computed from the unaggregated retained image contributions:

$$
C_g
=
\frac{1}{S_A}
\sum_{\mathbf q}a_{\mathbf q}
\Delta\mathbf x_{\mathbf q}\Delta\mathbf x_{\mathbf q}^{T}.
$$

It is stored for LD0-B but does not yet alter resolution selection.

## Diagnostics

Every canonical field records:

```text
smoothing_operator = discrete_periodized_v1
kernel_tail_tolerance
continuous_tail_mass_bound
kernel_cutoff_radius
stencil_pre_normalization_sum
stencil_normalization_factor
stencil_offset_count
periodic_image_contribution_count
stencil_covariance_cartesian
canonical_convolution_method = fft
canonical_negative_roundoff_clipped
canonical_post_convolution_normalization_factor
```

`1-S_A` is not called an omitted discrete mass because it combines continuous-tail
truncation and sampling quadrature error.

# Public numerical functions

```python
build_periodic_gaussian_stencil(
    grid_shape,
    display_cell,
    gaussian_bandwidth,
    *,
    kernel_tail_tolerance=1e-8,
) -> PeriodicGaussianStencil
```

```python
convolve_periodic_stencil_direct(
    mass_grid,
    stencil,
) -> NDArray[np.float64]
```

```python
convolve_periodic_stencil_fft(
    mass_grid,
    stencil,
) -> NDArray[np.float64]
```

```python
smooth_periodic_node_masses(
    mass_grid,
    display_cell,
    gaussian_bandwidth,
    kernel_options,
) -> tuple[NDArray[np.float64], FrozenJSONMapping]
```

The direct implementation is a correctness oracle. Production dense canonical fields
use FFT circular convolution.

# Floating-point completion policy

The canonical stencil is nonnegative and normalized before convolution.

After FFT convolution:

1. define
   $$
   \tau_-=64\epsilon_{\mathrm{mach}}
   \max\left(1,\max_g|\widetilde m_g|\right);
   $$
2. reject values below $-\tau_-$ as a numerical failure;
3. set only negative values in $[-\tau_-,0)$ to zero;
4. do not clip positive tails;
5. renormalize the smoothed node masses to the original deposited mass.

Direct convolution passes through the same completion function. This keeps direct
and FFT comparisons under one declared policy while preserving all positive canonical
stencil mass.

The legacy operator keeps its historical clipping and renormalization behavior
unchanged.

# Operator selection and compatibility

| Backend | `legacy_spectral_v1` | `discrete_periodized_v1` |
|---|---:|---:|
| `dense` | supported and default | supported explicitly |
| `local_sparse` | rejected | reserved for LD1-B |
| `auto` | rejected before LD4 | rejected before LD4 |

The default operator remains `legacy_spectral_v1` in this release.

# Planning integration

For a canonical dense field with $\sigma>0$:

```text
stencil_value_count = logical_node_count
```

because production FFT convolution materializes one dense stencil array. For the
identity path $\sigma=0$:

```text
stencil_value_count = 0
```

Phase A uses the logical node count as the canonical stencil upper bound. Phase C
checks the scene-wide sum against `max_density_stencil_values`.

Planning metadata records the requested operator for every field and the set of
operators present in the approved scene. Mixed atomic/framework operator choices are
permitted because every field is scientifically self-describing.

# Inputs and constraints

- `grid_shape` contains three positive integers.
- `display_cell` is finite, shape `(3, 3)`, and nonsingular.
- `gaussian_bandwidth` is finite and nonnegative.
- `kernel_tail_tolerance` lies in `[1e-15, 1e-3]`.
- `mass_grid` is finite, nonnegative within numerical tolerance, and has the same
  shape as the stencil.
- Full three-dimensional periodicity is required by the current density backend.

# Determinism

For fixed inputs:

- support bounds are deterministic;
- integer vectors are enumerated lexicographically;
- canonical aggregation is deterministic;
- active indices are C-order sorted;
- direct accumulation order is fixed;
- metadata field ordering is canonical;
- repeated builds are byte-identical on one NumPy/SciPy platform.

# Error handling

Raise `GraphStyleError` for invalid user kernel parameters.

Raise `GraphAdapterError` for malformed cells, shapes, arrays, zero normalization, or
FFT negativity beyond the declared roundoff tolerance.

Raise `GraphComplexityError` if the conservative support-enumeration candidate count
exceeds the implementation safety bound before scanning begins.

# Required focused tests

## Stencil construction

1. identity stencil for `sigma=0`;
2. nonnegative normalized stencil;
3. deterministic repeat build;
4. orthorhombic and skewed cells;
5. a support radius spanning multiple periodic images;
6. monotone cutoff growth as tail tolerance decreases;
7. exact active-index/value alignment;
8. covariance symmetry and positive semidefiniteness within tolerance.

## Convolution

For orthorhombic, LTA-primitive, random positive mass, CIC mass, and multiple-image
support cases:

```text
direct-vs-FFT relative L1 <= 5e-12
direct-vs-FFT relative L-infinity <= 2e-11
stencil sum absolute error <= 5e-15
integral error <= 5e-13 * max(1, total_measure)
```

## Integration

- atomic canonical fields integrate to selected occupancy;
- framework-vertex canonical fields integrate to projected vertex count;
- framework-edge canonical fields integrate to mean retained arc length;
- integer periodic translations are invariant;
- canonical metadata and planning counts are present;
- `legacy_spectral_v1` remains the default and numerically identical to
  `mdstats 0.19.42a0` fixtures;
- canonical and legacy operators may differ on under-resolved inputs without either
  being mislabeled.

# Acceptance gate

LD0-K passes only if:

1. all focused tests satisfy the fixed tolerances above;
2. the legacy default path is exactly preserved on matched fixtures;
3. `discrete_periodized_v1` works for atomic, framework-vertex, and framework-edge
   dense fields;
4. the zero-bandwidth path allocates no Gaussian stencil and returns exact CIC masses;
5. planning and realized metadata identify the operator consistently;
6. no default operator migration occurs;
7. documentation and code distinguish standard Fourier convolution and Gaussian
   probability background from the project-specific canonical stencil policy.

# Borrowed, standard, and project-specific material

- **Borrowed algorithm:** periodic trilinear cloud-in-cell assignment follows
  Hockney and Eastwood.
- **Standard mathematical background:** FFT circular convolution, the isotropic
  Gaussian density, and the $\chi_3^2$ radial law.
- **Project-specific design:** finite Cartesian support, canonical image aggregation,
  exact dense/sparse operator identity, diagnostics, roundoff completion, migration
  policy, and gate tolerances.

# References

1. R. W. Hockney and J. W. Eastwood, *Computer Simulation Using Particles*,
   Adam Hilger, 1988. Reprint DOI: 10.1201/9780367806934.
