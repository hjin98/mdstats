from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import mdstats
from mdstats import AtomisticFrameCollection, FrameCollectionProvenance
from mdstats.analysis.density import (
    NaLta300KDensityAttractorPilotOptions,
    NaLta300KRefinementLineageOptions,
    PilotEvidenceStatus,
    PilotOverallStatus,
    ReferenceCellSensitivityCertificate,
    SpeciesDensityResourcePolicy,
    prepare_na_lta_300k_refinement_lineage_pilot,
)


def _collection(*, final_cell_scale: float = 1.0) -> AtomisticFrameCollection:
    numbers = np.array([14] * 24 + [13] * 24 + [8] * 96 + [11] * 24, dtype=np.int32)
    masses = np.array([28.085] * 24 + [26.981] * 24 + [16.0] * 96 + [22.99] * 24)
    n_frames = 6
    rng = np.random.default_rng(20260726)
    base = rng.random((numbers.size, 3)) * 0.8 + 0.1
    fractional = np.repeat(base[None, :, :], n_frames, axis=0)
    drift = np.arange(n_frames, dtype=np.float64)[:, None, None] * np.array([0.002, -0.001, 0.0015])
    fractional += drift
    fractional[:, 48:144, 0] += np.arange(n_frames)[:, None] * 2.0e-5
    cells = np.repeat(np.diag([17.0, 17.0, 17.0])[None, :, :], n_frames, axis=0)
    cells[-1] *= final_cell_scale
    return AtomisticFrameCollection(
        frame_semantics="trajectory",
        frame_ids=np.arange(n_frames),
        atomic_numbers=numbers,
        masses=masses,
        pbc=np.array([True, True, True]),
        steps=np.arange(n_frames),
        times=np.arange(n_frames, dtype=np.float64) * 0.001,
        cells=cells,
        origins=np.zeros((n_frames, 3)),
        fractional_positions=fractional,
        velocities=np.zeros((n_frames, numbers.size, 3)),
        forces=rng.normal(size=(n_frames, numbers.size, 3)),
        temperatures=np.full(n_frames, 300.0),
        provenance=FrameCollectionProvenance(
            source_format="vasp-vasprun-xml",
            source_files=("vasprun.xml",),
            velocity_source="finite_difference",
            coordinate_normalization="minimum_image_inferred",
            stress_source="ASE vasprun.xml stress",
            units_source="VASP native units",
        ),
    )


def _raw_file(tmp_path: Path) -> Path:
    path = tmp_path / "vasprun.xml"
    path.write_bytes(b"synthetic Na-LTA vasprun source\n")
    return path


def _s1_options() -> NaLta300KDensityAttractorPilotOptions:
    return NaLta300KDensityAttractorPilotOptions(
        representative_frame_count=3,
        grid_shape=(6, 6, 6),
        kernel_sigma_angstrom=0.8,
        density_query_batch_size=64,
        density_sample_batch_size=64,
        relative_image_tolerance=1.0e-8,
        maximum_image_radius=2,
    )


def _s2_options(**changes: object) -> NaLta300KRefinementLineageOptions:
    values: dict[str, object] = {
        "bandwidth_sigmas_angstrom": (0.7, 0.8, 0.9),
        "central_bandwidth_sigma_angstrom": 0.8,
        "lineage_grid_shape": (6, 6, 6),
        "refinement_grid_shapes": ((6, 6, 6), (8, 8, 8)),
        "comparison_reference_frame_index": 5,
        "minimum_lineage_overlap": 0.0,
        "minimum_refinement_basin_overlap": 0.0,
        "density_query_batch_size": 64,
        "density_sample_batch_size": 64,
        "relative_image_tolerance": 1.0e-8,
        "maximum_image_radius": 2,
    }
    values.update(changes)
    return NaLta300KRefinementLineageOptions(**values)


def test_s2_options_reference_certificate_and_public_exports_round_trip(tmp_path: Path):
    options = _s2_options()
    assert NaLta300KRefinementLineageOptions.from_dict(options.to_dict()) == options

    result = prepare_na_lta_300k_refinement_lineage_pilot(
        _collection(),
        _raw_file(tmp_path),
        options=options,
        s1_options=_s1_options(),
        density_resources=SpeciesDensityResourcePolicy(max_image_terms=50_000_000),
    )
    certificate = ReferenceCellSensitivityCertificate.from_dict(
        result.reference_cell_sensitivity.to_dict()
    )
    assert certificate == result.reference_cell_sensitivity
    assert mdstats.PILOT_REFINEMENT_LINEAGE_STAGE == "11E8a-S2"
    assert mdstats.prepare_na_lta_300k_refinement_lineage_pilot is prepare_na_lta_300k_refinement_lineage_pilot
    assert "NaLta300KRefinementLineagePilot" in mdstats.__all__


def test_s2_binds_ladder_lineage_refinement_and_fixed_cell_reference(tmp_path: Path):
    result = prepare_na_lta_300k_refinement_lineage_pilot(
        _collection(),
        _raw_file(tmp_path),
        options=_s2_options(),
        s1_options=_s1_options(),
        density_resources=SpeciesDensityResourcePolicy(max_image_terms=50_000_000),
    )

    assert len(result.density_ladder.estimates) == 3
    assert result.density_ladder.catalog_signature == result.s1_pilot.pilot_samples.signature
    assert result.lineage.ladder_signature == result.density_ladder.signature
    assert result.lineage.catalog_signatures == tuple(c.signature for c in result.lineage_catalogs)
    assert result.grid_refinement.grid_shapes == ((6, 6, 6), (8, 8, 8))
    assert result.reference_cell_sensitivity.exact_identity_shortcut
    assert result.reference_cell_sensitivity.accepted
    assert result.reference_cell_sensitivity.fractional_probability_l1 == pytest.approx(0.0)
    assert result.report.overall_status is PilotOverallStatus.BLOCKED_MISSING_REQUIRED_EVIDENCE
    assert result.report.missing_required_evidence == (
        "structural_mapping",
        "temporal_support",
        "force_density_agreement",
        "transition_paths",
    )
    evidence = {item.evidence_id: item for item in result.report.evidence}
    assert evidence["reference_cell_sensitivity"].status is PilotEvidenceStatus.RESOLVED
    assert evidence["field_certificate"].status is PilotEvidenceStatus.RESOLVED
    assert result.report.metadata["s2_complete"] is True


def test_s2_nonidentical_reference_cell_is_evaluated_and_fail_closed(tmp_path: Path):
    # The perturbation is small enough for the S1 fixed-cell registration tolerance,
    # but larger than this deliberately strict S2 sensitivity limit.
    result = prepare_na_lta_300k_refinement_lineage_pilot(
        _collection(final_cell_scale=1.0 + 5.0e-12),
        _raw_file(tmp_path),
        options=_s2_options(maximum_reference_cell_relative_difference=1.0e-13),
        s1_options=_s1_options(),
        density_resources=SpeciesDensityResourcePolicy(max_image_terms=50_000_000),
    )
    certificate = result.reference_cell_sensitivity
    assert not certificate.exact_identity_shortcut
    assert certificate.relative_cell_frobenius_difference > certificate.cell_difference_limit
    assert not certificate.accepted
    evidence = {item.evidence_id: item for item in result.report.evidence}
    assert evidence["reference_cell_sensitivity"].status is PilotEvidenceStatus.BLOCKED
    assert "reference_cell_sensitivity" not in result.report.missing_required_evidence
    assert result.report.overall_status is PilotOverallStatus.BLOCKED_MISSING_REQUIRED_EVIDENCE


def test_s2_reuses_matching_s1_central_grid_realization(tmp_path: Path):
    s1_options = NaLta300KDensityAttractorPilotOptions(
        representative_frame_count=3,
        grid_shape=(8, 8, 8),
        kernel_sigma_angstrom=0.8,
        density_query_batch_size=64,
        density_sample_batch_size=64,
        relative_image_tolerance=1.0e-8,
        maximum_image_radius=2,
    )
    result = prepare_na_lta_300k_refinement_lineage_pilot(
        _collection(),
        _raw_file(tmp_path),
        options=_s2_options(),
        s1_options=s1_options,
        density_resources=SpeciesDensityResourcePolicy(max_image_terms=50_000_000),
    )
    assert result.grid_refinement_catalogs[-1].signature == result.s1_pilot.attractors.signature
    cost = next(item for item in result.report.evidence if item.evidence_id == "cost")
    assert cost.metrics["field_realization_count"] == 4
