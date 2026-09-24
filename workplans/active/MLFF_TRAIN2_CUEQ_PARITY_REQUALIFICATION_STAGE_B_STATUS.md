---
kind: workplan-stage-status
protocol_version: 6.4.0
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
stage: B
status: candidate-4-author-ready-awaiting-fresh-independent-review
date: 2026-09-24
candidate: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE.md
author_challenge: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_STAGE_B_AUTHOR_CHALLENGE_REVIEW.md
---

# TRAIN2 CuEq parity requalification — Stage B status

Stage A is PASS.

Three author-side Challenge passes blocked and repaired Candidates 1-3 before independent Review. Candidate 4 is the author-ready proposal.

Candidate 4:

- controls persistent global and order-cell bias with the inherited dtype calculator precision constants, explicitly as a new proposed TRAIN2-centroid use;
- budgets candidate stochastic variance by V_C <= V_R + T_dtype^2, so candidate evidence never sets its own scale;
- adds a coarse paired catastrophic guard at the accepted 0.01 property robust-loss transition scales;
- makes starting-state energy/force/stress channels mandatory;
- measures the real two-update TRAIN2 state transition rather than raw inference or raw parameter-gradient coordinates;
- harvests consecutive witness windows from the actual accepted loader exposure, including replay-first/target-second pre-shuffle order, seed/shuffle/batch, no-duplication, and drop-last semantics;
- observes update-induced energy/force/stress displacements through the canonical transient-to-portable state-transfer transform and portable-e3nn evaluator;
- independently checks every mapped CuEq state directly against the transient CuEq physical function, with an additional dependency-native state-transfer differential;
- prevents the measurement transform from re-importing source/DATA6 descriptor/FPS gating into TRAIN2;
- fixes binary64 reduction arithmetic/order;
- requires meaningful starting and non-initial model-state coverage;
- requires finite loss, gradient, model, optimizer, and EMA execution plus complete mutable transient-state closure;
- keeps source/DATA6 and deployment-projection relations separate; and
- does not relax FP64 forward tolerance, while refusing to call forward-only FP64 evidence a complete training-operator proof.

The first Candidate-4 representation at commit 5d63350dd13929c27fa6c2204238f2f2e8f93cbd contained mathematical escape corruption and is not a Review target. Its successor is a representation-only reconstruction of the same Candidate-4 semantics.

Candidate 4 is **proposed, not accepted**. The next valid gate is a genuinely fresh independent D2 Review of the final immutable Candidate-4 commit.
