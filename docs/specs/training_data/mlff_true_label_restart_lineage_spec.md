# MLFF true-label replay restart lineage specification

## Invariant

A multi-head replay run has two replay identities when independent true labels are supplied:

1. **training replay lineage** — the immutable DATA8 replay monitor referenced by `TrainingCampaignRunPlan.replay_monitor_artifact_digest`; this may contain foundation pseudolabels and defines the replay geometry/order used during training;
2. **evaluation replay artifact** — the independent `TRUE_DFT` artifact carrying labels used for evaluation, accepted only when configuration count and ordered geometry identities match the training replay monitor.

The two digests are expected to differ because label provenance and file bytes differ.

## Record semantics

`CheckpointEvaluationRecord.replay_monitor_artifact_digest` records the evaluation replay artifact actually used for candidate/foundation metrics.

`CheckpointMetricRecord.replay_monitor_artifact_digest` records the frozen training replay lineage against which `assess_checkpoint_admissibility()` authenticates the run.

This separation allows true-label evaluation without weakening run-plan provenance.

## Migration

A cached 0.20.95a0 evaluation may have the evaluation replay digest in both fields.  During cache reuse, `bind_checkpoint_evaluation_replay_provenance(..., training_replay_monitor_artifact_digest=<run digest>)` migrates the nested metric digest in memory and the campaign CLI immediately rewrites the durable evaluation row when its content digest changes.

The migration must not rerun inference, alter numerical metrics, change the enclosing evaluation replay artifact digest, or bypass the true-label geometry/order check.
