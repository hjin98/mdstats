# MLFF D1/D2 reconstruction — implementation conformance challenges

**Status:** non-normative review evidence / routed lower-layer challenges  
**Baseline inspected:** `9fd82b0ed40990d56716a393aa3f7db0a2ff44d0`  
**Date:** 2026-09-13

The D1/D2 reconstruction review compared accepted documentation with current implementation evidence. The findings below are **not** reasons to rewrite the reconstructed method to match lower-layer behavior. They are implementation-conformance questions that should be adjudicated by the owning D3/D4 workflow if the affected non-default/current path is relied upon.

## C1 — common target-size/post-selection configuration-weight projection may ignore declared policy fields

### Evidence

The generic DATA7 owner `build_training_weight_catalog(...)` consumes the complete `ConfigurationWeightPolicy`: condition equalization, event-anchor multiplier, protected-event multiplier, degraded-frame multiplier, lower/upper bounds, and mean-one normalization.

The current P3/P5 common path instead calls `fit_common_configuration_weights(...)`. The inspected implementation of that helper uses condition-stratum equalization (or uniform weight) followed by one mean-one normalization, then projects those frozen values into candidate/fold materialization. It does not visibly consume the event/protected/degraded multipliers or the declared min/max bounds.

### Why this matters

Current architecture describes configuration weights as a distinct scientific layer that may depend on applicable condition, regime, event, and quality evidence. `ConfigurationWeightPolicy` serializes those fields into policy identity. If a user changes a policy field that is authenticated but the P3/P5 numerical path ignores it, requested method identity and realized loss weighting may diverge.

### Required owning-layer adjudication

Do **not** resolve this by weakening D1/D2 prose. The D3/D4 owner should determine one of:

1. the complete configuration-weight policy is intended for current P3/P5, in which case the common-weight fitting seam should realize the declared fields once over the authorized common/fold domain and preserve candidate projection without per-N renormalization; or
2. those fields are intentionally inapplicable to P3/P5, in which case the accepted policy/architecture identity should be narrowed so inert fields cannot masquerade as realized method differences.

A repair should reuse the existing weighting owner or reduce duplicated authority rather than introduce a third weighting implementation.

## C2 — non-default atomic-reference ridge prior appears keyed by the wrong coordinate in the shared low-level solver

### Evidence

`AtomicReferenceFitPolicy.prior_by_atomic_number` is explicitly keyed by atomic number. `solve_atomic_reference_least_squares(...)`, however, receives only the composition count matrix and target vector and currently constructs the prior vector with `prior_map.get(index, 0.0)` for column positions `index = 0..element_count-1`.

The upstream common/fold fit constructs count-matrix columns in a separately determined element order (for example atomic numbers such as 3, 8, 11, ...). The low-level solver is not passed that element order. Therefore a non-empty atomic-number-keyed prior can be misaligned with matrix columns unless the keys accidentally equal zero-based column positions.

The default current policy has `ridge_lambda = 0.0` and an empty prior, so this observation does **not** show drift in the default production fit. It affects the declared non-default ridge/prior capability.

### Required owning-layer adjudication

The D2 method should continue to state an element-aligned prior. D4 should either:

- pass/reconstruct the authoritative element order at the solver boundary and build the prior vector by atomic-number key; or
- prove that the non-default prior path is intentionally unsupported and remove/retire that configuration surface from accepted current policy.

Tests should use multi-digit/non-contiguous atomic numbers and a nonzero ridge coefficient so column-index/atomic-number confusion cannot pass accidentally.

## Scope

These challenges were discovered while falsifying the documentation reconstruction. No executable source was changed in the documentation branch. They do not invalidate the reviewed D1/D2 extraction; they identify places where lower-layer conformance should be checked before claiming that every non-default declared policy is realized exactly.