"""Stage-11E2 deterministic density attractors and supported periodic basins.

The canonical backend operates on the complete periodic logical-node complex of a
Stage-11E1 density estimate. Unsupported nodes remain unknown. Deterministic
steepest-ascent ownership, plateau components, derivative-supported one-
dimensional ridges, supported saddles, provisional cores, bandwidth lineage,
and refinement certificates are retained as distinct immutable products.

Mean-shift mode seeking, nonparametric density ridges, discrete cell-complex
Morse bookkeeping, HDBSCAN, and k-means are external background methods. The
support propagation, deterministic ordering, torus ownership, core fallback,
and source-binding contracts in this module are mdstats-specific constructions.
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum, IntEnum
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import linear_sum_assignment

from .species import (
    AnalysisGeometryMetric,
    PeriodicSpeciesDensityEstimate,
    PeriodicSpeciesDensityLadder,
)

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]

DENSITY_ATTRACTOR_STAGE = "11E2"
DENSITY_ATTRACTOR_OPTIONS_SCHEMA = "mdstats.density-attractor-options.v1"
DENSITY_ATTRACTOR_SCHEMA = "mdstats.density-attractor.v1"
ATTRACTOR_LOCAL_CHART_SCHEMA = "mdstats.attractor-local-chart.v1"
SUPPORTED_PERIODIC_CELL_COMPLEX_SCHEMA = "mdstats.supported-periodic-cell-complex.v1"
SUPPORTED_SADDLE_SCHEMA = "mdstats.supported-saddle.v1"
PROVISIONAL_CORE_SCHEMA = "mdstats.provisional-core.v1"
TOPOLOGY_STABILITY_CERTIFICATE_SCHEMA = "mdstats.topology-stability-certificate.v1"
DENSITY_ATTRACTOR_CATALOG_SCHEMA = "mdstats.density-attractor-catalog.v1"
ATTRACTOR_CORRESPONDENCE_SCHEMA = "mdstats.attractor-correspondence.v1"
DENSITY_ATTRACTOR_LINEAGE_SCHEMA = "mdstats.density-attractor-lineage.v1"
SELECTION_VALIDATION_PROTOCOL_SCHEMA = "mdstats.selection-validation-protocol.v1"
SCALE_CONSENSUS_SCHEMA = "mdstats.scale-consensus.v1"
DENSITY_REFINEMENT_SERIES_SCHEMA = "mdstats.density-attractor-refinement-series.v1"
CLUSTER_COMPARISON_SCHEMA = "mdstats.periodic-cluster-comparison.v1"


class DensityAttractorError(ValueError):
    """Base Stage-11E2 error."""


class DensityAttractorInputError(DensityAttractorError):
    """Raised when a density field or option contract is inconsistent."""


class DensityAttractorResourceError(DensityAttractorError):
    """Raised transactionally before topology work exceeds declared limits."""


class DensityAttractorSerializationError(DensityAttractorError):
    """Raised when serialized Stage-11E2 data are malformed or tampered with."""


class AttractorGeometry(str, Enum):
    ISOLATED_MODE = "isolated_mode"
    RIDGE_OR_MANIFOLD = "ridge_or_manifold"
    FLAT_UNRESOLVED_COMPONENT = "flat_unresolved_component"


class CellClassification(IntEnum):
    UNSUPPORTED_UNKNOWN = 0
    SUPPORTED_BASIN = 1
    SUPPORTED_TRANSITION_REGION = 2
    SUPPORTED_BACKGROUND = 3
    NUMERICALLY_UNRESOLVED = 4


class CoreDepthSource(str, Enum):
    INTERBASIN_SADDLE_DEPTH = "interbasin_saddle_depth"
    SUPPORTED_BOUNDARY_DEPTH = "supported_boundary_depth"
    PROBABILITY_CONTENT_CORE = "probability_content_core"
    CORE_UNRESOLVED = "core_unresolved"


class TopologyStabilityStatus(str, Enum):
    UNASSESSED = "unassessed"
    STABLE = "stable"
    UNSTABLE = "unstable"
    UNRESOLVED = "unresolved"


class ScaleDecisionStatus(str, Enum):
    RESOLVED = "resolved"
    SCALE_AMBIGUOUS = "scale_ambiguous"
    UNRESOLVED = "unresolved"


class ClusterComparisonStatus(str, Enum):
    AVAILABLE = "available"
    OPTIONAL_DEPENDENCY_UNAVAILABLE = "optional_dependency_unavailable"
    UNSUPPORTED_WEIGHTS = "unsupported_weights"
    FAILED = "failed"


class LocalChartKind(str, Enum):
    ISOLATED_MODE = "isolated_mode_chart"
    ANNULAR = "annular_chart"
    MANIFOLD_UNRESOLVED = "manifold_chart_unresolved"


NeighborConnectivity = Literal[6, 18, 26]


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _array_digest(value: np.ndarray) -> str:
    arr = np.ascontiguousarray(value)
    h = hashlib.sha256()
    h.update(arr.dtype.str.encode("ascii"))
    h.update(str(arr.shape).encode("ascii"))
    h.update(arr.tobytes(order="C"))
    return h.hexdigest()


def _sha(value: str, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise DensityAttractorInputError(f"{name} must be a SHA-256 digest.")
    return value


def _readonly(value: Any, *, dtype: Any, ndim: int, name: str, shape: tuple[int, ...] | None = None) -> np.ndarray:
    arr = np.array(value, dtype=dtype, copy=True, order="C")
    if arr.ndim != ndim:
        raise DensityAttractorInputError(f"{name} must have ndim={ndim}; received {arr.shape}.")
    if shape is not None and arr.shape != shape:
        raise DensityAttractorInputError(f"{name} must have shape {shape}; received {arr.shape}.")
    if np.issubdtype(arr.dtype, np.floating) and np.any(~np.isfinite(arr)):
        raise DensityAttractorInputError(f"{name} contains non-finite values.")
    arr.setflags(write=False)
    return arr


def _freeze(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        result = float(value)
        if not np.isfinite(result):
            raise DensityAttractorInputError("Metadata contains a non-finite float.")
        return result
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(v) for v in value)
    raise DensityAttractorInputError(f"Unsupported metadata value {type(value).__name__}.")


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in sorted(value.items())}
    if isinstance(value, tuple):
        return [_json_value(v) for v in value]
    if isinstance(value, np.generic):
        return _json_value(value.item())
    return value


def _positive(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise DensityAttractorInputError(f"{name} must be finite and positive.")
    return result


def _nonnegative(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise DensityAttractorInputError(f"{name} must be finite and nonnegative.")
    return result


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or int(value) <= 0:
        raise DensityAttractorInputError(f"{name} must be a positive integer.")
    return int(value)


def _neighbor_offsets(connectivity: NeighborConnectivity) -> tuple[tuple[int, int, int], ...]:
    offsets: list[tuple[int, int, int]] = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                if dx == dy == dz == 0:
                    continue
                manhattan = abs(dx) + abs(dy) + abs(dz)
                if connectivity == 6 and manhattan != 1:
                    continue
                if connectivity == 18 and manhattan > 2:
                    continue
                offsets.append((dx, dy, dz))
    return tuple(sorted(offsets))


def _flat(index: tuple[int, int, int], shape: tuple[int, int, int]) -> int:
    return int(np.ravel_multi_index(index, shape))


def _unflat(index: int, shape: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(int(v) for v in np.unravel_index(index, shape))


def _wrapped_neighbor(index: tuple[int, int, int], offset: tuple[int, int, int], shape: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple((index[i] + offset[i]) % shape[i] for i in range(3))


def _periodic_delta(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    delta = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    return delta - np.rint(delta)


def _metric_distance(a: np.ndarray, b: np.ndarray, metric: AnalysisGeometryMetric) -> float:
    delta = _periodic_delta(a, b)
    return float(math.sqrt(max(0.0, float(delta @ metric.covariant @ delta))))


def _circular_mean(points: np.ndarray, weights: np.ndarray | None = None) -> np.ndarray:
    pts = np.mod(np.asarray(points, dtype=np.float64), 1.0)
    if weights is None:
        weights = np.ones(pts.shape[0], dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    angles = 2.0 * math.pi * pts
    sin_mean = np.sum(weights[:, None] * np.sin(angles), axis=0)
    cos_mean = np.sum(weights[:, None] * np.cos(angles), axis=0)
    result = np.mod(np.arctan2(sin_mean, cos_mean) / (2.0 * math.pi), 1.0)
    return np.asarray(result, dtype=np.float64)


def _component_nodes(mask: np.ndarray, offsets: tuple[tuple[int, int, int], ...]) -> list[np.ndarray]:
    shape = tuple(int(v) for v in mask.shape)
    seen = np.zeros(shape, dtype=bool)
    components: list[np.ndarray] = []
    for start_arr in np.argwhere(mask):
        start = tuple(int(v) for v in start_arr)
        if seen[start]:
            continue
        queue = deque([start])
        seen[start] = True
        nodes: list[int] = []
        while queue:
            current = queue.popleft()
            nodes.append(_flat(current, shape))
            for offset in offsets:
                nxt = _wrapped_neighbor(current, offset, shape)
                if mask[nxt] and not seen[nxt]:
                    seen[nxt] = True
                    queue.append(nxt)
        components.append(np.asarray(sorted(nodes), dtype=np.int64))
    return components


def _component_has_cycle(nodes: np.ndarray, shape: tuple[int, int, int], offsets6: tuple[tuple[int, int, int], ...]) -> bool:
    node_set = {int(v) for v in nodes}
    edges = 0
    for flat_index in node_set:
        index = _unflat(flat_index, shape)
        for offset in offsets6:
            neighbor = _flat(_wrapped_neighbor(index, offset, shape), shape)
            if neighbor in node_set:
                edges += 1
    edges //= 2
    return edges >= len(node_set)


@dataclass(frozen=True, slots=True)
class DensityAttractorOptions:
    neighbor_connectivity: NeighborConnectivity = 26
    plateau_relative_tolerance: float = 1.0e-10
    background_density_fraction: float = 1.0e-8
    minimum_point_curvature: float = 0.0
    ridge_density_fraction: float = 0.15
    ridge_normal_score_tolerance: float = 0.75
    ridge_minimum_normal_curvature: float = 0.0
    ridge_tangential_curvature_ratio: float = 0.35
    minimum_ridge_nodes: int = 8
    core_depth_fraction: float = 0.5
    core_probability_content: float = 0.5
    transition_boundary_layers: int = 1
    max_ascent_steps: int = 1_000_000
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        connectivity = int(self.neighbor_connectivity)
        if connectivity not in {6, 18, 26}:
            raise DensityAttractorInputError("neighbor_connectivity must be 6, 18, or 26.")
        plateau = _nonnegative(self.plateau_relative_tolerance, "plateau_relative_tolerance")
        background = _nonnegative(self.background_density_fraction, "background_density_fraction")
        if background >= 1.0:
            raise DensityAttractorInputError("background_density_fraction must be smaller than one.")
        point_curvature = _nonnegative(self.minimum_point_curvature, "minimum_point_curvature")
        ridge_fraction = _nonnegative(self.ridge_density_fraction, "ridge_density_fraction")
        if ridge_fraction > 1.0:
            raise DensityAttractorInputError("ridge_density_fraction must not exceed one.")
        ridge_score = _nonnegative(self.ridge_normal_score_tolerance, "ridge_normal_score_tolerance")
        ridge_curvature = _nonnegative(self.ridge_minimum_normal_curvature, "ridge_minimum_normal_curvature")
        ridge_ratio = _nonnegative(self.ridge_tangential_curvature_ratio, "ridge_tangential_curvature_ratio")
        minimum_ridge_nodes = _positive_int(self.minimum_ridge_nodes, "minimum_ridge_nodes")
        core_depth = _positive(self.core_depth_fraction, "core_depth_fraction")
        if core_depth >= 1.0:
            raise DensityAttractorInputError("core_depth_fraction must be smaller than one.")
        content = _positive(self.core_probability_content, "core_probability_content")
        if content > 1.0:
            raise DensityAttractorInputError("core_probability_content must not exceed one.")
        layers = _positive_int(self.transition_boundary_layers, "transition_boundary_layers")
        steps = _positive_int(self.max_ascent_steps, "max_ascent_steps")
        metadata = _freeze(dict(self.metadata))
        payload = {
            "schema": DENSITY_ATTRACTOR_OPTIONS_SCHEMA,
            "neighbor_connectivity": connectivity,
            "plateau_relative_tolerance": plateau,
            "background_density_fraction": background,
            "minimum_point_curvature": point_curvature,
            "ridge_density_fraction": ridge_fraction,
            "ridge_normal_score_tolerance": ridge_score,
            "ridge_minimum_normal_curvature": ridge_curvature,
            "ridge_tangential_curvature_ratio": ridge_ratio,
            "minimum_ridge_nodes": minimum_ridge_nodes,
            "core_depth_fraction": core_depth,
            "core_probability_content": content,
            "transition_boundary_layers": layers,
            "max_ascent_steps": steps,
            "metadata": _json_value(metadata),
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise DensityAttractorInputError("Density-attractor-options signature is inconsistent.")
        for name, value in (
            ("neighbor_connectivity", connectivity), ("plateau_relative_tolerance", plateau),
            ("background_density_fraction", background), ("minimum_point_curvature", point_curvature),
            ("ridge_density_fraction", ridge_fraction), ("ridge_normal_score_tolerance", ridge_score),
            ("ridge_minimum_normal_curvature", ridge_curvature),
            ("ridge_tangential_curvature_ratio", ridge_ratio), ("minimum_ridge_nodes", minimum_ridge_nodes),
            ("core_depth_fraction", core_depth), ("core_probability_content", content),
            ("transition_boundary_layers", layers), ("max_ascent_steps", steps),
            ("metadata", metadata), ("signature", expected),
        ):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": DENSITY_ATTRACTOR_OPTIONS_SCHEMA,
            "neighbor_connectivity": self.neighbor_connectivity,
            "plateau_relative_tolerance": self.plateau_relative_tolerance,
            "background_density_fraction": self.background_density_fraction,
            "minimum_point_curvature": self.minimum_point_curvature,
            "ridge_density_fraction": self.ridge_density_fraction,
            "ridge_normal_score_tolerance": self.ridge_normal_score_tolerance,
            "ridge_minimum_normal_curvature": self.ridge_minimum_normal_curvature,
            "ridge_tangential_curvature_ratio": self.ridge_tangential_curvature_ratio,
            "minimum_ridge_nodes": self.minimum_ridge_nodes,
            "core_depth_fraction": self.core_depth_fraction,
            "core_probability_content": self.core_probability_content,
            "transition_boundary_layers": self.transition_boundary_layers,
            "max_ascent_steps": self.max_ascent_steps,
            "metadata": _json_value(self.metadata),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DensityAttractorOptions":
        if payload.get("schema") != DENSITY_ATTRACTOR_OPTIONS_SCHEMA:
            raise DensityAttractorSerializationError("Unsupported density-attractor-options schema.")
        return cls(**{k: v for k, v in payload.items() if k != "schema"})


@dataclass(frozen=True, slots=True)
class DensityAttractorResourcePolicy:
    max_grid_nodes: int = 5_000_000
    max_neighbor_edges: int = 150_000_000
    max_attractors: int = 100_000
    max_lineage_pairs: int = 10_000_000
    max_serialized_nodes: int = 10_000_000

    def __post_init__(self) -> None:
        for name in ("max_grid_nodes", "max_neighbor_edges", "max_attractors", "max_lineage_pairs", "max_serialized_nodes"):
            object.__setattr__(self, name, _positive_int(getattr(self, name), name))


@dataclass(frozen=True, slots=True)
class AttractorLocalChart:
    kind: LocalChartKind
    anchor_fractional: FloatArray
    support_node_indices: IntArray
    validity_radius: float
    periodic_axis_parameter: FloatArray | None = None
    diagnostic: str | None = None
    signature: str = ""

    def __post_init__(self) -> None:
        kind = LocalChartKind(self.kind)
        anchor = _readonly(self.anchor_fractional, dtype=np.float64, ndim=1, name="anchor_fractional", shape=(3,))
        anchor = np.mod(anchor, 1.0); anchor.setflags(write=False)
        nodes = _readonly(self.support_node_indices, dtype=np.int64, ndim=1, name="support_node_indices")
        if np.any(nodes < 0):
            raise DensityAttractorInputError("support_node_indices must be nonnegative.")
        radius = _nonnegative(self.validity_radius, "validity_radius")
        parameter = None
        if self.periodic_axis_parameter is not None:
            parameter = _readonly(self.periodic_axis_parameter, dtype=np.float64, ndim=1, name="periodic_axis_parameter")
            if parameter.shape != nodes.shape:
                raise DensityAttractorInputError("periodic_axis_parameter must match support_node_indices.")
        payload = {
            "schema": ATTRACTOR_LOCAL_CHART_SCHEMA, "kind": kind.value,
            "anchor_digest": _array_digest(anchor), "nodes_digest": _array_digest(nodes),
            "validity_radius": radius, "parameter_digest": None if parameter is None else _array_digest(parameter),
            "diagnostic": self.diagnostic,
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise DensityAttractorInputError("Attractor-local-chart signature is inconsistent.")
        object.__setattr__(self, "kind", kind); object.__setattr__(self, "anchor_fractional", anchor)
        object.__setattr__(self, "support_node_indices", nodes); object.__setattr__(self, "validity_radius", radius)
        object.__setattr__(self, "periodic_axis_parameter", parameter); object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": ATTRACTOR_LOCAL_CHART_SCHEMA, "kind": self.kind.value,
                "anchor_fractional": self.anchor_fractional.tolist(),
                "support_node_indices": self.support_node_indices.tolist(), "validity_radius": self.validity_radius,
                "periodic_axis_parameter": None if self.periodic_axis_parameter is None else self.periodic_axis_parameter.tolist(),
                "diagnostic": self.diagnostic, "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AttractorLocalChart":
        if payload.get("schema") != ATTRACTOR_LOCAL_CHART_SCHEMA:
            raise DensityAttractorSerializationError("Unsupported attractor-local-chart schema.")
        return cls(kind=LocalChartKind(payload["kind"]), anchor_fractional=np.asarray(payload["anchor_fractional"]),
                   support_node_indices=np.asarray(payload["support_node_indices"]), validity_radius=float(payload["validity_radius"]),
                   periodic_axis_parameter=None if payload.get("periodic_axis_parameter") is None else np.asarray(payload["periodic_axis_parameter"]),
                   diagnostic=payload.get("diagnostic"), signature=str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class DensityAttractor:
    attractor_id: int
    geometry: AttractorGeometry
    anchor_fractional: FloatArray
    representative_node_index: int
    support_node_indices: IntArray
    peak_density: float
    basin_probability: float
    intrinsic_dimension: int | None
    orthonormal_hessian_eigenvalues: FloatArray
    eigenspace_resolved: bool
    local_chart: AttractorLocalChart
    diagnostic: str | None = None
    signature: str = ""

    def __post_init__(self) -> None:
        identifier = int(self.attractor_id)
        if identifier < 0:
            raise DensityAttractorInputError("attractor_id must be nonnegative.")
        geometry = AttractorGeometry(self.geometry)
        anchor = _readonly(self.anchor_fractional, dtype=np.float64, ndim=1, name="anchor_fractional", shape=(3,))
        anchor = np.mod(anchor, 1.0); anchor.setflags(write=False)
        representative = int(self.representative_node_index)
        if representative < 0:
            raise DensityAttractorInputError("representative_node_index must be nonnegative.")
        nodes = _readonly(self.support_node_indices, dtype=np.int64, ndim=1, name="support_node_indices")
        if nodes.size == 0 or np.any(nodes < 0):
            raise DensityAttractorInputError("An attractor requires nonnegative support nodes.")
        peak = _nonnegative(self.peak_density, "peak_density")
        basin = _nonnegative(self.basin_probability, "basin_probability")
        dimension = self.intrinsic_dimension
        if dimension is not None and int(dimension) not in {0, 1, 2, 3}:
            raise DensityAttractorInputError("intrinsic_dimension must be 0..3 or None.")
        dimension = None if dimension is None else int(dimension)
        eigenvalues = _readonly(self.orthonormal_hessian_eigenvalues, dtype=np.float64, ndim=1,
                                name="orthonormal_hessian_eigenvalues", shape=(3,))
        if self.local_chart.anchor_fractional.shape != (3,):
            raise DensityAttractorInputError("local_chart is malformed.")
        payload = {"schema": DENSITY_ATTRACTOR_SCHEMA, "attractor_id": identifier, "geometry": geometry.value,
                   "anchor_digest": _array_digest(anchor), "representative_node_index": representative,
                   "nodes_digest": _array_digest(nodes), "peak_density": peak, "basin_probability": basin,
                   "intrinsic_dimension": dimension, "eigenvalues_digest": _array_digest(eigenvalues),
                   "eigenspace_resolved": bool(self.eigenspace_resolved), "local_chart_signature": self.local_chart.signature,
                   "diagnostic": self.diagnostic}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise DensityAttractorInputError("Density-attractor signature is inconsistent.")
        for name, value in (("attractor_id", identifier), ("geometry", geometry), ("anchor_fractional", anchor),
                            ("representative_node_index", representative), ("support_node_indices", nodes),
                            ("peak_density", peak), ("basin_probability", basin), ("intrinsic_dimension", dimension),
                            ("orthonormal_hessian_eigenvalues", eigenvalues), ("eigenspace_resolved", bool(self.eigenspace_resolved)),
                            ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": DENSITY_ATTRACTOR_SCHEMA, "attractor_id": self.attractor_id, "geometry": self.geometry.value,
                "anchor_fractional": self.anchor_fractional.tolist(), "representative_node_index": self.representative_node_index,
                "support_node_indices": self.support_node_indices.tolist(), "peak_density": self.peak_density,
                "basin_probability": self.basin_probability, "intrinsic_dimension": self.intrinsic_dimension,
                "orthonormal_hessian_eigenvalues": self.orthonormal_hessian_eigenvalues.tolist(),
                "eigenspace_resolved": self.eigenspace_resolved, "local_chart": self.local_chart.to_dict(),
                "diagnostic": self.diagnostic, "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DensityAttractor":
        if payload.get("schema") != DENSITY_ATTRACTOR_SCHEMA:
            raise DensityAttractorSerializationError("Unsupported density-attractor schema.")
        return cls(attractor_id=int(payload["attractor_id"]), geometry=AttractorGeometry(payload["geometry"]),
                   anchor_fractional=np.asarray(payload["anchor_fractional"]), representative_node_index=int(payload["representative_node_index"]),
                   support_node_indices=np.asarray(payload["support_node_indices"]), peak_density=float(payload["peak_density"]),
                   basin_probability=float(payload["basin_probability"]), intrinsic_dimension=payload.get("intrinsic_dimension"),
                   orthonormal_hessian_eigenvalues=np.asarray(payload["orthonormal_hessian_eigenvalues"]),
                   eigenspace_resolved=bool(payload["eigenspace_resolved"]), local_chart=AttractorLocalChart.from_dict(payload["local_chart"]),
                   diagnostic=payload.get("diagnostic"), signature=str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class SupportedPeriodicCellComplex:
    grid_shape: tuple[int, int, int]
    classification: NDArray[np.uint8]
    basin_owner: NDArray[np.int32]
    ascent_successor: IntArray
    support_mask: BoolArray
    signature: str = ""

    def __post_init__(self) -> None:
        shape = tuple(_positive_int(v, "grid_shape") for v in self.grid_shape)
        if len(shape) != 3:
            raise DensityAttractorInputError("grid_shape must have three entries.")
        classes = _readonly(self.classification, dtype=np.uint8, ndim=3, name="classification", shape=shape)
        valid_codes = {int(v) for v in CellClassification}
        if any(int(v) not in valid_codes for v in np.unique(classes)):
            raise DensityAttractorInputError("classification contains an unknown code.")
        owner = _readonly(self.basin_owner, dtype=np.int32, ndim=3, name="basin_owner", shape=shape)
        successor = _readonly(self.ascent_successor, dtype=np.int64, ndim=3, name="ascent_successor", shape=shape)
        support = _readonly(self.support_mask, dtype=np.bool_, ndim=3, name="support_mask", shape=shape)
        if np.any((classes == CellClassification.UNSUPPORTED_UNKNOWN) != (~support)):
            raise DensityAttractorInputError("Unsupported classification must exactly match the inverse support mask.")
        payload = {"schema": SUPPORTED_PERIODIC_CELL_COMPLEX_SCHEMA, "grid_shape": list(shape),
                   "classification_digest": _array_digest(classes), "owner_digest": _array_digest(owner),
                   "successor_digest": _array_digest(successor), "support_digest": _array_digest(support)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise DensityAttractorInputError("Supported-periodic-cell-complex signature is inconsistent.")
        object.__setattr__(self, "grid_shape", shape); object.__setattr__(self, "classification", classes)
        object.__setattr__(self, "basin_owner", owner); object.__setattr__(self, "ascent_successor", successor)
        object.__setattr__(self, "support_mask", support); object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SUPPORTED_PERIODIC_CELL_COMPLEX_SCHEMA, "grid_shape": list(self.grid_shape),
                "classification": self.classification.tolist(), "basin_owner": self.basin_owner.tolist(),
                "ascent_successor": self.ascent_successor.tolist(), "support_mask": self.support_mask.tolist(),
                "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SupportedPeriodicCellComplex":
        if payload.get("schema") != SUPPORTED_PERIODIC_CELL_COMPLEX_SCHEMA:
            raise DensityAttractorSerializationError("Unsupported periodic-cell-complex schema.")
        return cls(grid_shape=tuple(payload["grid_shape"]), classification=np.asarray(payload["classification"]),
                   basin_owner=np.asarray(payload["basin_owner"]), ascent_successor=np.asarray(payload["ascent_successor"]),
                   support_mask=np.asarray(payload["support_mask"]), signature=str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class SupportedSaddle:
    basin_pair: tuple[int, int]
    saddle_density: float
    logical_edge_nodes: tuple[int, int]
    fully_supported: bool = True
    signature: str = ""

    def __post_init__(self) -> None:
        pair = tuple(sorted(int(v) for v in self.basin_pair))
        if len(pair) != 2 or pair[0] < 0 or pair[0] == pair[1]:
            raise DensityAttractorInputError("basin_pair must contain two distinct nonnegative ids.")
        density = _nonnegative(self.saddle_density, "saddle_density")
        edge = tuple(int(v) for v in self.logical_edge_nodes)
        if len(edge) != 2 or min(edge) < 0:
            raise DensityAttractorInputError("logical_edge_nodes must contain two nonnegative indices.")
        payload = {"schema": SUPPORTED_SADDLE_SCHEMA, "basin_pair": list(pair), "saddle_density": density,
                   "logical_edge_nodes": list(edge), "fully_supported": bool(self.fully_supported)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise DensityAttractorInputError("Supported-saddle signature is inconsistent.")
        object.__setattr__(self, "basin_pair", pair); object.__setattr__(self, "saddle_density", density)
        object.__setattr__(self, "logical_edge_nodes", edge); object.__setattr__(self, "fully_supported", bool(self.fully_supported))
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SUPPORTED_SADDLE_SCHEMA, "basin_pair": list(self.basin_pair), "saddle_density": self.saddle_density,
                "logical_edge_nodes": list(self.logical_edge_nodes), "fully_supported": self.fully_supported, "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SupportedSaddle":
        if payload.get("schema") != SUPPORTED_SADDLE_SCHEMA:
            raise DensityAttractorSerializationError("Unsupported supported-saddle schema.")
        return cls(basin_pair=tuple(payload["basin_pair"]), saddle_density=float(payload["saddle_density"]),
                   logical_edge_nodes=tuple(payload["logical_edge_nodes"]), fully_supported=bool(payload["fully_supported"]),
                   signature=str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class ProvisionalCore:
    attractor_id: int
    depth_source: CoreDepthSource
    core_node_indices: IntArray
    threshold_density: float | None
    local_threshold_density_range: tuple[float, float] | None = None
    retained_probability: float = 0.0
    resolved: bool = False
    diagnostic: str | None = None
    signature: str = ""

    def __post_init__(self) -> None:
        identifier = int(self.attractor_id)
        if identifier < 0:
            raise DensityAttractorInputError("attractor_id must be nonnegative.")
        source = CoreDepthSource(self.depth_source)
        nodes = _readonly(self.core_node_indices, dtype=np.int64, ndim=1, name="core_node_indices")
        if np.any(nodes < 0):
            raise DensityAttractorInputError("core_node_indices must be nonnegative.")
        threshold = None if self.threshold_density is None else _nonnegative(self.threshold_density, "threshold_density")
        local_range = None
        if self.local_threshold_density_range is not None:
            local_range = tuple(_nonnegative(v, "local_threshold_density_range") for v in self.local_threshold_density_range)
            if len(local_range) != 2 or local_range[0] > local_range[1]:
                raise DensityAttractorInputError("local_threshold_density_range must be an ordered pair.")
        probability = _nonnegative(self.retained_probability, "retained_probability")
        payload = {"schema": PROVISIONAL_CORE_SCHEMA, "attractor_id": identifier, "depth_source": source.value,
                   "nodes_digest": _array_digest(nodes), "threshold_density": threshold,
                   "local_threshold_density_range": None if local_range is None else list(local_range),
                   "retained_probability": probability, "resolved": bool(self.resolved), "diagnostic": self.diagnostic}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise DensityAttractorInputError("Provisional-core signature is inconsistent.")
        object.__setattr__(self, "attractor_id", identifier); object.__setattr__(self, "depth_source", source)
        object.__setattr__(self, "core_node_indices", nodes); object.__setattr__(self, "threshold_density", threshold)
        object.__setattr__(self, "local_threshold_density_range", local_range)
        object.__setattr__(self, "retained_probability", probability); object.__setattr__(self, "resolved", bool(self.resolved))
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": PROVISIONAL_CORE_SCHEMA, "attractor_id": self.attractor_id, "depth_source": self.depth_source.value,
                "core_node_indices": self.core_node_indices.tolist(), "threshold_density": self.threshold_density,
                "local_threshold_density_range": None if self.local_threshold_density_range is None else list(self.local_threshold_density_range),
                "retained_probability": self.retained_probability, "resolved": self.resolved,
                "diagnostic": self.diagnostic, "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProvisionalCore":
        if payload.get("schema") != PROVISIONAL_CORE_SCHEMA:
            raise DensityAttractorSerializationError("Unsupported provisional-core schema.")
        return cls(attractor_id=int(payload["attractor_id"]), depth_source=CoreDepthSource(payload["depth_source"]),
                   core_node_indices=np.asarray(payload["core_node_indices"]), threshold_density=payload.get("threshold_density"),
                   local_threshold_density_range=None if payload.get("local_threshold_density_range") is None else tuple(payload["local_threshold_density_range"]),
                   retained_probability=float(payload["retained_probability"]), resolved=bool(payload["resolved"]),
                   diagnostic=payload.get("diagnostic"), signature=str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class TopologyStabilityCertificate:
    status: TopologyStabilityStatus
    compared_catalog_signatures: tuple[str, ...]
    attractor_count_stable: bool
    geometry_multiset_stable: bool
    saddle_adjacency_stable: bool
    basin_overlap_minimum: float | None
    unresolved_reasons: tuple[str, ...] = ()
    signature: str = ""

    def __post_init__(self) -> None:
        status = TopologyStabilityStatus(self.status)
        signatures = tuple(_sha(v, "compared_catalog_signature") for v in self.compared_catalog_signatures)
        overlap = None if self.basin_overlap_minimum is None else _nonnegative(self.basin_overlap_minimum, "basin_overlap_minimum")
        if overlap is not None and overlap > 1.0 + 1e-12:
            raise DensityAttractorInputError("basin_overlap_minimum must not exceed one.")
        reasons = tuple(str(v) for v in self.unresolved_reasons)
        payload = {"schema": TOPOLOGY_STABILITY_CERTIFICATE_SCHEMA, "status": status.value,
                   "compared_catalog_signatures": list(signatures), "attractor_count_stable": bool(self.attractor_count_stable),
                   "geometry_multiset_stable": bool(self.geometry_multiset_stable),
                   "saddle_adjacency_stable": bool(self.saddle_adjacency_stable),
                   "basin_overlap_minimum": overlap, "unresolved_reasons": list(reasons)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise DensityAttractorInputError("Topology-stability-certificate signature is inconsistent.")
        object.__setattr__(self, "status", status); object.__setattr__(self, "compared_catalog_signatures", signatures)
        object.__setattr__(self, "basin_overlap_minimum", overlap); object.__setattr__(self, "unresolved_reasons", reasons)
        object.__setattr__(self, "signature", expected)

    @classmethod
    def unassessed(cls, catalog_signature: str) -> "TopologyStabilityCertificate":
        return cls(status=TopologyStabilityStatus.UNASSESSED, compared_catalog_signatures=(catalog_signature,),
                   attractor_count_stable=False, geometry_multiset_stable=False, saddle_adjacency_stable=False,
                   basin_overlap_minimum=None, unresolved_reasons=("single_realization_only",))

    def to_dict(self) -> dict[str, Any]:
        return {"schema": TOPOLOGY_STABILITY_CERTIFICATE_SCHEMA, "status": self.status.value,
                "compared_catalog_signatures": list(self.compared_catalog_signatures),
                "attractor_count_stable": self.attractor_count_stable, "geometry_multiset_stable": self.geometry_multiset_stable,
                "saddle_adjacency_stable": self.saddle_adjacency_stable, "basin_overlap_minimum": self.basin_overlap_minimum,
                "unresolved_reasons": list(self.unresolved_reasons), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TopologyStabilityCertificate":
        if payload.get("schema") != TOPOLOGY_STABILITY_CERTIFICATE_SCHEMA:
            raise DensityAttractorSerializationError("Unsupported topology-stability-certificate schema.")
        return cls(status=TopologyStabilityStatus(payload["status"]), compared_catalog_signatures=tuple(payload["compared_catalog_signatures"]),
                   attractor_count_stable=bool(payload["attractor_count_stable"]),
                   geometry_multiset_stable=bool(payload["geometry_multiset_stable"]),
                   saddle_adjacency_stable=bool(payload["saddle_adjacency_stable"]),
                   basin_overlap_minimum=payload.get("basin_overlap_minimum"),
                   unresolved_reasons=tuple(payload.get("unresolved_reasons", ())), signature=str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class DensityAttractorCatalog:
    density_estimate_signature: str
    domain_signature: str
    covariance_signature: str
    options: DensityAttractorOptions
    cell_complex: SupportedPeriodicCellComplex
    attractors: tuple[DensityAttractor, ...]
    saddles: tuple[SupportedSaddle, ...]
    provisional_cores: tuple[ProvisionalCore, ...]
    topology_certificate: TopologyStabilityCertificate | None = None
    refinement_history: tuple[Mapping[str, Any], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        estimate = _sha(self.density_estimate_signature, "density_estimate_signature")
        domain = _sha(self.domain_signature, "domain_signature")
        covariance = _sha(self.covariance_signature, "covariance_signature")
        attractors = tuple(self.attractors)
        if tuple(item.attractor_id for item in attractors) != tuple(range(len(attractors))):
            raise DensityAttractorInputError("Attractor ids must be contiguous and canonical.")
        if len(self.provisional_cores) != len(attractors):
            raise DensityAttractorInputError("Each attractor requires one provisional-core record.")
        if tuple(core.attractor_id for core in self.provisional_cores) != tuple(range(len(attractors))):
            raise DensityAttractorInputError("Provisional-core ids must align with attractor ids.")
        if np.any(self.cell_complex.basin_owner >= len(attractors)):
            raise DensityAttractorInputError("Cell complex refers to an unknown attractor.")
        history = tuple(_freeze(dict(item)) for item in self.refinement_history)
        metadata = _freeze(dict(self.metadata))
        certificate = self.topology_certificate
        payload = {"schema": DENSITY_ATTRACTOR_CATALOG_SCHEMA, "density_estimate_signature": estimate,
                   "domain_signature": domain, "covariance_signature": covariance, "options_signature": self.options.signature,
                   "cell_complex_signature": self.cell_complex.signature, "attractor_signatures": [v.signature for v in attractors],
                   "saddle_signatures": [v.signature for v in self.saddles], "core_signatures": [v.signature for v in self.provisional_cores],
                   "refinement_history": _json_value(history), "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise DensityAttractorInputError("Density-attractor-catalog signature is inconsistent.")
        object.__setattr__(self, "density_estimate_signature", estimate); object.__setattr__(self, "domain_signature", domain)
        object.__setattr__(self, "covariance_signature", covariance); object.__setattr__(self, "attractors", attractors)
        object.__setattr__(self, "saddles", tuple(self.saddles)); object.__setattr__(self, "provisional_cores", tuple(self.provisional_cores))
        object.__setattr__(self, "refinement_history", history); object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": DENSITY_ATTRACTOR_CATALOG_SCHEMA, "density_estimate_signature": self.density_estimate_signature,
                "domain_signature": self.domain_signature, "covariance_signature": self.covariance_signature,
                "options": self.options.to_dict(), "cell_complex": self.cell_complex.to_dict(),
                "attractors": [v.to_dict() for v in self.attractors], "saddles": [v.to_dict() for v in self.saddles],
                "provisional_cores": [v.to_dict() for v in self.provisional_cores],
                "topology_certificate": None if self.topology_certificate is None else self.topology_certificate.to_dict(),
                "refinement_history": _json_value(self.refinement_history), "metadata": _json_value(self.metadata),
                "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DensityAttractorCatalog":
        if payload.get("schema") != DENSITY_ATTRACTOR_CATALOG_SCHEMA:
            raise DensityAttractorSerializationError("Unsupported density-attractor-catalog schema.")
        return cls(density_estimate_signature=str(payload["density_estimate_signature"]), domain_signature=str(payload["domain_signature"]),
                   covariance_signature=str(payload["covariance_signature"]), options=DensityAttractorOptions.from_dict(payload["options"]),
                   cell_complex=SupportedPeriodicCellComplex.from_dict(payload["cell_complex"]),
                   attractors=tuple(DensityAttractor.from_dict(v) for v in payload["attractors"]),
                   saddles=tuple(SupportedSaddle.from_dict(v) for v in payload["saddles"]),
                   provisional_cores=tuple(ProvisionalCore.from_dict(v) for v in payload["provisional_cores"]),
                   topology_certificate=None if payload.get("topology_certificate") is None else TopologyStabilityCertificate.from_dict(payload["topology_certificate"]),
                   refinement_history=tuple(payload.get("refinement_history", ())), metadata=dict(payload.get("metadata", {})),
                   signature=str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class AttractorCorrespondence:
    source_catalog_signature: str
    target_catalog_signature: str
    links: tuple[tuple[int, int, float, float], ...]
    source_unmatched: tuple[int, ...]
    target_unmatched: tuple[int, ...]
    signature: str = ""

    def __post_init__(self) -> None:
        source = _sha(self.source_catalog_signature, "source_catalog_signature")
        target = _sha(self.target_catalog_signature, "target_catalog_signature")
        links = tuple((int(a), int(b), float(overlap), float(distance)) for a, b, overlap, distance in self.links)
        if any(a < 0 or b < 0 or overlap < 0.0 or overlap > 1.0 + 1e-12 or distance < 0.0 for a, b, overlap, distance in links):
            raise DensityAttractorInputError("Invalid attractor correspondence link.")
        source_unmatched = tuple(sorted(int(v) for v in self.source_unmatched))
        target_unmatched = tuple(sorted(int(v) for v in self.target_unmatched))
        payload = {"schema": ATTRACTOR_CORRESPONDENCE_SCHEMA, "source_catalog_signature": source,
                   "target_catalog_signature": target, "links": [list(v) for v in links],
                   "source_unmatched": list(source_unmatched), "target_unmatched": list(target_unmatched)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise DensityAttractorInputError("Attractor-correspondence signature is inconsistent.")
        object.__setattr__(self, "source_catalog_signature", source); object.__setattr__(self, "target_catalog_signature", target)
        object.__setattr__(self, "links", links); object.__setattr__(self, "source_unmatched", source_unmatched)
        object.__setattr__(self, "target_unmatched", target_unmatched); object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": ATTRACTOR_CORRESPONDENCE_SCHEMA, "source_catalog_signature": self.source_catalog_signature,
                "target_catalog_signature": self.target_catalog_signature, "links": [list(v) for v in self.links],
                "source_unmatched": list(self.source_unmatched), "target_unmatched": list(self.target_unmatched), "signature": self.signature}


@dataclass(frozen=True, slots=True)
class DensityAttractorLineage:
    ladder_signature: str
    catalog_signatures: tuple[str, ...]
    correspondences: tuple[AttractorCorrespondence, ...]
    survival_intervals: tuple[tuple[int, int, int], ...]
    ambiguous: bool
    signature: str = ""

    def __post_init__(self) -> None:
        ladder = _sha(self.ladder_signature, "ladder_signature")
        catalogs = tuple(_sha(v, "catalog_signature") for v in self.catalog_signatures)
        if len(catalogs) == 0 or len(self.correspondences) != max(0, len(catalogs) - 1):
            raise DensityAttractorInputError("Lineage correspondence count is inconsistent.")
        intervals = tuple((int(i), int(start), int(stop)) for i, start, stop in self.survival_intervals)
        payload = {"schema": DENSITY_ATTRACTOR_LINEAGE_SCHEMA, "ladder_signature": ladder,
                   "catalog_signatures": list(catalogs), "correspondence_signatures": [v.signature for v in self.correspondences],
                   "survival_intervals": [list(v) for v in intervals], "ambiguous": bool(self.ambiguous)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise DensityAttractorInputError("Density-attractor-lineage signature is inconsistent.")
        object.__setattr__(self, "ladder_signature", ladder); object.__setattr__(self, "catalog_signatures", catalogs)
        object.__setattr__(self, "correspondences", tuple(self.correspondences)); object.__setattr__(self, "survival_intervals", intervals)
        object.__setattr__(self, "ambiguous", bool(self.ambiguous)); object.__setattr__(self, "signature", expected)


@dataclass(frozen=True, slots=True)
class SelectionValidationProtocol:
    discovery_block_ids: tuple[str, ...]
    selection_block_ids: tuple[str, ...] = ()
    validation_block_ids: tuple[str, ...] = ()
    require_independent_selection: bool = False
    require_independent_validation: bool = False
    signature: str = ""

    def __post_init__(self) -> None:
        discovery = tuple(str(v) for v in self.discovery_block_ids)
        selection = tuple(str(v) for v in self.selection_block_ids)
        validation = tuple(str(v) for v in self.validation_block_ids)
        if not discovery:
            raise DensityAttractorInputError("discovery_block_ids must be nonempty.")
        if self.require_independent_selection and set(discovery) & set(selection):
            raise DensityAttractorInputError("Selection blocks overlap discovery blocks.")
        if self.require_independent_validation and (set(discovery) | set(selection)) & set(validation):
            raise DensityAttractorInputError("Validation blocks are not independent.")
        payload = {"schema": SELECTION_VALIDATION_PROTOCOL_SCHEMA, "discovery_block_ids": list(discovery),
                   "selection_block_ids": list(selection), "validation_block_ids": list(validation),
                   "require_independent_selection": bool(self.require_independent_selection),
                   "require_independent_validation": bool(self.require_independent_validation)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise DensityAttractorInputError("Selection-validation-protocol signature is inconsistent.")
        object.__setattr__(self, "discovery_block_ids", discovery); object.__setattr__(self, "selection_block_ids", selection)
        object.__setattr__(self, "validation_block_ids", validation); object.__setattr__(self, "signature", expected)


@dataclass(frozen=True, slots=True)
class ScaleConsensusResult:
    lineage_signature: str
    protocol_signature: str
    status: ScaleDecisionStatus
    selected_catalog_signature: str | None
    candidate_scale_intervals: tuple[tuple[int, int], ...]
    competing_catalog_signatures: tuple[str, ...]
    rationale: str
    signature: str = ""

    def __post_init__(self) -> None:
        lineage = _sha(self.lineage_signature, "lineage_signature")
        protocol = _sha(self.protocol_signature, "protocol_signature")
        status = ScaleDecisionStatus(self.status)
        selected = None if self.selected_catalog_signature is None else _sha(self.selected_catalog_signature, "selected_catalog_signature")
        intervals = tuple((int(a), int(b)) for a, b in self.candidate_scale_intervals)
        competing = tuple(_sha(v, "competing_catalog_signature") for v in self.competing_catalog_signatures)
        if status is ScaleDecisionStatus.RESOLVED and selected is None:
            raise DensityAttractorInputError("Resolved scale consensus requires a selected catalog.")
        payload = {"schema": SCALE_CONSENSUS_SCHEMA, "lineage_signature": lineage, "protocol_signature": protocol,
                   "status": status.value, "selected_catalog_signature": selected,
                   "candidate_scale_intervals": [list(v) for v in intervals],
                   "competing_catalog_signatures": list(competing), "rationale": str(self.rationale)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise DensityAttractorInputError("Scale-consensus signature is inconsistent.")
        object.__setattr__(self, "lineage_signature", lineage); object.__setattr__(self, "protocol_signature", protocol)
        object.__setattr__(self, "status", status); object.__setattr__(self, "selected_catalog_signature", selected)
        object.__setattr__(self, "candidate_scale_intervals", intervals); object.__setattr__(self, "competing_catalog_signatures", competing)
        object.__setattr__(self, "signature", expected)


@dataclass(frozen=True, slots=True)
class DensityAttractorRefinementSeries:
    catalog_signatures: tuple[str, ...]
    grid_shapes: tuple[tuple[int, int, int], ...]
    certificate: TopologyStabilityCertificate
    signature: str = ""

    def __post_init__(self) -> None:
        catalogs = tuple(_sha(v, "catalog_signature") for v in self.catalog_signatures)
        shapes = tuple(tuple(int(x) for x in shape) for shape in self.grid_shapes)
        if len(catalogs) < 2 or len(catalogs) != len(shapes):
            raise DensityAttractorInputError("Refinement series requires at least two aligned catalogs.")
        payload = {"schema": DENSITY_REFINEMENT_SERIES_SCHEMA, "catalog_signatures": list(catalogs),
                   "grid_shapes": [list(v) for v in shapes], "certificate_signature": self.certificate.signature}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise DensityAttractorInputError("Density-attractor-refinement-series signature is inconsistent.")
        object.__setattr__(self, "catalog_signatures", catalogs); object.__setattr__(self, "grid_shapes", shapes)
        object.__setattr__(self, "signature", expected)


@dataclass(frozen=True, slots=True)
class PeriodicClusterComparison:
    method: str
    status: ClusterComparisonStatus
    labels: IntArray
    centers_fractional: FloatArray
    objective: float | None
    diagnostic: str | None = None
    signature: str = ""

    def __post_init__(self) -> None:
        method = str(self.method)
        status = ClusterComparisonStatus(self.status)
        labels = _readonly(self.labels, dtype=np.int64, ndim=1, name="labels")
        centers = _readonly(self.centers_fractional, dtype=np.float64, ndim=2, name="centers_fractional")
        if centers.shape[1:] != (3,):
            raise DensityAttractorInputError("centers_fractional must have shape (n,3).")
        centers = np.mod(centers, 1.0); centers.setflags(write=False)
        objective = None if self.objective is None else _nonnegative(self.objective, "objective")
        payload = {"schema": CLUSTER_COMPARISON_SCHEMA, "method": method, "status": status.value,
                   "labels_digest": _array_digest(labels), "centers_digest": _array_digest(centers),
                   "objective": objective, "diagnostic": self.diagnostic}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise DensityAttractorInputError("Periodic-cluster-comparison signature is inconsistent.")
        object.__setattr__(self, "method", method); object.__setattr__(self, "status", status)
        object.__setattr__(self, "labels", labels); object.__setattr__(self, "centers_fractional", centers)
        object.__setattr__(self, "objective", objective); object.__setattr__(self, "signature", expected)


def _candidate_ridge_mask(estimate: PeriodicSpeciesDensityEstimate, options: DensityAttractorOptions) -> np.ndarray:
    rho = estimate.realization.probability_density_dense()
    support = estimate.realization.support_mask_dense()
    if not np.any(support):
        return np.zeros_like(support)
    score = estimate.realization.density_score_covector_dense()
    hessian = estimate.realization.density_hessian_covariant_dense()
    metric = estimate.analysis_metric
    score_y = metric.covectors_in_orthonormal_chart(score.reshape(-1, 3)).reshape(score.shape)
    hessian_y = metric.hessians_in_orthonormal_chart(hessian.reshape(-1, 3, 3)).reshape(hessian.shape)
    result = np.zeros_like(support)
    density_floor = options.ridge_density_fraction * float(np.max(rho[support]))
    for index_arr in np.argwhere(support & (rho >= density_floor)):
        index = tuple(int(v) for v in index_arr)
        eigvals, eigvecs = np.linalg.eigh(hessian_y[index])
        order = np.argsort(eigvals)[::-1]
        eigvals = eigvals[order]; eigvecs = eigvecs[:, order]
        normal = eigvecs[:, 1:]
        normal_score = float(np.linalg.norm(normal.T @ score_y[index]))
        normal_scale = max(abs(float(eigvals[1])), abs(float(eigvals[2])), np.finfo(float).eps)
        tangential_ratio = abs(float(eigvals[0])) / normal_scale
        if (normal_score <= options.ridge_normal_score_tolerance
                and float(eigvals[1]) < -options.ridge_minimum_normal_curvature
                and float(eigvals[2]) < -options.ridge_minimum_normal_curvature
                and tangential_ratio <= options.ridge_tangential_curvature_ratio):
            result[index] = True
    return result


def _local_maximum_plateaus(rho: np.ndarray, active: np.ndarray, offsets: tuple[tuple[int, int, int], ...], tolerance: float) -> list[np.ndarray]:
    shape = tuple(int(v) for v in rho.shape)
    max_value = float(np.max(rho[active])) if np.any(active) else 0.0
    absolute_tolerance = tolerance * max(max_value, 1.0)
    local = np.zeros(shape, dtype=bool)
    for idx_arr in np.argwhere(active):
        idx = tuple(int(v) for v in idx_arr)
        value = float(rho[idx])
        higher = False
        for offset in offsets:
            nxt = _wrapped_neighbor(idx, offset, shape)
            if active[nxt] and float(rho[nxt]) > value + absolute_tolerance:
                higher = True
                break
        if not higher:
            local[idx] = True
    components = _component_nodes(local, offsets)
    output: list[np.ndarray] = []
    for component in components:
        values = rho.reshape(-1)[component]
        if float(np.max(values) - np.min(values)) <= absolute_tolerance:
            output.append(component)
        else:
            maximum = float(np.max(values))
            mask = np.zeros(shape, dtype=bool)
            selected = component[np.abs(values - maximum) <= absolute_tolerance]
            mask.reshape(-1)[selected] = True
            output.extend(_component_nodes(mask, offsets))
    return output


def _build_charts(
    geometry: AttractorGeometry,
    nodes: np.ndarray,
    anchor: np.ndarray,
    shape: tuple[int, int, int],
    metric: AnalysisGeometryMetric,
) -> AttractorLocalChart:
    points = np.asarray([np.asarray(_unflat(int(v), shape), dtype=np.float64) / np.asarray(shape) for v in nodes])
    distances = np.asarray([_metric_distance(point, anchor, metric) for point in points], dtype=np.float64)
    radius = float(np.max(distances)) if distances.size else 0.0
    if geometry is AttractorGeometry.ISOLATED_MODE:
        return AttractorLocalChart(LocalChartKind.ISOLATED_MODE, anchor, nodes, radius)
    if geometry is AttractorGeometry.RIDGE_OR_MANIFOLD:
        deltas = np.asarray([_periodic_delta(point, anchor) for point in points])
        if len(points) >= 3:
            covariance = deltas.T @ deltas / max(len(points), 1)
            eigvals, eigvecs = np.linalg.eigh(covariance)
            normal = eigvecs[:, np.argmin(eigvals)]
            basis1 = eigvecs[:, np.argmax(eigvals)]
            basis2 = np.cross(normal, basis1)
            parameter = np.mod(np.arctan2(deltas @ basis2, deltas @ basis1), 2.0 * math.pi)
            order = np.argsort(parameter)
            ordered_parameter = np.empty_like(parameter); ordered_parameter[order] = np.linspace(0.0, 2.0 * math.pi, len(parameter), endpoint=False)
            return AttractorLocalChart(LocalChartKind.ANNULAR, anchor, nodes, radius, ordered_parameter)
        return AttractorLocalChart(LocalChartKind.MANIFOLD_UNRESOLVED, anchor, nodes, radius, diagnostic="insufficient_ridge_nodes")
    return AttractorLocalChart(LocalChartKind.MANIFOLD_UNRESOLVED, anchor, nodes, radius, diagnostic="flat_component")


def _assign_ascent(
    rho: np.ndarray,
    active: np.ndarray,
    seed_owner: np.ndarray,
    offsets: tuple[tuple[int, int, int], ...],
    max_steps: int,
) -> tuple[np.ndarray, np.ndarray]:
    shape = tuple(int(v) for v in rho.shape)
    owner = np.full(shape, -1, dtype=np.int32)
    successor = np.full(shape, -1, dtype=np.int64)
    owner[seed_owner >= 0] = seed_owner[seed_owner >= 0]
    flat_rho = rho.reshape(-1)
    flat_active = active.reshape(-1)
    flat_owner = owner.reshape(-1)
    flat_successor = successor.reshape(-1)
    for start in np.flatnonzero(flat_active):
        if flat_owner[start] >= 0:
            continue
        path: list[int] = []
        current = int(start)
        visited: set[int] = set()
        for _ in range(max_steps):
            if flat_owner[current] >= 0:
                resolved = int(flat_owner[current])
                break
            if current in visited:
                resolved = -2
                break
            visited.add(current); path.append(current)
            idx = _unflat(current, shape)
            candidates: list[tuple[float, int]] = []
            for offset in offsets:
                nxt = _flat(_wrapped_neighbor(idx, offset, shape), shape)
                if flat_active[nxt]:
                    candidates.append((float(flat_rho[nxt]), nxt))
            if not candidates:
                resolved = -2
                break
            best_value = max(v for v, _ in candidates)
            if best_value <= float(flat_rho[current]):
                # Canonical plateau walk, which must eventually reach a seed if
                # local-max plateau construction was complete.
                equal = [nxt for value, nxt in candidates if abs(value - float(flat_rho[current])) <= 1e-15]
                higher_owner = [nxt for nxt in equal if flat_owner[nxt] >= 0]
                if higher_owner:
                    next_node = min(higher_owner)
                else:
                    unvisited = [nxt for nxt in equal if nxt not in visited]
                    if not unvisited:
                        resolved = -2
                        break
                    next_node = min(unvisited)
            else:
                next_node = min(nxt for value, nxt in candidates if value == best_value)
            flat_successor[current] = next_node
            current = next_node
        else:
            resolved = -2
        for node in path:
            flat_owner[node] = resolved
    return owner, successor


def _build_saddles(owner: np.ndarray, rho: np.ndarray, support: np.ndarray) -> tuple[SupportedSaddle, ...]:
    shape = tuple(int(v) for v in rho.shape)
    offsets = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    best: dict[tuple[int, int], tuple[float, tuple[int, int]]] = {}
    for idx_arr in np.argwhere(support & (owner >= 0)):
        idx = tuple(int(v) for v in idx_arr)
        a = int(owner[idx])
        flat_a = _flat(idx, shape)
        for offset in offsets:
            nxt = _wrapped_neighbor(idx, offset, shape)
            if not support[nxt] or int(owner[nxt]) < 0 or int(owner[nxt]) == a:
                continue
            b = int(owner[nxt]); pair = tuple(sorted((a, b)))
            candidate = min(float(rho[idx]), float(rho[nxt]))
            edge = tuple(sorted((flat_a, _flat(nxt, shape))))
            if pair not in best or candidate > best[pair][0] or (candidate == best[pair][0] and edge < best[pair][1]):
                best[pair] = (candidate, edge)
    return tuple(SupportedSaddle(pair, density, edge) for pair, (density, edge) in sorted(best.items()))


def _build_provisional_cores(
    attractors: Sequence[DensityAttractor], owner: np.ndarray, classes: np.ndarray,
    rho: np.ndarray, saddles: Sequence[SupportedSaddle], voxel_volume: float,
    options: DensityAttractorOptions, metric: AnalysisGeometryMetric,
) -> tuple[ProvisionalCore, ...]:
    flat_owner = owner.reshape(-1); flat_classes = classes.reshape(-1); flat_rho = rho.reshape(-1)
    saddle_by_id: dict[int, list[float]] = defaultdict(list)
    for saddle in saddles:
        saddle_by_id[saddle.basin_pair[0]].append(saddle.saddle_density)
        saddle_by_id[saddle.basin_pair[1]].append(saddle.saddle_density)
    cores: list[ProvisionalCore] = []
    shape = tuple(int(v) for v in owner.shape)
    offsets6 = _neighbor_offsets(6)
    grid_points = np.asarray([np.asarray(_unflat(i, shape), dtype=np.float64) / np.asarray(shape) for i in range(flat_owner.size)])
    for attractor in attractors:
        basin_nodes = np.flatnonzero((flat_owner == attractor.attractor_id) & (flat_classes != CellClassification.SUPPORTED_TRANSITION_REGION))
        if basin_nodes.size == 0:
            cores.append(ProvisionalCore(attractor.attractor_id, CoreDepthSource.CORE_UNRESOLVED,
                                         np.empty(0, dtype=np.int64), None, None, 0.0, False, "empty_supported_basin"))
            continue
        peak = max(attractor.peak_density, np.finfo(float).tiny)
        threshold: float | None = None
        local_range: tuple[float, float] | None = None
        source: CoreDepthSource
        selected = np.empty(0, dtype=np.int64)
        if saddle_by_id.get(attractor.attractor_id):
            saddle = max(saddle_by_id[attractor.attractor_id])
            if saddle > 0.0 and saddle < peak:
                source = CoreDepthSource.INTERBASIN_SADDLE_DEPTH
                if attractor.geometry is AttractorGeometry.RIDGE_OR_MANIFOLD:
                    ridge_nodes = attractor.support_node_indices
                    ridge_points = grid_points[ridge_nodes]
                    local_thresholds = np.empty(basin_nodes.size, dtype=np.float64)
                    for index, node in enumerate(basin_nodes):
                        distances = np.asarray([_metric_distance(grid_points[node], point, metric) for point in ridge_points])
                        ridge_density = max(float(flat_rho[int(ridge_nodes[int(np.argmin(distances))])]), saddle)
                        local_thresholds[index] = math.exp(math.log(saddle) + options.core_depth_fraction * (math.log(ridge_density) - math.log(saddle)))
                    selected = basin_nodes[flat_rho[basin_nodes] >= local_thresholds]
                    local_range = (float(np.min(local_thresholds)), float(np.max(local_thresholds)))
                else:
                    threshold = math.exp(math.log(saddle) + options.core_depth_fraction * (math.log(peak) - math.log(saddle)))
                    selected = basin_nodes[flat_rho[basin_nodes] >= threshold]
            else:
                source = CoreDepthSource.CORE_UNRESOLVED
        else:
            boundary: list[int] = []
            for node in basin_nodes:
                idx = _unflat(int(node), shape)
                for offset in offsets6:
                    nxt = _wrapped_neighbor(idx, offset, shape)
                    nxt_flat = _flat(nxt, shape)
                    if (flat_classes[nxt_flat] in {CellClassification.UNSUPPORTED_UNKNOWN, CellClassification.SUPPORTED_BACKGROUND}
                            or (flat_owner[nxt_flat] >= 0 and flat_owner[nxt_flat] != attractor.attractor_id)):
                        boundary.append(int(node)); break
            boundary_nodes = np.asarray(sorted(set(boundary)), dtype=np.int64)
            boundary_density = float(np.max(flat_rho[boundary_nodes])) if boundary_nodes.size else peak
            if 0.0 < boundary_density < peak:
                threshold = math.exp(math.log(boundary_density) + options.core_depth_fraction * (math.log(peak) - math.log(boundary_density)))
                source = CoreDepthSource.SUPPORTED_BOUNDARY_DEPTH
                selected = basin_nodes[flat_rho[basin_nodes] >= threshold]
            else:
                source = CoreDepthSource.PROBABILITY_CONTENT_CORE
                ordered = basin_nodes[np.lexsort((basin_nodes, -flat_rho[basin_nodes]))]
                masses = flat_rho[ordered] * voxel_volume
                total = float(np.sum(masses))
                if total > 0.0:
                    count = int(np.searchsorted(np.cumsum(masses), options.core_probability_content * total, side="left") + 1)
                    selected = ordered[:count]
                    threshold = float(np.min(flat_rho[selected])) if selected.size else None
        retained = float(np.sum(flat_rho[selected]) * voxel_volume)
        cores.append(ProvisionalCore(attractor.attractor_id, source, np.asarray(sorted(selected), dtype=np.int64),
                                     threshold, local_range, retained, bool(selected.size),
                                     "local_ridge_depth" if local_range is not None else (None if selected.size else "core_unresolved")))
    return tuple(cores)


def prepare_density_attractor_catalog(
    estimate: PeriodicSpeciesDensityEstimate,
    *,
    options: DensityAttractorOptions | None = None,
    resources: DensityAttractorResourcePolicy | None = None,
) -> DensityAttractorCatalog:
    """Build the canonical support-restricted periodic attractor catalog."""
    options = DensityAttractorOptions() if options is None else options
    resources = DensityAttractorResourcePolicy() if resources is None else resources
    shape = estimate.realization.grid_shape
    nodes = int(np.prod(shape))
    offsets = _neighbor_offsets(options.neighbor_connectivity)
    if nodes > resources.max_grid_nodes:
        raise DensityAttractorResourceError(f"grid nodes {nodes}>{resources.max_grid_nodes}")
    if nodes > resources.max_serialized_nodes:
        raise DensityAttractorResourceError(f"serialized nodes {nodes}>{resources.max_serialized_nodes}")
    if nodes * len(offsets) > resources.max_neighbor_edges:
        raise DensityAttractorResourceError(f"neighbor edge visits {nodes * len(offsets)}>{resources.max_neighbor_edges}")
    rho = np.asarray(estimate.realization.probability_density_dense(), dtype=np.float64)
    support = np.asarray(estimate.realization.support_mask_dense(), dtype=bool)
    if not np.any(support):
        raise DensityAttractorInputError("The Stage-11E1 field contains no supported nodes.")
    max_density = float(np.max(rho[support]))
    active = support & (rho > options.background_density_fraction * max_density)
    classes = np.full(shape, CellClassification.UNSUPPORTED_UNKNOWN, dtype=np.uint8)
    classes[support] = CellClassification.SUPPORTED_BACKGROUND
    classes[active] = CellClassification.SUPPORTED_BASIN

    offsets6 = _neighbor_offsets(6)
    ridge_mask = _candidate_ridge_mask(estimate, options) & active
    # A sampled continuous ridge need not hit every adjacent logical node. Join
    # derivative-certified candidates through at most two layers of the same
    # high-density supported band; this cannot bridge unsupported cells or a
    # density valley below the declared ridge floor.
    ridge_band = ridge_mask.copy()
    ridge_floor = options.ridge_density_fraction * max_density
    for _ in range(2):
        grown = ridge_band.copy()
        for idx_arr in np.argwhere(ridge_band):
            idx = tuple(int(v) for v in idx_arr)
            for offset in offsets6:
                nxt = _wrapped_neighbor(idx, offset, shape)
                if active[nxt] and rho[nxt] >= ridge_floor:
                    grown[nxt] = True
        ridge_band = grown
    ridge_components = [component for component in _component_nodes(ridge_band, offsets6)
                        if len(component) >= options.minimum_ridge_nodes
                        and np.count_nonzero(ridge_mask.reshape(-1)[component]) >= options.minimum_ridge_nodes
                        and _component_has_cycle(component, shape, offsets6)]
    ridge_node_set = {int(v) for component in ridge_components for v in component}
    plateau_components = _local_maximum_plateaus(rho, active, offsets, options.plateau_relative_tolerance)

    seeds: list[tuple[AttractorGeometry, np.ndarray, str | None]] = []
    for component in ridge_components:
        seeds.append((AttractorGeometry.RIDGE_OR_MANIFOLD, component, None))
    for component in plateau_components:
        remaining = np.asarray([v for v in component if int(v) not in ridge_node_set], dtype=np.int64)
        if remaining.size == 0:
            continue
        representative = int(remaining[np.argmax(rho.reshape(-1)[remaining])])
        hessian = estimate.realization.density_hessian_covariant_dense().reshape(-1, 3, 3)[representative]
        hessian_y = estimate.analysis_metric.hessians_in_orthonormal_chart(hessian[None, :, :])[0]
        eigenvalues = np.linalg.eigvalsh(hessian_y)
        if np.all(eigenvalues < -options.minimum_point_curvature):
            geometry = AttractorGeometry.ISOLATED_MODE
            diagnostic = None
        elif len(remaining) >= options.minimum_ridge_nodes and _component_has_cycle(remaining, shape, offsets6):
            geometry = AttractorGeometry.RIDGE_OR_MANIFOLD
            diagnostic = "plateau_cycle"
        else:
            geometry = AttractorGeometry.FLAT_UNRESOLVED_COMPONENT
            diagnostic = "curvature_not_point_stable"
        seeds.append((geometry, remaining, diagnostic))

    seeds.sort(key=lambda item: (-float(np.max(rho.reshape(-1)[item[1]])), item[0].value, int(np.min(item[1]))))
    if len(seeds) > resources.max_attractors:
        raise DensityAttractorResourceError(f"attractors {len(seeds)}>{resources.max_attractors}")
    seed_owner = np.full(shape, -1, dtype=np.int32)
    for identifier, (_, component, _) in enumerate(seeds):
        seed_owner.reshape(-1)[component] = identifier
    owner, successor = _assign_ascent(rho, active, seed_owner, offsets, options.max_ascent_steps)
    unresolved = active & (owner < 0)
    classes[unresolved] = CellClassification.NUMERICALLY_UNRESOLVED

    # Mark supported basin boundaries as transition regions without allowing them
    # to create ownership through unsupported cells.
    for _ in range(options.transition_boundary_layers):
        boundary = np.zeros(shape, dtype=bool)
        for idx_arr in np.argwhere(active & (owner >= 0)):
            idx = tuple(int(v) for v in idx_arr); current = int(owner[idx])
            for offset in offsets6:
                nxt = _wrapped_neighbor(idx, offset, shape)
                if support[nxt] and int(owner[nxt]) >= 0 and int(owner[nxt]) != current:
                    boundary[idx] = True; break
        classes[boundary] = CellClassification.SUPPORTED_TRANSITION_REGION
    classes[active & (owner >= 0) & (classes != CellClassification.SUPPORTED_TRANSITION_REGION)] = CellClassification.SUPPORTED_BASIN

    voxel_volume = estimate.voxel_volume
    attractors: list[DensityAttractor] = []
    hessian_dense = estimate.realization.density_hessian_covariant_dense().reshape(-1, 3, 3)
    flat_rho = rho.reshape(-1)
    grid_points = np.asarray([np.asarray(_unflat(i, shape), dtype=np.float64) / np.asarray(shape) for i in range(nodes)])
    for identifier, (geometry, component, diagnostic) in enumerate(seeds):
        representative = int(component[np.argmax(flat_rho[component])])
        weights = np.maximum(flat_rho[component], 0.0)
        anchor = _circular_mean(grid_points[component], weights if float(np.sum(weights)) > 0.0 else None)
        eigenvalues = np.sort(np.linalg.eigvalsh(estimate.analysis_metric.hessians_in_orthonormal_chart(hessian_dense[representative][None])[0]))[::-1]
        if geometry is AttractorGeometry.ISOLATED_MODE:
            dimension: int | None = 0
            eigenspace_resolved = bool(np.all(eigenvalues < -options.minimum_point_curvature))
        elif geometry is AttractorGeometry.RIDGE_OR_MANIFOLD:
            dimension = 1
            eigenspace_resolved = bool(eigenvalues[1] < -options.ridge_minimum_normal_curvature)
        else:
            dimension = None
            eigenspace_resolved = False
        basin_probability = float(np.sum(flat_rho[owner.reshape(-1) == identifier]) * voxel_volume)
        chart = _build_charts(geometry, component, anchor, shape, estimate.analysis_metric)
        attractors.append(DensityAttractor(identifier, geometry, anchor, representative, component,
                                            float(flat_rho[representative]), basin_probability, dimension,
                                            eigenvalues, eigenspace_resolved, chart, diagnostic))
    saddles = _build_saddles(owner, rho, support)
    cores = _build_provisional_cores(attractors, owner, classes, rho, saddles, voxel_volume, options, estimate.analysis_metric)
    complex_record = SupportedPeriodicCellComplex(shape, classes, owner, successor, support)
    history = ({"level": 0, "grid_shape": shape, "density_estimate_signature": estimate.signature,
                "active_node_count": int(np.count_nonzero(active)), "supported_node_count": int(np.count_nonzero(support)),
                "method": "complete_periodic_logical_node_complex"},)
    preliminary = DensityAttractorCatalog(
        density_estimate_signature=estimate.signature, domain_signature=estimate.domain.signature,
        covariance_signature=estimate.kernel_covariance.signature, options=options, cell_complex=complex_record,
        attractors=tuple(attractors), saddles=saddles, provisional_cores=cores, topology_certificate=None,
        refinement_history=history,
        metadata={"rendering_used": False, "omitted_sparse_blocks_are_unknown": True,
                  "canonical_backend": "support_restricted_periodic_grid_ascent",
                  "ridge_backend": "derivative_supported_periodic_grid_components",
                  "source_catalog_signature": estimate.catalog_signature},
    )
    certificate = TopologyStabilityCertificate.unassessed(preliminary.signature)
    return DensityAttractorCatalog(
        density_estimate_signature=preliminary.density_estimate_signature, domain_signature=preliminary.domain_signature,
        covariance_signature=preliminary.covariance_signature, options=preliminary.options,
        cell_complex=preliminary.cell_complex, attractors=preliminary.attractors, saddles=preliminary.saddles,
        provisional_cores=preliminary.provisional_cores, topology_certificate=certificate,
        refinement_history=preliminary.refinement_history, metadata=preliminary.metadata,
    )


def match_density_attractor_catalogs(
    source: DensityAttractorCatalog,
    target: DensityAttractorCatalog,
    metric: AnalysisGeometryMetric,
    *,
    minimum_overlap: float = 0.05,
    maximum_distance: float | None = None,
) -> AttractorCorrespondence:
    if source.domain_signature != target.domain_signature:
        raise DensityAttractorInputError("Attractor correspondence requires one registered domain.")
    n_source, n_target = len(source.attractors), len(target.attractors)
    if n_source == 0 or n_target == 0:
        return AttractorCorrespondence(source.signature, target.signature, (), tuple(range(n_source)), tuple(range(n_target)))
    source_owner = source.cell_complex.basin_owner.reshape(-1)
    target_owner = target.cell_complex.basin_owner.reshape(-1)
    same_shape = source.cell_complex.grid_shape == target.cell_complex.grid_shape
    costs = np.full((n_source, n_target), 1.0e9, dtype=np.float64)
    diagnostics: dict[tuple[int, int], tuple[float, float]] = {}
    for i, a in enumerate(source.attractors):
        for j, b in enumerate(target.attractors):
            distance = _metric_distance(a.anchor_fractional, b.anchor_fractional, metric)
            mask_a = source_owner == i
            if same_shape:
                mask_b = target_owner == j
            else:
                source_shape = np.asarray(source.cell_complex.grid_shape, dtype=np.int64)
                target_shape = np.asarray(target.cell_complex.grid_shape, dtype=np.int64)
                source_indices = np.indices(tuple(source_shape), dtype=np.float64).reshape(3, -1).T
                q = source_indices / source_shape
                target_indices = np.mod(np.rint(q * target_shape).astype(np.int64), target_shape)
                sampled_target = target.cell_complex.basin_owner[
                    target_indices[:, 0], target_indices[:, 1], target_indices[:, 2]
                ]
                mask_b = sampled_target == j
            union = int(np.count_nonzero(mask_a | mask_b)); inter = int(np.count_nonzero(mask_a & mask_b))
            overlap = 0.0 if union == 0 else inter / union
            kind_penalty = 0.0 if a.geometry is b.geometry else 1.0
            costs[i, j] = distance + (1.0 - overlap) + kind_penalty
            diagnostics[(i, j)] = (overlap, distance)
    rows, cols = linear_sum_assignment(costs)
    links: list[tuple[int, int, float, float]] = []
    used_source: set[int] = set(); used_target: set[int] = set()
    for i, j in zip(rows, cols, strict=True):
        overlap, distance = diagnostics[(int(i), int(j))]
        distance_ok = maximum_distance is None or distance <= maximum_distance
        if distance_ok and (overlap >= minimum_overlap or not same_shape):
            links.append((int(i), int(j), float(overlap), float(distance)))
            used_source.add(int(i)); used_target.add(int(j))
    return AttractorCorrespondence(source.signature, target.signature, tuple(links),
                                   tuple(sorted(set(range(n_source)) - used_source)),
                                   tuple(sorted(set(range(n_target)) - used_target)))


def prepare_density_attractor_lineage(
    ladder: PeriodicSpeciesDensityLadder,
    *,
    options: DensityAttractorOptions | None = None,
    resources: DensityAttractorResourcePolicy | None = None,
    minimum_overlap: float = 0.05,
) -> tuple[tuple[DensityAttractorCatalog, ...], DensityAttractorLineage]:
    resources = DensityAttractorResourcePolicy() if resources is None else resources
    catalogs = tuple(prepare_density_attractor_catalog(estimate, options=options, resources=resources) for estimate in ladder.estimates)
    pairs = sum(len(a.attractors) * len(b.attractors) for a, b in zip(catalogs[:-1], catalogs[1:]))
    if pairs > resources.max_lineage_pairs:
        raise DensityAttractorResourceError(f"lineage pairs {pairs}>{resources.max_lineage_pairs}")
    correspondences = tuple(match_density_attractor_catalogs(a, b, ladder.estimates[0].analysis_metric,
                                                              minimum_overlap=minimum_overlap)
                            for a, b in zip(catalogs[:-1], catalogs[1:]))
    survival: list[tuple[int, int, int]] = []
    track_id = 0
    active_tracks: dict[tuple[int, int], int] = {}
    for attractor in range(len(catalogs[0].attractors)):
        active_tracks[(0, attractor)] = track_id; survival.append((track_id, 0, 0)); track_id += 1
    for scale, correspondence in enumerate(correspondences):
        linked_targets: set[int] = set()
        for source_id, target_id, _, _ in correspondence.links:
            linked_targets.add(target_id)
            existing = active_tracks.get((scale, source_id))
            if existing is None:
                existing = track_id; survival.append((existing, scale, scale)); track_id += 1
            active_tracks[(scale + 1, target_id)] = existing
            index = next(i for i, item in enumerate(survival) if item[0] == existing)
            survival[index] = (existing, survival[index][1], scale + 1)
        for target_id in range(len(catalogs[scale + 1].attractors)):
            if target_id not in linked_targets:
                active_tracks[(scale + 1, target_id)] = track_id
                survival.append((track_id, scale + 1, scale + 1)); track_id += 1
    ambiguous = any(c.source_unmatched or c.target_unmatched for c in correspondences)
    lineage = DensityAttractorLineage(ladder.signature, tuple(v.signature for v in catalogs), correspondences,
                                      tuple(sorted(survival)), ambiguous)
    return catalogs, lineage


def prepare_scale_consensus(
    catalogs: Sequence[DensityAttractorCatalog],
    lineage: DensityAttractorLineage,
    protocol: SelectionValidationProtocol,
) -> ScaleConsensusResult:
    if tuple(v.signature for v in catalogs) != lineage.catalog_signatures:
        raise DensityAttractorInputError("Scale consensus catalogs do not match the lineage.")
    topologies = [(len(c.attractors), tuple(sorted(a.geometry.value for a in c.attractors)),
                   tuple(sorted(s.basin_pair for s in c.saddles))) for c in catalogs]
    intervals: list[tuple[int, int]] = []
    start = 0
    for i in range(1, len(topologies) + 1):
        if i == len(topologies) or topologies[i] != topologies[start]:
            intervals.append((start, i - 1)); start = i
    max_length = max(b - a + 1 for a, b in intervals)
    best = [interval for interval in intervals if interval[1] - interval[0] + 1 == max_length]
    if len(best) == 1 and max_length >= 2 and not lineage.ambiguous:
        a, b = best[0]; selected_index = (a + b) // 2
        return ScaleConsensusResult(lineage.signature, protocol.signature, ScaleDecisionStatus.RESOLVED,
                                    catalogs[selected_index].signature, tuple(intervals), (),
                                    "unique_topology_stable_bandwidth_interval")
    competing = tuple(c.signature for c in catalogs)
    return ScaleConsensusResult(lineage.signature, protocol.signature, ScaleDecisionStatus.SCALE_AMBIGUOUS,
                                None, tuple(intervals), competing,
                                "spatial_evidence_does_not_select_one_bandwidth_hypothesis")


def certify_topology_refinement(
    catalogs: Sequence[DensityAttractorCatalog],
    metric: AnalysisGeometryMetric,
    *,
    minimum_basin_overlap: float = 0.5,
) -> DensityAttractorRefinementSeries:
    catalogs = tuple(catalogs)
    if len(catalogs) < 2:
        raise DensityAttractorInputError("At least two catalogs are required for refinement certification.")
    correspondences = [match_density_attractor_catalogs(a, b, metric, minimum_overlap=0.0)
                       for a, b in zip(catalogs[:-1], catalogs[1:])]
    count_stable = len({len(c.attractors) for c in catalogs}) == 1
    geometry_stable = len({tuple(sorted(a.geometry.value for a in c.attractors)) for c in catalogs}) == 1
    adjacency_stable = len({tuple(sorted(s.basin_pair for s in c.saddles)) for c in catalogs}) == 1
    overlaps = [overlap for correspondence in correspondences for _, _, overlap, _ in correspondence.links]
    minimum = min(overlaps) if overlaps else 0.0
    stable = count_stable and geometry_stable and adjacency_stable and minimum >= minimum_basin_overlap
    status = TopologyStabilityStatus.STABLE if stable else TopologyStabilityStatus.UNSTABLE
    reasons: list[str] = []
    if not count_stable: reasons.append("attractor_count_changes")
    if not geometry_stable: reasons.append("attractor_geometry_changes")
    if not adjacency_stable: reasons.append("saddle_adjacency_changes")
    if minimum < minimum_basin_overlap: reasons.append("basin_overlap_below_threshold")
    certificate = TopologyStabilityCertificate(status, tuple(c.signature for c in catalogs), count_stable,
                                               geometry_stable, adjacency_stable, minimum, tuple(reasons))
    return DensityAttractorRefinementSeries(tuple(c.signature for c in catalogs),
                                            tuple(c.cell_complex.grid_shape for c in catalogs), certificate)


def compare_periodic_kmeans(
    samples_fractional: FloatArray,
    metric: AnalysisGeometryMetric,
    *,
    n_clusters: int,
    weights: FloatArray | None = None,
    max_iterations: int = 200,
) -> PeriodicClusterComparison:
    samples = np.mod(np.asarray(samples_fractional, dtype=np.float64), 1.0)
    if samples.ndim != 2 or samples.shape[1:] != (3,):
        raise DensityAttractorInputError("samples_fractional must have shape (n,3).")
    n_clusters = _positive_int(n_clusters, "n_clusters")
    if n_clusters > len(samples):
        raise DensityAttractorInputError("n_clusters exceeds sample count.")
    weights_array = np.ones(len(samples), dtype=np.float64) if weights is None else np.asarray(weights, dtype=np.float64)
    if weights_array.shape != (len(samples),) or np.any(weights_array <= 0.0) or np.any(~np.isfinite(weights_array)):
        raise DensityAttractorInputError("weights must be finite, positive, and sample-aligned.")
    centers = [samples[0]]
    while len(centers) < n_clusters:
        distances = np.asarray([min(_metric_distance(point, center, metric) for center in centers) for point in samples])
        centers.append(samples[int(np.argmax(distances))])
    centers_array = np.asarray(centers, dtype=np.float64)
    labels = np.zeros(len(samples), dtype=np.int64)
    for _ in range(max_iterations):
        distance_matrix = np.asarray([[_metric_distance(point, center, metric) for center in centers_array] for point in samples])
        new_labels = np.argmin(distance_matrix, axis=1).astype(np.int64)
        new_centers = centers_array.copy()
        for cluster in range(n_clusters):
            mask = new_labels == cluster
            if np.any(mask):
                new_centers[cluster] = _circular_mean(samples[mask], weights_array[mask])
        if np.array_equal(new_labels, labels) and np.allclose(new_centers, centers_array, rtol=0.0, atol=1e-14):
            labels = new_labels; centers_array = new_centers; break
        labels = new_labels; centers_array = new_centers
    objective = float(sum(weights_array[i] * _metric_distance(samples[i], centers_array[labels[i]], metric) ** 2 for i in range(len(samples))))
    return PeriodicClusterComparison("periodic_kmeans", ClusterComparisonStatus.AVAILABLE, labels, centers_array, objective)


def compare_periodic_hdbscan(
    samples_fractional: FloatArray,
    metric: AnalysisGeometryMetric,
    *,
    min_cluster_size: int = 5,
    weights: FloatArray | None = None,
) -> PeriodicClusterComparison:
    samples = np.mod(np.asarray(samples_fractional, dtype=np.float64), 1.0)
    if samples.ndim != 2 or samples.shape[1:] != (3,):
        raise DensityAttractorInputError("samples_fractional must have shape (n,3).")
    if weights is not None and not np.allclose(weights, np.asarray(weights)[0], rtol=0.0, atol=0.0):
        return PeriodicClusterComparison("periodic_hdbscan", ClusterComparisonStatus.UNSUPPORTED_WEIGHTS,
                                         np.full(len(samples), -1, dtype=np.int64), np.empty((0, 3)), None,
                                         "the optional comparison backend does not accept nonuniform represented-time weights")
    try:
        from sklearn.cluster import HDBSCAN  # type: ignore
    except Exception as exc:
        return PeriodicClusterComparison("periodic_hdbscan", ClusterComparisonStatus.OPTIONAL_DEPENDENCY_UNAVAILABLE,
                                         np.full(len(samples), -1, dtype=np.int64), np.empty((0, 3)), None, str(exc))
    distances = np.zeros((len(samples), len(samples)), dtype=np.float64)
    for i in range(len(samples)):
        for j in range(i + 1, len(samples)):
            value = _metric_distance(samples[i], samples[j], metric)
            distances[i, j] = distances[j, i] = value
    try:
        model = HDBSCAN(min_cluster_size=_positive_int(min_cluster_size, "min_cluster_size"), metric="precomputed")
        labels = np.asarray(model.fit_predict(distances), dtype=np.int64)
        centers: list[np.ndarray] = []
        for label in sorted(int(v) for v in np.unique(labels) if int(v) >= 0):
            centers.append(_circular_mean(samples[labels == label]))
        return PeriodicClusterComparison("periodic_hdbscan", ClusterComparisonStatus.AVAILABLE, labels,
                                         np.asarray(centers, dtype=np.float64).reshape(-1, 3), None)
    except Exception as exc:
        return PeriodicClusterComparison("periodic_hdbscan", ClusterComparisonStatus.FAILED,
                                         np.full(len(samples), -1, dtype=np.int64), np.empty((0, 3)), None, str(exc))


__all__ = [
    "ATTRACTOR_CORRESPONDENCE_SCHEMA", "ATTRACTOR_LOCAL_CHART_SCHEMA", "CLUSTER_COMPARISON_SCHEMA",
    "DENSITY_ATTRACTOR_CATALOG_SCHEMA", "DENSITY_ATTRACTOR_LINEAGE_SCHEMA", "DENSITY_ATTRACTOR_OPTIONS_SCHEMA",
    "DENSITY_ATTRACTOR_SCHEMA", "DENSITY_ATTRACTOR_STAGE", "DENSITY_REFINEMENT_SERIES_SCHEMA",
    "PROVISIONAL_CORE_SCHEMA", "SCALE_CONSENSUS_SCHEMA", "SELECTION_VALIDATION_PROTOCOL_SCHEMA",
    "SUPPORTED_PERIODIC_CELL_COMPLEX_SCHEMA", "SUPPORTED_SADDLE_SCHEMA", "TOPOLOGY_STABILITY_CERTIFICATE_SCHEMA",
    "AttractorCorrespondence", "AttractorGeometry", "AttractorLocalChart", "CellClassification",
    "ClusterComparisonStatus", "CoreDepthSource", "DensityAttractor", "DensityAttractorCatalog",
    "DensityAttractorError", "DensityAttractorInputError", "DensityAttractorLineage", "DensityAttractorOptions",
    "DensityAttractorRefinementSeries", "DensityAttractorResourceError", "DensityAttractorResourcePolicy",
    "DensityAttractorSerializationError", "LocalChartKind", "PeriodicClusterComparison", "ProvisionalCore",
    "ScaleConsensusResult", "ScaleDecisionStatus", "SelectionValidationProtocol", "SupportedPeriodicCellComplex",
    "SupportedSaddle", "TopologyStabilityCertificate", "TopologyStabilityStatus", "certify_topology_refinement",
    "compare_periodic_hdbscan", "compare_periodic_kmeans", "match_density_attractor_catalogs",
    "prepare_density_attractor_catalog", "prepare_density_attractor_lineage", "prepare_scale_consensus",
]
