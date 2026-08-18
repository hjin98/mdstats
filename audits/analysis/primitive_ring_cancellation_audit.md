# Primitive Ring Cancellation Stage 5-P3 Audit

Date: 2026-07-18  
Package: `mdstats 0.19.12a0`

## Scope

This gate implements exact finite GF(2) cancellation of translated primitive-ring
physical edge support:

- exact `RingPlacementSupport` from `PrimitiveRingIndex` canonical edge anchors;
- complete `LiftedEdgeInstanceRef(edge_index, anchor_shift)` basis identity;
- deterministic finite span membership over explicitly supplied smaller placements;
- exact positive decomposition witnesses;
- exact negative `NOT_IN_SUPPLIED_SPAN` semantics.

No `RingStrengthDomain`, automatic candidate enumeration, component-count/radius
bound, global strong-ring classification, public periodic chain algebra, symmetry
discovery, embedded faces, or tiling is included.

## Attribution

The strong-ring sum/symmetric-difference concept follows:

1. Goetzke & Klein (1991), *J. Non-Cryst. Solids* 127, 215-220,
   DOI `10.1016/0022-3093(91)90145-V`.
2. Yuan & Cormack (2002), *Comput. Mater. Sci.* 24, 343-360,
   DOI `10.1016/S0927-0256(01)00256-7`.

The exact physical lifted-edge basis, translated placement support, deterministic
finite-span API, and strict separation between finite negative algebra and strength
certification are mdstats-specific adaptations. Gaussian elimination over GF(2) is
standard mathematical background.

## Correctness boundary

For one canonical ring edge instance `(e,a)` and placement translation `t`, the
support entry is exactly `(e,a+t)`.

Finite cancellation uses complete physical edge instances rather than quotient-edge
IDs. Therefore translated instances of one quotient edge cannot cancel spuriously.

The solver answers only whether the target belongs to the GF(2) span of the exact
supplied finite candidate set. A positive result is independently rechecked by exact
set symmetric difference. A negative result never implies `STRONG` or
`STRONG_IN_DOMAIN`.

## Focused test evidence

Command:

```text
pytest -q \
  tests/test_framework_topology.py \
  tests/test_periodic_graph.py \
  tests/test_primitive_ring.py \
  tests/test_primitive_ring_index.py \
  tests/test_periodic_ring_action.py \
  tests/test_primitive_ring_cancellation.py
```

Focused result:

```text
71 passed
```

Coverage includes:

- exact support construction and translation covariance;
- two-member parallel-edge support;
- a primitive 6-ring exactly equal to the GF(2) sum of three smaller 4-rings;
- common translated decomposition;
- omitted-component and wrong-periodic-image negative controls;
- deterministic candidate ordering and redundant-candidate handling;
- duplicate/equal/larger candidate rejection;
- Na-LTA support checks for all 82 represented ring orbits.

## Gate decision

**PASS.**

All three Stage-5 consumer prototypes now pass: exact placement, exact automorphism
occurrence action, and exact finite physical-edge cancellation. The next task is a
small comparison/refactor gate: extract only periodic helper operations that are
actually duplicated across P1/P2/P3, then freeze the lightweight Stage-5 identity
and view contracts before full `PeriodicNetView`/symmetry implementation.
