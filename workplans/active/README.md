# Active workplans

Active workplans are temporary engineering coordination contracts. They do not define current mdstats product behavior by repository presence alone; current behavior remains owned by accepted D1-D4 authority and conforming implementation.

## Current active MLFF work

`MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_WORKPLAN.md` remains the parent workplan on branch `fix/mlff-cv-competence-threshold-separation`, based on accepted `main` state `8553ebe9ed86b24dfe910c9e43acc6230d3ece90`.

The earlier assembled implementation review reopened the cycle through `MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_IMPLEMENTATION_REVIEW_REOPEN.md`. Its architectural finding remains valid: restored P5 is authorized through shared method + role-policy + role-plan/run-plan ancestry; broad DATA8 `TrainingProtocolIdentity` and a generic `Eval2EvaluationPlan` are not P5 authority and must not be added merely to restate ancestry.

The first independent D1/D2 review, recorded in `MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_D1_D2_REVIEW.md`, found one remaining authority mismatch: production `30 meV/angstrom` had been written as immutable even though the production role already had a configurable policy input.

On 2026-09-15 the stakeholder clarified and ratified the intended design: **all three foundation post-selection thresholds are configurable policy parameters**, with generated/current defaults `45 / 45 / 30 meV/angstrom` for CV checkpoint competence / default held-out target-force acceptance / fresh-production checkpoint quality. Independent re-review now records **D1 PASS / D2 PASS** in `MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_D1_D2_REREVIEW.md`.

The threshold-policy authority for this branch is now:

- D1: `docs/methods/mlff_post_selection_threshold_policy.md`
- D2: `docs/methods/mlff_post_selection_threshold_numerical_policy.md`
- D3: `docs/arch_manuals/mlff_training_data/85_post_selection_threshold_policy_ownership.md`
- D4 specification: `docs/specs/training_data/mlff_post_selection_threshold_policy_spec.md`

`MLFF_CV_COMPETENCE_THRESHOLD_PARAMETERIZATION_ALIGNMENT.md` is the active D3/D4 handoff. It requires one missing public knob to be wired through the existing owner: foundation `[post_selection.cv].checkpoint_maximum_target_force_rmse_ev_per_angstrom`, default `0.045`. The existing `[post_selection.cv].acceptance_maximum` remains the configurable outer threshold and `[acceptance].maximum_target_force_rmse_ev_per_angstrom` remains the configurable production threshold, default `0.030`.

The previously reviewed D4 candidate is therefore no longer final-conforming solely because foundation CV checkpoint competence is still hard-coded at `0.045` instead of optionally configurable. Repair must alter the existing resolver/config path and generated/public configuration surfaces; it must not add a threshold registry, synchronized alias, wrapper, compatibility translator, P5 protocol identity, generic EVAL2 plan, or second checkpoint engine.

Scratch/replay/shared hard gates, fixed-budget training, common-monitor semantics, frozen target selection, and downstream qualification separation remain unchanged. Production-scale GPU/CuEq/LAMMPS/MLIAP release qualification remains governed by the standing final-release policy and is not an intermediate gate for this cycle.

The preceding post-selection restoration workplan remains closed and archived. This threshold-parameterization cycle does not reopen that archived implementation by default.

There is no active target-order redesign. The withdrawn FPS/coverage Gate-A lineage remains archived and does not alter the accepted target-size method.

Completed/superseded workplans belong under `workplans/archive/`.
