# mdstats 0.20.113a0 patch notes

- Implement MLFF STOR2 authenticated completed-checkpoint compaction: after per-run checkpoint selection, retain the selected full restart-capable checkpoint and replace qualified nonselected optimizer-bearing checkpoints with smaller model-state-only evaluation capsules.
- Bind every capsule to the original checkpoint SHA-256, run/epoch lineage, immutable MACE config digest, reconstruction contract, model-state digest, and capsule byte identity; raw deletion occurs only after atomic capsule write, independent exact reconstruction, campaign-state commit/readback, and re-authentication.
- Make OPT-EVAL1/OPT-EVAL4 and true-label replay refresh representation-aware so later re-evaluation can transparently use capsules while preserving the original checkpoint scientific/cache identity.
- Preserve active/incomplete-run restart state and pre-selection raw checkpoints; unsupported layouts, corruption, ownership ambiguity, non-saving capsules, or reconstruction mismatch fail closed to raw retention.
- Qualify STOR2 on real MACE 0.3.16/e3nn with exact model-state and energy/force/stress equivalence. STOR3 is the next architecture gate.

