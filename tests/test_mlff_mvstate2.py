from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from mdstats.training_data.target_multi_view_selection_state_v2 import (
    TargetMultiViewSelectionStateV2StoreError,
    build_target_multi_view_selection_identity_v2,
    checkpoint_target_multi_view_forward_state_v2,
    read_target_multi_view_selection_checkpoint_v2,
    restore_target_multi_view_forward_state_v2,
    write_target_multi_view_selection_checkpoint_v2,
)
from mdstats.training_data.target_multi_view_selector_v2 import (
    build_target_multi_view_forward_state_v2,
    build_target_multi_view_lazy_frontier_v2,
    choose_target_multi_view_phase_a_candidate_v2,
    choose_target_multi_view_phase_b_candidate_v2,
    select_target_multi_view_candidate_v2,
)
from tests.test_mlff_mvsel2_forward import _forward_fixture


POLICY = {"target_sizes": (8, 12), "tau": 0.95, "epsilon": 1.0e-14,
          "objectives": "MVSEL2", "ties": "uid"}


def _select(reference_domain, forward_domain, state, target: int, *, rebuild_every: int = 0):
    frontier = None
    while state.selected_count < target:
        pending = state.unsatisfied_required_obligation_count > 0 or any(
            family.coverage_mass < 0.95 - 1.0e-14 for family in state.family_states
        )
        if pending:
            choice = choose_target_multi_view_phase_a_candidate_v2(
                reference_domain, forward_domain, state, batch_size=3, workers=4
            )
        else:
            if frontier is None or (rebuild_every and state.selected_count % rebuild_every == 0):
                frontier = build_target_multi_view_lazy_frontier_v2(forward_domain, state)
            choice = choose_target_multi_view_phase_b_candidate_v2(
                reference_domain, forward_domain, state, frontier
            )
        select_target_multi_view_candidate_v2(
            choice.candidate_index, forward_domain, state, score=choice.score
        )
    return state


def _checkpoint(tmp_path: Path):
    reference, _, forward = _forward_fixture()
    rd = reference.domain("target")
    fd = forward.domain("target")
    identity = build_target_multi_view_selection_identity_v2(
        rd, fd, dataset_id=reference.dataset_id, selector_policy=POLICY
    )
    state = build_target_multi_view_forward_state_v2(rd, fd)
    _select(rd, fd, state, 8)
    checkpoint = checkpoint_target_multi_view_forward_state_v2(state, identity)
    pointer = write_target_multi_view_selection_checkpoint_v2(checkpoint, tmp_path / "records")
    return rd, fd, identity, state, pointer


def test_mvstate2_resume_matches_uninterrupted_across_execution_settings(tmp_path: Path) -> None:
    rd, fd, identity, partial, pointer = _checkpoint(tmp_path)
    restored_checkpoint = read_target_multi_view_selection_checkpoint_v2(pointer, tmp_path)
    resumed = restore_target_multi_view_forward_state_v2(
        restored_checkpoint, rd, fd, expected_identity=identity
    )
    uninterrupted = restore_target_multi_view_forward_state_v2(
        checkpoint_target_multi_view_forward_state_v2(partial, identity),
        rd, fd, expected_identity=identity,
    )
    _select(rd, fd, resumed, 14, rebuild_every=2)
    _select(rd, fd, uninterrupted, 14, rebuild_every=0)
    assert resumed.selected_order == uninterrupted.selected_order
    assert not any("gain" in key for key in restored_checkpoint.__dataclass_fields__)


def test_mvstate2_rejects_v1_stale_and_tampered_artifacts(tmp_path: Path) -> None:
    rd, fd, identity, _, pointer = _checkpoint(tmp_path)
    with pytest.raises(TargetMultiViewSelectionStateV2StoreError, match="MVSTATE1"):
        read_target_multi_view_selection_checkpoint_v2(
            {**pointer, "schema": "mdstats.mlff-campaign-target-multi-view-selection-state-native-pointer.v1"},
            tmp_path,
        )
    checkpoint = read_target_multi_view_selection_checkpoint_v2(pointer, tmp_path)
    stale = type(identity)(**{**identity.metadata_dict(), "dataset_id": "stale-dataset"})
    with pytest.raises(TargetMultiViewSelectionStateV2StoreError, match="identity mismatch"):
        restore_target_multi_view_forward_state_v2(checkpoint, rd, fd, expected_identity=stale)
    manifest = tmp_path / pointer["relative_path"]
    manifest.write_bytes(manifest.read_bytes()[:-7])
    with pytest.raises(TargetMultiViewSelectionStateV2StoreError):
        read_target_multi_view_selection_checkpoint_v2(pointer, tmp_path)
    rebuilt_pointer = write_target_multi_view_selection_checkpoint_v2(checkpoint, tmp_path / "records")
    rebuilt = read_target_multi_view_selection_checkpoint_v2(rebuilt_pointer, tmp_path)
    assert rebuilt.selected_count == checkpoint.selected_count


def test_mvstate2_rejects_modified_continuation_state(tmp_path: Path) -> None:
    rd, fd, identity, state, _ = _checkpoint(tmp_path)
    checkpoint = checkpoint_target_multi_view_forward_state_v2(state, identity)
    altered = list(checkpoint.family_multiplicity)
    altered[0] = np.array(altered[0], copy=True)
    altered[0][0] += 1
    changed = type(checkpoint)(
        identity=identity,
        selected_order=checkpoint.selected_order,
        family_multiplicity=tuple(altered),
        family_coverage_mass=checkpoint.family_coverage_mass,
        obligation_counts=checkpoint.obligation_counts,
        unsatisfied_required_obligation_count=checkpoint.unsatisfied_required_obligation_count,
        correlation_unit_counts=checkpoint.correlation_unit_counts,
        representative_utility=checkpoint.representative_utility,
    )
    with pytest.raises(TargetMultiViewSelectionStateV2StoreError, match="multiplicity"):
        restore_target_multi_view_forward_state_v2(changed, rd, fd, expected_identity=identity)
