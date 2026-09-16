"""The single production MVSEL2 rank loop.

Restored from ``mvsel2_selection_engine`` (carrier ``3937881e``) and rebound to
one exact ``P_train`` domain.  The same loop builds the pure configured prefix,
continues after REPAIR2 through the complete ``P_train`` suffix, and resumes
from an authenticated MVSTATE2 checkpoint.  Phase A uses the locality kernel,
Phase B the certified lazy witness-term kernel; scoring semantics and state
mutation remain in :mod:`selector`.

Rank history (entries) is recorded only through ``record_entries_through``
(the configured ceiling) so journals stay bounded; suffix ranks contribute
only their exact frame indices to the complete order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Callable, Sequence

from .._common import TrainingDataInputError
from ..progress_timing import format_progress_fraction, format_progress_time
from .kernels import build_lazy_frontier, choose_phase_a, choose_phase_b
from .native import mvsel2_execution_backend
from .selector import (
    LazyFrontier,
    TargetMultiViewForwardState,
    TargetMultiViewSelectionEntry,
    TargetMultiViewSelectionRung,
    TargetMultiViewSelectorPolicy,
    build_forward_state,
    entry_from_choice,
    materialized_rung,
    phase_a_active,
    select_candidate,
)

CheckpointCallback = Callable[
    [TargetMultiViewForwardState, Sequence[TargetMultiViewSelectionEntry], Sequence[TargetMultiViewSelectionRung], "int | None"],
    None,
]


@dataclass(slots=True)
class SelectionTelemetry:
    backend: str
    workers: int
    ranks: int = 0
    phase_a_ranks: int = 0
    evaluation_edges: int = 0
    rescoring_count: int = 0
    frontier_rebases: int = 0
    fallback_count: int = 0
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "workers": self.workers,
            "ranks": self.ranks,
            "phase_a_ranks": self.phase_a_ranks,
            "evaluation_edges": self.evaluation_edges,
            "rescoring_count": self.rescoring_count,
            "frontier_rebases": self.frontier_rebases,
            "fallback_count": self.fallback_count,
            "elapsed_seconds": self.elapsed_seconds,
        }


@dataclass(slots=True)
class SelectionRun:
    state: TargetMultiViewForwardState
    entries: list[TargetMultiViewSelectionEntry]
    rungs: list[TargetMultiViewSelectionRung]
    phase_a_completed_at: int | None
    telemetry: SelectionTelemetry = field(repr=False)


def run_selection(
    reference: Any,
    forward: Any,
    policy: TargetMultiViewSelectorPolicy,
    *,
    stop: int,
    state: TargetMultiViewForwardState | None = None,
    entries: Sequence[TargetMultiViewSelectionEntry] = (),
    rungs: Sequence[TargetMultiViewSelectionRung] = (),
    phase_a_completed_at: int | None = None,
    rung_sizes: Sequence[int] = (),
    record_entries_through: int = 0,
    workers: int = 1,
    batch_size: int = 256,
    checkpoint: CheckpointCallback | None = None,
    checkpoint_interval: int = 0,
    progress_callback: Callable[[str], None] | None = None,
    progress_interval_seconds: float = 30.0,
) -> SelectionRun:
    """Advance exact MVSEL2 from ``state`` (or rank zero) to ``stop`` ranks."""

    workers = int(workers)
    stop = int(stop)
    if workers < 1 or int(batch_size) < 1 or int(checkpoint_interval) < 0:
        raise TrainingDataInputError("MVSEL2 worker/batch/checkpoint settings are invalid.")
    if state is None:
        if entries or rungs:
            raise TrainingDataInputError("MVSEL2 rank history was supplied without continuation state.")
        state = build_forward_state(reference, forward)
    start = state.selected_count
    if stop < start or stop > int(forward.candidate_count):
        raise TrainingDataInputError("MVSEL2 stop rank is outside the exact P_train domain.")
    entries = list(entries)
    if len(entries) != min(start, int(record_entries_through)):
        raise TrainingDataInputError("MVSEL2 rank history and continuation-state sizes disagree.")
    if tuple(entry.frame_uid for entry in entries) != tuple(reference.frame_uids[c] for c in state.selected_order[: len(entries)]):
        raise TrainingDataInputError("MVSEL2 rank history disagrees with the continuation prefix.")
    rungs = list(rungs)
    sizes = frozenset(int(v) for v in rung_sizes)
    previous_rung = max((item.target_size for item in rungs), default=0)
    telemetry = SelectionTelemetry(backend=mvsel2_execution_backend(workers), workers=workers)
    frontier: LazyFrontier | None = None
    started = time.monotonic()
    last_progress = started
    for rank in range(start, stop):
        phase_a = phase_a_active(state, policy)
        if phase_a:
            choice = choose_phase_a(reference, forward, state, policy, workers=workers)
            frontier = None
            telemetry.phase_a_ranks += 1
        else:
            if frontier is None:
                frontier = build_lazy_frontier(forward, state, workers=workers)
                telemetry.frontier_rebases += 1
            choice = choose_phase_b(reference, forward, state, frontier, policy, workers=workers, batch_size=batch_size)
        telemetry.evaluation_edges += int(choice.evaluation_edges)
        telemetry.rescoring_count += int(choice.rescoring_count)
        telemetry.fallback_count += int(choice.fallback_used)
        if rank < int(record_entries_through):
            entries.append(entry_from_choice(reference, forward, choice, rank=rank, phase_a=phase_a))
        select_candidate(choice.candidate_index, forward, state, score=choice.score)
        telemetry.ranks += 1
        size = rank + 1
        if phase_a_completed_at is None and not phase_a_active(state, policy):
            phase_a_completed_at = size
        boundary = False
        if size in sizes:
            rungs.append(
                materialized_rung(reference, forward, state, entries, target_size=size, previous_size=previous_rung)
            )
            previous_rung = size
            boundary = True
        elif checkpoint_interval and (size - start) % int(checkpoint_interval) == 0 and size < stop:
            boundary = True
        if boundary and checkpoint is not None:
            checkpoint(state, entries, rungs, phase_a_completed_at)
        now = time.monotonic()
        if progress_callback is not None and (size == stop or boundary or now - last_progress >= progress_interval_seconds):
            elapsed = now - started
            rate = (size - start) / elapsed if elapsed > 0.0 else 0.0
            eta = (stop - size) / rate if rate > 0.0 else None
            progress_callback(
                f"status=selecting; progress={format_progress_fraction(size, stop)}; "
                f"elapsed={format_progress_time(elapsed)}; eta={format_progress_time(eta)}; "
                f"phase={'hard_coverage' if phase_a else 'representative_fill'}; backend={telemetry.backend}; "
                f"workers={workers}; rescoring={telemetry.rescoring_count}; edges={telemetry.evaluation_edges}"
            )
            last_progress = now
    telemetry.elapsed_seconds = time.monotonic() - started
    return SelectionRun(state, entries, rungs, phase_a_completed_at, telemetry)


__all__ = ["SelectionRun", "SelectionTelemetry", "run_selection"]
