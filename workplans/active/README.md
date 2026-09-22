# Active workplans

Active workplans are temporary engineering coordination contracts. They do not define current mdstats product behavior by repository presence alone; current behavior remains owned by accepted D1-D4 authority and conforming implementation.

## Current active MLFF work

### Final-production model publication + lightweight MH-1 integration

Branch: `design/mlff-final-production-model-publication-mh1-integration`

Canonical workplan:

- `workplans/active/MLFF_FINAL_PRODUCTION_MODEL_PUBLICATION_MH1_INTEGRATION_WORKPLAN.md`

Revision 25 is **IMPLEMENTATION REVIEW NO-PASS / REOPENED FOR RESIDUAL D4 REPAIR** against assembled candidate `bd8ecf447a0209a22101c1d458f7e164c03d2d45`. Revision-22 D3 remains coherent and frozen; no Serious Challenge is active. The Revision-24 repair architecture remains accepted; Revision 25 is a narrow implementation delta.

The implementation correctly established most of the intended owner split—P5 decision versus subordinate full-model representation, exact selected-checkpoint reconstruction, model publication schema/paths, coherent observation, P7 checkpoint reference versus deployment source, storage child ownership, and lightweight MH-1 scaffolding—but independent Review found genuine blockers at the remaining trust/currentness boundaries. Mandatory implementation repair is Sections 26A-26C of the canonical workplan, with Revision-25 residual repair instructions controlling where they narrow/strengthen the prior delta.

Candidate `bd8ecf...` provisionally closes the late-P5 replay, descriptor-authenticated deployed execution, exact frozen-realization, and co-fenced first-reveal code paths. Residual blocking scope is now narrower: (1) late P7 binding revalidation must reload the authoritative current normalized campaign configuration rather than session-frozen `context.cfg`; (2) retries after failed P5/P7 directory or deployment-receipt fsync must establish a later successful durability fence before pointer/component publication; (3) local pathname `shutil.rmtree` of build/execution scratch must be removed or routed through the existing exact-owner descriptor-relative cleanup boundary; (4) MH-1 evidence must still cross the real current post-selection selected-checkpoint provider seam; and (5) the required focused/affected executable acceptance—including the new race/failure injections—must actually run for one exact assembled candidate. Long real MH-1 campaign/GPU/MD qualification remains deferred.

For exact candidate `bd8ecf447a0209a22101c1d458f7e164c03d2d45`, no GitHub status check or Actions run is visible, and the repair commit changed production code without adding the Revision-24-required falsification tests. Exact post-repair focused/affected commands, results and environment-dependent skip reasons remain a closeout requirement.

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
