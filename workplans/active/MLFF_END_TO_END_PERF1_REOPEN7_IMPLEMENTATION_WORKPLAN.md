# MLFF-END-TO-END-PERF1 Seventh-Reopen Narrow Closure Implementation Workplan

Status: **ACTIVE — FINAL FUNCTIONAL CLOSURE REOPENED**  
Branch: `feat/mlff-end-to-end-performance-v1`  
Reviewed implementation tip: `1d48a68995bbfe2d488b1d7722135fb9d149aa23`  
Parent active plan: `workplans/active/MLFF_END_TO_END_PERF1_REOPEN6_IMPLEMENTATION_WORKPLAN.md`  
Date reopened: 2026-08-24

## 1. Authority and scope

This file is the authoritative seventh-reopen delta for the remaining MLFF-END-TO-END-PERF1 functional closeout. It supersedes the REOPEN6 final acceptance conclusion while preserving every REOPEN6 design decision, implementation, test result, and closed gate that is not explicitly reopened here.

The REOPEN6 statement

> **FUNCTIONAL IMPLEMENTATION ACCEPTED — TARGET-WORKSTATION GPU QUALIFICATION DEFERRED**

is withdrawn as a current acceptance conclusion. Its recorded tests remain historical evidence for unchanged dimensions only.

This is a deliberately **narrow closure patch**, not an architecture redesign and not an invitation to reopen unrelated MLFF work. The independent review of implementation tip `1d48a68995bbfe2d488b1d7722135fb9d149aa23` found four implementation leaks plus one acceptance-fixture gap inside the already-frozen PERF1 surface:

1. production inference can still convert a J>1 worker backoff into the global single-provider batch ceiling;
2. fresh automatic concurrency can still grow private providers without a valid residency estimate when configured maximum J is greater than 2;
3. `InferenceExecutionPlan` wire/digest semantics changed while retaining schema `v2`, breaking historical-v2 restart compatibility;
4. private-provider pool shrink can trigger repeated/global CUDA cache reclamation instead of one executor-owned CUDA lifecycle release;
5. the REOPEN6 “assembled integration” exercises `_StagedEvaluationTask` callbacks rather than the required real production orchestration/state boundaries.

No reviewed evidence requires replacement of the accepted resource model, runtime authority, executor/provider ownership, static profile architecture, staged-EVAL ownership, numerical policy, or scientific workflow.

## 2. Frozen mechanisms — preserve without redesign

Implementation MUST preserve these accepted mechanisms unless a redesign trigger in Section 12 fires with concrete evidence:

- `StaticInferenceRuntimeAuthority` remains the sole `(batch_size, concurrent_model_jobs)` operating-point, resource, failure-boundary, selection, and profile-reuse authority;
- `StaticMaceInferenceExecutor` remains the sole persistent provider/model-shell pool and static-inference execution owner;
- real worker-private J-way execution and observed-concurrency evidence;
- deterministic prediction aggregation/order;
- one outer staged-EVAL inference owner, with no outer x inner inference-concurrency multiplication;
- persistent lazily grown private-provider pool;
- complete-first-job one-slot CUDA calibration;
- normalized post-base incremental RAM/VRAM coordinates with configured live safety fractions reapplied on reclamp;
- pre-base-model outer admission for DEPLOY/PES/LOCKED and equivalent command paths;
- pre-growth and post-growth live admission before worker-wave launch;
- v5 static runtime-profile/evidence semantics and conservative provider-residency floor;
- executor-owned explicit CUDA synchronization inside steady-state timing;
- graph-cache/head/checkpoint/dtype/precision behavior;
- restart/reuse/scientific identity semantics except the explicit execution-plan schema migration required below;
- DYN/RELAX architecture and unrelated accepted PERF1 gates;
- target-workstation RTX 3090/data-heavy production qualification remains deferred until final release handoff.

Do NOT add a second scheduler, retry manager, provider registry, resource authority, profile authority, or consumer-specific static inference path.

## 3. Engineering invariants for this closeout

The closure patch must establish all of the following on the same final candidate:

### 3.1 Failure-learning coordinate

The single-provider batch ceiling is a **J=1 capability constraint only**.

For a requested production/calibration point `(B, J)`:

- `J == 1` execution OOM or bounded internal batch backoff may lower the global single-provider safe batch ceiling;
- `J > 1` execution OOM or bounded internal batch backoff creates or tightens a two-dimensional `(B, J)` execution boundary;
- provider-pool/materialization OOM affects concurrency/provider-growth capability, not batch capability;
- transient live-resource rejection is not persisted as permanent capability evidence;
- successful predictions produced by bounded worker-local subdivision may be retained for the current wave, but the observed resource boundary must govern subsequent operating-point selection through the existing authority.

A J>1 runtime event must never invalidate a larger-B safe point already established at lower J solely by mutating the global batch ceiling.

### 3.2 Fresh private-provider growth

Fresh automatic `J > 1` growth is permitted only when a valid conservative provider-residency requirement exists.

If no configured/measured/persisted conservative provider estimate is available for fresh growth:

```text
candidate_concurrencies == (1,)
```

regardless of whether the configured maximum concurrency is 2, 4, 8, or larger.

Compatible v5 profile evidence with a valid conservative provider requirement remains valid reuse evidence; this fail-closed rule concerns fresh automatic growth without such authority.

### 3.3 CUDA cache reclamation ownership

Private-pool shrink is one executor-owned lifecycle transaction:

1. retire/close every surplus private provider without each provider independently flushing the global CUDA allocator cache;
2. after all surplus provider owners are released, perform at most one executor-owned CUDA allocator cache release if and only if that executor is CUDA-backed;
3. then refresh live resource telemetry before lower-J readmission.

A CPU executor running in a process where CUDA happens to be globally available must not flush unrelated CUDA allocator cache.

Terminal base-provider cleanup may retain its normal terminal release behavior.

### 3.4 Execution-plan persistence compatibility

Any change to serialized/digested `InferenceExecutionPlan` payload shape must use a new schema version.

Historical valid v2 payloads must:

1. be validated against the exact historical-v2 payload/digest shape;
2. migrate into the current representation;
3. never be rejected merely because current fields did not exist in v2;
4. never reinterpret absent historical provider-residency fields as historical evidence.

New writes must use the new schema.

### 3.5 Functional integration boundary

A bounded integration test is accepted only when it enters through real production orchestration/state-transition boundaries. Stage names attached to synthetic callbacks are not sufficient.

Expensive numerical/training backends may be stubbed **below** their production-facing interfaces, but production orchestration, manifests/state/restart/resource-plan/profile-reuse/publication wiring must remain real.

## 4. Gate CLOSE-1 — unify production execution-OOM/backoff learning

### 4.1 Objective

Make the production execution path obey exactly the same two-dimensional failure semantics already accepted for calibration.

### 4.2 Required implementation

Inspect the production loop in `StaticMaceInferenceExecutor._predict_joint_owned()` and the return contract of `_run_joint_wave()`.

The production path currently consumes `observed` and `safe_ceiling` but discards the returned backoff count, then directly tightens `authority.learned_safe_batch_ceiling`. Replace that behavior with authority-owned causal learning.

After a production wave requested at `(B, J)`:

- if `backoffs == 0` and the wave completed at the requested batch, do not create failure evidence;
- if bounded internal worker subdivision/backoff occurred or `safe_ceiling < B`, record an `execution-oom` boundary through `StaticInferenceRuntimeAuthority.record(...)` using the **requested** `(B, J)`;
- for `J == 1`, the existing authority logic may tighten the global single-provider ceiling;
- for `J > 1`, the existing authority logic must create/tighten only the 2-D execution boundary;
- do not directly assign the global batch ceiling from a J>1 worker-local safe ceiling;
- retain valid predictions already produced by bounded subdivision for the current wave, then allow the next wave to reselect using updated authority state;
- recognized hard execution OOM before successful completion continues to use the same existing failure path;
- non-resource exceptions still propagate.

Do not add another failure learner or retry loop.

### 4.3 Mandatory focused reproducers

Add focused tests proving at minimum:

1. `B=16,J=1` and `B=16,J=2` remain safe after a later production `B=16,J=4` internal backoff;
2. the J=4 backoff records a `(16,4)` execution boundary;
3. a subsequent production selection can still choose `B=16,J=1/2` when otherwise best/admissible;
4. a production `B=16,J=1` backoff still lowers the global single-provider batch ceiling;
5. predictions returned by a successfully subdivided current wave remain numerically/order equivalent;
6. no infinite retry/deadlock is introduced.

### 4.4 Gate acceptance

Before CLOSE-2, run focused tests plus affected static inference, runtime-profile/reuse, scheduler, numerical-equivalence, and restart regression for this behavior-changing gate.

## 5. Gate CLOSE-2 — finish fresh-growth fail-closed semantics and pool-shrink lifecycle

### 5.1 Objective

Close the remaining provider-growth and CUDA-cache ownership leaks without changing the accepted persistent-pool architecture.

### 5.2 Fresh candidate-concurrency requirement

`StaticInferenceRuntimeAuthority.candidate_concurrencies` must fail closed for all fresh private-provider growth when `private_provider_growth_available` is false.

Required behavior:

```text
if no valid provider-growth requirement:
    candidate_concurrencies = (1,)
else:
    construct the existing bounded geometric J ladder through configured maximum J
```

Do not merely omit the final configured cap while still exposing intermediate J=2/J=4 candidates.

Profile reuse may expose J>1 only when the reused evidence provides valid v5 provider-residency authority and passes current live admission.

### 5.3 Private-pool shrink requirement

Refine `_retire_private_providers()` and provider close ownership so that shrinking from J-high to J-low:

- closes each surplus private provider exactly once;
- does not trigger per-provider global CUDA cache flushes;
- performs one executor-owned allocator cache release after all surplus CUDA provider owners are gone;
- performs zero CUDA allocator cache releases for CPU executors even when `torch.cuda.is_available()` globally returns true;
- preserves existing partial-growth cleanup and base-provider ownership;
- refreshes/reclamps live resources before lower-J admission as already required by the accepted design.

For `MaceCalculatorProvider`, using its existing `close(release_cuda_memory=False)` capability for private-slot retirement is preferred over introducing new lifecycle machinery. Generic providers that only expose `close()` remain supported.

### 5.4 Mandatory focused reproducers

Add tests proving at minimum:

1. configured `max_J=4` with no valid provider-residency estimate yields `(1,)` and never calls the private provider factory;
2. same for `max_J=8`;
3. a valid estimate restores the bounded geometric J ladder;
4. compatible valid v5 profile evidence can still reuse J>1 subject to current admission;
5. CUDA pool shrink J4→J2 closes exactly two surplus providers and performs exactly one executor-owned cache release;
6. CPU pool shrink performs zero CUDA cache releases even on a CUDA-capable host/test double;
7. no cache flush occurs merely between same-J steady-state waves;
8. partial provider-growth failure cleans only attempt-local/surplus state and preserves accepted lower pool;
9. lower-J readmission sees refreshed resource state after shrink.

### 5.5 Gate acceptance

Before CLOSE-3, run focused lifecycle tests plus affected static inference, provider cleanup, resource-admission, profile reuse, staged-EVAL, DEPLOY/PES/LOCKED, and command-boundary regression.

## 6. Gate CLOSE-3 — restore `InferenceExecutionPlan` wire/restart compatibility

### 6.1 Objective

Repair the schema/digest drift without changing scientific identity or runtime authority.

### 6.2 Required schema change

Bump the current execution-plan schema to a new version, expected:

```text
mdstats.inference-execution-plan.v3
```

and retain explicit legacy constants/loaders for v2 and v1.

The v3 payload may contain the current fields including:

- batch policy/sizes;
- selected concurrency;
- CPU/RAM/VRAM policy fractions;
- provider residency RAM/VRAM estimates;
- graph/monitor/prediction cache flags;
- rationale.

### 6.3 Exact historical-v2 migration

The v2 loader must construct the **historical v2 payload shape**, excluding fields introduced only after v2 was originally defined, and validate the supplied historical digest against that exact shape.

Only after successful validation may it create a current v3 object.

For historical v2:

- provider-residency fields absent in the old wire format become `None`/unavailable in the migrated runtime plan unless recomputed by the normal current resource-planning path;
- do not invent persisted historical resource evidence;
- preserve supported historical batch/concurrency/fraction/cache choices;
- append an explicit migration rationale if current conventions use such rationale markers;
- current v3 serialization/digest must round-trip exactly.

Keep the existing exact v1 migration behavior.

### 6.4 Mandatory focused reproducers

Add fixed serialized fixtures or literal payloads proving:

1. a pre-REOPEN6 valid v2 payload with its original digest loads successfully;
2. the same payload with a corrupt digest is rejected;
3. migration produces a valid v3 plan without fabricated provider residency evidence;
4. v3 write/read/digest round-trip is exact;
5. existing v1 migration remains valid;
6. restart/manifest consumers accepting historical v2 plans continue through the normal current planning/reuse path;
7. scientific identity/checkpoint/head/numerical semantics are unchanged by the runtime schema migration.

### 6.5 Gate acceptance

Before CLOSE-4, run focused serialization tests plus affected campaign execution, restart/reuse, manifest, staged-EVAL, DEPLOY/PES/LOCKED, publication/command-boundary, and numerical-equivalence regression.

## 7. Gate CLOSE-4 — real bounded assembled production-interface integration

### 7.1 Objective

Replace the insufficient synthetic stage-name integration evidence with one bounded CPU-capable fixture that exercises the real assembled production boundaries required by REOPEN6.

The existing `test_reopen6_bounded_assembled_stage_chain_restarts_with_one_outer_owner` remains useful staged-scheduler coverage but MUST NOT be counted as the required assembled campaign integration by itself.

### 7.2 Required integration shape

Create or extend a bounded self-contained integration fixture that enters through the highest practical real campaign/public orchestration entrypoint and exercises the available chain:

```text
preflight
-> preparation/materialization
-> TRAIN/EVAL
-> DEPLOY
-> PES
-> RELAX
-> DYN
-> selection/publication
```

The fixture must:

- use a temporary/self-contained campaign root;
- use tiny synthetic atomic/configuration data sufficient for real orchestration contracts;
- exercise real stage/state transitions rather than manually naming callbacks after stages;
- exercise real manifests/ledgers/status artifacts where those are the production authority;
- exercise real resource-plan propagation into static inference;
- exercise runtime-profile persistence and a second invocation that performs real restart/profile reuse rather than simply rerunning identical callbacks;
- exercise the real production-facing DEPLOY/PES/RELAX/DYN boundaries available in the repository;
- exercise real final selection/publication state where available;
- allow expensive MACE training/model inference and LAMMPS/numerical work to be stubbed **below** their production-facing interface only;
- avoid externally supplied LTA roots, long trajectories, full MACE training, or target-GPU requirements;
- run on CPU when GPU is unavailable;
- exercise at least one bounded assembled failure/cancellation/cleanup boundary where practical without duplicating the entire chain.

If the repository has multiple orchestration layers, prefer the highest layer that is deterministic and bounded enough for routine regression. Do not create a parallel “test-only orchestrator” that restates production sequencing.

### 7.3 Restart invocation

The second invocation must demonstrate actual restart semantics through persisted production state. At minimum establish that completed work/state/profile evidence is recognized and reused through the production restart path rather than merely asserting two fresh invocations return the same names/results.

### 7.4 Gate acceptance evidence

Record the assembled integration result separately from focused and regression suites.

A passing callback-only staged scheduler test is not a substitute.

## 8. FINAL-CLOSE acceptance sequence

After the final executable edit from CLOSE-1..4:

### 8.1 Fresh affected-surface re-derivation

Independently re-derive the complete affected behavioral surface and search specifically for:

- direct writes to `learned_safe_batch_ceiling` from J>1 execution paths;
- worker-local backoff/safe-ceiling results not routed through causal authority learning;
- any fresh J>1 candidate path available without valid provider requirement;
- provider-pool OOM affecting batch capability;
- live-resource rejection becoming permanent capability evidence;
- pool shrink causing repeated/global cache flushes;
- CPU executors touching CUDA allocator cache;
- historical v2 execution-plan bytes validated using current-v3 payload shape;
- stale schema strings whose digest payload changed;
- profile/restart paths bypassing current resource admission;
- direct static-inference consumer bypasses;
- duplicate authorities/provider pools;
- provider sharing/leaks/double-close;
- candidate/wave launch without immediate live admission;
- nested outer x inner EVAL concurrency;
- scientific identity/configuration changes caused by runtime evidence;
- integration fixtures that substitute synthetic callbacks for real production state boundaries.

### 8.2 Mandatory focused suite

Every new reproducer from CLOSE-1, CLOSE-2, and CLOSE-3 must execute successfully on the final candidate. Required tests that do not run are not passes.

### 8.3 Fresh final affected regression

After all executable changes, rerun the complete affected regression covering at minimum:

- static MACE inference/batching;
- v5 runtime profile persistence/reuse/restart;
- `InferenceExecutionPlan` v1/v2 migration and v3 current persistence;
- resource planning/live telemetry;
- adaptive CUDA scheduler and one-slot completion calibration;
- persistent provider growth/shrink/cleanup;
- staged EVAL/campaign execution;
- DEPLOY/PES/LOCKED command paths;
- replay/static consumers;
- graph cache/head/checkpoint/dtype/precision semantics;
- numerical/reference equivalence;
- DYN/RELAX/shared-resource code where plausibly affected;
- failure/cancellation/cleanup paths;
- command/publication/restart boundaries.

Run broader/full available regression when the final affected surface cannot be bounded confidently. Pre-existing unrelated unavailable checks may be attributed explicitly but are never counted as passes.

### 8.4 Separate assembled integration

Run the CLOSE-4 production-interface integration **separately** on the same final candidate and record its exact command/result independently from the affected regression count.

### 8.5 Repository-required checks

Run repository-required static/compile/diff checks and any available CI-equivalent checks. An unavailable external dependency or pre-existing unrelated fixture problem is recorded explicitly, never converted into a pass.

Full target-workstation RTX 3090/data-heavy qualification remains deferred and is not part of functional closure.

## 9. Stage-local implementation sequence

Implementation must proceed in this order:

```text
CLOSE-1
production 2-D execution-OOM/backoff learning
    -> focused tests
    -> affected static/profile/scheduler regression

CLOSE-2
fresh-growth fail-closed semantics
+ one-owner pool-shrink CUDA reclamation
    -> focused lifecycle/resource tests
    -> affected consumer/resource regression

CLOSE-3
InferenceExecutionPlan v3
+ exact historical-v2 migration
    -> focused persistence tests
    -> affected restart/manifest/campaign regression

CLOSE-4
real bounded assembled production-interface integration
    -> execute assembled integration

FINAL-CLOSE
fresh affected-surface re-derivation
    -> all mandatory focused reproducers
    -> fresh complete affected regression
    -> separate fresh assembled integration
    -> repository-required/broader available checks
```

Do not defer all validation to FINAL-CLOSE. Stage-local affected regression is mandatory after each material behavior-changing gate.

## 10. Expected affected files

Inspect and modify only as required by the narrow defects, expected primarily:

- `mdstats/training_data/model_features.py`;
- `mdstats/training_data/campaign_execution.py`;
- provider close/resource helpers directly used by the persistent static-inference pool;
- runtime-plan serialization/restart consumers;
- `tests/test_mlff_static_mace_inference.py`;
- resource/provider lifecycle tests;
- campaign/restart/execution-plan serialization tests;
- `tests/test_mlff_perf1_reopen6_assembled_integration.py` or a replacement bounded assembled integration fixture;
- only direct transitive consumers found by final affected-surface derivation.

Do not edit scientific schemas, training algorithms, target-size architecture, DYN/RELAX scientific behavior, or unrelated MLFF stages merely to satisfy this closeout.

## 11. Gate disposition after seventh-reopen review

- R0: **CLOSED**
- R1: **CLOSED**
- complete-first-job one-slot CUDA calibration: **CLOSED subject final regression**
- normalized post-base incremental resource coordinate: **CLOSED subject final regression**
- v5 static runtime-profile/provider requirement architecture: **CLOSED subject final regression**
- genuine worker-private J-way concurrency: **PRESERVE**
- persistent provider pool: **PRESERVE**
- CLOSE-1 production 2-D failure-learning reconciliation: **OPEN**
- CLOSE-2 fresh-growth fail-closed and pool-shrink reclamation: **OPEN**
- CLOSE-3 execution-plan persistence compatibility: **OPEN**
- CLOSE-4 real bounded assembled integration: **OPEN**
- staged-EVAL one-outer-owner architecture: **PRESERVE**
- DEPLOY/PES/LOCKED pre-base admission: **PRESERVE**
- graph/head/checkpoint/dtype/precision/scientific identity: **PRESERVE**
- DYN/RELAX architecture: **PRESERVE**
- full RTX 3090/data-heavy qualification: **DEFERRED**

The REOPEN6 acceptance record is historical evidence only until these open gates pass on one final candidate.

## 12. Genuine redesign triggers

Stop dependent implementation and reopen only the affected design surface if evidence demonstrates that:

- the existing authority cannot represent production internal-backoff boundaries without duplicating failure ownership or producing incorrect operating-point selection;
- valid fresh J>1 operation cannot be safely exposed using the already-accepted provider-residency authority;
- provider memory cannot be released sufficiently on pool shrink without abandoning the persistent-pool model;
- exact historical-v2 migration cannot be implemented without changing scientific/runtime semantics beyond the execution-plan wire contract;
- a bounded assembled integration cannot enter real production orchestration without materially changing public production architecture;
- scientific/numerical outputs change outside frozen tolerances.

Ordinary bugs, a v3 execution-plan schema bump, local close-call specialization, authority routing of backoff evidence, candidate-filter correction, test-harness construction, or additional regression fixtures are **not** redesign triggers.

## 13. Product-complexity rules

Use the accepted ownership model and prefer:

```text
reuse -> consolidate -> refactor -> delete
```

Specifically:

- route production backoff through existing `StaticInferenceRuntimeAuthority.record()` rather than add a new learner;
- express no-estimate growth through existing candidate-generation authority rather than a consumer-specific guard;
- use existing provider close controls and executor lifecycle ownership rather than a cache manager;
- migrate historical execution-plan schemas in the existing owning serialization path rather than add translators elsewhere;
- use existing production orchestration for integration rather than a test-only parallel workflow;
- delete superseded special-case code only when the replacement authority is complete and regression-clean.

## 14. Final completion condition

MLFF-END-TO-END-PERF1 may return to:

**FUNCTIONAL IMPLEMENTATION ACCEPTED — TARGET-WORKSTATION GPU QUALIFICATION DEFERRED**

only when all of the following are true on the same final candidate:

- CLOSE-1, CLOSE-2, CLOSE-3, CLOSE-4, and FINAL-CLOSE are accepted;
- a J>1 production internal batch backoff cannot lower the global J=1 batch ceiling;
- J=1 production/calibration backoff still establishes the global single-provider batch constraint;
- J>1 execution failures/backoffs create only valid 2-D execution boundaries;
- provider-pool OOM remains concurrency-only;
- transient live-resource rejection remains non-permanent capability evidence;
- fresh automatic J>1 growth is impossible without valid conservative provider-residency authority for every configured maximum J;
- compatible valid v5 profile reuse retains safe J>1 operation subject to current admission;
- private-pool shrink closes surplus providers exactly and performs at most one executor-owned CUDA allocator release per shrink transaction;
- CPU executors never flush CUDA allocator cache merely because CUDA exists in the process;
- historical valid `InferenceExecutionPlan` v2 payloads validate against their historical shape and migrate successfully;
- new execution plans use v3 and round-trip exactly;
- no fabricated provider-residency evidence is inferred from legacy execution-plan bytes;
- real worker-private J concurrency, deterministic ordering, persistent provider reuse, exact cleanup, numerical equivalence, scientific identity, and restart behavior remain regression-clean;
- every mandatory focused reproducer executes successfully;
- fresh final affected-surface regression executes successfully;
- a **separate bounded assembled production-interface integration using real orchestration/state boundaries executes successfully** on the same final candidate, including a real restart/profile-reuse second invocation;
- repository-required/broader checks are recorded, and unrelated unavailable items are explicitly attributed rather than counted as passes;
- full target-workstation RTX 3090/data-heavy production qualification remains deferred to final release handoff.

If these conditions pass without firing a redesign trigger, archive this seventh-reopen workplan with the final evidence and close PERF1 functional implementation.