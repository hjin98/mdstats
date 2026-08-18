"""Lightweight full-resolution LTA partition states for MLFF-DATA4."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import hashlib
import struct
from ase.data import chemical_symbols

from .resources import isolated_process_map
from .progress_timing import format_progress_fraction
from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .eligibility import FrameEligibilityState
from .raw_features import minimum_image_displacements

LTA_RING_DEFINITION_SCHEMA = "mdstats.lta-ring-definition.v1"
LTA_PARTITION_PROFILE_POLICY_SCHEMA = "mdstats.lta-partition-profile-policy.v1"
LTA_MOBILE_SITE_STATE_SCHEMA = "mdstats.lta-mobile-site-state.v1"
LTA_FRAME_PARTITION_RECORD_SCHEMA = "mdstats.lta-frame-partition-record.v1"
LTA_PARTITION_FEATURE_CATALOG_SCHEMA = "mdstats.lta-partition-feature-catalog.v2"
LTA_PARTITION_FEATURE_CATALOG_LEGACY_SCHEMA = "mdstats.lta-partition-feature-catalog.v1"
LTA_PARTITION_PROFILE_POLICY_VERSION = "mdstats.mlff-data4.lta-partition-profile.2026-07.v1"


class LtaSiteClass(str, Enum):
    RING_4_ON_CENTER = "ring_4_on_center"
    RING_4_OFF_CENTER = "ring_4_off_center"
    RING_6_ON_CENTER = "ring_6_on_center"
    RING_6_OFF_CENTER = "ring_6_off_center"
    RING_8_ON_CENTER = "ring_8_on_center"
    RING_8_OFF_CENTER = "ring_8_off_center"
    UNASSIGNED = "unassigned"
    UNRESOLVED = "unresolved"


class LtaProfileStatus(str, Enum):
    RESOLVED = "resolved"
    PARTIAL = "partial"
    UNRESOLVED = "unresolved"


def _positive(value: float, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise TrainingDataInputError(f"{name} must be finite and positive.")
    return result


def _mapping_tuple(mapping: Mapping[int, float], *, name: str) -> tuple[tuple[int, float], ...]:
    result = tuple(sorted((int(key), _positive(value, name=name)) for key, value in mapping.items()))
    if any(key <= 0 for key, _ in result):
        raise TrainingDataInputError(f"{name} keys must be positive integers.")
    return result


@dataclass(frozen=True, slots=True)
class LtaRingDefinition:
    ring_id: str
    ring_size: int
    framework_atom_indices: tuple[int, ...]
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.ring_id.strip():
            raise TrainingDataInputError("ring_id must be non-empty.")
        if self.ring_size not in {4, 6, 8}:
            raise TrainingDataInputError("LTA ring_size must be 4, 6, or 8.")
        indices = tuple(int(v) for v in self.framework_atom_indices)
        if len(indices) != self.ring_size or len(set(indices)) != len(indices) or any(v < 0 for v in indices):
            raise TrainingDataInputError("Ring indices must be unique, nonnegative, and match ring_size.")
        object.__setattr__(self, "framework_atom_indices", indices)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LTA_RING_DEFINITION_SCHEMA,
            "ring_id": self.ring_id,
            "ring_size": self.ring_size,
            "framework_atom_indices": list(self.framework_atom_indices),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(payload)
            object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LtaRingDefinition":
        if payload.get("schema") != LTA_RING_DEFINITION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported LTA ring-definition schema.")
        result = cls(
            ring_id=str(payload["ring_id"]),
            ring_size=int(payload["ring_size"]),
            framework_atom_indices=tuple(int(v) for v in payload["framework_atom_indices"]),
        )
        supplied_digest = payload.get("content_digest")
        if supplied_digest is not None and supplied_digest != result.content_digest:
            raise TrainingDataSerializationError("LTA ring-definition digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class LtaPartitionProfilePolicy:
    ring_definitions: tuple[LtaRingDefinition, ...] = ()
    framework_atomic_numbers: tuple[int, ...] = (8, 13, 14)
    mobile_atomic_numbers: tuple[int, ...] = (3, 11, 19)
    framework_to_oxygen_cutoffs_angstrom: tuple[tuple[int, float], ...] = ((13, 2.35), (14, 2.20))
    mobile_to_oxygen_cutoffs_angstrom: tuple[tuple[int, float], ...] = ((3, 2.85), (11, 3.35), (19, 3.75))
    maximum_ring_center_radius_angstrom: tuple[tuple[int, float], ...] = ((4, 3.2), (6, 4.2), (8, 5.2))
    on_center_radial_threshold_angstrom: tuple[tuple[int, float], ...] = ((4, 0.80), (6, 1.10), (8, 1.60))
    ring_crossing_plane_tolerance_angstrom: float = 0.75
    require_tetrahedral_coordination: int = 4
    require_oxygen_framework_coordination: int = 2
    policy_version: str = LTA_PARTITION_PROFILE_POLICY_VERSION

    def __post_init__(self) -> None:
        rings = tuple(sorted(self.ring_definitions, key=lambda item: item.ring_id))
        if len({item.ring_id for item in rings}) != len(rings):
            raise TrainingDataInputError("LTA ring IDs must be unique.")
        framework = tuple(sorted(set(int(v) for v in self.framework_atomic_numbers)))
        mobile = tuple(sorted(set(int(v) for v in self.mobile_atomic_numbers)))
        if any(v <= 0 for v in framework + mobile) or set(framework) & set(mobile):
            raise TrainingDataInputError("Framework/mobile atomic numbers must be positive and disjoint.")
        object.__setattr__(self, "ring_definitions", rings)
        object.__setattr__(self, "framework_atomic_numbers", framework)
        object.__setattr__(self, "mobile_atomic_numbers", mobile)
        for name in (
            "framework_to_oxygen_cutoffs_angstrom",
            "mobile_to_oxygen_cutoffs_angstrom",
            "maximum_ring_center_radius_angstrom",
            "on_center_radial_threshold_angstrom",
        ):
            value = _mapping_tuple(dict(getattr(self, name)), name=name)
            object.__setattr__(self, name, value)
        if set(dict(self.maximum_ring_center_radius_angstrom)) != {4, 6, 8}:
            raise TrainingDataInputError("Ring-center radii must define 4, 6, and 8 rings.")
        if set(dict(self.on_center_radial_threshold_angstrom)) != {4, 6, 8}:
            raise TrainingDataInputError("On-center thresholds must define 4, 6, and 8 rings.")
        object.__setattr__(
            self,
            "ring_crossing_plane_tolerance_angstrom",
            _positive(self.ring_crossing_plane_tolerance_angstrom, name="ring_crossing_plane_tolerance_angstrom"),
        )
        if self.require_tetrahedral_coordination <= 0 or self.require_oxygen_framework_coordination <= 0:
            raise TrainingDataInputError("Framework coordination requirements must be positive.")
        if not self.policy_version.strip():
            raise TrainingDataInputError("policy_version must be non-empty.")

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LTA_PARTITION_PROFILE_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "ring_definitions": [item.to_dict() for item in self.ring_definitions],
            "framework_atomic_numbers": list(self.framework_atomic_numbers),
            "mobile_atomic_numbers": list(self.mobile_atomic_numbers),
            "framework_to_oxygen_cutoffs_angstrom": {str(k): v for k, v in self.framework_to_oxygen_cutoffs_angstrom},
            "mobile_to_oxygen_cutoffs_angstrom": {str(k): v for k, v in self.mobile_to_oxygen_cutoffs_angstrom},
            "maximum_ring_center_radius_angstrom": {str(k): v for k, v in self.maximum_ring_center_radius_angstrom},
            "on_center_radial_threshold_angstrom": {str(k): v for k, v in self.on_center_radial_threshold_angstrom},
            "ring_crossing_plane_tolerance_angstrom": self.ring_crossing_plane_tolerance_angstrom,
            "require_tetrahedral_coordination": self.require_tetrahedral_coordination,
            "require_oxygen_framework_coordination": self.require_oxygen_framework_coordination,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LtaPartitionProfilePolicy":
        if payload.get("schema") != LTA_PARTITION_PROFILE_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported LTA partition-profile policy schema.")
        result = cls(
            ring_definitions=tuple(LtaRingDefinition.from_dict(item) for item in payload.get("ring_definitions", ())),
            framework_atomic_numbers=tuple(int(v) for v in payload["framework_atomic_numbers"]),
            mobile_atomic_numbers=tuple(int(v) for v in payload["mobile_atomic_numbers"]),
            framework_to_oxygen_cutoffs_angstrom=tuple((int(k), float(v)) for k, v in payload["framework_to_oxygen_cutoffs_angstrom"].items()),
            mobile_to_oxygen_cutoffs_angstrom=tuple((int(k), float(v)) for k, v in payload["mobile_to_oxygen_cutoffs_angstrom"].items()),
            maximum_ring_center_radius_angstrom=tuple((int(k), float(v)) for k, v in payload["maximum_ring_center_radius_angstrom"].items()),
            on_center_radial_threshold_angstrom=tuple((int(k), float(v)) for k, v in payload["on_center_radial_threshold_angstrom"].items()),
            ring_crossing_plane_tolerance_angstrom=float(payload["ring_crossing_plane_tolerance_angstrom"]),
            require_tetrahedral_coordination=int(payload["require_tetrahedral_coordination"]),
            require_oxygen_framework_coordination=int(payload["require_oxygen_framework_coordination"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("LTA partition-profile policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class LtaMobileSiteState:
    frame_uid: str
    atom_index: int
    atomic_number: int
    symbol: str
    ring_id: str | None
    ring_size: int | None
    site_class: LtaSiteClass
    ring_center_distance_angstrom: float | None
    signed_plane_distance_angstrom: float | None
    radial_distance_angstrom: float | None
    oxygen_coordination: int | None
    coordination_changed: bool
    site_changed: bool
    ring_crossing: bool
    warning_codes: tuple[str, ...] = ()
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "frame_uid", validate_digest(self.frame_uid, name="frame_uid"))
        if self.atom_index < 0 or self.atomic_number <= 0 or not self.symbol.strip():
            raise TrainingDataInputError("Invalid LTA mobile-site identity.")
        object.__setattr__(self, "site_class", LtaSiteClass(self.site_class))
        if (self.ring_id is None) != (self.ring_size is None):
            raise TrainingDataInputError("ring_id and ring_size must be present together.")
        if self.ring_size is not None and self.ring_size not in {4, 6, 8}:
            raise TrainingDataInputError("ring_size must be 4, 6, or 8.")
        for name in ("ring_center_distance_angstrom", "radial_distance_angstrom"):
            value = getattr(self, name)
            if value is not None and (not np.isfinite(float(value)) or float(value) < 0.0):
                raise TrainingDataInputError(f"{name} must be finite and nonnegative.")
        if self.signed_plane_distance_angstrom is not None and not np.isfinite(float(self.signed_plane_distance_angstrom)):
            raise TrainingDataInputError("signed_plane_distance_angstrom must be finite.")
        if self.oxygen_coordination is not None and self.oxygen_coordination < 0:
            raise TrainingDataInputError("oxygen_coordination must be nonnegative.")
        object.__setattr__(self, "warning_codes", tuple(sorted(set(str(v) for v in self.warning_codes))))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LTA_MOBILE_SITE_STATE_SCHEMA,
            "frame_uid": self.frame_uid,
            "atom_index": self.atom_index,
            "atomic_number": self.atomic_number,
            "symbol": self.symbol,
            "ring_id": self.ring_id,
            "ring_size": self.ring_size,
            "site_class": self.site_class.value,
            "ring_center_distance_angstrom": self.ring_center_distance_angstrom,
            "signed_plane_distance_angstrom": self.signed_plane_distance_angstrom,
            "radial_distance_angstrom": self.radial_distance_angstrom,
            "oxygen_coordination": self.oxygen_coordination,
            "coordination_changed": self.coordination_changed,
            "site_changed": self.site_changed,
            "ring_crossing": self.ring_crossing,
            "warning_codes": list(self.warning_codes),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(payload)
            object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LtaMobileSiteState":
        if payload.get("schema") != LTA_MOBILE_SITE_STATE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported LTA mobile-site-state schema.")
        result = cls(
            frame_uid=str(payload["frame_uid"]),
            atom_index=int(payload["atom_index"]),
            atomic_number=int(payload["atomic_number"]),
            symbol=str(payload["symbol"]),
            ring_id=None if payload.get("ring_id") is None else str(payload["ring_id"]),
            ring_size=None if payload.get("ring_size") is None else int(payload["ring_size"]),
            site_class=LtaSiteClass(payload["site_class"]),
            ring_center_distance_angstrom=None if payload.get("ring_center_distance_angstrom") is None else float(payload["ring_center_distance_angstrom"]),
            signed_plane_distance_angstrom=None if payload.get("signed_plane_distance_angstrom") is None else float(payload["signed_plane_distance_angstrom"]),
            radial_distance_angstrom=None if payload.get("radial_distance_angstrom") is None else float(payload["radial_distance_angstrom"]),
            oxygen_coordination=None if payload.get("oxygen_coordination") is None else int(payload["oxygen_coordination"]),
            coordination_changed=bool(payload["coordination_changed"]),
            site_changed=bool(payload["site_changed"]),
            ring_crossing=bool(payload["ring_crossing"]),
            warning_codes=tuple(str(v) for v in payload.get("warning_codes", ())),
        )
        supplied_digest = payload.get("content_digest")
        if supplied_digest is not None and supplied_digest != result.content_digest:
            raise TrainingDataSerializationError("LTA mobile-site-state digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class LtaFramePartitionRecord:
    frame_uid: str
    frame_record_digest: str
    policy_digest: str
    profile_status: LtaProfileStatus
    framework_integrity: bool | None
    site_classes_present: tuple[str, ...]
    ring_sizes_present: tuple[int, ...]
    coordination_change: bool
    site_change: bool
    ring_crossing: bool
    mobile_state_count: int
    warning_codes: tuple[str, ...] = ()
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("frame_uid", "frame_record_digest", "policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        object.__setattr__(self, "profile_status", LtaProfileStatus(self.profile_status))
        sites = tuple(sorted(set(str(v) for v in self.site_classes_present)))
        sizes = tuple(sorted(set(int(v) for v in self.ring_sizes_present)))
        if any(v not in {4, 6, 8} for v in sizes) or self.mobile_state_count < 0:
            raise TrainingDataInputError("Invalid LTA frame partition summary.")
        object.__setattr__(self, "site_classes_present", sites)
        object.__setattr__(self, "ring_sizes_present", sizes)
        object.__setattr__(self, "warning_codes", tuple(sorted(set(str(v) for v in self.warning_codes))))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LTA_FRAME_PARTITION_RECORD_SCHEMA,
            "frame_uid": self.frame_uid,
            "frame_record_digest": self.frame_record_digest,
            "policy_digest": self.policy_digest,
            "profile_status": self.profile_status.value,
            "framework_integrity": self.framework_integrity,
            "site_classes_present": list(self.site_classes_present),
            "ring_sizes_present": list(self.ring_sizes_present),
            "coordination_change": self.coordination_change,
            "site_change": self.site_change,
            "ring_crossing": self.ring_crossing,
            "mobile_state_count": self.mobile_state_count,
            "warning_codes": list(self.warning_codes),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(payload)
            object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LtaFramePartitionRecord":
        if payload.get("schema") != LTA_FRAME_PARTITION_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported LTA frame-partition schema.")
        result = cls(
            frame_uid=str(payload["frame_uid"]),
            frame_record_digest=str(payload["frame_record_digest"]),
            policy_digest=str(payload["policy_digest"]),
            profile_status=LtaProfileStatus(payload["profile_status"]),
            framework_integrity=payload.get("framework_integrity"),
            site_classes_present=tuple(str(v) for v in payload.get("site_classes_present", ())),
            ring_sizes_present=tuple(int(v) for v in payload.get("ring_sizes_present", ())),
            coordination_change=bool(payload["coordination_change"]),
            site_change=bool(payload["site_change"]),
            ring_crossing=bool(payload["ring_crossing"]),
            mobile_state_count=int(payload["mobile_state_count"]),
            warning_codes=tuple(str(v) for v in payload.get("warning_codes", ())),
        )
        supplied_digest = payload.get("content_digest")
        if supplied_digest is not None and supplied_digest != result.content_digest:
            raise TrainingDataSerializationError("LTA frame-partition digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class LtaPartitionFeatureCatalog:
    dataset_id: str
    frame_catalog_digest: str
    policy: LtaPartitionProfilePolicy
    frame_records: tuple[LtaFramePartitionRecord, ...]
    mobile_states: tuple[LtaMobileSiteState, ...]
    _by_frame_uid: Mapping[str, LtaFramePartitionRecord] = field(default_factory=dict, init=False, repr=False, compare=False)
    _states_by_frame_uid: Mapping[str, tuple[LtaMobileSiteState, ...]] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)
    _frame_records_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)
    _mobile_states_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "frame_catalog_digest", validate_digest(self.frame_catalog_digest, name="frame_catalog_digest"))
        frames = tuple(sorted(self.frame_records, key=lambda item: item.frame_uid))
        states = tuple(sorted(self.mobile_states, key=lambda item: (item.frame_uid, item.atom_index)))
        if len({item.frame_uid for item in frames}) != len(frames):
            raise TrainingDataInputError("LTA frame records must have unique UIDs.")
        if any(item.policy_digest != self.policy.policy_digest for item in frames):
            raise TrainingDataInputError("LTA frame policy mismatch.")
        frame_uids = {item.frame_uid for item in frames}
        if any(item.frame_uid not in frame_uids for item in states):
            raise TrainingDataInputError("LTA mobile state references an unknown frame.")
        object.__setattr__(self, "frame_records", frames)
        object.__setattr__(self, "mobile_states", states)
        object.__setattr__(self, "_by_frame_uid", {item.frame_uid: item for item in frames})
        grouped: dict[str, list[LtaMobileSiteState]] = {}
        for item in states:
            grouped.setdefault(item.frame_uid, []).append(item)
        object.__setattr__(self, "_states_by_frame_uid", {key: tuple(value) for key, value in grouped.items()})

    def for_frame(self, frame_uid: str) -> LtaFramePartitionRecord:
        try:
            return self._by_frame_uid[frame_uid]
        except KeyError:
            raise KeyError(frame_uid) from None

    def states_for_frame(self, frame_uid: str) -> tuple[LtaMobileSiteState, ...]:
        return self._states_by_frame_uid.get(frame_uid, ())

    @staticmethod
    def _hash_text(hasher: "hashlib._Hash", value: str | None) -> None:
        if value is None:
            hasher.update(b"\x00")
            return
        encoded = value.encode("utf-8")
        hasher.update(b"\x01")
        hasher.update(struct.pack(">I", len(encoded)))
        hasher.update(encoded)

    @staticmethod
    def _hash_optional_int(hasher: "hashlib._Hash", value: int | None) -> None:
        if value is None:
            hasher.update(b"\x00")
        else:
            hasher.update(b"\x01")
            hasher.update(struct.pack(">q", int(value)))

    @staticmethod
    def _hash_optional_float(hasher: "hashlib._Hash", value: float | None) -> None:
        if value is None:
            hasher.update(b"\x00")
        else:
            hasher.update(b"\x01")
            hasher.update(struct.pack(">d", float(value)))

    def _frame_records_digest(self) -> str:
        cached = self._frame_records_digest_cache
        if cached is None:
            hasher = hashlib.sha256(b"mdstats.lta-frame-record-sequence.v1\x00")
            for item in self.frame_records:
                hasher.update(bytes.fromhex(item.content_digest))
            cached = hasher.hexdigest()
            object.__setattr__(self, "_frame_records_digest_cache", cached)
        return cached

    def _mobile_states_digest(self) -> str:
        cached = self._mobile_states_digest_cache
        if cached is not None:
            return cached
        hasher = hashlib.sha256(b"mdstats.lta-mobile-state-sequence.v1\x00")
        for item in self.mobile_states:
            self._hash_text(hasher, item.frame_uid)
            hasher.update(struct.pack(">q", item.atom_index))
            hasher.update(struct.pack(">q", item.atomic_number))
            self._hash_text(hasher, item.symbol)
            self._hash_text(hasher, item.ring_id)
            self._hash_optional_int(hasher, item.ring_size)
            self._hash_text(hasher, item.site_class.value)
            self._hash_optional_float(hasher, item.ring_center_distance_angstrom)
            self._hash_optional_float(hasher, item.signed_plane_distance_angstrom)
            self._hash_optional_float(hasher, item.radial_distance_angstrom)
            self._hash_optional_int(hasher, item.oxygen_coordination)
            hasher.update(bytes((int(item.coordination_changed), int(item.site_changed), int(item.ring_crossing))))
            hasher.update(struct.pack(">I", len(item.warning_codes)))
            for warning in item.warning_codes:
                self._hash_text(hasher, warning)
        cached = hasher.hexdigest()
        object.__setattr__(self, "_mobile_states_digest_cache", cached)
        return cached

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": LTA_PARTITION_FEATURE_CATALOG_SCHEMA,
            "dataset_id": self.dataset_id,
            "frame_catalog_digest": self.frame_catalog_digest,
            "policy_digest": self.policy.policy_digest,
            "frame_record_count": len(self.frame_records),
            "frame_records_digest": self._frame_records_digest(),
            "mobile_state_count": len(self.mobile_states),
            "mobile_states_digest": self._mobile_states_digest(),
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LTA_PARTITION_FEATURE_CATALOG_SCHEMA,
            "dataset_id": self.dataset_id,
            "frame_catalog_digest": self.frame_catalog_digest,
            "policy": self.policy.to_dict(),
            "frame_records": [item.to_dict() for item in self.frame_records],
            "mobile_states": [item.to_dict() for item in self.mobile_states],
        }

    def _legacy_payload(self) -> dict[str, Any]:
        payload = self._payload()
        payload["schema"] = LTA_PARTITION_FEATURE_CATALOG_LEGACY_SCHEMA
        return payload

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._identity_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LtaPartitionFeatureCatalog":
        schema = payload.get("schema")
        if schema not in {LTA_PARTITION_FEATURE_CATALOG_SCHEMA, LTA_PARTITION_FEATURE_CATALOG_LEGACY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported LTA partition-feature-catalog schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            policy=LtaPartitionProfilePolicy.from_dict(payload["policy"]),
            frame_records=tuple(LtaFramePartitionRecord.from_dict(item) for item in payload.get("frame_records", ())),
            mobile_states=tuple(LtaMobileSiteState.from_dict(item) for item in payload.get("mobile_states", ())),
        )
        supplied_digest = payload.get("content_digest")
        expected_digest = (
            result.content_digest
            if schema == LTA_PARTITION_FEATURE_CATALOG_SCHEMA
            else digest(result._legacy_payload())
        )
        if supplied_digest is not None and supplied_digest != expected_digest:
            raise TrainingDataSerializationError("LTA partition-feature-catalog digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class _RingGeometry:
    definition: LtaRingDefinition
    center_fractional: np.ndarray
    center_cartesian: np.ndarray
    normal: np.ndarray


def _ring_geometry(
    definition: LtaRingDefinition,
    fractional_positions: np.ndarray,
    cell: np.ndarray,
    pbc: np.ndarray,
) -> _RingGeometry | None:
    indices = np.asarray(definition.framework_atom_indices, dtype=np.int64)
    if np.any(indices >= fractional_positions.shape[0]):
        raise TrainingDataInputError(f"Ring {definition.ring_id!r} atom index is out of range.")
    ring_fractional = np.asarray(fractional_positions[indices], dtype=np.float64)
    anchor = ring_fractional[0]
    delta = ring_fractional - anchor
    for axis in range(3):
        if bool(pbc[axis]):
            delta[:, axis] -= np.rint(delta[:, axis])
    unwrapped_fractional = anchor + delta
    cartesian = unwrapped_fractional @ cell
    center_cartesian = np.mean(cartesian, axis=0)
    centered = cartesian - center_cartesian
    if np.linalg.matrix_rank(centered, tol=1.0e-10) < 2:
        return None
    _, _, vh = np.linalg.svd(centered, full_matrices=False)
    normal = np.asarray(vh[-1], dtype=np.float64)
    norm = float(np.linalg.norm(normal))
    if not np.isfinite(norm) or norm <= 0.0:
        return None
    normal /= norm
    pivot = int(np.argmax(np.abs(normal)))
    if normal[pivot] < 0.0:
        normal = -normal
    center_fractional = center_cartesian @ np.linalg.inv(cell)
    return _RingGeometry(definition, center_fractional, center_cartesian, normal)


def _oxygen_coordination(
    atom_index: int,
    atomic_number: int,
    atomic_numbers: np.ndarray,
    fractional_positions: np.ndarray,
    cell: np.ndarray,
    pbc: np.ndarray,
    cutoff_map: Mapping[int, float],
) -> int | None:
    cutoff = cutoff_map.get(int(atomic_number))
    oxygen_indices = np.flatnonzero(atomic_numbers == 8)
    if cutoff is None or oxygen_indices.size == 0:
        return None
    displacements = minimum_image_displacements(
        fractional_positions[[atom_index]],
        fractional_positions[oxygen_indices],
        cell=cell,
        pbc=pbc,
    )[0]
    return int(np.sum(np.linalg.norm(displacements, axis=1) <= cutoff))


def _framework_integrity(
    atomic_numbers: np.ndarray,
    fractional_positions: np.ndarray,
    cell: np.ndarray,
    pbc: np.ndarray,
    policy: LtaPartitionProfilePolicy,
) -> tuple[bool | None, tuple[str, ...]]:
    oxygen = np.flatnonzero(atomic_numbers == 8)
    t_indices = np.flatnonzero(np.isin(atomic_numbers, [13, 14]))
    warnings: list[str] = []
    if oxygen.size == 0 or t_indices.size == 0:
        return None, ("required_framework_species_absent",)
    t_cutoffs = dict(policy.framework_to_oxygen_cutoffs_angstrom)
    oxygen_counts = np.zeros(oxygen.size, dtype=np.int64)
    integrity = True
    for atom_index in t_indices:
        atomic_number = int(atomic_numbers[atom_index])
        cutoff = t_cutoffs.get(atomic_number)
        if cutoff is None:
            warnings.append(f"framework_cutoff_absent:{atomic_number}")
            return None, tuple(sorted(set(warnings)))
        distances = np.linalg.norm(
            minimum_image_displacements(
                fractional_positions[[atom_index]],
                fractional_positions[oxygen],
                cell=cell,
                pbc=pbc,
            )[0],
            axis=1,
        )
        neighbors = distances <= cutoff
        if int(np.sum(neighbors)) != policy.require_tetrahedral_coordination:
            integrity = False
        oxygen_counts += neighbors.astype(np.int64)
    if np.any(oxygen_counts != policy.require_oxygen_framework_coordination):
        integrity = False
    return integrity, tuple(sorted(set(warnings)))


def _mobile_oxygen_coordination_vectorized(
    mobile_indices: np.ndarray,
    oxygen_indices: np.ndarray,
    atomic_numbers: np.ndarray,
    fractional_positions: np.ndarray,
    cell: np.ndarray,
    pbc: np.ndarray,
    cutoff_map: Mapping[int, float],
) -> dict[int, int | None]:
    """Compute all mobile-ion oxygen coordinations in one MIC tensor."""

    if mobile_indices.size == 0:
        return {}
    if oxygen_indices.size == 0:
        return {int(index): None for index in mobile_indices}
    displacement = minimum_image_displacements(
        fractional_positions[mobile_indices],
        fractional_positions[oxygen_indices],
        cell=cell,
        pbc=pbc,
    )
    distances = np.linalg.norm(displacement, axis=-1)
    result: dict[int, int | None] = {}
    for row, atom_index_value in enumerate(mobile_indices):
        atom_index = int(atom_index_value)
        cutoff = cutoff_map.get(int(atomic_numbers[atom_index]))
        result[atom_index] = None if cutoff is None else int(np.count_nonzero(distances[row] <= cutoff))
    return result


def _framework_integrity_vectorized(
    atomic_numbers: np.ndarray,
    fractional_positions: np.ndarray,
    cell: np.ndarray,
    pbc: np.ndarray,
    policy: LtaPartitionProfilePolicy,
    oxygen_indices: np.ndarray,
    tetrahedral_indices: np.ndarray,
) -> tuple[bool | None, tuple[str, ...]]:
    """Assess all T--O bonds using one vectorized minimum-image calculation."""

    if oxygen_indices.size == 0 or tetrahedral_indices.size == 0:
        return None, ("required_framework_species_absent",)
    cutoff_map = dict(policy.framework_to_oxygen_cutoffs_angstrom)
    cutoffs = np.asarray(
        [cutoff_map.get(int(atomic_numbers[index]), np.nan) for index in tetrahedral_indices],
        dtype=np.float64,
    )
    if np.any(~np.isfinite(cutoffs)):
        missing = sorted({
            int(atomic_numbers[index])
            for index, cutoff in zip(tetrahedral_indices, cutoffs, strict=True)
            if not np.isfinite(cutoff)
        })
        return None, tuple(f"framework_cutoff_absent:{value}" for value in missing)
    displacement = minimum_image_displacements(
        fractional_positions[tetrahedral_indices],
        fractional_positions[oxygen_indices],
        cell=cell,
        pbc=pbc,
    )
    distances = np.linalg.norm(displacement, axis=-1)
    neighbors = distances <= cutoffs[:, None]
    tetrahedral_counts = np.count_nonzero(neighbors, axis=1)
    oxygen_counts = np.count_nonzero(neighbors, axis=0)
    integrity = bool(
        np.all(tetrahedral_counts == policy.require_tetrahedral_coordination)
        and np.all(oxygen_counts == policy.require_oxygen_framework_coordination)
    )
    return integrity, ()


def _site_class(ring_size: int, radial_distance: float, thresholds: Mapping[int, float]) -> LtaSiteClass:
    on_center = radial_distance <= thresholds[ring_size]
    return LtaSiteClass(f"ring_{ring_size}_{'on_center' if on_center else 'off_center'}")



def _assign_mobile_sites_vectorized(
    mobile_indices: np.ndarray,
    fractional: np.ndarray,
    cell: np.ndarray,
    pbc: np.ndarray,
    geometries: Sequence[_RingGeometry],
    radius_map: Mapping[int, float],
    threshold_map: Mapping[int, float],
) -> tuple[list[str | None], np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[LtaSiteClass]]:
    """Assign all mobile atoms to rings with one broadcasted MIC calculation."""

    count = int(mobile_indices.size)
    ring_ids: list[str | None] = [None] * count
    ring_sizes = np.full(count, -1, dtype=np.int16)
    distances = np.full(count, np.nan, dtype=np.float64)
    signed = np.full(count, np.nan, dtype=np.float64)
    radial = np.full(count, np.nan, dtype=np.float64)
    classes = [LtaSiteClass.UNASSIGNED] * count
    if count == 0 or not geometries:
        return ring_ids, ring_sizes, distances, signed, radial, classes

    ordered = sorted(geometries, key=lambda item: item.definition.ring_id)
    centers = np.stack([item.center_fractional for item in ordered], axis=0)
    normals = np.stack([item.normal for item in ordered], axis=0)
    sizes = np.asarray([item.definition.ring_size for item in ordered], dtype=np.int16)
    radii = np.asarray([radius_map[int(value)] for value in sizes], dtype=np.float64)
    mobile_fractional = np.asarray(fractional[mobile_indices], dtype=np.float64)
    delta_fractional = mobile_fractional[:, None, :] - centers[None, :, :]
    for axis in range(3):
        if bool(pbc[axis]):
            delta_fractional[..., axis] -= np.rint(delta_fractional[..., axis])
    delta_cartesian = delta_fractional @ cell
    all_distances = np.linalg.norm(delta_cartesian, axis=2)
    valid = all_distances <= radii[None, :]
    masked = np.where(valid, all_distances, np.inf)
    minimum = np.min(masked, axis=1)
    assigned = np.isfinite(minimum)
    # Preserve the original deterministic 1e-12 tie rule: ordered ring IDs
    # make argmax select the lexicographically first candidate.
    candidates = valid & (all_distances <= minimum[:, None] + 1.0e-12)
    selected = np.argmax(candidates, axis=1)
    rows = np.flatnonzero(assigned)
    if rows.size:
        columns = selected[rows]
        chosen_delta = delta_cartesian[rows, columns]
        chosen_normal = normals[columns]
        chosen_signed = np.einsum("ij,ij->i", chosen_delta, chosen_normal)
        chosen_radial = np.linalg.norm(
            chosen_delta - chosen_signed[:, None] * chosen_normal, axis=1
        )
        for local, row in enumerate(rows.tolist()):
            column = int(columns[local])
            size = int(sizes[column])
            ring_ids[row] = ordered[column].definition.ring_id
            ring_sizes[row] = size
            distances[row] = all_distances[row, column]
            signed[row] = chosen_signed[local]
            radial[row] = chosen_radial[local]
            classes[row] = _site_class(size, float(chosen_radial[local]), threshold_map)
    return ring_ids, ring_sizes, distances, signed, radial, classes


def _build_lta_features_for_run(task: tuple[Any, ...]) -> tuple[str, tuple[LtaFramePartitionRecord, ...], tuple[LtaMobileSiteState, ...]]:
    run_id, data, frame_by_source_index, decision_by_uid, active = task
    atomic_numbers = np.asarray(data.atomic_numbers, dtype=np.int32)
    pbc = np.asarray(data.pbc, dtype=np.bool_)
    oxygen_indices = np.flatnonzero(atomic_numbers == 8)
    tetrahedral_indices = np.flatnonzero(np.isin(atomic_numbers, (13, 14)))
    mobile_indices = np.flatnonzero(np.isin(atomic_numbers, active.mobile_atomic_numbers))
    order = np.argsort(np.asarray(data.source_frame_indices, dtype=np.int64), kind="stable")
    radius_map = dict(active.maximum_ring_center_radius_angstrom)
    threshold_map = dict(active.on_center_radial_threshold_angstrom)
    mobile_cutoffs = dict(active.mobile_to_oxygen_cutoffs_angstrom)
    previous: dict[int, LtaMobileSiteState] = {}
    previous_source_index: int | None = None
    mobile_states: list[LtaMobileSiteState] = []
    frame_records: list[LtaFramePartitionRecord] = []
    for local_index_value in order:
        local_index = int(local_index_value)
        source_index = int(data.source_frame_indices[local_index])
        frame = frame_by_source_index[source_index]
        decision = decision_by_uid[frame.frame_uid]
        fractional = np.asarray(data.fractional_positions[local_index], dtype=np.float64)
        cell = np.asarray(data.cells_angstrom[local_index], dtype=np.float64)
        warnings: list[str] = []
        geometries: list[_RingGeometry] = []
        for definition in active.ring_definitions:
            geometry = _ring_geometry(definition, fractional, cell, pbc)
            if geometry is None:
                warnings.append(f"ring_geometry_unresolved:{definition.ring_id}")
            else:
                geometries.append(geometry)
        framework_integrity, framework_warnings = _framework_integrity_vectorized(
            atomic_numbers, fractional, cell, pbc, active,
            oxygen_indices, tetrahedral_indices,
        )
        warnings.extend(framework_warnings)
        current: dict[int, LtaMobileSiteState] = {}
        coordination_by_atom = _mobile_oxygen_coordination_vectorized(
            mobile_indices, oxygen_indices, atomic_numbers, fractional, cell, pbc, mobile_cutoffs
        )
        (
            assigned_ring_ids, assigned_ring_sizes, assigned_distances,
            assigned_signed, assigned_radial, assigned_classes,
        ) = _assign_mobile_sites_vectorized(
            mobile_indices, fractional, cell, pbc, geometries, radius_map, threshold_map
        )
        consecutive = previous_source_index is not None and source_index == previous_source_index + 1
        for mobile_local, atom_index_value in enumerate(mobile_indices):
            atom_index = int(atom_index_value)
            atomic_number = int(atomic_numbers[atom_index])
            coordination = coordination_by_atom[atom_index]
            state_warnings: list[str] = []
            if not active.ring_definitions:
                site_class = LtaSiteClass.UNRESOLVED
                ring_id = None
                ring_size = None
                signed = radial = distance_value = None
                state_warnings.append("ring_definitions_absent")
            elif assigned_ring_ids[mobile_local] is None:
                site_class = LtaSiteClass.UNASSIGNED
                ring_id = None
                ring_size = None
                signed = radial = distance_value = None
                state_warnings.append("no_ring_within_assignment_radius")
            else:
                ring_id = assigned_ring_ids[mobile_local]
                ring_size = int(assigned_ring_sizes[mobile_local])
                signed = float(assigned_signed[mobile_local])
                radial = float(assigned_radial[mobile_local])
                distance_value = float(assigned_distances[mobile_local])
                site_class = assigned_classes[mobile_local]
            prior = previous.get(atom_index) if consecutive else None
            coordination_changed = (
                prior is not None
                and prior.oxygen_coordination is not None
                and coordination is not None
                and prior.oxygen_coordination != coordination
            )
            site_changed = (
                prior is not None
                and prior.ring_id is not None
                and ring_id is not None
                and prior.ring_id != ring_id
            )
            ring_crossing = (
                prior is not None
                and prior.ring_id is not None
                and prior.ring_id == ring_id
                and prior.signed_plane_distance_angstrom is not None
                and signed is not None
                and prior.signed_plane_distance_angstrom * signed < 0.0
                and min(abs(prior.signed_plane_distance_angstrom), abs(signed))
                <= active.ring_crossing_plane_tolerance_angstrom
            )
            state = LtaMobileSiteState(
                frame_uid=frame.frame_uid,
                atom_index=atom_index,
                atomic_number=atomic_number,
                symbol=chemical_symbols[atomic_number],
                ring_id=ring_id,
                ring_size=ring_size,
                site_class=site_class,
                ring_center_distance_angstrom=distance_value,
                signed_plane_distance_angstrom=signed,
                radial_distance_angstrom=radial,
                oxygen_coordination=coordination,
                coordination_changed=coordination_changed,
                site_changed=site_changed,
                ring_crossing=ring_crossing,
                warning_codes=tuple(state_warnings),
            )
            current[atom_index] = state
            mobile_states.append(state)

        if decision.state is not FrameEligibilityState.ELIGIBLE:
            warnings.append(f"frame_eligibility:{decision.state.value}")
        if not active.ring_definitions:
            profile_status = LtaProfileStatus.UNRESOLVED
        elif any(state.site_class in {LtaSiteClass.UNASSIGNED, LtaSiteClass.UNRESOLVED} for state in current.values()) or warnings:
            profile_status = LtaProfileStatus.PARTIAL
        else:
            profile_status = LtaProfileStatus.RESOLVED
        frame_records.append(
            LtaFramePartitionRecord(
                frame_uid=frame.frame_uid,
                frame_record_digest=frame.content_digest,
                policy_digest=active.policy_digest,
                profile_status=profile_status,
                framework_integrity=framework_integrity,
                site_classes_present=tuple(state.site_class.value for state in current.values()),
                ring_sizes_present=tuple(state.ring_size for state in current.values() if state.ring_size is not None),
                coordination_change=any(state.coordination_changed for state in current.values()),
                site_change=any(state.site_changed for state in current.values()),
                ring_crossing=any(state.ring_crossing for state in current.values()),
                mobile_state_count=len(current),
                warning_codes=tuple(warnings),
            )
        )
        previous = current
        previous_source_index = source_index
    return run_id, tuple(frame_records), tuple(mobile_states)




@dataclass(frozen=True, slots=True)
class _LtaRunColumns:
    run_id: str
    frame_uids: tuple[str, ...]
    frame_record_digests: tuple[str, ...]
    frame_profile_status: tuple[str, ...]
    framework_integrity: np.ndarray
    frame_warning_codes: tuple[tuple[str, ...], ...]
    mobile_atom_indices: np.ndarray
    mobile_atomic_numbers: np.ndarray
    ring_id_table: tuple[str, ...]
    ring_id_codes: np.ndarray
    ring_sizes: np.ndarray
    site_class_codes: np.ndarray
    distances: np.ndarray
    signed_distances: np.ndarray
    radial_distances: np.ndarray
    oxygen_coordination: np.ndarray
    coordination_changed: np.ndarray
    site_changed: np.ndarray
    ring_crossing: np.ndarray
    state_warning_codes: np.ndarray


_SITE_CLASS_TABLE = tuple(LtaSiteClass)
_SITE_CLASS_CODE = {value: index for index, value in enumerate(_SITE_CLASS_TABLE)}


def _build_lta_columns_for_run(task: tuple[Any, ...]) -> _LtaRunColumns:
    """Compute one run into compact columns suitable for process transfer."""

    run_id, data, frame_by_source_index, decision_by_uid, active = task
    atomic_numbers = np.asarray(data.atomic_numbers, dtype=np.int32)
    pbc = np.asarray(data.pbc, dtype=np.bool_)
    oxygen_indices = np.flatnonzero(atomic_numbers == 8)
    tetrahedral_indices = np.flatnonzero(np.isin(atomic_numbers, (13, 14)))
    mobile_indices = np.flatnonzero(np.isin(atomic_numbers, active.mobile_atomic_numbers))
    order = np.argsort(np.asarray(data.source_frame_indices, dtype=np.int64), kind="stable")
    frame_count = int(order.size)
    mobile_count = int(mobile_indices.size)
    radius_map = dict(active.maximum_ring_center_radius_angstrom)
    threshold_map = dict(active.on_center_radial_threshold_angstrom)
    mobile_cutoffs = dict(active.mobile_to_oxygen_cutoffs_angstrom)
    ring_id_table = tuple(sorted(definition.ring_id for definition in active.ring_definitions))
    ring_code = {value: index for index, value in enumerate(ring_id_table)}

    frame_uids: list[str] = []
    frame_digests: list[str] = []
    statuses: list[str] = []
    frame_warnings: list[tuple[str, ...]] = []
    framework_integrity = np.full(frame_count, -1, dtype=np.int8)
    ring_codes = np.full((frame_count, mobile_count), -1, dtype=np.int16)
    ring_sizes = np.full((frame_count, mobile_count), -1, dtype=np.int16)
    site_codes = np.full(
        (frame_count, mobile_count), _SITE_CLASS_CODE[LtaSiteClass.UNASSIGNED], dtype=np.int8
    )
    distances = np.full((frame_count, mobile_count), np.nan, dtype=np.float64)
    signed_values = np.full_like(distances, np.nan)
    radial_values = np.full_like(distances, np.nan)
    coordination = np.full((frame_count, mobile_count), -1, dtype=np.int16)
    coordination_changed = np.zeros((frame_count, mobile_count), dtype=np.bool_)
    site_changed = np.zeros((frame_count, mobile_count), dtype=np.bool_)
    ring_crossing = np.zeros((frame_count, mobile_count), dtype=np.bool_)
    state_warning_codes = np.zeros((frame_count, mobile_count), dtype=np.int8)

    previous_source_index: int | None = None
    previous_ring = np.full(mobile_count, -1, dtype=np.int16)
    previous_coordination = np.full(mobile_count, -1, dtype=np.int16)
    previous_signed = np.full(mobile_count, np.nan, dtype=np.float64)

    for frame_position, local_index_value in enumerate(order):
        local_index = int(local_index_value)
        source_index = int(data.source_frame_indices[local_index])
        frame = frame_by_source_index[source_index]
        decision = decision_by_uid[frame.frame_uid]
        fractional = np.asarray(data.fractional_positions[local_index], dtype=np.float64)
        cell = np.asarray(data.cells_angstrom[local_index], dtype=np.float64)
        warnings: list[str] = []
        geometries: list[_RingGeometry] = []
        for definition in active.ring_definitions:
            geometry = _ring_geometry(definition, fractional, cell, pbc)
            if geometry is None:
                warnings.append(f"ring_geometry_unresolved:{definition.ring_id}")
            else:
                geometries.append(geometry)
        integrity, integrity_warnings = _framework_integrity_vectorized(
            atomic_numbers, fractional, cell, pbc, active,
            oxygen_indices, tetrahedral_indices,
        )
        warnings.extend(integrity_warnings)
        framework_integrity[frame_position] = -1 if integrity is None else int(bool(integrity))
        coordination_by_atom = _mobile_oxygen_coordination_vectorized(
            mobile_indices, oxygen_indices, atomic_numbers, fractional, cell, pbc, mobile_cutoffs
        )
        (
            assigned_ring_ids, assigned_ring_sizes, assigned_distances,
            assigned_signed, assigned_radial, assigned_classes,
        ) = _assign_mobile_sites_vectorized(
            mobile_indices, fractional, cell, pbc, geometries, radius_map, threshold_map
        )
        current_ring = np.full(mobile_count, -1, dtype=np.int16)
        current_coord = np.full(mobile_count, -1, dtype=np.int16)
        current_signed = np.full(mobile_count, np.nan, dtype=np.float64)
        for mobile_local, atom_index_value in enumerate(mobile_indices):
            atom_index = int(atom_index_value)
            coord = coordination_by_atom[atom_index]
            if coord is not None:
                current_coord[mobile_local] = int(coord)
            if not active.ring_definitions:
                site_codes[frame_position, mobile_local] = _SITE_CLASS_CODE[LtaSiteClass.UNRESOLVED]
                state_warning_codes[frame_position, mobile_local] = 1
            elif assigned_ring_ids[mobile_local] is None:
                state_warning_codes[frame_position, mobile_local] = 2
            else:
                code = ring_code[str(assigned_ring_ids[mobile_local])]
                current_ring[mobile_local] = code
                ring_codes[frame_position, mobile_local] = code
                ring_sizes[frame_position, mobile_local] = int(assigned_ring_sizes[mobile_local])
                site_codes[frame_position, mobile_local] = _SITE_CLASS_CODE[assigned_classes[mobile_local]]
                distances[frame_position, mobile_local] = float(assigned_distances[mobile_local])
                signed_values[frame_position, mobile_local] = float(assigned_signed[mobile_local])
                radial_values[frame_position, mobile_local] = float(assigned_radial[mobile_local])
                current_signed[mobile_local] = float(assigned_signed[mobile_local])
            coordination[frame_position, mobile_local] = current_coord[mobile_local]

        consecutive = previous_source_index is not None and source_index == previous_source_index + 1
        if consecutive:
            coordination_changed[frame_position] = (
                (previous_coordination >= 0)
                & (current_coord >= 0)
                & (previous_coordination != current_coord)
            )
            site_changed[frame_position] = (
                (previous_ring >= 0) & (current_ring >= 0) & (previous_ring != current_ring)
            )
            same_ring = (previous_ring >= 0) & (previous_ring == current_ring)
            finite_signed = np.isfinite(previous_signed) & np.isfinite(current_signed)
            ring_crossing[frame_position] = (
                same_ring
                & finite_signed
                & (previous_signed * current_signed < 0.0)
                & (
                    np.minimum(np.abs(previous_signed), np.abs(current_signed))
                    <= active.ring_crossing_plane_tolerance_angstrom
                )
            )

        if decision.state is not FrameEligibilityState.ELIGIBLE:
            warnings.append(f"frame_eligibility:{decision.state.value}")
        if not active.ring_definitions:
            status = LtaProfileStatus.UNRESOLVED
        elif np.any(
            np.isin(
                site_codes[frame_position],
                (
                    _SITE_CLASS_CODE[LtaSiteClass.UNASSIGNED],
                    _SITE_CLASS_CODE[LtaSiteClass.UNRESOLVED],
                ),
            )
        ) or warnings:
            status = LtaProfileStatus.PARTIAL
        else:
            status = LtaProfileStatus.RESOLVED
        frame_uids.append(frame.frame_uid)
        frame_digests.append(frame.content_digest)
        statuses.append(status.value)
        frame_warnings.append(tuple(warnings))
        previous_source_index = source_index
        previous_ring = current_ring
        previous_coordination = current_coord
        previous_signed = current_signed

    return _LtaRunColumns(
        run_id=run_id,
        frame_uids=tuple(frame_uids),
        frame_record_digests=tuple(frame_digests),
        frame_profile_status=tuple(statuses),
        framework_integrity=framework_integrity,
        frame_warning_codes=tuple(frame_warnings),
        mobile_atom_indices=np.asarray(mobile_indices, dtype=np.int32),
        mobile_atomic_numbers=np.asarray(atomic_numbers[mobile_indices], dtype=np.int16),
        ring_id_table=ring_id_table,
        ring_id_codes=ring_codes,
        ring_sizes=ring_sizes,
        site_class_codes=site_codes,
        distances=distances,
        signed_distances=signed_values,
        radial_distances=radial_values,
        oxygen_coordination=coordination,
        coordination_changed=coordination_changed,
        site_changed=site_changed,
        ring_crossing=ring_crossing,
        state_warning_codes=state_warning_codes,
    )


def _materialize_lta_columns(
    columns: _LtaRunColumns, policy: LtaPartitionProfilePolicy
) -> tuple[tuple[LtaFramePartitionRecord, ...], tuple[LtaMobileSiteState, ...]]:
    frame_records: list[LtaFramePartitionRecord] = []
    states: list[LtaMobileSiteState] = []
    frame_count, mobile_count = columns.ring_id_codes.shape
    for frame_index in range(frame_count):
        frame_uid = columns.frame_uids[frame_index]
        frame_states: list[LtaMobileSiteState] = []
        for mobile_index in range(mobile_count):
            ring_code = int(columns.ring_id_codes[frame_index, mobile_index])
            ring_size_value = int(columns.ring_sizes[frame_index, mobile_index])
            warning_code = int(columns.state_warning_codes[frame_index, mobile_index])
            warning_codes = (
                () if warning_code == 0
                else (("ring_definitions_absent",) if warning_code == 1 else ("no_ring_within_assignment_radius",))
            )
            coordination_value = int(columns.oxygen_coordination[frame_index, mobile_index])
            state = LtaMobileSiteState(
                frame_uid=frame_uid,
                atom_index=int(columns.mobile_atom_indices[mobile_index]),
                atomic_number=int(columns.mobile_atomic_numbers[mobile_index]),
                symbol=chemical_symbols[int(columns.mobile_atomic_numbers[mobile_index])],
                ring_id=None if ring_code < 0 else columns.ring_id_table[ring_code],
                ring_size=None if ring_size_value < 0 else ring_size_value,
                site_class=_SITE_CLASS_TABLE[int(columns.site_class_codes[frame_index, mobile_index])],
                ring_center_distance_angstrom=(
                    None if not np.isfinite(columns.distances[frame_index, mobile_index])
                    else float(columns.distances[frame_index, mobile_index])
                ),
                signed_plane_distance_angstrom=(
                    None if not np.isfinite(columns.signed_distances[frame_index, mobile_index])
                    else float(columns.signed_distances[frame_index, mobile_index])
                ),
                radial_distance_angstrom=(
                    None if not np.isfinite(columns.radial_distances[frame_index, mobile_index])
                    else float(columns.radial_distances[frame_index, mobile_index])
                ),
                oxygen_coordination=None if coordination_value < 0 else coordination_value,
                coordination_changed=bool(columns.coordination_changed[frame_index, mobile_index]),
                site_changed=bool(columns.site_changed[frame_index, mobile_index]),
                ring_crossing=bool(columns.ring_crossing[frame_index, mobile_index]),
                warning_codes=warning_codes,
            )
            frame_states.append(state)
            states.append(state)
        integrity_code = int(columns.framework_integrity[frame_index])
        frame_records.append(
            LtaFramePartitionRecord(
                frame_uid=frame_uid,
                frame_record_digest=columns.frame_record_digests[frame_index],
                policy_digest=policy.policy_digest,
                profile_status=LtaProfileStatus(columns.frame_profile_status[frame_index]),
                framework_integrity=None if integrity_code < 0 else bool(integrity_code),
                site_classes_present=tuple(state.site_class.value for state in frame_states),
                ring_sizes_present=tuple(
                    state.ring_size for state in frame_states if state.ring_size is not None
                ),
                coordination_change=bool(np.any(columns.coordination_changed[frame_index])),
                site_change=bool(np.any(columns.site_changed[frame_index])),
                ring_crossing=bool(np.any(columns.ring_crossing[frame_index])),
                mobile_state_count=mobile_count,
                warning_codes=columns.frame_warning_codes[frame_index],
            )
        )
    return tuple(frame_records), tuple(states)


def build_lta_partition_feature_catalog(
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    *,
    policy: LtaPartitionProfilePolicy | None = None,
    progress_callback: Callable[[str], None] | None = None,
    parallel_workers: int = 1,
) -> LtaPartitionFeatureCatalog:
    """Build lightweight LTA states on every source frame before thinning."""

    active = LtaPartitionProfilePolicy() if policy is None else policy
    run_ids = {item.run_id for item in frame_catalog.frames}
    if set(frame_data_by_run) != run_ids:
        raise TrainingDataInputError("FrameData run IDs must exactly match frame-catalog runs.")
    frames_by_run: dict[str, dict[int, Any]] = {run_id: {} for run_id in run_ids}
    for item in frame_catalog.frames:
        frames_by_run[item.run_id][item.source_frame_index] = item
    decision_all = {item.frame_uid: item for item in frame_catalog.eligibility.decisions}
    mobile_states: list[LtaMobileSiteState] = []
    frame_records: list[LtaFramePartitionRecord] = []
    ordered_run_ids = sorted(run_ids)
    tasks = []
    for run_id in ordered_run_ids:
        run_frames = frames_by_run[run_id]
        run_uids = {item.frame_uid for item in run_frames.values()}
        tasks.append((
            run_id,
            frame_data_by_run[run_id],
            run_frames,
            {uid: decision_all[uid] for uid in run_uids},
            active,
        ))
    workers = max(1, min(int(parallel_workers), len(tasks))) if tasks else 1
    completed = 0
    if workers == 1:
        # Use the same columnar run kernel as the multiprocessing path.  The
        # legacy serial implementation materialized Python state objects while
        # still inside its per-frame loops and retained several duplicate
        # intermediate structures, making workers=1 needlessly slower and more
        # memory intensive.
        for task in tasks:
            columns = _build_lta_columns_for_run(task)
            run_frame_records, run_mobile_states = _materialize_lta_columns(
                columns, active
            )
            frame_records.extend(run_frame_records)
            mobile_states.extend(run_mobile_states)
            completed += 1
            if progress_callback is not None:
                progress_callback(
                    f"LTA partition features; status=item-complete; progress={format_progress_fraction(completed, len(tasks))}; "
                    f"item={columns.run_id}; frames={len(run_frame_records):,}; states={len(run_mobile_states):,}; "
                    "workers=1; backend=columnar"
                )
    else:
        for columns in isolated_process_map(__name__, "_build_lta_columns_for_run", tasks, workers=workers):
            run_frame_records, run_mobile_states = _materialize_lta_columns(columns, active)
            frame_records.extend(run_frame_records)
            mobile_states.extend(run_mobile_states)
            completed += 1
            if progress_callback is not None:
                progress_callback(
                    f"LTA partition features; status=item-complete; progress={format_progress_fraction(completed, len(tasks))}; "
                    f"item={columns.run_id}; frames={len(run_frame_records):,}; states={len(run_mobile_states):,}; workers={workers}"
                )

    return LtaPartitionFeatureCatalog(
        dataset_id=frame_catalog.dataset_id,
        frame_catalog_digest=frame_catalog.content_digest,
        policy=active,
        frame_records=tuple(frame_records),
        mobile_states=tuple(mobile_states),
    )
