# Active workplans

Active workplans are temporary engineering coordination contracts. They do not define current mdstats product behavior by repository presence alone; current behavior remains owned by accepted D1-D4 authority and conforming implementation.

## Current active MLFF work

`MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_WORKPLAN.md` remains the parent workplan on branch `fix/mlff-cv-competence-threshold-separation`, based on accepted `main` state `8553ebe9ed86b24dfe910c9e43acc6230d3ece90`.

The implementation candidate at `473437e2605f366a1c2c12dd121d6f9b1cf2ba2f` received an independent assembled review and is **NO-PASS / reopened**. The governing repair amendment is `MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_IMPLEMENTATION_REVIEW_REOPEN.md`.

The principal architectural finding is reductive rather than additive: accepted D3 already says broad DATA8 `TrainingProtocolIdentity` cannot authorize restored P5, and current P5 does not require a generic `Eval2EvaluationPlan`. The parent workplan's final-review amendment accidentally required those duplicate seams. The implementation correctly used the existing method + role-policy + role-plan/run-plan lineage; the reopen amendment supersedes the contradictory generic-protocol/EVAL2 requirements and explicitly forbids repairing them by adding wrappers or parallel authority.

The D1/D2 threshold-separation documents remain **proposed** and still require their owning independent reviews plus explicit stakeholder ratification. Required executable implementation evidence is also still open: the branch's documentation-PDF workflow passed, but no admissible focused/affected-regression/real-path test realization was available to this review. `docs/methods/.tmp_d1_threshold_revision.md` is temporary residue and must be removed before closure. Semantic-history and closeout-learning/HAS obligations also remain open.

The proposed scientific outcome remains foundation-CV competence at `45 meV/angstrom` target-force RMSE for the current cycle, fresh-production checkpoint quality at `30 meV/angstrom`, unchanged scratch/replay/shared hard gates, fixed-budget training, and downstream qualification separation. None of those proposed semantics are accepted-current until the D1/D2 acceptance gates complete.

The preceding post-selection restoration workplan remains closed and archived. This threshold-separation cycle does not reopen that archived implementation by default; it addresses a newly identified authority/identity coupling in the accepted restored baseline.

`MLFF_POST_SELECTION_UNIVERSAL_LOSS_MONITOR_AND_CV_METHOD_RESTORATION_WORKPLAN.md` was closed and archived on 2026-09-14 after independent Implementation/Integration Review R4 found no remaining D4 implementation/integration blocker and no Serious Challenge to its accepted D1/D2/D3 scope. Its lifecycle closeout record is `workplans/archive/MLFF_POST_SELECTION_UNIVERSAL_LOSS_MONITOR_AND_CV_METHOD_RESTORATION_CLOSEOUT_2026-09-14.md`.

Production-scale GPU/CuEq/LAMMPS/MLIAP release qualification remains governed by the standing final-release policy and is not an intermediate gate for the active threshold-separation cycle.

There is no active target-order redesign. The withdrawn FPS/coverage Gate-A lineage remains archived and does not alter the accepted target-size method.

Completed/superseded workplans belong under `workplans/archive/`.
