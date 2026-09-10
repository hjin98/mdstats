# Current MLFF implementation entrypoint

Implement the current repair from exactly one snapshot-complete workplan:

- `MLFF_REPLAY_MACE_P5_EXECUTION_RECOVERY_CONSOLIDATED_WORKPLAN.md`

That consolidated handoff supersedes earlier replay-membership/review/progress/scheduler amendments for implementation purposes. Those files remain provenance only.

Independent Protocol 6 review of executable candidate `577908bf117d033357e2bfb1847e5ed16047d288` accepts and freezes the candidate's scheduler-liveness, bounded optimizer-readiness, explicit current replay-identity-domain routing, serial selected-size topology, and persisted-architecture comparison direction. Preserve those changes.

The remaining D4 work is narrow:

1. remove content-based deduplication from the append-only MACE optimizer metrics observer so every newly consumed complete `mode="opt"` line counts exactly once;
2. after exact classification of an immediately-pre-fix architecture-stale run, use existing run-owned recovery mechanics to replace/recompute only that run instead of raising forever on every retry;
3. add bounded proxy-proof integration through the real per-size scheduler and real `MacePostSelectionTrainer` down to an owned tiny wrapper subprocess, and prove real TRAIN2 persistence supplies the architecture digest consumed by recovery;
4. execute the final affected regression/integration/static evidence set on one unchanged candidate.

The existing pinned real MACE parser/loader test remains the owner-level replay representation oracle; do not create another loader or replay identity mechanism unless that test actually fails.

Do not add a new scheduler, cross-size queue, progress daemon, compatibility database, replay/checkpoint/update registry, wrapper layer, migration framework, restart state machine, or durable progress authority. Selected sizes remain serial at the accepted outer D3 boundary.

No further Design round is required before implementation unless a genuine escalation trigger in the consolidated workplan fires. Full production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred to the final release package.
