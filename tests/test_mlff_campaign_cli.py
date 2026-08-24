from __future__ import annotations

import json
from pathlib import Path

import pytest

import mdstats
from mdstats.training_data import campaign_cli
from mdstats.training_data import _campaign_cli_core as campaign_core
from mdstats.training_data import campaign_execution
from mdstats.training_data._common import digest


def test_parser_exposes_small_unix_style_surface() -> None:
    parser = campaign_cli.build_parser()
    choices = parser._subparsers._group_actions[0].choices
    assert tuple(choices) == (
        "init", "doctor", "prepare", "preflight", "select-target-size", "materialize",
        "train", "extend-seed", "evaluate", "verify", "storage", "status", "advance", "guide"
    )
    assert parser.parse_args(["select-target-size"]).func is campaign_cli.command_select_target_size
    assert parser.parse_args(["materialize"]).func is campaign_cli.command_materialize
    storage = choices["storage"]
    storage_choices = storage._subparsers._group_actions[0].choices
    assert tuple(storage_choices) == ("report", "cleanup", "deduplicate", "archive")
    assert parser.parse_args(["storage"]).func is campaign_cli.command_storage
    assert parser.parse_args(["storage", "report", "--top", "7"]).top == 7
    assert parser.parse_args(["storage", "cleanup", "--tier", "cache"]).func is campaign_cli.command_cleanup
    assert parser.parse_args(["storage", "deduplicate", "--apply"]).func is campaign_cli.command_deduplicate
    assert parser.parse_args(["storage", "archive", "verify"]).archive_action == "verify"


def test_legacy_storage_commands_normalize_without_polluting_top_level_help() -> None:
    assert campaign_cli._normalize_legacy_storage_argv(["cleanup", "--tier", "safe"]) == [
        "storage", "cleanup", "--tier", "safe"
    ]
    assert campaign_cli._normalize_legacy_storage_argv([
        "--config", "campaign.toml", "deduplicate", "--apply"
    ]) == ["--config", "campaign.toml", "storage", "deduplicate", "--apply"]
    assert campaign_cli._normalize_legacy_storage_argv([
        "--config=campaign.toml", "archive", "verify"
    ]) == ["--config=campaign.toml", "storage", "archive", "verify"]


def test_init_creates_one_config_and_one_state_database(tmp_path: Path) -> None:
    config = tmp_path / "campaign.toml"
    result = campaign_cli.main([
        "--config", str(config), "init", "--workspace", "work",
        "--training-root", "training", "--foundation-model", "foundation.model",
        "--replay-train", "replay-train.xyz", "--replay-monitor", "replay-monitor.xyz",
    ])
    assert result == 0
    assert config.is_file()
    text = config.read_text(encoding="utf-8")
    assert '[training.naive_fine_tuning]' in text
    assert '[training.multihead_replay]' in text
    assert 'enabled = false' in text
    assert 'seeds = [1, 2]' in text
    assert 'mode = "external_pseudolabel"' in text
    assert "allow_small_corpus = false" in text
    assert "online_monitor_seed = 161803" in text
    assert "online_target_monitor_configurations = 256" in text
    assert "online_replay_monitor_configurations = 512" in text
    assert 'inference_batch_policy = "auto"' in text
    assert "maximum_parallel_dynamics_jobs = 1" in text
    assert "estimated_dynamics_output_mib_per_case = 512.0" in text
    assert "maximum_inference_batch_size = 32" in text
    assert "\nbatch_size = 8\n" not in text[text.index("[evaluation]"):text.index("[preflight]")]
    state = tmp_path / "work" / ".mdstats" / "campaign.sqlite3"
    assert state.is_file()
    assert not state.with_name(state.name + "-wal").exists()


def test_campaign_store_roundtrip_and_stage_state(tmp_path: Path) -> None:
    store = campaign_cli.CampaignStore(tmp_path / "state.sqlite3")
    store.put_record("example", {"schema": "example.v1", "value": 4})
    assert store.get_payload("example")["value"] == 4
    store.set_stage("prepare", campaign_cli.StageState.WAITING, "review manifest")
    assert store.stage("prepare") == (campaign_cli.StageState.WAITING, "review manifest")
    assert store.record_keys() == ("example",)


def test_manifest_discovery_requires_digest_approval(tmp_path: Path) -> None:
    training = tmp_path / "training"
    training.mkdir()
    (training / "LTA_Na.300K.init.xml").write_text("<modeling/>", encoding="utf-8")
    config = tmp_path / "campaign.toml"
    config.write_text(campaign_cli._config_template(
        workspace="work", training_root=str(training), foundation_model="foundation.model",
        replay_train="train.xyz", replay_monitor="monitor.xyz",
    ), encoding="utf-8")
    cfg, paths = campaign_cli._load_config(config)
    with pytest.raises(campaign_cli.CampaignCliError, match="Review reference groups"):
        campaign_cli._ensure_manifest(cfg, paths, approve=False)
    assert paths.manifest.is_file()
    with pytest.raises(campaign_cli.CampaignCliError, match="not approved"):
        campaign_cli._ensure_manifest(cfg, paths, approve=False)
    approved = campaign_cli._ensure_manifest(cfg, paths, approve=True)
    assert len(approved.runs) == 1
    assert approved.runs[0].run_id == "LTA_Na.300K.init"


def test_local_wrapper_shims_have_qualified_names(tmp_path: Path) -> None:
    config = tmp_path / "campaign.toml"
    config.write_text(campaign_cli._config_template(
        workspace="work", training_root="training", foundation_model="foundation.model",
        replay_train="train.xyz", replay_monitor="monitor.xyz",
    ), encoding="utf-8")
    cfg, paths = campaign_cli._load_config(config)
    wrappers = campaign_cli._ensure_local_wrappers(paths)
    assert set(wrappers) == {"mdstats-mace-train", "mdstats-mace-eval", "mdstats-mace-select-head"}
    assert all(path.is_file() and path.stat().st_mode & 0o111 for path in wrappers.values())


def test_checkpoint_evaluation_policy_separates_baseline_head() -> None:
    legacy = mdstats.CheckpointEvaluationPolicy(condition_keys=())
    assert legacy.replay_baseline_head_name == "pt_head"
    restored = mdstats.CheckpointEvaluationPolicy.from_dict(legacy.to_dict())
    assert restored == legacy
    foundation = mdstats.CheckpointEvaluationPolicy(replay_baseline_head_name=None)
    assert mdstats.CheckpointEvaluationPolicy.from_dict(foundation.to_dict()) == foundation
    assert foundation.policy_digest != legacy.policy_digest


def test_inference_execution_plan_roundtrip_is_separate_from_scientific_policy() -> None:
    policy = mdstats.CheckpointEvaluationPolicy(condition_keys=(), batch_size=8)
    plan = mdstats.InferenceExecutionPlan(
        batch_policy="auto", selected_batch_size=8, maximum_batch_size=32,
        rationale=("bounded-test",),
    )
    assert mdstats.InferenceExecutionPlan.from_dict(plan.to_dict()) == plan
    assert "execution_digest" in plan.to_dict()
    assert not ({
        "concurrent_model_jobs", "use_cuda_streams", "host_ram_budget_bytes",
        "compatible_profile_digest",
    } & plan.to_dict().keys())
    stale = plan.to_dict()
    stale["compatible_profile_digest"] = "a" * 64
    stale["execution_digest"] = digest({
        key: value for key, value in stale.items() if key != "execution_digest"
    })
    with pytest.raises(mdstats.TrainingDataSerializationError, match="digest mismatch"):
        mdstats.InferenceExecutionPlan.from_dict(stale)
    assert "inference" not in policy.to_dict()["schema"]
    assert "batch_policy" not in policy.to_dict()


def test_historical_inference_execution_plan_v1_is_validated_then_rebuilt_as_v2() -> None:
    legacy = {
        "schema": "mdstats.inference-execution-plan.v1",
        "batch_policy": "auto",
        "selected_batch_size": 8,
        "maximum_batch_size": 32,
        "concurrent_model_jobs": 3,
        "use_cuda_streams": True,
        "host_ram_budget_bytes": 8 * 1024**3,
        "graph_cache_enabled": False,
        "monitor_cache_enabled": False,
        "compatible_profile_digest": "a" * 64,
        "rationale": ["historical-fixture"],
    }
    legacy["execution_digest"] = digest(legacy)

    rebuilt = mdstats.InferenceExecutionPlan.from_dict(legacy)

    assert rebuilt.to_dict()["schema"] == "mdstats.inference-execution-plan.v2"
    assert rebuilt.selected_batch_size == 8
    assert rebuilt.maximum_batch_size == 32
    assert rebuilt.graph_cache_enabled is False
    assert rebuilt.monitor_cache_enabled is False
    assert rebuilt.rationale == (
        "historical-fixture",
        "rebuilt_from_inference_execution_plan_v1",
    )
    assert mdstats.InferenceExecutionPlan.from_dict(rebuilt.to_dict()) == rebuilt

    corrupted = dict(legacy)
    corrupted["selected_batch_size"] = 16
    with pytest.raises(mdstats.TrainingDataSerializationError, match="legacy v1 digest mismatch"):
        mdstats.InferenceExecutionPlan.from_dict(corrupted)


def test_runtime_variants_leave_scientific_policy_and_metrics_unchanged() -> None:
    import numpy as np
    from ase import Atoms
    from mdstats.training_data.model_features import AtomicModelPrediction

    first = mdstats.CheckpointEvaluationPolicy(
        condition_keys=(), batch_size=1, cache_monitor_datasets=False,
        cache_replay_baseline=False,
    )
    second = mdstats.CheckpointEvaluationPolicy(
        condition_keys=(), batch_size=64, cache_monitor_datasets=True,
        cache_replay_baseline=True,
    )
    assert first.policy_digest == second.policy_digest
    assert first.to_dict() == second.to_dict()

    atoms = Atoms("Li", cell=[5, 5, 5], pbc=True)
    atoms.info["REF_energy"] = 1.0
    atoms.info["REF_stress"] = np.zeros(6)
    atoms.arrays["REF_forces"] = np.zeros((1, 3))
    prediction = AtomicModelPrediction(
        energy_ev=1.0,
        forces_ev_per_angstrom=np.zeros((1, 3)),
        stress_ev_per_angstrom3=np.zeros((3, 3)),
    )
    assert campaign_execution._metrics_from_predictions(
        (atoms,), (prediction,), policy=first
    ) == campaign_execution._metrics_from_predictions(
        (atoms,), (prediction,), policy=second
    )

    small = mdstats.InferenceExecutionPlan(
        selected_batch_size=1, maximum_batch_size=1,
        graph_cache_enabled=False, monitor_cache_enabled=False,
        prediction_cache_enabled=False,
    )
    large = mdstats.InferenceExecutionPlan(
        selected_batch_size=32, maximum_batch_size=32,
    )
    assert small.execution_digest != large.execution_digest


def test_historical_evaluation_policy_digest_roundtrips_without_canonical_rewrite() -> None:
    payload = mdstats.CheckpointEvaluationPolicy(condition_keys=()).to_dict()
    payload.pop("policy_digest")
    payload["schema"] = "mdstats.checkpoint-evaluation-policy.v3"
    payload.update({
        "batch_size": 13,
        "cache_monitor_datasets": False,
        "cache_replay_baseline": False,
    })
    payload["policy_digest"] = digest(payload)
    restored = mdstats.CheckpointEvaluationPolicy.from_dict(payload)
    assert restored.batch_size == 13
    assert restored.policy_digest == payload["policy_digest"]
    assert restored.to_dict() == payload


def test_evaluation_execution_resolution_preserves_legacy_fixed_and_distinguishes_auto() -> None:
    legacy = campaign_core._evaluation_inference_execution_plan(
        {"evaluation": {"batch_size": 12}}
    )
    automatic = campaign_core._evaluation_inference_execution_plan(
        {
            "performance": {"cpu_fraction": 0.75, "ram_fraction": 0.65},
            "execution": {"inference_gpu_memory_fraction": 0.70},
            "evaluation": {
                "inference_batch_policy": "auto", "maximum_inference_batch_size": 24,
            },
        }
    )
    fixed = campaign_core._evaluation_inference_execution_plan(
        {"evaluation": {
            "inference_batch_policy": "fixed", "fixed_inference_batch_size": 6,
            "maximum_inference_batch_size": 24,
        }}
    )
    assert (legacy.batch_policy, legacy.selected_batch_size, legacy.maximum_batch_size) == (
        "fixed", 12, 12
    )
    assert (automatic.batch_policy, automatic.selected_batch_size, automatic.maximum_batch_size) == (
        "auto", 8, 24
    )
    assert (
        automatic.cpu_fraction,
        automatic.ram_fraction,
        automatic.gpu_memory_fraction,
    ) == (0.75, 0.65, 0.70)
    assert (fixed.batch_policy, fixed.selected_batch_size, fixed.maximum_batch_size) == (
        "fixed", 6, 24
    )


def _as_legacy_mpa0_config(text: str) -> str:
    """Turn a generated template into a pre-CONFIG1 singleton MPA-0 fixture."""
    start = text.index("[foundation]")
    end = text.index("\n[paths]", start)
    text = text[:start] + text[end + 1 :]
    return text.replace('foundation_name = "MACE-MH-1"', 'foundation_name = "MPA-0-medium"')


def _write_replay(path: Path, offsets: tuple[float, ...]) -> None:
    import numpy as np
    from ase import Atoms
    from ase.io import write

    frames = []
    for index, offset in enumerate(offsets):
        atoms = Atoms(
            numbers=[3, 8],
            positions=[[0.0, 0.0, 0.0], [1.5 + offset, 0.0, 0.0]],
            cell=np.eye(3) * (6.0 + 0.1 * index),
            pbc=True,
        )
        atoms.info["REF_energy"] = float(-2.0 + offset)
        atoms.info["REF_stress"] = np.zeros(6)
        atoms.arrays["REF_forces"] = np.zeros((2, 3))
        frames.append(atoms)
    write(path, frames, format="extxyz")


def test_replay_qualification_binds_pseudolabels_to_foundation_and_counts(tmp_path: Path) -> None:
    foundation = tmp_path / "foundation.model"
    foundation.write_bytes(b"exact-foundation-checkpoint")
    train = tmp_path / "replay-train.xyz"
    monitor = tmp_path / "replay-monitor.xyz"
    _write_replay(train, (0.0, 0.1))
    _write_replay(monitor, (0.3,))
    config = tmp_path / "campaign.toml"
    text = _as_legacy_mpa0_config(campaign_cli._config_template(
        workspace="work", training_root="training", foundation_model=str(foundation),
        replay_train=str(train), replay_monitor=str(monitor),
    ))
    text = text.replace("all_atomic_numbers = [3, 8, 11, 13, 14, 19]", "all_atomic_numbers = [3, 8]")
    text = text.replace("minimum_train_configurations = 100", "minimum_train_configurations = 2")
    text = text.replace("minimum_monitor_configurations = 20", "minimum_monitor_configurations = 1")
    config.write_text(text, encoding="utf-8")
    cfg, paths = campaign_cli._load_config(config)
    plan, summary, failures, warnings = campaign_cli._qualify_replay(cfg, paths)
    assert failures == []
    assert warnings == []
    assert summary["qualified"] is True
    assert summary["label_mode"] == "foundation_pseudolabel"
    assert summary["legacy_foundation_checkpoint_digest"] == campaign_cli._sha256(foundation)
    assert summary["foundation_label_generator_identity_digest"] is None
    assert plan.train_artifact.foundation_checkpoint_digest == campaign_cli._sha256(foundation)


def test_replay_qualification_blocks_smoke_sized_corpus_by_default(tmp_path: Path) -> None:
    foundation = tmp_path / "foundation.model"
    foundation.write_bytes(b"foundation")
    train = tmp_path / "train.xyz"
    monitor = tmp_path / "monitor.xyz"
    _write_replay(train, (0.0,))
    _write_replay(monitor, (0.3,))
    config = tmp_path / "campaign.toml"
    text = _as_legacy_mpa0_config(campaign_cli._config_template(
        workspace="work", training_root="training", foundation_model=str(foundation),
        replay_train=str(train), replay_monitor=str(monitor),
    )).replace("all_atomic_numbers = [3, 8, 11, 13, 14, 19]", "all_atomic_numbers = [3, 8]")
    config.write_text(text, encoding="utf-8")
    cfg, paths = campaign_cli._load_config(config)
    _, summary, failures, warnings = campaign_cli._qualify_replay(cfg, paths)
    assert summary["qualified"] is False
    assert warnings == []
    assert any("production policy requires" in item for item in failures)


def test_variant_matrix_is_deterministic() -> None:
    cfg = {
        "training": {"modes": ["naive_fine_tuning", "multihead_replay"], "seeds": [2, 1]},
        "selection": {"sizes": [256, 512]},
    }
    assert campaign_cli._variant_specs(cfg) == (
        ("naive_fine_tuning", 256, 2),
        ("naive_fine_tuning", 256, 1),
        ("naive_fine_tuning", 512, 2),
        ("naive_fine_tuning", 512, 1),
        ("multihead_replay", 256, 2),
        ("multihead_replay", 256, 1),
        ("multihead_replay", 512, 2),
        ("multihead_replay", 512, 1),
    )


def test_preflight_payload_uses_plain_json_boolean(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import numpy as np
    from types import SimpleNamespace

    config = tmp_path / "campaign.toml"
    config.write_text(campaign_cli._config_template(
        workspace="work", training_root="training", foundation_model="foundation.model",
        replay_train="train.xyz", replay_monitor="monitor.xyz",
    ), encoding="utf-8")
    cfg, paths = campaign_cli._load_config(config)
    job_root = tmp_path / "job"
    job_root.mkdir()
    config_path = job_root / "mace.yml"
    config_path.write_text("name: test\n", encoding="utf-8")
    prediction = paths.internal / "preflight-smoke" / "evaluation_predictions.xyz"

    class FakeAtoms:
        info = {"MACE_energy": np.asarray(1.0), "MACE_stress": np.zeros((3, 3))}
        arrays = {"MACE_forces": np.zeros((1, 3))}

    calls = iter((
        {"passed": True, "return_code": 0},
        {"passed": True, "return_code": 0},
        {"passed": True, "return_code": 0},
    ))

    def fake_run(*args, **kwargs):
        command = tuple(str(v) for v in args[0])
        smoke = paths.internal / "preflight-smoke"
        (smoke / "models").mkdir(parents=True, exist_ok=True)
        (smoke / "checkpoints").mkdir(parents=True, exist_ok=True)
        if "mdstats-mace-train" in command[0]:
            (smoke / "models" / "mdstats_campaign_preflight.model").write_bytes(b"model")
            (smoke / "checkpoints" / "epoch-0.pt").write_bytes(b"checkpoint")
        elif "mdstats-mace-select-head" in command[0]:
            (smoke / "target_head.model").write_bytes(b"head")
        else:
            prediction.parent.mkdir(parents=True, exist_ok=True)
            prediction.write_text("stub", encoding="utf-8")
        return next(calls)

    monkeypatch.setattr(campaign_core, "_run_bounded_process", fake_run)
    monkeypatch.setattr(campaign_core, "_ensure_local_wrappers", lambda paths: {
        "mdstats-mace-train": Path("mdstats-mace-train"),
        "mdstats-mace-select-head": Path("mdstats-mace-select-head"),
        "mdstats-mace-eval": Path("mdstats-mace-eval"),
    })
    import ase.io
    monkeypatch.setattr(ase.io, "read", lambda *args, **kwargs: [FakeAtoms()])
    # _run_local_preflight_smoke imports read locally, so patch its module symbol through ASE.
    bundle = SimpleNamespace(output_directory=str(job_root))
    job = SimpleNamespace(relative_directory=".", config_relative_path="mace.yml", config_sha256=campaign_cli._sha256(config_path))
    payload = campaign_cli._run_local_preflight_smoke(cfg, paths, bundle, job)
    assert payload["finite_round_trip"] is True
    json.dumps(payload)


def test_verification_guidance_is_actionable() -> None:
    guidance = campaign_cli._result_guidance(({
        "finite": True,
        "absolute_energy_drift_ev_per_atom_per_ps": 0.04,
        "minimum_pair_distance_angstrom": 0.7,
        "maximum_force_ev_per_angstrom": 150.0,
    },))
    joined = " ".join(guidance)
    assert "timestep" in joined
    assert "short-range" in joined
    assert "force" in joined


def test_status_prints_next_safe_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = tmp_path / "campaign.toml"
    config.write_text(campaign_cli._config_template(
        workspace="work", training_root="training", foundation_model="foundation.model",
        replay_train="train.xyz", replay_monitor="monitor.xyz",
    ), encoding="utf-8")
    assert campaign_cli.main(["--config", str(config), "status"]) == 0
    output = capsys.readouterr().out
    assert "Next command:" in output
    assert "doctor" in output






def test_prepare_refuses_to_skip_doctor(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = tmp_path / "campaign.toml"
    config.write_text(campaign_cli._config_template(
        workspace="work", training_root="training", foundation_model="foundation.model",
        replay_train="train.xyz", replay_monitor="monitor.xyz",
    ), encoding="utf-8")
    result = campaign_cli.main(["--config", str(config), "prepare"])
    assert result == 2
    assert "Stage `doctor` is not complete" in capsys.readouterr().err


def test_preflight_defaults_to_required_smoke() -> None:
    parser = campaign_cli.build_parser()
    args = parser.parse_args(["preflight"])
    assert args.check_only is False
    check = parser.parse_args(["preflight", "--check-only"])
    assert check.check_only is True


def test_stage_completion_is_bound_to_current_configuration(tmp_path: Path) -> None:
    config = tmp_path / "campaign.toml"
    config.write_text(campaign_cli._config_template(
        workspace="work", training_root="training", foundation_model="foundation.model",
        replay_train="train.xyz", replay_monitor="monitor.xyz",
    ), encoding="utf-8")
    cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    campaign_cli._mark_stage(store, paths, "doctor", campaign_cli.StageState.COMPLETE, "passed")
    assert campaign_cli._effective_stage(store, paths, "doctor")[0] is campaign_cli.StageState.COMPLETE
    config.write_text(config.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    state, message = campaign_cli._effective_stage(store, paths, "doctor")
    assert state is campaign_cli.StageState.WAITING
    assert "campaign.toml changed" in message


def test_train_cannot_bypass_target_size_selection_with_legacy_preflight_receipt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "campaign.toml"
    config.write_text(campaign_cli._config_template(
        workspace="work", training_root="training", foundation_model="foundation.model",
        replay_train="train.xyz", replay_monitor="monitor.xyz",
    ), encoding="utf-8")
    cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    campaign_cli._mark_stage(store, paths, "preflight", campaign_cli.StageState.COMPLETE, "legacy config-only preflight")
    result = campaign_cli.main(["--config", str(config), "train", "--dry-run"])
    assert result == 2
    error = capsys.readouterr().err
    assert "target_multi_view_repair_v2" in error or "select-target-size" in error


def test_real_flat_lta_archive_discovery_when_available(tmp_path: Path) -> None:
    import os
    root_value = os.environ.get("MLFF_TRAINING_ROOT")
    if not root_value:
        pytest.skip("real LTA training root not supplied")
    manifest = mdstats.discover_vasp_manifest(root_value, dataset_id="lta-real", system_profile="lta", pattern="**/*.xml")
    assert len(manifest.runs) == 27
    assert "LTA_Na.300K.init" in {run.run_id for run in manifest.runs}


def test_run_evidence_fails_closed_and_accepts_reviewed_ensemble_assertion() -> None:
    from types import SimpleNamespace

    source = SimpleNamespace(
        run_id="run-a",
        assertions=(),
        quality_outcome="degraded_quality",
        production_status="diagnostic_only",
        ensemble_status="unresolved",
        ensemble="unknown",
        frame_count=4,
        composition=SimpleNamespace(reduced_formula="AlNaO4Si"),
    )
    with pytest.raises(campaign_cli.CampaignCliError, match="ensemble_assertion_basis"):
        campaign_cli._run_evidence(SimpleNamespace(sources=(source,)))
    source.assertions = (
        ("ensemble", "nvt"),
        ("ensemble_assertion_basis", "originating INCAR: Langevin thermostat"),
        ("target_temperature_kelvin", 300.0),
    )
    payload = campaign_cli._run_evidence(SimpleNamespace(sources=(source,)))
    run = payload["runs"][0]
    assert run["ensemble_status"] == "resolved"
    assert run["ensemble"] == "nvt"
    assert run["quality_outcome"] == "degraded_quality"


def test_data8_runtime_entries_use_promoted_materialization_root(tmp_path: Path) -> None:
    from types import SimpleNamespace

    recorded_staging = tmp_path / ".data8-staging-deleted"
    materialization_root = tmp_path / "variant"
    promoted = materialization_root / "data8"
    promoted.mkdir(parents=True)
    bundle = SimpleNamespace(
        output_directory=str(recorded_staging),
        content_digest="a" * 64,
        jobs=(
            SimpleNamespace(
                protocol=SimpleNamespace(
                    training_mode=SimpleNamespace(value="multihead_replay"),
                    selection_size=512,
                    optimizer_policy=SimpleNamespace(seed=2),
                )
            ),
        ),
    )
    materialization = SimpleNamespace(
        root_directory=str(materialization_root),
        checkpoint=SimpleNamespace(
            data8_artifact=SimpleNamespace(
                relative_directory="data8",
                bundle_digest=bundle.content_digest,
            )
        ),
    )

    class FakeStore:
        def record_keys(self, prefix):
            assert prefix == "data8:"
            return ["data8:multihead_replay-n512-seed2"]

        def has_record(self, key):
            return key == "materialization:multihead_replay-n512-seed2"

        def get_record(self, key, record_type):
            del record_type
            if key.startswith("data8:"):
                return bundle
            if key.startswith("materialization:"):
                return materialization
            raise KeyError(key)

    entries = campaign_cli._current_data8_entries(FakeStore())
    assert len(entries) == 1
    assert entries[0].root == promoted.resolve()
    assert not recorded_staging.exists()


def test_data8_runtime_member_rebases_staged_replay_path(tmp_path: Path) -> None:
    from types import SimpleNamespace

    recorded_root = tmp_path / ".data8-staging-deleted"
    runtime_root = tmp_path / "generation"
    bundle = SimpleNamespace(output_directory=str(recorded_root))
    recorded = recorded_root / "shared" / "replay" / "replay_monitor.xyz"
    observed = campaign_cli._resolve_data8_runtime_member(bundle, runtime_root, recorded)
    assert observed == runtime_root / "shared" / "replay" / "replay_monitor.xyz"


def test_data8_job_member_resolves_job_scoped_extxyz_path(tmp_path: Path) -> None:
    from types import SimpleNamespace

    recorded_root = tmp_path / ".data8-staging-deleted"
    runtime_root = tmp_path / "generation"
    bundle = SimpleNamespace(output_directory=str(recorded_root))
    job = SimpleNamespace(relative_directory="jobs/fold_00")
    observed = campaign_cli._resolve_data8_job_member(
        bundle, runtime_root, job, "target_checkpoint_full.xyz"
    )
    assert observed == (runtime_root / "jobs" / "fold_00" / "target_checkpoint_full.xyz").resolve()


def test_data8_job_member_rebases_absolute_staged_path_without_double_job_prefix(tmp_path: Path) -> None:
    from types import SimpleNamespace

    recorded_root = tmp_path / ".data8-staging-deleted"
    runtime_root = tmp_path / "generation"
    bundle = SimpleNamespace(output_directory=str(recorded_root))
    job = SimpleNamespace(relative_directory="jobs/fold_00")
    recorded = recorded_root / "jobs" / "fold_00" / "fold_evaluation.xyz"
    observed = campaign_cli._resolve_data8_job_member(bundle, runtime_root, job, recorded)
    assert observed == runtime_root / "jobs" / "fold_00" / "fold_evaluation.xyz"


def test_preflight_static_e0_check_reports_replay_only_gap() -> None:
    payload = {
        "atomic_numbers": "[1, 3, 8]",
        "heads": repr({
            "target_head": {"E0s": repr({3: -1.0, 8: -2.0})},
            "pt_head": {},
        }),
    }
    failures = campaign_cli._mace_config_e0_coverage_failures(payload)
    assert failures == (
        "target_head E0s omit global atomic numbers [1]; "
        "regenerate DATA8 with mdstats >= 0.20.66a0",
    )


def test_preflight_static_e0_check_accepts_padded_target_mapping() -> None:
    payload = {
        "atomic_numbers": "[1, 3, 8]",
        "heads": repr({
            "target_head": {"E0s": repr({1: 0.0, 3: -1.0, 8: -2.0})},
            "pt_head": {},
        }),
    }
    assert campaign_cli._mace_config_e0_coverage_failures(payload) == ()


def test_preflight_error_summary_surfaces_last_exception(tmp_path: Path) -> None:
    path = tmp_path / "stderr.log"
    path.write_text(
        "warning\nTraceback (most recent call last):\nKeyError: missing E0\n",
        encoding="utf-8",
    )
    assert campaign_cli._preflight_error_summary(path) == "KeyError: missing E0"


def test_preflight_static_e0_check_accepts_head_specific_elements() -> None:
    payload = {
        "atomic_numbers": "[1, 3, 8]",
        "heads": repr({
            "target_head": {
                "atomic_numbers": "[3, 8]",
                "E0s": repr({3: -1.0, 8: -2.0}),
            },
            "pt_head": {},
        }),
    }
    assert campaign_cli._mace_config_e0_coverage_failures(payload) == ()


def test_preflight_builds_bounded_real_multihead_smoke_config(tmp_path: Path) -> None:
    import ast
    from types import SimpleNamespace

    import yaml
    from ase import Atoms
    from ase.io import write

    job_dir = tmp_path / "job"
    smoke_root = tmp_path / "smoke"
    job_dir.mkdir()
    smoke_root.mkdir()

    target_train = [Atoms("O", positions=[[float(i), 0.0, 0.0]]) for i in range(35)]
    target_train.append(Atoms("LiO", positions=[[0, 0, 0], [1, 0, 0]]))
    target_valid = [Atoms("LiO", positions=[[0, 0, 0], [1, 0, 0]]) for _ in range(12)]
    replay_train = [Atoms("H", positions=[[float(i), 0.0, 0.0]]) for i in range(100)]
    replay_valid = [Atoms("H", positions=[[float(i), 0.0, 0.0]]) for i in range(20)]
    for name, frames in (
        ("target_train.xyz", target_train),
        ("target_valid.xyz", target_valid),
        ("replay_train.xyz", replay_train),
        ("replay_valid.xyz", replay_valid),
    ):
        write(job_dir / name, frames, format="extxyz")

    payload = {
        "name": "source",
        "heads": repr({
            "target_head": {
                "train_file": "target_train.xyz",
                "valid_file": "target_valid.xyz",
                "atomic_numbers": repr([3, 8]),
                "E0s": repr({3: 0.0, 8: 0.0}),
            },
            "pt_head": {},
        }),
        "pt_train_file": "replay_train.xyz",
        "pt_valid_file": "replay_valid.xyz",
        "batch_size": 2,
        "real_pt_data_ratio_threshold": 0.1,
    }
    source_config = job_dir / "mace.yaml"
    source_config.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    cfg = {"preflight": {
        "target_train_configurations": 32,
        "target_valid_configurations": 8,
        "replay_train_configurations": 64,
        "replay_valid_configurations": 8,
    }}
    job = SimpleNamespace(loader_dry_run=SimpleNamespace(target_head_name="target_head"))

    smoke_config, metadata, expected, evaluation = campaign_cli._bounded_preflight_configuration(
        cfg,
        source_config_path=source_config,
        job_dir=job_dir,
        smoke_root=smoke_root,
        job=job,
    )
    assert metadata["bounded"] is True
    assert metadata["target_train_configurations"] == 33  # 32 leading + Li coverage
    assert metadata["target_valid_configurations"] == 8
    assert metadata["replay_train_configurations"] == 64
    assert metadata["replay_valid_configurations"] == 8
    assert expected == (33 + 64) // 2
    assert evaluation == smoke_root / "target_valid.smoke.xyz"
    rewritten = yaml.safe_load(smoke_config.read_text(encoding="utf-8"))
    heads = ast.literal_eval(rewritten["heads"])
    assert Path(heads["target_head"]["train_file"]).name == "target_train.smoke.xyz"
    assert Path(rewritten["pt_train_file"]).name == "replay_train.smoke.xyz"


def test_mace_training_progress_probe_reports_exact_gradient_percentage(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    results = tmp_path / "results"
    logs.mkdir()
    results.mkdir()
    (logs / "run.log").write_text(
        "===========TRAINING===========\nStarted training\n", encoding="utf-8"
    )
    rows = [json.dumps({"mode": "opt", "epoch": 0}) for _ in range(12)]
    (results / "run_train.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
    probe = campaign_cli._MaceTrainingProgressProbe(
        log_dir=logs,
        result_dir=results,
        expected_updates=48,
        device="cpu",
    )
    text = probe()
    assert "phase=epoch 1/1" in text
    assert "progress=12/48 (25.0%); unit=gradient-update" in text


def test_mace_training_progress_probe_marks_only_new_optimizer_activity_as_true_epoch(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    results = tmp_path / "results"
    logs.mkdir()
    results.mkdir()
    (logs / "run.log").write_text("optimizer running\n", encoding="utf-8")
    result_path = results / "run_train.txt"
    result_path.write_text(
        json.dumps({"mode": "opt", "epoch": 0}) + "\n",
        encoding="utf-8",
    )
    probe = campaign_cli._MaceTrainingProgressProbe(
        log_dir=logs,
        result_dir=results,
        expected_updates=48,
        device="cpu",
        epoch_activity_timeout_seconds=120.0,
    )
    # Existing checkpoint history is counted but cannot authorize scheduler
    # expansion before the restarted child produces fresh work.
    assert probe.snapshot().true_epoch_active is False
    with result_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"mode": "opt", "epoch": 0}) + "\n")
    state = probe.snapshot()
    assert state.updates == 2
    assert state.phase == "epoch 1/1"
    assert state.true_epoch_active is True


def test_legacy_parallel_fields_do_not_bypass_true_epoch_defaults() -> None:
    policy = campaign_cli._training_concurrency_policy(
        {
            "execution": {
                "minimum_parallel_training_jobs": 2,
                "parallel_training_ramp_up_seconds": 1.0,
                "parallel_training_stability_samples": 2,
            }
        }
    )
    # 0.20.72 campaign files may contain the legacy fields above. Their old
    # semantics must not shorten the new true-epoch calibration window.
    assert policy.epoch_stabilization_seconds == 60.0
    assert policy.stability_samples == 12
    assert policy.gpu_utilization_fraction == 0.90


def test_previous_generated_training_window_migrates_to_one_minute() -> None:
    policy = campaign_cli._training_concurrency_policy(
        {
            "execution": {
                "parallel_training_epoch_stabilization_seconds": 180.0,
            }
        }
    )
    assert policy.epoch_stabilization_seconds == 60.0


def test_custom_training_window_remains_authoritative() -> None:
    policy = campaign_cli._training_concurrency_policy(
        {
            "execution": {
                "parallel_training_epoch_stabilization_seconds": 90.0,
            }
        }
    )
    assert policy.epoch_stabilization_seconds == 90.0


def test_training_config_inputs_resolve_from_data8_job_directory(tmp_path: Path) -> None:
    import yaml

    root = tmp_path / "data8"
    job = root / "jobs" / "fold_00"
    shared = root / "shared"
    (shared / "foundation").mkdir(parents=True)
    (shared / "replay").mkdir(parents=True)
    job.mkdir(parents=True)
    for path in (
        shared / "foundation" / "mace.model",
        shared / "replay" / "train.xyz",
        shared / "replay" / "valid.xyz",
        job / "target_train.xyz",
        job / "target_valid.xyz",
    ):
        path.write_text("fixture\n", encoding="utf-8")
    config = job / "mace_config.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "foundation_model": "../../shared/foundation/mace.model",
                "pt_train_file": "../../shared/replay/train.xyz",
                "pt_valid_file": "../../shared/replay/valid.xyz",
                "heads": repr(
                    {
                        "target_head": {
                            "train_file": "target_train.xyz",
                            "valid_file": "target_valid.xyz",
                        }
                    }
                ),
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    assert campaign_cli._training_config_input_failures(config, job) == ()


def test_obsolete_training_runtime_retains_compact_diagnostic_and_deletes_heavy_bytes(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    (run_root / "logs").mkdir(parents=True)
    (run_root / "checkpoints").mkdir()
    (run_root / "checkpoints" / "partial.pt").write_bytes(b"x" * 4096)
    (run_root / "attempt-01.stderr.log").write_text("legacy failure\n", encoding="utf-8")
    (run_root / "training_execution.json").write_text("{}\n", encoding="utf-8")
    diagnostic = campaign_cli._archive_obsolete_training_runtime(run_root, "a" * 64)
    assert diagnostic is not None
    payload = json.loads(diagnostic.read_text(encoding="utf-8"))
    assert payload["schema"] == "mdstats.obsolete-training-runtime-diagnostic.v2"
    assert payload["logical_size_bytes_removed"] >= 4096
    assert payload["log_tails"]["attempt-01.stderr.log"] == "legacy failure\n"
    assert payload["prior_execution"] == {}
    assert not (run_root / "attempt-01.stderr.log").exists()
    assert not (run_root / "training_execution.json").exists()
    assert not (run_root / "logs").exists()
    assert not (run_root / "checkpoints").exists()



def test_campaign_cleanup_removes_only_reconstructable_caches_and_keeps_diagnostics(tmp_path: Path) -> None:
    config = tmp_path / "campaign.toml"
    config.write_text(
        campaign_cli._config_template(
            workspace="work",
            training_root="training",
            foundation_model="foundation.model",
            replay_train="replay.xyz",
            replay_monitor="monitor.xyz",
        ),
        encoding="utf-8",
    )
    cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    store.put_record(
        "preflight_smoke",
        {"schema": "smoke.v1", "passed": True, "target_model_sha256": "abc"},
    )
    frame_cache = paths.internal / "frame-cache"
    data7_cache = paths.internal / "data7-cache"
    frame_cache.mkdir()
    data7_cache.mkdir()
    (frame_cache / "frames.npz").write_bytes(b"x" * 1024)
    (data7_cache / "domain.zip").write_bytes(b"y" * 1024)
    smoke = paths.internal / "preflight-smoke"
    (smoke / "checkpoints").mkdir(parents=True)
    (smoke / "models").mkdir()
    (smoke / "checkpoints" / "epoch.pt").write_bytes(b"z" * 4096)
    (smoke / "models" / "model.model").write_bytes(b"m" * 2048)
    (smoke / "training.stderr.log").write_text("diagnostic tail\n", encoding="utf-8")

    orphan = store.external_record_directory / "orphan.json"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text("{}", encoding="utf-8")
    import os, time
    old = time.time() - 24 * 3600
    os.utime(orphan, (old, old))

    report = campaign_cli._campaign_cleanup(
        cfg,
        paths,
        store,
        phase="test",
        include_preparation_caches=True,
    )
    assert report.reclaimed_bytes >= 8 * 1024
    assert not frame_cache.exists()
    assert not data7_cache.exists()
    assert not orphan.exists()
    assert (smoke / "training.stderr.log").is_file()
    assert (smoke / "retained-diagnostic.json").is_file()
    assert not (smoke / "checkpoints").exists()
    assert not (smoke / "models").exists()


def test_shipped_campaign_example_matches_two_seed_default() -> None:
    text = (Path(__file__).resolve().parents[1] / "campaign.toml.example").read_text(encoding="utf-8")
    multi = text[text.index("[training.multihead_replay]") : text.index("[runtime]")]
    assert "enabled = true" in multi
    assert "seeds = [1, 2]" in multi
    assert "2 * (3 + 1) = 8" in multi
    naive = text[text.index("[training.naive_fine_tuning]") : text.index("[training.multihead_replay]")]
    assert "enabled = false" in naive
    assert "seeds = [1, 2]" in naive


def test_mlcv_select1_resolves_r_full_through_promoted_data8_runtime() -> None:
    import inspect

    source = inspect.getsource(campaign_cli._command_evaluate_mlcv_select1)
    assert "_resolve_data8_runtime_member(" in source
    assert "bundle, root, replay_full_artifact.path" in source
    assert "Path(replay_full_artifact.path)" not in source


def test_extend_seed_parser_and_config_edit_preserve_existing_fold_policy(tmp_path: Path) -> None:
    config = tmp_path / "campaign.toml"
    config.write_text(campaign_cli._config_template(
        workspace="work", training_root="training", foundation_model="foundation.model",
        replay_train="train.xyz", replay_monitor="monitor.xyz",
    ), encoding="utf-8")
    cfg, _ = campaign_cli._load_config(config)
    method = campaign_cli._method_spec_by_mode(cfg, "multihead_replay")
    assert method.seeds == (1, 2)
    assert method.seed_mode == "optimizer_only"
    assert method.cross_validation_folds == 3
    before, after = campaign_cli._replace_method_seed_array(
        config, mode="multihead_replay", expected_existing=method.seeds, new_seed=3
    )
    assert before != after
    cfg2, _ = campaign_cli._load_config(config)
    multi = campaign_cli._method_spec_by_mode(cfg2, "multihead_replay")
    naive = campaign_cli._method_spec_by_mode(
        {
            **cfg2,
            "training": {
                **cfg2["training"],
                "naive_fine_tuning": {**cfg2["training"]["naive_fine_tuning"], "enabled": True},
            },
        },
        "naive_fine_tuning",
    )
    assert multi.seeds == (1, 2, 3)
    assert multi.cross_validation_folds == 3
    assert multi.fold_partition_seed == 104729
    assert naive.seeds == (1, 2)
    parsed = campaign_cli.build_parser().parse_args(["extend-seed", "--seed", "3"])
    assert parsed.func is campaign_cli.command_extend_seed
    assert parsed.seed == 3


def test_same_fold_extension_rejects_changed_role_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    def entry(seed: int, role_digest: str):
        return SimpleNamespace(
            variant_id=f"multihead_replay-n512-seed{seed}",
            bundle=SimpleNamespace(mlcv_role_catalog=SimpleNamespace(content_digest=role_digest)),
        )

    monkeypatch.setattr(
        campaign_core, "_current_data8_entries",
        lambda store: [entry(1, "a" * 64), entry(2, "a" * 64), entry(4, "b" * 64)],
    )
    with pytest.raises(campaign_cli.CampaignCliError, match="same-fold requirement"):
        campaign_core._assert_seed_extension_same_folds(
            object(), mode="multihead_replay", selection_size=512, seed=4, parent_seeds=(1, 2)
        )


def test_same_fold_extension_accepts_identical_role_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    def entry(seed: int):
        return SimpleNamespace(
            variant_id=f"multihead_replay-n512-seed{seed}",
            bundle=SimpleNamespace(mlcv_role_catalog=SimpleNamespace(content_digest="a" * 64)),
        )

    monkeypatch.setattr(campaign_core, "_current_data8_entries", lambda store: [entry(1), entry(2), entry(4)])
    campaign_core._assert_seed_extension_same_folds(
        object(), mode="multihead_replay", selection_size=512, seed=4, parent_seeds=(1, 2)
    )


def test_extend_seed_orchestrates_only_new_seed_and_rebuilds_final1(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from types import SimpleNamespace

    config = tmp_path / "campaign.toml"
    legacy_text = campaign_cli._config_template(
        workspace="work", training_root="training", foundation_model="foundation.model",
        replay_train="train.xyz", replay_monitor="monitor.xyz",
    )
    # This fixture exercises the historical MLCV seed-extension lifecycle.  New
    # campaign templates are TRAIN2A by default, so make the historical authority
    # explicit rather than asking seed extension to reinterpret a new-policy file.
    legacy_text = legacy_text.replace('policy_generation = "train2"\n', '')
    legacy_text = legacy_text.replace(
        'checkpoint_strategy = "train2_target_first"',
        'checkpoint_strategy = "mlcv_nested_cv"',
    )
    config.write_text(legacy_text, encoding="utf-8")

    mode = SimpleNamespace(value="multihead_replay")
    parent_runs = tuple(
        SimpleNamespace(training_mode=mode, selection_size=512, seed=seed, run_id=f"run-seed{seed}")
        for seed in (1, 2)
    )
    parent_campaign = SimpleNamespace(content_digest="a" * 64, runs=parent_runs)
    parent_committee = SimpleNamespace(
        campaign_plan_digest=parent_campaign.content_digest,
        content_digest="b" * 64,
        members=tuple(SimpleNamespace(seed=seed) for seed in (1, 2)),
    )
    parent_selection = SimpleNamespace(
        campaign_plan_digest=parent_campaign.content_digest,
        content_digest="c" * 64,
    )
    parent_cv = SimpleNamespace(content_digest="d" * 64)

    class FakeStore:
        def __init__(self) -> None:
            self.records = {
                "training_campaign": parent_campaign,
                "mlcv_final_committee": parent_committee,
                "mlcv_final_selection": parent_selection,
                "mlcv_campaign_cv": parent_cv,
            }
            for run in parent_runs:
                self.records[f"execution:{run.run_id}"] = SimpleNamespace(
                    state=mdstats.TrainingRunState.SUCCEEDED
                )
            self.stages = {}
            self.meta = {}

        def get_record(self, key, cls=None):
            return self.records[key]

        def get_record_optional(self, key, cls=None):
            return self.records.get(key)

        def put_record(self, key, value):
            self.records[key] = value

        def get_payload_optional(self, key):
            value = self.records.get(key)
            return value if isinstance(value, dict) else None

        def get_payload(self, key):
            return self.records[key]

        def has_record(self, key):
            return key in self.records

        def record_keys(self, prefix=""):
            return tuple(sorted(key for key in self.records if key.startswith(prefix)))

        def delete_record(self, key):
            self.records.pop(key, None)

        def event(self, *args, **kwargs):
            return None

        def set_stage(self, name, state, message):
            self.stages[name] = (state, message)

        def set_meta(self, key, value):
            self.meta[key] = value

    store = FakeStore()
    monkeypatch.setattr(campaign_core, "CampaignStore", lambda path: store)
    monkeypatch.setattr(campaign_core, "_reopen_mlcv_authority_for_seed_extension", lambda *a, **k: None)
    monkeypatch.setattr(campaign_core, "_assert_seed_extension_same_folds", lambda *a, **k: None)
    monkeypatch.setattr(campaign_core, "command_doctor", lambda args: 0)
    monkeypatch.setattr(campaign_core, "command_prepare", lambda args: 0)
    monkeypatch.setattr(campaign_core, "command_preflight", lambda args: 0)

    captured = {}

    def fake_train(args):
        captured["train"] = args
        child_runs = parent_runs + (SimpleNamespace(
            training_mode=mode, selection_size=512, seed=3, run_id="run-seed3"
        ),)
        store.records["training_campaign"] = SimpleNamespace(
            content_digest="e" * 64, runs=child_runs
        )
        return 0

    def fake_evaluate(args):
        captured["evaluate"] = args
        child = store.records["training_campaign"]
        candidate = SimpleNamespace(seed=3, qualified=True, rejection_reasons=())
        store.records["mlcv_final_selection"] = SimpleNamespace(
            content_digest="f" * 64,
            campaign_plan_digest=child.content_digest,
            candidates=(candidate,),
        )
        store.records["mlcv_final_committee"] = SimpleNamespace(
            content_digest="1" * 64,
            campaign_plan_digest=child.content_digest,
            members=tuple(SimpleNamespace(seed=seed) for seed in (1, 2, 3)),
        )
        return 0

    monkeypatch.setattr(campaign_core, "command_train", fake_train)
    monkeypatch.setattr(campaign_core, "command_evaluate", fake_evaluate)

    result = campaign_core.command_extend_seed(SimpleNamespace(
        config=str(config), seed=3, training_mode=None, selection_size=None, dry_run=False
    ))
    assert result == 0
    assert captured["train"].seed == 3
    assert captured["train"].training_mode == "multihead_replay"
    assert captured["train"].selection_size == 512
    assert captured["train"].run_id is None
    assert captured["evaluate"].require_complete is True
    assert "seeds = [1, 2, 3]" in config.read_text(encoding="utf-8")
    extension = store.records["seed_extension:multihead_replay:n512:seed3"]
    assert extension["status"] == "complete_qualified"
    assert extension["admitted_to_committee"] is True


def test_seed_extension_freeze_guard_lists_frozen_authority(tmp_path: Path) -> None:
    store = campaign_cli.CampaignStore(tmp_path / "state.sqlite3")
    store.put_record("mlcv_verification", {"schema": "test.v1"})
    store.put_record("protocol_freeze", {"schema": "test.freeze.v1"})
    assert campaign_cli._seed_extension_forbidden_authority(store) == (
        "mlcv_verification", "protocol_freeze"
    )


def test_reopen_seed_extension_archives_campaign_level_authority_only(tmp_path: Path) -> None:
    store = campaign_cli.CampaignStore(tmp_path / "state.sqlite3")

    class ParentCampaign:
        content_digest = "a" * 64
        def to_dict(self):
            return {"schema": "parent-campaign.test.v1", "content_digest": self.content_digest}

    parent = ParentCampaign()
    store.put_record("mlcv_lifecycle_authority", {"schema": "life.test.v1", "content_digest": "b" * 64})
    store.put_record("mlcv_seed_cv:old", {"schema": "seed.test.v1", "content_digest": "c" * 64})
    store.put_record("mlcv_campaign_cv", {"schema": "cv.test.v1", "content_digest": "d" * 64})
    store.put_record("mlcv_final_selection", {"schema": "final.test.v1", "content_digest": "e" * 64})
    store.put_record("mlcv_final_committee", {"schema": "committee.test.v1", "content_digest": "f" * 64})
    store.put_record("mlcv_final_committee_member:seed1", {"schema": "member.test.v1", "content_digest": "1" * 64})
    store.put_record("mlcv_run_selection:run1", {"schema": "select.test.v1", "content_digest": "2" * 64})
    store.put_record("mlcv_outer_fold:run1", {"schema": "outer.test.v1", "content_digest": "3" * 64})

    campaign_cli._reopen_mlcv_authority_for_seed_extension(
        store, extension_id="multihead_replay-n512-seed4", parent_campaign=parent
    )

    for key in (
        "mlcv_lifecycle_authority", "mlcv_seed_cv:old", "mlcv_campaign_cv",
        "mlcv_final_selection", "mlcv_final_committee", "mlcv_final_committee_member:seed1",
    ):
        assert not store.has_record(key)
    assert store.has_record("mlcv_run_selection:run1")
    assert store.has_record("mlcv_outer_fold:run1")
    assert store.has_record("historical_training_campaign:" + parent.content_digest)
    assert len(store.record_keys("historical_seed_extension:")) == 6
