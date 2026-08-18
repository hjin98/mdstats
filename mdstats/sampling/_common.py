"""Internal canonical serialization helpers for :mod:`mdstats.sampling`."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any


class SamplingError(ValueError):
    """Base error for source-independent sampling primitives."""


class SamplingInputError(SamplingError):
    """Raised when a sampling primitive receives invalid input."""


class SamplingSerializationError(SamplingError):
    """Raised when serialized sampling evidence cannot be replayed."""


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def finite_float(value: Any, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise SamplingInputError(f"{name} must be finite.")
    return result
