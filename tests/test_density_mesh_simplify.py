"""LD9-V2 periodic fidelity-constrained simplification tests."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("fast_simplification", reason="requires mdstats[interactive]")

from mdstats import (
    GAUSSIAN_SIGMA_BROADENING,
    DensitySourceProvenance,
    MeshExtractionOptions,
    MeshSimplificationOptions,
    PeriodicWeightedSamples3D,
    evaluate_implicit_mesh_fidelity,
    pack_sparse_reference_blocks,
    prepare_sparse_canonical_density_reference,
    prepare_sparse_density_mesh,
    simplify_periodic_density_mesh,
)
from mdstats.plotting.graph_errors import GraphComplexityError


def sparse_field(
    positions: np.ndarray,
    *,
    shape: tuple[int, int, int] = (48, 44, 40),
    sigma: float = 0.30,
):
    cell = np.asarray(
        [[8.0, 0.0, 0.0], [1.0, 7.2, 0.0], [0.4, 0.8, 6.6]],
        dtype=np.float64,
    )
    positions = np.asarray(positions, dtype=np.float64)
    samples = PeriodicWeightedSamples3D(
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
        samples,
        grid_shape=shape,
        display_cell=cell,
        gaussian_bandwidth=sigma,
        field_key="ld9-v2-test",
        label="density",
        physical_units="angstrom^-3",
        broadening_metric=GAUSSIAN_SIGMA_BROADENING,
        max_workspace_bytes=500_000_000,
    )
    return pack_sparse_reference_blocks(
        reference,
        block_shape=(8, 8, 8),
        max_stored_block_values=10_000_000,
        max_planning_bytes=500_000_000,
    )


def policy(target_faces: int | None = None, **updates) -> MeshSimplificationOptions:
    values = dict(
        target_faces=target_faces,
        max_samples=6_000,
        max_surface_error_p99=0.15,
        max_surface_error_max=0.35,
        max_implicit_displacement_p99=0.03,
        max_normal_degradation_degrees=15.0,
        max_relative_scalar_residual_p99=0.20,
        projection_max_step=0.04,
    )
    values.update(updates)
    return MeshSimplificationOptions(**values)


def raw_mesh(field, fraction=0.8):
    result = prepare_sparse_density_mesh(
        field,
        fraction,
        max_faces=500_000,
        max_raw_faces=2_000_000,
        max_raw_vertices=4_000_000,
        max_workspace_bytes=1_000_000_000,
        extraction_options=MeshExtractionOptions(render_tile_shape=(16, 16, 16)),
    )
    assert result.mesh is not None
    return result.mesh


def test_options_json_round_trip() -> None:
    options = policy(1_234, metadata={"stage": "LD9-V2"})
    assert MeshSimplificationOptions.from_json_dict(options.to_json_dict()) == options


def test_component_qem_reduces_closed_interior_mesh_and_preserves_topology() -> None:
    field = sparse_field(np.asarray([[0.28, 0.35, 0.42], [0.72, 0.66, 0.58]]))
    raw = raw_mesh(field)
    target = max(32, int(raw.faces.shape[0] * 0.55))
    result = simplify_periodic_density_mesh(
        field,
        raw.vertices_fractional,
        raw.vertices_cartesian,
        raw.faces,
        contour_level=raw.render_level,
        options=policy(target),
    )
    assert result.output_faces <= target
    assert result.output_faces < result.input_faces
    assert result.fidelity.passed
    assert result.fidelity.reference_topology.euler_characteristic == result.fidelity.candidate_topology.euler_characteristic
    assert result.fidelity.reference_topology.connected_component_count == result.fidelity.candidate_topology.connected_component_count
    assert result.metadata["simplification"] == "periodic_component_qem_v1"


def test_seam_touching_component_uses_periodic_quotient_simplification() -> None:
    field = sparse_field(np.asarray([[0.99, 0.50, 0.50], [0.45, 0.45, 0.45]]))
    raw = raw_mesh(field)
    target = max(64, int(raw.faces.shape[0] * 0.72))
    result = simplify_periodic_density_mesh(
        field,
        raw.vertices_fractional,
        raw.vertices_cartesian,
        raw.faces,
        contour_level=raw.render_level,
        options=policy(target, hard_target=False),
    )
    assert result.output_faces < result.input_faces
    assert result.metadata["simplification"] == "periodic_lifted_component_qem_v1"
    assert result.metadata["periodic_quotient_component_count"] >= 1
    assert result.fidelity.passed


def test_target_below_lifted_periodic_minimum_fails_before_decimation() -> None:
    field = sparse_field(np.asarray([[0.99, 0.50, 0.50]]))
    raw = raw_mesh(field)
    with pytest.raises(GraphComplexityError, match="lifted periodic topology-safe minimum"):
        simplify_periodic_density_mesh(
            field,
            raw.vertices_fractional,
            raw.vertices_cartesian,
            raw.faces,
            contour_level=raw.render_level,
            options=policy(1),
        )


def test_prepare_sparse_density_mesh_integrates_simplification_and_local_reports() -> None:
    field = sparse_field(np.asarray([[0.30, 0.30, 0.30], [0.70, 0.70, 0.70]]))
    raw = raw_mesh(field)
    target = max(32, int(raw.faces.shape[0] * 0.65))
    prepared = prepare_sparse_density_mesh(
        field,
        0.8,
        max_faces=target,
        max_raw_faces=2_000_000,
        max_raw_vertices=4_000_000,
        max_workspace_bytes=1_000_000_000,
        extraction_options=MeshExtractionOptions(render_tile_shape=(48, 44, 40)),
        simplification_options=policy(target, local_target_fraction=0.85),
    )
    assert prepared.mesh is not None
    assert prepared.mesh.faces.shape[0] <= target
    record = prepared.mesh.metadata["mesh_simplification"]
    assert record["fidelity"]["passed"] is True
    tiled = prepared.mesh.metadata["tiled_extraction"]
    assert tiled["metadata"]["local_presimplification"] == "closed_tile_interior_qem_v1"
    assert sum(
        item["local_presimplification_attempted_components"]
        for item in tiled["tile_reports"]
    ) >= 1


def test_implicit_fidelity_detects_large_displacement() -> None:
    field = sparse_field(np.asarray([[0.50, 0.50, 0.50]]))
    raw = raw_mesh(field)
    displaced = np.asarray(raw.vertices_cartesian) + np.asarray([0.5, 0.0, 0.0])
    report = evaluate_implicit_mesh_fidelity(
        field,
        raw.vertices_cartesian,
        raw.faces,
        displaced,
        raw.faces,
        contour_level=raw.render_level,
        options=policy(raw.faces.shape[0], max_surface_error_p99=0.02),
    )
    assert not report.passed
    assert any("surface_error" in item for item in report.violations)


def test_simplification_result_json_round_trip_includes_geometry() -> None:
    field = sparse_field(np.asarray([[0.32, 0.38, 0.44], [0.68, 0.62, 0.56]]))
    raw = raw_mesh(field)
    target = max(32, int(raw.faces.shape[0] * 0.70))
    result = simplify_periodic_density_mesh(
        field,
        raw.vertices_fractional,
        raw.vertices_cartesian,
        raw.faces,
        contour_level=raw.render_level,
        options=policy(target),
    )
    from mdstats import PeriodicMeshSimplificationResult

    restored = PeriodicMeshSimplificationResult.from_json_dict(
        result.to_json_dict(include_geometry=True)
    )
    assert restored.target_faces == result.target_faces
    assert restored.component_reports == result.component_reports
    assert restored.fidelity == result.fidelity
    np.testing.assert_array_equal(restored.faces, result.faces)
    np.testing.assert_allclose(restored.vertices_cartesian, result.vertices_cartesian)
