"""Executable invalidation policy for the single-source replay pipeline.

REPLAY-UNIFY1E freezes the cache/restart invalidation matrix as a public,
serializable decision record.  The planner is deliberately metadata-only: it
never opens ExtXYZ files or model checkpoints and therefore can be used by
campaign planning, qualification tests, and diagnostics without triggering
expensive work.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .replay import ReplayLabelMode, normalize_replay_split_ratio

REPLAY_INVALIDATION_PLAN_SCHEMA = "mdstats.replay-invalidation-plan.v1"
REPLAY_INVALIDATION_VERSION = "REPLAY-UNIFY1E-v1"


@dataclass(frozen=True, slots=True)
class ReplayInvalidationPlan:
    label_mode: ReplayLabelMode
    reindex_source: bool
    rerun_pseudolabel_inference: bool
    requalify: bool
    resplit: bool
    rematerialize_roles: tuple[str, ...]
    reasons: tuple[str, ...]
    serialization_schema: str = REPLAY_INVALIDATION_PLAN_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "label_mode", ReplayLabelMode(self.label_mode))
        if self.serialization_schema != REPLAY_INVALIDATION_PLAN_SCHEMA:
            raise TrainingDataInputError("Unsupported replay invalidation-plan schema.")
        roles = tuple(sorted(set(str(v).strip() for v in self.rematerialize_roles if str(v).strip())))
        reasons = tuple(sorted(set(str(v).strip() for v in self.reasons if str(v).strip())))
        object.__setattr__(self, "rematerialize_roles", roles)
        object.__setattr__(self, "reasons", reasons)

    @property
    def content_digest(self) -> str:
        return digest({
            "schema": self.serialization_schema,
            "version": REPLAY_INVALIDATION_VERSION,
            "label_mode": self.label_mode.value,
            "reindex_source": self.reindex_source,
            "rerun_pseudolabel_inference": self.rerun_pseudolabel_inference,
            "requalify": self.requalify,
            "resplit": self.resplit,
            "rematerialize_roles": list(self.rematerialize_roles),
            "reasons": list(self.reasons),
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "version": REPLAY_INVALIDATION_VERSION,
            "label_mode": self.label_mode.value,
            "reindex_source": self.reindex_source,
            "rerun_pseudolabel_inference": self.rerun_pseudolabel_inference,
            "requalify": self.requalify,
            "resplit": self.resplit,
            "rematerialize_roles": list(self.rematerialize_roles),
            "reasons": list(self.reasons),
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReplayInvalidationPlan":
        if payload.get("schema") != REPLAY_INVALIDATION_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported replay invalidation-plan schema.")
        if payload.get("version") not in (None, REPLAY_INVALIDATION_VERSION):
            raise TrainingDataSerializationError("Unsupported replay invalidation-plan version.")
        result = cls(
            label_mode=ReplayLabelMode(payload["label_mode"]),
            reindex_source=bool(payload["reindex_source"]),
            rerun_pseudolabel_inference=bool(payload["rerun_pseudolabel_inference"]),
            requalify=bool(payload["requalify"]),
            resplit=bool(payload["resplit"]),
            rematerialize_roles=tuple(str(v) for v in payload.get("rematerialize_roles", ())),
            reasons=tuple(str(v) for v in payload.get("reasons", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Replay invalidation-plan digest mismatch.")
        return result


def _vd(value: str, name: str) -> str:
    return validate_digest(value, name=name)


def build_replay_invalidation_plan(
    *,
    label_mode: ReplayLabelMode | str,
    old_source_sha256: str,
    new_source_sha256: str,
    old_geometry_set_digest: str,
    new_geometry_set_digest: str,
    old_source_true_label_payload_digest: str,
    new_source_true_label_payload_digest: str,
    old_prediction_policy_digest: str | None = None,
    new_prediction_policy_digest: str | None = None,
    old_qualification_policy_digest: str | None = None,
    new_qualification_policy_digest: str | None = None,
    old_eligible_geometry_set_digest: str | None = None,
    new_eligible_geometry_set_digest: str | None = None,
    old_split_ratio: Sequence[int] = (5, 1),
    new_split_ratio: Sequence[int] = (5, 1),
    old_split_seed: int = 42,
    new_split_seed: int = 42,
    requested_roles: Sequence[str] = ("train", "monitor"),
    existing_materialized_roles: Sequence[str] = (),
) -> ReplayInvalidationPlan:
    """Return the minimum replay work required by two metadata states.

    Locator changes are intentionally absent: relocation with identical source
    bytes is not a scientific invalidation.  Source byte changes require source
    revalidation, while pseudo inference depends only on geometry membership and
    prediction-policy identity, never on source true-label payloads.
    """
    mode = ReplayLabelMode(label_mode)
    if mode not in {ReplayLabelMode.TRUE_DFT, ReplayLabelMode.FOUNDATION_PSEUDOLABEL}:
        raise TrainingDataInputError("Replay invalidation requires true_dft or foundation_pseudolabel mode.")
    old_sha = _vd(old_source_sha256, "old_source_sha256")
    new_sha = _vd(new_source_sha256, "new_source_sha256")
    old_geom = _vd(old_geometry_set_digest, "old_geometry_set_digest")
    new_geom = _vd(new_geometry_set_digest, "new_geometry_set_digest")
    old_labels = _vd(old_source_true_label_payload_digest, "old_source_true_label_payload_digest")
    new_labels = _vd(new_source_true_label_payload_digest, "new_source_true_label_payload_digest")

    source_bytes_changed = old_sha != new_sha
    geometry_changed = old_geom != new_geom
    true_labels_changed = old_labels != new_labels
    prediction_policy_changed = old_prediction_policy_digest != new_prediction_policy_digest
    qualification_policy_changed = old_qualification_policy_digest != new_qualification_policy_digest
    eligible_changed = old_eligible_geometry_set_digest != new_eligible_geometry_set_digest
    split_policy_changed = (
        normalize_replay_split_ratio(old_split_ratio) != normalize_replay_split_ratio(new_split_ratio)
        or int(old_split_seed) != int(new_split_seed)
    )

    reasons: list[str] = []
    if source_bytes_changed:
        reasons.append("source_bytes_changed")
    if geometry_changed:
        reasons.append("source_geometry_changed")
    if true_labels_changed:
        reasons.append("source_true_labels_changed")
    if prediction_policy_changed:
        reasons.append("prediction_policy_changed")
    if qualification_policy_changed:
        reasons.append("qualification_policy_changed")
    if eligible_changed:
        reasons.append("eligible_geometry_set_changed")
    if split_policy_changed:
        reasons.append("split_policy_changed")

    reindex = source_bytes_changed
    rerun_prediction = mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL and (
        geometry_changed or prediction_policy_changed
    )
    requalify = (
        geometry_changed
        or qualification_policy_changed
        or rerun_prediction
        or (mode is ReplayLabelMode.TRUE_DFT and true_labels_changed)
    )
    # Qualification authority is part of the split-manifest identity even when
    # the resulting membership happens to stay the same.
    resplit = requalify or eligible_changed or split_policy_changed

    requested = {str(v).strip() for v in requested_roles if str(v).strip()}
    existing = {str(v).strip() for v in existing_materialized_roles if str(v).strip()}
    rematerialize = set(requested - existing)
    if resplit:
        rematerialize.update(requested)
    elif mode is ReplayLabelMode.TRUE_DFT and true_labels_changed:
        rematerialize.update(requested)
    elif mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL and rerun_prediction:
        rematerialize.update(requested)

    return ReplayInvalidationPlan(
        label_mode=mode,
        reindex_source=reindex,
        rerun_pseudolabel_inference=rerun_prediction,
        requalify=requalify,
        resplit=resplit,
        rematerialize_roles=tuple(rematerialize),
        reasons=tuple(reasons),
    )


__all__ = [
    "REPLAY_INVALIDATION_PLAN_SCHEMA",
    "REPLAY_INVALIDATION_VERSION",
    "ReplayInvalidationPlan",
    "build_replay_invalidation_plan",
]
