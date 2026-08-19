"""Restartable checkpoint-bound DATA6 model sweeps.

This module owns execution lineage and restart semantics for expensive foundation
model descriptors and predictions.  It does not fit DATA7 transforms, select
training frames, or execute DATA8 training jobs.
"""
from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
import hashlib
import gc
import io
import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from ._npz_mmap import load_npz_members_mmap

from ._common import sha256_file_cached
from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ._frame_access import ase_atoms_for_frame, build_frame_array_index
from .difficulty import (
    PredictionMaterializationStatus,
    build_blinded_prediction_domains,
    build_training_difficulty_domains,
)
from .model_features import (
    AtomicModelPrediction,
    AtomicModelProvider,
    MaceDescriptorFileRecord,
    MaceDescriptorManifest,
    MaceDescriptorPolicy,
    MaceDescriptorSignature,
    ModelCheckpointIdentity,
    read_mace_descriptor_record_array,
)
from .partition import OuterRole

DATA6_MODEL_SWEEP_PLAN_SCHEMA = "mdstats.data6-model-sweep-plan.v2"
DATA6_MODEL_SWEEP_PLAN_V1_SCHEMA = "mdstats.data6-model-sweep-plan.v1"
ATOMIC_MODEL_PREDICTION_FILE_SCHEMA = "mdstats.atomic-model-prediction-file.v2"
ATOMIC_MODEL_PREDICTION_FILE_LEGACY_SCHEMA = "mdstats.atomic-model-prediction-file.v1"
ATOMIC_MODEL_PREDICTION_MANIFEST_SCHEMA = "mdstats.atomic-model-prediction-manifest.v1"
DATA6_MODEL_SWEEP_FRAME_SCHEMA = "mdstats.data6-model-sweep-frame.v1"
DATA6_MODEL_SWEEP_CHECKPOINT_SCHEMA = "mdstats.data6-model-sweep-checkpoint.v1"
DATA6_MODEL_SWEEP_EXECUTION_POLICY_SCHEMA = "mdstats.data6-model-sweep-execution-policy.v4"
DATA6_MODEL_SWEEP_EXECUTION_POLICY_V3_SCHEMA = "mdstats.data6-model-sweep-execution-policy.v3"
DATA6_MODEL_SWEEP_EXECUTION_POLICY_V2_SCHEMA = "mdstats.data6-model-sweep-execution-policy.v2"
DATA6_MODEL_SWEEP_EXECUTION_POLICY_LEGACY_SCHEMA = "mdstats.data6-model-sweep-execution-policy.v1"
DATA6_RUNTIME_BATCH_CAP_SCHEMA = "mdstats.data6-runtime-batch-cap.v1"
DATA6_MODEL_SWEEP_JOURNAL_HEADER_SCHEMA = "mdstats.data6-model-sweep-journal-header.v1"
DATA6_MODEL_SWEEP_JOURNAL_EVENT_SCHEMA = "mdstats.data6-model-sweep-journal-event.v1"
MLFF_DATA9A9A_VERSION = "mdstats.mlff-data9a9a.production-model-sweep.2026-07.v1"


def _sha256_file(path: Path) -> str:
    return sha256_file_cached(path)


def _read_verified_file(path: Path, expected_sha256: str) -> bytes:
    """Read a sidecar once while validating its recorded SHA-256.

    The previous verifier first streamed the file for SHA-256 and then opened
    it again through NumPy.  For tens of thousands of small sidecars that
    doubles filesystem metadata and read traffic.  A single bounded per-file
    byte buffer preserves exact verification while halving storage reads.
    """

    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise TrainingDataSerializationError(f"Cannot read model sidecar: {path}") from exc
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise TrainingDataSerializationError("Model sidecar SHA-256 mismatch.")
    return payload


def _array_digest(array: np.ndarray) -> str:
    values = np.ascontiguousarray(array)
    hasher = hashlib.sha256()
    hasher.update(b"mdstats.array.v1\0")
    hasher.update(values.dtype.str.encode("ascii"))
    hasher.update(b"\0")
    hasher.update(repr(tuple(int(v) for v in values.shape)).encode("ascii"))
    hasher.update(b"\0")
    hasher.update(memoryview(values).cast("B"))
    return hasher.hexdigest()


class _HashingBinaryWriter(io.BufferedIOBase):
    """Non-seekable writer that hashes bytes exactly once as NumPy emits them."""

    def __init__(self, handle: Any):
        self._handle = handle
        self._hasher = hashlib.sha256()
        self._position = 0

    def writable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return False

    def write(self, payload: bytes | bytearray | memoryview) -> int:
        view = memoryview(payload)
        self._hasher.update(view)
        written = self._handle.write(view)
        self._position += int(written)
        return int(written)

    def tell(self) -> int:
        return self._position

    def flush(self) -> None:
        if not self._handle.closed:
            self._handle.flush()

    @property
    def hexdigest(self) -> str:
        return self._hasher.hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Stream deterministic compact JSON without a second giant string copy."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    encoder = json.JSONEncoder(sort_keys=False, separators=(",", ":"), ensure_ascii=True)
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            for chunk in encoder.iterencode(payload):
                handle.write(chunk)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _compact_json(payload: Mapping[str, Any]) -> str:
    """Return deterministic compact JSON for append-only journal records."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _ordered_records(
    plan: "Data6ModelSweepPlan",
    records: Mapping[str, "Data6ModelSweepFrameRecord"],
) -> tuple["Data6ModelSweepFrameRecord", ...]:
    """Return records in the already-sorted plan order.

    Supplying deterministic input order lets the checkpoint dataclass validate
    and retain canonical ordering without repeatedly sorting a growing mapping.
    """

    return tuple(records[uid] for uid in plan.requested_frame_uids if uid in records)


def _rewrite_model_sweep_journal(
    path: Path,
    plan: "Data6ModelSweepPlan",
    records: Mapping[str, "Data6ModelSweepFrameRecord"],
) -> None:
    """Atomically rebind verified sidecar records to a lineage-compatible plan.

    DATA3 reference/strain corrections can change the frame-catalog and DATA5
    bundle digests without changing any frame occurrence, geometry, model
    request, or sidecar payload.  Rewriting only the journal header and record
    envelopes avoids repeating an expensive foundation-model sweep while
    preserving fail-closed validation of every per-frame digest.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    header = {
        "schema": DATA6_MODEL_SWEEP_JOURNAL_HEADER_SCHEMA,
        "plan_content_digest": plan.content_digest,
    }
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(_compact_json(header) + "\n")
            for record in _ordered_records(plan, records):
                _append_model_sweep_journal_event(handle, record=record)
            _flush_model_sweep_journal(handle)
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _lineage_only_model_sweep_change(
    previous: "Data6ModelSweepPlan",
    current: "Data6ModelSweepPlan",
) -> bool:
    """Return whether two plans differ only in rebuilt catalog lineage.

    Frame-catalog and DATA5 digests are intentionally excluded.  Every field
    that can alter the requested inference work or interpretation of a
    sidecar remains equality constrained.
    """

    return (
        previous.dataset_id == current.dataset_id
        and previous.data6_policy_digest == current.data6_policy_digest
        and previous.checkpoint_identity.content_digest
        == current.checkpoint_identity.content_digest
        and previous.descriptor_policy.policy_digest
        == current.descriptor_policy.policy_digest
        and (
            None if previous.descriptor_signature is None else previous.descriptor_signature.content_digest
        )
        == (
            None if current.descriptor_signature is None else current.descriptor_signature.content_digest
        )
        and previous.descriptor_frame_uids == current.descriptor_frame_uids
        and previous.prediction_frame_uids == current.prediction_frame_uids
        and previous.requested_frame_uids == current.requested_frame_uids
        and previous.sealed_or_excluded_frame_uids
        == current.sealed_or_excluded_frame_uids
    )


def _model_sweep_records_match_frame_catalog(
    records: Mapping[str, "Data6ModelSweepFrameRecord"],
    frame_catalog: Any,
) -> bool:
    """Verify that reusable sidecars still bind to the exact frame records."""

    current_digests = {item.frame_uid: item.content_digest for item in frame_catalog.frames}
    for frame_uid, item in records.items():
        expected = current_digests.get(frame_uid)
        if expected is None:
            return False
        if (
            item.descriptor_record is not None
            and item.descriptor_record.frame_record_digest != expected
        ):
            return False
        if (
            item.prediction_record is not None
            and item.prediction_record.frame_record_digest != expected
        ):
            return False
    return True


def _initialize_model_sweep_journal(
    path: Path,
    plan: "Data6ModelSweepPlan",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    payload = {
        "schema": DATA6_MODEL_SWEEP_JOURNAL_HEADER_SCHEMA,
        "plan_content_digest": plan.content_digest,
    }
    temporary.write_text(_compact_json(payload) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _load_model_sweep_journal(
    path: Path,
    plan: "Data6ModelSweepPlan",
) -> tuple[dict[str, "Data6ModelSweepFrameRecord"], set[str]]:
    """Load valid journal events, tolerating only an incomplete final line.

    The journal is append-only.  A crash may leave one unterminated tail record;
    all prior newline-terminated events remain valid and restartable.
    """

    records: dict[str, Data6ModelSweepFrameRecord] = {}
    touched: set[str] = set()
    if not path.is_file():
        return records, touched
    truncate_offset: int | None = None
    append_newline = False
    with path.open("r", encoding="utf-8") as handle:
        header_line = handle.readline()
        if not header_line.endswith("\n"):
            raise TrainingDataSerializationError("DATA6 model-sweep journal header is truncated.")
        try:
            header = json.loads(header_line)
        except Exception as exc:
            raise TrainingDataSerializationError("Cannot parse DATA6 model-sweep journal header.") from exc
        if header.get("schema") != DATA6_MODEL_SWEEP_JOURNAL_HEADER_SCHEMA:
            raise TrainingDataSerializationError("Unsupported DATA6 model-sweep journal schema.")
        if header.get("plan_content_digest") != plan.content_digest:
            raise TrainingDataInputError("Existing DATA6 model-sweep journal belongs to a different plan.")
        line_number = 1
        while True:
            offset = handle.tell()
            line = handle.readline()
            if line == "":
                break
            line_number += 1
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except Exception as exc:
                if not line.endswith("\n"):
                    truncate_offset = offset
                    break
                raise TrainingDataSerializationError(
                    f"Cannot parse DATA6 model-sweep journal event on line {line_number}."
                ) from exc
            if event.get("schema") != DATA6_MODEL_SWEEP_JOURNAL_EVENT_SCHEMA:
                raise TrainingDataSerializationError("Unsupported DATA6 model-sweep journal event schema.")
            operation = str(event.get("operation", ""))
            if operation == "upsert":
                try:
                    record = Data6ModelSweepFrameRecord.from_dict(event["record"])
                except Exception as exc:
                    raise TrainingDataSerializationError(
                        f"Invalid DATA6 model-sweep journal record on line {line_number}."
                    ) from exc
                touched.add(record.frame_uid)
                records[record.frame_uid] = record
            elif operation == "delete":
                frame_uid = validate_digest(str(event.get("frame_uid", "")), name="frame_uid")
                touched.add(frame_uid)
                records.pop(frame_uid, None)
            else:
                raise TrainingDataSerializationError(
                    f"Unsupported DATA6 model-sweep journal operation {operation!r}."
                )
            if not line.endswith("\n"):
                append_newline = True
    if truncate_offset is not None:
        with path.open("r+b") as handle:
            handle.truncate(truncate_offset)
    elif append_newline:
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n")
    return records, touched


def _append_model_sweep_journal_event(
    handle: Any,
    *,
    record: "Data6ModelSweepFrameRecord" | None = None,
    frame_uid: str | None = None,
) -> None:
    if (record is None) == (frame_uid is None):
        raise TrainingDataInputError("Journal events require exactly one record or frame_uid.")
    if record is not None:
        payload: dict[str, Any] = {
            "schema": DATA6_MODEL_SWEEP_JOURNAL_EVENT_SCHEMA,
            "operation": "upsert",
            "record": record.to_dict(),
        }
    else:
        payload = {
            "schema": DATA6_MODEL_SWEEP_JOURNAL_EVENT_SCHEMA,
            "operation": "delete",
            "frame_uid": validate_digest(str(frame_uid), name="frame_uid"),
        }
    handle.write(_compact_json(payload) + "\n")


def _flush_model_sweep_journal(handle: Any) -> None:
    handle.flush()
    os.fsync(handle.fileno())


def _atomic_npy(path: Path, array: np.ndarray) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    writer: _HashingBinaryWriter | None = None
    try:
        with temporary.open("wb") as handle:
            writer = _HashingBinaryWriter(handle)
            np.save(writer, array, allow_pickle=False)
            writer.flush()
            os.fsync(handle.fileno())
        assert writer is not None
        file_sha256 = writer.hexdigest
        os.replace(temporary, path)
        return file_sha256
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _atomic_npz(path: Path, **arrays: np.ndarray) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    writer: _HashingBinaryWriter | None = None
    try:
        with temporary.open("wb") as handle:
            writer = _HashingBinaryWriter(handle)
            np.savez(writer, **arrays)
            writer.flush()
            os.fsync(handle.fileno())
        assert writer is not None
        file_sha256 = writer.hexdigest
        os.replace(temporary, path)
        return file_sha256
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _file_identity(path: Path) -> tuple[str, int, int, int, int, int]:
    stat = path.stat()
    return (
        str(path.resolve()),
        int(stat.st_dev),
        int(stat.st_ino),
        int(stat.st_size),
        int(stat.st_mtime_ns),
        int(getattr(stat, "st_ctime_ns", 0)),
    )


@lru_cache(maxsize=8)
def _load_prediction_shard_cached(
    identity: tuple[str, int, int, int, int, int],
    expected_sha256: str,
    members: tuple[str, ...],
) -> Mapping[str, np.ndarray]:
    """Authenticate one prediction shard and load only required arrays.

    Energy-only consumers must not decompress or retain force/stress tensors.
    The requested-member tuple is part of the immutable cache key so full
    validation and scalar-only residual-E0 paths remain independently bounded.
    """

    path = Path(identity[0])
    if _sha256_file(path) != expected_sha256:
        raise TrainingDataSerializationError("Prediction shard SHA-256 mismatch.")
    requested = tuple(dict.fromkeys(str(name) for name in members))
    if not requested:
        raise TrainingDataSerializationError("Prediction shard member request is empty.")
    try:
        result = load_npz_members_mmap(path, requested)
    except KeyError as exc:
        raise TrainingDataSerializationError(
            f"Prediction shard is missing members: {tuple(exc.args[0])}."
        ) from exc
    except Exception as exc:
        raise TrainingDataSerializationError("Cannot read prediction shard.") from exc
    return result


def _load_prediction_shard(
    path: Path, expected_sha256: str, members: Sequence[str]
) -> Mapping[str, np.ndarray]:
    return _load_prediction_shard_cached(
        _file_identity(path), expected_sha256, tuple(str(name) for name in members)
    )


def _artifact_shard_token(frame_uids: Sequence[str]) -> str:
    hasher = hashlib.sha256()
    for uid in frame_uids:
        hasher.update(uid.encode("ascii"))
        hasher.update(b"\0")
    return hasher.hexdigest()[:20]


def _frames_for_roles(data5_bundle: Any, roles: Sequence[str]) -> tuple[str, ...]:
    role_set = {OuterRole(value) for value in roles}
    frames: list[str] = []
    for outer in data5_bundle.outer_partitions:
        for assignment in outer.assignments:
            if assignment.role in role_set:
                frames.extend(data5_bundle.unit_catalog.unit(assignment.unit_id).frame_uids)
    return tuple(sorted(set(frames)))


def _all_data5_frames(data5_bundle: Any) -> tuple[str, ...]:
    frames: list[str] = []
    for unit in data5_bundle.unit_catalog.units:
        frames.extend(unit.frame_uids)
    return tuple(sorted(set(frames)))


@dataclass(frozen=True, slots=True)
class Data6ModelSweepPlan:
    dataset_id: str
    frame_catalog_digest: str
    data5_bundle_digest: str
    data6_policy_digest: str
    checkpoint_identity: ModelCheckpointIdentity
    descriptor_policy: MaceDescriptorPolicy
    descriptor_frame_uids: tuple[str, ...]
    prediction_frame_uids: tuple[str, ...]
    requested_frame_uids: tuple[str, ...]
    sealed_or_excluded_frame_uids: tuple[str, ...]
    descriptor_signature: MaceDescriptorSignature | None = None
    plan_version: str = MLFF_DATA9A9A_VERSION
    serialization_schema: str = field(default=DATA6_MODEL_SWEEP_PLAN_SCHEMA, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.dataset_id.strip() or not self.plan_version.strip():
            raise TrainingDataInputError("DATA6 model-sweep identifiers must be non-empty.")
        for name in ("frame_catalog_digest", "data5_bundle_digest", "data6_policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in (
            "descriptor_frame_uids",
            "prediction_frame_uids",
            "requested_frame_uids",
            "sealed_or_excluded_frame_uids",
        ):
            values = tuple(sorted(set(validate_digest(v, name="frame_uid") for v in getattr(self, name))))
            object.__setattr__(self, name, values)
        expected = tuple(sorted(set(self.descriptor_frame_uids) | set(self.prediction_frame_uids)))
        if self.requested_frame_uids != expected:
            raise TrainingDataInputError("DATA6 model-sweep requested frames must equal descriptor/prediction union.")
        if set(self.requested_frame_uids) & set(self.sealed_or_excluded_frame_uids):
            raise TrainingDataInputError("DATA6 model-sweep requested and sealed/excluded frames overlap.")
        if not self.requested_frame_uids:
            raise TrainingDataInputError("DATA6 model sweep contains no requested frames.")
        if self.serialization_schema not in {
            DATA6_MODEL_SWEEP_PLAN_SCHEMA,
            DATA6_MODEL_SWEEP_PLAN_V1_SCHEMA,
        }:
            raise TrainingDataInputError("Unsupported DATA6 model-sweep plan serialization schema.")
        if self.descriptor_signature is None:
            object.__setattr__(self, "serialization_schema", DATA6_MODEL_SWEEP_PLAN_V1_SCHEMA)
        elif self.serialization_schema == DATA6_MODEL_SWEEP_PLAN_V1_SCHEMA:
            raise TrainingDataInputError("Legacy DATA6 model-sweep plans cannot carry descriptor signatures.")
        else:
            if self.descriptor_signature.invariants_only != self.descriptor_policy.invariants_only:
                raise TrainingDataInputError("DATA6 descriptor signature/policy mismatch.")
            expected_layers = (
                self.descriptor_signature.num_interactions
                if self.descriptor_policy.num_layers is None
                else int(self.descriptor_policy.num_layers)
            )
            if self.descriptor_signature.num_layers != expected_layers:
                raise TrainingDataInputError("DATA6 descriptor signature/policy layer-count mismatch.")

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": self.serialization_schema,
            "plan_version": self.plan_version,
            "dataset_id": self.dataset_id,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "data6_policy_digest": self.data6_policy_digest,
            "checkpoint_identity": self.checkpoint_identity.to_dict(),
            "descriptor_policy": self.descriptor_policy.to_dict(),
            "descriptor_frame_uids": list(self.descriptor_frame_uids),
            "prediction_frame_uids": list(self.prediction_frame_uids),
            "requested_frame_uids": list(self.requested_frame_uids),
            "sealed_or_excluded_frame_uids": list(self.sealed_or_excluded_frame_uids),
        }
        if self.serialization_schema == DATA6_MODEL_SWEEP_PLAN_SCHEMA:
            payload["descriptor_signature"] = self.descriptor_signature.to_dict() if self.descriptor_signature is not None else None
        return payload

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Data6ModelSweepPlan":
        schema = payload.get("schema")
        if schema not in {DATA6_MODEL_SWEEP_PLAN_SCHEMA, DATA6_MODEL_SWEEP_PLAN_V1_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported DATA6 model-sweep plan schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            data5_bundle_digest=str(payload["data5_bundle_digest"]),
            data6_policy_digest=str(payload["data6_policy_digest"]),
            checkpoint_identity=ModelCheckpointIdentity.from_dict(payload["checkpoint_identity"]),
            descriptor_policy=MaceDescriptorPolicy.from_dict(payload["descriptor_policy"]),
            descriptor_frame_uids=tuple(str(v) for v in payload["descriptor_frame_uids"]),
            prediction_frame_uids=tuple(str(v) for v in payload["prediction_frame_uids"]),
            requested_frame_uids=tuple(str(v) for v in payload["requested_frame_uids"]),
            sealed_or_excluded_frame_uids=tuple(str(v) for v in payload["sealed_or_excluded_frame_uids"]),
            descriptor_signature=(
                None
                if schema == DATA6_MODEL_SWEEP_PLAN_V1_SCHEMA or payload.get("descriptor_signature") is None
                else MaceDescriptorSignature.from_dict(payload["descriptor_signature"])
            ),
            plan_version=str(payload["plan_version"]),
            serialization_schema=str(schema),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("DATA6 model-sweep plan digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class AtomicModelPredictionFileRecord:
    frame_uid: str
    frame_record_digest: str
    checkpoint_identity_digest: str
    relative_path: str
    force_shape: tuple[int, int]
    force_dtype: str
    stress_present: bool
    file_sha256: str
    energy_digest: str
    forces_content_digest: str
    stress_content_digest: str | None
    storage_kind: str = "npz"
    shard_index: int | None = None
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in (
            "frame_uid",
            "frame_record_digest",
            "checkpoint_identity_digest",
            "file_sha256",
            "energy_digest",
            "forces_content_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.stress_content_digest is not None:
            object.__setattr__(self, "stress_content_digest", validate_digest(self.stress_content_digest, name="stress_content_digest"))
        if len(self.force_shape) != 2 or self.force_shape[1] != 3 or self.force_shape[0] < 1:
            raise TrainingDataInputError("Prediction force_shape must be (n_atoms, 3).")
        path = Path(self.relative_path)
        if not self.relative_path.strip() or path.is_absolute() or ".." in path.parts:
            raise TrainingDataInputError("Prediction sidecar path must be non-empty, safe, and relative.")
        if np.dtype(self.force_dtype).kind != "f":
            raise TrainingDataInputError("Prediction force dtype must be floating point.")
        if self.stress_present != (self.stress_content_digest is not None):
            raise TrainingDataInputError("Prediction stress presence/digest mismatch.")
        storage_kind = str(self.storage_kind)
        if storage_kind not in {"npz", "npz_shard"}:
            raise TrainingDataInputError("Unsupported prediction storage kind.")
        shard_index = None if self.shard_index is None else int(self.shard_index)
        if storage_kind == "npz_shard":
            if shard_index is None or shard_index < 0:
                raise TrainingDataInputError("Prediction shard records require a non-negative shard index.")
        elif shard_index is not None:
            raise TrainingDataInputError("Standalone prediction records cannot define shard_index.")
        object.__setattr__(self, "storage_kind", storage_kind)
        object.__setattr__(self, "shard_index", shard_index)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ATOMIC_MODEL_PREDICTION_FILE_SCHEMA,
            "frame_uid": self.frame_uid,
            "frame_record_digest": self.frame_record_digest,
            "checkpoint_identity_digest": self.checkpoint_identity_digest,
            "relative_path": self.relative_path,
            "force_shape": list(self.force_shape),
            "force_dtype": self.force_dtype,
            "stress_present": self.stress_present,
            "file_sha256": self.file_sha256,
            "energy_digest": self.energy_digest,
            "forces_content_digest": self.forces_content_digest,
            "stress_content_digest": self.stress_content_digest,
            "storage_kind": self.storage_kind,
            "shard_index": self.shard_index,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomicModelPredictionFileRecord":
        schema = payload.get("schema")
        if schema not in {ATOMIC_MODEL_PREDICTION_FILE_SCHEMA, ATOMIC_MODEL_PREDICTION_FILE_LEGACY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported prediction-file record schema.")
        result = cls(
            frame_uid=str(payload["frame_uid"]),
            frame_record_digest=str(payload["frame_record_digest"]),
            checkpoint_identity_digest=str(payload["checkpoint_identity_digest"]),
            relative_path=str(payload["relative_path"]),
            force_shape=tuple(int(v) for v in payload["force_shape"]),
            force_dtype=str(payload["force_dtype"]),
            stress_present=bool(payload["stress_present"]),
            file_sha256=str(payload["file_sha256"]),
            energy_digest=str(payload["energy_digest"]),
            forces_content_digest=str(payload["forces_content_digest"]),
            stress_content_digest=None if payload.get("stress_content_digest") is None else str(payload["stress_content_digest"]),
            storage_kind=str(payload.get("storage_kind", "npz")),
            shard_index=None if payload.get("shard_index") is None else int(payload["shard_index"]),
        )
        supplied = payload.get("content_digest")
        if schema == ATOMIC_MODEL_PREDICTION_FILE_LEGACY_SCHEMA:
            legacy = {
                "schema": ATOMIC_MODEL_PREDICTION_FILE_LEGACY_SCHEMA,
                "frame_uid": result.frame_uid,
                "frame_record_digest": result.frame_record_digest,
                "checkpoint_identity_digest": result.checkpoint_identity_digest,
                "relative_path": result.relative_path,
                "force_shape": list(result.force_shape),
                "force_dtype": result.force_dtype,
                "stress_present": result.stress_present,
                "file_sha256": result.file_sha256,
                "energy_digest": result.energy_digest,
                "forces_content_digest": result.forces_content_digest,
                "stress_content_digest": result.stress_content_digest,
            }
            expected = digest(legacy)
        else:
            expected = result.content_digest
        if supplied not in (None, expected):
            raise TrainingDataSerializationError("Prediction-file record digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class AtomicModelPredictionManifest:
    dataset_id: str
    frame_catalog_digest: str
    data5_bundle_digest: str
    checkpoint_identity: ModelCheckpointIdentity
    records: tuple[AtomicModelPredictionFileRecord, ...]
    excluded_frame_uids: tuple[str, ...]
    _by_frame_uid: Mapping[str, AtomicModelPredictionFileRecord] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("frame_catalog_digest", "data5_bundle_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        records = tuple(self.records)
        uids = tuple(item.frame_uid for item in records)
        if any(left >= right for left, right in zip(uids, uids[1:])):
            records = tuple(sorted(records, key=lambda item: item.frame_uid))
            uids = tuple(item.frame_uid for item in records)
        if any(left == right for left, right in zip(uids, uids[1:])):
            raise TrainingDataInputError("Prediction manifest contains duplicate frames.")
        if any(item.checkpoint_identity_digest != self.checkpoint_identity.content_digest for item in records):
            raise TrainingDataInputError("Prediction manifest checkpoint lineage mismatch.")
        excluded = tuple(sorted(set(validate_digest(v, name="excluded_frame_uid") for v in self.excluded_frame_uids)))
        if set(item.frame_uid for item in records) & set(excluded):
            raise TrainingDataInputError("Prediction manifest records overlap excluded frames.")
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "excluded_frame_uids", excluded)
        object.__setattr__(self, "_by_frame_uid", {item.frame_uid: item for item in records})

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ATOMIC_MODEL_PREDICTION_MANIFEST_SCHEMA,
            "dataset_id": self.dataset_id,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "checkpoint_identity": self.checkpoint_identity.to_dict(),
            "records": [item.to_dict() for item in self.records],
            "excluded_frame_uids": list(self.excluded_frame_uids),
        }

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": ATOMIC_MODEL_PREDICTION_MANIFEST_SCHEMA,
            "dataset_id": self.dataset_id,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "checkpoint_identity_digest": self.checkpoint_identity.content_digest,
            "record_digests": [item.content_digest for item in self.records],
            "excluded_frame_uids": list(self.excluded_frame_uids),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(self._digest_payload())
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    def for_frame(self, frame_uid: str) -> AtomicModelPredictionFileRecord:
        wanted = validate_digest(frame_uid, name="frame_uid")
        try:
            return self._by_frame_uid[wanted]
        except KeyError:
            raise KeyError(frame_uid) from None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomicModelPredictionManifest":
        if payload.get("schema") != ATOMIC_MODEL_PREDICTION_MANIFEST_SCHEMA:
            raise TrainingDataSerializationError("Unsupported prediction-manifest schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            data5_bundle_digest=str(payload["data5_bundle_digest"]),
            checkpoint_identity=ModelCheckpointIdentity.from_dict(payload["checkpoint_identity"]),
            records=tuple(AtomicModelPredictionFileRecord.from_dict(item) for item in payload["records"]),
            excluded_frame_uids=tuple(str(v) for v in payload.get("excluded_frame_uids", ())),
        )
        supplied = payload.get("content_digest")
        legacy_digest = digest({key: value for key, value in payload.items() if key != "content_digest"})
        if supplied not in (None, result.content_digest, legacy_digest):
            raise TrainingDataSerializationError("Prediction-manifest digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class Data6ModelSweepFrameRecord:
    frame_uid: str
    descriptor_record: MaceDescriptorFileRecord | None
    prediction_record: AtomicModelPredictionFileRecord | None
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "frame_uid", validate_digest(self.frame_uid, name="frame_uid"))
        if self.descriptor_record is None and self.prediction_record is None:
            raise TrainingDataInputError("Sweep frame record contains no artifact.")
        for record in (self.descriptor_record, self.prediction_record):
            if record is not None and record.frame_uid != self.frame_uid:
                raise TrainingDataInputError("Sweep frame/artifact UID mismatch.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": DATA6_MODEL_SWEEP_FRAME_SCHEMA,
            "frame_uid": self.frame_uid,
            "descriptor_record": None if self.descriptor_record is None else self.descriptor_record.to_dict(),
            "prediction_record": None if self.prediction_record is None else self.prediction_record.to_dict(),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Data6ModelSweepFrameRecord":
        if payload.get("schema") != DATA6_MODEL_SWEEP_FRAME_SCHEMA:
            raise TrainingDataSerializationError("Unsupported sweep-frame record schema.")
        result = cls(
            frame_uid=str(payload["frame_uid"]),
            descriptor_record=None if payload.get("descriptor_record") is None else MaceDescriptorFileRecord.from_dict(payload["descriptor_record"]),
            prediction_record=None if payload.get("prediction_record") is None else AtomicModelPredictionFileRecord.from_dict(payload["prediction_record"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Sweep-frame record digest mismatch.")
        return result


class Data6ModelSweepStatus(str, Enum):
    INCOMPLETE = "incomplete"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Data6ModelSweepCheckpoint:
    plan: Data6ModelSweepPlan
    records: tuple[Data6ModelSweepFrameRecord, ...]
    status: Data6ModelSweepStatus
    failed_frame_uid: str | None = None
    failure_type: str | None = None
    failure_message: str | None = None
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)
    _completed_frame_uids_cache: tuple[str, ...] = field(
        default=(), init=False, repr=False, compare=False
    )
    _pending_frame_uids_cache: tuple[str, ...] = field(
        default=(), init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        records = tuple(self.records)
        uids = tuple(item.frame_uid for item in records)
        if any(left >= right for left, right in zip(uids, uids[1:])):
            records = tuple(sorted(records, key=lambda item: item.frame_uid))
            uids = tuple(item.frame_uid for item in records)
        if any(left == right for left, right in zip(uids, uids[1:])):
            raise TrainingDataInputError("Sweep checkpoint contains duplicate frame records.")
        if not set(item.frame_uid for item in records).issubset(set(self.plan.requested_frame_uids)):
            raise TrainingDataInputError("Sweep checkpoint contains frames outside its plan.")
        object.__setattr__(self, "records", records)
        completed_frame_uids = tuple(item.frame_uid for item in records)
        completed_frame_uid_set = set(completed_frame_uids)
        object.__setattr__(self, "_completed_frame_uids_cache", completed_frame_uids)
        object.__setattr__(
            self,
            "_pending_frame_uids_cache",
            tuple(
                frame_uid
                for frame_uid in self.plan.requested_frame_uids
                if frame_uid not in completed_frame_uid_set
            ),
        )
        object.__setattr__(self, "status", Data6ModelSweepStatus(self.status))
        complete = self._artifacts_complete(records)
        if self.status is Data6ModelSweepStatus.COMPLETE and not complete:
            raise TrainingDataInputError("Complete sweep checkpoint is missing required artifacts.")
        if self.status is Data6ModelSweepStatus.FAILED:
            if self.failed_frame_uid is None or self.failure_type is None or self.failure_message is None:
                raise TrainingDataInputError("Failed sweep checkpoints require failure evidence.")
            object.__setattr__(self, "failed_frame_uid", validate_digest(self.failed_frame_uid, name="failed_frame_uid"))
        elif any(v is not None for v in (self.failed_frame_uid, self.failure_type, self.failure_message)):
            raise TrainingDataInputError("Non-failed sweep checkpoints cannot carry failure evidence.")

    def _artifacts_complete(self, records: Sequence[Data6ModelSweepFrameRecord]) -> bool:
        index = {item.frame_uid: item for item in records}
        descriptor_frames = set(self.plan.descriptor_frame_uids)
        prediction_frames = set(self.plan.prediction_frame_uids)
        for frame_uid in self.plan.requested_frame_uids:
            item = index.get(frame_uid)
            if item is None:
                return False
            if frame_uid in descriptor_frames and item.descriptor_record is None:
                return False
            if frame_uid in prediction_frames and item.prediction_record is None:
                return False
        return True

    @property
    def completed_frame_uids(self) -> tuple[str, ...]:
        return self._completed_frame_uids_cache

    @property
    def pending_frame_uids(self) -> tuple[str, ...]:
        # The completed membership set is constructed once during immutable
        # checkpoint validation.  Repeated status/restart queries are O(1).
        return self._pending_frame_uids_cache

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": DATA6_MODEL_SWEEP_CHECKPOINT_SCHEMA,
            "plan": self.plan.to_dict(),
            "records": [item.to_dict() for item in self.records],
            "status": self.status.value,
            "failed_frame_uid": self.failed_frame_uid,
            "failure_type": self.failure_type,
            "failure_message": self.failure_message,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Data6ModelSweepCheckpoint":
        if payload.get("schema") != DATA6_MODEL_SWEEP_CHECKPOINT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported model-sweep checkpoint schema.")
        result = cls(
            plan=Data6ModelSweepPlan.from_dict(payload["plan"]),
            records=tuple(Data6ModelSweepFrameRecord.from_dict(item) for item in payload["records"]),
            status=Data6ModelSweepStatus(payload["status"]),
            failed_frame_uid=None if payload.get("failed_frame_uid") is None else str(payload["failed_frame_uid"]),
            failure_type=None if payload.get("failure_type") is None else str(payload["failure_type"]),
            failure_message=None if payload.get("failure_message") is None else str(payload["failure_message"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Model-sweep checkpoint digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class Data6RuntimeBatchCap:
    """Durable execution-only cap learned from a production CUDA OOM."""

    identity_digest: str
    safe_batch_size: int
    rejected_batch_size: int
    oom_count: int = 1
    reason: str = "cuda_oom_backoff"

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity_digest", validate_digest(self.identity_digest, name="identity_digest"))
        if int(self.safe_batch_size) <= 0 or int(self.rejected_batch_size) <= 0:
            raise TrainingDataInputError("Runtime batch-cap sizes must be positive.")
        if int(self.safe_batch_size) >= int(self.rejected_batch_size):
            raise TrainingDataInputError("Runtime safe batch size must be smaller than the rejected OOM batch.")
        if int(self.oom_count) <= 0 or not str(self.reason).strip():
            raise TrainingDataInputError("Runtime batch-cap evidence is incomplete.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": DATA6_RUNTIME_BATCH_CAP_SCHEMA,
            "identity_digest": self.identity_digest,
            "safe_batch_size": int(self.safe_batch_size),
            "rejected_batch_size": int(self.rejected_batch_size),
            "oom_count": int(self.oom_count),
            "reason": self.reason,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Data6RuntimeBatchCap":
        if payload.get("schema") != DATA6_RUNTIME_BATCH_CAP_SCHEMA:
            raise TrainingDataSerializationError("Unsupported DATA6 runtime batch-cap schema.")
        result = cls(
            identity_digest=str(payload["identity_digest"]),
            safe_batch_size=int(payload["safe_batch_size"]),
            rejected_batch_size=int(payload["rejected_batch_size"]),
            oom_count=int(payload.get("oom_count", 1)),
            reason=str(payload.get("reason", "cuda_oom_backoff")),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("DATA6 runtime batch-cap digest mismatch.")
        return result


def _runtime_batch_cap_identity(
    provider: AtomicModelProvider,
    descriptor_policy: MaceDescriptorPolicy,
    execution_policy: "Data6ModelSweepExecutionPolicy",
) -> str:
    return digest({
        "schema": "mdstats.data6-runtime-batch-cap-identity.v1",
        "checkpoint_identity_digest": provider.checkpoint_identity.content_digest,
        "descriptor_policy_digest": descriptor_policy.policy_digest,
        "device": provider.checkpoint_identity.device,
        "dtype": provider.checkpoint_identity.default_dtype,
        "workload_mode": execution_policy.workload_mode,
        "capacity_calibration_digest": execution_policy.capacity_calibration_digest,
    })


@dataclass(frozen=True, slots=True)
class Data6ModelSweepExecutionPolicy:
    """Runtime policy for restartable DATA6 inference.

    ``checkpoint_interval`` is the number of completed frame records between
    durable append-journal flushes.  Full checkpoint compaction occurs only at
    normal return or failure, so steady-state work remains proportional to the
    number of newly processed frames.
    """

    checkpoint_interval: int = 128
    max_new_frames: int | None = None
    verify_existing: bool = True
    recompute_invalid: bool = True
    batch_size: int = 1
    adaptive_batching: bool = True
    artifact_shard_size: int = 1
    workload_mode: str = "combined_evaluate"
    capacity_calibration_digest: str | None = None
    pipeline_enabled: bool = True
    persistence_queue_depth: int = 1
    persist_oom_batch_cap: bool = True

    def __post_init__(self) -> None:
        if self.checkpoint_interval < 1:
            raise TrainingDataInputError("Sweep checkpoint_interval must be positive.")
        if self.max_new_frames is not None and self.max_new_frames < 1:
            raise TrainingDataInputError("Sweep max_new_frames must be positive when present.")
        if self.batch_size < 1:
            raise TrainingDataInputError("Sweep batch_size must be positive.")
        if self.artifact_shard_size < 1:
            raise TrainingDataInputError("Sweep artifact_shard_size must be positive.")
        if self.workload_mode not in {"descriptor_only", "prediction_only", "combined_evaluate"}:
            raise TrainingDataInputError("Unsupported DATA6 execution workload_mode.")
        if self.capacity_calibration_digest is not None:
            object.__setattr__(
                self, "capacity_calibration_digest",
                validate_digest(self.capacity_calibration_digest, name="capacity_calibration_digest"),
            )
        if self.persistence_queue_depth < 1 or self.persistence_queue_depth > 2:
            raise TrainingDataInputError("Sweep persistence_queue_depth must be one or two.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": DATA6_MODEL_SWEEP_EXECUTION_POLICY_SCHEMA,
            "checkpoint_interval": self.checkpoint_interval,
            "max_new_frames": self.max_new_frames,
            "verify_existing": self.verify_existing,
            "recompute_invalid": self.recompute_invalid,
            "batch_size": self.batch_size,
            "adaptive_batching": self.adaptive_batching,
            "artifact_shard_size": self.artifact_shard_size,
            "workload_mode": self.workload_mode,
            "capacity_calibration_digest": self.capacity_calibration_digest,
            "pipeline_enabled": self.pipeline_enabled,
            "persistence_queue_depth": self.persistence_queue_depth,
            "persist_oom_batch_cap": self.persist_oom_batch_cap,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Data6ModelSweepExecutionPolicy":
        schema = payload.get("schema")
        if schema not in {
            DATA6_MODEL_SWEEP_EXECUTION_POLICY_SCHEMA,
            DATA6_MODEL_SWEEP_EXECUTION_POLICY_V3_SCHEMA,
            DATA6_MODEL_SWEEP_EXECUTION_POLICY_V2_SCHEMA,
            DATA6_MODEL_SWEEP_EXECUTION_POLICY_LEGACY_SCHEMA,
        }:
            raise TrainingDataSerializationError("Unsupported sweep execution-policy schema.")
        result = cls(
            checkpoint_interval=int(payload["checkpoint_interval"]),
            max_new_frames=None if payload.get("max_new_frames") is None else int(payload["max_new_frames"]),
            verify_existing=bool(payload["verify_existing"]),
            recompute_invalid=bool(payload["recompute_invalid"]),
            batch_size=int(payload.get("batch_size", 1)),
            adaptive_batching=bool(payload.get("adaptive_batching", True)),
            artifact_shard_size=int(payload.get("artifact_shard_size", 1)),
            workload_mode=str(payload.get("workload_mode", "combined_evaluate")),
            capacity_calibration_digest=None if payload.get("capacity_calibration_digest") is None else str(payload["capacity_calibration_digest"]),
            pipeline_enabled=bool(payload.get("pipeline_enabled", False if schema != DATA6_MODEL_SWEEP_EXECUTION_POLICY_SCHEMA else True)),
            persistence_queue_depth=int(payload.get("persistence_queue_depth", 1)),
            persist_oom_batch_cap=bool(payload.get("persist_oom_batch_cap", True)),
        )
        expected = result.content_digest
        if schema in {DATA6_MODEL_SWEEP_EXECUTION_POLICY_V3_SCHEMA, DATA6_MODEL_SWEEP_EXECUTION_POLICY_V2_SCHEMA, DATA6_MODEL_SWEEP_EXECUTION_POLICY_LEGACY_SCHEMA}:
            legacy = result._payload()
            legacy["schema"] = schema
            for name in ("workload_mode", "capacity_calibration_digest", "pipeline_enabled", "persistence_queue_depth", "persist_oom_batch_cap"):
                legacy.pop(name, None)
            if schema in {DATA6_MODEL_SWEEP_EXECUTION_POLICY_V2_SCHEMA, DATA6_MODEL_SWEEP_EXECUTION_POLICY_LEGACY_SCHEMA}:
                legacy.pop("artifact_shard_size", None)
            if schema == DATA6_MODEL_SWEEP_EXECUTION_POLICY_LEGACY_SCHEMA:
                legacy.pop("batch_size", None)
                legacy.pop("adaptive_batching", None)
            expected = digest(legacy)
        if payload.get("content_digest") not in (None, expected):
            raise TrainingDataSerializationError("Sweep execution-policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class Data6ModelSweepArtifacts:
    root_directory: str
    checkpoint: Data6ModelSweepCheckpoint
    descriptor_manifest: MaceDescriptorManifest | None
    prediction_manifest: AtomicModelPredictionManifest | None
    runtime_batch_cap: Data6RuntimeBatchCap | None = None

    @property
    def complete(self) -> bool:
        return self.checkpoint.status is Data6ModelSweepStatus.COMPLETE

    def prediction_cache(self) -> "PersistentAtomicModelPredictionCache":
        if self.prediction_manifest is None:
            raise TrainingDataInputError("Incomplete model sweep has no prediction manifest.")
        return PersistentAtomicModelPredictionCache(self.prediction_manifest, self.root_directory)


def build_data6_model_sweep_plan(
    frame_catalog: Any,
    data5_bundle: Any,
    data6_policy: Any,
    checkpoint_identity: ModelCheckpointIdentity,
    *,
    descriptor_policy: MaceDescriptorPolicy | None = None,
    descriptor_signature: MaceDescriptorSignature | None = None,
) -> Data6ModelSweepPlan:
    if data5_bundle.frame_catalog_digest != frame_catalog.content_digest:
        raise TrainingDataInputError("DATA6 model-sweep DATA5/frame lineage mismatch.")
    active_descriptor = MaceDescriptorPolicy() if descriptor_policy is None else descriptor_policy
    descriptor_frames = (
        _frames_for_roles(data5_bundle, data6_policy.descriptor_roles)
        if bool(data6_policy.build_mace_descriptors)
        else ()
    )
    prediction_frames: set[str] = set()
    if bool(data6_policy.build_training_difficulty):
        for domain in build_training_difficulty_domains(data5_bundle):
            prediction_frames.update(domain.frame_uids)
    if bool(data6_policy.build_blinded_predictions):
        for domain in build_blinded_prediction_domains(data5_bundle):
            if domain.materialization_status is PredictionMaterializationStatus.MATERIALIZED_BLINDED:
                prediction_frames.update(domain.frame_uids)
    requested = tuple(sorted(set(descriptor_frames) | prediction_frames))
    all_frames = set(_all_data5_frames(data5_bundle))
    if not set(requested).issubset(all_frames):
        raise TrainingDataInputError("DATA6 model sweep requested frames outside DATA5 unit catalog.")
    return Data6ModelSweepPlan(
        dataset_id=frame_catalog.dataset_id,
        frame_catalog_digest=frame_catalog.content_digest,
        data5_bundle_digest=data5_bundle.content_digest,
        data6_policy_digest=data6_policy.policy_digest,
        checkpoint_identity=checkpoint_identity,
        descriptor_policy=active_descriptor,
        descriptor_frame_uids=descriptor_frames,
        prediction_frame_uids=tuple(sorted(prediction_frames)),
        requested_frame_uids=requested,
        sealed_or_excluded_frame_uids=tuple(sorted(all_frames - set(requested))),
        descriptor_signature=descriptor_signature,
    )


def _descriptor_valid(record: MaceDescriptorFileRecord, root: Path) -> bool:
    try:
        read_mace_descriptor_record_array(record, root)
        return True
    except (Exception, TrainingDataSerializationError):
        return False


def _prediction_arrays_for_record(
    record: AtomicModelPredictionFileRecord, root_directory: str | Path
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    path = Path(root_directory) / record.relative_path
    if not path.is_file():
        raise TrainingDataSerializationError("Prediction sidecar is missing.")
    try:
        if record.storage_kind == "npz_shard":
            payload = _load_prediction_shard(
                path,
                record.file_sha256,
                (
                    "energies",
                    "force_offsets",
                    "force_values",
                    "stress_present",
                    "stresses",
                ),
            )
            index = int(record.shard_index)
            energies = np.asarray(payload["energies"], dtype=np.float64)
            offsets = np.asarray(payload["force_offsets"], dtype=np.int64)
            all_forces = np.asarray(payload["force_values"])
            stress_present = np.asarray(payload["stress_present"], dtype=np.bool_)
            stresses = np.asarray(payload["stresses"], dtype=np.float64)
            start = int(offsets[index])
            stop = int(offsets[index + 1])
            energy = np.asarray(energies[index], dtype=np.float64)
            forces = all_forces[start:stop]
            stress = (
                np.asarray(stresses[index])
                if bool(stress_present[index])
                else np.empty((0,), dtype=np.float64)
            )
        else:
            raw = _read_verified_file(path, record.file_sha256)
            with np.load(io.BytesIO(raw), allow_pickle=False) as payload:
                energy = np.asarray(payload["energy"], dtype=np.float64)
                forces = np.asarray(payload["forces"])
                stress = np.asarray(payload["stress"])
    except Exception as exc:
        raise TrainingDataSerializationError("Cannot read prediction sidecar.") from exc
    return energy, forces, stress


def read_atomic_model_prediction(
    manifest: AtomicModelPredictionManifest,
    root_directory: str | Path,
    frame_uid: str,
) -> AtomicModelPrediction:
    record = manifest.for_frame(frame_uid)
    energy, forces, stress = _prediction_arrays_for_record(record, root_directory)
    if energy.shape != () or not np.isfinite(float(energy)) or _array_digest(energy) != record.energy_digest:
        raise TrainingDataSerializationError("Prediction energy sidecar content mismatch.")
    if forces.shape != record.force_shape or forces.dtype.name != record.force_dtype or np.any(~np.isfinite(forces)):
        raise TrainingDataSerializationError("Prediction forces shape, dtype, or finiteness mismatch.")
    if _array_digest(forces) != record.forces_content_digest:
        raise TrainingDataSerializationError("Prediction forces content mismatch.")
    if record.stress_present:
        if stress.shape != (3, 3) or np.any(~np.isfinite(stress)) or _array_digest(stress) != record.stress_content_digest:
            raise TrainingDataSerializationError("Prediction stress content mismatch.")
        stress_value: np.ndarray | None = stress
    else:
        if stress.size != 0:
            raise TrainingDataSerializationError("Prediction sidecar unexpectedly contains stress.")
        stress_value = None
    return AtomicModelPrediction(
        energy_ev=float(energy),
        forces_ev_per_angstrom=forces,
        stress_ev_per_angstrom3=stress_value,
    )


def read_atomic_model_prediction_energy(
    manifest: AtomicModelPredictionManifest,
    root_directory: str | Path,
    frame_uid: str,
) -> float:
    """Read and authenticate only the scalar energy needed by residual-E0 fits.

    For v2 shards this deliberately loads only the ``energies`` member.  The
    previous implementation reused the full prediction reader and therefore
    decompressed every force and stress array for a scalar residual-E0 lookup.
    """

    record = manifest.for_frame(frame_uid)
    path = Path(root_directory) / record.relative_path
    if not path.is_file():
        raise TrainingDataSerializationError("Prediction sidecar is missing.")
    try:
        if record.storage_kind == "npz_shard":
            payload = _load_prediction_shard(
                path, record.file_sha256, ("energies",)
            )
            energy = np.asarray(
                payload["energies"][int(record.shard_index)], dtype=np.float64
            )
        else:
            raw = _read_verified_file(path, record.file_sha256)
            with np.load(io.BytesIO(raw), allow_pickle=False) as payload:
                energy = np.asarray(payload["energy"], dtype=np.float64)
    except Exception as exc:
        if isinstance(exc, TrainingDataSerializationError):
            raise
        raise TrainingDataSerializationError(
            "Cannot read prediction energy sidecar."
        ) from exc
    if (
        energy.shape != ()
        or not np.isfinite(float(energy))
        or _array_digest(energy) != record.energy_digest
    ):
        raise TrainingDataSerializationError(
            "Prediction energy sidecar content mismatch."
        )
    return float(energy)


def _prediction_valid(record: AtomicModelPredictionFileRecord, root: Path, manifest: AtomicModelPredictionManifest) -> bool:
    try:
        read_atomic_model_prediction(manifest, root, record.frame_uid)
        return True
    except (TrainingDataSerializationError, KeyError):
        return False


class PersistentAtomicModelPredictionCache(MutableMapping[str, AtomicModelPrediction]):
    """Mutable mapping that lazily verifies and loads prediction sidecars."""

    def __init__(self, manifest: AtomicModelPredictionManifest, root_directory: str | Path):
        self.manifest = manifest
        self.root = Path(root_directory)
        self._records = {item.frame_uid: item for item in manifest.records}
        self._memory: dict[str, AtomicModelPrediction] = {}
        self._energy_memory: dict[str, float] = {}

    def __getitem__(self, key: str) -> AtomicModelPrediction:
        if key not in self._memory:
            if key not in self._records:
                raise KeyError(key)
            self._memory[key] = read_atomic_model_prediction(self.manifest, self.root, key)
            self._energy_memory[key] = self._memory[key].energy_ev
        return self._memory[key]

    def __setitem__(self, key: str, value: AtomicModelPrediction) -> None:
        self._memory[key] = value
        self._energy_memory[key] = value.energy_ev

    def __delitem__(self, key: str) -> None:
        # Release force/stress arrays after compact summaries are built while
        # retaining the scalar energy needed by DATA7 residual-E0 fits.
        self._memory.pop(key, None)

    def energy_for_frame(self, key: str) -> float:
        try:
            return self._energy_memory[key]
        except KeyError:
            if key not in self._records:
                raise KeyError(key) from None
            value = read_atomic_model_prediction_energy(self.manifest, self.root, key)
            self._energy_memory[key] = value
            return value

    def __iter__(self) -> Iterator[str]:
        return iter(self._records)

    def __len__(self) -> int:
        return len(self._records)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and (key in self._records or key in self._memory)


def _manifest_from_records(
    plan: Data6ModelSweepPlan,
    records: Sequence[Data6ModelSweepFrameRecord],
) -> tuple[MaceDescriptorManifest | None, AtomicModelPredictionManifest | None]:
    indexed = {item.frame_uid: item for item in records}
    descriptors = tuple(indexed[uid].descriptor_record for uid in plan.descriptor_frame_uids)
    predictions = tuple(indexed[uid].prediction_record for uid in plan.prediction_frame_uids)
    descriptor_manifest = None
    if descriptors:
        if any(item is None for item in descriptors):
            raise TrainingDataInputError("Cannot build descriptor manifest from incomplete sweep.")
        descriptor_manifest = MaceDescriptorManifest(
            dataset_id=plan.dataset_id,
            frame_catalog_digest=plan.frame_catalog_digest,
            data5_bundle_digest=plan.data5_bundle_digest,
            checkpoint_identity=plan.checkpoint_identity,
            policy=plan.descriptor_policy,
            records=tuple(item for item in descriptors if item is not None),
            excluded_frame_uids=plan.sealed_or_excluded_frame_uids,
            signature=plan.descriptor_signature,
        )
    prediction_manifest = None
    if predictions:
        if any(item is None for item in predictions):
            raise TrainingDataInputError("Cannot build prediction manifest from incomplete sweep.")
        prediction_manifest = AtomicModelPredictionManifest(
            dataset_id=plan.dataset_id,
            frame_catalog_digest=plan.frame_catalog_digest,
            data5_bundle_digest=plan.data5_bundle_digest,
            checkpoint_identity=plan.checkpoint_identity,
            records=tuple(item for item in predictions if item is not None),
            excluded_frame_uids=plan.sealed_or_excluded_frame_uids,
        )
    return descriptor_manifest, prediction_manifest


def _write_descriptor_shard(
    root: Path,
    *,
    entries: Sequence[tuple[str, str, np.ndarray, np.ndarray]],
    checkpoint_identity: ModelCheckpointIdentity,
    descriptor_policy: MaceDescriptorPolicy,
) -> dict[str, MaceDescriptorFileRecord]:
    if not entries:
        return {}
    frame_uids = tuple(item[0] for item in entries)
    descriptors = [np.ascontiguousarray(item[3]) for item in entries]
    dimension = int(descriptors[0].shape[1])
    dtype = descriptors[0].dtype
    if any(array.ndim != 2 or array.shape[1] != dimension for array in descriptors):
        raise TrainingDataInputError("Descriptor shard arrays have inconsistent dimensions.")
    if any(array.dtype != dtype for array in descriptors):
        descriptors = [np.ascontiguousarray(array, dtype=dtype) for array in descriptors]
    offsets = np.zeros(len(descriptors) + 1, dtype=np.int64)
    offsets[1:] = np.cumsum([array.shape[0] for array in descriptors], dtype=np.int64)
    values = np.concatenate(descriptors, axis=0)

    atomic_numbers = [np.asarray(item[2], dtype=np.int32).reshape(-1) for item in entries]
    if any(numbers.size != descriptor.shape[0] for numbers, descriptor in zip(atomic_numbers, descriptors, strict=True)):
        raise TrainingDataInputError("Descriptor shard atom identities are misaligned.")
    species = np.asarray(
        sorted({int(value) for numbers in atomic_numbers for value in numbers}),
        dtype=np.int32,
    )
    global_mean = np.stack([np.mean(array, axis=0) for array in descriptors])
    global_std = np.stack([np.std(array, axis=0) for array in descriptors])
    species_present = np.zeros((len(entries), len(species)), dtype=np.bool_)
    species_mean = np.zeros((len(entries), len(species), dimension), dtype=dtype)
    for frame_index, (numbers, descriptor) in enumerate(zip(atomic_numbers, descriptors, strict=True)):
        for species_index, atomic_number in enumerate(species):
            mask = numbers == int(atomic_number)
            if np.any(mask):
                species_present[frame_index, species_index] = True
                species_mean[frame_index, species_index] = np.mean(descriptor[mask], axis=0)

    token = _artifact_shard_token(frame_uids)
    relative = Path("descriptor-shards") / f"descriptor-{token}.npz"
    file_sha256 = _atomic_npz(
        root / relative,
        descriptor_values=values,
        descriptor_offsets=offsets,
        summary_global_mean=global_mean,
        summary_global_std=global_std,
        summary_species_atomic_numbers=species,
        summary_species_present=species_present,
        summary_species_mean=species_mean,
    )
    result: dict[str, MaceDescriptorFileRecord] = {}
    for index, ((frame_uid, frame_digest, _numbers, _descriptor), array) in enumerate(
        zip(entries, descriptors, strict=True)
    ):
        result[frame_uid] = MaceDescriptorFileRecord(
            frame_uid=frame_uid,
            frame_record_digest=frame_digest,
            checkpoint_identity_digest=checkpoint_identity.content_digest,
            descriptor_policy_digest=descriptor_policy.policy_digest,
            relative_path=relative.as_posix(),
            shape=array.shape,
            dtype=array.dtype.name,
            file_sha256=file_sha256,
            array_content_digest=_array_digest(array),
            storage_kind="npz_shard",
            shard_index=index,
        )
    return result


def _write_prediction_shard(
    root: Path,
    *,
    entries: Sequence[tuple[str, str, AtomicModelPrediction]],
    checkpoint_identity: ModelCheckpointIdentity,
) -> dict[str, AtomicModelPredictionFileRecord]:
    if not entries:
        return {}
    frame_uids = tuple(item[0] for item in entries)
    predictions = [item[2] for item in entries]
    energies = np.asarray([item.energy_ev for item in predictions], dtype=np.float64)
    force_arrays = [np.ascontiguousarray(item.forces_ev_per_angstrom) for item in predictions]
    force_dtype = np.result_type(*(array.dtype for array in force_arrays))
    force_arrays = [np.ascontiguousarray(array, dtype=force_dtype) for array in force_arrays]
    force_offsets = np.zeros(len(force_arrays) + 1, dtype=np.int64)
    force_offsets[1:] = np.cumsum([array.shape[0] for array in force_arrays], dtype=np.int64)
    forces = np.concatenate(force_arrays, axis=0)
    stress_present = np.asarray(
        [item.stress_ev_per_angstrom3 is not None for item in predictions],
        dtype=np.bool_,
    )
    stresses = np.zeros((len(predictions), 3, 3), dtype=np.float64)
    for index, prediction in enumerate(predictions):
        if prediction.stress_ev_per_angstrom3 is not None:
            stresses[index] = np.asarray(
                prediction.stress_ev_per_angstrom3, dtype=np.float64
            )
    token = _artifact_shard_token(frame_uids)
    relative = Path("prediction-shards") / f"prediction-{token}.npz"
    file_sha256 = _atomic_npz(
        root / relative,
        energies=energies,
        force_values=forces,
        force_offsets=force_offsets,
        stress_present=stress_present,
        stresses=stresses,
    )
    result: dict[str, AtomicModelPredictionFileRecord] = {}
    for index, ((frame_uid, frame_digest, prediction), force_array) in enumerate(
        zip(entries, force_arrays, strict=True)
    ):
        energy = np.asarray(prediction.energy_ev, dtype=np.float64)
        stress = (
            None
            if prediction.stress_ev_per_angstrom3 is None
            else np.ascontiguousarray(prediction.stress_ev_per_angstrom3)
        )
        result[frame_uid] = AtomicModelPredictionFileRecord(
            frame_uid=frame_uid,
            frame_record_digest=frame_digest,
            checkpoint_identity_digest=checkpoint_identity.content_digest,
            relative_path=relative.as_posix(),
            force_shape=force_array.shape,
            force_dtype=force_array.dtype.name,
            stress_present=stress is not None,
            file_sha256=file_sha256,
            energy_digest=_array_digest(energy),
            forces_content_digest=_array_digest(force_array),
            stress_content_digest=None if stress is None else _array_digest(stress),
            storage_kind="npz_shard",
            shard_index=index,
        )
    return result


def _write_prediction(
    root: Path,
    *,
    frame_uid: str,
    frame_record_digest: str,
    checkpoint_identity: ModelCheckpointIdentity,
    prediction: AtomicModelPrediction,
) -> AtomicModelPredictionFileRecord:
    """Legacy standalone writer retained for compatibility tests and callers."""

    forces = np.ascontiguousarray(prediction.forces_ev_per_angstrom)
    energy = np.asarray(prediction.energy_ev, dtype=np.float64)
    stress = (
        np.empty((0,), dtype=np.float64)
        if prediction.stress_ev_per_angstrom3 is None
        else np.ascontiguousarray(prediction.stress_ev_per_angstrom3)
    )
    relative = Path("predictions") / f"{frame_uid}.npz"
    path = root / relative
    file_sha256 = _atomic_npz(path, energy=energy, forces=forces, stress=stress)
    return AtomicModelPredictionFileRecord(
        frame_uid=frame_uid,
        frame_record_digest=frame_record_digest,
        checkpoint_identity_digest=checkpoint_identity.content_digest,
        relative_path=relative.as_posix(),
        force_shape=forces.shape,
        force_dtype=forces.dtype.name,
        stress_present=prediction.stress_ev_per_angstrom3 is not None,
        file_sha256=file_sha256,
        energy_digest=_array_digest(energy),
        forces_content_digest=_array_digest(forces),
        stress_content_digest=None if stress.size == 0 else _array_digest(stress),
    )


def run_restartable_data6_model_sweep(
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    data5_bundle: Any,
    data6_policy: Any,
    provider: AtomicModelProvider,
    output_directory: str | Path,
    *,
    descriptor_policy: MaceDescriptorPolicy | None = None,
    execution_policy: Data6ModelSweepExecutionPolicy | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
    phase_callback: Callable[[str], None] | None = None,
) -> Data6ModelSweepArtifacts:
    """Compute the DATA5-authorized model sweep with append-only recovery.

    Per-frame artifacts and one compact journal event are written exactly once.
    The complete checkpoint JSON is compacted only on return or failure, avoiding
    the previous repeated rewrite of every earlier record after every frame.
    """

    active_execution = Data6ModelSweepExecutionPolicy() if execution_policy is None else execution_policy
    active_descriptor_policy = MaceDescriptorPolicy() if descriptor_policy is None else descriptor_policy
    descriptor_signature = None
    if hasattr(provider, "descriptor_signature"):
        native_probe = getattr(provider, "_native_batch_supported", None)
        if native_probe is None or bool(native_probe()):
            descriptor_signature = provider.descriptor_signature(active_descriptor_policy)
    plan = build_data6_model_sweep_plan(
        frame_catalog,
        data5_bundle,
        data6_policy,
        provider.checkpoint_identity,
        descriptor_policy=active_descriptor_policy,
        descriptor_signature=descriptor_signature,
    )
    descriptor_frame_uids = frozenset(plan.descriptor_frame_uids)
    prediction_frame_uids = frozenset(plan.prediction_frame_uids)
    supported_atomic_numbers = frozenset(provider.checkpoint_identity.supported_atomic_numbers)
    atomic_numbers_by_run = {
        str(run_id): frozenset(int(value) for value in frame_data.atomic_numbers)
        for run_id, frame_data in frame_data_by_run.items()
    }

    root = Path(output_directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    checkpoint_path = root / "data6_model_sweep_checkpoint.json"
    journal_path = root / "data6_model_sweep_records.jsonl"

    if phase_callback is not None:
        phase_callback("restoring the compact checkpoint and append-only recovery journal")
    checkpoint_records: dict[str, Data6ModelSweepFrameRecord] = {}
    if checkpoint_path.is_file():
        try:
            existing = Data6ModelSweepCheckpoint.from_dict(
                json.loads(checkpoint_path.read_text(encoding="utf-8"))
            )
        except Exception as exc:
            raise TrainingDataSerializationError("Cannot restore DATA6 model-sweep checkpoint.") from exc
        if existing.plan.content_digest != plan.content_digest:
            if not _lineage_only_model_sweep_change(existing.plan, plan):
                raise TrainingDataInputError(
                    "Existing DATA6 model-sweep checkpoint belongs to a different plan (the inference request changed)."
                )
            previous_journal_records, previous_journal_touched = (
                _load_model_sweep_journal(journal_path, existing.plan)
            )
            reusable_records = {item.frame_uid: item for item in existing.records}
            for frame_uid in previous_journal_touched:
                if frame_uid in previous_journal_records:
                    reusable_records[frame_uid] = previous_journal_records[frame_uid]
                else:
                    reusable_records.pop(frame_uid, None)
            if not set(reusable_records).issubset(set(plan.requested_frame_uids)):
                raise TrainingDataInputError(
                    "Existing DATA6 model-sweep checkpoint contains frames outside the rebuilt plan."
                )
            if not _model_sweep_records_match_frame_catalog(
                reusable_records, frame_catalog
            ):
                raise TrainingDataInputError(
                    "Existing DATA6 model-sweep sidecars do not match the rebuilt frame records; "
                    "refusing lineage-only reuse."
                )
            migrated = Data6ModelSweepCheckpoint(
                plan=plan,
                records=_ordered_records(plan, reusable_records),
                status=Data6ModelSweepStatus.INCOMPLETE,
            )
            _atomic_json(checkpoint_path, migrated.to_dict())
            _rewrite_model_sweep_journal(journal_path, plan, reusable_records)
            if phase_callback is not None:
                phase_callback(
                    "rebound verified descriptor/prediction sidecars to rebuilt DATA3/DATA5 lineage"
                )
            checkpoint_records = dict(reusable_records)
        else:
            checkpoint_records = {item.frame_uid: item for item in existing.records}

    journal_records, journal_touched = _load_model_sweep_journal(journal_path, plan)
    existing_records = dict(checkpoint_records)
    for frame_uid in journal_touched:
        if frame_uid in journal_records:
            existing_records[frame_uid] = journal_records[frame_uid]
        else:
            existing_records.pop(frame_uid, None)
    if not journal_path.is_file():
        _initialize_model_sweep_journal(journal_path, plan)

    # Migrate legacy monolithic checkpoints into the journal once.  A journal
    # delete event intentionally overrides an older checkpoint record.
    with journal_path.open("a", encoding="utf-8") as journal:
        migrated = False
        for frame_uid, item in checkpoint_records.items():
            if frame_uid not in journal_touched:
                _append_model_sweep_journal_event(journal, record=item)
                migrated = True
        if migrated:
            _flush_model_sweep_journal(journal)

        descriptor_stub = MaceDescriptorManifest(
            dataset_id=plan.dataset_id,
            frame_catalog_digest=plan.frame_catalog_digest,
            data5_bundle_digest=plan.data5_bundle_digest,
            checkpoint_identity=plan.checkpoint_identity,
            policy=plan.descriptor_policy,
            records=tuple(
                item.descriptor_record
                for item in existing_records.values()
                if item.descriptor_record is not None
            ),
            excluded_frame_uids=plan.sealed_or_excluded_frame_uids,
            signature=plan.descriptor_signature,
        )
        prediction_stub = AtomicModelPredictionManifest(
            dataset_id=plan.dataset_id,
            frame_catalog_digest=plan.frame_catalog_digest,
            data5_bundle_digest=plan.data5_bundle_digest,
            checkpoint_identity=plan.checkpoint_identity,
            records=tuple(
                item.prediction_record
                for item in existing_records.values()
                if item.prediction_record is not None
            ),
            excluded_frame_uids=plan.sealed_or_excluded_frame_uids,
        )

        pending_journal_flush = 0
        if active_execution.verify_existing:
            if phase_callback is not None and existing_records:
                phase_callback(
                    f"verifying {len(existing_records)} existing descriptor/prediction sidecars"
                )
            for frame_uid, item in tuple(existing_records.items()):
                required_ok = (
                    (frame_uid not in descriptor_frame_uids or item.descriptor_record is not None)
                    and (frame_uid not in prediction_frame_uids or item.prediction_record is not None)
                )
                descriptor_ok = (
                    item.descriptor_record is None
                    or _descriptor_valid(item.descriptor_record, root)
                )
                prediction_ok = (
                    item.prediction_record is None
                    or _prediction_valid(item.prediction_record, root, prediction_stub)
                )
                if required_ok and descriptor_ok and prediction_ok:
                    continue
                if not active_execution.recompute_invalid:
                    raise TrainingDataSerializationError(
                        f"Invalid existing model-sweep artifact for frame {frame_uid}."
                    )
                del existing_records[frame_uid]
                _append_model_sweep_journal_event(journal, frame_uid=frame_uid)
                pending_journal_flush += 1
        if pending_journal_flush:
            _flush_model_sweep_journal(journal)
            pending_journal_flush = 0

        index = build_frame_array_index(frame_catalog, frame_data_by_run)
        if progress_callback is not None and existing_records:
            progress_callback(
                len(existing_records), len(plan.requested_frame_uids), "restored-checkpoint"
            )
        requested_pending = [
            uid for uid in plan.requested_frame_uids if uid not in existing_records
        ]
        if active_execution.max_new_frames is not None:
            requested_pending = requested_pending[: active_execution.max_new_frames]
        active_batch_size = max(
            1, min(active_execution.batch_size, len(requested_pending) or 1)
        )
        runtime_cap_path = root / "data6_runtime_batch_cap.json"
        runtime_cap_identity = _runtime_batch_cap_identity(
            provider, active_descriptor_policy, active_execution
        )
        runtime_batch_cap: Data6RuntimeBatchCap | None = None
        if runtime_cap_path.is_file():
            restored_cap = Data6RuntimeBatchCap.from_dict(
                json.loads(runtime_cap_path.read_text(encoding="utf-8"))
            )
            if restored_cap.identity_digest == runtime_cap_identity:
                runtime_batch_cap = restored_cap
                active_batch_size = min(active_batch_size, restored_cap.safe_batch_size)
                if phase_callback is not None:
                    phase_callback(
                        f"reusing DATA6 OOM-safe batch cap {restored_cap.safe_batch_size} "
                        f"for matching runtime identity"
                    )
        pending_oom_rejected: int | None = None
        pending_oom_count = 0
        cursor = 0
        artifact_buffer: list[
            tuple[str, Any, Any, int, np.ndarray | None, AtomicModelPrediction | None]
        ] = []

        persistence_executor = None
        pending_persistence: list[Any] = []
        pending_progress_targets: list[tuple[int, str]] = []
        initial_completed_count = len(existing_records)
        producer_executor = None
        prefetch_future = None
        prefetch_start: int | None = None
        prefetch_batch_size: int | None = None
        prepare_method = getattr(provider, "prepare_evaluate_batch", None)
        evaluate_prepared_method = getattr(provider, "evaluate_prepared_batch", None)
        native_probe = getattr(provider, "_native_batch_supported", None)
        prepare_capable = bool(
            callable(prepare_method)
            and callable(evaluate_prepared_method)
            and (native_probe is None or bool(native_probe()))
        )
        if active_execution.pipeline_enabled:
            from concurrent.futures import ThreadPoolExecutor
            persistence_executor = ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="mdstats-data6-persist"
            )
            if prepare_capable:
                producer_executor = ThreadPoolExecutor(
                    max_workers=1, thread_name_prefix="mdstats-data6-graph"
                )

        def build_batch_context(start_index: int, batch_size: int) -> tuple[Any, ...]:
            batch_uids = requested_pending[start_index : start_index + batch_size]
            batch_inputs: list[tuple[str, Any, Any, int]] = []
            for frame_uid in batch_uids:
                try:
                    record, frame_data, local_index = index[frame_uid]
                except KeyError as exc:
                    raise TrainingDataInputError(
                        f"Unknown model-sweep frame UID {frame_uid}."
                    ) from exc
                present = atomic_numbers_by_run[str(record.run_id)]
                if supported_atomic_numbers and not present.issubset(supported_atomic_numbers):
                    raise TrainingDataInputError(
                        "Checkpoint does not declare all model-sweep frame elements."
                    )
                batch_inputs.append((frame_uid, record, frame_data, local_index))
            atoms_by_uid = {
                uid: ase_atoms_for_frame(record, frame_data, local_index)
                for uid, record, frame_data, local_index in batch_inputs
            }
            descriptor_uids = [uid for uid in batch_uids if uid in descriptor_frame_uids]
            prediction_uids = [uid for uid in batch_uids if uid in prediction_frame_uids]
            prepared = None
            if (
                producer_executor is not None
                and callable(prepare_method)
                and descriptor_uids == list(batch_uids)
                and prediction_uids == list(batch_uids)
                and batch_uids
            ):
                prepared = prepare_method([atoms_by_uid[uid] for uid in batch_uids])
            return (batch_uids, batch_inputs, atoms_by_uid, descriptor_uids, prediction_uids, prepared)

        def discard_prefetch() -> None:
            nonlocal prefetch_future, prefetch_start, prefetch_batch_size
            if prefetch_future is not None:
                if not prefetch_future.cancel():
                    try:
                        prefetch_future.result()
                    except Exception:
                        pass
            prefetch_future = None
            prefetch_start = None
            prefetch_batch_size = None

        def write_artifact_chunk(chunk: tuple[Any, ...]) -> tuple[tuple[Any, ...], dict[str, Any], dict[str, Any]]:
            descriptor_entries = [
                (
                    uid,
                    record.content_digest,
                    np.asarray(frame_data.atomic_numbers, dtype=np.int32),
                    descriptor,
                )
                for uid, record, frame_data, _local_index, descriptor, _prediction in chunk
                if descriptor is not None
            ]
            prediction_entries = [
                (uid, record.content_digest, prediction)
                for uid, record, _frame_data, _local_index, _descriptor, prediction in chunk
                if prediction is not None
            ]
            descriptor_records = _write_descriptor_shard(
                root,
                entries=descriptor_entries,
                checkpoint_identity=provider.checkpoint_identity,
                descriptor_policy=plan.descriptor_policy,
            )
            prediction_records = _write_prediction_shard(
                root,
                entries=prediction_entries,
                checkpoint_identity=provider.checkpoint_identity,
            )
            return chunk, descriptor_records, prediction_records

        def commit_artifact_chunk(result: tuple[tuple[Any, ...], dict[str, Any], dict[str, Any]]) -> None:
            nonlocal pending_journal_flush
            chunk, descriptor_records, prediction_records = result
            last_persisted_uid: str | None = None
            for uid, _record, _frame_data, _local_index, _descriptor, _prediction in chunk:
                frame_record = Data6ModelSweepFrameRecord(
                    frame_uid=uid,
                    descriptor_record=descriptor_records.get(uid),
                    prediction_record=prediction_records.get(uid),
                )
                existing_records[uid] = frame_record
                _append_model_sweep_journal_event(journal, record=frame_record)
                pending_journal_flush += 1
                last_persisted_uid = uid
                if pending_journal_flush >= active_execution.checkpoint_interval:
                    _flush_model_sweep_journal(journal)
                    pending_journal_flush = 0

        def drain_one_persistence() -> None:
            if not pending_persistence:
                return
            future = pending_persistence.pop(0)
            commit_artifact_chunk(future.result())

        def emit_ready_progress() -> None:
            if progress_callback is None:
                return
            while pending_progress_targets and len(existing_records) >= pending_progress_targets[0][0]:
                _target_count, target_uid = pending_progress_targets.pop(0)
                progress_callback(
                    len(existing_records),
                    len(plan.requested_frame_uids),
                    target_uid,
                )

        def persist_artifact_buffer(*, force: bool = False) -> None:
            while artifact_buffer and (
                force or len(artifact_buffer) >= active_execution.artifact_shard_size
            ):
                count = min(len(artifact_buffer), active_execution.artifact_shard_size)
                chunk = tuple(artifact_buffer[:count])
                del artifact_buffer[:count]
                if persistence_executor is None:
                    commit_artifact_chunk(write_artifact_chunk(chunk))
                else:
                    while len(pending_persistence) >= active_execution.persistence_queue_depth:
                        drain_one_persistence()
                    pending_persistence.append(
                        persistence_executor.submit(write_artifact_chunk, chunk)
                    )
            if force:
                while pending_persistence:
                    drain_one_persistence()
            emit_ready_progress()

        try:
            while cursor < len(requested_pending):
                if (
                    prefetch_future is not None
                    and prefetch_start == cursor
                    and prefetch_batch_size == active_batch_size
                ):
                    (
                        batch_uids, batch_inputs, atoms_by_uid,
                        descriptor_uids, prediction_uids, prepared_batch,
                    ) = prefetch_future.result()
                    prefetch_future = None
                    prefetch_start = None
                    prefetch_batch_size = None
                else:
                    discard_prefetch()
                    (
                        batch_uids, batch_inputs, atoms_by_uid,
                        descriptor_uids, prediction_uids, prepared_batch,
                    ) = build_batch_context(cursor, active_batch_size)

                next_start = cursor + len(batch_uids)
                if producer_executor is not None and next_start < len(requested_pending):
                    prefetch_start = next_start
                    prefetch_batch_size = active_batch_size
                    prefetch_future = producer_executor.submit(
                        build_batch_context, next_start, active_batch_size
                    )
                try:
                    descriptors_by_uid: dict[str, np.ndarray] = {}
                    predictions_by_uid: dict[str, AtomicModelPrediction] = {}
                    prediction_uid_set = set(prediction_uids)
                    overlap_uids = [
                        uid for uid in descriptor_uids if uid in prediction_uid_set
                    ]
                    combined_method = getattr(provider, "evaluate_batch", None)
                    if (
                        prepared_batch is not None
                        and callable(evaluate_prepared_method)
                        and overlap_uids == list(batch_uids)
                    ):
                        descriptor_values, prediction_values = evaluate_prepared_method(
                            prepared_batch, plan.descriptor_policy
                        )
                        descriptors_by_uid.update(
                            zip(overlap_uids, descriptor_values, strict=True)
                        )
                        predictions_by_uid.update(
                            zip(overlap_uids, prediction_values, strict=True)
                        )
                    elif callable(combined_method) and overlap_uids:
                        descriptor_values, prediction_values = combined_method(
                            [atoms_by_uid[uid] for uid in overlap_uids],
                            plan.descriptor_policy,
                        )
                        descriptors_by_uid.update(
                            zip(overlap_uids, descriptor_values, strict=True)
                        )
                        predictions_by_uid.update(
                            zip(overlap_uids, prediction_values, strict=True)
                        )

                    descriptor_only = [
                        uid for uid in descriptor_uids if uid not in descriptors_by_uid
                    ]
                    if descriptor_only:
                        descriptor_method = getattr(
                            provider, "get_descriptors_batch", None
                        )
                        if callable(descriptor_method) and len(descriptor_only) > 1:
                            descriptor_values = descriptor_method(
                                [atoms_by_uid[uid] for uid in descriptor_only],
                                plan.descriptor_policy,
                            )
                        else:
                            descriptor_values = tuple(
                                provider.get_descriptors(
                                    atoms_by_uid[uid], plan.descriptor_policy
                                )
                                for uid in descriptor_only
                            )
                        descriptors_by_uid.update(
                            zip(descriptor_only, descriptor_values, strict=True)
                        )

                    prediction_only = [
                        uid for uid in prediction_uids if uid not in predictions_by_uid
                    ]
                    if prediction_only:
                        prediction_method = getattr(provider, "predict_batch", None)
                        if callable(prediction_method) and len(prediction_only) > 1:
                            prediction_values = prediction_method(
                                [atoms_by_uid[uid] for uid in prediction_only]
                            )
                        else:
                            prediction_values = tuple(
                                provider.predict(atoms_by_uid[uid])
                                for uid in prediction_only
                            )
                        predictions_by_uid.update(
                            zip(prediction_only, prediction_values, strict=True)
                        )
                except RuntimeError as exc:
                    is_oom = "out of memory" in str(exc).lower()
                    if (
                        is_oom
                        and active_execution.adaptive_batching
                        and active_batch_size > 1
                    ):
                        rejected_batch = int(active_batch_size)
                        active_batch_size = max(1, active_batch_size // 2)
                        pending_oom_rejected = rejected_batch
                        pending_oom_count += 1
                        try:
                            import torch
                            if torch.cuda.is_available():
                                try:
                                    torch.cuda.synchronize()
                                except RuntimeError:
                                    pass
                                gc.collect()
                                torch.cuda.empty_cache()
                                try:
                                    torch.cuda.synchronize()
                                except RuntimeError:
                                    pass
                        except ModuleNotFoundError:
                            gc.collect()
                        discard_prefetch()
                        if phase_callback is not None:
                            phase_callback(
                                f"CUDA OOM backoff: batch {rejected_batch} -> {active_batch_size}; "
                                "retrying without advancing DATA6 scientific order"
                            )
                        continue
                    raise

                for uid, record, frame_data, local_index in batch_inputs:
                    descriptor = (
                        None
                        if uid not in descriptors_by_uid
                        else np.ascontiguousarray(descriptors_by_uid[uid])
                    )
                    prediction = predictions_by_uid.get(uid)
                    artifact_buffer.append(
                        (uid, record, frame_data, local_index, descriptor, prediction)
                    )
                pending_progress_targets.append((
                    initial_completed_count + cursor + len(batch_uids),
                    batch_uids[-1],
                ))
                persist_artifact_buffer()
                if pending_oom_rejected is not None and active_execution.persist_oom_batch_cap:
                    runtime_batch_cap = Data6RuntimeBatchCap(
                        identity_digest=runtime_cap_identity,
                        safe_batch_size=int(active_batch_size),
                        rejected_batch_size=int(pending_oom_rejected),
                        oom_count=int(pending_oom_count),
                    )
                    _atomic_json(runtime_cap_path, runtime_batch_cap.to_dict())
                    pending_oom_rejected = None
                    pending_oom_count = 0
                cursor += len(batch_uids)

            persist_artifact_buffer(force=True)
            if pending_journal_flush:
                _flush_model_sweep_journal(journal)
                pending_journal_flush = 0
            discard_prefetch()
            if producer_executor is not None:
                producer_executor.shutdown(wait=True, cancel_futures=False)
                producer_executor = None
            if persistence_executor is not None:
                persistence_executor.shutdown(wait=True)
                persistence_executor = None

        except Exception as exc:
            try:
                persist_artifact_buffer(force=True)
            except Exception:
                pass
            discard_prefetch()
            if producer_executor is not None:
                producer_executor.shutdown(wait=True, cancel_futures=False)
                producer_executor = None
            if persistence_executor is not None:
                persistence_executor.shutdown(wait=True, cancel_futures=False)
                persistence_executor = None
            try:
                _flush_model_sweep_journal(journal)
            except OSError:
                pass
            failed_uid = frame_uid if "frame_uid" in locals() else plan.requested_frame_uids[0]
            failed = Data6ModelSweepCheckpoint(
                plan=plan,
                records=_ordered_records(plan, existing_records),
                status=Data6ModelSweepStatus.FAILED,
                failed_frame_uid=failed_uid,
                failure_type=type(exc).__name__,
                failure_message=str(exc),
            )
            _atomic_json(checkpoint_path, failed.to_dict())
            raise

    complete = len(existing_records) == len(plan.requested_frame_uids)
    if phase_callback is not None:
        phase_callback(
            f"compacting {len(existing_records)} journal records into the final checkpoint"
        )
    checkpoint = Data6ModelSweepCheckpoint(
        plan=plan,
        records=_ordered_records(plan, existing_records),
        status=(
            Data6ModelSweepStatus.COMPLETE
            if complete
            else Data6ModelSweepStatus.INCOMPLETE
        ),
    )
    _atomic_json(checkpoint_path, checkpoint.to_dict())
    descriptor_manifest = prediction_manifest = None
    if complete:
        if phase_callback is not None:
            phase_callback("constructing and streaming final descriptor/prediction manifests")
        descriptor_manifest, prediction_manifest = _manifest_from_records(
            plan, checkpoint.records
        )
        if descriptor_manifest is not None:
            _atomic_json(
                root / "mace_descriptor_manifest.json", descriptor_manifest.to_dict()
            )
        if prediction_manifest is not None:
            _atomic_json(
                root / "atomic_model_prediction_manifest.json",
                prediction_manifest.to_dict(),
            )
    return Data6ModelSweepArtifacts(
        root_directory=str(root),
        checkpoint=checkpoint,
        descriptor_manifest=descriptor_manifest,
        prediction_manifest=prediction_manifest,
        runtime_batch_cap=runtime_batch_cap,
    )


def load_data6_model_sweep_artifacts(
    output_directory: str | Path,
    *,
    verify_sidecars: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> Data6ModelSweepArtifacts:
    root = Path(output_directory).resolve()
    checkpoint_path = root / "data6_model_sweep_checkpoint.json"
    if not checkpoint_path.is_file():
        raise TrainingDataInputError("DATA6 model-sweep checkpoint is absent.")
    checkpoint = Data6ModelSweepCheckpoint.from_dict(json.loads(checkpoint_path.read_text(encoding="utf-8")))
    descriptor_manifest = prediction_manifest = None
    if checkpoint.status is Data6ModelSweepStatus.COMPLETE:
        descriptor_manifest, prediction_manifest = _manifest_from_records(checkpoint.plan, checkpoint.records)
        # Full eager verification remains available for explicit integrity
        # audits.  Campaign continuation may defer verification to the first
        # actual descriptor/prediction read, which avoids scanning every file
        # twice immediately after the producing sweep completed.
        total = (
            (0 if descriptor_manifest is None else len(descriptor_manifest.records))
            + (0 if prediction_manifest is None else len(prediction_manifest.records))
        )
        completed = 0
        if verify_sidecars and descriptor_manifest is not None:
            for record in descriptor_manifest.records:
                if not _descriptor_valid(record, root):
                    raise TrainingDataSerializationError("Restored descriptor sidecar failed verification.")
                completed += 1
                if progress_callback is not None:
                    progress_callback(completed, total, record.frame_uid)
        if verify_sidecars and prediction_manifest is not None:
            for record in prediction_manifest.records:
                read_atomic_model_prediction(prediction_manifest, root, record.frame_uid)
                completed += 1
                if progress_callback is not None:
                    progress_callback(completed, total, record.frame_uid)
    runtime_batch_cap = None
    runtime_cap_path = root / "data6_runtime_batch_cap.json"
    if runtime_cap_path.is_file():
        runtime_batch_cap = Data6RuntimeBatchCap.from_dict(
            json.loads(runtime_cap_path.read_text(encoding="utf-8"))
        )
    return Data6ModelSweepArtifacts(
        root_directory=str(root),
        checkpoint=checkpoint,
        descriptor_manifest=descriptor_manifest,
        prediction_manifest=prediction_manifest,
        runtime_batch_cap=runtime_batch_cap,
    )
