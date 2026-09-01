---
kind: implementation-repair-instructions
package_id: CODE-MLFF-TARGET-SIZE-V7-P3-P3A4-FINAL-REPAIR
governing_package_id: CODE-MLFF-TARGET-SIZE-V7-P3-P3A4-REPAIR
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
status: active
package_revision: 7
reviewed_implementation_commit: 4fdcf754540e69b49c25382e28a2234c5cb83ad6
reviewed_implementation_label: P3A4
---

# P3 revision-7 P3A4 final-review repair instructions

## 0. Authority, scope, and disposition

This file is a **cumulative implementation-repair amendment within P3 revision 7**. It does not introduce a new scientific design, does not increment the P3 revision, and does not reopen any frozen V7 target-size decision.

It binds the two blocking implementation findings remaining after independent review of commit `4fdcf754540e69b49c25382e28a2234c5cb83ad6` (`P3A4`). The governing authority remains the V7 parent workplan, P3 base package, Review-2 through Review-5 amendments, and `P3_P3A4_IMPLEMENTATION_REPAIR_INSTRUCTIONS.md`. This file narrows the next implementation pass to the two still-open nonconformances below and their directly affected regression/integration surface.

Preserve all P3A4 work already accepted in principle, including:

- mandatory immutable EVAL2 snapshot/evaluation-data role identity;
- one-provider ownership concept for state authentication and forward;
- sealed authenticated exact-M view and rejection of generic digest-spoofed views;
- stronger canonical P1 geometry/label/export-policy cross-validation;
- raw TRAIN2/EVAL2 failure translation inside completion owners;
- shared crash-safe persistence primitives;
- reducer-head locking and exact-retry idempotency;
- mandatory restart authority, typed content-addressed loading, and scientific replay;
- production resume resolution for n2/n3 through `resolve_target_size_candidate_for_resume()`;
- fresh-process success and raw-failure replay acceptance structure.

Do **not** redesign those surfaces merely because adjacent code is touched. Repair the earliest violated owners identified below.

P3 remains active until both repair passes and the final assembled acceptance gate close. P4 remains blocked.

---

# 1. Repair pass A — real MACE 0.3.16 provider reconstruction from TRAIN2 state

## A1. Root cause and protected concern

The current `_authenticate_target_size_provider()` correctly tries to make one provider/model instance own authentication and forward, but it still obtains the provider architecture from the raw TRAIN2 checkpoint or from `companion["model"]` and falls back to a synthetic parameter shell when neither is an `nn.Module`.

That is not production-correct for the pinned MACE 0.3.16 checkpoint format. MACE training checkpoints persist a mapping whose `model` entry is the model **state_dict**, alongside optimizer and scheduler state; the raw checkpoint is not a deployable MACE model object. The mdstats TRAIN2 companion carries live parameters, EMA state, RNG state, and continuation metadata, but does not provide a complete reconstructible MACE model shell.

Therefore a no-override production EVAL2 call can reach `from_authenticated_parameter_state(...)`, which is only a bounded test shell and cannot supply a deployable MACE calculator.

Protected concern: the exact trained boundary state must be evaluated by a real MACE provider whose architecture/configuration comes from the accepted candidate materialization/configuration authority, while the TRAIN2 checkpoint/companion contributes authenticated learned state only. A synthetic parameter shell must never become the production architecture owner.

## A2. Frozen corrected end state

The accepted production path must be:

```text
validated candidate materialization/configuration authority
    -> reconstruct the real MACE model shell / calculator-compatible architecture
    -> authenticate the exact TRAIN2 raw checkpoint state_dict against that shell
    -> authenticate/apply exact companion live state
    -> if EMA evaluation: authenticate/apply exact EMA shadow state
    -> recompute canonical evaluated-state digest from the same provider model
    -> perform forward with that same provider/model instance
```

The raw TRAIN2 checkpoint is an authenticated **state source**, not a model-construction authority.

The candidate MACE configuration/materialization remains the architecture/configuration authority. Reuse the existing shared MACE construction/loading machinery already used by the product where possible; do not add a P3-local second definition of MACE architecture compatibility.

## A3. Required implementation consequences

### A3.1 Decode the actual MACE checkpoint contract

The production loader must explicitly recognize the pinned MACE 0.3.16 checkpoint shape:

```text
checkpoint["model"] -> model state_dict
checkpoint["optimizer"] -> optimizer state
checkpoint["lr_scheduler"] -> scheduler state
```

A mapping `checkpoint["model"]` must not be treated as an `nn.Module` merely because the key is named `model`.

Validate that the raw checkpoint is the exact snapshot checkpoint already authenticated by SHA-256 and boundary metadata. Load it once through the accepted checkpoint/state loader path and extract the model state without promoting optimizer/scheduler data into EVAL2 authority.

### A3.2 Reconstruct the real MACE shell from accepted candidate configuration

Add or reuse one owner that can reconstruct the calculator-compatible MACE model shell from the validated candidate materialization/configuration authority used by TRAIN2. It must preserve all execution/scientific architecture required for prediction, including the model class/family, heads, atomic numbers, cutoff/r_max, interactions/products, irreps or equivalent execution structure, precision realization, and other existing shared architecture identity fields.

Do not infer this shell from the state_dict alone. Do not load a foundation model as a competing scientific state authority. If a foundation/model-construction source is needed to instantiate the architecture, it may be used only through the already accepted candidate configuration/materialization identity and must then receive the authenticated TRAIN2 state before evaluation.

### A3.3 Load and validate state through the shared provider owner

Once the real model shell exists:

1. construct one `MaceCalculatorProvider` around that shell;
2. load the raw checkpoint model state_dict using the shared compatibility/state-loading machinery with strict key/order/shape/dtype/architecture checks appropriate to the established MACE owner;
3. validate that the resulting model parameters correspond to the TRAIN2 continuation live state and `summary.live_parameter_digest`;
4. apply the exact companion live parameter state through the provider state owner if the checkpoint loader does not already yield byte-identical live state;
5. for EMA evaluation, validate exact shadow cardinality/order/key/shape/dtype against the provider model, apply every EMA shadow exactly once, and verify the resulting provider parameter digest against the authenticated EMA evidence;
6. perform inference only through this same provider/model instance.

No second model may be constructed after state authentication for the numerical forward.

### A3.4 Keep the fake seam below provider reconstruction/authentication

The bounded `inference_forward`/`inference_evaluator` seam remains allowed only below:

- real provider/model reconstruction;
- raw checkpoint state loading;
- companion live/EMA authentication;
- actual provider execution-identity derivation.

A fake may replace expensive numerical forward arithmetic. It may not justify `from_authenticated_parameter_state(...)` as the accepted production reconstruction path when a real MACE architecture should exist.

The synthetic parameter-shell path may remain only for narrowly scoped lower-level tests that explicitly do **not** claim production MACE provider acceptance. It must be structurally unreachable from a no-override production target-size EVAL2 call.

### A3.5 Prediction provenance remains actual, not defaulted

Continue deriving prediction evidence from the provider that actually forwards. Preserve at least:

- evaluated model-state digest;
- actual device;
- actual default dtype / critical precision realization;
- canonical execution-architecture identity;
- actual backend/compile policy;
- accepted batch/execution policy when prediction semantics depend on it.

The repaired real-MACE path must not regress to constructor defaults or metadata copied from configuration without verifying the realized provider.

## A4. Required acceptance evidence

### A4.1 Real-owner checkpoint-format reproducer — mandatory

Add a bounded CPU test using the real pinned MACE 0.3.16 checkpoint contract, not the synthetic `torch.nn.Linear` P3C checkpoint fixture.

The test must:

1. construct a minimal real MACE model through the same accepted candidate model-construction authority used by production;
2. create/save a MACE 0.3.16-style training checkpoint whose `model` entry is a state_dict rather than an `nn.Module`;
3. provide the corresponding authenticated TRAIN2 companion/live state and boundary snapshot metadata;
4. call the production target-size provider reconstruction/authentication owner with **no forward override**;
5. prove a real `MaceCalculatorProvider` owning a deployable MACE model is produced and can execute a tiny CPU prediction path, or equivalently execute the production `run_target_size_direct_boundary_inference()` path on a minimal exact-M fixture without an override;
6. prove the evaluated-state digest is computed from the provider model that actually forwards.

This is a functional integration test, not production qualification. Keep the model/data tiny and CPU-bounded.

### A4.2 Negative tests

Add focused failures proving:

- a real MACE state_dict with architecture-incompatible keys/shapes/dtypes is rejected before forward;
- a compatible raw state_dict whose live companion was altered is rejected;
- EMA cardinality/order/shape/dtype mismatch is rejected before forward;
- a configuration reconstructing a different MACE execution architecture (for example cutoff/r_max or another established architecture identity field) is rejected even if tensor keys/shapes are compatible;
- a no-override production call cannot silently fall back to `_AuthenticatedParameterShell`;
- model A authenticated / model B forwarded remains impossible.

### A4.3 Stage-local regression gate

After pass A, run focused provider/evaluation tests plus affected regression covering at least:

- `model_features.py` provider state/architecture compatibility;
- target-size candidate materialization/config validation;
- boundary snapshot authentication;
- direct target-size inference live and EMA paths;
- exact-M EVAL2 reduction linkage;
- existing hot-swap architecture tests whose shared provider machinery is touched.

Do not proceed to final closure while the real MACE state-dict integration reproducer is absent or skipped.

---

# 2. Repair pass B — publication must authenticate the complete parent graph before exposing completion/progress

## B1. Root cause and protected concern

`record_candidate_boundary_outcome()` still accepts a `TargetSizeCellCompletionRecord` while leaving success/failure parent objects optional. It resolves the planned rung and predecessor on omission, but does not equivalently resolve and validate all other mandatory completion parents before publishing the immutable completion and logical progress pointer.

As a result, a caller can hold a fully linked completion record in memory, omit materialization/snapshot/role/evaluation/prediction/metric objects, and still publish `completion` + `progress` even when those mandatory parents are absent from the durable graph. Reconciliation may fail later, but publication has already reported success and exposed an authoritative logical cell.

Protected concern: publication success means the complete scientific parent graph needed to justify that cell already exists durably and has been authenticated through the same typed/scientific owners used during replay. Restart validation must be a recheck of an accepted graph, not the first point at which missing mandatory parents are discovered.

## B2. Frozen corrected end state

Before either of these can become authoritative:

```text
completions/<boundary>/<digest>.json
progress/<boundary>/<logical-cell-key>.json
```

one variant-aware publication owner must prove every mandatory parent of that completion kind.

For any omitted parent argument, the publisher must resolve the parent by the digest already bound into the completion record and fully verify it. Omission is therefore an **idempotent retry convenience**, never an authority bypass.

If any required parent is missing, wrong type, wrong digest, bulk-invalid, scientifically incompatible, or outside its declared root, publication fails and neither completion nor progress may appear.

## B3. Required implementation consequences

### B3.1 Make publication variant-aware

Refactor `record_candidate_boundary_outcome()` or introduce a sealed variant-specific parent bundle so the publisher knows the mandatory graph for:

- `success`;
- `train2_failure`;
- `eval2_failure`.

A generic surface is acceptable only if it dispatches immediately into sealed variant-specific validation before publication.

### B3.2 Success parent graph

For `success`, require supply-or-resolve-and-verify of at least:

- trajectory;
- candidate materialization metadata and bulk materialization/config/target/harness artifacts;
- exact planned rung;
- predecessor initialization/continuation/snapshot ancestry as required by rung;
- immutable boundary snapshot metadata and snapshot bulk files;
- exact evaluation artifact metadata and sealed exact-M bulk bytes;
- EVAL2 role;
- prediction evidence;
- EVAL2 metric record.

Re-run the same necessary cross-links already enforced by the success completion builder/replay owner, including role↔snapshot/evaluation, prediction↔role/snapshot/evaluation, metric↔prediction, trajectory/materialization identity, and exact rung ancestry.

### B3.3 TRAIN2 failure parent graph

For `train2_failure`, require supply-or-resolve-and-verify of:

- trajectory;
- materialization;
- exact planned rung;
- explicit n1 initialization ancestry or exact later-rung predecessor ancestry;
- raw `Train2NumericalFailureRecord`;
- raw checkpoint bytes/SHA and any other failure bulk evidence required by the accepted taxonomy.

The publisher must not rely only on the already-derived P2 failure stored in the completion record.

### B3.4 EVAL2 failure parent graph

For `eval2_failure`, require supply-or-resolve-and-verify of:

- trajectory;
- materialization;
- exact planned rung and predecessor ancestry;
- boundary snapshot;
- evaluation artifact / exact-M bytes;
- EVAL2 role;
- exact prediction evidence;
- raw `Eval2NumericalEvaluationError`.

Recheck `error.prediction_digest == prediction.prediction_payload_digest` and role identity before publishing completion/progress.

### B3.5 Reuse the restart resolver/scientific validators

Do not create a weaker publication-only resolver. Reuse `TargetSizeExecutionResolver` and the same typed loaders/scientific validators used by reconciliation wherever possible.

A supplied object must be create-or-verified at its canonical path and then validated through the same owner as a resolved object. An omitted object must be resolved from the digest in the completion record and validated identically.

For bulk-bearing parents, metadata-only content-digest validation is insufficient. Validate the required bulk bytes/roots before completion publication.

### B3.6 Preserve publication ordering

The publication order must remain fail-safe:

```text
validate/supply-or-resolve every mandatory parent
    -> create-or-verify any newly supplied parent artifacts
    -> re-verify complete parent graph
    -> create-or-verify immutable completion record
    -> create-or-verify logical progress pointer
    -> return success
```

Do not publish the completion before mandatory parent validation merely because progress is written later.

If failure occurs at any earlier step, no new authoritative completion/progress record may be left behind for that attempted cell. Existing valid parents from an interrupted attempt may remain as harmless immutable evidence.

## B4. Required acceptance evidence

### B4.1 Empty-graph omitted-parent reproducer — mandatory

Construct a valid success completion in memory, then attempt to publish it into a screen root in which one or more of its required durable parents have deliberately not been published. Call the publication owner while omitting the corresponding parent arguments.

Required result:

- publication raises `TrainingDataInputError` or the established typed validation error;
- no new `completions/...json` exists for that completion;
- no new `progress/...json` exists for that logical cell.

The test must not pre-seed those parents through a helper that hides the condition being tested.

### B4.2 True identical retry — mandatory

Then publish the complete graph correctly once. Retry the same cell while omitting parent objects.

Required result:

- publisher resolves every mandatory parent from its bound digest;
- typed/scientific validation executes;
- retry returns the same logical completion/progress identity idempotently;
- no duplicate or divergent scientific object is created.

Mutating/removing any one durable mandatory parent before the retry must convert that retry into a failure rather than a success.

### B4.3 Variant coverage

Add equivalent focused checks for TRAIN2 and EVAL2 failure publication:

- missing raw TRAIN2 checkpoint parent -> no completion/progress publication;
- missing predecessor/rung parent -> no completion/progress publication;
- missing EVAL2 prediction parent -> no completion/progress publication;
- foreign EVAL2 error/prediction linkage -> no completion/progress publication.

### B4.4 Concurrency/idempotency regression

Retain concurrent identical worker publication coverage, but make it exercise the repaired parent resolution path rather than relying on preexisting graph state without verification. Identical retries may converge; conflicting cells/evidence remain fail-closed.

### B4.5 Stage-local regression gate

After pass B, run focused persistence/publication tests plus affected P3E/P3F regression covering:

- typed resolver loads;
- parent create-or-verify;
- logical progress key validation;
- completion collection;
- concurrent worker publication;
- complete boundary batch construction;
- commit/head idempotency;
- restart/reconciliation of both success and failure graphs.

---

# 3. Final assembled P3 acceptance after both repairs

## 3.1 Conformance closure

Before claiming P3 complete, inspect the assembled candidate and prove:

1. no no-override production target-size EVAL2 path can use `_AuthenticatedParameterShell` or another synthetic provider shell as its architecture owner;
2. the real MACE provider architecture comes from the validated candidate materialization/configuration authority;
3. the real pinned MACE checkpoint state_dict is loaded/authenticated into that provider before live/EMA evaluation;
4. the same provider/model instance whose state is authenticated performs production forward;
5. `record_candidate_boundary_outcome()` cannot publish a new completion/progress record until the complete mandatory variant parent graph is durable and validated;
6. omitted parents are accepted only as verified idempotent retry resolution, never as missing-authority tolerance;
7. all previously closed revision-7 obligations remain intact.

Structural/source inspection is required for the uniqueness/no-fallback claims because green behavior tests alone cannot prove the obsolete path is unreachable.

## 3.2 Final affected-surface regression

After all executable repairs, re-derive the affected surface from the final diff and run the complete affected regression. At minimum include the relevant P3 candidate/export/execution/evaluation/coordinator suites plus shared MACE provider/model-feature regression affected by the new real-checkpoint loading path.

If the provider reconstruction change touches a shared loader used outside target-size selection, include those consumers in affected regression rather than limiting testing to P3 files.

## 3.3 Final integration — proxy-proof real owners

Final P3 integration evidence must include both:

### Real MACE state-dict provider path

A bounded CPU real-MACE checkpoint-format path through the actual production provider reconstruction/authentication owner with no forward override. Synthetic `torch.nn.Linear`, `_AuthenticatedParameterShell`, or fake provider construction cannot establish this claim.

### Fresh-process durable graph path

Retain the existing process A/B/C fresh-process success lifecycle and fresh TRAIN2/EVAL2 failure replay, but execute them against the repaired publication owner. The test may use bounded numerical forward below the provider owner, except the dedicated real-MACE provider acceptance above must remain no-override.

The counterfactual acceptance criterion is: if real MACE checkpoint reconstruction or mandatory parent resolution were broken, the corresponding required acceptance test must fail.

## 3.4 Production qualification disposition

Do **not** run long GPU/data-heavy production qualification as part of this repair. Full production GPU qualification remains deferred to the final release package. These repairs require bounded functional, regression, persistence/restart, and CPU real-owner integration evidence only.

## 3.5 Exit gate

P3 revision 7 may pass only when:

- Repair pass A semantic and functional gates pass;
- Repair pass B semantic and functional gates pass;
- final affected-surface regression passes;
- proxy-proof real-MACE no-override integration passes;
- fresh-process success/failure restart integration passes;
- no genuinely blocking independent-review issue remains.

Only then may P3 be frozen/accepted and P4 unblocked.

---

# 4. Implementation authority and redesign trigger

Implementation owns local function decomposition, helper naming, exact test fixture construction, and reuse/refactoring mechanics, provided the frozen end states above remain intact.

Do not add a new scientific selection authority, checkpoint-selection rule, fallback evaluator, alternative persistence topology, or second provider-compatibility definition.

Reopen design only if evidence shows that the accepted candidate materialization/configuration cannot reconstruct the real TRAIN2 MACE architecture without adding a new scientific authority, or that the pinned MACE 0.3.16 checkpoint format differs materially from the verified state-dict contract in the actual deployed dependency. In that case stop only Repair pass A, preserve unrelated accepted work, and reopen the minimum architecture/state-reconstruction surface with concrete dependency evidence.
