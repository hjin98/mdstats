# Active workplans

Active workplans are temporary engineering coordination contracts. They do not define current mdstats product behavior by repository presence alone; current behavior remains owned by accepted D1-D4 authority and conforming implementation.

## Current active MLFF work

The MLFF CV competence threshold separation/parameterization cycle on branch `fix/mlff-cv-competence-threshold-separation` is **reopened / NO-PASS** after independent assembled implementation re-review of candidate `c632521f6aace258d68406afa1cc9f4c4290c9ac` (implementation commit `00d8b20659ee63830eab6d1b3400287af3caaa55`).

Current review contract:

`MLFF_CV_COMPETENCE_THRESHOLD_PARAMETERIZATION_IMPLEMENTATION_REVIEW_REOPEN.md`

The previously archived closeout `workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_AND_PARAMETERIZATION_CLOSEOUT_2026-09-15.md` remains historical evidence of the attempted closure but is superseded for current lifecycle state until this re-review closes PASS.

The accepted threshold design itself is not challenged: all three foundation post-selection thresholds are configurable role-policy parameters with generated/current defaults `45 / 45 / 30 meV/angstrom` for CV checkpoint competence / default held-out target-force acceptance / fresh-production checkpoint quality. D1/D2 independent re-review and stakeholder ratification remain valid.

D3 architecture and the main D4 ownership implementation are also preserved: `PostSelectionMethodIdentity` owns shared constraints, `CvValidationPolicyIdentity` owns CV checkpoint + outer policy, `FinalProductionPolicyIdentity` owns production policy, and one existing `post_selection_checkpoint_admissibility(...)` path composes the effective run policy. No P5 `TrainingProtocolIdentity`, generic `Eval2EvaluationPlan`, threshold registry, synchronized alias, wrapper, compatibility translator, or second checkpoint engine is required.

Three blockers prevent closure:

1. **Canonical/lifecycle representation drift.** The broad D1/D2 papers still declare the threshold revision proposed/pending review, retain several hard-coded default-value statements where the accepted invariant is parameterized, and route provenance to former active paths; the dedicated D4 threshold spec still says implementation reconciliation is required. These conflict with the closed/accepted claims and must be consolidated without creating parallel authority.
2. **Fail-closed type validation.** The threshold validator currently coerces with `float(...)`, so booleans and quoted numerics can be accepted despite the canonical CLI contract requiring finite-real fields to reject booleans and strings. The existing validation path must be made strict for `tau_cv`, `theta_cv`, and `tau_prod`.
3. **Confounded assembled currentness oracle.** The slow test claiming a checkpoint-only `tau_cv` edit also removes an explicit `theta_cv` override, changing two CV policy fields simultaneously. Add a real-path test that changes only `tau_cv` and proves the expected selective invalidation/currentness boundary.

Recorded passing tests and the successful documentation-PDF build remain applicable to the claims they actually discriminate, but they do not close these counterexamples. Production-scale GPU/CuEq/LAMMPS/MLIAP release qualification remains deferred to the final complete-release package and is not an intermediate gate here.

The archived parent workplan, D1/D2 review records, parameterization handoff, and prior closeout remain under `workplans/archive/`; do not duplicate or restore them merely to repair these bounded findings. Re-close only after the active review contract passes.

Completed/superseded workplans belong under `workplans/archive/`.
