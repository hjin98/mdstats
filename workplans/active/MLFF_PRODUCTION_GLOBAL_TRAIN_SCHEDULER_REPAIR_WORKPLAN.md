
---
kind: implementation-workplan
workplan_id: MLFF-PRODUCTION-GLOBAL-TRAIN-SCHEDULER-REPAIR
protocol_version: 6.4.0
status: implementation-reopened
created_date: 2026-09-19
reviewed_date: 2026-09-19
second_reviewed_date: 2026-09-19
closure_falsification_date: 2026-09-19
third_reviewed_date: 2026-09-19
third_review_closure_date: 2026-09-19
fourth_reviewed_date: 2026-09-19
fourth_review_closure_date: 2026-09-19
revision: 8
workplan_review_status: pass-after-fourth-review-consistency-closure
implementation_review_status: no-pass-d4-reopened
implementation_reviewed_head: f7d4925e08fe3e013b4a35a71a29d6fed8c8c2be
implementation_review_date: 2026-09-20
d4_repair_head: 0462f56f6bfb22ea254a28683a62937b6aad2740
d4_repair_evidence_date: 2026-09-20
reviewed_pre_repair_head: 10c68eb50cb7ee2b5f0bb8d43e35bb250a186d96
second_reviewed_pre_repair_head: 35fe7c19f60d99a2ae99257496acb2e82c35975d
closure_falsification_pre_repair_head: 47376b968a62ab05473e370746f79988436bb3e3
third_reviewed_pre_repair_head: 12959ef0bdc7a9ac9253fafa846d9f7bb4e0bb28
third_review_closure_pre_repair_head: a8dcbaa774ac4815ce03896e368a630577d20c51
fourth_review_pre_repair_head: e2b9c6221ba379ef78f8ddbfba0aff3ae814b181
fourth_review_closure_pre_repair_head: d7efcf62c8cc5b29cbd021f9f74cb13fff3f921e
branch: design/mlff-production-global-train-scheduler-repair
basis_commit: f341a3f993b931c5e0838e95520b8b4fd41459ae
highest_affected_domain: D3
authority_state: stakeholder-authorized-d3-reopen-candidate
d1_d2_change: false
production_gpu_qualification: deferred-final-release
---

# MLFF production global TRAIN scheduler repair - D3 -> D4 implementation workplan

## 0. Disposition

**PASS AS IMPLEMENTATION WORKPLAN AFTER FOURTH REVIEW CONSISTENCY CLOSURE / FROZEN FOR D4. No Serious Challenge is active.**

Revision 8 is the fourth-review consistency closure. Revision 7 closed the currentness-linearization and preflight-side-effect gaps; Revision 8 removes the last weaker derivative wording so the D4 obligation/capability-transfer sections require the same exact serialized collection-signature admission semantics as D3-16. Revision 6's recovery-normalization contract remains intact: only actual TRAIN_REQUIRED work enters the scheduler, and public CV selected-size/task-count/progress semantics remain unchanged. Revision 7 additionally requires a real linearization point between each new production admission and concurrent target-generation transitions, and explicitly preserves independently valid per-binding FinalProductionPlan pointers when later collection recovery normalization fails. The repair remains deliberately narrow: **only actual TRAIN2 continuation/admission is collection-global**. Recovery now distinguishes roots that truly still require trainer work from already-terminal-but-unsealed roots that require only the existing completion/seal transition. The latter are sealed before scheduler sizing and never inflate TRAIN task_count, controller ceilings, progress, or resource-profile compatibility. The same rule covers current post-cutover roots and authenticated historical/legacy roots through their existing recovery owners. EVAL2, per-seed assessment, and final publication remain inside the frozen-size-ordered finalization path. FinalProductionPlan pointers remain per-binding rather than collection-atomic, and the live generation/currentness fence still prevents new old-design TRAIN2 admission after target-size rollover.

No D1/D2 defect was found. No second scheduler, collection publication transaction, new persistent orchestration machinery, or widened evaluation semantics is authorized.

This cycle is a **stakeholder-authorized bounded D3 reopen of final-production selected-size scheduling**. Accepted multi-size lineage had ultimately frozen serial outer-size orchestration as the current concretization. This workplan intentionally supersedes that one production scheduling choice only; it does not retroactively reinterpret the archived serial design as already-global, and repository presence on this branch does not make the proposed D3 mutation accepted-current before independent falsification and merge through the normal architecture acceptance path.

This cycle repairs final-production orchestration only. The defect is not that the adaptive TRAIN2 controller cannot promote concurrent work. The defect is that train-production authenticates the frozen collection as one experiment, then serializes selected sizes outside the existing scheduler and constructs a fresh scheduler for each size. The scheduler therefore sees only the seeds of the current size, not all independently ready final-production trajectories.

For a frozen two-size collection with the current one-seed production policy, the implementation presents one task at a time to a scheduler whose truthful task ceiling is one. With two configured final seeds it presents two tasks for the first size and, only after that size is completely assessed and published, another two tasks for the second size. This is structurally work-starving when the one shared CPU/GPU resource envelope could safely admit concurrent production trajectories from different selected sizes.

The repair is to make **all final-production positions that remain TRAIN_REQUIRED after collection-wide recovery normalization participate in one existing adaptive TRAIN scheduler wave**. That shared wave ends at authenticated sealed TRAIN2 roots. Only after every scheduler-owned TRAIN2 position is terminal does the command resume the existing frozen-size-ordered finalization path: per-size serial EVAL2, per-seed assessment, and binding-scoped final publication. Later sizes may finish TRAIN2 early, but they do not perform fresh EVAL2 or publish assessments merely because their training finished first.

Cross-validation scheduling is explicitly out of scope and remains unchanged.

## Background and terminology

A **production position** is one exact final-production trajectory authorized by one FinalProductionPlan, identified by its selected TargetBinding, optimizer seed, production horizon, method/replay ancestry, and existing run-plan identity.

A **production collection wave** is the execution-local set of all currently required production positions across every frozen selected size after the collection-wide CV admission barrier succeeds. Recovery normalization partitions that set into reusable sealed/terminal state and the TRAIN_REQUIRED subset that alone becomes the scheduler wave.

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

After the collection-wide CV admission barrier succeeds and production recovery normalization completes, every position still classified TRAIN_REQUIRED across all selected contexts enters one scheduler-ready population governed by exactly one call path that constructs one TrainingConcurrencyPlan and one AdaptiveTrainingConcurrency for that production TRAIN wave.

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
  -> one TRAIN scheduler population for TRAIN_REQUIRED positions only
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

The collection scheduler owns TRAIN2 only and returns after every TRAIN_REQUIRED position has reached the existing authenticated sealed-root boundary. It MUST NOT run EVAL2 as part of the global scheduler wave.

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

Before the global concurrency plan is built, resolve each production position through the existing root-locator semantics, then hold the existing run-activity exclusion for recovery authentication and for any completion/seal mutation. Ordinary locator resolution need not acquire the lease; no liveness, completion, or reuse conclusion may be drawn from pathname existence alone.

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

Once Phase B has validly committed all per-binding FinalProductionPlan pointers, a later collection recovery-normalization failure likewise does **not** roll those pointers back. A current FinalProductionPlan pointer is planning authority for its own binding, not proof that TRAIN2, EVAL2, assessment, or publication completed. Recovery failure still occurs before the first new TRAIN admission, so it launches zero new trainers, begins no EVAL2, and publishes no new assessment/final-production decision. Any append-only terminal seals already completed by recovery normalization remain durable under D3-8. Do not add a collection transaction merely to erase independently valid plan pointers or completed recovery seals.

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

### D3-16 - Linearize frozen-design currentness with every new TRAIN admission

The global queue lengthens the interval between initial planning and later task admission. The accepted multi-size contract already requires that once a generation/design becomes stale, no further outer-size work is newly admitted for that retired design. Serial selected-size execution repeatedly crossed currentness owners; a collection queue must preserve that boundary without introducing a long-held campaign lease.

At collection construction, capture the invocation's compact **collection currentness signature** as:

~~~text
(expected campaign generation, ordered tuple of expected current binding digests)
~~~

The ordered binding tuple comes from the same canonical per-size binding projection that owns the current frozen design. Do **not** bind this signature to the campaign state revision: same-generation diagnostic/observational revisions that preserve the frozen design must not spuriously retire valid production work. Conversely, membership-only checking is insufficient as the collection contract; the queue belongs to the exact frozen ordered design that was authorized.

For current/v2 frozen designs, derive the tuple through `current_target_size_bindings(state)`. Do not invent a second binding formula. Retired/prerework schemas retain their existing compatibility behavior: if they cannot reach current final-production planning/publication under accepted owners, they must fail at that existing boundary rather than acquiring a new scheduler-only currentness interpretation.

Before the **first** TRAIN2 admission and before every later admission of a previously unstarted or demoted/requeued task, establish a real linearization point against target-size generation transitions. A plain read followed by `executor.submit(...)` is not sufficient because `prepare` can commit a new generation between those operations.

The admission fence must reuse the CampaignStore serialization authority already used by target-size transitions (for example, the existing `exclusive_transaction()` plus the canonical head/binding projection, or an exactly equivalent factored owner) so that one total order exists:

1. either the generation/design transition commits first, in which case the task is rejected as stale and is not newly admitted;
2. or the scheduler admission commits first while the expected collection signature is current, in which case that task is already admitted and may settle under ordinary historical/currentness rules even if rollover commits immediately afterwards.

The **admission commit point** is execution-local and durable state is not required. It must cover the scheduler's successful ownership transition for that task (dequeue/reservation plus successful future submission/active registration, or an equivalent indivisible scheduler transition) while the serialized currentness observation excludes a concurrent generation commit. Hold the CampaignStore serialization only for this short admission transition; never hold it while TRAIN2 runs, while waiting for a worker/future, during telemetry polling, or across the whole wave.

If the serialized currentness check finds a different generation or ordered binding tuple:

- admit no new queued TRAIN2 task for the retired design;
- route the stale condition through the existing whole-wave terminal abort path, so every already-active owned worker receives the ordinary cancellation signal and is reaped by its real execution/process owner;
- begin no new EVAL2/finalization admission for that invocation;
- preserve any authenticated terminal TRAIN2 evidence as historical/restart evidence subject to normal later currentness;
- fail with the existing stale/currentness error family, not a scientific rejection.

After the global TRAIN wave reaches terminality, perform the same serialized collection-signature check to linearize **admission of the per-size EVAL2/finalization phase**. If rollover committed first, no EVAL2 begins. If finalization admission linearizes first and rollover commits afterwards, already-admitted EVAL2 may finish as ordinary work, but the existing commit-time per-binding pointer/currentness fences remain authoritative and must prevent stale assessments/final products from becoming current. Do not keep the CampaignStore transaction open during EVAL2 merely to prevent a later legitimate generation transition.

This distinction is intentional: the architecture guarantees a total order at admission boundaries, not an impossible zero-duration race-free interval between a read and arbitrary later computation. No new persistent scheduler-currentness registry, generation lease, or rollback protocol is authorized.

### Delegated D4 space

Implementation may choose internal helper names, dataclass names, mapping shape, and whether planning/finalization are extracted from execute_final_production into private helpers. The required architecture is behavioral and ownership-based.

A preferred minimal reduction is:

~~~text
Phase A: construct/authenticate every per-size production bundle in memory
  -> validate unique global scientific/run identities
Phase B: publish existing per-binding final-plan/run-plan authorities
  -> production-only collection recovery normalization
       sealed roots: authenticate
       terminal-but-unsealed roots: existing owner seals with zero trainer launch
       incomplete/fresh roots: TRAIN_REQUIRED
  -> prove one compatible execution profile over TRAIN_REQUIRED only
  -> one generalized existing scheduler TRAINs only TRAIN_REQUIRED positions to seal
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

Before scheduling, all of those states pass the D3-7/D3-8 normalization. A retry schedules only positions that still require actual trainer continuation. Terminal-but-unsealed roots are completed/sealed through existing recovery owners with zero trainer launch and disappear from task_count. If normalization later fails on another position, already-valid per-binding FinalProductionPlan pointers and already-completed append-only seals remain durable, but no new trainer/EVAL2/assessment/final publication starts. After a successful collection TRAIN wave, per-size finalization reuses authenticated sealed roots and any exact reusable measurements through existing owners. Completed sibling TRAIN2 work cannot be invalidated merely because another selected size previously failed.

### O5 - Preserve publication barriers/currentness without inventing collection atomicity

Every existing publication remains under its binding/campaign-generation barrier and current-pointer/currentness checks. A collection scheduler result is not authority to publish if the owning context became stale before finalization.

No collection-level publication transaction is introduced for plans, assessments, or final products. Phase-B FinalProductionPlan pointer commits remain independently binding-scoped. If one pointer commit or a later per-size finalization fails its currentness/publication check, preserve already committed valid sibling pointers/evidence, stop before the next unauthorized phase as specified above, and report the real failure. Do not roll back immutable objects or current pointers merely to manufacture collection atomicity that the accepted architecture does not define.

### O6 - Preserve single-size behavior

For one selected size, the generalized path must remain behaviorally equivalent to the current production path: same plans/identities, task population, adaptive-controller semantics, TRAIN/EVAL separation, assessment/publication, and failure/restart semantics.

The repair must not special-case multi-size by maintaining two independent production implementations.

### O7 - Do not promote seed policy into scheduler policy

The current generated production default is seeds=[1]. This workplan does not change it.

The scheduler receives the sum, across selected sizes, of required final-seed positions that remain TRAIN_REQUIRED after recovery normalization. Root unsealedness by itself is not sufficient for scheduler admission.

Thus two selected sizes with one seed each naturally provide two independent TRAIN2 positions. If the user configures two final seeds per size, four scientific positions exist; that count comes from the existing production policy, not scheduler invention.

### O7A - Preserve stale-generation admission semantics through the D3-16 linearization owner

Factor or reuse the smallest existing currentness owner that can implement D3-16 without a second binding formula. The implementation obligation is the exact collection signature:

~~~text
(campaign generation, ordered tuple of current binding digests)
~~~

derived from the canonical current binding projection. A campaign state-revision change alone is not staleness, and unordered/membership-only comparison is not the collection scheduler contract.

The check and scheduler ownership transition must be **serialized against target-size generation transitions** through the existing CampaignStore transition authority. A helper that merely reads current bindings and returns a boolean for the caller to use later does not satisfy this obligation; it recreates the forbidden read-then-submit TOCTOU window.

Apply the linearized fence at:

- first TRAIN admission;
- every later admission, including a demoted/requeued task when it is newly readmitted;
- the post-TRAIN admission of the EVAL2/finalization phase.

On stale detection, route through the existing whole-wave terminal cancellation/reap path. On an admission that linearizes before rollover, treat the task/phase as already admitted and rely on the existing commit-time per-binding publication fences for any later rollover. Hold no CampaignStore transaction across TRAIN2, telemetry waits, EVAL2, or final publication.

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

Any change to _PendingPostSelectionRun, _preflight_post_selection_pending_runs, _execute_post_selection_pending_runs, or _run_post_selection_positions must retain the existing CV call path and semantics. The new collection-wide terminal-state normalization is required for **final production orchestration**; factoring a low-level current/legacy recovery classifier/seal primitive is allowed, but do not make public CV adopt a new collection-global pre-scheduler normalization, task-count definition, progress contract, or selected-size queue. No production-only assumptions may leak into the CV task carrier. Run the real public multi-size CV and scheduler/recovery regressions after the refactor.

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

| Existing capability | Current disposition |
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
| stale-generation/retired-design admission stop | PRESERVE through the D3-16 serialized `(generation, ordered binding digests)` linearization at every TRAIN admission and at EVAL/finalization-phase admission; commit-time per-binding fences remain authoritative after an admission wins the race |
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

- exactly two fresh TRAIN_REQUIRED positions enter one production scheduler wave;
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

In every failing case assert zero new sibling trainer launches, no EVAL2 begins, and the authoritative GPU admission baseline/controller is not used to admit work after the failure. When the failure occurs after Phase B, assert that already-valid per-binding FinalProductionPlan pointers remain current if their own binding is still current, while no assessment/final-publication pointer is created merely because planning succeeded. When an earlier normalization step already appended a valid terminal seal, assert that seal remains durable and is not rolled back.

#### A7 - terminal-but-unsealed normalization, mixed restart, and canonical EVAL order

Cover two real-owner subcases. First, use a multi-size production collection containing one valid already-sealed root, one post-cutover root with authenticated terminal TRAIN2 summary but no completion seal, and at least one genuinely incomplete/fresh sibling that still requires TRAIN2. Second, preserve/extend the existing historical-reuse real-owner fixture for an authenticated historical/legacy terminal-but-unsealed production root; if exact historical ancestry cannot lawfully coexist with the synthetic multi-size fixture, the historical case may remain single-size, but it must pass through the same factored production recovery-normalization owner.

Prove:

- every terminal-but-unsealed root in the applicable subcase is completed/sealed through its existing recovery owner with **zero trainer launch**;
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

**Post-Phase-B recovery-failure case:** let all per-binding plan pointers commit, then inject a corrupt later recovery root during collection normalization. Prove zero trainer/EVAL2 launches, no assessment/final publication, independently valid plan pointers remain current for bindings that are still current, and any valid earlier append-only terminal seal remains durable. This is not a collection rollback boundary.

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

Through the real production owner, instrument the existing run seam and prove that the collection-wide scheduler invokes only TRAIN_REQUIRED tasks with TRAIN-only semantics and returns after all scheduler-owned positions are authenticated terminal/sealed. No EVAL2 provider, candidate assessment, measurement publication, or final-seed assessment is entered from inside that global scheduler wave.

Then prove those same roots are consumed by the subsequent per-size finalizer through the existing run/EVAL owners. This is the structural/behavioral guard against accidentally globalizing EVAL2 while repairing TRAIN2 admission.

#### A19 - generation rollover is linearized against queue and EVAL admission

Exercise the real CampaignStore transition owner and the real production scheduler with enough tasks that at least one task is active and at least one later task remains queued.

Cover both orderings at the exact admission boundary:

1. **rollover wins** - arrange the new prepared generation transition to commit before the next queued task's admission linearization. Prove the queued old-generation task is never submitted/registered as active, stale currentness routes through whole-wave cancellation/reaping of already-owned workers, and no EVAL2/assessment/final publication begins.
2. **admission wins** - arrange the scheduler's serialized currentness/admission transition to complete first, then let generation rollover commit immediately afterwards. Prove that already-admitted task may settle under ordinary worker ownership, no *additional* old-generation task is admitted after rollover wins the next boundary, and commit-time currentness prevents stale assessment/final publication from becoming current.

Use a deterministic race seam/barrier capable of pausing at the currentness/admission boundary; a test that rolls the generation only well before or well after `submit()` does not prove closure of the TOCTOU window.

Also cover the phase boundary after all TRAIN2 tasks are terminal:

- if rollover commits before serialized EVAL/finalization admission, no EVAL2 begins;
- if EVAL/finalization admission linearizes first and rollover commits afterwards, EVAL may finish but stale assessment/final-publication current-pointer publication must fail through the existing per-binding commit-time fence;
- no long-held campaign lock, persistent scheduler-currentness registry, or rollback state is introduced.

Finally assert that same-generation state revisions which preserve `(generation, ordered binding digests)` do not spuriously cancel the wave.

### Structural acceptance

Static/source inspection must establish:

- no production outer loop calls a complete per-size execute_final_production(context) that internally creates its own scheduler;
- no second scheduler/executor/lease manager was added for size concurrency;
- only one adaptive TRAIN controller is created for one collection production TRAIN wave;
- all global production position descriptors are enumerated without eagerly creating fresh training materialization, duplicate run/training identities fail closed, and only post-normalization TRAIN_REQUIRED descriptors reach concurrency-plan construction;
- every sealed production root is authenticated and every durable unsealed current/legacy continuation is normalized before the authoritative TRAIN admission baseline;
- authenticated terminal-but-unsealed current/legacy roots are sealed through existing owners with zero trainer launch and excluded from task_count/profile compatibility;
- scheduler admission uses the canonical CampaignStore binding projection and the existing serialized transition owner to linearize `(generation, ordered binding digests)` against first/later task admission and EVAL-phase admission; a read-then-submit TOCTOU window is not accepted;
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

Refactor final-production planning so Phase A constructs/authenticates every per-size plan/task descriptor without current-plan pointer side effects or fresh training materialization and validates global scientific/run identities; then Phase B publishes through existing per-binding owners. Resource-profile compatibility is deliberately deferred until Stage P2 recovery normalization has derived the actual TRAIN_REQUIRED set. Preserve the second-line CV guard and one-size scientific identity. Run A3, A5, A11, A13, and A15 plus focused production identity/publication tests.

### Stage P2 - collection recovery + TRAIN-only scheduler generalization

Make pending tasks self-owning; perform collection-wide current/legacy recovery normalization; seal authenticated terminal-but-unsealed roots without trainer launch; derive TRAIN_REQUIRED positions; prove scheduler-profile compatibility over that reduced set; implement global task-count semantics plus a **serialized, linearizable** canonical collection-currentness admission fence; execute one TRAIN-only wave that ends at sealed roots. Run A1-A2, A6-A7, A10, A12, A17-A19 plus existing scheduler/currentness/historical-recovery regressions.

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
- preserving stale-generation admission semantics cannot be linearized using the existing short-lived CampaignStore serialization authority without a new persistent currentness registry or long-held campaign lock;
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
- every new TRAIN admission and the EVAL/finalization phase admission has a defined linearization point against target-generation transitions using `(generation, ordered binding digests)`; rollover that wins the boundary admits no stale work, while work admitted first remains subject to ordinary commit-time currentness;
- the collection scheduler stops at authenticated sealed TRAIN2 roots, and no EVAL2 begins until the entire global TRAIN wave is terminal;
- per-size EVAL2/assessment/publication then remains frozen-size/seed ordered and fail-fast, independent of scheduler order;
- public CV selected-size scheduling and semantics remain unchanged despite shared-helper refactoring;
- one-size behavior remains conforming;
- current D3/D4 documentation explicitly supersedes the accepted serial-production scheduler baseline and matches the repaired execution contract;
- all required focused and affected regression is green or explicitly unavailable/blocking;
- final affected surface, evidence applicability, and PEM/history impact are reconciled;
- no physical GPU qualification is falsely claimed.

Independent Review must reconstruct the real owner chain and attempt to falsify the global-scheduler claim. A test that merely calls a new helper with four synthetic tasks cannot close the workplan if the public train-production command can still serialize selected sizes before reaching that helper.


## 10. Independent implementation Review reopen — 2026-09-20

### 10.1 Review disposition and scope

**NO-PASS at reviewed head `f7d4925e08fe3e013b4a35a71a29d6fed8c8c2be`. No Serious Challenge to D3 is active.**

The collection-global TRAIN restructuring is directionally conformant: one TRAIN-only adaptive controller owns the production collection wave; EVAL2 remains outside that wave; FinalProductionPlan publication remains binding-scoped; finalization remains frozen-size ordered and fail-fast; execution-only scheduler keys remain outside scientific identity; `training_parallel.py` remains unchanged; and the exact collection signature is checked inside the existing CampaignStore serialization authority before each new TRAIN admission and before finalization admission.

The implementation is reopened at D4 for the six obligations below. These are **repairs and evidence closure against the already frozen Revision 8 D3 contract**. Do not reinterpret this section as authorization for a second scheduler, profile buckets, a new lease/currentness registry, a cross-size reducer, widened EVAL behavior, or a change to D1/D2. If R2 demonstrates that the existing one-controller resource model cannot safely represent the actual heterogeneous production workloads, stop D4 and reopen D3 under Section 8 rather than hiding the mismatch with local machinery.

### 10.2 R1 — classify every production root under the existing run-activity owner

**Owning surface:** `mdstats/training_data/campaign_post_selection_runtime.py::_normalize_final_production_recovery`, using the existing `post_selection_run_activity_lease(...)` and existing current/legacy recovery/authentication owners.

The current implementation may resolve a root locator before taking the run lease, but it SHALL NOT classify the position as fresh, incomplete, terminal-unsealed, sealed, corrupt, foreign, reusable, or TRAIN_REQUIRED from pathname existence, directory emptiness, or any other mutable root observation before the lease.

Repair the current shortcut equivalent to:

```python
if root.legacy is None and not (root.path.is_dir() and any(root.path.iterdir())):
    required.append(task)
    continue
```

so that the order is:

1. resolve the current/historical root locator without mutation;
2. acquire the existing run-activity lease for that resolved root;
3. while holding that lease, authenticate/classify all state relevant to TRAIN_REQUIRED versus reusable/sealable/fail-closed;
4. seal a terminal-but-unsealed root only through the already accepted completion/topology owner and keep it out of scheduler `task_count`;
5. append a genuinely fresh/incomplete position to TRAIN_REQUIRED only from that lease-owned classification;
6. release the run lease before any long-running scheduler admission or trainer execution.

Do not hold the run lease across the global scheduler wave, add an outer collection lease, add a liveness registry, infer ownership from PID/mtime/pathname, or weaken sealed-root read-only behavior.

**R1 acceptance:** add a deterministic race test at the real normalization owner. Arrange another invocation/owner to acquire the same run-activity lease and transition the position while normalization is blocked at the ownership boundary. After normalization obtains the lease, it must observe the authoritative post-transition state rather than an earlier empty/nonexistent-path observation. At minimum prove that a position completed/sealed by the winning owner is not counted as TRAIN_REQUIRED and does not cause a trainer request, scheduler task-count inflation, or duplicate run. Also preserve corrupt/foreign fail-closed-before-sibling-launch coverage.

### 10.3 R2 — close A17 with a real resource-compatibility proof, not profile-name equality

**Owning surfaces:** `_post_selection_scheduler_profile`, `_require_one_post_selection_scheduler_profile`, the TRAIN2 runtime/materialization request path, and the existing `TrainingConcurrencyPolicy`/`TrainingConcurrencyPlan` contract. `training_parallel.py` remains frozen unless this investigation triggers a D3 reopen.

The implementation must establish the resource consequences of distinct TRAIN_REQUIRED production sizes/horizons. Equality of configuration-derived profile fields is insufficient by itself.

Use at least two positions that both remain TRAIN_REQUIRED after normalization and differ materially in production workload. Prefer the actual selected-size regime `N=512` versus `N=8192` with their frozen `H_prod`; a smaller synthetic case is acceptable only if it is demonstrably discriminating for every resource dimension being proved.

For those positions, capture or derive at the existing real-owner/test seam the exact values entering TRAIN2 and the concurrency plan, including at least:

- device/backend/telemetry domain and learned/default precision;
- model/runtime realization and replay lineage affecting residency;
- batch and validation batch geometry;
- loader-worker/native-thread geometry and effective CPU allocation;
- structures/examples per epoch and any materialized dataset size that remains resident during training;
- production horizon and whether it changes simultaneous resident state versus only total work duration;
- configured per-job RAM and VRAM estimate regime;
- timeout/process-supervision and minimum-disk owners.

Then close the proof dimension by dimension:

- **VRAM:** establish from the actual trainer/runtime realization that changing `N` or `H_prod` does not create dataset-wide/device-resident state beyond the common batch/model/runtime geometry, or establish a conservative existing per-job VRAM bound valid for the largest admitted task.
- **RAM:** if host-resident materialization/dataset state scales with `N`, establish a conservative bound for the largest admitted task and prove the existing per-job RAM estimate used by the planner covers it. Do not treat the estimate merely being equal across tasks as proof that it is sufficient.
- **CPU/threading:** prove effective per-job thread/worker geometry is common or already conservatively represented by the one plan.
- **duration/horizon:** prove horizon affects work duration only unless evidence shows it changes simultaneous per-job resident demand.

A test that merely asserts `device == "cuda:0"`, equal loader-worker counts, or equality of `TrainingConcurrencyPolicy` objects does not satisfy A17.

If this investigation finds material per-job demand heterogeneity that cannot be bounded safely by the existing homogeneous controller/estimate contract, **stop and reopen D3**. Do not create per-size buckets, multiple controllers, task-weighted promotion, or a second resource model as a D4 workaround.

### 10.4 R3 — replace the non-discriminating A4 serial/concurrent equivalence test

**Owning test:** `tests/test_mlff_production_global_train_scheduler.py::test_serial_and_concurrent_widths_produce_identical_governed_identities` or its renamed replacement.

The current test runs the width-1 campaign to completion and then reruns the already completed workspace at a wider setting, where the second arm launches no trainer. That proves completed evidence is reusable across an execution-only width change; it does **not** prove a fresh serial execution and a fresh concurrent execution derive identical governed scientific identities/evidence.

Replace or supplement it with two isolated but identically prepared pre-production campaign states:

1. freeze the same selected bindings/memberships/horizons and establish the same accepted CV ancestry in both;
2. run final production in campaign A with effective scheduler width exactly 1;
3. run final production in campaign B with an admissible width greater than 1;
4. prove campaign B actually executes fresh concurrent TRAIN2 work — at least two trainer requests must overlap/be simultaneously admitted through the real collection scheduler, not merely be reusable sealed roots;
5. compare the governed outputs after canonical ordering while excluding execution-only telemetry/order/timing:
   - FinalProductionPlan identities;
   - TrainingTrajectoryIdentity/run identities;
   - assessment-position identities/policy ancestry;
   - selected checkpoint/measurement evidence under the deterministic bounded trainer seam;
   - per-seed assessments;
   - final per-binding publication decisions.

The width setting itself must not enter any scientific/numerical identity. Keep the existing reuse-across-width test if useful, but do not count it as A4.

### 10.5 R4 — add the missing incompatible historical interrupted-continuation normalization case

**Owning surfaces:** `_normalize_final_production_recovery`, `_complete_legacy_training_root(..., launch_trainer=False)`, and the existing historical training-equivalence/authentication owner.

Construct a multi-size production collection in which one production position resolves to an **interrupted historical/legacy continuation** whose persisted historical training ancestry is syntactically valid enough to reach authentication but is incompatible with the current authorized training trajectory/runtime continuation. Keep at least one sibling position otherwise fresh and runnable.

Invoke the real public `train-production` owner and prove:

- collection Phase A/Phase B behavior remains consistent with Revision 8; independently valid per-binding FinalProductionPlan pointers published before recovery failure are not rolled back;
- normalization rejects the incompatible historical continuation before construction/admission of sibling TRAIN work;
- **zero new trainer invocations** occur for every sibling position;
- no EVAL2/final-assessment/final-publication work begins;
- the incompatible historical root is not rewritten, copied, renamed, relabeled current, or partially resealed;
- diagnostic/historical bytes remain intact for retry/investigation.

Do not satisfy this with a direct unit call to the historical helper only; the acceptance boundary is the assembled production collection owner.

### 10.6 R5 — make A8 prove completed sibling preservation across a failed global wave

**Owning test:** the global-wave failure/restart acceptance in `tests/test_mlff_production_global_train_scheduler.py`.

The existing failure test cancels/fails all work and then legitimately reruns all positions. It does not prove the required case where one cross-size sibling has already reached authenticated sealed TRAIN2 before another sibling fails.

Add a deterministic real-owner test with at least two production positions from different selected sizes:

1. admit the global TRAIN wave through the normal scheduler;
2. force one position to reach terminal TRAIN2 and publish its existing completion/topology seal;
3. only after that seal is durable, make another active/admitted position fail;
4. prove no new EVAL2 starts, no further queued work is admitted after failure, and all still-active owned siblings are cancelled/reaped before the scheduler returns/raises;
5. retry from the same workspace with healthy execution;
6. prove recovery authenticates and reuses the already sealed sibling with **zero trainer relaunch for that position**;
7. prove only outstanding TRAIN_REQUIRED work re-enters `task_count`/the scheduler, then normal frozen-order finalization completes.

Use barriers/events in the bounded test trainer to make the completion-before-failure ordering deterministic. Do not add production retry state or a scheduler-specific completion registry.

### 10.7 R6 — execute and record evidence after the executable repair

Test source is an evidence specification, not evidence realization. After R1-R5 are implemented, record a fresh implementation-evidence subsection in this workplan or a repository-native evidence artifact that names the exact repaired commit SHA and exact commands/results. Do not close against results from `f7d4925e08fe3e013b4a35a71a29d6fed8c8c2be` or another pre-repair tree.

At minimum run, on the same repaired SHA:

```text
python -m compileall mdstats tests
python -m pytest -q tests/test_mlff_production_global_train_scheduler.py
python -m pytest -q tests/test_mlff_p5_replay_target_real_owner.py
python -m pytest -q tests/test_mlff_p5_train2_memory_backoff.py tests/test_mlff_p5_train2_zero_safe_admission.py
python -m pytest -q tests/test_mlff_target_size_multi_size_integration.py tests/test_mlff_target_size_multi_selection.py
python -m pytest -q tests/test_mlff_target_size_p5e_production_and_restart.py
python -m pytest -q tests/test_mlff_replay_mace_p5_execution_recovery.py
python -m pytest -q tests/test_mlff_campaign_currentness_races.py tests/test_mlff_campaign_assembled_lifecycle.py
python -m pytest -q tests/test_mlff_storage_reset_integration.py
```

Also rerun every additional test file directly touched by the repaired implementation or invalidated by the changed recovery/admission behavior. Then run the complete affected MLFF campaign/training-data CPU regression. If the impact boundary cannot be defended narrowly, run the repository's full available CPU test suite.

The evidence record must state pass/fail/skip counts, identify any unavailable environment-dependent checks, and distinguish those from actual failures. A docs-only GitHub Actions success does not close executable acceptance.

Physical production GPU throughput/VRAM qualification remains deferred to the final release package under standing project direction. R2 is still required now as deterministic owner/resource-contract evidence; do not falsely label it physical GPU qualification.

### 10.8 Re-review closure condition

A subsequent independent Review may return PASS only if all of the following hold on one exact candidate SHA:

- R1 removes every pre-lease liveness/completion/TRAIN_REQUIRED inference and the race acceptance passes;
- R2 positively closes A17, or D3 has been explicitly reopened because the one-controller resource assumption was falsified;
- R3 executes both fresh width-1 and genuinely concurrent width>1 production paths and establishes governed-output equivalence;
- R4 rejects an incompatible interrupted historical continuation before any sibling trainer launch while preserving valid Phase-B pointer semantics and historical bytes;
- R5 demonstrates sealed completed-sibling reuse after a later global-wave failure;
- R6 records executable realization of the focused and affected regression on the same repaired SHA;
- no repair introduces a second scheduler/resource/currentness/recovery owner or mutates D1/D2 semantics;
- the final candidate still satisfies Sections 1-9, including exact collection-signature admission linearization, TRAIN/EVAL phase separation, frozen-order fail-fast finalization, CV non-impact, and deferred physical GPU qualification.

## 11. D4 repair and executable evidence — 2026-09-20

### 11.0 Status

The Section 10 repair contract R1-R6 is implemented and its acceptance executed.
**This workplan stays open for independent Review.** Nothing here closes the
cycle, accepts the Revision 8 D3 candidate as accepted-current, or claims
physical GPU qualification.

**Repaired candidate SHA: `0462f56f6bfb22ea254a28683a62937b6aad2740`.**

Every executable result below was produced from that exact tree. This evidence
subsection is published in a later commit that changes no executable file; the
`mdstats/` and `tests/` trees of that commit are identical to
`0462f56f`, which `git diff 0462f56f -- mdstats tests` confirms as empty.

### 11.1 R1 - recovery classification is owned by the run-activity lease

**Owner:** `campaign_post_selection_runtime.py::_normalize_final_production_recovery`.

The pre-lease shortcut that appended a position to `TRAIN_REQUIRED` from
`root.path.is_dir() and any(root.path.iterdir())` is gone. The freshness
decision now happens inside the `post_selection_run_activity_lease(root.path)`
block the pass already held for every other classification, so no root is
classified fresh, incomplete, terminal, sealed, corrupt, reusable or
`TRAIN_REQUIRED` from mutable pathname state before ownership. Locator
resolution still happens outside the lease, the lease is still released before
scheduler admission, and the change adds no lease, liveness registry,
PID/mtime inference or collection lock. The whole source change is one moved
block plus its docstring.

**Acceptance.**
`tests/test_mlff_production_global_train_scheduler.py::test_recovery_classifies_positions_only_under_the_run_activity_lease`
drives the real `train-production` owner. Phase A/B publish both per-binding
plan pointers and stop before recovery, so the contested root is genuinely
absent. A competing owner then takes the *existing* run-activity lease for
that exact root while it is still absent, waits until normalization has
reached the ownership boundary, and drives the position to an authenticated
sealed TRAIN2 root through the real run owner (`_execute_post_selection_run_locked`,
`stop_after_training=True`). After normalization obtains the lease it observes
the authoritative post-transition state: the position is excluded from
`TRAIN_REQUIRED`, requests no trainer, produces no duplicate run, and the wave
is sized `task_count=1` with `train_required=1; sealed=1`.

The test is discriminating, not merely passing. Re-running it against the
pre-repair shortcut on an otherwise identical tree fails with
`assert [2] == [1]`: the pre-lease observation inflates the wave to two
positions and requests a trainer for a root another owner already owns.
Corrupt/foreign fail-closed-before-sibling-launch coverage is retained
unchanged (`test_corrupt_continuation_fails_before_any_sibling_trainer`,
`test_corrupt_sealed_root_fails_before_any_sibling_trainer`).

### 11.2 R2 - A17 closed positively; the one-controller resource assumption is not falsified

**Owner:** `_post_selection_scheduler_profile`, `_require_one_post_selection_scheduler_profile`,
the TRAIN2 runtime/materialization request path, and `build_training_concurrency_plan`.
`training_parallel.py` is unchanged.

`tests/test_mlff_production_global_train_scheduler.py::test_distinct_production_sizes_and_horizons_make_one_resource_demand`
takes the two positions that actually remain `TRAIN_REQUIRED` after recovery
normalization and that differ in *both* suspected inputs: selected size (and
therefore exact training membership and materialized dataset) and frozen
production horizon. It captures the exact values entering TRAIN2 and the
concurrency plan at the real owner seam and closes the proof dimension by
dimension.

* **VRAM / device residency.** Device, optimizer device, learned-model
  precision, training method/model realization, replay lineage and the
  batch/validation-batch geometry are equal across the two positions. Those
  are the only quantities that determine device residency in the realized
  runtime; the runtime plans the two positions receive are byte-identical once
  the epoch budget, per-epoch structure count and execution epoch limit are
  removed. No dataset-wide or horizon-wide device-resident state exists beside
  the common batch/model geometry. The live bound is additionally
  size-independent by construction: the plan's VRAM admission envelope is
  `observed aggregate telemetry total x configured fraction` with the observed
  aggregate used bytes as baseline, and promotion/backoff continue to run off
  that aggregate observation rather than off any per-task estimate.
* **CPU / threading.** Loader workers per job are equal, and the plan's
  `cpu_threads_per_job` is derived from the one CPU budget, the one loader
  geometry and the task count. `N` and `H_prod` are not inputs.
* **Host RAM.** This is the one per-job quantity that genuinely scales with
  `N`: the materialized training transport the trainer reads. The test shows
  it strictly larger for the larger selected size, and shows the planner
  representing it by one configured, size-independent per-job estimate
  (`estimated_training_ram_mib_per_job`), with the larger position's realized
  materialization inside that estimate.
* **Horizon.** `H_prod` reaches the runtime only through the epoch budget and
  the execution epoch limit; the budget policies differ only in
  `planned_epochs` and its derived digest. It changes work duration, not
  simultaneous resident demand.

**The decisive check.** `build_training_concurrency_plan` is called with exactly
`(task_count, device, loader_workers_per_job, resources, policy, gpu_sample)`.
The test asserts that set of inputs is complete, that the policy equals the one
each context derives, and then rebuilds the plan from the *larger* position's
context alone at the same task count: the resulting `TrainingConcurrencyPlan`
is equal to the plan the heterogeneous two-size wave actually used. The
collection wave therefore reserves per job exactly what the largest selected
size's own homogeneous wave of the same width already reserved under the
accepted per-size baseline. Globalization introduces no new per-job resource
demand, and the per-job estimate's adequacy for the production regime remains
the same pre-existing operator configuration obligation it already was for the
largest size.

Equality of `TrainingConcurrencyPolicy`, device or loader-worker settings is
*not* offered as the proof; it is the fail-closed guard that A10 exercises
(`test_incompatible_execution_profile_fails_before_any_trainer`,
`test_an_incompatible_profile_on_a_sealed_position_does_not_block_the_wave`),
and both remain green.

**Result: no material heterogeneity was found that the existing homogeneous
controller cannot represent. No D3 reopen is raised, and no resource bucket,
second controller, weighted promotion or second scheduler was introduced.**

**Regime limitation, stated explicitly.** The executed positions are the
fixture ladder's CV-feasible sizes (`N=8`, `H_prod=2` versus `N=16`,
`H_prod=3`), not `N=512` versus `N=8192`. The claim those positions establish
is *functional independence*: any dependence of a scheduler or runtime input on
`N` or `H_prod` would manifest between any two distinct values, and none does -
the only quantity that varies is the host-resident training transport, exactly
as derived. The magnitude question that a `512` versus `8192` run would answer
is per-job host-RAM *sufficiency*, and the final check above shows that this
magnitude question is unchanged by this cycle: the mixed wave's envelope is the
largest size's own accepted envelope. Physical production-scale VRAM/throughput
qualification remains deferred to the final release package and is not claimed
here.

### 11.3 R3 - genuine fresh-serial versus fresh-concurrent equivalence

`test_serial_and_concurrent_widths_produce_identical_governed_identities` was
retired as the A4 oracle. It is retained, renamed
`test_reusing_sealed_roots_across_a_width_change_retrains_nothing`, and
labelled as the reuse/restart property it actually proves.

The new A4 is
`test_fresh_serial_and_fresh_concurrent_production_agree`. It builds two
isolated campaigns, each from nothing, and asserts they are identically
prepared by comparing the frozen binding, method, current CV plan and current
CV acceptance digests of every selected size. Campaign A runs fresh production
at effective width exactly 1 (`plan.maximum_jobs == 1`). Campaign B runs fresh
production at an admissible width greater than 1 and must genuinely overlap:
the bounded child blocks until the wave owns two simultaneous trainers, the
test asserts `max_active >= 2`, and it additionally asserts that at least two
trainer windows overlap in time. Both arms train all four positions; neither
reuses the other's evidence.

The two campaigns are built one after another at the *same* absolute workspace
path, the first being moved aside in between. That was a deliberate design
decision after a measurement: run-local materialization records legitimately
carry their own absolute `output_directory`, so two campaigns at different
paths differ in `materialization_digest` *at equal width*. Reusing one path
keeps A4 an exact identity comparison instead of one that must normalize
workspace location away.

Compared after canonical ordering (frozen selected-size order, then
`required_final_seeds` order): FinalProductionPlan identities, run and
training-trajectory identities, training-root identities, the complete
per-seed assessment payloads (selected checkpoint, measurements, policy
ancestry and the bound materialization) and the per-binding final publication
payloads. All equal. The width setting appears in none of them.

### 11.4 R4 - incompatible interrupted historical continuation

`tests/test_mlff_p5_replay_target_real_owner.py::test_incompatible_interrupted_historical_continuation_stops_the_collection`.

A new legacy-workspace scenario, `two_size_production_interrupted`, builds a
genuine pre-cutover workspace with the baseline commit's own code: a frozen
**two-size** design, cross-validated by the baseline, whose first frozen size's
production TRAIN2 is interrupted mid-trajectory. Because the baseline's own
production orchestration is serial across sizes, the later size never reaches
production at all, so its position is fresh and runnable under current code.

The interrupted historical root is then made incompatible with current
authority: its persisted realized-preparation ancestry no longer matches what
the current training method reproduces, while the record stays internally
self-consistent, so the failure is the training-equivalence fence and not a
malformed-record rejection.

Driven through the real public `train-production` collection owner, the test
proves:

* rejection with "not training-equivalent", raised by recovery normalization;
* `harness.runs == []` - zero trainer invocations for every sibling position,
  including the other selected size's fresh runnable one;
* no EVAL2 call after the failure, and no `[TRAIN scheduler]` line at all, so
  no scheduler was sized;
* both independently valid Phase-B per-binding FinalProductionPlan pointers
  remain current - recovery failure is not a collection rollback;
* no final-production publication for either size;
* every historical byte preserved: no root added, renamed or removed, no
  pre-existing byte rewritten apart from the incompatibility the test itself
  injected, no completion anchor appended, and no partial reseal.

### 11.5 R5 - a sealed cross-size sibling survives a later wave failure

`tests/test_mlff_production_global_train_scheduler.py::test_a_sealed_sibling_survives_a_later_wave_failure_and_is_not_retrained`.

Four production positions across two selected sizes, with the owned-slot
ceiling set to two so the admission order is deterministic. The bounded
trainer makes the ordering explicit rather than probable: the first admitted
position runs alone and is sealed by the existing completion/topology owner;
the second fails only once it observes that a sibling seal is durable *and*
that another owned position is genuinely active beside it.

On failure the test proves no EVAL2 began, nothing further was admitted
(`admitted_after_failure == []`), the still-active owned sibling was signalled
and reaped before the command returned, exactly one production root is sealed,
and neither size published.

On retry from the same workspace with healthy execution, the sealed sibling
launches no trainer, the three outstanding positions re-enter the scheduler
(`task_count == 3`, `train_required=3; sealed=1`, `progress=0/3`), and normal
frozen-order finalization completes both sizes. No production retry state and
no scheduler-specific completion registry were added; the durable TRAIN2
completion/root authority is the only one used.

### 11.6 Preserved invariants and affected-surface inspection

The complete source change is a single moved block in
`_normalize_final_production_recovery` plus its docstring; everything else in
this cycle is test and non-executable documentation (11.10). Nothing else in
`mdstats/` changed, so the repair widened no architecture. Re-verified on the repaired tree:

* exactly one collection-global TRAIN-only adaptive scheduler; one controller
  and one plan construction site (structural test, green);
* CV selected-size orchestration unchanged (A16, green);
* no EVAL2 while scheduler-owned TRAIN2 work is active (A18, green);
* finalization frozen-size ordered and fail-fast (A14, green);
* FinalProductionPlan ownership per binding, no collection-atomic rollback
  (A13, and R4 above);
* `(campaign generation, ordered binding digests)` admission linearization at
  every TRAIN admission and at finalization admission (A19, green);
* global scheduler `key` absent from scientific identity (structural test);
* deterministic queue/backoff behavior (A9, green);
* sealed roots read-only; terminal-but-unsealed roots sealed only by the
  existing completion/topology owner (A7, green);
* no second scheduler, outer executor, resource controller, currentness
  registry, recovery registry, cross-size reducer or duplicate persistence
  authority;
* no D1/D2 semantic change.

### 11.7 R6 - executed evidence

Environment: conda env `mace`, CPU only, `pytest -p no:randomly`, xdist where
noted. No GPU was used or claimed; the device facts in the scheduler suite are
the existing bounded deterministic telemetry substitution below the P5 owner
boundary.

| Command (all `-p no:randomly`) | Result |
| --- | --- |
| `python -m compileall mdstats tests` | clean, exit 0 |
| `pytest -q tests/test_mlff_production_global_train_scheduler.py -n 8` | **26 passed** (93s) |
| `pytest -q tests/test_mlff_p5_replay_target_real_owner.py -n 8` | **11 passed** (83s) |
| `pytest -q tests/test_mlff_p5_train2_memory_backoff.py tests/test_mlff_p5_train2_zero_safe_admission.py -n 8` | 26 passed, **2 failed** - both pre-existing, see 11.8 |
| `pytest -q tests/test_mlff_target_size_multi_size_integration.py tests/test_mlff_target_size_multi_selection.py -n 8` | **47 passed** (77s) |
| `pytest -q tests/test_mlff_target_size_p5e_production_and_restart.py -n 8` | **27 passed** (127s) |
| `pytest -q tests/test_mlff_replay_mace_p5_execution_recovery.py -n 8` | **6 passed** (49s) |
| `pytest -q tests/test_mlff_campaign_currentness_races.py tests/test_mlff_campaign_assembled_lifecycle.py -n 8` | **5 passed** (61s) |
| `pytest -q tests/test_mlff_storage_reset_integration.py -n 8` | **167 passed** (1465s) |
| `pytest -q tests/test_mlff_*.py -n 16` (complete affected MLFF campaign/training-data CPU regression, 229 files) | 2825 passed, 15 skipped, **184 failed** - all pre-existing, see 11.8 |

Both test files this repair touched are fully green, individually and inside
the complete sweep. No skip in any focused suite hid an acceptance claim.

### 11.8 Failure attribution - no new failure was introduced

The repository carries a large pre-existing CPU failure population on this
branch, so the affected sweep is reported as a **failure-set diff against the
reviewed entry-point commit**, not as a raw count.

| Arm | Result |
| --- | --- |
| repaired `0462f56f` (main checkout) | 184 failed, 2825 passed, 15 skipped |
| entry-point `c4309145` (clean worktree, identical command) | 182 failed, 2819 passed, 18 skipped |

Set difference of the failing node ids:

* **failures present only in the repaired arm: 2**
* **failures fixed relative to the entry point: 0**

Both apparent extras are
`tests/test_mlff_target_size_p6_p5a6_compatibility.py::test_p6_reopens_the_preserved_p5a6_workspace_through_real_owners`
and `::test_corrupted_final_production_plan_m3_is_rejected_by_p2_oracle`, and
they are an artefact of *where* the two arms ran, not of the change. Those
tests are `skipif`-guarded on `qualification/p6-p5a6-compat/workspace/`, which
is gitignored and therefore exists only in the main checkout: the baseline
worktree skipped them (hence its 3 extra skips) while the repaired arm executed
them. Running that file in the **same** main checkout with the entry-point
revision of `campaign_post_selection_runtime.py` restored reproduces both
failures identically (`2 failed, 2 passed`). They are pre-existing and
unrelated to this repair.

**Net effect of the repair on the affected regression: zero new failures, zero
regressions.**

The two focused failures in
`tests/test_mlff_p5_train2_zero_safe_admission.py` -
`test_idle_transient_cuda_admission_blocking_missing_to_missing_fails_explicitly`
and `test_idle_transient_cuda_admission_blocking_waits_rather_than_spins_unsafe_to_safe` -
were likewise reproduced at `c4309145` with identical assertion signatures
(`scheduler must wait on poll interval while idle and admission blocked`, and a
`TrainingResourceObservabilityError` raised while one owned job is active).
They concern idle-poll/telemetry-observability behaviour in
`training_parallel.py`, which this repair does not touch.

No failure in either arm references
`docs/specs/training_data/mlff_post_selection_p5_spec.md` or
`docs/arch_manuals/mlff_training_data/60_execution_performance.md`. The large
`*_specification.py` failure families assert content of the *retired* assembled
architecture document and are outside this cycle's surface.

### 11.9 Production qualification

**Still deferred.** Everything above is deterministic CPU real-owner evidence.
No physical GPU throughput or VRAM qualification was performed or is claimed,
and R2 is explicitly *not* labelled as such: it is owner/resource-contract
evidence. Target-hardware qualification remains part of the final release
package under standing project direction, and no iterative GPU qualification
was requested from the stakeholder during this repair.

### 11.10 Documentation impact

Two current documents were reconciled with the repaired behaviour, both
non-executable:

* `docs/specs/training_data/mlff_post_selection_p5_spec.md` - the D4 normative
  rule that locator resolution needs no exclusion while every classification of
  a production root is taken under that position's existing run-activity lease
  (committed with the repair in `0462f56f`);
* `docs/arch_manuals/mlff_training_data/60_execution_performance.md` - the same
  ownership statement as a D3 bullet in the collection TRAIN-wave section
  (committed with this evidence record).

PDF regeneration follows the repository's existing automated documentation
build path and is not performed by hand here.

### 11.11 Open risk and handoff

* The pre-existing branch failure population (182 failures at the entry point)
  is untouched by this cycle and remains a separate concern; this workplan does
  not adopt it.
* R2's regime limitation is stated in 11.2 and is deliberately not hidden: the
  functional-independence claim is executed, the production-scale magnitude
  question is shown to be unchanged by globalization, and physical
  qualification stays deferred.
* **This workplan remains open.** Section 10.8's closure condition is for an
  independent Review to evaluate against `0462f56f`; nothing here self-closes
  it or declares the D3 candidate accepted-current.
