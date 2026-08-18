from __future__ import annotations

import numpy as np
import pytest

from mdstats.analysis._quadrature import cumulative_trapezoid_zero
from mdstats.analysis._dynamics_common import (
    DynamicsInputSignature,
    resolve_analysis_subspace,
)
from mdstats.analysis.diffusion import (
    DiffusionComparisonResult,
    DiffusionEstimate,
    compare_msd_vacf_diffusion,
    estimate_diffusion_plateau,
)
from mdstats.analysis.msd import MSDResult
from mdstats.analysis.vacf_transport import VACFDiffusionResult


def make_signature(
    times: np.ndarray,
    *,
    atom_indices: tuple[int, ...] = (0, 1),
    drift_mode: str | None = None,
    drift_atom_indices: tuple[int, ...] | None = None,
    source_files: tuple[str, ...] = ("synthetic",),
    coordinate_mode: str = "laboratory",
    component: str = "scalar",
    dimensions: int = 3,
) -> DynamicsInputSignature:
    times = np.asarray(times, dtype=np.float64)
    if component in ("x", "y", "z"):
        subspace = resolve_analysis_subspace(axes=(component,))
    elif dimensions == 3:
        subspace = resolve_analysis_subspace()
    elif dimensions == 2:
        subspace = resolve_analysis_subspace(axes=("x", "y"))
    else:
        subspace = resolve_analysis_subspace(axes=("x",))
    fingerprint = f"{source_files!r}:{times.tobytes().hex()}"
    return DynamicsInputSignature(
        source_format="synthetic",
        source_files=source_files,
        trajectory_fingerprint=fingerprint,
        frame_indices=tuple(range(times.size)),
        frame_times_ps=times,
        n_frames=times.size,
        sample_spacing_ps=(None if times.size < 2 else float(times[1] - times[0])),
        atom_indices=np.asarray(atom_indices, dtype=np.int64),
        coordinate_mode=coordinate_mode,
        reference_cell_mode=None,
        reference_cell=None,
        drift_mode=drift_mode,
        drift_atom_indices=(
            None
            if drift_mode is None
            else np.asarray(
                atom_indices if drift_atom_indices is None else drift_atom_indices,
                dtype=np.int64,
            )
        ),
        velocity_source="native",
        projection_basis=subspace.projection_basis,
        projection_labels=subspace.labels,
    )


def make_running(
    integrand: np.ndarray,
    times: np.ndarray,
    *,
    component: str = "scalar",
    dimensions: int = 3,
    atom_indices: tuple[int, ...] = (0, 1),
    drift_mode: str | None = None,
    drift_atom_indices: tuple[int, ...] | None = None,
    source_files: tuple[str, ...] = ("synthetic",),
) -> VACFDiffusionResult:
    integrand = np.asarray(integrand, dtype=np.float64)
    times = np.asarray(times, dtype=np.float64)
    effective_dimensions = 1 if component in ("x", "y", "z") else dimensions
    signature = make_signature(
        times,
        atom_indices=atom_indices,
        drift_mode=drift_mode,
        drift_atom_indices=drift_atom_indices,
        source_files=source_files,
        component=component,
        dimensions=effective_dimensions,
    )
    return VACFDiffusionResult(
        lag_times=times,
        running_diffusion_a2_per_ps=cumulative_trapezoid_zero(
            integrand, times, axis=0
        ),
        integrand=integrand,
        dimensions=effective_dimensions,
        component=component,
        weighting="uniform",
        integration="trapezoid",
        metadata={
            "selected_atom_indices": list(atom_indices),
            "drift_mode": drift_mode,
            "source_vacf_metadata": {"source_files": list(source_files)},
        },
        projection_basis=signature.projection_basis,
        projection_labels=signature.projection_labels,
        signature=signature,
    )


def make_estimate(
    value: float,
    times: np.ndarray,
    *,
    component: str = "scalar",
    dimensions: int = 3,
    atom_indices: tuple[int, ...] = (0, 1),
    drift_mode: str | None = None,
    drift_atom_indices: tuple[int, ...] | None = None,
    source_files: tuple[str, ...] = ("synthetic",),
    is_stable: bool | None = True,
) -> DiffusionEstimate:
    effective_dimensions = 1 if component in ("x", "y", "z") else dimensions
    signature = make_signature(
        times,
        atom_indices=atom_indices,
        drift_mode=drift_mode,
        drift_atom_indices=drift_atom_indices,
        source_files=source_files,
        component=component,
        dimensions=effective_dimensions,
    )
    return DiffusionEstimate(
        value_a2_per_ps=value,
        standard_error_a2_per_ps=None,
        time_range_ps=(float(times[0]), float(times[-1])),
        method="explicit",
        component=component,
        dimensions=effective_dimensions,
        n_points=max(2, int(times.size)),
        is_stable=is_stable,
        diagnostics={},
        metadata={
            "selected_atom_indices": list(atom_indices),
            "drift_mode": drift_mode,
            "source_files": list(source_files),
        },
        projection_basis=signature.projection_basis,
        projection_labels=signature.projection_labels,
        signature=signature,
    )


def make_msd(
    times: np.ndarray,
    diffusion: float,
    *,
    component: str = "scalar",
    dimensions: int = 3,
    atom_indices: tuple[int, ...] = (0, 1),
    drift_mode: str | None = None,
    drift_atom_indices: tuple[int, ...] | None = None,
    mode: str = "time_averaged",
    coordinate_mode: str = "laboratory",
    source_files: tuple[str, ...] = ("synthetic",),
    intercept: float = 0.0,
) -> MSDResult:
    times = np.asarray(times, dtype=np.float64)
    components = np.zeros((times.size, 3), dtype=np.float64)
    if component == "scalar":
        per_dimension = (2.0 * dimensions * diffusion * times + intercept) / 3.0
        components[:] = per_dimension[:, None]
    else:
        components[:, {"x": 0, "y": 1, "z": 2}[component]] = (
            2.0 * diffusion * times + intercept
        )
    msd = np.sum(components, axis=1)
    signature = make_signature(
        times,
        atom_indices=atom_indices,
        drift_mode=drift_mode,
        drift_atom_indices=drift_atom_indices,
        source_files=source_files,
        coordinate_mode=coordinate_mode,
        component="scalar",
        dimensions=3,
    )
    return MSDResult(
        lag_steps=np.arange(times.size, dtype=np.int64),
        lag_times=times,
        msd=msd,
        components=components,
        tensor=None,
        per_atom_msd=None,
        n_origins=np.arange(times.size, 0, -1, dtype=np.int64),
        atom_indices=np.asarray(atom_indices, dtype=np.int64),
        n_atoms=len(atom_indices),
        mode=mode,
        coordinate_mode=coordinate_mode,
        drift_mode=drift_mode,
        reference_cell=None,
        metadata={"source_files": list(source_files)},
        signature=signature,
    )

def test_explicit_plateau_uses_existing_samples_and_reports_diagnostics() -> None:
    times = np.linspace(0.0, 10.0, 101)
    integrand = np.where(times < 2.0, 0.25, 0.0)
    running = make_running(integrand, times)

    result = estimate_diffusion_plateau(
        running,
        time_range_ps=(4.05, 9.95),
        minimum_points=20,
        slope_tolerance=1.0e-12,
    )

    selected = (times >= 4.05) & (times <= 9.95)
    expected = np.mean(running.running_diffusion_a2_per_ps[selected])
    assert result.value_a2_per_ps == pytest.approx(expected)
    assert result.time_range_ps == pytest.approx((4.1, 9.9))
    assert result.n_points == int(np.count_nonzero(selected))
    assert result.standard_error_a2_per_ps is None
    assert result.is_stable is True
    assert abs(result.diagnostics["linear_slope_a2_per_ps2"]) < 1.0e-14
    assert result.metadata["selected_atom_indices"] == (0, 1)
    assert result.value_cm2_per_s == pytest.approx(result.value_a2_per_ps * 1.0e-4)


def test_slope_tolerance_can_flag_an_explicit_drifting_interval() -> None:
    times = np.linspace(0.0, 10.0, 101)
    running = make_running(np.full(times.size, 0.02), times)

    result = estimate_diffusion_plateau(
        running,
        time_range_ps=(4.0, 10.0),
        slope_tolerance=0.01,
    )

    assert result.diagnostics["linear_slope_a2_per_ps2"] == pytest.approx(0.02)
    assert result.is_stable is False
    assert result.diagnostics["passes_slope_tolerance"] is False


def test_stable_window_is_explicitly_deferred() -> None:
    times = np.linspace(0.0, 1.0, 11)
    running = make_running(np.ones(times.size), times)

    with pytest.raises(NotImplementedError, match="deferred"):
        estimate_diffusion_plateau(running, method="stable_window")


def test_plateau_interval_and_option_validation() -> None:
    times = np.linspace(0.0, 1.0, 11)
    running = make_running(np.ones(times.size), times)

    with pytest.raises(TypeError, match="VACFDiffusionResult"):
        estimate_diffusion_plateau(object(), time_range_ps=(0.0, 1.0))
    with pytest.raises(ValueError, match="required"):
        estimate_diffusion_plateau(running)
    with pytest.raises(ValueError, match="outside"):
        estimate_diffusion_plateau(running, time_range_ps=(0.5, 1.5))
    with pytest.raises(ValueError, match="minimum_points"):
        estimate_diffusion_plateau(
            running, time_range_ps=(0.0, 0.1), minimum_points=3
        )
    with pytest.raises(ValueError, match="finite and nonnegative"):
        estimate_diffusion_plateau(
            running, time_range_ps=(0.0, 1.0), slope_tolerance=-1.0
        )


def test_scalar_msd_and_vacf_diffusion_agree_exactly() -> None:
    times = np.linspace(0.0, 10.0, 101)
    diffusion = 0.35
    msd = make_msd(times, diffusion, dimensions=3)
    estimate = make_estimate(diffusion, times, dimensions=3)

    result = compare_msd_vacf_diffusion(
        msd,
        estimate,
        msd_fit_range_ps=(3.0, 9.0),
        dimensions=3,
    )

    assert result.msd_diffusion_a2_per_ps == pytest.approx(diffusion)
    assert result.vacf_diffusion_a2_per_ps == pytest.approx(diffusion)
    assert result.absolute_difference_a2_per_ps == pytest.approx(0.0, abs=1e-15)
    assert result.symmetric_relative_difference == pytest.approx(0.0, abs=1e-15)
    assert result.msd_slope_a2_per_ps == pytest.approx(6.0 * diffusion)
    assert result.diagnostics["msd_linear_r_squared"] == pytest.approx(1.0)
    assert result.metadata["selected_atom_indices"] == (0, 1)


def test_comparison_reports_symmetric_difference_without_preferred_estimator() -> None:
    times = np.linspace(0.0, 10.0, 51)
    msd = make_msd(times, 0.4)
    estimate = make_estimate(0.5, times)

    result = compare_msd_vacf_diffusion(
        msd,
        estimate,
        msd_fit_range_ps=(2.0, 8.0),
    )

    assert result.signed_difference_a2_per_ps == pytest.approx(-0.1)
    assert result.absolute_difference_a2_per_ps == pytest.approx(0.1)
    assert result.symmetric_relative_difference == pytest.approx(2.0 * 0.1 / 0.9)
    assert result.metadata["relative_difference_definition"].startswith("2*abs")
    assert result.diagnostics["one_estimator_declared_authoritative"] is False


def test_directional_comparison_uses_one_dimensional_einstein_factor() -> None:
    times = np.linspace(0.0, 5.0, 31)
    msd = make_msd(times, 0.2, component="x", dimensions=1)
    estimate = make_estimate(0.2, times, component="x", dimensions=1)

    result = compare_msd_vacf_diffusion(
        msd,
        estimate,
        msd_fit_range_ps=(1.0, 4.0),
        dimensions=1,
    )

    assert result.component == "x"
    assert result.msd_slope_a2_per_ps == pytest.approx(0.4)
    assert result.msd_diffusion_a2_per_ps == pytest.approx(0.2)
    assert result.diagnostics["msd_fit_divisor"] == pytest.approx(2.0)


def test_comparison_rejects_incompatible_provenance_and_semantics() -> None:
    times = np.linspace(0.0, 5.0, 31)
    estimate = make_estimate(0.2, times)

    with pytest.raises(ValueError, match="atom_indices"):
        compare_msd_vacf_diffusion(
            make_msd(times, 0.2, atom_indices=(0, 2)),
            estimate,
            msd_fit_range_ps=(1.0, 4.0),
        )
    with pytest.raises(ValueError, match="drift_mode"):
        compare_msd_vacf_diffusion(
            make_msd(times, 0.2, drift_mode="center_of_mass"),
            estimate,
            msd_fit_range_ps=(1.0, 4.0),
        )
    with pytest.raises(ValueError, match="source_files|trajectory_fingerprint"):
        compare_msd_vacf_diffusion(
            make_msd(times, 0.2, source_files=("other",)),
            estimate,
            msd_fit_range_ps=(1.0, 4.0),
        )
    with pytest.raises(ValueError, match="time_averaged"):
        compare_msd_vacf_diffusion(
            make_msd(times, 0.2, mode="fixed_origin"),
            estimate,
            msd_fit_range_ps=(1.0, 4.0),
        )
    with pytest.raises(ValueError, match="laboratory-frame"):
        compare_msd_vacf_diffusion(
            make_msd(times, 0.2, coordinate_mode="reference_cell"),
            estimate,
            msd_fit_range_ps=(1.0, 4.0),
        )


def test_comparison_dimension_and_range_validation() -> None:
    times = np.linspace(0.0, 5.0, 31)
    msd = make_msd(times, 0.2)
    estimate = make_estimate(0.2, times)

    with pytest.raises(ValueError, match="inconsistent with the stored analysis subspace"):
        compare_msd_vacf_diffusion(
            msd, estimate, msd_fit_range_ps=(1.0, 4.0), dimensions=2
        )
    with pytest.raises(ValueError, match="at least three"):
        compare_msd_vacf_diffusion(
            msd, estimate, msd_fit_range_ps=(1.0, 1.1)
        )
    with pytest.raises(ValueError, match="outside"):
        compare_msd_vacf_diffusion(
            msd, estimate, msd_fit_range_ps=(1.0, 6.0)
        )


def test_nonpositive_msd_slope_is_flagged_not_silently_reinterpreted() -> None:
    times = np.linspace(0.0, 5.0, 31)
    msd = make_msd(times, -0.1)
    estimate = make_estimate(0.0, times, is_stable=None)

    result = compare_msd_vacf_diffusion(
        msd, estimate, msd_fit_range_ps=(1.0, 4.0)
    )

    assert result.msd_diffusion_a2_per_ps < 0.0
    assert "nonpositive_msd_slope" in result.diagnostics["interpretation_flags"]
    assert "vacf_interval_stability_not_assessed" in result.diagnostics[
        "interpretation_flags"
    ]


def test_result_objects_validate_internal_consistency() -> None:
    with pytest.raises(ValueError, match="inconsistent"):
        DiffusionComparisonResult(
            msd_diffusion_a2_per_ps=1.0,
            vacf_diffusion_a2_per_ps=0.5,
            signed_difference_a2_per_ps=99.0,
            absolute_difference_a2_per_ps=0.5,
            symmetric_relative_difference=2.0 / 3.0,
            msd_fit_range_ps=(1.0, 2.0),
            msd_slope_a2_per_ps=6.0,
            msd_intercept_a2=0.0,
            component="scalar",
            dimensions=3,
            n_msd_points=3,
        )


def test_oscillatory_interval_preserves_spread_diagnostics() -> None:
    times = np.linspace(0.0, 8.0, 81)
    # A short positive transient establishes a nonzero level; the subsequent
    # sinusoidal integrand produces a valid oscillatory running integral.
    integrand = np.where(
        times < 1.0,
        0.3,
        0.02 * 2.0 * np.pi * np.cos(2.0 * np.pi * times),
    )
    running = make_running(integrand, times)
    result = estimate_diffusion_plateau(
        running,
        time_range_ps=(2.0, 8.0),
        minimum_points=20,
    )
    assert result.standard_error_a2_per_ps is None
    assert result.diagnostics["interval_span_a2_per_ps"] > 0.03
    assert result.diagnostics["uncertainty_policy"].startswith("no_independent")


def test_comparison_flags_nonpositive_msd_slope_without_clipping() -> None:
    times = np.linspace(0.0, 5.0, 31)
    msd = make_msd(times, -0.05)
    estimate = make_estimate(0.01, times, is_stable=None)
    result = compare_msd_vacf_diffusion(
        msd,
        estimate,
        msd_fit_range_ps=(1.0, 4.0),
    )
    assert result.msd_diffusion_a2_per_ps == pytest.approx(-0.05)
    assert "nonpositive_msd_slope" in result.diagnostics["interpretation_flags"]
    assert "vacf_interval_stability_not_assessed" in result.diagnostics[
        "interpretation_flags"
    ]


def test_result_objects_validate_redundant_fields() -> None:
    with pytest.raises(ValueError, match="inconsistent"):
        DiffusionComparisonResult(
            msd_diffusion_a2_per_ps=0.2,
            vacf_diffusion_a2_per_ps=0.1,
            signed_difference_a2_per_ps=0.0,
            absolute_difference_a2_per_ps=0.1,
            symmetric_relative_difference=2.0 / 3.0,
            msd_fit_range_ps=(1.0, 2.0),
            msd_slope_a2_per_ps=1.2,
            msd_intercept_a2=0.0,
            component="scalar",
            dimensions=3,
            n_msd_points=3,
        )


def test_directional_plateau_normalizes_result_dimensions_to_one() -> None:
    times = np.linspace(0.0, 2.0, 21)
    running = make_running(
        np.zeros(times.size),
        times,
        component="x",
        dimensions=3,
    )
    result = estimate_diffusion_plateau(
        running,
        time_range_ps=(0.5, 2.0),
        minimum_points=4,
    )
    assert result.component == "x"
    assert result.dimensions == 1
    assert result.metadata["source_dimensions"] == 1


def test_public_namespace_exports_g2_symbols() -> None:
    import mdstats
    import mdstats.analysis as analysis

    assert mdstats.DiffusionEstimate is DiffusionEstimate
    assert mdstats.DiffusionComparisonResult is DiffusionComparisonResult
    assert mdstats.estimate_diffusion_plateau is estimate_diffusion_plateau
    assert mdstats.compare_msd_vacf_diffusion is compare_msd_vacf_diffusion
    assert analysis.DiffusionEstimate is DiffusionEstimate
    assert analysis.compare_msd_vacf_diffusion is compare_msd_vacf_diffusion
