#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from mdstats import (
    AtomicDensity3DRenderOptions,
    AtomicDensityOptions,
    AtomicDensitySelection,
    AtomicMeanGraph3DRenderOptions,
    AtomicMeanGraphOptions,
    CanonicalCellDisplay,
    DistanceConnectivity,
    FrameworkDynamicsOptions,
    FrameworkDynamicsResources,
    FrameworkTopology,
    Graph3DRenderOptions,
    PairCutoffRegistry,
    SpatialRegistrationMode,
    Trajectory3DRenderOptions,
    TrajectoryAtomSelection,
    compute_atomic_connectivity,
    plot_framework_dynamics_3d,
    prepare_framework_dynamics_scene,
    read_vasp_frames,
)

trajectory_path = Path('/mnt/data/TRAJECTORY(2)')
topology_path = Path('/mnt/data/na_lta_framework_topology.json')
output_path = Path('/mnt/data/na_lta_300K_atomic_mean_graph_density.html')

trajectory = read_vasp_frames(
    trajectory_path,
    format='vasp-contcar-trajectory',
    stride=10,
    timestep_fs=1.0,
)
topology = FrameworkTopology.from_dict(json.loads(topology_path.read_text()))
connectivity = compute_atomic_connectivity(
    trajectory,
    DistanceConnectivity(
        cutoffs=PairCutoffRegistry.from_mapping({
            ('Si', 'O'): 2.1,
            ('Al', 'O'): 2.1,
            ('Na', 'O'): 2.9,
        })
    ),
)

scene = prepare_framework_dynamics_scene(
    trajectory,
    topology,
    trajectory_selection=TrajectoryAtomSelection(species=('Na',), label='Na trajectories'),
    atomic_connectivity=connectivity,
    atomic_mean_graph_options=AtomicMeanGraphOptions(mode='occupancy', occupancy_threshold=0.95),
    atomic_density_selections=(
        AtomicDensitySelection(species=('Na',), label='Na density'),
    ),
    atomic_density_options=AtomicDensityOptions(
        grid_shape=(48, 48, 48),
        gaussian_bandwidth=0.22,
    ),
    options=FrameworkDynamicsOptions(
        registration_mode=SpatialRegistrationMode.FRAMEWORK_REGISTERED,
        trajectory_display_mode='folded',
        display_cell='reference',
    ),
    resources=FrameworkDynamicsResources(),
)

result = plot_framework_dynamics_3d(
    scene,
    periodic=CanonicalCellDisplay(),
    graph_options=Graph3DRenderOptions(
        title='300 K Na-LTA: atomic mean net + Na density + mean framework',
        cell_mode='reference',
        edge_color_mode='constant',
        camera_projection='orthographic',
        equal_aspect=True,
    ),
    atomic_mean_graph_options=AtomicMeanGraph3DRenderOptions(
        node_size=4.0,
        edge_width=1.6,
        edge_opacity=0.45,
    ),
    trajectory_options=Trajectory3DRenderOptions(
        line_width=1.6,
        opacity=0.30,
        show_start_end=False,
        show_legend=True,
    ),
    density_options=AtomicDensity3DRenderOptions(
        mass_fractions=(0.50, 0.80, 0.95),
        inner_opacity=0.24,
        outer_opacity=0.05,
        render_mode='mesh',
        show_samples=False,
        show_legend=True,
    ),
)
result.figure.update_layout(
    legend={'itemsizing': 'constant', 'groupclick': 'togglegroup'},
    margin={'l': 0, 'r': 0, 't': 55, 'b': 0},
)
result.write_html(output_path, include_plotlyjs=True)
print(output_path)
