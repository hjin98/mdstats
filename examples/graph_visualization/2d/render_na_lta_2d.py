"""Reproduce the Na-LTA graph-visualization integration gallery."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from mdstats import (
    ConnectivityScope,
    DistanceConnectivity,
    EdgeStyle,
    Graph2DRenderOptions,
    GraphFocus,
    GraphLayoutOptions,
    GraphStyle,
    NodeStyle,
    NodeStylePatch,
    NodeStyleRule,
    PairCutoffRegistry,
    compute_atomic_connectivity,
    plot_atomic_connectivity_2d,
    read_structure,
)

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
STRUCTURE = ROOT / "tests" / "data" / "Na_LTA_relaxed.POSCAR"
collection = read_structure(STRUCTURE, format="vasp")

framework = compute_atomic_connectivity(
    collection,
    DistanceConnectivity(
        PairCutoffRegistry.from_mapping({("Si", "O"): 2.0, ("Al", "O"): 2.0}),
        scope=ConnectivityScope.from_selection(included_atom_indices=tuple(range(144))),
    ),
)

full = compute_atomic_connectivity(
    collection,
    DistanceConnectivity(
        PairCutoffRegistry.from_mapping(
            {("Si", "O"): 2.0, ("Al", "O"): 2.0, ("Na", "O"): 3.15}
        ),
        scope=ConnectivityScope.from_selection(included_atom_indices=tuple(range(168))),
    ),
)

base = GraphStyle.atomic_default()
framework_style = GraphStyle(
    node_default=NodeStyle(
        face_color=base.node_default.face_color,
        size=34.0,
        marker="o",
        alpha=0.98,
        edge_color="#202020",
        edge_width=0.45,
        zorder=3.0,
    ),
    edge_default=EdgeStyle(
        color="#8A8A8A",
        width=0.65,
        alpha=0.40,
        color_mode="midpoint_split",
        zorder=1.0,
    ),
    node_rules=(
        *base.node_rules,
        NodeStyleRule(
            "symbol", ("O",), NodeStylePatch(size=11.0, edge_width=0.25), priority=5
        ),
        NodeStyleRule("symbol", ("Si", "Al"), NodeStylePatch(size=50.0), priority=5),
    ),
    palette=base.palette,
    background_color="white",
    legend="auto",
)
full_style = GraphStyle(
    node_default=framework_style.node_default,
    edge_default=EdgeStyle(width=0.55, alpha=0.28, color_mode="midpoint_split"),
    node_rules=(
        *base.node_rules,
        NodeStyleRule(
            "symbol", ("O",), NodeStylePatch(size=9.0, edge_width=0.2), priority=5
        ),
        NodeStyleRule("symbol", ("Si", "Al"), NodeStylePatch(size=42.0), priority=5),
        NodeStyleRule(
            "symbol", ("Na",), NodeStylePatch(size=60.0, edge_width=0.65), priority=5
        ),
    ),
    palette=base.palette,
    background_color="white",
    legend="auto",
)


def save(name, rendered):
    rendered.figure.savefig(OUT / f"{name}.png", dpi=240, bbox_inches="tight")
    rendered.figure.savefig(OUT / f"{name}.svg", bbox_inches="tight")
    plt.close(rendered.figure)


save(
    "na_lta_framework_physical_pca",
    plot_atomic_connectivity_2d(
        collection,
        framework,
        frame_index=0,
        layout=GraphLayoutOptions(method="physical", projection="pca"),
        style=framework_style,
        options=Graph2DRenderOptions(
            figsize=(9.0, 8.0),
            show_axes=False,
            title="Relaxed Na-LTA: framework atomic connectivity (PCA projection)",
            periodic_edge_mode="translated_segment",
            periodic_node_mode="local_unwrapped",
        ),
    ),
)

save(
    "na_lta_framework_spring",
    plot_atomic_connectivity_2d(
        collection,
        framework,
        frame_index=0,
        layout=GraphLayoutOptions(method="spring", seed=7, spring_iterations=250),
        style=framework_style,
        options=Graph2DRenderOptions(
            figsize=(9.0, 8.0),
            show_axes=False,
            title="Relaxed Na-LTA: framework connectivity (schematic spring layout)",
        ),
    ),
)

save(
    "na_lta_framework_local_si0",
    plot_atomic_connectivity_2d(
        collection,
        framework,
        frame_index=0,
        layout=GraphLayoutOptions(method="physical", projection="pca"),
        style=framework_style,
        focus=GraphFocus(center_node_keys=(0,), hop_radius=3),
        options=Graph2DRenderOptions(
            figsize=(7.5, 6.5),
            show_axes=False,
            title="Relaxed Na-LTA: three-hop neighborhood of Si atom 0",
            periodic_edge_mode="translated_segment",
            periodic_node_mode="local_unwrapped",
        ),
    ),
)

save(
    "na_lta_full_atomic_physical_pca",
    plot_atomic_connectivity_2d(
        collection,
        full,
        frame_index=0,
        layout=GraphLayoutOptions(method="physical", projection="pca"),
        style=full_style,
        options=Graph2DRenderOptions(
            figsize=(9.5, 8.5),
            show_axes=False,
            title="Relaxed Na-LTA: framework and Na-O atomic connectivity",
            periodic_edge_mode="translated_segment",
            periodic_node_mode="local_unwrapped",
        ),
    ),
)

print("framework", framework.states[0].n_active_atoms, framework.states[0].n_edges)
print("full", full.states[0].n_active_atoms, full.states[0].n_edges)

for projection in ("xy", "xz", "yz"):
    save(
        f"na_lta_framework_{projection}",
        plot_atomic_connectivity_2d(
            collection,
            framework,
            frame_index=0,
            layout=GraphLayoutOptions(method="physical", projection=projection),
            style=framework_style,
            options=Graph2DRenderOptions(
                figsize=(8.2, 7.2),
                show_axes=False,
                title=(
                    "Relaxed Na-LTA: framework atomic connectivity "
                    f"({projection.upper()} projection)"
                ),
                periodic_edge_mode="translated_segment",
                periodic_node_mode="local_unwrapped",
            ),
        ),
    )

save(
    "na_lta_framework_local_si0_hop4",
    plot_atomic_connectivity_2d(
        collection,
        framework,
        frame_index=0,
        layout=GraphLayoutOptions(method="physical", projection="pca"),
        style=framework_style,
        focus=GraphFocus(center_node_keys=(0,), hop_radius=4),
        options=Graph2DRenderOptions(
            figsize=(8.0, 7.0),
            show_axes=False,
            title="Relaxed Na-LTA: four-hop neighborhood of Si atom 0",
            periodic_edge_mode="translated_segment",
            periodic_node_mode="local_unwrapped",
        ),
    ),
)
