"""LD9-V1 bounded contour-tile and tiled-mesh tests."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.spatial import cKDTree

from mdstats import (
    GAUSSIAN_SIGMA_BROADENING,
    ContourTilePlan,
    DensitySourceProvenance,
    MeshExtractionOptions,
    PeriodicWeightedSamples3D,
    TiledMeshExtractionResult,
    identify_sparse_mesh_candidate_cells,
    pack_sparse_reference_blocks,
    plan_contour_render_tiles,
    prepare_sparse_canonical_density_reference,
    prepare_sparse_density_mesh,
)
from mdstats.plotting.density_tiled_mesh import extract_tiled_density_mesh
from mdstats.plotting.graph_errors import GraphAdapterError, GraphComplexityError


def sparse_field(
    positions: np.ndarray,
    *,
    shape: tuple[int, int, int] = (40, 35, 29),
    cell: np.ndarray | None = None,
    sigma: float = 0.32,
    block_shape: tuple[int, int, int] = (8, 8, 8),
):
    if cell is None:
        cell = np.asarray(
            [[7.0, 0.0, 0.0], [1.2, 6.3, 0.0], [0.4, 0.7, 5.8]],
            dtype=np.float64,
        )
    positions = np.asarray(positions, dtype=np.float64)
    batch = PeriodicWeightedSamples3D(
        fractional_positions=positions,
        weights=np.full(positions.shape[0], 1.0 / positions.shape[0]),
        source_provenance=DensitySourceProvenance(
            source_kind="atomic_occupancy",
            atom_indices=tuple(range(positions.shape[0])),
        ),
        total_measure=1.0,
        measure_kind="occupancy",
        measure_units="count",
    )
    reference = prepare_sparse_canonical_density_reference(
        batch,
        grid_shape=shape,
        display_cell=cell,
        gaussian_bandwidth=sigma,
        field_key="ld9-v1-test",
        label="density",
        physical_units="angstrom^-3",
        broadening_metric=GAUSSIAN_SIGMA_BROADENING,
        max_workspace_bytes=500_000_000,
    )
    return pack_sparse_reference_blocks(
        reference,
        block_shape=block_shape,
        max_stored_block_values=10_000_000,
        max_planning_bytes=500_000_000,
    )


def assert_vertex_sets_close(first: np.ndarray, second: np.ndarray, tolerance: float) -> None:
    first_tree = cKDTree(first)
    second_tree = cKDTree(second)
    assert float(np.max(first_tree.query(second)[0], initial=0.0)) <= tolerance
    assert float(np.max(second_tree.query(first)[0], initial=0.0)) <= tolerance


def test_extraction_options_and_tile_plan_round_trip() -> None:
    options = MeshExtractionOptions(
        render_tile_shape=(11, 13, 7),
        max_crossing_cells_per_tile=20_000,
        metadata={"stage": "LD9-V1"},
    )
    assert MeshExtractionOptions.from_json_dict(options.to_json_dict()) == options
    field = sparse_field(np.asarray([[0.98, 0.97, 0.96]]))
    candidates = identify_sparse_mesh_candidate_cells(field, 0.8)
    plan = plan_contour_render_tiles(field, candidates, options=options)
    restored = ContourTilePlan.from_json_dict(plan.to_json_dict())
    assert restored == plan
    assert sum(tile.crossing_cell_count for tile in plan.tiles) == candidates.candidate_cell_count
    assert all(tile.cell_stop[a] <= field.grid_shape[a] for tile in plan.tiles for a in range(3))
    assert any(tile.cell_shape != options.render_tile_shape for tile in plan.tiles)


def test_tiled_extractor_invokes_marching_cubes_once_per_tile(monkeypatch) -> None:
    field = sparse_field(
        np.asarray([[0.24, 0.25, 0.30], [0.74, 0.72, 0.68]]),
        shape=(48, 40, 32),
        sigma=0.25,
    )
    candidates = identify_sparse_mesh_candidate_cells(field, 0.75)
    options = MeshExtractionOptions(render_tile_shape=(12, 10, 8))
    plan = plan_contour_render_tiles(field, candidates, options=options)
    import skimage.measure

    original = skimage.measure.marching_cubes
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(skimage.measure, "marching_cubes", counted)
    extraction = extract_tiled_density_mesh(field, plan, options=options)
    assert calls == plan.tile_count
    assert extraction.marching_cubes_call_count == plan.tile_count
    assert extraction.metadata["raw_tile_geometry_retained_after_tile"] is False
    assert extraction.maximum_tile_transient_bytes <= options.max_transient_mesh_bytes
    assert extraction.raw_face_count <= plan.total_raw_face_upper_bound
    assert extraction.raw_vertex_count <= plan.total_raw_vertex_upper_bound


def test_tiled_and_legacy_cell_geometry_are_equivalent() -> None:
    field = sparse_field(
        np.asarray([[0.34, 0.46, 0.57], [0.68, 0.58, 0.39]]),
        shape=(36, 34, 30),
        sigma=0.28,
    )
    tiled = prepare_sparse_density_mesh(
        field,
        0.8,
        extraction_method="tiled",
        extraction_options=MeshExtractionOptions(render_tile_shape=(12, 11, 9)),
        max_faces=500_000,
    ).mesh
    legacy = prepare_sparse_density_mesh(
        field,
        0.8,
        extraction_method="legacy_cell",
        max_faces=500_000,
    ).mesh
    assert tiled is not None and legacy is not None
    scale = max(np.linalg.norm(vector) for vector in field.display_cell)
    assert_vertex_sets_close(
        tiled.vertices_cartesian,
        legacy.vertices_cartesian,
        tolerance=3.0e-6 * scale,
    )
    assert tiled.topology.interior_edge_incidence_failures == 0
    assert tiled.topology.unpaired_boundary_edge_count == 0
    assert tiled.topology.canonical_boundary_edge_count == legacy.topology.canonical_boundary_edge_count
    assert tiled.metadata["contouring"] == "bounded_tile_lewiner_v1"


@pytest.mark.parametrize(
    "position",
    ((0.99, 0.50, 0.50), (0.99, 0.99, 0.50), (0.99, 0.99, 0.99)),
)
def test_tiled_periodic_face_edge_corner_seams(position) -> None:
    field = sparse_field(np.asarray([position]), shape=(37, 31, 29), sigma=0.30)
    mesh = prepare_sparse_density_mesh(
        field,
        0.8,
        extraction_options=MeshExtractionOptions(render_tile_shape=(10, 9, 8)),
        max_faces=500_000,
    ).mesh
    assert mesh is not None
    assert mesh.topology.interior_edge_incidence_failures == 0
    assert mesh.topology.unpaired_boundary_edge_count == 0
    assert mesh.topology.maximum_boundary_seam_mismatch <= 1.0e-10 * max(
        np.linalg.norm(vector) for vector in field.display_cell
    )


def test_tile_preflight_rejects_raw_limit_before_marching_cubes(monkeypatch) -> None:
    field = sparse_field(np.asarray([[0.50, 0.50, 0.50]]), sigma=0.35)
    candidates = identify_sparse_mesh_candidate_cells(field, 0.8)
    called = False

    def forbidden(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("marching cubes should not be called")

    monkeypatch.setattr("skimage.measure.marching_cubes", forbidden)
    with pytest.raises(GraphComplexityError, match="max_raw_faces_per_tile"):
        plan_contour_render_tiles(
            field,
            candidates,
            options=MeshExtractionOptions(
                render_tile_shape=field.grid_shape,
                max_raw_faces_per_tile=1,
            ),
        )
    assert called is False



def test_tiled_output_is_exactly_independent_of_render_tile_shape() -> None:
    field = sparse_field(
        np.asarray([[0.34, 0.46, 0.57], [0.68, 0.58, 0.39]]),
        shape=(36, 34, 30),
        sigma=0.28,
    )
    meshes = [
        prepare_sparse_density_mesh(
            field,
            0.8,
            extraction_options=MeshExtractionOptions(render_tile_shape=tile_shape),
            max_faces=500_000,
        ).mesh
        for tile_shape in ((8, 8, 8), (17, 13, 11), (36, 34, 30))
    ]
    assert all(mesh is not None for mesh in meshes)
    reference = meshes[0]
    assert reference is not None
    for candidate in meshes[1:]:
        assert candidate is not None
        np.testing.assert_array_equal(
            candidate.vertices_fractional, reference.vertices_fractional
        )
        np.testing.assert_array_equal(candidate.faces, reference.faces)


def test_tiled_extraction_result_json_is_auditable() -> None:
    field = sparse_field(np.asarray([[0.41, 0.52, 0.63]]), shape=(28, 27, 26))
    candidates = identify_sparse_mesh_candidate_cells(field, 0.8)
    options = MeshExtractionOptions(render_tile_shape=(9, 8, 7))
    plan = plan_contour_render_tiles(field, candidates, options=options)
    result = extract_tiled_density_mesh(field, plan, options=options)
    assert isinstance(result, TiledMeshExtractionResult)
    payload = result.to_json_dict(include_geometry=False)
    with pytest.raises(GraphAdapterError, match="requires geometry arrays"):
        TiledMeshExtractionResult.from_json_dict(payload)
    restored = TiledMeshExtractionResult.from_json_dict(
        result.to_json_dict(include_geometry=True)
    )
    np.testing.assert_array_equal(restored.vertices_fractional, result.vertices_fractional)
    np.testing.assert_array_equal(restored.vertices_cartesian, result.vertices_cartesian)
    np.testing.assert_array_equal(restored.faces, result.faces)
    assert restored.tile_reports == result.tile_reports
    assert restored.metadata == result.metadata
    assert payload["tile_count"] == plan.tile_count
    assert payload["marching_cubes_call_count"] == plan.tile_count
    assert payload["estimated_peak_bytes"] == (
        payload["retained_geometry_bytes"] + payload["maximum_tile_transient_bytes"]
    )
    assert sum(item["raw_face_count"] for item in payload["tile_reports"]) == payload["raw_face_count"]


def test_candidate_planning_expands_only_nodes_above_render_level() -> None:
    field = sparse_field(np.asarray([[0.50, 0.50, 0.50]]), shape=(48, 48, 48), sigma=0.30)
    candidates = identify_sparse_mesh_candidate_cells(field, 0.5)
    positive_count = field.storage_summary().nonzero_node_count
    # The adjacent upper bound would be 8 * positive_count in the old tail-wide
    # planner.  The exact high-node planner should be materially smaller.
    assert candidates.adjacent_cell_count < 4 * positive_count


def test_tiled_extractor_retains_point_like_cic_contour() -> None:
    """A near-maximum float32 level must not collapse to a zero-area mesh."""

    field = sparse_field(
        np.asarray([[0.70, 0.50, 0.50], [0.71, 0.50, 0.50]]),
        shape=(64, 64, 64),
        sigma=0.0,
        block_shape=(8, 8, 8),
    )
    tiled = prepare_sparse_density_mesh(
        field,
        0.5,
        extraction_options=MeshExtractionOptions(render_tile_shape=(32, 32, 32)),
        max_faces=500_000,
    ).mesh
    assert tiled is not None
    assert tiled.faces.shape[0] > 0
    assert tiled.render_level < tiled.scientific_hdr_threshold
    assert tiled.topology.interior_edge_incidence_failures == 0
    assert tiled.topology.unpaired_boundary_edge_count == 0


def test_v1_tiled_mesh_json_is_upgraded_to_v2_schema() -> None:
    field = sparse_field(np.asarray([[0.42, 0.48, 0.54]]))
    prepared = prepare_sparse_density_mesh(field, 0.8, max_faces=500_000)
    assert prepared.mesh is not None
    tiled = prepared.mesh.metadata["tiled_extraction"]
    legacy = dict(tiled)
    legacy["schema_version"] = "mdstats.tiled-mesh-extraction.v1"
    legacy["tile_reports"] = [
        {
            key: value
            for key, value in report.items()
            if not key.startswith("local_presimplification_")
        }
        | {"schema_version": "mdstats.tiled-mesh-tile-report.v1"}
        for report in tiled["tile_reports"]
    ]
    # Geometry is not embedded in mesh metadata; use a fresh serialized result.
    field_result = prepare_sparse_density_mesh(
        field,
        0.8,
        max_faces=500_000,
        extraction_options=MeshExtractionOptions(render_tile_shape=(16, 16, 16)),
    )
    assert field_result.mesh is not None
    # Re-extract directly so geometry-bearing JSON is available.
    candidates = identify_sparse_mesh_candidate_cells(field, 0.8)
    plan = plan_contour_render_tiles(
        field,
        candidates,
        options=MeshExtractionOptions(render_tile_shape=(16, 16, 16)),
    )
    extraction = extract_tiled_density_mesh(
        field,
        plan,
        options=MeshExtractionOptions(render_tile_shape=(16, 16, 16)),
    )
    payload = extraction.to_json_dict(include_geometry=True)
    payload["schema_version"] = "mdstats.tiled-mesh-extraction.v1"
    for report in payload["tile_reports"]:
        report["schema_version"] = "mdstats.tiled-mesh-tile-report.v1"
        for name in tuple(report):
            if name.startswith("local_presimplification_"):
                report.pop(name)
    restored = TiledMeshExtractionResult.from_json_dict(payload)
    assert restored.schema_version == "mdstats.tiled-mesh-extraction.v2"
    assert all(
        report.schema_version == "mdstats.tiled-mesh-tile-report.v2"
        for report in restored.tile_reports
    )
