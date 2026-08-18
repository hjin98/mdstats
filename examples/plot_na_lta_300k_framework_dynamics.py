#!/usr/bin/env python3
"""Render Na trajectories, canonical mean framework, and framework density."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mdstats import (
    CanonicalCellDisplay,
    FrameworkDensity3DRenderOptions,
    FrameworkDensityOptions,
    FrameworkDynamicsOptions,
    FrameworkDynamicsResources,
    FrameworkTopology,
    Graph3DRenderOptions,
    SpatialRegistrationMode,
    Trajectory3DRenderOptions,
    TrajectoryAtomSelection,
    plot_framework_dynamics_3d,
    prepare_framework_dynamics_scene,
    read_vasp_frames,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trajectory", type=Path)
    parser.add_argument("topology", type=Path)
    parser.add_argument("--output", type=Path, default=Path("na_lta_300K_framework_dynamics.html"))
    parser.add_argument("--timestep-fs", type=float, required=True)
    parser.add_argument("--stride", type=int, default=5)
    parser.add_argument("--grid", type=int, default=32)
    parser.add_argument(
        "--density-render-mode",
        choices=("mesh", "voxel_cloud"),
        default="voxel_cloud",
        help="Explicit triangular shells or a sparse browser-safe voxel cloud.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    trajectory = read_vasp_frames(
        args.trajectory,
        format="vasp-contcar-trajectory",
        stride=args.stride,
        timestep_fs=args.timestep_fs,
    )
    topology = FrameworkTopology.from_dict(json.loads(args.topology.read_text()))

    scene = prepare_framework_dynamics_scene(
        trajectory,
        topology,
        trajectory_selection=TrajectoryAtomSelection(
            species=("Na",),
            label="Na trajectories",
        ),
        framework_density_options=FrameworkDensityOptions(
            grid_shape=(args.grid, args.grid, args.grid),
            gaussian_bandwidth=0.24,
            include_vertex_density=True,
            include_edge_density=True,
            edge_source="projected",
            edge_sample_spacing=1.0,
        ),
        options=FrameworkDynamicsOptions(
            registration_mode=SpatialRegistrationMode.FRAMEWORK_REGISTERED,
            trajectory_display_mode="folded",
            display_cell="reference",
        ),
        resources=FrameworkDynamicsResources(),
    )

    rendered = plot_framework_dynamics_3d(
        scene,
        periodic=CanonicalCellDisplay(),
        graph_options=Graph3DRenderOptions(
            title="300 K Na-LTA: Na trajectories, mean framework, and framework density",
            cell_mode="reference",
            edge_color_mode="constant",
            camera_projection="orthographic",
            equal_aspect=True,
        ),
        trajectory_options=Trajectory3DRenderOptions(
            line_width=2.2,
            opacity=0.52,
            show_start_end=False,
            show_legend=True,
        ),
        framework_density_options=FrameworkDensity3DRenderOptions(
            mass_fractions=(0.55, 0.88),
            inner_opacity=0.48,
            outer_opacity=0.16,
            render_mode=args.density_render_mode,
            cloud_point_size=2.6,
            cloud_opacity=0.25,
            show_samples=False,
            show_legend=True,
        ),
    )

    # The collection time axis is stored in ps in this reader version.
    for trace in rendered.figure.data:
        text = getattr(trace, "text", None)
        if text is None:
            continue
        corrected = []
        changed = False
        for item in text:
            if isinstance(item, str) and "<br>time=" in item and item.endswith(" fs"):
                corrected.append(item[:-3] + " ps")
                changed = True
            else:
                corrected.append(item)
        if changed:
            trace.text = corrected

    rendered.figure.update_layout(
        legend={"itemsizing": "constant", "groupclick": "togglegroup"},
        margin={"l": 0, "r": 0, "t": 55, "b": 0},
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered.write_html(args.output, include_plotlyjs=True)

    fields = scene.framework_density_fields
    print(f"Wrote {args.output}")
    print(f"frames={trajectory.n_frames}, Na paths={scene.trajectory_paths.n_atoms}")
    if fields is not None:
        print(f"vertex integral={fields.vertex_density.integral:.12g}")
        print(f"edge integral={fields.edge_length_density.integral:.12g} angstrom")


if __name__ == "__main__":
    main()
