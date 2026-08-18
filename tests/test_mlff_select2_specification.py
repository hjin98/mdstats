from __future__ import annotations

import inspect
from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli


def test_select2_is_public_versioned_and_documented() -> None:
    assert mdstats.__version__ == "0.20.180a0"
    assert mdstats.SELECT2_VERSION == "0.20.176a0"
    assert hasattr(mdstats, "Select2SelectionRecord")
    assert hasattr(mdstats, "Select2FrozenCandidateRecord")
    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "arch_manuals" / "mlff_training_data_architecture.md").read_text(encoding="utf-8")
    assert "SELECT2 is implemented in `mdstats 0.20.176a0`" in text
    assert "Implementation status (`0.20.176a0`): complete" in text


def test_dyn_production_handoff_executes_select2_not_a_placeholder() -> None:
    source = inspect.getsource(campaign_cli._finalize_train2_dyn)
    assert "_command_verify_train2_select2" in source
    assert "SELECT2 is the next production-selection gate" not in source


def test_select2_freezes_static_order_before_physical_filter_and_stops_before_locked_test() -> None:
    core = inspect.getsource(mdstats.build_select2_selection)
    cli = inspect.getsource(campaign_cli._command_verify_train2_select2)
    assert "static_order" in core
    assert "physical_qualified" in core
    assert "fallback_count" in core
    assert "models" in cli and "select2-frozen" in cli
    assert "locked post-freeze test" in cli
    assert "StageState.WAITING" in cli


def test_select2_has_no_replay_or_rollout_metric_ranking_inputs() -> None:
    core = inspect.signature(mdstats.build_select2_selection)
    assert "replay" not in str(core).lower()
    source = inspect.getsource(mdstats.build_select2_selection)
    assert "order_eval2_admissible_candidates" in source
    assert "case_metrics" not in source
    assert "replay_degradation" not in source
