"""Focused GFX3D-2 independent-layer composition qualification."""

from __future__ import annotations

import itertools

import pytest

from mdstats import (
    DistanceConnectivity,
    PairCutoffRegistry,
    compute_atomic_connectivity,
    prepare_framework_dynamics_scene,
)
from mdstats.graphics3d import (
    DEFAULT_GRAPHICS_LAYER_REGISTRY,
    AtomicConnectivityLayer,
    AtomicDensityLayer,
    AtomicTrajectoryLayer,
    FrameworkTopologyLayer,
    GraphicsLayer3DRequest,
    GraphicsScene3DRequest,
    GraphicsSceneContext,
    GraphicsSelection,
    prepare_graphics3d_scene,
    render_graphics3d_plotly,
)
from mdstats.plotting.atomic_density import AtomicDensityOptions, AtomicDensitySelection
from mdstats.plotting.framework_dynamics import (
    AtomicMeanGraphOptions,
    FrameworkDynamicsResources,
    TrajectoryAtomSelection,
)

from tests.test_graphics3d_contracts import _small_collection, _small_topology


@pytest.fixture(scope="module")
def full_legacy_scene():
    collection = _small_collection()
    topology = _small_topology(collection)
    connectivity = compute_atomic_connectivity(
        collection,
        DistanceConnectivity(
            cutoffs=PairCutoffRegistry.from_mapping(
                {("Si", "O"): 2.1, ("Al", "O"): 2.1, ("Na", "O"): 4.5}
            )
        ),
    )
    return prepare_framework_dynamics_scene(
        collection,
        topology,
        trajectory_selection=TrajectoryAtomSelection(species=("Na",)),
        atomic_connectivity=connectivity,
        atomic_mean_graph_options=AtomicMeanGraphOptions(
            mode="occupancy", occupancy_threshold=0.0
        ),
        atomic_density_selections=(
            AtomicDensitySelection(species=("Na",), label="Na"),
        ),
        atomic_density_options=AtomicDensityOptions(
            grid_shape=(8, 8, 8),
            gaussian_bandwidth=2.0,
            adaptive_smearing=False,
            store_sample_positions=False,
        ),
        resources=FrameworkDynamicsResources(
            max_threads=1,
            max_memory_bytes=256 * 1024 * 1024,
        ),
    )


def _request(layer_types: tuple[str, ...]) -> GraphicsScene3DRequest:
    layers = []
    for layer_type in layer_types:
        if layer_type == "framework":
            layers.append(GraphicsLayer3DRequest(name="framework", layer_type="framework"))
        elif layer_type == "connectivity":
            layers.append(
                GraphicsLayer3DRequest(name="connectivity", layer_type="connectivity")
            )
        elif layer_type == "trajectory":
            layers.append(
                GraphicsLayer3DRequest(
                    name="trajectory",
                    layer_type="trajectory",
                    selection=GraphicsSelection(species=("Na",)),
                )
            )
        elif layer_type == "density":
            layers.append(
                GraphicsLayer3DRequest(
                    name="density",
                    layer_type="density",
                    selection=GraphicsSelection(species=("Na",)),
                )
            )
        else:  # pragma: no cover
            raise AssertionError(layer_type)
    return GraphicsScene3DRequest(layers=tuple(layers))


def test_builtin_layer_types_are_registered_with_production_adapters() -> None:
    assert set(DEFAULT_GRAPHICS_LAYER_REGISTRY.layer_types()) >= {
        "framework",
        "connectivity",
        "trajectory",
        "density",
    }
    assert isinstance(
        DEFAULT_GRAPHICS_LAYER_REGISTRY.get("framework").adapter_factory(),
        FrameworkTopologyLayer,
    )
    assert isinstance(
        DEFAULT_GRAPHICS_LAYER_REGISTRY.get("connectivity").adapter_factory(),
        AtomicConnectivityLayer,
    )
    assert isinstance(
        DEFAULT_GRAPHICS_LAYER_REGISTRY.get("trajectory").adapter_factory(),
        AtomicTrajectoryLayer,
    )
    assert isinstance(
        DEFAULT_GRAPHICS_LAYER_REGISTRY.get("density").adapter_factory(),
        AtomicDensityLayer,
    )


@pytest.mark.parametrize(
    "layer_types",
    [
        combo
        for size in range(1, 5)
        for combo in itertools.combinations(
            ("framework", "connectivity", "trajectory", "density"), size
        )
    ],
    ids=lambda value: "+".join(value),
)
def test_all_15_nonempty_layer_combinations_prepare_and_render(
    full_legacy_scene, layer_types
) -> None:
    context = GraphicsSceneContext(source=full_legacy_scene, source_identity="gfx3d2-small")
    prepared = prepare_graphics3d_scene(_request(layer_types), context=context)
    assert tuple(layer.request.layer_type for layer in prepared.layers) == layer_types
    # All four built-in adapters consume the same already-prepared scientific scene.
    assert dict(context.cache_report()) == {"entries": 1, "hits": 0, "misses": 1}

    rendered = render_graphics3d_plotly(prepared)
    assert tuple(rendered.layer_results) == tuple(layer.request.name for layer in prepared.layers)
    claimed: set[int] = set()
    for layer in prepared.layers:
        result = rendered.layer_results[layer.request.name]
        assert result.backend_object_indices
        assert not (claimed & set(result.backend_object_indices))
        claimed.update(result.backend_object_indices)
        assert result.scientific_identity == layer.scientific_identity
        assert result.render_identity == layer.render_identity
    scene_owned = set(rendered.render_metadata.get("scene_trace_indices", ()))
    assert not (claimed & scene_owned)
    assert claimed | scene_owned == set(range(len(rendered.artifact.data)))


def test_duplicate_instances_of_same_type_are_independent(full_legacy_scene) -> None:
    request = GraphicsScene3DRequest(
        layers=(
            GraphicsLayer3DRequest(
                name="Na path A",
                layer_type="trajectory",
                selection=GraphicsSelection(species=("Na",)),
                render_options={"opacity": 0.25},
            ),
            GraphicsLayer3DRequest(
                name="Na path B",
                layer_type="trajectory",
                selection=GraphicsSelection(species=("Na",)),
                render_options={"opacity": 0.85},
            ),
            GraphicsLayer3DRequest(
                name="Na density soft",
                layer_type="density",
                selection=GraphicsSelection(species=("Na",)),
                render_options={"inner_opacity": 0.15, "outer_opacity": 0.05},
            ),
            GraphicsLayer3DRequest(
                name="Na density strong",
                layer_type="density",
                selection=GraphicsSelection(species=("Na",)),
                render_options={"inner_opacity": 0.55, "outer_opacity": 0.20},
            ),
        )
    )
    context = GraphicsSceneContext(source=full_legacy_scene, source_identity="gfx3d2-duplicates")
    prepared = prepare_graphics3d_scene(request, context=context)
    assert prepared.layers[0].scientific_identity == prepared.layers[1].scientific_identity
    assert prepared.layers[0].render_identity != prepared.layers[1].render_identity
    assert prepared.layers[2].scientific_identity == prepared.layers[3].scientific_identity
    assert prepared.layers[2].render_identity != prepared.layers[3].render_identity
    rendered = render_graphics3d_plotly(prepared)
    assert len(rendered.layer_results) == 4
    assert all(result.backend_object_indices for result in rendered.layer_results.values())


def test_connectivity_pair_selection_is_scientific_and_filtered(full_legacy_scene) -> None:
    request = GraphicsScene3DRequest(
        layers=(
            GraphicsLayer3DRequest(
                name="Si-O",
                layer_type="connectivity",
                selection=GraphicsSelection(pairs=(("Si", "O"),)),
            ),
        )
    )
    prepared = prepare_graphics3d_scene(
        request,
        context=GraphicsSceneContext(source=full_legacy_scene, source_identity="gfx3d2-pair"),
    )
    graph = prepared.layers[0].product_refs["atomic_mean_graph"]
    assert set(graph.atomic_numbers.tolist()) == {8, 14}
    assert graph.edge_endpoints.shape[0] >= 1


def test_density_selection_fails_closed_when_not_present(full_legacy_scene) -> None:
    request = GraphicsScene3DRequest(
        layers=(
            GraphicsLayer3DRequest(
                name="K density",
                layer_type="density",
                selection=GraphicsSelection(species=("K",)),
            ),
        )
    )
    with pytest.raises(Exception, match="did not match any prepared density field"):
        prepare_graphics3d_scene(
            request,
            context=GraphicsSceneContext(source=full_legacy_scene, source_identity="gfx3d2-k"),
        )


def test_prepared_layer_does_not_silently_ignore_scientific_options(full_legacy_scene) -> None:
    request = GraphicsScene3DRequest(
        layers=(
            GraphicsLayer3DRequest(
                name="trajectory",
                layer_type="trajectory",
                selection=GraphicsSelection(species=("Na",)),
                analysis_options={"path_mode": "folded"},
            ),
        )
    )
    with pytest.raises(Exception, match="cannot apply scientific analysis options"):
        prepare_graphics3d_scene(
            request,
            context=GraphicsSceneContext(source=full_legacy_scene, source_identity="gfx3d2-options"),
        )


def test_gfx3d_density_renderer_accepts_packed_sparse_field() -> None:
    import numpy as np

    from mdstats.graphics3d.contracts import PreparedGraphicsLayer3D
    from mdstats.graphics3d.layers import _density_render_primitives
    from mdstats.graphics3d.primitives import PointSet3D, TriangleMesh3D
    from mdstats.plotting.density_contracts import (
        DensitySourceProvenance,
        PeriodicWeightedSamples3D,
    )
    from mdstats.plotting.density_packed_field import pack_sparse_reference_field
    from mdstats.plotting.density_sparse_reference import (
        prepare_sparse_canonical_density_reference,
    )

    positions = np.asarray([[0.46, 0.51, 0.54]], dtype=np.float64)
    batch = PeriodicWeightedSamples3D(
        fractional_positions=positions,
        weights=np.ones(1, dtype=np.float64),
        source_provenance=DensitySourceProvenance(
            source_kind="atomic_occupancy", atom_indices=(0,)
        ),
        total_measure=1.0,
        measure_kind="occupancy",
        measure_units="count",
    )
    reference = prepare_sparse_canonical_density_reference(
        batch,
        grid_shape=(20, 20, 20),
        display_cell=np.eye(3, dtype=np.float64) * 6.0,
        gaussian_bandwidth=0.35,
        field_key="atomic-density-0",
        label="Na density",
        physical_units="angstrom^-3",
        broadening_metric="gaussian_sigma_v1",
        max_workspace_bytes=128 * 1024 * 1024,
    )
    packed = pack_sparse_reference_field(reference, storage_block_shape=(8, 8, 8))
    request = GraphicsLayer3DRequest(
        name="Na density",
        layer_type="density",
        selection=GraphicsSelection(species=("Na",)),
        render_options={"mass_fractions": (0.5, 0.8)},
    )
    prepared = PreparedGraphicsLayer3D(
        request=request,
        scientific_identity="packed-sparse-density",
        product_refs={"density_field": packed},
    )
    primitives = _density_render_primitives(
        prepared,
        GraphicsSceneContext(source_identity="packed-sparse-density"),
    )
    assert primitives
    assert all(isinstance(value, (TriangleMesh3D, PointSet3D)) for value in primitives)
