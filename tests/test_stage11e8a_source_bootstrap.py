from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

import mdstats
from mdstats import AtomisticFrameCollection, FrameCollectionProvenance
from mdstats.analysis.density import (
    PilotAuditInputError,
    PilotEvidenceStatus,
    PilotOverallStatus,
    prepare_na_lta_300k_source_bootstrap,
)


def _collection(*, forces: bool = True, remove_one_na: bool = False) -> AtomisticFrameCollection:
    numbers = np.array([14] * 24 + [13] * 24 + [8] * 96 + [11] * 24, dtype=np.int32)
    if remove_one_na:
        numbers[-1] = 8
    n_frames = 4
    rng = np.random.default_rng(20260725)
    base = rng.random((numbers.size, 3))
    fractional = np.repeat(base[None, :, :], n_frames, axis=0)
    drift = np.arange(n_frames, dtype=np.float64)[:, None, None] * np.array([0.002, -0.001, 0.0015])
    fractional = fractional + drift
    cells = np.repeat(np.diag([17.0, 17.0, 17.0])[None, :, :], n_frames, axis=0)
    force_values = None if not forces else rng.normal(size=(n_frames, numbers.size, 3))
    return AtomisticFrameCollection(
        frame_semantics="trajectory",
        frame_ids=np.arange(n_frames),
        atomic_numbers=numbers,
        masses=np.ones(numbers.size),
        pbc=np.array([True, True, True]),
        steps=np.arange(n_frames),
        times=np.arange(n_frames, dtype=np.float64) * 0.001,
        cells=cells,
        origins=np.zeros((n_frames, 3)),
        fractional_positions=fractional,
        velocities=np.zeros((n_frames, numbers.size, 3)),
        forces=force_values,
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


def _raw_file(tmp_path: Path, payload: bytes = b"synthetic vasprun source\n") -> Path:
    path = tmp_path / "vasprun.xml"
    path.write_bytes(payload)
    return path


def test_source_bootstrap_binds_raw_bytes_registration_and_na_samples(tmp_path: Path):
    path = _raw_file(tmp_path)
    result = prepare_na_lta_300k_source_bootstrap(_collection(), path)

    assert result.trajectory_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result.report.dataset.trajectory_digest == result.trajectory_sha256
    assert result.report.dataset.registration_signature == result.registration.signature
    assert result.na_samples.registration_signature == result.registration.signature
    assert result.na_samples.n_samples == 4 * 24
    assert result.report.overall_status is PilotOverallStatus.BLOCKED_MISSING_REQUIRED_EVIDENCE
    assert "kernel_metric_periodization" in result.report.missing_required_evidence

    evidence = {item.evidence_id: item for item in result.report.evidence}
    assert evidence["registration"].status is PilotEvidenceStatus.RESOLVED
    assert evidence["registration"].metrics["reference_atom_count"] == 0
    assert evidence["registration"].metrics["spatial_policy"] == "physical"
    assert evidence["registration"].metrics["translation_mode"] == "none"
    assert evidence["registration"].metrics["collection_source_path_match"] == "basename_only"
    assert evidence["force_availability"].status is PilotEvidenceStatus.RESOLVED
    assert evidence["force_availability"].accepted_fraction == pytest.approx(1.0)
    assert evidence["stationarity"].status is PilotEvidenceStatus.PARTIAL
    assert evidence["stationarity"].accepted_fraction == pytest.approx(0.0)
    assert evidence["stationarity"].unresolved_fraction == pytest.approx(1.0)
    assert result.report.metadata["next_execution_boundary"] == "11E8a-S1 density and attractor pilot gauge"


def test_source_bootstrap_does_not_invent_missing_force_evidence(tmp_path: Path):
    result = prepare_na_lta_300k_source_bootstrap(_collection(forces=False), _raw_file(tmp_path))
    force = next(item for item in result.report.evidence if item.evidence_id == "force_availability")
    assert force.status is PilotEvidenceStatus.UNAVAILABLE
    assert force.accepted_fraction == pytest.approx(0.0)
    assert result.na_samples.transformed_forces is None
    assert not np.any(result.na_samples.evidence_masks.force_mask)


def test_source_bootstrap_rejects_wrong_composition_and_tracks_raw_byte_changes(tmp_path: Path):
    path = _raw_file(tmp_path, b"first\n")
    first = prepare_na_lta_300k_source_bootstrap(_collection(), path)
    path.write_bytes(b"second\n")
    second = prepare_na_lta_300k_source_bootstrap(_collection(), path)
    assert first.trajectory_sha256 != second.trajectory_sha256

    with pytest.raises(PilotAuditInputError, match="168-atom Na-LTA"):
        prepare_na_lta_300k_source_bootstrap(_collection(remove_one_na=True), path)


def test_source_bootstrap_rejects_collection_from_another_absolute_source(tmp_path: Path):
    path = _raw_file(tmp_path)
    collection = _collection()
    provenance = FrameCollectionProvenance(
        source_format=collection.provenance.source_format,
        source_files=(str(tmp_path / "different.xml"),),
        velocity_source=collection.provenance.velocity_source,
        coordinate_normalization=collection.provenance.coordinate_normalization,
        stress_source=collection.provenance.stress_source,
        units_source=collection.provenance.units_source,
    )
    mismatched = AtomisticFrameCollection(
        frame_semantics=collection.frame_semantics,
        frame_ids=collection.frame_ids,
        atomic_numbers=collection.atomic_numbers,
        masses=collection.masses,
        pbc=collection.pbc,
        steps=collection.steps,
        times=collection.times,
        cells=collection.cells,
        origins=collection.origins,
        fractional_positions=collection.fractional_positions,
        velocities=collection.velocities,
        forces=collection.forces,
        temperatures=collection.temperatures,
        provenance=provenance,
    )
    with pytest.raises(PilotAuditInputError, match="does not reference"):
        prepare_na_lta_300k_source_bootstrap(mismatched, path)


def test_source_bootstrap_public_exports():
    assert mdstats.PILOT_SOURCE_BOOTSTRAP_STAGE == "11E8a-S0"
    assert mdstats.prepare_na_lta_300k_source_bootstrap is prepare_na_lta_300k_source_bootstrap
    assert "NaLta300KSourceBootstrap" in mdstats.__all__
