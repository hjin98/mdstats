"""Stage 11E-GR2 plotting adaptation and compatibility tests."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    AtomicDensityOptions,
    AtomicDensitySelection,
    DENSE_BACKEND,
    DensityStorageOptions,
    FrameCollectionProvenance,
    FrameSemantics,
    FrameworkDensityOptions,
)
from mdstats.plotting import (
    DensityVisualGridAdaptation,
    GraphAdapterError,
    prepare_density_visual_grid_adaptation,
)
from mdstats.plotting.atomic_density import (
    prepare_atomic_density_fields,
    resolve_density_numerics,
)
from mdstats.plotting.framework_density import prepare_framework_density_fields

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DENSITY = ROOT / "mdstats" / "analysis" / "density"


def skew_cell() -> np.ndarray:
    return np.asarray(
        [[6.0, 0.0, 0.0], [2.1, 5.4, 0.0], [1.3, 0.8, 4.9]],
        dtype=np.float64,
    )


def samples() -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(
        [
            [[0.12, 0.18, 0.21], [0.72, 0.61, 0.54]],
            [[0.13, 0.17, 0.22], [0.71, 0.62, 0.53]],
            [[0.11, 0.19, 0.20], [0.73, 0.60, 0.55]],
            [[0.14, 0.16, 0.23], [0.70, 0.63, 0.52]],
        ],
        dtype=np.float64,
    )
    return values, np.full(values.shape[0], 1.0 / values.shape[0])


def resolved(options: AtomicDensityOptions, *, max_voxels: int = 1_000_000):
    positions, weights = samples()
    return resolve_density_numerics(
        skew_cell(),
        options=options,
        fractional_by_frame=positions,
        frame_weights=weights,
        pbc=np.ones(3, dtype=bool),
        max_voxels=max_voxels,
        field_label="GR2 test density",
    )


def test_explicit_grid_adaptation_uses_gr0_without_gr1_search() -> None:
    options = AtomicDensityOptions(
        grid_shape=(13, 12, 11),
        gaussian_bandwidth=0.27,
        adaptive_smearing=False,
    )
    numerics = resolved(options)
    adaptation = prepare_density_visual_grid_adaptation(
        skew_cell(),
        options=options,
        resolved_numerics=numerics,
        max_logical_voxels=1_000_000,
        consumer_kind="atomic",
        resolution_reference_source="atomic_samples",
    )
    assert adaptation.grid_shape == (13, 12, 11)
    assert adaptation.common_grid_plan is None
    assert adaptation.grid_definition == "explicit_shape"
    assert adaptation.grid_metadata_dict() == {
        "grid_definition": "explicit_shape",
        "grid_shape": (13, 12, 11),
        "logical_node_count": 13 * 12 * 11,
        "grid_interval_target": options.grid_interval,
        "grid_intervals_realized": numerics.realized_intervals,
    }


def test_automatic_grid_adaptation_replays_exact_gr1_grid() -> None:
    options = AtomicDensityOptions(
        grid_interval=0.55,
        adaptive_smearing=False,
    )
    numerics = resolved(options)
    adaptation = prepare_density_visual_grid_adaptation(
        skew_cell(),
        options=options,
        resolved_numerics=numerics,
        max_logical_voxels=1_000_000,
        consumer_kind="framework",
        resolution_reference_source="framework_vertices",
    )
    assert adaptation.common_grid_plan is not None
    assert adaptation.common_grid_plan.selected_geometry.grid_shape == numerics.grid_shape
    assert adaptation.common_grid_plan.metadata["planner_role"] == (
        "selected_visual_grid_replay"
    )
    assert adaptation.grid_definition == "target_lattice_interval"


def test_budget_limited_visual_state_is_preserved_not_promoted() -> None:
    cell = np.diag([4.0, 4.0, 4.0])
    positions = np.asarray(
        [
            [[0.100, 0.10, 0.10]],
            [[0.101, 0.10, 0.10]],
            [[0.099, 0.10, 0.10]],
            [[0.102, 0.10, 0.10]],
        ]
    )
    weights = np.full(4, 0.25)
    options = AtomicDensityOptions(grid_interval=0.5)
    with pytest.warns(RuntimeWarning, match="Adaptive density refinement"):
        numerics = resolve_density_numerics(
            cell,
            options=options,
            fractional_by_frame=positions,
            frame_weights=weights,
            pbc=np.ones(3, dtype=bool),
            max_voxels=1_000,
            field_label="budget-limited visual density",
        )
    adaptation = prepare_density_visual_grid_adaptation(
        cell,
        options=options,
        resolved_numerics=numerics,
        max_logical_voxels=1_000,
        consumer_kind="atomic",
        resolution_reference_source="atomic_samples",
    )
    assert adaptation.adaptive_smearing_triggered
    assert adaptation.adaptive_smearing_budget_limited
    assert "visual_resolution_budget_limited" in adaptation.warning_codes
    assert adaptation.common_grid_plan is not None
    assert adaptation.common_grid_plan.target_reached
    assert adaptation.metadata.get("scientific_convergence_certificate") is None


def test_visual_metadata_reproduces_legacy_keys_and_values() -> None:
    options = AtomicDensityOptions(
        grid_shape=(12, 11, 10),
        gaussian_bandwidth=0.25,
        adaptive_smearing=False,
    )
    numerics = resolved(options)
    adaptation = prepare_density_visual_grid_adaptation(
        skew_cell(),
        options=options,
        resolved_numerics=numerics,
        max_logical_voxels=1_000_000,
        consumer_kind="atomic",
        resolution_reference_source="atomic_samples",
    )
    metadata = adaptation.visual_metadata_dict()
    assert metadata["gaussian_bandwidth"] == numerics.gaussian_bandwidth
    assert metadata["gaussian_to_grid_ratio_target"] == options.gaussian_to_grid_ratio
    assert metadata["smearing_definition"] == numerics.smearing_definition
    assert metadata["adaptive_smearing_enabled"] is options.adaptive_smearing
    assert metadata["adaptive_smearing_triggered"] is numerics.adaptive_triggered
    assert metadata["adaptive_smearing_budget_limited"] is numerics.adaptive_budget_limited
    assert metadata["adaptive_target_defined"] is numerics.adaptive_target_defined
    assert metadata["resolution_reference_source"] == "atomic_samples"
    for key, value in numerics.spread_diagnostics.metadata_dict().items():
        assert metadata[key] == value
    for key, value in numerics.reciprocal_resolution.metadata_dict().items():
        assert metadata[key] == value


def test_signed_replay_and_tamper_rejection() -> None:
    options = AtomicDensityOptions(grid_interval=0.6, adaptive_smearing=False)
    numerics = resolved(options)
    adaptation = prepare_density_visual_grid_adaptation(
        skew_cell(),
        options=options,
        resolved_numerics=numerics,
        max_logical_voxels=1_000_000,
        consumer_kind="atomic",
        resolution_reference_source="atomic_samples",
        metadata={"case": "replay"},
    )
    restored = DensityVisualGridAdaptation.from_json_dict(adaptation.to_json_dict())
    assert restored.to_json_dict() == adaptation.to_json_dict()
    tampered = adaptation.to_json_dict()
    tampered["gaussian_bandwidth"] = adaptation.gaussian_bandwidth + 0.01
    with pytest.raises(GraphAdapterError, match="signature mismatch"):
        DensityVisualGridAdaptation.from_json_dict(tampered)


def test_common_geometry_mismatch_fails_closed() -> None:
    options = AtomicDensityOptions(
        grid_shape=(10, 10, 10),
        gaussian_bandwidth=0.2,
        adaptive_smearing=False,
    )
    numerics = resolved(options)
    broken = replace(
        numerics,
        realized_intervals=(
            numerics.realized_intervals[0] + 0.01,
            numerics.realized_intervals[1],
            numerics.realized_intervals[2],
        ),
    )
    with pytest.raises(GraphAdapterError, match="disagree with common GR0"):
        prepare_density_visual_grid_adaptation(
            skew_cell(),
            options=options,
            resolved_numerics=broken,
            max_logical_voxels=1_000_000,
            consumer_kind="atomic",
            resolution_reference_source="atomic_samples",
        )


def make_collection() -> AtomisticFrameCollection:
    positions, _weights = samples()
    # two atoms are enough for the direct density producer integration test.
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(positions.shape[0], dtype=np.int64),
        atomic_numbers=np.asarray([11, 8], dtype=np.int32),
        masses=np.asarray([22.99, 16.0]),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(positions.shape[0], dtype=np.int64),
        times=np.arange(positions.shape[0], dtype=np.float64),
        cells=np.repeat(skew_cell()[None, :, :], positions.shape[0], axis=0),
        origins=np.zeros((positions.shape[0], 3)),
        fractional_positions=positions,
        velocities=np.zeros_like(positions),
        provenance=FrameCollectionProvenance(
            source_format="synthetic-gr2",
            source_files=("synthetic",),
            velocity_source="synthetic",
            coordinate_normalization="time_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def test_atomic_field_producer_invokes_gr2_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    import mdstats.plotting.atomic_density as module

    calls: list[str] = []
    original = module.prepare_density_visual_grid_adaptation

    def spy(*args, **kwargs):
        calls.append(str(kwargs["consumer_kind"]))
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "prepare_density_visual_grid_adaptation", spy)
    options = AtomicDensityOptions(
        grid_shape=(8, 8, 8),
        gaussian_bandwidth=0.2,
        adaptive_smearing=False,
        storage_options=DensityStorageOptions(grid_backend=DENSE_BACKEND),
    )
    fields = prepare_atomic_density_fields(
        make_collection(),
        frame_indices=(0, 1, 2, 3),
        frame_weights=np.full(4, 0.25),
        display_cell=skew_cell(),
        registration_mode="laboratory",
        framework_drift=np.zeros((4, 3)),
        selections=(AtomicDensitySelection(atom_indices=(0,)),),
        options=options,
        max_fields=2,
        max_total_voxels=100_000,
        max_samples=100_000,
    )
    assert calls == ["atomic"]
    field = fields[0]
    assert field.metadata["grid_shape"] == (8, 8, 8)
    assert field.metadata["gaussian_bandwidth"] == 0.2


def test_framework_field_producer_invokes_gr2_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import mdstats.plotting.framework_density as module

    calls: list[str] = []
    original = module.prepare_density_visual_grid_adaptation

    def spy(*args, **kwargs):
        calls.append(str(kwargs["consumer_kind"]))
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "prepare_density_visual_grid_adaptation", spy)
    vertices = np.asarray(
        [
            [[0.10, 0.10, 0.10], [0.30, 0.10, 0.10]],
            [[0.11, 0.10, 0.10], [0.31, 0.10, 0.10]],
        ]
    )
    segments = np.asarray(
        [
            [[[0.10, 0.10, 0.10], [0.30, 0.10, 0.10]]],
            [[[0.11, 0.10, 0.10], [0.31, 0.10, 0.10]]],
        ]
    )
    options = FrameworkDensityOptions(
        grid_shape=(8, 8, 8),
        gaussian_bandwidth=0.2,
        adaptive_smearing=False,
        edge_sample_spacing=0.2,
        storage_options=DensityStorageOptions(grid_backend=DENSE_BACKEND),
    )
    fields = prepare_framework_density_fields(
        vertex_fractional_by_frame=vertices,
        vertex_atom_indices=(0, 1),
        edge_segments_fractional_by_frame=segments,
        edge_atom_indices=(0, 1),
        frame_weights=np.asarray([0.5, 0.5]),
        display_cell=skew_cell(),
        registration_mode="laboratory",
        options=options,
        max_fields=2,
        max_total_voxels=100_000,
        max_samples=100_000,
    )
    assert calls == ["framework"]
    assert fields.vertex_density is not None
    assert fields.edge_length_density is not None
    assert fields.vertex_density.metadata["grid_shape"] == (8, 8, 8)
    assert fields.edge_length_density.metadata["grid_shape"] == (8, 8, 8)


def test_analysis_density_modules_do_not_import_plotting_policy() -> None:
    forbidden = ("mdstats.plotting", "plotly", "density_visual_policy")
    for path in ANALYSIS_DENSITY.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        assert not any(
            any(token in imported for token in forbidden) for imported in imports
        ), path.name
