# Current MLFF implementation entrypoint

Implement the current repair from exactly one snapshot-complete workplan:

- `MLFF_REPLAY_MACE_P5_EXECUTION_RECOVERY_CONSOLIDATED_WORKPLAN.md`

That consolidated handoff supersedes earlier replay-membership/review/progress/scheduler amendments for implementation purposes. Those files remain provenance only.

Independent Protocol 6 review of executable candidate `dadb83e680032a30fe55b42baf77bf13538f94a7` accepts its optimizer-event accounting fix, scheduler liveness/readiness, explicit replay identity-domain routing, serial selected-size topology, actual-TRAIN2 architecture classifier, nominal bounded stale-run recomputation, real scheduler/trainer/process test boundary, and real TRAIN2 architecture-persistence test boundary. Preserve those changes.

The remaining D4 repair is narrow:

1. make the already-authenticated architecture-stale replacement transition interruption-idempotent. Current code removes the old materialization before the stale checkpoint continuation; interruption between those operations leaves durable continuation with no materialization and the next retry fails closed forever. Prefer retiring the proven-stale checkpoint continuation first, then rebuilding/removing materialization through the existing owner, or an equivalent existing-owner ordering with the same restart property;
2. add a bounded public-path failure-injection oracle at the inter-cleanup boundary proving that the next same-workspace invocation retrains only the affected run, leaves completed sibling evidence unchanged, and never destructively treats corrupt/foreign/unclassified state;
3. execute the complete focused/affected regression, real-owner integration, and configured static/structural checks on one unchanged final executable candidate.

Do not add a tombstone, persistent replacement flag, compatibility database, migration framework, stale-run registry, new run identity, permanent backup namespace, scheduler, cross-size queue, progress daemon, second wrapper, or new restart state machine for this repair.

No further Design round is required before implementation unless evidence shows that interruption-safe bounded replacement cannot be expressed using existing run ownership/classification/cleanup semantics. Full production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred to the final release package.
