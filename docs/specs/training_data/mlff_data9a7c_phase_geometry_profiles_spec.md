---
title: "MLFF-DATA9A7c Phase and Geometry Profiles"
version: "0.20.49a0"
date: "2026-07-30"
status: "implemented"
---

# Purpose

MLFF-DATA9A7c converts the explicit material contracts introduced by DATA9A7a
into immutable, phase- and geometry-aware defaults for MLFF data preparation.
The stage does not infer a material type. The user declares the phases,
geometry, chemistry modifiers, structural extensions, and atom groups; the
runtime then derives an auditable default selection plan.

The plan distinguishes:

- crystalline solids;
- amorphous solids;
- liquids;
- molecular or gas-like phases;
- bulk, surface, interface, confined, and cluster geometries.

An interface is a geometry containing two or more declared phases. It is not a
peer phase type.

# Ownership boundary

`mdstats.training_data.phase_geometry_profiles` owns only policy composition:

- active selection-grade feature families;
- active generic structural-event families;
- geometry-aware atom-group priority ordering;
- numerical default policy selection for the existing local-structure call;
- advisory identifiers for currently executable physical observable recipes;
- immutable plan identity and lineage.

`mdstats.analysis.local_structure` continues to own all numerical geometry:
minimum-image distances, switching functions, smooth coordination, radial and
angular projections, local density, and orientational order. The physical
observable modules continue to own RDFs, coordination distributions, angle
distributions, topology, dynamics, transport, and thermomechanical analyses.

# Phase defaults

Every phase contributes a set of selection feature families and temporal event
families. Multiple phases contribute the union of their requirements.

## Crystalline solid

Activate pair distance, radial environment, smooth coordination, weighted
connectivity, chemical-neighbor diversity, local density, angular environment,
and orientational order. The event path includes displacement, coordination,
neighbor-count, density, and orientational-order changes.

Orientational order is selection-grade evidence for loss of crystalline order,
polymorphic changes, and defect-like environments. It is not a replacement for
symmetry analysis, polyhedral template matching, phonons, or elasticity.

## Amorphous solid

Activate the same universal families, with a broader radial and density window.
The representation emphasizes distributions of local coordination, angle,
packing, and chemical environment while retaining orientational order as a
continuous measure of local ordering.

## Liquid

Use the broad disordered-phase radial and density window. Coordination,
chemical-neighbor diversity, local density, radial/angular structure, and
neighbor-change events are primary. Orientational order remains enabled as a
freezing or local-order detector, not as an assumption that a liquid possesses a
reference lattice.

## Molecular or gas-like phase

Activate pair distance, radial, coordination, connectivity, chemical,
density, and angular families. Bond-orientational order is excluded by default
because it is generally not a stable universal summary for sparse molecular or
gas-like configurations. Molecular internal coordinates and reaction-aware
features remain separate future providers.

# Geometry composition

Geometry changes coverage priority; it does not redefine phase physics.

## Bulk

Prioritize declared `bulk_like` groups and then phase-defining groups.

## Surface

Prefer groups carrying `surface`, `subsurface`, or `bulk_like` roles. If no
surface-region group is declared, execution remains possible but records the
warning `surface_region_groups_not_declared`.

## Interface

Require at least two phases through the DATA9A7a contract. Prefer `interface` or
`interfacial` groups, then phase-bulk and surface-related groups, followed by
each phase-defining group. Missing explicit interface groups produce
`interface_region_group_not_declared`; this is not silently replaced by an
inferred geometric slab.

## Confined system

Prefer `guest`, `confined`, `host`, `confining`, and interface groups. If none
are declared, record `confinement_role_groups_not_declared` and retain the phase
groups as a safe fallback.

## Cluster

Prefer surface and core groups when supplied. Nonperiodicity remains an input
collection property owned by the numerical analysis call.

# Immutable plan

`PhaseGeometrySelectionPlan` records:

- material-profile and aggregate-contract digests;
- declared phase kinds and geometry;
- enabled feature families and event types;
- ordered priority atom groups and roles;
- analysis-owned `LocalStructureFeaturePolicy` parameters;
- frame-aggregation statistics;
- advisory observable-recommendation profile IDs;
- warning codes;
- parser, schema, and plan versions.

The plan is deterministic for one `MaterialProfileContracts` value and is
round-trip serializable with digest verification.

# DATA6 integration

DATA6 schema v3 stores the phase/geometry plan next to universal structural
catalogs. When a profiled DATA4 bundle requests universal structural features:

1. derive the phase/geometry plan;
2. derive or bind a `UniversalStructuralSelectionPolicy` to the plan digest;
3. calculate all numerical local features through the analysis-owned kernel;
4. expose only the feature families enabled by the plan;
5. record only enabled generic event types;
6. aggregate declared atom groups and authorized per-element groups;
7. serialize plan, provider, policy, and material-profile lineage together.

An explicit user override is allowed, but it is rebound to the active plan. A
policy carrying a different plan digest is rejected.

DATA6-v1 and DATA6-v2 bundles remain readable. Historical catalogs without a
phase/geometry plan retain their historical semantics and do not acquire a
fabricated plan during deserialization.

# Selection integration

Generic atomic-environment selection first covers profile-priority atom groups
within each species, then performs the ordinary per-species environment pass.
This gives interfaces, surfaces, and confined regions explicit representation
without introducing a material-specific selector.

The feature metric continues to fit only authorized DATA5 roles. Phase and
geometry policy cannot inspect sealed frames to discover feature columns,
species, or atom groups.

# Physical-observable recommendations

The compositional profile may be mapped to one or more advisory
`ObservableRecommendationProfile` identifiers. The corresponding observable IDs
are a baseline of currently executable calls only. They are not a complete
validation recipe and contain no hidden scientific parameters. Interface
profiles compose the recommendations of their phases and the interface call
profile. Ionic transport remains an explicit user extension.

# Failure rules

Fail closed when:

- an interface contains fewer than two phases;
- profile phase groups are absent from the atom-group catalog;
- a universal structural policy references a different phase/geometry plan;
- DATA6 plan, material contracts, and structural catalog digests disagree;
- every structural feature family is disabled;
- a serialized plan or bundle fails digest or schema validation.

Missing optional surface, interface, or confinement region groups produce
explicit warnings rather than inferred membership.

# Acceptance tests

The stage is complete only when tests demonstrate:

- distinct crystalline, liquid, and molecular defaults;
- interface composition from solid and liquid phase profiles;
- geometry-role priority ordering and warning behavior;
- plan serialization and tamper evidence;
- plan-bound DATA6 construction and feature-family filtering;
- physical-observable recommendation composition;
- DATA6-v2 read compatibility;
- no implicit LTA activation;
- no sealed-role materialization;
- source and installed-wheel public API parity.
