"""Focused Stage-11E0a scientific density facade and ownership tests."""

from __future__ import annotations

import builtins
import json
import numpy as np
import pytest

import mdstats
from mdstats import AtomisticFrameCollection, FrameCollectionProvenance, FrameSemantics
from mdstats.analysis.density import (
    SCIENTIFIC_DENSITY_FACADE_STAGE,
    ScientificDensityField3D,
    ScientificDensityFieldAdapter,
    ScientificDensityResourcePolicy,
    adapt_scientific_density_field,
    prepare_atomic_density_fields as prepare_analysis_atomic_density_fields,
    prepare_framework_density_fields as prepare_analysis_framework_density_fields,
)
from mdstats.plotting.atomic_density import (
    AtomicDensityOptions,
    AtomicDensitySelection,
    prepare_atomic_density_fields as prepare_legacy_atomic_density_fields,
)
from mdstats.plotting.density_contracts import (
    DENSE_BACKEND,
    DensitySourceProvenance,
    DensityStorageOptions,
    GAUSSIAN_SIGMA_BROADENING,
    PeriodicWeightedSamples3D,
)
from mdstats.plotting.density_block_sparse import pack_sparse_reference_blocks
from mdstats.plotting.density_mesh_contracts import legacy_standalone_face_contract
from mdstats.plotting.density_sparse_reference import (
    prepare_sparse_canonical_density_reference,
)
from mdstats.plotting.density_render_budget import BrowserMeshBudget
from mdstats.plotting.density_resource_policy import DensityRenderingResourcePolicy
from mdstats.plotting.framework_density import (
    FrameworkDensityOptions,
    prepare_framework_density_fields as prepare_legacy_framework_density_fields,
)


def make_collection() -> AtomisticFrameCollection:
    fractional = np.asarray(
        [
            [[0.10, 0.20, 0.30], [0.60, 0.50, 0.40]],
            [[0.12, 0.20, 0.30], [0.62, 0.50, 0.40]],
        ],
        dtype=np.float64,
    )
    n_frames, n_atoms, _ = fractional.shape
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.asarray([11, 8], dtype=np.int32),
        masses=np.asarray([22.989769, 15.999], dtype=np.float64),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.arange(n_frames, dtype=np.float64),
        cells=np.repeat((np.eye(3) * 8.0)[None, :, :], n_frames, axis=0),
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=fractional,
        velocities=np.zeros((n_frames, n_atoms, 3), dtype=np.float64),
        provenance=FrameCollectionProvenance(
            source_format="synthetic-e0a",
            source_files=("synthetic",),
            velocity_source="synthetic",
            coordinate_normalization="time_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def scientific_resources() -> ScientificDensityResourcePolicy:
    return ScientificDensityResourcePolicy(
        max_fields=4,
        max_total_voxels=100_000,
        max_samples=100_000,
        max_nonzero_nodes=100_000,
        max_stored_block_values=100_000,
        max_blocks=10_000,
        max_kernel_pairs=5_000_000,
        max_planning_bytes=64 * 1024**2,
        max_workspace_bytes=64 * 1024**2,
        max_cic_contributions=5_000_000,
        max_memory_bytes=128 * 1024**2,
        max_threads=2,
        max_wall_time_seconds=120.0,
        metadata={"fixture": "stage11e0a"},
    )


def atomic_options() -> AtomicDensityOptions:
    return AtomicDensityOptions(
        grid_shape=(8, 8, 8),
        gaussian_bandwidth=2.00,
        adaptive_smearing=False,
        storage_options=DensityStorageOptions(grid_backend=DENSE_BACKEND),
    )


def framework_options() -> FrameworkDensityOptions:
    return FrameworkDensityOptions(
        grid_shape=(8, 8, 8),
        gaussian_bandwidth=2.00,
        adaptive_smearing=False,
        edge_sample_spacing=0.50,
        edge_sample_spacing_mode="explicit",
        storage_options=DensityStorageOptions(grid_backend=DENSE_BACKEND),
    )


def test_scientific_and_rendering_resource_policies_are_disjoint() -> None:
    scientific = scientific_resources()
    scientific_payload = scientific.to_json_dict()
    assert scientific_payload["resource_domain"] == "scientific_density"
    assert "max_plotly_traces" not in scientific_payload
    assert "max_mesh_faces" not in scientific_payload
    assert "browser_mesh_budget" not in scientific_payload
    assert scientific.metadata["fixture"] == "stage11e0a"
    with pytest.raises(TypeError):
        scientific.metadata["x"] = 1  # type: ignore[index]

    rendering = DensityRenderingResourcePolicy(
        browser_mesh_budget=BrowserMeshBudget(),
        mesh_face_contract=legacy_standalone_face_contract(
            max_faces=20_000, max_raw_faces=40_000
        ),
        cloud_max_points=10_000,
    )
    rendering_payload = rendering.to_json_dict()
    assert rendering_payload["resource_domain"] == "density_rendering"
    assert rendering_payload["scientific_limits_present"] is False
    assert "max_total_voxels" not in rendering_payload

    from mdstats.analysis.density import resolve_scientific_density_resources

    with pytest.raises(TypeError):
        resolve_scientific_density_resources(rendering)  # type: ignore[arg-type]


def test_zero_copy_adapter_satisfies_analysis_protocol() -> None:
    collection = make_collection()
    policy = scientific_resources()
    kwargs = policy.to_legacy_keyword_arguments()
    legacy = prepare_legacy_atomic_density_fields(
        collection,
        frame_indices=(0, 1),
        frame_weights=np.asarray([0.5, 0.5]),
        display_cell=np.eye(3) * 8.0,
        registration_mode="material",
        framework_drift=np.zeros((2, 3)),
        selections=(AtomicDensitySelection(atom_indices=(0,), label="Na"),),
        options=atomic_options(),
        **kwargs,
    )[0]
    adapter = adapt_scientific_density_field(
        legacy,
        numerical_owner="mdstats.plotting.atomic_density",
        metadata={"test": "zero_copy"},
    )
    assert isinstance(adapter, ScientificDensityFieldAdapter)
    assert isinstance(adapter, ScientificDensityField3D)
    assert adapter.legacy_field is legacy
    assert adapter.display_cell is legacy.display_cell
    assert adapter.metadata is legacy.metadata
    assert adapter.field_key == legacy.field_key
    assert adapter.integral == pytest.approx(legacy.integral, abs=0.0)
    np.testing.assert_array_equal(
        adapter.gather_node_values(np.asarray([[0, 0, 0], [1, 2, 3]])),
        legacy.gather_node_values(np.asarray([[0, 0, 0], [1, 2, 3]])),
    )
    json.dumps(adapter.to_json_dict(), allow_nan=False)




def test_zero_copy_adapter_accepts_block_sparse_scientific_field() -> None:
    samples = PeriodicWeightedSamples3D(
        fractional_positions=np.asarray(
            [[0.113, 0.287, 0.619], [0.913, 0.887, 0.019]],
            dtype=np.float64,
        ),
        weights=np.asarray([0.35, 0.65], dtype=np.float64),
        source_provenance=DensitySourceProvenance(
            source_kind="atomic_occupancy", atom_indices=(0, 1)
        ),
        total_measure=1.0,
        measure_kind="occupancy",
        measure_units="count",
    )
    reference = prepare_sparse_canonical_density_reference(
        samples,
        grid_shape=(10, 9, 7),
        display_cell=np.asarray(
            [[5.0, 0.0, 0.0], [1.2, 4.5, 0.0], [0.7, 0.4, 3.8]],
            dtype=np.float64,
        ),
        gaussian_bandwidth=0.36,
        field_key="atomic-density-sparse",
        label="sparse density",
        physical_units="angstrom^-3",
        broadening_metric=GAUSSIAN_SIGMA_BROADENING,
        max_workspace_bytes=64 * 1024**2,
    )
    legacy = pack_sparse_reference_blocks(
        reference,
        block_shape=(4, 4, 4),
        selected_atom_indices=(0, 1),
        max_stored_block_values=100_000,
    )
    adapter = adapt_scientific_density_field(
        legacy, numerical_owner="mdstats.plotting.density_block_sparse"
    )
    assert isinstance(adapter, ScientificDensityField3D)
    assert adapter.legacy_field is legacy
    assert adapter.storage_backend == legacy.storage_backend
    assert adapter.integral == pytest.approx(1.0, abs=5.0e-13)
    queries = np.asarray([[0, 0, 0], [-1, -1, -1], [10, 9, 7]])
    np.testing.assert_array_equal(
        adapter.gather_node_values(queries), legacy.gather_node_values(queries)
    )

def test_atomic_facade_matches_current_numerical_oracle() -> None:
    collection = make_collection()
    policy = scientific_resources()
    common = dict(
        frame_indices=(0, 1),
        frame_weights=np.asarray([0.25, 0.75]),
        display_cell=np.eye(3) * 8.0,
        registration_mode="material",
        framework_drift=np.zeros((2, 3)),
        selections=(AtomicDensitySelection(atom_indices=(0,), label="Na"),),
        options=atomic_options(),
    )
    legacy = prepare_legacy_atomic_density_fields(
        collection,
        **common,
        **policy.to_legacy_keyword_arguments(),
    )
    result = prepare_analysis_atomic_density_fields(
        collection,
        **common,
        resources=policy,
    )
    assert result.metadata["facade_stage"] == SCIENTIFIC_DENSITY_FACADE_STAGE
    assert result.metadata["rendering_policy_consumed"] is False
    assert result.metadata["mesh_constructed"] is False
    assert result.metadata["browser_budget_consumed"] is False
    assert result.resource_signature == policy.signature
    assert result.field_keys == ("atomic-density-0",)
    adapted = result.fields[0]
    np.testing.assert_array_equal(adapted.legacy_field.values, legacy[0].values)
    assert adapted.integral == pytest.approx(1.0, abs=2.0e-12)
    assert result.unwrap_legacy_fields()[0] is adapted.legacy_field
    assert result.signature == prepare_analysis_atomic_density_fields(
        collection,
        **common,
        resources=policy,
    ).signature


def test_framework_facade_matches_current_numerical_oracle() -> None:
    policy = scientific_resources()
    vertices = np.asarray(
        [
            [[0.10, 0.10, 0.10], [0.40, 0.10, 0.10]],
            [[0.11, 0.10, 0.10], [0.41, 0.10, 0.10]],
        ],
        dtype=np.float64,
    )
    segments = np.asarray(
        [
            [[[0.10, 0.10, 0.10], [0.40, 0.10, 0.10]]],
            [[[0.11, 0.10, 0.10], [0.41, 0.10, 0.10]]],
        ],
        dtype=np.float64,
    )
    common = dict(
        vertex_fractional_by_frame=vertices,
        vertex_atom_indices=(0, 1),
        edge_segments_fractional_by_frame=segments,
        edge_atom_indices=(0, 1),
        frame_weights=np.asarray([0.5, 0.5]),
        display_cell=np.eye(3) * 8.0,
        registration_mode="material",
        options=framework_options(),
        consumer_registration_signature="synthetic-registration",
        scientific_drift_owner="mdstats.coordinates.consumer_adapters",
    )
    legacy = prepare_legacy_framework_density_fields(
        **common,
        **policy.to_legacy_keyword_arguments(),
    )
    result = prepare_analysis_framework_density_fields(
        **common,
        resources=policy,
    )
    assert result.field_keys == tuple(field.field_key for field in legacy.fields)
    assert result.metadata["edge_source"] == "projected"
    assert result.metadata["rendering_policy_consumed"] is False
    for adapted, expected in zip(result.fields, legacy.fields, strict=True):
        assert adapted.legacy_field.physical_units == expected.physical_units
        np.testing.assert_array_equal(adapted.legacy_field.values, expected.values)
        assert adapted.integral == pytest.approx(expected.integral, abs=2.0e-12)


def test_facade_does_not_invoke_plotly_mesh_or_browser_admission(monkeypatch: pytest.MonkeyPatch) -> None:
    collection = make_collection()
    policy = scientific_resources()

    original_import = builtins.__import__

    def guarded_import(name: str, *args, **kwargs):
        if name.startswith("plotly") or name.startswith("skimage"):
            raise AssertionError(f"Scientific density attempted optional rendering import: {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    import mdstats.plotting.density_render_budget as render_budget

    monkeypatch.setattr(
        render_budget,
        "require_browser_mesh_budget",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Scientific facade invoked browser admission")
        ),
    )
    result = prepare_analysis_atomic_density_fields(
        collection,
        frame_indices=(0, 1),
        frame_weights=np.asarray([0.5, 0.5]),
        display_cell=np.eye(3) * 8.0,
        registration_mode="material",
        framework_drift=np.zeros((2, 3)),
        selections=(AtomicDensitySelection(atom_indices=(0,)),),
        options=atomic_options(),
        resources=policy,
    )
    assert len(result.fields) == 1


def test_canonical_exports_do_not_expose_render_options() -> None:
    import mdstats.analysis.density as density

    assert density.AtomicDensityOptions is AtomicDensityOptions
    assert density.FrameworkDensityOptions is FrameworkDensityOptions
    assert not hasattr(density, "AtomicDensity3DRenderOptions")
    assert not hasattr(density, "FrameworkDensity3DRenderOptions")
    assert mdstats.prepare_scientific_atomic_density_fields is prepare_analysis_atomic_density_fields
    assert mdstats.prepare_scientific_framework_density_fields is prepare_analysis_framework_density_fields
    assert mdstats.ScientificDensityResourcePolicy is ScientificDensityResourcePolicy
    assert mdstats.DensityRenderingResourcePolicy is DensityRenderingResourcePolicy
