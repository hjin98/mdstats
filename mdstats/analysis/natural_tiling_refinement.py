"""Stage-10C primitive-ring-bound rebuild and stable-key comparison.

Increasing the primitive-ring bound is a hard orchestration boundary.  This
module never incrementally patches a source-bound downstream result.  A caller
supplies one complete rebuild per requested bound; mdstats validates the source
bindings, reduces every scientific result to a bound-independent stable record,
and compares consecutive rebuilds without trusting dense local IDs or
catalog-bound digests.

The rebuild discipline and stable comparison model are project-specific.  The
natural-tiling eligibility rules remain those of Blatov, Delgado-Friedrichs,
O'Keeffe, and Proserpio (2007).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from numbers import Integral
from typing import Any, Callable, Mapping, Sequence

from .face_candidates import (
    FaceCompatibilityConstraintSystem,
    FacePlacementCertificate,
    FacePlacementStatus,
)
from .natural_tiling import (
    CandidateEligibility,
    NaturalTilingCatalog,
    NaturalTilingOutcomeKind,
    build_natural_tiling_catalog,
)
from .natural_tiling_search import NaturalTilingSearchResult, NaturalTilingSearchStatus
from .periodic_cell_complex import PeriodicCellComplex, PeriodicPartitionCertificate
from .primitive_ring import PrimitiveRingKey
from .primitive_ring_index import PrimitiveRingIndex
from .primitive_ring_symmetry import PrimitiveRingSymmetryIndex
from .ring_strength import RingStrengthCatalog, RingStrengthStatus

CANONICAL_BOUND_REFINEMENT_SCHEMA = "mdstats.natural-tiling-bound-refinement.v1"
BOUND_REFINEMENT_DIGEST_ALGORITHM = "sha256-canonical-json-v1"


class NaturalTilingRefinementError(ValueError):
    """Base exception for Stage-10C refinement orchestration."""


class NaturalTilingRefinementInputError(NaturalTilingRefinementError):
    """Raised when one rebuild is incomplete, misbound, or noncanonical."""


class NaturalTilingRefinementResourceError(NaturalTilingRefinementError):
    """Raised transactionally before the requested refinement family is built."""


class NaturalTilingRefinementSerializationError(NaturalTilingRefinementError):
    """Raised when a persistent report fails canonical reconstruction."""


class RefinementSnapshotStatus(str, Enum):
    COMPLETE = "complete"
    UNRESOLVED = "unresolved"


class RefinementTransitionStatus(str, Enum):
    STABLE = "stable"
    CHANGED = "changed"
    UNRESOLVED = "unresolved"
    INVALID = "invalid"


class RefinementChangeKind(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


class RefinementRecordCategory(str, Enum):
    RING = "ring"
    RING_ORBIT = "ring-orbit"
    STRENGTH = "strength"
    FACE = "face"
    COMPATIBILITY = "compatibility"
    MASTER_COMPLEX = "master-complex"
    MASTER_PARTITION = "master-partition"
    SEARCH = "search"
    TILING = "tiling"
    ESSENTIAL_RING = "essential-ring"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha(value: object, *, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise NaturalTilingRefinementInputError(f"{name} must be a SHA-256 digest.")
    return value


def _positive(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) <= 0:
        raise NaturalTilingRefinementInputError(f"{name} must be a positive integer.")
    return int(value)


def _normalize_payload(
    value: Any,
    *,
    replacements: Mapping[str, str] | None = None,
    drop_keys: frozenset[str] = frozenset(),
) -> Any:
    replacements = replacements or {}
    if isinstance(value, Mapping):
        return {
            str(key): _normalize_payload(item, replacements=replacements, drop_keys=drop_keys)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in drop_keys
        }
    if isinstance(value, (list, tuple)):
        return [_normalize_payload(item, replacements=replacements, drop_keys=drop_keys) for item in value]
    if isinstance(value, str):
        return replacements.get(value, value)
    return value


_VOLATILE_SOURCE_KEYS = frozenset(
    {
        "digest",
        "evidence_digest",
        "primitive_ring_catalog_digest",
        "periodic_cell_complex_digest",
        "master_cell_complex_digest",
        "master_partition_certificate_digest",
        "strength_catalog_digest",
        "compatibility_system_digest",
        "symmetry_action_digest",
        "partition_certificate_digest",
        "topology_graph_digest",
    }
)


def _ring_payload(key: PrimitiveRingKey) -> dict[str, Any]:
    return key.to_dict()


def _face_identity(certificate: FacePlacementCertificate) -> dict[str, Any]:
    placement = certificate.face_placement
    return {
        "periodic_net_embedding_digest": placement.periodic_net_embedding_digest,
        "ring_key": _ring_payload(placement.ring_placement.ring_key),
        "image_shift": list(placement.ring_placement.image_shift),
        "orientation": placement.orientation,
    }


def _face_key(certificate: FacePlacementCertificate) -> str:
    return _digest({"category": RefinementRecordCategory.FACE.value, "identity": _face_identity(certificate)})


def _complex_identity(complex_: PeriodicCellComplex) -> dict[str, Any]:
    face_keys = tuple(
        _digest(
            {
                "periodic_net_embedding_digest": face.periodic_net_embedding_digest,
                "ring_key": _ring_payload(face.ring_placement.ring_key),
                "image_shift": list(face.ring_placement.image_shift),
                "orientation": face.orientation,
            }
        )
        for face in complex_.face_placements
    )
    boundary_2 = sorted(
        (
            face_keys[index],
            [
                {
                    "edge_index": term.cell_index,
                    "image_shift": list(term.image_shift),
                    "coefficient": term.coefficient,
                }
                for term in column
            ],
        )
        for index, column in enumerate(complex_.boundary_2.columns)
    )
    shells = []
    for shell in complex_.tile_shells:
        shells.append(
            {
                "label": shell.label,
                "face_incidences": sorted(
                    (
                        face_keys[term.cell_index],
                        list(term.image_shift),
                        term.coefficient,
                    )
                    for term in shell.face_incidences
                ),
            }
        )
    return {
        "periodic_net_view_digest": complex_.periodic_net_view_digest,
        "periodic_net_embedding_digest": complex_.periodic_net_embedding_digest,
        "cell_counts": list(complex_.cell_counts),
        "boundary_1": _normalize_payload(complex_.boundary_1.to_dict(), drop_keys=frozenset({"digest"})),
        "boundary_2_by_face": boundary_2,
        "tile_shells": sorted(shells, key=_canonical_json),
    }


def _complex_key(complex_: PeriodicCellComplex) -> str:
    return _digest({"category": RefinementRecordCategory.MASTER_COMPLEX.value, "identity": _complex_identity(complex_)})


def _partition_identity(
    partition: PeriodicPartitionCertificate,
    complex_key_by_digest: Mapping[str, str],
) -> dict[str, Any]:
    normalized = _normalize_payload(
        partition.to_dict(),
        replacements=complex_key_by_digest,
        drop_keys=_VOLATILE_SOURCE_KEYS | frozenset({"periodic_net_embedding_digest", "overlap_candidate_set_digest"}),
    )
    return {
        "scientific_complex_key": complex_key_by_digest[partition.periodic_cell_complex_digest],
        "exact_auxiliary_partition": normalized,
    }


def _record(
    category: RefinementRecordCategory,
    identity: Any,
    state: Any,
) -> "StableRefinementRecord":
    return StableRefinementRecord(category, _canonical_json(identity), _canonical_json(state))


@dataclass(frozen=True, slots=True)
class NaturalTilingRefinementResources:
    max_bounds: int = 16
    max_records_per_snapshot: int = 1_000_000
    max_total_changes: int = 2_000_000

    def __post_init__(self) -> None:
        for name in ("max_bounds", "max_records_per_snapshot", "max_total_changes"):
            object.__setattr__(self, name, _positive(getattr(self, name), name=name))


@dataclass(frozen=True, slots=True)
class PrimitiveBoundBuild:
    """Transient complete rebuild products for one primitive-ring bound."""

    primitive_ring_bound: int
    periodic_net_view_digest: str
    periodic_net_embedding_digest: str
    ring_index: PrimitiveRingIndex = field(repr=False, compare=False)
    ring_symmetry: PrimitiveRingSymmetryIndex = field(repr=False, compare=False)
    strength_catalog: RingStrengthCatalog = field(repr=False, compare=False)
    face_certificates: tuple[FacePlacementCertificate, ...] = field(default=(), repr=False, compare=False)
    compatibility_systems: tuple[FaceCompatibilityConstraintSystem, ...] = field(default=(), repr=False, compare=False)
    master_complexes: tuple[PeriodicCellComplex, ...] = field(default=(), repr=False, compare=False)
    master_partitions: tuple[PeriodicPartitionCertificate, ...] = field(default=(), repr=False, compare=False)
    search_results: tuple[NaturalTilingSearchResult, ...] = field(default=(), repr=False, compare=False)
    catalog: NaturalTilingCatalog | None = field(default=None, repr=False, compare=False)
    unresolved_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        bound = _positive(self.primitive_ring_bound, name="primitive_ring_bound")
        _sha(self.periodic_net_view_digest, name="periodic_net_view_digest")
        _sha(self.periodic_net_embedding_digest, name="periodic_net_embedding_digest")
        if not isinstance(self.ring_index, PrimitiveRingIndex):
            raise NaturalTilingRefinementInputError("ring_index must be a PrimitiveRingIndex.")
        catalog = self.ring_index.catalog
        if catalog.options.max_ring_size != bound:
            raise NaturalTilingRefinementInputError("The primitive-ring options bound does not match primitive_ring_bound.")
        if catalog.complete_for_ring_sizes_up_to > bound:
            raise NaturalTilingRefinementInputError("Primitive-ring completeness cannot exceed the requested bound.")
        if not isinstance(self.ring_symmetry, PrimitiveRingSymmetryIndex):
            raise NaturalTilingRefinementInputError("ring_symmetry must be a PrimitiveRingSymmetryIndex.")
        if (
            self.ring_symmetry.periodic_net_view_digest != self.periodic_net_view_digest
            or self.ring_symmetry.primitive_ring_catalog_digest != catalog.digest
            or self.ring_symmetry.ring_keys != self.ring_index.ring_keys
        ):
            raise NaturalTilingRefinementInputError("Ring symmetry is not rebuilt from the current bound catalog.")
        if not isinstance(self.strength_catalog, RingStrengthCatalog) or (
            self.strength_catalog.primitive_ring_catalog_digest != catalog.digest
            or self.strength_catalog.topology_graph_digest != self.ring_index.topology_graph_digest
        ):
            raise NaturalTilingRefinementInputError("Strength catalog is not rebuilt from the current bound catalog.")

        certificates = tuple(self.face_certificates)
        if any(not isinstance(value, FacePlacementCertificate) for value in certificates):
            raise NaturalTilingRefinementInputError("face_certificates contain an invalid record.")
        if len({value.face_placement.digest for value in certificates}) != len(certificates):
            raise NaturalTilingRefinementInputError("Face placements must be unique within one bound rebuild.")
        if any(
            value.periodic_net_view_digest != self.periodic_net_view_digest
            or value.periodic_net_embedding_digest != self.periodic_net_embedding_digest
            or value.primitive_ring_catalog_digest != catalog.digest
            for value in certificates
        ):
            raise NaturalTilingRefinementInputError("A face certificate was reused from another source bound.")

        systems = tuple(self.compatibility_systems)
        complexes = tuple(self.master_complexes)
        partitions = tuple(self.master_partitions)
        searches = tuple(self.search_results)
        if any(not isinstance(value, FaceCompatibilityConstraintSystem) for value in systems):
            raise NaturalTilingRefinementInputError("compatibility_systems contain an invalid record.")
        if any(not isinstance(value, PeriodicCellComplex) for value in complexes):
            raise NaturalTilingRefinementInputError("master_complexes contain an invalid record.")
        if any(not isinstance(value, PeriodicPartitionCertificate) for value in partitions):
            raise NaturalTilingRefinementInputError("master_partitions contain an invalid record.")
        if any(not isinstance(value, NaturalTilingSearchResult) for value in searches):
            raise NaturalTilingRefinementInputError("search_results contain an invalid record.")
        if any(
            value.periodic_net_view_digest != self.periodic_net_view_digest
            or value.periodic_net_embedding_digest != self.periodic_net_embedding_digest
            or value.primitive_ring_catalog_digest != catalog.digest
            for value in complexes
        ):
            raise NaturalTilingRefinementInputError("A master complex was reused from another source bound.")
        complex_digests = {value.digest for value in complexes}
        partition_digests = {value.digest for value in partitions}
        system_digests = {value.digest for value in systems}
        if any(
            value.periodic_net_embedding_digest != self.periodic_net_embedding_digest
            or value.periodic_cell_complex_digest not in complex_digests
            for value in partitions
        ):
            raise NaturalTilingRefinementInputError("A master partition is not bound to a supplied current-bound complex.")
        if any(
            value.periodic_net_view_digest != self.periodic_net_view_digest
            or value.primitive_ring_catalog_digest != catalog.digest
            or value.master_cell_complex_digest not in complex_digests
            or value.master_partition_certificate_digest not in partition_digests
            or value.strength_catalog_digest != self.strength_catalog.digest
            or value.compatibility_system_digest not in system_digests
            for value in searches
        ):
            raise NaturalTilingRefinementInputError("A Stage-10B search result was reused or omitted from its current-bound sources.")

        supplied_catalog = self.catalog
        candidates = tuple(
            candidate
            for search in searches
            for candidate in search.catalog.candidates
        )
        expected_catalog = build_natural_tiling_catalog(
            candidates,
            periodic_net_view_digest=self.periodic_net_view_digest,
            primitive_ring_catalog_digest=catalog.digest,
        )
        if supplied_catalog is None:
            supplied_catalog = expected_catalog
        if not isinstance(supplied_catalog, NaturalTilingCatalog) or supplied_catalog.to_dict() != expected_catalog.to_dict():
            raise NaturalTilingRefinementInputError("The aggregate Stage-10A catalog does not match the rebuilt Stage-10B searches.")

        object.__setattr__(self, "primitive_ring_bound", bound)
        object.__setattr__(self, "face_certificates", certificates)
        object.__setattr__(self, "compatibility_systems", systems)
        object.__setattr__(self, "master_complexes", complexes)
        object.__setattr__(self, "master_partitions", partitions)
        object.__setattr__(self, "search_results", searches)
        object.__setattr__(self, "catalog", supplied_catalog)
        object.__setattr__(self, "unresolved_reasons", tuple(sorted(set(str(value) for value in self.unresolved_reasons if str(value)))))


@dataclass(frozen=True, order=True, slots=True)
class StableRefinementRecord:
    """One bound-independent scientific identity plus its current state."""

    category: RefinementRecordCategory
    identity_json: str
    state_json: str
    key_digest: str = field(default="", compare=True)
    state_digest: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        category = RefinementRecordCategory(self.category)
        try:
            identity = json.loads(self.identity_json)
            state = json.loads(self.state_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise NaturalTilingRefinementInputError("Stable record payloads must be canonical JSON.") from exc
        identity_json = _canonical_json(identity)
        state_json = _canonical_json(state)
        if identity_json != self.identity_json or state_json != self.state_json:
            raise NaturalTilingRefinementInputError("Stable record JSON must be canonical.")
        key = _digest({"category": category.value, "identity": identity})
        state_digest = _digest(state)
        if self.key_digest and self.key_digest != key:
            raise NaturalTilingRefinementInputError("Stable record key digest is inconsistent.")
        if self.state_digest and self.state_digest != state_digest:
            raise NaturalTilingRefinementInputError("Stable record state digest is inconsistent.")
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "key_digest", self.key_digest or key)
        object.__setattr__(self, "state_digest", self.state_digest or state_digest)

    @property
    def identity(self) -> Any:
        return json.loads(self.identity_json)

    @property
    def state(self) -> Any:
        return json.loads(self.state_json)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "identity": self.identity,
            "state": self.state,
            "key_digest": self.key_digest,
            "state_digest": self.state_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StableRefinementRecord":
        try:
            return cls(
                RefinementRecordCategory(str(payload["category"])),
                _canonical_json(payload["identity"]),
                _canonical_json(payload["state"]),
                str(payload["key_digest"]),
                str(payload["state_digest"]),
            )
        except NaturalTilingRefinementError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise NaturalTilingRefinementSerializationError("Invalid stable refinement record.") from exc


@dataclass(frozen=True, slots=True, eq=False)
class PrimitiveBoundSnapshot:
    primitive_ring_bound: int
    periodic_net_view_digest: str
    periodic_net_embedding_digest: str
    topology_graph_digest: str
    primitive_ring_catalog_digest: str
    stage_digests: tuple[tuple[str, str], ...]
    records: tuple[StableRefinementRecord, ...]
    outcome: NaturalTilingOutcomeKind
    status: RefinementSnapshotStatus
    unresolved_reasons: tuple[str, ...]
    canonical_schema_version: str = CANONICAL_BOUND_REFINEMENT_SCHEMA
    digest_algorithm: str = BOUND_REFINEMENT_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        bound = _positive(self.primitive_ring_bound, name="primitive_ring_bound")
        for name in (
            "periodic_net_view_digest",
            "periodic_net_embedding_digest",
            "topology_graph_digest",
            "primitive_ring_catalog_digest",
        ):
            _sha(getattr(self, name), name=name)
        stages = tuple(sorted((str(name), _sha(value, name=f"stage_digests[{name}]")) for name, value in self.stage_digests))
        if len({name for name, _ in stages}) != len(stages):
            raise NaturalTilingRefinementInputError("stage_digests require unique stage names.")
        records = tuple(sorted(self.records, key=lambda value: (value.category.value, value.key_digest)))
        if len({(value.category, value.key_digest) for value in records}) != len(records):
            raise NaturalTilingRefinementInputError("Stable records must be unique by category and key.")
        status = RefinementSnapshotStatus(self.status)
        unresolved = tuple(sorted(set(str(value) for value in self.unresolved_reasons if str(value))))
        if status is RefinementSnapshotStatus.COMPLETE and unresolved:
            raise NaturalTilingRefinementInputError("A complete bound snapshot cannot retain unresolved reasons.")
        if self.canonical_schema_version != CANONICAL_BOUND_REFINEMENT_SCHEMA or self.digest_algorithm != BOUND_REFINEMENT_DIGEST_ALGORITHM:
            raise NaturalTilingRefinementInputError("Unsupported bound-refinement schema or digest algorithm.")
        object.__setattr__(self, "primitive_ring_bound", bound)
        object.__setattr__(self, "stage_digests", stages)
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "outcome", NaturalTilingOutcomeKind(self.outcome))
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "unresolved_reasons", unresolved)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise NaturalTilingRefinementInputError("Stored primitive-bound snapshot digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PrimitiveBoundSnapshot) and self.digest == other.digest

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "primitive_ring_bound": self.primitive_ring_bound,
            "periodic_net_view_digest": self.periodic_net_view_digest,
            "periodic_net_embedding_digest": self.periodic_net_embedding_digest,
            "topology_graph_digest": self.topology_graph_digest,
            "primitive_ring_catalog_digest": self.primitive_ring_catalog_digest,
            "stage_digests": [[name, value] for name, value in self.stage_digests],
            "records": [value.to_dict() for value in self.records],
            "outcome": self.outcome.value,
            "status": self.status.value,
            "unresolved_reasons": list(self.unresolved_reasons),
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PrimitiveBoundSnapshot":
        try:
            return cls(
                int(payload["primitive_ring_bound"]),
                str(payload["periodic_net_view_digest"]),
                str(payload["periodic_net_embedding_digest"]),
                str(payload["topology_graph_digest"]),
                str(payload["primitive_ring_catalog_digest"]),
                tuple((str(value[0]), str(value[1])) for value in payload["stage_digests"]),
                tuple(StableRefinementRecord.from_dict(value) for value in payload["records"]),
                NaturalTilingOutcomeKind(str(payload["outcome"])),
                RefinementSnapshotStatus(str(payload["status"])),
                tuple(str(value) for value in payload["unresolved_reasons"]),
                str(payload["canonical_schema_version"]),
                str(payload["digest_algorithm"]),
                str(payload["digest"]),
            )
        except NaturalTilingRefinementError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise NaturalTilingRefinementSerializationError("Invalid primitive-bound snapshot.") from exc


@dataclass(frozen=True, order=True, slots=True)
class RefinementRecordChange:
    category: RefinementRecordCategory
    kind: RefinementChangeKind
    key_digest: str
    before_state_digest: str | None
    after_state_digest: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "category", RefinementRecordCategory(self.category))
        object.__setattr__(self, "kind", RefinementChangeKind(self.kind))
        _sha(self.key_digest, name="key_digest")
        for name in ("before_state_digest", "after_state_digest"):
            value = getattr(self, name)
            if value is not None:
                _sha(value, name=name)
        if self.kind is RefinementChangeKind.ADDED and (self.before_state_digest is not None or self.after_state_digest is None):
            raise NaturalTilingRefinementInputError("An added record requires only an after state.")
        if self.kind is RefinementChangeKind.REMOVED and (self.before_state_digest is None or self.after_state_digest is not None):
            raise NaturalTilingRefinementInputError("A removed record requires only a before state.")
        if self.kind is RefinementChangeKind.MODIFIED and (self.before_state_digest is None or self.after_state_digest is None or self.before_state_digest == self.after_state_digest):
            raise NaturalTilingRefinementInputError("A modified record requires two different states.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "kind": self.kind.value,
            "key_digest": self.key_digest,
            "before_state_digest": self.before_state_digest,
            "after_state_digest": self.after_state_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RefinementRecordChange":
        try:
            return cls(
                RefinementRecordCategory(str(payload["category"])),
                RefinementChangeKind(str(payload["kind"])),
                str(payload["key_digest"]),
                None if payload.get("before_state_digest") is None else str(payload["before_state_digest"]),
                None if payload.get("after_state_digest") is None else str(payload["after_state_digest"]),
            )
        except NaturalTilingRefinementError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise NaturalTilingRefinementSerializationError("Invalid refinement change record.") from exc


@dataclass(frozen=True, slots=True, eq=False)
class PrimitiveBoundTransition:
    lower_bound: int
    upper_bound: int
    lower_snapshot_digest: str
    upper_snapshot_digest: str
    changes: tuple[RefinementRecordChange, ...]
    outcome_changed: bool
    monotonicity_violations: tuple[str, ...]
    status: RefinementTransitionStatus
    digest: str = ""

    def __post_init__(self) -> None:
        lower = _positive(self.lower_bound, name="lower_bound")
        upper = _positive(self.upper_bound, name="upper_bound")
        if upper <= lower:
            raise NaturalTilingRefinementInputError("Refinement bounds must increase strictly.")
        _sha(self.lower_snapshot_digest, name="lower_snapshot_digest")
        _sha(self.upper_snapshot_digest, name="upper_snapshot_digest")
        changes = tuple(sorted(self.changes))
        violations = tuple(sorted(set(str(value) for value in self.monotonicity_violations if str(value))))
        status = RefinementTransitionStatus(self.status)
        if status is RefinementTransitionStatus.STABLE and (changes or self.outcome_changed or violations):
            raise NaturalTilingRefinementInputError("A stable transition cannot contain changes or violations.")
        if status is RefinementTransitionStatus.INVALID and not violations:
            raise NaturalTilingRefinementInputError("An invalid transition requires a monotonicity violation.")
        object.__setattr__(self, "lower_bound", lower)
        object.__setattr__(self, "upper_bound", upper)
        object.__setattr__(self, "changes", changes)
        object.__setattr__(self, "outcome_changed", bool(self.outcome_changed))
        object.__setattr__(self, "monotonicity_violations", violations)
        object.__setattr__(self, "status", status)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise NaturalTilingRefinementInputError("Stored refinement transition digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PrimitiveBoundTransition) and self.digest == other.digest

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "lower_snapshot_digest": self.lower_snapshot_digest,
            "upper_snapshot_digest": self.upper_snapshot_digest,
            "changes": [value.to_dict() for value in self.changes],
            "outcome_changed": self.outcome_changed,
            "monotonicity_violations": list(self.monotonicity_violations),
            "status": self.status.value,
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PrimitiveBoundTransition":
        try:
            return cls(
                int(payload["lower_bound"]),
                int(payload["upper_bound"]),
                str(payload["lower_snapshot_digest"]),
                str(payload["upper_snapshot_digest"]),
                tuple(RefinementRecordChange.from_dict(value) for value in payload["changes"]),
                bool(payload["outcome_changed"]),
                tuple(str(value) for value in payload["monotonicity_violations"]),
                RefinementTransitionStatus(str(payload["status"])),
                str(payload["digest"]),
            )
        except NaturalTilingRefinementError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise NaturalTilingRefinementSerializationError("Invalid primitive-bound transition.") from exc


@dataclass(frozen=True, slots=True, eq=False)
class PrimitiveBoundRefinementReport:
    snapshots: tuple[PrimitiveBoundSnapshot, ...]
    transitions: tuple[PrimitiveBoundTransition, ...]
    stable_tested_suffix_start: int | None
    status: RefinementTransitionStatus
    canonical_schema_version: str = CANONICAL_BOUND_REFINEMENT_SCHEMA
    digest_algorithm: str = BOUND_REFINEMENT_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        snapshots = tuple(self.snapshots)
        if not snapshots:
            raise NaturalTilingRefinementInputError("A refinement report requires at least one bound snapshot.")
        if tuple(value.primitive_ring_bound for value in snapshots) != tuple(sorted({value.primitive_ring_bound for value in snapshots})):
            raise NaturalTilingRefinementInputError("Snapshot bounds must be unique and strictly increasing.")
        if len({value.periodic_net_view_digest for value in snapshots}) != 1 or len({value.periodic_net_embedding_digest for value in snapshots}) != 1 or len({value.topology_graph_digest for value in snapshots}) != 1:
            raise NaturalTilingRefinementInputError("All refinement snapshots must describe one fixed net view, embedding, and topology.")
        expected_transitions = tuple(compare_primitive_bound_snapshots(left, right) for left, right in zip(snapshots, snapshots[1:]))
        if tuple(self.transitions) != expected_transitions:
            raise NaturalTilingRefinementInputError("Refinement transitions are not canonical for the supplied snapshots.")
        suffix = _stable_suffix_start(snapshots, expected_transitions)
        if self.stable_tested_suffix_start != suffix:
            raise NaturalTilingRefinementInputError("stable_tested_suffix_start is inconsistent.")
        status = RefinementTransitionStatus(self.status)
        expected_status = (
            RefinementTransitionStatus.INVALID
            if any(value.status is RefinementTransitionStatus.INVALID for value in expected_transitions)
            else RefinementTransitionStatus.UNRESOLVED
            if any(value.status is RefinementTransitionStatus.UNRESOLVED for value in expected_transitions) or any(value.status is RefinementSnapshotStatus.UNRESOLVED for value in snapshots)
            else RefinementTransitionStatus.STABLE
            if expected_transitions and all(value.status is RefinementTransitionStatus.STABLE for value in expected_transitions)
            else RefinementTransitionStatus.CHANGED
            if expected_transitions
            else RefinementTransitionStatus.STABLE
        )
        if status is not expected_status:
            raise NaturalTilingRefinementInputError("Refinement report status is inconsistent.")
        if self.canonical_schema_version != CANONICAL_BOUND_REFINEMENT_SCHEMA or self.digest_algorithm != BOUND_REFINEMENT_DIGEST_ALGORITHM:
            raise NaturalTilingRefinementInputError("Unsupported bound-refinement schema or digest algorithm.")
        object.__setattr__(self, "snapshots", snapshots)
        object.__setattr__(self, "transitions", expected_transitions)
        object.__setattr__(self, "status", status)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise NaturalTilingRefinementInputError("Stored refinement report digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PrimitiveBoundRefinementReport) and self.digest == other.digest

    @property
    def stabilized_over_tested_suffix(self) -> bool:
        return self.stable_tested_suffix_start is not None

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "snapshots": [value.to_dict() for value in self.snapshots],
            "transitions": [value.to_dict() for value in self.transitions],
            "stable_tested_suffix_start": self.stable_tested_suffix_start,
            "status": self.status.value,
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PrimitiveBoundRefinementReport":
        try:
            return cls(
                tuple(PrimitiveBoundSnapshot.from_dict(value) for value in payload["snapshots"]),
                tuple(PrimitiveBoundTransition.from_dict(value) for value in payload["transitions"]),
                None if payload.get("stable_tested_suffix_start") is None else int(payload["stable_tested_suffix_start"]),
                RefinementTransitionStatus(str(payload["status"])),
                str(payload["canonical_schema_version"]),
                str(payload["digest_algorithm"]),
                str(payload["digest"]),
            )
        except NaturalTilingRefinementError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise NaturalTilingRefinementSerializationError("Invalid primitive-bound refinement report.") from exc


def build_primitive_bound_snapshot(
    build: PrimitiveBoundBuild,
    *,
    resources: NaturalTilingRefinementResources | None = None,
) -> PrimitiveBoundSnapshot:
    """Validate and reduce one full rebuild to bound-independent stable records."""

    if not isinstance(build, PrimitiveBoundBuild):
        raise NaturalTilingRefinementInputError("build must be a PrimitiveBoundBuild.")
    limits = resources or NaturalTilingRefinementResources()
    records: list[StableRefinementRecord] = []

    for ring in build.ring_index.catalog.rings:
        records.append(_record(RefinementRecordCategory.RING, _ring_payload(ring.key), {"size": ring.size}))

    for orbit in build.ring_symmetry.ring_orbits:
        keys = sorted((_ring_payload(build.ring_symmetry.ring_keys[position]) for position in orbit), key=_canonical_json)
        stabilizers = sorted(len(build.ring_symmetry.ring_stabilizers[position]) for position in orbit)
        records.append(_record(RefinementRecordCategory.RING_ORBIT, {"ring_keys": keys}, {"stabilizer_orders": stabilizers}))

    for result in build.strength_catalog.results:
        state = _normalize_payload(result.to_dict(), drop_keys=_VOLATILE_SOURCE_KEYS)
        records.append(_record(RefinementRecordCategory.STRENGTH, _ring_payload(result.target_placement.ring_key), state))

    face_key_by_certificate: dict[str, str] = {}
    face_key_by_placement: dict[str, str] = {}
    witness_key_by_digest: dict[str, str] = {}
    for certificate in build.face_certificates:
        identity = _face_identity(certificate)
        key = _face_key(certificate)
        face_key_by_certificate[certificate.digest] = key
        face_key_by_placement[certificate.face_placement.digest] = key
        for witness in certificate.witnesses:
            witness_key_by_digest[witness.digest] = _digest(
                {
                    "face_key": key,
                    "witness_id": witness.witness_id,
                    "method": witness.method.value,
                    "triangles": [list(value) for value in witness.triangles],
                }
            )
        state = _normalize_payload(certificate.to_dict(), drop_keys=_VOLATILE_SOURCE_KEYS)
        records.append(_record(RefinementRecordCategory.FACE, identity, state))

    replacements = {**face_key_by_certificate, **face_key_by_placement, **witness_key_by_digest}
    compatibility_key_by_digest: dict[str, str] = {}
    for system in build.compatibility_systems:
        domain = sorted(replacements[value] for value in system.face_certificate_digests)
        state = _normalize_payload(system.to_dict(), replacements=replacements, drop_keys=frozenset({"digest"}))
        for list_key in (
            "face_certificate_digests",
            "assignments",
            "pair_certificates",
            "constraints",
            "face_symmetry_relations",
            "witness_symmetry_relations",
        ):
            if list_key in state:
                state[list_key] = sorted(state[list_key], key=_canonical_json)
        record = _record(RefinementRecordCategory.COMPATIBILITY, {"face_domain": domain}, state)
        records.append(record)
        compatibility_key_by_digest[system.digest] = record.key_digest

    complex_key_by_digest: dict[str, str] = {}
    for complex_ in build.master_complexes:
        identity = _complex_identity(complex_)
        record = _record(RefinementRecordCategory.MASTER_COMPLEX, identity, {"cell_counts": list(complex_.cell_counts)})
        records.append(record)
        complex_key_by_digest[complex_.digest] = record.key_digest

    partition_key_by_digest: dict[str, str] = {}
    for partition in build.master_partitions:
        identity = _partition_identity(partition, complex_key_by_digest)
        record = _record(
            RefinementRecordCategory.MASTER_PARTITION,
            identity,
            {
                "exact_tetrahedron_test_count": partition.exact_tetrahedron_test_count,
                "tetrahedron_count": len(partition.tetrahedra),
                "facet_pair_count": len(partition.facet_pairs),
            },
        )
        records.append(record)
        partition_key_by_digest[partition.digest] = record.key_digest

    tiling_key_by_candidate_digest: dict[str, str] = {}
    for search in build.search_results:
        stable_tilings = []
        for candidate in search.candidates:
            complex_identity = _complex_identity(candidate.cell_complex)
            tiling_identity = {
                "scientific_complex": complex_identity,
                "selected_ring_keys": [
                    _ring_payload(value)
                    for value in candidate.natural_tiling_candidate.selected_ring_keys
                ],
            }
            certification_state = candidate.natural_tiling_candidate.certification.to_dict()
            certification_state.pop("primitive_ring_bound", None)
            tiling_state = {
                "eligibility": candidate.natural_tiling_candidate.eligibility.value,
                "certification": certification_state,
            }
            tiling_record = _record(RefinementRecordCategory.TILING, tiling_identity, tiling_state)
            records.append(tiling_record)
            tiling_key_by_candidate_digest[candidate.natural_tiling_candidate.digest] = tiling_record.key_digest
            stable_tilings.append(tiling_record.key_digest)
        search_identity = {
            "master_complex_key": complex_key_by_digest[search.master_cell_complex_digest],
            "master_partition_key": partition_key_by_digest[search.master_partition_certificate_digest],
            "compatibility_key": compatibility_key_by_digest[search.compatibility_system_digest],
        }
        search_state = {
            "status": search.status.value,
            "attempted_selection_count": search.attempted_selection_count,
            "compatible_selection_count": search.compatible_selection_count,
            "constructed_selection_count": search.constructed_selection_count,
            "unresolved_reasons": list(search.unresolved_reasons),
            "tiling_keys": sorted(stable_tilings),
        }
        records.append(_record(RefinementRecordCategory.SEARCH, search_identity, search_state))

    for key in build.catalog.essential_ring_keys:  # type: ignore[union-attr]
        records.append(_record(RefinementRecordCategory.ESSENTIAL_RING, _ring_payload(key), {"essential": True}))

    if len(records) > limits.max_records_per_snapshot:
        raise NaturalTilingRefinementResourceError("Stable record count exceeds max_records_per_snapshot.")

    unresolved = list(build.unresolved_reasons)
    catalog = build.ring_index.catalog
    if not catalog.search_completed_without_resource_truncation or catalog.complete_for_ring_sizes_up_to < build.primitive_ring_bound:
        unresolved.append("primitive-ring search is incomplete or resource-truncated at the requested bound")
    if not build.ring_symmetry.source_search_completed_without_resource_truncation or build.ring_symmetry.complete_for_ring_sizes_up_to < build.primitive_ring_bound:
        unresolved.append("induced ring symmetry is not complete at the requested bound")
    if any(value.status in (RingStrengthStatus.UNRESOLVED_SOURCE_INCOMPLETE, RingStrengthStatus.UNRESOLVED_TRUNCATED) for value in build.strength_catalog.results):
        unresolved.append("one or more bounded ring-strength classifications are unresolved")
    if any(value.status is not FacePlacementStatus.CERTIFIED_ADMISSIBLE for value in build.face_certificates):
        unresolved.append("one or more face-placement searches are unresolved or inadmissible")
    if not build.search_results:
        unresolved.append("no rebuilt Stage-10B master-refinement search was supplied")
    if any(value.status is NaturalTilingSearchStatus.UNRESOLVED for value in build.search_results):
        unresolved.append("one or more Stage-10B searches are unresolved")
    if build.catalog.unresolved_candidates:  # type: ignore[union-attr]
        unresolved.append("the aggregate natural-tiling catalog contains unresolved candidates")
    unresolved_tuple = tuple(sorted(set(unresolved)))
    status = RefinementSnapshotStatus.UNRESOLVED if unresolved_tuple else RefinementSnapshotStatus.COMPLETE

    stage_digests = (
        ("primitive_ring_catalog", catalog.digest),
        ("ring_symmetry", build.ring_symmetry.digest),
        ("ring_strength", build.strength_catalog.digest),
        ("face_certificates", _digest(sorted(value.digest for value in build.face_certificates))),
        ("compatibility_systems", _digest(sorted(value.digest for value in build.compatibility_systems))),
        ("master_complexes", _digest(sorted(value.digest for value in build.master_complexes))),
        ("master_partitions", _digest(sorted(value.digest for value in build.master_partitions))),
        ("natural_tiling_searches", _digest(sorted(value.digest for value in build.search_results))),
        ("natural_tiling_catalog", build.catalog.digest),  # type: ignore[union-attr]
    )
    return PrimitiveBoundSnapshot(
        build.primitive_ring_bound,
        build.periodic_net_view_digest,
        build.periodic_net_embedding_digest,
        build.ring_index.topology_graph_digest,
        catalog.digest,
        stage_digests,
        tuple(records),
        build.catalog.outcome.kind,  # type: ignore[union-attr]
        status,
        unresolved_tuple,
    )


def compare_primitive_bound_snapshots(
    lower: PrimitiveBoundSnapshot,
    upper: PrimitiveBoundSnapshot,
) -> PrimitiveBoundTransition:
    """Compare consecutive complete rebuilds strictly by stable scientific keys."""

    if not isinstance(lower, PrimitiveBoundSnapshot) or not isinstance(upper, PrimitiveBoundSnapshot):
        raise NaturalTilingRefinementInputError("lower and upper must be PrimitiveBoundSnapshot records.")
    if upper.primitive_ring_bound <= lower.primitive_ring_bound:
        raise NaturalTilingRefinementInputError("The upper primitive-ring bound must be larger.")
    if (
        lower.periodic_net_view_digest != upper.periodic_net_view_digest
        or lower.periodic_net_embedding_digest != upper.periodic_net_embedding_digest
        or lower.topology_graph_digest != upper.topology_graph_digest
    ):
        raise NaturalTilingRefinementInputError("Stable-key refinement requires one fixed net view, embedding, and topology.")
    left = {(value.category, value.key_digest): value for value in lower.records}
    right = {(value.category, value.key_digest): value for value in upper.records}
    changes: list[RefinementRecordChange] = []
    for key in sorted(set(left) | set(right), key=lambda value: (value[0].value, value[1])):
        before = left.get(key)
        after = right.get(key)
        if before is None:
            changes.append(RefinementRecordChange(key[0], RefinementChangeKind.ADDED, key[1], None, after.state_digest))  # type: ignore[union-attr]
        elif after is None:
            changes.append(RefinementRecordChange(key[0], RefinementChangeKind.REMOVED, key[1], before.state_digest, None))
        elif before.state_digest != after.state_digest:
            changes.append(RefinementRecordChange(key[0], RefinementChangeKind.MODIFIED, key[1], before.state_digest, after.state_digest))

    violations = []
    removed_rings = [value for value in changes if value.category is RefinementRecordCategory.RING and value.kind is RefinementChangeKind.REMOVED]
    if removed_rings and lower.status is RefinementSnapshotStatus.COMPLETE and upper.status is RefinementSnapshotStatus.COMPLETE:
        violations.append(f"{len(removed_rings)} primitive-ring stable keys disappeared under an increased complete bound")
    outcome_changed = lower.outcome is not upper.outcome
    if violations:
        status = RefinementTransitionStatus.INVALID
    elif lower.status is RefinementSnapshotStatus.UNRESOLVED or upper.status is RefinementSnapshotStatus.UNRESOLVED:
        status = RefinementTransitionStatus.UNRESOLVED
    elif changes or outcome_changed:
        status = RefinementTransitionStatus.CHANGED
    else:
        status = RefinementTransitionStatus.STABLE
    return PrimitiveBoundTransition(
        lower.primitive_ring_bound,
        upper.primitive_ring_bound,
        lower.digest,
        upper.digest,
        tuple(changes),
        outcome_changed,
        tuple(violations),
        status,
    )


def _stable_suffix_start(
    snapshots: Sequence[PrimitiveBoundSnapshot],
    transitions: Sequence[PrimitiveBoundTransition],
) -> int | None:
    if len(snapshots) < 2 or not transitions:
        return None
    start = None
    for index in range(len(transitions) - 1, -1, -1):
        if transitions[index].status is RefinementTransitionStatus.STABLE:
            start = snapshots[index].primitive_ring_bound
        else:
            break
    return start


def build_primitive_bound_refinement_report(
    snapshots: Sequence[PrimitiveBoundSnapshot],
    *,
    resources: NaturalTilingRefinementResources | None = None,
) -> PrimitiveBoundRefinementReport:
    limits = resources or NaturalTilingRefinementResources()
    values = tuple(snapshots)
    if not values:
        raise NaturalTilingRefinementInputError("At least one bound snapshot is required.")
    if len(values) > limits.max_bounds:
        raise NaturalTilingRefinementResourceError("Requested snapshot count exceeds max_bounds.")
    transitions = tuple(compare_primitive_bound_snapshots(left, right) for left, right in zip(values, values[1:]))
    total_changes = sum(len(value.changes) for value in transitions)
    if total_changes > limits.max_total_changes:
        raise NaturalTilingRefinementResourceError("Refinement change count exceeds max_total_changes.")
    status = (
        RefinementTransitionStatus.INVALID
        if any(value.status is RefinementTransitionStatus.INVALID for value in transitions)
        else RefinementTransitionStatus.UNRESOLVED
        if any(value.status is RefinementTransitionStatus.UNRESOLVED for value in transitions) or any(value.status is RefinementSnapshotStatus.UNRESOLVED for value in values)
        else RefinementTransitionStatus.STABLE
        if transitions and all(value.status is RefinementTransitionStatus.STABLE for value in transitions)
        else RefinementTransitionStatus.CHANGED
        if transitions
        else RefinementTransitionStatus.STABLE
    )
    return PrimitiveBoundRefinementReport(values, transitions, _stable_suffix_start(values, transitions), status)


def run_primitive_bound_refinement(
    bounds: Sequence[int],
    rebuild: Callable[[int], PrimitiveBoundBuild],
    *,
    resources: NaturalTilingRefinementResources | None = None,
) -> PrimitiveBoundRefinementReport:
    """Execute one independent full rebuild per bound and compare the results."""

    limits = resources or NaturalTilingRefinementResources()
    requested = tuple(_positive(value, name="primitive-ring bound") for value in bounds)
    if not requested or requested != tuple(sorted(set(requested))):
        raise NaturalTilingRefinementInputError("bounds must be nonempty, unique, and strictly increasing.")
    if len(requested) > limits.max_bounds:
        raise NaturalTilingRefinementResourceError("Requested bound count exceeds max_bounds.")
    if not callable(rebuild):
        raise NaturalTilingRefinementInputError("rebuild must be callable.")
    snapshots = []
    for bound in requested:
        build = rebuild(bound)
        if not isinstance(build, PrimitiveBoundBuild) or build.primitive_ring_bound != bound:
            raise NaturalTilingRefinementInputError("The rebuild callback returned the wrong primitive-ring bound.")
        snapshots.append(build_primitive_bound_snapshot(build, resources=limits))
    return build_primitive_bound_refinement_report(tuple(snapshots), resources=limits)


__all__ = [
    "BOUND_REFINEMENT_DIGEST_ALGORITHM",
    "CANONICAL_BOUND_REFINEMENT_SCHEMA",
    "NaturalTilingRefinementError",
    "NaturalTilingRefinementInputError",
    "NaturalTilingRefinementResourceError",
    "NaturalTilingRefinementSerializationError",
    "NaturalTilingRefinementResources",
    "PrimitiveBoundBuild",
    "PrimitiveBoundRefinementReport",
    "PrimitiveBoundSnapshot",
    "PrimitiveBoundTransition",
    "RefinementChangeKind",
    "RefinementRecordCategory",
    "RefinementRecordChange",
    "RefinementSnapshotStatus",
    "RefinementTransitionStatus",
    "StableRefinementRecord",
    "build_primitive_bound_refinement_report",
    "build_primitive_bound_snapshot",
    "compare_primitive_bound_snapshots",
    "run_primitive_bound_refinement",
]
