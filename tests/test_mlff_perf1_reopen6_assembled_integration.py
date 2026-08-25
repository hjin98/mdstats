from __future__ import annotations

"""Bounded production-orchestration integration for PERF1 resource ownership."""

import json
from types import SimpleNamespace

import mdstats
from mdstats.training_data import _campaign_cli_core as campaign_cli


def test_reopen6_bounded_assembled_stage_chain_restarts_with_one_outer_owner(monkeypatch):
    """Exercise the real staged runner across the public PERF1 stage boundary.

    Expensive numerical backends are intentionally represented by tiny stage
    callbacks; resource ownership, plan propagation, ordering, and restart are
    provided by the production orchestrator rather than recreated here.
    """

    resources = SimpleNamespace(
        cpu_threads_available=4, cpu_fraction=0.9, cpu_threads_budget=3,
        ram_available_bytes=1 << 30, ram_fraction=0.8, ram_budget_bytes=1 << 29,
        gpu_memory_fraction=0.9,
        gpu=SimpleNamespace(available=False, budget_bytes=None, total_bytes=None,
                            free_bytes=None, device_name=None),
    )
    monkeypatch.setattr(campaign_cli, "detect_system_resources", lambda **_: resources)
    monkeypatch.setattr(campaign_cli, "query_gpu_telemetry", lambda *_: None)
    seen: list[str] = []

    def task(name: str):
        def prepare():
            return SimpleNamespace(execution_plan=mdstats.InferenceExecutionPlan(
                batch_policy="auto", selected_batch_size=1, maximum_batch_size=1
            ))
        def infer(prepared):
            assert prepared.execution_plan.provider_residency_ram_bytes is not None
            seen.append(name)
            return name
        return campaign_cli._StagedEvaluationTask(
            display_index=len(seen) + 1, key=name, label=name, start_detail=name,
            prepare=prepare, requires_inference=lambda _: True, infer=infer,
            finalize=lambda _, result: result, done_detail=lambda result, _: result,
        )

    stages = tuple(task(name) for name in (
        "preflight", "materialize", "train-eval", "deploy", "pes", "relax", "dyn", "publish"
    ))
    cfg = {"performance": {"cpu_fraction": 0.9, "ram_fraction": 0.8}, "execution": {
        "evaluation_estimated_ram_mib_per_job": 1.0,
        "parallel_evaluation_jobs": 1, "parallel_evaluation_prepare_jobs": 1,
        "parallel_evaluation_finalize_jobs": 1, "evaluation_pipeline_buffer_jobs": 2,
    }}
    first = campaign_cli._run_staged_evaluation_tasks(
        stages, cfg=cfg, phase="evaluation", device="cpu", progress=campaign_cli._ProgressReporter("INT", len(stages))
    )
    second = campaign_cli._run_staged_evaluation_tasks(
        stages, cfg=cfg, phase="evaluation", device="cpu", progress=campaign_cli._ProgressReporter("INT", len(stages))
    )
    assert tuple(first) == tuple(second) == tuple(name for name in (
        "preflight", "materialize", "train-eval", "deploy", "pes", "relax", "dyn", "publish"
    ))
    assert seen == list(first) + list(second)


def test_reopen7_campaign_state_and_canonical_static_profile_restart(tmp_path, monkeypatch):
    """Exercise real campaign state plus the production static-inference path.

    This is intentionally distinct from the scheduler-only test above.  It
    enters through the public campaign initializer, persists its runtime plan
    in the production SQLite state store, invokes the canonical model-on-atoms
    entrypoint, and performs a second invocation that discovers the durable
    runtime profile written by that entrypoint.  The model adapter is the only
    stubbed boundary; campaign state, runtime-plan wire format, profile
    persistence, and restart lookup remain production code.
    """
    import numpy as np
    from ase import Atoms

    from mdstats.training_data import campaign_execution, model_features, resources
    from mdstats.training_data.model_features import AtomicModelPrediction
    from mdstats.training_data.resources import GpuResourceSnapshot, SystemResourceSnapshot

    config = tmp_path / "campaign.toml"
    assert campaign_cli.main([
        "--config", str(config), "init", "--workspace", "work",
        "--training-root", "training", "--foundation-model", "foundation.model",
        "--replay-train", "replay-train.xyz", "--replay-monitor", "replay-monitor.xyz",
    ]) == 0
    _, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    plan = mdstats.InferenceExecutionPlan(
        batch_policy="auto", selected_batch_size=1, maximum_batch_size=2,
        selected_concurrent_model_jobs=2, provider_residency_ram_bytes=1,
    )
    plan_key = "inference_execution_plan:deploy:bounded-restart"
    store.put_record(plan_key, plan.to_dict())
    restored_plan = campaign_cli._evaluation_inference_execution_plan(
        {"evaluation": {"inference_batch_policy": "auto", "maximum_inference_batch_size": 2}},
        store=store,
        record_key=plan_key,
    )
    assert store.get_payload(plan_key)["schema"] == "mdstats.inference-execution-plan.v3"

    snapshot = SystemResourceSnapshot(
        cpu_threads_available=4, cpu_fraction=0.90, cpu_threads_budget=3,
        ram_available_bytes=1 << 30, ram_fraction=0.80, ram_budget_bytes=1 << 29,
        gpu_memory_fraction=0.90,
        gpu=GpuResourceSnapshot(False, 0, None, None, None, None, None, "cpu"),
    )
    monkeypatch.setattr(resources, "detect_system_resources", lambda **_: snapshot)

    class Provider:
        def set_head(self, head):
            pass

        def predict_batch(self, atoms, **_):
            return tuple(
                AtomicModelPrediction(
                    energy_ev=float(atom.positions[1, 2]),
                    forces_ev_per_angstrom=np.zeros((2, 3)),
                    stress_ev_per_angstrom3=np.zeros((3, 3)),
                )
                for atom in atoms
            )

        def close(self):
            pass

    monkeypatch.setattr(
        model_features.MaceCalculatorProvider,
        "from_model_path",
        classmethod(lambda cls, *args, **kwargs: Provider()),
    )
    original_authority = model_features.StaticInferenceRuntimeAuthority
    compatible_profiles = []

    class RecordingAuthority(original_authority):
        def __init__(self, *args, **kwargs):
            compatible_profiles.append(kwargs.get("compatible_profile"))
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(model_features, "StaticInferenceRuntimeAuthority", RecordingAuthority)
    model = tmp_path / "candidate.model"
    model.write_bytes(b"bounded-canonical-model")
    atoms = tuple(
        Atoms("H2", positions=[[0, 0, 0], [0, 0, 0.7 + 0.01 * index]])
        for index in range(8)
    )
    policy = mdstats.CheckpointEvaluationPolicy(
        condition_keys=(), device="cpu", default_dtype="float64"
    )
    graph_cache = paths.internal / "evaluation-graphs"
    first = campaign_execution._predict_model_on_atoms(
        model, atoms, head=None, policy=policy, execution_plan=restored_plan,
        provider=Provider(), graph_cache_directory=graph_cache,
    )
    profiles = tuple((paths.internal / "static-inference-runtime-profiles").glob("*.json"))
    assert len(profiles) == 1
    persisted = model_features.StaticInferenceRuntimeProfile.from_dict(
        json.loads(profiles[0].read_text(encoding="utf-8"))
    )
    assert persisted.to_dict()["schema"] == "mdstats.static-inference-runtime-profile.v6"
    second = campaign_execution._predict_model_on_atoms(
        model, atoms, head=None, policy=policy, execution_plan=restored_plan,
        provider=Provider(), graph_cache_directory=graph_cache,
    )

    assert [value.energy_ev for value in first] == [value.energy_ev for value in second]
    assert compatible_profiles == [None, persisted]
    assert campaign_cli.main(["--config", str(config), "status"]) == 0
