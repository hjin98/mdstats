from __future__ import annotations

from dataclasses import replace

import pytest

import mdstats


def _positive_distribution(item: mdstats.AcceleratorDistributionEvidence) -> mdstats.AcceleratorDistributionEvidence:
    versions = {
        "mace": "0.3.16",
        "e3nn": "0.4.4",
        "torch": "2.10.0+cu126",
        "cueq-core": "0.10.0",
        "cueq-torch": "0.10.0",
        "cueq-ops": "0.10.0",
        "oeq": "0.5.0",
    }
    return replace(
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


def _positive_record(*, require_oeq: bool = False) -> mdstats.CueqDep1RuntimeRecord:
    base = mdstats.capture_cueq_dep1_runtime(policy=mdstats.CueqDep1Policy(require_cuda=False))
    policy = mdstats.CueqDep1Policy(require_cuda=True, require_oeq=require_oeq)
    distributions = tuple(_positive_distribution(item) for item in base.distributions)
    device = mdstats.AcceleratorDeviceEvidence(
        torch_version="2.10.0+cu126",
        torch_cuda_version="12.6",
        cuda_available=True,
        cudnn_version=91002,
        deterministic_algorithms=True, deterministic_debug_mode=2,
        cudnn_benchmark=False, cudnn_deterministic=True,
        cuda_matmul_allow_tf32=False, cudnn_allow_tf32=False,
        float32_matmul_precision="highest",
        devices=((0, "NVIDIA GeForce RTX 3090", 8, 6, 24 * 1024**3),),
        nvidia_smi="driver=example",
        nvcc="cuda=example",
    )
    return mdstats.CueqDep1RuntimeRecord(
        policy=policy,
        python_version=base.python_version,
        platform=base.platform,
        mace_runtime=base.mace_runtime,
        distributions=distributions,
        device=device,
        environment=base.environment,
    )


def test_cueq_dep1_component_matrix_includes_cuda13_and_ops_layer() -> None:
    components = {name: candidates for name, _, candidates in mdstats.CUEQ_DEP1_COMPONENTS}
    assert "cueq-ops" in components
    assert components["cueq-ops"][0] == "cuequivariance-ops-torch-cu13"
    assert "cuequivariance-ops-torch-cu12" in components["cueq-ops"]


def test_cueq_dep1_positive_record_is_content_addressed_and_roundtrips() -> None:
    record = _positive_record()
    assert record.mace_runtime.core_runtime_passed
    assert record.required_stack_content_addressed
    assert record.accelerator_capability_passed
    assert record.passed
    assert record.blocking_reasons == ()
    assert mdstats.CueqDep1RuntimeRecord.from_dict(record.to_dict()) == record


def test_cueq_dep1_oeq_is_optional_for_phase1_but_fail_closed_when_required() -> None:
    record = _positive_record(require_oeq=False)
    distributions = tuple(
        replace(item, import_passed=False, metadata_sha256=None, record_sha256=None, module_file_sha256=None)
        if item.logical_name == "oeq" else item
        for item in record.distributions
    )
    phase1 = replace(record, distributions=distributions)
    assert phase1.passed
    required = replace(phase1, policy=mdstats.CueqDep1Policy(require_cuda=True, require_oeq=True))
    assert not required.passed
    assert "oeq_import" in required.blocking_reasons


def test_cueq_dep1_missing_cuda_is_negative_evidence_not_fallback() -> None:
    record = _positive_record()
    negative = replace(
        record,
        device=mdstats.AcceleratorDeviceEvidence(
            torch_version="2.10.0+cpu", torch_cuda_version=None, cuda_available=False,
            cudnn_version=None, deterministic_algorithms=None, deterministic_debug_mode=None,
            cudnn_benchmark=None, cudnn_deterministic=None, cuda_matmul_allow_tf32=None,
            cudnn_allow_tf32=None, float32_matmul_precision=None, devices=(), nvidia_smi=None, nvcc=None,
        ),
    )
    assert not negative.passed
    assert "torch_cuda_available" in negative.blocking_reasons
    assert negative.policy.training_kernel_mode == "cueq_pure"
    assert negative.policy.source_inference_kernel_mode == "e3nn"


def test_cueq_dep1_digest_tamper_fails_closed() -> None:
    payload = _positive_record().to_dict()
    payload["python_version"] = "tampered"
    with pytest.raises(mdstats.TrainingDataSerializationError, match="digest mismatch"):
        mdstats.CueqDep1RuntimeRecord.from_dict(payload)


def test_current_host_capture_has_consistent_pass_and_blocking_state() -> None:
    record = mdstats.capture_cueq_dep1_runtime()
    assert record.passed == (len(record.blocking_reasons) == 0)
    assert [item.logical_name for item in record.distributions] == [
        item[0] for item in mdstats.CUEQ_DEP1_COMPONENTS
    ]
