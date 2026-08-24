# MLFF-END-TO-END-PERF1 Third-Reopen Implementation Workplan

Status: **ACTIVE — FUNCTIONAL ACCEPTANCE REOPENED**  
Branch: `feat/mlff-end-to-end-performance-v1`  
Supersedes closeout status only: `MLFF_END_TO_END_PERF1_REOPEN_IMPLEMENTATION_WORKPLAN.md` section 14 acceptance record  
Date reopened: 2026-08-24

## 1. Authority and purpose

This file is the authoritative active delta-workplan for the next MLFF-END-TO-END-PERF1 closeout round.

The parent PERF1 architecture and the second-reopen workplan remain authoritative for all decisions not explicitly reopened here. The second-reopen implementation materially repaired persistence, pipeline RAM accounting, DEPLOY/PES admission, DYN cancellation, and several scheduler/resource gaps. A subsequent independent software-design closeout review found that the central R2 static-inference operating-point implementation still does not satisfy the accepted joint-optimization contract and that one-slot CUDA stages can bypass measured one-job infeasibility.

Therefore the prior statement that R2A/R2B/R8B are functionally accepted is withdrawn. Preserve unrelated accepted work and evidence. Do not replay closed design work unless a changed dimension below plausibly invalidates it.

Implementation may proceed gate-by-gate under this plan without another design round unless a redesign trigger in section 10 fires.

## 2. Frozen engineering envelope

All previously accepted scientific and product constraints remain frozen:

- scientific target-size authority, candidate population, seeds, thresholds, ranking/admissibility, verification resolution, precision/dtype, and 3 -> 10 -> 30 freeze semantics must not change;
- batch size, concurrent model jobs, cache/profile state, queueing, scheduling, and runtime resource evidence remain execution state and must not alter scientific identity;
- optimized execution must remain numerically equivalent to the accepted reference path within existing tolerances;
- immutable/restart evidence remains authenticated and deterministic;
- CPU/RAM/VRAM/storage/I/O admission must fail closed when one required work unit cannot fit the configured safety envelope;
- zero currently admissible jobs must be representable without forcing one job or deadlocking;
- concurrent static inference must use worker-private/model-private mutable execution state; no unsafe model-shell sharing is authorized;
- runtime operating-point evidence used for future admission/selection must describe work that was actually executed and resources actually observed;
- full production-scale GPU qualification remains separate from functional acceptance and remains deferred to the final assembled candidate on the target workstation.

Optimization hierarchy remains:

`product capability/correctness/resource fitness > minimum justified system complexity > development economy`

## 3. Accepted work that remains closed

### R0 — command-field hard failure: **CLOSED**
Preserve the corrected `InferenceExecutionPlan.selected_batch_size` consumers and real command-boundary coverage.

### R1 — scientific-policy/runtime separation: **CLOSED**
Preserve scientific identity independence from runtime batch/concurrency/cache/profile state and historical scientific-policy compatibility.

### R3B — aggregate staged-pipeline RAM ownership: **CLOSED SUBJECT TO AFFECTED REGRESSION**
No redesign is authorized absent a new failing invariant. Preserve global pipeline-budget enforcement, explicit worker-domain reservations, reservation cleanup, and permitted EVAL/DYN overlap.

### R4 — immutable concurrent publication: **CLOSED**
Preserve no-clobber identical reuse/conflict failure and attempt-local cleanup semantics.

### R5B — DEPLOY/PES pre-model resource admission: **LOCALLY CLOSED, TRANSITIVELY AFFECTED BY R2**
The direct admission bypass was repaired. DEPLOY/PES/LOCKED static prediction must remain routed through the canonical static runtime authority, but their acceptance must be rerun after that authority changes.

### R6B — DYN cancellation/resource split: **CLOSED SUBJECT TO AFFECTED REGRESSION**
Preserve simulation -> reduction separation, shared cancellation propagation, process-group TERM -> KILL cleanup, receipt semantics, streaming reduction, and bounded handoff.

### R7 — RELAX architecture: **CLOSED SUBJECT TO AFFECTED REGRESSION**
No RELAX redesign is authorized unless a regression appears.

## 4. Acceptance evidence retained but invalidated where necessary

The second-reopen acceptance record is retained as historical evidence for unchanged behavior, including its focused resource/pipeline/cancellation tests and bounded assembled integration.

The following claims are specifically invalidated and must be re-established:

- R2A measured/live one-job CUDA infeasibility for stages whose configured maximum concurrency is one;
- R2B "joint" `(batch_size, concurrent_model_jobs)` operating-point optimization;
- R2B persisted operating-point throughput/resource evidence when concurrency was not actually executed at the recorded level;
- R2B point-local peak RAM/VRAM evidence semantics;
- any R5B consumer acceptance that depends on the old R2 runtime authority/profile semantics;
- R8B final acceptance.

Do not discard still-valid regression evidence for unrelated behavior, but every executable gate below requires fresh stage-local affected regression and final assembled acceptance requires fresh final regression/integration.

## 5. Third-closeout findings promoted to implementation requirements

### T1 — CUDA `maximum_jobs == 1` bypasses measured one-job infeasibility

The adaptive controller treats a one-job concurrency ceiling as already calibrated. A workload can therefore pass the initial estimate, execute one real CUDA job above the configured VRAM envelope, and never transition to zero future admission because measured calibration is skipped when promotion above one is impossible.

Required outcome: `maximum_jobs == 1` means "never promote above one," not "skip measurement." The first real job must still establish post-launch resource feasibility. If measured evidence proves one job unsafe, no replacement work may launch and the scheduler must terminate with an actionable resource error.

### T2 — the current R2B authority is not a genuine joint optimizer

The runtime authority can explore batch size while model-job concurrency remains selected by an outer controller. Operating-point evidence can be tagged with `concurrent_model_jobs = N` even when the executor itself ran serially, and throughput can therefore reflect a synthetic concurrency multiplier rather than actual simultaneous execution.

Required outcome: one canonical owner must select among **actually measured** safe `(batch_size, concurrent_model_jobs)` operating points. A point with concurrency `N > 1` is valid only when `N` independent admitted model jobs were actually executed concurrently under the measured aggregate resource envelope. Synthetic multiplication of serial throughput is not operating-point evidence.

### T3 — persisted "peak" resource evidence is not sufficiently point-local

Post-provider VRAM sampling may miss transient allocation peaks, while process-lifetime `ru_maxrss` can carry an unrelated earlier RAM high-water mark into later operating points.

Required outcome: operating-point evidence used for profile selection/admission must use conservative measurements attributable to the evaluated point or a clearly conservative aggregate envelope. Existing persisted profiles whose evidence semantics cannot be trusted under the corrected definition must be versioned/invalidate-rebuilt through the owning runtime-profile layer.

## 6. Gated implementation sequence

### T-R2A — one-slot measured safety and evidence-schema correction

Implement first because the joint optimizer must build on correct resource semantics.

#### Required behavior

1. CUDA jobs must be observed for post-launch feasibility even when configured/planned maximum concurrency is exactly one.
2. A one-job ceiling prevents promotion above one but does not mark calibration complete before real evidence exists.
3. If the first measured job demonstrates that one-job VRAM or RAM demand breaches the configured safety envelope, set zero future admission and fail cleanly after owned in-flight cleanup; never launch a replacement.
4. Live external/baseline RAM or VRAM changes that make the next one-job launch infeasible must block that launch.
5. Preserve healthy already-running work unless immediate termination is required for safety; the primary contract is future admission.
6. Collect point-local/conservative resource evidence:
   - for CUDA, measure execution-region peak allocation/residency with an appropriate allocator peak primitive and/or sufficiently conservative live telemetry spanning the provider execution interval;
   - for RAM, measure a point/job-local baseline-to-peak working-set contribution or another bounded conservative aggregate rather than treating process-lifetime `ru_maxrss` as a point-local peak;
   - document which quantity each persisted field means so profile admission compares like with like.
7. If the corrected evidence meaning is incompatible with the current runtime-profile wire schema/compatibility digest, bump/version that runtime evidence or force deterministic owner-level rebuild. Do not silently reuse synthetic/old-semantic evidence as corrected evidence.
8. Scientific policy/result identity remains unchanged.

#### Focused regression

- `maximum_auto_jobs=1`: initial estimate fits, measured CUDA peak exceeds envelope -> zero future admission + actionable error;
- `maximum_auto_jobs=1`: measured job fits -> stage remains admissible at one and completes normally;
- live baseline rises after a valid one-job measurement -> next launch blocked;
- no zero-capacity deadlock;
- point-local RAM evidence does not inherit an unrelated earlier process high-water mark;
- CUDA peak fixture catches a transient peak that post-operation steady-state sampling alone would miss;
- old-semantic runtime profile is rejected/rebuilt deterministically if a schema/evidence-version transition is required;
- scientific policy digest/reference outputs unchanged.

#### Gate acceptance

T-R2A closes only after focused tests plus affected scheduler/profile/persistence/static-inference regression pass.

---

### T-R2B — genuine joint static-inference operating-point authority

This is the central remaining PERF1 architecture gate.

#### Ownership contract

There must be one production static-inference runtime authority that jointly owns:

- candidate/active batch size;
- candidate/active concurrent model-job count;
- worker-private model-shell admission;
- one-job and aggregate RAM/VRAM safety;
- measured throughput and point-local/conservative resource evidence;
- compatible runtime-profile reuse;
- live RAM/VRAM re-clamping;
- executor-local OOM safe-ceiling feedback.

Existing executor and adaptive-scheduler helpers may remain implementation mechanisms, but neither may independently choose a conflicting batch/concurrency operating point outside the canonical authority.

#### Actual-measurement contract

1. An operating point `(B, J)` is measurable/eligible only if up to `J` independent admitted model jobs are actually run concurrently with batch size `B` on representative queued work.
2. Do not share a mutable MACE/model shell concurrently across workers. Use worker-private/model-private execution state or the already accepted safe ownership model.
3. Throughput must be measured from real completed structures over real wall time for the joint trial; do not multiply serial throughput by `J`.
4. Aggregate RAM/VRAM evidence must cover the concurrent trial, including model/provider residency relevant to that operating point.
5. If queued work is insufficient to exercise a candidate `J`, that point remains unmeasured; do not fabricate evidence. Selection may conservatively use the best measured admissible point.

#### Bounded search/selection contract

1. Start from a safe bounded cold point.
2. Batch candidates remain bounded/geometric plus learned safe limits up to `maximum_inference_batch_size`; do not scan every integer.
3. Concurrency candidates remain bounded by task count, CPU, RAM, VRAM, configured limits, and the target stage's semantics.
4. Explore enough of the two-dimensional space to distinguish material batch/concurrency tradeoffs. A nested implementation is acceptable only if it produces genuine measurements for the tested `(B, J)` combinations and one authority owns the final choice.
5. Selection maximizes measured safe throughput subject to the configured resource envelope. For near-equivalent throughput, prefer lower resource use / lower concurrency / simpler operating point.
6. OOM halving remains a local safety mechanism. Its learned safe batch ceiling feeds the canonical authority and cannot become a hidden independent policy.
7. Live RAM/VRAM is rechecked before every future admission; a persisted or freshly selected point may be reduced or invalidated when the envelope shrinks.
8. Profile compatibility remains conservative across hardware, device, dtype/head, model identity, provider/graph/cache behavior, workload shape, and evidence-semantics version.
9. Runtime profile identity remains outside scientific identity.
10. Remove or demote obsolete synthetic-concurrency evidence fields/paths so there is one active authority and one definition of measured operating-point evidence.

#### Required regression

- deterministic synthetic joint fixture where `(B=8,J=2)` is truly fastest and is selected only after two concurrent jobs were actually exercised;
- fixture where larger `J` is slower or resource-unsafe and a smaller `J` wins;
- fixture where a batch above 8 is selected when genuinely faster/safe;
- fixture where a smaller batch is retained when larger batches regress throughput or violate resources;
- assertion that recorded `concurrent_model_jobs=J` corresponds to observed maximum simultaneous active jobs `J` during that trial;
- assertion that measured throughput equals real completed work / joint wall time and is not a serial-throughput multiplier;
- aggregate resource evidence grows/changes consistently when multiple model jobs are truly resident;
- deterministic output ordering under out-of-order completion;
- OOM backoff remains bounded and later candidate selection respects the learned ceiling;
- compatible corrected-semantic profile reuse avoids unnecessary cold search while still live-reclamping resources;
- stale/incompatible/old-semantic profile is ignored/rebuilt;
- one-job-only stages still use the same authority and close under T-R2A semantics;
- scientific/reference energy/force/stress outputs remain equivalent within frozen tolerances;
- code search/review confirms one active batch/concurrency operating-point authority and no synthetic concurrency evidence path.

Functional testing may use deterministic synthetic providers/telemetry and bounded CPU concurrency. **Do not run full target-GPU throughput qualification in this gate.**

---

### T-R5 — consumer/profile reconciliation after the R2 authority change

This is primarily integration and deletion/consolidation, not a new architecture search.

#### Required behavior

1. DEPLOY, PES, LOCKED-TEST2, EVAL, and any other static-MACE consumer must use the corrected canonical authority.
2. DEPLOY/PES pre-model one-job live RAM/VRAM admission remains before model construction/device transfer.
3. One-job command paths must still perform post-launch measurement and zero-future-admission handling when more prediction work remains.
4. Reuse only corrected-semantic compatible runtime profiles.
5. Remove stale adapters, duplicate outer/inner selection logic, or compatibility paths made obsolete by T-R2B.
6. Preserve sparse reads, graph reuse, deterministic ordering, probe/scientific identity, target-head semantics, and external LAMMPS resource ownership.

#### Required regression

- command-level DEPLOY/PES/LOCKED boundaries reach the corrected authority;
- initial one-job infeasibility fails before model construction;
- post-first-job measured infeasibility prevents later static predictions from launching;
- safe conditions preserve numerical parity and deterministic ordering;
- EVAL uses genuine joint point selection when enough concurrent work exists;
- runtime-profile evidence remains execution-only;
- no direct admission/selection bypass remains except lower-level APIs explicitly documented as caller-owned admission surfaces.

---

### T-R8 — final affected-surface regression and assembled acceptance

After T-R2A/T-R2B/T-R5 are complete:

1. Re-derive the complete affected behavioral surface from the assembled source rather than reusing the old list mechanically.
2. Include direct and transitive callers of static inference, adaptive scheduling, resource telemetry, runtime-profile persistence, execution-plan persistence, EVAL, DEPLOY, PES, LOCKED, DYN where shared scheduler/resource code intersects, RELAX if shared static inference/resource code intersects, public exports, config, CLI, restart/cache paths, and tests.
3. Search for:
   - synthetic concurrency multipliers or evidence tagged with unexecuted job counts;
   - duplicate batch/concurrency authorities;
   - `maximum_jobs==1` calibration bypasses;
   - process-lifetime RAM high-water values represented as point-local profile peaks;
   - post-operation-only VRAM samples represented as execution peaks without conservative justification;
   - obsolete runtime-profile schemas/compatibility paths;
   - direct static consumer admission bypasses.
4. Run focused tests for every new mechanism.
5. Run fresh complete affected-surface regression.
6. Run bounded production-interface integration through the real available preflight -> preparation/materialization -> TRAIN/EVAL -> DEPLOY -> PES -> RELAX -> DYN -> selection/publication boundaries.
7. Re-run restart/profile reuse paths affected by persistence changes.
8. Re-run cancellation/failure tests wherever shared scheduler changes could affect them; do not rerun unrelated production qualification.
9. Confirm R3B, R4, R6B, R7 and LOCKED isolation remain regression-clean.
10. Run repository-required broader/full available checks if final impact cannot be confidently bounded; triage every failure/error plausibly intersecting the changed surface.
11. Record genuinely unavailable required functional checks. Unavailable is not a pass.

A harness may stub heavyweight dependencies below the real production/public boundary, but it must not reconstruct the resource/operating-point authority being tested.

## 7. Functional acceptance invariants

This workplan may return to functional-accepted status only when the assembled candidate demonstrates all of the following:

- one-job CUDA stages still measure actual post-launch resource feasibility even when concurrency cannot exceed one;
- measured one-job infeasibility produces zero future admission and no deadlock/replacement launch;
- recorded operating-point concurrency equals concurrency actually executed;
- joint throughput is measured from real concurrent work and wall time, not inferred by multiplying serial throughput;
- batch size and model-job concurrency have one canonical owner and are selected as one operating point;
- operating-point RAM/VRAM evidence is point-local or conservatively aggregate and semantically documented;
- old/synthetic evidence cannot silently masquerade as corrected evidence;
- compatible corrected profiles can be reused and are live-reclamped before admission;
- DEPLOY/PES/LOCKED/EVAL use the corrected authority at their real orchestration boundaries;
- scientific identity and frozen reference outputs remain unchanged;
- R3B/R4/R6B/R7 remain regression-clean;
- final affected regression and bounded assembled integration pass.

## 8. Expected affected surface

At minimum inspect and test:

- `mdstats/training_data/inference_parallel.py`;
- `mdstats/training_data/model_features.py`;
- `mdstats/training_data/campaign_execution.py` where execution/profile schemas or plans intersect;
- `mdstats/training_data/_campaign_cli_core.py`;
- static prediction consumers including `deploy_verify.py`, `pes_verify.py`, EVAL/LOCKED paths, and relevant public exports;
- runtime-profile serialization/state-store/cache compatibility surfaces;
- resource telemetry/measurement helpers;
- `tests/test_mlff_inference_parallel_scheduler.py`;
- `tests/test_mlff_static_mace_inference.py`;
- `tests/test_mlff_perf1_reopen_command_boundaries.py`;
- staged EVAL/CLI/resource/restart tests transitively affected by scheduler/profile changes;
- any additional callers discovered by final impact analysis.

Do not treat this list as a hard boundary.

## 9. Stage-local regression rule

Every material executable gate must close with:

1. cheapest high-signal focused tests for the new/changed mechanism;
2. complete regression for old behavior plausibly affected by that gate;
3. real consumer/command integration when the change crosses a product boundary.

Do not defer all testing to T-R8. Reuse old evidence only for behavior whose establishing dimension did not change.

## 10. Genuine redesign triggers

Stop dependent implementation and reopen only the affected design surface if:

- actual representative joint measurements show that one shared operating-point abstraction cannot safely serve EVAL and static verification without materially different resource semantics;
- correct concurrent measurement requires unsafe sharing of a mutable model shell and no worker-private ownership strategy can satisfy target scale/resources;
- point-local/conservative RAM or VRAM measurement cannot be obtained sufficiently for safe profile reuse without replacing the broader resource model;
- corrected profile-evidence versioning cannot be introduced without ambiguous reinterpretation of durable accepted scientific state;
- genuine joint search materially changes scientific outputs outside frozen tolerances;
- implementation expands into a new architectural subsystem outside PERF1.

Ordinary bugs, missing tests, runtime-profile schema bumps/rebuilds, telemetry corrections, bounded scheduler refactoring, and deletion of synthetic evidence paths are **not** redesign triggers.

## 11. Production qualification boundary

Do **not** perform full production-scale GPU qualification during T-R2A through T-R8.

After functional acceptance, the existing target-workstation qualification handoff remains authoritative. That final qualification should measure the actual best `(batch_size, concurrent_model_jobs)` operating point, throughput, utilization, VRAM/RAM headroom, cold/warm profile behavior, external-process concurrency, DYN overlap, disk/I/O footprint, restart behavior, and end-to-end/per-stage wall time on the target system.

No target-hardware performance claim is accepted before that qualification, and qualification cannot substitute for missing functional regression/integration.

## 12. Withdrawn second-reopen acceptance record

The second-reopen section-14 acceptance record remains in Git history and in its original workplan as historical evidence, but its **R2A/R2B/R8B closeout conclusion is withdrawn by this third independent review**.

R3B/R4/R6B/R7 evidence remains usable while those behaviors are unchanged. R5B's pre-model admission repair remains accepted locally, but consumer acceptance must be rerun because the canonical R2 authority/profile semantics change underneath it.

## 13. Completion condition

Return MLFF-END-TO-END-PERF1 to **FUNCTIONAL IMPLEMENTATION ACCEPTED — TARGET-WORKSTATION GPU QUALIFICATION DEFERRED** only when:

- T-R2A, T-R2B, T-R5, and T-R8 are accepted;
- R0, R1, R3B, R4, R6B, and R7 remain regression-clean;
- one-slot measured infeasibility is fail-closed;
- actual concurrent execution, not synthetic scaling, underlies every persisted `J > 1` operating-point datum;
- one canonical authority owns batch/concurrency/profile/live-reclamp selection;
- operating-point peak-resource evidence is safe and semantically versioned;
- corrected profiles are compatible/reusable without entering scientific identity;
- static consumers use the corrected authority without bypass;
- final re-derived affected regression and bounded assembled integration pass;
- unavailable functional checks are explicitly recorded;
- production GPU qualification remains deferred as a separate final handoff.
