from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from mdstats.analysis._dynamics_common import (
    DynamicsInputSignature,
    resolve_analysis_subspace,
    trajectory_fingerprint,
)
from mdstats.analysis.diffusion import (
    DiffusionEstimate,
    compare_msd_vacf_diffusion,
    estimate_diffusion_plateau,
)
from mdstats.analysis.msd import MSDResult, compute_msd
from mdstats.analysis.vacf import VACFResult, compute_vacf
from mdstats.analysis.vacf_transport import (
    VACFDiffusionResult,
    integrate_vacf_to_diffusion,
)
from mdstats.analysis.velocity_spectrum import compute_vacf_spectrum, compute_vdos
from mdstats.collection import AtomisticFrameCollection
from mdstats.provenance import FrameCollectionProvenance
from mdstats.semantics import FrameSemantics


def make_signature(
    times: np.ndarray,
    *,
    atom_indices: tuple[int, ...] = (0, 1),
    drift_mode: str | None = None,
    drift_atom_indices: tuple[int, ...] | None = None,
    source_files: tuple[str, ...] = ("synthetic",),
    fingerprint: str = "trajectory-A",
    coordinate_mode: str = "laboratory",
    subspace=None,
) -> DynamicsInputSignature:
    times = np.asarray(times, dtype=np.float64)
    resolved = resolve_analysis_subspace() if subspace is None else subspace
    return DynamicsInputSignature(
        source_format="synthetic",
        source_files=source_files,
        trajectory_fingerprint=fingerprint,
        frame_indices=tuple(range(times.size)),
        frame_times_ps=times,
        n_frames=times.size,
        sample_spacing_ps=float(times[1] - times[0]),
        atom_indices=np.asarray(atom_indices, dtype=np.int64),
        coordinate_mode=coordinate_mode,
        reference_cell_mode=None,
        reference_cell=None,
        drift_mode=drift_mode,
        drift_atom_indices=(
            None
            if drift_mode is None
            else np.asarray(
                atom_indices if drift_atom_indices is None else drift_atom_indices,
                dtype=np.int64,
            )
        ),
        velocity_source="native",
        projection_basis=resolved.projection_basis,
        projection_labels=resolved.labels,
    )


def make_vacf(
    tensor_per_particle: np.ndarray,
    times: np.ndarray,
    *,
    signature: DynamicsInputSignature | None = None,
    retain_tensor: bool = True,
) -> VACFResult:
    tensor_per_particle = np.asarray(tensor_per_particle, dtype=np.float64)
    times = np.asarray(times, dtype=np.float64)
    components = np.diagonal(tensor_per_particle, axis1=1, axis2=2)
    return VACFResult(
        lag_steps=np.arange(times.size, dtype=np.int64),
        lag_times=times,
        scalar_sum=np.sum(components, axis=1),
        components_sum=components,
        tensor_sum=tensor_per_particle if retain_tensor else None,
        per_atom_scalar=None,
        per_atom_components=None,
        per_atom_indices=None,
        n_origins=np.arange(times.size, 0, -1, dtype=np.int64),
        atom_indices=np.array([0, 1], dtype=np.int64),
        atom_weights=np.ones(2, dtype=np.float64),
        weight_sum=2.0,
        weighting="uniform",
        drift_mode=None,
        backend="direct",
        metadata={"nested": {"values": [1, 2]}, "array": np.array([3.0])},
        signature=signature,
    )


def test_resolve_analysis_subspace_contract() -> None:
    xy = resolve_analysis_subspace(axes=("x", "y"))
    assert xy.rank == 2
    assert xy.labels == ("x", "y")
    np.testing.assert_array_equal(xy.projection_basis, np.eye(3)[:2])

    rotated = resolve_analysis_subspace(
        projection_basis=np.array([[1.0, 1.0, 0.0]]) / np.sqrt(2.0)
    )
    assert rotated.rank == 1
    assert rotated.labels is None

    with pytest.raises(ValueError, match="at most one"):
        resolve_analysis_subspace(
            axes=("x",), projection_basis=np.array([[1.0, 0.0, 0.0]])
        )
    with pytest.raises(ValueError, match="duplicates"):
        resolve_analysis_subspace(axes=("x", "x"))
    with pytest.raises(ValueError, match="orthonormal"):
        resolve_analysis_subspace(projection_basis=[[1.0, 1.0, 0.0]])


def test_green_kubo_uses_selected_subspace_before_dimensional_division() -> None:
    times = np.linspace(0.0, 1.0, 5)
    tensor = np.zeros((times.size, 3, 3), dtype=np.float64)
    tensor[:, 0, 0] = 2.0
    tensor[:, 1, 1] = 4.0
    tensor[:, 2, 2] = 20.0
    vacf = make_vacf(tensor * 2.0, times)

    xy = integrate_vacf_to_diffusion(vacf, axes=("x", "y"))
    np.testing.assert_allclose(xy.integrand, 3.0)
    np.testing.assert_allclose(xy.running_diffusion_a2_per_ps, 3.0 * times)
    assert xy.dimensions == 2
    assert xy.projection_labels == ("x", "y")

    with pytest.raises(ValueError, match="cannot reinterpret"):
        integrate_vacf_to_diffusion(vacf, dimensions=2)


def test_rotated_projection_uses_full_tensor_and_rejects_missing_tensor() -> None:
    times = np.linspace(0.0, 1.0, 5)
    tensor = np.zeros((times.size, 3, 3), dtype=np.float64)
    tensor[:, 0, 0] = 2.0
    tensor[:, 1, 1] = 4.0
    tensor[:, 0, 1] = tensor[:, 1, 0] = 1.0
    basis = np.array([[1.0, 1.0, 0.0]]) / np.sqrt(2.0)
    vacf = make_vacf(tensor * 2.0, times)

    rotated = integrate_vacf_to_diffusion(vacf, projection_basis=basis)
    np.testing.assert_allclose(rotated.integrand, 4.0)
    assert rotated.dimensions == 1
    assert rotated.projection_labels is None

    without_tensor = make_vacf(tensor * 2.0, times, retain_tensor=False)
    with pytest.raises(ValueError, match="requires the full VACF tensor"):
        integrate_vacf_to_diffusion(without_tensor, projection_basis=basis)


def test_signature_detects_drift_reference_and_frame_slice_mismatches() -> None:
    times = np.linspace(0.0, 1.0, 6)
    left = make_signature(
        times,
        drift_mode="center_of_mass",
        drift_atom_indices=(0,),
    )
    different_drift = make_signature(
        times,
        drift_mode="center_of_mass",
        drift_atom_indices=(1,),
    )
    assert left.mismatch_fields(different_drift) == ("drift_atom_indices",)

    shifted = make_signature(
        times + 0.1,
        drift_mode="center_of_mass",
        drift_atom_indices=(0,),
        fingerprint="trajectory-B",
    )
    mismatches = left.mismatch_fields(shifted)
    assert "trajectory_fingerprint" in mismatches
    assert "frame_times_ps" in mismatches


def test_comparison_projects_msd_tensor_and_fails_closed_on_unsigned_results() -> None:
    times = np.linspace(0.0, 5.0, 31)
    diffusion = 0.25
    components = np.repeat((2.0 * diffusion * times)[:, None], 3, axis=1)
    tensor = np.zeros((times.size, 3, 3), dtype=np.float64)
    diagonal = np.arange(3)
    tensor[:, diagonal, diagonal] = components
    base = make_signature(times)
    msd = MSDResult(
        lag_steps=np.arange(times.size, dtype=np.int64),
        lag_times=times,
        msd=np.sum(components, axis=1),
        components=components,
        tensor=tensor,
        per_atom_msd=None,
        n_origins=np.arange(times.size, 0, -1, dtype=np.int64),
        atom_indices=np.array([0, 1], dtype=np.int64),
        n_atoms=2,
        mode="time_averaged",
        coordinate_mode="laboratory",
        drift_mode=None,
        reference_cell=None,
        signature=base,
    )
    rotated = resolve_analysis_subspace(
        projection_basis=np.array([[1.0, 1.0, 0.0]]) / np.sqrt(2.0)
    )
    estimate = DiffusionEstimate(
        value_a2_per_ps=diffusion,
        standard_error_a2_per_ps=None,
        time_range_ps=(1.0, 4.0),
        method="explicit",
        component="scalar",
        dimensions=1,
        n_points=10,
        is_stable=True,
        projection_basis=rotated.projection_basis,
        projection_labels=rotated.labels,
        signature=base.with_subspace(rotated),
    )
    compared = compare_msd_vacf_diffusion(
        msd,
        estimate,
        msd_fit_range_ps=(1.0, 4.0),
    )
    assert compared.msd_diffusion_a2_per_ps == pytest.approx(diffusion)
    assert compared.dimensions == 1

    unsigned = MSDResult(
        lag_steps=msd.lag_steps,
        lag_times=msd.lag_times,
        msd=msd.msd,
        components=msd.components,
        tensor=msd.tensor,
        per_atom_msd=None,
        n_origins=msd.n_origins,
        atom_indices=msd.atom_indices,
        n_atoms=2,
        mode="time_averaged",
        coordinate_mode="laboratory",
        drift_mode=None,
        reference_cell=None,
    )
    with pytest.raises(ValueError, match="legacy unsigned"):
        compare_msd_vacf_diffusion(
            unsigned,
            estimate,
            msd_fit_range_ps=(1.0, 4.0),
        )


def test_recursive_result_immutability_and_signature_propagation() -> None:
    times = np.linspace(0.0, 1.0, 9)
    tensor = np.zeros((times.size, 3, 3), dtype=np.float64)
    tensor[0] = 2.0 * np.eye(3)
    signature = make_signature(times)
    vacf = make_vacf(tensor, times, signature=signature)

    with pytest.raises(ValueError):
        vacf.scalar_sum[0] = 99.0
    with pytest.raises(TypeError):
        vacf.metadata["new"] = 1
    with pytest.raises(TypeError):
        vacf.metadata["nested"]["new"] = 1
    with pytest.raises(TypeError):
        vacf.metadata["nested"]["values"][0] = 9
    with pytest.raises(ValueError):
        vacf.metadata["array"][0] = 9.0

    spectrum = compute_vacf_spectrum(vacf)
    vdos = compute_vdos(spectrum, normalization="unit_area")
    assert spectrum.signature is signature
    assert vdos.signature is signature
    with pytest.raises(ValueError):
        spectrum.scalar_spectrum[0] = 0.0
    with pytest.raises(TypeError):
        vdos.metadata["new"] = 1


def test_plateau_rejects_irregular_selected_grid() -> None:
    times = np.array([0.0, 0.1, 0.2, 0.5, 0.9, 1.4], dtype=np.float64)
    integrand = np.ones(times.size, dtype=np.float64)
    running = VACFDiffusionResult(
        lag_times=times,
        running_diffusion_a2_per_ps=np.array([0.0, 0.1, 0.2, 0.5, 0.9, 1.4]),
        integrand=integrand,
        dimensions=3,
        component="scalar",
        weighting="uniform",
        integration="trapezoid",
    )
    with pytest.raises(ValueError, match="uniformly spaced"):
        estimate_diffusion_plateau(
            running,
            time_range_ps=(0.0, 1.4),
            minimum_points=4,
        )


def make_collection() -> AtomisticFrameCollection:
    n_frames = 8
    times = np.linspace(0.0, 0.7, n_frames)
    velocities = np.zeros((n_frames, 2, 3), dtype=np.float64)
    velocities[:, 0, 0] = 1.0
    velocities[:, 1, 1] = 2.0
    positions = np.zeros_like(velocities)
    positions[:, 0, 0] = times
    positions[:, 1, 1] = 2.0 * times
    cells = np.repeat((10.0 * np.eye(3))[None, :, :], n_frames, axis=0)
    fractional = positions / 10.0
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.array([3, 11], dtype=np.int32),
        masses=np.array([6.94, 22.99], dtype=np.float64),
        pbc=np.array([True, True, True]),
        steps=np.arange(n_frames, dtype=np.int64),
        times=times,
        cells=cells,
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=fractional,
        velocities=velocities,
        provenance=FrameCollectionProvenance(
            source_format="ase-structure-collection",
            source_files=("synthetic.xyz",),
            velocity_source="native",
            coordinate_normalization="native_unwrapped_cartesian",
            stress_source=None,
            units_source="synthetic",
        ),
    )






def test_result_constructors_reject_inconsistent_signatures() -> None:
    times = np.linspace(0.0, 1.0, 5)
    tensor = np.repeat(np.eye(3)[None, :, :], times.size, axis=0)
    wrong_atoms = make_signature(times, atom_indices=(0,))
    with pytest.raises(ValueError, match="signature atom_indices"):
        make_vacf(tensor, times, signature=wrong_atoms)

    wrong_coordinates = make_signature(times, coordinate_mode="reference_cell")
    components = np.repeat(times[:, None], 3, axis=1)
    msd_tensor = np.zeros((times.size, 3, 3), dtype=np.float64)
    diagonal = np.arange(3)
    msd_tensor[:, diagonal, diagonal] = components
    with pytest.raises(ValueError, match="coordinate_mode"):
        MSDResult(
            lag_steps=np.arange(times.size, dtype=np.int64),
            lag_times=times,
            msd=np.sum(components, axis=1),
            components=components,
            tensor=msd_tensor,
            per_atom_msd=None,
            n_origins=np.arange(times.size, 0, -1, dtype=np.int64),
            atom_indices=np.array([0, 1], dtype=np.int64),
            n_atoms=2,
            mode="time_averaged",
            coordinate_mode="laboratory",
            drift_mode=None,
            reference_cell=None,
            signature=wrong_coordinates,
        )


def test_trajectory_fingerprint_includes_origins_masses_and_is_byteorder_stable() -> None:
    collection = make_collection()
    baseline = trajectory_fingerprint(collection)

    shifted_origins = replace(
        collection,
        origins=np.array(collection.origins, copy=True),
    )
    shifted_origins.origins[0, 0] = 0.25
    assert trajectory_fingerprint(shifted_origins) != baseline

    changed_masses = replace(
        collection,
        masses=np.array(collection.masses, copy=True),
    )
    changed_masses.masses[0] += 0.01
    assert trajectory_fingerprint(changed_masses) != baseline

    # Identical normalized values with explicit big-endian storage hash the same.
    endian_copy = replace(
        collection,
        times=np.asarray(collection.times, dtype=">f8"),
        cells=np.asarray(collection.cells, dtype=">f8"),
        origins=np.asarray(collection.origins, dtype=">f8"),
        fractional_positions=np.asarray(collection.fractional_positions, dtype=">f8"),
        velocities=np.asarray(collection.velocities, dtype=">f8"),
    )
    assert trajectory_fingerprint(endian_copy) == baseline


def test_compute_paths_attach_complete_signatures_and_reject_bool_integers() -> None:
    collection = make_collection()
    vacf = compute_vacf(collection, max_lag=4, backend="direct")
    msd = compute_msd(collection, max_lag=4, backend="direct")
    assert vacf.signature is not None
    assert msd.signature is not None
    assert vacf.signature.is_compatible_with(msd.signature)

    with pytest.raises(TypeError, match="origin_stride"):
        compute_vacf(collection, origin_stride=True)
    with pytest.raises(TypeError, match="lag_stride"):
        compute_msd(collection, lag_stride=True)
    with pytest.raises(TypeError, match="compute_tensor"):
        compute_vacf(collection, compute_tensor=1)
    with pytest.raises(TypeError, match="per_atom"):
        compute_msd(collection, per_atom=1)


def test_h0_public_exports_are_listed_at_both_api_layers() -> None:
    import mdstats
    import mdstats.analysis as analysis

    for name in (
        "AnalysisSubspace",
        "DynamicsInputSignature",
        "resolve_analysis_subspace",
    ):
        assert hasattr(mdstats, name)
        assert name in mdstats.__all__
        assert name in analysis.__all__
