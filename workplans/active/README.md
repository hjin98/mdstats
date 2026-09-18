# Active workplans

Active workplans are temporary engineering coordination contracts. They do not define current mdstats product behavior by repository presence alone; current behavior remains owned by accepted D1-D4 authority and conforming implementation.

## Current active MLFF work

### Replay retention and target-admissibility rework

Branch: `design/mlff-replay-retention-target-admissibility-rework`

Canonical workplan:

- `workplans/active/MLFF_REPLAY_RETENTION_AND_TARGET_ADMISSIBILITY_REWORK_WORKPLAN.md`

This cycle reopens accepted Protocol 6.4 D1/D2 for a post-selection policy revision: TRUE_DFT replay degradation uses configurable 50 meV/angstrom warning and 100 meV/angstrom catastrophic hard defaults; foundation CV defaults are 75/75 meV/angstrom, intentionally more permissive than the 50 meV/angstrom production target ceiling; and P5 checkpoint/final single-best selection is strict minimum authoritative target RMSE among hard-admissible checkpoints. The workplan also requires assessment-policy/currentness ownership to be separated from TRAIN2 trajectory and reusable EVAL2 measurement identity so policy-only edits do not force retraining or discard valid measurements.

Implementation is blocked until the renewed D1 then D2 authority passes Protocol 6.4 review/ratification. R2 passed the prior D1 meaning, but the stakeholder subsequently amended foundation CV defaults to `75/75 meV/angstrom`. The R3 reconciliation now also states that CV authorization does not guarantee the tighter production checkpoint gate and gives `theta_CV` outer-verdict-only currentness. The existing `1:10:1` UniversalLoss coefficients are clarified, not changed. Fresh independent D1 Review R3 of exact target `d761171f3c86c3c79b87a90cfc02ac324c261b1a` (D1 blob `612294ec4680db01a18085e13fbfe5dcfa9fb7ed`) returned **PASS with no SERIOUS CHALLENGE**, and the stakeholder explicitly ratified that exact target on 2026-09-18. Gate B is closed. D2 R1 candidate `e2b39917ab8c16556eb218d6a41e9682331bbca0` (blob `9e12728432d20bc7d16b9c5654bf7833cdee8df9`) is frozen for fresh independent Protocol-6.4 review. D3/D4 implementation remains blocked pending D2 review and stakeholder ratification.


### `pi_train` / MVSEL2 diversity + production-performance restoration cycle

Branch: `design/mlff-pi-train-fps-diversity-restoration`

Canonical workplan pointer:

- `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_CURRENT.md`

The active plan is the exact Revision-8 composition of immutable Revision 5, immutable Revision 6, immutable Revision 7, and `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_8.md`. Final independent workplan review is `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_REVISION_8_REVIEW.md` with disposition **PASS AS WORKPLAN**.

The stakeholder direction is to restore the latest mature pre-P6 selection path — selector-relevant DATA7 -> TargetCoverageReference/FEAS1 -> NEIGHBOR1/MVIDX1 -> optimized MVSEL2/MVSTATE2 -> optimized REPAIR2 -> bounded/progressive independent MVQUAL — beneath the current one-P_train/P2/prepared-generation architecture, dropping only concretely incompatible historical target-size topology and historically rejected execution experiments.

The restoration explicitly includes current-compatible performance machinery: shared resource budgeting, deterministic bounded scheduling, exact file-backed/OOC sparse construction with disk and descriptor bounds, locality/native MVSEL2 kernels, certified lazy execution, the final recovered native worker-preflight policy, authenticated restart/history and post-repair invalidation, REPAIR2 factorization/parallel proposal scoring/checkpoint reuse, and serial-rung/parallel-family progressive MVQUAL. Scientific outputs remain invariant to execution width/backend/chunk/queue/restart choices.

Current `TargetTrainingOrder` is a complete permutation owner. Therefore assembled acceptance must run the optimized MVSEL path through all of `P_train`, not merely the largest configured target-size rung, and must exercise restart in that suffix when `|P_train| > Nmax_current`.

#### R1 status

The authoring/reconstruction half of R1 is complete. The branch now contains proposed reconstruction evidence, exact proposed D1 and D2 overlays, an independent-review handoff, and `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_STATUS.md`.

The proposed method restores the final mature multi-view semantics under current one-`P_train` ownership: correlation-unit-balanced hard family coverage at 0.95, q01/q99 extents, canonical condition/event/profile/extent/correlation/current-user obligations, exact two-phase MVSEL2, configured active-shell REPAIR2, independent MVQUAL, and same-method continuation through the complete `P_train` order.

**No D1/D2 promotion has occurred.** Independent D1/D2 falsification and stakeholder human ratification remain mandatory before accepted-current method-paper promotion and before R2 begins. The current UID-capable product method therefore remains under **SERIOUS CHALLENGE**.

## Recently closed MLFF work

The CV competence threshold separation/parameterization cycle on branch `fix/mlff-cv-competence-threshold-separation` closed **PASS**. Its accepted design separates foundation CV checkpoint competence `tau_cv`, held-out CV threshold `theta_cv`, and production checkpoint quality `tau_prod`, with role-specific invalidation and no duplicate threshold/translation machinery.

Final review and closeout records are archived under:

- `workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_PARAMETERIZATION_IMPLEMENTATION_REVIEW_REOPEN.md`;
- `workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_AND_PARAMETERIZATION_CLOSEOUT_2026-09-15.md`.

Production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred to the final complete-release package under the standing MLFF qualification policy.

Completed/superseded workplans belong under `workplans/archive/` after their active cycle closes.