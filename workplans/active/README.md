# Active workplans

Active workplans are temporary engineering coordination contracts. They do not define current mdstats product behavior by repository presence alone; current behavior remains owned by accepted D1-D4 authority and conforming implementation.

## Current active MLFF work

`MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_WORKPLAN.md` is the current active MLFF workplan on branch `fix/mlff-cv-competence-threshold-separation`, based on accepted `main` state `8553ebe9ed86b24dfe910c9e43acc6230d3ece90`.

Its final independent workplan review is **PASS after amendment**. The workplan remains `proposed`, with highest affected domain D1, because the material D1/D2 authority revision still requires its own independent falsification/review and stakeholder ratification before accepted-current promotion. It governs the proposed separation between foundation-CV competence (`45 meV/angstrom` target-force RMSE for the current cycle) and fresh-production checkpoint quality (`30 meV/angstrom`), while preserving scratch, replay, fixed-budget training, common-monitor separation and downstream qualification semantics.

**Implementation state (2026-09-14):** Gates A-D have an implementation candidate on this branch. The D1/D2 amendments are drafted as **proposed** revisions; independent D1/D2 review, stakeholder ratification, and the Gate E assembled review remain open, so the plan is not closable or archivable yet. One D4 reconciliation needs reviewer attention: accepted D3 forbids `TrainingProtocolIdentity` from authorizing P5 and P5 builds no `Eval2EvaluationPlan`, so the workplan's per-run TRAIN2/EVAL2 binding is concretized through the existing role-plan lineage (see the workplan's implementation-reconciliation note).

The preceding post-selection restoration workplan is closed and archived. This new cycle does not reopen that archived implementation by default; it addresses a newly identified authority/identity coupling in the accepted restored baseline.

`MLFF_POST_SELECTION_UNIVERSAL_LOSS_MONITOR_AND_CV_METHOD_RESTORATION_WORKPLAN.md` was closed and archived on 2026-09-14 after independent Implementation/Integration Review R4 found no remaining D4 implementation/integration blocker and no Serious Challenge to its accepted D1/D2/D3 scope. Its lifecycle closeout record is `workplans/archive/MLFF_POST_SELECTION_UNIVERSAL_LOSS_MONITOR_AND_CV_METHOD_RESTORATION_CLOSEOUT_2026-09-14.md`.

Production-scale GPU/CuEq/LAMMPS/MLIAP release qualification remains governed by the standing final-release policy and is not an intermediate gate for the active threshold-separation cycle.

There is no active target-order redesign. The withdrawn FPS/coverage Gate-A lineage remains archived and does not alter the accepted target-size method.

Completed/superseded workplans belong under `workplans/archive/`.
