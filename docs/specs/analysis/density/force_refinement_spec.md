---
title: "Local Mean-Force and Harmonic/Manifold Refinement Specification"
subtitle: "Stage 11E3"
author: "mdstats"
date: "2026-07-25"
version: "0.20.1a0"
status: "implemented"
toc: true
toc-depth: 3
numbersections: true
geometry: margin=0.85in
fontsize: 10pt
header-includes:
  - |
    \usepackage{amsmath}
    \usepackage{amssymb}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{microtype}
    \usepackage{xcolor}
---

# Scope

Stage 11E3 refines the position-derived statistical candidates from Stage 11E2
with force evidence from the Stage 11E0b sample catalog. It does not create,
delete, merge, or label spatial sites. A candidate remains present when force
data are unavailable, inadmissible for PMF use, locally under-sampled, singular,
or inconsistent with a stable harmonic model.

The implementation owner is:

```text
mdstats.analysis.density.force_refinement
```

The stage consumes one source-compatible triple:

```text
FrameworkAlignedIonSampleCatalog
PeriodicSpeciesDensityEstimate
DensityAttractorCatalog
```

and returns one immutable `ForceRefinementCatalog`.

# Borrowed methods and package-specific constructions

The conditional-average-force interpretation follows Darve and Pohorille
(2001), DOI 10.1063/1.1410978. The local linear force-matching interpretation
follows Noid et al. (2008), DOI 10.1063/1.2938860. Complete-system blocking for
correlated uncertainty follows Flyvbjerg and Petersen (1989), DOI
10.1063/1.457480.

The following are mdstats-specific constructions:

- exact source binding across E0b, E1, and E2 signatures;
- retaining every E2 attractor regardless of force-evidence status;
- matched use of the E1 periodized Gaussian and image-truncation certificate;
- explicit Cartesian-to-fractional covector conversion before score comparison;
- support intersection with the E1 support mask;
- lifted periodic residence charts bound to one E2 attractor;
- separate density anchor, force center, curvature class, and chart-containment
  status;
- separate ordinary fit, covariance diagnostic, and density-force residual; and
- fail-closed serialization and resource preflight.

# Coordinate and force contract

Let the registered periodic domain use row-vector fractional coordinates
$\mathbf q$ and cell matrix $H$:

$$
\mathbf x=\mathbf qH.
$$

A registered Cartesian force covector $\mathbf F_x$ is transformed to the
fractional coordinate measure by work invariance:

$$
\mathbf F_q=\mathbf F_xH^{\mathsf T},
\qquad
\mathbf F_x\,d\mathbf x^{\mathsf T}
=
\mathbf F_q\,d\mathbf q^{\mathsf T}.
$$

The E1 density score $d_q\log p$ and $\mathbf F_q$ are therefore compared in the
same covector measure. The analysis metric is not applied until an orthonormal
local chart is required.

If $G=LL^{\mathsf T}$ is the E1 analysis metric and
$\boldsymbol\delta_y=\boldsymbol\delta_qL$, then local force covectors transform
as

$$
\mathbf F_y=\mathbf F_qL^{-\mathsf T}.
$$

# Matched-kernel conditional mean force

Only the E0b `pmf_force` evidence subset is admissible. For query node
$\mathbf q_g$, represented-time weights $w_n$, forces $\mathbf F_{q,n}$, and the
same periodized Gaussian $K_h^{\mathbb T^3}$ used by E1,

$$
\overline{\mathbf F}_q(\mathbf q_g)
=
\frac{\sum_n w_nK_h^{\mathbb T^3}(\mathbf q_g-\mathbf q_n)
\mathbf F_{q,n}}
{\sum_n w_nK_h^{\mathbb T^3}(\mathbf q_g-\mathbf q_n)}.
$$

The field stores:

- conditional force covector;
- conditional force covariance;
- local effective sample size;
- support mask;
- optional complete-system block standard error;
- represented ion time and force-sample count; and
- E0b/E1 source signatures.

A node is force-supported only when it also belongs to the E1 support mask and
passes the configured local effective-sample threshold. Unsupported field
values are finite zeros; the support mask is authoritative.

# Density-score comparison

At declared constant temperature $T$ and for PMF-admissible equilibrium
sampling,

$$
\overline{\mathbf F}_q(\mathbf q)
\approx
k_{\mathrm B}T\,d_q\log p(\mathbf q).
$$

For each E2 attractor, the result records the norm of the residual at the
representative logical node when both channels are supported. This residual is
a diagnostic. It does not overwrite either field or project the force field
onto a conservative subspace.

# Lifted residence chart

Samples assigned to attractor $i$ use the E2 basin owner at the nearest periodic
logical node. Relative positions are lifted by

$$
\boldsymbol\delta_q
=
(\mathbf q-\mathbf q_i)-\operatorname{rint}(\mathbf q-\mathbf q_i).
$$

A lift is accepted only when every component lies strictly inside the periodic
half-cell cut. The E3 fit chart is the union of the E2 local chart and accepted
residence lifts. This extension is recorded by the fit sample indices; it does
not alter the E2 topology.

# Symmetric local force fit

For point candidates and resolved extended candidates, fit

$$
\mathbf f_n
=
\mathbf b_i-\boldsymbol\delta_{y,n}K_i+\boldsymbol\epsilon_n,
\qquad K_i=K_i^{\mathsf T},
$$

with represented-time weighted least squares. The nine fitted parameters are
three intercept components and six independent stiffness components. The result
retains:

- design rank and condition number;
- intercept and symmetric stiffness;
- stiffness eigenvalues and eigenvectors;
- residual covariance;
- parameter standard errors;
- force-defined point center where identifiable; and
- center-within-chart status.

For nonsingular point fits,

$$
\boldsymbol\delta_y^{(F)}=\mathbf b_iK_i^{-1}.
$$

The center is not imposed for an extended attractor.

# Curvature classes

The force fit reports one of:

```text
stable_point
saddle_or_unstable
soft_manifold
flat_or_unresolved
not_evaluated
```

A stable point requires all stiffness eigenvalues above the declared minimum.
A saddle or unstable fit has at least one eigenvalue below the negative
threshold. A resolved one-dimensional E2 manifold is `soft_manifold` when two
normal directions are restoring and the soft eigenvalue is small relative to
the largest stiffness. Otherwise the result remains unresolved.

# Residence covariance diagnostic

For all position-admissible samples assigned to the provisional residence basin,
compute the represented-time weighted covariance in the same orthonormal chart:

$$
\Sigma_i^{(\mathrm{res})}
=
\operatorname{Cov}(\boldsymbol\delta_y\mid B_i).
$$

When $K_i$ is positive definite and a constant temperature is declared, also
report

$$
\Sigma_i^{(\mathrm{harm})}=k_{\mathrm B}TK_i^{-1}
$$

and the relative Frobenius discrepancy. This is diagnostic only. Basin
truncation, anharmonicity, many-ion conditioning, and finite sampling may make
the two covariances disagree.

# Evidence status

Every E2 attractor receives exactly one `LocalForceRefinement`. Its independent
force-evidence status is one of:

```text
resolved
force_unavailable
pmf_provenance_rejected
insufficient_local_support
chart_unresolved
rank_deficient
ill_conditioned
center_outside_chart
```

No non-resolved status deletes the position-derived candidate.

# Resource and serialization contract

`LocalMeanForceResourcePolicy` preflights grid nodes, force samples, Gaussian
image terms, workspace, output bytes, and attractor count before allocation.
All options, fields, refinements, and catalogs have deterministic SHA-256
signatures and strict replay constructors. Field replay requires numerical
values; summary-only dictionaries are not replayable scientific objects.

# Non-goals

Stage 11E3 does not:

- reconstruct a global PMF;
- project a raw force field to its conservative component;
- perform Helmholtz-Hodge decomposition;
- infer transition events or residences;
- assign structural or crystallographic site labels;
- estimate barriers or rates; or
- replace the E2 nonparametric basin catalog with harmonic ellipsoids.

# Acceptance tests

The focused gate must verify:

1. a synthetic harmonic well recovers center and stiffness;
2. unstable curvature is not labeled a stable point;
3. an extended attractor preserves a soft direction without a point center;
4. missing or PMF-inadmissible force data preserve all spatial attractors;
5. insufficient samples and singular designs lower evidence status;
6. matched fields retain E1 support and block uncertainty;
7. source mismatch and resource excess fail closed;
8. serialization replay is exact and tamper-evident; and
9. public exports and stage metadata are stable.

# References

Darve, E., and Pohorille, A. (2001). *Calculating Free Energies Using Average
Force*. Journal of Chemical Physics 115, 9169-9183. DOI: 10.1063/1.1410978.

Noid, W. G., et al. (2008). *The Multiscale Coarse-Graining Method. I. A
Rigorous Bridge between Atomistic and Coarse-Grained Models*. Journal of
Chemical Physics 128, 244114. DOI: 10.1063/1.2938860.

Flyvbjerg, H., and Petersen, H. G. (1989). *Error Estimates on Averages of
Correlated Data*. Journal of Chemical Physics 91, 461-466. DOI:
10.1063/1.457480.
