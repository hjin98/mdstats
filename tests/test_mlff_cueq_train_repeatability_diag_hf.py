from __future__ import annotations

from pathlib import Path
import numpy as np

import mdstats
from mdstats.training_data import acceleration, campaign_cli


class _FakeCalc:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0


def _payload(*, force_delta: float = 0.0, descriptor_delta: float = 0.0) -> dict[str, object]:
    return {
        "energy": np.asarray([0.0, 0.25], dtype=np.float64),
        "forces": np.asarray([0.0, 0.25, -0.5, 0.75, 1.0, -1.25], dtype=np.float64) + force_delta,
        "stress": np.asarray([0.0, 0.1, -0.2, 0.3, 0.4, -0.5], dtype=np.float64),
        "descriptors": np.asarray([[0.0, 0.0], [1.0, 1.0]], dtype=np.float64) + descriptor_delta,
        "atom_count": 2,
    }


def test_repeatability_diagnostic_separates_self_and_cross_noise(monkeypatch) -> None:
    reference = _FakeCalc("e3nn")
    candidate = _FakeCalc("cueq")
    # First value is the explicit discarded warm-up.
    ref_noise = [8.0e-6, 0.0, 1.0e-7, -2.0e-7, 0.5e-7]
    cueq_cross = [7.0e-6, 1.1e-5, 2.9e-5, 0.8e-5, 1.4e-5]

    def fake_evaluate(calc, structures):
        run = calc.calls
        calc.calls += 1
        if calc.name == "e3nn":
            return _payload(force_delta=ref_noise[run], descriptor_delta=run * 1.0e-10)
        return _payload(force_delta=cueq_cross[run], descriptor_delta=run * 1.0e-10)

    monkeypatch.setattr(acceleration, "_evaluate_acceleration_calculator", fake_evaluate)
    record = acceleration.diagnose_mace_acceleration_repeatability(
        reference,
        candidate,
        [object(), object()],
        dtype="float32",
        policy=campaign_cli._training_acceleration_parity_policy(),
        repeat_count=4,
        force_threshold=1.0e-5,
    )
    assert record.repeat_count == 4
    assert record.comparison_mode == "all_pairs"
    assert record.warmup_count == 1
    assert record.self_pair_count == 6
    assert record.cross_pair_count == 16
    assert len(record.e3nn_self_force_max_abs) == 6
    assert len(record.cueq_self_force_max_abs) == 6
    assert len(record.cross_force_max_abs) == 16
    assert max(record.e3nn_self_force_max_abs) < 3.1e-7
    assert max(record.cueq_self_force_max_abs) > 1.0e-5
    assert len(record.e3nn_self_force_p99_abs) == 6
    assert len(record.e3nn_self_force_p999_abs) == 6
    assert len(record.cueq_self_force_p99_abs) == 6
    assert len(record.cueq_self_force_p999_abs) == 6
    assert len(record.e3nn_self_force_above_threshold_count) == 6
    assert len(record.cueq_self_force_above_threshold_count) == 6
    assert len(record.e3nn_self_energy_max_abs) == 6
    assert len(record.cueq_self_energy_max_abs) == 6
    assert record.self_detail_available
    assert max(record.cross_force_max_abs) > 2.0e-5
    assert max(record.cross_force_above_threshold_count) == record.cross_force_component_count
    assert all(record.cross_selection_identical)
    assert record.summaries["cross_force_max_abs"]["max"] == max(record.cross_force_max_abs)
    assert mdstats.TrainingAccelerationRepeatabilityDiagnostic.from_dict(record.to_dict()) == record


def test_repeatability_diagnostic_prints_reportable_statistics(capsys) -> None:
    record = mdstats.TrainingAccelerationRepeatabilityDiagnostic(
        repeat_count=3,
        dtype="float32",
        structure_count=2,
        atom_count=4,
        force_threshold=1.0e-5,
        e3nn_self_force_max_abs=(1.0e-7, 2.0e-7),
        e3nn_self_force_rmse=(5.0e-8, 1.0e-7),
        cueq_self_force_max_abs=(1.2e-5, 2.5e-5),
        cueq_self_force_rmse=(2.0e-6, 3.0e-6),
        cross_energy_max_abs=(2.0e-7, 2.2e-7, 2.1e-7),
        cross_energy_rmse=(1.0e-7, 1.1e-7, 1.0e-7),
        cross_force_max_abs=(1.1e-5, 2.9e-5, 1.4e-5),
        cross_force_rmse=(1.0e-6, 2.0e-6, 1.5e-6),
        cross_force_p99_abs=(3.0e-6, 5.0e-6, 4.0e-6),
        cross_force_p999_abs=(8.0e-6, 1.5e-5, 9.0e-6),
        cross_force_above_threshold_count=(1, 4, 2),
        cross_force_component_count=1000,
        cross_stress_max_abs=(2.0e-7, 2.1e-7, 1.9e-7),
        cross_stress_rmse=(1.0e-7, 1.0e-7, 1.0e-7),
        cross_descriptor_max_abs=(2.0e-7, 2.0e-7, 2.0e-7),
        cross_descriptor_rmse=(1.0e-7, 1.0e-7, 1.0e-7),
        cross_selection_identical=(True, True, True),
        policy_digest=campaign_cli._training_acceleration_parity_policy().policy_digest,
        torch_deterministic_algorithms=False,
        torch_deterministic_debug_mode=0,
        cudnn_deterministic=False,
        cublas_workspace_config=None,
    )
    campaign_cli._print_training_repeatability_diagnostic(record)
    text = capsys.readouterr().out
    assert "[DIAG] TRAIN2 FP32 repeatability" in text
    assert "cross 01/03" in text
    assert "Fmax=1.100e-05" in text
    assert "Frmse=1.000e-06" in text
    assert "Fp99=" in text
    assert "Fp99.9=" in text
    assert "F>1.0e-05=1/1000" in text
    assert "e3nn-self Fmax" in text
    assert "e3nn-self Frmse" in text
    assert "CuEq-self Fmax" in text
    assert "CuEq-self Frmse" in text
    assert "selection_identical=3/3" in text


def test_repeatability_diagnostic_persists_in_campaign_store(tmp_path) -> None:
    record = mdstats.TrainingAccelerationRepeatabilityDiagnostic(
        repeat_count=2, dtype="float32", structure_count=1, atom_count=1, force_threshold=1.0e-5,
        e3nn_self_force_max_abs=(1.0e-7,), e3nn_self_force_rmse=(1.0e-7,),
        cueq_self_force_max_abs=(2.0e-5,), cueq_self_force_rmse=(2.0e-6,),
        cross_energy_max_abs=(1.0e-7, 1.1e-7), cross_energy_rmse=(1.0e-7, 1.0e-7),
        cross_force_max_abs=(1.0e-5, 2.0e-5), cross_force_rmse=(1.0e-6, 2.0e-6),
        cross_force_p99_abs=(9.0e-6, 1.8e-5), cross_force_p999_abs=(9.9e-6, 1.98e-5),
        cross_force_above_threshold_count=(0, 1), cross_force_component_count=3,
        cross_stress_max_abs=(1.0e-7, 1.1e-7), cross_stress_rmse=(1.0e-7, 1.0e-7),
        cross_descriptor_max_abs=(1.0e-7, 1.1e-7), cross_descriptor_rmse=(1.0e-7, 1.0e-7),
        cross_selection_identical=(True, True),
        policy_digest=campaign_cli._training_acceleration_parity_policy().policy_digest,
    )
    store = campaign_cli.CampaignStore(tmp_path / "state.sqlite3")
    store.put_record("training_acceleration_repeatability_diagnostic", record)
    loaded = store.get_record(
        "training_acceleration_repeatability_diagnostic",
        mdstats.TrainingAccelerationRepeatabilityDiagnostic,
    )
    assert loaded == record


def test_repeatability_diagnostic_prints_refined_self_tail_statistics(capsys) -> None:
    record = mdstats.TrainingAccelerationRepeatabilityDiagnostic(
        repeat_count=3, dtype="float32", structure_count=2, atom_count=4, force_threshold=1.0e-5,
        e3nn_self_force_max_abs=(1.2e-5, 2.1e-5), e3nn_self_force_rmse=(2.0e-6, 3.0e-6),
        cueq_self_force_max_abs=(1.1e-5, 2.0e-5), cueq_self_force_rmse=(2.1e-6, 3.1e-6),
        cross_energy_max_abs=(1e-7, 1e-7, 1e-7), cross_energy_rmse=(1e-7, 1e-7, 1e-7),
        cross_force_max_abs=(1.0e-5, 1.1e-5, 1.2e-5), cross_force_rmse=(2e-6, 2e-6, 2e-6),
        cross_force_p99_abs=(8e-6, 9e-6, 1e-5), cross_force_p999_abs=(9e-6, 1e-5, 1.1e-5),
        cross_force_above_threshold_count=(0, 1, 2), cross_force_component_count=90,
        cross_stress_max_abs=(1e-7, 1e-7, 1e-7), cross_stress_rmse=(1e-7, 1e-7, 1e-7),
        cross_descriptor_max_abs=(1e-7, 1e-7, 1e-7), cross_descriptor_rmse=(1e-7, 1e-7, 1e-7),
        cross_selection_identical=(True, True, True),
        policy_digest=campaign_cli._training_acceleration_parity_policy().policy_digest,
        e3nn_self_force_p99_abs=(8e-6, 1.1e-5), e3nn_self_force_p999_abs=(1.0e-5, 2.0e-5),
        e3nn_self_force_above_threshold_count=(1, 3),
        cueq_self_force_p99_abs=(7e-6, 1.0e-5), cueq_self_force_p999_abs=(9e-6, 1.9e-5),
        cueq_self_force_above_threshold_count=(0, 2),
    )
    campaign_cli._print_training_repeatability_diagnostic(record)
    text = capsys.readouterr().out
    assert "e3nn-self Fp99:" in text
    assert "e3nn-self Fp99.9:" in text
    assert "e3nn-self F>1.0e-05:" in text
    assert "CuEq-self Fp99:" in text
    assert "CuEq-self Fp99.9:" in text
    assert "CuEq-self F>1.0e-05:" in text




def test_deterministic_control_parent_uses_fresh_worker(monkeypatch, tmp_path) -> None:
    try:
        from ase import Atoms
    except Exception:
        import pytest
        pytest.skip("ASE unavailable")

    model = tmp_path / "model.model"
    model.write_bytes(b"model")
    nested = mdstats.TrainingAccelerationRepeatabilityDiagnostic(
        repeat_count=2, dtype="float32", structure_count=1, atom_count=1, force_threshold=1.0e-5,
        e3nn_self_force_max_abs=(0.0,), e3nn_self_force_rmse=(0.0,),
        cueq_self_force_max_abs=(0.0,), cueq_self_force_rmse=(0.0,),
        cross_energy_max_abs=(0.0, 0.0), cross_energy_rmse=(0.0, 0.0),
        cross_force_max_abs=(0.0, 0.0), cross_force_rmse=(0.0, 0.0),
        cross_force_p99_abs=(0.0, 0.0), cross_force_p999_abs=(0.0, 0.0),
        cross_force_above_threshold_count=(0, 0), cross_force_component_count=3,
        cross_stress_max_abs=(0.0, 0.0), cross_stress_rmse=(0.0, 0.0),
        cross_descriptor_max_abs=(0.0, 0.0), cross_descriptor_rmse=(0.0, 0.0),
        cross_selection_identical=(True, True),
        policy_digest=campaign_cli._training_acceleration_parity_policy().policy_digest,
        torch_deterministic_algorithms=True, torch_deterministic_debug_mode=2,
        cudnn_deterministic=True, cublas_workspace_config=":4096:8",
        e3nn_self_force_p99_abs=(0.0,), e3nn_self_force_p999_abs=(0.0,),
        e3nn_self_force_above_threshold_count=(0,),
        cueq_self_force_p99_abs=(0.0,), cueq_self_force_p999_abs=(0.0,),
        cueq_self_force_above_threshold_count=(0,),
    )

    class _Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, *, env, capture_output, text, timeout, check):
        output = command[command.index("--output") + 1]
        Path(output).write_text(
            __import__("json").dumps({"status": "completed", "repeatability": nested.to_dict()}),
            encoding="utf-8",
        )
        assert env["CUBLAS_WORKSPACE_CONFIG"] == ":4096:8"
        assert command[0] == __import__("sys").executable
        return _Completed()

    monkeypatch.setattr(acceleration.subprocess, "run", fake_run)
    record = acceleration.diagnose_training_acceleration_deterministic_control(
        training_model_path=model, training_head="default",
        structures=[Atoms("H", positions=[[0.0, 0.0, 0.0]])],
        device="cuda", dtype="float32",
        parity_policy=campaign_cli._training_acceleration_parity_policy(),
        repeat_count=2,
    )
    assert record.status == "completed"
    assert record.repeatability == nested
