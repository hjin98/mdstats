from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import mdstats
import pytest
from mdstats.training_data import campaign_cli
from mdstats.training_data import _campaign_cli_core as campaign_core
from mdstats.training_data import production_materialization
from mdstats.training_data.target_size_study import FIXED_TARGET_SIZES


_RETIRED_ENSURE_NAMES = (
    "_ensure_size_halve2_plan",
    "_ensure_size_fidelity2_execution_plan",
    "_ensure_target_multi_view_migration",
    "_resolve_active_target_data_ladder",
    "_ensure_target_production_corpus_decision",
    "_load_verified_target_size_convergence_authority",
)


def test_v5_fixed_universe_and_public_authority_are_unique() -> None:
    assert FIXED_TARGET_SIZES == (128, 256, 512, 1024, 2048, 4096, 8192, 16384)
    assert mdstats.TargetSizeStudyPolicy().candidate_sizes == FIXED_TARGET_SIZES
    assert mdstats.TargetMultiViewQualificationPolicyV2().candidate_sizes == FIXED_TARGET_SIZES
    for retired in (
        "TargetDataLadderPlan",
        "TargetSizeConvergencePlan",
        "SizeHalve2Plan",
        "SizeFidelity2ExecutionPlan",
        "TargetMultiViewMigrationPlan",
        "TargetProductionCorpusDecision",
        "TargetMultiViewSelectorPolicy",
        "TargetMultiViewSelectionPlan",
        "build_target_multi_view_selection_plan",
        "TargetMultiViewRepairPolicy",
        "TargetMultiViewRepairPlan",
        "build_target_multi_view_repair_plan",
    ):
        assert not hasattr(mdstats, retired), retired


def test_prepare_runtime_is_direct_repair2_mvqual2_target_size_study() -> None:
    source = inspect.getsource(campaign_cli._prepare_materialization)
    ordered = (
        "_ensure_target_multi_view_selection_v2(",
        "_ensure_target_multi_view_repair_v2(",
        "_ensure_target_multi_view_qualification_v2(",
        "_ensure_target_size_study(",
    )
    positions = [source.index(token) for token in ordered]
    assert positions == sorted(positions)
    for retired in _RETIRED_ENSURE_NAMES:
        assert retired not in source
        assert not hasattr(campaign_cli, retired)
    assert "No rescue sizes are permitted" in source
    assert "rescue above 16384 is forbidden" in source


def test_prepare_receipt_hard_cuts_retired_derived_authorities() -> None:
    keys = set(campaign_cli._PREPARE_RECEIPT_RECORD_KEYS)
    assert {
        "target_coverage_feasibility",
        "target_coverage_sparse_index",
        "target_multi_view_selection_v2",
        "target_multi_view_repair_v2",
        "target_multi_view_qualification_v2",
        "target_size_study",
    } <= keys
    assert not keys.intersection(
        {
            "target_data_ladder",
            "target_size_convergence",
            "target_multi_view_migration",
            "size_halve2",
            "size_fidelity2",
            "target_production_corpus_decision",
        }
    )


def test_target_size_funnel_finishes_before_held_out_cv() -> None:
    eval_source = inspect.getsource(campaign_cli._command_evaluate_train2)
    role_source = inspect.getsource(campaign_cli._eval2_target_role_for_run)
    assert "attach_epoch_3_outcomes" in eval_source
    assert "attach_epoch_10_outcomes" in eval_source
    assert "attach_epoch_30_outcomes" in eval_source
    assert "target-size selection frozen" in eval_source
    assert "Target data size selected and frozen: n={updated.selected_target_size}" in eval_source
    assert 'for stage_name in ("prepare", "preflight", "train", "evaluate")' in eval_source
    assert "Held-out CV EVAL2 is blocked until selected_target_size is frozen" in role_source
    for retired_mutator in ("with_stage_b0_evidence", "with_stage_b_evidence", "with_stage_c_evidence"):
        assert retired_mutator not in eval_source
        assert retired_mutator not in role_source


def test_held_out_cv_runtime_is_rejected_before_target_size_freeze(monkeypatch) -> None:
    monkeypatch.setattr(campaign_core, "_eval2_label_domain_id", lambda *_args, **_kwargs: "d0")
    run = SimpleNamespace(
        kind=mdstats.MaceJobKind.CROSS_VALIDATION_FOLD,
        fold_index=0,
    )
    study = SimpleNamespace(outcome=mdstats.OUTCOME_AWAITING_EPOCH_3)
    with pytest.raises(campaign_core.CampaignCliError, match="blocked until selected_target_size is frozen"):
        campaign_core._eval2_target_role_for_run(
            store=object(),
            target_size_study=study,
            repair2=object(),
            role_freeze=object(),
            bundle=object(),
            run=run,
        )


def test_screening_materialization_uses_exact_stage_sizes_and_ordered_seed_set(monkeypatch) -> None:
    method = SimpleNamespace(mode="multihead", fold_partition_seed=17)
    monkeypatch.setattr(campaign_core, "_training_method_specs", lambda _cfg: (method,))
    study = SimpleNamespace(
        outcome=mdstats.OUTCOME_AWAITING_EPOCH_10,
        next_training_sizes=(512, 2048),
        policy=SimpleNamespace(screening_optimizer_seeds=(7, 11)),
    )
    variants = campaign_core._target_size_materialization_variants({}, study=study)
    assert [(item.selection_size, item.seed) for item in variants] == [
        (512, 7),
        (512, 11),
        (2048, 7),
        (2048, 11),
    ]
    assert all(item.cross_validation_folds == 0 for item in variants)


def test_post_selection_verification_cannot_advance_target_size() -> None:
    functions = (
        campaign_cli._command_verify_train2_deploy,
        campaign_cli._command_verify_train2_pes,
        campaign_cli._command_verify_train2_relax,
        campaign_cli._command_verify_train2_dyn,
        campaign_cli._finalize_train2_dyn,
    )
    source = "\n".join(inspect.getsource(fn) for fn in functions)
    assert "_load_verified_target_size_study_authority" in source
    assert "attach_epoch_" not in source
    assert "with_stage_" not in source
    assert "target_production_corpus" not in source


def test_candidate_and_selected_prefix_materializations_are_distinct_contracts() -> None:
    source = inspect.getsource(production_materialization.ProductionMaterializationPlan.__post_init__)
    assert '"target_size_candidate"' in source
    assert '"selected_production_prefix"' in source
    assert "Only target_size_candidate materializations may bind the pre-selection development evaluation cohort" in source
    data7_source = inspect.getsource(__import__(
        "mdstats.training_data.data7_bundle", fromlist=["build_data7_preparation_bundle"]
    ).build_data7_preparation_bundle)
    assert "prescribed_selection_frame_uids" in data7_source
    assert "no second ranking is performed" in data7_source


def test_generated_config_exposes_no_retired_target_size_rescue_controls() -> None:
    template = campaign_cli._config_template(
        workspace="workspace",
        training_root="training",
        foundation_model="foundation.model",
        replay_train="replay_train.xyz",
        replay_monitor="replay_monitor.xyz",
        acceleration_backend="e3nn",
    )
    for retired in (
        "coverage_rescue_activated",
        "coverage_rescue_candidate_sizes",
        "coverage_rescue_min_qualifiers",
        "size_halve2",
        "size_fidelity2",
        "mvmigrate1",
        "target_data_ladder",
    ):
        assert retired not in template.lower()


def test_prepare_contract_signature_is_v5_only_and_current_upstreams_are_reusable() -> None:
    signature = campaign_cli._prepare_contract_signature()
    assert signature["prepare_contract_version"] == "target-size-v5.2026-08.v1"
    assert {
        "target_data2c_mvidx1_version",
        "target_data2c_mvsel2_version",
        "target_data2c_repair2_version",
        "target_data2c_mvqual2_version",
        "target_size_study_version",
    } <= set(signature)
    for retired_key in (
        "target_data2c_mvsel1_version",
        "target_data2c_repair1_version",
        "target_data2c_mvqual1_version",
        "target_data2c_ladder_version",
        "target_data2c_mvmigrate1_version",
        "target_data2c_migrated_ladder_version",
        "target_data2d_migrated_convergence_version",
        "target_data2e_migrated_production_version",
    ):
        assert retired_key not in signature

    # Selective restart reuse is owned by each authenticated current upstream
    # authority rather than by a migration bridge. Runtime installers wrap some
    # helpers, so inspect the owning source file rather than mutated callables.
    core_source = Path(campaign_core.__file__).read_text(encoding="utf-8")
    for helper_name in (
        "_ensure_target_coverage_feasibility",
        "_ensure_target_coverage_sparse_index",
        "_ensure_target_multi_view_selection_v2",
        "_ensure_target_multi_view_repair_v2",
        "_ensure_target_multi_view_qualification_v2",
        "_ensure_target_size_study",
    ):
        start = core_source.index(f"def {helper_name}(")
        next_def = core_source.find("\ndef ", start + 1)
        helper_source = core_source[start:] if next_def < 0 else core_source[start:next_def]
        assert "get_record_optional" in helper_source
        assert "reused" in helper_source
    start = core_source.index("def _try_reuse_completed_prepare(")
    next_def = core_source.find("\ndef ", start + 1)
    reuse_source = core_source[start:] if next_def < 0 else core_source[start:next_def]
    assert 'if not store.has_record("prepare_restart_receipt"):' in reuse_source
    assert "return False" in reuse_source
    assert "0.20.68a0" not in reuse_source


def test_scientific_candidate_failure_only_relaxes_scheduler_stop_during_active_v5_study() -> None:
    failure_attempt = SimpleNamespace(
        scientific_failure_code="train_nonfinite_model_state",
        scientific_failure_evidence_digest="a" * 64,
    )
    ordinary_attempt = SimpleNamespace(
        scientific_failure_code=None, scientific_failure_evidence_digest=None
    )
    failed_scientific = SimpleNamespace(
        state=mdstats.TrainingRunState.FAILED, attempts=(failure_attempt,)
    )
    failed_ordinary = SimpleNamespace(
        state=mdstats.TrainingRunState.FAILED, attempts=(ordinary_attempt,)
    )
    active = SimpleNamespace(outcome=mdstats.OUTCOME_AWAITING_EPOCH_3)
    selected = SimpleNamespace(outcome=mdstats.OUTCOME_SELECTED)

    assert campaign_core._is_target_size_scientific_execution_failure(
        failed_scientific, policy_family="train2", target_size_study=active
    )
    assert not campaign_core._is_target_size_scientific_execution_failure(
        failed_ordinary, policy_family="train2", target_size_study=active
    )
    assert not campaign_core._is_target_size_scientific_execution_failure(
        failed_scientific, policy_family="train2", target_size_study=selected
    )
    assert not campaign_core._is_target_size_scientific_execution_failure(
        failed_scientific, policy_family="legacy", target_size_study=active
    )


def _direct_digest(label: str) -> str:
    import hashlib
    return hashlib.sha256(label.encode()).hexdigest()


class _DirectRepairDomain:
    label_domain_id = "direct-domain"
    repaired_master_order = tuple(
        _direct_digest(f"direct-frame-{index}") for index in range(16384)
    )


class _DirectRepair:
    dataset_id = "direct-dataset"
    domains = (_DirectRepairDomain(),)
    content_digest = _direct_digest("direct-repair")

    def domain(self, label_domain_id: str):
        assert label_domain_id == self.domains[0].label_domain_id
        return self.domains[0]


class _DirectStore:
    def __init__(self, records):
        self.records = records

    def get_record_optional(self, key, _record_type):
        return self.records.get(key)


def _direct_study():
    repair = _DirectRepair()
    qualified = (2048, 4096, 8192, 16384)
    qualification = SimpleNamespace(
        dataset_id=repair.dataset_id,
        target_multi_view_repair_digest=repair.content_digest,
        content_digest=_direct_digest("direct-mvqual2"),
        mv_qualified_sizes=qualified,
    )
    policy = mdstats.TargetSizeStudyPolicy(screening_optimizer_seeds=(7, 11))
    return repair, mdstats.build_target_size_study(repair, qualification, policy=policy)


def _direct_protocol(tag: str):
    del tag
    policy = lambda name: SimpleNamespace(policy_digest=_direct_digest(f"direct-{name}"))
    return SimpleNamespace(
        training_budget_policy=policy("budget"),
        learning_rate_schedule_policy=policy("schedule"),
        checkpoint_admissibility_policy=policy("admissibility"),
        checkpoint_selection_policy=policy("selection"),
        checkpoint_control_policy=SimpleNamespace(target_head_name="target"),
        foundation_checkpoint=SimpleNamespace(
            canonical_content_digest=_direct_digest("direct-foundation")
        ),
    )


def _direct_failed_execution(evidence_digest: str, run_digest: str, job_digest: str):
    attempt = SimpleNamespace(
        scientific_failure_code="train_nonfinite_model_state",
        scientific_failure_evidence_digest=evidence_digest,
        content_digest=_direct_digest(f"attempt-{evidence_digest}"),
        failure_reason="scientific_failure:train_nonfinite_model_state:nonzero_exit:3",
        elapsed_seconds=1.0,
    )
    return SimpleNamespace(
        run_plan_digest=run_digest,
        mace_job_artifact_digest=job_digest,
        state=mdstats.TrainingRunState.FAILED,
        attempts=(attempt,),
        successful_attempt_index=None,
        content_digest=_direct_digest(f"execution-{evidence_digest}"),
    )


def test_real_target_size_eval_path_converts_authenticated_train2_failure_population(tmp_path: Path) -> None:
    import json

    repair, study = _direct_study()
    records = {}
    jobs = {}
    runs = []
    paths = SimpleNamespace(runs=tmp_path / "runs")
    for size in study.next_training_sizes:
        for seed in study.policy.screening_optimizer_seeds:
            run_id = f"direct-n{size}-s{seed}"
            run_digest = _direct_digest(f"run-{size}-{seed}")
            job_digest = _direct_digest(f"job-{size}-{seed}")
            failure = mdstats.Train2NumericalFailureRecord(
                failure_code="train_nonfinite_model_state",
                reason="controlled non-finite model state",
                failed_epoch=2,
                completed_updates=20,
                planned_updates=300,
                execution_epoch_limit=3,
                plan_digest=_direct_digest(f"runtime-plan-{size}-{seed}"),
                training_protocol_digest=_direct_digest(f"runtime-protocol-{size}-{seed}"),
                optimizer_policy_digest=_direct_digest(f"runtime-optimizer-{size}-{seed}"),
                budget_policy_digest=_direct_digest(f"runtime-budget-{size}-{seed}"),
                lr_policy_digest=_direct_digest(f"runtime-lr-{size}-{seed}"),
                raw_checkpoint_name="raw-numerical-state.bin",
                raw_checkpoint_sha256=_direct_digest(f"raw-{size}-{seed}"),
            )
            checkpoint_dir = paths.runs / run_id / "checkpoints"
            checkpoint_dir.mkdir(parents=True)
            (checkpoint_dir / mdstats.TRAIN2_NUMERICAL_FAILURE_FILENAME).write_text(
                json.dumps(failure.to_dict(), sort_keys=True), encoding="utf-8"
            )
            run = SimpleNamespace(
                run_id=run_id,
                kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
                selection_size=size,
                seed=seed,
                mace_job_artifact_digest=job_digest,
                content_digest=run_digest,
            )
            runs.append(run)
            jobs[job_digest] = (SimpleNamespace(), SimpleNamespace(protocol=_direct_protocol(f"{size}-{seed}")), tmp_path)
            records[f"execution:{run_id}"] = _direct_failed_execution(failure.content_digest, run_digest, job_digest)

    outcomes = campaign_core._eval2_target_size_endpoint_evidence(
        cfg={}, paths=paths, store=_DirectStore(records),
        campaign=SimpleNamespace(runs=tuple(runs)), jobs=jobs,
        target_size_study=study, repair2=repair, role_freeze=SimpleNamespace(),
        baseline_model=None, model_dtype="float64", local_wrappers={},
    )
    assert len(outcomes) == len(runs)
    assert all(item.success is None for item in outcomes)
    assert all(item.failure.failure_phase == mdstats.FAILURE_PHASE_TRAIN for item in outcomes)
    terminal = mdstats.attach_epoch_3_outcomes(study, outcomes)
    assert terminal.outcome == mdstats.OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES

    forged_run = runs[0]
    records[f"execution:{forged_run.run_id}"].run_plan_digest = _direct_digest("forged-run-plan")
    with pytest.raises(campaign_core.CampaignCliError, match="execution lineage mismatch"):
        campaign_core._eval2_target_size_endpoint_evidence(
            cfg={}, paths=paths, store=_DirectStore(records),
            campaign=SimpleNamespace(runs=tuple(runs)), jobs=jobs,
            target_size_study=study, repair2=repair, role_freeze=SimpleNamespace(),
            baseline_model=None, model_dtype="float64", local_wrappers={},
        )


def test_real_target_size_eval_path_converts_eval2_nonfinite_signal(tmp_path: Path, monkeypatch) -> None:
    import json

    repair, study = _direct_study()
    records = {}
    jobs = {}
    runs = []
    paths = SimpleNamespace(runs=tmp_path / "runs")
    eval_key = (study.next_training_sizes[0], study.policy.screening_optimizer_seeds[0])
    role_digest = _direct_digest("direct-eval-role")
    checkpoint_digest = _direct_digest("direct-eval-checkpoint")
    eval_execution = None

    for size in study.next_training_sizes:
        for seed in study.policy.screening_optimizer_seeds:
            run_id = f"direct-eval-n{size}-s{seed}"
            run_digest = _direct_digest(f"eval-run-{size}-{seed}")
            job_digest = _direct_digest(f"eval-job-{size}-{seed}")
            run = SimpleNamespace(
                run_id=run_id, kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
                selection_size=size, seed=seed,
                mace_job_artifact_digest=job_digest, content_digest=run_digest,
            )
            runs.append(run)
            jobs[job_digest] = (SimpleNamespace(), SimpleNamespace(protocol=_direct_protocol(f"eval-{size}-{seed}")), tmp_path)
            if (size, seed) == eval_key:
                eval_execution = SimpleNamespace(
                    run_plan_digest=run_digest,
                    mace_job_artifact_digest=job_digest,
                    state=mdstats.TrainingRunState.SUCCEEDED,
                    attempts=(SimpleNamespace(
                        content_digest=_direct_digest("eval-success-attempt"),
                        scientific_failure_code=None,
                        elapsed_seconds=1.0,
                    ),),
                    successful_attempt_index=1,
                    content_digest=_direct_digest("eval-success-execution"),
                )
                records[f"execution:{run_id}"] = eval_execution
                records[f"train2_runtime:{run_id}"] = SimpleNamespace(
                    completed_epochs=3, planned_epochs=30, completed_updates=30,
                    structures_presented=300, normalized_progress=0.1,
                    instantaneous_learning_rate=1.0e-3,
                    optimizer_state_digest=_direct_digest("eval-optimizer-state"),
                    rng_state_digest=_direct_digest("eval-rng-state"),
                )
                continue
            failure = mdstats.Train2NumericalFailureRecord(
                failure_code="train_nonfinite_model_state", reason="controlled non-finite model state",
                failed_epoch=2, completed_updates=20, planned_updates=300, execution_epoch_limit=3,
                plan_digest=_direct_digest(f"eval-runtime-plan-{size}-{seed}"),
                training_protocol_digest=_direct_digest(f"eval-runtime-protocol-{size}-{seed}"),
                optimizer_policy_digest=_direct_digest(f"eval-runtime-optimizer-{size}-{seed}"),
                budget_policy_digest=_direct_digest(f"eval-runtime-budget-{size}-{seed}"),
                lr_policy_digest=_direct_digest(f"eval-runtime-lr-{size}-{seed}"),
                raw_checkpoint_name="raw-numerical-state.bin",
                raw_checkpoint_sha256=_direct_digest(f"eval-raw-{size}-{seed}"),
            )
            checkpoint_dir = paths.runs / run_id / "checkpoints"
            checkpoint_dir.mkdir(parents=True)
            (checkpoint_dir / mdstats.TRAIN2_NUMERICAL_FAILURE_FILENAME).write_text(
                json.dumps(failure.to_dict(), sort_keys=True), encoding="utf-8"
            )
            records[f"execution:{run_id}"] = _direct_failed_execution(failure.content_digest, run_digest, job_digest)

    monkeypatch.setattr(campaign_core, "_eval2_target_role_for_run", lambda **_kwargs: SimpleNamespace(content_digest=role_digest))
    monkeypatch.setattr(campaign_core, "_eval2_target_artifact_for_run", lambda **_kwargs: (SimpleNamespace(), tmp_path / "target.xyz"))
    monkeypatch.setattr(campaign_core, "_evaluation_checkpoint_catalog", lambda *_args, **_kwargs: SimpleNamespace(
        root_directory=str(tmp_path), checkpoints=(SimpleNamespace(sha256=checkpoint_digest),)
    ))
    monkeypatch.setattr(mdstats, "read_train2_trajectory_points", lambda *_args, **_kwargs: (
        SimpleNamespace(epoch=2, checkpoint_sha256=checkpoint_digest),
    ))

    def _raise_eval2_numerical(**_kwargs):
        raise mdstats.Eval2NumericalEvaluationError(
            "eval_nonfinite_force_prediction", "controlled non-finite target force prediction",
            target_role_digest=role_digest, prediction_digest=_direct_digest("nonfinite-prediction"),
        )

    monkeypatch.setattr(campaign_core, "_eval2_full_checkpoint", _raise_eval2_numerical)
    outcomes = campaign_core._eval2_target_size_endpoint_evidence(
        cfg={}, paths=paths, store=_DirectStore(records),
        campaign=SimpleNamespace(runs=tuple(runs)), jobs=jobs,
        target_size_study=study, repair2=repair, role_freeze=SimpleNamespace(),
        baseline_model=None, model_dtype="float64", local_wrappers={},
    )
    outcome = next(item for item in outcomes if item.key == eval_key)
    failure = outcome.failure
    assert failure is not None
    assert failure.failure_phase == mdstats.FAILURE_PHASE_TARGET_EVALUATION
    assert failure.failure_code == "eval_nonfinite_force_prediction"
    assert failure.execution_record_digest == eval_execution.content_digest
    assert failure.execution_attempt_digest == eval_execution.attempts[0].content_digest
    assert failure.checkpoint_digest == checkpoint_digest
    assert failure.evaluation_role_digest == role_digest
    assert failure.target_evaluation_digest is not None

    def _raise_forged_eval2_role(**_kwargs):
        raise mdstats.Eval2NumericalEvaluationError(
            "eval_nonfinite_force_prediction", "forged role binding",
            target_role_digest=_direct_digest("forged-eval-role"),
            prediction_digest=_direct_digest("forged-nonfinite-prediction"),
        )

    monkeypatch.setattr(campaign_core, "_eval2_full_checkpoint", _raise_forged_eval2_role)
    with pytest.raises(campaign_core.CampaignCliError, match="role provenance"):
        campaign_core._eval2_target_size_endpoint_evidence(
            cfg={}, paths=paths, store=_DirectStore(records),
            campaign=SimpleNamespace(runs=tuple(runs)), jobs=jobs,
            target_size_study=study, repair2=repair, role_freeze=SimpleNamespace(),
            baseline_model=None, model_dtype="float64", local_wrappers={},
        )


def test_dependency_graph_keeps_replay_out_of_target_size_decision_authority() -> None:
    root = Path(__file__).resolve().parents[1]
    graph = json.loads(
        (root / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text()
    )
    replay_to_size = {
        (edge["from"], edge["to"], edge["type"])
        for edge in graph["edges"]
        if edge["from"] == "COMMON_REPLAY_MONITOR"
        and edge["to"] in {"SIZE_STUDY_EPOCH3", "SIZE_STUDY_EPOCH10", "SIZE_STUDY_EPOCH30", "TARGET_SIZE_DECISION"}
    }
    assert not replay_to_size
    assert (
        "replay-monitor metrics or diagnostics -> target-size ranking/qualification/tie-break"
        in graph["forbidden_current_paths"]
    )
    assert {
        "from": "COMMON_REPLAY_MONITOR",
        "to": "FROZEN_TRAINING_PROTOCOL",
        "type": "identity_requires",
    } in graph["edges"]


def test_target_size_materialization_resolver_confines_authority_namespaces_and_is_lazy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from mdstats.training_data._common import digest

    final_training_digest = digest({"domain": "final"})
    cv_training_digest = digest({"domain": "cv0"})
    final_frames = tuple(digest({"frame": index}) for index in range(12))
    cv_frames = tuple(digest({"cv-frame": index}) for index in range(10))
    final_authority_id = (
        "source-label::final_development:" + final_training_digest
    )
    cv_authority_id = (
        "source-label::cross_validation_training:fold0:" + cv_training_digest
    )
    coverage_reference = SimpleNamespace(
        domains=(
            SimpleNamespace(
                label_domain_id=final_authority_id,
                source_label_domain_id="source-label",
                training_domain_kind="final_development",
                training_domain_fold_index=None,
                training_domain_digest=final_training_digest,
                frame_uids=final_frames,
            ),
            SimpleNamespace(
                label_domain_id=cv_authority_id,
                source_label_domain_id="source-label",
                training_domain_kind="cross_validation_training",
                training_domain_fold_index=0,
                training_domain_digest=cv_training_digest,
                frame_uids=cv_frames,
            ),
        )
    )
    study = SimpleNamespace(
        qualified_sizes=(4, 8),
        outcome=mdstats.OUTCOME_AWAITING_EPOCH_10,
    )
    final_domain = SimpleNamespace(
        content_digest=final_training_digest,
        label_domain_id="source-label",
        kind=mdstats.FeatureFitDomainKind.FINAL_DEVELOPMENT,
        fold_index=None,
    )
    cv_domain = SimpleNamespace(
        content_digest=cv_training_digest,
        label_domain_id="source-label",
        kind=mdstats.FeatureFitDomainKind.CROSS_VALIDATION_TRAINING,
        fold_index=0,
    )
    calls: list[tuple[str, int]] = []

    def materialize_prefix(_study, *, repair2, label_domain_id: str, target_size: int):
        del repair2
        calls.append((label_domain_id, int(target_size)))
        if label_domain_id == final_authority_id:
            return final_frames[: int(target_size)]
        if label_domain_id == cv_authority_id:
            return cv_frames[: int(target_size)]
        raise AssertionError(f"source DATA2A label escaped resolver: {label_domain_id}")

    monkeypatch.setattr(mdstats, "materialize_candidate_prefix", materialize_prefix)
    resolver = campaign_core._TargetSizeMaterializationResolver(
        coverage_reference, study, object()
    )

    observed = resolver.prefixes_for_domains((final_domain,), 4)
    assert observed == {final_training_digest: final_frames[:4]}
    assert calls == [(final_authority_id, 4)]
    # Repeating the same actual training-domain request is a resolver cache hit.
    assert resolver.prefixes_for_domains((final_domain,), 4) == observed
    assert calls == [(final_authority_id, 4)]

    evaluation = resolver.candidate_evaluation_frames_for_domains((final_domain,))
    assert evaluation == {"source-label": final_frames[8:]}
    assert calls == [(final_authority_id, 4), (final_authority_id, 8)]

    # An unused synthetic CV coverage authority is not eagerly materialized.
    assert resolver.cached_prefix_count == 2
    assert resolver.prefixes_for_domains((cv_domain,), 4) == {
        cv_training_digest: cv_frames[:4]
    }
    assert calls[-1] == (cv_authority_id, 4)
    assert all(label != "source-label" for label, _ in calls)


def test_target_size_materialization_resolver_keeps_fixed_evaluation_cohort_across_fidelity_stages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from mdstats.training_data._common import digest

    training_digest = digest({"domain": "fixed-fidelity-final"})
    frames = tuple(digest({"fixed-fidelity-frame": index}) for index in range(12))
    authority_id = "source::final-authority"
    coverage_reference = SimpleNamespace(
        domains=(
            SimpleNamespace(
                label_domain_id=authority_id,
                source_label_domain_id="source",
                training_domain_kind="final_development",
                training_domain_fold_index=None,
                training_domain_digest=training_digest,
                frame_uids=frames,
            ),
        )
    )
    domain = SimpleNamespace(
        content_digest=training_digest,
        label_domain_id="source",
        kind=mdstats.FeatureFitDomainKind.FINAL_DEVELOPMENT,
        fold_index=None,
    )
    calls: list[tuple[str, int]] = []

    def materialize_prefix(_study, *, repair2, label_domain_id: str, target_size: int):
        del repair2
        calls.append((label_domain_id, int(target_size)))
        return frames[: int(target_size)]

    monkeypatch.setattr(mdstats, "materialize_candidate_prefix", materialize_prefix)
    observed = []
    for outcome in (
        mdstats.OUTCOME_AWAITING_EPOCH_3,
        mdstats.OUTCOME_AWAITING_EPOCH_10,
        mdstats.OUTCOME_AWAITING_EPOCH_30,
    ):
        resolver = campaign_core._TargetSizeMaterializationResolver(
            coverage_reference,
            SimpleNamespace(qualified_sizes=(4, 8), outcome=outcome),
            object(),
        )
        observed.append(resolver.candidate_evaluation_frames_for_domains((domain,)))

    assert observed == [{"source": frames[8:]}] * 3
    assert calls == [(authority_id, 8)] * 3


def test_target_size_materialization_resolver_selected_production_has_no_candidate_evaluation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from mdstats.training_data._common import digest

    training_digest = digest({"domain": "selected-final"})
    frames = tuple(digest({"selected-frame": index}) for index in range(8))
    coverage_reference = SimpleNamespace(
        domains=(
            SimpleNamespace(
                label_domain_id="source::final-authority",
                source_label_domain_id="source",
                training_domain_kind="final_development",
                training_domain_fold_index=None,
                training_domain_digest=training_digest,
                frame_uids=frames,
            ),
        )
    )
    study = SimpleNamespace(qualified_sizes=(4,), outcome=mdstats.OUTCOME_SELECTED)
    domain = SimpleNamespace(
        content_digest=training_digest,
        label_domain_id="source",
        kind=mdstats.FeatureFitDomainKind.FINAL_DEVELOPMENT,
        fold_index=None,
    )
    calls = 0

    def materialize_prefix(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return frames[:4]

    monkeypatch.setattr(mdstats, "materialize_candidate_prefix", materialize_prefix)
    resolver = campaign_core._TargetSizeMaterializationResolver(
        coverage_reference, study, object()
    )
    assert resolver.candidate_evaluation_frames_for_domains((domain,)) == {}
    assert calls == 0


def test_target_size_materialization_resolver_rejects_ambiguous_training_domain_identity() -> None:
    from mdstats.training_data._common import digest

    training_digest = digest({"domain": "ambiguous"})
    coverage = SimpleNamespace(
        source_label_domain_id="source",
        training_domain_kind="final_development",
        training_domain_fold_index=None,
        training_domain_digest=training_digest,
        frame_uids=(digest({"frame": 0}),),
    )
    reference = SimpleNamespace(
        domains=(
            SimpleNamespace(label_domain_id="authority-a", **vars(coverage)),
            SimpleNamespace(label_domain_id="authority-b", **vars(coverage)),
        )
    )
    with pytest.raises(campaign_core.CampaignCliError, match="ambiguous training-domain identity"):
        campaign_core._TargetSizeMaterializationResolver(
            reference,
            SimpleNamespace(qualified_sizes=(4,), outcome=mdstats.OUTCOME_AWAITING_EPOCH_3),
            object(),
        )


def test_materialization_plan_builder_does_not_expose_feature_domain_authority_injection() -> None:
    signature = inspect.signature(production_materialization.build_production_materialization_plan)
    assert "feature_fit_domains" not in signature.parameters
    assert hasattr(mdstats, "materialize_candidate_prefix")
