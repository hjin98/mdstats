# Active workplans

Active workplans are temporary engineering coordination contracts. They do not define current mdstats product behavior by repository presence alone; current behavior remains owned by accepted D1-D4 authority and conforming implementation.

## Current active MLFF work

No active MLFF workplan is open for the CV competence threshold separation/parameterization cycle.

The cycle on branch `fix/mlff-cv-competence-threshold-separation` closed **PASS** after final independent re-review. The accepted design is:

- foundation CV checkpoint competence `tau_cv`: independently configurable, default `0.045 eV/angstrom`;
- foundation held-out CV threshold `theta_cv`: independently configurable in the units of `acceptance_metric`, default `0.045 eV/angstrom` for the default target-force metric;
- foundation production checkpoint quality `tau_prod`: independently configurable, default `0.030 eV/angstrom`;
- role-only changes invalidate only their owning role lineage and material dependents;
- shared method identity contains no role target ceiling;
- scratch remains separately governed; and
- no duplicate threshold registry, production alias, P5 `TrainingProtocolIdentity`, generic `Eval2EvaluationPlan`, compatibility translator, wrapper, or second checkpoint engine exists.

Final review and closeout records are archived under:

- `workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_PARAMETERIZATION_IMPLEMENTATION_REVIEW_REOPEN.md`;
- `workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_AND_PARAMETERIZATION_CLOSEOUT_2026-09-15.md`.

Production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred to the final complete-release package under the standing MLFF qualification policy.

Completed/superseded workplans belong under `workplans/archive/`.