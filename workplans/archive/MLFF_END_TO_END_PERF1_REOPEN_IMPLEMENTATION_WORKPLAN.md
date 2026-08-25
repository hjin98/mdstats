# MLFF-END-TO-END-PERF1 Reopen Implementation Workplan

Status: **FUNCTIONAL IMPLEMENTATION ACCEPTED — TARGET-WORKSTATION GPU QUALIFICATION DEFERRED**
Branch: `feat/mlff-end-to-end-performance-v1`  
Second-round reviewed base tip: `8ddd481cafe75b0d40930e852d03447d0be3eb55`
Reopens: `MLFF_END_TO_END_PARALLELIZATION_OPTIMIZATION_WORKPLAN.md` closeout status and the superseded first-reopen acceptance record  
Date reopened: 2026-08-24

## 1. Authority and purpose

This file is the active implementation contract for the next MLFF-END-TO-END-PERF1 closeout round.

The parent `MLFF_END_TO_END_PARALLELIZATION_OPTIMIZATION_WORKPLAN.md` remains the architectural baseline. The first reopen round materially repaired the implementation, but an independent second closeout review found remaining resource-ownership, operating-point, persistence, and cancellation gaps. The prior statement that R0-R8 were functionally accepted is therefore superseded.

This second reopen is intentionally narrow. Preserve accepted mechanisms and evidence unless a changed dimension can plausibly invalidate them. Do not replay already-closed design work merely because a new implementation round begins.

Implementation may proceed gate-by-gate under this workplan without another design round unless a genuine redesign trigger in section 10 fires.

## 2. Frozen engineering envelope

The following requirements remain non-negotiable:

- preserve target-size authority, 3 -> 10 -> 30 dependency/freeze semantics, candidate population, seeds, scientific thresholds, ranking/admissibility rules, verification resolution, and precision/dtype policy;
- runtime batch size, model-job concurrency, cache use, queue depth, worker count, scheduling order, and runtime operating profiles are execution state and must not alter scientific identity;
- optimized execution must remain numerically equivalent to the accepted scientific/reference path within frozen tolerances;
- durable ordering and published authority must be deterministic and independent of concurrent completion order;
- immutable/restart evidence must be authenticated before reuse;
- CPU/RAM/VRAM/storage/I/O admission must fail closed when one required unit of work cannot fit the configured safety envelope;
- the scheduler must be able to represent **zero currently admissible jobs** and terminate with an actionable resource error rather than forcing one job or deadlocking;
- failure/cancellation must stop new admission, terminate owned workers/process groups, and preserve previously accepted atomic state;
- full production-scale GPU qualification remains separate from functional acceptance and remains deferred to the final assembled candidate on the target workstation.

The governing optimization hierarchy remains:

`product capability/correctness/resource fitness > minimum justified system complexity > development economy`

## 3. Accepted work that remains closed

### R0 — command-field hard failure: **CLOSED**

Preserve:

- DEPLOY/PES use the real `InferenceExecutionPlan.selected_batch_size` field;
- command-boundary tests exercise real execution-plan consumers;
- no long-lived compatibility alias was added for the stale field name.

### R1 — scientific-policy / runtime-plan separation: **CLOSED**

Preserve:

- canonical scientific `CheckpointEvaluationPolicy` identity excludes runtime batch/cache choices;
- runtime execution evidence is separate from scientific policy identity;
- historical scientific policy digests remain readable with explicit legacy semantics;
- EVAL2 ranking/admissibility semantics remain unchanged.

A runtime **execution-plan persistence schema** issue remains open below, but it does not reopen scientific-policy identity.

### R4 — immutable concurrent publication: **CLOSED**

Preserve the no-clobber publication behavior:

- identical concurrent publishers converge safely;
- conflicting bytes cannot replace an accepted immutable destination;
- attempt-local temporaries are cleaned without overwriting accepted state.

### R7 — RELAX architecture: **CLOSED subject to final affected regression**

No RELAX redesign is authorized unless a new regression appears. Preserve flattened `(candidate, base)` scheduling, worker-private mutable calculators, sequential ASE FIRE semantics, vectorized topology reductions, and deterministic aggregation.

## 4. Valid evidence retained from the first reopen round

The following evidence remains useful but is **not final acceptance** for the second-round candidate:

- final first-round affected surface: `250 passed, 2 skipped`;
- bounded production-interface suite: `121 passed`;
- broader available suite excluding the independently uncollectable mesh-topology fixture module: `3183 passed, 36 skipped, 261 failed, 84 errors`;
- command-level DEPLOY/PES coverage, split-DYN overlap/restart coverage, immutable staging concurrency coverage, and scientific/runtime policy-separation coverage.

Reuse stage-local evidence only while the behavior it establishes is unchanged. Every second-round executable edit still requires its own focused + affected stage-local regression, and the final assembled candidate requires a fresh affected-surface regression and integration pass.

## 5. Second closeout findings now promoted to implementation requirements

### S1 — measured/live CUDA infeasibility cannot become zero-admissible capacity

Initial estimated one-job RAM/VRAM checks now fail closed correctly, and VRAM calibration retains allocation peaks. However, post-launch calibration initializes the safe target at one job and the live hard-VRAM guard likewise clamps to at least one.

Consequences:

- an underestimated workload can prove, after the first calibration job, that even one job breaches the configured envelope yet still remain admitted at one;
- a later baseline/external VRAM increase can make one job infeasible while the controller still represents one replacement job as admissible.

Required outcome: resource control must represent a terminal/blocked zero-admission state and fail cleanly without launching another job.

### S2 — G3 joint static operating-point optimization/profile reuse is still absent

`inference_batch_policy = "auto"` currently chooses a bounded cold-start batch (normally 8), while `StaticMaceInferenceExecutor` can only reduce that batch after OOM. Model-job concurrency is calibrated separately by the outer adaptive scheduler. There is no production joint `(batch_size, concurrent_model_jobs)` operating-point search or compatible profile reuse.

Consequences:

- `maximum_inference_batch_size > 8` is not meaningfully explored by auto mode unless implementation-specific OOM behavior drives downward adjustment;
- batch and concurrency are optimized by separate authorities even though they compete for the same VRAM/RAM and jointly determine throughput;
- no persistent compatible runtime profile accelerates repeated runs/checkpoints;
- live host-RAM re-clamping is not symmetrical with live VRAM control.

Required outcome: one coherent production runtime authority must own joint batch/concurrency selection, compatibility evidence, reuse, and live re-clamping. Existing executor/scheduler mechanisms should be consolidated rather than wrapped in a third independent optimizer.

### S3 — DEPLOY/PES static prediction bypasses live resource admission

DEPLOY and PES now call the correct static executor/batch field, but they construct static prediction directly rather than entering the same RAM/VRAM admission authority used by adaptive evaluation/verification scheduling.

Required outcome: DEPLOY/PES must prove one-job feasibility from live resources before model materialization/accelerator prediction and use the same canonical static operating-point authority. Scientific probe/policy identity must remain unchanged.

### S4 — staged pipeline RAM ownership is improved but incomplete

The explicit payload ledger correctly measures important retained objects, including ASE arrays, and transfers prepared/result reservations. Remaining gaps:

- an explicitly configured `*_pipeline_buffer_mib` can exceed the campaign's global RAM budget unless capped/rejected;
- finalize/reduction workers do not hold an explicit per-worker working-memory reservation;
- relevant model/provider/cache residency is not consistently represented in the aggregate pipeline RAM envelope;
- DYN CPU reduction inherits these gaps because it uses the staged finalize domain.

Required outcome: the stage ledger must bound aggregate retained payload + active worker/model/cache reservations and fail closed before overcommit.

### S5 — DYN split is correct, but scheduler-level external-process cancellation is incomplete

The simulation -> reduction split, bounded handoff behavior, streaming canonical reduction, duplicate-timestep semantics, and authenticated case receipts are accepted. The remaining gap is cancellation propagation from the staged scheduler into already-running external LAMMPS processes.

Required outcome: sibling failure, scheduler cancellation, or user interruption must propagate a shared cancellation signal to owned external simulations; each process group must terminate promptly while prior accepted receipts remain intact.

### S6 — `InferenceExecutionPlan` wire semantics changed without a schema-version transition

The current `mdstats.inference-execution-plan.v1` representation removed former fields and added new runtime fields while retaining the same schema identifier. A historical v1 record can therefore be rejected because the new reader reconstructs different v1 semantics before checking the digest.

Required outcome: runtime evidence persistence must have explicit compatibility semantics. Prefer a v2 canonical write schema with an exact v1 reader/migration rule, or another equally simple solution that preserves old valid v1 evidence or deliberately invalidates/rebuilds it at the owning layer without masquerading as the same wire schema.

This is runtime evidence compatibility, not a scientific-policy schema change.

## 6. Next-round gated implementation sequence

### R2A — zero-admission state + execution-plan persistence repair

Implement first because later operating-point work depends on correct resource/persistence semantics.

#### Required behavior

1. Introduce an explicit representation for **no job currently admissible** after calibration/live re-clamp.
2. Do not force `target_jobs >= 1` when measured one-job projection breaches RAM/VRAM/utilization safety bounds.
3. A zero-admission decision must produce a deterministic actionable error/blocked outcome; the scheduler must not spin or deadlock with queued work and zero capacity.
4. Once a running job has demonstrated one-job infeasibility, do not launch a replacement after it completes.
5. If live external/baseline VRAM rises so that one additional calibrated job no longer fits, block new admission before launch; if the remaining queued workload can no longer ever fit, fail cleanly.
6. Preserve already-running work unless immediate termination is necessary for safety; do not convert a future-admission re-clamp into unnecessary cancellation of a healthy in-envelope active job.
7. Version `InferenceExecutionPlan` persistence correctly. Canonical new writes must not silently change the meaning of schema v1.
8. Preserve or explicitly rebuild old runtime evidence through one owning migration path; do not add scattered compatibility branches at consumers.

#### Focused regression

- configured one-job RAM infeasibility still fails before launch;
- configured one-job VRAM infeasibility still fails before launch;
- **new:** initial estimate fits, measured first-job VRAM peak proves one job infeasible -> zero future admission + clean error;
- **new:** calibrated plan initially fits, live VRAM baseline rises until one job cannot fit -> no new launch + clean error;
- zero-admission queue cannot deadlock;
- historical execution-plan v1 fixture has deterministic read/rebuild behavior;
- canonical new execution-plan serialization round-trips under the new schema/version contract;
- scientific policy digest and scientific metrics remain unchanged.

#### Gate acceptance

R2A closes only after focused tests plus affected scheduler/persistence/CLI regression pass.

---

### R2B — canonical joint static inference operating-point authority

This is the central remaining PERF1 architecture gate.

#### Product design to implement

One production **static-inference runtime authority** must jointly own:

- active inference batch size;
- concurrent model-job admission;
- one-job and aggregate RAM/VRAM safety;
- measured throughput/peak-resource operating-point evidence;
- compatible runtime-profile reuse;
- live re-clamping;
- bounded per-executor OOM learning.

It may delegate model execution to `StaticMaceInferenceExecutor` and telemetry/scheduling mechanics to existing helpers, but there must not be two independent optimizers deciding batch and concurrency without a shared operating-point decision.

#### Bounded operating-point search requirements

1. Auto mode begins from a safe bounded cold-start point, but must be able to explore other batch sizes up to `maximum_inference_batch_size` when representative work is available.
2. Candidate batch sizes should be a bounded monotonic/geometric set plus relevant learned limits rather than every integer.
3. Candidate concurrency must remain bounded by CPU/RAM/VRAM/task-count constraints.
4. Collect actual throughput and peak-safe resource evidence for feasible `(batch, jobs)` points without exhausting the machine.
5. Select the globally best justified safe point for the observed workload; when throughput is statistically/operationally near-equivalent, prefer the lower-resource/lower-complexity point.
6. Retain OOM halving as a local safety mechanism, and feed its learned safe ceiling back into the runtime authority rather than letting it become a hidden second batch policy.
7. The selected point must never exceed the live resource envelope after configured reserve/headroom.
8. Runtime-profile compatibility must include enough hardware/runtime/model/workload-shape identity to prevent unsafe reuse. A conservative compatibility key is acceptable; stale/incompatible profiles must be ignored/rebuilt.
9. Runtime profile identity must not enter scientific policy/probe/result identity.
10. Live RAM as well as live VRAM must be able to reduce future admission when the actual available envelope shrinks.
11. Remove obsolete operating-point/profile fields or mechanisms that are no longer authoritative.

#### Required regression

- batch-1/reference versus optimized energy/force/stress equivalence;
- auto mode with `maximum_inference_batch_size > 8` can select/exercise a batch above 8 when synthetic/representative evidence makes it best;
- auto mode can retain a smaller batch when larger points are slower or resource-unsafe;
- joint selection chooses the best safe `(batch, jobs)` point from a deterministic synthetic telemetry/throughput fixture;
- output ordering is deterministic under out-of-order worker completion;
- OOM backoff is bounded and the learned safe batch ceiling is respected by later point selection;
- profile reuse skips calibration when compatibility matches and live resources still admit the profile;
- stale/incompatible profile is ignored/rebuilt;
- compatible profile is live-reclamped before admission when RAM/VRAM changed;
- changing runtime operating points leaves scientific policy digest and bounded scientific results unchanged;
- code search/review confirms one active joint operating-point authority remains.

Representative CPU/synthetic telemetry evidence is sufficient for functional implementation. **Do not run full target-GPU throughput qualification here.**

---

### R3B — finish aggregate staged-pipeline RAM ownership

Preserve the current explicit payload ledger and improve only the missing aggregate ownership.

#### Required behavior

1. Explicit `evaluation_pipeline_buffer_mib` / `dynamics_pipeline_buffer_mib` values must be capped by or rejected against the active global RAM budget; a sub-budget cannot authorize more RAM than the campaign resource envelope.
2. Add explicit working-memory reservations for active prepare/inference/finalize domains where their execution requires memory beyond retained input/result payloads.
3. Charge model/provider residency and material graph/cache reservations when they are part of the active pipeline envelope; do not double-count shared immutable caches.
4. DYN reduction/finalize workers must have an explicit bounded working-memory reservation separate from the retained trajectory/result payload.
5. Reservation acquisition must precede worker launch; release must occur on every success/failure/cancellation path.
6. Queue-depth limits remain in force in addition to byte limits.
7. Preserve overlap where resources permit; do not solve accounting by globally serializing the pipeline.

#### Required regression

- explicit pipeline MiB greater than global RAM budget is rejected/capped deterministically;
- low-RAM EVAL fixture backpressures without exceeding the ledger;
- low-RAM DYN fixture allows simulation/reduction overlap only when both worker reservations fit;
- finalize/reduction worker reservation prevents over-admission;
- worker failure/cancellation releases all reservations;
- no reservation leak/deadlock under out-of-order completion;
- cold/warm EVAL2 and DYN scientific metrics/pass-fail remain unchanged.

---

### R5B — route DEPLOY/PES through the canonical static resource authority

After R2A/R2B stabilize the shared runtime owner:

1. DEPLOY checkpoint-head and target-only static predictions must enter the canonical static inference runtime authority.
2. PES foundation and candidate predictions must use the same authority.
3. Before model construction/device transfer, prove one-job feasibility against live RAM/VRAM for the selected device.
4. Reuse safe compatible runtime operating profiles when applicable, with live re-clamping before admission.
5. Preserve sparse target reads, stable geometry graph reuse, probe identities, scientific tolerances, deterministic ordering, and target-head/ML-IAP parity.
6. Keep external LAMMPS run-0 resource/process handling separate from static MACE prediction where the resource domains differ.
7. Remove direct static-prediction bypasses that evade resource admission unless retained solely as a lower-level library API with explicit caller-owned admission semantics.

#### Required regression

- command-level DEPLOY and PES still exercise the real orchestration boundary;
- DEPLOY/PES one-job RAM/VRAM infeasibility fails **before** model construction/prediction;
- safe resource conditions reach the canonical executor and preserve numerical parity;
- graph-cache identity remains safe across model/candidate changes;
- execution-profile evidence remains runtime-only;
- external LAMMPS run-0 failure/cancellation leaves no orphan process group or partial accepted artifact.

---

### R6B — DYN cancellation propagation + final resource closeout

Do not redesign the accepted simulation/reduction split.

#### Required behavior

1. Give the staged scheduler an explicit cancellation signal/token shared with active external simulations.
2. On sibling worker failure, user interruption, or scheduler abort: set cancellation, stop new admission, and propagate cancellation to owned LAMMPS processes.
3. `_run_file_backed_process` or its owning wrapper must observe cancellation while waiting and terminate the complete process group with the existing TERM -> KILL policy when necessary.
4. Cancellation of one unfinished case must not invalidate authenticated receipts from previously completed cases.
5. No completion receipt may be published for a cancelled/partial simulation or failed reduction.
6. Integrate R3B finalize/reduction RAM reservations into the DYN pipeline.
7. Preserve canonical streaming reduction, duplicate-timestep last-wins semantics, reference-frame semantics, drift/topology metrics, deterministic final ordering, disk reserve checks, and file-backed logs.

#### Required regression

- deterministic staged-runner test with an active fake external process proves sibling failure cancels/kills the process group;
- KeyboardInterrupt/cancel path kills the owned process group without waiting for natural completion;
- accepted prior case receipt remains reusable after later-case cancellation;
- cancelled/incomplete case has no accepted receipt and reruns on restart;
- simulated ENOSPC/write failure preserves prior receipts;
- simulation N can overlap reduction N-1 when RAM and CPU reservations permit;
- final DYN metrics/pass-fail remain identical to the accepted oracle fixtures.

## 7. R8B — final affected-surface reconciliation and functional acceptance

R8 is reopened and can close only after R2A, R2B, R3B, R5B, and R6B are accepted.

### Required final review/test sequence

1. Re-derive the complete affected behavioral surface from the assembled source.
2. Include modified and transitively affected callers, config, persistence, cache/profile, scheduler, static inference, DEPLOY/PES, DYN, RELAX, public API, and CLI boundaries.
3. Search for stale field names, duplicate batch/concurrency authorities, obsolete profile/cache owners, old execution-plan write schemas, direct DEPLOY/PES admission bypasses, and uncancelled external-process paths.
4. Run focused tests for every new second-round mechanism.
5. Run a fresh complete affected-surface regression after all second-round executable edits.
6. Re-run bounded production-interface integration through the real preflight -> preparation/materialization -> TRAIN/EVAL -> DEPLOY -> PES -> RELAX -> DYN -> selection/publication boundaries available in the representative fixture.
7. Re-run EVAL restart and DYN partial-completion/restart integration where changed resource/profile behavior can affect them.
8. Re-run cancellation/failure integration across worker and external-process boundaries.
9. Confirm LOCKED-TEST2 activation/prediction-evidence isolation remains unchanged.
10. Run repository-required broader/full available tests when the final affected surface cannot be bounded confidently; triage every failure/error that plausibly intersects the changed surface.
11. Record genuinely unavailable checks explicitly. An unavailable required functional check is not a pass.

A harness may stub heavyweight dependencies **below** the real production/public boundary. It must not reconstruct the orchestration/resource logic being tested.

### Functional acceptance invariants

Before this workplan may return to functional-accepted status, the assembled candidate must demonstrate all of the following:

- measured or live one-job infeasibility can become zero-admissible capacity and fails cleanly;
- no scheduler deadlock occurs at zero capacity;
- auto static inference genuinely chooses among bounded batch/concurrency operating points rather than freezing batch 8;
- compatible runtime profiles can be reused safely and stale ones are rejected;
- live RAM/VRAM changes re-clamp future admission;
- DEPLOY/PES cannot enter accelerator prediction without canonical resource admission;
- execution-plan persistence has explicit version/compatibility semantics;
- EVAL/DYN staged RAM accounting includes active worker working memory and cannot exceed the global envelope by configuration;
- DYN scheduler cancellation terminates owned external process groups and preserves prior accepted receipts;
- all scientific/reference outputs remain within frozen tolerances;
- final bounded assembled integration succeeds.

## 8. Expected second-round affected surface

At minimum:

- `mdstats/training_data/inference_parallel.py`;
- `mdstats/training_data/model_features.py`;
- `mdstats/training_data/campaign_execution.py`;
- `mdstats/training_data/_campaign_cli_core.py`;
- `mdstats/training_data/deploy_verify.py`;
- `mdstats/training_data/pes_verify.py` and direct PES callers;
- `mdstats/training_data/dyn_verify.py`;
- execution-plan serialization/export surfaces in `mdstats/training_data/__init__.py` and `mdstats/__init__.py` if schema/API changes propagate;
- campaign config generation/resolution for inference auto/fixed policy and pipeline RAM controls;
- state-store readers/writers for runtime execution evidence/profile persistence;
- scheduler/resource tests including `tests/test_mlff_inference_parallel_scheduler.py`;
- staged-pipeline tests including `tests/test_mlff_opt_eval4_staged_evaluation_pipeline.py`;
- command-boundary tests including `tests/test_mlff_perf1_reopen_command_boundaries.py`;
- DEPLOY/PES/DYN/RELAX affected regression consumers;
- all additional callers discovered by final assembled impact analysis.

Do not treat this list as a hard boundary.

## 9. Stage-local regression rule

Every material second-round gate must close with:

1. cheapest high-signal focused tests for the changed mechanism;
2. regression for all old behavior plausibly affected by that gate;
3. real consumer/command integration where the changed behavior crosses a product boundary.

Do not defer all testing to R8B. Reuse still-valid first-round evidence only for behavior unchanged by the current gate.

## 10. Genuine redesign triggers

Stop dependent implementation and reopen only the affected design surface if:

- batching/concurrency changes alter accepted scientific results beyond frozen tolerances;
- representative evidence shows no practical bounded joint operating-point scheme can safely satisfy both EVAL and verification without materially different resource semantics;
- a safe compatible profile key would require scientific identity coupling rather than runtime execution identity;
- exact execution-plan v1 compatibility cannot be preserved without corrupting or ambiguously reinterpreting accepted runtime evidence;
- live RAM cannot be measured/represented sufficiently for safe pre-admission without changing the broader resource model;
- DYN external cancellation cannot be integrated without replacing the existing process ownership model;
- implementation broadens into a new architectural subsystem not covered by PERF1.

Ordinary bugs, missing tests, local schema migration, conservative resource-estimate corrections, scheduler refactoring, and removal of stale authorities are **not** redesign triggers.

## 11. Production qualification boundary

Do **not** perform full production-scale GPU qualification during R2A-R8B implementation.

After functional R8B acceptance, prepare the final target-workstation qualification handoff. It should characterize the final assembled candidate on the user's target GPU/system, including:

- selected joint static inference `(batch_size, concurrent_jobs)` operating point and alternatives considered;
- throughput and calibration/profile reuse behavior;
- GPU utilization and peak/steady VRAM/headroom;
- CPU/RAM usage and live re-clamp behavior;
- LAMMPS external-process concurrency;
- DYN simulation/reduction overlap;
- disk/I/O and scratch footprint;
- cold/warm cache/profile and restart behavior;
- end-to-end/per-stage wall time.

No target-hardware performance claim is accepted before that qualification. Production qualification cannot substitute for missing functional regression/integration.

## 12. Superseded first-reopen acceptance record

The 2026-08-24 first-reopen record that declared R0-R8 functionally accepted is retained in Git history as evidence of that implementation round, but its **closeout conclusion is withdrawn** by this second independent review.

Its test results remain reusable evidence for unchanged behavior as described in section 4. They do not close the newly identified S1-S6 gaps.

## 13. Completion condition

This active workplan can be returned to **FUNCTIONAL IMPLEMENTATION ACCEPTED — TARGET-WORKSTATION GPU QUALIFICATION DEFERRED** only when:

- R2A, R2B, R3B, R5B, R6B, and R8B are accepted;
- R0, R1, R4, and R7 remain regression-clean;
- zero-admission resource infeasibility is represented and tested without deadlock;
- one canonical joint static operating-point authority owns batch/concurrency/profile/re-clamp decisions;
- execution-plan persistence has explicit version compatibility;
- DEPLOY/PES use canonical live resource admission;
- staged RAM accounting cannot exceed the global envelope and includes active worker working memory;
- DYN scheduler-level cancellation kills owned external processes and preserves prior accepted receipts;
- the final re-derived affected surface passes fresh regression and bounded assembled integration;
- unavailable functional checks are explicitly recorded;
- full production GPU qualification remains deferred as a separate final handoff.

## 14. Second-reopen implementation acceptance record (2026-08-24)

R2A, R2B, R3B, R5B, R6B, and R8B are functionally accepted on branch
`feat/mlff-end-to-end-performance-v1`.

- R2A introduced terminal zero-admission semantics for measured/live one-job
  infeasibility, actionable no-capacity scheduler failure, and a canonical
  `mdstats.inference-execution-plan.v2` writer with one exact owning v1
  validation/rebuild path. Complete scheduler/CLI persistence regression passed
  `82 passed, 1 skipped`.
- R2B introduced one executor-integrated static runtime authority for bounded
  geometric batch/job evidence, actual throughput and peak-resource evidence,
  near-best low-resource selection, OOM safe-ceiling feedback, conservative
  hardware/runtime/model/workload compatibility, persistent profile reuse, and
  live RAM/VRAM re-clamping. Auto mode exercises batches above eight when
  evidence supports them. The staged/CLI/static affected gate passed
  `117 passed, 1 skipped`.
- R3B rejects a pipeline sub-budget above the live global RAM envelope and
  reserves prepare/inference/finalize-or-reduction working memory before launch,
  including optional shared runtime residency. Reservations release on success,
  failure, cancellation, and queued-work cleanup while permitted EVAL/DYN overlap
  remains intact. Focused EVAL/DYN resource regression passed `24 passed`.
- R5B routes command-level DEPLOY, PES, and LOCKED-TEST2 static prediction through
  live one-job RAM/VRAM admission before model construction and through the same
  static runtime authority. Functional DEPLOY/PES boundary regression passed;
  two separately observed PES specification assertions remain historical stale
  checks for an old package version and the pre-facade CLI source layout.
- R6B propagates one staged-scheduler cancellation token into owned external
  LAMMPS process groups. Sibling failure and `KeyboardInterrupt` both exercise
  TERM-to-KILL-capable process-group shutdown; cancelled cases cannot reach
  reduction or receipt publication, while previously accepted receipts remain
  reusable. Complete DYN/staged regression passed `36 passed`.
- R8B re-derived the assembled surface and found legacy execution-plan fields
  only in the owning v1 migration and fixtures, one active static operating-point
  authority, no direct DEPLOY/PES/LOCKED admission bypass, and one cancellable DYN
  external-process wait path. Fresh affected regression passed
  `195 passed, 2 skipped`; a separate bounded production-interface suite covering
  preparation/materialization, EVAL, command DEPLOY/PES, RELAX/DYN and restart,
  SELECT2/publication, and LOCKED-TEST2 passed `113 passed`. The final core
  second-round suite passed `136 passed, 1 skipped`. Module compilation and
  `git diff --check` passed.

The unavailable functional checks are the repository fixture requiring a real
LTA training root and the optional real-MACE-model test. No supported target GPU
qualification was run. Production-scale GPU/VRAM, concurrency, cold/warm profile,
disk/I/O, and end-to-end timing qualification remains the separate handoff in
section 11; no target-hardware performance claim is made here.
