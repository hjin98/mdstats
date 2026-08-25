# MLFF-END-TO-END-PERF1 Sixth-Reopen Final-Closeout Implementation Workplan

Status: **ACTIVE — FINAL CLOSEOUT CORRECTIONS REQUIRED**  
Branch: `feat/mlff-end-to-end-performance-v1`  
Reviewed implementation tip: `73073530b48c580b40a2d1555785e625f12901a6`  
Parent archived plan: `workplans/archive/MLFF_END_TO_END_PERF1_REOPEN5_IMPLEMENTATION_WORKPLAN.md`  
Date reopened: 2026-08-24

## 1. Authority and scope

This file is the single authoritative active delta-workplan for the final functional closeout of MLFF-END-TO-END-PERF1. The original PERF1 plan and reopen rounds 2-5 remain historical/parent authority for decisions not explicitly changed here. The fifth plan is archived verbatim; its implementation record is historical evidence only and does not establish current acceptance.

This is a **narrow correction round**, not another architecture redesign. Preserve without replacement:

- `StaticInferenceRuntimeAuthority` as the sole `(batch_size, concurrent_model_jobs)` policy/resource authority;
- `StaticMaceInferenceExecutor` as the sole persistent provider/model-shell pool and execution owner;
- real worker-private J-way execution and observed-concurrency evidence;
- deterministic aggregation/order;
- one outer staged-EVAL inference owner, with no outer x inner concurrency multiplication;
- the persistent lazily grown private-provider pool;
- complete-first-job one-slot CUDA calibration;
- pre-base-model admission for DEPLOY/PES/LOCKED and equivalent command paths;
- normalized post-base incremental RAM/VRAM coordinates and live policy-fraction re-clamping;
- mandatory post-pool-growth admission before wave launch;
- explicit executor-owned CUDA synchronization inside steady-state timing;
- graph-cache/head/checkpoint/dtype/precision/scientific identity and restart semantics;
- DYN/RELAX architecture and all unrelated accepted PERF1 gates.

Do not introduce a second resource scheduler, retry manager, provider registry, profile authority, or consumer-specific static inference path.

## 2. Final-closeout diagnosis

The reviewed fifth implementation is directionally correct but not yet functionally acceptable for five reasons:

1. **Provider residency is not reproducible from persisted evidence.** The authority keeps a conservative provider estimate, but the executor persists raw observed construction deltas. A warmed allocator can reuse cached RAM/VRAM, making the raw delta smaller than the capacity required to reproduce the provider from the canonical one-provider baseline, including zero.
2. **Execution-OOM learning is still partly one-dimensional.** A J>1 execution OOM lowers one global batch ceiling, which can invalidate safe larger-B evidence at lower J even when the failure was caused by aggregate concurrent transient pressure.
3. **Normal pool shrink can leave allocator cache resident.** Retired provider tensors may be freed logically while CUDA cached blocks remain reserved, so the immediate lower-J live re-clamp can see falsely reduced free VRAM.
4. **Host-memory exhaustion classification is incomplete.** Bare `MemoryError` and `OSError(errno.ENOMEM)` may bypass adaptive provider-pool fallback because message matching alone is insufficient.
5. **Staged EVAL still lacks a demonstrably conservative provider-residency source and terminal assembled integration evidence.** `budget / requested_jobs` is not a provider-size estimate, and the previous plan allowed the required assembled integration to remain unavailable.

These are local defects inside the accepted authority/executor/resource-ledger design. They do not justify replacing the persistent-pool architecture.

## 3. Frozen final resource model

### 3.1 Post-base incremental coordinate remains authoritative

After the canonical base provider is resident, all static inference admission remains expressed as marginal bytes from the executor's current owned state:

```text
live_incremental_budget = min(initial_incremental_cap,
                              floor(current_live_available * policy_fraction))
```

This applies independently to host RAM and VRAM. Existing pre-base-model outer admission remains separate and must not be conflated with the post-base coordinate.

### 3.2 Observation and admission requirement are different quantities

For each private provider slot, distinguish:

```text
observed_slot_growth
    = diagnostic memory increase observed during construction

slot_required_residency
    = conservative incremental capacity required to reproduce the slot
      from the canonical one-provider baseline
```

The admission requirement is frozen as:

```text
slot_required_residency = max(preconstruction_provider_estimate,
                              conservative_observed_retained_growth)
```

For a J-provider pool:

```text
pool_required_residency(J)
    = sum(slot_required_residency for private slots 1 .. J-1)
```

A raw allocator/RSS construction delta must **never** replace the conservative pre-admission estimate when the raw observation is smaller. Allocator reuse is not proof that a fresh compatible process can reproduce the provider with that smaller capacity.

The next-slot estimate must remain monotone-conservative:

```text
next_slot_estimate = max(configured_provider_floor,
                         all retained measured/admitted slot requirements)
```

It may increase from evidence; it must not collapse because observed growth is zero or small.

### 3.3 Marginal admission remains current-state based

For a target known point `(B,J)`:

```text
remaining_pool_growth = max(0,
    target_pool_required_residency - current_pool_required_residency)

marginal_requirement = remaining_pool_growth + target_execution_peak
```

If the required J pool is already resident, admit only the execution transient. Never double-charge resident providers.

## 4. Gate FINAL-A — reproducible provider residency and runtime profile v5

### 4.1 Provider construction measurement

Reuse the existing resource monitor; do not create a second estimator subsystem. During private-provider construction, collect the strongest available conservative observations from existing runtime mechanisms, including as applicable:

- host RSS retained/peak growth;
- PyTorch allocated-memory growth;
- PyTorch reserved-memory growth;
- device/driver used-memory growth.

The persisted/admission requirement must be bounded below by the configured/provider-floor estimate even when allocator reuse makes all observed deltas smaller.

Exact diagnostic field mechanics are delegated to implementation, but the authority must be able to distinguish raw observation from the conservative requirement used for future admission.

### 4.2 Runtime profile v5

Bump runtime-only profile/evidence semantics to:

```text
mdstats.static-inference-runtime-profile.v5
```

Reject/rebuild v1-v4 deterministically. Do not reinterpret v4 bytes as v5.

Use unambiguous persistent semantics equivalent to:

```text
provider_pool_required_ram_bytes
provider_pool_required_vram_bytes
execution_peak_ram_bytes
execution_peak_vram_bytes
aggregate_required_ram_bytes
aggregate_required_vram_bytes
```

For every feasible point:

```text
aggregate_required_ram = provider_pool_required_ram + execution_peak_ram
```

and, when CUDA components are required/known:

```text
aggregate_required_vram = provider_pool_required_vram + execution_peak_vram
```

For J=1, private-pool requirement is exactly zero because the canonical base provider is the profile baseline.

CUDA J>1 evidence with unknown required provider VRAM or unknown execution VRAM is not reusable as an automatic safe profile point.

Raw construction observations may be retained as diagnostics but are not the reusable admission authority.

### 4.3 FINAL-A focused regression

Mandatory focused reproducers:

1. configured provider floor 5, raw construction delta 0 -> persisted provider requirement remains >=5;
2. configured floor 5, observed retained growth 7 -> future admission/profile uses >=7;
3. fresh J=2 requires provider 5 + transient 2, live budget 6 -> factory is never entered;
4. warm resident J=2 requires transient 2, live budget 2 -> wave is admitted without recharging pool residency;
5. v1-v4 profiles are rejected;
6. malformed v5 aggregate/component mismatch is rejected;
7. J=1 v5 records zero private-pool requirement plus actual execution peak;
8. unknown required CUDA provider/execution component cannot become reusable J>1 evidence;
9. profile round-trip preserves required-residency and execution components exactly;
10. scientific/result/configuration identity remains unchanged by v5 runtime evidence.

### 4.4 FINAL-A gate acceptance

Run the focused tests plus complete affected static-inference, profile serialization/reuse, restart, numerical-equivalence, command-consumer, and staged-EVAL regression before FINAL-B.

---

## 5. Gate FINAL-B — genuinely two-dimensional failure learning and type-aware recovery

### 5.1 Separate single-provider batch limit from J-dependent execution limits

Replace ambiguous global batch learning with two semantic layers inside the existing authority.

**Single-provider batch ceiling**:

- only an execution OOM established at `J=1` may lower the global per-provider batch ceiling;
- that ceiling applies to all J because each worker must execute one provider batch.

**J-dependent execution boundary**:

- an execution OOM at `(B_fail, J_fail > 1)` must not invalidate safe larger-B evidence at smaller J;
- it may conservatively make points with `J >= J_fail` and `B >= B_fail` ineligible for the compatible runtime state;
- smaller B at the same J remains eligible;
- lower J at the same B remains eligible unless independently disproven.

Candidate eligibility must therefore behave equivalently to:

```text
B <= single_provider_batch_ceiling
AND no provider-pool failure boundary with J_fail <= J
AND no J-dependent execution boundary with J_fail <= J and B_fail <= B
```

Do not create another optimizer. Represent/reconstruct these boundaries in `StaticInferenceRuntimeAuthority` from its existing evidence.

### 5.2 Live-resource rejection is transient, not capability evidence

`live-resource` means the current live snapshot does not admit a transition. It is not a stable hardware capability boundary.

- do not use it to permanently prune a compatible profile across later invocations;
- do not lower batch or concurrency capability solely from a transient live-resource rejection;
- it may exclude the current attempted state within one bounded execution attempt to prevent an immediate retry loop.

If persisted at all for diagnostics, it must be explicitly non-reusable for capability reconstruction.

### 5.3 Type-aware resource exception classification

Use one canonical classifier for recognized resource exhaustion. It must identify at least:

- Python `MemoryError`;
- `OSError` with `errno.ENOMEM`;
- PyTorch CUDA OOM exception types when available;
- known CUDA/PyTorch allocation failure messages as fallback.

Classify by lifecycle boundary:

```text
resource failure during provider construction -> provider-pool-oom
resource failure during prediction wave       -> execution-oom
pre-launch admission failure                   -> live-resource
```

Non-resource/model/scientific/programmer exceptions remain hard failures and propagate immediately.

### 5.4 Shared recovery remains mandatory

Cold calibration and compatible-profile execution continue to use one bounded recovery path:

1. preserve valid lower-J evidence and the last accepted pool;
2. record only the causal failure dimension;
3. re-clamp/reselect the best remaining measured safe point;
4. retire/grow the pool to that point;
5. continue if a safe point remains;
6. terminate cleanly if none remains;
7. never retry the same failed state indefinitely.

### 5.5 FINAL-B focused regression

Mandatory reproducers:

1. `(B=16,J=4)` execution OOM does not invalidate safe `(16,1)` or `(16,2)` evidence;
2. J=1 execution OOM lowers the single-provider batch ceiling for all J;
3. provider-pool OOM at J=4 changes the concurrency boundary only and leaves batch ceilings unchanged;
4. smaller B at the failed J remains searchable after J-dependent execution failure;
5. lower J at the same B remains searchable after J>1 execution failure;
6. transient `live-resource` rejection does not become a reusable permanent profile boundary;
7. bare `MemoryError()` during provider creation falls back to lower safe J;
8. `OSError(errno.ENOMEM)` during provider creation does the same;
9. recognized CUDA allocator OOM during provider construction is provider-pool-oom;
10. non-resource provider construction error propagates;
11. profile-selected J=2 provider resource failure falls back to measured J=1;
12. zero admissible points terminates cleanly without deadlock or forced prediction;
13. cleanup remains exact on every fallback/error path.

### 5.6 FINAL-B gate acceptance

Run focused failure/pruning/recovery tests plus affected scheduler, runtime-profile, restart/reuse, static consumer, staged-EVAL, DEPLOY/PES/LOCKED, and resource-ledger regression before FINAL-C.

---

## 6. Gate FINAL-C — pool-shrink reclamation and staged-EVAL reconciliation

### 6.1 Normal pool shrink is a physical resource transition

When reducing `J_high -> J_low`:

1. stop using surplus providers;
2. close surplus providers exactly once;
3. remove executor references to them;
4. ensure their model/calculator/device tensors are no longer retained by provider ownership;
5. on CUDA, release unused allocator cache **once after an actual shrink**;
6. take a fresh live RAM/VRAM snapshot;
7. only then admit the lower-J wave.

Do not call allocator-cache release:

- between steady-state waves;
- when J did not shrink;
- as a general hot-path operation.

If needed, make the canonical MACE provider's `close()` idempotently release calculator/model references. Do not add a second provider lifecycle owner.

### 6.2 Staged-EVAL provider estimate

`available_budget / requested_jobs` is explicitly prohibited as a provider-residency estimate. It is an allocation partition, not evidence of model residency.

Staged EVAL must pass the existing outer planner's explicit per-model/per-job RAM/VRAM estimate into the inner static authority when semantically compatible. DEPLOY and EVAL should therefore use the same class of provider-residency input.

If a static consumer has no valid outer provider estimate:

1. use a conservative explicitly measured base-provider residency if available;
2. otherwise automatic J>1 must fail closed;
3. never invent provider residency from `budget / J` or J=1 execution transient.

### 6.3 Outer staged-EVAL reservation must dominate permitted inner work

Freeze the enclosing ownership invariant:

```text
outer_eval_reserved_RAM
    >= canonical_base_provider_requirement
       + maximum permitted private_pool_required_RAM
       + maximum permitted execution_peak_RAM
```

Apply equivalent VRAM ownership where the outer plan owns device admission. Normalize shared components once; do not double-count a component already represented in the outer per-job estimate.

The inner authority must never select an operating point whose complete owned resource envelope exceeds the reservation held by the outer staged-EVAL inference owner.

One outer EVAL inference owner remains. No outer x inner concurrency multiplication.

### 6.4 FINAL-C focused regression

Mandatory reproducers:

1. J=4 -> J=2 shrink closes only surplus providers, releases CUDA cache once, re-clamps, and admits J=2 when sufficient headroom exists;
2. repeated J=2 production waves neither recreate providers nor release allocator cache;
3. failure cleanup and final executor close remain idempotent/exact;
4. post-growth resource shrink still blocks before any provider prediction enters the wave;
5. EVAL uses the canonical per-job provider estimate and contains no `budget / J` fallback;
6. equivalent EVAL and DEPLOY post-base states produce equivalent inner authority semantics;
7. outer staged-EVAL reservation is never below the maximum inner provider-pool + transient envelope it permits;
8. profile reuse cannot bypass outer staged/global admission;
9. J=1 paths remain simple and create no unnecessary private providers;
10. real J-way private state, deterministic result order, and numerical/reference parity remain unchanged.

### 6.5 FINAL-C gate acceptance

Run focused lifecycle/EVAL tests plus complete affected staged-EVAL, campaign execution, DEPLOY/PES/LOCKED, replay/static consumers, resource-planner, command-boundary, restart, DYN/RELAX-shared-resource, and numerical-equivalence regression.

---

## 7. Gate FINAL-D — final affected-surface acceptance and mandatory assembled integration

FINAL-D begins only after the final executable edit from FINAL-A/B/C.

### 7.1 Fresh affected-surface re-derivation

Independently re-derive the complete final affected behavioral surface. Search specifically for:

- raw observed provider growth used directly as reusable required residency;
- stale v1-v4 profile acceptance or compatibility translation;
- `budget / J` or J=1 transient used as provider-residency authority;
- global batch ceilings changed by J>1 execution OOM;
- live-resource evidence used as permanent capability pruning;
- message-only OOM classifiers that miss `MemoryError`/`ENOMEM`;
- pool shrink without physical provider release/cache reclamation before re-admission;
- direct static-prediction consumer bypasses;
- duplicate authority/provider-pool state;
- provider sharing across concurrent workers;
- provider leaks/double-close;
- candidate or worker-wave launch without immediate live admission;
- profile reuse bypassing outer resource ownership;
- nested outer x inner EVAL concurrency;
- scientific identity/configuration changes caused by runtime evidence.

### 7.2 Mandatory focused suite

Every focused reproducer enumerated in FINAL-A, FINAL-B, and FINAL-C must execute on the final candidate. A required focused test that does not run is not a pass.

### 7.3 Fresh final affected regression

After all executable changes, rerun the complete affected regression covering at minimum:

- static MACE inference and batching;
- runtime profile persistence/reuse/restart;
- resource planning and live telemetry;
- adaptive CUDA scheduler and one-slot completion calibration;
- staged EVAL and campaign execution;
- DEPLOY/PES/LOCKED command paths;
- replay/static consumers;
- graph cache/head/checkpoint/dtype/precision semantics;
- numerical/reference equivalence;
- DYN/RELAX/shared resource code where plausibly affected;
- failure/cancellation/cleanup paths;
- command/publication/restart boundaries.

Run repository-required checks and broader/full available regression if the final affected surface cannot be bounded confidently. Pre-existing unrelated unavailable/failing checks may be attributed explicitly but are never counted as passes.

### 7.4 Mandatory bounded assembled production-interface integration

"No assembled campaign is presently configured" is **not an acceptable terminal outcome** for this closeout.

If no suitable existing integration fixture exists, implementation must create one bounded self-contained production-interface integration fixture that enters through real production orchestration and executes the available chain:

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

The integration fixture must:

- use a temporary/self-contained campaign root;
- use tiny synthetic atomic/configuration data sufficient to exercise orchestration contracts;
- call real public/production orchestration and state-transition/resource-authority boundaries;
- exercise real manifests, restart/profile-reuse/publication wiring where applicable;
- permit expensive external numerical/training dependencies to be stubbed **below** the production interface only;
- avoid dependency on an externally supplied LTA training root;
- avoid full MACE training or long production data;
- be runnable on CPU when GPU is unavailable;
- include a second bounded invocation that exercises restart/profile reuse;
- exercise at least one assembled failure/cancellation/cleanup boundary when practical without duplicating the entire chain.

This is functional integration, not target-hardware production qualification.

### 7.5 FINAL-D acceptance evidence

Record separately:

1. focused suite result;
2. fresh final affected-surface regression result;
3. bounded assembled production-interface integration result;
4. repository-required/broader checks and any demonstrably unrelated unavailable items.

Do not collapse these into one aggregate pytest count that obscures whether the assembled integration actually ran.

---

## 8. Implementation sequence and stage-local gates

Implementation must proceed in this order:

```text
FINAL-A
v5 reproducible provider-residency semantics
+ conservative construction requirement
    -> focused v5/residency tests
    -> affected static/profile regression

FINAL-B
2-D execution-OOM boundaries
+ transient live-resource semantics
+ type-aware resource classification/recovery
    -> focused failure/pruning tests
    -> affected scheduler/profile/restart/consumer regression

FINAL-C
pool-shrink reclamation
+ staged-EVAL provider estimate normalization
+ outer reservation reconciliation
    -> focused lifecycle/EVAL tests
    -> affected EVAL/DEPLOY/resource regression

FINAL-D
final impact re-derivation
    -> all mandatory focused reproducers
    -> fresh complete affected-surface regression
    -> separate bounded assembled production-interface integration
    -> repository-required/broader available checks
```

Do not defer all testing to FINAL-D. Stage-local affected regression remains mandatory after each material behavior-changing gate before dependent implementation proceeds.

## 9. Expected affected files

At minimum inspect and modify as required:

- `mdstats/training_data/model_features.py`;
- `mdstats/training_data/campaign_execution.py`;
- `mdstats/training_data/deploy_verify.py`;
- resource/admission helpers used by staged EVAL and command paths;
- runtime profile persistence/compatibility helpers and exports;
- `tests/test_mlff_static_mace_inference.py`;
- staged-EVAL/resource/campaign/DEPLOY/PES/LOCKED/restart tests;
- bounded production-interface integration test/fixtures;
- any transitive consumer found by FINAL-D impact analysis.

Do not edit scientific schemas or unrelated architecture merely to satisfy this closeout.

## 10. Preserved gate disposition

- R0: **CLOSED**
- R1: **CLOSED**
- F-R2A complete-first-job one-slot calibration: **CLOSED subject to final regression**
- P5-R2B1 normalized resource-coordinate model: **CLOSED subject to final regression**
- FINAL-A / former P5-R2B2 + P5-R2C provider evidence: **OPEN**
- FINAL-B / former P5-R2B3 failure/pruning/recovery: **OPEN**
- FINAL-C / former P5-R5 staged/resource reconciliation: **OPEN**
- R3B: **CLOSED subject to final regression**
- R4: **CLOSED**
- R6B: **CLOSED subject to final regression**
- R7: **CLOSED subject to final regression**
- FINAL-D / former P5-R8: **OPEN**
- genuine J-way concurrency: **PRESERVE**
- persistent provider pool: **PRESERVE**
- complete-first-job calibration: **PRESERVE**
- normalized post-base live resource coordinate: **PRESERVE**

## 11. Product-complexity rules

Prefer correction of the accepted ownership model over new machinery:

```text
reuse -> consolidate -> refactor -> delete
```

- keep one operating-point/resource authority;
- keep one provider-pool/execution owner;
- reuse current resource telemetry and outer resource estimates;
- reconstruct J/B failure boundaries from existing authority evidence rather than add a separate optimization subsystem;
- keep raw construction observations diagnostic and conservative required-residency state authoritative;
- retire obsolete v4-specific compatibility code after v5 migration;
- do not add consumer-specific fallback schedulers;
- do not add production-scale qualification machinery to satisfy functional integration.

## 12. Genuine redesign triggers

Stop dependent implementation and reopen only the affected design surface if evidence demonstrates that:

- a conservative provider requirement cannot be derived from existing configured estimates plus retained runtime observations without making useful J>1 operation impossible;
- provider memory cannot be released sufficiently on pool shrink for lower-J reuse, making persistent high-water pool ownership globally inferior;
- the existing authority cannot represent the necessary 2-D failure boundaries without becoming less correct or materially more complex than a replacement policy;
- staged EVAL cannot expose a valid per-model resource estimate without replacing the broader campaign resource model;
- persistent private providers cannot coexist safely/usefully on intended hardware;
- scientific/numerical outputs change outside frozen tolerances;
- a bounded assembled integration cannot exercise the production boundaries without changing public production architecture.

Ordinary implementation bugs, profile version bump, additional test fixtures, type-aware OOM classification, cache release at pool shrink, per-J failure bookkeeping, resource-estimate plumbing, or test-harness construction are **not** redesign triggers.

## 13. Final completion condition

MLFF-END-TO-END-PERF1 may return to:

**FUNCTIONAL IMPLEMENTATION ACCEPTED — TARGET-WORKSTATION GPU QUALIFICATION DEFERRED**

only when all of the following are true on the same final candidate:

- FINAL-A, FINAL-B, FINAL-C, and FINAL-D are accepted;
- v5 is the only accepted current static runtime-profile schema and v1-v4 rebuild instead of reinterpret;
- persisted private-provider requirement can never fall below the conservative provider floor because of allocator reuse;
- raw construction observation and admission requirement are not conflated;
- first and subsequent provider growth remain pre-admitted and post-growth rechecked;
- resident providers are never double-counted against current free memory;
- pool shrink closes/releases surplus provider state and performs one lifecycle cache release before lower-J re-admission;
- J>1 execution OOM cannot invalidate safe larger-B lower-J evidence;
- J=1 execution OOM still establishes the global single-provider batch constraint;
- provider-pool OOM affects concurrency only;
- transient live-resource rejection is not persisted as a permanent capability boundary;
- `MemoryError`, `ENOMEM`, and recognized CUDA OOMs use bounded adaptive recovery at the correct lifecycle boundary;
- staged EVAL uses a real per-model/per-job provider estimate, never `budget / J` or J=1 transient;
- the outer EVAL reservation dominates every inner operating point it permits;
- profile reuse and cold calibration share identical bounded recovery semantics;
- real worker-private J concurrency, persistent provider reuse, deterministic ordering, exact cleanup, numerical equivalence, and scientific identity remain regression-clean;
- every mandatory focused reproducer executes successfully;
- fresh final affected-surface regression executes successfully;
- a **separate bounded assembled production-interface integration executes successfully** on the same final candidate;
- broader unavailable repository checks are demonstrably pre-existing/unrelated and explicitly recorded, never counted as passes;
- full target-workstation RTX 3090/data-heavy qualification remains deferred to the final release handoff.

No unavailable functional integration requirement may be converted into acceptance by documentation alone.
