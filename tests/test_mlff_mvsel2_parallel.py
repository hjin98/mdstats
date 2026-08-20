from __future__ import annotations

import threading
import time

from mdstats.training_data import target_multi_view_selector_v2 as selector_v2
from tests.test_mlff_mvsel2_forward import _forward_fixture


def test_mvsel2_phase_a_workers_execute_candidate_scoring_on_multiple_threads(
    monkeypatch,
) -> None:
    reference, _, forward = _forward_fixture()
    reference_domain = reference.domain("target")
    forward_domain = forward.domain("target")
    state = selector_v2.build_target_multi_view_forward_state_v2(
        reference_domain, forward_domain
    )

    original = selector_v2._family_coverage_gain_v2
    thread_ids: set[int] = set()
    lock = threading.Lock()

    def tracked(*args, **kwargs):
        with lock:
            thread_ids.add(threading.get_ident())
        # Keep candidate blocks alive long enough for the executor to schedule
        # more than one worker even on the tiny focused fixture.
        time.sleep(0.002)
        return original(*args, **kwargs)

    monkeypatch.setattr(selector_v2, "_family_coverage_gain_v2", tracked)
    selector_v2.choose_target_multi_view_phase_a_candidate_v2(
        reference_domain,
        forward_domain,
        state,
        batch_size=1,
        workers=4,
    )
    assert len(thread_ids) >= 2
