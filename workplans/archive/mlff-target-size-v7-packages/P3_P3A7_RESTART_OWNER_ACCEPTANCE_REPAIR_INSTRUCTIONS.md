---
kind: implementation-repair-instructions
package_id: CODE-MLFF-TARGET-SIZE-V7-P3-P3A7-RESTART-OWNER-ACCEPTANCE-REPAIR
governing_package_id: CODE-MLFF-TARGET-SIZE-V7-P3-P3A6-FINAL-ACCEPTANCE-REPAIR
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
status: active
package_revision: 7
reviewed_implementation_commit: faf9830d3b22048a18bb6180c95fbf673606e74f
reviewed_implementation_label: P3A7
---

# P3 revision-7 P3A7 restart-owner acceptance repair instructions

## 0. Authority, diagnosis, and narrow scope

This file is a **cumulative implementation-repair amendment within P3 revision 7**. It does not create revision 8, does not change target-size scientific policy, and does not reopen any frozen V7 architecture, statistics, checkpoint semantics, provider ownership, persistence topology, or reducer behavior.

Independent review of `faf9830d3b22048a18bb6180c95fbf673606e74f` (`P3A7`) found that the two substantive P3A6 defects are closed:

- candidate construction and validation now share the single canonical `target_size_evaluation_model_state(optimizer_policy)` authority;
- the real pinned MACE 0.3.16 `CheckpointHandler.save(CheckpointState(...))` path is exercised under real EMA parameter substitution, including divergent live-vs-shadow state and canonical EMA/LIVE no-override inference.

The **only known remaining blocker is acceptance evidence**: the durable-tamper test invokes `validate_target_size_candidate_trajectory(...)` directly. That proves the validator itself, but it does not prove the production restart/resume consumer reaches that validator. A direct helper test could remain green if the restart owner stopped calling the validator.

Current source inspection indicates the product wiring is already correct: the restart lineage owner loads the durable trajectory and calls `validate_target_size_candidate_trajectory(...)`. Therefore the default implementation for this amendment is **test-only**. Modify product code only if the required owner-level test reveals that the real restart path does not in fact reach the canonical validator.

Preserve all P3A7 product behavior unless such evidence requires a smallest owning-layer correction. In particular preserve:

- `target_size_evaluation_model_state(optimizer_policy)` as the sole EMA/LIVE authority;
- exact canonical validation in `validate_target_size_candidate_trajectory(...)`;
- TRAIN2 checkpoint-state provenance independent of evaluation choice;
- real MACE checkpoint-owner acceptance and divergent live/shadow coverage;
- one real provider/model owning state authentication, transition, provenance, and forward;
- exact-M, parent-graph, immutable publication, CAS/locking, failure, restart, and reducer closures from prior P3 revision-7 amendments.

P4 remains blocked until this owner-level acceptance closes and the cumulative P3 revision-7 exit gate passes.

---

# 1. Frozen acceptance claim and semantic owner

## 1.1 Claim to prove

The missing claim is:

```text
A durable EMA-enabled candidate trajectory whose self-digest and all restart-facing
content-addressed references have been recomputed consistently, but whose
`evaluation_model_state` has been changed from canonical `ema` to noncanonical
`live`, is rejected by the real production restart/resume path specifically when
that path re-authenticates the trajectory against the canonical optimizer policy.
```

The scientific invalidity under test is **only** the EMA/LIVE policy mismatch. The fixture must not obtain a pass by failing earlier on stale content digests, wrong filenames, broken CAS references, type/schema errors, missing files, or an intentionally inconsistent materialization/snapshot binding.

## 1.2 Required real semantic owner

The required owner for this repair is:

```python
resolve_target_size_candidate_for_resume(...)
```

using the real `TargetSizeRestartAuthority` and typed `TargetSizeExecutionResolver` on a real durable screen root.

This owner is preferred over a direct call to `validate_target_size_candidate_trajectory(...)` because it performs the production restart/resume handoff:

```text
authenticated reducer state
  -> durable progress pointer
  -> durable completion record
  -> typed content-addressed trajectory
  -> optimizer policy reconstructed from restart authority
  -> canonical trajectory validation
  -> materialization / predecessor snapshot / continuation workspace
```

The test must invoke `resolve_target_size_candidate_for_resume(...)` itself. Calling `_validate_replayed_candidate_lineage(...)`, `validate_target_size_candidate_trajectory(...)`, `TargetSizeCandidateTrajectory.from_dict(...)`, or another downstream helper directly is useful supporting coverage but **cannot close this amendment**.

## 1.3 Why an authenticated state may be supplied

Construct and reconcile a valid screen through exactly the first P3 boundary `n1` before tampering. Capture the resulting authenticated post-`n1` reducer state. After the root has been proven valid, that already-authenticated state may be passed as the `state=` argument to `resolve_target_size_candidate_for_resume(...)`.

This deliberately isolates the owner under acceptance. It avoids forcing the negative fixture to rewrite reducer-head history merely to test trajectory re-authentication, while still exercising the real durable candidate-resume consumer. The state must come from the real successful `n1` commit/reconciliation path; it may not be hand-constructed or copied from an expected-value fixture.

---

# 2. Exact adversarial durable fixture

Use an EMA-enabled P3 screen and one candidate that survives the first boundary so the next active boundary is `n2`.

## 2.1 Establish a valid control root first

Before any adversarial mutation:

1. Build the ordinary bounded P3 test environment using the same real screen/window/restart-authority machinery already used by P3-E/P3-F acceptance.
2. Execute/materialize one required candidate through `n1` using the existing bounded TRAIN2 fixture.
3. Promote the real `n1` boundary snapshot.
4. Create/publish its normal success completion through the existing P3 publication path.
5. Commit the complete `n1` boundary batch through the real reducer owner.
6. Call `reconcile_target_size_screen_root(...)` and require success.
7. Save the returned `post_state` as `authenticated_n1_state`.
8. Confirm the target candidate remains an active `(N, seed)` cell at `n2`.

The negative test may reuse existing P3-F/P3-E helpers, but the actual window, progress, completion, trajectory, materialization, snapshot, reducer state, resolver, and restart authority must be real production types/paths.

## 2.2 Create a recomputed noncanonical trajectory

Load the candidate's durable trajectory through its real typed CAS path. Starting from that valid serialized payload:

```text
evaluation_model_state: "ema" -> "live"
remove old content_digest
reconstruct with TargetSizeCandidateTrajectory.from_dict(...)
```

Required assertions before publication into the adversarial graph:

- optimizer policy in the restart authority still has `ema=True`;
- the tampered trajectory remains schema-valid;
- its target size, optimizer seed, memberships, context, realization, candidate training protocol, and all non-evaluation fields are unchanged;
- its new `content_digest` differs from the canonical trajectory digest solely because the serialized scientific state changed;
- it round-trips through `to_dict()` / `from_dict()`.

Write it at the canonical resolver path:

```text
trajectories/<tampered_trajectory_digest>.json
```

Do not overwrite the payload under the old digest and do not retain the old digest inside the new object.

## 2.3 Re-key the materialization to the tampered trajectory

The resume owner validates candidate lineage after trajectory validation. The fixture must therefore not contain a deliberately stale materialization binding that could mask the intended policy failure.

Load the real durable `TargetSizeCandidateMaterialization`, change only:

```text
trajectory_digest -> tampered_trajectory.content_digest
```

remove its old `content_digest`, reconstruct through `TargetSizeCandidateMaterialization.from_dict(...)`, and publish it at:

```text
materializations/<tampered_materialization_digest>.json
```

Do **not** rewrite ExtXYZ bytes or MACE config bytes. Changing EMA/LIVE evaluation representation does not change candidate training membership, optimizer training policy, seed, MACE training config, or exported data. The re-keyed materialization must still bind the same real output directory and exact same authenticated data/config artifacts.

## 2.4 Re-key the predecessor boundary snapshot

Load the real successful `n1` `TargetSizeBoundarySnapshot`. Change exactly:

```text
trajectory_digest      -> tampered_trajectory.content_digest
evaluation_model_state -> "live"
```

Remove its old `content_digest`, reconstruct through `TargetSizeBoundarySnapshot.from_dict(...)`, and publish at:

```text
snapshots/<tampered_snapshot_digest>.json
```

Keep the real snapshot bulk directory and all raw TRAIN2 files unchanged. The raw checkpoint, runtime summary, companion SHA, optimizer/live/EMA/RNG digests, completed updates, rung plan, and snapshot bulk bytes are not corrupted by this fixture.

The snapshot remains structurally valid because live evaluation is a representational field; the invalidity is that the governing EMA-enabled P3 policy does not permit this trajectory/snapshot convention.

## 2.5 Re-key the previous-boundary completion record

Load the real successful `n1` `TargetSizeCellCompletionRecord` for the selected candidate. Change only the restart-facing identities required by the adversarial graph:

```text
trajectory_digest         -> tampered_trajectory.content_digest
materialization_digest    -> tampered_materialization.content_digest
boundary_snapshot_digest  -> tampered_snapshot.content_digest
```

Leave the previously authenticated outcome, planned rung, exact-M/EVAL2 evidence, and all other scientific parent digests unchanged. Remove the old `content_digest`, reconstruct through `TargetSizeCellCompletionRecord.from_dict(...)`, and publish to its canonical completion CAS path.

This test is not claiming that the tampered completion is a publishable new scientific result; it is constructing a hostile durable restart graph to prove that restart re-authentication rejects noncanonical scientific state. Direct test-fixture serialization is therefore allowed here, exactly as controlled corruption is allowed in negative checkpoint tests. Production publication code must not be weakened to create this state.

## 2.6 Re-key the logical progress pointer

Load the real logical progress record for the same `n1` cell. Change:

```text
trajectory_digest          -> tampered_trajectory.content_digest
completion_record_digest   -> tampered_completion.content_digest
```

Remove its old `content_digest`, reconstruct through `TargetSizeCandidateOutcome.from_dict(...)`, and overwrite the same deterministic logical progress path for `(window, n1, N, seed)`.

The filename must remain the real deterministic `progress_path(...)` for that cell. The progress object, completion object, materialization object, snapshot object, and trajectory object must all independently deserialize and expose the exact digests referenced by the next object in the chain.

No stale-digest or wrong-filename failure is acceptable as the expected result.

---

# 3. Mandatory owner-level negative execution

After the adversarial graph above is written, invoke:

```python
resolve_target_size_candidate_for_resume(
    root,
    restart_authority,
    boundary_epoch=n2,
    target_size=N,
    optimizer_seed=seed,
    state=authenticated_n1_state,
    workspace_root=<fresh test workspace root>,
)
```

## 3.1 Expected failure

The call must raise the established typed input-validation exception from the **canonical trajectory policy check**, with an assertion narrow enough to distinguish it from generic CAS/serialization/lineage failures. For the current implementation, match the canonical mismatch message semantically equivalent to:

```text
Trajectory evaluation_model_state 'live' does not match optimizer policy EMA convention 'ema'.
```

Do not use `pytest.raises(TrainingDataInputError)` without a discriminating message/predicate. A generic exception-only assertion could remain green if the owner stopped invoking the canonical validator and later failed for an unrelated stale parent.

## 3.2 Failure ordering / no side effects

Also assert:

- the tampered trajectory file was successfully loaded through its CAS filename/digest before rejection;
- the failure is not a `TrainingDataSerializationError`, digest mismatch, missing-file error, or wrong-path error;
- no continuation workspace for the `n2` resume is created/populated after rejection;
- no boundary state, EVAL2 role, prediction, completion, reducer batch, or reducer head is published as a consequence of the rejected resume.

The test does not need to instrument private helpers. Observable exception identity/message plus absence of the resume workspace is sufficient.

## 3.3 Proxy-proof counterfactual

The fixture must be constructed so that the restart-facing lineage immediately following trajectory validation is otherwise coherent:

- progress -> completion digest matches;
- completion -> trajectory/materialization/snapshot digests match;
- materialization -> tampered trajectory digest matches;
- snapshot -> tampered trajectory digest and `live` evaluation state match;
- underlying materialization and snapshot bulk bytes remain the original authenticated bytes.

This ensures the evidence is aimed at the canonical policy handoff rather than an accidental malformed-CAS rejection. Do not satisfy this repair by leaving `materialization.trajectory_digest` or `snapshot.trajectory_digest` stale and merely matching the expected exception type.

---

# 4. Product-code authority during implementation

## 4.1 Default: no production change

P3A7 source inspection already shows restart lineage validation calls the canonical trajectory validator. If the owner-level test above passes on current product code, do not add another validator call, wrapper, compatibility path, special-case rejection, or duplicate EMA/LIVE table.

The intended implementation in that case is:

```text
add/replace acceptance test
+ preserve existing product code
+ run required regression
```

## 4.2 If the owner-level test exposes a real wiring gap

Only if the required test proves that `resolve_target_size_candidate_for_resume(...)` can consume the tampered trajectory without reaching canonical validation may product code change.

Then make the smallest owning-layer repair so the existing shared `validate_target_size_candidate_trajectory(...)` is reached before materialization/snapshot/workspace authorization. Do not copy the EMA/LIVE rule into coordinator/restart code. The single canonical validator remains the scientific authority.

Any product-code edit invalidates affected restart/replay evidence and therefore requires the complete affected P3 regression in section 5.2.

---

# 5. Acceptance and regression

## 5.1 Focused closure gate

The next implementation must execute and pass, on the same candidate commit:

1. the new real-owner durable-tamper `resolve_target_size_candidate_for_resume(...)` negative test above;
2. the existing direct canonical trajectory builder/validator tests;
3. canonical EMA no-override real-MACE direct inference;
4. canonical non-EMA LIVE no-override real-MACE direct inference;
5. real `CheckpointHandler.save()` divergent live-vs-shadow checkpoint semantics;
6. TRAIN2 raw-checkpoint role-validator independence tests.

The owner-level test must not be skipped, xfailed, replaced by a direct helper invocation, or reduced to a generic exception assertion.

## 5.2 Affected regression gate

If this amendment changes **tests only** and product source is byte-identical to P3A7, previously executed broader P3A7 regression evidence remains valid where it is available and attributable to the same product tree. Nevertheless rerun the high-signal restart/replay surface containing the new test, including the relevant P3-E/P3-F candidate-resume/reconciliation tests, to establish the new evidence on the current commit.

If any product code changes, rerun the complete affected P3 surface required by the P3A6 amendment, including at minimum:

- candidate trajectory/context/materialization validation;
- TRAIN2 continuation persistence/restore and checkpoint authentication;
- P3-C boundary/snapshot continuation;
- direct EVAL2/provider inference;
- P3-E publication, candidate resume, reconciliation and replay;
- P3-F bounded assembled success/restart/failure replay;
- P3A4/P3A5/P3A6 real-provider, checkpoint-owner, exact-M, parent-publication and restart closures;
- shared MACE provider tests only if shared provider code changes.

No full long GPU/production qualification is required. It remains deferred to final release.

## 5.3 Structural/conformance closure

Before handoff, inspect the final candidate and establish:

1. `target_size_evaluation_model_state(optimizer_policy)` remains the sole EMA/LIVE derivation authority;
2. `validate_target_size_candidate_trajectory(...)` still re-derives exact canonical state;
3. `resolve_target_size_candidate_for_resume(...)` reaches that shared validator through production replay lineage before authorizing continuation workspace state;
4. no duplicate EMA/LIVE rejection table was added to coordinator/restart code;
5. the new acceptance test invokes the real public restart/resume owner and not `_validate_replayed_candidate_lineage(...)` or the validator directly as its acceptance action;
6. the tampered durable graph recomputes and follows real CAS/schema identities for trajectory, materialization, snapshot, completion, and progress;
7. the expected failure specifically identifies canonical evaluation-state mismatch;
8. all prior P3A7 checkpoint/provider and P3A5/P3A6 persistence/restart closures remain intact.

---

# 6. Revised P3 exit condition

The cumulative P3 revision-7 implementation may claim **P3 PASS** after this repair only when:

```text
all P3A7 substantive product fixes remain closed
AND canonical builder/validator state authority remains unique
AND real MACE checkpoint-owner / divergent EMA semantics remain accepted
AND a self-consistent recomputed durable LIVE-under-EMA trajectory reaches
    resolve_target_size_candidate_for_resume(...)
AND that real owner rejects specifically at canonical trajectory policy validation
AND no continuation workspace or downstream scientific state is authorized
AND required focused + affected regression evidence passes
AND no new independent material issue is discovered
```

When those conditions are satisfied, the acceptance blocker identified in the P3A7 review is closed. No additional P3 implementation round is required merely for process ceremony; P3 revision 7 is eligible for final PASS and P4 may proceed.

---

# 7. Implementation authority

## Frozen

- P3 remains revision 7.
- EMA-enabled target-size trajectories evaluate canonical EMA; non-EMA trajectories evaluate canonical LIVE.
- the shared trajectory validator is the sole scientific re-authentication owner for that convention.
- real restart/resume must reach that validator before durable trajectory state can authorize continuation.
- no new scientific policy, configuration axis, fallback, compatibility mode, or duplicate authority may be introduced.
- P3A7 product code should remain unchanged if the owner-level test passes without a wiring correction.
- GPU/production-scale qualification remains deferred.

## Delegated

- exact test module and helper organization;
- whether existing P3-E/P3-F fixture helpers are reused or a small dedicated fixture is extracted;
- exact temporary directory names;
- exact JSON write helper used for adversarial negative fixture serialization;
- exact assertion helper for checking that the continuation workspace remains absent.

## Reopen only on evidence

Reopen only the smallest affected design surface if:

1. the production candidate-resume path cannot be exercised with a previously authenticated reducer state and real durable P3 objects as specified;
2. source/runtime evidence proves another production restart entrypoint can authorize candidate continuation without traversing the shared canonical validator;
3. the canonical validator cannot reject the noncanonical durable state without conflicting with another frozen P3 invariant.

A difficult test fixture, a stale existing test assumption, or the convenience of adding another coordinator-level EMA/LIVE check is not a redesign trigger.
