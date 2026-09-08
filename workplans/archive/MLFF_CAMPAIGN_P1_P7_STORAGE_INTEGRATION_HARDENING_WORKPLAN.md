---
kind: implementation-workplan
workplan_id: CODE-MLFF-CAMPAIGN-P1-P7-STORAGE-INTEGRATION-HARDENING
protocol_version: 5.14.0
status: active
created_date: 2026-09-04
branch: plan/mlff-storage-io-reset-r37-review-closure
branch_baseline: f020a70d7cd7586f7d76b63c15e71c385d888c17
scope: assembled-P1-P7-CampaignStore-storage-I-O-lifecycle-integration-hardening
parent_scientific_authority: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
composed_storage_authority: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-revision-38
current_p4_prerequisite: CODE-MLFF-TARGET-SIZE-V7-P4-PREPARED-GENERATION-STAGE-BOUNDARY-REPAIR
verdict: NO-PASS / INTEGRATION-REOPENED
---

# MLFF campaign P1-P7 + storage integration hardening workplan

## 0. Integration verdict

**NO-PASS / INTEGRATION-REOPENED.**

The individual P1-P7 packages and the storage reset contain substantial correct local ownership, scientific, persistence, restart, currentness, and cleanup machinery. The assembled campaign nevertheless has multiple genuine cross-boundary defects that prior package-local and assembled tests did not expose. The defects are not evidence that the target-size scientific model, P5 cross-validation/final-production science, P7 qualification science, or Storage Revision 38 architecture are wrong. They are evidence that the contracts **between** those accepted owners were never closed as one product-level lifecycle.

The integration pass found seven material failure families:

1. **Prepared-state ownership mismatch:** P4 binds digests but discards downstream-required prepared objects, so `select-target-size`, terminal exposure, P5 currentness, and lifecycle projection re-enter P1/P2/P3-common reconstruction.
2. **Scientific population / execution batch conflation:** P3 direct EVAL2 and P5 post-selection EVAL2 pass the entire scientific evaluation population as one accelerator batch.
3. **Observation / execution conflation:** public status/currentness paths open writable/create-capable state and invoke operational constructors; qualification status may construct execution support and run model inference merely to observe state.
4. **Lifecycle projection / operational-context conflation:** `_current_public_lifecycle()` builds P4/P5 operational contexts to determine what is current and what command is next; `advance` pays that path before dispatching the actual operation.
5. **Proxy acceptance above resource-realization owners:** existing assembled fixtures replace inference above the batching/device-materialization responsibility, so green tests can coexist with production OOM.
6. **No single assembled acceptance boundary spans P1 -> P7 plus storage and observation/restart semantics:** current integration is split among P4, P5, P7, and storage suites, leaving cross-package transitions and interleavings unowned.
7. **Authority/navigation drift:** package-level status documentation still says P1-P7 are closed and storage is unblocked while the current branch contains an active P4 NO-PASS repair and a Storage Revision-38 implementation NO-PASS/reopen.

These are recurring integration failures around shared Tier-2 mechanisms. Repeated local repair would add more currentness, cache, status, retry, or compatibility machinery around causes that should instead be reduced and canonicalized. Protocol-5.14 active simplicity therefore applies.

This workplan is the integration authority only. It composes, rather than replaces:

- the frozen V7 scientific parent and still-binding P1-P7 scientific semantics;
- the active P4 prepared-generation/resource-safety repair;
- Storage-I/O Reset Revision 38 and its current bounded implementation reopen;
- existing P3/P5/P7 immutable publication, currentness, and failure semantics where not contradicted by the integration repair below.

---

## 1. Original problem / product invariants / non-goals

### 1.1 Original product problem

The MLFF campaign is one restartable scientific workflow, not seven independent packages plus a storage utility. A user must be able to start from source calculations and progress through target-size selection, post-selection validation, final production, and product qualification while each command consumes exactly the durable authority produced by its predecessors, uses resources within the accepted execution envelope, survives process restart, and remains safe under owner-driven storage management.

The product-level lifecycle is materially:

```text
external/source inputs
  -> doctor / environment-input qualification
  -> prepare
       -> P1 canonical scientific substrate
       -> P2 target-size statistical authority
       -> one P3-common prepared substrate
       -> immutable prepared generation g
  -> select-target-size
       -> P3 paired-seed configurable-fidelity screen
       -> immutable terminal head/reducer
       -> P4 current terminal projection
       -> freeze N_selected + exact T_selected
  -> cross-validate
       -> P5 CV on exactly T_selected
       -> accepted/rejected frozen method
  -> train-production
       -> fresh final production on full T_selected
       -> immutable FinalProductionPublication
  -> qualification
       -> P7 product/environment/specification binding
       -> deployment / physical / relaxation / dynamics / calibration evidence
       -> explicit locked-test activation when required
       -> terminal release verdict
```

Storage/report/status operations are orthogonal services over this lifecycle. They are not scientific stages and may not create scientific state merely by observing it.

### 1.2 Tier-1 scientific and product invariants

The following remain invariant and must survive every repair:

1. **V7 target-size science is unchanged.** Candidate-size policy, neutral population, split exclusion, deterministic `pi_train`, exact `T_N`, exact M1/M2/M3 populations, paired optimizer seeds, fidelity epochs, reducer semantics, selected `N/T`, and typed scientific failure semantics are unchanged.
2. **P1 authority remains exact.** Source/control/provenance/canonical-frame semantics, labels, units, ordering, and current accepted scientific validation are unchanged.
3. **P2 authority remains exact.** Target-size statistical population, policy, experiment definition, training/evaluation order, exact candidate memberships, and reducer initialization remain unchanged.
4. **P3 scientific execution remains exact.** Checkpoint/model-state authentication, continuation, exact evaluation artifact membership, prediction evidence, metrics, immutable batch/head/reducer evidence, restart, and terminal reducer semantics remain unchanged.
5. **P5 science remains exact.** Cross-validation partitions and anti-leakage, target-only acceptance, method identity, fresh final-production semantics, replay-label distinctions, final-publication membership, and publication/currentness fences remain unchanged.
6. **P7 science remains exact.** Frozen-product qualification, evidence-role membership, physical/reference separation, stress applicability semantics, deployment parity, relaxation/dynamics/calibration, locked-test one-shot semantics, and release verdict semantics remain unchanged.
7. **CampaignStore remains the sole mutable current campaign-generation/lifecycle authority.** No second generation/currentness database, registry, mutable `latest` authority, or workflow state machine may be introduced.
8. **Immutable descendant evidence stays immutable and lineage-bound.** P3, P5, and P7 historical evidence may remain on disk but cannot be rebound to a new current generation or publication.
9. **Restartability is a product property.** Process death between accepted durable boundaries may require replay of incomplete work, but a downstream command may not silently repeat a completed upstream scientific stage merely because in-memory objects were lost.
10. **Observation is non-mutating.** `status`, qualification status, storage report/dry-run, and equivalent observational APIs must not create directories, state DBs, wrappers, caches, receipts, evidence roots, providers, models, or scientific artifacts; must not execute numerical science; and must not advance lifecycle state.
11. **Resource realization may not change science.** Scientific populations, precision, forces/stress channels, checkpoint/model state, ordering, metrics, and accepted reduction are not performance knobs. Execution batching/concurrency/device scheduling must fit them to the available resource envelope without reducing scientific content.
12. **Storage is owner-driven and scientifically neutral.** Storage may reclaim campaign-managed bytes only when the real owner establishes reclaimability under the current/in-flight lifecycle and all publication/write fences are respected. Storage never grants scientific authority or changes a decision.
13. **External inputs remain external.** Campaign-managed cleanup/dedup/archive never absorbs ownership of user/reference inputs merely because campaign science reads them.
14. **Public lifecycle guidance must be truthful.** `status`/`advance` may not report a stage complete/current or recommend a command from stale/superseded package documentation or from a reconstructed alternate authority.

### 1.3 Engineering envelope

The assembled implementation must remain usable on the supported local GPU/CPU workstation class, including the observed RTX-3090-class device, without assuming that an entire M1/M2/M3 or P5 evaluation population fits in VRAM at once. Resource planning must honor the existing campaign CPU/RAM/VRAM policy and execution-policy identities rather than inventing stage-local hidden limits.

A command that is intended to be observational must be cheap relative to the state it observes: its ordinary cost must scale with the compact persisted state/pointers and small metadata it actually needs, not with DATA4 size, source VASP parse cost, full P1/P2 construction, MACE model forward, or physical qualification workloads.

### 1.4 Non-goals

This workplan does **not**:

- redesign target-size science, P5 CV/final-production science, or P7 qualification science;
- create a generic workflow engine or new task scheduler;
- create a second cache/currentness/freshness/generation database;
- replace CampaignStore CAS or P3/P5/P7 immutable content-addressed publication with another persistence system;
- redesign Storage Revision 38's canonical cleanup architecture;
- add broad compatibility for retired V5/V6/V7-local intermediate machinery beyond still-supported current product contracts;
- introduce OOM-driven scientific degradation, reduced M, skipped force/stress channels, lower precision, or silent CPU fallback;
- require production-scale external-DFT or long-duration GPU qualification for ordinary software-functional closure;
- merge every stage-specific class/helper merely to reduce file count.

---

## 2. Integration diagnosis and failure-point census

This section records the bounded finite lifecycle/owner graph that the integration pass inspected. It is exhaustive over the public campaign transitions, currentness/persistence seams, direct evaluation resource boundary, storage integration boundary, and observation paths in scope. It is not a claim that every numerical helper in the repository was independently rederived.

### F1 — P4 generation state binds identities but not a restartable prepared snapshot

#### Evidence / concern

The current target-size runtime reconstructs `CurrentTargetSizeAuthorities` from source/lower-level inputs. The cutover/state contract explicitly describes binding reconstructed P1/P2 identities while persisting only stable identities. The terminal loader then reconstructs those authorities again before exposing current P4 state. P5's canonical selected-training adapter calls that terminal loader and therefore inherits the same work.

This is not a single slow helper. It is a cross-module ownership contract spanning:

- `campaign_target_size_runtime.py`;
- `campaign_target_size_cutover.py`;
- `campaign_target_size_state.py`;
- `campaign_target_size_terminal.py`;
- `campaign_post_selection.py` and all downstream current-selected consumers;
- lifecycle/status code that uses those currentness owners.

The existing active P4 prepared-generation repair already specifies the owning correction. This integration workplan adopts that repair as a prerequisite rather than creating a competing snapshot design.

#### Required integration end state

`prepare` is the sole live-source/lower-level construction boundary for the target-size prepared scientific substrate. A successful prepare publishes an immutable generation-scoped prepared snapshot sufficient for downstream P3/P5/P7 consumers, then CampaignStore CAS binds that generation and its exact component identities.

Downstream start/resume/terminal/current-result/P5 currentness loads that exact prepared generation and authenticates its persisted component integrity plus current CampaignStore binding. It does not reconstruct P1/P2/P3-common from live sources.

#### Anti-shortcut

Do not preserve live reconstruction and merely cache, parallelize, memoize, or add `trust_prepared`/`fast` flags around it. Do not retrofit a reconstructed snapshot onto an old generation that already owns immutable P3 evidence.

---

### F2 — direct EVAL2 execution conflates scientific population with accelerator batch

#### Evidence / concern

Two production owners share the same defect shape:

```text
P3 direct EVAL2:
  exact-M evaluation artifact -> atoms_list -> provider.predict_batch(atoms_list)

P5 post-selection EVAL2:
  authenticated monitor/outer/replay artifact -> atoms_list
  -> provider.predict_batch(atoms_list)
```

The observed production P3 failure attempted an additional ~8.54 GiB allocation with only ~8.26 GiB free on a ~23.55 GiB GPU while ~14.58 GiB was already allocated. Reserved-but-unallocated memory was small, so allocator fragmentation is not the material cause. The full derivative-bearing MACE graph batch exceeded the device envelope.

P5 has the same structural path and therefore the same latent failure class for CV monitor, outer evaluation, replay monitor, and final-production evaluation populations.

#### Required integration end state

Every large direct model-evaluation owner has an explicit execution-realization boundary **before** native graph/device materialization:

```text
exact scientific population in canonical order
  -> deterministic execution partition/chunks
  -> authenticated provider/model instance
  -> bounded device batch forward(s)
  -> exact-order prediction concatenation
  -> unchanged prediction-evidence digest / EVAL2 reduction
```

The scientific population and its order remain exact. Execution chunk width is bounded by an already-governed execution policy when sufficient; for current P3/P5 target evaluation, `MaceOptimizerPolicy.valid_batch_size` is the preferred existing authority because it is positive, serialized, and already participates in execution-policy identity. An equivalent existing canonical execution field is acceptable if implementation evidence shows it is the actual accepted owner.

One small shared direct-inference batching helper is permitted **only if** it replaces duplicated P3/P5 chunk orchestration and reduces total system complexity. A new generic inference framework is not justified.

#### Anti-shortcut

Forbidden as closure:

- reducing M1/M2/M3 or P5 evaluation membership;
- omitting force/stress computation;
- changing checkpoint/model state or precision;
- silently forcing CPU;
- relying on `torch.cuda.empty_cache()` or allocator environment tuning;
- retrying the same full-population batch after OOM;
- importing DATA6's complete adaptive/restart state machine merely to solve deterministic EVAL2 chunking.

If a single-frame accepted forward cannot fit on supported hardware, fail clearly as a genuine hardware-envelope incompatibility; do not degrade science.

---

### F3 — observational commands execute/mutate operational state

#### Evidence / concern

The repository already has a correct observational capability for storage commands: configuration can be resolved with `ensure=False`, CampaignStore can be opened with `create=False`, and `observational_campaign_state()` propagates a no-create/no-write capability to nested helpers.

The main campaign `status` path does not use this boundary. It resolves configuration with the ordinary create-capable path, opens a normal CampaignStore, and calls `_current_public_lifecycle()`.

Once a target-size selection exists, `_current_public_lifecycle()` calls current P4 selected-state exposure and then `build_post_selection_context(..., trainer=None)`. That operational constructor resolves a trainer/wrapper when none was supplied. Current helper design can therefore create `.mdstats/bin` wrappers merely to answer campaign status.

Qualification `status` has the same category error at greater cost. Although its public contract says status is observational, it builds a full `QualificationSession`. Session construction re-enters P4/P5 currentness, resolves environment/resource/executable/physical-plan state, opens qualification evidence roots, and for a new physical request can run model predictions to determine stress applicability.

The P5 and P7 store-opening helpers also use create-on-open semantics. That is appropriate for consequential execution but not for pure current-state resolution.

#### Required integration end state

All observational public commands and current-state projection APIs must execute under one repository-wide read-only capability contract:

- configuration path resolution does not create workspace subdirectories;
- CampaignStore is opened read-only and cannot create a DB;
- nested campaign helpers inherit observational state and cannot create receipts/caches/wrappers/evidence directories;
- no model/provider/trainer/deployment runtime is constructed;
- no numerical inference, source parse, DATA4/DATA6 restore, P1/P2 reconstruction, or physical-plan evaluation is performed;
- no lifecycle/stage/pointer/position record is written;
- missing state is described as missing/not-started/unresolved, not created to make observation easier.

Prefer adapting existing `observational_campaign_state()` + `CampaignStore(create=False)` semantics rather than inventing another read-only framework.

Evidence-store APIs may expose separate `open_existing` / read-only construction or simply construct non-creating path-backed readers where appropriate. Exact API shape is delegated.

#### Acceptance integrity

For each observational command, snapshot the workspace tree plus hashes/content of managed DB/files before and after. Except for external stdout/stderr and OS-level access metadata not represented in campaign content, the managed campaign state must be byte/path identical.

---

### F4 — lifecycle projection constructs operational contexts

#### Evidence / concern

`_current_public_lifecycle()` is supposed to project current owners into a user-facing lifecycle. Instead, it constructs enough operational state to validate/start downstream work. `command_advance()` first runs that lifecycle projection and then dispatches the actual next command, so an operation can pay repeated currentness construction before its own real execution.

This conflates two distinct questions:

1. **Observation:** what durable stage is current, and what command is admissible next?
2. **Execution admission:** can the next command fully reconstruct/validate every runtime dependency and begin work?

The first needs compact durable authority. The second may legitimately open execution support and perform task-specific validation.

#### Required integration end state

There is one pure lifecycle projection from already-persisted current state/pointers into public stages. It is not a new authority; it is a read-only view over CampaignStore plus owner-local immutable pointers/records that can be resolved without running science.

Materially:

```text
read-only CampaignStore target-size state
+ read-only P5 current pointer presence/validated small records
+ read-only P7 current pointer/status records
  -> CampaignLifecycleSnapshot / equivalent projection
  -> status output + next-command routing
```

Exact type/function names are delegated. A separate durable lifecycle registry is forbidden.

`advance` may use this pure projection to select the next command, then the selected command performs its own full admission/currentness validation exactly once.

If a stage's detailed readiness cannot be proven without expensive execution, the lifecycle view reports the narrow truthful state available from durable evidence (for example `not_started`, `waiting`, `current pointer present`, or `requires run`) rather than executing that work during observation.

---

### F5 — current assembled tests proxy-pass the resource owner

#### Evidence / concern

Existing P5/P7 assembled fixtures correctly keep P1-P5/P7 authority, lineage, persistence, and most orchestration in production code, but their numerical inference seam accepts the complete `atoms_list` and loops over it in the fake. That seam is **above** the production decision to build one native device batch.

Consequently the following can both be true:

- the assembled test is green;
- the production P3/P5 owner OOMs because it materializes the entire scientific population on the GPU.

The test double therefore bypasses a material part of the semantic owner for the resource-safety claim.

#### Required integration end state

Move bounded numerical doubles below the execution-partition owner:

```text
real artifact/member/authentication owner
 -> real exact-order chunk scheduler
 -> fake or real numerical forward per chunk
 -> real result concatenation / digest / reduction
```

The fake may replace expensive MACE arithmetic, but it may not decide chunking, currentness, artifact membership, provider-state authentication, ordering, restart, publication, or reducer behavior when those are the claim under acceptance.

Retain stage-specific cheap tests, but the final integration harness must make a bug in the real chunk/orchestration owner fail.

---

### F6 — assembled lifecycle acceptance is fragmented by package

#### Evidence / concern

Current suites provide useful but fragmented assembled boundaries:

- P4 exercises target-size prepare/screen ownership;
- P5 assembled integration runs `prepare -> select-target-size -> cross-validate -> train-production -> reopen`;
- P7 fixtures build on P5 and qualify a publication;
- storage reset has its own owner/integration fixtures.

No current single acceptance contract exercises the complete public lifecycle plus read-only observation, restart, source/config invalidation, and storage interleavings on the same assembled candidate/workspace. This leaves cross-package assumptions untested.

#### Required integration end state

Add one bounded **campaign integration contract** that drives the real public parser/dispatch and real owners from a fresh workspace through the full supported lifecycle, using only accepted bounded numerical seams below the owner under acceptance.

The contract is detailed in section 6.

This is a test/acceptance consolidation, not a new runtime workflow engine.

---

### F7 — current authority/navigation claims are inconsistent

#### Evidence / concern

The target-size package README still says P1-P6 are accepted/reclosed, P7 is closed/pass, and Storage reset is unblocked. On the same branch:

- the active P4 prepared-generation/EVAL2 workplan is NO-PASS;
- the Storage Revision-38 authority is explicitly `status: reopened` and `NO-PASS / IMPLEMENTATION-REOPENED`.

A stale package navigation entry can route implementers/reviewers/operators to superseded closure assumptions and defeats snapshot-complete handoff.

#### Required integration end state

After implementation, reconcile current navigation/status documentation so it truthfully names:

- the still-frozen scientific parent;
- current package closure/reopen state;
- this integration workplan and its final disposition;
- current Storage R38 authority/disposition;
- the actual assembled candidate/evidence identity.

Do not rewrite historical evidence to pretend earlier reviews saw later defects. Correct current navigation only.

---

## 3. Frozen high-level integration architecture

The following architecture is deliberately Frozen for this implementation cycle.

### 3.1 One directional scientific lifecycle

```text
LIVE INPUT AUTHORITY
  source/reference/config bytes
          |
          v
PREPARE — sole upstream construction/advance boundary
  P1 canonical substrate
  P2 target-size statistical authority
  P3 common preparation
  immutable prepared generation g
          |
          v
SELECT-TARGET-SIZE — prepared-generation consumer
  P3 screen / immutable evidence / terminal reducer
  P4 current terminal projection
          |
          v
POST-SELECTION — selected-binding consumers
  P5 CV -> accepted method
  P5 final production -> frozen FinalProductionPublication
          |
          v
QUALIFICATION — frozen-product consumer
  P7 nonlocked evidence -> optional explicit locked activation -> release verdict
```

No downstream command re-enters an already-completed upstream construction stage merely to prove currentness.

### 3.2 CampaignStore is the sole mutable current campaign authority

CampaignStore owns the current target-size generation/lifecycle and commit-time currentness fences. P5/P7 immutable objects and namespaced pointers remain descendants of exact selected/final-publication bindings. No parallel currentness database, generation registry, or `latest` state is added.

### 3.3 Durable owner boundary is publish -> verify -> adopt

For every stage whose output must survive restart:

```text
construct/validate descendant
 -> publish immutable object(s)
 -> verify exact identity/integrity
 -> atomic/CAS pointer or CampaignStore transition makes them current
```

A crash before adoption may leave unreachable residue; it does not create current authority. A current pointer/state must never name missing/corrupt required descendants without failing closed.

### 3.4 Observation and execution are separate capabilities

Observation reads the current graph; execution may extend it.

```text
OBSERVE
  no create
  no write
  no numerical execution
  no upstream reconstruction
  compact current-state projection only

EXECUTE
  full task-specific validation
  owner-specific resource plan
  immutable publication
  currentness-fenced adoption
```

The same helper may support both only if its observational mode is structurally incapable of writes/execution; do not rely on a caller convention around a create-capable implementation.

### 3.5 Scientific population and execution partition are separate concepts

`M`, `T_N`, fold memberships, monitor populations, replay populations, and qualification cohorts are scientific/domain membership. Batch/chunk/worker count is execution realization. All accelerators receive work through an explicit bounded realization boundary. Chunking must preserve exact input order and final numerical semantics.

### 3.6 Storage remains an orthogonal owner-driven service

Storage Revision 38 remains Frozen:

- semantic owners decide reclaimability;
- one canonical consequential destructive implementation family performs filesystem mutation;
- P3/P5/P7 publication barriers and activity/no-write leases reduce deletion authority;
- ambiguous/in-flight/current state fails closed;
- storage does not become a scientific/currentness authority.

This integration work adds the repaired prepared-generation/frame-payload lifetime to the owner graph and acceptance matrix; it does not create another cleanup route.

### 3.7 Currentness is dependency-local

A stage validates the identities it actually consumes. It does not recursively recompute the entire ancestral scientific graph when durable authenticated ancestry already establishes that parent.

Examples:

- select validates current CampaignStore generation + prepared snapshot integrity + P3 execution policy;
- P5 validates current selected binding + required prepared/P1 access + P5 method/config identities;
- P7 validates current final publication + qualification binding/environment/specification;
- status validates only compact state/pointer integrity needed to report lifecycle.

This keeps validation strict while eliminating repeated ancestor reconstruction.

---

## 4. Implementation obligations and delegated solution space

### INT-A — close and compose the P4 prepared-generation repair

**Concern.** Integration cannot be hardened while downstream currentness still means upstream reconstruction.

**Required end state.** Implement the active `P4_PREPARED_GENERATION_STAGE_BOUNDARY_REPAIR.md` contract and make the resulting prepared-generation loader the canonical P1/P2/P3-common dependency supplied to P3/P5/P7 current consumers.

**Integration-specific requirement.** The prepared snapshot publication must expose enough owner metadata for storage inventory/retention without requiring DATA4 or source reconstruction. The storage owner view must be able to identify current/in-flight prepared artifacts and the normalized frame payload they require.

**Delegated.** Exact snapshot record classes/layout, helper names, and manifest factoring remain governed by the P4 plan.

**Acceptance.** P4 plan acceptance plus the full assembled integration matrix in section 6.

---

### INT-B — canonicalize bounded direct-inference execution for P3/P5

**Concern.** The same unbounded batch defect exists in at least P3 direct EVAL2 and P5 post-selection EVAL2.

**Required end state.** P3 and P5 evaluate exact populations through deterministic bounded chunks before native graph/device materialization. All outputs are concatenated in exact role order and reduced exactly as before.

**Suggested realization, delegated.** One small internal chunk iterator/executor over an authenticated provider and ordered atom sequence, parameterized by accepted batch width, is preferable if it replaces duplicate logic. It must not own scientific membership, checkpoint selection, currentness, metrics, or persistence.

**Policy.** Prefer the already-authoritative `valid_batch_size` of the accepted optimizer/execution policy. Do not add `[target_size].eval_batch_size` or a second persistent execution-policy object unless implementation evidence proves the existing policy cannot represent the required execution semantics.

**Acceptance boundary.** Real P3/P5 evaluation owner and real chunk orchestration must execute. The expensive model arithmetic may be faked below that boundary. One bounded real MACE-provider CUDA smoke must exercise at least two chunks on the target hardware class before software closure if that hardware is available in the project environment; absence of CUDA blocks only that hardware-specific qualification claim, not CPU-only semantic regression.

**Numerical acceptance.** On deterministic fixtures, chunked versus single-call reference prediction entries must be equal within the existing accepted model/backend precision tolerance; all discrete role/order/digest identities must remain exact. The final EVAL2 metric/reducer input must be identical to the same ordered predictions.

---

### INT-C — make all status/report/current-lifecycle observation genuinely read-only

**Concern.** `status` and qualification status currently invoke create-capable operational paths.

**Required end state.** Route every observational command through the existing observational capability, `ensure=False` path resolution, read-only CampaignStore, and non-creating owner readers. Nested helpers must fail rather than write when observation is active.

At minimum reconcile:

- `command_status`;
- `_current_public_lifecycle` and `_next_public_operation`;
- qualification `status`;
- any storage/report commands not already using the observational boundary;
- P5/P7 current record readers reachable from those commands;
- wrapper/cache/receipt/evidence-root creation reached indirectly from observation.

**Required reduction.** Do not add `if status: skip X` checks throughout the call graph. Separate the pure projection/reader from operational context construction so the write-capable dependency disappears from the observation path.

**Acceptance.** Managed filesystem + DB snapshot before/after each observational command is exactly unchanged. Monkeypatch/guards make provider construction, MACE forward, `_ensure_local_wrappers`, DATA4/DATA6 restore, source parsing, prepare builder, directory creation in owner stores, and CampaignStore writes fail if called; status must still return truthful output for supported states.

---

### INT-D — reduce lifecycle routing to a pure persisted-state projection

**Concern.** `_current_public_lifecycle()` currently reconstructs operational context to answer stage/next-command questions.

**Required end state.** Derive lifecycle from current persisted owner state and small immutable/pointer records only. `advance` uses this projection to choose a command, then the chosen command performs task admission exactly once.

**Allowed projection content.** Target-size regime/lifecycle/generation, terminal selected/failure projection, P5 pointer presence/validated compact plan/acceptance/final-publication state, P7 compact qualification status/locked/release pointer state, and stage-marker information only where stage markers are explicitly diagnostic rather than authority.

**Forbidden.** Building a provider/trainer, parsing source calculations, restoring DATA4, loading complete prepared arrays merely for routing, evaluating qualification stress capability, or creating missing roots.

**Acceptance.** For every lifecycle state in the matrix, `status` and `advance` preflight choose the same next operation as the accepted owner states imply; `advance` does not invoke the expensive/currentness constructor twice before work begins.

---

### INT-E — reconcile create-on-open owner stores with observation

**Concern.** P5/P7 evidence-store open helpers create roots, which turns reads into mutations.

**Required end state.** Consequential execution may create generation/attempt roots. Read/currentness/observation paths must be able to inspect an existing store without creating it. Missing store/root means no evidence or a fail-closed missing-current-artifact error depending on the owner contract, not implicit creation.

**Delegated.** Separate `open_existing`, a `create` flag, direct path-backed readers, or another simpler API is acceptable. Do not create a parallel store implementation.

**Acceptance.** Read-only P5/P7 current-resolution tests against an absent root do not create the root. Current pointer -> missing object/root still fails closed as corruption; no evidence pointer -> absent root reports no evidence without mutation.

---

### INT-F — compose Storage R38 with the repaired prepared-generation lifetime

**Concern.** A correct prepared-generation boundary is defeated if cleanup can evict its required normalized frame payload or prepared objects and thereby force hidden source/DATA4 reconstruction.

**Required end state.** Storage owner inventory classifies the repaired current/in-flight prepared snapshot and its required frame payload according to actual P3/P5/P7 consumer lifetime. Current/in-flight consumers remain restartable after safe cleanup. Historical/redundant artifacts become reclaimable only when the real owner no longer needs them.

**Preserve Revision 38.** Do not modify the Frozen canonical destructive topology. Extend/reconcile owner views and retention facts only as needed for the new prepared-generation representation.

**Also close current Storage authority blockers.** Correct the two stale cleanup-topology specification statements identified by Storage IR20 and execute/record exact-candidate Revision-38 focused + affected regression/integration/static checks after material integration edits.

**Acceptance.** Section 6 storage interleavings plus existing Storage R38 acceptance. No current/in-flight P3/P5/P7/prepared artifact is reclaimed; no safe cleanup causes a later stage to re-enter prepare/DATA4/source reconstruction.

---

### INT-G — rebuild integration fixtures around real owner boundaries

**Concern.** Existing fixtures replace model inference above the batching/resource owner and therefore cannot establish hardware/resource orchestration claims.

**Required end state.** Retain cheap analytic/toy numerical arithmetic but move it below the real execution-partition owner. Record the actual chunk sizes/order received by the fake and assert they match the accepted execution policy.

The full campaign fixture must use:

- real public parser/dispatch for lifecycle commands;
- real CampaignStore and generation transitions;
- real prepared-generation publication/load;
- real P3/P5/P7 currentness and immutable persistence owners;
- real lifecycle projection/status/advance;
- real storage report/plan/executor owners for integration claims;
- fake training/model arithmetic only below the owner under acceptance;
- real MACE provider for a bounded CUDA resource smoke where required and available.

Do not build a second in-test state machine that predicts campaign behavior and then assert production output matches itself. The test model may be an oracle for invariants, not a replacement owner.

---

### INT-H — reconcile current authority/navigation and durable architecture docs

**Concern.** Current package navigation contradicts actual reopen state and future repaired architecture will change prepare/select/currentness/observation semantics.

**Required end state.** Reconcile at least:

- `workplans/active/mlff-target-size-v7-packages/README.md`;
- current P4 authority/navigation if it has a package entrypoint;
- `workplans/active/mlff-storage-io-reset/AUTHORITY.md` only for actual post-implementation review disposition, not to predeclare pass;
- stable campaign architecture/user documentation describing prepare -> select -> P5 -> P7;
- storage spec prepared-artifact/frame-cache ownership text;
- status/qualification-status observational contract;
- execution performance docs distinguishing scientific population from execution batch.

Historical revision/evidence files remain historical and are not rewritten.

---

## 5. Implementation authority

### 5.1 Frozen

The implementation cycle freezes:

1. all Tier-1 scientific/product invariants in section 1.2;
2. directional lifecycle `prepare -> select-target-size -> P5 -> P7` with storage/observation orthogonal;
3. prepare as sole creation/advance boundary for the target-size prepared scientific snapshot;
4. immutable generation-scoped prepared snapshot consumed downstream without live upstream reconstruction;
5. CampaignStore as sole mutable current generation/lifecycle authority;
6. P3/P5/P7 immutable descendant publication plus commit-time currentness fences;
7. observation/execution capability separation;
8. explicit execution partition before accelerator materialization, with scientific membership unaffected by batch width;
9. Storage Revision-38 canonical owner-driven destructive architecture;
10. no second currentness/cache/generation/freshness/workflow registry;
11. exact public lifecycle integration acceptance boundary in section 6, including restart, observation purity, storage interleavings, and resource-realization coverage.

### 5.2 Delegated

The following remain Tier 2 and replaceable:

- exact prepared snapshot classes/files/manifest layout, subject to the P4 repair;
- `CurrentTargetSizeAuthorities` name and decomposition;
- exact pure lifecycle projection class/function name;
- exact read-only store API shape;
- helper names and module boundaries;
- whether P3/P5 chunking uses one small shared helper or two thin calls over one iterator;
- exact chunk loop implementation;
- progress/timing messages;
- test fixture class names and factoring;
- exact storage owner-view record names for prepared artifacts;
- internal diagnostic stage markers not used as authority;
- existing wrappers/caches/receipts that can be deleted or narrowed while preserving Frozen behavior.

### 5.3 Reopen only on evidence

Reopen this design only if implementation/representative execution proves one of these Frozen assumptions false:

1. a downstream P3/P5/P7 scientific consumer genuinely requires live-source reinterpretation between prepare and consumption rather than a snapshot;
2. a required prepared object cannot be persisted/reloaded losslessly within the supported storage/resource envelope and no simpler equivalent representation exists;
3. existing optimizer/execution policy cannot express a safe deterministic direct-inference batch width without changing scientific identity and a distinct execution-policy field is therefore materially required;
4. a scientific algorithm genuinely requires simultaneous full-population GPU residency, making chunking mathematically nonequivalent;
5. Storage Revision 38 cannot retain/reclaim the prepared representation without changing its Frozen destructive architecture;
6. CampaignStore cannot represent the required current/adoption relationship without a material architecture change.

Evidence that a current helper/API is inconvenient, a test fixture is hard to adapt, or a prior patch assumed another boundary does not satisfy these triggers.

---

## 6. Assembled campaign acceptance contract

### 6.1 One fresh-workspace public lifecycle

Build one bounded campaign fixture from a fresh workspace and drive **real public parser/dispatch** through:

```text
1. doctor
2. prepare
3. close process / reopen
4. status
5. storage report + cleanup dry-run
6. select-target-size
7. close / reopen
8. status
9. cross-validate
10. close / reopen
11. status
12. train-production
13. resolve/freeze FinalProductionPublication
14. close / reopen
15. status
16. qualification status
17. qualification run
18. expected waiting_for_reference when independent reference is absent
19. close / reopen
20. supply bounded authenticated reference fixture
21. qualification run / resume through nonlocked completion
22. explicit locked activation when required
23. close / reopen
24. final qualification status / current release-evidence resolution
```

The fixture may use small data, few seeds/folds/epochs, and analytic/toy arithmetic, but every owner above the explicitly accepted numerical seams must be production code.

Required assertions:

- exact generation/state monotonicity;
- no current stage reads historical descendants as current;
- N/T and P5/P7 lineage match exact parents;
- process restart at every marked boundary changes no scientific identity;
- `status`/qualification status never alter state;
- P3/P5/P7 publication pointers survive reopen;
- `waiting_for_reference` is a truthful nonterminal product state, not failure or auto-activation;
- locked activation remains explicit and one-shot;
- final release evidence reauthenticates from the current final publication.

### 6.2 Observation-purity matrix

Exercise at least these states:

1. no workspace yet;
2. doctor only;
3. prepared generation;
4. active P3 screen;
5. terminal selected P4;
6. current P5 CV plan without acceptance;
7. accepted CV;
8. final-production plan without completion;
9. frozen final publication;
10. qualification not started;
11. qualification waiting for reference;
12. nonlocked qualification complete / locked not activated;
13. final qualified or rejected release state;
14. corrupt/missing current descendant states used for fail-closed tests.

For each applicable observational command (`status`, qualification status, storage report/dry-run and owner-level read APIs):

- snapshot managed path set + file hashes + CampaignStore logical rows before;
- execute command;
- assert exact managed state equality after;
- assert no wrapper/provider/model/source parser/DATA4 restore/prepare builder/numerical-forward owner was called.

### 6.3 Prepared-generation / invalidation matrix

#### Source mutation

```text
prepare -> g1
mutate one preparation-owned source/control/companion byte
status / select / P5 current read of g1
```

Must continue to observe/consume exact g1 without live reinterpretation. Then `prepare` detects the changed preparation input and creates g2. Old P3/P5/P7 descendants remain historical and cannot become g2-current.

#### P5-only configuration mutation

Change a P5 CV/final-production-only policy that is explicitly excluded from target-size identity. P4 prepared/selected generation remains current. P5 descendants whose own identity depends on the change become stale/recomputed under P5 rules; P4 is not rebuilt.

#### P7-only configuration mutation

Change a qualification-only policy. P1-P5 remain current; P7 binding/attempt changes as specified by qualification identity. Prior P7 evidence remains historical and cannot become current by pointer aliasing.

#### Execution-only resource change

Change a non-scientific resource realization such as available CPU or safe worker/chunk realization where policy permits runtime adaptation. Scientific identities remain unchanged; execution remains within resource limits.

### 6.4 Corruption / missing-artifact matrix

At minimum:

- missing prepared-generation component;
- corrupt prepared component;
- current CampaignStore binding to incomplete prepared state;
- missing normalized frame payload still required by current downstream consumer;
- corrupt/missing P3 head/batch/completion;
- corrupt P4 terminal projection;
- missing P5 immutable object behind a current pointer;
- stale P5 pointer/binding after generation advance;
- missing final publication member/checkpoint;
- corrupt P7 component evidence or pointer;
- absent qualification evidence root with no pointer;
- pointer to absent qualification object.

Every case must either truthfully report not-started/no-evidence or fail closed as corruption according to owner semantics. No case may reconstruct a missing upstream scientific product from live inputs inside a downstream command.

### 6.5 Resource-realization matrix

For P3 direct EVAL2 and P5 post-selection evaluation test:

- population size `1`;
- population size exactly `batch`;
- `batch + 1`;
- multiple full chunks plus remainder;
- heterogeneous atom counts representative of campaign structures;
- stress-present and stress-absent accepted cases;
- CPU/reference provider and target CUDA provider where available.

Required properties:

- chunk sizes never exceed accepted execution batch bound;
- exact input order preserved;
- prediction count/order exact;
- per-frame prediction entries equivalent to unchunked bounded reference;
- prediction digest/reduction/metrics equivalent;
- no scientific membership changes;
- provider/model state authenticated once per role as required by existing P3/P5 owner semantics;
- no full scientific population is materialized as one native device graph batch when its cardinality exceeds the bound;
- no OOM retry path changes scientific behavior.

### 6.6 Storage interleaving matrix

Use the real Storage Revision-38 plan/executor/owner views.

At minimum interleave storage report/dry-run and authorized cleanup at:

1. after prepare;
2. during/after active P3 publication window;
3. after P4 terminal selection;
4. during P5 run activity lease;
5. between P5 immutable-object publication and pointer commit;
6. after final publication;
7. during P7 qualification attempt;
8. between P7 object publication and pointer commit;
9. after final release evidence;
10. after a later prepare advances to a fresh generation.

Prove:

- current/in-flight prepared/P3/P5/P7 artifacts are retained;
- normalized frame payload required by current downstream consumers is retained or directly restorable from the prepared representation without source/DATA4 reconstruction;
- external inputs are never candidates;
- stale/historical reclaimability follows the actual owner, not pathname age;
- stale storage plans fail synchronized revalidation rather than retargeting;
- cleanup never changes scientific/current pointers;
- no safe cleanup makes the next valid command repeat a completed upstream stage.

### 6.7 Concurrency/currentness matrix

Bounded process/thread tests must cover:

- concurrent prepare/current-generation advance versus stale P5 writer;
- concurrent generation advance versus stale P7 writer;
- P3/P5/P7 publish-before-pointer windows versus cleanup;
- status/read-only observation concurrent with consequential execution;
- two identical idempotent publications;
- differing publications from the same expected predecessor where owner semantics require conflict.

No long training is needed. Keep expensive work outside locks and exercise only the commit/adoption boundary.

### 6.8 Structural / absence acceptance

On the final assembled candidate, use semantic caller/reference inspection and focused structural scanning where available. Establish:

1. one prepare-only scientific-substrate builder path;
2. one canonical prepared-generation loader/current consumer owner class/path;
3. no downstream production path calls the prepare builder as currentness fallback;
4. no `read_data4_sharded_record` / source VASP reconstruction reachable from ordinary select/resume/terminal/P5/P7 current exposure after successful prepare;
5. no P3/P5 evaluation owner directly maps an unbounded scientific population to `provider.predict_batch(whole_population)`;
6. no observational command reaches create-capable store/root/wrapper/provider/numerical execution;
7. no second currentness/generation/freshness/cache registry;
8. no managed campaign filesystem destructive path outside the canonical Storage-R38 destructive owner family;
9. P3/P5/P7 publication barriers/currentness fences remain live and reachable;
10. current package/navigation docs name the actual active authorities and candidate disposition.

When local analysis tools are available, use Serena for symbol caller/reference closure and Semgrep for focused structural variants/absence claims. Validate any acceptance-critical Semgrep rule against a known-positive construct and a known-negative construct. Do not infer exhaustive absence from text search alone where dynamic/exported callers matter.

### 6.9 Stateful/property testing

The campaign transition graph is finite but has many restart/observe/invalidation interleavings. Use Hypothesis stateful/property testing where it materially reduces missed combinations, with the **real production CampaignStore/owner transitions** under test and a small model only as the oracle.

Useful generated actions include:

- observe status;
- close/reopen;
- prepare unchanged;
- mutate preparation input then prepare;
- open/advance/complete bounded screen;
- publish P5 descendants;
- publish final publication;
- run qualification waiting/completion;
- storage report/dry-run/safe cleanup;
- stale writer attempts after generation advance.

Properties:

- observation is idempotent and non-mutating;
- generation is monotonic and changes only at accepted owners;
- a current descendant always has current ancestry;
- stale descendants never become current;
- restart alone changes no state;
- current required artifacts are never storage-reclaimed;
- currentness failure never triggers hidden upstream reconstruction.

Do not replace the production state transitions with a test-only state machine.

### 6.10 Performance / I-O acceptance

Record representative bounded before/after evidence for:

- repeated unchanged prepare;
- select startup and resume;
- campaign status on prepared/selected/post-selection states;
- qualification status before/after publication;
- P5 evaluation with chunked inference;
- storage report/dry-run.

Record at least:

- wall time;
- DATA4 restore count;
- source-frame parse/read count;
- prepare-builder invocation count;
- model-forward count and chunk sizes;
- bytes read where practical;
- peak RAM/VRAM for representative direct inference;
- filesystem/DB mutation count for observation (must be zero).

No arbitrary universal speedup percentage is required. Structural removal of repeated upstream work and bounded accelerator memory are mandatory.

### 6.11 Production qualification boundary

**Software-functional integration qualification is required.**

**Full production scientific qualification remains deferred** unless separately requested or required by release policy. The assembled bounded suite must exercise the real product owners, a representative real MACE CUDA inference path where available, and truthful P7 `waiting_for_reference` behavior. It need not run full production target-size training, external DFT, long MD, or production-scale P7 workloads merely to prove software integration.

---

## 7. Expected affected surface

This is an initial census, not a frozen file list. Re-derive the final affected surface from the assembled candidate.

### Target-size P4 / P3 integration

- `mdstats/training_data/campaign_target_size_runtime.py`
- `campaign_target_size_state.py`
- `campaign_target_size_cutover.py`
- `campaign_target_size_terminal.py`
- `campaign_target_size_view.py`
- `campaign_target_size_adoption.py` where prepared/current lineage crosses adoption
- `target_size_execution/evaluation.py`
- P3 execution context/resolver/persistence only as required by accepted prepared-generation/resource boundaries
- normalized frame cache access/retention owner

### P5 integration

- `campaign_post_selection.py`
- `campaign_post_selection_runtime.py`
- `post_selection_execution.py`
- `post_selection_store.py`
- final publication/currentness/reclosure owners only where current prepared/observation semantics propagate

### P7 integration

- `qualification/commands.py`
- `qualification/runtime.py`
- `qualification/store.py`
- `qualification/providers.py` only where observation/resource seams propagate
- current qualification pointer/exposure owners

### Campaign CLI / policy / resource integration

- `_campaign_cli_core.py`
  - configuration/path resolution
  - observational capability routing
  - `_current_public_lifecycle`
  - `command_status`
  - `command_advance`
  - wrapper creation boundary
  - CampaignStore read-only/open semantics as needed
- `resources.py` and accepted optimizer/execution-policy plumbing only as needed for direct-inference execution

### Storage

- `storage/owners.py`
- `storage/inventory.py` / control-plane owner views as affected
- `storage/executor.py` only if prepared-generation barrier/owner-view composition requires reconciliation; do not fork mutation mechanics
- existing canonical removal owner must remain sole destructive implementation family
- storage specs/docs and current Revision-38 closure evidence

### Tests / benchmarks / docs

- P4/P5/P7 current integration fixtures
- assembled P5/P7 lifecycle tests
- storage reset integration suite
- new campaign-wide integration harness/property tests
- bounded CUDA direct-inference smoke
- current package README/navigation
- campaign user/architecture/performance/storage docs

---

## 8. Implementation sequence

### Stage 1 — close prepared-generation ownership first

Implement/close the active P4 prepared-generation repair through its stage-local acceptance. Do not begin by building lifecycle/status wrappers around the old reconstruction model.

Stage-local closure:

- prepared snapshot round-trip/currentness;
- prepare-only reconstruction;
- select/resume/terminal no upstream replay;
- frame payload lifetime reconciled enough for downstream restart.

### Stage 2 — repair shared direct-inference resource realization

Cut P3/P5 direct evaluation over to bounded deterministic chunks and move test seams below chunk orchestration.

Stage-local closure:

- exact prediction/reduction equivalence;
- chunk boundary tests;
- representative real provider resource smoke;
- no remaining unbounded P3/P5 population-to-device-batch path.

### Stage 3 — separate observation from operational context

Refactor public lifecycle projection, core status/advance preflight, qualification status, and P5/P7 read-store access so observation is structurally read-only and non-numerical.

Stage-local closure:

- observation-purity matrix;
- truthful lifecycle routing;
- no wrapper/provider/root creation;
- no duplicate expensive admission before `advance` dispatch.

### Stage 4 — compose P5/P7 currentness over the repaired generation

Reconcile all current-selected/final-publication/qualification consumers with the prepared-generation loader and pure lifecycle projection. Remove any remaining downstream ancestor reconstruction or duplicate currentness path.

Stage-local closure:

- source/P5-only/P7-only invalidation matrix;
- stale-writer/current pointer guards;
- fresh-process reauthentication.

### Stage 5 — compose Storage Revision 38

Update prepared-generation/frame-payload owner views and retention, close Storage IR20 specification/evidence blockers, and run the storage interleaving matrix. Preserve the Revision-38 destructive owner architecture.

Stage-local closure:

- no current/in-flight artifact reclamation;
- safe reclaim of owner-authorized historical/redundant state;
- no cleanup-induced upstream regeneration;
- exact-candidate storage regression/integration evidence.

### Stage 6 — final assembled lifecycle acceptance

Run the entire section-6 campaign contract on one assembled candidate after all material executable edits. Add stateful/property coverage for restart/observe/invalidation/storage combinations. Re-run full affected regression and repository-required checks.

### Stage 7 — authority/documentation reconciliation and independent review

Update current navigation/docs to the actual integrated state. Record exact candidate SHA/tree and executed evidence. Independent Software Design review evaluates the assembled implementation against:

- frozen V7 science;
- this integration workplan;
- active P4 repair;
- Storage Revision 38 + current bounded reopen;
- actual current source/tests/evidence.

Pass only if no genuine integration blocker remains.

---

## 9. Simplification triggers and forbidden repair patterns

The current defect family has already crossed the simplification threshold: repeated P3/P4/P5/P6/P7 repair layers coexist with duplicated currentness reconstruction, create-on-read stores, operational status projection, and test seams above material resource decisions. The implementation must reduce these causes before adding new durable machinery.

### Prefer

```text
one CampaignStore current-generation authority
+ one immutable prepared generation
+ one prepare builder
+ one prepared loader
+ one pure lifecycle projection
+ one bounded direct-inference execution concept
+ existing P3/P5/P7 immutable descendant stores
+ one canonical Storage-R38 destructive owner family
```

### Avoid

```text
rebuild upstream science to check currentness
+ cache the rebuild
+ add fast/trust flags
+ special-case status skips
+ another lifecycle registry
+ stage-specific eval-batch policies everywhere
+ OOM retries around oversized batches
+ create-on-read evidence stores
+ package-local integration tests that bypass cross-package owners
```

### Explicitly forbidden

- a second campaign lifecycle/currentness database or durable state machine;
- a second prepared/frame cache when the existing representation can satisfy the owner lifetime;
- status-specific monkeypatching/bypass logic in production to suppress side effects rather than removing operational dependencies;
- a `trust_current`, `skip_prepare_validation`, `fast_status`, or similar weaker-currentness mode;
- automatic prepare/rebuild fallback from select/P5/P7;
- lowering scientific M/evaluation populations to fit GPU memory;
- CPU fallback or precision downgrade that changes accepted execution semantics without explicit policy;
- treating `torch.cuda.empty_cache()`/allocator tuning as the primary resource fix;
- copying DATA6's complete adaptive batching/restart machinery into P3/P5 without demonstrated need;
- a new storage cleanup path for prepared artifacts outside Revision 38;
- deleting/weakening tests simply because the repaired owner boundary makes prior proxy fixtures inconvenient;
- making stage markers authoritative when real owner state exists;
- updating current README/workplan status to PASS before exact assembled acceptance is established.

---

## 10. Tool-assisted implementation/review contract

When a local checkout/tool surface is available:

### Serena

Use semantic symbol/caller/reference inspection for:

- prepare builder / prepared loader callers;
- terminal/current selected consumers;
- `_current_public_lifecycle` and operational-context reachability;
- create-on-open evidence-store callers;
- P3/P5 direct inference callers;
- storage destructive owner/reference closure.

Cross-check dynamic/parser/exported paths with ordinary search/runtime evidence.

### Semgrep

Use focused structural rules for diagnosed variants/absence claims, including:

- whole-population `predict_batch(...)` in P3/P5 direct evaluation owners;
- observational commands constructing create-capable CampaignStore/path/store/wrapper operations;
- managed-root direct destructive filesystem calls outside the canonical storage removal owner;
- downstream fallback into prepare-only builders.

Validate acceptance-critical rules on known-positive and known-negative examples before relying on zero findings.

### Hypothesis

Use stateful/property testing for the bounded campaign transition/interleaving properties in section 6.9. The real CampaignStore/production owner transitions remain under test; the model is only an oracle.

If a specialized tool is unavailable or unsupported, preserve the engineering claim through branch-scoped semantic/source inspection and real-boundary runtime tests rather than weakening acceptance.

---

## 11. Closure criteria

This integration workplan closes only when one exact assembled candidate satisfies all of the following:

- P4 prepared-generation repair is closed;
- prepare is the only upstream P1/P2/P3-common creation/reconstruction boundary;
- ordinary downstream commands never restore DATA4 or parse live VASP sources merely to establish currentness;
- P3 and P5 direct evaluation use bounded deterministic execution partitioning without scientific change;
- public status and qualification status are genuinely read-only/non-numerical;
- lifecycle projection is derived from persisted owner state without operational context construction;
- `advance` selects then admits one command without duplicate expensive currentness reconstruction;
- P5/P7 reads do not create missing evidence roots;
- P5/P7 stale writers still lose commit-time currentness races;
- Storage Revision 38 correctly protects current/in-flight prepared/P3/P5/P7 artifacts and has its existing IR20 blockers closed;
- safe cleanup cannot force a later valid command to repeat completed upstream science;
- one fresh-workspace public lifecycle reaches P7 waiting/terminal states through real owners with restart boundaries;
- source/P5-only/P7-only/resource-only invalidation semantics are correct;
- observation-purity, corruption, resource, storage, and concurrency matrices pass;
- final affected regression and repository-required checks pass on the exact candidate;
- current navigation/docs truthfully describe the integrated authority state;
- no second currentness/cache/generation/freshness/workflow/destructive-storage machinery was introduced.

A candidate is **not** accepted merely because every package-local suite is green. The final acceptance claim is the assembled campaign: P1-P7, CampaignStore, resource realization, observational control plane, restart/currentness, and Storage Revision 38 must work together as one product.
