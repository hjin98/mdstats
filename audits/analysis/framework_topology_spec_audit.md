# Framework topology source/specification consistency audit

## Release scope

- Package version: `0.15.0`
- Public module: `mdstats.analysis.framework_topology`
- Normative Markdown: `docs/specs/analysis/framework_topology_spec.md`
- Normative PDF: `docs/specs/analysis/framework_topology_spec.pdf`
- Canonical mapping schema: `mdstats.framework-mapping.v2`
- Canonical topology schema: `mdstats.framework-topology.v2`

## Public API alignment

The source and specification agree on:

- `FrameworkPathRule(rule_id, linker_atomic_numbers, endpoint_atomic_numbers,
  edge_kind)`;
- complete endpoint/linker/endpoint reversal canonicalization;
- `FrameworkEdgeKey` as the canonical undirected decorated-edge key;
- `FrameworkEdgePath` as canonical atom-level provenance;
- `OrientedFrameworkEdgePath(edge, orientation)` as a derived traversal view;
- `FrameworkEdgePath.oriented()` and `oriented_from()`;
- unchanged role, mapping, projection, topology, validation, and build APIs.

`OrientedFrameworkEdgePath` is re-exported from both `mdstats.analysis` and the
package root.

## Scientific consistency

1. Atomic connectivity remains undirected.
2. Projected framework adjacency remains undirected and may be a multigraph.
3. Endpoint species and linker order form one complete rule signature.
4. Reversal equivalence reverses the complete path only.
5. `A-O-S-B == B-S-O-A`.
6. `A-O-S-B != A-S-O-B`.
7. Reverse traversal negates all directed periodic translations.
8. Parallel and self-image edge behavior remains unchanged.
9. Stage 3 topology identity consumes exact version-2 decorated edge records.
10. Stage 4 ring traversal consumes the oriented edge sign rather than a directed
    authoritative graph.

## Documentation validation

- Markdown/PDF API alignment: passed.
- PDF pages: 31.
- Structural preflight: passed.
- Rendered-page inspection: passed.
- No clipping, overlap, missing glyphs, or broken equations observed.
