# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

## Current MLFF implementation entrypoint

There is one current Protocol 6 implementation handoff:

- `workplans/active/MLFF_REPLAY_MACE_P5_EXECUTION_RECOVERY_CONSOLIDATED_WORKPLAN.md`

`workplans/active/CURRENT_IMPLEMENTATION_ENTRYPOINT.md` points to the same file. Earlier replay-membership, review-reopen, progress-recovery, and scheduler/architecture workplans/amendments remain provenance only and are not separate implementation stages.

### Current review state

Executable candidate `a4d722d6de6dda59f7f1a20eb9b583e4a756f12a` remains **NO-PASS / REOPENED**. The consolidated workplan itself has been re-reviewed and reconciled against current Scientific Software Development Protocol 6.0.0 and current mdstats architecture/specification authority. No Serious Challenge is active; D1 scientific formulation, D2 numerical method, and accepted D3 replay/P5/TRAIN2/MACE architecture remain unchanged.

A prior workplan requirement has been retracted: **do not schedule across selected sizes**. Current accepted D3 keeps the selected-size dimension serial outside fold/seed/MACE execution. The existing adaptive scheduler is to operate correctly within each selected size's independent CV folds/seeds or production members. Cross-validation still records every frozen size's verdict before campaign reduction; final production still performs the collection-wide accepted-CV preflight before any new production work, then retains per-size publication/currentness semantics.

Accepted implementation direction to preserve includes canonical single-source replay geometry identity without target `frame_uid`, process-local transport of authenticated replay split membership, incremental MACE metrics probing, supervised `Popen` child ownership, explicit current `compute_avg_num_neighbors=False`, and TRAIN2/EVAL2 transient-accelerator versus portable-model reconstruction with the fail-closed architecture guard retained.

Remaining blocking D4 repairs are:

1. scheduler task liveness is conflated with the human-readable MACE `phase`, so a training heartbeat can remove a live task from admission accounting;
2. scheduler readiness is the sticky `completed_epochs > 0` flag; it must instead use current training phase plus bounded fresh optimizer activity under the existing `parallel_training_epoch_activity_timeout_seconds` control, so first-epoch work is visible, validation cannot authorize promotion, and one slow legitimate step does not lose readiness merely because a telemetry poll saw no new record;
3. canonical single-source replay still has a cascading canonical -> historical -> file-reread membership fallback; the identity domain must be selected once from existing authenticated interface authority, with source-to-real-MACE-loaded canonical identity equivalence proven and mismatch failing closed;
4. the immediately-pre-fix completed stakeholder run must be classified from its persisted actual TRAIN2 architecture against the current authorized training realization before current-config spelling can cause rejection/deletion; absence of the historical `compute_avg_num_neighbors` control must never be silently normalized into today's value as proof of equivalence;
5. final real-owner reporter, failure-propagation, architecture-parity, affected regression, integration, and static evidence must execute on the unchanged final candidate.

The repair strategy is subtractive: derive liveness from the existing active-future relation, reuse the existing metrics probe and activity-timeout policy for scheduler readiness, preserve serial outer size orchestration, replace replay fallback selection with one explicit existing identity domain, and compare old state through existing TRAIN2/MACE architecture authority. Do not add a scheduler, cross-size queue, progress daemon, compatibility database, replay/checkpoint registry, wrapper, migration system, or restart state machine.

Implementation/review coordination remains on:

- `fix/mlff-replay-mace-membership-identity`

Full production-scale GPU/CuEq/LAMMPS/MLIAP target-machine qualification remains deferred until the complete final release package. A tiny bounded real CuEq functional reproduction remains required where needed to close the concrete checkpoint-realization defect and is not a release-performance qualification claim.
