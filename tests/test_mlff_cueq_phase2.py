from __future__ import annotations

from dataclasses import replace

import pytest

import mdstats


def _runtime() -> mdstats.CueqDep1RuntimeRecord:
    base = mdstats.capture_cueq_dep1_runtime(policy=mdstats.CueqDep1Policy(require_cuda=False))
    versions = {
        "torch": "2.10.0+cu126", "mace": "0.3.16", "e3nn": "0.4.4",
        "cueq-core": "0.10.0", "cueq-torch": "0.10.0", "cueq-ops": "0.10.0", "oeq": "0.5.0",
    }
    distributions = tuple(
        replace(
            item,
            import_passed=True,
            distribution_name=item.candidate_distributions[0],
            version=versions[item.logical_name],
            metadata_sha256="1" * 64,
            record_sha256="2" * 64,
            wheel_sha256="3" * 64,
            module_file=f"/runtime/{item.import_name}.py",
            module_file_sha256="4" * 64,
            error_type=None,
            error_message=None,
        )
        for item in base.distributions
    )
    device = mdstats.AcceleratorDeviceEvidence(
        torch_version="2.10.0+cu126", torch_cuda_version="12.6", cuda_available=True,
        cudnn_version=91002, deterministic_algorithms=True, deterministic_debug_mode=2,
        cudnn_benchmark=False, cudnn_deterministic=True, cuda_matmul_allow_tf32=False,
        cudnn_allow_tf32=False, float32_matmul_precision="highest",
        devices=((0, "NVIDIA GeForce RTX 3090", 8, 6, 24 * 1024**3),),
        nvidia_smi="driver=example", nvcc="cuda=example",
    )
    return mdstats.CueqDep1RuntimeRecord(
        policy=mdstats.CueqDep1Policy(require_cuda=True),
        python_version=base.python_version, platform=base.platform, mace_runtime=base.mace_runtime,
        distributions=distributions, device=device, environment=base.environment,
    )


def _accel(*, passed: bool = True, candidate_selection: tuple[str, ...] = ("a", "c")) -> mdstats.MaceAccelerationParityRecord:
    return mdstats.MaceAccelerationParityRecord(
        reference_mode="e3nn", candidate_mode="cueq_pure", dtype="float64",
        structure_count=12, atom_count=96,
        energy_max_abs=1e-10, energy_rmse=2e-11,
        force_max_abs=2e-10, force_rmse=3e-11,
        stress_max_abs=1e-11, stress_rmse=2e-12,
        descriptor_max_abs=4e-10, descriptor_rmse=8e-11,
        reference_selection=("a", "c"), candidate_selection=candidate_selection,
        policy_digest="5" * 64, passed=passed,
    )


def _corpus(*, locked: bool = False) -> mdstats.CueqPhase2DevelopmentCorpus:
    return mdstats.CueqPhase2DevelopmentCorpus(
        corpus_digest="6" * 64, deterministic_order_digest="7" * 64,
        structure_count=12, atom_count=96,
        locked_test_used_for_tuning=locked,
    )


def _assessment(runtime: mdstats.CueqDep1RuntimeRecord, *, pseudolabel: bool = True, data7_candidate=("u1", "u3")) -> mdstats.CueqPhase2PathAssessment:
    policy = mdstats.CueqPhase2Policy()
    realization = mdstats.cueq_phase2_execution_realization_digest(
        policy=policy, runtime_record_digest=runtime.content_digest, dtype="float64"
    )
    data6 = mdstats.CueqPhase2Data6ParityRecord(
        scientific_source_digest=policy.source_potential_digest,
        candidate_execution_realization_digest=realization,
        data6_protocol_digest="8" * 64,
        frozen_reference_transform_digest="9" * 64,
        difficulty_max_abs=1e-10, difficulty_rmse=2e-11, difficulty_parity_passed=True,
        pca_input_max_abs=2e-10, pca_input_rmse=3e-11, pca_input_parity_passed=True,
        fps_input_max_abs=2e-10, fps_input_rmse=3e-11, fps_input_parity_passed=True,
        reference_data6_selection=("s1", "s4"), candidate_data6_selection=("s1", "s4"),
        reference_data7_selection=("u1", "u3"), candidate_data7_selection=data7_candidate,
        pseudolabel_requested=pseudolabel,
        pseudolabel_values_parity_passed=True if pseudolabel else None,
        atomic_e0_parity_passed=True if pseudolabel else None,
        pseudolabel_scientific_source_digest=policy.source_potential_digest if pseudolabel else None,
        pseudolabel_execution_realization_digest=realization if pseudolabel else None,
    )
    return mdstats.CueqPhase2PathAssessment(
        policy=policy, corpus=_corpus(), runtime_record_digest=runtime.content_digest,
        reference_source_kernel_mode="e3nn", candidate_source_kernel_mode="cueq_pure", dtype="float64",
        acceleration_parity=_accel(), data6_parity=data6,
        reference_wall_time_seconds=100.0, candidate_wall_time_seconds=40.0,
        candidate_peak_vram_bytes=8 * 1024**3, candidate_reserved_vram_bytes=10 * 1024**3,
    )


def test_phase2_policy_freezes_original_scientific_source_and_selected_head_execution_identity() -> None:
    policy = mdstats.CueqPhase2Policy()
    assert policy.source_checkpoint_sha256 == mdstats.CUEQ_PHASE2_MH1_SHA256
    assert policy.source_head == "omat_pbe"
    assert policy.reference_source_kernel_mode == "e3nn"
    assert policy.candidate_source_kernel_mode == "cueq_pure"
    assert policy.selected_head_checkpoint_sha256 == mdstats.CUEQ_PHASE2_SELECTED_HEAD_SHA256
    assert policy.selected_head_qualification_digest == mdstats.CUEQ_PHASE2_SELECTED_HEAD_QUALIFICATION_DIGEST
    with pytest.raises(mdstats.TrainingDataInputError, match="scientific source head"):
        mdstats.CueqPhase2Policy(source_head="default")


def test_phase2_development_corpus_rejects_locked_test_tuning_and_missing_available_strata() -> None:
    assert _corpus().passed
    assert not _corpus(locked=True).passed
    corpus = mdstats.CueqPhase2DevelopmentCorpus(
        corpus_digest="a" * 64, deterministic_order_digest="b" * 64, structure_count=2, atom_count=4,
        available_strata=("ordinary", "high_force_difficulty"), covered_strata=("ordinary",),
    )
    assert not corpus.passed
    assert mdstats.CueqPhase2DevelopmentCorpus.from_dict(corpus.to_dict()) == corpus


def test_phase2_path_requires_existing_numerical_authority_and_exact_selection_identity() -> None:
    runtime = _runtime()
    assessment = _assessment(runtime)
    assert assessment.passed
    assert assessment.speedup == pytest.approx(2.5)
    assert mdstats.CueqPhase2PathAssessment.from_dict(assessment.to_dict()) == assessment

    bad = _assessment(runtime, data7_candidate=("u2", "u3"))
    assert not bad.passed
    assert "data7_selection_identity" in bad.blocking_reasons


def test_phase2_pseudolabel_authorization_requires_explicit_dual_lineage() -> None:
    runtime = _runtime()
    with_labels = _assessment(runtime, pseudolabel=True)
    qualified = mdstats.build_cueq_phase2_qualification(runtime=runtime, assessments=(with_labels,))
    assert qualified.passed
    assert qualified.selected_head_source_cueq_execution_authorized
    assert qualified.data6_cueq_execution_authorized
    assert qualified.source_evaluation_cueq_execution_authorized
    assert qualified.pseudolabel_cueq_execution_authorized
    assert not qualified.original_six_head_cueq_execution_authorized
    assert not qualified.generated_default_change_authorized

    without_labels = _assessment(runtime, pseudolabel=False)
    qualified_no_labels = mdstats.build_cueq_phase2_qualification(runtime=runtime, assessments=(without_labels,))
    assert qualified_no_labels.passed
    assert not qualified_no_labels.pseudolabel_cueq_execution_authorized


def test_phase2_negative_runtime_stays_deferred_and_cannot_authorize_source_execution() -> None:
    runtime = mdstats.capture_cueq_dep1_runtime()
    record = mdstats.build_cueq_phase2_qualification(runtime=runtime)
    assert not record.passed
    assert "development_path_assessment_missing" in record.blocking_reasons
    if not runtime.passed:
        assert "CUEQ_DEP1_RUNTIME_FREEZE" in record.blocking_reasons
    assert not record.selected_head_source_cueq_execution_authorized
    assert not record.data6_cueq_execution_authorized
    assert not record.original_six_head_cueq_execution_authorized


def test_phase2_serialization_detects_execution_lineage_tamper() -> None:
    runtime = _runtime()
    payload = _assessment(runtime).to_dict()
    payload["runtime_record_digest"] = "f" * 64
    with pytest.raises(mdstats.TrainingDataSerializationError, match="execution-realization digest mismatch|path-assessment digest mismatch"):
        mdstats.CueqPhase2PathAssessment.from_dict(payload)


def test_phase2_cli_runs_directly_from_source_tree(tmp_path) -> None:
    import json
    from pathlib import Path
    import subprocess
    import sys

    runtime = mdstats.capture_cueq_dep1_runtime()
    runtime_path = tmp_path / "runtime.json"
    output_path = tmp_path / "phase2.json"
    runtime_path.write_text(json.dumps(runtime.to_dict()), encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, str(root / "tools/qualify_mlff_cueq_phase2.py"), "deferred",
         "--runtime", str(runtime_path), "--output", str(output_path)],
        cwd=tmp_path, check=False, capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["schema"] == mdstats.CUEQ_PHASE2_QUALIFICATION_SCHEMA
    assert payload["passed"] is False
    assert "development_path_assessment_missing" in payload["blocking_reasons"]
