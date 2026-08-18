from __future__ import annotations

import numpy as np
import pytest

from mdstats.analysis._spectral import spectral_bin_integral
from mdstats.analysis._spectral_units import convert_frequency_axes
from mdstats.analysis.vacf import VACFResult
from mdstats.analysis.velocity_spectrum import (
    VDOSResult,
    VelocitySpectrumResult,
    compute_vacf_spectrum,
    compute_vdos,
)


def make_spectrum(
    components: np.ndarray,
    *,
    per_atom_components: np.ndarray | None = None,
    weighting: str = "mass",
) -> VelocitySpectrumResult:
    components = np.asarray(components, dtype=np.float64)
    n_frequency = components.shape[0]
    n_fft = 2 * (n_frequency - 1)
    sample_spacing_ps = 1.0 / float(n_fft)
    frequencies = np.arange(n_frequency, dtype=np.float64)
    angular, wavenumbers, energies = convert_frequency_axes(frequencies)
    scalar = np.sum(components, axis=1)
    tensor = np.zeros((n_frequency, 3, 3), dtype=np.complex128)
    diagonal = np.arange(3)
    tensor[:, diagonal, diagonal] = components

    per_atom_scalar = None
    per_atom_indices = None
    if per_atom_components is not None:
        per_atom_components = np.asarray(per_atom_components, dtype=np.float64)
        per_atom_scalar = np.sum(per_atom_components, axis=2)
        per_atom_indices = np.arange(per_atom_components.shape[1], dtype=np.int64)
        atom_indices = np.array(per_atom_indices, copy=True)
        atom_weights = np.arange(1, atom_indices.size + 1, dtype=np.float64)
    else:
        atom_indices = np.array([0, 1], dtype=np.int64)
        atom_weights = np.array([1.0, 2.0], dtype=np.float64)

    return VelocitySpectrumResult(
        frequencies_thz=frequencies,
        angular_frequencies_ps_inv=angular,
        wavenumbers_cm_inv=wavenumbers,
        energies_mev=energies,
        scalar_spectrum=scalar,
        component_spectra=components,
        tensor_spectrum=tensor,
        per_atom_scalar=per_atom_scalar,
        per_atom_components=per_atom_components,
        per_atom_indices=per_atom_indices,
        atom_indices=atom_indices,
        atom_weights=atom_weights,
        weight_sum=float(np.sum(atom_weights)),
        estimator="vacf_transform",
        weighting=weighting,
        normalization="raw",
        correlation_weighting="reported",
        spectral_sidedness="one_sided",
        spectral_scaling="density",
        spectrum_units="amu*Å^2/ps" if weighting == "mass" else "Å^2/ps",
        sample_spacing_ps=sample_spacing_ps,
        n_samples=64,
        n_fft=n_fft,
        window=None,
        detrend=None,
        metadata={"source": "synthetic"},
    )


def test_unit_area_vdos_uses_discrete_bin_measure() -> None:
    source = make_spectrum(
        np.array(
            [
                [1.0, 0.5, 0.25],
                [2.0, 1.0, 0.5],
                [3.0, 1.5, 0.75],
                [2.0, 1.0, 0.5],
                [1.0, 0.5, 0.25],
            ]
        )
    )
    original = np.array(source.component_spectra, copy=True)

    result = compute_vdos(source)

    assert isinstance(result, VDOSResult)
    assert result.normalization == "unit_area"
    assert result.target_weight == pytest.approx(1.0)
    assert spectral_bin_integral(result.total, result.frequencies_thz) == pytest.approx(
        1.0
    )
    assert result.integrated_weight_after == pytest.approx(1.0)
    np.testing.assert_allclose(result.total, np.sum(result.components, axis=1))
    assert result.density_units == "1/THz"
    assert result.metadata["interpretation"] == "mass_weighted_vdos"
    np.testing.assert_array_equal(source.component_spectra, original)

    trapezoidal = np.trapezoid(result.total, x=result.frequencies_thz)
    assert trapezoidal != pytest.approx(1.0)


@pytest.mark.parametrize("target", [12.0, 9.0, 4.5])
def test_explicit_degrees_of_freedom_targets(target: float) -> None:
    source = make_spectrum(np.ones((5, 3), dtype=np.float64))

    result = compute_vdos(
        source,
        normalization="degrees_of_freedom",
        target_degrees_of_freedom=target,
    )

    assert result.target_weight == pytest.approx(target)
    assert result.integrated_weight_after == pytest.approx(target)
    assert spectral_bin_integral(result.total, result.frequencies_thz) == pytest.approx(
        target
    )
    assert result.density_units == "degrees_of_freedom/THz"


def test_none_preserves_nonnegative_source_exactly() -> None:
    source = make_spectrum(
        np.array(
            [
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6],
                [0.7, 0.8, 0.9],
                [1.0, 1.1, 1.2],
            ]
        ),
        weighting="uniform",
    )

    result = compute_vdos(source, normalization="none")

    np.testing.assert_array_equal(result.total, source.scalar_spectrum)
    np.testing.assert_array_equal(result.components, source.component_spectra)
    np.testing.assert_array_equal(result.frequencies_thz, source.frequencies_thz)
    assert result.target_weight is None
    assert result.integrated_weight_before == pytest.approx(
        result.integrated_weight_after
    )
    assert result.density_units == source.spectrum_units
    assert result.metadata["interpretation"] == "velocity_derived_vdos"


def test_per_atom_projections_use_the_same_normalization_factor() -> None:
    per_atom = np.zeros((5, 2, 3), dtype=np.float64)
    per_atom[:, 0, 0] = [1.0, 2.0, 3.0, 2.0, 1.0]
    per_atom[:, 1, 1] = [0.5, 1.0, 1.5, 1.0, 0.5]
    source = make_spectrum(np.sum(per_atom, axis=1), per_atom_components=per_atom)

    result = compute_vdos(source, normalization="unit_area")
    factor = result.metadata["normalization_factor"]

    np.testing.assert_allclose(
        result.per_atom_components, source.per_atom_components * factor
    )
    np.testing.assert_allclose(result.per_atom, np.sum(result.per_atom_components, axis=2))
    np.testing.assert_allclose(np.sum(result.per_atom, axis=1), result.total)
    np.testing.assert_array_equal(result.per_atom_indices, source.per_atom_indices)


def test_low_frequency_crop_uses_existing_bins_only() -> None:
    source = make_spectrum(np.ones((6, 3), dtype=np.float64))

    result = compute_vdos(
        source,
        normalization="none",
        minimum_frequency_thz=2.2,
    )

    np.testing.assert_array_equal(result.frequencies_thz, [3.0, 4.0, 5.0])
    np.testing.assert_array_equal(result.components, source.component_spectra[3:])
    assert result.metadata["first_retained_bin"] == 3
    assert result.metadata["minimum_frequency_thz"] == pytest.approx(2.2)

    with pytest.raises(ValueError, match="at least two retained"):
        compute_vdos(source, minimum_frequency_thz=4.1)


def test_negative_policy_clips_roundoff_and_rejects_material_lobes() -> None:
    roundoff_components = np.ones((5, 3), dtype=np.float64)
    roundoff_components[2, 1] = -1.0e-14
    source = make_spectrum(roundoff_components)

    clipped = compute_vdos(source, normalization="none")
    assert clipped.components[2, 1] == 0.0
    assert clipped.total[2] == pytest.approx(2.0)

    with pytest.raises(ValueError, match="negative spectral"):
        compute_vdos(source, normalization="none", negative_policy="error")

    material = np.ones((5, 3), dtype=np.float64)
    material[2, 1] = -1.0e-4
    with pytest.raises(ValueError, match="material negative"):
        compute_vdos(make_spectrum(material), normalization="none")


def test_validation_of_targets_thresholds_and_zero_weight() -> None:
    source = make_spectrum(np.ones((5, 3), dtype=np.float64))

    with pytest.raises(ValueError, match="required"):
        compute_vdos(source, normalization="degrees_of_freedom")
    with pytest.raises(ValueError, match="strictly positive"):
        compute_vdos(
            source,
            normalization="degrees_of_freedom",
            target_degrees_of_freedom=0.0,
        )
    with pytest.raises(ValueError, match="only valid"):
        compute_vdos(source, target_degrees_of_freedom=3.0)
    with pytest.raises(ValueError, match="nonnegative"):
        compute_vdos(source, minimum_frequency_thz=-1.0)
    with pytest.raises(ValueError, match="negative_policy"):
        compute_vdos(source, negative_policy="preserve")
    with pytest.raises(ValueError, match="negative_tolerance"):
        compute_vdos(source, negative_tolerance=-1.0)

    zero = make_spectrum(np.zeros((5, 3), dtype=np.float64))
    with pytest.raises(ValueError, match="finite and positive"):
        compute_vdos(zero)


def test_zero_padding_changes_grid_not_normalized_weight() -> None:
    n_lags = 5
    components = np.zeros((n_lags, 3), dtype=np.float64)
    components[0] = [1.0, 2.0, 3.0]
    tensor = np.zeros((n_lags, 3, 3), dtype=np.float64)
    diagonal = np.arange(3)
    tensor[:, diagonal, diagonal] = components
    vacf = VACFResult(
        lag_steps=np.arange(n_lags, dtype=np.int64),
        lag_times=0.1 * np.arange(n_lags, dtype=np.float64),
        scalar_sum=np.sum(components, axis=1),
        components_sum=components,
        tensor_sum=tensor,
        per_atom_scalar=None,
        per_atom_components=None,
        per_atom_indices=None,
        n_origins=np.arange(20, 20 - n_lags, -1, dtype=np.int64),
        atom_indices=np.array([0], dtype=np.int64),
        atom_weights=np.array([1.0]),
        weight_sum=1.0,
        weighting="uniform",
        drift_mode=None,
        backend="direct",
        metadata={"correlation_units": "Å^2/ps^2", "frame_count": 20},
    )

    short = compute_vdos(compute_vacf_spectrum(vacf, normalization="raw"))
    padded = compute_vdos(
        compute_vacf_spectrum(vacf, normalization="raw", zero_pad_to=128)
    )

    assert short.frequencies_thz.size != padded.frequencies_thz.size
    assert short.integrated_weight_after == pytest.approx(1.0)
    assert padded.integrated_weight_after == pytest.approx(1.0)


def test_vdos_result_constructor_rejects_inconsistent_area() -> None:
    source = make_spectrum(np.ones((5, 3), dtype=np.float64))
    valid = compute_vdos(source)

    with pytest.raises(ValueError, match="inconsistent"):
        VDOSResult(
            frequencies_thz=valid.frequencies_thz,
            wavenumbers_cm_inv=valid.wavenumbers_cm_inv,
            energies_mev=valid.energies_mev,
            total=valid.total,
            components=valid.components,
            per_atom=valid.per_atom,
            per_atom_components=valid.per_atom_components,
            per_atom_indices=valid.per_atom_indices,
            normalization=valid.normalization,
            integrated_weight_before=valid.integrated_weight_before,
            integrated_weight_after=2.0,
            target_weight=valid.target_weight,
            source_estimator=valid.source_estimator,
            weighting=valid.weighting,
            density_units=valid.density_units,
            metadata=valid.metadata,
        )


def test_public_exports() -> None:
    import mdstats
    import mdstats.analysis as analysis

    assert mdstats.VDOSResult is VDOSResult
    assert mdstats.compute_vdos is compute_vdos
    assert analysis.VDOSResult is VDOSResult
    assert analysis.compute_vdos is compute_vdos
