from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

import mdstats
from mdstats.training_data import campaign_cli


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _candidate(rank: int, score: float, *, admissible: bool = True):
    return mdstats.FullEvaluationCandidateRecord(
        finalist_rank=rank,
        finalist_batch_index=1,
        run_plan_digest=_sha(f"run-{rank}"),
        run_id=f"run-{rank}",
        checkpoint_sha256=_sha(f"checkpoint-{rank}"),
        checkpoint_epoch=rank,
        evaluation_record_digest=_sha(f"eval-{rank}"),
        target_force_rmse_ev_per_angstrom=score,
        replay_force_rmse_ev_per_angstrom=score,
        full_score_ev_per_angstrom=score,
        admissible=admissible,
        rejection_reasons=() if admissible else ("target_force_rmse_threshold_exceeded",),
        replay_foundation_force_rmse_ev_per_angstrom=0.02,
        replay_absolute_degradation_ev_per_angstrom=score - 0.02,
        replay_fractional_degradation=(score - 0.02) / 0.02,
    )


def _full_eval(*candidates):
    return mdstats.AdaptiveFullEvaluationRecord(
        campaign_plan_digest=_sha("campaign"),
        policy_digest=_sha("eval-policy"),
        finalist_queue_digest=_sha("queue"),
        full_target_artifact_digest=_sha("target-domain"),
        full_replay_artifact_digest=_sha("replay-domain"),
        evaluated_candidates=tuple(candidates),
        completed_batch_count=1,
        outcome="admissible_candidates_available",
    )


def test_verify_order_uses_full_score_and_fallback_policy():
    record = _full_eval(_candidate(1, 0.028), _candidate(2, 0.024), _candidate(3, 0.026))
    ordered = mdstats.ordered_admissible_candidates(record)
    assert [item.finalist_rank for item in ordered] == [2, 3, 1]
    assert [item.finalist_rank for item in mdstats.ordered_admissible_candidates(
        record, fallback_to_next_admissible_candidate=False
    )] == [2]


def test_verification_reasons_are_hard_gates():
    good = {
        "finite": True,
        "absolute_energy_drift_ev_per_atom_per_ps": 0.010,
        "minimum_pair_distance_angstrom": 1.2,
        "maximum_force_ev_per_angstrom": 5.0,
    }
    assert mdstats.verification_rejection_reasons(
        [good],
        maximum_energy_drift_ev_per_atom_per_ps=0.026,
        minimum_pair_distance_angstrom=0.8,
        maximum_force_ev_per_angstrom=100.0,
    ) == ()
    bad = dict(good)
    bad.update(
        finite=False,
        absolute_energy_drift_ev_per_atom_per_ps=0.030,
        minimum_pair_distance_angstrom=0.7,
        maximum_force_ev_per_angstrom=101.0,
    )
    assert mdstats.verification_rejection_reasons(
        [bad],
        maximum_energy_drift_ev_per_atom_per_ps=0.026,
        minimum_pair_distance_angstrom=0.8,
        maximum_force_ev_per_angstrom=100.0,
    ) == (
        "energy_drift_threshold_exceeded",
        "maximum_force_threshold_exceeded",
        "minimum_pair_distance_threshold_violated",
        "nonfinite_nve_observable",
    )


def _attempt(rank: int, passed: bool):
    return mdstats.AdaptiveVerificationCandidateRecord(
        adaptive_full_evaluation_digest=_sha("full-eval"),
        verification_policy_digest=_sha("verify-policy"),
        full_evaluation_candidate_digest=_sha(f"full-candidate-{rank}"),
        finalist_rank=rank,
        finalist_batch_index=1,
        run_plan_digest=_sha(f"run-{rank}"),
        run_id=f"run-{rank}",
        checkpoint_sha256=_sha(f"checkpoint-{rank}"),
        checkpoint_epoch=rank,
        full_score_ev_per_angstrom=0.020 + rank / 1000,
        target_force_rmse_ev_per_angstrom=0.020,
        replay_force_rmse_ev_per_angstrom=0.021,
        candidate_model_sha256=_sha(f"model-{rank}"),
        model_inference_dtype="float32",
        scientific_analysis_dtype="float64",
        verification_case_digests=(_sha(f"case-{rank}"),),
        passed=passed,
        rejection_reasons=() if passed else ("energy_drift_threshold_exceeded",),
    )


def test_verification_record_stops_at_first_passing_candidate():
    failed = _attempt(1, False)
    passed = _attempt(2, True)
    record = mdstats.AdaptiveVerificationRecord(
        campaign_plan_digest=_sha("campaign"),
        adaptive_full_evaluation_digest=_sha("full-eval"),
        verification_policy_digest=_sha("verify-policy"),
        attempts=(failed, passed),
        outcome="verified_candidate_selected",
        selected_attempt_digest=passed.content_digest,
    )
    assert record.selected_attempt == passed
    assert mdstats.AdaptiveVerificationRecord.from_dict(record.to_dict()) == record
    passed_first = _attempt(1, True)
    failed_second = _attempt(2, False)
    with pytest.raises(Exception, match="stop immediately"):
        mdstats.AdaptiveVerificationRecord(
            campaign_plan_digest=_sha("campaign"),
            adaptive_full_evaluation_digest=_sha("full-eval"),
            verification_policy_digest=_sha("verify-policy"),
            attempts=(passed_first, failed_second),
            outcome="verified_candidate_selected",
            selected_attempt_digest=passed_first.content_digest,
        )


def test_binary_model_dtype_and_fp64_analysis_are_frozen_in_policy():
    single = mdstats.AdaptiveVerificationPolicy(model_inference_dtype="float32")
    double = mdstats.AdaptiveVerificationPolicy(model_inference_dtype="float64")
    assert single.model_inference_dtype == "float32"
    assert double.model_inference_dtype == "float64"
    assert single.scientific_analysis_dtype == double.scientific_analysis_dtype == "float64"
    with pytest.raises(Exception, match="float64"):
        mdstats.AdaptiveVerificationPolicy(
            model_inference_dtype="float32", scientific_analysis_dtype="float32"
        )


def test_adaptive_verify_routes_before_legacy_committee_lookup(monkeypatch, tmp_path: Path):
    cfg = {"evaluation": {"checkpoint_strategy": "adaptive_topk"}}
    paths = SimpleNamespace(state_db=tmp_path / "state.sqlite")
    fake_store = object()
    monkeypatch.setattr(campaign_cli, "_load_config", lambda _: (cfg, paths))
    monkeypatch.setattr(campaign_cli, "_binary_model_precision_contract", lambda _: {"model_dtype": "float32"})
    monkeypatch.setattr(campaign_cli, "CampaignStore", lambda _: fake_store)
    monkeypatch.setattr(campaign_cli, "_effective_stage", lambda *_: (campaign_cli.StageState.COMPLETE, "complete"))
    called = {}
    def fake_adaptive(args, **kwargs):
        called.update(kwargs)
        return 17
    monkeypatch.setattr(campaign_cli, "_command_verify_adaptive_topk", fake_adaptive)
    result = campaign_cli.command_verify(argparse.Namespace(config="campaign.toml"))
    assert result == 17
    assert called["store"] is fake_store
    assert called["model_dtype"] == "float32"


def test_generated_config_enables_score_ordered_verification_fallback():
    text = campaign_cli._config_template(
        workspace="workspace",
        training_root="training",
        foundation_model="foundation.model",
        replay_train="replay_train.xyz",
        replay_monitor="replay_monitor.xyz",
    )
    assert 'checkpoint_strategy = "mlcv_nested_cv"' in text
    assert "fallback_to_next_full_evaluation_candidate = true" in text


def test_atomic_publication_copies_exact_bytes(tmp_path: Path):
    source = tmp_path / "candidate.model"
    destination = tmp_path / "models" / "selected.model"
    source.write_bytes(b"verified-model")
    campaign_cli._atomic_copy_file(source, destination)
    assert destination.read_bytes() == b"verified-model"


def test_deployment_and_adaptive_freeze_preserve_verified_model_bytes(tmp_path: Path):
    failed = _attempt(1, False)
    passed = _attempt(2, True)
    verification = mdstats.AdaptiveVerificationRecord(
        campaign_plan_digest=_sha("campaign"),
        adaptive_full_evaluation_digest=_sha("full-eval"),
        verification_policy_digest=_sha("verify-policy"),
        attempts=(failed, passed),
        outcome="verified_candidate_selected",
        selected_attempt_digest=passed.content_digest,
    )
    model = tmp_path / "selected.model"
    model.write_bytes(b"model")
    model_sha = hashlib.sha256(model.read_bytes()).hexdigest()
    deployment = mdstats.AdaptiveDeploymentModelRecord(
        campaign_plan_digest=_sha("campaign"),
        adaptive_full_evaluation_digest=_sha("full-eval"),
        adaptive_verification_digest=verification.content_digest,
        selected_full_evaluation_candidate_digest=passed.full_evaluation_candidate_digest,
        selected_verification_attempt_digest=passed.content_digest,
        run_plan_digest=passed.run_plan_digest,
        run_id=passed.run_id,
        checkpoint_sha256=passed.checkpoint_sha256,
        checkpoint_epoch=passed.checkpoint_epoch,
        target_head_name="target_head",
        model_inference_dtype="float32",
        scientific_analysis_dtype="float64",
        exported_model_path=str(model),
        exported_model_sha256=model_sha,
        byte_size=model.stat().st_size,
    )
    restored = mdstats.AdaptiveDeploymentModelRecord.from_dict(deployment.to_dict())
    assert restored == deployment
    freeze = mdstats.AdaptiveProtocolFreezeRecord(
        production_qualification_digest=_sha("qualification"),
        campaign_plan_digest=_sha("campaign"),
        adaptive_full_evaluation_digest=_sha("full-eval"),
        adaptive_verification_digest=verification.content_digest,
        adaptive_deployment_model_digest=deployment.content_digest,
        selected_full_evaluation_candidate_digest=passed.full_evaluation_candidate_digest,
        full_target_artifact_digest=_sha("target-domain"),
        full_replay_artifact_digest=_sha("replay-domain"),
        exported_model_sha256=model_sha,
        model_inference_dtype="float32",
        scientific_analysis_dtype="float64",
        frozen_at_utc="2026-08-09T22:00:00+00:00",
    )
    assert mdstats.AdaptiveProtocolFreezeRecord.from_dict(freeze.to_dict()) == freeze


def test_adaptive_verify_falls_back_and_publishes_only_first_passer(monkeypatch, tmp_path: Path):
    from types import SimpleNamespace
    from tests.test_mlff_adapt_eval1_topk_full_evaluation import _evaluation
    from mdstats.training_data import campaign_execution

    class Store:
        def __init__(self):
            self.records = {}
        def get_record_optional(self, key, cls):
            return self.records.get(key)
        def get_record(self, key, cls):
            return self.records[key]
        def get_payload_optional(self, key):
            value = self.records.get(key)
            if value is None:
                return None
            return value if isinstance(value, dict) else value.to_dict()
        def get_payload(self, key):
            value = self.records[key]
            return value if isinstance(value, dict) else value.to_dict()
        def has_record(self, key):
            return key in self.records
        def put_record(self, key, value):
            self.records[key] = value
        def put_records(self, values):
            self.records.update(values)
        def delete_record(self, key):
            self.records.pop(key, None)

    workspace = tmp_path / "workspace"
    paths = SimpleNamespace(
        config_dir=tmp_path,
        workspace=workspace,
        state_db=workspace / ".mdstats" / "state.sqlite",
        internal=workspace / ".mdstats",
        runs=workspace / "runs",
        models=workspace / "models",
        results=workspace / "results",
    )
    for path in (paths.internal, paths.runs, paths.models, paths.results):
        path.mkdir(parents=True, exist_ok=True)
    structure = tmp_path / "verify.xyz"
    structure.write_text("structure", encoding="utf-8")

    stop_policy = mdstats.AdaptiveTrainingStopPolicy(
        target_head_name="target_head", replay_head_name="replay_monitor"
    )
    runs = []
    jobs = {}
    executions = {}
    finalists = []
    full_evals = {}
    for rank, score in ((1, 0.020), (2, 0.021)):
        run_digest = _sha(f"integration-run-{rank}")
        run_id = f"run-{rank}"
        checkpoint_path = tmp_path / f"checkpoint-{rank}.pt"
        checkpoint_path.write_bytes(f"model-{rank}".encode())
        checkpoint_sha = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
        checkpoint = mdstats.CheckpointFileRecord(
            run_plan_digest=run_digest,
            candidate_id=f"{run_id}:epoch:{rank}",
            epoch=rank,
            relative_path=checkpoint_path.name,
            sha256=checkpoint_sha,
            size_bytes=checkpoint_path.stat().st_size,
        )
        catalog = mdstats.CandidateCheckpointCatalog(
            run_plan_digest=run_digest,
            root_directory=str(tmp_path),
            checkpoints=(checkpoint,),
            pattern="*.pt",
        )
        run = SimpleNamespace(
            content_digest=run_digest,
            run_id=run_id,
            mace_job_artifact_digest=_sha(f"job-{rank}"),
        )
        runs.append(run)
        job_root = tmp_path / f"job-root-{rank}"
        job_root.mkdir()
        (job_root / "config.yaml").write_text("config", encoding="utf-8")
        job = SimpleNamespace(
            protocol=SimpleNamespace(adaptive_stop_policy=stop_policy),
            relative_directory=".",
            config_relative_path="config.yaml",
        )
        jobs[run.mace_job_artifact_digest] = (SimpleNamespace(), job, job_root)
        executions[run_digest] = SimpleNamespace(checkpoint_catalog=catalog)
        finalist = mdstats.CampaignFinalistCandidate(
            rank=rank,
            batch_index=1,
            run_plan_digest=run_digest,
            run_id=run_id,
            champion_record_digest=_sha(f"champ-{rank}"),
            checkpoint_sha256=checkpoint_sha,
            checkpoint_epoch=rank,
            lightweight_score_ev_per_angstrom=score,
        )
        full_eval = _evaluation(finalist, score, score)
        candidate = mdstats.FullEvaluationCandidateRecord(
            finalist_rank=rank,
            finalist_batch_index=1,
            run_plan_digest=run_digest,
            run_id=run_id,
            checkpoint_sha256=checkpoint_sha,
            checkpoint_epoch=rank,
            evaluation_record_digest=full_eval.content_digest,
            target_force_rmse_ev_per_angstrom=score,
            replay_force_rmse_ev_per_angstrom=score,
            full_score_ev_per_angstrom=score,
            admissible=True,
            replay_foundation_force_rmse_ev_per_angstrom=0.015,
            replay_absolute_degradation_ev_per_angstrom=score - 0.015,
            replay_fractional_degradation=(score - 0.015) / 0.015,
        )
        finalists.append(candidate)
        full_evals[(run_id, checkpoint_sha)] = full_eval

    campaign = SimpleNamespace(content_digest=_sha("integration-campaign"), runs=tuple(runs))
    full_record = mdstats.AdaptiveFullEvaluationRecord(
        campaign_plan_digest=campaign.content_digest,
        policy_digest=_sha("integration-full-policy"),
        finalist_queue_digest=_sha("integration-queue"),
        full_target_artifact_digest=_sha("integration-target"),
        full_replay_artifact_digest=_sha("integration-replay"),
        evaluated_candidates=tuple(finalists),
        completed_batch_count=1,
        outcome="admissible_candidates_available",
    )
    store = Store()
    store.records["adaptive_full_evaluation"] = full_record
    store.records["training_campaign"] = campaign
    store.records["production_qualification"] = SimpleNamespace(content_digest=_sha("qualification"))
    for (run_id, checkpoint_sha), value in full_evals.items():
        store.records[f"adaptive_full_evaluation:{run_id}:{checkpoint_sha}"] = value

    cfg = {
        "evaluation": {"checkpoint_strategy": "adaptive_topk"},
        "verification": {
            "structures": [str(structure)],
            "temperatures_kelvin": [300.0],
            "steps": 10,
            "timestep_fs": 0.5,
            "sample_interval_steps": 5,
            "velocity_seed": 7,
            "fallback_to_next_full_evaluation_candidate": True,
        },
    }
    fake_full_policy = SimpleNamespace(
        policy_digest=full_record.policy_digest,
        to_dict=lambda: {"policy_digest": full_record.policy_digest},
    )
    monkeypatch.setattr(campaign_cli, "_adaptive_full_evaluation_policy", lambda *a, **k: fake_full_policy)
    monkeypatch.setattr(campaign_cli, "_checkpoint_metric_policy", lambda cfg: object())
    monkeypatch.setattr(campaign_cli, "_current_data8_entries", lambda store: ())
    monkeypatch.setattr(campaign_cli, "_job_lookup", lambda entries: jobs)
    monkeypatch.setattr(campaign_cli, "_available_successful_executions", lambda *a, **k: executions)
    monkeypatch.setattr(campaign_cli, "_evaluation_checkpoint_catalog", lambda store, run_id, execution: execution.checkpoint_catalog)
    monkeypatch.setattr(campaign_cli, "_checkpoint_source_for_evaluation", lambda paths, store, run_id, checkpoint, catalog: (Path(catalog.root_directory) / checkpoint.relative_path, None))
    monkeypatch.setattr(campaign_cli, "_load_verification_structure_templates", lambda paths: {str(path): object() for path in paths})
    monkeypatch.setattr(campaign_cli, "_ensure_local_wrappers", lambda paths: {"mdstats-mace-train": tmp_path / "train", "mdstats-mace-select-head": tmp_path / "head"})
    fake_accel = SimpleNamespace(policy_digest=_sha("accel"), to_dict=lambda: {"backend": "test"})
    fake_critical = SimpleNamespace(policy_digest=_sha("critical"))
    monkeypatch.setattr(campaign_cli, "_acceleration_policy", lambda cfg: fake_accel)
    monkeypatch.setattr(campaign_cli, "_critical_precision_policy", lambda cfg: fake_critical)
    monkeypatch.setattr(campaign_cli, "_print_precision_profile", lambda cfg: {"model_dtype": "float32"})
    monkeypatch.setattr(campaign_cli, "_campaign_cleanup", lambda *a, **k: SimpleNamespace())
    monkeypatch.setattr(campaign_cli, "_print_cleanup_report", lambda *a, **k: None)
    monkeypatch.setattr(campaign_cli, "_update_benchmark", lambda *a, **k: None)
    monkeypatch.setattr(campaign_cli, "_mark_stage", lambda *a, **k: None)
    monkeypatch.setattr(campaign_cli, "_ok", lambda *a, **k: None)
    monkeypatch.setattr(campaign_cli, "_fail", lambda *a, **k: None)
    monkeypatch.setattr(campaign_cli, "_print_header", lambda *a, **k: None)
    monkeypatch.setattr(mdstats, "materialize_mace_checkpoint_model", lambda checkpoint, source, **kwargs: source)
    monkeypatch.setattr(mdstats, "remove_materialized_mace_checkpoint_model", lambda path: None)

    def fake_export(source, output, **kwargs):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(Path(source).read_bytes())
    monkeypatch.setattr(campaign_execution, "_export_target_head_model_with_dtype", fake_export)

    def fake_nve(model_path, *args, **kwargs):
        is_first = Path(model_path).read_bytes() == b"model-1"
        return {
            "finite": True,
            "absolute_energy_drift_ev_per_atom_per_ps": 0.030 if is_first else 0.010,
            "minimum_pair_distance_angstrom": 1.0,
            "maximum_force_ev_per_angstrom": 5.0,
            "model": str(model_path),
            "structure": str(structure),
            "temperature_kelvin": 300.0,
        }
    monkeypatch.setattr(campaign_cli, "_nve_verify", fake_nve)

    def run_tasks(tasks, **kwargs):
        result = {}
        for task in tasks:
            value = task.execute()
            result[task.key] = value
            if task.on_success is not None:
                task.on_success(value)
        return result
    monkeypatch.setattr(campaign_cli, "_run_adaptive_inference_tasks", run_tasks)

    rc = campaign_cli._command_verify_adaptive_topk(
        argparse.Namespace(structure=None, steps=None),
        cfg=cfg,
        paths=paths,
        store=store,
        model_dtype="float32",
    )
    assert rc == 0
    record = store.records["adaptive_verification"]
    assert [attempt.passed for attempt in record.attempts] == [False, True]
    deployment = store.records["adaptive_deployment_model"]
    assert deployment.run_id == "run-2"
    assert deployment.checkpoint_epoch == 2
    assert deployment.model_inference_dtype == "float32"
    assert deployment.scientific_analysis_dtype == "float64"
    published_models = list(paths.models.glob("*.model"))
    assert len(published_models) == 1
    assert published_models[0].read_bytes() == b"model-2"
    assert not any((paths.internal / "verification-candidates").rglob("*.model"))
