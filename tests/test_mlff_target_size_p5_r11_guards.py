"""Revision-11 guards for P5 evaluation-provider lifetime and ordering."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import mdstats.training_data.campaign_post_selection_runtime as runtime
import mdstats.training_data.eval2 as eval2
import mdstats.training_data.post_selection_execution as execution
from mdstats.training_data._common import sha256_file_cached
from mdstats.training_data.post_selection_execution import (
    DATASET_ROLE_CHECKPOINT_MONITOR,
    DATASET_ROLE_OUTER_EVALUATION,
)


def _digest(value: str) -> str:
    return value * 64


class _RecordingProvider:
    def __init__(self, name: str, events: list[str]) -> None:
        self.name = name
        self.closed = False
        self._events = events

    def close(self) -> None:
        self._events.append(f"close:{self.name}")
        self.closed = True


class _RecordingStore:
    def __init__(self) -> None:
        self.values: list[object] = []

    def put(self, value: object) -> None:
        self.values.append(value)


def _lifecycle_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    events: list[str],
    *,
    replay_enabled: bool = True,
    failure_role: str | None = None,
    fail_foundation_construction: bool = False,
):
    replay_monitor = tmp_path / "replay-monitor.extxyz"
    replay_monitor.write_bytes(b"bounded TRUE_DFT replay monitor")
    replay_monitor_artifact = SimpleNamespace(
        sha256=sha256_file_cached(replay_monitor),
        content_digest=_digest("1"),
        configuration_count=1,
    )
    replay_resolution = SimpleNamespace(
        train_path=str(tmp_path / "replay-train.extxyz"),
        monitor_path=str(replay_monitor),
        train_artifact=SimpleNamespace(),
        monitor_artifact=replay_monitor_artifact,
    )
    target_artifact = SimpleNamespace()
    outer_artifact = SimpleNamespace()

    preparation = SimpleNamespace(
        membership=("train-frame",),
        content_digest=_digest("2"),
    )
    materialization = SimpleNamespace(
        content_digest=_digest("3"),
        checkpoint_monitor_artifact=target_artifact,
        outer_evaluation_artifact=outer_artifact,
    )
    run_plan = SimpleNamespace(
        run_identity=_digest("4"),
        run_role="cv",
        content_digest=_digest("4"),
        optimizer_seed=17,
        planned_epochs=3,
    )
    runtime_plan = SimpleNamespace(content_digest=_digest("5"))
    summary = SimpleNamespace(
        plan_digest=runtime_plan.content_digest,
        content_digest=_digest("6"),
    )
    point = SimpleNamespace(checkpoint_sha256=_digest("7"))
    checkpoint = SimpleNamespace(relative_path="checkpoint.pt", sha256=_digest("7"))

    providers: list[_RecordingProvider] = []
    foundations: list[_RecordingProvider] = []

    def run_root(identity: str) -> Path:
        root = tmp_path / "runs" / identity
        root.mkdir(parents=True, exist_ok=True)
        return root

    def authenticate(**_kwargs):
        provider = _RecordingProvider(f"provider-{len(providers) + 1}", events)
        providers.append(provider)
        return provider, True

    def evaluate(*, dataset_role, provider, **_kwargs):
        events.append(f"evaluate:{dataset_role}:{provider.name}")
        if provider.closed:
            raise AssertionError(
                f"provider {provider.name} was closed before {dataset_role}"
            )
        if dataset_role == failure_role:
            raise RuntimeError(f"evaluation failure {dataset_role}")
        return SimpleNamespace(
            content_digest=_digest("8"),
            force_component_rmse_ev_per_angstrom=0.1,
        )

    def build_foundation(**_kwargs):
        if any(not provider.closed for provider in providers):
            raise AssertionError(
                "foundation provider constructed while a candidate provider was open"
            )
        events.append("construct:foundation")
        if fail_foundation_construction:
            raise RuntimeError("foundation construction failure")
        provider = _RecordingProvider("foundation", events)
        foundations.append(provider)
        return provider

    monkeypatch.setattr(
        runtime,
        "_resolve_post_selection_replay_resolution",
        lambda *_args, **_kwargs: replay_resolution,
    )
    monkeypatch.setattr(
        runtime,
        "_optimizer_policy_for",
        # The accepted execution policy also owns the evaluation device-batch
        # bound; a stand-in that omits it is not standing in for the real thing.
        lambda *_args, **_kwargs: SimpleNamespace(
            policy_digest=_digest("9"), valid_batch_size=4
        ),
    )
    monkeypatch.setattr(
        runtime,
        "materialize_post_selection_run",
        lambda *_args, **_kwargs: (preparation, materialization),
    )
    monkeypatch.setattr(
        runtime,
        "post_selection_runtime_plan",
        lambda **_kwargs: runtime_plan,
    )
    monkeypatch.setattr(
        runtime,
        "post_selection_checkpoint_candidates",
        lambda **_kwargs: (point,),
    )
    monkeypatch.setattr(
        runtime,
        "_checkpoint_catalog",
        lambda *_args, **_kwargs: SimpleNamespace(
            checkpoint_by_sha256=lambda _sha256: checkpoint
        ),
    )
    monkeypatch.setattr(runtime, "_component_block_ids", lambda *_args: ("block",))
    monkeypatch.setattr(runtime, "authenticate_post_selection_provider", authenticate)
    monkeypatch.setattr(runtime, "evaluate_post_selection_dataset", evaluate)
    monkeypatch.setattr(
        runtime,
        "select_cv_fold_representative",
        lambda records, **_kwargs: records[0],
    )
    monkeypatch.setattr(
        eval2,
        "assess_eval2_checkpoint",
        lambda point, **_kwargs: SimpleNamespace(
            stable_candidate_identity="candidate",
            trajectory_point=point,
            content_digest=_digest("a"),
        ),
    )
    monkeypatch.setattr(
        execution,
        "build_post_selection_foundation_baseline_provider",
        build_foundation,
    )

    context = SimpleNamespace(
        selected=SimpleNamespace(),
        method=SimpleNamespace(),
        method_policies=SimpleNamespace(
            extxyz=SimpleNamespace(),
            checkpoint_admissibility=SimpleNamespace(replay_enabled=replay_enabled),
            checkpoint_selection=SimpleNamespace(),
            training_mode="multihead_replay",
            mace_architecture=SimpleNamespace(),
            learning_rate_schedule=SimpleNamespace(),
            target_head_name="target_head",
            replay_head_name="pt_head",
            foundation_potential_identity=SimpleNamespace(
                canonical_content_digest=_digest("b")
            ),
            foundation_model=str(tmp_path / "foundation.model"),
            foundation_head="default",
            common_training=SimpleNamespace(
                eval2_metric_policy_digest=_digest("c"),
                default_dtype="float64",
            ),
            device="cpu",
        ),
        inference_evaluator=None,
        trainer=lambda request: summary,
        _baseline_replay_cache={},
        run_root=run_root,
        evidence_store=_RecordingStore(),
    )
    budget_policy = SimpleNamespace()
    return (
        context,
        run_plan,
        budget_policy,
        providers,
        foundations,
        replay_resolution,
    )


def _run_fixture(
    context,
    run_plan,
    budget_policy,
    *,
    outer: bool = False,
):
    return runtime.execute_post_selection_run(
        context,
        run_plan=run_plan,
        budget_policy=budget_policy,
        training_frame_uids=("train",),
        monitor_frame_uids=("monitor",),
        outer_evaluation_frame_uids=("outer",) if outer else None,
    )


def test_r11_candidate_closes_before_foundation_and_outer_is_exception_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    events: list[str] = []
    context, run_plan, budget, providers, foundations, _resolution = _lifecycle_fixture(
        tmp_path, monkeypatch, events
    )

    _run_fixture(context, run_plan, budget, outer=True)

    assert events == [
        f"evaluate:{DATASET_ROLE_CHECKPOINT_MONITOR}:provider-1",
        "evaluate:replay_monitor:provider-1",
        "close:provider-1",
        "construct:foundation",
        "evaluate:replay_monitor_baseline:foundation",
        "close:foundation",
        f"evaluate:{DATASET_ROLE_OUTER_EVALUATION}:provider-2",
        "close:provider-2",
    ]
    assert providers[0].closed
    assert providers[1].closed
    assert foundations[0].closed


def test_r11_candidate_closes_after_target_only_evaluation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    events: list[str] = []
    context, run_plan, budget, providers, foundations, _resolution = _lifecycle_fixture(
        tmp_path,
        monkeypatch,
        events,
        replay_enabled=False,
    )

    _run_fixture(context, run_plan, budget)

    assert events == [
        f"evaluate:{DATASET_ROLE_CHECKPOINT_MONITOR}:provider-1",
        "close:provider-1",
    ]
    assert providers[0].closed
    assert not foundations


def test_r11_baseline_cache_hit_does_not_construct_or_cache_a_live_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    events: list[str] = []
    context, run_plan, budget, providers, foundations, _resolution = _lifecycle_fixture(
        tmp_path, monkeypatch, events
    )

    _run_fixture(context, run_plan, budget)
    _run_fixture(context, run_plan, budget)

    assert events.count("construct:foundation") == 1
    assert len(foundations) == 1
    assert len(context._baseline_replay_cache) == 1
    assert all(provider.closed for provider in providers)
    assert foundations[0].closed


@pytest.mark.parametrize(
    "failure_role",
    (
        DATASET_ROLE_CHECKPOINT_MONITOR,
        "replay_monitor",
        "replay_monitor_baseline",
        DATASET_ROLE_OUTER_EVALUATION,
    ),
)
def test_r11_provider_cleanup_preserves_evaluation_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_role: str,
):
    events: list[str] = []
    context, run_plan, budget, providers, foundations, _resolution = _lifecycle_fixture(
        tmp_path,
        monkeypatch,
        events,
        failure_role=failure_role,
    )

    with pytest.raises(RuntimeError, match=f"evaluation failure {failure_role}"):
        _run_fixture(
            context,
            run_plan,
            budget,
            outer=failure_role == DATASET_ROLE_OUTER_EVALUATION,
        )

    assert providers
    assert all(provider.closed for provider in providers)
    if failure_role in {"replay_monitor_baseline", DATASET_ROLE_OUTER_EVALUATION}:
        assert foundations and foundations[0].closed
    else:
        assert not foundations


def test_r11_foundation_construction_failure_propagates_after_candidate_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    events: list[str] = []
    context, run_plan, budget, providers, foundations, _resolution = _lifecycle_fixture(
        tmp_path,
        monkeypatch,
        events,
        fail_foundation_construction=True,
    )

    with pytest.raises(RuntimeError, match="foundation construction failure"):
        _run_fixture(context, run_plan, budget)

    assert events == [
        f"evaluate:{DATASET_ROLE_CHECKPOINT_MONITOR}:provider-1",
        "evaluate:replay_monitor:provider-1",
        "close:provider-1",
        "construct:foundation",
    ]
    assert providers[0].closed
    assert not foundations
