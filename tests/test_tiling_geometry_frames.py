from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    ConnectivityScope,
    DistanceConnectivity,
    ExplicitConnectivity,
    FrameSemantics,
    PairCutoffRegistry,
    build_topology_catalog,
    compute_atomic_connectivity,
    read_structure,
)
from mdstats.analysis import (
    FrameTilingGeometryCatalog,
    FrameTilingGeometryInputError,
    FrameTilingGeometryResourceError,
    FrameTilingGeometryResources,
    FrameTilingGeometrySerializationError,
    FrameTilingGeometryStatus,
    map_tiling_geometry_to_frames,
)
from tests.test_framework_topology import tot_mapping
from tests._lta_tiling_fixture import DATA, lta_reference_geometry


@pytest.fixture(scope="module")
def lta_frame_sources():
    single = read_structure(DATA / "Na_LTA_relaxed.POSCAR", format="vasp")
    framework_atoms = tuple(range(144))
    scope = ConnectivityScope.from_selection(included_atom_indices=framework_atoms)
    base_connectivity = compute_atomic_connectivity(
        single,
        DistanceConnectivity(
            cutoffs=PairCutoffRegistry.from_mapping(
                {("Si", "O"): 2.0, ("Al", "O"): 2.0}
            ),
            scope=scope,
        ),
    )
    _topology, reference, geometry = lta_reference_geometry()
    return SimpleNamespace(
        single=single,
        scope=scope,
        base_edges=base_connectivity.states[0].edge_keys,
        reference=reference,
        geometry=geometry,
    )


def _collection(
    sources,
    fractional_positions: np.ndarray,
    *,
    cells: np.ndarray | None = None,
    semantics: FrameSemantics = FrameSemantics.TRAJECTORY,
) -> AtomisticFrameCollection:
    fractional = np.asarray(fractional_positions, dtype=np.float64)
    n_frames = fractional.shape[0]
    if cells is None:
        cells = np.repeat(sources.single.cells, n_frames, axis=0)
    if semantics is FrameSemantics.TRAJECTORY:
        steps = np.arange(n_frames, dtype=np.int64)
        times = np.arange(n_frames, dtype=np.float64)
        velocities = np.zeros_like(fractional)
        provenance = replace(
            sources.single.provenance,
            velocity_source="native",
            coordinate_normalization="minimum_image_inferred",
        )
    else:
        steps = None
        times = None
        velocities = None
        provenance = replace(
            sources.single.provenance,
            velocity_source="unavailable",
            coordinate_normalization="independent_frame_wrapping",
        )
    return AtomisticFrameCollection(
        frame_semantics=semantics,
        frame_ids=np.arange(100, 100 + n_frames, dtype=np.int64),
        atomic_numbers=sources.single.atomic_numbers,
        masses=sources.single.masses,
        pbc=sources.single.pbc,
        steps=steps,
        times=times,
        cells=np.asarray(cells, dtype=np.float64),
        origins=np.repeat(sources.single.origins, n_frames, axis=0),
        fractional_positions=fractional,
        velocities=velocities,
        provenance=provenance,
        metadata={},
    )


def _sources_for_collection(sources, collection, *, frame_edges=None):
    definition = ExplicitConnectivity(
        scope=sources.scope,
        uniform_edges=sources.base_edges if frame_edges is None else None,
        frame_edges=frame_edges,
    )
    connectivity = compute_atomic_connectivity(collection, definition)
    topology_catalog = build_topology_catalog(collection, connectivity, tot_mapping())
    return connectivity, topology_catalog


def _map(sources, collection, *, frame_edges=None, **kwargs):
    connectivity, topology_catalog = _sources_for_collection(
        sources, collection, frame_edges=frame_edges
    )
    result = map_tiling_geometry_to_frames(
        sources.geometry,
        sources.reference.complex,
        sources.reference.embedding,
        sources.reference.ring_index,
        collection,
        connectivity,
        topology_catalog,
        **kwargs,
    )
    return result, connectivity, topology_catalog


def test_real_lta_frame_maps_complete_scientific_geometry(lta_frame_sources):
    sources = lta_frame_sources
    collection = _collection(sources, sources.single.fractional_positions.copy())
    result, _connectivity, _topology = _map(sources, collection)
    assert result.mapped_frame_count == 1
    frame = result.frames[0]
    assert frame.status is FrameTilingGeometryStatus.MAPPED
    assert len(frame.tiles) == 10
    assert len(frame.tile_faces) == 116
    assert len(frame.windows) == 58
    assert frame.total_tile_volume == pytest.approx(frame.cell_volume, abs=1.0e-8)
    assert frame.volume_closure_error < 1.0e-8
    assert frame.topology_graph_digest == sources.reference.complex.topology_graph_digest


def test_isotropic_cell_deformation_scales_geometric_descriptors(lta_frame_sources):
    sources = lta_frame_sources
    fractional = np.repeat(sources.single.fractional_positions, 2, axis=0)
    cells = np.repeat(sources.single.cells, 2, axis=0)
    scale = 1.02
    cells[1] *= scale
    collection = _collection(sources, fractional, cells=cells)
    result, _connectivity, _topology = _map(sources, collection)
    first, second = result.frames
    assert first.mapped and second.mapped
    assert second.tiles[0].volume / first.tiles[0].volume == pytest.approx(scale**3)
    assert second.tiles[0].surface_area / first.tiles[0].surface_area == pytest.approx(
        scale**2
    )
    assert second.tiles[0].diameter / first.tiles[0].diameter == pytest.approx(scale)
    assert second.windows[0].area / first.windows[0].area == pytest.approx(scale**2)


def test_integer_atom_wrapping_does_not_change_intrinsic_geometry(lta_frame_sources):
    sources = lta_frame_sources
    fractional = np.repeat(sources.single.fractional_positions, 2, axis=0)
    fractional[1, 0] += np.array([2.0, -1.0, 3.0])
    fractional[1, 70] += np.array([-2.0, 4.0, 1.0])
    collection = _collection(sources, fractional)
    result, _connectivity, _topology = _map(sources, collection)
    first, second = result.frames
    assert first.mapped and second.mapped
    np.testing.assert_allclose(
        [tile.volume for tile in first.tiles],
        [tile.volume for tile in second.tiles],
        rtol=1.0e-12,
        atol=1.0e-9,
    )
    np.testing.assert_allclose(
        [face.area for face in first.tile_faces],
        [face.area for face in second.tile_faces],
        rtol=1.0e-12,
        atol=1.0e-9,
    )


def test_trajectory_anchor_crossing_preserves_continuity(lta_frame_sources):
    sources = lta_frame_sources
    fractional = np.repeat(sources.single.fractional_positions, 2, axis=0)
    fractional[1] += np.array([1.0, 0.0, 0.0])
    collection = _collection(sources, fractional)
    result, _connectivity, _topology = _map(sources, collection)
    first, second = result.frames
    assert second.global_image_shift[0] == first.global_image_shift[0] + 1
    delta = np.asarray(second.tiles[0].fractional_center) - np.asarray(
        first.tiles[0].fractional_center
    )
    np.testing.assert_allclose(delta, [1.0, 0.0, 0.0], atol=1.0e-12)
    assert second.tiles[0].volume == pytest.approx(first.tiles[0].volume)


def test_nonplanar_thermal_face_is_retained_descriptively(lta_frame_sources):
    sources = lta_frame_sources
    fractional = np.repeat(sources.single.fractional_positions, 2, axis=0)
    fractional[1, 0] += np.array([0.006, -0.004, 0.008])
    collection = _collection(sources, fractional)
    result, _connectivity, _topology = _map(sources, collection)
    assert result.frames[1].mapped
    baseline = np.asarray([face.planarity_max for face in result.frames[0].tile_faces])
    perturbed = np.asarray([face.planarity_max for face in result.frames[1].tile_faces])
    assert np.max(np.abs(perturbed - baseline)) > 1.0e-4
    assert np.max(perturbed) > 1.0e-3
    assert any(not face.planar_aperture_certified for face in result.frames[1].tile_faces)


def test_topology_change_is_explicit_and_metric_series_uses_nan(lta_frame_sources):
    sources = lta_frame_sources
    fractional = np.repeat(sources.single.fractional_positions, 2, axis=0)
    collection = _collection(sources, fractional)
    damaged = tuple(sources.base_edges[1:])
    frame_edges = {0: sources.base_edges, 1: damaged}
    result, _connectivity, _topology = _map(
        sources, collection, frame_edges=frame_edges
    )
    assert result.frames[0].mapped
    assert result.frames[1].status is FrameTilingGeometryStatus.TOPOLOGY_MISMATCH
    series = result.tile_metric(0, "volume")
    assert np.isfinite(series[0])
    assert np.isnan(series[1])
    assert result.unresolved_frame_count == 1


def test_ensemble_frames_are_independently_wrapped(lta_frame_sources):
    sources = lta_frame_sources
    fractional = np.repeat(sources.single.fractional_positions, 2, axis=0)
    fractional[1] += np.array([4.0, -3.0, 2.0])
    collection = _collection(
        sources, fractional, semantics=FrameSemantics.ENSEMBLE
    )
    result, _connectivity, _topology = _map(sources, collection)
    assert result.mapped_frame_count == 2
    assert result.frames[0].global_image_shift == result.frames[1].global_image_shift
    np.testing.assert_allclose(
        result.tile_metric(0, "volume"),
        [result.frames[0].tiles[0].volume] * 2,
        rtol=1.0e-12,
        atol=1.0e-9,
    )


def test_resource_preflight_occurs_before_mapping(lta_frame_sources):
    sources = lta_frame_sources
    fractional = np.repeat(sources.single.fractional_positions, 2, axis=0)
    collection = _collection(sources, fractional)
    connectivity, topology = _sources_for_collection(sources, collection)
    with pytest.raises(FrameTilingGeometryResourceError, match="max_frames"):
        map_tiling_geometry_to_frames(
            sources.geometry,
            sources.reference.complex,
            sources.reference.embedding,
            sources.reference.ring_index,
            collection,
            connectivity,
            topology,
            resources=FrameTilingGeometryResources(max_frames=1),
        )


def test_source_replay_and_tamper_rejection(lta_frame_sources):
    sources = lta_frame_sources
    collection = _collection(sources, sources.single.fractional_positions.copy())
    result, connectivity, topology = _map(sources, collection)
    assert (
        FrameTilingGeometryCatalog.from_dict(
            result.to_dict(),
            reference_geometry=sources.geometry,
            complex_=sources.reference.complex,
            embedding=sources.reference.embedding,
            ring_index=sources.reference.ring_index,
            collection=collection,
            connectivity=connectivity,
            topology_catalog=topology,
        )
        == result
    )
    payload = deepcopy(result.to_dict())
    payload["frames"][0]["tiles"][0]["volume"] += 1.0
    with pytest.raises(FrameTilingGeometrySerializationError):
        FrameTilingGeometryCatalog.from_dict(
            payload,
            reference_geometry=sources.geometry,
            complex_=sources.reference.complex,
            embedding=sources.reference.embedding,
            ring_index=sources.reference.ring_index,
            collection=collection,
            connectivity=connectivity,
            topology_catalog=topology,
        )


def test_wrong_source_type_and_bad_metric_are_rejected(lta_frame_sources):
    sources = lta_frame_sources
    collection = _collection(sources, sources.single.fractional_positions.copy())
    connectivity, topology = _sources_for_collection(sources, collection)
    with pytest.raises(FrameTilingGeometryInputError):
        map_tiling_geometry_to_frames(
            object(),  # type: ignore[arg-type]
            sources.reference.complex,
            sources.reference.embedding,
            sources.reference.ring_index,
            collection,
            connectivity,
            topology,
        )
    result = map_tiling_geometry_to_frames(
        sources.geometry,
        sources.reference.complex,
        sources.reference.embedding,
        sources.reference.ring_index,
        collection,
        connectivity,
        topology,
    )
    with pytest.raises(FrameTilingGeometryInputError, match="Unsupported tile metric"):
        result.tile_metric(0, "not-a-metric")
