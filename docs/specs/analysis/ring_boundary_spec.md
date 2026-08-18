---
title: "Atom-Resolved Structural Ring Boundary Specification"
subtitle: "Stage 11C3: Persistent T/O Chemistry, Serration, Harmonics, and Dihedral Gauges"
author: "mdstats"
date: "2026-07-24"
toc: true
toc-depth: 3
numbersections: true
geometry: margin=0.82in
fontsize: 10pt
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

# Purpose and stage boundary

Stage 11C3 extends the persistent T/O polygons from Stages 11C1 and 11C2 into an
atom-resolved, species-independent structural boundary:

```text
reference T/O ring identities + compatible-frame ring geometry
        + immutable framework chemistry
        + optional exact-source crystallographic aliases
        -> ordered T/O atom records
        -> exact cyclic-index structural sequences
        -> unweighted cyclic spectra
        -> boundary-measure angular moments
        -> rank-safe physical-angle fits
        -> symmetry-breaking, class-splitting, and continuity diagnostics
```

Runtime/API target:

```text
mdstats 0.19.94a0
```

Primary module:

```text
mdstats/analysis/ring_boundary.py
```

The exact ordered Cartesian T/O coordinates remain authoritative. Harmonic
coefficients are lossy descriptors and never replace, smooth, reconstruct, or
reorder the source ring.

This stage owns framework geometry and chemistry only. It does **not** own:

- M--O or M--T distances;
- mobile-species coordination fingerprints;
- statistical site centers or labels;
- occupancy-conditioned structural states;
- registered structural views; or
- kinetic transitions.

Those responsibilities remain downstream in C0A3 and Stage 11E5a.

# External methods and original construction

The finite cyclic spectrum is the standard discrete Fourier transform (DFT),
using the conventional negative exponential [1]. Weighted physical-angle
regression uses standard weighted linear least squares and condition/rank
analysis [2]. Continuous phase uncertainty uses first-order covariance
propagation; later blockwise phase distributions should use circular statistics
rather than ordinary linear means [3].

The following are project-specific `mdstats` constructions:

- strict separation of equal-atom cyclic DFTs from boundary-measure moments;
- exact even-ring Nyquist handling as a signed real coordinate;
- persistent ring-atom and periodic-image chemistry records;
- source-bound, fail-closed LTA O(1)/O(2)/O(3) alias profiles;
- explicit radial-center provenance and singular-angle rejection;
- simultaneous equal-atom and arc-length-weighted actual-angle fits;
- dihedral gauge metadata and coefficient transformation utilities;
- per-frame oxygen-class splitting, symmetry-breaking, and reference continuity;
- deterministic source replay, strict JSON serialization, and resource preflight.

# Inputs and source compatibility

The public constructor is:

```python
build_structural_ring_boundary_catalog(
    reference_geometry: ReferenceRingGeometryCatalog,
    frame_geometry: FrameRingGeometryCatalog,
    collection: AtomisticFrameCollection,
    *,
    alias_profile: LtaOxygenAliasProfile | None = None,
    options: RingBoundaryOptions | None = None,
    resources: RingBoundaryResources | None = None,
) -> StructuralRingBoundaryCatalog
```

The frame catalog must be bound to the supplied reference-ring digest. The
atomic-number vector is hashed separately as `collection_chemistry_digest`.
This stage does not infer or repair chemistry from coordinates.

The implementation preflights:

- number of persistent rings;
- number of compatible frames; and
- predicted T/O atom-record count.

A resource violation raises before descriptor arrays are allocated.

# Persistent atom boundary

For a ring of order $k$, Stage 11C3 retains two aligned sequences:

$$
(T_0,T_1,\ldots,T_{k-1}),
\qquad
(O_0,O_1,\ldots,O_{k-1}),
$$

where $O_j$ bridges $T_j$ and $T_{j+1\bmod k}$. Every atom record contains:

```text
boundary kind: T or O
cyclic index and canonical orientation
persistent atom index and lattice-image shift
atomic number and element symbol
reference Cartesian coordinate
instantaneous Cartesian coordinate
local (u, v, n) coordinate
projected radius, polar angle, and normal coordinate
```

An oxygen record additionally contains:

```text
ordered neighboring T references
ordered neighboring T atomic numbers and Si/Al classes
generic orientation-independent oxygen environment signature
optional validated crystallographic alias
```

The generic environment signature is based on the two neighboring T classes.
It remains available when no framework-specific alias is admissible.

# Center and local-coordinate contract

The default center is the Stage-11C1 projected oxygen-area centroid:

$$
\mathbf c_R = \mathbf c_{\mathrm O,A}.
$$

The local frame is the first persistent side frame
$(\hat{\mathbf e}_u,\hat{\mathbf e}_v,\hat{\mathbf n})$. For atom coordinate
$\mathbf x_j$,

$$
u_j=(\mathbf x_j-\mathbf c_R)\cdot\hat{\mathbf e}_u,
\quad
v_j=(\mathbf x_j-\mathbf c_R)\cdot\hat{\mathbf e}_v,
\quad
z_j=(\mathbf x_j-\mathbf c_R)\cdot\hat{\mathbf n},
$$

$$
\rho_j=\sqrt{u_j^2+v_j^2},
\qquad
\theta_j=\operatorname{atan2}(v_j,u_j).
$$

Every ring record stores:

```text
center_kind = oxygen_area_centroid
center_coordinates
center_uncertainty
minimum_projected_radius
angular_coordinate_defined
```

The current deterministic geometry has `center_uncertainty = 0`. This is not a
statistical uncertainty claim; it means that no stochastic center estimator is
used at this stage.

If any required projected radius satisfies

$$
\rho_j \le \rho_{\min},
$$

actual-angle fits fail closed with
`angular-coordinate-undefined`. No arbitrary angle is assigned to the singular
atom, and no boundary-measure moment is emitted for that affected sequence.

# Exact ordered structural sequences

Every resolved boundary provides exact sequences for:

- T projected radius;
- T normal coordinate;
- T atomic number;
- O projected radius;
- O normal coordinate; and
- number of adjacent Al T atoms for each O.

These arrays preserve cyclic order. String-valued environment signatures and
optional aliases remain in atom records and are not silently converted into an
arbitrary numerical code.

# Unweighted cyclic-index spectrum

For a real ordered scalar sequence $y_j$, $j=0,\ldots,k-1$,

$$
\widetilde y_m
=
\frac{1}{k}\sum_{j=0}^{k-1}
y_j\exp\left(-\frac{2\pi i m j}{k}\right).
$$

`UnweightedCyclicIndexSpectrum` always uses equal atom weights. It stores only
the unique real-sequence modes

$$
m=0,1,\ldots,\left\lfloor\frac{k}{2}\right\rfloor.
$$

For even $k$, $m=k/2$ is the Nyquist mode. Its coefficient is real up to
floating-point cleanup and is represented by:

```text
amplitude
nyquist_orientation_sign in {-1, 0, +1}
phase_defined = false
```

It does not own a continuous phase. In particular, the S6R sequence

$$
a,b,a,b,a,b
$$

has only a mean and an exact signed $m=3$ cyclic component.

Each non-Nyquist mode stores:

```text
real and imaginary coefficient
raw amplitude
optional normalized amplitude
phase when amplitude support is sufficient
phase_defined
phase_uncertainty
```

For an exact deterministic DFT descriptor, a resolved phase has numerical
uncertainty zero. Temporal/statistical phase uncertainty belongs to later
aggregation.

# Dihedral gauge

The canonical catalog uses the inherited ring origin and orientation. Public
utilities expose the exact dihedral action for testing and downstream matching.

If a new cyclic origin begins at old position $s$ without reversal,

$$
y'_j=y_{j+s},
\qquad
\widetilde y'_m
=
\widetilde y_m e^{+2\pi i m s/k}.
$$

If orientation is reversed about old position $s$,

$$
y'_j=y_{s-j},
\qquad
\widetilde y'_m
=
\widetilde y_m^* e^{-2\pi i m s/k}.
$$

The module provides:

```python
apply_cyclic_dihedral_gauge(...)
transform_cyclic_coefficient(...)
```

The ring record retains the canonical origin atom, orientation, and reversal
origin. A phase-dependent classification must reject an unresolved phase.

# Boundary-measure angular moments

A physical corrugated boundary is sampled nonuniformly in angle and arc length.
For positive boundary weights $w_j$,

$$
M_m^{(\mathrm{bdry})}
=
\frac{\sum_j w_j y_j e^{-im\theta_j}}{\sum_j w_j}.
$$

The implemented default is the polygonal arc-length Voronoi weight

$$
w_j=\frac12\left(
\lVert\mathbf x_j-\mathbf x_{j-1}\rVert
+
\lVert\mathbf x_{j+1}-\mathbf x_j\rVert
\right).
$$

This output is named `BoundaryMeasureAngularMoments`. It is not called an
unweighted DFT and makes no claim of exact cyclic orthogonality or exact
Nyquist semantics.

# Rank-safe physical-angle fits

For actual polar angles $\theta_j$ and requested modes $\mathcal M$,

$$
y_j
=
c_0+
\sum_{m\in\mathcal M}
\left[a_m\cos(m\theta_j)+b_m\sin(m\theta_j)\right]
+\epsilon_j.
$$

The design has

$$
p=1+2|\mathcal M|
$$

real parameters. Before solving, the implementation records and validates:

- angular-coordinate admissibility;
- sample count and design rank;
- weighted-design condition number;
- requested weighting measure;
- declared regularization; and
- requested mode set.

A fit is unresolved when:

```text
rank < parameter_count
condition_number > maximum_condition_number
an angular coordinate is undefined
```

No pseudoinverse is used to manufacture non-identifiable coefficients.
Regularization does not override the full-rank requirement.

For every geometric sequence, the catalog attempts two separately named fits:

```text
equal_atom
arc_length_voronoi
```

They are retained as distinct estimators.

For $g_m=a_m-i b_m$, the physical-angle phase is

$$
\phi_m=\arg g_m.
$$

When residual degrees of freedom exist, first-order covariance propagation
provides `phase_uncertainty`. With no residual degrees of freedom, the phase may
be resolved but its uncertainty remains unavailable rather than being reported
as zero.

# Raw and normalized amplitudes

Raw amplitudes retain the units of the source sequence. A normalized amplitude
is emitted only when a positive declared scale exists. For radial signals the
default scale is the absolute mean radius,

$$
\overline A_m=\frac{A_m}{|\overline\rho|},
$$

provided $|\overline\rho|$ exceeds `normalization_floor`.

A missing or inadmissible scale produces

```text
normalization_admissible = false
normalized_amplitude = null
```

A nonpositive explicitly supplied normalization scale is an input error.

# Oxygen-class splitting and symmetry breaking

O atoms are grouped by validated crystallographic alias when available;
otherwise they are grouped by the generic neighboring-T environment signature.
For every class, the result stores count, mean radial coordinate, and mean
normal coordinate.

The maximum class radial split is

$$
\Delta\rho_{\max}
=
\max_c\overline\rho_c-
\min_c\overline\rho_c.
$$

The oxygen radial symmetry-breaking diagnostic is

$$
S_\rho
=
\frac{
\sqrt{\sum_{m>0}|\widetilde\rho_m|^2}
}{|\widetilde\rho_0|},
$$

when the mean radius is admissible. The dominant radial mode is reported only
when its amplitude exceeds the declared support tolerance.

These are descriptors, not site classifications.

# Reference-to-frame continuity

Every compatible-frame boundary retains the same persistent atom identities.
For each cyclic sequence and mode, the frame result compares with the reference:

- amplitude ratio when the reference amplitude is nonzero;
- phase difference modulo $2\pi/m$ for resolved non-Nyquist phases; or
- Nyquist sign support for even-ring Nyquist modes.

No phase difference is reported when either amplitude is unresolved.

# LTA crystallographic aliases

`LtaOxygenAliasProfile` is optional and exact-source-bound. It contains:

```text
profile_id
reference_ring_geometry_digest
atom-index -> O(1)/O(2)/O(3) mapping
complete-coverage policy
optional S6R O(2)/O(3) alternation validation
```

Validation fails closed if:

- the reference digest differs;
- a mapped atom is not a persistent ring oxygen;
- an alias is assigned to a non-oxygen atom;
- required coverage is incomplete; or
- requested S6R O(2)/O(3) alternation is violated.

Exact digest binding is intentional. A conventional crystallographic alias
must not be transferred silently across a different atom ordering, origin,
framework composition, or structural model.

# Persistent outputs and serialization

`StructuralRingBoundaryCatalog` retains:

```text
reference and compatible-frame geometry digests
collection chemistry digest
alias validation and profile provenance
options and resource contract
reference boundaries
framewise boundaries
canonical schema and digest algorithm
canonical SHA-256 digest
```

`from_dict(...)` rebuilds from the supplied scientific sources and requires
byte-equivalent canonical JSON content. Tampered derived values are rejected.

# Acceptance tests

The focused C3 gate requires:

1. exact S6R alternating-sequence recovery at cyclic $m=3$;
2. declared cyclic shift and reversal coefficient transforms;
3. irregular-angle alternation not being forced into a pure physical-angle
   $m=3$ fit;
4. rank-deficient actual-angle mode sets failing closed;
5. singular projected atoms making physical-angle fits unresolved;
6. boundary-measure moments remaining distinct from unweighted DFTs;
7. phase becoming undefined below amplitude support;
8. all 58 real LTA ring boundaries retaining persistent T/O atom identities;
9. rigid-rotation invariance of local sequences and harmonic amplitudes;
10. optional aliases attaching only after exact-source validation;
11. source-mismatched and incomplete aliases failing closed;
12. serialization replay, resource preflight, and public exports.

# Deferred boundaries

The following remain outside Stage 11C3:

- C0A3 application of affine registration to structural views;
- site-conditioned M--O/M--T fingerprints;
- geometry-forward prediction of mobile-ion coordination;
- off-center versus serration residual classification;
- occupancy-conditioned exchangeability;
- circular block statistics over long trajectories; and
- transition-path sector analysis.

# References

[1] A. V. Oppenheim and R. W. Schafer, *Discrete-Time Signal Processing*,
3rd ed., Pearson, 2010.

[2] G. H. Golub and C. F. Van Loan, *Matrix Computations*, 4th ed., Johns
Hopkins University Press, 2013.

[3] K. V. Mardia and P. E. Jupp, *Directional Statistics*, Wiley, 2000.
