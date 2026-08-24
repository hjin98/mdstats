"""Authenticated native-array persistence for the NEIGHBOR1 forward-CSR cache."""

from __future__ import annotations

import hashlib
import json
import mmap
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np

from ._common import canonical_json, digest, sha256_file_cached
from .target_coverage import _coverage_array_reference, _validate_array_reference
from .target_coverage_exact_neighborhood import (
    TARGET_COVERAGE_EXACT_NEIGHBORHOOD_PERSISTENCE_VERSION,
    TargetCoverageExactNeighborhoodDomain,
    TargetCoverageExactNeighborhoodFamily,
    TargetCoverageExactNeighborhoodStore,
)

TARGET_COVERAGE_EXACT_NEIGHBORHOOD_LEGACY_NATIVE_MANIFEST_SCHEMA = (
    "mdstats.target-coverage-exact-neighborhood-native-manifest.v1"
)
TARGET_COVERAGE_EXACT_NEIGHBORHOOD_NATIVE_MANIFEST_SCHEMA = (
    "mdstats.target-coverage-exact-neighborhood-native-manifest.v2"
)
TARGET_COVERAGE_EXACT_NEIGHBORHOOD_NATIVE_POINTER_SCHEMA = (
    "mdstats.mlff-campaign-target-coverage-exact-neighborhood-native-pointer.v1"
)


class TargetCoverageExactNeighborhoodNativeStoreError(RuntimeError):
    """Persisted NEIGHBOR1 cache arrays are missing, stale, or inconsistent."""


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


def _family_sequence(store: TargetCoverageExactNeighborhoodStore) -> tuple[TargetCoverageExactNeighborhoodFamily, ...]:
    return tuple(family for domain in store.domains for family in domain.families)


def _shared_packed_root(
    families: Sequence[TargetCoverageExactNeighborhoodFamily],
    attribute: str,
) -> np.memmap | None:
    root: np.memmap | None = None
    cursor = 0
    for family in families:
        array = np.asarray(getattr(family, attribute))
        candidate = _root_memmap(array)
        if candidate is None or candidate.ndim != 1 or not array.flags.c_contiguous:
            return None
        if root is None:
            root = candidate
        elif candidate is not root:
            return None
        byte_offset = int(array.ctypes.data) - int(candidate.ctypes.data)
        if byte_offset != cursor * array.dtype.itemsize:
            return None
        cursor += int(array.size)
    if root is None or cursor != int(root.size):
        return None
    return root


def _packed_slice_descriptor(array: np.ndarray, start: int, stop: int) -> dict[str, Any]:
    return {
        "start": int(start),
        "stop": int(stop),
        "array_reference": _coverage_array_reference(array),
    }


def _write_packed_family_array(
    path: Path,
    families: Sequence[TargetCoverageExactNeighborhoodFamily],
    *,
    attribute: str,
    dtype: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    target_dtype = np.dtype(dtype).newbyteorder("<")
    root = _shared_packed_root(families, attribute)
    slices: list[dict[str, Any]] = []
    cursor = 0
    for family in families:
        array = np.asarray(getattr(family, attribute))
        stop = cursor + int(array.size)
        slices.append(_packed_slice_descriptor(array, cursor, stop))
        cursor = stop

    if root is not None and root.dtype == target_dtype:
        descriptor = _write_npy(path, root)
        return descriptor, slices

    packed = np.lib.format.open_memmap(
        path, mode="w+", dtype=target_dtype, shape=(cursor,)
    )
    try:
        cursor = 0
        for family in families:
            array = np.asarray(getattr(family, attribute), dtype=target_dtype)
            stop = cursor + int(array.size)
            packed[cursor:stop] = array
            cursor = stop
        packed.flush()
        descriptor = {
            "relative_path": path.name,
            "sha256": _sha256_file(path),
            "size_bytes": path.stat().st_size,
            "array_reference": _coverage_array_reference(packed),
        }
        return descriptor, slices
    finally:
        mapping = getattr(packed, "_mmap", None)
        if mapping is not None and not mapping.closed:
            mapping.close()


def _read_packed_npy(
    root: Path,
    descriptor: Mapping[str, Any],
    *,
    label: str,
) -> np.memmap:
    path = _safe_path(root, descriptor, label=label)
    reference = descriptor.get("array_reference")
    if not isinstance(reference, Mapping):
        raise TargetCoverageExactNeighborhoodNativeStoreError(
            f"Missing {label} packed-array identity."
        )
    try:
        array = np.load(path, mmap_mode="r", allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise TargetCoverageExactNeighborhoodNativeStoreError(
            f"Cannot restore {label} packed array: {path}"
        ) from exc
    try:
        _validate_array_reference(reference, array, name=label)
    except Exception as exc:
        mapping = getattr(array, "_mmap", None)
        if mapping is not None and not mapping.closed:
            mapping.close()
        raise TargetCoverageExactNeighborhoodNativeStoreError(str(exc)) from exc
    array.setflags(write=False)
    return array


def _packed_slice(
    packed: np.ndarray,
    descriptor: Mapping[str, Any],
    *,
    label: str,
) -> np.ndarray:
    start = int(descriptor.get("start", -1))
    stop = int(descriptor.get("stop", -1))
    if start < 0 or stop < start or stop > int(packed.size):
        raise TargetCoverageExactNeighborhoodNativeStoreError(
            f"Invalid {label} packed-array slice."
        )
    array = packed[start:stop]
    reference = descriptor.get("array_reference")
    if not isinstance(reference, Mapping):
        raise TargetCoverageExactNeighborhoodNativeStoreError(
            f"Missing {label} packed-slice identity."
        )
    try:
        _validate_array_reference(reference, array, name=label)
    except Exception as exc:
        raise TargetCoverageExactNeighborhoodNativeStoreError(str(exc)) from exc
    array.setflags(write=False)
    return array


def _safe_path(root: Path, descriptor: Mapping[str, Any], *, label: str) -> Path:
    relative = Path(str(descriptor.get("relative_path", "")))
    if relative.is_absolute() or ".." in relative.parts or relative in {Path(""), Path(".")}:
        raise TargetCoverageExactNeighborhoodNativeStoreError(f"Invalid {label} array path.")
    path = (root / relative).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise TargetCoverageExactNeighborhoodNativeStoreError(f"Missing {label} array: {path}")
    size = int(descriptor.get("size_bytes", -1))
    if size < 0 or path.stat().st_size != size:
        raise TargetCoverageExactNeighborhoodNativeStoreError(f"Size mismatch for {label} array: {path}")
    expected = str(descriptor.get("sha256", ""))
    if not expected or _sha256_file(path) != expected:
        raise TargetCoverageExactNeighborhoodNativeStoreError(f"Checksum mismatch for {label} array: {path}")
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
        raise TargetCoverageExactNeighborhoodNativeStoreError(f"Missing {label} array identity.")
    byte_count = int(reference.get("byte_count", -1))
    mmap_mode = "r" if byte_count >= max(0, int(mmap_threshold_bytes)) else None
    try:
        array = np.load(path, mmap_mode=mmap_mode, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise TargetCoverageExactNeighborhoodNativeStoreError(f"Cannot restore {label} array: {path}") from exc
    try:
        _validate_array_reference(reference, array, name=label)
    except Exception as exc:
        raise TargetCoverageExactNeighborhoodNativeStoreError(str(exc)) from exc
    array.setflags(write=False)
    return array


def _manifest_payload(store: TargetCoverageExactNeighborhoodStore, record_key: str) -> dict[str, Any]:
    return {
        "schema": TARGET_COVERAGE_EXACT_NEIGHBORHOOD_NATIVE_MANIFEST_SCHEMA,
        "persistence_version": TARGET_COVERAGE_EXACT_NEIGHBORHOOD_PERSISTENCE_VERSION,
        "record_key": record_key,
        "content_digest": store.content_digest,
        "dataset_id": store.dataset_id,
        "target_coverage_reference_digest": store.target_coverage_reference_digest,
        "authority_version": store.authority_version,
    }


def _validate_existing_manifest(root: Path, manifest: Mapping[str, Any]) -> None:
    packed = manifest.get("packed_arrays")
    if isinstance(packed, Mapping):
        for name, descriptor in packed.items():
            if not isinstance(descriptor, Mapping):
                raise TargetCoverageExactNeighborhoodNativeStoreError(
                    f"Invalid packed NEIGHBOR1 descriptor for {name}."
                )
            _safe_path(root, descriptor, label=f"packed {name}")
        return
    for domain in manifest.get("domains", ()):
        for family in domain.get("families", ()):
            for name, descriptor in family.get("arrays", {}).items():
                _safe_path(root, descriptor, label=f"family {family.get('family_id')} {name}")


def write_target_coverage_exact_neighborhood_native_record(
    store: TargetCoverageExactNeighborhoodStore,
    records_root: str | Path,
    *,
    record_key: str = "target_coverage_exact_neighborhoods",
) -> dict[str, Any]:
    root = Path(records_root)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"target-coverage-exact-neighborhood-{store.content_digest}"
    manifest_path = destination / "manifest.json"
    if manifest_path.is_file():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (
                isinstance(existing, Mapping)
                and existing.get("schema") == TARGET_COVERAGE_EXACT_NEIGHBORHOOD_NATIVE_MANIFEST_SCHEMA
                and existing.get("content_digest") == store.content_digest
                and existing.get("record_key") == record_key
                and existing.get("persistence_version") == TARGET_COVERAGE_EXACT_NEIGHBORHOOD_PERSISTENCE_VERSION
                and isinstance(existing.get("packed_arrays"), Mapping)
            ):
                supplied = existing.get("manifest_digest")
                expected = digest({key: value for key, value in existing.items() if key != "manifest_digest"})
                if supplied != expected:
                    raise TargetCoverageExactNeighborhoodNativeStoreError("NEIGHBOR1 native manifest digest mismatch.")
                _validate_existing_manifest(destination, existing)
                pointer = {
                    "schema": TARGET_COVERAGE_EXACT_NEIGHBORHOOD_NATIVE_POINTER_SCHEMA,
                    "persistence_version": TARGET_COVERAGE_EXACT_NEIGHBORHOOD_PERSISTENCE_VERSION,
                    "relative_path": str(manifest_path.relative_to(root.parent)),
                    "sha256": _sha256_file(manifest_path),
                    "content_digest": store.content_digest,
                    "record_key": record_key,
                }
                return {**pointer, "pointer_digest": digest(pointer)}
        except (OSError, json.JSONDecodeError, TargetCoverageExactNeighborhoodNativeStoreError):
            pass
        shutil.rmtree(destination, ignore_errors=True)

    temporary = Path(tempfile.mkdtemp(prefix="target-coverage-exact-neighborhood-write-", dir=root))
    try:
        all_families = _family_sequence(store)
        packed_offsets, offset_slices = _write_packed_family_array(
            temporary / "packed-witness-offsets.npy",
            all_families,
            attribute="witness_offsets",
            dtype="<u8",
        )
        packed_candidates, candidate_slices = _write_packed_family_array(
            temporary / "packed-witness-candidates.npy",
            all_families,
            attribute="witness_candidates",
            dtype="<u4",
        )
        domains: list[dict[str, Any]] = []
        family_index = 0
        for domain in store.domains:
            families: list[dict[str, Any]] = []
            for family in domain.families:
                families.append(
                    {
                        "label_domain_id": family.label_domain_id,
                        "frame_domain_digest": family.frame_domain_digest,
                        "family_id": family.family_id,
                        "family_digest": family.family_digest,
                        "candidate_count": family.candidate_count,
                        "witness_count": family.witness_count,
                        "edge_count": family.edge_count,
                        "metric_tolerance": family.metric_tolerance,
                        "distance_semantics": family.distance_semantics,
                        "authority_version": family.authority_version,
                        "identity_digest": family.identity_digest,
                        "content_digest": family.content_digest,
                        "array_slices": {
                            "witness_offsets": offset_slices[family_index],
                            "witness_candidates": candidate_slices[family_index],
                        },
                    }
                )
                family_index += 1
            domains.append(
                {
                    "label_domain_id": domain.label_domain_id,
                    "frame_domain_digest": domain.frame_domain_digest,
                    "candidate_count": domain.candidate_count,
                    "authority_version": domain.authority_version,
                    "families": families,
                    "content_digest": domain.content_digest,
                }
            )
        manifest = {
            **_manifest_payload(store, record_key),
            "packed_arrays": {
                "witness_offsets": packed_offsets,
                "witness_candidates": packed_candidates,
            },
            "domains": domains,
        }
        manifest = {**manifest, "manifest_digest": digest(manifest)}
        _write_json_atomic(temporary / "manifest.json", manifest)
        if destination.exists():
            shutil.rmtree(destination)
        os.replace(temporary, destination)
        manifest_path = destination / "manifest.json"
        pointer = {
            "schema": TARGET_COVERAGE_EXACT_NEIGHBORHOOD_NATIVE_POINTER_SCHEMA,
            "persistence_version": TARGET_COVERAGE_EXACT_NEIGHBORHOOD_PERSISTENCE_VERSION,
            "relative_path": str(manifest_path.relative_to(root.parent)),
            "sha256": _sha256_file(manifest_path),
            "content_digest": store.content_digest,
            "record_key": record_key,
        }
        return {**pointer, "pointer_digest": digest(pointer)}
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def read_target_coverage_exact_neighborhood_native_record(
    pointer: Mapping[str, Any],
    campaign_root: str | Path,
    *,
    mmap_threshold_bytes: int = 0,
) -> TargetCoverageExactNeighborhoodStore:
    if pointer.get("schema") != TARGET_COVERAGE_EXACT_NEIGHBORHOOD_NATIVE_POINTER_SCHEMA:
        raise TargetCoverageExactNeighborhoodNativeStoreError("Unsupported NEIGHBOR1 native pointer schema.")
    supplied_pointer_digest = pointer.get("pointer_digest")
    pointer_payload = {key: value for key, value in pointer.items() if key != "pointer_digest"}
    if supplied_pointer_digest not in (None, digest(pointer_payload)):
        raise TargetCoverageExactNeighborhoodNativeStoreError("NEIGHBOR1 native pointer digest mismatch.")
    root = Path(campaign_root).resolve()
    relative = Path(str(pointer.get("relative_path", "")))
    if relative.is_absolute() or ".." in relative.parts:
        raise TargetCoverageExactNeighborhoodNativeStoreError("NEIGHBOR1 native pointer escapes campaign root.")
    manifest_path = (root / relative).resolve()
    if root not in manifest_path.parents or not manifest_path.is_file():
        raise TargetCoverageExactNeighborhoodNativeStoreError("NEIGHBOR1 native manifest is missing.")
    if _sha256_file(manifest_path) != str(pointer.get("sha256", "")):
        raise TargetCoverageExactNeighborhoodNativeStoreError("NEIGHBOR1 native manifest checksum mismatch.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_schema = manifest.get("schema")
    if manifest_schema not in {
        TARGET_COVERAGE_EXACT_NEIGHBORHOOD_NATIVE_MANIFEST_SCHEMA,
        TARGET_COVERAGE_EXACT_NEIGHBORHOOD_LEGACY_NATIVE_MANIFEST_SCHEMA,
    }:
        raise TargetCoverageExactNeighborhoodNativeStoreError("Unsupported NEIGHBOR1 native manifest schema.")
    supplied = manifest.get("manifest_digest")
    expected = digest({key: value for key, value in manifest.items() if key != "manifest_digest"})
    if supplied != expected:
        raise TargetCoverageExactNeighborhoodNativeStoreError("NEIGHBOR1 native manifest digest mismatch.")
    data_root = manifest_path.parent
    packed_payload = manifest.get("packed_arrays")
    if (
        manifest_schema == TARGET_COVERAGE_EXACT_NEIGHBORHOOD_NATIVE_MANIFEST_SCHEMA
        and not isinstance(packed_payload, Mapping)
    ):
        raise TargetCoverageExactNeighborhoodNativeStoreError(
            "NEIGHBOR1 native v2 manifest is missing packed arrays."
        )
    packed_offsets: np.memmap | None = None
    packed_candidates: np.memmap | None = None
    if isinstance(packed_payload, Mapping):
        try:
            packed_offsets = _read_packed_npy(
                data_root, packed_payload["witness_offsets"], label="witness_offsets"
            )
            packed_candidates = _read_packed_npy(
                data_root, packed_payload["witness_candidates"], label="witness_candidates"
            )
        except Exception:
            for array in (packed_offsets, packed_candidates):
                if array is not None:
                    mapping = getattr(array, "_mmap", None)
                    if mapping is not None and not mapping.closed:
                        mapping.close()
            raise

    domains: list[TargetCoverageExactNeighborhoodDomain] = []
    packed_offset_cursor = 0
    packed_candidate_cursor = 0
    for domain_payload in manifest.get("domains", ()):
        families: list[TargetCoverageExactNeighborhoodFamily] = []
        for family_payload in domain_payload.get("families", ()):
            family_id = str(family_payload["family_id"])
            if packed_offsets is not None and packed_candidates is not None:
                slices = family_payload.get("array_slices", {})
                offset_slice = slices.get("witness_offsets", {})
                candidate_slice = slices.get("witness_candidates", {})
                if int(offset_slice.get("start", -1)) != packed_offset_cursor:
                    raise TargetCoverageExactNeighborhoodNativeStoreError(
                        f"NEIGHBOR1 packed witness_offsets are not canonical at family {family_id}."
                    )
                if int(candidate_slice.get("start", -1)) != packed_candidate_cursor:
                    raise TargetCoverageExactNeighborhoodNativeStoreError(
                        f"NEIGHBOR1 packed witness_candidates are not canonical at family {family_id}."
                    )
                witness_offsets = _packed_slice(
                    packed_offsets, offset_slice, label=f"family {family_id} witness_offsets"
                )
                witness_candidates = _packed_slice(
                    packed_candidates, candidate_slice, label=f"family {family_id} witness_candidates"
                )
                packed_offset_cursor = int(offset_slice["stop"])
                packed_candidate_cursor = int(candidate_slice["stop"])
            else:
                arrays = family_payload.get("arrays", {})
                witness_offsets = _read_npy(
                    data_root,
                    arrays["witness_offsets"],
                    label=f"family {family_id} witness_offsets",
                    mmap_threshold_bytes=mmap_threshold_bytes,
                )
                witness_candidates = _read_npy(
                    data_root,
                    arrays["witness_candidates"],
                    label=f"family {family_id} witness_candidates",
                    mmap_threshold_bytes=mmap_threshold_bytes,
                )
            family = TargetCoverageExactNeighborhoodFamily(
                label_domain_id=str(family_payload["label_domain_id"]),
                frame_domain_digest=str(family_payload["frame_domain_digest"]),
                family_id=family_id,
                family_digest=str(family_payload["family_digest"]),
                candidate_count=int(family_payload["candidate_count"]),
                witness_count=int(family_payload["witness_count"]),
                witness_offsets=witness_offsets,
                witness_candidates=witness_candidates,
                metric_tolerance=float(family_payload["metric_tolerance"]),
                distance_semantics=str(family_payload["distance_semantics"]),
                authority_version=str(family_payload["authority_version"]),
            )
            if family_payload.get("identity_digest") != family.identity_digest:
                raise TargetCoverageExactNeighborhoodNativeStoreError("NEIGHBOR1 family identity digest mismatch.")
            if family_payload.get("content_digest") != family.content_digest:
                raise TargetCoverageExactNeighborhoodNativeStoreError("NEIGHBOR1 family content digest mismatch.")
            if int(family_payload.get("edge_count", -1)) != family.edge_count:
                raise TargetCoverageExactNeighborhoodNativeStoreError("NEIGHBOR1 family edge count mismatch.")
            families.append(family)
        domain = TargetCoverageExactNeighborhoodDomain(
            label_domain_id=str(domain_payload["label_domain_id"]),
            frame_domain_digest=str(domain_payload["frame_domain_digest"]),
            candidate_count=int(domain_payload["candidate_count"]),
            families=tuple(families),
            authority_version=str(domain_payload["authority_version"]),
        )
        if domain_payload.get("content_digest") != domain.content_digest:
            raise TargetCoverageExactNeighborhoodNativeStoreError("NEIGHBOR1 domain content digest mismatch.")
        domains.append(domain)
    if packed_offsets is not None and packed_offset_cursor != int(packed_offsets.size):
        raise TargetCoverageExactNeighborhoodNativeStoreError(
            "NEIGHBOR1 packed witness_offsets contain unreferenced trailing data."
        )
    if packed_candidates is not None and packed_candidate_cursor != int(packed_candidates.size):
        raise TargetCoverageExactNeighborhoodNativeStoreError(
            "NEIGHBOR1 packed witness_candidates contain unreferenced trailing data."
        )
    store = TargetCoverageExactNeighborhoodStore(
        dataset_id=str(manifest["dataset_id"]),
        target_coverage_reference_digest=str(manifest["target_coverage_reference_digest"]),
        domains=tuple(domains),
        authority_version=str(manifest["authority_version"]),
    )
    if manifest.get("content_digest") != store.content_digest:
        raise TargetCoverageExactNeighborhoodNativeStoreError("NEIGHBOR1 native store content digest mismatch.")
    if pointer.get("content_digest") != store.content_digest:
        raise TargetCoverageExactNeighborhoodNativeStoreError("NEIGHBOR1 native pointer/store digest mismatch.")
    return store


__all__ = [
    "TARGET_COVERAGE_EXACT_NEIGHBORHOOD_LEGACY_NATIVE_MANIFEST_SCHEMA",
    "TARGET_COVERAGE_EXACT_NEIGHBORHOOD_NATIVE_MANIFEST_SCHEMA",
    "TARGET_COVERAGE_EXACT_NEIGHBORHOOD_NATIVE_POINTER_SCHEMA",
    "TargetCoverageExactNeighborhoodNativeStoreError",
    "write_target_coverage_exact_neighborhood_native_record",
    "read_target_coverage_exact_neighborhood_native_record",
]
