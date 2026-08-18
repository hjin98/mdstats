from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    DistanceConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    FrameworkAtomRole,
    FrameworkMapping,
    FrameworkPathRule,
    PairCutoffRegistry,
    build_topology_catalog,
    compute_atomic_connectivity,
    prepare_framework_dynamics_scene,
)
from mdstats.graphics3d import (
    GraphicsLayer3DRequest,
    GraphicsScene3DRequest,
    GraphicsSceneContext,
    GraphicsSelection,
    prepare_graphics3d_scene,
    render_graphics3d_plotly,
)
from mdstats.graphics3d.errors import Graphics3DValidationError
from mdstats.graphics3d.lta_preset import prepare_legacy_source_scene
from mdstats.graphics3d.view import resolve_camera, resolve_periodic_image_shifts
from tests.test_graphics3d_layers import full_legacy_scene


def _small_collection() -> AtomisticFrameCollection:
    frac = np.asarray(
        [
            [[0.10, 0.10, 0.10], [0.20, 0.10, 0.10], [0.30, 0.10, 0.10], [0.80, 0.50, 0.50]],
            [[0.10, 0.10, 0.10], [0.20, 0.10, 0.10], [0.30, 0.10, 0.10], [0.82, 0.50, 0.50]],
        ],
        dtype=float,
    )
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.asarray([10, 11], dtype=np.int64),
        atomic_numbers=np.asarray([14, 8, 13, 11], dtype=np.int32),
        masses=np.ones(4),
        pbc=np.ones(3, dtype=bool),
        steps=np.asarray([0, 1], dtype=np.int64),
        times=np.asarray([0.0, 1.0]),
        cells=np.repeat((np.eye(3) * 10.0)[None, :, :], 2, axis=0),
        origins=np.zeros((2, 3)),
        fractional_positions=frac,
        velocities=np.zeros((2, 4, 3)),
        provenance=FrameCollectionProvenance(
            source_format="synthetic-gfx3d-harden1",
            source_files=("synthetic",),
            velocity_source="synthetic",
            coordinate_normalization="time_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def _mapping() -> FrameworkMapping:
    return FrameworkMapping.from_symbol_roles(
        {
            "Si": FrameworkAtomRole.VERTEX,
            "Al": FrameworkAtomRole.VERTEX,
            "O": FrameworkAtomRole.LINKER,
            "Na": FrameworkAtomRole.SPECTATOR,
        },
        path_rules=(FrameworkPathRule.from_symbols("T-O-T", ("O",), edge_kind="oxygen_bridge"),),
    )


def test_periodic_and_camera_validation_is_strict() -> None:
    with pytest.raises(Graphics3DValidationError, match="exact integers"):
        resolve_periodic_image_shifts({"periodic_images": {"counts": [1.9, 1, 1]}})
    with pytest.raises(Graphics3DValidationError, match="exact integers"):
        resolve_periodic_image_shifts({"periodic_images": [[0.0, 0, 0]]})
    with pytest.raises(Graphics3DValidationError, match="finite"):
        resolve_camera({"camera": {"eye": [np.nan, 0.0, 1.0]}})
    with pytest.raises(Graphics3DValidationError, match="nonzero"):
        resolve_camera({"camera": {"eye": [0.0, 0.0, 0.0]}})
    with pytest.raises(Graphics3DValidationError, match="nonzero"):
        resolve_camera({"camera": {"up": [0.0, 0.0, 0.0]}})


def test_density_only_scene_gets_scene_owned_cell(full_legacy_scene) -> None:
    request = GraphicsScene3DRequest(
        layers=(
            GraphicsLayer3DRequest(
                "Na density", "density", selection=GraphicsSelection(species=("Na",))
            ),
        ),
        view={"cell_mode": "reference"},
    )
    prepared = prepare_graphics3d_scene(
        request,
        context=GraphicsSceneContext(source=full_legacy_scene, source_identity="density-only-cell"),
    )
    rendered = render_graphics3d_plotly(prepared)
    scene_indices = tuple(rendered.render_metadata["scene_trace_indices"])
    assert len(scene_indices) == 1
    assert scene_indices[0] not in rendered.layer_results["Na density"].backend_object_indices
    assert rendered.artifact.data[scene_indices[0]].mode == "lines"


def test_universal_trajectory_hover_matches_legacy_semantics(full_legacy_scene) -> None:
    request = GraphicsScene3DRequest(
        layers=(
            GraphicsLayer3DRequest(
                "Na trajectory",
                "trajectory",
                selection=GraphicsSelection(species=("Na",)),
                render_options={"enable_hover": True},
            ),
        )
    )
    prepared = prepare_graphics3d_scene(
        request,
        context=GraphicsSceneContext(source=full_legacy_scene, source_identity="hover"),
    )
    rendered = render_graphics3d_plotly(prepared)
    traces = [rendered.artifact.data[index] for index in rendered.layer_results["Na trajectory"].backend_object_indices]
    line = next(trace for trace in traces if trace.mode == "lines")
    assert line.hovertemplate == "%{text}<extra></extra>"
    joined = " ".join(str(value) for value in line.text if value is not None)
    assert "atom=" in joined and "frame=" in joined and "frame_id=" in joined


def test_browser_budget_fails_before_periodic_materialization(full_legacy_scene, monkeypatch) -> None:
    request = GraphicsScene3DRequest(
        layers=(GraphicsLayer3DRequest("framework", "framework"),),
        view={"periodic_images": "321x1x1", "cell_mode": "none"},
    )
    prepared = prepare_graphics3d_scene(
        request,
        context=GraphicsSceneContext(source=full_legacy_scene, source_identity="preflight-budget"),
    )
    import mdstats.graphics3d.plotly_renderer as renderer

    def forbidden(*args, **kwargs):
        raise AssertionError("periodic arrays were materialized before browser preflight")

    monkeypatch.setattr(renderer, "replicate_primitive", forbidden)
    with pytest.raises(Graphics3DValidationError, match="browser payload"):
        renderer.render_graphics3d_plotly(prepared, browser_profile="compact")


def test_uniform_topology_catalog_uses_fast_path(monkeypatch) -> None:
    collection = _small_collection()
    definition = DistanceConnectivity(cutoffs=PairCutoffRegistry.from_mapping({("Si", "O"): 2.1, ("Al", "O"): 2.1}))
    connectivity = compute_atomic_connectivity(collection, definition)
    catalog = build_topology_catalog(collection, connectivity, _mapping())
    assert len(catalog.topologies) == 1

    import mdstats.plotting.framework_dynamics as fd

    def forbidden(*args, **kwargs):
        raise AssertionError("uniform catalog should not enter partitioned preparation")

    monkeypatch.setattr(fd, "_prepare_partitioned_framework_dynamics_scene", forbidden)
    scene = prepare_framework_dynamics_scene(collection, catalog)
    assert scene.metadata["topology_category_policy"] == "uniform_catalog_fast_path_v1"
    assert scene.metadata["uniform_catalog_duplicate_preparation_avoided"] is True
    assert len(scene.topology_categories) == 1


def test_authenticated_topology_cache_reuses_exact_geometry(monkeypatch, tmp_path) -> None:
    import mdstats.graphics3d.lta_preset as lta

    collection = _small_collection()
    request = GraphicsScene3DRequest(layers=(GraphicsLayer3DRequest("framework", "framework"),))
    cache = tmp_path / "topology.json"
    output = tmp_path / "scene.html"
    calls = 0
    original = lta.compute_atomic_connectivity

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(lta, "compute_atomic_connectivity", counted)
    monkeypatch.setattr(lta, "prepare_framework_dynamics_scene", lambda *args, **kwargs: SimpleNamespace())
    options = {"topology_cache": str(cache)}

    _, first = prepare_legacy_source_scene(collection, request, input_options=options, output_path=output)
    assert calls == 1
    assert first["source"] == "inferred_hysteretic_catalog"
    assert cache.exists()

    _, second = prepare_legacy_source_scene(collection, request, input_options=options, output_path=output)
    assert calls == 1
    assert second["source"] == "authenticated_topology_cache"
    assert second["cache_authentication"] == "passed"

    changed = np.array(collection.fractional_positions, copy=True)
    changed[1, 3, 0] += 1.0e-6
    altered = replace(collection, fractional_positions=changed)
    _, third = prepare_legacy_source_scene(altered, request, input_options=options, output_path=output)
    assert calls == 2
    assert str(third["cache_reuse_rejected"]).startswith("authority_mismatch:trajectory_topology_identity")


def test_static_cell_bulk_framework_registration_matches_frame_local_reference(monkeypatch) -> None:
    collection = _small_collection()
    definition = DistanceConnectivity(
        cutoffs=PairCutoffRegistry.from_mapping({("Si", "O"): 2.1, ("Al", "O"): 2.1})
    )
    connectivity = compute_atomic_connectivity(collection, definition)
    catalog = build_topology_catalog(collection, connectivity, _mapping())
    topology = catalog.topologies[0]

    fast = prepare_framework_dynamics_scene(collection, topology)

    import mdstats.plotting.framework_dynamics as fd

    monkeypatch.setattr(fd, "_bulk_static_cell_projected_framework_lifts", lambda *args, **kwargs: None)
    reference = prepare_framework_dynamics_scene(collection, topology)

    assert np.array_equal(fast.mean_framework.edge_image_shifts, reference.mean_framework.edge_image_shifts)
    assert np.allclose(
        fast.mean_framework.node_positions_3d,
        reference.mean_framework.node_positions_3d,
        rtol=0.0,
        atol=1.0e-12,
    )
    assert fast.mean_framework.node_keys == reference.mean_framework.node_keys
    assert fast.mean_framework.edge_keys == reference.mean_framework.edge_keys
