"""Deterministic tests for pair RDF and coordination analysis."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import mdstats.analysis._neighbors as neighbors_module
from mdstats import (
    AtomisticFrameCollection,
    RDFResult,
    FrameCollectionProvenance,
    FrameSemantics,
    compute_pair_rdf,
)
from mdstats.analysis import InvalidRDFRangeError, InvalidSelectionError
from mdstats.analysis.rdf import compute_safe_r_max


def make_trajectory(
    cartesian_positions: np.ndarray,
    *,
    cells: np.ndarray | None = None,
    atomic_numbers: np.ndarray | None = None,
    pbc: np.ndarray | None = None,
) -> AtomisticFrameCollection:
    """Construct a valid synthetic AtomisticFrameCollection from Cartesian coordinates."""
    positions = np.asarray(cartesian_positions, dtype=np.float64)
    if positions.ndim == 2:
        positions = positions[None, ...]
    n_frames, n_atoms, _ = positions.shape

    if cells is None:
        cells = np.repeat(
            np.eye(3, dtype=np.float64)[None, :, :] * 10.0,
            n_frames,
            axis=0,
        )
    else:
        cells = np.asarray(cells, dtype=np.float64)
        if cells.shape == (3, 3):
            cells = np.repeat(cells[None, ...], n_frames, axis=0)

    if atomic_numbers is None:
        atomic_numbers = np.ones(n_atoms, dtype=np.int32)
    if pbc is None:
        pbc = np.ones(3, dtype=bool)

    inverse_cells = np.linalg.inv(cells)
    scaled = np.einsum("tni,tij->tnj", positions, inverse_cells, optimize=True)

    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.ENSEMBLE,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.asarray(atomic_numbers, dtype=np.int32),
        masses=np.ones(n_atoms, dtype=np.float64),
        pbc=np.asarray(pbc, dtype=bool),
        steps=None,
        times=None,
        cells=cells,
        origins=np.zeros((n_frames, 3), dtype=np.float64),
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


def test_cross_pair_histogram_and_coordination() -> None:
    trajectory = make_trajectory(
        np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        atomic_numbers=np.array([11, 8]),
    )

    rdf = compute_pair_rdf(trajectory, "Na", "O", r_max=4.0, n_bins=4)

    np.testing.assert_array_equal(rdf.counts, [0, 1, 0, 0])
    assert rdf.coordination_number[-1] == pytest.approx(1.0)
    expected = 1000.0 / rdf.shell_volumes[1]
    assert rdf.g_r[1] == pytest.approx(expected)
    assert rdf.species_a == "Na"
    assert rdf.species_b == "O"


def test_identical_group_counts_unordered_pairs_once() -> None:
    trajectory = make_trajectory(
        np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [3.0, 0.0, 0.0]]),
        atomic_numbers=np.array([1, 1, 1]),
    )

    rdf = compute_pair_rdf(trajectory, "H", "H", r_max=4.0, n_bins=4)

    np.testing.assert_array_equal(rdf.counts, [0, 1, 1, 1])
    assert rdf.counts.sum() == 3
    assert rdf.coordination_number[-1] == pytest.approx(2.0)


def test_triclinic_minimum_image_distance() -> None:
    cell = np.array([[4.0, 0.0, 0.0], [1.0, 4.0, 0.0], [0.5, 0.5, 4.0]])
    fractional = np.array([[0.95, 0.95, 0.95], [0.05, 0.05, 0.05]])
    positions = fractional @ cell
    expected_distance = np.linalg.norm(np.array([0.1, 0.1, 0.1]) @ cell)

    trajectory = make_trajectory(
        positions,
        cells=cell,
        atomic_numbers=np.array([11, 8]),
    )
    rdf = compute_pair_rdf(trajectory, "Na", "O", r_max=1.5, n_bins=150)

    occupied = np.flatnonzero(rdf.counts)
    assert occupied.size == 1
    assert rdf.r[occupied[0]] == pytest.approx(expected_distance, abs=0.01)


def test_safe_radius_for_cubic_cell() -> None:
    trajectory = make_trajectory(
        np.zeros((1, 1, 3)),
        cells=np.diag([10.0, 12.0, 14.0]),
    )
    safe = compute_safe_r_max(trajectory, np.array([0], dtype=np.int64))
    assert safe == pytest.approx(5.0)




def test_safe_radius_for_lta_primitive_cell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    a = 17.3630
    cell = np.array(
        [
            [a, 0.0, 0.0],
            [0.5 * a, np.sqrt(3.0) * 0.5 * a, 0.0],
            [0.5 * a, a / (2.0 * np.sqrt(3.0)), a * np.sqrt(2.0 / 3.0)],
        ]
    )
    monkeypatch.setattr(
        neighbors_module,
        "minkowski_reduce",
        lambda input_cell, pbc: (np.asarray(input_cell), np.eye(3, dtype=int)),
    )
    monkeypatch.setattr(
        neighbors_module,
        "is_minkowski_reduced",
        lambda input_cell, pbc: True,
    )
    trajectory = make_trajectory(np.zeros((1, 1, 3)), cells=cell)

    safe = compute_safe_r_max(trajectory, np.array([0], dtype=np.int64))

    assert safe == pytest.approx(0.5 * a)
    assert safe > 8.0


def test_random_cross_rdf_approaches_unity() -> None:
    rng = np.random.default_rng(12345)
    n_frames = 60
    n_a = 70
    n_b = 90
    box = 20.0
    positions = rng.uniform(0.0, box, size=(n_frames, n_a + n_b, 3))
    trajectory = make_trajectory(
        positions,
        cells=np.diag([box, box, box]),
        atomic_numbers=np.array([11] * n_a + [8] * n_b),
    )

    rdf = compute_pair_rdf(
        trajectory,
        "Na",
        "O",
        r_max=8.0,
        n_bins=80,
        block_size=32,
    )

    middle = (rdf.r > 2.0) & (rdf.r < 7.5)
    assert np.mean(rdf.g_r[middle]) == pytest.approx(1.0, abs=0.04)

    expected_cn = n_b * (4.0 * np.pi / 3.0) * 8.0**3 / box**3
    assert rdf.coordination_number[-1] == pytest.approx(expected_cn, abs=0.7)


def make_synthetic_feature_rdf() -> RDFResult:
    edges = np.linspace(0.0, 6.0, 601)
    r = 0.5 * (edges[:-1] + edges[1:])
    shell_volumes = (4.0 * np.pi / 3.0) * (edges[1:] ** 3 - edges[:-1] ** 3)

    baseline = 1.0 - np.exp(-((r / 1.2) ** 8))
    first_peak = 3.0 * np.exp(-0.5 * ((r - 2.0) / 0.18) ** 2)
    second_peak = 1.7 * np.exp(-0.5 * ((r - 4.0) / 0.28) ** 2)
    g_r = baseline + first_peak + second_peak
    cn_r = edges[1:]
    coordination = 6.0 * (1.0 - np.exp(-((cn_r / 3.2) ** 3)))

    return RDFResult(
        species_a="Na",
        species_b="O",
        r=r,
        g_r=g_r,
        counts=np.zeros(r.size, dtype=np.int64),
        bin_edges=edges,
        shell_volumes=shell_volumes,
        cn_r=cn_r,
        coordination_number=coordination,
        atom_indices_a=np.array([0], dtype=np.int64),
        atom_indices_b=np.array([1], dtype=np.int64),
        frame_indices=np.array([0], dtype=np.int64),
        n_frames=1,
        n_bins=r.size,
        r_max=6.0,
        average_volume=1000.0,
    )


def test_first_peak_detection() -> None:
    rdf = make_synthetic_feature_rdf()
    feature = rdf.first_peak(
        smoothing_sigma=0.05,
        search_start=0.8,
        prominence=0.2,
        minimum_width=0.05,
    )

    assert feature.kind == "peak"
    assert feature.radius == pytest.approx(2.0, abs=0.10)
    assert feature.value > 1.0
    assert feature.prominence is not None
    assert feature.width is not None


def test_first_minimum_and_first_shell_coordination() -> None:
    rdf = make_synthetic_feature_rdf()
    feature = rdf.first_minimum(
        smoothing_sigma=0.05,
        search_start=0.8,
        peak_prominence=0.2,
        minimum_prominence=0.1,
        minimum_width=0.05,
        stability_tolerance=0.08,
    )
    assert feature.radius == pytest.approx(3.0, abs=0.20)
    assert feature.confidence in {"high", "medium"}
    assert feature.stability_std is not None

    cn, returned = rdf.first_shell_coordination(
        return_feature=True,
        smoothing_sigma=0.05,
        search_start=0.8,
        peak_prominence=0.2,
        minimum_prominence=0.1,
        minimum_width=0.05,
        stability_tolerance=0.08,
    )
    assert returned.radius == feature.radius
    assert cn == pytest.approx(rdf.coordination_at(feature.radius))


def test_explicit_indices_are_validated_against_species() -> None:
    trajectory = make_trajectory(
        np.array([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [3.0, 0.0, 0.0]]),
        atomic_numbers=np.array([11, 11, 8]),
    )

    rdf = compute_pair_rdf(
        trajectory,
        "Na",
        "O",
        atom_indices_a=[1],
        atom_indices_b=[2],
        r_max=4.0,
        n_bins=20,
    )
    np.testing.assert_array_equal(rdf.atom_indices_a, [1])
    np.testing.assert_array_equal(rdf.atom_indices_b, [2])

    with pytest.raises(InvalidSelectionError, match="outside its species"):
        compute_pair_rdf(
            trajectory,
            "Na",
            "O",
            atom_indices_a=[2],
            atom_indices_b=[2],
            r_max=4.0,
        )


def test_partially_overlapping_groups_are_rejected() -> None:
    trajectory = make_trajectory(
        np.zeros((3, 3)),
        atomic_numbers=np.array([1, 1, 1]),
    )
    with pytest.raises(InvalidSelectionError, match="Partially overlapping"):
        compute_pair_rdf(
            trajectory,
            "H",
            "H",
            r_max=4.0,
            atom_indices_a=[0, 1],
            atom_indices_b=[1, 2],
        )


def test_rmax_above_safe_limit_is_rejected() -> None:
    trajectory = make_trajectory(
        np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        atomic_numbers=np.array([11, 8]),
    )
    with pytest.raises(InvalidRDFRangeError):
        compute_pair_rdf(trajectory, "Na", "O", r_max=5.1)


def test_dataframe_and_npz_serialization(tmp_path: Path) -> None:
    pd = pytest.importorskip("pandas")
    del pd
    rdf = make_synthetic_feature_rdf()
    dataframe = rdf.to_dataframe()
    assert list(dataframe.columns) == [
        "r",
        "g_r",
        "counts",
        "shell_volume",
        "cn_r",
        "coordination_number",
    ]

    output = tmp_path / "rdf.npz"
    rdf.metadata["example"] = np.int64(3)
    rdf.save_npz(output)
    archive = np.load(output)
    np.testing.assert_allclose(archive["g_r"], rdf.g_r)
    assert json.loads(str(archive["metadata_json"].item()))["example"] == 3


def test_variable_cell_uses_framewise_normalization() -> None:
    positions = np.array(
        [
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [5.0, 0.0, 0.0]],
        ]
    )
    cells = np.array([np.diag([10.0, 10.0, 10.0]), np.diag([12.0, 12.0, 12.0])])
    trajectory = make_trajectory(
        positions,
        cells=cells,
        atomic_numbers=np.array([11, 8]),
    )

    rdf = compute_pair_rdf(trajectory, "Na", "O", r_max=4.0, n_bins=4)
    expected_g = 0.5 * 1000.0 / rdf.shell_volumes[1]
    assert rdf.g_r[1] == pytest.approx(expected_g)
    assert rdf.coordination_number[-1] == pytest.approx(0.5)


def test_cross_species_symmetry_and_coordination_identity() -> None:
    rng = np.random.default_rng(9)
    n_a, n_b = 8, 11
    positions = rng.uniform(0.0, 10.0, size=(5, n_a + n_b, 3))
    trajectory = make_trajectory(
        positions,
        atomic_numbers=np.array([11] * n_a + [8] * n_b),
    )

    rdf_ab = compute_pair_rdf(trajectory, "Na", "O", r_max=4.0, n_bins=40)
    rdf_ba = compute_pair_rdf(trajectory, "O", "Na", r_max=4.0, n_bins=40)

    np.testing.assert_allclose(rdf_ab.g_r, rdf_ba.g_r)
    np.testing.assert_allclose(
        n_a * rdf_ab.coordination_number,
        n_b * rdf_ba.coordination_number,
    )


def test_frame_slice_and_explicit_only_selections() -> None:
    positions = np.array(
        [
            [[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [1.5, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [2.5, 0.0, 0.0]],
        ]
    )
    trajectory = make_trajectory(
        positions,
        atomic_numbers=np.array([11, 8]),
    )

    rdf = compute_pair_rdf(
        trajectory,
        atom_indices_a=[0],
        atom_indices_b=[1],
        frame_start=1,
        frame_stop=3,
        r_max=4.0,
        n_bins=4,
    )

    np.testing.assert_array_equal(rdf.frame_indices, [1, 2])
    np.testing.assert_array_equal(rdf.counts, [0, 1, 1, 0])
    assert rdf.species_a == "indices[1]"
    assert rdf.species_b == "indices[1]"


def test_public_rdf_result_name_is_consistent():
    import mdstats
    import mdstats.analysis as analysis

    assert mdstats.RDFResult is RDFResult
    assert analysis.RDFResult is RDFResult
    assert not hasattr(mdstats, "PairRDF")
    assert not hasattr(analysis, "PairRDF")
