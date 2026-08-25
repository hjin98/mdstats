from __future__ import annotations

"""Bounded production-orchestration integration for PERF1 resource ownership."""

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
