---
title: "Diffusion Estimation and MSD/VACF Consistency Specification"
subtitle: "G2/GK3 after H0: Explicit Plateau Selection and Signature-Checked Comparison"
author: "mdstats"
date: "2026-07-22"
geometry: margin=0.82in
fontsize: 10pt
toc: true
toc-depth: 3
numbersections: true
header-includes:
  - |
    \usepackage{amsmath}
    \usepackage{amssymb}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{microtype}
    \usepackage{xcolor}
    \usepackage{fvextra}
    \usepackage{hyperref}
    \DefineVerbatimEnvironment{Highlighting}{Verbatim}{breaklines,breakanywhere,commandchars=\\\{\}}
---

# Purpose and status

This document specifies the H0-hardened functions in

```text
mdstats/analysis/diffusion.py
```

```python
estimate_diffusion_plateau(...)
compare_msd_vacf_diffusion(...)
```

and the immutable `DiffusionEstimate` and `DiffusionComparisonResult` schemas.
The module consumes existing MSD and running Green-Kubo results. It does not
recompute trajectories, correlations, or transport integrals.

# Borrowed theory and numerical methods

For a physical subspace of rank $d$, the Einstein relation gives [1]

$$
M_B(t)\sim 2dD_Bt.
$$

Thus a linear slope $m_B$ yields

$$
D_B=\frac{m_B}{2d}.
$$

The compared VACF estimate follows Green [2] and Kubo [3]. The centered
ordinary-least-squares formulas used for descriptive slope diagnostics are
standard regression algebra. Explicit interval selection, refusal to infer an
uncertainty from adjacent running-integral samples, semantic-signature checking,
and the symmetric relative difference are mdstats policies.

# Explicit plateau estimate

## Public function

```python
def estimate_diffusion_plateau(
    running: VACFDiffusionResult,
    *,
    time_range_ps: tuple[float, float] | None = None,
    minimum_points: int = 8,
    slope_tolerance: float | None = None,
    method: Literal["explicit", "stable_window"] = "explicit",
) -> DiffusionEstimate:
    ...
```

Only `method="explicit"` is implemented. `"stable_window"` raises
`NotImplementedError` until a separately specified automatic-window stage.

The requested interval is inclusive within floating-point boundary tolerance
and must lie inside stored lag times. At least `minimum_points` selected samples
are required.

## Uniform-grid requirement

The current estimator is the arithmetic mean

$$
\widehat D
=
\frac{1}{N}\sum_{j=1}^{N}D(t_j).
$$

H0 requires the selected lag samples to be uniformly spaced. If their increments
are not equal within strict tolerance, the function raises. It does not allow a
dense region of an irregular grid to receive more implicit weight. A future
time-weighted interval estimator must use another method name.

## Diagnostics

The function stores descriptive values over the selected interval:

- mean, median, sample standard deviation, minimum, maximum, and span;
- endpoint drift;
- centered linear slope and intercept;
- $R^2$ and residual RMS;
- selected sample spacing; and
- an optional pass/fail result for the absolute slope tolerance.

`standard_error_a2_per_ps` remains `None`. Adjacent values on one cumulative
curve are serially correlated and are not treated as independent replicas.

# Diffusion estimate result

```python
@dataclass(frozen=True, slots=True)
class DiffusionEstimate:
    value_a2_per_ps: float
    standard_error_a2_per_ps: float | None
    time_range_ps: tuple[float, float]
    method: str
    component: str
    dimensions: int
    n_points: int
    is_stable: bool | None
    diagnostics: Mapping[str, Any]
    metadata: Mapping[str, Any]
    projection_basis: NDArray[np.float64]
    projection_labels: tuple[str, ...] | None
    signature: DynamicsInputSignature | None
```

The basis rank equals `dimensions`. The component label and optional signature
must agree with that subspace. Diagnostics and metadata are recursively
immutable. The cm$^2$/s property uses the exact package conversion factor
$10^{-4}$.

# MSD/VACF comparison

## Public function

```python
def compare_msd_vacf_diffusion(
    msd: MSDResult,
    vacf_diffusion: DiffusionEstimate,
    *,
    msd_fit_range_ps: tuple[float, float],
    dimensions: Literal[1, 2, 3] | None = None,
) -> DiffusionComparisonResult:
    ...
```

The optional `dimensions` argument is deprecated and acts only as a consistency
check against the stored subspace rank.

## Admission contract

The comparison requires:

- `msd.mode == "time_averaged"`;
- `msd.coordinate_mode == "laboratory"`;
- complete `DynamicsInputSignature` objects on both inputs; and
- equality of every semantic field after assigning the VACF estimate subspace to
  the MSD signature.

This detects mismatches in source identity, exact frame sequence and times,
measured atoms, coordinate/reference-cell treatment, drift mode, exact drift-
reference atoms, velocity source, and physical projection.

Unsigned legacy results fail closed.

## Projected MSD fit

The selected VACF estimate basis is also used for the MSD:

$$
M_B(t)=\operatorname{tr}[B M(t)B^\mathsf{T}].
$$

Canonical axis subsets may use stored components. A rotated basis requires the
full MSD tensor. At least three stored MSD points are required. Centered OLS with
an intercept produces slope $m_B$, then

$$
D_{\mathrm{MSD}}=\frac{m_B}{2d}.
$$

## Difference measures

The result stores

$$
\Delta D=D_{\mathrm{MSD}}-D_{\mathrm{VACF}},
$$

$$
|\Delta D|,
$$

and the symmetric relative difference

$$
\delta_{\mathrm{sym}}
=
\begin{cases}
0, & |D_{\mathrm{MSD}}|+|D_{\mathrm{VACF}}|=0,\\[4pt]
\dfrac{2|D_{\mathrm{MSD}}-D_{\mathrm{VACF}}|}
{|D_{\mathrm{MSD}}|+|D_{\mathrm{VACF}}|}, & \text{otherwise}.
\end{cases}
$$

Neither estimator is declared authoritative.

# Comparison result

```python
@dataclass(frozen=True, slots=True)
class DiffusionComparisonResult:
    msd_diffusion_a2_per_ps: float
    vacf_diffusion_a2_per_ps: float
    signed_difference_a2_per_ps: float
    absolute_difference_a2_per_ps: float
    symmetric_relative_difference: float
    msd_fit_range_ps: tuple[float, float]
    msd_slope_a2_per_ps: float
    msd_intercept_a2: float
    component: str
    dimensions: int
    n_msd_points: int
    diagnostics: Mapping[str, Any]
    metadata: Mapping[str, Any]
    projection_basis: NDArray[np.float64]
    projection_labels: tuple[str, ...] | None
    signature: DynamicsInputSignature
```

The constructor validates all algebraic difference identities, subspace fields,
fit interval, point count, and signature projection. Arrays and nested mappings
are immutable.

# Interpretation policy

The module reports, but does not automatically resolve:

- nonpositive MSD slopes;
- a VACF interval that fails the requested slope tolerance;
- a VACF interval whose stability was not assessed;
- imperfect linearity in the MSD fit; and
- finite-record differences between Einstein and Green-Kubo estimates.

No automatic ballistic/caged/diffusive classification is performed.

# Required tests

- constant and gently drifting running curves produce expected diagnostics;
- irregular selected lag grids raise;
- boolean point counts and invalid tolerances raise;
- an unsupported automatic window raises explicitly;
- scalar 3D and Cartesian comparison values preserve pre-H0 references;
- axis-subset and rotated MSD projections use the stored VACF subspace;
- a rotated projection without the MSD tensor raises;
- different drift-reference atoms raise;
- different slices under the same filename raise;
- coordinate/reference-cell and velocity-source mismatches raise;
- unsigned results raise;
- the deprecated `dimensions` check cannot reinterpret the subspace;
- difference identities and units are exact; and
- arrays, diagnostics, and metadata are deeply immutable.

# References

[1] A. Einstein, *Ann. Phys.* **322**, 549-560 (1905). DOI:
[10.1002/andp.19053220806](https://doi.org/10.1002/andp.19053220806).

[2] M. S. Green, *J. Chem. Phys.* **22**, 398-413 (1954). DOI:
[10.1063/1.1740082](https://doi.org/10.1063/1.1740082).

[3] R. Kubo, *J. Phys. Soc. Jpn.* **12**, 570-586 (1957). DOI:
[10.1143/JPSJ.12.570](https://doi.org/10.1143/JPSJ.12.570).
