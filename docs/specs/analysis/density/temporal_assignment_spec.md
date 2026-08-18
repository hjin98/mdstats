---
title: "Provisional Assignment and Temporal-Persistence Diagnostics Specification"
subtitle: "Stage 11E4"
author: "mdstats"
date: "2026-07-25"
version: "0.20.2a0"
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

Stage 11E4 evaluates whether the spatial hypotheses retained by Stage 11E2 have
usable temporal support in the Stage-11E0b registered trajectory evidence. It
preserves the exact E2 core, basin, transition-region, supported-background,
unsupported, and numerically unresolved distinctions. It does not fill
unassigned samples by nearest center and does not yet produce the final
hysteretic event catalog of Stage 11E6.

The implementation owner is:

```text
mdstats.analysis.density.temporal_assignment
```

The stage consumes one source-compatible triple:

```text
FrameworkAlignedIonSampleCatalog
PeriodicSpeciesDensityEstimate
DensityAttractorCatalog
```

## Coordinate-identical partition transfer

The density and attractor catalog normally bind directly to the assignment
sample catalog. A separate full-weight assignment catalog may be supplied only
when the spatial-discovery catalog is also supplied and exact transfer identity
is proven. The two catalogs must have the same source, registration, topology,
species, atom ordering, frame ordering, registered Cartesian coordinates,
wrapped fractional coordinates, and integer image shifts. Only statistical or
represented-time weights may differ.

A successful transfer records both catalog signatures and
`partition_transfer_identity = exact_registered_coordinate_identity`. Any
mismatch fails closed; the operation never remaps by nearest coordinate, atom,
frame, or site center. This contract permits a represented-time quadrature
catalog to discover the spatial partition while a coordinate-identical full
trajectory catalog supplies contiguous temporal evidence.

and may additionally bind one compatible `ForceRefinementCatalog`. The force
catalog is provenance only at this stage; temporal assignments remain determined
by E0b positions and E2 spatial topology.

# Borrowed methods and package-specific constructions

Core-set metastability and transition-path reasoning follow the established
Markov-state-model literature, including Sarich, Noe, and Schuette (2010), DOI
10.1137/090764049, and Guarnera and Vanden-Eijnden (2016), DOI
10.1063/1.4954769. The initial-positive-sequence truncation used for local
integrated autocorrelation estimates follows Geyer (1992), DOI
10.1214/ss/1177011137.

The following are mdstats-specific constructions:

- exact signature binding across E0b, E1, E2, and optional E3 inputs;
- immutable raw membership classes with no nearest-center fallback;
- explicit unsupported and numerically unresolved path gaps;
- a preliminary core-entry/basin-retention interval state machine;
- separate jump, return-excursion, unresolved-gap, and right-censored outcomes;
- independent temporal-support and evidence-pattern statuses;
- segment-aware represented-time weighting and trajectory-reset handling;
- a pooled, site-conditioned periodic-coordinate autocorrelation diagnostic; and
- deterministic serialization and transactional resource preflight.

# Input compatibility

The following identities must agree before any assignment is evaluated:

- E0b sample-catalog signature and registration signature;
- E1 catalog signature, registration signature, and periodic domain;
- E2 density-estimate, domain, and kernel signatures; and
- optional E3 sample, density, attractor, and registration signatures.

The E1 logical grid and E2 supported periodic cell complex must have identical
shape. Every E0b species sample must have one valid frame, atom, segment, and
registered fractional coordinate.

A source mismatch fails before interval, passage, or autocorrelation allocation.

# Raw membership projection

For registered fractional sample coordinate $\mathbf q_n$ and logical grid shape
$\mathbf N=(N_1,N_2,N_3)$, the nearest periodic node is

$$
\mathbf g_n
=
\operatorname{rint}(\mathbf q_n\odot\mathbf N)
\bmod \mathbf N.
$$

This projection chooses a grid node, not a statistical center. The node's E2
classification is authoritative.

Each sample receives exactly one raw class:

```text
evidence_excluded
core
basin
transition_region
supported_background
unsupported_unknown
numerically_unresolved
core_overlap
```

Core membership is evaluated from exact E2 provisional-core node sets. A node
belonging to more than one core is `core_overlap` and is not resolved by ordering,
nearest anchor, or basin ownership.

Only `core` and `basin` samples carry an attractor/basin identity. Transition,
background, unsupported, unresolved, overlap, and evidence-excluded samples keep
identity $-1$. Therefore

$$
\text{transition/background/unknown}\not\rightarrow
\text{nearest attractor}.
$$

The membership table retains sample, frame, atom, segment, logical-node,
classification, core, and basin arrays in frame-major sample order.

# Trajectory and ensemble semantics

Temporal intervals are constructed only for trajectory semantics. Independent
ensembles retain raw spatial membership but report
`ensemble_unavailable`; no continuity, dwell, passage, or autocorrelation is
invented between independent observations.

Trajectory continuity is restricted to one atom and one E0b segment. A source
segment boundary, missing represented-time interval, atom change, or explicitly
excluded evidence terminates the current temporal record. No interval or passage
may cross that boundary.

Represented-time weights are inherited exactly from E0b. Frame counts and
represented duration are stored separately because an irregular trajectory may
support frame-domain but not physical-time autocorrelation claims.

# Core visits

A `CoreVisitInterval` is a maximal contiguous run in one certified provisional
core for one atom and one segment. It stores:

- attractor identity;
- first and last sample/frame;
- represented duration and frame count;
- left- and right-censoring flags; and
- the source segment identity.

Core visits are observational records. A short core visit is not automatically a
metastable residence.

# Preliminary residence intervals

A residence begins on entry into a certified core. It is retained while samples
remain in that core or its E2 basin, including a temporary exit whose subsequent
core entry returns to the same attractor. It ends at the last retained sample
before one of:

- certified entry into a different core;
- an unsupported, unresolved, overlap, or excluded gap;
- a source discontinuity; or
- the right edge of the available trajectory.

A `PreliminaryResidenceInterval` records core-entry index, retained basin span,
represented duration, censoring, and the identity of the ending passage where
one exists. It is preliminary because Stage 11E6 will apply final hysteresis,
validated cores, and event acceptance.

# Preliminary passages

The interval between consecutive core visits is classified as one of:

```text
jump
return_excursion
unresolved_gap
right_censored_exit
```

A `jump` requires entry into a different certified core with no unsupported,
unresolved, overlap, or excluded sample in the intervening path. A return to the
same core is a `return_excursion`; it is not counted as a state transition.

Any unsupported or numerically unresolved path segment produces
`unresolved_gap`, even when a different core is observed later. The stage does
not bridge the gap by geometric proximity or temporal interpolation.

An exit without a subsequent core entry before the segment ends is
`right_censored_exit`. Censoring is evidence status, not a zero-duration event.

# Local decorrelation estimate

For provisional residence samples assigned to attractor $i$, let
$\mathbf q_i$ be its periodic anchor and let $G=LL^{\mathsf T}$ be the E1
analysis metric. Lift each sample relative to the anchor,

$$
\boldsymbol\delta_{q,n}
=
(\mathbf q_n-\mathbf q_i)
-
\operatorname{rint}(\mathbf q_n-\mathbf q_i),
\qquad
\boldsymbol\delta_{y,n}=\boldsymbol\delta_{q,n}L.
$$

The scalar normalized coordinate autocorrelation at lag $k$ is the trace-pooled
multivariate correlation

$$
\rho_i(k)
=
\frac{
\sum_n
(\boldsymbol\delta_{y,n}-\bar{\boldsymbol\delta}_y)
\cdot
(\boldsymbol\delta_{y,n+k}-\bar{\boldsymbol\delta}_y)
}{
\sum_n
\lVert\boldsymbol\delta_{y,n}-\bar{\boldsymbol\delta}_y\rVert^2
}.
$$

Following Geyer's initial-positive-sequence rule, paired sums

$$
\Gamma_m=\rho_i(2m)+\rho_i(2m+1)
$$

are accumulated only while positive. The statistical inefficiency and
integrated autocorrelation time are

$$
g_i=1+2\sum_k\rho_i(k),
\qquad
\tau_{i,\mathrm{frame}}=\frac{g_i}{2}.
$$

A physical-time estimate is reported only when represented-time stride is
sufficiently uniform. Otherwise the status is `frame_only_irregular_stride` and
only the frame-domain result is authoritative.

Possible statuses are:

```text
resolved
frame_only_irregular_stride
insufficient_samples
zero_variance
no_residence
```

The estimate is local and diagnostic. It is not a proof that the state is
Markovian or metastable.

# Excursion, recrossing, and persistence diagnostics

A return excursion is marked short when its frame count does not exceed

$$
N_{\mathrm{short},i}
=\max\!\left(
N_{\mathrm{short,min}},
\left\lceil c_{\mathrm{short}}\tau_{i,\mathrm{frame}}\right\rceil
\right),
$$

with the declared frame threshold used alone when $\tau_i$ is unavailable. A
pair of opposite resolved jumps is marked as recrossing when the intermediate
core-to-core span does not exceed the analogous maximum of the declared frame
threshold and a configured multiple of the local decorrelation time. These are
screening diagnostics rather than final event definitions.

For each attractor, the result records:

- number of core visits and preliminary residences;
- total represented residence duration;
- left/right censoring counts;
- jumps in and out;
- return excursions and short excursions;
- recrossing participation; and
- local decorrelation status and estimate.

The attractor receives a temporal-support status independent of the global
trajectory pattern:

```text
unavailable
insufficient
persistent
nonpersistent
stride_sensitive
```

The complete catalog separately reports one evidence pattern:

```text
ensemble_unavailable
no_core_entry
single_state
one_jump
repeated_hopping
short_excursion_only
excursions_only
mixed_hopping_and_excursions
unresolved_gaps_only
```

Thus one observed jump is not conflated with repeated hopping, and a short return
excursion is not promoted to a transition.

# Stride sensitivity

The assignment state machine is re-evaluated on declared integer stride factors.
The diagnostic stores the number of visits, residences, jumps, excursions, and
unresolved gaps for each factor. A change in qualitative pattern or event counts
marks the result `stride_sensitive` without changing the raw full-resolution
membership table.

Stride sensitivity is a diagnostic of temporal resolution. It is not repaired by
smoothing or center filling in this stage.

# Resource and serialization contract

`TemporalAssignmentResourcePolicy` preflights:

- samples and atoms;
- intervals and passages;
- total autocorrelation terms; and
- serialized output bytes.

Resource failure is transactional. Options, membership tables, intervals,
passages, decorrelation estimates, attractor diagnostics, stride diagnostics, and
catalogs have deterministic SHA-256 signatures. Replay constructors reject
schema, signature, shape, enum, source-binding, and non-finite-value errors.

# Non-goals

Stage 11E4 does not:

- modify E2 basin ownership or provisional cores;
- create a final site catalog;
- apply final hysteretic segmentation;
- assign structural ring, tile, cage, or coordination labels;
- fit transition paths, committors, barriers, rates, or a Markov model;
- infer missing continuity in an ensemble;
- bridge unsupported or unresolved gaps; or
- use force evidence to overwrite positional assignment.

# Acceptance tests

The focused gate must demonstrate:

1. transition, background, unknown, unresolved, and overlap samples remain
   unfilled;
2. a single jump, repeated hopping, and a short return excursion produce distinct
   evidence patterns;
3. unsupported gaps prevent resolved-jump claims;
4. core visits, preliminary residences, censoring, and passages respect atom and
   segment boundaries;
5. irregular stride downgrades physical-time autocorrelation without deleting the
   frame-domain result;
6. stride sensitivity is reported separately from raw labels;
7. ensembles retain spatial membership but no temporal continuity;
8. source mismatch, resource excess, and serialization tampering fail closed; and
9. E0b--E3 adjacent-stage and public-API regressions remain clean.
