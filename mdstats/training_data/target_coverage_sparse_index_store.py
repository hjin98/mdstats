"""Authenticated native-array persistence for TARGET-DATA2C-MVIDX1."""

from __future__ import annotations

import hashlib
import json
import mmap
import os
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any, Callable, Mapping

import numpy as np

from ._common import (
    canonical_json,
    digest,
    read_validation_receipt,
    sha256_file_cached,
    write_validation_receipt,
)
from .resources import available_memory_bytes
from .target_coverage import (
    TARGET_COVERAGE_ARRAY_SCHEMA,
    _coverage_array_reference,
    _validate_array_reference,
)
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
_MVIDX_VALIDATION_RECEIPT_NAMESPACE = "target-data2c-mvidx1-native-v1"
_MVIDX_VALIDATION_CHUNK_EDGES = 8 * 1024 * 1024
_MVIDX_AUTO_DISCARD_AVAILABLE_FRACTION = 0.8


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


def _safe_path_stat(root: Path, descriptor: Mapping[str, Any], *, label: str) -> tuple[Path, os.stat_result]:
    relative = Path(str(descriptor.get("relative_path", "")))
    if relative.is_absolute() or ".." in relative.parts or relative in {Path(""), Path(".")}:
        raise TargetCoverageSparseIndexNativeStoreError(f"Invalid {label} array path.")
    path = (root / relative).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise TargetCoverageSparseIndexNativeStoreError(f"Missing {label} array: {path}")
    stat = path.stat()
    size = int(descriptor.get("size_bytes", -1))
    if size < 0 or stat.st_size != size:
        raise TargetCoverageSparseIndexNativeStoreError(f"Size mismatch for {label} array: {path}")
    return path, stat


def _safe_path(root: Path, descriptor: Mapping[str, Any], *, label: str) -> Path:
    path, _ = _safe_path_stat(root, descriptor, label=label)
    expected = str(descriptor.get("sha256", ""))
    if not expected or _sha256_file(path) != expected:
        raise TargetCoverageSparseIndexNativeStoreError(f"Checksum mismatch for {label} array: {path}")
    return path


def _madvise_array(array: np.ndarray, advice: int) -> bool:
    """Apply best-effort advice to a file mapping without changing correctness."""

    root = _root_memmap(array)
    mapping = None if root is None else getattr(root, "base", None)
    if mapping is None or not hasattr(mapping, "madvise"):
        return False
    try:
        mapping.madvise(advice)
        return True
    except (OSError, ValueError):
        return False


def _validate_reference_metadata(
    reference: Mapping[str, Any], array: np.ndarray, *, label: str
) -> str:
    payload = {
        "schema": TARGET_COVERAGE_ARRAY_SCHEMA,
        "dtype": array.dtype.str,
        "shape": [int(value) for value in array.shape],
        "byte_count": int(array.nbytes),
        "value_sha256": str(reference.get("value_sha256", "")),
    }
    if (
        reference.get("schema") != TARGET_COVERAGE_ARRAY_SCHEMA
        or reference.get("dtype") != payload["dtype"]
        or reference.get("shape") != payload["shape"]
        or int(reference.get("byte_count", -1)) != payload["byte_count"]
        or reference.get("content_digest") != digest(payload)
        or len(payload["value_sha256"]) != 64
    ):
        raise TargetCoverageSparseIndexNativeStoreError(f"TARGET-DATA2C-MVIDX1 {label} array reference mismatch.")
    return payload["value_sha256"]


def _validate_native_index_array(
    reference: Mapping[str, Any],
    array: np.ndarray,
    offsets: np.ndarray,
    *,
    upper_bound: int,
    label: str,
) -> None:
    """Authenticate bytes, range, and CSR row ordering in one bounded pass."""

    expected_sha = _validate_reference_metadata(reference, array, label=label)
    hasher = hashlib.sha256()
    edge_count = int(array.size)
    chunk_size = max(1, int(_MVIDX_VALIDATION_CHUNK_EDGES))
    for start in range(0, edge_count, chunk_size):
        stop = min(edge_count, start + chunk_size)
        values = array[start:stop]
        hasher.update(memoryview(values).cast("B"))
        if values.size and int(np.max(values)) >= int(upper_bound):
            raise TargetCoverageSparseIndexNativeStoreError(
                "TARGET-DATA2C-MVIDX1 sparse family index contains out-of-range edges."
            )
        pair_start = max(0, start - 1)
        if stop - pair_start < 2:
            continue
        bad = np.flatnonzero(array[pair_start + 1 : stop] <= array[pair_start : stop - 1])
        if bad.size == 0:
            continue
        positions = bad.astype(np.int64, copy=False) + pair_start + 1
        boundary_rows = np.searchsorted(offsets, positions, side="left")
        is_boundary = np.zeros(positions.size, dtype=np.bool_)
        valid = boundary_rows < len(offsets)
        if np.any(valid):
            is_boundary[valid] = offsets[boundary_rows[valid]] == positions[valid]
        if np.any(~is_boundary):
            raise TargetCoverageSparseIndexNativeStoreError(
                f"TARGET-DATA2C-MVIDX1 {label} rows must be strictly sorted and duplicate-free."
            )
    if hasher.hexdigest() != expected_sha:
        raise TargetCoverageSparseIndexNativeStoreError(
            f"TARGET-DATA2C-MVIDX1 {label} array reference mismatch."
        )


def _read_npy(
    root: Path,
    descriptor: Mapping[str, Any],
    *,
    label: str,
    mmap_threshold_bytes: int,
    validate_array_reference: bool = True,
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
    if validate_array_reference:
        try:
            _validate_array_reference(reference, array, name=label)
        except Exception as exc:
            raise TargetCoverageSparseIndexNativeStoreError(str(exc)) from exc
    else:
        _validate_reference_metadata(reference, array, label=label)
    array.setflags(write=False)
    return array


def _manifest_array_descriptors(manifest: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    result: list[tuple[str, Mapping[str, Any]]] = []
    for domain in manifest.get("domains", ()):
        domain_id = str(domain.get("label_domain_id", ""))
        for family in domain.get("families", ()):
            family_id = str(family.get("family_id", ""))
            arrays = family.get("arrays")
            if not isinstance(arrays, Mapping):
                raise TargetCoverageSparseIndexNativeStoreError("TARGET-DATA2C-MVIDX1 family array manifest is missing.")
            for name, descriptor in sorted(arrays.items()):
                if not isinstance(descriptor, Mapping):
                    raise TargetCoverageSparseIndexNativeStoreError("TARGET-DATA2C-MVIDX1 family array descriptor is invalid.")
                result.append((f"domain {domain_id} family {family_id} {name}", descriptor))
        arrays = domain.get("arrays")
        if not isinstance(arrays, Mapping):
            raise TargetCoverageSparseIndexNativeStoreError("TARGET-DATA2C-MVIDX1 domain array manifest is missing.")
        for name, descriptor in sorted(arrays.items()):
            if not isinstance(descriptor, Mapping):
                raise TargetCoverageSparseIndexNativeStoreError("TARGET-DATA2C-MVIDX1 domain array descriptor is invalid.")
            result.append((f"domain {domain_id} {name}", descriptor))
    return result


def _restore_identity(
    data_root: Path,
    manifest: Mapping[str, Any],
) -> tuple[str, int]:
    files: list[dict[str, Any]] = []
    logical_bytes = 0
    for label, descriptor in _manifest_array_descriptors(manifest):
        path, stat = _safe_path_stat(data_root, descriptor, label=label)
        reference = descriptor.get("array_reference")
        if not isinstance(reference, Mapping):
            raise TargetCoverageSparseIndexNativeStoreError(f"Missing {label} array identity.")
        logical_bytes += max(0, int(reference.get("byte_count", 0)))
        files.append(
            {
                "path": str(path),
                "device": int(stat.st_dev),
                "inode": int(stat.st_ino),
                "size": int(stat.st_size),
                "mtime_ns": int(stat.st_mtime_ns),
                "ctime_ns": int(stat.st_ctime_ns),
            }
        )
    return digest(
        {
            "schema": _MVIDX_VALIDATION_RECEIPT_NAMESPACE,
            "manifest_digest": manifest.get("manifest_digest"),
            "files": files,
        }
    ), logical_bytes


def _resolved_cache_policy(policy: str, logical_bytes: int) -> str:
    requested = str(policy).strip().lower()
    if requested not in {"auto", "retain", "discard"}:
        raise ValueError("mmap_cache_policy must be 'auto', 'retain', or 'discard'.")
    if requested != "auto":
        return requested
    available = available_memory_bytes()
    if available is None:
        return "retain"
    return "discard" if logical_bytes > int(_MVIDX_AUTO_DISCARD_AVAILABLE_FRACTION * available) else "retain"


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
    mmap_cache_policy: str = "auto",
    progress_callback: Callable[[str], None] | None = None,
    progress_interval_seconds: float = 10.0,
) -> TargetCoverageSparseIndex:
    started = time.monotonic()
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
    restore_identity, logical_bytes = _restore_identity(data_root, manifest)
    expected_index_digest = str(manifest.get("index_content_digest", ""))
    receipt_hit = (
        read_validation_receipt(_MVIDX_VALIDATION_RECEIPT_NAMESPACE, restore_identity)
        == expected_index_digest
    )
    validation_mode = "receipt-hit" if receipt_hit else "full"
    cache_policy = _resolved_cache_policy(mmap_cache_policy, logical_bytes)
    family_total = sum(len(domain.get("families", ())) for domain in manifest.get("domains", ()))
    family_completed = 0
    completed_bytes = 0
    last_progress = started
    if progress_callback is not None:
        progress_callback(
            f"restore; status=start; validation={validation_mode}; cache_policy={cache_policy}; "
            f"families=0/{family_total}; bytes=0/{logical_bytes}"
        )
    domains: list[TargetCoverageSparseDomainIndex] = []
    for domain_payload in manifest.get("domains", ()):
        family_indices: list[TargetCoverageSparseFamilyIndex] = []
        for family_payload in domain_payload.get("families", ()):
            arrays = family_payload.get("arrays")
            if not isinstance(arrays, Mapping):
                raise TargetCoverageSparseIndexNativeStoreError("TARGET-DATA2C-MVIDX1 family array manifest is missing.")
            witness_offsets = _read_npy(
                data_root,
                arrays["witness_offsets"],
                label="witness_offsets",
                mmap_threshold_bytes=mmap_threshold_bytes,
                validate_array_reference=not receipt_hit,
            )
            witness_candidates = _read_npy(
                data_root,
                arrays["witness_candidates"],
                label="witness_candidates",
                mmap_threshold_bytes=mmap_threshold_bytes,
                validate_array_reference=False,
            )
            candidate_offsets = _read_npy(
                data_root,
                arrays["candidate_offsets"],
                label="candidate_offsets",
                mmap_threshold_bytes=mmap_threshold_bytes,
                validate_array_reference=not receipt_hit,
            )
            candidate_witnesses = _read_npy(
                data_root,
                arrays["candidate_witnesses"],
                label="candidate_witnesses",
                mmap_threshold_bytes=mmap_threshold_bytes,
                validate_array_reference=False,
            )
            if not receipt_hit:
                if hasattr(mmap, "MADV_SEQUENTIAL"):
                    _madvise_array(witness_candidates, mmap.MADV_SEQUENTIAL)
                    _madvise_array(candidate_witnesses, mmap.MADV_SEQUENTIAL)
                _validate_native_index_array(
                    arrays["witness_candidates"]["array_reference"],
                    witness_candidates,
                    witness_offsets,
                    upper_bound=int(family_payload["candidate_count"]),
                    label="witness-to-candidate",
                )
                if cache_policy == "discard" and hasattr(mmap, "MADV_DONTNEED"):
                    _madvise_array(witness_candidates, mmap.MADV_DONTNEED)
                _validate_native_index_array(
                    arrays["candidate_witnesses"]["array_reference"],
                    candidate_witnesses,
                    candidate_offsets,
                    upper_bound=int(family_payload["witness_count"]),
                    label="candidate-to-witness",
                )
                if cache_policy == "discard" and hasattr(mmap, "MADV_DONTNEED"):
                    _madvise_array(candidate_witnesses, mmap.MADV_DONTNEED)
            family = TargetCoverageSparseFamilyIndex._from_validated_native(
                array_references={
                    name: descriptor["array_reference"]
                    for name, descriptor in arrays.items()
                },
                family_id=str(family_payload["family_id"]),
                family_digest=str(family_payload["family_digest"]),
                candidate_count=int(family_payload["candidate_count"]),
                witness_count=int(family_payload["witness_count"]),
                witness_offsets=witness_offsets,
                witness_candidates=witness_candidates,
                candidate_offsets=candidate_offsets,
                candidate_witnesses=candidate_witnesses,
            )
            if int(family_payload.get("edge_count", family.edge_count)) != family.edge_count or family_payload.get("content_digest") != family.content_digest:
                raise TargetCoverageSparseIndexNativeStoreError("TARGET-DATA2C-MVIDX1 family manifest identity mismatch.")
            family_indices.append(family)
            family_completed += 1
            completed_bytes += sum(
                int(descriptor["array_reference"].get("byte_count", 0))
                for descriptor in arrays.values()
            )
            now = time.monotonic()
            if progress_callback is not None and (
                family_completed == family_total
                or now - last_progress >= max(0.1, float(progress_interval_seconds))
            ):
                elapsed = max(0.0, now - started)
                eta = 0.0 if completed_bytes <= 0 else elapsed * max(0, logical_bytes - completed_bytes) / completed_bytes
                progress_callback(
                    f"restore; status=progress; validation={validation_mode}; cache_policy={cache_policy}; "
                    f"families={family_completed}/{family_total}; bytes={completed_bytes}/{logical_bytes}; "
                    f"elapsed_s={elapsed:.1f}; eta_s={eta:.1f}"
                )
                last_progress = now
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
    final_identity, _ = _restore_identity(data_root, manifest)
    if final_identity != restore_identity:
        raise TargetCoverageSparseIndexNativeStoreError("TARGET-DATA2C-MVIDX1 sidecar identity changed during restore.")
    if not receipt_hit:
        write_validation_receipt(
            _MVIDX_VALIDATION_RECEIPT_NAMESPACE,
            restore_identity,
            result.content_digest,
        )
    if progress_callback is not None:
        progress_callback(
            f"restore; status=complete; validation={validation_mode}; cache_policy={cache_policy}; "
            f"families={family_completed}/{family_total}; bytes={logical_bytes}/{logical_bytes}; "
            f"elapsed_s={time.monotonic() - started:.1f}"
        )
    return result
