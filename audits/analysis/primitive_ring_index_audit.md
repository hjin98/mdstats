# Primitive Ring Index Stage 5-P0/P1 Audit

Date: 2026-07-18  
Package: `mdstats 0.19.10a0`

## Scope

This gate implements only the first exact periodic ring-placement infrastructure:

- hardened `PrimitiveRingCatalog` lifted-walk continuity validation;
- transient source-bound `PrimitiveRingIndex`;
- stable `PrimitiveRingKey` lookup;
- exact physical `LiftedEdgeInstanceRef` anchors;
- occurrence-level edge inverse incidence;
- translated ring-placement queries.

No periodic-net symmetry discovery, strong-ring classification, face geometry,
cell complex, natural tiling, or generalized periodic helper refactor is included.

## Attribution

The physical quotient-edge plus integer translation convention is attributed in
both source comments/docstrings and the paired specification to:

1. Chung, Hahn & Klee (1984), *Acta Cryst. A* 40, 42-50,
   DOI `10.1107/S0108767384000088`.
2. Klee (2004), *Cryst. Res. Technol.* 39, 959-968,
   DOI `10.1002/crat.200410281`.

The exact source-bound occurrence index and placement-query API are mdstats-specific
adaptations.

## Correctness checks

For quotient edge `(i, j, Delta)`, a physical edge instance anchored at `a` is
`(i,a) -> (j,a+Delta)`. A reverse-traversed canonical ring step therefore uses
anchor `source_image - Delta`. Aligning a canonical occurrence anchor `a_k` to a
requested anchor `a` gives the unique common translation `t = a - a_k`.

The index preserves every step occurrence. Repeated quotient-edge use and parallel
framework edges are not collapsed.

## Focused test evidence

Command:

```text
pytest -q \
  tests/test_framework_topology.py \
  tests/test_periodic_graph.py \
  tests/test_primitive_ring.py \
  tests/test_primitive_ring_index.py
```

Result:

```text
54 passed
```

The new dedicated file contributes 8 tests.

Na-LTA gate:

- 36 x 4R;
- 40 x 6R;
- 6 x 8R;
- 82 total ring orbits;
- 432 canonical ring-step occurrences checked exactly.

## Stage-4R invariance check

Revision-16 baseline versus Stage-5-P0/P1 implementation on the checked-in
Na-LTA topology:

```text
catalog digest:
32965d01ad6f6cb16855e4cebe9efaa73f0b6f0959aa8d6eecbb5daae221ed87

structural-key aggregate SHA-256:
4a537bca133f36271eab46a5f9e6a45afd5b5b764d49710cdbad07eafa461235

ring-digest aggregate SHA-256:
34fe3e815b7786255c0800c237159b4fdbeb55696612ca39d56185bd2ee1d1d7
```

All three are unchanged.

## Gate decision

**PASS.**

The next implementation target is the S5-P2 automorphism-induced ordered
ring-occurrence mapping prototype using known validated periodic transformations.
General `_periodic_graph.py` extraction remains deferred until that second consumer
shows which operations are genuinely shared.
