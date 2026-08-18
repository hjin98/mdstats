import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from mdstats.analysis.rdf import RDFResult
from mdstats.plotting import plot_pair_rdf


def make_rdf(*, species_a: str = "Na", species_b: str = "O") -> RDFResult:
    r = np.linspace(0.5, 4.5, 9)
    g_r = np.array([0.0, 0.2, 1.4, 2.5, 1.1, 0.35, 0.8, 1.2, 1.0])
    bin_edges = np.linspace(0.25, 4.75, 10)
    shell_volumes = 4.0 * np.pi / 3.0 * (bin_edges[1:] ** 3 - bin_edges[:-1] ** 3)
    cn = np.array([0.0, 0.05, 0.4, 1.2, 2.0, 2.2, 2.5, 2.9, 3.1])
    return RDFResult(
        species_a=species_a,
        species_b=species_b,
        r=r,
        g_r=g_r,
        counts=np.arange(9, dtype=np.int64),
        bin_edges=bin_edges,
        shell_volumes=shell_volumes,
        cn_r=r.copy(),
        coordination_number=cn,
        atom_indices_a=np.array([0, 1], dtype=np.int64),
        atom_indices_b=np.array([2, 3, 4], dtype=np.int64),
        frame_indices=np.array([0, 1, 2], dtype=np.int64),
        n_frames=3,
        n_bins=9,
        r_max=float(bin_edges[-1]),
        average_volume=1000.0,
        metadata={},
    )


def test_plot_single_pair_rdf():
    fig, ax = plot_pair_rdf(make_rdf(), label="Na-O")
    assert len(ax.lines) == 1
    assert ax.get_xlabel() == r"Distance $r$ ($\mathrm{\AA}$)"
    assert ax.get_ylabel() == r"$g(r)$"
    plt.close(fig)


def test_plot_multiple_pair_rdf_with_legend():
    fig, ax = plot_pair_rdf({"Na-O": make_rdf(), "K-O": make_rdf(species_a="K")})
    labels = [line.get_label() for line in ax.lines]
    assert labels == ["Na-O", "K-O"]
    assert ax.get_legend() is not None
    plt.close(fig)


def test_plot_smoothed_pair_rdf_draws_raw_and_smooth():
    fig, ax = plot_pair_rdf(make_rdf(), smoothing_sigma=0.10, show_raw=True)
    assert len(ax.lines) == 2
    plt.close(fig)


def test_plot_pair_rdf_marks_and_labels_first_peak_and_minimum():
    fig, ax = plot_pair_rdf(
        make_rdf(),
        show_first_peak=True,
        show_first_minimum=True,
        first_peak_options={"smoothing_sigma": 0.05},
        first_minimum_options={
            "smoothing_sigma": 0.05,
            "smoothing_stability_check": False,
        },
    )

    annotation_text = [text.get_text() for text in ax.texts]
    assert any(
        "First peak:" in text and "\\mathrm{\\AA}" in text for text in annotation_text
    )
    assert any(
        "First minimum:" in text and "\\mathrm{\\AA}" in text
        for text in annotation_text
    )
    assert len(ax.lines) >= 5
    plt.close(fig)


def test_plot_pair_rdf_forwards_first_peak_options():
    rdf = make_rdf()
    fig, ax = plot_pair_rdf(
        rdf,
        show_first_peak=True,
        first_peak_options={
            "smoothing_sigma": 0.05,
            "search_start": 0.5,
            "search_max": 3.0,
            "prominence": 0.05,
        },
    )

    expected = rdf.first_peak(
        smoothing_sigma=0.05,
        search_start=0.5,
        search_max=3.0,
        prominence=0.05,
    )
    annotation_text = [text.get_text() for text in ax.texts]
    assert any(f"First peak: {expected.radius:.2f}" in text for text in annotation_text)
    plt.close(fig)


def test_feature_labels_stay_inside_axes_and_do_not_overlap():
    first = make_rdf(species_a="Li", species_b="Cl")
    second = make_rdf(species_a="K", species_b="Cl")

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    plot_pair_rdf(
        {"Li-Cl": first, "K-Cl": second},
        ax=ax,
        title="LiCl-KCl partial radial distribution functions",
        show_first_peak=True,
        show_first_minimum=True,
        first_peak_options={"smoothing_sigma": 0.05},
        first_minimum_options={
            "smoothing_sigma": 0.05,
            "smoothing_stability_check": False,
        },
    )

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    axes_box = ax.get_window_extent(renderer)
    annotation_boxes = [
        text.get_bbox_patch().get_window_extent(renderer) for text in ax.texts
    ]

    assert len(annotation_boxes) == 4
    for box in annotation_boxes:
        assert box.x0 >= axes_box.x0 - 1.0
        assert box.x1 <= axes_box.x1 + 1.0
        assert box.y0 >= axes_box.y0 - 1.0
        assert box.y1 <= axes_box.y1 + 1.0

    for index, first_box in enumerate(annotation_boxes):
        for second_box in annotation_boxes[index + 1 :]:
            assert not first_box.overlaps(second_box)

    legend = ax.get_legend()
    assert legend is not None
    legend_box = legend.get_window_extent(renderer)
    assert all(not box.overlaps(legend_box) for box in annotation_boxes)

    title_box = ax.title.get_window_extent(renderer)
    assert all(not box.overlaps(title_box) for box in annotation_boxes)
    plt.close(fig)


def test_feature_annotation_opacity_is_configurable():
    fig, ax = plot_pair_rdf(
        make_rdf(),
        show_first_peak=True,
        show_first_minimum=True,
        first_peak_options={"smoothing_sigma": 0.05},
        first_minimum_options={
            "smoothing_sigma": 0.05,
            "smoothing_stability_check": False,
        },
        feature_annotation_text_alpha=0.35,
        feature_annotation_box_alpha=0.08,
        feature_annotation_arrow_alpha=0.25,
    )

    assert len(ax.texts) == 2
    for text in ax.texts:
        assert text.get_alpha() == 0.35
        assert text.get_bbox_patch().get_alpha() == 0.08
        assert text.arrow_patch is not None
        assert text.arrow_patch.get_alpha() == 0.25
    plt.close(fig)


def test_invalid_feature_annotation_opacity_is_rejected():
    import pytest

    with pytest.raises(ValueError, match="feature_annotation_box_alpha"):
        plot_pair_rdf(make_rdf(), feature_annotation_box_alpha=1.1)
