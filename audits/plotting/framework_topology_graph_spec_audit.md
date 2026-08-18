# Framework visualization source/specification consistency audit

## Release

- Package version: `0.15.0`
- Source: `mdstats/plotting/framework_topology_graph.py`
- Specification: `docs/specs/plotting/framework_topology_graph_spec.md/.pdf`
- Projected adapter schema: `mdstats.framework-topology-graph-view.v2`
- Atomic-path adapter schema: `mdstats.framework-topology-path-view.v2`

## Orientation-aware attributes

Projected edges expose:

```text
atomic_path_indices
reverse_atomic_path_indices
canonical_path_symbols
reverse_path_symbols
canonical_orientation
orientation_aware
```

Atomic diagnostic segments expose corresponding parent-edge canonical and reverse
path metadata. The graph remains `directed=False` and `multigraph=True`.

## Geometry behavior

- Canonical projected shifts remain authoritative.
- Frame-local display shifts are reconstructed from retained atomic paths.
- Reverse traversal uses the edge-level oriented view and negates shifts.
- No duplicate reverse edge is created for display.

## Tests

- asymmetric canonical/reverse path symbols: passed;
- independently swapped linker order remains distinct: passed;
- projected and atomic diagnostic metadata: passed;
- existing periodic, parallel, node-display, and relaxed Na-LTA tests: passed.

The 13-page PDF passed preflight and visual inspection.
