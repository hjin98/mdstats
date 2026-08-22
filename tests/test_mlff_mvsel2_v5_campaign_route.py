from __future__ import annotations

from types import SimpleNamespace

from mdstats.training_data import campaign_cli
from mdstats.training_data import mvsel2_v5_runtime


def test_campaign_facade_installs_v5_single_owner_selection_runtime() -> None:
    selection = campaign_cli._ensure_target_multi_view_selection_v2
    assert selection.__module__.endswith("mvsel2_v5_runtime")
    source = open(campaign_cli.__file__, encoding="utf-8").read()
    assert "choose_target_multi_view_phase_a_candidate_v2 =" not in source
    assert "build_target_multi_view_lazy_frontier_v2 =" not in source


def test_v5_runtime_uses_runtime_cpu_budget_as_selector_ceiling() -> None:
    resources = SimpleNamespace(cpu_threads_budget=28)
    captured = {}

    def detect_system_resources(**kwargs):
        captured.update(kwargs)
        return resources

    core = SimpleNamespace(
        detect_system_resources=detect_system_resources,
        _cfg=lambda cfg, section, key, default: cfg.get(section, {}).get(key, default),
    )
    workers, actual_resources = mvsel2_v5_runtime._selection_worker_budget(
        core, {"performance": {"cpu_fraction": 0.90}}
    )
    assert workers == 28
    assert actual_resources is resources
    assert captured["cpu_fraction"] == 0.90
    assert captured["device"] == "cpu"


def test_v5_runtime_does_not_borrow_target_coverage_worker_policy() -> None:
    resources = SimpleNamespace(cpu_threads_budget=57)
    core = SimpleNamespace(
        detect_system_resources=lambda **kwargs: resources,
        _cfg=lambda cfg, section, key, default: default,
        _target_coverage_query_workers=lambda cfg: (_ for _ in ()).throw(
            AssertionError("MVSEL2 must not use cKDTree worker policy")
        ),
    )
    workers, actual_resources = mvsel2_v5_runtime._selection_worker_budget(core, {})
    assert workers == 57
    assert actual_resources is resources


def test_v5_runtime_preflight_uses_best_qualified_parallel_worker_count(
    monkeypatch,
) -> None:
    state = object()
    forward = SimpleNamespace(domain=lambda domain_id: ("forward", domain_id))
    result = SimpleNamespace(
        scaling_passed=True,
        effective_workers=8,
    )
    monkeypatch.setattr(
        mvsel2_v5_runtime,
        "preflight_mvsel2_native_workers_v2",
        lambda domain, actual_state, max_workers: result,
    )
    monkeypatch.setattr(
        mvsel2_v5_runtime,
        "format_mvsel2_native_preflight_v2",
        lambda value: "meter",
    )
    assert (
        mvsel2_v5_runtime._preflight_selection_workers(
            forward,
            {"target": state},
            requested_workers=16,
        )
        == 8
    )


def test_v5_runtime_preflight_falls_back_to_g4b_when_scaling_fails(
    monkeypatch,
) -> None:
    state = object()
    forward = SimpleNamespace(domain=lambda domain_id: ("forward", domain_id))
    result = SimpleNamespace(
        scaling_passed=False,
        effective_workers=1,
    )
    monkeypatch.setattr(
        mvsel2_v5_runtime,
        "preflight_mvsel2_native_workers_v2",
        lambda domain, actual_state, max_workers: result,
    )
    monkeypatch.setattr(
        mvsel2_v5_runtime,
        "format_mvsel2_native_preflight_v2",
        lambda value: "meter",
    )
    assert (
        mvsel2_v5_runtime._preflight_selection_workers(
            forward,
            {"target": state},
            requested_workers=16,
        )
        == 1
    )


def test_v5_runtime_source_does_not_hardcode_serial_selector() -> None:
    source = open(mvsel2_v5_runtime.__file__, encoding="utf-8").read()
    assert "workers=selector_workers" in source
    assert "workers=1,\n            checkpoint_callback" not in source


def test_mvsel2_preflight_worker_points_include_runtime_endpoint() -> None:
    assert mvsel2_v5_runtime.preflight_mvsel2_native_workers_v2 is not None
    from mdstats.training_data.mvsel2_native_preflight import _worker_counts

    assert _worker_counts(28) == (1, 2, 4, 8, 16, 28)
    assert _worker_counts(32) == (1, 2, 4, 8, 16, 32)
    assert _worker_counts(57) == (1, 2, 4, 8, 16, 32, 57)
