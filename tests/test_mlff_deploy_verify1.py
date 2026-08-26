from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from ase import Atoms

import mdstats
from mdstats.training_data import deploy_verify as dv
from mdstats.training_data import model_features
from mdstats.training_data import resources as resource_module
from mdstats.training_data.resources import GpuResourceSnapshot, SystemResourceSnapshot
from mdstats.training_data.inference_parallel import InferenceConcurrencyPolicy


def _h(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()


def _role() -> SimpleNamespace:
    frames = tuple(_h(f"frame-{i}") for i in range(8))
    blocks = (_h("b0"), _h("b0"), _h("b0"), _h("b1"), _h("b1"), _h("b2"), _h("b3"), _h("b3"))
    return SimpleNamespace(
        content_digest=_h("role"),
        evaluation_frame_uids=frames,
        correlation_block_ids=blocks,
    )


def _comparison(a: float = 0.0) -> mdstats.DeployVerifyComparison:
    return mdstats.compare_prediction_channels(
        {"energy": np.array([1.0]), "forces": np.array([0.0, 1.0, 2.0])},
        {"energy": np.array([1.0 + a]), "forces": np.array([0.0, 1.0, 2.0 + a])},
        reference_identity="source",
        observed_identity="target",
        rtol=1e-5,
        atol=1e-6,
    )


def test_probe_set_is_deterministic_and_block_balanced():
    role = _role()
    probe = mdstats.build_deploy_verify_probe_set(
        role,
        target_artifact_digest=_h("artifact"),
        target_artifact_sha256=_h("bytes"),
        maximum_configurations=4,
    )
    assert len(probe.frame_uids) == 4
    assert len(set(probe.correlation_block_ids)) == 4
    assert probe == mdstats.build_deploy_verify_probe_set(
        role,
        target_artifact_digest=_h("artifact"),
        target_artifact_sha256=_h("bytes"),
        maximum_configurations=4,
    )
    assert mdstats.DeployVerifyProbeSet.from_dict(probe.to_dict()) == probe


def test_prediction_comparison_requires_energy_and_forces_and_detects_mismatch():
    assert _comparison(0.0).passed
    bad = _comparison(1e-2)
    assert not bad.passed
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.compare_prediction_channels(
            {"energy": np.array([1.0])}, {"energy": np.array([1.0])},
            reference_identity="a", observed_identity="b", rtol=1e-5, atol=1e-6,
        )


def test_probe_prediction_routes_through_canonical_static_executor(monkeypatch):
    calls = {}

    class Executor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def prediction_channels(self, atoms, *, geometry_identities=None):
            calls["atoms"] = tuple(atoms)
            calls["geometry_identities"] = tuple(geometry_identities or ())
            return {
                "energy": np.array([-1.0, -2.0]),
                "forces": np.zeros(6),
                "stress": np.zeros((2, 3, 3)),
            }

    def from_model_path(cls, model_path, **kwargs):
        calls["model_path"] = Path(model_path)
        calls["kwargs"] = kwargs
        return Executor()

    monkeypatch.setattr(
        model_features.StaticMaceInferenceExecutor,
        "from_model_path",
        classmethod(from_model_path),
    )
    atoms = (
        Atoms("Li", cell=[5, 5, 5], pbc=True),
        Atoms("Li", cell=[5, 5, 5], pbc=True),
    )
    view = mdstats.predict_mace_model_on_probe(
        __file__, atoms, device="cpu", model_dtype="float64", head="target",
        batch_size=2, geometry_identities=(_h("g0"), _h("g1")),
        graph_cache_directory=Path(__file__).parent / "graph-cache",
    )
    assert view["energy"].tolist() == [-1.0, -2.0]
    assert calls["geometry_identities"] == (_h("g0"), _h("g1"))
    assert calls["kwargs"]["batch_size"] == 2
    assert calls["kwargs"]["head"] == "target"


def test_probe_resource_admission_fails_before_model_construction(monkeypatch):
    constructed = False

    def from_model_path(cls, model_path, **kwargs):
        nonlocal constructed
        constructed = True
        raise AssertionError("model construction must not be reached")

    monkeypatch.setattr(
        model_features.StaticMaceInferenceExecutor,
        "from_model_path",
        classmethod(from_model_path),
    )
    monkeypatch.setattr(
        resource_module,
        "detect_system_resources",
        lambda **kwargs: SystemResourceSnapshot(
            cpu_threads_available=4,
            cpu_fraction=0.90,
            cpu_threads_budget=3,
            ram_available_bytes=1024**2,
            ram_fraction=0.80,
            ram_budget_bytes=512 * 1024,
            gpu_memory_fraction=0.90,
            gpu=GpuResourceSnapshot(False, 0, None, None, None, None, None, "cpu"),
        ),
    )
    plan = mdstats.InferenceExecutionPlan(
        batch_policy="fixed", selected_batch_size=1, maximum_batch_size=1
    )
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=1, estimated_ram_mib_per_job=2.0
    )

    with pytest.raises(mdstats.TrainingDataInputError, match="RAM admission cannot fit one job"):
        mdstats.predict_mace_model_on_probe(
            __file__,
            (Atoms("Li", cell=[5, 5, 5], pbc=True),),
            device="cpu",
            model_dtype="float64",
            head=None,
            execution_plan=plan,
            resource_policy=policy,
        )

    assert not constructed


def test_probe_execution_plan_reaches_canonical_static_runtime_authority(monkeypatch):
    captured = {}

    class Executor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def prediction_channels(self, atoms, **kwargs):
            return {
                "energy": np.asarray([-1.0]),
                "forces": np.zeros((1, 1, 3)),
                "stress": np.zeros((1, 3, 3)),
            }

    def from_model_path(cls, model_path, **kwargs):
        captured.update(kwargs)
        return Executor()

    monkeypatch.setattr(
        model_features.StaticMaceInferenceExecutor,
        "from_model_path",
        classmethod(from_model_path),
    )
    monkeypatch.setattr(
        resource_module,
        "detect_system_resources",
        lambda **kwargs: SystemResourceSnapshot(
            cpu_threads_available=4, cpu_fraction=0.90, cpu_threads_budget=3,
            ram_available_bytes=8 * 1024**3, ram_fraction=0.80,
            ram_budget_bytes=6 * 1024**3, gpu_memory_fraction=0.90,
            gpu=GpuResourceSnapshot(False, 0, None, None, None, None, None, "cpu"),
        ),
    )

    mdstats.predict_mace_model_on_probe(
        __file__,
        (Atoms("Li", cell=[5, 5, 5], pbc=True),),
        device="cpu",
        model_dtype="float64",
        head=None,
        execution_plan=mdstats.InferenceExecutionPlan(
            batch_policy="auto", selected_batch_size=1, maximum_batch_size=1
        ),
        resource_policy=InferenceConcurrencyPolicy(
            maximum_auto_jobs=1, estimated_ram_mib_per_job=1.0
        ),
    )

    assert isinstance(captured["runtime_authority"], model_features.StaticInferenceRuntimeAuthority)
    assert captured["concurrent_model_jobs"] == 1


def test_policy_roundtrip_and_dtype_tolerances():
    p32 = mdstats.DeployVerifyPolicy(model_dtype="float32")
    p64 = mdstats.DeployVerifyPolicy(model_dtype="float64")
    assert p32.tolerances == (1e-5, 1e-6)
    assert p64.tolerances == (1e-9, 1e-10)
    assert mdstats.DeployVerifyPolicy.from_dict(p32.to_dict()) == p32


def test_run_record_binds_probe_mliap_and_both_parity_layers():
    probe = mdstats.build_deploy_verify_probe_set(
        _role(), target_artifact_digest=_h("artifact"), target_artifact_sha256=_h("bytes"), maximum_configurations=3
    )
    comp = _comparison(0.0)
    run0 = mdstats.LammpsRun0Record(
        executable_path="/opt/lmp",
        executable_sha256=_h("lmp"),
        command_arguments=("-k", "on"),
        mliap_artifact_sha256=_h("mliap"),
        element_order=("Li", "O"),
        probe_set_digest=probe.content_digest,
        predictions_sha256=_h("pred"),
    )
    record = mdstats.DeployVerifyRunRecord(
        run_plan_digest=_h("run"), eval2_run_record_digest=_h("eval2"),
        policy=mdstats.DeployVerifyPolicy(model_dtype="float32"), probe_set=probe,
        selected_checkpoint_sha256=_h("ckpt"), selected_checkpoint_epoch=29,
        selected_checkpoint_model_sha256=_h("whole"), target_head_name="target_head",
        target_only_model_path="target.model", target_only_model_sha256=_h("target"),
        target_head_export_digest=mdstats.target_head_export_digest(source_model_sha256=_h("whole"), target_model_sha256=_h("target"), target_head="target_head", deployment_dtype="float32"),
        mliap_artifact_path="target.model-mliap_lammps.pt", mliap_artifact_sha256=_h("mliap"),
        mliap_export_digest=_h("export"), checkpoint_to_target_comparison=comp,
        target_to_lammps_comparison=comp, lammps_run0=run0,
    )
    assert record.passed
    assert mdstats.DeployVerifyRunRecord.from_dict(record.to_dict()) == record
    campaign = mdstats.DeployVerifyCampaignRecord(
        campaign_plan_digest=_h("campaign"), target_size_study_digest=_h("study"),
        run_records=(record,), stage_context="production",
    )
    assert mdstats.DeployVerifyCampaignRecord.from_dict(campaign.to_dict()) == campaign


def test_target_head_export_identity_is_recomputed_and_fail_closed():
    probe = mdstats.build_deploy_verify_probe_set(
        _role(), target_artifact_digest=_h("artifact"), target_artifact_sha256=_h("bytes"), maximum_configurations=2
    )
    comp = _comparison(0.0)
    run0 = mdstats.LammpsRun0Record(
        executable_path="/opt/lmp", executable_sha256=_h("lmp"), command_arguments=(),
        mliap_artifact_sha256=_h("mliap"), element_order=("Li",),
        probe_set_digest=probe.content_digest, predictions_sha256=_h("pred"),
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="target-head export identity"):
        mdstats.DeployVerifyRunRecord(
            run_plan_digest=_h("run"), eval2_run_record_digest=_h("eval2"),
            policy=mdstats.DeployVerifyPolicy(model_dtype="float32"), probe_set=probe,
            selected_checkpoint_sha256=_h("ckpt"), selected_checkpoint_epoch=29,
            selected_checkpoint_model_sha256=_h("whole"), target_head_name="target_head",
            target_only_model_path="target.model", target_only_model_sha256=_h("target"),
            target_head_export_digest=_h("tampered-export"),
            mliap_artifact_path="mliap.pt", mliap_artifact_sha256=_h("mliap"),
            mliap_export_digest=_h("export"), checkpoint_to_target_comparison=comp,
            target_to_lammps_comparison=comp, lammps_run0=run0,
        )


def test_failed_comparison_cannot_be_frozen():
    probe = mdstats.build_deploy_verify_probe_set(
        _role(), target_artifact_digest=_h("artifact"), target_artifact_sha256=_h("bytes"), maximum_configurations=2
    )
    run0 = mdstats.LammpsRun0Record(
        executable_path="/opt/lmp", executable_sha256=_h("lmp"), command_arguments=(),
        mliap_artifact_sha256=_h("mliap"), element_order=("Li",),
        probe_set_digest=probe.content_digest, predictions_sha256=_h("pred"),
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.DeployVerifyRunRecord(
            run_plan_digest=_h("run"), eval2_run_record_digest=_h("eval2"),
            policy=mdstats.DeployVerifyPolicy(model_dtype="float32"), probe_set=probe,
            selected_checkpoint_sha256=_h("ckpt"), selected_checkpoint_epoch=29,
            selected_checkpoint_model_sha256=_h("whole"), target_head_name="target_head",
            target_only_model_path="target.model", target_only_model_sha256=_h("target"),
            target_head_export_digest=mdstats.target_head_export_digest(source_model_sha256=_h("whole"), target_model_sha256=_h("target"), target_head="target_head", deployment_dtype="float32"),
            mliap_artifact_path="mliap.pt", mliap_artifact_sha256=_h("mliap"),
            mliap_export_digest=_h("export"), checkpoint_to_target_comparison=_comparison(1e-2),
            target_to_lammps_comparison=_comparison(0.0), lammps_run0=run0,
        )


def test_lammps_run0_contract_parses_energy_forces_and_stress(tmp_path: Path, monkeypatch):
    executable = tmp_path / "lmp"
    executable.write_bytes(b"fake-lammps")
    executable.chmod(0o755)
    mliap = tmp_path / "mliap.pt"
    mliap.write_bytes(b"mliap")
    target = tmp_path / "target.model"
    target.write_bytes(b"target")
    atoms = Atoms("LiO", positions=[[0, 0, 0], [1.5, 0, 0]], cell=[5, 5, 5], pbc=True)
    monkeypatch.setattr(dv, "_model_element_order", lambda path: ("Li", "O"))

    def fake_run(command, cwd, **kwargs):
        cwd = Path(cwd)
        (cwd / "metrics.txt").write_text("-3.0 1 2 3 4 5 6\n")
        (cwd / "forces.dump").write_text(
            "ITEM: TIMESTEP\n0\nITEM: NUMBER OF ATOMS\n2\nITEM: BOX BOUNDS pp pp pp\n0 5\n0 5\n0 5\n"
            "ITEM: ATOMS id type fx fy fz\n2 2 4 5 6\n1 1 1 2 3\n"
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(dv, "_run_file_backed_process", fake_run)
    predictions, record = mdstats.run_lammps_mliap_run0(
        mliap, target, (atoms,), probe_set_digest=_h("probe"),
        lammps_executable=executable, work_directory=tmp_path / "run0",
    )
    assert predictions["energy"].tolist() == [-3.0]
    assert predictions["forces"].tolist() == [1, 2, 3, 4, 5, 6]
    assert predictions["stress"].shape == (1, 3, 3)
    assert record.probe_set_digest == _h("probe")


def test_lammps_run0_timeout_terminates_process_group_and_rejects_stale_outputs(
    tmp_path: Path, monkeypatch
) -> None:
    import signal
    import subprocess

    class Process:
        pid = 4321

        def __init__(self):
            self.waits = 0

        def wait(self, timeout=None):
            self.waits += 1
            if self.waits == 1:
                raise subprocess.TimeoutExpired(["fake"], timeout)
            return -signal.SIGTERM

    process = Process()
    signals = []
    monkeypatch.setattr(dv.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(dv.os, "killpg", lambda pid, sig: signals.append((pid, sig)))
    case = tmp_path / "case"
    case.mkdir()
    (case / "metrics.txt").write_text("stale", encoding="utf-8")
    (case / "forces.dump").write_text("stale", encoding="utf-8")
    with pytest.raises(subprocess.TimeoutExpired):
        dv._run_file_backed_process(
            ("fake",), cwd=case, environment={}, stdout_path=case / "stdout.log",
            stderr_path=case / "stderr.log", timeout_seconds=0.01,
        )
    assert signals == [(4321, signal.SIGTERM)]
