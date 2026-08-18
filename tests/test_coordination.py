"""Deterministic tests for integer coordination-state distributions."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from mdstats import (
    CoordinationResult,
    AtomisticFrameCollection,
    RDFResult,
    FrameCollectionProvenance,
    FrameSemantics,
    compute_coordination_distribution,
)
from mdstats.analysis import (
    CoordinationFrameMismatchWarning,
    IncompatibleRDFError,
    InvalidCoordinationCutoffError,
    InvalidCoordinationSelectionError,
)


def make_trajectory(
    cartesian_positions: np.ndarray,
    *,
    cells: np.ndarray | None = None,
    atomic_numbers: np.ndarray | None = None,
    pbc: np.ndarray | None = None,
) -> AtomisticFrameCollection:
    positions = np.asarray(cartesian_positions, dtype=float)
    if positions.ndim == 2:
        positions = positions[None, ...]
    n_frames, n_atoms, _ = positions.shape
    if cells is None:
        cells = np.repeat(np.eye(3)[None, :, :] * 10.0, n_frames, axis=0)
    else:
        cells = np.asarray(cells, dtype=float)
        if cells.shape == (3, 3):
            cells = np.repeat(cells[None, :, :], n_frames, axis=0)
    if atomic_numbers is None:
        atomic_numbers = np.ones(n_atoms, dtype=np.int32)
    if pbc is None:
        pbc = np.ones(3, dtype=bool)
    scaled = np.einsum("tni,tij->tnj", positions, np.linalg.inv(cells), optimize=True)
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.ENSEMBLE,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.asarray(atomic_numbers, dtype=np.int32),
        masses=np.ones(n_atoms),
        pbc=np.asarray(pbc, dtype=bool),
        steps=None,
        times=None,
        cells=cells,
        origins=np.zeros((n_frames, 3)),
        fractional_positions=scaled,
        velocities=None,
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("synthetic",),
            velocity_source="unavailable",
            coordinate_normalization="independent_frame_wrapping",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def make_compatible_rdf(
    *,
    indices_a: np.ndarray,
    indices_b: np.ndarray,
    frame_indices: np.ndarray,
    minimum_radius: float = 2.5,
    n_atoms_total: int = 4,
) -> RDFResult:
    edges = np.linspace(0.0, 4.0, 401)
    r = 0.5 * (edges[:-1] + edges[1:])
    first_peak = 3.0 * np.exp(-0.5 * ((r - 1.5) / 0.12) ** 2)
    second_peak = 1.5 * np.exp(-0.5 * ((r - 3.2) / 0.18) ** 2)
    valley_shape = 1.0 - 0.55 * np.exp(-0.5 * ((r - minimum_radius) / 0.22) ** 2)
    g_r = valley_shape + first_peak + second_peak
    shell_volumes = (4.0 * np.pi / 3.0) * (edges[1:] ** 3 - edges[:-1] ** 3)
    return RDFResult(
        species_a="Li",
        species_b="Cl",
        r=r,
        g_r=g_r,
        counts=np.zeros(r.size, dtype=np.int64),
        bin_edges=edges,
        shell_volumes=shell_volumes,
        cn_r=edges[1:],
        coordination_number=np.linspace(0.0, 4.0, r.size),
        atom_indices_a=indices_a,
        atom_indices_b=indices_b,
        frame_indices=frame_indices,
        n_frames=frame_indices.size,
        n_bins=r.size,
        r_max=4.0,
        average_volume=1000.0,
        metadata={"n_atoms_total": n_atoms_total},
    )


def test_known_distinct_species_coordination_distribution() -> None:
    positions = np.array(
        [
            [[0, 0, 0], [5, 0, 0], [1, 0, 0], [0, 1, 0]],
            [[0, 0, 0], [5, 0, 0], [1, 0, 0], [4, 0, 0]],
        ],
        dtype=float,
    )
    trajectory = make_trajectory(
        positions,
        atomic_numbers=np.array([3, 3, 17, 17]),
    )
    result = compute_coordination_distribution(trajectory, "Li", "Cl", cutoff=1.5)

    np.testing.assert_array_equal(result.per_atom_per_frame, [[2, 0], [1, 1]])
    np.testing.assert_array_equal(result.coordination_values, [0, 1, 2])
    np.testing.assert_array_equal(result.counts, [1, 2, 1])
    np.testing.assert_allclose(result.probabilities, [0.25, 0.5, 0.25])
    np.testing.assert_allclose(result.per_frame_mean, [1.0, 1.0])
    np.testing.assert_allclose(result.per_frame_std, [1.0, 0.0])
    np.testing.assert_allclose(result.per_atom_mean, [1.5, 0.5])
    np.testing.assert_allclose(result.per_atom_std, [0.5, 0.5])
    assert result.mean == pytest.approx(1.0)
    assert result.variance == pytest.approx(0.5)
    assert result.std == pytest.approx(np.sqrt(0.5))
    assert result.cutoff_source == "manual"
    assert result.cutoff_feature is None


def test_identical_selection_excludes_self_pairs() -> None:
    trajectory = make_trajectory(
        np.array([[0, 0, 0], [1, 0, 0], [3, 0, 0]], dtype=float),
        atomic_numbers=np.array([1, 1, 1]),
    )
    result = compute_coordination_distribution(trajectory, "H", "H", cutoff=1.5)
    np.testing.assert_array_equal(result.per_atom_per_frame, [[1, 1, 0]])
    np.testing.assert_array_equal(result.counts, [1, 2])


def test_single_atom_identical_selection_has_zero_coordination() -> None:
    trajectory = make_trajectory(
        np.array([[0, 0, 0]], dtype=float), atomic_numbers=np.array([1])
    )
    result = compute_coordination_distribution(trajectory, "H", "H", cutoff=1.0)
    np.testing.assert_array_equal(result.per_atom_per_frame, [[0]])
    assert result.probability_at(0) == 1.0


def test_strict_cutoff_excludes_equal_distance() -> None:
    trajectory = make_trajectory(
        np.array([[0, 0, 0], [1, 0, 0]], dtype=float),
        atomic_numbers=np.array([3, 17]),
    )
    result = compute_coordination_distribution(trajectory, "Li", "Cl", cutoff=1.0)
    np.testing.assert_array_equal(result.per_atom_per_frame, [[0]])


def test_triclinic_periodic_distance() -> None:
    cell = np.array([[4.0, 0.0, 0.0], [1.0, 4.0, 0.0], [0.5, 0.5, 4.0]])
    fractional = np.array([[0.95, 0.95, 0.95], [0.05, 0.05, 0.05]])
    positions = fractional @ cell
    distance = np.linalg.norm(np.array([0.1, 0.1, 0.1]) @ cell)
    trajectory = make_trajectory(
        positions, cells=cell, atomic_numbers=np.array([3, 17])
    )
    result = compute_coordination_distribution(
        trajectory, "Li", "Cl", cutoff=distance + 1.0e-4
    )
    np.testing.assert_array_equal(result.per_atom_per_frame, [[1]])


def test_frame_slicing() -> None:
    positions = np.array(
        [
            [[0, 0, 0], [0.5, 0, 0]],
            [[0, 0, 0], [2.0, 0, 0]],
            [[0, 0, 0], [0.5, 0, 0]],
            [[0, 0, 0], [2.0, 0, 0]],
        ],
        dtype=float,
    )
    trajectory = make_trajectory(positions, atomic_numbers=np.array([3, 17]))
    result = compute_coordination_distribution(
        trajectory,
        "Li",
        "Cl",
        cutoff=1.0,
        frame_start=0,
        frame_stop=4,
        frame_step=2,
    )
    np.testing.assert_array_equal(result.frame_indices, [0, 2])
    np.testing.assert_array_equal(result.per_atom_per_frame, [[1], [1]])


def test_rdf_derived_cutoff_and_provenance() -> None:
    trajectory = make_trajectory(
        np.array([[0, 0, 0], [1, 0, 0], [5, 0, 0], [6, 0, 0]], dtype=float),
        atomic_numbers=np.array([3, 17, 3, 17]),
    )
    rdf = make_compatible_rdf(
        indices_a=np.array([0, 2]),
        indices_b=np.array([1, 3]),
        frame_indices=np.array([0]),
    )
    result = compute_coordination_distribution(
        trajectory,
        "Li",
        "Cl",
        rdf_result=rdf,
        minimum_options={
            "smoothing_sigma": 0.04,
            "search_start": 0.8,
            "peak_prominence": 0.15,
            "minimum_prominence": 0.08,
            "minimum_width": 0.04,
            "smoothing_stability_check": False,
        },
    )
    assert result.cutoff_source == "rdf_first_minimum"
    assert result.cutoff_feature is not None
    assert result.cutoff == pytest.approx(result.cutoff_feature.radius)
    assert result.cutoff == pytest.approx(2.5, abs=0.2)


def test_rdf_incompatible_atom_selection_is_rejected() -> None:
    trajectory = make_trajectory(
        np.zeros((4, 3)), atomic_numbers=np.array([3, 17, 3, 17])
    )
    rdf = make_compatible_rdf(
        indices_a=np.array([0]),
        indices_b=np.array([1, 3]),
        frame_indices=np.array([0]),
    )
    with pytest.raises(IncompatibleRDFError, match="center-atom"):
        compute_coordination_distribution(trajectory, "Li", "Cl", rdf_result=rdf)


def test_rdf_frame_mismatch_warns_but_is_allowed() -> None:
    positions = np.array(
        [
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [4.0, 0.0, 0.0], [5.0, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [4.0, 0.0, 0.0], [5.0, 0.0, 0.0]],
        ]
    )
    trajectory = make_trajectory(positions, atomic_numbers=np.array([3, 17, 3, 17]))
    rdf = make_compatible_rdf(
        indices_a=np.array([0, 2]),
        indices_b=np.array([1, 3]),
        frame_indices=np.array([0]),
    )
    with pytest.warns(CoordinationFrameMismatchWarning):
        result = compute_coordination_distribution(
            trajectory,
            "Li",
            "Cl",
            rdf_result=rdf,
            minimum_options={
                "smoothing_sigma": 0.04,
                "search_start": 0.8,
                "peak_prominence": 0.15,
                "minimum_prominence": 0.08,
                "minimum_width": 0.04,
                "smoothing_stability_check": False,
            },
        )
    assert result.metadata["rdf_frame_relation"] == "rdf_subset_of_coordination"


def test_partial_overlap_and_invalid_cutoff_sources_are_rejected() -> None:
    trajectory = make_trajectory(np.zeros((3, 3)), atomic_numbers=np.array([1, 1, 1]))
    with pytest.raises(
        InvalidCoordinationSelectionError, match="Partially overlapping"
    ):
        compute_coordination_distribution(
            trajectory,
            atom_indices_a=[0, 1],
            atom_indices_b=[1, 2],
            cutoff=1.0,
        )
    with pytest.raises(InvalidCoordinationCutoffError, match="Exactly one"):
        compute_coordination_distribution(trajectory, "H", "H")
    with pytest.raises(InvalidCoordinationCutoffError, match="Exactly one"):
        compute_coordination_distribution(
            trajectory,
            "H",
            "H",
            cutoff=1.0,
            rdf_result=make_compatible_rdf(
                indices_a=np.array([0, 1, 2]),
                indices_b=np.array([0, 1, 2]),
                frame_indices=np.array([0]),
                n_atoms_total=3,
            ),
        )


def test_cutoff_above_safe_radius_is_rejected() -> None:
    trajectory = make_trajectory(
        np.array([[0, 0, 0], [1, 0, 0]], dtype=float),
        atomic_numbers=np.array([3, 17]),
    )
    with pytest.raises(InvalidCoordinationCutoffError, match="safe"):
        compute_coordination_distribution(trajectory, "Li", "Cl", cutoff=5.1)


def test_convenience_methods_and_tie_breaking() -> None:
    trajectory = make_trajectory(
        np.array(
            [
                [[0, 0, 0], [0.5, 0, 0]],
                [[0, 0, 0], [2.0, 0, 0]],
            ],
            dtype=float,
        ),
        atomic_numbers=np.array([3, 17]),
    )
    result = compute_coordination_distribution(trajectory, "Li", "Cl", cutoff=1.0)
    assert result.probability_at(0) == 0.5
    assert result.probability_at(1) == 0.5
    assert result.probability_at(5) == 0.0
    assert result.most_probable_coordination == 0
    with pytest.raises(TypeError):
        result.probability_at(1.5)


def test_dataframe_and_serialization_round_trip(tmp_path: Path) -> None:
    pd = pytest.importorskip("pandas")
    del pd
    trajectory = make_trajectory(
        np.array([[0, 0, 0], [0.5, 0, 0]], dtype=float),
        atomic_numbers=np.array([3, 17]),
    )
    result = compute_coordination_distribution(trajectory, "Li", "Cl", cutoff=1.0)
    dataframe = result.to_dataframe()
    assert list(dataframe.columns) == ["coordination", "count", "probability"]

    filename = tmp_path / "coordination.npz"
    result.save_npz(filename)
    restored = CoordinationResult.load_npz(filename)
    np.testing.assert_array_equal(
        restored.per_atom_per_frame, result.per_atom_per_frame
    )
    np.testing.assert_allclose(restored.probabilities, result.probabilities)
    assert restored.cutoff_source == result.cutoff_source
    assert restored.metadata["n_observations"] == result.metadata["n_observations"]
