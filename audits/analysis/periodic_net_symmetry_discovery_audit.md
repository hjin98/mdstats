# Automatic Periodic-Net Symmetry Discovery Audit

Date: 2026-07-18  
Version: `0.19.17a0`  
Architecture: revision 24

## Scope

This gate discovers the complete automorphism group modulo translations for one
eligible `PeriodicNetView`. It computes an exact rational barycentric placement,
enumerates all affine maps determined by a spanning incident-edge frame, validates
every candidate against the original decorated periodic quotient multigraph, and
passes a reduced generator set to the existing finite group assembler.

It does not compute a Euclidean crystallographic space group, physical metric,
Wyckoff positions, natural tiling, or embedding geometry.

## Implemented contracts

- exact rational quotient equilibrium placement;
- deterministic anchor and spanning star-frame selection;
- exhaustive signature-compatible target-frame enumeration;
- exact affine map and integer-unimodular lattice-action recovery;
- exact quotient-vertex permutation and image-shift recovery;
- exact explicit multiedge action, including parallel-edge permutations;
- full candidate validation against `PeriodicNetView`;
- deterministic generator reduction;
- integration with exact finite group/ring-action assembly;
- source-bound discovery result and serialization;
- hard resource limits with no partial result; and
- exact translation-cocycle support for absolute lifted placements.

## Completeness domain

The first backend certifies completeness only for views satisfying all of:

```text
pbc == (True, True, True)
quotient components == 1
translation rank == 3
translation subgroup index == 1
barycentric placement collision-free modulo Z^3
one incident vertex star contains a 3-D frame
```

Outside this domain the backend raises an unsupported/resource error and returns
no symmetry object.

## Scientific invariants

- `PeriodicNetView.digest` defines the exact decorated symmetry problem.
- Every accepted operation preserves active vertex and edge signatures.
- Parallel edge records remain distinct.
- Candidate acceptance uses exact rational/integer arithmetic, not tolerances.
- Under the declared domain, every automorphism maps the fixed source frame to one
enumerated target frame.
- The returned `PeriodicNetSymmetry` is complete for the supplied view, not merely
a subgroup from caller-supplied generators.
- The barycentric placement is a topological computational realization, not a
physical geometry.

## Translation-cocycle correction

Automatic Na-LTA testing exposed that normalized representatives obey

```text
g_hat h_hat = T_c(g,h) (gh)_hat
```

with nonzero translations for many operation pairs. The finite group now stores
and validates `composition_translation_table`; absolute ring placements compose
with the corresponding cocycle correction. This changes no abstract group
multiplication but is required for exact lifted actions.

## Algorithmic provenance

The exact periodic-net isomorphism/symmetry framework follows Delgado-Friedrichs
and O'Keeffe (2003), DOI `10.1107/S0108767303012017`. The rational barycentric
placement follows Delgado-Friedrichs (2004), DOI
`10.1007/978-3-540-24595-7_17`.

The exact `Fraction` implementation, source-frame policy, explicit multiedge
matching, parallel-edge generator handling, deterministic generator reduction,
resource semantics, source-bound persistence, and cocycle integration are
`mdstats` adaptations.

## Validation

Focused Stage-4/5/6 gate:

```text
105 passed
```

Full package suite in seven nonoverlapping groups:

```text
620 passed, 28 warnings
```

Na-LTA acceptance result:

```text
group order: 96
vertex orbits: 1
edge orbits: 3
primitive-ring orbit sizes: 6, 12, 16, 24, 24
primitive rings covered: 82
```

Additional coverage includes exact synthetic diamond symmetry, signature-policy
group reduction, deterministic serialization, nonzero cocycles, barycentric
collision rejection, partial-periodicity rejection, and transactional frame/group
resource limits.

## Gate decision

**PASS.**

The next scientific module is bounded strong-ring classification. Euclidean
embedding diagnostics remain deferred to the explicit `PeriodicNetEmbedding`
stage.
