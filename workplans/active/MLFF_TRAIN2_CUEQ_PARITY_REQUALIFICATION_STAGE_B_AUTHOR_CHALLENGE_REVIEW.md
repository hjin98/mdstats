---
kind: author-challenge-review
protocol_version: 6.4.0
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
stage: B
date: 2026-09-24
reviewed_candidate: MLFF-TRAIN2-CUEQ-EQUIVALENCE-D2-CANDIDATE-1
disposition: BLOCKED_AND_REPAIRED_AS_CANDIDATE_2
independent_review: false
---

# Stage-B author Challenge Review

This is an adversarial author-side review. It does **not** satisfy the required fresh independent D2 Review.

## Blocking finding B1 — stochastic RMS was incorrectly used as a systematic-bias margin

Candidate 1 proposed

[
D^2 le V_R
]

for backend centroid displacement.

That admits a persistent backend bias as large as one ordinary e3nn realization standard deviation. For a training operator, the semantics differ: realization noise may be approximately zero-mean across updates, while a backend-centered gradient/state-transition bias can recur coherently and accumulate.

Stage-A evidence itself showed a nonzero backend-centered force component smaller than fresh-process variability. Therefore Candidate 1 would effectively convert the observation used to diagnose stochastic structure into a permissive systematic margin.

**Disposition:** blocking. Removed.

## Blocking finding B2 — raw gradient coordinates would overconstrain implementation representation while underrepresenting optimizer consequence

Candidate 1 made the canonical flattened gradient vector the primary authorizing observable.

Although gradients are closer to the backend-specific training boundary than calculator outputs, exact parameter-coordinate comparison is representation-sensitive and still does not directly show the consequence after stateful optimizer/EMA recurrence.

**Disposition:** blocking for candidate quality. Replaced by a two-update training-state-transition witness observed through the canonical portable e3nn function. Loss/gradient/optimizer/EMA finiteness remains mandatory during the witness.

## Repair in Candidate 2

Candidate 2 separates:

1. **persistent bias** — global and order-cell centroids use the already established dtype mixed numerical envelope;
2. **stochastic spread** — CuEq variance is bounded from e3nn-only variance with a fixed dtype-tolerance floor, never from candidate cross discrepancy;
3. **training consequence** — two optimizer updates are executed from exact reset state, then update-induced portable-e3nn E/F/stress displacements are compared;
4. **state domain** — both starting and independently obtained non-initial model states are required for a full TRAIN2 claim.

The two-update horizon is minimal rather than empirical: update 1 populates stateful optimizer/EMA recurrence and update 2 consumes it.

## Remaining independent-review targets

Candidate 2 still requires fresh challenge of:

- whether the existing source-side mixed tolerances are adequate as persistent transition-bias envelopes;
- whether the factor-two stochastic variance budget is justified and non-permissive;
- whether two updates plus (S_0/S_1) adequately represent the claimed training-operator domain;
- whether the portable projection can serve as a non-circular measurement dependency once independently qualified;
- whether the witness corpus/objective-branch coverage prevents localized false passes;
- whether FP64 support should be qualified or explicitly narrowed.

No product-code change is authorized by this author review.
