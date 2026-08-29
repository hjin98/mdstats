---
kind: implementation-repair-instructions
package_id: CODE-MLFF-TARGET-SIZE-V7-P3-P3A5-EMA-CHECKPOINT-STATE-REPAIR
governing_package_id: CODE-MLFF-TARGET-SIZE-V7-P3-P3A4-FINAL-REPAIR
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
status: active
package_revision: 7
reviewed_implementation_commit: 0ae8003ad2c05c7434da92882218e32b474a50b6
reviewed_implementation_label: P3A5
---

# P3 revision-7 P3A5 EMA checkpoint-state repair instructions

## 0. Authority, scope, and disposition

This file is a **cumulative implementation-repair amendment within P3 revision 7**. It does not create revision 8, change target-size scientific policy, or reopen any frozen V7 decision.

It binds the single blocking implementation nonconformance remaining after independent review of `0ae8003ad2c05c7434da92882218e32b474a50b6` (`P3A5`). The governing authority remains the V7 parent workplan, the P3 base package, Review-2 through Review-5, `P3_P3A4_IMPLEMENTATION_REPAIR_INSTRUCTIONS.md`, and `P3_P3A4_FINAL_REVIEW_REPAIR_INSTRUCTIONS.md`.

P3A5 materially closed the previously open provider-shell reconstruction and complete-parent-graph publication defects. Preserve those closures. In particular, do not regress:

- candidate-configuration-owned reconstruction of one real MACE model/provider;
- strict loading of the real MACE 0.3.16 checkpoint `model` state dict, including buffers;
- one provider/model instance owning state authentication and numerical forward;
- no `_AuthenticatedParameterShell` fallback on a no-override production EVAL2 path;
- actual provider architecture/device/dtype/backend provenance;
- complete variant-aware parent-graph resolution and scientific replay before completion/progress publication;
- restart/reconciliation, CAS/idempotency, exact-M, raw-failure, and fresh-process closures already accepted in principle.

The remaining defect is narrower: P3A5 conflates the parameter values saved inside a MACE EMA checkpoint with mdstats' live continuation parameters.

P3 remains active until this repair and the final assembled P3 acceptance gate close. P4 remains blocked.

---

# 1. Root cause and protected concern

## 1.1 Actual MACE 0.3.16 checkpoint semantics

When EMA is enabled, the pinned MACE 0.3.16 training loop saves checkpoints while the model is inside `ema.average_parameters()`. During that context, the model parameters have been replaced by the EMA shadow values. Therefore the raw training checkpoint contains:

```text
checkpoint["model"] parameter values == EMA shadow parameters
```

for an EMA-enabled run.

After the MACE checkpoint-save context exits, the model's ordinary live optimization parameters are restored. mdstats then persists the TRAIN2 runtime companion. Consequently the durable boundary carries distinct state authorities:

```text
raw MACE checkpoint model state_dict
    parameter values = EMA shadow when EMA is enabled

TRAIN2 companion live_parameters
    parameter values = restored live optimization state

TRAIN2 companion ema_state.shadow_params
    parameter values = EMA evaluation state
```

When EMA is disabled, the raw MACE checkpoint parameters and the companion live parameters represent the same live state.

## 1.2 P3A5 defect

P3A5 reconstructs the real model correctly and strictly loads the raw state dict, but then unconditionally requires the raw checkpoint parameter digest to equal `summary.live_parameter_digest` before applying the companion live state.

That equality is valid only when EMA is disabled. For a normal EMA-enabled production boundary after live and EMA have diverged, the raw checkpoint parameters are the EMA shadow while `summary.live_parameter_digest` authenticates the restored live parameters. A valid boundary is therefore rejected before inference.

## 1.3 Protected concern

The product must authenticate **all three state roles without conflating them**:

1. raw checkpoint state must be the exact MACE checkpoint state produced at the durable boundary;
2. live continuation state must be the exact live TRAIN2 state persisted after checkpoint-save restoration;
3. EMA state must be the exact authenticated shadow state when EMA exists.

The raw-checkpoint parameter semantics are determined by whether the TRAIN2 run had EMA enabled, **not** by whether EVAL2 later chooses LIVE or EMA for evaluation.

No repair may weaken exact checkpoint SHA, architecture, state-dict key/order/shape/dtype, buffer, live-state, EMA-state, or same-provider-forward authentication merely to make the valid EMA case pass.

---

# 2. Frozen corrected state model

The implementation must preserve the following state model.

| TRAIN2 EMA state | Raw checkpoint model parameters | Final EVAL2 state if trajectory requests LIVE | Final EVAL2 state if trajectory requests EMA |
| --- | --- | --- | --- |
| absent | live parameters | live parameters | invalid: EMA state unavailable |
| present | EMA shadow parameters | authenticated companion live parameters | authenticated EMA shadow parameters |

The table separates **checkpoint-save semantics** from **evaluation-state choice**. A LIVE evaluation of an EMA-enabled run is specifically valid: its raw checkpoint still authenticates against the EMA shadow, then the same provider is restored to the authenticated live state for forward.

The following identities remain distinct:

- `summary.live_parameter_digest` authenticates the companion's live parameter payload and the provider after live state is applied;
- `summary.ema_state_digest` authenticates the accepted EMA runtime payload under its existing schema;
- the raw checkpoint SHA authenticates the complete serialized checkpoint bytes;
- the raw checkpoint model state dict must additionally be structurally compatible with the reconstructed provider and parameter-value-consistent with the checkpoint-save state described above.

Do **not** compare the raw checkpoint parameter subset to the whole `summary.ema_state_digest` if that digest covers EMA bookkeeping beyond the shadow parameters. Authenticate the raw parameter subset against `ema_state.shadow_params` directly or through one canonical parameter-only comparison owned by TRAIN2.

`ema_state.collected_params`, if represented by the existing continuation schema, is restoration/bookkeeping state. It is not the raw checkpoint model-state authority and is not the evaluated parameter state. Preserve its existing validation, but do not use it to justify raw checkpoint parameter equality.

No new persistent state digest/schema is required merely to repair this defect: the raw checkpoint, companion live parameters, EMA shadow parameters, and summary digests already provide sufficient authority. Introduce a new persisted field only if implementation evidence proves the existing durable information cannot authenticate the required relationship; such a schema change is not the default realization.

---

# 3. Required implementation consequences

## 3.1 Move checkpoint-value semantics to the TRAIN2 owner

The rule describing what MACE saved belongs to TRAIN2 runtime/checkpoint provenance, not to a P3-local inference special case.

Add or reuse one shared TRAIN2 checkpoint-state validator, preferably in `train2_runtime.py` or an existing shared TRAIN2 provenance owner, that can authenticate the raw checkpoint model parameters against the already-authenticated companion/summary state.

The target-size provider authentication path must consume that owner rather than independently hard-coding `raw checkpoint == live` or duplicating EMA checkpoint semantics.

Delegated: exact helper name and internal representation.

Frozen behavior:

- EMA absent -> raw checkpoint parameters must exactly match authenticated live parameters;
- EMA present -> raw checkpoint parameters must exactly match authenticated EMA shadow parameters;
- the decision is derived from authenticated TRAIN2 EMA presence/summary consistency, not `trajectory.evaluation_model_state`;
- an arbitrary same-architecture parameter state must not be accepted as a valid raw boundary checkpoint.

## 3.2 Preserve strict full-state-dict authentication

Keep P3A5's real provider reconstruction and strict state-dict load.

Before any numerical forward:

1. authenticate raw checkpoint bytes by the already-bound SHA-256;
2. decode the exact MACE 0.3.16 checkpoint contract;
3. reconstruct the real MACE shell from validated candidate configuration/materialization authority;
4. strictly validate/load the complete checkpoint model state dict against that shell, including exact state keys/order, tensor shapes, tensor dtypes, finite floating values, buffers, and existing execution-architecture checks;
5. authenticate the checkpoint's **parameter values** against the correct TRAIN2 state role from section 2.

The EMA repair must not become a parameter-only loader that ignores state-dict buffers or architecture.

## 3.3 Authenticate and apply live state after raw checkpoint validation

After the raw checkpoint has been authenticated as the correct boundary checkpoint state:

1. authenticate the companion `live_parameters` against `summary.live_parameter_digest` using the existing canonical TRAIN2 tensor-state owner;
2. apply the complete live state through the same `MaceCalculatorProvider` instance;
3. recompute the provider's live parameter state and require it to match the authenticated live state/digest.

This live-state application is required even when the raw checkpoint happened to contain live parameters. It keeps one explicit continuation authority and one deterministic provider-state transition.

## 3.4 Apply EMA only as the selected evaluation state

If `trajectory.evaluation_model_state == EMA`:

- require authenticated EMA state to exist;
- preserve exact shadow cardinality/order/shape/dtype/finite checks against the provider model;
- apply every EMA shadow parameter exactly once after live-state authentication;
- verify the provider's resident parameters exactly correspond to the authenticated shadow state;
- forward with that same provider/model instance.

If `trajectory.evaluation_model_state == LIVE`:

- do not apply the EMA shadow for forward, even though the raw checkpoint of an EMA-enabled run was authenticated against the shadow;
- forward with the already-authenticated live provider state.

If EMA evaluation is requested but no authenticated EMA state exists, fail closed.

## 3.5 Evaluated-state provenance remains the state that actually forwards

Prediction evidence must continue to bind the provider/model that executes numerical inference.

For LIVE evaluation, its evaluated-state identity must correspond to the provider after live parameters are applied.

For EMA evaluation, its evaluated-state identity must correspond to the provider after EMA shadow parameters are applied.

Do not substitute raw checkpoint identity for evaluated-state identity merely because the raw checkpoint happens to contain the EMA shadow under MACE's save policy.

If the existing EMA evidence digest includes continuation bookkeeping that is not resident in the forwarding model, preserve the existing durable EMA evidence linkage separately while ensuring there remains an explicit equality/digest proof of the actual resident provider parameters. Do not claim provider-state proof from non-resident `collected_params`.

## 3.6 No competing state authority or compatibility fallback

Forbidden repair shortcuts:

- removing the raw checkpoint/live relationship check entirely;
- accepting any shape-compatible state dict when EMA is enabled;
- assuming raw checkpoint state always equals EMA solely because EVAL2 requests EMA;
- assuming raw checkpoint state always equals live solely because EVAL2 requests LIVE;
- replacing strict state-dict loading with companion-only parameter loading;
- deriving architecture from checkpoint tensor structure;
- reconstructing a second model for forward after authenticating the first;
- using `_AuthenticatedParameterShell` on the no-override production path;
- changing fixtures so live and EMA are equal to avoid exercising the defect.

---

# 4. Required acceptance evidence

## 4.1 Real MACE EMA checkpoint-semantics reproducer — mandatory

Add a bounded CPU test in which live and EMA parameters are **deliberately different**.

The test must use the real pinned dependency owners for the semantic boundary being accepted:

1. construct a minimal real MACE model through the same candidate model-construction authority used by production;
2. instantiate the real EMA mechanism used by MACE/TRAIN2;
3. deterministically establish finite same-shape/same-dtype live and EMA-shadow states that are observably different;
4. create the raw MACE checkpoint through MACE's real checkpoint builder/save machinery while the model is under the real `ema.average_parameters()` context, rather than fabricating a checkpoint by simply copying the live model state;
5. prove as a fixture invariant that the saved checkpoint model parameters equal the EMA shadow and differ from the restored live parameters;
6. prove the model returns to the live state after the EMA checkpoint-save context exits;
7. provide a valid TRAIN2 companion/summary carrying the distinct live and EMA states through the existing continuation schema/validators;
8. pass the checkpoint/companion through the production target-size provider authentication path with **no forward override**.

This is bounded functional acceptance, not production qualification. No training epochs or GPU execution are required to establish the checkpoint-state invariant.

## 4.2 Production direct-inference test — LIVE with EMA enabled

Using the divergent live/EMA fixture above, execute the assembled `run_target_size_direct_boundary_inference()` path with:

```text
TRAIN2 EMA enabled
raw checkpoint parameters = EMA shadow
trajectory evaluation state = LIVE
no inference override
```

Required result:

- real MACE provider reconstruction succeeds;
- raw checkpoint authenticates against EMA shadow, not live;
- the same provider is then restored to authenticated live parameters;
- the real tiny CPU forward succeeds;
- the provider that actually forwards contains the live parameters;
- prediction evidence reports the live evaluated-state identity and actual provider execution provenance.

This case is mandatory because it proves checkpoint-state semantics are not being selected from `trajectory.evaluation_model_state`.

## 4.3 Production direct-inference test — EMA with live != shadow

Run the same assembled path with EMA evaluation.

Required result:

- raw checkpoint authenticates against the EMA shadow;
- companion live state is still independently authenticated/applied first;
- EMA shadow is then applied through the same provider;
- the real tiny CPU forward succeeds;
- the provider that actually forwards contains the exact authenticated EMA shadow;
- prediction evidence binds the actual EMA forwarding state.

The test must fail if the implementation silently forwards live parameters or a second model.

## 4.4 Negative tests

Add focused failures proving at least:

1. **EMA-enabled raw-state mismatch:** a raw checkpoint with same architecture/keys/shapes/dtypes but parameter values that differ from the authenticated EMA shadow is rejected before forward.
2. **EMA-disabled raw-state mismatch:** without EMA, a raw checkpoint whose parameters differ from authenticated live state is rejected.
3. **Altered live companion:** modifying live state without matching authenticated summary evidence is rejected.
4. **Altered EMA shadow:** modifying shadow state or its cardinality/order/shape/dtype is rejected before forward.
5. **Checkpoint semantics independent of evaluation choice:** the valid EMA-saved raw checkpoint succeeds for LIVE evaluation after live restoration; changing only evaluation choice must not change what raw state the loader expects.
6. Existing architecture mismatch, strict state-dict incompatibility, no-override synthetic-shell rejection, and model-A/model-B ownership tests remain green.

## 4.5 Anti-proxy requirement

A test in which `shadow_params` are merely clones of `live_parameters` **cannot close this repair**, even if it uses a real MACE model. Such a fixture cannot distinguish the invalid P3A5 equality assumption from correct behavior.

The acceptance fixture must assert `live != shadow` before invoking the owner under test. If that assertion is removed or false, the real-owner EMA acceptance test is invalid.

Mocks/fakes may not replace:

- MACE model construction;
- the EMA average-parameters checkpoint-save semantic boundary;
- raw checkpoint state-dict creation/authentication;
- provider reconstruction/state loading;
- evaluation-state transition;
- the provider/model that performs the accepted tiny CPU inference.

Only unrelated expensive data/training volume may be reduced.

---

# 5. Affected surface and regression gates

Expected direct owning surface:

- `mdstats/training_data/train2_runtime.py` — TRAIN2 live/EMA/checkpoint-state provenance owner;
- `mdstats/training_data/target_size_execution/evaluation.py` — provider authentication and live/EMA state transition;
- `mdstats/training_data/model_features.py` only if shared provider state-comparison/loading support is genuinely needed;
- `tests/test_mlff_target_size_p3a4_final_review.py` or its successor real-owner acceptance module.

Plausibly affected regression surface includes:

- TRAIN2 continuation persistence/restore and content-digest tests;
- MACE provider state-dict and parameter-state compatibility tests;
- target-size boundary snapshot authentication;
- P3D direct inference LIVE and EMA paths;
- P3E publication/replay because replay re-authenticates provider state;
- P3F fresh-process success/restart replay;
- existing MACE hot-swap architecture tests if shared provider machinery changes.

### Stage-local gate

After the checkpoint-state semantics repair, run:

1. the divergent live-vs-EMA real-MACE reproducer;
2. LIVE-with-EMA-enabled no-override direct inference;
3. EMA-with-divergent-shadow no-override direct inference;
4. the negative state-role matrix above;
5. affected TRAIN2/provider/P3D regression.

Do not proceed to final closure while either real no-override divergent-state case is absent, skipped, or replaced by a fixture with equal live/shadow values.

### Final assembled P3 gate

After all executable edits:

- re-run the complete affected P3 regression surface, including P3E/P3F replay paths;
- retain all P3A5 parent-publication tests and earlier revision-7 exact-M/failure/restart/CAS tests;
- inspect the final source for an unconditional raw-checkpoint-parameter == live-state assumption or an equivalent evaluation-state-driven shortcut;
- verify one real provider still owns reconstruction, state transitions, provenance, and forward;
- run repository-required checks for the affected surface.

Full long GPU/production qualification remains deferred to final release. This repair requires only bounded CPU functional/integration evidence.

---

# 6. Implementation authority and reopen conditions

## Frozen

- P3 remains revision 7.
- MACE 0.3.16 EMA checkpoint parameters are authenticated according to the actual checkpoint-save context, not assumed live.
- TRAIN2 live state and EMA shadow remain distinct authenticated authorities.
- checkpoint-save semantics are independent of EVAL2's LIVE/EMA selection.
- one real reconstructed provider owns all state transitions and forward.
- strict full-state-dict/architecture authentication and all previously closed P3A5 publication/restart semantics remain intact.

## Delegated

- helper/function names;
- exact internal tensor-comparison implementation;
- whether the checkpoint-state semantic validator returns a tag, digest, or validated object;
- test fixture size and tiny physical geometry, provided real semantic owners above execute.

## Reopen only on evidence

Reopen this narrow design surface only if representative source/runtime evidence proves one of the following:

1. the pinned MACE checkpoint owner used by TRAIN2 does not in fact save model parameters under the EMA-average context assumed above;
2. mdstats persists its TRAIN2 companion while that EMA context is still active, so `live_parameters` are not restored live parameters;
3. the existing companion/summary lacks enough durable state to authenticate the raw checkpoint-to-shadow/live relationship without a schema change;
4. a supported MACE checkpoint mode has materially different save semantics that must coexist in the same accepted P3 execution path.

If none of these triggers fires, this is a local implementation repair. Do not reopen the target-size scientific design or create revision 8.
