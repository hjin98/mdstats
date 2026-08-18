#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def _bootstrap_mdstats_source_tree() -> Path | None:
    """Make the adjacent source checkout importable for direct example runs.

    When this file lives in ``<repository>/examples``, launching it directly puts
    only the examples directory on ``sys.path``. Prefer the matching repository
    source tree over any separately installed mdstats version. If the script has
    been copied elsewhere, leave ``sys.path`` unchanged and use the installed
    package normally.
    """
    script_path = Path(__file__).resolve()
    if len(script_path.parents) < 2:
        return None
    repository_root = script_path.parents[1]
    package_init = repository_root / "mdstats" / "__init__.py"
    if not package_init.is_file():
        return None
    root_text = str(repository_root)
    if not sys.path or sys.path[0] != root_text:
        try:
            sys.path.remove(root_text)
        except ValueError:
            pass
        sys.path.insert(0, root_text)
    return repository_root


SOURCE_TREE_ROOT = _bootstrap_mdstats_source_tree()

from ase.data import chemical_symbols

from mdstats import (
    AtomicDensity3DRenderOptions,
    AtomicDensityOptions,
    AtomicDensitySelection,
    AtomicMeanGraph3DRenderOptions,
    AtomicMeanGraphOptions,
    BrowserMeshBudget,
    BrowserMeshProfile,
    CanonicalCellDisplay,
    HystereticDistanceConnectivity,
    FrameworkAtomRole,
    FrameworkDynamicsOptions,
    FrameworkDynamicsResources,
    FrameworkMapping,
    FrameworkPathRule,
    FrameworkTopology,
    TopologyCatalog,
    Graph3DRenderOptions,
    PairCutoffRegistry,
    SpatialRegistrationMode,
    ProgressEmitter,
    TextProgressPort,
    Trajectory3DRenderOptions,
    TrajectoryAtomSelection,
    build_topology_catalog,
    compute_atomic_connectivity,
    plot_framework_dynamics_3d,
    prepare_framework_dynamics_scene,
    read_vasp_frames,
)


TOPOLOGY_CACHE_SUFFIX = '_topology_catalog.json'
FRAMEWORK_SPECIES_ORDER = ('Si', 'Al', 'O')
MOBILE_SPECIES_ORDER = ('Li', 'Na', 'K')
MOBILE_OXYGEN_CUTOFFS = {
    'Li': 2.6,
    'Na': 2.9,
    'K': 3.3,
}



def framework_mapping() -> FrameworkMapping:
    return FrameworkMapping.from_symbol_roles(
        {
            'Si': FrameworkAtomRole.VERTEX,
            'Al': FrameworkAtomRole.VERTEX,
            'O': FrameworkAtomRole.LINKER,
            'Li': FrameworkAtomRole.SPECTATOR,
            'Na': FrameworkAtomRole.SPECTATOR,
            'K': FrameworkAtomRole.SPECTATOR,
        },
        path_rules=(
            FrameworkPathRule.from_symbols(
                'T-O-T', ('O',), edge_kind='oxygen_bridge'
            ),
        ),
    )


def detect_present_species(trajectory) -> tuple[str, ...]:
    present = {chemical_symbols[int(z)] for z in trajectory.atomic_numbers}
    ordered = [
        symbol
        for symbol in FRAMEWORK_SPECIES_ORDER + MOBILE_SPECIES_ORDER
        if symbol in present
    ]
    return tuple(ordered)


def detect_mobile_species(trajectory) -> tuple[str, ...]:
    present = set(detect_present_species(trajectory))
    return tuple(symbol for symbol in MOBILE_SPECIES_ORDER if symbol in present)


def _sample_framework_bond_distances(
    trajectory,
    left_symbol: str,
    *,
    coordination_number: int = 4,
) -> list[float]:
    """Sample the nearest framework bond shell for hysteresis calibration.

    LTA T atoms are tetrahedrally coordinated.  Sampling only the single
    nearest oxygen underestimates the formation cutoff and can omit the long
    member of an otherwise intact T--O shell.  This helper therefore records
    the four nearest oxygen distances for every selected T atom.
    """
    from ase.geometry import find_mic
    import numpy as np

    symbols = [chemical_symbols[int(z)] for z in trajectory.atomic_numbers]
    left = np.asarray(
        [i for i, value in enumerate(symbols) if value == left_symbol],
        dtype=np.int64,
    )
    oxygen = np.asarray(
        [i for i, value in enumerate(symbols) if value == 'O'],
        dtype=np.int64,
    )
    if left.size == 0 or oxygen.size < coordination_number:
        return []
    sample_count = min(96, trajectory.n_frames)
    frame_indices = np.unique(
        np.linspace(0, trajectory.n_frames - 1, sample_count).round().astype(int)
    )
    values: list[float] = []
    for frame in frame_indices:
        cell = np.asarray(trajectory.cells[frame], dtype=float)
        cart = np.asarray(trajectory.fractional_positions[frame], dtype=float) @ cell
        delta = cart[oxygen][None, :, :] - cart[left][:, None, :]
        _mic, distances = find_mic(
            delta.reshape(-1, 3),
            cell,
            pbc=trajectory.pbc,
        )
        matrix = np.asarray(distances, dtype=float).reshape(left.size, oxygen.size)
        nearest_shell = np.partition(
            matrix,
            kth=coordination_number - 1,
            axis=1,
        )[:, :coordination_number]
        values.extend(
            float(value)
            for value in nearest_shell.reshape(-1)
            if np.isfinite(value)
        )
    return values


def _calibrated_framework_cutoffs(
    trajectory,
    *,
    formation_override: float | None = None,
    breaking_override: float | None = None,
) -> tuple[dict[tuple[str, str], float], dict[tuple[str, str], float], dict[str, dict[str, float]]]:
    """Calibrate separate formation and breaking cutoffs for Si/Al--O."""
    import numpy as np

    present = set(detect_present_species(trajectory))
    formation: dict[tuple[str, str], float] = {}
    breaking: dict[tuple[str, str], float] = {}
    audit: dict[str, dict[str, float]] = {}
    lower_bounds = {'Si': 1.90, 'Al': 1.95}
    formation_caps = {'Si': 2.12, 'Al': 2.18}
    breaking_caps = {'Si': 2.38, 'Al': 2.45}

    for symbol in ('Si', 'Al'):
        if symbol not in present:
            continue
        sampled = np.asarray(
            _sample_framework_bond_distances(trajectory, symbol),
            dtype=float,
        )
        if sampled.size:
            q995 = float(np.quantile(sampled, 0.995))
            q999 = float(np.quantile(sampled, 0.999))
            form = float(
                np.clip(q995 + 0.03, lower_bounds[symbol], formation_caps[symbol])
            )
            retain = float(
                np.clip(
                    max(form + 0.18, q999 + 0.10),
                    form + 0.12,
                    breaking_caps[symbol],
                )
            )
        else:
            q995 = float('nan')
            q999 = float('nan')
            form = 2.05 if symbol == 'Si' else 2.10
            retain = 2.30 if symbol == 'Si' else 2.38

        if formation_override is not None:
            form = float(formation_override)
        if breaking_override is not None:
            retain = float(breaking_override)
        if not form < retain:
            raise ValueError(
                'Framework hysteresis requires formation cutoff < breaking cutoff; '
                f'got {form:.6g} and {retain:.6g} A for {symbol}-O.'
            )
        formation[(symbol, 'O')] = form
        breaking[(symbol, 'O')] = retain
        audit[symbol] = {
            'formation_cutoff_angstrom': form,
            'breaking_cutoff_angstrom': retain,
            'sample_q995_angstrom': q995,
            'sample_q999_angstrom': q999,
            'sample_count': float(sampled.size),
        }
    return formation, breaking, audit


def framework_connectivity_definition(
    trajectory,
    *,
    formation_override: float | None = None,
    breaking_override: float | None = None,
) -> tuple[HystereticDistanceConnectivity, dict[str, dict[str, float]]]:
    """Return framework-only hysteresis for topology classification."""
    formation, breaking, audit = _calibrated_framework_cutoffs(
        trajectory,
        formation_override=formation_override,
        breaking_override=breaking_override,
    )
    return (
        HystereticDistanceConnectivity(
            formation_cutoffs=PairCutoffRegistry.from_mapping(formation),
            breaking_cutoffs=PairCutoffRegistry.from_mapping(breaking),
        ),
        audit,
    )


def atomic_connectivity_definition(
    trajectory,
    framework_definition: HystereticDistanceConnectivity,
) -> HystereticDistanceConnectivity:
    """Extend framework hysteresis with mobile-ion--oxygen contacts."""
    formation = {
        pair: float(cutoff.radius)
        for pair, cutoff in framework_definition.formation_cutoffs.cutoffs.items()
    }
    breaking = {
        pair: float(cutoff.radius)
        for pair, cutoff in framework_definition.breaking_cutoffs.cutoffs.items()
    }
    present = set(detect_present_species(trajectory))
    for symbol in MOBILE_SPECIES_ORDER:
        if symbol in present:
            formation[(symbol, 'O')] = MOBILE_OXYGEN_CUTOFFS[symbol]
            breaking[(symbol, 'O')] = MOBILE_OXYGEN_CUTOFFS[symbol] + 0.25
    return HystereticDistanceConnectivity(
        formation_cutoffs=PairCutoffRegistry.from_mapping(formation),
        breaking_cutoffs=PairCutoffRegistry.from_mapping(breaking),
    )


def build_density_selections(trajectory) -> tuple[AtomicDensitySelection, ...]:
    selections: list[AtomicDensitySelection] = []
    for symbol in detect_mobile_species(trajectory):
        selections.append(
            AtomicDensitySelection(species=(symbol,), label=f'{symbol} density')
        )
    for symbol in FRAMEWORK_SPECIES_ORDER:
        if symbol in detect_present_species(trajectory):
            selections.append(
                AtomicDensitySelection(species=(symbol,), label=f'{symbol} density')
            )
    return tuple(selections)


def trajectory_selection_label(trajectory) -> str:
    mobile = detect_mobile_species(trajectory)
    if not mobile:
        return 'Framework trajectories'
    return 'Framework and alkali trajectories'


def default_topology_cache_path(output: Path) -> Path:
    return output.with_name(output.stem + TOPOLOGY_CACHE_SUFFIX)


def default_output_path() -> Path:
    return Path('lta_density_framework_trajectories.html')


def figure_title(trajectory) -> str:
    mobile = detect_mobile_species(trajectory)
    mobile_text = ' + '.join(mobile) if mobile else 'no alkali cations'
    return (
        'LTA: detected-species densities, trajectories, '
        f'atomic mean net, and mean framework ({mobile_text}; '
        f'{trajectory.n_frames} frames)'
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            'Render an LTA trajectory with the averaged framework, occupancy-filtered '            'atomic mean net, three-shell atomic densities, and trajectories. '            'The script detects Li/Na/K automatically and includes the alkali '            'species that are present.'
        )
    )
    parser.add_argument('trajectory', type=Path, help='Watcher-generated TRAJECTORY file.')
    parser.add_argument(
        '--topology',
        type=Path,
        default=None,
        help=(
            'Optional FrameworkTopology or TopologyCatalog JSON override/cache. If supplied, the '
            'script loads this topology instead of inferring one from the '
            'trajectory.'
        ),
    )
    parser.add_argument(
        '--topology-cache',
        type=Path,
        default=None,
        help=(
            'Optional output path for the inferred TopologyCatalog JSON cache. '
            'Default: <output stem>_framework_topology.json next to the HTML.'
        ),
    )
    parser.add_argument(
        '--no-topology-cache',
        action='store_true',
        help='Do not write the inferred framework-topology cache file.',
    )
    parser.add_argument(
        '--framework-formation-cutoff',
        type=float,
        default=None,
        help=(
            'Optional Si/Al--O formation-cutoff override in angstrom. '
            'Default: calibrate from the four-nearest-oxygen shell.'
        ),
    )
    parser.add_argument(
        '--framework-breaking-cutoff',
        type=float,
        default=None,
        help=(
            'Optional Si/Al--O breaking-cutoff override in angstrom. '
            'Must be larger than the formation cutoff.'
        ),
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=default_output_path(),
        help='Self-contained output HTML file.',
    )
    parser.add_argument(
        '--title',
        type=str,
        default=None,
        help='Optional custom figure title. Default: an automatically generated LTA title.',
    )
    parser.add_argument(
        '--stride',
        type=int,
        default=1,
        help='Frame stride. The default 1 uses every trajectory frame.',
    )
    parser.add_argument(
        '--max-memory',
        default=None,
        help='Maximum package-owned memory, for example 12GiB. Default: 80%% of detected availability.',
    )
    parser.add_argument(
        '--max-threads',
        type=int,
        default=None,
        help='Maximum worker/native threads. Default: floor(90%% of detected CPU allocation).',
    )
    parser.add_argument(
        '--wall-time-target',
        '--max-wall-time',
        dest='max_wall_time',
        type=float,
        default=None,
        help='Advisory complete-scene wall-time target in seconds; never a hard stop. --max-wall-time is retained as a compatibility alias. Default: 1200.',
    )
    parser.add_argument(
        '--browser-profile',
        choices=('compact', 'balanced', 'quality'),
        default='balanced',
        help='Interactive mesh profile. Default: balanced (600,000 final density faces).',
    )
    parser.add_argument(
        '--max-browser-faces',
        type=int,
        default=None,
        help='Optional final browser density-face override; the generic interactive profile is used otherwise.',
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress progress messages; final result summaries are still printed.',
    )
    return parser.parse_args()


def resolve_framework_topology(
    trajectory,
    args: argparse.Namespace,
    progress: ProgressEmitter,
    framework_definition: HystereticDistanceConnectivity,
    hysteresis_audit: dict[str, dict[str, float]],
):
    if args.topology is not None:
        progress.update("framework_topology", f"loading override from {args.topology}")
        payload = json.loads(args.topology.read_text())
        if 'frame_topology_ids' in payload and 'topologies' in payload:
            value = TopologyCatalog.from_dict(payload)
            source = 'user_supplied_catalog'
        else:
            value = FrameworkTopology.from_dict(payload)
            source = 'user_supplied_topology'
        return value, None, {'source': source, 'path': str(args.topology)}

    progress.started("framework_topology", "computing hysteretic atomic connectivity across selected frames")
    connectivity_started = time.perf_counter()
    definition = framework_definition
    connectivity = compute_atomic_connectivity(trajectory, definition)
    progress.update(
        "framework_topology",
        'hysteretic atomic connectivity complete; '
        f'{connectivity.n_states} unique states in {time.perf_counter() - connectivity_started:.1f} s',
    )
    progress.update("framework_topology", "projecting and classifying framework topology states")
    catalog_started = time.perf_counter()
    catalog = build_topology_catalog(trajectory, connectivity, framework_mapping())
    progress.completed(
        "framework_topology",
        'catalog complete; '
        f'consistency={catalog.consistency.value}, topologies={len(catalog.topologies)}, '
        f'elapsed={time.perf_counter() - catalog_started:.1f} s',
    )
    cache_written = None
    if not args.no_topology_cache:
        cache_path = args.topology_cache or default_topology_cache_path(args.output)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(catalog.to_dict(), indent=2) + '\n')
        cache_written = str(cache_path)
        progress.update("framework_topology", f"wrote full topology-catalog cache to {cache_path}")
    return catalog, connectivity, {
        'source': 'inferred_hysteretic_catalog',
        'connectivity_state_count': int(connectivity.n_states),
        'catalog_consistency': catalog.consistency.value,
        'n_topologies': len(catalog.topologies),
        'cache_written': cache_written,
        'connectivity_definition': definition.to_dict(),
        'framework_hysteresis_calibration': hysteresis_audit,
    }


def main() -> None:
    args = parse_arguments()
    progress_port = TextProgressPort(
        label="LTA plot",
        stream=sys.stdout,
        enabled=not args.quiet,
        show_source=False,
    )
    progress = ProgressEmitter(
        progress_port,
        source="examples.lta_density",
    )
    if SOURCE_TREE_ROOT is None:
        progress.update("import_mode", "using installed mdstats package")
    else:
        progress.update("import_mode", f"using source checkout at {SOURCE_TREE_ROOT}")
    progress.started("trajectory_input", f"reading {args.trajectory} with stride={args.stride}")
    parse_started = time.perf_counter()
    trajectory = read_vasp_frames(
        args.trajectory,
        format='vasp-contcar-trajectory',
        stride=args.stride,
        timestep_fs=1.0,
    )
    progress.completed("trajectory_input", 
        f'loaded {trajectory.n_frames} frames and {trajectory.n_atoms} atoms '
        f'in {time.perf_counter() - parse_started:.1f} s'
    )
    present_species = detect_present_species(trajectory)
    mobile_species = detect_mobile_species(trajectory)
    density_selections = build_density_selections(trajectory)
    progress.update("species_detection", 
        f'present={present_species}, mobile={mobile_species}, '
        f'density_fields={len(density_selections)}'
    )
    framework_definition, hysteresis_audit = framework_connectivity_definition(
        trajectory,
        formation_override=args.framework_formation_cutoff,
        breaking_override=args.framework_breaking_cutoff,
    )
    cutoff_summary = ', '.join(
        f"{symbol}-O {values['formation_cutoff_angstrom']:.3f}/{values['breaking_cutoff_angstrom']:.3f} A"
        for symbol, values in hysteresis_audit.items()
    )
    progress.update(
        "framework_topology",
        "hysteresis formation/breaking cutoffs: " + cutoff_summary,
    )
    topology, framework_connectivity, topology_metadata = resolve_framework_topology(
        trajectory,
        args,
        progress,
        framework_definition,
        hysteresis_audit,
    )
    full_definition = atomic_connectivity_definition(
        trajectory,
        framework_definition,
    )
    if full_definition.to_dict() == framework_definition.to_dict() and framework_connectivity is not None:
        connectivity = framework_connectivity
    else:
        progress.started(
            "atomic_mean_graph",
            "computing hysteretic framework/mobile connectivity for the mean graph",
        )
        connectivity = compute_atomic_connectivity(trajectory, full_definition)
        progress.completed(
            "atomic_mean_graph",
            f"connectivity complete; {connectivity.n_states} unique states",
        )

    resources = FrameworkDynamicsResources(
        max_memory_bytes=args.max_memory,
        max_threads=args.max_threads,
        max_wall_time_seconds=args.max_wall_time,
    )
    progress.update("resource_policy", 
        'resolved '
        f'memory={resources.max_memory_bytes / 1024**3:.2f} GiB, '
        f'threads={resources.max_threads}, '
        f'wall_time_target={resources.max_wall_time_seconds:.0f} s (advisory)'
    )
    progress.started("scene_preparation", "starting framework registration, trajectories, mean graph, and density fields")
    scene = prepare_framework_dynamics_scene(
        trajectory,
        topology,
        trajectory_selection=TrajectoryAtomSelection(
            species=present_species,
            label=trajectory_selection_label(trajectory),
        ),
        atomic_connectivity=connectivity,
        atomic_mean_graph_options=AtomicMeanGraphOptions(
            mode='occupancy', occupancy_threshold=0.95
        ),
        atomic_density_selections=density_selections,
        atomic_density_options=AtomicDensityOptions(
            grid_interval=0.20,
            gaussian_to_grid_ratio=2.0,
            adaptive_smearing=True,
            max_smearing_to_sample_sd_ratio=0.50,
            sample_sd_quantile=0.10,
        ),
        options=FrameworkDynamicsOptions(
            registration_mode=SpatialRegistrationMode.FRAMEWORK_REGISTERED,
            trajectory_display_mode='folded',
            display_cell='reference',
        ),
        resources=resources,
        progress=progress_port,
    )

    progress.started("rendering", "starting Plotly assembly and density-mesh extraction")
    result = plot_framework_dynamics_3d(
        scene,
        periodic=CanonicalCellDisplay(),
        graph_options=Graph3DRenderOptions(
            title=args.title or figure_title(trajectory),
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
            opacity=0.28,
            # show_start_end=True and endpoint legend labels are defaults.
            show_legend=True,
        ),
        mesh_profile=(
            BrowserMeshProfile.coerce(args.browser_profile)
            if args.max_browser_faces is None
            else BrowserMeshProfile.custom(
                BrowserMeshBudget(max_final_density_faces=args.max_browser_faces)
            )
        ),
        density_options=AtomicDensity3DRenderOptions(
            mass_fractions=(0.50, 0.80, 0.95),
            inner_opacity=0.22,
            outer_opacity=0.04,
            render_mode='mesh',
            show_samples=False,
            show_legend=True,
        ),
        progress=progress_port,
    )
    progress.completed("rendering", "Plotly scene assembly complete")
    result.figure.update_layout(
        legend={'itemsizing': 'constant', 'groupclick': 'togglegroup'},
        margin={'l': 0, 'r': 0, 't': 55, 'b': 0},
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    progress.started("output", f"serializing self-contained HTML to {args.output}")
    html_started = time.perf_counter()
    result.write_html(args.output, include_plotlyjs=True)
    output_size_mib = args.output.stat().st_size / 1024**2
    progress.completed("output", 
        f'wrote {output_size_mib:.1f} MiB HTML in '
        f'{time.perf_counter() - html_started:.1f} s'
    )
    progress.completed("workflow", "complete")
    print(args.output)
    print('present_species=' + repr(present_species))
    print('mobile_species=' + repr(mobile_species))
    print('topology_resolution=' + repr(topology_metadata))
    print('runtime_resource_budget=' + repr(scene.resources.runtime_budget.to_json_dict()))
    print(
        f'frames={trajectory.n_frames} atoms={trajectory.n_atoms} '
        f'trajectory_traces={len(set(result.trajectory_trace_indices.values()))} '
        f'endpoint_traces={len(result.endpoint_trace_indices)}'
    )
    print(
        'endpoint_legend_entries='
        + repr([result.figure.data[i].name for i in result.endpoint_trace_indices])
    )
    for field in scene.atomic_density_fields:
        print(
            field.label,
            'backend=', field.storage_backend,
            'grid=', field.grid_shape,
            'sigma=', field.gaussian_bandwidth,
            'sample_sd=', field.metadata.get('sample_sd_reference'),
            'budget_limited=', field.metadata.get('adaptive_smearing_budget_limited'),
        )


if __name__ == '__main__':
    main()
