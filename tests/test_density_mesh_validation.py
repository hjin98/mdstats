"""LD9-V0 mesh-fidelity metric tests."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats.plotting.density_mesh_validation import (
    MeshFidelityOptions,
    compare_mesh_fidelity,
    summarize_mesh_topology,
)
from mdstats.plotting.graph_errors import GraphAdapterError


def octahedron() -> tuple[np.ndarray, np.ndarray]:
    vertices = np.asarray(
        [
            [1.0, 0.0, 0.0],
            [-1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, -1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, -1.0],
        ],
        dtype=np.float64,
    )
    faces = np.asarray(
        [
            [0, 2, 4],
            [2, 1, 4],
            [1, 3, 4],
            [3, 0, 4],
            [2, 0, 5],
            [1, 2, 5],
            [3, 1, 5],
            [0, 3, 5],
        ],
        dtype=np.int64,
    )
    return vertices, faces


def test_topology_summary_recognizes_closed_octahedron() -> None:
    vertices, faces = octahedron()
    summary = summarize_mesh_topology(vertices, faces)
    assert summary.vertex_count == 6
    assert summary.edge_count == 12
    assert summary.face_count == 8
    assert summary.connected_component_count == 1
    assert summary.euler_characteristic == 2
    assert summary.is_closed_two_manifold


def test_identical_mesh_passes_geometry_normal_and_topology_metrics() -> None:
    vertices, faces = octahedron()
    report = compare_mesh_fidelity(
        vertices,
        faces,
        vertices,
        faces,
        options=MeshFidelityOptions(max_samples=20_000, max_surface_error=1.0e-12),
    )
    assert report.passed
    assert report.symmetric_distance_max <= 1.0e-12
    assert report.normal_error_p99_degrees <= 1.0e-10


def test_shifted_mesh_fails_surface_error_but_preserves_topology() -> None:
    vertices, faces = octahedron()
    shifted = vertices + np.asarray([0.08, 0.0, 0.0])
    report = compare_mesh_fidelity(
        vertices,
        faces,
        shifted,
        faces,
        options=MeshFidelityOptions(max_samples=50_000, max_surface_error=0.02),
    )
    assert not report.passed
    assert any(value.startswith("surface_error=") for value in report.violations)
    assert report.reference_topology.euler_characteristic == 2
    assert report.candidate_topology.euler_characteristic == 2


def test_scalar_residual_is_measured_against_contour_level() -> None:
    vertices, faces = octahedron()

    def radius_squared(points: np.ndarray) -> np.ndarray:
        return np.sum(points * points, axis=1)

    report = compare_mesh_fidelity(
        vertices,
        faces,
        vertices,
        faces,
        options=MeshFidelityOptions(
            max_samples=20_000,
            max_surface_error=1.0e-12,
            max_scalar_residual=0.8,
        ),
        scalar_sampler=radius_squared,
        contour_level=1.0,
    )
    assert report.scalar_residual_max is not None
    assert report.scalar_residual_max < 0.8


def test_malformed_face_index_is_rejected() -> None:
    vertices, faces = octahedron()
    malformed = faces.copy()
    malformed[0, 0] = vertices.shape[0]
    with pytest.raises(GraphAdapterError):
        summarize_mesh_topology(vertices, malformed)


def test_zero_area_triangle_is_rejected_for_fidelity() -> None:
    vertices = np.asarray(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]],
        dtype=np.float64,
    )
    faces = np.asarray([[0, 1, 2]], dtype=np.int64)
    with pytest.raises(GraphAdapterError):
        compare_mesh_fidelity(vertices, faces, vertices, faces)


def test_mesh_validation_records_round_trip_canonical_json() -> None:
    vertices, faces = octahedron()
    report = compare_mesh_fidelity(vertices, faces, vertices, faces)
    restored = type(report).from_json_dict(report.to_json_dict())
    assert restored == report
    assert restored.to_json_dict() == report.to_json_dict()
