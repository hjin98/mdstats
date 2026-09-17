"""The sole fitted selector numerical owner: ``TargetCoverageReference``.

Restored from the mature TARGET-DATA2B coverage authority (recovery carrier
``3937881e`` blob ``760d6e9e``) and rebound to the current architecture: the
one fit/reference domain is exact ``P_train``; correlation units are the
current P1 units; structural, pair-geometry and target-development families
are built from authenticated current evidence.  Historical label-domain/fold
fan-out, DATA7 fitted metrics, strata and foundation/profile families that
have no active current provider are not part of this owner.  Hard membership
support is owned by :mod:`obligations`; this module records only the fitted
reference quantities and the represented structural-event support incidence
that obligation construction consumes.

Scientific semantics follow D2 section 3 exactly: correlation-balanced
witness weights normalized once by their binary64 sum, stable weighted
quantiles, the IQR -> q01/q99 -> max(std, 1) robust scale floored at 1e-12,
leave-one-out local radii at ``beta=1/128`` with the ``1e-15`` mass guard, the
inclusive ``d <= r + 1e-12*max(1, r)`` neighborhood, q01/q99 extents and the
``C + 1e-12 >= 0.95`` family predicate.  Worker counts and row blocks are
execution-only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from scipy.spatial import cKDTree

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ..progress_timing import format_progress_fraction
from ..resources import StageResourceScope
from ..work_queue import DeterministicWorkQueue
from .artifact_store import (
    PublishedArtifact,
    TargetOrderArtifactStoreError,
    array_reference,
    packed_slice,
    publish_artifact_directory,
    read_manifest,
    read_packed,
    validate_array_reference,
    write_packed,
)

TARGET_COVERAGE_POLICY_SCHEMA = "mdstats.target-coverage-policy.v2"
TARGET_COVERAGE_EXTENT_SCHEMA = "mdstats.target-coverage-extent.v1"
TARGET_COVERAGE_FAMILY_SCHEMA = "mdstats.target-coverage-family.v3"
TARGET_COVERAGE_REFERENCE_SCHEMA = "mdstats.target-coverage-reference.v4"
TARGET_COVERAGE_FAMILY_REPORT_SCHEMA = "mdstats.target-coverage-family-report.v1"
TARGET_COVERAGE_REPORT_SCHEMA = "mdstats.target-coverage-report.v2"
TARGET_COVERAGE_ARTIFACT_SCHEMA = "mdstats.target-coverage-reference-artifact.v1"
TARGET_COVERAGE_VERSION = "mdstats.target-order.coverage-reference.p-train.v1"

COVERAGE_THRESHOLD = 0.95
COVERAGE_RESOLUTION_MASS = 1.0 / 128.0
EXTENT_QUANTILE_ALPHA = 0.01
METRIC_MINIMUM_SCALE = 1.0e-12
NEIGHBORHOOD_METRIC_TOLERANCE = 1.0e-12

_REFERENCE_METRIC = "scaled_rms_l2"
_FAMILY_KINDS = frozenset({"structural", "pair_geometry", "target_label"})

REQUIRED_STRUCTURAL_FEATURE_FAMILIES = (
    "pair_distance",
    "radial_environment",
    "coordination",
    "connectivity",
    "chemical_environment",
    "local_density",
    "angular_environment",
    "orientational_order",
)
EXTENT_STRUCTURAL_FEATURE_FAMILIES = ("pair_distance", "coordination", "local_density")


def _canonical_array(
    values: np.ndarray | Sequence[Any], *, dtype: str, ndim: int, name: str
) -> np.ndarray:
    target = np.dtype(dtype)
    if target.itemsize > 1:
        target = target.newbyteorder("<")
    array = np.asarray(values, dtype=target)
    if array.ndim != ndim:
        raise TrainingDataInputError(f"{name} must have {ndim} dimensions.")
    array = np.ascontiguousarray(array, dtype=target)
    array.setflags(write=False)
    return array


@dataclass(frozen=True, slots=True)
class TargetCoveragePolicy:
    """Frozen D2 coverage policy; no field is a tuning knob.

    Every value is numerical authority accepted in D2 section 3.  There is no
    active named-family threshold override and no configurable relaxation.
    """

    coverage_metric: str = "reference_mass_local_knn"
    coverage_threshold: float = COVERAGE_THRESHOLD
    coverage_resolution_mass: float = COVERAGE_RESOLUTION_MASS
    coverage_leave_one_out: bool = True
    extent_quantile_alpha: float = EXTENT_QUANTILE_ALPHA
    metric_minimum_scale: float = METRIC_MINIMUM_SCALE
    required_structural_feature_families: tuple[str, ...] = REQUIRED_STRUCTURAL_FEATURE_FAMILIES
    extent_structural_feature_families: tuple[str, ...] = EXTENT_STRUCTURAL_FEATURE_FAMILIES
    minimum_family_elements: int = 2
    policy_version: str = TARGET_COVERAGE_VERSION

    def __post_init__(self) -> None:
        expected = TargetCoveragePolicy.__dataclass_fields__
        for name in (
            "coverage_metric",
            "coverage_threshold",
            "coverage_resolution_mass",
            "coverage_leave_one_out",
            "extent_quantile_alpha",
            "metric_minimum_scale",
            "required_structural_feature_families",
            "extent_structural_feature_families",
            "minimum_family_elements",
            "policy_version",
        ):
            value = getattr(self, name)
            default = expected[name].default
            if isinstance(default, tuple):
                value = tuple(str(item) for item in value)
                object.__setattr__(self, name, value)
            if value != default:
                raise TrainingDataInputError(
                    f"TargetCoveragePolicy.{name} is frozen D2 numerical authority; "
                    f"{value!r} is not the accepted value {default!r}."
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "coverage_metric": self.coverage_metric,
            "coverage_threshold": self.coverage_threshold,
            "coverage_resolution_mass": self.coverage_resolution_mass,
            "coverage_leave_one_out": self.coverage_leave_one_out,
            "extent_quantile_alpha": self.extent_quantile_alpha,
            "metric_minimum_scale": self.metric_minimum_scale,
            "required_structural_feature_families": list(self.required_structural_feature_families),
            "extent_structural_feature_families": list(self.extent_structural_feature_families),
            "minimum_family_elements": self.minimum_family_elements,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoveragePolicy":
        if payload.get("schema") != TARGET_COVERAGE_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported target-coverage policy schema.")
        result = cls(
            coverage_metric=str(payload["coverage_metric"]),
            coverage_threshold=float(payload["coverage_threshold"]),
            coverage_resolution_mass=float(payload["coverage_resolution_mass"]),
            coverage_leave_one_out=bool(payload["coverage_leave_one_out"]),
            extent_quantile_alpha=float(payload["extent_quantile_alpha"]),
            metric_minimum_scale=float(payload["metric_minimum_scale"]),
            required_structural_feature_families=tuple(payload["required_structural_feature_families"]),
            extent_structural_feature_families=tuple(payload["extent_structural_feature_families"]),
            minimum_family_elements=int(payload["minimum_family_elements"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Target-coverage policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageExtentChannel:
    feature_name: str
    feature_index: int
    lower_reference_quantile: float
    upper_reference_quantile: float

    def __post_init__(self) -> None:
        if not self.feature_name.strip() or self.feature_index < 0:
            raise TrainingDataInputError("Target-coverage extent-channel identity is invalid.")
        lower = float(self.lower_reference_quantile)
        upper = float(self.upper_reference_quantile)
        if not np.isfinite(lower) or not np.isfinite(upper) or lower > upper:
            raise TrainingDataInputError("Target-coverage extent bounds are invalid.")
        object.__setattr__(self, "lower_reference_quantile", lower)
        object.__setattr__(self, "upper_reference_quantile", upper)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_COVERAGE_EXTENT_SCHEMA,
            "feature_name": self.feature_name,
            "feature_index": self.feature_index,
            "lower_reference_quantile": self.lower_reference_quantile,
            "upper_reference_quantile": self.upper_reference_quantile,
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageExtentChannel":
        if payload.get("schema") != TARGET_COVERAGE_EXTENT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported target-coverage extent schema.")
        result = cls(
            feature_name=str(payload["feature_name"]),
            feature_index=int(payload["feature_index"]),
            lower_reference_quantile=float(payload["lower_reference_quantile"]),
            upper_reference_quantile=float(payload["upper_reference_quantile"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("Target-coverage extent digest mismatch.")
        return result


_FAMILY_ARRAY_NAMES = ("frame_indices", "values", "weights", "scales", "local_radii")


@dataclass(frozen=True, slots=True, eq=False)
class TargetCoverageFamilyReference:
    """One required multi-view family fitted on exact ``P_train``."""

    family_id: str
    family_kind: str
    semantic_family: str
    feature_names: tuple[str, ...]
    frame_indices: np.ndarray | Sequence[int]
    values: np.ndarray | Sequence[Sequence[float]]
    weights: np.ndarray | Sequence[float]
    scales: np.ndarray | Sequence[float]
    local_radii: np.ndarray | Sequence[float]
    extent_channels: tuple[TargetCoverageExtentChannel, ...]
    source_evidence_digest: str
    _array_references: Mapping[str, Mapping[str, Any]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.family_id.strip() or not self.semantic_family.strip():
            raise TrainingDataInputError("Target-coverage family identifiers must be non-empty.")
        if self.family_kind not in _FAMILY_KINDS:
            raise TrainingDataInputError(f"Unsupported target-coverage family kind {self.family_kind!r}.")
        names = tuple(str(value).strip() for value in self.feature_names)
        if any(not value for value in names) or len(set(names)) != len(names):
            raise TrainingDataInputError("Target-coverage family feature names must be unique and non-empty.")
        indices = _canonical_array(self.frame_indices, dtype="<i8", ndim=1, name="family frame_indices")
        matrix = _canonical_array(self.values, dtype="<f8", ndim=2, name="family values")
        weights = _canonical_array(self.weights, dtype="<f8", ndim=1, name="family weights")
        scales = _canonical_array(self.scales, dtype="<f8", ndim=1, name="family scales")
        radii = _canonical_array(self.local_radii, dtype="<f8", ndim=1, name="family local_radii")
        n, d = matrix.shape
        if n < 2 or d == 0 or len(names) != d:
            raise TrainingDataInputError("Target-coverage family arrays are empty or misaligned.")
        if indices.shape != (n,) or weights.shape != (n,) or radii.shape != (n,):
            raise TrainingDataInputError("Target-coverage family arrays are empty or misaligned.")
        if np.any(indices < 0) or np.unique(indices).size != n:
            raise TrainingDataInputError("Target-coverage family frame indices must be unique and nonnegative.")
        if np.any(~np.isfinite(matrix)):
            raise TrainingDataInputError("Target-coverage family values must be finite.")
        if scales.shape != (d,) or np.any(~np.isfinite(scales)) or np.any(scales <= 0.0):
            raise TrainingDataInputError("Target-coverage family metric scales are invalid.")
        if np.any(~np.isfinite(weights)) or np.any(weights <= 0.0):
            raise TrainingDataInputError("Target-coverage family weights must be positive and finite.")
        if not math.isclose(float(np.sum(weights, dtype=np.float64)), 1.0, rel_tol=1.0e-10, abs_tol=1.0e-12):
            raise TrainingDataInputError("Target-coverage family weights must sum to one.")
        if np.any(~np.isfinite(radii)) or np.any(radii < 0.0):
            raise TrainingDataInputError("Target-coverage local radii must be finite and nonnegative.")
        extents = tuple(self.extent_channels)
        if any(item.feature_index >= d or item.feature_name != names[item.feature_index] for item in extents):
            raise TrainingDataInputError("Target-coverage extent channels are misaligned with family features.")
        object.__setattr__(self, "feature_names", names)
        object.__setattr__(self, "frame_indices", indices)
        object.__setattr__(self, "values", matrix)
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "scales", scales)
        object.__setattr__(self, "local_radii", radii)
        object.__setattr__(self, "extent_channels", extents)
        object.__setattr__(
            self, "source_evidence_digest", validate_digest(self.source_evidence_digest, name="source_evidence_digest")
        )
        object.__setattr__(
            self,
            "_array_references",
            {name: array_reference(getattr(self, name)) for name in _FAMILY_ARRAY_NAMES},
        )

    @property
    def array_references(self) -> Mapping[str, Mapping[str, Any]]:
        return self._array_references

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_FAMILY_SCHEMA,
            "family_id": self.family_id,
            "family_kind": self.family_kind,
            "semantic_family": self.semantic_family,
            "metric": _REFERENCE_METRIC,
            "feature_names": list(self.feature_names),
            "array_references": {name: dict(self._array_references[name]) for name in _FAMILY_ARRAY_NAMES},
            "extent_channels": [item.to_dict() for item in self.extent_channels],
            "source_evidence_digest": self.source_evidence_digest,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TargetCoverageFamilyReference):
            return NotImplemented
        return self.content_digest == other.content_digest

    def __hash__(self) -> int:
        return hash(self.content_digest)


@dataclass(frozen=True, slots=True, eq=False)
class TargetCoverageReference:
    """Frozen correlation-balanced multi-view reference on exact ``P_train``.

    ``frame_uids`` is the one canonical candidate order (sorted current frame
    UIDs); every family ``frame_indices`` addresses it.  Structural-event
    support is recorded as fitted incidence because obligation construction
    must not need the raw descriptor catalog again.
    """

    dataset_id: str
    population_digest: str
    split_digest: str
    raw_feature_catalog_digest: str
    structural_catalog_digest: str
    policy: TargetCoveragePolicy
    frame_uids: tuple[str, ...]
    correlation_unit_ids: tuple[str, ...]
    families: tuple[TargetCoverageFamilyReference, ...]
    structural_event_support: tuple[tuple[str, tuple[int, ...]], ...] = ()
    _family_by_id: Mapping[str, TargetCoverageFamilyReference] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _frame_index_by_uid: Mapping[str, int] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not str(self.dataset_id).strip():
            raise TrainingDataInputError("TargetCoverageReference dataset_id must be non-empty.")
        for name in (
            "population_digest",
            "split_digest",
            "raw_feature_catalog_digest",
            "structural_catalog_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        frames = tuple(validate_digest(value, name="frame_uid") for value in self.frame_uids)
        if len(frames) < 2 or len(set(frames)) != len(frames) or frames != tuple(sorted(frames)):
            raise TrainingDataInputError(
                "TargetCoverageReference requires at least two unique canonically sorted P_train frames."
            )
        units = tuple(validate_digest(value, name="correlation_unit_id") for value in self.correlation_unit_ids)
        if len(units) != len(frames):
            raise TrainingDataInputError("TargetCoverageReference correlation units are misaligned.")
        families = tuple(sorted(self.families, key=lambda item: item.family_id))
        if not families or len({item.family_id for item in families}) != len(families):
            raise TrainingDataInputError("TargetCoverageReference requires unique required families.")
        if any(int(np.max(item.frame_indices)) >= len(frames) for item in families):
            raise TrainingDataInputError("A target-coverage family references a frame outside P_train.")
        events: list[tuple[str, tuple[int, ...]]] = []
        for event_type, indices in sorted(self.structural_event_support):
            rows = tuple(sorted(set(int(value) for value in indices)))
            if not str(event_type).strip() or not rows or rows[0] < 0 or rows[-1] >= len(frames):
                raise TrainingDataInputError("TargetCoverageReference structural-event support is invalid.")
            events.append((str(event_type), rows))
        if len({name for name, _ in events}) != len(events):
            raise TrainingDataInputError("TargetCoverageReference structural-event types must be unique.")
        object.__setattr__(self, "frame_uids", frames)
        object.__setattr__(self, "correlation_unit_ids", units)
        object.__setattr__(self, "families", families)
        object.__setattr__(self, "structural_event_support", tuple(events))
        object.__setattr__(self, "_family_by_id", {item.family_id: item for item in families})
        object.__setattr__(self, "_frame_index_by_uid", {uid: i for i, uid in enumerate(frames)})

    @property
    def candidate_count(self) -> int:
        return len(self.frame_uids)

    @property
    def frame_domain_digest(self) -> str:
        return digest({
            "schema": "mdstats.target-order-frame-domain.v1",
            "split_digest": self.split_digest,
            "frame_uids": list(self.frame_uids),
        })

    def family(self, family_id: str) -> TargetCoverageFamilyReference:
        try:
            return self._family_by_id[family_id]
        except KeyError:
            raise KeyError(family_id) from None

    def frame_index(self, frame_uid: str) -> int:
        try:
            return self._frame_index_by_uid[frame_uid]
        except KeyError:
            raise KeyError(frame_uid) from None

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_REFERENCE_SCHEMA,
            "coverage_version": TARGET_COVERAGE_VERSION,
            "dataset_id": self.dataset_id,
            "population_digest": self.population_digest,
            "split_digest": self.split_digest,
            "raw_feature_catalog_digest": self.raw_feature_catalog_digest,
            "structural_catalog_digest": self.structural_catalog_digest,
            "policy": self.policy.to_dict(),
            "frame_domain_digest": self.frame_domain_digest,
            "correlation_unit_ids_digest": digest(list(self.correlation_unit_ids)),
            "family_digests": [item.content_digest for item in self.families],
            "structural_event_support": [[name, list(rows)] for name, rows in self.structural_event_support],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TargetCoverageReference):
            return NotImplemented
        return self.content_digest == other.content_digest

    def __hash__(self) -> int:
        return hash(self.content_digest)


# --- weighted statistics ---------------------------------------------------


def _weighted_quantiles(values: np.ndarray, weights: np.ndarray, quantiles: Sequence[float]) -> np.ndarray:
    """First value in stable ascending order whose cumulative weight reaches q."""

    values = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    requested = np.asarray(tuple(float(value) for value in quantiles), dtype=np.float64)
    if (
        values.ndim != 1
        or weights.shape != values.shape
        or values.size == 0
        or requested.ndim != 1
        or requested.size == 0
        or np.any(~np.isfinite(values))
        or np.any(~np.isfinite(weights))
        or np.any(weights < 0.0)
        or np.any(~np.isfinite(requested))
        or np.any(requested < 0.0)
        or np.any(requested > 1.0)
    ):
        raise TrainingDataInputError("Weighted quantile inputs are invalid.")
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    cumulative = np.cumsum(weights[order], dtype=np.float64)
    total = float(cumulative[-1])
    if not np.isfinite(total) or total <= 0.0:
        raise TrainingDataInputError("Weighted quantile weights have no positive mass.")
    indices = np.searchsorted(cumulative, requested, side="left")
    indices = np.minimum(indices, sorted_values.size - 1)
    return np.asarray(sorted_values[indices], dtype=np.float64)


@dataclass(frozen=True, slots=True)
class _WeightedColumnStatistics:
    scales: np.ndarray
    lower_extents: np.ndarray | None
    upper_extents: np.ndarray | None


def _weighted_column_statistics(
    values: np.ndarray, weights: np.ndarray, *, minimum: float, extent_alpha: float | None = None
) -> _WeightedColumnStatistics:
    matrix = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if matrix.ndim != 2 or weights.shape != (matrix.shape[0],):
        raise TrainingDataInputError("Weighted column-statistic inputs are invalid.")
    scales = np.empty(matrix.shape[1], dtype=np.float64)
    lower = None if extent_alpha is None else np.empty(matrix.shape[1], dtype=np.float64)
    upper = None if extent_alpha is None else np.empty(matrix.shape[1], dtype=np.float64)
    for column in range(matrix.shape[1]):
        quantiles = [0.01, 0.25, 0.75, 0.99]
        if extent_alpha is not None:
            quantiles.extend((float(extent_alpha), 1.0 - float(extent_alpha)))
        unique = tuple(sorted(set(quantiles)))
        by_quantile = dict(zip(unique, _weighted_quantiles(matrix[:, column], weights, unique)))
        scale = float(by_quantile[0.75] - by_quantile[0.25])
        if not np.isfinite(scale) or scale <= minimum:
            scale = float(by_quantile[0.99] - by_quantile[0.01])
        if not np.isfinite(scale) or scale <= minimum:
            scale = max(float(np.std(matrix[:, column])), 1.0)
        scales[column] = max(scale, minimum)
        if lower is not None and upper is not None and extent_alpha is not None:
            lower[column] = by_quantile[float(extent_alpha)]
            upper[column] = by_quantile[1.0 - float(extent_alpha)]
    return _WeightedColumnStatistics(scales, lower, upper)


def correlation_balanced_weights(unit_ids: Sequence[str]) -> np.ndarray:
    """Equal mass per represented P1 unit, equal mass per witness in a unit."""

    grouped: dict[str, list[int]] = {}
    for row, unit_id in enumerate(unit_ids):
        grouped.setdefault(str(unit_id), []).append(row)
    if not grouped:
        raise TrainingDataInputError("A target-coverage family has no represented correlation unit.")
    weights = np.zeros(len(unit_ids), dtype=np.float64)
    unit_mass = 1.0 / len(grouped)
    for rows in grouped.values():
        weights[np.asarray(rows, dtype=np.int64)] = unit_mass / len(rows)
    weights /= np.sum(weights, dtype=np.float64)
    return weights


@dataclass(slots=True)
class _WeightProfileCache:
    """Execution-only reuse of identical witness-weight profiles across families."""

    profiles: dict[tuple[int, ...], np.ndarray] = field(default_factory=dict)

    def resolve(self, frame_indices: np.ndarray, unit_ids: Sequence[str]) -> np.ndarray:
        key = tuple(int(value) for value in frame_indices)
        cached = self.profiles.get(key)
        if cached is None:
            cached = correlation_balanced_weights([unit_ids[index] for index in key])
            cached.setflags(write=False)
            self.profiles[key] = cached
        return cached


# --- local reference radii (exact, block-parallel) -------------------------


def _uniform_reference_rank(weights: np.ndarray, *, beta: float, leave_one_out: bool) -> int | None:
    weights = np.asarray(weights, dtype=np.float64)
    if weights.ndim != 1 or weights.size < 2 or not np.all(weights == weights[0]):
        return None
    if leave_one_out:
        denominator = 1.0 - float(weights[0])
        count = weights.size - 1
    else:
        denominator = 1.0
        count = weights.size
    if denominator <= 0.0:
        raise TrainingDataInputError("Uniform local-radius reference is degenerate.")
    increments = np.full(count, float(weights[0]) / denominator, dtype=np.float64)
    cumulative = np.cumsum(increments, dtype=np.float64)
    index = int(np.searchsorted(cumulative, float(beta) - 1.0e-15, side="left"))
    if index >= count:
        if cumulative[-1] + 1.0e-12 < beta:
            raise TrainingDataInputError("Local-radius mass target cannot be reached.")
        index = count - 1
    return index + 1


def _local_reference_radii_uniform_block(
    tree: cKDTree, points: np.ndarray, *, start: int, stop: int, rank: int, leave_one_out: bool, query_workers: int
) -> tuple[int, np.ndarray]:
    n, dim = points.shape
    query_k = min(n, rank + (1 if leave_one_out else 0))
    rows = np.arange(start, stop, dtype=np.int64)
    distances, neighbors = tree.query(points[rows], k=query_k, workers=query_workers)
    if query_k == 1:
        distances = np.asarray(distances, dtype=np.float64)[:, None]
        neighbors = np.asarray(neighbors, dtype=np.int64)[:, None]
    else:
        distances = np.asarray(distances, dtype=np.float64)
        neighbors = np.asarray(neighbors, dtype=np.int64)
    valid = np.isfinite(distances) & (neighbors >= 0) & (neighbors < n)
    if leave_one_out:
        valid &= neighbors != rows[:, None]
    valid_rank = np.cumsum(valid, axis=1)
    reached = valid & (valid_rank == rank)
    if np.any(~np.any(reached, axis=1)):
        raise TrainingDataInputError("Uniform neighbor rank cannot be resolved.")
    hit = np.argmax(reached, axis=1)
    block = distances[np.arange(rows.size), hit] / math.sqrt(float(dim))
    return int(start), np.asarray(block, dtype=np.float64)


def _local_reference_radii_weighted_block(
    tree: cKDTree,
    points: np.ndarray,
    weights: np.ndarray,
    *,
    start: int,
    stop: int,
    beta: float,
    leave_one_out: bool,
    query_workers: int,
) -> tuple[int, np.ndarray]:
    n, dim = points.shape
    k = min(n, max(8, int(math.ceil(beta * n * 1.5)) + 2))
    norm = math.sqrt(float(dim))
    block = np.empty(stop - start, dtype=np.float64)
    pending = np.arange(start, stop, dtype=np.int64)
    while pending.size:
        distances, neighbors = tree.query(points[pending], k=k, workers=query_workers)
        if k == 1:
            distances = distances[:, None]
            neighbors = neighbors[:, None]
        distances = np.asarray(distances, dtype=np.float64)
        neighbors = np.asarray(neighbors, dtype=np.int64)
        valid = np.isfinite(distances) & (neighbors >= 0) & (neighbors < n)
        if leave_one_out:
            valid &= neighbors != pending[:, None]
            denominators = 1.0 - weights[pending]
        else:
            denominators = np.ones(pending.size, dtype=np.float64)
        if np.any(denominators <= 0.0) or np.any(~np.any(valid, axis=1)):
            raise TrainingDataInputError("Local-radius reference is degenerate.")
        safe_neighbors = np.where(valid, neighbors, 0)
        neighbor_mass = np.where(valid, weights[safe_neighbors], 0.0)
        cumulative = np.cumsum(neighbor_mass / denominators[:, None], axis=1)
        reached = cumulative >= beta - 1.0e-15
        resolved = np.any(reached, axis=1)
        if np.any(resolved):
            rows = np.flatnonzero(resolved)
            first_hit = np.argmax(reached[rows], axis=1)
            block[pending[rows] - start] = distances[rows, first_hit] / norm
        unresolved_rows = np.flatnonzero(~resolved)
        if unresolved_rows.size == 0:
            break
        if k >= n:
            tails = cumulative[unresolved_rows, -1]
            if np.any(tails + 1.0e-12 < beta):
                raise TrainingDataInputError("Local-radius mass target cannot be reached.")
            block[pending[unresolved_rows] - start] = distances[unresolved_rows, -1] / norm
            break
        pending = pending[unresolved_rows]
        k = min(n, max(k + 1, k * 2))
    return int(start), block


def _covref_parallel_block_size(*, n: int, query_k: int, configured_block_size: int, workers: int) -> int:
    configured = max(1, int(configured_block_size))
    rows = max(1, int(n))
    k = max(1, int(query_k))
    memory_rows = max(64, (2 * 1024 * 1024) // max(1, k * 48))
    occupancy_rows = max(64, int(math.ceil(rows / max(1, int(workers) * 4))))
    return max(1, min(configured, memory_rows, occupancy_rows, rows))


def local_reference_radii(
    values: np.ndarray,
    weights: np.ndarray,
    *,
    beta: float = COVERAGE_RESOLUTION_MASS,
    leave_one_out: bool = True,
    block_size: int = 1024,
    query_workers: int = 1,
    work_queue: DeterministicWorkQueue | None = None,
    task_prefix: str = "target-coverage",
) -> np.ndarray:
    """Exact leave-one-out fixed-reference-mass radii on scaled coordinates.

    ``work_queue`` activates single-level block parallelism over one shared
    tree; row results are independent of block boundaries.
    """

    points = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if points.ndim != 2 or weights.shape != (points.shape[0],):
        raise TrainingDataInputError("Local-radius arrays are misaligned.")
    n, _ = points.shape
    if n < 2:
        raise TrainingDataInputError("Local radii require at least two elements.")
    if int(query_workers) < 1:
        raise TrainingDataInputError("query_workers must be positive.")
    tree = cKDTree(points)
    radii = np.empty(n, dtype=np.float64)
    rank = _uniform_reference_rank(weights, beta=beta, leave_one_out=leave_one_out)
    if rank is not None:
        query_k = min(n, int(rank) + (1 if leave_one_out else 0))
    else:
        query_k = min(n, max(8, int(math.ceil(beta * n * 1.5)) + 2))
    tasks: list[tuple[int, int]] = []
    if work_queue is None:
        row_block = max(1, int(block_size))
        workers = int(query_workers)
    else:
        row_block = _covref_parallel_block_size(
            n=n, query_k=query_k, configured_block_size=block_size, workers=work_queue.allocated_workers
        )
        workers = 1
    tasks = [(start, min(n, start + row_block)) for start in range(0, n, row_block)]

    def run(start: int, stop: int) -> tuple[int, np.ndarray]:
        if rank is not None:
            return _local_reference_radii_uniform_block(
                tree, points, start=start, stop=stop, rank=int(rank), leave_one_out=leave_one_out, query_workers=workers
            )
        return _local_reference_radii_weighted_block(
            tree, points, weights, start=start, stop=stop, beta=beta, leave_one_out=leave_one_out, query_workers=workers
        )

    if work_queue is None:
        for start, stop in tasks:
            block_start, block = run(start, stop)
            radii[block_start:block_start + block.size] = block
        return radii
    next_submit = 0
    completed = 0
    while completed < len(tasks):
        while next_submit < len(tasks) and work_queue.can_submit():
            start, stop = tasks[next_submit]
            work_queue.submit(
                task_id=f"{task_prefix}:radius:{next_submit:08d}",
                canonical_order=(next_submit,),
                function=run,
                args=(start, stop),
                task_kind="target-coverage-reference-radius",
                estimated_memory_bytes=int(max(1, stop - start) * max(1, query_k) * 48 + max(1, stop - start) * 128),
                locality_key=task_prefix,
            )
            next_submit += 1
        work_queue.wait_for_completion()
        for completion in work_queue.drain_completed():
            block_start, block = completion.value
            radii[int(block_start):int(block_start) + block.size] = np.asarray(block, dtype=np.float64)
            completed += 1
    if next_submit != len(tasks) or work_queue.has_outstanding_work:
        raise RuntimeError("Target-coverage radius queue did not drain exactly.")
    return radii


def local_reference_radii_dense_exact(
    values: np.ndarray, weights: np.ndarray, *, beta: float = COVERAGE_RESOLUTION_MASS, leave_one_out: bool = True
) -> np.ndarray:
    """Bounded dense exact radius oracle used only for qualification."""

    points = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    n, dim = points.shape
    norm = math.sqrt(float(dim))
    result = np.empty(n, dtype=np.float64)
    delta = points[:, None, :] - points[None, :, :]
    distances = np.sqrt(np.sum(delta * delta, axis=2, dtype=np.float64))
    for row in range(n):
        valid = np.ones(n, dtype=np.bool_)
        denominator = 1.0
        if leave_one_out:
            valid[row] = False
            denominator = 1.0 - weights[row]
        order = np.argsort(distances[row], kind="mergesort")
        order = order[valid[order]]
        cumulative = np.cumsum(weights[order] / denominator, dtype=np.float64)
        hit = int(np.searchsorted(cumulative, beta - 1.0e-15, side="left"))
        if hit >= order.size:
            raise TrainingDataInputError("Dense local-radius mass target cannot be reached.")
        result[row] = distances[row, order[hit]] / norm
    return result


@dataclass(frozen=True, slots=True)
class _BuildContext:
    frame_uids: tuple[str, ...]
    unit_ids: tuple[str, ...]
    policy: TargetCoveragePolicy
    weight_cache: _WeightProfileCache
    radius_block_size: int
    query_workers: int
    radius_queue: DeterministicWorkQueue | None


def _build_family(
    context: _BuildContext,
    *,
    family_id: str,
    family_kind: str,
    semantic_family: str,
    feature_names: Sequence[str],
    frame_indices: Sequence[int],
    values: np.ndarray,
    source_evidence_digest: str,
    extent: bool,
) -> TargetCoverageFamilyReference | None:
    names = tuple(feature_names)
    matrix = np.asarray(values, dtype=np.float64)
    if matrix.ndim == 1:
        matrix = matrix[:, None]
    indices = np.asarray(tuple(int(value) for value in frame_indices), dtype=np.int64)
    if matrix.shape != (indices.size, len(names)):
        raise TrainingDataInputError("Target-coverage family builder received misaligned values.")
    if indices.size < context.policy.minimum_family_elements:
        return None
    if np.any(~np.isfinite(matrix)):
        raise TrainingDataInputError("Target-coverage family values must be finite.")
    weights = context.weight_cache.resolve(indices, context.unit_ids)
    statistics = _weighted_column_statistics(
        matrix,
        weights,
        minimum=context.policy.metric_minimum_scale,
        extent_alpha=context.policy.extent_quantile_alpha if extent else None,
    )
    scaled = matrix / statistics.scales[None, :]
    radii = local_reference_radii(
        scaled,
        weights,
        beta=context.policy.coverage_resolution_mass,
        leave_one_out=context.policy.coverage_leave_one_out,
        block_size=context.radius_block_size,
        query_workers=context.query_workers,
        work_queue=context.radius_queue,
        task_prefix=family_id,
    )
    channels: list[TargetCoverageExtentChannel] = []
    if extent:
        assert statistics.lower_extents is not None and statistics.upper_extents is not None
        for column, name in enumerate(names):
            channels.append(
                TargetCoverageExtentChannel(
                    feature_name=name,
                    feature_index=column,
                    lower_reference_quantile=float(statistics.lower_extents[column]),
                    upper_reference_quantile=float(statistics.upper_extents[column]),
                )
            )
    return TargetCoverageFamilyReference(
        family_id=family_id,
        family_kind=family_kind,
        semantic_family=semantic_family,
        feature_names=names,
        frame_indices=indices,
        values=matrix,
        weights=weights,
        scales=statistics.scales,
        local_radii=radii,
        extent_channels=tuple(channels),
        source_evidence_digest=source_evidence_digest,
    )


def _structural_feature_name_parts(name: str) -> tuple[str, str, str] | None:
    if not name.startswith("group:"):
        return None
    body = name[len("group:"):]
    try:
        left, statistic = body.rsplit(":", 1)
        group_id, base_feature = left.rsplit(":", 1)
    except ValueError:
        return None
    if statistic not in {"mean", "std", "min", "max", "q10", "q50", "q90"}:
        return None
    return group_id, base_feature, statistic


def structural_feature_family(base_feature: str) -> str | None:
    """Map one accepted universal structural feature to its semantic family."""

    if base_feature.startswith("radial_density_"):
        return "radial_environment"
    if base_feature.startswith("angular_legendre_"):
        return "angular_environment"
    if base_feature.startswith("bond_orientational_"):
        return "orientational_order"
    if base_feature in {
        "nearest_neighbor_distance_angstrom",
        "weighted_neighbor_distance_mean_angstrom",
        "weighted_neighbor_distance_std_angstrom",
    }:
        return "pair_distance"
    if base_feature == "smooth_coordination":
        return "coordination"
    if base_feature in {"hard_neighbor_count", "weighted_degree_l2"}:
        return "connectivity"
    if base_feature == "neighbor_species_entropy":
        return "chemical_environment"
    if base_feature == "local_number_density_angstrom^-3":
        return "local_density"
    return None


def _structural_families(context: _BuildContext, structural_catalog: Any, progress: Callable[[str], None] | None):
    table = structural_catalog.frame_descriptor_table
    index_by_uid = {uid: i for i, uid in enumerate(context.frame_uids)}
    selected_rows = np.fromiter(
        (row for row, uid in enumerate(table.frame_uids) if uid in index_by_uid), dtype=np.int64
    )
    required = set(context.policy.required_structural_feature_families)
    extent = set(context.policy.extent_structural_feature_families)
    by_key: dict[tuple[str, str], list[int]] = {}
    for column, name in enumerate(table.feature_names):
        parts = _structural_feature_name_parts(name)
        if parts is None:
            continue
        group_id, base_feature, _ = parts
        semantic = structural_feature_family(base_feature)
        if semantic is None or semantic not in required:
            continue
        by_key.setdefault((group_id, semantic), []).append(column)
    provider_key = structural_catalog.provider_identity.content_digest
    keys = sorted(by_key)
    result: list[TargetCoverageFamilyReference] = []
    for number, (group_id, semantic) in enumerate(keys, start=1):
        columns = np.asarray(by_key[(group_id, semantic)], dtype=np.int64)
        missing = table.missing_mask[np.ix_(selected_rows, columns)]
        rows = selected_rows[~np.any(missing, axis=1)]
        names = tuple(table.feature_names[int(column)] for column in columns)
        family_key = digest({
            "provider": provider_key,
            "group": group_id,
            "semantic_family": semantic,
            "features": list(names),
        })[:16]
        if progress is not None:
            progress(
                f"structural family; progress={format_progress_fraction(number, len(keys))}; "
                f"family={semantic}/{group_id}; reference_elements={rows.size:,}"
            )
        family = _build_family(
            context,
            family_id=f"structural:{semantic}:{group_id}:{family_key}",
            family_kind="structural",
            semantic_family=semantic,
            feature_names=names,
            frame_indices=[index_by_uid[table.frame_uids[int(row)]] for row in rows],
            values=table.values[np.ix_(rows, columns)],
            source_evidence_digest=structural_catalog.content_digest,
            extent=semantic in extent,
        )
        if family is not None:
            result.append(family)
    return result


_PAIR_FAMILY_SPECS = (
    (
        "bond_length_distribution",
        (
            "minimum_pair_distance_angstrom",
            "mean_nearest_neighbor_distance_angstrom",
            "maximum_nearest_neighbor_distance_angstrom",
        ),
    ),
    ("coordination_distribution", ("coordination_mean", "coordination_maximum")),
)


def _pair_families(context: _BuildContext, raw_features: Any):
    pair_by_rule = [
        {item.rule_id: item for item in raw_features.for_frame(uid).pair_geometry_statistics}
        for uid in context.frame_uids
    ]
    rule_ids = sorted({rule_id for mapping in pair_by_rule for rule_id in mapping})
    result: list[TargetCoverageFamilyReference] = []
    for rule_id in rule_ids:
        for semantic, feature_names in _PAIR_FAMILY_SPECS:
            indices: list[int] = []
            rows: list[tuple[float, ...]] = []
            for index, mapping in enumerate(pair_by_rule):
                match = mapping.get(rule_id)
                if match is None:
                    continue
                values = tuple(getattr(match, name) for name in feature_names)
                if any(value is None for value in values):
                    continue
                indices.append(index)
                rows.append(tuple(float(value) for value in values))
            if not rows:
                continue
            family = _build_family(
                context,
                family_id=f"pair:{rule_id}:{semantic}",
                family_kind="pair_geometry",
                semantic_family=semantic,
                feature_names=feature_names,
                frame_indices=indices,
                values=np.asarray(rows, dtype=np.float64),
                source_evidence_digest=raw_features.content_digest,
                extent=True,
            )
            if family is not None:
                result.append(family)
    return result


_SCALAR_TARGET_SPECS = (
    ("target_label:energy_per_atom", "energy_per_atom_ev"),
    ("target_label:instantaneous_temperature", "instantaneous_temperature_kelvin"),
    ("target_label:hydrostatic_strain", "hydrostatic_strain"),
    ("target_label:deviatoric_strain", "deviatoric_strain_norm"),
    ("target_label:pressure", "pressure_ev_per_angstrom3"),
    ("target_label:stress_deviatoric", "stress_deviatoric_norm_ev_per_angstrom3"),
)


def _target_label_families(context: _BuildContext, raw_features: Any):
    records = [raw_features.for_frame(uid) for uid in context.frame_uids]
    result: list[TargetCoverageFamilyReference] = []
    force_names = [
        "force_component_rms_ev_per_angstrom",
        "force_norm_mean_ev_per_angstrom",
        "force_norm_max_ev_per_angstrom",
    ]
    quantile_names = sorted({key for record in records for key, _ in record.force_norm_quantiles_ev_per_angstrom})
    force_names.extend(f"force_norm_{name}_ev_per_angstrom" for name in quantile_names)
    force_indices: list[int] = []
    force_rows: list[tuple[float, ...]] = []
    for index, record in enumerate(records):
        quantiles = dict(record.force_norm_quantiles_ev_per_angstrom)
        values = (
            record.force_component_rms_ev_per_angstrom,
            record.force_norm_mean_ev_per_angstrom,
            record.force_norm_max_ev_per_angstrom,
            *(quantiles.get(name) for name in quantile_names),
        )
        if any(value is None for value in values):
            continue
        force_indices.append(index)
        force_rows.append(tuple(float(value) for value in values))
    if force_rows:
        family = _build_family(
            context,
            family_id="target_label:force_distribution",
            family_kind="target_label",
            semantic_family="force_tail",
            feature_names=force_names,
            frame_indices=force_indices,
            values=np.asarray(force_rows, dtype=np.float64),
            source_evidence_digest=raw_features.content_digest,
            extent=True,
        )
        if family is not None:
            result.append(family)
    for family_id, feature_name in _SCALAR_TARGET_SPECS:
        indices = [index for index, record in enumerate(records) if getattr(record, feature_name) is not None]
        scalar = np.asarray(
            [(float(getattr(records[index], feature_name)),) for index in indices], dtype=np.float64
        ).reshape(-1, 1)
        # D2: a constant optional scalar family is omitted rather than
        # creating a zero-information dimension.
        if scalar.size == 0 or np.allclose(scalar[:, 0], scalar[0, 0]):
            continue
        family = _build_family(
            context,
            family_id=family_id,
            family_kind="target_label",
            semantic_family=feature_name,
            feature_names=(feature_name,),
            frame_indices=indices,
            values=scalar,
            source_evidence_digest=raw_features.content_digest,
            extent=True,
        )
        if family is not None:
            result.append(family)
    return result


def build_target_coverage_reference(
    *,
    dataset_id: str,
    population: Any,
    split: Any,
    raw_feature_catalog: Any,
    structural_catalog: Any,
    policy: TargetCoveragePolicy | None = None,
    query_workers: int = 1,
    radius_block_size: int = 1024,
    execution_scope: StageResourceScope | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> TargetCoverageReference:
    """Fit the sole selector reference on exact ``P_train``.

    ``population``/``split`` are the current P2 population and exact split;
    the raw feature catalog is the authenticated P1 neutral evidence and the
    structural catalog is the built-in universal structural provider output.
    ``execution_scope`` enables single-level radius block parallelism.
    """

    active = TargetCoveragePolicy() if policy is None else policy
    if split.population_digest != population.content_digest:
        raise TrainingDataInputError("TargetCoverageReference population/split lineage mismatch.")
    frame_uids = tuple(sorted(split.training_frame_uids))
    unit_ids = tuple(population.frame(uid).unit_id for uid in frame_uids)
    missing_raw = [uid for uid in frame_uids if uid not in raw_feature_catalog._by_frame_uid]
    if missing_raw:
        raise TrainingDataInputError("Raw feature evidence does not cover exact P_train.")
    table_uids = set(structural_catalog.frame_descriptor_table.frame_uids)
    if any(uid not in table_uids for uid in frame_uids):
        raise TrainingDataInputError("Universal structural evidence does not cover exact P_train.")
    if execution_scope is not None and int(query_workers) != 1:
        raise TrainingDataInputError(
            "A block-parallel reference build requires query_workers=1 (single-level parallelism)."
        )

    def build(queue: DeterministicWorkQueue | None) -> tuple[TargetCoverageFamilyReference, ...]:
        context = _BuildContext(
            frame_uids=frame_uids,
            unit_ids=unit_ids,
            policy=active,
            weight_cache=_WeightProfileCache(),
            radius_block_size=max(1, int(radius_block_size)),
            query_workers=int(query_workers),
            radius_queue=queue,
        )
        families: list[TargetCoverageFamilyReference] = []
        families.extend(_structural_families(context, structural_catalog, progress_callback))
        families.extend(_pair_families(context, raw_feature_catalog))
        families.extend(_target_label_families(context, raw_feature_catalog))
        return tuple(families)

    if execution_scope is None:
        families = build(None)
        if progress_callback is not None:
            progress_callback(
                "stage=target-coverage-reference; execution=serial; "
                f"radius_block_size={max(1, int(radius_block_size))}; query_workers={int(query_workers)}"
            )
    else:
        width = max(2, 2 * int(execution_scope.python_workers))
        with DeterministicWorkQueue(
            execution_scope,
            max_ready_tasks=width,
            max_inflight_tasks=width,
            max_completed_tasks=width,
            thread_name_prefix="mdstats-covref",
        ) as queue:
            families = build(queue)
            # COVREF-PAR1 admission accounting: the stage budget and what the
            # deterministic queue actually admitted against it.
            snapshot = queue.snapshot()
        if progress_callback is not None:
            progress_callback(
                f"stage=target-coverage-reference; execution=covref-par1; {execution_scope.summary()}; "
                f"radius_block_size={max(1, int(radius_block_size))}; query_workers={int(query_workers)}; "
                f"queue_lanes={snapshot.allocated_workers}; queue_max_busy={snapshot.max_busy_workers}; "
                f"queue_peak_accounted_bytes={snapshot.peak_accounted_memory_bytes}; "
                f"queue_memory_budget_bytes={snapshot.memory_budget_bytes}; "
                f"queue_memory_backpressure={snapshot.memory_backpressure_events}; "
                f"queue_backpressure={snapshot.queue_backpressure_events}; "
                f"queue_tasks={snapshot.committed_tasks}"
            )
    represented = {item.semantic_family for item in families if item.family_kind == "structural"}
    missing_structural = [name for name in active.required_structural_feature_families if name not in represented]
    if missing_structural:
        raise TrainingDataInputError(
            "Exact P_train retains no valid reference family for required universal structural "
            f"semantic families {missing_structural}; the frozen family catalog is not thinned."
        )
    index_by_uid = {uid: i for i, uid in enumerate(frame_uids)}
    by_event: dict[str, set[int]] = {}
    for event in structural_catalog.events:
        index = index_by_uid.get(event.current_frame_uid)
        if index is not None:
            by_event.setdefault(str(event.event_type), set()).add(index)
    return TargetCoverageReference(
        dataset_id=str(dataset_id),
        population_digest=population.content_digest,
        split_digest=split.content_digest,
        raw_feature_catalog_digest=raw_feature_catalog.content_digest,
        structural_catalog_digest=structural_catalog.content_digest,
        policy=active,
        frame_uids=frame_uids,
        correlation_unit_ids=unit_ids,
        families=families,
        structural_event_support=tuple((name, tuple(sorted(rows))) for name, rows in by_event.items()),
    )


# --- independent direct coverage scoring -----------------------------------


@dataclass(frozen=True, slots=True)
class TargetCoverageFamilyReport:
    family_id: str
    reference_element_count: int
    representative_element_count: int
    covered_reference_mass: float
    threshold: float
    coverage_passed: bool
    extent_passed: bool
    extent_failures: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_COVERAGE_FAMILY_REPORT_SCHEMA,
            "family_id": self.family_id,
            "reference_element_count": self.reference_element_count,
            "representative_element_count": self.representative_element_count,
            "covered_reference_mass": self.covered_reference_mass,
            "threshold": self.threshold,
            "coverage_passed": self.coverage_passed,
            "extent_passed": self.extent_passed,
            "extent_failures": list(self.extent_failures),
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageFamilyReport":
        if payload.get("schema") != TARGET_COVERAGE_FAMILY_REPORT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported target-coverage family-report schema.")
        result = cls(
            family_id=str(payload["family_id"]),
            reference_element_count=int(payload["reference_element_count"]),
            representative_element_count=int(payload["representative_element_count"]),
            covered_reference_mass=float(payload["covered_reference_mass"]),
            threshold=float(payload["threshold"]),
            coverage_passed=bool(payload["coverage_passed"]),
            extent_passed=bool(payload["extent_passed"]),
            extent_failures=tuple(str(value) for value in payload.get("extent_failures", ())),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("Target-coverage family-report digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageReport:
    reference_digest: str
    selected_count: int
    selected_frame_uids_digest: str
    family_reports: tuple[TargetCoverageFamilyReport, ...]

    @property
    def passed(self) -> bool:
        return all(item.coverage_passed and item.extent_passed for item in self.family_reports)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_REPORT_SCHEMA,
            "reference_digest": self.reference_digest,
            "selected_count": self.selected_count,
            "selected_frame_uids_digest": self.selected_frame_uids_digest,
            "family_reports": [item.to_dict() for item in self.family_reports],
            "passed": self.passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}


def _family_report(
    family: TargetCoverageFamilyReference,
    *,
    selected_rows: np.ndarray,
    nearest_distance: np.ndarray,
    selected_minimum: np.ndarray,
    selected_maximum: np.ndarray,
    threshold: float,
) -> TargetCoverageFamilyReport:
    if selected_rows.size == 0:
        return TargetCoverageFamilyReport(
            family_id=family.family_id,
            reference_element_count=len(family.values),
            representative_element_count=0,
            covered_reference_mass=0.0,
            threshold=threshold,
            coverage_passed=False,
            extent_passed=not family.extent_channels,
            extent_failures=tuple(
                f"{item.feature_name}:{side}" for item in family.extent_channels for side in ("lower", "upper")
            ),
        )
    radii = np.asarray(family.local_radii, dtype=np.float64)
    covered = nearest_distance <= radii + NEIGHBORHOOD_METRIC_TOLERANCE * np.maximum(1.0, radii)
    mass = float(np.sum(np.asarray(family.weights, dtype=np.float64)[covered], dtype=np.float64))
    failures: list[str] = []
    for channel in family.extent_channels:
        if selected_minimum[channel.feature_index] > channel.lower_reference_quantile + 1.0e-12:
            failures.append(f"{channel.feature_name}:lower")
        if selected_maximum[channel.feature_index] < channel.upper_reference_quantile - 1.0e-12:
            failures.append(f"{channel.feature_name}:upper")
    return TargetCoverageFamilyReport(
        family_id=family.family_id,
        reference_element_count=len(family.values),
        representative_element_count=int(selected_rows.size),
        covered_reference_mass=mass,
        threshold=threshold,
        coverage_passed=mass + 1.0e-12 >= threshold,
        extent_passed=not failures,
        extent_failures=tuple(failures),
    )


@dataclass(slots=True)
class ProgressiveFamilyCoverageState:
    """Serial nested-rung state for one immutable family (execution-only).

    Rungs evolve strictly in canonical order inside one family: nearest
    selected distances and selected extents are carried forward from newly
    added rows only, while the covered-mass reduction is recomputed in full
    canonical witness order at every rung.
    """

    family: TargetCoverageFamilyReference
    scaled: np.ndarray
    row_by_frame_index: dict[int, int]
    selected_rows: np.ndarray
    nearest_selected_distance: np.ndarray
    selected_minimum: np.ndarray
    selected_maximum: np.ndarray

    @classmethod
    def build(cls, family: TargetCoverageFamilyReference) -> "ProgressiveFamilyCoverageState":
        values = np.asarray(family.values, dtype=np.float64)
        return cls(
            family=family,
            scaled=values / np.asarray(family.scales, dtype=np.float64)[None, :],
            row_by_frame_index={int(index): row for row, index in enumerate(family.frame_indices)},
            selected_rows=np.zeros(values.shape[0], dtype=np.bool_),
            nearest_selected_distance=np.full(values.shape[0], np.inf, dtype=np.float64),
            selected_minimum=np.full(values.shape[1], np.inf, dtype=np.float64),
            selected_maximum=np.full(values.shape[1], -np.inf, dtype=np.float64),
        )

    def add_frame_indices(self, frame_indices: Sequence[int], *, query_workers: int = 1) -> None:
        rows = [self.row_by_frame_index[int(index)] for index in frame_indices if int(index) in self.row_by_frame_index]
        if not rows:
            return
        new_rows = np.unique(np.asarray(rows, dtype=np.int64))
        new_rows = new_rows[~self.selected_rows[new_rows]]
        if new_rows.size == 0:
            return
        tree = cKDTree(self.scaled[new_rows])
        distances, _ = tree.query(self.scaled, k=1, workers=int(query_workers))
        normalized = np.asarray(distances, dtype=np.float64) / math.sqrt(float(self.scaled.shape[1]))
        np.minimum(self.nearest_selected_distance, normalized, out=self.nearest_selected_distance)
        self.selected_rows[new_rows] = True
        raw = np.asarray(self.family.values, dtype=np.float64)[new_rows]
        np.minimum(self.selected_minimum, np.min(raw, axis=0), out=self.selected_minimum)
        np.maximum(self.selected_maximum, np.max(raw, axis=0), out=self.selected_maximum)

    def report(self, *, threshold: float) -> TargetCoverageFamilyReport:
        return _family_report(
            self.family,
            selected_rows=np.flatnonzero(self.selected_rows),
            nearest_distance=self.nearest_selected_distance,
            selected_minimum=self.selected_minimum,
            selected_maximum=self.selected_maximum,
            threshold=threshold,
        )


def _selected_indices(reference: TargetCoverageReference, selected_frame_uids: Sequence[str]) -> tuple[int, ...]:
    selected = tuple(str(value) for value in selected_frame_uids)
    if not selected or len(set(selected)) != len(selected):
        raise TrainingDataInputError("Selected frames must be non-empty and unique.")
    try:
        return tuple(reference.frame_index(uid) for uid in selected)
    except KeyError as exc:
        raise TrainingDataInputError("A selected frame lies outside exact P_train.") from exc


def score_target_subset_coverage(
    reference: TargetCoverageReference, selected_frame_uids: Sequence[str], *, query_workers: int = 1
) -> TargetCoverageReport:
    """Independently score one selected subset against the immutable reference."""

    indices = _selected_indices(reference, selected_frame_uids)
    reports = []
    for family in reference.families:
        state = ProgressiveFamilyCoverageState.build(family)
        state.add_frame_indices(indices, query_workers=query_workers)
        reports.append(state.report(threshold=reference.policy.coverage_threshold))
    return TargetCoverageReport(
        reference_digest=reference.content_digest,
        selected_count=len(indices),
        selected_frame_uids_digest=digest(sorted(str(uid) for uid in selected_frame_uids)),
        family_reports=tuple(reports),
    )


# --- persistence -----------------------------------------------------------


def write_target_coverage_reference(destination: Path, reference: TargetCoverageReference) -> PublishedArtifact:
    """Publish the reference as one immutable packed artifact directory."""

    def write(directory: Path) -> Mapping[str, Any]:
        families = reference.families
        packed: dict[str, Any] = {}
        slices: dict[str, list[dict[str, Any]]] = {}
        for name, dtype, members in (
            ("frame_indices", "<i8", [item.frame_indices for item in families]),
            ("values", "<f8", [np.asarray(item.values).reshape(-1) for item in families]),
            ("weights", "<f8", [item.weights for item in families]),
            ("scales", "<f8", [item.scales for item in families]),
            ("local_radii", "<f8", [item.local_radii for item in families]),
        ):
            packed[name], slices[name] = write_packed(directory, f"packed-{name.replace('_', '-')}.npy", members, dtype=dtype)
        return {
            "schema": TARGET_COVERAGE_ARTIFACT_SCHEMA,
            "content_digest": reference.content_digest,
            "dataset_id": reference.dataset_id,
            "population_digest": reference.population_digest,
            "split_digest": reference.split_digest,
            "raw_feature_catalog_digest": reference.raw_feature_catalog_digest,
            "structural_catalog_digest": reference.structural_catalog_digest,
            "policy": reference.policy.to_dict(),
            "frame_uids": list(reference.frame_uids),
            "correlation_unit_ids": list(reference.correlation_unit_ids),
            "structural_event_support": [[name, list(rows)] for name, rows in reference.structural_event_support],
            "packed_arrays": packed,
            "families": [
                {
                    "family_id": item.family_id,
                    "family_kind": item.family_kind,
                    "semantic_family": item.semantic_family,
                    "feature_names": list(item.feature_names),
                    "value_shape": [int(v) for v in np.asarray(item.values).shape],
                    "extent_channels": [channel.to_dict() for channel in item.extent_channels],
                    "source_evidence_digest": item.source_evidence_digest,
                    "content_digest": item.content_digest,
                    "array_slices": {name: slices[name][position] for name in slices},
                }
                for position, item in enumerate(families)
            ],
        }

    return publish_artifact_directory(
        destination,
        schema=TARGET_COVERAGE_ARTIFACT_SCHEMA,
        write=write,
        verify_existing=lambda path, _manifest: read_target_coverage_reference(path),
    )


def read_target_coverage_reference(directory: Path) -> TargetCoverageReference:
    manifest = read_manifest(directory, schema=TARGET_COVERAGE_ARTIFACT_SCHEMA)
    roots = {
        name: read_packed(Path(directory), descriptor, label=f"coverage {name}")
        for name, descriptor in manifest["packed_arrays"].items()
    }
    cursors = {name: 0 for name in roots}
    families: list[TargetCoverageFamilyReference] = []
    try:
        for payload in manifest["families"]:
            arrays: dict[str, np.ndarray] = {}
            for name in _FAMILY_ARRAY_NAMES:
                descriptor = payload["array_slices"][name]
                arrays[name] = packed_slice(roots[name], descriptor, label=f"coverage {name}", cursor=cursors[name])
                cursors[name] = int(descriptor["stop"])
            family = TargetCoverageFamilyReference(
                family_id=str(payload["family_id"]),
                family_kind=str(payload["family_kind"]),
                semantic_family=str(payload["semantic_family"]),
                feature_names=tuple(payload["feature_names"]),
                frame_indices=arrays["frame_indices"],
                values=np.asarray(arrays["values"]).reshape(tuple(int(v) for v in payload["value_shape"])),
                weights=arrays["weights"],
                scales=arrays["scales"],
                local_radii=arrays["local_radii"],
                extent_channels=tuple(TargetCoverageExtentChannel.from_dict(item) for item in payload["extent_channels"]),
                source_evidence_digest=str(payload["source_evidence_digest"]),
            )
            if family.content_digest != payload["content_digest"]:
                raise TargetOrderArtifactStoreError("Target-coverage family content identity mismatch.")
            families.append(family)
        if any(cursors[name] != int(roots[name].size) for name in roots):
            raise TargetOrderArtifactStoreError("Target-coverage packed arrays carry unreferenced data.")
        reference = TargetCoverageReference(
            dataset_id=str(manifest["dataset_id"]),
            population_digest=str(manifest["population_digest"]),
            split_digest=str(manifest["split_digest"]),
            raw_feature_catalog_digest=str(manifest["raw_feature_catalog_digest"]),
            structural_catalog_digest=str(manifest["structural_catalog_digest"]),
            policy=TargetCoveragePolicy.from_dict(manifest["policy"]),
            frame_uids=tuple(manifest["frame_uids"]),
            correlation_unit_ids=tuple(manifest["correlation_unit_ids"]),
            families=tuple(families),
            structural_event_support=tuple(
                (str(name), tuple(int(v) for v in rows)) for name, rows in manifest["structural_event_support"]
            ),
        )
    except (KeyError, TypeError, ValueError, TrainingDataInputError) as exc:
        raise TargetOrderArtifactStoreError(f"Target-coverage reference artifact is invalid: {exc}") from exc
    if reference.content_digest != manifest["content_digest"]:
        raise TargetOrderArtifactStoreError("Target-coverage reference content identity mismatch.")
    return reference


__all__ = [
    "COVERAGE_RESOLUTION_MASS",
    "COVERAGE_THRESHOLD",
    "NEIGHBORHOOD_METRIC_TOLERANCE",
    "ProgressiveFamilyCoverageState",
    "TargetCoverageExtentChannel",
    "TargetCoverageFamilyReference",
    "TargetCoverageFamilyReport",
    "TargetCoveragePolicy",
    "TargetCoverageReference",
    "TargetCoverageReport",
    "build_target_coverage_reference",
    "correlation_balanced_weights",
    "local_reference_radii",
    "local_reference_radii_dense_exact",
    "read_target_coverage_reference",
    "score_target_subset_coverage",
    "structural_feature_family",
    "write_target_coverage_reference",
]
