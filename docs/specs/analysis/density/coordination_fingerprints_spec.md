---
title: "Species-Dependent Coordination Fingerprints and Structural Classification Specification"
subtitle: "Stage 11E5a"
author: "mdstats"
date: "2026-07-25"
version: "0.20.4a0"
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

Stage 11E5a converts a frozen Stage-11E5 statistical-state catalog and its
registered structural associations into exact, species-dependent physical
coordination records. The implementation owner is:

```text
mdstats.analysis.density.coordination_fingerprints
```

The stage consumes a source-compatible chain:

```text
AtomisticFrameCollection                   physical coordinates and cells
FrameworkAlignedIonSampleCatalog           E0b registered sample identity
ProvisionalTemporalAssignmentCatalog       E4 state membership
ValidatedFrozenCatalog                     E5 frozen states and associations
RegisteredStructuralGeometryView           C0A3 persistent ring geometry
```

It produces one `CoordinationFingerprintCatalog`. A state with several plausible
ring associations produces one separate fingerprint record for each retained
candidate. A non-ring association is retained with an explicit unsupported
status; it is not silently converted to the nearest ring.

This stage does **not** move state centers, redefine basins, fit a many-body PMF,
condition the structural frame on mobile-ion coordinates, publish final events,
or estimate rates. Those remain Stage 11E5b, E6, and later responsibilities.

# Borrowed methods and package-specific constructions

The following are standard background methods:

- the finite cyclic discrete Fourier transform of an equal-index sequence;
- weighted angular moments on a circular coordinate;
- least-squares trigonometric regression with explicit rank and condition
  diagnostics; and
- circular mean phase and mean resultant length.

The implementation reuses the exact cyclic/actual-angle separation established
by Stage 11C3. Standard DFT background follows Oppenheim and Schafer,
*Discrete-Time Signal Processing*, third edition (2010). Circular-resultant
background follows Fisher, *Statistical Analysis of Circular Data* (1993).

The following are mdstats-specific constructions:

- exact E0b/E4/E5/C0A3 source binding before physical-distance work;
- the authoritative state-conditioned M--O and M--T sample matrices with
  persistent atom/image identities;
- a centered-reference sequence that preserves the observed normal coordinate
  while setting the in-plane displacement to zero;
- a framewise geometry-forward prediction based on the weighted state center in
  the physical ring frame;
- explicit separation of direct off-center coordinates from residual harmonic
  diagnostics;
- oxygen-, gap-, and sector-locking scores that are admissible only when the
  circular phase is resolved and stable;
- occupancy-conditioned mixture detection without automatically splitting the
  frozen E5 state; and
- a conservative structural-class evidence lattice.

# Source compatibility and physical coordinate rule

The builder fails before allocating distance matrices unless:

- the E5 sample-catalog signature equals the supplied E0b catalog;
- the E5 temporal-assignment signature equals the supplied E4 catalog;
- the E5 registered-structural-view digest equals the supplied C0A3 view;
- the E0b and C0A3 registration signatures agree; and
- the physical collection binding digest equals the collection digest stored in
  the C0A3 view.

Registered coordinates are used only to establish statistical-state membership
and structural association. Exact distances are evaluated in each source
frame's physical Cartesian geometry.

For sample $n$ in frame $t$, let $\mathbf x_{M,n}$ be the physical ion position
and $\mathbf c_t$ the matched physical ring center. The ion image is chosen by
the exact triclinic minimum-image operator already owned by the shared neighbor
geometry layer:

$$
\widetilde{\mathbf x}_{M,n}
=
\mathbf c_t+
\operatorname{MIC}_{H_t}
\left(\mathbf x_{M,n}-\mathbf c_t\right).
$$

The matched ring oxygen and T coordinates already carry persistent periodic
images in the C0A3 structural view. Distances are therefore

$$
d^{\mathrm O}_{n,j}
=
\left\|
\widetilde{\mathbf x}_{M,n}-\mathbf x^{(\mathrm{matched})}_{\mathrm O_j,t}
\right\|,
\qquad
 d^{\mathrm T}_{n,j}
=
\left\|
\widetilde{\mathbf x}_{M,n}-\mathbf x^{(\mathrm{matched})}_{\mathrm T_j,t}
\right\|.
$$

The complete matrices $d^{\mathrm O}_{n,j}$ and $d^{\mathrm T}_{n,j}$ are the
authoritative coordination fingerprint. Mean sequences and harmonic summaries
are derived views.

# Direct local coordinates and centered reference

For each resolved physical ring frame $(\mathbf u_t,\mathbf v_t,\mathbf n_t)$,

$$
(u_n,v_n,z_n)
=
\left(
(\widetilde{\mathbf x}_{M,n}-\mathbf c_t)\cdot\mathbf u_t,
(\widetilde{\mathbf x}_{M,n}-\mathbf c_t)\cdot\mathbf v_t,
(\widetilde{\mathbf x}_{M,n}-\mathbf c_t)\cdot\mathbf n_t
\right),
$$

and

$$
r_{\perp,n}=\sqrt{u_n^2+v_n^2}.
$$

These direct coordinates, not a harmonic amplitude, determine whether a state is
centered or off-center.

For the centered-reference diagnostic, retain the same normal coordinate while
setting the in-plane displacement to zero:

$$
\mathbf x^{(0)}_{M,n}
=
\mathbf c_t+z_n\mathbf n_t,
\qquad
 d^{(0)}_{n,j}
=
\left\|
\mathbf x^{(0)}_{M,n}-\mathbf x^{(\mathrm{matched})}_{\mathrm O_j,t}
\right\|.
$$

The residual sequence is

$$
\Delta d_{n,j}=d^{\mathrm O}_{n,j}-d^{(0)}_{n,j}.
$$

Its cyclic and angular spectra are diagnostic only. Irregular spacing,
puckering, chemical serration, large displacement, and nonlinear distance
geometry can mix modes. The implementation records
`residual_spectra_are_diagnostic_not_exact_component_separation=true`.

# Three distinct harmonic measures

For each weighted state mean sequence $\bar d_j$, E5a records three different
objects.

## Equal-atom cyclic spectrum

For an ordered $k$-atom sequence,

$$
D_m
=
\frac{1}{k}
\sum_{j=0}^{k-1}
\bar d_j
\exp\left(-\frac{2\pi i m j}{k}\right),
\qquad
0\le m\le\left\lfloor\frac{k}{2}\right\rfloor.
$$

This is an exact discrete sequence descriptor. It does not approximate a
continuous boundary measure.

## Boundary-measure angular moments

For physical polar angles $\theta_j$ and positive arc-length Voronoi weights
$w_j$,

$$
A_m
=
\frac{\sum_j w_j\bar d_j e^{-im\theta_j}}
     {\sum_j w_j}.
$$

This is the appropriate descriptor when the intended measure is a continuous
ring boundary rather than equal atom count.

## Rank-safe actual-angle fit

The model

$$
\bar d(\theta)
=
a_0+
\sum_{m=1}^{m_{\max}}
\left[a_m\cos(m\theta)+b_m\sin(m\theta)\right]
$$

is solved only when the weighted design matrix has full parameter rank and its
condition number does not exceed the declared maximum. An unresolved fit stores
rank and parameter count but no fitted harmonic coefficients. Regularization is
explicit and defaults to zero.

Raw and normalized amplitudes are retained. A normalized amplitude uses the
mean distance magnitude as its declared scale; it never replaces the raw
coefficient.

# Geometry-forward check

Let $\bar{\boldsymbol\xi}=(\bar u,\bar v,\bar z)$ be the represented-time
weighted mean direct local coordinate. For each frame, construct

$$
\mathbf x^{\mathrm{geom}}_{M,t}
=
\mathbf c_t+\bar u\mathbf u_t+\bar v\mathbf v_t+\bar z\mathbf n_t
$$

and evaluate the complete physical M--O vector against that frame's matched
oxygen images. The implementation stores the resulting per-sample geometry
prediction and reports

$$
\epsilon_{\mathrm{geom}}
=
\sqrt{\frac{1}{k}
\sum_j
\left(
\bar d^{\mathrm O}_j-\bar d^{\mathrm{geom}}_j
\right)^2}.
$$

A bounded explained fraction compares the observed centered-reference
modulation with the geometry-predicted modulation. It is a consistency
diagnostic, not a decomposition into chemical and geometric components.

# Phase and locking evidence

For samples with $r_{\perp,n}$ above the declared centered threshold, define
$\phi_n=\operatorname{atan2}(v_n,u_n)$. The weighted circular resultant is

$$
R
=
\left|
\frac{\sum_n w_n e^{i\phi_n}}{\sum_n w_n}
\right|.
$$

A phase-dependent label is admissible only when:

1. the direct radial displacement exceeds the centered threshold; and
2. $R$ exceeds `phase_stability_threshold`.

When admissible, the mean phase is compared separately with persistent oxygen
angles and inter-oxygen gap angles. The output retains continuous
oxygen-locking, gap-locking, and sector-locking scores. No chemical-direction
label is emitted when the phase is unresolved.

# Occupancy-conditioned fingerprints

An optional per-sample occupancy-context label $\eta_n$ produces one
`OccupancyContextFingerprint` per sufficiently supported group. It retains:

- sample count and represented time;
- mean local coordinates;
- covariance trace;
- mean radial offset; and
- circular phase and resultant when defined.

Two supported contexts produce `resolved_mixture` when their local centers or
stable phases differ beyond declared thresholds. The frozen E5 state is not
silently split. The pooled fingerprint remains available together with its
explicit mixture status.

# Conservative structural classes

`CoordinationClassificationEvidence` retains continuous evidence and one
provisional class:

```text
point
bilateral
discrete_off_center
smooth_annular
corrugated_annular
cage
general
classification_ambiguous
```

The decision order is conservative:

- a tile/cage association is `cage`;
- sufficiently annular sampling is `smooth_annular` or
  `corrugated_annular` according to angular corrugation;
- balanced support on opposite normal sides is `bilateral`;
- `discrete_off_center` requires direct radial displacement, stable phase, and a
  geometry-forward explained fraction;
- a state below the direct radial threshold is `point`, regardless of a
  short-wavelength serration harmonic;
- an occupancy mixture or unresolved phase at appreciable radial displacement
  remains `classification_ambiguous`; and
- remaining cases are `general`.

A centered serrated S6R can therefore have a dominant $m=3$ M--O component while
remaining `point`. An $m=1$ amplitude alone can never force
`discrete_off_center`.

# Resource and serialization contracts

`CoordinationFingerprintResourcePolicy` preflights:

```text
max_states
max_associations
max_sample_distance_values
max_occupancy_groups
max_serialized_records
```

The builder fails transactionally before exceeding the declared work. All
arrays are immutable and all options, spectra, context summaries,
classifications, state records, and catalogs carry deterministic SHA-256
signatures. Strict JSON serialization rejects non-finite values and tampering.

# Acceptance tests

The focused gate requires:

- a centered serrated S6R remains `point` even when its $m=3$ amplitude exceeds
  $m=1$;
- coherent direct off-centering agrees with the framewise geometry-forward
  prediction;
- centered-reference residual spectra are marked diagnostic only;
- a circulating angular population cannot receive a discrete phase label;
- occupancy-conditioned mixtures remain explicit;
- rank-deficient actual-angle fits retain rank diagnostics without fitted modes;
- multiple plausible associations remain separate records;
- source signatures, serialization, resources, and public exports fail closed;
- real ASE 3.29.0 is used for physical minimum-image and VASP I/O regression
  coverage in the release environment.

# References

1. A. V. Oppenheim and R. W. Schafer, *Discrete-Time Signal Processing*, third
   edition, Pearson, 2010.
2. N. I. Fisher, *Statistical Analysis of Circular Data*, Cambridge University
   Press, 1993.
3. K. Pearson, "On Lines and Planes of Closest Fit to Systems of Points in
   Space," *Philosophical Magazine* **2**, 559-572 (1901). The plane-fit
   construction is owned upstream by Stage 11C/C0A3; E5a consumes its physical
   ring frame.
