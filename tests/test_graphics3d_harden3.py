from __future__ import annotations

import numpy as np
from ase.geometry import find_mic

from mdstats.analysis._neighbors import minimum_image_geometry
from mdstats.analysis.density.diagnostics import (
    PeriodicMeanPolicy,
    periodic_frechet_mean_diagnostic,
)


def test_general_mic_tracks_integer_shift_through_reduced_basis() -> None:
    # Deliberately ill-conditioned lattice/vector magnitudes that make the old
    # post-hoc inv(cell)+round reconstruction lose enough digits to reject an
    # otherwise valid ASE general MIC.  HARDEN3 carries the integer unimodular
    # reduction coefficients directly instead.
    cell = np.asarray(
        [
            [10.0, 0.0, 0.0],
            [9.999999081224159, 5.116449174399241e-05, 0.0],
            [-3.6667620654764965, 5.300585973057492, 1.5529062110592453e-05],
        ],
        dtype=np.float64,
    )
    raw = np.asarray(
        [
            [1228.3673423796624, 1105.9551899477349, -956.0397208860936],
            [1131.5585700312968, 1191.2792066871687, 753.5223471604891],
            [-1363.7429720417267, 492.03974381873013, -73.06001742295476],
            [1510.35257006504, 526.5587967094705, -2003.003376865705],
        ],
        dtype=np.float64,
    )
    vectors, distances, shifts = minimum_image_geometry(raw, cell=cell, pbc=[1, 1, 1])
    ase_vectors, ase_distances = find_mic(raw, cell, pbc=[1, 1, 1])
    assert np.allclose(vectors, ase_vectors, rtol=1.0e-11, atol=1.0e-10)
    assert np.allclose(distances, ase_distances, rtol=1.0e-11, atol=1.0e-10)
    assert np.allclose(raw + shifts @ cell, vectors, rtol=2.0e-12, atol=3.0e-8)


def test_certified_periodic_mean_matches_authoritative_multistart() -> None:
    rng = np.random.default_rng(44)
    cell = np.asarray(
        [[18.0, 0.0, 0.0], [7.0, 15.0, 0.0], [5.0, 3.0, 14.0]],
        dtype=np.float64,
    )
    samples = np.mod(
        np.asarray([0.22, 0.31, 0.43])[None, :] + rng.normal(0.0, 0.004, size=(256, 3)),
        1.0,
    )
    weights = np.linspace(1.0, 2.0, samples.shape[0])
    exact = periodic_frechet_mean_diagnostic(
        samples, weights=weights, cell=cell, pbc=[1, 1, 1]
    )
    fast = periodic_frechet_mean_diagnostic(
        samples,
        weights=weights,
        cell=cell,
        pbc=[1, 1, 1],
        policy=PeriodicMeanPolicy(certified_fast_path=True),
    )
    assert fast.start_count == 1
    assert fast.candidate_solution_count == 1
    assert not fast.mean_ambiguity_detected
    assert np.allclose(fast.mean_cartesian, exact.mean_cartesian, rtol=0.0, atol=2.0e-11)
    assert np.isclose(fast.objective_value, exact.objective_value, rtol=1.0e-12, atol=1.0e-12)


def test_certified_periodic_mean_falls_back_for_wide_distribution() -> None:
    cell = np.diag([10.0, 10.0, 10.0])
    samples = np.asarray(
        [
            [0.10, 0.25, 0.25],
            [0.12, 0.25, 0.25],
            [0.58, 0.25, 0.25],
            [0.60, 0.25, 0.25],
        ],
        dtype=np.float64,
    )
    result = periodic_frechet_mean_diagnostic(
        samples,
        weights=np.ones(4),
        cell=cell,
        pbc=[1, 1, 1],
        policy=PeriodicMeanPolicy(certified_fast_path=True),
    )
    # The sample cloud spans more than the strong-convexity certificate, so the
    # original exact multi-start machinery remains authoritative.
    assert result.start_count > 1


def _small_star_trajectory():
    from mdstats import AtomisticFrameCollection, FrameCollectionProvenance, FrameSemantics

    positions = np.asarray(
        [
            [[1.62 + 0.01 * t, 0.0, 0.0], [-1.72, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 2.42 + 0.02 * t, 0.0]]
            for t in range(5)
        ],
        dtype=np.float64,
    )
    cells = np.repeat((np.eye(3) * 12.0)[None, :, :], positions.shape[0], axis=0)
    fractional = np.einsum("tni,tij->tnj", positions, np.linalg.inv(cells))
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(positions.shape[0], dtype=np.int64),
        atomic_numbers=np.asarray([14, 13, 8, 11], dtype=np.int32),
        masses=np.ones(4, dtype=np.float64),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(positions.shape[0], dtype=np.int64),
        times=np.arange(positions.shape[0], dtype=np.float64),
        cells=cells,
        origins=np.zeros((positions.shape[0], 3), dtype=np.float64),
        fractional_positions=fractional,
        velocities=np.zeros_like(positions),
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("synthetic",),
            velocity_source="native",
            coordinate_normalization="minimum_image_inferred",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def _small_star_definitions():
    from mdstats import HystereticDistanceConnectivity, PairCutoffRegistry

    full = HystereticDistanceConnectivity(
        formation_cutoffs=PairCutoffRegistry.from_mapping(
            {("Si", "O"): 1.9, ("Al", "O"): 2.0, ("Na", "O"): 2.7}
        ),
        breaking_cutoffs=PairCutoffRegistry.from_mapping(
            {("Si", "O"): 2.2, ("Al", "O"): 2.3, ("Na", "O"): 3.0}
        ),
    )
    framework = HystereticDistanceConnectivity(
        formation_cutoffs=PairCutoffRegistry.from_mapping(
            {("Si", "O"): 1.9, ("Al", "O"): 2.0}
        ),
        breaking_cutoffs=PairCutoffRegistry.from_mapping(
            {("Si", "O"): 2.2, ("Al", "O"): 2.3}
        ),
    )
    return full, framework


def test_exact_framework_projection_matches_direct_hysteretic_result() -> None:
    from mdstats import compute_atomic_connectivity, project_atomic_connectivity_subset

    trajectory = _small_star_trajectory()
    full_definition, framework_definition = _small_star_definitions()
    full = compute_atomic_connectivity(trajectory, full_definition)
    projected = project_atomic_connectivity_subset(trajectory, full, framework_definition)
    direct = compute_atomic_connectivity(trajectory, framework_definition)

    np.testing.assert_array_equal(projected.frame_state_ids, direct.frame_state_ids)
    assert [state.digest for state in projected.states] == [state.digest for state in direct.states]
    assert projected.transitions == direct.transitions


def test_star_batch_neighbor_enumeration_is_exact(monkeypatch) -> None:
    import mdstats.analysis.atomic_connectivity as connectivity_module
    from mdstats import NeighborSearchOptions, compute_atomic_connectivity

    trajectory = _small_star_trajectory()
    full_definition, _framework_definition = _small_star_definitions()
    options = NeighborSearchOptions(backend="cell_list", cache_mode="none")
    optimized = compute_atomic_connectivity(
        trajectory, full_definition, neighbor_search_options=options
    )
    monkeypatch.setattr(connectivity_module, "_nested_star_batch", lambda *args, **kwargs: None)
    reference = compute_atomic_connectivity(
        trajectory, full_definition, neighbor_search_options=options
    )

    np.testing.assert_array_equal(optimized.frame_state_ids, reference.frame_state_ids)
    assert [state.digest for state in optimized.states] == [state.digest for state in reference.states]
    assert optimized.transitions == reference.transitions


def test_fixed_periodic_cell_list_plan_is_reused_across_frames() -> None:
    from mdstats import NeighborSearchOptions, compute_atomic_connectivity
    from mdstats.analysis._cell_list import _cached_periodic_cell_list_plan

    trajectory = _small_star_trajectory()
    full_definition, _framework_definition = _small_star_definitions()
    _cached_periodic_cell_list_plan.cache_clear()
    compute_atomic_connectivity(
        trajectory,
        full_definition,
        neighbor_search_options=NeighborSearchOptions(backend="cell_list", cache_mode="none"),
    )
    info = _cached_periodic_cell_list_plan.cache_info()
    assert info.misses == 1
    assert info.hits >= trajectory.n_frames - 1


def test_canonical_state_reuse_cache_is_bounded_for_fragmented_trajectory() -> None:
    import mdstats.analysis.atomic_connectivity as connectivity_module
    from mdstats import ConnectivityScope
    from mdstats.analysis.atomic_connectivity import AtomicEdgeKey

    trajectory = _small_star_trajectory()
    resolved = connectivity_module._resolve_connectivity_scope(
        trajectory, ConnectivityScope.all()
    )
    cache = {}
    for winding in range(connectivity_module._STATE_BUILD_CACHE_MAX_ENTRIES + 37):
        connectivity_module._build_state(
            trajectory,
            resolved,
            (
                AtomicEdgeKey(0, 1, (winding, 0, 0)),
                AtomicEdgeKey(0, 2, (0, 0, 0)),
                AtomicEdgeKey(1, 2, (0, 0, 0)),
            ),
            state_cache=cache,
        )
    assert len(cache) == connectivity_module._STATE_BUILD_CACHE_MAX_ENTRIES
