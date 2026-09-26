---
kind: implementation-workplan
workplan_id: CODE-MLFF-P5-TRAIN2-MH1-SELECTED-HEAD-ROUTING-REPAIR
protocol_version: 6.4.0
status: review-reopened
created_date: 2026-09-25
baseline_branch: main
baseline_commit: c82388122cc3e72921a2f7a07d906b9527c4e229
implementation_branch: fix/mlff-p5-train2-mh1-selected-head-routing
scope: P5 TRAIN2/EVAL2 reconstruction routing of the doctor-qualified training-foundation checkpoint for foundation-backed MLFF campaigns
earliest_affected_domain: D4 implementation/concretization under accepted phase-separated source/training realization architecture
review_disposition: PASS AS WORKPLAN
workplan_review_revision: 2
serious_challenge: none
implementation_review_verdict: CODE-PASS-E1-PENDING
implementation_base: 7143f36b02f26a6c3fb1ded95445ea36477f10a2
---

# MLFF P5 TRAIN2 MH-1 selected-head routing repair workplan

## 0. Disposition

A real MH-1 P5 cross-validation launch reaches MACE 0.3.16 and fails before epoch 1 while MACE tries to remove the selected `omat_pbe` head from the original six-head `mace-mh-1.model`. The state-dict mismatch is the already-qualified MH1-EXTRACT1 reconstruction defect: stock removal from that public six-head file reconstructs the wrong first-interaction shape unless the existing narrowly qualified compatibility path is used.

This is **not** a new MACE compatibility problem and is **not** a CuEq numerical, scheduler, precision, or GPU-capacity defect. The existing doctor path already performs MH1-EXTRACT1, qualifies the exact selected-head checkpoint, and freezes that checkpoint in `TrainingAccelerationRealizationRecord.v1`. The downstream P5 launch currently bypasses that training realization and passes `context.method_policies.foundation_model`, which is the raw scientific source checkpoint, into TRAIN2.

The repair is therefore a narrow D4 routing/ownership correction:

```text
raw six-head MH-1 + source head omat_pbe
  -> source identity / DATA6 / source-side inference authority
  -> MH1-EXTRACT1 (existing owner)
  -> qualified single selected-head checkpoint, head still named omat_pbe
  -> TrainingAccelerationRealizationRecord.v1
  -> P5 TRAIN2 construction and every reconstruction of that TRAIN2 architecture
  -> portable post-TRAIN2 model / EVAL2
```

No new extractor, compatibility shim, checkpoint format, fallback route, MACE wrapper, or D2/D3 campaign is authorized.

## 1. Governing authority and frozen invariants

### 1.1 Accepted authority

The implementation must preserve the accepted current architecture/specification:

1. Source inference/DATA6 use the scientific source realization.
2. TRAIN2 uses the training realization.
3. For multi-head MH-1, the TRAIN2 candidate starts from the exact MH1-EXTRACT1-qualified selected-head `omat_pbe` checkpoint.
4. The original six-head MH-1 bytes plus exact `omat_pbe` head remain the scientific source-foundation identity.
5. `TrainingAccelerationRealizationRecord.v1` binds the exact selected-head training checkpoint, checkpoint SHA-256, selected-head qualification digest, backend/kernel, device/dtype, and runtime/parity identity.
6. CuEq is a TRAIN2 execution realization. The downstream portable/e3nn model remains the post-training representation required by the accepted phase-separated path.
7. Foundation scientific identity is content/head/family identity; a filesystem locator is not scientific identity.

Historical qualification establishes that the selected-head checkpoint SHA-256
`7b6f3cce6d2086164082f1cb5739098de2db990d6a49f0d60e66a3a0f1ae545e`
with `foundation_head=omat_pbe` was accepted by the pinned MACE parser and completed bounded real training. The repair must preserve that established parser contract; it must not rename the training-side head to `default`.

### 1.2 Frozen non-goals

This cycle does not change:

- D1 scientific meaning or training data membership;
- D2 training method, CV method, numerical tolerances, convergence, precision, or CuEq parity semantics;
- D3 phase separation between source realization and training realization;
- MACE architecture fields such as channels/irreps/`max_L`;
- optimizer, loss, learning rate, batch size, epoch budget, scheduler admission, CV folds/seeds, replay policy, target/replay heads, checkpoint selection, or publication semantics;
- the raw MH-1 checkpoint;
- MH1-EXTRACT1 implementation or its compatibility policy;
- source-side DATA6/inference behavior;
- long production-scale GPU qualification policy.

TorchScript/deprecation/`weights_only` warnings adjacent to the traceback remain non-causal and are not repair targets.

## 2. Root cause and current violating flow

### 2.1 Existing correct owners

The current code already has the required training-foundation authority:

- doctor qualifies/reuses selected-head extraction via `_qualify_selected_head_training_foundation(...)`;
- doctor freezes the exact TRAIN2 checkpoint through `TrainingAccelerationRealizationRecord.training_checkpoint_reference`, `training_checkpoint_sha256`, and `selected_head_qualification_digest`;
- `_stored_training_acceleration_realization(..., require_qualified=True)` fail-closes when the record is absent, runtime-incompatible, unqualified, missing, or byte-changed;
- optimizer policy already binds the stored training-realization digest/kernel, proving P5 is already expected to execute under that frozen realization.

### 2.2 Current defect

P5 constructs `PostSelectionRungRequest` with:

```text
foundation_identity   = context.method_policies.foundation_potential_identity
foundation_model_path = context.method_policies.foundation_model
```

Both denote the **scientific source foundation**, so for MH-1 the trainer authenticates and launches the raw six-head checkpoint. `MacePostSelectionTrainer` then projects that locator into the executable MACE configuration. MACE 0.3.16 consequently executes stock multi-head foundation removal on the public six-head MH-1 and re-enters the already-known MH1-EXTRACT1 failure.

The same conflation also exists wherever P5 reconstructs a TRAIN2 checkpoint architecture by calling `authenticate_train2_checkpoint_provider(... foundation_model_path=...)`: reconstruction must start from the same selected-head training checkpoint that TRAIN2 actually used, or architecture authentication can diverge even after launch is fixed.

## 3. Cycle design: separate source identity from TRAIN2 construction checkpoint

### 3.1 Frozen ownership

For every foundation-backed P5 run, maintain two distinct concepts:

```text
scientific source foundation
  identity: family + raw source checkpoint SHA + selected source head
  owner: PostSelectionMethodPolicies/FoundationPotentialIdentity
  purpose: scientific lineage, source-side behavior, policy identity

TRAIN2 construction foundation
  identity: exact qualified training checkpoint SHA + qualification/realization binding
  owner: current TrainingAccelerationRealizationRecord
  purpose: MACE TRAIN2 construction and reconstruction of TRAIN2 architecture/state
```

They are related but must not be represented as one pathname/SHA field.

### 3.2 Required source of truth

For phase-separated TRAIN2, the exact checkpoint used to launch or reconstruct TRAIN2 must come from the **current qualified stored training realization**, not from `[paths].foundation_model`, not from a re-run of extraction, not from a guessed path beside the raw checkpoint, and not from a copied historical audit path.

For non-phase-separated modes where the accepted training realization legitimately equals the source checkpoint, existing semantics may collapse to one file. The implementation must preserve those modes without manufacturing selected-head requirements where none apply.

### 3.3 One invocation-scoped execution binding

Resolve the authenticated TRAIN2 construction foundation **once per P5 invocation/context** and reuse that same resolved binding for:

- real TRAIN2 launch;
- candidate/outer-evaluation provider reconstruction;
- publication/model-product provider reconstruction;
- any restart/currentness operation that reconstructs current TRAIN2 execution authority.

Do not let each consumer independently reopen campaign state and reinterpret the record. The exact transient representation is delegated (for example, an execution-only field/object on the resolved post-selection context), but it must carry enough information to authenticate the current training-realization digest, checkpoint locator/SHA, and selected-head qualification ancestry.

Source-only operations such as foundation residual evaluation and replay-foundation baseline evaluation must continue to use the scientific source binding, not this TRAIN2 execution binding.

### 3.4 Minimality constraint

Prefer rewiring existing P5 execution context/request authentication to carry the already-existing training-realization checkpoint binding. Do not add a second persistent record or duplicate the training realization inside P5 materialization. If a small transient execution object/fields are needed to carry the existing record to the trainer/provider boundary, they are delegated D4 plumbing, not new authority.

## 4. Implementation obligations

### O1 — resolve one authenticated TRAIN2 construction foundation at P5 context/execution entry

For a phase-separated foundation-backed P5 invocation:

- obtain the current stored `TrainingAccelerationRealizationRecord` through an existing or minimally shared current owner;
- require it to be qualified under the current runtime/policy exactly as existing preparation/optimizer intake does;
- authenticate `training_checkpoint_reference` exists and its SHA-256 equals `training_checkpoint_sha256`;
- require its `selected_head_qualification_digest` when the source foundation is genuinely multi-head and selected-head qualification is required;
- when that digest is required, load the current stored selected-head qualification and require exact digest equality, then re-authenticate that qualification's extraction against the current source `FoundationPotentialIdentity`: source potential/content digest, raw source checkpoint SHA-256, and source head must all match, and the extraction's derived checkpoint SHA-256 must equal the training-realization checkpoint SHA-256;
- preserve the record's content digest already bound by optimizer policy and reject disagreement between the optimizer's realization digest and the checkpoint binding carried to execution.

This ancestry check closes the otherwise possible stale-record hole: a byte-valid training checkpoint from another source/head/campaign generation must not become current merely because a `TrainingAccelerationRealizationRecord` exists.

Do not silently fall back to the raw scientific source checkpoint when this record is required but missing/stale.

For scratch training, no foundation checkpoint is introduced. For foundation modes not requiring phase-separated selected-head realization, preserve current supported behavior.

### O2 — authenticate source lineage and TRAIN2 bytes independently

The current trainer check assumes the execution path SHA equals `foundation_identity.sha256`; that is invalid for MH-1 because source SHA and selected-head training SHA intentionally differ.

Repair the boundary so it separately verifies:

- source scientific identity/head remains exactly the one bound by the immutable P5 method;
- executable TRAIN2 checkpoint bytes equal the exact stored training-realization SHA;
- training realization is current/qualified and, where applicable, binds the current selected-head qualification digest;
- the configured `foundation_head` remains the accepted source head (`omat_pbe` for MH-1), matching the established selected-head checkpoint parser contract.

No check may be weakened into “file exists”.

### O3 — launch MACE with the selected-head training checkpoint

`post_selection_mace_run_configuration(... foundation_model_path=...)` must receive the authenticated TRAIN2 construction checkpoint for foundation-backed phase-separated training.

For the reported MH-1 case, the resulting MACE launch must therefore name the doctor-produced selected-head checkpoint, not `01_models/mace-mh-1.model`.

The internal immutable P5 MACE configuration remains path-independent. Runtime path injection remains launch-local.

### O4 — use the same checkpoint for independent TRAIN2 reconstruction

Every P5 call that reconstructs the TRAIN2 architecture/state through `authenticate_train2_checkpoint_provider` or equivalent must receive the **same authenticated TRAIN2 construction checkpoint** used by launch.

Current affected consumers include at minimum:

- the real TRAIN2 launch request built in `campaign_post_selection_runtime.py`;
- checkpoint-candidate assessment paths in `campaign_post_selection_runtime.py` that call `authenticate_post_selection_provider(...)`;
- `post_selection_model_products.py` representative/publication reconstruction;
- direct P5/MH-1 publication integration callers that rebuild the provider;
- any continuation/restart path that re-projects a dependency-facing MACE executable payload or rebuilds the MACE shell from the materialized P5 configuration.

The final implementation review must re-run repository search over `authenticate_post_selection_provider`, `authenticate_train2_checkpoint_provider`, `build_mace_model_from_configuration`, and current uses of `context.method_policies.foundation_model`; this list is an initial affected surface, not permission to stop at these named sites.

This obligation does **not** change the post-training portable/e3nn evaluation policy. It ensures that the shell used to authenticate TRAIN2 state is reconstructed from the same qualified starting checkpoint before the existing CuEq->portable projection/evaluation path runs.

A source-side consumer that is not reconstructing TRAIN2 must continue using the scientific source realization.

### O5 — keep MH1-EXTRACT1 single-owned

Do not call `extract_mace_selected_foundation_head()` from P5, TRAIN2, EVAL2, or provider reconstruction. Do not reproduce the `use_edge_irreps_first` shim in any new location.

The only permitted dependency is the already-qualified selected-head artifact and its authenticated record.

### O6 — restart/currentness behavior

A failed P5 attempt that produced materialization but no accepted gradient-update evidence must be restartable after this repair without deleting unrelated campaign authority.

Because the immutable P5 MACE configuration is path-independent, changing the runtime foundation locator to the correct selected-head checkpoint must not rewrite accepted method/materialization identity.

However, a failed launch can leave **execution-local** dependency-facing payload/evidence that contains the old raw-source locator. The implementation must classify this separately from immutable materialization:

- accepted TRAIN2 progress/evidence remains immutable and reusable only if its execution authority and training-foundation ancestry authenticate under the corrected current owner;
- zero-update or otherwise unaccepted execution-local launch payload/evidence carrying the obsolete raw-source locator may be reclaimed/recreated only through the existing run-root activity lease/recovery owner;
- another live process remains protected from destructive reconciliation;
- locator correction must not delete accepted checkpoints merely to make the retry green.

Do not add a migration state machine or mutate historical accepted evidence in place.

### O7 — error messages identify the two identities

Where a mismatch is rejected, diagnostics must distinguish at least:

- scientific source foundation mismatch; versus
- TRAIN2 construction checkpoint/realization mismatch.

Do not report the selected-head training artifact as if it were the raw scientific source checkpoint.

## 5. Required tests and acceptance evidence

### 5.1 Focused D4 tests

Add/repair tests that explicitly use **different files and SHA-256 values** for:

```text
source foundation       = raw multi-head fixture
TRAIN2 foundation       = qualified selected-head fixture
```

A fixture that points both concepts at the same file is insufficient to prove this repair.

Required assertions:

1. P5 method/source identity remains bound to the raw source foundation and selected source head.
2. TRAIN2 launch receives the training-realization checkpoint path.
3. The executable MACE config preserves the accepted `foundation_head` while using the distinct selected-head checkpoint.
4. Trainer authentication rejects tampered training checkpoint bytes.
5. Missing/unqualified/stale required training realization fails closed before MACE launch.
6. Wrong training-realization digest or selected-head qualification binding fails closed.
7. A selected-head qualification whose source potential digest, raw source SHA, source head, or derived checkpoint SHA disagrees with the current source/training realization fails closed.
8. Raw source checkpoint is not used as an implicit fallback.
9. Scratch P5 remains foundation-free.
10. A supported non-phase-separated foundation path remains unchanged.
11. TRAIN2 provider reconstruction receives the training checkpoint, not the source checkpoint.
12. Source-only consumers continue to receive the scientific source foundation where applicable, including foundation-residual/source-evaluation preparation.
13. A same-workspace retry after a zero-update launch failure can proceed through existing restart ownership without manual deletion solely because the runtime locator is corrected.
14. Stale unaccepted execution-local payload/evidence carrying the raw-source locator is reconciled under the existing activity lease, while accepted/current progress is never destructively rewritten.

### 5.2 Affected regression

Run the focused post-selection, TRAIN2/EVAL2 architecture, downstream integration, MH-1 integration, restart/currentness, and CuEq execution-semantics suites that cover the changed boundary. Correct stale tests that encode “one foundation pathname must serve both source identity and TRAIN2 construction” rather than preserving that accidental conflation.

Do not weaken tests that protect source content/head authentication.

### 5.3 Real-owner bounded MH-1 acceptance

After CPU/fixture regression is green, run one bounded real MH-1 P5 TRAIN2 launch on the intended runtime/hardware sufficient to prove:

- the MACE log names the qualified selected-head training checkpoint;
- MACE no longer attempts stock selected-head removal from the original six-head `mace-mh-1.model`;
- execution reaches actual epoch computation / at least one gradient update;
- no architecture-authentication failure is introduced when reconstructing that TRAIN2 state.

Then rerun the previously failing cross-validation command far enough to establish the repaired owner/consumer boundary. Long production-scale qualification remains deferred.

A successful doctor-only run is not acceptance for this defect because doctor already passed before the failure.

## 6. Evidence and history impact

### 6.1 Existing evidence reused

MH1-EXTRACT1 evidence remains applicable: it proves the public six-head checkpoint's stock-removal defect and the qualified selected-head artifact/parity.

MH1-TRAIN1 evidence remains applicable: it proves that the selected-head checkpoint with `foundation_head=omat_pbe` is a valid pinned-MACE training start and therefore falsifies any proposed repair that changes the head to `default`.

Existing TRAIN2 acceleration evidence remains applicable only if its exact realization/checkpoint/runtime identity matches the active campaign record.

### 6.2 Project Engineering Memory

`FF-001 — Realized-model identity drift across duplicated construction paths` is applicable as a falsification guide: launch and independent reconstruction must not use different construction foundations.

Do not automatically create a new PEM family or recurrence count. At closeout, assess whether this incident is independently recurrent under FF-001's exact semantic envelope or merely a new affected surface of the same already-known integration mechanism. Record only if the repository's PEM admission criteria are actually met.

## 7. Authority/documentation impact

Expected disposition:

- D1 change: **NO**
- D2 change: **NO**
- D3 architecture change: **NO**
- D4 specification mutation: **NO**; this is conformance repair to already-accepted source/training realization separation
- permanent architecture/specification edits: **not required unless implementation review discovers current accepted prose that still tells P5 TRAIN2 to use the raw source checkpoint**
- generated documentation/PDF regeneration: **not required unless a permanent documentation owner changes**
- workplan index: add this plan as the active narrow P5 MH-1 routing repair; archive it on accepted closeout

## 8. Implementation sequence

### Stage A — wiring and authentication

1. Resolve one invocation-scoped authenticated current TRAIN2 construction-foundation binding from existing training-realization + selected-head-qualification authority, including full source->extraction->training-checkpoint ancestry.
2. Carry that exact same transient binding through P5 execution and TRAIN2 reconstruction without replacing the scientific source identity; do not independently re-resolve it in sibling consumers.
3. Split trainer authentication of source lineage from training-checkpoint bytes.
4. Inject the training checkpoint into the real MACE launch.

Run focused launch/config/authentication tests.

### Stage B — reconstruction closure

1. Re-derive all P5 TRAIN2 reconstruction call sites from the final diff.
2. Route the same authenticated training checkpoint through checkpoint/provider reconstruction.
3. Confirm source-only consumers remain source-owned.
4. Run focused TRAIN2/EVAL2 and downstream integration regression.

### Stage C — bounded real-owner acceptance

Run the bounded real MH-1 launch and the previously failing CV path far enough to prove the repaired seam. Do not broaden this into production-scale qualification.

## 9. Forbidden repairs

The implementation must not:

- increase a numerical tolerance to hide this error;
- alter CuEq/e3nn architecture to fit the raw checkpoint;
- change model channels/irreps/`max_L`;
- alter scheduler admission or GPU resource policy;
- rename MH-1's accepted selected head merely to avoid extraction;
- patch MACE's `remove_pt_head()` from P5;
- duplicate MH1-EXTRACT1 compatibility logic;
- copy the historical audit checkpoint into the campaign instead of using the current doctor-owned artifact;
- add fallback from missing training realization to raw source foundation;
- add another persistent foundation/checkpoint registry;
- weaken checkpoint/provider architecture authentication;
- rewrite immutable scientific method identity around a filesystem path.

## 10. Reopen / Challenge triggers

Remain D4-local unless evidence shows otherwise.

Reopen D3 only if the existing accepted phase-separated architecture cannot represent one source scientific foundation plus one distinct authenticated TRAIN2 construction checkpoint without competing durable owners.

Route D2/D1 only if the correct selected-head checkpoint changes scientific/numerical training semantics rather than merely realizing the already-accepted method.

Raise a Serious Challenge if current accepted authority is found to simultaneously require TRAIN2 to start from both the raw multi-head source checkpoint and the qualified selected-head training checkpoint with no compatibility/equivalence rule.

If implementation begins accumulating new wrappers/fallbacks/duplicate records, stop and simplify the wiring before continuing.

## 11. Workplan acceptance

This workplan is ready for Implementation only when independent workplan review establishes all of the following:

- the defect is bounded to existing D4 source-vs-training checkpoint routing;
- every TRAIN2 construction/reconstruction consumer is covered;
- source scientific identity is preserved separately;
- selected-head qualification remains single-owned;
- restart/currentness implications are bounded;
- tests discriminate source checkpoint from training checkpoint;
- real acceptance crosses the failing P5 owner/consumer boundary;
- no unnecessary upstream redesign or new durable machinery is required.

Current workplan-review verdict: **PASS AS WORKPLAN**.

## 12. Workplan review pass 1

The first independent workplan review found four material omissions in the initial draft; all are incorporated above:

1. **Stale ancestry gap — CLOSED IN O1/O2.** Checking only the training checkpoint SHA and qualification digest was insufficient. The plan now requires the current qualification to bind back to the current source potential digest, raw source SHA, source head, and the same derived checkpoint SHA.
2. **Reconstruction-surface gap — CLOSED IN O4.** A launch-only repair would still leave current provider/publication reconstruction using the raw source locator. The plan now names the known reconstruction consumers and requires a final call-site re-derivation.
3. **Restart execution-local evidence gap — CLOSED IN O6.** Materialization is path-independent, but a failed launch can leave dependency-facing executable evidence with the obsolete locator. The plan now distinguishes immutable accepted progress from reclaimable zero-update execution-local residue under the existing lease.
4. **Source-only consumer ambiguity — CLOSED IN O4/tests.** Foundation-residual/source-side preparation must continue to use the scientific source realization; the training checkpoint is only for TRAIN2 construction/reconstruction.

No upstream scientific/numerical/architectural contradiction was found. The remaining review task is a fresh recheck of Revision 1 against the actual call graph and accepted evidence.


## 13. Workplan review pass 2 and final recheck

Pass 2 re-derived the current call graph and found one remaining coordination weakness: Revision 1 required the correct record at every consumer but did not require those consumers to share one resolved invocation-scoped binding. Independent re-resolution would preserve the same duplicated-construction risk highlighted by PEM FF-001 and could allow launch/reconstruction drift if campaign state changed between reads.

That gap is now closed in Section 3 and Stage A: one authenticated TRAIN2 construction-foundation binding is resolved once and reused by the entire P5 invocation. This is transient D4 plumbing over the existing persistent owner, not a new authority record.

The final recheck then classified current `context.method_policies.foundation_model` uses:

- **must remain source-owned:** replay foundation baseline identity/provider and foundation-residual/source evaluation;
- **must switch to the invocation-scoped TRAIN2 binding:** real TRAIN2 launch and all `authenticate_post_selection_provider` / TRAIN2-shell reconstruction paths in `campaign_post_selection_runtime.py` and `post_selection_model_products.py`;
- **tests encoding the conflation:** update only where they currently use the same fixture path for both roles.

No additional materially affected production caller, upstream authority conflict, required new persistent state, or new numerical/scientific obligation was found.

**Final workplan review disposition: PASS AS WORKPLAN.** Implementation may proceed under the bounded D4 plan. A later implementation Review must still re-derive the final affected surface from the assembled diff and may reopen this plan if implementation exposes a real omitted owner.


## 14. Implementation record (D4)

Implemented on `fix/mlff-p5-train2-mh1-selected-head-routing` over reviewed head `7143f36b`. No Serious Challenge; no D1/D2/D3 or D4-specification mutation. No new persistent record, extractor, shim, wrapper, or fallback.

### 14.1 Concretization

| Obligation | Concretization |
|---|---|
| O1 | `_campaign_cli_core._current_train2_foundation_realization(cfg, paths, potential)` — one small owner-local resolver beside the existing doctor/realization owners. Phase-separated + foundation-backed only; otherwise `None` (collapsed/scratch semantics unchanged). Reuses `_stored_training_acceleration_realization(require_qualified=True)` (missing / runtime-incompatible / unqualified / byte-changed) and `_selected_head_qualification_matches`. Multi-head source: requires the realization's `selected_head_qualification_digest`, the stored qualification with that exact digest, lineage to the current source potential digest / raw SHA / head, and `derived_checkpoint_sha256 == training_checkpoint_sha256`. Single-head source: the realization must be the source checkpoint itself (no digest, SHA equal). |
| O1 / §3.3 | Resolved **once** in `build_post_selection_contexts` and carried as the execution-only field `PostSelectionContext.train2_foundation_realization`; `PostSelectionContext.train2_foundation_path` projects it (source locator only when TRAIN2 is not phase-separated; raises rather than falling back when phase-separated and unresolved). |
| O2 / O7 | `MacePostSelectionTrainer` step 5 now checks the source head against the scientific source identity, then authenticates the construction checkpoint either against the source SHA (no realization) or against the carried realization: qualified, `content_digest == optimizer_policy.acceleration_realization_digest`, reference path == launch path, bytes == `training_checkpoint_sha256`. Diagnostics name "scientific source foundation" vs "TRAIN2 construction checkpoint / training realization" distinctly. A request carrying a realization counts as foundation-backed (scratch cannot smuggle one). |
| O3 | `PostSelectionRungRequest` gains execution-only `training_realization`; both P5 launch sites pass `context.train2_foundation_path` + `context.train2_foundation_realization`. Immutable P5 MACE config stays path-free. |
| O4 | All three `authenticate_post_selection_provider` call sites (checkpoint-candidate assessment, outer evaluation, `post_selection_model_products` publication/representative) use `context.train2_foundation_path`. Final re-derivation over `authenticate_post_selection_provider`, `authenticate_train2_checkpoint_provider`, `build_mace_model_from_configuration`, `method_policies.foundation_model`: remaining production `foundation_model` uses are source-only (replay-baseline identity guard, `build_post_selection_foundation_baseline_provider`, `resolve_foundation_residual_inputs`); P3 target-size `authenticate_train2_checkpoint_provider` callers are foundation-free. |
| O5 | No P5/TRAIN2/EVAL2 module references `extract_mace_selected_foundation_head` (structurally asserted). |
| O6 | No code change required: execution evidence and materialization never bind the locator; `mace_run_config.yaml` is rewritten per launch. A zero-update failure's stale raw-source payload is recreated on retry through the existing run owner; materialization bytes are preserved. |

Test-only reconciliation: `test_mlff_mh1_publication_integration.py` MH-1-shaped foundation/campaign builders lifted to module helpers for reuse; TRAIN2 reconstruction callers in it and in `test_mlff_mace_execution_semantics_assembled.py` now use `context.train2_foundation_path`; the CUDA CuEq fixture's spurious `selected_head_qualification_digest="b"*64` on a single-head source (the conflation this repair rejects) is now `None`; r8's expected source-SHA diagnostic string updated.

### 14.2 Evidence

Focused (`tests/test_mlff_p5_train2_foundation_routing.py`, distinct source/training files and SHAs throughout):

- owner resolver: happy path; missing / unqualified / byte-tampered realization; absent or wrong qualification digest; missing qualification; qualification lineage mismatch on source potential digest, raw SHA, head; derived-SHA mismatch; raw source never accepted as TRAIN2 checkpoint; single-head collapsed mode; non-phase-separated and scratch return `None`; context projection refuses fallback (§5.1 items 5–10);
- assembled real-owner P5 CV run (real MACE training, CPU) over a three-head MH-1-shaped source with checkpoints produced by the real doctor owners (`_qualify_selected_head_training_foundation` + `qualify_training_acceleration_realization`): a pre-repair-shaped zero-update failure writes a raw-source `mace_run_config.yaml`; same-workspace retry succeeds without deletion, materialization bytes unchanged; launch requests carry source identity + selected-head path + realization; executable config `foundation_model` = selected-head checkpoint, `foundation_head=omat_pbe`; `completed_updates > 0`; every TRAIN2 provider reconstruction used the selected-head checkpoint; residual inputs and replay baseline stayed on the raw source (§5.1 items 1–3, 11–14);
- mutation check: re-routing the launch to the raw source makes the assembled test fail on the request-path assertion;
- structural: every production `authenticate_post_selection_provider` (3) and `PostSelectionRungRequest` site uses the invocation binding; no EXTRACT1 in P5 modules.

- real trainer rejection matrix, driven with mutated copies of the captured real launch request (rejected before any subprocess): tampered training-checkpoint bytes; realization dropped (selected-head SHA ≠ source SHA); raw-source path under the realization; optimizer realization-digest mismatch; unqualified realization (§5.1 items 4–6, 8).

The r8 pre-launch harness (`test_claims_21_to_29…`) is **pre-existing broken** at `7143f36b` (stale `PostSelectionMethodIdentity` / `PostSelectionMaterialization` constructors) and was not used; only its expected diagnostic string was updated.

Affected regression (17 files directly exercising the changed symbols: new routing suite, MH-1 publication integration, assembled execution semantics, downstream integration closure, TRAIN2/EVAL2 CuEq realization parity (CUDA cases ran on the RTX 3090), model publication acceptance, replay P5 execution recovery, restoration method owners, P5 r6/r7/r8/r10/r11 guards, execution semantics, executable config, CUEQ-TRAIN-DEFAULT1, EXTRACT1), `-n 16`: **239 passed, 10 failed, 3 skipped in 23 min**. All 10 failures reproduce at base `7143f36b` and are unrelated: 8 × `test_mlff_target_size_p5_r11_guards.py` (monkeypatches the removed `select_cv_fold_representative`), r8 `test_claims_21_to_29…` (stale constructors), and `test_extract1_stock_success_self_disables_architecture_shim` (order-dependent process-global torch default-dtype leak; reproduced at base by replaying the same worker's test sequence). **New failures: 0.** The 3 skips are gated on a locked real MH-1 path/CUDA-only cases outside the changed boundary.

A broader 64-file grep-derived run was attempted first and abandoned after stalling at 93 % for hours with no per-test ids; it yields no attributable evidence and is not claimed.

### 14.3 Bounded real MH-1 acceptance (§5.3)

Runtime: RTX 3090, PyTorch 2.13.0+cu126, mace-torch 0.3.16, TRAIN2 `cueq_pure`. Executed in a disposable scratch copy of `05_mace_training/LTA/mh1/FP32` (external campaign untouched); the stored realization references the doctor artifact `…/foundation-selected-head/mace_mh_1-omat_pbe.model` (`training_checkpoint_sha256 e8f90826a78b549d…`, qualification digest `f158457777259402…`).

- The copy first refused the pre-repair failed run's materialization because it binds the original workspace's absolute `output_directory` — a relocation property of the copy, not of this repair; the zero-update run root was removed **in the scratch copy only** and `cross-validate` rerun.
- MACE log: `Using foundation model …/foundation-selected-head/mace_mh_1-omat_pbe.model as initial checkpoint`; parsed `foundation_head='omat_pbe'`, `multiheads_finetuning=True`, `enable_cueq=True`. No `remove_pt_head` / state-dict size-mismatch.
- Execution reached epoch-0 gradient updates: 247/51,670 updates (~5.7 update/s once warm) before a deliberate SIGINT; the run ended `status=cancelled` cleanly.
- **PENDING:** real-MH-1 reconstruction of a durable TRAIN2 epoch checkpoint (needs ≥1 epoch = 5,167 updates) and the full previously-failing CV path. Reconstruction from the selected-head checkpoint is proven on the MH-1-shaped real-MACE fixture, not yet on real MH-1. Long production-scale qualification remains deferred.

### 14.4 Residual risk / closeout

- r8 pre-launch trainer harness is stale at base (pre-existing; out of scope). Recommended follow-up: repair it rather than add a parallel harness.
- Same-workspace retry in the *real* MH-1 workspace is expected to proceed (materialization `output_directory` matches there) but was not executed, per the read-only boundary.
- PEM FF-001: this is another affected surface of the same known duplicated-construction mechanism (launch vs reconstruction foundation), repaired by one shared invocation binding; no independent recurrence → no new PEM family or count.
- Documentation: no current architecture/specification prose routes P5 TRAIN2 to the raw source; no permanent doc or PDF change.
- Disposition: **implementation complete; ready for D4 Review.** Archive on accepted closeout once §14.3 pending evidence is either run or explicitly risk-accepted.


## 15. Independent D4 implementation Review — reopen

**Reviewed candidate:** `a74ed1ca373da2815e5d9f528305eca9c066e95e`  
**Verdict:** **NO-PASS / bounded D4 repair required**  
**Serious Challenge:** **NONE**

The implementation correctly separates the raw scientific source foundation from the selected-head TRAIN2 construction checkpoint at the principal launch and reconstruction boundaries. The new selected-head ancestry checks, trainer-side source/training authentication split, provider routing, source-only consumer preservation, and focused distinct-file tests are directionally conforming.

One implementation blocker and one required evidence closure item remain.

### B1 — BLOCKER: the invocation-scoped TRAIN2 realization is still re-resolved by optimizer-policy construction

The reviewed workplan Section 3.3 requires one authenticated TRAIN2 construction binding to be resolved once per P5 invocation and reused by sibling TRAIN2 consumers. Candidate `a74ed1ca373da2815e5d9f528305eca9c066e95e` does resolve `PostSelectionContext.train2_foundation_realization` once, but `campaign_post_selection_runtime._optimizer_policy_for()` still calls:

```python
_optimizer_policy(..., paths=context.paths, ...)
```

and `_campaign_cli_core._optimizer_policy()` therefore calls `_stored_training_acceleration_realization(...)` again. This independently reopens campaign state for every optimizer/evaluation-policy construction.

The later trainer check

```text
request.training_realization.content_digest
    == optimizer_policy.acceleration_realization_digest
```

is a useful fail-closed guard, but it does not satisfy the one-snapshot contract: a state change between context resolution and a later optimizer-policy read produces a runtime disagreement instead of making every consumer descend from the same invocation binding. Repeated evaluation-model-state resolution also traverses this reread path.

**Required repair — keep it small:**

1. Preserve `_optimizer_policy` as the single optimizer-policy constructor.
2. Add the minimum delegated input needed for P5 to supply an already-resolved training realization **without reopening CampaignStore**. Prefer an optional resolved-realization argument/sentinel over a second optimizer constructor.
3. In `_optimizer_policy_for(context,...)`, when the invocation carries `context.train2_foundation_realization`, pass that exact object to the canonical optimizer-policy constructor. Preserve existing resolution for unaffected/non-phase-separated callers.
4. Assert the resulting policy's `acceleration_realization_digest` and `resolved_acceleration_kernel_mode` descend from that exact carried realization.
5. Add a regression that mutates/replaces the stored `training_acceleration_realization` after `PostSelectionContext` construction and proves the same invocation continues to use its frozen binding rather than rereading the store. A fresh invocation may observe the new current state and must re-authenticate normally.

Do **not** add another context record, cache, wrapper, or fallback.

### E1 — REQUIRED ACCEPTANCE EVIDENCE: exact real-MH-1 reconstruction boundary remains unexecuted

The bounded RTX 3090 run materially improves confidence: MACE launched from the doctor-produced selected-head checkpoint with `foundation_head=omat_pbe`, avoided the old `remove_pt_head` mismatch, and reached real gradient updates.

However, the workplan's real-owner acceptance also requires the repaired path to cross the **TRAIN2 checkpoint -> independent reconstruction** boundary on real MH-1. The run was deliberately stopped before the first durable epoch checkpoint, so that exact proposition remains unexecuted.

After B1 is repaired and focused/affected regression is green, run only the minimum real-MH-1 continuation needed to:

1. produce one durable TRAIN2 epoch checkpoint;
2. invoke the ordinary P5 provider reconstruction/EVAL2 authentication on that checkpoint;
3. confirm reconstruction uses the same selected-head training checkpoint and does not re-enter raw-source head removal or architecture mismatch.

A complete multi-fold/full-production qualification is **not** required for this repair. Stop once this owner/consumer boundary is proven. Long production qualification remains deferred.

### Non-blocking review observations

- The new dependency from `campaign_post_selection_runtime` to the existing CLI-core realization helpers is not a new circular-import defect: those imports are function-local and the runtime already depended on CLI-core policy/path helpers. Do not refactor modules solely for this repair.
- The reported 10 affected-suite failures are pre-existing/stale-test failures rather than evidence of this candidate's routing defect; they should not be repaired inside this narrow cycle unless the B1 delta directly touches them.
- Same-workspace recovery is adequately covered by the assembled owner-level retry test for this cycle; the inability to reuse an externally relocated scratch copy does not establish a product defect.

### Reopen disposition

Repair B1, rerun the new routing suite plus directly affected regression, and obtain E1. Then request a fresh D4 Review. No D1/D2/D3 redesign, tolerance change, new compatibility mechanism, or broader qualification campaign is authorized.


## 16. Reopened implementation continuation — B1 repaired, E1 pending

**Reopen base:** `e0b04a5998b0c505559c5335997e81f8efa61c4b`
**Scope:** D4 blocker B1 only; no D1/D2/D3 change or Serious Challenge.

### 16.1 B1 implementation

- `_campaign_cli_core._optimizer_policy` remains the canonical optimizer-policy constructor and now accepts optional `resolved_training_acceleration_realization`. When supplied, it builds policy realization fields from that exact record without reopening `CampaignStore`; callers that omit it keep the existing stored-record resolution.
- `campaign_post_selection_runtime._optimizer_policy_for` supplies `context.train2_foundation_realization` when present and checks that the returned policy's realization digest and resolved kernel mode equal that carried record. A context without a resolved realization retains the prior constructor call behavior.
- No additional context record, cache, wrapper, fallback, or optimizer constructor was added.
- The regression is in `test_phase_separated_mh1_p5_trains_and_reconstructs_from_selected_head` in `tests/test_mlff_p5_train2_foundation_routing.py`. After building a real P5 context, it replaces the stored realization with a same-byte checkpoint at a different locator. The existing context retains the original path and its optimizer policy retains the original digest/kernel; a newly built context resolves and binds the replacement path/digest/kernel. The stored fixture record is restored before the assembled P5 run continues.

### 16.2 Focused and directly affected regression

Executed serially in Conda environment `mace` (one concurrent test job):

1. `conda run -n mace python -m pytest -q -ra tests/test_mlff_p5_train2_foundation_routing.py tests/test_mlff_target_size_canonical_optimizer_settings.py tests/test_mlff_cueq_train_default1.py` — **110 passed**, 458 warnings, 63.69 seconds. Includes the distinct-source/selected-head routing suite, assembled P5 launch/provider reconstruction, and the new invocation-snapshot/fresh-resolution regression.
2. `conda run -n mace python -m pytest -q -ra tests/test_mlff_target_size_optimizer_normalization.py tests/test_mlff_production_global_train_scheduler.py` — **103 passed**, 6,738 warnings, 546.23 seconds.

These are focused fixture/regression evidence. They do not constitute the real-MH-1 E1 checkpoint evidence or production qualification.

### 16.3 E1 environment boundary

E1 was **not executed** in this session. Preflight command `conda run -n mace python -c 'import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.device_count())'` returned PyTorch `2.13.0+cu126`, CUDA unavailable, and device count `0`; `nvidia-smi` could not communicate with the NVIDIA driver. Inspection of `/home/samjin/QE/lammps-proj/zeolite/05_mace_training/LTA/mh1/FP32/campaign.toml` confirmed `training.device = "cuda"` and TRAIN2 `training_backend = "cueq"`. The run-root inventory under `.mdstats/post-selection/g1/runs/cfe00a1420621581b00539cd64e9cf648edcb1b3efc2aab45e8e2ed64f1037c8` contains materialization/log files but no durable epoch checkpoint. The available log remains the prior raw-source `remove_pt_head()` failure; it cannot establish post-repair checkpoint reconstruction.

The external campaign and trajectory inputs remained read-only. No real-MH-1 epoch checkpoint was produced and no ordinary provider/EVAL2 reconstruction was attempted on a real-MH-1 checkpoint. E1 remains required on the intended CUDA/CuEq runtime. Keep this workplan reopened and defer fresh D4 Review until E1 is completed; long production qualification remains out of scope.


## 17. Independent D4 re-Review of reopened implementation

**Reviewed candidate:** `467018ae309a679fbdaadbe80f9d47805344831b`  
**Review basis:** reopened Section 15 plus the accepted workplan  
**Verdict:** **NO-PASS FOR CLOSURE — CODE CONFORMS; E1 REQUIRED EVIDENCE PENDING**  
**Serious Challenge:** **NONE**

### 17.1 B1 recheck — CLOSED

The reopened B1 is repaired without broadening the design.

- `_optimizer_policy(...)` remains the one canonical optimizer-policy constructor.
- P5 `_optimizer_policy_for(context,...)` now supplies `context.train2_foundation_realization` when that invocation has one.
- With that argument present, `_optimizer_policy` does not call `_stored_training_acceleration_realization(...)`; therefore sibling P5 policy/evaluation consumers no longer reopen CampaignStore to select a different realization.
- The returned optimizer policy is checked against the carried realization's exact `content_digest` and `training_kernel_mode`.
- Callers outside this P5 snapshot path retain the prior stored-record resolution behavior.
- The regression changes the stored realization after context construction, proves the existing context retains its original TRAIN2 path/digest/kernel, and proves a fresh context resolves the replacement normally.

No second optimizer constructor, durable cache, context record, fallback, or compatibility layer was introduced. This satisfies Section 15 B1 and the workplan's one-invocation/one-binding requirement.

### 17.2 Affected-surface recheck — PASS

The B1 delta is limited to the canonical optimizer constructor's delegated input, P5 policy projection, one regression, and workplan evidence. The previous candidate's accepted routing remains intact:

- scientific source identity remains the raw source checkpoint/head;
- phase-separated TRAIN2 launch uses the doctor-qualified selected-head checkpoint;
- all P5 TRAIN2 provider reconstruction paths use `context.train2_foundation_path`;
- source-only residual/baseline consumers remain on `method_policies.foundation_model`;
- trainer authentication still separately checks source head identity and TRAIN2 checkpoint realization/bytes;
- EXTRACT1 remains single-owned.

The reported post-B1 regression is adequate for the code delta: **110 passed** in the focused routing/canonical-optimizer/CuEq-default set and **103 passed** in optimizer-normalization/global-scheduler regression. No new code failure is reported.

### 17.3 Coordination drift — corrected by this Review

Before this Review, `workplans/active/README.md` still described candidate `a74ed1ca` and B1 as open even though `467018ae309a679fbdaadbe80f9d47805344831b` had repaired it. That is stale coordination state, not a product defect. The active index is updated with this Review so it now identifies E1 as the sole blocker.

### 17.4 E1 — SOLE REMAINING BLOCKER

E1 remains unexecuted. The latest implementation session had no usable CUDA device, and the real MH-1 run root still has no post-repair durable epoch checkpoint. Therefore the exact required proposition remains unproven:

```text
real MH-1 selected-head TRAIN2
  -> durable epoch checkpoint
  -> ordinary authenticate_post_selection_provider / EVAL2 reconstruction
  -> same selected-head construction foundation
  -> no raw-source remove_pt_head / architecture mismatch
```

Protocol acceptance cannot convert an unavailable required check into a pass.

No further implementation change is requested. On the intended CUDA/CuEq host, run only far enough to create one durable epoch checkpoint and let the ordinary P5 provider/EVAL2 reconstruction authenticate it. Full multi-fold CV, final production, and long GPU qualification are not required for this repair.

### 17.5 Disposition

- D1/D2/D3: unchanged; no Challenge.
- D4 code conformance: **PASS on current review evidence**.
- Required real-owner integration evidence: **INCOMPLETE (E1)**.
- Overall workplan closure: **NO-PASS / remain open solely for E1**.
- Further code repair: **NONE identified**.

After E1 is recorded, a final closure Review should verify only that evidence against candidate `467018ae309a679fbdaadbe80f9d47805344831b` (or a descendant that changes review/evidence artifacts only). Do not restart a broad implementation campaign unless E1 exposes a concrete defect.


## 18. Current execution handoff — E1 only

**Current reviewed code candidate:** `467018ae309a679fbdaadbe80f9d47805344831b`  
**Current coordination descendant:** `06c42c0b9936683c937a174ea222e3222f669fa4`  
**Code disposition:** **PASS**  
**Only open acceptance item:** **E1 real-MH-1 durable-checkpoint reconstruction evidence**

No additional product-code change is authorized unless E1 exposes a concrete defect.

### 18.1 Required execution

On the intended CUDA/CuEq host, use the existing real MH-1 campaign and repaired branch to continue only far enough to:

1. produce the first durable TRAIN2 epoch checkpoint from the qualified selected-head `omat_pbe` checkpoint;
2. allow the ordinary P5 provider/EVAL2 reconstruction path to authenticate and reconstruct that checkpoint;
3. record evidence that reconstruction uses the same selected-head TRAIN2 foundation and does not invoke raw-source selected-head removal or reproduce the prior architecture/state-dict mismatch.

The evidence must exercise the real production owner path. A fixture, manually reconstructed model, or helper-only probe does not close E1.

### 18.2 Stop condition

Stop once the first durable checkpoint has crossed the ordinary provider/EVAL2 reconstruction boundary successfully. Do **not** continue into full multi-fold CV, final production, long-running GPU qualification, or unrelated cleanup solely for this workplan.

If E1 succeeds, update this workplan with the exact candidate, runtime, checkpoint/reconstruction evidence, and request final closure Review.

If E1 fails, preserve the failure evidence and reopen only the concrete affected D4 owner. Do not pre-emptively change tolerances, MACE architecture, CuEq policy, EXTRACT1, scheduler policy, or source/training identity semantics.
