"""Neutral feature and correlation evidence boundary without legacy lineage."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Sequence

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ..data4_bundle import Data4FeatureBundle
from ..events import FullResolutionEventCatalog
from ..profile_extensions import (
    ProfileFeatureCatalog,
    ProfileFeatureStage,
    rebind_partition_profile_catalog,
)
from ..raw_features import RawFeatureCatalog
from .frame_authority import CanonicalFrameAuthority
from .sources import SourceAuthority

NEUTRAL_FEATURE_EVIDENCE_SCHEMA = "mdstats.neutral-feature-evidence.v1"


@dataclass(frozen=True, slots=True)
class NeutralFeatureEvidence:
    dataset_id: str
    source_authority_digest: str
    frame_authority_digest: str
    raw_features: RawFeatureCatalog
    events: FullResolutionEventCatalog
    profile_partition_features: tuple[ProfileFeatureCatalog, ...] = ()
    notes: tuple[str, ...] = ()
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_authority_digest",
            validate_digest(self.source_authority_digest, name="source_authority_digest"),
        )
        object.__setattr__(
            self,
            "frame_authority_digest",
            validate_digest(self.frame_authority_digest, name="frame_authority_digest"),
        )
        if (
            self.raw_features.source_catalog_digest != self.source_authority_digest
            or self.raw_features.frame_catalog_digest != self.frame_authority_digest
        ):
            raise TrainingDataInputError(
                "Raw features do not belong to the neutral source and frame authorities."
            )
        if (
            self.events.frame_catalog_digest != self.frame_authority_digest
            or self.events.raw_feature_catalog_digest != self.raw_features.content_digest
        ):
            raise TrainingDataInputError(
                "Event catalog does not belong to the neutral frame authority and raw features."
            )
        for profile in self.profile_partition_features:
            if profile.frame_catalog_digest != self.frame_authority_digest:
                raise TrainingDataInputError(
                    "Profile partition features do not belong to the neutral frame authority."
                )
        object.__setattr__(
            self, "profile_partition_features", tuple(self.profile_partition_features)
        )
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": NEUTRAL_FEATURE_EVIDENCE_SCHEMA,
            "dataset_id": self.dataset_id,
            "source_authority_digest": self.source_authority_digest,
            "frame_authority_digest": self.frame_authority_digest,
            "raw_features": self.raw_features.to_dict(),
            "events": self.events.to_dict(),
            "profile_partition_features": [
                item.to_dict() for item in self.profile_partition_features
            ],
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
        payload = self._payload()
        return {**payload, "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "NeutralFeatureEvidence":
        if payload.get("schema") != NEUTRAL_FEATURE_EVIDENCE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported neutral-feature-evidence schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            source_authority_digest=str(payload["source_authority_digest"]),
            frame_authority_digest=str(payload["frame_authority_digest"]),
            raw_features=RawFeatureCatalog.from_dict(payload["raw_features"]),
            events=FullResolutionEventCatalog.from_dict(payload["events"]),
            profile_partition_features=tuple(
                ProfileFeatureCatalog.from_dict(item)
                for item in payload.get("profile_partition_features", ())
            ),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Neutral-feature-evidence digest mismatch.")
        return result


def build_neutral_feature_evidence_from_data4_bundle(
    source_authority: SourceAuthority,
    frame_authority: CanonicalFrameAuthority,
    data4_bundle: Data4FeatureBundle,
) -> NeutralFeatureEvidence:
    """Build neutral feature evidence rebinding DATA4 features to current-generation authorities."""
    if not isinstance(source_authority, SourceAuthority):
        raise TrainingDataInputError(
            "NeutralFeatureEvidence requires a current-generation SourceAuthority."
        )
    if not isinstance(frame_authority, CanonicalFrameAuthority):
        raise TrainingDataInputError(
            "NeutralFeatureEvidence requires a current-generation CanonicalFrameAuthority."
        )
    if frame_authority.source_authority_digest != source_authority.content_digest:
        raise TrainingDataInputError(
            "Frame authority does not match the provided source authority."
        )

    clean_raw_records = tuple(
        replace(
            r,
            frame_record_digest=frame_authority.frame(r.frame_uid).content_digest,
        )
        for r in data4_bundle.raw_features.records
    )
    clean_raw_features = RawFeatureCatalog(
        dataset_id=frame_authority.dataset_id,
        source_catalog_digest=source_authority.content_digest,
        frame_catalog_digest=frame_authority.content_digest,
        policy=data4_bundle.raw_features.policy,
        records=clean_raw_records,
    )

    clean_profiles: list[ProfileFeatureCatalog] = []
    for p in data4_bundle.profile_partition_features:
        if p.stage is not ProfileFeatureStage.PARTITION:
            raise TrainingDataInputError(
                f"Unsupported non-partition profile feature stage in DATA4: {p.stage!r}"
            )
        clean_p = rebind_partition_profile_catalog(p, frame_authority)
        clean_profiles.append(clean_p)

    clean_events = FullResolutionEventCatalog(
        dataset_id=frame_authority.dataset_id,
        frame_catalog_digest=frame_authority.content_digest,
        raw_feature_catalog_digest=clean_raw_features.content_digest,
        lta_feature_catalog_digest=None,
        policy=data4_bundle.events.policy,
        events=data4_bundle.events.events,
        profile_feature_catalog_digests=tuple(item.content_digest for item in clean_profiles),
    )

    return NeutralFeatureEvidence(
        dataset_id=frame_authority.dataset_id,
        source_authority_digest=source_authority.content_digest,
        frame_authority_digest=frame_authority.content_digest,
        raw_features=clean_raw_features,
        events=clean_events,
        profile_partition_features=tuple(clean_profiles),
        notes=(
            "Neutral feature evidence binds physical observables and events to current-generation "
            "source and frame authorities.",
        ),
    )
