"""Small wall-clock progress-rate helpers for MLFF campaign reporting.

The training-data pipeline often computes work in batches and then publishes
many logical completions together.  A callback-drain rate is not a compute
throughput rate, so ETA calculations must be based on wall-clock work since a
stable baseline rather than on arbitrarily short callback bursts.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


PROGRESS_TIME_UNKNOWN = "--:--:--"

def format_progress_time(seconds: float | None) -> str:
    """Format an MLFF progress duration as fixed-width ``HH:MM:SS``.

    Unknown, non-finite, or negative estimates use ``--:--:--``.  Elapsed
    values should normally be passed as non-negative numbers; accepting an
    unknown value here keeps every user-facing ``eta=`` field syntactically
    stable while a rate estimate is still warming up.
    """

    if seconds is None:
        return PROGRESS_TIME_UNKNOWN
    value = float(seconds)
    if not math.isfinite(value) or value < 0.0:
        return PROGRESS_TIME_UNKNOWN
    rounded = max(0, int(round(value)))
    hours, remainder = divmod(rounded, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_progress_fraction(completed: int, total: int) -> str:
    """Return the canonical MLFF ``completed/total (percent)`` field."""

    done = int(completed)
    count = int(total)
    if count < 0 or done < 0 or done > count:
        raise ValueError("progress counts must satisfy 0 <= completed <= total")
    percent = 100.0 if count == 0 else 100.0 * done / count
    return f"{done:,}/{count:,} ({percent:.1f}%)"


def format_progress_rate(rate: float | None, unit: str, *, precision: int = 2) -> str:
    """Return one canonical MLFF throughput value, including its unit."""

    if rate is None:
        return f"-- {unit}"
    value = float(rate)
    if not math.isfinite(value) or value <= 0.0:
        return f"-- {unit}"
    return f"{value:.{int(precision)}f} {unit}"


def format_progress_timing_fields(
    *,
    elapsed_seconds: float,
    eta_seconds: float | None,
    recent_rate: float | None = None,
    average_rate: float | None = None,
    rate_unit: str | None = None,
    rate_precision: int = 2,
) -> str:
    """Format canonical timing/rate fields for MLFF progress messages.

    Field order is intentionally stable across campaign stages: elapsed, ETA,
    recent/current rate, then cumulative average rate.
    """

    fields = [
        f"elapsed={format_progress_time(max(0.0, float(elapsed_seconds)))}",
        f"eta={format_progress_time(eta_seconds)}",
    ]
    if rate_unit is not None and recent_rate is not None:
        fields.append(
            f"recent={format_progress_rate(recent_rate, rate_unit, precision=rate_precision)}"
        )
    if rate_unit is not None and average_rate is not None:
        fields.append(
            f"avg={format_progress_rate(average_rate, rate_unit, precision=rate_precision)}"
        )
    return "; ".join(fields)


@dataclass(frozen=True, slots=True)
class ProgressTimingSnapshot:
    """One stable progress timing estimate."""

    average_rate: float
    recent_rate: float
    eta_seconds: float | None
    elapsed_seconds: float


class ProgressRateTracker:
    """Track cumulative and recent rates without sampling callback bursts.

    ``average_rate`` and ETA use all actual work completed since the current
    baseline.  ``recent_rate`` is an EWMA, but a new sample is accepted only
    after ``minimum_recent_window_seconds`` of wall time.  This prevents a
    batched producer from looking thousands of times faster merely because it
    emits many completion callbacks after the numerical batch has finished.
    """

    __slots__ = (
        "alpha",
        "baseline_completed",
        "minimum_recent_window_seconds",
        "recent_rate",
        "sample_completed",
        "sample_started",
        "started",
    )

    def __init__(
        self,
        *,
        completed: int = 0,
        started_at: float,
        minimum_recent_window_seconds: float = 1.0,
        alpha: float = 0.35,
    ) -> None:
        if completed < 0:
            raise ValueError("completed must be nonnegative")
        if minimum_recent_window_seconds <= 0.0:
            raise ValueError("minimum_recent_window_seconds must be positive")
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = float(alpha)
        self.minimum_recent_window_seconds = float(minimum_recent_window_seconds)
        self.reset(completed=completed, now=float(started_at))

    def reset(self, *, completed: int, now: float) -> None:
        if completed < 0:
            raise ValueError("completed must be nonnegative")
        self.baseline_completed = int(completed)
        self.started = float(now)
        self.sample_completed = int(completed)
        self.sample_started = float(now)
        self.recent_rate = 0.0

    def snapshot(
        self,
        *,
        completed: int,
        total: int,
        now: float,
    ) -> ProgressTimingSnapshot:
        completed = int(completed)
        total = int(total)
        now = float(now)
        if total < 0 or completed < 0 or completed > total:
            raise ValueError("progress counts must satisfy 0 <= completed <= total")
        if completed < self.baseline_completed:
            raise ValueError("completed cannot precede the timing baseline")

        elapsed = max(0.0, now - self.started)
        completed_since_baseline = completed - self.baseline_completed
        average_rate = (
            completed_since_baseline / elapsed
            if completed_since_baseline > 0 and elapsed > 0.0
            else 0.0
        )

        sample_elapsed = max(0.0, now - self.sample_started)
        sample_delta = completed - self.sample_completed
        if (
            sample_delta > 0
            and sample_elapsed >= self.minimum_recent_window_seconds
        ):
            instantaneous_rate = sample_delta / sample_elapsed
            self.recent_rate = (
                instantaneous_rate
                if self.recent_rate <= 0.0
                else self.alpha * instantaneous_rate
                + (1.0 - self.alpha) * self.recent_rate
            )
            self.sample_completed = completed
            self.sample_started = now

        # ETA intentionally uses the cumulative post-baseline rate.  The recent
        # rate is useful diagnostics, but on batched/parallel pipelines it can
        # legitimately be bursty even with a minimum sampling window.  A stable
        # cumulative ETA is preferable to optimistic countdowns that jump by
        # orders of magnitude.
        remaining = total - completed
        if remaining == 0:
            eta_seconds: float | None = 0.0
        elif average_rate > 0.0:
            eta_seconds = remaining / average_rate
        else:
            eta_seconds = None
        return ProgressTimingSnapshot(
            average_rate=float(average_rate),
            recent_rate=float(self.recent_rate),
            eta_seconds=eta_seconds,
            elapsed_seconds=float(elapsed),
        )
