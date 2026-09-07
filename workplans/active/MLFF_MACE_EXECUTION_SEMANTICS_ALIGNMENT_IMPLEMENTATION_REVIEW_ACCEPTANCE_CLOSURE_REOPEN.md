---
kind: implementation-workplan-review-reopen
workplan_id: MLFF-MACE-EXECUTION-SEMANTICS-ALIGNMENT-IMPLEMENTATION-REVIEW-ACCEPTANCE-CLOSURE
parent_workplan_path: workplans/active/MLFF_MACE_EXECUTION_SEMANTICS_ALIGNMENT_IMPLEMENTATION_REVIEW_THIRD_REOPEN.md
governing_workplan_path: workplans/active/MLFF_MACE_EXECUTION_SEMANTICS_ALIGNMENT_REOPEN_WORKPLAN.md
protocol_version: 5.15.0
status: acceptance-evidence-required
created_date: 2026-09-07
reviewed_source_branch: rework/mlff-target-size-normalization-practical-ceiling
reviewed_implementation_commit: bbaf10e07220be81f76ce1243398da731fa440ee
reviewed_parent_commit: 014294f20c71932c2f392d01dce8741d3485c810
design_verdict: pass-frozen-architecture-unchanged
source_conformance_verdict: pass-t1-source-repair
implementation_review_verdict: no-pass-acceptance-incomplete
precedence: This is an evidence-closure continuation of the existing implementation-review lineage, not a new scientific or architectural workplan. It narrows the third reopen by recording T1 source closure and the remaining executable acceptance obligations. All earlier governing scientific, architectural, compatibility, currentness, and simplicity requirements remain binding.
---

# MLFF MACE execution-semantics alignment — acceptance closure reopen

## 0. Verdict

**Software Design / frozen architecture: PASS.**
**T1 source repair at `bbaf10e07220be81f76ce1243398da731fa440ee`: PASS.**
**Implementation closure: NO-PASS — executable acceptance remains incomplete.**

No new scientific or architectural defect was found in the `lr-norm-8` implementation delta. The prior hard-coded P5 live-state contradiction is repaired in the existing owners and no duplicate checkpoint/state authority was added.

The remaining work is acceptance closure only. Do not redesign P3/P4/P5, do not restore per-epoch full TRAIN2 companions, and do not add a new evaluation-state identity or checkpoint registry.

---

## 1. T1 source repair accepted

The reviewed candidate correctly implements the third-reopen repair:

1. `POST_SELECTION_EVALUATION_MODEL_STATE = "live"` is removed from P5 orchestration.
2. P5 checkpoint representation is derived from the existing optimizer-policy owner using the existing `target_size_evaluation_model_state()` rule:
   - EMA enabled -> `ema`;
   - EMA disabled -> `live`.
3. The real checkpoint-ranking loop derives that state from the same optimizer policy already used for the run.
4. Held-out outer evaluation resolves the same policy-derived state from the run seed/horizon.
5. Legacy/reopened representative re-evaluation flows through the same `evaluate_post_selection_run_candidates()` owner.
6. Qualification/P7 member access resolves the state from the published member's optimizer seed and current production horizon rather than a hard-coded alias.
7. `allow_forward_override` no longer suppresses native-checkpoint EMA/live admission. The only remaining exception is the existing bounded synthetic-shell case where no native MACE checkpoint state exists.
8. `POST_SELECTION_METHOD_RECIPE_VERSION` advances once from v3 to v4, preserving one shared currentness owner across scratch, naive fine-tuning, and replay.
9. The previous S1/S2/S3 repairs remain intact: ordinary P5 `Default` reconstruction, explicit fitted E0s, one latest continuation companion, immutable per-epoch JSON boundaries, no per-epoch full `.pt` companion family, native weighted E/F/S loss, replay LR/duplication controls, and historical DATA8/P5 readability separation.

This is the intended minimum-complexity realization. No further source change is justified merely to restate the same rule elsewhere.

---

## 2. Remaining blocker A1 — exact final executable evidence is absent

For `bbaf10e07220be81f76ce1243398da731fa440ee`:

- no GitHub Actions run is attached to the SHA;
- no commit-status checks are attached to the SHA;
- the implementation delta contains no final affected-regression / real-MACE execution record;
- the independent review environment cannot clone the repository because outbound DNS/network access is unavailable, so it cannot replace the missing execution evidence locally.

Under Protocol 5.15, a required affected regression or integration check that did not execute is not a pass. Source inspection cannot substitute for the required executable closure.

Run the final acceptance on one exact executable candidate after all material code changes. Required real-MACE checks must execute under `mace-torch==0.3.16`; required skips are incomplete acceptance.

---

## 3. Remaining blocker A2 — two T1 acceptance claims still need discriminating executable oracles

The new test source strongly improves T1 coverage: the real replay run now exercises the production checkpoint-ranking loop with EMA enabled and multiple native checkpoints, and the explicit historical-live counterfactual fails both with and without a numerical forward override. Preserve those tests.

Two task-specific claims still need evidence that can reject the corresponding regression rather than only source plausibility.

### A2.1 Serialized v3 currentness cutover

The current tests create an in-memory v3 identity/authorization by `dataclasses.replace(...)`, while the retained static fixture is v2. This proves digest/current-owner rejection but does not prove that an actually serialized previous-generation v3 method/CV/acceptance chain remains readable history and is rejected by the current v4 authorization owner.

Close this cheaply using existing serializers/readers only:

- mechanically capture or construct one exact v3 serialized method + minimum CV plan/acceptance chain using the pre-v4 schema;
- deserialize it through the current readers;
- prove the real final-production authorization owner rejects it against v4 before trainer launch;
- prove corrected v4 CV authorization is admitted by the same owner.

Do not add a migration layer or new historical schema.

### A2.2 Earlier-EMA representative through outer and qualification consumers

The real replay assembled test currently executes checkpoint ranking with `outer_evaluation_frame_uids=None`, then manually authenticates the earliest EMA checkpoint. That closes the ranking/provider state owner but does not execute the held-out outer consumer on an earlier EMA representative.

Likewise, existing P7 tests use the established toy-checkpoint / bounded-forward seams. Those remain useful P7 owner tests, but because the synthetic-shell exception is intentionally allowed below the real state owner, they are not by themselves a discriminating oracle for the native historical EMA representation.

Using existing fixtures/owners, add a small complementary acceptance path that establishes:

- an EMA-enabled P5 run has at least two native MACE checkpoints;
- an earlier checkpoint is the representative actually consumed by held-out outer evaluation, and that outer evaluation authenticates the EMA representation successfully;
- the same frozen native representative can be consumed through the P7/qualification `member_provider` path using the policy-derived state;
- an injected hard-coded `live` request for that same native earlier checkpoint would fail, so the oracle cannot remain green under the retired behavior.

This may be one test or a small complementary set. Do not create a new harness if the existing real-MACE assembled fixture plus current publication/member-provider owners can establish the claims.

---

## 4. Final acceptance set

On one exact final SHA, execute and record at minimum:

- focused T1 EMA/live state-representation and v3->v4 currentness tests;
- `tests/test_mlff_mace_execution_semantics_assembled.py` with all required real-MACE cases executing;
- `tests/test_mlff_target_size_p5_r6_cutover_authorization.py` including serialized v3 currentness evidence;
- P5 scratch / naive / replay affected regression;
- TRAIN2 checkpoint, immutable boundary, restart, and continuation regression;
- P5 representative/outer evaluation regression including the earlier-EMA case;
- qualification/member-provider regression including the native earlier-EMA member case;
- historical DATA8 compatibility/currentness regression;
- real non-divisible P3 integration and P3 EMA/live preservation;
- MACE wrapper/source-qualification/objective/export weighting regression;
- repository/project-required checks;
- broader MLFF regression if the final affected surface cannot be bounded confidently.

Record exact SHA, commands, dependency identity, and pass/fail/skip counts. A required skip is not a pass.

---

## 5. Closure rule

If the acceptance set above executes successfully on the final candidate with no new affected regression, perform one fresh independent Software Design closure review. At that point, absent a new genuine blocker, archive/close the governing MACE execution-semantics repair workplan and its review amendments together.

Do not request another source redesign pass merely because executable evidence was previously missing.
