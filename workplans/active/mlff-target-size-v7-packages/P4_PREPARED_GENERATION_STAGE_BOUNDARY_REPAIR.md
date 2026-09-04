---
kind: implementation-package-amendment
package_id: CODE-MLFF-TARGET-SIZE-V7-P4-PREPARED-GENERATION-STAGE-BOUNDARY-REPAIR
parent_package: P4_ATOMIC_RUNTIME_PERSISTENCE_CUTOVER.md
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
status: active
created_date: 2026-09-04
branch: plan/mlff-storage-io-reset-r37-review-closure
branch_baseline: 4d61cd1f5ba0356a5746d5c45254430db5188595
scope: bounded-P4-stage-ownership-persistence-currentness-and-I/O-simplification
compatibility_policy: destructive-current-generation-rebind-no-scientific-change
design_reopen: P4-D prepare/select/terminal prepared-state ownership only
---

# P4 prepared-generation stage-boundary repair

## 0. Verdict and reason for reopening P4-D

**NO-PASS until this amendment closes.**

The current runtime violates the intended stage ownership of the V7 lifecycle. `prepare` constructs the expensive target-size scientific substrate, but the implementation persists only selected digests and then makes later commands reconstruct the same upstream scientific graph again. The result is repeated O(dataset) work and repeated large-artifact I/O across command boundaries.

The present call graph is materially:

```text
prepare
  -> _prepare_catalog(...) when needed
       -> DATA2/DATA3/DATA4/DATA5 construction and persistence
  -> build_current_target_size_authorities(...)
       -> restore DATA4 from CampaignStore
       -> rebuild P1 source authority
       -> fresh P1 source authentication
       -> restore/rebuild normalized frame payload
       -> rebuild canonical frame authority
       -> rebuild neutral statistical substrate
       -> rebuild P2 target-size aggregate
       -> rebuild P3 common preparation
  -> persist only target-size generation identities/digests

select-target-size
  -> build_screen_context(...)
       -> build_current_target_size_authorities(...) AGAIN
            -> restore DATA4 AGAIN
            -> rebuild P1/P2/P3-common AGAIN
  -> run/resume P3 screen

terminal result exposure / replay / downstream P5 consumption
  -> load_validated_target_size_terminal_result(...)
       -> build_current_target_size_authorities(...) AGAIN
            -> restore DATA4 AGAIN
            -> rebuild P1/P2/P3-common AGAIN
       -> validate P3 head/reducer/terminal projection
```

`CampaignStore.get_record("data4", Data4FeatureBundle)` is not a cheap pointer lookup. It restores and verifies the sharded DATA4 artifact. Therefore every downstream call to `build_current_target_size_authorities(...)` can replay the full DATA4 restore path even though DATA4 is already a completed prepare-owned artifact.

The recently implemented post-DATA4 performance repair remains useful inside the **prepare builder**: it removed redundant direct VASP frame rereads, split fresh P1 authentication from frame payload acquisition, reused the existing normalized frame cache, and restored bounded canonical-frame parallelism. However, it optimized an upstream reconstruction that downstream commands should not be performing at all. Further tuning of repeated reconstruction would preserve the wrong lifecycle.

This amendment therefore reopens only the P4-D prepared-state/currentness architecture and the directly dependent terminal/current-exposure validation path. It does **not** reopen target-size science, P1/P2 scientific semantics, P3 screen/reducer semantics, CampaignStore as the sole current-generation authority, STOR ownership, P5 science, or P7 science.

---

## 1. Original problem and product invariants

The stakeholder-visible workflow is staged deliberately:

```text
prepare
  -> construct and freeze the scientific substrate for one target-size generation

select-target-size
  -> consume that frozen substrate and perform the paired-seed configurable-fidelity screen

post-selection / terminal consumers
  -> consume the same frozen generation and its authenticated P3 descendants
```

The product requirement is not merely that all commands eventually derive equal digests. The stage boundary must make expensive completed preparation reusable and restartable.

### 1.1 Frozen scientific invariants

The following remain unchanged:

1. The V7 target-size scientific question and one-dimensional `N` experiment.
2. Exact P1 source/canonical-frame semantics, including the accepted source/control/ensemble/energy authentication facts.
3. Exact neutral statistical substrate and split-exclusion semantics.
4. Exact P2 target-size policy, experiment definition, training order, aggregate, and reducer initialization semantics.
5. Exactly one deterministic P3 common preparation per target-size generation.
6. Exact paired optimizer-seed, fidelity-boundary, M1/M2/M3, TRAIN2/EVAL2, continuation, immutable evidence, reducer, and selected-`N/T` semantics.
7. Worker count, cache representation, persistence representation, and command restarts must not change scientific identities.
8. CampaignStore remains the sole current generation/revision/lifecycle authority.
9. Immutable P3 execution evidence remains generation-bound and is never rewritten to make a changed scientific identity fit an old generation.

### 1.2 Stage and operational invariants

The repaired product must additionally satisfy the stage semantics already implied by the V7 lifecycle:

1. A successful `prepare` freezes one immutable prepared scientific snapshot for canonical generation `g`.
2. `select-target-size` **must not recompute or reinterpret the upstream prepared substrate** for `g`.
3. `select-target-size` must not restore DATA4 merely to recreate P1/P2/P3-common objects that `prepare` already completed.
4. Resume/reload/report paths must not repeat O(dataset) preparation work merely to prove that the same generation is still the same generation.
5. The prepared generation is a snapshot. Live source-file edits after successful `prepare` do not silently mutate or reinterpret that already-prepared generation.
6. A later `prepare` is the boundary that may detect changed preparation-owned inputs and advance to a fresh generation.
7. Corrupt/missing prepared-generation artifacts fail closed with actionable `prepare` repair/rebuild guidance. Downstream commands do not silently fall back to rebuilding P1/P2/P3 from live sources.
8. Existing immutable screen evidence remains associated with the exact prepared generation that created it. A changed preparation must advance generation/root instead of trying to republish a different `screen.json` under the old generation.
9. Warm command startup must be bounded by the data that command actually consumes. It must not scale with DATA4 size or P1/P2 reconstruction cost when no preparation change is being requested.

### 1.3 Non-goals

This repair does not:

- change target-size scientific policy or candidate/fidelity/seed semantics;
- weaken P1 authentication during creation of a new prepared generation;
- introduce a second scientific authority beside CampaignStore + the generation-bound prepared artifacts;
- migrate or reinterpret retired pre-V7 derived state;
- add a general cache database, freshness registry, generation registry, or workflow engine;
- make a result-view file authoritative;
- require long GPU training or full production qualification;
- optimize unrelated P5/P6/P7 numerical kernels.

---

## 2. Frozen high-level architecture

### 2.1 Creation and consumption are different ownership operations

For this repair the following high-level ownership is Frozen:

```text
                         PREPARE OWNS CREATION

live source inputs
  -> DATA2/DATA3/DATA4/DATA5 and normalized frame payload
  -> fresh P1 authentication
  -> canonical frame authority
  -> neutral statistical substrate + split exclusion
  -> P2 target-size aggregate/definition
  -> one P3 common preparation
  -> publish immutable prepared-generation artifacts
  -> CampaignStore CAS binds/advances canonical generation

                         DOWNSTREAM OWNS CONSUMPTION

CampaignStore current generation
  -> load exact prepared-generation artifacts for that generation
  -> verify persisted component identity/integrity against CampaignStore
  -> select-target-size / resume
  -> terminal validation/report/current result exposure
  -> P5/P7 consumers as applicable
```

A downstream consumer may authenticate the **prepared artifact it is loading** and the current CampaignStore revision. It must not prove currentness by reconstructing the entire upstream scientific graph from live source data.

### 2.2 Prepared generation is immutable and generation-scoped

Prepared scientific state required by downstream P3 must be persisted under immutable generation-scoped ownership. Mutable generic aliases may exist only as convenience pointers if they are never scientific authority.

The current realization already persists the generation plus the important scientific digests:

- frame authority;
- neutral statistical base;
- split exclusion;
- target-size policy;
- experiment definition;
- aggregate;
- common preparation.

The repaired implementation must persist enough corresponding prepared objects to let downstream consumers load the exact objects whose identities are already bound to CampaignStore, rather than reconstructing them.

The exact class names and record layout are delegated, but the minimal consumer-facing prepared state should be preferred. Do **not** persist every intermediate merely because it exists in memory.

At minimum, downstream P3 currently needs the semantic equivalents of:

- canonical frame authority;
- split-exclusion/correlation evidence required by P3;
- target-size aggregate/definition/reducer initial state;
- common preparation;
- frame catalog;
- normalized frame payload / frame array access needed for materialization/evaluation.

Persist neutral/source/feature intermediates only when a real downstream consumer needs them or when one compact persisted representation demonstrably reduces total machinery. DATA4 itself remains a lower-level durable preparation artifact but is not a normal P3 startup dependency.

### 2.3 Existing frame payload representation is reused, not reinvented

The existing authenticated normalized frame cache is the canonical hot representation for normalized frame payload. Do not add a second frame cache.

For an active prepared generation whose P3/P5/P7 consumers still require normalized frame payload, retention follows actual owner demand. It must not be deleted merely because `prepare` returned. The existing storage reset already treats this cache as a current mmap-oriented representation whose lifetime follows current consumers rather than `after_prepare` folklore.

If the implementation chooses to keep the frame payload formally classified as a reusable cache, eviction while an active downstream consumer still requires it must not trigger hidden upstream reconstruction inside `select-target-size`. Either retention prevents such eviction during the required lifetime or the owning prepared-generation representation must provide an equivalent direct restore. Prefer retention over another representation unless measured storage pressure proves a second representation is necessary.

### 2.4 DATA4 is prepare-owned cold evidence after preparation

DATA4 may remain durable for reproducibility, later explicit re-preparation, auditing, or other real consumers. That does not make it a mandatory dependency of every target-size command.

After successful preparation:

- `select-target-size` ordinary start/resume: **no DATA4 sharded restore**;
- terminal load/report/current result exposure: **no DATA4 sharded restore**;
- P5/P7 target-size-result consumption: **no DATA4 sharded restore unless those stages independently need DATA4 for their own scientific work**.

No downstream command may load DATA4 solely because an implementation helper happens to rebuild P1/P2 objects from it.

### 2.5 Currentness is snapshot currentness, not live-source reconstruction

For an already prepared generation `g`, currentness means:

1. CampaignStore says `g` is the current canonical generation/revision expected by the caller;
2. the generation-scoped prepared artifacts exist;
3. their intrinsic digests/integrity checks match the identities bound in that CampaignStore generation;
4. downstream P3/P5/P7 evidence binds to those exact identities and generation.

It does **not** mean reparsing live source files and rebuilding P1/P2/P3 before every downstream exposure.

Fresh P1 source authentication remains mandatory when `prepare` creates a new scientific snapshot. Once those exact source bytes and their derived prepared products are frozen into `g`, later mutation of the external source tree does not retroactively alter `g`.

### 2.6 Re-running prepare

`prepare` remains the only command allowed to create/advance the prepared scientific snapshot.

A repeated `prepare` should first determine whether the existing prepared generation remains reusable using preparation-owned input identity, not by unconditionally rebuilding the whole scientific graph.

Use the cheapest existing identities that safely establish this decision, for example:

- approved manifest identity;
- explicit preparation-owned configuration projection/digest;
- exact source/companion byte identities already authenticated at preparation time, using the existing shared SHA/validation-receipt machinery where safe;
- lower-level artifact identities such as source/frame/DATA4 identities where they are already authoritative outputs of the same prepared snapshot.

If exact source bytes and preparation-owned configuration are unchanged, prior semantic authentication of those unchanged bytes remains valid and the prepared generation may be reused without reconstructing P1/P2/P3.

If a preparation-owned source dependency or semantic configuration changes, or the operator explicitly requests the relevant rebuild, `prepare` performs the required fresh P1/DATA4/etc. work and publishes a fresh generation. A byte change may require semantic reparse/re-authentication; unchanged bytes do not.

Do not add an independent freshness database. Reuse existing content identities/hash receipts and the prepared-generation publication contract.

---

## 3. Required simplification of the current implementation

The current design statement in `CurrentTargetSizeAuthorities` — that every member is rebuilt from source inputs and CampaignStore stores only identities — is the mechanism causing the repeated work. It is Tier-2/P4-D machinery and is explicitly reopened by this amendment.

### 3.1 Split builder from loader

Replace the current single semantic role of `build_current_target_size_authorities(...)` with two distinct operations:

1. **prepare builder** — constructs a new prepared substrate from live/lower-level inputs and performs fresh P1 authentication;
2. **prepared-generation loader** — loads the immutable prepared substrate already bound to the current CampaignStore generation and verifies component integrity/digests.

Exact names are delegated. The old function may be renamed, narrowed, split, or removed.

A downstream current loader must never call the prepare builder as a fallback.

### 3.2 Stop the DATA4 write/read bounce inside prepare

When `_prepare_catalog(...)` has just produced DATA4 and the normalized frame payload in the same invocation, the subsequent prepare builder must consume those in-memory outputs directly where practical. It must not persist DATA4 and immediately restore the same sharded record merely because the next helper only knows how to fetch it from CampaignStore.

Refactor the boundary so newly built lower-level outputs can flow forward into the prepare builder in the same invocation. Persistence remains mandatory before stage completion, but persistence should not force an immediate read-back of a large artifact whose validated object is already available.

For a warm/reused prepare, load the existing prepared generation rather than restoring DATA4 and rebuilding P1/P2/P3 merely to discover equal digests.

### 3.3 Remove prepare reconstruction from select-target-size

`build_screen_context(...)` must consume the current prepared-generation loader/result. It must not invoke the prepare builder.

Screen initialization must therefore use the exact `aggregate`, `common`, frame authority, split exclusion, frame catalog, and normalized frame payload belonging to the prepared generation.

This also guarantees that `initialize_target_size_screen(...)` sees the same frozen scientific/preparation identity that `prepare` bound. If preparation changes, the campaign advances to a new generation/root; the implementation must not attempt to republish a different immutable screen descriptor under the old generation.

### 3.4 Remove prepare reconstruction from terminal/current-result exposure

`load_validated_target_size_terminal_result(...)` currently establishes currentness by rebuilding P1/P2/P3 from source inputs. Replace that part of its validation chain with the current prepared-generation loader.

The authoritative terminal-load chain becomes materially:

```text
CampaignStore current terminal revision
  -> load exact prepared generation bound to that revision
  -> verify prepared component digests/integrity
  -> reconstruct only cheap execution context derived from that prepared state/config as needed
  -> resolve real P3 execution root
  -> authenticate adopted immutable head + reducer state
  -> rederive terminal projection / selected membership
  -> compare persisted terminal projection
```

The real P3 head/reducer/terminal validation remains mandatory. What disappears is source/DATA4/P1/P2 reconstruction that has already been frozen by `prepare`.

Update `ValidatedTargetSizeTerminalResult` documentation and tests accordingly. It should prove current prepared-generation identity, not claim that live P1/P2 were reconstructed during every exposure.

### 3.5 Downstream consumers follow the same boundary

Search every caller of the prepare builder/current-authority reconstruction path. Production P5/P7/current-result consumers must load the current prepared generation rather than re-enter preparation.

Tests that directly call the prepare builder to exercise P1/P2 construction remain legitimate prepare/P1 tests. They must not be used as the ordinary downstream production path.

---

## 4. Persistence/publication contract

### 4.1 Minimum sufficient prepared state

Persist the minimum set of generation-scoped prepared objects needed to restart and consume P3 without recomputing preparation.

Prefer existing serializable scientific objects and `CampaignStore`/existing content-addressed storage primitives. Avoid creating a parallel object store.

A small generation manifest/receipt is allowed only if it canonicalizes the component membership and replaces broader duplicated synchronization. It must not become a second current-generation authority; CampaignStore remains the current pointer.

### 4.2 Publish-before-adopt crash safety

Use the repository's existing immutable publish-before-adopt pattern:

```text
build/validate prepared components
  -> publish immutable generation-scoped component records
  -> verify published component identities
  -> CAS CampaignStore generation/revision to bind those identities
```

If interruption occurs before CampaignStore adoption, the published content is not current and may later be recognized as unreachable residue. If the CampaignStore revision is current, every required prepared component must be present and digest-valid.

Do not overwrite an adopted generation's prepared component with different bytes.

### 4.3 Existing generations without prepared artifacts

Do not fabricate prepared objects for an already existing generation by reconstructing from live sources and pretending they were the original snapshot.

A current generation created before this repair that lacks the new minimum prepared-state persistence is incompatible with downstream reuse. Require one explicit `prepare` to create/bind a fresh generation under the repaired contract. Preserve historical immutable evidence under its old generation; do not reinterpret it.

This one-time rebind is the compatibility boundary and also prevents immutable `screen.json` collision caused by trying to run changed preparation under an old execution root.

### 4.4 No duplicate currentness state

Forbidden:

- a second generation counter;
- a prepared-state `latest` record that can disagree with CampaignStore and is treated as authority;
- a freshness registry separate from existing content/hash identities;
- a `trust_prepared`, `skip_validation`, `fast`, or `reuse_anyway` bypass;
- silent fallback from prepared-load failure to live-source reconstruction in downstream commands;
- mutable overwrite of generation-scoped prepared scientific records.

---

## 5. Implementation obligations

### P4-STAGE-A — establish the prepared-generation persistence owner

**Concern.** A stage cannot be reusable when its downstream-required outputs are discarded after only their digests are persisted.

**Required end state.** `prepare` publishes enough immutable generation-scoped prepared state to restart P3 without reconstructing P1/P2/P3-common.

**Delegated solution space.** Reuse existing typed records, externalized CampaignStore records, generation-scoped content-addressed files, or one compact canonical manifest over those objects. Prefer the smallest representation and fewest owners.

**Acceptance.** A fresh process can close `prepare`, destroy all in-memory Python objects, reopen the campaign, and load the complete downstream-required prepared state with identities equal to the CampaignStore-bound digests and with no DATA4/P1/P2 rebuild.

### P4-STAGE-B — make prepare the sole creation owner

**Concern.** Cold prepare currently can build lower-level artifacts and then read them back immediately; repeated prepare can rebuild the whole graph merely to rediscover equality.

**Required end state.** New lower-level objects flow directly into the prepare builder when already available. Repeated prepare reuses the current prepared generation when preparation-owned input identity is unchanged, and creates a fresh generation only when preparation-owned inputs changed or an explicit rebuild requires it.

**Acceptance.** Cold prepare does not immediately perform a DATA4 sharded restore after producing/persisting DATA4 solely for P1/P2 construction. An unchanged repeated prepare does not rebuild P1/P2/P3-common.

### P4-STAGE-C — cut select-target-size over to consumption only

**Concern.** `build_screen_context()` currently re-enters preparation.

**Required end state.** `select-target-size` loads and validates the prepared generation, constructs only P3 execution/runtime state that belongs to selection, and then runs/resumes the screen.

**Acceptance boundary.** The real `execute_current_select_target_size -> build_screen_context -> initialize/reconcile screen` path must execute. Expensive TRAIN2/inference may be replaced below the P3 owner for bounded testing, but the prepared-state loader may not be patched to return a desired object.

**Acceptance.** Ordinary start and resume after successful prepare perform zero DATA4 sharded restores and zero calls to the prepare-only scientific builders listed in §6.1.

### P4-STAGE-D — cut terminal/current exposure over to the same prepared generation

**Concern.** Terminal currentness currently reconstructs P1/P2/P3 from source every time a current result is loaded/reported.

**Required end state.** Current terminal exposure authenticates CampaignStore currentness, exact prepared-generation identity/integrity, P3 immutable head/reducer evidence, and terminal projection without re-entering preparation.

**Acceptance boundary.** Exercise the real public/current terminal loader/writer/reporter and P5-facing current-result seam. Do not replace those owners with a fixture formatter.

**Acceptance.** Repeated current terminal load/write/report performs no DATA4 restore, no live P1 source authentication, and no P1/P2/common rebuild, while stale revision, corrupt prepared component, corrupt immutable P3 evidence, and projection mismatch still fail closed.

### P4-STAGE-E — reconcile storage lifetime

**Concern.** Stage separation is defeated if storage cleanup removes the normalized frame payload while active downstream consumers still require it, forcing hidden regeneration.

**Required end state.** Owner-driven storage retention protects exactly the hot prepared-generation representations still required by active/current P3/P5/P7 consumers. DATA4 may be cold and need not be loaded by those consumers.

**Acceptance.** Safe cleanup cannot make an otherwise valid active prepared generation require hidden DATA4/P1 reconstruction. If cache-policy eviction remains allowed during that lifetime, the owning design must provide a direct equivalent prepared restore without live-source reconstruction; otherwise retain the cache until the last required consumer closes.

### P4-STAGE-F — remove obsolete reconstruction-currentness doctrine

**Concern.** Documentation/tests currently encode “nothing persisted is trusted; rebuild P1/P2 on every load” as if that implementation strategy were the product invariant.

**Required end state.** Documentation distinguishes:

- CampaignStore current revision authority;
- immutable generation-scoped prepared scientific state;
- live-source authentication during `prepare` creation/rebuild;
- prepared-artifact integrity during downstream consumption;
- P3 immutable-evidence authentication during screening/terminal exposure.

Remove tests/docs that require downstream reconstruction merely because the old implementation did it. Preserve tests for the actual scientific/currentness outcomes.

---

## 6. Task-specific acceptance

### 6.1 Exact no-reconstruction downstream assertions

After one successful `prepare`, instrument the real production path. A normal `select-target-size` start and resume must make **zero** calls to all of the following preparation-only operations:

```text
read_data4_sharded_record(...)              # DATA4 restore
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

If implementation legitimately renames/replaces one of these delegated owners, remap the assertions to the final real prepare-only owner. The semantic claim is zero preparation reconstruction, not preservation of function names.

The same zero-reconstruction assertion applies to current terminal reload/write/report and the P5-facing current terminal result seam.

### 6.2 DATA4 I/O acceptance

Required cases:

1. **Cold prepare that constructs DATA4:** after DATA4 construction/persistence, no immediate sharded DATA4 restore is performed solely to continue P1/P2/P3 preparation when the validated in-memory object is already available.
2. **Warm select after prepare:** zero DATA4 restore.
3. **Select resume:** zero DATA4 restore.
4. **Terminal reload/report:** zero DATA4 restore.
5. **Prepared-state corruption:** fail closed before selection/report; do not restore DATA4 as an automatic repair path.

Record DATA4 restore count explicitly in bounded integration evidence.

### 6.3 Scientific identity equivalence

On a bounded real multi-run corpus, compare the pre-repair builder result with the newly published prepared generation. Require equality of every still-binding scientific identity:

- frame authority;
- neutral statistical base;
- split exclusion;
- target-size policy;
- experiment definition;
- aggregate;
- common preparation;
- P3 execution context when built from the same downstream configuration;
- initial screen window/schedule identity.

Persistence/load round-trip must preserve those identities exactly.

### 6.4 Snapshot mutation semantics

Required regression:

```text
prepare -> generation g1 prepared snapshot
mutate one live source/control/companion file after prepare
select-target-size g1
```

`select-target-size` must continue to consume the exact g1 prepared snapshot and must not silently reconstruct/reinterpret it from the changed live source tree.

Then run `prepare` again. It must detect the preparation-owned source identity change through the accepted preparation input-currentness mechanism, perform the required fresh authentication/rebuild, and advance to fresh generation `g2` before any g2 screen is opened.

This establishes the correct boundary: source mutation affects the next preparation, not an already-frozen experiment.

### 6.5 Existing-generation compatibility regression

Construct or load a current generation in the old representation that has CampaignStore scientific digests but lacks the new prepared-generation artifacts.

`select-target-size` must refuse it with actionable guidance to run `prepare`. It must **not** reconstruct missing prepared state from live sources and attach it to the old generation.

After `prepare`, prove:

- a fresh generation is bound;
- the new generation has complete prepared artifacts;
- old immutable execution evidence/root remains historical;
- a new screen uses the new generation root;
- no immutable `screen.json` collision/overwrite occurs.

### 6.6 Corruption and partial-publication regressions

Test at least:

- missing prepared component;
- corrupt prepared component bytes/payload;
- prepared component digest mismatch;
- publish prepared component then crash before CampaignStore adoption;
- current CampaignStore revision pointing to incomplete/corrupt prepared state must be rejected;
- stale historical prepared generation cannot be loaded as current by changing only a convenience path/pointer.

No case may fall back to reconstructing upstream science in a downstream command.

### 6.7 Currentness negatives remain closed

Preserve failure of:

- stale expected CampaignStore revision;
- changed generation;
- wrong execution-context digest;
- missing/corrupt P3 execution root evidence;
- adopted head mismatch;
- reducer mismatch;
- terminal projection mismatch;
- stale current-result publication attempts already covered by P4-E4.

The repair changes **how prepared scientific currentness is established**, not the requirement that stale/historical terminal evidence cannot be exposed as current.

### 6.8 Structural absence/uniqueness

After implementation, inspect the final production call graph and structurally verify:

1. exactly one prepare-only scientific substrate builder path;
2. exactly one current prepared-generation loader/owner path or one semantically equivalent canonical owner;
3. `select-target-size`, terminal current exposure, and P5-facing current result consumption do not call the prepare builder;
4. no second DATA4/frame cache or freshness/currentness registry was introduced;
5. no downstream fallback calls live-source P1 reconstruction when prepared load fails;
6. CampaignStore remains the sole current generation/revision authority;
7. generation-scoped prepared artifacts are immutable after adoption.

Use semantic caller/reference inspection and a focused structural scan when available. Text search alone is not sufficient for dynamic/exported call paths, but it remains a useful cross-check.

### 6.9 Performance/resource evidence

This repair is structurally performance-motivated; no universal wall-time speedup percentage is required because filesystem/cache conditions vary.

Measure bounded before/after startup for:

- unchanged repeated `prepare`;
- first `select-target-size` after prepare;
- select resume;
- terminal reload/report.

Record at minimum:

- wall time;
- DATA4 restore count;
- source-frame read count;
- P1 authentication count;
- preparation-builder invocation count;
- bytes read when practical;
- peak RSS when material.

Structural elimination of upstream replay is mandatory even if a tiny synthetic corpus has noisy wall time.

---

## 7. Expected affected surface

Initially inspect and reconcile at least:

### Runtime/orchestration

- `mdstats/training_data/campaign_target_size_runtime.py`
  - `CurrentTargetSizeAuthorities`
  - `build_current_target_size_authorities`
  - `execute_current_prepare`
  - `build_screen_context`
  - `execute_current_select_target_size`
  - current terminal reporting seam
- `mdstats/training_data/campaign_target_size_cutover.py`
  - authority binding/generation advance/publication ordering
- `mdstats/training_data/campaign_target_size_state.py`
  - only if prepared-state binding requires a state-schema field; avoid schema growth if existing bound component digests plus deterministic generation ownership are sufficient
- `mdstats/training_data/campaign_target_size_terminal.py`
  - `ValidatedTargetSizeTerminalResult`
  - `load_validated_target_size_terminal_result`
- `mdstats/training_data/campaign_target_size_view.py`
  - current exposure consumers if loader contract changes
- `mdstats/training_data/_campaign_cli_core.py`
  - `_prepare_catalog`
  - CampaignStore prepared-component serialization/load path
  - preparation config/input reuse checks
- `mdstats/training_data/frame_cache.py`
  - only if retention/identity ownership requires adjustment; do not create another cache

### Scientific objects

- P1/P2/P3 `to_dict/from_dict` or existing serialization boundaries for only those prepared objects actually persisted;
- neutral/canonical/aggregate/common owners only as needed to support lossless round-trip; do not change scientific definitions.

### Storage

- current storage owner inventory/retention policy for normalized frame payload and prepared generation artifacts;
- cleanup tests proving active prepared state remains restartable without hidden upstream rebuild.

### Tests

At minimum rederive impact over:

- P1 neutral scientific substrate tests;
- DATA4 sharded persistence/restore tests;
- frame-cache integrity/lifetime tests;
- P4-A through P4-G state/cutover/runtime/terminal/integration suites;
- P3 execution/restart/immutable publication suites;
- P5 current-result consumer tests;
- P6/STOR retention tests affected by artifact classification;
- P7 current-generation consumers if they load target-size prepared state;
- the post-DATA4 authority-reconstruction I/O tests, whose expected ownership must be revised from “fast downstream reconstruction” to “reconstruction occurs only in prepare.”

Final affected surface must be re-derived after implementation rather than copied mechanically from this list.

---

## 8. Implementation sequence

### Stage 1 — persist/load one prepared generation

Implement the generation-scoped prepared-state publication and canonical loader first. Establish lossless round-trip and crash/currentness behavior before changing downstream callers.

Stage-local closure:

- scientific digest equivalence;
- publish/load round-trip;
- missing/corrupt/partial publication negatives;
- no second currentness authority.

### Stage 2 — make prepare reuse and remove same-invocation DATA4 bounce

Route newly created DATA4/frame payload directly into the prepare builder; add/reconcile unchanged-prepare reuse through preparation-owned input identity.

Stage-local closure:

- cold prepare has no DATA4 immediate read-back solely for builder continuation;
- repeated unchanged prepare does not rebuild P1/P2/P3-common;
- changed preparation input produces fresh generation.

### Stage 3 — cut select-target-size to prepared consumption

Remove prepare-builder invocation from `build_screen_context`/selection startup and consume the exact current prepared generation.

Stage-local closure:

- zero DATA4/P1/P2/P3 reconstruction on start and resume;
- same screen/aggregate/context identities;
- existing-generation-without-snapshot rejection;
- immutable screen collision reproducer closes through fresh-generation ownership, not overwrite.

### Stage 4 — cut terminal/current-result and downstream consumers

Replace terminal live-source reconstruction with prepared-generation loading while preserving real P3/currentness validation.

Stage-local closure:

- zero upstream reconstruction on current terminal load/write/report;
- stale/currentness/corruption negatives remain closed;
- P5-facing seam uses same current prepared generation.

### Stage 5 — reconcile storage retention and final assembled acceptance

Update owner-driven storage retention only as necessary, rederive final affected surface, run full affected regression/integration, and record bounded startup/I/O evidence.

---

## 9. Simplification triggers and forbidden repair patterns

This defect is already a simplification trigger: repeated reconstruction was introduced to avoid persisting prepared objects, then performance machinery was added to make the repeated reconstruction cheaper. Do not add another optimization layer around that repetition.

### Required simplification direction

Prefer:

```text
one prepare builder
+ one immutable prepared generation
+ one prepared loader
+ one current CampaignStore generation authority
```

rather than:

```text
rebuild upstream science in every command
+ cache those rebuilds
+ freshness flags
+ skip-validation switches
+ more parallelism
+ more reconciliation
```

### Forbidden patterns

Do not close this workplan by:

- retaining downstream P1/P2/P3 reconstruction and merely making it faster;
- adding an in-process memoization cache that disappears between CLI invocations;
- adding a second prepared-state cache beside the existing normalized frame cache when generation-scoped persistence is the real missing capability;
- adding `fast`, `trust_cache`, `trust_prepared`, `skip_auth`, or similar bypass modes;
- treating DATA4 restore progress as acceptable merely because it is faster than recomputation;
- automatically rebuilding a missing prepared generation inside `select-target-size` or terminal load;
- binding freshly reconstructed objects to an old generation that already owns immutable P3 evidence;
- weakening immutable publication to allow a changed `screen.json` to overwrite the old one;
- copying the P1 authentication checklist into a second currentness verifier;
- making source filesystem mtimes alone scientific identity;
- making a result-view file or prepared convenience alias authoritative over CampaignStore.

---

## 10. Implementation authority

### Frozen

- V7 scientific model and P1/P2/P3 scientific identities.
- `prepare` is the sole creation/advance boundary for the target-size scientific substrate.
- Successful prepare defines one immutable generation-scoped prepared snapshot.
- `select-target-size`, resume, terminal current exposure, and downstream target-size consumers load that snapshot rather than reconstructing it from live upstream inputs.
- CampaignStore remains the sole current generation/revision/lifecycle authority.
- Live source mutation affects a future `prepare`/generation, not an already-prepared generation.
- Missing/corrupt prepared state fails closed; no downstream reconstruction fallback.
- No DATA4 restore solely for ordinary downstream currentness/reconstruction.
- No weakening of immutable P3 evidence or generation-root identity.
- Existing normalized frame payload machinery is reused; no second frame cache.

### Delegated

- Exact prepared snapshot class/record names.
- Whether prepared components are individual generation-scoped CampaignStore records or one compact canonical manifest over existing records.
- Exact private helper factoring and function names.
- Whether `CurrentTargetSizeAuthorities` is renamed, split, or removed.
- Exact serialization layout for prepared components.
- Exact cheap source-byte-currentness implementation used by repeated `prepare`, provided it relies on exact content identity/integrity rather than mtimes alone and does not create a second authority database.
- Exact storage classification enum/name for active normalized frame payload, provided downstream restartability and no-hidden-rebuild semantics hold.

### Reopen only on evidence

Reopen this design only if implementation evidence proves one of the following:

1. a downstream scientific consumer genuinely requires DATA4 content itself, not merely objects previously derived from DATA4;
2. a required prepared object cannot be persisted/reloaded losslessly without an unacceptable resource footprint and no simpler equivalent representation exists;
3. retaining normalized frame payload for active downstream consumers violates a demonstrated storage budget and a different direct prepared representation is required;
4. a governed external compatibility contract requires live-source reinterpretation between `prepare` and `select-target-size` rather than snapshot semantics.

If any trigger fires, reopen only the affected representation/ownership surface. Do not reopen V7 target-size science by convenience.

---

## 11. Closure criteria

This amendment closes only when all of the following are true on one assembled candidate:

- `prepare` owns expensive preparation creation and publishes restartable prepared state;
- cold prepare does not immediately restore newly created DATA4 solely because of an internal API boundary;
- unchanged repeated prepare reuses the prepared generation without rebuilding P1/P2/P3-common;
- select start/resume performs zero DATA4 restore and zero preparation reconstruction;
- terminal current load/write/report performs zero DATA4 restore and zero preparation reconstruction;
- downstream P5/current consumers use the same current prepared generation;
- prepared-load corruption fails closed without live-source fallback;
- source mutation after prepare cannot mutate/reinterpret an in-progress generation;
- a subsequent prepare detects changed preparation inputs and advances generation;
- legacy/current generations lacking prepared artifacts require explicit fresh prepare rather than retroactive reconstruction;
- immutable old screen evidence is never overwritten under a changed preparation identity;
- scientific digests match the accepted pre-refactor construction;
- final affected regression and real-owner bounded integration pass;
- no second cache/currentness/generation/freshness machinery was introduced.

A system that is scientifically correct but still replays DATA4/P1/P2/P3 across command boundaries is **not** accepted. A system that avoids the replay by weakening authentication/currentness or by trusting mutable aliases is also **not** accepted. The required end state is one immutable prepared scientific generation, one current CampaignStore authority, and downstream consumption without reconstruction.
