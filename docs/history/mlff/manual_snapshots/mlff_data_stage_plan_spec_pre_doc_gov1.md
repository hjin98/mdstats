---
title: "MLFF-DATA Stage and Data-Contract Specification"
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

This specification freezes the canonical stage order and controlling data
contracts for the future `mdstats.training_data` branch. It is subordinate to
`mlff_training_data_architecture.{md,pdf}` and normative where it uses **MUST**,
**MUST NOT**, **SHALL**, or **SHALL NOT**.

No public runtime object is implemented at MLFF-DATA0. DATA1 through DATA8, DATA9A hardening through DATA9A9c, and DATA9B1 through DATA9B3A are implemented; later stages MUST NOT expose a public placeholder before its specification, tests, and gate are complete. The
mdstats core has no mandatory MACE, PyTorch, or replay-data dependency.

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

# Stage gates

## MLFF-DATA0

Freeze architecture, stage order, data contracts, dependency graph, references,
PDFs, tests, and release records. No runtime API.

## MLFF-DATA1 - implemented in 0.20.29a0

Implemented source-independent autocorrelation, complete-frame blocks, purge,
and deterministic assignment. Stage 11 public and serialized behavior is
preserved by exact parity fixtures.

## MLFF-DATA2 - implemented in 0.20.30a0

Implemented deterministic manifest/discovery, immutable VASP source catalogs,
composition reconstruction, ensemble references, named energy policy,
decomposed label identities, complete-link label-domain grouping, optional
quality/production references, and per-label-domain structural atomic-reference identifiability.
No frame eligibility, fitted E0 value, or MACE artifact is introduced.

## MLFF-DATA2A - automatic review-manifest inference gate - implemented in 0.20.60a0

DATA2A is an operational refinement of DATA2 source discovery. The first campaign
`prepare` invocation SHALL read completed VASP XML controls and cell matrices,
infer reviewable ensemble, thermostat, target-temperature, timestep, and fixed-cell
metadata, and propose LTA strain intent from filenames. Filename values at or
above one SHALL default to percent semantics, so `hydro+5` means +5%, while
`hydro+0.05` remains a fractional +0.05 volume change.

A proposed fixed-cell strain relationship SHALL NOT become an operational
assertion or reference group until the actual right-polar stretch and volume ratio
match the exact LTA hydrostatic, volume-preserving orthorhombic, or symmetric
right-polar shear definition. Candidate references may differ in temperature;
temperature ranks geometry-passing candidates but never overrides a failed cell
relationship. Rejected or ambiguous candidates SHALL remain diagnostic only, emit
a warning, and leave both the strained run and that candidate relationship in the
conservative ungrouped state. Manifest approval remains mandatory. The DATA2
source gate SHALL also recover a demonstrably trailing interrupted XML stream
when controls, atom identities, and complete ionic records are unambiguous. It
SHALL retain complete records, conditionally recover one complete but unclosed
final calculation, and record the interruption as soft-quality evidence. Mid-file
corruption and critically incomplete streams remain hard failures.

## MLFF-DATA3 - implemented in 0.20.31a0

Implemented immutable frame facts, manifest-bound occurrence UID, geometry/label identities, exact duplicate and restart detection, post-DFT eligibility, temperature conditions, reference-cell resolution, and the normative ASE-row finite-strain convention. No partition, fitted feature, selection, or MACE artifact is introduced.

## MLFF-DATA4 - implemented in 0.20.32a0

Implemented partition-independent raw physical features, lightweight full-resolution LTA ring/site states, event-anchor and protected-window catalogs before thinning, deterministic canonical-JSON feature caching, and `PartitionRoleBudgetPolicy`. The stage records role requests only; DATA5 retains feasibility and assignment ownership. No fitted transform, partition, selection, label-derived evaluation residual, or MACE artifact is introduced.

## MLFF-DATA5 - implemented in 0.20.33a0

Implemented full-resolution eligible-frame partition units, condition-aware autocorrelation blocks, protected-event-window preservation, role-budget feasibility, deterministic outer development/monitor/calibration/locked-test/purge assignments, independence evidence including replicas and declared structural realizations, independent cross-validation folds with nested checkpoint monitors, blinding boundaries, and fail-closed duplicate/event/role/purge leakage audits. The stage introduces no fitted metric, selection, MACE descriptor, or training artifact.

## MLFF-DATA6 - implemented in 0.20.34a0

Implemented profile-aware universal structural and optional extension features, optional checkpoint-bound MACE atomic descriptor sidecars, canonical final-development and fold-training difficulty domains, data-derived species and focus-group residuals, blinded outer/calibration/fold prediction catalogs, sealed locked-test records, and immutable DATA6 orchestration. MACE and PyTorch remain optional lazy dependencies. No fitted transform, E0 fit, weighting, selection, or training artifact is introduced.

## MLFF-DATA7 - implemented in 0.20.35a0

Implemented canonical final/fold training domains, static feature-metric templates, fold-local and final robust/standard fitted metrics, optional deterministic block PCA, domain-local explicit E0 fits with rank/null-space audits, training objective and configuration/property weight policies, focus-group-resolved checkpoint policies, quota-interleaved deterministic master orders, strict nested ladders, and coverage reports. No MACE training or evaluation artifact is introduced.

## MLFF-DATA8 - implemented in 0.20.36a0

Implemented verified minimal extended XYZ plus sidecar export, explicit atomic-number E0 mappings, a version-locked MACE compatibility/source probe, local replay preparation and disjoint monitor artifacts, fixed-file exposure, checkpoint-control policy, complete `TrainingProtocolIdentity`, loader realization dry runs, independent final/fold job bundles, and sealed evaluation artifacts. No MACE process is executed and no locked test is materialized.

## MLFF-DATA9 - integration qualification and protocol execution

### MLFF-DATA9A - integration and production qualification

The mdstats-side hardening is implemented in 0.20.37a0, the offline MACE
runtime bootstrap in 0.20.38a0, and real MACE artifact realization/execution
smokes in 0.20.39a0. Implemented contracts include foundation-residual E0
fitting, portable artifact paths, complete extended-XYZ round-trip validation,
replay property/provenance/element audits, explicit selection-level job
generation, source-declared dependency manifests, isolated local-artifact
installation, installed-runtime qualification, v0.3.16 scalar-literal YAML
serialization, fixed-file target/replay weight realization, genuine parser and
loader dry runs, one-epoch training, checkpoint/head inventory, target-head
extraction, and finite evaluation round trips. The supplied dependency bundle
and MPA-0 checkpoint pass these gates. DATA9A3 in 0.20.40a0 closes the
target-corpus portion of the production gate: all 27 trajectories and 37,632
complete frames pass DATA3-DATA5 with a passing leakage audit. No expensive
protocol training may begin until the exact frozen production-corpus plan,
checkpoint-bound DATA6/DATA7, verified DATA8-generation, and replay-corpus artifacts close
the full DATA9A gate.

### MLFF-DATA9B - protocol-matched execution and freeze

DATA9B remains gated until DATA9A records a dependency-complete genuine MACE
runtime, successful naive and replay smoke jobs, identified MPA-0 and replay
artifacts, qualified optional profile-extension evidence where declared, checkpoint-bound production
DATA6/DATA7 evidence, and executable DATA8 job artifacts. The target-corpus
DATA2-DATA5 benchmark is complete.

Execute independent protocol-matched cross-validation and final-development
jobs; catalog every candidate checkpoint; apply target, profile focus-group, stress, and
replay-retention constraints; generate training-size learning curves; compare
naive and replay protocols; train multiple seeds; construct the final committee;
extract the target head; and emit the `ProtocolFreezeRecord`.

### MLFF-DATA9B1 - campaign and checkpoint control - implemented in 0.20.56a0

Freeze the exact mode/selection-size/seed experiment matrix after a passed full
DATA9A gate. Bind every fold and final run to its exact DATA8 job, protocol
family, seed variant, monitor artifacts, and `mdstats-mace-train` wrapper.
Inventory every saved checkpoint by contained path, epoch, size, and SHA-256.
Record externally evaluated target/focus/stress/worst-condition/replay metrics;
apply the frozen `CheckpointMetricPolicy`; reject incomplete or threshold-
violating candidates; and select the deterministic constrained optimum only
when every cataloged checkpoint has a decision.

### MLFF-DATA9B2 - execution, aggregation, committee, and freeze - implemented in 0.20.57a0

Supervise exact MACE commands with bounded retries and restart-latest semantics;
record immutable process/log/environment evidence after every attempt and terminate
complete process groups under the frozen timeout/grace policy; automatically evaluate every
checkpoint on target and replay monitors; aggregate protocol-matched folds and
seeds; construct learning curves; compare complete naive and replay families;
export selected final target heads into a seed committee; emit
`ProtocolFreezeRecord`; and activate sealed evaluation only after exact lineage
verification.

The runtime and record contracts are complete and pass bounded real-MACE smoke
tests. The actual long production campaign remains gated on completing the real
production DATA6-DATA8 realization and binding the intended production replay
corpora.

### MLFF-DATA9B3 - unified campaign CLI and bounded verification - implemented in 0.20.58a0

Expose DATA2-DATA9B2 through one source-checkout UNIX-style command with one
TOML configuration, digest-approved manifest, one SQLite orchestration database,
compact status/benchmark/result outputs, source-local critical-precision wrapper
shims, and fail-closed stage advancement. Wrap production preparation, DATA9A
qualification, required real-MACE preflight, restartable training, checkpoint evaluation, protocol
comparison, committee export, and protocol freeze. Add bounded committee-wide
NVE deployment checks and actionable failure guidance without claiming the
analysis-owned RDF/diffusion acceptance responsibilities of DATA11. Qualify
replay as a first-class production input: checkpoint-bound pseudo-label
provenance, geometry-disjoint train/monitor sets, target-element coverage, and
minimum corpus sizes are mandatory unless an exploratory override is explicit.

### MLFF-DATA9B3A - cuEquivariance campaign backend - implemented in 0.20.59a0

Freeze the MACE execution backend as `e3nn` or `cueq`; resolve the initialization
default once from the active environment; require a real foundation-model CuEq
smoke in `doctor`; bind package/CUDA probe evidence to the campaign; and propagate
the same backend through DATA6, DATA8, preflight, production training, checkpoint
evaluation, and bounded verification. Reject silent fallback and reject
`only_cueq=true` for the portable production path.

## MLFF-DATA10

Implement active-learning candidate admissibility, out-of-fold uncertainty
diagnostics, final-committee calibration, applicability/transfer decisions,
calibrated or rank-only acquisition, burst deduplication, DFT queries, labeled-
round ingestion, append-only role inheritance, and immutable child generations.

## MLFF-DATA11

Run complete regression, real-data preparation, partition-feasibility cases,
naive and replay protocol-matched cross-validation smoke jobs, MACE checkpoint
control and exposure-realization tests, final committee calibration, sealed-test
activation, active-learning replay, and performance acceptance.

# Testing requirements

The branch SHALL include tests for:

- graph acyclicity and forbidden dependencies;
- no edge from locked tests to fit, selection, difficulty, calibration,
  checkpoint, or acquisition;
- record-family and static-template/fitted-record separation;
- label compatibility classification;
- E0 rank/null-space reporting and exact explicit mapping export;
- fold/final E0 fits excluding monitors and holdouts;
- ASE-row strain convention with nonsymmetric shear and rotated stretch;
- stress units/sign/Voigt/shear round trip;
- exact and near-duplicate geometry across copied/restart sources;
- event-before-thinning ordering;
- partition-role feasibility reductions;
- fold-local transform, metric, E0, difficulty, and selector isolation;
- checkpoint-monitor/held-out evaluation separation;
- complete protocol identity equality between cross-validation and final runs;
- deterministic quota-interleaved master-order prefixes;
- species-resolved checkpoint constraints;
- replay train/monitor disjointness;
- target-last validation-head control for every supported MACE version;
- save-all candidate checkpoint audit;
- implicit replay-ratio duplication detection and realization accounting;
- dynamic-resampling rejection by the fixed-file adapter;
- locked tests absent from development MACE configurations;
- protocol-freeze requirements before evaluation activation;
- final-committee calibration identity and applicability binding;
- append-only role inheritance and immutable dataset lineage;
- clean-wheel import and artifact read-back when runtime APIs are added;
- exact MACE `setup.cfg` dependency-manifest parsing;
- offline local-artifact installation with `--no-index`;
- missing-dependency fail-closed behavior without compatibility stubs;
- genuine CLI help and short-training smoke records once the environment is complete.
- protocol-selected float32/float64 config realization and serialized-model dtype inspection;
- float64-foundation to float32-trained transition evidence and float64 control evidence;

# Documentation requirements

Each runtime module receives a Markdown/PDF specification before implementation.
External algorithms and version-dependent MACE behavior are cited. mdstats-local
policy choices, thresholds, and tie-breaking rules are identified as such.

The normative bibliography is maintained in
`mlff_training_data_architecture.{md,pdf}`.

### MLFF-DATA9A3 - implemented in 0.20.40a0

Qualified the complete bulk-LTA target corpus through DATA5. The target-corpus
gate passes with explicit temporal-block and weak-independence warnings. DATA9B
remains blocked on the exact frozen production-corpus plan, complete production
DATA6/DATA7 realization, verified DATA8 generation, and production replay identity.

### MLFF-DATA9A4 - selectable precision implemented in 0.20.41a0

The DATA8 optimizer policy owns the requested MACE fine-tuning precision. Both
`float32` and `float64` are supported even when the foundation MPA-0 checkpoint
is uniformly float64. Parser realization, execution, saved-model inspection,
and target-head inspection MUST agree with the protocol-selected precision.
Mixed floating-point state fails closed. Real one-epoch transfer smokes for both
precisions are required before release. The production 2,734-frame DATA6--DATA8
realization remains a separate unfinished gate and DATA9B remains closed.


### MLFF-DATA9A5a - critical-FP64 execution implemented in 0.20.42a0

Training and inference model bodies remain independently selectable as float32
or float64. For the qualified Python/ASE MACE 0.3.16 path, TF32 is disabled and
atomic-energy, virial, and stress reductions plus returned observables are
safety-locked to float64. ASE positions, cell, masses, and momenta are audited
as float64 before MD. Optimization-time force Jacobians remain in the selected
model dtype because the upstream FP32 second-derivative graph rejects an FP64
scalar seed. Production DATA6-DATA8 realization and DATA9B remain separate gates.


### MLFF-DATA9A5b - deployment-artifact closure implemented in 0.20.43a0

mdstats owns deterministic export of a uniformly `float32` or `float64` MACE
model, exact state conversion, reload validation, immutable provenance, and a
model-specific inference smoke. Float32-to-float64 promotion is not precision
recovery. LAMMPS is a downstream consumer of the selected model; its internal
mixed precision, reductions, Kokkos kernels, and integration behavior are not
mdstats implementation or qualification targets. No LAMMPS-specific implementation stage is created.

### MLFF-DATA9A6 - observable ownership bridge implemented in 0.20.44a0

The analysis branch now owns a standardized call registry and immutable recipes
for implemented structural, topology, dynamical, spectral, and transport
observables. The MLFF branch owns only material-profile recommendations,
reference/candidate pairing, invocation lineage, and later comparison policy.
No RDF, coordination, angle, connectivity, diffusion, VDOS, or conductivity
algorithm is duplicated in `training_data`.

### MLFF-DATA9A6b - architecture and observable-evidence consistency closure - implemented in 0.20.45a0

The canonical manuals, indices, stage identifiers, and dependency graph are
reconciled. `ObservableAnalysisRecipe` rejects self, unknown, forward, and
missing dependencies during construction. Capability records expose
machine-checkable collection requirements, required/alternative arguments,
versioned codecs, owner-signature identities, and result hints. Execution
preflights collection semantics and records warnings, runtime versions, and
capability digests.

`ObservableCollectionIdentity` records exact scientific collection identity while
keeping filesystem paths as non-identity location hints. DATA9A6b introduced the
candidate-generation record, runtime evidence, and capability contracts; the
remaining verification and leakage gates are closed in DATA9A6c.

The temporary flat enum is renamed `ObservableRecommendationProfile`;
The obsolete flat `MaterialValidationProfile` alias has been removed. A separate
thermomechanical and energetic validation architecture now owns EOS, elasticity,
finite-temperature response, stress-correlation viscosity, phonons, surfaces,
interfaces, defects, and migration paths.


### MLFF-DATA9A6c - observable evidence and leakage closure - implemented in 0.20.46a0

The bridge SHALL verify caller-supplied collection identities against the actual
arrays and reject object-dtype identity inputs. Production evidence SHALL bind
both reference and candidate trajectories through symmetric
`TrajectoryGenerationIdentity` records whose `output_collection_digest` equals
the analyzed collection identity.

Every native analysis result SHALL receive an analysis-owned
`ObservableResultIdentity`. The MLFF bridge SHALL store only those identities,
paired types, warnings, durations, runtime identity, and upstream lineage; it
SHALL NOT define a competing scientific-result schema. A lightweight
`MLFFObservableValidationEvidenceRecord` SHALL round-trip and detect tampering
without loading result arrays.

Every execution SHALL declare an `ObservableEvidenceRole`. Outer-validation,
calibration, locked-test, and external-benchmark roles SHALL bind a comparison
policy selected before realized evidence. Locked-test execution SHALL also bind
partition policy/assignment, protocol freeze, and explicit evaluation
activation. Observable evidence SHALL NOT tune its own comparison policy or
retroactively alter selection, training protocol, checkpoint choice,
calibration policy, or acquisition.

Runtime evidence SHALL identify the executing mdstats source/version and module
hash separately from installed-distribution metadata. Capability identity SHALL
include owner implementation source digest and a stable owner-manual ID/URI.

### MLFF-DATA9A7a - material-profile and atom-group contracts - implemented in 0.20.47a0

Immutable compositional phase, geometry, chemistry-modifier, structural-extension,
atom-group, condition-axis, and independence-axis contracts are public. The
runtime-checkable `SystemProfileProvider` owns declarative identity only. DATA4
schema v2 may carry the aggregate contract while retaining v1 read compatibility.
The one-phase fallback declares only `all_atoms`; multi-phase and interface
systems require explicit atom-group membership. Generic defaults do not activate
LTA modules or extensions.

### MLFF-DATA9A7b - universal structural selection providers - implemented in 0.20.48a0

The analysis-owned local-structure kernel now supplies chemistry-scaled smooth
coordination, nearest-neighbor and radial-basis features, weighted connectivity,
local-density proxies, angular Legendre moments, and bond-orientational order.
The MLFF provider aggregates these features by declared atom groups and present
elements, records generic geometry-only temporal events, and threads immutable
catalogs through DATA6 schema v2. DATA7 may fit the `universal_structural` block,
and generic per-species environment FPS prefers these descriptors. Existing
checkpoint-bound MACE descriptors remain the learned novelty path. DATA6 v1 is
read-compatible, generic defaults do not activate LTA, and sealed roles cannot
be materialized.

### MLFF-DATA9A7c - phase and geometry profiles - implemented in 0.20.49a0

The explicit DATA9A7a material contracts now derive one immutable
`PhaseGeometrySelectionPlan`. Crystalline, amorphous, liquid, molecular/gas,
and custom phases contribute universal feature-family and generic event-family
defaults. Bulk, surface, interface, confined, cluster, and custom geometries
contribute atom-group priority ordering and explicit missing-region warnings.
An interface composes two or more phase profiles and is not a peer phase value.

DATA6 schema v3 stores the plan, binds the universal structural policy to its
digest, filters exposed selection features/events by the enabled families, and
prioritizes profile-declared surface/interface/phase groups before generic
per-element environment coverage. DATA6-v1/v2 remain readable. The profile also
composes advisory IDs for currently executable physical-observable calls without
moving any numerical observable into the MLFF branch.

### MLFF-DATA9A7d - optional profile-extension and LTA migration - implemented in 0.20.50a0

Canonical DATA4/DATA6 evidence now stores generic partition- and selection-stage
`ProfileFeatureCatalog` envelopes. LTA ring, cage, window, site, and crossing
payloads remain provider-owned and are consumed only through common frame,
atomic-environment, and environment-class adapters. Generic profiles never
activate LTA; the explicit `porous_network -> zeolite -> lta` chain is required.

DATA4 schema v3 and DATA6 schema v4 remove LTA-named top-level fields from new
serialization while retaining v1-v3 read compatibility and deprecated Python
views. Generic feature metrics and selectors derive species from authorized
roles, and optional focus groups replace fixed Li/Na/K policies. Structural
realization and extension-coverage records replace cation-ordering and LTA-site
concepts in generic evidence.

### MLFF-DATA9A7e - cross-system qualification - implemented in 0.20.51a0

Run bounded DATA4--DATA7 workflows for generic crystal, amorphous solid,
liquid, multiphase interface, and LTA-extension cases. Persist immutable
clean-import, per-case, and complete-suite evidence. Generic cases must not
import the MLFF LTA implementation modules, activate the `lta` extension, or
serialize legacy LTA top-level fields. The LTA case must use the explicit
porous/zeolite/LTA hierarchy and generic extension envelopes. Qualification
proves software-path generality and lineage, not physical model validity.

### MLFF-DATA9A8 - profile-aware observable comparison policies - implemented in 0.20.52a0

Implement frozen rule, threshold, score-uncertainty, comparison-result, and
acceptance-decision records over native analysis-owned results. Bind policies to
the recipe, observable recommendation profile, optional material-profile
contracts, statistical role, atom-group/condition scopes, and pre-execution
activation digest. Implement absolute, symmetric-relative, normalized-RMSE,
integrated-curve, Jensen--Shannon, peak-shift, and exact-mismatch scores. Reject
reverse policy fitting from realized evidence and preserve locked-test leakage
gates.

DATA9A8 also removes misleading deprecated public aliases and pre-generalization
objective/checkpoint/partition/coverage schemas while retaining only the
currently justified DATA4/DATA6 cache readers.

### MLFF-DATA9A9a - restartable checkpoint-bound DATA6 model sweep - implemented in 0.20.53a0

Derive the exact DATA5-authorized descriptor and prediction frame sets from the
active DATA6 policy. Persist per-frame descriptor and prediction sidecars with
file and numerical content digests. Maintain an atomically replaced
`Data6ModelSweepCheckpoint` that supports bounded execution, interruption,
failure evidence, resume, and corruption recovery. Bind a complete sweep to
DATA6 schema v5 and reuse persisted predictions when constructing residual and
blinded-summary catalogs. Locked-test, purge, excluded, and otherwise
unauthorized frames remain outside the requested union.

### MLFF-DATA9A9b - production DATA6--DATA8 materialization - implemented in 0.20.54a0

Freeze one complete DATA6 sweep together with every canonical final and fold
DATA7 domain, all fitting/selection policies, the exact replay train and monitor
artifacts, the foundation checkpoint, and the MACE execution policies. Persist
one verified DATA7 bundle per domain, resume after interruption, invalidate
DATA8 after any upstream modification, and emit a verified final/fold DATA8
artifact tree. `ProductionMaterializationRecord` binds the completed DATA7 and
DATA8 evidence and is the required input to production qualification and DATA9B.

### MLFF-DATA9A9c - production-gate integrity closure - implemented in 0.20.55a0

DATA9A9c binds production qualification to an immutable `ProductionCorpusPlan`
containing exact source/frame identities, expected runs, condition summaries,
fold count, optional-extension evidence requirements, and required DATA9A
artifacts. Foundation descriptors/predictions and foundation-residual E0 are
derived from verified DATA6/DATA7 evidence rather than caller Booleans. Replay
semantic identity includes numerical energy, force, and stress payloads while
excluding intentionally transformed configuration weights. Foundation and replay
paths are non-identity location hints. DATA8 is built in a hidden staging tree,
promoted to a content-addressed generation, and exposed through an atomic pointer
switch. Materialization loaders reverify artifacts before deserialization.
DATA9B remains closed until the real production plan passes this gate.

The control layer is implemented and qualified on a bounded complete workflow.
The full 2,734-frame corpus must still finish DATA9A9a and then execute this
DATA9A9b plan before DATA9B protocol-matched training and freeze begin.


### MLFF-PERF1 - profiled campaign execution and bounded-state persistence - implemented in 0.20.62a0

Require one normalized VASP decode per source, bounded source concurrency,
checksummed resumable frame caches, constant-time catalog access, vectorized
per-frame numerical kernels, and memory-bounded DATA4 persistence. Approval must
not implicitly start expensive work. Every long stage and external subprocess
must expose actionable progress, elapsed time, and either ETA or heartbeat
evidence. Production validation must use the complete supplied LTA corpus and
preserve scientific identities across optimized and reference kernels.


### MLFF-PERF2 - resource-aware parallel and GPU execution - implemented in 0.20.63a0

The campaign SHALL detect effective CPU threads, currently available RAM, selected
CUDA availability, and free VRAM. Automatic plans SHALL target configurable
fractional budgets whose current defaults are 0.90 for CPU and GPU/VRAM and 0.80
for RAM. Worker assignment SHALL be bounded by
independent task count, CPU budget, estimated per-worker memory, and memory reserved
for the accumulated parent-side result. Explicit worker overrides SHALL NOT bypass
those hard bounds.

Source ingestion, DATA3 construction, raw DATA4 features, and profile-specific
trajectory features SHALL support process-level parallel execution. Object-heavy
paths SHALL NOT use Python thread pools. High-volume workers SHALL suppress nested
BLAS/OpenMP parallelism and release native state after each trajectory. LTA process
results SHALL use compact typed columns rather than transferring the immutable
record hierarchy. Scientific field values and ordering SHALL match the serial path.

DATA6 SHALL use native MACE graph batching only when the source-locked MACE adapter
qualifies that path. Automatic batch size SHALL be bounded by the configured fraction
of free VRAM, and CUDA OOM SHALL reduce the batch and retry without invalidating
already verified frame artifacts. DATA8, preflight, and training SHALL receive one
CPU/RAM-bounded MACE DataLoader worker plan. GPU acceleration SHALL be used only for
kernels whose arithmetic intensity justifies transfer and conversion overhead.

All plans and long-running stages SHALL emit informative progress. Production
qualification SHALL compare serial and parallel scientific identities and execute
the complete supplied LTA corpus, including interrupted XML sources.


### MLFF-PERF4 - adaptive evaluation and verification inference - implemented in 0.20.86a0

Checkpoint evaluation and bounded NVE verification SHALL execute independent
inference jobs concurrently. CUDA execution SHALL start with one job and SHALL
admit one additional job only after fixed-window telemetry projects both aggregate
VRAM and GPU utilization strictly below their configured ceilings, whose defaults
are 0.90. CPU execution SHALL divide the effective 0.90 thread budget among outer
jobs and SHALL use aggregate CPU-utilization telemetry for admission. All phases
SHALL retain the 0.80 available-RAM budget.

The scheduler SHALL bound concurrency by task count, effective CPU allocation,
available-RAM budget, estimated per-job RAM/VRAM, and optional user caps. Runtime
parallelism SHALL NOT enter evaluation-policy, checkpoint-metric, selection, or
verification-case scientific digests. Existing completed verification cases SHALL
remain reusable when their immutable model, structure, runtime dependency, and
scientific integration identities are unchanged.

Parallel checkpoint evaluation SHALL serialize the first authenticated monitor
parse and the first foundation-model metric calculation per immutable cache key;
candidate-model inference may remain concurrent. Parallel verification SHALL give
each active case a private mutable ASE/MACE calculator. Campaign-state database
writes SHALL remain in the parent scheduler thread.


### MLFF-PERF5 - true-inference telemetry gating - implemented in 0.20.87a0

Evaluation and verification admission telemetry SHALL begin only after every active
worker at the current concurrency level reaches its first real model forward pass.
Checkpoint materialization, monitor parsing, model/calculator construction, CUDA
context initialization, and other setup phases SHALL NOT contribute samples or
advance the calibration clock.

The default calibration window SHALL be 60 seconds. The scheduler SHALL require
both elapsed-window coverage and the corresponding minimum sample count. Any change
in active job count, any newly admitted worker that has not signaled true inference,
or loss of telemetry SHALL reset calibration. A higher concurrency level SHALL NOT
reuse initialization samples or steady-state samples from the previous level.

GPU promotion SHALL continue to require projected aggregate VRAM and GPU utility
strictly below their 0.90 ceilings. CPU promotion SHALL use the same first-forward
gate and SHALL reset the stateful CPU counter at gate entry so initialization cannot
contaminate the first utilization interval. RAM SHALL remain bounded at 0.80.

The canonical configuration key SHALL be
`parallel_inference_calibration_window_seconds`, with phase-specific evaluation and
verification variants. Legacy stabilization keys SHALL remain readable. The exact
10-second default generated by 0.20.86a0 SHALL migrate to 60 seconds; other legacy
values and all canonical values SHALL remain explicit user choices.


### MLFF-PERF6 - mixed-stage admission and progress - implemented in 0.20.88a0

Evaluation and verification admission telemetry SHALL begin at the first
computation-heavy operation rather than waiting for the first model forward pass.
Checkpoint authentication/deserialization SHALL be the campaign evaluation
boundary; MACE model loading/device transfer SHALL be the bounded-NVE boundary.
Lightweight queue and thread launch SHALL remain excluded.

The default evaluation/verification calibration window SHALL be 20 seconds and
SHALL span all subsequent stages without reset. Training SHALL retain a separate
60-second true-epoch window. Concurrency-level changes, telemetry loss, or an
unsignaled replacement worker SHALL reset evaluation/verification calibration.

Evaluation and verification SHALL emit per-task stage transitions and periodic
active-stage summaries. Scheduling/progress changes SHALL remain runtime-only and
SHALL NOT alter scientific cache identities.
