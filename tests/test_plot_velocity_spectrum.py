import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

from mdstats import plot_velocity_spectrum
import mdstats.plotting as plotting
from mdstats.analysis._spectral_units import convert_frequency_axes
from mdstats.analysis.velocity_spectrum import (
    VDOSResult,
    VelocitySpectrumResult,
    compute_vdos,
)


def make_spectrum(
    *,
    n_per_atom: int = 2,
    include_per_atom: bool = True,
    weighting: str = "uniform",
    normalization: str = "per_weight",
) -> VelocitySpectrumResult:
    n_fft = 8
    sample_spacing_ps = 0.25
    frequencies = np.arange(n_fft // 2 + 1, dtype=np.float64) / (
        n_fft * sample_spacing_ps
    )
    angular, wavenumbers, energies = convert_frequency_axes(frequencies)

    components = np.column_stack(
        [
            np.array([0.0, 1.0, 2.0, 1.0, 0.25]),
            np.array([0.0, 0.5, 1.0, 0.5, 0.125]),
            np.array([0.0, 0.25, 0.5, 0.25, 0.0625]),
        ]
    )
    scalar = np.sum(components, axis=1)

    atom_indices = np.arange(10, 10 + n_per_atom, dtype=np.int64)
    atom_weights = np.ones(n_per_atom, dtype=np.float64)
    if weighting == "mass":
        atom_weights = np.linspace(20.0, 20.0 + n_per_atom - 1, n_per_atom)

    if include_per_atom:
        base = np.linspace(0.2, 1.0, n_per_atom, dtype=np.float64)
        per_atom_components = components[:, None, :] * base[None, :, None]
        per_atom_scalar = np.sum(per_atom_components, axis=2)
        per_atom_indices = atom_indices.copy()
    else:
        per_atom_components = None
        per_atom_scalar = None
        per_atom_indices = None

    if weighting == "mass" and normalization == "raw":
        units = "amu*Å^2/ps"
    else:
        units = "Å^2/ps"

    return VelocitySpectrumResult(
        frequencies_thz=frequencies,
        angular_frequencies_ps_inv=angular,
        wavenumbers_cm_inv=wavenumbers,
        energies_mev=energies,
        scalar_spectrum=scalar,
        component_spectra=components,
        tensor_spectrum=None,
        per_atom_scalar=per_atom_scalar,
        per_atom_components=per_atom_components,
        per_atom_indices=per_atom_indices,
        atom_indices=atom_indices,
        atom_weights=atom_weights,
        weight_sum=float(np.sum(atom_weights)),
        estimator="vacf_transform",
        weighting=weighting,
        normalization=normalization,
        correlation_weighting="reported",
        spectral_sidedness="one_sided",
        spectral_scaling="density",
        spectrum_units=units,
        sample_spacing_ps=sample_spacing_ps,
        n_samples=8,
        n_fft=n_fft,
        window=None,
        detrend=None,
        metadata={"fixture": True},
    )


def make_vdos() -> VDOSResult:
    return compute_vdos(make_spectrum(), normalization="unit_area")


@pytest.mark.parametrize(
    ("x_axis", "attribute", "label"),
    [
        ("thz", "frequencies_thz", "Frequency (THz)"),
        ("cm^-1", "wavenumbers_cm_inv", r"Wavenumber ($\mathrm{cm}^{-1}$)"),
        ("mev", "energies_mev", "Energy (meV)"),
    ],
)
def test_supported_horizontal_axes(x_axis: str, attribute: str, label: str) -> None:
    result = make_spectrum()
    fig, ax = plot_velocity_spectrum(result, x_axis=x_axis)
    np.testing.assert_allclose(ax.lines[0].get_xdata(), getattr(result, attribute))
    assert ax.get_xlabel() == label
    plt.close(fig)


def test_total_velocity_spectrum_is_not_silently_normalized() -> None:
    result = make_spectrum()
    original = result.scalar_spectrum.copy()
    fig, ax = plot_velocity_spectrum(result)
    np.testing.assert_allclose(ax.lines[0].get_ydata(), original)
    np.testing.assert_array_equal(result.scalar_spectrum, original)
    assert ax.get_ylabel() == (
        r"Velocity spectral density ($\mathrm{\AA}^2/\mathrm{ps}$)"
    )
    assert ax.get_legend() is None
    plt.close(fig)


def test_raw_mass_weighted_units_are_labeled() -> None:
    result = make_spectrum(weighting="mass", normalization="raw")
    fig, ax = plot_velocity_spectrum(result)
    assert ax.get_ylabel() == (
        r"Velocity spectral density ($\mathrm{amu}\,\mathrm{\AA}^2/\mathrm{ps}$)"
    )
    plt.close(fig)


def test_vdos_is_labeled_as_vdos_not_phonon_dos() -> None:
    result = make_vdos()
    fig, ax = plot_velocity_spectrum(result)
    assert ax.get_ylabel() == r"VDOS ($\mathrm{THz}^{-1}$)"
    assert "phonon" not in ax.get_ylabel().lower()
    np.testing.assert_allclose(ax.lines[0].get_ydata(), result.total)
    plt.close(fig)


def test_component_projection_draws_three_trace_curves() -> None:
    result = make_spectrum()
    fig, ax = plot_velocity_spectrum(result, projection="components")
    assert [line.get_label() for line in ax.lines] == [r"$x$", r"$y$", r"$z$"]
    for column, line in enumerate(ax.lines):
        np.testing.assert_allclose(line.get_ydata(), result.component_spectra[:, column])
    assert ax.get_legend() is not None
    plt.close(fig)


def test_explicit_per_atom_subset_preserves_request_order() -> None:
    result = make_spectrum(n_per_atom=4)
    fig, ax = plot_velocity_spectrum(
        result,
        projection="per_atom",
        atom_indices=[13, 10],
    )
    assert [line.get_label() for line in ax.lines] == ["Atom 13", "Atom 10"]
    np.testing.assert_allclose(ax.lines[0].get_ydata(), result.per_atom_scalar[:, 3])
    np.testing.assert_allclose(ax.lines[1].get_ydata(), result.per_atom_scalar[:, 0])
    plt.close(fig)


def test_small_per_atom_result_may_be_plotted_implicitly() -> None:
    result = make_spectrum(n_per_atom=3)
    fig, ax = plot_velocity_spectrum(result, projection="per_atom")
    assert [line.get_label() for line in ax.lines] == [
        "Atom 10",
        "Atom 11",
        "Atom 12",
    ]
    plt.close(fig)


def test_large_per_atom_result_requires_explicit_subset() -> None:
    result = make_spectrum(n_per_atom=13)
    with pytest.raises(ValueError, match="atom_indices explicitly"):
        plot_velocity_spectrum(result, projection="per_atom")


def test_missing_per_atom_data_is_rejected() -> None:
    with pytest.raises(ValueError, match="Per-atom spectral data are unavailable"):
        plot_velocity_spectrum(
            make_spectrum(include_per_atom=False), projection="per_atom"
        )


@pytest.mark.parametrize(
    ("indices", "message"),
    [
        ([], "must not be empty"),
        ([10, 10], "duplicates"),
        ([999], "absent"),
        ([10.0], "integers"),
    ],
)
def test_invalid_per_atom_requests_are_rejected(indices, message: str) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        plot_velocity_spectrum(
            make_spectrum(), projection="per_atom", atom_indices=indices
        )


def test_atom_indices_is_invalid_for_non_per_atom_projection() -> None:
    with pytest.raises(ValueError, match="only valid"):
        plot_velocity_spectrum(make_spectrum(), atom_indices=[10])


def test_display_normalization_uses_one_common_scale_without_mutation() -> None:
    result = make_spectrum()
    original = result.component_spectra.copy()
    fig, ax = plot_velocity_spectrum(
        result,
        projection="components",
        normalize_for_display=True,
    )
    scale = np.max(np.abs(original))
    for column, line in enumerate(ax.lines):
        np.testing.assert_allclose(line.get_ydata(), original[:, column] / scale)
    np.testing.assert_array_equal(result.component_spectra, original)
    assert ax.get_ylabel() == "Display-normalized intensity (arb. units)"
    plt.close(fig)


def test_existing_axes_are_reused() -> None:
    fig, supplied = plt.subplots()
    returned_fig, returned_ax = plot_velocity_spectrum(make_vdos(), ax=supplied)
    assert returned_fig is fig
    assert returned_ax is supplied
    plt.close(fig)


@pytest.mark.parametrize(
    ("keyword", "value", "message"),
    [
        ("x_axis", "hz", "x_axis"),
        ("projection", "tensor", "projection"),
        ("normalize_for_display", 1, "boolean"),
        ("ax", object(), "Axes"),
    ],
)
def test_invalid_public_options_are_rejected(keyword: str, value, message: str) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        plot_velocity_spectrum(make_spectrum(), **{keyword: value})


def test_invalid_result_type_is_rejected() -> None:
    with pytest.raises(TypeError, match="VelocitySpectrumResult or VDOSResult"):
        plot_velocity_spectrum(object())


def test_plotting_namespace_export_is_available() -> None:
    assert plotting.plot_velocity_spectrum is plot_velocity_spectrum
