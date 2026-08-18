---
title: "Geometry-Conditioned Site Refinement Specification"
subtitle: "Stage 11E5b"
author: "mdstats"
date: "2026-07-25"
version: "0.20.5a0"
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

Stage 11E5b is an optional refinement downstream of the frozen Stage-11E5
statistical catalog and Stage-11E5a structural fingerprints. It asks whether a
validated site's center follows independently measured framework geometry.
The implementation owner is:

```text
mdstats.analysis.density.geometry_conditioning
```

The stage consumes:

```text
ValidatedFrozenCatalog               Stage 11E5 state identity and block plan
CoordinationFingerprintCatalog       Stage 11E5a exact local ion coordinates
FrameworkPredictorTable              framework-only structural descriptors
FrozenRegionDefinition               frozen center, core, and basin radii
```

It produces one `GeometryConditionedSiteCatalog`. The dynamic model may move a
site center and rigidly translate its nested core and basin, but it never changes
the persistent statistical-state identity, redefines the framework frame, or
iteratively reassigns discovery samples.

This stage does **not** publish final residence or transition events, rates,
barriers, a PMF, or a kinetic network. Those remain Stage 11E6 and later work.

# Borrowed methods and package-specific constructions

Weighted affine regression and held-out model comparison are standard
statistical methods. The regression and bias--variance background follows Hastie,
Tibshirani, and Friedman, *The Elements of Statistical Learning*, second edition
(2009). The separation of model fitting and independent predictive assessment is
standard cross-validation/model-selection practice; see Stone (1974),
*Journal of the Royal Statistical Society B* **36**, 111--147.

The following are mdstats-specific constructions:

- exact E5/E5a/registered-structural-view source binding;
- a framework-only predictor contract that rejects mobile-ion-derived features;
- one-pass fitting on frozen discovery assignments;
- selection-block comparison followed by untouched final-validation confirmation;
- rigid translation of a frozen nested region rather than implicit use of the
  frozen basin around a moving center;
- simultaneous static and dynamic membership records;
- explicit comoving, center, and boundary displacement diagnostics;
- an exclusive assignment-conflict vocabulary; and
- lower/upper occupancy bounds under moving-region overlap.

# Source and predictor contracts

For state $i$ and structural association $a$, the fingerprint, predictor table,
and frozen region must share:

```text
state_id
candidate_index
persistent_identity
sample_indices
frame_indices
registered_structural_view_digest
validated_frozen_catalog_signature
```

Only one selected structural association per statistical state enters one E5b
catalog. Alternative E5a associations remain available in the E5a catalog and
may be evaluated in separate candidate runs; they are not silently merged.

A `FrameworkPredictorTable` stores one row per E5a sample and one column per
structural feature. Examples include:

- ring aperture, area, perimeter, and puckering;
- oxygen-class radii;
- rank-safe structural harmonic coefficients;
- gauge-defined structural phase coordinates when supported;
- tile or cage volume; and
- local framework strain descriptors.

The table carries `framework_only=true`. Mobile-ion positions, ion-derived
coordination distances, provisional site labels, or residuals computed from the
same mobile-ion target are forbidden as predictors. This prevents the structural
frame from being redefined by the ion whose position is being predicted.

# Static and affine center models

Let $\mathbf y_n\in\mathbb R^3$ be the ion coordinate in the persistent local
structural frame and $\boldsymbol\xi_n\in\mathbb R^p$ the framework descriptor.
The frozen static model is

$$
\widehat{\mathbf c}^{\mathrm{static}}_n=\mathbf c_0.
$$

The candidate framework-conditioned model is

$$
\widehat{\mathbf c}^{\mathrm{dyn}}_n
=
\mathbf b+
B\left(\boldsymbol\xi_n-\overline{\boldsymbol\xi}_{D}\right),
$$

where $D$ is the discovery block. With represented-time weights $w_n$, E5b
solves

$$
\min_{\mathbf b,B}
\sum_{n\in D}w_n
\left\|
\mathbf y_n-
\mathbf b-
B(\boldsymbol\xi_n-\overline{\boldsymbol\xi}_{D})
\right\|^2.
$$

The fitted record stores:

```text
predictor mean
intercept
coefficient matrix
fit rank and parameter count
condition number
sample count
weighted residual RMS
residual covariance
```

The fit fails closed when discovery support is insufficient, the weighted design
is rank deficient, or its condition number exceeds the declared threshold.
Regularization is explicit and defaults to zero; when enabled, the intercept is
not penalized.

# Noncircular selection and validation

The E5 block plan supplies disjoint or explicitly provenance-labeled frame sets:

```text
discovery
selection
final_validation
```

Discovery assignments are the frozen E5/E5a samples. They are not recomputed
after fitting. For block $R$, define

$$
\operatorname{RMS}_{R}(m)
=
\left[
\frac{\sum_{n\in R}w_n
\|\mathbf y_n-\widehat{\mathbf c}_{m,n}\|^2}
{\sum_{n\in R}w_n}
\right]^{1/2}.
$$

The selection improvement is

$$
I_S=
\frac{
\operatorname{RMS}_{S}(\mathrm{static})-
\operatorname{RMS}_{S}(\mathrm{dynamic})
}{
\max[\operatorname{RMS}_{S}(\mathrm{static}),\epsilon]
}.
$$

The dynamic model is eligible only when $I_S$ exceeds the declared minimum.
It is retained only when the untouched validation block has adequate support and

$$
\operatorname{RMS}_{V}(\mathrm{dynamic})
\le
(1+\delta_V)
\operatorname{RMS}_{V}(\mathrm{static}),
$$

where $\delta_V$ is the maximum admitted validation degradation. Otherwise the
static model remains selected and the exact reason is stored:

```text
static_retained
dynamic_retained
insufficient_discovery_support
insufficient_selection_support
independent_validation_unavailable
final_validation_contradicted
rank_deficient
ill_conditioned
unresolved
```

Selection success is therefore not itself final confirmation.

# Moving nested regions

A `FrozenRegionDefinition` contains a center $\mathbf c_0$, core radius $r_C$,
and basin radius $r_B$ satisfying

$$
0<r_C<r_B.
$$

The first implementation translates the frozen shape without changing its
radii or covariance:

$$
C_i(t)=
\left\{\mathbf y:\|\mathbf y-\widehat{\mathbf c}_i(t)\|\le r_C\right\},
$$

$$
B_i(t)=
\left\{\mathbf y:\|\mathbf y-\widehat{\mathbf c}_i(t)\|\le r_B\right\}.
$$

A moving center therefore never uses a basin still centered at $\mathbf c_0$.
Shape-conditioned or covariance-conditioned regions are explicitly deferred.

Every sample retains three memberships:

```text
static_membership
dynamic_membership
selected_membership
```

The selected membership uses the dynamic region only when the dynamic model
passes the selection and final-validation gate. Static and candidate-dynamic
memberships remain available as counterfactual diagnostics.

# Motion and crossing diagnostics

For adjacent samples of the same atom and source segment, E5b records

$$
\Delta\mathbf y_n=\mathbf y_n-\mathbf y_{n-1},
$$

$$
\Delta\mathbf c_n=
\widehat{\mathbf c}^{\mathrm{dyn}}_n-
\widehat{\mathbf c}^{\mathrm{dyn}}_{n-1},
$$

and the local comoving displacement

$$
\Delta\mathbf y^{\mathrm{comov}}_n
=
(\mathbf y_n-\widehat{\mathbf c}^{\mathrm{dyn}}_n)
-
(\mathbf y_{n-1}-\widehat{\mathbf c}^{\mathrm{dyn}}_{n-1}).
$$

For a rigidly translated spherical region, the boundary displacement magnitude
is $\|\Delta\mathbf c_n\|$. A dynamic membership change is classified as
`boundary_induced` only when the frozen membership does not change and the ion
movement is small relative to the boundary motion. Other changes remain
`ion_driven`, `mixed`, or `unresolved`. A boundary-swept crossing is never
silently counted as a purely ion-driven jump.

Crossing diagnostics never bridge atom identities or E0b source-segment resets.

# Assignment conflicts and occupancy bounds

Moving regions belonging to distinct states may overlap. Each represented
sample receives one exclusive `AssignmentConflictStatus`:

```text
unique_core
unique_basin
multiple_core_overlap
multiple_basin_overlap
static_dynamic_conflict
outside_supported_regions
assignment_unresolved
```

No ion is double-counted in the lower occupancy estimate. For state $i$,

$$
W_i^{\mathrm{lower}}
=
\sum_n w_n
\mathbf 1\{n\text{ is uniquely assigned to }i\},
$$

$$
W_i^{\mathrm{upper}}
=
\sum_n w_n
\mathbf 1\{n\text{ belongs to any selected region of }i\}.
$$

The result stores lower and upper fractions, core-overlap fraction,
basin-overlap fraction, and unresolved fraction. Declared overlap gates are
reported in catalog diagnostics; they do not silently delete a state.

# Residual covariance

E5b reports weighted residual covariance before and after conditioning:

$$
\Sigma_m=
\frac{1}{\sum_n w_n}
\sum_nw_n
(\mathbf r_{m,n}-\overline{\mathbf r}_m)
(\mathbf r_{m,n}-\overline{\mathbf r}_m)^{\mathsf T}.
$$

A reduced trace is supporting evidence for framework-conditioned motion, not a
standalone validation decision. The held-out residual gate remains authoritative.

# Persistence, resources, and serialization

All option, predictor, region, model, score, crossing, state, conflict,
occupancy, and catalog records are immutable and SHA-256 signed. Deserialization
recomputes every nested signature and rejects tampering.

Resource preflight bounds:

```text
states
samples
predictor values
crossing records
conflict records
serialized records
```

The preflight occurs before aggregate conflict and occupancy construction.

# Acceptance tests

The focused acceptance suite must demonstrate:

1. a true framework-following center is selected and confirmed on held-out data;
2. a selection gain contradicted by final validation leaves the static model selected;
3. rank-deficient predictors fail closed;
4. mobile-ion-dependent predictors are rejected;
5. static and dynamic memberships remain jointly available;
6. a boundary-swept crossing is not labeled ion driven;
7. overlap produces exclusive conflicts and occupancy bounds;
8. source mismatch, resources, serialization, and tamper checks fail closed; and
9. public package exports remain stable.

# Deferred work

Stage 11E6 owns final core--basin hysteresis, residence intervals, transition
intervals, recrossing policy, censoring, and final event statistics. E5b records
candidate memberships and motion diagnostics only.
