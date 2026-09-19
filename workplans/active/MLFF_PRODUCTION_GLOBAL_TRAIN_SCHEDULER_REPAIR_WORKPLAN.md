
---
kind: implementation-workplan
workplan_id: MLFF-PRODUCTION-GLOBAL-TRAIN-SCHEDULER-REPAIR
protocol_version: 6.4.0
status: implementation-ready
created_date: 2026-09-19
reviewed_date: 2026-09-19
revision: 2
workplan_review_status: pass-after-repair
reviewed_pre_repair_head: 10c68eb50cb7ee2b5f0bb8d43e35bb250a186d96
branch: design/mlff-production-global-train-scheduler-repair
basis_commit: f341a3f993b931c5e0838e95520b8b4fd41459ae
highest_affected_domain: D3
authority_state: stakeholder-authorized-d3-reopen-candidate
d1_d2_change: false
production_gpu_qualification: deferred-final-release
---

# MLFF production global TRAIN scheduler repair - D3 -> D4 implementation workplan

## 0. Disposition

**PASS AS IMPLEMENTATION WORKPLAN AFTER REVIEW REPAIR / FROZEN FOR D4. No Serious Challenge is active.**

This Revision 2 closes the bounded design-review gaps found against the accepted multi-size lineage, current P5/TRAIN2 owners, recovery/resource authority, and Protocol 6.4 handoff requirements. The review found no D1/D2 defect and no need for a second scheduler or new persistent orchestration machinery.

This cycle is a **stakeholder-authorized bounded D3 reopen of final-production selected-size scheduling**. Accepted multi-size lineage had ultimately frozen serial outer-size orchestration as the current concretization. This workplan intentionally supersedes that one production scheduling choice only; it does not retroactively reinterpret the archived serial design as already-global, and repository presence on this branch does not make the proposed D3 mutation accepted-current before independent falsification and merge through the normal architecture acceptance path.

This cycle repairs final-production orchestration only. The defect is not that the adaptive TRAIN2 controller cannot promote concurrent work. The defect is that train-production authenticates the frozen collection as one experiment, then serializes selected sizes outside the existing scheduler and constructs a fresh scheduler for each size. The scheduler therefore sees only the seeds of the current size, not all independently ready final-production trajectories.

For a frozen two-size collection with the current one-seed production policy, the implementation presents one task at a time to a scheduler whose truthful task ceiling is one. With two configured final seeds it presents two tasks for the first size and, only after that size is completely assessed and published, another two tasks for the second size. This is structurally work-starving when the one shared CPU/GPU resource envelope could safely admit concurrent production trajectories from different selected sizes.

The repair is to make **all unsealed final-production TRAIN2 positions across the fully admitted frozen collection participate in one existing adaptive TRAIN scheduler wave**, then return each result to its original per-size scientific owner for assessment and publication.

Cross-validation scheduling is explicitly out of scope and remains unchanged.

## Background and terminology

A **production position** is one exact final-production trajectory authorized by one FinalProductionPlan, identified by its selected TargetBinding, optimizer seed, production horizon, method/replay ancestry, and existing run-plan identity.

A **production collection wave** is the execution-local set of all currently required, not-already-sealed production positions across every frozen selected size after the collection-wide CV admission barrier succeeds.

A **scheduler slot** is execution-local queue identity only. It must be unique within the collection wave and must not enter scientific/numerical identities.

A **scheduler-compatible execution profile** is the set of runtime/resource facts that must either be equal or be conservatively represented by the existing single-controller planning contract for positions to share one AdaptiveTrainingConcurrency instance. It includes effective device/backend and telemetry domain, training precision/runtime realization, canonical execution concurrency policy, effective CPU/RAM allocation, loader-worker and inner-thread geometry, batch/model realization relevant to residency, the applicable per-job RAM/VRAM estimate regime, and the existing trainer/process-supervision and disk-reserve owners. Scientific inputs such as N, exact target membership, optimizer seed, production horizon, and accepted CV ancestry remain distinct identities; however, their *resource consequences* are not assumed irrelevant and must be checked where they can change scheduler demand.

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

The original multi-size workplan permitted bounded overlap through the existing scheduler as an implementation option, but the later accepted closure lineage froze **serial outer-size orchestration/resource ownership** as the selected current concretization. In particular, the multi-size implementation review and next-round closure retained serial selected-size orchestration, and later P5 recovery acceptance continued to treat serial selected-size orchestration as a structural oracle. Those accepted choices are not erased by the current Architecture Manual being less explicit.

The stakeholder direction for this cycle therefore reopens D3 narrowly: **final-production TRAIN2 scheduling across selected sizes becomes collection-scoped and work-conserving under the one existing adaptive scheduler**. Cross-validation selected-size orchestration remains serial and all non-conflicting multi-size architecture remains accepted.

Current canonical architecture/specification must be strengthened to represent this new accepted candidate if implementation and independent review pass. The Architecture Manual currently states the per-size descendant and collection-wide barrier invariants but is under-specified about final-production size scheduling; the CLI specification still states serial outer iteration. Both must be reconciled before the D3 change can become accepted-current.

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

Before any production TRAIN2 child is admitted, the collection execution owner must prove that all unsealed production positions can legally share one scheduler resource domain **under the assumptions the existing TrainingConcurrencyPlan/AdaptiveTrainingConcurrency actually make**.

The compatibility proof covers, at minimum:

- effective device/backend and exact GPU telemetry domain;
- shared method/model/runtime realization and learned-model precision relevant to residency;
- canonical execution parallel-training policy and effective CPU/RAM allocation;
- loader-worker count plus any inner native-thread/nested-runtime geometry that contributes to per-job CPU demand;
- batch/model/materialization geometry when it changes host or device memory demand;
- the per-job RAM and VRAM estimate regime consumed by the existing planner;
- trainer/process-supervision ownership, timeout semantics, and the trainer-local minimum-free-disk reserve owner.

N, exact membership, seed, and H_prod do **not** have to be equal. They remain scientific identities. But the implementation must establish whether changing N or another per-position input materially changes the per-job resource demand assumed by the homogeneous planner. The current code uses one loader-worker count and one configured RAM/VRAM estimate for the whole plan, then learns promotion demand from active jobs; it is therefore forbidden to calibrate on a light position and silently assume that observation bounds a later heavier position unless the existing resource contract makes that inference valid.

The preferred current result is a single compatible profile because all contexts share cfg, method, trainer, device, and execution policy. That expectation is not proof. D4 must provide a bounded real-owner compatibility test over distinct selected sizes/horizons and inspect the actual scheduler inputs.

If materially heterogeneous demand cannot be bounded safely by the existing single-controller contract without changing training_parallel.py, inventing per-profile buckets, or running multiple resource schedulers, **reopen D3**. Do not silently choose the first task's values, take ad-hoc minima/maxima, or broaden the controller inside this workplan.

The minimum-free-disk reserve remains enforced by MacePostSelectionTrainer per owned child. Do not add a disk scheduler. A disk/timeout failure retains the existing whole-wave terminal failure/cancel/reap semantics.

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

### D3-12 - Preserve both production authorization fences

The collection-wide _cv_admission_blockers(contexts) barrier remains the first production admission fence, but it is not the only one.

Before a per-size FinalProductionPlan is built or made current, the per-size production planner must re-run the existing exact authorization relation:

- resolve_current_cv_plan(context);
- resolve_current_cv_acceptance(context);
- require_cv_acceptance_for_method(...) against the current method and selected binding.

This is the accepted second-line race/currentness fence formerly inside execute_final_production(context). Splitting planning from execution MUST NOT delete, weaken, or replace it with the earlier collection preflight.

Every selected size's second-line authorization and final-plan/run-position planning must complete successfully **before the first new collection TRAIN2 child launches**. If any size fails this re-check, launch zero new trainers for the invocation. Commit-time selected-binding/generation fences remain authoritative later when pointers/assessments/publications are made current.

### D3-13 - Global TRAIN/EVAL may run ahead; finalization remains fail-fast in frozen size order

Globalizing TRAIN2 means a later selected size may already have authenticated TRAIN2/EVAL2 evidence before an earlier size's final-seed assessment is reduced. That execution overlap does not authorize later publication.

After the successful collection TRAIN wave and deterministic serial EVAL2:

1. finalize selected sizes in frozen collection order;
2. within a size, reduce required final seeds in FinalProductionPlan.required_final_seeds order;
3. on the first per-size assessment/publication failure, abort later size finalization for that invocation;
4. do not create a new final publication for any later selected size after that earlier failure;
5. preserve already-authenticated sibling TRAIN2 roots and immutable measurement evidence for ordinary reuse on rerun.

Thus the repair increases ready-work execution overlap while preserving the current fail-fast public finalization semantics. It does not invent a campaign-level production reducer or declare a failed size equivalent to a CV rejection.

### D3-14 - CV scheduling is an explicitly preserved sibling capability

The shared private pending-run/scheduler helpers serve both CV and final production. Refactoring them is therefore an affected surface even though CV architecture is not being changed.

The current public CV control shape remains:

~~~text
frozen selected sizes in frozen order
  -> one size at a time
  -> that size's existing fold/seed TRAIN scheduler wave
  -> serial post-TRAIN EVAL2
  -> per-size CV verdict
~~~

Do not flatten CV work across selected sizes, do not change CV queue ordering, and do not alter CV failure/rejection/restart semantics as a side effect of making tasks self-owning.

### D3-15 - Enumerate exact global production identity before scheduler construction

All per-size final plans, required run plans, assessment positions, and production tasks must be materialized/authenticated before constructing the collection concurrency plan.

Local seed slots are not globally unique. The collection execution owner must assign an execution-only wave key and prove before launch that no two tasks resolve to the same run_plan.run_identity or training-trajectory identity. A duplicate means a planning/identity defect and fails closed; the scheduler must never concurrently launch the same logical run twice.

Results route back through the owning binding/context plus local position (or an equivalent exact owner key). The wave key cannot enter a scientific digest, run-root identity, assessment position, or publication record.

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

The extracted per-size planner must preserve the accepted second-line CV authorization guard immediately before final-plan construction/publication. Build/authorize **all** per-size bundles before constructing the global TRAIN scheduler; a later-size planning/currentness failure must not occur after an earlier-size trainer has already launched.

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

If generalization exposes a genuine controller defect independent of task scoping or proves heterogeneous cross-size resource demand cannot be represented by its existing single-profile contract, stop and reopen D3 with evidence rather than bundling an unrelated scheduler-policy change.

### O10 - Preserve public finalization failure behavior

The global execution wave may produce reusable evidence for later siblings, but per-size assessment/publication still commits in frozen selected-size order and remains fail-fast. A failed N_i must prevent new final publication of N_j for j > i in that invocation. Do not turn available sibling measurements into implicit permission to complete/publicly succeed the remaining subset.

### O11 - Preserve CV behavior through shared-helper changes

Any change to _PendingPostSelectionRun, _preflight_post_selection_pending_runs, _execute_post_selection_pending_runs, or _run_post_selection_positions must retain the existing CV call path and semantics. No production-only assumptions may leak into the CV task carrier. Run the real public multi-size CV and scheduler/recovery regressions after the refactor.

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
- workplans/archive/MLFF_TARGET_SIZE_MULTI_SELECTION_AND_PER_SIZE_HORIZON_IMPLEMENTATION_REVIEW_REOPEN.md, including the mandatory second-line per-size production authorization fence;
- workplans/archive/MLFF_TARGET_SIZE_MULTI_SELECTION_NEXT_ROUND_REPAIR_WORKPLAN.md, which records the accepted serial outer-size concretization this cycle now reopens narrowly;
- workplans/archive/MLFF_REPLAY_MACE_EXECUTION_MEMBERSHIP_IDENTITY_REPAIR_SCHEDULER_ARCHITECTURE_AMENDMENT.md, historical evidence that one adaptive scheduler can own bounded multi-size/multi-member final-production work while preserving exact identities;
- workplans/archive/MLFF_REPLAY_MACE_P5_EXECUTION_RECOVERY_CONSOLIDATED_WORKPLAN.md, including serial selected-size orchestration as a now-stale structural oracle and retained recovery semantics;
- workplans/archive/MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_*.md;
- workplans/archive/MLFF_P5_TRAIN2_MEMORY_PRESSURE_BACKOFF_AND_TERMINAL_INFEASIBILITY_*.md;
- current campaign_post_selection_runtime.py;
- current training_parallel.py;
- current multi-size integration and P5 execution/recovery tests.

Archived workplans are historical/lineage evidence here, not parallel current authority. Their applicable capabilities and constraints must be reconciled into current Architecture Manual/specification before this D3 candidate becomes accepted-current.

### Capability-transfer map

This cycle replaces one mature orchestration concretization, so the following transfer is mandatory rather than implicit:

| Existing capability | Revision-2 disposition |
| --- | --- |
| collection-wide CV admission barrier before any production job | PRESERVE at _cv_admission_blockers |
| per-size second-line CV/current-method authorization before final-plan construction | PRESERVE in extracted per-size planner |
| exact per-size FinalProductionPlan/run/assessment identities | PRESERVE through existing owners |
| one effective TRAIN resource owner | PRESERVE/EXPAND ready-work population through existing AdaptiveTrainingConcurrency |
| TRAIN2/EVAL2 accelerator phase separation | PRESERVE, now across the whole production collection wave |
| per-run process cancellation, termination, reaping, disk/timeout ownership | PRESERVE at MacePostSelectionTrainer/run owner |
| authenticated sealed-root/restart reuse | PRESERVE; sealed roots never consume fresh TRAIN admission |
| deterministic queue/backoff behavior | PRESERVE with frozen-size/seed queue order and most-recent-admission demotion |
| per-size final assessment/publication and no cross-size committee | PRESERVE |
| fail-fast production finalization in frozen size order | PRESERVE after global execution; later publication stops at first failure |
| multi-size terminal lifecycle with no implicit release winner | PRESERVE |
| CV serial selected-size orchestration | PRESERVE unchanged |
| production serial selected-size TRAIN scheduling | **RETIRE/SUPERSEDE ONLY THIS CAPABILITY** with one collection-scoped TRAIN wave |

No capability may be dropped merely because its former location was inside execute_final_production(context).

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
- docs/arch_manuals/mlff_training_data/60_execution_performance.md
- docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md
- docs/specs/training_data/mlff_post_selection_p5_spec.md if final affected-surface review finds its scheduler/execution wording materially incomplete

The assembled architecture manual is derived from the canonical chapter sources; regenerate it through the repository's normal documentation build path rather than hand-maintaining a divergent duplicate.

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

#### A13 - second-line authorization remains before any launch

Use a two-size frozen design whose collection barrier initially passes. Make a later size stale/inconsistent at the exact per-size CV authorization boundary before its final plan is built. Through real train-production prove:

- the extracted planner re-runs the real CV-plan/acceptance/method guard;
- zero new trainers launch for either size;
- no new earlier-size final plan/publication becomes current merely because its own guard passed first;
- existing immutable evidence remains untouched.

Retain the historical CV-policy currentness/acceptance-ancestry regressions that established this fence.

#### A14 - production finalization stays fail-fast after global execution

Create a bounded two-size production wave where both sizes reach authenticated TRAIN2/EVAL2, but the first selected size's final-seed assessment is rejected or otherwise fails at the existing finalization owner.

Prove:

- the command fails at that first size;
- the later size gets no new final publication in that invocation;
- the later size's already-authenticated TRAIN2/measurement evidence remains reusable;
- rerun does not retrain that valid sibling evidence and may finalize it only after the earlier blocking condition is resolved/current.

#### A15 - global identity uniqueness and exact routing

For a real two-size/two-seed plan, prove four distinct scientific run/training-trajectory identities are enumerated before scheduler construction even though each size has local slots 0/1. Prove result routing returns each outcome to its owning binding and assessment position.

Add a bounded negative seam showing a duplicate global run/training identity fails before trainer launch rather than starting two workers on one run root.

#### A16 - CV non-impact

Drive the real public multi-size cross-validate path after the shared-helper refactor and prove:

- selected sizes remain outer-serial in frozen order;
- each size retains its existing internal fold/seed scheduler semantics;
- CV rejection/failure/restart behavior and canonical reduction order are unchanged;
- no cross-size CV global queue or second scheduler is introduced.

#### A17 - real resource-profile compatibility, not first-task assumption

Using two distinct production sizes/horizons through the real planner, inspect the exact values fed to the existing concurrency plan and TRAIN2 runtime. Prove that every material per-job scheduler/resource dimension is equal or already conservatively bounded by the existing common estimate contract.

The negative A10 case remains mandatory. If the positive case shows materially different demand that the existing single-profile controller cannot safely bound, the correct result is D3 reopen, not a passing test with ad-hoc maxima/minima.

### Structural acceptance

Static/source inspection must establish:

- no production outer loop calls a complete per-size execute_final_production(context) that internally creates its own scheduler;
- no second scheduler/executor/lease manager was added for size concurrency;
- only one adaptive TRAIN controller is created for one collection production TRAIN wave;
- all global production tasks are enumerated before concurrency-plan construction and duplicate run/training identities fail closed;
- the per-size second-line CV authorization fence still exists before final-plan construction and before first TRAIN launch;
- public CV still performs selected-size outer-serial orchestration and has not acquired a collection-global size queue;
- no wave-global slot/key participates in scientific content digests;
- historical architecture snapshots are unchanged.

### Affected regression

At minimum run focused suites covering multi-size target integration, the historical multi-size CV-currentness/production-barrier regressions, public multi-size CV behavior, P5 production/restart, zero-safe admission and memory backoff, replay/MACE P5 execution recovery, final-production assessment/publication, campaign lifecycle/status/advance around multi-size completion, and storage/currentness tests whose production roots/pointers are touched.

Then run complete affected MLFF campaign/training-data regression after all executable edits. If impact cannot be bounded confidently, run the repository's full available CPU test suite.

### Production qualification

**Deferred.** Functional CPU/deterministic real-owner acceptance is required now. Physical GPU throughput/VRAM qualification remains deferred to the final release package per standing project direction.

## 6. Authority/documentation/history impact

### D3 Architecture Manual

Update current target-size control-plane architecture to state that the previously accepted serial selected-size production scheduling is superseded: after the collection-wide production barrier and all per-size second-line authorization/planning complete, final-production TRAIN2 positions across selected sizes share one bounded scheduler resource allocation. Preserve per-size scientific descendant ownership, fail-fast finalization, and no cross-size reducer/publication.

Also reconcile the execution/performance chapter because it owns shared resource/concurrency architecture. The current Architecture Manual's silence on the exact production size-scheduler scope is under-specification, not evidence that the serial baseline lacked authority.

This branch carries a proposed D3 overlay only. The durable D3 correction becomes accepted-current only after implementation evidence, independent falsification/conformance review, canonical documentation reconciliation, and normal integration/merge acceptance.

### D4 specification

Update the CLI specification sentence that currently says the size dimension has serial outer iteration. It may remain true for current CV orchestration, but must no longer imply production serialization.

### D1/D2

No mutation. If implementation requires changing seed sets, horizon meaning, optimizer ordering, checkpoint acceptance, replay policy, or cross-size result reduction, stop and route the earliest upstream owner.

### Semantic history / PEM

Do not rewrite archived workplans or historical architecture snapshots.

At closeout, evaluate whether this episode materially extends an existing PEM family/pattern. Do not manufacture a new recurrence without accepted-repair chronology/evidence.

## 7. Stages and reuse

### Stage P1 - execution-bundle decomposition and authorization preservation

Refactor final-production planning/finalization so every per-size plan and position can exist before execution. Preserve the per-size second-line CV guard, enumerate all bundles before launch, add exact global identity/routing checks, and retain one-size scientific identity. Run A3, A5, A11, A13, and A15 plus focused production identity/publication tests.

### Stage P2 - collection scheduler generalization and resource compatibility

Make pending tasks self-owning; prove scheduler-profile compatibility; flatten only unsealed production positions; implement collection preflight/global task-count semantics; execute one TRAIN wave and deterministic post-TRAIN EVAL2. Run A1-A2, A6-A7, A10, A12, A17 plus existing scheduler regressions.

### Stage P3 - failure/restart/finalization closure and CV non-impact

Exercise global cancellation, demotion, sealed-root recovery, currentness/publication races, fail-fast per-size finalization, and retry. Run A8-A9, A14, A16 and affected CV/recovery/storage suites.

### Stage P4 - documentation and assembled acceptance

Reconcile Architecture Manual execution chapters and current specifications, re-derive final affected surface, run A4 plus complete affected regression, inspect capability-transfer/absence/ownership conditions, and prepare independent Review handoff.

## 8. Reopen / Challenge triggers

### D4-local blockers

Keep within D4 when implementation can satisfy this workplan by restructuring private task carriers/helpers while preserving frozen ownership and semantics.

### Evidence requiring D3 reopen

Reopen D3 if:

- selected production contexts genuinely require incompatible simultaneous resource owners that cannot safely share one adaptive controller;
- N/horizon/batch/materialization differences create materially heterogeneous RAM/VRAM/CPU demand that the existing homogeneous planner/telemetry projection cannot conservatively represent;
- safe execution would require multiple profile buckets/controllers, a changed training_parallel.py resource model, or another durable scheduler;
- collection-wide TRAIN/EVAL separation requires a second durable scheduler or materially new persisted orchestration state;
- per-size finalization cannot preserve current fail-fast semantics without changing public/architectural behavior;
- the current one-resource-domain assumption is false for an accepted campaign configuration.

### Evidence requiring D2/D1 challenge/reopen

Route upstream if concurrency/interleaving alters governed training semantics that D2 treats as execution-invariant, or if a cross-size result/seed/horizon rule becomes necessary.

### Structural complexity trigger

If implementation starts adding wrappers that retain the old per-size scheduler and synchronize a new collection scheduler around it, stop. Replace/consolidate the old boundary instead.

### Serious Challenge status

No current evidence contradicts accepted D1/D2. No Serious Challenge is active.

## 9. Final handoff

Implementation is complete only when:

- all production TRAIN2 positions across a fully admitted and second-line-authorized multi-size collection are enumerated before launch and visible to one existing adaptive scheduler wave;
- scheduler/resource ownership is singular, the shared resource-profile assumption is positively established, and process teardown/disk/timeout authority is preserved;
- local slot collisions cannot duplicate a global run and sealed/restartable work is handled without duplicate training;
- collection-wide TRAIN/EVAL phase separation survives success, backoff, failure, and interruption;
- per-size plan/assessment/publication identity is independent of scheduler order and fail-fast finalization remains frozen-size ordered;
- public CV selected-size scheduling and semantics remain unchanged despite shared-helper refactoring;
- one-size behavior remains conforming;
- current D3/D4 documentation explicitly supersedes the accepted serial-production scheduler baseline and matches the repaired execution contract;
- all required focused and affected regression is green or explicitly unavailable/blocking;
- final affected surface, evidence applicability, and PEM/history impact are reconciled;
- no physical GPU qualification is falsely claimed.

Independent Review must reconstruct the real owner chain and attempt to falsify the global-scheduler claim. A test that merely calls a new helper with four synthetic tasks cannot close the workplan if the public train-production command can still serialize selected sizes before reaching that helper.
