"""DATA4 feature bundle, canonical cache, and VASP/ASE integration."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping, TYPE_CHECKING

import numpy as np

from ._common import sha256_file_cached
from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    canonical_json,
    digest,
    validate_digest,
)
from .events import (
    EventDetectionPolicy,
    FullResolutionEventCatalog,
    detect_full_resolution_events,
)
from .frame_catalog import (
    FrameData,
    TrainingFrameCatalog,
    build_training_frame_catalog,
)
if TYPE_CHECKING:
    from .lta_profile import LtaPartitionFeatureCatalog, LtaPartitionProfilePolicy
from .raw_features import RawFeatureCatalog, RawFeaturePolicy, build_raw_feature_catalog
from .material_profiles import MaterialProfileContracts
from .profile_extensions import (
    ProfileFeatureCatalog, ProfileFeatureStage, find_profile_feature,
    normalize_profile_feature_catalogs, wrap_lta_partition_features,
)
from .role_budget import PartitionRoleBudgetPolicy

DATA4_FEATURE_BUNDLE_SCHEMA = "mdstats.data4-feature-bundle.v4"
DATA4_FEATURE_BUNDLE_V3_SCHEMA = "mdstats.data4-feature-bundle.v3"
DATA4_FEATURE_BUNDLE_V2_SCHEMA = "mdstats.data4-feature-bundle.v2"
DATA4_FEATURE_BUNDLE_LEGACY_SCHEMA = "mdstats.data4-feature-bundle.v1"
FEATURE_CACHE_FILE_RECORD_SCHEMA = "mdstats.feature-cache-file-record.v1"
FEATURE_CACHE_MANIFEST_SCHEMA = "mdstats.feature-cache-manifest.v1"



def _decode_legacy_lta_partition_features(payload: Any) -> "LtaPartitionFeatureCatalog | None":
    if payload is None:
        return None
    from .lta_profile import LtaPartitionFeatureCatalog

    return LtaPartitionFeatureCatalog.from_dict(payload)


@dataclass(frozen=True, slots=True)
class Data4FeatureBundle:
    dataset_id: str
    source_catalog_digest: str
    frame_catalog_digest: str
    raw_features: RawFeatureCatalog
    lta_partition_features: "LtaPartitionFeatureCatalog | None"
    events: FullResolutionEventCatalog
    partition_role_budget: PartitionRoleBudgetPolicy
    material_profile_contracts: MaterialProfileContracts | None = None
    profile_partition_features: tuple[ProfileFeatureCatalog, ...] = ()
    notes: tuple[str, ...] = ()
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_catalog_digest", validate_digest(self.source_catalog_digest, name="source_catalog_digest"))
        object.__setattr__(self, "frame_catalog_digest", validate_digest(self.frame_catalog_digest, name="frame_catalog_digest"))
        if self.raw_features.source_catalog_digest != self.source_catalog_digest or self.raw_features.frame_catalog_digest != self.frame_catalog_digest:
            raise TrainingDataInputError("Raw features do not belong to the DATA4 source/frame catalogs.")
        catalogs = tuple(self.profile_partition_features)
        if self.lta_partition_features is not None:
            if self.lta_partition_features.frame_catalog_digest != self.frame_catalog_digest:
                raise TrainingDataInputError("LTA features do not belong to the DATA4 frame catalog.")
            existing = find_profile_feature(catalogs, "lta")
            if existing is None:
                catalogs = catalogs + (wrap_lta_partition_features(self.lta_partition_features),)
            else:
                embedded = existing.scientific_payload_digest
                if embedded != self.lta_partition_features.content_digest:
                    raise TrainingDataInputError("Legacy and generic LTA partition feature evidence disagree.")
                existing.bind_scientific_payload(self.lta_partition_features)
        catalogs = normalize_profile_feature_catalogs(
            catalogs, stage=ProfileFeatureStage.PARTITION, contracts=self.material_profile_contracts
        ) if catalogs else ()
        for catalog in catalogs:
            if catalog.frame_catalog_digest != self.frame_catalog_digest:
                raise TrainingDataInputError("Profile partition features do not belong to the DATA4 frame catalog.")
        object.__setattr__(self, "profile_partition_features", catalogs)
        lta_extension = find_profile_feature(catalogs, "lta") if catalogs else None
        if self.lta_partition_features is None and lta_extension is not None:
            object.__setattr__(self, "lta_partition_features", lta_extension.as_lta_partition())
        if self.events.frame_catalog_digest != self.frame_catalog_digest or self.events.raw_feature_catalog_digest != self.raw_features.content_digest:
            raise TrainingDataInputError("Event catalog does not belong to the DATA4 feature catalogs.")
        expected_extension_digests = tuple(item.content_digest for item in catalogs)
        if self.events.profile_feature_catalog_digests != expected_extension_digests:
            raise TrainingDataInputError("Event/profile-feature linkage is inconsistent.")
        if self.material_profile_contracts is not None:
            if not self.material_profile_contracts.profile.user_declared:
                raise TrainingDataInputError("DATA4 material profiles must be explicitly user-declared.")
            if self.lta_partition_features is not None and "lta" not in self.material_profile_contracts.profile.extensions:
                raise TrainingDataInputError(
                    "LTA partition features require a material profile with the explicit lta extension."
                )
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    def _identity_payload(self) -> dict[str, Any]:
        """Compact Merkle identity for the potentially very large DATA4 bundle."""

        return {
            "schema": DATA4_FEATURE_BUNDLE_SCHEMA,
            "dataset_id": self.dataset_id,
            "source_catalog_digest": self.source_catalog_digest,
            "frame_catalog_digest": self.frame_catalog_digest,
            "raw_feature_catalog_digest": self.raw_features.content_digest,
            "profile_partition_features": [item.to_dict() for item in self.profile_partition_features],
            "profile_scientific_payload_digests": {
                item.extension_id: item.scientific_payload_digest
                for item in self.profile_partition_features
            },
            "event_catalog_digest": self.events.content_digest,
            "partition_role_budget": self.partition_role_budget.to_dict(),
            "material_profile_contracts_digest": (
                None if self.material_profile_contracts is None
                else self.material_profile_contracts.content_digest
            ),
            "notes": list(self.notes),
        }

    def _profile_partition_payloads(self) -> dict[str, Any]:
        payloads: dict[str, Any] = {}
        for catalog in self.profile_partition_features:
            if catalog.payload_embedded:
                continue
            if catalog.extension_id == "lta" and self.lta_partition_features is not None:
                payloads[catalog.extension_id] = self.lta_partition_features.to_dict()
            else:
                payloads[catalog.extension_id] = dict(catalog.payload_mapping)
        return payloads

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": DATA4_FEATURE_BUNDLE_SCHEMA,
            "dataset_id": self.dataset_id,
            "source_catalog_digest": self.source_catalog_digest,
            "frame_catalog_digest": self.frame_catalog_digest,
            "raw_features": self.raw_features.to_dict(),
            "profile_partition_features": [item.to_dict() for item in self.profile_partition_features],
            "profile_partition_payloads": self._profile_partition_payloads(),
            "events": self.events.to_dict(),
            "partition_role_budget": self.partition_role_budget.to_dict(),
            "material_profile_contracts": None if self.material_profile_contracts is None else self.material_profile_contracts.to_dict(),
            "notes": list(self.notes),
        }

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
    def from_dict(cls, payload: Mapping[str, Any]) -> "Data4FeatureBundle":
        schema = payload.get("schema")
        supported = {
            DATA4_FEATURE_BUNDLE_SCHEMA,
            DATA4_FEATURE_BUNDLE_V3_SCHEMA,
            DATA4_FEATURE_BUNDLE_V2_SCHEMA,
            DATA4_FEATURE_BUNDLE_LEGACY_SCHEMA,
        }
        if schema not in supported:
            raise TrainingDataSerializationError("Unsupported DATA4 feature-bundle schema.")

        profile_catalogs = tuple(
            ProfileFeatureCatalog.from_dict(item)
            for item in payload.get("profile_partition_features", ())
        )
        lta_partition = _decode_legacy_lta_partition_features(
            payload.get("lta_partition_features")
        )
        if schema == DATA4_FEATURE_BUNDLE_SCHEMA:
            profile_payloads = payload.get("profile_partition_payloads", {})
            if not isinstance(profile_payloads, Mapping):
                raise TrainingDataSerializationError("DATA4 profile payload table must be a mapping.")
            lta_payload = profile_payloads.get("lta")
            if lta_payload is not None:
                lta_partition = _decode_legacy_lta_partition_features(lta_payload)
                lta_ref = find_profile_feature(profile_catalogs, "lta")
                if lta_ref is None:
                    raise TrainingDataSerializationError("DATA4 LTA payload lacks its profile reference.")
                lta_ref.bind_scientific_payload(lta_partition)

        result = cls(
            dataset_id=str(payload["dataset_id"]),
            source_catalog_digest=str(payload["source_catalog_digest"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            raw_features=RawFeatureCatalog.from_dict(payload["raw_features"]),
            lta_partition_features=lta_partition,
            events=FullResolutionEventCatalog.from_dict(payload["events"]),
            partition_role_budget=PartitionRoleBudgetPolicy.from_dict(payload["partition_role_budget"]),
            material_profile_contracts=None if payload.get("material_profile_contracts") is None else MaterialProfileContracts.from_dict(payload["material_profile_contracts"]),
            profile_partition_features=profile_catalogs,
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        supplied_digest = payload.get("content_digest")
        if schema == DATA4_FEATURE_BUNDLE_SCHEMA:
            if supplied_digest not in (None, result.content_digest):
                raise TrainingDataSerializationError("DATA4 feature-bundle digest mismatch.")
            return result

        # Legacy bundles used a digest over their complete embedded payload.
        raw_payload_digest = digest({key: value for key, value in payload.items() if key != "content_digest"})
        if supplied_digest == raw_payload_digest:
            return result
        legacy_payload = {
            "schema": schema,
            "dataset_id": result.dataset_id,
            "source_catalog_digest": result.source_catalog_digest,
            "frame_catalog_digest": result.frame_catalog_digest,
            "raw_features": result.raw_features.to_dict(),
            "lta_partition_features": None if result.lta_partition_features is None else result.lta_partition_features.to_dict(),
            "events": payload["events"],
            "partition_role_budget": result.partition_role_budget.to_dict(),
            **({} if schema == DATA4_FEATURE_BUNDLE_LEGACY_SCHEMA else {"material_profile_contracts": None if result.material_profile_contracts is None else result.material_profile_contracts.to_dict()}),
            "notes": list(result.notes),
        }
        if supplied_digest not in (None, digest(legacy_payload)):
            raise TrainingDataSerializationError("DATA4 feature-bundle digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class FeatureCacheFileRecord:
    relative_path: str
    sha256: str
    content_digest: str

    def __post_init__(self) -> None:
        path = Path(self.relative_path)
        if path.is_absolute() or ".." in path.parts or self.relative_path in {"", "."}:
            raise TrainingDataInputError("Feature-cache relative_path must remain inside the cache root.")
        object.__setattr__(self, "sha256", validate_digest(self.sha256, name="sha256"))
        object.__setattr__(self, "content_digest", validate_digest(self.content_digest, name="content_digest"))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": FEATURE_CACHE_FILE_RECORD_SCHEMA,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "content_digest": self.content_digest,
        }
        return {**payload, "record_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FeatureCacheFileRecord":
        if payload.get("schema") != FEATURE_CACHE_FILE_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported feature-cache-file schema.")
        result = cls(
            relative_path=str(payload["relative_path"]),
            sha256=str(payload["sha256"]),
            content_digest=str(payload["content_digest"]),
        )
        expected = result.to_dict()["record_digest"]
        if payload.get("record_digest") not in (None, expected):
            raise TrainingDataSerializationError("Feature-cache-file record digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class FeatureCacheManifest:
    dataset_id: str
    bundle_digest: str
    files: tuple[FeatureCacheFileRecord, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "bundle_digest", validate_digest(self.bundle_digest, name="bundle_digest"))
        files = tuple(sorted(self.files, key=lambda item: item.relative_path))
        if len({item.relative_path for item in files}) != len(files):
            raise TrainingDataInputError("Feature-cache paths must be unique.")
        object.__setattr__(self, "files", files)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FEATURE_CACHE_MANIFEST_SCHEMA,
            "dataset_id": self.dataset_id,
            "bundle_digest": self.bundle_digest,
            "files": [item.to_dict() for item in self.files],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FeatureCacheManifest":
        if payload.get("schema") != FEATURE_CACHE_MANIFEST_SCHEMA:
            raise TrainingDataSerializationError("Unsupported feature-cache-manifest schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            bundle_digest=str(payload["bundle_digest"]),
            files=tuple(FeatureCacheFileRecord.from_dict(item) for item in payload.get("files", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Feature-cache-manifest digest mismatch.")
        return result


def build_data4_feature_bundle(
    source_catalog: Any,
    frame_catalog: TrainingFrameCatalog,
    frame_data_by_run: Mapping[str, FrameData],
    *,
    raw_feature_policy: RawFeaturePolicy | None = None,
    lta_profile_policy: "LtaPartitionProfilePolicy | None" = None,
    event_policy: EventDetectionPolicy | None = None,
    partition_role_budget: PartitionRoleBudgetPolicy | None = None,
    material_profile_contracts: MaterialProfileContracts | None = None,
    progress_callback: Callable[[str], None] | None = None,
    parallel_workers: int = 1,
    lta_parallel_workers: int | None = None,
) -> Data4FeatureBundle:
    raw = build_raw_feature_catalog(
        source_catalog,
        frame_catalog,
        frame_data_by_run,
        policy=raw_feature_policy,
        progress_callback=progress_callback,
        parallel_workers=parallel_workers,
    )
    lta = None
    if lta_profile_policy is not None:
        from .lta_profile import build_lta_partition_feature_catalog

        lta = build_lta_partition_feature_catalog(
            frame_catalog,
            frame_data_by_run,
            policy=lta_profile_policy,
            progress_callback=progress_callback,
            parallel_workers=(parallel_workers if lta_parallel_workers is None else lta_parallel_workers),
        )
    profile_partition_features = () if lta is None else (wrap_lta_partition_features(lta),)
    events = detect_full_resolution_events(
        frame_catalog,
        raw,
        lta_features=lta,
        profile_features=profile_partition_features,
        policy=event_policy,
        progress_callback=progress_callback,
    )
    return Data4FeatureBundle(
        dataset_id=frame_catalog.dataset_id,
        source_catalog_digest=source_catalog.content_digest,
        frame_catalog_digest=frame_catalog.content_digest,
        raw_features=raw,
        lta_partition_features=lta,
        events=events,
        partition_role_budget=(
            PartitionRoleBudgetPolicy()
            if partition_role_budget is None
            else partition_role_budget
        ),
        material_profile_contracts=material_profile_contracts,
        profile_partition_features=profile_partition_features,
        notes=(
            "DATA4 features and events are full-resolution and partition-independent; DATA5 owns feasibility and role assignment.",
        ),
    )


def _sha256_file(path: Path) -> str:
    return sha256_file_cached(path)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(canonical_json(payload) + "\n", encoding="utf-8")


def write_data4_feature_cache(bundle: Data4FeatureBundle, directory: str | Path) -> FeatureCacheManifest:
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    payloads: list[tuple[str, Mapping[str, Any], str]] = [
        ("raw_features.json", bundle.raw_features.to_dict(), bundle.raw_features.content_digest),
        ("events.json", bundle.events.to_dict(), bundle.events.content_digest),
        ("partition_role_budget.json", bundle.partition_role_budget.to_dict(), bundle.partition_role_budget.policy_digest),
        ("data4_feature_bundle.json", bundle.to_dict(), bundle.content_digest),
    ]
    insert_at = 1
    if bundle.material_profile_contracts is not None:
        payloads.insert(
            insert_at,
            (
                "material_profile_contracts.json",
                bundle.material_profile_contracts.to_dict(),
                bundle.material_profile_contracts.content_digest,
            ),
        )
        insert_at += 1
    if bundle.profile_partition_features:
        profile_payload = {
            "schema": "mdstats.profile-partition-feature-catalogs.v1",
            "catalogs": [item.to_dict() for item in bundle.profile_partition_features],
        }
        payloads.insert(
            insert_at,
            (
                "profile_partition_features.json",
                profile_payload,
                digest(profile_payload),
            ),
        )
    records: list[FeatureCacheFileRecord] = []
    for relative, payload, content_digest in payloads:
        path = root / relative
        _write_json(path, payload)
        records.append(
            FeatureCacheFileRecord(
                relative_path=relative,
                sha256=_sha256_file(path),
                content_digest=content_digest,
            )
        )
    manifest = FeatureCacheManifest(
        dataset_id=bundle.dataset_id,
        bundle_digest=bundle.content_digest,
        files=tuple(records),
    )
    _write_json(root / "cache_manifest.json", manifest.to_dict())
    return manifest


def read_data4_feature_cache(directory: str | Path) -> tuple[Data4FeatureBundle, FeatureCacheManifest]:
    root = Path(directory).resolve()
    manifest_path = root / "cache_manifest.json"
    if not manifest_path.is_file():
        raise TrainingDataInputError("Feature cache manifest is absent.")
    try:
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TrainingDataSerializationError("Feature cache manifest is invalid.") from exc
    manifest = FeatureCacheManifest.from_dict(manifest_payload)
    payload_by_path: dict[str, Mapping[str, Any]] = {}
    for record in manifest.files:
        path = (root / record.relative_path).resolve()
        if root not in path.parents:
            raise TrainingDataSerializationError("Feature-cache path escaped its root.")
        if not path.is_file() or _sha256_file(path) != record.sha256:
            raise TrainingDataSerializationError(f"Feature-cache hash mismatch: {record.relative_path}.")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise TrainingDataSerializationError(f"Invalid feature-cache file: {record.relative_path}.") from exc
        payload_by_path[record.relative_path] = payload
    if "data4_feature_bundle.json" not in payload_by_path:
        raise TrainingDataSerializationError("Feature cache lacks data4_feature_bundle.json.")
    serialized_bundle_payload = payload_by_path["data4_feature_bundle.json"]
    bundle = Data4FeatureBundle.from_dict(serialized_bundle_payload)
    serialized_bundle_digest = str(serialized_bundle_payload.get("content_digest", bundle.content_digest))
    validate_digest(serialized_bundle_digest, name="serialized_bundle_digest")
    if serialized_bundle_digest != manifest.bundle_digest:
        raise TrainingDataSerializationError("Feature-cache bundle digest mismatch.")
    expected_digests = {
        "raw_features.json": bundle.raw_features.content_digest,
        "events.json": bundle.events.content_digest,
        "partition_role_budget.json": bundle.partition_role_budget.policy_digest,
        "data4_feature_bundle.json": serialized_bundle_digest,
    }
    if bundle.material_profile_contracts is not None:
        expected_digests["material_profile_contracts.json"] = bundle.material_profile_contracts.content_digest
    if bundle.profile_partition_features:
        profile_payload = {
            "schema": "mdstats.profile-partition-feature-catalogs.v1",
            "catalogs": [item.to_dict() for item in bundle.profile_partition_features],
        }
        expected_digests["profile_partition_features.json"] = digest(profile_payload)
    actual = {item.relative_path: item.content_digest for item in manifest.files}
    if actual != expected_digests:
        raise TrainingDataSerializationError("Feature-cache cross-file content digests mismatch.")
    return bundle, manifest


def _control_value(run_controls: Any, name: str) -> Any:
    value = run_controls.effective_value(name)
    return run_controls.explicit_value(name) if value is None else value


def load_vasp_frame_data_by_run(
    source_catalog: Any,
    *,
    base_directory: str | Path = ".",
    strict: bool = True,
) -> tuple[dict[str, FrameData], dict[str, Any]]:
    """Read ASE-backed VASP frames and temperature-target evidence once per source."""

    from mdstats.io import read_vasp_frames, read_vasp_run_controls
    from .conditions import TemperatureTargetEvidence

    base = Path(base_directory)
    frame_data: dict[str, FrameData] = {}
    targets: dict[str, TemperatureTargetEvidence] = {}
    for source in source_catalog.sources:
        path = Path(source.source_locator)
        if not path.is_absolute():
            path = base / path
        controls = read_vasp_run_controls(path)
        if controls.source_identity.signature != source.source_identity_signature:
            raise TrainingDataInputError(f"Source identity changed for {source.run_id!r}.")
        if controls.signature != source.source_control_bundle_signature:
            raise TrainingDataInputError(f"Source control bundle changed for {source.run_id!r}.")
        channel = controls.energy_catalog.channel(source.selected_energy.source_name)
        if channel is None:
            raise TrainingDataInputError(f"Selected energy channel is absent for {source.run_id!r}.")
        collection = read_vasp_frames(
            path,
            strict=strict,
            assess_quality=False,
            assess_stationarity=False,
            assess_admissibility=False,
        )
        frame_data[source.run_id] = FrameData.from_collection(
            collection,
            source_frame_indices=np.arange(collection.n_frames, dtype=np.int64),
            energies_ev=channel.as_array(),
            scf_iteration_limit_reached=controls.numerical_quality_controls.scf_iteration_limit_reached,
        )
        tebeg = _control_value(controls.run_controls, "TEBEG")
        teend = _control_value(controls.run_controls, "TEEND")
        targets[source.run_id] = TemperatureTargetEvidence(
            target_start_kelvin=None if tebeg is None else float(tebeg),
            target_end_kelvin=None if teend is None else float(teend),
            evidence="VASP effective/explicit TEBEG and TEEND",
        )
    return frame_data, targets


def build_vasp_data4_feature_bundle(
    source_catalog: Any,
    *,
    base_directory: str | Path = ".",
    frame_catalog: TrainingFrameCatalog | None = None,
    strict: bool = True,
    **kwargs: Any,
) -> tuple[TrainingFrameCatalog, Data4FeatureBundle]:
    """Build DATA3 and DATA4 from the VASP sources bound by a DATA2 catalog."""

    frame_data, targets = load_vasp_frame_data_by_run(
        source_catalog,
        base_directory=base_directory,
        strict=strict,
    )
    if frame_catalog is None:
        frame_catalog = build_training_frame_catalog(
            source_catalog,
            frame_data,
            temperature_targets_by_run=targets,
        )
    elif frame_catalog.source_catalog_digest != source_catalog.content_digest:
        raise TrainingDataInputError("Provided frame catalog belongs to another source catalog.")
    bundle = build_data4_feature_bundle(
        source_catalog,
        frame_catalog,
        frame_data,
        **kwargs,
    )
    return frame_catalog, bundle
