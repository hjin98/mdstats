# S4R Primitive-Ring Implementation and Consistency Audit

Release: `mdstats 0.18.1a0`  
Date: 2026-07-14

## Scope

This audit covers the corrected Stage-4 ring foundation implemented in:

```text
mdstats/analysis/primitive_ring.py
```

and its alignment with:

```text
docs/specs/analysis/primitive_ring_spec.{md,pdf}
docs/arch_manuals/framework_ring_architecture.{md,pdf}
```

The module consumes one immutable `FrameworkTopology`. It does not rebuild
atomic connectivity, reproject the framework, compute geometry, infer cages, or
assign ring-site labels.

## Algorithmic attribution

The implementation cites and adapts:

- Horton (1987), shortest-path cycle candidates;
- Vismara (1997), parity-aware shortest-path families for relevant cycles;
- Goetzke and Klein (1991), primitive/irreducible ring definitions;
- Yuan and Cormack (2002), efficient primitive-ring analysis in topological
  networks.

The following features are specific to `mdstats`:

- exact lifted periodic vertices `(atom_index, image_shift)`;
- decorated framework multigraph edge identity;
- physical lifted-edge-instance checks;
- bounded transactional resource limits;
- canonical rotation/reversal identity and deterministic digests;
- v1 subset migration and explicit method/family metadata.

## Stage gates

### S4R.0 - API, terminology, and schema

Passed.

- Added `PrimitiveRingSearchMethod` and `PrimitiveRingFamily`.
- Made `SHORTEST_PATH_PAIRS -> PRIMITIVE_NO_SHORTCUT` the default.
- Retained `REMOVED_EDGE_SHORTEST -> EDGE_SHORTEST_SUBSET` explicitly.
- Advanced serialization to `mdstats.primitive-ring.v2`.
- Added compatibility aliases for v1 constructor and result field names.
- Verified that v1 catalogs migrate only as removed-edge subset catalogs.

### S4R.1 - Lifted shortest-path index

Passed.

- Builds one deterministic bounded BFS index per quotient framework vertex.
- Stores exact lifted relative-image distances and all tied predecessors.
- Commits breadth-first layers transactionally.
- Records the maximum complete depth for every source.
- Rejects or records state-limit truncation according to `strict`.

### S4R.2 - Even and odd candidate generators

Passed.

- Even `2r` candidates join two internally disjoint tied shortest paths of
  length `r` between exact lifted antipodes.
- Odd `2r+1` candidates join two internally disjoint shortest root paths of
  length `r` with one exact lifted closing edge.
- Two-member parallel-edge rings and triangles use the same parity framework.
- Candidate construction enforces lifted simplicity, exact continuity,
  physical-edge-instance uniqueness, and zero winding.
- Certified shortest pairs are retained to avoid redundant primitive queries.

### S4R.3 - Primitive no-shortcut classification

Passed.

- Even cycles test the uncertified antipodal pairs.
- Odd cycles test the uncertified maximal shorter-arc pairs.
- Distance queries include exact relative periodic image.
- Optional external-shortcut witness search removes the candidate's exact
  lifted edge instances and disallows cycle vertices internally.
- Nonprimitive candidates are rejected before canonical catalog insertion.

### S4R.4 - Canonical catalog and compatibility

Passed.

- Candidate keys are invariant under cyclic rotation, whole-cycle reversal,
  and global lattice translation.
- Complete decorated `FrameworkEdgeKey` identity is retained.
- Ring IDs are assigned only after sorting unique canonical keys.
- Vertex and edge incidence indexes are rebuilt and validated.
- v2 serialization, canonical JSON digests, tamper rejection, and v1 migration
  passed.

### S4R.5 - Validation and release gate

Passed.

Focused analytical coverage includes:

- triangle, square, diagonal square, tree, and theta graphs;
- parallel decorated two-rings;
- even and odd tied-shortest-path generators;
- periodic zero-winding and noncontractible cycles;
- exact translated edge-instance behavior;
- asymmetric linker-order expansion;
- strict and non-strict resource limits;
- deterministic serialization and digest validation;
- v1 subset migration;
- production Na-LTA comparison.

A dedicated octagon fixture adds a two-edge detour parallel to every octagon
edge. The octagon is primitive because no detour is shorter than the adjacent
one-edge arc. The corrected default finds eight triangles plus one 8-ring; the
removed-edge method finds only the triangles. This directly protects against
the conceptual incompleteness found in `0.18.0a0`.

## Na-LTA acceptance result

Input topology:

```text
48 framework vertices
96 decorated projected edges
one connected component
```

Bound: ring sizes 2 through 8.

```text
primitive/no-shortcut: 36 x 4R + 40 x 6R + 6 x 8R = 82 rings
edge-shortest subset:   36 x 4R + 16 x 6R        = 52 rings
```

The default lifted index depth is four. The run completes without resource
truncation. Atomic-path expansion contains only framework vertices and declared
linkers; Na spectators do not enter the expanded cycles.

The counts are topological primitive-cycle counts. They are not yet equivalent
to conventional 4R, 6R, and 8R site-family counts. Geometry, cage incidence,
portal semantics, and site classification remain downstream.

When the search bound is extended through size twelve, 32 primitive 12-cycles
are also found. They are retained as valid topological output and not interpreted
physically inside Stage 4.

## Regression and quality gates

```text
Focused primitive-ring tests: 20 passed
Complete package regression:  418 passed
Expected warnings:             27
Failures:                       0
Ruff formatting:               passed
Ruff lint:                     passed
Python compilation:            passed
```

The complete suite was executed in four independent groups to remain within the
single-command runtime window.

## Documentation alignment

The following were reviewed together:

- public exports in `mdstats.analysis` and `mdstats`;
- `PrimitiveRingOptions`, result dataclasses, diagnostics, serialization, and
  compatibility aliases;
- default and secondary method semantics;
- shortest-path index depth and parity-specific candidate generation;
- primitive no-shortcut correctness lemma;
- resource limits and completeness language;
- Na-LTA acceptance results and downstream interpretation warning;
- citations and separation of published theory from mdstats adaptations.

No unresolved API/specification mismatch remains at the release gate.
