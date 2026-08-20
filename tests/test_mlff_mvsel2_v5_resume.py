from __future__ import annotations

import pytest

from mdstats.training_data._common import digest
from mdstats.training_data import mvsel2_selection_engine as engine
from mdstats.training_data.mvsel2_selection_engine import (
    build_target_multi_view_selection_plan_v2_engine,
)
from mdstats.training_data.target_multi_view_selection_history_v2 import (
    decode_target_multi_view_selection_history_v2,
    encode_target_multi_view_selection_history_v2,
)
from mdstats.training_data.target_multi_view_selection_state_v2 import (
    build_target_multi_view_selection_identity_v2,
    checkpoint_target_multi_view_forward_state_v2,
    restore_target_multi_view_forward_state_v2,
)
from mdstats.training_data.target_multi_view_selector_v2 import (
    TargetMultiViewSelectorPolicyV2,
    build_target_multi_view_selection_plan_v2,
)
from mdstats.training_data.target_multi_view_selector_v2_resume import (
    preserve_checkpoint_float_history_v2,
)
from tests.test_mlff_mvsel2_forward import _forward_fixture


POLICY = TargetMultiViewSelectorPolicyV2(target_sizes=(4, 8, 12))


class _StopAtCheckpoint(RuntimeError):
    pass


def _fixture():
    reference, _, forward = _forward_fixture()
    return reference, forward, reference.domain("target"), forward.domain("target")


def _captured_eight_state_and_history():
    reference, forward, reference_domain, forward_domain = _fixture()
    identity = build_target_multi_view_selection_identity_v2(
        reference_domain,
        forward_domain,
        dataset_id=reference.dataset_id,
        selector_policy=POLICY.to_dict(),
    )
    captured: dict[str, object] = {}

    def checkpoint(_reference_domain, _forward_domain, state, size: int) -> None:
        if size == 8:
            captured["checkpoint"] = checkpoint_target_multi_view_forward_state_v2(
                state, identity
            )

    def history_checkpoint(_reference_domain, _forward_domain, history, size: int) -> None:
        if size == 8:
            captured["history"] = history
            raise _StopAtCheckpoint

    with pytest.raises(_StopAtCheckpoint):
        build_target_multi_view_selection_plan_v2_engine(
            reference,
            forward,
            policy=POLICY,
            workers=32,
            checkpoint_callback=checkpoint,
            history_callback=history_checkpoint,
        )

    checkpoint_value = captured["checkpoint"]
    restored = restore_target_multi_view_forward_state_v2(
        checkpoint_value,
        reference_domain,
        forward_domain,
        expected_identity=identity,
    )
    restored = preserve_checkpoint_float_history_v2(checkpoint_value, restored)
    return (
        reference,
        forward,
        identity,
        restored,
        captured["history"],
    )


def test_v5_engine_fresh_matches_independent_reference_builder() -> None:
    reference, forward, _, _ = _fixture()
    expected = build_target_multi_view_selection_plan_v2(
        reference,
        forward,
        policy=POLICY,
        workers=1,
    )
    actual = build_target_multi_view_selection_plan_v2_engine(
        reference,
        forward,
        policy=POLICY,
        workers=32,
    )
    assert actual.to_dict() == expected.to_dict()
    assert actual.content_digest == expected.content_digest


def test_v5_journal_resume_matches_fresh_without_prefix_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference, forward, _, restored, history = _captured_eight_state_and_history()
    fresh = build_target_multi_view_selection_plan_v2_engine(
        reference,
        forward,
        policy=POLICY,
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("journal-backed resume must not replay the selected prefix")

    monkeypatch.setattr(engine, "_replay_selected_prefix_history", forbidden)
    resumed = build_target_multi_view_selection_plan_v2_engine(
        reference,
        forward,
        policy=POLICY,
        resume_states={"target": restored},
        resume_histories={"target": history},
    )
    assert resumed.to_dict() == fresh.to_dict()
    assert resumed.content_digest == fresh.content_digest


def test_v5_legacy_checkpoint_fallback_replays_once_and_matches_fresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference, forward, _, restored, _ = _captured_eight_state_and_history()
    fresh = build_target_multi_view_selection_plan_v2_engine(
        reference,
        forward,
        policy=POLICY,
    )
    original = engine._replay_selected_prefix_history
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(engine, "_replay_selected_prefix_history", counted)
    resumed = build_target_multi_view_selection_plan_v2_engine(
        reference,
        forward,
        policy=POLICY,
        resume_states={"target": restored},
    )
    assert calls == 1
    assert resumed.to_dict() == fresh.to_dict()


def test_v5_rank_history_record_is_bound_to_state_identity_and_prefix() -> None:
    _, _, identity, restored, history = _captured_eight_state_and_history()
    order_digest = digest(tuple(int(value) for value in restored.selected_order))
    record = encode_target_multi_view_selection_history_v2(
        history,
        identity_digest=identity.content_digest,
        selected_order_digest=order_digest,
    )
    decoded = decode_target_multi_view_selection_history_v2(
        record,
        expected_identity_digest=identity.content_digest,
        expected_selected_order_digest=order_digest,
        expected_selected_count=8,
    )
    assert decoded.content_digest == history.content_digest
    with pytest.raises(Exception, match="selected-prefix identity"):
        decode_target_multi_view_selection_history_v2(
            record,
            expected_identity_digest=identity.content_digest,
            expected_selected_order_digest="0" * 64,
            expected_selected_count=8,
        )
