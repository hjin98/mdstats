import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

from mdstats import plot_vacf_diffusion
import mdstats.plotting as plotting
from mdstats.analysis.vacf_transport import VACFDiffusionResult


def make_result(*, component: str = "scalar", scale: float = 1.0) -> VACFDiffusionResult:
    times = np.array([0.0, 0.1, 0.2, 0.3], dtype=np.float64)
    integrand = scale * np.array([1.0, 0.8, 0.4, 0.0], dtype=np.float64)
    running = np.array([0.0, 0.09, 0.15, 0.17], dtype=np.float64) * scale
    return VACFDiffusionResult(
        lag_times=times,
        running_diffusion_a2_per_ps=running,
        integrand=integrand,
        dimensions=3,
        component=component,
        weighting="uniform",
        integration="trapezoid",
        metadata={"fixture": True},
    )


def test_public_exports() -> None:
    assert plotting.plot_vacf_diffusion is plot_vacf_diffusion


def test_internal_units_and_no_mutation() -> None:
    result = make_result()
    original = result.running_diffusion_a2_per_ps.copy()
    fig, ax = plot_vacf_diffusion(
        result,
        diffusion_unit="angstrom2/ps",
        show_zero_line=False,
    )
    np.testing.assert_allclose(ax.lines[0].get_xdata(), result.lag_times)
    np.testing.assert_allclose(ax.lines[0].get_ydata(), original)
    np.testing.assert_array_equal(result.running_diffusion_a2_per_ps, original)
    assert ax.get_ylabel() == (
        r"Running self-diffusion $D(t)$ ($\mathrm{\AA}^2/\mathrm{ps}$)"
    )
    plt.close(fig)


def test_cm2_per_s_and_fs_axes() -> None:
    result = make_result()
    fig, ax = plot_vacf_diffusion(
        result,
        time_unit="fs",
        diffusion_unit="cm2/s",
        show_zero_line=False,
    )
    np.testing.assert_allclose(ax.lines[0].get_xdata(), 1000.0 * result.lag_times)
    np.testing.assert_allclose(
        ax.lines[0].get_ydata(), result.running_diffusion_cm2_per_s
    )
    assert ax.get_xlabel() == "Time lag (fs)"
    assert ax.get_ylabel() == (
        r"Running self-diffusion $D(t)$ ($\mathrm{cm}^2/\mathrm{s}$)"
    )
    plt.close(fig)


def test_mapping_draws_labeled_multiple_curves() -> None:
    first = make_result(scale=1.0)
    second = make_result(component="x", scale=0.5)
    fig, ax = plot_vacf_diffusion(
        {"Na": first, "Li": second},
        show_zero_line=False,
    )
    assert [line.get_label() for line in ax.lines] == ["Na", "Li"]
    assert ax.get_legend() is not None
    plt.close(fig)


def test_single_explicit_label_requests_legend() -> None:
    fig, ax = plot_vacf_diffusion(
        make_result(), label="Na", show_zero_line=False
    )
    assert ax.lines[0].get_label() == "Na"
    assert ax.get_legend() is not None
    plt.close(fig)


def test_zero_reference_is_optional() -> None:
    fig, ax = plot_vacf_diffusion(make_result(), show_zero_line=True)
    assert len(ax.lines) == 2
    np.testing.assert_allclose(ax.lines[1].get_ydata(), [0.0, 0.0])
    plt.close(fig)


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"time_unit": "minute"}, "time_unit"),
        ({"diffusion_unit": "m2/s"}, "diffusion_unit"),
        ({"show_zero_line": 1}, "show_zero_line"),
        ({"grid": 1}, "grid"),
    ],
)
def test_invalid_options_fail(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        plot_vacf_diffusion(make_result(), **kwargs)


def test_label_contracts() -> None:
    with pytest.raises(ValueError, match="labels is only valid"):
        plot_vacf_diffusion(make_result(), labels=["Na"])
    with pytest.raises(ValueError, match="label is only valid"):
        plot_vacf_diffusion([make_result()], label="Na")
    with pytest.raises(ValueError, match="same length"):
        plot_vacf_diffusion([make_result(), make_result()], labels=["Na"])
