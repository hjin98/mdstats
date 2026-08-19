"""Single-source replay foundation pseudo-label prediction and qualification.

REPLAY-UNIFY1C keeps expensive model inference independent from cheap
qualification, splitting, and ExtXYZ materialization. Prediction shards are
content-authenticated transport caches; logical cache identity is the
order-independent geometry -> prediction/audit mapping.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib
import json
import math
import shutil

import numpy as np

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    sha256_file_cached,
    validate_digest,
)
from .acceleration import MaceAccelerationKernelMode
from .foundation import FoundationInferenceIdentity, FoundationPotentialIdentity
from .replay_index import ReplaySourceIndex, iter_indexed_replay_frames, replay_source_indices_for_identities
from .replay import (
    ReplayLabelMode,
    ReplayLabelNamespace,
    ReplaySourceArtifact,
    ReplaySplitManifest,
    ReplaySplitRole,
    _BufferedReplayExtXYZWriter,
    _split_role_geometry_identities,
    canonical_replay_geometry_identity,
)

REPLAY_FOUNDATION_PREDICTION_POLICY_SCHEMA = "mdstats.replay-foundation-prediction-policy.v1"
REPLAY_FOUNDATION_PREDICTION_SHARD_SCHEMA = "mdstats.replay-foundation-prediction-shard.v1"
REPLAY_FOUNDATION_PREDICTION_CACHE_SCHEMA = "mdstats.replay-foundation-prediction-cache.v1"
REPLAY_FOUNDATION_AUDIT_CACHE_SCHEMA = "mdstats.replay-foundation-audit-cache.v1"
REPLAY_PSEUDOLABEL_QUALIFICATION_POLICY_SCHEMA = "mdstats.replay-pseudolabel-qualification-policy.v1"
REPLAY_PSEUDOLABEL_QUALIFICATION_SCHEMA = "mdstats.replay-pseudolabel-qualification.v1"
REPLAY_PSEUDOLABEL_VIEW_SCHEMA = "mdstats.replay-pseudolabel-view.v1"
REPLAY_PSEUDOLABEL_VIEW_RECEIPT_SCHEMA = "mdstats.replay-pseudolabel-view-receipt.v1"
REPLAY_PSEUDOLABEL_CACHE_KEY_SCHEMA = "mdstats.replay-foundation-prediction-cache-key.v1"
REPLAY_PSEUDOLABEL_ARRAY_SCHEMA = "mdstats.replay-pseudolabel-array.v1"

DEFAULT_REPLAY_MAX_FORCE_EV_PER_A = 20.0
DEFAULT_REPLAY_MAX_FORCE_RMS_EV_PER_A = 5.0
DEFAULT_REPLAY_MAX_STRESS_EV_PER_A3 = 0.5
DEFAULT_REPLAY_PREDICTION_BATCH_SIZE = 32
DEFAULT_REPLAY_PREDICTION_SHARD_SIZE = 256


def _array_identity(values: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(values, dtype=np.float64))
    h = hashlib.sha256()
    h.update(REPLAY_PSEUDOLABEL_ARRAY_SCHEMA.encode("ascii"))
    h.update(b"\0")
    h.update(array.dtype.str.encode("ascii"))
    h.update(b"\0")
    h.update(repr(tuple(int(v) for v in array.shape)).encode("ascii"))
    h.update(b"\0")
    h.update(memoryview(array).cast("B"))
    return h.hexdigest()


def _prediction_identity(energy: float, forces: np.ndarray, stress: np.ndarray | None) -> str:
    return digest(
        {
            "namespace": ReplayLabelNamespace.FOUNDATION_PSEUDOLABEL.value,
            "energy": _array_identity(np.asarray([float(energy)], dtype=np.float64)),
            "forces": _array_identity(forces),
            "stress": None if stress is None else _array_identity(stress),
        }
    )


def _audit_identity(*, natoms: int, force_rms: float, maximum_force: float, maximum_stress: float | None) -> str:
    values = np.asarray(
        [
            float(natoms),
            float(force_rms),
            float(maximum_force),
            np.nan if maximum_stress is None else float(maximum_stress),
        ],
        dtype=np.float64,
    )
    return _array_identity(values)


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _sha256_file(path: Path) -> str:
    return sha256_file_cached(path)


@dataclass(frozen=True, slots=True)
class ReplayFoundationPredictionPolicy:
    """Scientific/runtime authority for replay foundation predictions.

    Batch size and shard size are intentionally not part of this identity.
    They are execution/storage knobs and may change without invalidating an
    otherwise identical prediction authority.
    """

    foundation_potential: FoundationPotentialIdentity
    foundation_inference: FoundationInferenceIdentity
    device: str = "cpu"
    serialization_schema: str = REPLAY_FOUNDATION_PREDICTION_POLICY_SCHEMA

    def __post_init__(self) -> None:
        if self.serialization_schema != REPLAY_FOUNDATION_PREDICTION_POLICY_SCHEMA:
            raise TrainingDataInputError("Unsupported replay foundation-prediction policy schema.")
        if self.foundation_inference.foundation_potential_digest != self.foundation_potential.canonical_content_digest:
            raise TrainingDataInputError("Replay prediction inference identity does not bind the foundation potential.")
        try:
            mode = MaceAccelerationKernelMode(self.foundation_inference.resolved_kernel_mode)
        except ValueError as exc:
            raise TrainingDataInputError("Replay prediction has an unsupported resolved acceleration kernel mode.") from exc
        if mode is MaceAccelerationKernelMode.CUEQ_UNRESOLVED:
            raise TrainingDataInputError("Replay pseudo-label prediction cannot use unresolved CuEq execution.")
        if mode.backend.value != self.foundation_inference.backend:
            raise TrainingDataInputError("Replay prediction backend and resolved kernel mode disagree.")
        device = str(self.device).strip().lower()
        if not device:
            raise TrainingDataInputError("Replay prediction device must be non-empty.")
        object.__setattr__(self, "device", device)

    @property
    def content_digest(self) -> str:
        return digest(
            {
                "schema": self.serialization_schema,
                "foundation_potential_digest": self.foundation_potential.canonical_content_digest,
                "foundation_inference_digest": self.foundation_inference.content_digest,
                "foundation_checkpoint_sha256": self.foundation_potential.sha256,
                "foundation_head": self.foundation_potential.foundation_head,
                "device": self.device,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "foundation_potential": self.foundation_potential.to_dict(),
            "foundation_inference": self.foundation_inference.to_dict(),
            "device": self.device,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReplayFoundationPredictionPolicy":
        if payload.get("schema") != REPLAY_FOUNDATION_PREDICTION_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported replay foundation-prediction policy schema.")
        result = cls(
            foundation_potential=FoundationPotentialIdentity.from_dict(payload["foundation_potential"]),
            foundation_inference=FoundationInferenceIdentity.from_dict(payload["foundation_inference"]),
            device=str(payload["device"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Replay foundation-prediction policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ReplayFoundationPredictionShard:
    relative_path: str
    sha256: str
    geometry_identities: tuple[str, ...]
    prediction_label_identities: tuple[str, ...]
    audit_identities: tuple[str, ...]
    serialization_schema: str = REPLAY_FOUNDATION_PREDICTION_SHARD_SCHEMA

    def __post_init__(self) -> None:
        if self.serialization_schema != REPLAY_FOUNDATION_PREDICTION_SHARD_SCHEMA:
            raise TrainingDataInputError("Unsupported replay prediction-shard schema.")
        path = Path(self.relative_path)
        if path.is_absolute() or ".." in path.parts or str(path) in {"", "."}:
            raise TrainingDataInputError("Replay prediction shard path must remain inside the cache root.")
        object.__setattr__(self, "sha256", validate_digest(self.sha256, name="sha256"))
        geometry = tuple(validate_digest(v, name="geometry_identity") for v in self.geometry_identities)
        labels = tuple(validate_digest(v, name="prediction_label_identity") for v in self.prediction_label_identities)
        audits = tuple(validate_digest(v, name="audit_identity") for v in self.audit_identities)
        if not geometry or len(set(geometry)) != len(geometry):
            raise TrainingDataInputError("Replay prediction shard geometries must be unique and non-empty.")
        if len(labels) != len(geometry) or len(audits) != len(geometry):
            raise TrainingDataInputError("Replay prediction shard identities must match configuration count.")
        object.__setattr__(self, "geometry_identities", geometry)
        object.__setattr__(self, "prediction_label_identities", labels)
        object.__setattr__(self, "audit_identities", audits)

    @property
    def configuration_count(self) -> int:
        return len(self.geometry_identities)

    @property
    def logical_digest(self) -> str:
        return digest(
            {
                "schema": self.serialization_schema,
                "records": [
                    [g, p, a]
                    for g, p, a in zip(
                        self.geometry_identities,
                        self.prediction_label_identities,
                        self.audit_identities,
                        strict=True,
                    )
                ],
            }
        )

    @property
    def content_digest(self) -> str:
        return digest(
            {
                "schema": self.serialization_schema,
                "relative_path": self.relative_path,
                "sha256": self.sha256,
                "configuration_count": self.configuration_count,
                "logical_digest": self.logical_digest,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "geometry_identities": list(self.geometry_identities),
            "prediction_label_identities": list(self.prediction_label_identities),
            "audit_identities": list(self.audit_identities),
            "configuration_count": self.configuration_count,
            "logical_digest": self.logical_digest,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReplayFoundationPredictionShard":
        if payload.get("schema") != REPLAY_FOUNDATION_PREDICTION_SHARD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported replay prediction-shard schema.")
        result = cls(
            relative_path=str(payload["relative_path"]),
            sha256=str(payload["sha256"]),
            geometry_identities=tuple(str(v) for v in payload["geometry_identities"]),
            prediction_label_identities=tuple(str(v) for v in payload["prediction_label_identities"]),
            audit_identities=tuple(str(v) for v in payload["audit_identities"]),
        )
        for key, expected in (("logical_digest", result.logical_digest), ("content_digest", result.content_digest)):
            if payload.get(key) not in (None, expected):
                raise TrainingDataSerializationError(f"Replay prediction-shard {key} mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ReplayFoundationPredictionCache:
    root_directory: str
    source_geometry_set_digest: str
    prediction_policy: ReplayFoundationPredictionPolicy
    shards: tuple[ReplayFoundationPredictionShard, ...]
    audit_relative_path: str
    audit_sha256: str
    serialization_schema: str = REPLAY_FOUNDATION_PREDICTION_CACHE_SCHEMA

    def __post_init__(self) -> None:
        if self.serialization_schema != REPLAY_FOUNDATION_PREDICTION_CACHE_SCHEMA:
            raise TrainingDataInputError("Unsupported replay foundation-prediction cache schema.")
        object.__setattr__(
            self,
            "source_geometry_set_digest",
            validate_digest(self.source_geometry_set_digest, name="source_geometry_set_digest"),
        )
        shards = tuple(self.shards)
        if not shards:
            raise TrainingDataInputError("Replay foundation-prediction cache requires at least one shard.")
        geometries = [g for shard in shards for g in shard.geometry_identities]
        if len(set(geometries)) != len(geometries):
            raise TrainingDataInputError("Replay foundation-prediction cache contains duplicate geometry records.")
        if digest({"geometry_identities": sorted(geometries)}) != self.source_geometry_set_digest:
            raise TrainingDataInputError("Replay foundation-prediction cache does not cover the source geometry authority.")
        audit_path = Path(self.audit_relative_path)
        if audit_path.is_absolute() or ".." in audit_path.parts or str(audit_path) in {"", "."}:
            raise TrainingDataInputError("Replay audit-cache path must remain inside the prediction-cache root.")
        object.__setattr__(self, "audit_relative_path", str(audit_path))
        object.__setattr__(self, "audit_sha256", validate_digest(self.audit_sha256, name="audit_sha256"))
        object.__setattr__(self, "root_directory", str(Path(self.root_directory).expanduser().resolve()))
        object.__setattr__(self, "shards", shards)

    @property
    def configuration_count(self) -> int:
        return sum(shard.configuration_count for shard in self.shards)

    @property
    def prediction_mapping_digest(self) -> str:
        records = sorted(
            (g, p)
            for shard in self.shards
            for g, p in zip(shard.geometry_identities, shard.prediction_label_identities, strict=True)
        )
        return digest(
            {
                "namespace": ReplayLabelNamespace.FOUNDATION_PSEUDOLABEL.value,
                "records": [[g, p] for g, p in records],
            }
        )

    @property
    def audit_mapping_digest(self) -> str:
        records = sorted(
            (g, a)
            for shard in self.shards
            for g, a in zip(shard.geometry_identities, shard.audit_identities, strict=True)
        )
        return digest({"records": [[g, a] for g, a in records]})

    @property
    def storage_manifest_digest(self) -> str:
        return digest({"shards": [shard.content_digest for shard in self.shards], "audit_relative_path": self.audit_relative_path, "audit_sha256": self.audit_sha256})

    @property
    def content_digest(self) -> str:
        # Logical identity deliberately excludes root path and physical shard
        # grouping so repacking an equivalent cache does not invalidate splits.
        return digest(
            {
                "schema": self.serialization_schema,
                "source_geometry_set_digest": self.source_geometry_set_digest,
                "prediction_policy_digest": self.prediction_policy.content_digest,
                "configuration_count": self.configuration_count,
                "prediction_mapping_digest": self.prediction_mapping_digest,
                "audit_mapping_digest": self.audit_mapping_digest,
            }
        )

    @property
    def cache_key(self) -> str:
        return replay_foundation_prediction_cache_key(
            self.source_geometry_set_digest,
            self.prediction_policy.content_digest,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "root_directory": self.root_directory,
            "source_geometry_set_digest": self.source_geometry_set_digest,
            "prediction_policy": self.prediction_policy.to_dict(),
            "shards": [shard.to_dict() for shard in self.shards],
            "audit_relative_path": self.audit_relative_path,
            "audit_sha256": self.audit_sha256,
            "configuration_count": self.configuration_count,
            "prediction_mapping_digest": self.prediction_mapping_digest,
            "audit_mapping_digest": self.audit_mapping_digest,
            "storage_manifest_digest": self.storage_manifest_digest,
            "cache_key": self.cache_key,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReplayFoundationPredictionCache":
        if payload.get("schema") != REPLAY_FOUNDATION_PREDICTION_CACHE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported replay foundation-prediction cache schema.")
        result = cls(
            root_directory=str(payload["root_directory"]),
            source_geometry_set_digest=str(payload["source_geometry_set_digest"]),
            prediction_policy=ReplayFoundationPredictionPolicy.from_dict(payload["prediction_policy"]),
            shards=tuple(ReplayFoundationPredictionShard.from_dict(v) for v in payload["shards"]),
            audit_relative_path=str(payload["audit_relative_path"]),
            audit_sha256=str(payload["audit_sha256"]),
        )
        for key, expected in (
            ("prediction_mapping_digest", result.prediction_mapping_digest),
            ("audit_mapping_digest", result.audit_mapping_digest),
            ("storage_manifest_digest", result.storage_manifest_digest),
            ("cache_key", result.cache_key),
            ("content_digest", result.content_digest),
        ):
            if payload.get(key) not in (None, expected):
                raise TrainingDataSerializationError(f"Replay foundation-prediction cache {key} mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ReplayPseudolabelQualificationPolicy:
    maximum_force_ev_per_angstrom: float | None = DEFAULT_REPLAY_MAX_FORCE_EV_PER_A
    force_component_rms_ev_per_angstrom: float | None = DEFAULT_REPLAY_MAX_FORCE_RMS_EV_PER_A
    maximum_abs_stress_ev_per_angstrom3: float | None = DEFAULT_REPLAY_MAX_STRESS_EV_PER_A3
    require_stress: bool = False
    serialization_schema: str = REPLAY_PSEUDOLABEL_QUALIFICATION_POLICY_SCHEMA

    def __post_init__(self) -> None:
        if self.serialization_schema != REPLAY_PSEUDOLABEL_QUALIFICATION_POLICY_SCHEMA:
            raise TrainingDataInputError("Unsupported replay pseudo-label qualification policy schema.")
        for name in (
            "maximum_force_ev_per_angstrom",
            "force_component_rms_ev_per_angstrom",
            "maximum_abs_stress_ev_per_angstrom3",
        ):
            value = getattr(self, name)
            if value is None:
                continue
            numeric = float(value)
            if not math.isfinite(numeric) or numeric < 0.0:
                raise TrainingDataInputError(f"{name} must be a finite nonnegative value or None.")
            object.__setattr__(self, name, numeric)
        object.__setattr__(self, "require_stress", bool(self.require_stress))

    @property
    def content_digest(self) -> str:
        return digest(
            {
                "schema": self.serialization_schema,
                "maximum_force_ev_per_angstrom": self.maximum_force_ev_per_angstrom,
                "force_component_rms_ev_per_angstrom": self.force_component_rms_ev_per_angstrom,
                "maximum_abs_stress_ev_per_angstrom3": self.maximum_abs_stress_ev_per_angstrom3,
                "require_stress": self.require_stress,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "maximum_force_ev_per_angstrom": self.maximum_force_ev_per_angstrom,
            "force_component_rms_ev_per_angstrom": self.force_component_rms_ev_per_angstrom,
            "maximum_abs_stress_ev_per_angstrom3": self.maximum_abs_stress_ev_per_angstrom3,
            "require_stress": self.require_stress,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReplayPseudolabelQualificationPolicy":
        if payload.get("schema") != REPLAY_PSEUDOLABEL_QUALIFICATION_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported replay pseudo-label qualification policy schema.")
        result = cls(
            maximum_force_ev_per_angstrom=(
                None if payload.get("maximum_force_ev_per_angstrom") is None else float(payload["maximum_force_ev_per_angstrom"])
            ),
            force_component_rms_ev_per_angstrom=(
                None if payload.get("force_component_rms_ev_per_angstrom") is None else float(payload["force_component_rms_ev_per_angstrom"])
            ),
            maximum_abs_stress_ev_per_angstrom3=(
                None if payload.get("maximum_abs_stress_ev_per_angstrom3") is None else float(payload["maximum_abs_stress_ev_per_angstrom3"])
            ),
            require_stress=bool(payload.get("require_stress", False)),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Replay pseudo-label qualification policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ReplayPseudolabelQualification:
    source_geometry_set_digest: str
    prediction_cache_digest: str
    prediction_policy_digest: str
    audit_mapping_digest: str
    policy: ReplayPseudolabelQualificationPolicy
    eligible_geometry_identities: tuple[str, ...]
    rejected: tuple[tuple[str, tuple[str, ...]], ...]
    serialization_schema: str = REPLAY_PSEUDOLABEL_QUALIFICATION_SCHEMA

    def __post_init__(self) -> None:
        if self.serialization_schema != REPLAY_PSEUDOLABEL_QUALIFICATION_SCHEMA:
            raise TrainingDataInputError("Unsupported replay pseudo-label qualification schema.")
        for name in (
            "source_geometry_set_digest",
            "prediction_cache_digest",
            "prediction_policy_digest",
            "audit_mapping_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        eligible = tuple(sorted(validate_digest(v, name="eligible_geometry_identity") for v in self.eligible_geometry_identities))
        if len(set(eligible)) != len(eligible):
            raise TrainingDataInputError("Replay pseudo-label qualification has duplicate eligible geometries.")
        rejected_records: list[tuple[str, tuple[str, ...]]] = []
        for raw_geometry, raw_reasons in self.rejected:
            geometry = validate_digest(raw_geometry, name="rejected_geometry_identity")
            reasons = tuple(sorted(set(str(v) for v in raw_reasons if str(v))))
            if not reasons:
                raise TrainingDataInputError("Rejected replay geometry must carry at least one reason.")
            rejected_records.append((geometry, reasons))
        rejected_records.sort(key=lambda item: item[0])
        rejected_ids = [item[0] for item in rejected_records]
        if len(set(rejected_ids)) != len(rejected_ids) or set(eligible) & set(rejected_ids):
            raise TrainingDataInputError("Replay pseudo-label qualification membership is inconsistent.")
        geometry_set_digest = digest({"geometry_identities": sorted([*eligible, *rejected_ids])})
        if geometry_set_digest != self.source_geometry_set_digest:
            raise TrainingDataInputError("Replay pseudo-label qualification does not cover source geometry authority.")
        object.__setattr__(self, "eligible_geometry_identities", eligible)
        object.__setattr__(self, "rejected", tuple(rejected_records))

    @property
    def eligible_count(self) -> int:
        return len(self.eligible_geometry_identities)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)

    @property
    def reason_counts(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for _, reasons in self.rejected:
            for reason in reasons:
                result[reason] = result.get(reason, 0) + 1
        return dict(sorted(result.items()))

    @property
    def eligible_geometry_set_digest(self) -> str:
        return digest({"geometry_identities": sorted(self.eligible_geometry_identities)})

    @property
    def content_digest(self) -> str:
        return digest(
            {
                "schema": self.serialization_schema,
                "source_geometry_set_digest": self.source_geometry_set_digest,
                "prediction_cache_digest": self.prediction_cache_digest,
                "prediction_policy_digest": self.prediction_policy_digest,
                "audit_mapping_digest": self.audit_mapping_digest,
                "qualification_policy_digest": self.policy.content_digest,
                "eligible_geometry_identities": list(self.eligible_geometry_identities),
                "rejected": [[g, list(reasons)] for g, reasons in self.rejected],
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "source_geometry_set_digest": self.source_geometry_set_digest,
            "prediction_cache_digest": self.prediction_cache_digest,
            "prediction_policy_digest": self.prediction_policy_digest,
            "audit_mapping_digest": self.audit_mapping_digest,
            "policy": self.policy.to_dict(),
            "eligible_geometry_identities": list(self.eligible_geometry_identities),
            "rejected": [[g, list(reasons)] for g, reasons in self.rejected],
            "eligible_count": self.eligible_count,
            "rejected_count": self.rejected_count,
            "reason_counts": self.reason_counts,
            "eligible_geometry_set_digest": self.eligible_geometry_set_digest,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReplayPseudolabelQualification":
        if payload.get("schema") != REPLAY_PSEUDOLABEL_QUALIFICATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported replay pseudo-label qualification schema.")
        result = cls(
            source_geometry_set_digest=str(payload["source_geometry_set_digest"]),
            prediction_cache_digest=str(payload["prediction_cache_digest"]),
            prediction_policy_digest=str(payload["prediction_policy_digest"]),
            audit_mapping_digest=str(payload["audit_mapping_digest"]),
            policy=ReplayPseudolabelQualificationPolicy.from_dict(payload["policy"]),
            eligible_geometry_identities=tuple(str(v) for v in payload["eligible_geometry_identities"]),
            rejected=tuple((str(item[0]), tuple(str(v) for v in item[1])) for item in payload["rejected"]),
        )
        for key, expected in (
            ("eligible_geometry_set_digest", result.eligible_geometry_set_digest),
            ("content_digest", result.content_digest),
        ):
            if payload.get(key) not in (None, expected):
                raise TrainingDataSerializationError(f"Replay pseudo-label qualification {key} mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ReplayPseudolabelViewArtifact:
    role: ReplaySplitRole
    path: str
    sha256: str
    configuration_count: int
    geometry_set_digest: str
    prediction_label_set_digest: str
    source_geometry_set_digest: str
    prediction_cache_digest: str
    qualification_digest: str
    split_manifest_digest: str
    serialization_schema: str = REPLAY_PSEUDOLABEL_VIEW_SCHEMA

    def __post_init__(self) -> None:
        if self.serialization_schema != REPLAY_PSEUDOLABEL_VIEW_SCHEMA:
            raise TrainingDataInputError("Unsupported replay pseudo-label view schema.")
        object.__setattr__(self, "role", ReplaySplitRole(self.role))
        if int(self.configuration_count) <= 0:
            raise TrainingDataInputError("Replay pseudo-label view must contain at least one configuration.")
        object.__setattr__(self, "configuration_count", int(self.configuration_count))
        for name in (
            "sha256", "geometry_set_digest", "prediction_label_set_digest", "source_geometry_set_digest",
            "prediction_cache_digest", "qualification_digest", "split_manifest_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))

    @property
    def logical_digest(self) -> str:
        return digest(
            {
                "schema": self.serialization_schema,
                "role": self.role.value,
                "configuration_count": self.configuration_count,
                "geometry_set_digest": self.geometry_set_digest,
                "prediction_label_set_digest": self.prediction_label_set_digest,
                "source_geometry_set_digest": self.source_geometry_set_digest,
                "prediction_cache_digest": self.prediction_cache_digest,
                "qualification_digest": self.qualification_digest,
                "split_manifest_digest": self.split_manifest_digest,
                "label_namespace": ReplayLabelNamespace.FOUNDATION_PSEUDOLABEL.value,
                "transport_fields": ["REF_energy", "REF_forces", "REF_stress"],
            }
        )

    @property
    def content_digest(self) -> str:
        return digest(
            {
                "schema": self.serialization_schema,
                "logical_digest": self.logical_digest,
                "path": self.path,
                "sha256": self.sha256,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "role": self.role.value,
            "path": self.path,
            "sha256": self.sha256,
            "configuration_count": self.configuration_count,
            "geometry_set_digest": self.geometry_set_digest,
            "prediction_label_set_digest": self.prediction_label_set_digest,
            "source_geometry_set_digest": self.source_geometry_set_digest,
            "prediction_cache_digest": self.prediction_cache_digest,
            "qualification_digest": self.qualification_digest,
            "split_manifest_digest": self.split_manifest_digest,
            "logical_digest": self.logical_digest,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReplayPseudolabelViewArtifact":
        if payload.get("schema") != REPLAY_PSEUDOLABEL_VIEW_SCHEMA:
            raise TrainingDataSerializationError("Unsupported replay pseudo-label view schema.")
        result = cls(
            role=ReplaySplitRole(payload["role"]),
            path=str(payload["path"]),
            sha256=str(payload["sha256"]),
            configuration_count=int(payload["configuration_count"]),
            geometry_set_digest=str(payload["geometry_set_digest"]),
            prediction_label_set_digest=str(payload["prediction_label_set_digest"]),
            source_geometry_set_digest=str(payload["source_geometry_set_digest"]),
            prediction_cache_digest=str(payload["prediction_cache_digest"]),
            qualification_digest=str(payload["qualification_digest"]),
            split_manifest_digest=str(payload["split_manifest_digest"]),
        )
        for key, expected in (("logical_digest", result.logical_digest), ("content_digest", result.content_digest)):
            if payload.get(key) not in (None, expected):
                raise TrainingDataSerializationError(f"Replay pseudo-label view {key} mismatch.")
        return result


def replay_foundation_prediction_cache_key(source_geometry_set_digest: str, prediction_policy_digest: str) -> str:
    return digest(
        {
            "schema": REPLAY_PSEUDOLABEL_CACHE_KEY_SCHEMA,
            "source_geometry_set_digest": validate_digest(source_geometry_set_digest, name="source_geometry_set_digest"),
            "prediction_policy_digest": validate_digest(prediction_policy_digest, name="prediction_policy_digest"),
        }
    )


def _prediction_cache_directory(root: Path, key: str) -> Path:
    return root / key[:2] / key


def _prediction_manifest_path(directory: Path) -> Path:
    return directory / "manifest.json"


def _validate_cache_storage(cache: ReplayFoundationPredictionCache) -> None:
    root = Path(cache.root_directory)
    audit_path = root / cache.audit_relative_path
    if not audit_path.is_file() or _sha256_file(audit_path) != cache.audit_sha256:
        raise TrainingDataInputError(f"Replay audit cache is missing or changed: {audit_path!s}.")
    for shard in cache.shards:
        path = root / shard.relative_path
        if not path.is_file() or _sha256_file(path) != shard.sha256:
            raise TrainingDataInputError(f"Replay prediction cache shard is missing or changed: {path!s}.")


def _load_existing_prediction_cache(
    directory: Path,
    *,
    source_geometry_set_digest: str,
    prediction_policy: ReplayFoundationPredictionPolicy,
) -> ReplayFoundationPredictionCache | None:
    manifest = _prediction_manifest_path(directory)
    if not manifest.is_file():
        return None
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        cache = ReplayFoundationPredictionCache.from_dict(payload)
        if Path(cache.root_directory) != directory.resolve():
            return None
        if cache.source_geometry_set_digest != source_geometry_set_digest:
            return None
        if cache.prediction_policy.content_digest != prediction_policy.content_digest:
            return None
        if cache.cache_key != directory.name:
            return None
        _validate_cache_storage(cache)
        return cache
    except Exception:
        return None


def _provider_predictions(
    provider: Any,
    atoms_batch: Sequence[Any],
    geometry_identities: Sequence[str],
    *,
    graph_cache_directory: str | Path | None,
) -> tuple[Any, ...]:
    try:
        result = provider.predict_batch(
            atoms_batch,
            geometry_identities=geometry_identities,
            graph_cache_directory=graph_cache_directory,
        )
    except TypeError as exc:
        message = str(exc)
        if "unexpected keyword" not in message and "geometry_identities" not in message:
            raise
        result = provider.predict_batch(atoms_batch)
    except RuntimeError as exc:
        message = str(exc).lower()
        memory_error = any(
            marker in message
            for marker in ("out of memory", "cannot allocate memory", "cuda error: memory allocation", "cublas_status_alloc_failed")
        )
        if len(atoms_batch) <= 1 or not memory_error:
            raise
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        middle = len(atoms_batch) // 2
        return (
            *_provider_predictions(
                provider,
                atoms_batch[:middle],
                geometry_identities[:middle],
                graph_cache_directory=graph_cache_directory,
            ),
            *_provider_predictions(
                provider,
                atoms_batch[middle:],
                geometry_identities[middle:],
                graph_cache_directory=graph_cache_directory,
            ),
        )
    return tuple(result)


def _construct_prediction_provider(policy: ReplayFoundationPredictionPolicy, source: ReplaySourceArtifact) -> Any:
    from .model_features import MaceCalculatorProvider

    model_supported = set(policy.foundation_potential.model_atomic_numbers)
    if model_supported and not set(source.atomic_numbers).issubset(model_supported):
        missing = sorted(set(source.atomic_numbers) - model_supported)
        raise TrainingDataInputError(f"Replay source contains species unsupported by the foundation model: {missing}.")
    mode = MaceAccelerationKernelMode(policy.foundation_inference.resolved_kernel_mode)
    calculator_kwargs = dict(mode.calculator_kwargs())
    return MaceCalculatorProvider.from_model_path(
        policy.foundation_potential.reference,
        device=policy.device,
        default_dtype=policy.foundation_inference.default_dtype,
        requested_atomic_numbers=source.atomic_numbers,
        foundation_potential_identity=policy.foundation_potential,
        foundation_inference_identity=policy.foundation_inference,
        **calculator_kwargs,
    )


def _validate_prediction_provider(provider: Any, policy: ReplayFoundationPredictionPolicy) -> None:
    checkpoint = getattr(provider, "checkpoint_identity", None)
    if checkpoint is None:
        raise TrainingDataInputError("Replay pseudo-label provider must expose checkpoint_identity.")
    if str(getattr(checkpoint, "checkpoint_sha256", "")) != policy.foundation_potential.sha256:
        raise TrainingDataInputError("Replay pseudo-label provider checkpoint SHA does not match prediction policy.")
    if str(getattr(checkpoint, "default_dtype", "")) != policy.foundation_inference.default_dtype:
        raise TrainingDataInputError("Replay pseudo-label provider dtype does not match prediction policy.")
    potential_digest = getattr(checkpoint, "foundation_potential_digest", None)
    inference_digest = getattr(checkpoint, "foundation_inference_digest", None)
    foundation_head = getattr(checkpoint, "foundation_head", None)
    if any(value is not None for value in (potential_digest, inference_digest, foundation_head)):
        if potential_digest != policy.foundation_potential.canonical_content_digest:
            raise TrainingDataInputError("Replay pseudo-label provider foundation potential binding mismatch.")
        if inference_digest != policy.foundation_inference.content_digest:
            raise TrainingDataInputError("Replay pseudo-label provider foundation inference binding mismatch.")
        if foundation_head != policy.foundation_potential.foundation_head:
            raise TrainingDataInputError("Replay pseudo-label provider foundation head binding mismatch.")
    if hasattr(provider, "set_head"):
        provider.set_head(policy.foundation_potential.foundation_head)


def _prediction_payload(prediction: Any, *, expected_natoms: int) -> tuple[float, np.ndarray, np.ndarray | None, str, str, tuple[float, float, float | None]]:
    energy = float(prediction.energy_ev)
    forces = np.asarray(prediction.forces_ev_per_angstrom, dtype=np.float64)
    stress = None if prediction.stress_ev_per_angstrom3 is None else np.asarray(prediction.stress_ev_per_angstrom3, dtype=np.float64)
    if not math.isfinite(energy) or forces.shape != (expected_natoms, 3) or not np.all(np.isfinite(forces)):
        raise TrainingDataInputError("Replay foundation prediction contains invalid energy/forces.")
    if stress is not None:
        if stress.shape == (6,):
            # Provider-native MACE predictions are 3x3; retain controlled support
            # for test/third-party providers that use ASE Voigt storage.
            xx, yy, zz, yz, xz, xy = stress
            stress = np.asarray([[xx, xy, xz], [xy, yy, yz], [xz, yz, zz]], dtype=np.float64)
        if stress.shape != (3, 3) or not np.all(np.isfinite(stress)):
            raise TrainingDataInputError("Replay foundation prediction contains invalid stress.")
    force_rms = float(np.sqrt(np.mean(forces * forces)))
    maximum_force = float(np.max(np.linalg.norm(forces, axis=1)))
    maximum_stress = None if stress is None else float(np.max(np.abs(stress)))
    prediction_identity = _prediction_identity(energy, forces, stress)
    audit_identity = _audit_identity(
        natoms=expected_natoms,
        force_rms=force_rms,
        maximum_force=maximum_force,
        maximum_stress=maximum_stress,
    )
    return energy, forces, stress, prediction_identity, audit_identity, (force_rms, maximum_force, maximum_stress)


def _write_prediction_shard(directory: Path, index: int, records: Sequence[tuple[str, float, np.ndarray, np.ndarray | None, str, str, tuple[float, float, float | None]]]) -> ReplayFoundationPredictionShard:
    if not records:
        raise TrainingDataInputError("Cannot write an empty replay prediction shard.")
    geometries = tuple(item[0] for item in records)
    energies = np.asarray([item[1] for item in records], dtype=np.float64)
    natoms = np.asarray([item[2].shape[0] for item in records], dtype=np.int32)
    offsets = np.empty(len(records) + 1, dtype=np.int64)
    offsets[0] = 0
    np.cumsum(natoms, dtype=np.int64, out=offsets[1:])
    forces = np.concatenate([item[2] for item in records], axis=0).astype(np.float64, copy=False)
    stress_present = np.asarray([item[3] is not None for item in records], dtype=np.uint8)
    stresses = np.zeros((len(records), 3, 3), dtype=np.float64)
    for row, item in enumerate(records):
        if item[3] is not None:
            stresses[row] = item[3]
    prediction_ids = tuple(item[4] for item in records)
    audit_ids = tuple(item[5] for item in records)
    path = directory / "shards" / f"predictions-{index:05d}.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp.npz")
    np.savez(
        temporary,
        geometry_identities=np.asarray(geometries, dtype="S64"),
        energies=energies,
        natoms=natoms,
        force_offsets=offsets,
        forces=forces,
        stress_present=stress_present,
        stresses=stresses,
    )
    temporary.replace(path)
    return ReplayFoundationPredictionShard(
        relative_path=str(path.relative_to(directory)),
        sha256=_sha256_file(path),
        geometry_identities=geometries,
        prediction_label_identities=prediction_ids,
        audit_identities=audit_ids,
    )


def _write_audit_cache(
    directory: Path,
    records: Sequence[tuple[str, tuple[float, float, float | None], str]],
) -> tuple[str, str]:
    if not records:
        raise TrainingDataInputError("Cannot write an empty replay foundation audit cache.")
    path = directory / "audit.npz"
    temporary = path.with_name(path.name + ".tmp.npz")
    np.savez(
        temporary,
        schema=np.asarray([REPLAY_FOUNDATION_AUDIT_CACHE_SCHEMA], dtype="S64"),
        geometry_identities=np.asarray([item[0] for item in records], dtype="S64"),
        force_component_rms=np.asarray([item[1][0] for item in records], dtype=np.float64),
        maximum_force=np.asarray([item[1][1] for item in records], dtype=np.float64),
        maximum_abs_stress=np.asarray([
            np.nan if item[1][2] is None else item[1][2] for item in records
        ], dtype=np.float64),
        audit_identities=np.asarray([item[2] for item in records], dtype="S64"),
    )
    temporary.replace(path)
    return str(path.relative_to(directory)), _sha256_file(path)


def _foundation_prediction_input_frame(atoms: Any) -> Any:
    """Return a geometry-only copy so source truth cannot enter prediction graphs."""

    frame = atoms.copy()
    frame.calc = None
    for key in (
        "energy", "REF_energy", "stress", "REF_stress", "virial", "virials",
        "REF_virial", "REF_virials", "corrected_total_energy",
    ):
        frame.info.pop(key, None)
    for key in ("forces", "REF_forces"):
        if key in frame.arrays:
            del frame.arrays[key]
    return frame


def build_replay_foundation_prediction_cache(
    source: ReplaySourceArtifact,
    policy: ReplayFoundationPredictionPolicy,
    cache_root: str | Path,
    *,
    provider: Any | None = None,
    batch_size: int = DEFAULT_REPLAY_PREDICTION_BATCH_SIZE,
    shard_size: int = DEFAULT_REPLAY_PREDICTION_SHARD_SIZE,
    graph_cache_directory: str | Path | None = None,
    source_index: ReplaySourceIndex | None = None,
) -> ReplayFoundationPredictionCache:
    """Return/create a reusable foundation-prediction cache for one replay source.

    A valid cache hit returns before the replay source is opened and before a
    model provider is constructed. Missing caches stream the source in bounded
    inference batches and flush fixed-size prediction shards independently of
    the inference batch size.
    """

    if int(batch_size) <= 0 or int(shard_size) <= 0:
        raise TrainingDataInputError("Replay prediction batch_size and shard_size must be positive.")
    if policy.foundation_potential.model_atomic_numbers and not set(source.atomic_numbers).issubset(
        set(policy.foundation_potential.model_atomic_numbers)
    ):
        missing = sorted(set(source.atomic_numbers) - set(policy.foundation_potential.model_atomic_numbers))
        raise TrainingDataInputError(f"Replay source contains species unsupported by the foundation model: {missing}.")
    root = Path(cache_root).expanduser().resolve()
    key = replay_foundation_prediction_cache_key(source.geometry_set_digest, policy.content_digest)
    directory = _prediction_cache_directory(root, key)
    cached = _load_existing_prediction_cache(
        directory,
        source_geometry_set_digest=source.geometry_set_digest,
        prediction_policy=policy,
    )
    if cached is not None:
        return cached

    source_path = Path(source.path).expanduser().resolve()
    if not source_path.is_file():
        raise TrainingDataInputError(f"Replay source file does not exist: {source_path!s}.")
    if _sha256_file(source_path) != source.sha256:
        raise TrainingDataInputError("Replay source file SHA-256 differs from the authenticated source artifact.")
    if provider is None:
        model_path = Path(policy.foundation_potential.reference).expanduser().resolve()
        if not model_path.is_file() or _sha256_file(model_path) != policy.foundation_potential.sha256:
            raise TrainingDataInputError("Foundation checkpoint file is missing or differs from the prediction policy.")
        provider = _construct_prediction_provider(policy, source)
    _validate_prediction_provider(provider, policy)

    try:
        from ase.io import iread
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for replay pseudo-label prediction.") from exc

    work = directory.with_name(directory.name + ".work")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=False)
    batch_atoms: list[Any] = []
    batch_ids: list[str] = []
    shard_records: list[tuple[str, float, np.ndarray, np.ndarray | None, str, str, tuple[float, float, float | None]]] = []
    shards: list[ReplayFoundationPredictionShard] = []
    audit_records: list[tuple[str, tuple[float, float, float | None], str]] = []
    seen: set[str] = set()

    def flush_inference_batch() -> None:
        nonlocal shard_records
        if not batch_atoms:
            return
        predictions = _provider_predictions(
            provider,
            tuple(batch_atoms),
            tuple(batch_ids),
            graph_cache_directory=graph_cache_directory,
        )
        if len(predictions) != len(batch_atoms):
            raise TrainingDataInputError("Replay foundation prediction provider returned the wrong batch size.")
        for identity, atoms, prediction in zip(batch_ids, batch_atoms, predictions, strict=True):
            energy, forces, stress, prediction_identity, audit_identity, audit = _prediction_payload(
                prediction,
                expected_natoms=len(atoms),
            )
            shard_records.append((identity, energy, forces, stress, prediction_identity, audit_identity, audit))
            audit_records.append((identity, audit, audit_identity))
            if len(shard_records) >= int(shard_size):
                shards.append(_write_prediction_shard(work, len(shards), shard_records[: int(shard_size)]))
                del shard_records[: int(shard_size)]
        batch_atoms.clear()
        batch_ids.clear()

    if source_index is None:
        frame_iterator = enumerate(iread(source_path, index=":", format="extxyz"))
    else:
        frame_iterator = iter_indexed_replay_frames(source, source_index)
    try:
        for source_frame_index, atoms in frame_iterator:
            identity = source.geometry_identities[source_frame_index]
            if identity in seen:
                raise TrainingDataInputError("Replay source yielded a duplicate geometry during pseudo-label prediction.")
            seen.add(identity)
            batch_atoms.append(_foundation_prediction_input_frame(atoms))
            batch_ids.append(identity)
            if len(batch_atoms) >= int(batch_size):
                flush_inference_batch()
        flush_inference_batch()
        if shard_records:
            shards.append(_write_prediction_shard(work, len(shards), shard_records))
            shard_records.clear()
        if seen != set(source.geometry_identities):
            raise TrainingDataInputError("Replay prediction source membership differs from the authenticated source artifact.")
        audit_relative_path, audit_sha256 = _write_audit_cache(work, audit_records)
        cache = ReplayFoundationPredictionCache(
            root_directory=str(work.resolve()),
            source_geometry_set_digest=source.geometry_set_digest,
            prediction_policy=policy,
            shards=tuple(shards),
            audit_relative_path=audit_relative_path,
            audit_sha256=audit_sha256,
        )
        manifest_payload = cache.to_dict()
        _atomic_write_json(_prediction_manifest_path(work), manifest_payload)
        directory.parent.mkdir(parents=True, exist_ok=True)
        if directory.exists():
            shutil.rmtree(directory)
        work.replace(directory)
        # Relocation changes only the locator, not logical cache identity.
        cache = ReplayFoundationPredictionCache(
            root_directory=str(directory),
            source_geometry_set_digest=cache.source_geometry_set_digest,
            prediction_policy=cache.prediction_policy,
            shards=cache.shards,
            audit_relative_path=cache.audit_relative_path,
            audit_sha256=cache.audit_sha256,
        )
        _atomic_write_json(_prediction_manifest_path(directory), cache.to_dict())
        return cache
    except Exception:
        if work.exists():
            shutil.rmtree(work, ignore_errors=True)
        raise


class _ReplayPredictionShardReader:
    def __init__(self, cache: ReplayFoundationPredictionCache, *, max_resident_shards: int = 4) -> None:
        self.cache = cache
        self.max_resident_shards = max(1, int(max_resident_shards))
        self.index: dict[str, tuple[int, int]] = {}
        for shard_index, shard in enumerate(cache.shards):
            for local_index, identity in enumerate(shard.geometry_identities):
                self.index[identity] = (shard_index, local_index)
        self._audit_table: dict[str, np.ndarray] | None = None
        self._audit_index: dict[str, int] | None = None
        self._prediction_resident: OrderedDict[int, dict[str, np.ndarray]] = OrderedDict()

    def _prediction_path(self, shard_index: int) -> Path:
        shard = self.cache.shards[shard_index]
        path = Path(self.cache.root_directory) / shard.relative_path
        if not path.is_file() or _sha256_file(path) != shard.sha256:
            raise TrainingDataInputError("Replay prediction shard is missing or changed during use.")
        return path

    def _load_audit_table(self) -> tuple[dict[str, np.ndarray], dict[str, int]]:
        if self._audit_table is not None and self._audit_index is not None:
            return self._audit_table, self._audit_index
        path = Path(self.cache.root_directory) / self.cache.audit_relative_path
        if not path.is_file() or _sha256_file(path) != self.cache.audit_sha256:
            raise TrainingDataInputError("Replay foundation audit cache is missing or changed during use.")
        with np.load(path, allow_pickle=False) as payload:
            schema_raw = payload["schema"][0]
            schema = schema_raw.decode("ascii") if isinstance(schema_raw, (bytes, np.bytes_)) else str(schema_raw)
            if schema != REPLAY_FOUNDATION_AUDIT_CACHE_SCHEMA:
                raise TrainingDataInputError("Replay foundation audit-cache schema mismatch.")
            geometry_raw = np.array(payload["geometry_identities"], copy=True)
            data = {
                "force_component_rms": np.array(payload["force_component_rms"], copy=True),
                "maximum_force": np.array(payload["maximum_force"], copy=True),
                "maximum_abs_stress": np.array(payload["maximum_abs_stress"], copy=True),
                "audit_identities": np.array(payload["audit_identities"], copy=True),
            }
        geometry = [value.decode("ascii") if isinstance(value, (bytes, np.bytes_)) else str(value) for value in geometry_raw]
        if len(geometry) != self.cache.configuration_count or set(geometry) != set(self.index):
            raise TrainingDataInputError("Replay foundation audit-cache geometry membership mismatch.")
        audit_index = {identity: index for index, identity in enumerate(geometry)}
        if len(audit_index) != len(geometry):
            raise TrainingDataInputError("Replay foundation audit cache contains duplicate geometries.")
        # Authenticate compact audit values against manifest-level audit identities.
        expected = {
            g: a
            for shard in self.cache.shards
            for g, a in zip(shard.geometry_identities, shard.audit_identities, strict=True)
        }
        for identity, row in audit_index.items():
            raw = data["audit_identities"][row]
            observed = raw.decode("ascii") if isinstance(raw, (bytes, np.bytes_)) else str(raw)
            if observed != expected[identity]:
                raise TrainingDataInputError("Replay foundation audit-cache identity mismatch.")
        self._audit_table = data
        self._audit_index = audit_index
        return data, audit_index

    def _load_prediction(self, shard_index: int) -> dict[str, np.ndarray]:
        cached = self._prediction_resident.get(shard_index)
        if cached is not None:
            self._prediction_resident.move_to_end(shard_index)
            return cached
        path = self._prediction_path(shard_index)
        with np.load(path, allow_pickle=False) as payload:
            data = {
                "energies": np.array(payload["energies"], copy=True),
                "force_offsets": np.array(payload["force_offsets"], copy=True),
                "forces": np.array(payload["forces"], copy=True),
                "stress_present": np.array(payload["stress_present"], copy=True),
                "stresses": np.array(payload["stresses"], copy=True),
            }
        self._prediction_resident[shard_index] = data
        while len(self._prediction_resident) > self.max_resident_shards:
            self._prediction_resident.popitem(last=False)
        return data

    def audit(self, geometry_identity: str) -> tuple[float, float, float | None]:
        data, audit_index = self._load_audit_table()
        try:
            local_index = audit_index[geometry_identity]
        except KeyError as exc:
            raise TrainingDataInputError("Replay geometry is absent from the foundation audit cache.") from exc
        stress_value = float(data["maximum_abs_stress"][local_index])
        return (
            float(data["force_component_rms"][local_index]),
            float(data["maximum_force"][local_index]),
            None if np.isnan(stress_value) else stress_value,
        )

    def prediction(self, geometry_identity: str) -> tuple[float, np.ndarray, np.ndarray | None, str]:
        try:
            shard_index, local_index = self.index[geometry_identity]
        except KeyError as exc:
            raise TrainingDataInputError("Replay geometry is absent from the foundation-prediction cache.") from exc
        data = self._load_prediction(shard_index)
        offsets = data["force_offsets"]
        start = int(offsets[local_index])
        stop = int(offsets[local_index + 1])
        forces = np.asarray(data["forces"][start:stop], dtype=np.float64).copy()
        stress = None
        if bool(data["stress_present"][local_index]):
            stress = np.asarray(data["stresses"][local_index], dtype=np.float64).copy()
        identity = self.cache.shards[shard_index].prediction_label_identities[local_index]
        return float(data["energies"][local_index]), forces, stress, identity

def build_replay_pseudolabel_qualification(
    cache: ReplayFoundationPredictionCache,
    policy: ReplayPseudolabelQualificationPolicy | None = None,
) -> ReplayPseudolabelQualification:
    """Classify cached predictions without opening the source or invoking MACE."""

    active = ReplayPseudolabelQualificationPolicy() if policy is None else policy
    reader = _ReplayPredictionShardReader(cache)
    eligible: list[str] = []
    rejected: list[tuple[str, tuple[str, ...]]] = []
    for identity in sorted(reader.index):
        force_rms, maximum_force, maximum_stress = reader.audit(identity)
        reasons: list[str] = []
        if active.maximum_force_ev_per_angstrom is not None and maximum_force > active.maximum_force_ev_per_angstrom:
            reasons.append("maximum_force")
        if active.force_component_rms_ev_per_angstrom is not None and force_rms > active.force_component_rms_ev_per_angstrom:
            reasons.append("force_component_rms")
        if maximum_stress is None:
            if active.require_stress:
                reasons.append("missing_stress")
        elif (
            active.maximum_abs_stress_ev_per_angstrom3 is not None
            and maximum_stress > active.maximum_abs_stress_ev_per_angstrom3
        ):
            reasons.append("maximum_abs_stress")
        if reasons:
            rejected.append((identity, tuple(reasons)))
        else:
            eligible.append(identity)
    return ReplayPseudolabelQualification(
        source_geometry_set_digest=cache.source_geometry_set_digest,
        prediction_cache_digest=cache.content_digest,
        prediction_policy_digest=cache.prediction_policy.content_digest,
        audit_mapping_digest=cache.audit_mapping_digest,
        policy=active,
        eligible_geometry_identities=tuple(eligible),
        rejected=tuple(rejected),
    )


def _pseudo_view_expected(
    cache: ReplayFoundationPredictionCache,
    qualification: ReplayPseudolabelQualification,
    split: ReplaySplitManifest,
    role: ReplaySplitRole,
) -> tuple[str, str, str, int]:
    identities = _split_role_geometry_identities(split, role)
    geometry_set_digest = digest({"geometry_identities": sorted(identities)})
    prediction_map = {
        geometry: prediction
        for shard in cache.shards
        for geometry, prediction in zip(shard.geometry_identities, shard.prediction_label_identities, strict=True)
    }
    records = []
    for identity in identities:
        if identity not in prediction_map:
            raise TrainingDataInputError("Replay split geometry is absent from the pseudo-label prediction cache.")
        records.append((identity, prediction_map[identity]))
    label_set_digest = digest(
        {
            "namespace": ReplayLabelNamespace.FOUNDATION_PSEUDOLABEL.value,
            "records": [[g, p] for g, p in sorted(records)],
        }
    )
    logical = digest(
        {
            "schema": REPLAY_PSEUDOLABEL_VIEW_SCHEMA,
            "role": role.value,
            "configuration_count": len(identities),
            "geometry_set_digest": geometry_set_digest,
            "prediction_label_set_digest": label_set_digest,
            "source_geometry_set_digest": cache.source_geometry_set_digest,
            "prediction_cache_digest": cache.content_digest,
            "qualification_digest": qualification.content_digest,
            "split_manifest_digest": split.content_digest,
            "label_namespace": ReplayLabelNamespace.FOUNDATION_PSEUDOLABEL.value,
            "transport_fields": ["REF_energy", "REF_forces", "REF_stress"],
        }
    )
    return logical, geometry_set_digest, label_set_digest, len(identities)


def _load_pseudo_view_cache(output: Path, *, expected_logical_digest: str) -> ReplayPseudolabelViewArtifact | None:
    receipt = output.with_name(output.name + ".replay.json")
    if not output.is_file() or not receipt.is_file():
        return None
    try:
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        if payload.get("schema") != REPLAY_PSEUDOLABEL_VIEW_RECEIPT_SCHEMA:
            return None
        view = ReplayPseudolabelViewArtifact.from_dict(payload["view"])
        if view.path != str(output) or view.logical_digest != expected_logical_digest:
            return None
        if _sha256_file(output) != view.sha256:
            return None
        return view
    except Exception:
        return None


def _render_pseudo_frame(
    atoms: Any,
    *,
    geometry_identity: str,
    role: ReplaySplitRole,
    source_index: int,
    cache: ReplayFoundationPredictionCache,
    cache_digest: str,
    inference_digest: str,
    qualification_digest: str,
    split_digest: str,
    reader: _ReplayPredictionShardReader,
) -> Any:
    energy, forces, stress, prediction_identity = reader.prediction(geometry_identity)
    frame = atoms.copy()
    frame.calc = None
    for key in (
        "energy", "REF_energy", "stress", "REF_stress", "virial", "virials", "REF_virial", "REF_virials",
        "corrected_total_energy",
    ):
        frame.info.pop(key, None)
    for key in ("forces", "REF_forces"):
        if key in frame.arrays:
            del frame.arrays[key]
    frame.info["REF_energy"] = energy
    frame.arrays["REF_forces"] = forces
    if stress is not None:
        frame.info["REF_stress"] = stress
    frame.info["replay_label_mode"] = ReplayLabelMode.FOUNDATION_PSEUDOLABEL.value
    frame.info["replay_label_namespace"] = ReplayLabelNamespace.FOUNDATION_PSEUDOLABEL.value
    frame.info["replay_geometry_identity"] = geometry_identity
    frame.info["replay_split_role"] = role.value
    frame.info["replay_source_index"] = int(source_index)
    frame.info["replay_pseudolabel_identity"] = prediction_identity
    frame.info["replay_pseudolabel_model_sha256"] = cache.prediction_policy.foundation_potential.sha256
    frame.info["replay_pseudolabel_foundation_head"] = cache.prediction_policy.foundation_potential.foundation_head
    frame.info["replay_pseudolabel_inference_digest"] = inference_digest
    frame.info["replay_pseudolabel_cache_digest"] = cache_digest
    frame.info["replay_pseudolabel_qualification_digest"] = qualification_digest
    frame.info["replay_split_manifest_digest"] = split_digest
    return frame


def materialize_replay_pseudolabel_views(
    source: ReplaySourceArtifact,
    cache: ReplayFoundationPredictionCache,
    qualification: ReplayPseudolabelQualification,
    split: ReplaySplitManifest,
    output_directory: str | Path,
    *,
    roles: Sequence[ReplaySplitRole | str] = (ReplaySplitRole.TRAIN, ReplaySplitRole.MONITOR),
    buffer_size: int = 64,
    max_resident_prediction_shards: int = 4,
    source_index: ReplaySourceIndex | None = None,
) -> dict[ReplaySplitRole, ReplayPseudolabelViewArtifact]:
    """Lazily materialize pseudo-label train/monitor views without model inference."""

    if int(buffer_size) <= 0 or int(max_resident_prediction_shards) <= 0:
        raise TrainingDataInputError("Replay pseudo-label materialization buffer/cache sizes must be positive.")
    requested: list[ReplaySplitRole] = []
    for value in roles:
        role = ReplaySplitRole(value)
        if role not in requested:
            requested.append(role)
    if not requested:
        return {}
    if source.geometry_set_digest != cache.source_geometry_set_digest:
        raise TrainingDataInputError("Replay source and pseudo-label cache geometry authorities differ.")
    if qualification.source_geometry_set_digest != source.geometry_set_digest:
        raise TrainingDataInputError("Replay pseudo-label qualification source authority mismatch.")
    if qualification.prediction_cache_digest != cache.content_digest:
        raise TrainingDataInputError("Replay pseudo-label qualification/cache authority mismatch.")
    if qualification.prediction_policy_digest != cache.prediction_policy.content_digest:
        raise TrainingDataInputError("Replay pseudo-label qualification prediction-policy mismatch.")
    if split.source_geometry_set_digest != source.geometry_set_digest:
        raise TrainingDataInputError("Replay pseudo-label split/source authority mismatch.")
    if split.qualification_authority_digest != qualification.content_digest:
        raise TrainingDataInputError("Replay pseudo-label split is not bound to the supplied qualification authority.")
    if split.eligible_geometry_set_digest != qualification.eligible_geometry_set_digest:
        raise TrainingDataInputError("Replay pseudo-label split eligible set differs from qualification authority.")

    output_root = Path(output_directory).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    outputs = {role: output_root / f"replay_{role.value}.pseudolabel.extxyz" for role in requested}
    expected = {role: _pseudo_view_expected(cache, qualification, split, role) for role in requested}
    results: dict[ReplaySplitRole, ReplayPseudolabelViewArtifact] = {}
    pending: list[ReplaySplitRole] = []
    for role in requested:
        cached = _load_pseudo_view_cache(outputs[role], expected_logical_digest=expected[role][0])
        if cached is None:
            pending.append(role)
        else:
            results[role] = cached
    if not pending:
        return results

    cache_digest = cache.content_digest
    inference_digest = cache.prediction_policy.foundation_inference.content_digest
    qualification_digest = qualification.content_digest
    split_digest = split.content_digest

    source_path = Path(source.path).expanduser().resolve()
    if not source_path.is_file() or _sha256_file(source_path) != source.sha256:
        raise TrainingDataInputError("Replay source file is missing or differs from its authenticated artifact.")
    try:
        from ase.io import iread
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required to materialize replay pseudo-label views.") from exc

    memberships = {role: set(_split_role_geometry_identities(split, role)) for role in pending}
    identity_role = {identity: role for role, identities in memberships.items() for identity in identities}
    pending_union = set(identity_role)
    temporary = {role: outputs[role].with_name(outputs[role].name + ".tmp") for role in pending}
    writers = {role: _BufferedReplayExtXYZWriter(temporary[role], buffer_size=int(buffer_size)) for role in pending}
    seen = {role: set() for role in pending}
    reader = _ReplayPredictionShardReader(cache, max_resident_shards=int(max_resident_prediction_shards))
    if source_index is None:
        frame_iterator = enumerate(iread(source_path, index=":", format="extxyz"))
    else:
        selected_indices = replay_source_indices_for_identities(source, pending_union)
        frame_iterator = iter_indexed_replay_frames(
            source, source_index, source_indices=selected_indices
        )
    try:
        for source_frame_index, atoms in frame_iterator:
            identity = source.geometry_identities[source_frame_index]
            matched = identity_role.get(identity)
            if matched is None:
                continue
            if identity in seen[matched]:
                raise TrainingDataInputError("Replay source yielded duplicate geometry during pseudo-label materialization.")
            writers[matched].add(
                _render_pseudo_frame(
                    atoms,
                    geometry_identity=identity,
                    role=matched,
                    source_index=source_frame_index,
                    cache=cache,
                    cache_digest=cache_digest,
                    inference_digest=inference_digest,
                    qualification_digest=qualification_digest,
                    split_digest=split_digest,
                    reader=reader,
                )
            )
            seen[matched].add(identity)
        for writer in writers.values():
            writer.close()
        for role in pending:
            if seen[role] != memberships[role] or writers[role].count != len(memberships[role]):
                raise TrainingDataInputError(f"Pseudo-label {role.value} materialization membership mismatch.")
        for role in pending:
            temporary[role].replace(outputs[role])
            logical, geometry_set_digest, label_set_digest, count = expected[role]
            view = ReplayPseudolabelViewArtifact(
                role=role,
                path=str(outputs[role]),
                sha256=_sha256_file(outputs[role]),
                configuration_count=count,
                geometry_set_digest=geometry_set_digest,
                prediction_label_set_digest=label_set_digest,
                source_geometry_set_digest=source.geometry_set_digest,
                prediction_cache_digest=cache.content_digest,
                qualification_digest=qualification.content_digest,
                split_manifest_digest=split.content_digest,
            )
            if view.logical_digest != logical:
                raise TrainingDataInputError("Internal pseudo-label view logical-digest mismatch.")
            _atomic_write_json(
                outputs[role].with_name(outputs[role].name + ".replay.json"),
                {"schema": REPLAY_PSEUDOLABEL_VIEW_RECEIPT_SCHEMA, "view": view.to_dict()},
            )
            results[role] = view
    except Exception:
        for writer in writers.values():
            try:
                writer._buffer.clear()
            except Exception:
                pass
        for path in temporary.values():
            path.unlink(missing_ok=True)
        raise
    return results


__all__ = [
    "REPLAY_FOUNDATION_PREDICTION_POLICY_SCHEMA",
    "REPLAY_FOUNDATION_PREDICTION_SHARD_SCHEMA",
    "REPLAY_FOUNDATION_PREDICTION_CACHE_SCHEMA",
    "REPLAY_FOUNDATION_AUDIT_CACHE_SCHEMA",
    "REPLAY_PSEUDOLABEL_QUALIFICATION_POLICY_SCHEMA",
    "REPLAY_PSEUDOLABEL_QUALIFICATION_SCHEMA",
    "REPLAY_PSEUDOLABEL_VIEW_SCHEMA",
    "REPLAY_PSEUDOLABEL_VIEW_RECEIPT_SCHEMA",
    "DEFAULT_REPLAY_MAX_FORCE_EV_PER_A",
    "DEFAULT_REPLAY_MAX_FORCE_RMS_EV_PER_A",
    "DEFAULT_REPLAY_MAX_STRESS_EV_PER_A3",
    "DEFAULT_REPLAY_PREDICTION_BATCH_SIZE",
    "DEFAULT_REPLAY_PREDICTION_SHARD_SIZE",
    "ReplayFoundationPredictionPolicy",
    "ReplayFoundationPredictionShard",
    "ReplayFoundationPredictionCache",
    "ReplayPseudolabelQualificationPolicy",
    "ReplayPseudolabelQualification",
    "ReplayPseudolabelViewArtifact",
    "replay_foundation_prediction_cache_key",
    "build_replay_foundation_prediction_cache",
    "build_replay_pseudolabel_qualification",
    "materialize_replay_pseudolabel_views",
]
