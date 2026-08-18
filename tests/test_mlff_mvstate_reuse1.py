from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import mdstats
from mdstats.training_data.campaign_cli import CampaignStore
from tests.test_mlff_target_data2b_feas1 import _reference_and_role


def _fixture():
    reference, role = _reference_and_role(split_units=True)
    feasibility, neighborhoods = mdstats.build_target_coverage_feasibility_artifacts(reference, role)
    sparse = mdstats.build_target_coverage_sparse_index(
        reference, role, feasibility, exact_neighborhood_store=neighborhoods
    )
    policy = mdstats.TargetMultiViewSelectorPolicy(target_sizes=(2, 4, 8, 16))
    selection, cache = mdstats.build_target_multi_view_selection_artifacts(reference, sparse, policy=policy)
    return reference, sparse, selection, cache


def test_mvstate_checkpoints_equal_exact_selector_replay() -> None:
    reference, sparse, selection, cache = _fixture()
    mdstats.validate_target_multi_view_selection_state_cache(
        cache,
        target_coverage_reference=reference,
        target_coverage_sparse_index=sparse,
        target_multi_view_selection=selection,
        verify_state_replay=True,
    )
    domain = cache.domain("target")
    assert [cp.target_size for cp in domain.checkpoints] == [2, 4, 8, 16]
    assert all(np.count_nonzero(~cp.available) == cp.target_size for cp in domain.checkpoints)


def test_mvstate_cached_repair_is_byte_identical_to_replay_oracle() -> None:
    reference, sparse, selection, cache = _fixture()
    reference_plan = mdstats.build_target_multi_view_repair_plan(
        reference, sparse, selection, execution_mode="optimized", proposal_workers=2
    )
    cached_plan = mdstats.build_target_multi_view_repair_plan(
        reference, sparse, selection, execution_mode="optimized", proposal_workers=2,
        selection_state_cache=cache,
    )
    assert cached_plan.to_dict() == reference_plan.to_dict()
    assert cached_plan.content_digest == reference_plan.content_digest


def test_mvstate_cache_native_round_trip_and_campaign_store(tmp_path: Path) -> None:
    reference, sparse, selection, cache = _fixture()
    records = tmp_path / "records"
    pointer = mdstats.write_target_multi_view_selection_state_native_record(cache, records)
    restored = mdstats.read_target_multi_view_selection_state_native_record(pointer, tmp_path)
    assert restored.content_digest == cache.content_digest
    mdstats.validate_target_multi_view_selection_state_cache(
        restored,
        target_coverage_reference=reference,
        target_coverage_sparse_index=sparse,
        target_multi_view_selection=selection,
        verify_state_replay=True,
    )

    store = CampaignStore(tmp_path / "campaign.sqlite3")
    store.put_record("target_multi_view_selection_state_cache", cache)
    stored = store.get_record("target_multi_view_selection_state_cache", mdstats.TargetMultiViewSelectionStateCache)
    assert stored.content_digest == cache.content_digest
    assert any("target-multi-view-selection-state" in str(path) for path in store.storage_references())


def test_mvstate_native_tamper_is_rejected(tmp_path: Path) -> None:
    _, _, _, cache = _fixture()
    pointer = mdstats.write_target_multi_view_selection_state_native_record(cache, tmp_path / "records")
    manifest = tmp_path / pointer["relative_path"]
    payload = json.loads(manifest.read_text())
    bundle_name = payload["array_bundle"]["relative_path"]
    array_path = manifest.parent / bundle_name
    data = bytearray(array_path.read_bytes())
    data[-1] ^= 1
    array_path.write_bytes(data)
    with pytest.raises(mdstats.TargetMultiViewSelectionStateNativeStoreError):
        mdstats.read_target_multi_view_selection_state_native_record(pointer, tmp_path)


def test_mvstate_stale_selection_lineage_is_rejected() -> None:
    reference, sparse, selection, cache = _fixture()
    payload = selection.to_dict()
    payload["domains"][0]["phase_a_completed_at"] = None if payload["domains"][0]["phase_a_completed_at"] is not None else 1
    payload["domains"][0].pop("content_digest", None)
    payload.pop("content_digest", None)
    payload.pop("domain_digests", None)
    changed = mdstats.TargetMultiViewSelectionPlan.from_dict(payload)
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.validate_target_multi_view_selection_state_cache(
            cache,
            target_coverage_reference=reference,
            target_coverage_sparse_index=sparse,
            target_multi_view_selection=changed,
        )


def test_mvstate_batched_replay_matches_scalar_state_exactly() -> None:
    import mdstats.training_data.target_multi_view_selector as selector

    reference, sparse, selection, cache = _fixture()
    reference_domain = reference.domain("target")
    sparse_domain = sparse.domain("target")
    domain = cache.domain("target")
    checkpoint = domain.checkpoint(4)
    batch_state = mdstats.restore_domain_state(
        checkpoint, reference_domain, sparse_domain
    )
    scalar_state = mdstats.restore_domain_state(
        checkpoint, reference_domain, sparse_domain
    )
    uid_to_candidate = {uid: i for i, uid in enumerate(reference_domain.frame_uids)}
    order = [uid_to_candidate[item.frame_uid] for item in selection.domain("target").master_order]
    candidates = order[4:16]
    batch_utility = selector._select_many_and_update_exact(
        candidates, sparse_domain, batch_state, checkpoint.representative_utility, candidate_block_size=4
    )
    scalar_utility = float(checkpoint.representative_utility)
    for candidate in candidates:
        scalar_utility += float(scalar_state.total_representative_gain[candidate])
        selector._select_and_update(int(candidate), sparse_domain, scalar_state)
    assert selector._states_exactly_equal(batch_state, scalar_state)
    assert batch_utility == scalar_utility
