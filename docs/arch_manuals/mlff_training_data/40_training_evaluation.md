# Part IV - Training and evaluation

## Multi-head replay and training-protocol contract

### Concept

Multi-head replay fine-tuning trains a shared MACE backbone on target data and a
foundation replay dataset with separate output heads. The replay objective helps
limit catastrophic forgetting while the target head adapts [11, 12].

### `TrainingProtocolIdentity`

Every cross-validation family and final run is bound to one complete protocol:

```text
foundation checkpoint and head
naive or multi-head mode
replay source, selection, and monitor
training objective and property weights
target/replay head weights
exposure backend and realized-balancing policy
checkpoint metric
MaceCheckpointControlPolicy
replay-retention policy
optimizer, scheduler, epoch cap, and seed policy
MACE adapter lock
```

Cross-validation results apply only to this identity. Hyperparameters selected
under naive fine-tuning are not automatically valid for replay fine-tuning.

### Separate lineages

Target and replay data retain separate:

```text
source catalog
label domain
atomic-reference policy
selection plan
training weights
exposure accounting
validation or sentinel monitoring
```

### Replay source modes

```text
MP_SHORTCUT
EXTERNAL_TRUE_LABEL
EXTERNAL_PSEUDOLABEL
PRESELECTED
```

The mdstats core records a `ReplayPreparationPlan`; it does not download replay
data. The optional MACE adapter may execute or print the official MACE selection
command.

### Replay-retention monitor and constraint

A training-only replay file is insufficient. The bundle also contains a
disjoint `replay_monitor.xyz` or named `foundation_retention_suite`.

For true-label replay, it measures held-out DFT errors. For pseudo-label replay,
it measures drift from the original foundation model on unseen sentinel
configurations.

A `ReplayRetentionPolicy` defines:

```text
retention metric
foundation or pre-fine-tuning baseline
tolerated degradation delta
aggregation across energy/force/stress
failure or override behavior
```

### Checkpoint metric and constrained choice

A `CheckpointMetricPolicy` defines the target checkpoint objective and all
constraints. It must include:

```text
primary target scalar
energy/force/stress normalization
Li/Na/K species metrics
worst-condition metrics
rare-event metrics
replay-retention constraint
missing-label behavior
```

A typical rule is

$$
\min_c L_{\mathrm{target\ monitor}}(c)
$$

subject to

$$
L_{F,\mathrm{Li/Na/K}}(c) \le \boldsymbol\delta_F,
\qquad
\Delta L_{\mathrm{replay\ monitor}}(c) \le \delta_{\mathrm{replay}}.
$$

The exact metrics and thresholds are project policy and are serialized.

### MACE checkpoint-control policy

MACE 0.3.16 evaluates all validation heads but uses the **last** validation head
for learning-rate scheduling, patience, and native best-checkpoint decisions
[17]. Its multi-head assembly places `pt_head` before target heads in the
versioned source [18], but this ordering is an implementation detail that must
be tested rather than assumed.

The initial adapter supports:

```text
NATIVE_TARGET_LAST_WITH_EXTERNAL_CONSTRAINT_AUDIT
```

It must:

1. verify by source lock and smoke test that the target checkpoint monitor is the
   last validation head controlling native scheduling;
2. use a fixed epoch cap and configure patience so the run is not terminated by
   replay-head behavior;
3. enable retention of every evaluation checkpoint;
4. evaluate each candidate checkpoint externally on the target checkpoint
   monitor and replay monitor;
5. apply `CheckpointMetricPolicy` deterministically;
6. fail closed if the tested head-order or checkpoint behavior changes.

Later modes may provide full external scheduler control or a custom training
loop. A post-training audit alone is insufficient if native early stopping was
allowed to terminate on the wrong head.

### Exposure diagnostic

A coarse intended ratio is

$$
R_{\mathrm{exposure}}=
\frac{N_{\mathrm{replay}}w_{\mathrm{pt}}}
{N_{\mathrm{target}}w_{\mathrm{target}}}.
$$

The realized record additionally counts implicit duplication, batches, and
energy/force/stress exposures. Intended counts never substitute for observed
loader behavior.

## MACE adapter and output contract

### Version lock and compatibility matrix

The initial adapter targets `mace-torch==0.3.16`, the current PyPI release at
this architecture revision [9]. Every supported version records:

```text
mace version
package wheel/source SHA-256
Git commit or tag
mace_run_train --help
fine_tuning_select --help
key parser, loader, and train-loop source digests
validated head order
validated checkpoint-control behavior
validated replay-ratio behavior
```

Documentation URLs alone are not treated as a stable API contract.

### Minimal XYZ plus complete sidecar manifest

Extended XYZ contains only MACE-readable labels, weights, and compact stable
identities. Long provenance and reason lists live in a sidecar frame manifest
keyed by `frame_uid`. DATA8 writes Cartesian positions and per-atom floating
labels with 17 significant decimal digits rather than ASE 3.29's eight-decimal
default, then certifies the artifact through a streamed ASE read-back.

Minimum target-frame XYZ fields are:

```text
REF_energy
REF_forces
REF_stress
frame_uid
config_type
config_weight
config_energy_weight
config_forces_weight
config_stress_weight
```

The sidecar stores geometry/label fingerprints, source lineage, composition,
temperature, ensemble, strain, regime, selection reasons, policy digests, and
all audit evidence.

### Separated development, calibration, and evaluation artifacts

```text
mace_artifacts/
  development_bundle/
    target_train.xyz
    target_valid.xyz
    replay_train.xyz
    replay_monitor.xyz
    mace_config.yaml
    frame_manifest.json
    target_label_domain.json
    structural_atomic_reference_report.json
    atomic_reference_fit.json
    feature_metric_fit.json
    training_objective_policy.json
    checkpoint_metric_policy.json
    training_protocol_identity.json
    mace_checkpoint_control_policy.json
    replay_plan.json
    replay_retention_policy.json
    selection_manifest.json
    exposure_backend_policy.json
    adapter_lock.json
    cross_validation/
      fold_00/
        train.xyz
        checkpoint_monitor.xyz
        replay_train.xyz
        replay_monitor.xyz
        mace_config.yaml
        transform.json
        feature_metric_fit.json
        selection.json
        atomic_reference_fit.json
        training_protocol_identity.json
      fold_01/
        ...

  calibration_bundle/
    calibration.xyz
    committee_identity.json
    calibration_policy.json

  sealed_evaluation_bundle/
    target_test.xyz
    challenge_tests/
    evaluation_commands.yaml
    bundle_digest.json

  evaluation_activation/
    protocol_freeze_record.json
    selected_committee_identity.json
    activation_decision.json

  evaluation_results/
    evaluation_result_catalog.json
```

Replay files are omitted when replay is disabled. A sealed evaluation bundle may
be prepared early, but it is not opened or referenced by training. Activation
requires a `ProtocolFreezeRecord`, complete `TrainingProtocolIdentity`, selected
committee digests, and checkpoint-selection decision.

### Explicit E0 serialization

`AtomicReferenceFitRecord` is converted to the exact MACE input accepted by the
version lock, normally an explicit atomic-number mapping:

```yaml
E0s:
  3:  -1.234
  8:  -2.345
  11: -3.456
  13: -4.567
  14: -5.678
  19: -6.789
```

The fit-record path and digest belong in provenance. A conceptual fit-record placeholder is never emitted as the MACE `E0s` value.

### One target label domain per bundle

The development configuration contains one target head and an optional replay
head. It contains no locked test path. Its exact schema is generated by the
locked adapter and must preserve target-last validation control under the
accepted checkpoint policy.

### Export and loader round trip

The gate verifies:

1. ASE write/read equality;
2. atom order;
3. cell and PBC;
4. selected energy;
5. forces;
6. stress convention;
7. weights;
8. head labels and validation order;
9. explicit E0 mapping;
10. MACE parser recognition;
11. effective target/replay counts after loader assembly;
12. LAMMPS element mapping at later deployment.

## Protocol-matched cross-validation and final training workflow

The recommended initial workflow is:

1. Build one immutable outer partition, feasibility report, and independence
   report.
2. Define candidate `TrainingProtocolIdentity` objects, including naive/replay
   mode, replay preparation, objective, exposure backend, and checkpoint policy.
3. For each protocol, create $K$ independent jobs. Each has a fold-training
   domain, nested checkpoint monitor, held-out evaluation fold, and the same
   protocol-matched replay lineage.
4. Fit fold-local transforms, metric, selection, and atomic references using
   only each fold-training domain.
5. Train one fresh model per fold under the version-tested MACE checkpoint
   control. Freeze the externally audited checkpoint without inspecting the
   held-out evaluation fold.
6. Evaluate the frozen checkpoint on the held-out fold and collect out-of-fold
   predictions and independence grades.
7. Compare complete protocols using aggregate out-of-fold metrics and the fixed
   outer monitor. A naive protocol and a replay protocol are compared as
   different identities.
8. Freeze the selected data, objective, replay, exposure, stopping, checkpoint,
   and seed policies.
9. Fit final transforms, selection, and atomic references on the final target
   training domain.
10. Train independent final seeds under the same frozen protocol and record
    actual MACE exposure realization.
11. Apply constrained checkpoint selection and create the final committee.
12. Run that committee on the dedicated calibration cohort, record its
    applicability domain, and calibrate numerical uncertainty thresholds.
13. Create a `ProtocolFreezeRecord`; activate the sealed evaluation bundle and
    evaluate locked tests once.
14. Use the calibrated committee for active learning within its applicability
    domain; use rank-only acquisition outside it until recalibration.

If a final-refit mode consumes the outer monitor, its protocol must use a
predeclared epoch/checkpoint rule and only locked external tests remain
independent evidence.

## Active-learning architecture

### Immutable loop

```text
trained independent-seed committee
  -> exploratory ASE/LAMMPS trajectories
  -> candidate occurrence catalog
  -> candidate admissibility
  -> physical events + descriptors + disagreement
  -> calibrated acquisition and burst deduplication
  -> DFT query manifest
  -> labeled source ingestion
  -> labeled-frame eligibility
  -> append-only child dataset version
  -> retraining
```

### Acquisition evidence

A candidate may be selected using a Pareto or quota policy over:

- committee force disagreement;
- energy or stress disagreement;
- nearest-training descriptor distance;
- rare-event or physical-risk state;
- condition coverage gap;
- redundancy penalty.

A single weighted sum may be reported, but individual components remain
available.

### Calibration, committee binding, and applicability

Committee disagreement is a ranking signal, not an error guarantee [13, 14].
The architecture distinguishes:

```text
OutOfFoldUncertaintyDiagnostic
    Tests whether uncertainty ranks error during development.

FinalCommitteeCalibration
    Sets numerical thresholds using predictions from the actual final
    committee on a dedicated calibration cohort.
```

A calibration record is bound to:

```text
committee model digests
architecture and number of members
target-training lineage
replay lineage and retention policy
seed policy
MACE version and adapter lock
precision and inference settings
calibration-cohort identity
```

`CalibrationApplicabilityDomain` additionally records:

```text
elements and compositions
temperature and strain range
cell-size range
site and event classes
descriptor-distance range
force/stress range
framework-integrity state
```

A `CalibrationTransferDecision` classifies each candidate domain as:

```text
within_calibrated_domain
rank_only_outside_domain
recalibration_required
rejected_incompatible_domain
```

Out-of-fold predictions alone do not define the numerical scale for a committee
trained on full development data. If no valid final-committee calibration
cohort exists, the workflow emits only an explicitly **uncalibrated rank-only**
acquisition plan.

Report:

- Spearman uncertainty-error correlation;
- high-error recall in top uncertainty quantiles;
- false-negative rate;
- per-species and per-condition calibration;
- applicability-domain coverage;
- calibration transfer warnings when committee identity or candidate domain
  changes.

Locked tests are excluded.

### Burst deduplication

Adjacent uncertain frames from one event are clustered by trajectory, time,
geometry fingerprint, descriptor distance, and event identity. A compact
representative stencil is selected.

### Append-only role inheritance

A child dataset inherits all existing frame roles unchanged by default:

```text
existing development/validation/calibration/test roles
    -> inherited unchanged

selection-biased active-learning labels
    -> new development/training candidate pool

independent random labels from a newly entered domain
    -> possible new calibration or validation cohort

predeclared physical challenge calculations
    -> new named locked challenge set
```

A complete repartition is permitted only as a new evaluation lineage with a new
partition identity. Its metrics must not be presented as directly comparable to
the old locked-test lineage without qualification.

## Determinism and reproducibility

Every build records:

- source digests and source identities;
- parser and mdstats versions;
- policies and policy digests;
- reference-cell identities and cell-matrix convention;
- feature-provider versions;
- foundation checkpoint digest;
- MACE adapter lock and compatibility-test evidence;
- random seeds and floating-point dtype;
- `FeatureMetricPolicyTemplate` plus fold/final fitted metrics;
- fold checkpoint-monitor policy;
- fold and final `AtomicReferenceFitRecord` objects;
- `PartitionRoleBudgetPolicy`, feasibility, and independence reports;
- `SelectionBudgetPolicy` and realized evidence-class budgets;
- `TrainingObjectivePolicy`, configuration/property weights, and
  `CheckpointMetricPolicy`;
- complete `TrainingProtocolIdentity`;
- MACE checkpoint-control and exposure-backend policies;
- `MaceExposureRealizationRecord`;
- replay-retention and checkpoint-selection decisions;
- protocol-freeze and evaluation-activation records;
- calibration applicability and transfer decisions;
- active-learning role-inheritance policy;
- tie-breaking rules, fold assignments, selection master order, and output
  checksums.

## Performance and storage

The first implementation processes one trajectory at a time. It stores compact
metadata and feature arrays, releases full trajectories, and uses one of two
explicit export policies:

```text
SEQUENTIAL_REPARSE
    Reparse each source sequentially and emit selected frames.

SELECTED_FRAME_CACHE
    Cache selected atomic arrays during the first pass after the selection is
    known through a second controlled source pass.
```

The architecture does not promise XML random access. A later indexed or
streaming VASP reader may replace the second sequential parse without changing
scientific contracts.

## Failure semantics

The workflow fails closed when:

- source or label identity is unresolved;
- required labels are absent or nonfinite;
- incompatible label domains are mixed;
- strain requires an ambiguous reference cell or the cell convention is unclear;
- requested partition roles are statistically infeasible under the declared
  independence policy;
- locked or monitor labels reach a fitted transform, E0 fit, selector, difficulty
  feature, calibration, or acquisition operation;
- `E0s: estimated` is requested without an accepted training-domain
  atomic-reference fit or exact adapter serialization;
- a cross-validation held-out fold controls checkpoint selection;
- a cross-validation family is not bound to the same complete training protocol
  used for final training;
- the tested MACE validation-head order or native checkpoint behavior changes;
- native MACE silently changes target/replay exposure without an accepted
  realization record;
- a locked-test path appears in a development MACE configuration;
- no checkpoint satisfies mandatory target, focus-group, or replay-retention
  constraints;
- replay checkpoint and replay source are incompatible;
- dynamic epoch resampling is requested through a fixed-file-only adapter;
- calibrated candidate acquisition is attempted outside the calibration
  applicability domain without rank-only fallback or recalibration;
- active-learning child generation reassigns existing roles without a new
  evaluation lineage.

The workflow reports, rather than fabricates, absent profile-declared transition events,
independent replicas, strain-composition combinations, calibration cohorts, or
challenge sets.
