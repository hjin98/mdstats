from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

import pytest

import mdstats


def _upstream(*, phase1: bool = True, phase2: bool = False) -> mdstats.PerfCert1UpstreamAuthority:
    return mdstats.PerfCert1UpstreamAuthority(
        cueq_dep1_runtime_digest="a" * 64,
        cueq_phase1_qualification_digest="b" * 64,
        cueq_phase1_passed=phase1,
        phase1_training_authorized=phase1,
        cueq_phase2_qualification_digest="c" * 64,
        cueq_phase2_passed=phase2,
        phase2_source_authorized=phase2,
        phase2_data6_authorized=phase2,
        phase2_source_evaluation_authorized=phase2,
        phase2_pseudolabel_authorized=False,
    )


def _telemetry(total: float, *, workload: str = "d" * 64) -> mdstats.PerfCert1Telemetry:
    factor = total / 1000.0
    return mdstats.PerfCert1Telemetry(
        workload_digest=workload,
        preparation_wall_time_seconds=300.0 * factor,
        target_data2b_wall_time_seconds=80.0 * factor,
        target_data2b_families_per_second=4.0 / factor,
        target_data2c_selection_scoring_seconds=60.0 * factor,
        data6_wall_time_seconds=100.0 * factor,
        data6_frames_per_second=20.0 / factor,
        data6_peak_vram_bytes=8 * 1024**3,
        data6_reserved_vram_bytes=10 * 1024**3,
        data6_headroom_bytes=14 * 1024**3,
        training_wall_time_seconds=600.0 * factor,
        training_updates_per_second=2.0 / factor,
        evaluation_wall_time_seconds=100.0 * factor,
        total_wall_time_seconds=total,
        cuda_oom_count=0,
        cuda_backoff_count=0,
    )


def _profile(
    kind: str,
    *,
    profile_id: str,
    total: float,
    runtime: str = "a" * 64,
    checkpoint: str = "e" * 64,
    target_selection: str = "2" * 64,
    locked_test: bool = False,
) -> mdstats.PerfCert1ProfileRecord:
    modes = {
        mdstats.PROFILE_BASELINE: ("e3nn", "e3nn"),
        mdstats.PROFILE_PHASE1: ("e3nn", "cueq_pure"),
        mdstats.PROFILE_PHASE2: ("cueq_pure", "cueq_pure"),
        mdstats.PROFILE_FALLBACK: ("e3nn", "e3nn"),
    }
    source_mode, train_mode = modes[kind]
    return mdstats.PerfCert1ProfileRecord(
        profile_id=profile_id,
        profile_kind=kind,
        source_kernel_mode=source_mode,
        training_kernel_mode=train_mode,
        scientific_source_digest="0" * 64,
        source_execution_realization_digest="1" * 64,
        training_execution_realization_digest="3" * 64,
        dependency_lock_digest="4" * 64,
        runtime_record_digest=runtime,
        scientific_protocol_digest="5" * 64,
        mace_mh1_sha256=mdstats.PERF_CERT1_MH1_SHA256,
        mace_mpa0_sha256=mdstats.PERF_CERT1_MPA0_SHA256,
        target_head="omat_pbe",
        target_data2b_family_order_digest="6" * 64,
        target_data2c_selection_digest=target_selection,
        data6_selection_digest="7" * 64,
        data7_selection_digest="8" * 64,
        descriptor_parity_passed=True,
        difficulty_parity_passed=True,
        pca_fps_parity_passed=True,
        replay_retention_passed=True,
        checkpoint_admissible=True,
        target_head_extraction_passed=True,
        selected_checkpoint_sha256=checkpoint,
        target_head_sha256="9" * 64,
        selected_target_size=2048,
        selected_seed=17,
        target_validation_metric_name="force_rmse",
        target_validation_metric=0.041,
        replay_validation_metric_name="force_rmse",
        replay_validation_metric=0.055,
        eval2_passed=True,
        eval2_decision_digest="f" * 64,
        deployment_verification_state="pass",
        deployment_verification_digest="a1" * 32,
        physical_verification_state="pass",
        physical_verification_digest="b2" * 32,
        telemetry=_telemetry(total),
        locked_test_used_for_tuning=locked_test,
    )


def test_perf_cert1_phase1_profile_can_pass_without_optional_phase2() -> None:
    baseline = _profile(mdstats.PROFILE_BASELINE, profile_id="e3nn-baseline", total=1000.0)
    # Different final checkpoint bytes are allowed when the hard decisions stay fixed.
    candidate = _profile(mdstats.PROFILE_PHASE1, profile_id="phase1", total=650.0, checkpoint="c1" * 32)
    record = mdstats.PerfCert1QualificationRecord(
        policy=mdstats.PerfCert1Policy(), upstream=_upstream(phase1=True, phase2=False),
        baseline=baseline, candidates=(candidate,),
    )
    assert record.passed
    assert record.recommended_profile_id == "phase1"
    assert record.phase_separated_acceleration_profile_recommended
    assert not record.generated_default_change_authorized
    assert record.generated_default_policy_revision_required
    assessment = record.assessments[0]
    assert assessment.passed
    assert assessment.total_speedup == pytest.approx(1000.0 / 650.0)
    assert baseline.selected_checkpoint_sha256 != candidate.selected_checkpoint_sha256


def test_perf_cert1_faster_profile_fails_if_hard_scientific_decision_changes() -> None:
    baseline = _profile(mdstats.PROFILE_BASELINE, profile_id="e3nn-baseline", total=1000.0)
    candidate = _profile(
        mdstats.PROFILE_PHASE1, profile_id="fast-but-different", total=400.0, target_selection="aa" * 32
    )
    assessment = mdstats.PerfCert1ProfileAssessment(
        policy=mdstats.PerfCert1Policy(), upstream=_upstream(), baseline=baseline, candidate=candidate,
    )
    assert assessment.total_speedup == pytest.approx(2.5)
    assert not assessment.passed
    assert "hard_scientific_decision_identity" in assessment.blocking_reasons
    assert "target_data2c_selection_identity" in assessment.blocking_reasons


def test_perf_cert1_requires_measured_end_to_end_benefit() -> None:
    baseline = _profile(mdstats.PROFILE_BASELINE, profile_id="e3nn-baseline", total=1000.0)
    candidate = _profile(mdstats.PROFILE_PHASE1, profile_id="not-faster", total=1000.0)
    assessment = mdstats.PerfCert1ProfileAssessment(
        policy=mdstats.PerfCert1Policy(), upstream=_upstream(), baseline=baseline, candidate=candidate,
    )
    assert not assessment.performance_benefit_passed
    assert "measured_end_to_end_operational_benefit" in assessment.blocking_reasons


def test_perf_cert1_phase2_is_independently_gated_and_optional_for_phase1_recommendation() -> None:
    baseline = _profile(mdstats.PROFILE_BASELINE, profile_id="e3nn-baseline", total=1000.0)
    phase1 = _profile(mdstats.PROFILE_PHASE1, profile_id="phase1", total=700.0)
    phase2 = _profile(mdstats.PROFILE_PHASE2, profile_id="phase2", total=500.0)

    record = mdstats.PerfCert1QualificationRecord(
        policy=mdstats.PerfCert1Policy(), upstream=_upstream(phase1=True, phase2=False),
        baseline=baseline, candidates=(phase1, phase2),
    )
    assert record.passed
    assert record.recommended_profile_id == "phase1"
    phase2_assessment = next(item for item in record.assessments if item.candidate.profile_id == "phase2")
    assert not phase2_assessment.passed
    assert "CUEQ_PHASE2_SOURCE_DATA6_QUALIFICATION" in phase2_assessment.blocking_reasons

    qualified = replace(record, upstream=_upstream(phase1=True, phase2=True))
    assert qualified.passed
    assert qualified.recommended_profile_id == "phase2"


def test_perf_cert1_locked_test_tuning_fails_closed() -> None:
    baseline = _profile(mdstats.PROFILE_BASELINE, profile_id="e3nn-baseline", total=1000.0)
    candidate = _profile(mdstats.PROFILE_PHASE1, profile_id="tuned", total=300.0, locked_test=True)
    assessment = mdstats.PerfCert1ProfileAssessment(
        policy=mdstats.PerfCert1Policy(), upstream=_upstream(), baseline=baseline, candidate=candidate,
    )
    assert not assessment.passed
    assert "locked_test_used_for_tuning" in assessment.blocking_reasons


def test_perf_cert1_serialization_detects_derived_recommendation_tamper() -> None:
    record = mdstats.PerfCert1QualificationRecord(
        policy=mdstats.PerfCert1Policy(), upstream=_upstream(),
        baseline=_profile(mdstats.PROFILE_BASELINE, profile_id="e3nn-baseline", total=1000.0),
        candidates=(_profile(mdstats.PROFILE_PHASE1, profile_id="phase1", total=600.0),),
    )
    payload = record.to_dict()
    assert mdstats.PerfCert1QualificationRecord.from_dict(payload) == record
    payload["recommended_profile_id"] = "forged-profile"
    with pytest.raises(mdstats.TrainingDataSerializationError, match="recommendation mismatch"):
        mdstats.PerfCert1QualificationRecord.from_dict(payload)


def test_perf_cert1_deferred_cli_runs_directly_from_source_tree(tmp_path: Path) -> None:
    runtime = mdstats.capture_cueq_dep1_runtime()
    phase1 = mdstats.build_cueq_phase1_qualification(runtime=runtime)
    phase2 = mdstats.build_cueq_phase2_qualification(runtime=runtime)
    p1 = tmp_path / "phase1.json"
    p2 = tmp_path / "phase2.json"
    out = tmp_path / "perf-cert1.json"
    p1.write_text(json.dumps(phase1.to_dict()), encoding="utf-8")
    p2.write_text(json.dumps(phase2.to_dict()), encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, str(root / "tools/qualify_mlff_perf_cert1.py"), "deferred",
         "--phase1", str(p1), "--phase2", str(p2), "--output", str(out)],
        cwd=tmp_path, check=False, capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == mdstats.PERF_CERT1_QUALIFICATION_SCHEMA
    assert payload["passed"] is False
    assert "authoritative_e3nn_baseline_missing" in payload["blocking_reasons"]
    assert "accelerated_profile_evidence_missing" in payload["blocking_reasons"]
    assert payload["authorization"]["generated_default_change_authorized"] is False
