"""Backend-neutral contracts for periodic scalar-density fields.

This module implements architecture gate LD0-R1.  It deliberately contains no
scientific density estimator and no Plotly dependency.  The dense backend supports the compatibility operator ``legacy_spectral_v1`` and
the canonical operator ``discrete_periodized_v1``. The local-sparse and automatic backends require the canonical discrete operator;
automatic selection is implemented by architecture gate LD4.

The cloud-in-cell assignment used by the current density implementation follows
Hockney and Eastwood, *Computer Simulation Using Particles* (1988).  This module
only defines immutable records, validation, provenance, serialization, and public
field-access protocols around that existing estimator.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Literal, Protocol, TypeAlias, runtime_checkable

import numpy as np
from numpy.typing import NDArray

from .graph_errors import GraphAdapterError, GraphStyleError, GraphUnsupportedFeatureError
from .runtime_resources import RuntimeResourceBudget, resolve_runtime_resource_budget

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

DENSITY_PROVENANCE_SCHEMA = "mdstats.density-source-provenance.v1"
DENSITY_WEIGHTED_SAMPLES_SCHEMA = "mdstats.periodic-weighted-samples.v1"
DENSITY_STORAGE_SUMMARY_SCHEMA = "mdstats.density-storage-summary.v1"
DENSITY_OPTIONS_SCHEMA = "mdstats.density-options.v1"
DENSITY_FIELD_CONTRACT_SCHEMA = "mdstats.scalar-field-contract.v1"

DENSE_BACKEND = "dense"
LOCAL_SPARSE_BACKEND = "local_sparse"
AUTO_BACKEND = "auto"

LEGACY_SPECTRAL_OPERATOR = "legacy_spectral_v1"
DISCRETE_PERIODIZED_OPERATOR = "discrete_periodized_v1"

GAUSSIAN_SIGMA_BROADENING = "gaussian_sigma_v1"
EFFECTIVE_CIC_STENCIL_BROADENING = "effective_cic_stencil_rms_v1"

CanonicalJSONScalar: TypeAlias = str | int | float | bool | None
CanonicalJSONValue: TypeAlias = Any
CanonicalSourceKey: TypeAlias = tuple[CanonicalJSONValue, ...]


def _shape3(value: Any, *, name: str) -> tuple[int, int, int]:
    if len(value) != 3:
        raise GraphStyleError(f"{name} must contain three entries.")
    result: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, np.integer)):
            raise GraphStyleError(f"{name} entries must be positive integers.")
        integer = int(item)
        if integer <= 0:
            raise GraphStyleError(f"{name} entries must be positive integers.")
        result.append(integer)
    return tuple(result)  # type: ignore[return-value]


def _as_python_scalar(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Enum):
        return value.value
    return value


def _freeze_json_value(value: Any, *, path: str = "metadata") -> CanonicalJSONValue:
    value = _as_python_scalar(value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not np.isfinite(value):
            raise GraphAdapterError(f"{path} contains a non-finite float.")
        return float(value)
    if isinstance(value, np.ndarray):
        return tuple(
            _freeze_json_value(item, path=f"{path}[]") for item in value.tolist()
        )
    if isinstance(value, Mapping):
        return FrozenJSONMapping(value, _path=path)
    if isinstance(value, (tuple, list)):
        return tuple(
            _freeze_json_value(item, path=f"{path}[]") for item in value
        )
    raise GraphAdapterError(
        f"{path} contains unsupported non-JSON value {type(value).__name__}."
    )


def _thaw_json_value(value: CanonicalJSONValue) -> Any:
    if isinstance(value, FrozenJSONMapping):
        return value.to_json_dict()
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    return value


class FrozenJSONMapping(Mapping[str, CanonicalJSONValue]):
    """Recursively immutable, canonical, JSON-compatible mapping.

    Keys are stored in lexical order.  Sequences are frozen as tuples and are
    emitted as JSON arrays by :meth:`to_json_dict`.
    """

    __slots__ = ("_data", "_hash")

    def __init__(
        self,
        mapping: Mapping[str, Any] | None = None,
        *,
        _path: str = "metadata",
    ) -> None:
        source = {} if mapping is None else dict(mapping)
        frozen: dict[str, CanonicalJSONValue] = {}
        for key in sorted(source):
            if not isinstance(key, str):
                raise GraphAdapterError(f"{_path} keys must be strings.")
            frozen[key] = _freeze_json_value(source[key], path=f"{_path}.{key}")
        self._data = MappingProxyType(frozen)
        self._hash: int | None = None

    def __getitem__(self, key: str) -> CanonicalJSONValue:
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
        return {key: _thaw_json_value(value) for key, value in self._data.items()}

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_json_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )


def freeze_json_mapping(value: Mapping[str, Any] | FrozenJSONMapping | None) -> FrozenJSONMapping:
    if isinstance(value, FrozenJSONMapping):
        return value
    return FrozenJSONMapping(value)


def canonical_source_key(value: Any) -> CanonicalSourceKey:
    """Return one tagged recursively JSON-compatible source key."""

    if not isinstance(value, (tuple, list)) or not value:
        raise GraphAdapterError("A canonical source key must be a nonempty tuple/list.")
    frozen = tuple(_freeze_json_value(item, path="source_key") for item in value)
    if not isinstance(frozen[0], str) or not frozen[0]:
        raise GraphAdapterError("A canonical source key must begin with a nonempty string tag.")
    return frozen


def _canonical_key_sort_key(value: CanonicalSourceKey) -> str:
    return json.dumps(
        _thaw_json_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _readonly_array(
    value: Any,
    dtype: Any,
    *,
    ndim: int | None = None,
    name: str,
) -> NDArray[Any]:
    array = np.array(value, dtype=dtype, copy=True, order="C")
    if ndim is not None and array.ndim != ndim:
        raise GraphAdapterError(
            f"{name} must be {ndim}-dimensional; received shape {array.shape}."
        )
    if np.issubdtype(array.dtype, np.floating) and np.any(~np.isfinite(array)):
        raise GraphAdapterError(f"{name} must contain only finite values.")
    array.setflags(write=False)
    return array


def _positive_int(value: Any, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be an integer >= {minimum}.")
    result = int(value)
    if result < minimum:
        raise GraphStyleError(f"{name} must be >= {minimum}.")
    return result


@dataclass(frozen=True, slots=True)
class DensitySourceProvenance:
    """Persistent scientific identity of one density source."""

    schema_version: str = DENSITY_PROVENANCE_SCHEMA
    source_kind: str = "unspecified"
    atom_indices: tuple[int, ...] = ()
    vertex_keys: tuple[CanonicalSourceKey, ...] = ()
    edge_keys: tuple[CanonicalSourceKey, ...] = ()
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_PROVENANCE_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported provenance schema {self.schema_version!r}."
            )
        if not isinstance(self.source_kind, str) or not self.source_kind:
            raise GraphAdapterError("source_kind must be a nonempty string.")
        atoms: list[int] = []
        for value in self.atom_indices:
            if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
                raise GraphAdapterError("atom_indices must contain integers.")
            index = int(value)
            if index < 0:
                raise GraphAdapterError("atom_indices must be nonnegative.")
            atoms.append(index)
        vertices = tuple(
            sorted(
                (canonical_source_key(value) for value in self.vertex_keys),
                key=_canonical_key_sort_key,
            )
        )
        edges = tuple(
            sorted(
                (canonical_source_key(value) for value in self.edge_keys),
                key=_canonical_key_sort_key,
            )
        )
        object.__setattr__(self, "atom_indices", tuple(sorted(set(atoms))))
        object.__setattr__(self, "vertex_keys", vertices)
        object.__setattr__(self, "edge_keys", edges)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_kind": self.source_kind,
            "atom_indices": list(self.atom_indices),
            "vertex_keys": [_thaw_json_value(value) for value in self.vertex_keys],
            "edge_keys": [_thaw_json_value(value) for value in self.edge_keys],
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensitySourceProvenance":
        return cls(
            schema_version=str(value["schema_version"]),
            source_kind=str(value["source_kind"]),
            atom_indices=tuple(value.get("atom_indices", ())),
            vertex_keys=tuple(tuple(item) for item in value.get("vertex_keys", ())),
            edge_keys=tuple(tuple(item) for item in value.get("edge_keys", ())),
            metadata=value.get("metadata", {}),
        )


@dataclass(frozen=True, slots=True)
class PeriodicWeightedSamples3D:
    """Backend-neutral registered weighted samples in one periodic display cell."""

    fractional_positions: FloatArray
    weights: FloatArray
    source_provenance: DensitySourceProvenance
    total_measure: float
    measure_kind: Literal["occupancy", "arc_length"]
    measure_units: str
    sample_group_ids: IntArray | None = None
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_WEIGHTED_SAMPLES_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_WEIGHTED_SAMPLES_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported weighted-sample schema {self.schema_version!r}."
            )
        positions = _readonly_array(
            self.fractional_positions,
            np.float64,
            ndim=2,
            name="fractional_positions",
        )
        if positions.shape[1:] != (3,):
            raise GraphAdapterError("fractional_positions must have shape (n_samples, 3).")
        if np.any(positions < 0.0) or np.any(positions >= 1.0):
            raise GraphAdapterError("fractional_positions must be folded to [0, 1).")
        weights = _readonly_array(self.weights, np.float64, ndim=1, name="weights")
        if weights.shape != (positions.shape[0],):
            raise GraphAdapterError("weights must align with fractional_positions.")
        if np.any(weights < 0.0):
            raise GraphAdapterError("weights must be nonnegative.")
        total = float(self.total_measure)
        if not np.isfinite(total) or total <= 0.0:
            raise GraphAdapterError("total_measure must be finite and positive.")
        if not np.isclose(float(np.sum(weights)), total, rtol=5.0e-13, atol=5.0e-13 * max(1.0, total)):
            raise GraphAdapterError("weights must sum to total_measure within tolerance.")
        groups = None
        if self.sample_group_ids is not None:
            groups = _readonly_array(
                self.sample_group_ids,
                np.int64,
                ndim=1,
                name="sample_group_ids",
            )
            if groups.shape != (positions.shape[0],):
                raise GraphAdapterError("sample_group_ids must align with samples.")
            if np.any(groups < 0):
                raise GraphAdapterError("sample_group_ids must be nonnegative.")
        if not isinstance(self.source_provenance, DensitySourceProvenance):
            raise TypeError("source_provenance must be DensitySourceProvenance.")
        if self.measure_kind not in {"occupancy", "arc_length"}:
            raise GraphAdapterError("measure_kind must be 'occupancy' or 'arc_length'.")
        if not isinstance(self.measure_units, str) or not self.measure_units:
            raise GraphAdapterError("measure_units must be a nonempty string.")
        object.__setattr__(self, "fractional_positions", positions)
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "sample_group_ids", groups)
        object.__setattr__(self, "total_measure", total)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "fractional_positions": self.fractional_positions.tolist(),
            "weights": self.weights.tolist(),
            "sample_group_ids": (
                None if self.sample_group_ids is None else self.sample_group_ids.tolist()
            ),
            "source_provenance": self.source_provenance.to_json_dict(),
            "total_measure": self.total_measure,
            "measure_kind": self.measure_kind,
            "measure_units": self.measure_units,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "PeriodicWeightedSamples3D":
        return cls(
            schema_version=str(value["schema_version"]),
            fractional_positions=np.asarray(value["fractional_positions"], dtype=np.float64),
            weights=np.asarray(value["weights"], dtype=np.float64),
            sample_group_ids=(
                None
                if value.get("sample_group_ids") is None
                else np.asarray(value["sample_group_ids"], dtype=np.int64)
            ),
            source_provenance=DensitySourceProvenance.from_json_dict(
                value["source_provenance"]
            ),
            total_measure=float(value["total_measure"]),
            measure_kind=str(value["measure_kind"]),  # type: ignore[arg-type]
            measure_units=str(value["measure_units"]),
            metadata=value.get("metadata", {}),
        )


@dataclass(frozen=True, slots=True)
class DensityStorageSummary:
    """Backend-neutral scalar-storage accounting."""

    storage_backend: str
    logical_grid_shape: tuple[int, int, int]
    logical_node_count: int
    nonzero_node_count: int
    stored_value_count: int
    stored_block_count: int
    estimated_bytes: int
    realized_bytes: int | None
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_STORAGE_SUMMARY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_STORAGE_SUMMARY_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported storage-summary schema {self.schema_version!r}."
            )
        if self.storage_backend not in {DENSE_BACKEND, LOCAL_SPARSE_BACKEND}:
            raise GraphAdapterError("storage_backend must be dense or local_sparse.")
        shape = tuple(
            _positive_int(value, name="logical_grid_shape entry")
            for value in self.logical_grid_shape
        )
        if len(shape) != 3:
            raise GraphAdapterError("logical_grid_shape must contain three entries.")
        counts = {}
        for name in (
            "logical_node_count",
            "nonzero_node_count",
            "stored_value_count",
            "stored_block_count",
            "estimated_bytes",
        ):
            counts[name] = _positive_int(getattr(self, name), name=name, minimum=0)
        realized = self.realized_bytes
        if realized is not None:
            realized = _positive_int(realized, name="realized_bytes", minimum=0)
        expected = int(np.prod(shape, dtype=object))
        if counts["logical_node_count"] != expected:
            raise GraphAdapterError("logical_node_count does not match logical_grid_shape.")
        if counts["nonzero_node_count"] > counts["stored_value_count"]:
            raise GraphAdapterError("nonzero_node_count cannot exceed stored_value_count.")
        object.__setattr__(self, "logical_grid_shape", shape)
        for name, result in counts.items():
            object.__setattr__(self, name, result)
        object.__setattr__(self, "realized_bytes", realized)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "storage_backend": self.storage_backend,
            "logical_grid_shape": list(self.logical_grid_shape),
            "logical_node_count": self.logical_node_count,
            "nonzero_node_count": self.nonzero_node_count,
            "stored_value_count": self.stored_value_count,
            "stored_block_count": self.stored_block_count,
            "estimated_bytes": self.estimated_bytes,
            "realized_bytes": self.realized_bytes,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityStorageSummary":
        return cls(
            schema_version=str(value["schema_version"]),
            storage_backend=str(value["storage_backend"]),
            logical_grid_shape=tuple(value["logical_grid_shape"]),
            logical_node_count=int(value["logical_node_count"]),
            nonzero_node_count=int(value["nonzero_node_count"]),
            stored_value_count=int(value["stored_value_count"]),
            stored_block_count=int(value["stored_block_count"]),
            estimated_bytes=int(value["estimated_bytes"]),
            realized_bytes=(
                None if value.get("realized_bytes") is None else int(value["realized_bytes"])
            ),
            metadata=value.get("metadata", {}),
        )


@dataclass(frozen=True, slots=True)
class DensityResolutionOptions:
    """Shared grid, bandwidth, and adaptive-resolution policy."""

    grid_shape: tuple[int, int, int] | None = None
    grid_interval: float = 0.20
    gaussian_bandwidth: float | None = None
    gaussian_to_grid_ratio: float = 2.0
    adaptive_smearing: bool = True
    max_smearing_to_sample_sd_ratio: float = 0.50
    sample_sd_quantile: float = 0.10
    spread_sample_size: int = 128
    spread_sample_seed: int = 0
    spread_sampling_strategy: Literal["all", "stratified_random"] = (
        "stratified_random"
    )
    spread_replicate_count: int = 4
    spread_max_replicate_count: int = 8
    spread_convergence_relative_tolerance: float = 0.01
    spread_basin_mode: Literal["auto", "global"] = "auto"
    broadening_metric: str = GAUSSIAN_SIGMA_BROADENING
    schema_version: str = DENSITY_OPTIONS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_OPTIONS_SCHEMA:
            raise GraphAdapterError(f"Unsupported density-options schema {self.schema_version!r}.")
        shape = self.grid_shape
        if shape is not None:
            if len(shape) != 3:
                raise GraphStyleError("grid_shape must contain three integers or be None.")
            shape = tuple(
                _positive_int(value, name="grid_shape entry", minimum=4)
                for value in shape
            )
        interval = float(self.grid_interval)
        bandwidth = self.gaussian_bandwidth
        if not np.isfinite(interval) or interval <= 0.0:
            raise GraphStyleError("grid_interval must be finite and positive.")
        if bandwidth is not None:
            bandwidth = float(bandwidth)
            if not np.isfinite(bandwidth) or bandwidth < 0.0:
                raise GraphStyleError("gaussian_bandwidth must be finite and nonnegative or None.")
        ratio = float(self.gaussian_to_grid_ratio)
        sd_ratio = float(self.max_smearing_to_sample_sd_ratio)
        quantile = float(self.sample_sd_quantile)
        if not np.isfinite(ratio) or ratio <= 0.0:
            raise GraphStyleError("gaussian_to_grid_ratio must be finite and positive.")
        if not np.isfinite(sd_ratio) or sd_ratio <= 0.0:
            raise GraphStyleError("max_smearing_to_sample_sd_ratio must be finite and positive.")
        if not np.isfinite(quantile) or not 0.0 <= quantile <= 1.0:
            raise GraphStyleError("sample_sd_quantile must lie in [0, 1].")
        sample_size = _positive_int(
            self.spread_sample_size, name="spread_sample_size", minimum=2
        )
        if isinstance(self.spread_sample_seed, bool) or not isinstance(
            self.spread_sample_seed, (int, np.integer)
        ):
            raise GraphStyleError("spread_sample_seed must be an integer.")
        sample_seed = int(self.spread_sample_seed)
        if self.spread_sampling_strategy not in {"all", "stratified_random"}:
            raise GraphStyleError(
                "spread_sampling_strategy must be all or stratified_random."
            )
        replicate_count = _positive_int(
            self.spread_replicate_count, name="spread_replicate_count", minimum=1
        )
        max_replicates = _positive_int(
            self.spread_max_replicate_count, name="spread_max_replicate_count", minimum=1
        )
        if max_replicates < replicate_count:
            raise GraphStyleError(
                "spread_max_replicate_count cannot be smaller than spread_replicate_count."
            )
        convergence_tolerance = float(self.spread_convergence_relative_tolerance)
        if not np.isfinite(convergence_tolerance) or convergence_tolerance <= 0.0:
            raise GraphStyleError(
                "spread_convergence_relative_tolerance must be finite and positive."
            )
        if self.spread_basin_mode not in {"auto", "global"}:
            raise GraphStyleError("spread_basin_mode must be auto or global.")
        if self.broadening_metric not in {
            GAUSSIAN_SIGMA_BROADENING,
            EFFECTIVE_CIC_STENCIL_BROADENING,
        }:
            raise GraphStyleError("Unknown broadening_metric.")
        object.__setattr__(self, "grid_shape", shape)
        object.__setattr__(self, "grid_interval", interval)
        object.__setattr__(self, "gaussian_bandwidth", bandwidth)
        object.__setattr__(self, "gaussian_to_grid_ratio", ratio)
        object.__setattr__(self, "adaptive_smearing", bool(self.adaptive_smearing))
        object.__setattr__(self, "max_smearing_to_sample_sd_ratio", sd_ratio)
        object.__setattr__(self, "sample_sd_quantile", quantile)
        object.__setattr__(self, "spread_sample_size", sample_size)
        object.__setattr__(self, "spread_sample_seed", sample_seed)
        object.__setattr__(self, "spread_replicate_count", replicate_count)
        object.__setattr__(self, "spread_max_replicate_count", max_replicates)
        object.__setattr__(
            self, "spread_convergence_relative_tolerance", convergence_tolerance
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "grid_shape": None if self.grid_shape is None else list(self.grid_shape),
            "grid_interval": self.grid_interval,
            "gaussian_bandwidth": self.gaussian_bandwidth,
            "gaussian_to_grid_ratio": self.gaussian_to_grid_ratio,
            "adaptive_smearing": self.adaptive_smearing,
            "max_smearing_to_sample_sd_ratio": self.max_smearing_to_sample_sd_ratio,
            "sample_sd_quantile": self.sample_sd_quantile,
            "spread_sample_size": self.spread_sample_size,
            "spread_sample_seed": self.spread_sample_seed,
            "spread_sampling_strategy": self.spread_sampling_strategy,
            "spread_replicate_count": self.spread_replicate_count,
            "spread_max_replicate_count": self.spread_max_replicate_count,
            "spread_convergence_relative_tolerance": self.spread_convergence_relative_tolerance,
            "spread_basin_mode": self.spread_basin_mode,
            "broadening_metric": self.broadening_metric,
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityResolutionOptions":
        return cls(
            schema_version=str(value["schema_version"]),
            grid_shape=None if value.get("grid_shape") is None else tuple(value["grid_shape"]),
            grid_interval=float(value["grid_interval"]),
            gaussian_bandwidth=(None if value.get("gaussian_bandwidth") is None else float(value["gaussian_bandwidth"])),
            gaussian_to_grid_ratio=float(value["gaussian_to_grid_ratio"]),
            adaptive_smearing=bool(value["adaptive_smearing"]),
            max_smearing_to_sample_sd_ratio=float(value["max_smearing_to_sample_sd_ratio"]),
            sample_sd_quantile=float(value["sample_sd_quantile"]),
            spread_sample_size=int(value.get("spread_sample_size", 128)),
            spread_sample_seed=int(value.get("spread_sample_seed", 0)),
            spread_sampling_strategy=str(
                value.get("spread_sampling_strategy", "stratified_random")
            ),  # type: ignore[arg-type]
            spread_replicate_count=int(value.get("spread_replicate_count", 4)),
            spread_max_replicate_count=int(value.get("spread_max_replicate_count", 8)),
            spread_convergence_relative_tolerance=float(
                value.get("spread_convergence_relative_tolerance", 0.01)
            ),
            spread_basin_mode=str(value.get("spread_basin_mode", "auto")),  # type: ignore[arg-type]
            broadening_metric=str(value["broadening_metric"]),
        )


@dataclass(frozen=True, slots=True)
class DensityKernelOptions:
    """Shared smoothing-operator policy.

    The canonical finite-support periodized Gaussian is the production default.
    ``legacy_spectral_v1`` remains available as an explicit dense-only
    compatibility choice.
    """

    smoothing_operator: str = DISCRETE_PERIODIZED_OPERATOR
    kernel_tail_tolerance: float = 1.0e-8
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_OPTIONS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_OPTIONS_SCHEMA:
            raise GraphAdapterError(f"Unsupported density-options schema {self.schema_version!r}.")
        if self.smoothing_operator not in {
            LEGACY_SPECTRAL_OPERATOR,
            DISCRETE_PERIODIZED_OPERATOR,
        }:
            raise GraphStyleError("Unknown smoothing_operator.")
        tolerance = float(self.kernel_tail_tolerance)
        if not np.isfinite(tolerance) or not 1.0e-15 <= tolerance <= 1.0e-3:
            raise GraphStyleError("kernel_tail_tolerance must lie in [1e-15, 1e-3].")
        object.__setattr__(self, "kernel_tail_tolerance", tolerance)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "smoothing_operator": self.smoothing_operator,
            "kernel_tail_tolerance": self.kernel_tail_tolerance,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityKernelOptions":
        return cls(
            schema_version=str(value["schema_version"]),
            smoothing_operator=str(value["smoothing_operator"]),
            kernel_tail_tolerance=float(value["kernel_tail_tolerance"]),
            metadata=value.get("metadata", {}),
        )


@dataclass(frozen=True, slots=True)
class DensityStorageOptions:
    """Shared dense/sparse storage-selection policy.

    Automatic selection is the production default. It resolves the requested
    scientific grid and Gaussian width first, estimates dense and local-sparse
    realizations at that identical resolution, and then chooses a feasible
    backend transactionally. Explicit ``dense`` and ``local_sparse`` values
    remain expert/reproducibility overrides.
    """

    grid_backend: Literal["dense", "local_sparse", "auto"] = AUTO_BACKEND
    local_block_shape: tuple[int, int, int] = (16, 16, 16)
    sparse_activation_fraction: float = 0.20
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_OPTIONS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_OPTIONS_SCHEMA:
            raise GraphAdapterError(f"Unsupported density-options schema {self.schema_version!r}.")
        if self.grid_backend not in {DENSE_BACKEND, LOCAL_SPARSE_BACKEND, AUTO_BACKEND}:
            raise GraphStyleError("grid_backend must be dense, local_sparse, or auto.")
        if len(self.local_block_shape) != 3:
            raise GraphStyleError("local_block_shape must contain three integers.")
        shape = tuple(
            _positive_int(value, name="local_block_shape entry")
            for value in self.local_block_shape
        )
        fraction = float(self.sparse_activation_fraction)
        if not np.isfinite(fraction) or not 0.0 < fraction < 1.0:
            raise GraphStyleError("sparse_activation_fraction must lie in (0, 1).")
        object.__setattr__(self, "local_block_shape", shape)
        object.__setattr__(self, "sparse_activation_fraction", fraction)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "grid_backend": self.grid_backend,
            "local_block_shape": list(self.local_block_shape),
            "sparse_activation_fraction": self.sparse_activation_fraction,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityStorageOptions":
        return cls(
            schema_version=str(value["schema_version"]),
            grid_backend=str(value["grid_backend"]),  # type: ignore[arg-type]
            local_block_shape=tuple(value["local_block_shape"]),
            sparse_activation_fraction=float(value["sparse_activation_fraction"]),
            metadata=value.get("metadata", {}),
        )


@dataclass(frozen=True, slots=True)
class DensityOptimizationOptions:
    """Performance-only policy for the certified sparse density path.

    Resource-sensitive fields remain unresolved as ``None`` until a complete
    scene budget is known.  :meth:`resolve` then binds them to the same primary
    memory/thread/wall policy used by planning.  This avoids snapshot drift and
    prevents an option object created before ``FrameworkDynamicsResources``
    from silently requesting more workers than the scene permits.
    """

    sparse_evaluation_mode: Literal["optimized", "reference"] = "optimized"
    cache_stencil_supports: bool = True
    sparse_pair_chunk_size: int | None = None
    sparse_group_batch_size: int = 8
    sparse_realization_mode: Literal["hybrid", "ld7"] = "hybrid"
    allow_ld7_fallback: bool = True
    hybrid_compute_tile_shape: tuple[int, int, int] = (32, 32, 32)
    hybrid_min_fft_source_nodes: int = 32
    hybrid_fft_workers: int | None = None
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_OPTIONS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_OPTIONS_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported density-options schema {self.schema_version!r}."
            )
        if self.sparse_evaluation_mode not in {"optimized", "reference"}:
            raise GraphStyleError(
                "sparse_evaluation_mode must be optimized or reference."
            )
        if self.sparse_pair_chunk_size is not None:
            object.__setattr__(
                self,
                "sparse_pair_chunk_size",
                _positive_int(
                    self.sparse_pair_chunk_size, name="sparse_pair_chunk_size"
                ),
            )
        object.__setattr__(
            self,
            "sparse_group_batch_size",
            _positive_int(
                self.sparse_group_batch_size, name="sparse_group_batch_size"
            ),
        )
        if self.sparse_realization_mode not in {"hybrid", "ld7"}:
            raise GraphStyleError("sparse_realization_mode must be hybrid or ld7.")
        object.__setattr__(
            self,
            "hybrid_compute_tile_shape",
            _shape3(self.hybrid_compute_tile_shape, name="hybrid_compute_tile_shape"),
        )
        object.__setattr__(
            self,
            "hybrid_min_fft_source_nodes",
            _positive_int(
                self.hybrid_min_fft_source_nodes,
                name="hybrid_min_fft_source_nodes",
            ),
        )
        if self.hybrid_fft_workers is not None:
            object.__setattr__(
                self,
                "hybrid_fft_workers",
                _positive_int(self.hybrid_fft_workers, name="hybrid_fft_workers"),
            )
        object.__setattr__(
            self, "cache_stencil_supports", bool(self.cache_stencil_supports)
        )
        object.__setattr__(self, "allow_ld7_fallback", bool(self.allow_ld7_fallback))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def resource_resolved(self) -> bool:
        return (
            self.sparse_pair_chunk_size is not None
            and self.hybrid_fft_workers is not None
        )

    def resolve(
        self,
        *,
        max_memory_bytes: int | str | None = None,
        max_threads: int | None = None,
        max_wall_time_seconds: float | None = None,
        runtime_budget: RuntimeResourceBudget | None = None,
    ) -> "DensityOptimizationOptions":
        """Bind batching and FFT workers to one authoritative runtime budget."""

        if runtime_budget is not None:
            if not isinstance(runtime_budget, RuntimeResourceBudget):
                raise TypeError("runtime_budget must be RuntimeResourceBudget or None.")
            budget = runtime_budget
        else:
            budget = resolve_runtime_resource_budget(
                max_memory_bytes=max_memory_bytes,
                max_threads=max_threads,
                max_wall_time_seconds=max_wall_time_seconds,
            )
        default_chunk = max(
            4_096,
            min(
                1_048_576,
                budget.max_memory_bytes
                // max(128, 128 * budget.max_threads),
            ),
        )
        requested_chunk = self.sparse_pair_chunk_size
        chunk = (
            default_chunk
            if requested_chunk is None
            else min(default_chunk, requested_chunk)
        )
        requested_workers = self.hybrid_fft_workers
        workers = (
            budget.max_threads
            if requested_workers is None
            else min(budget.max_threads, requested_workers)
        )
        metadata = self.metadata.to_json_dict()
        metadata.update(
            {
                "resource_policy": "runtime_derived_v2",
                "sparse_pair_chunk_source": (
                    "runtime_memory_per_thread"
                    if requested_chunk is None
                    else (
                        "explicit_clamped_to_runtime"
                        if requested_chunk > default_chunk
                        else "explicit"
                    )
                ),
                "hybrid_fft_workers_source": (
                    "runtime_thread_budget"
                    if requested_workers is None
                    else (
                        "explicit_clamped_to_runtime"
                        if requested_workers > budget.max_threads
                        else "explicit"
                    )
                ),
                "runtime_max_memory_bytes": budget.max_memory_bytes,
                "runtime_max_threads": budget.max_threads,
                "runtime_max_wall_time_seconds": budget.max_wall_time_seconds,
            }
        )
        return DensityOptimizationOptions(
            sparse_evaluation_mode=self.sparse_evaluation_mode,
            cache_stencil_supports=self.cache_stencil_supports,
            sparse_pair_chunk_size=chunk,
            sparse_group_batch_size=self.sparse_group_batch_size,
            sparse_realization_mode=self.sparse_realization_mode,
            allow_ld7_fallback=self.allow_ld7_fallback,
            hybrid_compute_tile_shape=self.hybrid_compute_tile_shape,
            hybrid_min_fft_source_nodes=self.hybrid_min_fft_source_nodes,
            hybrid_fft_workers=workers,
            metadata=metadata,
            schema_version=self.schema_version,
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "sparse_evaluation_mode": self.sparse_evaluation_mode,
            "cache_stencil_supports": self.cache_stencil_supports,
            "sparse_pair_chunk_size": self.sparse_pair_chunk_size,
            "sparse_group_batch_size": self.sparse_group_batch_size,
            "sparse_realization_mode": self.sparse_realization_mode,
            "allow_ld7_fallback": self.allow_ld7_fallback,
            "hybrid_compute_tile_shape": list(self.hybrid_compute_tile_shape),
            "hybrid_min_fft_source_nodes": self.hybrid_min_fft_source_nodes,
            "hybrid_fft_workers": self.hybrid_fft_workers,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityOptimizationOptions":
        return cls(
            schema_version=str(value["schema_version"]),
            sparse_evaluation_mode=str(value["sparse_evaluation_mode"]),  # type: ignore[arg-type]
            cache_stencil_supports=bool(value["cache_stencil_supports"]),
            sparse_pair_chunk_size=(
                None
                if value.get("sparse_pair_chunk_size") is None
                else int(value["sparse_pair_chunk_size"])
            ),
            sparse_group_batch_size=int(value.get("sparse_group_batch_size", 8)),
            sparse_realization_mode=str(value.get("sparse_realization_mode", "hybrid")),  # type: ignore[arg-type]
            allow_ld7_fallback=bool(value.get("allow_ld7_fallback", True)),
            hybrid_compute_tile_shape=tuple(value.get("hybrid_compute_tile_shape", (32, 32, 32))),
            hybrid_min_fft_source_nodes=int(value.get("hybrid_min_fft_source_nodes", 32)),
            hybrid_fft_workers=(
                None
                if value.get("hybrid_fft_workers") is None
                else int(value["hybrid_fft_workers"])
            ),
            metadata=value.get("metadata", {}),
        )


@dataclass(frozen=True, slots=True)
class DensityRenderOptions:
    """Shared shell, cloud, replication, and standalone mesh policy.

    ``standalone_final_mesh_faces`` is the hard terminal limit used only when a
    density mesh is prepared outside a scene fitting controller.  The legacy
    constructor/attribute name ``max_mesh_faces`` remains as a deprecated alias
    for one migration cycle.  Scene-wide visual targets are allocated
    separately and must not be interpreted as extraction safety limits.
    """

    mass_fractions: tuple[float, ...] = (0.50, 0.80, 0.95)
    render_mode: Literal["mesh", "voxel_cloud"] = "mesh"
    display_replication: Literal["canonical", "match_graph"] = "canonical"
    standalone_final_mesh_faces: int = 250_000
    max_mesh_faces: int | None = None
    cloud_max_points: int = 40_000
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_OPTIONS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_OPTIONS_SCHEMA:
            raise GraphAdapterError(f"Unsupported density-options schema {self.schema_version!r}.")
        fractions = tuple(float(value) for value in self.mass_fractions)
        if len(fractions) < 2 or any(
            not np.isfinite(value) or not 0.0 < value < 1.0 for value in fractions
        ):
            raise GraphStyleError(
                "mass_fractions must contain at least two values strictly between zero and one."
            )
        if tuple(sorted(set(fractions))) != fractions:
            raise GraphStyleError("mass_fractions must be strictly increasing.")
        if self.render_mode not in {"mesh", "voxel_cloud"}:
            raise GraphStyleError("render_mode must be mesh or voxel_cloud.")
        if self.display_replication not in {"canonical", "match_graph"}:
            raise GraphStyleError("display_replication must be canonical or match_graph.")
        standalone = _positive_int(
            self.standalone_final_mesh_faces,
            name="standalone_final_mesh_faces",
        )
        legacy = self.max_mesh_faces
        if legacy is not None:
            legacy_value = _positive_int(legacy, name="max_mesh_faces")
            if self.standalone_final_mesh_faces != 250_000 and standalone != legacy_value:
                raise GraphStyleError(
                    "standalone_final_mesh_faces and deprecated max_mesh_faces disagree."
                )
            standalone = legacy_value
        object.__setattr__(self, "mass_fractions", fractions)
        object.__setattr__(self, "standalone_final_mesh_faces", standalone)
        # Preserve read compatibility while all internal code uses the explicit name.
        object.__setattr__(self, "max_mesh_faces", standalone)
        object.__setattr__(
            self,
            "cloud_max_points",
            _positive_int(self.cloud_max_points, name="cloud_max_points"),
        )
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "mass_fractions": list(self.mass_fractions),
            "render_mode": self.render_mode,
            "display_replication": self.display_replication,
            "standalone_final_mesh_faces": self.standalone_final_mesh_faces,
            # Compatibility key for 0.19.74a0 and earlier readers.
            "max_mesh_faces": self.standalone_final_mesh_faces,
            "cloud_max_points": self.cloud_max_points,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityRenderOptions":
        standalone = value.get("standalone_final_mesh_faces")
        if standalone is None:
            standalone = value["max_mesh_faces"]
        return cls(
            schema_version=str(value["schema_version"]),
            mass_fractions=tuple(value["mass_fractions"]),
            render_mode=str(value["render_mode"]),  # type: ignore[arg-type]
            display_replication=str(value["display_replication"]),  # type: ignore[arg-type]
            standalone_final_mesh_faces=int(standalone),
            max_mesh_faces=None,
            cloud_max_points=int(value["cloud_max_points"]),
            metadata=value.get("metadata", {}),
        )


def validate_density_implementation_selection(
    *,
    resolution: DensityResolutionOptions,
    kernel: DensityKernelOptions,
    storage: DensityStorageOptions,
) -> None:
    """Reject identifiers whose owning architecture gate is not implemented."""

    if (
        resolution.broadening_metric == EFFECTIVE_CIC_STENCIL_BROADENING
        and kernel.smoothing_operator != DISCRETE_PERIODIZED_OPERATOR
    ):
        raise GraphUnsupportedFeatureError(
            "effective_cic_stencil_rms_v1 requires "
            "smoothing_operator='discrete_periodized_v1'."
        )
    if (
        storage.grid_backend in {LOCAL_SPARSE_BACKEND, AUTO_BACKEND}
        and kernel.smoothing_operator != DISCRETE_PERIODIZED_OPERATOR
    ):
        raise GraphUnsupportedFeatureError(
            "grid_backend='local_sparse' or 'auto' requires "
            "smoothing_operator='discrete_periodized_v1'."
        )


@runtime_checkable
class ScalarField3D(Protocol):
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
    source_provenance: DensitySourceProvenance
    metadata: FrozenJSONMapping

    @property
    def grid_shape(self) -> tuple[int, int, int]: ...

    @property
    def voxel_volume(self) -> float: ...

    @property
    def integral(self) -> float: ...

    def hdr_details(self, q: float) -> Any: ...

    def threshold_for_mass_fraction(self, q: float) -> float: ...

    def storage_summary(self) -> DensityStorageSummary: ...


@runtime_checkable
class PeriodicNodeFieldAccess(Protocol):
    def iter_stored_nodes(
        self,
        *,
        batch_size: int | None = None,
    ) -> Iterator[tuple[IntArray, FloatArray]]: ...

    def gather_node_values(self, logical_indices: IntArray) -> FloatArray: ...


def is_scalar_field3d(value: Any) -> bool:
    return isinstance(value, ScalarField3D)


def is_periodic_node_field_access(value: Any) -> bool:
    return isinstance(value, PeriodicNodeFieldAccess)


@dataclass(frozen=True, slots=True)
class DensePeriodicNodeFieldAdapter:
    """Zero-copy public adapter around an existing dense field."""

    field: ScalarField3D
    node_access: PeriodicNodeFieldAccess
    values: FloatArray

    @classmethod
    def from_field(cls, field: Any) -> "DensePeriodicNodeFieldAdapter":
        if not is_scalar_field3d(field) or not is_periodic_node_field_access(field):
            raise TypeError("field must satisfy ScalarField3D and PeriodicNodeFieldAccess.")
        values = getattr(field, "values", None)
        if not isinstance(values, np.ndarray) or values.dtype != np.float64 or values.ndim != 3:
            raise TypeError("The dense adapter requires a public float64 3-D values array.")
        if values.flags.writeable:
            raise GraphAdapterError("Dense field values must be read-only.")
        return cls(field=field, node_access=field, values=values)

    def __post_init__(self) -> None:
        if self.values is not getattr(self.field, "values", None):
            raise GraphAdapterError("DensePeriodicNodeFieldAdapter must not copy values.")
