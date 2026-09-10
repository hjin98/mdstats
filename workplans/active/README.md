# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

## Current MLFF implementation entrypoint

There is one current Protocol 6 implementation handoff:

- `workplans/active/MLFF_REPLAY_MACE_P5_EXECUTION_RECOVERY_CONSOLIDATED_WORKPLAN.md`

`workplans/active/CURRENT_IMPLEMENTATION_ENTRYPOINT.md` points to the same file. Earlier replay-membership, review-reopen, progress-recovery, and scheduler/architecture workplans/amendments are retained as provenance only and are not separate implementation stages.

### Current review state

Independent Software Design review of executable candidate
`a4d722d6de6dda59f7f1a20eb9b583e4a756f12a` is **NO-PASS / REOPENED** under Scientific Software Development Protocol 6.0.0. No Serious Challenge is active; D1 scientific formulation, D2 numerical method, and accepted D3 replay/P5/TRAIN2/MACE architecture remain unchanged.

Accepted implementation direction to preserve includes: canonical single-source replay geometry identity without target `frame_uid`; process-local transport of authenticated replay split membership; incremental MACE metrics probing; supervised `Popen` child ownership and bounded progress reporting; explicit current `compute_avg_num_neighbors=False`; and TRAIN2/EVAL2 transient-accelerator versus portable-model reconstruction with the fail-closed architecture guard retained.

Blocking D4 repairs are consolidated in the current workplan:

1. scheduler task lifecycle and MACE/reporting `phase` are conflated, so the first child observation removes the job from the scheduler's `phase == running` true-epoch count and prevents adaptive promotion;
2. scheduler readiness is a sticky `completed_epochs > 0` flag rather than fresh current optimizer activity, so first-epoch compute is missed and validation idleness can be misclassified as steady training;
3. the scheduler is recreated separately for each selected size while the public CV and production loops remain serial over sizes, contrary to the command-wide pending `(N, seed, fold/member)` admission contract;
4. the single-source child membership path still tries canonical identity, historical identity, then a full replay-file metadata reread, allowing the prohibited redundant parse to reappear instead of failing closed on a broken canonical loaded-geometry relation;
5. the stakeholder's pre-fix completed workspace cannot yet be classified under the newly explicit `compute_avg_num_neighbors=False` realization because recovery treats the old config as foreign before determining whether the actual trained architecture merely differs in representation or genuinely used a different model normalization;
6. final real-owner regression/integration/static evidence has not been recorded for the exact candidate; GitHub has no check-run/status evidence for `a4d722d6...`.

The repair strategy is subtractive: derive active tasks from the existing future->task relation, derive admission readiness from fresh metrics progress, lift one existing `AdaptiveTrainingConcurrency` session to the public multi-size command owner, replace replay fallback selection with one explicit existing identity domain, and classify the old run through its actual authenticated architecture before any deletion/retraining. Do not add a new scheduler, queue, progress daemon, compatibility database, replay/checkpoint registry, wrapper, or restart state machine.

Implementation/review coordination remains on:

- `fix/mlff-replay-mace-membership-identity`

Full production-scale GPU/CuEq/LAMMPS/MLIAP target-machine qualification remains deferred to the final release package. A tiny bounded real CuEq functional test remains required where needed to close the concrete checkpoint-realization defect and is not a release-performance qualification claim.
