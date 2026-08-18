from __future__ import annotations

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    BrowserMeshProfile,
    DensityShellFitResult,
    DensityShellGeometry,
    ExplicitConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    FrameworkMapping,
    FrameworkPathRule,
    PeriodicScalarField3D,
    build_topology_catalog,
    compute_atomic_connectivity,
    fit_density_scene_to_browser_budget,
    plot_framework_dynamics_3d,
    prepare_framework_dynamics_scene,
)
from mdstats.analysis.atomic_connectivity import AtomicEdgeKey


def _partitioned_fixture():
    atomic_numbers = np.asarray([14, 14, 13, 13, 8, 8, 8, 8, 8, 8], dtype=np.int32)
    n_frames = 7
    n_atoms = len(atomic_numbers)
    fractional = np.zeros((n_frames, n_atoms, 3), dtype=float)
    fractional[:, :, 0] = np.linspace(0.1, 0.8, n_atoms)[None, :]
    fractional[:, :, 1] = np.linspace(0.2, 0.7, n_atoms)[None, :]
    collection = AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=atomic_numbers,
        masses=np.ones(n_atoms),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.arange(n_frames, dtype=float),
        cells=np.repeat((np.eye(3) * 20.0)[None, ...], n_frames, axis=0),
        origins=np.zeros((n_frames, 3)),
        fractional_positions=fractional,
        velocities=np.zeros((n_frames, n_atoms, 3)),
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("partitioned-01976",),
            velocity_source="native",
            coordinate_normalization="minimum_image_inferred",
            stress_source=None,
            units_source="synthetic",
        ),
    )
    pairs = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
    frame_edges = {}
    for frame, (left, right) in enumerate(pairs):
        linker = 4 + frame
        frame_edges[frame] = (AtomicEdgeKey(left, linker), AtomicEdgeKey(linker, right))
    frame_edges[6] = ()
    connectivity = compute_atomic_connectivity(
        collection, ExplicitConnectivity(frame_edges=frame_edges)
    )
    mapping = FrameworkMapping.from_symbol_roles(
        {"Si": "vertex", "Al": "vertex", "O": "linker"},
        path_rules=(FrameworkPathRule.from_symbols("T-O-T", ("O",)),),
    )
    return collection, build_topology_catalog(collection, connectivity, mapping)


def _large_geometry(face_count: int) -> DensityShellGeometry:
    field = PeriodicScalarField3D(
        field_key="test-density",
        label="test density",
        values=np.ones((8, 8, 8), dtype=float),
        display_cell=np.eye(3) * 10.0,
        total_measure=1.0,
        selected_atom_indices=(0,),
        gaussian_bandwidth=0.2,
    )
    vertices = np.asarray([[0.1, 0.1, 0.1], [0.2, 0.1, 0.1], [0.1, 0.2, 0.1]])
    faces = np.tile(np.asarray([[0, 1, 2]], dtype=np.int64), (face_count, 1))
    return DensityShellGeometry(
        shell_key="atomic:test-density:0.5",
        field=field,
        mass_fraction=0.5,
        contour_level=0.5,
        vertices_fractional=vertices,
        vertices_cartesian=vertices @ field.display_cell,
        faces=faces,
        minimum_faces=4,
    )


@pytest.mark.parametrize("face_count", (301_838, 314_640, 582_375))
def test_closed_loop_routes_reported_overshoots_to_refit(monkeypatch, face_count: int) -> None:
    import mdstats.plotting.density_scene_fit as module

    geometry = _large_geometry(face_count)

    def fake_fit(item, *, target_faces, simplification_options, profile):
        fitted = item.with_geometry(
            item.vertices_fractional,
            item.vertices_cartesian,
            item.faces[:target_faces],
            source_kind="test_refit",
        )
        return DensityShellFitResult(
            geometry=fitted,
            initial_faces=item.face_count,
            initial_target_faces=target_faces,
            final_target_faces=target_faces,
            attempts=(),
            fallback_level="test_refit",
            target_met=True,
        )

    monkeypatch.setattr(module, "fit_density_shell", fake_fit)
    fitted, report = fit_density_scene_to_browser_budget(
        (geometry,), profile=BrowserMeshProfile.compact(), non_density_trace_count=4
    )
    assert report.passed
    assert fitted[0].face_count <= 300_000
    assert report.usage.final_density_face_count <= 300_000


def test_partitioned_catalog_prepares_and_renders_grouped_category_layers() -> None:
    pytest.importorskip("plotly")
    collection, catalog = _partitioned_fixture()
    scene = prepare_framework_dynamics_scene(collection, catalog)
    assert len(scene.topology_categories) == 7
    assert scene.topology_catalog is catalog
    assert sum(len(item.frame_indices) for item in scene.topology_categories) == 7
    assert np.isclose(sum(item.probability for item in scene.topology_categories), 1.0)
    assert scene.metadata["preparation_wall_seconds"] > 0.0
    assert (
        scene.metadata["partitioned_category_preparation_wall_seconds"]
        == scene.metadata["preparation_wall_seconds"]
    )

    result = plot_framework_dynamics_3d(scene)
    groups = result.render_metadata["topology_category_trace_indices"]
    assert len(groups) == 7
    for layer in scene.topology_categories:
        indices = groups[str(layer.topology_id)]
        assert indices
        traces = [result.figure.data[index] for index in indices]
        assert {trace.legendgroup for trace in traces} == {
            f"framework-topology:{layer.topology_id}"
        }
        expected = True if layer.topology_id == scene.dominant_topology_id else "legendonly"
        assert all(trace.visible == expected for trace in traces)
        assert len(indices) <= 4
    assert len(result.figure.data) <= result.browser_budget.max_plotly_traces
    assert result.browser_budget_report is not None
    assert result.browser_budget_report.passed
    assert result.figure.layout.legend.groupclick == "togglegroup"
