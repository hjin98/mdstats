# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

## Current MLFF implementation entrypoint

There is one current Protocol 6 implementation handoff:

- `workplans/active/MLFF_REPLAY_MACE_P5_EXECUTION_RECOVERY_CONSOLIDATED_WORKPLAN.md`

`workplans/active/CURRENT_IMPLEMENTATION_ENTRYPOINT.md` points to the same file. Earlier replay-membership, review-reopen, progress-recovery, and scheduler/architecture amendments remain provenance only.

### Current independent review state

Executable candidate `577908bf117d033357e2bfb1847e5ed16047d288` is **NO-PASS / REOPENED** after independent SSDP 6 Software Design review. No Serious Challenge is active; D1 scientific formulation, D2 numerical method, and accepted D3 replay/P5/TRAIN2/MACE plus serial selected-size architecture remain unchanged.

Source-level corrections to preserve:

- scheduler liveness comes from active futures rather than human-readable MACE phase;
- optimizer readiness uses current training phase plus bounded fresh optimizer activity under the existing activity-timeout policy;
- selected sizes remain serial;
- current single-source replay selects canonical loaded-geometry identity once and cannot enter legacy/file-reread fallback on mismatch;
- supported legacy replay remains explicitly routed through its historical identity domain;
- immediately-pre-fix continuation classification compares persisted actual TRAIN2 architecture with the current authorized training realization instead of interpreting a missing historical control using today's default.

Remaining blockers are narrow D4/evidence closure:

1. the append-only MACE metrics observer suppresses a newly appended `mode="opt"` row when its JSON content equals the preceding optimizer row; byte offset already owns exactly-once observation, so content deduplication must be removed and identical rows must count as distinct optimizer completions;
2. an exactly authenticated immediately-pre-fix run whose persisted architecture is noncurrent currently raises forever on retry; after classification it must use existing run-owned recovery mechanics to replace/recompute only that run, while ambiguous/corrupt/foreign state remains preserved;
3. acceptance must exercise the real per-size scheduler -> real `MacePostSelectionTrainer` -> owned subprocess boundary for promotion and cancellation/reaping, and separately prove the real TRAIN2 persistence owner produces the architecture digest consumed by recovery;
4. final focused/affected regression, integration, lint/type/static, and structural evidence must execute on one unchanged final candidate. GitHub exposes no check-runs/statuses for `577908bf...`.

The existing suite already contains a pinned real `mace.cli.run_train.run` parser/loader path that authenticates single-source replay after real loader construction; together with the candidate's explicit-domain no-reread negative test, no additional replay identity abstraction is required unless execution actually fails.

Do not add a scheduler, cross-size queue, progress daemon, update/replay/checkpoint registry, compatibility database, migration framework, restart state machine, or second wrapper. Keep the repair subtractive and D4-local.

Implementation/review coordination remains on:

- `fix/mlff-replay-mace-membership-identity`

Full production-scale GPU/CuEq/LAMMPS/MLIAP target-machine qualification remains deferred until the complete final release package. Bounded real MACE/CuEq functional boundary tests needed for concrete bug closure are implementation evidence, not production qualification.
