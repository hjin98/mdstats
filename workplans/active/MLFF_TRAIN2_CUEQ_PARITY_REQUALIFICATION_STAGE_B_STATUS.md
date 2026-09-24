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

Two author-side Challenge passes have now blocked and repaired two successive drafts before independent Review.

Candidate 4:

- controls persistent global and order-cell bias with the existing dtype mixed numerical envelope;
- budgets candidate stochastic variance as (V_C le V_R + T_{m dtype}^2), so candidate evidence never sets its own scale;
- adds a coarse per-observation catastrophic guard at the accepted 0.01 property Huber transition scales;
- measures the real two-update TRAIN2 state transition rather than raw inference or raw parameter-gradient coordinates;
- harvests consecutive witness windows from the actual accepted loader exposure, including replay-first/target-second pre-shuffle order, seed/shuffle/batch and `drop_last` semantics;
- observes update-induced E/F/stress displacements through the canonical transient->portable state-transfer transform and portable e3nn evaluator, while independently checking every mapped CuEq state directly against the transient CuEq physical function;
- prevents that measurement transform from re-importing source/DATA6 descriptor/FPS gating into TRAIN2;
- fixes binary64 reduction arithmetic/order;
- requires meaningful starting/non-initial state coverage;
- requires finite loss/gradient/model/optimizer/EMA execution and complete mutable transient state;
- keeps source/DATA6 and deployment projection relations separate;
- does not relax FP64 forward tolerance, while refusing to call forward-only FP64 evidence a complete training-operator proof.

Candidate 4 is **proposed, not accepted**. The next valid gate is a genuinely fresh independent D2 Review of the immutable candidate.
