from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import mdstats
from mdstats import AtomisticFrameCollection, FrameCollectionProvenance
from mdstats.analysis.density import (
    FrameworkRegistrationGaugeValidation,
    NaLta300KDensityAttractorPilotOptions,
    PilotAuditInputError,
    PilotEvidenceStatus,
    PilotOverallStatus,
    SpeciesDensityOptions,
    prepare_na_lta_300k_density_attractor_pilot,
)


def _collection() -> AtomisticFrameCollection:
    numbers = np.array([14] * 24 + [13] * 24 + [8] * 96 + [11] * 24, dtype=np.int32)
    masses = np.array([28.085] * 24 + [26.981] * 24 + [16.0] * 96 + [22.99] * 24)
    n_frames = 6
    rng = np.random.default_rng(20260726)
    base = rng.random((numbers.size, 3)) * 0.8 + 0.1
    fractional = np.repeat(base[None, :, :], n_frames, axis=0)
    drift = np.arange(n_frames, dtype=np.float64)[:, None, None] * np.array([0.002, -0.001, 0.0015])
    fractional += drift
    # Small O-only motion makes CoG/CoM a genuine, but safely small, sensitivity test.
    fractional[:, 48:144, 0] += np.arange(n_frames)[:, None] * 2.0e-5
    cells = np.repeat(np.diag([17.0, 17.0, 17.0])[None, :, :], n_frames, axis=0)
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


def _options(**changes: object) -> NaLta300KDensityAttractorPilotOptions:
    values: dict[str, object] = {
        "representative_frame_count": 3,
        "grid_shape": (8, 8, 8),
        "kernel_sigma_angstrom": 0.8,
        "density_query_batch_size": 64,
        "density_sample_batch_size": 64,
        "relative_image_tolerance": 1.0e-8,
        "maximum_image_radius": 2,
    }
    values.update(changes)
    return NaLta300KDensityAttractorPilotOptions(**values)


def test_s1_pilot_binds_gauge_density_attractors_and_fail_closed_dossier(tmp_path: Path):
    result = prepare_na_lta_300k_density_attractor_pilot(
        _collection(), _raw_file(tmp_path), options=_options()
    )

    assert result.gauge_validation.accepted
    assert result.gauge_validation.framework_atom_count == 144
    assert result.gauge_validation.selected_weighting == "center_of_geometry"
    assert result.gauge_validation.comparison_weighting == "center_of_mass"
    assert result.gauge_validation.solver_method_counts == {"certified_local_convexity": 6}
    assert result.gauge_validation.minimum_uniqueness_margin_angstrom > 0.0
    assert len(result.representative_frame_indices) == 3
    assert np.count_nonzero(result.pilot_samples.temporal_weighting.temporal_mask) == 3
    assert np.count_nonzero(result.pilot_samples.represented_time_weights) == 3 * 24
    assert result.density.catalog_signature == result.pilot_samples.signature
    assert result.attractors.density_estimate_signature == result.density.signature
    assert result.density.integrals.mean_occupancy_integral == pytest.approx(24.0)
    assert result.density.integrals.probability_integral == pytest.approx(1.0)

    assert result.report.overall_status is PilotOverallStatus.BLOCKED_MISSING_REQUIRED_EVIDENCE
    assert result.report.missing_required_evidence == (
        "structural_mapping",
        "reference_cell_sensitivity",
        "temporal_support",
        "force_density_agreement",
        "transition_paths",
    )
    evidence = {item.evidence_id: item for item in result.report.evidence}
    assert evidence["registration"].status is PilotEvidenceStatus.RESOLVED
    assert evidence["kernel_metric_periodization"].status is PilotEvidenceStatus.RESOLVED
    assert evidence["field_certificate"].status is PilotEvidenceStatus.PARTIAL
    assert evidence["topology_certificate"].status is PilotEvidenceStatus.PARTIAL
    assert evidence["attractor_lineage"].unresolved_fraction == pytest.approx(1.0)
    assert result.report.metadata["s1_complete"] is True


def test_s1_options_and_gauge_validation_round_trip(tmp_path: Path):
    options = _options()
    assert NaLta300KDensityAttractorPilotOptions.from_dict(options.to_dict()) == options
    result = prepare_na_lta_300k_density_attractor_pilot(
        _collection(), _raw_file(tmp_path), options=options
    )
    restored = FrameworkRegistrationGaugeValidation.from_dict(
        result.gauge_validation.to_dict()
    )
    assert restored == result.gauge_validation
    assert restored.signature == result.gauge_validation.signature


def test_s1_rejects_registration_continuity_outside_declared_limit(tmp_path: Path):
    with pytest.raises(PilotAuditInputError, match="gauge failed"):
        prepare_na_lta_300k_density_attractor_pilot(
            _collection(),
            _raw_file(tmp_path),
            options=_options(maximum_translation_step_angstrom=1.0e-8),
        )


def test_s1_accepts_explicit_density_options_and_public_exports(tmp_path: Path):
    result = prepare_na_lta_300k_density_attractor_pilot(
        _collection(),
        _raw_file(tmp_path),
        options=_options(),
        density_options=SpeciesDensityOptions(
            grid_shape=(8, 8, 8),
            relative_image_tolerance=1.0e-8,
            max_image_radius=2,
            query_batch_size=64,
            sample_batch_size=64,
        ),
    )
    assert result.density.realization.grid_shape == (8, 8, 8)
    assert mdstats.PILOT_DENSITY_ATTRACTOR_STAGE == "11E8a-S1"
    assert mdstats.prepare_na_lta_300k_density_attractor_pilot is prepare_na_lta_300k_density_attractor_pilot
    assert "NaLta300KDensityAttractorPilot" in mdstats.__all__
