
---
kind: implementation-workplan
workplan_id: MLFF-PRODUCTION-GLOBAL-TRAIN-SCHEDULER-REPAIR
protocol_version: 6.4.0
status: implementation-ready
created_date: 2026-09-19
branch: design/mlff-production-global-train-scheduler-repair
basis_commit: f341a3f993b931c5e0838e95520b8b4fd41459ae
highest_affected_domain: D3
d1_d2_change: false
production_gpu_qualification: deferred-final-release
---

# MLFF production global TRAIN scheduler repair - D3 -> D4 implementation workplan

## 0. Disposition

**PASS AS IMPLEMENTATION WORKPLAN / FROZEN FOR D4. No Serious Challenge is active.**

This cycle repairs final-production orchestration only. The defect is not that the adaptive TRAIN2 controller cannot promote concurrent work. The defect is that train-production authenticates the frozen collection as one experiment, then serializes selected sizes outside the existing scheduler and constructs a fresh scheduler for each size. The scheduler therefore sees only the seeds of the current size, not all independently ready final-production trajectories.

For a frozen two-size collection with the current one-seed production policy, the implementation presents one task at a time to a scheduler whose truthful task ceiling is one. With two configured final seeds it presents two tasks for the first size and, only after that size is completely assessed and published, another two tasks for the second size. This is structurally work-starving when the one shared CPU/GPU resource envelope could safely admit concurrent production trajectories from different selected sizes.

The repair is to make **all unsealed final-production TRAIN2 positions across the fully admitted frozen collection participate in one existing adaptive TRAIN scheduler wave**, then return each result to its original per-size scientific owner for assessment and publication.

Cross-validation scheduling is explicitly out of scope and remains unchanged.

## Background and terminology

A **production position** is one exact final-production trajectory authorized by one FinalProductionPlan, identified by its selected TargetBinding, optimizer seed, production horizon, method/replay ancestry, and existing run-plan identity.

A **production collection wave** is the execution-local set of all currently required, not-already-sealed production positions across every frozen selected size after the collection-wide CV admission barrier succeeds.

A **scheduler slot** is execution-local queue identity only. It must be unique within the collection wave and must not enter scientific/numerical identities.

A **scheduler-compatible execution profile** is the set of resource-control inputs that must be common for positions to share one AdaptiveTrainingConcurrency instance: effective device/backend, training precision/runtime realization, canonical execution concurrency policy, effective CPU/RAM resource budget, loader-worker geometry used by scheduler planning, and live GPU telemetry domain. Scientific inputs such as N, exact target membership, optimizer seed, production horizon, and per-size accepted CV ancestry are intentionally not collapsed into this profile.

## 1. Outcome and authority

### Protected stakeholder/product outcome

After train-production has authenticated the entire frozen multi-size design and every selected size has current accepted CV ancestry, all independent production TRAIN2 positions that are ready to run must be visible to the **one existing bounded TRAIN scheduler**. Idle admissible capacity must not be withheld merely because another ready trajectory belongs to a later selected size.

The change must preserve exact per-size scientific identity, assessment, publication, restart, failure, and currentness semantics.

### Accepted D3 architecture being concretized/revised

Current D3 already establishes:

- one frozen ordered selected-size collection over one prepared generation;
- independent CV and production descendants under each size's own TargetBinding;
- a collection-wide final-production admission barrier;
- no cross-size final-publication committee or release winner;
- completed sibling evidence remains reusable across retries;
- one effective resource allocation must own post-selection MACE concurrency;
- TRAIN2 and EVAL2 are phase-separated so EVAL2 never shares accelerator residency with an active scheduler-owned TRAIN2 process;
- process outcome, cancellation completion, and accelerator teardown remain owned by the TRAIN2/run owner rather than inferred by the scheduler.

The predecessor multi-size workplan allowed serial outer-size execution as a simple default but explicitly allowed overlapping sizes **through the existing bounded scheduling** provided resource ownership was not multiplied. This cycle selects that already-admissible work-conserving architecture for final production and supersedes the serial-production concretization only.

The current Architecture Manual at docs/arch_manuals/mlff_training_data/50_target_size_selection.md does not require production serialization; it requires per-size descendant isolation plus a collection-wide admission barrier. The current CLI specification contains the stale stronger statement that outer size iteration is serial; that D4 specification must be reconciled.

### Applicable D1/D2 constraints

This is a D3/D4 execution repair. It MUST NOT change:

- selected sizes or frozen order;
- exact T_N membership;
- CV fold construction, CV seeds, CV acceptance, or CV scheduler behavior;
- production seed policy or default seed count;
- optimizer-seed identity;
- per-size production horizon;
- training method, optimizer, objective, replay exposure/admissibility, precision, architecture, or checkpoint policy;
- final-seed assessment policy;
- representative selection;
- per-size publication decision or product identity;
- the absence of a cross-size reducer/committee/release-selection rule.

Execution width, queue position, task completion order, and cross-size interleaving remain non-scientific execution facts.

### Stable D4 contracts/specification

Preserve the existing public train-production command, configuration surface, FinalProductionPlan, production run-plan identities, run roots, assessment-position identities, publication records, current pointers, and restart artifacts.

No new public option, environment variable, scheduler configuration key, persistence schema, database table, GPU lease manager, retry subsystem, or cross-size scientific record is authorized.

### Explicit non-goals

- No CV scheduler change.
- No production seed-count change.
- No adaptive promotion/backoff redesign in training_parallel.py unless implementation proves a separate coherent defect; such a finding reopens scope.
- No concurrent EVAL2.
- No cross-size publication aggregation.
- No release qualification rule for multi-size experiments.
- No production-scale GPU qualification during this cycle; standing project policy defers that to the final complete-release qualification package.

## 2. Cycle decisions and delegated D4 space

### D3-1 - One collection-level TRAIN scheduler owner

After the collection-wide CV admission barrier succeeds, every unsealed final-production position from every selected context enters one scheduler-ready population governed by exactly one call path that constructs one TrainingConcurrencyPlan and one AdaptiveTrainingConcurrency for that production TRAIN wave.

The implementation MUST NOT create an outer size executor around existing per-size schedulers. It MUST NOT nest one scheduler per selected size beneath another resource owner.

### D3-2 - Planning and publication remain per-size; execution queue is collection-scoped

Scientific planning remains owned per PostSelectionContext:

~~~text
selected context
  -> current accepted CV ancestry
  -> FinalProductionPlan
  -> final run plans / assessment positions
~~~

Only execution-ready positions are flattened:

~~~text
all per-size production positions
  -> one TRAIN scheduler population
  -> one global TRAIN phase
  -> deterministic EVAL2 completion
  -> return results to each original per-size owner
  -> per-size assessment/publication
~~~

Flattening must not synthesize a collection-level FinalProductionPlan, run identity, assessment policy, completion record, or publication decision.

### D3-3 - Scheduler task carries its real owner

The execution item passed to the shared scheduler must carry or resolve, without ambiguity:

- owning PostSelectionContext;
- owning training budget policy;
- run plan;
- exact training/monitor/outer-evaluation memberships;
- progress context;
- reusable measurement offers;
- local per-size position identity/slot needed for deterministic reduction;
- one wave-global execution slot/key used only for scheduler bookkeeping.

The scheduler must never use a single outer context or budget_policy for heterogeneous tasks merely because the current implementation signature does.

### D3-4 - One scheduler-compatible execution profile is proved before launch

Before any production TRAIN2 child is admitted, the collection execution owner must prove that all pending TRAIN2 positions can legally share one scheduler resource domain.

At minimum the compatibility check covers all values consumed by scheduler planning or shared telemetry:

- effective device/backend and GPU telemetry domain;
- method/runtime realization relevant to accelerator ownership;
- precision where it changes runtime residency;
- canonical execution parallel-training policy;
- effective CPU/RAM allocation returned by the existing resource owner;
- loader-worker count/geometry consumed by build_training_concurrency_plan;
- any existing per-job resource estimate used by admission.

The expected current campaign configuration should make these identical across selected sizes. If they are not identical, fail closed **before starting any new production TRAIN2 process** and report the incompatible fields. Do not silently choose the first context's values, take minima/maxima ad hoc, or launch multiple schedulers.

This validation is execution-local. Do not persist a new resource-profile authority.

### D3-5 - TRAIN/EVAL phase separation is collection-wide

No fresh EVAL2 work may begin while **any** production TRAIN2 task in the collection wave remains active, queued, demoting, cancelling, or not yet terminal.

After the global TRAIN wave succeeds, EVAL2 executes through the existing continuation/run owner from authenticated TRAIN2 roots. EVAL2 remains serial unless separately redesigned later.

The deterministic EVAL2 traversal order is frozen collection order, then each final plan's required_final_seeds order. Runtime TRAIN completion order must not determine scientific assessment/publication order.

### D3-6 - Existing failure and teardown ownership survives globalization

A terminal TRAIN-wave failure or user interruption:

1. stops new admission;
2. signals every scheduler-owned active task through the existing per-run cancellation event;
3. waits for the execution/process owner to return and reap its child;
4. begins no EVAL2 in that failed invocation;
5. preserves every authenticated TRAIN2 completion already durably published;
6. relies on ordinary restart/currentness on a later healthy invocation.

Memory-pressure demotion remains a scheduler resource action, not a scientific failure. The demoted position retains exact run identity and returns to the same pending population.

The scheduler must not infer successful teardown from a cancellation request, future cancellation flag, or elapsed timeout.

### D3-7 - Sealed roots do not consume TRAIN admission capacity

Before the global concurrency plan is built, authenticate/classify every production position using the existing run-root completion owner.

Already sealed TRAIN2 roots:

- do not enter the TRAIN task count;
- do not launch a trainer;
- do not consume maximum_jobs;
- remain eligible for post-TRAIN EVAL2/reassessment through the existing continuation path.

Thus task_count means **unsealed TRAIN2 work actually needing scheduler admission**, not total scientific positions.

If all required TRAIN roots are already sealed, no adaptive TRAIN scheduler is constructed merely to report zero work; proceed through deterministic EVAL2/reassessment/publication using existing authenticated state.

### D3-8 - Recovery preflight is collection-wide before admission baseline

The existing durable-continuation preflight can realize training state and affect CUDA occupancy. Therefore all unsealed production positions across the collection must complete recovery classification/authentication before the authoritative post-preflight GPU baseline and before any new child is admitted.

A foreign/corrupt/incompatible continuation in any pending production position fails the wave before sibling launch. Do not preflight lazily after other sizes have started.

### D3-9 - Collection-wide production barrier remains stronger than scheduler readiness

_cv_admission_blockers(contexts) remains ahead of all production planning/execution that could start new training. If one selected size lacks current accepted CV ancestry, the command launches zero production trainers for every size.

The globalization repair must not turn the barrier into per-task filtering.

### D3-10 - Per-size assessment/publication remains authoritative and ordered

After all required results exist, each selected context is finalized independently using its current FinalProductionPlan, positions, and evidence.

For each size:

- every required final seed is assessed;
- typed no-admissible outcomes remain durable;
- a rejected final seed prevents that size's final publication exactly as today;
- no sibling size's evidence can satisfy or alter local completion;
- publication uses the existing per-binding owner.

The implementation may finalize sizes in frozen collection order after the global evaluation phase. It must not make cross-size scheduler arrival order observable in publication semantics.

### D3-11 - Campaign-level progress tells the truth

The public TRAIN scheduler line for final production must describe the global unsealed TRAIN wave:

- progress = completed TRAIN roots / global unsealed TRAIN positions;
- active/queued/failed counts are global to that wave;
- plan ceiling is computed from that task count and shared resource profile.

Per-child TRAIN heartbeats retain their own N_selected, seed/run, and phase context.

For two selected sizes with one required production seed each, a fresh run must initially expose two scheduler positions, not an isolated 0/1 wave followed by a second unrelated 0/1 wave.

Stage-level campaign status remains one post_selection_final_production stage over the complete requested collection.

### Delegated D4 space

Implementation may choose internal helper names, dataclass names, mapping shape, and whether planning/finalization are extracted from execute_final_production into private helpers. The required architecture is behavioral and ownership-based.

A preferred minimal reduction is:

~~~text
prepare one per-size production execution bundle
  -> collect bundles
  -> classify sealed vs unsealed positions
  -> execute unsealed positions once through generalized existing scheduler
  -> evaluate sealed/trained positions in deterministic order
  -> finalize each per-size bundle with existing assessment/publication logic
~~~

The implementer may re-shape _PendingPostSelectionRun, _preflight_post_selection_pending_runs, _execute_post_selection_pending_runs, and _run_post_selection_positions so each task owns its context/policy instead of receiving one function-global context.

### Simplification target

Remove the final-production outer serialization in execute_current_train_production as the owner of resource scheduling.

Do **not** compensate by adding another executor, queue, scheduler, lease registry, or retry wrapper. Rewire the existing scheduler boundary so it receives all authorized ready production work.

## 3. Material implementation obligations

### O1 - Extract planning from execution without duplicating production authority

Refactor execute_final_production as needed so the command can construct and authenticate every per-size plan/run position before launching the collection TRAIN wave.

Planning must continue using the exact current owners for CV reauthentication, replay resolution/lineage, common monitor/separation, final-plan construction/validation, final training budget policy, assessment policy digest, reuse offers, run-plan construction, evidence-store publication, and final-plan current-pointer publication.

Do not copy these calculations into a second collection-specific planner.

Acceptance: changing only execution width or cross-size queue order produces byte-identical scientific run/position identities to serial execution for the same accepted inputs.

### O2 - Generalize the existing pending-run execution boundary

The scheduler path currently accepts one context and one budget_policy; that is insufficient for collection work. Rewire it so execution calls execute_post_selection_run with the owning task's context/policy.

All scheduler state maps must key by a wave-global unique slot/key. A local seed index such as slot=0 is not globally unique across sizes and MUST NOT be used directly once positions are flattened.

The global slot/key is execution-only and MUST NOT be hashed into run plans, assessment positions, evidence, or publication.

### O3 - Preserve deterministic resource backoff

Insertion order of active tasks currently defines the deterministic most-recently-admitted backoff victim. Preserve deterministic behavior after globalization.

Fresh queue order is frozen selected-size order, then FinalProductionPlan.required_final_seeds order.

A demoted task returns to the existing restartable queue with its original scientific owner and wave identity. Do not substitute smallest/largest N or seed ranking as backoff policy.

### O4 - Preserve exact restart/reuse semantics

Globalization must work when the initial collection contains any mix of no prior roots, sealed TRAIN2 roots awaiting EVAL2, complete current assessments, stale historical assessment offers, interrupted resumable TRAIN2 roots, and positions requiring fresh training.

A retry must schedule only actually unsealed current TRAIN2 work, then evaluate/reassess through existing owners. Completed sibling work cannot be invalidated merely because another selected size previously failed.

### O5 - Preserve publication barriers/currentness

Every existing publication remains under its binding/campaign-generation barrier and current-pointer/currentness checks. A collection scheduler result is not authority to publish if the owning context became stale before finalization.

No collection-level publication transaction is introduced. If a later per-size finalization fails its currentness/publication check, preserve already immutable evidence and report the real failure.

### O6 - Preserve single-size behavior

For one selected size, the generalized path must remain behaviorally equivalent to the current production path: same plans/identities, task population, adaptive-controller semantics, TRAIN/EVAL separation, assessment/publication, and failure/restart semantics.

The repair must not special-case multi-size by maintaining two independent production implementations.

### O7 - Do not promote seed policy into scheduler policy

The current generated production default is seeds=[1]. This workplan does not change it.

The scheduler receives the sum, across selected sizes, of required final seeds whose current TRAIN2 roots are unsealed.

Thus two selected sizes with one seed each naturally provide two independent TRAIN2 positions. If the user configures two final seeds per size, four scientific positions exist; that count comes from the existing production policy, not scheduler invention.

### O8 - Reconcile specification/documentation without rewriting history

Update current documentation so it no longer says final-production outer iteration over sizes is necessarily serial.

Current architecture/specification must distinguish:

- CV: unchanged current orchestration;
- production: collection-wide barrier followed by one bounded collection TRAIN wave, then per-size evaluation/assessment/publication.

Do not edit historical snapshots to make history look different. The archived predecessor workplan remains historical evidence that serial production was once an accepted concretization and that bounded overlap through the existing scheduler was already permitted.

### O9 - Keep training_parallel.py stable unless separately falsified

The present production defect is upstream of the adaptive controller's task population. Do not alter promotion thresholds, monotone backoff, stabilization windows, GPU budget formulas, or requested/min/max concurrency merely to make the multi-size test pass.

If generalization exposes a genuine controller defect independent of task scoping, stop and reopen the workplan with evidence rather than bundling an unrelated scheduler-policy change.

## 4. Evidence and dependencies

### Historical Applicability Set (HAS)

Decision basis:

~~~yaml
pem_basis:
  repository_state: hjin98/mdstats@f341a3f993b931c5e0838e95520b8b4fd41459ae
  published_pem: hjin98/mdstats@f341a3f993b931c5e0838e95520b8b4fd41459ae:PROJECT-ENGINEERING-MEMORY.md
  pem_declared_reconciled_through: 4eabe2ae9783c7ff92f3a1093c37502a01380812
  coverage: PARTIAL
candidate_overlay: NONE at workplan creation
~~~

Material current PEM entries:

- FF-004: scheduler policy must not infer process outcome/teardown or live accelerator residency outside the process/resource owner.
- FF-002: restartable TRAIN2 state must remain authenticated at the exact durable boundary.
- SP-001: prefer rewiring the real owner over additive duplicated machinery.
- SP-003: authenticated completed run evidence remains reusable across restart and sibling failure.
- SP-004: real-owner integration is required for orchestration claims.

Because the published PEM is partial and declares reconciliation only through 4eabe2ae, absence of a later family is not evidence of no relevant history. This workplan additionally binds direct bounded intake of:

- workplans/archive/MLFF_TARGET_SIZE_MULTI_SELECTION_AND_PER_SIZE_HORIZON_WORKPLAN.md, especially R4/R6;
- its implementation review/closure lineage;
- workplans/archive/MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_*.md;
- workplans/archive/MLFF_P5_TRAIN2_MEMORY_PRESSURE_BACKOFF_AND_TERMINAL_INFEASIBILITY_*.md;
- current campaign_post_selection_runtime.py;
- current training_parallel.py;
- current multi-size integration and P5 execution/recovery tests.

### Evidence applicability

Existing tests for per-size scientific identity, CV barrier semantics, TRAIN2 cancellation/teardown, memory backoff, and restart remain relevant but are insufficient to prove the new collection scheduler scope.

Any old test whose oracle specifically requires serial production size iteration becomes stale by intended D3 change and must be replaced with an oracle for the stronger work-conserving ownership contract, not simply deleted.

No previous GPU performance result is accepted as proof of the new assembled collection scheduler. Target-hardware production qualification remains deferred.

## 5. Affected surface and acceptance

### Expected affected source surface

Primary:

- mdstats/training_data/campaign_post_selection_runtime.py

Expected unchanged semantic owner:

- mdstats/training_data/training_parallel.py

Current documentation/specification:

- docs/arch_manuals/mlff_training_data/50_target_size_selection.md
- docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md

Tests expected to require addition/reconciliation include:

- tests/test_mlff_target_size_multi_size_integration.py
- tests/test_mlff_replay_mace_p5_execution_recovery.py
- tests/test_mlff_p5_train2_zero_safe_admission.py
- relevant P5 production/restart and downstream-integration suites discovered from the final diff.

Re-derive the complete affected surface after implementation.

### Required focused acceptance

#### A1 - two sizes, one production seed each, global admission

Through the real train-production owner, with current accepted CV for both sizes and deterministic safe resource telemetry, prove:

- exactly two unsealed TRAIN2 positions enter one production scheduler wave;
- one AdaptiveTrainingConcurrency instance owns that wave;
- concurrency plan task_count is 2;
- safe telemetry can promote/hold two simultaneously active trainers;
- each trainer receives its own exact selected membership and horizon;
- both sizes finalize through their own publication owner.

A helper-level queue unit test is insufficient.

#### A2 - two sizes, two seeds each

With two configured final seeds per size, prove four production positions are present in one wave and bounded concurrency drains that global queue without duplicate run identities or schedule-order-dependent reduction.

#### A3 - heterogeneous horizons

Give selected sizes different frozen H_prod. Each run must receive the exact horizon from its own plan.

#### A4 - serial/concurrent semantic equivalence

Run the same bounded deterministic campaign with effective training concurrency one and greater than one. Require equality of scheduler-independent governed identities/results available to the deterministic test double: final plans, run-plan/training-trajectory identities, assessment positions, seed assessments, and per-size final completion/publication identities.

#### A5 - collection CV barrier

Make one selected size missing/stale/rejected at CV. Assert zero production trainer launches and no newly current subset publication.

#### A6 - preflight-before-launch

Install a foreign/corrupt durable continuation for one pending size while another is runnable. Assert collection preflight fails before any new sibling trainer starts.

#### A7 - sealed-root mixed restart

Provide one sealed TRAIN2 root and one unsealed sibling across different sizes. Assert only the unsealed position enters task_count/TRAIN admission; after the TRAIN wave, both reach the proper EVAL2/reassessment path from their own authenticated roots.

#### A8 - failure/cancellation/restart

Inject a real-owner TRAIN2 child failure after at least two cross-size tasks have been admitted. Assert no further admission, all active owned tasks are signalled/reaped, no EVAL2 starts, no orphan child remains, authenticated completed TRAIN2 state survives, and the next invocation schedules only outstanding work.

#### A9 - memory demotion identity

Force deterministic resource backoff while tasks from different sizes are active. Prove the most-recently-admitted task is the victim, execution owner returns cancellation verdict, task is requeued with unchanged scientific identity, and completed work is not duplicated.

#### A10 - incompatible shared resource profile

Construct two contexts differing in a scheduler-critical execution/resource value through a bounded test seam. Assert fail-closed behavior before any new trainer launches and an error identifying the incompatible dimension.

#### A11 - single-size regression

Run current one-size production acceptance/restart tests through the generalized path. No alternate implementation branch may remain.

#### A12 - truthful progress

For a fresh two-size/one-seed campaign, capture real scheduler output and prove planned/running lines report a two-job global wave. Child progress must still expose correct N_selected and seed/run context.

### Structural acceptance

Static/source inspection must establish:

- no production outer loop calls a complete per-size execute_final_production(context) that internally creates its own scheduler;
- no second scheduler/executor/lease manager was added for size concurrency;
- only one adaptive TRAIN controller is created for one collection production TRAIN wave;
- no wave-global slot/key participates in scientific content digests;
- historical architecture snapshots are unchanged.

### Affected regression

At minimum run focused suites covering multi-size target integration, P5 production/restart, zero-safe admission and memory backoff, replay/MACE P5 execution recovery, final-production assessment/publication, campaign lifecycle/status/advance around multi-size completion, and storage/currentness tests whose production roots/pointers are touched.

Then run complete affected MLFF campaign/training-data regression after all executable edits. If impact cannot be bounded confidently, run the repository's full available CPU test suite.

### Production qualification

**Deferred.** Functional CPU/deterministic real-owner acceptance is required now. Physical GPU throughput/VRAM qualification remains deferred to the final release package per standing project direction.

## 6. Authority/documentation/history impact

### D3 Architecture Manual

Update current target-size control-plane architecture to state that after the collection-wide production barrier, final-production TRAIN2 positions across selected sizes share one bounded scheduler resource allocation. Preserve per-size scientific descendant ownership and no cross-size reducer/publication.

This durable D3 correction must receive independent conformance review before promotion/merge.

### D4 specification

Update the CLI specification sentence that currently says the size dimension has serial outer iteration. It may remain true for current CV orchestration, but must no longer imply production serialization.

### D1/D2

No mutation. If implementation requires changing seed sets, horizon meaning, optimizer ordering, checkpoint acceptance, replay policy, or cross-size result reduction, stop and route the earliest upstream owner.

### Semantic history / PEM

Do not rewrite archived workplans or historical architecture snapshots.

At closeout, evaluate whether this episode materially extends an existing PEM family/pattern. Do not manufacture a new recurrence without accepted-repair chronology/evidence.

## 7. Stages and reuse

### Stage P1 - execution-bundle decomposition

Refactor final-production planning/finalization so per-size plans and positions can exist before execution. No behavior change to one-size scientific identity. Run focused production identity/publication tests.

### Stage P2 - collection scheduler generalization

Make pending tasks self-owning; flatten all unsealed production positions; implement compatibility/preflight/global task-count semantics; execute one TRAIN wave and deterministic post-TRAIN EVAL2. Run A1-A3, A6-A7, A10-A12 plus existing scheduler regressions.

### Stage P3 - failure/restart closure

Exercise global cancellation, demotion, sealed-root recovery, currentness/publication races, and retry. Run A5, A8-A9 and affected recovery/storage suites.

### Stage P4 - documentation and assembled acceptance

Reconcile Architecture Manual/CLI specification, re-derive final affected surface, run A4 plus complete affected regression, inspect absence/ownership conditions, and prepare independent Review handoff.

## 8. Reopen / Challenge triggers

### D4-local blockers

Keep within D4 when implementation can satisfy this workplan by restructuring private task carriers/helpers while preserving frozen ownership and semantics.

### Evidence requiring D3 reopen

Reopen D3 if:

- selected production contexts genuinely require incompatible simultaneous resource owners that cannot safely share one adaptive controller;
- collection-wide TRAIN/EVAL separation requires a second durable scheduler or materially new persisted orchestration state;
- per-size finalization cannot be made schedule-order-independent without changing public/architectural semantics;
- the current one-resource-domain assumption is false for an accepted campaign configuration.

### Evidence requiring D2/D1 challenge/reopen

Route upstream if concurrency/interleaving alters governed training semantics that D2 treats as execution-invariant, or if a cross-size result/seed/horizon rule becomes necessary.

### Structural complexity trigger

If implementation starts adding wrappers that retain the old per-size scheduler and synchronize a new collection scheduler around it, stop. Replace/consolidate the old boundary instead.

### Serious Challenge status

No current evidence contradicts accepted D1/D2. No Serious Challenge is active.

## 9. Final handoff

Implementation is complete only when:

- all production TRAIN2 positions across a fully admitted multi-size collection are visible to one existing adaptive scheduler wave;
- scheduler/resource ownership is singular and process teardown authority is preserved;
- sealed/restartable work is handled without duplicate training;
- collection-wide TRAIN/EVAL phase separation survives success, backoff, failure, and interruption;
- per-size plan/assessment/publication identity is independent of scheduler order;
- one-size behavior remains conforming;
- current D3/D4 documentation matches the repaired execution contract;
- all required focused and affected regression is green or explicitly unavailable/blocking;
- final affected surface, evidence applicability, and PEM/history impact are reconciled;
- no physical GPU qualification is falsely claimed.

Independent Review must reconstruct the real owner chain and attempt to falsify the global-scheduler claim. A test that merely calls a new helper with four synthetic tasks cannot close the workplan if the public train-production command can still serialize selected sizes before reaching that helper.
