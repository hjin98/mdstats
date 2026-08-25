# MLFF-END-TO-END-PERF1 Fifth-Reopen Implementation Workplan

Status: **ACTIVE — FUNCTIONAL ACCEPTANCE REOPENED**  
Branch: `feat/mlff-end-to-end-performance-v1`  
Reviewed implementation tip: `b477fd923345a7bc90b4fc1e759d93c8182c1e69`  
Parent active plan: `MLFF_END_TO_END_PERF1_REOPEN4_IMPLEMENTATION_WORKPLAN.md`  
Date reopened: 2026-08-24

## 1. Authority and scope

This file is the authoritative fifth-closeout delta for MLFF-END-TO-END-PERF1. The original PERF1 plan and reopen rounds 2-4 remain authoritative for every decision not explicitly changed here.

The fourth implementation is directionally correct and must not be discarded. Preserve:

- the canonical `StaticInferenceRuntimeAuthority` as the sole `(batch_size, concurrent_model_jobs)` policy owner;
- the canonical `StaticMaceInferenceExecutor` as the sole provider/model-shell execution and pool owner;
- real worker-private J-way concurrency and observed-concurrency evidence;
- deterministic aggregation/order;
- one outer staged-EVAL inference owner;
- the persistent lazily grown private-provider pool;
- complete-first-job one-slot CUDA calibration;
- pre-base-model command admission in DEPLOY/PES/LOCKED paths;
- scientific identity, numerical policy, checkpoint/head/graph-cache semantics, restart semantics, DYN/RELAX architecture, and all unrelated accepted PERF1 gates.

The fourth implementation is nevertheless not functionally accepted because resource quantities are expressed in incompatible coordinate systems and the persistent-pool lifecycle does not yet use a correct marginal admission model. This delta reopens only F-R2B, F-R2C, F-R5 transitively, and F-R8. F-R2A remains locally accepted subject to final regression.

Do not introduce a second resource scheduler, provider registry, profile authority, or consumer-specific static-inference implementation.

## 2. Fifth-closeout diagnosis

The reviewed tip has seven material defects.

1. `live_vram_budget_bytes` has inconsistent semantics across consumers: some callers provide a fraction of currently free VRAM while others provide an absolute used-memory ceiling derived from total VRAM.
2. Once a private pool is resident, admission still compares the profile's fresh-baseline aggregate requirement (`pool residency + execution peak`) against current free memory, double-counting provider residency already reflected in current free RAM/VRAM.
3. Before the first private clone exists, J=1 execution transient memory is used as a bootstrap estimate for the memory required to materialize another complete MACE provider. These are not equivalent quantities.
4. The code admits before `_run_joint_wave()`, then may grow the provider pool and immediately launch the wave without a fresh live re-clamp after actual materialization.
5. Compatible-profile execution does not share the cold-search resource-failure degradation path; provider-pool OOM during profile reuse can abort despite retained lower-J safe evidence.
6. Provider materialization OOM is recorded as generic `oom`, which incorrectly lowers the learned batch-size ceiling even when batch size was not causal. `failed_concurrency` can likewise over-prune smaller-batch points at the same J.
7. v3 evidence does not enforce its own aggregate/component invariants, and J=1 evidence can be persisted with nonzero aggregate peaks but zero component fields. Current v3 bytes therefore cannot be trusted as strict persistent-pool evidence.

A smaller timing robustness gap also remains: steady-state elapsed time should end after an explicit executor-owned device synchronization rather than depending on provider internals to have synchronized before returning.

## 3. Frozen resource-coordinate model

### 3.1 One coordinate system inside the static authority

After the canonical base provider exists, the static authority must reason only in **incremental/marginal bytes from the executor's current owned state**.

For both RAM and VRAM define:

- `initial_incremental_cap`: the configured safe incremental envelope at authority creation;
- `live_available`: current host available RAM or current device free VRAM;
- `policy_fraction`: the configured RAM/VRAM safety fraction;
- `live_incremental_budget = min(initial_incremental_cap, floor(live_available * policy_fraction))`.

Do not compare an absolute used-memory ceiling directly with an incremental requirement. If an outer command path uses an absolute ceiling for pre-base-model admission, convert/re-resolve to the incremental coordinate after the base provider has been constructed before creating/using the static runtime authority.

This preserves the configured 20% host-RAM and 10% VRAM headroom when live availability shrinks; do not replace `fraction * live_available` with raw `live_available`.

### 3.2 Outer admission versus inner authority

Two different lifecycle boundaries are valid and must remain explicit:

1. **pre-base-model outer admission**: DEPLOY/PES/LOCKED and other command paths may use configured per-job estimates and absolute/aggregate device ceilings to decide whether the base model can be constructed at all;
2. **post-base-model static authority**: once the canonical base provider is resident, all batch/concurrency/pool decisions use the incremental coordinate defined above.

The inner authority must not silently inherit the outer plan's absolute ceiling semantics.

### 3.3 Fresh-profile requirement versus marginal current-state requirement

Persisted profile evidence remains relative to the canonical one-provider baseline:

- `provider_pool_resident_*`: cumulative incremental residency for private slots `1..J-1`;
- `execution_peak_*`: incremental transient demand above the fully resident J-provider pool;
- `aggregate_requirement_* = provider_pool_resident_* + execution_peak_*`.

At admission time, however, compare against current live headroom using only the **remaining marginal requirement**:

```text
remaining_pool_growth = max(0, target_provider_residency - current_provider_residency)
marginal_requirement = remaining_pool_growth + target_execution_peak
```

If the required target pool is already resident, the next steady-state wave is admitted against `execution_peak_*` only. Never charge already-resident private providers twice.

For an entirely fresh one-provider baseline, `current_provider_residency == 0`, so the same formula naturally reduces to the full aggregate profile requirement.

## 4. Gate P5-R2B1 — normalize live resource budgets

### Required implementation

1. Give `StaticInferenceRuntimeAuthority` enough execution-only configuration to recompute safe live incremental budgets under the configured RAM and VRAM fractions. Exact helper/dataclass mechanics are delegated to implementation; semantics are frozen by section 3.
2. Replace stale `min(previous_budget, raw_available)` logic with `min(initial_cap, floor(raw_available * policy_fraction))` for RAM and VRAM.
3. Ensure EVAL, DEPLOY, PES, LOCKED, replay/static consumers, and profile reuse instantiate/use the authority with the same incremental meaning.
4. Preserve pre-model outer command admission before any base model construction/device transfer.
5. After the base provider is resident, take a fresh live snapshot before the static authority admits private-provider growth or inference.
6. Treat unavailable required CUDA telemetry as fail-closed for automatic J>1 growth; do not manufacture free VRAM.
7. Keep all resource state out of scientific identity.

### Focused regression

- 24 GiB total, 18 GiB live used, 6 GiB free, 90% policy -> inner incremental budget is at most 5.4 GiB, not 21.6 GiB and not raw 6 GiB;
- live RAM/VRAM shrink recomputes the configured fraction of current availability;
- EVAL and DEPLOY create equivalent inner-budget semantics from equivalent post-base-provider states;
- DEPLOY/PES/LOCKED initial infeasibility still fails before base model construction;
- unavailable CUDA telemetry blocks automatic private-pool growth.

### Gate acceptance

Run focused resource-coordinate tests plus affected resource-planner, command-admission, static-inference, and staged-EVAL regression before P5-R2B2.

---

## 5. Gate P5-R2B2 — marginal pool admission and exact transition boundaries

### 5.1 Provider-residency estimate

Do not use J=1 execution transient demand as the estimate for a complete private provider.

Before the first private slot is built, use a conservative provider-residency estimate from an existing configured per-model/per-job resource estimate or an explicitly measured base-provider construction/residency estimate. Reuse existing outer scheduler/resource estimates where semantically valid rather than introducing an independent estimator.

After private slots have been measured, update the growth estimate conservatively from actual observed slot residency (for example, the maximum retained per-slot observation, bounded below by the configured estimate). Runtime measurement may tighten or raise the estimate but must never replace an unknown model residency with zero.

### 5.2 Per-slot pool growth

Grow the pool one slot at a time. For each new slot:

1. refresh live incremental budgets;
2. estimate the marginal bytes needed for exactly the next slot;
3. reject before factory/model construction if the next slot cannot fit;
4. materialize the slot;
5. measure actual incremental residency;
6. update the resident-pool accounting and conservative next-slot estimate;
7. refresh live incremental budgets again before attempting another slot.

A partial growth failure must restore the last accepted pool and close only attempt-local providers.

### 5.3 Re-admission before wave launch

After the required J-provider pool is actually resident and immediately before starting prediction workers:

1. refresh live RAM/VRAM budgets again;
2. compute the target point's marginal wave requirement using current resident pool state;
3. reject/reselect before the barrier/workers enter inference if transient execution demand no longer fits.

This post-growth check is mandatory even when the pre-growth estimate passed.

### 5.4 Known-profile and measured-point admission

For a known `(B,J)` point, never compare `aggregate_requirement` directly to current free memory when some or all of its provider pool is already resident. Use the marginal formula from section 3.3.

A smaller-J point must not inherit the residency cost of a larger currently explored pool. If evaluating/selecting a smaller J requires interpretable point semantics, retire surplus providers before measuring that smaller-J point or use the persisted point's own provider-residency components rather than current larger-pool residency.

### Focused regression

- resident J=2 pool with 10 GiB recorded residency and 4 GiB execution peak; current live headroom 8 GiB -> steady-state J=2 wave is admitted because marginal need is 4 GiB, not rejected as a 14 GiB fresh requirement;
- fresh J=2 requirement 10+4 GiB with only 12 GiB live headroom -> rejected before clone/wave launch;
- configured/model residency estimate 5 GiB, J=1 execution transient 1 GiB, live headroom 4 GiB -> first private factory is never called;
- live headroom shrinks or measured clone residency exceeds estimate during pool growth -> wave is blocked after growth and before provider prediction;
- several batches at one resident J reuse the same provider pool without double-charging residency;
- selected lower J after exploring higher J retires surplus once and remains admissible under its own marginal semantics;
- provider call/factory counts continue to prove no per-wave model reconstruction.

### Gate acceptance

Run focused pool-admission tests plus complete affected static inference, profile reuse, staged EVAL, and command-consumer regression before P5-R2B3.

---

## 6. Gate P5-R2B3 — failure taxonomy, pruning, and shared recovery

### 6.1 Failure classes

Separate resource failures by causal dimension. Exact enum/string spelling is delegated, but semantics must distinguish at least:

- **batch/execution OOM**: transient inference at `(B,J)` exceeded executable batch working memory; may lower the learned batch ceiling;
- **provider-pool/residency OOM**: materializing/retaining J model shells failed; may lower/prune concurrency, but must not lower B solely because of provider residency;
- **live-resource rejection**: current headroom does not admit the requested transition before execution; re-clamp/reselect without fabricating an OOM;
- non-resource/provider/model/scientific/programmer failures: hard errors, never converted to adaptive resource evidence.

`StaticInferenceRuntimeAuthority.record()` must update `learned_safe_batch_ceiling` only from evidence whose causal dimension establishes a batch-size limit.

### 6.2 Monotonic pruning

Prune only dimensions justified by evidence:

- provider-pool residency failure at J -> larger/equal J may be pruned for that compatible resource state, independent of B;
- execution/batch failure at `(B,J)` may prune larger B at the relevant J/learned batch ceiling, but must not automatically prove a smaller B at the same J infeasible;
- an arbitrary live-resource failure at `(B,J)` must not globally suppress all future J points unless the rejected component is demonstrably J-only residency.

Remove/replace the current single global `failed_concurrency` behavior if it cannot express these rules cleanly.

### 6.3 Shared cold-search and profile-reuse recovery

Cold calibration and compatible-profile execution must use the same bounded recovery semantics.

If the selected/profile-reused J cannot be materialized or launched for a recognized resource reason:

1. preserve already valid lower-J evidence and the last accepted provider pool;
2. record the causal infeasible boundary;
3. re-clamp/reselect the best remaining measured safe point;
4. retire/grow the pool to that selected point as needed;
5. continue prediction if a safe point remains;
6. terminate cleanly if zero points remain admissible.

Do not retry the same failed state indefinitely. Non-resource exceptions propagate immediately.

### Focused regression

- profile selects J=2, J=2 provider construction OOMs, retained J=1 evidence is safe -> prediction completes at J=1 rather than aborting;
- provider-pool OOM at J=4 leaves the learned safe batch ceiling unchanged and prunes higher concurrency appropriately;
- execution OOM at large B lowers the batch ceiling and preserves eligible lower-B work;
- `(B=8,J=2)` transient/live rejection does not suppress `(B=4,J=2)` unless the causal evidence is J-only residency;
- non-resource provider construction error still propagates;
- zero remaining admission terminates cleanly without deadlock or forced one-job execution;
- exact provider cleanup remains correct on every fallback path.

### Gate acceptance

Run focused failure/recovery tests plus affected scheduler, restart/profile, static consumer, staged-EVAL, and resource-ledger regression.

---

## 7. Gate P5-R2C — strict runtime profile v4 and synchronized timing

The reviewed v3 schema is not strict enough to guarantee its advertised semantics. Fifth-closeout therefore **bumps the static runtime profile/evidence semantics to v4**. Existing v1-v3 profiles must be rejected/rebuilt deterministically. Scientific schemas remain unchanged.

### 7.1 v4 feasible-evidence invariants

Every feasible point must explicitly satisfy:

- `completed_structures > 0`;
- `elapsed_seconds > 0`;
- `observed_max_active_jobs == concurrent_model_jobs`;
- `structures_per_second == completed_structures / elapsed_seconds` within existing serialization tolerance;
- `peak_ram_bytes == provider_pool_resident_ram_bytes + execution_peak_ram_bytes`;
- when all VRAM components are known, `peak_vram_bytes == provider_pool_resident_vram_bytes + execution_peak_vram_bytes`;
- J=1 explicitly records provider-pool residency as zero and records its actual execution peak in the execution component fields rather than relying on compatibility defaults;
- CUDA evidence with unknown required VRAM components is not reusable as safe automatic profile evidence.

Do not allow missing v4 component fields to default silently to zero in `from_dict()` for feasible evidence.

Infeasible evidence may omit unavailable measurement components only where the failure happened before those components could be measured, but its failure class must remain explicit.

### 7.2 Timing boundary

Steady-state throughput remains intentionally warm/persistent-pool throughput, excluding one-time provider materialization. However, elapsed time must include complete result availability on the selected device.

For CUDA, perform an explicit executor-owned device synchronization before stopping the steady-state timer. Resource-monitor teardown may occur afterward, but the throughput timer must not rely on `.cpu()`, `.numpy()`, or other provider-specific side effects to synchronize implicitly.

Do not include provider teardown in steady-state throughput because persistent providers survive the wave.

### 7.3 Profile reuse

A v4 compatible profile is only a source of measured point evidence. Live current-state admission remains authoritative. Profile reuse must:

- re-clamp before any private pool growth;
- use remaining pool growth + execution peak for marginal admission;
- share the resource-failure fallback from P5-R2B3;
- never bypass staged/global RAM accounting;
- never alter scientific identity.

### Focused regression

- v1/v2/v3 profiles are rejected;
- malformed v4 feasible point with aggregate/component mismatch is rejected;
- valid J=1 v4 point explicitly records zero private residency plus nonzero execution peak;
- valid J>1 v4 profile round-trips with exact component invariants;
- CUDA profile with unknown required VRAM component is not accepted as a safe reusable point;
- injected device-synchronization delay is included in `elapsed_seconds`/throughput;
- profile reuse with already-resident pool uses marginal rather than aggregate admission;
- scientific policy/result identity remains unchanged by v4 runtime evidence.

### Gate acceptance

Run focused serialization/timing tests plus all runtime-profile, restart/reuse, numerical-equivalence, and static-consumer regression.

---

## 8. Gate P5-R5 — consumer and staged-resource reconciliation

After P5-R2B1/B2/B3 and P5-R2C stabilize, reconcile every static-MACE consumer to the normalized resource contract.

### Required behavior

1. EVAL, DEPLOY, PES, LOCKED-TEST2, replay pseudo-labeling where applicable, and all discovered static consumers continue through the canonical executor/authority.
2. Consumers may perform pre-base-model admission using their existing outer policy, but after base-provider materialization they must resolve the inner authority's live incremental budgets identically.
3. No consumer passes an absolute used-memory ceiling into a field interpreted as marginal/free headroom.
4. Staged EVAL reserves enough RAM for the maximum permitted inner model pool plus its transient working set; dynamic tightening is allowed only after measured evidence exists and must not under-reserve.
5. Profile reuse never bypasses outer staged/global admission or inner live re-clamping.
6. One outer EVAL inference owner remains; no outer x inner concurrency multiplication.
7. Fixed-J=1 paths remain simple and do not create unnecessary private providers.
8. Preserve graph-cache/head/checkpoint/dtype/precision semantics, sparse reads, restart behavior, and external LAMMPS resource ownership.
9. Remove obsolete adapters/helpers only when their ownership is fully superseded by the canonical resource path.

### Required regression

- equivalent post-base-provider EVAL and DEPLOY states yield equivalent authority resource semantics;
- DEPLOY/PES/LOCKED still fail initial infeasibility before base provider construction;
- post-base live shrink prevents private-pool expansion before clone construction;
- staged EVAL reservation is never below the maximum admitted provider-pool + transient envelope;
- profile-reused command path falls back to lower safe J on provider-pool resource failure;
- numerical/reference parity remains unchanged;
- no duplicate batch/concurrency/provider-pool authority or direct prediction bypass exists.

---

## 9. Gate P5-R8 — final affected-surface reconciliation and acceptance

After the final executable change:

1. independently re-derive the complete affected behavioral surface;
2. search for mixed absolute/incremental VRAM budget semantics, raw-live-availability admission without policy fraction, double-charged provider residency, J=1 transient used as model-residency estimate, candidate/wave launches without immediate admission, generic OOM records that update the wrong dimension, global over-pruning, profile-reuse recovery bypass, malformed v4 evidence acceptance, synthetic concurrency, provider sharing, provider leaks/double-close, and direct consumer admission bypasses;
3. run every new focused reproducer from P5-R2B1/B2/B3/R2C/R5;
4. run fresh complete affected-surface regression across static inference, runtime profiles, resource planning, adaptive scheduler, staged EVAL, DEPLOY/PES/LOCKED, replay/static consumers, restart/reuse, command boundaries, and shared DYN/RELAX/resource code where plausibly affected;
5. run repository-required checks and broader available tests when impact cannot be bounded confidently;
6. run a **separate fresh bounded assembled production-interface integration** on the same final candidate through the available real chain of preflight -> preparation/materialization -> TRAIN/EVAL -> DEPLOY -> PES -> RELAX -> DYN -> selection/publication;
7. the assembled integration must use production orchestration/resource authorities; heavyweight dependencies may be stubbed only below the real public/production boundary;
8. record unavailable checks explicitly; unavailable required functional checks are not passes;
9. keep target-workstation full GPU qualification deferred.

### Minimum new bug reproducers required before final acceptance

- correct 90%-of-live-free VRAM coordinate after base-provider residency;
- correct 80%-of-live-available RAM re-clamp;
- already-resident J>1 pool admits only its execution transient and is not double-counted;
- fresh profile point requires remaining pool growth + transient demand;
- first private provider is blocked by a conservative model-residency estimate even when J=1 execution transient is small;
- post-growth live re-clamp can block the wave before any provider prediction;
- profile-reuse provider-pool OOM falls back to lower measured safe J;
- provider-pool OOM does not lower batch ceiling;
- execution/batch OOM does lower batch ceiling;
- smaller B at the same J remains searchable after a batch-dependent resource rejection;
- v3 profile rejection and strict v4 aggregate/component validation;
- explicit CUDA synchronization is inside steady-state elapsed time;
- provider pool remains persistent/reused and cleanup remains exact;
- actual J concurrency and deterministic numerical ordering remain preserved.

## 10. Stage-local regression sequence

Implementation should proceed in this order because each stage establishes assumptions required by the next:

```text
P5-R2B1 resource-coordinate normalization
    -> focused + affected resource/consumer regression
P5-R2B2 marginal pool admission and transition rechecks
    -> focused + static/profile/staged regression
P5-R2B3 failure taxonomy/pruning/shared recovery
    -> focused + scheduler/restart/consumer regression
P5-R2C strict v4 evidence + synchronized timing
    -> focused + serialization/equivalence/profile regression
P5-R5 consumer reconciliation
    -> command/staged/static integration regression
P5-R8 final affected-surface re-derivation
    -> fresh affected regression
    -> separate fresh assembled integration
```

Do not defer all testing to P5-R8. Reuse older evidence only for behavior untouched by the current stage.

## 11. Product-complexity rules

Prefer repair of the existing ownership model over new machinery.

- `StaticInferenceRuntimeAuthority` remains the one operating-point/resource-policy owner.
- `StaticMaceInferenceExecutor` remains the one persistent-provider execution owner.
- Reuse existing resource telemetry and configured per-job estimates; do not create a second estimator subsystem merely for private-provider growth.
- A small resource-budget value object/helper is acceptable if it removes mixed units/semantics across consumers; it must not become a parallel scheduler.
- Failure taxonomy should be represented in the existing evidence/authority path, not a separate retry manager.
- v4 replaces v3 evidence semantics; do not retain compatibility translators that reinterpret old v3 bytes as v4.

## 12. Preserved gate disposition

- R0: **CLOSED**
- R1: **CLOSED**
- F-R2A: **LOCALLY CLOSED subject to final regression**
- F-R2B: **REOPENED as P5-R2B1/B2/B3**
- F-R2C: **REOPENED as P5-R2C**
- R3B: **CLOSED subject to affected regression**
- R4: **CLOSED**
- F-R5: **TRANSITIVELY REOPENED as P5-R5**
- R6B: **CLOSED subject to affected regression**
- R7: **CLOSED subject to affected regression**
- F-R8: **REOPENED as P5-R8**
- third-round genuine concurrency: **PRESERVE**
- fourth-round persistent provider pool: **PRESERVE**
- fourth-round complete-first-job one-slot calibration: **PRESERVE**

The fourth-reopen section-17 functional acceptance conclusion is withdrawn by this fifth independent review. Its passing tests remain reusable historical evidence only where their establishing dimensions are unchanged.

## 13. Genuine redesign triggers

Stop dependent implementation and reopen only the affected design surface if evidence shows that:

- no single incremental resource coordinate can serve the static consumers without breaking mandatory pre-base-model admission;
- representative MACE provider residency cannot be conservatively estimated or measured sufficiently to avoid unsafe blind pool growth;
- persistent private providers cannot coexist safely at useful J on the intended hardware, making the preserved provider-pool architecture globally inferior;
- v4 resource semantics require replacing the broader campaign resource model rather than normalizing the existing one;
- scientific outputs change outside frozen tolerances;
- correct recovery requires a second scheduler/authority rather than local reconciliation inside the canonical authority/executor.

Ordinary implementation bugs, profile schema bump, resource-coordinate normalization, additional live rechecks, failure-class separation, candidate-pruning correction, or test additions are not redesign triggers.

## 14. Completion condition

Return MLFF-END-TO-END-PERF1 to **FUNCTIONAL IMPLEMENTATION ACCEPTED — TARGET-WORKSTATION GPU QUALIFICATION DEFERRED** only when:

- P5-R2B1, P5-R2B2, P5-R2B3, P5-R2C, P5-R5, and P5-R8 are accepted;
- all static consumers use one coherent post-base incremental RAM/VRAM coordinate;
- configured safety fractions remain enforced on every live re-clamp;
- already-resident providers are never double-counted against current free memory;
- first and subsequent private-provider growth is pre-admitted with a conservative provider-residency estimate and rechecked from measured live state;
- every wave is re-admitted after pool growth and before inference launch;
- provider-pool/resource failure degrades to retained lower safe points in both cold search and compatible-profile reuse;
- failure evidence updates only the causal optimization dimension;
- candidate pruning does not remove smaller-B points without justified monotonic evidence;
- strict v4 profile evidence is internally self-consistent and old v1-v3 profiles are rebuilt rather than reinterpreted;
- steady-state CUDA throughput includes explicit device synchronization;
- persistent provider reuse, actual J concurrency, deterministic ordering, exact cleanup, scientific identity, numerical equivalence, and preserved gates remain regression-clean;
- fresh final affected-surface regression passes;
- a distinct fresh assembled production-interface integration passes on the same candidate;
- genuinely unavailable checks are explicitly recorded;
- full target-workstation GPU qualification remains deferred as the final release handoff.
