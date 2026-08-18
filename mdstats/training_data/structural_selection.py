"""Universal structural selection features for MLFF-DATA9A7b.

The numerical local-geometry kernel is owned by
:mod:`mdstats.analysis.local_structure`.  This module owns only MLFF-facing
aggregation, atom-group realization, temporal event records, lineage, and
selection-grade serialization.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from dataclasses import dataclass, field
from functools import lru_cache
import math
import sys
import threading
import time
from typing import Any, Callable, Iterator, Mapping, Protocol, Sequence, runtime_checkable

import numpy as np
from ase.data import atomic_masses, chemical_symbols

from mdstats import AtomisticFrameCollection, FrameCollectionProvenance
from mdstats.analysis.local_structure import (
    LocalStructureFeaturePolicy,
    LocalStructureFeatureResult,
    _LocalStructureScratch,
    _compute_local_structure_features_arrays,
    _local_structure_topology_workspace,
    compute_local_structure_features,
)

from .progress_timing import (
    ProgressRateTracker,
    format_progress_fraction,
    format_progress_rate,
    format_progress_time,
)
from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ._frame_access import build_frame_array_index
from .material_profiles import (
    AtomGroupCatalog,
    AtomGroupDefinition,
    AtomGroupSelectorKind,
    AtomGroupSetOperation,
    MaterialProfileContracts,
)
from .raw_features import minimum_image_displacements
from .resources import (
    available_cpu_threads,
    build_stage_resource_scope,
    detect_system_resources,
    stage_resource_scope,
)

UNIVERSAL_STRUCTURAL_SELECTION_POLICY_SCHEMA = "mdstats.universal-structural-selection-policy.v3"
UNIVERSAL_STRUCTURAL_SELECTION_POLICY_V2_SCHEMA = "mdstats.universal-structural-selection-policy.v2"
UNIVERSAL_STRUCTURAL_SELECTION_POLICY_LEGACY_SCHEMA = "mdstats.universal-structural-selection-policy.v1"
UNIVERSAL_ATOMIC_ENVIRONMENT_SCHEMA = "mdstats.universal-atomic-environment.v1"
UNIVERSAL_FRAME_DESCRIPTOR_SCHEMA = "mdstats.universal-frame-structural-descriptor.v1"
GENERIC_STRUCTURAL_EVENT_SCHEMA = "mdstats.generic-structural-event.v1"
STRUCTURAL_FEATURE_PROVIDER_IDENTITY_SCHEMA = "mdstats.structural-feature-provider-identity.v1"
UNIVERSAL_STRUCTURAL_FEATURE_CATALOG_SCHEMA = "mdstats.universal-structural-feature-catalog.v2"
UNIVERSAL_STRUCTURAL_FEATURE_CATALOG_LEGACY_SCHEMA = "mdstats.universal-structural-feature-catalog.v1"
UNIVERSAL_STRUCTURAL_SELECTION_POLICY_VERSION = "mdstats.mlff-data9a7c.universal-structure.2026-08.v3"
UNIVERSAL_STRUCTURAL_PROVIDER_ID = "mdstats.universal_local_structure"
UNIVERSAL_STRUCTURAL_PROVIDER_VERSION = "1"
MLFF_DATA9A7B_PARSER_VERSION = "0.20.49a0"
MLFF_DATA9A7B_LEGACY_PARSER_VERSION = "0.20.48a0"


def _finite_nonnegative(value: float, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise TrainingDataInputError(f"{name} must be finite and nonnegative.")
    return result


def _feature_pairs(names: tuple[str, ...], values: np.ndarray) -> tuple[tuple[str, float], ...]:
    array = np.asarray(values, dtype=np.float64)
    if array.shape != (len(names),) or np.any(~np.isfinite(array)):
        raise TrainingDataInputError("Named structural feature vector is invalid.")
    return tuple((name, float(value)) for name, value in zip(names, array, strict=True))


@dataclass(frozen=True, slots=True)
class StructuralFeatureProviderIdentity:
    provider_id: str
    provider_version: str
    policy_digest: str
    analysis_owner: str = "mdstats.analysis.local_structure"
    _content_digest_cache: str = field(
        default="", init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if not self.provider_id.strip() or not self.provider_version.strip() or not self.analysis_owner.strip():
            raise TrainingDataInputError("Structural provider identity fields must be non-empty.")
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": STRUCTURAL_FEATURE_PROVIDER_IDENTITY_SCHEMA,
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "policy_digest": self.policy_digest,
            "analysis_owner": self.analysis_owner,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "StructuralFeatureProviderIdentity":
        if payload.get("schema") != STRUCTURAL_FEATURE_PROVIDER_IDENTITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported structural-feature-provider schema.")
        result = cls(
            provider_id=str(payload["provider_id"]),
            provider_version=str(payload["provider_version"]),
            policy_digest=str(payload["policy_digest"]),
            analysis_owner=str(payload.get("analysis_owner", "mdstats.analysis.local_structure")),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Structural-feature-provider digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class UniversalStructuralSelectionPolicy:
    local_structure_policy: LocalStructureFeaturePolicy = field(default_factory=LocalStructureFeaturePolicy)
    aggregate_statistics: tuple[str, ...] = ("mean", "std", "min", "max", "q10", "q50", "q90")
    include_declared_atom_groups: bool = True
    include_element_groups: bool = True
    materialize_atomic_environments: bool = True
    displacement_event_threshold_angstrom: float = 0.75
    coordination_event_threshold: float = 1.0
    hard_neighbor_event_threshold: int = 2
    density_event_threshold_angstrom3_inv: float = 0.02
    orientational_event_threshold: float = 0.25
    maximum_source_frame_gap: int = 1
    missing_value_fill: float = 0.0
    enabled_feature_families: tuple[str, ...] = (
        "pair_distance",
        "radial_environment",
        "coordination",
        "connectivity",
        "chemical_environment",
        "local_density",
        "angular_environment",
        "orientational_order",
    )
    enabled_event_types: tuple[str, ...] = (
        "large_atomic_displacement",
        "smooth_coordination_change",
        "hard_neighbor_count_change",
        "local_density_change",
        "orientational_order_change",
    )
    phase_geometry_plan_digest: str | None = None
    policy_version: str = UNIVERSAL_STRUCTURAL_SELECTION_POLICY_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.local_structure_policy, LocalStructureFeaturePolicy):
            raise TrainingDataInputError("local_structure_policy has the wrong type.")
        allowed = {"mean", "std", "min", "max", "q10", "q50", "q90"}
        statistics = tuple(str(value) for value in self.aggregate_statistics)
        if not statistics or len(set(statistics)) != len(statistics) or any(value not in allowed for value in statistics):
            raise TrainingDataInputError("aggregate_statistics are invalid.")
        if isinstance(self.hard_neighbor_event_threshold, bool) or int(self.hard_neighbor_event_threshold) <= 0:
            raise TrainingDataInputError("hard_neighbor_event_threshold must be positive.")
        if isinstance(self.maximum_source_frame_gap, bool) or int(self.maximum_source_frame_gap) <= 0:
            raise TrainingDataInputError("maximum_source_frame_gap must be positive.")
        for name in (
            "displacement_event_threshold_angstrom",
            "coordination_event_threshold",
            "density_event_threshold_angstrom3_inv",
            "orientational_event_threshold",
        ):
            object.__setattr__(self, name, _finite_nonnegative(getattr(self, name), name=name))
        fill = float(self.missing_value_fill)
        if not np.isfinite(fill):
            raise TrainingDataInputError("missing_value_fill must be finite.")
        allowed_families = {
            "pair_distance", "radial_environment", "coordination", "connectivity",
            "chemical_environment", "local_density", "angular_environment", "orientational_order",
        }
        families = tuple(sorted(set(str(value) for value in self.enabled_feature_families)))
        if not families or any(value not in allowed_families for value in families):
            raise TrainingDataInputError("enabled_feature_families are invalid.")
        allowed_events = {
            "large_atomic_displacement", "smooth_coordination_change", "hard_neighbor_count_change",
            "local_density_change", "orientational_order_change",
        }
        event_types = tuple(sorted(set(str(value) for value in self.enabled_event_types)))
        if any(value not in allowed_events for value in event_types):
            raise TrainingDataInputError("enabled_event_types are invalid.")
        if self.phase_geometry_plan_digest is not None:
            object.__setattr__(self, "phase_geometry_plan_digest", validate_digest(self.phase_geometry_plan_digest, name="phase_geometry_plan_digest"))
        if not self.policy_version.strip():
            raise TrainingDataInputError("policy_version must be non-empty.")
        object.__setattr__(self, "aggregate_statistics", statistics)
        object.__setattr__(self, "enabled_feature_families", families)
        object.__setattr__(self, "enabled_event_types", event_types)
        object.__setattr__(self, "hard_neighbor_event_threshold", int(self.hard_neighbor_event_threshold))
        object.__setattr__(self, "maximum_source_frame_gap", int(self.maximum_source_frame_gap))
        object.__setattr__(self, "missing_value_fill", fill)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": UNIVERSAL_STRUCTURAL_SELECTION_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "local_structure_policy": self.local_structure_policy.to_dict(),
            "aggregate_statistics": list(self.aggregate_statistics),
            "include_declared_atom_groups": self.include_declared_atom_groups,
            "include_element_groups": self.include_element_groups,
            "materialize_atomic_environments": self.materialize_atomic_environments,
            "displacement_event_threshold_angstrom": self.displacement_event_threshold_angstrom,
            "coordination_event_threshold": self.coordination_event_threshold,
            "hard_neighbor_event_threshold": self.hard_neighbor_event_threshold,
            "density_event_threshold_angstrom3_inv": self.density_event_threshold_angstrom3_inv,
            "orientational_event_threshold": self.orientational_event_threshold,
            "maximum_source_frame_gap": self.maximum_source_frame_gap,
            "missing_value_fill": self.missing_value_fill,
            "enabled_feature_families": list(self.enabled_feature_families),
            "enabled_event_types": list(self.enabled_event_types),
            "phase_geometry_plan_digest": self.phase_geometry_plan_digest,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "UniversalStructuralSelectionPolicy":
        schema = payload.get("schema")
        if schema not in (UNIVERSAL_STRUCTURAL_SELECTION_POLICY_SCHEMA, UNIVERSAL_STRUCTURAL_SELECTION_POLICY_V2_SCHEMA, UNIVERSAL_STRUCTURAL_SELECTION_POLICY_LEGACY_SCHEMA):
            raise TrainingDataSerializationError("Unsupported universal-structural policy schema.")
        result = cls(
            local_structure_policy=LocalStructureFeaturePolicy.from_dict(payload["local_structure_policy"]),
            aggregate_statistics=tuple(str(value) for value in payload["aggregate_statistics"]),
            include_declared_atom_groups=bool(payload["include_declared_atom_groups"]),
            include_element_groups=bool(payload["include_element_groups"]),
            materialize_atomic_environments=bool(payload.get("materialize_atomic_environments", True)),
            displacement_event_threshold_angstrom=float(payload["displacement_event_threshold_angstrom"]),
            coordination_event_threshold=float(payload["coordination_event_threshold"]),
            hard_neighbor_event_threshold=int(payload["hard_neighbor_event_threshold"]),
            density_event_threshold_angstrom3_inv=float(payload["density_event_threshold_angstrom3_inv"]),
            orientational_event_threshold=float(payload["orientational_event_threshold"]),
            maximum_source_frame_gap=int(payload["maximum_source_frame_gap"]),
            missing_value_fill=float(payload["missing_value_fill"]),
            enabled_feature_families=tuple(str(value) for value in payload.get("enabled_feature_families", (
                "pair_distance", "radial_environment", "coordination", "connectivity",
                "chemical_environment", "local_density", "angular_environment", "orientational_order",
            ))),
            enabled_event_types=tuple(str(value) for value in payload.get("enabled_event_types", (
                "large_atomic_displacement", "smooth_coordination_change", "hard_neighbor_count_change",
                "local_density_change", "orientational_order_change",
            ))),
            phase_geometry_plan_digest=None if payload.get("phase_geometry_plan_digest") is None else str(payload["phase_geometry_plan_digest"]),
            policy_version=(UNIVERSAL_STRUCTURAL_SELECTION_POLICY_VERSION if schema in {UNIVERSAL_STRUCTURAL_SELECTION_POLICY_V2_SCHEMA, UNIVERSAL_STRUCTURAL_SELECTION_POLICY_LEGACY_SCHEMA} else str(payload["policy_version"])),
        )
        if schema == UNIVERSAL_STRUCTURAL_SELECTION_POLICY_SCHEMA and payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Universal-structural policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class UniversalAtomicEnvironmentDescriptor:
    frame_uid: str
    atom_index: int
    atomic_number: int
    symbol: str
    named_features: tuple[tuple[str, float], ...]
    missing_mask: tuple[bool, ...]
    atom_group_ids: tuple[str, ...]
    provider_identity_digest: str
    frame_record_digest: str
    _content_digest_cache: str = field(
        default="", init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in ("frame_uid", "provider_identity_digest", "frame_record_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.atom_index < 0 or self.atomic_number <= 0 or not self.symbol.strip():
            raise TrainingDataInputError("Invalid atomic-environment identity.")
        features = tuple((str(name), float(value)) for name, value in self.named_features)
        if not features or len({name for name, _ in features}) != len(features) or any(not np.isfinite(value) for _, value in features):
            raise TrainingDataInputError("Atomic-environment features are invalid.")
        mask = tuple(bool(value) for value in self.missing_mask)
        if len(mask) != len(features):
            raise TrainingDataInputError("Atomic-environment missing mask is misaligned.")
        object.__setattr__(self, "named_features", features)
        object.__setattr__(self, "missing_mask", mask)
        object.__setattr__(self, "atom_group_ids", tuple(sorted(set(str(value) for value in self.atom_group_ids))))

    @property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.named_features)

    @property
    def vector(self) -> tuple[float, ...]:
        return tuple(value for _, value in self.named_features)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": UNIVERSAL_ATOMIC_ENVIRONMENT_SCHEMA,
            "frame_uid": self.frame_uid,
            "atom_index": self.atom_index,
            "atomic_number": self.atomic_number,
            "symbol": self.symbol,
            "named_features": dict(self.named_features),
            "feature_order": list(self.feature_names),
            "missing_mask": list(self.missing_mask),
            "atom_group_ids": list(self.atom_group_ids),
            "provider_identity_digest": self.provider_identity_digest,
            "frame_record_digest": self.frame_record_digest,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "UniversalAtomicEnvironmentDescriptor":
        if payload.get("schema") != UNIVERSAL_ATOMIC_ENVIRONMENT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported universal atomic-environment schema.")
        order = tuple(str(value) for value in payload["feature_order"])
        values = payload["named_features"]
        result = cls(
            frame_uid=str(payload["frame_uid"]),
            atom_index=int(payload["atom_index"]),
            atomic_number=int(payload["atomic_number"]),
            symbol=str(payload["symbol"]),
            named_features=tuple((name, float(values[name])) for name in order),
            missing_mask=tuple(bool(value) for value in payload["missing_mask"]),
            atom_group_ids=tuple(str(value) for value in payload.get("atom_group_ids", ())),
            provider_identity_digest=str(payload["provider_identity_digest"]),
            frame_record_digest=str(payload["frame_record_digest"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Universal atomic-environment digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class UniversalFrameStructuralDescriptor:
    frame_uid: str
    frame_record_digest: str
    provider_identity_digest: str
    named_features: tuple[tuple[str, float], ...]
    missing_mask: tuple[bool, ...]
    atom_count: int
    warning_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("frame_uid", "frame_record_digest", "provider_identity_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.atom_count <= 0:
            raise TrainingDataInputError("atom_count must be positive.")
        features = tuple((str(name), float(value)) for name, value in self.named_features)
        mask = tuple(bool(value) for value in self.missing_mask)
        if not features or len(mask) != len(features) or any(not np.isfinite(value) for _, value in features):
            raise TrainingDataInputError("Frame structural features are invalid.")
        object.__setattr__(self, "named_features", features)
        object.__setattr__(self, "missing_mask", mask)
        object.__setattr__(self, "warning_codes", tuple(sorted(set(str(value) for value in self.warning_codes))))

    @property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.named_features)

    @property
    def vector(self) -> tuple[float, ...]:
        return tuple(value for _, value in self.named_features)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": UNIVERSAL_FRAME_DESCRIPTOR_SCHEMA,
            "frame_uid": self.frame_uid,
            "frame_record_digest": self.frame_record_digest,
            "provider_identity_digest": self.provider_identity_digest,
            "named_features": dict(self.named_features),
            "feature_order": list(self.feature_names),
            "missing_mask": list(self.missing_mask),
            "atom_count": self.atom_count,
            "warning_codes": list(self.warning_codes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "UniversalFrameStructuralDescriptor":
        if payload.get("schema") != UNIVERSAL_FRAME_DESCRIPTOR_SCHEMA:
            raise TrainingDataSerializationError("Unsupported universal frame-descriptor schema.")
        order = tuple(str(value) for value in payload["feature_order"])
        values = payload["named_features"]
        result = cls(
            frame_uid=str(payload["frame_uid"]),
            frame_record_digest=str(payload["frame_record_digest"]),
            provider_identity_digest=str(payload["provider_identity_digest"]),
            named_features=tuple((name, float(values[name])) for name in order),
            missing_mask=tuple(bool(value) for value in payload["missing_mask"]),
            atom_count=int(payload["atom_count"]),
            warning_codes=tuple(str(value) for value in payload.get("warning_codes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Universal frame-descriptor digest mismatch.")
        return result


def _array_content_digest(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    return digest({
        "dtype": contiguous.dtype.str,
        "shape": list(contiguous.shape),
        "bytes_sha256": __import__("hashlib").sha256(memoryview(contiguous).cast("B")).hexdigest(),
    })


@dataclass(frozen=True, slots=True, eq=False)
class UniversalFrameDescriptorTable(Sequence[UniversalFrameStructuralDescriptor]):
    """Columnar storage for a large universal frame-descriptor population.

    Feature names and lineage strings are shared once, while numerical values
    remain in dense NumPy matrices.  Individual descriptor objects are created
    lazily only when a caller explicitly iterates or indexes the public
    sequence.  This avoids tens of millions of Python ``(name, value)`` pairs
    for production DATA6 campaigns.
    """

    frame_uids: tuple[str, ...]
    frame_record_digests: tuple[str, ...]
    provider_identity_digest: str
    feature_names: tuple[str, ...]
    values: np.ndarray
    missing_mask: np.ndarray
    atom_counts: np.ndarray
    warning_codes: tuple[tuple[str, ...], ...]
    _index_by_uid: Mapping[str, int] = field(default_factory=dict, init=False, repr=False, compare=False)
    _frame_uid_set: frozenset[str] = field(default_factory=frozenset, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        frame_uids = tuple(validate_digest(value, name="frame_uid") for value in self.frame_uids)
        frame_record_digests = tuple(validate_digest(value, name="frame_record_digest") for value in self.frame_record_digests)
        provider_digest = validate_digest(self.provider_identity_digest, name="provider_identity_digest")
        feature_names = tuple(str(value) for value in self.feature_names)
        values = np.ascontiguousarray(self.values, dtype=np.float64)
        missing = np.ascontiguousarray(self.missing_mask, dtype=np.bool_)
        atom_counts = np.ascontiguousarray(self.atom_counts, dtype=np.int32)
        warnings = tuple(tuple(sorted(set(str(code) for code in row))) for row in self.warning_codes)
        n_frames = len(frame_uids)
        if n_frames == 0 or len(set(frame_uids)) != n_frames:
            raise TrainingDataInputError("Universal structural frame table requires unique frame UIDs.")
        if len(frame_record_digests) != n_frames or len(warnings) != n_frames:
            raise TrainingDataInputError("Universal structural frame-table metadata is misaligned.")
        if not feature_names or len(set(feature_names)) != len(feature_names):
            raise TrainingDataInputError("Universal structural frame-table feature names are invalid.")
        if values.shape != (n_frames, len(feature_names)) or missing.shape != values.shape:
            raise TrainingDataInputError("Universal structural frame-table arrays are misaligned.")
        if atom_counts.shape != (n_frames,) or np.any(atom_counts <= 0):
            raise TrainingDataInputError("Universal structural frame-table atom counts are invalid.")
        if np.any(~np.isfinite(values)):
            raise TrainingDataInputError("Universal structural frame-table values must be finite.")
        values.setflags(write=False)
        missing.setflags(write=False)
        atom_counts.setflags(write=False)
        object.__setattr__(self, "frame_uids", frame_uids)
        object.__setattr__(self, "frame_record_digests", frame_record_digests)
        object.__setattr__(self, "provider_identity_digest", provider_digest)
        object.__setattr__(self, "feature_names", feature_names)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "missing_mask", missing)
        object.__setattr__(self, "atom_counts", atom_counts)
        object.__setattr__(self, "warning_codes", warnings)
        object.__setattr__(self, "_index_by_uid", {uid: index for index, uid in enumerate(frame_uids)})
        object.__setattr__(self, "_frame_uid_set", frozenset(frame_uids))

    @classmethod
    def _from_authenticated_arrays(
        cls,
        *,
        frame_uids: Sequence[str],
        frame_record_digests: Sequence[str],
        provider_identity_digest: str,
        feature_names: Sequence[str],
        values: np.ndarray,
        missing_mask: np.ndarray,
        atom_counts: np.ndarray,
        warning_codes: Sequence[Sequence[str]],
        content_digest: str,
    ) -> "UniversalFrameDescriptorTable":
        """Restore a table whose members were independently authenticated."""

        uids = tuple(validate_digest(value, name="frame_uid") for value in frame_uids)
        record_digests = tuple(
            validate_digest(value, name="frame_record_digest")
            for value in frame_record_digests
        )
        provider_digest = validate_digest(
            provider_identity_digest, name="provider_identity_digest"
        )
        names = tuple(str(value) for value in feature_names)
        value_array = np.asarray(values, dtype=np.float64, order="C")
        missing_array = np.asarray(missing_mask, dtype=np.bool_, order="C")
        count_array = np.asarray(atom_counts, dtype=np.int32, order="C")
        warnings = tuple(tuple(str(code) for code in row) for row in warning_codes)
        n_frames = len(uids)
        if (
            not uids
            or len(record_digests) != n_frames
            or len(warnings) != n_frames
            or value_array.shape != (n_frames, len(names))
            or missing_array.shape != value_array.shape
            or count_array.shape != (n_frames,)
        ):
            raise TrainingDataInputError(
                "Authenticated universal structural table metadata is misaligned."
            )
        for array in (value_array, missing_array, count_array):
            array.setflags(write=False)
        result = object.__new__(cls)
        object.__setattr__(result, "frame_uids", uids)
        object.__setattr__(result, "frame_record_digests", record_digests)
        object.__setattr__(result, "provider_identity_digest", provider_digest)
        object.__setattr__(result, "feature_names", names)
        object.__setattr__(result, "values", value_array)
        object.__setattr__(result, "missing_mask", missing_array)
        object.__setattr__(result, "atom_counts", count_array)
        object.__setattr__(result, "warning_codes", warnings)
        object.__setattr__(result, "_index_by_uid", {uid: index for index, uid in enumerate(uids)})
        object.__setattr__(result, "_frame_uid_set", frozenset(uids))
        object.__setattr__(result, "_content_digest_cache", validate_digest(content_digest, name="content_digest"))
        return result

    @classmethod
    def from_descriptors(
        cls, descriptors: Sequence[UniversalFrameStructuralDescriptor]
    ) -> "UniversalFrameDescriptorTable":
        ordered = tuple(sorted(descriptors, key=lambda item: item.frame_uid))
        if not ordered:
            raise TrainingDataInputError("Universal structural frame table cannot be empty.")
        names = ordered[0].feature_names
        if any(item.feature_names != names for item in ordered[1:]):
            raise TrainingDataInputError("Structural feature ordering must be stable across the catalog.")
        return cls(
            frame_uids=tuple(item.frame_uid for item in ordered),
            frame_record_digests=tuple(item.frame_record_digest for item in ordered),
            provider_identity_digest=ordered[0].provider_identity_digest,
            feature_names=names,
            values=np.asarray([item.vector for item in ordered], dtype=np.float64),
            missing_mask=np.asarray([item.missing_mask for item in ordered], dtype=np.bool_),
            atom_counts=np.asarray([item.atom_count for item in ordered], dtype=np.int32),
            warning_codes=tuple(item.warning_codes for item in ordered),
        )

    def __len__(self) -> int:
        return len(self.frame_uids)

    def _descriptor(self, index: int) -> UniversalFrameStructuralDescriptor:
        return UniversalFrameStructuralDescriptor(
            frame_uid=self.frame_uids[index],
            frame_record_digest=self.frame_record_digests[index],
            provider_identity_digest=self.provider_identity_digest,
            named_features=_feature_pairs(self.feature_names, self.values[index]),
            missing_mask=tuple(bool(value) for value in self.missing_mask[index]),
            atom_count=int(self.atom_counts[index]),
            warning_codes=self.warning_codes[index],
        )

    def __getitem__(self, index: int | slice) -> UniversalFrameStructuralDescriptor | tuple[UniversalFrameStructuralDescriptor, ...]:
        if isinstance(index, slice):
            return tuple(self._descriptor(value) for value in range(*index.indices(len(self))))
        normalized = int(index)
        if normalized < 0:
            normalized += len(self)
        if normalized < 0 or normalized >= len(self):
            raise IndexError(index)
        return self._descriptor(normalized)

    def __iter__(self) -> Iterator[UniversalFrameStructuralDescriptor]:
        for index in range(len(self)):
            yield self._descriptor(index)

    @property
    def frame_uid_set(self) -> frozenset[str]:
        return self._frame_uid_set

    def index_for_uid(self, frame_uid: str) -> int:
        try:
            return self._index_by_uid[frame_uid]
        except KeyError:
            raise KeyError(frame_uid) from None

    def descriptor_for_uid(self, frame_uid: str) -> UniversalFrameStructuralDescriptor:
        return self._descriptor(self.index_for_uid(frame_uid))

    def matrix_for_uids(self, frame_uids: Sequence[str]) -> tuple[tuple[str, ...], np.ndarray, np.ndarray]:
        indices = np.fromiter(
            (self.index_for_uid(uid) for uid in frame_uids),
            dtype=np.int64,
            count=len(frame_uids),
        )
        if indices.size == 0:
            return (
                self.feature_names,
                self.values[:0],
                self.missing_mask[:0],
            )
        start = int(indices[0])
        expected = np.arange(start, start + indices.size, dtype=np.int64)
        if np.array_equal(indices, expected):
            stop = start + int(indices.size)
            return (
                self.feature_names,
                self.values[start:stop],
                self.missing_mask[start:stop],
            )
        values = np.empty((indices.size, self.values.shape[1]), dtype=self.values.dtype)
        missing = np.empty((indices.size, self.missing_mask.shape[1]), dtype=np.bool_)
        np.take(self.values, indices, axis=0, out=values)
        np.take(self.missing_mask, indices, axis=0, out=missing)
        values.setflags(write=False)
        missing.setflags(write=False)
        return self.feature_names, values, missing

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest({
                "frame_uids": list(self.frame_uids),
                "frame_record_digests": list(self.frame_record_digests),
                "provider_identity_digest": self.provider_identity_digest,
                "feature_names": list(self.feature_names),
                "values_digest": _array_content_digest(self.values),
                "missing_mask_digest": _array_content_digest(self.missing_mask),
                "atom_counts_digest": _array_content_digest(self.atom_counts),
                "warning_codes": [list(value) for value in self.warning_codes],
            })
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "mdstats.universal-frame-descriptor-table.v1",
            "frame_uids": list(self.frame_uids),
            "frame_record_digests": list(self.frame_record_digests),
            "provider_identity_digest": self.provider_identity_digest,
            "feature_names": list(self.feature_names),
            "values": self.values.tolist(),
            "missing_mask": self.missing_mask.tolist(),
            "atom_counts": self.atom_counts.tolist(),
            "warning_codes": [list(value) for value in self.warning_codes],
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "UniversalFrameDescriptorTable":
        if payload.get("schema") != "mdstats.universal-frame-descriptor-table.v1":
            raise TrainingDataSerializationError("Unsupported universal frame-descriptor table schema.")
        result = cls(
            frame_uids=tuple(str(value) for value in payload["frame_uids"]),
            frame_record_digests=tuple(str(value) for value in payload["frame_record_digests"]),
            provider_identity_digest=str(payload["provider_identity_digest"]),
            feature_names=tuple(str(value) for value in payload["feature_names"]),
            values=np.asarray(payload["values"], dtype=np.float64),
            missing_mask=np.asarray(payload["missing_mask"], dtype=np.bool_),
            atom_counts=np.asarray(payload["atom_counts"], dtype=np.int32),
            warning_codes=tuple(tuple(str(code) for code in row) for row in payload["warning_codes"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Universal frame-descriptor table digest mismatch.")
        return result

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UniversalFrameDescriptorTable):
            return False
        return (
            self.frame_uids == other.frame_uids
            and self.frame_record_digests == other.frame_record_digests
            and self.provider_identity_digest == other.provider_identity_digest
            and self.feature_names == other.feature_names
            and np.array_equal(self.values, other.values)
            and np.array_equal(self.missing_mask, other.missing_mask)
            and np.array_equal(self.atom_counts, other.atom_counts)
            and self.warning_codes == other.warning_codes
        )


@dataclass(frozen=True, slots=True)
class GenericStructuralEventRecord:
    event_type: str
    run_id: str
    previous_frame_uid: str
    current_frame_uid: str
    atom_index: int
    atomic_number: int
    magnitude: float
    threshold: float
    source_frame_gap: int
    provider_identity_digest: str
    _event_id_cache: str = field(
        default="", init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in ("previous_frame_uid", "current_frame_uid", "provider_identity_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if not self.event_type.strip() or not self.run_id.strip() or self.atom_index < 0 or self.atomic_number <= 0:
            raise TrainingDataInputError("Invalid generic structural-event identity.")
        for name in ("magnitude", "threshold"):
            object.__setattr__(self, name, _finite_nonnegative(getattr(self, name), name=name))
        if self.source_frame_gap <= 0:
            raise TrainingDataInputError("source_frame_gap must be positive.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": GENERIC_STRUCTURAL_EVENT_SCHEMA,
            "event_type": self.event_type,
            "run_id": self.run_id,
            "previous_frame_uid": self.previous_frame_uid,
            "current_frame_uid": self.current_frame_uid,
            "atom_index": self.atom_index,
            "atomic_number": self.atomic_number,
            "magnitude": self.magnitude,
            "threshold": self.threshold,
            "source_frame_gap": self.source_frame_gap,
            "provider_identity_digest": self.provider_identity_digest,
        }

    @property
    def event_id(self) -> str:
        cached = self._event_id_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_event_id_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "event_id": self.event_id}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GenericStructuralEventRecord":
        if payload.get("schema") != GENERIC_STRUCTURAL_EVENT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported generic structural-event schema.")
        result = cls(
            event_type=str(payload["event_type"]),
            run_id=str(payload["run_id"]),
            previous_frame_uid=str(payload["previous_frame_uid"]),
            current_frame_uid=str(payload["current_frame_uid"]),
            atom_index=int(payload["atom_index"]),
            atomic_number=int(payload["atomic_number"]),
            magnitude=float(payload["magnitude"]),
            threshold=float(payload["threshold"]),
            source_frame_gap=int(payload["source_frame_gap"]),
            provider_identity_digest=str(payload["provider_identity_digest"]),
        )
        if payload.get("event_id") not in (None, result.event_id):
            raise TrainingDataSerializationError("Generic structural-event digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class UniversalStructuralFeatureCatalog:
    dataset_id: str
    frame_catalog_digest: str
    data4_bundle_digest: str
    material_profile_contracts_digest: str | None
    atom_group_catalog_digest: str | None
    provider_identity: StructuralFeatureProviderIdentity
    policy: UniversalStructuralSelectionPolicy
    frame_descriptors: UniversalFrameDescriptorTable | Sequence[UniversalFrameStructuralDescriptor]
    atomic_environment_descriptors: tuple[UniversalAtomicEnvironmentDescriptor, ...]
    events: tuple[GenericStructuralEventRecord, ...]
    parser_version: str = MLFF_DATA9A7B_PARSER_VERSION
    _environments_by_frame_uid: Mapping[str, tuple[UniversalAtomicEnvironmentDescriptor, ...]] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("frame_catalog_digest", "data4_bundle_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in ("material_profile_contracts_digest", "atom_group_catalog_digest"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        if self.provider_identity.policy_digest != self.policy.policy_digest:
            raise TrainingDataInputError("Structural provider/policy identity mismatch.")
        table = (
            self.frame_descriptors
            if isinstance(self.frame_descriptors, UniversalFrameDescriptorTable)
            else UniversalFrameDescriptorTable.from_descriptors(self.frame_descriptors)
        )
        if table.provider_identity_digest != self.provider_identity.content_digest:
            raise TrainingDataInputError("Structural frame table/provider lineage mismatch.")
        raw_atoms = tuple(self.atomic_environment_descriptors)
        atom_key = lambda item: (item.frame_uid, item.atom_index)
        atoms = (
            raw_atoms
            if all(
                atom_key(left) <= atom_key(right)
                for left, right in zip(raw_atoms, raw_atoms[1:])
            )
            else tuple(sorted(raw_atoms, key=atom_key))
        )
        raw_events = tuple(self.events)
        event_key = lambda item: (
            item.current_frame_uid,
            item.event_type,
            item.atom_index,
        )
        events = (
            raw_events
            if all(
                event_key(left) <= event_key(right)
                for left, right in zip(raw_events, raw_events[1:])
            )
            else tuple(sorted(raw_events, key=event_key))
        )
        frame_ids = frozenset(table.frame_uids)
        if any(item.frame_uid not in frame_ids for item in atoms):
            raise TrainingDataInputError("Atomic descriptors reference frames outside the catalog.")
        if any(item.current_frame_uid not in frame_ids or item.previous_frame_uid not in frame_ids for item in events):
            raise TrainingDataInputError("Structural events reference frames outside the catalog.")
        provider_digest = self.provider_identity.content_digest
        if any(item.provider_identity_digest != provider_digest for item in atoms):
            raise TrainingDataInputError("Structural atomic catalog/provider lineage mismatch.")
        if any(item.provider_identity_digest != provider_digest for item in events):
            raise TrainingDataInputError("Structural event catalog/provider lineage mismatch.")
        if atoms:
            first_order = atoms[0].feature_names
            if any(item.feature_names != first_order for item in atoms[1:]):
                raise TrainingDataInputError("Atomic structural feature ordering must be stable across the catalog.")
        elif self.policy.materialize_atomic_environments:
            raise TrainingDataInputError(
                "Universal structural policy requested atomic environments but the catalog is empty."
            )
        object.__setattr__(self, "frame_descriptors", table)
        object.__setattr__(self, "atomic_environment_descriptors", atoms)
        object.__setattr__(self, "events", events)
        grouped: dict[str, list[UniversalAtomicEnvironmentDescriptor]] = {}
        for item in atoms:
            grouped.setdefault(item.frame_uid, []).append(item)
        object.__setattr__(self, "_environments_by_frame_uid", {key: tuple(value) for key, value in grouped.items()})

    @property
    def frame_descriptor_table(self) -> UniversalFrameDescriptorTable:
        assert isinstance(self.frame_descriptors, UniversalFrameDescriptorTable)
        return self.frame_descriptors

    def for_frame(self, frame_uid: str) -> UniversalFrameStructuralDescriptor:
        return self.frame_descriptor_table.descriptor_for_uid(frame_uid)

    def frame_feature_matrix(
        self, frame_uids: Sequence[str]
    ) -> tuple[tuple[str, ...], np.ndarray, np.ndarray]:
        return self.frame_descriptor_table.matrix_for_uids(frame_uids)

    def environments_for_frame(self, frame_uid: str) -> tuple[UniversalAtomicEnvironmentDescriptor, ...]:
        return self._environments_by_frame_uid.get(frame_uid, ())

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": UNIVERSAL_STRUCTURAL_FEATURE_CATALOG_SCHEMA,
            "parser_version": self.parser_version,
            "dataset_id": self.dataset_id,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data4_bundle_digest": self.data4_bundle_digest,
            "material_profile_contracts_digest": self.material_profile_contracts_digest,
            "atom_group_catalog_digest": self.atom_group_catalog_digest,
            "provider_identity_digest": self.provider_identity.content_digest,
            "policy_digest": self.policy.policy_digest,
            "frame_descriptor_table_digest": self.frame_descriptor_table.content_digest,
            "atomic_environment_digests": [item.content_digest for item in self.atomic_environment_descriptors],
            "event_ids": [item.event_id for item in self.events],
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": UNIVERSAL_STRUCTURAL_FEATURE_CATALOG_SCHEMA,
            "parser_version": self.parser_version,
            "dataset_id": self.dataset_id,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data4_bundle_digest": self.data4_bundle_digest,
            "material_profile_contracts_digest": self.material_profile_contracts_digest,
            "atom_group_catalog_digest": self.atom_group_catalog_digest,
            "provider_identity": self.provider_identity.to_dict(),
            "policy": self.policy.to_dict(),
            "frame_descriptor_table": self.frame_descriptor_table.to_dict(),
            "atomic_environment_descriptors": [item.to_dict() for item in self.atomic_environment_descriptors],
            "events": [item.to_dict() for item in self.events],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "UniversalStructuralFeatureCatalog":
        schema = payload.get("schema")
        if schema not in {UNIVERSAL_STRUCTURAL_FEATURE_CATALOG_SCHEMA, UNIVERSAL_STRUCTURAL_FEATURE_CATALOG_LEGACY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported universal structural-feature catalog schema.")
        if payload.get("parser_version") not in (None, MLFF_DATA9A7B_PARSER_VERSION, MLFF_DATA9A7B_LEGACY_PARSER_VERSION):
            raise TrainingDataSerializationError("Unsupported universal structural-feature parser version.")
        if schema == UNIVERSAL_STRUCTURAL_FEATURE_CATALOG_SCHEMA:
            frame_descriptors: UniversalFrameDescriptorTable | Sequence[UniversalFrameStructuralDescriptor] = UniversalFrameDescriptorTable.from_dict(payload["frame_descriptor_table"])
        else:
            frame_descriptors = tuple(
                UniversalFrameStructuralDescriptor.from_dict(item)
                for item in payload["frame_descriptors"]
            )
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            data4_bundle_digest=str(payload["data4_bundle_digest"]),
            material_profile_contracts_digest=None if payload.get("material_profile_contracts_digest") is None else str(payload["material_profile_contracts_digest"]),
            atom_group_catalog_digest=None if payload.get("atom_group_catalog_digest") is None else str(payload["atom_group_catalog_digest"]),
            provider_identity=StructuralFeatureProviderIdentity.from_dict(payload["provider_identity"]),
            policy=UniversalStructuralSelectionPolicy.from_dict(payload["policy"]),
            frame_descriptors=frame_descriptors,
            atomic_environment_descriptors=tuple(UniversalAtomicEnvironmentDescriptor.from_dict(item) for item in payload.get("atomic_environment_descriptors", ())),
            events=tuple(GenericStructuralEventRecord.from_dict(item) for item in payload.get("events", ())),
            parser_version=str(payload.get("parser_version", MLFF_DATA9A7B_PARSER_VERSION)),
        )
        if schema == UNIVERSAL_STRUCTURAL_FEATURE_CATALOG_SCHEMA and payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Universal structural-feature catalog digest mismatch.")
        return result


@runtime_checkable
class AtomGroupMembershipProvider(Protocol):
    provider_id: str
    provider_version: str

    def resolve_group(
        self,
        group: AtomGroupDefinition,
        *,
        frame_record: Any,
        frame_data: Any,
        local_frame_index: int,
    ) -> tuple[int, ...]: ...


@runtime_checkable
class StructuralSelectionProvider(Protocol):
    provider_id: str
    provider_version: str

    def build_catalog(
        self,
        frame_catalog: Any,
        frame_data_by_run: Mapping[str, Any],
        data4_bundle: Any,
        *,
        frame_uids: tuple[str, ...],
        policy: UniversalStructuralSelectionPolicy | None = None,
        membership_provider: AtomGroupMembershipProvider | None = None,
        progress_callback: Callable[[str], None] | None = None,
        max_workers: int = 0,
    ) -> UniversalStructuralFeatureCatalog: ...


def _single_frame_collection(frame_data: Any, local_index: int, *, run_id: str) -> AtomisticFrameCollection:
    numbers = np.asarray(frame_data.atomic_numbers, dtype=np.int32)
    fractional = np.asarray(frame_data.fractional_positions[local_index], dtype=np.float64)
    wrapped = np.array(fractional, copy=True)
    pbc = np.asarray(frame_data.pbc, dtype=np.bool_)
    for axis in range(3):
        if pbc[axis]:
            wrapped[:, axis] %= 1.0
    return AtomisticFrameCollection(
        frame_semantics="ensemble",
        frame_ids=np.asarray([int(frame_data.frame_ids[local_index])], dtype=np.int64),
        atomic_numbers=numbers,
        masses=np.asarray(atomic_masses[numbers], dtype=np.float64),
        pbc=pbc,
        steps=None,
        times=None,
        cells=np.asarray(frame_data.cells_angstrom[local_index : local_index + 1], dtype=np.float64),
        origins=np.zeros((1, 3), dtype=np.float64),
        fractional_positions=wrapped[None, :, :],
        provenance=FrameCollectionProvenance(
            source_format="ase-structure-collection",
            source_files=(str(run_id),),
            velocity_source="unavailable",
            coordinate_normalization="independent_frame_wrapping",
            stress_source=None,
            units_source="training_data.FrameData",
        ),
        metadata={"training_data_run_id": str(run_id)},
    )


def _resolve_group_indices(
    catalog: AtomGroupCatalog | None,
    *,
    atomic_numbers: np.ndarray,
    frame_record: Any,
    frame_data: Any,
    local_index: int,
    membership_provider: AtomGroupMembershipProvider | None,
) -> dict[str, np.ndarray]:
    if catalog is None:
        return {"all_atoms": np.arange(atomic_numbers.size, dtype=np.int64)}
    by_id = {group.group_id: group for group in catalog.groups}
    resolved: dict[str, np.ndarray] = {}

    def resolve(group_id: str) -> np.ndarray:
        if group_id in resolved:
            return resolved[group_id]
        group = by_id[group_id]
        selector = group.selector
        if selector.kind is AtomGroupSelectorKind.ALL_ATOMS:
            indices = np.arange(atomic_numbers.size, dtype=np.int64)
        elif selector.kind is AtomGroupSelectorKind.ATOMIC_NUMBERS:
            indices = np.flatnonzero(np.isin(atomic_numbers, np.asarray(selector.atomic_numbers, dtype=np.int32)))
        elif selector.kind is AtomGroupSelectorKind.ATOM_INDICES:
            indices = np.asarray(selector.atom_indices, dtype=np.int64)
            if np.any(indices >= atomic_numbers.size):
                raise TrainingDataInputError(f"Atom group {group_id!r} contains an out-of-range atom index.")
        elif selector.kind in {AtomGroupSelectorKind.METADATA_VALUE, AtomGroupSelectorKind.PROVIDER}:
            if membership_provider is None:
                raise TrainingDataInputError(
                    f"Atom group {group_id!r} requires an AtomGroupMembershipProvider."
                )
            if selector.kind is AtomGroupSelectorKind.PROVIDER and selector.provider_identity is not None:
                if membership_provider.provider_id != selector.provider_identity.provider_id or membership_provider.provider_version != selector.provider_identity.provider_version:
                    raise TrainingDataInputError(f"Atom-group membership provider identity does not match group {group_id!r}.")
            indices = np.asarray(
                membership_provider.resolve_group(
                    group,
                    frame_record=frame_record,
                    frame_data=frame_data,
                    local_frame_index=local_index,
                ),
                dtype=np.int64,
            )
        else:
            sources = [set(int(value) for value in resolve(source)) for source in selector.source_group_ids]
            operation = selector.operation
            if operation is AtomGroupSetOperation.UNION:
                result_set = set().union(*sources)
            elif operation is AtomGroupSetOperation.INTERSECTION:
                result_set = set.intersection(*sources)
            elif operation is AtomGroupSetOperation.DIFFERENCE:
                result_set = set(sources[0])
                for source in sources[1:]:
                    result_set.difference_update(source)
            elif operation is AtomGroupSetOperation.COMPLEMENT:
                result_set = set(range(atomic_numbers.size)) - sources[0]
            else:  # pragma: no cover - enum guard
                raise TrainingDataInputError("Unsupported atom-group set operation.")
            indices = np.asarray(sorted(result_set), dtype=np.int64)
        indices = np.unique(indices)
        if np.any(indices < 0) or np.any(indices >= atomic_numbers.size):
            raise TrainingDataInputError(f"Atom group {group_id!r} contains invalid atom indices.")
        if indices.size == 0 and not group.allow_empty:
            raise TrainingDataInputError(f"Atom group {group_id!r} resolved empty but allow_empty is false.")
        resolved[group_id] = indices
        return indices

    for group_id in catalog.group_ids:
        resolve(group_id)
    return resolved


def _feature_family(feature_name: str) -> str:
    if feature_name.startswith("radial_density_"):
        return "radial_environment"
    if feature_name.startswith("angular_legendre_"):
        return "angular_environment"
    if feature_name.startswith("bond_orientational_"):
        return "orientational_order"
    if feature_name in {
        "nearest_neighbor_distance_angstrom",
        "weighted_neighbor_distance_mean_angstrom",
        "weighted_neighbor_distance_std_angstrom",
    }:
        return "pair_distance"
    if feature_name == "smooth_coordination":
        return "coordination"
    if feature_name in {"hard_neighbor_count", "weighted_degree_l2"}:
        return "connectivity"
    if feature_name == "neighbor_species_entropy":
        return "chemical_environment"
    if feature_name == "local_number_density_angstrom^-3":
        return "local_density"
    raise TrainingDataInputError(f"Unclassified universal structural feature {feature_name!r}.")


def _enabled_feature_indices_from_names(
    feature_names: tuple[str, ...],
    policy: UniversalStructuralSelectionPolicy,
) -> np.ndarray:
    enabled = set(policy.enabled_feature_families)
    indices = np.asarray(
        [
            index
            for index, name in enumerate(feature_names)
            if _feature_family(name) in enabled
        ],
        dtype=np.int64,
    )
    if indices.size == 0:
        raise TrainingDataInputError(
            "Universal structural policy disabled every local feature."
        )
    return indices


def _enabled_feature_indices(
    local: LocalStructureFeatureResult,
    policy: UniversalStructuralSelectionPolicy,
) -> np.ndarray:
    return _enabled_feature_indices_from_names(local.feature_names, policy)


def _aggregate(values: np.ndarray, missing: np.ndarray, statistic: str) -> tuple[float, bool]:
    valid = np.asarray(values, dtype=np.float64)[~np.asarray(missing, dtype=np.bool_)]
    if valid.size == 0:
        return 0.0, True
    if statistic == "mean":
        return float(np.mean(valid)), False
    if statistic == "std":
        return float(np.std(valid)), False
    if statistic == "min":
        return float(np.min(valid)), False
    if statistic == "max":
        return float(np.max(valid)), False
    quantile = {"q10": 10.0, "q50": 50.0, "q90": 90.0}[statistic]
    return float(np.percentile(valid, quantile)), False


@lru_cache(maxsize=256)
def _aggregate_feature_names(
    group_ids: tuple[str, ...],
    enabled_names: tuple[str, ...],
    statistics: tuple[str, ...],
) -> tuple[str, ...]:
    names: list[str] = []
    for group_id in group_ids:
        names.extend((f"group:{group_id}:atom_count", f"group:{group_id}:atom_fraction"))
        names.extend(
            f"group:{group_id}:{feature_name}:{statistic}"
            for feature_name in enabled_names
            for statistic in statistics
        )
    return tuple(names)


@dataclass(frozen=True, slots=True)
class _FrameAggregationPlan:
    """Static aggregation metadata reused for every frame in one run."""

    group_ids: tuple[str, ...]
    group_rows: tuple[np.ndarray, ...]
    enabled_indices: np.ndarray
    enabled_names: tuple[str, ...]
    feature_names: tuple[str, ...]
    membership: Mapping[int, tuple[str, ...]]
    quantile_statistics: tuple[str, ...]
    quantile_values: np.ndarray


def _build_frame_aggregation_plan(
    *,
    atom_indices: np.ndarray,
    atomic_numbers: np.ndarray,
    declared_groups: Mapping[str, np.ndarray],
    all_atomic_numbers: tuple[int, ...],
    policy: UniversalStructuralSelectionPolicy,
    build_membership: bool,
) -> _FrameAggregationPlan:
    atom_indices = np.asarray(atom_indices, dtype=np.int64)
    atomic_numbers = np.asarray(atomic_numbers, dtype=np.int32)
    group_indices: dict[str, np.ndarray] = {}
    if policy.include_declared_atom_groups:
        group_indices.update(
            {
                str(key): np.asarray(value, dtype=np.int64)
                for key, value in declared_groups.items()
            }
        )
    if policy.include_element_groups:
        for atomic_number in all_atomic_numbers:
            group_indices[f"element_Z{atomic_number}"] = atom_indices[
                atomic_numbers == atomic_number
            ]
    if not group_indices:
        group_indices["all_atoms"] = atom_indices

    identity_centers = np.array_equal(
        atom_indices, np.arange(atom_indices.size, dtype=np.int64)
    )
    membership_lists: dict[int, list[str]] | None = (
        {int(atom_index): [] for atom_index in atom_indices}
        if build_membership
        else None
    )
    group_ids = tuple(sorted(group_indices))
    group_rows: list[np.ndarray] = []
    for group_id in group_ids:
        selected = np.asarray(group_indices[group_id], dtype=np.int64)
        if identity_centers:
            valid = (selected >= 0) & (selected < atom_indices.size)
            rows = selected[valid]
        else:
            positions = np.searchsorted(atom_indices, selected)
            valid = positions < atom_indices.size
            if np.any(valid):
                clipped = np.minimum(positions, atom_indices.size - 1)
                valid &= atom_indices[clipped] == selected
            rows = positions[valid]
        rows = np.asarray(rows, dtype=np.int64)
        group_rows.append(rows)
        if membership_lists is not None:
            for atom_index in selected[valid]:
                membership_lists[int(atom_index)].append(group_id)

    enabled = _enabled_feature_indices_from_names(
        policy.local_structure_policy.feature_names, policy
    )
    enabled_names = tuple(
        policy.local_structure_policy.feature_names[int(index)] for index in enabled
    )
    quantile_statistics = tuple(
        statistic
        for statistic in policy.aggregate_statistics
        if statistic.startswith("q")
    )
    quantile_values = np.asarray(
        [float(statistic[1:]) for statistic in quantile_statistics],
        dtype=np.float64,
    )
    membership = (
        {}
        if membership_lists is None
        else {
            atom_index: tuple(sorted(groups))
            for atom_index, groups in membership_lists.items()
        }
    )
    return _FrameAggregationPlan(
        group_ids=group_ids,
        group_rows=tuple(group_rows),
        enabled_indices=enabled,
        enabled_names=enabled_names,
        feature_names=_aggregate_feature_names(
            group_ids, enabled_names, policy.aggregate_statistics
        ),
        membership=membership,
        quantile_statistics=quantile_statistics,
        quantile_values=quantile_values,
    )


def _column_percentiles_with_missing(
    values: np.ndarray,
    missing: np.ndarray,
    percentiles: np.ndarray,
) -> np.ndarray:
    """Vectorized NumPy-compatible linear percentiles by feature column.

    ``np.nanpercentile(..., axis=0)`` currently dispatches through
    ``apply_along_axis`` and therefore executes one Python quantile operation
    per feature. DATA6 invokes this for every atom group of every frame. One
    sort plus vectorized gathers preserves NumPy's default linear interpolation
    while removing that repeated interpreter overhead.
    """

    counts = np.count_nonzero(~missing, axis=0).astype(np.int64, copy=False)
    result = np.full(
        (int(percentiles.size), int(values.shape[1])),
        np.nan,
        dtype=np.float64,
    )
    valid = counts > 0
    if not np.any(valid) or percentiles.size == 0:
        return result

    # Columns can have different valid counts. Group equal-count columns so a
    # single np.partition call extracts only the order statistics actually
    # needed by the requested percentiles, rather than fully sorting every
    # atom-group feature column.
    for valid_count in np.unique(counts[valid]):
        columns = np.flatnonzero(counts == valid_count)
        positions = (int(valid_count) - 1) * (percentiles / 100.0)
        lower = np.floor(positions).astype(np.int64)
        upper = np.ceil(positions).astype(np.int64)
        work = np.where(missing[:, columns], np.inf, values[:, columns])
        kth = np.unique(np.concatenate((lower, upper)))
        if work.shape[0] <= 32 or kth.size >= work.shape[0] // 2:
            ordered = np.sort(work, axis=0)
        else:
            ordered = np.partition(work, kth=kth, axis=0)
        column_positions = np.arange(columns.size, dtype=np.int64)[None, :]
        lower_values = ordered[lower[:, None], column_positions]
        upper_values = ordered[upper[:, None], column_positions]
        fraction = (positions - lower)[:, None]
        result[:, columns] = lower_values + fraction * (
            upper_values - lower_values
        )
    return result


def _frame_aggregate_from_plan(
    local: LocalStructureFeatureResult,
    *,
    plan: _FrameAggregationPlan,
    policy: UniversalStructuralSelectionPolicy,
) -> tuple[tuple[str, ...], np.ndarray, np.ndarray, Mapping[int, tuple[str, ...]]]:
    if local.feature_names != policy.local_structure_policy.feature_names:
        raise TrainingDataInputError(
            "Local structural feature ordering changed during universal aggregation."
        )
    total_atoms = max(1, local.atom_indices.size)
    feature_count = int(plan.enabled_indices.size)
    statistics = tuple(policy.aggregate_statistics)
    statistic_count = len(statistics)
    aggregate_size = feature_count * statistic_count
    group_width = 2 + aggregate_size
    values_out = np.empty(len(plan.group_rows) * group_width, dtype=np.float64)
    missing_out = np.zeros(values_out.shape, dtype=np.bool_)
    cursor = 0

    for rows in plan.group_rows:
        values_out[cursor] = float(rows.size)
        values_out[cursor + 1] = float(rows.size / total_atoms)
        cursor += 2
        if rows.size == 0:
            values_out[cursor : cursor + aggregate_size] = policy.missing_value_fill
            missing_out[cursor : cursor + aggregate_size] = True
            cursor += aggregate_size
            continue

        block_values = np.asarray(
            local.values[np.ix_(rows, plan.enabled_indices)], dtype=np.float64
        )
        block_missing = np.asarray(
            local.missing_mask[np.ix_(rows, plan.enabled_indices)], dtype=np.bool_
        )
        valid = ~block_missing
        valid_count = np.count_nonzero(valid, axis=0)
        all_missing = valid_count == 0
        statistic_matrix = np.empty(
            (feature_count, statistic_count), dtype=np.float64
        )
        statistic_index = {name: index for index, name in enumerate(statistics)}

        means: np.ndarray | None = None
        if "mean" in statistic_index or "std" in statistic_index:
            sums = np.sum(block_values, axis=0, where=valid, initial=0.0)
            means = np.divide(
                sums,
                valid_count,
                out=np.zeros(feature_count, dtype=np.float64),
                where=valid_count > 0,
            )
            if "mean" in statistic_index:
                statistic_matrix[:, statistic_index["mean"]] = means
            if "std" in statistic_index:
                centered_squared = np.empty_like(block_values)
                np.subtract(block_values, means[None, :], out=centered_squared)
                np.square(centered_squared, out=centered_squared)
                variance = np.divide(
                    np.sum(
                        centered_squared,
                        axis=0,
                        where=valid,
                        initial=0.0,
                    ),
                    valid_count,
                    out=np.zeros(feature_count, dtype=np.float64),
                    where=valid_count > 0,
                )
                statistic_matrix[:, statistic_index["std"]] = np.sqrt(
                    np.maximum(variance, 0.0)
                )
        if "min" in statistic_index:
            statistic_matrix[:, statistic_index["min"]] = np.min(
                block_values, axis=0, where=valid, initial=np.inf
            )
        if "max" in statistic_index:
            statistic_matrix[:, statistic_index["max"]] = np.max(
                block_values, axis=0, where=valid, initial=-np.inf
            )
        if plan.quantile_statistics:
            quantiles = _column_percentiles_with_missing(
                block_values, block_missing, plan.quantile_values
            )
            for row_index, statistic in enumerate(plan.quantile_statistics):
                statistic_matrix[:, statistic_index[statistic]] = quantiles[row_index]

        missing_matrix = all_missing[:, None] | ~np.isfinite(statistic_matrix)
        flat_values = statistic_matrix.reshape(-1)
        flat_missing = missing_matrix.reshape(-1)
        target = values_out[cursor : cursor + aggregate_size]
        target[:] = flat_values
        target[flat_missing] = policy.missing_value_fill
        missing_out[cursor : cursor + aggregate_size] = flat_missing
        cursor += aggregate_size

    values_out.setflags(write=False)
    missing_out.setflags(write=False)
    return plan.feature_names, values_out, missing_out, plan.membership


def _frame_aggregate(
    local: LocalStructureFeatureResult,
    *,
    declared_groups: Mapping[str, np.ndarray],
    all_atomic_numbers: tuple[int, ...],
    policy: UniversalStructuralSelectionPolicy,
    build_membership: bool,
) -> tuple[tuple[str, ...], np.ndarray, np.ndarray, Mapping[int, tuple[str, ...]]]:
    """Compatibility path for frame-dependent membership providers."""

    plan = _build_frame_aggregation_plan(
        atom_indices=local.atom_indices,
        atomic_numbers=local.atomic_numbers,
        declared_groups=declared_groups,
        all_atomic_numbers=all_atomic_numbers,
        policy=policy,
        build_membership=build_membership,
    )
    return _frame_aggregate_from_plan(local, plan=plan, policy=policy)


def _resident_set_mib() -> float | None:
    try:
        import resource

        value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return value / (
            1024.0 if sys.platform != "darwin" else 1024.0 * 1024.0
        )
    except Exception:  # pragma: no cover - platform dependent
        return None


def _automatic_structural_worker_cap(task_count: int) -> int:
    """Return the safe outer-thread search bound for structural kernels."""

    if task_count <= 1:
        return 1
    cpu_budget = max(1, int(math.floor(available_cpu_threads() * 0.9)))
    # These frames already contain internally vectorized NumPy/SciPy kernels.
    # Higher outer concurrency usually saturates memory bandwidth and increases
    # the simultaneous exact-MIC working set. The final choice is autotuned.
    return max(1, min(task_count, cpu_budget, 8))


def _autotune_structural_workers(
    compute_record: Callable[[Any], Any],
    records: Sequence[Any],
    *,
    worker_cap: int,
) -> tuple[int, tuple[tuple[int, float], ...]]:
    """Benchmark a tiny representative prefix and choose economical threads.

    CPU count alone is a poor predictor for this stage: exact MIC, radial
    tensors, and angular reductions are memory-bandwidth-heavy. A 2--3 second
    microbenchmark is negligible for a tens-of-thousands-frame campaign and
    avoids making eight threads slower than two on a particular NUMA/cache
    topology. Within five percent of the fastest rate, fewer workers win.
    """

    cap = max(1, min(int(worker_cap), len(records)))
    if cap <= 1 or len(records) < 8:
        return 1, ((1, 0.0),)
    candidates = tuple(
        value for value in (1, 2, 4, 8) if value <= cap
    )
    if candidates[-1] != cap:
        candidates = tuple(sorted(set((*candidates, cap))))
    sample_count = min(len(records), max(12, 2 * cap), 24)
    if sample_count == len(records):
        sample = tuple(records)
    else:
        sample_indices = np.linspace(
            0, len(records) - 1, sample_count, dtype=np.int64
        )
        sample = tuple(records[int(index)] for index in sample_indices)

    # Warm chemistry/cell caches before timing any candidate so the first
    # candidate is not penalized by one-time setup.
    compute_record(sample[0])
    rates: list[tuple[int, float]] = []
    try:
        from threadpoolctl import threadpool_limits

        thread_limits = threadpool_limits(limits=1)
    except ModuleNotFoundError:  # pragma: no cover - optional package
        thread_limits = nullcontext()
    with thread_limits:
        for workers in candidates:
            started = time.perf_counter()
            if workers == 1:
                for record in sample:
                    compute_record(record)
            else:
                with ThreadPoolExecutor(
                    max_workers=workers,
                    thread_name_prefix="mdstats-structure-tune",
                ) as executor:
                    tuple(executor.map(compute_record, sample))
            elapsed = max(time.perf_counter() - started, 1.0e-12)
            rates.append((workers, sample_count / elapsed))
    fastest = max(rate for _, rate in rates)
    economical = [
        workers for workers, rate in rates if rate >= 0.95 * fastest
    ]
    return min(economical), tuple(rates)


def _append_transition_events(
    events: list[GenericStructuralEventRecord],
    *,
    previous_record: Any,
    current_record: Any,
    previous_result: LocalStructureFeatureResult,
    current_result: LocalStructureFeatureResult,
    previous_fractional: np.ndarray,
    current_fractional: np.ndarray,
    current_cell: np.ndarray,
    pbc: np.ndarray,
    provider_identity_digest: str,
    policy: UniversalStructuralSelectionPolicy,
) -> None:
    gap = int(current_record.source_frame_index - previous_record.source_frame_index)
    if gap <= 0 or gap > policy.maximum_source_frame_gap:
        return
    if not np.array_equal(previous_result.atom_indices, current_result.atom_indices):
        raise TrainingDataInputError(
            "Temporal structural events require stable atom indexing within each run."
        )
    feature_index = {
        name: index for index, name in enumerate(policy.local_structure_policy.feature_names)
    }
    enabled_events = set(policy.enabled_event_types)
    event_specs = tuple(
        spec
        for spec in (
            ("smooth_coordination_change", "smooth_coordination", policy.coordination_event_threshold),
            ("hard_neighbor_count_change", "hard_neighbor_count", float(policy.hard_neighbor_event_threshold)),
            ("local_density_change", "local_number_density_angstrom^-3", policy.density_event_threshold_angstrom3_inv),
            ("orientational_order_change", "bond_orientational_q6", policy.orientational_event_threshold),
        )
        if spec[0] in enabled_events and spec[1] in feature_index
    )
    for event_type, feature_name, threshold in event_specs:
        column = feature_index[feature_name]
        delta = np.abs(current_result.values[:, column] - previous_result.values[:, column])
        valid = ~(current_result.missing_mask[:, column] | previous_result.missing_mask[:, column])
        for row in np.flatnonzero(valid & (delta >= threshold)):
            events.append(GenericStructuralEventRecord(
                event_type=event_type,
                run_id=current_record.run_id,
                previous_frame_uid=previous_record.frame_uid,
                current_frame_uid=current_record.frame_uid,
                atom_index=int(current_result.atom_indices[row]),
                atomic_number=int(current_result.atomic_numbers[row]),
                magnitude=float(delta[row]),
                threshold=float(threshold),
                source_frame_gap=gap,
                provider_identity_digest=provider_identity_digest,
            ))

    if "large_atomic_displacement" not in enabled_events:
        return
    # Same-atom motion needs only N displacement vectors.  The previous code
    # constructed an N x N center-neighbor tensor and then selected its
    # diagonal, adding avoidable O(N^2) work and memory for every transition.
    delta_fractional = np.asarray(current_fractional - previous_fractional, dtype=np.float64)
    for axis in range(3):
        if bool(pbc[axis]):
            delta_fractional[:, axis] -= np.rint(delta_fractional[:, axis])
    magnitudes = np.linalg.norm(delta_fractional @ current_cell, axis=1)
    for atom_index in np.flatnonzero(
        magnitudes >= policy.displacement_event_threshold_angstrom
    ):
        events.append(GenericStructuralEventRecord(
            event_type="large_atomic_displacement",
            run_id=current_record.run_id,
            previous_frame_uid=previous_record.frame_uid,
            current_frame_uid=current_record.frame_uid,
            atom_index=int(atom_index),
            atomic_number=int(current_result.atomic_numbers[atom_index]),
            magnitude=float(magnitudes[atom_index]),
            threshold=policy.displacement_event_threshold_angstrom,
            source_frame_gap=gap,
            provider_identity_digest=provider_identity_digest,
        ))


@dataclass(frozen=True, slots=True)
class UniversalStructuralSelectionProvider:
    provider_id: str = UNIVERSAL_STRUCTURAL_PROVIDER_ID
    provider_version: str = UNIVERSAL_STRUCTURAL_PROVIDER_VERSION

    def build_catalog(
        self,
        frame_catalog: Any,
        frame_data_by_run: Mapping[str, Any],
        data4_bundle: Any,
        *,
        frame_uids: tuple[str, ...],
        policy: UniversalStructuralSelectionPolicy | None = None,
        membership_provider: AtomGroupMembershipProvider | None = None,
        progress_callback: Callable[[str], None] | None = None,
        max_workers: int = 0,
    ) -> UniversalStructuralFeatureCatalog:
        active = UniversalStructuralSelectionPolicy() if policy is None else policy
        if data4_bundle.frame_catalog_digest != frame_catalog.content_digest:
            raise TrainingDataInputError(
                "Universal structural features require matching DATA4/frame lineage."
            )
        included = frozenset(
            validate_digest(value, name="frame_uid") for value in frame_uids
        )
        records = tuple(
            record for record in frame_catalog.frames if record.frame_uid in included
        )
        if {record.frame_uid for record in records} != set(included):
            raise TrainingDataInputError(
                "Universal structural feature domain contains unknown frame UIDs."
            )
        if not records:
            raise TrainingDataInputError(
                "Universal structural feature domain is empty."
            )
        if isinstance(max_workers, bool) or int(max_workers) < 0:
            raise TrainingDataInputError(
                "max_workers must be zero (automatic) or a positive integer."
            )

        contracts: MaterialProfileContracts | None = (
            data4_bundle.material_profile_contracts
        )
        group_catalog = None if contracts is None else contracts.atom_groups
        selected_run_ids = {record.run_id for record in records}
        all_atomic_numbers = tuple(
            sorted(
                {
                    int(value)
                    for run_id in selected_run_ids
                    for value in np.asarray(
                        frame_data_by_run[run_id].atomic_numbers
                    )
                }
            )
        )
        provider_identity = StructuralFeatureProviderIdentity(
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            policy_digest=active.policy_digest,
        )
        provider_digest = provider_identity.content_digest
        frame_index = build_frame_array_index(frame_catalog, frame_data_by_run)

        output_records = tuple(sorted(records, key=lambda item: item.frame_uid))
        output_index = {
            record.frame_uid: index for index, record in enumerate(output_records)
        }
        chronological = tuple(
            sorted(
                records,
                key=lambda item: (
                    item.run_id,
                    item.source_frame_index,
                    item.frame_uid,
                ),
            )
        )

        requested_workers = int(max_workers)
        worker_count = (
            _automatic_structural_worker_cap(len(chronological))
            if requested_workers == 0
            else min(requested_workers, len(chronological))
        )
        # A dynamic membership provider may depend on chronological state or
        # external non-thread-safe resources. Preserve its original serial
        # contract; static material-profile groups use the parallel fast path.
        if membership_provider is not None:
            worker_count = 1

        aggregation_plans_by_run: dict[str, _FrameAggregationPlan] = {}
        topology_workspaces_by_run: dict[str, Any] = {}
        first_record_by_run: dict[str, Any] = {}
        for record in chronological:
            first_record_by_run.setdefault(record.run_id, record)
        for run_id, record in first_record_by_run.items():
            _, frame_data, local_index = frame_index[record.frame_uid]
            numbers = np.asarray(frame_data.atomic_numbers, dtype=np.int32)
            topology_workspaces_by_run[run_id] = _local_structure_topology_workspace(
                numbers, policy=active.local_structure_policy
            )
            if membership_provider is None:
                groups = _resolve_group_indices(
                    group_catalog,
                    atomic_numbers=numbers,
                    frame_record=record,
                    frame_data=frame_data,
                    local_index=local_index,
                    membership_provider=None,
                )
                aggregation_plans_by_run[run_id] = _build_frame_aggregation_plan(
                    atom_indices=np.arange(numbers.size, dtype=np.int64),
                    atomic_numbers=numbers,
                    declared_groups=groups,
                    all_atomic_numbers=all_atomic_numbers,
                    policy=active,
                    build_membership=active.materialize_atomic_environments,
                )

        frame_values: np.ndarray | None = None
        frame_missing: np.ndarray | None = None
        atom_counts = np.empty(len(records), dtype=np.int32)
        warning_codes: list[tuple[str, ...] | None] = [None] * len(records)
        expected_frame_names: tuple[str, ...] | None = None
        atomic_descriptors_by_frame: dict[
            str, list[UniversalAtomicEnvironmentDescriptor]
        ] = {}
        events_by_frame: dict[str, list[GenericStructuralEventRecord]] = {}
        event_count = 0
        previous_by_run: dict[
            str, tuple[Any, LocalStructureFeatureResult, np.ndarray]
        ] = {}
        progress_interval = max(100, min(1_000, len(records) // 100 or 1))
        started = time.monotonic()
        last_report_time = started
        last_report_completed = 0
        progress_timing = ProgressRateTracker(
            completed=0,
            started_at=started,
            minimum_recent_window_seconds=1.0,
        )

        if progress_callback is not None:
            membership_note = (
                "; dynamic membership forced serial execution"
                if membership_provider is not None
                else ""
            )
            worker_note = (
                f"autotune<={worker_count}"
                if requested_workers == 0 and membership_provider is None
                else str(worker_count)
            )
            progress_callback(
                f"universal structure; status=start; progress={format_progress_fraction(0, len(records))}; "
                f"workers={worker_note}; "
                f"atomic-environment materialization="
                f"{'on' if active.materialize_atomic_environments else 'off'}"
                f"{membership_note}"
            )

        worker_local = threading.local()

        def compute_record(record: Any) -> tuple[
            Any,
            LocalStructureFeatureResult,
            tuple[str, ...],
            np.ndarray,
            np.ndarray,
            Mapping[int, tuple[str, ...]],
            np.ndarray,
            np.ndarray,
            np.ndarray,
        ]:
            _, frame_data, local_index = frame_index[record.frame_uid]
            scratch = getattr(worker_local, "local_structure_scratch", None)
            if scratch is None:
                scratch = _LocalStructureScratch()
                worker_local.local_structure_scratch = scratch
            local = _compute_local_structure_features_arrays(
                atomic_numbers=frame_data.atomic_numbers,
                fractional_positions=frame_data.fractional_positions[local_index],
                cell=frame_data.cells_angstrom[local_index],
                pbc=frame_data.pbc,
                frame_index=0,
                policy=active.local_structure_policy,
                topology_workspace=topology_workspaces_by_run[record.run_id],
                scratch=scratch,
                wrap_periodic=True,
            )
            if membership_provider is None:
                names, values, missing, membership = _frame_aggregate_from_plan(
                    local,
                    plan=aggregation_plans_by_run[record.run_id],
                    policy=active,
                )
            else:
                groups = _resolve_group_indices(
                    group_catalog,
                    atomic_numbers=np.asarray(
                        frame_data.atomic_numbers, dtype=np.int32
                    ),
                    frame_record=record,
                    frame_data=frame_data,
                    local_index=local_index,
                    membership_provider=membership_provider,
                )
                names, values, missing, membership = _frame_aggregate(
                    local,
                    declared_groups=groups,
                    all_atomic_numbers=all_atomic_numbers,
                    policy=active,
                    build_membership=active.materialize_atomic_environments,
                )
            return (
                record,
                local,
                names,
                values,
                missing,
                membership,
                np.asarray(
                    frame_data.fractional_positions[local_index],
                    dtype=np.float64,
                ),
                np.asarray(
                    frame_data.cells_angstrom[local_index], dtype=np.float64
                ),
                np.asarray(frame_data.pbc, dtype=np.bool_),
            )

        if requested_workers == 0 and membership_provider is None:
            worker_count, tuning_rates = _autotune_structural_workers(
                compute_record, chronological, worker_cap=worker_count
            )
            if progress_callback is not None:
                rate_text = ", ".join(
                    f"{workers}={rate:.1f} frame/s"
                    for workers, rate in tuning_rates
                    if rate > 0.0
                )
                progress_callback(
                    f"universal structure; status=autotune; selected_workers={worker_count}; candidates={rate_text}"
                )

        def consume_result(
            result: tuple[
                Any,
                LocalStructureFeatureResult,
                tuple[str, ...],
                np.ndarray,
                np.ndarray,
                Mapping[int, tuple[str, ...]],
                np.ndarray,
                np.ndarray,
                np.ndarray,
            ],
            completed: int,
        ) -> None:
            nonlocal frame_values, frame_missing, expected_frame_names
            nonlocal last_report_time, last_report_completed
            nonlocal event_count
            (
                record,
                local,
                names,
                values,
                missing,
                membership,
                fractional,
                cell,
                pbc,
            ) = result
            if expected_frame_names is None:
                expected_frame_names = names
                frame_values = np.empty(
                    (len(records), len(names)), dtype=np.float64
                )
                frame_missing = np.empty(
                    (len(records), len(names)), dtype=np.bool_
                )
            elif names != expected_frame_names:
                raise TrainingDataInputError(
                    "Universal structural frame feature ordering changed "
                    "across frames."
                )
            assert frame_values is not None and frame_missing is not None
            row_index = output_index[record.frame_uid]
            frame_values[row_index] = values
            frame_missing[row_index] = missing
            atom_counts[row_index] = int(local.atom_indices.size)
            warning_codes[row_index] = local.warning_codes

            if active.materialize_atomic_environments:
                enabled_indices = _enabled_feature_indices(local, active)
                enabled_names = tuple(
                    local.feature_names[int(index)] for index in enabled_indices
                )
                frame_atomic_descriptors: list[
                    UniversalAtomicEnvironmentDescriptor
                ] = []
                for row, atom_index in enumerate(local.atom_indices):
                    atomic_number = int(local.atomic_numbers[row])
                    symbol = (
                        chemical_symbols[atomic_number]
                        if atomic_number < len(chemical_symbols)
                        else f"Z{atomic_number}"
                    )
                    frame_atomic_descriptors.append(
                        UniversalAtomicEnvironmentDescriptor(
                            frame_uid=record.frame_uid,
                            atom_index=int(atom_index),
                            atomic_number=atomic_number,
                            symbol=symbol,
                            named_features=_feature_pairs(
                                enabled_names,
                                local.values[row, enabled_indices],
                            ),
                            missing_mask=tuple(
                                bool(value)
                                for value in local.missing_mask[
                                    row, enabled_indices
                                ]
                            ),
                            atom_group_ids=membership[int(atom_index)],
                            provider_identity_digest=provider_digest,
                            frame_record_digest=record.content_digest,
                        )
                    )
                atomic_descriptors_by_frame[record.frame_uid] = (
                    frame_atomic_descriptors
                )

            previous = previous_by_run.get(record.run_id)
            if previous is not None:
                previous_record, previous_local, previous_fractional = previous
                frame_events: list[GenericStructuralEventRecord] = []
                _append_transition_events(
                    frame_events,
                    previous_record=previous_record,
                    current_record=record,
                    previous_result=previous_local,
                    current_result=local,
                    previous_fractional=previous_fractional,
                    current_fractional=fractional,
                    current_cell=cell,
                    pbc=pbc,
                    provider_identity_digest=provider_digest,
                    policy=active,
                )
                if frame_events:
                    frame_events.sort(
                        key=lambda item: (item.event_type, item.atom_index)
                    )
                    events_by_frame[record.frame_uid] = frame_events
                    event_count += len(frame_events)
            previous_by_run[record.run_id] = (
                record,
                local,
                np.array(fractional, copy=True),
            )

            now = time.monotonic()
            if progress_callback is not None and (
                completed == len(records)
                or completed - last_report_completed >= progress_interval
                or now - last_report_time >= 30.0
            ):
                timing = progress_timing.snapshot(
                    completed=completed, total=len(records), now=now
                )
                rss = _resident_set_mib()
                rss_text = "" if rss is None else f"; peak_rss={rss:,.0f} MiB"
                progress_callback(
                    f"universal structure; progress={format_progress_fraction(completed, len(records))}; "
                    f"elapsed={format_progress_time(timing.elapsed_seconds)}; "
                    f"eta={format_progress_time(timing.eta_seconds)}; "
                    f"recent={format_progress_rate(timing.recent_rate, 'frame/s')}; "
                    f"avg={format_progress_rate(timing.average_rate, 'frame/s')}; "
                    f"events={event_count:,}{rss_text}"
                )
                last_report_time = now
                last_report_completed = completed

        structural_resources = detect_system_resources(
            cpu_fraction=1.0, ram_fraction=1.0, gpu_memory_fraction=1.0, device="cpu"
        )
        # The worker count has already been bounded by available_cpu_threads().
        # Keep native BLAS/OpenMP at one thread while frame-level structural
        # workers are active so nested libraries cannot multiply the stage CPU
        # budget. The scope is execution-only and never enters scientific
        # authority.
        structural_scope = build_stage_resource_scope(
            structural_resources,
            stage_name="DATA6-structural",
            structural_workers=worker_count,
            blas_threads=1,
        )
        with stage_resource_scope(structural_scope):
            if worker_count == 1:
                for completed, record in enumerate(chronological, start=1):
                    consume_result(compute_record(record), completed)
            else:
                chunk_size = max(worker_count * 4, 16)
                with ThreadPoolExecutor(
                    max_workers=worker_count,
                    thread_name_prefix="mdstats-structure",
                ) as executor:
                    completed = 0
                    for start in range(0, len(chronological), chunk_size):
                        chunk = chronological[start : start + chunk_size]
                        for result in executor.map(compute_record, chunk):
                            completed += 1
                            consume_result(result, completed)

        assert expected_frame_names is not None
        assert frame_values is not None and frame_missing is not None
        if any(value is None for value in warning_codes):
            raise RuntimeError(
                "Universal structural frame table was not filled completely."
            )
        atomic_descriptors = tuple(
            item
            for record in output_records
            for item in atomic_descriptors_by_frame.get(record.frame_uid, ())
        )
        events = tuple(
            item
            for record in output_records
            for item in events_by_frame.get(record.frame_uid, ())
        )
        table = UniversalFrameDescriptorTable(
            frame_uids=tuple(record.frame_uid for record in output_records),
            frame_record_digests=tuple(
                record.content_digest for record in output_records
            ),
            provider_identity_digest=provider_digest,
            feature_names=expected_frame_names,
            values=frame_values,
            missing_mask=frame_missing,
            atom_counts=atom_counts,
            warning_codes=tuple(
                value for value in warning_codes if value is not None
            ),
        )
        return UniversalStructuralFeatureCatalog(
            dataset_id=frame_catalog.dataset_id,
            frame_catalog_digest=frame_catalog.content_digest,
            data4_bundle_digest=data4_bundle.content_digest,
            material_profile_contracts_digest=(
                None if contracts is None else contracts.content_digest
            ),
            atom_group_catalog_digest=(
                None if group_catalog is None else group_catalog.content_digest
            ),
            provider_identity=provider_identity,
            policy=active,
            frame_descriptors=table,
            atomic_environment_descriptors=tuple(atomic_descriptors),
            events=tuple(events),
        )


def build_universal_structural_feature_catalog(
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    data4_bundle: Any,
    *,
    frame_uids: tuple[str, ...],
    policy: UniversalStructuralSelectionPolicy | None = None,
    membership_provider: AtomGroupMembershipProvider | None = None,
    progress_callback: Callable[[str], None] | None = None,
    max_workers: int = 0,
) -> UniversalStructuralFeatureCatalog:
    """Convenience facade for the built-in universal provider."""

    return UniversalStructuralSelectionProvider().build_catalog(
        frame_catalog,
        frame_data_by_run,
        data4_bundle,
        frame_uids=frame_uids,
        policy=policy,
        membership_provider=membership_provider,
        progress_callback=progress_callback,
        max_workers=max_workers,
    )
