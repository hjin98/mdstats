---
title: "LD0-B Effective Density-Broadening Specification"
subtitle: "CIC-phase covariance, canonical-stencil covariance, and versioned adaptive resolution"
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

This specification implements architecture gate **LD0-B** for `mdstats 0.19.44a0`.
It is subordinate to the *Dynamical Framework and Atomic Density Architecture
Standard*.

The gate introduces the explicit broadening metric
`effective_cic_stencil_rms_v1`. It combines the covariance of periodic trilinear
cloud-in-cell assignment with the covariance of the canonical
`discrete_periodized_v1` smoothing stencil.

The existing `gaussian_sigma_v1` metric remains the default. No existing call changes
its resolved grid or density values unless the new metric is selected explicitly.

This gate does not implement:

- local-sparse storage or sparse convolution;
- automatic dense/sparse backend selection;
- framework-edge quadrature refinement;
- probability-shell or mesh changes;
- sample-dependent Gaussian bandwidths.

# Scientific ownership

The trilinear cloud-in-cell assignment follows the particle-mesh construction of
Hockney and Eastwood (1988). Covariance addition for centered independent smoothing
kernels is standard probability theory. The phase-resolved periodic CIC covariance,
its combination with the canonical stencil, the deterministic refinement search, and
the migration policy are project-specific derivations and policies.

# Logical sampling basis

Let the row-vector display cell be

$$
H=\begin{bmatrix}\mathbf a_1\\\mathbf a_2\\\mathbf a_3\end{bmatrix},
$$

and let the logical grid shape be

$$
\mathbf N=(N_1,N_2,N_3).
$$

The real-space sampling-basis rows are

$$
\mathbf b_a=\frac{\mathbf a_a}{N_a}.
$$

For a folded fractional sample $\mathbf f_s$, define the grid phase

$$
\mathbf d_s
=
\mathbf N\odot\mathbf f_s
-
\left\lfloor\mathbf N\odot\mathbf f_s\right\rfloor,
\qquad 0\le d_{sa}<1.
$$

The phase computation uses exactly the same logical-node convention as periodic CIC
deposition.

# CIC assignment covariance

Along axis $a$, CIC assigns the sample to the lower node with probability
$1-d_{sa}$ and to the upper node with probability $d_{sa}$. Relative to the sample,
the two displacements are

$$
-d_{sa}\mathbf b_a
\quad\text{and}\quad
(1-d_{sa})\mathbf b_a.
$$

Their weighted mean is zero and their covariance contribution is

$$
C_{\mathrm{CIC},s,a}
=
d_{sa}(1-d_{sa})\mathbf b_a\mathbf b_a^T.
$$

Thus

$$
C_{\mathrm{CIC},s}
=
\sum_{a=1}^{3}
 d_{sa}(1-d_{sa})\mathbf b_a\mathbf b_a^T.
$$

For nonnegative source weights $w_s$ with positive total weight, define

$$
\omega_s=\frac{w_s}{\sum_t w_t},
$$

and

$$
\overline C_{\mathrm{CIC}}
=
\sum_s\omega_sC_{\mathrm{CIC},s}.
$$

Atomic and framework-vertex occupancy use repeated frame weights. Framework-edge
quadrature uses its arc-length quadrature weights when reporting the realized edge
field diagnostic. When framework-edge resolution is inherited from framework
vertices, metadata records
`resolution_reference_source="framework_vertices"`.

# Canonical-stencil covariance

For the unaggregated retained image contributions $a_{\mathbf q}$ defined by
`discrete_periodized_v1`, let

$$
\Delta\mathbf x_{\mathbf q}
=
\left(\frac{q_1}{N_1},\frac{q_2}{N_2},\frac{q_3}{N_3}\right)H.
$$

The normalized canonical-stencil covariance is

$$
C_g
=
\frac{
\sum_{\mathbf q}a_{\mathbf q}
\Delta\mathbf x_{\mathbf q}
\Delta\mathbf x_{\mathbf q}^{T}
}{
\sum_{\mathbf q}a_{\mathbf q}
}.
$$

It is evaluated by the same bounded support enumeration used to build the canonical
stencil, but a covariance-only path must not allocate the dense stencil array.

For $\sigma=0$,

$$
C_g=0.
$$

# Effective artificial broadening

The total artificial covariance is

$$
C_{\mathrm{art}}
=
\overline C_{\mathrm{CIC}}+C_g.
$$

The scalar broadening metric is the isotropic RMS component width

$$
s_{\mathrm{art}}
=
\sqrt{\frac{\operatorname{tr}(C_{\mathrm{art}})}{3}}.
$$

The component diagnostics are

$$
s_{\mathrm{CIC}}
=
\sqrt{\frac{\operatorname{tr}(\overline C_{\mathrm{CIC}})}{3}},
\qquad
s_g
=
\sqrt{\frac{\operatorname{tr}(C_g)}{3}}.
$$

The adaptive target is

$$
s_{\mathrm{art}}\le\alpha s_q,
$$

where $s_q$ is the approved positional-spread reference and the default is
$\alpha=0.5$.

# Compatibility and selection rules

The valid implemented combinations are:

| Broadening metric | Smoothing operator | Status |
|---|---|---|
| `gaussian_sigma_v1` | `legacy_spectral_v1` | supported and default |
| `gaussian_sigma_v1` | `discrete_periodized_v1` | supported |
| `effective_cic_stencil_rms_v1` | `discrete_periodized_v1` | supported explicitly |
| `effective_cic_stencil_rms_v1` | `legacy_spectral_v1` | rejected |

The effective metric is not a diagnostic for the legacy spectral operator because its
stencil covariance is defined by `discrete_periodized_v1`.

Explicit `grid_shape` and explicit `gaussian_bandwidth` remain authoritative. If their
resolved effective width exceeds the target, the implementation records the failure
and emits a warning; it does not change the explicit value.

# Automatic resolution search

The effective-width search applies only when:

1. `adaptive_smearing=True`;
2. the broadening metric is `effective_cic_stencil_rms_v1`;
3. no explicit `grid_shape` is supplied;
4. no explicit `gaussian_bandwidth` is supplied;
5. the positional-spread target is finite and valid.

Starting from the nominal interval, the implementation evaluates the exact effective
width for the resolved logical shape. On failure, it proposes a smaller interval from
the local scale estimate

$$
h_{n+1}
=
h_n\min\left(0.9,0.98\frac{\alpha s_q}{s_{\mathrm{art},n}}\right).
$$

If this proposal leaves the logical shape unchanged, the next exact shape-transition
interval is used. The process continues until a passing shape is found or the dense
voxel budget is reached. A deterministic bracket refinement then seeks a coarser
passing interval while retaining one certified passing shape.

Every accepted automatic result is re-evaluated and must satisfy the target within

$$
\tau_s
=
5\times10^{-13}\max(1,\alpha s_q).
$$

If the finest shape allowed by the dense budget fails, the result is marked
`adaptive_smearing_budget_limited=True` and the unresolved ratio is recorded.

# Zero-spread and zero-bandwidth policies

If $s_q=0$, no positive finite target is defined:

```text
adaptive_target_defined = False
adaptive_refinement_applied = False
nominal or explicit resolution retained
warning and metadata emitted
```

For $\sigma=0$, the stencil covariance is zero but CIC covariance remains. Therefore

$$
s_{\mathrm{art}}=s_{\mathrm{CIC}}.
$$

An explicit zero bandwidth is preserved. The implementation reports whether the CIC
width alone exceeds the positional target.

# Data structures

## `ArtificialBroadeningDiagnostic`

```python
@dataclass(frozen=True, slots=True)
class ArtificialBroadeningDiagnostic:
    grid_shape: tuple[int, int, int]
    sample_count: int
    source_weight_sum: float
    phase_variance_coefficients: NDArray[np.float64]  # shape (3,)
    cic_covariance: NDArray[np.float64]                # shape (3, 3)
    stencil_covariance: NDArray[np.float64]            # shape (3, 3)
    total_covariance: NDArray[np.float64]              # shape (3, 3)
    cic_rms: float
    stencil_rms: float
    effective_rms: float
    metadata: FrozenJSONMapping
```

All arrays are defensive, C-contiguous, finite, and read-only.

## `PeriodicGaussianStencilMoments`

```python
@dataclass(frozen=True, slots=True)
class PeriodicGaussianStencilMoments:
    grid_shape: tuple[int, int, int]
    display_cell: NDArray[np.float64]
    gaussian_bandwidth: float
    kernel_tail_tolerance: float
    cutoff_radius: float
    pre_normalization_sum: float
    normalization_factor: float
    periodic_image_contribution_count: int
    covariance: NDArray[np.float64]
    metadata: FrozenJSONMapping
```

This record uses the canonical support enumerator without allocating a dense logical
stencil.

# Metadata

Fields using the effective metric record:

```text
broadening_metric
effective_artificial_rms
cic_assignment_rms
canonical_stencil_rms
cic_covariance_cartesian
stencil_covariance_cartesian
artificial_covariance_cartesian
cic_phase_variance_coefficients
broadening_sample_count
broadening_source_weight_sum
adaptive_target_width
adaptive_target_achieved
adaptive_target_ratio
resolution_reference_source
```

Atomic and framework-vertex fields use their own samples as the resolution reference.
Framework-edge fields additionally report their own realized edge-sample artificial
covariance while retaining `resolution_reference_source="framework_vertices"`.

# Public API

The existing option record is used:

```python
DensityResolutionOptions(
    broadening_metric="effective_cic_stencil_rms_v1",
)

DensityKernelOptions(
    smoothing_operator="discrete_periodized_v1",
    kernel_tail_tolerance=1.0e-8,
)
```

No default changes in LD0-B.

# Validation

LD0-B passes only if:

1. analytic CIC covariance matches brute-force eight-node assignment covariance with
   relative Frobenius error $\le5\times10^{-13}$;
2. covariance-only canonical-stencil moments match the full stencil covariance with
   relative Frobenius error $\le5\times10^{-13}$;
3. on-node CIC phase produces exactly zero CIC covariance;
4. half-node phase produces the analytic maximum
   $\frac14\sum_a\mathbf b_a\mathbf b_a^T$;
5. weighted atomic, framework-vertex, and edge-quadrature diagnostics conserve source
   weighting semantics;
6. every automatically accepted finite target satisfies the declared effective-width
   inequality;
7. budget-limited, explicit-grid, explicit-bandwidth, zero-spread, and zero-bandwidth
   cases follow the declared warning and metadata policies;
8. `gaussian_sigma_v1` plus `legacy_spectral_v1` remains byte-for-byte compatible with
   `mdstats 0.19.43a0`;
9. the default broadening metric and default smoothing operator do not change.

# Failure policy

The implementation fails before density allocation when:

- the effective metric is paired with `legacy_spectral_v1`;
- sample positions or weights are invalid;
- source weights are negative or have nonpositive total weight;
- canonical support enumeration exceeds its declared complexity limit;
- a resolved automatic shape exceeds the field voxel budget.

An unresolved target caused by an explicit input or finite resource budget is reported
honestly and is not converted into an exception unless the existing resource limit is
itself exceeded.

# References

1. Hockney, R. W., and J. W. Eastwood. *Computer Simulation Using Particles*.
   Taylor & Francis, 1988. CIC assignment is adapted from this source.
2. The covariance addition and Gaussian covariance identities are standard
   probability background. The periodic phase-resolved combination and adaptive
   selection policy are project-specific.
