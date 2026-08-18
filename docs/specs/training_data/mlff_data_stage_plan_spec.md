---
title: "MLFF Training-Data System Contract Specification"
subtitle: "MLFF-DATA0"
author: "mdstats project"
date: "2026-08-04 (through DATA9B3A)"
geometry: margin=0.78in
toc: true
toc-depth: 2
numbersections: true
fontsize: 10.5pt
header-includes:
  - |-
    \usepackage{booktabs}
  - |-
    \usepackage{longtable}
  - |-
    \usepackage{microtype}
---

# Scope

This document is the cross-cutting current system contract for the mdstats MLFF training-data and fine-tuning workflow. It owns invariants that span multiple narrower module specifications: evidence-role separation, identity and lineage boundaries, leakage prevention, protocol identity, target/replay separation, MACE realization, calibration applicability, and append-only active-learning lineage.

The legacy filename is retained for stable repository references. It is **not** an implementation stage plan. Developer sequencing and future gates belong in `workplans/`; completed implementation chronology belongs in `docs/history/mlff/`. Narrower current specifications under this directory own module-local API, schema, algorithm, persistence, and runtime details.

# Normative principles

1. Source facts, eligibility, partition, selection, weighting, exposure, and
   acquisition are separate immutable record families.
2. A frame that has contributed a gradient is not independent validation
   evidence for that model.
3. Cross-validation SHALL train one fresh model per held-out evaluation fold.
4. A held-out evaluation fold SHALL NOT control stopping or checkpoint choice.
5. Every fold SHALL have a checkpoint-monitor domain disjoint from both its
   gradient-training domain and held-out evaluation fold.
6. Cross-validation SHALL be bound to the complete `TrainingProtocolIdentity`
   used for final training. Naive and replay protocols are different protocols.
7. Feature fitting, label-derived difficulty features, E0 fitting, and selection
   SHALL inspect only the applicable training domain.
8. Locked tests SHALL NOT affect fitting, selection, protocol choice, stopping,
   checkpointing, uncertainty calibration, or acquisition.
9. Locked tests SHALL be absent from training configurations and activated only
   after a `ProtocolFreezeRecord` and selected committee identity exist.
10. Partition-critical system-profile features SHALL exist before the outer
    partition is locked.
11. The first MACE adapter SHALL support one target label domain, an optional
    replay head, and fixed-file native training only.
12. The first MACE adapter SHALL verify native head ordering, checkpoint control,
    and target/replay exposure realization against its version lock.
13. Replay retention SHALL be governed by an explicit constraint and applied to
    saved candidate checkpoints.
14. Dynamic per-epoch resampling SHALL require a custom runtime adapter or
    explicit multi-job protocol; fixed files alone SHALL NOT claim that feature.
15. Active-learning calibration SHALL be bound to the actual final committee and
    a declared applicability domain.
16. Existing frame roles SHALL be inherited unchanged by active-learning child
    datasets unless a new evaluation lineage is explicitly created.

# Record-family contract

| Record | Owns | Must not own |
|---|---|---|
| `TrainingDataSource` | source path, hashes, composition, controls, ensemble, quality, label domain | frame eligibility or split role |
| `TrainingFrameRecord` | source-bound frame facts and identity references | eligibility, partition, selection, exposure, acquisition |
| `FrameEligibilityDecision` | post-DFT label/quality outcome | partition or training membership |
| `PartitionAssignment` | one statistical role under one partition policy | feature-selection outcome |
| `PartitionFeasibilityReport` | support for requested roles and declared reductions | fabricated independent cohorts |
| `PartitionIndependenceReport` | evidence grade, purge, correlation, and duplicate limits | claim of stronger independence than observed |
| `SelectionAssignment` | selected/not-selected and reasons | epoch use count |
| `ExposureAssignment` | head, epochs, weights, and use counts | independent-evidence claim |
| `MaceExposureRealizationRecord` | actual loader counts, duplication, batches, and property exposures | intended exposure only |
| `AtomicReferenceFitRecord` | training-domain E0 corrections and residual | held-out labels |
| `TrainingProtocolIdentity` | complete model/data/replay/objective/exposure/checkpoint protocol | mutable runtime observations |
| `ProtocolFreezeRecord` | frozen selected protocol and committee identities | evaluation results |
| `CandidateAdmissibilityDecision` | pre-DFT geometry and trajectory safety | DFT convergence claim |
| `AcquisitionDecision` | calibrated or rank-only acquisition result | post-DFT eligibility |
| `MaterialProfileIdentity` | user-declared phases, geometry, chemistry modifiers, and optional extensions | structural feature values or automatic classification claims |
| `AtomGroupCatalog` | immutable group selectors and phase linkage | per-frame group membership arrays unless owned by a provider artifact |
| `ConditionAxisCatalog` | axes whose coverage may matter | observed coverage or partition assignment |
| `IndependenceAxisCatalog` | candidate sources of independent evidence | proof that independent realizations exist |
| `MaterialProfileContracts` | digest-bound aggregate of the four declarative profile families | physical features, events, or validation results |

Every serialized record SHALL include a versioned schema and deterministic
content digest. Policy and decision records SHALL additionally carry their
policy identity and explicit failure reasons where applicable. Identity records
SHALL carry their declared parent or provider lineage rather than a fictitious
policy digest.

# Identity contract

## Source occurrence

`frame_uid` SHALL be derived from source identity and source frame index. It
identifies an occurrence, not a unique physical configuration.

## Geometry and label identities

The following identities SHALL be separate:

```text
geometry_fingerprint
label_payload_digest
labeled_configuration_fingerprint
```

`geometry_fingerprint` SHALL exclude energy, force, and stress labels.
`label_payload_digest` SHALL include selected labels and label-domain identity.
The combined fingerprint SHALL identify the same geometry with the same labeled
payload.

Leakage audits SHALL use exact UID overlap, exact geometry overlap, exact
labeled-configuration overlap, near-duplicate geometry/descriptor distance, and
forbidden temporal proximity.

# Label-domain and energy contract

A label-domain fingerprint SHALL be decomposed into:

```text
TheoryIdentity
EnergyReferenceIdentity
DerivativeConvention
NumericalQualityProfile
SoftwareProvenance
```

A versioned compatibility policy SHALL classify differences. Exact equality of
all provenance fields is not required; theory- or energy-reference differences
cannot be silently combined.

The first adapter SHALL export one target label domain per MACE bundle. Multiple
incompatible target domains SHALL produce multiple bundles.

The selected VASP energy channel SHALL be named, complete, and consistent with
the derivative labels. The channel identity SHALL be preserved in provenance.

# Atomic-reference contract

The structural `AtomicReferenceIdentifiabilityReport` SHALL record:

```text
count matrix
rank
singular values
condition number
null-space dimension
identifiable combinations
policy outcome
transfer limitations
```

It SHALL NOT contain fitted corrections or fit residuals.

Each fold and final training domain SHALL receive a separate
`AtomicReferenceFitRecord` containing:

```text
training-domain frame UIDs
element support
identifiability-report digest
foundation-checkpoint digest
fitted corrections
fit residual
solver/tolerance
policy outcome
```

The fit SHALL exclude held-out evaluation, checkpoint-monitor, outer monitor,
calibration, and locked-test labels. Missing elemental support SHALL fail or
invoke an explicit alternative policy.

An emitted MACE configuration SHALL contain the exact version-supported E0 value,
normally an explicit atomic-number mapping. A conceptual record name SHALL NOT
be written into the `E0s` field.

# Cell, strain, stress, and virial contract

ASE cell vectors SHALL be treated as rows. Fractional row vectors SHALL map as

$$
\mathbf r_{\mathrm{row}}=\mathbf s_{\mathrm{row}}\mathbf H.
$$

For reference cell $\mathbf H_0$ and current cell $\mathbf H_t$, the reported
deformation gradient acting on Cartesian column vectors SHALL be

$$
\mathbf F=\left(\mathbf H_0^{-1}\mathbf H_t\right)^T.
$$

The implementation SHALL record whether internal calculations use an equivalent
right-acting row-vector map. Tests SHALL include nonsymmetric shear and rotated
stretch fixtures.

Canonical `REF_stress` SHALL be a symmetric Cartesian 3 x 3 Cauchy-stress tensor
in eV/Angstrom^3, using the ASE/MACE sign convention verified by the version-
locked adapter. Virial and stress SHALL use distinct keys.

The export gate SHALL test units, sign, Voigt order, shear factors, and MACE
read-back. Missing stress MAY use `config_stress_weight=0.0` under an explicit
heterogeneous-label policy.

# Event, feature, and blinding contract

Full-resolution event detection SHALL run before ordinary thinning. Protected
events include coordination changes, site changes, ring crossings, topology
changes, strain extrema, and high but physical restoring-force excursions.

DATA4 SHALL provide partition-critical system-profile features before the outer
partition is locked. For LTA these SHALL include resolvable coarse ring-site,
off-center, coordination-change, site-change, ring-crossing, and framework-
integrity states.

Raw feature providers SHALL be partition-independent. Scaling, PCA, whitening,
or fitted metrics SHALL be represented by separate static templates and fitted
records:

```text
FeatureMetricPolicyTemplate
FoldFeatureTransform
FoldFeatureMetricFit
FinalFeatureTransform
FinalFeatureMetricFit
```

A static template SHALL define feature blocks, scaling rules, block/species
weights, retained dimensions, missing-block behavior, distance metric, dtype,
and tolerance. A fitted record SHALL contain only parameters learned from its
declared training domain.

Foundation descriptors may be computed for all domains. Foundation-model
residuals require DFT labels and SHALL be exposed only in a
`TrainingDifficultyFeatureCatalog` for the applicable training domain. Outer
monitor, calibration, held-out-fold, and locked-test residuals SHALL remain
blinded until authorized evaluation.

# Partition feasibility and outer-role contract

A `PartitionRoleBudgetPolicy` SHALL declare requested roles, minimum block counts,
minimum independence grades, and allowable reductions. A
`PartitionFeasibilityReport` SHALL classify support before assignment.

Allowed outcomes include:

```text
fully_supported
supported_with_temporal_blocks_only
calibration_deferred
challenge_set_external_only
reduced_cross_validation_folds
insufficient_for_locked_test
insufficient_for_requested_roles
```

The workflow SHALL NOT fabricate every role from a short trajectory to satisfy
fixed percentages.

Every feasible target label domain may define:

```text
development_pool
outer_monitor_validation
uncertainty_calibration
locked_interpolation_test
zero or more locked_challenge_tests
```

The calibration domain MAY be deferred to later independent calculations.
Locked tests SHALL remain operationally sealed.

The LTA profile SHALL use hierarchical applicable schemas rather than a global
Cartesian product:

```text
unstrained: composition x temperature x regime
strained: composition x reference-condition x strain-mode x sign x regime
```

Every cohort SHALL emit a `PartitionIndependenceReport` with machine-readable
grades such as independent replica, independent ordering, independent run,
purged temporal block, slow-state not decorrelated, or insufficient
independence.

# Cross-validation and training-protocol contract

A `TrainingProtocolIdentity` SHALL bind:

```text
foundation checkpoint and head
naive or multi-head mode
replay source, selection, and monitor
training objective and property weights
target/replay head weights
exposure backend and balancing policy
checkpoint metric and checkpoint-control policy
replay-retention policy
optimizer, scheduler, epoch cap, and seed policy
MACE adapter lock
```

A `CrossValidationJobFamily` SHALL contain $K$ independent jobs using the same
complete protocol. For fold $k$:

1. designate a held-out evaluation fold;
2. form the non-evaluation domain;
3. carve a deterministic purged checkpoint-monitor split;
4. fit transform, metric, E0, difficulty features, and selector only on the
   remaining gradient-training domain;
5. initialize a fresh model and optimizer;
6. train under the declared MACE checkpoint-control policy;
7. select and freeze a checkpoint without inspecting the held-out fold;
8. evaluate only then on the held-out fold;
9. emit out-of-fold predictions and independence grades.

A rotating inner-validation fold inside one evolving model is prohibited.
Cross-validation results from a naive protocol SHALL NOT be used as validation
of a replay protocol.

# Selection-budget contract

The selector SHALL construct one deterministic master order with mandatory
anchors followed by quota-interleaved evidence classes:

```text
representative coverage
species-environment coverage
rare events
descriptor FPS
difficulty enrichment
```

`SelectionBudgetPolicy` SHALL define counts or fractions and a deterministic
deficit-redistribution rule. Later evidence classes SHALL NOT be starved because
an earlier selector consumed the size budget.

Near-duplicate pruning SHALL occur during master-order construction. Requested
sizes SHALL be exact prefixes. A size smaller than the mandatory-anchor count is
infeasible.

Species-specific Li, Na, and K environment selection SHALL be available in the
LTA profile. Whole-cell framework-dominated descriptors alone are insufficient.

# Training objective, weights, and checkpoint metrics

`TrainingObjectivePolicy` SHALL define the loss family, energy/force/stress
weights, head weights, normalization, robust-loss settings, and missing-label
behavior.

`ConfigurationWeightPolicy` and `PropertyWeightPolicy` SHALL define
condition-, regime-, event-, quality-, and property-specific weights. Selection,
weighting, and exposure are separate decisions.

The first adapter SHALL use standard MACE configuration/property weights and
SHALL NOT claim a species-aware atomwise loss. It SHALL report species-resolved
force metrics and impose profile focus-group acceptance or checkpoint constraints. Any
custom species-aware loss SHALL create a different `TrainingProtocolIdentity`.

`CheckpointMetricPolicy` SHALL define the primary target scalar plus energy,
force, stress, species, worst-condition, rare-event, and replay-retention
constraints.

# Exposure and MACE realization contract

Exposure backends are:

```text
NATIVE_MACE_FIXED
CUSTOM_EPOCH_RESAMPLE
MULTI_JOB_RESAMPLE
FINAL_REFIT
```

The first adapter SHALL support only `NATIVE_MACE_FIXED`. Dynamic epoch
resampling SHALL NOT be represented by static files alone.

Every run SHALL emit a `MaceExposureRealizationRecord` containing:

```text
real_pt_data_ratio_threshold
pre-MACE target/replay counts
post-MACE effective target/replay counts
implicit duplication factor
expected and observed batches
configuration, energy, force, and stress exposures
```

The adapter SHALL disable implicit target duplication where supported. Otherwise
it SHALL bind the realized duplication to `TrainingProtocolIdentity` and fail if
observed loader counts differ from the accepted plan.

# MACE checkpoint-control and replay contract

The initial adapter target is `mace-torch==0.3.16`, with a tested compatibility
matrix. It SHALL capture package digest, source/tag identity, CLI help, and key
parser, loader, and training-loop source digests.

MACE 0.3.16 uses the last validation head for native scheduling, patience, and
best-checkpoint decisions. The accepted first mode is:

```text
NATIVE_TARGET_LAST_WITH_EXTERNAL_CONSTRAINT_AUDIT
```

The adapter SHALL:

1. verify that the target monitor is the last validation head;
2. prevent replay-head behavior from terminating training;
3. retain every evaluation checkpoint;
4. externally evaluate target, focus-group-resolved, and replay monitors;
5. apply `CheckpointMetricPolicy` deterministically;
6. fail closed when version-tested behavior changes.

Replay preparation SHALL precede replay-aware cross-validation. The replay
monitor SHALL be disjoint from replay training. `ReplayRetentionPolicy` SHALL
define baseline, metric, tolerated degradation, and failure/override behavior.

# MACE artifact contract

Extended XYZ SHALL contain only MACE-readable labels, weights, and compact stable
identities. Complete provenance and selection reasons SHALL live in a sidecar
manifest keyed by `frame_uid`.

The development bundle SHALL contain no locked-test path and SHALL include the
complete `TrainingProtocolIdentity`, objective, checkpoint metric, replay plan,
checkpoint-control policy, E0 mapping, and adapter lock.

The following artifacts SHALL be separate:

```text
development_bundle/
calibration_bundle/
sealed_evaluation_bundle/
evaluation_activation/
evaluation_results/
```

A sealed evaluation bundle MAY be prepared early. An
`EvaluationActivationDecision` SHALL require a `ProtocolFreezeRecord`, selected
committee identity, complete training-protocol digest, and checkpoint-selection
decision.

# Calibration and active-learning contract

Out-of-fold predictions MAY diagnose uncertainty ranking. Numerical thresholds
SHALL be calibrated from the actual final committee on a dedicated calibration
cohort.

`CalibrationApplicabilityDomain` SHALL record covered elements, compositions,
temperatures, strains, cell sizes, site/event classes, descriptor-distance
range, force/stress range, and framework-integrity state.

`CalibrationTransferDecision` SHALL classify candidates as:

```text
within_calibrated_domain
rank_only_outside_domain
recalibration_required
rejected_incompatible_domain
```

Locked tests are forbidden from calibration and acquisition.

Pre-DFT candidates receive `CandidateAdmissibilityDecision`. Child datasets
SHALL inherit existing roles unchanged by default. Selection-biased new labels
enter the development pool; independent random labels may form new
validation/calibration cohorts; predeclared challenges may form new locked
challenge sets. A full repartition SHALL create a new evaluation lineage.

# Authority and supersession

This specification owns only the cross-cutting invariants stated above. The dedicated current specifications listed in `README.md` own their module-local behavior and may refine implementation details without weakening these invariants. Runtime/product gates remain normative where they define current software behavior; developer implementation gates are non-normative coordination artifacts under `workplans/`.

The complete pre-DOC-GOV1 mixed specification, including completed stage chronology and historical/future developer planning, is preserved at `docs/history/mlff/manual_snapshots/mlff_data_stage_plan_spec_pre_doc_gov1.md` and is non-normative.

# Authority and supersession

This specification owns only the cross-cutting invariants stated above. The dedicated current specifications listed in `README.md` own their module-local behavior and may refine implementation details without weakening these invariants. Runtime/product gates remain normative where they define current software behavior; developer implementation gates are non-normative coordination artifacts under `workplans/`.

The complete pre-DOC-GOV1 mixed specification, including completed stage chronology and historical/future developer planning, is preserved at `docs/history/mlff/manual_snapshots/mlff_data_stage_plan_spec_pre_doc_gov1.md` and is non-normative.
