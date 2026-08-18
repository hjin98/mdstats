"""Canonical serialization and identity helpers for GFX3D.

Scientific, render, and execution identities are intentionally separate.  This
module contains no renderer or scientific-analysis imports.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

from .errors import Graphics3DValidationError


def canonical_value(value: Any) -> Any:
    """Return a JSON-compatible deterministic representation.

    The function is deliberately strict: NaN/infinity and opaque mutable Python
    objects are rejected rather than receiving process-specific string forms.
    """

    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if not np.isfinite(number):
            raise Graphics3DValidationError(
                "Canonical GFX3D values cannot contain NaN or infinity."
            )
        return number
    if isinstance(value, Enum):
        return canonical_value(value.value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        if np.issubdtype(value.dtype, np.floating) and np.any(~np.isfinite(value)):
            raise Graphics3DValidationError(
                "Canonical GFX3D arrays cannot contain NaN or infinity."
            )
        return canonical_value(value.tolist())
    if is_dataclass(value):
        return {
            item.name: canonical_value(getattr(value, item.name))
            for item in fields(value)
            if not item.name.startswith("_")
        }
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise Graphics3DValidationError(
                    "Canonical GFX3D mapping keys must be nonempty strings."
                )
            normalized[key] = canonical_value(item)
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, (tuple, list)):
        return [canonical_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        encoded = [canonical_value(item) for item in value]
        return sorted(encoded, key=lambda item: canonical_json(item))
    raise Graphics3DValidationError(
        f"Unsupported canonical GFX3D value {type(value).__name__}."
    )


def canonical_json(value: Any, *, indent: int | None = None) -> str:
    """Serialize *value* using the canonical GFX3D JSON contract."""

    return json.dumps(
        canonical_value(value),
        sort_keys=True,
        separators=(",", ":") if indent is None else None,
        ensure_ascii=False,
        allow_nan=False,
        indent=indent,
    )


def identity_digest(schema: str, value: Any) -> str:
    """Return a schema-bound SHA-256 identity for a canonical payload."""

    if not isinstance(schema, str) or not schema.strip():
        raise Graphics3DValidationError("Identity schema must be a nonempty string.")
    payload = {"schema": schema.strip(), "value": canonical_value(value)}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
