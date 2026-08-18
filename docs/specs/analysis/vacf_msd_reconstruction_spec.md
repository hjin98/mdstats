---
title: "VACF-to-MSD Reconstruction Specification"
subtitle: "GK4 after H0: Projected Correlation-to-Displacement Diagnostic"
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

This document specifies the H0-hardened

```python
reconstruct_msd_from_vacf(...)
```

implementation in `mdstats/analysis/vacf_transport.py`. It reconstructs the
mean-square displacement implied by a stored physical self VACF. It is a
consistency diagnostic; direct position-based `compute_msd()` remains primary.

# Borrowed theory

For a stationary trajectory projected onto an orthonormal subspace $B$,

$$
B[\mathbf r(t)-\mathbf r(0)]
=
\int_0^t B\mathbf v(s)\,ds.
$$

The correlation-to-displacement identity is

$$
M_B(t)
=
2\int_0^t (t-\tau)C_B(\tau)\,d\tau,
$$

with

$$
C_B(\tau)=\operatorname{tr}\left[B C(\tau)B^\mathsf{T}\right].
$$

The equivalent two-moment implementation is

$$
I_0(t)=\int_0^t C_B(\tau)\,d\tau,
\qquad
I_1(t)=\int_0^t \tau C_B(\tau)\,d\tau,
$$

$$
M_B(t)=2[tI_0(t)-I_1(t)].
$$

This identity belongs to the Einstein/Green-Kubo/Helfand transport framework
[1-4]. The two-cumulative-integral sampled implementation, explicit subspace
API, and provenance schema are mdstats design.

# Public function

```python
def reconstruct_msd_from_vacf(
    vacf: VACFResult,
    *,
    axes: Sequence[Literal["x", "y", "z"]] | None = None,
    projection_basis: ArrayLike | None = None,
    component: Literal["scalar", "x", "y", "z"] = "scalar",
    maximum_time_ps: float | None = None,
    integration: Literal["trapezoid"] = "trapezoid",
) -> VACFMSDResult:
    ...
```

`axes` or `projection_basis` defines the physical subspace. The legacy
`component` adapter is accepted only when no explicit subspace is supplied.
Default scalar means full 3D; x/y/z means that one axis.

The equal-positive-weight, lag validation, tensor requirement, and truncation
rules are identical to `integrate_vacf_to_diffusion()`.

No dimensional divisor is applied: the result is the total projected MSD
$M_B(t)$, not $D_B$.

# Result contract

```python
@dataclass(frozen=True, slots=True)
class VACFMSDResult:
    lag_times: NDArray[np.float64]
    reconstructed_msd_a2: NDArray[np.float64]
    physical_vacf_a2_per_ps2: NDArray[np.float64]
    cumulative_vacf_a2_per_ps: NDArray[np.float64]
    cumulative_time_weighted_vacf_a2: NDArray[np.float64]
    component: str
    weighting: str
    integration: str
    metadata: Mapping[str, Any]
    dimensions: int
    projection_basis: NDArray[np.float64]
    projection_labels: tuple[str, ...] | None
    signature: DynamicsInputSignature | None
```

The constructor requires:

- every numerical array has shape `(L,)` and finite entries;
- lag time begins at zero and is strictly increasing;
- reconstructed MSD and both cumulative moments begin at zero;
- the basis rank equals `dimensions`;
- the component label agrees with a single Cartesian basis when applicable;
- the stored signature subspace agrees with the result; and
- both cumulative integrals and the reconstructed MSD reproduce the defining
  trapezoidal identities within strict tolerance.

All arrays and nested metadata are deeply immutable.

# Algorithm

1. Resolve and validate the physical subspace.
2. Validate physical equal-positive self weighting.
3. Retain the accepted lag prefix.
4. Project the source VACF onto the subspace.
5. Compute $I_0$ and $I_1$ by cumulative trapezoidal integration.
6. Compute $2(tI_0-I_1)$ and force the exact zero-lag value to zero.
7. Propagate the source signature with the selected subspace.
8. Validate and freeze the result.

The implementation is $O(L)$ after the projected VACF has been assembled.

# Interpretation limits

Finite-record reconstructed and direct MSD curves need not match exactly because:

- the VACF assumes stationary time-origin averaging;
- direct fixed-origin MSD is a different estimator;
- noisy long-lag correlations accumulate under integration;
- finite-difference velocities may attenuate high frequencies; and
- source and direct estimators can use different finite-origin weighting.

These limitations remain visible in source metadata. Reconstruction does not
replace direct MSD, choose a diffusion plateau, or classify a dynamical regime.

# Required tests

- zero and constant projected VACFs reproduce analytic sampled identities;
- full-3D and Cartesian legacy calls preserve pre-H0 values;
- axis-subset additivity holds;
- rotated projections include tensor cross terms;
- missing tensor data for a rotated basis raises;
- uniform weighting and explicit-equal weighting agree;
- mass and nonuniform weights raise;
- truncation uses existing lag samples only;
- all stored identities are constructor-validated;
- signatures propagate with the selected subspace; and
- every array and nested metadata object is immutable.

# References

[1] A. Einstein, *Ann. Phys.* **322**, 549-560 (1905). DOI:
[10.1002/andp.19053220806](https://doi.org/10.1002/andp.19053220806).

[2] M. S. Green, *J. Chem. Phys.* **22**, 398-413 (1954). DOI:
[10.1063/1.1740082](https://doi.org/10.1063/1.1740082).

[3] R. Kubo, *J. Phys. Soc. Jpn.* **12**, 570-586 (1957). DOI:
[10.1143/JPSJ.12.570](https://doi.org/10.1143/JPSJ.12.570).

[4] E. Helfand, *Phys. Rev.* **119**, 1-9 (1960). DOI:
[10.1103/PhysRev.119.1](https://doi.org/10.1103/PhysRev.119.1).
