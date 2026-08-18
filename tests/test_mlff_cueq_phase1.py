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


def _trajectory(runtime_digest: str, mode: str, *, role: str = "short", epoch_budget: int = 8, update_budget: int = 80, suffix: str = "a") -> mdstats.CueqPhase1TrajectoryRecord:
    return mdstats.CueqPhase1TrajectoryRecord(
        role=role, training_kernel_mode=mode, runtime_record_digest=runtime_digest,
        source_foundation_digest="0" * 64, starting_checkpoint_sha256="1" * 64,
        selected_head_qualification_digest="2" * 64, data8_bundle_digest="3" * 64,
        optimizer_semantics_digest="4" * 64, split_identity_digest="5" * 64,
        order_identity_digest="6" * 64, objective_policy_digest="7" * 64,
        lr_schedule_digest="8" * 64, stopping_policy_digest="9" * 64,
        replay_policy_digest="a" * 64, validation_protocol_digest="b" * 64,
        evaluation_protocol_digest="c" * 64, seed=7, dtype="float32",
        epoch_budget=epoch_budget, update_budget=update_budget,
        completed_epochs=epoch_budget, gradient_updates=update_budget,
        target_validation_metric_name="force_rmse_mev_per_a", target_validation_metric=21.0 if mode == "e3nn" else 21.3,
        replay_validation_metric_name="force_rmse_mev_per_a", replay_validation_metric=18.0 if mode == "e3nn" else 18.2,
        replay_retention_passed=True, losses_finite=True, gradients_finite=True, parameters_finite=True,
        checkpoint_admissible=True, checkpoint_ranking_digest="d" * 64,
        target_head_extraction_passed=True, target_head_sha256=suffix * 64,
        eval2_passed=True, eval2_decision_digest="e" * 64,
        physical_verification_state="not_available", wall_time_seconds=100.0 if mode == "e3nn" else 60.0,
        updates_per_second=0.8 if mode == "e3nn" else 1.333,
        peak_vram_bytes=8 * 1024**3, reserved_vram_bytes=10 * 1024**3,
        representative_full_trajectory=(role == "full"),
    )


def test_phase1_policy_freezes_training_only_split_and_short_window() -> None:
    policy = mdstats.CueqPhase1Policy()
    assert policy.source_inference_kernel_mode == "e3nn"
    assert policy.reference_training_kernel_mode == "e3nn"
    assert policy.candidate_training_kernel_mode == "cueq_pure"
    assert 5 <= policy.short_epoch_budget <= 10
    with pytest.raises(mdstats.TrainingDataInputError, match=r"\[5, 10\]"):
        mdstats.CueqPhase1Policy(short_epoch_budget=4)
    with pytest.raises(mdstats.TrainingDataInputError, match="source inference"):
        mdstats.CueqPhase1Policy(source_inference_kernel_mode="cueq_pure")


def test_phase1_pair_accepts_nonidentical_weights_but_requires_same_protocol_and_decisions() -> None:
    runtime = _runtime()
    policy = mdstats.CueqPhase1Policy()
    ref = _trajectory(runtime.content_digest, "e3nn", suffix="1")
    cueq = _trajectory(runtime.content_digest, "cueq_pure", suffix="2")
    pair = mdstats.CueqPhase1PairedAssessment(policy, ref, cueq)
    assert pair.passed
    assert pair.target_metric_delta == pytest.approx(0.3)
    assert pair.replay_metric_delta == pytest.approx(0.2)
    assert pair.speedup == pytest.approx(100.0 / 60.0)
    assert ref.target_head_sha256 != cueq.target_head_sha256
    assert mdstats.CueqPhase1PairedAssessment.from_dict(pair.to_dict()) == pair

    mismatched = replace(cueq, data8_bundle_digest="f" * 64)
    bad = mdstats.CueqPhase1PairedAssessment(policy, ref, mismatched)
    assert not bad.passed
    assert "common_protocol_identity" in bad.blocking_reasons


def test_phase1_pair_fails_closed_on_replay_or_eval_decision_change() -> None:
    runtime = _runtime()
    policy = mdstats.CueqPhase1Policy()
    ref = _trajectory(runtime.content_digest, "e3nn")
    cueq = replace(_trajectory(runtime.content_digest, "cueq_pure"), replay_retention_passed=False, eval2_passed=False)
    pair = mdstats.CueqPhase1PairedAssessment(policy, ref, cueq)
    assert not pair.passed
    assert "hard_decision_disagreement:replay_retention" in pair.blocking_reasons
    assert "hard_decision_disagreement:eval2" in pair.blocking_reasons
    assert "replay_retention_pass" in pair.blocking_reasons
    assert "eval2_pass" in pair.blocking_reasons


def test_phase1_gate_requires_positive_runtime_short_then_representative_full_pair() -> None:
    runtime = _runtime()
    policy = mdstats.CueqPhase1Policy(short_epoch_budget=8)
    short = mdstats.CueqPhase1PairedAssessment(
        policy, _trajectory(runtime.content_digest, "e3nn"), _trajectory(runtime.content_digest, "cueq_pure", suffix="2")
    )
    full = mdstats.CueqPhase1PairedAssessment(
        policy,
        _trajectory(runtime.content_digest, "e3nn", role="full", epoch_budget=30, update_budget=300),
        _trajectory(runtime.content_digest, "cueq_pure", role="full", epoch_budget=30, update_budget=300, suffix="2"),
    )
    deferred = mdstats.build_cueq_phase1_qualification(runtime=runtime, short_pairs=(short,), policy=policy)
    assert not deferred.passed
    assert "representative_full_pair_missing" in deferred.blocking_reasons

    qualified = mdstats.build_cueq_phase1_qualification(runtime=runtime, short_pairs=(short,), full_pairs=(full,), policy=policy)
    assert qualified.passed
    assert qualified.phase_separated_training_authorized
    assert not qualified.source_cueq_execution_authorized
    assert not qualified.generated_default_change_authorized
    assert mdstats.CueqPhase1QualificationRecord.from_dict(qualified.to_dict()) == qualified


def test_phase1_negative_runtime_stays_deferred_and_never_falls_back() -> None:
    runtime = mdstats.capture_cueq_dep1_runtime()
    record = mdstats.build_cueq_phase1_qualification(runtime=runtime)
    assert record.cueq_dep1_passed == runtime.passed
    assert not record.passed
    assert "short_paired_adaptation_missing" in record.blocking_reasons
    assert "representative_full_pair_missing" in record.blocking_reasons
    assert record.policy.candidate_training_kernel_mode == "cueq_pure"
    if not runtime.passed:
        assert "CUEQ_DEP1_RUNTIME_FREEZE" in record.blocking_reasons


def test_phase1_trajectory_tamper_is_detected() -> None:
    runtime = _runtime()
    payload = _trajectory(runtime.content_digest, "e3nn").to_dict()
    payload["seed"] = 99
    with pytest.raises(mdstats.TrainingDataSerializationError, match="protocol digest mismatch"):
        mdstats.CueqPhase1TrajectoryRecord.from_dict(payload)
