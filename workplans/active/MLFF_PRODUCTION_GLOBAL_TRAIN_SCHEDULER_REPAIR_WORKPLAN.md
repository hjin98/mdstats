
---
kind: implementation-workplan
workplan_id: MLFF-PRODUCTION-GLOBAL-TRAIN-SCHEDULER-REPAIR
protocol_version: 6.4.0
status: implementation-ready
created_date: 2026-09-19
reviewed_date: 2026-09-19
second_reviewed_date: 2026-09-19
closure_falsification_date: 2026-09-19
third_reviewed_date: 2026-09-19
revision: 5
workplan_review_status: pass-after-third-review-repair
reviewed_pre_repair_head: 10c68eb50cb7ee2b5f0bb8d43e35bb250a186d96
second_reviewed_pre_repair_head: 35fe7c19f60d99a2ae99257496acb2e82c35975d
closure_falsification_pre_repair_head: 47376b968a62ab05473e370746f79988436bb3e3
third_reviewed_pre_repair_head: 12959ef0bdc7a9ac9253fafa846d9f7bb4e0bb28
branch: design/mlff-production-global-train-scheduler-repair
basis_commit: f341a3f993b931c5e0838e95520b8b4fd41459ae
highest_affected_domain: D3
authority_state: stakeholder-authorized-d3-reopen-candidate
d1_d2_change: false
production_gpu_qualification: deferred-final-release
---

# MLFF production global TRAIN scheduler repair - D3 -> D4 implementation workplan

## 0. Disposition

**PASS AS IMPLEMENTATION WORKPLAN AFTER SECOND REVIEW REPAIR / FROZEN FOR D4. No Serious Challenge is active.**

Revision 5 closes the remaining recovery-normalization gap found by the third independent D3 pass. The repair remains deliberately narrow: **only actual TRAIN2 continuation/admission is collection-global**. Recovery now distinguishes roots that truly still require trainer work from already-terminal-but-unsealed roots that require only the existing completion/seal transition. The latter are sealed before scheduler sizing and never inflate TRAIN task_count, controller ceilings, progress, or resource-profile compatibility. The same rule covers current post-cutover roots and authenticated historical/legacy roots through their existing recovery owners. EVAL2, per-seed assessment, and final publication remain inside the frozen-size-ordered finalization path. FinalProductionPlan pointers remain per-binding rather than collection-atomic, and the live generation/currentness fence still prevents new old-design TRAIN2 admission after target-size rollover.

No D1/D2 defect was found. No second scheduler, collection publication transaction, new persistent orchestration machinery, or widened evaluation semantics is authorized.

This cycle is a **stakeholder-authorized bounded D3 reopen of final-production selected-size scheduling**. Accepted multi-size lineage had ultimately frozen serial outer-size orchestration as the current concretization. This workplan intentionally supersedes that one production scheduling choice only; it does not retroactively reinterpret the archived serial design as already-global, and repository presence on this branch does not make the proposed D3 mutation accepted-current before independent falsification and merge through the normal architecture acceptance path.

This cycle repairs final-production orchestration only. The defect is not that the adaptive TRAIN2 controller cannot promote concurrent work. The defect is that train-production authenticates the frozen collection as one experiment, then serializes selected sizes outside the existing scheduler and constructs a fresh scheduler for each size. The scheduler therefore sees only the seeds of the current size, not all independently ready final-production trajectories.

For a frozen two-size collection with the current one-seed production policy, the implementation presents one task at a time to a scheduler whose truthful task ceiling is one. With two configured final seeds it presents two tasks for the first size and, only after that size is completely assessed and published, another two tasks for the second size. This is structurally work-starving when the one shared CPU/GPU resource envelope could safely admit concurrent production trajectories from different selected sizes.

The repair is to make **all unsealed final-production TRAIN2 positions across the fully admitted frozen collection participate in one existing adaptive TRAIN scheduler wave**. That shared wave ends at authenticated sealed TRAIN2 roots. Only after every scheduler-owned TRAIN2 position is terminal does the command resume the existing frozen-size-ordered finalization path: per-size serial EVAL2, per-seed assessment, and binding-scoped final publication. Later sizes may finish TRAIN2 early, but they do not perform fresh EVAL2 or publish assessments merely because their training finished first.

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

### D3-2 - Planning and publication remain per-size; only the TRAIN2 queue is collection-scoped

Scientific planning remains owned per PostSelectionContext:

~~~text
selected context
  -> current accepted CV ancestry
  -> FinalProductionPlan
  -> final run plans / assessment positions
~~~

Only TRAIN2-ready positions are flattened:

~~~text
all per-size production positions
  -> collection recovery/integrity classification
  -> one TRAIN scheduler population for unsealed roots only
  -> one global TRAIN-only phase ending at sealed TRAIN2 roots
  -> frozen size N1: serial EVAL2 -> all seed assessments -> final publication
  -> frozen size N2: serial EVAL2 -> all seed assessments -> final publication
  -> ...
~~~

If finalization of N_i fails, N_{i+1} and later sizes do not begin fresh EVAL2 in that invocation. Their already-authenticated sealed TRAIN2 roots remain ordinary reusable evidence.

Flattening must not synthesize a collection-level FinalProductionPlan, run identity, assessment policy, completion record, measurement batch, or publication decision.

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

### D3-4 - One scheduler-compatible execution profile is proved over actual TRAIN-required work

Before any production TRAIN2 child is admitted, the collection execution owner must first complete the recovery normalization in D3-7/D3-8 and then prove that every position still classified **TRAIN_REQUIRED** can legally share one scheduler resource domain **under the assumptions the existing TrainingConcurrencyPlan/AdaptiveTrainingConcurrency actually make**.

Positions that are already sealed, or whose authenticated TRAIN2 continuation is already terminal and is sealed during recovery normalization without a trainer launch, do not participate in the scheduler-profile compatibility proof merely because their roots were unsealed at command entry.

The compatibility proof over TRAIN_REQUIRED positions covers, at minimum:

- effective device/backend and exact GPU telemetry domain;
- shared method/model/runtime realization and learned-model precision relevant to residency;
- canonical execution parallel-training policy and effective CPU/RAM allocation;
- loader-worker count plus any inner native-thread/nested-runtime geometry that contributes to per-job CPU demand;
- batch/model/materialization geometry when it changes host or device memory demand;
- the per-job RAM and VRAM estimate regime consumed by the existing planner;
- trainer/process-supervision ownership, timeout semantics, and the trainer-local minimum-free-disk reserve owner.

N, exact membership, seed, and H_prod do **not** have to be equal. They remain scientific identities. But the implementation must establish whether changing N or another per-position input materially changes the per-job resource demand assumed by the homogeneous planner. The current code uses one loader-worker count and one configured RAM/VRAM estimate for the whole plan, then learns promotion demand from active jobs; it is therefore forbidden to calibrate on a light TRAIN_REQUIRED position and silently assume that observation bounds a later heavier position unless the existing resource contract makes that inference valid.

The preferred current result is a single compatible profile because all current production contexts share cfg, method, trainer, device, and execution policy. That expectation is not proof. D4 must provide a bounded real-owner compatibility test over distinct selected sizes/horizons and inspect the actual scheduler inputs **after recovery normalization**.

If materially heterogeneous TRAIN_REQUIRED demand cannot be bounded safely by the existing single-controller contract without changing training_parallel.py, inventing per-profile buckets, or running multiple resource schedulers, **reopen D3**. Do not silently choose the first task's values, take ad-hoc minima/maxima, or broaden the controller inside this workplan.

The minimum-free-disk reserve remains enforced by MacePostSelectionTrainer per owned child. Do not add a disk scheduler. A disk/timeout failure retains the existing whole-wave terminal failure/cancel/reap semantics.

This validation is execution-local. Do not persist a new resource-profile authority.

### D3-5 - TRAIN/EVAL phase separation is collection-wide; EVAL finalization remains per-size

No fresh EVAL2 work may begin while **any** production TRAIN2 task in the collection wave remains active, queued, demoting, cancelling, or not yet terminal.

The collection scheduler owns TRAIN2 only and returns after every required unsealed position has reached the existing authenticated sealed-root boundary. It MUST NOT run EVAL2 as part of the global scheduler wave.

After successful global TRAIN2, finalization resumes in frozen selected-size order. For one size, EVAL2 traverses that FinalProductionPlan.required_final_seeds order, regardless of whether a root was already sealed at invocation start or became sealed in the global wave. The existing run owner re-authenticates each sealed root before numerical evaluation.

EVAL2 remains serial unless separately redesigned later. Runtime TRAIN completion order, prior-sealed versus newly-trained classification, or global scheduler slot must not determine EVAL2/assessment/publication order.

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

### D3-7 - Normalize terminal training state before scheduler sizing

Before the global concurrency plan is built, classify every production position under the existing run-root/recovery owners while holding the existing run-activity exclusion whenever the root is inspected or mutated.

A position is scheduler work only if authenticated recovery proves that its TRAIN2 trajectory still requires additional trainer execution. Use the execution-local classification **TRAIN_REQUIRED** only for queue construction; do not persist a new state enum or recovery registry.

A position that already has authenticated terminal TRAIN2 but lacks the current completion/seal proof is **not** TRAIN_REQUIRED. Complete the accepted owner-local seal transition before scheduler sizing:

- for a post-cutover root, reuse/factor the existing terminal-continuation path that validates the exact materialization, runtime plan, runtime summary, optimizer/RNG/checkpoint ancestry and then calls the existing training-completion/topology owner;
- for a historical/legacy root, reuse/factor `_authenticate_legacy_training_state(...)`, `_authenticate_post_selection_continuation(...)`, the existing continuation-execution-evidence check, and the accepted append-only historical completion path;
- launch no trainer for either case;
- for a historical root, rewrite/copy/rename/symlink no pre-existing byte; only the already-authorized append-only topology/completion proof may be added;
- publish no EVAL2 result, assessment pointer, final publication, or new currentness authority during this normalization. Existing idempotent content-addressed compatibility evidence may be stored only through its already-accepted historical-reuse owner.

Once sealed, authenticate the root through `_authenticate_sealed_training_root(...)` (which delegates to `_authenticate_legacy_sealed_training_root(...)` for historical roots) or a conforming factored successor. A sealed root:

- does not enter TRAIN task_count;
- does not launch a trainer;
- does not consume maximum_jobs;
- remains eligible for later per-size EVAL2/reassessment through the existing run path.

A corrupt, foreign, incompatible, or contradictory partial-proof state fails before sibling TRAIN launch.

Thus task_count means **positions that still require real TRAIN2 continuation/trainer ownership after recovery normalization**, not merely roots that happened to be unsealed when the command began.

If normalization leaves zero TRAIN_REQUIRED positions, construct no adaptive TRAIN scheduler merely to report zero work; after the required currentness fence, proceed directly to frozen-size-ordered finalization.

### D3-8 - Recovery/integrity normalization is collection-wide before admission baseline

Before the authoritative GPU admission baseline and before any new child is admitted, every production position must resolve to one of these execution-local outcomes:

1. **post-cutover fresh root, no durable continuation** -> TRAIN_REQUIRED;
2. **post-cutover authenticated incomplete continuation** -> TRAIN_REQUIRED, preserving its exact restart ancestry;
3. **post-cutover authenticated terminal continuation, not yet sealed** -> publish only the existing training completion/topology proof, authenticate the resulting sealed root, then exclude it from TRAIN_REQUIRED;
4. **post-cutover sealed root** -> authenticate read-only, then exclude it from TRAIN_REQUIRED;
5. **historical/legacy interrupted root** -> prove the existing exact historical-equivalence/runtime/continuation contract; if incomplete, TRAIN_REQUIRED continuation under the historical runtime identity;
6. **historical/legacy terminal-but-unsealed root** -> prove the same historical contract, append only the already-authorized seal, authenticate the resulting sealed root, then exclude it from TRAIN_REQUIRED;
7. **historical/legacy sealed root** -> authenticate through the existing historical sealed-root owner and exclude it from TRAIN_REQUIRED;
8. **foreign/corrupt/incompatible/ambiguous partial state** -> typed failure before any sibling TRAIN launch.

Do not use `_prepare_post_selection_run(...)` as a generic legacy validator: current and historical roots have distinct accepted recovery owners. Factor shared read-only classification only where doing so preserves those semantics exactly.

Recovery normalization can realize training-side state and may affect CUDA occupancy. Therefore all applicable normalization finishes before the authoritative post-normalization GPU sample used by `build_training_concurrency_plan()`.

Any append-only seal created during normalization is an accepted recovery completion, not a scheduler completion and not scientific assessment. It remains durable even if a later sibling fails preflight; do not roll it back.

Do not preflight lazily after other sizes have started. Do not turn recovery normalization into EVAL2.

### D3-9 - Collection-wide production barrier remains stronger than scheduler readiness

_cv_admission_blockers(contexts) remains ahead of all production planning/execution that could start new training. If one selected size lacks current accepted CV ancestry, the command launches zero production trainers for every size.

The globalization repair must not turn the barrier into per-task filtering.

### D3-10 - Per-size EVAL2/assessment/publication remains authoritative and ordered

After the global TRAIN-only wave succeeds, each selected context is finalized independently in frozen collection order using its current FinalProductionPlan, positions, sealed roots, and evidence.

For each size:

- EVAL2 visits required final seeds in FinalProductionPlan.required_final_seeds order;
- every required final seed is assessed before that size's aggregate production verdict is decided;
- measurements/candidate records are durably published through the existing owner before the corresponding assessment, exactly as today;
- typed no-admissible outcomes remain durable;
- if any required seed has no admissible representative, the size receives no final publication and the invocation fails after preserving the complete per-seed assessment set for that size;
- no sibling size's evidence can satisfy or alter local completion;
- final publication uses the existing per-binding owner and separately re-authenticates current production authorization.

If one size fails EVAL2, assessment, currentness, or final publication, later selected sizes do not begin fresh EVAL2/finalization in that invocation. Their already-sealed TRAIN2 roots remain reusable. Cross-size scheduler arrival order is never observable in scientific reduction or publication semantics.

### D3-11 - Campaign-level progress tells the truth

The public TRAIN scheduler line for final production must describe the global **TRAIN_REQUIRED** wave after recovery normalization:

- progress = newly scheduler-completed TRAIN roots / positions that actually required TRAIN2 continuation at scheduler construction;
- active/queued/failed counts are global to that TRAIN_REQUIRED wave;
- already-sealed and terminal-but-unsealed roots normalized to sealed state are reported through bounded reuse/recovery diagnostics, not counted as TRAIN jobs;
- plan ceiling is computed from the TRAIN_REQUIRED task count and shared resource profile.

Per-child TRAIN heartbeats retain their own N_selected, seed/run, and phase context.

For two selected sizes with one required production seed each, a fresh run must initially expose two scheduler positions, not an isolated 0/1 wave followed by a second unrelated 0/1 wave.

Stage-level campaign status remains one post_selection_final_production stage over the complete requested collection.

### D3-12 - Preserve both production authorization fences and per-binding pointer semantics

The collection-wide _cv_admission_blockers(contexts) barrier remains the first production admission fence, but it is not the only one.

Before a per-size FinalProductionPlan is constructed, the per-size production planner must re-run the existing exact authorization relation:

- resolve_current_cv_plan(context);
- resolve_current_cv_acceptance(context);
- require_cv_acceptance_for_method(...) against the current method and selected binding.

This is the accepted second-line race/currentness fence formerly inside execute_final_production(context). Splitting planning from execution MUST NOT delete, weaken, or replace it with the earlier collection preflight.

The collection owner uses a two-phase pre-launch planning discipline:

**Phase A - construct/authenticate without current-pointer side effects.** For every selected size in frozen order, re-run the second-line CV authorization and construct/validate its FinalProductionPlan, run plans, assessment positions, task descriptors, reuse offers, and execution profile in memory (plus immutable content-addressed objects only where the existing owner can publish them without making them current). Phase A must succeed for the whole collection before any new trainer launches.

**Phase B - publish through existing per-binding owners.** After all Phase-A bundles pass, publish each binding-scoped FinalProductionPlan/run-plan object and current plan pointer through the existing publication barrier/currentness owner. No collection-wide pointer transaction, rollback protocol, or shadow planned-collection authority is introduced.

If Phase A fails for any size, launch zero trainers and do not make a new sibling FinalProductionPlan pointer current as part of this invocation. If a concurrent currentness race is detected during Phase B after earlier valid per-binding pointers were already committed, stop before TRAIN2; those earlier pointers remain subject to their own normal currentness and are not rolled back merely to simulate collection atomicity.

Commit-time selected-binding/generation fences remain authoritative again when assessments and final publications are made current.

### D3-13 - Global TRAIN2 may run ahead; EVAL2/finalization remains fail-fast in frozen size order

Globalizing TRAIN2 means a later selected size may already have an authenticated sealed TRAIN2 root before an earlier size's EVAL2/assessment is decided. That execution overlap authorizes no later evaluation or publication.

After the successful collection TRAIN-only wave:

1. finalize selected sizes in frozen collection order;
2. for the current size, perform serial EVAL2 for every required final seed in required-seed order;
3. publish that size's measurements and complete per-seed assessment set through the existing owners;
4. if any required seed is a typed no-admissible outcome, or EVAL2/currentness/publication otherwise fails, abort before beginning fresh EVAL2 for later sizes;
5. only a fully accepted size may publish its existing binding-scoped final-production decision;
6. preserve already-authenticated sibling TRAIN2 roots and any measurement evidence that was already durable before the failure for ordinary reuse on rerun.

This preserves the current policy that all required seeds of one size are assessed before that size fails for a no-admissible member; it does **not** turn the first rejected seed into an intra-size early stop. The repair increases TRAIN2 overlap only and does not invent a campaign-level production reducer.

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

### D3-15 - Enumerate exact global production identity before scheduler construction without eagerly materializing fresh training

All per-size final plans, required run plans, assessment positions, and production position **descriptors** must be constructed/enumerated and authority-validated before recovery normalization. Only descriptors that remain TRAIN_REQUIRED after D3-7/D3-8 become scheduler tasks and participate in concurrency-plan construction.

Enumerated here does **not** mean eagerly creating a fresh PostSelectionMaterialization, fitting a fresh PostSelectionFittedPreparation, opening a model/provider, or launching MACE. Fresh preparation/materialization remains owned by execute_post_selection_run(...) after scheduler admission, exactly as in the current run lifecycle. The pre-launch recovery pass may inspect/authenticate only durable state that already exists.

Local seed slots are not globally unique. The collection execution owner must assign an execution-only wave key and prove before launch that no two tasks resolve to the same run_plan.run_identity or training-trajectory identity. A duplicate means a planning/identity defect and fails closed; the scheduler must never concurrently launch the same logical run twice.

Results/state route back through the owning binding/context plus local position (or an equivalent exact owner key). The wave key cannot enter a scientific digest, run-root identity, assessment position, or publication record.

### D3-16 - Revalidate frozen-design currentness before every later TRAIN admission

The global queue lengthens the interval between initial planning and later task admission. The accepted multi-size contract already requires that once a generation/design becomes stale, no further outer-size work is newly admitted for that retired design. Serial selected-size execution satisfied this naturally because later sizes crossed a fresh owner/currentness boundary. A collection queue must restore that property explicitly.

Before the **first** TRAIN2 launch, and again immediately before every subsequent dequeue/submit that would admit a previously unstarted production task, the scheduler owner must re-read the compact current target-size CampaignStore state and verify that the invocation's expected frozen bindings are still current. Reuse the existing target-size currentness projection (`current_target_size_bindings(state)` over the current target-size revision), or a factored helper with exactly that semantics. Do not reconstruct a second currentness rule and do not call the expensive full scientific-context builder merely as a polling mechanism.

If the generation or expected binding membership is no longer current:

- admit no further queued TRAIN2 tasks for the retired design;
- do not begin EVAL2 or publish new assessments/final products for that invocation;
- let already-admitted workers settle through the existing owned-worker failure/teardown policy without treating stale authority as a scientific rejection;
- preserve any authenticated terminal TRAIN2 evidence as historical/restart evidence subject to normal later currentness;
- fail the invocation with the existing stale/currentness error family.

Revalidate the same compact currentness condition once more after the global TRAIN wave reaches terminality and before the first per-size EVAL2 begins. This closes the case where rollover occurs after the last task was admitted, when no later dequeue exists to observe the change.

This is a transient admission fence, not a new campaign lease. Do not add a long-held global lock that prevents legitimate `prepare`/generation rollover merely to make the scheduler easier to reason about.

### Delegated D4 space

Implementation may choose internal helper names, dataclass names, mapping shape, and whether planning/finalization are extracted from execute_final_production into private helpers. The required architecture is behavioral and ownership-based.

A preferred minimal reduction is:

~~~text
Phase A: construct/authenticate every per-size production bundle in memory
  -> validate unique global task identities + compatible execution profile
Phase B: publish existing per-binding final-plan/run-plan authorities
  -> collection recovery/integrity preflight
       sealed roots: read-only sealed-root authentication
       resumable roots: existing continuation preflight
       fresh roots: no eager materialization
  -> one generalized existing scheduler TRAINs only unsealed positions to seal
  -> frozen-size loop:
       serial EVAL2 in required seed order
       publish measurements/assessments
       publish or fail that size
~~~

The implementer may re-shape _PendingPostSelectionRun, _preflight_post_selection_pending_runs, _execute_post_selection_pending_runs, and _run_post_selection_positions so each task owns its context/policy instead of receiving one function-global context.

### Simplification target

Remove the final-production outer serialization in execute_current_train_production as the owner of resource scheduling.

Do **not** compensate by adding another executor, queue, scheduler, lease registry, or retry wrapper. Rewire the existing scheduler boundary so it receives all authorized ready production work.

## 3. Material implementation obligations

### O1 - Extract two-phase planning from execution without duplicating production authority

Refactor execute_final_production as needed so the command can construct and authenticate every per-size plan/run position before launching the collection TRAIN wave.

Planning must continue using the exact current owners for CV reauthentication, replay resolution/lineage, common monitor/separation, final-plan construction/validation, final training budget policy, assessment policy digest, reuse offers, run-plan construction, evidence-store publication, and final-plan current-pointer publication.

The extracted per-size planner must preserve the accepted second-line CV authorization guard immediately before final-plan construction. Build/authorize **all** per-size bundles in Phase A before any current-plan publication or collection TRAIN scheduling. Only after Phase A succeeds may Phase B publish the existing binding-scoped plan/run objects and pointers.

A Phase-B commit-time stale-binding failure stops before TRAIN2 but does not roll back an earlier sibling's independently valid pointer. Do not introduce collection-atomic pointer machinery to erase a legitimate per-binding commit.

Do not copy these calculations into a second collection-specific planner and do not perform fresh training materialization merely to enumerate the collection.

Acceptance: changing only execution width or cross-size queue order produces byte-identical scientific run/position identities to serial execution for the same accepted inputs.

### O2 - Generalize the existing pending-run execution boundary as TRAIN-only

The scheduler path currently accepts one context and one budget_policy; that is insufficient for collection work. Rewire it so TRAIN2 execution calls execute_post_selection_run(..., stop_after_training=True) with the owning task's context/policy and returns only after the owned task reaches the sealed terminal TRAIN2 boundary.

Move/retain EVAL2 outside the global scheduler helper. The generalized scheduler must not return PostSelectionRunResult as the product of the collection TRAIN wave merely by running EVAL2 internally.

All scheduler state maps must key by a wave-global unique slot/key. A local seed index such as slot=0 is not globally unique across sizes and MUST NOT be used directly once positions are flattened.

The global slot/key is execution-only and MUST NOT be hashed into run plans, assessment positions, evidence, or publication.

### O3 - Preserve deterministic resource backoff

Insertion order of active tasks currently defines the deterministic most-recently-admitted backoff victim. Preserve deterministic behavior after globalization.

Fresh queue order is frozen selected-size order, then FinalProductionPlan.required_final_seeds order.

A demoted task returns to the existing restartable queue with its original scientific owner and wave identity. Do not substitute smallest/largest N or seed ranking as backoff policy.

### O4 - Preserve exact restart/reuse semantics

Globalization must work when the initial collection contains any mix of no prior roots, sealed TRAIN2 roots awaiting EVAL2, complete current assessments, stale historical assessment offers, interrupted resumable TRAIN2 roots, terminal-but-unsealed post-cutover roots, terminal-but-unsealed historical roots, historical interrupted continuations, and positions requiring fresh training.

Before scheduling, all of those states pass the D3-7/D3-8 normalization. A retry schedules only positions that still require actual trainer continuation. Terminal-but-unsealed roots are completed/sealed through existing recovery owners with zero trainer launch and disappear from task_count. After the collection TRAIN wave, per-size finalization reuses authenticated sealed roots and any exact reusable measurements through existing owners. Completed sibling TRAIN2 work cannot be invalidated merely because another selected size previously failed.

### O5 - Preserve publication barriers/currentness without inventing collection atomicity

Every existing publication remains under its binding/campaign-generation barrier and current-pointer/currentness checks. A collection scheduler result is not authority to publish if the owning context became stale before finalization.

No collection-level publication transaction is introduced for plans, assessments, or final products. Phase-B FinalProductionPlan pointer commits remain independently binding-scoped. If one pointer commit or a later per-size finalization fails its currentness/publication check, preserve already committed valid sibling pointers/evidence, stop before the next unauthorized phase as specified above, and report the real failure. Do not roll back immutable objects or current pointers merely to manufacture collection atomicity that the accepted architecture does not define.

### O6 - Preserve single-size behavior

For one selected size, the generalized path must remain behaviorally equivalent to the current production path: same plans/identities, task population, adaptive-controller semantics, TRAIN/EVAL separation, assessment/publication, and failure/restart semantics.

The repair must not special-case multi-size by maintaining two independent production implementations.

### O7 - Do not promote seed policy into scheduler policy

The current generated production default is seeds=[1]. This workplan does not change it.

The scheduler receives the sum, across selected sizes, of required final seeds whose current TRAIN2 roots are unsealed.

Thus two selected sizes with one seed each naturally provide two independent TRAIN2 positions. If the user configures two final seeds per size, four scientific positions exist; that count comes from the existing production policy, not scheduler invention.

### O7A - Preserve stale-generation admission semantics during the global wave

Factor or reuse the smallest existing binding-currentness owner needed for a cheap scheduler admission check. At minimum it must compare the invocation's expected frozen binding digests/generation against the current target-size CampaignStore revision through the canonical `current_target_size_bindings` projection.

Perform this check before first launch, before each later queued-task admission, and after TRAIN terminality before EVAL2. A stale result blocks new admission and later finalization; it is not a reason to introduce a campaign-wide mutex, cancel/rollback valid immutable history, or mutate the target-size state.

### O8 - Reconcile specification/documentation without rewriting history

Update current documentation so it no longer says final-production outer iteration over sizes is necessarily serial.

Current architecture/specification must distinguish:

- CV: unchanged current orchestration;
- production: collection-wide barrier followed by one bounded collection TRAIN wave, then per-size evaluation/assessment/publication.

Do not edit historical snapshots to make history look different. The archived predecessor workplan remains historical evidence that serial production was once an accepted concretization and that bounded overlap through the existing scheduler was already permitted.

### O9 - Keep training_parallel.py stable unless separately falsified

The present production defect is upstream of the adaptive controller's task population. Do not alter promotion thresholds, monotone backoff, stabilization windows, GPU budget formulas, or requested/min/max concurrency merely to make the multi-size test pass.

If generalization exposes a genuine controller defect independent of task scoping or proves heterogeneous cross-size resource demand cannot be represented by its existing single-profile contract, stop and reopen D3 with evidence rather than bundling an unrelated scheduler-policy change.

### O10 - Preserve public EVAL2/finalization failure behavior

The global TRAIN-only wave may produce reusable sealed TRAIN2 roots for later siblings, but EVAL2/assessment/publication still commits in frozen selected-size order and remains fail-fast. A failed N_i must prevent fresh EVAL2 and new final publication of N_j for j > i in that invocation. Do not eagerly evaluate later siblings merely because their TRAIN2 roots are ready, and do not turn any already-durable sibling measurements into implicit permission to complete/publicly succeed the remaining subset.

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
| authenticated sealed-root/restart reuse | PRESERVE; sealed roots authenticate before sibling TRAIN admission, terminal-but-unsealed current/legacy roots normalize to sealed state with zero trainer launch, and only genuinely incomplete trajectories consume TRAIN capacity |
| deterministic queue/backoff behavior | PRESERVE with frozen-size/seed queue order and most-recent-admission demotion |
| per-size serial EVAL2, final assessment/publication and no cross-size committee | PRESERVE after the global TRAIN-only wave |
| fail-fast production finalization in frozen size order | PRESERVE; later sizes do not begin fresh EVAL2/publication after earlier-size failure |
| stale-generation/retired-design admission stop | PRESERVE explicitly at global-queue admission and again before EVAL2 using existing CampaignStore binding currentness |
| multi-size terminal lifecycle with no implicit release winner | PRESERVE |
| CV serial selected-size orchestration | PRESERVE unchanged |
| production serial selected-size TRAIN scheduling | **RETIRE/SUPERSEDE ONLY THIS CAPABILITY** with one collection-scoped TRAIN wave |

No capability may be dropped merely because its former location was inside execute_final_production(context).

### Evidence applicability

Existing tests for per-size scientific identity, CV barrier semantics, TRAIN2 cancellation/teardown, memory backoff, and restart remain relevant but are insufficient to prove the new collection scheduler scope.

Any old test whose oracle specifically requires serial **production TRAIN2** size iteration becomes stale by intended D3 change and must be split/replaced with an oracle for the stronger work-conserving TRAIN ownership contract, not simply deleted. In particular, tests/test_mlff_target_size_multi_selection.py::test_outer_size_execution_is_serial_and_adds_no_scheduler currently conflates CV and production: retain its CV outer-serial/resource-ownership protection while replacing only the production-TRAIN serialization assertion. Per-size production EVAL2/finalization remains serial and ordered.

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

#### A6 - complete recovery/integrity normalization before launch

Through the real collection owner while another size has runnable fresh TRAIN2 work, cover at least:

1. a foreign/corrupt durable post-cutover unsealed continuation;
2. a corrupt/foreign/incompatible post-cutover sealed root;
3. an incompatible historical/legacy interrupted continuation;
4. a corrupt/contradictory historical sealed or partial-proof root.

In every failing case assert zero new sibling trainer launches, no EVAL2 begins, and the authoritative GPU admission baseline/controller is not used to admit work after the failure.

#### A7 - terminal-but-unsealed normalization, mixed restart, and canonical EVAL order

Construct a real production collection containing:

- one valid already-sealed root;
- one post-cutover root with authenticated terminal TRAIN2 summary but no completion seal;
- one authenticated historical/legacy terminal-but-unsealed root;
- one genuinely incomplete/fresh position that still requires TRAIN2.

Prove:

- both terminal-but-unsealed roots are completed/sealed through their existing recovery owners with **zero trainer launch**;
- the historical root receives only the accepted append-only seal and no pre-existing byte changes;
- the already-sealed and newly normalized roots do not enter scheduler task_count or resource-profile compatibility;
- only the genuinely TRAIN_REQUIRED position enters the adaptive scheduler;
- if every position is sealed/terminal after normalization, no adaptive scheduler is constructed at all;
- the global scheduler itself performs no EVAL2;
- finalization later visits sizes in frozen order and required seeds in `required_final_seeds` order regardless of whether a root was initially sealed, normalized-to-sealed, or trained in the wave;
- valid sealed roots never relaunch a trainer.

#### A8 - failure/cancellation/restart

Inject a real-owner TRAIN2 child failure after at least two cross-size tasks have been admitted. Assert no further admission, all active owned tasks are signalled/reaped, no EVAL2 starts, no orphan child remains, authenticated completed TRAIN2 state survives, and the next invocation schedules only outstanding work.

#### A9 - memory demotion identity

Force deterministic resource backoff while tasks from different sizes are active. Prove the most-recently-admitted task is the victim, execution owner returns cancellation verdict, task is requeued with unchanged scientific identity, and completed work is not duplicated.

#### A10 - incompatible shared resource profile

Construct two **TRAIN_REQUIRED** contexts differing in a scheduler-critical execution/resource value through a bounded test seam. Assert fail-closed behavior before any new trainer launches and an error identifying the incompatible dimension. Also prove that an incompatible profile attached only to a position normalized to sealed state does not spuriously block the scheduler, because that position never shares the TRAIN resource domain.

#### A11 - single-size regression

Run current one-size production acceptance/restart tests through the generalized path. No alternate implementation branch may remain.

#### A12 - truthful progress

For a fresh two-size/one-seed campaign, capture real scheduler output and prove planned/running lines report a two-job global wave. Child progress must still expose correct N_selected and seed/run context.

#### A13 - second-line authorization and per-binding plan-publication semantics

Use a two-size frozen design whose collection barrier initially passes.

**Phase-A case:** make the later size stale/inconsistent at the exact per-size CV authorization boundary before any plan pointer publication. Through real train-production prove:

- the extracted planner re-runs the real CV-plan/acceptance/method guard for every size;
- Phase A fails before any new FinalProductionPlan pointer is made current for this invocation;
- zero new trainers launch;
- existing immutable evidence remains untouched.

**Phase-B race case:** after all Phase-A bundles validate, inject a currentness/generation race while sequential binding-scoped FinalProductionPlan pointers are being committed. Prove:

- the failing pointer publication aborts before TRAIN2;
- any earlier sibling plan pointer that validly committed remains governed by its own per-binding currentness and is not rolled back;
- no collection-level pointer transaction/rollback machinery is introduced.

Retain the historical CV-policy currentness/acceptance-ancestry regressions that established the second-line fence.

#### A14 - production EVAL2/finalization stays fail-fast after global TRAIN2

Create a bounded two-size production wave where both sizes reach authenticated sealed TRAIN2 roots, but the first selected size's finalization yields at least one typed no-admissible seed outcome (or fails at the existing EVAL2/currentness/publication owner).

Prove:

- all required seeds of the first size are evaluated/assessed according to the existing per-size policy before a no-admissible member causes that size to fail;
- the command fails at that first size and creates no final publication for it;
- the later size begins no fresh EVAL2 and gets no new assessment/final publication in that invocation;
- the later size's authenticated sealed TRAIN2 roots, plus any sibling measurement evidence that was already durable before the failure, remain reusable;
- rerun does not retrain those valid sibling roots and may evaluate/finalize them only after earlier blocking conditions permit the command to reach them.

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

Using two distinct production sizes/horizons that remain TRAIN_REQUIRED after recovery normalization, inspect the exact values fed to the existing concurrency plan and TRAIN2 runtime. Prove that every material per-job scheduler/resource dimension is equal or already conservatively bounded by the existing common estimate contract.

The negative A10 case remains mandatory. If the positive case shows materially different demand among actual TRAIN_REQUIRED positions that the existing single-profile controller cannot safely bound, the correct result is D3 reopen, not a passing test with ad-hoc maxima/minima.

#### A18 - global scheduler stops at the sealed TRAIN2 boundary

Through the real production owner, instrument the existing run seam and prove that the collection-wide scheduler invokes tasks with TRAIN-only semantics and returns after all unsealed roots are authenticated terminal/sealed. No EVAL2 provider, candidate assessment, measurement publication, or final-seed assessment is entered from inside that global scheduler wave.

Then prove those same roots are consumed by the subsequent per-size finalizer through the existing run/EVAL owners. This is the structural/behavioral guard against accidentally globalizing EVAL2 while repairing TRAIN2 admission.

#### A19 - generation rollover stops new global-queue admission

Start a bounded multi-size production wave with enough tasks that at least one task is active and at least one later task remains queued. After the first task is admitted, atomically roll the target-size campaign to a new prepared generation through the real current-state owner.

Prove:

- before the scheduler admits the next queued task, it re-reads current target-size state through the canonical binding projection and detects the retired design;
- no queued old-generation task is newly launched after detection;
- already-admitted owned workers are settled/reaped through existing ownership semantics and any terminal evidence remains non-current historical evidence;
- no EVAL2, assessment pointer, or final publication from the stale invocation is made current;
- the invocation fails with typed stale/currentness semantics, not a scientific rejection;
- no global campaign lock, scheduler-currentness registry, or rollback state is introduced.

Also cover rollover after the last TRAIN2 task has already been admitted but before global TRAIN terminality: the mandatory pre-EVAL currentness recheck must reject before any EVAL2 begins.

### Structural acceptance

Static/source inspection must establish:

- no production outer loop calls a complete per-size execute_final_production(context) that internally creates its own scheduler;
- no second scheduler/executor/lease manager was added for size concurrency;
- only one adaptive TRAIN controller is created for one collection production TRAIN wave;
- all global production position descriptors are enumerated without eagerly creating fresh training materialization, duplicate run/training identities fail closed, and only post-normalization TRAIN_REQUIRED descriptors reach concurrency-plan construction;
- every sealed production root is authenticated and every durable unsealed current/legacy continuation is normalized before the authoritative TRAIN admission baseline;
- authenticated terminal-but-unsealed current/legacy roots are sealed through existing owners with zero trainer launch and excluded from task_count/profile compatibility;
- scheduler admission reuses the canonical CampaignStore target-binding currentness projection before first launch and every later queued-task launch, with a final recheck before EVAL2;
- the global production scheduler ends at sealed TRAIN2 and contains no EVAL2/final-assessment loop;
- the per-size second-line CV authorization fence still exists before final-plan construction and before first TRAIN launch;
- no collection-level plan-pointer transaction/rollback authority was added;
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

### Stage P1 - two-phase execution-bundle decomposition and authorization preservation

Refactor final-production planning so Phase A constructs/authenticates every per-size plan/task descriptor without current-plan pointer side effects or fresh training materialization; validate global identities/profile; then Phase B publishes through existing per-binding owners. Preserve the second-line CV guard and one-size scientific identity. Run A3, A5, A11, A13, and A15 plus focused production identity/publication tests.

### Stage P2 - collection recovery + TRAIN-only scheduler generalization

Make pending tasks self-owning; perform collection-wide current/legacy recovery normalization; seal authenticated terminal-but-unsealed roots without trainer launch; derive TRAIN_REQUIRED positions; prove scheduler-profile compatibility over that reduced set; implement global task-count semantics plus the canonical binding-currentness admission fence; execute one TRAIN-only wave that ends at sealed roots. Run A1-A2, A6-A7, A10, A12, A17-A19 plus existing scheduler/currentness/historical-recovery regressions.

### Stage P3 - per-size EVAL/failure/restart closure and CV non-impact

Exercise global TRAIN cancellation/demotion, sealed-root recovery, canonical mixed-root EVAL order, currentness/publication races, fail-fast per-size EVAL/assessment/publication, and retry. Run A8-A9, A14, A16 and affected CV/recovery/storage suites.

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
- collection-wide TRAIN-only scheduling cannot hand off cleanly to the existing sealed-root/EVAL owners without a second durable scheduler or materially new persisted orchestration state;
- recovery normalization cannot distinguish terminal-but-unsealed from genuinely incomplete current/legacy trajectories without duplicating or weakening the existing recovery owner;
- sealing authenticated terminal-but-unsealed state before scheduler sizing would require a new persistent recovery authority rather than factoring the existing completion/topology owner;
- preserving stale-generation admission semantics would require a new persistent currentness registry or long-held campaign lock rather than a bounded read of existing CampaignStore authority;
- per-size EVAL2/finalization cannot preserve current fail-fast semantics without changing public/architectural behavior;
- the current one-resource-domain assumption is false for an accepted campaign configuration.

### Evidence requiring D2/D1 challenge/reopen

Route upstream if concurrency/interleaving alters governed training semantics that D2 treats as execution-invariant, or if a cross-size result/seed/horizon rule becomes necessary.

### Structural complexity trigger

If implementation starts adding wrappers that retain the old per-size scheduler and synchronize a new collection scheduler around it, stop. Replace/consolidate the old boundary instead.

### Serious Challenge status

No current evidence contradicts accepted D1/D2. No Serious Challenge is active.

## 9. Final handoff

Implementation is complete only when:

- all production position descriptors across a fully admitted and second-line-authorized multi-size collection are enumerated without eager fresh materialization, then recovery normalization excludes all already-terminal work before scheduler construction;
- scheduler/resource ownership is singular, the shared resource-profile assumption is positively established over actual TRAIN_REQUIRED positions, and process teardown/disk/timeout authority is preserved;
- every existing sealed root and every current/legacy continuation is authenticated before sibling TRAIN admission; terminal-but-unsealed roots seal with zero trainer launch; local slot collisions cannot duplicate a global run;
- no queued task is newly admitted after the invocation's frozen bindings cease to be current, and currentness is rechecked again before EVAL2;
- the collection scheduler stops at authenticated sealed TRAIN2 roots, and no EVAL2 begins until the entire global TRAIN wave is terminal;
- per-size EVAL2/assessment/publication then remains frozen-size/seed ordered and fail-fast, independent of scheduler order;
- public CV selected-size scheduling and semantics remain unchanged despite shared-helper refactoring;
- one-size behavior remains conforming;
- current D3/D4 documentation explicitly supersedes the accepted serial-production scheduler baseline and matches the repaired execution contract;
- all required focused and affected regression is green or explicitly unavailable/blocking;
- final affected surface, evidence applicability, and PEM/history impact are reconciled;
- no physical GPU qualification is falsely claimed.

Independent Review must reconstruct the real owner chain and attempt to falsify the global-scheduler claim. A test that merely calls a new helper with four synthetic tasks cannot close the workplan if the public train-production command can still serialize selected sizes before reaching that helper.
