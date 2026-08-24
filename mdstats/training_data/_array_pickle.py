"""Pickle helpers that preserve large NumPy arrays as file references.

The MLFF isolated-worker path uses one-shot subprocesses for crash containment.
Ordinary pickle serializes ``numpy.memmap`` payloads byte-for-byte, defeating
our read-only frame-cache architecture.  These helpers encode direct mmap views
as path/offset references and spill large in-memory arrays to temporary NPY
members.  Public scientific serialization is unaffected; this module is only a
process-local transport optimization.
"""
from __future__ import annotations

import mmap
import os
from pathlib import Path
import pickle
from dataclasses import fields, is_dataclass
from collections.abc import Mapping
from typing import Any, BinaryIO

import numpy as np

_ARRAY_REF_TAG = "mdstats.ndarray-file-ref.v1"
_DEFAULT_EXTERNALIZE_BYTES = 1 << 20


def _root_memmap(array: np.ndarray) -> np.memmap | None:
    current: Any = array
    visited: set[int] = set()
    while isinstance(current, np.ndarray) and id(current) not in visited:
        visited.add(id(current))
        if isinstance(current, np.memmap):
            base = current.base
            if isinstance(base, mmap.mmap):
                return current
        current = getattr(current, "base", None)
    return None


def _order(array: np.ndarray) -> str | None:
    if array.flags.c_contiguous:
        return "C"
    if array.flags.f_contiguous:
        return "F"
    return None


class _ArrayReferencePickler(pickle.Pickler):
    def __init__(
        self,
        handle: BinaryIO,
        *,
        array_directory: Path,
        externalize_bytes: int,
    ) -> None:
        super().__init__(handle, protocol=5)
        self._array_directory = array_directory
        self._externalize_bytes = max(0, int(externalize_bytes))
        self._seen: dict[int, tuple[Any, ...]] = {}
        self._counter = 0

    def persistent_id(self, obj: Any) -> tuple[Any, ...] | None:
        if not isinstance(obj, np.ndarray):
            return None
        cached = self._seen.get(id(obj))
        if cached is not None:
            return cached
        order = _order(obj)
        root = _root_memmap(obj)
        if root is not None and order is not None:
            filename = getattr(root, "filename", None)
            if filename is not None:
                path = Path(os.fspath(filename)).resolve()
                byte_offset = int(root.offset) + int(obj.ctypes.data - root.ctypes.data)
                pid = (
                    _ARRAY_REF_TAG,
                    "raw-mmap",
                    str(path),
                    byte_offset,
                    obj.dtype.str,
                    tuple(int(v) for v in obj.shape),
                    order,
                )
                self._seen[id(obj)] = pid
                return pid
        if int(obj.nbytes) < self._externalize_bytes:
            return None
        self._array_directory.mkdir(parents=True, exist_ok=True)
        name = f"array-{self._counter:06d}.npy"
        self._counter += 1
        destination = self._array_directory / name
        temporary = destination.with_suffix(".npy.tmp")
        with temporary.open("wb") as handle:
            np.save(handle, np.asarray(obj, order="C"), allow_pickle=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        pid = (_ARRAY_REF_TAG, "npy", str(destination.resolve()))
        self._seen[id(obj)] = pid
        return pid


class _ArrayReferenceUnpickler(pickle.Unpickler):
    def persistent_load(self, pid: Any) -> np.ndarray:
        if not isinstance(pid, tuple) or not pid or pid[0] != _ARRAY_REF_TAG:
            raise pickle.UnpicklingError(f"Unsupported persistent pickle ID: {pid!r}")
        kind = pid[1]
        if kind == "npy":
            path = Path(str(pid[2]))
            try:
                array = np.load(path, mmap_mode="r", allow_pickle=False)
            except Exception as exc:
                raise pickle.UnpicklingError(
                    f"Cannot restore externalized array {path!s}."
                ) from exc
            array.setflags(write=False)
            return array
        if kind == "raw-mmap":
            _, _, raw_path, offset, dtype, shape, order = pid
            path = Path(str(raw_path))
            if not path.is_file():
                raise pickle.UnpicklingError(
                    f"Referenced memory-map source is missing: {path!s}."
                )
            try:
                array = np.memmap(
                    path,
                    mode="r",
                    dtype=np.dtype(dtype),
                    offset=int(offset),
                    shape=tuple(int(v) for v in shape),
                    order=str(order),
                )
            except Exception as exc:
                raise pickle.UnpicklingError(
                    f"Cannot restore memory-map reference {path!s}."
                ) from exc
            array.setflags(write=False)
            return array
        raise pickle.UnpicklingError(f"Unsupported array reference kind: {kind!r}")



def estimate_array_reference_spill_bytes(
    value: Any, *, externalize_bytes: int = _DEFAULT_EXTERNALIZE_BYTES
) -> int:
    """Estimate NPY bytes that ``dump_with_array_references`` will externalize.

    Direct mmap views contribute no new disk bytes.  Large in-memory arrays are
    counted once by object identity with a small NPY-header allowance.  The
    traversal intentionally covers the immutable dataclass/container graph used
    by DATA8 worker contexts without invoking arbitrary properties.
    """

    threshold = max(0, int(externalize_bytes))
    seen: set[int] = set()

    def visit(obj: Any) -> int:
        if isinstance(obj, np.ndarray):
            key = id(obj)
            if key in seen:
                return 0
            seen.add(key)
            if _root_memmap(obj) is not None and _order(obj) is not None:
                return 0
            return int(obj.nbytes) + 4096 if int(obj.nbytes) >= threshold else 0
        if isinstance(obj, (str, bytes, bytearray, int, float, bool, type(None), Path)):
            return 0
        key = id(obj)
        if key in seen:
            return 0
        seen.add(key)
        if isinstance(obj, Mapping):
            return sum(visit(k) + visit(v) for k, v in obj.items())
        if isinstance(obj, (tuple, list, set, frozenset)):
            return sum(visit(item) for item in obj)
        if is_dataclass(obj) and not isinstance(obj, type):
            return sum(visit(getattr(obj, field.name)) for field in fields(obj))
        state = getattr(obj, "__dict__", None)
        if isinstance(state, dict):
            return visit(state)
        return 0

    return visit(value)

def dump_with_array_references(
    value: Any,
    handle: BinaryIO,
    *,
    array_directory: str | Path,
    externalize_bytes: int = _DEFAULT_EXTERNALIZE_BYTES,
) -> None:
    _ArrayReferencePickler(
        handle,
        array_directory=Path(array_directory),
        externalize_bytes=externalize_bytes,
    ).dump(value)


def load_with_array_references(handle: BinaryIO) -> Any:
    return _ArrayReferenceUnpickler(handle).load()
