from __future__ import annotations

import copy
from pathlib import Path

import pytest

import mdstats
from mdstats.analysis.density import (
    REQUIRED_PILOT_EVIDENCE_IDS,
    NaLta300KPilotReport,
    PilotArtifactRecord,
    PilotAuditInputError,
    PilotAuditResourceError,
    PilotAuditResourcePolicy,
    PilotDatasetIdentity,
    PilotEvidenceRecord,
    PilotEvidenceStatus,
    PilotOverallStatus,
    PilotPMFStatus,
    PilotRateStatus,
    PilotResourceUsage,
    PilotScientificOutcome,
    audit_bundled_na_lta_300k_legacy_evidence,
    prepare_na_lta_300k_pilot_report,
    render_na_lta_300k_pilot_markdown,
)

DIGEST = "a" * 64


def _dataset(*, available=True):
    return PilotDatasetIdentity(
        material="Na-LTA",
        mobile_species="Na",
        temperature_kelvin=300.0,
        atom_count=168,
        species_counts={"Na": 24, "Al": 24, "Si": 24, "O": 96},
        frame_count=2000,
        duration_ps=2.0,
        trajectory_available=available,
        trajectory_digest=DIGEST if available else None,
        registration_signature="b" * 64 if available else None,
    )


def _evidence(*, status=PilotEvidenceStatus.RESOLVED, digest=DIGEST):
    return tuple(
        PilotEvidenceRecord(
            evidence_id=evidence_id,
            stage_id="11E7" if evidence_id == "transition_paths" else "11E8a",
            status=status,
            source_digest=digest,
            accepted_fraction=1.0,
            unresolved_fraction=0.0,
            metrics={"checked": True},
        )
        for evidence_id in REQUIRED_PILOT_EVIDENCE_IDS
    )


def test_complete_pilot_dossier_requires_all_source_bound_evidence():
    report = prepare_na_lta_300k_pilot_report(
        _dataset(),
        _evidence(),
        resources=PilotResourceUsage(wall_seconds=42.0, peak_memory_bytes=1024, worker_count=4),
        outcome=PilotScientificOutcome(
            site_center_count=2,
            supported_basin_count=2,
            observed_connection_count=1,
            transition_path_ensemble_count=1,
            undersampled_path_ensemble_count=1,
            rate_status=PilotRateStatus.UNIDENTIFIED,
            global_pmf_status=PilotPMFStatus.UNSUPPORTED,
            conclusions=("Two supported basins and one observed connection.",),
        ),
    )
    assert report.overall_status is PilotOverallStatus.COMPLETE
    assert report.missing_required_evidence == ()
    assert report.outcome.rate_status is PilotRateStatus.UNIDENTIFIED
    assert report.metadata["rates_inferred"] is False


def test_missing_raw_trajectory_blocks_without_upgrading_legacy_summaries():
    report = prepare_na_lta_300k_pilot_report(
        _dataset(available=False),
        (PilotEvidenceRecord("topology_certificate", "legacy-TS2", PilotEvidenceStatus.LEGACY_SUMMARY_ONLY),),
    )
    assert report.overall_status is PilotOverallStatus.BLOCKED_MISSING_TRAJECTORY
    assert "registration" in report.missing_required_evidence
    assert report.metadata["legacy_summaries_replace_raw_trajectory"] is False


def test_source_mismatch_and_missing_evidence_are_fail_closed():
    mismatched = prepare_na_lta_300k_pilot_report(_dataset(), _evidence(digest="c" * 64))
    assert mismatched.overall_status is PilotOverallStatus.BLOCKED_SOURCE_MISMATCH
    incomplete = prepare_na_lta_300k_pilot_report(_dataset(), _evidence()[:-1])
    assert incomplete.overall_status is PilotOverallStatus.BLOCKED_MISSING_REQUIRED_EVIDENCE
    with pytest.raises(PilotAuditInputError, match="300 K Na-LTA"):
        prepare_na_lta_300k_pilot_report(
            PilotDatasetIdentity("Li-LTA", "Li", 300.0, 1, {"Li": 1}, trajectory_available=False), ()
        )


def test_partial_evidence_is_not_promoted_to_complete():
    evidence = list(_evidence())
    evidence[0] = PilotEvidenceRecord(
        evidence[0].evidence_id,
        evidence[0].stage_id,
        PilotEvidenceStatus.PARTIAL,
        DIGEST,
        accepted_fraction=0.8,
        unresolved_fraction=0.2,
    )
    report = prepare_na_lta_300k_pilot_report(_dataset(), evidence)
    assert report.overall_status is PilotOverallStatus.SCIENTIFICALLY_PARTIAL


def test_serialization_tamper_artifact_binding_and_resources():
    artifact = PilotArtifactRecord("trajectory", "raw trajectory", "data/XDATCAR", 12, "d" * 64, "raw")
    evidence = list(_evidence())
    evidence[0] = PilotEvidenceRecord(
        evidence[0].evidence_id,
        evidence[0].stage_id,
        evidence[0].status,
        DIGEST,
        1.0,
        0.0,
        artifact_ids=("trajectory",),
    )
    report = prepare_na_lta_300k_pilot_report(_dataset(), evidence, artifacts=(artifact,))
    replay = NaLta300KPilotReport.from_dict(report.to_dict())
    assert replay.signature == report.signature
    payload = copy.deepcopy(report.to_dict())
    payload["evidence"][0]["accepted_fraction"] = 0.5
    with pytest.raises(PilotAuditInputError):
        NaLta300KPilotReport.from_dict(payload)
    with pytest.raises(PilotAuditInputError, match="unknown artifacts"):
        prepare_na_lta_300k_pilot_report(
            _dataset(),
            (PilotEvidenceRecord("registration", "C0", PilotEvidenceStatus.RESOLVED, DIGEST,
                                 artifact_ids=("missing",)),),
        )
    with pytest.raises(PilotAuditResourceError, match="artifact limit"):
        prepare_na_lta_300k_pilot_report(
            _dataset(), _evidence(), artifacts=(artifact, PilotArtifactRecord("extra", "extra", "data/extra", 1, "e" * 64)), policy=PilotAuditResourcePolicy(max_artifacts=1)
        )


def test_bundled_real_na_lta_evidence_is_certified_but_pilot_remains_blocked():
    root = Path(__file__).resolve().parents[1]
    report = audit_bundled_na_lta_300k_legacy_evidence(root)
    assert report.overall_status is PilotOverallStatus.BLOCKED_MISSING_TRAJECTORY
    assert report.dataset.atom_count == 168
    assert dict(report.dataset.species_counts) == {"Al": 24, "Na": 24, "O": 96, "Si": 24}
    structural = next(v for v in report.evidence if v.evidence_id == "structural_mapping")
    assert structural.metrics["atomic_states"] == 72
    assert structural.metrics["framework_classes"] == 1
    assert structural.metrics["primitive_ring_count"] == 82
    density = next(v for v in report.evidence if v.evidence_id == "kernel_metric_periodization")
    assert density.metrics["density_frame_count"] == 1300
    assert report.resources.wall_seconds == pytest.approx(125.2780524750001)
    assert all(item.sha256 and item.byte_count > 0 for item in report.artifacts)


def test_markdown_renderer_preserves_blocked_status_and_evidence():
    report = prepare_na_lta_300k_pilot_report(_dataset(available=False), ())
    text = render_na_lta_300k_pilot_markdown(report)
    assert "blocked_missing_trajectory" in text
    assert "Raw trajectory available: false" in text
    assert report.signature in text


def test_public_exports_and_stage_boundary():
    assert mdstats.PILOT_AUDIT_STAGE == "11E8a"
    assert mdstats.prepare_na_lta_300k_pilot_report is prepare_na_lta_300k_pilot_report
    assert mdstats.audit_bundled_na_lta_300k_legacy_evidence is audit_bundled_na_lta_300k_legacy_evidence
    assert "NaLta300KPilotReport" in mdstats.__all__
