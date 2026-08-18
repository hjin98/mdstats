"""Generate Na-LTA framework-topology visualization acceptance artifacts."""

from __future__ import annotations

from pathlib import Path


from mdstats import (
    CanonicalCellDisplay,
    ConnectivityScope,
    DistanceConnectivity,
    ExpandedCellDisplay,
    FrameworkAtomRole,
    FrameworkGraphDisplayMode,
    FrameworkMapping,
    FrameworkPathRule,
    Graph2DRenderOptions,
    Graph3DRenderOptions,
    GraphFocus,
    GraphLayoutOptions,
    GraphStyle,
    NodeDisplayMode,
    LocalUnwrappedDisplay,
    PairCutoffRegistry,
    build_framework_topology,
    compute_atomic_connectivity,
    graph_view_from_framework_topology,
    plot_framework_topology_2d,
    plot_framework_topology_3d,
    read_structure,
)


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    output = Path(__file__).resolve().parent
    structure = root / "tests" / "data" / "Na_LTA_relaxed.POSCAR"
    collection = read_structure(structure, format="vasp")
    connectivity = compute_atomic_connectivity(
        collection,
        DistanceConnectivity(
            cutoffs=PairCutoffRegistry.from_mapping(
                {("Si", "O"): 2.0, ("Al", "O"): 2.0}
            ),
            scope=ConnectivityScope.from_selection(
                included_atom_indices=tuple(range(144))
            ),
        ),
    )
    mapping = FrameworkMapping.from_symbol_roles(
        {
            "Si": FrameworkAtomRole.VERTEX,
            "Al": FrameworkAtomRole.VERTEX,
            "O": FrameworkAtomRole.LINKER,
            "Na": FrameworkAtomRole.SPECTATOR,
        },
        path_rules=(
            FrameworkPathRule.from_symbols("T-O-T", ("O",), edge_kind="oxygen_bridge"),
        ),
        name="Na-LTA T-O-T projection",
    )
    topology = build_framework_topology(connectivity.states[0], mapping)

    projected_view = graph_view_from_framework_topology(
        collection, topology, frame_index=0
    )
    path_view = graph_view_from_framework_topology(
        collection,
        topology,
        frame_index=0,
        display_mode=FrameworkGraphDisplayMode.ATOMIC_PATHS,
    )

    projected = plot_framework_topology_2d(
        collection,
        topology,
        frame_index=0,
        periodic=LocalUnwrappedDisplay(0),
        layout=GraphLayoutOptions(method="physical", projection="pca"),
        options=Graph2DRenderOptions(
            show_axes=False,
            title="Na-LTA projected framework topology",
            figsize=(9.0, 8.0),
        ),
    )
    projected.figure.savefig(
        output / "na_lta_projected_framework_pca_2d.png",
        dpi=220,
        bbox_inches="tight",
    )
    projected.figure.savefig(
        output / "na_lta_projected_framework_pca_2d.svg",
        bbox_inches="tight",
    )

    projected_dots = plot_framework_topology_2d(
        collection,
        topology,
        frame_index=0,
        periodic=LocalUnwrappedDisplay(0),
        layout=GraphLayoutOptions(method="physical", projection="pca"),
        style=GraphStyle.framework_default(
            node_display_mode=NodeDisplayMode.DOTS, node_dot_size=16.0
        ),
        options=Graph2DRenderOptions(
            show_axes=False,
            title="Na-LTA projected framework topology: compact vertices",
            figsize=(9.0, 8.0),
        ),
    )
    projected_dots.figure.savefig(
        output / "na_lta_projected_framework_dots_pca_2d.png",
        dpi=220,
        bbox_inches="tight",
    )

    projected_edges_only = plot_framework_topology_2d(
        collection,
        topology,
        frame_index=0,
        periodic=LocalUnwrappedDisplay(0),
        layout=GraphLayoutOptions(method="physical", projection="pca"),
        style=GraphStyle.framework_default(node_display_mode=NodeDisplayMode.HIDDEN),
        options=Graph2DRenderOptions(
            show_axes=False,
            title="Na-LTA projected framework topology: edges only",
            figsize=(9.0, 8.0),
        ),
    )
    projected_edges_only.figure.savefig(
        output / "na_lta_projected_framework_edges_only_pca_2d.png",
        dpi=220,
        bbox_inches="tight",
    )

    local = plot_framework_topology_2d(
        collection,
        topology,
        frame_index=0,
        focus=GraphFocus(center_node_keys=(0,), hop_radius=3),
        periodic=LocalUnwrappedDisplay(0, hop_radius=3),
        layout=GraphLayoutOptions(method="physical", projection="pca"),
        options=Graph2DRenderOptions(
            show_axes=False,
            title="Na-LTA projected framework: three-hop neighborhood of T0",
            figsize=(8.0, 7.0),
        ),
    )
    local.figure.savefig(
        output / "na_lta_projected_framework_local_t0_hop3_2d.png",
        dpi=220,
        bbox_inches="tight",
    )

    diagnostic = plot_framework_topology_2d(
        collection,
        topology,
        frame_index=0,
        display_mode="atomic_paths",
        periodic=LocalUnwrappedDisplay(0),
        layout=GraphLayoutOptions(method="physical", projection="pca"),
        options=Graph2DRenderOptions(
            show_axes=False,
            title="Na-LTA retained T-O-T atomic paths",
            figsize=(9.0, 8.0),
        ),
    )
    diagnostic.figure.savefig(
        output / "na_lta_framework_atomic_paths_pca_2d.png",
        dpi=220,
        bbox_inches="tight",
    )

    canonical_3d = plot_framework_topology_3d(
        collection,
        topology,
        frame_index=0,
        periodic=CanonicalCellDisplay(),
        options=Graph3DRenderOptions(
            title="Na-LTA projected framework topology",
            cell_mode="reference",
            edge_color_mode="constant",
        ),
    )
    canonical_3d.write_html(output / "na_lta_projected_framework_canonical_3d.html")

    expanded_3d = plot_framework_topology_3d(
        collection,
        topology,
        frame_index=0,
        periodic=ExpandedCellDisplay(((0, 1), (0, 1), (0, 0))),
        options=Graph3DRenderOptions(
            title="Na-LTA projected framework topology, 2x2x1",
            cell_mode="outer_boundary",
            edge_color_mode="constant",
        ),
    )
    expanded_3d.write_html(output / "na_lta_projected_framework_2x2x1_3d.html")

    dots_3d = plot_framework_topology_3d(
        collection,
        topology,
        frame_index=0,
        periodic=CanonicalCellDisplay(),
        style=GraphStyle.framework_default(node_display_mode=NodeDisplayMode.DOTS),
        options=Graph3DRenderOptions(
            title="Na-LTA projected framework: compact vertices",
            cell_mode="reference",
            edge_color_mode="constant",
        ),
    )
    dots_3d.write_html(output / "na_lta_projected_framework_dots_canonical_3d.html")

    edges_only_3d = plot_framework_topology_3d(
        collection,
        topology,
        frame_index=0,
        periodic=CanonicalCellDisplay(),
        style=GraphStyle.framework_default(node_display_mode=NodeDisplayMode.HIDDEN),
        options=Graph3DRenderOptions(
            title="Na-LTA projected framework: edges only",
            cell_mode="reference",
            edge_color_mode="constant",
        ),
    )
    edges_only_3d.write_html(
        output / "na_lta_projected_framework_edges_only_canonical_3d.html"
    )

    edges_only_expanded_3d = plot_framework_topology_3d(
        collection,
        topology,
        frame_index=0,
        periodic=ExpandedCellDisplay(((0, 1), (0, 1), (0, 0))),
        style=GraphStyle.framework_default(node_display_mode=NodeDisplayMode.HIDDEN),
        options=Graph3DRenderOptions(
            title="Na-LTA projected framework 2x2x1: edges only",
            cell_mode="outer_boundary",
            edge_color_mode="constant",
        ),
    )
    edges_only_expanded_3d.write_html(
        output / "na_lta_projected_framework_edges_only_2x2x1_3d.html"
    )

    paths_3d = plot_framework_topology_3d(
        collection,
        topology,
        frame_index=0,
        display_mode="atomic_paths",
        periodic=CanonicalCellDisplay(),
        options=Graph3DRenderOptions(
            title="Na-LTA retained framework atomic paths",
            cell_mode="reference",
            edge_color_mode="midpoint_split",
        ),
    )
    paths_3d.write_html(output / "na_lta_framework_atomic_paths_canonical_3d.html")

    report = f"""# Na-LTA Framework Visualization Integration Audit

## Scientific source

- Collection atoms: {collection.n_atoms}
- Atomic connectivity active atoms: {connectivity.states[0].n_active_atoms}
- Atomic T-O edges: {connectivity.states[0].n_edges}
- Framework vertices: {topology.n_vertices}
- Framework projected edges: {topology.n_edges}
- Framework graph digest: `{topology.graph_digest}`

## Projected adapter view

- Source nodes: {projected_view.n_nodes}
- Source edges: {projected_view.n_edges}
- Node species: {sorted(set(projected_view.node_attributes["symbol"]))}
- Edge kinds: {sorted(set(projected_view.edge_attributes["edge_kind"]))}
- Degree set: {sorted(set(int(x) for x in projected_view.node_attributes["projected_degree"]))}

## Atomic-path diagnostic view

- Source nodes: {path_view.n_nodes}
- Source edges: {path_view.n_edges}
- Vertex nodes: {sum(role == "vertex" for role in path_view.node_attributes["framework_role"])}
- Linker nodes: {sum(role == "linker" for role in path_view.node_attributes["framework_role"])}
- Sodium nodes: {sum(symbol == "Na" for symbol in path_view.node_attributes["symbol"])}
- Segment kinds: {sorted(set(path_view.edge_attributes["segment_kind"]))}

## Rendered artifacts

- `na_lta_projected_framework_pca_2d.png`
- `na_lta_projected_framework_pca_2d.svg`
- `na_lta_projected_framework_dots_pca_2d.png`
- `na_lta_projected_framework_edges_only_pca_2d.png`
- `na_lta_projected_framework_local_t0_hop3_2d.png`
- `na_lta_framework_atomic_paths_pca_2d.png`
- `na_lta_projected_framework_canonical_3d.html`
- `na_lta_projected_framework_2x2x1_3d.html`
- `na_lta_projected_framework_dots_canonical_3d.html`
- `na_lta_projected_framework_edges_only_canonical_3d.html`
- `na_lta_projected_framework_edges_only_2x2x1_3d.html`
- `na_lta_framework_atomic_paths_canonical_3d.html`

The 3-D files are intentionally delivered as external HTML artifacts rather than inline previews.
"""
    (
        root / "audits" / "plotting" / "framework_topology_graph_integration_audit.md"
    ).write_text(report)


if __name__ == "__main__":
    main()
