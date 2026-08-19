"""Memory-bounded campaign persistence for large DATA6 records.

The public DATA6 object model remains available.  Campaign persistence stores
large homogeneous sequences as JSONL and universal frame matrices as native
NumPy arrays, avoiding ``Data6FeatureBundle.to_dict()`` and the duplicate
multi-gigabyte Python object graph that operation would create.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Callable, Iterable, Mapping, TypeVar

import numpy as np

from .progress_timing import format_progress_fraction
from ._common import canonical_json, digest, sha256_file_cached
from .data6_bundle import Data6FeatureBundle, Data6Policy
from .difficulty import (
    BlindedEvaluationPredictionCatalog,
    BlindedPredictionDomain,
    DifficultyFrameRecord,
    ModelPredictionSummary,
    TrainingDifficultyDomain,
    TrainingDifficultyFeatureCatalog,
)
from .lta_selection import (
    LtaAtomicEnvironmentDescriptor,
    LtaFrameSelectionDescriptor,
    LtaSelectionFeatureCatalog,
    LtaSelectionPolicy,
)
from .model_features import (
    MaceDescriptorFileRecord,
    MaceDescriptorManifest,
    MaceDescriptorPolicy,
    ModelCheckpointIdentity,
)
from .phase_geometry_profiles import PhaseGeometrySelectionPlan
from .production_model_sweep import (
    AtomicModelPredictionFileRecord,
    AtomicModelPredictionManifest,
    Data6ModelSweepPlan,
)
from .profile_extensions import ProfileFeatureCatalog
from .structural_selection import (
    GenericStructuralEventRecord,
    StructuralFeatureProviderIdentity,
    UniversalAtomicEnvironmentDescriptor,
    UniversalFrameDescriptorTable,
    UniversalStructuralFeatureCatalog,
    UniversalStructuralSelectionPolicy,
)

DATA6_SHARDED_MANIFEST_SCHEMA = "mdstats.mlff-data6-sharded-record.v1"
DATA6_SHARDED_POINTER_SCHEMA = "mdstats.mlff-campaign-data6-sharded-pointer.v1"

T = TypeVar("T")


class Data6ShardedStoreError(RuntimeError):
    """Raised when a DATA6 campaign shard is missing or inconsistent."""


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


def _write_jsonl(
    path: Path,
    values: Iterable[Any],
    converter: Callable[[Any], Mapping[str, Any]],
) -> dict[str, Any]:
    hasher = hashlib.sha256()
    count = 0
    size = 0
    with path.open("wb") as handle:
        for value in values:
            line = (canonical_json(converter(value)) + "\n").encode("utf-8")
            handle.write(line)
            hasher.update(line)
            count += 1
            size += len(line)
        handle.flush()
        os.fsync(handle.fileno())
    return {
        "relative_path": path.name,
        "count": count,
        "sha256": hasher.hexdigest(),
        "size_bytes": size,
    }


class _HashingBinaryWriter:
    """File-like adapter that hashes bytes as NumPy writes them."""

    def __init__(self, handle: Any) -> None:
        self.handle = handle
        self.hasher = hashlib.sha256()
        self.size = 0

    def write(self, value: bytes | bytearray | memoryview) -> int:
        view = memoryview(value)
        if not view.contiguous:
            view = memoryview(bytes(view))
        written = self.handle.write(view)
        if written:
            self.hasher.update(view[:written])
            self.size += int(written)
        return int(written)

    def flush(self) -> None:
        self.handle.flush()

    def fileno(self) -> int:
        return int(self.handle.fileno())

    def tell(self) -> int:
        return int(self.handle.tell())

    def seek(self, offset: int, whence: int = 0) -> int:
        # np.save only seeks on unusual object-array paths, which are disabled,
        # but supporting the file contract is inexpensive. Rehashing after a
        # backwards seek would be incorrect, so fail closed.
        if whence != 1 or offset != 0:
            raise OSError("Hashing NumPy writer does not support repositioning.")
        return self.tell()


def _write_npy(path: Path, array: np.ndarray) -> dict[str, Any]:
    contiguous = np.ascontiguousarray(array)
    with path.open("wb") as raw_handle:
        handle = _HashingBinaryWriter(raw_handle)
        np.save(handle, contiguous, allow_pickle=False)
        handle.flush()
        os.fsync(handle.fileno())
        file_hash = handle.hasher.hexdigest()
        size_bytes = handle.size
    return {
        "relative_path": path.name,
        "sha256": file_hash,
        "size_bytes": size_bytes,
        "shape": list(contiguous.shape),
        "dtype": contiguous.dtype.str,
    }


def _resolve_shard(root: Path, descriptor: Mapping[str, Any], *, label: str) -> Path:
    relative = Path(str(descriptor.get("relative_path", "")))
    if relative.is_absolute() or ".." in relative.parts or relative in {Path(""), Path(".")}:
        raise Data6ShardedStoreError(f"Invalid {label} shard path.")
    path = (root / relative).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise Data6ShardedStoreError(f"Missing {label} shard: {path}")
    expected_size = int(descriptor.get("size_bytes", -1))
    if expected_size < 0 or path.stat().st_size != expected_size:
        raise Data6ShardedStoreError(f"Size mismatch for {label} shard: {path}")
    expected_hash = str(descriptor.get("sha256", ""))
    if not expected_hash or _sha256_file(path) != expected_hash:
        raise Data6ShardedStoreError(f"Checksum mismatch for {label} shard: {path}")
    return path


def _read_jsonl(
    root: Path,
    descriptor: Mapping[str, Any],
    converter: Callable[[Mapping[str, Any]], T],
    *,
    label: str,
    progress_callback: Callable[[str], None] | None = None,
) -> tuple[T, ...]:
    path = _resolve_shard(root, descriptor, label=label)
    expected_count = int(descriptor.get("count", -1))
    result: list[T] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise Data6ShardedStoreError(
                    f"Invalid JSON in {label} at line {line_number}: {path}"
                ) from exc
            if not isinstance(payload, Mapping):
                raise Data6ShardedStoreError(f"Invalid {label} record: {path}")
            result.append(converter(payload))
            if progress_callback is not None and len(result) % 100_000 == 0:
                progress_callback(
                    f"restore; status=progress; progress={format_progress_fraction(len(result), expected_count)}; kind={label}"
                )
    if len(result) != expected_count:
        raise Data6ShardedStoreError(
            f"Record count mismatch for {label}: expected {expected_count}, read {len(result)}."
        )
    if progress_callback is not None and expected_count:
        progress_callback(f"restore; status=progress; progress={format_progress_fraction(len(result), expected_count)}; kind={label}")
    return tuple(result)


def _read_npy(root: Path, descriptor: Mapping[str, Any], *, label: str) -> np.ndarray:
    path = _resolve_shard(root, descriptor, label=label)
    array = np.load(path, mmap_mode="r", allow_pickle=False)
    expected_shape = tuple(int(value) for value in descriptor.get("shape", ()))
    expected_dtype = str(descriptor.get("dtype", ""))
    if array.shape != expected_shape or array.dtype.str != expected_dtype:
        raise Data6ShardedStoreError(f"Array metadata mismatch for {label}: {path}")
    return array


def _structural_manifest(
    temporary: Path,
    catalog: UniversalStructuralFeatureCatalog,
    index: int,
) -> dict[str, Any]:
    table = catalog.frame_descriptor_table
    prefix = f"structural-{index}"
    return {
        "content_digest": catalog.content_digest,
        "dataset_id": catalog.dataset_id,
        "frame_catalog_digest": catalog.frame_catalog_digest,
        "data4_bundle_digest": catalog.data4_bundle_digest,
        "material_profile_contracts_digest": catalog.material_profile_contracts_digest,
        "atom_group_catalog_digest": catalog.atom_group_catalog_digest,
        "provider_identity": catalog.provider_identity.to_dict(),
        "policy": catalog.policy.to_dict(),
        "parser_version": catalog.parser_version,
        "frame_table": {
            "content_digest": table.content_digest,
            "frame_uids": list(table.frame_uids),
            "frame_record_digests": list(table.frame_record_digests),
            "provider_identity_digest": table.provider_identity_digest,
            "feature_names": list(table.feature_names),
            "warning_codes": [list(value) for value in table.warning_codes],
            "values": _write_npy(temporary / f"{prefix}-values.npy", table.values),
            "missing_mask": _write_npy(
                temporary / f"{prefix}-missing.npy", table.missing_mask
            ),
            "atom_counts": _write_npy(
                temporary / f"{prefix}-atom-counts.npy", table.atom_counts
            ),
        },
        "atomic_environments": _write_jsonl(
            temporary / f"{prefix}-atomic.jsonl",
            catalog.atomic_environment_descriptors,
            lambda item: item.to_dict(),
        ),
        "events": _write_jsonl(
            temporary / f"{prefix}-events.jsonl",
            catalog.events,
            lambda item: item.to_dict(),
        ),
    }


def _lta_manifest(temporary: Path, catalog: LtaSelectionFeatureCatalog) -> dict[str, Any]:
    return {
        "content_digest": catalog.content_digest,
        "dataset_id": catalog.dataset_id,
        "frame_catalog_digest": catalog.frame_catalog_digest,
        "data4_bundle_digest": catalog.data4_bundle_digest,
        "policy": catalog.policy.to_dict(),
        "frames": _write_jsonl(
            temporary / "lta-selection-frames.jsonl",
            catalog.frame_descriptors,
            lambda item: item.to_dict(),
        ),
        "atomic_environments": _write_jsonl(
            temporary / "lta-selection-atomic.jsonl",
            catalog.atomic_environment_descriptors,
            lambda item: item.to_dict(),
        ),
    }


def _manifest_records(
    temporary: Path,
    name: str,
    manifest: Any,
) -> dict[str, Any]:
    payload = {
        key: value
        for key, value in manifest._payload().items()
        if key != "records"
    }
    payload["content_digest"] = manifest.content_digest
    payload["records"] = _write_jsonl(
        temporary / f"{name}-records.jsonl",
        manifest.records,
        lambda item: item.to_dict(),
    )
    return payload


def _difficulty_manifest(
    temporary: Path,
    prefix: str,
    catalogs: Iterable[Any],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, catalog in enumerate(catalogs):
        result.append(
            {
                "content_digest": catalog.content_digest,
                "dataset_id": catalog.dataset_id,
                "frame_catalog_digest": catalog.frame_catalog_digest,
                "domain": catalog.domain.to_dict(),
                "checkpoint_identity": catalog.checkpoint_identity.to_dict(),
                "records": _write_jsonl(
                    temporary / f"{prefix}-{index}-records.jsonl",
                    catalog.records,
                    lambda item: item.to_dict(),
                ),
            }
        )
    return result


def _validate_manifest_shards(root: Path, node: Any, *, prefix: str = "DATA6") -> None:
    """Verify every referenced shard before reusing a content-addressed tree."""

    if isinstance(node, Mapping):
        if {"relative_path", "sha256", "size_bytes"}.issubset(node):
            _resolve_shard(root, node, label=prefix)
            return
        for key, value in node.items():
            _validate_manifest_shards(root, value, prefix=f"{prefix}.{key}")
    elif isinstance(node, (list, tuple)):
        for index, value in enumerate(node):
            _validate_manifest_shards(root, value, prefix=f"{prefix}[{index}]")


def write_data6_sharded_record(
    bundle: Data6FeatureBundle,
    records_root: str | Path,
    *,
    record_key: str = "data6",
) -> dict[str, Any]:
    """Persist DATA6 without materializing the complete nested mapping."""

    root = Path(records_root)
    root.mkdir(parents=True, exist_ok=True)
    content_digest = bundle.content_digest
    destination = root / f"data6-{content_digest}"
    manifest_path = destination / "manifest.json"
    if manifest_path.is_file():
        try:
            with manifest_path.open("r", encoding="utf-8") as handle:
                existing = json.load(handle)
            if (
                isinstance(existing, Mapping)
                and existing.get("schema") == DATA6_SHARDED_MANIFEST_SCHEMA
                and existing.get("content_digest") == content_digest
                and existing.get("record_key") == record_key
            ):
                _validate_manifest_shards(destination, existing)
                return {
                    "schema": DATA6_SHARDED_POINTER_SCHEMA,
                    "relative_path": str(manifest_path.relative_to(root.parent)),
                    "sha256": _sha256_file(manifest_path),
                    "content_digest": content_digest,
                    "record_key": record_key,
                }
        except (OSError, json.JSONDecodeError, Data6ShardedStoreError):
            pass
        shutil.rmtree(destination, ignore_errors=True)

    temporary = Path(tempfile.mkdtemp(prefix="data6-write-", dir=root))
    try:
        manifest: dict[str, Any] = {
            "schema": DATA6_SHARDED_MANIFEST_SCHEMA,
            "record_key": record_key,
            "content_digest": content_digest,
            "dataset_id": bundle.dataset_id,
            "source_catalog_digest": bundle.source_catalog_digest,
            "frame_catalog_digest": bundle.frame_catalog_digest,
            "data4_bundle_digest": bundle.data4_bundle_digest,
            "data5_bundle_digest": bundle.data5_bundle_digest,
            "policy": bundle.policy.to_dict(),
            "universal_structural_features": [
                _structural_manifest(temporary, catalog, index)
                for index, catalog in enumerate(bundle.universal_structural_features)
            ],
            "lta_selection_features": (
                None
                if bundle.lta_selection_features is None
                else _lta_manifest(temporary, bundle.lta_selection_features)
            ),
            "phase_geometry_profile_plan": (
                None
                if bundle.phase_geometry_profile_plan is None
                else bundle.phase_geometry_profile_plan.to_dict()
            ),
            "profile_selection_features": [
                item.to_dict() for item in bundle.profile_selection_features
            ],
            "checkpoint_identity": (
                None
                if bundle.checkpoint_identity is None
                else bundle.checkpoint_identity.to_dict()
            ),
            "mace_descriptor_manifest": (
                None
                if bundle.mace_descriptor_manifest is None
                else _manifest_records(
                    temporary, "mace-descriptors", bundle.mace_descriptor_manifest
                )
            ),
            "model_sweep_plan": (
                None
                if bundle.model_sweep_plan is None
                else bundle.model_sweep_plan.to_dict()
            ),
            "prediction_manifest": (
                None
                if bundle.prediction_manifest is None
                else _manifest_records(
                    temporary, "model-predictions", bundle.prediction_manifest
                )
            ),
            "model_sweep_checkpoint_digest": bundle.model_sweep_checkpoint_digest,
            "training_difficulty_catalogs": _difficulty_manifest(
                temporary, "difficulty", bundle.training_difficulty_catalogs
            ),
            "blinded_prediction_catalogs": _difficulty_manifest(
                temporary, "blinded", bundle.blinded_prediction_catalogs
            ),
            "notes": list(bundle.notes),
        }
        _write_json_atomic(temporary / "manifest.json", manifest)
        if destination.exists():
            shutil.rmtree(destination)
        os.replace(temporary, destination)
        manifest_path = destination / "manifest.json"
        return {
            "schema": DATA6_SHARDED_POINTER_SCHEMA,
            "relative_path": str(manifest_path.relative_to(root.parent)),
            "sha256": _sha256_file(manifest_path),
            "content_digest": content_digest,
            "record_key": record_key,
        }
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _restore_structural(
    root: Path,
    meta: Mapping[str, Any],
    *,
    progress_callback: Callable[[str], None] | None,
) -> UniversalStructuralFeatureCatalog:
    table_meta = meta["frame_table"]
    table = UniversalFrameDescriptorTable._from_authenticated_arrays(
        frame_uids=tuple(str(value) for value in table_meta["frame_uids"]),
        frame_record_digests=tuple(
            str(value) for value in table_meta["frame_record_digests"]
        ),
        provider_identity_digest=str(table_meta["provider_identity_digest"]),
        feature_names=tuple(str(value) for value in table_meta["feature_names"]),
        values=_read_npy(root, table_meta["values"], label="universal values"),
        missing_mask=_read_npy(
            root, table_meta["missing_mask"], label="universal missing mask"
        ),
        atom_counts=_read_npy(
            root, table_meta["atom_counts"], label="universal atom counts"
        ),
        warning_codes=tuple(
            tuple(str(code) for code in row) for row in table_meta["warning_codes"]
        ),
        content_digest=str(table_meta["content_digest"]),
    )
    catalog = UniversalStructuralFeatureCatalog(
        dataset_id=str(meta["dataset_id"]),
        frame_catalog_digest=str(meta["frame_catalog_digest"]),
        data4_bundle_digest=str(meta["data4_bundle_digest"]),
        material_profile_contracts_digest=(
            None
            if meta.get("material_profile_contracts_digest") is None
            else str(meta["material_profile_contracts_digest"])
        ),
        atom_group_catalog_digest=(
            None
            if meta.get("atom_group_catalog_digest") is None
            else str(meta["atom_group_catalog_digest"])
        ),
        provider_identity=StructuralFeatureProviderIdentity.from_dict(
            meta["provider_identity"]
        ),
        policy=UniversalStructuralSelectionPolicy.from_dict(meta["policy"]),
        frame_descriptors=table,
        atomic_environment_descriptors=_read_jsonl(
            root,
            meta["atomic_environments"],
            UniversalAtomicEnvironmentDescriptor.from_dict,
            label="universal atomic environment",
            progress_callback=progress_callback,
        ),
        events=_read_jsonl(
            root,
            meta["events"],
            GenericStructuralEventRecord.from_dict,
            label="universal structural event",
            progress_callback=progress_callback,
        ),
        parser_version=str(meta.get("parser_version", "0.20.49a0")),
    )
    object.__setattr__(catalog, "_content_digest_cache", str(meta["content_digest"]))
    return catalog


def _restore_manifest_records(
    root: Path,
    meta: Mapping[str, Any],
    *,
    manifest_kind: str,
    progress_callback: Callable[[str], None] | None,
) -> Any:
    if manifest_kind == "descriptor":
        records = _read_jsonl(
            root,
            meta["records"],
            MaceDescriptorFileRecord.from_dict,
            label="MACE descriptor manifest",
            progress_callback=progress_callback,
        )
        result = MaceDescriptorManifest(
            dataset_id=str(meta["dataset_id"]),
            frame_catalog_digest=str(meta["frame_catalog_digest"]),
            data5_bundle_digest=str(meta["data5_bundle_digest"]),
            checkpoint_identity=ModelCheckpointIdentity.from_dict(
                meta["checkpoint_identity"]
            ),
            policy=MaceDescriptorPolicy.from_dict(meta["policy"]),
            records=records,
            excluded_frame_uids=tuple(
                str(value) for value in meta.get("excluded_frame_uids", ())
            ),
        )
    else:
        records = _read_jsonl(
            root,
            meta["records"],
            AtomicModelPredictionFileRecord.from_dict,
            label="prediction manifest",
            progress_callback=progress_callback,
        )
        result = AtomicModelPredictionManifest(
            dataset_id=str(meta["dataset_id"]),
            frame_catalog_digest=str(meta["frame_catalog_digest"]),
            data5_bundle_digest=str(meta["data5_bundle_digest"]),
            checkpoint_identity=ModelCheckpointIdentity.from_dict(
                meta["checkpoint_identity"]
            ),
            records=records,
            excluded_frame_uids=tuple(
                str(value) for value in meta.get("excluded_frame_uids", ())
            ),
        )
    object.__setattr__(result, "_content_digest_cache", str(meta["content_digest"]))
    return result


def read_data6_sharded_record(
    pointer: Mapping[str, Any],
    state_root: str | Path,
    *,
    progress_callback: Callable[[str], None] | None = None,
) -> Data6FeatureBundle:
    """Restore a checksummed sharded DATA6 campaign record."""

    if pointer.get("schema") != DATA6_SHARDED_POINTER_SCHEMA:
        raise Data6ShardedStoreError("Unsupported DATA6 sharded pointer schema.")
    state_root_path = Path(state_root).resolve()
    relative = Path(str(pointer.get("relative_path", "")))
    if relative.is_absolute() or ".." in relative.parts:
        raise Data6ShardedStoreError("DATA6 pointer escapes the campaign workspace.")
    manifest_path = (state_root_path / relative).resolve()
    if state_root_path not in manifest_path.parents or not manifest_path.is_file():
        raise Data6ShardedStoreError(f"Missing DATA6 sharded manifest: {manifest_path}")
    expected_hash = str(pointer.get("sha256", ""))
    if not expected_hash or _sha256_file(manifest_path) != expected_hash:
        raise Data6ShardedStoreError("DATA6 sharded manifest checksum mismatch.")
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, Mapping) or manifest.get("schema") != DATA6_SHARDED_MANIFEST_SCHEMA:
        raise Data6ShardedStoreError("Invalid DATA6 sharded manifest.")
    root = manifest_path.parent

    lta_meta = manifest.get("lta_selection_features")
    lta = None
    if lta_meta is not None:
        lta = LtaSelectionFeatureCatalog(
            dataset_id=str(lta_meta["dataset_id"]),
            frame_catalog_digest=str(lta_meta["frame_catalog_digest"]),
            data4_bundle_digest=str(lta_meta["data4_bundle_digest"]),
            policy=LtaSelectionPolicy.from_dict(lta_meta["policy"]),
            frame_descriptors=_read_jsonl(
                root,
                lta_meta["frames"],
                LtaFrameSelectionDescriptor.from_dict,
                label="LTA selection frame",
                progress_callback=progress_callback,
            ),
            atomic_environment_descriptors=_read_jsonl(
                root,
                lta_meta["atomic_environments"],
                LtaAtomicEnvironmentDescriptor.from_dict,
                label="LTA selection atomic environment",
                progress_callback=progress_callback,
            ),
        )

    difficulty: list[TrainingDifficultyFeatureCatalog] = []
    for meta in manifest.get("training_difficulty_catalogs", ()):
        catalog = TrainingDifficultyFeatureCatalog(
            dataset_id=str(meta["dataset_id"]),
            frame_catalog_digest=str(meta["frame_catalog_digest"]),
            domain=TrainingDifficultyDomain.from_dict(meta["domain"]),
            checkpoint_identity=ModelCheckpointIdentity.from_dict(
                meta["checkpoint_identity"]
            ),
            records=_read_jsonl(
                root,
                meta["records"],
                DifficultyFrameRecord.from_dict,
                label="difficulty",
                progress_callback=progress_callback,
            ),
        )
        object.__setattr__(catalog, "_content_digest_cache", str(meta["content_digest"]))
        difficulty.append(catalog)

    blinded: list[BlindedEvaluationPredictionCatalog] = []
    for meta in manifest.get("blinded_prediction_catalogs", ()):
        catalog = BlindedEvaluationPredictionCatalog(
            dataset_id=str(meta["dataset_id"]),
            frame_catalog_digest=str(meta["frame_catalog_digest"]),
            domain=BlindedPredictionDomain.from_dict(meta["domain"]),
            checkpoint_identity=ModelCheckpointIdentity.from_dict(
                meta["checkpoint_identity"]
            ),
            records=_read_jsonl(
                root,
                meta["records"],
                ModelPredictionSummary.from_dict,
                label="blinded prediction",
                progress_callback=progress_callback,
            ),
        )
        object.__setattr__(catalog, "_content_digest_cache", str(meta["content_digest"]))
        blinded.append(catalog)

    result = Data6FeatureBundle(
        dataset_id=str(manifest["dataset_id"]),
        source_catalog_digest=str(manifest["source_catalog_digest"]),
        frame_catalog_digest=str(manifest["frame_catalog_digest"]),
        data4_bundle_digest=str(manifest["data4_bundle_digest"]),
        data5_bundle_digest=str(manifest["data5_bundle_digest"]),
        policy=Data6Policy.from_dict(manifest["policy"]),
        universal_structural_features=tuple(
            _restore_structural(root, meta, progress_callback=progress_callback)
            for meta in manifest.get("universal_structural_features", ())
        ),
        phase_geometry_profile_plan=(
            None
            if manifest.get("phase_geometry_profile_plan") is None
            else PhaseGeometrySelectionPlan.from_dict(
                manifest["phase_geometry_profile_plan"]
            )
        ),
        lta_selection_features=lta,
        profile_selection_features=tuple(
            ProfileFeatureCatalog.from_dict(item)
            for item in manifest.get("profile_selection_features", ())
        ),
        checkpoint_identity=(
            None
            if manifest.get("checkpoint_identity") is None
            else ModelCheckpointIdentity.from_dict(manifest["checkpoint_identity"])
        ),
        mace_descriptor_manifest=(
            None
            if manifest.get("mace_descriptor_manifest") is None
            else _restore_manifest_records(
                root,
                manifest["mace_descriptor_manifest"],
                manifest_kind="descriptor",
                progress_callback=progress_callback,
            )
        ),
        model_sweep_plan=(
            None
            if manifest.get("model_sweep_plan") is None
            else Data6ModelSweepPlan.from_dict(manifest["model_sweep_plan"])
        ),
        prediction_manifest=(
            None
            if manifest.get("prediction_manifest") is None
            else _restore_manifest_records(
                root,
                manifest["prediction_manifest"],
                manifest_kind="prediction",
                progress_callback=progress_callback,
            )
        ),
        model_sweep_checkpoint_digest=(
            None
            if manifest.get("model_sweep_checkpoint_digest") is None
            else str(manifest["model_sweep_checkpoint_digest"])
        ),
        training_difficulty_catalogs=tuple(difficulty),
        blinded_prediction_catalogs=tuple(blinded),
        notes=tuple(str(value) for value in manifest.get("notes", ())),
    )
    expected = str(pointer.get("content_digest", manifest.get("content_digest", "")))
    if not expected or expected != str(manifest.get("content_digest", "")):
        raise Data6ShardedStoreError("DATA6 bundle digest mismatch after restore.")
    actual = digest(result._digest_payload())
    if actual != expected:
        raise Data6ShardedStoreError(
            "DATA6 scientific content digest mismatch after shard restore."
        )
    object.__setattr__(result, "_content_digest_cache", actual)
    return result
