---
kind: author-challenge-review
protocol_version: 6.4.0
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
stage: B
date: 2026-09-24
reviewed_candidates:
  - MLFF-TRAIN2-CUEQ-EQUIVALENCE-D2-CANDIDATE-1
  - MLFF-TRAIN2-CUEQ-EQUIVALENCE-D2-CANDIDATE-2
  - MLFF-TRAIN2-CUEQ-EQUIVALENCE-D2-CANDIDATE-3
disposition: CANDIDATES_1_2_3_BLOCKED; REPAIRED_AS_CANDIDATE_4
independent_review: false
---

# Stage-B author Challenge Review

This is an adversarial author-side review. It does **not** satisfy the required fresh independent D2 Review.

## Candidate 1

### B1 — stochastic RMS was incorrectly used as a systematic-bias margin

Candidate 1 proposed D^2 <= V_R for backend centroid displacement.

That would admit a persistent backend bias as large as one ordinary e3nn realization standard deviation. For a training operator these semantics differ: realization noise may be approximately zero-mean across updates, while a backend-centered state-transition bias can recur coherently and accumulate.

Stage-A evidence itself showed a nonzero backend-centered force component smaller than fresh-process variability. Candidate 1 would therefore have converted method-design evidence about stochastic structure into a permissive systematic-bias margin.

**Disposition:** blocking. Removed.

### B2 — raw gradient coordinates overconstrained representation while underrepresenting optimizer consequence

Candidate 1 used the flattened parameter-gradient vector as the primary authorizing observable.

Gradients are closer to the backend-specific training boundary than calculator outputs, but parameter-coordinate comparison remains representation-sensitive and does not directly express the consequence after stateful optimizer/EMA recurrence.

**Disposition:** blocking. Replaced by a two-update training-state-transition witness observed through a common portable-e3nn function. Loss, gradient, model, optimizer, and EMA finiteness remain mandatory.

## Candidate 2

Candidate 2 separated persistent bias from stochastic spread, used a two-update transition witness, and required starting plus non-initial states.

### B3 — no rare-outlier materiality guard

Global/cell centroids and variance could dilute a sufficiently rare gross discrepancy.

**Repair:** Candidate 3 added a candidate-independent paired catastrophic guard at the already accepted property robust-loss transition scales: 0.01 eV/atom, 0.01 eV/Angstrom, and 0.01 eV/Angstrom^3. This guard is deliberately much looser than normal numerical equivalence and cannot be tuned from CuEq observations.

### B4 — factor-two variance budget was unnecessarily permissive

Candidate 2 used V_C <= 2*max(V_R,T^2). That can nearly double an already large noisy-reference variance even when the fixed dtype tolerance scale is tiny.

**Repair:** Candidate 3 changed the rule to V_C <= V_R + T^2, globally and per cell. Candidate stochastic spread may exceed reference spread only by one fixed dtype-tolerance-sized variance budget.

### B5 — projection measurement dependency could re-import descriptor/FPS gating

Candidate 2 required the broader trained-state deployment projection relation before using portable e3nn as the transition evaluator. That relation historically includes generic calculator descriptor/FPS parity, which would contradict the protected-consequence decision to remove descriptors from TRAIN2 authorization.

**Repair:** Candidate 3 split the dependency-native state-transfer mapping used for measurement from the broader deployment projection relation. TRAIN2 no longer inherits source-selection descriptor/FPS as a hard gate merely through the mapping.

### B6 — reduction arithmetic was underspecified

Candidate 2 defined centroids and variances without fixing control precision or accumulation order.

**Repair:** Candidate 3 fixed IEEE-754 binary64 control arithmetic and lexicographic reduction order as D2 method identity.

### B7 — non-initial state could be nominally different but numerically trivial

Candidate 2 required S1 != S0 but did not require S1 to exercise a materially different function.

**Repair:** Candidate 3 requires at least one governed portable-e3nn witness output at S1 to differ from S0 beyond the dtype mixed envelope.

## Candidate 3 final readiness pass

### B8 — real TRAIN2 exposure semantics were not concretely bound

Candidate 3 required the real TRAIN2 objective/exposure but did not define how the two optimizer-update batches are obtained.

Accepted D2 makes pre-shuffle corpus/head order, seeded shuffle, batch geometry, drop-last behavior, and realized sample order numerically material. In replay-enabled P5 the accepted layout is replay/pretraining-head first and target second. A hand-assembled target or replay batch can exercise the same loss code while bypassing the actual stochastic training operator.

**Repair:** Candidate 4 harvests qualification windows from the real accepted loader trace, preserving replay-first/target-second layout, seed/shuffle/sampler, batch size, no target duplication, and drop-last. The smallest deterministic set of consecutive two-update windows covering active branches is chosen from metadata before CuEq outcomes.

### B9 — measurement-transform qualification was too weak/common-mode

Candidate 3 required an independently qualified transient-to-portable mapping but did not define a discriminating per-state oracle. A defective mapping used by transition evaluation could hide the state difference being measured.

**Repair:** Candidate 4 requires every measured CuEq state to pass direct transient-CuEq versus mapped-portable-e3nn energy/force/stress parity on a frozen mapping witness under the dtype envelope, plus exact canonical-shell architecture. A separate bounded dependency-native conversion/state-value differential remains supporting anti-common-mode evidence. Descriptor/FPS acceptance is not imported into TRAIN2.

### B10 — tolerance provenance wording overstated acceptance

Candidate 3 described the centroid envelope using the existing dtype mixed numerical constants without sufficiently distinguishing their new use.

**Repair:** Candidate 4 states that the constants are inherited from the existing calculator precision scale, while applying them to TRAIN2 transition centroids is a new proposed D2 use requiring independent falsification.

## Representation correction

The first immutable Candidate-4 draft at commit 5d63350dd13929c27fa6c2204238f2f2e8f93cbd contained programmatic escape corruption in mathematical notation. That commit is historical and must not be used as the independent Review target. The subsequent Candidate-4 descendant reconstructs the same semantics with lossless notation; no D2 rule, threshold, scope, or decision was changed by this representation repair.

## Readiness disposition

No further author-known Stage-B scope/oracle defect remains after B1-B10. This is **not** an independent PASS. Candidate 4 must be reviewed in a genuinely fresh independent context before any Stage-C evidence or D4 implementation.
