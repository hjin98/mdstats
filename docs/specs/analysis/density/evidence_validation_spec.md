---
title: "Joint Evidence Validation and Structural Association Specification"
subtitle: "Stage 11E5"
author: "mdstats"
date: "2026-07-25"
version: "0.20.3a0"
status: "implemented baseline; revision-42 production-regime migration planned"
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

## Revision-42 migration status

The implemented E5 baseline consumes the legacy E0b evidence fields. Revision 42
defines the replacement contract in which E5 consumes an exact signed
`ProductionRegimeCatalog` and `EvidenceAdmissibilityOverlay`. This document
specifies that target migration without claiming that ENS/STAT runtime modules
already exist. Untested stationarity remains unresolved during the migration.

Stage 11E5 freezes one selected Stage-11E2 statistical-state catalog and combines
its independent evidence channels without replacing them by one opaque score. It
also associates each learned state with persistent Stage-C0A3 ring, window, or
natural-tile/cage objects in the registered density domain.

The implementation owner is:

```text
mdstats.analysis.density.evidence_validation
```

The stage consumes one source-compatible chain:

```text
FrameworkAlignedIonSampleCatalog          (E0b)
PeriodicSpeciesDensityEstimate             (E1)
DensityAttractorCatalog                    (E2)
ProvisionalTemporalAssignmentCatalog       (E4)
RegisteredStructuralGeometryView           (C0A3)
optional ForceRefinementCatalog            (E3)
```

It produces an immutable `ValidatedFrozenCatalog`. An optional all-data refit is
stored separately as `FinalRefitCatalog` and cannot inherit parameter-validation
evidence for relocated centers or boundaries.

This stage does **not** compute M--O/M--T coordination fingerprints, assign final
structural classes, perform geometry-conditioned moving-boundary refinement,
publish final hysteretic events, or estimate barriers and rates. Those remain
Stage 11E5a, E5b, E6, and later responsibilities.

# Borrowed methods and package-specific constructions

The separation of model construction, selection, and independent validation is
standard statistical practice. Core-set metastability and held-out validation
for molecular-state models follow the established Markov-state-model literature,
including Sarich, Noe, and Schuette (2010), DOI 10.1137/090764049, and Prinz et
al. (2011), DOI 10.1063/1.3565032.

The following are mdstats-specific constructions:

- exact E0b--E4 and C0A3 source-signature binding;
- an orthogonal status lattice for spatial, temporal, force, force-score,
  stationarity, geometry, curvature, and final-validation evidence;
- comparison of force covectors only with the density score covector in the same
  registered coordinate measure;
- a fail-closed structural-association radius with no nearest-object fallback;
- retention of all plausible structural objects when the primary association is
  ambiguous;
- explicit `selection_conditioned_validation` and
  `independent_validation_unavailable` outcomes;
- conservative exchangeability checks before any structural symmetry orbit is
  accepted;
- prohibition of default symmetry augmentation of trajectory samples; and
- a strict frozen-catalog versus final-refit distinction.

# Source compatibility

Before any validation or structural-distance work, the following identities must
agree:

- E1 sample-catalog signature equals the supplied E0b catalog;
- E2 density-estimate signature equals the supplied E1 estimate;
- E4 sample, density, and attractor signatures equal the supplied E0b--E2 chain;
- optional E3 sample, density, and attractor signatures equal the same chain;
- the C0A3 registered-structural-view registration signature equals the E0b
  registration signature; and
- the E1 periodic domain registration signature equals the E0b registration.

State counts must agree across E2, E3, and E4. A mismatch fails before structural
candidate enumeration or block summaries are allocated.

# Discovery, selection, validation, and refit blocks

`EvidenceBlockPlan` records four complete-system frame sets:

```text
discovery_frame_indices
selection_frame_indices
final_validation_frame_indices
optional_refit_frame_indices
```

The first three roles are evaluated as follows:

- disjoint nonempty discovery, selection, and final-validation sets produce
  `independent_selection_and_validation`;
- overlap with final-validation data, overlap between discovery and selection,
  or absent selection data produces `selection_conditioned_validation`; and
- absent final-validation data produces `independent_validation_unavailable`.

The optional refit set may include all frames because it is used only after the
validation decision has been frozen.

For state $i$ and block $B$, the implementation records sample count, core count,
basin count, represented ion time, block ion-time fraction, and mean frame
occupancy. The represented-time fraction is

$$
\widehat P_{i,B}
=
\frac{
\sum_{n\in B} w_n
\mathbf 1\{n\in C_i\cup B_i\}
}{
\sum_{n\in B} w_n
\mathbf 1\{n\text{ is position evidence}\}
}.
$$

Independent transfer is supported only when selection and validation blocks each
contain the declared minimum state support and their ion-time fractions agree
within the declared tolerance. If one basin occurs mainly before a single jump
and another mainly after it, missing support in one held-out block is reported as
`insufficient_transfer_support`, not as state rejection.

# Orthogonal evidence status

Each `ValidatedStatisticalState` contains one `SiteEvidenceStatus` with separate
fields:

```text
spatial
temporal
force
force_score_consistency
stationarity
geometry
curvature
final_validation
overall
```

The common channel vocabulary is:

```text
resolved
supported
unavailable
insufficient
ambiguous
disagreement
rejected
unresolved
```

## Spatial evidence

A resolved isolated or manifold attractor with a stable E2 topology certificate
is `resolved`. A supported attractor whose topology is not yet independently
assessed is `supported`. Flat unresolved components remain `unresolved`; an
unstable topology certificate is retained as `disagreement`.

## Temporal evidence

E4 statuses map without reinterpretation:

| E4 temporal status | E5 channel status |
|---|---|
| `persistent` | `resolved` |
| `nonpersistent` | `rejected` |
| `stride_sensitive` | `ambiguous` |
| `insufficient` | `insufficient` |
| `unavailable` | `unavailable` |

## Force and curvature evidence

Every E2 state is preserved when force data are absent or PMF provenance is
inadmissible. E3 `resolved` force fits become resolved force evidence. Missing
forces remain unavailable; rejected PMF provenance remains rejected; rank,
support, and conditioning failures remain insufficient or unresolved.

Stable-point and soft-manifold E3 curvature classes are resolved curvature
evidence. Saddle/unstable curvature is explicit disagreement with a stable-site
interpretation.

## Stationarity evidence

E5 consumes the signed `ProductionRegimeCatalog` and its canonical diagnostic
status. A tested stationary production regime maps to resolved evidence. A
selection-conditioned or conservation-warning regime may map to conditional or
unresolved evidence according to policy. Tested nonstationarity maps to rejected;
insufficient independent blocks map to insufficient; unavailable diagnostics remain
unavailable. User labels and untested stationarity assertions never produce supported
evidence.

# Force-to-score-covector consistency

For registered fractional coordinate $\mathbf q$, the E1 density score is the
covector

$$
\mathbf s_q(\mathbf q)=\nabla_q\ln \widehat p(\mathbf q).
$$

At equilibrium, the conditional force covector is compared with

$$
\overline{\mathbf F}_q(\mathbf q)
\stackrel{?}{=}
k_{\mathrm B}T\,\mathbf s_q(\mathbf q).
$$

The comparison is never made against an unqualified Euclidean gradient or the
metric-raised vector. E5 consumes the matched E3 residual. A residual above the
declared threshold is `disagreement`; it is not repaired by changing the metric,
force sign, or state center.

# Registered structural association

Structural identities remain species-independent and are supplied by C0A3. E5
uses registered fractional centers only to evaluate association distance; the
physical geometry record remains attached for later exact bond-distance and
coordination work.

For attractor anchor $\mathbf q_i$, structural center $\mathbf c_j$, and E1
analysis metric $G$, the certified torus distance is

$$
d_G(i,j)
=
\min_{\mathbf n\in\mathbb Z^3}
\sqrt{(\mathbf q_i-\mathbf c_j-\mathbf n)^{\mathsf T}
G
(\mathbf q_i-\mathbf c_j-\mathbf n)}.
$$

The closest lattice image is found by the certified finite enumeration owned by
C0A2. Candidate objects are retained only when their mean resolved-frame
distance does not exceed `maximum_association_distance`.

Supported object kinds are:

```text
ring
window
tile_cage
```

Each `StructuralAssociationCandidate` stores:

- persistent structural identity;
- mean and maximum registered distance;
- geometric score;
- optional species-independent structural-chemistry consistency score;
- resolved-frame support count; and
- a physical-geometry reference.

If no object lies inside the declared radius, the association is `unresolved`.
The nearest object outside the radius is not inserted. If the two best retained
candidates differ by no more than `association_ambiguity_distance`, the
association is `ambiguous`, no primary object is selected, and all candidates
remain available. Otherwise the best retained candidate is primary and the
others remain secondary.

A `StructuralSiteComplex` groups distinct statistical states only when they have
the same resolved primary structural identity. State instances remain distinct.

# Overall certification

The overall status is derived from the orthogonal channels, not from a weighted
sum:

```text
spatial_candidate
spatial_temporal_validated
force_validated
fully_validated
evidence_disagreement
rejected
unresolved
```

A force-free trajectory may reach `spatial_temporal_validated` but cannot reach
`force_validated` or `fully_validated`. A state may be force validated without
independent final validation. `fully_validated` additionally requires resolved
or supported stationarity, resolved structural association, and independently
supported final validation.

Any force-score, curvature, topology, or independent-transfer disagreement
remains `evidence_disagreement`. Temporal nonpersistence or declared
nonequilibrium can reject a stable-site claim. Missing channels lower
certification but do not delete the state.

# Symmetry exchangeability

No symmetry orbit is created by default. A caller must provide explicit
`SymmetryOrbitCandidate` records with member state identities, ideal
multiplicity, and symmetry provenance.

Before an orbit can be marked `supported`, the implementation compares:

- ion-time probability;
- mean frame occupancy;
- structural object kind and structural-chemistry signature;
- temporal persistence;
- observed outgoing transition counts; and
- force/curvature evidence.

An explicit mismatch gives `rejected`. Missing channels give `insufficient`.
Only fully available and compatible evidence gives `supported`. Regardless of
status,

```text
augmentation_performed = false
```

and no trajectory sample is copied, rotated, or multiplied by ideal symmetry.
The observed kinetic network continues to use statistical-state instances as
nodes.

# Frozen and refit catalogs

`ValidatedFrozenCatalog` stores the exact selected state anchors, basins,
provisional cores, evidence statuses, block summaries, structural associations,
complexes, and optional orbit diagnostics that were applied to validation data.
The stage does not relocate these parameters during validation.

An optional `FinalRefitCatalog` records a later all-data E2/E3 parameter refit. It
must preserve the validated state count and decision identity, but it always
stores:

```text
decision_inherited = true
parameter_validation_inherited = false
```

Therefore evidence obtained for frozen centers and boundaries is not silently
attributed to moved refit parameters.

# Resource policy

`JointEvidenceResourcePolicy` limits:

- state count;
- state--structural-object candidate work;
- block-membership work;
- orbit pair comparisons; and
- serialized records.

Limits are checked before their corresponding allocations. Resource failure is
transactional and produces no partial catalog.

# Serialization and public API

Every public E5 record is immutable and carries a deterministic SHA-256
signature over canonical JSON and array digests. Replay verifies nested
signatures and rejects tampered evidence, association, orbit, or source records.

Public preparation functions are:

```python
prepare_validated_frozen_catalog(...)
prepare_final_refit_catalog(...)
```

# Acceptance tests

The focused gate requires:

- force-free spatial/temporal validation without force certification;
- fully validated harmonic evidence when all channels and independent transfer
  agree;
- explicit matched-force/score-covector disagreement;
- ambiguous multi-object association with no nearest fallback;
- unresolved association when every object lies outside the declared radius;
- one-transition early/late blocks yielding insufficient or unavailable
  validation rather than rejection;
- opt-in symmetry candidates with exchangeability checked before grouping;
- explicit selection-conditioned and unavailable-validation outcomes;
- a separate final-refit record with no inherited parameter validation;
- deterministic serialization, tamper rejection, source binding, resource
  preflight, and public API stability.

# Next boundary

Stage 11E5a adds species-dependent M--O/M--T coordination fingerprints and
continuous structural classification. It must consume the E5 structural
association rather than rediscovering or forcing a nearest ring.
