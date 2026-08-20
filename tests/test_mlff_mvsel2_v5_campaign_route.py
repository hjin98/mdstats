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


def test_v5_runtime_routes_existing_query_worker_budget_to_selector() -> None:
    resources = object()
    core = SimpleNamespace(
        _target_coverage_query_workers=lambda cfg: (12, resources),
    )
    workers, actual_resources = mvsel2_v5_runtime._selection_worker_budget(
        core, {}
    )
    assert workers == 12
    assert actual_resources is resources


def test_v5_runtime_caps_selector_workers_at_qualified_ceiling() -> None:
    resources = object()
    core = SimpleNamespace(
        _target_coverage_query_workers=lambda cfg: (28, resources),
    )
    workers, actual_resources = mvsel2_v5_runtime._selection_worker_budget(
        core, {}
    )
    assert workers == 16
    assert actual_resources is resources


def test_v5_runtime_source_does_not_hardcode_serial_selector() -> None:
    source = open(mvsel2_v5_runtime.__file__, encoding="utf-8").read()
    assert "workers=selector_workers" in source
    assert "workers=1,\n            checkpoint_callback" not in source
