"""Focused C0-C1 tests for collective charge currents and correlations."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

import mdstats
from mdstats import (
    AtomisticFrameCollection,
    ChargeCurrentResult,
    CurrentCorrelationResult,
    FrameCollectionProvenance,
    FrameSemantics,
    compute_charge_current,
    compute_current_correlation,
)


def make_collection(
    velocities: np.ndarray,
    *,
    atomic_numbers: np.ndarray | None = None,
    masses: np.ndarray | None = None,
    times: np.ndarray | None = None,
    cells: np.ndarray | None = None,
    pbc: np.ndarray | None = None,
) -> AtomisticFrameCollection:
    velocities = np.asarray(velocities, dtype=np.float64)
    n_frames, n_atoms, _ = velocities.shape
    if atomic_numbers is None:
        atomic_numbers = np.array([11, 17] + [1] * max(0, n_atoms - 2), dtype=np.int32)
    if masses is None:
        masses = np.arange(1, n_atoms + 1, dtype=np.float64)
    if times is None:
        times = np.arange(n_frames, dtype=np.float64) * 0.2
    if cells is None:
        cells = np.repeat(np.eye(3)[None, :, :] * 10.0, n_frames, axis=0)
    if pbc is None:
        pbc = np.array([True, True, True])
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.asarray(atomic_numbers, dtype=np.int32),
        masses=np.asarray(masses, dtype=np.float64),
        pbc=np.asarray(pbc, dtype=np.bool_),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.asarray(times, dtype=np.float64),
        cells=np.asarray(cells, dtype=np.float64),
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=np.zeros((n_frames, n_atoms, 3), dtype=np.float64),
        velocities=velocities,
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("current-synthetic",),
            velocity_source="native",
            coordinate_normalization="native_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def test_array_and_species_charge_sources_agree() -> None:
    rng = np.random.default_rng(3)
    collection = make_collection(
        rng.normal(size=(8, 2, 3)),
        atomic_numbers=np.array([11, 17]),
    )
    array = compute_charge_current(collection, charges=[1.0, -1.0])
    mapped = compute_charge_current(
        collection,
        species_charges={"Na": 1.0, "Cl": -1.0},
    )
    np.testing.assert_allclose(array.total_current, mapped.total_current)
    np.testing.assert_allclose(mapped.charges_e, [1.0, -1.0])
    assert mapped.metadata["charge_source"] == "species_map"
    assert mapped.metadata["current_units"] == "e*Angstrom/ps"


def test_charge_source_validation_and_neutrality() -> None:
    collection = make_collection(np.zeros((5, 2, 3)))
    with pytest.raises(ValueError, match="exactly one"):
        compute_charge_current(collection)
    with pytest.raises(ValueError, match="exactly one"):
        compute_charge_current(
            collection,
            charges=[1.0, -1.0],
            species_charges={"Na": 1.0, "Cl": -1.0},
        )
    with pytest.raises(ValueError, match="shape"):
        compute_charge_current(collection, charges=[0.0])
    with pytest.raises(TypeError, match="booleans"):
        compute_charge_current(collection, charges=[True, False])
    with pytest.raises(ValueError, match="finite"):
        compute_charge_current(collection, charges=[np.nan, 0.0])
    with pytest.raises(TypeError, match="integer keys"):
        compute_charge_current(collection, species_charges={11: 1.0, "Cl": -1.0})  # type: ignore[dict-item]
    with pytest.raises(ValueError, match="missing"):
        compute_charge_current(collection, species_charges={"Na": 1.0})
    with pytest.raises(ValueError, match="unused"):
        compute_charge_current(
            collection,
            species_charges={"Na": 1.0, "Cl": -1.0, "K": 0.0},
        )
    with pytest.raises(ValueError, match="exceeds"):
        compute_charge_current(collection, charges=[1.0, 0.0])
    with pytest.raises(ValueError, match="nonzero"):
        compute_charge_current(collection, charges=[0.0, 0.0])

    accepted = compute_charge_current(
        collection,
        charges=[1.0, -1.0 + 5.0e-13],
        neutrality_tolerance_e=1.0e-12,
    )
    assert abs(accepted.total_charge_e) <= accepted.neutrality_tolerance_e
    with pytest.raises(TypeError, match="real number"):
        compute_charge_current(
            collection,
            charges=[1.0, -1.0],
            neutrality_tolerance_e=True,  # type: ignore[arg-type]
        )


def test_neutral_rigid_translation_and_paired_charge_algebra() -> None:
    translation = np.array([2.0, -1.5, 0.25])
    velocities = np.repeat(translation[None, None, :], 7, axis=0)
    velocities = np.repeat(velocities, 2, axis=1)
    collection = make_collection(velocities)
    result = compute_charge_current(collection, charges=[1.0, -1.0])
    np.testing.assert_allclose(result.total_current, 0.0, atol=1.0e-14)

    velocities = np.zeros((4, 2, 3), dtype=np.float64)
    velocities[:, 0] = np.array([1.0, 2.0, 3.0])
    velocities[:, 1] = np.array([0.25, -1.0, 4.0])
    collection = make_collection(velocities)
    result = compute_charge_current(collection, charges=[2.0, -2.0])
    expected = 2.0 * velocities[:, 0] - 2.0 * velocities[:, 1]
    np.testing.assert_allclose(result.total_current, expected)



def test_constant_nonzero_current_is_not_mean_subtracted() -> None:
    velocities = np.zeros((8, 2, 3), dtype=np.float64)
    velocities[:, 0, 0] = 2.0
    collection = make_collection(velocities)
    current = compute_charge_current(collection, charges=[1.0, -1.0])
    np.testing.assert_allclose(current.total_current[:, 0], 2.0)

    correlation = compute_current_correlation(
        current,
        max_lag=4,
        backend="direct",
        compute_tensor=True,
    )
    np.testing.assert_allclose(correlation.scalar, 4.0)
    np.testing.assert_allclose(correlation.components[:, 0], 4.0)
    np.testing.assert_allclose(correlation.components[:, 1:], 0.0)
    np.testing.assert_allclose(correlation.tensor[:, 0, 0], 4.0)
    assert correlation.metadata["mean_current_subtracted"] is False

def test_drift_provenance_and_neutral_total_invariance() -> None:
    rng = np.random.default_rng(5)
    velocities = rng.normal(size=(9, 3, 3))
    collection = make_collection(
        velocities,
        atomic_numbers=np.array([11, 17, 1]),
        masses=np.array([23.0, 35.0, 1.0]),
    )
    raw = compute_charge_current(collection, charges=[1.0, -1.0, 0.0])
    corrected = compute_charge_current(
        collection,
        charges=[1.0, -1.0, 0.0],
        drift_mode="center_of_mass",
        drift_atom_indices=[2, 0],
    )
    np.testing.assert_allclose(corrected.total_current, raw.total_current, atol=2e-14)
    np.testing.assert_array_equal(corrected.signature.drift_atom_indices, [2, 0])
    assert corrected.signature.drift_mode == "center_of_mass"


def test_exact_group_partition_and_failures() -> None:
    velocities = np.zeros((6, 4, 3), dtype=np.float64)
    velocities[:, :, 0] = np.array([1.0, 2.0, -3.0, 4.0])
    collection = make_collection(
        velocities,
        atomic_numbers=np.array([11, 11, 17, 17]),
    )
    result = compute_charge_current(
        collection,
        charges=[1.0, 1.0, -1.0, -1.0],
        species_groups={"cation": "Na", "anion": "Cl"},
    )
    assert result.group_names == ("cation", "anion")
    np.testing.assert_array_equal(result.group_atom_indices["cation"], [0, 1])
    np.testing.assert_array_equal(result.group_atom_indices["anion"], [2, 3])
    np.testing.assert_allclose(np.sum(result.group_currents, axis=1), result.total_current)

    with pytest.raises(ValueError, match="cover"):
        compute_charge_current(
            collection,
            charges=[1.0, 1.0, -1.0, -1.0],
            species_groups={"cation": "Na"},
        )
    with pytest.raises(ValueError, match="overlap"):
        compute_charge_current(
            collection,
            charges=[1.0, 1.0, -1.0, -1.0],
            species_groups={"all": ["Na", "Cl"], "anion": "Cl"},
        )
    with pytest.raises(ValueError, match="matched no atoms"):
        compute_charge_current(
            collection,
            charges=[1.0, 1.0, -1.0, -1.0],
            species_groups={"potassium": "K", "rest": ["Na", "Cl"]},
        )
    with pytest.raises(ValueError, match="must not be empty"):
        compute_charge_current(
            collection,
            charges=[1.0, 1.0, -1.0, -1.0],
            species_groups={},
        )


def test_fixed_and_constant_volume_variable_cell_provenance() -> None:
    velocities = np.zeros((5, 2, 3), dtype=np.float64)
    fixed = compute_charge_current(make_collection(velocities), charges=[1.0, -1.0])
    assert fixed.cell_mode == "fixed"
    assert fixed.fixed_volume_a3 == pytest.approx(1000.0)

    cells = np.empty((5, 3, 3), dtype=np.float64)
    for frame, stretch in enumerate(np.linspace(0.8, 1.2, 5)):
        cells[frame] = np.diag([10.0 * stretch, 10.0 / stretch, 10.0])
    variable = compute_charge_current(
        make_collection(velocities, cells=cells),
        charges=[1.0, -1.0],
    )
    assert variable.cell_mode == "variable"
    assert variable.fixed_volume_a3 is None
    np.testing.assert_allclose(variable.cell_volumes_a3, 1000.0)


def test_direct_and_fft_total_and_group_correlations_agree() -> None:
    rng = np.random.default_rng(12)
    velocities = rng.normal(size=(65, 4, 3))
    collection = make_collection(
        velocities,
        atomic_numbers=np.array([11, 11, 17, 17]),
    )
    current = compute_charge_current(
        collection,
        charges=[1.0, 1.0, -1.0, -1.0],
        species_groups={"cation": "Na", "anion": "Cl"},
    )
    direct = compute_current_correlation(
        current,
        max_lag=27,
        lag_stride=2,
        backend="direct",
    )
    fft = compute_current_correlation(
        current,
        max_lag=27,
        lag_stride=2,
        backend="fft",
    )
    np.testing.assert_allclose(fft.tensor, direct.tensor, atol=4e-13)
    np.testing.assert_allclose(fft.scalar, direct.scalar, atol=6e-13)
    np.testing.assert_allclose(fft.group_tensor, direct.group_tensor, atol=4e-13)
    np.testing.assert_allclose(fft.group_scalar, direct.group_scalar, atol=6e-13)
    np.testing.assert_allclose(
        np.sum(direct.group_scalar, axis=(1, 2)), direct.scalar, atol=5e-13
    )
    np.testing.assert_allclose(
        np.sum(direct.group_tensor, axis=(1, 2)), direct.tensor, atol=5e-13
    )
    np.testing.assert_array_equal(direct.n_origins, 65 - direct.lag_steps)


def test_ordered_group_cross_correlations_are_not_symmetrized() -> None:
    a = np.array([1.0, 2.0, 4.0, 8.0, 16.0, 3.0])
    b = np.array([0.5, -2.0, 1.0, 5.0, -1.0, 7.0])
    velocities = np.zeros((a.size, 2, 3), dtype=np.float64)
    velocities[:, 0, 0] = a
    velocities[:, 1, 0] = -b  # q=-1 gives group current +b
    collection = make_collection(velocities)
    current = compute_charge_current(
        collection,
        charges=[1.0, -1.0],
        species_groups={"A": "Na", "B": "Cl"},
    )
    result = compute_current_correlation(current, max_lag=2, backend="direct")
    expected_ab = np.mean(a[:-1] * b[1:])
    expected_ba = np.mean(b[:-1] * a[1:])
    assert result.group_scalar[1, 0, 1] == pytest.approx(expected_ab)
    assert result.group_scalar[1, 1, 0] == pytest.approx(expected_ba)
    assert result.group_scalar[1, 0, 1] != pytest.approx(result.group_scalar[1, 1, 0])


def test_zero_current_and_no_tensor_mode() -> None:
    collection = make_collection(np.zeros((70, 2, 3), dtype=np.float64))
    current = compute_charge_current(
        collection,
        charges=[1.0, -1.0],
        species_groups={"cation": "Na", "anion": "Cl"},
    )
    result = compute_current_correlation(
        current,
        max_lag=10,
        compute_tensor=False,
        backend="fft",
    )
    np.testing.assert_allclose(result.scalar, 0.0)
    np.testing.assert_allclose(result.components, 0.0)
    np.testing.assert_allclose(result.group_scalar, 0.0)
    assert result.tensor is None
    assert result.group_tensor is None


def test_correlation_validation_backend_policy_and_strict_types() -> None:
    collection = make_collection(np.zeros((8, 2, 3), dtype=np.float64))
    current = compute_charge_current(collection, charges=[1.0, -1.0])
    with pytest.raises(TypeError, match="current"):
        compute_current_correlation(object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="backend"):
        compute_current_correlation(current, backend="bad")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="origin_stride"):
        compute_current_correlation(current, backend="fft", origin_stride=2)
    with pytest.raises(TypeError, match="origin_stride"):
        compute_current_correlation(current, origin_stride=True)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="lag_stride"):
        compute_current_correlation(current, lag_stride=False)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="compute_tensor"):
        compute_current_correlation(current, compute_tensor=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="max_lag"):
        compute_current_correlation(current, max_lag=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="largest"):
        compute_current_correlation(current, max_lag=8)


def test_results_are_deeply_immutable_and_publicly_exported() -> None:
    velocities = np.zeros((6, 2, 3), dtype=np.float64)
    current = compute_charge_current(
        make_collection(velocities),
        charges=[1.0, -1.0],
        species_groups={"cation": "Na", "anion": "Cl"},
    )
    correlation = compute_current_correlation(current, max_lag=2)
    assert isinstance(current, ChargeCurrentResult)
    assert isinstance(correlation, CurrentCorrelationResult)
    assert mdstats.compute_charge_current is compute_charge_current
    assert mdstats.compute_current_correlation is compute_current_correlation
    assert "ChargeCurrentResult" in mdstats.__all__
    assert "CurrentCorrelationResult" in mdstats.__all__

    with pytest.raises(ValueError):
        current.total_current[0, 0] = 1.0
    with pytest.raises(ValueError):
        current.group_atom_indices["cation"][0] = 99
    with pytest.raises(TypeError):
        current.group_atom_indices["new"] = np.array([0])  # type: ignore[index]
    with pytest.raises(TypeError):
        correlation.metadata["new"] = 1  # type: ignore[index]
    with pytest.raises(ValueError):
        correlation.group_scalar[0, 0, 0] = 1.0
    assert correlation.signature is current.signature



def test_zero_charge_atoms_are_excluded_from_partition_and_signature() -> None:
    velocities = np.zeros((5, 3, 3), dtype=np.float64)
    collection = make_collection(
        velocities,
        atomic_numbers=np.array([11, 17, 1]),
    )
    result = compute_charge_current(
        collection,
        charges=[1.0, -1.0, 0.0],
        species_groups={"cation": "Na", "anion": "Cl"},
    )
    np.testing.assert_array_equal(result.current_atom_indices, [0, 1])
    np.testing.assert_array_equal(result.signature.atom_indices, [0, 1])
    assert 2 not in result.group_atom_indices["cation"]
    assert 2 not in result.group_atom_indices["anion"]


def test_origin_stride_counts_and_tensor_retention_do_not_change_scalar() -> None:
    rng = np.random.default_rng(44)
    collection = make_collection(rng.normal(size=(15, 2, 3)))
    current = compute_charge_current(collection, charges=[1.0, -1.0])
    tensor = compute_current_correlation(
        current,
        max_lag=7,
        origin_stride=3,
        backend="direct",
        compute_tensor=True,
    )
    scalar_only = compute_current_correlation(
        current,
        max_lag=7,
        origin_stride=3,
        backend="direct",
        compute_tensor=False,
    )
    np.testing.assert_allclose(scalar_only.scalar, tensor.scalar)
    np.testing.assert_allclose(scalar_only.components, tensor.components)
    expected = [len(range(0, 15 - lag, 3)) for lag in tensor.lag_steps]
    np.testing.assert_array_equal(tensor.n_origins, expected)


def test_result_constructor_invariants_fail_closed() -> None:
    velocities = np.zeros((6, 2, 3), dtype=np.float64)
    current = compute_charge_current(
        make_collection(velocities),
        charges=[1.0, -1.0],
        species_groups={"cation": "Na", "anion": "Cl"},
    )
    correlation = compute_current_correlation(current, max_lag=2)
    broken_group = np.array(current.group_currents, copy=True)
    broken_group[:, 0, 0] += 1.0
    with pytest.raises(ValueError, match="sum exactly"):
        replace(current, group_currents=broken_group)
    with pytest.raises(ValueError, match="fixed_volume"):
        replace(current, fixed_volume_a3=999.0)

    broken_scalar = np.array(correlation.scalar, copy=True)
    broken_scalar[0] += 1.0
    with pytest.raises(ValueError, match="sum of Cartesian"):
        replace(correlation, scalar=broken_scalar)
    broken_group_scalar = np.array(correlation.group_scalar, copy=True)
    broken_group_scalar[:, 0, 1] += 1.0
    with pytest.raises(ValueError, match="group-tensor traces"):
        replace(correlation, group_scalar=broken_group_scalar)
