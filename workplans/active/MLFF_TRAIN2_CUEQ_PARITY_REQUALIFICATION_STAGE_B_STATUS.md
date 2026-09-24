---
kind: workplan-stage-status
protocol_version: 6.4.0
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
stage: B
status: candidate-2-drafted-awaiting-fresh-independent-review
date: 2026-09-24
candidate: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE.md
author_challenge: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_STAGE_B_AUTHOR_CHALLENGE_REVIEW.md
---

# TRAIN2 CuEq parity requalification — Stage B status

Stage A is PASS.

The first Stage-B candidate was challenged before independent Review. Its reference-noise margin could admit persistent backend bias, and its raw-gradient observable did not directly express stateful optimizer consequence. Candidate 1 is superseded.

Candidate 2 now:

- controls persistent backend bias with the existing dtype mixed numerical envelope on global and order-cell centroids;
- uses e3nn-only variability plus a fixed dtype-tolerance floor solely for stochastic non-degradation;
- tests the real training consequence with a two-update state-transition witness;
- observes update-induced E/F/stress changes through the independently governed portable-e3nn representation;
- requires finite loss/gradient/optimizer/EMA state throughout;
- removes descriptors/FPS from TRAIN2 authorization when no TRAIN2 consumer exists;
- requires both starting and non-initial model-state coverage;
- keeps source/DATA6 and trained-state projection relations separate;
- does not relax FP64 forward tolerance, while refusing to call forward-only FP64 evidence a complete training-operator proof.

Candidate 2 is **proposed, not accepted**. The next gate is a genuinely fresh independent D2 Review of the immutable candidate.
