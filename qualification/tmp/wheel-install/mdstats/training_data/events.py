"""Full-resolution partition-critical event detection for MLFF-DATA4."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping

import numpy as np

from .progress_timing import format_progress_fraction
from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .eligibility import FrameEligibilityState

EVENT_DETECTION_POLICY_SCHEMA = "mdstats.event-detection-policy.v1"
FRAME_EVENT_RECORD_SCHEMA = "mdstats.frame-event-record.v1"
FULL_RESOLUTION_EVENT_CATALOG_SCHEMA = "mdstats.full-resolution-event-catalog.v2"
FULL_RESOLUTION_EVENT_CATALOG_LEGACY_SCHEMA = "mdstats.full-resolution-event-catalog.v1"
EVENT_DETECTION_POLICY_VERSION = "mdstats.mlff-data4.events.2026-07.v1"


class FrameEventType(str, Enum):
    COORDINATION_CHANGE = "coordination_change"
    SITE_CHANGE = "site_change"
    RING_CROSSING = "ring_crossing"
    FRAMEWORK_INTEGRITY_LOSS = "framework_integrity_loss"
    FRAMEWORK_INTEGRITY_RECOVERY = "framework_integrity_recovery"
    FORCE_THRESHOLD = "force_threshold"
    PRESSURE_THRESHOLD = "pressure_threshold"
    TEMPERATURE_DEVIATION = "temperature_deviation"


def _nonnegative_int(value: int, *, name: str) -> int:
    result = int(value)
    if result < 0:
        raise TrainingDataInputError(f"{name} must be nonnegative.")
    return result


def _optional_positive(value: float | None, *, name: str) -> float | None:
    if value is None:
        return None
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise TrainingDataInputError(f"{name} must be finite and positive when present.")
    return result


@dataclass(frozen=True, slots=True)
class EventDetectionPolicy:
    pre_frames: int = 1
    post_frames: int = 1
    merge_gap_frames: int = 1
    force_norm_max_threshold_ev_per_angstrom: float | None = None
    absolute_pressure_threshold_ev_per_angstrom3: float | None = None
    temperature_deviation_threshold_kelvin: float | None = None
    include_lta_state_changes: bool = True
    include_framework_integrity_changes: bool = True
    eligible_frames_only: bool = True
    policy_version: str = EVENT_DETECTION_POLICY_VERSION

    def __post_init__(self) -> None:
        for name in ("pre_frames", "post_frames", "merge_gap_frames"):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name=name))
        for name in (
            "force_norm_max_threshold_ev_per_angstrom",
            "absolute_pressure_threshold_ev_per_angstrom3",
            "temperature_deviation_threshold_kelvin",
        ):
            object.__setattr__(self, name, _optional_positive(getattr(self, name), name=name))
        if not self.policy_version.strip():
            raise TrainingDataInputError("policy_version must be non-empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": EVENT_DETECTION_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "pre_frames": self.pre_frames,
            "post_frames": self.post_frames,
            "merge_gap_frames": self.merge_gap_frames,
            "force_norm_max_threshold_ev_per_angstrom": self.force_norm_max_threshold_ev_per_angstrom,
            "absolute_pressure_threshold_ev_per_angstrom3": self.absolute_pressure_threshold_ev_per_angstrom3,
            "temperature_deviation_threshold_kelvin": self.temperature_deviation_threshold_kelvin,
            "include_lta_state_changes": self.include_lta_state_changes,
            "include_framework_integrity_changes": self.include_framework_integrity_changes,
            "eligible_frames_only": self.eligible_frames_only,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EventDetectionPolicy":
        if payload.get("schema") != EVENT_DETECTION_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported event-detection policy schema.")
        result = cls(
            pre_frames=int(payload["pre_frames"]),
            post_frames=int(payload["post_frames"]),
            merge_gap_frames=int(payload["merge_gap_frames"]),
            force_norm_max_threshold_ev_per_angstrom=None if payload.get("force_norm_max_threshold_ev_per_angstrom") is None else float(payload["force_norm_max_threshold_ev_per_angstrom"]),
            absolute_pressure_threshold_ev_per_angstrom3=None if payload.get("absolute_pressure_threshold_ev_per_angstrom3") is None else float(payload["absolute_pressure_threshold_ev_per_angstrom3"]),
            temperature_deviation_threshold_kelvin=None if payload.get("temperature_deviation_threshold_kelvin") is None else float(payload["temperature_deviation_threshold_kelvin"]),
            include_lta_state_changes=bool(payload["include_lta_state_changes"]),
            include_framework_integrity_changes=bool(payload["include_framework_integrity_changes"]),
            eligible_frames_only=bool(payload["eligible_frames_only"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Event-detection policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class FrameEventRecord:
    event_id: str
    run_id: str
    event_type: FrameEventType
    policy_digest: str
    anchor_frame_uid: str
    burst_frame_uids: tuple[str, ...]
    protected_frame_uids: tuple[str, ...]
    source_frame_start: int
    source_frame_stop: int
    severity: float | None
    affected_atom_indices: tuple[int, ...]
    evidence_codes: tuple[str, ...]
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("event_id", "policy_digest", "anchor_frame_uid"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        object.__setattr__(self, "event_type", FrameEventType(self.event_type))
        if not self.run_id.strip() or self.source_frame_start < 0 or self.source_frame_stop < self.source_frame_start:
            raise TrainingDataInputError("Invalid event run/frame interval.")
        burst = tuple(self.burst_frame_uids)
        protected = tuple(self.protected_frame_uids)
        if not burst or self.anchor_frame_uid not in burst:
            raise TrainingDataInputError("Event anchor must belong to the burst.")
        for uid in burst + protected:
            validate_digest(uid, name="event frame UID")
        if len(set(burst)) != len(burst) or len(set(protected)) != len(protected):
            raise TrainingDataInputError("Event frame UID lists must be unique.")
        if self.severity is not None and (not np.isfinite(float(self.severity)) or float(self.severity) < 0.0):
            raise TrainingDataInputError("Event severity must be finite and nonnegative.")
        affected = tuple(sorted(set(int(v) for v in self.affected_atom_indices)))
        if any(v < 0 for v in affected):
            raise TrainingDataInputError("Affected atom indices must be nonnegative.")
        object.__setattr__(self, "burst_frame_uids", burst)
        object.__setattr__(self, "protected_frame_uids", protected)
        object.__setattr__(self, "affected_atom_indices", affected)
        object.__setattr__(self, "evidence_codes", tuple(sorted(set(str(v) for v in self.evidence_codes))))

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        event_type: FrameEventType,
        policy_digest: str,
        anchor_frame_uid: str,
        burst_frame_uids: tuple[str, ...],
        protected_frame_uids: tuple[str, ...],
        source_frame_start: int,
        source_frame_stop: int,
        severity: float | None,
        affected_atom_indices: tuple[int, ...],
        evidence_codes: tuple[str, ...],
    ) -> "FrameEventRecord":
        event_id = digest(
            {
                "run_id": run_id,
                "event_type": FrameEventType(event_type).value,
                "policy_digest": policy_digest,
                "anchor_frame_uid": anchor_frame_uid,
                "burst_frame_uids": list(burst_frame_uids),
            }
        )
        return cls(
            event_id=event_id,
            run_id=run_id,
            event_type=event_type,
            policy_digest=policy_digest,
            anchor_frame_uid=anchor_frame_uid,
            burst_frame_uids=burst_frame_uids,
            protected_frame_uids=protected_frame_uids,
            source_frame_start=source_frame_start,
            source_frame_stop=source_frame_stop,
            severity=severity,
            affected_atom_indices=affected_atom_indices,
            evidence_codes=evidence_codes,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FRAME_EVENT_RECORD_SCHEMA,
            "event_id": self.event_id,
            "run_id": self.run_id,
            "event_type": self.event_type.value,
            "policy_digest": self.policy_digest,
            "anchor_frame_uid": self.anchor_frame_uid,
            "burst_frame_uids": list(self.burst_frame_uids),
            "protected_frame_uids": list(self.protected_frame_uids),
            "source_frame_start": self.source_frame_start,
            "source_frame_stop": self.source_frame_stop,
            "severity": self.severity,
            "affected_atom_indices": list(self.affected_atom_indices),
            "evidence_codes": list(self.evidence_codes),
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameEventRecord":
        if payload.get("schema") != FRAME_EVENT_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported frame-event-record schema.")
        result = cls(
            event_id=str(payload["event_id"]),
            run_id=str(payload["run_id"]),
            event_type=FrameEventType(payload["event_type"]),
            policy_digest=str(payload["policy_digest"]),
            anchor_frame_uid=str(payload["anchor_frame_uid"]),
            burst_frame_uids=tuple(str(v) for v in payload["burst_frame_uids"]),
            protected_frame_uids=tuple(str(v) for v in payload["protected_frame_uids"]),
            source_frame_start=int(payload["source_frame_start"]),
            source_frame_stop=int(payload["source_frame_stop"]),
            severity=None if payload.get("severity") is None else float(payload["severity"]),
            affected_atom_indices=tuple(int(v) for v in payload.get("affected_atom_indices", ())),
            evidence_codes=tuple(str(v) for v in payload.get("evidence_codes", ())),
        )
        supplied_digest = payload.get("content_digest")
        if supplied_digest is not None and supplied_digest != result.content_digest:
            raise TrainingDataSerializationError("Frame-event-record digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class FullResolutionEventCatalog:
    dataset_id: str
    frame_catalog_digest: str
    raw_feature_catalog_digest: str
    lta_feature_catalog_digest: str | None
    policy: EventDetectionPolicy
    events: tuple[FrameEventRecord, ...]
    profile_feature_catalog_digests: tuple[str, ...] = ()
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)
    _protected_frame_uids_cache: tuple[str, ...] = field(
        default=(), init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in ("frame_catalog_digest", "raw_feature_catalog_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.lta_feature_catalog_digest is not None:
            object.__setattr__(self, "lta_feature_catalog_digest", validate_digest(self.lta_feature_catalog_digest, name="lta_feature_catalog_digest"))
        extension_digests = tuple(sorted(set(validate_digest(value, name="profile_feature_catalog_digest") for value in self.profile_feature_catalog_digests)))
        if self.lta_feature_catalog_digest is not None and not extension_digests:
            extension_digests = (self.lta_feature_catalog_digest,)
        object.__setattr__(self, "profile_feature_catalog_digests", extension_digests)
        events = tuple(sorted(self.events, key=lambda item: (item.run_id, item.source_frame_start, item.event_type.value, item.event_id)))
        if len({item.event_id for item in events}) != len(events):
            raise TrainingDataInputError("Event IDs must be unique.")
        if any(item.policy_digest != self.policy.policy_digest for item in events):
            raise TrainingDataInputError("Event policy mismatch.")
        object.__setattr__(self, "events", events)
        object.__setattr__(
            self,
            "_protected_frame_uids_cache",
            tuple(
                sorted(
                    {
                        uid
                        for event in events
                        for uid in event.protected_frame_uids
                    }
                )
            ),
        )

    @property
    def protected_frame_uids(self) -> tuple[str, ...]:
        return self._protected_frame_uids_cache

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FULL_RESOLUTION_EVENT_CATALOG_SCHEMA,
            "dataset_id": self.dataset_id,
            "frame_catalog_digest": self.frame_catalog_digest,
            "raw_feature_catalog_digest": self.raw_feature_catalog_digest,
            "lta_feature_catalog_digest": self.lta_feature_catalog_digest,
            "profile_feature_catalog_digests": list(self.profile_feature_catalog_digests),
            "policy": self.policy.to_dict(),
            "events": [item.to_dict() for item in self.events],
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "FullResolutionEventCatalog":
        schema = payload.get("schema")
        if schema not in {FULL_RESOLUTION_EVENT_CATALOG_SCHEMA, FULL_RESOLUTION_EVENT_CATALOG_LEGACY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported full-resolution-event-catalog schema.")
        legacy_lta = None if payload.get("lta_feature_catalog_digest") is None else str(payload["lta_feature_catalog_digest"])
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            raw_feature_catalog_digest=str(payload["raw_feature_catalog_digest"]),
            lta_feature_catalog_digest=legacy_lta,
            policy=EventDetectionPolicy.from_dict(payload["policy"]),
            events=tuple(FrameEventRecord.from_dict(item) for item in payload.get("events", ())),
            profile_feature_catalog_digests=tuple(str(v) for v in payload.get("profile_feature_catalog_digests", (() if legacy_lta is None else (legacy_lta,)))),
        )
        expected = result.content_digest
        if schema == FULL_RESOLUTION_EVENT_CATALOG_LEGACY_SCHEMA:
            expected = digest({
                "schema": FULL_RESOLUTION_EVENT_CATALOG_LEGACY_SCHEMA,
                "dataset_id": result.dataset_id,
                "frame_catalog_digest": result.frame_catalog_digest,
                "raw_feature_catalog_digest": result.raw_feature_catalog_digest,
                "lta_feature_catalog_digest": result.lta_feature_catalog_digest,
                "policy": result.policy.to_dict(),
                "events": [item.to_dict() for item in result.events],
            })
        if payload.get("content_digest") not in (None, expected):
            raise TrainingDataSerializationError("Full-resolution-event-catalog digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class _Anchor:
    run_id: str
    source_frame_index: int
    frame_uid: str
    event_type: FrameEventType
    severity: float | None
    affected_atom_indices: tuple[int, ...]
    evidence_codes: tuple[str, ...]


def _target_temperature(frame_catalog: Any, run_id: str, position: int, count: int) -> float | None:
    condition = frame_catalog.temperature_conditions.for_run(run_id)
    start = condition.target_start_kelvin
    end = condition.target_end_kelvin
    if start is None or end is None:
        return None
    if count <= 1:
        return float(start)
    fraction = position / float(count - 1)
    return float(start + fraction * (end - start))


def detect_full_resolution_events(
    frame_catalog: Any,
    raw_features: Any,
    *,
    lta_features: Any | None = None,
    profile_features: tuple[Any, ...] = (),
    policy: EventDetectionPolicy | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> FullResolutionEventCatalog:
    """Detect events on every eligible frame before any temporal thinning."""

    active = EventDetectionPolicy() if policy is None else policy
    if profile_features:
        from .profile_extensions import find_profile_feature
        extension = find_profile_feature(tuple(profile_features), "lta")
        if lta_features is None:
            lta_features = None if extension is None else extension.as_lta_partition()
        elif extension is not None:
            embedded = extension.scientific_payload_digest
            if embedded is not None and embedded != lta_features.content_digest:
                raise TrainingDataInputError("Conflicting LTA event inputs were supplied.")
    if raw_features.frame_catalog_digest != frame_catalog.content_digest:
        raise TrainingDataInputError("Raw feature/frame catalog mismatch.")
    if lta_features is not None and lta_features.frame_catalog_digest != frame_catalog.content_digest:
        raise TrainingDataInputError("LTA feature/frame catalog mismatch.")
    raw_by_uid = {item.frame_uid: item for item in raw_features.records}
    lta_frame_by_uid = (
        {} if lta_features is None
        else {item.frame_uid: item for item in lta_features.frame_records}
    )
    # LTA v2 catalogs build an immutable frame-to-state index once during
    # construction. Reuse it directly instead of regrouping ~10^6 mobile-state
    # objects and allocating a second hierarchy during every event scan.
    states_for_frame = (
        (lambda _uid: ())
        if lta_features is None
        else lta_features.states_for_frame
    )

    anchors: list[_Anchor] = []
    decision_by_uid = {item.frame_uid: item for item in frame_catalog.eligibility.decisions}
    temperature_by_run = {item.run_id: item for item in frame_catalog.temperature_conditions.records}
    frame_order_by_run: dict[str, list[Any]] = {}
    for frame in frame_catalog.frames:
        frame_order_by_run.setdefault(frame.run_id, []).append(frame)
    uid_by_index_by_run: dict[str, dict[int, str]] = {}
    available_indices_by_run: dict[str, tuple[int, ...]] = {}
    for run_id, frames in frame_order_by_run.items():
        frames.sort(key=lambda item: item.source_frame_index)
        uid_by_index = {item.source_frame_index: item.frame_uid for item in frames}
        uid_by_index_by_run[run_id] = uid_by_index
        available_indices_by_run[run_id] = tuple(uid_by_index)
        previous_lta = None
        for position, frame in enumerate(frames):
            decision = decision_by_uid[frame.frame_uid]
            if active.eligible_frames_only and decision.state is not FrameEligibilityState.ELIGIBLE:
                previous_lta = lta_frame_by_uid.get(frame.frame_uid)
                continue
            raw = raw_by_uid[frame.frame_uid]
            lta = lta_frame_by_uid.get(frame.frame_uid)
            states = states_for_frame(frame.frame_uid)
            if active.include_lta_state_changes and lta is not None:
                affected_coord = tuple(state.atom_index for state in states if state.coordination_changed)
                affected_site = tuple(state.atom_index for state in states if state.site_changed)
                affected_crossing = tuple(state.atom_index for state in states if state.ring_crossing)
                if lta.coordination_change:
                    anchors.append(_Anchor(run_id, frame.source_frame_index, frame.frame_uid, FrameEventType.COORDINATION_CHANGE, None, affected_coord, ("lta_integer_coordination_changed",)))
                if lta.site_change:
                    anchors.append(_Anchor(run_id, frame.source_frame_index, frame.frame_uid, FrameEventType.SITE_CHANGE, None, affected_site, ("lta_ring_assignment_changed",)))
                if lta.ring_crossing:
                    anchors.append(_Anchor(run_id, frame.source_frame_index, frame.frame_uid, FrameEventType.RING_CROSSING, None, affected_crossing, ("lta_signed_ring_plane_coordinate_changed_sign",)))
            if active.include_framework_integrity_changes and lta is not None and previous_lta is not None:
                if previous_lta.framework_integrity is True and lta.framework_integrity is False:
                    anchors.append(_Anchor(run_id, frame.source_frame_index, frame.frame_uid, FrameEventType.FRAMEWORK_INTEGRITY_LOSS, None, (), ("framework_integrity_true_to_false",)))
                elif previous_lta.framework_integrity is False and lta.framework_integrity is True:
                    anchors.append(_Anchor(run_id, frame.source_frame_index, frame.frame_uid, FrameEventType.FRAMEWORK_INTEGRITY_RECOVERY, None, (), ("framework_integrity_false_to_true",)))
            if active.force_norm_max_threshold_ev_per_angstrom is not None and raw.force_norm_max_ev_per_angstrom is not None and raw.force_norm_max_ev_per_angstrom > active.force_norm_max_threshold_ev_per_angstrom:
                anchors.append(_Anchor(run_id, frame.source_frame_index, frame.frame_uid, FrameEventType.FORCE_THRESHOLD, raw.force_norm_max_ev_per_angstrom, (), ("force_norm_max_exceeded_policy_threshold",)))
            if active.absolute_pressure_threshold_ev_per_angstrom3 is not None and raw.pressure_ev_per_angstrom3 is not None and abs(raw.pressure_ev_per_angstrom3) > active.absolute_pressure_threshold_ev_per_angstrom3:
                anchors.append(_Anchor(run_id, frame.source_frame_index, frame.frame_uid, FrameEventType.PRESSURE_THRESHOLD, abs(raw.pressure_ev_per_angstrom3), (), ("absolute_pressure_exceeded_policy_threshold",)))
            if active.temperature_deviation_threshold_kelvin is not None and raw.instantaneous_temperature_kelvin is not None:
                condition = temperature_by_run[run_id]
                start = condition.target_start_kelvin
                end = condition.target_end_kelvin
                target = None
                if start is not None and end is not None:
                    target = float(start) if len(frames) <= 1 else float(
                        start + (position / float(len(frames) - 1)) * (end - start)
                    )
                if target is not None:
                    deviation = abs(raw.instantaneous_temperature_kelvin - target)
                    if deviation > active.temperature_deviation_threshold_kelvin:
                        anchors.append(_Anchor(run_id, frame.source_frame_index, frame.frame_uid, FrameEventType.TEMPERATURE_DEVIATION, deviation, (), ("temperature_deviation_exceeded_policy_threshold",)))
            previous_lta = lta
        if progress_callback is not None:
            progress_callback(
                f"status=item-complete; phase=event-scan; item={run_id}; frames={len(frames):,}; anchors={len(anchors):,}"
            )

    # Merge adjacent anchors of the same run/type.
    grouped: dict[tuple[str, FrameEventType], list[_Anchor]] = {}
    for anchor in anchors:
        grouped.setdefault((anchor.run_id, anchor.event_type), []).append(anchor)
    events: list[FrameEventRecord] = []
    for (run_id, event_type), items in sorted(grouped.items(), key=lambda pair: (pair[0][0], pair[0][1].value)):
        items.sort(key=lambda item: (item.source_frame_index, item.frame_uid))
        bursts: list[list[_Anchor]] = []
        for item in items:
            if not bursts or item.source_frame_index - bursts[-1][-1].source_frame_index > active.merge_gap_frames + 1:
                bursts.append([item])
            else:
                bursts[-1].append(item)
        # Frame order/index is a run property.  Reuse it for every event type
        # rather than sorting and rebuilding the same maps once per type.
        uid_by_index = uid_by_index_by_run[run_id]
        available_indices = available_indices_by_run[run_id]
        for burst in bursts:
            if any(item.severity is not None for item in burst):
                anchor = min(
                    burst,
                    key=lambda item: (
                        -(item.severity if item.severity is not None else -1.0),
                        item.source_frame_index,
                        item.frame_uid,
                    ),
                )
                severity = max(item.severity for item in burst if item.severity is not None)
            else:
                anchor = min(burst, key=lambda item: (item.source_frame_index, item.frame_uid))
                severity = None
            start = min(item.source_frame_index for item in burst)
            stop = max(item.source_frame_index for item in burst)
            lower = start - active.pre_frames
            upper = stop + active.post_frames
            first = bisect_left(available_indices, lower)
            last = bisect_right(available_indices, upper)
            protected = tuple(
                uid_by_index[index] for index in available_indices[first:last]
            )
            burst_uids = tuple(item.frame_uid for item in burst)
            affected = tuple(sorted({idx for item in burst for idx in item.affected_atom_indices}))
            evidence = tuple(sorted({code for item in burst for code in item.evidence_codes}))
            events.append(
                FrameEventRecord.create(
                    run_id=run_id,
                    event_type=event_type,
                    policy_digest=active.policy_digest,
                    anchor_frame_uid=anchor.frame_uid,
                    burst_frame_uids=burst_uids,
                    protected_frame_uids=protected,
                    source_frame_start=start,
                    source_frame_stop=stop,
                    severity=severity,
                    affected_atom_indices=affected,
                    evidence_codes=evidence,
                )
            )
    return FullResolutionEventCatalog(
        dataset_id=frame_catalog.dataset_id,
        frame_catalog_digest=frame_catalog.content_digest,
        raw_feature_catalog_digest=raw_features.content_digest,
        lta_feature_catalog_digest=None if lta_features is None else lta_features.content_digest,
        policy=active,
        events=tuple(events),
        profile_feature_catalog_digests=tuple(item.content_digest for item in profile_features),
    )
