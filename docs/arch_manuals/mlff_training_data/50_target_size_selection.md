# Part V - Target-size lifecycle and control-plane architecture

## Purpose and authority boundary

This chapter defines how the target-size method is integrated into the campaign control plane. D1 owns what the target-size experiment means and what claims its evidence supports. D2 owns the exact split, target-training/evaluation orders, common preparation, screen trajectory, metric, reducer, qualification rules, and numerical failure semantics. For `TargetTrainingOrder` / `pi_train`, the scoped D1/D2 owners are `docs/methods/mlff_target_training_order_scientific_method.md` and `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`; the detailed D3 owner is `45_target_training_order.md`.

D3 owns the lifecycle, operator/control-plane ownership, persistent identities, freeze boundary, restart/currentness behavior, and separation from downstream stages.

## Lifecycle

The current campaign path is:

```text
prepared target-size generation
  -> optional automatic screen/reducer evidence
  -> operator-owned provisional design
  -> cross-validate admission
  -> immutable frozen design and per-size TargetBinding records
  -> post-selection cross-validation for every frozen size
  -> collection-wide production admission barrier
  -> fresh final production per frozen size
  -> downstream qualification only where the accepted product contract permits it
```

The automatic screen produces evidence and an optional recommendation; it does not freeze the design. The operator owns the provisional design. `cross-validate` admission is the only freeze boundary.

## Prepared generation

One target-size generation binds the accepted upstream canonical evidence, protected-relation authority, target-size policy, exact `P_train/M3` split, `pi_eval`, the complete restored `TargetTrainingOrder`, configured-prefix qualification, and common P3 training preparation.

The target-training order is not reconstructed by P3 candidate execution. Its detailed preparation-owned chain is defined by `45_target_training_order.md`: sole fitted `TargetCoverageReference`, one canonical membership-obligation authority, one shared FEAS1/NEIGHBOR1 relation, MVIDX representation, MVSEL2/REPAIR2 construction, independent MVQUAL, and one complete `pi_train` whose configured memberships are exact prefixes.

Expensive target-order products are reusable while their authenticated parents remain current. The completed prepared generation has one currentness authority in `CampaignStore` plus content-authenticated large artifacts owned by their respective preparation/storage owner. A report, workspace path, selector checkpoint, or execution head is never an alternate generation authority.

Pre-adoption selector continuation state is subordinate reconstructible `prepare`/prepared-storage build state. It is attempt/build-owned, authenticated by prospective build identity and prefix/repair ancestry, and cannot be consumed downstream or make a generation current. CampaignStore currentness begins only after completed immutable prepared products are published and adopted through the existing currentness transition.

Unsupported historical target-size generations are not semantically migrated into current authority. In particular, `candidate_independent_priority.v1` target-order generations become stale/reconstructible when the restored multi-view policy is activated. Current loaders may detect and reject/quarantine obsolete derived state, while independently reusable lower-level source/frame/cache products remain subject to their own current owners. Old target ranks are not translated into the restored method.

## Automatic diagnostic integration

The P3 execution owner schedules only work authorized by the current D2 reducer state and publishes authenticated boundary evidence. It consumes the prepared P2 order/qualification projection; it does not map NEIGHBOR/MVIDX, resume MVSTATE, or reconstruct target-order science.

The reducer is pure with respect to campaign selection: it can emit a recommendation or typed no-recommendation result, but it has no API to mutate the frozen design.

A completed diagnostic is durable and reusable even when the provisional design changes. When an automatic invocation attempts to adopt a recommendation, it does so through the same provisional-design compare-and-set owner used by manual selection. If the operator changes the proposal or freezes the design while the diagnostic is running, the diagnostic evidence remains valid but its attempted adoption loses the race.

The human-facing diagnostic report is a derived, rebuildable view of authenticated reducer evidence. No consumer reads target size or currentness back from the report.

## Manual target-size selection

Manual `select-target-size N` consumes only the compact prepared P2 experiment definition/order/qualification evidence required to authenticate `N` and its exact prefix. It must not map NEIGHBOR/MVIDX, restore selector checkpoints, or trigger target-order preparation. An unqualified or nonexistent configured prefix fails before training/CV; manual choice is not a bypass around MVQUAL/P2 qualification.

## Provisional design

Before freeze, the operator controls an ordered collection of distinct selected sizes. Each entry records the selected size, the exact derived target membership identity, selection provenance, and resolved CV/production role horizons.

Architecturally:

- one size appears at most once;
- adding a distinct size appends an experiment;
- reselecting an existing size replaces that complete entry in place;
- resetting clears the provisional collection without deleting the prepared generation or valid diagnostic evidence; and
- selection provenance is audit metadata, not numerical identity.

Exact CLI spelling, defaults, argument validation, and serialized record fields are D4.

## Freeze at cross-validation admission

`cross-validate` admission authenticates the complete provisional collection against the current prepared generation and D2 candidate authority, re-derives every exact target membership from the already-prepared complete `pi_train`, and freezes the collection atomically before numerical CV begins.

One invalid member rejects the admission. There is no partial freeze and no silent reduction to the subset that still validates. After freeze, target selection commands cannot mutate the design.

The freeze creates two related representations:

- the **full frozen design entry**, which is the immutable operator/audit record including role horizons and provenance; and
- the **TargetBinding**, which is the role-neutral target identity consumed by CV, production, and qualification descendants.

The TargetBinding excludes sibling-list position, selection provenance, and role-specific horizons so unrelated steering does not contaminate another product's identity.

## Currentness and compare-and-set transitions

Campaign control-plane mutations are compare-and-set transitions against the exact predecessor revision. Long-running work captures the state it intends to update and may publish a current pointer only if the relevant authority is still current at commit time.

Currentness is re-established from authoritative parents at every public exposure. A stale caller object, report, cached pointer, workspace, or selector checkpoint cannot make itself current by being passed back to an API.

Currentness changes preserve historical evidence. They change the current pointer/ancestry relation; they do not rewrite old immutable records.

## Invalidation scope

Invalidation follows dependency, not stage name.

- A change to target-size D1/D2 identity creates a new target-size generation and retires its dependent screen/selection descendants.
- A target-order scientific parent/policy change invalidates the dependent restored order/qualification products; execution-only worker/cache/path changes do not.
- A CV-only policy change invalidates CV and downstream production for the affected target binding without changing target-size evidence.
- A production-only policy change invalidates production descendants without changing accepted CV evidence.
- A replay-only post-selection lineage change invalidates post-selection descendants that consume replay while leaving the target-size generation and frozen target bindings unchanged.
- Presentation, report, cache, worker-count, and other execution-only changes do not invalidate scientific/numerical evidence unless an owning D2/D4 contract declares them semantic.

## Per-size post-selection isolation

For a multi-size frozen design, each size owns independent CV and production descendants under its own TargetBinding. No size consumes another size's horizons, folds, run evidence, pointer, publication decision, or completion state.

Campaign CV acceptance is all-sizes. Final-production admission is also a collection-wide barrier: no new production work begins unless every frozen size has current accepted CV ancestry. Completed sibling evidence remains reusable across retries.

## Final-production scheduling is collection-scoped

Cross-validation keeps serial outer iteration over selected sizes. Final production does not: the previously accepted serial selected-size production scheduling is **superseded**, because it let idle admissible capacity stand while an independently ready trajectory of a later size waited for an earlier size to be completely assessed and published.

After the collection-wide barrier, `train-production` proceeds in one order for the whole collection:

1. **plan every size before publishing any of it.** Each size re-runs its own second-line current-CV/method authorization and constructs its FinalProductionPlan, run plans, assessment positions and reuse offers in memory. Only when every size has passed does each size publish its own binding-scoped plan objects and current pointer. There is no collection-level pointer transaction: a per-binding commit that validly succeeded is not rolled back because a sibling later fails, and a current plan pointer remains planning authority for its own binding rather than proof that training, evaluation, assessment or publication happened.
2. **normalize recovery across the collection.** Every production position resolves, under its existing run-activity exclusion and through its own current or historical recovery owner, to sealed state or to *still requires trainer execution*. An authenticated terminal-but-unsealed root - current or historical - is sealed there, with zero trainer launch, and is then authenticated read-only. Such a seal is an accepted recovery completion: it is durable even if a later sibling fails, and it is not an assessment.
3. **train what remains, in one wave.** Only positions that still require trainer execution enter the existing adaptive TRAIN scheduler, and they all enter the same one. Those positions must share one execution/resource profile, proved over exactly that set; a difference that the existing single-controller contract cannot represent fails closed before any trainer starts. Sealed positions never enter the task count, the controller ceiling, progress, or the profile proof.
4. **finalize per size, in frozen order.** Only after every scheduler-owned position is at an authenticated sealed TRAIN2 root does evaluation begin. Each size is then finalized independently and serially - EVAL2 in `required_final_seeds` order, all seed assessments, then its own binding-scoped publication - and finalization is fail-fast: a size that fails prevents later sizes from beginning fresh evaluation or publication in that invocation, while their sealed roots stay reusable evidence.

Scheduler arrival order, cross-size interleaving and execution width remain non-scientific execution facts. No cross-size reducer, committee, release winner, or collection-level completion record is created, and no size consumes another size's evidence.

Because the queue lengthens the interval between planning and admission, currentness is linearized rather than merely re-read: the invocation captures the exact `(campaign generation, ordered current binding digests)` of the design it was authorized for, and every new admission - the first, every later one including a requeued position, and the admission of the evaluation/finalization phase - is taken inside the same serialized CampaignStore transition authority that commits target-size generation transitions. Either the transition commits first and no further work is admitted for the retired design, or the admission commits first and that work settles as ordinary work whose results still face the existing commit-time per-binding publication fences. Same-generation state revisions that preserve the frozen design are not staleness. No campaign lock is held across training, telemetry waits, evaluation, or publication, and no persistent scheduler-currentness state exists.

## Multi-size completion boundary

When every selected size has a current final publication, a multi-size comparative training experiment is complete. The current release architecture has no owner that chooses one winning size from that collection, so downstream release qualification does not invent one by list order, automatic recommendation, or a downstream score.

A future release-selection rule requires its own accepted upstream method and D3 integration before it can become consequential.

## Public orchestration surface

The campaign lifecycle is:

```text
init -> doctor -> prepare -> select-target-size -> cross-validate -> train-production
```

`prepare` is the only public stage that may interpret live selector inputs and build/publish the restored target-order subsystem. `status` and `advance` project the owner graph; they are not independent state machines. `advance` may route only already-authorized consequential steps and cannot invent a target-size choice or reveal locked evidence.

Post-production qualification remains a separate downstream command family. Storage management is orthogonal to scientific lifecycle: it manages representations and retained artifacts but never advances selection, CV, production, or qualification authority.

## Restart and recovery

Completed prepared generations, diagnostic evidence, provisional/frozen control state, CV runs, and production runs resume through their existing authenticated owners.

Within target-order preparation, pre-adoption MVSTATE/rank-history/checkpoint products are reconstructible prepare-owned state rather than campaign-current state. Reuse requires exact prospective build identity, content/schema integrity, exact prefix/repair ancestry, and attempt isolation. Stale/corrupt/incompatible or foreign-attempt state is rejected/discarded or exactly reconstructed; path existence alone is never sufficient. Journals/history remain bounded and pre-repair continuation state cannot authorize post-repair continuation after divergence.

Partial screen matrices, CV runs, and production runs may be reused when their completion evidence authenticates. Contradictory durable evidence fails closed rather than being normalized into the expected shape.

Execution-local scratch may be reclaimed by its owning lifecycle only after rechecking that no accepted/current/restartable work depends on it. There is no selector-specific currentness database, migration registry, or GC owner.
