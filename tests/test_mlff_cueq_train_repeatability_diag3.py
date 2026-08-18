from __future__ import annotations

import numpy as np

from mdstats.training_data import acceleration, campaign_cli


class _FakeCalc:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0


def _payload(delta: float, descriptor_delta: float = 0.0) -> dict[str, object]:
    return {
        "energy": np.asarray([0.0, 0.25], dtype=np.float64) + delta * 0.01,
        "forces": np.asarray([0.0, 0.25, -0.5, 0.75, 1.0, -1.25], dtype=np.float64) + delta,
        "stress": np.asarray([0.0, 0.1, -0.2, 0.3, 0.4, -0.5], dtype=np.float64) + delta * 0.02,
        "descriptors": np.asarray([[0.0, 0.0], [1.0, 1.0]], dtype=np.float64) + descriptor_delta,
        "atom_count": 2,
    }


def test_diag3_discards_warmup_and_uses_all_pairs(monkeypatch) -> None:
    e3nn = _FakeCalc("e3nn")
    cueq = _FakeCalc("cueq")
    # A deliberately huge first-call perturbation must be absent from evidence.
    e3nn_values = [1.0e-2, 0.0, 1.0e-7, 2.0e-7, 3.0e-7]
    cueq_values = [-1.0e-2, 1.0e-5, 1.1e-5, 1.2e-5, 1.3e-5]

    def fake_evaluate(calc, structures):
        i = calc.calls
        calc.calls += 1
        values = e3nn_values if calc.name == "e3nn" else cueq_values
        return _payload(values[i], descriptor_delta=i * 1.0e-12)

    monkeypatch.setattr(acceleration, "_evaluate_acceleration_calculator", fake_evaluate)
    record = acceleration.diagnose_mace_acceleration_repeatability(
        e3nn, cueq, [object()], dtype="float32",
        policy=campaign_cli._training_acceleration_parity_policy(), repeat_count=4,
    )
    assert e3nn.calls == 5 and cueq.calls == 5
    assert record.warmup_count == 1
    assert record.comparison_mode == "all_pairs"
    assert record.self_pair_count == 6
    assert record.cross_pair_count == 16
    assert len(record.e3nn_self_force_max_abs) == 6
    assert len(record.cueq_self_force_max_abs) == 6
    assert len(record.cross_force_max_abs) == 16
    assert max(record.e3nn_self_force_max_abs) < 4.0e-7
    assert max(record.cueq_self_force_max_abs) < 4.0e-6
    assert max(record.cross_force_max_abs) < 2.0e-5
    assert all(record.e3nn_self_selection_identical)
    assert all(record.cueq_self_selection_identical)
    assert all(record.cross_selection_identical)
    assert acceleration.TrainingAccelerationRepeatabilityDiagnostic.from_dict(record.to_dict()) == record


def test_diag3_prints_compact_all_pairs_statistics(monkeypatch, capsys) -> None:
    e3nn = _FakeCalc("e3nn")
    cueq = _FakeCalc("cueq")

    def fake_evaluate(calc, structures):
        i = calc.calls
        calc.calls += 1
        base = 1.0e-7 * i if calc.name == "e3nn" else 1.0e-5 + 2.0e-7 * i
        return _payload(base, descriptor_delta=i * 1.0e-12)

    monkeypatch.setattr(acceleration, "_evaluate_acceleration_calculator", fake_evaluate)
    record = acceleration.diagnose_mace_acceleration_repeatability(
        e3nn, cueq, [object()], dtype="float32", repeat_count=4,
        policy=campaign_cli._training_acceleration_parity_policy(),
    )
    campaign_cli._print_training_repeatability_diagnostic(record)
    text = capsys.readouterr().out
    assert "warmups=1, mode=all_pairs" in text
    assert "comparison counts: e3nn-self=6, CuEq-self=6, cross=16" in text
    assert "p99=" in text
    assert "e3nn-self Emax" in text
    assert "CuEq-self Smax" in text
    assert "cross Dmax" in text
    assert "cross selection_identical=16/16" in text
    # All-pairs mode is compact; it does not dump every cross pair.
    assert "cross 01/" not in text
