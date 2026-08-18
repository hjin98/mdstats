from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from mdstats import AtomisticFrameCollection, FrameCollectionProvenance, FrameSemantics
from mdstats.plotting.atomic_density import (
    AtomicDensityOptions,
    AtomicDensitySelection,
    prepare_atomic_density_fields,
)
from mdstats.plotting.density_contracts import (
    DISCRETE_PERIODIZED_OPERATOR,
    LOCAL_SPARSE_BACKEND,
    DensityKernelOptions,
    DensityOptimizationOptions,
    DensityStorageOptions,
)
from mdstats.plotting.density_packed_field import PeriodicPackedBlockScalarField3D
from mdstats.plotting.graph_errors import GraphAdapterError, GraphComplexityError


def _collection() -> AtomisticFrameCollection:
    fractional = np.asarray(
        [
            [[0.15, 0.20, 0.25]],
            [[0.16, 0.20, 0.25]],
            [[0.17, 0.20, 0.25]],
        ],
        dtype=np.float64,
    )
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(3, dtype=np.int64),
        atomic_numbers=np.asarray([11], dtype=np.int32),
        masses=np.asarray([22.99]),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(3, dtype=np.int64),
        times=np.arange(3, dtype=np.float64),
        cells=np.repeat((np.eye(3) * 8.0)[None, :, :], 3, axis=0),
        origins=np.zeros((3, 3)),
        fractional_positions=fractional,
        velocities=np.zeros((3, 1, 3)),
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("synthetic",),
            velocity_source="synthetic",
            coordinate_normalization="time_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def _options(mode: str = "hybrid", *, fallback: bool = True) -> AtomicDensityOptions:
    return AtomicDensityOptions(
        grid_shape=(32, 32, 32),
        gaussian_bandwidth=0.45,
        adaptive_smearing=False,
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR,
            kernel_tail_tolerance=1.0e-8,
        ),
        storage_options=DensityStorageOptions(
            grid_backend=LOCAL_SPARSE_BACKEND,
            local_block_shape=(8, 8, 8),
        ),
        optimization_options=DensityOptimizationOptions(
            sparse_realization_mode=mode,
            allow_ld7_fallback=fallback,
            hybrid_compute_tile_shape=(16, 16, 16),
            hybrid_min_fft_source_nodes=2,
        ),
    )


def _prepare(options: AtomicDensityOptions):
    return prepare_atomic_density_fields(
        _collection(),
        frame_indices=(0, 1, 2),
        frame_weights=np.full(3, 1.0 / 3.0),
        display_cell=np.eye(3) * 8.0,
        registration_mode="material",
        framework_drift=np.zeros((3, 3)),
        selections=(AtomicDensitySelection(atom_indices=(0,), label="Na"),),
        options=options,
        max_fields=2,
        max_total_voxels=1,
        max_samples=100,
    )[0]


def test_normal_sparse_dispatch_uses_hybrid_and_matches_ld7() -> None:
    hybrid = _prepare(_options("hybrid"))
    legacy = _prepare(_options("ld7"))
    assert isinstance(hybrid, PeriodicPackedBlockScalarField3D)
    assert hybrid.metadata["production_backend"] is True
    assert hybrid.metadata["ld8_s4_normal_dispatch"] is True
    assert hybrid.metadata["sparse_realization_backend"] == "ld8_s3_hybrid"
    np.testing.assert_allclose(
        hybrid.to_dense_values(max_nodes=32**3),
        legacy.to_dense_values(max_nodes=32**3),
        rtol=5.0e-11,
        atol=5.0e-13,
    )


def test_complexity_failure_falls_back_only_when_authorized(monkeypatch) -> None:
    import mdstats.plotting.atomic_density as module

    def fail(*args, **kwargs):
        raise GraphComplexityError("forced planning limit")

    monkeypatch.setattr(module, "build_density_support_atlas", fail)
    fallback = _prepare(_options("hybrid", fallback=True))
    assert fallback.metadata["ld8_s4_fallback_used"] is True
    assert fallback.metadata["sparse_realization_backend"] == "ld7"
    with pytest.raises(GraphComplexityError, match="forced planning limit"):
        _prepare(_options("hybrid", fallback=False))


def test_identity_error_is_never_hidden_by_fallback(monkeypatch) -> None:
    import mdstats.plotting.atomic_density as module

    def fail(*args, **kwargs):
        raise GraphAdapterError("forced identity defect")

    monkeypatch.setattr(module, "build_density_support_atlas", fail)
    with pytest.raises(GraphAdapterError, match="forced identity defect"):
        _prepare(_options("hybrid", fallback=True))


def test_optimization_options_round_trip_includes_s4_dispatch_controls() -> None:
    options = _options().optimization_options
    restored = DensityOptimizationOptions.from_json_dict(options.to_json_dict())
    assert restored == options
