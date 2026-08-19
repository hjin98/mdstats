"""Memory-bounded persistence for large DATA4 campaign records.

The public DATA4 schema remains unchanged.  This module is an internal campaign
storage codec that persists the large record sequences as checksummed JSONL
shards, avoiding construction of a second giant nested ``dict`` merely to put
or restore campaign state.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Callable, Iterable, Mapping, TypeVar

from .progress_timing import format_progress_fraction
from ._common import canonical_json, sha256_file_cached
from .data4_bundle import Data4FeatureBundle
from .events import EventDetectionPolicy, FrameEventRecord, FullResolutionEventCatalog
from .lta_profile import (
    LtaFramePartitionRecord,
    LtaMobileSiteState,
    LtaPartitionFeatureCatalog,
    LtaPartitionProfilePolicy,
)
from .material_profiles import MaterialProfileContracts
from .profile_extensions import ProfileFeatureCatalog
from .raw_features import RawFeatureCatalog, RawFeaturePolicy, RawFrameFeatureRecord
from .role_budget import PartitionRoleBudgetPolicy

DATA4_SHARDED_MANIFEST_SCHEMA = "mdstats.mlff-data4-sharded-record.v1"
DATA4_SHARDED_POINTER_SCHEMA = "mdstats.mlff-campaign-data4-sharded-pointer.v1"

T = TypeVar("T")


def _strip_content_digests(value: Any) -> None:
    """Remove redundant per-object integrity fields after shard SHA verification."""

    if isinstance(value, dict):
        value.pop("content_digest", None)
        for child in value.values():
            _strip_content_digests(child)
    elif isinstance(value, list):
        for child in value:
            _strip_content_digests(child)


def _trusted_record_from_dict(cls: type[T], payload: Mapping[str, Any]) -> T:
    mutable = dict(payload)
    supplied = mutable.get("content_digest")
    _strip_content_digests(mutable)
    result = cls.from_dict(mutable)
    if supplied is not None and hasattr(result, "_content_digest_cache"):
        object.__setattr__(result, "_content_digest_cache", str(supplied))
    return result


class Data4ShardedStoreError(RuntimeError):
    """Raised when an internal DATA4 shard is absent, corrupt, or inconsistent."""


def _sha256_file(path: Path) -> str:
    return sha256_file_cached(path)


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(canonical_json(payload))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _write_jsonl(path: Path, values: Iterable[Any], converter: Callable[[Any], Mapping[str, Any]]) -> tuple[int, str, int]:
    hasher = hashlib.sha256()
    count = 0
    size = 0
    with path.open("wb") as handle:
        for value in values:
            line = (canonical_json(converter(value)) + "\n").encode("utf-8")
            handle.write(line)
            hasher.update(line)
            size += len(line)
            count += 1
        handle.flush()
        os.fsync(handle.fileno())
    return count, hasher.hexdigest(), size


def _read_jsonl(
    root: Path,
    descriptor: Mapping[str, Any],
    converter: Callable[[Mapping[str, Any]], T],
    *,
    label: str,
    progress_callback: Callable[[str], None] | None = None,
) -> tuple[T, ...]:
    relative = Path(str(descriptor.get("relative_path", "")))
    if relative.is_absolute() or ".." in relative.parts or relative in {Path(""), Path(".")}:
        raise Data4ShardedStoreError(f"Invalid {label} shard path.")
    path = (root / relative).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise Data4ShardedStoreError(f"Missing {label} shard: {path}")
    expected_hash = str(descriptor.get("sha256", ""))
    if not expected_hash or _sha256_file(path) != expected_hash:
        raise Data4ShardedStoreError(f"Checksum mismatch for {label} shard: {path}")
    expected_count = int(descriptor.get("count", -1))
    output: list[T] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise Data4ShardedStoreError(
                    f"Invalid JSON in {label} shard at line {line_number}: {path}"
                ) from exc
            if not isinstance(payload, Mapping):
                raise Data4ShardedStoreError(f"Invalid record in {label} shard: {path}")
            output.append(converter(payload))
            if progress_callback is not None and len(output) % 100_000 == 0:
                progress_callback(f"restore; status=progress; progress={format_progress_fraction(len(output), expected_count)}; kind={label}")
    if progress_callback is not None:
        progress_callback(f"restore; status=progress; progress={format_progress_fraction(len(output), expected_count)}; kind={label}")
    if len(output) != expected_count:
        raise Data4ShardedStoreError(
            f"Record count mismatch for {label} shard: expected {expected_count}, read {len(output)}."
        )
    return tuple(output)


def _validate_existing_sharded_directory(
    destination: Path,
    *,
    expected_content_digest: str,
    expected_record_key: str,
) -> Path:
    """Validate a pre-existing content-addressed DATA4 directory before reuse."""

    manifest_path = destination / "manifest.json"
    if not manifest_path.is_file():
        raise Data4ShardedStoreError(f"Missing DATA4 sharded manifest: {manifest_path}")
    try:
        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise Data4ShardedStoreError(f"Could not read DATA4 sharded manifest: {manifest_path}") from exc
    if not isinstance(manifest, Mapping) or manifest.get("schema") != DATA4_SHARDED_MANIFEST_SCHEMA:
        raise Data4ShardedStoreError(f"Invalid DATA4 sharded manifest: {manifest_path}")
    if str(manifest.get("content_digest", "")) != expected_content_digest:
        raise Data4ShardedStoreError(
            "Existing DATA4 shard directory has the wrong content digest: "
            f"{destination}"
        )
    if str(manifest.get("record_key", "")) != expected_record_key:
        raise Data4ShardedStoreError(
            "Existing DATA4 shard directory has the wrong record key: "
            f"{destination}"
        )

    descriptors: list[tuple[str, Mapping[str, Any]]] = []
    raw = manifest.get("raw")
    events = manifest.get("events")
    if not isinstance(raw, Mapping) or not isinstance(raw.get("records"), Mapping):
        raise Data4ShardedStoreError(f"Invalid raw-feature descriptor: {manifest_path}")
    if not isinstance(events, Mapping) or not isinstance(events.get("records"), Mapping):
        raise Data4ShardedStoreError(f"Invalid event descriptor: {manifest_path}")
    descriptors.extend((("raw-feature", raw["records"]), ("event", events["records"])))
    lta = manifest.get("lta")
    if lta is not None:
        if not isinstance(lta, Mapping):
            raise Data4ShardedStoreError(f"Invalid LTA descriptor: {manifest_path}")
        for name, key in (("LTA frame", "frame_records"), ("LTA mobile-state", "mobile_states")):
            descriptor = lta.get(key)
            if not isinstance(descriptor, Mapping):
                raise Data4ShardedStoreError(f"Invalid {name} descriptor: {manifest_path}")
            descriptors.append((name, descriptor))

    root = destination.resolve()
    for label, descriptor in descriptors:
        relative = Path(str(descriptor.get("relative_path", "")))
        if relative.is_absolute() or ".." in relative.parts or relative in {Path(""), Path(".")}:
            raise Data4ShardedStoreError(f"Invalid {label} shard path in {manifest_path}")
        shard = (root / relative).resolve()
        if root not in shard.parents or not shard.is_file():
            raise Data4ShardedStoreError(f"Missing {label} shard: {shard}")
        expected_hash = str(descriptor.get("sha256", ""))
        expected_size = int(descriptor.get("size_bytes", -1))
        if not expected_hash or _sha256_file(shard) != expected_hash:
            raise Data4ShardedStoreError(f"Checksum mismatch for {label} shard: {shard}")
        if expected_size < 0 or shard.stat().st_size != expected_size:
            raise Data4ShardedStoreError(f"Size mismatch for {label} shard: {shard}")
    return manifest_path


def write_data4_sharded_record(
    bundle: Data4FeatureBundle,
    records_root: str | Path,
    *,
    record_key: str = "data4",
) -> dict[str, Any]:
    """Persist DATA4 without materializing its complete nested dictionary."""

    root = Path(records_root)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"data4-{bundle.content_digest}"
    if destination.is_dir():
        try:
            manifest_path = _validate_existing_sharded_directory(
                destination,
                expected_content_digest=bundle.content_digest,
                expected_record_key=record_key,
            )
        except Data4ShardedStoreError:
            shutil.rmtree(destination, ignore_errors=True)
        else:
            return {
                "schema": DATA4_SHARDED_POINTER_SCHEMA,
                "relative_path": str(manifest_path.relative_to(root.parent)),
                "sha256": _sha256_file(manifest_path),
                "content_digest": bundle.content_digest,
                "record_key": record_key,
            }

    temporary = Path(tempfile.mkdtemp(prefix="data4-write-", dir=root))
    try:
        raw_desc = _write_jsonl(
            temporary / "raw-records.jsonl", bundle.raw_features.records, lambda item: item.to_dict()
        )
        event_desc = _write_jsonl(
            temporary / "events.jsonl", bundle.events.events, lambda item: item.to_dict()
        )
        lta_frame_desc: tuple[int, str, int] | None = None
        lta_mobile_desc: tuple[int, str, int] | None = None
        if bundle.lta_partition_features is not None:
            lta_frame_desc = _write_jsonl(
                temporary / "lta-frame-records.jsonl",
                bundle.lta_partition_features.frame_records,
                lambda item: item._payload(),
            )
            lta_mobile_desc = _write_jsonl(
                temporary / "lta-mobile-states.jsonl",
                bundle.lta_partition_features.mobile_states,
                lambda item: item._payload(),
            )

        def descriptor(filename: str, values: tuple[int, str, int]) -> dict[str, Any]:
            count, sha256, size = values
            return {
                "relative_path": filename,
                "count": count,
                "sha256": sha256,
                "size_bytes": size,
            }

        manifest: dict[str, Any] = {
            "schema": DATA4_SHARDED_MANIFEST_SCHEMA,
            "record_key": record_key,
            "content_digest": bundle.content_digest,
            "dataset_id": bundle.dataset_id,
            "source_catalog_digest": bundle.source_catalog_digest,
            "frame_catalog_digest": bundle.frame_catalog_digest,
            "raw": {
                "content_digest": bundle.raw_features.content_digest,
                "policy": bundle.raw_features.policy.to_dict(),
                "records": descriptor("raw-records.jsonl", raw_desc),
            },
            "lta": None,
            "events": {
                "content_digest": bundle.events.content_digest,
                "raw_feature_catalog_digest": bundle.events.raw_feature_catalog_digest,
                "lta_feature_catalog_digest": bundle.events.lta_feature_catalog_digest,
                "profile_feature_catalog_digests": list(bundle.events.profile_feature_catalog_digests),
                "policy": bundle.events.policy.to_dict(),
                "records": descriptor("events.jsonl", event_desc),
            },
            "profile_partition_features": [item.to_dict() for item in bundle.profile_partition_features],
            "partition_role_budget": bundle.partition_role_budget.to_dict(),
            "material_profile_contracts": (
                None if bundle.material_profile_contracts is None
                else bundle.material_profile_contracts.to_dict()
            ),
            "notes": list(bundle.notes),
        }
        if bundle.lta_partition_features is not None:
            assert lta_frame_desc is not None and lta_mobile_desc is not None
            manifest["lta"] = {
                "content_digest": bundle.lta_partition_features.content_digest,
                "policy": bundle.lta_partition_features.policy.to_dict(),
                "frame_records": descriptor("lta-frame-records.jsonl", lta_frame_desc),
                "mobile_states": descriptor("lta-mobile-states.jsonl", lta_mobile_desc),
            }
        _write_json_atomic(temporary / "manifest.json", manifest)
        if destination.exists():
            shutil.rmtree(temporary)
        else:
            os.replace(temporary, destination)
        manifest_path = destination / "manifest.json"
        return {
            "schema": DATA4_SHARDED_POINTER_SCHEMA,
            "relative_path": str(manifest_path.relative_to(root.parent)),
            "sha256": _sha256_file(manifest_path),
            "content_digest": bundle.content_digest,
            "record_key": record_key,
        }
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def read_data4_sharded_record(
    pointer: Mapping[str, Any],
    state_root: str | Path,
    *,
    progress_callback: Callable[[str], None] | None = None,
) -> Data4FeatureBundle:
    """Restore and verify a sharded DATA4 campaign record."""

    if pointer.get("schema") != DATA4_SHARDED_POINTER_SCHEMA:
        raise Data4ShardedStoreError("Unsupported DATA4 sharded pointer schema.")
    state_root_path = Path(state_root).resolve()
    relative = Path(str(pointer.get("relative_path", "")))
    if relative.is_absolute() or ".." in relative.parts:
        raise Data4ShardedStoreError("DATA4 sharded pointer escapes the campaign state directory.")
    manifest_path = (state_root_path / relative).resolve()
    if state_root_path not in manifest_path.parents or not manifest_path.is_file():
        raise Data4ShardedStoreError(f"Missing DATA4 sharded manifest: {manifest_path}")
    expected_manifest_hash = str(pointer.get("sha256", ""))
    if not expected_manifest_hash or _sha256_file(manifest_path) != expected_manifest_hash:
        raise Data4ShardedStoreError(f"DATA4 sharded manifest checksum mismatch: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, Mapping) or manifest.get("schema") != DATA4_SHARDED_MANIFEST_SCHEMA:
        raise Data4ShardedStoreError("Invalid DATA4 sharded manifest.")
    shard_root = manifest_path.parent

    raw_meta = manifest["raw"]
    raw_records = _read_jsonl(
        shard_root, raw_meta["records"], lambda payload: _trusted_record_from_dict(RawFrameFeatureRecord, payload), label="raw-feature",
        progress_callback=progress_callback,
    )
    raw = RawFeatureCatalog(
        dataset_id=str(manifest["dataset_id"]),
        source_catalog_digest=str(manifest["source_catalog_digest"]),
        frame_catalog_digest=str(manifest["frame_catalog_digest"]),
        policy=RawFeaturePolicy.from_dict(raw_meta["policy"]),
        records=raw_records,
    )
    object.__setattr__(raw, "_content_digest_cache", str(raw_meta["content_digest"]))

    lta: LtaPartitionFeatureCatalog | None = None
    lta_meta = manifest.get("lta")
    if lta_meta is not None:
        lta_frames = _read_jsonl(
            shard_root,
            lta_meta["frame_records"],
            lambda payload: _trusted_record_from_dict(LtaFramePartitionRecord, payload),
            label="LTA frame",
            progress_callback=progress_callback,
        )
        lta_states = _read_jsonl(
            shard_root,
            lta_meta["mobile_states"],
            lambda payload: _trusted_record_from_dict(LtaMobileSiteState, payload),
            label="LTA mobile-state",
            progress_callback=progress_callback,
        )
        lta = LtaPartitionFeatureCatalog(
            dataset_id=str(manifest["dataset_id"]),
            frame_catalog_digest=str(manifest["frame_catalog_digest"]),
            policy=LtaPartitionProfilePolicy.from_dict(lta_meta["policy"]),
            frame_records=lta_frames,
            mobile_states=lta_states,
        )
        object.__setattr__(lta, "_content_digest_cache", str(lta_meta["content_digest"]))

    event_meta = manifest["events"]
    events = FullResolutionEventCatalog(
        dataset_id=str(manifest["dataset_id"]),
        frame_catalog_digest=str(manifest["frame_catalog_digest"]),
        raw_feature_catalog_digest=str(event_meta["raw_feature_catalog_digest"]),
        lta_feature_catalog_digest=(
            None if event_meta.get("lta_feature_catalog_digest") is None
            else str(event_meta["lta_feature_catalog_digest"])
        ),
        policy=EventDetectionPolicy.from_dict(event_meta["policy"]),
        events=_read_jsonl(
            shard_root, event_meta["records"], lambda payload: _trusted_record_from_dict(FrameEventRecord, payload), label="event",
            progress_callback=progress_callback,
        ),
        profile_feature_catalog_digests=tuple(
            str(value) for value in event_meta.get("profile_feature_catalog_digests", ())
        ),
    )
    object.__setattr__(events, "_content_digest_cache", str(event_meta["content_digest"]))

    result = Data4FeatureBundle(
        dataset_id=str(manifest["dataset_id"]),
        source_catalog_digest=str(manifest["source_catalog_digest"]),
        frame_catalog_digest=str(manifest["frame_catalog_digest"]),
        raw_features=raw,
        lta_partition_features=lta,
        events=events,
        partition_role_budget=PartitionRoleBudgetPolicy.from_dict(manifest["partition_role_budget"]),
        material_profile_contracts=(
            None if manifest.get("material_profile_contracts") is None
            else MaterialProfileContracts.from_dict(manifest["material_profile_contracts"])
        ),
        profile_partition_features=tuple(
            ProfileFeatureCatalog.from_dict(item)
            for item in manifest.get("profile_partition_features", ())
        ),
        notes=tuple(str(value) for value in manifest.get("notes", ())),
    )
    expected = str(pointer.get("content_digest", manifest.get("content_digest", "")))
    object.__setattr__(result, "_content_digest_cache", expected)
    if not expected or result.content_digest != expected or result.content_digest != str(manifest["content_digest"]):
        raise Data4ShardedStoreError("DATA4 bundle digest mismatch after sharded restore.")
    return result
