"""PERFBASE1 reproducible campaign performance-baseline authority.

PERFBASE1 is deliberately measurement-only.  It binds representative supplied
and synthetic workloads to exact scientific-output digests, while recording
host/run telemetry separately so later exact-equivalent optimizations can be
compared without making timing or worker count part of scientific authority.

The record is foundation-model generic.  A concrete run binds the active model
family/variant and checkpoint SHA-256 (for example MPA-0 during current LTA
qualification, or MH-1 in a later campaign) but no workload semantics depend on
one hard-coded MACE foundation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

import numpy as np

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    canonical_json,
    digest,
    json_value,
    validate_digest,
)
from .performance_baseline import (
    PerfBase0ArtifactIdentity,
    PerfBase0StageMeter,
    perf_base0_runtime_environment,
)

PERFBASE1_VERSION = "mdstats.mlff-perfbase1.2026-08.v1"
PERFBASE1_TRIAL_SCHEMA = "mdstats.mlff-perfbase1-trial.v1"
PERFBASE1_WORKLOAD_SCHEMA = "mdstats.mlff-perfbase1-workload.v1"
PERFBASE1_RECORD_SCHEMA = "mdstats.mlff-perfbase1-record.v1"


def _nonempty(value: str, *, name: str) -> str:
    result = str(value).strip()
    if not result:
        raise TrainingDataInputError(f"{name} must be non-empty.")
    return result


def _nonnegative_int(value: int, *, name: str) -> int:
    result = int(value)
    if result < 0:
        raise TrainingDataInputError(f"{name} must be nonnegative.")
    return result


def _positive_int(value: int, *, name: str) -> int:
    result = int(value)
    if result <= 0:
        raise TrainingDataInputError(f"{name} must be positive.")
    return result


def _finite_nonnegative(value: float, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise TrainingDataInputError(f"{name} must be finite and nonnegative.")
    return result


def _utc(value: str, *, name: str) -> str:
    text = _nonempty(value, name=name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TrainingDataInputError(f"{name} must be ISO-8601.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TrainingDataInputError(f"{name} must include a timezone.")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_mapping(value: Mapping[str, Any] | None, *, name: str) -> str:
    payload = {} if value is None else json_value(value)
    try:
        return canonical_json(payload)
    except Exception as exc:  # pragma: no cover - defensive serialization boundary
        raise TrainingDataInputError(f"{name} must be deterministic JSON metadata.") from exc


def _canonical_mapping_from_payload(value: Any, *, name: str) -> str:
    if value is None:
        value = {}
    if not isinstance(value, Mapping):
        raise TrainingDataSerializationError(f"{name} must be an object.")
    return _canonical_mapping(value, name=name)


@dataclass(frozen=True, slots=True)
class PerfBase1Trial:
    """One isolated workload measurement.

    ``scientific_output_digest`` is the exact output identity and is the only
    trial field that participates in workload scientific equivalence.  All
    timing, memory, worker, counter, and queue observations are execution-only.
    """

    workload_id: str
    schedule_label: str
    repeat_index: int
    requested_workers: int
    allocated_workers: int
    measured_at_utc: str
    wall_seconds: float
    process_cpu_seconds: float
    effective_cpu_cores: float
    assigned_lane_occupancy: float
    rss_start_bytes: int
    rss_end_bytes: int
    sampled_peak_rss_bytes: int
    process_peak_rss_bytes: int
    persisted_bytes: int
    temporary_array_bytes: int
    scientific_output_digest: str
    counters_json_text: str = "{}"
    queue_json_text: str = "{}"
    worker_settings_json_text: str = "{}"
    environment_json_text: str = "{}"
    events: tuple[str, ...] = ()
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "workload_id", _nonempty(self.workload_id, name="workload_id"))
        object.__setattr__(self, "schedule_label", _nonempty(self.schedule_label, name="schedule_label"))
        object.__setattr__(self, "repeat_index", _nonnegative_int(self.repeat_index, name="repeat_index"))
        requested = _positive_int(self.requested_workers, name="requested_workers")
        allocated = _positive_int(self.allocated_workers, name="allocated_workers")
        object.__setattr__(self, "requested_workers", requested)
        object.__setattr__(self, "allocated_workers", allocated)
        object.__setattr__(self, "measured_at_utc", _utc(self.measured_at_utc, name="measured_at_utc"))
        wall = _finite_nonnegative(self.wall_seconds, name="wall_seconds")
        cpu = _finite_nonnegative(self.process_cpu_seconds, name="process_cpu_seconds")
        cores = _finite_nonnegative(self.effective_cpu_cores, name="effective_cpu_cores")
        occupancy = _finite_nonnegative(self.assigned_lane_occupancy, name="assigned_lane_occupancy")
        if wall > 0.0 and not np.isclose(cores, cpu / wall, rtol=1e-10, atol=1e-12):
            raise TrainingDataInputError("PERFBASE1 effective_cpu_cores is inconsistent with CPU/wall time.")
        if not np.isclose(occupancy, cores / allocated, rtol=1e-10, atol=1e-12):
            raise TrainingDataInputError("PERFBASE1 assigned-lane occupancy is inconsistent with allocated workers.")
        object.__setattr__(self, "wall_seconds", wall)
        object.__setattr__(self, "process_cpu_seconds", cpu)
        object.__setattr__(self, "effective_cpu_cores", cores)
        object.__setattr__(self, "assigned_lane_occupancy", occupancy)
        for name in (
            "rss_start_bytes", "rss_end_bytes", "sampled_peak_rss_bytes", "process_peak_rss_bytes",
            "persisted_bytes", "temporary_array_bytes",
        ):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name=name))
        if self.sampled_peak_rss_bytes < max(self.rss_start_bytes, self.rss_end_bytes):
            raise TrainingDataInputError("PERFBASE1 sampled peak RSS cannot be below start/end RSS.")
        object.__setattr__(
            self,
            "scientific_output_digest",
            validate_digest(self.scientific_output_digest, name="scientific_output_digest"),
        )
        for field_name in (
            "counters_json_text", "queue_json_text", "worker_settings_json_text", "environment_json_text"
        ):
            text = str(getattr(self, field_name))
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                raise TrainingDataInputError(f"{field_name} is invalid JSON.") from exc
            canonical = _canonical_mapping(parsed, name=field_name)
            if canonical != text:
                raise TrainingDataInputError(f"{field_name} must be canonical JSON.")
        object.__setattr__(self, "events", tuple(str(value) for value in self.events))

    @classmethod
    def build(
        cls,
        *,
        workload_id: str,
        schedule_label: str,
        repeat_index: int,
        requested_workers: int,
        allocated_workers: int,
        measured_at_utc: str,
        wall_seconds: float,
        process_cpu_seconds: float,
        rss_start_bytes: int,
        rss_end_bytes: int,
        sampled_peak_rss_bytes: int,
        process_peak_rss_bytes: int,
        persisted_bytes: int,
        temporary_array_bytes: int,
        scientific_output_digest: str,
        counters: Mapping[str, Any] | None = None,
        queue: Mapping[str, Any] | None = None,
        worker_settings: Mapping[str, Any] | None = None,
        environment: Mapping[str, Any] | None = None,
        events: Sequence[str] = (),
    ) -> "PerfBase1Trial":
        wall = float(wall_seconds)
        cpu = float(process_cpu_seconds)
        cores = 0.0 if wall <= 0.0 else cpu / wall
        allocated = int(allocated_workers)
        return cls(
            workload_id=workload_id,
            schedule_label=schedule_label,
            repeat_index=repeat_index,
            requested_workers=requested_workers,
            allocated_workers=allocated,
            measured_at_utc=measured_at_utc,
            wall_seconds=wall,
            process_cpu_seconds=cpu,
            effective_cpu_cores=cores,
            assigned_lane_occupancy=cores / max(1, allocated),
            rss_start_bytes=rss_start_bytes,
            rss_end_bytes=rss_end_bytes,
            sampled_peak_rss_bytes=sampled_peak_rss_bytes,
            process_peak_rss_bytes=process_peak_rss_bytes,
            persisted_bytes=persisted_bytes,
            temporary_array_bytes=temporary_array_bytes,
            scientific_output_digest=scientific_output_digest,
            counters_json_text=_canonical_mapping(counters, name="counters"),
            queue_json_text=_canonical_mapping(queue, name="queue"),
            worker_settings_json_text=_canonical_mapping(worker_settings, name="worker_settings"),
            environment_json_text=_canonical_mapping(environment, name="environment"),
            events=tuple(events),
        )

    @property
    def counters(self) -> dict[str, Any]:
        return json.loads(self.counters_json_text)

    @property
    def queue(self) -> dict[str, Any]:
        return json.loads(self.queue_json_text)

    @property
    def worker_settings(self) -> dict[str, Any]:
        return json.loads(self.worker_settings_json_text)

    @property
    def environment(self) -> dict[str, Any]:
        return json.loads(self.environment_json_text)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PERFBASE1_TRIAL_SCHEMA,
            "workload_id": self.workload_id,
            "schedule_label": self.schedule_label,
            "repeat_index": self.repeat_index,
            "requested_workers": self.requested_workers,
            "allocated_workers": self.allocated_workers,
            "measured_at_utc": self.measured_at_utc,
            "wall_seconds": self.wall_seconds,
            "process_cpu_seconds": self.process_cpu_seconds,
            "effective_cpu_cores": self.effective_cpu_cores,
            "assigned_lane_occupancy": self.assigned_lane_occupancy,
            "rss_start_bytes": self.rss_start_bytes,
            "rss_end_bytes": self.rss_end_bytes,
            "sampled_peak_rss_bytes": self.sampled_peak_rss_bytes,
            "process_peak_rss_bytes": self.process_peak_rss_bytes,
            "persisted_bytes": self.persisted_bytes,
            "temporary_array_bytes": self.temporary_array_bytes,
            "scientific_output_digest": self.scientific_output_digest,
            "counters": self.counters,
            "queue": self.queue,
            "worker_settings": self.worker_settings,
            "environment": self.environment,
            "events": list(self.events),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfBase1Trial":
        if payload.get("schema") != PERFBASE1_TRIAL_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERFBASE1 trial schema.")
        result = cls.build(
            workload_id=str(payload["workload_id"]),
            schedule_label=str(payload["schedule_label"]),
            repeat_index=int(payload["repeat_index"]),
            requested_workers=int(payload["requested_workers"]),
            allocated_workers=int(payload["allocated_workers"]),
            measured_at_utc=str(payload["measured_at_utc"]),
            wall_seconds=float(payload["wall_seconds"]),
            process_cpu_seconds=float(payload["process_cpu_seconds"]),
            rss_start_bytes=int(payload["rss_start_bytes"]),
            rss_end_bytes=int(payload["rss_end_bytes"]),
            sampled_peak_rss_bytes=int(payload["sampled_peak_rss_bytes"]),
            process_peak_rss_bytes=int(payload["process_peak_rss_bytes"]),
            persisted_bytes=int(payload.get("persisted_bytes", 0)),
            temporary_array_bytes=int(payload.get("temporary_array_bytes", 0)),
            scientific_output_digest=str(payload["scientific_output_digest"]),
            counters=payload.get("counters", {}),
            queue=payload.get("queue", {}),
            worker_settings=payload.get("worker_settings", {}),
            environment=payload.get("environment", {}),
            events=tuple(str(value) for value in payload.get("events", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERFBASE1 trial digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PerfBase1Workload:
    workload_id: str
    workload_kind: str
    corpus_digests: tuple[str, ...]
    policy_digests: tuple[str, ...]
    scientific_output_digest: str
    throughput_unit: str
    trials: tuple[PerfBase1Trial, ...]
    notes: tuple[str, ...] = ()
    _scientific_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "workload_id", _nonempty(self.workload_id, name="workload_id"))
        kind = _nonempty(self.workload_kind, name="workload_kind")
        if kind not in {"supplied", "synthetic", "hybrid"}:
            raise TrainingDataInputError("PERFBASE1 workload_kind must be supplied, synthetic, or hybrid.")
        object.__setattr__(self, "workload_kind", kind)
        corpus = tuple(validate_digest(v, name="corpus_digest") for v in self.corpus_digests)
        policy = tuple(validate_digest(v, name="policy_digest") for v in self.policy_digests)
        if len(corpus) != len(set(corpus)) or len(policy) != len(set(policy)):
            raise TrainingDataInputError("PERFBASE1 corpus/policy digests must be unique per workload.")
        object.__setattr__(self, "corpus_digests", corpus)
        object.__setattr__(self, "policy_digests", policy)
        sci = validate_digest(self.scientific_output_digest, name="scientific_output_digest")
        object.__setattr__(self, "scientific_output_digest", sci)
        object.__setattr__(self, "throughput_unit", _nonempty(self.throughput_unit, name="throughput_unit"))
        trials = tuple(self.trials)
        if not trials:
            raise TrainingDataInputError("PERFBASE1 workload requires at least one trial.")
        keys = [(t.schedule_label, t.repeat_index) for t in trials]
        if len(keys) != len(set(keys)):
            raise TrainingDataInputError("PERFBASE1 trial schedule/repeat identities must be unique.")
        if any(t.workload_id != self.workload_id for t in trials):
            raise TrainingDataInputError("PERFBASE1 trial workload IDs are misaligned.")
        if any(t.scientific_output_digest != sci for t in trials):
            raise TrainingDataInputError(
                f"PERFBASE1 scientific output drift detected for workload {self.workload_id!r}."
            )
        object.__setattr__(self, "trials", trials)
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    def _scientific_payload(self) -> dict[str, Any]:
        return {
            "schema": "mdstats.mlff-perfbase1-workload-scientific.v1",
            "workload_id": self.workload_id,
            "workload_kind": self.workload_kind,
            "corpus_digests": list(self.corpus_digests),
            "policy_digests": list(self.policy_digests),
            "scientific_output_digest": self.scientific_output_digest,
            "throughput_unit": self.throughput_unit,
        }

    @property
    def scientific_digest(self) -> str:
        cached = self._scientific_digest_cache
        if cached is None:
            cached = digest(self._scientific_payload())
            object.__setattr__(self, "_scientific_digest_cache", cached)
        return cached

    def _payload(self) -> dict[str, Any]:
        scientific = self._scientific_payload().copy()
        scientific.pop("schema", None)
        return {
            "schema": PERFBASE1_WORKLOAD_SCHEMA,
            **scientific,
            "scientific_digest": self.scientific_digest,
            "trials": [t.to_dict() for t in self.trials],
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfBase1Workload":
        if payload.get("schema") != PERFBASE1_WORKLOAD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERFBASE1 workload schema.")
        result = cls(
            workload_id=str(payload["workload_id"]),
            workload_kind=str(payload["workload_kind"]),
            corpus_digests=tuple(str(v) for v in payload.get("corpus_digests", ())),
            policy_digests=tuple(str(v) for v in payload.get("policy_digests", ())),
            scientific_output_digest=str(payload["scientific_output_digest"]),
            throughput_unit=str(payload["throughput_unit"]),
            trials=tuple(PerfBase1Trial.from_dict(v) for v in payload.get("trials", ())),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("scientific_digest") not in (None, result.scientific_digest):
            raise TrainingDataSerializationError("PERFBASE1 workload scientific digest mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERFBASE1 workload content digest mismatch.")
        return result

    def schedule_summary(self) -> dict[str, dict[str, float | int]]:
        result: dict[str, dict[str, float | int]] = {}
        for label in dict.fromkeys(t.schedule_label for t in self.trials):
            rows = [t for t in self.trials if t.schedule_label == label]
            walls = np.asarray([t.wall_seconds for t in rows], dtype=np.float64)
            occ = np.asarray([t.assigned_lane_occupancy for t in rows], dtype=np.float64)
            center = float(median(walls.tolist()))
            result[label] = {
                "allocated_workers": int(rows[0].allocated_workers),
                "repeat_count": len(rows),
                "median_wall_seconds": center,
                "wall_cv": 0.0 if len(rows) < 2 or center <= 0 else float(np.std(walls, ddof=1) / np.mean(walls)),
                "median_assigned_lane_occupancy": float(median(occ.tolist())),
                "peak_rss_bytes": int(max(t.sampled_peak_rss_bytes for t in rows)),
            }
        return result


@dataclass(frozen=True, slots=True)
class PerfBase1Record:
    baseline_id: str
    source_version: str
    created_at_utc: str
    foundation_family: str
    foundation_variant: str
    foundation_model_sha256: str
    source_artifacts: tuple[PerfBase0ArtifactIdentity, ...]
    workloads: tuple[PerfBase1Workload, ...]
    unavailable_workloads: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    _scientific_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)
    _execution_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "baseline_id", _nonempty(self.baseline_id, name="baseline_id"))
        object.__setattr__(self, "source_version", _nonempty(self.source_version, name="source_version"))
        object.__setattr__(self, "created_at_utc", _utc(self.created_at_utc, name="created_at_utc"))
        object.__setattr__(self, "foundation_family", _nonempty(self.foundation_family, name="foundation_family"))
        object.__setattr__(self, "foundation_variant", _nonempty(self.foundation_variant, name="foundation_variant"))
        object.__setattr__(
            self, "foundation_model_sha256", validate_digest(self.foundation_model_sha256, name="foundation_model_sha256")
        )
        artifacts = tuple(self.source_artifacts)
        paths = [a.logical_path for a in artifacts]
        if len(paths) != len(set(paths)):
            raise TrainingDataInputError("PERFBASE1 source artifact paths must be unique.")
        workloads = tuple(self.workloads)
        ids = [w.workload_id for w in workloads]
        if not workloads or len(ids) != len(set(ids)):
            raise TrainingDataInputError("PERFBASE1 workloads must be non-empty and uniquely named.")
        object.__setattr__(self, "source_artifacts", artifacts)
        object.__setattr__(self, "workloads", workloads)
        object.__setattr__(self, "unavailable_workloads", tuple(str(v) for v in self.unavailable_workloads))
        object.__setattr__(self, "limitations", tuple(str(v) for v in self.limitations))

    def _scientific_payload(self) -> dict[str, Any]:
        return {
            "schema": "mdstats.mlff-perfbase1-scientific-authority.v1",
            "authority_version": PERFBASE1_VERSION,
            "foundation_family": self.foundation_family,
            "foundation_variant": self.foundation_variant,
            "foundation_model_sha256": self.foundation_model_sha256,
            "source_artifacts": [a.to_dict() for a in self.source_artifacts],
            "workloads": [w._scientific_payload() for w in self.workloads],
        }

    @property
    def scientific_digest(self) -> str:
        cached = self._scientific_digest_cache
        if cached is None:
            cached = digest(self._scientific_payload())
            object.__setattr__(self, "_scientific_digest_cache", cached)
        return cached

    def _execution_payload(self) -> dict[str, Any]:
        return {
            "schema": "mdstats.mlff-perfbase1-execution-authority.v1",
            "baseline_id": self.baseline_id,
            "source_version": self.source_version,
            "created_at_utc": self.created_at_utc,
            "workloads": [w.to_dict() for w in self.workloads],
            "unavailable_workloads": list(self.unavailable_workloads),
            "limitations": list(self.limitations),
        }

    @property
    def execution_digest(self) -> str:
        cached = self._execution_digest_cache
        if cached is None:
            cached = digest(self._execution_payload())
            object.__setattr__(self, "_execution_digest_cache", cached)
        return cached

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PERFBASE1_RECORD_SCHEMA,
            "authority_version": PERFBASE1_VERSION,
            "baseline_id": self.baseline_id,
            "source_version": self.source_version,
            "created_at_utc": self.created_at_utc,
            "foundation_family": self.foundation_family,
            "foundation_variant": self.foundation_variant,
            "foundation_model_sha256": self.foundation_model_sha256,
            "source_artifacts": [a.to_dict() for a in self.source_artifacts],
            "workloads": [w.to_dict() for w in self.workloads],
            "unavailable_workloads": list(self.unavailable_workloads),
            "limitations": list(self.limitations),
            "scientific_digest": self.scientific_digest,
            "execution_digest": self.execution_digest,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfBase1Record":
        if payload.get("schema") != PERFBASE1_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERFBASE1 record schema.")
        result = cls(
            baseline_id=str(payload["baseline_id"]),
            source_version=str(payload["source_version"]),
            created_at_utc=str(payload["created_at_utc"]),
            foundation_family=str(payload["foundation_family"]),
            foundation_variant=str(payload["foundation_variant"]),
            foundation_model_sha256=str(payload["foundation_model_sha256"]),
            source_artifacts=tuple(PerfBase0ArtifactIdentity.from_dict(v) for v in payload.get("source_artifacts", ())),
            workloads=tuple(PerfBase1Workload.from_dict(v) for v in payload.get("workloads", ())),
            unavailable_workloads=tuple(str(v) for v in payload.get("unavailable_workloads", ())),
            limitations=tuple(str(v) for v in payload.get("limitations", ())),
        )
        if payload.get("authority_version") not in (None, PERFBASE1_VERSION):
            raise TrainingDataSerializationError("Unsupported PERFBASE1 authority version.")
        if payload.get("scientific_digest") not in (None, result.scientific_digest):
            raise TrainingDataSerializationError("PERFBASE1 scientific digest mismatch.")
        if payload.get("execution_digest") not in (None, result.execution_digest):
            raise TrainingDataSerializationError("PERFBASE1 execution digest mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERFBASE1 content digest mismatch.")
        return result


def write_perfbase1_record(path: str | Path, record: PerfBase1Record) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def read_perfbase1_record(path: str | Path) -> PerfBase1Record:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TrainingDataSerializationError(f"Could not read PERFBASE1 record: {exc}") from exc
    return PerfBase1Record.from_dict(payload)


class PerfBase1TrialMeter:
    """Thin PERFBASE1 adapter over the frozen PERF-BASE0 process meter."""

    def __init__(
        self,
        workload_id: str,
        *,
        schedule_label: str,
        repeat_index: int,
        requested_workers: int,
        allocated_workers: int,
        worker_settings: Mapping[str, Any] | None = None,
        environment: Mapping[str, Any] | None = None,
        sample_interval_seconds: float = 0.01,
    ) -> None:
        self.workload_id = workload_id
        self.schedule_label = schedule_label
        self.repeat_index = repeat_index
        self.requested_workers = requested_workers
        self.allocated_workers = allocated_workers
        self.worker_settings = {} if worker_settings is None else dict(worker_settings)
        self._meter = PerfBase0StageMeter(
            workload_id,
            worker_settings=self.worker_settings,
            sample_interval_seconds=sample_interval_seconds,
            environment=perf_base0_runtime_environment() if environment is None else environment,
        )

    def __enter__(self) -> "PerfBase1TrialMeter":
        self._meter.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self._meter.__exit__(exc_type, exc, tb)

    def trial(
        self,
        *,
        scientific_output_digest: str,
        throughput_count: int,
        throughput_unit: str,
        persisted_bytes: int = 0,
        temporary_array_bytes: int = 0,
        counters: Mapping[str, Any] | None = None,
        queue: Mapping[str, Any] | None = None,
        events: Sequence[str] = (),
    ) -> PerfBase1Trial:
        base = self._meter.telemetry(
            throughput_count=throughput_count,
            throughput_unit=throughput_unit,
            temporary_array_bytes=temporary_array_bytes,
            events=events,
        )
        merged_counters = dict(counters or {})
        merged_counters.setdefault("throughput_count", int(throughput_count))
        merged_counters.setdefault("throughput_unit", str(throughput_unit))
        merged_counters.setdefault("throughput_per_second", float(base.throughput_per_second))
        return PerfBase1Trial.build(
            workload_id=self.workload_id,
            schedule_label=self.schedule_label,
            repeat_index=self.repeat_index,
            requested_workers=self.requested_workers,
            allocated_workers=self.allocated_workers,
            measured_at_utc=base.measured_at_utc,
            wall_seconds=base.wall_seconds,
            process_cpu_seconds=base.process_cpu_seconds,
            rss_start_bytes=base.rss_start_bytes,
            rss_end_bytes=base.rss_end_bytes,
            sampled_peak_rss_bytes=base.sampled_peak_rss_bytes,
            process_peak_rss_bytes=base.process_peak_rss_bytes,
            persisted_bytes=persisted_bytes,
            temporary_array_bytes=temporary_array_bytes,
            scientific_output_digest=scientific_output_digest,
            counters=merged_counters,
            queue=queue,
            worker_settings=self.worker_settings,
            environment=base.environment,
            events=events,
        )


def render_perfbase1_markdown(record: PerfBase1Record) -> str:
    lines = [
        "# MLFF PERFBASE1 reproducible performance baseline",
        "",
        f"- Baseline ID: `{record.baseline_id}`",
        f"- mdstats source: `{record.source_version}`",
        f"- Foundation: `{record.foundation_family}` / `{record.foundation_variant}`",
        f"- Foundation SHA-256: `{record.foundation_model_sha256}`",
        f"- Scientific digest: `{record.scientific_digest}`",
        f"- Execution digest: `{record.execution_digest}`",
        f"- Content digest: `{record.content_digest}`",
        "",
        "## Workload summaries",
        "",
        "| Workload | Schedule | Workers | Repeats | Median wall (s) | Wall CV | Median occupancy | Peak RSS (MiB) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for workload in record.workloads:
        for label, summary in workload.schedule_summary().items():
            lines.append(
                f"| `{workload.workload_id}` | `{label}` | {summary['allocated_workers']} | "
                f"{summary['repeat_count']} | {summary['median_wall_seconds']:.6f} | "
                f"{summary['wall_cv']:.4f} | {summary['median_assigned_lane_occupancy']:.4f} | "
                f"{summary['peak_rss_bytes'] / (1024 ** 2):.2f} |"
            )
    if record.unavailable_workloads:
        lines.extend(["", "## Unavailable on this host", ""])
        lines.extend(f"- {item}" for item in record.unavailable_workloads)
    if record.limitations:
        lines.extend(["", "## Limitations", ""])
        lines.extend(f"- {item}" for item in record.limitations)
    lines.append("")
    return "\n".join(lines)
