# Stage 7R Certification and Persistence Boundary Audit

Version: `0.19.19a0`  
Architecture: revision 26

## Scope

This audit covers the consolidation performed before `PeriodicNetEmbedding`:

- core net symmetry versus primitive-ring-derived action;
- exact barycentric placement ownership;
- persistent ring-strength theorem versus transient candidate workspace;
- independent certificate verification;
- finite `GF(2)` memory protection; and
- fast view-source lookup.

## Scientific invariance

The refactor changes ownership and serialization only. It does not change:

- `PrimitiveRingCatalog` enumeration or digest semantics;
- exact lifted ring placement;
- validated periodic automorphisms;
- the 96-operation unlabeled Na-LTA symmetry group;
- the five Na-LTA primitive-ring orbits;
- physical-edge `GF(2)` cancellation; or
- bounded strength statuses and witnesses.

## Boundary checks

### Core group

`PeriodicNetSymmetry` schema `mdstats.periodic_net_symmetry.v3` contains only the
normalized finite group, multiplication/inverse tables, translation cocycle,
vertex/edge orbits, and source identities. It contains no ring keys, ring action
table, ring orbit, or stabilizer payload.

### Derived ring index

`PrimitiveRingSymmetryIndex` schema `mdstats.primitive-ring-symmetry.v1` is bound
to:

- `PeriodicNetSymmetry.digest`;
- `PeriodicNetView.digest`;
- topology graph digest;
- `PrimitiveRingCatalog.digest`; and
- ring-catalog completeness metadata.

Action cells use integer ring positions, image shifts, and cycle
parameterizations. Exact cocycle-corrected action composition is revalidated.

### Barycentric placement

`PeriodicBarycentricPlacement` schema
`mdstats.periodic-barycentric-placement.v1` owns the exact rational equilibrium
coordinates, gauge anchor, collision pairs, rational bit-growth diagnostic, and
source digests. Automatic discovery consumes this object rather than a private
coordinate solver.

### Strength persistence

`RingStrengthResult` schema `mdstats.ring_strength.v2` stores the finite theorem,
diagnostics, candidate-set digest, and optional witness. The full candidate tuple
is owned only by transient `RingStrengthSearchWorkspace`.

`RingStrengthResult.verify(index)` independently:

1. checks source digests;
2. verifies weak-witness physical edge parity;
3. reconstructs the declared finite candidate set;
4. checks its digest; and
5. replays exact classification.

A payload modified and rehashed with a false witness is rejected.

### Memory policy

`FiniteRingCancellationResources` bounds support-matrix bits and provenance bits
before elimination allocation. Exceeding either bound raises a resource error;
the strength layer returns `UNRESOLVED_TRUNCATED` and never a negative theorem.

## Measured Na-LTA persistence effect

```text
old combined symmetry/ring payload          ~9.17 MB
new core PeriodicNetSymmetry                ~0.83 MB
new PrimitiveRingSymmetryIndex              ~1.01 MB
new combined discovery payload              ~1.84 MB

depth-eight strength candidates             3,240
persistent RingStrengthResult               ~4 KB
```

## Test evidence

Focused Stage-4--7 integration:

```text
120 passed
```

Complete package suite in eight nonoverlapping groups:

```text
635 passed
28 expected warnings
0 failures
55/55 test files covered exactly once
```

Python bytecode compilation also passed.

## Conclusion

The Stage 7R boundary is accepted. Scientific results no longer own
reconstructible ring-action or candidate-search payloads, and serialized
certificates are independently source-verified. The codebase is ready to define
the Euclidean metric and Cartesian realization in Stage 8A.
