# Periodic Net Symmetry Group Audit

Date: 2026-07-18  
Version: `0.19.17a0`  
Architecture: revision 24

## Scope

This audit covers the finite symmetry-group object used by both explicit-generator
assembly and automatic discovery. The group consists of normalized periodic-net
automorphism representatives modulo lattice translations.

## Implemented contracts

- deterministic source-anchor translation gauge;
- exact integer lattice-matrix composition and inversion;
- exact vertex and explicit multiedge action composition;
- exact inverse operations;
- finite closure from generators and inverses;
- transactional operation/ring-check resource limits;
- deterministic operation ordering;
- multiplication, inverse, and composition-translation cocycle tables;
- vertex and edge orbit partitions;
- optional primitive-ring action, ring orbits, and stabilizers;
- cocycle-corrected ring-action homomorphism validation;
- canonical result digests; and
- source-validated serialization.

## Translation cocycle

For normalized representatives,

```text
g_hat h_hat = T_c(g,h) (gh)_hat
```

The v2 schema stores `composition_translation_table`. Every entry is recomputed
from the normalized operation records during construction and serialization.
Absolute lifted ring placements use the cocycle correction; quotient operation
indices continue to use the ordinary multiplication table.

## Scientific invariants

- Every operation belongs to one exact `PeriodicNetView.digest`.
- Equal signatures permit exchange but never graph-record collapse.
- Operations differing only by common translation normalize to one representative.
- Direct construction from explicit generators is complete for that generated
subgroup.
- Automatic Stage-6C discovery supplies a complete generator set only inside its
declared exact domain.
- Missing transformed primitive-ring keys are errors.
- Resource truncation never produces a partial group result.

## Algorithmic provenance

Periodic quotient/vector representations follow Chung, Hahn, and Klee (1984),
DOI `10.1107/S0108767384000088`. Exact combinatorial periodic-net symmetry follows
Delgado-Friedrichs and O'Keeffe (2003), DOI
`10.1107/S0108767303012017`.

The explicit source-bound catalog, deterministic gauge, multiedge action, cocycle,
ring occurrence tables, and transactional resources are `mdstats` adaptations.

## Validation

Focused Stage-4/5/6 gate:

```text
105 passed
```

Full package suite:

```text
620 passed, 28 warnings
```

Coverage includes identity, cyclic and dihedral groups, noncommuting generators,
integer lattice inverses, parallel-edge exchanges, deterministic ordering,
vertex/edge/ring orbits, stabilizers, cocycle corruption rejection,
cocycle-corrected ring-action composition, serialization, unbounded-shear
rejection, and automatic Na-LTA full-group recovery.

## Gate decision

**PASS.**
