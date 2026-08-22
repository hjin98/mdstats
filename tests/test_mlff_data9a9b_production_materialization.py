from __future__ import annotations

from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace
import hashlib
import json

import numpy as np
import pytest
from ase.calculators.calculator import Calculator, all_changes

import mdstats
from mdstats.training_data._common import digest
from tests.test_mlff_data5_partition_roles import _build
from tests.test_mlff_data8_mace_artifacts import _probe, _write_replay


class _Calculator(Calculator):
    implemented_properties = ["energy", "forces", "stress"]

    def __init__(self):
        super().__init__()
        self.descriptor_calls = 0
        self.prediction_calls = 0

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        self.prediction_calls += 1
        super().calculate(atoms, properties, system_changes)
        positions = np.asarray(self.atoms.positions, dtype=float)
        self.results = {
            "energy": float(np.sum(positions**2)),
            "forces": -2.0 * positions,
            "stress": np.asarray([0.01, 0.02, 0.03, 0.004, 0.005, 0.006]),
        }

    def get_descriptors(self, atoms, *, invariants_only=True, num_layers=None):
        self.descriptor_calls += 1
        positions = np.asarray(atoms.positions, dtype=float)
        return np.column_stack((np.asarray(atoms.numbers, dtype=float), positions))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path):
    sources, frames, data4, data5 = _build(tmp_path / "target")
    frame_data, _ = mdstats.load_vasp_frame_data_by_run(sources, base_directory=tmp_path / "target")
    foundation_path = tmp_path / "foundation.model"
    foundation_path.write_bytes(b"data9a9b-foundation-fixture")
    foundation = mdstats.FoundationCheckpointIdentity.from_file(foundation_path)
    calc = _Calculator()
    provider = mdstats.MaceCalculatorProvider.from_calculator(
        calc,
        checkpoint_identity=mdstats.ModelCheckpointIdentity(
            model_family="fake-mace",
            checkpoint_locator=str(foundation_path),
            checkpoint_sha256=foundation.sha256,
            calculator_class="tests._Calculator",
            model_version="0.test",
            supported_atomic_numbers=(3, 8, 11, 13, 14, 19),
            device="cpu",
            default_dtype="float64",
        ),
    )
    policy = mdstats.Data6Policy(
        build_lta_selection_features=False,
        build_mace_descriptors=True,
        build_training_difficulty=True,
        build_blinded_predictions=True,
    )
    sweep = mdstats.run_restartable_data6_model_sweep(
        frames, frame_data, data5, policy, provider, tmp_path / "sweep"
    )
    data6 = mdstats.build_data6_feature_bundle(
        sources, frames, frame_data, data4, data5,
        policy=policy, model_provider=provider, model_sweep_artifacts=sweep,
    )
    replay_train = tmp_path / "replay_train.xyz"
    replay_monitor = tmp_path / "replay_monitor.xyz"
    _write_replay(replay_train, offset=0.25, count=4)
    _write_replay(replay_monitor, offset=0.40, count=2)
    replay = mdstats.build_local_replay_plan(replay_train, replay_monitor)
    plan = mdstats.build_production_materialization_plan(
        sources, frames, data4, data5, data6, sweep,
        foundation_checkpoint=foundation,
        compatibility_probe=_probe(),
        replay_plan=replay,
        feature_metric_policy=mdstats.FeatureMetricPolicyTemplate(
            blocks=(mdstats.FeatureBlockPolicy("raw_physical", required=True),)
        ),
        atomic_reference_policy=mdstats.AtomicReferenceFitPolicy(),
        selection_budget_policy=mdstats.SelectionBudgetPolicy(target_sizes=(4, 8)),
        optimizer_policy=mdstats.MaceOptimizerPolicy(device="cpu", max_num_epochs=2),
        require_foundation_residual_e0=False,
    )
    return sources, frames, frame_data, data4, data5, data6, sweep, plan, calc


def test_restartable_data7_then_atomic_data8_materialization(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    root = tmp_path / "materialized"
    partial = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], root,
        execution_policy=mdstats.ProductionMaterializationExecutionPolicy(max_new_data7_domains=1),
    )
    assert not partial.complete
    assert len(partial.checkpoint.data7_artifacts) == 1
    assert partial.checkpoint.data8_artifact is None
    assert not (root / "data8").exists()

    complete = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], root
    )
    assert complete.complete
    assert len(complete.checkpoint.data7_artifacts) == len(complete.checkpoint.plan.domains) == 4
    assert complete.checkpoint.data8_artifact is not None
    data8_payload = json.loads((root / "data8" / "data8_preparation_bundle.json").read_text())
    data8 = mdstats.Data8PreparationBundle.from_dict(data8_payload)
    # The immutable bundle records its assembly-time staging locator. Runtime
    # consumers must use the promoted directory exposed by the materialization
    # record rather than this deleted path.
    assert not Path(data8.output_directory).exists()
    assert complete.data8_runtime_directory is not None
    assert Path(complete.data8_runtime_directory).is_dir()
    assert len(data8.jobs) == 4
    assert data8.replay_plan.mode is mdstats.ReplayMode.PRESELECTED
    assert all(job.protocol.replay_plan_digest == data8.replay_plan.content_digest for job in data8.jobs)
    restored = mdstats.load_production_materialization(root)
    assert restored.checkpoint.content_digest == complete.checkpoint.content_digest
    assert mdstats.ProductionMaterializationRecord.from_dict(complete.to_dict()) == complete
    assert len(complete.load_data7_bundles()) == 4
    assert complete.load_data8_bundle().content_digest == data8.content_digest


def test_resume_reuses_valid_data7_and_repairs_tamper(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    root = tmp_path / "materialized"
    first = mdstats.run_restartable_production_materialization(*inputs[:7], inputs[7], root)
    records = {item.domain_digest: item for item in first.checkpoint.data7_artifacts}
    hashes = {key: item.file_sha256 for key, item in records.items()}
    second = mdstats.run_restartable_production_materialization(*inputs[:7], inputs[7], root)
    assert {item.domain_digest: item.file_sha256 for item in second.checkpoint.data7_artifacts} == hashes

    victim = next(iter(second.checkpoint.data7_artifacts))
    (root / victim.relative_path).write_text("{}\n", encoding="utf-8")
    tampered_sha = _sha(root / victim.relative_path)
    repaired = mdstats.run_restartable_production_materialization(*inputs[:7], inputs[7], root)
    assert repaired.complete
    repaired_record = next(item for item in repaired.checkpoint.data7_artifacts if item.domain_digest == victim.domain_digest)
    assert repaired_record.file_sha256 != tampered_sha
    assert repaired_record.file_sha256 == _sha(root / repaired_record.relative_path)
    assert mdstats.load_production_materialization(root).complete


def test_plan_requires_complete_sweep_and_exact_replay(tmp_path: Path) -> None:
    sources, frames, frame_data, data4, data5, data6, sweep, plan, _ = _fixture(tmp_path)
    assert mdstats.ProductionMaterializationPlan.from_dict(plan.to_dict()) == plan
    with pytest.raises(mdstats.TrainingDataInputError, match="requires an exact replay corpus"):
        replace(plan, replay_plan=mdstats.ReplayPreparationPlan(mode=mdstats.ReplayMode.NONE))


def test_naive_materialization_drops_replay_and_emits_naive_protocol(tmp_path: Path) -> None:
    sources, frames, frame_data, data4, data5, data6, sweep, replay_plan, _ = _fixture(tmp_path)
    naive_plan = mdstats.build_production_materialization_plan(
        sources,
        frames,
        data4,
        data5,
        data6,
        sweep,
        foundation_checkpoint=replay_plan.foundation_checkpoint,
        compatibility_probe=replay_plan.compatibility_probe,
        replay_plan=replay_plan.replay_plan,
        feature_metric_policy=replay_plan.feature_metric_policy,
        atomic_reference_policy=replay_plan.atomic_reference_policy,
        objective_policy=replay_plan.objective_policy,
        configuration_weight_policy=replay_plan.configuration_weight_policy,
        checkpoint_metric_policy=replay_plan.checkpoint_metric_policy,
        selection_budget_policy=replay_plan.selection_budget_policy,
        compatibility_policy=replay_plan.compatibility_policy,
        optimizer_policy=replay_plan.optimizer_policy,
        checkpoint_control_policy=replay_plan.checkpoint_control_policy,
        extxyz_policy=replay_plan.extxyz_policy,
        foundation_reference_energies=dict(replay_plan.foundation_reference_energies),
        selection_size=replay_plan.selection_size,
        require_foundation_residual_e0=replay_plan.require_foundation_residual_e0,
        require_replay=False,
    )
    assert naive_plan.replay_plan.mode is mdstats.ReplayMode.NONE
    materialized = mdstats.run_restartable_production_materialization(
        sources,
        frames,
        frame_data,
        data4,
        data5,
        data6,
        sweep,
        naive_plan,
        tmp_path / "naive-materialized",
    )
    bundle = materialized.load_data8_bundle()
    assert bundle.replay_plan.mode is mdstats.ReplayMode.NONE
    assert all(
        job.protocol.training_mode is mdstats.TrainingMode.NAIVE_FINE_TUNING
        for job in bundle.jobs
    )
    assert all(job.protocol.replay_plan_digest is None for job in bundle.jobs)


def test_existing_plan_mismatch_fails_closed(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    root = tmp_path / "materialized"
    mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], root,
        execution_policy=mdstats.ProductionMaterializationExecutionPolicy(max_new_data7_domains=1),
    )
    changed = mdstats.ProductionMaterializationPlan.from_dict({
        **inputs[7].to_dict(),
        "selection_size": 4,
        "content_digest": None,
    })
    with pytest.raises(mdstats.TrainingDataInputError, match="another plan"):
        mdstats.run_restartable_production_materialization(*inputs[:7], changed, root)


def test_materialization_updates_production_qualification(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    record = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], tmp_path / "materialized"
    )
    sources, frames, _, data4, data5, data6 = inputs[:6]
    run_evidence = {
        "runs": [
            {
                "run_id": "bounded-run-001",
                "frame_count": len(frames.frames),
                "energy_complete": True,
                "forces_complete": True,
                "stress_complete": True,
                "ensemble_status": "resolved",
                "quality_outcome": "qualified",
                "production_status": "accepted",
                "reduced_formula": "LiO",
                "ensemble": "NVT",
                "target_start_kelvin": 300.0,
                "target_end_kelvin": 300.0,
            }
        ]
    }
    normalization = {"version": 1}
    reference = {"version": 1}
    production_plan = mdstats.ProductionCorpusPlan(
        plan_id="bounded-data9a9b-fixture",
        dataset_id=frames.dataset_id,
        source_catalog_digest=sources.content_digest,
        frame_catalog_digest=frames.content_digest,
        normalization_manifest_digest=digest(normalization),
        reference_manifest_digest=digest(reference),
        expected_runs=(mdstats.ProductionExpectedRun(
            run_id="bounded-run-001", frame_count=len(frames.frames), reduced_formula="LiO",
            ensemble="NVT", target_start_kelvin=300.0, target_end_kelvin=300.0,
        ),),
        expected_cross_validation_fold_count=sum(len(v.folds) for v in data5.cross_validation_plans),
    )
    qualification = mdstats.build_production_corpus_qualification_record(
        production_plan=production_plan,
        normalization_manifest=normalization,
        reference_manifest=reference,
        run_evidence_manifest=run_evidence,
        source_catalog=sources,
        frame_catalog=frames,
        data4_bundle=data4,
        data5_bundle=data5,
        data6_bundle=data6,
        production_materialization=record,
    )
    assert qualification.data7_bundle_digests == record.data7_bundle_digests
    assert qualification.data8_bundle_digest == record.data8_bundle_digest
    assert qualification.data8_artifacts_materialized
    assert qualification.replay_corpus_bound
    assert qualification.foundation_features_materialized
    assert not qualification.foundation_residual_e0_materialized
    assert "foundation_residual_e0_not_materialized" in qualification.blockers
    assert not qualification.full_data9a_passed


def test_data8_tree_tamper_is_detected_and_rebuilt(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    root = tmp_path / "materialized"
    complete = mdstats.run_restartable_production_materialization(*inputs[:7], inputs[7], root)
    data8 = complete.checkpoint.data8_artifact
    assert data8 is not None
    victim_rel = next(path for path, _ in data8.tree_entries if path.endswith("mace_config.yaml"))
    victim = root / data8.relative_directory / victim_rel
    victim.write_text(victim.read_text(encoding="utf-8") + "# tamper\n", encoding="utf-8")
    with pytest.raises(mdstats.TrainingDataSerializationError, match="DATA8 artifact"):
        mdstats.load_production_materialization(root)
    repaired = mdstats.run_restartable_production_materialization(*inputs[:7], inputs[7], root)
    assert repaired.complete
    assert mdstats.load_production_materialization(root).complete


def test_shared_data7_cache_reuses_scientific_artifacts_across_variants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _fixture(tmp_path)
    import mdstats.training_data.production_materialization as module

    original = module.build_data7_preparation_bundle
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "build_data7_preparation_bundle", counted)
    shared: dict[str, object] = {}
    cache = tmp_path / "shared-data7"
    first = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        inputs[7],
        tmp_path / "variant-one",
        shared_data7_cache_directory=cache,
        shared_data7_artifacts=shared,
    )
    first_calls = calls
    assert first.complete
    assert first_calls == len(first.checkpoint.plan.domains)

    second = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        inputs[7],
        tmp_path / "variant-two",
        shared_data7_cache_directory=cache,
        shared_data7_artifacts=shared,
    )
    assert second.complete
    assert calls == first_calls
    assert second.data7_bundle_digests == first.data7_bundle_digests
    assert len(shared) == len(first.checkpoint.plan.domains)

    restored_shared: dict[str, object] = {}
    third = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        inputs[7],
        tmp_path / "variant-three",
        shared_data7_cache_directory=cache,
        shared_data7_artifacts=restored_shared,
    )
    assert third.complete
    assert calls == first_calls
    assert third.data7_bundle_digests == first.data7_bundle_digests
    assert len(restored_shared) == len(first.checkpoint.plan.domains)


def test_promoted_data7_artifacts_can_seed_optimizer_only_variant_reuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _fixture(tmp_path)
    import mdstats.training_data.production_materialization as module

    original = module.build_data7_preparation_bundle
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "build_data7_preparation_bundle", counted)
    first = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], tmp_path / "seed-one"
    )
    first_calls = calls
    assert first.complete
    assert first_calls == len(first.checkpoint.plan.domains)

    shared: dict[str, object] = {}
    registered = mdstats.register_reusable_data7_artifacts(first, shared)
    assert registered == len(first.checkpoint.plan.domains)

    changed_plan = replace(
        inputs[7],
        optimizer_policy=replace(inputs[7].optimizer_policy, seed=97),
    )
    assert changed_plan.content_digest != inputs[7].content_digest
    second = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        changed_plan,
        tmp_path / "seed-ninety-seven",
        shared_data7_artifacts=shared,
    )
    assert second.complete
    assert calls == first_calls
    assert second.data7_bundle_digests == first.data7_bundle_digests


def test_atomic_json_hash_is_computed_during_streaming_write(tmp_path: Path) -> None:
    import mdstats.training_data.production_materialization as module

    path = tmp_path / "large.json"
    payload = {"records": [{"index": index, "value": "x" * 64} for index in range(500)]}
    observed = module._atomic_json(path, payload)
    assert observed == hashlib.sha256(path.read_bytes()).hexdigest()
    assert json.loads(path.read_text(encoding="utf-8")) == payload


def test_campaign_rejects_legacy_naive_variant_with_replay_protocol(tmp_path: Path) -> None:
    from mdstats.training_data import campaign_cli

    inputs = _fixture(tmp_path)
    record = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], tmp_path / "materialized"
    )
    bundle = record.load_data8_bundle()
    with pytest.raises(campaign_cli.CampaignCliError, match="naive/replay aliasing"):
        campaign_cli._validate_data8_variant_identity(
            "naive_fine_tuning-n8-seed1", bundle
        )


def test_campaign_resolves_promoted_data8_configs_without_reprepare(tmp_path: Path) -> None:
    from mdstats.training_data import campaign_cli

    inputs = _fixture(tmp_path)
    root = tmp_path / "materialized"
    record = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], root
    )
    bundle = record.load_data8_bundle()
    store = campaign_cli.CampaignStore(tmp_path / "campaign.sqlite3")
    variant_id = "multihead_replay-n8-seed1"
    store.put_record(f"materialization:{variant_id}", record)
    store.put_record(f"data8:{variant_id}", bundle)

    entries = campaign_cli._current_data8_entries(store)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.root == (root / "data8").resolve()
    for job in entry.bundle.jobs:
        config = entry.root / job.config_relative_path
        assert config.is_file()
        assert campaign_cli._sha256(config) == job.config_sha256


def test_preflight_completion_is_bound_to_current_data8_matrix(tmp_path: Path) -> None:
    from mdstats.training_data import campaign_cli

    inputs = _fixture(tmp_path / "fixture")
    record = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], tmp_path / "materialized"
    )
    bundle = record.load_data8_bundle()
    config = tmp_path / "campaign.toml"
    config.write_text(
        campaign_cli._config_template(
            workspace="workspace",
            training_root="training",
            foundation_model="foundation.model",
            replay_train="replay_train.xyz",
            replay_monitor="replay_monitor.xyz",
            acceleration_backend="e3nn",
        ),
        encoding="utf-8",
    )
    _, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    variant_id = "multihead_replay-n8-seed1"
    store.put_record(f"materialization:{variant_id}", record)
    store.put_record(f"data8:{variant_id}", bundle)
    store.put_record(
        "preflight_smoke",
        {"passed": True, "data8_matrix_digest": "0" * 64},
    )
    campaign_cli._mark_stage(
        store,
        paths,
        "preflight",
        campaign_cli.StageState.COMPLETE,
        "legacy DATA8 smoke",
    )
    state, message = campaign_cli._effective_stage(store, paths, "preflight")
    assert state is campaign_cli.StageState.WAITING
    assert "DATA8 variants changed" in message


def test_check_only_preflight_reuses_promoted_data8_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import argparse
    from mdstats.training_data import campaign_cli

    inputs = _fixture(tmp_path / "fixture")
    materialization_root = tmp_path / "materialized"
    record = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], materialization_root
    )
    bundle = record.load_data8_bundle()

    config = tmp_path / "campaign.toml"
    config.write_text(
        campaign_cli._config_template(
            workspace="workspace",
            training_root="training",
            foundation_model="foundation.model",
            replay_train="replay_train.xyz",
            replay_monitor="replay_monitor.xyz",
            acceleration_backend="e3nn",
        ),
        encoding="utf-8",
    )
    _, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    variant_id = "multihead_replay-n8-seed1"
    store.put_record(f"materialization:{variant_id}", record)
    store.put_record(f"data8:{variant_id}", bundle)
    campaign_cli._mark_stage(
        store, paths, "prepare", campaign_cli.StageState.COMPLETE,
        "production data gate passed",
    )
    monkeypatch.setattr(campaign_cli, "command_doctor", lambda args: 0)
    # These tests isolate promoted-DATA8 preflight behavior. Gate authorities are
    # exercised in their dedicated suites, so provide authenticated-looking
    # records rather than constructing a second full prepare graph here.
    authority = SimpleNamespace(content_digest="a" * 64)
    study = SimpleNamespace(
        content_digest="d" * 64, qualified_sizes=(128, 256, 512),
        outcome="awaiting_epoch_10", decision_reason="test target-size study",
    )
    monkeypatch.setattr(campaign_cli, "_load_verified_foundation_audit_authority", lambda store: authority)
    monkeypatch.setattr(campaign_cli, "_load_verified_target_coverage_reference_authority", lambda store: authority)
    monkeypatch.setattr(campaign_cli, "_load_verified_target_size_study_authority", lambda store: study)

    result = campaign_cli.command_preflight(
        argparse.Namespace(config=str(config), check_only=True)
    )
    assert result == 2
    output = capsys.readouterr().out
    assert "verified 4 MACE job configurations across 1 variants" in output
    assert "DATA8 config failed byte verification" not in output


def test_preflight_prints_variant_qualified_config_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import argparse
    from mdstats.training_data import campaign_cli

    inputs = _fixture(tmp_path / "fixture")
    materialization_root = tmp_path / "materialized"
    record = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], materialization_root
    )
    bundle = record.load_data8_bundle()
    victim = next(job for job in bundle.jobs if job.job_id == "final")
    config_path = materialization_root / "data8" / victim.config_relative_path
    config_path.write_text(config_path.read_text(encoding="utf-8") + "# tampered\n", encoding="utf-8")

    config = tmp_path / "campaign.toml"
    config.write_text(
        campaign_cli._config_template(
            workspace="workspace",
            training_root="training",
            foundation_model="foundation.model",
            replay_train="replay_train.xyz",
            replay_monitor="replay_monitor.xyz",
            acceleration_backend="e3nn",
        ),
        encoding="utf-8",
    )
    _, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    variant_id = "multihead_replay-n8-seed1"
    store.put_record(f"materialization:{variant_id}", record)
    store.put_record(f"data8:{variant_id}", bundle)
    campaign_cli._mark_stage(
        store, paths, "prepare", campaign_cli.StageState.COMPLETE,
        "production data gate passed",
    )
    monkeypatch.setattr(campaign_cli, "command_doctor", lambda args: 0)
    # These tests isolate promoted-DATA8 preflight behavior. Gate authorities are
    # exercised in their dedicated suites, so provide authenticated-looking
    # records rather than constructing a second full prepare graph here.
    authority = SimpleNamespace(content_digest="a" * 64)
    study = SimpleNamespace(
        content_digest="d" * 64, qualified_sizes=(128, 256, 512),
        outcome="awaiting_epoch_10", decision_reason="test target-size study",
    )
    monkeypatch.setattr(campaign_cli, "_load_verified_foundation_audit_authority", lambda store: authority)
    monkeypatch.setattr(campaign_cli, "_load_verified_target_coverage_reference_authority", lambda store: authority)
    monkeypatch.setattr(campaign_cli, "_load_verified_target_size_study_authority", lambda store: study)

    result = campaign_cli.command_preflight(
        argparse.Namespace(config=str(config), check_only=True)
    )
    assert result == 1
    output = capsys.readouterr().out
    assert "[FAIL] DATA8 config failed byte verification" in output
    assert "multihead_replay-n8-seed1/final" in output
    assert "stopped before launching MACE" in output
