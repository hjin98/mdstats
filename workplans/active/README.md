# Active workplans

Active workplans are temporary engineering coordination contracts. They do not define current mdstats product behavior by repository presence alone; current behavior remains owned by accepted D1-D4 authority and conforming implementation.

## Current active MLFF work

### `pi_train` / MVSEL2 diversity + production-performance restoration cycle

Branch: `design/mlff-pi-train-fps-diversity-restoration`

Canonical workplan pointer:

- `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_CURRENT.md`

The active plan is the exact Revision-8 composition of immutable Revision 5, immutable Revision 6, immutable Revision 7, and `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_8.md`. Final independent workplan review is `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_REVISION_8_REVIEW.md` with disposition **PASS AS WORKPLAN**.

The stakeholder direction is to restore the latest mature pre-P6 selection path — selector-relevant DATA7 -> TargetCoverageReference/FEAS1 -> NEIGHBOR1/MVIDX1 -> optimized MVSEL2/MVSTATE2 -> optimized REPAIR2 -> bounded/progressive independent MVQUAL — beneath the current one-P_train/P2/prepared-generation architecture, dropping only concretely incompatible historical target-size topology and historically rejected execution experiments.

The restoration explicitly includes current-compatible performance machinery: shared resource budgeting, deterministic bounded scheduling, exact file-backed/OOC sparse construction with disk and descriptor bounds, locality/native MVSEL2 kernels, certified lazy execution, the final recovered native worker-preflight policy, authenticated restart/history and post-repair invalidation, REPAIR2 factorization/parallel proposal scoring/checkpoint reuse, and serial-rung/parallel-family progressive MVQUAL. Scientific outputs remain invariant to execution width/backend/chunk/queue/restart choices.

Current `TargetTrainingOrder` is a complete permutation owner. Therefore assembled acceptance must run the optimized MVSEL path through all of `P_train`, not merely the largest configured target-size rung, and must exercise restart in that suffix when `|P_train| > Nmax_current`.

The current UID-capable target-order product method remains under **SERIOUS CHALLENGE**. Implementation must begin at R1 D1/D2 historical reconstruction, independent falsification and required human ratification, followed by the R2 exact semantic + performance + provenance dependency-closure census before production restoration. PASS of the workplan is not acceptance of the restored scientific/numerical method.

## Recently closed MLFF work

The CV competence threshold separation/parameterization cycle on branch `fix/mlff-cv-competence-threshold-separation` closed **PASS**. Its accepted design separates foundation CV checkpoint competence `tau_cv`, held-out CV threshold `theta_cv`, and production checkpoint quality `tau_prod`, with role-specific invalidation and no duplicate threshold/translation machinery.

Final review and closeout records are archived under:

- `workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_PARAMETERIZATION_IMPLEMENTATION_REVIEW_REOPEN.md`;
- `workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_AND_PARAMETERIZATION_CLOSEOUT_2026-09-15.md`.

Production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred to the final complete-release package under the standing MLFF qualification policy.

Completed/superseded workplans belong under `workplans/archive/` after their active cycle closes.