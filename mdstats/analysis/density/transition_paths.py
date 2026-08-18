"""Stage-11E6b observed transition-path and collective-event diagnostics.

The stage reconstructs registered paths from immutable Stage-11E6 passage
records and the Stage-11E0b compact sample catalog.  It never interpolates a
core hit, bridges unsupported evidence, estimates a rate, or promotes a density
shoulder to a state.  Periodic translations are derived from retained integer
image bookkeeping, and path pooling requires an explicit registration
compatibility certificate.

Core-set transition-path ensembles are standard background.  The exact
first-hit taxonomy, source binding, cadence provenance, periodic-translation
identity, structural-evidence table, collective-context rules, and
registration-compatibility certificate are mdstats-specific constructions.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
import hashlib
import json
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ..site_samples import FrameworkAlignedIonSampleCatalog
from .final_segmentation import (
    FinalHystereticSegmentationCatalog,
    FinalPassageInterval,
    FinalPassageOutcome,
)

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
Int32Array = NDArray[np.int32]
BoolArray = NDArray[np.bool_]

TRANSITION_PATH_STAGE = "11E6b"
TRANSITION_PATH_OPTIONS_SCHEMA = "mdstats.transition-path-options.v1"
TRANSITION_PATH_RESOURCES_SCHEMA = "mdstats.transition-path-resources.v1"
PATH_EVIDENCE_TABLE_SCHEMA = "mdstats.transition-path-evidence-table.v1"
REGISTRATION_COMPATIBILITY_SCHEMA = "mdstats.registration-compatibility-class.v1"
OCCUPANCY_CONTEXT_SCHEMA = "mdstats.transition-occupancy-context.v1"
OBSERVED_TRANSITION_EVENT_SCHEMA = "mdstats.observed-transition-event.v1"
TRANSITION_PATH_ENSEMBLE_SCHEMA = "mdstats.transition-path-ensemble.v1"
TRANSITION_PATH_CATALOG_SCHEMA = "mdstats.transition-path-catalog.v1"


class TransitionPathError(ValueError):
    """Base Stage-11E6b error."""


class TransitionPathInputError(TransitionPathError):
    """Raised when source binding or path evidence is inconsistent."""


class TransitionPathResourceError(TransitionPathError):
    """Raised transactionally before declared work limits are exceeded."""


class TransitionPathSerializationError(TransitionPathError):
    """Raised when serialized E6b data are malformed or tampered with."""


class FirstHitResolutionStatus(str, Enum):
    RESOLVED_FIRST_HIT = "resolved_first_hit"
    TEMPORALLY_BRACKETED_FIRST_HIT = "temporally_bracketed_first_hit"
    MULTIPLE_TARGETS_BETWEEN_FRAMES = "multiple_targets_between_frames"
    TARGET_AMBIGUOUS = "target_ambiguous"
    GAP_INTERRUPTED = "gap_interrupted"
    FAILED_EXCURSION = "failed_excursion"
    RECROSSING = "recrossing"
    RIGHT_CENSORED = "right_censored"


class PathEvidenceStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class CollectiveEventStatus(str, Enum):
    ISOLATED_SINGLE_ION = "isolated_single_ion"
    TEMPORALLY_OVERLAPPING = "temporally_overlapping"
    CANDIDATE_EXCHANGE = "candidate_exchange"
    CANDIDATE_CONCERTED = "candidate_concerted"
    COLLECTIVE_UNRESOLVED = "collective_unresolved"


class PathEnsembleStatus(str, Enum):
    SINGLE_OBSERVED_PATH = "single_observed_path"
    PATH_ENSEMBLE_UNDERSAMPLED = "path_ensemble_undersampled"
    PATH_ENSEMBLE_RESOLVED = "path_ensemble_resolved"


class PathClusteringStatus(str, Enum):
    NOT_REQUESTED = "not_requested"
    INSUFFICIENT_PATHS = "insufficient_paths"
    RESOLVED = "resolved"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _array_digest(value: np.ndarray) -> str:
    arr = np.ascontiguousarray(value)
    h = hashlib.sha256()
    h.update(arr.dtype.str.encode("ascii")); h.update(str(arr.shape).encode("ascii")); h.update(arr.tobytes(order="C"))
    return h.hexdigest()


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise TransitionPathInputError(f"{name} must be a SHA-256 digest.")
    return value


def _readonly(value: Any, *, dtype: Any, ndim: int, name: str, shape: tuple[int, ...] | None = None) -> np.ndarray:
    arr = np.array(value, dtype=dtype, copy=True, order="C")
    if arr.ndim != ndim or (shape is not None and arr.shape != shape):
        raise TransitionPathInputError(f"{name} has invalid shape {arr.shape}.")
    if np.issubdtype(arr.dtype, np.floating) and np.any(~np.isfinite(arr)):
        raise TransitionPathInputError(f"{name} contains non-finite values.")
    arr.setflags(write=False)
    return arr


def _freeze(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        result = float(value)
        if not np.isfinite(result):
            raise TransitionPathInputError("Metadata contains a non-finite float.")
        return result
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in sorted(value.items(), key=lambda p: str(p[0]))})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    raise TransitionPathInputError(f"Unsupported metadata value {type(value).__name__}.")


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in sorted(value.items())}
    if isinstance(value, tuple):
        return [_json_value(v) for v in value]
    if isinstance(value, np.generic):
        return _json_value(value.item())
    return value


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or int(value) <= 0:
        raise TransitionPathInputError(f"{name} must be a positive integer.")
    return int(value)


def _nonnegative(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise TransitionPathInputError(f"{name} must be finite and nonnegative.")
    return result


@dataclass(frozen=True, slots=True)
class TransitionPathOptions:
    include_failed_passages: bool = True
    concurrent_frame_window: int = 0
    minimum_paths_for_resolved_ensemble: int = 3
    enable_path_clustering: bool = False
    minimum_paths_for_clustering: int = 5
    clustering_rmsd_threshold: float = 0.35
    clustering_resample_points: int = 24
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        window = int(self.concurrent_frame_window)
        if window < 0:
            raise TransitionPathInputError("concurrent_frame_window must be nonnegative.")
        resolved = _positive_int(self.minimum_paths_for_resolved_ensemble, "minimum_paths_for_resolved_ensemble")
        minimum_cluster = _positive_int(self.minimum_paths_for_clustering, "minimum_paths_for_clustering")
        threshold = _nonnegative(self.clustering_rmsd_threshold, "clustering_rmsd_threshold")
        points = _positive_int(self.clustering_resample_points, "clustering_resample_points")
        if points < 2:
            raise TransitionPathInputError("clustering_resample_points must be at least two.")
        metadata = _freeze(dict(self.metadata))
        payload = {
            "schema": TRANSITION_PATH_OPTIONS_SCHEMA,
            "include_failed_passages": bool(self.include_failed_passages),
            "concurrent_frame_window": window,
            "minimum_paths_for_resolved_ensemble": resolved,
            "enable_path_clustering": bool(self.enable_path_clustering),
            "minimum_paths_for_clustering": minimum_cluster,
            "clustering_rmsd_threshold": threshold,
            "clustering_resample_points": points,
            "metadata": _json_value(metadata),
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise TransitionPathInputError("Transition-path options signature is inconsistent.")
        for name, value in (
            ("include_failed_passages", bool(self.include_failed_passages)),
            ("concurrent_frame_window", window),
            ("minimum_paths_for_resolved_ensemble", resolved),
            ("enable_path_clustering", bool(self.enable_path_clustering)),
            ("minimum_paths_for_clustering", minimum_cluster),
            ("clustering_rmsd_threshold", threshold),
            ("clustering_resample_points", points),
            ("metadata", metadata), ("signature", expected),
        ):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TRANSITION_PATH_OPTIONS_SCHEMA,
            "include_failed_passages": self.include_failed_passages,
            "concurrent_frame_window": self.concurrent_frame_window,
            "minimum_paths_for_resolved_ensemble": self.minimum_paths_for_resolved_ensemble,
            "enable_path_clustering": self.enable_path_clustering,
            "minimum_paths_for_clustering": self.minimum_paths_for_clustering,
            "clustering_rmsd_threshold": self.clustering_rmsd_threshold,
            "clustering_resample_points": self.clustering_resample_points,
            "metadata": _json_value(self.metadata), "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TransitionPathOptions":
        if payload.get("schema") != TRANSITION_PATH_OPTIONS_SCHEMA:
            raise TransitionPathSerializationError("Unsupported transition-path options schema.")
        return cls(
            include_failed_passages=bool(payload["include_failed_passages"]),
            concurrent_frame_window=int(payload["concurrent_frame_window"]),
            minimum_paths_for_resolved_ensemble=int(payload["minimum_paths_for_resolved_ensemble"]),
            enable_path_clustering=bool(payload["enable_path_clustering"]),
            minimum_paths_for_clustering=int(payload["minimum_paths_for_clustering"]),
            clustering_rmsd_threshold=float(payload["clustering_rmsd_threshold"]),
            clustering_resample_points=int(payload["clustering_resample_points"]),
            metadata=dict(payload.get("metadata", {})), signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class TransitionPathResourcePolicy:
    max_events: int = 100_000
    max_path_samples: int = 5_000_000
    max_ensembles: int = 100_000
    max_annotation_values: int = 50_000_000
    max_output_bytes: int = 2_000_000_000
    signature: str = ""

    def __post_init__(self) -> None:
        values = {name: _positive_int(getattr(self, name), name) for name in (
            "max_events", "max_path_samples", "max_ensembles", "max_annotation_values", "max_output_bytes")}
        payload = {"schema": TRANSITION_PATH_RESOURCES_SCHEMA, **values}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise TransitionPathInputError("Transition-path resource signature is inconsistent.")
        for name, value in (*values.items(), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": TRANSITION_PATH_RESOURCES_SCHEMA,
                "max_events": self.max_events, "max_path_samples": self.max_path_samples,
                "max_ensembles": self.max_ensembles, "max_annotation_values": self.max_annotation_values,
                "max_output_bytes": self.max_output_bytes, "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TransitionPathResourcePolicy":
        if payload.get("schema") != TRANSITION_PATH_RESOURCES_SCHEMA:
            raise TransitionPathSerializationError("Unsupported transition-path resource schema.")
        return cls(*(int(payload[name]) for name in (
            "max_events", "max_path_samples", "max_ensembles", "max_annotation_values", "max_output_bytes")),
            signature=str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class TransitionPathEvidenceTable:
    sample_catalog_signature: str
    sample_indices: IntArray
    ring_ids: Int32Array
    ring_sector_ids: Int32Array
    feature_names: tuple[str, ...]
    coordination_values: FloatArray
    harmonic_names: tuple[str, ...]
    harmonic_amplitudes: FloatArray
    harmonic_phases: FloatArray
    apertures: FloatArray
    puckering: FloatArray
    local_occupancy: FloatArray
    density_values: FloatArray | None = None
    pmf_values: FloatArray | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        source = _sha(self.sample_catalog_signature, "sample_catalog_signature")
        samples = _readonly(self.sample_indices, dtype=np.int64, ndim=1, name="sample_indices")
        if samples.size and (np.any(samples < 0) or np.any(np.diff(samples) <= 0)):
            raise TransitionPathInputError("Evidence sample_indices must be unique, sorted, and nonnegative.")
        n = samples.size
        rings = _readonly(self.ring_ids, dtype=np.int32, ndim=1, name="ring_ids", shape=(n,))
        sectors = _readonly(self.ring_sector_ids, dtype=np.int32, ndim=1, name="ring_sector_ids", shape=(n,))
        names = tuple(str(v) for v in self.feature_names)
        if len(set(names)) != len(names):
            raise TransitionPathInputError("feature_names must be unique.")
        coordination = _readonly(self.coordination_values, dtype=np.float64, ndim=2, name="coordination_values", shape=(n, len(names)))
        harmonic_names = tuple(str(v) for v in self.harmonic_names)
        if len(set(harmonic_names)) != len(harmonic_names):
            raise TransitionPathInputError("harmonic_names must be unique.")
        amplitudes = _readonly(self.harmonic_amplitudes, dtype=np.float64, ndim=2, name="harmonic_amplitudes", shape=(n, len(harmonic_names)))
        phases = _readonly(self.harmonic_phases, dtype=np.float64, ndim=2, name="harmonic_phases", shape=(n, len(harmonic_names)))
        apertures = _readonly(self.apertures, dtype=np.float64, ndim=1, name="apertures", shape=(n,))
        puckering = _readonly(self.puckering, dtype=np.float64, ndim=1, name="puckering", shape=(n,))
        occupancy = _readonly(self.local_occupancy, dtype=np.float64, ndim=1, name="local_occupancy", shape=(n,))
        density = None if self.density_values is None else _readonly(self.density_values, dtype=np.float64, ndim=1, name="density_values", shape=(n,))
        pmf = None if self.pmf_values is None else _readonly(self.pmf_values, dtype=np.float64, ndim=1, name="pmf_values", shape=(n,))
        metadata = _freeze(dict(self.metadata))
        payload = {
            "schema": PATH_EVIDENCE_TABLE_SCHEMA, "sample_catalog_signature": source,
            "sample_indices_digest": _array_digest(samples), "ring_ids_digest": _array_digest(rings),
            "ring_sector_ids_digest": _array_digest(sectors), "feature_names": list(names),
            "coordination_values_digest": _array_digest(coordination), "harmonic_names": list(harmonic_names),
            "harmonic_amplitudes_digest": _array_digest(amplitudes), "harmonic_phases_digest": _array_digest(phases),
            "apertures_digest": _array_digest(apertures), "puckering_digest": _array_digest(puckering),
            "local_occupancy_digest": _array_digest(occupancy),
            "density_values_digest": None if density is None else _array_digest(density),
            "pmf_values_digest": None if pmf is None else _array_digest(pmf), "metadata": _json_value(metadata),
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise TransitionPathInputError("Transition-path evidence signature is inconsistent.")
        for name, value in (
            ("sample_catalog_signature", source), ("sample_indices", samples), ("ring_ids", rings),
            ("ring_sector_ids", sectors), ("feature_names", names), ("coordination_values", coordination),
            ("harmonic_names", harmonic_names), ("harmonic_amplitudes", amplitudes), ("harmonic_phases", phases),
            ("apertures", apertures), ("puckering", puckering), ("local_occupancy", occupancy),
            ("density_values", density), ("pmf_values", pmf), ("metadata", metadata), ("signature", expected),
        ):
            object.__setattr__(self, name, value)

    @property
    def n_samples(self) -> int:
        return int(self.sample_indices.size)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PATH_EVIDENCE_TABLE_SCHEMA, "sample_catalog_signature": self.sample_catalog_signature,
            "sample_indices": self.sample_indices.tolist(), "ring_ids": self.ring_ids.tolist(),
            "ring_sector_ids": self.ring_sector_ids.tolist(), "feature_names": list(self.feature_names),
            "coordination_values": self.coordination_values.tolist(), "harmonic_names": list(self.harmonic_names),
            "harmonic_amplitudes": self.harmonic_amplitudes.tolist(), "harmonic_phases": self.harmonic_phases.tolist(),
            "apertures": self.apertures.tolist(), "puckering": self.puckering.tolist(),
            "local_occupancy": self.local_occupancy.tolist(),
            "density_values": None if self.density_values is None else self.density_values.tolist(),
            "pmf_values": None if self.pmf_values is None else self.pmf_values.tolist(),
            "metadata": _json_value(self.metadata), "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TransitionPathEvidenceTable":
        if payload.get("schema") != PATH_EVIDENCE_TABLE_SCHEMA:
            raise TransitionPathSerializationError("Unsupported transition-path evidence schema.")
        return cls(
            str(payload["sample_catalog_signature"]), np.asarray(payload["sample_indices"], dtype=np.int64),
            np.asarray(payload["ring_ids"], dtype=np.int32), np.asarray(payload["ring_sector_ids"], dtype=np.int32),
            tuple(payload["feature_names"]), np.asarray(payload["coordination_values"], dtype=np.float64),
            tuple(payload["harmonic_names"]), np.asarray(payload["harmonic_amplitudes"], dtype=np.float64),
            np.asarray(payload["harmonic_phases"], dtype=np.float64), np.asarray(payload["apertures"], dtype=np.float64),
            np.asarray(payload["puckering"], dtype=np.float64), np.asarray(payload["local_occupancy"], dtype=np.float64),
            None if payload.get("density_values") is None else np.asarray(payload["density_values"], dtype=np.float64),
            None if payload.get("pmf_values") is None else np.asarray(payload["pmf_values"], dtype=np.float64),
            dict(payload.get("metadata", {})), str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class RegistrationCompatibilityClass:
    member_sample_catalog_signatures: tuple[str, ...]
    member_registration_signatures: tuple[str, ...]
    registration_group_signature: str | None
    registration_policy_signatures: tuple[str, ...]
    represented_time_units: str
    state_correspondence: tuple[tuple[int, int, int], ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        catalogs = tuple(_sha(v, "member sample catalog signature") for v in self.member_sample_catalog_signatures)
        registrations = tuple(_sha(v, "member registration signature") for v in self.member_registration_signatures)
        policies = tuple(_sha(v, "member registration policy signature") for v in self.registration_policy_signatures)
        if not catalogs or len(catalogs) != len(registrations) or len(catalogs) != len(policies):
            raise TransitionPathInputError("Registration compatibility members must be nonempty and aligned.")
        if len(set(catalogs)) != len(catalogs):
            raise TransitionPathInputError("Compatibility member sample catalogs must be unique.")
        group = self.registration_group_signature
        if group is not None:
            group = _sha(group, "registration_group_signature")
        if len(catalogs) > 1 and group is None and len(set(registrations)) != 1:
            raise TransitionPathInputError(
                "Independent registrations require one shared registration-group signature."
            )
        units = str(self.represented_time_units)
        if not units:
            raise TransitionPathInputError("represented_time_units must be nonempty.")
        correspondence = tuple(sorted({(int(m), int(local), int(canonical)) for m, local, canonical in self.state_correspondence}))
        if any(m < 0 or m >= len(catalogs) or local < 0 or canonical < 0 for m, local, canonical in correspondence):
            raise TransitionPathInputError("State correspondence contains invalid identifiers.")
        if len({(m, local) for m, local, _ in correspondence}) != len(correspondence):
            raise TransitionPathInputError("A member-local state may map to only one canonical state.")
        metadata = _freeze(dict(self.metadata))
        payload = {
            "schema": REGISTRATION_COMPATIBILITY_SCHEMA,
            "member_sample_catalog_signatures": list(catalogs),
            "member_registration_signatures": list(registrations),
            "registration_group_signature": group,
            "registration_policy_signatures": list(policies),
            "represented_time_units": units,
            "state_correspondence": [list(v) for v in correspondence],
            "metadata": _json_value(metadata),
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise TransitionPathInputError("Registration-compatibility signature is inconsistent.")
        for name, value in (("member_sample_catalog_signatures", catalogs),
                            ("member_registration_signatures", registrations),
                            ("registration_group_signature", group),
                            ("registration_policy_signatures", policies),
                            ("represented_time_units", units),
                            ("state_correspondence", correspondence), ("metadata", metadata), ("signature", expected)):
            object.__setattr__(self, name, value)

    def canonical_state(self, member_index: int, local_state: int) -> int:
        for member, local, canonical in self.state_correspondence:
            if member == member_index and local == local_state:
                return canonical
        return local_state

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": REGISTRATION_COMPATIBILITY_SCHEMA,
            "member_sample_catalog_signatures": list(self.member_sample_catalog_signatures),
            "member_registration_signatures": list(self.member_registration_signatures),
            "registration_group_signature": self.registration_group_signature,
            "registration_policy_signatures": list(self.registration_policy_signatures),
            "represented_time_units": self.represented_time_units,
            "state_correspondence": [list(v) for v in self.state_correspondence],
            "metadata": _json_value(self.metadata), "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RegistrationCompatibilityClass":
        if payload.get("schema") != REGISTRATION_COMPATIBILITY_SCHEMA:
            raise TransitionPathSerializationError("Unsupported registration-compatibility schema.")
        return cls(tuple(payload["member_sample_catalog_signatures"]), tuple(payload["member_registration_signatures"]),
                   payload.get("registration_group_signature"), tuple(payload["registration_policy_signatures"]),
                   str(payload["represented_time_units"]), tuple(tuple(int(v) for v in row) for row in payload["state_correspondence"]),
                   dict(payload.get("metadata", {})), str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class TransitionOccupancyContext:
    state_ids: Int32Array
    before_counts: Int32Array
    during_min_counts: Int32Array
    during_max_counts: Int32Array
    after_counts: Int32Array
    signature: str = ""

    def __post_init__(self) -> None:
        states = _readonly(self.state_ids, dtype=np.int32, ndim=1, name="state_ids")
        if np.any(states < 0) or (states.size and np.any(np.diff(states) <= 0)):
            raise TransitionPathInputError("Occupancy state_ids must be sorted unique nonnegative values.")
        arrays = {}
        for name in ("before_counts", "during_min_counts", "during_max_counts", "after_counts"):
            arr = _readonly(getattr(self, name), dtype=np.int32, ndim=1, name=name, shape=states.shape)
            if np.any(arr < 0):
                raise TransitionPathInputError("Occupancy counts must be nonnegative.")
            arrays[name] = arr
        if np.any(arrays["during_min_counts"] > arrays["during_max_counts"]):
            raise TransitionPathInputError("During occupancy minima cannot exceed maxima.")
        payload = {"schema": OCCUPANCY_CONTEXT_SCHEMA, "state_ids_digest": _array_digest(states),
                   **{f"{name}_digest": _array_digest(arr) for name, arr in arrays.items()}}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise TransitionPathInputError("Occupancy-context signature is inconsistent.")
        object.__setattr__(self, "state_ids", states)
        for name, arr in arrays.items(): object.__setattr__(self, name, arr)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": OCCUPANCY_CONTEXT_SCHEMA, "state_ids": self.state_ids.tolist(),
                "before_counts": self.before_counts.tolist(), "during_min_counts": self.during_min_counts.tolist(),
                "during_max_counts": self.during_max_counts.tolist(), "after_counts": self.after_counts.tolist(),
                "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TransitionOccupancyContext":
        if payload.get("schema") != OCCUPANCY_CONTEXT_SCHEMA:
            raise TransitionPathSerializationError("Unsupported occupancy-context schema.")
        return cls(*(np.asarray(payload[name], dtype=np.int32) for name in
                     ("state_ids", "before_counts", "during_min_counts", "during_max_counts", "after_counts")),
                   signature=str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class ObservedTransitionEvent:
    event_id: int
    member_index: int
    source_passage_id: int
    sample_catalog_signature: str
    final_segmentation_signature: str
    atom_index: int
    segment_id: int
    source_state_id: int | None
    target_state_id: int | None
    candidate_target_state_ids: Int32Array
    first_hit_status: FirstHitResolutionStatus
    successful_connection: bool
    sample_indices: IntArray
    frame_indices: IntArray
    frame_ids: IntArray
    path_times: FloatArray | None
    represented_time_weights: FloatArray
    registered_positions: FloatArray
    registered_wrapped_fractional: FloatArray
    registered_image_shifts: IntArray
    periodic_translation: IntArray
    source_exit_bracket: IntArray
    target_entry_bracket: IntArray
    minimum_resolvable_duration: float
    transformed_forces: FloatArray | None
    force_available_mask: BoolArray
    evidence_status: PathEvidenceStatus
    ring_ids: Int32Array
    ring_sector_ids: Int32Array
    feature_names: tuple[str, ...]
    coordination_values: FloatArray
    harmonic_names: tuple[str, ...]
    harmonic_amplitudes: FloatArray
    harmonic_phases: FloatArray
    apertures: FloatArray
    puckering: FloatArray
    local_occupancy: FloatArray
    density_values: FloatArray | None
    pmf_values: FloatArray | None
    minimum_density: float | None
    maximum_pmf: float | None
    primary_structural_id: int | None
    structural_ambiguity: bool
    occupancy_context: TransitionOccupancyContext
    concurrent_event_ids: IntArray
    collective_status: CollectiveEventStatus
    boundary_induced: bool
    contains_unknown: bool
    contains_conflict: bool
    left_censored: bool
    right_censored: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        ids = {name: int(getattr(self, name)) for name in ("event_id", "member_index", "source_passage_id", "atom_index", "segment_id")}
        if min(ids.values()) < 0:
            raise TransitionPathInputError("Transition-event identifiers must be nonnegative.")
        sample_sig = _sha(self.sample_catalog_signature, "sample_catalog_signature")
        final_sig = _sha(self.final_segmentation_signature, "final_segmentation_signature")
        source = None if self.source_state_id is None else int(self.source_state_id)
        target = None if self.target_state_id is None else int(self.target_state_id)
        if source is not None and source < 0 or target is not None and target < 0:
            raise TransitionPathInputError("Transition state IDs must be nonnegative or None.")
        candidates = _readonly(self.candidate_target_state_ids, dtype=np.int32, ndim=1, name="candidate_target_state_ids")
        if np.any(candidates < 0) or (candidates.size and np.any(np.diff(candidates) <= 0)):
            raise TransitionPathInputError("Candidate target state IDs must be sorted unique and nonnegative.")
        if target is not None and candidates.size and target not in candidates:
            raise TransitionPathInputError("A resolved target must belong to the retained candidate set.")
        status = FirstHitResolutionStatus(self.first_hit_status)
        samples = _readonly(self.sample_indices, dtype=np.int64, ndim=1, name="sample_indices")
        if samples.size < 1 or np.any(samples < 0):
            raise TransitionPathInputError("An observed path requires nonnegative samples.")
        n = samples.size
        frames = _readonly(self.frame_indices, dtype=np.int64, ndim=1, name="frame_indices", shape=(n,))
        frame_ids = _readonly(self.frame_ids, dtype=np.int64, ndim=1, name="frame_ids", shape=(n,))
        times = None if self.path_times is None else _readonly(self.path_times, dtype=np.float64, ndim=1, name="path_times", shape=(n,))
        weights = _readonly(self.represented_time_weights, dtype=np.float64, ndim=1, name="represented_time_weights", shape=(n,))
        positions = _readonly(self.registered_positions, dtype=np.float64, ndim=2, name="registered_positions", shape=(n, 3))
        wrapped = _readonly(self.registered_wrapped_fractional, dtype=np.float64, ndim=2, name="registered_wrapped_fractional", shape=(n, 3))
        shifts = _readonly(self.registered_image_shifts, dtype=np.int64, ndim=2, name="registered_image_shifts", shape=(n, 3))
        translation = _readonly(self.periodic_translation, dtype=np.int64, ndim=1, name="periodic_translation", shape=(3,))
        if not np.array_equal(translation, shifts[-1] - shifts[0]):
            raise TransitionPathInputError("Periodic translation must equal retained endpoint image-shift difference.")
        source_bracket = _readonly(self.source_exit_bracket, dtype=np.int64, ndim=1, name="source_exit_bracket")
        target_bracket = _readonly(self.target_entry_bracket, dtype=np.int64, ndim=1, name="target_entry_bracket")
        if source_bracket.size not in (0, 2) or target_bracket.size not in (0, 2):
            raise TransitionPathInputError("Transition brackets must contain zero or two compact sample indices.")
        min_duration = _nonnegative(self.minimum_resolvable_duration, "minimum_resolvable_duration")
        forces = None if self.transformed_forces is None else _readonly(self.transformed_forces, dtype=np.float64, ndim=2, name="transformed_forces", shape=(n, 3))
        force_mask = _readonly(self.force_available_mask, dtype=np.bool_, ndim=1, name="force_available_mask", shape=(n,))
        if forces is None and np.any(force_mask):
            raise TransitionPathInputError("Force availability cannot be true without transformed forces.")
        evidence_status = PathEvidenceStatus(self.evidence_status)
        rings = _readonly(self.ring_ids, dtype=np.int32, ndim=1, name="ring_ids", shape=(n,))
        sectors = _readonly(self.ring_sector_ids, dtype=np.int32, ndim=1, name="ring_sector_ids", shape=(n,))
        feature_names = tuple(str(v) for v in self.feature_names)
        coordination = _readonly(self.coordination_values, dtype=np.float64, ndim=2, name="coordination_values", shape=(n, len(feature_names)))
        harmonic_names = tuple(str(v) for v in self.harmonic_names)
        amplitudes = _readonly(self.harmonic_amplitudes, dtype=np.float64, ndim=2, name="harmonic_amplitudes", shape=(n, len(harmonic_names)))
        phases = _readonly(self.harmonic_phases, dtype=np.float64, ndim=2, name="harmonic_phases", shape=(n, len(harmonic_names)))
        apertures = _readonly(self.apertures, dtype=np.float64, ndim=1, name="apertures", shape=(n,))
        puckering = _readonly(self.puckering, dtype=np.float64, ndim=1, name="puckering", shape=(n,))
        occupancy = _readonly(self.local_occupancy, dtype=np.float64, ndim=1, name="local_occupancy", shape=(n,))
        density = None if self.density_values is None else _readonly(self.density_values, dtype=np.float64, ndim=1, name="density_values", shape=(n,))
        pmf = None if self.pmf_values is None else _readonly(self.pmf_values, dtype=np.float64, ndim=1, name="pmf_values", shape=(n,))
        minimum_density = None if self.minimum_density is None else float(self.minimum_density)
        maximum_pmf = None if self.maximum_pmf is None else float(self.maximum_pmf)
        if minimum_density is not None and (not np.isfinite(minimum_density) or density is None or abs(minimum_density - float(np.min(density))) > 1e-12):
            raise TransitionPathInputError("minimum_density is inconsistent with retained density values.")
        if maximum_pmf is not None and (not np.isfinite(maximum_pmf) or pmf is None or abs(maximum_pmf - float(np.max(pmf))) > 1e-12):
            raise TransitionPathInputError("maximum_pmf is inconsistent with retained PMF values.")
        structural_id = None if self.primary_structural_id is None else int(self.primary_structural_id)
        if structural_id is not None and structural_id < 0:
            raise TransitionPathInputError("primary_structural_id must be nonnegative or None.")
        concurrent = _readonly(self.concurrent_event_ids, dtype=np.int64, ndim=1, name="concurrent_event_ids")
        if np.any(concurrent < 0) or (concurrent.size and np.any(np.diff(concurrent) <= 0)) or ids["event_id"] in concurrent:
            raise TransitionPathInputError("Concurrent event IDs must be sorted unique and exclude self.")
        collective = CollectiveEventStatus(self.collective_status)
        successful = bool(self.successful_connection)
        if successful and (source is None or target is None or source == target or status not in (
            FirstHitResolutionStatus.RESOLVED_FIRST_HIT, FirstHitResolutionStatus.TEMPORALLY_BRACKETED_FIRST_HIT)):
            raise TransitionPathInputError("Successful connections require a resolved change of state.")
        metadata = _freeze(dict(self.metadata))
        payload = {
            "schema": OBSERVED_TRANSITION_EVENT_SCHEMA, **ids,
            "sample_catalog_signature": sample_sig, "final_segmentation_signature": final_sig,
            "source_state_id": source, "target_state_id": target,
            "candidate_target_state_ids_digest": _array_digest(candidates), "first_hit_status": status.value,
            "successful_connection": successful, "sample_indices_digest": _array_digest(samples),
            "frame_indices_digest": _array_digest(frames), "frame_ids_digest": _array_digest(frame_ids),
            "path_times_digest": None if times is None else _array_digest(times),
            "represented_time_weights_digest": _array_digest(weights), "registered_positions_digest": _array_digest(positions),
            "registered_wrapped_fractional_digest": _array_digest(wrapped), "registered_image_shifts_digest": _array_digest(shifts),
            "periodic_translation": translation.tolist(), "source_exit_bracket": source_bracket.tolist(),
            "target_entry_bracket": target_bracket.tolist(), "minimum_resolvable_duration": min_duration,
            "transformed_forces_digest": None if forces is None else _array_digest(forces),
            "force_available_mask_digest": _array_digest(force_mask), "evidence_status": evidence_status.value,
            "ring_ids_digest": _array_digest(rings), "ring_sector_ids_digest": _array_digest(sectors),
            "feature_names": list(feature_names), "coordination_values_digest": _array_digest(coordination),
            "harmonic_names": list(harmonic_names), "harmonic_amplitudes_digest": _array_digest(amplitudes),
            "harmonic_phases_digest": _array_digest(phases), "apertures_digest": _array_digest(apertures),
            "puckering_digest": _array_digest(puckering), "local_occupancy_digest": _array_digest(occupancy),
            "density_values_digest": None if density is None else _array_digest(density),
            "pmf_values_digest": None if pmf is None else _array_digest(pmf),
            "minimum_density": minimum_density, "maximum_pmf": maximum_pmf,
            "primary_structural_id": structural_id, "structural_ambiguity": bool(self.structural_ambiguity),
            "occupancy_context_signature": self.occupancy_context.signature,
            "concurrent_event_ids_digest": _array_digest(concurrent), "collective_status": collective.value,
            "boundary_induced": bool(self.boundary_induced), "contains_unknown": bool(self.contains_unknown),
            "contains_conflict": bool(self.contains_conflict), "left_censored": bool(self.left_censored),
            "right_censored": bool(self.right_censored), "metadata": _json_value(metadata),
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise TransitionPathInputError("Observed-transition signature is inconsistent.")
        values = {
            **ids, "sample_catalog_signature": sample_sig, "final_segmentation_signature": final_sig,
            "source_state_id": source, "target_state_id": target, "candidate_target_state_ids": candidates,
            "first_hit_status": status, "successful_connection": successful, "sample_indices": samples, "frame_indices": frames,
            "frame_ids": frame_ids, "path_times": times, "represented_time_weights": weights,
            "registered_positions": positions, "registered_wrapped_fractional": wrapped,
            "registered_image_shifts": shifts, "periodic_translation": translation,
            "source_exit_bracket": source_bracket, "target_entry_bracket": target_bracket,
            "minimum_resolvable_duration": min_duration, "transformed_forces": forces,
            "force_available_mask": force_mask, "evidence_status": evidence_status, "ring_ids": rings,
            "ring_sector_ids": sectors, "feature_names": feature_names, "coordination_values": coordination,
            "harmonic_names": harmonic_names, "harmonic_amplitudes": amplitudes, "harmonic_phases": phases,
            "apertures": apertures, "puckering": puckering, "local_occupancy": occupancy,
            "density_values": density, "pmf_values": pmf, "minimum_density": minimum_density,
            "maximum_pmf": maximum_pmf, "primary_structural_id": structural_id,
            "structural_ambiguity": bool(self.structural_ambiguity), "concurrent_event_ids": concurrent,
            "collective_status": collective, "boundary_induced": bool(self.boundary_induced),
            "contains_unknown": bool(self.contains_unknown), "contains_conflict": bool(self.contains_conflict),
            "left_censored": bool(self.left_censored), "right_censored": bool(self.right_censored),
            "metadata": metadata, "signature": expected,
        }
        for name, value in values.items(): object.__setattr__(self, name, value)

    @property
    def represented_time(self) -> float:
        return float(np.sum(self.represented_time_weights))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": OBSERVED_TRANSITION_EVENT_SCHEMA,
            "event_id": self.event_id, "member_index": self.member_index, "source_passage_id": self.source_passage_id,
            "sample_catalog_signature": self.sample_catalog_signature, "final_segmentation_signature": self.final_segmentation_signature,
            "atom_index": self.atom_index, "segment_id": self.segment_id, "source_state_id": self.source_state_id,
            "target_state_id": self.target_state_id, "candidate_target_state_ids": self.candidate_target_state_ids.tolist(),
            "first_hit_status": self.first_hit_status.value,
            "successful_connection": self.successful_connection, "sample_indices": self.sample_indices.tolist(),
            "frame_indices": self.frame_indices.tolist(), "frame_ids": self.frame_ids.tolist(),
            "path_times": None if self.path_times is None else self.path_times.tolist(),
            "represented_time_weights": self.represented_time_weights.tolist(),
            "registered_positions": self.registered_positions.tolist(),
            "registered_wrapped_fractional": self.registered_wrapped_fractional.tolist(),
            "registered_image_shifts": self.registered_image_shifts.tolist(),
            "periodic_translation": self.periodic_translation.tolist(),
            "source_exit_bracket": self.source_exit_bracket.tolist(), "target_entry_bracket": self.target_entry_bracket.tolist(),
            "minimum_resolvable_duration": self.minimum_resolvable_duration,
            "transformed_forces": None if self.transformed_forces is None else self.transformed_forces.tolist(),
            "force_available_mask": self.force_available_mask.tolist(), "evidence_status": self.evidence_status.value,
            "ring_ids": self.ring_ids.tolist(), "ring_sector_ids": self.ring_sector_ids.tolist(),
            "feature_names": list(self.feature_names), "coordination_values": self.coordination_values.tolist(),
            "harmonic_names": list(self.harmonic_names), "harmonic_amplitudes": self.harmonic_amplitudes.tolist(),
            "harmonic_phases": self.harmonic_phases.tolist(), "apertures": self.apertures.tolist(),
            "puckering": self.puckering.tolist(), "local_occupancy": self.local_occupancy.tolist(),
            "density_values": None if self.density_values is None else self.density_values.tolist(),
            "pmf_values": None if self.pmf_values is None else self.pmf_values.tolist(),
            "minimum_density": self.minimum_density, "maximum_pmf": self.maximum_pmf,
            "primary_structural_id": self.primary_structural_id, "structural_ambiguity": self.structural_ambiguity,
            "occupancy_context": self.occupancy_context.to_dict(), "concurrent_event_ids": self.concurrent_event_ids.tolist(),
            "collective_status": self.collective_status.value, "boundary_induced": self.boundary_induced,
            "contains_unknown": self.contains_unknown, "contains_conflict": self.contains_conflict,
            "left_censored": self.left_censored, "right_censored": self.right_censored,
            "metadata": _json_value(self.metadata), "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ObservedTransitionEvent":
        if payload.get("schema") != OBSERVED_TRANSITION_EVENT_SCHEMA:
            raise TransitionPathSerializationError("Unsupported observed-transition schema.")
        return cls(
            int(payload["event_id"]), int(payload["member_index"]), int(payload["source_passage_id"]),
            str(payload["sample_catalog_signature"]), str(payload["final_segmentation_signature"]),
            int(payload["atom_index"]), int(payload["segment_id"]), payload.get("source_state_id"), payload.get("target_state_id"),
            np.asarray(payload.get("candidate_target_state_ids", []), dtype=np.int32),
            FirstHitResolutionStatus(payload["first_hit_status"]), bool(payload["successful_connection"]),
            np.asarray(payload["sample_indices"], dtype=np.int64), np.asarray(payload["frame_indices"], dtype=np.int64),
            np.asarray(payload["frame_ids"], dtype=np.int64), None if payload.get("path_times") is None else np.asarray(payload["path_times"], dtype=np.float64),
            np.asarray(payload["represented_time_weights"], dtype=np.float64), np.asarray(payload["registered_positions"], dtype=np.float64),
            np.asarray(payload["registered_wrapped_fractional"], dtype=np.float64), np.asarray(payload["registered_image_shifts"], dtype=np.int64),
            np.asarray(payload["periodic_translation"], dtype=np.int64), np.asarray(payload["source_exit_bracket"], dtype=np.int64),
            np.asarray(payload["target_entry_bracket"], dtype=np.int64), float(payload["minimum_resolvable_duration"]),
            None if payload.get("transformed_forces") is None else np.asarray(payload["transformed_forces"], dtype=np.float64),
            np.asarray(payload["force_available_mask"], dtype=np.bool_), PathEvidenceStatus(payload["evidence_status"]),
            np.asarray(payload["ring_ids"], dtype=np.int32), np.asarray(payload["ring_sector_ids"], dtype=np.int32),
            tuple(payload["feature_names"]), np.asarray(payload["coordination_values"], dtype=np.float64),
            tuple(payload["harmonic_names"]), np.asarray(payload["harmonic_amplitudes"], dtype=np.float64),
            np.asarray(payload["harmonic_phases"], dtype=np.float64), np.asarray(payload["apertures"], dtype=np.float64),
            np.asarray(payload["puckering"], dtype=np.float64), np.asarray(payload["local_occupancy"], dtype=np.float64),
            None if payload.get("density_values") is None else np.asarray(payload["density_values"], dtype=np.float64),
            None if payload.get("pmf_values") is None else np.asarray(payload["pmf_values"], dtype=np.float64),
            payload.get("minimum_density"), payload.get("maximum_pmf"), payload.get("primary_structural_id"),
            bool(payload["structural_ambiguity"]), TransitionOccupancyContext.from_dict(payload["occupancy_context"]),
            np.asarray(payload["concurrent_event_ids"], dtype=np.int64), CollectiveEventStatus(payload["collective_status"]),
            bool(payload["boundary_induced"]), bool(payload["contains_unknown"]), bool(payload["contains_conflict"]),
            bool(payload["left_censored"]), bool(payload["right_censored"]), dict(payload.get("metadata", {})),
            str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class TransitionPathEnsemble:
    ensemble_id: int
    source_state_id: int
    target_state_id: int
    periodic_translation: IntArray
    primary_structural_id: int | None
    registration_compatibility_signature: str
    event_ids: IntArray
    status: PathEnsembleStatus
    clustering_status: PathClusteringStatus
    cluster_labels: Int32Array
    duration_mean: float
    duration_std: float
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        ensemble = int(self.ensemble_id); source = int(self.source_state_id); target = int(self.target_state_id)
        if min(ensemble, source, target) < 0 or source == target:
            raise TransitionPathInputError("Path-ensemble identifiers require a state change.")
        translation = _readonly(self.periodic_translation, dtype=np.int64, ndim=1, name="periodic_translation", shape=(3,))
        structural = None if self.primary_structural_id is None else int(self.primary_structural_id)
        if structural is not None and structural < 0:
            raise TransitionPathInputError("primary_structural_id must be nonnegative or None.")
        compatibility = _sha(self.registration_compatibility_signature, "registration_compatibility_signature")
        events = _readonly(self.event_ids, dtype=np.int64, ndim=1, name="event_ids")
        if events.size == 0 or np.any(events < 0) or np.any(np.diff(events) <= 0):
            raise TransitionPathInputError("Path ensembles require sorted unique event IDs.")
        status = PathEnsembleStatus(self.status); clustering = PathClusteringStatus(self.clustering_status)
        labels = _readonly(self.cluster_labels, dtype=np.int32, ndim=1, name="cluster_labels", shape=events.shape)
        if clustering is not PathClusteringStatus.RESOLVED and np.any(labels >= 0):
            raise TransitionPathInputError("Cluster labels require resolved clustering.")
        mean = _nonnegative(self.duration_mean, "duration_mean"); std = _nonnegative(self.duration_std, "duration_std")
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": TRANSITION_PATH_ENSEMBLE_SCHEMA, "ensemble_id": ensemble,
                   "source_state_id": source, "target_state_id": target, "periodic_translation": translation.tolist(),
                   "primary_structural_id": structural, "registration_compatibility_signature": compatibility,
                   "event_ids_digest": _array_digest(events), "status": status.value,
                   "clustering_status": clustering.value, "cluster_labels_digest": _array_digest(labels),
                   "duration_mean": mean, "duration_std": std, "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise TransitionPathInputError("Transition-path ensemble signature is inconsistent.")
        for name, value in (("ensemble_id", ensemble), ("source_state_id", source), ("target_state_id", target),
                            ("periodic_translation", translation), ("primary_structural_id", structural),
                            ("registration_compatibility_signature", compatibility), ("event_ids", events),
                            ("status", status), ("clustering_status", clustering), ("cluster_labels", labels),
                            ("duration_mean", mean), ("duration_std", std), ("metadata", metadata), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": TRANSITION_PATH_ENSEMBLE_SCHEMA, "ensemble_id": self.ensemble_id,
                "source_state_id": self.source_state_id, "target_state_id": self.target_state_id,
                "periodic_translation": self.periodic_translation.tolist(), "primary_structural_id": self.primary_structural_id,
                "registration_compatibility_signature": self.registration_compatibility_signature,
                "event_ids": self.event_ids.tolist(), "status": self.status.value,
                "clustering_status": self.clustering_status.value, "cluster_labels": self.cluster_labels.tolist(),
                "duration_mean": self.duration_mean, "duration_std": self.duration_std,
                "metadata": _json_value(self.metadata), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TransitionPathEnsemble":
        if payload.get("schema") != TRANSITION_PATH_ENSEMBLE_SCHEMA:
            raise TransitionPathSerializationError("Unsupported path-ensemble schema.")
        return cls(int(payload["ensemble_id"]), int(payload["source_state_id"]), int(payload["target_state_id"]),
                   np.asarray(payload["periodic_translation"], dtype=np.int64), payload.get("primary_structural_id"),
                   str(payload["registration_compatibility_signature"]), np.asarray(payload["event_ids"], dtype=np.int64),
                   PathEnsembleStatus(payload["status"]), PathClusteringStatus(payload["clustering_status"]),
                   np.asarray(payload["cluster_labels"], dtype=np.int32), float(payload["duration_mean"]),
                   float(payload["duration_std"]), dict(payload.get("metadata", {})), str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class ObservedTransitionPathCatalog:
    options: TransitionPathOptions
    resources: TransitionPathResourcePolicy
    registration_compatibility: RegistrationCompatibilityClass
    member_sample_catalog_signatures: tuple[str, ...]
    member_final_segmentation_signatures: tuple[str, ...]
    events: tuple[ObservedTransitionEvent, ...]
    ensembles: tuple[TransitionPathEnsemble, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        sample_sigs = tuple(_sha(v, "member sample catalog signature") for v in self.member_sample_catalog_signatures)
        final_sigs = tuple(_sha(v, "member final segmentation signature") for v in self.member_final_segmentation_signatures)
        if len(sample_sigs) != len(final_sigs) or sample_sigs != self.registration_compatibility.member_sample_catalog_signatures:
            raise TransitionPathInputError("Path-catalog member sources disagree with compatibility class.")
        events = tuple(self.events); ensembles = tuple(self.ensembles)
        if tuple(v.event_id for v in events) != tuple(range(len(events))):
            raise TransitionPathInputError("Observed transition events must use dense ordered IDs.")
        if tuple(v.ensemble_id for v in ensembles) != tuple(range(len(ensembles))):
            raise TransitionPathInputError("Path ensembles must use dense ordered IDs.")
        if any(v.sample_catalog_signature not in sample_sigs or v.final_segmentation_signature not in final_sigs for v in events):
            raise TransitionPathInputError("An event is not bound to a catalog member.")
        all_event_ids = {v.event_id for v in events}
        if any(not set(v.event_ids).issubset(all_event_ids) for v in ensembles):
            raise TransitionPathInputError("An ensemble references an unknown event.")
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": TRANSITION_PATH_CATALOG_SCHEMA, "options_signature": self.options.signature,
                   "resources_signature": self.resources.signature,
                   "registration_compatibility_signature": self.registration_compatibility.signature,
                   "member_sample_catalog_signatures": list(sample_sigs),
                   "member_final_segmentation_signatures": list(final_sigs),
                   "event_signatures": [v.signature for v in events], "ensemble_signatures": [v.signature for v in ensembles],
                   "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise TransitionPathInputError("Transition-path catalog signature is inconsistent.")
        for name, value in (("member_sample_catalog_signatures", sample_sigs),
                            ("member_final_segmentation_signatures", final_sigs), ("events", events),
                            ("ensembles", ensembles), ("metadata", metadata), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": TRANSITION_PATH_CATALOG_SCHEMA, "options": self.options.to_dict(),
                "resources": self.resources.to_dict(), "registration_compatibility": self.registration_compatibility.to_dict(),
                "member_sample_catalog_signatures": list(self.member_sample_catalog_signatures),
                "member_final_segmentation_signatures": list(self.member_final_segmentation_signatures),
                "events": [v.to_dict() for v in self.events], "ensembles": [v.to_dict() for v in self.ensembles],
                "metadata": _json_value(self.metadata), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ObservedTransitionPathCatalog":
        if payload.get("schema") != TRANSITION_PATH_CATALOG_SCHEMA:
            raise TransitionPathSerializationError("Unsupported transition-path catalog schema.")
        return cls(TransitionPathOptions.from_dict(payload["options"]), TransitionPathResourcePolicy.from_dict(payload["resources"]),
                   RegistrationCompatibilityClass.from_dict(payload["registration_compatibility"]),
                   tuple(payload["member_sample_catalog_signatures"]), tuple(payload["member_final_segmentation_signatures"]),
                   tuple(ObservedTransitionEvent.from_dict(v) for v in payload["events"]),
                   tuple(TransitionPathEnsemble.from_dict(v) for v in payload["ensembles"]),
                   dict(payload.get("metadata", {})), str(payload.get("signature", "")))


def prepare_registration_compatibility_class(
    sample_catalogs: Sequence[FrameworkAlignedIonSampleCatalog],
    *, state_correspondence: Sequence[tuple[int, int, int]] = (),
    metadata: Mapping[str, Any] | None = None,
) -> RegistrationCompatibilityClass:
    catalogs = tuple(sample_catalogs)
    if not catalogs:
        raise TransitionPathInputError("At least one sample catalog is required.")
    units = {v.temporal_weighting.weight_units for v in catalogs}
    if len(units) != 1:
        raise TransitionPathInputError("Compatible path catalogs require one represented-time unit convention.")
    groups = {v.registration_group_signature for v in catalogs}
    group = next(iter(groups)) if len(groups) == 1 else None
    if group is not None:
        member_indices = tuple(v.registration_group_member_index for v in catalogs)
        if any(v is None for v in member_indices) or len(set(member_indices)) != len(member_indices):
            raise TransitionPathInputError(
                "A shared registration group requires distinct declared member indices."
            )
    if len(catalogs) > 1 and (group is None or None in groups):
        if len({v.registration_signature for v in catalogs}) != 1:
            raise TransitionPathInputError(
                "Independent path catalogs require a shared registration group or identical registration."
            )
        group = None
    return RegistrationCompatibilityClass(
        tuple(v.signature for v in catalogs), tuple(v.registration_signature for v in catalogs), group,
        tuple(v.registration_policy_signature for v in catalogs), next(iter(units)),
        tuple(tuple(int(x) for x in row) for row in state_correspondence),
        {} if metadata is None else metadata,
    )


def _frame_time_map(catalog: FrameworkAlignedIonSampleCatalog) -> dict[int, float] | None:
    source_times = catalog.temporal_weighting.source_times
    if source_times is None:
        return None
    return {int(frame): float(time) for frame, time in zip(catalog.temporal_weighting.frame_indices, source_times, strict=True)}


def _minimum_resolvable_duration(catalog: FrameworkAlignedIonSampleCatalog, frames: np.ndarray) -> float:
    mapping = _frame_time_map(catalog)
    if mapping is None:
        positive = catalog.represented_time_weights[catalog.represented_time_weights > 0.0]
        return 0.0 if positive.size == 0 else float(np.min(positive))
    values = np.asarray([mapping[int(v)] for v in frames], dtype=np.float64)
    diffs = np.diff(values)
    positive = diffs[diffs > 0.0]
    if positive.size:
        return float(np.min(positive))
    all_values = np.asarray(list(mapping.values()), dtype=np.float64)
    positive = np.diff(np.sort(np.unique(all_values)))
    return 0.0 if positive.size == 0 else float(np.min(positive))


def _residence_brackets(final: FinalHystereticSegmentationCatalog, passage: FinalPassageInterval) -> tuple[int | None, int | None]:
    source_candidates = [r for r in final.residences if r.atom_index == passage.atom_index and r.segment_id == passage.segment_id
                         and passage.source_state_id is not None and r.state_id == passage.source_state_id
                         and (passage.sample_indices.size == 0 or r.sample_indices[-1] < passage.sample_indices[0])]
    target_candidates = [r for r in final.residences if r.atom_index == passage.atom_index and r.segment_id == passage.segment_id
                         and passage.target_state_id is not None and r.state_id == passage.target_state_id
                         and (passage.sample_indices.size == 0 or r.sample_indices[0] > passage.sample_indices[-1])]
    source_sample = None if not source_candidates else int(max(source_candidates, key=lambda r: int(r.sample_indices[-1])).sample_indices[-1])
    target_sample = None if not target_candidates else int(min(target_candidates, key=lambda r: int(r.sample_indices[0])).sample_indices[0])
    return source_sample, target_sample


def _ordered_path_samples(final: FinalHystereticSegmentationCatalog, passage: FinalPassageInterval) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    source, target = _residence_brackets(final, passage)
    body = [int(v) for v in passage.sample_indices]
    values = ([] if source is None else [source]) + body + ([] if target is None else [target])
    # Preserve traversal order while removing duplicate bracket endpoints.
    seen: set[int] = set(); path = []
    for value in values:
        if value not in seen:
            seen.add(value); path.append(value)
    source_bracket = np.asarray([], dtype=np.int64)
    target_bracket = np.asarray([], dtype=np.int64)
    if source is not None and body:
        source_bracket = np.asarray([source, body[0]], dtype=np.int64)
    if target is not None:
        previous = body[-1] if body else source
        if previous is not None:
            target_bracket = np.asarray([previous, target], dtype=np.int64)
    return np.asarray(path, dtype=np.int64), source_bracket, target_bracket


def _first_hit_status(passage: FinalPassageInterval, catalog: FrameworkAlignedIonSampleCatalog,
                      target_bracket: np.ndarray, candidate_targets: np.ndarray) -> tuple[FirstHitResolutionStatus, bool]:
    outcome = passage.outcome
    if candidate_targets.size > 1:
        return FirstHitResolutionStatus.MULTIPLE_TARGETS_BETWEEN_FRAMES, False
    if outcome is FinalPassageOutcome.RESOLVED_TRANSITION and passage.counted_transition:
        if target_bracket.size == 2:
            a, b = map(int, target_bracket)
            frame_gap = int(catalog.frame_indices[b]) - int(catalog.frame_indices[a])
            if frame_gap > 1:
                return FirstHitResolutionStatus.TEMPORALLY_BRACKETED_FIRST_HIT, True
        return FirstHitResolutionStatus.RESOLVED_FIRST_HIT, True
    if outcome is FinalPassageOutcome.UNRESOLVED_GAP:
        return FirstHitResolutionStatus.GAP_INTERRUPTED, False
    if outcome is FinalPassageOutcome.ASSIGNMENT_CONFLICT:
        return FirstHitResolutionStatus.TARGET_AMBIGUOUS, False
    if outcome in (FinalPassageOutcome.RETURN_EXCURSION, FinalPassageOutcome.RETAINED_EXCURSION):
        return FirstHitResolutionStatus.FAILED_EXCURSION, False
    if outcome is FinalPassageOutcome.RECROSSING:
        return FirstHitResolutionStatus.RECROSSING, False
    if outcome is FinalPassageOutcome.RIGHT_CENSORED_EXIT:
        return FirstHitResolutionStatus.RIGHT_CENSORED, False
    if outcome is FinalPassageOutcome.BOUNDARY_INDUCED:
        return FirstHitResolutionStatus.TARGET_AMBIGUOUS, False
    return FirstHitResolutionStatus.TARGET_AMBIGUOUS, False


def _evidence_slice(table: TransitionPathEvidenceTable | None, samples: np.ndarray) -> dict[str, Any]:
    n = samples.size
    if table is None:
        return {"status": PathEvidenceStatus.UNAVAILABLE, "ring_ids": np.full(n, -1, np.int32),
                "ring_sector_ids": np.full(n, -1, np.int32), "feature_names": (),
                "coordination_values": np.empty((n, 0), np.float64), "harmonic_names": (),
                "harmonic_amplitudes": np.empty((n, 0), np.float64), "harmonic_phases": np.empty((n, 0), np.float64),
                "apertures": np.full(n, 0.0), "puckering": np.full(n, 0.0),
                "local_occupancy": np.full(n, 0.0), "density_values": None, "pmf_values": None}
    lookup = {int(sample): index for index, sample in enumerate(table.sample_indices)}
    present = np.asarray([int(sample) in lookup for sample in samples], dtype=np.bool_)
    rows = np.asarray([lookup.get(int(sample), -1) for sample in samples], dtype=np.int64)
    def take1(values: np.ndarray, fill: float | int) -> np.ndarray:
        out = np.full(n, fill, dtype=values.dtype); out[present] = values[rows[present]]; return out
    def take2(values: np.ndarray) -> np.ndarray:
        out = np.zeros((n, values.shape[1]), dtype=values.dtype); out[present] = values[rows[present]]; return out
    status = PathEvidenceStatus.COMPLETE if np.all(present) else (PathEvidenceStatus.PARTIAL if np.any(present) else PathEvidenceStatus.UNAVAILABLE)
    return {"status": status, "ring_ids": take1(table.ring_ids, -1), "ring_sector_ids": take1(table.ring_sector_ids, -1),
            "feature_names": table.feature_names, "coordination_values": take2(table.coordination_values),
            "harmonic_names": table.harmonic_names, "harmonic_amplitudes": take2(table.harmonic_amplitudes),
            "harmonic_phases": take2(table.harmonic_phases), "apertures": take1(table.apertures, 0.0),
            "puckering": take1(table.puckering, 0.0), "local_occupancy": take1(table.local_occupancy, 0.0),
            "density_values": None if table.density_values is None else take1(table.density_values, 0.0),
            "pmf_values": None if table.pmf_values is None else take1(table.pmf_values, 0.0)}


def _primary_structural_id(ring_ids: np.ndarray) -> tuple[int | None, bool]:
    valid = ring_ids[ring_ids >= 0]
    if valid.size == 0:
        return None, False
    values, counts = np.unique(valid, return_counts=True)
    maximum = np.max(counts); winners = values[counts == maximum]
    return int(winners[0]), bool(winners.size > 1 or values.size > 1)


def _occupancy_context(sample_catalog: FrameworkAlignedIonSampleCatalog, final: FinalHystereticSegmentationCatalog,
                       frames: np.ndarray) -> TransitionOccupancyContext:
    states = np.asarray(sorted({int(v) for v in final.assigned_state_ids if v >= 0}), dtype=np.int32)
    if states.size == 0:
        empty = np.zeros(0, dtype=np.int32)
        return TransitionOccupancyContext(empty, empty, empty, empty, empty)
    unique_frames = np.unique(frames)
    all_frames = np.unique(sample_catalog.frame_indices)
    first, last = int(unique_frames[0]), int(unique_frames[-1])
    before_candidates = all_frames[all_frames < first]; after_candidates = all_frames[all_frames > last]
    before_frame = None if before_candidates.size == 0 else int(before_candidates[-1])
    after_frame = None if after_candidates.size == 0 else int(after_candidates[0])
    def counts(frame: int | None) -> np.ndarray:
        if frame is None: return np.zeros(states.size, dtype=np.int32)
        ids = final.assigned_state_ids[sample_catalog.frame_indices == frame]
        return np.asarray([np.count_nonzero(ids == state) for state in states], dtype=np.int32)
    during = np.vstack([counts(int(frame)) for frame in unique_frames])
    return TransitionOccupancyContext(states, counts(before_frame), np.min(during, axis=0), np.max(during, axis=0), counts(after_frame))


def _build_event(member_index: int, event_id: int, sample_catalog: FrameworkAlignedIonSampleCatalog,
                 final: FinalHystereticSegmentationCatalog, passage: FinalPassageInterval,
                 evidence: TransitionPathEvidenceTable | None, candidate_targets: Sequence[int] = ()) -> ObservedTransitionEvent:
    samples, source_bracket, target_bracket = _ordered_path_samples(final, passage)
    if samples.size == 0:
        # A zero-body censored exit still needs one retained boundary sample.
        source, target = _residence_brackets(final, passage)
        fallback = source if source is not None else target
        if fallback is None:
            raise TransitionPathInputError(f"Passage {passage.passage_id} has no reconstructible path sample.")
        samples = np.asarray([fallback], dtype=np.int64)
    if np.any(samples >= sample_catalog.n_samples):
        raise TransitionPathInputError("A final passage references samples outside the source catalog.")
    candidate_array = np.asarray(sorted({int(v) for v in candidate_targets}), dtype=np.int32)
    if passage.target_state_id is not None and candidate_array.size == 0:
        candidate_array = np.asarray([int(passage.target_state_id)], dtype=np.int32)
    status, successful = _first_hit_status(passage, sample_catalog, target_bracket, candidate_array)
    frame_indices = sample_catalog.frame_indices[samples]
    time_map = _frame_time_map(sample_catalog)
    path_times = None if time_map is None else np.asarray([time_map[int(v)] for v in frame_indices], dtype=np.float64)
    forces = None if sample_catalog.transformed_forces is None else sample_catalog.transformed_forces[samples]
    force_mask = sample_catalog.evidence_masks.force_mask[samples] if hasattr(sample_catalog.evidence_masks, "force_mask") else np.zeros(samples.size, dtype=np.bool_)
    # Current evidence-mask contract exposes mask_for; use it as the authoritative fallback.
    if hasattr(sample_catalog.evidence_masks, "mask_for"):
        force_mask = np.asarray(sample_catalog.evidence_masks.mask_for("force")[samples], dtype=np.bool_)
    sliced = _evidence_slice(evidence, samples)
    primary, ambiguity = _primary_structural_id(sliced["ring_ids"])
    density = sliced["density_values"]; pmf = sliced["pmf_values"]
    return ObservedTransitionEvent(
        event_id, member_index, passage.passage_id, sample_catalog.signature, final.signature,
        passage.atom_index, passage.segment_id, passage.source_state_id, passage.target_state_id,
        candidate_array, status, successful, samples, frame_indices, sample_catalog.frame_ids[samples], path_times,
        sample_catalog.represented_time_weights[samples], sample_catalog.registered_positions[samples],
        sample_catalog.registered_wrapped_fractional[samples], sample_catalog.registered_image_shifts[samples],
        sample_catalog.registered_image_shifts[samples][-1] - sample_catalog.registered_image_shifts[samples][0],
        source_bracket, target_bracket, _minimum_resolvable_duration(sample_catalog, frame_indices),
        forces, force_mask, sliced["status"], sliced["ring_ids"], sliced["ring_sector_ids"],
        sliced["feature_names"], sliced["coordination_values"], sliced["harmonic_names"],
        sliced["harmonic_amplitudes"], sliced["harmonic_phases"], sliced["apertures"],
        sliced["puckering"], sliced["local_occupancy"], density, pmf,
        None if density is None else float(np.min(density)), None if pmf is None else float(np.max(pmf)),
        primary, ambiguity, _occupancy_context(sample_catalog, final, frame_indices),
        np.empty(0, dtype=np.int64), CollectiveEventStatus.ISOLATED_SINGLE_ION,
        passage.boundary_induced, passage.contains_unknown, passage.contains_conflict,
        False, status is FirstHitResolutionStatus.RIGHT_CENSORED,
        {"rates_deferred": True, "interpolation_used": False, "shoulder_promotion_deferred": True},
    )


def _overlap(a: ObservedTransitionEvent, b: ObservedTransitionEvent, window: int) -> bool:
    if a.member_index != b.member_index or a.segment_id != b.segment_id or a.atom_index == b.atom_index:
        return False
    return int(np.min(a.frame_indices)) <= int(np.max(b.frame_indices)) + window and int(np.min(b.frame_indices)) <= int(np.max(a.frame_indices)) + window


def _classify_collective(events: list[ObservedTransitionEvent], window: int) -> list[ObservedTransitionEvent]:
    links: dict[int, list[int]] = defaultdict(list)
    for i, a in enumerate(events):
        for b in events[i + 1:]:
            if _overlap(a, b, window):
                links[a.event_id].append(b.event_id); links[b.event_id].append(a.event_id)
    by_id = {v.event_id: v for v in events}
    result = []
    for event in events:
        concurrent = np.asarray(sorted(links.get(event.event_id, [])), dtype=np.int64)
        if concurrent.size == 0:
            status = CollectiveEventStatus.ISOLATED_SINGLE_ION
        else:
            others = [by_id[int(v)] for v in concurrent]
            exchange = any(event.successful_connection and other.successful_connection and
                           event.source_state_id == other.target_state_id and event.target_state_id == other.source_state_id
                           for other in others)
            concerted = any(event.successful_connection and other.successful_connection and
                            event.source_state_id == other.source_state_id and event.target_state_id == other.target_state_id
                            for other in others)
            if exchange: status = CollectiveEventStatus.CANDIDATE_EXCHANGE
            elif concerted: status = CollectiveEventStatus.CANDIDATE_CONCERTED
            elif all(v.successful_connection for v in [event, *others]): status = CollectiveEventStatus.TEMPORALLY_OVERLAPPING
            else: status = CollectiveEventStatus.COLLECTIVE_UNRESOLVED
        result.append(replace(event, concurrent_event_ids=concurrent, collective_status=status, signature=""))
    return result


def _resample_path(positions: np.ndarray, points: int) -> np.ndarray:
    if positions.shape[0] == 1:
        return np.repeat(positions, points, axis=0)
    lengths = np.linalg.norm(np.diff(positions, axis=0), axis=1)
    arc = np.r_[0.0, np.cumsum(lengths)]
    if arc[-1] <= np.finfo(float).tiny:
        return np.repeat(positions[:1], points, axis=0)
    targets = np.linspace(0.0, arc[-1], points)
    return np.column_stack([np.interp(targets, arc, positions[:, axis]) for axis in range(3)])


def _cluster_events(events: list[ObservedTransitionEvent], options: TransitionPathOptions) -> tuple[PathClusteringStatus, np.ndarray]:
    n = len(events)
    labels = np.full(n, -1, dtype=np.int32)
    if not options.enable_path_clustering:
        return PathClusteringStatus.NOT_REQUESTED, labels
    if n < options.minimum_paths_for_clustering:
        return PathClusteringStatus.INSUFFICIENT_PATHS, labels
    paths = [_resample_path(v.registered_positions - v.registered_positions[0], options.clustering_resample_points) for v in events]
    adjacency = np.eye(n, dtype=np.bool_)
    for i in range(n):
        for j in range(i + 1, n):
            rmsd = float(np.sqrt(np.mean(np.sum((paths[i] - paths[j]) ** 2, axis=1))))
            adjacency[i, j] = adjacency[j, i] = rmsd <= options.clustering_rmsd_threshold
    cluster = 0
    for start in range(n):
        if labels[start] >= 0: continue
        stack = [start]; labels[start] = cluster
        while stack:
            node = stack.pop()
            for neighbor in np.flatnonzero(adjacency[node]):
                if labels[neighbor] < 0:
                    labels[neighbor] = cluster; stack.append(int(neighbor))
        cluster += 1
    return PathClusteringStatus.RESOLVED, labels


def _prepare_ensembles(events: Sequence[ObservedTransitionEvent], compatibility: RegistrationCompatibilityClass,
                       options: TransitionPathOptions) -> tuple[TransitionPathEnsemble, ...]:
    grouped: dict[tuple[int, int, tuple[int, int, int], int | None], list[ObservedTransitionEvent]] = defaultdict(list)
    for event in events:
        if not event.successful_connection or event.contains_unknown or event.contains_conflict:
            continue
        source = compatibility.canonical_state(event.member_index, int(event.source_state_id))
        target = compatibility.canonical_state(event.member_index, int(event.target_state_id))
        grouped[(source, target, tuple(int(v) for v in event.periodic_translation), event.primary_structural_id)].append(event)
    ensembles = []
    for ensemble_id, (key, members) in enumerate(sorted(grouped.items(), key=lambda item: item[0])):
        source, target, translation, structural = key
        event_ids = np.asarray(sorted(v.event_id for v in members), dtype=np.int64)
        n = len(members)
        status = (PathEnsembleStatus.SINGLE_OBSERVED_PATH if n == 1 else
                  PathEnsembleStatus.PATH_ENSEMBLE_RESOLVED if n >= options.minimum_paths_for_resolved_ensemble else
                  PathEnsembleStatus.PATH_ENSEMBLE_UNDERSAMPLED)
        clustering_status, labels = _cluster_events(members, options)
        durations = np.asarray([v.represented_time for v in members], dtype=np.float64)
        ensembles.append(TransitionPathEnsemble(
            ensemble_id, source, target, np.asarray(translation, dtype=np.int64), structural,
            compatibility.signature, event_ids, status, clustering_status, labels,
            float(np.mean(durations)), float(np.std(durations, ddof=1)) if n > 1 else 0.0,
            {"rates_identified": False, "representative_path_claimed": status is PathEnsembleStatus.PATH_ENSEMBLE_RESOLVED},
        ))
    return tuple(ensembles)


def prepare_observed_transition_paths(
    sample_catalogs: FrameworkAlignedIonSampleCatalog | Sequence[FrameworkAlignedIonSampleCatalog],
    final_segmentations: FinalHystereticSegmentationCatalog | Sequence[FinalHystereticSegmentationCatalog],
    *,
    evidence_tables: TransitionPathEvidenceTable | None | Sequence[TransitionPathEvidenceTable | None] = None,
    first_hit_candidate_states: Mapping[int, Sequence[int]] | Sequence[Mapping[int, Sequence[int]]] | None = None,
    registration_compatibility: RegistrationCompatibilityClass | None = None,
    state_correspondence: Sequence[tuple[int, int, int]] = (),
    options: TransitionPathOptions | None = None,
    resources: TransitionPathResourcePolicy | None = None,
) -> ObservedTransitionPathCatalog:
    """Reconstruct observed E6b paths and registration-compatible ensembles."""
    catalogs = (sample_catalogs,) if isinstance(sample_catalogs, FrameworkAlignedIonSampleCatalog) else tuple(sample_catalogs)
    finals = (final_segmentations,) if isinstance(final_segmentations, FinalHystereticSegmentationCatalog) else tuple(final_segmentations)
    if len(catalogs) != len(finals) or not catalogs:
        raise TransitionPathInputError("Sample catalogs and final segmentations must be nonempty and aligned.")
    if evidence_tables is None or isinstance(evidence_tables, TransitionPathEvidenceTable):
        tables = (evidence_tables,) * len(catalogs)
    else:
        tables = tuple(evidence_tables)
    if len(tables) != len(catalogs):
        raise TransitionPathInputError("Evidence tables must align with catalog members.")
    if first_hit_candidate_states is None or isinstance(first_hit_candidate_states, Mapping):
        candidate_maps = ({} if first_hit_candidate_states is None else first_hit_candidate_states,) * len(catalogs)
    else:
        candidate_maps = tuple(first_hit_candidate_states)
    if len(candidate_maps) != len(catalogs):
        raise TransitionPathInputError("First-hit candidate maps must align with catalog members.")
    opts = options or TransitionPathOptions(); limits = resources or TransitionPathResourcePolicy()
    compatibility = registration_compatibility or prepare_registration_compatibility_class(catalogs, state_correspondence=state_correspondence)
    if compatibility.member_sample_catalog_signatures != tuple(v.signature for v in catalogs):
        raise TransitionPathInputError("Registration compatibility does not bind the supplied sample catalogs in order.")
    event_count = sum(len(v.passages) for v in finals)
    if event_count > limits.max_events:
        raise TransitionPathResourceError(f"Transition events {event_count}>{limits.max_events}.")
    total_path_samples = 0; annotation_values = 0
    for catalog, final, table in zip(catalogs, finals, tables, strict=True):
        if final.sample_catalog_signature != catalog.signature:
            raise TransitionPathInputError("Final segmentation is not bound to its sample catalog.")
        if table is not None:
            if table.sample_catalog_signature != catalog.signature or np.any(table.sample_indices >= catalog.n_samples):
                raise TransitionPathInputError("Transition evidence table is not bound to its sample catalog.")
            annotation_values += int(table.coordination_values.size + table.harmonic_amplitudes.size + table.harmonic_phases.size)
        total_path_samples += sum(max(1, len(v.sample_indices) + 2) for v in final.passages)
    if total_path_samples > limits.max_path_samples:
        raise TransitionPathResourceError(f"Transition path samples {total_path_samples}>{limits.max_path_samples}.")
    if annotation_values > limits.max_annotation_values:
        raise TransitionPathResourceError(f"Transition annotation values {annotation_values}>{limits.max_annotation_values}.")
    events: list[ObservedTransitionEvent] = []
    for member, (catalog, final, table, candidate_map) in enumerate(zip(catalogs, finals, tables, candidate_maps, strict=True)):
        for passage in final.passages:
            if not opts.include_failed_passages and not passage.counted_transition:
                continue
            events.append(_build_event(member, len(events), catalog, final, passage, table,
                                       candidate_map.get(passage.passage_id, ())))
    events = _classify_collective(events, opts.concurrent_frame_window)
    ensembles = _prepare_ensembles(events, compatibility, opts)
    if len(ensembles) > limits.max_ensembles:
        raise TransitionPathResourceError(f"Transition path ensembles {len(ensembles)}>{limits.max_ensembles}.")
    result = ObservedTransitionPathCatalog(
        opts, limits, compatibility, tuple(v.signature for v in catalogs), tuple(v.signature for v in finals),
        tuple(events), ensembles,
        {"rates_deferred": True, "barriers_deferred": True, "global_pmf_deferred": True,
         "n_successful_connections": sum(v.successful_connection for v in events),
         "n_failed_or_unresolved_passages": sum(not v.successful_connection for v in events)},
    )
    estimated_bytes = len(_canonical_json(result.to_dict()).encode("utf-8"))
    if estimated_bytes > limits.max_output_bytes:
        raise TransitionPathResourceError(f"Serialized transition-path output {estimated_bytes}>{limits.max_output_bytes} bytes.")
    return result


__all__ = [
    "TRANSITION_PATH_STAGE", "TRANSITION_PATH_OPTIONS_SCHEMA", "TRANSITION_PATH_RESOURCES_SCHEMA",
    "PATH_EVIDENCE_TABLE_SCHEMA", "REGISTRATION_COMPATIBILITY_SCHEMA", "OCCUPANCY_CONTEXT_SCHEMA",
    "OBSERVED_TRANSITION_EVENT_SCHEMA", "TRANSITION_PATH_ENSEMBLE_SCHEMA", "TRANSITION_PATH_CATALOG_SCHEMA",
    "TransitionPathError", "TransitionPathInputError", "TransitionPathResourceError", "TransitionPathSerializationError",
    "FirstHitResolutionStatus", "PathEvidenceStatus", "CollectiveEventStatus", "PathEnsembleStatus",
    "PathClusteringStatus", "TransitionPathOptions", "TransitionPathResourcePolicy", "TransitionPathEvidenceTable",
    "RegistrationCompatibilityClass", "TransitionOccupancyContext", "ObservedTransitionEvent",
    "TransitionPathEnsemble", "ObservedTransitionPathCatalog", "prepare_registration_compatibility_class",
    "prepare_observed_transition_paths",
]
