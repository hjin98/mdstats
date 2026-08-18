from __future__ import annotations

from mdstats.plotting.runtime_resources import (
    DENSITY_TIME_MODEL_SCHEMA,
    _calibrate_density_time_model_cached,
    calibrate_density_time_model,
)


def test_par_dens1_calibrates_execution_faithful_direct_and_scipy_fft(monkeypatch) -> None:
    monkeypatch.delenv("MDSTATS_DISABLE_TIME_CALIBRATION", raising=False)
    _calibrate_density_time_model_cached.cache_clear()
    model = calibrate_density_time_model(max_threads=1)
    assert model.schema_version == DENSITY_TIME_MODEL_SCHEMA
    assert model.calibration_source.startswith("par_dens1_runtime_execution_calibration_v1:")
    assert model.direct_index_pairs_per_second > 0.0
    assert model.direct_reduction_pairs_per_second > 0.0
    assert model.support_region_operations_per_second > 0.0
    assert model.fft_work_units_per_second > 0.0
    metadata = model.calibration_metadata
    assert metadata["calibration_policy"] == "par_dens1_execution_faithful_v1"
    assert metadata["array_dtype"] == "float64"
    assert metadata["tile_shape"] == [32, 32, 32]
    assert metadata["direct_contribution_count"] > 0
    assert metadata["direct_bincount_pairs_per_second_measured"] > 0.0
    assert metadata["direct_add_at_pairs_per_second_measured"] > 0.0
    assert metadata["direct_reduction_pairs_per_second_measured"] == min(
        metadata["direct_bincount_pairs_per_second_measured"],
        metadata["direct_add_at_pairs_per_second_measured"],
    )
    assert metadata["direct_reduction_calibration_policy"] == (
        "slower_of_bincount_and_add_at_v1"
    )
    assert metadata["source_occupancy"] > 0.0
    assert metadata["temporary_memory_bytes"] > 0
    assert metadata["fft_backend"] == "scipy.fft.pocketfft"


def test_par_dens1_disabled_calibration_remains_explicit(monkeypatch) -> None:
    monkeypatch.setenv("MDSTATS_DISABLE_TIME_CALIBRATION", "1")
    _calibrate_density_time_model_cached.cache_clear()
    model = calibrate_density_time_model(max_threads=1)
    assert model.calibration_source == "conservative_static_disabled_v3"
    assert model.calibration_metadata["disabled"] is True


def test_par_dens1_hybrid_selector_uses_measured_direct_fft_cross_over(monkeypatch) -> None:
    import math

    from mdstats.plotting.density_tiled_fft import (
        DensityHybridExecutorOptions,
        _choose_executor,
    )

    monkeypatch.delenv("MDSTATS_DISABLE_TIME_CALIBRATION", raising=False)
    _calibrate_density_time_model_cached.cache_clear()
    options = DensityHybridExecutorOptions(min_fft_source_nodes=32, fft_workers=1)
    padded_nodes = 64**3
    fft_work = padded_nodes * math.log2(padded_nodes)
    fft_seconds = options.fft_fixed_seconds + fft_work * options.fft_work_seconds
    crossover_pairs = max(2, int(math.ceil(fft_seconds / options.direct_pair_seconds)))

    sparse = _choose_executor(
        source_count=8,
        direct_pairs=max(1, crossover_pairs // 4),
        padded_nodes=padded_nodes,
        options=options,
        fft_feasible=True,
    )
    intermediate = _choose_executor(
        source_count=64,
        direct_pairs=max(1, crossover_pairs // 2),
        padded_nodes=padded_nodes,
        options=options,
        fft_feasible=True,
    )
    dense = _choose_executor(
        source_count=64,
        direct_pairs=4 * crossover_pairs,
        padded_nodes=padded_nodes,
        options=options,
        fft_feasible=True,
    )

    assert sparse[0] == "direct"
    assert sparse[1] < sparse[2]
    assert intermediate[0] == "direct"
    assert intermediate[1] < intermediate[2]
    assert dense[0] == "fft"
    assert dense[2] < dense[1]
