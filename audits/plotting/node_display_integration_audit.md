# Na-LTA framework visualization integration audit

## Scientific source

- Collection atoms: 168
- Atomic connectivity active atoms: 144
- Atomic T-O edges: 192
- Framework vertices: 48
- Framework projected edges: 96
- Framework graph digest: `964084097eaae05ab53c6a5cd689a1a2805203e9e5fb84d6bf1c897259a37627`

## Projected adapter view

- Source nodes: 48
- Source edges: 96
- Node species: ['Al', 'Si']
- Edge kinds: ['oxygen_bridge']
- Degree set: [4]

## Atomic-path diagnostic view

- Source nodes: 144
- Source edges: 192
- Vertex nodes: 48
- Linker nodes: 96
- Sodium nodes: 0
- Segment kinds: ['linker_vertex', 'vertex_linker']

## Rendered artifacts

- `na_lta_projected_framework_pca_2d.png`
- `na_lta_projected_framework_pca_2d.svg`
- `na_lta_projected_framework_local_t0_hop3_2d.png`
- `na_lta_framework_atomic_paths_pca_2d.png`
- `na_lta_projected_framework_canonical_3d.html`
- `na_lta_projected_framework_2x2x1_3d.html`
- `na_lta_framework_atomic_paths_canonical_3d.html`

The 3-D files are intentionally delivered as external HTML artifacts rather than inline previews.

## Compact node-display extension (0.13.1)

- `markers`: existing full framework vertex markers.
- `dots`: 48 compact color-coded T-site markers; all 96 projected edges retained.
- `hidden`: 0 node marker artists/traces; all 48 scientific node keys and all 96 projected edges retained.
- Hidden mode suppresses periodic ghost markers, node labels, and node legend entries.
- Expanded 2x2x1 edge-only HTML retains periodic replication and the outer cell boundary.

Artifacts:

- `examples/graph_visualization/framework_topology/na_lta_projected_framework_dots_pca_2d.png`
- `examples/graph_visualization/framework_topology/na_lta_projected_framework_edges_only_pca_2d.png`
- `examples/graph_visualization/framework_topology/na_lta_projected_framework_dots_canonical_3d.html`
- `examples/graph_visualization/framework_topology/na_lta_projected_framework_edges_only_canonical_3d.html`
- `examples/graph_visualization/framework_topology/na_lta_projected_framework_edges_only_2x2x1_3d.html`
