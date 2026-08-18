"""Structured progress reporting ports for long-running mdstats operations.

Computational modules emit immutable :class:`ProgressEvent` records through a
small :class:`ProgressPort` protocol.  Modules never configure global logging,
print directly, or assume a particular user interface.  Applications may bind
that port to stdout/stderr, ``logging.Logger``, a GUI, a notebook progress bar,
or a custom callback.
"""

from __future__ import annotations

import logging
import os
from numbers import Integral, Real
import sys
import time
import warnings
from threading import Lock
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Callable, Literal, Mapping, Protocol, TextIO, runtime_checkable

PROGRESS_EVENT_SCHEMA = "mdstats.progress-event.v1"
ProgressStatus = Literal["started", "running", "completed", "warning", "info"]
ProgressMetadataValue = str | int | float | bool | None
ProgressMetadata = Mapping[str, ProgressMetadataValue]


class ProgressError(ValueError):
    """Raised when a progress event or port configuration is invalid."""


def _nonempty_text(value: str, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProgressError(f"{name} must be a nonempty string.")
    return value.strip()


def _optional_count(value: int | None, *, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Integral) or value < 0:
        raise ProgressError(f"{name} must be a nonnegative integer or None.")
    return int(value)


def _metadata(value: ProgressMetadata | None) -> ProgressMetadata:
    if value is None:
        return MappingProxyType({})
    result: dict[str, ProgressMetadataValue] = {}
    for raw_key, raw_value in value.items():
        key = _nonempty_text(str(raw_key), name="metadata key")
        if raw_value is None or isinstance(raw_value, (str, bool)):
            result[key] = raw_value
        elif isinstance(raw_value, Integral):
            result[key] = int(raw_value)
        elif isinstance(raw_value, Real):
            result[key] = float(raw_value)
        else:
            raise ProgressError(
                "Progress metadata values must be scalar str/int/float/bool/None values."
            )
    return MappingProxyType(result)


@dataclass(frozen=True, slots=True)
class ProgressEvent:
    """One immutable, UI-neutral progress record.

    ``current`` and ``total`` identify the current work position and total work
    units. They are omitted for stage-only messages.  ``metadata`` is deliberately restricted to small
    scalar values so progress reporting cannot retain scientific arrays or
    materially change resource use.
    """

    source: str
    stage: str
    message: str
    status: ProgressStatus = "running"
    current: int | None = None
    total: int | None = None
    unit: str | None = None
    metadata: ProgressMetadata = field(default_factory=dict)
    schema_version: str = PROGRESS_EVENT_SCHEMA

    def __post_init__(self) -> None:
        source = _nonempty_text(self.source, name="source")
        stage = _nonempty_text(self.stage, name="stage")
        message = _nonempty_text(self.message, name="message")
        if self.status not in {"started", "running", "completed", "warning", "info"}:
            raise ProgressError(f"Unsupported progress status {self.status!r}.")
        current = _optional_count(self.current, name="current")
        total = _optional_count(self.total, name="total")
        if current is not None and total is None:
            raise ProgressError("current requires total.")
        if total is not None and current is None:
            raise ProgressError("total requires current.")
        if current is not None and total is not None and current > total:
            raise ProgressError("current cannot exceed total.")
        unit = None if self.unit is None else _nonempty_text(self.unit, name="unit")
        if unit is not None and total is None:
            raise ProgressError("unit requires current and total.")
        schema = _nonempty_text(self.schema_version, name="schema_version")
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "stage", stage)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "current", current)
        object.__setattr__(self, "total", total)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "metadata", _metadata(self.metadata))
        object.__setattr__(self, "schema_version", schema)

    @property
    def fraction(self) -> float | None:
        if self.current is None or self.total is None or self.total == 0:
            return None
        return float(self.current) / float(self.total)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "stage": self.stage,
            "message": self.message,
            "status": self.status,
            "current": self.current,
            "total": self.total,
            "unit": self.unit,
            "metadata": dict(self.metadata),
            "schema_version": self.schema_version,
        }


@runtime_checkable
class ProgressPort(Protocol):
    """Minimal port implemented by progress consumers."""

    def emit(self, event: ProgressEvent, /) -> None:
        """Consume one progress event."""


ProgressEventCallback = Callable[[ProgressEvent], None]
LegacyProgressCallback = Callable[[str], None]
ProgressPortLike = ProgressPort | ProgressEventCallback


class NullProgressPort:
    """No-op progress port."""

    __slots__ = ()

    def emit(self, event: ProgressEvent, /) -> None:
        if not isinstance(event, ProgressEvent):
            raise TypeError("event must be a ProgressEvent.")


NULL_PROGRESS_PORT = NullProgressPort()


@dataclass(slots=True)
class CallbackProgressPort:
    """Adapter from a structured event callback to :class:`ProgressPort`."""

    callback: ProgressEventCallback

    def __post_init__(self) -> None:
        if not callable(self.callback):
            raise TypeError("callback must be callable.")

    def emit(self, event: ProgressEvent, /) -> None:
        self.callback(event)


@dataclass(slots=True)
class LegacyTextCallbackPort:
    """Compatibility adapter for the former ``Callable[[str], None]`` API."""

    callback: LegacyProgressCallback

    def __post_init__(self) -> None:
        if not callable(self.callback):
            raise TypeError("callback must be callable.")

    def emit(self, event: ProgressEvent, /) -> None:
        self.callback(format_progress_event(event, include_source=False))


class TextProgressPort:
    """Human-readable stream port with one shared elapsed-time origin."""

    def __init__(
        self,
        *,
        label: str = "mdstats",
        stream: TextIO | None = None,
        enabled: bool = True,
        show_source: bool = False,
        started_at: float | None = None,
    ) -> None:
        self.label = _nonempty_text(label, name="label")
        self.stream = sys.stderr if stream is None else stream
        self.enabled = bool(enabled)
        self.show_source = bool(show_source)
        self.started_at = time.perf_counter() if started_at is None else float(started_at)
        self._lock = Lock()

    def emit(self, event: ProgressEvent, /) -> None:
        if not isinstance(event, ProgressEvent):
            raise TypeError("event must be a ProgressEvent.")
        if not self.enabled:
            return
        elapsed = max(0.0, time.perf_counter() - self.started_at)
        text = format_progress_event(event, include_source=self.show_source)
        with self._lock:
            print(
                f"[{self.label} | {elapsed:8.1f} s] {text}",
                file=self.stream,
                flush=True,
            )


class LoggingProgressPort:
    """Adapter that writes structured progress through ``logging.Logger``."""

    def __init__(
        self,
        logger: logging.Logger,
        *,
        level: int = logging.INFO,
        include_source: bool = True,
    ) -> None:
        if not isinstance(logger, logging.Logger):
            raise TypeError("logger must be a logging.Logger.")
        self.logger = logger
        self.level = int(level)
        self.include_source = bool(include_source)

    def emit(self, event: ProgressEvent, /) -> None:
        self.logger.log(
            self.level,
            format_progress_event(event, include_source=self.include_source),
            extra={"mdstats_progress": event.to_dict()},
        )


def format_progress_event(event: ProgressEvent, *, include_source: bool = True) -> str:
    """Format one event without adding timestamps or configuring a logger."""
    if not isinstance(event, ProgressEvent):
        raise TypeError("event must be a ProgressEvent.")
    prefix = f"{event.source}: " if include_source else ""
    count = ""
    if event.current is not None and event.total is not None:
        unit = "" if event.unit is None else f" {event.unit}"
        count = f" [{event.current}/{event.total}{unit}]"
    return f"{prefix}{event.stage}{count}: {event.message}"


def environment_progress_enabled(name: str) -> bool:
    token = os.environ.get(name, "").strip().lower()
    return token not in {"", "0", "false", "no", "off"}


def resolve_progress_port(
    progress: ProgressPortLike | None = None,
    *,
    progress_callback: LegacyProgressCallback | None = None,
    environment_variable: str | None = None,
    environment_label: str = "mdstats",
    environment_stream: TextIO | None = None,
) -> ProgressPort:
    """Resolve the structured port and preserve the legacy string callback.

    New module APIs should expose ``progress``.  ``progress_callback`` is a
    compatibility-only alias and must not be combined with ``progress``.
    """
    if progress is not None and progress_callback is not None:
        raise ProgressError("Specify progress or progress_callback, not both.")
    if progress_callback is not None:
        warnings.warn(
            "progress_callback is deprecated; pass a ProgressPort through progress=.",
            DeprecationWarning,
            stacklevel=3,
        )
        return LegacyTextCallbackPort(progress_callback)
    if progress is not None:
        if isinstance(progress, ProgressPort):
            return progress
        if callable(progress):
            return CallbackProgressPort(progress)
        raise TypeError("progress must implement ProgressPort or be callable.")
    if environment_variable and environment_progress_enabled(environment_variable):
        return TextProgressPort(
            label=environment_label,
            stream=environment_stream,
            show_source=True,
        )
    return NULL_PROGRESS_PORT


class ProgressEmitter:
    """Module-side helper that emits validated events through one port."""

    __slots__ = ("port", "source")

    def __init__(self, port: ProgressPort, *, source: str) -> None:
        if not isinstance(port, ProgressPort):
            raise TypeError("port must implement ProgressPort.")
        self.port = port
        self.source = _nonempty_text(source, name="source")

    def emit(
        self,
        stage: str,
        message: str,
        *,
        status: ProgressStatus = "running",
        current: int | None = None,
        total: int | None = None,
        unit: str | None = None,
        metadata: ProgressMetadata | None = None,
    ) -> None:
        self.port.emit(
            ProgressEvent(
                source=self.source,
                stage=stage,
                message=message,
                status=status,
                current=current,
                total=total,
                unit=unit,
                metadata={} if metadata is None else metadata,
            )
        )

    def started(self, stage: str, message: str, **kwargs: Any) -> None:
        self.emit(stage, message, status="started", **kwargs)

    def update(self, stage: str, message: str, **kwargs: Any) -> None:
        self.emit(stage, message, status="running", **kwargs)

    def completed(self, stage: str, message: str, **kwargs: Any) -> None:
        self.emit(stage, message, status="completed", **kwargs)

    def warning(self, stage: str, message: str, **kwargs: Any) -> None:
        self.emit(stage, message, status="warning", **kwargs)

    def child(self, source: str) -> "ProgressEmitter":
        return ProgressEmitter(self.port, source=source)
