"""Generic optional material-profile feature extension contracts.

The MLFF core stores optional porous, zeolite, LTA, polymer, interface, or
custom evidence through this module.  Scientific payload schemas remain owned
by their extension providers.  The core binds identity, stage, lineage, and
serialization only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    json_value,
    tuple_value,
    validate_digest,
)
from .material_profiles import MaterialProfileContracts, MaterialProfileProviderIdentity

PROFILE_FEATURE_CATALOG_SCHEMA = "mdstats.profile-feature-catalog.v2"
PROFILE_FEATURE_CATALOG_LEGACY_SCHEMA = "mdstats.profile-feature-catalog.v1"
PROFILE_FEATURE_PROVIDER_VERSION = "mdstats.mlff-data9a7d.profile-extension.2026-07.v1"
MLFF_DATA9A7D_PARSER_VERSION = "0.20.50a0"


class ProfileFeatureStage(str, Enum):
    PARTITION = "partition"
    SELECTION = "selection"


def _thaw(value: Any) -> Any:
    if isinstance(value, tuple):
        if all(isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str) for item in value):
            return {item[0]: _thaw(item[1]) for item in value}
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class ProfileFeatureCatalog:
    """Generic profile-extension identity with optional embedded payload.

    Partition-scale scientific catalogs may be bound by digest and retained as
    a typed in-memory object instead of being deep-copied into this wrapper.
    Selection-scale catalogs remain embeddable for standalone round trips.
    """

    extension_id: str
    stage: ProfileFeatureStage
    provider_identity: MaterialProfileProviderIdentity
    frame_catalog_digest: str
    payload_schema: str
    payload: Mapping[str, Any] | tuple[tuple[str, Any], ...] | None = None
    scientific_payload_digest_value: str | None = None
    parent_bundle_digest: str | None = None
    notes: tuple[str, ...] = ()
    _resolved_payload: Any | None = field(default=None, init=False, repr=False, compare=False)
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        extension_id = str(self.extension_id).strip().lower()
        if not extension_id or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_.:-" for ch in extension_id):
            raise TrainingDataInputError("extension_id must be a lowercase identifier.")
        object.__setattr__(self, "extension_id", extension_id)
        object.__setattr__(self, "stage", ProfileFeatureStage(self.stage))
        object.__setattr__(self, "frame_catalog_digest", validate_digest(self.frame_catalog_digest, name="frame_catalog_digest"))
        if self.parent_bundle_digest is not None:
            object.__setattr__(self, "parent_bundle_digest", validate_digest(self.parent_bundle_digest, name="parent_bundle_digest"))
        schema = str(self.payload_schema).strip()
        if not schema:
            raise TrainingDataInputError("payload_schema must be non-empty.")
        object.__setattr__(self, "payload_schema", schema)

        embedded_digest: str | None = None
        if self.payload is not None:
            normalized = json_value(_thaw(self.payload) if isinstance(self.payload, tuple) else self.payload)
            if not isinstance(normalized, Mapping):
                raise TrainingDataInputError("Profile feature payload must be a mapping.")
            embedded = normalized.get("content_digest")
            if embedded is not None:
                embedded_digest = validate_digest(str(embedded), name="scientific_payload_digest")
            object.__setattr__(self, "payload", tuple_value(normalized))

        explicit = self.scientific_payload_digest_value
        if explicit is not None:
            explicit = validate_digest(str(explicit), name="scientific_payload_digest")
        if explicit is None:
            explicit = embedded_digest
        elif embedded_digest is not None and explicit != embedded_digest:
            raise TrainingDataInputError("Embedded and declared profile payload digests disagree.")
        if explicit is None:
            raise TrainingDataInputError("Profile feature requires a scientific payload digest.")
        object.__setattr__(self, "scientific_payload_digest_value", explicit)
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))
        if self.stage is ProfileFeatureStage.PARTITION and self.parent_bundle_digest is not None:
            raise TrainingDataInputError("Partition-stage profile features cannot depend on a later bundle.")
        if self.stage is ProfileFeatureStage.SELECTION and self.parent_bundle_digest is None:
            raise TrainingDataInputError("Selection-stage profile features require a parent DATA4 bundle digest.")

    @property
    def payload_mapping(self) -> Mapping[str, Any]:
        resolved = self._resolved_payload
        if resolved is not None:
            if hasattr(resolved, "to_dict"):
                value = resolved.to_dict()
            elif isinstance(resolved, Mapping):
                value = json_value(resolved)
            else:
                raise TrainingDataSerializationError("Resolved profile payload is not serializable.")
            if not isinstance(value, Mapping):
                raise TrainingDataSerializationError("Resolved profile payload is not a mapping.")
            return value
        if self.payload is None:
            raise TrainingDataSerializationError(
                "Profile payload is digest-bound but not resolved in this object."
            )
        value = _thaw(self.payload)
        if not isinstance(value, Mapping):
            raise TrainingDataSerializationError("Profile feature payload is not a mapping.")
        return value

    @property
    def scientific_payload_digest(self) -> str:
        return str(self.scientific_payload_digest_value)

    @property
    def payload_embedded(self) -> bool:
        return self.payload is not None

    def bind_scientific_payload(self, payload: Any) -> "ProfileFeatureCatalog":
        if hasattr(payload, "content_digest"):
            actual = str(payload.content_digest)
        elif isinstance(payload, Mapping) and payload.get("content_digest") is not None:
            actual = str(payload["content_digest"])
        else:
            raise TrainingDataInputError("Resolved profile payload lacks a content digest.")
        actual = validate_digest(actual, name="resolved_scientific_payload_digest")
        if actual != self.scientific_payload_digest:
            raise TrainingDataInputError("Resolved profile payload digest does not match its reference.")
        object.__setattr__(self, "_resolved_payload", payload)
        return self

    def _payload(self) -> dict[str, Any]:
        result = {
            "schema": PROFILE_FEATURE_CATALOG_SCHEMA,
            "extension_id": self.extension_id,
            "stage": self.stage.value,
            "provider_identity": self.provider_identity.to_dict(),
            "frame_catalog_digest": self.frame_catalog_digest,
            "parent_bundle_digest": self.parent_bundle_digest,
            "payload_schema": self.payload_schema,
            "scientific_payload_digest": self.scientific_payload_digest,
            "payload_embedded": self.payload_embedded,
            "notes": list(self.notes),
        }
        if self.payload_embedded:
            result["payload"] = dict(self.payload_mapping)
        return result

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
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProfileFeatureCatalog":
        schema = payload.get("schema")
        if schema not in {PROFILE_FEATURE_CATALOG_SCHEMA, PROFILE_FEATURE_CATALOG_LEGACY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported profile-feature-catalog schema.")
        if schema == PROFILE_FEATURE_CATALOG_LEGACY_SCHEMA:
            supplied = payload.get("content_digest")
            if supplied not in (None, digest({k: v for k, v in payload.items() if k != "content_digest"})):
                raise TrainingDataSerializationError("Legacy profile-feature-catalog digest mismatch.")
            embedded_payload = payload["payload"]
            scientific_digest = embedded_payload.get("content_digest")
        else:
            embedded_payload = payload.get("payload") if bool(payload.get("payload_embedded", False)) else None
            scientific_digest = payload.get("scientific_payload_digest")
        result = cls(
            extension_id=str(payload["extension_id"]),
            stage=ProfileFeatureStage(str(payload["stage"])),
            provider_identity=MaterialProfileProviderIdentity.from_dict(payload["provider_identity"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            parent_bundle_digest=None if payload.get("parent_bundle_digest") is None else str(payload["parent_bundle_digest"]),
            payload_schema=str(payload["payload_schema"]),
            payload=embedded_payload,
            scientific_payload_digest_value=None if scientific_digest is None else str(scientific_digest),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if schema == PROFILE_FEATURE_CATALOG_SCHEMA and payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Profile-feature-catalog digest mismatch.")
        return result

    def as_lta_partition(self):
        if self.extension_id != "lta" or self.stage is not ProfileFeatureStage.PARTITION:
            raise TrainingDataInputError("Profile feature is not an LTA partition catalog.")
        from .lta_profile import LTA_PARTITION_FEATURE_CATALOG_SCHEMA, LtaPartitionFeatureCatalog
        if self.payload_schema != LTA_PARTITION_FEATURE_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unexpected LTA partition payload schema.")
        if isinstance(self._resolved_payload, LtaPartitionFeatureCatalog):
            return self._resolved_payload
        result = LtaPartitionFeatureCatalog.from_dict(self.payload_mapping)
        self.bind_scientific_payload(result)
        return result

    def as_lta_selection(self):
        if self.extension_id != "lta" or self.stage is not ProfileFeatureStage.SELECTION:
            raise TrainingDataInputError("Profile feature is not an LTA selection catalog.")
        from .lta_selection import LTA_SELECTION_FEATURE_CATALOG_SCHEMA, LtaSelectionFeatureCatalog
        if self.payload_schema != LTA_SELECTION_FEATURE_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unexpected LTA selection payload schema.")
        if isinstance(self._resolved_payload, LtaSelectionFeatureCatalog):
            return self._resolved_payload
        result = LtaSelectionFeatureCatalog.from_dict(self.payload_mapping)
        self.bind_scientific_payload(result)
        return result

    def frame_feature_vector(self, frame_uid: str) -> tuple[tuple[str, ...], tuple[float, ...], tuple[bool, ...]]:
        """Return the extension provider's standardized frame vector."""
        if self.extension_id == "lta" and self.stage is ProfileFeatureStage.SELECTION:
            record = self.as_lta_selection().for_frame(frame_uid)
            names = tuple(f"lta:{name}" for name in record.feature_names)
            return names, tuple(float(v) for v in record.vector), tuple(bool(v) for v in record.missing_mask)
        raise TrainingDataInputError(
            f"Extension {self.extension_id!r} does not expose a standardized frame-feature adapter."
        )

    def atomic_environment_descriptors(self) -> tuple[Any, ...]:
        """Return provider-owned atomic environments through the common adapter."""
        if self.extension_id == "lta" and self.stage is ProfileFeatureStage.SELECTION:
            return tuple(self.as_lta_selection().atomic_environment_descriptors)
        return ()

    def environment_class_labels(self, frame_uids: tuple[str, ...] | set[str]) -> tuple[str, ...]:
        selected = set(frame_uids)
        if self.extension_id == "lta" and self.stage is ProfileFeatureStage.SELECTION:
            catalog = self.as_lta_selection()
            return tuple(sorted({
                label
                for frame_uid in selected
                for label in catalog.environment_class_labels_for_frame(frame_uid)
            }))
        return ()


def _provider_identity(*, extension_id: str, stage: ProfileFeatureStage, configuration_digest: str) -> MaterialProfileProviderIdentity:
    return MaterialProfileProviderIdentity(
        provider_id=f"mdstats.profile.{extension_id}.{stage.value}",
        provider_version=PROFILE_FEATURE_PROVIDER_VERSION,
        configuration_digest=configuration_digest,
    )


def wrap_lta_partition_features(catalog: Any) -> ProfileFeatureCatalog:
    from .lta_profile import LTA_PARTITION_FEATURE_CATALOG_SCHEMA

    result = ProfileFeatureCatalog(
        extension_id="lta",
        stage=ProfileFeatureStage.PARTITION,
        provider_identity=_provider_identity(
            extension_id="lta",
            stage=ProfileFeatureStage.PARTITION,
            configuration_digest=catalog.policy.policy_digest,
        ),
        frame_catalog_digest=catalog.frame_catalog_digest,
        payload_schema=LTA_PARTITION_FEATURE_CATALOG_SCHEMA,
        payload=None,
        scientific_payload_digest_value=catalog.content_digest,
        notes=("Optional LTA partition extension; scientific payload is stored once by DATA4.",),
    )
    return result.bind_scientific_payload(catalog)


def wrap_lta_selection_features(
    catalog: Any,
    *,
    data4_bundle_digest: str,
    embed_payload: bool = True,
) -> ProfileFeatureCatalog:
    from .lta_selection import LTA_SELECTION_FEATURE_CATALOG_SCHEMA

    # Standalone extension records embed their payload and therefore round-trip
    # without an owning DATA6 bundle. Production DATA6 keeps one scientific
    # catalog and a digest-only wrapper; its sharded store persists the catalog
    # once, while Data6FeatureBundle.to_dict() embeds on demand for compatibility.
    result = ProfileFeatureCatalog(
        extension_id="lta",
        stage=ProfileFeatureStage.SELECTION,
        provider_identity=_provider_identity(
            extension_id="lta",
            stage=ProfileFeatureStage.SELECTION,
            configuration_digest=catalog.policy.policy_digest,
        ),
        frame_catalog_digest=catalog.frame_catalog_digest,
        parent_bundle_digest=data4_bundle_digest,
        payload_schema=LTA_SELECTION_FEATURE_CATALOG_SCHEMA,
        payload=catalog.to_dict() if embed_payload else None,
        scientific_payload_digest_value=catalog.content_digest,
        notes=(
            "Optional LTA selection extension; scientific payload is "
            + ("embedded for standalone use." if embed_payload else "stored once by DATA6."),
        ),
    )
    return result.bind_scientific_payload(catalog)


def normalize_profile_feature_catalogs(
    catalogs: tuple[ProfileFeatureCatalog, ...],
    *,
    stage: ProfileFeatureStage,
    contracts: MaterialProfileContracts | None,
) -> tuple[ProfileFeatureCatalog, ...]:
    result = tuple(sorted(catalogs, key=lambda item: (item.extension_id, item.provider_identity.content_digest)))
    if len({(item.extension_id, item.provider_identity.content_digest) for item in result}) != len(result):
        raise TrainingDataInputError("Profile feature catalogs must have unique extension/provider identities.")
    for item in result:
        if item.stage is not stage:
            raise TrainingDataInputError("Profile feature catalog appears in the wrong workflow stage.")
        if contracts is None:
            if item.extension_id == "lta":
                continue  # legacy compatibility; production profile gates remain explicit
            raise TrainingDataInputError("Optional profile features require explicit material-profile contracts.")
        if item.extension_id not in contracts.profile.extensions:
            if item.extension_id == "lta":
                raise TrainingDataInputError(
                    "LTA partition features require a material profile with the explicit lta extension."
                )
            raise TrainingDataInputError(
                f"Profile feature extension {item.extension_id!r} is not activated by the material profile."
            )
    return result


def find_profile_feature(
    catalogs: tuple[ProfileFeatureCatalog, ...],
    extension_id: str,
) -> ProfileFeatureCatalog | None:
    matches = [item for item in catalogs if item.extension_id == str(extension_id).strip().lower()]
    if len(matches) > 1:
        raise TrainingDataInputError("Multiple providers supplied the same extension; an explicit provider choice is required.")
    return None if not matches else matches[0]


def profile_partition_state_changed(
    catalogs: tuple[ProfileFeatureCatalog, ...],
    frame_uids: tuple[str, ...] | list[str],
) -> bool:
    """Ask optional extension adapters whether a slow structural state changed."""

    for catalog in catalogs:
        if catalog.extension_id == "lta" and catalog.stage is ProfileFeatureStage.PARTITION:
            typed = catalog.as_lta_partition()
            for frame_uid in frame_uids:
                record = typed.for_frame(frame_uid)
                if record.coordination_change or record.site_change or record.ring_crossing:
                    return True
    return False
