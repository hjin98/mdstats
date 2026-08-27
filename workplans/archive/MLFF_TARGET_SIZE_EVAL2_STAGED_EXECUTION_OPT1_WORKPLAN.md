---
kind: implementation-workplan
workplan_id: CODE-MLFF-TARGET-SIZE-EVAL2-STAGED-EXECUTION-OPT1
protocol_version: 5.7.0
status: completed
completed_date: 2026-08-26
created_date: 2026-08-26
initial_reviewed_head: 31133d75b53817cdd63857ba2a93e603507aacef
reviewed_head: 9170557bd01ca9a0c2a55d4cfb89fed2dc8d17e5
implementation_review_date: 2026-08-26
implementation_review_disposition: closed_after_rework
gpu_qualification_disposition: deferred_to_FINAL-GPU1
controlling_workplan: workplans/active/MLFF_TARGET_SIZE_EXACT_BOUNDARY_SCREENING_REWORK_WORKPLAN.md
---

# MLFF Target-Size EVAL2 Staged Execution and Performance Rework Workplan

## Objective

Complete and close the TARGET-SIZE-V5 exact-boundary EVAL2 transition from the original opaque private serial endpoint loop into the established staged evaluation execution architecture, preserving the correctly landed staged topology while repairing the remaining resource-accounting, authority-validation, restart, cancellation, prepare-stage, and performance-evidence gaps found by independent review. Reuse existing mdstats CPU/GPU scheduling, resource admission, caching, failure propagation, restart, and deterministic aggregation machinery rather than adding target-size-specific substitutes.

The change is an execution/performance/operability rework only. It does **not** change target-size scientific semantics. Exact configured screening boundaries remain the only evaluation epochs; target-size ranking remains target-only; paired screening-seed logic and the existing reducer remain unchanged; and post-selection production remains a separate fresh campaign.

The user-visible defect motivating this work is the long silent interval after:

```text
EVAL2 target-first checkpoint evaluation
----------------------------------------
[PASS] precision: ...
```

At the original design baseline, the source was not intentionally idle there. `_eval2_target_size_endpoint_evidence()` performed substantial endpoint work serially, including target-role/materialization work, checkpoint authentication/model reconstruction, static-inference calibration, GPU prediction, metric reduction, and persistence. Lower layers already emitted structured phase events, but the target-size path bypassed the callback/scheduler context that rendered those events. More importantly, that private loop bypassed the existing OPT-EVAL4 staged execution topology that already provided CPU prepare/finalize overlap, bounded buffering, adaptive GPU admission, progress/heartbeat, cancellation, and deterministic aggregation.

This workplan therefore treats the original silence as evidence of a broader execution-architecture drift rather than merely a missing print statement. The first implementation pass has since landed the staged topology; the independent-review reopening below governs the remaining closure defects.

## Authority and precedence

This plan is subordinate to, and must preserve, the scientific and lifecycle decisions in:

- `workplans/active/MLFF_TARGET_SIZE_EXACT_BOUNDARY_SCREENING_REWORK_WORKPLAN.md`;
- `docs/arch_manuals/mlff_training_data_architecture.md`;
- `docs/arch_manuals/mlff_bounded_evaluation_verification.md`;
- `docs/arch_manuals/mlff_checkpoint_model_reconstruction.md`;
- current accepted target-size/EVAL2 specifications and tests.

This plan does not supersede those authorities before implementation acceptance. If a proposed optimization conflicts with their scientific/provenance semantics, the optimization yields unless design is explicitly reopened on evidence.

### Reviewed source baseline

The original design baseline was:

```text
fix/target-size-exact-boundary-screening
31133d75b53817cdd63857ba2a93e603507aacef
```

The independent post-implementation review is bound to the current remote implementation head:

```text
fix/target-size-exact-boundary-screening
9170557bd01ca9a0c2a55d4cfb89fed2dc8d17e5
```

The two immediately preceding correctness repairs required by this rework remain present on that lineage:

1. the DATA2A source-label to final-development REPAIR2 authority bridge and coherence checks (`patch3`, commit `0e86fe0b4d9eb47d8a0c27af1fabaaa0b305dbbd` lineage);
2. independent `allow_target_only_evaluation` versus `allow_target_monitor_override` semantics for TARGET-SIZE-V5 target-only evaluation.

Implementation must preserve both repairs. This workplan must not reintroduce naked DATA2A→REPAIR2 domain lookup or couple target-only authorization back to target-monitor override.

## Original design review findings and corrections

The pre-implementation design review established the following constraints for the rework. They remain protected unless the independent-review reopening below explicitly tightens them.

### 1. The real defect is execution-path drift, not only missing logging

At the original baseline, TARGET-SIZE-V5 owned a private serial `(size, seed)` endpoint loop while mature evaluation code already owned staged scheduling. The globally simpler and more performant target state remains consolidation onto `_run_staged_evaluation_tasks()` (or its current owning successor), not a second target-size-specific scheduler. The first implementation pass has landed this central consolidation and it must not regress during rework.

### 2. Durable scientific publication remains parent-thread owned

Worker threads may prepare data, materialize/reuse computational artifacts, run inference, and produce typed attempt results. They must not independently mutate authoritative `CampaignStore` scientific state or publish target-size endpoint completion. The parent/orchestrator validates returned authority identities and commits terminal evidence deterministically.

Cached and freshly computed outcomes must pass through the same parent validation/publication path. A cache hit is not completion merely because bytes exist.

### 3. Endpoint identity and duplicate scheduling must be explicit

One logical task identity must include enough authority to prevent accidental aliasing or duplicate publication, including at least:

- target-size study/current generation authority;
- exact boundary/rung epoch;
- candidate size;
- screening seed/run identity;
- target-role/label-domain authority;
- checkpoint/run authority needed to authenticate the endpoint.

Two tasks with the same human-readable `n=... seed=...` label but different authority generations are not the same task.

### 4. Shared target reuse must not collapse scientific authority

All candidate checkpoints within one compatible label-domain/rung generally evaluate the same `size_development_complement`, so parsed target data and immutable evaluation views should be shared. However, byte identity is only a computational-cache fact.

Scientific role/authority remains explicit and separate. Byte-equal files from different authorities cannot silently establish scientific equivalence.

A shared target context must therefore be scoped by the compatible target scientific authority (label domain + role/rung/current target-size generation) and carry an authenticated content digest. Computational parse/view cache keys may then use content digest plus parser/view schema and policy version.

### 5. Shared mutable objects are unsafe

ASE `Atoms` and similar parsed objects can be mutable. Stage-wide sharing is allowed only for an immutable normalized representation or under a verified read-only contract. If a downstream consumer can mutate objects, clone at that boundary rather than sharing one mutable object between workers.

### 6. Shared resident memory must be budgeted exactly once

The canonical target dataset/view is stage-resident memory. It must be admitted against the evaluation RAM budget once and remain visible to resource accounting. `_PipelineByteLedger` or its current owner must neither multiply this shared resident cost by every endpoint nor omit it entirely while accounting only for per-task buffers.

### 7. ContextVar phase telemetry must survive worker dispatch

Existing inference phase reporting is ContextVar-based. If staged CPU work uses `ThreadPoolExecutor`, the execution path must use the repository's existing context-propagation helper or `contextvars.copy_context()` equivalent so the parent-bound phase callback remains active inside worker work. Concurrent worker logs must serialize through the reporter; workers must not independently print interleaved CLI lines.

### 8. Progress counts accepted logical work, not submitted futures

Population progress advances when an expected endpoint reaches an authenticated terminal scientific state:

- successful target evaluation; or
- an explicitly approved candidate-specific scientific/numerical failure represented by typed failure evidence.

Submitting a future, completing a cache probe, or observing a worker disappear does not advance logical completion. Cache reuse advances progress only after authority validation.

ETA is observational and based on terminal completed work; it is not an admission criterion.

### 9. Ranking has a hard terminal-state barrier

The target-size reducer may run only after every expected endpoint for the rung has one valid terminal scientific state. Approved scientific failures may participate according to existing target-size failure semantics. Any infrastructure/programming/authority/corruption failure aborts before ranking. Concurrent arrival order must never change reducer input ordering or results.

### 10. Cancellation/preemption and partial publication remain fail-closed

When cancellation or a fatal worker failure begins:

- stop admitting new endpoint work;
- cancel owned queued work where safe;
- propagate/cancel owned child processes according to existing scheduler semantics;
- clean worker-private GPU/provider/temp resources;
- never publish partial endpoint work as COMPLETE;
- preserve already authenticated terminal evidence for restart.

### 11. One GPU resource owner remains mandatory

The initial migration must not create outer concurrent checkpoint GPU jobs around an inner static-inference scheduler. The staged evaluator admits one accelerator-stage task according to the existing GPU authority; `StaticMaceInferenceExecutor` remains the owner of internal batch size and concurrent model/inference jobs.

CPU preparation and finalization may overlap the accelerator stage using existing worker/resource controls.

Outer multi-checkpoint GPU concurrency is a later evidence-gated design decision only if the repaired pipeline still leaves material accelerator capacity idle.

### 12. Provider hot-swap requires state-dependent cache invalidation

The existing compatible-state loader is a promising optimization, but a reusable provider/model shell must be worker-private and never concurrently mutated. Any calculator, compiled graph, converted model, or other cache whose validity depends on model weights must be rebuilt or independently proven weight-independent before hot-swapped state is used.

### 13. Calibration compatibility must not be broadened speculatively

Repeated per-checkpoint static-inference calibration may be expensive, but current exact-model runtime-profile identity is conservative by design. The mandatory rework instruments calibration cost first. Broader architecture/workload-compatible calibration reuse is permitted only after representative measurements show material value and a bounded equivalence/resource-safety qualification supports the new compatibility relation.

### 14. Legacy reconstruction heartbeat is not an initial semantic rewrite

The existing checkpoint reconstruction fallback may block in a long subprocess. First restore staged scheduler heartbeat plus existing phase telemetry. Only if measurements show that the subprocess remains a materially opaque dominant interval should its wait loop be changed to a monitored/polling equivalent that preserves timeout, stdout/stderr, return-code, cleanup, and reconstruction semantics exactly.

### 15. Configuration must remain consolidated

Reuse existing controls unless evidence proves they cannot express the required plan:

- `parallel_evaluation_prepare_jobs`;
- `parallel_evaluation_finalize_jobs`;
- `evaluation_pipeline_buffer_jobs`;
- `evaluation_pipeline_buffer_mib`;
- existing static-inference batch/concurrency settings;
- existing CPU/native-thread and RAM/VRAM budgets.

Do not add target-size-specific worker-count or GPU-concurrency settings merely because this caller was previously serial.

## Protected concerns and invariants

Implementation must preserve all of the following.

### Scientific/target-size semantics

- Exact `n1 -> n2 -> n3` boundary evaluation only.
- Existing candidate universe, MVQUAL admission, promotion geometry, paired screening-seed semantics, ranking/equivalence/tie policy, and selected-size freeze.
- Target-only EVAL2 ranking for target-size screening; no replay metric, foundation-baseline replay metric, or production acceptance criterion may enter target-size ranking.
- No evaluation of eliminated candidates at later boundaries.
- No nonboundary checkpoint may substitute for the configured rung checkpoint.
- Precision policy and scientific arithmetic remain unchanged.

### Authority/provenance

- Preserve the DATA2A source-label ↔ TARGET-DATA2B ↔ final-development REPAIR2 authority bridge.
- Preserve independent target-only and target-monitor-override authorization semantics.
- Preserve exact run/checkpoint/optimizer/RNG continuation identity for surviving screening trajectories.
- Scientific artifacts/digests/schema are unchanged by the mandatory execution migration unless an independently necessary schema defect is discovered.
- Computational cache versions may change when needed to invalidate stale parse/view/runtime cache entries; such cache invalidation must not masquerade as scientific-state invalidation.

### Failure semantics

- Existing typed TRAIN2 candidate scientific failure remains `TargetSizeTrajectoryFailureEvidence` with training-phase ownership.
- Only the explicitly accepted EVAL2 numerical/scientific exception class may be converted into target-evaluation failure evidence.
- Infrastructure, programming, authority, corruption, persistence, and unexpected exceptions remain fatal and visible.
- No broad catch/continue or automatic retry of unknown failures.

### Resource/concurrency

- Existing stage CPU/RAM/VRAM/I/O budgets remain authoritative.
- One accelerator resource owner; no nested independent GPU schedulers.
- Bounded queues/backpressure; no unbounded future/result/materialization population.
- Deterministic externally visible result ordering independent of worker completion order.
- Worker-private mutable model/provider state.

### Restart/persistence

- Already authenticated terminal endpoint evidence remains reusable after interruption.
- Partial/in-progress attempt artifacts never become accepted terminal scientific state.
- Cache hits and fresh results converge through the same authority validation/publication step.
- Existing trained checkpoints are not invalidated merely by this execution rework.

## Target execution architecture

The mandatory target topology is:

```text
parent target-size authority/preflight
        |
        +-- authenticated pre-existing TRAIN2 scientific failures
        |       -> typed terminal target-size failure evidence
        |
        +-- successful exact endpoint descriptors
                |
                +-> shared immutable target evaluation context
                |
                +-> OPT-EVAL4 staged execution
                       CPU prepare workers
                             |
                       bounded ready/backpressure queue
                             |
                       existing accelerator authority
                             |
                       CPU finalize workers
                |
                +-> typed attempt result
                        |
                  parent authority validation/publication
                        |
                  deterministic endpoint ordering
                        |
                  terminal-state barrier
                        |
                  existing target-size reducer
```

No worker is allowed to bypass the parent publication or ranking barrier.

## Scope

Expected executable owners include, as evidence requires:

- `mdstats/training_data/_campaign_cli_core.py` — target-size EVAL2 endpoint orchestration, staged task construction, progress binding, parent commit/ranking barrier;
- `mdstats/training_data/campaign_execution.py` — only where shared immutable target/view identity, cache identity, inference phase/progress callbacks, or prepared-evaluation seams need generalized ownership;
- existing static-inference/model-provider/cache modules used by OPT-EVAL4, only where required to expose already-owned reuse/timing or qualified provider-state replacement;
- target-size/EVAL2/OPT-EVAL4 regression and integration tests;
- accepted architecture/specification documentation only after implementation changes current durable behavior.

Out of scope for the mandatory migration:

- changing target-size ranking/scientific policy;
- changing screening seed count or semantics;
- changing `n1/n2/n3` or production `n` defaults;
- full production-scale/GPU qualification;
- new target-size-specific scheduler infrastructure;
- outer multi-checkpoint GPU concurrency without evidence-gated redesign;
- speculative calibration-compatibility broadening;
- unrelated TRAIN2/preparation optimization.

## Independent implementation review reopening — 2026-08-26

The first implementation pass successfully established the central architectural target: TARGET-SIZE-V5 endpoint evaluation now uses the existing staged evaluation scheduler; progress/heartbeat and ContextVar phase telemetry are wired; one accelerator owner remains authoritative; deterministic endpoint ordering and the complete-population ranking barrier are present; the target-only and DATA2A/TARGET-DATA2B/REPAIR2 correctness repairs remain intact; and shared target reuse validates scientific role/content/frame identity before computational reuse. These accepted surfaces should be preserved and their still-valid regression evidence reused unless a repair below can plausibly invalidate them.

Independent review of implementation head `9170557bd01ca9a0c2a55d4cfb89fed2dc8d17e5` found the following mandatory closure gaps. They are implementation nonconformances within the accepted design, not a reason to reopen target-size scientific semantics.

### R1 — Shared target RAM must be charged exactly once in the real prepared payload

The staged owner reserves `SharedTargetEvaluationContext.retained_bytes` once, but generic prepared-payload estimation can recursively count the same `target_atoms`/`target_view` again for every `PreparedCheckpointEvaluation`. The existing scalar-only RAM test cannot detect this.

Required end state:

- stage-shared target/view identities are charged once at stage residency;
- each endpoint is charged only its incremental prepared state;
- the generic scheduler remains correct for callers without shared residency;
- no under-accounting is introduced by simply zeroing or globally ignoring target payloads.

Acceptance must use an actual or representative `PreparedCheckpointEvaluation` carrying the shared target/view and prove that increasing endpoint count does not multiply the already-resident bytes.

### R2 — Parent publication must validate endpoint authority, not merely execute on the parent thread

Worker results must be treated as attempt-local data. Before any `CampaignStore.put_record`, the parent must bind the result to the expected immutable endpoint descriptor and independently validate the material run/checkpoint/target-role/target-artifact/policy/prediction/target-only identities. Record keys should be parent-derived or independently checked against parent-derived keys.

At minimum, a successful result must prove correspondence for:

- `(size, seed)` and exact rung/boundary;
- expected run/run-plan authority;
- expected checkpoint identity/epoch;
- expected target role and target artifact/SHA/frame ordering;
- evaluation policy identity;
- prediction digest linkage into the metric/evaluation records;
- absence of replay evaluation for TARGET-SIZE-V5;
- authorized target-only provenance;
- checkpoint-assessment linkage to the expected evaluation/metric/checkpoint.

A negative integration test must swap or forge otherwise valid endpoint results and prove that parent publication rejects them before persistence.

### R3 — All authenticated terminal endpoint states must be restartable, including EVAL2 scientific failure

A successful endpoint is already durably reusable, but an EVAL2 numerical/scientific failure must not exist only in the in-memory rung result until the reducer eventually commits the study. Persist deterministic per-endpoint terminal failure evidence using existing target-size failure semantics where possible.

Required restart behavior:

```text
valid successful endpoint -> reuse
valid TRAIN2 scientific failure -> reuse
valid EVAL2 scientific failure -> reuse
missing endpoint -> schedule
```

If a later sibling suffers a fatal infrastructure/programming/authority failure, already authenticated terminal states must remain reusable on the next invocation.

### R4 — Real-owner persistence/restart integration is mandatory

The acceptance boundary is the assembled production owner:

```text
_eval2_target_size_endpoint_evidence
  -> _run_staged_evaluation_tasks
  -> parent authority validation/publication
  -> real CampaignStore durability/reopen
  -> target-size terminal-state barrier
  -> real reducer
```

The staged scheduler and parent publication owner may not be mocked. Expensive MACE prediction may be bounded/faked below this boundary. The integration must demonstrate successful publication, a later sibling interruption/failure, restart/reuse of accepted endpoints, execution of only missing work, and final reduction.

### R5 — Cancellation must affect active evaluation at safe boundaries

Stopping new queue admission is necessary but insufficient when already-running evaluation ignores `inference_cancellation_requested()`. Add cooperative checks at safe orchestration boundaries such as before expensive materialization, between calibration/inference waves or batches, and before final persistence. Do not attempt unsafe interruption inside a running device kernel.

If the legacy checkpoint reconstruction subprocess can remain active for a materially long interval after cancellation, replace only its waiting mechanism with an equivalent monitored child process that preserves timeout, stdout/stderr, return-code, cleanup, and reconstruction semantics while allowing termination of an owned child.

### R6 — Endpoint-specific checkpoint-byte authentication belongs in CPU prepare

The parent should own scientific enumeration, expected authority, deterministic keys, and durable-state lookup. Potentially expensive raw checkpoint/capsule byte hashing/authentication that is independent per endpoint should occur in the existing parallel CPU-prepare stage so it can overlap accelerator work. Do not move scientific decision authority into workers.

### R7 — Graph/static-cache reuse requires assembled target-size-owner evidence

Generic graph-cache tests are not enough. Add a bounded test through the real target-size orchestrator and staged scheduler, retaining the real graph/cache owner and replacing only expensive model forward work below it. Compatible endpoints over the same target geometry must demonstrate graph reuse, deterministic prediction ordering, and unchanged scientific results.

### R8 — Fine-grained performance evidence is required before G6/G7 can close with “no change”

The generic prepare/infer/finalize timings are insufficient to decide whether provider construction or repeated calibration is materially wasteful. Capture low-overhead endpoint timing/counters that distinguish, as available from existing owners:

- target role/materialization/preparation;
- checkpoint/model materialization;
- static-inference calibration;
- production forward/inference;
- prediction persistence and metric finalization;
- graph-cache hit/miss or reuse count;
- prediction-cache hit/miss.

G6 and G7 may close with no executable change only after these measurements show the proposed optimization is not materially justified. Absence of target GPU evidence is not sufficient to make that conclusion about CPU-visible provider/calibration overhead.

G8 outer-checkpoint GPU concurrency remains deferred to the existing final target-hardware qualification policy when no representative target GPU is available. Current implementation may close functional acceptance without G8 throughput qualification, but it must not claim the existing GPU schedule is globally optimal until that evidence exists.

### Rework sequencing after independent review

Resume implementation from the earliest affected gates rather than rebuilding the correctly landed architecture:

```text
R1/R2 -> G2/G4 resource + publication closure
R3/R4/R5 -> G3 restart/cancellation closure
R6 -> G2 prepare-stage closure
R7/R8 -> G5/G0 evidence closure
then explicit G6/G7 decisions
G8 deferred to FINAL-GPU1 when target hardware is required
then G9 final assembled acceptance/documentation
```

The two high-severity items R1 and R2 block implementation freeze/merge. R3-R8 block final workplan closure unless explicitly deferred above.

## Gates

### G0 — Baseline binding, reproducer, and measurement seam

**Goal:** Bind implementation to the reviewed correctness baseline and establish inexpensive evidence for the silent/serial path before material scheduling edits.

**Work:**

- Verify the current source still contains the REPAIR2 namespace bridge and independent target-only authorization described above.
- Add/retain a bounded reproducer proving TARGET-SIZE-V5 endpoint evaluation currently reaches the real endpoint owner after the precision banner.
- Capture per-endpoint timing categories at a low-overhead boundary: role/target preparation, checkpoint/model materialization, calibration, production inference, finalize/persistence, and graph/prediction cache-hit classification. Generic `prepare/infer/finalize` timing alone does not satisfy this obligation.
- Record the existing evaluation resource plan used by the ordinary staged evaluator so target-size migration can reuse, not rederive, those settings.

**Acceptance:**

- Existing exact-boundary and target-only correctness regressions pass.
- The reproducer identifies the endpoint population without changing scientific output.
- Timing/progress instrumentation is observational and does not alter identities/digests/results.
- The measurements are sufficiently decomposed to make a truthful G6 provider-reuse and G7 calibration-reuse decision.

### G1 — Restore hierarchical progress and existing phase telemetry

**Goal:** Eliminate the apparent freeze before changing scheduling semantics.

**Work:**

- Create one existing `_ProgressReporter`-style population reporter per exact target-size rung.
- Report each `(size, seed)` logical endpoint with stage/boundary identity, terminal progress, elapsed time, and observational ETA.
- Bind the existing inference phase callback across the complete endpoint operation so existing lower-level messages become visible: target monitor loading, cache checks, checkpoint payload/model restoration, accelerator inference, and CPU finalization.
- Preserve ContextVar callback propagation through any worker boundary.
- Render the existing resource plan and scheduler heartbeat for long-running work.
- Report authenticated cache reuse versus accelerator-required work.
- Serialize all concurrent phase/progress output through the reporter; do not add direct worker `print()` calls.

**Acceptance:**

- Real target-size endpoint orchestration emits start/phase/heartbeat/terminal progress through the real owner path.
- Progress advances on terminal logical endpoints, not future submission.
- Cache hits are reported only after authority validation.
- Scientific results and persisted identities are byte/semantic equivalent to the pre-reporting path.
- Existing non-target-size library consumers remain silent unless a callback is bound.

### G2 — Migrate target-size endpoint execution onto OPT-EVAL4 staged scheduling

**Goal:** Remove the private serial execution topology and reuse the existing evaluation scheduler/resource owners.

**Work:**

- Represent each successful exact endpoint as an immutable task descriptor with complete dedup/authority identity.
- Reuse `_run_staged_evaluation_tasks()` or the current canonical staged-evaluation owner instead of introducing another pool/scheduler.
- Put safe CPU/I/O preparation in the prepare stage, including endpoint-local raw checkpoint/capsule byte authentication that can be performed after parent authority enumeration; keep accelerator/model/inference work behind the existing GPU admission owner, and metric/persistence preparation in finalize.
- Reuse existing `parallel_evaluation_prepare_jobs`, `parallel_evaluation_finalize_jobs`, buffer limits, RAM ledger, CPU/native-thread policy, inference batch/concurrency policy, live VRAM admission, and OOM behavior.
- Keep parent-thread scientific publication and deterministic `(size, seed)` aggregation. Before persistence, bind every worker result to the expected immutable endpoint descriptor and validate its material authority/linkage; derive or independently verify publication keys in the parent.
- Ensure cache-only tasks can bypass accelerator work without bypassing parent validation/publication.
- Do **not** enable concurrent outer checkpoint GPU inference in this gate.

**Acceptance:**

- Direct serial reference versus staged execution yields identical typed target-size endpoint outcomes and reducer inputs for a bounded deterministic fixture.
- The real `_eval2_target_size_endpoint_evidence -> staged scheduler -> parent publication` path executes in integration testing; the scheduler owner itself is not mocked.
- CPU prepare/finalize overlap is structurally exercised while one canonical GPU owner remains in control.
- Output ordering, seed identity, checkpoint identity, metrics, and target-size decision are independent of task completion order.
- A forged/swapped otherwise-valid endpoint result is rejected by the parent before any scientific record is published.
- Endpoint-local checkpoint/capsule byte authentication is exercised in CPU prepare rather than serialized in the parent planning loop, while scientific authority enumeration remains parent-owned.

### G3 — Failure, cancellation, restart, and ranking-barrier closure

**Goal:** Prove concurrency does not weaken target-size failure or persistence semantics.

**Work:**

- Preserve typed TRAIN2 scientific-failure and EVAL2 numerical-failure conversion exactly.
- Propagate every non-approved exception as a fatal stage failure.
- Stop new admission after fatal failure/cancellation and clean owned work/resources using existing scheduler semantics. Add cooperative cancellation checks at safe prepare/materialize/inference-wave/finalize boundaries so active work can terminate without waiting for unrelated long operations to finish; owned long-running reconstruction children must be terminable without changing their success/timeout semantics.
- Keep partial attempt results non-authoritative.
- Reuse already accepted terminal evidence on restart and avoid resubmitting it unnecessarily, including deterministic persisted EVAL2 numerical/scientific failure evidence rather than keeping such failures only in an in-memory rung result.
- Require the complete expected endpoint key set to have terminal scientific states before invoking the reducer.
- Route cached and fresh results through one parent commit path.

**Acceptance:**

- Scientific failure of one candidate produces the same target-size failure evidence as serial execution.
- Programming/authority/corruption failures abort before ranking.
- Cancellation during prepare, inference, finalize, and publication cannot create false COMPLETE evidence.
- Restart after partial endpoint completion reuses authenticated successful endpoints, TRAIN2 scientific failures, and EVAL2 scientific failures, and computes only missing work.
- Duplicate logical endpoints cannot be scheduled/published twice.
- A real `CampaignStore` integration executes the assembled target-size orchestrator, staged scheduler, parent validation/publication, interruption/restart, and reducer; only expensive inference below that owner may be faked.
- Cancellation/fatal sibling tests prove both new admission stops and already-running evaluation observes cancellation at safe boundaries without publishing partial COMPLETE state.

### G4 — Consolidate common target data and content-address computational views

**Goal:** Remove repeated parsing/materialization/view construction for the common development-complement target without weakening scientific authority.

**Work:**

- Introduce or reuse an immutable `SharedTargetEvaluationContext`-equivalent value owned per compatible label-domain + target-role/rung + target-size-generation authority.
- Resolve/materialize/authenticate the shared `size_development_complement` once per compatible context.
- Separate scientific identity from computational-cache identity.
- After byte authentication, key immutable parse/view reuse by content digest plus parser/evaluation schema/policy/options rather than path alone.
- Treat path/inode/mtime metadata as staleness/performance hints, never as scientific identity.
- Enforce read-only sharing or clone mutable `Atoms`/consumer inputs at the mutation boundary.
- Account shared resident target/view memory once in the stage resource plan and per-task incremental buffers separately.

**Acceptance:**

- Multiple endpoint paths containing the same authenticated target content parse/build the immutable evaluation view once within the admitted cache lifetime.
- Different content digests or incompatible parser/view policy versions cannot reuse the cache entry.
- Byte-equal data under distinct scientific authorities does not collapse role/provenance validation.
- RAM accounting demonstrates shared resident bytes are neither multiplied per endpoint nor omitted. This must use an actual or representative `PreparedCheckpointEvaluation` containing the shared target/view; scalar stand-ins are insufficient.
- Per-task prepared-payload accounting excludes only identities already charged as stage-shared residency and still charges all endpoint-incremental state.
- Serial and staged scientific outputs remain equivalent.

### G5 — Close existing graph/static-inference reuse for the target-size population

**Goal:** Ensure TARGET-SIZE-V5 benefits from the existing expensive-computation reuse and adaptive accelerator machinery.

**Work:**

- Route target-size accelerator work through the canonical `StaticMaceInferenceExecutor` and existing graph/prediction cache interfaces.
- Verify identical target geometry reuses persistent graph materialization across compatible candidate checkpoints where current graph-cache identity permits it.
- Preserve joint `(batch_size, concurrent_model_jobs)` selection, live VRAM clamping, worker-private inference providers, CUDA-stream policy, and bounded OOM backoff.
- Surface low-cost cache/timing diagnostics sufficient to distinguish graph reuse, prediction reuse, model materialization, calibration, and production inference.
- Do not add a target-size-specific graph cache or independent GPU scheduler.

**Acceptance:**

- Existing static-inference resource/concurrency controls are demonstrably active on the real target-size path.
- Compatible repeated target geometry shows graph-cache reuse without changing prediction values or ordering through the real target-size orchestrator + staged scheduler + graph/cache owner path; generic executor-only cache tests do not close this claim.
- Prediction-cache reuse is authority-correct and bypasses unnecessary inference.
- OOM/resource failure behavior remains bounded and fail-closed under existing policy.
- Endpoint diagnostics distinguish graph reuse, prediction reuse, model materialization, calibration, production inference, and finalization sufficiently to support G6/G7 decisions.

### G6 — Measure and, only if justified, activate compatible provider/model-shell state reuse

**Goal:** Remove repeated provider/model-shell construction only when it is a measured material cost and the existing compatibility seam can do so safely.

**Work:**

- Use G0/G5 timings to quantify checkpoint/provider materialization share.
- If material, reuse the existing `candidate_provider` / `load_compatible_model_state()`-style seam for strictly compatible checkpoints.
- Keep each mutable provider shell worker-private and single-owner.
- Require exact model class/state-key/tensor-shape/dtype and existing scientific identity checks.
- Rebuild/invalidate calculator, compiled/converted model, or other state-dependent caches after weight replacement unless independently proven weight-independent.
- Fall back automatically to standard fresh materialization for incompatible or unsafe cases.

**Acceptance:**

- Fresh-provider versus compatible-state-swap predictions/metrics are equivalent on a bounded representative fixture.
- Incompatible state is rejected rather than coerced.
- No mutable provider is simultaneously used by concurrent workers.
- Resource cleanup remains correct after success/failure.
- If the required decomposed G0/G5 measurements do not show material value, close this gate explicitly with no product change; generic whole-stage timings or absence of GPU hardware are not sufficient evidence.

### G7 — Calibration-reuse evidence gate

**Goal:** Decide whether exact-model static-inference calibration identity is materially wasteful across screening checkpoints without speculatively weakening resource safety.

**Work:**

- Use staged timing evidence to quantify calibration fraction and repeated operating-point similarity across candidate checkpoints.
- Keep exact-model calibration identity unchanged by default.
- Reopen only this narrow design surface if repeated calibration is a material wall-time contributor and evidence supports a stronger architecture/workload-compatible runtime profile identity.
- Any broadened profile must still live-clamp against current VRAM/resources and retain OOM backoff/first-use validation.

**Acceptance:**

- Either (a) no change is made because decomposed endpoint measurements show calibration is not materially dominant, or (b) an independently justified compatibility rule is implemented with equivalence/resource-safety tests and representative benchmark evidence.
- Scientific checkpoint/model identity is never weakened merely to share a runtime performance profile.

### G8 — Outer checkpoint GPU-concurrency decision gate

**Goal:** Consider inter-checkpoint GPU concurrency only after consolidation, pipeline overlap, caching, and canonical static-inference concurrency are operating.

**Work:**

- Measure residual GPU utilization/idle intervals after G1-G7.
- Compare the existing one-admitted-checkpoint + internal static-inference concurrency strategy against multi-checkpoint residency only if meaningful idle capacity remains.
- If outer concurrency is justified, design one shared GPU admission authority that jointly accounts checkpoint concurrency, per-checkpoint inference jobs, batch size, and aggregate VRAM. Do not nest independent controllers.
- Preserve deterministic aggregation and worker-private mutable model state.

**Acceptance:**

- No product change is required when representative target-hardware evidence shows existing canonical inference saturates the useful accelerator envelope.
- When representative target GPU hardware is unavailable during implementation, this gate is explicitly deferred to the project's final GPU qualification (`FINAL-GPU1`) rather than guessed closed; functional implementation may proceed, but no claim of globally optimal GPU scheduling is permitted.
- Any adopted outer concurrency must show representative wall-time benefit without unacceptable VRAM/RAM growth, correctness drift, or instability.
- This gate may trigger a bounded design reopen; implementation must not invent outer concurrency ad hoc.

### G9 — Final assembled regression, integration, benchmark evidence, and documentation closeout

**Goal:** Close the complete affected surface after all accepted executable edits.

**Functional acceptance:**

Run focused and affected regression covering at minimum:

- target-size exact-boundary topology and `1/3/10` flexible fidelity;
- paired screening-seed ranking and deterministic endpoint order;
- EVAL2 target-only authorization and target-monitor override independence;
- DATA2A/TARGET-DATA2B/REPAIR2 materialization authority bridge;
- `_eval2_target_size_endpoint_evidence` real orchestration;
- OPT-EVAL4 staged scheduling/resource controls;
- checkpoint model materialization/reconstruction;
- static MACE inference and graph/prediction/monitor/view caches;
- TRAIN2 exact continuation and restart;
- candidate scientific failure versus fatal infrastructure failure;
- cancellation/partial publication/restart, including persisted EVAL2 scientific-failure reuse;
- parent authority validation with forged/swapped-result rejection;
- exact-once shared target/view RAM accounting using real prepared-evaluation payloads;
- campaign CLI integration through `select-target-size -> evaluate -> reducer` with bounded scientific fixtures;
- successful endpoint publication -> later sibling fatal failure/interruption -> `CampaignStore` reopen -> reuse of accepted endpoints -> only missing work -> real reducer;
- graph-cache reuse through the assembled target-size owner rather than only generic executor tests.

The real target-size orchestrator and staged scheduler must execute for the material integration claim. Expensive MACE kernels, external data volume, or accelerator work may be bounded/faked below that semantic-owner boundary where appropriate.

If the affected surface cannot be confidently bounded after implementation, run the broader MLFF regression suite.

**Performance acceptance:**

Use bounded representative before/after evidence on the same source-compatible inputs/environment where practical. Record:

- population wall time;
- per-endpoint target-prep/checkpoint-materialize/calibrate/production-infer/finalize time;
- target parse/view build counts;
- graph/prediction cache hit/miss counts where available;
- configured/selected prepare/finalize workers and inference `(B,J)` operating point;
- peak/bounded RAM and VRAM evidence appropriate to the available environment;
- cold versus warm/restart behavior where relevant.

Do not invent a fixed speedup percentage before a representative baseline exists. An optimization is accepted because it removes demonstrated redundant work or produces representative material improvement while preserving scientific equivalence and resource safety, not because it satisfies an arbitrary number.

Full long data-heavy production qualification and final target-hardware GPU qualification remain separate and deferred. Do not claim production GPU throughput/VRAM qualification unless it was actually run on the supported target environment.

**Documentation closeout:**

After implementation is accepted:

- update `docs/arch_manuals/mlff_training_data_architecture.md` and any dedicated evaluation/checkpoint manuals whose current-state execution ownership changed;
- update affected specifications only for accepted durable behavior/contracts, not workplan chronology;
- regenerate required documentation PDFs/manifests under repository policy when permanent Markdown authority changes;
- record completed chronology/evidence in the appropriate history/audit/benchmark locations;
- archive this workplan when the transition is accepted.

## Implementation authority

### Frozen decisions

Implementation must not change without explicit design reopen:

- exact-boundary target-size scientific semantics;
- target-only ranking scope;
- authority/provenance bridges fixed on the reviewed baseline;
- parent-thread durable scientific publication **after parent validation against the immutable expected endpoint authority**;
- one canonical GPU resource owner during the mandatory migration;
- deterministic externally visible aggregation;
- fail-closed distinction between scientific candidate failure and infrastructure/programming failure;
- reuse of existing staged evaluation/resource configuration before adding target-size-specific controls.

### Delegated mechanics

Implementation may choose locally equivalent details for:

- exact immutable task/result dataclass names;
- reporter formatting consistent with existing CLI conventions;
- placement of the shared target context/cache helper;
- internal callback/context propagation helper reuse;
- exact prepare/finalize decomposition, provided semantic-owner and resource boundaries above remain intact;
- low-overhead timing/counter representation.

### Reopen only on evidence

Reopen only the affected design surface if evidence shows:

- `_run_staged_evaluation_tasks()` cannot represent target-size typed failure/publication semantics without compromising its existing consumers;
- shared immutable target data cannot be safely represented within current RAM/cache ownership;
- current static-inference resource authority cannot safely serve the target-size endpoint population;
- provider state replacement has unavoidable state-dependent cache hazards;
- calibration reuse or outer checkpoint GPU concurrency is materially beneficial but requires a new compatibility/admission contract;
- representative measurement demonstrates the proposed consolidation materially regresses end-to-end performance/resources despite correct implementation.

Do not reopen scientific target-size ranking or exact-boundary policy merely because an execution optimization is difficult.

## Closeout

When all mandatory gates pass and optional evidence gates are either implemented or explicitly closed with no justified change:

1. reconcile every obligation in this plan against the assembled candidate;
2. run final affected regression and real-owner integration;
3. record bounded performance evidence without conflating it with production qualification;
4. update permanent architecture/specification authority for accepted current behavior;
5. record chronology/evidence in permanent locations;
6. archive this workplan when it no longer coordinates active implementation.
