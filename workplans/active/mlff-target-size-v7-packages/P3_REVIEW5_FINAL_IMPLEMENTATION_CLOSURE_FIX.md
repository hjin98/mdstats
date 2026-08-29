---
kind: implementation-package-amendment
package_id: CODE-MLFF-TARGET-SIZE-V7-P3-REVIEW5
amends_package_id: CODE-MLFF-TARGET-SIZE-V7-P3
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 3
status: active
package_revision: 7
amended_date: 2026-08-28
blocked_implementation_commit: d054c719a2a4a37f38cf200ef5918f39a128a592
---

# P3 Review-5 final implementation-closure amendment — single evaluated model, sealed exact-M input, crash-safe publication, and mandatory scientific replay

## 0. Authority and routing

This is a **cumulative precision amendment** to P3 revision 6 after independent review of `d054c719a2a4a37f38cf200ef5918f39a128a592` (`P3A3`). It does not reopen the V7 architecture or change P1/P2/P3-A/B/C scientific semantics. It makes previously implicit consequences explicit so an implementation cannot satisfy local checks while still bypassing the protected owner/provenance/restart outcome.

P3 revision 7 is therefore:

1. `P3_CANDIDATE_EXECUTION_PAIRED_SCREEN.md`;
2. `P3_REVIEW2_AUTHENTICATED_EVAL_RESTART_FIX.md`;
3. `P3_REVIEW3_EXECUTION_OWNER_IMMUTABILITY_CLOSURE_FIX.md`;
4. `P3_REVIEW4_FINAL_OWNER_REPLAY_CLOSURE_FIX.md`; and
5. this amendment.

Review-2/3/4 remain authoritative. Where this amendment is more specific, it controls the implementation consequence. These are implementation nonconformances exposed by `P3A3`, not a new scientific design. P4 remains blocked until cumulative revision-7 P3 passes.

---

# 1. Frozen anti-shortcut invariants

The final implementation must make all of the following structurally true, not merely true in the happy-path test fixture:

- the **same provider/model instance whose parameter state is authenticated is the instance that performs the production forward**;
- accepted `TargetSizeEval2Role` identity always includes one exact immutable boundary snapshot and one exact evaluation-artifact digest; neither parent is optional;
- the bytes/labels consumed by inference and EVAL2 reduction are the bytes authenticated for the exact-M artifact; validation and consumption may not observe two different file states;
- no caller-supplied object can become an authenticated evaluation view merely by carrying a matching digest attribute;
- success, TRAIN2-failure and EVAL2-failure completions are constructed only from their raw immediate scientific parents; a pretranslated `TargetSizeNumericalFailure` or serialized outcome is never sufficient authority;
- every content-addressed load verifies schema/type, filename digest, object digest, and required bulk bytes/locator before use;
- no accepted scientific file is published through check-then-replace, last-writer-wins replacement, or direct partial writing into its final authoritative pathname;
- reducer-head/current-pointer advancement is serialized/CAS-protected so two callers cannot both report successful advancement from the same pre-state;
- restart has no optional schedule/policy/P1/export/root authority path and no missing-parent fallback;
- final acceptance crosses an actual fresh-interpreter boundary and proves mid-screen continuation from durable ancestry, not only terminal reread.

---

# 2. P3-D precise repair instructions

## D-R5.1. One authenticated provider instance owns load + state + forward

Replace the current two-object pattern in `run_target_size_direct_boundary_inference()` where one object/checkpoint is inspected for live/EMA digest and a separately constructed `MaceCalculatorProvider` performs `predict_batch()`.

Required end state:

1. Reconstruct/create the shared MACE provider shell from the **validated candidate materialization/configuration authority**, not from an assumption that the TRAIN2 raw checkpoint is a directly executable standalone MACE model.
2. Load the exact immutable boundary snapshot state into that provider/model through the shared provider/static-inference state-loading owner. Reuse/extract existing provider compatibility/hot-swap machinery rather than implementing another P3 state loader.
3. For `live`, recompute the canonical live parameter-state digest from the provider model after load and require equality with `snapshot.live_parameter_digest` and the runtime summary.
4. For `ema`, authenticate the complete EMA state, require exact key/order/cardinality/shape/dtype compatibility, apply every EMA value to the provider model, then recompute the canonical **actual provider model** parameter-state digest and require equality with the declared EMA evaluated-state identity.
5. Only after step 4 may the production provider execute `predict_batch()` or the test fake replace the expensive numerical-forward primitive.

The fake seam is **below the authenticated provider-state owner**. A fixture that never reconstructs/loads/authenticates the provider model does not establish this requirement.

Do not retain direct P3 `torch.load()` state interpretation as an independent scientific owner. It may be used inside the shared provider loader if that loader already owns the semantics.

### Prediction provenance consequence

`TargetSizePredictionEvidence` must additionally bind the execution realization that can change prediction semantics, using the existing shared provider/static-inference authority where available. At minimum bind/rederive:

- provider/model execution-architecture identity;
- device/default-dtype/critical-precision realization;
- acceleration/compile backend policy relevant to the provider shell;
- batching/execution-policy identity when it can affect the accepted execution path.

The evidence does not need to make harmless runtime tuning scientific identity, but it must not claim one policy while executing another.

## D-R5.2. Make exact role parents non-optional in schema and construction

`TargetSizeEval2Role` accepted P3 schema must require `evaluation_data_digest`; remove the accepted `None` state. `build_target_size_eval2_role()` must require:

- `TargetSizeBoundarySnapshot` specifically, not `TargetSizeBoundaryState | TargetSizeBoundarySnapshot`;
- one validated `TargetSizeEvaluationArtifact`;
- exact `boundary_state_digest == snapshot.content_digest`;
- exact `evaluation_data_digest == evaluation_artifact.content_digest`.

Because pre-revision-7 P3 roots are not production compatibility targets, do not preserve an optional-field fallback merely for old P3-local fixtures. Unsupported older local records may fail closed.

## D-R5.3. Seal exact-M validation to the bytes actually consumed

The current validator now checks ordered `frame_uid`, which is necessary but insufficient. Close both payload authenticity and TOCTOU.

### Full evaluation-artifact re-derivation

The accepted validator must prove:

- `role == f"eval_m{M}"` or the exact canonical evaluation role representation;
- dataset id, canonical P1 authority digest, membership digest and common-preparation semantics are exact;
- exact accepted `MaceExtxyzPolicy` identity, including energy/forces/stress keys, rather than trusting keys/digest stored by the artifact itself;
- sidecar contains exactly the expected UID set and each record equals the current P1 canonical record for geometry fingerprint, canonical label payload digest, labeled-configuration fingerprint, selected label channel(s), run/source identity where governed, and any other field used to prove the exported label identity;
- parsed ExtXYZ ordered UIDs and atom ordering are exact;
- the actual parsed geometry and label payload used by EVAL2 correspond to the canonical P1 identities represented by the sidecar/authority, not merely that the sidecar is non-empty.

Reuse canonical fingerprint/label-validation helpers where available; do not introduce a second fingerprint definition.

### Same-byte consumption

Prevent `validate(file)` followed by `read(possibly changed file)` from becoming an authority gap. Use one of these equivalent designs:

- read exact-M bytes once into an immutable validated input object, hash them, parse those same bytes for inference/reduction; or
- perform a validated read transaction that proves the SHA/order before and after the parse and rejects any change.

The exact-M payload is small enough that correctness dominates micro-optimization here.

Reduction must re-establish that the labels it consumes still correspond to `evaluation_data.sha256`/view identity. A mutation after prediction but before metric reduction must fail, not silently score against new labels.

## D-R5.4. Eliminate spoofable view provenance

Do not accept an arbitrary object merely because it has `evaluation_view_digest == expected` and a matching `configuration_count`.

Preferred end state: remove the externally supplied generic `view` from the accepted reduction path and have the reduction owner construct the EVAL2 view internally from the sealed/validated exact-M input.

If a reusable view wrapper is retained, it must be a dedicated immutable authenticated type produced only by the evaluation-artifact owner and bind at least artifact digest/SHA, exact ordered UIDs, view digest, label-key policy and count. Reduction must validate/rederive that wrapper; a `SimpleNamespace` or ordinary `EvaluationDatasetView` with copied attributes must not be sufficient.

Add an adversarial test with a **forged object carrying the correct digest**, not only missing/wrong digest.

## D-R5.5. Make completion linkage exact at construction

For `success`, the builder must require `prediction_evidence` and `eval2_metric_record` and prove all of the following before constructing the completion:

```text
role.boundary_state_digest == snapshot.content_digest
role.evaluation_data_digest == evaluation_data.content_digest
prediction.role_digest == role.content_digest
prediction.boundary_state_digest == snapshot.content_digest
prediction.evaluation_data_digest == evaluation_data.content_digest
prediction.prediction_payload_digest == metric.prediction_digest
metric.target_role_digest == role.content_digest
derived_P2_metric == completion.outcome
```

There is no outcome-only or metric-only accepted branch.

For `eval2_failure`, require a real `Eval2NumericalEvaluationError` plus the exact prediction evidence/attempt. Require:

```text
error.target_role_digest == role.content_digest
error.prediction_digest == prediction.prediction_payload_digest
prediction.role_digest == role.content_digest
prediction.evaluation_data_digest == evaluation_data.content_digest
```

Then derive the P2 numerical failure internally. Remove the accepted path where a caller supplies only a pretranslated `TargetSizeNumericalFailure`/classification digest.

---

# 3. P3-E precise repair instructions

## E-R5.1. Reuse the real optimizer/export/materialization validators

`validate_target_size_candidate_trajectory()` must call the same `validate_candidate_optimizer_policy()` authority used during trajectory construction, with the authorized seed, before accepting the realization/protocol digest. Equality of a reduced realization digest is not a substitute for full optimizer-policy conformance.

`validate_target_size_materialization()` accepted path must require current definition/common/projection derivation, exact candidate optimizer policy, canonical P1 authority and exact `MaceExtxyzPolicy`. It must not silently instantiate `MaceExtxyzPolicy()` as the validation authority.

For target/harness artifacts, validation must cross-bind the artifact + sidecar to the expected:

- role;
- dataset id;
- canonical P1 authority;
- exact ordered membership/membership digest;
- common-preparation digest semantics;
- export policy/label keys;
- per-frame canonical geometry/label identity.

Where the durable ExtXYZ itself is used as TRAIN2 input, verify enough of the actual parsed payload against its P1/sidecar identity that a coherently rewritten ExtXYZ + updated local hashes cannot become a different training dataset under the same accepted parentage.

## E-R5.2. Replace all check-then-replace writers with one crash-safe create-or-verify primitive

Create/reuse one local-filesystem publication primitive for immutable P3 scientific artifacts. Required semantics:

1. serialize/write the complete candidate bytes to an attempt-local temporary file;
2. flush/fsync the temporary file as required for process-crash safety;
3. validate/hash/deserialize the completed temporary object;
4. enter a per-object/per-cell or narrow root publication lock/CAS section;
5. if destination absent, publish the complete temporary object atomically;
6. if destination exists, verify exact identity and reuse it;
7. if destination differs, fail without altering the accepted destination.

A portable advisory `flock` around verify + rename is acceptable; an equivalent no-replace primitive is also acceptable. Lock **ownership**, not lock-file existence, owns exclusion.

Explicitly replace these current unsafe patterns:

- ExtXYZ `if exists -> compare; else os.replace(temp, target)` race;
- `_atomic_text_bytes()` unconditional replacement for sidecars;
- candidate config unconditional replacement before materialization conflict detection;
- snapshot `if exists -> compare; else os.replace()` race;
- content-addressed parent `if not path.is_file(): _atomic_json_write(...)` without existing-object verification;
- direct `O_CREAT|O_EXCL` writes into final completion/progress JSON paths, which can leave truncated authoritative files after process death;
- `screen.json`, immutable batch/head files, and any other authoritative object still using check-then-replace semantics.

For completion/progress specifically, **do not write JSON incrementally into the final exclusive pathname**. Prepare complete bytes first, then publish them under exclusion.

## E-R5.3. Serialize reducer-head advancement with expected-parent CAS semantics

`commit_target_size_boundary_batch()` must not let two callers both read one `current_head`, independently publish heads, overwrite `current_head.json`, and both return success.

Use a narrow screen-root commit lock/CAS around:

1. reload/verify current immutable head under the lock;
2. require its digest/post-state equals the caller's expected parent/pre-state;
3. create-or-verify the exact batch;
4. deterministically compute the post-state;
5. create-or-verify exactly one head for that parent/batch;
6. advance the mutable current pointer only if it still equals the expected parent;
7. return success only after the pointer represents that head.

Identical concurrent commits may converge idempotently. Differing batches/heads for one pre-state are a hard conflict; the loser must not report success. Do not hold the commit lock across TRAIN2/EVAL2 work.

`initialize_target_size_screen()` requires analogous create-or-verify semantics so concurrent differing initializers cannot last-writer-win `screen.json`.

## E-R5.4. Make failure completion constructors raw-evidence-only

### TRAIN2

The accepted `train2_failure` builder input is a real `Train2NumericalFailureRecord`, not a `TargetSizeNumericalFailure` substitute. It must also receive/resolve:

- exact attempted `TargetSizeRungPlan`;
- predecessor continuation/snapshot ancestry for later rungs, or an explicit initialization ancestry for n1;
- any checkpoint locator required by the failure taxonomy.

The builder validates the raw record against trajectory/schedule/rung/predecessor, validates recorded checkpoint bytes/SHA when the record claims a checkpoint, calls `translate_target_size_train2_failure()` itself, and uses any caller-supplied P2 outcome only as an optional equality assertion.

Delete the branch where a raw TRAIN2 record becomes admissible only because the caller already supplied `outcome`, and delete the branch accepting a pretranslated P2 failure as `failure_record`.

### EVAL2

The accepted `eval2_failure` builder requires exact snapshot + role + evaluation artifact + prediction evidence/attempt + real EVAL2 error. It validates prediction-digest equality and derives the P2 failure itself. Delete outcome-only/classification-digest fallback authority.

## E-R5.5. Make the completion graph mandatory and root-resolvable

Replace `record_candidate_boundary_outcome(... optional_parent=None ...)` with one real variant-aware publication owner or a sealed parent-bundle type. For each completion kind, every required parent must either be supplied and create-or-verified or resolved and fully verified before the completion/cell pointer is published.

The resolver must include deterministic paths/root mappings for all referenced parents, including the currently under-specified predecessor continuation ancestry. At minimum support:

- trajectory;
- materialization record + materialization bulk root;
- boundary snapshot record + snapshot bulk root;
- attempted rung plan;
- predecessor continuation/request or predecessor snapshot;
- evaluation artifact record + evaluation bulk root;
- EVAL2 role;
- prediction evidence;
- metric or EVAL2 error;
- TRAIN2 failure record + required checkpoint/companion root;
- completion, logical-cell pointer, batch and head.

Persist root mappings as execution metadata, not scientific identity. Relative locators must be normalized/root-contained; reject absolute/`..` traversal inside fields that are defined as relative locators. Absolute external roots, if supported as execution mappings, remain untrusted locators whose resolved content must pass digest/authority validation.

On identical retry, omitting parent objects is acceptable only if the publication owner resolves and fully verifies every already-persisted required parent before returning success.

---

# 4. P3-E restart/reconciliation closure

## R-R5.1. No optional restart authority

Refactor reconciliation to require one authenticated restart authority containing:

- aggregate/definition and initial reducer state;
- context/common preparation;
- exact screen schedule;
- seed-neutral optimizer template and deterministic per-seed policy derivation;
- canonical P1 frame/numerical authority;
- exact export/evaluation policy;
- resolver plus all materialization/snapshot/evaluation/TRAIN2-failure bulk-root mappings.

Remove accepted `schedule=None` behavior and any fallback that uses `record.outcome` because an authority was omitted. Missing authority is an execution/restart error.

## R-R5.2. Every resolver load is content-address verified

Centralize typed content-address loading. Every load must require:

```text
requested_digest == path.stem
loaded_object.content_digest == requested_digest
loaded schema/type == expected type
required bulk locator resolves inside its declared root
bulk hashes/validators pass
```

Apply this uniformly to role, prediction, metric, failure/error, trajectory, materialization, snapshot, rung plan, continuation, completion, batch and head. In particular:

- success replay must fail if prediction evidence is missing; `if pred_file.is_file(): validate` is forbidden;
- EVAL2 failure replay must verify both role and error object content digests, plus prediction evidence;
- batch enumeration must verify filename stem equals batch digest, not only deserialize the object;
- logical progress-pointer filename must equal the deterministic `(window,boundary,N,seed)` key and its referenced completion must describe that exact cell.

## R-R5.3. Re-run full scientific validators before outcome reconstruction

For every committed success cell, fresh replay must execute, in order:

1. trajectory re-derivation including optimizer policy;
2. materialization/config/export/P1 validation;
3. immutable snapshot/continuation validation;
4. exact role validation;
5. exact-M sealed-byte/P1/policy validation;
6. prediction evidence validation, including actual evaluated-state/provider-policy provenance;
7. metric linkage validation;
8. deterministic P2 metric derivation.

For TRAIN2 failure, replay must validate trajectory/materialization + attempted rung + predecessor + raw failure + checkpoint evidence and derive the P2 failure.

For EVAL2 failure, replay must perform the successful pre-prediction ancestry checks, validate the exact prediction attempt and raw EVAL2 error, then derive the P2 failure.

Only after this may the serialized completion outcome be compared as a cache/integrity cross-check.

## R-R5.4. Missing-current-pointer repair must validate the whole root first

When `current_head.json` is absent, do not skip head/completion conflict scanning and infer authority from batch presence.

First enumerate/validate all immutable heads, batches and completion evidence exactly as in the normal reopen path. Then:

- if there is one fully valid committed head chain and only its current pointer is missing, repair that pointer;
- if there is no committed successor but exactly one fully validated complete batch for the current replayed pre-state, it may be committed/repaired through the normal CAS owner;
- sibling/orphan/fork heads or conflicting batches/completions remain fail-closed.

A complete batch with an unrelated/unreachable pre-state must not silently sit outside the verified history and later be mistaken for authority.

---

# 5. P3-F final acceptance must be proxy-proof

Revision-7 acceptance now makes an actual subprocess/fresh interpreter mandatory because same-process retained-lane tests have repeatedly hidden the restart defects.

## F-R5.1. Mid-screen fresh-process continuation + terminal replay

Use a bounded fixture but execute at least this process boundary:

```text
process A:
  build P1/P2/P3 authorities
  run n1 complete matrix
  persist all parents/completions/batch/head
  exit without exporting Python lane/state objects

process B:
  rebuild accepted external authorities from durable fixture inputs
  reconcile from root only
  resolve surviving trajectory + immutable n1 snapshot/continuation ancestry
  continue survivors to n2/n3
  reach terminal state and persist it
  exit

process C:
  rebuild authorities again
  full scientific graph replay from initial reducer state
  reproduce identical terminal head/state
```

No `_CandidateLane`, in-memory boundary state/materialization, or inherited Python object may cross the process boundary.

## F-R5.2. Real TRAIN2-failure fresh replay

Generate a real authenticated TRAIN2 numerical-failure record with actual checkpoint evidence when required by its taxonomy. Do not use `_failure_record(... sha="a"*64)` or manual pretranslation as the acceptance owner. Commit it in a complete boundary matrix, exit, reopen in a fresh process, revalidate raw ancestry and reproduce the reducer transition.

## F-R5.3. Real EVAL2-failure fresh replay

Create an authenticated snapshot/exact-M/prediction attempt, cause the real EVAL2 owner to emit a numerical error bound to that prediction digest, let the completion owner derive the P2 failure, commit the matrix, exit, then reproduce it by fresh scientific replay.

## F-R5.4. Required newly explicit adversarial checks

In addition to revision-6 tests, add focused checks that would fail the exact P3A3 escape hatches:

- role with missing `evaluation_data_digest` is structurally inadmissible;
- role built from mutable `TargetSizeBoundaryState` is inadmissible;
- authenticated-model A / forwarding-provider B state mismatch is rejected;
- provider live/EMA state is changed after metadata authentication but before forward -> rejected;
- provider execution-policy/dtype/acceleration realization differs from prediction evidence -> rejected;
- supplied fake view carries the **correct** evaluation-view digest but is not owner-produced -> rejected;
- evaluation ExtXYZ is mutated after prediction validation but before reduction -> reduction rejects it;
- sidecar uses correct UID set but changed canonical geometry/label fingerprint -> rejected;
- target/harness artifact uses self-consistent foreign role/dataset/common/export policy -> rejected;
- trajectory is paired with an optimizer policy differing in a field outside the reduced realization -> rejected by the real optimizer-policy validator;
- raw TRAIN2 failure + caller-supplied translated outcome cannot bypass raw failure/checkpoint validation;
- EVAL2 error with correct role but foreign prediction digest is rejected by completion owner and restart;
- required success prediction record deleted -> restart fails rather than skipping validation;
- resolver file contains an internally valid object whose digest differs from its filename -> rejected for every parent class;
- batch filename/content-digest mismatch -> rejected;
- progress pointer is renamed to the wrong logical-cell key -> rejected;
- process death during completion/progress publication leaves no truncated authoritative final object;
- two concurrent screen initializers with different windows cannot last-writer-win;
- two concurrent head commits from one pre-state: identical commits converge; differing commits cannot both report success or overwrite current head;
- current pointer missing with orphan/fork evidence present -> no automatic repair.

Use bounded CPU fixtures and a small real/provider-compatible MACE model where needed to exercise the state-loading owner. No long GPU/production qualification is required.

---

# 6. Implementation order and final gate

Perform the repair in four material passes with stage-local affected regression:

1. **Single-provider + sealed exact-M owner**: provider reconstruction/state load/authentication, non-optional role parents, exact consumed-byte validation, unspoofable/internal evaluation view, prediction execution-policy provenance.
2. **Raw-evidence completion + crash-safe persistence**: full optimizer/export/materialization validation, shared create-or-verify primitive, raw TRAIN2/EVAL2 failure derivation, mandatory parent graph, logical-cell and head CAS semantics.
3. **Mandatory full scientific restart**: typed resolver loads, root mappings, no optional authority/fallbacks, full parent validators, missing-current repair after whole-root uniqueness validation.
4. **Fresh-process assembled closure**: mid-screen continuation, terminal replay, real TRAIN2/EVAL2 failure paths, adversarial matrix, fresh final affected-surface regression/integration.

P3 revision 7 passes only when a fresh process can prove every reducer input from one exact authenticated parent chain and continue/replay without retained runtime objects, while concurrent/crashed publication cannot create an accepted partial, overwritten, forked or scientifically ambiguous state.

Do not create another P3 design layer after this amendment unless implementation evidence invalidates a frozen V7 scientific/architectural decision. Otherwise remaining failures route directly to implementation repair.