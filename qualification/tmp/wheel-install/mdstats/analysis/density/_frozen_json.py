"""Small immutable JSON mapping used by analysis-owned numerical records."""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from enum import Enum
from types import MappingProxyType
from typing import Any

import numpy as np

from .numerical_errors import DensityNumericalInputError


def _as_python_scalar(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Enum):
        return value.value
    return value


def _freeze(value: Any, *, path: str) -> Any:
    value = _as_python_scalar(value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not np.isfinite(value):
            raise DensityNumericalInputError(f"{path} contains a non-finite float.")
        return float(value)
    if isinstance(value, np.ndarray):
        return tuple(_freeze(item, path=f"{path}[]") for item in value.tolist())
    if isinstance(value, Mapping):
        return FrozenJSONMapping(value, _path=path)
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item, path=f"{path}[]") for item in value)
    raise DensityNumericalInputError(
        f"{path} contains unsupported non-JSON value {type(value).__name__}."
    )


def _thaw(value: Any) -> Any:
    if isinstance(value, FrozenJSONMapping):
        return value.to_json_dict()
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


class FrozenJSONMapping(Mapping[str, Any]):
    __slots__ = ("_data", "_hash")

    def __init__(
        self, mapping: Mapping[str, Any] | None = None, *, _path: str = "metadata"
    ) -> None:
        source = {} if mapping is None else dict(mapping)
        frozen: dict[str, Any] = {}
        for key in sorted(source):
            if not isinstance(key, str):
                raise DensityNumericalInputError(f"{_path} keys must be strings.")
            frozen[key] = _freeze(source[key], path=f"{_path}.{key}")
        self._data = MappingProxyType(frozen)
        self._hash: int | None = None

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"FrozenJSONMapping({dict(self._data)!r})"

    def __hash__(self) -> int:
        if self._hash is None:
            self._hash = hash(self.canonical_json())
        return self._hash

    def to_json_dict(self) -> dict[str, Any]:
        return {key: _thaw(value) for key, value in self._data.items()}

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_json_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )


def freeze_json_mapping(
    value: Mapping[str, Any] | FrozenJSONMapping | None,
) -> FrozenJSONMapping:
    if isinstance(value, FrozenJSONMapping):
        return value
    return FrozenJSONMapping(value)
