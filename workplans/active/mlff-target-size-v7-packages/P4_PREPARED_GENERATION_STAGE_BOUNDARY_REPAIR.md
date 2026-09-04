---
kind: implementation-package-amendment
package_id: CODE-MLFF-TARGET-SIZE-V7-P4-PREPARED-GENERATION-STAGE-BOUNDARY-REPAIR
parent_package: P4_ATOMIC_RUNTIME_PERSISTENCE_CUTOVER.md
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
status: active
created_date: 2026-09-04
amended_date: 2026-09-04
branch: plan/mlff-storage-io-reset-r37-review-closure
branch_baseline: 4d61cd1f5ba0356a5746d5c45254430db5188595
scope: bounded-P4-stage-ownership-persistence-currentness-I/O-and-direct-EVAL2-resource-safety
compatibility_policy: destructive-current-generation-rebind-no-scientific-change
design_reopen: P4-D prepared-state ownership plus P3 direct-EVAL2 execution batching only
---

# P4 prepared-generation stage-boundary and direct-EVAL2 resource-safety repair

## 0. Verdict and bounded design reopening

**NO-PASS until this amendment closes.**

Two independent implementation defects now block the current target-size workflow.

### Defect A — preparation is reconstructed across command boundaries

`prepare` constructs the expensive target-size scientific substrate, but the implementation persists only selected identities and later commands reconstruct the same upstream scientific graph. The present control flow is materially:

```text
prepare
  -> DATA2/DATA3/DATA4/DATA5 + normalized frame payload as needed
  -> restore DATA4
  -> rebuild/authenticate P1
  -> rebuild neutral substrate / split exclusion
  -> rebuild P2 aggregate
  -> rebuild P3 common preparation
  -> persist generation identities/digests

select-target-size
  -> restore DATA4 AGAIN
  -> rebuild P1/P2/P3-common AGAIN
  -> run/resume P3 screen

terminal/current-result/P5-facing load
  -> restore DATA4 AGAIN
  -> rebuild P1/P2/P3-common AGAIN
  -> validate P3 terminal evidence
```

`CampaignStore.get_record("data4", Data4FeatureBundle)` performs the real sharded DATA4 restore/verification path. This is repeated O(dataset) work, not a cheap currentness check.

The prior post-DATA4 performance repair remains valid inside the **prepare builder**: it removed redundant direct VASP frame rereads, separated fresh P1 authentication from frame acquisition, reused normalized frame data, and restored bounded canonical-frame parallelism. It does not justify repeating preparation in downstream commands.

### Defect B — direct EVAL2 passes the scientific population as one GPU batch

The supplied failing production run reaches the first target-size boundary, completes TRAIN2, then fails in direct EVAL2 inference with:

```text
run_target_size_direct_boundary_inference(...)
  -> provider.predict_batch(atoms_list)
  -> MaceCalculatorProvider.predict_batch(...)
  -> one native torch_geometric Batch for the entire atoms_list
  -> model(... compute_stress=True ...)
  -> CUDA OOM
```

Observed failure evidence includes:

- GPU total capacity about 23.55 GiB;
- about 8.26 GiB free at the failing operation;
- one additional requested allocation of about 8.54 GiB;
- about 14.58 GiB already actively allocated by PyTorch;
- only about 72.62 MiB reserved-but-unallocated.

Therefore allocator fragmentation is not the material cause. The active derivative-bearing MACE forward for the full evaluation set exceeds the device envelope. `PYTORCH_CUDA_ALLOC_CONF`, `empty_cache()`, or allocator tuning cannot make an intrinsically oversized full-evaluation batch a sound execution policy.

The current source confirms the mismatch:

```text
run_target_size_direct_boundary_inference
  -> read and authenticate exact-M evaluation artifact
  -> atoms_list = all M frames
  -> provider.predict_batch(atoms_list)
```

while the native provider path:

```text
predict_batch(atoms_batch)
  -> _native_batch(atoms_batch)
       -> build one CPU graph batch
       -> move that whole batch to the configured device
  -> derivative-enabled model forward
```

The scientific **evaluation population size M** and the resource **execution batch width** are different concepts. Conflating them makes VRAM scale with the full scientific population and will become worse at later M2/M3 boundaries.

This amendment therefore reopens only:

1. P4-D prepared-state/currentness ownership and its dependent terminal/current-result seam; and
2. the P3 direct-EVAL2 **execution batching/resource realization**, without changing any P3 scientific role, population, model-state, metric, reduction, or evidence semantics.

A bounded sibling census is also required for direct MACE evaluation consumers that repeat the same full-list `predict_batch(...)` pattern, including post-selection evaluation if the current candidate still does so. This is affected-surface expansion of the same resource invariant, not a reopening of P5 science.

---

## 1. Original problem and product invariants

The stakeholder-visible lifecycle remains:

```text
prepare
  -> construct and freeze the scientific substrate for one generation

select-target-size
  -> consume that frozen substrate
  -> execute paired-seed configurable-fidelity TRAIN2/EVAL2 screening

terminal/post-selection consumers
  -> consume the same frozen generation and authenticated P3 descendants
```

The product must be scientifically exact, restartable, reusable across command boundaries, and executable within the configured machine resource envelope without requiring a scientific-policy change merely to fit memory.

### 1.1 Frozen scientific invariants

The following remain unchanged:

1. The V7 target-size scientific question and one-dimensional `N` experiment.
2. Exact P1 source/canonical-frame semantics and accepted source/control/ensemble/energy authentication facts.
3. Exact neutral statistical substrate and split-exclusion semantics.
4. Exact P2 target-size policy, experiment definition, deterministic training order, aggregate, and reducer initialization semantics.
5. Exactly one deterministic P3 common preparation per target-size generation.
6. Exact ordered candidate sizes, optimizer-seed pairing, fidelity boundaries, M1/M2/M3 evaluation populations, TRAIN2/EVAL2 roles, continuation, immutable evidence, reducer, and selected-`N/T` semantics.
7. Exact EVAL2 evaluation membership and order for each role.
8. The authenticated model/checkpoint state, live-vs-EMA choice, device, dtype/precision policy, required forces/stress/energy predictions, metric definition, and reducer outcome do not change as a memory workaround.
9. CampaignStore remains the sole current generation/revision/lifecycle authority.
10. Immutable P3 execution evidence remains generation-bound and is never rewritten to make changed scientific identity fit an old generation.

### 1.2 Stage and operational invariants

1. Successful `prepare` freezes one immutable prepared scientific snapshot for generation `g`.
2. `select-target-size` does not recompute or reinterpret the upstream prepared substrate for `g`.
3. Downstream commands do not restore DATA4 merely to recreate already-completed P1/P2/P3-common state.
4. Resume/reload/report paths do not repeat O(dataset) preparation work merely to prove currentness.
5. Live source edits after successful `prepare` do not retroactively mutate or reinterpret `g`; a subsequent `prepare` owns detection and generation advance.
6. Missing/corrupt prepared state fails closed with actionable `prepare` guidance. Downstream commands do not silently rebuild it from live sources.
7. Existing immutable screen evidence stays bound to the exact prepared generation that created it.
8. Warm startup scales with data the command actually consumes, not DATA4/P1/P2 reconstruction cost.
9. Scientific evaluation size `M` is not an execution batch size. Peak device work for one direct-EVAL2 forward must be bounded independently of full `M`.
10. Batching/chunking is an execution realization only: concatenated predictions must preserve exact evaluation order, count, role ancestry, and accepted numerical semantics.
11. One authenticated provider/model state performs all chunks for one direct-EVAL2 role. Chunking must not rebuild/reload a different provider state per chunk.

### 1.3 Resource envelope

For the accepted MACE GPU path:

- no single target-size EVAL2 call may intentionally materialize the entire exact-M evaluation population as one native device batch unless `M <= optimizer_policy.valid_batch_size`;
- the production EVAL2 batch width is bounded by the already accepted positive `MaceOptimizerPolicy.valid_batch_size` for that candidate policy;
- the final short batch may be smaller;
- scientific `M`, frame order, model state, dtype/device, force/stress computation, and reduction remain unchanged;
- target-hardware acceptance must include a real GPU smoke because CPU-only tests cannot establish the VRAM claim.

The existing optimizer policy already serializes `valid_batch_size`, and the seed-neutral target-size execution-context identity includes the optimizer-policy payload except only the explicitly excluded seed/per-realization acceleration fields. No second `eval2_batch_size` configuration is required.

### 1.4 Non-goals

This repair does not:

- change candidate sizes, fidelity epochs, evaluation sizes, seeds, or P2/P3 ranking policy;
- lower evaluation size to avoid OOM;
- disable forces, stress, or any accepted EVAL2 observable;
- change precision, device, acceleration backend, or checkpoint state to avoid OOM;
- add automatic CPU fallback;
- add a general workflow engine, cache database, freshness registry, generation registry, or resource-policy database;
- add a second frame cache;
- make result-view files authoritative;
- require long full-screen GPU qualification during ordinary implementation tests;
- optimize unrelated P5/P6/P7 numerical kernels. A direct-inference full-batch sibling is affected only because it violates the same memory-safety invariant.

---

## 2. Frozen high-level architecture

### 2.1 Prepare creates; downstream commands consume

Frozen ownership:

```text
                         PREPARE OWNS CREATION

live source inputs
  -> DATA2/DATA3/DATA4/DATA5 + normalized frame payload
  -> fresh P1 authentication
  -> canonical frame authority
  -> neutral statistical substrate + split exclusion
  -> P2 target-size aggregate/definition
  -> one P3 common preparation
  -> publish immutable prepared-generation artifacts
  -> CampaignStore CAS binds/advances canonical generation

                         DOWNSTREAM OWNS CONSUMPTION

CampaignStore current generation
  -> load exact generation-scoped prepared artifacts
  -> verify prepared component integrity against CampaignStore
  -> select-target-size / resume
  -> terminal validation/report/current-result exposure
  -> P5/P7 consumers as applicable
```

A downstream consumer may verify the prepared artifact it loads and the current CampaignStore revision. It must not establish currentness by reconstructing the entire upstream scientific graph from live inputs.

### 2.2 Prepared state is immutable and generation-scoped

Persist enough downstream-required prepared state to restart P3 without P1/P2/P3-common reconstruction. Prefer the minimum sufficient consumer-facing state.

At minimum downstream P3 currently needs semantic equivalents of:

- canonical frame authority;
- split-exclusion/correlation evidence required by P3;
- target-size aggregate/definition/reducer initial state;
- common preparation;
- frame catalog;
- normalized frame payload/frame-array access required for materialization/evaluation.

Persist neutral/source/feature intermediates only when a real downstream consumer requires them or one compact representation reduces total machinery.

A compact prepared-generation manifest/receipt is allowed only if it canonicalizes component membership and replaces broader synchronization. It is not a second current pointer; CampaignStore remains sole current-generation authority.

### 2.3 Existing normalized frame representation is reused

The existing authenticated normalized frame cache remains the canonical hot frame representation. Do not create another frame cache.

For an active prepared generation whose P3/P5/P7 consumers require it, retention follows actual owner demand. Cleanup must not evict it in a way that forces hidden DATA4/P1 reconstruction inside downstream commands. Prefer retaining the existing representation over adding another one unless measured storage pressure proves otherwise.

### 2.4 DATA4 is prepare-owned cold evidence after preparation

After successful preparation:

- ordinary `select-target-size` start/resume: zero DATA4 sharded restore;
- terminal load/report/current-result exposure: zero DATA4 sharded restore;
- P5/P7 target-size-result consumption: zero DATA4 restore unless the stage independently needs DATA4 for its own science.

No downstream command loads DATA4 solely because a helper reconstructs P1/P2 objects from it.

### 2.5 Snapshot currentness replaces live-source reconstruction

For prepared generation `g`, downstream currentness means:

1. CampaignStore identifies the expected current generation/revision;
2. required generation-scoped prepared artifacts exist;
3. their intrinsic integrity/digests equal the identities bound to `g`;
4. downstream P3/P5/P7 evidence binds to those exact identities and generation.

Fresh P1 source authentication remains mandatory when `prepare` creates a new snapshot. Unchanged exact source bytes do not require repeating semantic authentication merely because another command starts.

### 2.6 Re-running prepare

`prepare` is the sole command that may create/advance the prepared snapshot.

Repeated `prepare` first decides reuse from preparation-owned exact input identity using existing identities/receipts, such as:

- manifest identity;
- preparation configuration projection/digest;
- exact source/companion byte identities already authenticated at preparation time;
- existing lower-level artifact identities where authoritative for the same snapshot.

Unchanged bytes/config permit reuse. Changed preparation inputs trigger the required fresh authentication/rebuild and a fresh generation. Do not add a freshness database or use mtimes alone as scientific identity.

### 2.7 Direct EVAL2 separates scientific population from execution minibatches

For each accepted EVAL2 role:

```text
exact immutable role + exact-M evaluation artifact
  -> authenticate one provider/model state
  -> preserve the exact ordered M frames
  -> deterministic contiguous chunks, each size <= optimizer_policy.valid_batch_size
       -> same provider.predict_batch(chunk)
       -> materialize predictions to host representation
  -> concatenate in exact role order
  -> require exactly M predictions
  -> compute one prediction-evidence digest / reduce exactly as before
```

The production semantic owner remains `run_target_size_direct_boundary_inference(...)` or an equivalent final owner if implementation legitimately refactors it. The chunking decision must execute **inside that real owner or below it without bypassing its state/role/evaluation validation**.

For this cycle, `optimizer_policy.valid_batch_size` is the existing canonical EVAL2 batch-width bound. Do not add `target_size_eval_batch_size`, a second resource policy, or an auto-tuned scientific identity merely to repair this defect.

The same authenticated provider instance is reused across chunks. Provider/state authentication occurs once per direct-EVAL2 role, not once per chunk.

The forward test seam remains below the chunking/resource owner: a fake may replace the expensive numerical forward for each chunk, but a test fake may not receive the whole M-frame population and thereby bypass the production chunk orchestration it claims to test.

### 2.8 OOM behavior is fail-closed, not hidden policy mutation

The ordinary corrected path should fit because its batch width is already bounded by accepted `valid_batch_size`.

If one configured batch still OOMs, do not silently change scientific `M`, device, dtype, observables, checkpoint/model state, or execution-context policy. Surface a clear resource failure naming the configured EVAL2 batch width and the need for an explicit compatible policy/configuration change.

A hidden adaptive OOM-halving loop is not required for this repair and must not be added merely to preserve an oversized configured batch. If implementation proposes adaptive backoff, it must first prove that batch grouping cannot alter accepted numerical/evidence identity and that the backoff is represented consistently in execution provenance; otherwise bounded deterministic batching is the accepted simpler design.

---

## 3. Required simplification / repair of current implementation

### 3.1 Split prepare builder from prepared loader

Replace the current single semantic role of `build_current_target_size_authorities(...)` with:

1. a **prepare builder** that constructs a new prepared substrate and performs fresh P1 authentication; and
2. a **prepared-generation loader** that loads/validates the immutable substrate already bound to the current generation.

Exact names are delegated. The old function may be narrowed, renamed, split, or removed. A downstream loader never invokes the prepare builder as fallback.

### 3.2 Stop DATA4 write/read bounce inside prepare

When `_prepare_catalog(...)` has just produced DATA4 and normalized frame data in the same invocation, flow those validated objects directly into the prepare builder where practical. Do not persist DATA4 and immediately restore it solely because a helper API only accepts CampaignStore lookup.

Warm/reused prepare loads the prepared generation rather than restoring DATA4 and rebuilding P1/P2/P3 merely to rediscover equal digests.

### 3.3 Select-target-size becomes consumption-only upstream of P3 execution

`build_screen_context(...)` loads the exact prepared generation and does not invoke the prepare builder.

Screen initialization uses that generation's exact aggregate/common/frame authority/split exclusion/frame catalog/normalized frame payload. Changed preparation creates a fresh generation/root rather than attempting to republish a changed immutable `screen.json` under the old root.

### 3.4 Terminal/current-result exposure uses prepared state

Replace terminal live-source P1/P2/P3 reconstruction with prepared-generation loading while preserving strict P3 immutable-evidence validation:

```text
CampaignStore current terminal revision
  -> load exact prepared generation
  -> verify prepared component integrity/digests
  -> derive only cheap P3 execution context as needed
  -> resolve real P3 execution root
  -> authenticate adopted head + reducer
  -> rederive terminal projection / selected membership
  -> compare persisted projection
```

Update terminal result documentation/tests to prove current prepared-generation identity, not repeated live-source reconstruction.

### 3.5 Direct EVAL2 must not call `predict_batch` on the full role population

Current code effectively does:

```text
atoms_list = parse_exact_M_artifact(...)
raw_predictions = provider.predict_batch(atoms_list)
```

Replace this with ordered bounded execution. Suggested realization:

```text
batch_width = optimizer_policy.valid_batch_size
predictions = []
for start in range(0, len(atoms_list), batch_width):
    chunk = atoms_list[start:start + batch_width]
    predictions.extend(forward(provider, chunk))
require len(predictions) == M
```

This pseudocode is not a frozen helper/API shape. The required semantics are:

- exact ordered contiguous partition;
- every chunk size `<= valid_batch_size`;
- same authenticated provider state for all chunks;
- no missing/duplicate/reordered frames;
- predictions concatenated before existing evidence/reduction;
- no full-M native provider batch.

Do not pass a generator into a provider API that materializes it back into one full batch. The memory bound must exist at the device-batch owner.

### 3.6 Do not “fix” the OOM by weakening EVAL2

Forbidden as the primary repair:

- lowering M1/M2/M3 or otherwise changing evaluation membership;
- reducing target-size candidate population or fidelity policy;
- setting `compute_stress=False`, dropping forces, or changing accepted metrics;
- switching CUDA to CPU after OOM;
- changing float precision or acceleration backend for memory reasons;
- `torch.cuda.empty_cache()` between a still-oversized full-M attempt;
- relying on `PYTORCH_CUDA_ALLOC_CONF`/allocator fragmentation tuning;
- catching OOM and retrying the same full-M batch;
- adding a second EVAL2 batch-size configuration when `valid_batch_size` already owns the accepted bound;
- constructing one full CPU graph batch and only slicing after transfer/build; chunk before native graph/device materialization.

### 3.7 Close the bounded sibling family, not only this call site

Inspect direct MACE evaluation consumers that accept an ordered scientific population and call `provider.predict_batch(...)` on the entire list. At minimum inspect:

- target-size direct EVAL2;
- post-selection direct evaluation/current P5 execution if the current candidate retains the same full-list call;
- any shared authenticated checkpoint/provider evaluation seam used by those paths.

If more than one production consumer needs the same ordered bounded inference operation, implementation may extract **one small canonical helper** that replaces duplication. Do not import DATA6's restart/journal/runtime-batch state machine wholesale into P3/P5. Reuse only a genuinely compatible minimal primitive if one already exists.

This census is bounded to direct authenticated MACE evaluation. It does not authorize a general inference-framework redesign.

---

## 4. Persistence/publication contract

### 4.1 Minimum sufficient prepared state

Persist the smallest set of generation-scoped prepared objects needed to restart P3 without preparation reconstruction. Prefer existing typed serialization and CampaignStore/content-addressed primitives. Avoid a parallel object store.

### 4.2 Publish before adopt

Use the existing immutable publish-before-adopt pattern:

```text
build/validate prepared components
  -> publish immutable generation-scoped components
  -> verify component identities
  -> CAS CampaignStore generation/revision to bind those identities
```

If interrupted before adoption, published residue is not current. If CampaignStore identifies a current generation, all required prepared components must exist and validate. Never overwrite an adopted generation component with different bytes.

### 4.3 Existing generations without prepared artifacts

Do not reconstruct missing prepared objects from live sources and retroactively attach them to an already existing generation.

An old-format current generation lacking required prepared state is incompatible with repaired downstream reuse. `select-target-size` refuses it with actionable guidance to run `prepare`. One explicit `prepare` creates/binds a fresh generation under the repaired contract. Historical immutable evidence remains historical under its old generation/root.

### 4.4 No duplicate authority/currentness state

Forbidden:

- second generation counter;
- authoritative prepared-state `latest` pointer beside CampaignStore;
- independent freshness registry;
- `trust_prepared`, `skip_validation`, `fast`, or `reuse_anyway` bypass;
- downstream prepared-load failure falling back to live-source reconstruction;
- mutable overwrite of generation-scoped prepared scientific records.

---

## 5. Implementation obligations

### P4-STAGE-A — establish prepared-generation persistence owner

**Concern.** A stage cannot be reusable when downstream-required objects are discarded after only digests are persisted.

**Required end state.** `prepare` publishes enough immutable generation-scoped state to restart P3 without reconstructing P1/P2/P3-common.

**Delegated solution space.** Existing typed records, externalized CampaignStore records, generation-scoped content-addressed files, or one compact canonical manifest over those objects. Prefer the smallest representation and fewest owners.

**Acceptance.** A fresh process after `prepare` can load complete downstream-required prepared state with identities equal to CampaignStore-bound identities and with zero DATA4/P1/P2 rebuild.

### P4-STAGE-B — make prepare sole creation owner

**Concern.** Cold prepare can write then immediately reread DATA4; repeated prepare can rebuild the whole graph merely to rediscover equality.

**Required end state.** Newly built lower-level objects flow directly into the prepare builder when already available. Repeated prepare reuses current prepared state when preparation-owned input identity is unchanged and creates a fresh generation when required inputs change.

**Acceptance.** Cold prepare has no immediate DATA4 sharded restore solely for P1/P2 continuation. Unchanged repeated prepare does not rebuild P1/P2/P3-common.

### P4-STAGE-C — cut select-target-size to prepared consumption

**Concern.** `build_screen_context()` currently re-enters preparation.

**Required end state.** Selection loads/validates the prepared generation, constructs only P3-owned runtime state, and runs/resumes the screen.

**Acceptance boundary.** Execute the real `execute_current_select_target_size -> build_screen_context -> initialize/reconcile screen` production path. Expensive TRAIN2/numerical inference may be replaced below the P3 semantic owners; the prepared loader itself may not be patched to return desired state.

**Acceptance.** Ordinary start/resume after successful prepare has zero DATA4 restore and zero prepare-only builders listed in §6.1.

### P4-STAGE-D — cut terminal/current exposure to prepared generation

**Concern.** Current terminal loading reconstructs P1/P2/P3 from source inputs.

**Required end state.** Current terminal exposure authenticates CampaignStore currentness, prepared-generation integrity, P3 head/reducer evidence, and terminal projection without preparation reconstruction.

**Acceptance boundary.** Exercise real public/current terminal loader/writer/reporter and P5-facing current-result seam.

**Acceptance.** Repeated current terminal load/write/report performs no DATA4 restore, live P1 authentication, or P1/P2/common rebuild while stale revision, corrupt prepared state, corrupt P3 evidence, and projection mismatch still fail closed.

### P4-STAGE-E — make direct EVAL2 resource-safe without scientific change

**Concern.** The real direct-EVAL2 owner authenticates an exact-M artifact but then submits all M frames to one native MACE batch, causing CUDA OOM on the supplied production workload.

**Required end state.** The exact-M role is evaluated in deterministic ordered device batches bounded by the accepted candidate `optimizer_policy.valid_batch_size`. The same authenticated provider/model state is reused for all chunks. Existing prediction evidence and EVAL2 reduction consume the concatenated exact-order predictions exactly as before.

**Acceptance boundary.** Execute the real `run_target_size_direct_boundary_inference(...)` owner, including role/evaluation/checkpoint/provider authentication and its chunk orchestration. A test fake may replace the expensive numerical forward **per chunk** but may not replace the chunking owner or receive the whole M-frame list.

**Acceptance.** For `M > valid_batch_size`, observed provider calls are all `<= valid_batch_size`, cover every frame exactly once in original order, produce exactly M predictions, and never submit one full-M native batch. Real GPU smoke on representative MACE/LTA-like geometry succeeds without OOM.

### P4-STAGE-F — close direct-inference sibling variants

**Concern.** The same full-list `provider.predict_batch(atoms_list)` pattern exists or may exist in post-selection/direct-evaluation consumers; fixing one call site would leave the same failure class downstream.

**Required end state.** All current production direct MACE evaluation consumers in the bounded target-size/post-selection family obey the same ordered bounded-batch memory contract or use one minimal canonical helper.

**Delegated solution space.** Small shared helper if it replaces duplicate orchestration; otherwise equivalent local use of an existing compatible primitive. No new batching policy class/database/state machine.

**Acceptance.** Bounded caller census shows no affected production direct-evaluation path that submits an entire scientific evaluation population to a native MACE batch when it exceeds its accepted batch bound.

### P4-STAGE-G — reconcile storage lifetime and obsolete doctrine

**Concern.** Stage separation fails if cleanup removes normalized frame data while active consumers still need it; documentation/tests also encode reconstruction as currentness doctrine.

**Required end state.** Owner-driven retention preserves exactly the hot representation required by active/current consumers. Documentation distinguishes CampaignStore current authority, immutable prepared scientific state, prepare-time live-source authentication, downstream prepared-artifact integrity, and P3 immutable-evidence authentication.

**Acceptance.** Safe cleanup cannot force hidden DATA4/P1 reconstruction for a valid active generation. Tests/docs no longer require downstream reconstruction merely because the old implementation did it.

---

## 6. Task-specific acceptance

### 6.1 Zero preparation reconstruction downstream

After one successful `prepare`, instrument the real production path. Normal `select-target-size` start/resume must make **zero** calls to preparation-only operations semantically equivalent to:

```text
read_data4_sharded_record(...)
build_source_authority_from_data2_catalog(...)
authenticate_vasp_source_authority(...)
build_canonical_frame_authority(...)
build_neutral_feature_evidence_from_data4_bundle(...)
build_neutral_statistical_base(...)
build_neutral_split_exclusion_evidence(...)
build_target_size_statistical_aggregate(...)
build_target_size_common_preparation(...)
read_vasp_frames(...)
```

If implementation renames/replaces a delegated owner, remap the assertion to the final real prepare-only owner. The semantic claim is zero reconstruction, not preservation of function names.

Apply the same zero-reconstruction claim to current terminal reload/write/report and P5-facing current-result loading.

### 6.2 DATA4 I/O acceptance

Required cases:

1. Cold prepare constructing DATA4: no immediate sharded restore solely to continue preparation while the validated object is already in memory.
2. Warm select after prepare: zero DATA4 restore.
3. Select resume: zero DATA4 restore.
4. Terminal reload/report: zero DATA4 restore.
5. Prepared-state corruption: fail closed; no DATA4 auto-repair fallback.

Record DATA4 restore count in bounded integration evidence.

### 6.3 Prepared scientific identity equivalence

On a bounded real multi-run corpus, compare pre-repair construction with the published prepared generation. Require exact equality of still-binding scientific identities including:

- frame authority;
- neutral statistical base;
- split exclusion;
- target-size policy;
- experiment definition;
- aggregate;
- common preparation;
- P3 execution context for the same downstream configuration;
- initial screen window/schedule identity.

Persistence/load round-trip preserves these identities exactly.

### 6.4 Snapshot mutation semantics

Regression:

```text
prepare -> g1
mutate one live source/control/companion file
select-target-size g1
```

Selection continues to consume exact g1 prepared state and does not reinterpret it from the changed source tree.

Then run `prepare` again. It detects the preparation-owned input identity change, performs required fresh authentication/rebuild, and advances to fresh `g2` before a g2 screen opens.

### 6.5 Existing-generation compatibility

For an old current generation with CampaignStore digests but no repaired prepared artifacts:

- `select-target-size` refuses with explicit `prepare` guidance;
- no live-source reconstruction retrofits the old generation;
- explicit `prepare` binds a fresh complete generation;
- old immutable execution evidence remains historical;
- new screen uses the new generation root;
- no immutable `screen.json` overwrite/collision occurs.

### 6.6 Corruption/partial publication

Test at least:

- missing prepared component;
- corrupt prepared component;
- digest mismatch;
- published component followed by crash before CampaignStore adoption;
- current revision pointing to incomplete/corrupt prepared state;
- stale historical prepared generation cannot become current through a convenience alias.

No case falls back to upstream reconstruction.

### 6.7 Currentness negatives remain closed

Preserve failure for:

- stale expected CampaignStore revision;
- changed generation;
- wrong execution-context digest;
- missing/corrupt P3 root evidence;
- adopted head mismatch;
- reducer mismatch;
- terminal projection mismatch;
- stale current-result publication attempts already covered by P4-E4.

### 6.8 Direct-EVAL2 bounded-batch unit/property acceptance

Use a deterministic provider fake **below** the real direct-inference owner. For representative cases including `M=1`, `M=batch`, `M=batch+1`, and multiple batches:

- every forward call has `1 <= len(chunk) <= optimizer_policy.valid_batch_size`;
- concatenated observed frame identities equal the exact role order with no loss/duplication/reordering;
- exactly M prediction entries are returned;
- reference per-frame or bounded-batch predictions and chunked predictions produce the accepted same numerical result under the project's required tolerance/exactness contract;
- prediction-evidence role/model/evaluation ancestry is unchanged;
- reduction/M1/M2/M3 outcome is unchanged for identical predictions.

The fake must record chunk widths so a test cannot pass if chunking is never exercised.

### 6.9 Direct-EVAL2 real-provider integration

Exercise one real authenticated MACE provider/checkpoint through the production direct-EVAL2 owner with an evaluation population larger than `valid_batch_size`.

Required evidence:

- provider/model authentication executes once for the role;
- more than one bounded forward occurs when `M > valid_batch_size`;
- no full-M native batch is materialized;
- output count/order and evidence validation pass;
- device/dtype/forces/stress semantics remain unchanged.

A reduced scientific fixture is acceptable if it crosses the real provider/state/chunk owner.

### 6.10 GPU resource regression for the supplied failure class

Because the blocker is CUDA VRAM, run a real CUDA smoke on representative target hardware when available. Prefer the same MACE architecture/dtype and LTA-like cell size as the failing run; full long TRAIN2 is unnecessary because the acceptance claim is direct inference.

Record:

- GPU/device identity and total/free memory before evaluation;
- configured `valid_batch_size`;
- maximum observed chunk width;
- peak allocated/reserved VRAM when practical;
- success/failure.

The corrected path must complete without OOM for the representative workload with the accepted batch bound. If the exact previously failing boundary artifact is readily available, rerun it as strong qualification evidence; this is valuable but does not replace regression/integration tests.

Do not accept allocator tuning as substitute evidence.

### 6.11 Sibling direct-inference census

Use semantic caller/reference inspection plus focused structural search where available. Verify affected current production direct-evaluation paths do not retain the semantic pattern:

```text
scientific evaluation population -> one provider.predict_batch(full_population)
```

At minimum inspect target-size EVAL2 and current post-selection direct evaluation. Validate any structural query against a known positive/negative example before treating zero findings as acceptance evidence.

### 6.12 Structural ownership/absence

After implementation verify:

1. one prepare-only scientific substrate builder path;
2. one canonical current prepared-generation loader/owner;
3. selection/terminal/P5 current-result consumers do not call the prepare builder;
4. no second DATA4/frame cache or freshness/currentness registry;
5. no downstream fallback to live-source P1 reconstruction;
6. CampaignStore remains sole current generation/revision authority;
7. generation-scoped prepared artifacts are immutable after adoption;
8. direct EVAL2 cannot bypass its bounded batch owner on the production provider path;
9. no new EVAL2 batch-size policy duplicates `MaceOptimizerPolicy.valid_batch_size`.

### 6.13 Performance/resource evidence

No universal speedup percentage is required. Measure bounded before/after startup for:

- unchanged repeated prepare;
- first select after prepare;
- select resume;
- terminal reload/report.

Record at minimum wall time, DATA4 restore count, source-frame read count, P1 authentication count, preparation-builder invocation count, and bytes read/peak RSS when practical.

For direct EVAL2 record maximum chunk width and peak VRAM when practical. Structural elimination of full-M device batching is mandatory even if a tiny fixture does not OOM.

---

## 7. Expected affected surface

### Runtime/orchestration

- `mdstats/training_data/campaign_target_size_runtime.py`
  - `CurrentTargetSizeAuthorities`
  - `build_current_target_size_authorities`
  - `execute_current_prepare`
  - `build_screen_context`
  - `execute_current_select_target_size`
  - `_execute_candidate_cell` only as needed to preserve the real EVAL2 owner boundary
- `mdstats/training_data/campaign_target_size_cutover.py`
  - generation binding/adoption/publication ordering
- `mdstats/training_data/campaign_target_size_state.py`
  - only if prepared binding truly needs a field; avoid schema growth when existing digests/generation ownership suffice
- `mdstats/training_data/campaign_target_size_terminal.py`
  - `ValidatedTargetSizeTerminalResult`
  - `load_validated_target_size_terminal_result`
- `mdstats/training_data/campaign_target_size_view.py`
  - current exposure consumers if loader contract changes
- `mdstats/training_data/_campaign_cli_core.py`
  - `_prepare_catalog`
  - prepared-component serialization/load path
  - preparation input reuse checks
- `mdstats/training_data/frame_cache.py`
  - only if retention ownership requires adjustment

### Direct inference / model execution

- `mdstats/training_data/target_size_execution/evaluation.py`
  - `run_target_size_direct_boundary_inference`
  - exact-M byte validation/parse must remain intact
  - ordered bounded forward orchestration
- `mdstats/training_data/model_features.py`
  - `MaceCalculatorProvider.predict_batch` only if a smaller canonical batching seam is required; do not move policy ownership here unless justified
- `mdstats/training_data/protocol.py`
  - normally no schema change; existing `valid_batch_size` is the accepted bound
- `mdstats/training_data/target_size_execution/context.py`
  - normally no schema change; verify existing optimizer-policy identity already binds the batch parameter
- `mdstats/training_data/post_selection_execution.py`
  - inspect direct full-list inference sibling and repair only if present in current candidate
- shared authenticated provider/checkpoint owner only if a minimal common ordered-batch helper belongs there cleanly

### Scientific objects

Only P1/P2/P3 serialization boundaries required for lossless prepared-state round-trip. Do not change scientific definitions.

### Tests

At minimum rederive impact over:

- P1 neutral/canonical authority tests;
- DATA4 sharded persistence/restore tests;
- frame-cache integrity/lifetime tests;
- P4 state/cutover/runtime/terminal/integration suites;
- P3 direct EVAL2 authentication/evidence/reducer tests;
- P3 execution/restart/immutable publication suites;
- target-size MACE real-provider integration tests;
- P5 current-result consumer and direct-evaluation tests if sibling batching is affected;
- resource/parallelism tests, including existing adaptive-batching tests only as reference rather than authority;
- storage retention tests affected by artifact classification;
- post-DATA4 authority-reconstruction I/O tests, whose ownership expectation changes from fast downstream reconstruction to reconstruction only in prepare.

Final affected surface must be re-derived from the assembled implementation.

---

## 8. Implementation sequence

### Stage 1 — persist/load one prepared generation

Implement generation-scoped prepared-state publication and canonical loading first.

Stage-local closure:

- scientific digest equivalence;
- publish/load round-trip;
- missing/corrupt/partial publication negatives;
- no second currentness authority.

### Stage 2 — make prepare reuse and remove DATA4 bounce

Route newly created DATA4/frame payload directly into the builder and support unchanged-prepare reuse through existing exact input identity.

Stage-local closure:

- no immediate DATA4 read-back solely for continuation;
- repeated unchanged prepare does not rebuild P1/P2/P3-common;
- changed preparation input creates fresh generation.

### Stage 3 — cut selection startup to prepared consumption

Remove prepare-builder invocation from selection startup and consume the current prepared generation.

Stage-local closure:

- zero DATA4/P1/P2/P3 reconstruction on start/resume;
- same aggregate/context/screen identities;
- old-generation-without-snapshot rejection;
- immutable-screen collision closes through fresh generation ownership.

### Stage 4 — repair direct EVAL2 memory ownership

Keep exact-M artifact/state authentication, then introduce deterministic ordered bounded batching using the accepted `valid_batch_size` before native graph/device materialization. Close the bounded post-selection sibling if present.

Stage-local closure:

- chunk-owner focused tests including non-divisible M;
- real production owner with per-chunk fake forward;
- real MACE provider integration;
- CUDA smoke on representative geometry/hardware when available;
- no scientific/evidence identity drift;
- no new batching policy/state machine.

### Stage 5 — cut terminal/current-result and downstream consumers

Replace terminal live-source reconstruction with prepared loading while preserving P3/currentness validation.

Stage-local closure:

- zero upstream reconstruction on current terminal load/write/report;
- stale/currentness/corruption negatives remain closed;
- P5-facing current-result seam uses same prepared generation.

### Stage 6 — reconcile retention and final assembled acceptance

Update storage retention only as necessary, rederive final affected surface, run complete affected regression/integration, and record bounded startup/I/O/VRAM evidence.

---

## 9. Simplification triggers and forbidden repair patterns

The stage-boundary defect already triggered simplification: repeated reconstruction led to performance machinery to make unnecessary repetition cheaper. The EVAL2 OOM is likewise caused by a simple ownership conflation—scientific population size was passed directly to a resource-level batch API. Repair the cause rather than layering workarounds around it.

Prefer:

```text
one prepare builder
+ one immutable prepared generation
+ one prepared loader
+ one CampaignStore current authority
+ one bounded direct-inference batch contract
```

not:

```text
rebuild upstream science in every command
+ caches/freshness switches around rebuilds
+ full-M GPU batches
+ OOM retries / allocator flags / CPU fallbacks
+ duplicate batch-size configuration
```

Forbidden closure patterns include:

- retaining downstream reconstruction and merely making it faster;
- in-process memoization as the cross-command fix;
- second prepared/frame cache;
- trust/skip-auth/fast bypass flags;
- accepting DATA4 restore because it is faster than recomputation;
- auto-rebuilding missing prepared state inside select/terminal;
- binding fresh reconstruction to old immutable generation evidence;
- weakening immutable screen publication;
- copying P1 authentication into a second verifier;
- mtime-only scientific identity;
- result-view/prepared alias authoritative over CampaignStore;
- lowering scientific M to fit VRAM;
- changing required EVAL2 observables/precision/device to fit VRAM;
- allocator tuning or `empty_cache()` as the main OOM fix;
- hidden retry of a full-M native batch;
- a new EVAL2 resource-policy object when existing `valid_batch_size` is sufficient;
- importing DATA6 restart/adaptive-batching machinery wholesale into P3.

If implementation finds multiple tiny copies of ordered bounded direct inference, consolidate them only when one small canonical helper genuinely reduces total complexity. Do not generalize beyond the bounded family.

---

## 10. Implementation authority

### Frozen

- V7 P1/P2/P3 scientific model and identities.
- `prepare` is sole creation/advance boundary for target-size prepared scientific state.
- Successful prepare defines one immutable generation-scoped prepared snapshot.
- selection/resume/terminal/current downstream consumers load that snapshot rather than reconstruct it from live upstream inputs.
- CampaignStore remains sole current generation/revision/lifecycle authority.
- live source mutation affects a future prepare/generation, not an already prepared generation.
- missing/corrupt prepared state fails closed without downstream reconstruction fallback.
- no DATA4 restore solely for ordinary downstream currentness/reconstruction.
- immutable P3 evidence and generation-root identity remain strict.
- existing normalized frame representation is reused; no second frame cache.
- scientific EVAL2 population `M` remains exact and unchanged.
- direct EVAL2 device execution is partitioned deterministically before native batch/device materialization, with each chunk bounded by the accepted `optimizer_policy.valid_batch_size`.
- the same authenticated provider/model state evaluates every chunk of one role.
- exact role order/count, required observables, dtype/device/model-state, evidence, metrics, and reducer semantics are preserved.
- no hidden scientific-policy mutation or allocator workaround substitutes for bounded batching.

### Delegated

- exact prepared snapshot class/record names and serialization layout;
- individual prepared records versus compact manifest;
- private helper factoring and function names;
- whether `CurrentTargetSizeAuthorities` is renamed/split/removed;
- exact source-byte-currentness implementation using existing exact identities/receipts;
- exact storage classification name;
- whether ordered bounded direct inference is implemented directly in each final owner or through one minimal shared helper, provided there is no duplicate policy/state authority;
- progress/diagnostic wording for chunked EVAL2;
- optional non-authoritative resource telemetry.

### Reopen only on evidence

Reopen only the affected surface if evidence proves:

1. a downstream scientific consumer genuinely requires DATA4 content itself;
2. a required prepared object cannot be persisted/reloaded losslessly within acceptable resource bounds and no simpler representation exists;
3. retaining normalized frame payload violates a demonstrated storage budget and another direct prepared representation is necessary;
4. a governed compatibility contract requires live-source reinterpretation between prepare and select rather than snapshot semantics;
5. the accepted `optimizer_policy.valid_batch_size` cannot safely bound direct EVAL2 on supported target hardware even at 1, in which case the device/model workload itself exceeds the supported hardware envelope;
6. deterministic batching at the accepted bound is demonstrated to alter a governed scientific result beyond accepted numerical tolerance, requiring a bounded reconsideration of execution-identity/numerical policy.

Do not reopen target-size science merely because a more elaborate batching/autotuning framework could be built.

---

## 11. Closure criteria

This amendment closes only when one assembled candidate satisfies all of the following:

- `prepare` owns expensive preparation creation and publishes restartable prepared state;
- cold prepare does not immediately restore newly created DATA4 solely because of an internal API boundary;
- unchanged repeated prepare reuses prepared state without rebuilding P1/P2/P3-common;
- select start/resume performs zero DATA4 restore and zero preparation reconstruction;
- terminal current load/write/report performs zero DATA4 restore and zero preparation reconstruction;
- downstream P5/current-result consumers use the same current prepared generation;
- prepared-load corruption fails closed without live-source fallback;
- source mutation after prepare cannot mutate/reinterpret an in-progress generation;
- subsequent prepare detects changed preparation inputs and advances generation;
- old generations lacking prepared artifacts require explicit fresh prepare rather than retroactive reconstruction;
- immutable old screen evidence is never overwritten under changed preparation identity;
- prepared scientific digests match accepted construction;
- direct target-size EVAL2 never submits a scientific population larger than `valid_batch_size` as one native MACE batch;
- exact-M membership/order/model-state/observables/evidence/reduction are preserved across chunking;
- real-provider integration passes and representative CUDA execution no longer reproduces the supplied OOM class;
- bounded sibling direct-inference paths are closed rather than leaving the same full-list pattern downstream;
- final affected regression and real-owner integration pass;
- no second cache/currentness/generation/freshness/batching-policy machinery was introduced.

A system that is scientifically correct but still replays DATA4/P1/P2/P3 across command boundaries is not accepted. A system that avoids replay by weakening currentness is not accepted. A system that keeps exact science but sends the full evaluation population to one derivative-bearing GPU batch is also not accepted. The required end state is one immutable prepared generation, one CampaignStore current authority, downstream consumption without reconstruction, and resource-bounded direct evaluation that preserves the exact scientific experiment.
