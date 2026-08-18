from __future__ import annotations

from pathlib import Path
import importlib.util
import os

import pytest

import mdstats


MACE_SOURCE = Path(os.environ.get("MDSTATS_MACE_SOURCE", "/mnt/data/work_data9a/mace_src"))
MH1_MODEL = Path(os.environ.get("MDSTATS_TEST_MH1_MODEL", "/mnt/data/mace-mh-1.model"))
MPA0_MODEL = Path(os.environ.get("MDSTATS_TEST_MPA0_MODEL", "/mnt/data/mace-mpa-0-medium.model"))
DEPENDENCY_ARCHIVE = Path(os.environ.get("MDSTATS_MACE_DEPENDENCY_ARCHIVE", "/mnt/data/dependencies.tar(20260814-095402).gz"))


def _component(name: str, *, available: bool, version: str | None = "1.0") -> mdstats.MaceRuntimeComponentCapability:
    import_name = {
        "cueq-core": "cuequivariance",
        "cueq-torch": "cuequivariance_torch",
        "cueq-ops": "cuequivariance_ops_torch",
        "oeq": "openequivariance",
    }[name]
    return mdstats.MaceRuntimeComponentCapability(
        logical_name=name,
        import_name=import_name,
        candidate_distributions=(import_name.replace("_", "-"),),
        import_passed=available,
        installed_distribution=import_name.replace("_", "-") if available else None,
        version=version if available else None,
        error_type=None if available else "ModuleNotFoundError",
        error_message=None if available else f"No module named {import_name!r}",
    )


def _source_evidence(policy: mdstats.MaceRuntimeFreezePolicy, *, match: bool = True):
    return tuple(
        mdstats.MaceRuntimeSourceEvidence(
            relative_path=path,
            expected_sha256=expected,
            observed_sha256=expected if match else "0" * 64,
        )
        for path, expected in policy.source_lock
    )


def test_runtime_freeze_policy_and_nested_records_round_trip() -> None:
    policy = mdstats.MaceRuntimeFreezePolicy()
    assert policy.required_mace_version == "0.3.16"
    assert policy.required_e3nn_version == "0.4.4"
    assert len(policy.source_lock) == 8
    assert mdstats.MaceRuntimeFreezePolicy.from_dict(policy.to_dict()) == policy

    capability = _component("cueq-core", available=True, version="0.2.0")
    assert mdstats.MaceRuntimeComponentCapability.from_dict(capability.to_dict()) == capability

    evidence = mdstats.MaceRuntimeSourceEvidence(
        relative_path=policy.source_lock[0][0],
        expected_sha256=policy.source_lock[0][1],
        observed_sha256=policy.source_lock[0][1],
    )
    assert evidence.matched
    assert mdstats.MaceRuntimeSourceEvidence.from_dict(evidence.to_dict()) == evidence


def test_runtime_freeze_independently_reports_cueq_and_oeq_without_fallback() -> None:
    policy = mdstats.MaceRuntimeFreezePolicy()
    components = (
        _component("cueq-core", available=True),
        _component("cueq-torch", available=True),
        _component("cueq-ops", available=True),
        _component("oeq", available=False),
    )
    record = mdstats.MaceRuntimeFreezeRecord(
        policy=policy,
        python_version="3.11.0",
        platform="test",
        torch_version="2.10.0+cu126",
        torch_cuda_version="12.6",
        cuda_available=True,
        mace_version="0.3.16",
        e3nn_version="0.4.4",
        calculator_enable_cueq_supported=True,
        calculator_enable_oeq_supported=True,
        training_enable_cueq_supported=True,
        training_enable_oeq_supported=True,
        source_evidence=_source_evidence(policy),
        component_capabilities=components,
    )
    assert record.core_runtime_passed
    assert record.cueq_stack_available
    assert not record.oeq_available
    # OEQ is optional for the public CuEq backend: pure CuEq is a complete
    # MACE-0.3.16 training/inference realization.
    assert record.dependency_target_passed
    assert not record.qualified_for_mh1_dep0  # no explicit checkpoint-load evidence in this unit record
    assert record.passed_for_backend("e3nn")
    assert record.passed_for_backend("cueq")
    assert not any("OpenEquivariance" in item for item in record.backend_failure_reasons("cueq"))
    # The evidence layer contains no selected/fallback backend field: missing
    # OEQ remains an explicit missing capability rather than an e3nn mutation.
    payload = record.to_dict()
    assert "backend" not in payload
    restored = mdstats.MaceRuntimeFreezeRecord.from_dict(payload)
    assert restored == record


def test_runtime_freeze_can_require_oeq_explicitly() -> None:
    policy = mdstats.MaceRuntimeFreezePolicy(require_oeq=True)
    record = mdstats.MaceRuntimeFreezeRecord(
        policy=policy,
        python_version="3.11.0", platform="test",
        torch_version="2.10.0+cu126", torch_cuda_version="12.6",
        cuda_available=True, mace_version="0.3.16", e3nn_version="0.4.4",
        calculator_enable_cueq_supported=True, calculator_enable_oeq_supported=True,
        training_enable_cueq_supported=True, training_enable_oeq_supported=True,
        source_evidence=_source_evidence(policy),
        component_capabilities=(
            _component("cueq-core", available=True), _component("cueq-torch", available=True),
            _component("cueq-ops", available=True), _component("oeq", available=False),
        ),
    )
    assert not record.passed_for_backend("cueq")
    assert any("OpenEquivariance" in item for item in record.backend_failure_reasons("cueq"))


def test_runtime_freeze_semantic_source_probe_can_authorize_nonidentical_0316_bytes() -> None:
    policy = mdstats.MaceRuntimeFreezePolicy(require_cueq_stack=False, require_oeq=False)
    record = mdstats.MaceRuntimeFreezeRecord(
        policy=policy,
        python_version="3.11.0", platform="test",
        torch_version="2.10.0", torch_cuda_version=None, cuda_available=False,
        mace_version="0.3.16", e3nn_version="0.4.4",
        calculator_enable_cueq_supported=True, calculator_enable_oeq_supported=True,
        training_enable_cueq_supported=True, training_enable_oeq_supported=True,
        source_evidence=_source_evidence(policy, match=False),
        component_capabilities=(
            _component("cueq-core", available=False), _component("cueq-torch", available=False),
            _component("cueq-ops", available=False), _component("oeq", available=False),
        ),
        semantic_source_compatibility_passed=True,
        semantic_source_compatibility_notes=("semantic probe passed",),
    )
    assert not record.source_lock_passed
    assert record.source_compatibility_passed
    assert record.core_runtime_passed
    assert record.passed_for_backend("e3nn")
    restored = mdstats.MaceRuntimeFreezeRecord.from_dict(record.to_dict())
    assert restored == record


def test_runtime_freeze_source_lock_is_fail_closed() -> None:
    policy = mdstats.MaceRuntimeFreezePolicy(require_cueq_stack=False, require_oeq=False)
    components = (
        _component("cueq-core", available=False),
        _component("cueq-torch", available=False),
        _component("cueq-ops", available=False),
        _component("oeq", available=False),
    )
    record = mdstats.MaceRuntimeFreezeRecord(
        policy=policy,
        python_version="3.11.0",
        platform="test",
        torch_version="2.10.0",
        torch_cuda_version=None,
        cuda_available=False,
        mace_version="0.3.16",
        e3nn_version="0.4.4",
        calculator_enable_cueq_supported=True,
        calculator_enable_oeq_supported=True,
        training_enable_cueq_supported=True,
        training_enable_oeq_supported=True,
        source_evidence=_source_evidence(policy, match=False),
        component_capabilities=components,
    )
    assert not record.source_lock_passed
    assert not record.core_runtime_passed
    assert not record.dependency_target_passed


def test_locked_v0316_source_hashes_match_supplied_source_tree() -> None:
    if not MACE_SOURCE.is_dir():
        pytest.skip("supplied MACE 0.3.16 source tree is not mounted")
    policy = mdstats.MaceRuntimeFreezePolicy()
    import hashlib

    observed = []
    for relative_path, expected in policy.source_lock:
        path = MACE_SOURCE / relative_path
        assert path.is_file(), relative_path
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        observed.append((relative_path, actual))
        assert actual == expected, relative_path
    assert tuple(path for path, _ in observed) == tuple(path for path, _ in policy.source_lock)


@pytest.mark.slow
def test_real_mh1_and_mpa0_checkpoints_load_through_e3nn_reference_path() -> None:
    if importlib.util.find_spec("mace") is None or importlib.util.find_spec("e3nn") is None:
        pytest.skip("real MACE/e3nn environment is not active")
    if not MH1_MODEL.is_file() or not MPA0_MODEL.is_file():
        pytest.skip("supplied MH-1/MPA-0 checkpoints are not mounted")

    # Accelerator packages are not required for this particular acceptance
    # clause; they are probed independently by the same record.
    policy = mdstats.MaceRuntimeFreezePolicy(require_cueq_stack=False, require_oeq=False)
    record = mdstats.probe_mace_runtime_freeze(
        policy=policy,
        checkpoint_requests=(
            (MH1_MODEL, "omat_pbe"),
            (MPA0_MODEL, "default"),
        ),
        supplied_artifacts=(DEPENDENCY_ARCHIVE,) if DEPENDENCY_ARCHIVE.is_file() else (),
    )
    assert record.core_runtime_passed, record.to_dict()
    assert len(record.checkpoint_loads) == 2
    assert all(item.passed for item in record.checkpoint_loads), record.to_dict()
    assert record.checkpoint_loads[0].available_heads[-1] == "omat_pbe"
    assert record.checkpoint_loads[1].available_heads == ("default",)
    assert record.checkpoints_passed
    if DEPENDENCY_ARCHIVE.is_file():
        assert record.supplied_artifacts and record.supplied_artifacts[0][0] == DEPENDENCY_ARCHIVE.name


def test_doctor_runtime_freeze_backend_guard_is_fail_closed() -> None:
    from mdstats.training_data import campaign_cli

    acceleration = mdstats.MaceAccelerationPolicy(backend="cueq", require_available=True)
    policy = mdstats.MaceRuntimeFreezePolicy()
    record = mdstats.MaceRuntimeFreezeRecord(
        policy=policy,
        python_version="3.11.0",
        platform="test",
        torch_version="2.10.0+cu126",
        torch_cuda_version="12.6",
        cuda_available=True,
        mace_version="0.3.16",
        e3nn_version="0.4.4",
        calculator_enable_cueq_supported=True,
        calculator_enable_oeq_supported=True,
        training_enable_cueq_supported=True,
        training_enable_oeq_supported=True,
        source_evidence=_source_evidence(policy),
        component_capabilities=(
            _component("cueq-core", available=False),
            _component("cueq-torch", available=False),
            _component("cueq-ops", available=False),
            _component("oeq", available=False),
        ),
    )
    message = campaign_cli._runtime_freeze_backend_failure(acceleration, record)
    assert message is not None
    assert "no backend fallback was applied" in message
    assert acceleration.backend.value == "cueq"

    e3nn = mdstats.MaceAccelerationPolicy(backend="e3nn")
    assert campaign_cli._runtime_freeze_backend_failure(e3nn, record) is None


def test_runtime_freeze_semantic_probe_accepts_nonsemantic_source_byte_change(tmp_path: Path) -> None:
    import mace
    from mdstats.training_data import mace_runtime_freeze as runtime_freeze

    source_root = Path(mace.__file__).resolve().parent.parent
    required = (
        "mace/cli/run_train.py",
        "mace/tools/train.py",
        "mace/tools/multihead_tools.py",
        "mace/tools/scripts_utils.py",
        "mace/tools/arg_parser.py",
    )
    for relative in required:
        src = source_root / relative
        if not src.is_file():
            pytest.skip(f"MACE source file unavailable: {src}")
        dst = tmp_path / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
    # Change the bytes without changing any behavior required by mdstats.
    run_train = tmp_path / "mace/cli/run_train.py"
    run_train.write_text(run_train.read_text(encoding="utf-8") + "\n# mdstats semantic-lock test\n", encoding="utf-8")
    passed, notes = runtime_freeze._probe_mace_source_semantics(tmp_path)
    assert passed, notes
