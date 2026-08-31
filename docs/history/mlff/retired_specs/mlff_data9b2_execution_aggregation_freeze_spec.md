# MLFF-DATA9B2 specification: execution, evaluation, aggregation, committee, and freeze

Version: 0.20.57a0

## Purpose

DATA9B2 closes the production-training control loop after DATA9B1. It does not
make a model scientifically acceptable by itself. It makes every training run,
checkpoint evaluation, protocol comparison, committee member, and protocol
freeze an immutable, lineage-checked record.

## Inputs

DATA9B2 consumes only:

- a passed `ProductionCorpusQualificationRecord`;
- a frozen `TrainingCampaignPlan` and exact `TrainingCampaignRunPlan` objects;
- exact DATA8 `MaceJobArtifact` files;
- the precision-aware `mdstats-mace-train`, `mdstats-mace-eval`, and
  `mdstats-mace-select-head` wrappers;
- checkpoint catalogs and monitor artifacts whose digests match the campaign;
- the frozen `CheckpointMetricPolicy` and replay-retention identity.

## Supervised execution

`TrainingExecutionPolicy` freezes the wrapper name, retry limit, timeout,
restart behavior, checkpoint glob, and environment evidence allowlist. Each attempt is a `TrainingRunAttemptRecord`; the complete supervised result is a `TrainingRunExecutionRecord`.

`execute_training_run` shall:

1. verify the DATA8 config bytes against the job artifact;
2. launch only the declared mdstats wrapper;
3. record exact argv, working directory, environment digest, timestamps,
   elapsed time, return code, stdout, and stderr for every attempt;
4. persist a fail-closed execution record after every failed or timed-out attempt,
   so an interrupted supervisor can resume from immutable attempt evidence;
5. terminate the complete POSIX process group on timeout, first with `SIGTERM`
   and then with `SIGKILL` after the frozen grace period when necessary;
6. add `--restart_latest` only on policy-authorized retries;
7. inventory successful checkpoint bytes by SHA-256;
8. reject a successful process that produced no candidate checkpoint when the
   policy requires checkpoints;
9. reverify all checkpoint bytes before reusing a completed execution record.

A failed or timed-out process is evidence, not an exception that can be silently
ignored.

## Automatic checkpoint evaluation

`CheckpointEvaluationPolicy` freezes the inputs used to create a `CheckpointEvaluationRecord`:

- target and replay head names;
- reference energy, force, and stress keys;
- focus atomic numbers;
- condition-group keys;
- replay metric and baseline floor;
- combined-metric weights;
- device and dtype.

`evaluate_mace_checkpoint` shall evaluate the exact checkpoint bytes with the
critical-FP64 patch installed. It materializes:

- energy MAE per atom;
- force-component RMSE;
- focus-species force RMSE;
- stress RMSE when labels exist;
- worst declared-condition force RMSE;
- target combined loss;
- replay baseline and candidate metrics;
- replay degradation fraction;
- monitor, model, and policy hashes.

For pseudo-label replay, the baseline floor prevents division by a numerically
zero foundation-model error from producing an undefined ratio. Absolute
baseline and candidate metrics remain serialized.

## Fold and seed aggregation

`ProtocolVariantAggregate` groups one seed's protocol-matched final run and all
cross-validation folds. It records fold values, mean, standard deviation, and
worst fold.

`ProtocolFamilyAggregate` combines seed variants only when training mode,
selection size, protocol family, campaign, and primary metric all match.

`LearningCurveRecord` orders comparable protocol families by selection size.
It never assumes monotonic improvement.

`ProtocolComparisonRecord` ranks complete family aggregates by the frozen mean
cross-validated primary metric, then worst-seed metric, then content digest.
Naive and replay campaigns are different protocol families.

## Committee export

`CommitteeExportPolicy` requires the precision-aware
`mdstats-mace-select-head` wrapper and freezes the target head and export device.

Each `CommitteeMemberRecord` binds:

- final run and seed;
- checkpoint-selection record;
- source checkpoint SHA-256;
- extracted target-head SHA-256 and size.

`CommitteeIdentity` requires exact campaign seed coverage and distinct exported
model bytes. Cross-validation checkpoints cannot become committee members.

## Protocol freeze

`ProtocolFreezeRecord` owns only frozen identities:

- passed production qualification;
- campaign plan;
- source, frame, and DATA5 lineages;
- selected protocol comparison and family aggregate;
- committee identity and member model hashes;
- exact final checkpoint-selection records.

It shall not contain locked-test results.

`EvaluationActivationDecision` may activate sealed evaluation only when the
freeze, committee, frame catalog, DATA5 bundle, and activation requirement all
match. Otherwise it records explicit rejection reasons.

## Fail-closed requirements

DATA9B2 shall reject:

- raw `mace_run_train` or unqualified head-selection wrappers;
- changed DATA8 config bytes;
- missing checkpoint output after successful training;
- checkpoint/model hash mismatch;
- missing target or replay monitor evidence;
- incomplete fold/final or seed coverage;
- mixed protocol identities in an aggregate;
- committee members from fold jobs;
- duplicate committee seeds or exported model bytes;
- protocol freeze before full DATA9A passage;
- locked evaluation whose frame or DATA5 lineage differs from the freeze.

## Scope boundary

This stage implements the production execution and freeze machinery and tests it
with bounded external processes plus the supplied real MACE multi-head smoke
model. It does not claim that the 2,734-frame production DATA6-DATA8 realization
or a long multi-seed production campaign has been executed. Scientific
acceptance, calibration, long MD validation, and active learning remain DATA10
and DATA11 responsibilities.
