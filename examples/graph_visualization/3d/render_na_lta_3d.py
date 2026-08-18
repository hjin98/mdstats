"""Generate interactive Na-LTA graph-visualization acceptance artifacts."""

from __future__ import annotations

from pathlib import Path

from mdstats import (
    CanonicalCellDisplay,
    ConnectivityScope,
    DistanceConnectivity,
    ExpandedCellDisplay,
    Graph3DRenderOptions,
    GraphFocus,
    GraphStyle,
    LocalUnwrappedDisplay,
    PairCutoffRegistry,
    compute_atomic_connectivity,
    plot_atomic_connectivity_3d,
    read_structure,
)

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
STRUCTURE = ROOT / "tests" / "data" / "Na_LTA_relaxed.POSCAR"

collection = read_structure(STRUCTURE, format="vasp")
framework = compute_atomic_connectivity(
    collection,
    DistanceConnectivity(
        cutoffs=PairCutoffRegistry.from_mapping({("Si", "O"): 2.0, ("Al", "O"): 2.0}),
        scope=ConnectivityScope.from_selection(included_atom_indices=tuple(range(144))),
    ),
)
full = compute_atomic_connectivity(
    collection,
    DistanceConnectivity(
        cutoffs=PairCutoffRegistry.from_mapping(
            {
                ("Si", "O"): 2.0,
                ("Al", "O"): 2.0,
                ("Na", "O"): 3.15,
            }
        ),
        scope=ConnectivityScope.from_selection(included_atom_indices=tuple(range(168))),
    ),
)

common = dict(style=GraphStyle.atomic_default(), frame_index=0)

canonical = plot_atomic_connectivity_3d(
    collection,
    framework,
    periodic=CanonicalCellDisplay(),
    options=Graph3DRenderOptions(
        title="Relaxed Na-LTA framework - canonical periodic cell",
        cell_mode="reference",
        camera_projection="perspective",
    ),
    **common,
)
canonical.write_html(OUT / "na_lta_framework_canonical_3d.html")

orthographic = plot_atomic_connectivity_3d(
    collection,
    framework,
    periodic=CanonicalCellDisplay(),
    options=Graph3DRenderOptions(
        title="Relaxed Na-LTA framework - orthographic canonical view",
        cell_mode="reference",
        camera_projection="orthographic",
        camera_eye=(1.5, 1.5, 1.5),
    ),
    **common,
)
orthographic.write_html(OUT / "na_lta_framework_canonical_orthographic_3d.html")

local = plot_atomic_connectivity_3d(
    collection,
    framework,
    periodic=LocalUnwrappedDisplay(0, hop_radius=4),
    focus=GraphFocus(center_node_keys=(0,), hop_radius=4),
    options=Graph3DRenderOptions(
        title="Relaxed Na-LTA - local unwrapped four-hop neighborhood of Si 0",
        cell_mode="reference",
        camera_projection="perspective",
    ),
    **common,
)
local.write_html(OUT / "na_lta_framework_local_si0_hop4_3d.html")

expanded = plot_atomic_connectivity_3d(
    collection,
    framework,
    periodic=ExpandedCellDisplay(((0, 1), (0, 1), (0, 0))),
    options=Graph3DRenderOptions(
        title="Relaxed Na-LTA framework - expanded 2 x 2 x 1 display",
        cell_mode="outer_boundary",
        camera_projection="perspective",
        edge_hover=False,
    ),
    **common,
)
expanded.write_html(OUT / "na_lta_framework_expanded_2x2x1_3d.html")

full_atomic = plot_atomic_connectivity_3d(
    collection,
    full,
    periodic=CanonicalCellDisplay(),
    options=Graph3DRenderOptions(
        title="Relaxed Na-LTA framework plus illustrative Na-O contacts",
        cell_mode="reference",
        camera_projection="perspective",
    ),
    **common,
)
full_atomic.write_html(OUT / "na_lta_full_atomic_canonical_3d.html")

lines = [
    "# Na-LTA interactive 3-D gallery",
    "",
    "All files are standalone Plotly HTML documents using the CDN-hosted Plotly runtime.",
    "",
    f"Framework scientific graph: {framework.states[0].n_active_atoms} nodes, {framework.states[0].n_edges} edges.",
    f"Full illustrative graph: {full.states[0].n_active_atoms} nodes, {full.states[0].n_edges} edges.",
    "",
    "The Na-O cutoff (3.15 A) is an illustrative visualization fixture, not a universal bonding rule.",
    "",
    "## Display counts",
    "",
]
for name, result in [
    ("canonical", canonical),
    ("orthographic canonical", orthographic),
    ("local Si0 hop4", local),
    ("expanded 2x2x1", expanded),
    ("full atomic canonical", full_atomic),
]:
    lines.append(
        f"- {name}: {result.periodic_view.graph.n_nodes} display nodes, "
        f"{result.periodic_view.graph.n_edges} display edges, "
        f"{result.render_metadata['trace_count']} Plotly traces."
    )
(OUT / "README.md").write_text("\n".join(lines) + "\n")
