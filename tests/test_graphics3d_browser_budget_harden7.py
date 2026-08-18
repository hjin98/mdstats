from __future__ import annotations

from dataclasses import replace

import numpy as np

from mdstats.graphics3d import (
    GraphicsLayer3DRequest,
    GraphicsScene3DRequest,
    GraphicsSceneContext,
    GraphicsSelection,
    TriangleMesh3D,
    prepare_graphics3d_scene,
)
from mdstats.plotting import BrowserMeshBudget, BrowserMeshProfile
from mdstats.plotting.density_mesh_simplify import MeshSimplificationOptions
from mdstats.plotting.density_scene_budget import (
    DensitySceneAllocationOptions,
    DensitySceneShellRequest,
    allocate_density_scene_budget,
)
from tests.test_graphics3d_layers import full_legacy_scene


def _density_scene(full_legacy_scene, *, count: int = 1):
    request = GraphicsScene3DRequest(
        layers=tuple(
            GraphicsLayer3DRequest(
                name=f"density-{index}",
                layer_type="density",
                selection=GraphicsSelection(species=("Na",)),
            )
            for index in range(count)
        )
    )
    return prepare_graphics3d_scene(
        request,
        context=GraphicsSceneContext(
            source=full_legacy_scene,
            source_identity="gfx3d-browser-budget-harden7",
        ),
    )


def test_scene_density_allocator_is_shared_across_duplicate_density_layers(full_legacy_scene):
    import mdstats.graphics3d.plotly_renderer as renderer

    scene = _density_scene(full_legacy_scene, count=4)
    profile = BrowserMeshProfile.balanced()
    resources = renderer._density_scene_render_resources(
        scene,
        shifts=((0, 0, 0),),
        mesh_profile=profile,
    )
    plan = resources["density_scene_budget_plan"]
    assert len(plan.allocations) == 12
    assert plan.allocated_serialized_faces <= profile.budget.max_final_density_faces
    # The old GFX3D path handed every shell the standalone 250k target.  A
    # four-field scene must instead receive a true shared allocation.
    assert max(item.target_canonical_faces for item in plan.allocations) < 250_000


def test_density_layer_consumes_scene_allocated_target(full_legacy_scene, monkeypatch):
    import mdstats.graphics3d.layers as layers
    import mdstats.plotting.density_sparse_mesh as sparse_mesh
    from mdstats.graphics3d.contracts import PreparedGraphicsLayer3D
    from mdstats.plotting.density_contracts import (
        DensitySourceProvenance,
        PeriodicWeightedSamples3D,
    )
    from mdstats.plotting.density_packed_field import pack_sparse_reference_field
    from mdstats.plotting.density_sparse_reference import prepare_sparse_canonical_density_reference

    batch = PeriodicWeightedSamples3D(
        fractional_positions=np.asarray([[0.46, 0.51, 0.54]], dtype=np.float64),
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
        scientific_identity="packed-scene-budget",
        product_refs={"density_field": packed},
    )
    requests = tuple(
        DensitySceneShellRequest(
            shell_key=f"Na density:{packed.field_key}:{fraction:.12g}",
            field_key=str(packed.field_key),
            label=str(packed.label),
            mass_fraction=fraction,
            selected_node_count=packed.hdr_details(fraction).selected_node_count,
            max_canonical_faces=250_000,
        )
        for fraction in (0.5, 0.8)
    )
    budget = BrowserMeshBudget(
        max_final_density_faces=20_000,
        max_final_density_vertices=20_000,
        max_final_html_bytes=16 * 1024**2,
        max_plotly_traces=64,
    )
    plan = allocate_density_scene_budget(
        requests,
        budget=budget,
        options=DensitySceneAllocationOptions(min_canonical_faces_per_shell=100),
    )
    captured: list[tuple[int, int | None]] = []
    original = sparse_mesh.prepare_sparse_density_mesh

    def wrapped(*args, **kwargs):
        contract = kwargs["face_contract"]
        simplification = kwargs.get("simplification_options")
        captured.append(
            (
                int(contract.visual_target_faces),
                None if simplification is None else int(simplification.target_faces),
            )
        )
        return original(*args, **kwargs)

    monkeypatch.setattr(sparse_mesh, "prepare_sparse_density_mesh", wrapped)
    context = GraphicsSceneContext(
        source_identity="packed-scene-budget",
        resources={
            "mesh_profile": BrowserMeshProfile.custom(budget),
            "density_scene_budget_plan": plan,
            "density_mesh_simplification_options": MeshSimplificationOptions(hard_target=False),
        },
    )
    primitives = layers._density_render_primitives(prepared, context)
    assert primitives
    targets = [item.target_canonical_faces for item in plan.allocations]
    assert [value[0] for value in captured] == targets
    assert [value[1] for value in captured] == targets


def test_custom_density_face_budget_propagates_to_universal_browser_cap(full_legacy_scene, monkeypatch):
    import mdstats.graphics3d.plotly_renderer as renderer

    scene = _density_scene(full_legacy_scene)
    # Deliberately make the generic face cap smaller than the tiny test density
    # mesh.  The custom density budget must enlarge the universal cap too.
    monkeypatch.setattr(
        renderer.GraphicsBrowserBudget,
        "for_profile",
        classmethod(
            lambda cls, _profile: renderer.GraphicsBrowserBudget(
                max_traces=512,
                max_points=5_000_000,
                max_faces=1_000,
                max_geometry_bytes=512 * 1024 * 1024,
            )
        ),
    )
    profile = BrowserMeshProfile.custom(
        BrowserMeshBudget(
            max_final_density_faces=20_000,
            max_final_density_vertices=20_000,
            max_final_html_bytes=20 * 1024**2,
            max_plotly_traces=64,
        )
    )
    rendered = renderer.render_graphics3d_plotly(scene, mesh_profile=profile)
    assert rendered.render_metadata["browser_payload"]["face_count"] > 1_000
    assert rendered.render_metadata["browser_budget"]["max_faces"] == 20_000


def test_aggregate_overspend_invokes_scene_fitter(full_legacy_scene, monkeypatch):
    import mdstats.graphics3d.plotly_renderer as renderer
    import mdstats.plotting.density_scene_fit as scene_fit

    scene = _density_scene(full_legacy_scene)
    layer = scene.layers[0]
    field = layer.product_refs["density_field"]
    # Create one deliberately overspending but structurally simple primitive.
    vertices = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64)
    faces = np.tile(np.asarray([[0, 1, 2]], dtype=np.int64), (6_000, 1))
    primitive = TriangleMesh3D(
        owner_layer=layer.request.name,
        primitive_id="density-shell-0",
        vertices=vertices,
        faces=faces,
        scientific_refs=(layer.scientific_identity,),
        render_attributes={"mass_fraction": 0.5, "hdr_threshold": 1.0},
    )
    profile = BrowserMeshProfile.custom(
        BrowserMeshBudget(
            max_final_density_faces=5_000,
            max_final_density_vertices=5_000,
            max_final_html_bytes=20 * 1024**2,
            max_plotly_traces=64,
        )
    )
    called = {"value": False}

    def fake_fit(geometries, **kwargs):
        called["value"] = True
        geometry = geometries[0]
        reduced = geometry.with_geometry(
            geometry.vertices_fractional,
            geometry.vertices_cartesian,
            geometry.faces[:4_000],
            source_kind="test_scene_fit",
        )
        report = type("Report", (), {"to_json_dict": lambda self: {"passed": True}})()
        return (reduced,), report

    monkeypatch.setattr(scene_fit, "fit_density_scene_to_browser_budget", fake_fit)
    updated, report = renderer._fit_density_primitives_to_scene_budget(
        {layer.request.name: (primitive,)},
        scene,
        shifts=((0, 0, 0),),
        mesh_profile=profile,
    )
    assert called["value"] is True
    assert report is not None
    reduced = updated[layer.request.name][0]
    assert isinstance(reduced, TriangleMesh3D)
    assert reduced.faces.shape[0] == 4_000
    assert reduced.render_attributes["scene_fit_applied"] is True


def test_cli_face_override_scales_companion_density_budgets(full_legacy_scene, monkeypatch):
    import mdstats.graphics3d.cli as cli

    scene = _density_scene(full_legacy_scene)
    captured = {}

    def fake_render(scene_arg, *, mesh_profile):
        captured["profile"] = mesh_profile
        return type("Result", (), {"artifact": type("Artifact", (), {"update_layout": lambda *args, **kwargs: None})()})()

    monkeypatch.setattr(cli, "render_graphics3d_plotly", fake_render)
    request = type("Request", (), {"scene_options": {}})()
    cli._render_output(scene, request, browser_profile="balanced", max_browser_faces=1_200_000)
    budget = captured["profile"].budget
    assert budget.max_final_density_faces == 1_200_000
    assert budget.max_final_density_vertices >= 900_000
    assert budget.max_final_html_bytes >= 144 * 1024**2
