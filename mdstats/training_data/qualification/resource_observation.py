"""What the qualification actually consumed, as immutable release evidence.

The resource *scope* digest says which machine budget a run was entitled to.
That is identity, not measurement: it is the same whether a component took two
seconds or two days. Target-machine qualification has to record what the run
actually cost, so this module owns one immutable observation record bound to the
exact attempt.

It is evidence, never policy. Free disk and RAM fluctuate for reasons that have
nothing to do with the product, so an observation never stales numerical
evidence. The one place it can act is safety: the campaign already declares a
free-disk reserve, and materializing large deployment artifacts or dynamics
scratch below that reserve is an operational failure, not a scientific result.
Reading that existing reserve is not a new storage authority - deduplication,
archival, inventory, and cross-owner admission remain the successor workplan's.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
import os
import shutil

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .errors import QualificationError

RESOURCE_OBSERVATION_SCHEMA = "mdstats.qualification-resource-observation.v1"
COMPONENT_TIMING_SCHEMA = "mdstats.qualification-component-timing.v1"
FILESYSTEM_SAMPLE_SCHEMA = "mdstats.qualification-filesystem-sample.v1"

_BYTES_PER_GIB = 1024 ** 3


class QualificationDiskReserveError(QualificationError):
    """The configured free-disk reserve would be violated by this work."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class FilesystemSample:
    """One point-in-time filesystem observation for the attempt workspace."""

    label: str
    observed_at: str
    total_bytes: int
    free_bytes: int
    attempt_footprint_bytes: int

    def __post_init__(self) -> None:
        label = str(self.label).strip()
        if not label:
            raise TrainingDataInputError("A filesystem sample requires a label.")
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "observed_at", str(self.observed_at))
        for name in ("total_bytes", "free_bytes", "attempt_footprint_bytes"):
            value = int(getattr(self, name))
            if value < 0:
                raise TrainingDataInputError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, value)

    @property
    def free_gib(self) -> float:
        return self.free_bytes / _BYTES_PER_GIB

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": FILESYSTEM_SAMPLE_SCHEMA,
            "label": self.label,
            "observed_at": self.observed_at,
            "total_bytes": self.total_bytes,
            "free_bytes": self.free_bytes,
            "attempt_footprint_bytes": self.attempt_footprint_bytes,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FilesystemSample":
        if payload.get("schema") != FILESYSTEM_SAMPLE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported filesystem-sample schema.")
        return cls(
            label=str(payload["label"]),
            observed_at=str(payload["observed_at"]),
            total_bytes=int(payload["total_bytes"]),
            free_bytes=int(payload["free_bytes"]),
            attempt_footprint_bytes=int(payload["attempt_footprint_bytes"]),
        )


@dataclass(frozen=True, slots=True)
class ComponentTiming:
    """Elapsed wall time for one qualification component."""

    component: str
    started_at: str
    finished_at: str
    elapsed_seconds: float
    reused: bool = False

    def __post_init__(self) -> None:
        component = str(self.component).strip()
        if not component:
            raise TrainingDataInputError("A component timing requires a component name.")
        object.__setattr__(self, "component", component)
        elapsed = float(self.elapsed_seconds)
        if elapsed < 0.0 or elapsed != elapsed:
            raise TrainingDataInputError("Elapsed seconds must be finite and nonnegative.")
        object.__setattr__(self, "elapsed_seconds", elapsed)
        object.__setattr__(self, "started_at", str(self.started_at))
        object.__setattr__(self, "finished_at", str(self.finished_at))
        object.__setattr__(self, "reused", bool(self.reused))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": COMPONENT_TIMING_SCHEMA,
            "component": self.component,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "elapsed_seconds": self.elapsed_seconds,
            "reused": self.reused,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ComponentTiming":
        if payload.get("schema") != COMPONENT_TIMING_SCHEMA:
            raise TrainingDataSerializationError("Unsupported component-timing schema.")
        return cls(
            component=str(payload["component"]),
            started_at=str(payload["started_at"]),
            finished_at=str(payload["finished_at"]),
            elapsed_seconds=float(payload["elapsed_seconds"]),
            reused=bool(payload.get("reused", False)),
        )


@dataclass(frozen=True, slots=True)
class QualificationResourceObservation:
    """Immutable measured cost of one exact qualification attempt."""

    binding_digest: str
    attempt_identity: str
    resource_scope_digest: str
    started_at: str
    finished_at: str
    elapsed_seconds: float
    component_timings: tuple[ComponentTiming, ...]
    filesystem_samples: tuple[FilesystemSample, ...]
    minimum_free_disk_gib: float
    disk_reserve_satisfied: bool
    peak_process_rss_bytes: int | None
    accelerator_model: str | None
    accelerator_total_memory_bytes: int | None
    accelerator_peak_allocated_bytes: int | None
    runtime_identity_digest: str | None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("binding_digest", "attempt_identity", "resource_scope_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.runtime_identity_digest is not None:
            object.__setattr__(
                self,
                "runtime_identity_digest",
                validate_digest(self.runtime_identity_digest, name="runtime_identity_digest"),
            )
        elapsed = float(self.elapsed_seconds)
        if elapsed < 0.0:
            raise TrainingDataInputError("Elapsed seconds must be nonnegative.")
        object.__setattr__(self, "elapsed_seconds", elapsed)
        object.__setattr__(
            self,
            "component_timings",
            tuple(sorted(self.component_timings, key=lambda item: item.component)),
        )
        object.__setattr__(self, "filesystem_samples", tuple(self.filesystem_samples))
        if not self.filesystem_samples:
            raise TrainingDataInputError(
                "A resource observation requires at least one filesystem sample."
            )
        object.__setattr__(self, "minimum_free_disk_gib", float(self.minimum_free_disk_gib))
        object.__setattr__(self, "disk_reserve_satisfied", bool(self.disk_reserve_satisfied))
        for name in (
            "peak_process_rss_bytes",
            "accelerator_total_memory_bytes",
            "accelerator_peak_allocated_bytes",
        ):
            value = getattr(self, name)
            if value is not None:
                value = int(value)
                if value < 0:
                    raise TrainingDataInputError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, value)
        model = self.accelerator_model
        object.__setattr__(
            self, "accelerator_model", None if model is None else str(model).strip() or None
        )
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": RESOURCE_OBSERVATION_SCHEMA,
            "binding_digest": self.binding_digest,
            "attempt_identity": self.attempt_identity,
            "resource_scope_digest": self.resource_scope_digest,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "elapsed_seconds": self.elapsed_seconds,
            "component_timings": [item.to_dict() for item in self.component_timings],
            "filesystem_samples": [item.to_dict() for item in self.filesystem_samples],
            "minimum_free_disk_gib": self.minimum_free_disk_gib,
            "disk_reserve_satisfied": self.disk_reserve_satisfied,
            "peak_process_rss_bytes": self.peak_process_rss_bytes,
            "accelerator_model": self.accelerator_model,
            "accelerator_total_memory_bytes": self.accelerator_total_memory_bytes,
            "accelerator_peak_allocated_bytes": self.accelerator_peak_allocated_bytes,
            "runtime_identity_digest": self.runtime_identity_digest,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    @property
    def is_measured(self) -> bool:
        """True when this observation carries real, non-placeholder timings."""

        return bool(self.elapsed_seconds >= 0.0 and self.component_timings)

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "QualificationResourceObservation":
        if payload.get("schema") != RESOURCE_OBSERVATION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported qualification resource-observation schema."
            )
        result = cls(
            binding_digest=str(payload["binding_digest"]),
            attempt_identity=str(payload["attempt_identity"]),
            resource_scope_digest=str(payload["resource_scope_digest"]),
            started_at=str(payload["started_at"]),
            finished_at=str(payload["finished_at"]),
            elapsed_seconds=float(payload["elapsed_seconds"]),
            component_timings=tuple(
                ComponentTiming.from_dict(item) for item in payload["component_timings"]
            ),
            filesystem_samples=tuple(
                FilesystemSample.from_dict(item) for item in payload["filesystem_samples"]
            ),
            minimum_free_disk_gib=float(payload["minimum_free_disk_gib"]),
            disk_reserve_satisfied=bool(payload["disk_reserve_satisfied"]),
            peak_process_rss_bytes=payload.get("peak_process_rss_bytes"),
            accelerator_model=payload.get("accelerator_model"),
            accelerator_total_memory_bytes=payload.get("accelerator_total_memory_bytes"),
            accelerator_peak_allocated_bytes=payload.get("accelerator_peak_allocated_bytes"),
            runtime_identity_digest=payload.get("runtime_identity_digest"),
            notes=tuple(payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Qualification resource-observation digest mismatch."
            )
        return result


# ---------------------------------------------------------------------------
# Measurement helpers
# ---------------------------------------------------------------------------


def directory_footprint_bytes(root: str | os.PathLike[str]) -> int:
    """Bounded on-disk footprint of one owner-local attempt tree."""

    total = 0
    base = Path(root)
    if not base.is_dir():
        return 0
    for path in base.rglob("*"):
        try:
            if path.is_file() and not path.is_symlink():
                total += int(path.stat().st_size)
        except OSError:
            continue
    return total


def filesystem_sample(
    label: str, workspace: str | os.PathLike[str], attempt_root: str | os.PathLike[str]
) -> FilesystemSample:
    usage = shutil.disk_usage(str(workspace))
    return FilesystemSample(
        label=label,
        observed_at=_utc_now(),
        total_bytes=int(usage.total),
        free_bytes=int(usage.free),
        attempt_footprint_bytes=directory_footprint_bytes(attempt_root),
    )


def require_free_disk_reserve(
    workspace: str | os.PathLike[str], *, minimum_free_gib: float, operation: str
) -> float:
    """Fail before materializing work that would breach the configured reserve.

    This reads the campaign's existing ``[execution].minimum_free_disk_gib``
    policy. It is an owner-local safety check on the workspace this attempt is
    about to write to, not a cross-owner admission authority.
    """

    usage = shutil.disk_usage(str(workspace))
    free_gib = usage.free / _BYTES_PER_GIB
    if free_gib < float(minimum_free_gib):
        raise QualificationDiskReserveError(
            f"{operation} needs the configured free-disk reserve of "
            f"{float(minimum_free_gib):.1f} GiB, but the workspace has "
            f"{free_gib:.1f} GiB free. Qualification stops before materializing "
            "work it cannot safely complete; no scientific input is changed."
        )
    return free_gib


def peak_process_rss_bytes() -> int | None:
    """Peak resident set size of this process, from the existing OS counter."""

    try:
        import resource as _resource

        peak = int(_resource.getrusage(_resource.RUSAGE_SELF).ru_maxrss)
    except Exception:
        return None
    # Linux reports kibibytes; macOS reports bytes.  Both are accepted inputs
    # and normalized here rather than in the record.
    import sys

    return peak if sys.platform == "darwin" else peak * 1024


def accelerator_observation(device: str) -> tuple[str | None, int | None, int | None]:
    """(model, total VRAM bytes, peak allocated bytes) from existing telemetry."""

    if not str(device).startswith("cuda"):
        return None, None, None
    try:
        import torch

        if not torch.cuda.is_available():
            return None, None, None
        properties = torch.cuda.get_device_properties(0)
        return (
            str(getattr(properties, "name", "")) or None,
            int(getattr(properties, "total_memory", 0)) or None,
            int(torch.cuda.max_memory_allocated()) or None,
        )
    except Exception:
        return None, None, None


@dataclass
class ResourceObservationRecorder:
    """Accumulates the measurements one attempt actually produced."""

    binding_digest: str
    attempt_identity: str
    resource_scope_digest: str
    workspace: Path
    attempt_root: Path
    minimum_free_disk_gib: float
    device: str = "cpu"
    runtime_identity_digest: str | None = None
    started_at: str = field(default_factory=_utc_now)
    _monotonic_start: float = field(default_factory=lambda: __import__("time").monotonic())
    component_timings: list[ComponentTiming] = field(default_factory=list)
    samples: list[FilesystemSample] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def sample_filesystem(self, label: str) -> FilesystemSample:
        sample = filesystem_sample(label, self.workspace, self.attempt_root)
        self.samples.append(sample)
        return sample

    def record_component(
        self, component: str, *, started: str, elapsed: float, reused: bool
    ) -> None:
        self.component_timings.append(
            ComponentTiming(
                component=component,
                started_at=started,
                finished_at=_utc_now(),
                elapsed_seconds=float(elapsed),
                reused=bool(reused),
            )
        )

    def require_disk_reserve(self, operation: str) -> float:
        return require_free_disk_reserve(
            self.workspace,
            minimum_free_gib=self.minimum_free_disk_gib,
            operation=operation,
        )

    def finish(self) -> QualificationResourceObservation:
        import time

        if not self.samples:
            self.sample_filesystem("start")
        end_sample = self.sample_filesystem("end")
        model, total_vram, peak_vram = accelerator_observation(self.device)
        satisfied = all(
            sample.free_gib >= float(self.minimum_free_disk_gib) for sample in self.samples
        )
        return QualificationResourceObservation(
            binding_digest=self.binding_digest,
            attempt_identity=self.attempt_identity,
            resource_scope_digest=self.resource_scope_digest,
            started_at=self.started_at,
            finished_at=end_sample.observed_at,
            elapsed_seconds=max(0.0, time.monotonic() - self._monotonic_start),
            component_timings=tuple(self.component_timings),
            filesystem_samples=tuple(self.samples),
            minimum_free_disk_gib=float(self.minimum_free_disk_gib),
            disk_reserve_satisfied=satisfied,
            peak_process_rss_bytes=peak_process_rss_bytes(),
            accelerator_model=model,
            accelerator_total_memory_bytes=total_vram,
            accelerator_peak_allocated_bytes=peak_vram,
            runtime_identity_digest=self.runtime_identity_digest,
            notes=tuple(self.notes),
        )


__all__ = [
    "COMPONENT_TIMING_SCHEMA",
    "FILESYSTEM_SAMPLE_SCHEMA",
    "RESOURCE_OBSERVATION_SCHEMA",
    "ComponentTiming",
    "FilesystemSample",
    "QualificationDiskReserveError",
    "QualificationResourceObservation",
    "ResourceObservationRecorder",
    "accelerator_observation",
    "directory_footprint_bytes",
    "filesystem_sample",
    "peak_process_rss_bytes",
    "require_free_disk_reserve",
]
