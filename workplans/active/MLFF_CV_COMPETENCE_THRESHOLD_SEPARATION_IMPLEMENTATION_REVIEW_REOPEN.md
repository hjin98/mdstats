---
kind: implementation-review-reopen-amendment
protocol_version: 6.3.0
status: reopened
parent_workplan: workplans/active/MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_WORKPLAN.md
branch: fix/mlff-cv-competence-threshold-separation
accepted_baseline_commit: 8553ebe9ed86b24dfe910c9e43acc6230d3ece90
reviewed_candidate_commit: 473437e2605f366a1c2c12dd121d6f9b1cf2ba2f
review_disposition: NO-PASS
highest_open_owner: D1
---

# MLFF CV Competence Threshold Separation — Implementation Review Reopen

## 0. Disposition

Independent assembled implementation review is **NO-PASS**. No Serious Challenge is raised against the accepted P5 architecture or against the scientific intent of the proposed 45/45/30 meV/angstrom split. Static reconstruction finds the implemented D4 ownership split materially aligned with the accepted P5 lineage and finds no justification for adding a P5 `TrainingProtocolIdentity`, generic `Eval2EvaluationPlan`, wrapper, shadow registry, or second policy engine.

Closure is blocked by authority/lifecycle/evidence defects that must be repaired before this cycle can be accepted or archived.

## 1. Blocking findings

### B1 — The parent workplan contradicts accepted D3 after its final-review amendment

Accepted D3 states that restored P5 is authorized by `PostSelectionMethodIdentity -> CV/final role policy -> role plan -> run/checkpoint/evaluation evidence`; the broad DATA8-era `TrainingProtocolIdentity` may remain for non-P5/historical consumers but **cannot authorize restored P5**. Current P5 also does not construct a generic `Eval2EvaluationPlan`.

The parent workplan's invariants 19-20, D2->D3 graph, falsification cases 17-21, Gates C/D/E, HAS SP-004 wording, reverse-semantic question, and final acceptance criteria nevertheless require per-run `TrainingProtocolIdentity` plus generic EVAL2-plan policy-digest agreement. Its later “Implementation reconciliation” correctly recognizes that contradiction, but the binding contract was never repaired. The workplan is therefore internally inconsistent and cannot govern closure as written.

**Repair at the plan/D3 handoff, not by adding product machinery.** The authoritative P5 concretization for this cycle is:

```text
PostSelectionMethodIdentity(shared checkpoint constraints)
  + CV/final role policy(role target ceiling)
  -> CV/final role plan
  -> CV/final run plan / run identity / run root
  -> authenticate method + exact role-policy digest
  -> compose one effective CheckpointAdmissibilityPolicy
  -> preparation/TRAIN2 execution
  -> EVAL2 candidate assessment under that same composed policy
  -> fold acceptance or final run evidence binding the run-plan digest
```

A role-ceiling edit must move the corresponding role policy, plan and run identity/root. A shared replay/physical/integrity edit must move the method and both dependent roles. Recovery must authenticate the current plan/run-plan ancestry before reuse; completed evidence is not numerically re-thresholded under another role policy.

Generic `Eval2CheckpointRecord` may remain a reusable content record. It does not gain an added role/policy field solely for this change; policy authority is supplied by the run-plan-bound acceptance/run-evidence lineage. Do not create a duplicate EVAL2 plan or a new P5 protocol identity merely to restate ancestry already owned by the role/run plans.

### B2 — D1 and D2 authority are still explicitly proposed and unratified

`docs/methods/mlff_scientific_method.md` identifies this threshold-separation revision as proposed and pending independent D1 review plus stakeholder ratification. `docs/methods/mlff_numerical_algorithmic_method.md` likewise identifies the D2 revision as proposed and pending independent D2 review plus stakeholder ratification.

The D4 candidate may exist provisionally on the branch, but the cycle cannot close, merge as accepted authority, or archive the workplan while the governing D1/D2 mutation remains proposed. Do not convert successful software tests into authority acceptance.

Required sequence:

1. independently falsify/review the proposed D1 role separation, calibration provenance, evidence-role interpretation, scratch boundary, and downstream-qualification separation;
2. after D1 acceptance, independently review D2 exact predicates, units, inclusive IEEE-754 boundaries, all-fold/all-seed aggregation, dimensional separation, fixed-budget semantics, and stale-evidence behavior;
3. obtain explicit stakeholder ratification of the material D1/D2 revision;
4. only then treat D3/D4 descendants as candidates for accepted-current promotion.

### B3 — Required executable acceptance has not been demonstrated

The branch has documentation-PDF workflow success, but no CI/test status or durable implementation-evidence record demonstrates the focused, affected-regression, recovery, and real-path tests required by the workplan. During this review the available execution environment could not reach GitHub, so the tests are **UNAVAILABLE**, not PASS.

Before re-review, execute and record at minimum:

```text
pytest -q tests/test_mlff_p5_cv_competence_threshold_separation.py
pytest -q \
  tests/test_mlff_target_size_p5_r7_guards.py \
  tests/test_mlff_target_size_p5_r8_guards.py \
  tests/test_mlff_target_size_p5_r10_guards.py \
  tests/test_mlff_target_size_p5_r11_guards.py \
  tests/test_mlff_target_size_p5d_cv_acceptance.py \
  tests/test_mlff_target_size_p5e_production_and_restart.py \
  tests/test_mlff_target_size_p5g_assembled_integration.py \
  tests/test_mlff_p5_cv_no_admissible_outcome.py \
  tests/test_mlff_campaign_cli.py \
  tests/test_mlff_downstream_integration_closure.py
python -m compileall -q mdstats/training_data
git diff --check 8553ebe9ed86b24dfe910c9e43acc6230d3ece90...HEAD
```

If the repository's maintained affected surface is broader than this list after collection/impact analysis, run the broader affected suite. GPU/production-scale qualification remains deferred to the final complete-release package; it is not required to close this CPU/static behavioral repair.

The executable evidence must discriminate at least: foundation CV 42 meV/angstrom pass; production 42 fail; scratch 42 fail; 45 and 30 inclusive boundaries; next-representable-above failures; alternate outer-metric dimensionality; shared replay-gate preservation; no-admissible behavior; fixed horizon/no early stop; one-time schema cutover; post-cutover role-only invalidation; stale run-plan/recovery rejection; explicit old outer `0.030` preservation; generated/example config convergence; and real `cross-validate -> persisted acceptance -> train-production` authorization.

### B4 — Committed temporary D1 staging residue remains in the normative methods tree

`docs/methods/.tmp_d1_threshold_revision.md` contains only `placeholder`. It has no authority or evidentiary role and must be deleted. Do not replace it with another staging artifact or compatibility file.

### B5 — Semantic-history and closeout-learning obligations remain open

This is a material D1/D2/D3 identity/currentness change. Before closure, append the threshold-separation evolution to the existing relevant MLFF post-selection semantic-history owner rather than creating a competing history stream. Record previous vs replacement semantics, stakeholder calibration provenance, one-time P5 currentness cutover, steady-state minimal invalidation, and the preserved downstream-qualification boundary.

Refresh the workplan HAS only if the project-governed accepted PEM basis advances. Perform the Protocol 6.3 closeout-learning assessment after accepted repair/evidence. Mutate `PROJECT-ENGINEERING-MEMORY.md` only if admission criteria are actually met; otherwise record that no PEM mutation is required.

## 2. Static implementation assessment preserved for re-review

The following candidate choices are **not blockers** and should be preserved unless executable evidence falsifies them:

- `PostSelectionMethodIdentity` v3 removes the target-bearing full checkpoint-admissibility digest and binds shared checkpoint constraints instead.
- CV policy v3 owns the foundation-CV checkpoint ceiling; final-production policy v2 owns production checkpoint quality.
- one existing `post_selection_checkpoint_admissibility(...)` composition path builds the effective generic policy from shared constraints plus the authenticated role ceiling.
- `PostSelectionContext.checkpoint_admissibility(run_plan)` checks current method and role-policy ancestry before training and before checkpoint assessment.
- CV and final run plans already bind method + role-policy digests; their plan digest determines role-specific run identity/root, so role-policy edits cannot silently reuse the old run position.
- current CV/final plan recovery compares stored method/role-policy digests against freshly resolved authority before reuse.
- `_completed_fold_acceptance()` and final run-evidence reuse bind exact run-plan digests; they do not authorize cross-policy reuse.
- `[acceptance].maximum_target_force_rmse_ev_per_angstrom` remains `0.030` and retains scratch/production meaning; foundation CV gets its role-specific `0.045` without a global rewrite.
- `acceptance_maximum` remains dimensioned by the selected outer metric and explicit values are preserved.
- no threshold-driven early stopping was introduced and the frozen CV horizon remains the training budget.

Do **not** repair B1 by adding `TrainingProtocolIdentity`/`Eval2EvaluationPlan` to P5. That would duplicate authority, contradict accepted D3, and solve the workplan wording instead of the product problem.

## 3. Re-review acceptance

Implementation review may return PASS only when all of the following are true:

- the parent workplan's contradictory generic TRAIN2/EVAL2 requirements are superseded/reconciled to the accepted P5 role-plan/run-plan lineage above;
- proposed D1 and D2 have completed their owning independent reviews and explicit stakeholder ratification;
- required focused + affected regression + real-path integration evidence has executed and is admissible for the reviewed candidate;
- no candidate-attributable regression remains;
- the temporary methods placeholder is removed;
- semantic history and closeout-learning/HAS obligations are reconciled;
- the assembled implementation still demonstrates 45/45 foundation CV, 30 foundation production, unchanged scratch, unchanged shared replay/physical/integrity gates, fixed-budget training, exact currentness/recovery, and downstream qualification separation; and
- no repair introduces a second checkpoint-policy owner, P5 protocol graph, EVAL2 wrapper/plan, compatibility translator, or duplicated threshold state.

Until then the active cycle remains **reopened / NO-PASS**.