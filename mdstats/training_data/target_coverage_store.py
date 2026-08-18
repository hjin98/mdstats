"""Authenticated native-array persistence for TARGET-DATA2B authority."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping

import numpy as np

from ._common import canonical_json, digest, sha256_file_cached
from .target_coverage import (
    TARGET_COVERAGE_PERSISTENCE_VERSION,
    TARGET_COVERAGE_REFERENCE_SCHEMA,
    TargetCoverageDomainReference,
    TargetCoverageExtentChannel,
    TargetCoverageFamilyReference,
    TargetCoveragePolicy,
    TargetCoverageReference,
    TargetCoverageStratumRequirement,
    _coverage_array_reference,
    _validate_array_reference,
)

TARGET_COVERAGE_NATIVE_MANIFEST_SCHEMA = "mdstats.target-coverage-native-manifest.v2"
TARGET_COVERAGE_NATIVE_POINTER_SCHEMA = "mdstats.mlff-campaign-target-coverage-native-pointer.v2"
TARGET_COVERAGE_NATIVE_WEIGHT_PROFILE_SCHEMA = "mdstats.target-coverage-native-weight-profile.v1"


class TargetCoverageNativeStoreError(RuntimeError):
    """Raised when native TARGET-DATA2B storage is missing or inconsistent."""


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


class _HashingBinaryWriter:
    def __init__(self, handle: Any) -> None:
        self.handle = handle
        self.hasher = hashlib.sha256()
        self.size = 0

    def write(self, value: bytes | bytearray | memoryview) -> int:
        view = memoryview(value)
        if not view.contiguous:
            view = memoryview(bytes(view))
        written = int(self.handle.write(view))
        if written:
            self.hasher.update(view[:written])
            self.size += written
        return written

    def flush(self) -> None:
        self.handle.flush()

    def fileno(self) -> int:
        return int(self.handle.fileno())

    def tell(self) -> int:
        return int(self.handle.tell())

    def seek(self, offset: int, whence: int = 0) -> int:
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
    return {
        "relative_path": path.name,
        "sha256": handle.hasher.hexdigest(),
        "size_bytes": handle.size,
        "array_reference": _coverage_array_reference(contiguous),
    }


def _safe_path(root: Path, descriptor: Mapping[str, Any], *, label: str) -> Path:
    relative = Path(str(descriptor.get("relative_path", "")))
    if relative.is_absolute() or ".." in relative.parts or relative in {Path(""), Path(".")}:
        raise TargetCoverageNativeStoreError(f"Invalid {label} array path.")
    path = (root / relative).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise TargetCoverageNativeStoreError(f"Missing {label} array: {path}")
    size = int(descriptor.get("size_bytes", -1))
    if size < 0 or path.stat().st_size != size:
        raise TargetCoverageNativeStoreError(f"Size mismatch for {label} array: {path}")
    expected = str(descriptor.get("sha256", ""))
    if not expected or _sha256_file(path) != expected:
        raise TargetCoverageNativeStoreError(f"Checksum mismatch for {label} array: {path}")
    return path


def _read_npy(
    root: Path,
    descriptor: Mapping[str, Any],
    *,
    label: str,
    mmap_threshold_bytes: int,
) -> np.ndarray:
    path = _safe_path(root, descriptor, label=label)
    reference = descriptor.get("array_reference")
    if not isinstance(reference, Mapping):
        raise TargetCoverageNativeStoreError(f"Missing {label} array identity.")
    byte_count = int(reference.get("byte_count", -1))
    mmap_mode = "r" if byte_count >= max(0, int(mmap_threshold_bytes)) else None
    try:
        array = np.load(path, mmap_mode=mmap_mode, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise TargetCoverageNativeStoreError(f"Cannot restore {label} array: {path}") from exc
    try:
        _validate_array_reference(reference, array, name=label)
    except Exception as exc:
        raise TargetCoverageNativeStoreError(str(exc)) from exc
    array.setflags(write=False)
    return array


def _weight_profile_identity(
    domain_id: str,
    frame_indices: np.ndarray,
    weights: np.ndarray,
) -> str:
    return digest(
        {
            "schema": TARGET_COVERAGE_NATIVE_WEIGHT_PROFILE_SCHEMA,
            "label_domain_id": domain_id,
            "frame_indices": _coverage_array_reference(frame_indices),
            "weights": _coverage_array_reference(weights),
        }
    )


def _family_metadata(family: TargetCoverageFamilyReference) -> dict[str, Any]:
    return {
        "family_id": family.family_id,
        "family_kind": family.family_kind,
        "semantic_family": family.semantic_family,
        "required": family.required,
        "metric": family.metric,
        "fidelity_diagnostic": family.fidelity_diagnostic,
        "feature_names": list(family.feature_names),
        "extent_channels": [item.to_dict() for item in family.extent_channels],
        "source_evidence_digest": family.source_evidence_digest,
        "notes": list(family.notes),
        "content_digest": family.content_digest,
    }


def _manifest_payload(reference: TargetCoverageReference, record_key: str) -> dict[str, Any]:
    return {
        "schema": TARGET_COVERAGE_NATIVE_MANIFEST_SCHEMA,
        "persistence_version": TARGET_COVERAGE_PERSISTENCE_VERSION,
        "record_key": record_key,
        "reference_schema": TARGET_COVERAGE_REFERENCE_SCHEMA,
        "reference_content_digest": reference.content_digest,
        "dataset_id": reference.dataset_id,
        "source_catalog_digest": reference.source_catalog_digest,
        "frame_catalog_digest": reference.frame_catalog_digest,
        "data4_bundle_digest": reference.data4_bundle_digest,
        "data5_bundle_digest": reference.data5_bundle_digest,
        "data6_bundle_digest": reference.data6_bundle_digest,
        "target_data_role_freeze_digest": reference.target_data_role_freeze_digest,
        "foundation_target_audit_digest": reference.foundation_target_audit_digest,
        "policy": reference.policy.to_dict(),
    }


def _validate_existing_manifest(root: Path, manifest: Mapping[str, Any]) -> None:
    for profile in manifest.get("weight_profiles", ()):
        for name in ("frame_indices", "weights"):
            _safe_path(root, profile[name], label=f"weight-profile {name}")
    for domain in manifest.get("domains", ()):
        for family in domain.get("families", ()):
            for name in ("values", "scales", "local_radii"):
                _safe_path(root, family["arrays"][name], label=f"family {name}")


def write_target_coverage_native_record(
    reference: TargetCoverageReference,
    records_root: str | Path,
    *,
    record_key: str = "target_coverage_reference",
) -> dict[str, Any]:
    """Persist TARGET-DATA2B arrays without constructing nested numeric JSON."""

    root = Path(records_root)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"target-coverage-{reference.content_digest}"
    manifest_path = destination / "manifest.json"
    if manifest_path.is_file():
        try:
            with manifest_path.open("r", encoding="utf-8") as handle:
                existing = json.load(handle)
            if (
                isinstance(existing, Mapping)
                and existing.get("schema") == TARGET_COVERAGE_NATIVE_MANIFEST_SCHEMA
                and existing.get("reference_content_digest") == reference.content_digest
                and existing.get("record_key") == record_key
            ):
                supplied = existing.get("manifest_digest")
                expected = digest({key: value for key, value in existing.items() if key != "manifest_digest"})
                if supplied != expected:
                    raise TargetCoverageNativeStoreError("TARGET-DATA2B native manifest digest mismatch.")
                _validate_existing_manifest(destination, existing)
                pointer_payload = {
                    "schema": TARGET_COVERAGE_NATIVE_POINTER_SCHEMA,
                    "persistence_version": TARGET_COVERAGE_PERSISTENCE_VERSION,
                    "relative_path": str(manifest_path.relative_to(root.parent)),
                    "sha256": _sha256_file(manifest_path),
                    "content_digest": reference.content_digest,
                    "record_key": record_key,
                }
                return {**pointer_payload, "pointer_digest": digest(pointer_payload)}
        except (OSError, json.JSONDecodeError, KeyError, TargetCoverageNativeStoreError):
            pass
        shutil.rmtree(destination, ignore_errors=True)

    temporary = Path(tempfile.mkdtemp(prefix="target-coverage-write-", dir=root))
    try:
        weight_profiles: dict[str, dict[str, Any]] = {}
        domains: list[dict[str, Any]] = []
        for domain_index, domain in enumerate(reference.domains):
            family_rows: list[dict[str, Any]] = []
            for family_index, family in enumerate(domain.families):
                profile_id = _weight_profile_identity(
                    domain.label_domain_id, family.frame_indices, family.weights
                )
                if profile_id not in weight_profiles:
                    prefix = f"weight-{len(weight_profiles):04d}"
                    weight_profiles[profile_id] = {
                        "schema": TARGET_COVERAGE_NATIVE_WEIGHT_PROFILE_SCHEMA,
                        "weight_profile_id": profile_id,
                        "label_domain_id": domain.label_domain_id,
                        "frame_indices": _write_npy(
                            temporary / f"{prefix}-frame-indices.npy", family.frame_indices
                        ),
                        "weights": _write_npy(
                            temporary / f"{prefix}-weights.npy", family.weights
                        ),
                    }
                prefix = f"domain-{domain_index:03d}-family-{family_index:04d}"
                family_rows.append(
                    {
                        **_family_metadata(family),
                        "weight_profile_id": profile_id,
                        "arrays": {
                            "values": _write_npy(
                                temporary / f"{prefix}-values.npy", family.values
                            ),
                            "scales": _write_npy(
                                temporary / f"{prefix}-scales.npy", family.scales
                            ),
                            "local_radii": _write_npy(
                                temporary / f"{prefix}-local-radii.npy", family.local_radii
                            ),
                        },
                    }
                )
            domains.append(
                {
                    "label_domain_id": domain.label_domain_id,
                    "frame_uids": list(domain.frame_uids),
                    "frame_domain_digest": domain.frame_domain_digest,
                    "strata": [item.to_dict() for item in domain.strata],
                    "families": family_rows,
                    "content_digest": domain.content_digest,
                }
            )
        manifest = {
            **_manifest_payload(reference, record_key),
            "weight_profiles": [weight_profiles[key] for key in sorted(weight_profiles)],
            "domains": domains,
        }
        manifest = {**manifest, "manifest_digest": digest(manifest)}
        _write_json_atomic(temporary / "manifest.json", manifest)
        if destination.exists():
            shutil.rmtree(destination)
        os.replace(temporary, destination)
        manifest_path = destination / "manifest.json"
        pointer_payload = {
            "schema": TARGET_COVERAGE_NATIVE_POINTER_SCHEMA,
            "persistence_version": TARGET_COVERAGE_PERSISTENCE_VERSION,
            "relative_path": str(manifest_path.relative_to(root.parent)),
            "sha256": _sha256_file(manifest_path),
            "content_digest": reference.content_digest,
            "record_key": record_key,
        }
        return {**pointer_payload, "pointer_digest": digest(pointer_payload)}
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def read_target_coverage_native_record(
    pointer: Mapping[str, Any],
    state_root: str | Path,
    *,
    mmap_threshold_bytes: int = 8 * 1024 * 1024,
) -> TargetCoverageReference:
    """Restore and authenticate a native TARGET-DATA2B authority."""

    if pointer.get("schema") != TARGET_COVERAGE_NATIVE_POINTER_SCHEMA:
        raise TargetCoverageNativeStoreError("Unsupported TARGET-DATA2B native pointer schema.")
    pointer_payload = {key: value for key, value in pointer.items() if key != "pointer_digest"}
    if pointer.get("pointer_digest") not in (None, digest(pointer_payload)):
        raise TargetCoverageNativeStoreError("TARGET-DATA2B native pointer digest mismatch.")
    if pointer.get("persistence_version") != TARGET_COVERAGE_PERSISTENCE_VERSION:
        raise TargetCoverageNativeStoreError("Unsupported TARGET-DATA2B native persistence version.")
    state_root_path = Path(state_root).resolve()
    relative = Path(str(pointer.get("relative_path", "")))
    if relative.is_absolute() or ".." in relative.parts:
        raise TargetCoverageNativeStoreError("TARGET-DATA2B pointer escapes the campaign workspace.")
    manifest_path = (state_root_path / relative).resolve()
    if state_root_path not in manifest_path.parents or not manifest_path.is_file():
        raise TargetCoverageNativeStoreError(f"Missing TARGET-DATA2B native manifest: {manifest_path}")
    if _sha256_file(manifest_path) != str(pointer.get("sha256", "")):
        raise TargetCoverageNativeStoreError("TARGET-DATA2B native manifest checksum mismatch.")
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, Mapping) or manifest.get("schema") != TARGET_COVERAGE_NATIVE_MANIFEST_SCHEMA:
        raise TargetCoverageNativeStoreError("Invalid TARGET-DATA2B native manifest.")
    expected_manifest_digest = digest(
        {key: value for key, value in manifest.items() if key != "manifest_digest"}
    )
    if manifest.get("manifest_digest") != expected_manifest_digest:
        raise TargetCoverageNativeStoreError("TARGET-DATA2B native manifest digest mismatch.")
    if manifest.get("persistence_version") != TARGET_COVERAGE_PERSISTENCE_VERSION:
        raise TargetCoverageNativeStoreError("Unsupported TARGET-DATA2B native manifest version.")
    root = manifest_path.parent

    profiles: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for profile in manifest.get("weight_profiles", ()):
        profile_id = str(profile["weight_profile_id"])
        frame_indices = _read_npy(
            root,
            profile["frame_indices"],
            label=f"weight-profile {profile_id} frame_indices",
            mmap_threshold_bytes=mmap_threshold_bytes,
        )
        weights = _read_npy(
            root,
            profile["weights"],
            label=f"weight-profile {profile_id} weights",
            mmap_threshold_bytes=mmap_threshold_bytes,
        )
        expected_profile_id = _weight_profile_identity(
            str(profile["label_domain_id"]), frame_indices, weights
        )
        if expected_profile_id != profile_id or profile_id in profiles:
            raise TargetCoverageNativeStoreError("TARGET-DATA2B native weight-profile identity mismatch.")
        profiles[profile_id] = (frame_indices, weights)

    domains: list[TargetCoverageDomainReference] = []
    for domain_meta in manifest.get("domains", ()):
        families: list[TargetCoverageFamilyReference] = []
        for family_meta in domain_meta.get("families", ()):
            profile_id = str(family_meta["weight_profile_id"])
            try:
                frame_indices, weights = profiles[profile_id]
            except KeyError as exc:
                raise TargetCoverageNativeStoreError("TARGET-DATA2B family references an unknown weight profile.") from exc
            arrays = family_meta["arrays"]
            family = TargetCoverageFamilyReference(
                family_id=str(family_meta["family_id"]),
                family_kind=str(family_meta["family_kind"]),
                semantic_family=str(family_meta["semantic_family"]),
                required=bool(family_meta["required"]),
                metric=str(family_meta["metric"]),
                fidelity_diagnostic=(
                    None
                    if family_meta.get("fidelity_diagnostic") is None
                    else str(family_meta["fidelity_diagnostic"])
                ),
                feature_names=tuple(str(value) for value in family_meta["feature_names"]),
                frame_indices=frame_indices,
                values=_read_npy(
                    root,
                    arrays["values"],
                    label=f"family {family_meta['family_id']} values",
                    mmap_threshold_bytes=mmap_threshold_bytes,
                ),
                weights=weights,
                scales=_read_npy(
                    root,
                    arrays["scales"],
                    label=f"family {family_meta['family_id']} scales",
                    mmap_threshold_bytes=mmap_threshold_bytes,
                ),
                local_radii=_read_npy(
                    root,
                    arrays["local_radii"],
                    label=f"family {family_meta['family_id']} local_radii",
                    mmap_threshold_bytes=mmap_threshold_bytes,
                ),
                extent_channels=tuple(
                    TargetCoverageExtentChannel.from_dict(item)
                    for item in family_meta.get("extent_channels", ())
                ),
                source_evidence_digest=str(family_meta["source_evidence_digest"]),
                notes=tuple(str(value) for value in family_meta.get("notes", ())),
            )
            if family.content_digest != str(family_meta["content_digest"]):
                raise TargetCoverageNativeStoreError("TARGET-DATA2B native family digest mismatch.")
            families.append(family)
        domain = TargetCoverageDomainReference(
            label_domain_id=str(domain_meta["label_domain_id"]),
            frame_uids=tuple(str(value) for value in domain_meta["frame_uids"]),
            families=tuple(families),
            strata=tuple(
                TargetCoverageStratumRequirement.from_dict(item)
                for item in domain_meta.get("strata", ())
            ),
            frame_domain_digest=str(domain_meta["frame_domain_digest"]),
        )
        if domain.content_digest != str(domain_meta["content_digest"]):
            raise TargetCoverageNativeStoreError("TARGET-DATA2B native domain digest mismatch.")
        domains.append(domain)

    reference = TargetCoverageReference(
        dataset_id=str(manifest["dataset_id"]),
        source_catalog_digest=str(manifest["source_catalog_digest"]),
        frame_catalog_digest=str(manifest["frame_catalog_digest"]),
        data4_bundle_digest=str(manifest["data4_bundle_digest"]),
        data5_bundle_digest=str(manifest["data5_bundle_digest"]),
        data6_bundle_digest=str(manifest["data6_bundle_digest"]),
        target_data_role_freeze_digest=str(manifest["target_data_role_freeze_digest"]),
        foundation_target_audit_digest=str(manifest["foundation_target_audit_digest"]),
        policy=TargetCoveragePolicy.from_dict(manifest["policy"]),
        domains=tuple(domains),
    )
    expected_digest = str(manifest["reference_content_digest"])
    if reference.content_digest != expected_digest or str(pointer.get("content_digest")) != expected_digest:
        raise TargetCoverageNativeStoreError("TARGET-DATA2B native reference digest mismatch.")
    return reference
