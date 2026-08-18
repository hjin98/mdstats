from __future__ import annotations

import mdstats
from mdstats.training_data import campaign_cli


def _diag(*, cross_frmse=3.975e-6, cross_fp99=1.735e-5, cross_fp999=2.032e-5, cross_fmax=2.261e-5, stable=5.602e-7, self_fmax=2.337e-5):
    self_n=45
    cross_n=100
    stable_policy=campaign_cli._training_acceleration_parity_policy()
    return mdstats.TrainingAccelerationRepeatabilityDiagnostic(
        repeat_count=10, warmup_count=1, comparison_mode="all_pairs", dtype="float32",
        structure_count=3, atom_count=30, force_threshold=1.0e-5,
        e3nn_self_force_max_abs=(self_fmax,)*self_n, e3nn_self_force_rmse=(3.690e-6,)*self_n,
        cueq_self_force_max_abs=(1.734e-5,)*self_n, cueq_self_force_rmse=(2.988e-6,)*self_n,
        e3nn_self_force_p99_abs=(1.701e-5,)*self_n, e3nn_self_force_p999_abs=(2.262e-5,)*self_n,
        cueq_self_force_p99_abs=(1.341e-5,)*self_n, cueq_self_force_p999_abs=(1.627e-5,)*self_n,
        e3nn_self_force_above_threshold_count=(4,)*self_n, cueq_self_force_above_threshold_count=(2,)*self_n,
        e3nn_self_energy_max_abs=(2.623e-7,)*self_n, e3nn_self_stress_max_abs=(4.415e-7,)*self_n,
        e3nn_self_descriptor_max_abs=(1.218e-7,)*self_n, cueq_self_energy_max_abs=(2.623e-7,)*self_n,
        cueq_self_stress_max_abs=(6.103e-7,)*self_n, cueq_self_descriptor_max_abs=(1.382e-7,)*self_n,
        e3nn_self_selection_identical=(True,)*self_n, cueq_self_selection_identical=(True,)*self_n,
        cross_energy_max_abs=(3.099e-7,)*cross_n, cross_energy_rmse=(1e-7,)*cross_n,
        cross_force_max_abs=(cross_fmax,)*cross_n, cross_force_rmse=(cross_frmse,)*cross_n,
        cross_force_p99_abs=(cross_fp99,)*cross_n, cross_force_p999_abs=(cross_fp999,)*cross_n,
        cross_force_above_threshold_count=(4,)*cross_n, cross_force_component_count=90,
        cross_stress_max_abs=(stable,)*cross_n, cross_stress_rmse=(1e-7,)*cross_n,
        cross_descriptor_max_abs=(2.936e-7,)*cross_n, cross_descriptor_rmse=(1e-7,)*cross_n,
        cross_selection_identical=(True,)*cross_n, policy_digest=stable_policy.policy_digest,
    )


def test_mpa0_diag3_evidence_passes_permanent_noise_normalized_gate():
    policy=campaign_cli._training_acceleration_noise_normalized_policy()
    record=mdstats.build_training_noise_normalized_parity_record(_diag(), policy=policy)
    assert record.passed
    assert record.selection_identical
    assert record.force_rmse_ratio is not None and record.force_rmse_ratio < 1.10
    assert record.force_p99_ratio is not None and record.force_p99_ratio < 1.03
    assert record.force_p999_ratio is not None and record.force_p999_ratio < 0.91
    assert record.force_max_cross < record.force_max_limit
    restored=mdstats.TrainingAccelerationNoiseNormalizedParityRecord.from_dict(record.to_dict())
    assert restored.content_digest == record.content_digest


def test_noise_normalized_gate_rejects_distribution_ratio_above_1p25():
    record=mdstats.build_training_noise_normalized_parity_record(_diag(cross_frmse=5.0e-6))
    assert not record.passed
    assert any("Frmse" in item for item in record.failure_reasons)


def test_noise_normalized_gate_keeps_absolute_catastrophic_fmax_guard():
    record=mdstats.build_training_noise_normalized_parity_record(_diag(cross_fmax=2.0e-4, self_fmax=1.0e-3))
    assert not record.passed
    assert record.force_max_limit == 1.0e-4
    assert any(item.startswith("Fmax=") for item in record.failure_reasons)


def test_training_realization_uses_noise_normalized_record_for_fp32(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from mdstats.training_data import acceleration
    import mace.calculators

    checkpoint=tmp_path/'model.model'
    checkpoint.write_bytes(b'noise-normalized-test-model')
    monkeypatch.setattr(mace.calculators, 'MACECalculator', lambda **kwargs: object())
    evidence=_diag()
    monkeypatch.setattr(acceleration, 'diagnose_mace_acceleration_repeatability', lambda *args, **kwargs: evidence)
    probe=SimpleNamespace(cueq_available=True, mace_version='0.3.16', cueq_versions=(('cuequivariance','test'),))
    realization, parity=acceleration.qualify_training_acceleration_realization(
        backend='cueq', training_model_path=checkpoint, training_head='default', structures=[object()],
        device='cuda', dtype='float32', probe=probe,
        parity_policy=campaign_cli._training_acceleration_parity_policy(),
        noise_normalized_policy=campaign_cli._training_acceleration_noise_normalized_policy(),
    )
    assert isinstance(parity, mdstats.TrainingAccelerationNoiseNormalizedParityRecord)
    assert parity.passed
    assert realization.qualified
    assert realization.training_parity_record_digest == parity.content_digest
