"""Stage-10A natural-tiling candidate certification and properness.

This module does not search for natural faces or split provisional tiles.  It
certifies caller-proposed Stage-9 complexes along independent scientific axes and
checks properness against a *complete* exact periodic-net symmetry discovery.
Auxiliary face triangulations and tetrahedral partition meshes remain evidence;
they are excluded from scientific tiling identity.

The properness requirement and natural-tiling orchestration follow the framework
of Blatov, Delgado-Friedrichs, O'Keeffe, and Proserpio (2007).  mdstats adds exact
translation-labelled face/tile actions, finite group-action validation,
source-bound multidimensional certification, and ambiguity-preserving catalogs.

Reference
---------
V. A. Blatov, O. Delgado-Friedrichs, M. O'Keeffe, and D. M. Proserpio,
"Three-periodic nets and tilings: natural tilings for nets", Acta Cryst. A 63,
418-425 (2007), doi:10.1107/S0108767307038287.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from numbers import Integral
from typing import Any, Iterable, Mapping, Sequence

from ._periodic_graph import LatticeShift, add_shift, matvec_shift, subtract_shift
from .face_candidates import (
    FaceCompatibilityConstraintSystem,
    FaceConstraintKind,
    FaceEmbeddingWitness,
    FacePlacementCertificate,
    FacePlacementStatus,
    FaceWitnessAssignment,
    map_face_placement,
)
from .net_symmetry import PeriodicNetSymmetry
from .net_symmetry_discovery import PeriodicNetSymmetryDiscovery
from .periodic_cell_complex import (
    PeriodicCellComplex,
    PeriodicPartitionCertificate,
    PeriodicTileShell,
    TranslatedCellTerm,
)
from .periodic_net_view import PeriodicNetView
from .primitive_ring import PrimitiveRingFamily, PrimitiveRingKey
from .primitive_ring_index import PrimitiveRingIndex
from .primitive_ring_symmetry import PrimitiveRingSymmetryIndex
from .ring_strength import RingStrengthCatalog, RingStrengthStatus

CANONICAL_CELL_COMPLEX_SYMMETRY_SCHEMA = "mdstats.cell-complex-symmetry-action.v1"
CANONICAL_NATURAL_TILING_CANDIDATE_SCHEMA = "mdstats.natural-tiling-candidate.v1"
CANONICAL_NATURAL_TILING_CATALOG_SCHEMA = "mdstats.natural-tiling-catalog.v1"
NATURAL_TILING_DIGEST_ALGORITHM = "sha256-canonical-json-v1"
ZERO_SHIFT: LatticeShift = (0, 0, 0)


class NaturalTilingError(ValueError):
    """Base exception for Stage-10A natural-tiling certification."""


class NaturalTilingInputError(NaturalTilingError):
    """Raised when source identities or explicit candidate evidence disagree."""


class NaturalTilingInvariantError(NaturalTilingError):
    """Raised when a purported exact symmetry action violates group algebra."""


class NaturalTilingResourceError(NaturalTilingError):
    """Raised before a declared finite validation bound is exceeded."""


class NaturalTilingSerializationError(NaturalTilingError):
    """Raised when persistent Stage-10A data are altered or noncanonical."""


class CertificationState(str, Enum):
    """Independent certification state for one eligibility dimension."""

    CERTIFIED = "certified"
    REJECTED = "rejected"
    UNRESOLVED = "unresolved"


class PropernessStatus(str, Enum):
    """Exact properness result relative to the declared full net symmetry."""

    CERTIFIED_PROPER = "certified_proper"
    CERTIFIED_IMPROPER = "certified_improper"
    UNRESOLVED = "unresolved"


class CandidateEligibility(str, Enum):
    """Aggregate eligibility without erasing independent certification axes."""

    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNRESOLVED = "unresolved"


class NaturalTilingOutcomeKind(str, Enum):
    """Multiplicity of accepted scientific natural-tiling candidates."""

    NONE = "none"
    UNIQUE = "unique"
    MULTIPLE = "multiple"


class SymmetryOperationStatus(str, Enum):
    """Whether one exact net automorphism preserves the scientific complex."""

    PRESERVED = "preserved"
    NOT_PRESERVED = "not_preserved"


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _sha(value: object, *, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise NaturalTilingInputError(f"{name} must be a SHA-256 digest.")
    return value


def _nonnegative(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        raise NaturalTilingInputError(f"{name} must be a nonnegative integer.")
    return int(value)


def _positive(value: object, *, name: str) -> int:
    result = _nonnegative(value, name=name)
    if result == 0:
        raise NaturalTilingInputError(f"{name} must be positive.")
    return result


def _combine_terms(terms: Iterable[TranslatedCellTerm]) -> tuple[TranslatedCellTerm, ...]:
    coefficients: dict[tuple[int, LatticeShift], int] = {}
    for term in terms:
        key = (term.cell_index, term.image_shift)
        coefficients[key] = coefficients.get(key, 0) + term.coefficient
    return tuple(
        TranslatedCellTerm(cell_index, shift, coefficient)
        for (cell_index, shift), coefficient in sorted(coefficients.items())
        if coefficient
    )


@dataclass(frozen=True, order=True, slots=True)
class OrientedCellImage:
    """Image of one oriented quotient cell representative modulo translation."""

    target_cell_index: int
    image_shift: LatticeShift
    orientation: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_cell_index",
            _nonnegative(self.target_cell_index, name="target_cell_index"),
        )
        shift = tuple(int(value) for value in self.image_shift)
        if len(shift) != 3:
            raise NaturalTilingInputError("image_shift must contain three integers.")
        if self.orientation not in (-1, 1):
            raise NaturalTilingInputError("orientation must be +1 or -1.")
        object.__setattr__(self, "image_shift", shift)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_cell_index": self.target_cell_index,
            "image_shift": list(self.image_shift),
            "orientation": self.orientation,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "OrientedCellImage":
        try:
            return cls(
                int(payload["target_cell_index"]),
                tuple(int(value) for value in payload["image_shift"]),
                int(payload["orientation"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise NaturalTilingSerializationError(
                "Invalid OrientedCellImage payload."
            ) from exc


@dataclass(frozen=True, slots=True)
class CellComplexSymmetryOperation:
    """Scientific face/tile action for one normalized net automorphism."""

    operation_index: int
    status: SymmetryOperationStatus
    face_images: tuple[OrientedCellImage, ...] = ()
    tile_images: tuple[OrientedCellImage, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        index = _nonnegative(self.operation_index, name="operation_index")
        status = SymmetryOperationStatus(self.status)
        faces = tuple(self.face_images)
        tiles = tuple(self.tile_images)
        if any(not isinstance(value, OrientedCellImage) for value in (*faces, *tiles)):
            raise NaturalTilingInputError("Symmetry image tables contain an invalid record.")
        if status is SymmetryOperationStatus.PRESERVED:
            if self.reason is not None:
                raise NaturalTilingInputError("A preserved operation cannot carry a failure reason.")
        else:
            if not self.reason:
                raise NaturalTilingInputError("A non-preserving operation requires a reason.")
            if faces or tiles:
                raise NaturalTilingInputError("A non-preserving operation cannot publish a partial action.")
        object.__setattr__(self, "operation_index", index)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "face_images", faces)
        object.__setattr__(self, "tile_images", tiles)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_index": self.operation_index,
            "status": self.status.value,
            "face_images": [value.to_dict() for value in self.face_images],
            "tile_images": [value.to_dict() for value in self.tile_images],
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CellComplexSymmetryOperation":
        try:
            return cls(
                int(payload["operation_index"]),
                SymmetryOperationStatus(str(payload["status"])),
                tuple(OrientedCellImage.from_dict(value) for value in payload["face_images"]),
                tuple(OrientedCellImage.from_dict(value) for value in payload["tile_images"]),
                None if payload.get("reason") is None else str(payload["reason"]),
            )
        except NaturalTilingError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise NaturalTilingSerializationError(
                "Invalid CellComplexSymmetryOperation payload."
            ) from exc


@dataclass(frozen=True, slots=True, eq=False)
class PeriodicCellComplexSymmetryAction:
    """Exact action, or explicit failure to act, on one scientific complex."""

    periodic_net_symmetry_digest: str
    primitive_ring_symmetry_digest: str
    periodic_cell_complex_digest: str
    operation_results: tuple[CellComplexSymmetryOperation, ...]
    composition_check_count: int
    canonical_schema_version: str = CANONICAL_CELL_COMPLEX_SYMMETRY_SCHEMA
    digest_algorithm: str = NATURAL_TILING_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        for name in (
            "periodic_net_symmetry_digest",
            "primitive_ring_symmetry_digest",
            "periodic_cell_complex_digest",
        ):
            _sha(getattr(self, name), name=name)
        results = tuple(self.operation_results)
        if tuple(value.operation_index for value in results) != tuple(range(len(results))):
            raise NaturalTilingInputError("operation_results must be dense and ordered.")
        checks = _nonnegative(self.composition_check_count, name="composition_check_count")
        if self.canonical_schema_version != CANONICAL_CELL_COMPLEX_SYMMETRY_SCHEMA:
            raise NaturalTilingInputError("Unsupported cell-complex symmetry schema.")
        if self.digest_algorithm != NATURAL_TILING_DIGEST_ALGORITHM:
            raise NaturalTilingInputError("Unsupported natural-tiling digest algorithm.")
        object.__setattr__(self, "operation_results", results)
        object.__setattr__(self, "composition_check_count", checks)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise NaturalTilingInputError("Stored cell-complex symmetry digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PeriodicCellComplexSymmetryAction) and self.digest == other.digest

    @property
    def preserved(self) -> bool:
        return all(value.status is SymmetryOperationStatus.PRESERVED for value in self.operation_results)

    @property
    def failed_operation_indices(self) -> tuple[int, ...]:
        return tuple(
            value.operation_index
            for value in self.operation_results
            if value.status is SymmetryOperationStatus.NOT_PRESERVED
        )

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "periodic_net_symmetry_digest": self.periodic_net_symmetry_digest,
            "primitive_ring_symmetry_digest": self.primitive_ring_symmetry_digest,
            "periodic_cell_complex_digest": self.periodic_cell_complex_digest,
            "operation_results": [value.to_dict() for value in self.operation_results],
            "composition_check_count": self.composition_check_count,
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
        complex_: PeriodicCellComplex,
        symmetry: PeriodicNetSymmetry,
        ring_symmetry: PrimitiveRingSymmetryIndex,
        resources: "NaturalTilingSymmetryResources | None" = None,
    ) -> "PeriodicCellComplexSymmetryAction":
        """Rebuild the exact action and reject altered serialized evidence."""

        try:
            rebuilt = build_periodic_cell_complex_symmetry_action(
                complex_, symmetry, ring_symmetry, resources=resources
            )
            if rebuilt.to_dict() != dict(payload):
                raise NaturalTilingSerializationError(
                    "Serialized cell-complex symmetry action is not canonical for the supplied sources."
                )
            return rebuilt
        except NaturalTilingError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise NaturalTilingSerializationError(
                "Invalid PeriodicCellComplexSymmetryAction payload."
            ) from exc


@dataclass(frozen=True, slots=True)
class NaturalTilingSymmetryResources:
    """Finite exact validation limits for scientific face/tile actions."""

    max_operation_face_images: int = 5_000_000
    max_operation_tile_images: int = 5_000_000
    max_composition_checks: int = 20_000_000

    def __post_init__(self) -> None:
        for name in (
            "max_operation_face_images",
            "max_operation_tile_images",
            "max_composition_checks",
        ):
            object.__setattr__(self, name, _positive(getattr(self, name), name=name))


def _face_images_for_operation(
    complex_: PeriodicCellComplex,
    symmetry: PeriodicNetSymmetry,
    ring_symmetry: PrimitiveRingSymmetryIndex,
    operation_index: int,
) -> tuple[OrientedCellImage, ...] | None:
    target_by_key: dict[PrimitiveRingKey, int] = {}
    for index, face in enumerate(complex_.face_placements):
        key = face.ring_placement.ring_key
        if key in target_by_key:
            raise NaturalTilingInputError(
                "Stage-10A requires one scientific face-orbit representative per primitive ring key."
            )
        target_by_key[key] = index
    images: list[OrientedCellImage] = []
    for face in complex_.face_placements:
        mapped = map_face_placement(face, symmetry, ring_symmetry, operation_index)
        target_index = target_by_key.get(mapped.ring_placement.ring_key)
        if target_index is None:
            return None
        target = complex_.face_placements[target_index]
        images.append(
            OrientedCellImage(
                target_index,
                subtract_shift(
                    mapped.ring_placement.image_shift,
                    target.ring_placement.image_shift,
                ),
                mapped.orientation * target.orientation,
            )
        )
    return tuple(images)


def _map_shell(
    shell: PeriodicTileShell,
    face_images: Sequence[OrientedCellImage],
    lattice_matrix: tuple[tuple[int, int, int], ...],
) -> tuple[TranslatedCellTerm, ...]:
    return _combine_terms(
        TranslatedCellTerm(
            face_images[term.cell_index].target_cell_index,
            add_shift(
                matvec_shift(lattice_matrix, term.image_shift),
                face_images[term.cell_index].image_shift,
            ),
            term.coefficient * face_images[term.cell_index].orientation,
        )
        for term in shell.face_incidences
    )


def _translated_oriented_shell(
    shell: PeriodicTileShell,
    shift: LatticeShift,
    orientation: int,
) -> tuple[TranslatedCellTerm, ...]:
    return _combine_terms(
        TranslatedCellTerm(
            term.cell_index,
            add_shift(term.image_shift, shift),
            term.coefficient * orientation,
        )
        for term in shell.face_incidences
    )


def _match_tile_shell(
    mapped: tuple[TranslatedCellTerm, ...],
    shells: Sequence[PeriodicTileShell],
) -> OrientedCellImage | None:
    matches: set[OrientedCellImage] = set()
    if not mapped:
        return None
    anchor = mapped[0]
    for shell in shells:
        if len(shell.face_incidences) != len(mapped):
            continue
        for orientation in (-1, 1):
            for term in shell.face_incidences:
                if term.cell_index != anchor.cell_index or term.coefficient * orientation != anchor.coefficient:
                    continue
                shift = subtract_shift(anchor.image_shift, term.image_shift)
                if _translated_oriented_shell(shell, shift, orientation) == mapped:
                    matches.add(OrientedCellImage(shell.tile_index, shift, orientation))
    if len(matches) > 1:
        raise NaturalTilingInputError(
            "Scientific tile-orbit representatives are duplicate or symmetry-image ambiguous."
        )
    return next(iter(matches)) if matches else None


def _validate_action_composition(
    action_rows: Sequence[CellComplexSymmetryOperation],
    symmetry: PeriodicNetSymmetry,
    resources: NaturalTilingSymmetryResources,
) -> int:
    if not all(row.status is SymmetryOperationStatus.PRESERVED for row in action_rows):
        return 0
    n_faces = len(action_rows[0].face_images)
    n_tiles = len(action_rows[0].tile_images)
    required = symmetry.order * symmetry.order * (n_faces + n_tiles)
    if required > resources.max_composition_checks:
        raise NaturalTilingResourceError(
            "Exact scientific cell-action composition exceeds max_composition_checks."
        )
    checks = 0
    for outer_index, outer in enumerate(symmetry.operations):
        for inner_index in range(symmetry.order):
            direct_index = symmetry.multiplication_table[outer_index][inner_index]
            removed = symmetry.composition_translation_table[outer_index][inner_index]
            for attr in ("face_images", "tile_images"):
                inner_row = getattr(action_rows[inner_index], attr)
                outer_row = getattr(action_rows[outer_index], attr)
                direct_row = getattr(action_rows[direct_index], attr)
                for source_index, inner_image in enumerate(inner_row):
                    outer_image = outer_row[inner_image.target_cell_index]
                    expected = OrientedCellImage(
                        outer_image.target_cell_index,
                        subtract_shift(
                            add_shift(
                                matvec_shift(outer.lattice_matrix, inner_image.image_shift),
                                outer_image.image_shift,
                            ),
                            removed,
                        ),
                        inner_image.orientation * outer_image.orientation,
                    )
                    if direct_row[source_index] != expected:
                        raise NaturalTilingInvariantError(
                            "Scientific face/tile action violates exact group composition."
                        )
                    checks += 1
    return checks


def build_periodic_cell_complex_symmetry_action(
    complex_: PeriodicCellComplex,
    symmetry: PeriodicNetSymmetry,
    ring_symmetry: PrimitiveRingSymmetryIndex,
    *,
    resources: NaturalTilingSymmetryResources | None = None,
) -> PeriodicCellComplexSymmetryAction:
    """Map every exact net automorphism onto scientific faces and tile shells.

    A missing face or tile image is a proof that the proposed complex is not
    invariant under that operation.  Auxiliary witness and tetrahedral meshes do
    not participate in the action.
    """

    if not isinstance(complex_, PeriodicCellComplex):
        raise NaturalTilingInputError("complex_ must be a PeriodicCellComplex.")
    if not isinstance(symmetry, PeriodicNetSymmetry):
        raise NaturalTilingInputError("symmetry must be a PeriodicNetSymmetry.")
    if not isinstance(ring_symmetry, PrimitiveRingSymmetryIndex):
        raise NaturalTilingInputError("ring_symmetry must be a PrimitiveRingSymmetryIndex.")
    if (
        complex_.periodic_net_view_digest != symmetry.periodic_net_view_digest
        or complex_.topology_graph_digest != symmetry.topology_graph_digest
        or ring_symmetry.periodic_net_symmetry_digest != symmetry.digest
        or ring_symmetry.periodic_net_view_digest != symmetry.periodic_net_view_digest
        or ring_symmetry.topology_graph_digest != symmetry.topology_graph_digest
        or ring_symmetry.primitive_ring_catalog_digest != complex_.primitive_ring_catalog_digest
    ):
        raise NaturalTilingInputError("Complex, symmetry, and ring action do not share exact sources.")
    active = resources or NaturalTilingSymmetryResources()
    if symmetry.order * len(complex_.face_placements) > active.max_operation_face_images:
        raise NaturalTilingResourceError("Face-image validation exceeds max_operation_face_images.")
    if symmetry.order * len(complex_.tile_shells) > active.max_operation_tile_images:
        raise NaturalTilingResourceError("Tile-image validation exceeds max_operation_tile_images.")

    rows: list[CellComplexSymmetryOperation] = []
    for operation_index, operation in enumerate(symmetry.operations):
        face_images = _face_images_for_operation(
            complex_, symmetry, ring_symmetry, operation_index
        )
        if face_images is None:
            rows.append(
                CellComplexSymmetryOperation(
                    operation_index,
                    SymmetryOperationStatus.NOT_PRESERVED,
                    reason="one selected scientific face orbit maps outside the selected face set",
                )
            )
            continue
        tile_images: list[OrientedCellImage] = []
        failure: str | None = None
        for shell in complex_.tile_shells:
            mapped = _map_shell(shell, face_images, operation.lattice_matrix)
            image = _match_tile_shell(mapped, complex_.tile_shells)
            if image is None:
                failure = "one translated scientific tile attaching map has no target tile orbit"
                break
            tile_images.append(image)
        if failure is not None:
            rows.append(
                CellComplexSymmetryOperation(
                    operation_index,
                    SymmetryOperationStatus.NOT_PRESERVED,
                    reason=failure,
                )
            )
        else:
            rows.append(
                CellComplexSymmetryOperation(
                    operation_index,
                    SymmetryOperationStatus.PRESERVED,
                    face_images,
                    tuple(tile_images),
                )
            )
    checks = _validate_action_composition(rows, symmetry, active)
    return PeriodicCellComplexSymmetryAction(
        symmetry.digest,
        ring_symmetry.digest,
        complex_.digest,
        tuple(rows),
        checks,
    )


@dataclass(frozen=True, slots=True)
class NaturalTilingCertification:
    """Independent certification axes for one proposed scientific tiling."""

    primitive_ring_bound: int
    primitive_complete: CertificationState
    symmetry_complete: CertificationState
    strength_complete: CertificationState
    embedding_complete: CertificationState
    compatibility_complete: CertificationState
    cell_complex_valid: CertificationState
    partition_certified: CertificationState
    properness: PropernessStatus
    resource_truncations: tuple[str, ...] = ()
    unresolved_assumptions: tuple[str, ...] = ()
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "primitive_ring_bound",
            _nonnegative(self.primitive_ring_bound, name="primitive_ring_bound"),
        )
        for name in (
            "primitive_complete",
            "symmetry_complete",
            "strength_complete",
            "embedding_complete",
            "compatibility_complete",
            "cell_complex_valid",
            "partition_certified",
        ):
            object.__setattr__(self, name, CertificationState(getattr(self, name)))
        object.__setattr__(self, "properness", PropernessStatus(self.properness))
        for name in ("resource_truncations", "unresolved_assumptions", "rejection_reasons"):
            values = tuple(sorted(set(str(value) for value in getattr(self, name) if str(value))))
            object.__setattr__(self, name, values)

    @property
    def eligibility(self) -> CandidateEligibility:
        states = (
            self.primitive_complete,
            self.symmetry_complete,
            self.strength_complete,
            self.embedding_complete,
            self.compatibility_complete,
            self.cell_complex_valid,
            self.partition_certified,
        )
        if (
            CertificationState.REJECTED in states
            or self.properness is PropernessStatus.CERTIFIED_IMPROPER
            or self.rejection_reasons
        ):
            return CandidateEligibility.INELIGIBLE
        if (
            all(value is CertificationState.CERTIFIED for value in states)
            and self.properness is PropernessStatus.CERTIFIED_PROPER
            and not self.resource_truncations
            and not self.unresolved_assumptions
        ):
            return CandidateEligibility.ELIGIBLE
        return CandidateEligibility.UNRESOLVED

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitive_ring_bound": self.primitive_ring_bound,
            "primitive_complete": self.primitive_complete.value,
            "symmetry_complete": self.symmetry_complete.value,
            "strength_complete": self.strength_complete.value,
            "embedding_complete": self.embedding_complete.value,
            "compatibility_complete": self.compatibility_complete.value,
            "cell_complex_valid": self.cell_complex_valid.value,
            "partition_certified": self.partition_certified.value,
            "properness": self.properness.value,
            "resource_truncations": list(self.resource_truncations),
            "unresolved_assumptions": list(self.unresolved_assumptions),
            "rejection_reasons": list(self.rejection_reasons),
            "eligibility": self.eligibility.value,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "NaturalTilingCertification":
        try:
            result = cls(
                primitive_ring_bound=int(payload["primitive_ring_bound"]),
                primitive_complete=CertificationState(str(payload["primitive_complete"])),
                symmetry_complete=CertificationState(str(payload["symmetry_complete"])),
                strength_complete=CertificationState(str(payload["strength_complete"])),
                embedding_complete=CertificationState(str(payload["embedding_complete"])),
                compatibility_complete=CertificationState(str(payload["compatibility_complete"])),
                cell_complex_valid=CertificationState(str(payload["cell_complex_valid"])),
                partition_certified=CertificationState(str(payload["partition_certified"])),
                properness=PropernessStatus(str(payload["properness"])),
                resource_truncations=tuple(str(value) for value in payload["resource_truncations"]),
                unresolved_assumptions=tuple(str(value) for value in payload["unresolved_assumptions"]),
                rejection_reasons=tuple(str(value) for value in payload["rejection_reasons"]),
            )
            if payload.get("eligibility") != result.eligibility.value:
                raise NaturalTilingSerializationError(
                    "Serialized certification eligibility is inconsistent."
                )
            return result
        except NaturalTilingError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise NaturalTilingSerializationError(
                "Invalid NaturalTilingCertification payload."
            ) from exc


@dataclass(frozen=True, slots=True, eq=False)
class NaturalTilingCandidate:
    """One scientific Stage-9 complex plus Stage-10A certification evidence."""

    periodic_net_view_digest: str
    topology_graph_digest: str
    primitive_ring_catalog_digest: str
    periodic_cell_complex_digest: str
    selected_ring_keys: tuple[PrimitiveRingKey, ...]
    certification: NaturalTilingCertification
    symmetry_action_digest: str | None = field(default=None, compare=False)
    partition_certificate_digest: str | None = field(default=None, compare=False)
    strength_catalog_digest: str | None = field(default=None, compare=False)
    compatibility_system_digest: str | None = field(default=None, compare=False)
    canonical_schema_version: str = CANONICAL_NATURAL_TILING_CANDIDATE_SCHEMA
    digest_algorithm: str = NATURAL_TILING_DIGEST_ALGORITHM
    digest: str = ""
    evidence_digest: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        for name in (
            "periodic_net_view_digest",
            "topology_graph_digest",
            "primitive_ring_catalog_digest",
            "periodic_cell_complex_digest",
        ):
            _sha(getattr(self, name), name=name)
        keys = tuple(sorted(set(self.selected_ring_keys)))
        if not keys:
            raise NaturalTilingInputError("A natural-tiling candidate requires selected face rings.")
        if not isinstance(self.certification, NaturalTilingCertification):
            raise NaturalTilingInputError("certification must be NaturalTilingCertification.")
        for name in (
            "symmetry_action_digest",
            "partition_certificate_digest",
            "strength_catalog_digest",
            "compatibility_system_digest",
        ):
            value = getattr(self, name)
            if value is not None:
                _sha(value, name=name)
        if self.canonical_schema_version != CANONICAL_NATURAL_TILING_CANDIDATE_SCHEMA:
            raise NaturalTilingInputError("Unsupported natural-tiling candidate schema.")
        if self.digest_algorithm != NATURAL_TILING_DIGEST_ALGORITHM:
            raise NaturalTilingInputError("Unsupported natural-tiling digest algorithm.")
        object.__setattr__(self, "selected_ring_keys", keys)
        scientific = _digest(self._scientific_payload(False))
        if self.digest and self.digest != scientific:
            raise NaturalTilingInputError("Stored scientific candidate digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or scientific)
        evidence = _digest(self._evidence_payload(False))
        if self.evidence_digest and self.evidence_digest != evidence:
            raise NaturalTilingInputError("Stored candidate evidence digest is inconsistent.")
        object.__setattr__(self, "evidence_digest", self.evidence_digest or evidence)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NaturalTilingCandidate) and self.digest == other.digest

    @property
    def eligibility(self) -> CandidateEligibility:
        return self.certification.eligibility

    def _scientific_payload(self, include_digest: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "periodic_net_view_digest": self.periodic_net_view_digest,
            "topology_graph_digest": self.topology_graph_digest,
            "primitive_ring_catalog_digest": self.primitive_ring_catalog_digest,
            "periodic_cell_complex_digest": self.periodic_cell_complex_digest,
            "selected_ring_keys": [key.to_dict() for key in self.selected_ring_keys],
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def _evidence_payload(self, include_digest: bool) -> dict[str, Any]:
        payload = self._scientific_payload(True)
        payload.update(
            {
                "certification": self.certification.to_dict(),
                "symmetry_action_digest": self.symmetry_action_digest,
                "partition_certificate_digest": self.partition_certificate_digest,
                "strength_catalog_digest": self.strength_catalog_digest,
                "compatibility_system_digest": self.compatibility_system_digest,
            }
        )
        if include_digest:
            payload["evidence_digest"] = self.evidence_digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._evidence_payload(True)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "NaturalTilingCandidate":
        try:
            return cls(
                periodic_net_view_digest=str(payload["periodic_net_view_digest"]),
                topology_graph_digest=str(payload["topology_graph_digest"]),
                primitive_ring_catalog_digest=str(payload["primitive_ring_catalog_digest"]),
                periodic_cell_complex_digest=str(payload["periodic_cell_complex_digest"]),
                selected_ring_keys=tuple(
                    PrimitiveRingKey.from_dict(value)
                    for value in payload["selected_ring_keys"]
                ),
                certification=NaturalTilingCertification.from_dict(payload["certification"]),
                symmetry_action_digest=(
                    None if payload.get("symmetry_action_digest") is None
                    else str(payload["symmetry_action_digest"])
                ),
                partition_certificate_digest=(
                    None if payload.get("partition_certificate_digest") is None
                    else str(payload["partition_certificate_digest"])
                ),
                strength_catalog_digest=(
                    None if payload.get("strength_catalog_digest") is None
                    else str(payload["strength_catalog_digest"])
                ),
                compatibility_system_digest=(
                    None if payload.get("compatibility_system_digest") is None
                    else str(payload["compatibility_system_digest"])
                ),
                canonical_schema_version=str(payload["canonical_schema_version"]),
                digest_algorithm=str(payload["digest_algorithm"]),
                digest=str(payload["digest"]),
                evidence_digest=str(payload["evidence_digest"]),
            )
        except NaturalTilingError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise NaturalTilingSerializationError(
                "Invalid NaturalTilingCandidate payload."
            ) from exc


@dataclass(frozen=True, slots=True)
class NaturalTilingOutcome:
    """Multiplicity statement over eligible scientific candidate identities."""

    kind: NaturalTilingOutcomeKind
    candidate_digests: tuple[str, ...]

    def __post_init__(self) -> None:
        kind = NaturalTilingOutcomeKind(self.kind)
        candidates = tuple(sorted(set(self.candidate_digests)))
        for value in candidates:
            _sha(value, name="candidate_digest")
        expected = (
            NaturalTilingOutcomeKind.NONE
            if not candidates
            else NaturalTilingOutcomeKind.UNIQUE
            if len(candidates) == 1
            else NaturalTilingOutcomeKind.MULTIPLE
        )
        if kind is not expected:
            raise NaturalTilingInputError("NaturalTilingOutcome kind disagrees with candidate multiplicity.")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "candidate_digests", candidates)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "candidate_digests": list(self.candidate_digests)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "NaturalTilingOutcome":
        try:
            return cls(
                NaturalTilingOutcomeKind(str(payload["kind"])),
                tuple(str(value) for value in payload["candidate_digests"]),
            )
        except NaturalTilingError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise NaturalTilingSerializationError(
                "Invalid NaturalTilingOutcome payload."
            ) from exc


@dataclass(frozen=True, slots=True, eq=False)
class NaturalTilingCatalog:
    """Ambiguity-preserving collection of scientific Stage-10A candidates."""

    periodic_net_view_digest: str
    primitive_ring_catalog_digest: str
    candidates: tuple[NaturalTilingCandidate, ...]
    outcome: NaturalTilingOutcome
    essential_ring_keys: tuple[PrimitiveRingKey, ...]
    canonical_schema_version: str = CANONICAL_NATURAL_TILING_CATALOG_SCHEMA
    digest_algorithm: str = NATURAL_TILING_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        _sha(self.periodic_net_view_digest, name="periodic_net_view_digest")
        _sha(self.primitive_ring_catalog_digest, name="primitive_ring_catalog_digest")
        candidates = tuple(self.candidates)
        if candidates != tuple(sorted(candidates, key=lambda value: value.digest)):
            raise NaturalTilingInputError("Catalog candidates must be sorted by scientific digest.")
        if len({value.digest for value in candidates}) != len(candidates):
            raise NaturalTilingInputError("Catalog candidates must have unique scientific identities.")
        if any(
            value.periodic_net_view_digest != self.periodic_net_view_digest
            or value.primitive_ring_catalog_digest != self.primitive_ring_catalog_digest
            for value in candidates
        ):
            raise NaturalTilingInputError("Catalog candidates do not share source identities.")
        eligible = tuple(value.digest for value in candidates if value.eligibility is CandidateEligibility.ELIGIBLE)
        if self.outcome.candidate_digests != eligible:
            raise NaturalTilingInputError("Catalog outcome does not list exactly the eligible candidates.")
        essential = tuple(sorted(set(self.essential_ring_keys)))
        expected_essential = tuple(
            sorted(
                {
                    key
                    for value in candidates
                    if value.eligibility is CandidateEligibility.ELIGIBLE
                    for key in value.selected_ring_keys
                }
            )
        )
        if essential != expected_essential:
            raise NaturalTilingInputError("Essential rings must be exactly the accepted face-ring union.")
        if self.canonical_schema_version != CANONICAL_NATURAL_TILING_CATALOG_SCHEMA:
            raise NaturalTilingInputError("Unsupported natural-tiling catalog schema.")
        if self.digest_algorithm != NATURAL_TILING_DIGEST_ALGORITHM:
            raise NaturalTilingInputError("Unsupported natural-tiling digest algorithm.")
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "essential_ring_keys", essential)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise NaturalTilingInputError("Stored natural-tiling catalog digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NaturalTilingCatalog) and self.digest == other.digest

    @property
    def eligible_candidates(self) -> tuple[NaturalTilingCandidate, ...]:
        return tuple(value for value in self.candidates if value.eligibility is CandidateEligibility.ELIGIBLE)

    @property
    def unresolved_candidates(self) -> tuple[NaturalTilingCandidate, ...]:
        return tuple(value for value in self.candidates if value.eligibility is CandidateEligibility.UNRESOLVED)

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "periodic_net_view_digest": self.periodic_net_view_digest,
            "primitive_ring_catalog_digest": self.primitive_ring_catalog_digest,
            "candidates": [value.to_dict() for value in self.candidates],
            "outcome": self.outcome.to_dict(),
            "essential_ring_keys": [key.to_dict() for key in self.essential_ring_keys],
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "NaturalTilingCatalog":
        try:
            return cls(
                periodic_net_view_digest=str(payload["periodic_net_view_digest"]),
                primitive_ring_catalog_digest=str(payload["primitive_ring_catalog_digest"]),
                candidates=tuple(
                    NaturalTilingCandidate.from_dict(value)
                    for value in payload["candidates"]
                ),
                outcome=NaturalTilingOutcome.from_dict(payload["outcome"]),
                essential_ring_keys=tuple(
                    PrimitiveRingKey.from_dict(value)
                    for value in payload["essential_ring_keys"]
                ),
                canonical_schema_version=str(payload["canonical_schema_version"]),
                digest_algorithm=str(payload["digest_algorithm"]),
                digest=str(payload["digest"]),
            )
        except NaturalTilingError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise NaturalTilingSerializationError(
                "Invalid NaturalTilingCatalog payload."
            ) from exc


def _selected_assignment_state(
    certificates: Sequence[FacePlacementCertificate],
    witnesses: Sequence[FaceEmbeddingWitness],
    compatibility: FaceCompatibilityConstraintSystem | None,
) -> tuple[CertificationState, tuple[str, ...], tuple[str, ...]]:
    if compatibility is None:
        return (
            CertificationState.UNRESOLVED,
            ("no complete face-witness compatibility system was supplied",),
            (),
        )
    expected = tuple(sorted(value.digest for value in certificates))
    if compatibility.face_certificate_digests != expected:
        raise NaturalTilingInputError("Compatibility system does not cover exactly the selected faces.")
    selected = frozenset(
        FaceWitnessAssignment(certificate.face_placement.digest, witness.witness_id, witness.digest)
        for certificate, witness in zip(certificates, witnesses, strict=True)
    )
    if not selected.issubset(frozenset(compatibility.assignments)):
        raise NaturalTilingInputError("Selected witnesses are absent from the compatibility domain.")
    unresolved: list[str] = []
    rejected: list[str] = []
    for constraint in compatibility.constraints:
        if set(constraint.assignments).issubset(selected):
            if constraint.kind is FaceConstraintKind.UNRESOLVED:
                unresolved.append(constraint.reason)
            else:
                rejected.append(constraint.reason)
    if rejected:
        return CertificationState.REJECTED, (), tuple(rejected)
    if unresolved:
        return CertificationState.UNRESOLVED, tuple(unresolved), ()
    return CertificationState.CERTIFIED, (), ()


def certify_natural_tiling_candidate(
    view: PeriodicNetView,
    discovery: PeriodicNetSymmetryDiscovery,
    ring_index: PrimitiveRingIndex,
    strength_catalog: RingStrengthCatalog | None,
    face_certificates: Sequence[FacePlacementCertificate],
    selected_witnesses: Sequence[FaceEmbeddingWitness],
    compatibility: FaceCompatibilityConstraintSystem | None,
    complex_: PeriodicCellComplex,
    partition_certificate: PeriodicPartitionCertificate | None,
    *,
    symmetry_resources: NaturalTilingSymmetryResources | None = None,
) -> NaturalTilingCandidate:
    """Certify one caller-proposed Stage-9 complex along independent axes."""

    if not isinstance(view, PeriodicNetView):
        raise NaturalTilingInputError("view must be a PeriodicNetView.")
    if not isinstance(discovery, PeriodicNetSymmetryDiscovery):
        raise NaturalTilingInputError("discovery must certify the complete first-backend symmetry group.")
    if not isinstance(ring_index, PrimitiveRingIndex):
        raise NaturalTilingInputError("ring_index must be a PrimitiveRingIndex.")
    if not isinstance(complex_, PeriodicCellComplex):
        raise NaturalTilingInputError("complex_ must be a PeriodicCellComplex.")
    if (
        discovery.periodic_net_view_digest != view.digest
        or discovery.topology_graph_digest != view.source_graph_digest
        or complex_.periodic_net_view_digest != view.digest
        or complex_.topology_graph_digest != view.source_graph_digest
        or complex_.primitive_ring_catalog_digest != ring_index.catalog_digest
    ):
        raise NaturalTilingInputError("Natural-tiling sources do not share exact identities.")
    ring_symmetry = discovery.ring_symmetry
    if ring_symmetry is None:
        raise NaturalTilingInputError("Complete discovery must include the source-bound ring action.")
    certificates = tuple(face_certificates)
    witnesses = tuple(selected_witnesses)
    if len(certificates) != len(complex_.face_placements) or len(witnesses) != len(certificates):
        raise NaturalTilingInputError("Face certificates and witnesses must align with the scientific complex.")
    by_face = {certificate.face_placement.digest: (certificate, witness) for certificate, witness in zip(certificates, witnesses, strict=True)}
    try:
        ordered = tuple(by_face[face.digest] for face in complex_.face_placements)
    except KeyError as exc:
        raise NaturalTilingInputError("A scientific complex face lacks its source certificate.") from exc
    certificates = tuple(value[0] for value in ordered)
    witnesses = tuple(value[1] for value in ordered)

    unresolved: list[str] = []
    rejected: list[str] = []
    truncations: list[str] = []

    face_sizes = tuple(len(face.ring_placement.ring_key.edge_tokens) for face in complex_.face_placements)
    primitive_ok = (
        ring_index.catalog.ring_family is PrimitiveRingFamily.PRIMITIVE_NO_SHORTCUT
        and ring_index.catalog.options.min_ring_size == 2
        and ring_index.catalog.search_completed_without_resource_truncation
        and ring_index.catalog.complete_for_ring_sizes_up_to >= max(face_sizes)
    )
    primitive_state = CertificationState.CERTIFIED if primitive_ok else CertificationState.UNRESOLVED
    if not ring_index.catalog.search_completed_without_resource_truncation:
        truncations.append("primitive-ring enumeration was resource-truncated")
    if ring_index.catalog.options.min_ring_size != 2:
        unresolved.append("primitive-ring catalog is not lower-closed from size two")
    if ring_index.catalog.complete_for_ring_sizes_up_to < max(face_sizes):
        unresolved.append("primitive-ring completeness bound is below a selected face size")

    symmetry_state = CertificationState.CERTIFIED
    action = build_periodic_cell_complex_symmetry_action(
        complex_, discovery.symmetry, ring_symmetry, resources=symmetry_resources
    )
    properness = (
        PropernessStatus.CERTIFIED_PROPER
        if action.preserved
        else PropernessStatus.CERTIFIED_IMPROPER
    )
    if not action.preserved:
        rejected.append(
            "scientific tiling is not invariant under full net symmetry operations "
            + ",".join(str(value) for value in action.failed_operation_indices)
        )

    embedding_state = CertificationState.CERTIFIED
    for certificate, witness in zip(certificates, witnesses, strict=True):
        if certificate.status is not FacePlacementStatus.CERTIFIED_ADMISSIBLE or witness not in certificate.admissible_witnesses:
            embedding_state = CertificationState.UNRESOLVED
            unresolved.append("a selected scientific face lacks a certified admissible witness")
            break

    compatibility_state, compatibility_unresolved, compatibility_rejected = _selected_assignment_state(
        certificates, witnesses, compatibility
    )
    unresolved.extend(compatibility_unresolved)
    rejected.extend(compatibility_rejected)

    if strength_catalog is None:
        strength_state = CertificationState.UNRESOLVED
        unresolved.append("no bounded ring-strength catalog was supplied")
    else:
        if (
            strength_catalog.topology_graph_digest != view.source_graph_digest
            or strength_catalog.primitive_ring_catalog_digest != ring_index.catalog_digest
        ):
            raise NaturalTilingInputError("Ring-strength catalog belongs to different sources.")
        result_by_key = {value.target_placement.ring_key: value for value in strength_catalog.results}
        statuses = []
        for face in complex_.face_placements:
            result = result_by_key.get(face.ring_placement.ring_key)
            if result is None:
                statuses.append(None)
                unresolved.append("a selected face ring lacks a strength result")
            else:
                statuses.append(result.status)
                if result.status is RingStrengthStatus.WEAK_CERTIFIED:
                    rejected.append("a selected face ring is certified weak in its declared domain")
                elif result.status is RingStrengthStatus.UNRESOLVED_TRUNCATED:
                    truncations.append(result.diagnostics.truncation_reason or "ring-strength search truncated")
                elif result.status is RingStrengthStatus.UNRESOLVED_SOURCE_INCOMPLETE:
                    unresolved.append(result.diagnostics.source_issue or "ring-strength source incomplete")
        if any(value is RingStrengthStatus.WEAK_CERTIFIED for value in statuses):
            strength_state = CertificationState.REJECTED
        elif statuses and all(value is RingStrengthStatus.STRONG_IN_DOMAIN for value in statuses):
            strength_state = CertificationState.CERTIFIED
        else:
            strength_state = CertificationState.UNRESOLVED

    partition_state = CertificationState.UNRESOLVED
    if partition_certificate is None:
        unresolved.append("no exact periodic partition certificate was supplied")
    elif (
        partition_certificate.periodic_cell_complex_digest != complex_.digest
        or partition_certificate.periodic_net_embedding_digest != complex_.periodic_net_embedding_digest
    ):
        raise NaturalTilingInputError("Partition certificate belongs to a different scientific complex or embedding.")
    else:
        partition_state = CertificationState.CERTIFIED

    certification = NaturalTilingCertification(
        primitive_ring_bound=ring_index.catalog.complete_for_ring_sizes_up_to,
        primitive_complete=primitive_state,
        symmetry_complete=symmetry_state,
        strength_complete=strength_state,
        embedding_complete=embedding_state,
        compatibility_complete=compatibility_state,
        cell_complex_valid=CertificationState.CERTIFIED,
        partition_certified=partition_state,
        properness=properness,
        resource_truncations=tuple(truncations),
        unresolved_assumptions=tuple(unresolved),
        rejection_reasons=tuple(rejected),
    )
    return NaturalTilingCandidate(
        periodic_net_view_digest=view.digest,
        topology_graph_digest=view.source_graph_digest,
        primitive_ring_catalog_digest=ring_index.catalog_digest,
        periodic_cell_complex_digest=complex_.digest,
        selected_ring_keys=tuple(face.ring_placement.ring_key for face in complex_.face_placements),
        certification=certification,
        symmetry_action_digest=action.digest,
        partition_certificate_digest=(None if partition_certificate is None else partition_certificate.digest),
        strength_catalog_digest=(None if strength_catalog is None else strength_catalog.digest),
        compatibility_system_digest=(None if compatibility is None else compatibility.digest),
    )


def build_natural_tiling_catalog(
    candidates: Sequence[NaturalTilingCandidate],
    *,
    periodic_net_view_digest: str | None = None,
    primitive_ring_catalog_digest: str | None = None,
) -> NaturalTilingCatalog:
    """Deduplicate scientific identities and preserve NONE/UNIQUE/MULTIPLE outcomes.

    If duplicate scientific complexes carry different evidence, the strongest
    aggregate eligibility is retained: eligible beats unresolved, which beats
    ineligible.  Conflicting eligible/ineligible evidence for one identity is an
    input error rather than an enumeration-order tie-break.
    """

    values = tuple(candidates)
    if values:
        view_digest = values[0].periodic_net_view_digest
        ring_digest = values[0].primitive_ring_catalog_digest
        if periodic_net_view_digest is not None and periodic_net_view_digest != view_digest:
            raise NaturalTilingInputError("Explicit view digest disagrees with candidate sources.")
        if primitive_ring_catalog_digest is not None and primitive_ring_catalog_digest != ring_digest:
            raise NaturalTilingInputError("Explicit ring-catalog digest disagrees with candidate sources.")
    else:
        if periodic_net_view_digest is None or primitive_ring_catalog_digest is None:
            raise NaturalTilingInputError(
                "Empty catalogs require explicit periodic_net_view_digest and primitive_ring_catalog_digest."
            )
        view_digest = _sha(periodic_net_view_digest, name="periodic_net_view_digest")
        ring_digest = _sha(primitive_ring_catalog_digest, name="primitive_ring_catalog_digest")
    if any(
        value.periodic_net_view_digest != view_digest
        or value.primitive_ring_catalog_digest != ring_digest
        for value in values
    ):
        raise NaturalTilingInputError("All candidate records must share view and ring-catalog sources.")
    grouped: dict[str, list[NaturalTilingCandidate]] = {}
    for value in values:
        grouped.setdefault(value.digest, []).append(value)
    selected: list[NaturalTilingCandidate] = []
    rank = {
        CandidateEligibility.INELIGIBLE: 0,
        CandidateEligibility.UNRESOLVED: 1,
        CandidateEligibility.ELIGIBLE: 2,
    }
    for digest in sorted(grouped):
        group = grouped[digest]
        eligibilities = {value.eligibility for value in group}
        if CandidateEligibility.ELIGIBLE in eligibilities and CandidateEligibility.INELIGIBLE in eligibilities:
            raise NaturalTilingInputError("Conflicting accepted and rejected evidence exists for one scientific tiling identity.")
        selected.append(max(group, key=lambda value: (rank[value.eligibility], value.evidence_digest)))
    ordered = tuple(sorted(selected, key=lambda value: value.digest))
    eligible = tuple(value.digest for value in ordered if value.eligibility is CandidateEligibility.ELIGIBLE)
    kind = (
        NaturalTilingOutcomeKind.NONE
        if not eligible
        else NaturalTilingOutcomeKind.UNIQUE
        if len(eligible) == 1
        else NaturalTilingOutcomeKind.MULTIPLE
    )
    essential = tuple(
        sorted(
            {
                key
                for value in ordered
                if value.eligibility is CandidateEligibility.ELIGIBLE
                for key in value.selected_ring_keys
            }
        )
    )
    return NaturalTilingCatalog(
        view_digest,
        ring_digest,
        ordered,
        NaturalTilingOutcome(kind, eligible),
        essential,
    )
