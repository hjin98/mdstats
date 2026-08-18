---
title: "Registered Position-Force Sample Catalog"
subtitle: "Stage 11E0b: compact species evidence, represented time, force provenance, and structural masks"
author: "mdstats"
date: "2026-07-25"
version: "0.19.98a0"
status: "implemented baseline; revision-42 admissibility-overlay migration planned"
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

## Revision-42 migration status

The current runtime baseline predates `SimulationControlCertificate`,
`ProductionRegimeCatalog`, `PmfAdmissibilityCertificate`, and
`EvidenceAdmissibilityOverlay`. Existing serialized catalogs may therefore
still contain legacy scientific masks. Revision 42 defines the target
migration: E0b retains raw availability and geometry masks only, while ENS/STAT
construct signed overlays. Until that implementation stage is complete, legacy
masks are compatibility data and cannot override unresolved ENS/STAT evidence.

Stage 11E0b creates the compact trajectory-evidence object consumed by later
nonparametric site discovery. It joins the immutable source collection to one
Stage-C0 registration without introducing a density estimator, site label,
basin, transition state, or kinetic rate.

The canonical module is:

```python
mdstats.analysis.site_samples
```

The scientific path is:

```text
source collection
    + certified FrameRegistrationResult
    + declared temporal segments
    + optional topology regimes
    + force and thermodynamic provenance
        -> compact one-species sample catalog
        -> exact evidence-channel views
        -> later density / force / validation stages
```

The catalog never eagerly materializes every ion-frame-ring or
ion-frame-tile descriptor. Structural annotations remain lazy and are resolved
only for an explicitly requested sample subset after a candidate has been
associated with a persistent structural identity.

# Coordinate and identity contract

One catalog contains exactly one atomic number. Let the selected atoms be

$$
A_Z=\{a_0,\ldots,a_{N_Z-1}\}.
$$

The compact sample index is frame-major:

$$
s=tN_Z+j,
\qquad
(t,j)\in\{0,\ldots,N_t-1\}\times\{0,\ldots,N_Z-1\}.
$$

Each sample retains:

- source frame index and persistent frame ID;
- source atom index and species atomic number;
- registered unwrapped Cartesian position;
- registered wrapped fractional coordinate and integer image shift;
- transformed force covector when available;
- represented-time weight;
- exact topology-regime ID or the explicit unknown value `-1`; and
- all evidence masks and provenance signatures.

The authoritative registration products are copied only for the selected
species. The catalog verifies independently that

$$
q_{ta}=x_{ta}M_t+b_t
$$

for the supplied source collection and registration. A registration produced
from a different collection fails closed even when array shapes happen to
match.

# Segment-aware represented time

## Continuous trajectory segments

A trajectory is divided into explicit continuous segments. Segment starts
include:

- frame zero;
- user-declared restart or discontinuity boundaries; and
- Stage-C0 translation-branch reset points.

No represented-time interval crosses a segment boundary.

For times

$$
t_0<t_1<\cdots<t_{n-1}
$$

inside one segment, the frame weights are the midpoint control-volume widths,
equivalently the sample weights of composite trapezoidal quadrature:

$$
w_0=\frac{t_1-t_0}{2},
$$

$$
w_i=\frac{t_{i+1}-t_{i-1}}{2},
\qquad 0<i<n-1,
$$

and

$$
w_{n-1}=\frac{t_{n-1}-t_{n-2}}{2}.
$$

A one-frame trajectory segment has no represented duration and is rejected
unless explicit nonnegative frame weights are supplied.

## Independent ensembles

Independent ensembles receive unit frame weights and every frame is a segment
start. This is a sample-count measure, not a temporal-continuity claim.

## Segment inclusion

A multi-segment trajectory requires explicit `included_segment_ids`. The
library does not silently pool restarts, heating, equilibration, or production
segments. Pooling a declared heating segment with a declared production segment
requires a separate explicit opt-in.

Every segment has one of the labels:

```text
heating
 equilibration
production
other
unknown
```

The labels are provenance. They do not infer equilibrium or stationarity.

# Topology regimes and structural evidence

`TopologyRegimeAssignment` retains per-frame:

- exact topology-regime ID;
- connectivity-flicker mask;
- structural-evidence mask; and
- optional source `TopologyCatalog` digest.

When an exact topology catalog is supplied:

- catalog frame IDs must match the source collection;
- exact topology IDs are projected to source-frame positions;
- transient topology segments are marked as connectivity flicker; and
- the two frames adjacent to each exact transition are marked as flicker by
  default.

A connectivity-flicker frame cannot simultaneously be accepted as structural
evidence. Unknown topology IDs may still retain position evidence when the user
has explicitly allowed the structural frame; the unknown identity remains
visible rather than being replaced by a guessed class.

# Nested evidence masks

For every compact sample, retain the source masks

$$
P_0,\quad F_0,
$$

the temporal and structural masks

$$
T,\quad S,
$$

and the connectivity-flicker diagnostic

$$
C.
$$

The effective position and force masks are defined exactly by

$$
P=P_0\land T\land S,
$$

$$
F=F_0\land T\land S.
$$

The matched density-force subset is

$$
J=P\land F.
$$

`joint_mask` must equal this intersection bit-for-bit. A matched force-density
comparison obtains positions, forces, identities, topology regimes, and weights
from the same compact sample indices. It is not permitted to recompute two
independent selections and assume they match.

# Force and PMF provenance

The catalog retains, without reinterpretation:

- source force completeness;
- bias or constraint-force evidence;
- stochastic or thermostat-force evidence;
- geometric force-transform status;
- PMF force-admissibility status;
- Stage-C0 registration signature; and
- explanatory reasons from the force-admissibility contract.

Ordinary geometric force evidence and thermodynamic PMF evidence are distinct.
A diagnostic structure-fitted force projection may remain available in `F` and
`J`, while remaining forbidden from the PMF subset.

The immutable E0b catalog stores raw availability and geometry masks. It does
not construct a PMF subset. A later `EvidenceAdmissibilityOverlay` may define

$$
J_{\mathrm{PMF}}
=
J
\land A_F
\land R
\land P,
$$

where:

- $J$ is the raw joint position/force availability mask;
- $A_F$ is the Stage-C0 force-coordinate admissibility result;
- $R$ selects a tested production regime from `ProductionRegimeCatalog`; and
- $P$ is the relevant accepted permission in `PmfAdmissibilityCertificate`.

No user declaration or untested stationarity assertion can set $R$ or $P$.
Framewise temperatures remain provenance and do not become one PMF temperature
implicitly. Unresolved prerequisite certificates produce an unresolved or empty
overlay while preserving the raw catalog.

# Sampling-state and temperature provenance

Source declarations, tested diagnostics, and promotion decisions remain separate:

```text
source_declaration:
    user_comment_only
    explicit_protocol_claim
    unknown

diagnostic_status:
    resolved
    unresolved
    insufficient
    rejected
    unavailable
    not_applicable

promotion_decision:
    accepted
    conditional
    blocked
    rejected
```

Every overlay records the exact ensemble, production-regime, PMF-admissibility,
policy, and E0b signatures.

`PMFTemperatureProvenance` distinguishes:

```text
declared_constant
framewise_observed
unavailable
unknown
```

A constant PMF temperature must be positive and include a source declaration.
An observed framewise range is never promoted automatically to a thermodynamic
PMF declaration.

# Evidence views and measures

The catalog exposes exact views for:

```text
position
force
joint
pmf_force
```

Each view contains the selected compact indices, source frame/atom identities,
registered positions, forces when required, represented-time weights, and
regime IDs.

For channel $K$, the ion-time measure is

$$
\mathcal T_K=\sum_{s\in K}w_s.
$$

The normalized sample weights are

$$
\widehat w_s=\frac{w_s}{\mathcal T_K}.
$$

Later density stages must state whether they use ion-time measure, normalized
probability measure, or mean occupancy. Stage 11E0b stores the source measure
but does not choose a density normalization.

# Lazy structural annotations

`LazyStructuralAnnotationView` accepts a resolver callable and materializes
annotations only for:

- one declared evidence channel; or
- one explicit compact sample-index sequence.

The resolver returns a mapping of arrays with leading dimension equal to the
requested sample count. Results are immutable and cached by exact sample-index
tuple. The catalog itself stores no eager
$N_{\mathrm{ion}}N_{\mathrm{frame}}N_{\mathrm{ring}}$ tensor.

The resolver is intentionally not serialized. It is executable analysis logic,
not source evidence.

# Multi-trajectory registration groups

`FrameRegistrationGroup` certifies that multiple trajectory registrations share
one fixed periodic domain. Every member must have:

- identical periodic axes;
- one fixed registered cell within the declared tolerance;
- the same analysis-geometry metric digest; and
- a registered cell equal to the shared cell within tolerance.

The group retains member source-contract and registration signatures, internal
cell deviations, cross-member deviation, and a group signature. A grouped
catalog records its exact member index and group signature.

The group does not assert kinetic pooling, equilibrium equivalence, identical
force provenance, or statistical exchangeability. Those are later validation
questions.

# Serialization and immutability

All persistent records use strict JSON schemas and deterministic SHA-256
signatures. Arrays become read-only copies at construction. Catalog signatures
bind:

- compact identities and coordinates;
- transformed force values;
- time weights and regime IDs;
- every evidence-mask signature;
- temporal, topology, force, state, and temperature provenance;
- source, registration, policy, and optional registration-group signatures; and
- JSON-safe metadata.

A changed coordinate, mask, weight, provenance field, or signature fails replay.
Lazy annotation resolvers and caches are not serialized.

# Failure behavior

The stage fails closed for:

- no matching species atoms;
- mixed atomic numbers in one species catalog;
- a registration not bound geometrically to the collection;
- frame IDs that disagree across temporal or topology products;
- hidden pooling of multiple trajectory segments;
- heating/production pooling without explicit opt-in;
- non-increasing times inside a continuous segment;
- one-frame trajectory segments without explicit weights;
- selected force evidence without transformed forces;
- a connectivity-flicker sample accepted as structural evidence;
- a joint mask unequal to the exact position/force intersection;
- a PMF mask outside the joint subset;
- incompatible multi-trajectory registered domains; or
- malformed or tampered serialized records.

# Public API

The principal entry points are:

```python
prepare_trajectory_segment_weighting(...)
prepare_topology_regime_assignment(...)
prepare_frame_registration_group(...)
prepare_framework_aligned_ion_sample_catalog(...)
```

The principal records are:

```python
TrajectorySegmentWeighting
TopologyRegimeAssignment
SamplingStateProvenance
PMFTemperatureProvenance
SampleForceProvenance
SampleEvidenceMasks
FrameRegistrationGroup
FrameworkAlignedIonSampleCatalog
SpeciesSampleEvidenceView
LazyStructuralAnnotationView
```

They are exported from `mdstats.analysis` and the package root.

# Acceptance requirements

- Represented-time weights do not cross declared discontinuities.
- A multi-segment trajectory is not pooled without an explicit segment subset.
- Heating and production are not mixed silently.
- One catalog contains one species and the exact registered C0 coordinates.
- Position, force, joint, and PMF evidence use their declared immutable masks.
- `joint_mask` is exactly `position_mask & force_mask`.
- Matched position-force views use identical compact sample indices and weights.
- Connectivity-flicker frames remain explicit and are excluded from structural
  evidence.
- Diagnostic geometric forces can remain visible without becoming PMF evidence.
- PMF evidence requires force, equilibrium, stationarity, and constant-temperature
  provenance simultaneously.
- Structural annotations are lazy and subset-bound.
- Compatible registration groups certify one fixed periodic domain and reject
  mismatched cells, metrics, or periodic axes.
- Serialization replay is deterministic and tamper-evident.

# Deferred work

Stage 11E0b does not implement:

- periodic kernel density estimation;
- density scores, metric gradients, or Hessians;
- attractors, ridges, basins, or scale selection;
- structural candidate association;
- M--O or M--T fingerprints;
- force-field reconstruction;
- residence segmentation;
- transition-path extraction; or
- rate estimation.

These remain Stage 11E1 and later boundaries.

# Method provenance

The midpoint control-volume weights are standard composite-trapezoidal sampled
data quadrature; SciPy documents the equivalent trapezoidal integration rule
[1]. Stage 11E0b's segment resets, explicit inclusion gate, compact evidence
catalog, exact nested-mask algebra, conservative PMF subset, registration-group
certificate, and lazy structural annotation boundary are project-specific
constructions.

Force covector transformation and PMF admissibility are not re-derived here;
they are inherited from the Stage-C0A1/C0A2 coordinate specifications.

# Reference

[1] SciPy Developers. `scipy.integrate.trapezoid` documentation.
<https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.trapezoid.html>.
