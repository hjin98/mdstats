---
kind: implementation-repair-instructions
package_id: CODE-MLFF-TARGET-SIZE-V7-P3-P3A4-REPAIR
governing_package_id: CODE-MLFF-TARGET-SIZE-V7-P3-REVIEW5
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 3
status: active
package_revision: 7
reviewed_implementation_commit: ab0f5f3b66766b7a566023b253fbac57872ce59d
reviewed_implementation_label: P3A4
---

# P3 revision-7 P3A4 implementation repair instructions

## 0. Authority and routing

This file is **not a new P3 design amendment and does not increment P3 revision 7**. It records the exact implementation repairs required after independent review of `ab0f5f3b66766b7a566023b253fbac57872ce59d` (`P3A4`). The governing scientific and architectural authority remains the V7 parent workplan plus the cumulative P3 base/Review-2/Review-3/Review-4/Review-5 contracts.

All findings below are **implementation nonconformance**. Preserve the P3A4 work that is already conformant: mandatory `evaluation_data_digest`, snapshot-only EVAL2 role construction, full optimizer-policy validation at trajectory validation, success prediction/metric linkage, coordinator temporary-file publication, screen-level commit locking, mandatory schedule on reconciliation, required success prediction evidence, and the introduction of a real subprocess boundary.

P4 remains blocked until the repairs below and cumulative revision-7 acceptance pass.

---

# 1. Repair pass A — one authenticated provider and one sealed exact-M input

## A1. Replace the two-model inference path with one provider-owned state path

### Current nonconformance

`run_target_size_direct_boundary_inference()` still authenticates a manually `torch.load()`ed model/companion and then constructs a separate `MaceCalculatorProvider` to perform production prediction. EMA state is copied again into that second provider. The fake-forward path can bypass provider construction entirely.

### Required code end state

Refactor the direct inference owner so there is exactly one accepted execution object:

1. Validate trajectory, materialization, snapshot, role, P1 authority and exact-M artifact before numerical forward.
2. Construct/reconstruct the MACE provider shell from the validated candidate materialization/configuration authority. Do not treat the TRAIN2 raw checkpoint pathname as an independent executable-model authority.
3. Load the exact immutable boundary snapshot state into that provider/model through the shared `MaceCalculatorProvider` state-loading/compatibility machinery. Reuse or extract the established canonical execution-architecture and shell-policy authorities in `model_features.py`; do not add a second P3 compatibility definition.
4. For live evaluation, compute the canonical live parameter digest **from the provider model after load** and require equality with the snapshot/runtime summary.
5. For EMA evaluation, validate exact cardinality/order/key/shape/dtype compatibility against the provider model, apply every shadow parameter exactly once, and recompute the canonical digest from the actual provider model after application. Any unchecked `zip()` over provider parameters/shadows is inadmissible.
6. Only after steps 1-5 may prediction execute.

Delete the accepted pattern:

```text
manual checkpoint model -> authenticate
separate provider.from_model_path(...) -> predict
```

The same provider/model instance that is authenticated must be the instance that predicts.

### Fake boundary

Retain a bounded test seam only **below** authenticated provider construction/state loading. A suitable shape is conceptually:

```text
provider = build + load + authenticate
raw_predictions = forward_override(provider, authenticated_atoms)
# or provider.predict_batch(authenticated_atoms)
```

Do not pass only `boundary_state` to a fake that replaces provider construction/state loading. A fake may replace expensive forward arithmetic, not the owner being accepted.

### Prediction evidence

Populate execution provenance from the actual provider/run; do not rely on dataclass defaults. Bind at least:

- canonical provider/model execution-architecture digest or equivalent established identity;
- actual device;
- actual default dtype / critical precision realization;
- actual acceleration/compile backend policy;
- actual accepted batch/execution policy where it changes the prediction path.

If a field is part of accepted prediction identity, construction must require it or derive it from the real provider. Defaults such as `cpu`, `float64`, `eager`, or batch size `4` must not silently describe a different execution.

### Acceptance

Add focused CPU-bounded tests proving:

- mutating the provider state after snapshot metadata is presented but before authentication is rejected;
- live and EMA digests are computed from the provider that actually forwards;
- EMA cardinality/shape/dtype/order mismatch fails before forward;
- the fake-forward test still constructs and authenticates the real provider owner;
- execution-policy evidence differs if and only if the actual accepted provider realization differs;
- an implementation that authenticates model A but forwards model B cannot pass.

## A2. Make exact-M bytes the single evaluation input object

### Current nonconformance

`build_authenticated_evaluation_view()` hashes `target.read_bytes()` but then reopens the pathname with `ase.io.read(str(target))`. Reduction also retains an arbitrary-object fallback when the object carries a matching `evaluation_view_digest`.

### Required code end state

Introduce/finish one immutable authenticated exact-M input produced by the evaluation-artifact owner. It must bind:

- evaluation artifact content digest;
- ExtXYZ SHA-256;
- exact ordered frame UIDs;
- evaluation membership digest/count;
- energy/forces/stress key policy and policy digest;
- canonical P1 authority identity;
- parsed atoms/labels or the owner-produced EVAL2 view derived from the same authenticated bytes.

Read the ExtXYZ bytes once and parse those exact bytes. Prefer an in-memory stream such as `io.BytesIO(raw_bytes)` with explicit ExtXYZ format rather than hashing bytes and reopening the pathname. Equivalent before/after verified-read transaction semantics are acceptable only if they reject any intervening mutation.

Inference and reduction must consume this authenticated object or independently rebuild it from the same durable artifact under the same validator. They must not validate one file state and consume another.

## A3. Remove spoofable generic view acceptance

In `run_target_size_eval2_reduction()` remove the branch that accepts an arbitrary object merely because it has `evaluation_view_digest == expected`.

Accepted alternatives are:

1. preferred: no external view argument on the production reduction path; construct the authenticated view internally from the exact-M artifact/root; or
2. accept only `TargetSizeAuthenticatedEvaluationView` and fully verify all of its bound fields against the `TargetSizeEvaluationArtifact` before using its underlying view.

`SimpleNamespace`, generic `EvaluationDatasetView`, or any unrelated object with copied digest/count attributes must fail with `TrainingDataInputError`.

## A4. Finish P1/export-policy re-derivation for exact-M and TRAIN2 artifacts

`validate_target_size_evaluation_artifact()` must compare each sidecar record to `canonical_frame_authority.frame(uid)` rather than merely checking that the record is non-empty. At minimum compare all governed identity fields emitted by the exporter:

- run/source frame identity;
- geometry fingerprint;
- canonical label payload digest;
- labeled-configuration fingerprint;
- selected energy/label channel;
- exact role/dataset id;
- exact ordered membership/membership digest;
- expected common-preparation semantics (`None` for EVAL2 where defined);
- exact accepted `MaceExtxyzPolicy` digest and energy/forces/stress keys.

Validate the parsed ExtXYZ payload sufficiently to prove its atom order, geometry, and label values correspond to those canonical identities. Reuse established canonical fingerprint/label helpers; do not invent a second P1 fingerprint algorithm.

Apply the same cross-binding discipline to target-train and harness-validation artifacts in `validate_target_size_extxyz_artifact()` / `validate_target_size_materialization()`. `validate_target_size_materialization()` must receive the exact accepted `MaceExtxyzPolicy`; do not silently instantiate `MaceExtxyzPolicy()` as validation authority.

### Pass-A gate

Before persistence/restart work proceeds, run focused P3D/candidate/export tests plus affected regression covering candidate materialization, snapshot inference, exact-M validation and EVAL2 reduction. The adversarial forged-view test must call the real `view=` parameter and must require `TrainingDataInputError`; accepting `TypeError` from a misspelled keyword is forbidden acceptance evidence.

---

# 2. Repair pass B — raw failure ownership and one crash-safe publication primitive

## B1. Split completion construction by scientific variant or enforce sealed variant inputs

The current generic `build_target_size_cell_completion_record()` retains too many optional authority branches. Either replace its accepted surface with variant-specific builders or make the generic function an internal dispatcher over sealed parent bundles.

Required accepted owners are conceptually:

```text
build_success_completion(... exact snapshot, role, eval artifact, prediction, metric ...)
build_train2_failure_completion(... raw TRAIN2 failure, rung, predecessor/init ancestry ...)
build_eval2_failure_completion(... snapshot, role, eval artifact, prediction, raw EVAL2 error ...)
```

Do not retain an accepted branch where a pretranslated `TargetSizeNumericalFailure` is the scientific parent.

## B2. TRAIN2 failure must be raw-evidence-only

For `train2_failure`:

- require a real `Train2NumericalFailureRecord`;
- require the exact `TargetSizeRungPlan` object/digest, not an optional bare digest;
- require either the exact predecessor continuation/snapshot ancestry for n2/n3 or an explicit authenticated initial-request ancestry for n1;
- resolve/validate the raw checkpoint bytes/SHA whenever the failure taxonomy says a checkpoint exists;
- validate failure epoch/update/rung lineage against trajectory + schedule + predecessor;
- call `translate_target_size_train2_failure()` inside the completion owner;
- allow a caller-supplied translated P2 outcome only as an optional equality assertion after internal derivation.

Delete both current shortcuts:

- `failure_record` may be `TargetSizeNumericalFailure`;
- raw TRAIN2 failure is accepted only because `outcome` was already supplied.

## B3. EVAL2 failure must bind the exact prediction attempt

For `eval2_failure`, require a real `Eval2NumericalEvaluationError` plus the exact snapshot, role, evaluation artifact and prediction evidence. Before translation require:

```text
error.target_role_digest == role.content_digest
error.prediction_digest == prediction.prediction_payload_digest
prediction.role_digest == role.content_digest
prediction.boundary_state_digest == snapshot.content_digest
prediction.evaluation_data_digest == evaluation_data.content_digest
```

Only then call `translate_target_size_eval2_failure()`.

The same prediction-digest equality must be rechecked during restart replay.

## B4. Move immutable publication to one shared persistence owner

The coordinator helper is not sufficient while exporters/config/snapshots retain different publication rules. Create one target-size persistence utility (location delegated; a small `persistence.py` under `target_size_execution` is reasonable) with two primitives:

- immutable bytes create-or-verify;
- typed JSON create-or-verify.

Required semantics for immutable bytes:

1. write complete attempt-local temp bytes;
2. flush/fsync temp file;
3. compute/validate expected SHA/content before publication;
4. acquire a per-destination or narrow-root advisory lock;
5. if destination exists, verify exact bytes/hash and reuse;
6. if absent, atomically rename complete temp into place under the lock;
7. on mismatch, fail without touching existing accepted bytes.

Required semantics for typed JSON add:

- deserialize the temp through the real type constructor before publication;
- on existing destination, deserialize/recompute the existing object and compare semantic `content_digest`;
- never trust an existing JSON object's advertised `content_digest` field by itself.

Apply the shared primitive to all P3 scientific immutable publication, including:

- target/harness/evaluation ExtXYZ;
- ExtXYZ sidecars (remove `_atomic_text_bytes()` from accepted P3 publication);
- candidate MACE config and materialization record;
- snapshot raw checkpoint, runtime summary, continuation companion and snapshot metadata;
- trajectories/materializations/snapshots/rung plans/continuations/evaluation artifacts/roles/predictions/metrics/failures/completions/progress/batches/heads.

For raw bytes such as checkpoints, exact SHA verification is the create-or-verify identity; JSON deserialization is not applicable.

## B5. Complete reducer-head CAS and idempotency semantics

Keep the narrow `.screen_commit.lock`, but make `commit_target_size_boundary_batch()` distinguish these cases under the lock:

1. **Exact retry already committed**: current head has the same batch digest, same pre-state, and deterministic post-state -> verify immutable head and return that head successfully.
2. **Normal successor**: current head post-state equals the caller/batch pre-state -> publish/verify one successor and move the pointer.
3. **Conflict/stale caller**: current head is neither the exact requested commit nor the expected parent -> fail.

Before returning success, verify the mutable current pointer represents the exact immutable head just accepted.

Differing child heads for one parent are a hard conflict even if both files exist. Identical retries converge; they must not fail merely because another caller committed the same batch first.

`initialize_target_size_screen()` retains analogous create-or-verify behavior.

### Pass-B gate

Run focused raw-failure, publication, crash-simulation and concurrency tests plus affected P3C/P3E regression. Include:

- process termination after temp completion but before publication -> no partial authoritative file;
- existing JSON with forged matching `content_digest` but invalid body -> rejected;
- conflicting ExtXYZ/sidecar/config/snapshot writers -> first valid object preserved;
- identical concurrent head commit -> both callers observe the same committed head/idempotent result;
- differing concurrent head commit -> at most one succeeds and current pointer is not overwritten;
- real EVAL2 error with foreign prediction digest -> rejected;
- raw TRAIN2 failure cannot be accepted without rung/predecessor/checkpoint validation.

---

# 3. Repair pass C — mandatory typed scientific restart authority

## C1. Introduce one non-optional restart authority

Replace the current reconciliation signature with one accepted authority bundle (name delegated; `TargetSizeRestartAuthority` is suitable) that contains or can deterministically derive:

- aggregate/definition + initial reducer state;
- execution context + common preparation;
- exact screen schedule;
- seed-neutral optimizer template and deterministic per-seed optimizer derivation;
- canonical P1 frame/numerical authority;
- exact accepted `MaceExtxyzPolicy` / EVAL2 policy;
- resolver;
- explicit bulk-root mappings for materialization, snapshot, evaluation and TRAIN2 failure/checkpoint ancestry.

The accepted reconciliation path must not permit missing P1/export/policy/root authority. `schedule` being mandatory alone is not sufficient.

Prefer:

```text
reconcile_target_size_screen_root(root, restart_authority)
```

or an equivalent signature in which all listed authority is non-optional.

## C2. Complete resolver coverage and correct directory names

`TargetSizeExecutionResolver` must resolve every parent class referenced by a completion or replay step:

- trajectory;
- materialization metadata + materialization bulk directory;
- snapshot metadata + snapshot bulk directory;
- planned rung;
- initial/predecessor continuation request or predecessor snapshot;
- evaluation artifact metadata + evaluation bulk directory;
- EVAL2 role;
- prediction evidence;
- metric;
- raw EVAL2 error;
- raw TRAIN2 failure + required checkpoint/companion bulk evidence;
- completion;
- logical progress pointer;
- batch;
- head.

Fix the current scan/path disagreement: evaluation records are published under `evaluation_artifacts/`; whole-root validation must scan the same owner path, not `evaluations/`.

Normalize relative locators and reject path traversal/out-of-root resolution for fields defined as relative.

## C3. Centralize typed content-addressed loading

Use one loader that receives expected digest + expected type/deserializer + optional bulk validator. It must prove:

```text
requested digest == filename stem
schema/type == expected type
loaded object content_digest == requested digest
required bulk locator resolves through declared root
bulk SHA/scientific validator succeeds
```

Use it for every parent class; do not hand-roll partial checks in individual replay branches.

Also validate logical progress pointer filenames by recomputing the deterministic `(window, boundary, N, seed)` key and cross-checking the referenced completion describes that exact cell.

## C4. Replay success through real scientific validators before reducer reconstruction

For every success completion, fresh replay must resolve and validate, in this order:

1. trajectory + exact per-seed optimizer policy through `validate_target_size_candidate_trajectory()`;
2. materialization/config/target/harness/P1/export policy through `validate_target_size_materialization()`;
3. exact planned rung / continuation ancestry as applicable;
4. immutable snapshot through `validate_target_size_boundary_snapshot()` and snapshot bulk hashes;
5. EVAL2 role against snapshot + exact evaluation artifact;
6. exact-M artifact through the sealed-byte/P1/export-policy validator;
7. prediction evidence against actual snapshot/provider execution identity and exact-M parent;
8. metric against role + prediction payload;
9. derive the P2 boundary metric;
10. compare the derived outcome to the serialized completion outcome only as an integrity/cache check.

Do not derive the reducer outcome merely from role/metric JSON relationships while skipping materialization, snapshot and exact-M scientific validation.

## C5. Replay TRAIN2 and EVAL2 failures from raw parents only

TRAIN2 replay:

- load/validate trajectory + materialization;
- load exact rung plan;
- load/validate predecessor/init ancestry;
- load raw `Train2NumericalFailureRecord`;
- verify checkpoint bytes/SHA when required;
- translate through the real TRAIN2 failure owner;
- compare to completion outcome.

EVAL2 replay:

- execute all successful pre-prediction ancestry validation through exact-M/prediction evidence;
- load raw `Eval2NumericalEvaluationError` as a typed object;
- require its prediction digest equals the exact prediction evidence payload digest;
- translate through the real EVAL2 failure owner;
- compare to completion outcome.

Delete restart fallbacks that deserialize a persisted `TargetSizeNumericalFailure` and treat it as raw authority.

## C6. Missing-current repair occurs only after complete root validation

Before repairing `current_head.json` or committing an orphan complete batch:

- validate all immutable heads/batches/completions and their filename/content identity;
- reject forks/orphans/conflicting logical-cell completions;
- replay the unique committed head chain scientifically;
- establish the exact current pre-state;
- validate any candidate uncommitted batch and its complete parent evidence against that state.

Only then use the normal locked CAS owner to repair/advance the pointer. A batch with an unrelated pre-state must not be ignored during root validation and later become accidental authority.

### Pass-C gate

Run focused resolver/reconciliation adversarial tests plus complete affected P3E restart regression. At minimum delete/rename/tamper each parent category one at a time and prove restart fails closed. Include filename/content-digest mismatches for trajectory, materialization, snapshot, role, evaluation artifact, prediction, metric/error, raw failure, rung, continuation, completion, batch and head.

---

# 4. Repair pass D — proxy-proof fresh-process assembled acceptance

## D1. Process B must resume through production durable ancestry, not harness path knowledge

Keep the A/B/C subprocess structure, but remove harness-side reconstruction that knows `lane-{size}-{seed}`, `mat-{size}-{seed}`, previous-boundary arithmetic, or other private persistence conventions.

Required path:

```text
Process A
  build external fixture authorities
  execute n1 through real owners
  persist complete parent graph + batch/head
  exit

Process B
  rebuild only the external P1/P2/config authorities
  construct TargetSizeRestartAuthority
  reconcile from the screen root
  ask the production continuation/resume owner to resolve each surviving candidate's
    trajectory/materialization/predecessor snapshot or continuation from durable roots
  continue n2/n3
  persist terminal head
  exit

Process C
  rebuild external authorities again
  full scientific reconcile/replay from initial reducer state only
  reproduce identical terminal head/state
```

The test harness may select a bounded dataset and fake expensive forward **below the authenticated provider owner**, but it may not reimplement resolver path conventions, continuation ancestry selection, or restart state reconstruction.

If no production resume helper currently exists, implement the minimum owner needed by the P3 runtime rather than reproducing that logic in the test.

## D2. Fix the forged-view adversarial test

The P3A4 test currently passes `evaluation_view=fake_view` to a function whose parameter is `view`, and accepts `TypeError`. Replace it with the real call:

```text
run_target_size_eval2_reduction(..., view=fake_view)
```

and require `TrainingDataInputError` specifically. This test must fail against the current generic-view fallback and pass only after A3 is implemented.

## D3. Add fresh-process TRAIN2-failure assembled acceptance

Create a bounded subprocess scenario in which Process A or B produces a real `Train2NumericalFailureRecord` through the accepted TRAIN2 numerical-failure owner, with actual checkpoint evidence when required by that failure code. Complete the full active boundary matrix, commit it, exit, then reopen in a fresh process and scientifically derive the same P2 failure/reducer transition from raw ancestry.

No `_failure_record(... sha='a'*64)`, manually fabricated placeholder SHA, or manual pretranslation can be the acceptance owner.

## D4. Add fresh-process EVAL2-failure assembled acceptance

Create an authenticated snapshot + exact-M + prediction attempt, cause the real EVAL2 owner to emit a numerical error bound to that prediction digest, let the completion owner derive the P2 failure, complete/commit the matrix, exit, then fresh-process replay and reproduce the reducer transition.

## D5. Required adversarial matrix after the repairs

Ensure the final P3F acceptance contains direct tests for all still-material escape hatches:

- authenticated provider state differs from state used for forward;
- EMA parameter cardinality/order/shape/dtype mismatch;
- prediction execution provenance claims a policy different from the actual provider;
- arbitrary object carries the **correct** view digest;
- ExtXYZ changes between authentication and parse/reduction;
- sidecar has correct UIDs but foreign canonical geometry/label identity;
- target/harness artifact is self-consistent but carries foreign role/dataset/common/export policy;
- raw TRAIN2 failure is paired with wrong rung/predecessor/checkpoint SHA;
- EVAL2 error has correct role but foreign prediction digest;
- typed resolver parent is valid internally but stored under the wrong digest filename;
- logical progress pointer is renamed to another cell key;
- immutable publisher is interrupted before commit and exposes no partial final object;
- conflicting concurrent initializer;
- identical concurrent head commit converges;
- differing concurrent head commit cannot both report success;
- current pointer missing while orphan/fork/conflicting evidence exists -> no repair.

---

# 5. Required implementation order and acceptance gate

Implement in this order because each pass supplies the trustworthy owner needed by the next:

1. **A — provider/exact-M owner**
2. **B — raw failure + publication/CAS owner**
3. **C — mandatory full scientific restart**
4. **D — fresh-process assembled closure**

After every pass, run focused tests and stage-local affected regression before continuing. After all executable edits:

- reconcile the full cumulative P3 revision-7 contract against the source;
- re-derive the affected surface;
- run the complete P3 affected regression set (P3A through P3F and directly affected shared provider/export/TRAIN2 tests);
- run assembled integration through the fresh-process success, TRAIN2-failure and EVAL2-failure paths;
- run broader repository regression if impact cannot be bounded confidently.

Full long GPU/production qualification remains deferred to final release. Bounded CPU/provider-compatible MACE tests are sufficient for P3 functional closure when they exercise the real provider/state-loading owner.

P3 passes only when all six P3A4 blockers are structurally closed and the real fresh-process owner cannot produce a green result while provider state, exact-M identity, publication durability, raw failure ancestry, or restart reconstruction is broken.