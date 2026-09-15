"""Authenticated file-backed persistence shared by the target-order products.

The recovered TARGET-DATA2B reference, NEIGHBOR1 and MVIDX1 stores each carried
their own copy of the same NPY/manifest/hash mechanics.  This module is the one
current implementation of that mechanism: immutable artifact directories whose
manifest authenticates every member file, packed shared roots so mapped file
descriptors stay O(1) in family count, and create-or-verify publication through
an attempt-owned temporary directory plus one locked atomic rename.

Nothing here is scientific authority.  Directory names, mmap policy, and hard
link reuse are execution/storage details; the owner that writes an artifact
decides what its manifest binds.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import mmap
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from .._common import (
    TrainingDataError,
    canonical_json,
    digest,
    sha256_file_cached,
)
from ..persistence import artifact_publication_lock, fsync_parent_directory

ARRAY_REFERENCE_SCHEMA = "mdstats.target-coverage-array.v1"
ARTIFACT_MANIFEST_NAME = "manifest.json"


class TargetOrderArtifactStoreError(TrainingDataError):
    """A persisted target-order artifact is missing, modified, or inconsistent."""


def _sha256_array_bytes(array: np.ndarray, *, chunk_bytes: int = 8 * 1024 * 1024) -> str:
    contiguous = np.ascontiguousarray(array)
    view = memoryview(contiguous).cast("B")
    hasher = hashlib.sha256()
    for offset in range(0, len(view), max(1, int(chunk_bytes))):
        hasher.update(view[offset:offset + chunk_bytes])
    return hasher.hexdigest()


def array_reference(array: np.ndarray) -> dict[str, Any]:
    """Content identity of one canonical numerical array."""

    contiguous = np.ascontiguousarray(array)
    payload = {
        "schema": ARRAY_REFERENCE_SCHEMA,
        "dtype": contiguous.dtype.str,
        "shape": [int(value) for value in contiguous.shape],
        "byte_count": int(contiguous.nbytes),
        "value_sha256": _sha256_array_bytes(contiguous),
    }
    return {**payload, "content_digest": digest(payload)}


def validate_array_reference(
    supplied: Mapping[str, Any] | None, array: np.ndarray, *, name: str
) -> None:
    if supplied is None:
        return
    if dict(supplied) != array_reference(array):
        raise TargetOrderArtifactStoreError(f"{name} array reference mismatch.")


def _validate_reference_metadata(
    reference: Mapping[str, Any], array: np.ndarray, *, label: str
) -> None:
    """Check identity metadata without rehashing file-authenticated bytes."""

    payload = {
        "schema": ARRAY_REFERENCE_SCHEMA,
        "dtype": array.dtype.str,
        "shape": [int(value) for value in array.shape],
        "byte_count": int(array.nbytes),
        "value_sha256": str(reference.get("value_sha256", "")),
    }
    if (
        reference.get("schema") != ARRAY_REFERENCE_SCHEMA
        or reference.get("dtype") != payload["dtype"]
        or reference.get("shape") != payload["shape"]
        or int(reference.get("byte_count", -1)) != payload["byte_count"]
        or reference.get("content_digest") != digest(payload)
        or len(payload["value_sha256"]) != 64
    ):
        raise TargetOrderArtifactStoreError(f"{label} array identity mismatch.")


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


def root_memmap(array: np.ndarray) -> np.memmap | None:
    """Return the memmap that owns the actual file mapping behind ``array``."""

    current: Any = array
    visited: set[int] = set()
    while isinstance(current, np.ndarray) and id(current) not in visited:
        visited.add(id(current))
        if isinstance(current, np.memmap) and isinstance(getattr(current, "base", None), mmap.mmap):
            return current
        current = getattr(current, "base", None)
    return None


def close_memmap(array: np.ndarray | None) -> None:
    if array is None:
        return
    root = root_memmap(array)
    mapping = None if root is None else getattr(root, "_mmap", None)
    if mapping is not None and not mapping.closed:
        mapping.close()


def _whole_npy_memmap_source(array: np.ndarray) -> Path | None:
    """Return the backing NPY file when ``array`` covers one complete memmap."""

    root = root_memmap(array)
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
        close_memmap(probe)
        del probe
    return source


def write_npy(directory: Path, filename: str, array: np.ndarray) -> dict[str, Any]:
    """Write one NPY member, hard-linking an already complete NPY memmap."""

    path = Path(directory) / filename
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
                "sha256": sha256_file_cached(source),
                "size_bytes": source.stat().st_size,
                "array_reference": array_reference(contiguous),
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
        "array_reference": array_reference(contiguous),
    }


def _shared_packed_root(arrays: Sequence[np.ndarray]) -> np.memmap | None:
    root: np.memmap | None = None
    cursor = 0
    for raw in arrays:
        array = np.asarray(raw)
        candidate = root_memmap(array)
        if candidate is None or candidate.ndim != 1 or not array.flags.c_contiguous:
            return None
        if root is None:
            root = candidate
        elif candidate is not root:
            return None
        if int(array.ctypes.data) - int(candidate.ctypes.data) != cursor * array.dtype.itemsize:
            return None
        cursor += int(array.size)
    if root is None or cursor != int(root.size):
        return None
    return root


def write_packed(
    directory: Path,
    filename: str,
    arrays: Sequence[np.ndarray],
    *,
    dtype: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Pack many one-dimensional members into one shared NPY root.

    Returns the root descriptor plus one ``{start, stop, array_reference}``
    slice per member.  An input that already is one complete packed memmap is
    hard-linked instead of copied.
    """

    target = np.dtype(dtype).newbyteorder("<")
    members = [np.asarray(item) for item in arrays]
    slices: list[dict[str, Any]] = []
    cursor = 0
    for member in members:
        if member.ndim != 1:
            raise TargetOrderArtifactStoreError("Packed members must be one-dimensional.")
        stop = cursor + int(member.size)
        slices.append(
            {
                "start": int(cursor),
                "stop": int(stop),
                "array_reference": array_reference(np.asarray(member, dtype=target)),
            }
        )
        cursor = stop
    root = _shared_packed_root(members)
    if root is not None and root.dtype == target:
        descriptor = write_npy(directory, filename, root)
        descriptor.pop("array_reference")
        return {**descriptor, "dtype": target.str, "shape": [int(cursor)]}, slices
    path = Path(directory) / filename
    packed = np.lib.format.open_memmap(path, mode="w+", dtype=target, shape=(cursor,))
    try:
        cursor = 0
        for member in members:
            stop = cursor + int(member.size)
            packed[cursor:stop] = np.asarray(member, dtype=target)
            cursor = stop
        packed.flush()
    finally:
        close_memmap(packed)
        del packed
    return (
        {
            "relative_path": path.name,
            "sha256": sha256_file_cached(path),
            "size_bytes": path.stat().st_size,
            "dtype": target.str,
            "shape": [int(cursor)],
        },
        slices,
    )


def _safe_member(directory: Path, descriptor: Mapping[str, Any], *, label: str) -> Path:
    relative = Path(str(descriptor.get("relative_path", "")))
    if relative.is_absolute() or ".." in relative.parts or relative in {Path(""), Path(".")}:
        raise TargetOrderArtifactStoreError(f"Invalid {label} member path.")
    root = Path(directory).resolve()
    path = (root / relative).resolve()
    if root not in path.parents or not path.is_file():
        raise TargetOrderArtifactStoreError(f"Missing {label} member: {path}")
    size = int(descriptor.get("size_bytes", -1))
    if size < 0 or path.stat().st_size != size:
        raise TargetOrderArtifactStoreError(f"Truncated or resized {label} member: {path}")
    expected = str(descriptor.get("sha256", ""))
    if not expected or sha256_file_cached(path) != expected:
        raise TargetOrderArtifactStoreError(f"Checksum mismatch for {label} member: {path}")
    return path


def read_npy(
    directory: Path,
    descriptor: Mapping[str, Any],
    *,
    label: str,
    mmap_threshold_bytes: int = 8 * 1024 * 1024,
) -> np.ndarray:
    path = _safe_member(directory, descriptor, label=label)
    reference = descriptor.get("array_reference")
    if not isinstance(reference, Mapping):
        raise TargetOrderArtifactStoreError(f"Missing {label} array identity.")
    byte_count = int(reference.get("byte_count", -1))
    mode = "r" if byte_count >= max(0, int(mmap_threshold_bytes)) else None
    try:
        array = np.load(path, mmap_mode=mode, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise TargetOrderArtifactStoreError(f"Cannot restore {label} member: {path}") from exc
    _validate_reference_metadata(reference, array, label=label)
    array.setflags(write=False)
    return array


def read_packed(directory: Path, descriptor: Mapping[str, Any], *, label: str) -> np.memmap:
    path = _safe_member(directory, descriptor, label=label)
    try:
        array = np.load(path, mmap_mode="r", allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise TargetOrderArtifactStoreError(f"Cannot restore packed {label}: {path}") from exc
    if (
        array.ndim != 1
        or array.dtype.str != str(descriptor.get("dtype", ""))
        or [int(v) for v in array.shape] != list(descriptor.get("shape", ()))
    ):
        close_memmap(array)
        raise TargetOrderArtifactStoreError(f"Packed {label} metadata mismatch.")
    array.setflags(write=False)
    return array


def packed_slice(
    packed: np.ndarray, descriptor: Mapping[str, Any], *, label: str, cursor: int
) -> np.ndarray:
    """Return one canonical packed member; slices must tile the root in order."""

    start = int(descriptor.get("start", -1))
    stop = int(descriptor.get("stop", -1))
    if start != int(cursor) or stop < start or stop > int(packed.size):
        raise TargetOrderArtifactStoreError(f"Packed {label} slices are not canonical.")
    member = packed[start:stop]
    reference = descriptor.get("array_reference")
    if not isinstance(reference, Mapping):
        raise TargetOrderArtifactStoreError(f"Missing {label} packed-slice identity.")
    _validate_reference_metadata(reference, member, label=label)
    member.setflags(write=False)
    return member


def write_manifest(directory: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    manifest = {**dict(payload), "manifest_digest": digest(dict(payload))}
    path = Path(directory) / ARTIFACT_MANIFEST_NAME
    temporary = path.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(canonical_json(manifest))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return manifest


def read_manifest(directory: Path, *, schema: str) -> dict[str, Any]:
    path = Path(directory) / ARTIFACT_MANIFEST_NAME
    if not path.is_file():
        raise TargetOrderArtifactStoreError(f"Target-order artifact manifest is missing: {path}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TargetOrderArtifactStoreError(f"Unreadable target-order artifact manifest: {path}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema") != schema:
        raise TargetOrderArtifactStoreError(
            f"Unsupported or obsolete target-order artifact layout at {path}."
        )
    expected = digest({key: value for key, value in manifest.items() if key != "manifest_digest"})
    if manifest.get("manifest_digest") != expected:
        raise TargetOrderArtifactStoreError(f"Target-order artifact manifest digest mismatch: {path}")
    return manifest


@dataclass(frozen=True, slots=True)
class PublishedArtifact:
    """One immutable artifact directory and the manifest that authenticates it."""

    directory: Path
    manifest: Mapping[str, Any]

    @property
    def content_digest(self) -> str:
        return str(self.manifest["content_digest"])

    @property
    def manifest_digest(self) -> str:
        return str(self.manifest["manifest_digest"])


def publish_artifact_directory(
    destination: Path,
    *,
    schema: str,
    write: Callable[[Path], Mapping[str, Any]],
    verify_existing: Callable[[Path, Mapping[str, Any]], None],
) -> PublishedArtifact:
    """Create-or-verify one immutable artifact directory.

    ``write`` fills an attempt-owned temporary directory and returns the
    manifest payload (which must carry ``schema`` and ``content_digest``).  The
    directory becomes visible only through one atomic rename under the shared
    destination advisory lock, so an interrupted or failed writer leaves
    nothing reachable at ``destination``.  When the destination already exists
    it is authenticated under that lock: identical valid content is reused and
    ours is discarded; corrupt, obsolete, or conflicting content fails closed
    and is left untouched.  A published destination may be protected by a
    prepared generation, so retiring it belongs to the storage/retention owner,
    never to a publisher.
    """

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{destination.name[:24]}-attempt-", dir=destination.parent)
    )
    try:
        payload = dict(write(temporary))
        if payload.get("schema") != schema or not payload.get("content_digest"):
            raise TargetOrderArtifactStoreError(
                "Target-order artifact writer returned an incomplete manifest."
            )
        manifest = write_manifest(temporary, payload)
        with artifact_publication_lock(destination):
            if destination.exists():
                try:
                    existing = read_manifest(destination, schema=schema)
                    if existing.get("content_digest") != manifest["content_digest"]:
                        raise TargetOrderArtifactStoreError(
                            "the published artifact carries different content"
                        )
                    verify_existing(destination, existing)
                except (TargetOrderArtifactStoreError, TrainingDataError) as exc:
                    raise TargetOrderArtifactStoreError(
                        f"Existing immutable target-order artifact at {destination} is corrupt "
                        f"or conflicting ({exc}); it is not replaced by publication."
                    ) from exc
                shutil.rmtree(temporary, ignore_errors=True)
                return PublishedArtifact(destination, existing)
            os.rename(temporary, destination)
            fsync_parent_directory(destination)
        return PublishedArtifact(destination, manifest)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


__all__ = [
    "ARRAY_REFERENCE_SCHEMA",
    "PublishedArtifact",
    "TargetOrderArtifactStoreError",
    "array_reference",
    "close_memmap",
    "packed_slice",
    "publish_artifact_directory",
    "read_manifest",
    "read_npy",
    "read_packed",
    "root_memmap",
    "validate_array_reference",
    "write_manifest",
    "write_npy",
    "write_packed",
]
