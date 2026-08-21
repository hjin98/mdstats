from __future__ import annotations

from pathlib import Path

from mdstats.training_data import target_multi_view_selector_v2 as selector_v2
from tests.test_mlff_mvsel2_forward import _forward_fixture


def test_g4_par1_thread_executor_is_not_executable_source() -> None:
    source = Path(selector_v2.__file__).read_text(encoding="utf-8")
    assert "ThreadPoolExecutor" not in source
    assert 'thread_name_prefix="mdstats-mvsel2"' not in source
    assert "executor.map(" not in source


def test_g4_scalar_reference_workers_setting_is_semantically_inert() -> None:
    reference, _index, forward = _forward_fixture()
    rd = reference.domain("target")
    fd = forward.domain("target")
    left = selector_v2.build_target_multi_view_forward_state_v2(rd, fd)
    right = selector_v2.build_target_multi_view_forward_state_v2(rd, fd)
    a = selector_v2.choose_target_multi_view_phase_a_candidate_v2(
        rd, fd, left, batch_size=2, workers=1
    )
    b = selector_v2.choose_target_multi_view_phase_a_candidate_v2(
        rd, fd, right, batch_size=2, workers=32
    )
    assert a == b


def test_g4_bulk_score_workers_setting_is_semantically_inert() -> None:
    reference, _index, forward = _forward_fixture()
    rd = reference.domain("target")
    fd = forward.domain("target")
    state = selector_v2.build_target_multi_view_forward_state_v2(rd, fd)
    candidates = tuple(range(min(8, fd.candidate_count)))
    assert selector_v2.score_target_multi_view_candidates_v2(
        candidates, fd, state, batch_size=2, workers=1
    ) == selector_v2.score_target_multi_view_candidates_v2(
        candidates, fd, state, batch_size=2, workers=32
    )
