---
kind: author-challenge-review
protocol_version: 6.4.0
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
stage: B
date: 2026-09-24
reviewed_candidate: MLFF-TRAIN2-CUEQ-EQUIVALENCE-D2-CANDIDATE-1
disposition: CANDIDATES_1_AND_2_BLOCKED; REPAIRED_AS_CANDIDATE_3
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


## Second author Challenge — Candidate 2

### Blocking finding B3 — no rare-outlier materiality guard

Candidate 2 bounded global/cell centroids and variance but could still admit a sufficiently rare large discrepancy whose contribution was diluted by the finite average.

For a training operator, one gross update can corrupt optimizer state even when aggregate statistics remain small.

**Repair:** Candidate 3 adds a candidate-independent per-retained-pair catastrophic guard at the already accepted property Huber transition scales: (0.01) eV/atom, eV/Angstrom and eV/Angstrom^3 for energy, force and stress. This is deliberately much looser than the normal numerical envelope and cannot be tuned from CuEq evidence.

### Blocking finding B4 — factor-two variance budget was unnecessarily permissive

Candidate 2 allowed

[
V_C le 2max(V_R,T^2).
]

That can nearly double a large noisy-reference variance even when the fixed dtype tolerance scale is tiny.

**Repair:** Candidate 3 uses

[
V_C le V_R + T^2,
]

globally and per cell. Candidate spread may exceed reference spread only by one fixed dtype-tolerance-sized variance budget.

### Blocking finding B5 — projection measurement dependency could re-import descriptor/FPS gating

Candidate 2 required the broader trained-state projection relation before using portable e3nn as the common transition evaluator. That deployment relation historically includes the generic calculator parity record, which itself includes descriptors/FPS. This could contradict the protected-consequence decision to remove descriptors from TRAIN2 authorization.

**Repair:** Candidate 3 distinguishes the dependency-native **state-transfer mapping** used as a measurement transform from the broader deployment projection acceptance relation. The transform must preserve canonical shell/state mapping and be independently qualified, but it does not import source-selection descriptor/FPS as a TRAIN2 gate.

### Blocking finding B6 — reduction arithmetic was underspecified

Candidate 2 defined centroids/variances but not the exact control precision/accumulation order.

**Repair:** Candidate 3 fixes binary64 control arithmetic and lexicographic reduction order as D2 method identity.

### Blocking finding B7 — non-initial state could be nominally different but numerically trivial

Candidate 2 required (S_1
eq S_0) but did not require that (S_1) exercise a materially different function.

**Repair:** Candidate 3 requires at least one governed portable-e3nn witness output at (S_1) to differ from (S_0) beyond the fixed dtype mixed envelope.

Candidate 3 remains proposed and requires fresh independent Review.
