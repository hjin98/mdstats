from __future__ import annotations

from pathlib import Path

import numpy as np
from ase.io import read

import mdstats
from mdstats import AtomisticFrameCollection, FrameCollectionProvenance
from mdstats.analysis.density import (
    ForceDensityAgreementCertificate,
    ForceDensityAgreementStatus,
    NaLta300KDensityAttractorPilotOptions,
    NaLta300KForcePathOptions,
    NaLta300KRefinementLineageOptions,
    PilotOverallStatus,
    SpeciesDensityResourcePolicy,
    TransitionPathPreparationCertificate,
    TransitionPathPreparationStatus,
    prepare_na_lta_300k_force_path_pilot,
)


def _collection() -> AtomisticFrameCollection:
    atoms = read(Path(__file__).parent / "data" / "Na_LTA_relaxed.POSCAR")
    numbers = np.asarray(atoms.numbers, dtype=np.int32)
    masses = np.asarray(atoms.get_masses(), dtype=np.float64)
    cell = np.asarray(atoms.cell.array, dtype=np.float64)
    base_frac = np.asarray(atoms.get_scaled_positions(wrap=True), dtype=np.float64)
    n_frames = 10
    frac = np.repeat(base_frac[None, :, :], n_frames, axis=0)
    phase = np.arange(n_frames, dtype=float)[:, None]
    frac[:, :144, 0] += 2.0e-5 * np.sin(phase)
    frac[:, 144:, 1] += 5.0e-4 * np.sin(phase + np.arange(24)[None, :])
    rng = np.random.default_rng(20260726)
    return AtomisticFrameCollection(
        frame_semantics="trajectory",
        frame_ids=np.arange(n_frames),
        atomic_numbers=numbers,
        masses=masses,
        pbc=np.array([True, True, True]),
        steps=np.arange(n_frames),
        times=np.arange(n_frames, dtype=float) * 0.001,
        cells=np.repeat(cell[None, :, :], n_frames, axis=0),
        origins=np.zeros((n_frames, 3)),
        fractional_positions=frac,
        velocities=np.zeros((n_frames, numbers.size, 3)),
        forces=rng.normal(scale=0.1, size=(n_frames, numbers.size, 3)),
        temperatures=np.full(n_frames, 300.0),
        provenance=FrameCollectionProvenance(
            source_format="vasp-vasprun-xml",
            source_files=("vasprun.xml",),
            velocity_source="source",
            coordinate_normalization="wrapped_fractional",
            stress_source="unavailable",
            units_source="VASP native units",
        ),
    )


def _raw_file(tmp_path: Path) -> Path:
    path = tmp_path / "vasprun.xml"
    path.write_bytes(b"synthetic Na-LTA S4 source\n")
    return path


def _s1_options() -> NaLta300KDensityAttractorPilotOptions:
    return NaLta300KDensityAttractorPilotOptions(
        representative_frame_count=5,
        grid_shape=(8, 8, 8),
        kernel_sigma_angstrom=0.8,
        density_query_batch_size=64,
        density_sample_batch_size=64,
        relative_image_tolerance=1.0e-8,
        maximum_image_radius=2,
    )


def _s2_options() -> NaLta300KRefinementLineageOptions:
    return NaLta300KRefinementLineageOptions(
        bandwidth_sigmas_angstrom=(0.7, 0.8, 0.9),
        central_bandwidth_sigma_angstrom=0.8,
        lineage_grid_shape=(6, 6, 6),
        refinement_grid_shapes=((6, 6, 6), (8, 8, 8)),
        minimum_lineage_overlap=0.0,
        minimum_refinement_basin_overlap=0.0,
        density_query_batch_size=64,
        density_sample_batch_size=64,
        relative_image_tolerance=1.0e-8,
        maximum_image_radius=2,
    )


def test_s4_options_and_public_exports_round_trip():
    options = NaLta300KForcePathOptions(maximum_median_relative_residual=1.5)
    assert NaLta300KForcePathOptions.from_dict(options.to_dict()) == options
    assert mdstats.PILOT_FORCE_PATH_STAGE == "11E8a-S4"
    assert mdstats.prepare_na_lta_300k_force_path_pilot is prepare_na_lta_300k_force_path_pilot


def test_s4_fails_closed_on_pmf_provenance_and_unresolved_spatial_hypothesis(tmp_path: Path):
    result = prepare_na_lta_300k_force_path_pilot(
        _collection(),
        _raw_file(tmp_path),
        s2_options=_s2_options(),
        s1_options=_s1_options(),
        density_resources=SpeciesDensityResourcePolicy(max_image_terms=50_000_000),
    )
    agreement = result.force_density_agreement
    readiness = result.transition_path_preparation
    assert agreement.status is ForceDensityAgreementStatus.PMF_PROVENANCE_REJECTED
    assert agreement.joint_force_sample_count > 0
    assert agreement.pmf_force_sample_count == 0
    assert set(agreement.refinement_status_counts) == {"pmf_provenance_rejected"}
    assert ForceDensityAgreementCertificate.from_dict(agreement.to_dict()).signature == agreement.signature
    assert readiness.status is TransitionPathPreparationStatus.SPATIAL_HYPOTHESIS_UNRESOLVED
    assert readiness.provisional_passage_count == len(result.s3_pilot.temporal_assignment.passages)
    assert result.final_segmentation is None and result.transition_paths is None
    assert TransitionPathPreparationCertificate.from_dict(readiness.to_dict()).signature == readiness.signature
    assert result.report.overall_status is PilotOverallStatus.SCIENTIFICALLY_PARTIAL
    assert result.report.missing_required_evidence == ()
    assert result.report.blockers == ("force_density_agreement", "transition_paths")
    assert result.report.metadata["s4_complete"] is True
