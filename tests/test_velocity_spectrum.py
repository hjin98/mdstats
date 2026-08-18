from __future__ import annotations

import numpy as np
import pytest

from mdstats.analysis._spectral import resolve_spectrum_fft_length
from mdstats.analysis.vacf import VACFResult
from mdstats.analysis.velocity_spectrum import (
    VelocitySpectrumResult,
    compute_vacf_spectrum,
)


def make_vacf(
    components: np.ndarray,
    *,
    dt_ps: float = 0.1,
    tensor: np.ndarray | None = None,
    per_atom_components: np.ndarray | None = None,
    n_origins: np.ndarray | None = None,
    weights: np.ndarray | None = None,
    weighting: str = "uniform",
    correlation_units: str = "Å^2/ps^2",
    lag_steps: np.ndarray | None = None,
) -> VACFResult:
    components = np.asarray(components, dtype=np.float64)
    n_lags = components.shape[0]
    if lag_steps is None:
        lag_steps = np.arange(n_lags, dtype=np.int64)
    else:
        lag_steps = np.asarray(lag_steps, dtype=np.int64)
    lag_times = np.arange(n_lags, dtype=np.float64) * dt_ps
    scalar = np.sum(components, axis=1)

    if tensor is None:
        tensor = np.zeros((n_lags, 3, 3), dtype=np.float64)
        diagonal = np.arange(3)
        tensor[:, diagonal, diagonal] = components
    if n_origins is None:
        n_origins = np.arange(32, 32 - n_lags, -1, dtype=np.int64)
    if weights is None:
        weights = np.array([1.0], dtype=np.float64)

    per_atom_scalar = None
    per_atom_indices = None
    if per_atom_components is not None:
        per_atom_components = np.asarray(per_atom_components, dtype=np.float64)
        per_atom_scalar = np.sum(per_atom_components, axis=2)
        per_atom_indices = np.arange(per_atom_components.shape[1], dtype=np.int64)
        atom_indices = np.array(per_atom_indices, copy=True)
        if weights.size != atom_indices.size:
            weights = np.ones(atom_indices.size, dtype=np.float64)
    else:
        atom_indices = np.arange(weights.size, dtype=np.int64)

    return VACFResult(
        lag_steps=lag_steps,
        lag_times=lag_times,
        scalar_sum=scalar,
        components_sum=components,
        tensor_sum=tensor,
        per_atom_scalar=per_atom_scalar,
        per_atom_components=per_atom_components,
        per_atom_indices=per_atom_indices,
        n_origins=np.asarray(n_origins, dtype=np.int64),
        atom_indices=atom_indices,
        atom_weights=np.asarray(weights, dtype=np.float64),
        weight_sum=float(np.sum(weights)),
        weighting=weighting,
        drift_mode=None,
        backend="direct",
        metadata={
            "correlation_units": correlation_units,
            "frame_count": int(n_origins[0]),
            "time_step_ps": dt_ps,
        },
    )


def test_vacf_spectrum_on_grid_cosine_peak_and_axes() -> None:
    n_lags = 8
    n_fft = resolve_spectrum_fft_length(n_lags, zero_pad_to=None)
    dt_ps = 0.1
    frequency_index = 3
    lag = np.arange(n_lags)
    correlation = np.cos(2.0 * np.pi * frequency_index * lag / n_fft)
    components = np.zeros((n_lags, 3), dtype=np.float64)
    components[:, 0] = correlation
    vacf = make_vacf(components, dt_ps=dt_ps)

    result = compute_vacf_spectrum(vacf, normalization="raw")

    assert isinstance(result, VelocitySpectrumResult)
    assert result.n_fft == n_fft
    assert np.argmax(result.scalar_spectrum) == frequency_index
    assert result.frequencies_thz[frequency_index] == pytest.approx(
        frequency_index / (n_fft * dt_ps)
    )
    np.testing.assert_allclose(result.scalar_spectrum, result.component_spectra.sum(1))
    np.testing.assert_allclose(
        np.diagonal(result.tensor_spectrum, axis1=1, axis2=2).real,
        result.component_spectra,
    )
    df = result.frequencies_thz[1] - result.frequencies_thz[0]
    assert df * np.sum(result.scalar_spectrum) == pytest.approx(1.0, abs=2e-13)
    assert result.wavenumbers_cm_inv[frequency_index] > 0.0
    assert result.energies_mev[frequency_index] > 0.0


def test_raw_and_per_weight_normalization_are_exact() -> None:
    components = np.ones((6, 3), dtype=np.float64)
    vacf = make_vacf(
        components,
        weights=np.array([1.0, 3.0]),
        weighting="mass",
        correlation_units="amu*Å^2/ps^2",
    )

    raw = compute_vacf_spectrum(vacf, normalization="raw")
    mean = compute_vacf_spectrum(vacf, normalization="per_weight")

    np.testing.assert_allclose(raw.scalar_spectrum, 4.0 * mean.scalar_spectrum)
    np.testing.assert_allclose(raw.component_spectra, 4.0 * mean.component_spectra)
    assert raw.spectrum_units == "amu*Å^2/ps"
    assert mean.spectrum_units == "Å^2/ps"


def test_biased_weighting_matches_explicitly_weighted_reported_vacf() -> None:
    rng = np.random.default_rng(14)
    components = rng.normal(size=(7, 3))
    n_origins = np.array([40, 35, 31, 26, 20, 13, 7], dtype=np.int64)
    vacf = make_vacf(components, n_origins=n_origins)

    biased = compute_vacf_spectrum(
        vacf,
        normalization="raw",
        correlation_weighting="biased",
    )
    factor = n_origins / n_origins[0]
    explicit = make_vacf(
        components * factor[:, None],
        n_origins=n_origins,
    )
    reported = compute_vacf_spectrum(
        explicit,
        normalization="raw",
        correlation_weighting="reported",
    )

    np.testing.assert_allclose(biased.scalar_spectrum, reported.scalar_spectrum)
    np.testing.assert_allclose(biased.component_spectra, reported.component_spectra)
    assert biased.metadata["origin_weighting_factor"] == pytest.approx(factor.tolist())


def test_nonsymmetric_positive_lag_tensor_gives_hermitian_spectrum() -> None:
    components = np.zeros((5, 3), dtype=np.float64)
    components[:, 0] = [2.0, 0.9, 0.2, -0.1, 0.05]
    components[:, 1] = [1.0, 0.4, 0.1, 0.0, -0.02]
    components[:, 2] = [0.5, 0.1, 0.0, -0.04, 0.01]
    tensor = np.zeros((5, 3, 3), dtype=np.float64)
    diagonal = np.arange(3)
    tensor[:, diagonal, diagonal] = components
    tensor[0, 0, 1] = tensor[0, 1, 0] = 0.2
    tensor[1:, 0, 1] = [0.8, -0.3, 0.1, 0.05]
    tensor[1:, 1, 0] = [-0.2, 0.6, -0.1, 0.02]
    vacf = make_vacf(components, tensor=tensor)

    result = compute_vacf_spectrum(vacf, normalization="raw")

    np.testing.assert_allclose(
        result.tensor_spectrum,
        np.conjugate(np.swapaxes(result.tensor_spectrum, 1, 2)),
        atol=2e-13,
    )
    assert np.max(np.abs(result.tensor_spectrum[:, 0, 1].imag)) > 0.0


def test_per_atom_spectra_reproduce_total() -> None:
    n_lags = 6
    per_atom = np.zeros((n_lags, 2, 3), dtype=np.float64)
    per_atom[:, 0, 0] = [1.0, 0.7, 0.3, 0.1, 0.0, -0.05]
    per_atom[:, 1, 1] = [2.0, 1.0, 0.5, 0.2, 0.1, 0.0]
    components = np.sum(per_atom, axis=1)
    vacf = make_vacf(
        components,
        per_atom_components=per_atom,
        weights=np.array([1.0, 1.0]),
    )

    result = compute_vacf_spectrum(vacf, normalization="raw")

    np.testing.assert_allclose(
        np.sum(result.per_atom_components, axis=1), result.component_spectra
    )
    np.testing.assert_allclose(
        np.sum(result.per_atom_scalar, axis=1), result.scalar_spectrum
    )
    np.testing.assert_array_equal(result.per_atom_indices, [0, 1])


def test_half_hann_preserves_zero_lag_bin_area() -> None:
    components = np.zeros((9, 3), dtype=np.float64)
    components[:, 0] = np.exp(-np.arange(9) / 3.0)
    vacf = make_vacf(components)

    result = compute_vacf_spectrum(
        vacf,
        normalization="raw",
        window="half_hann",
        zero_pad_to=64,
    )

    df = result.frequencies_thz[1] - result.frequencies_thz[0]
    assert df * np.sum(result.scalar_spectrum) == pytest.approx(
        vacf.scalar_sum[0], abs=2e-13
    )
    assert result.window == "half_hann"
    assert result.metadata["lag_window"]["alpha"] == 1.0


def test_negative_spectrum_policies() -> None:
    components = np.zeros((2, 3), dtype=np.float64)
    components[:, 0] = [1.0, -2.0]
    vacf = make_vacf(components)

    preserved = compute_vacf_spectrum(
        vacf, normalization="raw", negative_policy="preserve"
    )
    assert np.min(preserved.scalar_spectrum) < 0.0

    clipped = compute_vacf_spectrum(
        vacf, normalization="raw", negative_policy="clip_roundoff"
    )
    assert np.min(clipped.scalar_spectrum) < 0.0

    with pytest.raises(ValueError, match="material negative"):
        compute_vacf_spectrum(vacf, normalization="raw", negative_policy="error")


def test_validation_rejects_noncontiguous_lags_and_invalid_options() -> None:
    components = np.ones((3, 3), dtype=np.float64)
    noncontiguous = make_vacf(components, lag_steps=np.array([0, 2, 4]))
    with pytest.raises(ValueError, match="contiguous"):
        compute_vacf_spectrum(noncontiguous)

    vacf = make_vacf(components)
    with pytest.raises(ValueError, match="normalization"):
        compute_vacf_spectrum(vacf, normalization="invalid")
    with pytest.raises(ValueError, match="correlation_weighting"):
        compute_vacf_spectrum(vacf, correlation_weighting="invalid")
    with pytest.raises(ValueError, match="negative_policy"):
        compute_vacf_spectrum(vacf, negative_policy="invalid")
    with pytest.raises(ValueError, match=r"window\[0\]"):
        compute_vacf_spectrum(vacf, window=[0.0, 0.5, 0.0])


def make_velocity_collection(
    velocities: np.ndarray,
    *,
    dt_ps: float = 0.05,
    masses: np.ndarray | None = None,
    atomic_numbers: np.ndarray | None = None,
):
    from mdstats import AtomisticFrameCollection, FrameCollectionProvenance, FrameSemantics

    velocities = np.asarray(velocities, dtype=np.float64)
    n_frames, n_atoms, _ = velocities.shape
    if masses is None:
        masses = np.ones(n_atoms, dtype=np.float64)
    if atomic_numbers is None:
        atomic_numbers = np.ones(n_atoms, dtype=np.int32)
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.asarray(atomic_numbers, dtype=np.int32),
        masses=np.asarray(masses, dtype=np.float64),
        pbc=np.array([True, True, True]),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.arange(n_frames, dtype=np.float64) * dt_ps,
        cells=np.repeat(np.eye(3)[None, :, :] * 10.0, n_frames, axis=0),
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=np.zeros((n_frames, n_atoms, 3), dtype=np.float64),
        velocities=velocities,
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("synthetic",),
            velocity_source="native",
            coordinate_normalization="native_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def test_welch_matches_scipy_welch_and_csd() -> None:
    from scipy.signal import csd, welch
    from mdstats.analysis.velocity_spectrum import compute_velocity_spectrum

    rng = np.random.default_rng(812)
    dt_ps = 0.02
    n_samples = 320
    velocities = np.zeros((n_samples, 1, 3), dtype=np.float64)
    velocities[:, 0, 0] = rng.normal(size=n_samples)
    velocities[:, 0, 1] = 0.4 * velocities[:, 0, 0] + rng.normal(
        scale=0.7, size=n_samples
    )
    velocities[:, 0, 2] = rng.normal(scale=0.5, size=n_samples)
    collection = make_velocity_collection(velocities, dt_ps=dt_ps)

    result = compute_velocity_spectrum(
        collection,
        segment_length=64,
        overlap=32,
        window="hann",
        detrend="none",
        zero_pad_to=96,
        compute_tensor=True,
    )
    fs = 1.0 / dt_ps
    frequencies, pxx = welch(
        velocities[:, 0, 0],
        fs=fs,
        window="hann",
        nperseg=64,
        noverlap=32,
        nfft=result.n_fft,
        detrend=False,
        return_onesided=True,
        scaling="density",
        average="mean",
    )
    _, pxy = csd(
        velocities[:, 0, 0],
        velocities[:, 0, 1],
        fs=fs,
        window="hann",
        nperseg=64,
        noverlap=32,
        nfft=result.n_fft,
        detrend=False,
        return_onesided=True,
        scaling="density",
        average="mean",
    )
    np.testing.assert_allclose(result.frequencies_thz, frequencies, rtol=0, atol=0)
    np.testing.assert_allclose(result.component_spectra[:, 0], pxx, rtol=2e-13, atol=2e-14)
    np.testing.assert_allclose(result.tensor_spectrum[:, 0, 1], pxy, rtol=3e-13, atol=3e-14)
    np.testing.assert_allclose(
        result.tensor_spectrum,
        np.conjugate(np.swapaxes(result.tensor_spectrum, 1, 2)),
        rtol=2e-13,
        atol=2e-14,
    )
    assert result.estimator == "welch"
    assert result.normalization == "raw"
    assert result.metadata["segment_count"] == 9


def test_welch_per_atom_sum_self_only_and_block_invariance() -> None:
    from mdstats.analysis.velocity_spectrum import compute_velocity_spectrum

    n_samples = 256
    dt_ps = 0.01
    time = np.arange(n_samples) * dt_ps
    velocities = np.zeros((n_samples, 3, 3), dtype=np.float64)
    velocities[:, 0, 0] = np.cos(2.0 * np.pi * 5.0 * time)
    velocities[:, 1, 0] = 2.0 * np.cos(2.0 * np.pi * 11.0 * time + 0.2)
    velocities[:, 2, 1] = 0.5 * np.cos(2.0 * np.pi * 17.0 * time)
    collection = make_velocity_collection(velocities, dt_ps=dt_ps)

    block_one = compute_velocity_spectrum(
        collection,
        segment_length=128,
        overlap=64,
        window="boxcar",
        per_atom=True,
        atom_block_size=1,
    )
    block_all = compute_velocity_spectrum(
        collection,
        segment_length=128,
        overlap=64,
        window="boxcar",
        per_atom=True,
        atom_block_size=99,
    )
    np.testing.assert_allclose(block_one.scalar_spectrum, block_all.scalar_spectrum, rtol=5e-15, atol=5e-17)
    np.testing.assert_allclose(block_one.per_atom_components, block_all.per_atom_components, rtol=5e-15, atol=5e-17)
    np.testing.assert_allclose(
        block_one.component_spectra,
        np.sum(block_one.per_atom_components, axis=1),
        rtol=2e-14,
        atol=2e-14,
    )
    assert block_one.metadata["self_terms_only"] is True
    assert block_one.metadata["cross_atom_products_included"] is False


def test_welch_full_record_boxcar_matches_biased_vacf_transform() -> None:
    from mdstats import compute_vacf
    from mdstats.analysis.velocity_spectrum import compute_velocity_spectrum

    rng = np.random.default_rng(91)
    n_samples = 48
    dt_ps = 0.04
    velocities = rng.normal(size=(n_samples, 2, 3))
    collection = make_velocity_collection(velocities, dt_ps=dt_ps)
    minimum_fft = 2 * n_samples - 1

    vacf = compute_vacf(
        collection,
        max_lag=n_samples - 1,
        backend="direct",
        compute_tensor=True,
        per_atom=True,
    )
    transformed = compute_vacf_spectrum(
        vacf,
        normalization="raw",
        correlation_weighting="biased",
        zero_pad_to=minimum_fft,
    )
    direct = compute_velocity_spectrum(
        collection,
        segment_length=n_samples,
        overlap=0,
        window="boxcar",
        zero_pad_to=minimum_fft,
        compute_tensor=True,
        per_atom=True,
    )
    assert transformed.n_fft == direct.n_fft
    np.testing.assert_allclose(transformed.scalar_spectrum, direct.scalar_spectrum, rtol=5e-13, atol=5e-13)
    np.testing.assert_allclose(transformed.component_spectra, direct.component_spectra, rtol=5e-13, atol=5e-13)
    np.testing.assert_allclose(transformed.tensor_spectrum, direct.tensor_spectrum, rtol=7e-13, atol=7e-13)
    np.testing.assert_allclose(transformed.per_atom_components, direct.per_atom_components, rtol=5e-13, atol=5e-13)


def test_welch_detrend_constant_removes_dc_and_weighting_is_exact() -> None:
    from mdstats.analysis.velocity_spectrum import compute_velocity_spectrum

    velocities = np.zeros((128, 2, 3), dtype=np.float64)
    velocities[:, 0, 0] = 3.0
    velocities[:, 1, 0] = -1.0
    collection = make_velocity_collection(
        velocities, masses=np.array([2.0, 5.0], dtype=np.float64)
    )
    none = compute_velocity_spectrum(
        collection,
        weights="mass",
        segment_length=64,
        overlap=32,
        window="boxcar",
        detrend="none",
    )
    constant = compute_velocity_spectrum(
        collection,
        weights="mass",
        segment_length=64,
        overlap=32,
        window="boxcar",
        detrend="constant",
    )
    assert none.scalar_spectrum[0] > 0.0
    np.testing.assert_allclose(constant.scalar_spectrum, 0.0, atol=1e-28)
    assert none.spectrum_units == "amu*Å^2/ps"
    assert none.weight_sum == pytest.approx(7.0)


def test_welch_selection_per_atom_order_and_validation() -> None:
    from mdstats.analysis.velocity_spectrum import compute_velocity_spectrum

    velocities = np.zeros((32, 3, 3), dtype=np.float64)
    collection = make_velocity_collection(
        velocities,
        atomic_numbers=np.array([11, 8, 19], dtype=np.int32),
    )
    result = compute_velocity_spectrum(
        collection,
        species=["Na", "K"],
        per_atom_indices=[2, 0],
        segment_length=16,
        overlap=0.5,
        window=("tukey", 0.25),
        compute_tensor=False,
        memory_target_bytes=1,
    )
    np.testing.assert_array_equal(result.atom_indices, [0, 2])
    np.testing.assert_array_equal(result.per_atom_indices, [2, 0])
    assert result.tensor_spectrum is None
    assert result.window == "tukey(0.25)"
    assert result.metadata["atom_block_size"] == 1

    with pytest.raises(ValueError, match="exceeds"):
        compute_velocity_spectrum(collection, segment_length=33)
    with pytest.raises(ValueError, match="smaller"):
        compute_velocity_spectrum(collection, segment_length=16, overlap=16)
    with pytest.raises(ValueError, match="0 <= overlap < 1"):
        compute_velocity_spectrum(collection, segment_length=16, overlap=1.0)
    with pytest.raises(ValueError, match="detrend"):
        compute_velocity_spectrum(collection, detrend="linear")
    with pytest.raises(ValueError, match="Invalid Welch window"):
        compute_velocity_spectrum(collection, window="not_a_window")
    with pytest.raises(TypeError, match="compute_tensor"):
        compute_velocity_spectrum(collection, compute_tensor=1)


def test_welch_public_exports() -> None:
    import mdstats
    from mdstats import analysis
    from mdstats.analysis.velocity_spectrum import compute_velocity_spectrum

    assert mdstats.compute_velocity_spectrum is compute_velocity_spectrum
    assert analysis.compute_velocity_spectrum is compute_velocity_spectrum
