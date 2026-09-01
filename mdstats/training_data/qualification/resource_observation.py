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
import json
import math
import os
import shutil

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    json_value,
    validate_digest,
)
from .errors import QualificationError, QualificationLineageError

RESOURCE_OBSERVATION_SCHEMA = "mdstats.qualification-resource-observation.v1"
COMPONENT_TIMING_SCHEMA = "mdstats.qualification-component-timing.v1"
FILESYSTEM_SAMPLE_SCHEMA = "mdstats.qualification-filesystem-sample.v1"
RESOURCE_OBSERVATION_POINTER_SCHEMA = "mdstats.qualification-resource-observation-pointer.v1"
RESOURCE_OBSERVATION_POINTER_FILENAME = "resource-observation.json"

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
        if not math.isfinite(elapsed) or elapsed < 0.0:
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
    previous_observation_digest: str | None = None
    resource_scope_material: Mapping[str, Any] = field(default_factory=dict)
    incremental_headroom_bytes: int = 0

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
        if not math.isfinite(elapsed) or elapsed < 0.0:
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
        minimum_free = float(self.minimum_free_disk_gib)
        if not math.isfinite(minimum_free) or minimum_free < 0.0:
            raise TrainingDataInputError(
                "minimum_free_disk_gib must be finite and nonnegative."
            )
        object.__setattr__(self, "minimum_free_disk_gib", minimum_free)
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
        if self.previous_observation_digest is not None:
            object.__setattr__(
                self,
                "previous_observation_digest",
                validate_digest(
                    self.previous_observation_digest,
                    name="previous_observation_digest",
                ),
            )
        if not isinstance(self.resource_scope_material, Mapping):
            raise TrainingDataInputError("resource_scope_material must be a mapping.")
        object.__setattr__(
            self,
            "resource_scope_material",
            json_value(dict(self.resource_scope_material)),
        )
        if self.resource_scope_material and digest(self.resource_scope_material) != self.resource_scope_digest:
            raise TrainingDataInputError(
                "resource_scope_material does not reproduce resource_scope_digest."
            )
        headroom = int(self.incremental_headroom_bytes)
        if headroom < 0:
            raise TrainingDataInputError("incremental_headroom_bytes must be nonnegative.")
        object.__setattr__(self, "incremental_headroom_bytes", headroom)

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
            "previous_observation_digest": self.previous_observation_digest,
            "resource_scope_material": dict(self.resource_scope_material),
            "incremental_headroom_bytes": self.incremental_headroom_bytes,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    @property
    def is_measured(self) -> bool:
        """True when this observation carries real, non-placeholder timings."""

        return bool(self.elapsed_seconds > 0.0 and self.component_timings)

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
            previous_observation_digest=payload.get("previous_observation_digest"),
            resource_scope_material=dict(payload.get("resource_scope_material", {})),
            incremental_headroom_bytes=int(payload.get("incremental_headroom_bytes", 0)),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Qualification resource-observation digest mismatch."
            )
        return result


# ---------------------------------------------------------------------------
# Measurement helpers
# ---------------------------------------------------------------------------


def resource_observation_pointer_path(
    attempt_root: str | os.PathLike[str],
) -> Path:
    return Path(attempt_root) / RESOURCE_OBSERVATION_POINTER_FILENAME


def read_resource_observation_pointer(
    attempt_root: str | os.PathLike[str],
) -> str | None:
    """Read the owner-local locator for the latest immutable observation."""

    path = resource_observation_pointer_path(attempt_root)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != RESOURCE_OBSERVATION_POINTER_SCHEMA:
            raise QualificationLineageError(
                "Unsupported qualification resource-observation pointer schema."
            )
        return validate_digest(
            payload.get("observation_digest", ""), name="observation_digest"
        )
    except QualificationLineageError:
        raise
    except (OSError, ValueError, KeyError, TrainingDataInputError) as exc:
        raise QualificationLineageError(
            f"Qualification resource-observation pointer {path!s} is corrupt."
        ) from exc


def publish_resource_observation_pointer(
    attempt_root: str | os.PathLike[str],
    *,
    observation: QualificationResourceObservation,
) -> Path:
    """Atomically advance the latest-observation locator for one attempt."""

    from ..target_size_execution import publish_mutable_json_atomic

    path = resource_observation_pointer_path(attempt_root)
    payload = {
        "schema": RESOURCE_OBSERVATION_POINTER_SCHEMA,
        "binding_digest": observation.binding_digest,
        "attempt_identity": observation.attempt_identity,
        "resource_scope_digest": observation.resource_scope_digest,
        "observation_digest": observation.content_digest,
    }
    publish_mutable_json_atomic(path, payload)
    return path


def directory_footprint_bytes(root: str | os.PathLike[str]) -> int:
    """Bounded on-disk footprint of one owner-local attempt tree."""

    total = 0
    base = Path(root)
    if not base.is_dir():
        return 0
    # ``Path.rglob`` can raise from a directory that disappears between its
    # existence check and recursive ``scandir``. Qualification deliberately
    # permits concurrent owner-local artifact workers, so walk with an
    # ``onerror`` handler and treat a transiently disappearing entry as an
    # observational omission rather than failing the scientific operation.
    for directory, _subdirectories, filenames in os.walk(
        base, topdown=True, onerror=lambda _error: None
    ):
        for filename in filenames:
            path = Path(directory) / filename
            try:
                if not path.is_symlink():
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
    workspace: str | os.PathLike[str],
    *,
    minimum_free_gib: float,
    operation: str,
    required_incremental_headroom_bytes: int = 0,
    headroom_bytes: int | None = None,
) -> float:
    """Fail before materializing work that would breach the configured reserve.

    This reads the campaign's existing ``[execution].minimum_free_disk_gib``
    policy. It is an owner-local safety check on the workspace this attempt is
    about to write to, not a cross-owner admission authority.
    """

    if headroom_bytes is not None:
        if required_incremental_headroom_bytes:
            raise QualificationError(
                "Specify only one incremental disk-headroom argument."
            )
        required_incremental_headroom_bytes = int(headroom_bytes)
    headroom = int(required_incremental_headroom_bytes)
    if headroom < 0:
        raise QualificationError("Incremental disk headroom must be nonnegative.")
    reserve = float(minimum_free_gib)
    if not math.isfinite(reserve) or reserve < 0.0:
        raise QualificationError("minimum_free_gib must be finite and nonnegative.")
    usage = shutil.disk_usage(str(workspace))
    free_gib = usage.free / _BYTES_PER_GIB
    required_bytes = int(math.ceil(reserve * _BYTES_PER_GIB)) + headroom
    if int(usage.free) < required_bytes:
        raise QualificationDiskReserveError(
            f"{operation} needs the configured free-disk reserve of "
            f"{reserve:.1f} GiB plus {headroom} bytes of incremental headroom, but the workspace has "
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
        device_text = str(device).strip().lower()
        selected = 0 if device_text == "cuda" else int(device_text.split(":", 1)[1])
        if selected < 0 or selected >= int(torch.cuda.device_count()):
            return None, None, None
        properties = torch.cuda.get_device_properties(selected)
        with torch.cuda.device(selected):
            allocated = int(torch.cuda.max_memory_allocated(selected))
        return (
            str(getattr(properties, "name", "")) or None,
            int(getattr(properties, "total_memory", 0)) or None,
            allocated or None,
        )
    except Exception:
        return None, None, None


@dataclass
class ResourceObservationRecorder:
    """Accumulates an immutable, resumable measurement lineage for one attempt."""

    binding_digest: str
    attempt_identity: str
    resource_scope_digest: str
    workspace: Path
    attempt_root: Path
    minimum_free_disk_gib: float
    device: str = "cpu"
    runtime_identity_digest: str | None = None
    resource_scope_material: Mapping[str, Any] = field(default_factory=dict)
    previous_observation: QualificationResourceObservation | None = None
    previous_observation_digest: str | None = None
    started_at: str = field(default_factory=_utc_now)
    _monotonic_start: float = field(default_factory=lambda: __import__("time").monotonic())
    component_timings: list[ComponentTiming] = field(default_factory=list)
    samples: list[FilesystemSample] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    _base_elapsed_seconds: float = field(default=0.0, init=False, repr=False)
    _base_component_timings: tuple[ComponentTiming, ...] = field(default=(), init=False, repr=False)
    _base_samples: tuple[FilesystemSample, ...] = field(default=(), init=False, repr=False)
    _base_peak_rss: int | None = field(default=None, init=False, repr=False)
    _base_accelerator: tuple[str | None, int | None, int | None] = field(
        default=(None, None, None), init=False, repr=False
    )
    _base_notes: tuple[str, ...] = field(default=(), init=False, repr=False)
    _base_headroom: int = field(default=0, init=False, repr=False)
    _required_headroom: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        self.binding_digest = validate_digest(self.binding_digest, name="binding_digest")
        self.attempt_identity = validate_digest(self.attempt_identity, name="attempt_identity")
        self.resource_scope_digest = validate_digest(
            self.resource_scope_digest, name="resource_scope_digest"
        )
        if self.previous_observation is not None:
            previous = self.previous_observation
            if (
                previous.binding_digest != self.binding_digest
                or previous.attempt_identity != self.attempt_identity
                or previous.resource_scope_digest != self.resource_scope_digest
            ):
                raise QualificationLineageError(
                    "A prior resource observation belongs to a different qualification "
                    "binding, attempt, or resource scope."
                )
            previous_digest = previous.content_digest
            if self.previous_observation_digest not in (None, previous_digest):
                raise QualificationLineageError(
                    "The prior resource observation digest does not authenticate its object."
                )
            self.previous_observation_digest = previous_digest
            self.started_at = previous.started_at
            self._base_elapsed_seconds = previous.elapsed_seconds
            self._base_component_timings = previous.component_timings
            self._base_samples = previous.filesystem_samples
            self._base_peak_rss = previous.peak_process_rss_bytes
            self._base_accelerator = (
                previous.accelerator_model,
                previous.accelerator_total_memory_bytes,
                previous.accelerator_peak_allocated_bytes,
            )
            self._base_notes = previous.notes
            self._base_headroom = previous.incremental_headroom_bytes
            if not self.resource_scope_material:
                self.resource_scope_material = previous.resource_scope_material
            elif dict(self.resource_scope_material) != dict(previous.resource_scope_material):
                raise QualificationLineageError(
                    "A resumed resource observation changed the authenticated scope material."
                )
        elif self.previous_observation_digest is not None:
            raise QualificationLineageError(
                "A resource-observation predecessor digest has no authenticated predecessor object."
            )
        if not isinstance(self.resource_scope_material, Mapping):
            raise TrainingDataInputError("resource_scope_material must be a mapping.")
        self.resource_scope_material = json_value(dict(self.resource_scope_material))
        if self.resource_scope_material and digest(self.resource_scope_material) != self.resource_scope_digest:
            raise QualificationLineageError(
                "Resource-scope material does not reproduce the authenticated scope digest."
            )
        self._required_headroom = self._base_headroom

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

    def require_disk_reserve(
        self,
        operation: str,
        *,
        required_incremental_headroom_bytes: int = 0,
        headroom_bytes: int | None = None,
    ) -> float:
        if headroom_bytes is not None:
            if required_incremental_headroom_bytes:
                raise QualificationError(
                    "Specify only one incremental disk-headroom argument."
                )
            required_incremental_headroom_bytes = int(headroom_bytes)
        headroom = int(required_incremental_headroom_bytes)
        if headroom < 0:
            raise QualificationError("Incremental disk headroom must be nonnegative.")
        self._required_headroom = max(self._required_headroom, headroom)
        return require_free_disk_reserve(
            self.workspace,
            minimum_free_gib=self.minimum_free_disk_gib,
            operation=operation,
            required_incremental_headroom_bytes=headroom,
        )

    def finish(self) -> QualificationResourceObservation:
        import time

        if not self.samples:
            self.sample_filesystem("start")
        end_sample = self.sample_filesystem("end")
        model, total_vram, peak_vram = accelerator_observation(self.device)
        model = model or self._base_accelerator[0]
        total_vram = total_vram or self._base_accelerator[1]
        peak_vram = max(
            value for value in (peak_vram or 0, self._base_accelerator[2] or 0)
        ) or None
        all_samples = self._base_samples + tuple(self.samples)
        all_timings = self._base_component_timings + tuple(self.component_timings)
        headroom = max(self._required_headroom, self._base_headroom)
        reserve_bytes = int(math.ceil(float(self.minimum_free_disk_gib) * _BYTES_PER_GIB))
        satisfied = all(
            int(sample.free_bytes) >= reserve_bytes + headroom for sample in all_samples
        )
        return QualificationResourceObservation(
            binding_digest=self.binding_digest,
            attempt_identity=self.attempt_identity,
            resource_scope_digest=self.resource_scope_digest,
            started_at=self.started_at,
            finished_at=end_sample.observed_at,
            elapsed_seconds=self._base_elapsed_seconds
            + max(0.0, time.monotonic() - self._monotonic_start),
            component_timings=all_timings,
            filesystem_samples=all_samples,
            minimum_free_disk_gib=float(self.minimum_free_disk_gib),
            disk_reserve_satisfied=satisfied,
            peak_process_rss_bytes=max(
                value for value in (peak_process_rss_bytes() or 0, self._base_peak_rss or 0)
            ) or None,
            accelerator_model=model,
            accelerator_total_memory_bytes=total_vram,
            accelerator_peak_allocated_bytes=peak_vram,
            runtime_identity_digest=self.runtime_identity_digest,
            notes=self._base_notes + tuple(self.notes),
            previous_observation_digest=self.previous_observation_digest,
            resource_scope_material=self.resource_scope_material,
            incremental_headroom_bytes=headroom,
        )

    def mark_published(self, observation: QualificationResourceObservation) -> None:
        """Start another invocation without rewriting prior immutable evidence."""

        if (
            observation.binding_digest != self.binding_digest
            or observation.attempt_identity != self.attempt_identity
            or observation.resource_scope_digest != self.resource_scope_digest
        ):
            raise QualificationLineageError(
                "Published resource observation does not belong to this recorder."
            )
        self.previous_observation = observation
        self.previous_observation_digest = observation.content_digest
        self._base_elapsed_seconds = observation.elapsed_seconds
        self._base_component_timings = observation.component_timings
        self._base_samples = observation.filesystem_samples
        self._base_peak_rss = observation.peak_process_rss_bytes
        self._base_accelerator = (
            observation.accelerator_model,
            observation.accelerator_total_memory_bytes,
            observation.accelerator_peak_allocated_bytes,
        )
        self._base_notes = observation.notes
        self._base_headroom = observation.incremental_headroom_bytes
        self.component_timings.clear()
        self.samples.clear()
        self.notes.clear()
        self._required_headroom = self._base_headroom
        self._monotonic_start = __import__("time").monotonic()


__all__ = [
    "COMPONENT_TIMING_SCHEMA",
    "FILESYSTEM_SAMPLE_SCHEMA",
    "RESOURCE_OBSERVATION_SCHEMA",
    "RESOURCE_OBSERVATION_POINTER_FILENAME",
    "RESOURCE_OBSERVATION_POINTER_SCHEMA",
    "ComponentTiming",
    "FilesystemSample",
    "QualificationDiskReserveError",
    "QualificationResourceObservation",
    "ResourceObservationRecorder",
    "accelerator_observation",
    "directory_footprint_bytes",
    "filesystem_sample",
    "peak_process_rss_bytes",
    "publish_resource_observation_pointer",
    "read_resource_observation_pointer",
    "resource_observation_pointer_path",
    "require_free_disk_reserve",
]
