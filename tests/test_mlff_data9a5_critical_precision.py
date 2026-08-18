from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pytest

import mdstats
from mdstats.training_data import critical_precision_cli

FOUNDATION_MODEL = Path(
    os.environ.get("MDSTATS_MACE_FOUNDATION_MODEL", "/mnt/data/mace-mpa-0-medium.model")
)
REAL_TRAJECTORY = Path(
    os.environ.get("MDSTATS_MACE_REAL_TRAJECTORY", "/mnt/data/vasprun.xml")
)


def test_critical_precision_policy_is_safety_locked_and_round_trips() -> None:
    policy = mdstats.MaceCriticalPrecisionPolicy()
    assert policy.energy_accumulation_dtype == "float64"
    assert policy.virial_accumulation_dtype == "float64"
    assert policy.observable_output_dtype == "float64"
    assert policy.md_state_dtype == "float64"
    assert not policy.allow_tf32
    assert policy.training_force_jacobian_dtype == "model"
    assert mdstats.MaceCriticalPrecisionPolicy.from_dict(policy.to_dict()) == policy
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.MaceCriticalPrecisionPolicy(energy_accumulation_dtype="float32")
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.MaceCriticalPrecisionPolicy(allow_tf32=True)
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.MaceCriticalPrecisionPolicy(training_force_jacobian_dtype="float64")


def test_ase_md_state_is_fail_closed_and_round_trips() -> None:
    from ase import Atoms

    atoms = Atoms("H2", positions=[[0.0, 0.0, 0.0], [0.7, 0.0, 0.0]], cell=[5, 5, 5], pbc=True)
    atoms.set_momenta(np.zeros((2, 3), dtype=np.float64))
    audit = mdstats.audit_ase_md_state_precision(atoms, require_momenta=True)
    assert audit.passed
    assert mdstats.AseMdStatePrecisionAudit.from_dict(audit.to_dict()) == audit

    atoms.arrays["momenta"] = atoms.arrays["momenta"].astype(np.float32)
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.audit_ase_md_state_precision(atoms, require_momenta=True)


def test_optimizer_identity_separates_model_and_critical_precision() -> None:
    fp32 = mdstats.MaceOptimizerPolicy(default_dtype="float32")
    fp64 = mdstats.MaceOptimizerPolicy(default_dtype="float64")
    assert fp32.default_dtype == "float32"
    assert fp64.default_dtype == "float64"
    assert fp32.critical_precision_policy == fp64.critical_precision_policy
    assert fp32.policy_digest != fp64.policy_digest
    assert mdstats.MaceOptimizerPolicy.from_dict(fp32.to_dict()) == fp32


def test_legacy_optimizer_policy_deserializes_with_default_critical_precision() -> None:
    from mdstats.training_data._common import digest

    payload = {
        "schema": "mdstats.mace-optimizer-policy.v1",
        "learning_rate": 1.0e-4,
        "batch_size": 1,
        "valid_batch_size": 1,
        "max_num_epochs": 30,
        "eval_interval": 1,
        "ema": True,
        "ema_decay": 0.99999,
        "amsgrad": True,
        "weight_decay": 1.0e-6,
        "clip_grad": 10.0,
        "default_dtype": "float32",
        "device": "cuda",
        "seed": 1,
    }
    payload["policy_digest"] = digest(payload)
    restored = mdstats.MaceOptimizerPolicy.from_dict(payload)
    assert restored.default_dtype == "float32"
    assert restored.critical_precision_policy == mdstats.MaceCriticalPrecisionPolicy()


def test_eval_completion_probe_requires_complete_finite_output(tmp_path: Path) -> None:
    from ase import Atoms
    from ase.io import write

    atoms = Atoms("LiO", positions=[[0.0, 0.0, 0.0], [1.6, 0.0, 0.0]], cell=[6, 6, 6], pbc=True)
    atoms.info["MACE_energy"] = -2.0
    atoms.info["MACE_stress"] = np.zeros(6)
    atoms.arrays["MACE_forces"] = np.zeros((2, 3))
    output = tmp_path / "predictions.xyz"
    write(output, [atoms], format="extxyz")
    assert critical_precision_cli._valid_eval_output(output, expected_count=1, require_stress=True)
    assert not critical_precision_cli._valid_eval_output(output, expected_count=2, require_stress=True)
    del atoms.info["MACE_stress"]
    write(output, [atoms], format="extxyz")
    assert not critical_precision_cli._valid_eval_output(output, expected_count=1, require_stress=True)
    atoms.arrays["MACE_forces"][0, 0] = np.nan
    write(output, [atoms], format="extxyz")
    assert not critical_precision_cli._valid_eval_output(output, expected_count=1, require_stress=False)


@pytest.mark.slow
def test_real_fp32_body_returns_fp64_critical_observables() -> None:
    if not FOUNDATION_MODEL.is_file() or not REAL_TRAJECTORY.is_file():
        pytest.skip("real MPA-0 model or VASP trajectory is not mounted")
    pytest.importorskip("mace")
    pytest.importorskip("ase")
    import torch
    from ase.io import read
    from mace.calculators import MACECalculator

    mdstats.install_mace_critical_fp64_patch()
    atoms = read(REAL_TRAJECTORY, index=0)
    calculator = MACECalculator(
        model_paths=str(FOUNDATION_MODEL),
        device="cpu",
        default_dtype="float32",
    )
    atoms.calc = calculator
    energy = atoms.get_potential_energy()
    forces = atoms.get_forces()
    stress = atoms.get_stress(voigt=False)
    assert next(calculator.models[0].parameters()).dtype == torch.float32
    assert np.asarray(calculator.results["energy"]).dtype == np.float64
    assert np.asarray(calculator.results["node_energy"]).dtype == np.float64
    assert np.asarray(calculator.results["forces"]).dtype == np.float64
    assert np.asarray(calculator.results["stress"]).dtype == np.float64
    assert np.isfinite(energy)
    assert np.all(np.isfinite(forces))
    assert np.all(np.isfinite(stress))

    batch = calculator._atoms_to_batch(atoms)
    model = calculator.models[0]
    batch = calculator._clone_batch(batch)
    model_dtype = next(model.parameters()).dtype
    for key in batch.keys:
        value = batch[key]
        if torch.is_tensor(value) and torch.is_floating_point(value):
            batch[key] = value.to(dtype=model_dtype)
    output = model(
        batch.to_dict(),
        compute_force=True,
        compute_virials=True,
        compute_stress=True,
    )
    audit = mdstats.audit_mace_critical_precision(model, output)
    assert audit.passed
    assert audit.model_dtype == "float32"
    assert audit.energy_dtype == "float64"
    assert audit.force_dtype == "float64"
    assert audit.virial_dtype == "float64"
    assert audit.stress_dtype == "float64"
    assert mdstats.MaceCriticalPrecisionAudit.from_dict(audit.to_dict()) == audit


def _pid_is_running(pid: int) -> bool:
    """Treat a Linux zombie as terminated for process-leak assertions."""

    stat = Path(f"/proc/{pid}/stat")
    if stat.is_file():
        try:
            if stat.read_text(encoding="utf-8").split()[2] == "Z":
                return False
        except (OSError, IndexError):
            pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@pytest.mark.skipif(os.name != "posix", reason="process-group signal forwarding is POSIX-specific")
@pytest.mark.parametrize("terminating_signal", [signal.SIGINT, signal.SIGTERM])
def test_precision_wrapper_forwards_termination_to_nested_mace_group(
    tmp_path: Path,
    terminating_signal: signal.Signals,
) -> None:
    """Stopping the wrapper must not orphan its detached CUDA/MACE process tree."""

    child_pid_path = tmp_path / "child.pid"
    grandchild_pid_path = tmp_path / "grandchild.pid"
    artifact = tmp_path / "never-created.model"
    grandchild_code = (
        "import os,time; from pathlib import Path; "
        f"Path({str(grandchild_pid_path)!r}).write_text(str(os.getpid()), encoding='utf-8'); "
        "time.sleep(300)"
    )
    child_code = "\n".join(
        (
            "import os, subprocess, sys, time",
            "from pathlib import Path",
            f"Path({str(child_pid_path)!r}).write_text(str(os.getpid()), encoding='utf-8')",
            f"subprocess.Popen([sys.executable, '-c', {grandchild_code!r}])",
            "time.sleep(300)",
        )
    )
    source_root = Path(mdstats.__file__).resolve().parents[1]
    outer_code = "\n".join(
        (
            "from pathlib import Path",
            "from mdstats.training_data import critical_precision_cli as cli",
            f"cli._child_code = lambda module: {child_code!r}",
            f"cli._run_child_until_artifact('train', artifact=Path({str(artifact)!r}), validator=lambda path: False)",
        )
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(source_root)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )
    wrapper = subprocess.Popen(
        [sys.executable, "-c", outer_code],
        env=env,
        start_new_session=True,
    )
    child_pid = -1
    grandchild_pid = -1
    try:
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            if child_pid_path.is_file() and grandchild_pid_path.is_file():
                child_pid = int(child_pid_path.read_text(encoding="utf-8"))
                grandchild_pid = int(grandchild_pid_path.read_text(encoding="utf-8"))
                break
            time.sleep(0.05)
        assert child_pid > 0 and grandchild_pid > 0

        os.killpg(wrapper.pid, terminating_signal)
        wrapper.wait(timeout=10.0)

        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and (
            _pid_is_running(child_pid) or _pid_is_running(grandchild_pid)
        ):
            time.sleep(0.05)
        assert not _pid_is_running(child_pid)
        assert not _pid_is_running(grandchild_pid)
    finally:
        for pid in (grandchild_pid, child_pid):
            if pid > 0 and _pid_is_running(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        if wrapper.poll() is None:
            try:
                os.killpg(wrapper.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            wrapper.wait(timeout=5.0)
