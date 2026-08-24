# MLFF-END-TO-END-PERF1 Fourth-Reopen Implementation Workplan

Status: **ACTIVE — FUNCTIONAL ACCEPTANCE REOPENED**  
Branch: `feat/mlff-end-to-end-performance-v1`  
Reviewed implementation tip: `514d70a57a3c954bd777c99eee314019107f9ef2`  
Supersedes closeout conclusion only: `MLFF_END_TO_END_PERF1_REOPEN3_IMPLEMENTATION_WORKPLAN.md` section 14  
Date reopened: 2026-08-24

## 1. Authority and purpose

This file is the authoritative active delta-workplan for the fourth MLFF-END-TO-END-PERF1 closeout round.

The parent PERF1 architecture, the second-reopen workplan, and the third-reopen workplan remain authoritative for decisions not explicitly reopened here. The third-round implementation genuinely repaired the prior synthetic-concurrency defect: static operating points now execute worker-private model shells concurrently, recorded concurrency must match observed concurrency, throughput is derived from completed work and wall time, runtime-profile evidence is versioned, and staged EVAL has one outer inference owner.

A subsequent independent software-design review nevertheless found remaining lifecycle defects in the joint optimizer. The defects are narrower than the previous architecture gap but material for resource safety and performance:

1. live RAM/VRAM is not rechecked immediately before every cold-search candidate launch;
2. provider/model-shell construction failure for a higher-concurrency candidate aborts inference instead of making that candidate infeasible while retaining a lower safe point;
3. additional private MACE providers are recreated and destroyed for every calibration and production wave instead of being persistently owned and reused;
4. the operating-point timing/resource boundary does not cleanly distinguish persistent provider residency from steady-state execution cost;
5. generic one-slot CUDA calibration still declares feasibility after the first safe active telemetry sample rather than after the complete first job observation interval;
6. the final third-round acceptance record does not independently establish the explicitly required fresh assembled integration boundary after the final executable changes.

Therefore T-R2A, T-R2B, T-R5, and T-R8 are reopened again. Preserve all unrelated accepted mechanisms and evidence unless a fourth-round change can plausibly affect them. Do not replay closed design work merely because this is another implementation round.

Implementation may proceed gate-by-gate under this plan without another design round unless a genuine redesign trigger in section 11 fires.

## 2. Frozen engineering envelope

All previously accepted scientific and product requirements remain non-negotiable:

- target-size authority, candidate population, seeds, thresholds, ranking/admissibility, verification resolution, precision/dtype policy, and 3 -> 10 -> 30 freeze semantics must not change;
- batch size, model-job concurrency, provider-pool size, runtime profiles, resource evidence, scheduling order, cache state, and OOM ceilings are execution state and must not alter scientific identity;
- optimized execution must remain numerically equivalent to the accepted reference path within frozen tolerances;
- static concurrent inference must use worker-private/model-private mutable calculator state; one mutable MACE shell may never be shared concurrently;
- one canonical static runtime authority remains the sole owner of joint `(batch_size, concurrent_model_jobs)` selection, profile reuse, live re-clamping, and OOM learning;
- recorded `J > 1` evidence remains valid only when `J` independent jobs were actually active concurrently;
- CPU/RAM/VRAM/storage/I/O admission must fail closed when the required next unit of work cannot fit the configured safety envelope;
- live resource changes must be checked at the admission boundary, not merely at an earlier planning boundary;
- model/provider materialization is part of the resource lifecycle and may not escape RAM/VRAM accounting;
- zero currently admissible jobs must remain representable and must terminate cleanly rather than force one job or deadlock;
- provider/model-shell cleanup must be deterministic on success, candidate failure, cancellation, and executor teardown;
- immutable/restart evidence remains authenticated and deterministic;
- full production-scale GPU qualification remains separate from functional acceptance and remains deferred to the final assembled candidate on the target workstation.

The optimization hierarchy remains:

`product capability/correctness/resource fitness > minimum justified system complexity > development economy`

## 3. Accepted work that remains closed

### R0 — command-field hard failure: **CLOSED**

Preserve corrected execution-plan field consumers and command-boundary coverage.

### R1 — scientific-policy/runtime separation: **CLOSED**

Preserve runtime/profile/pool state outside scientific policy and result identity.

### R3B — aggregate staged-pipeline RAM ownership: **CLOSED SUBJECT TO AFFECTED REGRESSION**

Preserve global pipeline-budget enforcement, retained-payload accounting, explicit prepare/inference/finalize reservations, cleanup, and permitted overlap. Fourth-round provider-pool residency must integrate with this accounting where the staged EVAL owner holds multiple private model shells.

### R4 — immutable concurrent publication: **CLOSED**

No publication redesign is authorized absent a new regression.

### R6B — DYN cancellation/resource split: **CLOSED SUBJECT TO AFFECTED REGRESSION**

Preserve simulation -> reduction separation, cancellation propagation, TERM -> KILL process-group cleanup, authenticated receipts, and streaming reduction.

### R7 — RELAX architecture: **CLOSED SUBJECT TO AFFECTED REGRESSION**

No RELAX redesign is authorized absent a new regression.

### Third-round genuine-concurrency repair: **PRESERVE**

Do not regress the following accepted third-round properties:

- actual concurrent execution under `J > 1`;
- worker-private/model-private providers;
- deterministic output ordering;
- evidence validation requiring observed concurrency to equal recorded concurrency;
- throughput arithmetic derived from actual completed structures and actual measured wall time;
- runtime-profile schema/evidence version separation from old synthetic evidence;
- one outer staged-EVAL inference owner rather than nested outer × inner concurrency multiplication;
- DEPLOY/PES/LOCKED pre-model one-job admission;
- canonical static executor usage by reconciled consumers.

## 4. Acceptance evidence retained and invalidated

The third-reopen acceptance record remains useful historical evidence for mechanisms whose establishing dimensions are unchanged. In particular, its scientific equivalence, genuine-concurrency fixture, ordering, profile-v2 rejection of old evidence, DYN cancellation, pipeline accounting, immutable publication, and other unrelated regression results may be reused during stage-local work when not invalidated by a fourth-round edit.

The following claims are specifically invalidated and must be re-established:

- complete one-slot CUDA post-launch feasibility calibration;
- live re-clamping immediately before each joint candidate admission;
- graceful search behavior when provider/model-shell materialization for a candidate fails for RAM/VRAM/OOM reasons;
- model/provider lifecycle efficiency and leak-free reuse across calibration and production waves;
- persisted operating-point resource semantics after provider-pool residency becomes persistent;
- throughput semantics after separating cold materialization from steady-state execution;
- T-R5 consumer/profile acceptance that depends on the revised provider-pool/resource evidence lifecycle;
- T-R8 final functional acceptance and assembled integration.

Do not invalidate unrelated closed evidence merely because the runtime authority changes internally.

## 5. Fourth-closeout findings promoted to implementation requirements

### F1 — cold-search candidates are not admitted against fresh live resources

The third-round authority performs a live re-clamp before cold search and before later production waves, but the cold candidate loop can launch multiple `(B,J)` trials without a fresh admission check immediately before each one. RAM/VRAM can change between trials, especially as private model shells are materialized.

Required outcome: every candidate transition that can increase batch demand, active job count, provider residency, or transient memory must pass fresh live admission immediately before resource acquisition/launch.

### F2 — higher-J provider construction failure aborts instead of degrading to a lower safe point

A candidate can fail while constructing private providers before its concurrent wave begins. The current path cleans partial clones but re-raises the error. Thus a valid measured point such as `(B,2)` can be lost when probing `(B,4)` exceeds VRAM during model construction.

Required outcome: recognized RAM/VRAM/OOM failure while materializing a higher operating point must mark that candidate/range infeasible, clean only attempt-local resources, retain previously measured safe points, prune impossible larger concurrency where justified, and continue/select safely. Non-resource construction failures remain hard errors.

### F3 — private providers are recreated for every calibration and production wave

Actual concurrency currently comes from private provider/model shells, but `J-1` additional shells are created and destroyed for each `_run_joint_wave`. On real MACE this can repeatedly deserialize/model-materialize, transfer to GPU, initialize calculator/backend state, churn the allocator, and dominate wall time.

Required outcome: one canonical static executor owns a persistent, lazily grown private-provider pool for its lifetime. Providers are materialized only when a larger admitted `J` is actually needed, reused across candidate batches and production waves, and closed once when retired or when the executor closes. Do not create a second pool manager beside the canonical executor/authority.

### F4 — resource evidence and timing do not yet match a persistent-pool lifecycle

With a persistent pool, model residency and steady-state execution are different resource/time components. Measuring only a wave-local delta after providers are already resident can understate what a reused runtime profile must pre-admit on a fresh process; including repeated provider construction in every throughput trial would instead misrepresent steady-state performance.

Required outcome: define one explicit, conservative evidence model that supports both safe fresh-process profile reuse and meaningful steady-state operating-point selection.

The frozen preferred representation is:

- **provider-pool residency**: cumulative incremental RAM/VRAM needed to reach and retain pool size `J` from the canonical one-provider baseline;
- **steady-state execution peak**: incremental RAM/VRAM above the fully resident `J`-provider pool while executing `(B,J)`;
- **aggregate point requirement**: a conservative combination of persistent residency plus transient execution demand used for fresh-process/profile admission;
- **steady-state throughput**: completed structures divided by wall time for the concurrent prediction wave after the required provider pool is resident and immediately before/through completion synchronization of that wave;
- **cold pool materialization cost**: execution-only diagnostic/calibration overhead, not silently folded into steady-state throughput, but retained where useful to avoid pathological search cost and measured separately during final target qualification.

An equally simple representation is allowed only if it preserves these semantics without ambiguity. If persisted profile fields change meaning, bump/version the runtime-profile evidence schema again; do not reinterpret v2 bytes silently.

### F5 — one-slot CUDA calibration still closes on the first safe sample

The third-round patch removed the unconditional `maximum_jobs <= 1` calibration bypass, but then finalizes one-slot calibration on the first active telemetry sample. That sample may precede a transient peak later in the same job.

Required outcome: a one-slot ceiling disables promotion above one but does not establish one-job feasibility until the first admitted job's observation interval is complete, unless an equivalent authoritative execution-region peak source proves the complete job envelope. The controller must retain the maximum relevant observed demand across the first job, finalize at the job-completion boundary, and block replacement work if that complete-job evidence is unsafe.

## 6. Gate F-R2A — complete-first-job one-slot admission semantics

Implement this before changing the persistent static pool so generic scheduler semantics are correct independently of static MACE details.

### Required behavior

1. For CUDA plans with `maximum_jobs == 1`, begin calibration when the first admitted job starts but do not mark calibration complete merely because one safe sample arrives.
2. Retain the relevant maximum incremental VRAM and GPU-utilization evidence across the complete first job observation interval.
3. Finalize one-slot calibration at the explicit first-job completion transition, or from an authoritative complete execution-region peak measurement that is at least as conservative.
4. If complete-job evidence proves one job outside the configured VRAM/resource envelope, set zero future admission before any replacement is launched.
5. If the first job fits, remain at one without waiting for the multi-job promotion stability window.
6. If no reliable active telemetry sample was captured, use the existing conservative configured/fallback estimate; do not fabricate a zero-cost job.
7. Live external/baseline RAM/VRAM changes after calibration must still block the next launch when one job no longer fits.
8. Preserve multi-job CUDA calibration behavior unless a shared helper must be refactored to express the completion boundary cleanly.

### Focused regression

- one-slot first sample safe, later sample unsafe, then job completes -> zero future admission and no replacement launch;
- one-slot first sample safe, later transient/peak sample safe, job completes -> calibration closes at one and queued work proceeds;
- one-slot job completes with no retained active sample -> conservative fallback is used, not zero demand;
- replacement cannot launch between first-job completion and calibration finalization;
- complete-job unsafe outcome cannot deadlock the queue;
- post-calibration live baseline increase still blocks future admission;
- existing multi-job calibration and CPU scheduler regression remain clean.

### Gate acceptance

F-R2A closes only after the focused bug reproducers and complete affected scheduler/CLI regression pass.

---

## 7. Gate F-R2B — persistent provider pool + admission-safe joint search

This is the central fourth-round implementation gate.

### 7.1 Ownership contract

`StaticInferenceRuntimeAuthority` remains the sole operating-point policy owner. `StaticMaceInferenceExecutor` remains the sole model-shell execution owner. Implement persistent provider reuse inside that ownership boundary; do not add another scheduler, provider registry, or optimization authority.

The executor must own:

- provider slot 0: the existing canonical provider;
- lazily materialized private provider slots `1..J-1`;
- the current resident pool size;
- cleanup/retirement of surplus providers;
- per-wave use of those stable worker-private providers;
- pool residency observations needed by the runtime authority.

The authority must own:

- bounded candidate `(B,J)` enumeration/order;
- fresh resource admission before pool growth and wave launch;
- safe/infeasible evidence;
- monotonic pruning where measured evidence proves larger J cannot fit;
- selected point;
- compatible profile reuse;
- live re-clamping;
- OOM safe batch ceiling.

### 7.2 Candidate-search order and pool growth

Prefer an order that avoids repeated provider churn:

1. evaluate bounded batch candidates at `J=1` using the base provider;
2. if justified and live-admissible, grow the provider pool to the next bounded concurrency candidate;
3. evaluate relevant batch candidates at that `J` using the already resident pool;
4. grow monotonically through concurrency candidates while safe;
5. once cold search selects a point, retire surplus providers once if the selected `J` is lower than the largest successfully materialized pool;
6. reuse the selected resident pool for all subsequent production waves.

Equivalent ordering is acceptable only if it provides the same bounded construction count and does not repeatedly destroy/recreate providers.

### 7.3 Fresh admission before every material transition

Immediately before each operation that can increase resource demand:

- refresh live host RAM;
- refresh live VRAM/free-device evidence when CUDA is active;
- combine current persistent pool residency, candidate pool-growth demand, and candidate transient execution demand conservatively;
- reject/defer the candidate before provider creation/wave launch if the next step does not fit.

A profile-reused point must undergo the same fresh admission before its provider pool is materialized.

### 7.4 Resource-failure semantics

Recognize resource failures at both stages:

- provider/model-shell materialization;
- concurrent prediction wave.

For a recognized candidate-specific RAM/VRAM/OOM failure:

1. stop the candidate;
2. close only newly created attempt-local providers that were not part of the previously safe persistent pool;
3. release allocator/cache state where the existing runtime policy permits;
4. record explicit infeasible evidence or an equivalent authoritative infeasible boundary;
5. preserve previously measured safe evidence;
6. prune larger `J` for the same or more demanding resource state when monotonicity is justified;
7. continue/select the best remaining safe point.

Do not swallow non-resource exceptions, malformed model errors, scientific/model incompatibility, or provider construction failures unrelated to resource exhaustion.

A failure of `(B,J_high)` must not abort a valid `(B,J_low)` result unless no safe operating point remains.

### 7.5 Persistent-pool cleanup

- every non-base private provider is closed exactly once;
- partial pool-growth failure leaves the last accepted pool intact;
- executor cancellation/failure closes owned private providers;
- normal executor close closes the pool;
- no private provider survives beyond the owning executor;
- the caller-owned base provider retains its existing ownership semantics;
- if the executor owns the base provider, it closes it exactly once after private providers are retired.

### 7.6 Required focused regression

Use cheap deterministic providers; no real GPU production run is required.

- provider factory call count demonstrates private providers are materialized at most once per retained slot, not once per wave;
- several production waves at selected `J > 1` perform no additional provider construction after the pool is established;
- cold search with several batch candidates reuses the same `J`-provider pool;
- selected `J` lower than maximum explored `J` retires surplus providers once and keeps the selected pool resident;
- partial provider construction failure at `J=4` after safe `J=2` cleans partial slots, marks/prunes the high-J point, and completes using `J=2` rather than aborting;
- non-resource provider construction failure still propagates as a hard error;
- live RAM/VRAM shrink between candidate trials prevents the next candidate from launching;
- resource shrink while a safe lower pool is resident causes selection/re-clamp rather than unsafe growth;
- `J > 1` still records actual observed concurrency `J` and never shares one mutable shell;
- deterministic result ordering remains identical;
- OOM batch backoff remains bounded and updates the canonical learned batch ceiling;
- no provider leak on success, OOM, ordinary exception, cancellation, or executor teardown.

### Gate acceptance

F-R2B is not accepted until focused tests plus affected static-inference, profile, staged-EVAL, resource-ledger, and consumer regression pass.

---

## 8. Gate F-R2C — runtime evidence/profile semantics for persistent pools

This gate may be implemented together with F-R2B if the code is one coherent executable change, but its acceptance requirements remain explicit because persistence safety is distinct from pool mechanics.

### Required evidence semantics

For each measured `(B,J)` point, persist enough execution-only evidence to establish safely:

1. the selected batch and actually realized concurrency;
2. completed structures and steady-state joint elapsed time;
3. steady-state throughput = completed structures / steady-state elapsed time;
4. cumulative incremental resident RAM/VRAM required by the persistent `J`-provider pool relative to the defined baseline;
5. incremental execution peak above that fully resident pool;
6. conservative aggregate RAM/VRAM requirement for materializing/reusing that point on a fresh compatible process/device;
7. feasibility/failure classification and learned batch ceiling where relevant.

Do not use process-lifetime high-water marks as point-local working memory. Do not subtract baselines in a way that loses provider residency on profile reuse. Do not allow an already-grown larger pool to make a smaller-J candidate appear to require the larger pool; search ordering/measurement must keep point semantics interpretable.

### Timing boundary

Steady-state operating-point elapsed time must begin only after the required `J` provider shells are ready and admitted, and must include the complete concurrent inference wave through device synchronization/observable completion. It must not stop before mandatory synchronization that determines when the result is actually available.

One-time provider materialization/initialization is not part of steady-state throughput when the provider pool is persistent. If materialization duration is retained, label it explicitly as cold-start execution cost. Do not mix cold construction time into some operating points but not others under the same throughput field.

### Profile versioning

If the existing v2 fields cannot express the corrected provider-residency + steady-state-peak semantics without changing their meaning, write a new runtime-profile schema/evidence-semantics version. Old v2 profiles must then be deterministically rejected/rebuilt by the owning profile layer. Scientific policy/result schemas remain unchanged.

### Required regression

- two consecutive waves at the same selected point reuse the same provider pool and produce comparable steady-state timing semantics;
- profile aggregate resource requirement includes extra private-provider residency for `J > 1`;
- fresh compatible profile reuse pre-admits enough RAM/VRAM to materialize the selected pool before launching inference;
- insufficient live resources reject/re-clamp a compatible profile before unsafe pool growth;
- old evidence semantics are rejected/rebuilt if version changes;
- a smaller-J point is not polluted by residency from previously explored larger J;
- throughput arithmetic remains completed structures / complete synchronized steady-state wave time;
- scientific policy/result identity is byte-for-byte unchanged by runtime pool/profile state where existing tests expose it.

---

## 9. Gate F-R5 — consumer and staged-resource reconciliation

After F-R2A/F-R2B/F-R2C stabilize, reconcile affected consumers without creating a new architecture.

### Required behavior

1. EVAL, DEPLOY, PES, LOCKED-TEST2, replay pseudo-labeling where applicable, and every other static-MACE consumer discovered by impact analysis continue to use the canonical static executor/runtime authority.
2. DEPLOY/PES/LOCKED pre-model one-job admission remains before base model construction/device transfer.
3. When a consumer permits `J > 1`, fresh admission must include persistent private-provider pool growth before those extra models are materialized.
4. Staged EVAL's inference working-memory reservation must remain conservative for the maximum model-job pool that the inner authority may materialize; if actual pool residency becomes available dynamically, accounting may tighten but must not under-reserve.
5. Runtime-profile reuse must not bypass the staged/global RAM ledger or live VRAM admission.
6. One outer staged-EVAL inference owner remains; do not restore outer × inner nested model concurrency.
7. Replay or other fixed-batch consumers that intentionally remain `J=1` must not acquire unnecessary provider-pool complexity.
8. Preserve sparse reads, graph-cache validity, checkpoint/head semantics, deterministic ordering, restart behavior, and external LAMMPS resource ownership.
9. Remove obsolete per-wave provider factory/reload helpers and stale evidence paths once the persistent pool is authoritative.

### Required regression

- real staged-EVAL boundary shows one outer inference owner and persistent inner provider pool;
- staged RAM reservation is not lower than the admitted provider-pool envelope;
- DEPLOY/PES/LOCKED initial infeasibility still fails before base model construction;
- post-base-model live shrink blocks private-pool expansion before clone construction;
- profile-reused command path cannot materialize more providers than live resources admit;
- safe command paths preserve numerical/reference parity;
- replay/fixed-J=1 paths remain simple and regression-clean;
- no direct provider prediction/admission bypass is introduced;
- no duplicate batch/concurrency/provider-pool authority remains.

---

## 10. Gate F-R8 — final affected-surface regression and assembled acceptance

After all fourth-round executable edits:

1. independently re-derive the complete affected behavioral surface from the assembled branch tip;
2. include static inference, provider construction/cleanup, runtime profiles, live telemetry, adaptive scheduler completion transitions, staged EVAL resource accounting, DEPLOY/PES/LOCKED, replay/static consumers, CLI/config, restart/profile reuse, and every transitive caller changed by the new provider lifecycle;
3. include R3B/DYN/RELAX only where shared scheduler/resource code makes them plausibly affected; do not rerun unrelated expensive qualification;
4. search source for:
   - per-wave `from_model_path`/provider-factory creation inside the production joint-wave loop;
   - duplicate provider pools or duplicate joint operating-point authorities;
   - candidate launches without immediate live admission/re-clamp;
   - resource-construction exceptions that abort despite a retained lower safe point;
   - first-safe-sample one-slot calibration completion;
   - persisted profile fields whose memory/timing semantics no longer match their schema;
   - synthetic concurrency multipliers;
   - mutable model-shell sharing;
   - provider cleanup leaks/double-close paths;
   - direct consumer admission bypasses;
5. run focused tests for every new mechanism;
6. run a fresh complete affected-surface regression after the final executable edit;
7. run a **separate fresh bounded assembled production-interface integration** through the real available campaign boundaries, covering at minimum the available chain of preflight -> preparation/materialization -> TRAIN/EVAL -> DEPLOY -> PES -> RELAX -> DYN -> selection/publication;
8. the assembled integration must exercise the production orchestration/resource authority rather than reconstructing it in the harness; heavyweight dependencies may be stubbed only below the real public/production boundary;
9. rerun restart/profile reuse integration and relevant failure/cancellation paths;
10. confirm R0/R1/R3B/R4/R6B/R7 and LOCKED isolation remain regression-clean;
11. run broader/full available repository tests when final impact cannot be bounded confidently; triage every failure/error plausibly intersecting the changed surface;
12. record genuinely unavailable checks explicitly. Unavailable required functional checks are not passes.

### Final functional acceptance invariants

PERF1 cannot return to functional-accepted status unless the final candidate demonstrates all of the following:

- one-slot CUDA feasibility is based on the complete first-job observation boundary, not the first safe sample;
- no replacement launches after complete-job evidence proves one job unsafe;
- every resource-increasing joint-search transition receives fresh RAM/VRAM admission;
- failure to materialize a higher-J provider pool for resource reasons degrades to a lower measured safe point when one exists;
- private providers are persistent and reused across calibration batches and production waves rather than recreated per wave;
- every private provider is owned and closed exactly once;
- selected `J > 1` still means `J` actually concurrent independent model shells;
- runtime-profile resource evidence includes both persistent provider residency and steady-state transient demand conservatively enough for fresh-process reuse;
- steady-state throughput measures complete synchronized prediction-wave wall time and does not mix inconsistent cold construction semantics;
- compatible profiles are live-reclamped before provider-pool materialization and prediction;
- staged EVAL accounting remains conservative for the inner pool and does not restore nested concurrency multiplication;
- scientific identity and frozen outputs remain unchanged;
- fresh affected regression passes;
- a separate fresh bounded assembled integration pass succeeds on the same final candidate;
- production-scale target-GPU qualification remains deferred.

## 11. Genuine redesign triggers

Stop dependent implementation and reopen only the affected design surface if evidence shows that:

- persistent worker-private MACE providers cannot safely coexist within the intended resource envelope even at useful `J > 1`, making true concurrent model shells globally inferior to a different concurrency strategy;
- representative bounded measurement shows provider-pool materialization/reuse fundamentally conflicts with safe graph/cache/head/model isolation;
- a safe profile cannot represent persistent provider residency plus transient execution demand without replacing the broader runtime resource model;
- one canonical static authority cannot serve EVAL and static verification consumers without materially incompatible provider-lifecycle semantics;
- correct complete-job CUDA calibration requires replacing the generic scheduler ownership model rather than adding a clear completion transition;
- scientific outputs change outside frozen tolerances under persistent private providers;
- implementation expands into a new architectural subsystem outside PERF1.

The following are **not** redesign triggers: ordinary bugs, adding a provider pool inside the canonical executor, runtime-profile schema bump/rebuild, candidate pruning, resource-exception classification, cleanup fixes, timing-boundary corrections, completion callbacks, test additions, or deletion of stale helpers.

## 12. Expected fourth-round affected surface

At minimum inspect and test:

- `mdstats/training_data/model_features.py` — joint authority, static executor, provider pool, resource monitor/profile evidence;
- `mdstats/training_data/inference_parallel.py` — one-slot complete-job calibration and admission state;
- `mdstats/training_data/campaign_execution.py` — static EVAL provider factory/profile/runtime wiring;
- `mdstats/training_data/_campaign_cli_core.py` — staged EVAL completion/admission/resource reservations;
- `mdstats/training_data/deploy_verify.py` and PES/LOCKED static consumers;
- `mdstats/training_data/replay_pseudolabel.py` and other static-executor callers if the executor lifecycle changes their behavior;
- public exports if runtime-profile schema/classes change;
- runtime-profile persistence/cache directories and compatibility-key construction;
- `tests/test_mlff_static_mace_inference.py`;
- `tests/test_mlff_inference_parallel_scheduler.py`;
- `tests/test_mlff_opt_eval4_staged_evaluation_pipeline.py`;
- command-boundary/DEPLOY/PES/LOCKED tests;
- restart/profile-reuse tests;
- DYN/RELAX/resource tests only where shared code is affected;
- all additional consumers discovered by final impact analysis.

Do not treat this list as a hard boundary.

## 13. Stage-local regression rule

Every material fourth-round executable gate must close with:

1. cheapest high-signal focused tests for the changed mechanism;
2. regression for all old behavior plausibly affected by that gate;
3. real consumer/orchestration integration where the change crosses a product boundary.

Do not defer all regression to F-R8. Reuse third-round evidence only when the behavior it established is unchanged. After all material executable changes, final affected-surface regression and the separate assembled integration must both be fresh.

## 14. Production qualification boundary

Do **not** perform full production-scale GPU qualification during F-R2A through F-R8.

After functional F-R8 acceptance, retain the existing target-workstation qualification handoff. The final target-machine run should characterize at least:

- cold base-provider and private-provider pool materialization cost;
- selected `(batch_size, concurrent_model_jobs)` and alternatives considered;
- steady-state joint throughput and dispersion;
- persistent RAM/VRAM residency for the selected provider pool;
- transient execution peak and resulting headroom;
- pool growth/re-clamp behavior;
- compatible-profile cold/warm reuse behavior;
- CPU/native-thread utilization and nested-parallelism control;
- LAMMPS/DYN overlap where relevant;
- disk/I/O/cache/restart footprint;
- per-stage and end-to-end wall time.

No target-hardware performance claim is accepted before that qualification. Production qualification cannot substitute for missing functional regression or integration.

## 15. Withdrawn third-reopen acceptance record

The third-reopen section-14 acceptance record remains in Git history and in the prior workplan as historical evidence, but its **T-R2A/T-R2B/T-R5/T-R8 closeout conclusion is withdrawn by this fourth independent review**.

The third-round repair of synthetic concurrency remains accepted as a mechanism and must be preserved. R0/R1/R3B/R4/R6B/R7 remain closed as stated above unless fourth-round regression produces contrary evidence.

## 16. Completion condition

Return MLFF-END-TO-END-PERF1 to **FUNCTIONAL IMPLEMENTATION ACCEPTED — TARGET-WORKSTATION GPU QUALIFICATION DEFERRED** only when:

- F-R2A, F-R2B, F-R2C, F-R5, and F-R8 are accepted;
- R0, R1, R3B, R4, R6B, and R7 remain regression-clean;
- complete-first-job one-slot calibration is fail-closed;
- per-candidate live admission is enforced;
- higher-J resource/materialization failure cannot destroy a retained lower safe point;
- private provider/model shells are persistently owned and reused, not reconstructed per wave;
- provider cleanup is exact on every exit path;
- persistent residency and steady-state transient resource evidence have explicit safe profile semantics;
- actual concurrent execution remains the basis of every `J > 1` datum;
- static consumers and staged EVAL remain on the single canonical authority without nested concurrency or admission bypass;
- final affected-surface regression is fresh and passes;
- a distinct fresh bounded assembled production-interface integration passes on the same candidate;
- unavailable checks are explicitly recorded;
- full target-workstation GPU qualification remains deferred as a separate final handoff.
