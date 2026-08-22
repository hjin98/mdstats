from __future__ import annotations

import json

import numpy as np

import mdstats
from mdstats.training_data import target_coverage_sparse_index_store as mvidx_store
from mdstats.training_data import target_multi_view_repair_v2 as repair_v2
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.mvsel2_hardening_runtime import (
    _all_valid_rung_states,
    _build_repair_from_checkpoints,
    _highest_valid_resume_states,
)
from mdstats.training_data.target_coverage_sparse_forward_view import (
    target_coverage_sparse_forward_view,
)
from mdstats.training_data.target_multi_view_selection_state_v2 import (
    build_target_multi_view_selection_identity_v2,
    checkpoint_target_multi_view_forward_state_v2,
    write_target_multi_view_selection_checkpoint_v2,
)
from mdstats.training_data.target_multi_view_selector_v2 import (
    TargetMultiViewSelectionDomainPlanV2,
    TargetMultiViewSelectionPlanV2,
    TargetMultiViewSelectorPolicyV2,
    build_target_multi_view_forward_state_v2,
    build_target_multi_view_selection_plan_v2,
    score_target_multi_view_candidate_v2,
    select_target_multi_view_candidate_v2,
)
from mdstats.training_data.target_multi_view_selector_v2_resume import (
    build_target_multi_view_selection_plan_v2_resumable,
)
from tests.test_mlff_mvsel2_forward import _forward_fixture
from tests.test_mlff_repair2 import _trace
from tests._mlff_multiview_legacy_fixtures import _redundant_selection


def _state_for_prefix(reference_domain, forward_domain, entries):
    state = build_target_multi_view_forward_state_v2(reference_domain, forward_domain)
    uid_to_index = {uid: i for i, uid in enumerate(reference_domain.frame_uids)}
    for entry in entries:
        candidate = uid_to_index[entry.frame_uid]
        score = score_target_multi_view_candidate_v2(candidate, forward_domain, state)
        select_target_multi_view_candidate_v2(candidate, forward_domain, state, score=score)
    return state


def _write_checkpoint(store, reference, forward, policy, size, state):
    reference_domain = reference.domain("target")
    forward_domain = forward.domain("target")
    identity = build_target_multi_view_selection_identity_v2(
        reference_domain,
        forward_domain,
        dataset_id=reference.dataset_id,
        selector_policy=policy.to_dict(),
    )
    checkpoint = checkpoint_target_multi_view_forward_state_v2(state, identity)
    pointer = write_target_multi_view_selection_checkpoint_v2(
        checkpoint, store.external_record_directory
    )
    store.put_record(f"target_multi_view_selection_state_v2:target:{size}", pointer)
    return pointer


def test_native_forward_reader_never_opens_inverse_arrays(tmp_path, monkeypatch) -> None:
    _reference, index, _forward = _forward_fixture()
    records_root = tmp_path / "records"
    pointer = mvidx_store.write_target_coverage_sparse_index_native_record(
        index, records_root
    )
    opened: list[str] = []
    original = mvidx_store._read_npy

    def guarded(*args, label, **kwargs):
        opened.append(label)
        assert label not in {
            "witness_offsets",
            "witness_candidates",
            "obligation_offsets",
            "obligation_candidates",
        }
        return original(*args, label=label, **kwargs)

    monkeypatch.setattr(mvidx_store, "_read_npy", guarded)
    restored = mvidx_store.read_target_coverage_sparse_index_forward_view_native_record(
        pointer, records_root.parent, mmap_threshold_bytes=0
    )
    assert restored.mvidx1_content_digest == index.content_digest
    assert "candidate_offsets" in opened
    assert "candidate_witnesses" in opened


def test_resumed_selector_reconstructs_exact_cold_authority() -> None:
    reference, _index, forward = _forward_fixture()
    policy = TargetMultiViewSelectorPolicyV2(target_sizes=(4, 8, 12, 16))
    cold = build_target_multi_view_selection_plan_v2(reference, forward, policy=policy)
    domain = cold.domain("target")
    checkpoint_size = 8
    state = _state_for_prefix(
        reference.domain("target"),
        forward.domain("target"),
        domain.master_order[:checkpoint_size],
    )
    resumed = build_target_multi_view_selection_plan_v2_resumable(
        reference,
        forward,
        policy=policy,
        resume_states={"target": state},
    )
    assert resumed.content_digest == cold.content_digest
    assert resumed.domain("target").content_digest == domain.content_digest
    assert resumed.domain("target").master_order == domain.master_order
    assert resumed.domain("target").rungs == domain.rungs


def test_checkpoint_discovery_falls_back_from_corrupt_newest(tmp_path) -> None:
    reference, _index, forward = _forward_fixture()
    policy = TargetMultiViewSelectorPolicyV2(target_sizes=(4, 8, 12, 16))
    cold = build_target_multi_view_selection_plan_v2(reference, forward, policy=policy)
    store = CampaignStore(tmp_path / "campaign.sqlite3")
    try:
        domain = cold.domain("target")
        state4 = _state_for_prefix(
            reference.domain("target"), forward.domain("target"), domain.master_order[:4]
        )
        state8 = _state_for_prefix(
            reference.domain("target"), forward.domain("target"), domain.master_order[:8]
        )
        _write_checkpoint(store, reference, forward, policy, 4, state4)
        pointer8 = _write_checkpoint(store, reference, forward, policy, 8, state8)
        corrupt = dict(pointer8)
        corrupt["sha256"] = "0" * 64
        store.put_record("target_multi_view_selection_state_v2:target:16", corrupt)

        states, _pointers = _highest_valid_resume_states(
            store, reference, forward, policy
        )
        assert states["target"].selected_count == 8
        resumed = build_target_multi_view_selection_plan_v2_resumable(
            reference, forward, policy=policy, resume_states=states
        )
        assert resumed.content_digest == cold.content_digest
    finally:
        store.close()


def _v2_redundant_selection():
    reference, index, legacy_selection = _redundant_selection()
    forward = target_coverage_sparse_forward_view(index)
    legacy_domain = legacy_selection.domain("target")
    selection = TargetMultiViewSelectionPlanV2(
        dataset_id=reference.dataset_id,
        target_coverage_reference_digest=reference.content_digest,
        mvidx1_content_digest=index.content_digest,
        policy=TargetMultiViewSelectorPolicyV2(
            target_sizes=legacy_selection.policy.target_sizes
        ),
        domains=(TargetMultiViewSelectionDomainPlanV2(
            label_domain_id="target",
            reference_domain_digest=legacy_domain.reference_domain_digest,
            mvidx1_domain_digest=index.domain("target").content_digest,
            candidate_count=legacy_domain.candidate_count,
            master_order=legacy_domain.master_order,
            rungs=legacy_domain.rungs,
            phase_a_completed_at=legacy_domain.phase_a_completed_at,
        ),),
    )
    return reference, index, forward, selection


def test_repair_checkpoint_reuse_stops_after_first_divergence(tmp_path) -> None:
    reference, _index, forward, selection = _v2_redundant_selection()
    policy = repair_v2.TargetMultiViewRepairPolicyV2()
    baseline = repair_v2.build_target_multi_view_repair_plan_v2(
        reference, forward, selection, policy=policy
    )
    assert baseline.domain("target").total_swaps > 0

    store = CampaignStore(tmp_path / "campaign.sqlite3")
    try:
        for rung in selection.domain("target").rungs:
            if not rung.materializable:
                continue
            state = _state_for_prefix(
                reference.domain("target"),
                forward.domain("target"),
                selection.domain("target").master_order[: rung.target_size],
            )
            _write_checkpoint(
                store, reference, forward, selection.policy, rung.target_size, state
            )
        checkpoint_states = _all_valid_rung_states(
            store, reference, forward, selection.policy
        )
        progress: list[str] = []
        resumed = _build_repair_from_checkpoints(
            reference,
            forward,
            selection,
            policy=policy,
            checkpoint_states=checkpoint_states,
            progress_callback=progress.append,
        )
    finally:
        store.close()

    assert _trace(resumed) == _trace(baseline)
    assert resumed.domain("target").repaired_master_order == baseline.domain("target").repaired_master_order
    first_divergent = next(i for i, text in enumerate(progress) if "swaps=0" not in text)
    assert any("mvstate2_restore_count=" in text for text in progress[: first_divergent + 1])
    assert all(
        "selected_prefix_state_mode=post_divergence_carried_state" in text
        for text in progress[first_divergent:]
    )


def test_repair2_rejected_proposals_do_not_mutate_or_clone_state(monkeypatch) -> None:
    reference, _index, forward, selection = _v2_redundant_selection()
    deselections = 0
    selections = 0
    original_deselect = repair_v2.deselect_target_multi_view_candidate_v2
    original_select = repair_v2.select_target_multi_view_candidate_v2

    def counted_deselect(*args, **kwargs):
        nonlocal deselections
        deselections += 1
        return original_deselect(*args, **kwargs)

    def counted_select(*args, **kwargs):
        nonlocal selections
        selections += 1
        return original_select(*args, **kwargs)

    monkeypatch.setattr(
        repair_v2, "deselect_target_multi_view_candidate_v2", counted_deselect
    )
    monkeypatch.setattr(
        repair_v2, "select_target_multi_view_candidate_v2", counted_select
    )
    progress: list[str] = []
    plan = repair_v2.build_target_multi_view_repair_plan_v2(
        reference,
        forward,
        selection,
        policy=repair_v2.TargetMultiViewRepairPolicyV2(),
        progress_callback=progress.append,
    )
    total_swaps = plan.domain("target").total_swaps
    # Selections include the initial selector-prefix replay plus exactly one
    # accepted replacement per swap.  Deselect is accepted-swap-only.
    assert deselections == total_swaps
    assert selections == len(selection.domain("target").master_order) + total_swaps
    assert all("proposal_full_state_copies=0" in text for text in progress)
    source = open(repair_v2.__file__, encoding="utf-8").read()
    assert "def _copy_state" not in source
