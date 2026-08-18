# mdstats 0.20.96a0 patch notes

## True-label replay restart lineage hotfix

0.20.95a0 correctly allowed a multi-head replay campaign trained against a foundation-pseudolabel replay monitor to evaluate against an independent `TRUE_DFT` replay monitor with identical authenticated geometry/order.  However, the nested `CheckpointMetricRecord.replay_monitor_artifact_digest` was populated with the evaluation-only true-label artifact digest.  Checkpoint admissibility intentionally compares that nested field with the replay monitor frozen into the DATA8 run plan.  A restart that tried to reconcile already-complete checkpoint evaluations could therefore raise `TrainingDataInputError: Replay monitor artifact lineage mismatch.` even though the evaluation itself was valid.

0.20.96a0 separates the two identities already represented by the evaluation record:

- `CheckpointEvaluationRecord.replay_monitor_artifact_digest` identifies the replay artifact whose labels were actually evaluated (the independent true-DFT override when configured).
- `CheckpointMetricRecord.replay_monitor_artifact_digest` identifies the frozen training replay lineage used by the run plan and checkpoint-admissibility policy.

The true-label override continues to be accepted only after configuration count, geometry identity, and order match the frozen training replay monitor.

## Restart migration

When 0.20.96a0 loads a reusable 0.20.95a0 evaluation row, it rebinds only the nested metric lineage digest to the run plan's training replay digest, preserves the outer true-label evaluation artifact identity and all numerical metrics, and writes the migrated record back to the campaign store.  No MACE inference is repeated.

This specifically repairs the state where all shortlisted checkpoint evaluations are complete but model selection/export was interrupted.  Rerunning `evaluate` can now authenticate the cached true-label evaluations, select the admissible checkpoint, and execute the 0.20.95a0 immediate parent-level `models/<run-id>-target.model` reconciliation path.

## Compatibility

No checkpoint-evaluation policy digest, acceptance threshold, run-plan identity, or model weights change.  Legacy pseudolabel-only records continue to behave as before.  The public replay-provenance binding helper retains its old two-argument call surface; the training lineage digest is an optional keyword used by campaign restart reconciliation.
