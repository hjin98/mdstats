---
title: "MLFF Physical Observable Validation Bridge Specification"
author: "mdstats project"
date: "2026-07-30 (v3 evidence and leakage closure)"
geometry: margin=0.82in
toc: true
numbersections: true
fontsize: 10.5pt
---

# Scope

`mdstats.training_data.observable_validation` owns MLFF-specific pairing,
statistical role, trajectory lineage, and later comparison decisions around
analysis-owned observables. It does not implement or reinterpret the observable.

# Advisory recommendation profile

`ObservableRecommendationProfile` lists currently executable baseline calls for
generic condensed, crystalline, amorphous, liquid, and interface use cases. It
is not the future compositional material-profile system. The
`MaterialValidationProfile` name remains a compatibility alias only.

# Verified collection identity

`ObservableCollectionIdentity` records frame semantics, dimensions,
composition digest and counts, frame selection, geometry, dynamics, labels,
provenance status, and source-content digests. Human labels and filesystem paths
are location metadata and do not change scientific identity.

A supplied identity is never trusted. The bridge recomputes the identity from
the collection actually passed to the analysis and rejects any mismatch.
Object-dtype arrays are rejected because pointer bytes are not stable content.
Large systems store composition counts and sequence digest without requiring the
entire atomic-number sequence in evidence.

# Symmetric trajectory-generation identity

`TrajectoryGenerationIdentity` is used for both reference and candidate
trajectories. It binds:

- generator kind and artifact digest;
- optional generator manifest;
- calculation or MD protocol digest;
- exact output collection digest;
- engine and version;
- runtime environment;
- initial configuration and source provenance when available;
- precision policy, random seed, and notes.

The older `MLFFTrajectoryGenerationIdentity` is a compatibility wrapper. Under
complete-lineage mode it must explicitly declare `output_collection_digest`.
The bridge verifies both reference and candidate generation records against the
actual collections.

# Statistical role and activation

Every plan contains an `ObservableEvidenceRole`:

- `training_diagnostic`;
- `checkpoint_monitor`;
- `outer_validation`;
- `calibration`;
- `locked_test`;
- `external_benchmark`.

`ObservableValidationActivationRecord` binds partition policy/assignment,
predeclared comparison-policy identity, protocol freeze, and locked-test
activation as required by the role. Locked-test execution fails unless all
required upstream identities are present.

The permitted order is:

```text
comparison policy + activation + frozen protocol/partition identity
                     -> observable execution evidence
                     -> comparison result
                     -> acceptance decision
```

Realized evidence must never tune its own thresholds or retroactively alter data
selection, training protocol, checkpoint selection, calibration policy, or
active-learning acquisition.

# Plan and evidence

`MLFFObservableValidationPlan` binds the recipe, advisory profile, paired labels,
lineage requirement, ionic-chain declaration, activation record, notes, and
bridge version.

`MLFFObservableValidationEvidence` stores:

- verified reference/candidate collection identities;
- symmetric generation identities;
- runtime and capability identities;
- warnings and durations;
- paired native result types;
- paired analysis-owned `ObservableResultIdentity` records;
- activation and recipe/plan digests.

`MLFFObservableValidationEvidenceRecord` is a lightweight restorable,
digest-verified summary. It does not load or duplicate scientific arrays.

# Execution

```python
run_mlff_observable_validation(
    reference_collection,
    candidate_collection,
    plan,
    reference_generation=...,
    candidate_generation=...,
)
```

Complete lineage is required by default. Diagnostic callers may explicitly
disable the gate, but such evidence is not production validation evidence.

# Ownership

The MLFF bridge owns recipe selection, pairing, lineage, role activation,
comparison-policy identity, aggregation, and eventual checkpoint decisions. RDF,
coordination, dynamics, transport, thermomechanical, energetic, and path
algorithms remain under their own analysis architectures.

# Comparison layer

Revision 0.20.52a0 implements the separate `ObservableComparisonPolicy`,
`ObservableComparisonResult`, and `ObservableAcceptanceDecision` records in
`mdstats.training_data.observable_comparison`. The bridge still owns only
execution, pairing, and lineage; numerical discrepancy and checkpoint decisions
remain downstream policy objects.

# Required tests

Tests verify:

- supplied-identity mismatch rejection;
- symmetric complete lineage;
- output-collection binding;
- relocation-invariant identity;
- role and locked-test gates;
- analysis-owned result digests;
- evidence-record round trip and tamper rejection;
- recipe equality and paired runtime/capability lineage;
- no evidence-to-policy reverse dependency.
