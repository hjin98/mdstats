"""LD2-B periodic sparse density mesh tests."""

from __future__ import annotations


import numpy as np
import pytest
from scipy.spatial import cKDTree

from mdstats import (
    GAUSSIAN_SIGMA_BROADENING,
    DensitySourceProvenance,
    PeriodicBlockScalarField3D,
    PeriodicWeightedSamples3D,
    identify_sparse_mesh_candidate_cells,
    label_periodic_cell_components,
    pack_sparse_reference_blocks,
    prepare_sparse_canonical_density_reference,
    prepare_sparse_density_mesh,
)
from mdstats.plotting.atomic_density import PeriodicScalarField3D, density_mesh_arrays
from mdstats.plotting.density_sparse_mesh import _require_sparse_mesh_face_limit
from mdstats.plotting.graph_errors import GraphComplexityError


def sparse_field(
    positions: np.ndarray,
    *,
    shape: tuple[int, int, int] = (24, 24, 24),
    cell: np.ndarray | None = None,
    sigma: float = 0.35,
    block_shape: tuple[int, int, int] = (8, 8, 8),
) -> PeriodicBlockScalarField3D:
    if cell is None:
        cell = np.eye(3) * 6.0
    positions = np.asarray(positions, dtype=np.float64)
    weights = np.full(positions.shape[0], 1.0 / positions.shape[0])
    batch = PeriodicWeightedSamples3D(
        fractional_positions=positions,
        weights=weights,
        source_provenance=DensitySourceProvenance(
            source_kind="atomic_occupancy", atom_indices=tuple(range(positions.shape[0]))
        ),
        total_measure=1.0,
        measure_kind="occupancy",
        measure_units="count",
    )
    reference = prepare_sparse_canonical_density_reference(
        batch,
        grid_shape=shape,
        display_cell=np.asarray(cell, dtype=np.float64),
        gaussian_bandwidth=sigma,
        field_key="atomic-density-0",
        label="density",
        physical_units="angstrom^-3",
        broadening_metric=GAUSSIAN_SIGMA_BROADENING,
        max_workspace_bytes=500_000_000,
    )
    return pack_sparse_reference_blocks(
        reference,
        block_shape=block_shape,
        max_stored_block_values=5_000_000,
        max_planning_bytes=500_000_000,
    )


def dense_adapter(field: PeriodicBlockScalarField3D) -> PeriodicScalarField3D:
    return PeriodicScalarField3D(
        field_key=field.field_key,
        label=field.label,
        values=field.to_dense_values(max_nodes=10_000_000),
        display_cell=field.display_cell,
        total_measure=field.total_measure,
        selected_atom_indices=(field.selected_atom_indices or field.source_provenance.atom_indices or (0,)),
        gaussian_bandwidth=field.gaussian_bandwidth,
        source_provenance=field.source_provenance,
        metadata=field.metadata,
    )


def assert_vertex_sets_close(first: np.ndarray, second: np.ndarray, tolerance: float) -> None:
    tree_first = cKDTree(first)
    tree_second = cKDTree(second)
    assert float(np.max(tree_first.query(second)[0], initial=0.0)) <= tolerance
    assert float(np.max(tree_second.query(first)[0], initial=0.0)) <= tolerance


def test_candidate_cells_and_nonwinding_component_are_deterministic() -> None:
    field = sparse_field(np.asarray([[0.45, 0.50, 0.55]]))
    first = identify_sparse_mesh_candidate_cells(field, 0.8)
    second = identify_sparse_mesh_candidate_cells(field, 0.8)
    np.testing.assert_array_equal(first.flat_indices, second.flat_indices)
    components = label_periodic_cell_components(first)
    assert len(components) == 1
    assert components[0].winding_vectors == ()
    assert components[0].cell_count == first.candidate_cell_count


@pytest.mark.parametrize(
    "position",
    (
        (0.98, 0.50, 0.50),
        (0.98, 0.98, 0.50),
        (0.98, 0.98, 0.98),
    ),
)
def test_face_edge_corner_crossings_are_periodically_paired(position) -> None:
    cell = np.asarray(
        [[6.0, 0.0, 0.0], [1.5, 5.5, 0.0], [0.7, 0.3, 5.0]],
        dtype=np.float64,
    )
    field = sparse_field(np.asarray([position]), cell=cell)
    surface = prepare_sparse_density_mesh(field, 0.8)
    assert surface.render_kind == "mesh"
    assert surface.mesh is not None
    topology = surface.mesh.topology
    assert topology.interior_edge_incidence_failures == 0
    assert topology.unpaired_boundary_edge_count == 0
    assert topology.maximum_boundary_seam_mismatch <= 1.0e-10 * max(
        np.linalg.norm(vector) for vector in cell
    )
    assert topology.maximum_mesh_edge_length <= topology.mesh_edge_length_upper_bound


def test_sparse_and_dense_geometry_agree_for_interior_and_skewed_fields() -> None:
    cases = (
        (np.eye(3) * 6.0, np.asarray([[0.45, 0.50, 0.55]])),
        (
            np.asarray(
                [[6.0, 0.0, 0.0], [3.0, 5.196152423, 0.0], [1.0, 0.4, 5.0]]
            ),
            np.asarray([[0.32, 0.48, 0.61], [0.68, 0.52, 0.39]]),
        ),
    )
    for cell, positions in cases:
        field = sparse_field(positions, cell=cell)
        sparse = prepare_sparse_density_mesh(field, 0.8)
        assert sparse.mesh is not None
        dense_vertices, _dense_faces, _level = density_mesh_arrays(
            dense_adapter(field), 0.8, max_faces=250_000
        )
        assert_vertex_sets_close(
            sparse.mesh.vertices_cartesian,
            dense_vertices,
            tolerance=2.0e-6 * max(np.linalg.norm(vector) for vector in cell),
        )


def test_separated_clouds_form_deterministic_multiple_components() -> None:
    field = sparse_field(np.asarray([[0.20, 0.20, 0.20], [0.70, 0.70, 0.70]]), sigma=0.22)
    candidates = identify_sparse_mesh_candidate_cells(field, 0.75)
    components = label_periodic_cell_components(candidates)
    assert len(components) == 2
    surface = prepare_sparse_density_mesh(field, 0.75)
    assert surface.mesh is not None
    assert surface.mesh.resources.component_count == 2


def test_partial_terminal_blocks_and_block_shape_do_not_change_mesh() -> None:
    positions = np.asarray([[0.92, 0.41, 0.63]])
    first = sparse_field(
        positions, shape=(23, 21, 19), block_shape=(8, 8, 8), sigma=0.28
    )
    second = sparse_field(
        positions, shape=(23, 21, 19), block_shape=(5, 7, 6), sigma=0.28
    )
    assert first.block_valid_masks is not None
    assert second.block_valid_masks is not None
    mesh_first = prepare_sparse_density_mesh(first, 0.8).mesh
    mesh_second = prepare_sparse_density_mesh(second, 0.8).mesh
    assert mesh_first is not None and mesh_second is not None
    np.testing.assert_array_equal(mesh_first.vertices_fractional, mesh_second.vertices_fractional)
    np.testing.assert_array_equal(mesh_first.faces, mesh_second.faces)


def winding_candidates() -> tuple[int, tuple]:
    shape = (4, 2, 2)
    cells = np.asarray([[x, 0, 0] for x in range(shape[0])], dtype=np.int64)
    flat = np.ravel_multi_index((cells[:, 0], cells[:, 1], cells[:, 2]), shape)
    from mdstats import SparseMeshCandidateCells

    record = SparseMeshCandidateCells(
        logical_grid_shape=shape,
        scientific_hdr_threshold=0.5,
        render_level=0.5,
        flat_indices=flat,
        cell_indices=cells,
        adjacent_cell_count=cells.shape[0],
        planning_bytes=cells.nbytes + flat.nbytes,
    )
    components = label_periodic_cell_components(record)
    return len(components), components


def test_winding_detection_is_deterministic() -> None:
    count, components = winding_candidates()
    assert count == 1
    assert components[0].is_winding
    assert (-4, 0, 0) in components[0].winding_vectors
    assert (4, 0, 0) in components[0].winding_vectors


def winding_field() -> PeriodicBlockScalarField3D:
    shape = (8, 8, 8)
    y = np.arange(shape[1], dtype=np.float64)
    profile = 1.0 + 0.8 * np.cos(2.0 * np.pi * y / shape[1])
    values = np.broadcast_to(profile[None, :, None], shape).copy()
    cell = np.eye(3) * 8.0
    total = float(np.sum(values))
    return PeriodicBlockScalarField3D(
        field_key="winding",
        label="winding",
        physical_units="angstrom^-3",
        logical_grid_shape=shape,
        block_shape=shape,
        active_block_indices=np.asarray([[0, 0, 0]], dtype=np.int64),
        block_values=values[None, ...],
        block_valid_masks=None,
        display_cell=cell,
        total_measure=total,
        gaussian_bandwidth=0.0,
        broadening_metric=GAUSSIAN_SIGMA_BROADENING,
        source_provenance=DensitySourceProvenance(
            source_kind="atomic_occupancy", atom_indices=(0,)
        ),
    )


def test_winding_component_uses_dense_then_cloud_fallback() -> None:
    field = winding_field()
    dense = prepare_sparse_density_mesh(
        field, 0.5, max_dense_fallback_nodes=10_000, max_faces=100_000
    )
    assert dense.render_kind == "mesh"
    assert dense.fallback_mode == "dense_canonical"
    assert dense.mesh is not None
    assert dense.mesh.topology.winding_component_count >= 1

    cloud = prepare_sparse_density_mesh(
        field,
        0.5,
        max_dense_fallback_nodes=1,
        allow_cloud_fallback=True,
        cloud_max_points=100,
    )
    assert cloud.render_kind == "node_cloud"
    assert cloud.fallback_mode == "node_cloud"
    assert cloud.cloud is not None

    with pytest.raises(GraphComplexityError, match="winding periodic component"):
        prepare_sparse_density_mesh(
            field,
            0.5,
            max_dense_fallback_nodes=1,
            allow_cloud_fallback=False,
        )


def test_candidate_resource_limit_fails_before_contouring(monkeypatch) -> None:
    field = sparse_field(np.asarray([[0.50, 0.50, 0.50]]))
    called = False

    def forbidden(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("marching cubes was called")

    monkeypatch.setattr("skimage.measure.marching_cubes", forbidden)
    with pytest.raises(GraphComplexityError, match="max_candidate_cells"):
        prepare_sparse_density_mesh(field, 0.8, max_candidate_cells=1)
    assert called is False


def test_sparse_mesh_json_round_trip_is_exact() -> None:
    field = sparse_field(np.asarray([[0.36, 0.48, 0.59]]), sigma=0.30)
    mesh = prepare_sparse_density_mesh(field, 0.8).mesh
    assert mesh is not None
    payload = mesh.to_json_dict()
    restored = type(mesh).from_json_dict(payload)
    np.testing.assert_array_equal(restored.vertices_fractional, mesh.vertices_fractional)
    np.testing.assert_array_equal(restored.vertices_cartesian, mesh.vertices_cartesian)
    np.testing.assert_array_equal(restored.faces, mesh.faces)
    assert restored.resources.to_json_dict() == mesh.resources.to_json_dict()
    assert restored.topology.to_json_dict() == mesh.topology.to_json_dict()
    assert restored.metadata == mesh.metadata


def test_the_face_limit_says_whether_simplification_already_ran() -> None:
    """A terminal shell overshoot has to be distinguishable from a pre-check.

    An operator who sees the limit reported before simplification can still
    lower the mesh resolution; the same number reported *after* simplification
    means the geometry itself does not fit, and the message has to say which
    one happened.
    """

    with pytest.raises(
        GraphComplexityError,
        match=(
            r"Sparse density mesh contains 582375 faces after optional "
            r"simplification, exceeding max_mesh_faces=250000"
        ),
    ):
        _require_sparse_mesh_face_limit(582_375, 250_000, after_simplification=True)

    with pytest.raises(GraphComplexityError) as before:
        _require_sparse_mesh_face_limit(582_375, 250_000, after_simplification=False)
    assert "after optional simplification" not in str(before.value)
    assert "max_mesh_faces=250000" in str(before.value)

    _require_sparse_mesh_face_limit(250_000, 250_000, after_simplification=True)
