"""Private shared helpers for the Stage-11E8a pilot modules.

The functions in this module centralize deterministic serialization, SHA-256
signing, immutable metadata normalization, array accounting, and evidence-record
replacement. They are intentionally private: public schemas and exception types
remain owned by :mod:`pilot_audit` and the stage modules.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np


def _input_error(message: str) -> Exception:
    # Lazy import avoids a module cycle while preserving the public exception
    # type exported by pilot_audit.
    from .pilot_audit import PilotAuditInputError

    return PilotAuditInputError(message)


def canonical_json(value: Any) -> str:
    """Return the canonical JSON representation used by every pilot signature."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def digest(value: Any) -> str:
    """Return the canonical SHA-256 digest of a JSON-compatible value."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    """Return the SHA-256 digest of exact file bytes."""

    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def array_digest(value: np.ndarray) -> str:
    """Digest an array with dtype and shape included in the signed payload."""

    array = np.ascontiguousarray(value)
    hasher = hashlib.sha256()
    hasher.update(array.dtype.str.encode("ascii"))
    hasher.update(str(array.shape).encode("ascii"))
    hasher.update(array.tobytes())
    return hasher.hexdigest()


def freeze(value: Any) -> Any:
    """Normalize metadata to recursively immutable finite Python values."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        result = float(value)
        if not np.isfinite(result):
            raise _input_error("Metadata contains a non-finite value.")
        return result
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, Mapping):
        return MappingProxyType(
            {
                str(key): freeze(item)
                for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            }
        )
    if isinstance(value, (tuple, list)):
        return tuple(freeze(item) for item in value)
    raise _input_error(f"Unsupported metadata value {type(value).__name__}.")


def json_value(value: Any) -> Any:
    """Convert frozen metadata back to deterministic JSON-compatible values."""

    if isinstance(value, Mapping):
        return {
            str(key): json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, tuple):
        return [json_value(item) for item in value]
    if isinstance(value, np.generic):
        return json_value(value.item())
    return value


def positive(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise _input_error(f"{name} must be finite and positive.")
    return result


def nonnegative(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise _input_error(f"{name} must be finite and nonnegative.")
    return result


def fraction(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or not (0.0 <= result <= 1.0):
        raise _input_error(f"{name} must be in [0, 1].")
    return result


def positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or int(value) <= 0:
        raise _input_error(f"{name} must be a positive integer.")
    return int(value)


def readonly_array(
    value: Any,
    *,
    dtype: Any,
    ndim: int,
    name: str,
    shape: tuple[int, ...] | None = None,
) -> np.ndarray:
    array = np.array(value, dtype=dtype, copy=True)
    if array.ndim != ndim or (shape is not None and array.shape != shape):
        raise _input_error(f"{name} has invalid shape {array.shape}.")
    if np.issubdtype(array.dtype, np.floating) and np.any(~np.isfinite(array)):
        raise _input_error(f"{name} contains non-finite values.")
    array.setflags(write=False)
    return array


def array_payload_bytes(*objects: Any) -> int:
    """Count unique resident NumPy payload bytes reachable from objects."""

    seen_objects: set[int] = set()
    seen_arrays: set[int] = set()
    total = 0

    def visit(value: Any) -> None:
        nonlocal total
        if value is None or isinstance(
            value, (str, bytes, bool, int, float, np.generic)
        ):
            return
        identifier = id(value)
        if identifier in seen_objects:
            return
        seen_objects.add(identifier)
        if isinstance(value, np.ndarray):
            if identifier not in seen_arrays:
                seen_arrays.add(identifier)
                total += int(value.nbytes)
            return
        if is_dataclass(value):
            for item in fields(value):
                visit(getattr(value, item.name))
            return
        if isinstance(value, Mapping):
            for item in value.values():
                visit(item)
            return
        if isinstance(value, (tuple, list)):
            for item in value:
                visit(item)

    for obj in objects:
        visit(obj)
    return total


def replace_evidence(records: tuple[Any, ...], replacements: Mapping[str, Any]) -> tuple[Any, ...]:
    """Replace evidence records by ``evidence_id`` in canonical order."""

    retained = [
        record for record in records if record.evidence_id not in replacements
    ]
    retained.extend(replacements.values())
    return tuple(sorted(retained, key=lambda record: record.evidence_id))
