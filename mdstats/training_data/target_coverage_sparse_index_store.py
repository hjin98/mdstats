"""Authenticated native-array persistence for TARGET-DATA2C-MVIDX1."""

from __future__ import annotations

import hashlib
import json
import mmap
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping

import numpy as np

from ._common import canonical_json, digest, sha256_file_cached
from .target_coverage import _coverage_array_reference, _validate_array_reference
from .target_coverage_sparse_index import (
    TARGET_COVERAGE_SPARSE_INDEX_PERSISTENCE_VERSION,
    TargetCoverageHardObligation,
    TargetCoverageSparseDomainIndex,
    TargetCoverageSparseFamilyIndex,
    TargetCoverageSparseIndex,
    TargetCoverageSparseIndexPolicy,
)

TARGET_COVERAGE_SPARSE_INDEX_NATIVE_MANIFEST_SCHEMA = "mdstats.target-coverage-sparse-index-native-manifest.v1"
TARGET_COVERAGE_SPARSE_INDEX_NATIVE_POINTER_SCHEMA = "mdstats.mlff-campaign-target-coverage-sparse-index-native-pointer.v1"


class TargetCoverageSparseIndexNativeStoreError(RuntimeError):
    """Raised when persisted MVIDX1 scientific arrays are missing or inconsistent."""


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


def _root_memmap(array: np.ndarray) -> np.memmap | None:
    current: Any = array
    visited: set[int] = set()
    while isinstance(current, np.ndarray) and id(current) not in visited:
        visited.add(id(current))
        if isinstance(current, np.memmap) and isinstance(current.base, mmap.mmap):
            return current
        current = getattr(current, "base", None)
    return None


def _whole_npy_memmap_source(array: np.ndarray) -> Path | None:
    """Return the backing NPY file when ``array`` covers one complete memmap."""

    root = _root_memmap(array)
    if root is None or not array.flags.c_contiguous:
        return None
    filename = getattr(root, "filename", None)
    if filename is None:
        return None
    source = Path(os.fspath(filename)).resolve()
    if source.suffix.lower() != ".npy" or not source.is_file():
        return None
    if (
        int(array.ctypes.data) != int(root.ctypes.data)
        or int(array.nbytes) != int(root.nbytes)
        or tuple(array.shape) != tuple(root.shape)
        or array.dtype != root.dtype
    ):
        return None
    try:
        probe = np.load(source, mmap_mode="r", allow_pickle=False)
    except (OSError, ValueError):
        return None
    try:
        if tuple(probe.shape) != tuple(array.shape) or probe.dtype != array.dtype:
            return None
    finally:
        del probe
    return source


def _write_npy(path: Path, array: np.ndarray) -> dict[str, Any]:
    contiguous = np.ascontiguousarray(array)
    source = _whole_npy_memmap_source(contiguous)
    if source is not None:
        try:
            os.link(source, path)
        except OSError:
            source = None
        else:
            return {
                "relative_path": path.name,
                "sha256": _sha256_file(source),
                "size_bytes": source.stat().st_size,
                "array_reference": _coverage_array_reference(contiguous),
            }
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
        raise TargetCoverageSparseIndexNativeStoreError(f"Invalid {label} array path.")
    path = (root / relative).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise TargetCoverageSparseIndexNativeStoreError(f"Missing {label} array: {path}")
    size = int(descriptor.get("size_bytes", -1))
    if size < 0 or path.stat().st_size != size:
        raise TargetCoverageSparseIndexNativeStoreError(f"Size mismatch for {label} array: {path}")
    expected = str(descriptor.get("sha256", ""))
    if not expected or _sha256_file(path) != expected:
        raise TargetCoverageSparseIndexNativeStoreError(f"Checksum mismatch for {label} array: {path}")
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
        raise TargetCoverageSparseIndexNativeStoreError(f"Missing {label} array identity.")
    byte_count = int(reference.get("byte_count", -1))
    mmap_mode = "r" if byte_count >= max(0, int(mmap_threshold_bytes)) else None
    try:
        array = np.load(path, mmap_mode=mmap_mode, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise TargetCoverageSparseIndexNativeStoreError(f"Cannot restore {label} array: {path}") from exc
    try:
        _validate_array_reference(reference, array, name=label)
    except Exception as exc:
        raise TargetCoverageSparseIndexNativeStoreError(str(exc)) from exc
    array.setflags(write=False)
    return array


def _family_metadata(family: TargetCoverageSparseFamilyIndex) -> dict[str, Any]:
    return {
        "family_id": family.family_id,
        "family_digest": family.family_digest,
        "candidate_count": family.candidate_count,
        "witness_count": family.witness_count,
        "edge_count": family.edge_count,
        "content_digest": family.content_digest,
    }


def _manifest_payload(index: TargetCoverageSparseIndex, record_key: str) -> dict[str, Any]:
    return {
        "schema": TARGET_COVERAGE_SPARSE_INDEX_NATIVE_MANIFEST_SCHEMA,
        "persistence_version": TARGET_COVERAGE_SPARSE_INDEX_PERSISTENCE_VERSION,
        "record_key": record_key,
        "index_content_digest": index.content_digest,
        "dataset_id": index.dataset_id,
        "target_coverage_reference_digest": index.target_coverage_reference_digest,
        "target_data_role_freeze_digest": index.target_data_role_freeze_digest,
        "target_coverage_feasibility_digest": index.target_coverage_feasibility_digest,
        "policy": index.policy.to_dict(),
        "authority_version": index.authority_version,
    }


def _validate_existing_manifest(root: Path, manifest: Mapping[str, Any]) -> None:
    for domain in manifest.get("domains", ()):
        for family in domain.get("families", ()):
            for name, descriptor in family.get("arrays", {}).items():
                _safe_path(root, descriptor, label=f"family {family.get('family_id')} {name}")
        for name, descriptor in domain.get("arrays", {}).items():
            _safe_path(root, descriptor, label=f"domain {domain.get('label_domain_id')} {name}")


def write_target_coverage_sparse_index_native_record(
    index: TargetCoverageSparseIndex,
    records_root: str | Path,
    *,
    record_key: str = "target_coverage_sparse_index",
) -> dict[str, Any]:
    root = Path(records_root)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"target-coverage-sparse-index-{index.content_digest}"
    manifest_path = destination / "manifest.json"
    if manifest_path.is_file():
        try:
            with manifest_path.open("r", encoding="utf-8") as handle:
                existing = json.load(handle)
            if (
                isinstance(existing, Mapping)
                and existing.get("schema") == TARGET_COVERAGE_SPARSE_INDEX_NATIVE_MANIFEST_SCHEMA
                and existing.get("index_content_digest") == index.content_digest
                and existing.get("record_key") == record_key
            ):
                supplied = existing.get("manifest_digest")
                expected = digest({key: value for key, value in existing.items() if key != "manifest_digest"})
                if supplied != expected:
                    raise TargetCoverageSparseIndexNativeStoreError("TARGET-DATA2C-MVIDX1 native manifest digest mismatch.")
                _validate_existing_manifest(destination, existing)
                pointer = {
                    "schema": TARGET_COVERAGE_SPARSE_INDEX_NATIVE_POINTER_SCHEMA,
                    "persistence_version": TARGET_COVERAGE_SPARSE_INDEX_PERSISTENCE_VERSION,
                    "relative_path": str(manifest_path.relative_to(root.parent)),
                    "sha256": _sha256_file(manifest_path),
                    "content_digest": index.content_digest,
                    "record_key": record_key,
                }
                return {**pointer, "pointer_digest": digest(pointer)}
        except (OSError, json.JSONDecodeError, KeyError, TargetCoverageSparseIndexNativeStoreError):
            pass
        shutil.rmtree(destination, ignore_errors=True)

    temporary = Path(tempfile.mkdtemp(prefix="target-coverage-sparse-index-write-", dir=root))
    try:
        domains: list[dict[str, Any]] = []
        for domain_position, domain in enumerate(index.domains):
            family_rows: list[dict[str, Any]] = []
            for family_position, family in enumerate(domain.families):
                prefix = f"domain-{domain_position:03d}-family-{family_position:04d}"
                family_rows.append({
                    **_family_metadata(family),
                    "arrays": {
                        "witness_offsets": _write_npy(temporary / f"{prefix}-witness-offsets.npy", family.witness_offsets),
                        "witness_candidates": _write_npy(temporary / f"{prefix}-witness-candidates.npy", family.witness_candidates),
                        "candidate_offsets": _write_npy(temporary / f"{prefix}-candidate-offsets.npy", family.candidate_offsets),
                        "candidate_witnesses": _write_npy(temporary / f"{prefix}-candidate-witnesses.npy", family.candidate_witnesses),
                    },
                })
            prefix = f"domain-{domain_position:03d}"
            domains.append({
                "label_domain_id": domain.label_domain_id,
                "frame_domain_digest": domain.frame_domain_digest,
                "candidate_count": domain.candidate_count,
                "families": family_rows,
                "obligations": [item.to_dict() for item in domain.obligations],
                "correlation_unit_ids": list(domain.correlation_unit_ids),
                "obligation_edge_count": domain.obligation_edge_count,
                "arrays": {
                    "obligation_offsets": _write_npy(temporary / f"{prefix}-obligation-offsets.npy", domain.obligation_offsets),
                    "obligation_candidates": _write_npy(temporary / f"{prefix}-obligation-candidates.npy", domain.obligation_candidates),
                    "candidate_obligation_offsets": _write_npy(temporary / f"{prefix}-candidate-obligation-offsets.npy", domain.candidate_obligation_offsets),
                    "candidate_obligations": _write_npy(temporary / f"{prefix}-candidate-obligations.npy", domain.candidate_obligations),
                    "candidate_correlation_unit_codes": _write_npy(temporary / f"{prefix}-candidate-correlation-unit-codes.npy", domain.candidate_correlation_unit_codes),
                },
                "content_digest": domain.content_digest,
            })
        manifest = {**_manifest_payload(index, record_key), "domains": domains}
        manifest = {**manifest, "manifest_digest": digest(manifest)}
        _write_json_atomic(temporary / "manifest.json", manifest)
        if destination.exists():
            shutil.rmtree(destination)
        os.replace(temporary, destination)
        manifest_path = destination / "manifest.json"
        pointer = {
            "schema": TARGET_COVERAGE_SPARSE_INDEX_NATIVE_POINTER_SCHEMA,
            "persistence_version": TARGET_COVERAGE_SPARSE_INDEX_PERSISTENCE_VERSION,
            "relative_path": str(manifest_path.relative_to(root.parent)),
            "sha256": _sha256_file(manifest_path),
            "content_digest": index.content_digest,
            "record_key": record_key,
        }
        return {**pointer, "pointer_digest": digest(pointer)}
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def read_target_coverage_sparse_index_native_record(
    pointer: Mapping[str, Any],
    state_root: str | Path,
    *,
    mmap_threshold_bytes: int = 8 * 1024 * 1024,
) -> TargetCoverageSparseIndex:
    if pointer.get("schema") != TARGET_COVERAGE_SPARSE_INDEX_NATIVE_POINTER_SCHEMA:
        raise TargetCoverageSparseIndexNativeStoreError("Unsupported TARGET-DATA2C-MVIDX1 native pointer schema.")
    if pointer.get("persistence_version") != TARGET_COVERAGE_SPARSE_INDEX_PERSISTENCE_VERSION:
        raise TargetCoverageSparseIndexNativeStoreError("Unsupported TARGET-DATA2C-MVIDX1 persistence version.")
    relative = Path(str(pointer.get("relative_path", "")))
    if relative.is_absolute() or ".." in relative.parts or relative in {Path(""), Path(".")}:
        raise TargetCoverageSparseIndexNativeStoreError("Invalid TARGET-DATA2C-MVIDX1 manifest path.")
    root = Path(state_root).resolve()
    manifest_path = (root / relative).resolve()
    if root not in manifest_path.parents or not manifest_path.is_file():
        raise TargetCoverageSparseIndexNativeStoreError("Missing TARGET-DATA2C-MVIDX1 native manifest.")
    expected_sha = str(pointer.get("sha256", ""))
    if not expected_sha or _sha256_file(manifest_path) != expected_sha:
        raise TargetCoverageSparseIndexNativeStoreError("TARGET-DATA2C-MVIDX1 manifest checksum mismatch.")
    supplied_pointer_digest = pointer.get("pointer_digest")
    pointer_payload = {key: value for key, value in pointer.items() if key != "pointer_digest"}
    if supplied_pointer_digest not in (None, digest(pointer_payload)):
        raise TargetCoverageSparseIndexNativeStoreError("TARGET-DATA2C-MVIDX1 pointer digest mismatch.")
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, Mapping) or manifest.get("schema") != TARGET_COVERAGE_SPARSE_INDEX_NATIVE_MANIFEST_SCHEMA:
        raise TargetCoverageSparseIndexNativeStoreError("Invalid TARGET-DATA2C-MVIDX1 native manifest.")
    if manifest.get("persistence_version") != TARGET_COVERAGE_SPARSE_INDEX_PERSISTENCE_VERSION:
        raise TargetCoverageSparseIndexNativeStoreError("Unsupported TARGET-DATA2C-MVIDX1 native manifest version.")
    supplied_manifest_digest = manifest.get("manifest_digest")
    expected_manifest_digest = digest({key: value for key, value in manifest.items() if key != "manifest_digest"})
    if supplied_manifest_digest != expected_manifest_digest:
        raise TargetCoverageSparseIndexNativeStoreError("TARGET-DATA2C-MVIDX1 native manifest digest mismatch.")
    if pointer.get("content_digest") != manifest.get("index_content_digest"):
        raise TargetCoverageSparseIndexNativeStoreError("TARGET-DATA2C-MVIDX1 pointer/manifest content digest mismatch.")
    data_root = manifest_path.parent
    domains: list[TargetCoverageSparseDomainIndex] = []
    for domain_payload in manifest.get("domains", ()):
        family_indices: list[TargetCoverageSparseFamilyIndex] = []
        for family_payload in domain_payload.get("families", ()):
            arrays = family_payload.get("arrays")
            if not isinstance(arrays, Mapping):
                raise TargetCoverageSparseIndexNativeStoreError("TARGET-DATA2C-MVIDX1 family array manifest is missing.")
            family = TargetCoverageSparseFamilyIndex(
                family_id=str(family_payload["family_id"]),
                family_digest=str(family_payload["family_digest"]),
                candidate_count=int(family_payload["candidate_count"]),
                witness_count=int(family_payload["witness_count"]),
                witness_offsets=_read_npy(data_root, arrays["witness_offsets"], label="witness_offsets", mmap_threshold_bytes=mmap_threshold_bytes),
                witness_candidates=_read_npy(data_root, arrays["witness_candidates"], label="witness_candidates", mmap_threshold_bytes=mmap_threshold_bytes),
                candidate_offsets=_read_npy(data_root, arrays["candidate_offsets"], label="candidate_offsets", mmap_threshold_bytes=mmap_threshold_bytes),
                candidate_witnesses=_read_npy(data_root, arrays["candidate_witnesses"], label="candidate_witnesses", mmap_threshold_bytes=mmap_threshold_bytes),
            )
            if int(family_payload.get("edge_count", family.edge_count)) != family.edge_count or family_payload.get("content_digest") != family.content_digest:
                raise TargetCoverageSparseIndexNativeStoreError("TARGET-DATA2C-MVIDX1 family manifest identity mismatch.")
            family_indices.append(family)
        arrays = domain_payload.get("arrays")
        if not isinstance(arrays, Mapping):
            raise TargetCoverageSparseIndexNativeStoreError("TARGET-DATA2C-MVIDX1 domain array manifest is missing.")
        domain = TargetCoverageSparseDomainIndex(
            label_domain_id=str(domain_payload["label_domain_id"]),
            frame_domain_digest=str(domain_payload["frame_domain_digest"]),
            candidate_count=int(domain_payload["candidate_count"]),
            families=tuple(family_indices),
            obligations=tuple(TargetCoverageHardObligation.from_dict(item) for item in domain_payload["obligations"]),
            obligation_offsets=_read_npy(data_root, arrays["obligation_offsets"], label="obligation_offsets", mmap_threshold_bytes=mmap_threshold_bytes),
            obligation_candidates=_read_npy(data_root, arrays["obligation_candidates"], label="obligation_candidates", mmap_threshold_bytes=mmap_threshold_bytes),
            candidate_obligation_offsets=_read_npy(data_root, arrays["candidate_obligation_offsets"], label="candidate_obligation_offsets", mmap_threshold_bytes=mmap_threshold_bytes),
            candidate_obligations=_read_npy(data_root, arrays["candidate_obligations"], label="candidate_obligations", mmap_threshold_bytes=mmap_threshold_bytes),
            correlation_unit_ids=tuple(str(item) for item in domain_payload["correlation_unit_ids"]),
            candidate_correlation_unit_codes=_read_npy(data_root, arrays["candidate_correlation_unit_codes"], label="candidate_correlation_unit_codes", mmap_threshold_bytes=mmap_threshold_bytes),
        )
        if int(domain_payload.get("obligation_edge_count", domain.obligation_edge_count)) != domain.obligation_edge_count or domain_payload.get("content_digest") != domain.content_digest:
            raise TargetCoverageSparseIndexNativeStoreError("TARGET-DATA2C-MVIDX1 domain manifest identity mismatch.")
        domains.append(domain)
    result = TargetCoverageSparseIndex(
        dataset_id=str(manifest["dataset_id"]),
        target_coverage_reference_digest=str(manifest["target_coverage_reference_digest"]),
        target_data_role_freeze_digest=str(manifest["target_data_role_freeze_digest"]),
        target_coverage_feasibility_digest=str(manifest["target_coverage_feasibility_digest"]),
        policy=TargetCoverageSparseIndexPolicy.from_dict(manifest["policy"]),
        domains=tuple(domains),
        authority_version=str(manifest["authority_version"]),
    )
    if result.content_digest != manifest.get("index_content_digest") or result.content_digest != pointer.get("content_digest"):
        raise TargetCoverageSparseIndexNativeStoreError("TARGET-DATA2C-MVIDX1 restored content digest mismatch.")
    return result
