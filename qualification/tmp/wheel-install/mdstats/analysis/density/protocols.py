"""Analysis-owned protocols and adapters for scientific density fields.

Stage 11E0a intentionally does not move the established numerical density
implementations.  Instead, this module defines the canonical analysis-facing
protocol and zero-copy adapters around any compatible current field object.
No rendering, mesh, browser-budget, Plotly, or HTML type is imported here.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

SCIENTIFIC_DENSITY_FIELD_ADAPTER_SCHEMA = (
    "mdstats.analysis-density-field-adapter.v1"
)
SCIENTIFIC_DENSITY_BUNDLE_SCHEMA = "mdstats.analysis-density-bundle.v1"
SCIENTIFIC_DENSITY_FACADE_STAGE = "11E0a"


class ScientificDensityError(RuntimeError):
    """Base error for the Stage-11E0a scientific density facade."""


class ScientificDensityInputError(ScientificDensityError, ValueError):
    """Raised when a requested density facade input is invalid."""


class ScientificDensityCompatibilityError(ScientificDensityError, TypeError):
    """Raised when a legacy field does not satisfy the scientific protocol."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not np.isfinite(value):
            raise ScientificDensityInputError(
                "Density metadata contains a non-finite float."
            )
        return float(value)
    if isinstance(value, np.generic):
        return _json_value(value.item())
    if isinstance(value, np.ndarray):
        return [_json_value(item) for item in value.tolist()]
    if isinstance(value, Mapping):
        return {
            str(key): _json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    to_json_dict = getattr(value, "to_json_dict", None)
    if callable(to_json_dict):
        return _json_value(to_json_dict())
    raise ScientificDensityInputError(
        f"Density metadata contains unsupported value {type(value).__name__}."
    )


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    source = {} if value is None else dict(value)
    frozen = {
        str(key): _freeze_value(item)
        for key, item in sorted(source.items(), key=lambda pair: str(pair[0]))
    }
    return MappingProxyType(frozen)


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, np.ndarray):
        array = np.array(value, copy=True)
        array.setflags(write=False)
        return array
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_value(item) for item in value)
    return value


def _readonly_float_array(
    value: Any, *, name: str, shape: tuple[int, ...] | None = None
) -> FloatArray:
    array = np.asarray(value, dtype=np.float64)
    if shape is not None and array.shape != shape:
        raise ScientificDensityCompatibilityError(
            f"{name} must have shape {shape}; received {array.shape}."
        )
    if np.any(~np.isfinite(array)):
        raise ScientificDensityCompatibilityError(f"{name} must be finite.")
    if array.flags.writeable:
        raise ScientificDensityCompatibilityError(
            f"{name} must be read-only at the scientific facade boundary."
        )
    return array


@runtime_checkable
class ScientificDensityField3D(Protocol):
    """Backend-neutral scientific scalar-field protocol.

    The protocol intentionally excludes rendering arrays, meshes, traces,
    browser budgets, and HTML methods.  Dense and sparse implementations expose
    the same scientific measure, periodic domain, normalization, HDR, and
    storage-summary surface.
    """

    schema_version: str
    field_key: str
    label: str
    physical_units: str
    display_cell: FloatArray
    total_measure: float
    gaussian_bandwidth: float
    smoothing_operator: str
    broadening_metric: str
    storage_backend: str
    source_provenance: Any
    metadata: Mapping[str, Any]

    @property
    def grid_shape(self) -> tuple[int, int, int]: ...

    @property
    def voxel_volume(self) -> float: ...

    @property
    def integral(self) -> float: ...

    def hdr_details(self, q: float) -> Any: ...

    def threshold_for_mass_fraction(self, q: float) -> float: ...

    def storage_summary(self) -> Any: ...


@runtime_checkable
class ScientificPeriodicNodeAccess(Protocol):
    """Optional periodic logical-node access for scientific field consumers."""

    def iter_stored_nodes(
        self,
        *,
        batch_size: int | None = None,
    ) -> Iterator[tuple[IntArray, FloatArray]]: ...

    def gather_node_values(self, logical_indices: IntArray) -> FloatArray: ...


def is_scientific_density_field(value: Any) -> bool:
    """Return whether *value* satisfies the analysis-owned field protocol."""

    return isinstance(value, ScientificDensityField3D)


def has_scientific_periodic_node_access(value: Any) -> bool:
    """Return whether *value* exposes periodic logical-node access."""

    return isinstance(value, ScientificPeriodicNodeAccess)


def _field_contract_payload(field: ScientificDensityField3D) -> dict[str, Any]:
    source = getattr(field, "source_provenance")
    source_json = (
        source.to_json_dict()
        if callable(getattr(source, "to_json_dict", None))
        else _json_value(source)
    )
    storage = field.storage_summary()
    storage_json = (
        storage.to_json_dict()
        if callable(getattr(storage, "to_json_dict", None))
        else _json_value(storage)
    )
    metadata = getattr(field, "metadata")
    if callable(getattr(metadata, "to_json_dict", None)):
        metadata_json = metadata.to_json_dict()
    else:
        metadata_json = _json_value(metadata)
    return {
        "schema_version": str(field.schema_version),
        "field_key": str(field.field_key),
        "label": str(field.label),
        "physical_units": str(field.physical_units),
        "display_cell": np.asarray(field.display_cell, dtype=np.float64).tolist(),
        "total_measure": float(field.total_measure),
        "gaussian_bandwidth": float(field.gaussian_bandwidth),
        "smoothing_operator": str(field.smoothing_operator),
        "broadening_metric": str(field.broadening_metric),
        "storage_backend": str(field.storage_backend),
        "grid_shape": [int(value) for value in field.grid_shape],
        "voxel_volume": float(field.voxel_volume),
        "integral": float(field.integral),
        "source_provenance": _json_value(source_json),
        "metadata": _json_value(metadata_json),
        "storage_summary": _json_value(storage_json),
    }


def _digest_payload(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(_json_value(payload)).encode("ascii")).hexdigest()


@dataclass(frozen=True, slots=True)
class ScientificDensityFieldAdapter:
    """Zero-copy compatibility adapter around one current numerical field.

    The adapter validates the scientific contract and delegates all numerical
    access to the existing immutable field.  Its signature certifies the field
    contract and provenance, not every stored voxel byte; numerical ownership is
    unchanged until Stage 11E0b.
    """

    legacy_field: ScientificDensityField3D
    numerical_owner: str
    adapter_metadata: Mapping[str, Any] = field(default_factory=dict)
    adapter_schema_version: str = SCIENTIFIC_DENSITY_FIELD_ADAPTER_SCHEMA
    contract_signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.adapter_schema_version != SCIENTIFIC_DENSITY_FIELD_ADAPTER_SCHEMA:
            raise ScientificDensityInputError(
                f"Unsupported field-adapter schema {self.adapter_schema_version!r}."
            )
        if not is_scientific_density_field(self.legacy_field):
            raise ScientificDensityCompatibilityError(
                "legacy_field does not satisfy ScientificDensityField3D."
            )
        if not isinstance(self.numerical_owner, str) or not self.numerical_owner:
            raise ScientificDensityInputError(
                "numerical_owner must be a nonempty module path."
            )
        field_value = self.legacy_field
        _readonly_float_array(
            field_value.display_cell, name="display_cell", shape=(3, 3)
        )
        shape = tuple(int(item) for item in field_value.grid_shape)
        if len(shape) != 3 or any(item <= 0 for item in shape):
            raise ScientificDensityCompatibilityError(
                "grid_shape must contain three positive integers."
            )
        for name, number, positive in (
            ("total_measure", field_value.total_measure, True),
            ("voxel_volume", field_value.voxel_volume, True),
            ("integral", field_value.integral, False),
            ("gaussian_bandwidth", field_value.gaussian_bandwidth, False),
        ):
            scalar = float(number)
            if not np.isfinite(scalar) or (positive and scalar <= 0.0) or (
                not positive and scalar < 0.0
            ):
                raise ScientificDensityCompatibilityError(
                    f"{name} has an invalid scientific value."
                )
        for name in (
            "schema_version",
            "field_key",
            "label",
            "physical_units",
            "smoothing_operator",
            "broadening_metric",
            "storage_backend",
        ):
            value = getattr(field_value, name)
            if not isinstance(value, str) or not value:
                raise ScientificDensityCompatibilityError(
                    f"{name} must be a nonempty string."
                )
        frozen_metadata = _freeze_mapping(self.adapter_metadata)
        payload = {
            "adapter_schema": self.adapter_schema_version,
            "facade_stage": SCIENTIFIC_DENSITY_FACADE_STAGE,
            "numerical_owner": self.numerical_owner,
            "field_contract": _field_contract_payload(field_value),
            "adapter_metadata": _json_value(frozen_metadata),
        }
        object.__setattr__(self, "adapter_metadata", frozen_metadata)
        object.__setattr__(self, "contract_signature", _digest_payload(payload))

    @property
    def schema_version(self) -> str:
        return self.legacy_field.schema_version

    @property
    def metadata(self) -> Mapping[str, Any]:
        return self.legacy_field.metadata

    @property
    def field_key(self) -> str:
        return self.legacy_field.field_key

    @property
    def label(self) -> str:
        return self.legacy_field.label

    @property
    def physical_units(self) -> str:
        return self.legacy_field.physical_units

    @property
    def display_cell(self) -> FloatArray:
        return self.legacy_field.display_cell

    @property
    def total_measure(self) -> float:
        return float(self.legacy_field.total_measure)

    @property
    def gaussian_bandwidth(self) -> float:
        return float(self.legacy_field.gaussian_bandwidth)

    @property
    def smoothing_operator(self) -> str:
        return self.legacy_field.smoothing_operator

    @property
    def broadening_metric(self) -> str:
        return self.legacy_field.broadening_metric

    @property
    def storage_backend(self) -> str:
        return self.legacy_field.storage_backend

    @property
    def source_provenance(self) -> Any:
        return self.legacy_field.source_provenance

    @property
    def grid_shape(self) -> tuple[int, int, int]:
        return tuple(int(item) for item in self.legacy_field.grid_shape)

    @property
    def voxel_volume(self) -> float:
        return float(self.legacy_field.voxel_volume)

    @property
    def integral(self) -> float:
        return float(self.legacy_field.integral)

    @property
    def has_periodic_node_access(self) -> bool:
        return has_scientific_periodic_node_access(self.legacy_field)

    def hdr_details(self, q: float) -> Any:
        return self.legacy_field.hdr_details(q)

    def threshold_for_mass_fraction(self, q: float) -> float:
        return float(self.legacy_field.threshold_for_mass_fraction(q))

    def storage_summary(self) -> Any:
        return self.legacy_field.storage_summary()

    def iter_stored_nodes(
        self,
        *,
        batch_size: int | None = None,
    ) -> Iterator[tuple[IntArray, FloatArray]]:
        if not has_scientific_periodic_node_access(self.legacy_field):
            raise ScientificDensityCompatibilityError(
                "The adapted field does not expose periodic node access."
            )
        yield from self.legacy_field.iter_stored_nodes(batch_size=batch_size)

    def gather_node_values(self, logical_indices: IntArray) -> FloatArray:
        if not has_scientific_periodic_node_access(self.legacy_field):
            raise ScientificDensityCompatibilityError(
                "The adapted field does not expose periodic node access."
            )
        return self.legacy_field.gather_node_values(logical_indices)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.adapter_schema_version,
            "field_schema_version": self.schema_version,
            "facade_stage": SCIENTIFIC_DENSITY_FACADE_STAGE,
            "field_key": self.field_key,
            "numerical_owner": self.numerical_owner,
            "contract_signature": self.contract_signature,
            "adapter_metadata": _json_value(self.adapter_metadata),
            "field_contract": _field_contract_payload(self.legacy_field),
        }


@dataclass(frozen=True, slots=True)
class ScientificDensityFieldBundle:
    """Canonical analysis result containing one or more scientific fields."""

    fields: tuple[ScientificDensityFieldAdapter, ...]
    source_kind: str
    resource_signature: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = SCIENTIFIC_DENSITY_BUNDLE_SCHEMA
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != SCIENTIFIC_DENSITY_BUNDLE_SCHEMA:
            raise ScientificDensityInputError(
                f"Unsupported density-bundle schema {self.schema_version!r}."
            )
        resolved = tuple(self.fields)
        if not resolved:
            raise ScientificDensityInputError(
                "A scientific density bundle requires at least one field."
            )
        if any(not isinstance(item, ScientificDensityFieldAdapter) for item in resolved):
            raise ScientificDensityCompatibilityError(
                "fields must contain ScientificDensityFieldAdapter objects."
            )
        keys = tuple(item.field_key for item in resolved)
        if len(set(keys)) != len(keys):
            raise ScientificDensityInputError("Density field keys must be unique.")
        if not isinstance(self.source_kind, str) or not self.source_kind:
            raise ScientificDensityInputError("source_kind must be nonempty.")
        if not isinstance(self.resource_signature, str) or not self.resource_signature:
            raise ScientificDensityInputError("resource_signature must be nonempty.")
        frozen_metadata = _freeze_mapping(self.metadata)
        payload = {
            "schema_version": self.schema_version,
            "facade_stage": SCIENTIFIC_DENSITY_FACADE_STAGE,
            "source_kind": self.source_kind,
            "resource_signature": self.resource_signature,
            "field_signatures": [item.contract_signature for item in resolved],
            "metadata": _json_value(frozen_metadata),
        }
        object.__setattr__(self, "fields", resolved)
        object.__setattr__(self, "metadata", frozen_metadata)
        object.__setattr__(self, "signature", _digest_payload(payload))

    @property
    def field_keys(self) -> tuple[str, ...]:
        return tuple(item.field_key for item in self.fields)

    def field(self, field_key: str) -> ScientificDensityFieldAdapter:
        for item in self.fields:
            if item.field_key == field_key:
                return item
        raise KeyError(field_key)

    def unwrap_legacy_fields(self) -> tuple[ScientificDensityField3D, ...]:
        """Return the exact current numerical fields without copying values."""

        return tuple(item.legacy_field for item in self.fields)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "facade_stage": SCIENTIFIC_DENSITY_FACADE_STAGE,
            "source_kind": self.source_kind,
            "resource_signature": self.resource_signature,
            "signature": self.signature,
            "metadata": _json_value(self.metadata),
            "fields": [item.to_json_dict() for item in self.fields],
        }


def adapt_scientific_density_field(
    field: ScientificDensityField3D,
    *,
    numerical_owner: str,
    metadata: Mapping[str, Any] | None = None,
) -> ScientificDensityFieldAdapter:
    """Adapt one existing numerical field without copying its storage."""

    return ScientificDensityFieldAdapter(
        legacy_field=field,
        numerical_owner=numerical_owner,
        adapter_metadata={} if metadata is None else metadata,
    )


def adapt_scientific_density_fields(
    fields: Sequence[ScientificDensityField3D],
    *,
    source_kind: str,
    numerical_owner: str,
    resource_signature: str,
    metadata: Mapping[str, Any] | None = None,
) -> ScientificDensityFieldBundle:
    """Adapt a deterministic sequence of existing scientific fields."""

    adapters = tuple(
        adapt_scientific_density_field(
            item,
            numerical_owner=numerical_owner,
            metadata={"field_index": index},
        )
        for index, item in enumerate(fields)
    )
    return ScientificDensityFieldBundle(
        fields=adapters,
        source_kind=source_kind,
        resource_signature=resource_signature,
        metadata={} if metadata is None else metadata,
    )


__all__ = [
    "SCIENTIFIC_DENSITY_BUNDLE_SCHEMA",
    "SCIENTIFIC_DENSITY_FACADE_STAGE",
    "SCIENTIFIC_DENSITY_FIELD_ADAPTER_SCHEMA",
    "ScientificDensityCompatibilityError",
    "ScientificDensityError",
    "ScientificDensityField3D",
    "ScientificDensityFieldAdapter",
    "ScientificDensityFieldBundle",
    "ScientificDensityInputError",
    "ScientificPeriodicNodeAccess",
    "adapt_scientific_density_field",
    "adapt_scientific_density_fields",
    "has_scientific_periodic_node_access",
    "is_scientific_density_field",
]
