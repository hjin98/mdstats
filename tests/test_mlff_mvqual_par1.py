from __future__ import annotations

from threading import Lock
from pathlib import Path
import time

import pytest

import mdstats
from mdstats.training_data import campaign_cli
from mdstats.training_data import target_multi_view_qualification as mvqual
from mdstats.training_data.resources import StageResourceScope
from tests.test_mlff_target_data2c_mvqual1 import _authorities


def test_mvqual_par1_worker_counts_preserve_complete_plan() -> None:
    reference, role, feasibility, sparse, _, repair, legacy, policy = _authorities(160)
    plans = [
        mdstats.build_target_multi_view_qualification_plan(
            reference, sparse, feasibility, role, legacy, repair,
            policy=policy, scoring_workers=workers,
        )
        for workers in (1, 2, 4)
    ]
    assert plans[0].to_dict() == plans[1].to_dict() == plans[2].to_dict()


def test_mvqual_par1_parallel_jobs_are_concurrent_and_native_tree_single_threaded(monkeypatch) -> None:
    reference, role, feasibility, sparse, _, repair, legacy, policy = _authorities(160)
    original = mvqual.score_target_subset_coverage
    lock = Lock()
    active = 0
    max_active = 0
    observed_query_workers: list[int] = []

    def wrapped(*args, **kwargs):
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
            observed_query_workers.append(int(kwargs["query_workers"]))
        try:
            time.sleep(0.015)
            return original(*args, **kwargs)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(mvqual, "score_target_subset_coverage", wrapped)
    plan = mdstats.build_target_multi_view_qualification_plan(
        reference, sparse, feasibility, role, legacy, repair,
        policy=policy, coverage_query_workers=4, scoring_workers=4,
    )
    assert plan.global_common_target_sizes == (4, 8, 16, 32)
    assert max_active >= 2
    assert observed_query_workers
    assert set(observed_query_workers) == {1}


def test_mvqual_par1_progress_reduction_remains_canonical() -> None:
    reference, role, feasibility, sparse, _, repair, legacy, policy = _authorities(160)
    serial_messages: list[str] = []
    parallel_messages: list[str] = []
    serial = mdstats.build_target_multi_view_qualification_plan(
        reference, sparse, feasibility, role, legacy, repair,
        policy=policy, scoring_workers=1, progress_callback=serial_messages.append,
    )
    parallel = mdstats.build_target_multi_view_qualification_plan(
        reference, sparse, feasibility, role, legacy, repair,
        policy=policy, scoring_workers=4, progress_callback=parallel_messages.append,
    )
    assert parallel.content_digest == serial.content_digest
    # Worker count is execution telemetry, not scientific output. Canonical
    # scientific progress remains identical after removing that field.
    normalize = lambda message: message.replace("workers=4", "workers=1")
    assert [normalize(item) for item in parallel_messages] == serial_messages


def test_mvqual_par1_rejects_undersized_explicit_scope() -> None:
    reference, role, feasibility, sparse, _, repair, legacy, policy = _authorities(80)
    scope = StageResourceScope(
        stage_name="mvqual-test",
        cpu_threads_available=4,
        cpu_threads_budget=2,
        python_workers=2,
        structural_workers=1,
        tree_workers=1,
        blas_threads=1,
        pytorch_cpu_workers=1,
        ram_budget_bytes=None,
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="fewer Python workers"):
        mdstats.build_target_multi_view_qualification_plan(
            reference, sparse, feasibility, role, legacy, repair,
            policy=policy, scoring_workers=3, resource_scope=scope,
        )


def test_mvqual_par1_campaign_configuration_and_resolver_are_wired() -> None:
    source = Path(campaign_cli._core.__file__).read_text(encoding="utf-8")
    assert "target_multi_view_qualification_workers = 0" in source
    workers, resources = campaign_cli._target_multi_view_qualification_parallelism(
        {"performance": {"cpu_fraction": 0.90, "ram_fraction": 0.80,
                         "gpu_memory_fraction": 0.90,
                         "target_multi_view_qualification_workers": 2}}
    )
    assert 1 <= workers <= 2
    assert workers <= resources.cpu_threads_budget


def test_mvqual_par1_explicit_campaign_scope_preserves_blas1_authority_across_workers() -> None:
    reference, role, feasibility, sparse, _, repair, legacy, policy = _authorities(200)
    scope4 = StageResourceScope(
        stage_name="mvqual-campaign-test",
        cpu_threads_available=4,
        cpu_threads_budget=4,
        python_workers=4,
        structural_workers=1,
        tree_workers=1,
        blas_threads=1,
        pytorch_cpu_workers=1,
        ram_budget_bytes=None,
    )
    scope1 = StageResourceScope(
        stage_name="mvqual-campaign-test",
        cpu_threads_available=4,
        cpu_threads_budget=4,
        python_workers=1,
        structural_workers=1,
        tree_workers=1,
        blas_threads=1,
        pytorch_cpu_workers=1,
        ram_budget_bytes=None,
    )
    serial = mdstats.build_target_multi_view_qualification_plan(
        reference, sparse, feasibility, role, legacy, repair,
        policy=policy, coverage_query_workers=1, scoring_workers=1, resource_scope=scope1,
    )
    parallel = mdstats.build_target_multi_view_qualification_plan(
        reference, sparse, feasibility, role, legacy, repair,
        policy=policy, coverage_query_workers=1, scoring_workers=4, resource_scope=scope4,
    )
    assert parallel.to_dict() == serial.to_dict()
