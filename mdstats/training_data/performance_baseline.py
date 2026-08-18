"""PERF-BASE0 numerical-oracle and execution-telemetry records.

The post-MH1 performance program needs two deliberately separate authorities:

* deterministic scientific references that must remain identical across
  execution-equivalent optimizations; and
* host/run telemetry that is expected to change when an implementation is
  optimized or moved to another machine.

This module keeps those authorities structurally separate.  Scientific array
references hash canonical little-endian C-order bytes.  Timing, RSS, I/O,
thread-pool, cgroup, and accelerator observations never enter a scientific
content digest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import resource
import sys
import threading
import time
from typing import Any, Mapping, Sequence

import numpy as np
from threadpoolctl import threadpool_info

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    canonical_json,
    digest,
    json_value,
    sha256_file_cached,
    validate_digest,
)

PERF_BASE0_VERSION = "mdstats.mlff-perf-base0.2026-08.v1"
PERF_BASE0_ARRAY_SCHEMA = "mdstats.perf-base0-array-reference.v1"
PERF_BASE0_JSON_SCHEMA = "mdstats.perf-base0-json-reference.v1"
PERF_BASE0_ARTIFACT_SCHEMA = "mdstats.perf-base0-artifact-identity.v1"
PERF_BASE0_CORPUS_SCHEMA = "mdstats.perf-base0-corpus-identity.v1"
PERF_BASE0_SCIENTIFIC_STAGE_SCHEMA = "mdstats.perf-base0-scientific-stage.v1"
PERF_BASE0_TELEMETRY_SCHEMA = "mdstats.perf-base0-execution-telemetry.v1"
PERF_BASE0_RECORD_SCHEMA = "mdstats.perf-base0-record.v1"
PERF_BASE0_COMPARISON_SCHEMA = "mdstats.perf-base0-comparison.v1"


_JSON_SCALAR_OR_CONTAINER = (type(None), bool, int, float, str, list, dict)


def _nonempty(value: str, *, name: str) -> str:
    result = str(value).strip()
    if not result:
        raise TrainingDataInputError(f"{name} must be non-empty.")
    return result


def _canonical_text(value: Any, *, name: str) -> str:
    try:
        return canonical_json(value)
    except (TypeError, ValueError, TrainingDataInputError) as exc:
        raise TrainingDataInputError(f"{name} must be deterministic JSON metadata.") from exc


def _canonical_text_from_serialized(value: Any, *, name: str) -> str:
    return _canonical_text(value, name=name)


def _json_from_text(text: str) -> Any:
    return json.loads(text)


def _utc_timestamp(value: str, *, name: str) -> str:
    result = _nonempty(value, name=name)
    try:
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TrainingDataInputError(f"{name} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TrainingDataInputError(f"{name} must include a UTC offset.")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _finite_nonnegative(value: float, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise TrainingDataInputError(f"{name} must be finite and nonnegative.")
    return result


def _nonnegative_int(value: int, *, name: str) -> int:
    result = int(value)
    if result < 0:
        raise TrainingDataInputError(f"{name} must be nonnegative.")
    return result


def _unique_nonempty(values: Sequence[str], *, name: str) -> tuple[str, ...]:
    result = tuple(_nonempty(str(value), name=name) for value in values)
    if len(result) != len(set(result)):
        raise TrainingDataInputError(f"{name} must be unique.")
    return result


def _canonical_numeric_array(values: np.ndarray | Sequence[Any]) -> np.ndarray:
    array = np.asarray(values)
    if array.dtype.kind not in {"b", "i", "u", "f"}:
        raise TrainingDataInputError(
            "PERF-BASE0 array references support boolean, integer, unsigned, and floating arrays only."
        )
    dtype = array.dtype
    if dtype.itemsize > 1:
        dtype = dtype.newbyteorder("<")
    canonical = np.ascontiguousarray(array, dtype=dtype)
    return canonical


def _array_bytes_sha256(array: np.ndarray) -> str:
    hasher = hashlib.sha256()
    if array.nbytes:
        hasher.update(memoryview(array).cast("B"))
    return hasher.hexdigest()


@dataclass(frozen=True, slots=True)
class PerfBase0ArrayReference:
    """Exact canonical-byte identity plus human-auditable numerical summary."""

    name: str
    dtype: str
    shape: tuple[int, ...]
    byte_count: int
    value_sha256: str
    finite_count: int
    nan_count: int
    positive_infinity_count: int
    negative_infinity_count: int
    minimum: float | int | None
    maximum: float | int | None
    mean: float | None
    notes: tuple[str, ...] = ()
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _nonempty(self.name, name="array reference name"))
        try:
            dtype = np.dtype(self.dtype)
        except TypeError as exc:
            raise TrainingDataInputError("PERF-BASE0 array dtype is invalid.") from exc
        if dtype.kind not in {"b", "i", "u", "f"}:
            raise TrainingDataInputError("PERF-BASE0 array dtype is not supported.")
        if dtype.itemsize > 1 and dtype.str[0] != "<":
            raise TrainingDataInputError("PERF-BASE0 array dtype must be canonical little-endian.")
        shape = tuple(int(value) for value in self.shape)
        if any(value < 0 for value in shape):
            raise TrainingDataInputError("PERF-BASE0 array shape cannot contain negative dimensions.")
        expected = int(np.prod(shape, dtype=np.int64)) * int(dtype.itemsize)
        byte_count = _nonnegative_int(self.byte_count, name="array byte_count")
        if byte_count != expected:
            raise TrainingDataInputError("PERF-BASE0 array byte_count does not match dtype and shape.")
        counts = (
            _nonnegative_int(self.finite_count, name="finite_count"),
            _nonnegative_int(self.nan_count, name="nan_count"),
            _nonnegative_int(self.positive_infinity_count, name="positive_infinity_count"),
            _nonnegative_int(self.negative_infinity_count, name="negative_infinity_count"),
        )
        element_count = int(np.prod(shape, dtype=np.int64))
        if sum(counts) != element_count:
            raise TrainingDataInputError("PERF-BASE0 array finite/non-finite counts are inconsistent.")
        validate_digest(self.value_sha256, name="value_sha256")
        if counts[0] == 0:
            if self.minimum is not None or self.maximum is not None or self.mean is not None:
                raise TrainingDataInputError("Empty/non-finite arrays cannot carry finite summaries.")
        else:
            if self.minimum is None or self.maximum is None or self.mean is None:
                raise TrainingDataInputError("Finite PERF-BASE0 arrays require min/max/mean summaries.")
            summary = (float(self.minimum), float(self.maximum), float(self.mean))
            if any(not np.isfinite(value) for value in summary):
                raise TrainingDataInputError("PERF-BASE0 array summaries must be finite.")
            if summary[0] > summary[1]:
                raise TrainingDataInputError("PERF-BASE0 array minimum exceeds maximum.")
        object.__setattr__(self, "dtype", dtype.str)
        object.__setattr__(self, "shape", shape)
        object.__setattr__(self, "byte_count", byte_count)
        object.__setattr__(self, "finite_count", counts[0])
        object.__setattr__(self, "nan_count", counts[1])
        object.__setattr__(self, "positive_infinity_count", counts[2])
        object.__setattr__(self, "negative_infinity_count", counts[3])
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))

    @classmethod
    def from_array(
        cls,
        name: str,
        values: np.ndarray | Sequence[Any],
        *,
        notes: Sequence[str] = (),
    ) -> "PerfBase0ArrayReference":
        array = _canonical_numeric_array(values)
        if array.dtype.kind == "f":
            finite = np.isfinite(array)
            finite_values = array[finite]
            finite_count = int(np.count_nonzero(finite))
            nan_count = int(np.count_nonzero(np.isnan(array)))
            positive_infinity_count = int(np.count_nonzero(np.isposinf(array)))
            negative_infinity_count = int(np.count_nonzero(np.isneginf(array)))
        else:
            finite_values = array.reshape(-1)
            finite_count = int(array.size)
            nan_count = 0
            positive_infinity_count = 0
            negative_infinity_count = 0
        if finite_values.size:
            minimum: float | int | None
            maximum: float | int | None
            if array.dtype.kind in {"b", "i", "u"}:
                minimum = int(np.min(finite_values))
                maximum = int(np.max(finite_values))
            else:
                minimum = float(np.min(finite_values))
                maximum = float(np.max(finite_values))
            mean = float(np.mean(finite_values, dtype=np.float64))
        else:
            minimum = maximum = mean = None
        return cls(
            name=name,
            dtype=array.dtype.str,
            shape=tuple(int(value) for value in array.shape),
            byte_count=int(array.nbytes),
            value_sha256=_array_bytes_sha256(array),
            finite_count=finite_count,
            nan_count=nan_count,
            positive_infinity_count=positive_infinity_count,
            negative_infinity_count=negative_infinity_count,
            minimum=minimum,
            maximum=maximum,
            mean=mean,
            notes=tuple(notes),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PERF_BASE0_ARRAY_SCHEMA,
            "name": self.name,
            "dtype": self.dtype,
            "shape": list(self.shape),
            "byte_count": self.byte_count,
            "value_sha256": self.value_sha256,
            "finite_count": self.finite_count,
            "nan_count": self.nan_count,
            "positive_infinity_count": self.positive_infinity_count,
            "negative_infinity_count": self.negative_infinity_count,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "mean": self.mean,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfBase0ArrayReference":
        if payload.get("schema") != PERF_BASE0_ARRAY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERF-BASE0 array-reference schema.")
        result = cls(
            name=str(payload["name"]),
            dtype=str(payload["dtype"]),
            shape=tuple(int(value) for value in payload["shape"]),
            byte_count=int(payload["byte_count"]),
            value_sha256=str(payload["value_sha256"]),
            finite_count=int(payload["finite_count"]),
            nan_count=int(payload["nan_count"]),
            positive_infinity_count=int(payload["positive_infinity_count"]),
            negative_infinity_count=int(payload["negative_infinity_count"]),
            minimum=payload.get("minimum"),
            maximum=payload.get("maximum"),
            mean=None if payload.get("mean") is None else float(payload["mean"]),
            notes=tuple(str(value) for value in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-BASE0 array-reference digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PerfBase0JsonReference:
    """Authenticated exact JSON reference for orders, decisions, and reports."""

    name: str
    canonical_json_text: str
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _nonempty(self.name, name="JSON reference name"))
        try:
            value = json.loads(str(self.canonical_json_text))
        except json.JSONDecodeError as exc:
            raise TrainingDataInputError("PERF-BASE0 JSON reference is not valid JSON.") from exc
        text = _canonical_text(value, name="JSON reference value")
        if text != self.canonical_json_text:
            raise TrainingDataInputError("PERF-BASE0 JSON reference text must be canonical.")

    @classmethod
    def from_value(cls, name: str, value: Any) -> "PerfBase0JsonReference":
        return cls(name=name, canonical_json_text=_canonical_text(value, name=name))

    @property
    def value(self) -> Any:
        return _json_from_text(self.canonical_json_text)

    @property
    def value_sha256(self) -> str:
        return hashlib.sha256(self.canonical_json_text.encode("utf-8")).hexdigest()

    @property
    def byte_count(self) -> int:
        return len(self.canonical_json_text.encode("utf-8"))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PERF_BASE0_JSON_SCHEMA,
            "name": self.name,
            "value": self.value,
            "byte_count": self.byte_count,
            "value_sha256": self.value_sha256,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfBase0JsonReference":
        if payload.get("schema") != PERF_BASE0_JSON_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERF-BASE0 JSON-reference schema.")
        result = cls.from_value(str(payload["name"]), payload.get("value"))
        if int(payload.get("byte_count", result.byte_count)) != result.byte_count:
            raise TrainingDataSerializationError("PERF-BASE0 JSON-reference byte count mismatch.")
        if payload.get("value_sha256") not in (None, result.value_sha256):
            raise TrainingDataSerializationError("PERF-BASE0 JSON-reference value digest mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-BASE0 JSON-reference content digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PerfBase0ArtifactIdentity:
    logical_path: str
    role: str
    byte_count: int
    sha256: str
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        logical_path = _nonempty(self.logical_path, name="artifact logical_path")
        if Path(logical_path).is_absolute() or ".." in Path(logical_path).parts:
            raise TrainingDataInputError("PERF-BASE0 artifact logical_path must be relative and traversal-free.")
        object.__setattr__(self, "logical_path", logical_path.replace("\\", "/"))
        object.__setattr__(self, "role", _nonempty(self.role, name="artifact role"))
        object.__setattr__(self, "byte_count", _nonnegative_int(self.byte_count, name="artifact byte_count"))
        validate_digest(self.sha256, name="artifact sha256")

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        logical_path: str,
        role: str,
    ) -> "PerfBase0ArtifactIdentity":
        source = Path(path)
        if not source.is_file():
            raise TrainingDataInputError(f"PERF-BASE0 artifact does not exist: {source!s}.")
        return cls(
            logical_path=logical_path,
            role=role,
            byte_count=int(source.stat().st_size),
            sha256=sha256_file_cached(source),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PERF_BASE0_ARTIFACT_SCHEMA,
            "logical_path": self.logical_path,
            "role": self.role,
            "byte_count": self.byte_count,
            "sha256": self.sha256,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfBase0ArtifactIdentity":
        if payload.get("schema") != PERF_BASE0_ARTIFACT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERF-BASE0 artifact schema.")
        result = cls(
            logical_path=str(payload["logical_path"]),
            role=str(payload["role"]),
            byte_count=int(payload["byte_count"]),
            sha256=str(payload["sha256"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-BASE0 artifact digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PerfBase0CorpusIdentity:
    corpus_id: str
    role: str
    selection_rule: str
    artifacts: tuple[PerfBase0ArtifactIdentity, ...]
    frame_count: int
    atom_count: int
    source_unit_count: int
    metadata_json_text: str = "{}"
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "corpus_id", _nonempty(self.corpus_id, name="corpus_id"))
        object.__setattr__(self, "role", _nonempty(self.role, name="corpus role"))
        object.__setattr__(self, "selection_rule", _nonempty(self.selection_rule, name="selection_rule"))
        artifacts = tuple(self.artifacts)
        if not artifacts:
            raise TrainingDataInputError("PERF-BASE0 corpus must contain at least one artifact.")
        logical_paths = [item.logical_path for item in artifacts]
        if len(logical_paths) != len(set(logical_paths)):
            raise TrainingDataInputError("PERF-BASE0 corpus artifact paths must be unique.")
        object.__setattr__(self, "artifacts", artifacts)
        object.__setattr__(self, "frame_count", _nonnegative_int(self.frame_count, name="corpus frame_count"))
        object.__setattr__(self, "atom_count", _nonnegative_int(self.atom_count, name="corpus atom_count"))
        object.__setattr__(self, "source_unit_count", _nonnegative_int(self.source_unit_count, name="source_unit_count"))
        try:
            metadata = json.loads(str(self.metadata_json_text))
        except json.JSONDecodeError as exc:
            raise TrainingDataInputError("PERF-BASE0 corpus metadata is not valid JSON.") from exc
        canonical = _canonical_text(metadata, name="corpus metadata")
        if canonical != self.metadata_json_text:
            raise TrainingDataInputError("PERF-BASE0 corpus metadata must be canonical JSON.")

    @classmethod
    def build(
        cls,
        *,
        corpus_id: str,
        role: str,
        selection_rule: str,
        artifacts: Sequence[PerfBase0ArtifactIdentity],
        frame_count: int,
        atom_count: int,
        source_unit_count: int,
        metadata: Mapping[str, Any] | None = None,
    ) -> "PerfBase0CorpusIdentity":
        return cls(
            corpus_id=corpus_id,
            role=role,
            selection_rule=selection_rule,
            artifacts=tuple(artifacts),
            frame_count=frame_count,
            atom_count=atom_count,
            source_unit_count=source_unit_count,
            metadata_json_text=_canonical_text({} if metadata is None else metadata, name="corpus metadata"),
        )

    @property
    def metadata(self) -> Any:
        return _json_from_text(self.metadata_json_text)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PERF_BASE0_CORPUS_SCHEMA,
            "corpus_id": self.corpus_id,
            "role": self.role,
            "selection_rule": self.selection_rule,
            "artifacts": [item.to_dict() for item in self.artifacts],
            "frame_count": self.frame_count,
            "atom_count": self.atom_count,
            "source_unit_count": self.source_unit_count,
            "metadata": self.metadata,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfBase0CorpusIdentity":
        if payload.get("schema") != PERF_BASE0_CORPUS_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERF-BASE0 corpus schema.")
        result = cls.build(
            corpus_id=str(payload["corpus_id"]),
            role=str(payload["role"]),
            selection_rule=str(payload["selection_rule"]),
            artifacts=tuple(PerfBase0ArtifactIdentity.from_dict(item) for item in payload["artifacts"]),
            frame_count=int(payload["frame_count"]),
            atom_count=int(payload["atom_count"]),
            source_unit_count=int(payload["source_unit_count"]),
            metadata=payload.get("metadata", {}),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-BASE0 corpus digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PerfBase0ScientificStage:
    stage_id: str
    algorithm_ids: tuple[str, ...]
    corpus_digests: tuple[str, ...]
    policy_digests: tuple[str, ...]
    subset_rule: str
    arrays: tuple[PerfBase0ArrayReference, ...] = ()
    json_references: tuple[PerfBase0JsonReference, ...] = ()
    notes: tuple[str, ...] = ()
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "stage_id", _nonempty(self.stage_id, name="scientific stage_id"))
        object.__setattr__(self, "algorithm_ids", _unique_nonempty(self.algorithm_ids, name="algorithm_ids"))
        corpus_digests = tuple(validate_digest(value, name="corpus_digest") for value in self.corpus_digests)
        policy_digests = tuple(validate_digest(value, name="policy_digest") for value in self.policy_digests)
        if len(corpus_digests) != len(set(corpus_digests)):
            raise TrainingDataInputError("PERF-BASE0 scientific-stage corpus digests must be unique.")
        if len(policy_digests) != len(set(policy_digests)):
            raise TrainingDataInputError("PERF-BASE0 scientific-stage policy digests must be unique.")
        object.__setattr__(self, "corpus_digests", corpus_digests)
        object.__setattr__(self, "policy_digests", policy_digests)
        object.__setattr__(self, "subset_rule", _nonempty(self.subset_rule, name="subset_rule"))
        arrays = tuple(self.arrays)
        json_references = tuple(self.json_references)
        names = [item.name for item in arrays] + [item.name for item in json_references]
        if len(names) != len(set(names)):
            raise TrainingDataInputError("PERF-BASE0 scientific reference names must be unique within a stage.")
        if not names:
            raise TrainingDataInputError("PERF-BASE0 scientific stage must contain at least one reference.")
        object.__setattr__(self, "arrays", arrays)
        object.__setattr__(self, "json_references", json_references)
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PERF_BASE0_SCIENTIFIC_STAGE_SCHEMA,
            "stage_id": self.stage_id,
            "algorithm_ids": list(self.algorithm_ids),
            "corpus_digests": list(self.corpus_digests),
            "policy_digests": list(self.policy_digests),
            "subset_rule": self.subset_rule,
            "arrays": [item.to_dict() for item in self.arrays],
            "json_references": [item.to_dict() for item in self.json_references],
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfBase0ScientificStage":
        if payload.get("schema") != PERF_BASE0_SCIENTIFIC_STAGE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERF-BASE0 scientific-stage schema.")
        result = cls(
            stage_id=str(payload["stage_id"]),
            algorithm_ids=tuple(str(value) for value in payload.get("algorithm_ids", ())),
            corpus_digests=tuple(str(value) for value in payload.get("corpus_digests", ())),
            policy_digests=tuple(str(value) for value in payload.get("policy_digests", ())),
            subset_rule=str(payload["subset_rule"]),
            arrays=tuple(PerfBase0ArrayReference.from_dict(item) for item in payload.get("arrays", ())),
            json_references=tuple(
                PerfBase0JsonReference.from_dict(item) for item in payload.get("json_references", ())
            ),
            notes=tuple(str(value) for value in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-BASE0 scientific-stage digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PerfBase0ExecutionTelemetry:
    stage_id: str
    measured_at_utc: str
    wall_seconds: float
    process_cpu_seconds: float
    effective_cpu_cores: float
    rss_start_bytes: int
    rss_end_bytes: int
    sampled_peak_rss_bytes: int
    process_peak_rss_bytes: int
    temporary_array_bytes: int
    read_bytes: int
    write_bytes: int
    read_characters: int
    written_characters: int
    throughput_count: int
    throughput_unit: str
    throughput_per_second: float
    worker_settings_json_text: str = "{}"
    environment_json_text: str = "{}"
    events: tuple[str, ...] = ()
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "stage_id", _nonempty(self.stage_id, name="telemetry stage_id"))
        object.__setattr__(self, "measured_at_utc", _utc_timestamp(self.measured_at_utc, name="measured_at_utc"))
        wall = _finite_nonnegative(self.wall_seconds, name="wall_seconds")
        cpu = _finite_nonnegative(self.process_cpu_seconds, name="process_cpu_seconds")
        cores = _finite_nonnegative(self.effective_cpu_cores, name="effective_cpu_cores")
        counts = {
            "rss_start_bytes": self.rss_start_bytes,
            "rss_end_bytes": self.rss_end_bytes,
            "sampled_peak_rss_bytes": self.sampled_peak_rss_bytes,
            "process_peak_rss_bytes": self.process_peak_rss_bytes,
            "temporary_array_bytes": self.temporary_array_bytes,
            "read_bytes": self.read_bytes,
            "write_bytes": self.write_bytes,
            "read_characters": self.read_characters,
            "written_characters": self.written_characters,
            "throughput_count": self.throughput_count,
        }
        normalized = {name: _nonnegative_int(value, name=name) for name, value in counts.items()}
        throughput_unit = _nonempty(self.throughput_unit, name="throughput_unit")
        throughput_rate = _finite_nonnegative(self.throughput_per_second, name="throughput_per_second")
        if wall > 0.0:
            expected = normalized["throughput_count"] / wall
            if not np.isclose(throughput_rate, expected, rtol=1.0e-10, atol=1.0e-12):
                raise TrainingDataInputError("PERF-BASE0 throughput rate is inconsistent with count and wall time.")
        elif throughput_rate != 0.0:
            raise TrainingDataInputError("Zero-duration telemetry must have zero throughput.")
        if normalized["sampled_peak_rss_bytes"] < max(
            normalized["rss_start_bytes"], normalized["rss_end_bytes"]
        ):
            raise TrainingDataInputError("Sampled peak RSS cannot be below start/end RSS.")
        for field_name in ("worker_settings_json_text", "environment_json_text"):
            text = str(getattr(self, field_name))
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise TrainingDataInputError(f"{field_name} is not valid JSON.") from exc
            canonical = _canonical_text(value, name=field_name)
            if canonical != text:
                raise TrainingDataInputError(f"{field_name} must be canonical JSON.")
        object.__setattr__(self, "wall_seconds", wall)
        object.__setattr__(self, "process_cpu_seconds", cpu)
        object.__setattr__(self, "effective_cpu_cores", cores)
        for name, value in normalized.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "throughput_unit", throughput_unit)
        object.__setattr__(self, "throughput_per_second", throughput_rate)
        object.__setattr__(self, "events", tuple(str(value) for value in self.events))

    @classmethod
    def build(
        cls,
        *,
        stage_id: str,
        measured_at_utc: str,
        wall_seconds: float,
        process_cpu_seconds: float,
        rss_start_bytes: int,
        rss_end_bytes: int,
        sampled_peak_rss_bytes: int,
        process_peak_rss_bytes: int,
        temporary_array_bytes: int,
        read_bytes: int,
        write_bytes: int,
        read_characters: int,
        written_characters: int,
        throughput_count: int,
        throughput_unit: str,
        worker_settings: Mapping[str, Any] | None = None,
        environment: Mapping[str, Any] | None = None,
        events: Sequence[str] = (),
    ) -> "PerfBase0ExecutionTelemetry":
        wall = float(wall_seconds)
        cpu = float(process_cpu_seconds)
        return cls(
            stage_id=stage_id,
            measured_at_utc=measured_at_utc,
            wall_seconds=wall,
            process_cpu_seconds=cpu,
            effective_cpu_cores=0.0 if wall <= 0.0 else cpu / wall,
            rss_start_bytes=rss_start_bytes,
            rss_end_bytes=rss_end_bytes,
            sampled_peak_rss_bytes=sampled_peak_rss_bytes,
            process_peak_rss_bytes=process_peak_rss_bytes,
            temporary_array_bytes=temporary_array_bytes,
            read_bytes=read_bytes,
            write_bytes=write_bytes,
            read_characters=read_characters,
            written_characters=written_characters,
            throughput_count=throughput_count,
            throughput_unit=throughput_unit,
            throughput_per_second=0.0 if wall <= 0.0 else int(throughput_count) / wall,
            worker_settings_json_text=_canonical_text(
                {} if worker_settings is None else worker_settings,
                name="worker_settings",
            ),
            environment_json_text=_canonical_text(
                {} if environment is None else environment,
                name="environment",
            ),
            events=tuple(events),
        )

    @property
    def worker_settings(self) -> Any:
        return _json_from_text(self.worker_settings_json_text)

    @property
    def environment(self) -> Any:
        return _json_from_text(self.environment_json_text)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PERF_BASE0_TELEMETRY_SCHEMA,
            "stage_id": self.stage_id,
            "measured_at_utc": self.measured_at_utc,
            "wall_seconds": self.wall_seconds,
            "process_cpu_seconds": self.process_cpu_seconds,
            "effective_cpu_cores": self.effective_cpu_cores,
            "rss_start_bytes": self.rss_start_bytes,
            "rss_end_bytes": self.rss_end_bytes,
            "sampled_peak_rss_bytes": self.sampled_peak_rss_bytes,
            "process_peak_rss_bytes": self.process_peak_rss_bytes,
            "temporary_array_bytes": self.temporary_array_bytes,
            "read_bytes": self.read_bytes,
            "write_bytes": self.write_bytes,
            "read_characters": self.read_characters,
            "written_characters": self.written_characters,
            "throughput_count": self.throughput_count,
            "throughput_unit": self.throughput_unit,
            "throughput_per_second": self.throughput_per_second,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfBase0ExecutionTelemetry":
        if payload.get("schema") != PERF_BASE0_TELEMETRY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERF-BASE0 telemetry schema.")
        result = cls(
            stage_id=str(payload["stage_id"]),
            measured_at_utc=str(payload["measured_at_utc"]),
            wall_seconds=float(payload["wall_seconds"]),
            process_cpu_seconds=float(payload["process_cpu_seconds"]),
            effective_cpu_cores=float(payload["effective_cpu_cores"]),
            rss_start_bytes=int(payload["rss_start_bytes"]),
            rss_end_bytes=int(payload["rss_end_bytes"]),
            sampled_peak_rss_bytes=int(payload["sampled_peak_rss_bytes"]),
            process_peak_rss_bytes=int(payload["process_peak_rss_bytes"]),
            temporary_array_bytes=int(payload["temporary_array_bytes"]),
            read_bytes=int(payload["read_bytes"]),
            write_bytes=int(payload["write_bytes"]),
            read_characters=int(payload["read_characters"]),
            written_characters=int(payload["written_characters"]),
            throughput_count=int(payload["throughput_count"]),
            throughput_unit=str(payload["throughput_unit"]),
            throughput_per_second=float(payload["throughput_per_second"]),
            worker_settings_json_text=_canonical_text_from_serialized(
                payload.get("worker_settings", {}), name="worker_settings"
            ),
            environment_json_text=_canonical_text_from_serialized(
                payload.get("environment", {}), name="environment"
            ),
            events=tuple(str(value) for value in payload.get("events", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-BASE0 telemetry digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PerfBase0Record:
    baseline_id: str
    source_version: str
    created_at_utc: str
    authority_status: str
    source_artifacts: tuple[PerfBase0ArtifactIdentity, ...]
    corpora: tuple[PerfBase0CorpusIdentity, ...]
    scientific_stages: tuple[PerfBase0ScientificStage, ...]
    execution_telemetry: tuple[PerfBase0ExecutionTelemetry, ...]
    unavailable_stages: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    _scientific_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)
    _execution_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "baseline_id", _nonempty(self.baseline_id, name="baseline_id"))
        object.__setattr__(self, "source_version", _nonempty(self.source_version, name="source_version"))
        object.__setattr__(self, "created_at_utc", _utc_timestamp(self.created_at_utc, name="created_at_utc"))
        status = _nonempty(self.authority_status, name="authority_status")
        if status not in {"complete", "bounded", "partial"}:
            raise TrainingDataInputError("PERF-BASE0 authority_status must be complete, bounded, or partial.")
        object.__setattr__(self, "authority_status", status)
        source_artifacts = tuple(self.source_artifacts)
        corpora = tuple(self.corpora)
        stages = tuple(self.scientific_stages)
        telemetry = tuple(self.execution_telemetry)
        if not corpora or not stages:
            raise TrainingDataInputError("PERF-BASE0 record requires corpora and scientific stages.")
        for items, label, key in (
            (source_artifacts, "source artifact", lambda item: item.logical_path),
            (corpora, "corpus", lambda item: item.corpus_id),
            (stages, "scientific stage", lambda item: item.stage_id),
            (telemetry, "telemetry stage", lambda item: item.stage_id),
        ):
            keys = [key(item) for item in items]
            if len(keys) != len(set(keys)):
                raise TrainingDataInputError(f"PERF-BASE0 {label} identities must be unique.")
        corpus_digest_set = {item.content_digest for item in corpora}
        for stage in stages:
            unknown = set(stage.corpus_digests) - corpus_digest_set
            if unknown:
                raise TrainingDataInputError(
                    f"PERF-BASE0 scientific stage {stage.stage_id!r} cites an unknown corpus digest."
                )
        stage_ids = {item.stage_id for item in stages}
        if any(item.stage_id not in stage_ids for item in telemetry):
            raise TrainingDataInputError("PERF-BASE0 telemetry cannot cite a non-scientific stage.")
        object.__setattr__(self, "source_artifacts", source_artifacts)
        object.__setattr__(self, "corpora", corpora)
        object.__setattr__(self, "scientific_stages", stages)
        object.__setattr__(self, "execution_telemetry", telemetry)
        object.__setattr__(self, "unavailable_stages", _unique_nonempty(self.unavailable_stages, name="unavailable_stages"))
        object.__setattr__(self, "limitations", tuple(str(value) for value in self.limitations))

    def _scientific_payload(self) -> dict[str, Any]:
        return {
            "schema": "mdstats.perf-base0-scientific-authority.v1",
            "authority_version": PERF_BASE0_VERSION,
            "corpora": [item.to_dict() for item in self.corpora],
            "scientific_stages": [item.to_dict() for item in self.scientific_stages],
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
            "schema": "mdstats.perf-base0-execution-authority.v1",
            "execution_telemetry": [item.to_dict() for item in self.execution_telemetry],
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
            "schema": PERF_BASE0_RECORD_SCHEMA,
            "authority_version": PERF_BASE0_VERSION,
            "baseline_id": self.baseline_id,
            "source_version": self.source_version,
            "created_at_utc": self.created_at_utc,
            "authority_status": self.authority_status,
            "source_artifacts": [item.to_dict() for item in self.source_artifacts],
            "corpora": [item.to_dict() for item in self.corpora],
            "scientific_stages": [item.to_dict() for item in self.scientific_stages],
            "execution_telemetry": [item.to_dict() for item in self.execution_telemetry],
            "unavailable_stages": list(self.unavailable_stages),
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfBase0Record":
        if payload.get("schema") != PERF_BASE0_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERF-BASE0 record schema.")
        if payload.get("authority_version") != PERF_BASE0_VERSION:
            raise TrainingDataSerializationError("Unsupported PERF-BASE0 authority version.")
        result = cls(
            baseline_id=str(payload["baseline_id"]),
            source_version=str(payload["source_version"]),
            created_at_utc=str(payload["created_at_utc"]),
            authority_status=str(payload["authority_status"]),
            source_artifacts=tuple(
                PerfBase0ArtifactIdentity.from_dict(item) for item in payload.get("source_artifacts", ())
            ),
            corpora=tuple(PerfBase0CorpusIdentity.from_dict(item) for item in payload.get("corpora", ())),
            scientific_stages=tuple(
                PerfBase0ScientificStage.from_dict(item) for item in payload.get("scientific_stages", ())
            ),
            execution_telemetry=tuple(
                PerfBase0ExecutionTelemetry.from_dict(item)
                for item in payload.get("execution_telemetry", ())
            ),
            unavailable_stages=tuple(str(value) for value in payload.get("unavailable_stages", ())),
            limitations=tuple(str(value) for value in payload.get("limitations", ())),
        )
        if payload.get("scientific_digest") not in (None, result.scientific_digest):
            raise TrainingDataSerializationError("PERF-BASE0 scientific digest mismatch.")
        if payload.get("execution_digest") not in (None, result.execution_digest):
            raise TrainingDataSerializationError("PERF-BASE0 execution digest mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-BASE0 record digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PerfBase0Comparison:
    reference_scientific_digest: str
    candidate_scientific_digest: str
    scientific_match: bool
    mismatches: tuple[str, ...]
    performance_json_text: str
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        validate_digest(self.reference_scientific_digest, name="reference_scientific_digest")
        validate_digest(self.candidate_scientific_digest, name="candidate_scientific_digest")
        mismatches = tuple(str(value) for value in self.mismatches)
        if bool(self.scientific_match) == bool(mismatches):
            raise TrainingDataInputError(
                "PERF-BASE0 comparison scientific_match must be true exactly when mismatches are empty."
            )
        try:
            performance = json.loads(self.performance_json_text)
        except json.JSONDecodeError as exc:
            raise TrainingDataInputError("PERF-BASE0 performance comparison is not valid JSON.") from exc
        canonical = _canonical_text(performance, name="performance comparison")
        if canonical != self.performance_json_text:
            raise TrainingDataInputError("PERF-BASE0 performance comparison must be canonical JSON.")
        object.__setattr__(self, "mismatches", mismatches)

    @property
    def performance(self) -> Any:
        return _json_from_text(self.performance_json_text)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PERF_BASE0_COMPARISON_SCHEMA,
            "reference_scientific_digest": self.reference_scientific_digest,
            "candidate_scientific_digest": self.candidate_scientific_digest,
            "scientific_match": self.scientific_match,
            "mismatches": list(self.mismatches),
            "performance": self.performance,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfBase0Comparison":
        if payload.get("schema") != PERF_BASE0_COMPARISON_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERF-BASE0 comparison schema.")
        result = cls(
            reference_scientific_digest=str(payload["reference_scientific_digest"]),
            candidate_scientific_digest=str(payload["candidate_scientific_digest"]),
            scientific_match=bool(payload["scientific_match"]),
            mismatches=tuple(str(value) for value in payload.get("mismatches", ())),
            performance_json_text=_canonical_text_from_serialized(
                payload.get("performance", {}), name="performance comparison"
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-BASE0 comparison digest mismatch.")
        return result


def compare_perf_base0_records(
    reference: PerfBase0Record,
    candidate: PerfBase0Record,
) -> PerfBase0Comparison:
    """Compare exact scientific authorities and report telemetry ratios separately."""

    mismatches: list[str] = []
    reference_corpora = {item.corpus_id: item for item in reference.corpora}
    candidate_corpora = {item.corpus_id: item for item in candidate.corpora}
    for corpus_id in sorted(set(reference_corpora) | set(candidate_corpora)):
        if corpus_id not in reference_corpora:
            mismatches.append(f"unexpected_corpus:{corpus_id}")
        elif corpus_id not in candidate_corpora:
            mismatches.append(f"missing_corpus:{corpus_id}")
        elif reference_corpora[corpus_id].content_digest != candidate_corpora[corpus_id].content_digest:
            mismatches.append(f"corpus_digest_mismatch:{corpus_id}")

    reference_stages = {item.stage_id: item for item in reference.scientific_stages}
    candidate_stages = {item.stage_id: item for item in candidate.scientific_stages}
    for stage_id in sorted(set(reference_stages) | set(candidate_stages)):
        if stage_id not in reference_stages:
            mismatches.append(f"unexpected_stage:{stage_id}")
        elif stage_id not in candidate_stages:
            mismatches.append(f"missing_stage:{stage_id}")
        elif reference_stages[stage_id].content_digest != candidate_stages[stage_id].content_digest:
            mismatches.append(f"stage_digest_mismatch:{stage_id}")

    reference_telemetry = {item.stage_id: item for item in reference.execution_telemetry}
    candidate_telemetry = {item.stage_id: item for item in candidate.execution_telemetry}
    performance: dict[str, Any] = {}
    for stage_id in sorted(set(reference_telemetry) & set(candidate_telemetry)):
        old = reference_telemetry[stage_id]
        new = candidate_telemetry[stage_id]
        performance[stage_id] = {
            "reference_wall_seconds": old.wall_seconds,
            "candidate_wall_seconds": new.wall_seconds,
            "wall_ratio_candidate_over_reference": (
                None if old.wall_seconds == 0.0 else new.wall_seconds / old.wall_seconds
            ),
            "reference_process_cpu_seconds": old.process_cpu_seconds,
            "candidate_process_cpu_seconds": new.process_cpu_seconds,
            "cpu_ratio_candidate_over_reference": (
                None if old.process_cpu_seconds == 0.0 else new.process_cpu_seconds / old.process_cpu_seconds
            ),
            "reference_sampled_peak_rss_bytes": old.sampled_peak_rss_bytes,
            "candidate_sampled_peak_rss_bytes": new.sampled_peak_rss_bytes,
            "rss_ratio_candidate_over_reference": (
                None
                if old.sampled_peak_rss_bytes == 0
                else new.sampled_peak_rss_bytes / old.sampled_peak_rss_bytes
            ),
            "reference_throughput_per_second": old.throughput_per_second,
            "candidate_throughput_per_second": new.throughput_per_second,
        }
    return PerfBase0Comparison(
        reference_scientific_digest=reference.scientific_digest,
        candidate_scientific_digest=candidate.scientific_digest,
        scientific_match=not mismatches,
        mismatches=tuple(mismatches),
        performance_json_text=_canonical_text(performance, name="performance comparison"),
    )


def assert_perf_base0_scientific_equivalence(
    reference: PerfBase0Record,
    candidate: PerfBase0Record,
) -> PerfBase0Comparison:
    comparison = compare_perf_base0_records(reference, candidate)
    if not comparison.scientific_match:
        raise TrainingDataInputError(
            "PERF-BASE0 scientific equivalence failed: " + ", ".join(comparison.mismatches)
        )
    return comparison


def write_perf_base0_record(path: str | Path, record: PerfBase0Record) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(record.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, target)
    return target


def read_perf_base0_record(path: str | Path) -> PerfBase0Record:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TrainingDataSerializationError(f"Cannot read PERF-BASE0 record {source!s}.") from exc
    if not isinstance(payload, Mapping):
        raise TrainingDataSerializationError("PERF-BASE0 record root must be a mapping.")
    return PerfBase0Record.from_dict(payload)


def _read_proc_status_rss_bytes() -> int:
    try:
        for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return 0


def _process_peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    # Linux reports KiB; macOS reports bytes.
    return value if sys.platform == "darwin" else value * 1024


def _read_proc_io() -> dict[str, int]:
    result = {"read_bytes": 0, "write_bytes": 0, "rchar": 0, "wchar": 0}
    try:
        for line in Path("/proc/self/io").read_text(encoding="utf-8").splitlines():
            key, value = line.split(":", 1)
            if key in result:
                result[key] = int(value.strip())
    except (OSError, ValueError):
        pass
    return result


def _read_text_file(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def perf_base0_runtime_environment() -> dict[str, Any]:
    """Return host/runtime facts suitable for execution telemetry only."""

    cpu_max = _read_text_file("/sys/fs/cgroup/cpu.max")
    memory_max = _read_text_file("/sys/fs/cgroup/memory.max")
    cpuset = _read_text_file("/sys/fs/cgroup/cpuset.cpus.effective")
    cpu_model = None
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.lower().startswith("model name"):
                cpu_model = line.split(":", 1)[1].strip()
                break
    except (OSError, ValueError, IndexError):
        pass
    cgroup_cpu_quota_cores = None
    if cpu_max:
        fields = cpu_max.split()
        if len(fields) == 2 and fields[0] != "max":
            try:
                cgroup_cpu_quota_cores = float(fields[0]) / float(fields[1])
            except (ValueError, ZeroDivisionError):
                pass
    package_versions: dict[str, str | None] = {}
    for distribution in (
        "mdstats",
        "numpy",
        "scipy",
        "ase",
        "threadpoolctl",
        "torch",
        "mace-torch",
        "e3nn",
    ):
        try:
            package_versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            package_versions[distribution] = None
    # The source checkout can intentionally supersede installed metadata.
    try:
        from .._version import __version__ as source_version
    except Exception:  # pragma: no cover - defensive telemetry path
        source_version = None
    package_versions["mdstats_source"] = source_version
    threadpools = []
    try:
        for item in threadpool_info():
            threadpools.append(
                {
                    "user_api": item.get("user_api"),
                    "internal_api": item.get("internal_api"),
                    "num_threads": item.get("num_threads"),
                    "prefix": item.get("prefix"),
                    "version": item.get("version"),
                    "threading_layer": item.get("threading_layer"),
                    "architecture": item.get("architecture"),
                }
            )
    except Exception as exc:  # pragma: no cover - defensive telemetry path
        threadpools = [{"inspection_error": f"{type(exc).__name__}: {exc}"}]
    return json_value(
        {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_model": cpu_model,
            "logical_cpu_count": os.cpu_count(),
            "affinity_cpu_count": (
                len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None
            ),
            "cgroup_cpu_max": cpu_max,
            "cgroup_cpu_quota_cores": cgroup_cpu_quota_cores,
            "cgroup_cpuset_effective": cpuset,
            "cgroup_memory_max": memory_max,
            "package_versions": package_versions,
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "threadpools": threadpools,
            "environment_threads": {
                key: os.environ.get(key)
                for key in (
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS",
                    "VECLIB_MAXIMUM_THREADS",
                )
            },
        }
    )


class PerfBase0StageMeter:
    """Stage-local wall/CPU/RSS/I/O meter with a lightweight RSS sampler."""

    def __init__(
        self,
        stage_id: str,
        *,
        worker_settings: Mapping[str, Any] | None = None,
        sample_interval_seconds: float = 0.01,
        environment: Mapping[str, Any] | None = None,
    ) -> None:
        self.stage_id = _nonempty(stage_id, name="meter stage_id")
        self.worker_settings = {} if worker_settings is None else json_value(worker_settings)
        interval = float(sample_interval_seconds)
        if not np.isfinite(interval) or interval <= 0.0:
            raise TrainingDataInputError("sample_interval_seconds must be finite and positive.")
        self.sample_interval_seconds = interval
        self.environment = (
            perf_base0_runtime_environment() if environment is None else json_value(environment)
        )
        self._started = False
        self._closed = False
        self._stop = threading.Event()
        self._sampler: threading.Thread | None = None
        self._peak_rss = 0
        self._measured_at = ""
        self._wall_start = 0.0
        self._cpu_start = 0.0
        self._io_start: dict[str, int] = {}
        self._rss_start = 0
        self._wall_seconds = 0.0
        self._cpu_seconds = 0.0
        self._io_end: dict[str, int] = {}
        self._rss_end = 0

    def _sample(self) -> None:
        while not self._stop.wait(self.sample_interval_seconds):
            self._peak_rss = max(self._peak_rss, _read_proc_status_rss_bytes())

    def __enter__(self) -> "PerfBase0StageMeter":
        if self._started:
            raise TrainingDataInputError("PERF-BASE0 stage meter cannot be entered twice.")
        self._started = True
        self._measured_at = _now_utc()
        self._rss_start = _read_proc_status_rss_bytes()
        self._peak_rss = self._rss_start
        self._io_start = _read_proc_io()
        self._cpu_start = time.process_time()
        self._wall_start = time.perf_counter()
        self._sampler = threading.Thread(
            target=self._sample,
            name=f"perf-base0-rss-{self.stage_id}",
            daemon=True,
        )
        self._sampler.start()
        return self

    def close(self) -> None:
        if not self._started or self._closed:
            return
        self._wall_seconds = time.perf_counter() - self._wall_start
        self._cpu_seconds = time.process_time() - self._cpu_start
        self._stop.set()
        if self._sampler is not None:
            self._sampler.join(timeout=max(0.1, self.sample_interval_seconds * 4.0))
        self._rss_end = _read_proc_status_rss_bytes()
        self._peak_rss = max(self._peak_rss, self._rss_end)
        self._io_end = _read_proc_io()
        self._closed = True

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()

    def telemetry(
        self,
        *,
        throughput_count: int,
        throughput_unit: str,
        temporary_array_bytes: int = 0,
        events: Sequence[str] = (),
    ) -> PerfBase0ExecutionTelemetry:
        self.close()
        if not self._closed:
            raise TrainingDataInputError("PERF-BASE0 stage meter was not started.")
        def delta(key: str) -> int:
            return max(0, int(self._io_end.get(key, 0)) - int(self._io_start.get(key, 0)))
        return PerfBase0ExecutionTelemetry.build(
            stage_id=self.stage_id,
            measured_at_utc=self._measured_at,
            wall_seconds=self._wall_seconds,
            process_cpu_seconds=self._cpu_seconds,
            rss_start_bytes=self._rss_start,
            rss_end_bytes=self._rss_end,
            sampled_peak_rss_bytes=self._peak_rss,
            process_peak_rss_bytes=_process_peak_rss_bytes(),
            temporary_array_bytes=temporary_array_bytes,
            read_bytes=delta("read_bytes"),
            write_bytes=delta("write_bytes"),
            read_characters=delta("rchar"),
            written_characters=delta("wchar"),
            throughput_count=throughput_count,
            throughput_unit=throughput_unit,
            worker_settings=self.worker_settings,
            environment=self.environment,
            events=events,
        )


def render_perf_base0_markdown(record: PerfBase0Record) -> str:
    """Render a compact human-readable companion to a machine record."""

    lines = [
        "# mdstats MLFF PERF-BASE0 baseline",
        "",
        f"- Baseline ID: `{record.baseline_id}`",
        f"- Source version: `{record.source_version}`",
        f"- Authority status: **{record.authority_status}**",
        f"- Scientific digest: `{record.scientific_digest}`",
        f"- Execution digest: `{record.execution_digest}`",
        f"- Record digest: `{record.content_digest}`",
        "",
        "## Corpora",
        "",
        "| Corpus | Role | Frames | Atoms | Source units | Bytes |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for corpus in record.corpora:
        byte_count = sum(item.byte_count for item in corpus.artifacts)
        lines.append(
            f"| `{corpus.corpus_id}` | {corpus.role} | {corpus.frame_count:,} | "
            f"{corpus.atom_count:,} | {corpus.source_unit_count:,} | {byte_count:,} |"
        )
    lines.extend(
        [
            "",
            "## Scientific references",
            "",
            "| Stage | Subset rule | Arrays | JSON references | Digest |",
            "|---|---|---:|---:|---|",
        ]
    )
    for stage in record.scientific_stages:
        lines.append(
            f"| `{stage.stage_id}` | {stage.subset_rule} | {len(stage.arrays)} | "
            f"{len(stage.json_references)} | `{stage.content_digest}` |"
        )
    lines.extend(
        [
            "",
            "## CPU execution telemetry",
            "",
            "| Stage | Wall (s) | Process CPU (s) | Effective cores | Peak RSS (MiB) | Throughput |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for item in record.execution_telemetry:
        lines.append(
            f"| `{item.stage_id}` | {item.wall_seconds:.6f} | {item.process_cpu_seconds:.6f} | "
            f"{item.effective_cpu_cores:.3f} | {item.sampled_peak_rss_bytes / (1024**2):.2f} | "
            f"{item.throughput_per_second:.3f} {item.throughput_unit}/s |"
        )
    if record.unavailable_stages:
        lines.extend(["", "## Unavailable stages", ""])
        lines.extend(f"- `{value}`" for value in record.unavailable_stages)
    if record.limitations:
        lines.extend(["", "## Limitations", ""])
        lines.extend(f"- {value}" for value in record.limitations)
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "PERF_BASE0_VERSION",
    "PERF_BASE0_ARRAY_SCHEMA",
    "PERF_BASE0_JSON_SCHEMA",
    "PERF_BASE0_ARTIFACT_SCHEMA",
    "PERF_BASE0_CORPUS_SCHEMA",
    "PERF_BASE0_SCIENTIFIC_STAGE_SCHEMA",
    "PERF_BASE0_TELEMETRY_SCHEMA",
    "PERF_BASE0_RECORD_SCHEMA",
    "PERF_BASE0_COMPARISON_SCHEMA",
    "PerfBase0ArrayReference",
    "PerfBase0JsonReference",
    "PerfBase0ArtifactIdentity",
    "PerfBase0CorpusIdentity",
    "PerfBase0ScientificStage",
    "PerfBase0ExecutionTelemetry",
    "PerfBase0Record",
    "PerfBase0Comparison",
    "PerfBase0StageMeter",
    "perf_base0_runtime_environment",
    "compare_perf_base0_records",
    "assert_perf_base0_scientific_equivalence",
    "write_perf_base0_record",
    "read_perf_base0_record",
    "render_perf_base0_markdown",
]
