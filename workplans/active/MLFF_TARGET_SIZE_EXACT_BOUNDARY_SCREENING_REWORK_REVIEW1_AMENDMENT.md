---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-EXACT-BOUNDARY-SCREENING-REWORK-V1-REVIEW1
parent_workplan: CODE-MLFF-TARGET-SIZE-EXACT-BOUNDARY-SCREENING-REWORK-V1
protocol_version: 5.7.0
status: active
created_date: 2026-08-26
reviewed_implementation_head: f56f348f6add8443e91e26f07b53efc944be6fc3
review_verdict: fail
routing: implementation_nonconformance
---

# Exact-Boundary Screening Rework — Review-1 Closure Amendment

## Authority

This amendment extends and tightens `MLFF_TARGET_SIZE_EXACT_BOUNDARY_SCREENING_REWORK_WORKPLAN.md` after independent review of implementation head `f56f348f6add8443e91e26f07b53efc944be6fc3`.

The original product design remains accepted. No architecture reopen is required. All previously frozen exact-boundary, continuation, production-independence, classifier, evidence, and horizon-removal semantics remain authoritative. This amendment adds the two blocking implementation/acceptance obligations that the reviewed implementation did not yet close.

Where this amendment is more specific than the parent workplan on overshoot recovery or acceptance-boundary fidelity, this amendment controls.

## Review disposition

The reviewed implementation substantially realizes the target design, including authoritative DATA8 job-protocol classification, boundary-only target-size reporting/evidence, independent production `n`, and removal of target-size screen-horizon authority. It nevertheless remains **FAIL** for closure because:

1. overshoot detection is not guaranteed for interrupted/failed-but-recoverable TRAIN2 runtime state before continuation; and
2. the required assembled `select-target-size` acceptance still substitutes fakes for semantic owners whose production behavior is the claim under test.

Both findings are implementation nonconformance under the existing design. Neither is a redesign trigger.

## Blocking finding R1 — overshoot recovery must be execution-state agnostic

### Protected concern

Exact-boundary screening authorizes training only through the current active boundary. Authorization is a property of authenticated runtime state, not of whether the outer `TrainingRunExecutionRecord` has already reached `SUCCEEDED`.

An interrupted, failed, cancelled, or recovered attempt may have durably persisted a valid TRAIN2 runtime summary/checkpoint at epoch `e`. If `e > active_boundary`, that state is scientifically unauthorized for the current rung and must never be resumed or accepted merely because the outer execution record is non-successful.

The reviewed implementation currently performs its explicit overshoot routing only after entering the successful-run continuation path. That is insufficient for interruption/recovery closure.

### Frozen corrected invariant

For every current target-size TRAIN2 run with recoverable runtime artifacts, before the scheduler decides to skip, resume, retry, recover, or enqueue further training:

```text
authenticated_completed_epoch <= active_boundary
```

must hold.

If authenticated state proves:

```text
authenticated_completed_epoch > active_boundary
```

then the current screening generation is overshot. It must fail closed, preserve compact forensic diagnostics, invalidate current target-size screen execution/evidence/selection authority, and restart the screen from coarse while preserving scientifically unchanged REPAIR2/MVQUAL2 and DATA7/DATA8 candidate materialization.

This rule applies independently of outer execution-record state, including:

- `SUCCEEDED`;
- interrupted/nonterminal attempts;
- failed infrastructure attempts with recoverable TRAIN2 state;
- locally recovered execution records;
- parent-process interruption after the child has durably persisted a boundary companion/summary.

A recoverable run at or below the active boundary is not overshot merely because the attempt was interrupted. Existing authentic restart semantics remain valid for such state.

### Required implementation consequences

1. Centralize current target-size runtime-state reconciliation before continuation disposition. Do not make overshoot inspection conditional on `TrainingRunState.SUCCEEDED`.
2. When TRAIN2 runtime artifacts exist, authenticate the runtime summary/companion using the existing TRAIN2 ownership path before deciding whether the run may resume.
3. Route `completed_epochs > active_boundary` through the existing safe overshoot invalidation owner or an equivalent single owner; do not duplicate ad-hoc deletion logic in scheduler branches.
4. Preserve candidate-specific scientific/numerical-failure semantics. A genuine authenticated numerical failure at/before the active boundary remains a candidate outcome rather than being converted into overshoot.
5. Existing runtime artifacts that imply resumability but lack a valid/authentic summary/companion must fail closed with an actionable recovery diagnostic. They must not be silently treated as a fresh run while stale checkpoints can still be discovered.
6. Add defense-in-depth at TRAIN2 runtime activation/continuation: a restored/current epoch strictly greater than `execution_epoch_limit` must be rejected before another optimizer update can execute. The campaign owner remains responsible for user-facing invalidation/restart routing; the runtime guard prevents accidental bypass by any caller.
7. Do not invalidate scientifically valid DATA7/DATA8 solely because a screen execution overshot. The rework remains an execution/evidence reset, not a rematerialization mandate unless independent DATA8 identity validation fails.

### R1 acceptance evidence

Focused and affected regression must establish all of the following:

- successful persisted run at boundary: accepted as the exact current boundary;
- successful persisted run above boundary: invalidated/restarted coarse;
- interrupted/non-successful run with authenticated runtime state below boundary: resumable under existing restart rules;
- interrupted/non-successful run exactly at boundary: treated as recoverable boundary completion, not authorized to advance past the reducer;
- interrupted/non-successful run above boundary: invalidated/restarted coarse before any new child work starts;
- stale/corrupt/missing TRAIN2 continuation summary with otherwise recoverable-looking target-size runtime artifacts: fail closed;
- lower-level runtime continuation with `current_epoch > execution_epoch_limit`: rejects before training;
- valid numerical failure at/before the boundary retains candidate-failure semantics.

At least one test must exercise the production scheduler/recovery caller that detects overshoot; directly calling `_invalidate_overshot_target_size_screen()` alone is not acceptance for this finding.

## Blocking finding R2 — assembled real-owner target-size acceptance is mandatory

### Protected concern

The original defect escaped because lower-level TRAIN2 runtime behavior could be correct while the public campaign was misclassified as historical and therefore assembled the wrong authorization geometry. Acceptance must therefore be **proxy-proof** against failures in the real orchestration chain.

A test that patches `_execute_train_current_authority`, `_execute_evaluate_current_authority`, the policy-family classifier, reducer, scheduler authorization, runtime-plan owner, persistence owner, or selected-size transition can remain green while the real product path is broken. Such evidence cannot close this workplan.

### Required real owner/path

After the final executable correction, at least one bounded integration test must execute the real semantic chain:

```text
current TOML/config
-> real CampaignStore/current-state reconciliation
-> real target-size study/boundary authority
-> real DATA8 job lookup
-> real TrainingCampaignPlan/run construction
-> real MaceJobArtifact protocol classification
-> real shared scheduler authorization
-> real TRAIN2 runtime-plan assembly
-> bounded external numerical child seam
-> real training execution persistence/recovery consumer
-> real exact-boundary endpoint evidence assembly
-> real target-size reducer
-> real survivor authorization for next boundary
-> real final selected-size freeze
```

The public owner must be `command_select_target_size` (or the exact public CLI entry that delegates to it without replacing semantics).

### Allowed test doubles

To keep functional acceptance bounded and hardware-independent, the test may replace only dependencies below/outside the semantic-owner boundary, including:

- expensive external MACE numerical stepping/subprocess compute;
- GPU execution;
- expensive model prediction payloads;
- large scientific datasets, using deterministic reduced fixtures that preserve the same ownership/state transitions.

A bounded fake child may consume the real runtime plan/environment and emit deterministic minimal artifacts needed by the real parent consumer. It must not decide which candidates survive, what the active boundary is, whether continuation is authorized, or what target size is selected.

### Forbidden substitutions for closure evidence

The assembled acceptance test must not monkeypatch, stub, precompute, or substantially reimplement:

- `command_select_target_size`;
- `_campaign_training_policy_family()` or its successor;
- `_execute_train_current_authority()` as an owner;
- `_execute_evaluate_current_authority()` as an owner when it performs target-size endpoint/reducer ownership;
- target-size stage/boundary selection;
- survivor reduction/ranking;
- shared scheduler authorization/disposition;
- `build_train2_runtime_plan()` / runtime-plan ownership;
- `CampaignStore` persistence/reopen behavior;
- TRAIN2 restart/continuation authentication;
- selected-size freeze/state transition.

A structural guard should prevent the designated real-owner acceptance module from accidentally patching those owners in future revisions. This guard is supplemental; it does not replace execution of the real path.

### Required assembled scenarios

#### R2-A — default exact-boundary funnel

Using default `(1,3,10)` screening boundaries:

1. all qualified candidates receive authorization only through epoch 1;
2. each real parent consumer observes exact epoch-1 completion;
3. coarse ranking/reduction executes before any epoch-2 work is authorized;
4. eliminated candidates receive no later child invocation;
5. survivors resume authenticated continuation and are authorized only through epoch 3;
6. short reduction executes before epoch-4 work is authorized;
7. finalists continue only through epoch 10;
8. final reduction freezes exactly one selected target size;
9. no screening epoch 11 exists;
10. `command_select_target_size` returns without falling through into production training.

The evidence must make it impossible for a regression back to `Historical training` / full-10-epoch coarse execution to remain green.

#### R2-B — interruption/reopen continuation

Within the same real-owner harness:

1. interrupt after authentic screen runtime state has been durably persisted at an allowed boundary or partial pre-boundary point;
2. close and reopen `CampaignStore` / command state;
3. rerun the public target-size owner;
4. prove the real recovery path reuses the authenticated checkpoint/optimizer/LR/RNG continuation rather than restarting the surviving trajectory;
5. prove the reducer still interposes before authorization of the next boundary.

#### R2-C — overshot interrupted state

Seed, through the allowed bounded child seam, an authentically serialized TRAIN2 runtime state whose completed epoch is above the active boundary while the outer run is non-successful/interrupted. Reopen through the real public owner and prove:

- overshoot is detected before new training work;
- current screen execution/evidence is invalidated;
- screen authority returns to coarse;
- scientifically valid DATA7/DATA8 remain reusable;
- unauthorized checkpoint state cannot become reducer evidence.

This scenario closes R1 and R2 together at the assembled boundary.

### Additional nondefault coverage

The existing nondefault `(2,5,12)` functional tests may remain lower-cost focused/integration coverage if they exercise the real target-size authority/reducer semantics. A second full expensive assembled harness is not required merely for symmetry unless the implementation branches materially on those values.

## Gate G — state-agnostic recovery closure

Gate G is added after existing Gate D implementation and before final acceptance closure.

Required completion:

- implement R1 state-agnostic overshoot reconciliation;
- add the runtime defense-in-depth guard;
- run focused recovery tests;
- run affected scheduler/runtime/persistence regression before proceeding;
- demonstrate no regression to valid partial continuation or scientific-failure handling.

Gate G **fails** if any existing recoverable target-size runtime can execute a new optimizer update while its authenticated completed epoch already exceeds the active boundary.

## Gate H — proxy-proof assembled acceptance closure

Gate H is the final executable acceptance gate.

Required completion:

- implement the R2 real-owner harness;
- execute R2-A, R2-B, and R2-C after the last material executable edit;
- rerun the final affected-surface regression derived from the assembled diff;
- run repository-required checks that intersect the affected surface;
- record any unexecuted required check as blocking rather than treating proxy/unit evidence as a pass.

Gate H **fails** if a test replaces a semantic owner listed under forbidden substitutions and is then used as evidence for that owner's correctness.

## Secondary nonblocking cleanup

The following review observations should be corrected opportunistically when touching their owning surface, but they do not independently block merge once Gates G/H and the parent workplan are satisfied:

1. `PerfP2RStagePlan.trajectory_schedule_extent_epoch` duplicates `fidelity_epochs[-1]` for screening. Prefer deriving it or structurally enforce equality so it cannot become a second mutable screen authority. Do not reopen the architecture solely to remove the field if it remains demonstrably derived/internal.
2. Generic TRAIN2 comments/errors that still say "full horizon" or "frozen epoch horizon" for screening should use role-neutral deterministic schedule/budget terminology where practical. Production horizon terminology remains valid for production `n`.

These cleanups must not delay or weaken the two blocking closures.

## Updated task-specific acceptance

The parent workplan's acceptance list remains required, with these clarifications/additions:

- Parent item 7 (overshoot recovery) applies to **all authenticated recoverable runtime states regardless of outer execution-record terminality**.
- Parent item 15 (final integration) means the R2 assembled real-owner path; helper-level or command tests that replace scheduler/train/evaluate/reducer ownership do not satisfy it.
- The final candidate must pass Gate G and Gate H after the final material executable edit.
- Full GPU/long-data/production-scale qualification remains deferred exactly as in the parent workplan; none of the new acceptance obligations requires production-scale MACE or target-hardware execution.

## Implementation authority amendment

### Frozen

- overshoot authorization is determined from authenticated TRAIN2 runtime progress, not `TrainingRunExecutionRecord` success alone;
- no restored/current TRAIN2 epoch above the active execution boundary may perform another optimizer update;
- overshot interrupted state invalidates current screening authority and restarts coarse while preserving scientifically valid DATA7/DATA8;
- final acceptance must execute the real target-size public owner, classifier, scheduler, runtime-plan assembly, persistence/recovery, reducer, survivor authorization, and selected-size freeze;
- bounded numerical/GPU work may be faked only below that semantic boundary.

### Delegated

- exact helper factoring used to reconcile existing runtime state before scheduler disposition;
- exact bounded child transport used by the assembled integration test;
- exact interruption injection point, provided durable authentic runtime/restart state is exercised;
- exact forensic diagnostic naming;
- whether the lower-level epoch-limit defense lives in runtime construction, activation, continuation restoration, or an equivalent pre-update invariant, provided bypass is impossible.

### Reopen only on evidence

Reopen design only if implementation demonstrates with concrete evidence that:

- the current TRAIN2 persistence format cannot authenticate completed epoch for interrupted state without destructive ambiguity; or
- the real semantic owner/path cannot be exercised with a bounded external numerical seam without executing production-scale/GPU training.

Test inconvenience, fixture complexity, or existing proxy tests are not redesign triggers.
