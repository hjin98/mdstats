"""Focused GFX3D-1 universal-contract qualification tests."""

from __future__ import annotations

from dataclasses import replace

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
    build_framework_topology,
    compute_atomic_connectivity,
    plot_framework_dynamics_3d,
    prepare_framework_dynamics_scene,
)
from mdstats.graphics3d import (
    Graphics3DValidationError,
    GraphicsDependencyKey,
    GraphicsDependencyRequest,
    GraphicsLayer3DRequest,
    GraphicsLayerRegistration,
    GraphicsLayerRegistry,
    GraphicsScene3DRequest,
    GraphicsSceneContext,
    GraphicsSelection,
    PointSet3D,
    PreparedGraphicsLayer3D,
    adapt_framework_dynamics_render_result,
    adapt_framework_dynamics_scene,
    build_graphics_scene_manifest,
    canonical_json,
    deduplicate_dependency_requests,
    plan_graphics_scene_dependencies,
)


class _MockAdapter:
    def dependencies(self, request, context):
        return (
            GraphicsDependencyRequest(
                GraphicsDependencyKey(
                    "registered_coordinates",
                    {"source": context.source_identity or "source", "gauge": "material"},
                )
            ),
        )

    def prepare(self, request, resolved_dependencies, context):  # pragma: no cover - protocol shape
        return PreparedGraphicsLayer3D(
            request=request,
            scientific_identity=request.scientific_identity,
        )

    def render_primitives(self, prepared, context):  # pragma: no cover - protocol shape
        return ()


def _registration(layer_type: str, *, supported=("species",)) -> GraphicsLayerRegistration:
    return GraphicsLayerRegistration(
        layer_type=layer_type,
        schema_version=f"test.{layer_type}.v1",
        adapter_factory=_MockAdapter,
        supported_selection_fields=frozenset(supported),
        required_dependency_providers=("registered_coordinates",),
        supported_primitive_types=("PointSet3D",),
    )


def test_selection_normalizes_and_serializes_deterministically() -> None:
    left = GraphicsSelection(
        species=("Na", "Li", "Na"),
        atom_indices=(5, 1, 5),
        pairs=(("O", "Na"), ("Na", "O")),
        ring_sizes=(8, 4, 8),
        site_ids=("8R-b", "8R-a"),
    )
    right = GraphicsSelection(
        site_ids=("8R-a", "8R-b"),
        ring_sizes=(4, 8),
        pairs=(("Na", "O"),),
        atom_indices=(1, 5),
        species=("Li", "Na"),
    )
    assert left == right
    assert left.identity == right.identity
    assert canonical_json(left) == canonical_json(right)
    assert left.species == ("Li", "Na")
    assert left.pairs == (("O", "Na"),)


def test_selection_fails_closed_on_unknown_species() -> None:
    with pytest.raises(Graphics3DValidationError, match="Unknown chemical species"):
        GraphicsSelection(species=("NotAnElement",))


def test_duplicate_layer_names_fail_closed() -> None:
    layer = GraphicsLayer3DRequest(name="Na density", layer_type="density")
    with pytest.raises(Graphics3DValidationError, match="must be unique"):
        GraphicsScene3DRequest(layers=(layer, replace(layer, layer_type="trajectory")))


def test_render_only_changes_do_not_change_scientific_identity() -> None:
    base = GraphicsLayer3DRequest(
        name="Na density",
        layer_type="density",
        selection=GraphicsSelection(species=("Na",)),
        analysis_options={"sigma_angstrom": 0.5, "grid_shape": [64, 64, 64]},
        render_options={"opacity": 0.1},
    )
    styled = replace(
        base,
        name="sodium occupancy",
        initially_visible=False,
        render_options={"opacity": 0.75, "color": "blue"},
    )
    assert base.scientific_identity == styled.scientific_identity
    assert base.render_identity != styled.render_identity


def test_scientific_selection_and_analysis_change_scientific_identity() -> None:
    base = GraphicsLayer3DRequest(
        name="density",
        layer_type="density",
        selection=GraphicsSelection(species=("Na",)),
        analysis_options={"sigma_angstrom": 0.5},
    )
    potassium = replace(base, selection=GraphicsSelection(species=("K",)))
    broader = replace(base, analysis_options={"sigma_angstrom": 0.7})
    assert base.scientific_identity != potassium.scientific_identity
    assert base.scientific_identity != broader.scientific_identity




def test_scene_identity_domains_are_separate() -> None:
    layer = GraphicsLayer3DRequest(
        name="Na",
        layer_type="density",
        selection=GraphicsSelection(species=("Na",)),
        analysis_options={"sigma": 0.5},
        render_options={"opacity": 0.2},
    )
    base = GraphicsScene3DRequest(
        layers=(layer,),
        scene_options={"registration": "material"},
        view={"projection": "orthographic"},
        resources={"max_threads": 1},
    )
    visual = replace(base, view={"projection": "perspective"})
    execution = replace(base, resources={"max_threads": 4})
    assert base.scientific_identity == visual.scientific_identity == execution.scientific_identity
    assert base.render_identity != visual.render_identity
    assert base.execution_request_identity != execution.execution_request_identity

def test_execution_identity_is_separate_from_scientific_and_render_identity() -> None:
    request = GraphicsLayer3DRequest(name="Na", layer_type="density")
    cpu = PreparedGraphicsLayer3D(
        request=request,
        scientific_identity=request.scientific_identity,
        execution_evidence={"workers": 1, "backend": "cpu"},
    )
    threaded = PreparedGraphicsLayer3D(
        request=request,
        scientific_identity=request.scientific_identity,
        execution_evidence={"workers": 4, "backend": "cpu"},
    )
    assert cpu.scientific_identity == threaded.scientific_identity
    assert cpu.render_identity == threaded.render_identity
    assert cpu.execution_identity != threaded.execution_identity


def test_dependency_requests_deduplicate_and_required_dominates_optional() -> None:
    key_a = GraphicsDependencyKey("registered_coordinates", {"source": "abc", "mode": "material"})
    key_b = GraphicsDependencyKey("registered_coordinates", {"mode": "material", "source": "abc"})
    plan = deduplicate_dependency_requests(
        [
            GraphicsDependencyRequest(key_a, role="optional", consumer_layer="trajectory"),
            GraphicsDependencyRequest(key_b, role="required", consumer_layer="density"),
        ]
    )
    assert len(plan) == 1
    assert plan[0].key.identity == key_a.identity == key_b.identity
    assert plan[0].role == "required"
    assert plan[0].consumers == ("density", "trajectory")


def test_scene_context_resolves_equal_dependency_once() -> None:
    context = GraphicsSceneContext(source_identity="source-A")
    key = GraphicsDependencyKey("registered_coordinates", {"mode": "material"})
    calls = []

    def resolver():
        calls.append(1)
        return object()

    first = context.resolve_dependency(key, resolver)
    second = context.resolve_dependency(key, resolver)
    assert first is second
    assert calls == [1]
    assert dict(context.cache_report()) == {"entries": 1, "hits": 1, "misses": 1}


def test_registry_enumeration_is_deterministic_and_duplicate_registration_fails() -> None:
    registry = GraphicsLayerRegistry()
    registry.register(_registration("trajectory"))
    registry.register(_registration("density"))
    registry.register(_registration("framework"))
    assert registry.layer_types() == ("density", "framework", "trajectory")
    with pytest.raises(Exception, match="already registered"):
        registry.register(_registration("density"))


def test_scene_dependency_planner_deduplicates_shared_provider() -> None:
    registry = GraphicsLayerRegistry()
    registry.register(_registration("trajectory"))
    registry.register(_registration("density"))
    request = GraphicsScene3DRequest(
        layers=(
            GraphicsLayer3DRequest(
                name="Na path",
                layer_type="trajectory",
                selection=GraphicsSelection(species=("Na",)),
            ),
            GraphicsLayer3DRequest(
                name="Na density",
                layer_type="density",
                selection=GraphicsSelection(species=("Na",)),
            ),
        )
    )
    plan = plan_graphics_scene_dependencies(
        request,
        context=GraphicsSceneContext(source_identity="same-source"),
        registry=registry,
    )
    assert len(plan) == 1
    assert plan[0].consumers == ("Na density", "Na path")


def test_layer_selection_support_is_validated_by_registry() -> None:
    registry = GraphicsLayerRegistry()
    registry.register(_registration("framework", supported=()))
    request = GraphicsScene3DRequest(
        layers=(
            GraphicsLayer3DRequest(
                name="framework",
                layer_type="framework",
                selection=GraphicsSelection(species=("Na",)),
            ),
        )
    )
    with pytest.raises(Graphics3DValidationError, match="does not support selection fields"):
        plan_graphics_scene_dependencies(request, registry=registry)


def test_manifest_is_canonical_and_preserves_declared_layer_order() -> None:
    registry = GraphicsLayerRegistry()
    registry.register(_registration("trajectory"))
    registry.register(_registration("density"))
    request = GraphicsScene3DRequest(
        layers=(
            GraphicsLayer3DRequest(name="trajectory", layer_type="trajectory"),
            GraphicsLayer3DRequest(name="density", layer_type="density"),
        ),
        resources={"max_threads": 4},
        view={"projection": "orthographic"},
    )
    manifest_a = build_graphics_scene_manifest(
        request,
        registry=registry,
        context=GraphicsSceneContext(source_identity="abc"),
        source_descriptors=({"sha256": "abc", "path": "traj.dump"},),
        resolved_input_format="lammps-dump",
    )
    manifest_b = build_graphics_scene_manifest(
        request,
        registry=registry,
        context=GraphicsSceneContext(source_identity="abc"),
        source_descriptors=({"path": "traj.dump", "sha256": "abc"},),
        resolved_input_format="lammps-dump",
    )
    assert manifest_a.manifest_id == manifest_b.manifest_id
    payload = manifest_a.to_json_dict()
    assert [layer.name for layer in payload["ordered_layer_requests"]] == [
        "trajectory",
        "density",
    ]


def test_renderer_neutral_point_primitive_is_immutable() -> None:
    values = np.asarray([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    points = PointSet3D(owner_layer="Na", primitive_id="atoms", positions=values)
    values[0, 0] = 99.0
    assert points.positions[0, 0] == 1.0
    assert not points.positions.flags.writeable
    with pytest.raises(ValueError):
        points.positions[0, 0] = 2.0


def _small_collection() -> AtomisticFrameCollection:
    frac = np.asarray(
        [
            [
                [0.10, 0.10, 0.10],
                [0.20, 0.10, 0.10],
                [0.30, 0.10, 0.10],
                [0.80, 0.50, 0.50],
            ],
            [
                [0.10, 0.10, 0.10],
                [0.20, 0.10, 0.10],
                [0.30, 0.10, 0.10],
                [0.82, 0.50, 0.50],
            ],
        ]
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
            source_format="synthetic-gfx3d",
            source_files=("synthetic",),
            velocity_source="synthetic",
            coordinate_normalization="time_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def _small_topology(collection: AtomisticFrameCollection):
    connectivity = DistanceConnectivity(
        cutoffs=PairCutoffRegistry.from_mapping({("Si", "O"): 2.1, ("Al", "O"): 2.1})
    )
    state = compute_atomic_connectivity(collection, connectivity).states[0]
    mapping = FrameworkMapping.from_symbol_roles(
        {
            "Si": FrameworkAtomRole.VERTEX,
            "Al": FrameworkAtomRole.VERTEX,
            "O": FrameworkAtomRole.LINKER,
            "Na": FrameworkAtomRole.SPECTATOR,
        },
        path_rules=(FrameworkPathRule.from_symbols("T-O-T", ("O",), edge_kind="oxygen_bridge"),),
    )
    return build_framework_topology(state, mapping)


def test_current_framework_dynamics_scene_adapts_without_recomputing_science() -> None:
    collection = _small_collection()
    scene = prepare_framework_dynamics_scene(collection, _small_topology(collection))
    adapted = adapt_framework_dynamics_scene(scene)
    assert tuple(layer.request.name for layer in adapted.layers) == ("framework",)
    assert adapted.layers[0].product_refs["mean_framework"] is scene.mean_framework
    assert adapted.display_gauge["cell"] is not scene.display_cell
    np.testing.assert_array_equal(adapted.display_gauge["cell"], scene.display_cell)
    assert adapted.manifest.request.layers[0].layer_type == "framework"


def test_current_framework_dynamics_render_result_adapts_to_layer_keyed_result() -> None:
    collection = _small_collection()
    scene = prepare_framework_dynamics_scene(collection, _small_topology(collection))
    legacy = plot_framework_dynamics_3d(scene)
    adapted = adapt_framework_dynamics_render_result(legacy)
    assert adapted.artifact is legacy.figure
    assert tuple(adapted.layer_results) == ("framework",)
    framework = adapted.layer_results["framework"]
    assert framework.scientific_identity == adapted.scene.layers[0].scientific_identity
    assert framework.backend_object_indices
