"""Semantic relationship between frames in an atomistic collection."""

from __future__ import annotations

from enum import Enum


class FrameSemantics(str, Enum):
    """Describe whether frames form a time series or independent samples.

    ``TRAJECTORY`` means that frame order, source times, and continuity between
    adjacent frames are physically meaningful. ``ENSEMBLE`` means that frames
    are independent samples; their stored order is only an indexing choice.
    """

    TRAJECTORY = "trajectory"
    ENSEMBLE = "ensemble"


def coerce_frame_semantics(value: FrameSemantics | str) -> FrameSemantics:
    """Return a validated :class:`FrameSemantics` value."""
    if isinstance(value, FrameSemantics):
        return value
    try:
        return FrameSemantics(str(value))
    except ValueError as exc:
        allowed = ", ".join(item.value for item in FrameSemantics)
        raise ValueError(
            f"frame_semantics must be one of {{{allowed}}}; received {value!r}."
        ) from exc
