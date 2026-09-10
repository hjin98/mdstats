---
kind: implementation-workplan
workplan_id: CODE-MLFF-REPLAY-MACE-MEMBERSHIP-IDENTITY-REPAIR
protocol_version: 6.0.0
status: active
created_date: 2026-09-09
implementation_branch: fix/mlff-replay-mace-membership-identity
planning_base_commit: 9abb2b89930b48d9e2771addb5f59879bfec1001
baseline_executable_commit: 13859556cd4d472837a9e171c2be32e59d5e6d82
highest_affected_domain: D4 realization under unchanged accepted D3 replay/MACE architecture
serious_challenge: none
scope: single-source replay membership identity at the P5 -> MACE execution-authority and TRAIN2 restart boundary
---

# MLFF single-source replay -> MACE membership-identity repair

## 0. Disposition

A real `cross-validate` invocation fails before TRAIN2 starts with:

```text
TrainingDataInputError: MACE execution frame identity requires non-empty UID values.
```

The failure is a bounded D4 integration defect. It is **not** evidence that the accepted target-size/CV/replay scientific method is wrong, and it does not require reopening the recently closed downstream D3 architecture.

The supported single-source replay pipeline uses one external `[paths].replay_set`, canonical replay geometry/source/split identities, and reconstructable generated ExtXYZ train/monitor views. Those generated views are valid without target-domain `frame_uid` metadata. The strengthened P5/MACE execution-authority realization introduced in executable candidate `13859556...` assumes that every replay training frame can be represented by the same `frame_uid` field used for target DATA8 membership. The real single-source replay transport does not make that promise.

Repair the existing execution-identity adapter so the replay head is authenticated from the **existing replay membership authority** rather than requiring a target-only transport field. Do not add a new replay identity, rewrite replay science, introduce another persistence record, or require manual deletion/reprepare.

The TorchScript deprecation warnings and the MACE float64 -> float32 calculator warning printed immediately before the traceback are non-causal to this defect and are outside this repair.

---

## 1. Diagnosis and causal chain

### 1.1 Supported single-source replay has no `frame_uid` requirement

The current REPLAY-UNIFY single-source architecture makes the selected replay ExtXYZ and deterministic split the external/canonical replay authority. Generated train/monitor ExtXYZ files under `.mdstats/replay-unified/views` are reconstructable internal transports. Current single-source test/source fixtures deliberately contain valid labeled configurations without `frame_uid`, and generated true-label/pseudolabel views carry replay-specific provenance such as `replay_geometry_identity`, `replay_split_role`, and `replay_source_index` rather than target DATA occurrence identity.

`ReplayFileArtifact` likewise owns replay geometry/label/file identity with `geometry_identities`, `label_identities`, file SHA, label mode, and related provenance. It has no `frame_uids` field and rejects duplicate replay geometries.

This is intentional: target DATA membership and replay membership are different semantic identity domains.

### 1.2 The new execution helper imposes the wrong transport assumption

`post_selection_execution._mace_execution_frame_uid_set_digest()` currently does:

```text
artifact.frame_uids if present
else read artifact.path as ExtXYZ
     -> str(atoms.info.get("frame_uid")) for every frame
     -> mace_frame_uid_set_digest(...)
```

For a valid single-source generated replay frame without `frame_uid`, `atoms.info.get(...)` is `None`, it becomes the string `"None"`, and `mace_frame_uid_set_digest()` correctly rejects it as a non-empty UID violation.

That is the exact observed traceback.

### 1.3 Removing only the parent-side check is not a fix

The dependency-facing MACE wrapper has the same assumption. `_annotate_mace_collections_with_exported_uids()` reads MACE training files and currently requires every exported frame to contain non-empty `frame_uid`; `_validate_mace_execution_loader()` then digests the loaded target/replay membership and compares it to the authenticated launch authority.

Therefore any patch that merely makes `_mace_execution_frame_uid_set_digest()` return `None` or suppresses its exception would only move the crash into the child MACE process and would weaken the exact-membership restart/currentness protection. This is forbidden.

### 1.4 Why existing acceptance missed the defect

The legacy P5 replay guard fixture explicitly writes `atoms.info["frame_uid"] = ...`, so the real trainer/MACE tests built on that fixture satisfy the newer assumption.

The canonical REPLAY-UNIFY1D source fixture, by contrast, intentionally writes valid replay frames without `frame_uid`, but its tests stop at replay planning/materialization/persistence and do not carry that generated single-source transport through the real MACE execution-membership owner.

The defect is therefore a **composed-boundary acceptance gap**:

```text
single-source replay owner: valid independently
MACE exact-membership owner: valid independently with legacy frame_uid fixtures
assembled single-source replay -> MACE boundary: untested and broken
```

---

## 2. Governing Protocol 6 authority and impact classification

### 2.1 D1 — unchanged

No scientific formulation changes are authorized. Preserve:

- replay training exposure versus independent TRUE_DFT replay admissibility;
- selected-size/CV/final-production scientific meaning;
- replay source/split/label semantics;
- foundation scientific identity;
- multi-size experiment semantics.

### 2.2 D2 — unchanged

No numerical/algorithm change is authorized. Preserve:

- optimizer/loss/weighting/batching semantics;
- CV horizons and acceptance predicates;
- precision/dtype policy;
- checkpoint ranking/evaluation conventions;
- target/replay exposure counts and training behavior.

### 2.3 D3 — accepted architecture remains current

Preserve these current architectural owners:

1. single-source replay source + deterministic split own replay membership/lineage;
2. generated replay ExtXYZ views are reconstructable internal transport/cache, not new scientific authority;
3. target DATA occurrence membership is identified by target `frame_uid` authority;
4. P5 owns exact run/materialization/currentness;
5. MACE execution evidence authenticates the actual membership consumed by the dependency-facing loader;
6. TRAIN2 continuation may be reused only when its persisted MACE execution evidence matches the current P5 materialization/execution authority.

No Serious Challenge is active against these claims.

### 2.4 D4 — defect owner

The defect is the D4 mapping between the replay transport identity domain and the generic MACE execution-membership evidence. The repair must alter/consolidate that mapping rather than changing upstream replay authority to satisfy the adapter.

---

## 3. Frozen repair invariants

The implementation must satisfy all of the following.

### R1 — role-appropriate exact membership

Target and replay membership may share a generic MACE execution-evidence mechanism, but they do **not** have to share the same source metadata field.

- target execution continues to bind exact target `frame_uid` membership;
- single-source replay execution binds the exact existing replay geometry membership represented by the authenticated replay artifact/view and split;
- no replay membership is guessed from order, count, pathname, or an index created only for this repair.

### R2 — no new replay scientific identity

Do not introduce a new durable replay UID namespace, replay-ID registry, compatibility database, mapping table, or alternate replay-lineage digest.

When the MACE adapter needs an opaque per-frame token, it must be a direct deterministic projection of an already-authoritative replay identity. Existing `replay_geometry_identity` / authenticated replay geometry membership is the intended source. A second independently generated hash is not justified.

### R3 — preserve current scientific lineage and prepared workspace

The currently frozen P5 replay lineage includes authenticated train/monitor view digests and SHA values. Therefore **do not rewrite otherwise valid generated single-source replay view bytes solely to inject `frame_uid` metadata** if doing so changes the current view SHA/lineage and invalidates the already-frozen experiment.

The supplied failed workspace must be recoverable by installing the fix and rerunning `cross-validate`:

- no `prepare` rerun required solely for this defect;
- no manual deletion of `.mdstats/replay-unified`, P5 materialization, or campaign state;
- no mutation of the external replay source;
- no change to source/split/method/replay-lineage identity merely to satisfy MACE transport bookkeeping.

If implementation evidence shows this cannot be achieved without changing accepted replay-lineage semantics, stop and return to Software Design rather than silently redefining lineage.

### R4 — keep exact MACE execution evidence and restart protection

Do not weaken the MACE execution-authority check to counts only and do not set replay membership evidence to `None` merely to pass launch.

The actual loaded replay collection must still be authenticated against the exact expected replay membership before training, and persisted TRAIN2 continuation evidence must still bind that exact membership on restart/full-horizon reclosure.

### R5 — preserve supported legacy replay behavior

The historical split replay interface remains supported where current authority says it is supported. Do not invalidate otherwise authentic legacy continuation/evidence solely because the single-source adapter is repaired.

If legacy files use explicit `frame_uid` as their current execution-membership token while single-source generated views use replay geometry identity, keep the distinction explicit and bounded at the existing adapter owner. Do not create a generic cascading fallback that silently mixes identity domains within one replay file/run.

A file/run with partial or conflicting identity metadata must fail typed rather than selecting per-frame fallbacks.

### R6 — no warning/dtype detour

Do not change warning condensation, TorchScript compatibility handling, model dtype conversion policy, or MACE calculator construction as part of this fix. They are not on the causal path.

---

## 4. Preferred realization direction — delegated D4 details

The exact helper names/signatures remain delegated, but the preferred minimum-complexity realization is an **adapter-level role-aware membership projection**, not transport rewriting.

A coherent realization may:

1. replace/narrow `_mace_execution_frame_uid_set_digest()` with a membership resolver whose semantics distinguish target versus replay;
2. for single-source replay, derive the expected execution-membership digest from the already-authenticated replay geometry identity available in the replay artifact/generated view;
3. update the existing MACE collection annotation/validation owner so the actual replay collection is annotated/validated from the same replay identity domain while target collections continue to use target `frame_uid`;
4. keep the existing MACE execution-authority/evidence record family and TRAIN2 continuation binding rather than adding a new persistent record;
5. retain current legacy split behavior through an explicit supported-interface rule if needed.

Prefer one shared role-aware resolver/normalization rule used by launch and child-loader validation. Do not independently implement the same mapping in P5 and the MACE wrapper if it can be expressed once and reused.

### Forbidden shortcuts

Do not:

- catch/ignore the `TrainingDataInputError`;
- pass `replay_frame_uid_set_digest=None` while replay is enabled;
- disable replay-membership comparison in `record_mace_execution_evidence()`;
- inject arbitrary sequential IDs based on file order;
- derive identity from a filesystem path;
- rewrite user replay source files;
- rewrite generated single-source view bytes merely to make the current helper happy if that changes frozen replay lineage;
- require the user to delete prepared replay views/P5 state;
- add a migration DB, replay-ID registry, compatibility daemon, second MACE wrapper, or new restart state machine.

---

## 5. Affected surface

Re-derive from the final candidate, but the expected direct surface includes:

- `mdstats/training_data/post_selection_execution.py`
  - execution-membership digest resolution;
  - `_build_post_selection_mace_execution_authority()`;
  - real `MacePostSelectionTrainer` launch path.
- `mdstats/training_data/critical_precision_cli.py`
  - `_annotate_mace_collections_with_exported_uids()` or its resulting owner;
  - `_validate_mace_execution_loader()` replay membership observation.
- `mdstats/training_data/mace_compatibility.py`
  - inspect only as necessary; preserve generic authority/evidence integrity unless a minimal semantic rename/refactor is genuinely required.
- `mdstats/training_data/campaign_post_selection_runtime.py`
  - P5 replay resolution/request wiring and continuation reauthentication; change only if the execution owner needs explicit existing replay-interface context.
- `mdstats/training_data/replay.py` / `replay_pseudolabel.py`
  - inspect as canonical identity/transport owners; **do not modify generated view bytes by default**.
- TRAIN2 continuation owner only to verify persisted MACE evidence remains exact; avoid changes unless required by actual evidence.

Expected test surface includes at least:

- `tests/test_mlff_replay_unify1b.py`
- `tests/test_mlff_replay_unify1c.py`
- `tests/test_mlff_replay_unify1d.py`
- current REPLAY-UNIFY1E/restart equivalents
- `tests/test_mlff_target_size_p5_r8_guards.py`
- `tests/test_mlff_target_size_p5_r9_guards.py`
- `tests/test_mlff_target_size_p5_r10_guards.py`
- `tests/test_mlff_downstream_integration_closure.py`
- `tests/test_mlff_mace_execution_semantics.py`
- `tests/test_mlff_mace_execution_semantics_assembled.py`
- `tests/test_mlff_mace_executable_config.py`
- `tests/test_mlff_train2a_policy.py`
- `tests/test_mlff_train2b_runtime.py`
- affected multi-size campaign integration/currentness tests.

The three known stale campaign-warning CLI tests from the prior closure remain separate test debt and are not to be patched into this workplan unless new evidence shows the present repair actually affects them.

---

## 6. Acceptance and falsification requirements

### A1 — exact observed regression, no `frame_uid`

Use the canonical single-source replay fixture whose source/generated views do not carry `frame_uid`.

Through the real P5 request/trainer owner, prove:

```text
single-source replay resolution
 -> MacePostSelectionTrainer
 -> MACE execution authority construction
```

no longer rejects non-empty UID identity before wrapper launch.

Do not add `frame_uid` to the fixture merely to make the test pass.

### A2 — dependency-facing real-owner proof

Execute a bounded pinned-MACE path in which the actual generated single-source replay training view lacks `frame_uid` and the real MACE loader/collection validation owner runs.

Prove:

- replay train count is exact;
- actual loaded replay membership digest equals the authenticated expected digest;
- target membership still uses target `frame_uid` and remains exact;
- resolved MACE execution evidence contains the replay membership evidence and is accepted by `record_mace_execution_evidence()`;
- training reaches the accepted bounded seam rather than failing in collection annotation/validation.

Expensive training may be bounded below the real loader/semantic owner. A helper-only digest test is insufficient.

### A3 — same-workspace / no-lineage-churn counterfactual

Construct a prepared single-source campaign using the pre-fix generated views, record at minimum:

- replay source content digest/SHA;
- split manifest digest;
- train/monitor generated view SHA and artifact content digests;
- P5 replay lineage digest;
- method identity.

Run the fixed owner on the **same workspace**.

Required result:

- no manual deletion or reprepare;
- existing generated view bytes remain unchanged unless independently corrupt;
- source/split/view/method/replay-lineage identities remain unchanged;
- MACE execution-membership authority is established from the existing replay identity;
- cross-validation proceeds beyond the previous failure point.

### A4 — exact membership mutation

Counterfactuals must prove the repair has not weakened execution ancestry:

- mutate/substitute one replay training geometry after the expected replay artifact/authority is established -> reject before training evidence is accepted;
- reorder frames only -> behavior must follow the governing set/order semantics already owned by replay/MACE authority; do not invent a new order requirement;
- partial/conflicting identity metadata -> typed fail-closed;
- duplicate replay geometry remains rejected by the existing replay owner;
- target `frame_uid` mutation still rejects independently.

### A5 — restart/continuation

Prove with the real P5/TRAIN2 owner:

- current single-source replay continuation persists and reauthenticates the same replay execution-membership evidence;
- a continuation with mismatched replay membership is rejected before resume/EVAL2/publication;
- full-horizon continuation cannot bypass replay membership authentication;
- current supported legacy replay continuation remains reusable when its existing execution identity is unchanged.

Do not add a compatibility persistence record for this purpose.

### A6 — multi-size composition

Use a bounded frozen multi-size campaign with replay enabled, ideally `[N1, N2]` with different CV horizons, and prove the shared replay execution repair does not reintroduce subset/first-size-only behavior.

The test need not train production-scale `N=512/8192`; it must execute the real multi-size orchestration and real replay/P5 owner with expensive numerical work bounded below the accepted seam.

### A7 — structural absence / family closure

Use Semgrep when available; otherwise a bounded AST/source fallback with known-positive/known-negative validation.

Establish at minimum:

- no single-source P5/MACE path requires `frame_uid` as the **sole** replay membership source;
- no user replay source mutation/in-place `frame_uid` injection was introduced;
- no new replay UID registry/schema/state-machine/fallback service exists;
- no count-only or `None` replay-membership shortcut was introduced;
- target `frame_uid` exactness remains present.

### A8 — final affected regression

At minimum run the applicable current versions of:

```bash
pytest -q \
  tests/test_mlff_replay_unify1b.py \
  tests/test_mlff_replay_unify1c.py \
  tests/test_mlff_replay_unify1d.py \
  tests/test_mlff_target_size_p5_r8_guards.py \
  tests/test_mlff_target_size_p5_r9_guards.py \
  tests/test_mlff_target_size_p5_r10_guards.py \
  tests/test_mlff_downstream_integration_closure.py

pytest -q \
  tests/test_mlff_mace_executable_config.py \
  tests/test_mlff_mace_execution_semantics.py \
  tests/test_mlff_mace_execution_semantics_assembled.py \
  tests/test_mlff_train2a_policy.py \
  tests/test_mlff_train2b_runtime.py
```

Then run affected multi-size campaign/currentness/restart/storage tests re-derived from the final diff and the repository-configured fast Python static/lint/type checks where available.

If the changed shared MACE execution helper reaches target-size screening or other training roles, include those affected regressions rather than assuming P5-only impact.

Full GPU/CuEq/LAMMPS/MLIAP target-machine qualification remains deferred to final release qualification.

---

## 7. Implementation sequence

### Stage A — identity-owner correction

Repair the P5/MACE replay membership mapping at the existing execution owner while preserving target `frame_uid`, replay source/split/view identities, and current legacy behavior.

Run A1, focused MACE semantic tests, and structural checks immediately.

### Stage B — assembled loader + restart closure

Run the real dependency-facing MACE loader path and TRAIN2 continuation counterfactuals A2-A5. If the implementation needs additional state or a schema migration to pass, stop and return to Software Design before adding it.

### Stage C — multi-size/final regression

Run A6-A8 on one unchanged executable candidate. Re-derive the final affected surface after the actual patch rather than mechanically using this provisional list.

No documentation/architecture rewrite is expected unless implementation uncovers a real contradiction in current D3 authority. A local code comment/test clarification is not a reason to revise the Architecture Manual.

---

## 8. PASS criteria for independent Software Design review

```text
[ ] exact user failure is reproduced by a regression using valid single-source replay without frame_uid
[ ] fixed real P5 trainer no longer rejects that transport before launch
[ ] real MACE loader validates the same exact replay membership authority
[ ] target frame_uid membership remains exact and unchanged
[ ] single-source source/split/view SHA/content/replay-lineage/method identities do not churn solely for this fix
[ ] same prepared workspace retries without prepare/reset/manual deletion
[ ] no external replay source is modified
[ ] replay membership is not reduced to count-only/None evidence
[ ] replay membership mutation is rejected before accepted training evidence
[ ] TRAIN2 partial/full-horizon continuation reauthenticates replay membership exactly
[ ] supported legacy replay continuation semantics are not silently invalidated
[ ] multi-size orchestration remains complete
[ ] no new replay identity, registry, migration DB, state machine, wrapper, daemon, or path-based authority is introduced
[ ] required affected regression/integration/static evidence executes and passes on the exact final candidate
```

---

## 9. Reopen triggers

Return to Software Design only if evidence shows one of the following:

1. accepted single-source replay geometry/split identity is insufficient to prove the exact replay membership MACE consumes;
2. preserving the already-frozen replay lineage necessarily requires changing current D3 replay-lineage semantics;
3. current supported legacy and single-source replay execution identities cannot coexist without a durable compatibility/migration mechanism;
4. MACE 0.3.16 cannot expose/validate replay membership without rewriting canonical replay transport or changing D2 training semantics;
5. the repair materially changes replay labels, exposure, optimizer behavior, precision, CV science, or checkpoint-selection meaning.

Absent such evidence, keep this a bounded D4 repair beneath the accepted Protocol 6 D3 architecture.
