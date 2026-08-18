# mdstats 0.20.212a0

REPLAY-UNIFY1C implements the additive foundation pseudo-label cache, qualification, and lazy materialization layer for the new single replay-source architecture.

- adds `ReplayFoundationPredictionPolicy` bound to exact foundation checkpoint/head and frozen inference/runtime identity;
- reuses the existing batched `MaceCalculatorProvider.predict_batch()` production surface with bounded OOM split-backoff;
- strips source truth/calculator results from inference geometry copies so pseudo labels cannot consume true labels;
- stores bounded ragged energy/force/stress prediction shards with source-order-independent logical identity;
- adds a compact authenticated scalar audit sidecar for force-RMS/max-force/max-stress qualification;
- makes threshold-only reclassification a zero-inference, audit-only operation;
- lazily materializes only requested pseudo-label train/monitor ExtXYZ views and authenticates their split/qualification/prediction lineage;
- reconstructs deleted transport views from cached predictions without reinference and returns authenticated view hits without source parsing;
- fails closed on audit-sidecar and prediction-shard tampering at their respective use boundaries;
- validates the complete 12,000-frame control plane as 10,000/2,000 with bounded memory using a deterministic non-MACE development provider;
- keeps live TRAIN2/DATA8 replay execution unchanged until REPLAY-UNIFY1D and defers real MACE/CUDA/CuEq qualification to regenerated FINAL-GPU1 after REPLAY-UNIFY1E.
