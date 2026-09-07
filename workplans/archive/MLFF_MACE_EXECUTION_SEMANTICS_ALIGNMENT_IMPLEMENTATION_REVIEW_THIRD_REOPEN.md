---
kind: implementation-workplan-review-reopen
workplan_id: MLFF-MACE-EXECUTION-SEMANTICS-ALIGNMENT-IMPLEMENTATION-REVIEW-THIRD-REOPEN
parent_workplan_path: workplans/active/MLFF_MACE_EXECUTION_SEMANTICS_ALIGNMENT_IMPLEMENTATION_REVIEW_SECOND_REOPEN.md
governing_workplan_path: workplans/active/MLFF_MACE_EXECUTION_SEMANTICS_ALIGNMENT_REOPEN_WORKPLAN.md
protocol_version: 5.15.0
status: implementation-repair-required
created_date: 2026-09-07
reviewed_source_branch: rework/mlff-target-size-normalization-practical-ceiling
reviewed_implementation_commit: 3ff14212363791d0af63d6c747b923851c584c18
reviewed_parent_commit: 35986072441175bf783f89b3b6c570235de6541c
design_verdict: pass-frozen-architecture-unchanged
implementation_review_verdict: no-pass
precedence: This is a bounded continuation of the existing MACE execution-semantics implementation-review lineage. It does not create a new scientific workplan. The governing workplan, first review reopen, final design closure, and second review reopen remain authoritative except where this file supplies the concrete composed-state repair and acceptance obligations surfaced by the third independent implementation review.
---

# MLFF MACE execution-semantics alignment — third independent implementation review reopen

## 0. Verdict

**NO-PASS / one composed runtime blocker plus final executable-evidence closure remain.**  
**Frozen scientific architecture and high-level P3/P4/P5 ownership: PASS / unchanged.**

Reviewed implementation: `3ff14212363791d0af63d6c747b923851c584c18` (`lr-norm-7`), exactly one commit above the second reopen.

The implementation substantially and correctly closes the three explicit repair families from the second reopen:

- **S1 source/owner repair:** ordinary post-selection scratch/naive reconstruction now resolves pinned MACE `Default`, P3 keeps `target_head`, replay keeps explicit `pt_head`/`target_head`, and ordinary P5 uses its explicit fitted E0s rather than foundation E0s;
- **S2 reduction:** the per-epoch full `train2_runtime_epoch-*.pt` companion family is removed; only the latest continuation companion remains, with immutable per-epoch JSON boundary summaries plus raw MACE checkpoints for historical evaluation;
- **S3 acceptance shape:** a serialized pre-repair v2 method/CV/acceptance fixture is read through current deserializers, and the assembled replay test now checks non-default LR/EMA, below-threshold target/replay ratio, no duplication, and native weighted-loss coefficients.

Those repairs must be preserved. One blocking inconsistency remains at the composition boundary between S2 and the real P5 checkpoint-selection owner, and the exact candidate still lacks the required final executable acceptance record.

Do not reintroduce per-epoch full companions and do not add a new checkpoint/state authority to repair this.

---

## 1. Global invariant and root-cause analysis

The governing product invariant remains:

> every checkpoint ranked, selected, published, or qualified by mdstats must be evaluated in the exact scientifically authorized model-state representation that the authenticated MACE/optimizer policy actually defines, and a bounded numerical test double must not weaken checkpoint provenance or state identity.

Pinned MACE 0.3.16 establishes the relevant physical execution fact:

- with EMA enabled, validation executes inside `ema.average_parameters()`;
- raw epoch checkpoints are also saved inside `ema.average_parameters()`;
- therefore an earlier raw epoch checkpoint contains the EMA checkpoint representation, not the unavailable historical live parameter state.

The accepted storage reduction is therefore sound: raw checkpoint + immutable epoch boundary is sufficient to evaluate the historical EMA representation, while the single latest continuation companion remains sufficient for exact restart/latest live-state recovery.

The remaining defect is that P5 orchestration still requests the wrong representation.

---

## 2. Blocker T1 — real P5 asks for `live` on every historical checkpoint even when EMA is enabled

### 2.1 Production contradiction

`campaign_post_selection_runtime.py` still declares:

```text
POST_SELECTION_EVALUATION_MODEL_STATE = "live"
```

and `evaluate_post_selection_run_candidates()` passes that value to `authenticate_post_selection_provider()` for **every checkpoint candidate** in the trajectory. The same global value is used again for held-out outer evaluation and by qualification's published-member provider path.

After S2, `authenticate_train2_checkpoint_provider()` correctly refuses an earlier EMA-enabled checkpoint requested as `live`, because no historical live state exists after the full per-epoch companions were removed. For a native MACE checkpoint and no numerical override, the code raises:

```text
An earlier TRAIN2 checkpoint saved with EMA cannot be evaluated as live state.
```

Thus a real EMA-enabled P5 run with more than one checkpoint cannot complete its normal checkpoint-ranking loop: the first non-latest candidate is requested as `live` even though its authenticated raw checkpoint is the EMA representation.

This is a direct implementation nonconformance with the second reopen requirement that an earlier EMA-enabled checkpoint be evaluated as MACE's checkpoint representation and that unavailable historical live state fail closed.

### 2.2 Why the new assembled test does not close this owner

The assembled replay test constructs the P5 context with a bounded `inference_evaluator`. That sets `allow_forward_override=True` during the real checkpoint-selection loop.

The current shared authentication helper uses `allow_forward_override` not only to substitute numerical forwarding, but also to suppress the earlier-EMA/live rejection. Consequently the bounded arithmetic double changes checkpoint **state-admission semantics**, which is above the permitted numerical-double boundary.

The test later authenticates the earliest checkpoint directly using `evaluation_model_state="ema"` and `allow_forward_override=False`. That proves the reduced historical EMA path works, but it proves a different state request from the actual P5 orchestration, which still requests `live`.

A test can therefore remain green while the real production owner fails. This is a proxy-proof acceptance failure as well as a runtime defect.

---

## 3. Required repair — alter existing state resolution; add no new state machinery

### 3.1 One policy-derived checkpoint representation

Replace the global hard-coded P5 `live` execution authority with the already established policy rule:

```text
EMA enabled  -> evaluate checkpoint candidates as EMA
EMA disabled -> evaluate checkpoint candidates as live
```

The resolved value must come from the authenticated run/method optimizer semantics already present in current configuration/materialization/runtime authority. Reuse existing `EVALUATION_MODEL_STATE_LIVE` / `EVALUATION_MODEL_STATE_EMA` semantics and, if useful, the existing P3 `target_size_evaluation_model_state()` rule. Do not add another enum, registry, checkpoint database, or parallel scientific identity.

Apply the same resolved representation consistently to all P5 descendants that authenticate the selected checkpoint:

- per-checkpoint target/replay monitor ranking;
- held-out outer evaluation after representative freeze;
- legacy/reopened representative re-evaluation;
- final-production member authentication;
- P7/qualification access to the frozen published P5 member;
- any other direct P5 checkpoint-provider consumer found by affected-surface review.

The exact checkpoint bytes and immutable per-epoch boundary remain the historical state authority. Do **not** restore historical full live/EMA companions.

### 3.2 Numerical overrides must not weaken provenance/state semantics

Narrow `allow_forward_override` back to its intended role: permitting a bounded synthetic provider shell / substituted numerical forward where the fixture genuinely lacks native model state.

For a native MACE checkpoint state, the presence of a numerical evaluator must not change:

- live-vs-EMA admissibility;
- raw-checkpoint SHA authentication;
- boundary-summary authentication;
- architecture matching;
- method/runtime/currentness checks.

In particular, requesting historical `live` from an EMA-enabled native checkpoint must fail whether `allow_forward_override` is `False` or `True`. If a special exception is still required for old toy fixtures with no native MACE state, scope it to that synthetic-shell condition rather than the broad boolean itself.

### 3.3 Currentness cutover

This correction can change which checkpoint wins P5 ranking under the same user configuration: an EMA-enabled v3 method currently records the same method identity while the executable evaluation representation changes from the old hard-coded `live` convention to the real EMA checkpoint representation.

Use the **existing method-recipe cutover owner** rather than adding another digest:

- advance `POST_SELECTION_METHOD_RECIPE_VERSION` once from v3 to a new current generation;
- apply the cutover globally to the shared P5 method identity rather than creating mode-specific versions;
- old v3 CV/final authorization remains readable history but cannot authorize the corrected current method;
- P4 `N_selected` / `T_selected` remains unchanged by this P5-only cutover.

No new method-identity schema field is required merely to encode this deterministic EMA-policy rule; the shared optimizer identity already binds `ema`/`ema_decay`, while the recipe token binds the algorithmic interpretation.

---

## 4. Acceptance required for T1

Use existing owners and fixtures. Do not create another acceptance harness.

At minimum establish on the final candidate:

1. **EMA-enabled multi-checkpoint P5 assembled run:** execute real `MacePostSelectionTrainer` + qualified wrapper + native MACE TRAIN2, produce at least two raw checkpoints, then execute the real `evaluate_post_selection_run_candidates()` owner through all candidates. State authentication must be native and must use the policy-derived EMA representation. A bounded numerical predictor may remain only if it no longer changes state/provenance admission.
2. **Counterfactual guard:** the same earlier native EMA checkpoint explicitly requested as `live` fails closed both with and without a numerical forward override.
3. **EMA-disabled path:** scratch/naive non-replay P5 continues to use live checkpoint state and real provider/EVAL2 authentication.
4. **Representative/outer path:** when the selected representative is an earlier EMA checkpoint, held-out outer evaluation authenticates that same EMA state successfully.
5. **Qualification path:** a published P5 member is authenticated using the same policy-derived state convention; no hard-coded live alias remains in qualification.
6. **Currentness:** stored/readable v3 P5 authorization cannot authorize the new method generation; corrected CV can authorize corrected final production.
7. **P3 preservation:** target-size `target_size_evaluation_model_state()` semantics and restart/EVAL2 remain unchanged and green.
8. **S2 preservation:** exactly one latest `train2_runtime.pt` exists; no `train2_runtime_epoch-*.pt` family returns.

The acceptance oracle must be able to fail if the actual P5 owner is switched back to hard-coded `live` under EMA.

---

## 5. Final executable-evidence blocker T2

The exact reviewed SHA `3ff14212363791d0af63d6c747b923851c584c18` has no GitHub Actions run and no commit status attached, and the implementation delta contains no final R8-D execution-evidence record. This review environment also cannot fetch the repository into the execution container, so it cannot independently substitute local test execution for missing repository evidence.

After T1 changes, all prior affected tests are stale for that surface anyway. On one exact final executable SHA, record and run:

- focused T1 state-representation/currentness tests;
- P5 scratch, naive, and replay stage-local affected regression;
- TRAIN2 checkpoint/boundary/restart regression;
- historical DATA8/P5 currentness regression;
- real non-divisible P3 integration;
- real replay-enabled P5 integration with LR/EMA/ratio/native-loss assertions;
- P5 representative/outer and qualification-provider regression;
- complete affected-surface MACE wrapper/compatibility/TRAIN2/P3/P5 regression;
- broader MLFF suite if the affected surface cannot be bounded confidently;
- repository/project-required checks.

Required real-MACE tests must execute under `mace-torch==0.3.16`; a required skip is incomplete acceptance. Record exact SHA, commands, pass/fail/skip counts, and dependency identity in the existing evidence convention.

---

## 6. Accepted implementation state to preserve

Do not regress the correctly repaired state at `3ff142...`:

- P5 `Default` reconstruction for ordinary scratch/naive execution;
- explicit fitted P5 E0s for ordinary single-head reconstruction;
- P3 `target_head` and replay `target_head`/`pt_head` reconstruction;
- one qualified MACE wrapper and native weighted stress loss;
- explicit non-replay `multiheads_finetuning=False`;
- replay `force_mh_ft_lr=True` and ratio threshold `0.0`;
- no implicit target duplication;
- complete P3 non-divisible batch exposure;
- historical/current DATA8/MACE compatibility separation;
- static historical P5 authorization fixture and real final-authorization rejection;
- exactly one latest continuation companion plus immutable per-epoch JSON boundary summaries;
- no special checkpoint-inventory filtering for deleted runtime `.pt` files;
- exact latest restart authority;
- P3/P4/P5 scientific ownership and fresh final production.

The repair should alter/remove the hard-coded state alias and overly broad override exception, not rebuild checkpoint persistence.

---

## 7. Disposition

**Software Design / frozen architecture:** PASS — no broad redesign required.  
**Implementation:** **NO-PASS** — T1 and T2 remain blocking.

After T1 is implemented and exact final executable evidence closes T2, perform a fresh independent implementation closure review. If no blocker remains, archive the governing repair workplan and its implementation-review amendments together.