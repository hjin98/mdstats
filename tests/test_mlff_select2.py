from __future__ import annotations

import mdstats

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64
D5 = "5" * 64
D6 = "6" * 64
D7 = "7" * 64
D8 = "8" * 64
D9 = "9" * 64
DA = "a" * 64
DB = "b" * 64
DC = "c" * 64


def _point(epoch: int, sha: str, score: float = 0.020) -> mdstats.Eval2TrajectoryPoint:
    return mdstats.Eval2TrajectoryPoint(
        epoch=epoch,
        checkpoint_sha256=sha,
        lightweight_target_score_ev_per_angstrom=score,
        normalized_schedule_progress=0.95,
        instantaneous_learning_rate=1.0e-5,
        phase="refinement",
        runtime_summary_digest=D1,
        stable_candidate_identity=f"epoch-{epoch}:{sha}",
    )


def _metrics(rmse: float, secondary: float, pred: str) -> mdstats.Eval2TargetMetricRecord:
    blocks = tuple(
        mdstats.Eval2TargetBlockMetric(
            block_id=f"block-{i:02d}",
            force_squared_error_sum=(rmse * rmse) * 30,
            force_component_count=30,
            configuration_count=1,
        )
        for i in range(12)
    )
    return mdstats.Eval2TargetMetricRecord(
        configuration_count=12,
        atom_count=120,
        energy_mae_ev_per_atom=0.001,
        relative_energy_rmse_ev_per_atom=0.0005,
        force_component_rmse_ev_per_angstrom=rmse,
        species_macro_force_rmse_ev_per_angstrom=secondary,
        species_force_rmse_ev_per_angstrom=(("Na", secondary),),
        force_error_p90_ev_per_angstrom=secondary,
        force_error_p95_ev_per_angstrom=secondary,
        force_error_p99_ev_per_angstrom=secondary,
        worst_stratum_force_rmse_ev_per_angstrom=secondary,
        stratum_force_rmse_ev_per_angstrom=(("species:Na", secondary),),
        stress_rmse_ev_per_angstrom3=None,
        block_metrics=blocks,
        target_role_digest=D2,
        prediction_digest=pred,
    )


def _checkpoint(seed: int, rmse: float, secondary: float, *, replay: float = 0.02) -> mdstats.Eval2CheckpointRecord:
    sha = f"{100 + seed:064x}"[-64:]
    return mdstats.assess_eval2_checkpoint(
        _point(29, sha, rmse),
        evaluation_record_digest=D3,
        target_metrics=_metrics(rmse, secondary, D4 if seed == 1 else D5),
        admissibility_policy=mdstats.CheckpointAdmissibilityPolicy(),
        replay_candidate_force_rmse_ev_per_angstrom=replay,
        replay_foundation_force_rmse_ev_per_angstrom=0.02,
        replay_label_mode="true_dft",
    )


def _candidate(seed: int, rmse: float, secondary: float, *, physical: bool = True, replay: float = 0.02) -> mdstats.Select2CandidateRecord:
    return mdstats.Select2CandidateRecord(
        run_plan_digest=D6 if seed == 1 else D7,
        run_id=f"final-seed-{seed}",
        optimizer_seed=seed,
        eval2_run_record_digest=D8 if seed == 1 else D9,
        selected_checkpoint=_checkpoint(seed, rmse, secondary, replay=replay),
        deploy_verify_run_digest=DA,
        pes_verify_run_digest=DB if physical else None,
        relax_verify_run_digest=DC if physical else None,
        dyn_verify_run_digest=D5 if physical else None,
        physical_qualified=physical,
        failure_reasons=() if physical else ("pes_qualification_failed", "relax_qualification_failed", "dynamics_qualification_failed"),
        target_only_model_path=f"/tmp/seed-{seed}.model",
        target_only_model_sha256=D1,
        mliap_artifact_path=f"/tmp/seed-{seed}.pt",
        mliap_artifact_sha256=D2,
    )


def _select(*candidates: mdstats.Select2CandidateRecord) -> mdstats.Select2SelectionRecord:
    return mdstats.build_select2_selection(
        campaign_plan_digest=D1,
        target_production_corpus_decision_digest=D2,
        dyn_verify_campaign_digest=D3,
        selection_policy=mdstats.CheckpointSelectionPolicy(),
        candidates=candidates,
    )


def test_select2_physical_gate_beats_better_static_rmse():
    broken_but_better = _candidate(1, 0.018, 0.018, physical=False)
    stable = _candidate(2, 0.022, 0.022, physical=True)
    result = _select(broken_but_better, stable)
    assert result.outcome == "selected"
    assert result.selected_candidate.optimizer_seed == 2
    assert result.qualified_order_run_plan_digests == (stable.run_plan_digest,)


def test_select2_replay_margin_has_zero_ranking_credit_after_admissibility():
    better_target_worse_replay = _candidate(1, 0.020, 0.020, replay=0.049)
    worse_target_better_replay = _candidate(2, 0.023, 0.023, replay=0.020)
    result = _select(better_target_worse_replay, worse_target_better_replay)
    assert result.selected_candidate.optimizer_seed == 1


def test_select2_practical_equivalence_uses_secondary_target_evidence():
    # 0.5 meV/A primary difference is inside the 1 meV/A equivalence band.
    slightly_better_primary = _candidate(1, 0.0200, 0.0300)
    much_better_tail = _candidate(2, 0.0205, 0.0190)
    result = _select(slightly_better_primary, much_better_tail)
    assert result.selected_candidate.optimizer_seed == 2


def test_select2_candidate_identity_includes_run_even_for_identical_checkpoint_bytes():
    first = _candidate(1, 0.020, 0.020)
    second = _candidate(2, 0.020, 0.020)
    # Force exact identical checkpoint evidence while retaining independent run lineage.
    second = mdstats.Select2CandidateRecord(
        run_plan_digest=second.run_plan_digest,
        run_id=second.run_id,
        optimizer_seed=second.optimizer_seed,
        eval2_run_record_digest=second.eval2_run_record_digest,
        selected_checkpoint=first.selected_checkpoint,
        deploy_verify_run_digest=second.deploy_verify_run_digest,
        pes_verify_run_digest=second.pes_verify_run_digest,
        relax_verify_run_digest=second.relax_verify_run_digest,
        dyn_verify_run_digest=second.dyn_verify_run_digest,
        physical_qualified=True,
        failure_reasons=(),
        target_only_model_path=second.target_only_model_path,
        target_only_model_sha256=second.target_only_model_sha256,
        mliap_artifact_path=second.mliap_artifact_path,
        mliap_artifact_sha256=second.mliap_artifact_sha256,
    )
    result = _select(first, second)
    assert result.outcome == "selected"
    assert len(result.qualified_order_run_plan_digests) == 2
    assert first.stable_candidate_identity != second.stable_candidate_identity


def test_select2_no_physical_candidate_fails_closed_and_roundtrips():
    result = _select(_candidate(1, 0.018, 0.018, physical=False), _candidate(2, 0.019, 0.019, physical=False))
    assert result.outcome == "no_physically_qualified_candidate"
    assert result.selected_candidate is None
    assert mdstats.Select2SelectionRecord.from_dict(result.to_dict()) == result


def test_select2_frozen_candidate_is_prelocked_test_authority_and_roundtrips():
    selected = _select(_candidate(1, 0.020, 0.020), _candidate(2, 0.024, 0.024)).selected_candidate
    assert selected is not None
    record = mdstats.Select2FrozenCandidateRecord(
        campaign_plan_digest=D1,
        selection_record_digest=D2,
        selected_candidate_digest=selected.content_digest,
        run_plan_digest=selected.run_plan_digest,
        run_id=selected.run_id,
        optimizer_seed=selected.optimizer_seed,
        checkpoint_sha256=selected.selected_checkpoint.trajectory_point.checkpoint_sha256,
        checkpoint_epoch=selected.selected_checkpoint.trajectory_point.epoch,
        target_model_path="/tmp/frozen.model",
        target_model_sha256=D3,
        mliap_artifact_path="/tmp/frozen.pt",
        mliap_artifact_sha256=D4,
        frozen_at_utc="2026-08-13T23:00:00Z",
    )
    assert mdstats.Select2FrozenCandidateRecord.from_dict(record.to_dict()) == record
    assert "locked" not in record.to_dict()
