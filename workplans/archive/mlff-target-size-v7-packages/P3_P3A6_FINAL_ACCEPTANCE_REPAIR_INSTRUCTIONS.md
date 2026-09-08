---
kind: implementation-repair-instructions
package_id: CODE-MLFF-TARGET-SIZE-V7-P3-P3A6-FINAL-ACCEPTANCE-REPAIR
governing_package_id: CODE-MLFF-TARGET-SIZE-V7-P3-P3A5-EMA-CHECKPOINT-STATE-REPAIR
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
status: active
package_revision: 7
reviewed_implementation_commit: f71e81b7df18275bce92d5d46d64d7ae466de31b
reviewed_implementation_label: P3A6
---

# P3 revision-7 P3A6 final-acceptance repair instructions

## 0. Authority, exact supersession, and scope

This file is a **cumulative implementation-repair amendment within P3 revision 7**. It does not create revision 8, does not change target-size scientific policy, and does not reopen any frozen V7 architecture or statistical decision.

It binds the two blocking findings from independent review of `f71e81b7df18275bce92d5d46d64d7ae466de31b` (`P3A6`):

1. P3A6 weakened the canonical target-size evaluation-model-state authority so an EMA-enabled optimizer could validate either `ema` or `live`, creating an unauthorized candidate-varying scientific axis.
2. The positive EMA checkpoint-semantics acceptance fixture still manually constructed a checkpoint dictionary and called `torch.save`, so it did not exercise the pinned MACE 0.3.16 checkpoint owner whose real save semantics caused the original defect.

Preserve the substantive P3A6 checkpoint-state repair. In particular, preserve:

- `verify_train2_checkpoint_model_parameters(...)` or its semantically equivalent shared TRAIN2 owner;
- EMA-present raw checkpoint parameters authenticated against authenticated EMA shadow state;
- EMA-absent raw checkpoint parameters authenticated against authenticated live state;
- strict full MACE `state_dict` loading, including buffers/architecture/key/shape/dtype checks;
- candidate-configuration-owned real MACE reconstruction;
- one provider/model instance owning state authentication, state transition, provenance and forward;
- P3A5 complete-parent-graph publication, restart, exact-M, failure, CAS/idempotency and fresh-process closures.

### 0.1 Specific correction to the preceding P3A5 repair amendment

`P3_P3A5_EMA_CHECKPOINT_STATE_REPAIR_INSTRUCTIONS.md` remains authoritative **except** for language that treated LIVE-vs-EMA as a selectable P3 trajectory choice when TRAIN2 EMA is enabled. This amendment supersedes that narrow wording.

Specifically, the following prior intent is corrected:

- the section-2 table cell that presented `TRAIN2 EMA present + trajectory requests LIVE` as an accepted P3 production mode;
- section 3.4 insofar as it implied P3 may choose LIVE when the frozen optimizer policy enables EMA;
- section 4.2's mandatory assembled `LIVE with EMA enabled` production test;
- section 4.4 item 5 insofar as it required a production LIVE-with-EMA trajectory;
- section 6 wording that could be read as making LIVE/EMA a free P3 evaluation choice.

The **underlying checkpoint-provenance invariant remains frozen**: raw MACE checkpoint parameter semantics are derived from authenticated TRAIN2 EMA presence, not from downstream evaluation-state metadata. That independence must now be proven at the TRAIN2 checkpoint-state owner boundary without weakening P3's canonical evaluation convention.

P3 remains active until this repair and final assembled P3 acceptance close. P4 remains blocked.

---

# 1. Frozen corrected authority model

## 1.1 One canonical evaluation-model-state convention

P3 already owns one canonical derivation:

```text
target_size_evaluation_model_state(optimizer_policy)
    -> "ema"  if optimizer_policy.ema is enabled
    -> "live" otherwise
```

That derivation is the sole accepted P3 evaluation-model-state authority.

Frozen consequences:

- `evaluation_model_state` is **derived scientific identity**, not caller-selectable policy;
- every candidate under the same seed-neutral optimizer policy uses the same convention;
- N, optimizer seed, restart state, caller, test fixture, worker, or persisted trajectory may not change the convention;
- an EMA-enabled P3 screen evaluates the authenticated EMA state;
- a non-EMA P3 screen evaluates the authenticated live state;
- no new configuration option, runtime flag, test-only accepted mode, or compatibility fallback may make LIVE/EMA selectable inside ordinary P3 screening.

A future requirement to evaluate LIVE while training with EMA would be a target-size scientific-policy design change and must reopen the smallest affected design surface. It must not be introduced as an implementation convenience for this repair.

## 1.2 Checkpoint-save semantics remain independent of evaluation metadata

This remains separately true:

```text
TRAIN2 EMA absent  -> raw checkpoint parameters must match authenticated live
TRAIN2 EMA present -> raw checkpoint parameters must match authenticated EMA shadow
```

The decision belongs to TRAIN2 provenance and must be based on authenticated continuation/summary EMA presence. It must not inspect `trajectory.evaluation_model_state`.

Therefore:

```text
checkpoint-save state authority != evaluation-state selection authority
```

The first is a TRAIN2 provenance fact. The second is fixed by the canonical P3 policy above. Keeping them independent does **not** imply that P3 supports two evaluation modes under one optimizer policy.

---

# 2. Repair pass A — restore canonical evaluation-state closure

## A1. Centralize construction and validation on the existing owner

`build_target_size_candidate_trajectory(...)` and `validate_target_size_candidate_trajectory(...)` must both use the existing canonical `target_size_evaluation_model_state(optimizer_policy)` owner, or one semantically identical shared owner if module direction requires relocation.

Required validator behavior:

```text
expected = target_size_evaluation_model_state(optimizer_policy)
trajectory.evaluation_model_state == expected
```

Anything else fails closed with `TrainingDataInputError` or the established typed input-validation error.

Do not retain logic equivalent to:

```text
if optimizer_policy.ema:
    accept either "ema" or "live"
```

Do not duplicate a second EMA/live policy table in candidate validation.

## A2. Re-authenticate durable/restart trajectories, not just newly built ones

Builder correctness alone is insufficient because persisted or reconstructed trajectories can be modified independently of the builder.

Every accepted production/restart path that consumes a durable or caller-supplied `TargetSizeCandidateTrajectory` must reach the canonical trajectory validator before its evaluation-state identity can authorize boundary state, snapshot, EVAL2 role, prediction, completion, or replay.

Preserve existing exact trajectory -> boundary -> snapshot equality checks. If current production orchestration already guarantees the canonical validator is executed before those owners, retain that path and prove it in tests; otherwise add the smallest owning-layer validation call needed to close the gap.

A trajectory produced by `dataclasses.replace(..., evaluation_model_state="live")` from an EMA-enabled canonical trajectory must never become accepted scientific state merely because its self-digest was recomputed.

## A3. Remove the acceptance-driven policy drift

The P3A6 positive acceptance test that mutates a canonical EMA trajectory to LIVE solely to prove checkpoint-state independence must be removed or converted to a **negative policy test**.

Allowed positive assembled production tests are now exactly:

```text
optimizer EMA enabled  -> canonical trajectory state EMA -> EMA direct inference
optimizer EMA disabled -> canonical trajectory state LIVE -> LIVE direct inference
```

Checkpoint-save/evaluation independence is proven below the scientific-policy boundary in pass B.

## A4. Mandatory acceptance evidence for pass A

Add/retain focused tests proving all of the following:

1. `build_target_size_candidate_trajectory(...)` produces `ema` when optimizer EMA is enabled.
2. It produces `live` when optimizer EMA is disabled.
3. `validate_target_size_candidate_trajectory(...)` rejects a recomputed/tampered EMA-enabled trajectory whose state is changed to `live`.
4. The same validation rejects any unsupported state string.
5. Two different N values and two different authorized optimizer seeds under the same seed-neutral optimizer policy cannot validate different evaluation-model-state conventions.
6. Restart/replay of a durable trajectory with altered evaluation-model-state fails before that altered state can authorize a boundary/EVAL2 result.
7. The real assembled no-override direct-inference path remains green for canonical EMA evaluation with EMA enabled.
8. The real assembled no-override direct-inference path remains green for canonical LIVE evaluation with EMA disabled.

A positive test that bypasses canonical validation by mutating `trajectory.evaluation_model_state` cannot establish assembled P3 acceptance.

---

# 3. Repair pass B — prove EMA checkpoint semantics through the real pinned MACE owner

## B1. Required semantic owner

The positive checkpoint-semantics fixture must use the pinned MACE 0.3.16 checkpoint implementation itself.

The relevant owner is:

```python
from mace.tools.checkpoint import CheckpointHandler, CheckpointState
```

In pinned MACE 0.3.16:

```text
CheckpointHandler.save(...)
  -> CheckpointBuilder.create_checkpoint(...)
       -> model.state_dict()
       -> optimizer.state_dict()
       -> lr_scheduler.state_dict()
  -> CheckpointIO.save(...)
       -> torch.save(...)
```

The acceptance fixture must therefore call `CheckpointHandler.save(...)`; calling `torch.save` directly on a hand-built `{"model": ..., "optimizer": ..., "lr_scheduler": ...}` mapping is not real-owner evidence.

## B2. Exact positive fixture construction

Use a bounded CPU fixture with:

- one minimal real MACE model reconstructed through the same candidate configuration authority used by P3;
- real `torch_ema.ExponentialMovingAverage` over that model;
- a lightweight real Torch optimizer bound to the same model parameters;
- a lightweight real Torch LR scheduler bound to that optimizer;
- real MACE `CheckpointHandler` and `CheckpointState`.

Deterministically establish finite live and EMA-shadow states such that:

```text
live != shadow
```

Then save through the exact owner:

```python
handler = CheckpointHandler(directory=..., tag=..., keep=True)
with ema.average_parameters():
    handler.save(
        state=CheckpointState(model, optimizer, lr_scheduler),
        epochs=0,
        keep_last=True,
    )
```

The positive fixture must not monkeypatch or wrap away:

- `ExponentialMovingAverage.average_parameters()`;
- `CheckpointHandler.save()`;
- `CheckpointBuilder.create_checkpoint()`;
- `CheckpointIO.save()`;
- `model.state_dict()`.

No training epoch or GPU run is required. The purpose is to exercise the real serialization owner and the real EMA parameter-substitution boundary, not to qualify MACE training performance.

## B3. Mandatory fixture invariants before mdstats authentication

Load the file emitted by the real handler and assert before invoking mdstats:

1. exactly one expected checkpoint for the fixture epoch/tag is present;
2. its top-level checkpoint contract contains `model`, `optimizer`, and `lr_scheduler` entries from the real builder;
3. `checkpoint["model"]` is a state-dict mapping, not an `nn.Module`;
4. every model parameter value saved in the checkpoint exactly equals the EMA shadow value in canonical model-parameter order;
5. at least one saved parameter differs from the restored live parameter state;
6. after leaving `ema.average_parameters()`, the real MACE model parameters exactly equal the pre-context live state.

These are exact discrete/tensor-identity assertions, not tolerance-based scientific comparisons.

If any fixture invariant fails, the acceptance test must fail as an invalid reproducer rather than silently adapting expected values.

## B4. Feed the owner-produced checkpoint through the production P3 path

Use those exact owner-produced bytes as the raw TRAIN2 checkpoint supplied to the production target-size provider authentication/direct-inference path.

For the canonical EMA-enabled P3 trajectory:

```text
real MACE CheckpointHandler-produced raw checkpoint
  -> exact SHA authentication
  -> real candidate-config MACE reconstruction
  -> strict full state-dict load
  -> TRAIN2 checkpoint parameter validator proves raw == EMA shadow
  -> companion live state independently authenticated/applied
  -> EMA shadow independently authenticated/applied
  -> same provider performs tiny real CPU forward
  -> prediction provenance binds the actually forwarded EMA state
```

No forward override and no `_AuthenticatedParameterShell` are allowed in this acceptance path.

Retain the canonical non-EMA real-owner case as well:

```text
EMA absent -> real CheckpointHandler checkpoint parameters == authenticated live
```

## B5. Prove independence at the correct owner boundary

The corrected independence proof is:

- the shared TRAIN2 checkpoint-state validator takes raw model parameters + authenticated TRAIN2 companion/summary state;
- it does not take `trajectory`, `evaluation_model_state`, EVAL2 role, or another downstream evaluation selector;
- with divergent live/shadow and authenticated EMA present, the real owner-produced checkpoint succeeds because raw parameters equal shadow even though they differ from live;
- with EMA absent, the same validator requires raw parameters to equal live.

This is the required evidence that MACE checkpoint-save semantics are independent of downstream EVAL2 metadata. Do not manufacture a scientifically invalid LIVE-with-EMA trajectory to prove this property.

## B6. Negative tests may mutate a real owner-produced checkpoint

For negative rejection tests, it is acceptable to load/copy the **real owner-produced checkpoint**, mutate one controlled field/value, and serialize the corrupt copy for the sole purpose of proving rejection.

Required negative coverage includes:

1. EMA enabled: same keys/shapes/dtypes but one raw checkpoint parameter value differs from authenticated shadow -> reject before forward.
2. EMA disabled: same keys/shapes/dtypes but one raw checkpoint parameter value differs from authenticated live -> reject.
3. Altered live companion without matching authenticated summary -> reject.
4. Altered EMA shadow/cardinality/order/shape/dtype -> reject.
5. Architecture/state-dict incompatibility remains rejected.
6. No-override synthetic-shell fallback remains impossible.

Manual `torch.save` of a hand-built checkpoint is permitted only for an explicitly negative corrupt-copy test derived from an owner-produced valid checkpoint. It cannot serve as positive semantic-owner evidence.

---

# 4. Stage-local and final acceptance gates

This repair is one coherent material behavior/evidence stage. Do not split it into additional scientific gates.

## 4.1 Stage-local focused gate

Before claiming the repair stage closed, execute all of:

- canonical trajectory construction/validation tests from A4;
- divergent live-vs-shadow real MACE `CheckpointHandler.save()` reproducer;
- canonical EMA no-override direct inference using the owner-produced checkpoint;
- canonical non-EMA LIVE no-override direct inference;
- checkpoint-state role mismatch negatives from B6;
- affected TRAIN2 checkpoint/continuation and provider state-loading tests.

A required test that is skipped, xfailed, substituted with a hand-built checkpoint, or run only through a forward override is **not passed evidence**.

## 4.2 Affected regression gate

Run the affected P3 regression surface after the executable changes, including at minimum:

- candidate trajectory/context/materialization validation;
- TRAIN2 continuation persistence/restore and checkpoint authentication;
- P3-C boundary/snapshot continuation tests;
- direct EVAL2/provider inference tests;
- P3-E publication/replay tests that re-authenticate scientific parents;
- P3-F fresh-process success/restart/failure replay tests;
- P3A4/P3A5 real-provider, exact-M, parent-publication and restart closure tests;
- shared MACE provider/hot-swap architecture tests if shared provider code changes.

Use the broader available affected suite if impact cannot be bounded confidently.

## 4.3 Final structural/conformance inspection — mandatory

Before handoff, inspect the assembled source and tests and establish all of the following absence/uniqueness claims:

1. no accepted candidate validator contains logic equivalent to `EMA enabled -> accept both live and ema`;
2. construction and validation derive evaluation-model-state from one canonical policy owner;
3. no public/runtime/test-only switch introduces a second accepted P3 evaluation-state authority;
4. the TRAIN2 checkpoint-state validator does not depend on trajectory/EVAL2 evaluation choice;
5. the positive real-owner acceptance fixture calls MACE `CheckpointHandler.save()` and does not manually construct the checkpoint mapping it is supposed to validate;
6. the positive canonical EMA assembled test does not mutate the trajectory to LIVE;
7. one real provider/model still owns reconstruction, strict raw-state load, live/EMA state transitions, provenance and forward;
8. P3A5 complete-parent publication/restart/CAS/exact-M/failure closures remain intact.

## 4.4 P3 exit condition after this repair

The next implementation round may claim **P3 PASS** only if all conditions below are simultaneously true:

```text
canonical evaluation-state authority restored
AND durable/restart trajectory tampering rejected
AND shared TRAIN2 raw-checkpoint role validator preserved
AND real MACE CheckpointHandler/CheckpointBuilder positive fixture executed
AND real fixture proves checkpoint params == shadow != live under EMA
AND canonical EMA no-override tiny CPU inference passes
AND canonical non-EMA LIVE no-override tiny CPU inference passes
AND focused + complete affected regression passes
AND final source/conformance inspection finds no alternate scientific authority or proxy acceptance
```

If these conditions pass and no new independent material issue is discovered, the two P3A6 blockers are closed and P3 revision 7 is eligible for final PASS. P4 may then proceed according to the package sequence.

Full long GPU/real-production qualification remains deferred to final release. Do not add GPU qualification to this repair gate.

---

# 5. Implementation sequence

Implement in this order because it removes the scientific-policy drift before rewriting acceptance around the corrected boundary:

1. Restore canonical evaluation-model-state derivation/validation and remove the EMA-enabled LIVE acceptance path.
2. Convert the former LIVE-with-EMA positive assembled test into canonical-policy negative coverage or delete it if redundant.
3. Replace the positive manually serialized EMA checkpoint fixture with the real pinned MACE `CheckpointHandler.save()` fixture.
4. Reuse that owner-produced valid checkpoint for canonical EMA assembled inference and for controlled corrupt-copy negative cases.
5. Run the stage-local focused gate.
6. Run final affected P3 regression and conformance inspection on the assembled candidate.

Do not modify unrelated target-size science, reducer rules, fidelity/evaluation ladders, exact-M membership, resource policy, persistence topology, or P4/P5/P6 semantics.

---

# 6. Implementation authority and reopen conditions

## Frozen

- P3 remains revision 7.
- EMA-enabled target-size trajectories evaluate EMA; non-EMA trajectories evaluate LIVE.
- that convention is one study-wide derived authority, not candidate-selectable state;
- raw checkpoint parameter role is derived from authenticated TRAIN2 EMA presence and is independent of downstream evaluation metadata;
- real MACE 0.3.16 checkpoint-owner execution is mandatory positive acceptance evidence;
- one real provider owns state authentication and forward;
- all previously closed P3A5/P3A6 provider, publication, restart, exact-M and failure semantics remain preserved.

## Delegated

- exact test helper names and fixture module organization;
- lightweight optimizer/scheduler classes used solely to satisfy real `CheckpointState` in the bounded checkpoint-owner fixture;
- exact tiny CPU geometry;
- whether the canonical evaluation-state helper remains in `execution.py` or moves to another single shared owner, provided dependency direction remains clean and there is still exactly one authority;
- negative-test corrupt-copy serialization mechanics.

## Reopen only on evidence

Reopen only the affected design surface if:

1. the installed/pinned MACE 0.3.16 checkpoint API materially differs from `mace.tools.checkpoint.CheckpointHandler/CheckpointState` and the actual TRAIN2 owner cannot be exercised as specified;
2. representative production evidence proves P3 genuinely requires LIVE evaluation while training with EMA, which would be a scientific-policy change rather than this implementation repair;
3. the accepted production path can consume durable trajectories without any legitimate point at which canonical trajectory policy can be authenticated, requiring a broader ownership correction.

If the exact MACE API differs only mechanically, adapt the fixture to the actual pinned real owner and preserve the same semantic boundary; do **not** fall back to manual checkpoint reconstruction.
