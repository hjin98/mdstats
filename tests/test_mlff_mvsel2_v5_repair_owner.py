from __future__ import annotations

from pathlib import Path

from mdstats.training_data import campaign_cli
from mdstats.training_data import mvsel2_hardening_runtime as runtime


def test_g3_campaign_has_no_repair_monkeypatch_or_duplicate_runtime_import() -> None:
    source = Path(campaign_cli.__file__).read_text(encoding="utf-8")
    assert "mvsel2_repair_checkpoint_runtime" not in source
    assert "_build_repair_from_checkpoints =" not in source
    assert "repair_rung_from_authenticated_state" not in source


def test_g3_runtime_contains_no_repair_science_loop() -> None:
    source = Path(runtime.__file__).read_text(encoding="utf-8")
    forbidden = (
        "_RepairProposalScratchV2",
        "_repair._proposal(",
        "_repair._better(",
        "deselect_target_multi_view_candidate_v2",
        "score_target_multi_view_candidate_v2",
        "select_target_multi_view_candidate_v2",
        "for pass_index in range(policy.max_passes_per_shell)",
    )
    for token in forbidden:
        assert token not in source
    assert "_repair.build_target_multi_view_repair_plan_v2(" in source


def test_g3_compatibility_repair_facade_delegates_to_canonical_owner(monkeypatch) -> None:
    sentinel = object()
    captured: dict[str, object] = {}

    def canonical(reference, forward, selection, **kwargs):
        captured["reference"] = reference
        captured["forward"] = forward
        captured["selection"] = selection
        captured["kwargs"] = kwargs
        return sentinel

    monkeypatch.setattr(
        runtime._repair,
        "build_target_multi_view_repair_plan_v2",
        canonical,
    )
    reference = object()
    forward = object()
    selection = object()
    policy = object()
    progress: list[str] = []
    result = runtime._build_repair_from_checkpoints(
        reference,
        forward,
        selection,
        policy=policy,
        checkpoint_states={"target": {128: object()}},
        progress_callback=progress.append,
    )
    assert result is sentinel
    assert captured["reference"] is reference
    assert captured["forward"] is forward
    assert captured["selection"] is selection
    kwargs = captured["kwargs"]
    assert kwargs["policy"] is policy
    assert kwargs["workers"] == 1
    assert callable(kwargs["progress_callback"])
    kwargs["progress_callback"]("status=rung; selected_prefix_state_mode=selected_prefix_forward_replay")
    assert progress == [
        "status=rung; selected_prefix_state_mode=selected_prefix_forward_replay; "
        "mvstate2_restore_count=0"
    ]


def test_g3_production_repair_path_does_not_discover_selector_checkpoints() -> None:
    source = Path(runtime.__file__).read_text(encoding="utf-8")
    ensure_source = source.split("def _ensure_target_multi_view_repair_v2", 1)[1]
    ensure_source = ensure_source.split("def install_campaign_hardening", 1)[0]
    assert "_all_valid_rung_states(" not in ensure_source
    assert "checkpoint_states" not in ensure_source
    assert "build_target_multi_view_repair_plan_v2(" in ensure_source
