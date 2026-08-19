from __future__ import annotations

import sys
from pathlib import Path

from mdstats.training_data import target_multi_view_repair_v2 as repair_v2
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.mvsel2_repair_checkpoint_runtime import (
    build_repair_from_checkpoints,
)
from tests.test_mlff_mvsel2_hardening import (
    _all_valid_rung_states,
    _state_for_prefix,
    _v2_redundant_selection,
    _write_checkpoint,
)
from tests.test_mlff_repair2 import _trace

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import mvsel2_qualification_support as support


def _checkpoint_fixture(tmp_path):
    reference, _index, forward, selection = _v2_redundant_selection()
    store = CampaignStore(tmp_path / "campaign.sqlite3")
    for rung in selection.domain("target").rungs:
        if not rung.materializable:
            continue
        state = _state_for_prefix(
            reference.domain("target"),
            forward.domain("target"),
            selection.domain("target").master_order[: rung.target_size],
        )
        _write_checkpoint(
            store,
            reference,
            forward,
            selection.policy,
            rung.target_size,
            state,
        )
    checkpoint_states = _all_valid_rung_states(
        store, reference, forward, selection.policy
    )
    return reference, forward, selection, store, checkpoint_states


def test_shared_checkpoint_repair_is_trace_equivalent_to_canonical_repair(
    tmp_path,
) -> None:
    reference, forward, selection, store, checkpoint_states = _checkpoint_fixture(
        tmp_path
    )
    try:
        policy = repair_v2.TargetMultiViewRepairPolicyV2()
        canonical = repair_v2.build_target_multi_view_repair_plan_v2(
            reference, forward, selection, policy=policy
        )
        shared = build_repair_from_checkpoints(
            reference,
            forward,
            selection,
            policy=policy,
            checkpoint_states=checkpoint_states,
        )
        assert _trace(shared) == _trace(canonical)
        assert (
            shared.domain("target").repaired_master_order
            == canonical.domain("target").repaired_master_order
        )
    finally:
        store.close()


def test_checkpoint_repair_builder_skips_fresh_validation_when_checkpoints_cover_rungs(
    tmp_path, monkeypatch
) -> None:
    reference, forward, selection, store, checkpoint_states = _checkpoint_fixture(
        tmp_path
    )
    try:
        def forbidden(*_args, **_kwargs):
            raise AssertionError(
                "fresh full-domain validation must not run when compatible checkpoints exist"
            )

        monkeypatch.setattr(
            repair_v2, "build_target_multi_view_forward_state_v2", forbidden
        )
        plan = build_repair_from_checkpoints(
            reference,
            forward,
            selection,
            policy=repair_v2.TargetMultiViewRepairPolicyV2(),
            checkpoint_states=checkpoint_states,
        )
        assert plan.domain("target").rungs
    finally:
        store.close()


def test_campaign_facade_routes_production_to_shared_checkpoint_builder() -> None:
    from mdstats.training_data import campaign_cli
    from mdstats.training_data import mvsel2_hardening_runtime as hardening

    assert hardening._build_repair_from_checkpoints is build_repair_from_checkpoints
    assert campaign_cli._core._ensure_target_multi_view_repair_v2 is not None


def test_repair_projection_requires_measured_proposal_cost() -> None:
    assert (
        support.repair_projection_upper(
            [{"shell_size": 128, "proposals": 0, "wall_seconds": 1.0}],
            candidate_count=100,
            materializable_sizes=(128, 256),
            removal_shortlist_limit=64,
            max_swaps_per_shell=32,
            max_passes_per_shell=2,
        )
        is None
    )

    value = support.repair_projection_upper(
        [{"shell_size": 128, "proposals": 2, "wall_seconds": 1.0}],
        candidate_count=100,
        materializable_sizes=(128, 256),
        removal_shortlist_limit=64,
        max_swaps_per_shell=32,
        max_passes_per_shell=2,
    )
    assert value is not None and value > 0.0


def test_selector_projection_increases_with_phase_b_cost() -> None:
    common = dict(
        current_restore_seconds=10.0,
        historical_cold_preflight_seconds=20.0,
        phase_a_prefix_size=128,
        max_phase_a_rank_seconds=0.2,
        measured_phase_a_seconds=30.0,
        exact_rebase_seconds=40.0,
        phase_a_end=452,
        target_size=16384,
    )
    lower = support.selector_projection_upper(
        **common, max_phase_b_rank_seconds=0.4
    )
    upper = support.selector_projection_upper(
        **common, max_phase_b_rank_seconds=0.5
    )
    assert upper > lower > 0.0


def test_resource_plan_user_caps_only_tighten(tmp_path) -> None:
    default = support.derive_resource_plan(root=tmp_path)
    capped = support.derive_resource_plan(
        root=tmp_path,
        max_rss_gib=max(1.5, default.hard_rss_bytes / support.GIB / 2.0),
        max_scratch_gib=0.25,
        total_seconds=300.0,
    )
    assert capped.hard_rss_bytes <= default.hard_rss_bytes
    assert capped.hard_scratch_bytes <= default.hard_scratch_bytes
    assert capped.hard_total_seconds == 300.0
    assert capped.operating_rss_bytes < capped.hard_rss_bytes
    assert capped.operating_total_seconds < capped.hard_total_seconds


def test_scavenger_removes_only_owned_dead_scratch(tmp_path) -> None:
    parent = tmp_path / "scratch"
    parent.mkdir()
    owned = parent / "owned"
    foreign = parent / "foreign"
    owned.mkdir()
    foreign.mkdir()
    support.json_dump(
        owned / "OWNER.json",
        {
            "schema": support.OWNER_SCHEMA,
            "scratch_dir": str(owned.resolve()),
            "parent_pid": 99999999,
            "parent_start_ticks": None,
        },
    )
    (foreign / "OWNER.json").write_text("{}", encoding="utf-8")

    removed = support.scavenge_owned_scratch(parent)

    assert removed == ["owned"]
    assert not owned.exists()
    assert foreign.exists()
