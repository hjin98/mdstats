"""S4 consumer integration and automatic-policy acceptance tests."""

from __future__ import annotations

import numpy as np
from mdstats import (
    AtomisticFrameCollection,
    DistanceConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    HystereticDistanceConnectivity,
    NeighborSearchOptions,
    PairCutoffRegistry,
    ReferenceDistanceConnectivity,
    compute_atomic_connectivity,
    compute_bond_angle_distribution,
    compute_coordination_distribution,
    compute_pair_rdf,
)
from mdstats.analysis._neighbors import CellListOptions


def structured_trajectory(
    *, n_groups: int = 18, n_frames: int = 5, variable_cell: bool = False
) -> AtomisticFrameCollection:
    side = int(np.ceil(n_groups ** (1.0 / 3.0)))
    bases: list[np.ndarray] = []
    for i in range(side):
        for j in range(side):
            for k in range(side):
                bases.append(np.array([2.0 + 3.4 * i, 2.0 + 3.4 * j, 2.0 + 3.4 * k]))
                if len(bases) == n_groups:
                    break
            if len(bases) == n_groups:
                break
        if len(bases) == n_groups:
            break
    positions = []
    numbers = []
    for base in bases:
        positions.extend([base, base + [0.8, 0.0, 0.0], base + [0.0, 0.8, 0.0]])
        numbers.extend([14, 8, 8])
    positions0 = np.asarray(positions, dtype=float)
    length = 4.0 + 3.4 * side
    base_cell = np.diag([length, length, length])
    base_fractional = positions0 @ np.linalg.inv(base_cell)
    cells = []
    fractional = []
    rng = np.random.default_rng(20260713 + n_groups)
    cumulative = np.zeros_like(base_fractional)
    for frame in range(n_frames):
        if variable_cell:
            strain = np.array(
                [
                    [1.0 + 0.002 * frame, 0.0, 0.0],
                    [0.001 * frame, 1.0 - 0.001 * frame, 0.0],
                    [0.0, 0.0005 * frame, 1.0 + 0.001 * frame],
                ]
            )
            cell = base_cell @ strain
        else:
            cell = base_cell.copy()
        if frame:
            cumulative += rng.normal(scale=2.0e-4, size=cumulative.shape)
        cells.append(cell)
        fractional.append(base_fractional + cumulative)
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.asarray(numbers, dtype=np.int32),
        masses=np.ones(len(numbers)),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.arange(n_frames, dtype=float),
        cells=np.asarray(cells),
        origins=np.zeros((n_frames, 3)),
        fractional_positions=np.asarray(fractional),
        velocities=np.zeros((n_frames, len(numbers), 3)),
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("s4-structured",),
            velocity_source="native",
            coordinate_normalization="minimum_image_inferred",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def random_identical_trajectory(
    n_atoms: int, n_frames: int = 2
) -> AtomisticFrameCollection:
    rng = np.random.default_rng(9000 + n_atoms)
    length = float((n_atoms / 0.025) ** (1.0 / 3.0))
    cell = np.diag([length, length, length])
    fractional = rng.random((n_frames, n_atoms, 3))
    fractional[1:] = fractional[0] + rng.normal(
        scale=1.0e-4, size=(n_frames - 1, n_atoms, 3)
    )
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.ones(n_atoms, dtype=np.int32),
        masses=np.ones(n_atoms),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.arange(n_frames, dtype=float),
        cells=np.repeat(cell[None, :, :], n_frames, axis=0),
        origins=np.zeros((n_frames, 3)),
        fractional_positions=fractional,
        velocities=np.zeros((n_frames, n_atoms, 3)),
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("s4-random",),
            velocity_source="native",
            coordinate_normalization="minimum_image_inferred",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def independent_ensemble(
    n_atoms: int = 80,
    n_frames: int = 6,
    *,
    variable_cell: bool = False,
    close_frames: bool = False,
) -> AtomisticFrameCollection:
    rng = np.random.default_rng(11200 + n_atoms + n_frames)
    length = float((n_atoms / 0.025) ** (1.0 / 3.0))
    base_cell = np.diag([length, length, length])
    cells = []
    fractional = []
    base = rng.random((n_atoms, 3))
    for frame in range(n_frames):
        if variable_cell:
            scale = 1.0 + 0.01 * frame
            cell = base_cell @ np.diag([scale, 1.0 / scale, 1.0])
        else:
            cell = base_cell.copy()
        cells.append(cell)
        if close_frames:
            positions = np.mod(base + rng.normal(scale=1.0e-4, size=base.shape), 1.0)
        else:
            positions = rng.random((n_atoms, 3))
        fractional.append(positions)
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.ENSEMBLE,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.ones(n_atoms, dtype=np.int32),
        masses=np.ones(n_atoms),
        pbc=np.ones(3, dtype=bool),
        steps=None,
        times=None,
        cells=np.asarray(cells),
        origins=np.zeros((n_frames, 3)),
        fractional_positions=np.asarray(fractional),
        velocities=None,
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("s4-ensemble",),
            velocity_source="unavailable",
            coordinate_normalization="independent_frame_wrapping",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def translated_ensemble() -> AtomisticFrameCollection:
    rng = np.random.default_rng(12031)
    n_atoms = 80
    n_frames = 5
    length = float((n_atoms / 0.025) ** (1.0 / 3.0))
    cell = np.diag([length, length, length])
    base = rng.uniform(0.2, 0.7, size=(n_atoms, 3))
    cartesian_shifts = np.asarray([0.0, 0.35, 0.40, 0.75, 1.10])
    fractional = np.asarray(
        [np.mod(base + [shift / length, 0.0, 0.0], 1.0) for shift in cartesian_shifts]
    )
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.ENSEMBLE,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.ones(n_atoms, dtype=np.int32),
        masses=np.ones(n_atoms),
        pbc=np.ones(3, dtype=bool),
        steps=None,
        times=None,
        cells=np.repeat(cell[None, :, :], n_frames, axis=0),
        origins=np.zeros((n_frames, 3)),
        fractional_positions=fractional,
        velocities=None,
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("s4-translated-ensemble",),
            velocity_source="unavailable",
            coordinate_normalization="independent_frame_wrapping",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def modes() -> tuple[
    NeighborSearchOptions, NeighborSearchOptions, NeighborSearchOptions
]:
    return (
        NeighborSearchOptions(backend="dense"),
        NeighborSearchOptions(backend="cell_list", cache_mode="none"),
        NeighborSearchOptions(
            backend="cell_list", cache_mode="verlet", deformation_aware=True, skin=0.4
        ),
    )


def test_dense_override_resolves_cache_without_mutating_requested_mode() -> None:
    options = NeighborSearchOptions(backend="dense")
    assert options.backend == "dense"
    assert options.cache_mode == "auto"

    collection = random_identical_trajectory(32)
    result = compute_coordination_distribution(
        collection,
        "H",
        "H",
        cutoff=1.5,
        neighbor_search_options=options,
    )
    diagnostics = result.metadata["neighbor_search"]
    assert diagnostics["cache_mode_requested"] == "auto"
    assert diagnostics["cache_mode_selected"] == "none"
    assert diagnostics["cache_resolution_reasons"] == {"backend_not_cell_list": 1}


def test_auto_policy_uses_measured_pair_work_threshold() -> None:
    small = random_identical_trajectory(32)
    small_result = compute_coordination_distribution(
        small,
        "H",
        "H",
        cutoff=1.5,
        neighbor_search_options=NeighborSearchOptions(
            backend="auto", cache_mode="none", dense_pair_threshold=32_768
        ),
    )
    assert small_result.metadata["neighbor_search"]["backend_selected"] == "dense"

    large = random_identical_trajectory(200)
    large_result = compute_coordination_distribution(
        large,
        "H",
        "H",
        cutoff=1.5,
        neighbor_search_options=NeighborSearchOptions(
            backend="auto", cache_mode="none", dense_pair_threshold=32_768
        ),
    )
    assert large_result.metadata["neighbor_search"]["backend_selected"] == "cell_list"


def test_rdf_dense_cell_list_and_cached_outputs_are_identical() -> None:
    collection = structured_trajectory(variable_cell=True)
    results = [
        compute_pair_rdf(
            collection,
            "Si",
            "O",
            r_max=1.5,
            n_bins=60,
            neighbor_search_options=mode,
        )
        for mode in modes()
    ]
    for result in results[1:]:
        np.testing.assert_array_equal(result.counts, results[0].counts)
        np.testing.assert_allclose(result.g_r, results[0].g_r, rtol=0.0, atol=0.0)
        np.testing.assert_allclose(
            result.coordination_number,
            results[0].coordination_number,
            rtol=0.0,
            atol=0.0,
        )
    diagnostics = results[-1].metadata["neighbor_search"]
    assert diagnostics["cache_mode_selected"] == "verlet"
    assert diagnostics["cell_list_rebuild_count"] >= 1
    assert len(diagnostics["minimum_safety_margin_by_rebuild_interval"]) >= 1


def test_coordination_dense_cell_list_and_cached_outputs_are_identical() -> None:
    collection = structured_trajectory(variable_cell=True)
    results = [
        compute_coordination_distribution(
            collection,
            "Si",
            "O",
            cutoff=1.3,
            neighbor_search_options=mode,
        )
        for mode in modes()
    ]
    for result in results[1:]:
        np.testing.assert_array_equal(
            result.per_atom_per_frame, results[0].per_atom_per_frame
        )
        np.testing.assert_array_equal(result.counts, results[0].counts)
        np.testing.assert_allclose(result.probabilities, results[0].probabilities)


def test_bond_angle_dense_cell_list_and_cached_outputs_are_identical() -> None:
    collection = structured_trajectory(variable_cell=True)
    registry = PairCutoffRegistry.from_mapping({("Si", "O"): 1.3})
    results = [
        compute_bond_angle_distribution(
            collection,
            triplet=("O", "Si", "O"),
            cutoffs=registry,
            bins=90,
            per_frame=True,
            return_angles=True,
            neighbor_search_options=mode,
        )
        for mode in modes()
    ]
    for result in results[1:]:
        np.testing.assert_array_equal(result.counts, results[0].counts)
        np.testing.assert_array_equal(
            result.per_frame_counts, results[0].per_frame_counts
        )
        np.testing.assert_allclose(
            result.raw_angles, results[0].raw_angles, rtol=0.0, atol=1e-12
        )


def test_connectivity_distance_hysteretic_and_reference_are_backend_neutral() -> None:
    collection = structured_trajectory(variable_cell=True)
    outer = PairCutoffRegistry.from_mapping({("Si", "O"): 1.3})
    inner = PairCutoffRegistry.from_mapping({("Si", "O"): 1.0})
    definitions = (
        DistanceConnectivity(outer),
        HystereticDistanceConnectivity(
            formation_cutoffs=inner,
            breaking_cutoffs=outer,
            initial_state="formation_cutoff",
        ),
        ReferenceDistanceConnectivity(
            reference_frame=0,
            discovery_cutoffs=inner,
            formation_cutoffs=inner,
            retention_cutoffs=outer,
        ),
    )
    for definition in definitions:
        dense = compute_atomic_connectivity(
            collection,
            definition,
            neighbor_search_options=NeighborSearchOptions(backend="dense"),
        )
        cached = compute_atomic_connectivity(
            collection,
            definition,
            neighbor_search_options=NeighborSearchOptions(
                backend="cell_list",
                cache_mode="verlet",
                deformation_aware=True,
                skin=0.4,
            ),
        )
        assert dense.frame_state_ids.tolist() == cached.frame_state_ids.tolist()
        assert [state.digest for state in dense.states] == [
            state.digest for state in cached.states
        ]


def test_single_frame_preserves_stateless_cell_list_behavior() -> None:
    collection = random_identical_trajectory(200, n_frames=1)
    result = compute_coordination_distribution(
        collection,
        "H",
        "H",
        cutoff=1.5,
        neighbor_search_options=NeighborSearchOptions(
            backend="cell_list",
            cache_mode="verlet",
            minimum_cache_frames=2,
        ),
    )
    diagnostics = result.metadata["neighbor_search"]
    assert diagnostics["backend_selected"] == "cell_list"
    assert diagnostics["cache_mode_selected"] == "none"
    assert diagnostics["cache_statistics"] is None
    assert diagnostics["median_frames_per_rebuild"] == 0.0


def test_unsafe_verlet_list_radius_falls_back_to_stateless_cell_list() -> None:
    collection = random_identical_trajectory(80)
    safe = 0.5 * float(collection.cells[0, 0, 0])
    result = compute_coordination_distribution(
        collection,
        "H",
        "H",
        cutoff=safe - 0.1,
        neighbor_search_options=NeighborSearchOptions(
            backend="cell_list",
            cache_mode="verlet",
            skin=0.5,
            dense_pair_threshold=1,
        ),
    )
    diagnostics = result.metadata["neighbor_search"]
    assert diagnostics["backend_selected"] == "cell_list"
    assert diagnostics["cache_mode_selected"] == "none"
    assert diagnostics["fallback_events"] == {
        "verlet_list_radius_unsafe_to_stateless": 1
    }


def test_auto_cell_list_complexity_falls_back_to_dense() -> None:
    collection = random_identical_trajectory(80, n_frames=1)
    result = compute_coordination_distribution(
        collection,
        "H",
        "H",
        cutoff=1.5,
        neighbor_search_options=NeighborSearchOptions(
            backend="auto",
            cache_mode="none",
            dense_pair_threshold=1,
            fallback_to_dense=True,
            cell_list_options=CellListOptions(max_stencil_candidates=1),
        ),
    )
    diagnostics = result.metadata["neighbor_search"]
    assert diagnostics["backend_selected"] == "dense"
    assert diagnostics["fallback_events"] == {"cell_list_complexity_to_dense": 1}


def test_cache_interval_diagnostics_are_deterministic() -> None:
    collection = structured_trajectory(variable_cell=True)
    options = NeighborSearchOptions(
        backend="cell_list", cache_mode="verlet", deformation_aware=True, skin=0.4
    )
    first = compute_coordination_distribution(
        collection, "Si", "O", cutoff=1.3, neighbor_search_options=options
    ).metadata["neighbor_search"]
    second = compute_coordination_distribution(
        collection, "Si", "O", cutoff=1.3, neighbor_search_options=options
    ).metadata["neighbor_search"]
    assert first == second


def test_auto_cache_policy_is_semantics_aware() -> None:
    trajectory = random_identical_trajectory(80, n_frames=3)
    trajectory_result = compute_coordination_distribution(
        trajectory,
        "H",
        "H",
        cutoff=1.5,
        neighbor_search_options=NeighborSearchOptions(backend="cell_list"),
    )
    trajectory_diagnostics = trajectory_result.metadata["neighbor_search"]
    assert trajectory_diagnostics["frame_semantics"] == "trajectory"
    assert trajectory_diagnostics["cache_mode_requested"] == "auto"
    assert trajectory_diagnostics["cache_mode_selected"] == "verlet"
    assert trajectory_diagnostics["cache_resolution_reasons"] == {
        "trajectory_cache_eligible": 1
    }

    ensemble = independent_ensemble(n_frames=3)
    ensemble_result = compute_coordination_distribution(
        ensemble,
        "H",
        "H",
        cutoff=1.5,
        neighbor_search_options=NeighborSearchOptions(backend="cell_list"),
    )
    ensemble_diagnostics = ensemble_result.metadata["neighbor_search"]
    assert ensemble_diagnostics["frame_semantics"] == "ensemble"
    assert ensemble_diagnostics["cache_mode_requested"] == "auto"
    assert ensemble_diagnostics["cache_mode_selected"] == "none"
    assert ensemble_diagnostics["cache_resolution_reasons"] == {
        "ensemble_default_stateless": 1
    }
    assert ensemble_diagnostics["cache_statistics"] is None
    assert ensemble_diagnostics["backend_counts"] == {"cell_list": 3}


def test_single_selected_frame_auto_policy_is_stateless() -> None:
    collection = random_identical_trajectory(80, n_frames=3)
    result = compute_coordination_distribution(
        collection,
        "H",
        "H",
        cutoff=1.5,
        frame_start=1,
        frame_stop=2,
        neighbor_search_options=NeighborSearchOptions(backend="cell_list"),
    )
    diagnostics = result.metadata["neighbor_search"]
    assert diagnostics["frame_semantics"] == "single_frame"
    assert diagnostics["cache_mode_selected"] == "none"
    assert diagnostics["cache_resolution_reasons"] == {"single_frame_stateless": 1}


def test_explicit_verlet_can_reuse_close_fixed_cell_ensemble() -> None:
    collection = independent_ensemble(n_frames=4, close_frames=True)
    result = compute_coordination_distribution(
        collection,
        "H",
        "H",
        cutoff=1.5,
        neighbor_search_options=NeighborSearchOptions(
            backend="cell_list", cache_mode="verlet", skin=0.5
        ),
    )
    diagnostics = result.metadata["neighbor_search"]
    assert diagnostics["cache_mode_selected"] == "verlet"
    assert diagnostics["cache_resolution_reasons"] == {"explicit_verlet_request": 1}
    assert diagnostics["cell_list_rebuild_count"] == 1
    assert diagnostics["cache_reuse_frame_count"] == 3
    assert not diagnostics["cache_disabled_during_run"]


def test_variable_cell_ensemble_explicit_verlet_rebuilds_conservatively() -> None:
    collection = independent_ensemble(n_frames=3, variable_cell=True)
    result = compute_coordination_distribution(
        collection,
        "H",
        "H",
        cutoff=1.5,
        neighbor_search_options=NeighborSearchOptions(
            backend="cell_list",
            cache_mode="verlet",
            max_consecutive_zero_reuse_rebuilds=10,
        ),
    )
    diagnostics = result.metadata["neighbor_search"]
    assert diagnostics["cache_mode_selected"] == "verlet"
    assert diagnostics["cell_list_rebuild_count"] == 3
    assert diagnostics["cache_reuse_frame_count"] == 0
    assert diagnostics["rebuild_reason_counts"] == {
        "fractional_unwrapping_unavailable": 2,
        "initial_build": 1,
    }


def test_repeated_zero_reuse_disables_cache_for_remaining_ensemble_frames() -> None:
    collection = independent_ensemble(n_frames=7)
    result = compute_coordination_distribution(
        collection,
        "H",
        "H",
        cutoff=1.5,
        neighbor_search_options=NeighborSearchOptions(
            backend="cell_list",
            cache_mode="verlet",
            skin=0.4,
            max_consecutive_zero_reuse_rebuilds=3,
        ),
    )
    diagnostics = result.metadata["neighbor_search"]
    request = diagnostics["requests"][0]
    assert diagnostics["cache_mode_selected"] == "verlet_then_none"
    assert diagnostics["cache_disabled_during_run"]
    assert diagnostics["cache_disable_reasons"] == {"repeated_zero_reuse": 1}
    assert diagnostics["fallback_events"] == {"repeated_zero_reuse_to_stateless": 1}
    assert request["consecutive_zero_reuse_rebuilds"] == 3
    assert diagnostics["backend_counts"] == {
        "cell_list": 3,
        "verlet_cache": 4,
    }


def test_successful_reuse_resets_zero_reuse_counter() -> None:
    collection = translated_ensemble()
    result = compute_coordination_distribution(
        collection,
        "H",
        "H",
        cutoff=1.5,
        neighbor_search_options=NeighborSearchOptions(
            backend="cell_list",
            cache_mode="verlet",
            skin=0.5,
            max_consecutive_zero_reuse_rebuilds=2,
        ),
    )
    diagnostics = result.metadata["neighbor_search"]
    request = diagnostics["requests"][0]
    assert diagnostics["cache_reuse_frame_count"] >= 1
    assert not diagnostics["cache_disabled_during_run"]
    assert request["consecutive_zero_reuse_rebuilds"] < 2


def test_all_distance_consumers_share_ensemble_auto_stateless_policy() -> None:
    trajectory = structured_trajectory(n_groups=8, n_frames=3, variable_cell=True)
    collection = AtomisticFrameCollection(
        frame_semantics=FrameSemantics.ENSEMBLE,
        frame_ids=trajectory.frame_ids.copy(),
        atomic_numbers=trajectory.atomic_numbers.copy(),
        masses=trajectory.masses.copy(),
        pbc=trajectory.pbc.copy(),
        steps=trajectory.steps.copy() if trajectory.steps is not None else None,
        times=trajectory.times.copy() if trajectory.times is not None else None,
        cells=trajectory.cells.copy(),
        origins=trajectory.origins.copy(),
        fractional_positions=np.mod(trajectory.fractional_positions, 1.0),
        velocities=None,
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("s4-structured-ensemble",),
            velocity_source="discarded_for_ensemble",
            coordinate_normalization="independent_frame_wrapping",
            stress_source=None,
            units_source="synthetic",
        ),
    )
    auto = NeighborSearchOptions(backend="cell_list")
    stateless = NeighborSearchOptions(backend="cell_list", cache_mode="none")

    rdf_auto = compute_pair_rdf(
        collection,
        "Si",
        "O",
        r_max=1.5,
        n_bins=40,
        neighbor_search_options=auto,
    )
    rdf_none = compute_pair_rdf(
        collection,
        "Si",
        "O",
        r_max=1.5,
        n_bins=40,
        neighbor_search_options=stateless,
    )
    np.testing.assert_array_equal(rdf_auto.counts, rdf_none.counts)

    coordination_auto = compute_coordination_distribution(
        collection,
        "Si",
        "O",
        cutoff=1.3,
        neighbor_search_options=auto,
    )
    coordination_none = compute_coordination_distribution(
        collection,
        "Si",
        "O",
        cutoff=1.3,
        neighbor_search_options=stateless,
    )
    np.testing.assert_array_equal(
        coordination_auto.per_atom_per_frame,
        coordination_none.per_atom_per_frame,
    )

    registry = PairCutoffRegistry.from_mapping({("Si", "O"): 1.3})
    angle_auto = compute_bond_angle_distribution(
        collection,
        triplet=("O", "Si", "O"),
        cutoffs=registry,
        bins=60,
        neighbor_search_options=auto,
    )
    angle_none = compute_bond_angle_distribution(
        collection,
        triplet=("O", "Si", "O"),
        cutoffs=registry,
        bins=60,
        neighbor_search_options=stateless,
    )
    np.testing.assert_array_equal(angle_auto.counts, angle_none.counts)

    connectivity_auto = compute_atomic_connectivity(
        collection,
        DistanceConnectivity(registry),
        neighbor_search_options=auto,
    )
    connectivity_none = compute_atomic_connectivity(
        collection,
        DistanceConnectivity(registry),
        neighbor_search_options=stateless,
    )
    assert [state.digest for state in connectivity_auto.states] == [
        state.digest for state in connectivity_none.states
    ]

    for result in (rdf_auto, coordination_auto, angle_auto, connectivity_auto):
        diagnostics = result.metadata["neighbor_search"]
        assert diagnostics["frame_semantics"] == "ensemble"
        assert diagnostics["cache_mode_selected"] == "none"
        assert diagnostics["cache_statistics"] is None
