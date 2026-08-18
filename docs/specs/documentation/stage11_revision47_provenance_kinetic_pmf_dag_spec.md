---
title: "Stage 11 Revision 47 Provenance, PMF, Kinetic Cross-Fit, and Typed-DAG Consistency"
author: "mdstats"
date: "2026-07-27"
version: "0.20.16a0"
status: "normative planning contract"
---

# Purpose

This specification prevents thermodynamic-source ambiguity, mandatory cross-check
over-gating, PMF estimator conflation, in-sample kinetic validation, zero-event edge loss,
candidate-freeze ambiguity, source mixing, and weak dependency-edge semantics.

# Thermodynamic provenance and optional verification

Every thermodynamic result must include `ThermodynamicResultProvenance`, including the
estimator, source bundle, source records/channels, ensemble and target measure, state
semantics, coordinate measure/Jacobian, estimation partition, sampling, uncertainty, and
assumptions. A result whose own gates pass may be reported as
`source_qualified_unverified`. Cross-checking is optional unless the caller explicitly
requests a `cross_validated` product.

Verification status is one of `not_requested`, `unavailable`, `insufficient`, `agreed`,
`partially_agreed`, or `disagreed`. Disagreement blocks only a combined consensus and
retains both source estimates.

# PMF estimator split

- `PMF_DENSITY` produces `DensityPmfCertificate` without requiring force data.
- `PMF_FORCE` produces `ForcePmfCertificate` from E3B admissible mean-force evidence.
- `PMF_CROSSCHECK` is optional and compares compatible density and force PMFs.

# Cross-fitting and rates

`EvidenceCrossfitPartition` separates thermodynamic estimation from optional verification.
`KineticCrossfitPartition` separately owns `kinetic_model_selection`, `kinetic_model_fit`, and
`kinetic_model_validation` complete episodes. F0 uses fit evidence; E9B uses untouched validation
evidence. Crossing episodes are censored under a signed boundary policy.

`RateCandidateEdgeUniverse` is declared before rate fitting. It retains candidates with
valid at-risk exposure even when zero events are observed. Candidate edges and observed
event edges are distinct.

# Candidate freeze and source identity

E2 emits per-realization candidate catalogs. GR4 alone emits the
`FrozenCandidateCatalog`. All source-derived records carry one
`SourceTrajectoryBundleIdentity`; controls and coordinates from different bundles may not
be combined.

# Typed DAG

`stage11_dependency_graph.json` schema version 2 uses typed edges:

```text
source_identity_requires
execution_requires
promotion_requires
conditional_requires
optional_enrichment
optional_verification
supersedes
replay_triggers
```

Tests must verify source identity, required-edge acyclicity, PMF split, optional
thermodynamic verification, kinetic fit/validation separation, zero-event candidate-edge
support, GR4 freeze ownership, persistent model-generation records, and product-specific
E8b gates.

# Persistent model-generation contract

`StateModelGeneration` records the state catalog, parent generation, segmentation policy,
rate-candidate policy, and all partition signatures. `GenerationReplayPlan` lists the
bounded stages to replay after gating or semi-Markov revision.
`GenerationTerminationCertificate` records accepted, unsupported, cycle-prevented,
maximum-generation, or sampling-insufficient termination.

# E8b product separation

Geometry, thermodynamic, corridor, path, transition-state, event-network, and kinetic
comparisons are distinct products. THERMO4A is optional verification for basin
thermodynamics and cannot gate geometry or occupancy comparison. E6b gates path comparison;
THERMO3B gates transition-state comparison.

# Grid and correspondence policy

`stage11_grid_stopping_v1` and `stage11_feature_correspondence_v1` are versioned initial
presets. Exact values are serialized. A changed tolerance or cost definition requires a
new identifier and cannot silently change prior certificates.
