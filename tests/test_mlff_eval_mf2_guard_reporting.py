from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

import mdstats
from mdstats.training_data import campaign_cli

QUALIFICATION = Path(__file__).resolve().parents[1] / "release" / "mlff_eval_mf2_exhaustive_30_checkpoint_qualification.json"


def _h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _metric(sha: str, primary: float, *, replay: float | None = None) -> mdstats.CheckpointMetricRecord:
    kwargs = {}
    if replay is not None:
        kwargs = {
            "replay_monitor_artifact_digest": _h("replay"),
            "replay_baseline_metric": 1.0,
            "replay_candidate_metric": 1.0 + replay,
            "replay_degradation_fraction": replay,
            "replay_label_mode": mdstats.ReplayLabelMode.TRUE_DFT,
        }
    return mdstats.CheckpointMetricRecord(
        run_plan_digest=_h("run"),
        checkpoint_sha256=sha,
        target_monitor_artifact_digest=_h("target"),
        energy_mae_ev_per_atom=primary,
        force_component_rmse_ev_per_angstrom=primary,
        target_combined_loss=primary,
        **kwargs,
    )


def _round(sha: str, primary: float, blocks: tuple[float, ...], *, replay: float | None = None):
    return SimpleNamespace(
        metric_record=_metric(sha, primary, replay=replay),
        target_primary_block_values=tuple((f"b{i}", value) for i, value in enumerate(blocks)),
    )


def test_mf2_paired_guard_retains_candidate_indistinguishable_from_cutoff() -> None:
    shas = tuple(_h(f"cp-{i}") for i in range(6))
    records = {
        shas[0]: _round(shas[0], 0.90, (0.90, 0.90, 0.90, 0.90)),
        shas[1]: _round(shas[1], 1.00, (1.00, 1.00, 1.00, 1.00)),
        # Aggregate metric is slightly worse than the nominal cutoff, but paired
        # block differences straddle zero and therefore remain ambiguous.
        shas[2]: _round(shas[2], 1.01, (1.03, 0.98, 1.02, 0.99)),
        shas[3]: _round(shas[3], 1.20, (1.20, 1.20, 1.20, 1.20)),
        shas[4]: _round(shas[4], 1.30, (1.30, 1.30, 1.30, 1.30)),
        shas[5]: _round(shas[5], 1.40, (1.40, 1.40, 1.40, 1.40)),
    }
    policy = mdstats.MultiFidelityEvaluationPolicy(
        survival_fraction=1 / 3,
        minimum_finalists=2,
        guard_standard_error_multiplier=2.0,
        guard_relative_margin=0.0,
        guard_minimum_blocks=4,
    )
    decision = mdstats.conservative_survivor_decision(
        shas,
        records,
        metric_policy=mdstats.CheckpointMetricPolicy(),
        policy=policy,
        next_round_is_final=False,
    )
    assert decision.nominal_keep_count == 2
    assert decision.retained_checkpoint_sha256s == shas[:3]
    assert decision.guard_retained_checkpoint_sha256s == (shas[2],)


def test_mf2_true_replay_reserve_prevents_target_only_elimination() -> None:
    shas = tuple(_h(f"rp-{i}") for i in range(6))
    records = {
        shas[0]: _round(shas[0], 0.80, (0.8, 0.8, 0.8, 0.8), replay=0.40),
        shas[1]: _round(shas[1], 0.90, (0.9, 0.9, 0.9, 0.9), replay=0.35),
        shas[2]: _round(shas[2], 1.00, (1.0, 1.0, 1.0, 1.0), replay=0.10),
        shas[3]: _round(shas[3], 1.10, (1.1, 1.1, 1.1, 1.1), replay=0.12),
        shas[4]: _round(shas[4], 1.20, (1.2, 1.2, 1.2, 1.2), replay=0.50),
        shas[5]: _round(shas[5], 1.30, (1.3, 1.3, 1.3, 1.3), replay=0.60),
    }
    policy = mdstats.MultiFidelityEvaluationPolicy(
        survival_fraction=1 / 3,
        minimum_finalists=2,
        guard_band_enabled=False,
    )
    decision = mdstats.conservative_survivor_decision(
        shas,
        records,
        metric_policy=mdstats.CheckpointMetricPolicy(maximum_replay_degradation_fraction=0.20),
        policy=policy,
        next_round_is_final=False,
        maximum_replay_degradation_fraction=0.20,
    )
    assert set(decision.retained_checkpoint_sha256s) == {shas[0], shas[1], shas[2], shas[3]}
    assert set(decision.replay_rescued_checkpoint_sha256s) == {shas[2], shas[3]}


def test_mf2_rank_instability_expands_next_round() -> None:
    shas = tuple(_h(f"inv-{i}") for i in range(8))
    records = {
        sha: _round(sha, 0.5 + 0.1 * i, (0.5 + 0.1 * i,) * 4)
        for i, sha in enumerate(shas)
    }
    policy = mdstats.MultiFidelityEvaluationPolicy(
        survival_fraction=0.25,
        minimum_finalists=2,
        guard_band_enabled=False,
        instability_inversion_fraction=0.20,
        instability_survival_fraction=0.50,
    )
    previous = tuple(reversed(shas))
    decision = mdstats.conservative_survivor_decision(
        shas,
        records,
        metric_policy=mdstats.CheckpointMetricPolicy(),
        policy=policy,
        next_round_is_final=False,
        previous_ranking_sha256s=previous,
    )
    assert decision.nominal_keep_count == 2
    assert decision.instability_expanded
    assert decision.inversion_fraction == pytest.approx(1.0)
    assert decision.retained_checkpoint_sha256s == shas[:4]


def test_mf2_remains_historical_while_new_configs_default_to_mlcv_nested_cv(tmp_path: Path) -> None:
    del tmp_path
    text = Path(campaign_cli.__file__).read_text(encoding="utf-8")
    assert 'checkpoint_strategy = "mlcv_nested_cv"' in text
    assert "finalist_count = 5" in text
    assert "finalist_rescue_batch_size = 5" in text
    # Historical EVAL-MF behavior remains directly qualified by the tests above
    # and by the public MultiFidelityEvaluationPolicy API; it is no longer the
    # generated production default after ADAPT-EVAL1.
    assert mdstats.MultiFidelityEvaluationPolicy().minimum_finalists >= 1
    example = (Path(campaign_cli.__file__).parents[2] / "campaign.toml.example").read_text(encoding="utf-8")
    assert 'checkpoint_strategy = "mlcv_nested_cv"' in example


def test_mf2_report_writes_all_epochs_and_round_metrics(tmp_path: Path) -> None:
    # Exercise report generation against durable round/survivor records without
    # requiring MACE inference; the report is a pure campaign-state projection.
    cfg_file = tmp_path / "campaign.toml"
    cfg_file.write_text("", encoding="utf-8")
    cfg = {"campaign": {"workspace": str(tmp_path / "workspace")}}
    paths = campaign_cli.CampaignPaths.from_config(cfg_file, cfg)
    paths.ensure()
    store = campaign_cli.CampaignStore(paths.state_db)
    metric_policy = mdstats.CheckpointMetricPolicy()
    run = mdstats.TrainingCampaignRunPlan(
        run_id="mf2-report",
        data8_bundle_digest=_h("d8"),
        mace_job_artifact_digest=_h("job"),
        job_id="job",
        kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
        fold_index=None,
        training_mode=mdstats.TrainingMode.NAIVE_FINE_TUNING,
        selection_size=1,
        seed=1,
        protocol_family_digest=_h("family"),
        protocol_variant_digest=_h("variant"),
        protocol_digest=_h("protocol"),
        checkpoint_metric_policy_digest=metric_policy.policy_digest,
        target_monitor_artifact_digest=_h("target-artifact"),
        replay_monitor_artifact_digest=None,
        relative_output_directory="run",
    )
    checkpoint_root = tmp_path / "checkpoints"
    checkpoint_root.mkdir()
    checkpoints = []
    for epoch in range(3):
        path = checkpoint_root / f"epoch-{epoch}.pt"
        path.write_bytes(f"cp-{epoch}".encode())
        checkpoints.append(
            mdstats.CheckpointFileRecord(
                run_plan_digest=run.content_digest,
                candidate_id=f"cp-{epoch}",
                epoch=epoch,
                relative_path=path.name,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                size_bytes=path.stat().st_size,
            )
        )
    catalog = mdstats.CandidateCheckpointCatalog(
        run_plan_digest=run.content_digest,
        root_directory=str(checkpoint_root),
        checkpoints=tuple(checkpoints),
        pattern="*.pt",
    )
    policy = mdstats.MultiFidelityEvaluationPolicy(round_fractions=(0.5, 1.0), minimum_finalists=1)
    evaluation_policy = mdstats.CheckpointEvaluationPolicy(condition_keys=())
    for checkpoint in checkpoints[:2]:
        metric = mdstats.CheckpointMetricRecord(
            run_plan_digest=run.content_digest,
            checkpoint_sha256=checkpoint.sha256,
            target_monitor_artifact_digest=run.target_monitor_artifact_digest,
            energy_mae_ev_per_atom=0.01,
            force_component_rmse_ev_per_angstrom=0.02 + 0.01 * checkpoint.epoch,
            target_combined_loss=0.03,
        )
        # Minimal full CheckpointEvaluationRecord accepted by the round record.
        evaluation = mdstats.CheckpointEvaluationRecord(
            run_plan_digest=run.content_digest,
            checkpoint_sha256=checkpoint.sha256,
            evaluation_policy_digest=evaluation_policy.policy_digest,
            target_monitor_artifact_digest=_h("target-eval-artifact"),
            target_monitor_sha256=_h("target-file"),
            replay_monitor_artifact_digest=None,
            replay_monitor_sha256=None,
            candidate_model_path=str(checkpoint_root / checkpoint.relative_path),
            candidate_model_sha256=checkpoint.sha256,
            replay_baseline_model_path=None,
            replay_baseline_model_sha256=None,
            target_configuration_count=1,
            replay_configuration_count=0,
            condition_force_rmse_ev_per_angstrom=(),
            metric_record=metric,
        )
        round_record = mdstats.MultiFidelityCheckpointRoundRecord(
            run_plan_digest=run.content_digest,
            checkpoint_sha256=checkpoint.sha256,
            round_index=0,
            round_fraction=0.5,
            target_ladder_digest=_h("ladder"),
            replay_ladder_digest=None,
            target_configuration_count=1,
            replay_configuration_count=0,
            evaluation_record=evaluation,
            full_fidelity=False,
            target_primary_block_values=(("b0", metric.force_component_rmse_ev_per_angstrom),),
        )
        store.put_record(
            f"multifidelity_round:{run.run_id}:{policy.policy_digest}:0:{checkpoint.sha256}",
            round_record,
        )
    store.put_record(
        f"multifidelity_survivors:{run.run_id}:{policy.policy_digest}:0",
        {
            "schema": "mdstats.mlff-multi-fidelity-survivors.v2",
            "ranking": [
                {
                    "checkpoint_sha256": checkpoints[0].sha256,
                    "outcome": "retained",
                    "reason_code": "multifidelity_round1_survivor",
                },
                {
                    "checkpoint_sha256": checkpoints[1].sha256,
                    "outcome": "screened_out",
                    "reason_code": "multifidelity_round1_screened_out",
                },
            ],
        },
    )
    json_path, csv_path, md_path = campaign_cli._write_multi_fidelity_epoch_report(
        paths=paths,
        store=store,
        run=run,
        original_catalog=catalog,
        policy=policy,
        evaluation_policy=evaluation_policy,
        metric_policy=metric_policy,
    )
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert [item["epoch"] for item in payload["epochs"]] == [0, 1, 2]
    assert payload["epochs"][0]["rounds"][0]["fraction"] == 0.5
    assert payload["epochs"][1]["outcome"] == "screened_out"
    assert csv_path.is_file()
    assert "Checkpoint evaluation history" in md_path.read_text(encoding="utf-8")
    store.close()


def test_mf2_representative_30_checkpoint_matches_exhaustive_with_cost_reduction(tmp_path: Path) -> None:
    """Representative EVAL-MF2 qualification against exhaustive 30-epoch selection.

    The synthetic history deliberately places the unconstrained target optimum in a
    true-replay-inadmissible region.  The multi-fidelity path must therefore preserve
    the best replay-admissible checkpoint while buying only nested incremental monitor
    coverage.  This is the deterministic exhaustive-comparison qualification case
    recorded in the 0.20.107a0 release evidence.
    """

    metric_policy = mdstats.CheckpointMetricPolicy(
        maximum_replay_degradation_fraction=0.20,
    )
    mf_policy = mdstats.MultiFidelityEvaluationPolicy()
    run = mdstats.TrainingCampaignRunPlan(
        run_id="mf2-exhaustive-30",
        data8_bundle_digest=_h("d8-mf2-exhaustive"),
        mace_job_artifact_digest=_h("job-mf2-exhaustive"),
        job_id="job-mf2-exhaustive",
        kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
        fold_index=None,
        training_mode=mdstats.TrainingMode.MULTIHEAD_REPLAY,
        selection_size=512,
        seed=1,
        protocol_family_digest=_h("family-mf2-exhaustive"),
        protocol_variant_digest=_h("variant-mf2-exhaustive"),
        protocol_digest=_h("protocol-mf2-exhaustive"),
        checkpoint_metric_policy_digest=metric_policy.policy_digest,
        target_monitor_artifact_digest=_h("target-mf2-exhaustive"),
        replay_monitor_artifact_digest=_h("replay-mf2-exhaustive"),
        relative_output_directory="mf2-exhaustive-30",
    )
    checkpoint_root = tmp_path / "checkpoints"
    checkpoint_root.mkdir()
    checkpoints = []
    for epoch in range(30):
        path = checkpoint_root / f"epoch-{epoch}.pt"
        path.write_bytes(f"mf2-checkpoint-{epoch}".encode())
        checkpoints.append(
            mdstats.CheckpointFileRecord(
                run_plan_digest=run.content_digest,
                candidate_id=f"epoch-{epoch}",
                epoch=epoch,
                relative_path=path.name,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                size_bytes=path.stat().st_size,
            )
        )
    catalog = mdstats.CandidateCheckpointCatalog(
        run_plan_digest=run.content_digest,
        root_directory=str(checkpoint_root),
        checkpoints=tuple(checkpoints),
        pattern="*.pt",
    )

    def metric(epoch: int, round_index: int) -> mdstats.CheckpointMetricRecord:
        # Full target optimum is epoch 14, but epochs <= 15 deliberately violate
        # the replay-retention threshold.  The exhaustive admissible winner is 16.
        target_full = 0.020 + 0.00012 * (epoch - 14) ** 2
        target_noise = (
            0.00045 * math.sin(1.7 * epoch)
            + 0.00018 * math.cos(0.37 * epoch),
            0.00018 * math.sin(1.3 * epoch)
            - 0.00008 * math.cos(0.51 * epoch),
            0.0,
        )[round_index]
        target = target_full + target_noise
        replay_full = 0.32 if epoch <= 15 else 0.10 + 0.003 * abs(epoch - 20)
        replay_noise = (
            0.025 * math.sin(0.9 * epoch),
            0.010 * math.cos(0.7 * epoch),
            0.0,
        )[round_index]
        replay = replay_full + replay_noise
        return mdstats.CheckpointMetricRecord(
            run_plan_digest=run.content_digest,
            checkpoint_sha256=checkpoints[epoch].sha256,
            target_monitor_artifact_digest=run.target_monitor_artifact_digest,
            energy_mae_ev_per_atom=target,
            force_component_rmse_ev_per_angstrom=target,
            target_combined_loss=target,
            replay_monitor_artifact_digest=run.replay_monitor_artifact_digest,
            replay_baseline_metric=1.0,
            replay_candidate_metric=1.0 + replay,
            replay_degradation_fraction=replay,
            replay_label_mode=mdstats.ReplayLabelMode.TRUE_DFT,
        )

    full_metrics = tuple(metric(epoch, 2) for epoch in range(30))
    exhaustive = mdstats.select_checkpoint(run, catalog, full_metrics, metric_policy)
    assert exhaustive.selected_checkpoint_epoch == 16

    surviving_epochs = list(range(30))
    previous_ranking: tuple[str, ...] = ()
    previous_fraction = 0.0
    full_checkpoint_equivalents = 0.0
    round_candidate_counts: list[int] = []
    for round_index, fraction in enumerate(mf_policy.round_fractions):
        round_candidate_counts.append(len(surviving_epochs))
        full_checkpoint_equivalents += len(surviving_epochs) * (fraction - previous_fraction)
        records = {}
        for epoch in surviving_epochs:
            round_metric = metric(epoch, round_index)
            blocks = tuple(
                (
                    f"source-block-{block}",
                    round_metric.force_component_rmse_ev_per_angstrom
                    + 0.00015 * math.sin(block * 1.1 + epoch * 0.2),
                )
                for block in range(8)
            )
            records[checkpoints[epoch].sha256] = SimpleNamespace(
                metric_record=round_metric,
                target_primary_block_values=blocks,
            )
        ranked_epochs = sorted(
            surviving_epochs,
            key=lambda epoch: mdstats.provisional_ranking_key(
                records[checkpoints[epoch].sha256].metric_record,
                epoch,
                checkpoints[epoch].sha256,
                metric_policy,
            ),
        )
        if fraction == 1.0:
            finalist_catalog = mdstats.CandidateCheckpointCatalog(
                run_plan_digest=run.content_digest,
                root_directory=str(checkpoint_root),
                checkpoints=tuple(checkpoints[epoch] for epoch in ranked_epochs),
                pattern="*.pt",
            )
            finalist_metrics = tuple(metric(epoch, 2) for epoch in ranked_epochs)
            staged = mdstats.select_checkpoint(run, finalist_catalog, finalist_metrics, metric_policy)
            break
        decision = mdstats.conservative_survivor_decision(
            tuple(checkpoints[epoch].sha256 for epoch in ranked_epochs),
            records,
            metric_policy=metric_policy,
            policy=mf_policy,
            next_round_is_final=(round_index + 1 == len(mf_policy.round_fractions) - 1),
            previous_ranking_sha256s=previous_ranking,
            maximum_replay_degradation_fraction=metric_policy.maximum_replay_degradation_fraction,
        )
        retained = set(decision.retained_checkpoint_sha256s)
        previous_ranking = tuple(checkpoints[epoch].sha256 for epoch in ranked_epochs)
        surviving_epochs = [epoch for epoch in ranked_epochs if checkpoints[epoch].sha256 in retained]
        previous_fraction = fraction

    assert staged.selected_checkpoint_epoch == exhaustive.selected_checkpoint_epoch == 16
    assert round_candidate_counts == [30, 11, 8]
    assert full_checkpoint_equivalents == pytest.approx(10.89)
    assert full_checkpoint_equivalents / 30.0 == pytest.approx(0.363)
    assert 1.0 - full_checkpoint_equivalents / 30.0 == pytest.approx(0.637)


def test_mf2_release_qualification_evidence_is_explicit_and_bounded() -> None:
    payload = json.loads(QUALIFICATION.read_text(encoding="utf-8"))
    assert payload["schema"] == "mdstats.mlff-eval-mf2-exhaustive-qualification.v1"
    assert payload["runtime_version"] == "0.20.107a0"
    assert payload["architecture_revision"] == 26
    assert payload["evidence_class"] == "synthetic_representative_exhaustive_comparison"
    assert payload["target_and_replay_use_same_fraction"] is True
    assert payload["winner_agreement"] is True
    assert payload["round_candidate_counts"] == [30, 11, 8]
    assert payload["candidate_inference_full_checkpoint_equivalents"] == pytest.approx(10.89)
    assert payload["candidate_inference_reduction_fraction"] == pytest.approx(0.637)
    assert payload["real_mace_qualification"]["mace_version"] == "0.3.16"
    assert "synthetic" in payload["real_mace_qualification"]["note"].lower()
