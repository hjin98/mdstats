"""Single production MVSEL2 selection engine with authenticated resume history.

The engine owns the only production rank loop for fresh and resumed MVSEL2
selection. Scientific scoring/mutation remains in the selector primitives;
Phase A uses the Protocol-5 locality kernel and Phase B uses the exact
witness-term cached lazy kernel. MVSTATE2 provides continuation state, while an
optional authenticated rank-history journal avoids rescoring the selected
prefix solely to reconstruct plan history.
"""
from __future__ import annotations

import math
import time
from typing import Any, Mapping

import numpy as np

from ._common import TrainingDataInputError
from .mvsel2_phase_a_kernel import (
    choose_target_multi_view_phase_a_candidate_v2_kernel,
)
from .mvsel2_phase_b_kernel import (
    build_target_multi_view_lazy_frontier_v2_kernel,
    choose_target_multi_view_phase_b_candidate_v2_kernel,
)
from .progress_timing import format_progress_fraction, format_progress_time
from .target_multi_view_selection_history_v2 import (
    TargetMultiViewSelectionHistoryV2,
)
from .target_multi_view_selector import (
    TargetMultiViewSelectionEntry,
    TargetMultiViewSelectionRung,
)
from .target_multi_view_selector_v2 import (
    TargetMultiViewCandidateScoreV2,
    TargetMultiViewForwardStateV2,
    TargetMultiViewLazyFrontierV2,
    TargetMultiViewSelectionDomainPlanV2,
    TargetMultiViewSelectionPlanV2,
    TargetMultiViewSelectorPolicyV2,
    build_target_multi_view_forward_state_v2,
    score_target_multi_view_candidate_v2,
    select_target_multi_view_candidate_v2,
)


def _phase_a(
    state: TargetMultiViewForwardStateV2,
    policy: TargetMultiViewSelectorPolicyV2,
) -> bool:
    return state.unsatisfied_required_obligation_count > 0 or any(
        item.coverage_mass
        < policy.coverage_threshold - policy.gain_tie_tolerance
        for item in state.family_states
    )


def _bottleneck_family_id(
    forward_domain: Any,
    state: TargetMultiViewForwardStateV2,
    policy: TargetMultiViewSelectorPolicyV2,
) -> str:
    ratios = np.asarray(
        [
            item.coverage_mass / float(policy.coverage_threshold)
            for item in state.family_states
        ],
        dtype=np.float64,
    )
    minimum = float(np.min(ratios))
    index = int(
        np.flatnonzero(ratios <= minimum + policy.gain_tie_tolerance)[0]
    )
    return str(forward_domain.families[index].family_id)


def _entry_from_score(
    reference_domain: Any,
    forward_domain: Any,
    score: TargetMultiViewCandidateScoreV2,
    *,
    rank: int,
    phase_a: bool,
    bottleneck_id: str | None,
) -> TargetMultiViewSelectionEntry:
    bottleneck_gain = 0.0
    if bottleneck_id is not None:
        bottleneck_index = next(
            index
            for index, family in enumerate(forward_domain.families)
            if family.family_id == bottleneck_id
        )
        bottleneck_gain = float(score.family_coverage_gains[bottleneck_index])
    return TargetMultiViewSelectionEntry(
        rank=int(rank),
        frame_uid=reference_domain.frame_uids[score.candidate_index],
        phase="hard_coverage" if phase_a else "representative_fill",
        primary_reason=(
            "hard_obligation_gain"
            if score.hard_obligation_gain > 0
            else "worst_view_coverage"
            if phase_a
            else "density_aware_representative_fill"
        ),
        bottleneck_family_id=bottleneck_id,
        hard_obligation_gain=score.hard_obligation_gain,
        bottleneck_coverage_gain=bottleneck_gain,
        total_coverage_gain=score.total_coverage_gain,
        representative_gain=score.representative_gain,
        normalized_diversity=score.sparse_diversity,
        correlation_unit_code=int(
            forward_domain.candidate_correlation_unit_codes[score.candidate_index]
        ),
    )


def _materialized_rung(
    entries: list[TargetMultiViewSelectionEntry],
    state: TargetMultiViewForwardStateV2,
    forward_domain: Any,
    policy: TargetMultiViewSelectorPolicyV2,
    *,
    target_size: int,
    previous_rung: int,
) -> TargetMultiViewSelectionRung:
    unsatisfied = tuple(
        sorted(
            item.obligation_id
            for index, item in enumerate(forward_domain.obligations)
            if item.required
            and int(state.obligation_counts[index])
            < int(item.minimum_selected_frames)
        )
    )
    coverage = tuple(
        (item.family_id, min(1.0, max(0.0, item.coverage_mass)))
        for item in state.family_states
    )
    shell = entries[previous_rung:target_size]
    return TargetMultiViewSelectionRung(
        target_size=int(target_size),
        materializable=True,
        frame_uids=tuple(item.frame_uid for item in entries),
        family_coverage=coverage,
        hard_obligations_passed=not unsatisfied,
        unsatisfied_obligation_ids=unsatisfied,
        hard_coverage_qualified=(
            not unsatisfied
            and all(
                value
                >= policy.coverage_threshold - policy.gain_tie_tolerance
                for _, value in coverage
            )
        ),
        phase_at_boundary=entries[-1].phase,
        shell_coverage_gain=float(
            np.sum(
                [item.total_coverage_gain for item in shell],
                dtype=np.float64,
            )
        ),
        shell_representative_gain=float(
            np.sum(
                [item.representative_gain for item in shell],
                dtype=np.float64,
            )
        ),
    )


def _history_from_progress(
    entries: list[TargetMultiViewSelectionEntry],
    rung_by_size: Mapping[int, TargetMultiViewSelectionRung],
    phase_a_completed_at: int | None,
) -> TargetMultiViewSelectionHistoryV2:
    return TargetMultiViewSelectionHistoryV2(
        entries=tuple(entries),
        rungs=tuple(rung_by_size[size] for size in sorted(rung_by_size)),
        phase_a_completed_at=phase_a_completed_at,
    )


def _validate_resume_history(
    history: TargetMultiViewSelectionHistoryV2,
    reference_domain: Any,
    restored: TargetMultiViewForwardStateV2,
) -> None:
    if history.selected_count != restored.selected_count:
        raise TrainingDataInputError(
            "MVSTATE2 rank history and continuation-state sizes disagree."
        )
    expected_uids = tuple(
        reference_domain.frame_uids[int(candidate)]
        for candidate in restored.selected_order
    )
    history_uids = tuple(entry.frame_uid for entry in history.entries)
    if history_uids != expected_uids:
        raise TrainingDataInputError(
            "MVSTATE2 rank history selected prefix disagrees with continuation state."
        )


def _replay_selected_prefix_history(
    reference_domain: Any,
    forward_domain: Any,
    selected_prefix: tuple[int, ...],
    materializable: tuple[int, ...],
    limit: int,
    policy: TargetMultiViewSelectorPolicyV2,
) -> TargetMultiViewSelectionHistoryV2:
    """Compatibility fallback for legacy checkpoints that predate rank history.

    Each historical candidate is scored exactly once. This replay reconstructs
    plan evidence only; the authenticated restored MVSTATE2 state remains the
    continuation authority after reconstruction.
    """

    replay_state = build_target_multi_view_forward_state_v2(
        reference_domain,
        forward_domain,
        coverage_threshold=policy.coverage_threshold,
        epsilon=policy.gain_tie_tolerance,
        requested_cardinality=limit,
    )
    entries: list[TargetMultiViewSelectionEntry] = []
    rung_by_size: dict[int, TargetMultiViewSelectionRung] = {}
    phase_a_completed_at: int | None = None
    previous_rung = 0
    for rank, candidate in enumerate(selected_prefix):
        phase_a = _phase_a(replay_state, policy)
        bottleneck_id = (
            _bottleneck_family_id(forward_domain, replay_state, policy)
            if phase_a
            else None
        )
        score = score_target_multi_view_candidate_v2(
            candidate, forward_domain, replay_state
        )
        entries.append(
            _entry_from_score(
                reference_domain,
                forward_domain,
                score,
                rank=rank,
                phase_a=phase_a,
                bottleneck_id=bottleneck_id,
            )
        )
        select_target_multi_view_candidate_v2(
            candidate,
            forward_domain,
            replay_state,
            score=score,
        )
        size = rank + 1
        if phase_a_completed_at is None and not _phase_a(replay_state, policy):
            phase_a_completed_at = size
        if size in materializable:
            rung_by_size[size] = _materialized_rung(
                entries,
                replay_state,
                forward_domain,
                policy,
                target_size=size,
                previous_rung=previous_rung,
            )
            previous_rung = size
    history = _history_from_progress(
        entries, rung_by_size, phase_a_completed_at
    )
    if history.selected_count != len(selected_prefix):
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 legacy resume history reconstruction failed."
        )
    return history


def build_target_multi_view_selection_plan_v2_engine(
    target_coverage_reference: Any,
    target_coverage_forward_index: Any,
    *,
    policy: TargetMultiViewSelectorPolicyV2 | None = None,
    batch_size: int = 256,
    workers: int = 1,
    frontier_rebuild_interval: int = 0,
    checkpoint_callback: Any | None = None,
    history_callback: Any | None = None,
    progress_callback: Any | None = None,
    progress_interval_seconds: float = 30.0,
    resume_states: Mapping[str, TargetMultiViewForwardStateV2] | None = None,
    resume_histories: Mapping[str, TargetMultiViewSelectionHistoryV2] | None = None,
) -> TargetMultiViewSelectionPlanV2:
    """Build or resume exact MVSEL2 through one production rank loop."""

    policy = policy or TargetMultiViewSelectorPolicyV2()
    batch_size = int(batch_size)
    workers = int(workers)
    if batch_size < 1 or workers < 1:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 batch/worker settings must be positive."
        )
    if (
        not math.isfinite(progress_interval_seconds)
        or progress_interval_seconds <= 0.0
    ):
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 progress interval must be positive."
        )
    if target_coverage_reference.dataset_id != target_coverage_forward_index.dataset_id:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 dataset identity mismatch."
        )
    resume_states = {} if resume_states is None else resume_states
    resume_histories = {} if resume_histories is None else resume_histories
    domains: list[TargetMultiViewSelectionDomainPlanV2] = []

    for reference_domain in target_coverage_reference.domains:
        domain_id = reference_domain.label_domain_id
        forward_domain = target_coverage_forward_index.domain(domain_id)
        materializable = tuple(
            size
            for size in policy.target_sizes
            if size <= forward_domain.candidate_count
        )
        if not materializable:
            raise TrainingDataInputError(
                "TARGET-DATA2C-MVSEL2 candidate pool is smaller than every target size."
            )
        limit = int(materializable[-1])
        restored = resume_states.get(domain_id)
        resume_size = 0 if restored is None else int(restored.selected_count)
        if resume_size < 0 or resume_size > limit:
            raise TrainingDataInputError(
                "TARGET-DATA2C-MVSEL2 resume size is invalid."
            )

        supplied_history = resume_histories.get(domain_id)
        if restored is None and supplied_history is not None:
            raise TrainingDataInputError(
                "TARGET-DATA2C-MVSEL2 rank history was supplied without MVSTATE2 state."
            )

        if restored is None:
            state = build_target_multi_view_forward_state_v2(
                reference_domain,
                forward_domain,
                coverage_threshold=policy.coverage_threshold,
                epsilon=policy.gain_tie_tolerance,
                requested_cardinality=limit,
            )
            entries: list[TargetMultiViewSelectionEntry] = []
            rung_by_size: dict[int, TargetMultiViewSelectionRung] = {}
            phase_a_completed_at: int | None = None
            history_mode = "rank_zero"
        else:
            selected_prefix = tuple(int(value) for value in restored.selected_order)
            if len(selected_prefix) != resume_size:
                raise TrainingDataInputError(
                    "TARGET-DATA2C-MVSEL2 resume prefix is inconsistent."
                )
            if supplied_history is None:
                history = _replay_selected_prefix_history(
                    reference_domain,
                    forward_domain,
                    selected_prefix,
                    materializable,
                    limit,
                    policy,
                )
                history_mode = "mvstate2+legacy_history_replay"
            else:
                _validate_resume_history(
                    supplied_history,
                    reference_domain,
                    restored,
                )
                history = supplied_history
                history_mode = "mvstate2+journal"
            entries = list(history.entries)
            rung_by_size = {
                int(rung.target_size): rung for rung in history.rungs
            }
            phase_a_completed_at = history.phase_a_completed_at
            state = restored

        previous_rung = max(rung_by_size, default=0)
        frontier: TargetMultiViewLazyFrontierV2 | None = None
        started = time.monotonic()
        last_progress = started
        completed_after_resume = 0
        cumulative_evaluation_edges = 0
        cumulative_mutation_edges = 0
        fallback_count = 0
        phase_b_resume_rebases = 0

        if progress_callback is not None:
            progress_callback(
                f"status=selecting; progress={format_progress_fraction(resume_size, limit)}; "
                f"elapsed={format_progress_time(0.0)}; eta=--:--:--; "
                f"phase=resume; domain={domain_id}; resume_size={resume_size}; "
                f"resume_mode={history_mode}"
            )

        for rank in range(resume_size, limit):
            phase_a = _phase_a(state, policy)
            if phase_a:
                choice = choose_target_multi_view_phase_a_candidate_v2_kernel(
                    reference_domain,
                    forward_domain,
                    state,
                    coverage_threshold=policy.coverage_threshold,
                    epsilon=policy.gain_tie_tolerance,
                    batch_size=batch_size,
                    workers=workers,
                )
                bottleneck_id = choice.bottleneck_family_id
                phase = "hard_coverage"
                evaluation_edges = (
                    choice.telemetry.candidate_evaluation_forward_edges
                )
                contender_width = choice.telemetry.final_contender_count
                rescoring_count = 0
                heap_entries = 0
            else:
                if frontier is None or (
                    frontier_rebuild_interval > 0
                    and rank % frontier_rebuild_interval == 0
                ):
                    frontier = build_target_multi_view_lazy_frontier_v2_kernel(
                        forward_domain, state
                    )
                    if restored is not None and completed_after_resume == 0:
                        phase_b_resume_rebases += 1
                choice = choose_target_multi_view_phase_b_candidate_v2_kernel(
                    reference_domain,
                    forward_domain,
                    state,
                    frontier,
                    epsilon=policy.gain_tie_tolerance,
                )
                bottleneck_id = None
                phase = "representative_fill"
                evaluation_edges = (
                    choice.telemetry.representative_evaluation_edges
                    + choice.telemetry.diversity_evaluation_edges
                )
                contender_width = choice.telemetry.certified_frontier_width
                rescoring_count = choice.telemetry.rescoring_count
                heap_entries = choice.telemetry.heap_entries
                fallback_count += int(choice.telemetry.fallback_used)

            score = choice.score
            entries.append(
                _entry_from_score(
                    reference_domain,
                    forward_domain,
                    score,
                    rank=rank,
                    phase_a=phase_a,
                    bottleneck_id=bottleneck_id,
                )
            )
            select_target_multi_view_candidate_v2(
                score.candidate_index,
                forward_domain,
                state,
                score=score,
            )
            mutation_edges = sum(
                len(family.candidate_witness_indices(score.candidate_index))
                for family in forward_domain.families
            ) + len(
                forward_domain.candidate_obligation_indices(score.candidate_index)
            )
            cumulative_evaluation_edges += int(evaluation_edges)
            cumulative_mutation_edges += int(mutation_edges)
            completed_after_resume += 1

            if phase_a_completed_at is None and not _phase_a(state, policy):
                phase_a_completed_at = rank + 1
            size = rank + 1
            if size in materializable:
                rung_by_size[size] = _materialized_rung(
                    entries,
                    state,
                    forward_domain,
                    policy,
                    target_size=size,
                    previous_rung=previous_rung,
                )
                previous_rung = size
                if checkpoint_callback is not None:
                    checkpoint_callback(
                        reference_domain,
                        forward_domain,
                        state,
                        size,
                    )
                if history_callback is not None:
                    history_callback(
                        reference_domain,
                        forward_domain,
                        _history_from_progress(
                            entries,
                            rung_by_size,
                            phase_a_completed_at,
                        ),
                        size,
                    )

            now = time.monotonic()
            if progress_callback is not None and (
                size == limit
                or size in materializable
                or now - last_progress >= progress_interval_seconds
            ):
                elapsed = now - started
                throughput = (
                    completed_after_resume / elapsed
                    if elapsed > 0.0
                    else 0.0
                )
                remaining = limit - size
                eta = remaining / throughput if throughput > 0.0 else None
                progress_callback(
                    f"status=selecting; progress={format_progress_fraction(size, limit)}; "
                    f"elapsed={format_progress_time(elapsed)}; eta={format_progress_time(eta)}; "
                    f"throughput={throughput:.3f} ranks/s; phase={phase}; rank={rank}; "
                    f"resume_size={resume_size}; resume_mode={history_mode}; "
                    f"phase_b_resume_rebases={phase_b_resume_rebases}; "
                    f"mutation_forward_edges={mutation_edges}; "
                    f"candidate_evaluation_forward_edges={evaluation_edges}; "
                    f"cumulative_mutation_edges={cumulative_mutation_edges}; "
                    f"cumulative_evaluation_edges={cumulative_evaluation_edges}; "
                    f"contender_width={contender_width}; "
                    f"rescoring_count={rescoring_count}; heap_entries={heap_entries}; "
                    f"fallback_count={fallback_count}"
                )
                last_progress = now

        rungs = tuple(
            rung_by_size.get(size)
            or TargetMultiViewSelectionRung(
                target_size=size,
                materializable=False,
                unavailable_reason=(
                    f"authorized_pool_has_{forward_domain.candidate_count}_frames_"
                    f"below_required_{size}"
                ),
            )
            for size in policy.target_sizes
        )
        domains.append(
            TargetMultiViewSelectionDomainPlanV2(
                label_domain_id=domain_id,
                reference_domain_digest=reference_domain.content_digest,
                mvidx1_domain_digest=forward_domain.mvidx1_domain_digest,
                candidate_count=forward_domain.candidate_count,
                master_order=tuple(entries),
                rungs=rungs,
                phase_a_completed_at=phase_a_completed_at,
            )
        )

    return TargetMultiViewSelectionPlanV2(
        dataset_id=target_coverage_reference.dataset_id,
        target_coverage_reference_digest=target_coverage_reference.content_digest,
        mvidx1_content_digest=target_coverage_forward_index.mvidx1_content_digest,
        policy=policy,
        domains=tuple(domains),
    )
