import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

from mdstats.analysis.msd import MSDResult
from mdstats.plotting import plot_msd


def make_result(*, per_atom: bool = True) -> MSDResult:
    times = np.array([0.0, 1.0, 2.0])
    components = np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0], [2.0, 4.0, 6.0]])
    atom_data = np.array([[0.0, 0.0], [2.0, 4.0], [4.0, 8.0]]) if per_atom else None
    return MSDResult(
        lag_steps=np.array([0, 1, 2]),
        lag_times=times,
        msd=components.sum(axis=1),
        components=components,
        tensor=np.array([np.diag(row) for row in components]),
        per_atom_msd=atom_data,
        n_origins=np.array([3, 2, 1]),
        atom_indices=np.array([4, 9]),
        n_atoms=2,
        mode="time_averaged",
        coordinate_mode="laboratory",
        drift_mode=None,
        reference_cell=None,
    )


def test_plot_scalar_and_components():
    fig, ax = plot_msd(make_result(), show_components=True, time_unit="fs")
    assert len(ax.lines) == 4
    assert ax.get_xlabel() == "Time lag (fs)"
    assert ax.get_ylabel() == r"MSD ($\mathrm{\AA}^2$)"
    plt.close(fig)


def test_plot_selected_per_atom_curves():
    fig, ax = plot_msd(
        make_result(), show_per_atom=True, per_atom_indices=[9], time_unit="ps"
    )
    labels = [line.get_label() for line in ax.lines]
    assert labels == ["Time-averaged MSD", "Atom 9"]
    plt.close(fig)


def test_missing_per_atom_data_is_rejected():
    with pytest.raises(ValueError, match="per_atom=True"):
        plot_msd(make_result(per_atom=False), show_per_atom=True)


def test_plot_multiple_species_from_mapping():
    na = make_result()
    k = make_result()
    fig, ax = plot_msd({"Na": na, "K": k})
    assert [line.get_label() for line in ax.lines] == ["Na", "K"]
    assert ax.get_legend() is not None
    plt.close(fig)


def test_plot_multiple_results_from_sequence_with_labels():
    fig, ax = plot_msd([make_result(), make_result()], labels=["Li", "Na"])
    assert [line.get_label() for line in ax.lines] == ["Li", "Na"]
    plt.close(fig)


def test_plot_atoms_across_multiple_results_with_custom_labels():
    first = make_result()
    second = make_result()
    fig, ax = plot_msd(
        {"Species A": first, "Species B": second},
        show_per_atom=True,
        per_atom_indices=[9],
        atom_labels={9: "site atom 9"},
    )
    assert [line.get_label() for line in ax.lines] == [
        "Species A",
        "Species A: site atom 9",
        "Species B",
        "Species B: site atom 9",
    ]
    plt.close(fig)
