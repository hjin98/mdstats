# Active workplans

Active workplans are temporary engineering coordination contracts. They do not define current mdstats product behavior by repository presence alone; current behavior remains owned by accepted D1-D4 authority and conforming implementation.

## Current active MLFF work

### TRAIN2 CuEq FP32 backend-parity requalification

Branch: `design/mlff-train2-cueq-parity-requalification`

Canonical workplan:

- `workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md`

Formal workplan review:

- `workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN_REVIEW_R5.md` — **PASS AS WORKPLAN after Revision-6 repair**; supersedes R4/R3/R2/R1. The D2 numerical challenge itself remains open.
- `workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN_REVIEW_R4.md` — historical fourth review.
- `workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN_REVIEW_R3.md` — historical third review.
- `workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN_REVIEW_R2.md` — historical second review.
- `workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN_REVIEW_R1.md` — historical first review.

A real MACE-MH-1 / `omat_pbe` RTX 3090 doctor realization challenged the current executable TRAIN2 FP32 noise-normalized backend-equivalence rule: force-tail ratios narrowly exceeded the generic ratio ceiling and, more importantly, cross-backend descriptor variation exceeded the absolute `1e-6` stable-channel ceiling while same-backend descriptor repeatability itself reached roughly `1.8-1.9e-6`. The cycle therefore starts at D2 and preserves the current fail-closed/no-silent-fallback D3/D4 behavior until a replacement numerical relation passes fresh independent falsification and stakeholder ratification.

The repair must not tune constants to the observed failure. It must formally source-close the current CuEq acceleration-equivalence family by role/dtype, reconstruct the MPA-0 and MH-1 evidence basis, account for dependence in the current repeated all-pairs statistics, test adversarial false-pass/false-fail cases, repair stale realization currentness, and redesign only the challenged TRAIN2 FP32 member unless another member is independently falsified. The current generated MH-1 default remains e3nn. Explicit CuEq remains an opt-in path whose selected-head/runtime realization must pass the doctor parity gate; this workplan repairs the missing D2 authority behind that gate without rewriting separate CUEQ-PHASE1/PERF-CERT1/FINAL-GPU1 claims.

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

The final-production global TRAIN scheduler repair on branch `design/mlff-production-global-train-scheduler-repair` closed **PASS** under Protocol 6.4 at reviewed candidate `62d42da57f948f70bbd50ec338435c3a82b22d49`. Final production now normalizes recovery collection-wide, executes only remaining TRAIN_REQUIRED positions through one existing adaptive TRAIN scheduler wave, and retains serial/fail-fast EVAL2/assessment/publication in frozen selected-size order. Exact CampaignStore collection-signature admission linearization, authenticated restart/reuse, and zero-safe/backoff semantics remain intact. Production-scale RAM/VRAM adequacy is deferred to actual runs and target-hardware GPU qualification to the final release package.

Final closure record:

- `workplans/archive/MLFF_PRODUCTION_GLOBAL_TRAIN_SCHEDULER_REPAIR_WORKPLAN.md`.


The replay-retention / target-admissibility rework on branch `design/mlff-replay-retention-target-admissibility-rework` closed **PASS** under Protocol 6.4. Final D4 Review accepted executable candidate `042b84b74d0b109dd576b725eafe6359629a55ea` with evidence-only binding descendant `51db5d33723fad862b803b2487ea448cb876ec06`, with no Serious Challenge to accepted D1/D2/D3 authority. Final affected CPU evidence records 656 passing tests, including all 167 storage-integration tests. Production-scale GPU qualification remains deferred to the final complete-release package.

Final closure record:

- `workplans/archive/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_FINAL_D4_REVIEW_CLOSURE.md`.


The CV competence threshold separation/parameterization cycle on branch `fix/mlff-cv-competence-threshold-separation` closed **PASS**. Its accepted design separates foundation CV checkpoint competence `tau_cv`, held-out CV threshold `theta_cv`, and production checkpoint quality `tau_prod`, with role-specific invalidation and no duplicate threshold/translation machinery.

Final review and closeout records are archived under:

- `workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_PARAMETERIZATION_IMPLEMENTATION_REVIEW_REOPEN.md`;
- `workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_AND_PARAMETERIZATION_CLOSEOUT_2026-09-15.md`.

Production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred to the final complete-release package under the standing MLFF qualification policy.

Completed/superseded workplans belong under `workplans/archive/` after their active cycle closes.
