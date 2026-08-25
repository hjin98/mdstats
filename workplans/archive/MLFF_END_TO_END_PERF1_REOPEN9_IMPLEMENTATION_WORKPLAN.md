# MLFF-END-TO-END-PERF1 Ninth-Reopen Final Transactional / Assembled-Acceptance Closeout Workplan

Status: **ACTIVE — NARROW FINAL CLOSURE FIX REQUIRED**  
Branch: `feat/mlff-end-to-end-performance-v1`  
Reviewed implementation tip: `c60a52d07cc58ee2d9a857c6f7af34f67ac3a006`  
Parent active delta: `workplans/active/MLFF_END_TO_END_PERF1_REOPEN8_IMPLEMENTATION_WORKPLAN.md`  
Date reopened: 2026-08-24

## 1. Authority and scope

This file is the authoritative narrow delta-workplan for the remaining MLFF-END-TO-END-PERF1 closeout after independent review of implementation tip `c60a52d07cc58ee2d9a857c6f7af34f67ac3a006`.

REOPEN8 implemented its principal source corrections correctly. This round **does not reopen the PERF1 architecture**. It reopens only the following three surfaces:

1. **provider-slot commit exception atomicity:** `_ensure_provider_pool()` can still partially mutate the provider pool and its parallel bookkeeping arrays if an exception occurs after provider construction but during the slot commit, allowing double-close, metadata-length drift, a masked original exception, or leaked ownership;
2. **historical execution-plan v2 production-consumer evidence:** v2 -> v3 source wiring is now correct, but the mandatory test still invokes the resolver/static helper directly rather than letting a real EVAL/DEPLOY/PES production consumer encounter the persisted historical record;
3. **assembled production integration:** the current integration still consists of a synthetic staged-callback chain plus a direct canonical static-inference restart test; it does not traverse the real bounded preflight/materialization/TRAIN-EVAL/DEPLOY/PES/RELAX/DYN/selection-publication product path.

C8-A runtime-profile v6 invalidation is accepted as source-correct. C8-B single-owner cache-release direction is accepted except for slot-commit exception atomicity. C8-C production call-site wiring is accepted as source-correct. The remaining work is local correctness plus acceptance evidence.

Full RTX 3090 / data-heavy production qualification remains deferred to final release handoff.

## 2. Frozen accepted mechanisms

Implementation MUST preserve the following and MUST NOT redesign them merely to satisfy this closeout:

- `StaticInferenceRuntimeAuthority` as the sole `(batch_size, concurrent_model_jobs)` operating-point/resource/failure/profile authority;
- `StaticMaceInferenceExecutor` as the sole persistent provider/model-shell pool and execution owner;
- runtime-profile schema/evidence semantics v6;
- rejection of v1-v5 runtime profiles for current reusable evidence;
- `InferenceExecutionPlan` v3 and exact historical v1/v2 validation/migration;
- two-dimensional failure semantics:
  - J=1 execution OOM/backoff may tighten the single-provider/global batch ceiling;
  - J>1 execution OOM/backoff creates only the appropriate `(B,J)` boundary;
  - provider-pool OOM affects provider concurrency only;
  - live-resource rejection remains transient;
- genuine worker-private J-way inference and deterministic aggregation;
- conservative provider-residency requirements distinct from raw observed deltas;
- fail-closed fresh J>1 growth without complete provider-residency authority;
- normalized post-base incremental resource coordinates and live reclamping;
- pre-/post-growth admission;
- one outer staged-EVAL owner;
- persistent private-provider reuse;
- one executor-owned allocator-release transaction for normal pool shrink/provider-growth failure;
- complete-first-job one-slot calibration;
- graph/head/checkpoint/dtype/precision/cache/scientific identity semantics;
- current TRAIN/EVAL/DEPLOY/PES/RELAX/DYN/publication architecture;
- all unrelated PERF1 gates already closed by previous rounds.

Do NOT introduce a second scheduler, provider registry, resource authority, migration layer, compatibility cache, restart mechanism, or test-only campaign orchestrator.

## 3. Gate C9-A — make provider-slot growth commit exception-atomic

### 3.1 Root cause

Current `_ensure_provider_pool()` constructs a provider, computes its required/observed residency values, then mutates several independent collections:

```text
_provider_pool
_provider_pool_resident_ram_bytes
_provider_pool_resident_vram_bytes
_provider_pool_observed_ram_bytes
_provider_pool_observed_vram_bytes
```

The provider is appended before all bookkeeping appends complete and before `attempt_provider` is cleared. A `MemoryError`, `OSError(ENOMEM)`, or other exception during any later append/update can therefore leave:

- pool and bookkeeping lengths inconsistent;
- the same provider reachable from both `attempt_provider` and `_provider_pool`;
- double close during rollback;
- `_retire_private_providers()` popping from a bookkeeping list that never received the corresponding entry;
- `IndexError` or another cleanup exception masking the original causal exception;
- leaked provider ownership or stale residency accounting.

The accepted design requires each provider slot to become visible atomically as one ownership/bookkeeping unit.

### 3.2 Required invariant

For every provider-growth attempt, either:

```text
all slot state commits exactly once
```

or:

```text
no slot state remains committed
+ the provider closes exactly once
+ all pool/bookkeeping collections return to their pre-attempt lengths
+ one CUDA allocator release at most (zero on CPU)
+ the original causal exception is re-raised
```

The pre-existing accepted pool must remain untouched.

### 3.3 Required implementation strategy

Keep the existing pool architecture and parallel collections. Do not replace them with a new registry/dataclass subsystem during closeout.

Implement slot insertion as a local transaction:

1. before attempting a slot, capture the accepted lengths of all five collections;
2. construct the provider and compute all `growth_*` / `required_*` values into local variables before exposing the provider to pool ownership;
3. use one explicit ownership-transfer marker, e.g. `slot_committed = False` or equivalent;
4. commit the provider and all four metadata entries as one guarded block;
5. only after all five append operations succeed:
   - mark ownership transferred;
   - clear the attempt-local reference;
   - publish `observe_provider_residency(...)`;
6. if any exception occurs during the commit block:
   - truncate each collection independently back to its captured accepted length rather than assuming collection lengths are mutually consistent;
   - identify and close each provider added during the failed transaction exactly once;
   - if the attempt-local provider was never transferred, close it exactly once;
   - avoid calling `_retire_private_providers()` on internally inconsistent parallel-array state unless it has first been made consistent;
   - perform at most one executor-owned CUDA cache release after rollback; CPU remains zero;
   - re-raise the **original exception**, not a cleanup exception;
7. if `runtime_authority.observe_provider_residency(...)` itself can raise, define it as post-commit policy update and either:
   - include it inside the same slot transaction and roll the slot back on failure, or
   - prove it cannot materially raise for valid computed inputs. Prefer transactional rollback if this cannot be proven cheaply.

Cleanup must be best-effort without masking the causal exception. Any cleanup failure should not replace the original resource/programming exception.

### 3.4 Mandatory focused reproducers

Add failure-injection tests covering at minimum:

1. exception before provider creation returns: accepted pool unchanged, one release at most;
2. provider construction succeeds, then `_provider_pool.append` fails;
3. failure after provider append but before resident-RAM append;
4. failure after resident-RAM append but before resident-VRAM append;
5. failure after resident-VRAM append but before observed-RAM append;
6. failure after observed-RAM append but before observed-VRAM append;
7. failure during `observe_provider_residency(...)` if it is included in the transaction;
8. each failure restores all five collection lengths exactly to their pre-attempt values;
9. provider close count is exactly one for each failed/new provider and zero for pre-existing accepted providers;
10. original `MemoryError` / `OSError(ENOMEM)` / non-resource exception is preserved;
11. CUDA failed growth performs at most one allocator release;
12. CPU failed growth performs zero allocator releases;
13. a later-slot failure after one or more successful new slots restores the pool to the pre-call accepted size defined by `_ensure_provider_pool()`'s current contract;
14. successful multi-slot growth preserves current conservative residency observations and profile semantics.

### 3.5 C9-A stage-local regression

Before C9-B, run focused transactional tests plus affected regression for:

- static inference/provider pool;
- provider construction/close lifecycle;
- resource admission/reclamp;
- runtime profile v6 persistence/reuse;
- OOM/ENOMEM/non-resource recovery;
- staged EVAL and static consumers;
- DEPLOY/PES/LOCKED where they reuse the provider path;
- cancellation/error cleanup;
- numerical equivalence/deterministic ordering.

## 4. Gate C9-B — prove historical v2 through an actual production consumer

### 4.1 Objective

No source redesign is authorized. The current `_evaluation_inference_execution_plan(..., store, record_key)` wiring in EVAL/DEPLOY/PES is accepted as the intended production path.

The missing requirement is executable evidence that a real production consumer—not the resolver helper in isolation—encounters historical persisted v2 and continues correctly.

### 4.2 Required test shape

Use the smallest real consumer practical, preferably DEPLOY because its normal persistence key is already well-defined and it feeds canonical static inference.

The test must:

1. create a real temporary campaign state/store with the minimum production records/artifacts required to enter the chosen EVAL/DEPLOY/PES consumer;
2. seed an exact historical-v2 `InferenceExecutionPlan` under the **actual record key that consumer reads**;
3. invoke the production-facing consumer/command boundary that owns the plan lookup;
4. allow the consumer to call `_evaluation_inference_execution_plan(...)` naturally; do not call the resolver first in test code;
5. prove the loaded runtime plan is current v3;
6. prove provider-residency RAM/VRAM remains absent unless current resource planning independently derives a conservative requirement;
7. prove fresh J>1 remains fail-closed until such current authority exists;
8. prove canonical current planning can then enable J>1 when valid current residency evidence exists;
9. prove the normal persisted record is rewritten as current v3;
10. repeat with a corrupted historical-v2 digest and prove failure propagates through the same production consumer boundary;
11. preserve checkpoint/head/scientific/numerical identity.

Do not add a second parser or migration shim. The test must consume the existing v3 authority.

### 4.3 Preferred consolidation

If practical, implement this as part of the C9-C assembled fixture by seeding historical v2 before the first DEPLOY/EVAL transition. A separate lower-level direct-helper test may remain, but it is not acceptance evidence by itself.

### 4.4 C9-B stage-local regression

Run the focused real-consumer migration test plus affected campaign store/restart, EVAL/DEPLOY/PES/static inference, resource planning, serialization, publication/command-boundary, and numerical regression before C9-C.

## 5. Gate C9-C — complete the real bounded assembled production integration

### 5.1 Acceptance objective

This is the final functional acceptance blocker. The existing tests remain useful lower-level coverage but do not satisfy assembled-product acceptance:

- `_run_staged_evaluation_tasks()` with callbacks named after stages is scheduler integration only;
- direct `_predict_model_on_atoms()` plus campaign SQLite/profile persistence is static-profile/restart integration only.

C9-C must exercise the actual production orchestration/state-transition boundaries with bounded synthetic data and sub-interface stubs.

### 5.2 Required path

Use the highest practical real public/CLI campaign progression to traverse:

```text
init / durable campaign state
-> preflight
-> preparation / materialization
-> TRAIN / EVAL orchestration
-> DEPLOY
-> PES
-> RELAX
-> DYN
-> selection / publication
```

Cross the actual production-facing implementations/modules used by the campaign for those stages. Expensive numerical/training backends may be stubbed **below** these interfaces; the production orchestration/state/resource/persistence code itself must remain real.

Do not recreate the stage machine in the test.

### 5.3 Bounded fixture construction

The fixture must be CPU-runnable and self-contained:

- temporary campaign root and real `CampaignStore`;
- minimum valid config/manifests/ledgers;
- tiny ASE/reference/configuration data sufficient for real stage contracts;
- tiny fake model/checkpoint artifacts where production interfaces accept them;
- real preflight and materialization transitions;
- real TRAIN/EVAL orchestration with expensive MACE training/evaluation stubbed beneath the production boundary;
- real DEPLOY orchestration with model execution stubbed beneath provider/model boundaries;
- real PES orchestration with expensive numerical model calls stubbed beneath its production interface;
- real RELAX and DYN orchestration with LAMMPS/external trajectory work stubbed beneath their production interfaces;
- real final selection/publication state/artifact generation;
- no external LTA root, full MACE training, long trajectory, GPU requirement, or production-sized data.

Counters/fakes should live below expensive external interfaces and record invocation only; they must not decide stage order or mutate campaign stage state directly.

### 5.4 Seed compatibility/restart conditions into the assembled fixture

The assembled fixture must deliberately start with both:

1. a syntactically valid **stale v5 runtime profile** whose persisted global ceiling is contaminated/reduced; and
2. an exact **historical-v2 inference execution plan** under an actual production consumer key (preferably the DEPLOY or EVAL key used in the run).

This consolidates C8-A/C9-B acceptance into one real product path.

### 5.5 First invocation assertions

The first run must prove through durable production records/artifacts:

- preflight and materialization reach their real completed/eligible states;
- TRAIN/EVAL traverses its real production owner;
- stale v5 static runtime evidence is rejected and does not constrain the current authority;
- cold/current calibration occurs where required;
- current runtime evidence is written as **v6**;
- the historical-v2 execution plan is encountered by the real consumer, validated, migrated, and re-persisted as **v3**;
- no historical provider-residency evidence is fabricated;
- DEPLOY executes through its production boundary;
- PES executes through its production boundary;
- RELAX executes through its production boundary;
- DYN executes through its production boundary;
- final selection/publication is produced through production code;
- deterministic scientific output/identity remains consistent with bounded fixture expectations;
- at least one bounded failure/cancellation/cleanup edge is exercised where practical without duplicating the whole chain.

### 5.6 Second invocation / restart assertions

Run the same campaign root again through the real public restart path. Prove:

- completed stage/state records are recognized;
- completed expensive external work is not redundantly replayed except where production semantics intentionally require a check;
- the migrated v3 execution plan is consumed directly rather than historical v2 being reparsed again;
- stale v5 evidence remains ignored;
- the first-run v6 runtime profile is actually loaded and reused;
- the second run does not repeat cold calibration when compatibility/live admission permits reuse;
- live RAM/VRAM admission still reclamps before executing reusable operating points;
- terminal selection/publication remains deterministic and consistent;
- counters below expensive boundaries demonstrate genuine restart skips/reuse rather than a test-side shortcut.

Profile reuse must be asserted through production-observable evidence, e.g. compatible-profile loader/authority state or absence of calibration candidate waves—not output equality alone.

### 5.7 Acceptance evidence must be separate

Report separately:

1. first-run bounded assembled production integration;
2. second-run persisted restart/v6 reuse integration;
3. bounded assembled failure/cancellation/cleanup check if implemented separately.

Do not count scheduler-only callback tests or direct helper tests as this gate.

## 6. Final affected-surface re-derivation

After the last executable edit, independently re-derive the affected surface and search specifically for:

- provider-pool and bookkeeping-list mutations that are not transactionally reconciled;
- cleanup code that assumes parallel collection lengths are consistent after an arbitrary exception;
- double-close of an attempt-local provider also appended to the pool;
- cleanup exceptions masking original provider-construction/commit failures;
- provider-growth failure paths with more than one allocator release;
- CPU paths reaching CUDA cache release;
- v1-v5 runtime profiles accepted or migrated into reusable v6 evidence;
- stale v5 compatibility semantics/path aliases;
- direct J>1 writes to the global/J=1 safe batch ceiling;
- historical-v2 migration tests that invoke only `_evaluation_inference_execution_plan()` instead of a real consumer;
- production EVAL/DEPLOY/PES call sites that bypass persisted execution-plan lookup;
- tests that seed plans under arbitrary keys rather than actual production keys;
- assembled tests that replace DEPLOY/PES/RELAX/DYN/publication with callback labels;
- direct `_predict_model_on_atoms()` calls being counted as campaign traversal;
- second-run tests that prove only output equality rather than persisted restart/profile reuse;
- duplicate schedulers/resource authorities/provider registries introduced by the repair;
- any scientific/policy/identity drift outside the authorized closeout.

## 7. Mandatory final validation

On the same final commit:

### 7.1 Focused tests

Run all C9-A transactional failure-injection tests plus still-valid C8-A/B/C and REOPEN7 focused reproducers.

### 7.2 Fresh final affected regression

Run the complete affected surface including:

- static MACE inference/batching;
- provider pool/growth/shrink/cleanup;
- runtime-profile v6 persistence/reuse/restart;
- 2-D failure learning and one-slot calibration;
- resource planning/live telemetry/admission;
- `InferenceExecutionPlan` v1/v2/v3 serialization/migration;
- campaign store/state/manifest/restart;
- staged EVAL/campaign execution;
- DEPLOY/PES/LOCKED/replay/static consumers;
- RELAX/DYN/shared-resource/failure cleanup;
- selection/publication/command boundaries;
- cache/head/checkpoint/dtype/precision/scientific identity;
- numerical equivalence/determinism.

Run the broader/full available repository regression if final impact cannot be confidently bounded. A required test that does not execute is not a pass. Pre-existing unrelated unavailable checks may be attributed but never counted as passed.

### 7.3 Assembled integration

Run C9-C separately from the regression aggregate and report first run and restart run separately.

## 8. Implementation sequence

```text
C9-A
provider-slot transactional commit/rollback
    -> failure-injection focused tests
    -> affected provider/static/profile/resource regression

C9-B
historical v2 through actual EVAL/DEPLOY/PES consumer
    -> focused production-consumer migration test
    -> affected campaign/restart/serialization/static-consumer regression

C9-C
real bounded assembled campaign path
+ stale v5 rejection -> v6 write/reuse
+ historical v2 -> v3 through real consumer
+ real DEPLOY/PES/RELAX/DYN/publication boundaries
    -> fresh impact re-derivation
    -> all focused reproducers
    -> complete fresh affected regression
    -> first-run assembled integration
    -> second-run restart/v6-reuse integration
```

Do not defer C9-A or C9-B stage-local regression to the final gate.

## 9. Gate disposition entering REOPEN9

- original PERF1 architecture: **CLOSED / PRESERVE**
- runtime profile v6 source implementation: **CLOSED subject final regression**
- stale v1-v5 profile invalidation: **CLOSED subject assembled proof**
- 2-D J=1/J>1 execution failure semantics: **CLOSED subject final regression**
- conservative provider residency/fail-closed J>1 growth: **CLOSED**
- normal pool shrink / single cache-release ownership: **CLOSED**
- C9-A slot-commit exception atomicity: **OPEN narrowly**
- `InferenceExecutionPlan` v3 parser and historical v1/v2 migration: **CLOSED**
- production EVAL/DEPLOY/PES persisted-plan source wiring: **CLOSED subject final regression**
- C9-B historical-v2 actual-consumer executable evidence: **OPEN narrowly**
- C9-C real assembled production integration: **OPEN / final acceptance blocker**
- scientific identity/numerics/training policy/DYN/RELAX architecture: **CLOSED / PRESERVE**
- RTX 3090/data-heavy production qualification: **DEFERRED**

## 10. Genuine redesign triggers

Do not reopen broader design for ordinary implementation/test issues. Reopen only the implicated surface if concrete evidence demonstrates that:

- provider-slot state cannot be made exception-atomic without replacing the current pool representation;
- the existing v3 migration authority cannot be reached through real persisted consumers without changing public restart contracts;
- the actual production DEPLOY/PES/RELAX/DYN/selection chain cannot be exercised with bounded sub-interface stubs without altering production architecture;
- scientific/numerical outputs change outside frozen tolerances because of these fixes.

A local transaction helper/marker, rollback utility, failure-injection hook/test double, test fixture, production-boundary stub, or compatibility fixture is **not** a redesign trigger.

## 11. Final completion condition

MLFF-END-TO-END-PERF1 may be marked:

**FUNCTIONAL IMPLEMENTATION ACCEPTED — TARGET-WORKSTATION GPU QUALIFICATION DEFERRED**

only when, on one final commit:

- every provider-slot growth attempt is exception-atomic;
- all pool/bookkeeping collections remain length-consistent after any injected commit failure;
- failed/new providers are closed exactly once and accepted providers remain owned;
- cleanup never masks the original causal exception;
- failed CUDA growth performs at most one executor-owned allocator release; CPU performs zero;
- runtime profile v6 remains the sole current reusable evidence format;
- stale v1-v5 evidence cannot influence current selection/admission/global ceiling;
- historical v2 is encountered by a real production consumer and re-persisted as v3 without fabricated residency evidence;
- real bounded orchestration crosses preflight/materialization/TRAIN-EVAL/DEPLOY/PES/RELAX/DYN/selection-publication boundaries;
- first assembled run rejects stale v5, writes v6, migrates v2 -> v3, and reaches terminal publication;
- second assembled run proves actual persisted restart and v6 profile reuse with current live admission;
- all focused tests execute successfully;
- fresh complete affected-surface regression executes successfully;
- assembled first-run and restart integration execute successfully and are reported separately;
- no unrelated PERF1 architecture/scientific behavior changes;
- unavailable unrelated checks, if any, are explicitly attributed rather than counted as passes;
- target RTX 3090/data-heavy production qualification remains deferred to final release handoff.
