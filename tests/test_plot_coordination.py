import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

from mdstats import PairCutoff
from mdstats.analysis.coordination import CoordinationResult
from mdstats.plotting import plot_coordination_distribution


def make_result(*, species_a: str = "Li") -> CoordinationResult:
    matrix = np.array([[3, 4], [4, 4], [3, 5]], dtype=np.int32)
    flat = matrix.ravel()
    counts = np.bincount(flat).astype(np.int64)
    return CoordinationResult(
        species_a=species_a,
        species_b="Cl",
        pair_cutoff=PairCutoff.manual(
            "Li" if species_a == "Li" else "K", "Cl", radius=3.5
        ),
        coordination_values=np.arange(counts.size, dtype=np.int32),
        counts=counts,
        probabilities=counts / flat.size,
        per_atom_per_frame=matrix,
        per_frame_mean=matrix.mean(axis=1),
        per_frame_std=matrix.std(axis=1),
        per_atom_mean=matrix.mean(axis=0),
        per_atom_std=matrix.std(axis=0),
        atom_indices_a=np.array([0, 1]),
        atom_indices_b=np.array([2, 3, 4]),
        frame_indices=np.array([0, 1, 2]),
        mean=float(flat.mean()),
        std=float(flat.std()),
        variance=float(flat.var()),
    )


def test_single_distribution_plot() -> None:
    fig, axes = plot_coordination_distribution(make_result())
    assert axes.shape == (1, 1)
    ax = axes[0, 0]
    assert len(ax.patches) == make_result().coordination_values.size
    assert ax.get_xlabel() == "Coordination number"
    assert ax.get_ylabel() == "Probability"
    plt.close(fig)


def test_two_results_use_one_by_two_atlas() -> None:
    fig, axes = plot_coordination_distribution(
        {"Li-Cl": make_result(), "K-Cl": make_result(species_a="K")},
        probability_unit="percent",
        title="Coordination distributions",
        sharey=True,
    )
    assert axes.shape == (1, 2)
    assert all(ax.get_ylabel() == "Probability (%)" for ax in axes.ravel())
    assert fig._suptitle is not None
    plt.close(fig)


def test_four_results_use_two_by_two_atlas() -> None:
    results = {
        "Li-Cl": make_result(species_a="Li"),
        "Na-Cl": make_result(species_a="Na"),
        "K-Cl": make_result(species_a="K"),
        "Rb-Cl": make_result(species_a="Rb"),
    }
    fig, axes = plot_coordination_distribution(results)
    assert axes.shape == (2, 2)
    assert all(ax.get_visible() for ax in axes.ravel())
    plt.close(fig)


def test_unused_atlas_panels_are_hidden() -> None:
    results = {
        "Li-Cl": make_result(species_a="Li"),
        "Na-Cl": make_result(species_a="Na"),
        "K-Cl": make_result(species_a="K"),
    }
    fig, axes = plot_coordination_distribution(results, ncols=2)
    assert axes.shape == (2, 2)
    assert sum(ax.get_visible() for ax in axes.ravel()) == 3
    plt.close(fig)


def test_user_supplied_axes_atlas_is_supported() -> None:
    fig, supplied = plt.subplots(2, 2)
    _, axes = plot_coordination_distribution(
        {"Li-Cl": make_result(), "K-Cl": make_result(species_a="K")},
        axes=supplied,
    )
    assert axes.shape == (2, 2)
    assert supplied[1, 0].get_visible() is False
    assert supplied[1, 1].get_visible() is False
    plt.close(fig)


def test_invalid_probability_unit_is_rejected() -> None:
    with pytest.raises(ValueError, match="probability_unit"):
        plot_coordination_distribution(make_result(), probability_unit="density")


def test_invalid_ncols_is_rejected() -> None:
    with pytest.raises(ValueError, match="ncols"):
        plot_coordination_distribution(make_result(), ncols=0)


def test_removed_average_coordination_plot_is_not_public() -> None:
    import mdstats
    import mdstats.plotting as plotting

    assert not hasattr(mdstats, "plot_coordination_number")
    assert not hasattr(plotting, "plot_coordination_number")


def test_x_axis_is_trimmed_to_nonzero_probability_support() -> None:
    fig, axes = plot_coordination_distribution(make_result())
    ax = axes[0, 0]
    xmin, xmax = ax.get_xlim()
    assert xmin == pytest.approx(3.0 - 0.55)
    assert xmax == pytest.approx(5.0 + 0.55)
    assert np.array_equal(ax.get_xticks(), np.array([3, 4, 5]))
    plt.close(fig)


def test_zero_probability_trimming_can_be_disabled() -> None:
    result = make_result()
    fig, axes = plot_coordination_distribution(
        result,
        trim_zero_probability=False,
    )
    assert np.array_equal(axes[0, 0].get_xticks(), result.coordination_values)
    plt.close(fig)


def test_annotation_opacity_is_configurable() -> None:
    fig, axes = plot_coordination_distribution(
        make_result(),
        annotation_text_alpha=0.4,
        annotation_box_alpha=0.1,
    )
    text = axes[0, 0].texts[0]
    assert text.get_alpha() == pytest.approx(0.4)
    assert text.get_bbox_patch().get_alpha() == pytest.approx(0.1)
    plt.close(fig)
