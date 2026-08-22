from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

import mdstats


def _positive_distribution(item: mdstats.AcceleratorDistributionEvidence) -> mdstats.AcceleratorDistributionEvidence:
    versions = {
        "mace": "0.3.16", "e3nn": "0.4.4", "torch": "2.10.0+cu126",
        "cueq-core": "0.10.0", "cueq-torch": "0.10.0", "cueq-ops": "0.10.0", "oeq": "0.5.0",
    }
    return replace(
        item, import_passed=True, distribution_name=item.candidate_distributions[0],
        version=versions[item.logical_name], metadata_sha256="1" * 64,
        record_sha256="2" * 64, wheel_sha256="3" * 64,
        module_file=f"/runtime/{item.import_name}.py", module_file_sha256="4" * 64,
        error_type=None, error_message=None,
    )


def _runtime() -> mdstats.CueqDep1RuntimeRecord:
    base = mdstats.capture_cueq_dep1_runtime(policy=mdstats.CueqDep1Policy(require_cuda=False))
    mace_runtime = replace(
        base.mace_runtime,
        mace_version="0.3.16", e3nn_version="0.4.4",
        blocking_error_type=None, blocking_error_message=None,
        semantic_source_compatibility_passed=True,
    )
    return mdstats.CueqDep1RuntimeRecord(
        policy=mdstats.CueqDep1Policy(require_cuda=True),
        python_version=base.python_version,
        platform=base.platform,
        mace_runtime=mace_runtime,
        distributions=tuple(_positive_distribution(v) for v in base.distributions),
        device=mdstats.AcceleratorDeviceEvidence(
            torch_version="2.10.0+cu126", torch_cuda_version="12.6", cuda_available=True,
            cudnn_version=91002, deterministic_algorithms=True, deterministic_debug_mode=2,
            cudnn_benchmark=False, cudnn_deterministic=True, cuda_matmul_allow_tf32=False,
            cudnn_allow_tf32=False, float32_matmul_precision="highest",
            devices=((0, "NVIDIA GeForce RTX 3090", 8, 6, 24 * 1024**3),),
            nvidia_smi="driver=example", nvcc="cuda=example",
        ),
        environment=base.environment,
    )


def _telemetry(total: float) -> mdstats.PerfCert1Telemetry:
    factor = total / 1000.0
    return mdstats.PerfCert1Telemetry(
        workload_digest="d" * 64,
        preparation_wall_time_seconds=300 * factor,
        target_data2b_wall_time_seconds=80 * factor,
        target_data2b_families_per_second=4 / factor,
        target_data2c_selection_scoring_seconds=60 * factor,
        data6_wall_time_seconds=100 * factor,
        data6_frames_per_second=20 / factor,
        data6_peak_vram_bytes=8 * 1024**3,
        data6_reserved_vram_bytes=10 * 1024**3,
        data6_headroom_bytes=14 * 1024**3,
        training_wall_time_seconds=600 * factor,
        training_updates_per_second=2 / factor,
        evaluation_wall_time_seconds=100 * factor,
        total_wall_time_seconds=total,
        cuda_oom_count=0, cuda_backoff_count=0,
    )


def _profile(kind: str, profile_id: str, total: float, runtime: str) -> mdstats.PerfCert1ProfileRecord:
    modes = {
        mdstats.PROFILE_BASELINE: ("e3nn", "e3nn"),
        mdstats.PROFILE_PHASE1: ("e3nn", "cueq_pure"),
    }
    source_mode, train_mode = modes[kind]
    return mdstats.PerfCert1ProfileRecord(
        profile_id=profile_id, profile_kind=kind, source_kernel_mode=source_mode,
        training_kernel_mode=train_mode, scientific_source_digest="0" * 64,
        source_execution_realization_digest="1" * 64,
        training_execution_realization_digest="3" * 64,
        dependency_lock_digest="4" * 64, runtime_record_digest=runtime,
        scientific_protocol_digest="5" * 64,
        mace_mh1_sha256=mdstats.PERF_CERT1_MH1_SHA256,
        mace_mpa0_sha256=mdstats.PERF_CERT1_MPA0_SHA256, target_head="omat_pbe",
        target_data2b_family_order_digest="6" * 64,
        target_data2c_selection_digest="2" * 64,
        data6_selection_digest="7" * 64, data7_selection_digest="8" * 64,
        descriptor_parity_passed=True, difficulty_parity_passed=True,
        pca_fps_parity_passed=True, replay_retention_passed=True,
        checkpoint_admissible=True, target_head_extraction_passed=True,
        selected_checkpoint_sha256=("e" if kind == mdstats.PROFILE_BASELINE else "c") * 64,
        target_head_sha256="9" * 64, selected_target_size=2048, selected_seed=17,
        target_validation_metric_name="force_rmse", target_validation_metric=0.041,
        replay_validation_metric_name="force_rmse", replay_validation_metric=0.055,
        eval2_passed=True, eval2_decision_digest="f" * 64,
        deployment_verification_state="pass", deployment_verification_digest="a1" * 32,
        physical_verification_state="pass", physical_verification_digest="b2" * 32,
        telemetry=_telemetry(total), locked_test_used_for_tuning=False,
    )


def _perf(runtime: mdstats.CueqDep1RuntimeRecord) -> mdstats.PerfCert1QualificationRecord:
    upstream = mdstats.PerfCert1UpstreamAuthority(
        cueq_dep1_runtime_digest=runtime.content_digest,
        cueq_phase1_qualification_digest="b" * 64, cueq_phase1_passed=True,
        phase1_training_authorized=True, cueq_phase2_qualification_digest="c" * 64,
        cueq_phase2_passed=False, phase2_source_authorized=False,
        phase2_data6_authorized=False, phase2_source_evaluation_authorized=False,
        phase2_pseudolabel_authorized=False,
    )
    return mdstats.PerfCert1QualificationRecord(
        policy=mdstats.PerfCert1Policy(), upstream=upstream,
        baseline=_profile(mdstats.PROFILE_BASELINE, "e3nn-baseline", 1000.0, runtime.content_digest),
        candidates=(_profile(mdstats.PROFILE_PHASE1, "phase1", 650.0, runtime.content_digest),),
    )


def _evidence(policy: mdstats.FinalGpu1Policy, release: str, runtime: str, perf: mdstats.PerfCert1QualificationRecord):
    records = []
    for gate in policy.required_pass_gates:
        content = None
        schema = "example.pass.v1"
        if gate == "CUEQ_DEP1_RUNTIME_FREEZE":
            content = runtime
            schema = mdstats.CUEQ_DEP1_RUNTIME_SCHEMA
        elif gate == "CUEQ_PHASE1_TRAINING_ONLY_QUALIFICATION":
            content = perf.upstream.cueq_phase1_qualification_digest
            schema = mdstats.CUEQ_PHASE1_QUALIFICATION_SCHEMA
        elif gate == "PERF_CERT1_END_TO_END_CERTIFICATION":
            content = perf.content_digest
            schema = mdstats.PERF_CERT1_QUALIFICATION_SCHEMA
        records.append(mdstats.FinalGpu1EvidenceRecord(
            gate_id=gate, acceptance=policy.acceptance_for(gate), disposition="pass",
            release_artifact_sha256=release, evidence_sha256="a" * 64,
            evidence_schema=schema, evidence_content_digest=content,
            cueq_dep1_runtime_digest=runtime,
        ))
    for gate in policy.measure_only_gates:
        records.append(mdstats.FinalGpu1EvidenceRecord(
            gate_id=gate, acceptance=policy.acceptance_for(gate), disposition="fail",
            release_artifact_sha256=release, evidence_sha256="b" * 64,
            evidence_schema="example.measurement.v1", cueq_dep1_runtime_digest=runtime,
        ))
    return tuple(records)


def test_final_gpu1_policy_classifies_old_direct_cueq_probe_as_measure_only() -> None:
    policy = mdstats.FinalGpu1Policy()
    assert policy.acceptance_for("CUEQ_PHASE1_TRAINING_ONLY_QUALIFICATION") == "must_pass"
    assert policy.acceptance_for("MH1_ACCEL1_CUEQ_NUMERICAL_PARITY") == "measure_only"
    assert policy.acceptance_for("CUEQ_PHASE2_SELECTED_HEAD_SOURCE_EXECUTION_OPTIONAL") == "optional"
    assert policy.generated_default_change_authorized is False


def test_final_gpu1_measure_only_failure_does_not_block_passing_phase1_profile() -> None:
    runtime = _runtime()
    assert runtime.passed
    perf = _perf(runtime)
    assert perf.passed
    policy = mdstats.FinalGpu1Policy()
    release = "f" * 64
    record = mdstats.build_final_gpu1_qualification(
        release_artifact_sha256=release,
        foundation_model_sha256=mdstats.FINAL_GPU1_LOCKED_FOUNDATION_SHA256,
        cueq_dep1_runtime=runtime, perf_cert1=perf,
        evidence=_evidence(policy, release, runtime.content_digest, perf), policy=policy,
    )
    assert record.passed
    assert record.recommended_profile_id == "phase1"
    assert not record.generated_default_change_authorized
    assert record.generated_default_policy_revision_required


def test_final_gpu1_missing_measurement_and_required_failure_fail_closed() -> None:
    runtime = _runtime(); perf = _perf(runtime); policy = mdstats.FinalGpu1Policy(); release = "f" * 64
    evidence = list(_evidence(policy, release, runtime.content_digest, perf))
    evidence = [v for v in evidence if v.gate_id != "PERF_P5_ACCELERATOR_PERSISTENCE_REUSE"]
    target = next(i for i, v in enumerate(evidence) if v.gate_id == "SIZE_FIDELITY1_EXHAUSTIVE_CALIBRATION")
    evidence[target] = replace(evidence[target], disposition="fail")
    record = mdstats.build_final_gpu1_qualification(
        release_artifact_sha256=release,
        foundation_model_sha256=mdstats.FINAL_GPU1_LOCKED_FOUNDATION_SHA256,
        cueq_dep1_runtime=runtime, perf_cert1=perf, evidence=evidence, policy=policy,
    )
    assert not record.passed
    assert "required_gate_not_passed:SIZE_FIDELITY1_EXHAUSTIVE_CALIBRATION" in record.blocking_reasons
    assert "missing_measurement_evidence:PERF_P5_ACCELERATOR_PERSISTENCE_REUSE" in record.blocking_reasons


def test_final_gpu1_release_or_runtime_cross_contamination_fails_closed() -> None:
    runtime = _runtime(); perf = _perf(runtime); policy = mdstats.FinalGpu1Policy(); release = "f" * 64
    evidence = list(_evidence(policy, release, runtime.content_digest, perf))
    evidence[0] = replace(evidence[0], release_artifact_sha256="0" * 64, cueq_dep1_runtime_digest="1" * 64)
    record = mdstats.build_final_gpu1_qualification(
        release_artifact_sha256=release,
        foundation_model_sha256=mdstats.FINAL_GPU1_LOCKED_FOUNDATION_SHA256,
        cueq_dep1_runtime=runtime, perf_cert1=perf, evidence=evidence, policy=policy,
    )
    assert not record.passed
    assert any(v.startswith("release_artifact_identity:") for v in record.blocking_reasons)
    assert any(v.startswith("cueq_runtime_identity:") for v in record.blocking_reasons)


def test_final_gpu1_evidence_serialization_detects_tamper(tmp_path: Path) -> None:
    evidence_file = tmp_path / "evidence.json"
    evidence_file.write_text(json.dumps({"schema": "example.v1", "passed": True, "content_digest": "1" * 64}), encoding="utf-8")
    record = mdstats.FinalGpu1EvidenceRecord.from_json_file(
        gate_id="CUEQ_DEP1_RUNTIME_FREEZE", acceptance="must_pass", disposition="pass",
        release_artifact_sha256="2" * 64, evidence_path=evidence_file,
        cueq_dep1_runtime_digest="3" * 64,
    )
    payload = record.to_dict()
    assert mdstats.FinalGpu1EvidenceRecord.from_dict(payload) == record
    payload["disposition"] = "fail"
    with pytest.raises(mdstats.TrainingDataSerializationError, match="digest mismatch"):
        mdstats.FinalGpu1EvidenceRecord.from_dict(payload)


def test_final_gpu1_measure_only_terminal_state_requires_content_addressed_evidence() -> None:
    runtime = _runtime(); perf = _perf(runtime); policy = mdstats.FinalGpu1Policy(); release = "f" * 64
    evidence = list(_evidence(policy, release, runtime.content_digest, perf))
    target = next(i for i, v in enumerate(evidence) if v.gate_id == "PERF_P5_ACCELERATOR_PERSISTENCE_REUSE")
    evidence[target] = mdstats.FinalGpu1EvidenceRecord(
        gate_id="PERF_P5_ACCELERATOR_PERSISTENCE_REUSE",
        acceptance="measure_only", disposition="not_applicable",
        release_artifact_sha256=release, evidence_schema="example.na.v1",
        cueq_dep1_runtime_digest=runtime.content_digest,
    )
    record = mdstats.build_final_gpu1_qualification(
        release_artifact_sha256=release,
        foundation_model_sha256=mdstats.FINAL_GPU1_LOCKED_FOUNDATION_SHA256,
        cueq_dep1_runtime=runtime, perf_cert1=perf, evidence=evidence, policy=policy,
    )
    assert not record.passed
    assert "measurement_evidence_not_content_addressed:PERF_P5_ACCELERATOR_PERSISTENCE_REUSE" in record.blocking_reasons


def test_final_gpu1_runtime_bound_evidence_requires_explicit_runtime_identity() -> None:
    runtime = _runtime(); perf = _perf(runtime); policy = mdstats.FinalGpu1Policy(); release = "f" * 64
    evidence = list(_evidence(policy, release, runtime.content_digest, perf))
    target = next(i for i, v in enumerate(evidence) if v.gate_id == "MH1_ACCEL1_CUEQ_NUMERICAL_PARITY")
    evidence[target] = replace(evidence[target], cueq_dep1_runtime_digest=None)
    record = mdstats.build_final_gpu1_qualification(
        release_artifact_sha256=release,
        foundation_model_sha256=mdstats.FINAL_GPU1_LOCKED_FOUNDATION_SHA256,
        cueq_dep1_runtime=runtime, perf_cert1=perf, evidence=evidence, policy=policy,
    )
    assert not record.passed
    assert "cueq_runtime_binding_missing:MH1_ACCEL1_CUEQ_NUMERICAL_PARITY" in record.blocking_reasons
    assert "MH1_ACCEL1_CUEQ_NUMERICAL_PARITY" in mdstats.FINAL_GPU1_RUNTIME_BOUND_GATES


def test_final_gpu1_handoff_integrity_failure_is_release_blocking_and_serialized() -> None:
    runtime = _runtime(); perf = _perf(runtime); policy = mdstats.FinalGpu1Policy(); release = "f" * 64
    record = mdstats.build_final_gpu1_qualification(
        release_artifact_sha256=release,
        foundation_model_sha256=mdstats.FINAL_GPU1_LOCKED_FOUNDATION_SHA256,
        cueq_dep1_runtime=runtime, perf_cert1=perf,
        evidence=_evidence(policy, release, runtime.content_digest, perf), policy=policy,
        handoff_integrity_failures=("evidence:PERF_P5_ACCELERATOR_PERSISTENCE_REUSE:sha256_changed",),
    )
    assert not record.passed
    assert record.blocking_reasons[0].startswith("handoff_integrity:")
    payload = record.to_dict()
    restored = mdstats.FinalGpu1QualificationRecord.from_dict(payload)
    assert restored.content_digest == record.content_digest


def _handoff_tool():
    import importlib.util

    path = Path(__file__).resolve().parents[1] / "tools" / "run_mlff_final_gpu_qualification.py"
    spec = importlib.util.spec_from_file_location("mdstats_final_gpu1_handoff_tool", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module




def _patch_tool_locks_for_fake_models(tool, monkeypatch: pytest.MonkeyPatch, mh1: Path, mpa0: Path) -> None:
    monkeypatch.setattr(tool, "LOCKED_MODELS", {
        "mace_mh_1": {
            "label": "MACE-MH-1",
            "sha256": tool._sha256(mh1),
            "required_head": "omat_pbe",
        },
        "mace_mpa_0": {
            "label": "MACE-MPA-0-medium",
            "sha256": tool._sha256(mpa0),
            "required_head": "default",
        },
    })

def test_final_gpu1_handoff_registration_is_immutable_and_rehashes_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tool = _handoff_tool()
    mh1 = tmp_path / "mh1.model"; mh1.write_bytes(b"mh1")
    mpa0 = tmp_path / "mpa0.model"; mpa0.write_bytes(b"mpa0")
    _patch_tool_locks_for_fake_models(tool, monkeypatch, mh1, mpa0)
    release = tmp_path / "release.zip"; release.write_bytes(b"release")
    root = tmp_path / "run"
    tool.initialize_handoff(root, mh1, mpa0, release)
    assert tool.verify_handoff_integrity(root)["passed"]

    evidence = tmp_path / "baseline.json"
    evidence.write_text(json.dumps({"schema": "example.baseline.v1", "passed": True, "content_digest": "9" * 64}))
    registered = tool.register_evidence(
        root, "E3NN_BASELINE_COMPLETE_CAMPAIGN", evidence, disposition="auto"
    )
    assert registered["disposition"] == "pass"
    assert tool.verify_handoff_integrity(root)["passed"]

    with pytest.raises(ValueError, match="already contains data"):
        tool.initialize_handoff(root, mh1, mpa0, release)

    replacement = tmp_path / "replacement.json"
    replacement.write_text(json.dumps({"schema": "example.baseline.v1", "passed": True, "content_digest": "8" * 64}))
    with pytest.raises(ValueError, match="already registered"):
        tool.register_evidence(root, "E3NN_BASELINE_COMPLETE_CAMPAIGN", replacement, disposition="auto")

    copied = root / registered["evidence_relative_path"]
    copied.write_text(json.dumps({"schema": "example.baseline.v1", "passed": True, "content_digest": "7" * 64}))
    integrity = tool.verify_handoff_integrity(root)
    assert not integrity["passed"]
    assert "evidence:E3NN_BASELINE_COMPLETE_CAMPAIGN:sha256_changed" in integrity["failures"]


def test_final_gpu1_handoff_rejects_disposition_override_and_missing_cueq_binding(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tool = _handoff_tool()
    mh1 = tmp_path / "mh1.model"; mh1.write_bytes(b"mh1")
    mpa0 = tmp_path / "mpa0.model"; mpa0.write_bytes(b"mpa0")
    _patch_tool_locks_for_fake_models(tool, monkeypatch, mh1, mpa0)
    release = tmp_path / "release.zip"; release.write_bytes(b"release")
    root = tmp_path / "run"
    tool.initialize_handoff(root, mh1, mpa0, release)

    negative = tmp_path / "negative.json"
    negative.write_text(json.dumps({"schema": "example.v1", "passed": False, "content_digest": "1" * 64}))
    with pytest.raises(ValueError, match="contradicts evidence payload"):
        tool.register_evidence(root, "E3NN_BASELINE_COMPLETE_CAMPAIGN", negative, disposition="pass")
    with pytest.raises(ValueError, match="requires the frozen CUEQ-DEP1 runtime digest"):
        tool.register_evidence(root, "PREC3_REAL_CUEQ_ACTIVATION", negative, disposition="auto")



def test_final_gpu1_handoff_integrity_binds_policy_and_complete_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tool = _handoff_tool()
    mh1 = tmp_path / "mh1.model"; mh1.write_bytes(b"mh1")
    mpa0 = tmp_path / "mpa0.model"; mpa0.write_bytes(b"mpa0")
    _patch_tool_locks_for_fake_models(tool, monkeypatch, mh1, mpa0)
    release = tmp_path / "release.zip"; release.write_bytes(b"release")
    root = tmp_path / "run"
    tool.initialize_handoff(root, mh1, mpa0, release)
    manifest_path = root / "final_gpu1_handoff.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["matrix"].pop()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    integrity = tool.verify_handoff_integrity(root)
    assert not integrity["passed"]
    assert "matrix:policy_gate_order_changed" in integrity["failures"]

    manifest = json.loads(manifest_path.read_text())
    manifest["policy"]["optional_gates"] = manifest["policy"]["optional_gates"][:-1]
    manifest["policy"].pop("content_digest", None)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    integrity = tool.verify_handoff_integrity(root)
    assert not integrity["passed"]
    assert "policy_record:authority_changed" in integrity["failures"]


def test_final_gpu1_workstation_clis_bootstrap_the_packaged_source_tree() -> None:
    root = Path(__file__).resolve().parents[1]
    tools = (
        "tools/mdstats-mlff-campaign.py",
        "tools/capture_mlff_cueq_dep1_runtime.py",
        "tools/qualify_mlff_cueq_phase1.py",
        "tools/qualify_mlff_cueq_phase2.py",
        "tools/qualify_mlff_perf_cert1.py",
        "tools/run_mlff_final_gpu_qualification.py",
    )
    for relative in tools:
        text = (root / relative).read_text(encoding="utf-8")
        assert "Path(__file__).resolve().parents[1]" in text
        assert "sys.path.insert(0, str(ROOT))" in text
