"""TARGET-DATA2B reference-side empirical-mass coverage authority.

The target-size ladder is intentionally *not* owned here.  This module freezes
what "coverage" means for the authorized TARGET-DATA2A development domain and
provides a deterministic scorer for any later selected frame subset.

Reference elements are frame-level summaries of local-environment
distributions, pair-specific geometry, target-label tails, and cached
foundation-model residuals.  Keeping one element per frame/family reuses the
production DATA6 representation and avoids materializing millions of duplicate
per-atom Python records while retaining species/group-resolved local physics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import math
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from scipy.spatial import cKDTree
from scipy.stats import wasserstein_distance

from .progress_timing import format_progress_fraction
from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .difficulty import TrainingDifficultyDomainKind
from .resources import StageResourceScope
from .work_queue import DeterministicWorkQueue

TARGET_COVERAGE_POLICY_SCHEMA = "mdstats.target-coverage-policy.v1"
TARGET_COVERAGE_EXTENT_SCHEMA = "mdstats.target-coverage-extent.v1"
TARGET_COVERAGE_ARRAY_SCHEMA = "mdstats.target-coverage-array.v1"
TARGET_COVERAGE_FAMILY_LEGACY_SCHEMA = "mdstats.target-coverage-family.v1"
TARGET_COVERAGE_FAMILY_SCHEMA = "mdstats.target-coverage-family.v2"
TARGET_COVERAGE_STRATUM_SCHEMA = "mdstats.target-coverage-stratum.v1"
TARGET_COVERAGE_DOMAIN_LEGACY_SCHEMA = "mdstats.target-coverage-domain.v1"
TARGET_COVERAGE_DOMAIN_SCHEMA = "mdstats.target-coverage-domain.v3"
TARGET_COVERAGE_REFERENCE_LEGACY_SCHEMA = "mdstats.target-coverage-reference.v1"
TARGET_COVERAGE_REFERENCE_SCHEMA = "mdstats.target-coverage-reference.v3"
TARGET_COVERAGE_FAMILY_REPORT_SCHEMA = "mdstats.target-coverage-family-report.v1"
TARGET_COVERAGE_STRATUM_REPORT_SCHEMA = "mdstats.target-coverage-stratum-report.v1"
TARGET_COVERAGE_REPORT_SCHEMA = "mdstats.target-coverage-report.v1"
TARGET_COVERAGE_VERSION = "mdstats.target-data2b.coverage.2026-08.v1"
TARGET_COVERAGE_PERSISTENCE_VERSION = "mdstats.target-data2b.native-persistence.2026-08.v2"
TARGET_COVERAGE_MIGRATION_SCHEMA = "mdstats.target-coverage-migration-report.v1"

_REFERENCE_METRIC = "scaled_rms_l2"
_SCALAR_FIDELITY = "normalized_first_wasserstein"


def _finite_unit_interval(value: float, *, name: str, open_zero: bool = False) -> float:
    result = float(value)
    lower_ok = result > 0.0 if open_zero else result >= 0.0
    if not np.isfinite(result) or not lower_ok or result >= 1.0:
        bracket = "(0,1)" if open_zero else "[0,1)"
        raise TrainingDataInputError(f"{name} must lie in {bracket}.")
    return result


def _unique_nonempty(values: Sequence[str], *, name: str) -> tuple[str, ...]:
    result = tuple(str(value).strip() for value in values)
    if any(not value for value in result) or len(set(result)) != len(result):
        raise TrainingDataInputError(f"{name} must contain unique non-empty values.")
    return result


def _canonical_coverage_array(
    values: np.ndarray | Sequence[Any],
    *,
    dtype: str | np.dtype[Any],
    ndim: int,
    name: str,
) -> np.ndarray:
    """Return a read-only little-endian C-order numerical array."""

    target_dtype = np.dtype(dtype)
    if target_dtype.itemsize > 1:
        target_dtype = target_dtype.newbyteorder("<")
    array = np.asarray(values, dtype=target_dtype)
    if array.ndim != ndim:
        raise TrainingDataInputError(f"{name} must have {ndim} dimensions.")
    array = np.ascontiguousarray(array, dtype=target_dtype)
    array.setflags(write=False)
    return array


def _sha256_array_bytes(array: np.ndarray, *, chunk_bytes: int = 8 * 1024 * 1024) -> str:
    """Hash canonical array bytes incrementally without materializing Python scalars."""

    contiguous = np.ascontiguousarray(array)
    view = memoryview(contiguous).cast("B")
    hasher = hashlib.sha256()
    for offset in range(0, len(view), max(1, int(chunk_bytes))):
        hasher.update(view[offset:offset + chunk_bytes])
    return hasher.hexdigest()


def _coverage_array_reference(array: np.ndarray) -> dict[str, Any]:
    contiguous = np.ascontiguousarray(array)
    payload = {
        "schema": TARGET_COVERAGE_ARRAY_SCHEMA,
        "dtype": contiguous.dtype.str,
        "shape": [int(value) for value in contiguous.shape],
        "byte_count": int(contiguous.nbytes),
        "value_sha256": _sha256_array_bytes(contiguous),
    }
    return {**payload, "content_digest": digest(payload)}


def _validate_array_reference(
    supplied: Mapping[str, Any] | None,
    array: np.ndarray,
    *,
    name: str,
) -> None:
    if supplied is None:
        return
    expected = _coverage_array_reference(array)
    if dict(supplied) != expected:
        raise TrainingDataSerializationError(
            f"TARGET-DATA2B {name} array reference mismatch."
        )


def _legacy_payload_digest(payload: Mapping[str, Any]) -> str:
    return digest({key: value for key, value in payload.items() if key != "content_digest"})


@dataclass(frozen=True, slots=True)
class TargetCoveragePolicy:
    """Frozen scientific policy defining TARGET-DATA2B coverage semantics."""

    coverage_metric: str = "reference_mass_local_knn"
    coverage_threshold: float = 0.95
    coverage_resolution_mass: float = 1.0 / 128.0
    coverage_leave_one_out: bool = True
    extent_quantile_alpha: float = 0.01
    metric_minimum_scale: float = 1.0e-12
    required_structural_feature_families: tuple[str, ...] = (
        "pair_distance",
        "radial_environment",
        "coordination",
        "connectivity",
        "chemical_environment",
        "local_density",
        "angular_environment",
        "orientational_order",
    )
    extent_structural_feature_families: tuple[str, ...] = (
        "pair_distance",
        "coordination",
        "local_density",
    )
    require_condition_support: bool = True
    require_structural_event_support: bool = True
    include_profile_selection_features: bool = True
    require_profile_environment_support: bool = True
    minimum_family_elements: int = 2
    policy_version: str = TARGET_COVERAGE_VERSION

    def __post_init__(self) -> None:
        if self.coverage_metric != "reference_mass_local_knn":
            raise TrainingDataInputError("TARGET-DATA2B supports only reference_mass_local_knn coverage.")
        threshold = float(self.coverage_threshold)
        if not np.isfinite(threshold) or threshold <= 0.0 or threshold > 1.0:
            raise TrainingDataInputError("coverage_threshold must lie in (0,1].")
        beta = _finite_unit_interval(
            self.coverage_resolution_mass,
            name="coverage_resolution_mass",
            open_zero=True,
        )
        alpha = _finite_unit_interval(
            self.extent_quantile_alpha,
            name="extent_quantile_alpha",
            open_zero=True,
        )
        if alpha >= 0.5:
            raise TrainingDataInputError("extent_quantile_alpha must be below 0.5.")
        minimum_scale = float(self.metric_minimum_scale)
        if not np.isfinite(minimum_scale) or minimum_scale <= 0.0:
            raise TrainingDataInputError("metric_minimum_scale must be positive and finite.")
        if int(self.minimum_family_elements) < 2:
            raise TrainingDataInputError("minimum_family_elements must be at least two.")
        if not self.policy_version.strip():
            raise TrainingDataInputError("TARGET-DATA2B policy_version must be non-empty.")
        object.__setattr__(self, "coverage_threshold", threshold)
        object.__setattr__(self, "coverage_resolution_mass", beta)
        object.__setattr__(self, "extent_quantile_alpha", alpha)
        object.__setattr__(self, "metric_minimum_scale", minimum_scale)
        object.__setattr__(self, "minimum_family_elements", int(self.minimum_family_elements))
        object.__setattr__(
            self,
            "required_structural_feature_families",
            _unique_nonempty(self.required_structural_feature_families, name="required_structural_feature_families"),
        )
        object.__setattr__(
            self,
            "extent_structural_feature_families",
            _unique_nonempty(self.extent_structural_feature_families, name="extent_structural_feature_families"),
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
            "require_condition_support": self.require_condition_support,
            "require_structural_event_support": self.require_structural_event_support,
            "include_profile_selection_features": self.include_profile_selection_features,
            "require_profile_environment_support": self.require_profile_environment_support,
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
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2B coverage-policy schema.")
        result = cls(
            coverage_metric=str(payload["coverage_metric"]),
            coverage_threshold=float(payload["coverage_threshold"]),
            coverage_resolution_mass=float(payload["coverage_resolution_mass"]),
            coverage_leave_one_out=bool(payload["coverage_leave_one_out"]),
            extent_quantile_alpha=float(payload["extent_quantile_alpha"]),
            metric_minimum_scale=float(payload["metric_minimum_scale"]),
            required_structural_feature_families=tuple(str(v) for v in payload["required_structural_feature_families"]),
            extent_structural_feature_families=tuple(str(v) for v in payload["extent_structural_feature_families"]),
            require_condition_support=bool(payload["require_condition_support"]),
            require_structural_event_support=bool(payload["require_structural_event_support"]),
            include_profile_selection_features=bool(payload.get("include_profile_selection_features", True)),
            require_profile_environment_support=bool(payload.get("require_profile_environment_support", True)),
            minimum_family_elements=int(payload["minimum_family_elements"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("TARGET-DATA2B coverage-policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageExtentChannel:
    feature_name: str
    feature_index: int
    lower_reference_quantile: float
    upper_reference_quantile: float

    def __post_init__(self) -> None:
        if not self.feature_name.strip() or self.feature_index < 0:
            raise TrainingDataInputError("TARGET-DATA2B extent-channel identity is invalid.")
        lower = float(self.lower_reference_quantile)
        upper = float(self.upper_reference_quantile)
        if not np.isfinite(lower) or not np.isfinite(upper) or lower > upper:
            raise TrainingDataInputError("TARGET-DATA2B extent bounds are invalid.")
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
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2B extent schema.")
        result = cls(
            feature_name=str(payload["feature_name"]),
            feature_index=int(payload["feature_index"]),
            lower_reference_quantile=float(payload["lower_reference_quantile"]),
            upper_reference_quantile=float(payload["upper_reference_quantile"]),
        )
        expected = result.to_dict()["content_digest"]
        if payload.get("content_digest") not in (None, expected):
            raise TrainingDataSerializationError("TARGET-DATA2B extent digest mismatch.")
        return result


@dataclass(frozen=True, slots=True, eq=False)
class TargetCoverageFamilyReference:
    family_id: str
    family_kind: str
    semantic_family: str
    required: bool
    metric: str
    fidelity_diagnostic: str | None
    feature_names: tuple[str, ...]
    frame_indices: np.ndarray | Sequence[int]
    values: np.ndarray | Sequence[Sequence[float]]
    weights: np.ndarray | Sequence[float]
    scales: np.ndarray | Sequence[float]
    local_radii: np.ndarray | Sequence[float]
    extent_channels: tuple[TargetCoverageExtentChannel, ...]
    source_evidence_digest: str
    notes: tuple[str, ...] = ()
    _array_references: Mapping[str, Mapping[str, Any]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.family_id.strip() or not self.semantic_family.strip():
            raise TrainingDataInputError("TARGET-DATA2B family identifiers must be non-empty.")
        if self.family_kind not in {
            "structural", "profile", "pair_geometry", "target_label", "foundation_residual"
        }:
            raise TrainingDataInputError(
                f"Unsupported TARGET-DATA2B family kind {self.family_kind!r}."
            )
        if self.metric != _REFERENCE_METRIC:
            raise TrainingDataInputError(
                "TARGET-DATA2B continuous families require scaled_rms_l2 metric."
            )
        names = _unique_nonempty(self.feature_names, name="coverage family feature_names")
        indices = _canonical_coverage_array(
            self.frame_indices, dtype="<i8", ndim=1, name="coverage family frame_indices"
        )
        matrix = _canonical_coverage_array(
            self.values, dtype="<f8", ndim=2, name="coverage family values"
        )
        weights = _canonical_coverage_array(
            self.weights, dtype="<f8", ndim=1, name="coverage family weights"
        )
        scales = _canonical_coverage_array(
            self.scales, dtype="<f8", ndim=1, name="coverage family scales"
        )
        radii = _canonical_coverage_array(
            self.local_radii, dtype="<f8", ndim=1, name="coverage family local_radii"
        )
        n, d = matrix.shape
        if n < 2 or d == 0 or len(names) != d:
            raise TrainingDataInputError("TARGET-DATA2B family arrays are empty or misaligned.")
        if indices.shape != (n,) or weights.shape != (n,) or radii.shape != (n,):
            raise TrainingDataInputError("TARGET-DATA2B family arrays are empty or misaligned.")
        if np.any(indices < 0):
            raise TrainingDataInputError(
                "TARGET-DATA2B family frame indices must be nonnegative."
            )
        if np.any(~np.isfinite(matrix)):
            raise TrainingDataInputError(
                "TARGET-DATA2B family values must be finite and rectangular."
            )
        if scales.shape != (d,) or np.any(~np.isfinite(scales)) or np.any(scales <= 0.0):
            raise TrainingDataInputError("TARGET-DATA2B family metric scales are invalid.")
        if np.any(~np.isfinite(weights)) or np.any(weights <= 0.0):
            raise TrainingDataInputError("TARGET-DATA2B family weights must be positive and finite.")
        if not math.isclose(
            float(np.sum(weights, dtype=np.float64)),
            1.0,
            rel_tol=1.0e-10,
            abs_tol=1.0e-12,
        ):
            raise TrainingDataInputError("TARGET-DATA2B family weights must sum to one.")
        if np.any(~np.isfinite(radii)) or np.any(radii < 0.0):
            raise TrainingDataInputError(
                "TARGET-DATA2B local radii must be finite and nonnegative."
            )
        extents = tuple(self.extent_channels)
        if any(
            item.feature_index >= d or item.feature_name != names[item.feature_index]
            for item in extents
        ):
            raise TrainingDataInputError(
                "TARGET-DATA2B extent channels are misaligned with family features."
            )
        source_digest = validate_digest(
            self.source_evidence_digest, name="source_evidence_digest"
        )
        array_references = {
            "frame_indices": _coverage_array_reference(indices),
            "values": _coverage_array_reference(matrix),
            "weights": _coverage_array_reference(weights),
            "scales": _coverage_array_reference(scales),
            "local_radii": _coverage_array_reference(radii),
        }
        object.__setattr__(self, "feature_names", names)
        object.__setattr__(self, "frame_indices", indices)
        object.__setattr__(self, "values", matrix)
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "scales", scales)
        object.__setattr__(self, "local_radii", radii)
        object.__setattr__(self, "extent_channels", extents)
        object.__setattr__(self, "source_evidence_digest", source_digest)
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))
        object.__setattr__(self, "_array_references", array_references)

    @property
    def array_references(self) -> Mapping[str, Mapping[str, Any]]:
        return self._array_references

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_FAMILY_SCHEMA,
            "family_id": self.family_id,
            "family_kind": self.family_kind,
            "semantic_family": self.semantic_family,
            "required": self.required,
            "metric": self.metric,
            "fidelity_diagnostic": self.fidelity_diagnostic,
            "feature_names": list(self.feature_names),
            "array_references": {
                name: dict(reference)
                for name, reference in sorted(self._array_references.items())
            },
            "extent_channels": [item.to_dict() for item in self.extent_channels],
            "source_evidence_digest": self.source_evidence_digest,
            "notes": list(self.notes),
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

    def to_dict(self) -> dict[str, Any]:
        """Return the v2 inline JSON compatibility form.

        Campaign persistence does not use this representation; it writes the
        arrays as authenticated NPY shards. Inline JSON remains available for
        compact fixtures, debugging, and API compatibility.
        """

        payload = {
            **self._digest_payload(),
            "array_encoding": "inline-json-v1",
            "frame_indices": self.frame_indices.tolist(),
            "values": self.values.tolist(),
            "weights": self.weights.tolist(),
            "scales": self.scales.tolist(),
            "local_radii": self.local_radii.tolist(),
        }
        return {**payload, "content_digest": self.content_digest}

    def to_legacy_v1_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_COVERAGE_FAMILY_LEGACY_SCHEMA,
            "family_id": self.family_id,
            "family_kind": self.family_kind,
            "semantic_family": self.semantic_family,
            "required": self.required,
            "metric": self.metric,
            "fidelity_diagnostic": self.fidelity_diagnostic,
            "feature_names": list(self.feature_names),
            "frame_indices": self.frame_indices.tolist(),
            "values": self.values.tolist(),
            "weights": self.weights.tolist(),
            "scales": self.scales.tolist(),
            "local_radii": self.local_radii.tolist(),
            "extent_channels": [item.to_dict() for item in self.extent_channels],
            "source_evidence_digest": self.source_evidence_digest,
            "notes": list(self.notes),
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageFamilyReference":
        schema = payload.get("schema")
        if schema not in {
            TARGET_COVERAGE_FAMILY_SCHEMA,
            TARGET_COVERAGE_FAMILY_LEGACY_SCHEMA,
        }:
            raise TrainingDataSerializationError(
                "Unsupported TARGET-DATA2B family schema."
            )
        if schema == TARGET_COVERAGE_FAMILY_LEGACY_SCHEMA:
            supplied = payload.get("content_digest")
            if supplied not in (None, _legacy_payload_digest(payload)):
                raise TrainingDataSerializationError(
                    "TARGET-DATA2B legacy family digest mismatch."
                )
        result = cls(
            family_id=str(payload["family_id"]),
            family_kind=str(payload["family_kind"]),
            semantic_family=str(payload["semantic_family"]),
            required=bool(payload["required"]),
            metric=str(payload["metric"]),
            fidelity_diagnostic=(
                None
                if payload.get("fidelity_diagnostic") is None
                else str(payload["fidelity_diagnostic"])
            ),
            feature_names=tuple(str(value) for value in payload["feature_names"]),
            frame_indices=np.asarray(payload["frame_indices"], dtype=np.int64),
            values=np.asarray(payload["values"], dtype=np.float64),
            weights=np.asarray(payload["weights"], dtype=np.float64),
            scales=np.asarray(payload["scales"], dtype=np.float64),
            local_radii=np.asarray(payload["local_radii"], dtype=np.float64),
            extent_channels=tuple(
                TargetCoverageExtentChannel.from_dict(item)
                for item in payload.get("extent_channels", ())
            ),
            source_evidence_digest=str(payload["source_evidence_digest"]),
            notes=tuple(str(value) for value in payload.get("notes", ())),
        )
        if schema == TARGET_COVERAGE_FAMILY_SCHEMA:
            references = payload.get("array_references")
            if not isinstance(references, Mapping):
                raise TrainingDataSerializationError(
                    "TARGET-DATA2B v2 family lacks array references."
                )
            for name in (
                "frame_indices", "values", "weights", "scales", "local_radii"
            ):
                supplied_reference = references.get(name)
                if not isinstance(supplied_reference, Mapping):
                    raise TrainingDataSerializationError(
                        f"TARGET-DATA2B v2 family lacks {name} array identity."
                    )
                _validate_array_reference(
                    supplied_reference, getattr(result, name), name=name
                )
            if payload.get("content_digest") not in (None, result.content_digest):
                raise TrainingDataSerializationError(
                    "TARGET-DATA2B family digest mismatch."
                )
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageStratumRequirement:
    stratum_id: str
    stratum_kind: str
    label: str
    frame_indices: tuple[int, ...]
    minimum_selected_frames: int = 1
    required: bool = True

    def __post_init__(self) -> None:
        if not self.stratum_id.strip() or not self.stratum_kind.strip() or not self.label.strip():
            raise TrainingDataInputError("TARGET-DATA2B stratum identity is invalid.")
        indices = tuple(sorted(set(int(v) for v in self.frame_indices)))
        minimum = int(self.minimum_selected_frames)
        if not indices or any(v < 0 for v in indices) or minimum <= 0 or minimum > len(indices):
            raise TrainingDataInputError("TARGET-DATA2B stratum support requirement is invalid.")
        object.__setattr__(self, "frame_indices", indices)
        object.__setattr__(self, "minimum_selected_frames", minimum)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_COVERAGE_STRATUM_SCHEMA,
            "stratum_id": self.stratum_id,
            "stratum_kind": self.stratum_kind,
            "label": self.label,
            "frame_indices": list(self.frame_indices),
            "minimum_selected_frames": self.minimum_selected_frames,
            "required": self.required,
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageStratumRequirement":
        if payload.get("schema") != TARGET_COVERAGE_STRATUM_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2B stratum schema.")
        result = cls(
            stratum_id=str(payload["stratum_id"]),
            stratum_kind=str(payload["stratum_kind"]),
            label=str(payload["label"]),
            frame_indices=tuple(int(v) for v in payload["frame_indices"]),
            minimum_selected_frames=int(payload["minimum_selected_frames"]),
            required=bool(payload["required"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("TARGET-DATA2B stratum digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageDomainReference:
    label_domain_id: str
    frame_uids: tuple[str, ...]
    families: tuple[TargetCoverageFamilyReference, ...]
    strata: tuple[TargetCoverageStratumRequirement, ...]
    frame_domain_digest: str
    source_label_domain_id: str | None = None
    training_domain_kind: str = "final_development"
    training_domain_fold_index: int | None = None
    training_domain_digest: str | None = None
    _family_by_id: Mapping[str, TargetCoverageFamilyReference] = field(default_factory=dict, init=False, repr=False, compare=False)
    _frame_index_by_uid: Mapping[str, int] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.label_domain_id.strip():
            raise TrainingDataInputError("TARGET-DATA2B domain label must be non-empty.")
        frames = tuple(validate_digest(v, name="frame_uid") for v in self.frame_uids)
        if len(frames) < 2 or len(set(frames)) != len(frames):
            raise TrainingDataInputError("TARGET-DATA2B domain requires at least two unique frames.")
        families = tuple(sorted(self.families, key=lambda item: item.family_id))
        if not families or len({item.family_id for item in families}) != len(families):
            raise TrainingDataInputError("TARGET-DATA2B domain requires unique coverage families.")
        if not any(item.required for item in families):
            raise TrainingDataInputError("TARGET-DATA2B domain requires at least one required family.")
        if any(int(np.max(item.frame_indices)) >= len(frames) for item in families):
            raise TrainingDataInputError("TARGET-DATA2B family references a frame outside its domain.")
        strata = tuple(sorted(self.strata, key=lambda item: item.stratum_id))
        if len({item.stratum_id for item in strata}) != len(strata):
            raise TrainingDataInputError("TARGET-DATA2B stratum IDs must be unique.")
        if any(max(item.frame_indices) >= len(frames) for item in strata):
            raise TrainingDataInputError("TARGET-DATA2B stratum references a frame outside its domain.")
        object.__setattr__(self, "frame_uids", frames)
        object.__setattr__(self, "families", families)
        object.__setattr__(self, "strata", strata)
        object.__setattr__(self, "frame_domain_digest", validate_digest(self.frame_domain_digest, name="frame_domain_digest"))
        source_label = self.label_domain_id if self.source_label_domain_id is None else str(self.source_label_domain_id)
        if not source_label.strip():
            raise TrainingDataInputError("TARGET-DATA2B source label domain must be non-empty.")
        kind = str(self.training_domain_kind)
        if kind not in {"final_development", "cross_validation_training"}:
            raise TrainingDataInputError("TARGET-DATA2B training domain kind is invalid.")
        fold = None if self.training_domain_fold_index is None else int(self.training_domain_fold_index)
        if kind == "cross_validation_training" and (fold is None or fold < 0):
            raise TrainingDataInputError("TARGET-DATA2B CV training domains require a fold index.")
        if kind == "final_development" and fold is not None:
            raise TrainingDataInputError("TARGET-DATA2B final-development domains cannot carry a fold index.")
        training_digest = self.training_domain_digest
        if training_digest is None:
            training_digest = digest({
                "schema": "mdstats.target-coverage-training-domain.v1",
                "source_label_domain_id": source_label,
                "kind": kind,
                "fold_index": fold,
                "frame_uids": list(frames),
            })
        object.__setattr__(self, "source_label_domain_id", source_label)
        object.__setattr__(self, "training_domain_kind", kind)
        object.__setattr__(self, "training_domain_fold_index", fold)
        object.__setattr__(self, "training_domain_digest", validate_digest(training_digest, name="training_domain_digest"))
        object.__setattr__(self, "_family_by_id", {item.family_id: item for item in families})
        object.__setattr__(self, "_frame_index_by_uid", {uid: i for i, uid in enumerate(frames)})

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
            "schema": TARGET_COVERAGE_DOMAIN_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "frame_uids": list(self.frame_uids),
            "frame_domain_digest": self.frame_domain_digest,
            "source_label_domain_id": self.source_label_domain_id,
            "training_domain_kind": self.training_domain_kind,
            "training_domain_fold_index": self.training_domain_fold_index,
            "training_domain_digest": self.training_domain_digest,
            "family_digests": [item.content_digest for item in self.families],
            "strata": [item.to_dict() for item in self.strata],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = {
            **self._digest_payload(),
            "families": [item.to_dict() for item in self.families],
        }
        return {**payload, "content_digest": self.content_digest}

    def to_legacy_v1_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_COVERAGE_DOMAIN_LEGACY_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "frame_uids": list(self.frame_uids),
            "frame_domain_digest": self.frame_domain_digest,
            "families": [item.to_legacy_v1_dict() for item in self.families],
            "strata": [item.to_dict() for item in self.strata],
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageDomainReference":
        schema = payload.get("schema")
        if schema not in {
            TARGET_COVERAGE_DOMAIN_SCHEMA,
            TARGET_COVERAGE_DOMAIN_LEGACY_SCHEMA,
        }:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2B domain schema.")
        if schema == TARGET_COVERAGE_DOMAIN_LEGACY_SCHEMA:
            supplied = payload.get("content_digest")
            if supplied not in (None, _legacy_payload_digest(payload)):
                raise TrainingDataSerializationError("TARGET-DATA2B legacy domain digest mismatch.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            frame_uids=tuple(str(v) for v in payload["frame_uids"]),
            frame_domain_digest=str(payload["frame_domain_digest"]),
            source_label_domain_id=(None if payload.get("source_label_domain_id") is None else str(payload["source_label_domain_id"])),
            training_domain_kind=str(payload.get("training_domain_kind", "final_development")),
            training_domain_fold_index=(None if payload.get("training_domain_fold_index") is None else int(payload["training_domain_fold_index"])),
            training_domain_digest=(None if payload.get("training_domain_digest") is None else str(payload["training_domain_digest"])),
            families=tuple(TargetCoverageFamilyReference.from_dict(item) for item in payload["families"]),
            strata=tuple(TargetCoverageStratumRequirement.from_dict(item) for item in payload.get("strata", ())),
        )
        if schema == TARGET_COVERAGE_DOMAIN_SCHEMA:
            family_digests = payload.get("family_digests")
            if family_digests is not None and list(family_digests) != [
                item.content_digest for item in result.families
            ]:
                raise TrainingDataSerializationError("TARGET-DATA2B domain family-digest mismatch.")
            if payload.get("content_digest") not in (None, result.content_digest):
                raise TrainingDataSerializationError("TARGET-DATA2B domain digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageReference:
    dataset_id: str
    source_catalog_digest: str
    frame_catalog_digest: str
    data4_bundle_digest: str
    data5_bundle_digest: str
    data6_bundle_digest: str
    target_data_role_freeze_digest: str
    foundation_target_audit_digest: str
    policy: TargetCoveragePolicy
    domains: tuple[TargetCoverageDomainReference, ...]
    _domain_by_id: Mapping[str, TargetCoverageDomainReference] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)
    _source_schema: str = field(default=TARGET_COVERAGE_REFERENCE_SCHEMA, init=False, repr=False, compare=False)
    _source_content_digest: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in (
            "source_catalog_digest",
            "frame_catalog_digest",
            "data4_bundle_digest",
            "data5_bundle_digest",
            "data6_bundle_digest",
            "target_data_role_freeze_digest",
            "foundation_target_audit_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if not self.dataset_id.strip():
            raise TrainingDataInputError("TARGET-DATA2B dataset_id must be non-empty.")
        domains = tuple(sorted(self.domains, key=lambda item: item.label_domain_id))
        if not domains or len({item.label_domain_id for item in domains}) != len(domains):
            raise TrainingDataInputError("TARGET-DATA2B reference domains must be non-empty and unique.")
        object.__setattr__(self, "domains", domains)
        object.__setattr__(self, "_domain_by_id", {item.label_domain_id: item for item in domains})

    def domain(self, label_domain_id: str) -> TargetCoverageDomainReference:
        try:
            return self._domain_by_id[label_domain_id]
        except KeyError:
            raise KeyError(label_domain_id) from None

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_REFERENCE_SCHEMA,
            "coverage_version": TARGET_COVERAGE_VERSION,
            "persistence_version": TARGET_COVERAGE_PERSISTENCE_VERSION,
            "dataset_id": self.dataset_id,
            "source_catalog_digest": self.source_catalog_digest,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data4_bundle_digest": self.data4_bundle_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "data6_bundle_digest": self.data6_bundle_digest,
            "target_data_role_freeze_digest": self.target_data_role_freeze_digest,
            "foundation_target_audit_digest": self.foundation_target_audit_digest,
            "policy": self.policy.to_dict(),
            "domain_digests": [item.content_digest for item in self.domains],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    @property
    def source_schema(self) -> str:
        return self._source_schema

    @property
    def source_content_digest(self) -> str:
        return self._source_content_digest or self.content_digest

    @property
    def requires_native_persistence_migration(self) -> bool:
        return self._source_schema == TARGET_COVERAGE_REFERENCE_LEGACY_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        payload = {
            **self._digest_payload(),
            "domains": [item.to_dict() for item in self.domains],
        }
        return {**payload, "content_digest": self.content_digest}

    def to_legacy_v1_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_COVERAGE_REFERENCE_LEGACY_SCHEMA,
            "coverage_version": TARGET_COVERAGE_VERSION,
            "dataset_id": self.dataset_id,
            "source_catalog_digest": self.source_catalog_digest,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data4_bundle_digest": self.data4_bundle_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "data6_bundle_digest": self.data6_bundle_digest,
            "target_data_role_freeze_digest": self.target_data_role_freeze_digest,
            "foundation_target_audit_digest": self.foundation_target_audit_digest,
            "policy": self.policy.to_dict(),
            "domains": [item.to_legacy_v1_dict() for item in self.domains],
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageReference":
        schema = payload.get("schema")
        if schema not in {
            TARGET_COVERAGE_REFERENCE_SCHEMA,
            TARGET_COVERAGE_REFERENCE_LEGACY_SCHEMA,
        }:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2B reference schema.")
        if payload.get("coverage_version") not in (None, TARGET_COVERAGE_VERSION):
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2B coverage version.")
        if schema == TARGET_COVERAGE_REFERENCE_SCHEMA and payload.get(
            "persistence_version"
        ) not in (None, TARGET_COVERAGE_PERSISTENCE_VERSION):
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2B persistence version.")
        if schema == TARGET_COVERAGE_REFERENCE_LEGACY_SCHEMA:
            supplied = payload.get("content_digest")
            if supplied not in (None, _legacy_payload_digest(payload)):
                raise TrainingDataSerializationError("TARGET-DATA2B legacy reference digest mismatch.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            source_catalog_digest=str(payload["source_catalog_digest"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            data4_bundle_digest=str(payload["data4_bundle_digest"]),
            data5_bundle_digest=str(payload["data5_bundle_digest"]),
            data6_bundle_digest=str(payload["data6_bundle_digest"]),
            target_data_role_freeze_digest=str(payload["target_data_role_freeze_digest"]),
            foundation_target_audit_digest=str(payload["foundation_target_audit_digest"]),
            policy=TargetCoveragePolicy.from_dict(payload["policy"]),
            domains=tuple(TargetCoverageDomainReference.from_dict(item) for item in payload["domains"]),
        )
        if schema == TARGET_COVERAGE_REFERENCE_SCHEMA:
            domain_digests = payload.get("domain_digests")
            if domain_digests is not None and list(domain_digests) != [
                item.content_digest for item in result.domains
            ]:
                raise TrainingDataSerializationError("TARGET-DATA2B reference domain-digest mismatch.")
            if payload.get("content_digest") not in (None, result.content_digest):
                raise TrainingDataSerializationError("TARGET-DATA2B reference digest mismatch.")
        object.__setattr__(result, "_source_schema", str(schema))
        object.__setattr__(result, "_source_content_digest", str(payload.get("content_digest") or result.content_digest))
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageMigrationReport:
    source_schema: str
    source_content_digest: str
    target_schema: str
    target_content_digest: str
    exact_match: bool
    difference_paths: tuple[str, ...]
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_content_digest", validate_digest(self.source_content_digest, name="source_content_digest"))
        object.__setattr__(self, "target_content_digest", validate_digest(self.target_content_digest, name="target_content_digest"))
        differences = tuple(sorted(set(str(value) for value in self.difference_paths)))
        if bool(self.exact_match) == bool(differences):
            raise TrainingDataInputError("TARGET-DATA2B migration result and differences disagree.")
        object.__setattr__(self, "difference_paths", differences)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_MIGRATION_SCHEMA,
            "source_schema": self.source_schema,
            "source_content_digest": self.source_content_digest,
            "target_schema": self.target_schema,
            "target_content_digest": self.target_content_digest,
            "exact_match": self.exact_match,
            "difference_paths": list(self.difference_paths),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageMigrationReport":
        if payload.get("schema") != TARGET_COVERAGE_MIGRATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2B migration-report schema.")
        result = cls(
            source_schema=str(payload["source_schema"]),
            source_content_digest=str(payload["source_content_digest"]),
            target_schema=str(payload["target_schema"]),
            target_content_digest=str(payload["target_content_digest"]),
            exact_match=bool(payload["exact_match"]),
            difference_paths=tuple(str(value) for value in payload.get("difference_paths", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2B migration-report digest mismatch.")
        return result


def compare_target_coverage_references_exact(
    source: TargetCoverageReference,
    target: TargetCoverageReference,
) -> TargetCoverageMigrationReport:
    """Compare v1/v2 authorities without scalarizing their numerical arrays."""

    differences: list[str] = []
    scalar_fields = (
        "dataset_id",
        "source_catalog_digest",
        "frame_catalog_digest",
        "data4_bundle_digest",
        "data5_bundle_digest",
        "data6_bundle_digest",
        "target_data_role_freeze_digest",
        "foundation_target_audit_digest",
    )
    for name in scalar_fields:
        if getattr(source, name) != getattr(target, name):
            differences.append(name)
    if source.policy.to_dict() != target.policy.to_dict():
        differences.append("policy")
    if len(source.domains) != len(target.domains):
        differences.append("domains.length")
    for domain_index, (left_domain, right_domain) in enumerate(zip(source.domains, target.domains)):
        domain_path = f"domains[{domain_index}]"
        for name in ("label_domain_id", "frame_uids", "frame_domain_digest", "strata"):
            if getattr(left_domain, name) != getattr(right_domain, name):
                differences.append(f"{domain_path}.{name}")
        if len(left_domain.families) != len(right_domain.families):
            differences.append(f"{domain_path}.families.length")
        for family_index, (left_family, right_family) in enumerate(zip(left_domain.families, right_domain.families)):
            family_path = f"{domain_path}.families[{family_index}]"
            for name in (
                "family_id",
                "family_kind",
                "semantic_family",
                "required",
                "metric",
                "fidelity_diagnostic",
                "feature_names",
                "extent_channels",
                "source_evidence_digest",
                "notes",
            ):
                if getattr(left_family, name) != getattr(right_family, name):
                    differences.append(f"{family_path}.{name}")
            for name in ("frame_indices", "values", "weights", "scales", "local_radii"):
                if not np.array_equal(getattr(left_family, name), getattr(right_family, name)):
                    differences.append(f"{family_path}.{name}")
    return TargetCoverageMigrationReport(
        source_schema=source.source_schema,
        source_content_digest=source.source_content_digest,
        target_schema=TARGET_COVERAGE_REFERENCE_SCHEMA,
        target_content_digest=target.content_digest,
        exact_match=not differences,
        difference_paths=tuple(differences),
    )


@dataclass(frozen=True, slots=True)
class TargetCoverageFamilyReport:
    family_id: str
    required: bool
    reference_element_count: int
    representative_element_count: int
    covered_reference_mass: float
    threshold: float
    coverage_passed: bool
    extent_passed: bool
    extent_failures: tuple[str, ...]
    fidelity_diagnostic: str | None
    fidelity_value: float | None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_COVERAGE_FAMILY_REPORT_SCHEMA,
            "family_id": self.family_id,
            "required": self.required,
            "reference_element_count": self.reference_element_count,
            "representative_element_count": self.representative_element_count,
            "covered_reference_mass": self.covered_reference_mass,
            "threshold": self.threshold,
            "coverage_passed": self.coverage_passed,
            "extent_passed": self.extent_passed,
            "extent_failures": list(self.extent_failures),
            "fidelity_diagnostic": self.fidelity_diagnostic,
            "fidelity_value": self.fidelity_value,
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageFamilyReport":
        if payload.get("schema") != TARGET_COVERAGE_FAMILY_REPORT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2B family-report schema.")
        result = cls(
            family_id=str(payload["family_id"]),
            required=bool(payload["required"]),
            reference_element_count=int(payload["reference_element_count"]),
            representative_element_count=int(payload["representative_element_count"]),
            covered_reference_mass=float(payload["covered_reference_mass"]),
            threshold=float(payload["threshold"]),
            coverage_passed=bool(payload["coverage_passed"]),
            extent_passed=bool(payload["extent_passed"]),
            extent_failures=tuple(str(v) for v in payload.get("extent_failures", ())),
            fidelity_diagnostic=None if payload.get("fidelity_diagnostic") is None else str(payload["fidelity_diagnostic"]),
            fidelity_value=None if payload.get("fidelity_value") is None else float(payload["fidelity_value"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("TARGET-DATA2B family-report digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageStratumReport:
    stratum_id: str
    required: bool
    selected_frame_count: int
    minimum_selected_frames: int
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_COVERAGE_STRATUM_REPORT_SCHEMA,
            "stratum_id": self.stratum_id,
            "required": self.required,
            "selected_frame_count": self.selected_frame_count,
            "minimum_selected_frames": self.minimum_selected_frames,
            "passed": self.passed,
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageStratumReport":
        if payload.get("schema") != TARGET_COVERAGE_STRATUM_REPORT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2B stratum-report schema.")
        result = cls(
            stratum_id=str(payload["stratum_id"]),
            required=bool(payload["required"]),
            selected_frame_count=int(payload["selected_frame_count"]),
            minimum_selected_frames=int(payload["minimum_selected_frames"]),
            passed=bool(payload["passed"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("TARGET-DATA2B stratum-report digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageReport:
    reference_digest: str
    label_domain_id: str
    selected_frame_uids: tuple[str, ...]
    family_reports: tuple[TargetCoverageFamilyReport, ...]
    stratum_reports: tuple[TargetCoverageStratumReport, ...]
    passed: bool
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "reference_digest", validate_digest(self.reference_digest, name="reference_digest"))
        frames = tuple(validate_digest(v, name="selected_frame_uid") for v in self.selected_frame_uids)
        if not frames or len(set(frames)) != len(frames):
            raise TrainingDataInputError("TARGET-DATA2B coverage report requires unique selected frames.")
        object.__setattr__(self, "selected_frame_uids", frames)
        object.__setattr__(self, "family_reports", tuple(sorted(self.family_reports, key=lambda item: item.family_id)))
        object.__setattr__(self, "stratum_reports", tuple(sorted(self.stratum_reports, key=lambda item: item.stratum_id)))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_REPORT_SCHEMA,
            "reference_digest": self.reference_digest,
            "label_domain_id": self.label_domain_id,
            "selected_frame_uids": list(self.selected_frame_uids),
            "family_reports": [item.to_dict() for item in self.family_reports],
            "stratum_reports": [item.to_dict() for item in self.stratum_reports],
            "passed": self.passed,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageReport":
        if payload.get("schema") != TARGET_COVERAGE_REPORT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2B coverage-report schema.")
        result = cls(
            reference_digest=str(payload["reference_digest"]),
            label_domain_id=str(payload["label_domain_id"]),
            selected_frame_uids=tuple(str(v) for v in payload["selected_frame_uids"]),
            family_reports=tuple(TargetCoverageFamilyReport.from_dict(item) for item in payload["family_reports"]),
            stratum_reports=tuple(TargetCoverageStratumReport.from_dict(item) for item in payload.get("stratum_reports", ())),
            passed=bool(payload["passed"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2B coverage-report digest mismatch.")
        return result


def _weighted_quantiles(
    values: np.ndarray,
    weights: np.ndarray,
    quantiles: Sequence[float],
) -> np.ndarray:
    """Evaluate several exact weighted quantiles from one stable ordering."""

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
    targets = requested * total
    indices = np.searchsorted(cumulative, targets, side="left")
    indices = np.minimum(indices, sorted_values.size - 1)
    return np.asarray(sorted_values[indices], dtype=np.float64)


def _weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    return float(_weighted_quantiles(values, weights, (q,))[0])


@dataclass(frozen=True, slots=True)
class _WeightedColumnStatistics:
    scales: np.ndarray
    lower_extents: np.ndarray | None
    upper_extents: np.ndarray | None


def _weighted_column_statistics(
    values: np.ndarray,
    weights: np.ndarray,
    *,
    minimum: float,
    extent_alpha: float | None = None,
) -> _WeightedColumnStatistics:
    """Compute robust scales and optional extent bounds with one sort per column."""

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
        observed = _weighted_quantiles(matrix[:, column], weights, unique)
        by_quantile = dict(zip(unique, observed))
        scale = float(by_quantile[0.75] - by_quantile[0.25])
        if not np.isfinite(scale) or scale <= minimum:
            scale = float(by_quantile[0.99] - by_quantile[0.01])
        if not np.isfinite(scale) or scale <= minimum:
            scale = max(float(np.std(matrix[:, column])), 1.0)
        scales[column] = max(scale, minimum)
        if lower is not None and upper is not None and extent_alpha is not None:
            lower[column] = by_quantile[float(extent_alpha)]
            upper[column] = by_quantile[1.0 - float(extent_alpha)]
    scales.setflags(write=False)
    if lower is not None:
        lower.setflags(write=False)
    if upper is not None:
        upper.setflags(write=False)
    return _WeightedColumnStatistics(scales, lower, upper)


def _robust_scales(values: np.ndarray, weights: np.ndarray, *, minimum: float) -> np.ndarray:
    return _weighted_column_statistics(values, weights, minimum=minimum).scales


def _balanced_frame_weights(
    frame_uids: Sequence[str],
    *,
    data5_bundle: Any,
) -> np.ndarray:
    """Equal mass per correlation unit, then equal mass per available frame."""

    grouped: dict[str, list[int]] = {}
    for row, frame_uid in enumerate(frame_uids):
        try:
            unit = data5_bundle.unit_catalog.unit_for_frame(frame_uid)
        except KeyError as exc:
            raise TrainingDataInputError("TARGET-DATA2B family contains a frame outside DATA5.") from exc
        grouped.setdefault(unit.unit_id, []).append(row)
    if not grouped:
        raise TrainingDataInputError("TARGET-DATA2B cannot weight an empty family.")
    weights = np.zeros(len(frame_uids), dtype=np.float64)
    unit_mass = 1.0 / len(grouped)
    for rows in grouped.values():
        per_frame = unit_mass / len(rows)
        weights[np.asarray(rows, dtype=np.int64)] = per_frame
    weights /= np.sum(weights, dtype=np.float64)
    return weights


@dataclass(frozen=True, slots=True)
class _TargetCoverageWeightProfile:
    identity: str
    frame_indices: np.ndarray
    weights: np.ndarray
    uniform: bool


@dataclass(slots=True)
class _TargetCoverageBuildCache:
    profiles: dict[str, _TargetCoverageWeightProfile] = field(default_factory=dict)

    def resolve(
        self,
        *,
        label_domain_id: str,
        frame_uids: Sequence[str],
        domain_frame_index: Mapping[str, int],
        correlation_unit_by_uid: Mapping[str, str],
        leave_one_out: bool,
    ) -> _TargetCoverageWeightProfile:
        indices = _canonical_coverage_array(
            np.fromiter(
                (domain_frame_index[uid] for uid in frame_uids),
                dtype=np.int64,
                count=len(frame_uids),
            ),
            dtype="<i8",
            ndim=1,
            name="coverage weight-profile frame_indices",
        )
        unit_ids = tuple(correlation_unit_by_uid[uid] for uid in frame_uids)
        identity_payload = {
            "schema": "mdstats.target-coverage-weight-profile-identity.v1",
            "label_domain_id": label_domain_id,
            "frame_indices": _coverage_array_reference(indices),
            "correlation_unit_ids": list(unit_ids),
            "weighting": "equal-unit-then-equal-frame",
            "leave_one_out": bool(leave_one_out),
        }
        identity = digest(identity_payload)
        cached = self.profiles.get(identity)
        if cached is not None:
            return cached
        grouped: dict[str, list[int]] = {}
        for row, unit_id in enumerate(unit_ids):
            grouped.setdefault(unit_id, []).append(row)
        if not grouped:
            raise TrainingDataInputError("TARGET-DATA2B cannot weight an empty family.")
        weights = np.zeros(len(unit_ids), dtype=np.float64)
        unit_mass = 1.0 / len(grouped)
        for rows in grouped.values():
            weights[np.asarray(rows, dtype=np.int64)] = unit_mass / len(rows)
        weights /= np.sum(weights, dtype=np.float64)
        weights = _canonical_coverage_array(
            weights, dtype="<f8", ndim=1, name="coverage weight-profile weights"
        )
        profile = _TargetCoverageWeightProfile(
            identity=identity,
            frame_indices=indices,
            weights=weights,
            uniform=bool(np.all(weights == weights[0])),
        )
        self.profiles[identity] = profile
        return profile



@dataclass(frozen=True, slots=True)
class _TargetCoverageExecutionContext:
    label_domain_id: str
    correlation_unit_by_uid: Mapping[str, str]
    weight_cache: _TargetCoverageBuildCache | None
    radius_block_size: int
    uniform_fast_path: bool
    radius_queue: DeterministicWorkQueue | None = None


def _uniform_reference_rank(
    weights: np.ndarray,
    *,
    beta: float,
    leave_one_out: bool,
) -> int | None:
    """Return the exact one-based neighbor rank for a uniform weight profile."""

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
        raise TrainingDataInputError("TARGET-DATA2B uniform local-radius reference is degenerate.")
    increments = np.full(count, float(weights[0]) / denominator, dtype=np.float64)
    cumulative = np.cumsum(increments, dtype=np.float64)
    index = int(np.searchsorted(cumulative, float(beta) - 1.0e-15, side="left"))
    if index >= count:
        if cumulative[-1] + 1.0e-12 < beta:
            raise TrainingDataInputError("TARGET-DATA2B local-radius mass target cannot be reached.")
        index = count - 1
    return index + 1


def _local_reference_radii_uniform_block(
    tree: cKDTree,
    points: np.ndarray,
    *,
    start: int,
    stop: int,
    rank: int,
    leave_one_out: bool,
    query_workers: int,
) -> tuple[int, np.ndarray]:
    """Resolve one uniform local-radius row block exactly."""

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
        raise TrainingDataInputError("TARGET-DATA2B uniform neighbor rank cannot be resolved.")
    hit = np.argmax(reached, axis=1)
    norm = math.sqrt(float(dim))
    block = distances[np.arange(rows.size), hit] / norm
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
    """Resolve one weighted local-radius row block exactly."""

    n, dim = points.shape
    initial_k = min(n, max(8, int(math.ceil(beta * n * 1.5)) + 2))
    norm = math.sqrt(float(dim))
    block = np.empty(stop - start, dtype=np.float64)
    pending = np.arange(start, stop, dtype=np.int64)
    k = initial_k
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
            raise TrainingDataInputError("TARGET-DATA2B local-radius reference is degenerate.")
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
                raise TrainingDataInputError("TARGET-DATA2B local-radius mass target cannot be reached.")
            block[pending[unresolved_rows] - start] = distances[unresolved_rows, -1] / norm
            break
        pending = pending[unresolved_rows]
        k = min(n, max(k + 1, k * 2))
    return int(start), block


def _local_reference_radii_uniform(
    points: np.ndarray,
    *,
    rank: int,
    leave_one_out: bool,
    block_size: int,
    query_workers: int,
) -> np.ndarray:
    n, _ = points.shape
    tree = cKDTree(points)
    radii = np.empty(n, dtype=np.float64)
    for start in range(0, n, block_size):
        stop = min(n, start + block_size)
        block_start, block = _local_reference_radii_uniform_block(
            tree,
            points,
            start=start,
            stop=stop,
            rank=rank,
            leave_one_out=leave_one_out,
            query_workers=query_workers,
        )
        radii[block_start:block_start + block.size] = block
    return radii


def _local_reference_radii_weighted(
    points: np.ndarray,
    weights: np.ndarray,
    *,
    beta: float,
    leave_one_out: bool,
    block_size: int,
    query_workers: int,
) -> np.ndarray:
    n, _ = points.shape
    tree = cKDTree(points)
    radii = np.empty(n, dtype=np.float64)
    for start in range(0, n, block_size):
        stop = min(n, start + block_size)
        block_start, block = _local_reference_radii_weighted_block(
            tree,
            points,
            weights,
            start=start,
            stop=stop,
            beta=beta,
            leave_one_out=leave_one_out,
            query_workers=query_workers,
        )
        radii[block_start:block_start + block.size] = block
    return radii


def _covref_parallel_block_size(
    *,
    n: int,
    query_k: int,
    configured_block_size: int,
    workers: int,
) -> int:
    """Choose an execution-only row block that keeps tasks cache-sized and plentiful.

    The scientific result is row-local and independent of block boundaries.
    COVREF-PAR1 therefore caps each task near a ~2 MiB temporary-query working
    set and also exposes at least four blocks per assigned outer lane when the
    family is large enough.  The user/configured block remains an upper bound.
    """

    configured = max(1, int(configured_block_size))
    rows = max(1, int(n))
    k = max(1, int(query_k))
    lanes = max(1, int(workers))
    target_temp_bytes = 2 * 1024 * 1024
    memory_rows = max(64, target_temp_bytes // max(1, k * 48))
    occupancy_rows = max(64, int(math.ceil(rows / max(1, lanes * 4))))
    return max(1, min(configured, memory_rows, occupancy_rows, rows))


def _parallel_radius_memory_estimate(
    *,
    rows: int,
    query_k: int,
) -> int:
    """Estimate bounded cKDTree block temporaries for scheduler admission."""

    # Distances, indices, safe indices, masses/cumulative/rank arrays and
    # boolean masks.  This is execution telemetry/admission only and is not
    # scientific authority.
    return int(max(1, rows) * max(1, query_k) * 48 + max(1, rows) * 128)


def _local_reference_radii_parallel(
    values: np.ndarray,
    weights: np.ndarray,
    *,
    beta: float,
    leave_one_out: bool,
    block_size: int,
    queue: DeterministicWorkQueue,
    task_prefix: str,
    uniform_fast_path: bool,
) -> np.ndarray:
    """Exact single-level COVREF-PAR1 block scheduling over one shared tree."""

    points = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if points.ndim != 2 or weights.shape != (points.shape[0],):
        raise TrainingDataInputError("TARGET-DATA2B local-radius arrays are misaligned.")
    n, _ = points.shape
    if n < 2:
        raise TrainingDataInputError("TARGET-DATA2B local radii require at least two elements.")
    configured_block = max(1, int(block_size))
    tree = cKDTree(points)
    radii = np.empty(n, dtype=np.float64)
    rank = _uniform_reference_rank(weights, beta=beta, leave_one_out=leave_one_out)
    uniform = bool(uniform_fast_path and rank is not None)
    if uniform:
        query_k = min(n, int(rank) + (1 if leave_one_out else 0))
    else:
        query_k = min(n, max(8, int(math.ceil(beta * n * 1.5)) + 2))
    row_block = _covref_parallel_block_size(
        n=n,
        query_k=query_k,
        configured_block_size=configured_block,
        workers=queue.allocated_workers,
    )

    submitters: list[Callable[[], None]] = []
    for block_number, start in enumerate(range(0, n, row_block)):
        stop = min(n, start + row_block)
        memory = _parallel_radius_memory_estimate(rows=stop - start, query_k=query_k)
        if uniform:
            def submit_uniform(
                *,
                block_number: int = block_number,
                start: int = start,
                stop: int = stop,
                memory: int = memory,
            ) -> None:
                queue.submit(
                    task_id=f"{task_prefix}:radius:{block_number:08d}",
                    canonical_order=(block_number,),
                    function=_local_reference_radii_uniform_block,
                    args=(tree, points),
                    kwargs={
                        "start": start,
                        "stop": stop,
                        "rank": int(rank),
                        "leave_one_out": leave_one_out,
                        "query_workers": 1,
                    },
                    task_kind="target-data2b-reference-radius",
                    estimated_memory_bytes=memory,
                    locality_key=task_prefix,
                )
            submitters.append(submit_uniform)
        else:
            def submit_weighted(
                *,
                block_number: int = block_number,
                start: int = start,
                stop: int = stop,
                memory: int = memory,
            ) -> None:
                queue.submit(
                    task_id=f"{task_prefix}:radius:{block_number:08d}",
                    canonical_order=(block_number,),
                    function=_local_reference_radii_weighted_block,
                    args=(tree, points, weights),
                    kwargs={
                        "start": start,
                        "stop": stop,
                        "beta": beta,
                        "leave_one_out": leave_one_out,
                        "query_workers": 1,
                    },
                    task_kind="target-data2b-reference-radius",
                    estimated_memory_bytes=memory,
                    locality_key=task_prefix,
                )
            submitters.append(submit_weighted)

    # Submit/drain directly instead of using a nested executor.  The queue is
    # shared across the entire TARGET-DATA2B construction stage.
    next_submit = 0
    completed = 0
    while completed < len(submitters):
        while next_submit < len(submitters) and queue.can_submit():
            submitters[next_submit]()
            next_submit += 1
        queue.wait_for_completion()
        for completion in queue.drain_completed():
            start, block = completion.value
            block = np.asarray(block, dtype=np.float64)
            radii[int(start):int(start) + block.size] = block
            completed += 1
    if next_submit != len(submitters) or queue.has_outstanding_work:
        raise RuntimeError("COVREF-PAR1 radius queue did not drain exactly.")
    return radii


def _local_reference_radii(
    values: np.ndarray,
    weights: np.ndarray,
    *,
    beta: float,
    leave_one_out: bool,
    block_size: int = 1024,
    query_workers: int = 1,
    uniform_fast_path: bool = True,
    work_queue: DeterministicWorkQueue | None = None,
    task_prefix: str = "target-data2b",
) -> np.ndarray:
    """Return exact fixed-reference-mass radii with bounded query memory.

    ``work_queue`` activates COVREF-PAR1 single-level block parallelism.  It is
    execution-only; omitted callers retain the historical native-cKDTree
    ``query_workers`` behavior for backward compatibility and qualification.
    """

    points = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if points.ndim != 2 or weights.shape != (points.shape[0],):
        raise TrainingDataInputError("TARGET-DATA2B local-radius arrays are misaligned.")
    n, _ = points.shape
    if n < 2:
        raise TrainingDataInputError("TARGET-DATA2B local radii require at least two elements.")
    workers = int(query_workers)
    if workers < 1:
        raise TrainingDataInputError("TARGET-DATA2B query_workers must be positive.")
    row_block = max(1, int(block_size))
    if work_queue is not None:
        return _local_reference_radii_parallel(
            points,
            weights,
            beta=beta,
            leave_one_out=leave_one_out,
            block_size=row_block,
            queue=work_queue,
            task_prefix=str(task_prefix),
            uniform_fast_path=uniform_fast_path,
        )
    rank = _uniform_reference_rank(weights, beta=beta, leave_one_out=leave_one_out)
    if uniform_fast_path and rank is not None:
        return _local_reference_radii_uniform(
            points,
            rank=rank,
            leave_one_out=leave_one_out,
            block_size=row_block,
            query_workers=workers,
        )
    return _local_reference_radii_weighted(
        points,
        weights,
        beta=beta,
        leave_one_out=leave_one_out,
        block_size=row_block,
        query_workers=workers,
    )

def _local_reference_radii_dense_exact(
    values: np.ndarray,
    weights: np.ndarray,
    *,
    beta: float,
    leave_one_out: bool,
    block_size: int = 128,
) -> np.ndarray:
    """Bounded exact dense reference backend used only for qualification."""

    points = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if points.ndim != 2 or weights.shape != (points.shape[0],):
        raise TrainingDataInputError("TARGET-DATA2B dense local-radius arrays are misaligned.")
    n, dim = points.shape
    norm = math.sqrt(float(dim))
    result = np.empty(n, dtype=np.float64)
    for start in range(0, n, max(1, int(block_size))):
        stop = min(n, start + max(1, int(block_size)))
        delta = points[start:stop, None, :] - points[None, :, :]
        distances = np.sqrt(np.sum(delta * delta, axis=2, dtype=np.float64))
        for local_row, global_row in enumerate(range(start, stop)):
            valid = np.ones(n, dtype=np.bool_)
            if leave_one_out:
                valid[global_row] = False
                denominator = 1.0 - weights[global_row]
            else:
                denominator = 1.0
            order = np.argsort(distances[local_row], kind="mergesort")
            order = order[valid[order]]
            cumulative = np.cumsum(weights[order] / denominator, dtype=np.float64)
            hit = int(np.searchsorted(cumulative, beta - 1.0e-15, side="left"))
            if hit >= order.size:
                raise TrainingDataInputError("TARGET-DATA2B dense local-radius mass target cannot be reached.")
            result[global_row] = distances[local_row, order[hit]] / norm
    return result

def _build_family(
    *,
    family_id: str,
    family_kind: str,
    semantic_family: str,
    feature_names: Sequence[str],
    frame_uids: Sequence[str],
    values: np.ndarray,
    domain_frame_index: Mapping[str, int],
    data5_bundle: Any,
    policy: TargetCoveragePolicy,
    source_evidence_digest: str,
    required: bool = True,
    extent: bool = False,
    notes: Sequence[str] = (),
    query_workers: int = 1,
    radius_block_size: int = 1024,
    uniform_fast_path: bool = True,
    execution_context: _TargetCoverageExecutionContext | None = None,
) -> TargetCoverageFamilyReference | None:
    frame_uids = tuple(frame_uids)
    names = tuple(feature_names)
    matrix = np.asarray(values, dtype=np.float64)
    if matrix.ndim == 1:
        matrix = matrix[:, None]
    if matrix.shape != (len(frame_uids), len(names)):
        raise TrainingDataInputError("TARGET-DATA2B family builder received misaligned values.")
    if len(frame_uids) < policy.minimum_family_elements:
        return None
    if any(uid not in domain_frame_index for uid in frame_uids):
        raise TrainingDataInputError("TARGET-DATA2B family includes a frame outside the frozen domain.")
    if np.any(~np.isfinite(matrix)):
        raise TrainingDataInputError("TARGET-DATA2B family values must be finite.")

    if execution_context is not None and execution_context.weight_cache is not None:
        profile = execution_context.weight_cache.resolve(
            label_domain_id=execution_context.label_domain_id,
            frame_uids=frame_uids,
            domain_frame_index=domain_frame_index,
            correlation_unit_by_uid=execution_context.correlation_unit_by_uid,
            leave_one_out=policy.coverage_leave_one_out,
        )
        frame_indices = profile.frame_indices
        weights = profile.weights
    else:
        frame_indices = np.fromiter(
            (domain_frame_index[uid] for uid in frame_uids),
            dtype=np.int64,
            count=len(frame_uids),
        )
        weights = _balanced_frame_weights(frame_uids, data5_bundle=data5_bundle)

    statistics = _weighted_column_statistics(
        matrix,
        weights,
        minimum=policy.metric_minimum_scale,
        extent_alpha=policy.extent_quantile_alpha if extent else None,
    )
    scales = statistics.scales
    scaled = matrix / scales[None, :]
    radii = _local_reference_radii(
        scaled,
        weights,
        beta=policy.coverage_resolution_mass,
        leave_one_out=policy.coverage_leave_one_out,
        block_size=(execution_context.radius_block_size if execution_context is not None else radius_block_size),
        query_workers=query_workers,
        uniform_fast_path=(execution_context.uniform_fast_path if execution_context is not None else uniform_fast_path),
        work_queue=(execution_context.radius_queue if execution_context is not None else None),
        task_prefix=(
            f"{execution_context.label_domain_id}:{family_id}"
            if execution_context is not None else family_id
        ),
    )
    extent_channels: list[TargetCoverageExtentChannel] = []
    if extent:
        if statistics.lower_extents is None or statistics.upper_extents is None:
            raise TrainingDataInputError("TARGET-DATA2B extent statistics are unavailable.")
        for column, name in enumerate(names):
            extent_channels.append(
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
        required=required,
        metric=_REFERENCE_METRIC,
        fidelity_diagnostic=_SCALAR_FIDELITY if matrix.shape[1] == 1 else None,
        feature_names=names,
        frame_indices=frame_indices,
        values=matrix,
        weights=weights,
        scales=scales,
        local_radii=radii,
        extent_channels=tuple(extent_channels),
        source_evidence_digest=source_evidence_digest,
        notes=tuple(notes),
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


def _structural_feature_family(base_feature: str) -> str | None:
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


def _structural_families_for_domain(
    *,
    domain_frame_uids: tuple[str, ...],
    domain_frame_index: Mapping[str, int],
    data5_bundle: Any,
    data6_bundle: Any,
    policy: TargetCoveragePolicy,
    query_workers: int = 1,
    execution_context: _TargetCoverageExecutionContext | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> list[TargetCoverageFamilyReference]:
    allowed = set(domain_frame_uids)
    required_families = set(policy.required_structural_feature_families)
    extent_families = set(policy.extent_structural_feature_families)
    result: list[TargetCoverageFamilyReference] = []
    for catalog_index, catalog in enumerate(data6_bundle.universal_structural_features):
        table = catalog.frame_descriptor_table
        selected_rows = np.fromiter(
            (i for i, uid in enumerate(table.frame_uids) if uid in allowed),
            dtype=np.int64,
        )
        if selected_rows.size < policy.minimum_family_elements:
            continue
        by_key: dict[tuple[str, str], list[int]] = {}
        for column, name in enumerate(table.feature_names):
            parts = _structural_feature_name_parts(name)
            if parts is None:
                continue
            group_id, base_feature, _ = parts
            semantic = _structural_feature_family(base_feature)
            if semantic is None or semantic not in required_families:
                continue
            by_key.setdefault((group_id, semantic), []).append(column)
        provider_key = catalog.provider_identity.content_digest
        family_keys = sorted(by_key)
        for family_number, (group_id, semantic) in enumerate(family_keys, start=1):
            columns = by_key[(group_id, semantic)]
            column_indices = np.asarray(columns, dtype=np.int64)
            family_missing = table.missing_mask[np.ix_(selected_rows, column_indices)]
            rows = selected_rows[~np.any(family_missing, axis=1)]
            if rows.size < policy.minimum_family_elements:
                continue
            uids = tuple(table.frame_uids[int(row)] for row in rows)
            values = table.values[np.ix_(rows, column_indices)]
            names = tuple(table.feature_names[column] for column in columns)
            family_key = digest({
                "provider": provider_key,
                "group": group_id,
                "semantic_family": semantic,
                "features": list(names),
            })[:16]
            if progress_callback is not None:
                progress_callback(
                    f"TARGET-DATA2B structural family; progress={format_progress_fraction(family_number, len(family_keys))}; "
                    f"family={semantic}/{group_id}; reference_elements={rows.size:,}"
                )
            family = _build_family(
                family_id=f"structural:{semantic}:{group_id}:{family_key}",
                family_kind="structural",
                semantic_family=semantic,
                feature_names=names,
                frame_uids=uids,
                values=values,
                domain_frame_index=domain_frame_index,
                data5_bundle=data5_bundle,
                policy=policy,
                source_evidence_digest=catalog.content_digest,
                required=True,
                extent=semantic in extent_families,
                notes=(
                    "Frame-level species/group-resolved local-environment distribution summary from DATA6.",
                    "Vector metric is robustly scaled and normalized by feature dimension.",
                ),
                query_workers=query_workers,
                execution_context=execution_context,
            )
            if family is not None:
                result.append(family)
        if progress_callback is not None:
            progress_callback(
                f"TARGET-DATA2B structural provider; progress={format_progress_fraction(catalog_index + 1, len(data6_bundle.universal_structural_features))}; "
                f"families={len(result)}"
            )
    return result



def _profile_families_for_domain(
    *,
    domain_frame_uids: tuple[str, ...],
    domain_frame_index: Mapping[str, int],
    data5_bundle: Any,
    data6_bundle: Any,
    policy: TargetCoveragePolicy,
    query_workers: int = 1,
    execution_context: _TargetCoverageExecutionContext | None = None,
) -> list[TargetCoverageFamilyReference]:
    """Adapt profile scalars through one columnar extraction per provider."""

    if not policy.include_profile_selection_features:
        return []
    allowed = set(domain_frame_uids)
    result: list[TargetCoverageFamilyReference] = []
    for catalog in getattr(data6_bundle, "profile_selection_features", ()):
        selected_uids: tuple[str, ...]
        names: tuple[str, ...]
        matrix: np.ndarray
        missing_matrix: np.ndarray

        if catalog.extension_id == "lta" and str(catalog.stage.value) == "selection":
            # LTA already owns an immutable frame-descriptor table. Resolve it
            # once and materialize one bounded columnar block instead of
            # repeating uid -> frame_feature_vector -> tuple for every scalar.
            records = tuple(
                item for item in catalog.as_lta_selection().frame_descriptors
                if item.frame_uid in allowed
            )
            if not records:
                continue
            base_names = records[0].feature_names
            if any(item.feature_names != base_names for item in records):
                raise TrainingDataInputError(
                    "TARGET-DATA2B profile frame-feature ordering changed across frames."
                )
            names = tuple(f"lta:{name}" for name in base_names)
            selected_uids = tuple(item.frame_uid for item in records)
            matrix = np.asarray([item.vector for item in records], dtype=np.float64)
            missing_matrix = np.asarray(
                [item.missing_mask for item in records], dtype=np.bool_
            )
        else:
            uid_rows: list[str] = []
            value_rows: list[tuple[float, ...]] = []
            missing_rows: list[tuple[bool, ...]] = []
            expected_names: tuple[str, ...] | None = None
            for uid in domain_frame_uids:
                try:
                    raw_names, raw_values, raw_missing = catalog.frame_feature_vector(uid)
                except (KeyError, TrainingDataInputError):
                    continue
                current_names = tuple(str(value) for value in raw_names)
                current_values = tuple(float(value) for value in raw_values)
                current_missing = tuple(bool(value) for value in raw_missing)
                if len(current_names) != len(current_values) or len(current_names) != len(current_missing):
                    raise TrainingDataInputError(
                        "TARGET-DATA2B profile frame-feature adapter returned misaligned arrays."
                    )
                if expected_names is None:
                    expected_names = current_names
                elif current_names != expected_names:
                    raise TrainingDataInputError(
                        "TARGET-DATA2B profile frame-feature ordering changed across frames."
                    )
                uid_rows.append(uid)
                value_rows.append(current_values)
                missing_rows.append(current_missing)
            if expected_names is None:
                continue
            names = expected_names
            selected_uids = tuple(uid_rows)
            matrix = np.asarray(value_rows, dtype=np.float64)
            missing_matrix = np.asarray(missing_rows, dtype=np.bool_)

        if matrix.shape != missing_matrix.shape or matrix.shape != (
            len(selected_uids), len(names)
        ):
            raise TrainingDataInputError(
                "TARGET-DATA2B profile bulk adapter returned misaligned arrays."
            )
        provider_key = catalog.provider_identity.content_digest
        for column, name in enumerate(names):
            valid = (~missing_matrix[:, column]) & np.isfinite(matrix[:, column])
            rows = np.flatnonzero(valid)
            if rows.size < policy.minimum_family_elements:
                continue
            values = np.asarray(matrix[rows, column], dtype=np.float64)
            if np.allclose(values, values[0], rtol=0.0, atol=policy.metric_minimum_scale):
                continue
            feature_key = digest({
                "provider": provider_key,
                "extension_id": catalog.extension_id,
                "stage": catalog.stage.value,
                "feature_name": name,
            })[:16]
            family = _build_family(
                family_id=f"profile:{catalog.extension_id}:{feature_key}",
                family_kind="profile",
                semantic_family=f"profile:{catalog.extension_id}:{name}",
                feature_names=(name,),
                frame_uids=tuple(selected_uids[int(row)] for row in rows),
                values=values[:, None],
                domain_frame_index=domain_frame_index,
                data5_bundle=data5_bundle,
                policy=policy,
                source_evidence_digest=catalog.content_digest,
                required=True,
                extent=True,
                notes=(
                    "Material-profile scalar supplied through the generic profile adapter.",
                    "Sparse profile features are evaluated only on frames where the provider declares them valid.",
                    "Profile-specific environment classes are protected separately as mandatory strata.",
                ),
                query_workers=query_workers,
                execution_context=execution_context,
            )
            if family is not None:
                result.append(family)
    return result


def _raw_pair_families_for_domain(
    *,
    domain_frame_uids: tuple[str, ...],
    domain_frame_index: Mapping[str, int],
    data4_bundle: Any,
    data5_bundle: Any,
    policy: TargetCoveragePolicy,
    query_workers: int = 1,
    execution_context: _TargetCoverageExecutionContext | None = None,
) -> list[TargetCoverageFamilyReference]:
    records = {uid: data4_bundle.raw_features.for_frame(uid) for uid in domain_frame_uids}
    pair_by_rule = {
        uid: {item.rule_id: item for item in record.pair_geometry_statistics}
        for uid, record in records.items()
    }
    rule_ids = sorted({rule_id for mapping in pair_by_rule.values() for rule_id in mapping})
    result: list[TargetCoverageFamilyReference] = []
    for rule_id in rule_ids:
        for semantic, feature_names, getters in (
            (
                "bond_length_distribution",
                ("minimum_pair_distance_angstrom", "mean_nearest_neighbor_distance_angstrom", "maximum_nearest_neighbor_distance_angstrom"),
                (
                    lambda x: x.minimum_pair_distance_angstrom,
                    lambda x: x.mean_nearest_neighbor_distance_angstrom,
                    lambda x: x.maximum_nearest_neighbor_distance_angstrom,
                ),
            ),
            (
                "coordination_distribution",
                ("coordination_mean", "coordination_maximum"),
                (lambda x: x.coordination_mean, lambda x: x.coordination_maximum),
            ),
        ):
            uids: list[str] = []
            rows: list[tuple[float, ...]] = []
            for uid in domain_frame_uids:
                match = pair_by_rule[uid].get(rule_id)
                if match is None:
                    continue
                values = tuple(getter(match) for getter in getters)
                if any(value is None for value in values):
                    continue
                uids.append(uid)
                rows.append(tuple(float(value) for value in values))
            family = _build_family(
                family_id=f"pair:{rule_id}:{semantic}",
                family_kind="pair_geometry",
                semantic_family=semantic,
                feature_names=feature_names,
                frame_uids=uids,
                values=np.asarray(rows, dtype=np.float64),
                domain_frame_index=domain_frame_index,
                data5_bundle=data5_bundle,
                policy=policy,
                source_evidence_digest=data4_bundle.raw_features.content_digest,
                required=True,
                extent=True,
                notes=("Pair-specific reference derived from DATA4 raw physical geometry.",),
                query_workers=query_workers,
                execution_context=execution_context,
            )
            if family is not None:
                result.append(family)
    return result


def _target_label_families_for_domain(
    *,
    domain_frame_uids: tuple[str, ...],
    domain_frame_index: Mapping[str, int],
    data4_bundle: Any,
    data5_bundle: Any,
    policy: TargetCoveragePolicy,
    query_workers: int = 1,
    execution_context: _TargetCoverageExecutionContext | None = None,
) -> list[TargetCoverageFamilyReference]:
    records = [data4_bundle.raw_features.for_frame(uid) for uid in domain_frame_uids]
    result: list[TargetCoverageFamilyReference] = []

    force_names = ["force_component_rms_ev_per_angstrom", "force_norm_mean_ev_per_angstrom", "force_norm_max_ev_per_angstrom"]
    quantile_names = sorted({key for record in records for key, _ in record.force_norm_quantiles_ev_per_angstrom})
    force_names.extend(f"force_norm_{name}_ev_per_angstrom" for name in quantile_names)
    force_uids: list[str] = []
    force_rows: list[tuple[float, ...]] = []
    for uid, record in zip(domain_frame_uids, records):
        q = dict(record.force_norm_quantiles_ev_per_angstrom)
        values = (
            record.force_component_rms_ev_per_angstrom,
            record.force_norm_mean_ev_per_angstrom,
            record.force_norm_max_ev_per_angstrom,
            *(q.get(name) for name in quantile_names),
        )
        if any(value is None for value in values):
            continue
        force_uids.append(uid)
        force_rows.append(tuple(float(value) for value in values))
    family = _build_family(
        family_id="target_label:force_distribution",
        family_kind="target_label",
        semantic_family="force_tail",
        feature_names=force_names,
        frame_uids=force_uids,
        values=np.asarray(force_rows, dtype=np.float64),
        domain_frame_index=domain_frame_index,
        data5_bundle=data5_bundle,
        policy=policy,
        source_evidence_digest=data4_bundle.raw_features.content_digest,
        required=True,
        extent=True,
        notes=("DFT target force magnitude/tail reference; not a held-out evaluation statistic.",),
        query_workers=query_workers,
        execution_context=execution_context,
    )
    if family is not None:
        result.append(family)

    scalar_specs = (
        ("target_label:energy_per_atom", "energy_per_atom_ev", lambda r: r.energy_per_atom_ev),
        ("target_label:instantaneous_temperature", "instantaneous_temperature_kelvin", lambda r: r.instantaneous_temperature_kelvin),
        ("target_label:hydrostatic_strain", "hydrostatic_strain", lambda r: r.hydrostatic_strain),
        ("target_label:deviatoric_strain", "deviatoric_strain_norm", lambda r: r.deviatoric_strain_norm),
        ("target_label:pressure", "pressure_ev_per_angstrom3", lambda r: r.pressure_ev_per_angstrom3),
        ("target_label:stress_deviatoric", "stress_deviatoric_norm_ev_per_angstrom3", lambda r: r.stress_deviatoric_norm_ev_per_angstrom3),
    )
    for family_id, feature_name, getter in scalar_specs:
        uids = []
        rows = []
        for uid, record in zip(domain_frame_uids, records):
            value = getter(record)
            if value is None:
                continue
            uids.append(uid)
            rows.append((float(value),))
        scalar_values = np.asarray(rows, dtype=np.float64)
        # This is exactly the historical post-build rejection predicate, moved
        # before robust statistics/tree construction so a constant scalar
        # family cannot consume COVREF work.
        if scalar_values.size and np.allclose(scalar_values[:, 0], scalar_values[0, 0]):
            continue
        family = _build_family(
            family_id=family_id,
            family_kind="target_label",
            semantic_family=feature_name,
            feature_names=(feature_name,),
            frame_uids=uids,
            values=scalar_values,
            domain_frame_index=domain_frame_index,
            data5_bundle=data5_bundle,
            policy=policy,
            source_evidence_digest=data4_bundle.raw_features.content_digest,
            required=True,
            extent=True,
            notes=("Physically interpretable scalar target-development channel.",),
            query_workers=query_workers,
            execution_context=execution_context,
        )
        if family is not None:
            result.append(family)
    return result


def _foundation_residual_families_for_domain(
    *,
    label_domain_id: str,
    domain_frame_uids: tuple[str, ...],
    domain_frame_index: Mapping[str, int],
    data5_bundle: Any,
    data6_bundle: Any,
    foundation_target_audit: Any,
    policy: TargetCoveragePolicy,
    query_workers: int = 1,
    execution_context: _TargetCoverageExecutionContext | None = None,
) -> list[TargetCoverageFamilyReference]:
    difficulty = None
    for catalog in data6_bundle.training_difficulty_catalogs:
        if (
            catalog.domain.kind is TrainingDifficultyDomainKind.FINAL_DEVELOPMENT
            and catalog.domain.label_domain_id == label_domain_id
        ):
            difficulty = catalog
            break
    if difficulty is None:
        raise TrainingDataInputError(f"TARGET-DATA2B lacks foundation residuals for {label_domain_id!r}.")
    by_uid = {item.frame_uid: item for item in difficulty.records}
    if not set(domain_frame_uids).issubset(set(by_uid)):
        raise TrainingDataInputError(
            "TARGET-DATA2B gradient-training domain is not covered by the source final-development foundation residual evidence."
        )
    result: list[TargetCoverageFamilyReference] = []
    global_names = (
        "absolute_energy_error_per_atom_ev",
        "force_component_rmse_ev_per_angstrom",
        "force_vector_error_mean_ev_per_angstrom",
        "force_vector_error_max_ev_per_angstrom",
    )
    global_rows = np.asarray(
        [
            (
                by_uid[uid].absolute_energy_error_per_atom_ev,
                by_uid[uid].force_component_rmse_ev_per_angstrom,
                by_uid[uid].force_vector_error_mean_ev_per_angstrom,
                by_uid[uid].force_vector_error_max_ev_per_angstrom,
            )
            for uid in domain_frame_uids
        ],
        dtype=np.float64,
    )
    family = _build_family(
        family_id="foundation_residual:global",
        family_kind="foundation_residual",
        semantic_family="foundation_weakness",
        feature_names=global_names,
        frame_uids=domain_frame_uids,
        values=global_rows,
        domain_frame_index=domain_frame_index,
        data5_bundle=data5_bundle,
        policy=policy,
        source_evidence_digest=difficulty.content_digest,
        required=True,
        extent=True,
        notes=("Zero-shot residual family projects cached source final-development DATA6 foundation evidence onto this gradient-training domain.",),
        query_workers=query_workers,
        execution_context=execution_context,
    )
    if family is not None:
        result.append(family)

    species_by_uid = {
        uid: {item.atomic_number: item for item in by_uid[uid].species_force_errors}
        for uid in domain_frame_uids
    }
    atomic_numbers = sorted({atomic_number for mapping in species_by_uid.values() for atomic_number in mapping})
    for atomic_number in atomic_numbers:
        uids: list[str] = []
        rows: list[tuple[float, ...]] = []
        symbol = f"Z{atomic_number}"
        for uid in domain_frame_uids:
            match = species_by_uid[uid].get(atomic_number)
            if match is None:
                continue
            symbol = match.symbol
            uids.append(uid)
            rows.append(
                (
                    match.component_rmse_ev_per_angstrom,
                    match.vector_error_mean_ev_per_angstrom,
                    match.vector_error_max_ev_per_angstrom,
                )
            )
        family = _build_family(
            family_id=f"foundation_residual:species:{symbol}",
            family_kind="foundation_residual",
            semantic_family="foundation_species_weakness",
            feature_names=(
                "component_rmse_ev_per_angstrom",
                "vector_error_mean_ev_per_angstrom",
                "vector_error_max_ev_per_angstrom",
            ),
            frame_uids=uids,
            values=np.asarray(rows, dtype=np.float64),
            domain_frame_index=domain_frame_index,
            data5_bundle=data5_bundle,
            policy=policy,
            source_evidence_digest=difficulty.content_digest,
            required=True,
            extent=True,
            notes=("Species-normalized foundation residual family; species are separate pass/fail authorities.",),
            query_workers=query_workers,
            execution_context=execution_context,
        )
        if family is not None:
            result.append(family)
    # Bind the aggregate FOUNDATION-AUDIT1 identity even though per-frame values
    # come from its authenticated DATA6 residual source.
    if foundation_target_audit.content_digest == "":  # pragma: no cover - defensive API invariant
        raise TrainingDataInputError("TARGET-DATA2B foundation audit identity is unavailable.")
    return result


def _strata_for_domain(
    *,
    label_domain_id: str,
    domain_frame_uids: tuple[str, ...],
    domain_frame_index: Mapping[str, int],
    data5_bundle: Any,
    data6_bundle: Any,
    policy: TargetCoveragePolicy,
) -> list[TargetCoverageStratumRequirement]:
    allowed = set(domain_frame_uids)
    strata: list[TargetCoverageStratumRequirement] = []
    if policy.require_condition_support:
        by_condition: dict[str, list[str]] = {}
        condition_label: dict[str, str] = {}
        for unit in data5_bundle.unit_catalog.for_domain(label_domain_id):
            frames = [uid for uid in unit.frame_uids if uid in allowed]
            if not frames:
                continue
            key = unit.condition.condition_id
            by_condition.setdefault(key, []).extend(frames)
            condition_label[key] = (
                f"formula={unit.condition.reduced_formula};T={unit.condition.temperature_condition};"
                f"strain={unit.condition.strain_class};regime={unit.condition.regime}"
            )
        for condition_id, frames in sorted(by_condition.items()):
            indices = tuple(domain_frame_index[uid] for uid in sorted(set(frames)))
            strata.append(
                TargetCoverageStratumRequirement(
                    stratum_id=f"condition:{condition_id}",
                    stratum_kind="condition",
                    label=condition_label[condition_id],
                    frame_indices=indices,
                    minimum_selected_frames=1,
                    required=True,
                )
            )
    if policy.require_structural_event_support:
        by_event: dict[str, set[str]] = {}
        for catalog in data6_bundle.universal_structural_features:
            for event in catalog.events:
                if event.current_frame_uid in allowed:
                    by_event.setdefault(event.event_type, set()).add(event.current_frame_uid)
        for event_type, frames in sorted(by_event.items()):
            strata.append(
                TargetCoverageStratumRequirement(
                    stratum_id=f"structural_event:{event_type}",
                    stratum_kind="rare_structural_event",
                    label=event_type,
                    frame_indices=tuple(domain_frame_index[uid] for uid in sorted(frames)),
                    minimum_selected_frames=1,
                    required=True,
                )
            )
    if policy.require_profile_environment_support:
        for catalog in getattr(data6_bundle, "profile_selection_features", ()):
            by_label: dict[str, set[str]] = {}
            for uid in domain_frame_uids:
                try:
                    labels = catalog.environment_class_labels({uid})
                except (KeyError, TrainingDataInputError):
                    continue
                for label in labels:
                    by_label.setdefault(str(label), set()).add(uid)
            for label, frames in sorted(by_label.items()):
                label_key = digest({
                    "extension_id": catalog.extension_id,
                    "provider": catalog.provider_identity.content_digest,
                    "label": label,
                })[:16]
                strata.append(
                    TargetCoverageStratumRequirement(
                        stratum_id=f"profile_environment:{catalog.extension_id}:{label_key}",
                        stratum_kind="profile_environment",
                        label=label,
                        frame_indices=tuple(domain_frame_index[uid] for uid in sorted(frames)),
                        minimum_selected_frames=1,
                        required=True,
                    )
                )
    return strata


@dataclass(frozen=True, slots=True)
class _TargetCoverageTrainingDomainSpec:
    authority_domain_id: str
    source_label_domain_id: str
    kind: str
    fold_index: int | None
    training_domain_digest: str
    frame_uids: tuple[str, ...]


def _target_training_domain_authority_id(domain: Any) -> str:
    kind = str(getattr(getattr(domain, "kind", "final_development"), "value", getattr(domain, "kind", "final_development")))
    fold = getattr(domain, "fold_index", None)
    fold_token = "final" if fold is None else f"fold{int(fold)}"
    return (
        f"{str(domain.label_domain_id)}::{kind}:{fold_token}:"
        f"{str(domain.content_digest)}"
    )


def _resolve_target_training_domain_specs(
    data5_bundle: Any,
    target_data_role_freeze: Any,
    training_domains: Sequence[Any] | None,
) -> tuple[_TargetCoverageTrainingDomainSpec, ...]:
    if training_domains is None:
        result = []
        for frozen in target_data_role_freeze.domains:
            frames = tuple(sorted(frozen.size_development_frame_uids))
            training_digest = digest({
                "schema": "mdstats.target-coverage-training-domain.v1",
                "source_label_domain_id": frozen.label_domain_id,
                "kind": "final_development",
                "fold_index": None,
                "frame_uids": list(frames),
            })
            result.append(_TargetCoverageTrainingDomainSpec(
                authority_domain_id=frozen.label_domain_id,
                source_label_domain_id=frozen.label_domain_id,
                kind="final_development",
                fold_index=None,
                training_domain_digest=training_digest,
                frame_uids=frames,
            ))
        return tuple(result)

    result = []
    seen_digests: set[str] = set()
    seen_ids: set[str] = set()
    for domain in training_domains:
        if str(domain.data5_bundle_digest) != str(data5_bundle.content_digest):
            raise TrainingDataInputError("TARGET-DATA2B training-domain/DATA5 lineage mismatch.")
        training_digest = validate_digest(str(domain.content_digest), name="training_domain_digest")
        if training_digest in seen_digests:
            continue
        source_label = str(domain.label_domain_id)
        try:
            frozen = target_data_role_freeze.domain(source_label)
        except KeyError as exc:
            raise TrainingDataInputError(
                f"TARGET-DATA2B training domain references unknown label domain {source_label!r}."
            ) from exc
        frames = tuple(sorted(str(uid) for uid in domain.frame_uids))
        if not frames or not set(frames).issubset(set(frozen.size_development_frame_uids)):
            raise TrainingDataInputError(
                "TARGET-DATA2B training domain must be a non-empty subset of DATA2A development frames."
            )
        units = tuple(sorted(str(uid) for uid in domain.unit_ids))
        expected_frames = tuple(sorted({
            uid
            for unit_id in units
            for uid in data5_bundle.unit_catalog.unit(unit_id).frame_uids
        }))
        if expected_frames != frames:
            raise TrainingDataInputError(
                "TARGET-DATA2B training-domain frames do not exactly match its DATA5 units."
            )
        kind = str(getattr(domain.kind, "value", domain.kind))
        fold = None if domain.fold_index is None else int(domain.fold_index)
        authority_id = _target_training_domain_authority_id(domain)
        if authority_id in seen_ids:
            raise TrainingDataInputError("TARGET-DATA2B training-domain authority IDs collided.")
        seen_ids.add(authority_id)
        seen_digests.add(training_digest)
        result.append(_TargetCoverageTrainingDomainSpec(
            authority_domain_id=authority_id,
            source_label_domain_id=source_label,
            kind=kind,
            fold_index=fold,
            training_domain_digest=training_digest,
            frame_uids=frames,
        ))
    if not result:
        raise TrainingDataInputError("TARGET-DATA2B requires at least one gradient-training domain.")
    return tuple(sorted(result, key=lambda item: item.authority_domain_id))


@dataclass(frozen=True, slots=True)
class _TargetCoverageRoleDomainView:
    label_domain_id: str
    size_development_unit_ids: tuple[str, ...]
    size_development_frame_uids: tuple[str, ...]
    development_intervals: tuple[Any, ...]


def target_coverage_role_domain_view(
    target_data_role_freeze: Any,
    reference_domain: TargetCoverageDomainReference,
) -> Any:
    """Project DATA2A provenance onto one final/CV gradient-training domain."""

    base = target_data_role_freeze.domain(reference_domain.source_label_domain_id)
    frame_set = set(reference_domain.frame_uids)
    if not frame_set.issubset(set(base.size_development_frame_uids)):
        raise TrainingDataInputError(
            "TARGET-DATA2B projected DATA2A frame-domain mismatch for the training domain."
        )
    intervals = []
    for interval in base.development_intervals:
        overlap = frame_set.intersection(interval.frame_uids)
        if not overlap:
            continue
        if overlap != set(interval.frame_uids):
            raise TrainingDataInputError(
                "TARGET-DATA2B training domains must preserve complete DATA5 correlation units."
            )
        intervals.append(interval)
    covered = {uid for interval in intervals for uid in interval.frame_uids}
    if covered != frame_set:
        raise TrainingDataInputError(
            "TARGET-DATA2B projected DATA2A provenance does not cover the training domain exactly."
        )
    return _TargetCoverageRoleDomainView(
        label_domain_id=reference_domain.label_domain_id,
        size_development_unit_ids=tuple(sorted(interval.unit_id for interval in intervals)),
        size_development_frame_uids=tuple(reference_domain.frame_uids),
        development_intervals=tuple(intervals),
    )


def build_target_coverage_reference(
    data4_bundle: Any,
    data5_bundle: Any,
    data6_bundle: Any,
    target_data_role_freeze: Any,
    foundation_target_audit: Any,
    *,
    training_domains: Sequence[Any] | None = None,
    policy: TargetCoveragePolicy | None = None,
    progress_callback: Callable[[str], None] | None = None,
    query_workers: int = 1,
    radius_block_size: int = 1024,
    use_execution_caches: bool = True,
    uniform_fast_path: bool = True,
    execution_scope: StageResourceScope | None = None,
) -> TargetCoverageReference:
    """Freeze TARGET-DATA2B descriptor families, weights, local radii, and strata."""

    active = TargetCoveragePolicy() if policy is None else policy
    if data4_bundle.content_digest != data6_bundle.data4_bundle_digest:
        raise TrainingDataInputError("TARGET-DATA2B DATA4/DATA6 lineage mismatch.")
    if data5_bundle.content_digest != data6_bundle.data5_bundle_digest:
        raise TrainingDataInputError("TARGET-DATA2B DATA5/DATA6 lineage mismatch.")
    if target_data_role_freeze.data5_bundle_digest != data5_bundle.content_digest:
        raise TrainingDataInputError("TARGET-DATA2B TARGET-DATA2A/DATA5 lineage mismatch.")
    if foundation_target_audit.data5_bundle_digest != data5_bundle.content_digest:
        raise TrainingDataInputError("TARGET-DATA2B FOUNDATION-AUDIT1/DATA5 lineage mismatch.")
    if foundation_target_audit.data6_bundle_digest != data6_bundle.content_digest:
        raise TrainingDataInputError("TARGET-DATA2B FOUNDATION-AUDIT1/DATA6 lineage mismatch.")
    if foundation_target_audit.target_data_role_freeze_digest != target_data_role_freeze.content_digest:
        raise TrainingDataInputError("TARGET-DATA2B FOUNDATION-AUDIT1/TARGET-DATA2A lineage mismatch.")
    if not data6_bundle.universal_structural_features:
        raise TrainingDataInputError("TARGET-DATA2B requires DATA6 universal structural features.")

    domain_specs = _resolve_target_training_domain_specs(
        data5_bundle, target_data_role_freeze, training_domains
    )

    if execution_scope is not None and int(query_workers) != 1:
        raise TrainingDataInputError(
            "COVREF-PAR1 execution_scope requires query_workers=1 to prevent nested cKDTree parallelism."
        )

    def _build_domains(radius_queue: DeterministicWorkQueue | None) -> list[TargetCoverageDomainReference]:
        domains: list[TargetCoverageDomainReference] = []
        shared_weight_cache = _TargetCoverageBuildCache() if use_execution_caches else None
        for domain_number, domain_spec in enumerate(domain_specs, start=1):
            frame_uids = domain_spec.frame_uids
            frame_index = {uid: index for index, uid in enumerate(frame_uids)}
            try:
                correlation_unit_by_uid = {
                    uid: data5_bundle.unit_catalog.unit_for_frame(uid).unit_id
                    for uid in frame_uids
                }
            except KeyError as exc:
                raise TrainingDataInputError(
                    "TARGET-DATA2B domain contains a frame outside DATA5."
                ) from exc
            execution_context = _TargetCoverageExecutionContext(
                # Domain-local cache/task identity must distinguish CV folds that
                # share one source label domain.
                label_domain_id=domain_spec.authority_domain_id,
                correlation_unit_by_uid=correlation_unit_by_uid,
                weight_cache=shared_weight_cache,
                radius_block_size=max(1, int(radius_block_size)),
                uniform_fast_path=bool(uniform_fast_path),
                radius_queue=radius_queue,
            )
            if progress_callback is not None:
                progress_callback(
                    f"TARGET-DATA2B domain; progress={format_progress_fraction(domain_number, len(domain_specs))}; "
                    f"domain={domain_spec.authority_domain_id}; reference_frames={len(frame_uids):,}"
                )
                if radius_queue is None:
                    progress_callback(
                        f"status=configuration; phase=TARGET-DATA2B-local-kNN; native_workers={int(query_workers)}; "
                        "outer_block_queue=off; vectorized_weighted_mass=on"
                    )
                else:
                    progress_callback(
                        "status=configuration; phase=TARGET-DATA2B-local-kNN; "
                        f"outer_workers={radius_queue.allocated_workers}; native_workers=1; "
                        "outer_block_queue=on; vectorized_weighted_mass=on"
                    )
            families: list[TargetCoverageFamilyReference] = []
            families.extend(
                _structural_families_for_domain(
                    domain_frame_uids=frame_uids,
                    domain_frame_index=frame_index,
                    data5_bundle=data5_bundle,
                    data6_bundle=data6_bundle,
                    policy=active,
                    progress_callback=progress_callback,
                    query_workers=query_workers,
                    execution_context=execution_context,
                )
            )
            families.extend(
                _profile_families_for_domain(
                    domain_frame_uids=frame_uids,
                    domain_frame_index=frame_index,
                    data5_bundle=data5_bundle,
                    data6_bundle=data6_bundle,
                    policy=active,
                    query_workers=query_workers,
                    execution_context=execution_context,
                )
            )
            families.extend(
                _raw_pair_families_for_domain(
                    domain_frame_uids=frame_uids,
                    domain_frame_index=frame_index,
                    data4_bundle=data4_bundle,
                    data5_bundle=data5_bundle,
                    policy=active,
                    query_workers=query_workers,
                    execution_context=execution_context,
                )
            )
            families.extend(
                _target_label_families_for_domain(
                    domain_frame_uids=frame_uids,
                    domain_frame_index=frame_index,
                    data4_bundle=data4_bundle,
                    data5_bundle=data5_bundle,
                    policy=active,
                    query_workers=query_workers,
                    execution_context=execution_context,
                )
            )
            families.extend(
                _foundation_residual_families_for_domain(
                    label_domain_id=domain_spec.source_label_domain_id,
                    domain_frame_uids=frame_uids,
                    domain_frame_index=frame_index,
                    data5_bundle=data5_bundle,
                    data6_bundle=data6_bundle,
                    foundation_target_audit=foundation_target_audit,
                    policy=active,
                    query_workers=query_workers,
                    execution_context=execution_context,
                )
            )
            if not families:
                raise TrainingDataInputError(f"TARGET-DATA2B produced no coverage families for {domain_spec.authority_domain_id!r}.")
            strata = _strata_for_domain(
                label_domain_id=domain_spec.source_label_domain_id,
                domain_frame_uids=frame_uids,
                domain_frame_index=frame_index,
                data5_bundle=data5_bundle,
                data6_bundle=data6_bundle,
                policy=active,
            )
            frame_domain_digest = digest(
                {
                    "schema": "mdstats.target-coverage-frame-domain.v1",
                    "label_domain_id": domain_spec.authority_domain_id,
                    "source_label_domain_id": domain_spec.source_label_domain_id,
                    "training_domain_digest": domain_spec.training_domain_digest,
                    "frame_uids": list(frame_uids),
                }
            )
            domains.append(
                TargetCoverageDomainReference(
                    label_domain_id=domain_spec.authority_domain_id,
                    frame_uids=frame_uids,
                    families=tuple(families),
                    strata=tuple(strata),
                    frame_domain_digest=frame_domain_digest,
                    source_label_domain_id=domain_spec.source_label_domain_id,
                    training_domain_kind=domain_spec.kind,
                    training_domain_fold_index=domain_spec.fold_index,
                    training_domain_digest=domain_spec.training_domain_digest,
                )
            )
            if progress_callback is not None:
                progress_callback(
                    f"status=domain-complete; domain={domain_spec.authority_domain_id}; required_families={len(families)}; support_strata={len(strata)}"
                )
        return domains

    if execution_scope is None:
        domains = _build_domains(None)
    else:
        with DeterministicWorkQueue(
            execution_scope,
            max_ready_tasks=max(2, 2 * int(execution_scope.python_workers)),
            max_inflight_tasks=max(2, 2 * int(execution_scope.python_workers)),
            max_completed_tasks=max(2, 2 * int(execution_scope.python_workers)),
            thread_name_prefix="mdstats-covref-par1",
        ) as radius_queue:
            domains = _build_domains(radius_queue)

    return TargetCoverageReference(
        dataset_id=data4_bundle.dataset_id,
        source_catalog_digest=data4_bundle.source_catalog_digest,
        frame_catalog_digest=data4_bundle.frame_catalog_digest,
        data4_bundle_digest=data4_bundle.content_digest,
        data5_bundle_digest=data5_bundle.content_digest,
        data6_bundle_digest=data6_bundle.content_digest,
        target_data_role_freeze_digest=target_data_role_freeze.content_digest,
        foundation_target_audit_digest=foundation_target_audit.content_digest,
        policy=active,
        domains=tuple(domains),
    )


def _score_family(
    family: TargetCoverageFamilyReference,
    *,
    selected_frame_indices: frozenset[int],
    threshold: float,
    query_workers: int = 1,
) -> TargetCoverageFamilyReport:
    family_frames = np.asarray(family.frame_indices, dtype=np.int64)
    representative_rows = np.flatnonzero(np.fromiter((int(v) in selected_frame_indices for v in family_frames), dtype=np.bool_, count=len(family_frames)))
    if representative_rows.size == 0:
        return TargetCoverageFamilyReport(
            family_id=family.family_id,
            required=family.required,
            reference_element_count=len(family.values),
            representative_element_count=0,
            covered_reference_mass=0.0,
            threshold=threshold,
            coverage_passed=False,
            extent_passed=not family.extent_channels,
            extent_failures=tuple(item.feature_name for item in family.extent_channels),
            fidelity_diagnostic=family.fidelity_diagnostic,
            fidelity_value=None,
        )
    values = np.asarray(family.values, dtype=np.float64)
    scales = np.asarray(family.scales, dtype=np.float64)
    scaled = values / scales[None, :]
    selected = scaled[representative_rows]
    tree = cKDTree(selected)
    distances, _ = tree.query(scaled, k=1, workers=int(query_workers))
    distances = np.asarray(distances, dtype=np.float64) / math.sqrt(float(scaled.shape[1]))
    radii = np.asarray(family.local_radii, dtype=np.float64)
    covered = distances <= radii + 1.0e-12 * np.maximum(1.0, radii)
    weights = np.asarray(family.weights, dtype=np.float64)
    mass = float(np.sum(weights[covered]))

    extent_failures: list[str] = []
    raw_selected = values[representative_rows]
    for channel in family.extent_channels:
        column = raw_selected[:, channel.feature_index]
        if float(np.min(column)) > channel.lower_reference_quantile + 1.0e-12:
            extent_failures.append(f"{channel.feature_name}:lower")
        if float(np.max(column)) < channel.upper_reference_quantile - 1.0e-12:
            extent_failures.append(f"{channel.feature_name}:upper")

    fidelity_value: float | None = None
    if family.fidelity_diagnostic == _SCALAR_FIDELITY and values.shape[1] == 1:
        selected_weights = weights[representative_rows]
        selected_weights = selected_weights / np.sum(selected_weights)
        fidelity_value = float(
            wasserstein_distance(
                values[:, 0],
                values[representative_rows, 0],
                u_weights=weights,
                v_weights=selected_weights,
            )
            / scales[0]
        )
    return TargetCoverageFamilyReport(
        family_id=family.family_id,
        required=family.required,
        reference_element_count=len(family.values),
        representative_element_count=int(representative_rows.size),
        covered_reference_mass=mass,
        threshold=threshold,
        coverage_passed=mass + 1.0e-12 >= threshold,
        extent_passed=not extent_failures,
        extent_failures=tuple(extent_failures),
        fidelity_diagnostic=family.fidelity_diagnostic,
        fidelity_value=fidelity_value,
    )


def score_target_subset_coverage(
    reference: TargetCoverageReference,
    label_domain_id: str,
    selected_frame_uids: Sequence[str],
    *,
    query_workers: int = 1,
) -> TargetCoverageReport:
    """Score one selected target subset against the immutable full reference.

    ``query_workers`` is execution-only; it cannot change the report schema or
    scientific digest.
    """

    workers = int(query_workers)
    if workers < 1:
        raise TrainingDataInputError("TARGET-DATA2B coverage query_workers must be positive.")
    domain = reference.domain(label_domain_id)
    selected = tuple(
        sorted(validate_digest(v, name="selected_frame_uid") for v in selected_frame_uids)
    )
    if not selected or len(set(selected)) != len(selected):
        raise TrainingDataInputError("TARGET-DATA2B selected frames must be non-empty and unique.")
    unknown = sorted(set(selected) - set(domain.frame_uids))
    if unknown:
        raise TrainingDataInputError(
            "TARGET-DATA2B selected frames lie outside the frozen training-eligible reference: "
            + ", ".join(value[:12] for value in unknown[:5])
        )
    indices = frozenset(domain.frame_index(uid) for uid in selected)
    family_reports = tuple(
        _score_family(
            family,
            selected_frame_indices=indices,
            threshold=reference.policy.coverage_threshold,
            query_workers=workers,
        )
        for family in domain.families
    )
    stratum_reports = tuple(
        TargetCoverageStratumReport(
            stratum_id=item.stratum_id,
            required=item.required,
            selected_frame_count=sum(index in indices for index in item.frame_indices),
            minimum_selected_frames=item.minimum_selected_frames,
            passed=sum(index in indices for index in item.frame_indices) >= item.minimum_selected_frames,
        )
        for item in domain.strata
    )
    passed = all(
        (not item.required) or (item.coverage_passed and item.extent_passed)
        for item in family_reports
    ) and all((not item.required) or item.passed for item in stratum_reports)
    return TargetCoverageReport(
        reference_digest=reference.content_digest,
        label_domain_id=label_domain_id,
        selected_frame_uids=selected,
        family_reports=family_reports,
        stratum_reports=stratum_reports,
        passed=passed,
    )


@dataclass(slots=True)
class _ProgressiveFamilyCoverageState:
    """Execution-only coverage state for one immutable reference family."""

    family: TargetCoverageFamilyReference
    scaled: np.ndarray
    frame_rows: dict[int, np.ndarray]
    selected_rows: np.ndarray
    nearest_selected_distance: np.ndarray
    selected_minimum: np.ndarray
    selected_maximum: np.ndarray

    @classmethod
    def build(cls, family: TargetCoverageFamilyReference) -> "_ProgressiveFamilyCoverageState":
        values = np.asarray(family.values, dtype=np.float64)
        scales = np.asarray(family.scales, dtype=np.float64)
        frame_rows_lists: dict[int, list[int]] = {}
        for row, frame_index in enumerate(np.asarray(family.frame_indices, dtype=np.int64)):
            frame_rows_lists.setdefault(int(frame_index), []).append(row)
        return cls(
            family=family,
            scaled=values / scales[None, :],
            frame_rows={
                frame_index: np.asarray(rows, dtype=np.int64)
                for frame_index, rows in frame_rows_lists.items()
            },
            selected_rows=np.zeros(values.shape[0], dtype=np.bool_),
            nearest_selected_distance=np.full(values.shape[0], np.inf, dtype=np.float64),
            selected_minimum=np.full(values.shape[1], np.inf, dtype=np.float64),
            selected_maximum=np.full(values.shape[1], -np.inf, dtype=np.float64),
        )

    def add_frame_indices(self, frame_indices: Sequence[int], *, query_workers: int) -> None:
        rows = [self.frame_rows[index] for index in frame_indices if index in self.frame_rows]
        if not rows:
            return
        new_rows = np.concatenate(rows) if len(rows) > 1 else rows[0]
        if new_rows.size == 0:
            return
        # Repeated frame indices are rejected by the nested-subset validator,
        # but a family may map more than one element to the same frame.
        new_rows = np.unique(new_rows)
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
        representative_rows = np.flatnonzero(self.selected_rows)
        if representative_rows.size == 0:
            return TargetCoverageFamilyReport(
                family_id=self.family.family_id,
                required=self.family.required,
                reference_element_count=len(self.family.values),
                representative_element_count=0,
                covered_reference_mass=0.0,
                threshold=threshold,
                coverage_passed=False,
                extent_passed=not self.family.extent_channels,
                extent_failures=tuple(item.feature_name for item in self.family.extent_channels),
                fidelity_diagnostic=self.family.fidelity_diagnostic,
                fidelity_value=None,
            )
        radii = np.asarray(self.family.local_radii, dtype=np.float64)
        covered = self.nearest_selected_distance <= radii + 1.0e-12 * np.maximum(1.0, radii)
        weights = np.asarray(self.family.weights, dtype=np.float64)
        mass = float(np.sum(weights[covered]))
        extent_failures: list[str] = []
        for channel in self.family.extent_channels:
            if self.selected_minimum[channel.feature_index] > channel.lower_reference_quantile + 1.0e-12:
                extent_failures.append(f"{channel.feature_name}:lower")
            if self.selected_maximum[channel.feature_index] < channel.upper_reference_quantile - 1.0e-12:
                extent_failures.append(f"{channel.feature_name}:upper")
        fidelity_value: float | None = None
        values = np.asarray(self.family.values, dtype=np.float64)
        scales = np.asarray(self.family.scales, dtype=np.float64)
        if self.family.fidelity_diagnostic == _SCALAR_FIDELITY and values.shape[1] == 1:
            selected_weights = weights[representative_rows]
            selected_weights = selected_weights / np.sum(selected_weights)
            fidelity_value = float(
                wasserstein_distance(
                    values[:, 0],
                    values[representative_rows, 0],
                    u_weights=weights,
                    v_weights=selected_weights,
                )
                / scales[0]
            )
        return TargetCoverageFamilyReport(
            family_id=self.family.family_id,
            required=self.family.required,
            reference_element_count=len(self.family.values),
            representative_element_count=int(representative_rows.size),
            covered_reference_mass=mass,
            threshold=threshold,
            coverage_passed=mass + 1.0e-12 >= threshold,
            extent_passed=not extent_failures,
            extent_failures=tuple(extent_failures),
            fidelity_diagnostic=self.family.fidelity_diagnostic,
            fidelity_value=fidelity_value,
        )


def score_target_nested_subsets_coverage(
    reference: TargetCoverageReference,
    label_domain_id: str,
    nested_selected_frame_uids: Sequence[Sequence[str]],
    *,
    query_workers: int = 1,
) -> tuple[TargetCoverageReport, ...]:
    """Score nested target subsets with one progressive family workspace.

    Each family is loaded/scaled once, scored across every nested rung, then
    released before the next family is materialized.  Nearest-selected
    reference distances, selected extents, and representative membership are
    updated only from each newly added rung block.  Returned reports retain the
    unchanged TARGET-DATA2B schema and numerical authority.
    """

    workers = int(query_workers)
    if workers < 1:
        raise TrainingDataInputError("TARGET-DATA2C coverage query_workers must be positive.")
    domain = reference.domain(label_domain_id)
    domain_uid_set = set(domain.frame_uids)
    normalized: list[tuple[str, ...]] = []
    selected_indices_by_rung: list[frozenset[int]] = []
    added_indices_by_rung: list[tuple[int, ...]] = []
    previous: frozenset[str] = frozenset()
    for raw_selected in nested_selected_frame_uids:
        selected = tuple(sorted(validate_digest(v, name="selected_frame_uid") for v in raw_selected))
        if not selected or len(set(selected)) != len(selected):
            raise TrainingDataInputError("TARGET-DATA2B selected frames must be non-empty and unique.")
        current = frozenset(selected)
        unknown = sorted(current - domain_uid_set)
        if unknown:
            raise TrainingDataInputError(
                "TARGET-DATA2B selected frames lie outside the frozen training-eligible reference: "
                + ", ".join(value[:12] for value in unknown[:5])
            )
        if not previous.issubset(current):
            raise TrainingDataInputError("TARGET-DATA2B progressive coverage requires exactly nested selected sets.")
        normalized.append(selected)
        selected_indices_by_rung.append(frozenset(domain.frame_index(uid) for uid in selected))
        added_indices_by_rung.append(
            tuple(sorted(domain.frame_index(uid) for uid in current - previous))
        )
        previous = current

    family_reports_by_rung: list[list[TargetCoverageFamilyReport]] = [
        [] for _ in normalized
    ]
    for family in domain.families:
        state = _ProgressiveFamilyCoverageState.build(family)
        for rung_index, added_indices in enumerate(added_indices_by_rung):
            state.add_frame_indices(added_indices, query_workers=workers)
            family_reports_by_rung[rung_index].append(
                state.report(threshold=reference.policy.coverage_threshold)
            )

    reports: list[TargetCoverageReport] = []
    for rung_index, selected in enumerate(normalized):
        indices = selected_indices_by_rung[rung_index]
        family_reports = tuple(family_reports_by_rung[rung_index])
        stratum_reports = tuple(
            TargetCoverageStratumReport(
                stratum_id=item.stratum_id,
                required=item.required,
                selected_frame_count=sum(index in indices for index in item.frame_indices),
                minimum_selected_frames=item.minimum_selected_frames,
                passed=sum(index in indices for index in item.frame_indices) >= item.minimum_selected_frames,
            )
            for item in domain.strata
        )
        passed = all(
            (not item.required) or (item.coverage_passed and item.extent_passed)
            for item in family_reports
        ) and all((not item.required) or item.passed for item in stratum_reports)
        reports.append(
            TargetCoverageReport(
                reference_digest=reference.content_digest,
                label_domain_id=label_domain_id,
                selected_frame_uids=selected,
                family_reports=family_reports,
                stratum_reports=stratum_reports,
                passed=passed,
            )
        )
    return tuple(reports)


def assert_nested_coverage_monotonicity(
    reports: Sequence[TargetCoverageReport],
    *,
    tolerance: float = 1.0e-12,
) -> None:
    """Fail closed if nested subsets show decreasing frozen-reference coverage."""

    items = tuple(reports)
    for previous, current in zip(items, items[1:]):
        if previous.reference_digest != current.reference_digest or previous.label_domain_id != current.label_domain_id:
            raise TrainingDataInputError("TARGET-DATA2B monotonicity audit requires one reference/domain.")
        if not set(previous.selected_frame_uids).issubset(current.selected_frame_uids):
            raise TrainingDataInputError("TARGET-DATA2B monotonicity audit requires exactly nested selected sets.")
        prev = {item.family_id: item for item in previous.family_reports}
        cur = {item.family_id: item for item in current.family_reports}
        if prev.keys() != cur.keys():
            raise TrainingDataInputError("TARGET-DATA2B monotonicity audit family identity changed.")
        for family_id in prev:
            if cur[family_id].covered_reference_mass + tolerance < prev[family_id].covered_reference_mass:
                raise TrainingDataInputError(
                    f"TARGET-DATA2B nested coverage reversal for family {family_id!r}."
                )


def validate_target_coverage_reference_authority(
    reference: TargetCoverageReference,
    *,
    data4_bundle: Any,
    data5_bundle: Any,
    data6_bundle: Any,
    target_data_role_freeze: Any,
    foundation_target_audit: Any,
    training_domains: Sequence[Any] | None = None,
) -> None:
    expected = {
        "source_catalog_digest": data4_bundle.source_catalog_digest,
        "frame_catalog_digest": data4_bundle.frame_catalog_digest,
        "data4_bundle_digest": data4_bundle.content_digest,
        "data5_bundle_digest": data5_bundle.content_digest,
        "data6_bundle_digest": data6_bundle.content_digest,
        "target_data_role_freeze_digest": target_data_role_freeze.content_digest,
        "foundation_target_audit_digest": foundation_target_audit.content_digest,
    }
    for name, value in expected.items():
        if getattr(reference, name) != value:
            raise TrainingDataInputError(f"TARGET-DATA2B authority mismatch: {name} changed.")
    specs = _resolve_target_training_domain_specs(
        data5_bundle, target_data_role_freeze, training_domains
    )
    live_domains = {
        item.authority_domain_id: (
            item.source_label_domain_id,
            item.kind,
            item.fold_index,
            item.training_domain_digest,
            tuple(item.frame_uids),
        )
        for item in specs
    }
    frozen_domains = {
        item.label_domain_id: (
            item.source_label_domain_id,
            item.training_domain_kind,
            item.training_domain_fold_index,
            item.training_domain_digest,
            tuple(item.frame_uids),
        )
        for item in reference.domains
    }
    if live_domains != frozen_domains:
        raise TrainingDataInputError("TARGET-DATA2B frozen gradient-training domains changed.")
