# MLFF-END-TO-END-PERF1 Eighth-Reopen Narrow Compatibility and Acceptance Closeout Workplan

Status: **ACTIVE — FINAL COMPATIBILITY / ACCEPTANCE CLOSEOUT**  
Branch: `feat/mlff-end-to-end-performance-v1`  
Reviewed implementation tip: `6a148a643a21d14dfc62627f3ba8029504860a8c`  
Parent active delta: `workplans/active/MLFF_END_TO_END_PERF1_REOPEN7_IMPLEMENTATION_WORKPLAN.md`  
Date reopened: 2026-08-24

## 1. Authority and scope

This file is the authoritative narrow delta-workplan for the remaining MLFF-END-TO-END-PERF1 functional closeout after independent review of implementation tip `6a148a643a21d14dfc62627f3ba8029504860a8c`.

REOPEN7 implemented its main source-level architectural corrections correctly. This round therefore **does not reopen the PERF1 architecture**. It reopens only four tightly bounded surfaces:

1. **derived static runtime-profile compatibility:** pre-REOPEN7 profile v5 can contain a globally reduced batch ceiling learned incorrectly from a J>1 production backoff, yet current code still accepts the same v5 schema/evidence semantics;
2. **provider-growth rollback cleanup:** a failed multi-slot growth can release CUDA allocator cache once during rollback and again in the outer provider-OOM handler;
3. **historical execution-plan v2 consumer coverage:** the v2 -> v3 parser/migration is correct locally but has not yet been exercised through the actual persisted restart/manifest consumer path;
4. **assembled integration:** the current REOPEN7 integration exercises real campaign state and static-profile persistence, but still does not traverse the required production-facing DEPLOY -> PES -> RELAX -> DYN -> selection/publication chain.

Nothing else is reopened. In particular, do not redesign or replace the scheduler, runtime authority, provider pool, resource-coordinate model, staged-EVAL ownership, scientific policy, training protocol, selection policy, DYN/RELAX architecture, or target-size architecture merely to satisfy this closeout.

Full target-workstation RTX 3090/data-heavy production qualification remains deferred to the final release handoff.

## 2. Frozen accepted mechanisms

Implementation MUST preserve without replacement unless a genuine redesign trigger in Section 10 fires with concrete evidence:

- `StaticInferenceRuntimeAuthority` as the sole `(batch_size, concurrent_model_jobs)` operating-point/resource/failure/profile-reuse authority;
- `StaticMaceInferenceExecutor` as the sole persistent provider/model-shell pool and static-inference execution owner;
- genuine worker-private J-way execution and observed-concurrency evidence;
- deterministic prediction aggregation/order;
- the accepted two-dimensional failure model:
  - J=1 execution OOM/backoff may tighten the single-provider/global batch ceiling;
  - J>1 execution OOM/backoff creates a `(B,J)` boundary and does not invalidate safe larger-B lower-J evidence;
  - provider-pool OOM affects provider concurrency only;
  - live-resource rejection is transient and is not reusable capability evidence;
- fresh automatic J>1 growth fails closed unless a complete conservative provider-residency requirement exists;
- one outer staged-EVAL inference owner with no outer x inner inference-concurrency multiplication;
- normalized post-base incremental RAM/VRAM coordinates and fresh policy-fraction reclamping;
- pre-base command admission and pre-/post-provider-growth admission;
- conservative provider-residency requirement distinct from raw observed allocator/RSS growth;
- persistent private-provider reuse and one executor-owned normal pool-shrink reclamation transaction;
- complete-first-job one-slot CUDA calibration;
- explicit executor-owned CUDA synchronization inside steady-state timing;
- `InferenceExecutionPlan` v3 and its exact historical v1/v2 migration logic;
- graph-cache/head/checkpoint/dtype/precision/numerical/scientific identity semantics;
- restart, DYN, RELAX, and publication architecture except for the bounded integration evidence required below.

Do NOT introduce a second scheduler, retry manager, profile authority, provider registry, resource planner, compatibility translator, or test-only orchestration implementation.

## 3. Gate C8-A — invalidate pre-fix static runtime evidence with profile v6

### 3.1 Root cause

Before REOPEN7, a successful J>1 production wave with internal worker batch backoff could directly tighten `learned_safe_batch_ceiling`. The resulting profile v5 could therefore persist a batch ceiling whose causal meaning was corrupted: a concurrency-dependent J>1 event had been encoded as a single-provider/global batch constraint.

REOPEN7 corrected future learning, but it retained:

```text
mdstats.static-inference-runtime-profile.v5
persistent-provider-required-residency-plus-steady-state-execution-peak.v5
```

and current profile reuse still trusts the persisted `learned_safe_batch_ceiling`. Old v5 bytes therefore cannot be proven semantically safe.

This is derived runtime optimization evidence, not authoritative scientific/user data. Per the compatibility policy, **invalidate and rebuild rather than attempt an ambiguous migration**.

### 3.2 Required implementation

Bump both the runtime-profile schema and evidence-semantics authority to v6, for example:

```text
STATIC_INFERENCE_RUNTIME_PROFILE_SCHEMA =
    "mdstats.static-inference-runtime-profile.v6"

STATIC_INFERENCE_EVIDENCE_SEMANTICS =
    "persistent-provider-required-residency-plus-2d-failure-learning.v6"
```

The exact string may differ, but it MUST encode the new causal failure semantics and MUST differ from v5.

Requirements:

- current writes use v6 only;
- v1-v5 runtime profiles are not migrated into reusable current evidence;
- `StaticInferenceRuntimeProfile.load_compatible(...)` must treat v1-v5 as incompatible/unusable and force normal fresh calibration;
- the v6 payload may retain the current field layout unless a strictly necessary local adjustment is found; do not invent a new profile subsystem;
- the v6 compatibility digest/path must be distinct from v5 because compatibility identity includes evidence semantics; verify this rather than merely assuming it;
- a stale v5 profile file may remain on disk as harmless cache residue, but it must never influence current selection or `learned_safe_batch_ceiling`;
- first current invocation after encountering only v5 evidence calibrates normally and writes v6;
- second compatible invocation reuses the newly written v6 evidence subject to current live admission;
- this profile-version bump MUST NOT alter `InferenceExecutionPlan` v3, scientific policy digests, checkpoint/head identity, numerical output, or campaign scientific identity.

Do not attempt to reconstruct a v6 global batch ceiling from v5 because v5 lacks sufficient causal evidence to determine whether its persisted ceiling came from J=1 or the old J>1 production bug.

### 3.3 Mandatory focused reproducers

Add focused tests proving at minimum:

1. syntactically valid v1-v5 static runtime profiles are refused for automatic current reuse;
2. a specifically constructed valid v5 profile whose persisted global ceiling is artificially reduced is ignored, rather than constraining the current authority;
3. v6 write/read/content-digest round-trip is exact;
4. v6 compatibility identity differs from v5 identity for otherwise identical hardware/model/workload inputs;
5. first current invocation with only stale v5 evidence calibrates and writes v6;
6. second current invocation loads and reuses v6 without repeating cold calibration when live resources remain admissible;
7. J=1 and J>1 failure evidence in v6 reconstruct the accepted causal limits correctly;
8. scientific/numerical outputs and `InferenceExecutionPlan` v3 identity remain unchanged.

### 3.4 C8-A stage-local acceptance

Before C8-B, run the focused v6 tests plus affected regression covering static inference, profile persistence/reuse, compatibility-key/path construction, campaign EVAL, DEPLOY/PES/static consumers, restart, and numerical equivalence.

## 4. Gate C8-B — make provider-growth failure cleanup a single executor-owned transaction

### 4.1 Root cause

Normal J-high -> J-low pool shrink now has correct one-release ownership. A partial growth failure can still execute two releases:

```text
accepted J
 -> create one or more new private slots
 -> later private-slot construction fails
 -> _ensure_provider_pool rollback via _retire_private_providers(...)
      -> CUDA cache release
 -> exception reaches prepare_wave provider-OOM handler
      -> second CUDA cache release
```

If the first attempted private slot fails before any new provider is appended, rollback does not shrink but allocator fragments from failed construction may still need one cleanup release. Therefore simply removing all failure-path releases is not sufficient.

### 4.2 Required ownership rule

`_ensure_provider_pool()` owns the complete cleanup transaction for **provider-construction/growth failure**. `prepare_wave()` owns classification/recovery policy but not allocator cleanup for an exception already cleaned by `_ensure_provider_pool()`.

Recommended local realization:

1. add a narrow private control to `_retire_private_providers`, e.g. `release_cuda_cache: bool = True`, preserving the current default behavior for normal lifecycle shrink;
2. in `_ensure_provider_pool()` exception handling:
   - remember the accepted pool size before growth;
   - retire any newly accepted surplus providers back to that size with `release_cuda_cache=False`;
   - close any attempt-local provider exactly once if construction returned ownership before failing;
   - call the executor's `_release_cuda_cache()` exactly once after rollback; CPU executors naturally no-op through the existing device guard;
   - re-raise the original exception without changing its causal type;
3. in `prepare_wave()`:
   - classify the re-raised failure as `live-resource`, `provider-pool-oom`, or non-resource error using the existing classifier;
   - **do not call `_release_cuda_cache()` again for provider-construction failure**;
   - retain lower accepted pool/evidence and continue bounded fallback exactly as today;
4. do not alter steady-state wave cache behavior, normal J-high -> J-low shrink behavior, provider ownership, or the OOM classifier.

The implementation may choose an equivalent local structure, but the invariant is mandatory:

```text
one failed provider-growth transaction
    -> exact provider rollback
    -> at most one executor-owned CUDA allocator release
```

### 4.3 Mandatory focused reproducers

Add tests proving at minimum:

1. CUDA first-private-slot resource OOM performs exactly one cache release and preserves the base provider;
2. CUDA later-slot OOM after at least one successful new private provider closes only newly added/surplus providers, returns to the prior accepted pool, and performs exactly one cache release;
3. generic `MemoryError()` and `OSError(ENOMEM)` use the same one-release cleanup and provider-pool fallback;
4. a non-resource provider-construction exception propagates after exact cleanup and does not become fake OOM evidence;
5. CPU growth failure performs zero CUDA releases;
6. normal CUDA J4 -> J2 shrink still closes exactly two providers and performs exactly one release;
7. same-J steady-state waves perform no allocator release;
8. no provider is leaked or double-closed.

### 4.4 C8-B stage-local acceptance

Before C8-C, run focused cleanup tests plus affected static inference, provider lifecycle, resource-admission, profile-reuse, staged-EVAL, DEPLOY/PES/LOCKED, cancellation/error, and command-boundary regression.

## 5. Gate C8-C — exercise historical execution-plan v2 through the actual persisted consumer

### 5.1 Objective

The REOPEN7 v2 -> v3 parser is accepted as the source authority. This gate does not redesign it. It closes the remaining consumer-level compatibility evidence requirement.

### 5.2 Required integration shape

Use an exact historical-v2 payload and digest under the **actual production persistence key/artifact/manifest/state path consumed by restart/evaluation**, not an arbitrary test-only key.

Drive the real consumer far enough that it:

1. reads historical v2 bytes from normal persisted campaign/restart state;
2. invokes the existing `InferenceExecutionPlan.from_dict()` migration authority;
3. obtains a current v3 runtime plan;
4. retains `provider_residency_ram_bytes=None` and `provider_residency_vram_bytes=None` unless the normal current resource-planning path independently supplies new conservative estimates;
5. enters the canonical current static inference/resource authority path;
6. if the plan is persisted again, writes current v3 bytes/digest rather than silently preserving or rewriting v2 under old semantics.

Do not add a test-only migration store, alternate parser, or compatibility shim.

### 5.3 Mandatory checks

The consumer-level test must prove:

- valid historical v2 survives the normal restart/consumer boundary;
- corrupted historical v2 still fails through that same boundary;
- no provider-residency evidence is fabricated from old bytes;
- current planning remains fail-closed for J>1 until valid current provider-residency authority exists;
- normal current resource planning may then enable J>1 exactly as designed;
- current re-persistence is v3;
- checkpoint/head/scientific/numerical identity is unaffected.

### 5.4 C8-C stage-local acceptance

Before C8-D, run focused persisted-consumer tests plus affected campaign execution, manifest/state store, restart/reuse, staged-EVAL, static inference, DEPLOY/PES/LOCKED, publication/command-boundary, and numerical-equivalence regression.

## 6. Gate C8-D — complete the real bounded assembled production integration

### 6.1 Objective

Close the final acceptance gap without production-scale work. The existing scheduler-only callback test and REOPEN7 campaign-state/static-profile test remain useful lower-level integration coverage, but neither by itself satisfies assembled product integration.

### 6.2 Production boundary requirement

Use the highest practical real campaign/public orchestration entrypoint, preferably the real `campaign_cli.main(...)` command progression and production campaign state machinery, to exercise a bounded version of:

```text
init / campaign state
-> preflight
-> preparation / materialization
-> TRAIN / EVAL orchestration
-> DEPLOY
-> PES
-> RELAX
-> DYN
-> selection / publication
```

The repository already owns the relevant production modules, including `production_materialization.py`, `deploy_verify.py`, `pes_verify.py`, `relax_verify.py`, and `dyn_verify.py`. The integration must cross their production-facing boundaries where they are part of the campaign path; it must not replace them with synthetic `_StagedEvaluationTask` callbacks named after the stages.

### 6.3 Bounded fixture rules

The fixture must:

- create a temporary/self-contained campaign root;
- create the minimum tiny ASE/configuration/reference artifacts needed by real orchestration contracts;
- use the real `CampaignStore`, manifests/ledgers/stage states, plan propagation, and publication/restart state;
- enter production preflight/preparation/materialization/training/evaluation/verification orchestration through real command or public production boundaries;
- stub expensive MACE training/model execution and LAMMPS/numerical work **below** their production-facing interfaces only;
- keep real DEPLOY/PES/RELAX/DYN orchestration, state transitions, resource ownership, and publication wiring;
- avoid external LTA training roots, full MACE training, long trajectories, target GPU requirements, and production-scale data;
- run on CPU;
- not create a parallel test-only campaign orchestrator.

### 6.4 First invocation assertions

The first run must establish, through durable production state/artifacts rather than only call ordering:

- preflight and materialization transition through their real states;
- TRAIN/EVAL consumes the real execution-plan/resource ownership path;
- canonical static inference writes a **v6** runtime profile;
- production-facing DEPLOY, PES, RELAX, and DYN boundaries each execute at least once;
- final selection/publication state/artifact is produced through production code;
- a bounded failure/cancellation/cleanup boundary is exercised where practical without duplicating the full chain;
- counters inserted below expensive external boundaries show that orchestration—not a test-side replay of orchestration—owns execution order.

### 6.5 Second invocation / restart assertions

Run the same campaign root a second time and prove actual restart/reuse behavior:

- persisted completed stage/state records are recognized;
- already completed expensive external work is not redundantly replayed unless production semantics intentionally require it;
- an exact historical-v2 execution-plan fixture, where used for C8-C, is consumed/migrated through the real restart path;
- stale v5 runtime profile evidence is ignored;
- current v6 runtime profile is actually loaded/reused on the second compatible static-inference invocation, not merely regenerated;
- live admission still re-clamps current resources before use;
- terminal selection/publication state remains consistent and deterministic.

Profile reuse must be asserted through production-observable behavior/evidence, such as the compatible-profile loader result or absence of cold-calibration candidate waves, rather than output equality alone.

### 6.6 C8-D acceptance evidence

Report separately:

1. bounded assembled production integration, first invocation;
2. restart/reuse second invocation;
3. any bounded failure/cancellation/cleanup assembled-path test.

A scheduler-only callback chain, direct helper invocation without downstream production stages, or repeated fresh invocation that merely returns the same outputs is not sufficient.

## 7. Final acceptance sequence

After the final executable edit from C8-A..D:

### 7.1 Fresh affected-surface re-derivation

Re-derive the final affected surface and search specifically for:

- any accepted current `mdstats.static-inference-runtime-profile.v5` or older profile path;
- stale v5 evidence-semantics identifiers that permit reuse;
- any loader/migration that translates v5 runtime evidence into current reusable evidence;
- compatibility-key/path logic that does not change when evidence semantics change;
- direct J>1 writes to `learned_safe_batch_ceiling`;
- provider-growth rollback followed by a second allocator release in `prepare_wave` or another caller;
- CPU executor paths touching CUDA allocator cache;
- double-close or leaked private providers on growth failure;
- historical-v2 tests using arbitrary test-only store keys rather than an actual consumer;
- v2 migration fabricating provider-residency evidence;
- assembled integration that bypasses `deploy_verify`, `pes_verify`, `relax_verify`, `dyn_verify`, or final selection/publication production boundaries;
- direct helper calls being counted as assembled campaign traversal;
- second-run tests that compare outputs without proving restart/profile reuse;
- duplicate schedulers/resource authorities/provider pools introduced by the repair.

### 7.2 Mandatory final regression

On the same final candidate, run:

- all C8-A/B/C focused reproducers;
- all still-valid REOPEN6/REOPEN7 focused static-inference, scheduler, provider-pool, profile, resource, serialization, and numerical tests;
- complete affected static MACE inference/profile persistence/reuse regression;
- campaign execution/staged-EVAL/resource planner regression;
- DEPLOY/PES/LOCKED/replay/static-consumer regression;
- restart/manifest/store/publication/command-boundary regression;
- DYN/RELAX/shared-resource/failure-cleanup regression where plausibly affected;
- repository-required checks and the broader available suite if final impact cannot be bounded confidently.

Then run C8-D assembled integration separately and record its result separately from the regression aggregate.

A required test that does not execute is not a pass. Demonstrably pre-existing unrelated unavailable checks may be recorded, but must not be counted as functional acceptance.

## 8. Implementation sequence

Implement in this order:

```text
C8-A
runtime profile v6 invalidation
+ v5 refusal / v6 recalibration-reuse
    -> focused profile/compatibility tests
    -> stage-local static/profile/restart regression

C8-B
single-owner provider-growth failure cleanup
    -> focused lifecycle/error tests
    -> stage-local resource/provider/consumer regression

C8-C
historical v2 through actual persisted consumer
    -> focused restart/manifest compatibility tests
    -> stage-local campaign/restart/command regression

C8-D
real bounded assembled campaign integration
    -> fresh affected-surface re-derivation
    -> all focused reproducers
    -> fresh complete affected-surface regression
    -> first-run assembled integration
    -> second-run restart/profile-reuse integration
    -> repository-required/broader available checks
```

Do not defer all regression to C8-D. Each behavior-changing executable gate requires its own focused + affected stage-local regression before dependent implementation proceeds.

## 9. Gate disposition entering REOPEN8

- original PERF1 architecture: **CLOSED / PRESERVE**
- complete-first-job CUDA calibration: **CLOSED subject final regression**
- normalized post-base resource coordinate: **CLOSED**
- conservative provider-residency floor: **CLOSED**
- genuine worker-private J concurrency: **CLOSED / PRESERVE**
- persistent provider pool: **CLOSED / PRESERVE**
- REOPEN7 CLOSE-1 production 2-D backoff learning source fix: **CLOSED subject final regression**
- REOPEN7 CLOSE-2 fresh no-estimate J>1 fail-closed behavior: **CLOSED**
- REOPEN7 CLOSE-2 normal pool-shrink ownership: **CLOSED**
- C8-B partial-growth failure cleanup: **OPEN narrowly**
- REOPEN7 CLOSE-3 `InferenceExecutionPlan` v3 parser/migration source fix: **CLOSED**
- C8-C v2 actual-consumer compatibility evidence: **OPEN narrowly**
- C8-A static runtime-profile v5 reuse: **OPEN narrowly; invalidate to v6**
- C8-D assembled production integration: **OPEN**
- scientific identity/numerics/training protocol/DYN/RELAX architecture: **CLOSED / PRESERVE**
- target RTX 3090/data-heavy production qualification: **DEFERRED**

## 10. Genuine redesign triggers

Do not reopen broader design for ordinary implementation/test work. Stop dependent implementation and reopen only the implicated surface if evidence demonstrates that:

- current v6-compatible runtime evidence cannot represent the accepted 2-D failure semantics without changing the authority model;
- safe provider-growth cleanup cannot be expressed with one executor-owned transaction under current provider ownership;
- historical-v2 production state cannot be consumed through the existing v3 migration authority without changing public restart contracts;
- real production DEPLOY/PES/RELAX/DYN/selection boundaries cannot be exercised in a bounded fixture without changing the public production architecture;
- scientific/numerical outputs change outside frozen tolerances because of these repairs.

A runtime-profile schema bump, cache invalidation, local rollback flag/helper, test fixture, additional production-boundary stub, or regression repair is **not** a redesign trigger.

## 11. Final completion condition

MLFF-END-TO-END-PERF1 may be marked:

**FUNCTIONAL IMPLEMENTATION ACCEPTED — TARGET-WORKSTATION GPU QUALIFICATION DEFERRED**

only when all of the following hold on the same final commit:

- v6 is the only accepted current static runtime-profile schema/evidence semantics;
- v1-v5 runtime profiles cannot influence current `learned_safe_batch_ceiling`, operating-point selection, or provider-growth admission;
- stale/contaminated v5 evidence causes normal fresh calibration, not compatibility translation;
- first current calibration writes valid v6 and a second compatible invocation genuinely reuses it;
- v6 compatibility identity/path is distinct from v5;
- REOPEN7 2-D J=1/J>1 failure semantics remain regression-clean;
- every provider-growth failure rolls back exact ownership and performs at most one executor-owned CUDA allocator release;
- CPU executor failures perform zero CUDA allocator releases;
- historical execution-plan v2 is consumed through the actual production persisted restart/manifest path and migrates to v3 without fabricated provider-residency evidence;
- current re-persistence uses v3;
- the bounded assembled production path crosses real preflight/materialization/TRAIN-EVAL/DEPLOY/PES/RELAX/DYN/selection-publication boundaries;
- the second assembled invocation proves actual persisted restart and v6 profile reuse rather than output equality alone;
- all required focused tests execute successfully;
- fresh final affected-surface regression executes successfully;
- assembled integration executes successfully and is reported separately from regression counts;
- no unrelated PERF1 architecture or scientific behavior is changed;
- broader unavailable checks, if any, are demonstrably pre-existing/unrelated and recorded as unavailable rather than passed;
- full RTX 3090/data-heavy production qualification remains deferred to the final release handoff.

No documentation-only claim, callback-only pseudo-chain, stale v5 compatibility, or unavailable assembled test may substitute for these executable acceptance requirements.
