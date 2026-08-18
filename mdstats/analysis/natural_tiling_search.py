"""Stage-10B symmetry-pruned natural-face selection and local splitting.

The first backend is complete for one explicit *master refinement*: a certified
Stage-9 periodic tetrahedral partition whose scientific interfaces contain every
ring cut admitted to the finite search.  A candidate face selection removes some
master interfaces and merges tetrahedra across them.  Translation-labelled
connectivity then reconstructs finite tile orbits, their oriented shells, and a
new exact partition certificate.

This construction implements the natural-tiling principles of symmetry-preserved
locally strong ring faces and splitting along admissible non-face strong rings
from Blatov, Delgado-Friedrichs, O'Keeffe, and Proserpio (2007).  The exact
master-refinement coarsening, voltage-consistency test for finite lifted tile
components, shell reconstruction, maximal-splitting rule, and explicit bounded
failure semantics are mdstats-specific constructions.

The backend does not infer a master refinement, introduce Steiner surfaces, or
claim completeness outside the supplied exact tetrahedral arrangement.

Reference
---------
V. A. Blatov, O. Delgado-Friedrichs, M. O'Keeffe, and D. M. Proserpio,
"Three-periodic nets and tilings: natural tilings for nets", Acta Cryst. A 63,
418-425 (2007), doi:10.1107/S0108767307038287.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import itertools
import json
from numbers import Integral
from typing import Any, Iterable, Mapping, Sequence

from ._periodic_graph import LatticeShift, add_shift, subtract_shift
from .face_candidates import (
    FaceCompatibilityConstraint,
    FaceCompatibilityConstraintSystem,
    FaceConstraintKind,
    FaceEmbeddingWitness,
    FacePlacementCertificate,
    FaceWitnessAssignment,
)
from .natural_tiling import (
    CandidateEligibility,
    NaturalTilingCandidate,
    NaturalTilingCatalog,
    NaturalTilingSymmetryResources,
    build_natural_tiling_catalog,
    build_periodic_cell_complex_symmetry_action,
    certify_natural_tiling_candidate,
)
from .net_symmetry_discovery import PeriodicNetSymmetryDiscovery
from .periodic_cell_complex import (
    PartitionFacetKind,
    PeriodicCellComplex,
    PeriodicCellComplexError,
    PeriodicCellComplexInvariantError,
    PeriodicCellComplexResourceError,
    PeriodicPartitionCertificate,
    PeriodicPartitionResources,
    PeriodicTetrahedron,
    PeriodicTileShell,
    TilePlacementRef,
    TranslatedCellTerm,
    _canonical_ref_facet,
    _facet_vertices,
    build_periodic_cell_complex,
    certify_periodic_tetrahedral_partition,
)
from .periodic_net_embedding import PeriodicNetEmbedding
from .periodic_net_view import PeriodicNetView
from .primitive_ring import PrimitiveRingKey
from .primitive_ring_index import PrimitiveRingIndex
from .ring_strength import RingStrengthCatalog, RingStrengthStatus

CANONICAL_NATURAL_TILING_SEARCH_SCHEMA = "mdstats.natural-tiling-search.v1"
NATURAL_TILING_SEARCH_DIGEST_ALGORITHM = "sha256-canonical-json-v1"
ZERO_SHIFT: LatticeShift = (0, 0, 0)


class NaturalTilingSearchError(ValueError):
    """Base exception for Stage-10B natural-tiling search."""


class NaturalTilingSearchInputError(NaturalTilingSearchError):
    """Raised when the master refinement or source records disagree."""


class NaturalTilingSearchInvariantError(NaturalTilingSearchError):
    """Raised when exact master-refinement algebra is internally inconsistent."""


class NaturalTilingSearchResourceError(NaturalTilingSearchError):
    """Raised transactionally before a declared finite search limit is exceeded."""


class NaturalTilingSearchSerializationError(NaturalTilingSearchError):
    """Raised when persistent search data fail source replay."""


class NaturalTilingSearchStatus(str, Enum):
    """Completeness of the finite master-refinement search."""

    COMPLETE = "complete"
    UNRESOLVED = "unresolved"


class NaturalFaceOrbitStrength(str, Enum):
    """Bounded strength state of one symmetry-closed master-face orbit."""

    STRONG_SELECTABLE = "strong-selectable"
    WEAK_EXCLUDED = "weak-excluded"
    UNRESOLVED = "unresolved"


class NaturalTilingSearchRejectionKind(str, Enum):
    """Machine-readable reason one symmetry-closed selection did not survive."""

    EMPTY_SELECTION = "empty-selection"
    FORBIDDEN_COMPATIBILITY = "forbidden-compatibility"
    UNRESOLVED_COMPATIBILITY = "unresolved-compatibility"
    NONCOMPACT_TILE_COMPONENT = "noncompact-tile-component"
    NONSEPARATING_SELECTED_FACE = "nonseparating-selected-face"
    INVALID_CELL_COMPLEX = "invalid-cell-complex"
    INVALID_PARTITION = "invalid-partition"
    INELIGIBLE_CERTIFICATION = "ineligible-certification"
    NONMAXIMAL_SPLITTING = "nonmaximal-splitting"


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _sha(value: object, *, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise NaturalTilingSearchInputError(f"{name} must be a SHA-256 digest.")
    return value


def _nonnegative(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        raise NaturalTilingSearchInputError(f"{name} must be a nonnegative integer.")
    return int(value)


def _positive(value: object, *, name: str) -> int:
    result = _nonnegative(value, name=name)
    if result == 0:
        raise NaturalTilingSearchInputError(f"{name} must be positive.")
    return result


def _negate_shift(value: LatticeShift) -> LatticeShift:
    return (-value[0], -value[1], -value[2])


@dataclass(frozen=True, slots=True)
class NaturalTilingSearchResources:
    """Transactional bounds for the finite Stage-10B search family."""

    max_face_orbits: int = 24
    max_face_selections: int = 1_000_000
    max_connectivity_arcs: int = 5_000_000
    max_candidate_constructions: int = 1_000_000

    def __post_init__(self) -> None:
        for name in (
            "max_face_orbits",
            "max_face_selections",
            "max_connectivity_arcs",
            "max_candidate_constructions",
        ):
            object.__setattr__(self, name, _positive(getattr(self, name), name=name))


@dataclass(frozen=True, slots=True, eq=False)
class NaturalFaceOrbit:
    """One exact orbit of master scientific faces under the full net group."""

    orbit_index: int
    face_indices: tuple[int, ...]
    face_digests: tuple[str, ...]
    ring_keys: tuple[PrimitiveRingKey, ...]
    strength: NaturalFaceOrbitStrength
    digest: str = ""

    def __post_init__(self) -> None:
        index = _nonnegative(self.orbit_index, name="orbit_index")
        raw_faces = tuple(_nonnegative(value, name="face_index") for value in self.face_indices)
        faces = tuple(sorted(set(raw_faces)))
        if not faces:
            raise NaturalTilingSearchInputError("A natural-face orbit cannot be empty.")
        if raw_faces != faces:
            raise NaturalTilingSearchInputError(
                "face_indices must be strictly increasing so aligned face_digests and ring_keys remain unambiguous."
            )
        digests = tuple(self.face_digests)
        if len(digests) != len(faces) or len(set(digests)) != len(digests):
            raise NaturalTilingSearchInputError("face_digests must align with unique face_indices.")
        for value in digests:
            _sha(value, name="face_digest")
        keys = tuple(self.ring_keys)
        if len(keys) != len(faces):
            raise NaturalTilingSearchInputError("ring_keys must align with face_indices.")
        strength = NaturalFaceOrbitStrength(self.strength)
        object.__setattr__(self, "orbit_index", index)
        object.__setattr__(self, "face_indices", faces)
        object.__setattr__(self, "face_digests", digests)
        object.__setattr__(self, "ring_keys", keys)
        object.__setattr__(self, "strength", strength)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise NaturalTilingSearchInputError("Stored natural-face-orbit digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NaturalFaceOrbit) and self.digest == other.digest

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "orbit_index": self.orbit_index,
            "face_indices": list(self.face_indices),
            "face_digests": list(self.face_digests),
            "ring_keys": [value.to_dict() for value in self.ring_keys],
            "strength": self.strength.value,
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)


@dataclass(frozen=True, slots=True, eq=False)
class NaturalFaceSelection:
    """One symmetry-closed fixed-witness cut selection in the master refinement."""

    selected_orbit_indices: tuple[int, ...]
    selected_face_indices: tuple[int, ...]
    selected_face_digests: tuple[str, ...]
    selected_witness_digests: tuple[str, ...]
    digest: str = ""

    def __post_init__(self) -> None:
        raw_orbits = tuple(
            _nonnegative(value, name="selected_orbit_index")
            for value in self.selected_orbit_indices
        )
        raw_faces = tuple(
            _nonnegative(value, name="selected_face_index")
            for value in self.selected_face_indices
        )
        orbits = tuple(sorted(set(raw_orbits)))
        faces = tuple(sorted(set(raw_faces)))
        if raw_orbits != orbits or raw_faces != faces:
            raise NaturalTilingSearchInputError(
                "Selection indices must be strictly increasing so aligned digests remain unambiguous."
            )
        if not orbits or not faces:
            raise NaturalTilingSearchInputError("A stored face selection must be nonempty.")
        face_digests = tuple(self.selected_face_digests)
        witness_digests = tuple(self.selected_witness_digests)
        if len(face_digests) != len(faces) or len(witness_digests) != len(faces):
            raise NaturalTilingSearchInputError("Selection digests must align with selected faces.")
        for name, values in (
            ("selected_face_digest", face_digests),
            ("selected_witness_digest", witness_digests),
        ):
            for value in values:
                _sha(value, name=name)
        object.__setattr__(self, "selected_orbit_indices", orbits)
        object.__setattr__(self, "selected_face_indices", faces)
        object.__setattr__(self, "selected_face_digests", face_digests)
        object.__setattr__(self, "selected_witness_digests", witness_digests)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise NaturalTilingSearchInputError("Stored natural-face-selection digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NaturalFaceSelection) and self.digest == other.digest

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "selected_orbit_indices": list(self.selected_orbit_indices),
            "selected_face_indices": list(self.selected_face_indices),
            "selected_face_digests": list(self.selected_face_digests),
            "selected_witness_digests": list(self.selected_witness_digests),
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)


@dataclass(frozen=True, slots=True)
class NaturalTilingSearchRejection:
    """One rejected, unresolved, or dominated symmetry-closed selection."""

    selected_orbit_indices: tuple[int, ...]
    kind: NaturalTilingSearchRejectionKind
    reason: str

    def __post_init__(self) -> None:
        indices = tuple(sorted(set(_nonnegative(value, name="selected_orbit_index") for value in self.selected_orbit_indices)))
        kind = NaturalTilingSearchRejectionKind(self.kind)
        if not isinstance(self.reason, str) or not self.reason:
            raise NaturalTilingSearchInputError("A search rejection requires a nonempty reason.")
        object.__setattr__(self, "selected_orbit_indices", indices)
        object.__setattr__(self, "kind", kind)

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_orbit_indices": list(self.selected_orbit_indices),
            "kind": self.kind.value,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True, eq=False)
class NaturalTilingSearchCandidate:
    """One maximal exact coarsening plus its Stage-10A certification."""

    selection: NaturalFaceSelection
    cell_complex: PeriodicCellComplex
    partition_certificate: PeriodicPartitionCertificate
    natural_tiling_candidate: NaturalTilingCandidate
    digest: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.selection, NaturalFaceSelection):
            raise NaturalTilingSearchInputError("selection must be a NaturalFaceSelection.")
        if not isinstance(self.cell_complex, PeriodicCellComplex):
            raise NaturalTilingSearchInputError("cell_complex must be a PeriodicCellComplex.")
        if not isinstance(self.partition_certificate, PeriodicPartitionCertificate):
            raise NaturalTilingSearchInputError("partition_certificate must be a PeriodicPartitionCertificate.")
        if not isinstance(self.natural_tiling_candidate, NaturalTilingCandidate):
            raise NaturalTilingSearchInputError("natural_tiling_candidate must be a NaturalTilingCandidate.")
        if self.partition_certificate.periodic_cell_complex_digest != self.cell_complex.digest:
            raise NaturalTilingSearchInputError("Partition certificate and generated complex disagree.")
        if self.natural_tiling_candidate.periodic_cell_complex_digest != self.cell_complex.digest:
            raise NaturalTilingSearchInputError("Stage-10A candidate and generated complex disagree.")
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise NaturalTilingSearchInputError("Stored search-candidate digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NaturalTilingSearchCandidate) and self.digest == other.digest

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "selection": self.selection.to_dict(),
            "cell_complex": self.cell_complex.to_dict(),
            "partition_certificate": self.partition_certificate.to_dict(),
            "natural_tiling_candidate": self.natural_tiling_candidate.to_dict(),
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)


@dataclass(frozen=True, slots=True, eq=False)
class NaturalTilingSearchResult:
    """Persistent result of one complete or explicitly unresolved finite search."""

    periodic_net_view_digest: str
    primitive_ring_catalog_digest: str
    master_cell_complex_digest: str
    master_partition_certificate_digest: str
    strength_catalog_digest: str
    compatibility_system_digest: str
    face_orbits: tuple[NaturalFaceOrbit, ...]
    attempted_selection_count: int
    compatible_selection_count: int
    constructed_selection_count: int
    candidates: tuple[NaturalTilingSearchCandidate, ...]
    rejections: tuple[NaturalTilingSearchRejection, ...]
    status: NaturalTilingSearchStatus
    unresolved_reasons: tuple[str, ...]
    catalog: NaturalTilingCatalog
    canonical_schema_version: str = CANONICAL_NATURAL_TILING_SEARCH_SCHEMA
    digest_algorithm: str = NATURAL_TILING_SEARCH_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        for name in (
            "periodic_net_view_digest",
            "primitive_ring_catalog_digest",
            "master_cell_complex_digest",
            "master_partition_certificate_digest",
            "strength_catalog_digest",
            "compatibility_system_digest",
        ):
            _sha(getattr(self, name), name=name)
        orbits = tuple(self.face_orbits)
        if tuple(value.orbit_index for value in orbits) != tuple(range(len(orbits))):
            raise NaturalTilingSearchInputError("Natural-face orbit IDs must be dense and ordered.")
        candidates = tuple(sorted(self.candidates, key=lambda value: value.selection.digest))
        if len({value.selection.digest for value in candidates}) != len(candidates):
            raise NaturalTilingSearchInputError("Search candidates require unique face selections.")
        rejections = tuple(
            sorted(
                self.rejections,
                key=lambda value: (value.selected_orbit_indices, value.kind.value, value.reason),
            )
        )
        attempted = _nonnegative(self.attempted_selection_count, name="attempted_selection_count")
        compatible = _nonnegative(self.compatible_selection_count, name="compatible_selection_count")
        constructed = _nonnegative(self.constructed_selection_count, name="constructed_selection_count")
        if compatible > attempted or constructed > compatible:
            raise NaturalTilingSearchInputError("Search counters are not monotone.")
        status = NaturalTilingSearchStatus(self.status)
        unresolved = tuple(sorted(set(str(value) for value in self.unresolved_reasons if str(value))))
        if status is NaturalTilingSearchStatus.COMPLETE and unresolved:
            raise NaturalTilingSearchInputError("A complete search cannot retain unresolved reasons.")
        expected_catalog_candidates = tuple(
            value.natural_tiling_candidate for value in candidates
        )
        if self.catalog.candidates != tuple(
            sorted(expected_catalog_candidates, key=lambda value: value.digest)
        ):
            raise NaturalTilingSearchInputError("Search catalog does not match maximal generated candidates.")
        if self.canonical_schema_version != CANONICAL_NATURAL_TILING_SEARCH_SCHEMA:
            raise NaturalTilingSearchInputError("Unsupported natural-tiling-search schema.")
        if self.digest_algorithm != NATURAL_TILING_SEARCH_DIGEST_ALGORITHM:
            raise NaturalTilingSearchInputError("Unsupported natural-tiling-search digest algorithm.")
        object.__setattr__(self, "face_orbits", orbits)
        object.__setattr__(self, "attempted_selection_count", attempted)
        object.__setattr__(self, "compatible_selection_count", compatible)
        object.__setattr__(self, "constructed_selection_count", constructed)
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "rejections", rejections)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "unresolved_reasons", unresolved)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise NaturalTilingSearchInputError("Stored natural-tiling-search digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NaturalTilingSearchResult) and self.digest == other.digest

    @property
    def search_complete(self) -> bool:
        return self.status is NaturalTilingSearchStatus.COMPLETE

    @property
    def certified_catalog(self) -> NaturalTilingCatalog | None:
        return self.catalog if self.search_complete else None

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "periodic_net_view_digest": self.periodic_net_view_digest,
            "primitive_ring_catalog_digest": self.primitive_ring_catalog_digest,
            "master_cell_complex_digest": self.master_cell_complex_digest,
            "master_partition_certificate_digest": self.master_partition_certificate_digest,
            "strength_catalog_digest": self.strength_catalog_digest,
            "compatibility_system_digest": self.compatibility_system_digest,
            "face_orbits": [value.to_dict() for value in self.face_orbits],
            "attempted_selection_count": self.attempted_selection_count,
            "compatible_selection_count": self.compatible_selection_count,
            "constructed_selection_count": self.constructed_selection_count,
            "candidates": [value.to_dict() for value in self.candidates],
            "rejections": [value.to_dict() for value in self.rejections],
            "status": self.status.value,
            "unresolved_reasons": list(self.unresolved_reasons),
            "catalog": self.catalog.to_dict(),
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        view: PeriodicNetView,
        discovery: PeriodicNetSymmetryDiscovery,
        embedding: PeriodicNetEmbedding,
        ring_index: PrimitiveRingIndex,
        strength_catalog: RingStrengthCatalog,
        face_certificates: Sequence[FacePlacementCertificate],
        master_witnesses: Sequence[FaceEmbeddingWitness],
        compatibility: FaceCompatibilityConstraintSystem,
        master_complex: PeriodicCellComplex,
        master_partition: PeriodicPartitionCertificate,
        resources: NaturalTilingSearchResources | None = None,
        symmetry_resources: NaturalTilingSymmetryResources | None = None,
        partition_resources: PeriodicPartitionResources | None = None,
    ) -> "NaturalTilingSearchResult":
        """Replay the complete finite search and reject altered persistence."""

        rebuilt = search_natural_tilings_from_master_refinement(
            view,
            discovery,
            embedding,
            ring_index,
            strength_catalog,
            face_certificates,
            master_witnesses,
            compatibility,
            master_complex,
            master_partition,
            resources=resources,
            symmetry_resources=symmetry_resources,
            partition_resources=partition_resources,
        )
        if rebuilt.to_dict() != dict(payload):
            raise NaturalTilingSearchSerializationError(
                "Serialized natural-tiling search is not canonical for the supplied sources."
            )
        return rebuilt


class _SelectionFailure(Exception):
    def __init__(self, kind: NaturalTilingSearchRejectionKind, reason: str):
        super().__init__(reason)
        self.kind = kind
        self.reason = reason


def _validate_sources(
    view: PeriodicNetView,
    discovery: PeriodicNetSymmetryDiscovery,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    strength_catalog: RingStrengthCatalog,
    certificates: Sequence[FacePlacementCertificate],
    witnesses: Sequence[FaceEmbeddingWitness],
    compatibility: FaceCompatibilityConstraintSystem,
    master_complex: PeriodicCellComplex,
    master_partition: PeriodicPartitionCertificate,
) -> tuple[tuple[FacePlacementCertificate, ...], tuple[FaceEmbeddingWitness, ...]]:
    if not isinstance(view, PeriodicNetView):
        raise NaturalTilingSearchInputError("view must be a PeriodicNetView.")
    if not isinstance(discovery, PeriodicNetSymmetryDiscovery) or discovery.ring_symmetry is None:
        raise NaturalTilingSearchInputError("A complete source-bound symmetry discovery is required.")
    if not isinstance(embedding, PeriodicNetEmbedding):
        raise NaturalTilingSearchInputError("embedding must be a PeriodicNetEmbedding.")
    if not isinstance(ring_index, PrimitiveRingIndex):
        raise NaturalTilingSearchInputError("ring_index must be a PrimitiveRingIndex.")
    if not isinstance(strength_catalog, RingStrengthCatalog):
        raise NaturalTilingSearchInputError("strength_catalog must be a RingStrengthCatalog.")
    if not isinstance(compatibility, FaceCompatibilityConstraintSystem):
        raise NaturalTilingSearchInputError("compatibility must be a FaceCompatibilityConstraintSystem.")
    if not isinstance(master_complex, PeriodicCellComplex):
        raise NaturalTilingSearchInputError("master_complex must be a PeriodicCellComplex.")
    if not isinstance(master_partition, PeriodicPartitionCertificate):
        raise NaturalTilingSearchInputError("master_partition must be a PeriodicPartitionCertificate.")
    if (
        discovery.periodic_net_view_digest != view.digest
        or discovery.topology_graph_digest != view.source_graph_digest
        or embedding.periodic_net_view_digest != view.digest
        or embedding.topology_graph_digest != view.source_graph_digest
        or ring_index.topology_graph_digest != view.source_graph_digest
        or strength_catalog.topology_graph_digest != view.source_graph_digest
        or strength_catalog.primitive_ring_catalog_digest != ring_index.catalog_digest
        or master_complex.periodic_net_view_digest != view.digest
        or master_complex.topology_graph_digest != view.source_graph_digest
        or master_complex.periodic_net_embedding_digest != embedding.digest
        or master_complex.primitive_ring_catalog_digest != ring_index.catalog_digest
        or master_partition.periodic_cell_complex_digest != master_complex.digest
        or master_partition.periodic_net_embedding_digest != embedding.digest
    ):
        raise NaturalTilingSearchInputError("Stage-10B sources do not share exact identities.")
    certs = tuple(certificates)
    selected = tuple(witnesses)
    if len(certs) != len(master_complex.face_placements) or len(selected) != len(certs):
        raise NaturalTilingSearchInputError("Master face certificates and witnesses must align with the master complex.")
    by_face = {
        certificate.face_placement.digest: (certificate, witness)
        for certificate, witness in zip(certs, selected, strict=True)
    }
    try:
        ordered = tuple(by_face[face.digest] for face in master_complex.face_placements)
    except KeyError as exc:
        raise NaturalTilingSearchInputError("A master scientific face lacks its source certificate.") from exc
    certs = tuple(value[0] for value in ordered)
    selected = tuple(value[1] for value in ordered)
    if tuple(value.digest for value in selected) != master_complex.construction_witness_digests:
        raise NaturalTilingSearchInputError("Master witnesses disagree with the certified master complex.")
    if compatibility.face_certificate_digests != tuple(sorted(value.digest for value in certs)):
        raise NaturalTilingSearchInputError("Compatibility system must cover exactly the master face certificates.")
    assignments = frozenset(compatibility.assignments)
    for certificate, witness in zip(certs, selected, strict=True):
        assignment = FaceWitnessAssignment(
            certificate.face_placement.digest,
            witness.witness_id,
            witness.digest,
        )
        if assignment not in assignments:
            raise NaturalTilingSearchInputError("A master witness is absent from the compatibility domain.")
    action = build_periodic_cell_complex_symmetry_action(
        master_complex,
        discovery.symmetry,
        discovery.ring_symmetry,
    )
    if not action.preserved:
        raise NaturalTilingSearchInputError("The master refinement is not invariant under the full net symmetry group.")
    return certs, selected


def _strength_by_ring_key(strength_catalog: RingStrengthCatalog) -> dict[PrimitiveRingKey, RingStrengthStatus]:
    result: dict[PrimitiveRingKey, RingStrengthStatus] = {}
    for value in strength_catalog.results:
        key = value.target_placement.ring_key
        previous = result.get(key)
        if previous is not None and previous is not value.status:
            raise NaturalTilingSearchInputError("Conflicting strength results exist for one primitive ring key.")
        result[key] = value.status
    return result


def _face_orbits(
    master_complex: PeriodicCellComplex,
    discovery: PeriodicNetSymmetryDiscovery,
    strength_catalog: RingStrengthCatalog,
    *,
    symmetry_resources: NaturalTilingSymmetryResources | None,
) -> tuple[NaturalFaceOrbit, ...]:
    ring_symmetry = discovery.ring_symmetry
    assert ring_symmetry is not None
    action = build_periodic_cell_complex_symmetry_action(
        master_complex,
        discovery.symmetry,
        ring_symmetry,
        resources=symmetry_resources,
    )
    if not action.preserved:
        raise NaturalTilingSearchInputError("The master refinement is not full-symmetry invariant.")
    images: list[set[int]] = [set((index,)) for index in range(len(master_complex.face_placements))]
    for operation in action.operation_results:
        for source, image in enumerate(operation.face_images):
            images[source].add(image.target_cell_index)
    remaining = set(range(len(images)))
    partitions: list[tuple[int, ...]] = []
    while remaining:
        seed = min(remaining)
        orbit = tuple(sorted(images[seed]))
        if not set(orbit).issubset(remaining):
            raise NaturalTilingSearchInvariantError("Face-image sets do not form a symmetry partition.")
        if any(images[value] != set(orbit) for value in orbit):
            raise NaturalTilingSearchInvariantError("Face symmetry relation is not orbit-consistent.")
        remaining.difference_update(orbit)
        partitions.append(orbit)
    strength = _strength_by_ring_key(strength_catalog)
    result = []
    for orbit_index, face_indices in enumerate(partitions):
        statuses = tuple(
            strength.get(master_complex.face_placements[index].ring_placement.ring_key)
            for index in face_indices
        )
        if statuses and all(value is RingStrengthStatus.STRONG_IN_DOMAIN for value in statuses):
            orbit_strength = NaturalFaceOrbitStrength.STRONG_SELECTABLE
        elif statuses and all(value is RingStrengthStatus.WEAK_CERTIFIED for value in statuses):
            orbit_strength = NaturalFaceOrbitStrength.WEAK_EXCLUDED
        elif any(value is RingStrengthStatus.WEAK_CERTIFIED for value in statuses) and any(
            value is RingStrengthStatus.STRONG_IN_DOMAIN for value in statuses
        ):
            raise NaturalTilingSearchInvariantError("A full symmetry orbit has inconsistent certified strength states.")
        else:
            orbit_strength = NaturalFaceOrbitStrength.UNRESOLVED
        result.append(
            NaturalFaceOrbit(
                orbit_index,
                face_indices,
                tuple(master_complex.face_placements[index].digest for index in face_indices),
                tuple(master_complex.face_placements[index].ring_placement.ring_key for index in face_indices),
                orbit_strength,
            )
        )
    return tuple(result)


def _selection(
    orbit_indices: Sequence[int],
    face_orbits: Sequence[NaturalFaceOrbit],
    master_complex: PeriodicCellComplex,
    witnesses: Sequence[FaceEmbeddingWitness],
) -> NaturalFaceSelection:
    selected_orbits = tuple(sorted(set(int(value) for value in orbit_indices)))
    face_indices = tuple(
        sorted(
            index
            for orbit_index in selected_orbits
            for index in face_orbits[orbit_index].face_indices
        )
    )
    return NaturalFaceSelection(
        selected_orbits,
        face_indices,
        tuple(master_complex.face_placements[index].digest for index in face_indices),
        tuple(witnesses[index].digest for index in face_indices),
    )


def _selected_assignments(
    selection: NaturalFaceSelection,
    certificates: Sequence[FacePlacementCertificate],
    witnesses: Sequence[FaceEmbeddingWitness],
) -> frozenset[FaceWitnessAssignment]:
    return frozenset(
        FaceWitnessAssignment(
            certificates[index].face_placement.digest,
            witnesses[index].witness_id,
            witnesses[index].digest,
        )
        for index in selection.selected_face_indices
    )


def _compatibility_state(
    selection: NaturalFaceSelection,
    certificates: Sequence[FacePlacementCertificate],
    witnesses: Sequence[FaceEmbeddingWitness],
    compatibility: FaceCompatibilityConstraintSystem,
) -> tuple[bool, bool, str | None]:
    assignments = _selected_assignments(selection, certificates, witnesses)
    for constraint in compatibility.constraints:
        if set(constraint.assignments).issubset(assignments):
            if constraint.kind is FaceConstraintKind.UNRESOLVED:
                return False, True, constraint.reason
            return False, False, constraint.reason
    return True, False, None


def _subset_compatibility(
    selection: NaturalFaceSelection,
    certificates: Sequence[FacePlacementCertificate],
    compatibility: FaceCompatibilityConstraintSystem,
) -> FaceCompatibilityConstraintSystem:
    face_indices = set(selection.selected_face_indices)
    face_digests = {certificates[index].face_placement.digest for index in face_indices}
    witness_digests = {
        assignment.witness_digest
        for assignment in compatibility.assignments
        if assignment.face_placement_digest in face_digests
    }
    assignments = tuple(
        value
        for value in compatibility.assignments
        if value.face_placement_digest in face_digests
    )
    pair_certificates = tuple(
        value
        for value in compatibility.pair_certificates
        if value.left_witness_digest in witness_digests
        and value.right_witness_digest in witness_digests
    )
    constraints = tuple(
        value
        for value in compatibility.constraints
        if all(item.face_placement_digest in face_digests for item in value.assignments)
    )
    face_relations = tuple(
        value
        for value in compatibility.face_symmetry_relations
        if value.source_face_digest in face_digests and value.target_face_digest in face_digests
    )
    witness_relations = tuple(
        value
        for value in compatibility.witness_symmetry_relations
        if value.source_witness_digest in witness_digests and value.target_witness_digest in witness_digests
    )
    return FaceCompatibilityConstraintSystem(
        tuple(certificates[index].digest for index in sorted(face_indices)),
        assignments,
        pair_certificates,
        constraints,
        face_relations,
        witness_relations,
    )


def _facet_translation(
    master_partition: PeriodicPartitionCertificate,
    pair_index: int,
) -> LatticeShift:
    pair = master_partition.facet_pairs[pair_index]
    left = master_partition.tetrahedra[pair.tetrahedron_i]
    right = master_partition.tetrahedra[pair.tetrahedron_j]
    _, left_anchor = _canonical_ref_facet(_facet_vertices(left, pair.local_facet_i))
    _, right_anchor = _canonical_ref_facet(_facet_vertices(right, pair.local_facet_j))
    return subtract_shift(left_anchor, right_anchor)


def _component_offsets(
    master_partition: PeriodicPartitionCertificate,
    selected_faces: frozenset[int],
    resources: NaturalTilingSearchResources,
) -> tuple[tuple[int, LatticeShift], ...]:
    adjacency: list[list[tuple[int, LatticeShift]]] = [
        [] for _ in master_partition.tetrahedra
    ]
    arc_count = 0
    for pair_index, pair in enumerate(master_partition.facet_pairs):
        if pair.kind is PartitionFacetKind.SCIENTIFIC_INTERFACE and pair.face_index in selected_faces:
            continue
        translation = _facet_translation(master_partition, pair_index)
        adjacency[pair.tetrahedron_i].append((pair.tetrahedron_j, translation))
        adjacency[pair.tetrahedron_j].append((pair.tetrahedron_i, _negate_shift(translation)))
        arc_count += 2
    if arc_count > resources.max_connectivity_arcs:
        raise NaturalTilingSearchResourceError(
            "Master-refinement connectivity exceeds max_connectivity_arcs."
        )
    assignments: list[tuple[int, LatticeShift] | None] = [None] * len(adjacency)
    component_index = 0
    for seed in range(len(adjacency)):
        if assignments[seed] is not None:
            continue
        assignments[seed] = (component_index, ZERO_SHIFT)
        queue: deque[int] = deque((seed,))
        while queue:
            source = queue.popleft()
            source_component, source_shift = assignments[source]  # type: ignore[misc]
            for target, translation in adjacency[source]:
                target_shift = add_shift(source_shift, translation)
                current = assignments[target]
                if current is None:
                    assignments[target] = (source_component, target_shift)
                    queue.append(target)
                elif current != (source_component, target_shift):
                    raise _SelectionFailure(
                        NaturalTilingSearchRejectionKind.NONCOMPACT_TILE_COMPONENT,
                        "Merging omitted interfaces creates a lifted component with a nonzero translation cycle.",
                    )
        component_index += 1
    return tuple(value for value in assignments if value is not None)


def _master_side_sign(
    master_complex: PeriodicCellComplex,
    master_partition: PeriodicPartitionCertificate,
    pair_index: int,
) -> int:
    pair = master_partition.facet_pairs[pair_index]
    assert pair.face_index is not None and pair.face_image_shift is not None
    left_tile = master_partition.tetrahedra[pair.tetrahedron_i].tile_placement
    relative_shift = subtract_shift(pair.face_image_shift, left_tile.image_shift)
    matches = tuple(
        term.coefficient
        for term in master_complex.boundary_3.columns[left_tile.tile_index]
        if term.cell_index == pair.face_index and term.image_shift == relative_shift
    )
    if len(matches) != 1:
        raise NaturalTilingSearchInvariantError(
            "Master interface facet cannot be matched to one oriented scientific tile side."
        )
    return matches[0]


def _coarsen_master_refinement(
    view: PeriodicNetView,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    certificates: Sequence[FacePlacementCertificate],
    witnesses: Sequence[FaceEmbeddingWitness],
    compatibility: FaceCompatibilityConstraintSystem,
    master_complex: PeriodicCellComplex,
    master_partition: PeriodicPartitionCertificate,
    selection: NaturalFaceSelection,
    *,
    resources: NaturalTilingSearchResources,
    partition_resources: PeriodicPartitionResources | None,
) -> tuple[PeriodicCellComplex, PeriodicPartitionCertificate]:
    selected_faces = frozenset(selection.selected_face_indices)
    offsets = _component_offsets(master_partition, selected_faces, resources)
    old_to_new_face = {
        old_index: new_index
        for new_index, old_index in enumerate(selection.selected_face_indices)
    }
    new_tetrahedra = tuple(
        PeriodicTetrahedron(
            tetrahedron.tetrahedron_index,
            tetrahedron.vertices,
            TilePlacementRef(
                offsets[tetrahedron.tetrahedron_index][0],
                _negate_shift(offsets[tetrahedron.tetrahedron_index][1]),
            ),
        )
        for tetrahedron in master_partition.tetrahedra
    )
    coverage_by_pair = {
        value.facet_pair_index: value for value in master_partition.face_triangle_coverage
    }
    expected_triangles = {
        face_index: set(range(len(witnesses[face_index].triangles)))
        for face_index in selected_faces
    }
    side_records: dict[
        tuple[int, int, LatticeShift], list[tuple[int, int]]
    ] = defaultdict(list)
    for pair_index, pair in enumerate(master_partition.facet_pairs):
        if pair.kind is not PartitionFacetKind.SCIENTIFIC_INTERFACE or pair.face_index not in selected_faces:
            continue
        assert pair.face_index is not None and pair.face_image_shift is not None
        translation = _facet_translation(master_partition, pair_index)
        left_component, left_offset = offsets[pair.tetrahedron_i]
        right_component, right_offset = offsets[pair.tetrahedron_j]
        left_tile = TilePlacementRef(left_component, _negate_shift(left_offset))
        right_tile = TilePlacementRef(
            right_component,
            add_shift(_negate_shift(right_offset), translation),
        )
        if left_tile == right_tile:
            raise _SelectionFailure(
                NaturalTilingSearchRejectionKind.NONSEPARATING_SELECTED_FACE,
                "A selected ring surface does not separate two translated tile placements.",
            )
        coverage = coverage_by_pair.get(pair_index)
        if coverage is None or coverage.face_index != pair.face_index:
            raise NaturalTilingSearchInvariantError(
                "Master scientific interface lacks exact witness-triangle coverage."
            )
        left_sign = _master_side_sign(master_complex, master_partition, pair_index)
        for tile, sign in ((left_tile, left_sign), (right_tile, -left_sign)):
            relative_shift = subtract_shift(pair.face_image_shift, tile.image_shift)
            side_records[
                (tile.tile_index, old_to_new_face[pair.face_index], relative_shift)
            ].append((coverage.triangle_index, sign))
    component_count = 1 + max(value[0] for value in offsets)
    shells: list[PeriodicTileShell] = []
    selected_face_order = selection.selected_face_indices
    for tile_index in range(component_count):
        terms: list[TranslatedCellTerm] = []
        for (record_tile, new_face, relative_shift), records in sorted(side_records.items()):
            if record_tile != tile_index:
                continue
            old_face = selected_face_order[new_face]
            triangle_indices = {triangle_index for triangle_index, _ in records}
            signs = {sign for _, sign in records}
            if triangle_indices != expected_triangles[old_face] or len(records) != len(triangle_indices):
                raise NaturalTilingSearchInvariantError(
                    "A reconstructed tile side does not cover one selected witness exactly once."
                )
            if len(signs) != 1:
                raise NaturalTilingSearchInvariantError(
                    "A reconstructed tile side has inconsistent triangle orientations."
                )
            terms.append(
                TranslatedCellTerm(new_face, relative_shift, next(iter(signs)))
            )
        if not terms:
            raise _SelectionFailure(
                NaturalTilingSearchRejectionKind.INVALID_CELL_COMPLEX,
                "A reconstructed tile component has no selected boundary faces.",
            )
        shells.append(PeriodicTileShell(tile_index, tuple(terms), f"natural-tile-{tile_index}"))
    selected_certificates = tuple(certificates[index] for index in selection.selected_face_indices)
    selected_witnesses = tuple(witnesses[index] for index in selection.selected_face_indices)
    subset_compatibility = _subset_compatibility(selection, certificates, compatibility)
    try:
        complex_ = build_periodic_cell_complex(
            view,
            embedding,
            ring_index,
            selected_certificates,
            selected_witnesses,
            tuple(shells),
            compatibility=subset_compatibility,
        )
    except PeriodicCellComplexError as exc:
        raise _SelectionFailure(
            NaturalTilingSearchRejectionKind.INVALID_CELL_COMPLEX,
            str(exc),
        ) from exc
    try:
        partition = certify_periodic_tetrahedral_partition(
            complex_,
            embedding,
            ring_index,
            selected_witnesses,
            master_partition.auxiliary_vertices,
            new_tetrahedra,
            resources=partition_resources,
        )
    except PeriodicCellComplexResourceError as exc:
        raise NaturalTilingSearchResourceError(str(exc)) from exc
    except (PeriodicCellComplexInvariantError, PeriodicCellComplexError) as exc:
        raise _SelectionFailure(
            NaturalTilingSearchRejectionKind.INVALID_PARTITION,
            str(exc),
        ) from exc
    return complex_, partition


def maximal_face_selections(
    selections: Sequence[NaturalFaceSelection],
) -> tuple[NaturalFaceSelection, ...]:
    """Return all inclusion-maximal selections without enumeration-order ties."""

    by_digest = {value.digest: value for value in selections}
    values = tuple(sorted(by_digest.values(), key=lambda value: value.digest))
    sets = {value.digest: frozenset(value.selected_orbit_indices) for value in values}
    return tuple(
        value
        for value in values
        if not any(
            sets[value.digest] < sets[other.digest]
            for other in values
            if other.digest != value.digest
        )
    )


def search_natural_tilings_from_master_refinement(
    view: PeriodicNetView,
    discovery: PeriodicNetSymmetryDiscovery,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    strength_catalog: RingStrengthCatalog,
    face_certificates: Sequence[FacePlacementCertificate],
    master_witnesses: Sequence[FaceEmbeddingWitness],
    compatibility: FaceCompatibilityConstraintSystem,
    master_complex: PeriodicCellComplex,
    master_partition: PeriodicPartitionCertificate,
    *,
    resources: NaturalTilingSearchResources | None = None,
    symmetry_resources: NaturalTilingSymmetryResources | None = None,
    partition_resources: PeriodicPartitionResources | None = None,
) -> NaturalTilingSearchResult:
    """Enumerate the complete bounded coarsening family of one master refinement.

    The master partition contains every cut surface in the finite family.  The
    search enumerates all nonempty subsets of certified-strong face orbits,
    prunes fixed-witness incompatibilities, reconstructs exact tile components,
    and retains every inclusion-maximal viable splitting.
    """

    active = resources or NaturalTilingSearchResources()
    certificates, witnesses = _validate_sources(
        view,
        discovery,
        embedding,
        ring_index,
        strength_catalog,
        face_certificates,
        master_witnesses,
        compatibility,
        master_complex,
        master_partition,
    )
    face_orbits = _face_orbits(
        master_complex,
        discovery,
        strength_catalog,
        symmetry_resources=symmetry_resources,
    )
    selectable = tuple(
        value.orbit_index
        for value in face_orbits
        if value.strength is NaturalFaceOrbitStrength.STRONG_SELECTABLE
    )
    if len(selectable) > active.max_face_orbits:
        raise NaturalTilingSearchResourceError(
            "Selectable face-orbit count exceeds max_face_orbits."
        )
    selection_count = (1 << len(selectable)) - 1
    if selection_count > active.max_face_selections:
        raise NaturalTilingSearchResourceError(
            "Symmetry-closed face-selection family exceeds max_face_selections."
        )
    unresolved_reasons = []
    for orbit in face_orbits:
        if orbit.strength is NaturalFaceOrbitStrength.UNRESOLVED:
            unresolved_reasons.append(
                f"face orbit {orbit.orbit_index} has unresolved bounded strength"
            )
    attempted = 0
    compatible_count = 0
    constructed_count = 0
    rejections: list[NaturalTilingSearchRejection] = []
    viable: list[NaturalTilingSearchCandidate] = []
    for size in range(1, len(selectable) + 1):
        for chosen in itertools.combinations(selectable, size):
            attempted += 1
            selection = _selection(chosen, face_orbits, master_complex, witnesses)
            compatible, unresolved, reason = _compatibility_state(
                selection, certificates, witnesses, compatibility
            )
            if not compatible:
                kind = (
                    NaturalTilingSearchRejectionKind.UNRESOLVED_COMPATIBILITY
                    if unresolved
                    else NaturalTilingSearchRejectionKind.FORBIDDEN_COMPATIBILITY
                )
                rejections.append(
                    NaturalTilingSearchRejection(chosen, kind, reason or kind.value)
                )
                if unresolved:
                    unresolved_reasons.append(
                        f"selection {chosen} retains unresolved witness compatibility"
                    )
                continue
            compatible_count += 1
            if compatible_count > active.max_candidate_constructions:
                raise NaturalTilingSearchResourceError(
                    "Candidate construction count exceeds max_candidate_constructions."
                )
            try:
                complex_, partition = _coarsen_master_refinement(
                    view,
                    embedding,
                    ring_index,
                    certificates,
                    witnesses,
                    compatibility,
                    master_complex,
                    master_partition,
                    selection,
                    resources=active,
                    partition_resources=partition_resources,
                )
            except _SelectionFailure as exc:
                rejections.append(NaturalTilingSearchRejection(chosen, exc.kind, exc.reason))
                continue
            constructed_count += 1
            selected_certificates = tuple(
                certificates[index] for index in selection.selected_face_indices
            )
            selected_witnesses = tuple(
                witnesses[index] for index in selection.selected_face_indices
            )
            subset_compatibility = _subset_compatibility(
                selection, certificates, compatibility
            )
            candidate = certify_natural_tiling_candidate(
                view,
                discovery,
                ring_index,
                strength_catalog,
                selected_certificates,
                selected_witnesses,
                subset_compatibility,
                complex_,
                partition,
                symmetry_resources=symmetry_resources,
            )
            if candidate.eligibility is CandidateEligibility.INELIGIBLE:
                rejections.append(
                    NaturalTilingSearchRejection(
                        chosen,
                        NaturalTilingSearchRejectionKind.INELIGIBLE_CERTIFICATION,
                        "; ".join(candidate.certification.rejection_reasons)
                        or "Stage-10A certification rejected the generated complex.",
                    )
                )
                continue
            viable.append(
                NaturalTilingSearchCandidate(selection, complex_, partition, candidate)
            )
    maximal_selections = maximal_face_selections(tuple(value.selection for value in viable))
    maximal_digests = {value.digest for value in maximal_selections}
    maximal_candidates = []
    for value in viable:
        if value.selection.digest in maximal_digests:
            maximal_candidates.append(value)
        else:
            rejections.append(
                NaturalTilingSearchRejection(
                    value.selection.selected_orbit_indices,
                    NaturalTilingSearchRejectionKind.NONMAXIMAL_SPLITTING,
                    "A strict compatible valid superset adds further admissible strong-ring cuts.",
                )
            )
    catalog = build_natural_tiling_catalog(
        tuple(value.natural_tiling_candidate for value in maximal_candidates),
        periodic_net_view_digest=view.digest,
        primitive_ring_catalog_digest=ring_index.catalog_digest,
    )
    status = (
        NaturalTilingSearchStatus.COMPLETE
        if not unresolved_reasons
        else NaturalTilingSearchStatus.UNRESOLVED
    )
    return NaturalTilingSearchResult(
        periodic_net_view_digest=view.digest,
        primitive_ring_catalog_digest=ring_index.catalog_digest,
        master_cell_complex_digest=master_complex.digest,
        master_partition_certificate_digest=master_partition.digest,
        strength_catalog_digest=strength_catalog.digest,
        compatibility_system_digest=compatibility.digest,
        face_orbits=face_orbits,
        attempted_selection_count=attempted,
        compatible_selection_count=compatible_count,
        constructed_selection_count=constructed_count,
        candidates=tuple(maximal_candidates),
        rejections=tuple(rejections),
        status=status,
        unresolved_reasons=tuple(unresolved_reasons),
        catalog=catalog,
    )


__all__ = [
    "CANONICAL_NATURAL_TILING_SEARCH_SCHEMA",
    "NATURAL_TILING_SEARCH_DIGEST_ALGORITHM",
    "NaturalFaceOrbit",
    "NaturalFaceOrbitStrength",
    "NaturalFaceSelection",
    "NaturalTilingSearchCandidate",
    "NaturalTilingSearchError",
    "NaturalTilingSearchInputError",
    "NaturalTilingSearchInvariantError",
    "NaturalTilingSearchRejection",
    "NaturalTilingSearchRejectionKind",
    "NaturalTilingSearchResourceError",
    "NaturalTilingSearchResources",
    "NaturalTilingSearchResult",
    "NaturalTilingSearchSerializationError",
    "NaturalTilingSearchStatus",
    "maximal_face_selections",
    "search_natural_tilings_from_master_refinement",
]
