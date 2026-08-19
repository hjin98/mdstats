"""Contiguous complete-frame block construction.

The primitives in this module operate only on frame indices and finite scalar
observables.  They do not know about atoms, trajectories, VASP, or downstream
scientific roles.  Complete-system and training-data records adapt these generic
intervals without changing the source-independent numerical decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

import numpy as np

from ._common import (
    SamplingInputError,
    SamplingSerializationError,
    digest,
    finite_float,
)
from .autocorrelation import (
    AutocorrelationPolicy,
    integrated_autocorrelation_time,
)

FRAME_INTERVAL_SCHEMA = "mdstats.sampling-frame-interval.v1"
COMPLETE_FRAME_BLOCK_POLICY_SCHEMA = "mdstats.complete-frame-block-policy.v1"
COMPLETE_FRAME_BLOCK_PLAN_SCHEMA = "mdstats.complete-frame-block-plan.v1"
COMPLETE_FRAME_BLOCK_POLICY_VERSION = (
    "mdstats.complete-frame-block-policy.2026-07.v1"
)


@dataclass(frozen=True, slots=True, order=True)
class FrameInterval:
    """Half-open contiguous interval of stored frame indices."""

    frame_start: int
    frame_stop: int

    def __post_init__(self) -> None:
        if self.frame_start < 0 or self.frame_stop <= self.frame_start:
            raise SamplingInputError("Frame interval must be nonempty and nonnegative.")

    @property
    def frame_count(self) -> int:
        return self.frame_stop - self.frame_start

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FRAME_INTERVAL_SCHEMA,
            "frame_start": self.frame_start,
            "frame_stop": self.frame_stop,
        }

    @property
    def signature(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameInterval":
        if payload.get("schema") != FRAME_INTERVAL_SCHEMA:
            raise SamplingSerializationError("Unsupported sampling-frame-interval schema.")
        result = cls(
            frame_start=int(payload["frame_start"]),
            frame_stop=int(payload["frame_stop"]),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SamplingSerializationError("Sampling-frame-interval signature mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CompleteFrameBlockPolicy:
    """Policy for autocorrelation-aware complete-frame interval construction."""

    policy_version: str = COMPLETE_FRAME_BLOCK_POLICY_VERSION
    minimum_block_frames: int = 32
    autocorrelation_block_multiplier: float = 2.0
    explicit_block_length_frames: int | None = None
    remainder_strategy: str = "balanced_all_frames"
    autocorrelation_policy: AutocorrelationPolicy = AutocorrelationPolicy()

    def __post_init__(self) -> None:
        if not self.policy_version:
            raise SamplingInputError("Complete-frame block policy version is required.")
        if self.minimum_block_frames < 1:
            raise SamplingInputError("minimum_block_frames must be positive.")
        multiplier = finite_float(
            self.autocorrelation_block_multiplier,
            name="autocorrelation_block_multiplier",
        )
        if multiplier < 0.0:
            raise SamplingInputError(
                "autocorrelation_block_multiplier must be nonnegative."
            )
        if (
            self.explicit_block_length_frames is not None
            and self.explicit_block_length_frames < 1
        ):
            raise SamplingInputError(
                "explicit_block_length_frames must be positive."
            )
        if self.remainder_strategy != "balanced_all_frames":
            raise SamplingInputError("Unsupported block remainder strategy.")
        if not isinstance(self.autocorrelation_policy, AutocorrelationPolicy):
            raise SamplingInputError(
                "autocorrelation_policy must be AutocorrelationPolicy."
            )
        object.__setattr__(self, "autocorrelation_block_multiplier", multiplier)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": COMPLETE_FRAME_BLOCK_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "minimum_block_frames": self.minimum_block_frames,
            "autocorrelation_block_multiplier": self.autocorrelation_block_multiplier,
            "explicit_block_length_frames": self.explicit_block_length_frames,
            "remainder_strategy": self.remainder_strategy,
            "autocorrelation_policy": self.autocorrelation_policy.to_dict(),
        }

    @property
    def signature(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CompleteFrameBlockPolicy":
        if payload.get("schema") != COMPLETE_FRAME_BLOCK_POLICY_SCHEMA:
            raise SamplingSerializationError(
                "Unsupported complete-frame-block-policy schema."
            )
        result = cls(
            policy_version=str(payload["policy_version"]),
            minimum_block_frames=int(payload["minimum_block_frames"]),
            autocorrelation_block_multiplier=float(
                payload["autocorrelation_block_multiplier"]
            ),
            explicit_block_length_frames=(
                None
                if payload.get("explicit_block_length_frames") is None
                else int(payload["explicit_block_length_frames"])
            ),
            remainder_strategy=str(payload["remainder_strategy"]),
            autocorrelation_policy=AutocorrelationPolicy.from_dict(
                payload["autocorrelation_policy"]
            ),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SamplingSerializationError(
                "Complete-frame-block-policy signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class CompleteFrameBlockPlan:
    """Deterministic source-independent block plan over eligible frames."""

    policy_signature: str
    eligible_frame_indices: tuple[int, ...]
    contiguous_runs: tuple[FrameInterval, ...]
    block_intervals: tuple[FrameInterval, ...]
    observable_autocorrelation_times_frames: tuple[tuple[str, float], ...]
    maximum_autocorrelation_time_frames: float
    decorrelation_target_length_frames: int
    resolved_block_length_frames: int
    explicit_length_override: bool
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.policy_signature) != 64:
            raise SamplingInputError("policy_signature must be a SHA-256 digest.")
        indices = tuple(int(value) for value in self.eligible_frame_indices)
        if not indices:
            raise SamplingInputError("eligible_frame_indices must be nonempty.")
        if any(value < 0 for value in indices):
            raise SamplingInputError("Eligible frame indices must be nonnegative.")
        if tuple(sorted(set(indices))) != indices:
            raise SamplingInputError(
                "Eligible frame indices must be strictly increasing and unique."
            )
        runs = tuple(self.contiguous_runs)
        blocks = tuple(self.block_intervals)
        if not runs or not blocks:
            raise SamplingInputError("Block plan requires runs and blocks.")
        run_indices = tuple(
            index
            for interval in runs
            for index in range(interval.frame_start, interval.frame_stop)
        )
        block_indices = tuple(
            index
            for interval in blocks
            for index in range(interval.frame_start, interval.frame_stop)
        )
        if run_indices != indices or block_indices != indices:
            raise SamplingInputError(
                "Runs and blocks must cover every eligible frame exactly once."
            )
        tau_items = tuple(
            sorted(
                (str(name), finite_float(value, name="autocorrelation time"))
                for name, value in self.observable_autocorrelation_times_frames
            )
        )
        tau_names = tuple(name for name, _ in tau_items)
        if any(not name for name in tau_names) or len(set(tau_names)) != len(tau_names):
            raise SamplingInputError(
                "Observable autocorrelation names must be nonempty and unique."
            )
        if any(value <= 0.0 for _, value in tau_items):
            raise SamplingInputError(
                "Observable autocorrelation times must be positive."
            )
        maximum_tau = finite_float(
            self.maximum_autocorrelation_time_frames,
            name="maximum_autocorrelation_time_frames",
        )
        if maximum_tau <= 0.0:
            raise SamplingInputError(
                "maximum_autocorrelation_time_frames must be positive."
            )
        if tau_items and maximum_tau != max(value for _, value in tau_items):
            raise SamplingInputError(
                "maximum_autocorrelation_time_frames must equal the recorded "
                "observable maximum."
            )
        if self.decorrelation_target_length_frames < 1:
            raise SamplingInputError(
                "decorrelation_target_length_frames must be positive."
            )
        if self.resolved_block_length_frames < 1:
            raise SamplingInputError(
                "resolved_block_length_frames must be positive."
            )
        object.__setattr__(self, "eligible_frame_indices", indices)
        object.__setattr__(self, "contiguous_runs", runs)
        object.__setattr__(self, "block_intervals", blocks)
        object.__setattr__(
            self, "observable_autocorrelation_times_frames", tau_items
        )
        object.__setattr__(
            self, "maximum_autocorrelation_time_frames", maximum_tau
        )
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": COMPLETE_FRAME_BLOCK_PLAN_SCHEMA,
            "policy_signature": self.policy_signature,
            "eligible_frame_indices": list(self.eligible_frame_indices),
            "contiguous_runs": [item.to_dict() for item in self.contiguous_runs],
            "block_intervals": [item.to_dict() for item in self.block_intervals],
            "observable_autocorrelation_times_frames": [
                [name, value]
                for name, value in self.observable_autocorrelation_times_frames
            ],
            "maximum_autocorrelation_time_frames": self.maximum_autocorrelation_time_frames,
            "decorrelation_target_length_frames": self.decorrelation_target_length_frames,
            "resolved_block_length_frames": self.resolved_block_length_frames,
            "explicit_length_override": self.explicit_length_override,
            "notes": list(self.notes),
        }

    @property
    def signature(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CompleteFrameBlockPlan":
        if payload.get("schema") != COMPLETE_FRAME_BLOCK_PLAN_SCHEMA:
            raise SamplingSerializationError(
                "Unsupported complete-frame-block-plan schema."
            )
        result = cls(
            policy_signature=str(payload["policy_signature"]),
            eligible_frame_indices=tuple(
                int(value) for value in payload["eligible_frame_indices"]
            ),
            contiguous_runs=tuple(
                FrameInterval.from_dict(item) for item in payload["contiguous_runs"]
            ),
            block_intervals=tuple(
                FrameInterval.from_dict(item) for item in payload["block_intervals"]
            ),
            observable_autocorrelation_times_frames=tuple(
                (str(item[0]), float(item[1]))
                for item in payload["observable_autocorrelation_times_frames"]
            ),
            maximum_autocorrelation_time_frames=float(
                payload["maximum_autocorrelation_time_frames"]
            ),
            decorrelation_target_length_frames=int(
                payload["decorrelation_target_length_frames"]
            ),
            resolved_block_length_frames=int(
                payload["resolved_block_length_frames"]
            ),
            explicit_length_override=bool(payload["explicit_length_override"]),
            notes=tuple(str(value) for value in payload.get("notes", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SamplingSerializationError(
                "Complete-frame-block-plan signature mismatch."
            )
        return result


def contiguous_frame_runs(
    frame_indices: Sequence[int] | np.ndarray,
) -> tuple[FrameInterval, ...]:
    """Return maximal contiguous half-open intervals for sorted unique indices."""

    indices = np.asarray(frame_indices, dtype=np.int64)
    if indices.ndim != 1:
        raise SamplingInputError("frame_indices must be one-dimensional.")
    if indices.size == 0:
        return ()
    if np.any(indices < 0):
        raise SamplingInputError("frame_indices must be nonnegative.")
    if np.any(np.diff(indices) <= 0):
        raise SamplingInputError(
            "frame_indices must be strictly increasing and unique."
        )
    breaks = np.flatnonzero(np.diff(indices) != 1) + 1
    chunks = np.split(indices, breaks)
    return tuple(
        FrameInterval(int(chunk[0]), int(chunk[-1]) + 1) for chunk in chunks
    )


def split_frame_interval(
    frame_start: int,
    frame_stop: int,
    target_block_frames: int,
) -> tuple[FrameInterval, ...]:
    """Split one interval into balanced blocks while retaining every frame.

    The number of blocks is ``max(1, floor(length / target))``.  Remainder
    frames are distributed one by one from the earliest block.  This exactly
    matches the historical STAT1/SAMP0 behavior.
    """

    interval = FrameInterval(int(frame_start), int(frame_stop))
    if target_block_frames < 1:
        raise SamplingInputError("target_block_frames must be positive.")
    length = interval.frame_count
    if length <= target_block_frames:
        return (interval,)
    block_count = max(1, length // target_block_frames)
    base, remainder = divmod(length, block_count)
    result: list[FrameInterval] = []
    cursor = interval.frame_start
    for index in range(block_count):
        width = base + (1 if index < remainder else 0)
        result.append(FrameInterval(cursor, cursor + width))
        cursor += width
    return tuple(result)


def _validated_observables(
    frame_observables: Mapping[str, Sequence[float] | np.ndarray],
    *,
    eligible_frame_indices: np.ndarray,
) -> dict[str, np.ndarray]:
    result: dict[str, np.ndarray] = {}
    for name, values in frame_observables.items():
        key = str(name)
        if not key:
            raise SamplingInputError("Observable names must be nonempty.")
        vector = np.asarray(values, dtype=np.float64)
        if vector.ndim != 1 or vector.size <= int(eligible_frame_indices[-1]):
            raise SamplingInputError(
                f"Frame observable {key!r} must be one-dimensional and cover "
                "every eligible frame."
            )
        if np.any(~np.isfinite(vector[eligible_frame_indices])):
            raise SamplingInputError(
                f"Frame observable {key!r} must be finite on eligible frames."
            )
        result[key] = vector
    return result


def build_complete_frame_block_plan(
    *,
    eligible_frame_indices: Sequence[int] | np.ndarray,
    frame_observables: Mapping[str, Sequence[float] | np.ndarray],
    policy: CompleteFrameBlockPolicy | None = None,
) -> CompleteFrameBlockPlan:
    """Build a deterministic block plan without crossing a frame-index gap."""

    active = CompleteFrameBlockPolicy() if policy is None else policy
    indices = np.asarray(eligible_frame_indices, dtype=np.int64)
    runs = contiguous_frame_runs(indices)
    if not runs:
        raise SamplingInputError("At least one eligible frame is required.")
    observables = _validated_observables(
        frame_observables,
        eligible_frame_indices=indices,
    )

    per_observable: list[tuple[str, float]] = []
    maximum_tau = active.autocorrelation_policy.minimum_tau_frames
    for name, values in sorted(observables.items()):
        local = tuple(
            integrated_autocorrelation_time(
                values[run.frame_start : run.frame_stop],
                policy=active.autocorrelation_policy,
            )
            for run in runs
        )
        observable_tau = max(
            local,
            default=active.autocorrelation_policy.minimum_tau_frames,
        )
        per_observable.append((name, observable_tau))
        maximum_tau = max(maximum_tau, observable_tau)

    decorrelation_target = max(
        1,
        int(math.ceil(active.autocorrelation_block_multiplier * maximum_tau)),
    )
    resolved = max(active.minimum_block_frames, decorrelation_target)
    explicit = active.explicit_block_length_frames is not None
    if explicit:
        resolved = int(active.explicit_block_length_frames)

    blocks = tuple(
        block
        for run in runs
        for block in split_frame_interval(
            run.frame_start,
            run.frame_stop,
            resolved,
        )
    )
    notes: list[str] = []
    if explicit and resolved < decorrelation_target:
        notes.append(
            "explicit block length is shorter than the autocorrelation-derived target"
        )
    if not observables:
        notes.append(
            "no observables supplied; the autocorrelation policy floor controls the target"
        )
    return CompleteFrameBlockPlan(
        policy_signature=active.signature,
        eligible_frame_indices=tuple(int(value) for value in indices),
        contiguous_runs=runs,
        block_intervals=blocks,
        observable_autocorrelation_times_frames=tuple(per_observable),
        maximum_autocorrelation_time_frames=maximum_tau,
        decorrelation_target_length_frames=decorrelation_target,
        resolved_block_length_frames=resolved,
        explicit_length_override=explicit,
        notes=tuple(notes),
    )
