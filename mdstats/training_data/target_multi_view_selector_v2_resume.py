"""Compatibility facade for MVSEL2 authenticated continuation.

The production rank loop lives exclusively in ``mvsel2_selection_engine``.
This module retains the established resumable entry point and the small helper
that restores checkpointed FP64 history after independent MVSTATE2 validation.
"""
from __future__ import annotations

from typing import Any, Mapping

from ._common import TrainingDataInputError
from .mvsel2_selection_engine import (
    build_target_multi_view_selection_plan_v2_engine,
)
from .target_multi_view_selection_history_v2 import (
    TargetMultiViewSelectionHistoryV2,
)
from .target_multi_view_selector_v2 import (
    TargetMultiViewForwardStateV2,
    TargetMultiViewSelectionPlanV2,
    TargetMultiViewSelectorPolicyV2,
)


def preserve_checkpoint_float_history_v2(
    checkpoint: Any,
    restored_state: TargetMultiViewForwardStateV2,
) -> TargetMultiViewForwardStateV2:
    """Retain authenticated stored FP64 history after structural validation.

    MVSTATE2 restore independently recomputes masses and representative utility
    to validate the checkpoint. Exact continuation then restores the stored
    values because recomputation can change last bits at a frozen tolerance tie.
    """

    if len(checkpoint.family_coverage_mass) != len(restored_state.family_states):
        raise TrainingDataInputError(
            "MVSTATE2 stored family-mass cardinality mismatch."
        )
    for family_state, stored_mass in zip(
        restored_state.family_states,
        checkpoint.family_coverage_mass,
        strict=True,
    ):
        family_state.coverage_mass = float(stored_mass)
    restored_state.representative_utility = float(
        checkpoint.representative_utility
    )
    return restored_state


def build_target_multi_view_selection_plan_v2_resumable(
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
    """Compatibility entry point delegating to the single production engine."""

    return build_target_multi_view_selection_plan_v2_engine(
        target_coverage_reference,
        target_coverage_forward_index,
        policy=policy,
        batch_size=batch_size,
        workers=workers,
        frontier_rebuild_interval=frontier_rebuild_interval,
        checkpoint_callback=checkpoint_callback,
        history_callback=history_callback,
        progress_callback=progress_callback,
        progress_interval_seconds=progress_interval_seconds,
        resume_states=resume_states,
        resume_histories=resume_histories,
    )
