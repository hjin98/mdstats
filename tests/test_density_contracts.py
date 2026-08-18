from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import numpy as np
import pytest

from mdstats.plotting import (
    AUTO_BACKEND,
    DISCRETE_PERIODIZED_OPERATOR,
    EFFECTIVE_CIC_STENCIL_BROADENING,
    LEGACY_SPECTRAL_OPERATOR,
    DensePeriodicNodeFieldAdapter,
    DensityKernelOptions,
    DensityRenderOptions,
    DensityResolutionOptions,
    DensitySourceProvenance,
    DensityStorageOptions,
    DensityStorageSummary,
    FrozenJSONMapping,
    PeriodicNodeFieldAccess,
    PeriodicScalarField3D,
    PeriodicWeightedSamples3D,
    ScalarField3D,
    canonical_source_key,
)
from mdstats.plotting.atomic_density import (
    AtomicDensity3DRenderOptions,
    AtomicDensityOptions,
)
from mdstats.plotting.framework_density import FrameworkDensityOptions
from mdstats.plotting.graph_errors import GraphAdapterError, GraphUnsupportedFeatureError


def _field() -> PeriodicScalarField3D:
    values = np.arange(24, dtype=np.float64).reshape(2, 3, 4)
    values /= values.sum()
    values *= 24.0
    return PeriodicScalarField3D(
        field_key="test-density",
        label="test density",
        values=values,
        display_cell=np.diag([2.0, 3.0, 4.0]),
        total_measure=24.0,
        selected_atom_indices=(1, 3),
        gaussian_bandwidth=0.4,
        metadata={
            "schema_version": "mdstats.test-density.v1",
            "source_kind": "atomic_occupancy",
            "physical_units": "angstrom^-3",
            "nested": {"values": [1, 2, 3]},
        },
    )


def test_shared_options_normalize_legacy_wrappers() -> None:
    resolution = DensityResolutionOptions(
        grid_shape=(12, 14, 16),
        grid_interval=0.03,
        gaussian_bandwidth=0.2,
        gaussian_to_grid_ratio=2.5,
        adaptive_smearing=False,
        max_smearing_to_sample_sd_ratio=0.4,
        sample_sd_quantile=0.25,
    )
    atomic = AtomicDensityOptions(resolution_options=resolution)
    framework = FrameworkDensityOptions(resolution_options=resolution)

    for options in (atomic, framework):
        assert options.resolution_options == resolution
        assert options.grid_shape == (12, 14, 16)
        assert options.grid_interval == pytest.approx(0.03)
        assert options.gaussian_bandwidth == pytest.approx(0.2)
        assert options.gaussian_to_grid_ratio == pytest.approx(2.5)
        assert options.adaptive_smearing is False
        assert options.max_smearing_to_sample_sd_ratio == pytest.approx(0.4)
        assert options.sample_sd_quantile == pytest.approx(0.25)

    shared_render = DensityRenderOptions(
        mass_fractions=(0.4, 0.7, 0.9),
        render_mode="voxel_cloud",
        display_replication="match_graph",
        max_mesh_faces=1234,
        cloud_max_points=567,
    )
    render = AtomicDensity3DRenderOptions(render_options=shared_render)
    assert render.mass_fractions == shared_render.mass_fractions
    assert render.render_mode == "voxel_cloud"
    assert render.max_mesh_faces == 1234
    assert render.cloud_max_points == 567
    assert render.render_options == shared_render


def test_default_density_policy_is_canonical_and_automatic() -> None:
    for options in (AtomicDensityOptions(), FrameworkDensityOptions()):
        assert (
            options.kernel_options.smoothing_operator
            == DISCRETE_PERIODIZED_OPERATOR
        )
        assert options.storage_options.grid_backend == AUTO_BACKEND


def test_reserved_identifiers_are_explicitly_rejected() -> None:
    canonical = AtomicDensityOptions()
    assert (
        canonical.kernel_options.smoothing_operator
        == DISCRETE_PERIODIZED_OPERATOR
    )
    with pytest.raises(GraphUnsupportedFeatureError, match="requires"):
        AtomicDensityOptions(
            resolution_options=DensityResolutionOptions(
                broadening_metric=EFFECTIVE_CIC_STENCIL_BROADENING
            ),
            kernel_options=DensityKernelOptions(
                smoothing_operator=LEGACY_SPECTRAL_OPERATOR
            ),
            storage_options=DensityStorageOptions(grid_backend="dense"),
        )
    effective = AtomicDensityOptions(
        resolution_options=DensityResolutionOptions(
            broadening_metric=EFFECTIVE_CIC_STENCIL_BROADENING
        ),
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
    )
    assert (
        effective.resolution_options.broadening_metric
        == EFFECTIVE_CIC_STENCIL_BROADENING
    )
    with pytest.raises(GraphUnsupportedFeatureError, match="requires"):
        AtomicDensityOptions(
            kernel_options=DensityKernelOptions(
                smoothing_operator=LEGACY_SPECTRAL_OPERATOR
            ),
            storage_options=DensityStorageOptions(grid_backend=AUTO_BACKEND),
        )
    automatic = AtomicDensityOptions(
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
        storage_options=DensityStorageOptions(grid_backend=AUTO_BACKEND),
    )
    assert automatic.storage_options.grid_backend == AUTO_BACKEND


def test_provenance_and_source_keys_round_trip_canonically() -> None:
    provenance = DensitySourceProvenance(
        source_kind="framework_edge_length",
        atom_indices=(5, 2, 5),
        vertex_keys=(
            ("vertex", "T", 4, ("shift", 0, 1, -1)),
            ("vertex", "T", 1, ("shift", 0, 0, 0)),
        ),
        edge_keys=(
            ("edge", ("node", 2), ("node", 9), ("shift", 1, 0, 0), 3),
        ),
        metadata={"mode": "projected", "nested": {"ok": True}},
    )
    payload = provenance.to_json_dict()
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    restored = DensitySourceProvenance.from_json_dict(json.loads(encoded))

    assert restored == provenance
    assert restored.atom_indices == (2, 5)
    assert restored.vertex_keys[0] == canonical_source_key(
        ("vertex", "T", 1, ("shift", 0, 0, 0))
    )
    assert isinstance(restored.metadata, FrozenJSONMapping)


def test_weighted_samples_are_read_only_and_round_trip() -> None:
    samples = PeriodicWeightedSamples3D(
        fractional_positions=np.array([[0.1, 0.2, 0.3], [0.9, 0.8, 0.7]]),
        weights=np.array([0.4, 0.6]),
        sample_group_ids=np.array([3, 3]),
        source_provenance=DensitySourceProvenance(
            source_kind="atomic_occupancy", atom_indices=(3,)
        ),
        total_measure=1.0,
        measure_kind="occupancy",
        measure_units="count",
        metadata={"registration": "material"},
    )
    assert not samples.fractional_positions.flags.writeable
    assert not samples.weights.flags.writeable
    assert samples.sample_group_ids is not None
    assert not samples.sample_group_ids.flags.writeable
    with pytest.raises(ValueError):
        samples.weights[0] = 0.5

    restored = PeriodicWeightedSamples3D.from_json_dict(samples.to_json_dict())
    np.testing.assert_array_equal(restored.fractional_positions, samples.fractional_positions)
    np.testing.assert_array_equal(restored.weights, samples.weights)
    np.testing.assert_array_equal(restored.sample_group_ids, samples.sample_group_ids)
    assert restored.source_provenance == samples.source_provenance
    assert restored.metadata == samples.metadata

    with pytest.raises(GraphAdapterError, match="sum"):
        PeriodicWeightedSamples3D(
            fractional_positions=np.array([[0.1, 0.2, 0.3]]),
            weights=np.array([0.5]),
            source_provenance=samples.source_provenance,
            total_measure=1.0,
            measure_kind="occupancy",
            measure_units="count",
        )


def test_dense_field_satisfies_protocols_and_public_node_access() -> None:
    field = _field()
    assert isinstance(field, ScalarField3D)
    assert isinstance(field, PeriodicNodeFieldAccess)
    assert field.storage_backend == "dense"
    assert field.smoothing_operator == "legacy_spectral_v1"
    assert field.broadening_metric == "gaussian_sigma_v1"
    assert field.physical_units == "angstrom^-3"
    assert field.source_provenance.atom_indices == (1, 3)

    batches = list(field.iter_stored_nodes(batch_size=5))
    indices = np.concatenate([item[0] for item in batches], axis=0)
    values = np.concatenate([item[1] for item in batches], axis=0)
    expected_indices = np.array(
        [[i, j, k] for i in range(2) for j in range(3) for k in range(4)],
        dtype=np.int64,
    )
    np.testing.assert_array_equal(indices, expected_indices)
    np.testing.assert_array_equal(values, field.values.ravel())
    assert all(not item[0].flags.writeable and not item[1].flags.writeable for item in batches)

    gathered = field.gather_node_values(
        np.array([[0, 0, 0], [2, -1, 5], [-1, 3, -4]], dtype=np.int64)
    )
    expected = np.array(
        [field.values[0, 0, 0], field.values[0, 2, 1], field.values[1, 0, 0]]
    )
    np.testing.assert_array_equal(gathered, expected)
    assert not gathered.flags.writeable


def test_dense_adapter_is_zero_copy_and_storage_summary_round_trips() -> None:
    field = _field()
    adapter = DensePeriodicNodeFieldAdapter.from_field(field)
    assert adapter.values is field.values
    assert np.shares_memory(adapter.values, field.values)

    summary = field.storage_summary()
    assert summary.logical_grid_shape == field.grid_shape
    assert summary.logical_node_count == field.values.size
    assert summary.stored_value_count == field.values.size
    assert summary.stored_block_count == 0
    assert summary.realized_bytes == field.values.nbytes
    assert DensityStorageSummary.from_json_dict(summary.to_json_dict()) == summary


def test_dense_field_json_round_trip_and_recursive_immutability() -> None:
    field = _field()
    restored = PeriodicScalarField3D.from_json_dict(field.to_json_dict())
    np.testing.assert_array_equal(restored.values, field.values)
    np.testing.assert_array_equal(restored.display_cell, field.display_cell)
    assert restored.field_key == field.field_key
    assert restored.source_provenance == field.source_provenance
    assert restored.metadata == field.metadata
    assert restored.integral == pytest.approx(field.integral, rel=0.0, abs=1.0e-14)

    with pytest.raises(ValueError):
        restored.values[0, 0, 0] = 1.0
    with pytest.raises(TypeError):
        restored.metadata["new"] = 1  # type: ignore[index]
    nested = restored.metadata["nested"]
    assert isinstance(nested, FrozenJSONMapping)
    with pytest.raises(TypeError):
        nested["new"] = 1  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        restored.total_measure = 1.0  # type: ignore[misc]



def test_shared_option_records_round_trip_all_schema_fields() -> None:
    records = (
        DensityResolutionOptions(
            grid_shape=(8, 10, 12),
            grid_interval=0.17,
            gaussian_bandwidth=0.31,
            gaussian_to_grid_ratio=1.9,
            adaptive_smearing=False,
            max_smearing_to_sample_sd_ratio=0.45,
            sample_sd_quantile=0.2,
        ),
        DensityKernelOptions(
            kernel_tail_tolerance=1.0e-9, metadata={"policy": "reserved"}
        ),
        DensityStorageOptions(
            local_block_shape=(8, 12, 16),
            sparse_activation_fraction=0.3,
            metadata={"phase": "LD0-R1"},
        ),
        DensityRenderOptions(
            mass_fractions=(0.25, 0.5, 0.9),
            render_mode="voxel_cloud",
            display_replication="match_graph",
            max_mesh_faces=321,
            cloud_max_points=654,
            metadata={"mode": "test"},
        ),
    )
    for record in records:
        payload = json.loads(json.dumps(record.to_json_dict(), sort_keys=True))
        restored = type(record).from_json_dict(payload)
        assert restored == record

def test_scientific_contract_module_has_no_plotly_dependency() -> None:
    module_path = Path(__file__).parents[1] / "mdstats" / "plotting" / "density_contracts.py"
    source = module_path.read_text(encoding="utf-8")
    assert "import plotly" not in source
    assert "from plotly" not in source
