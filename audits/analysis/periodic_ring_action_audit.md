# Periodic Ring Action Stage 5-P2 Audit

Date: 2026-07-18  
Package: `mdstats 0.19.11a0`

## Scope

This gate implements exact application of explicitly supplied periodic multigraph
automorphisms to primitive-ring occurrences:

- integer unimodular lattice action;
- lifted framework-vertex permutation and shifts;
- explicit edge permutation/orientation for multigraphs;
- exact edge-incidence/image-shift validation;
- exact lifted edge-instance mapping;
- stable-key target ring lookup;
- ordered vertex/step occurrence maps;
- translated target ring placement recovery.

No automatic symmetry discovery, `PeriodicNetView` signature validation, symmetry
group serialization, strong-ring classification, embedded faces, or tiling is included.

## Attribution

Periodic quotient edges and integer translation labels follow:

1. Chung, Hahn & Klee (1984), *Acta Cryst. A* 40, 42-50,
   DOI `10.1107/S0108767384000088`.

The exact periodic-net combinatorial automorphism viewpoint follows:

2. Delgado-Friedrichs & O'Keeffe (2003), *Acta Cryst. A* 59, 351-360,
   DOI `10.1107/S0108767303012017`.

The explicit multiedge action records, occurrence-level ring alignment, stable-key
target lookup, and physical edge-instance verification are mdstats-specific adaptations.

## Correctness checks

A representative acts on lifted vertices as

```text
(i,n) -> (pi(i), A n + tau_i)
```

with integer unimodular `A`.

For every quotient edge, the validator checks exact endpoint permutation and image-shift
relations for the declared target edge and orientation. Parallel edges remain distinct.

For each ring map:

1. every lifted source vertex is transformed exactly;
2. every oriented source edge step is transformed exactly;
3. the transformed edge-token cycle identifies the target stable ring key;
4. all `2n` cyclic/reversed alignments are considered;
5. one common target translation must align all lifted vertices;
6. all mapped physical edge instances must equal the aligned target instances;
7. exactly one occurrence map must survive.

## Focused test evidence

Command:

```text
pytest -q \
  tests/test_periodic_ring_action.py \
  tests/test_primitive_ring_index.py \
  tests/test_primitive_ring.py \
  tests/test_periodic_graph.py \
  tests/test_framework_topology.py
```

Focused coverage includes:

- identity and common translation gauge;
- nontrivial unimodular lattice action;
- square rotation;
- square reflection / reversed boundary orientation;
- explicit parallel-edge swap;
- invalid edge-action rejection;
- topology-digest mismatch rejection;
- repeated-action versus directly supplied composed action;
- Na-LTA translated-identity action over all 82 ring orbits and 432 ordered steps.

## Gate decision

**PASS.**

Focused result: `63 passed`.

The next Stage-5 consumer target is exact finite modulo-two cancellation of translated
smaller-ring physical edge support. General periodic-helper extraction remains deferred
until that third consumer demonstrates concrete shared machinery.
