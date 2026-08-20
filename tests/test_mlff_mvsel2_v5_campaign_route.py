from __future__ import annotations

from mdstats.training_data import campaign_cli


def test_campaign_facade_installs_v5_single_owner_selection_runtime() -> None:
    selection = campaign_cli._ensure_target_multi_view_selection_v2
    assert selection.__module__.endswith("mvsel2_v5_runtime")
    source = open(campaign_cli.__file__, encoding="utf-8").read()
    assert "choose_target_multi_view_phase_a_candidate_v2 =" not in source
    assert "build_target_multi_view_lazy_frontier_v2 =" not in source
