"""Stage-11E7 observed periodic network and transferred-model validation.

This stage composes immutable Stage-11E5 validated state instances with the
Stage-11E6b observed transition-path catalog.  It preserves statistical-state
instances, structural site complexes, validated symmetry orbits, semantic
classes, and canonical transfer models as distinct identities.  Structural
adjacency never creates an observed edge, and a compact transferred model never
creates a rate or merges state instances.

Observed-network summaries and transfer-domain bookkeeping are mdstats-specific
constructions.  Network aggregation and held-out/external validation are
standard scientific background.
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

from ...coordinates import AnalysisGeometryMetric, closest_periodic_image
from .evidence_validation import ValidatedFrozenCatalog
from .transition_paths import ObservedTransitionPathCatalog

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
Int32Array = NDArray[np.int32]
BoolArray = NDArray[np.bool_]

OBSERVED_NETWORK_STAGE = "11E7"
OBSERVED_NETWORK_OPTIONS_SCHEMA = "mdstats.observed-network-options.v1"
OBSERVED_NETWORK_RESOURCES_SCHEMA = "mdstats.observed-network-resources.v1"
STRUCTURAL_EDGE_SCHEMA = "mdstats.structural-network-edge.v1"
OBSERVED_NODE_SCHEMA = "mdstats.observed-network-node.v1"
OBSERVED_EDGE_SCHEMA = "mdstats.observed-network-edge.v1"
SITE_COMPLEX_SUMMARY_SCHEMA = "mdstats.site-complex-summary.v1"
SYMMETRY_ORBIT_SUMMARY_SCHEMA = "mdstats.symmetry-orbit-summary.v1"
SEMANTIC_CLASS_SUMMARY_SCHEMA = "mdstats.semantic-class-summary.v1"
COMPACT_STATE_MODEL_SCHEMA = "mdstats.compact-transferred-state-model.v1"
TRANSFER_DOMAIN_SCHEMA = "mdstats.transfer-domain-metadata.v1"
TRANSFER_APPLICATION_SCHEMA = "mdstats.transfer-application-result.v1"
OBSERVED_NETWORK_CATALOG_SCHEMA = "mdstats.observed-network-model-catalog.v1"


class ObservedNetworkError(ValueError):
    """Base Stage-11E7 error."""


class ObservedNetworkInputError(ObservedNetworkError):
    """Raised when source binding or network evidence is inconsistent."""


class ObservedNetworkResourceError(ObservedNetworkError):
    """Raised transactionally before declared resource limits are exceeded."""


class ObservedNetworkSerializationError(ObservedNetworkError):
    """Raised when serialized E7 data are malformed or tampered with."""


class StructuralEdgeComparisonStatus(str, Enum):
    OBSERVED_AND_STRUCTURAL = "observed_and_structural"
    OBSERVED_OFF_STRUCTURAL_NETWORK = "observed_off_structural_network"
    STRUCTURAL_UNOBSERVED = "structural_unobserved"
    STRUCTURAL_COMPARISON_UNAVAILABLE = "structural_comparison_unavailable"


class CompactModelStatus(str, Enum):
    RESOLVED = "resolved"
    SINGLE_INSTANCE = "single_instance"
    PERIODIC_ANCHOR_AMBIGUOUS = "periodic_anchor_ambiguous"


class TransferApplicationKind(str, Enum):
    UNTOUCHED_FINAL_VALIDATION = "untouched_final_validation"
    EXTERNAL_TRANSFER = "external_transfer"


class TransferValidationStatus(str, Enum):
    REPRODUCED_WITHIN_UNCERTAINTY = "reproduced_within_uncertainty"
    PARTIAL_REPRODUCTION = "partial_reproduction"
    OFF_NETWORK_EVENTS = "off_network_events"
    FAILED_TRANSFER = "failed_transfer"
    DOMAIN_MISMATCH = "domain_mismatch"
    REFERENCE_UNAVAILABLE = "reference_unavailable"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


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
        raise ObservedNetworkInputError(f"{name} must be a SHA-256 digest.")
    return value


def _readonly(value: Any, *, dtype: Any, ndim: int, name: str, shape: tuple[int, ...] | None = None) -> np.ndarray:
    arr = np.array(value, dtype=dtype, copy=True, order="C")
    if arr.ndim != ndim or (shape is not None and arr.shape != shape):
        raise ObservedNetworkInputError(f"{name} has invalid shape {arr.shape}.")
    if np.issubdtype(arr.dtype, np.floating) and np.any(~np.isfinite(arr)):
        raise ObservedNetworkInputError(f"{name} contains non-finite values.")
    arr.setflags(write=False)
    return arr


def _freeze(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        result = float(value)
        if not np.isfinite(result):
            raise ObservedNetworkInputError("Metadata contains a non-finite float.")
        return result
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in sorted(value.items(), key=lambda p: str(p[0]))})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    raise ObservedNetworkInputError(f"Unsupported metadata value {type(value).__name__}.")


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
        raise ObservedNetworkInputError(f"{name} must be a positive integer.")
    return int(value)


def _nonnegative(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise ObservedNetworkInputError(f"{name} must be finite and nonnegative.")
    return result


def _edge_key(source: int, target: int, translation: Sequence[int]) -> tuple[int, int, int, int, int]:
    t = tuple(int(v) for v in translation)
    if len(t) != 3:
        raise ObservedNetworkInputError("A periodic edge translation must have length three.")
    return int(source), int(target), t[0], t[1], t[2]


@dataclass(frozen=True, slots=True)
class ObservedNetworkOptions:
    minimum_events_for_observed_edge: int = 1
    minimum_anchor_concentration: float = 0.15
    default_transfer_radius: float = 0.25
    default_ambiguity_distance: float = 0.02
    default_mismatch_tolerance: float = 0.10
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        minimum = _positive_int(self.minimum_events_for_observed_edge, "minimum_events_for_observed_edge")
        concentration = _nonnegative(self.minimum_anchor_concentration, "minimum_anchor_concentration")
        if concentration > 1.0:
            raise ObservedNetworkInputError("minimum_anchor_concentration must not exceed one.")
        radius = _nonnegative(self.default_transfer_radius, "default_transfer_radius")
        ambiguity = _nonnegative(self.default_ambiguity_distance, "default_ambiguity_distance")
        tolerance = _nonnegative(self.default_mismatch_tolerance, "default_mismatch_tolerance")
        if tolerance > 1.0:
            raise ObservedNetworkInputError("default_mismatch_tolerance must not exceed one.")
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": OBSERVED_NETWORK_OPTIONS_SCHEMA, "minimum_events_for_observed_edge": minimum,
                   "minimum_anchor_concentration": concentration, "default_transfer_radius": radius,
                   "default_ambiguity_distance": ambiguity, "default_mismatch_tolerance": tolerance,
                   "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise ObservedNetworkInputError("Observed-network options signature is inconsistent.")
        for name, value in (("minimum_events_for_observed_edge", minimum),
                            ("minimum_anchor_concentration", concentration),
                            ("default_transfer_radius", radius), ("default_ambiguity_distance", ambiguity),
                            ("default_mismatch_tolerance", tolerance), ("metadata", metadata), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": OBSERVED_NETWORK_OPTIONS_SCHEMA,
                "minimum_events_for_observed_edge": self.minimum_events_for_observed_edge,
                "minimum_anchor_concentration": self.minimum_anchor_concentration,
                "default_transfer_radius": self.default_transfer_radius,
                "default_ambiguity_distance": self.default_ambiguity_distance,
                "default_mismatch_tolerance": self.default_mismatch_tolerance,
                "metadata": _json_value(self.metadata), "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "ObservedNetworkOptions":
        if p.get("schema") != OBSERVED_NETWORK_OPTIONS_SCHEMA:
            raise ObservedNetworkSerializationError("Unsupported observed-network options schema.")
        return cls(int(p["minimum_events_for_observed_edge"]), float(p["minimum_anchor_concentration"]),
                   float(p["default_transfer_radius"]), float(p["default_ambiguity_distance"]),
                   float(p["default_mismatch_tolerance"]), dict(p.get("metadata", {})), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class ObservedNetworkResourcePolicy:
    max_state_instances: int = 100_000
    max_observed_edges: int = 500_000
    max_structural_edges: int = 500_000
    max_transfer_samples: int = 5_000_000
    max_transfer_applications: int = 10_000
    signature: str = ""

    def __post_init__(self) -> None:
        values = {name: _positive_int(getattr(self, name), name) for name in (
            "max_state_instances", "max_observed_edges", "max_structural_edges",
            "max_transfer_samples", "max_transfer_applications")}
        expected = _digest({"schema": OBSERVED_NETWORK_RESOURCES_SCHEMA, **values})
        if self.signature and self.signature != expected:
            raise ObservedNetworkInputError("Observed-network resources signature is inconsistent.")
        for name, value in values.items(): object.__setattr__(self, name, value)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": OBSERVED_NETWORK_RESOURCES_SCHEMA, **{name: getattr(self, name) for name in (
            "max_state_instances", "max_observed_edges", "max_structural_edges",
            "max_transfer_samples", "max_transfer_applications")}, "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "ObservedNetworkResourcePolicy":
        if p.get("schema") != OBSERVED_NETWORK_RESOURCES_SCHEMA:
            raise ObservedNetworkSerializationError("Unsupported observed-network resources schema.")
        return cls(*(int(p[name]) for name in ("max_state_instances", "max_observed_edges", "max_structural_edges",
                                                "max_transfer_samples", "max_transfer_applications")),
                   signature=str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class StructuralNetworkEdge:
    source_state_id: int
    target_state_id: int
    periodic_translation: IntArray
    structural_identity: str | None = None
    provenance: str = "declared_structural_candidate"
    signature: str = ""

    def __post_init__(self) -> None:
        source, target = int(self.source_state_id), int(self.target_state_id)
        if min(source, target) < 0 or source == target:
            raise ObservedNetworkInputError("Structural network edges require distinct nonnegative states.")
        translation = _readonly(self.periodic_translation, dtype=np.int64, ndim=1,
                                name="periodic_translation", shape=(3,))
        identity = None if self.structural_identity is None else str(self.structural_identity).strip()
        provenance = str(self.provenance).strip()
        if self.structural_identity is not None and not identity or not provenance:
            raise ObservedNetworkInputError("Structural edge identity/provenance must be nonempty when supplied.")
        payload = {"schema": STRUCTURAL_EDGE_SCHEMA, "source_state_id": source, "target_state_id": target,
                   "periodic_translation": translation.tolist(), "structural_identity": identity,
                   "provenance": provenance}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise ObservedNetworkInputError("Structural-edge signature is inconsistent.")
        for name, value in (("source_state_id", source), ("target_state_id", target),
                            ("periodic_translation", translation), ("structural_identity", identity),
                            ("provenance", provenance), ("signature", expected)):
            object.__setattr__(self, name, value)

    @property
    def key(self) -> tuple[int, int, int, int, int]:
        return _edge_key(self.source_state_id, self.target_state_id, self.periodic_translation)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": STRUCTURAL_EDGE_SCHEMA, "source_state_id": self.source_state_id,
                "target_state_id": self.target_state_id, "periodic_translation": self.periodic_translation.tolist(),
                "structural_identity": self.structural_identity, "provenance": self.provenance,
                "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "StructuralNetworkEdge":
        if p.get("schema") != STRUCTURAL_EDGE_SCHEMA:
            raise ObservedNetworkSerializationError("Unsupported structural-edge schema.")
        return cls(int(p["source_state_id"]), int(p["target_state_id"]),
                   np.asarray(p["periodic_translation"], dtype=np.int64), p.get("structural_identity"),
                   str(p.get("provenance", "declared_structural_candidate")), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class ObservedNetworkNode:
    node_id: int
    member_index: int
    local_state_id: int
    canonical_state_id: int
    validated_state_signature: str
    anchor_fractional: FloatArray
    geometry: str
    overall_evidence_status: str
    final_validation_status: str
    structural_complex_ids: Int32Array
    symmetry_orbit_ids: Int32Array
    structural_identities: tuple[str, ...]
    primary_structural_identity: str | None
    semantic_class: str | None = None
    signature: str = ""

    def __post_init__(self) -> None:
        ids = {n: int(getattr(self, n)) for n in ("node_id", "member_index", "local_state_id", "canonical_state_id")}
        if min(ids.values()) < 0:
            raise ObservedNetworkInputError("Observed-network node identifiers must be nonnegative.")
        state_sig = _sha(self.validated_state_signature, "validated_state_signature")
        anchor = _readonly(self.anchor_fractional, dtype=np.float64, ndim=1, name="anchor_fractional", shape=(3,))
        anchor = np.mod(anchor, 1.0); anchor.setflags(write=False)
        geometry = str(self.geometry); overall = str(self.overall_evidence_status); final = str(self.final_validation_status)
        complexes = _readonly(self.structural_complex_ids, dtype=np.int32, ndim=1, name="structural_complex_ids")
        orbits = _readonly(self.symmetry_orbit_ids, dtype=np.int32, ndim=1, name="symmetry_orbit_ids")
        if np.any(complexes < 0) or np.any(orbits < 0):
            raise ObservedNetworkInputError("Structural summary identifiers must be nonnegative.")
        identities = tuple(sorted({str(v) for v in self.structural_identities if str(v)}))
        primary = None if self.primary_structural_identity is None else str(self.primary_structural_identity)
        if primary is not None and primary not in identities:
            raise ObservedNetworkInputError("Primary structural identity must belong to retained identities.")
        semantic = None if self.semantic_class is None else str(self.semantic_class).strip()
        if self.semantic_class is not None and not semantic:
            raise ObservedNetworkInputError("semantic_class must be nonempty when supplied.")
        payload = {"schema": OBSERVED_NODE_SCHEMA, **ids, "validated_state_signature": state_sig,
                   "anchor_digest": _array_digest(anchor), "geometry": geometry,
                   "overall_evidence_status": overall, "final_validation_status": final,
                   "structural_complex_ids_digest": _array_digest(complexes),
                   "symmetry_orbit_ids_digest": _array_digest(orbits),
                   "structural_identities": list(identities), "primary_structural_identity": primary,
                   "semantic_class": semantic}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise ObservedNetworkInputError("Observed-network node signature is inconsistent.")
        assignments = tuple(ids.items()) + (
            ("validated_state_signature", state_sig), ("anchor_fractional", anchor),
            ("geometry", geometry), ("overall_evidence_status", overall),
            ("final_validation_status", final), ("structural_complex_ids", complexes),
            ("symmetry_orbit_ids", orbits), ("structural_identities", identities),
            ("primary_structural_identity", primary), ("semantic_class", semantic),
            ("signature", expected),
        )
        for name, value in assignments:
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": OBSERVED_NODE_SCHEMA, "node_id": self.node_id, "member_index": self.member_index,
                "local_state_id": self.local_state_id, "canonical_state_id": self.canonical_state_id,
                "validated_state_signature": self.validated_state_signature,
                "anchor_fractional": self.anchor_fractional.tolist(), "geometry": self.geometry,
                "overall_evidence_status": self.overall_evidence_status,
                "final_validation_status": self.final_validation_status,
                "structural_complex_ids": self.structural_complex_ids.tolist(),
                "symmetry_orbit_ids": self.symmetry_orbit_ids.tolist(),
                "structural_identities": list(self.structural_identities),
                "primary_structural_identity": self.primary_structural_identity,
                "semantic_class": self.semantic_class, "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "ObservedNetworkNode":
        if p.get("schema") != OBSERVED_NODE_SCHEMA:
            raise ObservedNetworkSerializationError("Unsupported observed-node schema.")
        return cls(int(p["node_id"]), int(p["member_index"]), int(p["local_state_id"]),
                   int(p["canonical_state_id"]), str(p["validated_state_signature"]),
                   np.asarray(p["anchor_fractional"], dtype=float), str(p["geometry"]),
                   str(p["overall_evidence_status"]), str(p["final_validation_status"]),
                   np.asarray(p["structural_complex_ids"], dtype=np.int32),
                   np.asarray(p["symmetry_orbit_ids"], dtype=np.int32), tuple(p["structural_identities"]),
                   p.get("primary_structural_identity"), p.get("semantic_class"), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class ObservedNetworkEdge:
    edge_id: int
    source_state_id: int
    target_state_id: int
    periodic_translation: IntArray
    ensemble_ids: IntArray
    event_ids: IntArray
    observed_event_count: int
    ensemble_statuses: tuple[str, ...]
    duration_mean: float
    duration_std: float
    structural_comparison: StructuralEdgeComparisonStatus
    structural_edge_signatures: tuple[str, ...]
    primary_structural_ids: Int32Array
    signature: str = ""

    def __post_init__(self) -> None:
        edge, source, target, count = int(self.edge_id), int(self.source_state_id), int(self.target_state_id), int(self.observed_event_count)
        if min(edge, source, target) < 0 or source == target or count <= 0:
            raise ObservedNetworkInputError("Observed edges require valid identifiers and positive support.")
        translation = _readonly(self.periodic_translation, dtype=np.int64, ndim=1, name="periodic_translation", shape=(3,))
        ensembles = _readonly(self.ensemble_ids, dtype=np.int64, ndim=1, name="ensemble_ids")
        events = _readonly(self.event_ids, dtype=np.int64, ndim=1, name="event_ids")
        if ensembles.size == 0 or events.size != count or np.any(ensembles < 0) or np.any(events < 0):
            raise ObservedNetworkInputError("Observed edge support identifiers are inconsistent.")
        statuses = tuple(str(v) for v in self.ensemble_statuses)
        if len(statuses) != ensembles.size:
            raise ObservedNetworkInputError("Ensemble statuses must align with ensemble IDs.")
        mean = _nonnegative(self.duration_mean, "duration_mean"); std = _nonnegative(self.duration_std, "duration_std")
        comparison = StructuralEdgeComparisonStatus(self.structural_comparison)
        structural = tuple(_sha(v, "structural edge signature") for v in self.structural_edge_signatures)
        primary = _readonly(self.primary_structural_ids, dtype=np.int32, ndim=1, name="primary_structural_ids")
        if np.any(primary < 0):
            raise ObservedNetworkInputError("primary_structural_ids must be nonnegative.")
        if comparison is StructuralEdgeComparisonStatus.OBSERVED_AND_STRUCTURAL and not structural:
            raise ObservedNetworkInputError("Observed-and-structural edges require structural support.")
        payload = {"schema": OBSERVED_EDGE_SCHEMA, "edge_id": edge, "source_state_id": source,
                   "target_state_id": target, "periodic_translation": translation.tolist(),
                   "ensemble_ids_digest": _array_digest(ensembles), "event_ids_digest": _array_digest(events),
                   "observed_event_count": count, "ensemble_statuses": list(statuses),
                   "duration_mean": mean, "duration_std": std, "structural_comparison": comparison.value,
                   "structural_edge_signatures": list(structural), "primary_structural_ids_digest": _array_digest(primary)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise ObservedNetworkInputError("Observed-edge signature is inconsistent.")
        for name, value in (("edge_id", edge), ("source_state_id", source), ("target_state_id", target),
                            ("periodic_translation", translation), ("ensemble_ids", ensembles), ("event_ids", events),
                            ("observed_event_count", count), ("ensemble_statuses", statuses),
                            ("duration_mean", mean), ("duration_std", std), ("structural_comparison", comparison),
                            ("structural_edge_signatures", structural), ("primary_structural_ids", primary),
                            ("signature", expected)):
            object.__setattr__(self, name, value)

    @property
    def key(self) -> tuple[int, int, int, int, int]:
        return _edge_key(self.source_state_id, self.target_state_id, self.periodic_translation)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": OBSERVED_EDGE_SCHEMA, "edge_id": self.edge_id, "source_state_id": self.source_state_id,
                "target_state_id": self.target_state_id, "periodic_translation": self.periodic_translation.tolist(),
                "ensemble_ids": self.ensemble_ids.tolist(), "event_ids": self.event_ids.tolist(),
                "observed_event_count": self.observed_event_count, "ensemble_statuses": list(self.ensemble_statuses),
                "duration_mean": self.duration_mean, "duration_std": self.duration_std,
                "structural_comparison": self.structural_comparison.value,
                "structural_edge_signatures": list(self.structural_edge_signatures),
                "primary_structural_ids": self.primary_structural_ids.tolist(), "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "ObservedNetworkEdge":
        if p.get("schema") != OBSERVED_EDGE_SCHEMA:
            raise ObservedNetworkSerializationError("Unsupported observed-edge schema.")
        return cls(int(p["edge_id"]), int(p["source_state_id"]), int(p["target_state_id"]),
                   np.asarray(p["periodic_translation"], dtype=np.int64), np.asarray(p["ensemble_ids"], dtype=np.int64),
                   np.asarray(p["event_ids"], dtype=np.int64), int(p["observed_event_count"]),
                   tuple(p["ensemble_statuses"]), float(p["duration_mean"]), float(p["duration_std"]),
                   StructuralEdgeComparisonStatus(p["structural_comparison"]), tuple(p["structural_edge_signatures"]),
                   np.asarray(p["primary_structural_ids"], dtype=np.int32), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class SiteComplexSummary:
    summary_id: int
    member_index: int
    source_complex_id: int
    source_complex_signature: str
    kind: str
    persistent_identity: str
    member_node_ids: IntArray
    canonical_state_ids: Int32Array
    preliminary: bool
    signature: str = ""

    def __post_init__(self) -> None:
        summary, member, source = int(self.summary_id), int(self.member_index), int(self.source_complex_id)
        if min(summary, member, source) < 0:
            raise ObservedNetworkInputError("Site-complex summary identifiers must be nonnegative.")
        source_sig = _sha(self.source_complex_signature, "source_complex_signature")
        kind, identity = str(self.kind), str(self.persistent_identity)
        nodes = _readonly(self.member_node_ids, dtype=np.int64, ndim=1, name="member_node_ids")
        states = _readonly(self.canonical_state_ids, dtype=np.int32, ndim=1, name="canonical_state_ids")
        if nodes.size == 0 or nodes.size != states.size or np.any(nodes < 0) or np.any(states < 0):
            raise ObservedNetworkInputError("Site-complex members are inconsistent.")
        payload = {"schema": SITE_COMPLEX_SUMMARY_SCHEMA, "summary_id": summary, "member_index": member,
                   "source_complex_id": source, "source_complex_signature": source_sig, "kind": kind,
                   "persistent_identity": identity, "member_node_ids_digest": _array_digest(nodes),
                   "canonical_state_ids_digest": _array_digest(states), "preliminary": bool(self.preliminary)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise ObservedNetworkInputError("Site-complex summary signature is inconsistent.")
        for name, value in (("summary_id", summary), ("member_index", member), ("source_complex_id", source),
                            ("source_complex_signature", source_sig), ("kind", kind),
                            ("persistent_identity", identity), ("member_node_ids", nodes),
                            ("canonical_state_ids", states), ("preliminary", bool(self.preliminary)),
                            ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SITE_COMPLEX_SUMMARY_SCHEMA, "summary_id": self.summary_id,
                "member_index": self.member_index, "source_complex_id": self.source_complex_id,
                "source_complex_signature": self.source_complex_signature, "kind": self.kind,
                "persistent_identity": self.persistent_identity, "member_node_ids": self.member_node_ids.tolist(),
                "canonical_state_ids": self.canonical_state_ids.tolist(), "preliminary": self.preliminary,
                "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "SiteComplexSummary":
        if p.get("schema") != SITE_COMPLEX_SUMMARY_SCHEMA:
            raise ObservedNetworkSerializationError("Unsupported site-complex-summary schema.")
        return cls(int(p["summary_id"]), int(p["member_index"]), int(p["source_complex_id"]),
                   str(p["source_complex_signature"]), str(p["kind"]), str(p["persistent_identity"]),
                   np.asarray(p["member_node_ids"], dtype=np.int64), np.asarray(p["canonical_state_ids"], dtype=np.int32),
                   bool(p["preliminary"]), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class SymmetryOrbitSummary:
    summary_id: int
    member_index: int
    source_orbit_id: int
    source_orbit_signature: str
    label: str
    exchangeability_status: str
    member_node_ids: IntArray
    canonical_state_ids: Int32Array
    augmentation_performed: bool = False
    signature: str = ""

    def __post_init__(self) -> None:
        summary, member, source = int(self.summary_id), int(self.member_index), int(self.source_orbit_id)
        if min(summary, member, source) < 0:
            raise ObservedNetworkInputError("Symmetry-orbit summary identifiers must be nonnegative.")
        source_sig = _sha(self.source_orbit_signature, "source_orbit_signature")
        label, status = str(self.label), str(self.exchangeability_status)
        nodes = _readonly(self.member_node_ids, dtype=np.int64, ndim=1, name="member_node_ids")
        states = _readonly(self.canonical_state_ids, dtype=np.int32, ndim=1, name="canonical_state_ids")
        if nodes.size < 2 or nodes.size != states.size or np.any(nodes < 0) or np.any(states < 0):
            raise ObservedNetworkInputError("Symmetry-orbit members are inconsistent.")
        if self.augmentation_performed:
            raise ObservedNetworkInputError("Stage 11E7 forbids implicit symmetry augmentation.")
        payload = {"schema": SYMMETRY_ORBIT_SUMMARY_SCHEMA, "summary_id": summary, "member_index": member,
                   "source_orbit_id": source, "source_orbit_signature": source_sig, "label": label,
                   "exchangeability_status": status, "member_node_ids_digest": _array_digest(nodes),
                   "canonical_state_ids_digest": _array_digest(states), "augmentation_performed": False}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise ObservedNetworkInputError("Symmetry-orbit summary signature is inconsistent.")
        for name, value in (("summary_id", summary), ("member_index", member), ("source_orbit_id", source),
                            ("source_orbit_signature", source_sig), ("label", label),
                            ("exchangeability_status", status), ("member_node_ids", nodes),
                            ("canonical_state_ids", states), ("augmentation_performed", False),
                            ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SYMMETRY_ORBIT_SUMMARY_SCHEMA, "summary_id": self.summary_id,
                "member_index": self.member_index, "source_orbit_id": self.source_orbit_id,
                "source_orbit_signature": self.source_orbit_signature, "label": self.label,
                "exchangeability_status": self.exchangeability_status,
                "member_node_ids": self.member_node_ids.tolist(), "canonical_state_ids": self.canonical_state_ids.tolist(),
                "augmentation_performed": self.augmentation_performed, "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "SymmetryOrbitSummary":
        if p.get("schema") != SYMMETRY_ORBIT_SUMMARY_SCHEMA:
            raise ObservedNetworkSerializationError("Unsupported symmetry-orbit-summary schema.")
        return cls(int(p["summary_id"]), int(p["member_index"]), int(p["source_orbit_id"]),
                   str(p["source_orbit_signature"]), str(p["label"]), str(p["exchangeability_status"]),
                   np.asarray(p["member_node_ids"], dtype=np.int64), np.asarray(p["canonical_state_ids"], dtype=np.int32),
                   bool(p.get("augmentation_performed", False)), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class SemanticClassSummary:
    class_label: str
    member_node_ids: IntArray
    canonical_state_ids: Int32Array
    signature: str = ""

    def __post_init__(self) -> None:
        label = str(self.class_label).strip()
        nodes = _readonly(self.member_node_ids, dtype=np.int64, ndim=1, name="member_node_ids")
        states = _readonly(self.canonical_state_ids, dtype=np.int32, ndim=1, name="canonical_state_ids")
        if not label or nodes.size == 0 or nodes.size != states.size or np.any(nodes < 0) or np.any(states < 0):
            raise ObservedNetworkInputError("Semantic-class summary is inconsistent.")
        payload = {"schema": SEMANTIC_CLASS_SUMMARY_SCHEMA, "class_label": label,
                   "member_node_ids_digest": _array_digest(nodes), "canonical_state_ids_digest": _array_digest(states)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise ObservedNetworkInputError("Semantic-class summary signature is inconsistent.")
        for name, value in (("class_label", label), ("member_node_ids", nodes),
                            ("canonical_state_ids", states), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SEMANTIC_CLASS_SUMMARY_SCHEMA, "class_label": self.class_label,
                "member_node_ids": self.member_node_ids.tolist(), "canonical_state_ids": self.canonical_state_ids.tolist(),
                "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "SemanticClassSummary":
        if p.get("schema") != SEMANTIC_CLASS_SUMMARY_SCHEMA:
            raise ObservedNetworkSerializationError("Unsupported semantic-class-summary schema.")
        return cls(str(p["class_label"]), np.asarray(p["member_node_ids"], dtype=np.int64),
                   np.asarray(p["canonical_state_ids"], dtype=np.int32), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class CompactTransferredStateModel:
    canonical_state_id: int
    member_node_ids: IntArray
    instance_anchors_fractional: FloatArray
    circular_anchor_fractional: FloatArray
    coordinate_concentrations: FloatArray
    basin_probability_mean: float
    basin_probability_std: float
    mean_occupancy_mean: float
    mean_occupancy_std: float
    structural_identities: tuple[str, ...]
    semantic_classes: tuple[str, ...]
    status: CompactModelStatus
    signature: str = ""

    def __post_init__(self) -> None:
        state = int(self.canonical_state_id)
        if state < 0:
            raise ObservedNetworkInputError("canonical_state_id must be nonnegative.")
        nodes = _readonly(self.member_node_ids, dtype=np.int64, ndim=1, name="member_node_ids")
        anchors = _readonly(self.instance_anchors_fractional, dtype=np.float64, ndim=2,
                            name="instance_anchors_fractional", shape=(nodes.size, 3))
        anchors = np.mod(anchors, 1.0); anchors.setflags(write=False)
        circular = _readonly(self.circular_anchor_fractional, dtype=np.float64, ndim=1,
                             name="circular_anchor_fractional", shape=(3,))
        circular = np.mod(circular, 1.0); circular.setflags(write=False)
        concentrations = _readonly(self.coordinate_concentrations, dtype=np.float64, ndim=1,
                                   name="coordinate_concentrations", shape=(3,))
        if nodes.size == 0 or np.any(nodes < 0) or np.any(concentrations < 0) or np.any(concentrations > 1.0 + 1e-12):
            raise ObservedNetworkInputError("Compact model members/concentrations are inconsistent.")
        values = {name: _nonnegative(getattr(self, name), name) for name in (
            "basin_probability_mean", "basin_probability_std", "mean_occupancy_mean", "mean_occupancy_std")}
        identities = tuple(sorted({str(v) for v in self.structural_identities if str(v)}))
        classes = tuple(sorted({str(v) for v in self.semantic_classes if str(v)}))
        status = CompactModelStatus(self.status)
        payload = {"schema": COMPACT_STATE_MODEL_SCHEMA, "canonical_state_id": state,
                   "member_node_ids_digest": _array_digest(nodes), "anchors_digest": _array_digest(anchors),
                   "circular_anchor_digest": _array_digest(circular),
                   "concentrations_digest": _array_digest(concentrations), **values,
                   "structural_identities": list(identities), "semantic_classes": list(classes),
                   "status": status.value}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise ObservedNetworkInputError("Compact-state-model signature is inconsistent.")
        for name, value in (("canonical_state_id", state), ("member_node_ids", nodes),
                            ("instance_anchors_fractional", anchors), ("circular_anchor_fractional", circular),
                            ("coordinate_concentrations", concentrations), *values.items(),
                            ("structural_identities", identities), ("semantic_classes", classes),
                            ("status", status), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": COMPACT_STATE_MODEL_SCHEMA, "canonical_state_id": self.canonical_state_id,
                "member_node_ids": self.member_node_ids.tolist(),
                "instance_anchors_fractional": self.instance_anchors_fractional.tolist(),
                "circular_anchor_fractional": self.circular_anchor_fractional.tolist(),
                "coordinate_concentrations": self.coordinate_concentrations.tolist(),
                "basin_probability_mean": self.basin_probability_mean,
                "basin_probability_std": self.basin_probability_std,
                "mean_occupancy_mean": self.mean_occupancy_mean, "mean_occupancy_std": self.mean_occupancy_std,
                "structural_identities": list(self.structural_identities),
                "semantic_classes": list(self.semantic_classes), "status": self.status.value,
                "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "CompactTransferredStateModel":
        if p.get("schema") != COMPACT_STATE_MODEL_SCHEMA:
            raise ObservedNetworkSerializationError("Unsupported compact-state-model schema.")
        return cls(int(p["canonical_state_id"]), np.asarray(p["member_node_ids"], dtype=np.int64),
                   np.asarray(p["instance_anchors_fractional"], dtype=float),
                   np.asarray(p["circular_anchor_fractional"], dtype=float),
                   np.asarray(p["coordinate_concentrations"], dtype=float),
                   float(p["basin_probability_mean"]), float(p["basin_probability_std"]),
                   float(p["mean_occupancy_mean"]), float(p["mean_occupancy_std"]),
                   tuple(p["structural_identities"]), tuple(p["semantic_classes"]),
                   CompactModelStatus(p["status"]), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class TransferDomainMetadata:
    domain_id: str
    application_kind: TransferApplicationKind
    species: str
    coordinate_frame: str
    length_units: str
    registration_signature: str | None
    registration_group_signature: str | None
    analysis_metric_covariant: FloatArray
    temperature: float | None = None
    composition: str | None = None
    external_source: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        domain, species, frame, units = (str(v).strip() for v in
                                         (self.domain_id, self.species, self.coordinate_frame, self.length_units))
        if not all((domain, species, frame, units)):
            raise ObservedNetworkInputError("Transfer-domain identifiers must be nonempty.")
        kind = TransferApplicationKind(self.application_kind)
        registration = None if self.registration_signature is None else _sha(self.registration_signature, "registration_signature")
        group = None if self.registration_group_signature is None else _sha(self.registration_group_signature, "registration_group_signature")
        metric = _readonly(self.analysis_metric_covariant, dtype=np.float64, ndim=2,
                           name="analysis_metric_covariant", shape=(3, 3))
        if not np.allclose(metric, metric.T, atol=1e-12) or np.min(np.linalg.eigvalsh(metric)) <= 0.0:
            raise ObservedNetworkInputError("Transfer analysis metric must be symmetric positive definite.")
        temperature = None if self.temperature is None else _nonnegative(self.temperature, "temperature")
        composition = None if self.composition is None else str(self.composition)
        external = None if self.external_source is None else str(self.external_source)
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": TRANSFER_DOMAIN_SCHEMA, "domain_id": domain, "application_kind": kind.value,
                   "species": species, "coordinate_frame": frame, "length_units": units,
                   "registration_signature": registration, "registration_group_signature": group,
                   "analysis_metric_digest": _array_digest(metric), "temperature": temperature,
                   "composition": composition, "external_source": external, "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise ObservedNetworkInputError("Transfer-domain signature is inconsistent.")
        for name, value in (("domain_id", domain), ("application_kind", kind), ("species", species),
                            ("coordinate_frame", frame), ("length_units", units),
                            ("registration_signature", registration), ("registration_group_signature", group),
                            ("analysis_metric_covariant", metric), ("temperature", temperature),
                            ("composition", composition), ("external_source", external),
                            ("metadata", metadata), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": TRANSFER_DOMAIN_SCHEMA, "domain_id": self.domain_id,
                "application_kind": self.application_kind.value, "species": self.species,
                "coordinate_frame": self.coordinate_frame, "length_units": self.length_units,
                "registration_signature": self.registration_signature,
                "registration_group_signature": self.registration_group_signature,
                "analysis_metric_covariant": self.analysis_metric_covariant.tolist(),
                "temperature": self.temperature, "composition": self.composition,
                "external_source": self.external_source, "metadata": _json_value(self.metadata),
                "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "TransferDomainMetadata":
        if p.get("schema") != TRANSFER_DOMAIN_SCHEMA:
            raise ObservedNetworkSerializationError("Unsupported transfer-domain schema.")
        return cls(str(p["domain_id"]), TransferApplicationKind(p["application_kind"]), str(p["species"]),
                   str(p["coordinate_frame"]), str(p["length_units"]), p.get("registration_signature"),
                   p.get("registration_group_signature"), np.asarray(p["analysis_metric_covariant"], dtype=float),
                   p.get("temperature"), p.get("composition"), p.get("external_source"),
                   dict(p.get("metadata", {})), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class TransferApplicationResult:
    application_id: int
    model_basis_signature: str
    domain: TransferDomainMetadata
    assigned_state_ids: Int32Array
    minimum_distances: FloatArray
    ambiguity_mask: BoolArray
    outside_domain_mask: BoolArray
    reference_state_ids: Int32Array | None
    observed_transition_edges: IntArray
    off_network_transition_edges: IntArray
    assigned_fraction: float
    mismatch_fraction: float | None
    unresolved_fraction: float
    status: TransferValidationStatus
    diagnostics: tuple[str, ...] = ()
    signature: str = ""

    def __post_init__(self) -> None:
        application = int(self.application_id)
        if application < 0:
            raise ObservedNetworkInputError("application_id must be nonnegative.")
        model = _sha(self.model_basis_signature, "model_basis_signature")
        assigned = _readonly(self.assigned_state_ids, dtype=np.int32, ndim=1, name="assigned_state_ids")
        n = assigned.size
        distances = _readonly(self.minimum_distances, dtype=np.float64, ndim=1, name="minimum_distances", shape=(n,))
        ambiguous = _readonly(self.ambiguity_mask, dtype=np.bool_, ndim=1, name="ambiguity_mask", shape=(n,))
        outside = _readonly(self.outside_domain_mask, dtype=np.bool_, ndim=1, name="outside_domain_mask", shape=(n,))
        reference = None if self.reference_state_ids is None else _readonly(
            self.reference_state_ids, dtype=np.int32, ndim=1, name="reference_state_ids", shape=(n,))
        observed = _readonly(self.observed_transition_edges, dtype=np.int64, ndim=2,
                             name="observed_transition_edges")
        off = _readonly(self.off_network_transition_edges, dtype=np.int64, ndim=2,
                        name="off_network_transition_edges")
        if observed.shape[1:] != (5,) or off.shape[1:] != (5,):
            raise ObservedNetworkInputError("Transfer transition edges must have shape (n, 5).")
        assigned_fraction = _nonnegative(self.assigned_fraction, "assigned_fraction")
        unresolved_fraction = _nonnegative(self.unresolved_fraction, "unresolved_fraction")
        mismatch = None if self.mismatch_fraction is None else _nonnegative(self.mismatch_fraction, "mismatch_fraction")
        if max(assigned_fraction, unresolved_fraction, 0.0 if mismatch is None else mismatch) > 1.0 + 1e-12:
            raise ObservedNetworkInputError("Transfer fractions must not exceed one.")
        status = TransferValidationStatus(self.status); diagnostics = tuple(str(v) for v in self.diagnostics)
        payload = {"schema": TRANSFER_APPLICATION_SCHEMA, "application_id": application,
                   "model_basis_signature": model, "domain_signature": self.domain.signature,
                   "assigned_digest": _array_digest(assigned), "distance_digest": _array_digest(distances),
                   "ambiguity_digest": _array_digest(ambiguous), "outside_digest": _array_digest(outside),
                   "reference_digest": None if reference is None else _array_digest(reference),
                   "observed_edges_digest": _array_digest(observed), "off_network_edges_digest": _array_digest(off),
                   "assigned_fraction": assigned_fraction, "mismatch_fraction": mismatch,
                   "unresolved_fraction": unresolved_fraction, "status": status.value,
                   "diagnostics": list(diagnostics)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise ObservedNetworkInputError("Transfer-application signature is inconsistent.")
        for name, value in (("application_id", application), ("model_basis_signature", model),
                            ("assigned_state_ids", assigned), ("minimum_distances", distances),
                            ("ambiguity_mask", ambiguous), ("outside_domain_mask", outside),
                            ("reference_state_ids", reference), ("observed_transition_edges", observed),
                            ("off_network_transition_edges", off), ("assigned_fraction", assigned_fraction),
                            ("mismatch_fraction", mismatch), ("unresolved_fraction", unresolved_fraction),
                            ("status", status), ("diagnostics", diagnostics), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": TRANSFER_APPLICATION_SCHEMA, "application_id": self.application_id,
                "model_basis_signature": self.model_basis_signature, "domain": self.domain.to_dict(),
                "assigned_state_ids": self.assigned_state_ids.tolist(),
                "minimum_distances": self.minimum_distances.tolist(),
                "ambiguity_mask": self.ambiguity_mask.tolist(), "outside_domain_mask": self.outside_domain_mask.tolist(),
                "reference_state_ids": None if self.reference_state_ids is None else self.reference_state_ids.tolist(),
                "observed_transition_edges": self.observed_transition_edges.tolist(),
                "off_network_transition_edges": self.off_network_transition_edges.tolist(),
                "assigned_fraction": self.assigned_fraction, "mismatch_fraction": self.mismatch_fraction,
                "unresolved_fraction": self.unresolved_fraction, "status": self.status.value,
                "diagnostics": list(self.diagnostics), "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "TransferApplicationResult":
        if p.get("schema") != TRANSFER_APPLICATION_SCHEMA:
            raise ObservedNetworkSerializationError("Unsupported transfer-application schema.")
        return cls(int(p["application_id"]), str(p["model_basis_signature"]),
                   TransferDomainMetadata.from_dict(p["domain"]), np.asarray(p["assigned_state_ids"], dtype=np.int32),
                   np.asarray(p["minimum_distances"], dtype=float), np.asarray(p["ambiguity_mask"], dtype=bool),
                   np.asarray(p["outside_domain_mask"], dtype=bool),
                   None if p.get("reference_state_ids") is None else np.asarray(p["reference_state_ids"], dtype=np.int32),
                   np.asarray(p["observed_transition_edges"], dtype=np.int64).reshape((-1, 5)),
                   np.asarray(p["off_network_transition_edges"], dtype=np.int64).reshape((-1, 5)),
                   float(p["assigned_fraction"]), p.get("mismatch_fraction"), float(p["unresolved_fraction"]),
                   TransferValidationStatus(p["status"]), tuple(p.get("diagnostics", ())),
                   str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class ObservedNetworkModelCatalog:
    options: ObservedNetworkOptions
    resources: ObservedNetworkResourcePolicy
    validated_catalog_signatures: tuple[str, ...]
    transition_path_catalog_signature: str
    registration_compatibility_signature: str
    nodes: tuple[ObservedNetworkNode, ...]
    observed_edges: tuple[ObservedNetworkEdge, ...]
    unobserved_structural_edges: tuple[StructuralNetworkEdge, ...]
    site_complexes: tuple[SiteComplexSummary, ...]
    symmetry_orbits: tuple[SymmetryOrbitSummary, ...]
    semantic_classes: tuple[SemanticClassSummary, ...]
    compact_models: tuple[CompactTransferredStateModel, ...]
    transfer_applications: tuple[TransferApplicationResult, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    model_basis_signature: str = ""
    signature: str = ""

    def __post_init__(self) -> None:
        validated = tuple(_sha(v, "validated catalog signature") for v in self.validated_catalog_signatures)
        path = _sha(self.transition_path_catalog_signature, "transition_path_catalog_signature")
        compatibility = _sha(self.registration_compatibility_signature, "registration_compatibility_signature")
        nodes = tuple(self.nodes); edges = tuple(self.observed_edges); structural = tuple(self.unobserved_structural_edges)
        complexes = tuple(self.site_complexes); orbits = tuple(self.symmetry_orbits)
        classes = tuple(self.semantic_classes); models = tuple(self.compact_models); applications = tuple(self.transfer_applications)
        if tuple(v.node_id for v in nodes) != tuple(range(len(nodes))):
            raise ObservedNetworkInputError("Observed-network nodes must use dense ordered IDs.")
        if tuple(v.edge_id for v in edges) != tuple(range(len(edges))):
            raise ObservedNetworkInputError("Observed-network edges must use dense ordered IDs.")
        if tuple(v.summary_id for v in complexes) != tuple(range(len(complexes))) or tuple(v.summary_id for v in orbits) != tuple(range(len(orbits))):
            raise ObservedNetworkInputError("Site-complex and orbit summaries must use dense ordered IDs.")
        if tuple(v.canonical_state_id for v in models) != tuple(sorted({v.canonical_state_id for v in nodes})):
            raise ObservedNetworkInputError("Compact models must cover each canonical state exactly once.")
        if tuple(v.application_id for v in applications) != tuple(range(len(applications))):
            raise ObservedNetworkInputError("Transfer applications must use dense ordered IDs.")
        metadata = _freeze(dict(self.metadata))
        basis_payload = {"stage": OBSERVED_NETWORK_STAGE, "validated_catalog_signatures": list(validated),
                         "transition_path_catalog_signature": path,
                         "registration_compatibility_signature": compatibility,
                         "node_signatures": [v.signature for v in nodes], "edge_signatures": [v.signature for v in edges],
                         "structural_edge_signatures": [v.signature for v in structural],
                         "site_complex_signatures": [v.signature for v in complexes],
                         "symmetry_orbit_signatures": [v.signature for v in orbits],
                         "semantic_class_signatures": [v.signature for v in classes],
                         "compact_model_signatures": [v.signature for v in models]}
        basis = _digest(basis_payload)
        if self.model_basis_signature and self.model_basis_signature != basis:
            raise ObservedNetworkInputError("Observed-network model-basis signature is inconsistent.")
        if any(v.model_basis_signature != basis for v in applications):
            raise ObservedNetworkInputError("A transfer application belongs to another model basis.")
        payload = {"schema": OBSERVED_NETWORK_CATALOG_SCHEMA, "options_signature": self.options.signature,
                   "resources_signature": self.resources.signature, "model_basis_signature": basis,
                   "transfer_application_signatures": [v.signature for v in applications],
                   "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise ObservedNetworkInputError("Observed-network catalog signature is inconsistent.")
        for name, value in (("validated_catalog_signatures", validated),
                            ("transition_path_catalog_signature", path),
                            ("registration_compatibility_signature", compatibility), ("nodes", nodes),
                            ("observed_edges", edges), ("unobserved_structural_edges", structural),
                            ("site_complexes", complexes), ("symmetry_orbits", orbits),
                            ("semantic_classes", classes), ("compact_models", models),
                            ("transfer_applications", applications), ("metadata", metadata),
                            ("model_basis_signature", basis), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": OBSERVED_NETWORK_CATALOG_SCHEMA, "options": self.options.to_dict(),
                "resources": self.resources.to_dict(),
                "validated_catalog_signatures": list(self.validated_catalog_signatures),
                "transition_path_catalog_signature": self.transition_path_catalog_signature,
                "registration_compatibility_signature": self.registration_compatibility_signature,
                "nodes": [v.to_dict() for v in self.nodes], "observed_edges": [v.to_dict() for v in self.observed_edges],
                "unobserved_structural_edges": [v.to_dict() for v in self.unobserved_structural_edges],
                "site_complexes": [v.to_dict() for v in self.site_complexes],
                "symmetry_orbits": [v.to_dict() for v in self.symmetry_orbits],
                "semantic_classes": [v.to_dict() for v in self.semantic_classes],
                "compact_models": [v.to_dict() for v in self.compact_models],
                "transfer_applications": [v.to_dict() for v in self.transfer_applications],
                "metadata": _json_value(self.metadata), "model_basis_signature": self.model_basis_signature,
                "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "ObservedNetworkModelCatalog":
        if p.get("schema") != OBSERVED_NETWORK_CATALOG_SCHEMA:
            raise ObservedNetworkSerializationError("Unsupported observed-network catalog schema.")
        return cls(ObservedNetworkOptions.from_dict(p["options"]), ObservedNetworkResourcePolicy.from_dict(p["resources"]),
                   tuple(p["validated_catalog_signatures"]), str(p["transition_path_catalog_signature"]),
                   str(p["registration_compatibility_signature"]),
                   tuple(ObservedNetworkNode.from_dict(v) for v in p["nodes"]),
                   tuple(ObservedNetworkEdge.from_dict(v) for v in p["observed_edges"]),
                   tuple(StructuralNetworkEdge.from_dict(v) for v in p["unobserved_structural_edges"]),
                   tuple(SiteComplexSummary.from_dict(v) for v in p["site_complexes"]),
                   tuple(SymmetryOrbitSummary.from_dict(v) for v in p["symmetry_orbits"]),
                   tuple(SemanticClassSummary.from_dict(v) for v in p["semantic_classes"]),
                   tuple(CompactTransferredStateModel.from_dict(v) for v in p["compact_models"]),
                   tuple(TransferApplicationResult.from_dict(v) for v in p.get("transfer_applications", ())),
                   dict(p.get("metadata", {})), str(p.get("model_basis_signature", "")), str(p.get("signature", "")))


def _circular_anchor(anchors: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    phases = 2.0 * np.pi * anchors
    mean_complex = np.mean(np.exp(1j * phases), axis=0)
    concentrations = np.abs(mean_complex)
    angles = np.mod(np.angle(mean_complex), 2.0 * np.pi)
    centers = angles / (2.0 * np.pi)
    centers[concentrations <= 1e-15] = anchors[0, concentrations <= 1e-15]
    return centers.astype(np.float64), concentrations.astype(np.float64)


def prepare_observed_network_model(
    validated_catalogs: Sequence[ValidatedFrozenCatalog] | ValidatedFrozenCatalog,
    transition_paths: ObservedTransitionPathCatalog,
    *,
    structural_edges: Sequence[StructuralNetworkEdge] = (),
    semantic_class_labels: Mapping[tuple[int, int], str] | None = None,
    options: ObservedNetworkOptions | None = None,
    resources: ObservedNetworkResourcePolicy | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ObservedNetworkModelCatalog:
    """Build the E7 observed network and compact transfer-model basis."""
    catalogs = (validated_catalogs,) if isinstance(validated_catalogs, ValidatedFrozenCatalog) else tuple(validated_catalogs)
    options = options or ObservedNetworkOptions(); resources = resources or ObservedNetworkResourcePolicy()
    if not catalogs or len(catalogs) != len(transition_paths.member_sample_catalog_signatures):
        raise ObservedNetworkInputError("Validated catalogs must align one-to-one with path-catalog members.")
    for member, (catalog, sample_sig) in enumerate(zip(catalogs, transition_paths.member_sample_catalog_signatures, strict=True)):
        if catalog.sample_catalog_signature != sample_sig:
            raise ObservedNetworkInputError(f"Validated catalog member {member} belongs to another sample catalog.")
    structural_edges = tuple(structural_edges)
    if len(structural_edges) > resources.max_structural_edges:
        raise ObservedNetworkResourceError("structural edges exceed max_structural_edges")
    structural_by_key: dict[tuple[int, int, int, int, int], list[StructuralNetworkEdge]] = defaultdict(list)
    for edge in structural_edges:
        structural_by_key[edge.key].append(edge)
    labels = {} if semantic_class_labels is None else {(int(m), int(s)): str(v) for (m, s), v in semantic_class_labels.items()}

    node_lookup: dict[tuple[int, int], int] = {}
    nodes: list[ObservedNetworkNode] = []
    for member, catalog in enumerate(catalogs):
        complexes_for_state: dict[int, list[int]] = defaultdict(list)
        for complex_ in catalog.structural_complexes:
            for state_id in complex_.member_state_ids: complexes_for_state[int(state_id)].append(complex_.complex_id)
        orbits_for_state: dict[int, list[int]] = defaultdict(list)
        for orbit in catalog.symmetry_orbits:
            for state_id in orbit.candidate.member_state_ids: orbits_for_state[int(state_id)].append(orbit.orbit_id)
        for state in catalog.states:
            canonical = transition_paths.registration_compatibility.canonical_state(member, state.state_id)
            association = state.structural_association
            identities = tuple(v.persistent_identity for v in association.candidates)
            primary = None if association.primary is None else association.primary.persistent_identity
            node_id = len(nodes); node_lookup[(member, state.state_id)] = node_id
            nodes.append(ObservedNetworkNode(
                node_id, member, state.state_id, canonical, state.signature, state.anchor_fractional,
                state.geometry.value, state.evidence.overall.value, state.evidence.final_validation.value,
                np.asarray(sorted(complexes_for_state[state.state_id]), dtype=np.int32),
                np.asarray(sorted(orbits_for_state[state.state_id]), dtype=np.int32), identities, primary,
                labels.get((member, state.state_id)),
            ))
    if len(nodes) > resources.max_state_instances:
        raise ObservedNetworkResourceError("state instances exceed max_state_instances")

    observed_groups: dict[tuple[int, int, int, int, int], list[Any]] = defaultdict(list)
    for ensemble in transition_paths.ensembles:
        if ensemble.event_ids.size < options.minimum_events_for_observed_edge:
            continue
        observed_groups[_edge_key(ensemble.source_state_id, ensemble.target_state_id,
                                  ensemble.periodic_translation)].append(ensemble)
    if len(observed_groups) > resources.max_observed_edges:
        raise ObservedNetworkResourceError("observed edges exceed max_observed_edges")
    observed_edges: list[ObservedNetworkEdge] = []
    for edge_id, key in enumerate(sorted(observed_groups)):
        ensembles = observed_groups[key]
        event_ids = np.unique(np.concatenate([v.event_ids for v in ensembles])).astype(np.int64)
        durations = np.asarray([event.minimum_resolvable_duration for event in transition_paths.events
                               if event.event_id in set(int(x) for x in event_ids)], dtype=float)
        structural = structural_by_key.get(key, [])
        comparison = (StructuralEdgeComparisonStatus.OBSERVED_AND_STRUCTURAL if structural else
                      (StructuralEdgeComparisonStatus.OBSERVED_OFF_STRUCTURAL_NETWORK if structural_edges else
                       StructuralEdgeComparisonStatus.STRUCTURAL_COMPARISON_UNAVAILABLE))
        primary_ids = sorted({int(v.primary_structural_id) for v in ensembles if v.primary_structural_id is not None})
        observed_edges.append(ObservedNetworkEdge(
            edge_id, key[0], key[1], np.asarray(key[2:], dtype=np.int64),
            np.asarray([v.ensemble_id for v in ensembles], dtype=np.int64), event_ids, int(event_ids.size),
            tuple(v.status.value for v in ensembles), float(np.mean(durations)) if durations.size else 0.0,
            float(np.std(durations)) if durations.size else 0.0, comparison,
            tuple(v.signature for v in structural), np.asarray(primary_ids, dtype=np.int32),
        ))
    observed_keys = set(observed_groups)
    unobserved_structural = tuple(edge for edge in structural_edges if edge.key not in observed_keys)

    complex_summaries: list[SiteComplexSummary] = []
    orbit_summaries: list[SymmetryOrbitSummary] = []
    for member, catalog in enumerate(catalogs):
        for complex_ in catalog.structural_complexes:
            ids = np.asarray([node_lookup[(member, int(v))] for v in complex_.member_state_ids], dtype=np.int64)
            states = np.asarray([nodes[int(v)].canonical_state_id for v in ids], dtype=np.int32)
            complex_summaries.append(SiteComplexSummary(
                len(complex_summaries), member, complex_.complex_id, complex_.signature,
                complex_.kind.value, complex_.persistent_identity, ids, states, complex_.preliminary,
            ))
        for orbit in catalog.symmetry_orbits:
            ids = np.asarray([node_lookup[(member, int(v))] for v in orbit.candidate.member_state_ids], dtype=np.int64)
            states = np.asarray([nodes[int(v)].canonical_state_id for v in ids], dtype=np.int32)
            orbit_summaries.append(SymmetryOrbitSummary(
                len(orbit_summaries), member, orbit.orbit_id, orbit.signature, orbit.candidate.label,
                orbit.status.value, ids, states, orbit.augmentation_performed,
            ))

    class_groups: dict[str, list[ObservedNetworkNode]] = defaultdict(list)
    for node in nodes:
        if node.semantic_class is not None: class_groups[node.semantic_class].append(node)
    semantic_summaries = tuple(SemanticClassSummary(
        label, np.asarray([v.node_id for v in values], dtype=np.int64),
        np.asarray([v.canonical_state_id for v in values], dtype=np.int32),
    ) for label, values in sorted(class_groups.items()))

    state_groups: dict[int, list[ObservedNetworkNode]] = defaultdict(list)
    state_records: dict[tuple[int, int], Any] = {}
    for member, catalog in enumerate(catalogs):
        for state in catalog.states: state_records[(member, state.state_id)] = state
    for node in nodes: state_groups[node.canonical_state_id].append(node)
    models: list[CompactTransferredStateModel] = []
    for canonical, members in sorted(state_groups.items()):
        anchors = np.asarray([v.anchor_fractional for v in members], dtype=float)
        center, concentration = _circular_anchor(anchors)
        records = [state_records[(v.member_index, v.local_state_id)] for v in members]
        basin = np.asarray([v.basin_probability for v in records], dtype=float)
        occupancy = np.asarray([v.mean_occupancy for v in records], dtype=float)
        identities = tuple(sorted({item for v in members for item in v.structural_identities}))
        classes = tuple(sorted({v.semantic_class for v in members if v.semantic_class is not None}))
        if len(members) == 1: status = CompactModelStatus.SINGLE_INSTANCE
        elif float(np.min(concentration)) < options.minimum_anchor_concentration:
            status = CompactModelStatus.PERIODIC_ANCHOR_AMBIGUOUS
        else: status = CompactModelStatus.RESOLVED
        models.append(CompactTransferredStateModel(
            canonical, np.asarray([v.node_id for v in members], dtype=np.int64), anchors, center, concentration,
            float(np.mean(basin)), float(np.std(basin)), float(np.mean(occupancy)), float(np.std(occupancy)),
            identities, classes, status,
        ))
    return ObservedNetworkModelCatalog(
        options, resources, tuple(v.signature for v in catalogs), transition_paths.signature,
        transition_paths.registration_compatibility.signature, tuple(nodes), tuple(observed_edges),
        unobserved_structural, tuple(complex_summaries), tuple(orbit_summaries), semantic_summaries,
        tuple(models), (), metadata={
            "state_instances_merged": False,
            "structural_edges_create_observed_edges": False,
            "rates_inferred": False,
            "structural_unobserved_edge_count": len(unobserved_structural),
            "observed_off_structural_edge_count": sum(v.structural_comparison is StructuralEdgeComparisonStatus.OBSERVED_OFF_STRUCTURAL_NETWORK for v in observed_edges),
            "registration_signatures": tuple(transition_paths.registration_compatibility.member_registration_signatures),
            "registration_group_signatures": (() if transition_paths.registration_compatibility.registration_group_signature is None
                                               else (transition_paths.registration_compatibility.registration_group_signature,)),
            **({} if metadata is None else dict(metadata)),
        },
    )


def apply_observed_network_model(
    catalog: ObservedNetworkModelCatalog,
    registered_fractional_positions: Any,
    domain: TransferDomainMetadata,
    *,
    reference_state_ids: Any | None = None,
    observed_transition_edges: Sequence[Sequence[int]] = (),
    maximum_assignment_distance: float | None = None,
    ambiguity_distance: float | None = None,
    mismatch_tolerance: float | None = None,
    application_id: int | None = None,
) -> TransferApplicationResult:
    """Apply compact E7 anchors to untouched validation or an external domain.

    Assignment is fail-closed: no state is assigned outside the declared radius,
    and close competitors remain ambiguous.  The function validates catalog
    reproduction; it does not refit anchors or add off-network states/edges.
    """
    positions = _readonly(registered_fractional_positions, dtype=np.float64, ndim=2,
                          name="registered_fractional_positions")
    if positions.shape[1:] != (3,):
        raise ObservedNetworkInputError("registered_fractional_positions must have shape (n, 3).")
    if positions.shape[0] > catalog.resources.max_transfer_samples:
        raise ObservedNetworkResourceError("transfer samples exceed max_transfer_samples")
    application = len(catalog.transfer_applications) if application_id is None else int(application_id)
    radius = catalog.options.default_transfer_radius if maximum_assignment_distance is None else _nonnegative(maximum_assignment_distance, "maximum_assignment_distance")
    ambiguity = catalog.options.default_ambiguity_distance if ambiguity_distance is None else _nonnegative(ambiguity_distance, "ambiguity_distance")
    tolerance = catalog.options.default_mismatch_tolerance if mismatch_tolerance is None else _nonnegative(mismatch_tolerance, "mismatch_tolerance")
    if tolerance > 1.0: raise ObservedNetworkInputError("mismatch_tolerance must not exceed one.")
    # The compatibility signature itself is opaque, so accept a declared group when one exists in domain,
    # or a registration signature explicitly retained in model metadata.  prepare_observed_network_model
    # records the source member signatures in immutable nodes, not raw registration details.
    source_groups = set(catalog.metadata.get("registration_group_signatures", ()))
    source_registrations = set(catalog.metadata.get("registration_signatures", ()))
    compatible: bool
    if source_groups or source_registrations:
        compatible = ((domain.registration_group_signature is not None and domain.registration_group_signature in source_groups)
                      or (domain.registration_signature is not None and domain.registration_signature in source_registrations))
    else:
        compatible = domain.registration_signature is not None or domain.registration_group_signature is not None
    n = positions.shape[0]
    assigned = np.full(n, -1, dtype=np.int32); distances = np.full(n, radius, dtype=float)
    ambiguous_mask = np.zeros(n, dtype=bool); outside = np.zeros(n, dtype=bool)
    diagnostics: list[str] = []
    if not compatible:
        outside[:] = True; distances[:] = 0.0
        status = TransferValidationStatus.DOMAIN_MISMATCH
    else:
        metric = AnalysisGeometryMetric(matrix=tuple(tuple(float(x) for x in row) for row in domain.analysis_metric_covariant),
                                        units=f"{domain.length_units}^2", coordinate_frame=domain.coordinate_frame)
        for i, point in enumerate(positions):
            ranked: list[tuple[float, int]] = []
            for model in catalog.compact_models:
                best = min(closest_periodic_image(point - anchor, cell=np.eye(3), metric=metric).distance
                           for anchor in model.instance_anchors_fractional)
                ranked.append((float(best), model.canonical_state_id))
            ranked.sort(key=lambda v: (v[0], v[1]))
            distances[i] = ranked[0][0]
            if ranked[0][0] > radius:
                outside[i] = True
            elif len(ranked) > 1 and ranked[1][0] - ranked[0][0] <= ambiguity:
                ambiguous_mask[i] = True; assigned[i] = -2
            else:
                assigned[i] = ranked[0][1]
        reference = None if reference_state_ids is None else _readonly(reference_state_ids, dtype=np.int32, ndim=1,
                                                                       name="reference_state_ids", shape=(n,))
        observed = np.asarray([_edge_key(int(row[0]), int(row[1]), row[2:5]) for row in observed_transition_edges], dtype=np.int64).reshape((-1, 5))
        model_keys = {v.key for v in catalog.observed_edges}
        off = np.asarray([row for row in observed if tuple(int(v) for v in row) not in model_keys], dtype=np.int64).reshape((-1, 5))
        assigned_fraction = float(np.mean(assigned >= 0)) if n else 0.0
        unresolved_fraction = float(np.mean(assigned < 0)) if n else 0.0
        if reference is None:
            mismatch = None
            if off.size: status = TransferValidationStatus.OFF_NETWORK_EVENTS
            elif n == 0: status = TransferValidationStatus.INSUFFICIENT_EVIDENCE
            else: status = TransferValidationStatus.REFERENCE_UNAVAILABLE
        else:
            reference_mask = reference >= 0
            mismatch = None if not np.any(reference_mask) else float(np.mean(assigned[reference_mask] != reference[reference_mask]))
            if off.size: status = TransferValidationStatus.OFF_NETWORK_EVENTS
            elif mismatch is None: status = TransferValidationStatus.INSUFFICIENT_EVIDENCE
            elif mismatch <= tolerance: status = TransferValidationStatus.REPRODUCED_WITHIN_UNCERTAINTY
            elif mismatch <= min(1.0, 2.0 * tolerance) or (0.0 < unresolved_fraction <= tolerance):
                status = TransferValidationStatus.PARTIAL_REPRODUCTION
            else: status = TransferValidationStatus.FAILED_TRANSFER
        return TransferApplicationResult(application, catalog.model_basis_signature, domain, assigned, distances,
                                         ambiguous_mask, outside, reference, observed, off, assigned_fraction,
                                         mismatch, unresolved_fraction, status, tuple(diagnostics))
    reference = None if reference_state_ids is None else _readonly(reference_state_ids, dtype=np.int32, ndim=1,
                                                                   name="reference_state_ids", shape=(n,))
    observed = np.asarray([_edge_key(int(row[0]), int(row[1]), row[2:5]) for row in observed_transition_edges], dtype=np.int64).reshape((-1, 5))
    return TransferApplicationResult(application, catalog.model_basis_signature, domain, assigned, distances,
                                     ambiguous_mask, outside, reference, observed, observed.copy(), 0.0, None,
                                     1.0 if n else 0.0, status, ("registration_domain_incompatible",))


def attach_transfer_applications(
    catalog: ObservedNetworkModelCatalog,
    applications: Sequence[TransferApplicationResult],
) -> ObservedNetworkModelCatalog:
    combined = tuple(catalog.transfer_applications) + tuple(applications)
    if len(combined) > catalog.resources.max_transfer_applications:
        raise ObservedNetworkResourceError("transfer applications exceed max_transfer_applications")
    normalized = tuple(replace(v, application_id=i, signature="") if v.application_id != i else v
                       for i, v in enumerate(combined))
    return replace(catalog, transfer_applications=normalized, signature="")


__all__ = [
    "OBSERVED_NETWORK_STAGE", "OBSERVED_NETWORK_OPTIONS_SCHEMA", "OBSERVED_NETWORK_RESOURCES_SCHEMA",
    "STRUCTURAL_EDGE_SCHEMA", "OBSERVED_NODE_SCHEMA", "OBSERVED_EDGE_SCHEMA",
    "SITE_COMPLEX_SUMMARY_SCHEMA", "SYMMETRY_ORBIT_SUMMARY_SCHEMA", "SEMANTIC_CLASS_SUMMARY_SCHEMA",
    "COMPACT_STATE_MODEL_SCHEMA", "TRANSFER_DOMAIN_SCHEMA", "TRANSFER_APPLICATION_SCHEMA",
    "OBSERVED_NETWORK_CATALOG_SCHEMA", "ObservedNetworkError", "ObservedNetworkInputError",
    "ObservedNetworkResourceError", "ObservedNetworkSerializationError", "StructuralEdgeComparisonStatus",
    "CompactModelStatus", "TransferApplicationKind", "TransferValidationStatus", "ObservedNetworkOptions",
    "ObservedNetworkResourcePolicy", "StructuralNetworkEdge", "ObservedNetworkNode", "ObservedNetworkEdge",
    "SiteComplexSummary", "SymmetryOrbitSummary", "SemanticClassSummary", "CompactTransferredStateModel",
    "TransferDomainMetadata", "TransferApplicationResult", "ObservedNetworkModelCatalog",
    "prepare_observed_network_model", "apply_observed_network_model", "attach_transfer_applications",
]
