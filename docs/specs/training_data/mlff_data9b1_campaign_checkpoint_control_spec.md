# MLFF-DATA9B1 specification: campaign and checkpoint control

Version: 0.20.56a0

## Purpose

DATA9B1 is the first executable control layer after the DATA9A production gate.
It does not train a model by itself. It freezes the exact protocol-matched job
matrix, inventories every saved MACE checkpoint, evaluates candidate metrics
against the already frozen `CheckpointMetricPolicy`, and selects a checkpoint
only from candidates that satisfy every mandatory constraint.

The stage exists so that later large MACE runs cannot silently change seeds,
fold coverage, training mode, selection size, checkpoint files, or selection
rules after results are visible.

## Inputs

DATA9B1 consumes only immutable records and files:

- a `ProductionCorpusQualificationRecord` whose status is `passed`;
- exact DATA8 `MaceJobArtifact` records;
- a `TrainingCampaignPolicy` declaring required seeds, training modes,
  selection sizes, cross-validation coverage, and final-development coverage;
- saved MACE checkpoint files;
- target/replay evaluation metrics computed on the declared monitor artifacts.

Locked-test labels are forbidden inputs.

## Record families

### `TrainingCampaignPolicy`

Declares the required experiment matrix:

- required seeds;
- required training modes (`naive_fine_tuning` and/or `multihead_replay`);
- a naïve DATA8 variant MUST bind `ReplayMode.NONE`; a replay-backed plan MUST
  materialize as `multihead_replay`, and the persisted variant label MUST match
  the mode, selection size, and optimizer seed frozen in every job;
- required selection sizes;
- whether one final-development job is required per variant;
- whether all declared cross-validation folds are required;
- whether all evaluation checkpoints must be retained;
- required execution wrapper (`mdstats-mace-train`).

### `TrainingCampaignRunPlan`

Binds one exact DATA8 job to:

- its job and protocol digests;
- fold or final-development role;
- training mode;
- selection size;
- seed;
- protocol-family and protocol-variant identities;
- output directory and required execution wrapper.

A protocol family excludes fold-local data identities and the scalar seed. A
protocol variant adds the scalar seed. Every variant must contain the complete
fold set and exactly one final-development job when required.

### `TrainingCampaignPlan`

Binds the complete job matrix to the passed DATA9A gate and validates:

1. unique DATA8 job identities;
2. required mode/selection-size/seed Cartesian coverage;
3. exact fold indices `0..N-1` for every protocol variant;
4. one final-development job per variant;
5. save-all checkpoint control and external checkpoint audit;
6. use of the mdstats precision-aware MACE training wrapper.

### `CheckpointFileRecord` and `CandidateCheckpointCatalog`

Every checkpoint is content-addressed by SHA-256 and records its byte size,
epoch, relative path, run-plan lineage, and candidate ID. The inventory rejects
missing files, duplicate epochs, duplicate paths, duplicate file digests, and
checkpoint files outside the declared output root.

### `CheckpointMetricRecord`

Stores externally evaluated target and replay metrics for one exact checkpoint:

- target energy MAE per atom;
- target force-component RMSE;
- optional focus-group force RMSE values;
- optional stress RMSE;
- optional worst-condition force RMSE;
- optional target combined loss;
- optional replay baseline, candidate metric, and degradation fraction;
- exact target and replay monitor artifact digests.

All supplied metrics must be finite and nonnegative.

### `CheckpointAdmissibilityDecision`

Applies `CheckpointMetricPolicy` without discretion. A candidate is rejected
when a required metric is absent, any hard threshold is exceeded, replay
retention is missing for a replay protocol, or metric/checkpoint lineage does
not match.

### `CheckpointSelectionRecord`

Selects the admissible candidate with the minimum frozen primary metric.
Tie-breaking is deterministic:

1. lower replay degradation when available;
2. lower epoch;
3. lexical checkpoint SHA-256.

If no checkpoint is admissible, selection fails closed.

## Prohibited behavior

DATA9B1 shall reject:

- a campaign built from a blocked or conditionally-ready DATA9A record;
- incomplete cross-validation or seed coverage;
- a raw `mace_run_train` execution wrapper;
- candidate checkpoints not bound to the campaign plan;
- monitor metrics with missing or mismatched artifact identities;
- use of locked-test results in checkpoint choice;
- manual selection of a rejected checkpoint;
- selection before every cataloged candidate has an admissibility decision.

## Focused tests

The stage must include tests for:

- serialization round trips and digest tamper detection;
- passed-gate enforcement;
- Cartesian mode/size/seed and fold/final coverage;
- protocol-family matching across fold-local DATA8 jobs;
- checkpoint file inventory and path-containment checks;
- every checkpoint threshold and missing-metric failure;
- deterministic primary-metric selection and tie-breaking;
- fail-closed behavior when all candidates are rejected;
- actual inventory of the supplied MACE one-epoch checkpoint;
- compatibility with the supplied 27-file LTA training corpus and offline
  dependency archive at the file-discovery level.

## Deferred to DATA9B2 and later

DATA9B1 does not yet:

- launch or supervise long-running MACE processes;
- parse MACE evaluation output into metric records automatically;
- aggregate folds and seeds into learning curves;
- compare full naive and replay campaigns statistically;
- construct the final committee;
- emit `ProtocolFreezeRecord`;
- activate the locked test.

## Planned multi-fidelity successor

The current DATA9B1 selection contract remains authoritative: final admissibility and
selection consume complete monitor-bound checkpoint metrics. The planned EVAL-MF1/MF2
roadmap changes how candidate evaluation budget is allocated before those final records
exist; it does not weaken DATA9B1's final metric/admissibility requirements.
Partial-round metrics will be explicitly typed as screening evidence and shall not be
serialized as ordinary full-fidelity `CheckpointMetricRecord` objects. See
`mlff_eval_mf_successive_halving_spec.md`.
