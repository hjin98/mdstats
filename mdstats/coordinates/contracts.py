"""Stage-C0 source-coordinate and force-admissibility contracts.

This module records what the normalized source collection means before any
analysis-specific affine registration is attempted.  It deliberately separates
geometric force transformation from thermodynamic PMF-force admissibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:  # pragma: no cover
    from ..collection import AtomisticFrameCollection

SOURCE_COORDINATE_CONTRACT_SCHEMA = "mdstats.source-coordinate-contract.v1"
SOURCE_FIELD_SEMANTICS_SCHEMA = "mdstats.source-field-semantics.v1"
FORCE_ADMISSIBILITY_SCHEMA = "mdstats.force-admissibility.v1"
REFERENCE_CELL_DEFINITION_SCHEMA = "mdstats.reference-cell-definition.v1"
COORDINATE_CONTRACT_DIGEST_ALGORITHM = "sha256-canonical-json-v1"


class CoordinateContractError(ValueError):
    """Base exception for Stage-C0 coordinate contracts."""


class SourceSemanticsError(CoordinateContractError):
    """Raised when a requested source-field meaning is unavailable."""


class ReferenceCellError(CoordinateContractError):
    """Raised when a reference-cell definition violates the initial scope."""


class PositionFrame(str, Enum):
    CELL_ORIGIN_RELATIVE_CARTESIAN = "cell_origin_relative_cartesian"
    UNKNOWN = "unknown"


class VelocityFrame(str, Enum):
    NORMALIZED_CARTESIAN = "normalized_cartesian"
    FINITE_DIFFERENCE_NORMALIZED_CARTESIAN = (
        "finite_difference_normalized_cartesian"
    )
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ForceFrame(str, Enum):
    NORMALIZED_CARTESIAN_COVECTOR = "normalized_cartesian_covector"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class BoxOriginFrame(str, Enum):
    LABORATORY_CARTESIAN = "laboratory_cartesian"
    ZERO_ORIGIN_CONVENTION = "zero_origin_convention"
    UNKNOWN = "unknown"


class EvidenceState(str, Enum):
    ABSENT = "absent"
    PRESENT = "present"
    UNKNOWN = "unknown"


class GeometricForceTransformStatus(str, Enum):
    EXACT_EXTERNAL_AFFINE_COVECTOR = "exact_external_affine_covector"
    EXACT_TRANSLATION_RELATIVE_TO_DISJOINT_REFERENCE_GROUP = (
        "exact_translation_relative_to_disjoint_reference_group"
    )
    DIAGNOSTIC_STRUCTURE_FITTED_PROJECTION = (
        "diagnostic_structure_fitted_projection"
    )
    GENERALIZED_FORCE_UNAVAILABLE = "generalized_force_unavailable"


class PMFForceAdmissibilityStatus(str, Enum):
    PMF_FORCE_ADMISSIBLE = "pmf_force_admissible"
    PMF_FORCE_INADMISSIBLE_VARIABLE_CELL_MEASURE = (
        "pmf_force_inadmissible_variable_cell_measure"
    )
    PMF_FORCE_INADMISSIBLE_STRUCTURE_FITTED_MAP = (
        "pmf_force_inadmissible_structure_fitted_map"
    )
    PMF_FORCE_INADMISSIBLE_UNTRACKED_BIAS_OR_CONSTRAINT = (
        "pmf_force_inadmissible_untracked_bias_or_constraint"
    )
    PMF_FORCE_PROVENANCE_UNKNOWN = "pmf_force_provenance_unknown"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _enum(enum_type: type[Enum], value: object, *, name: str) -> Enum:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise SourceSemanticsError(f"{name} must be one of: {allowed}.") from exc


def _matrix_tuple(matrix: object, *, name: str) -> tuple[tuple[float, float, float], ...]:
    array = np.asarray(matrix, dtype=np.float64)
    if array.shape != (3, 3) or not np.all(np.isfinite(array)):
        raise ReferenceCellError(f"{name} must be a finite 3x3 matrix.")
    return tuple(tuple(float(value) for value in row) for row in array)


def _pbc_tuple(pbc: object) -> tuple[bool, bool, bool]:
    array = np.asarray(pbc, dtype=np.bool_)
    if array.shape != (3,):
        raise ReferenceCellError("periodic_axes must have shape (3,).")
    return tuple(bool(value) for value in array)


@dataclass(frozen=True, slots=True)
class SourceFieldSemantics:
    """Meanings of normalized position, velocity, force, and origin fields."""

    position_frame: PositionFrame = PositionFrame.CELL_ORIGIN_RELATIVE_CARTESIAN
    velocity_frame: VelocityFrame = VelocityFrame.UNKNOWN
    force_frame: ForceFrame = ForceFrame.UNKNOWN
    box_origin_frame: BoxOriginFrame = BoxOriginFrame.UNKNOWN

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "position_frame",
            _enum(PositionFrame, self.position_frame, name="position_frame"),
        )
        object.__setattr__(
            self,
            "velocity_frame",
            _enum(VelocityFrame, self.velocity_frame, name="velocity_frame"),
        )
        object.__setattr__(
            self,
            "force_frame",
            _enum(ForceFrame, self.force_frame, name="force_frame"),
        )
        object.__setattr__(
            self,
            "box_origin_frame",
            _enum(BoxOriginFrame, self.box_origin_frame, name="box_origin_frame"),
        )

    @property
    def velocity_transformable(self) -> bool:
        return self.velocity_frame in {
            VelocityFrame.NORMALIZED_CARTESIAN,
            VelocityFrame.FINITE_DIFFERENCE_NORMALIZED_CARTESIAN,
        }

    @property
    def force_transformable(self) -> bool:
        return self.force_frame is ForceFrame.NORMALIZED_CARTESIAN_COVECTOR

    def require_positions(self, claim: str) -> None:
        if self.position_frame is PositionFrame.UNKNOWN:
            raise SourceSemanticsError(
                f"{claim} requires known source-position frame semantics."
            )

    def require_velocities(self, claim: str) -> None:
        if not self.velocity_transformable:
            raise SourceSemanticsError(
                f"{claim} requires transformable source velocities; "
                f"status is {self.velocity_frame.value}."
            )

    def require_forces(self, claim: str) -> None:
        if not self.force_transformable:
            raise SourceSemanticsError(
                f"{claim} requires transformable source-force covectors; "
                f"status is {self.force_frame.value}."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SOURCE_FIELD_SEMANTICS_SCHEMA,
            "position_frame": self.position_frame.value,
            "velocity_frame": self.velocity_frame.value,
            "force_frame": self.force_frame.value,
            "box_origin_frame": self.box_origin_frame.value,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceFieldSemantics":
        if payload.get("schema") != SOURCE_FIELD_SEMANTICS_SCHEMA:
            raise SourceSemanticsError("Unsupported source-field-semantics schema.")
        return cls(
            position_frame=payload.get("position_frame", "unknown"),
            velocity_frame=payload.get("velocity_frame", "unknown"),
            force_frame=payload.get("force_frame", "unknown"),
            box_origin_frame=payload.get("box_origin_frame", "unknown"),
        )


@dataclass(frozen=True, slots=True)
class ForceSourceProvenance:
    """Source evidence needed before a force may support a PMF claim."""

    physical_force_complete: EvidenceState = EvidenceState.UNKNOWN
    bias_or_constraint_force: EvidenceState = EvidenceState.UNKNOWN
    stochastic_or_thermostat_force: EvidenceState = EvidenceState.UNKNOWN
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "physical_force_complete",
            "bias_or_constraint_force",
            "stochastic_or_thermostat_force",
        ):
            object.__setattr__(
                self,
                name,
                _enum(EvidenceState, getattr(self, name), name=name),
            )
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "physical_force_complete": self.physical_force_complete.value,
            "bias_or_constraint_force": self.bias_or_constraint_force.value,
            "stochastic_or_thermostat_force": self.stochastic_or_thermostat_force.value,
            "notes": list(self.notes),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any] | None) -> "ForceSourceProvenance":
        if payload is None:
            return cls()
        return cls(
            physical_force_complete=payload.get("physical_force_complete", "unknown"),
            bias_or_constraint_force=payload.get("bias_or_constraint_force", "unknown"),
            stochastic_or_thermostat_force=payload.get(
                "stochastic_or_thermostat_force", "unknown"
            ),
            notes=tuple(payload.get("notes", ())),
        )


@dataclass(frozen=True, slots=True)
class ForceAdmissibilityContract:
    """Independent geometric and thermodynamic force statuses."""

    geometric_status: GeometricForceTransformStatus
    pmf_status: PMFForceAdmissibilityStatus
    source_provenance: ForceSourceProvenance
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "geometric_status",
            _enum(
                GeometricForceTransformStatus,
                self.geometric_status,
                name="geometric_status",
            ),
        )
        object.__setattr__(
            self,
            "pmf_status",
            _enum(PMFForceAdmissibilityStatus, self.pmf_status, name="pmf_status"),
        )
        if not isinstance(self.source_provenance, ForceSourceProvenance):
            raise SourceSemanticsError(
                "source_provenance must be ForceSourceProvenance."
            )
        object.__setattr__(self, "reasons", tuple(str(value) for value in self.reasons))

    @property
    def geometric_force_available(self) -> bool:
        return (
            self.geometric_status
            is not GeometricForceTransformStatus.GENERALIZED_FORCE_UNAVAILABLE
        )

    @property
    def pmf_force_admissible(self) -> bool:
        return self.pmf_status is PMFForceAdmissibilityStatus.PMF_FORCE_ADMISSIBLE

    def require_pmf_force(self, claim: str) -> None:
        if not self.pmf_force_admissible:
            raise SourceSemanticsError(
                f"{claim} requires PMF-admissible force evidence; status is "
                f"{self.pmf_status.value}."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": FORCE_ADMISSIBILITY_SCHEMA,
            "geometric_status": self.geometric_status.value,
            "pmf_status": self.pmf_status.value,
            "source_provenance": self.source_provenance.to_dict(),
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ForceAdmissibilityContract":
        if payload.get("schema") != FORCE_ADMISSIBILITY_SCHEMA:
            raise SourceSemanticsError("Unsupported force-admissibility schema.")
        source_payload = payload.get("source_provenance")
        if not isinstance(source_payload, Mapping):
            raise SourceSemanticsError("Missing force-source provenance payload.")
        return cls(
            geometric_status=payload.get(
                "geometric_status", "generalized_force_unavailable"
            ),
            pmf_status=payload.get("pmf_status", "pmf_force_provenance_unknown"),
            source_provenance=ForceSourceProvenance.from_mapping(source_payload),
            reasons=tuple(payload.get("reasons", ())),
        )


@dataclass(frozen=True, slots=True)
class ReferenceCellDefinition:
    """Immutable reference cell admitted by the initial Stage-C0 scope."""

    source_kind: str
    matrix: tuple[tuple[float, float, float], ...]
    periodic_axes: tuple[bool, bool, bool]
    selected_frame_index: int | None
    handedness: int
    determinant: float
    condition_number: float
    basis_gauge_signature: str | None
    tolerance: float
    digest: str = ""

    def __post_init__(self) -> None:
        if self.source_kind not in {"explicit_matrix", "selected_source_frame"}:
            raise ReferenceCellError(
                "source_kind must be explicit_matrix or selected_source_frame."
            )
        matrix = _matrix_tuple(self.matrix, name="matrix")
        periodic_axes = _pbc_tuple(self.periodic_axes)
        array = np.asarray(matrix, dtype=np.float64)
        determinant = float(np.linalg.det(array))
        tolerance = float(self.tolerance)
        if not np.isfinite(tolerance) or tolerance <= 0.0:
            raise ReferenceCellError("tolerance must be finite and positive.")
        if abs(determinant) <= tolerance:
            raise ReferenceCellError("Reference cell must be full rank.")
        if not all(periodic_axes):
            raise ReferenceCellError(
                "Initial reference-material registration requires full 3D periodicity."
            )
        handedness = 1 if determinant > 0.0 else -1
        condition_number = float(np.linalg.cond(array))
        if not np.isfinite(condition_number):
            raise ReferenceCellError("Reference-cell condition number is non-finite.")
        if self.source_kind == "selected_source_frame":
            if self.selected_frame_index is None or self.selected_frame_index < 0:
                raise ReferenceCellError(
                    "selected_source_frame requires a nonnegative selected_frame_index."
                )
            if not self.basis_gauge_signature:
                raise ReferenceCellError(
                    "selected_source_frame requires a basis_gauge_signature."
                )
        elif self.selected_frame_index is not None:
            raise ReferenceCellError(
                "explicit_matrix must not carry selected_frame_index."
            )
        payload = {
            "schema": REFERENCE_CELL_DEFINITION_SCHEMA,
            "source_kind": self.source_kind,
            "matrix": [list(row) for row in matrix],
            "periodic_axes": list(periodic_axes),
            "selected_frame_index": self.selected_frame_index,
            "handedness": handedness,
            "determinant": determinant,
            "condition_number": condition_number,
            "basis_gauge_signature": self.basis_gauge_signature,
            "tolerance": tolerance,
        }
        expected = _digest(payload)
        if self.digest and self.digest != expected:
            raise ReferenceCellError("Reference-cell digest is inconsistent.")
        object.__setattr__(self, "matrix", matrix)
        object.__setattr__(self, "periodic_axes", periodic_axes)
        object.__setattr__(self, "handedness", handedness)
        object.__setattr__(self, "determinant", determinant)
        object.__setattr__(self, "condition_number", condition_number)
        object.__setattr__(self, "tolerance", tolerance)
        object.__setattr__(self, "digest", expected)

    @classmethod
    def explicit_matrix(
        cls,
        matrix: object,
        *,
        periodic_axes: object = (True, True, True),
        tolerance: float = 1.0e-12,
    ) -> "ReferenceCellDefinition":
        return cls(
            source_kind="explicit_matrix",
            matrix=_matrix_tuple(matrix, name="matrix"),
            periodic_axes=_pbc_tuple(periodic_axes),
            selected_frame_index=None,
            handedness=0,
            determinant=0.0,
            condition_number=0.0,
            basis_gauge_signature=None,
            tolerance=tolerance,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": REFERENCE_CELL_DEFINITION_SCHEMA,
            "source_kind": self.source_kind,
            "matrix": [list(row) for row in self.matrix],
            "periodic_axes": list(self.periodic_axes),
            "selected_frame_index": self.selected_frame_index,
            "handedness": self.handedness,
            "determinant": self.determinant,
            "condition_number": self.condition_number,
            "basis_gauge_signature": self.basis_gauge_signature,
            "tolerance": self.tolerance,
            "digest": self.digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReferenceCellDefinition":
        if payload.get("schema") != REFERENCE_CELL_DEFINITION_SCHEMA:
            raise ReferenceCellError("Unsupported reference-cell schema.")
        result = cls(
            source_kind=str(payload["source_kind"]),
            matrix=_matrix_tuple(payload["matrix"], name="matrix"),
            periodic_axes=_pbc_tuple(payload["periodic_axes"]),
            selected_frame_index=(
                None
                if payload.get("selected_frame_index") is None
                else int(payload["selected_frame_index"])
            ),
            handedness=int(payload["handedness"]),
            determinant=float(payload["determinant"]),
            condition_number=float(payload["condition_number"]),
            basis_gauge_signature=(
                None
                if payload.get("basis_gauge_signature") is None
                else str(payload["basis_gauge_signature"])
            ),
            tolerance=float(payload["tolerance"]),
            digest=str(payload.get("digest", "")),
        )
        if int(payload["handedness"]) != result.handedness:
            raise ReferenceCellError("Serialized reference-cell handedness is inconsistent.")
        if not np.isclose(
            float(payload["determinant"]), result.determinant, rtol=1.0e-12, atol=0.0
        ):
            raise ReferenceCellError("Serialized reference-cell determinant is inconsistent.")
        if not np.isclose(
            float(payload["condition_number"]),
            result.condition_number,
            rtol=1.0e-12,
            atol=0.0,
        ):
            raise ReferenceCellError(
                "Serialized reference-cell condition number is inconsistent."
            )
        return result


def infer_source_field_semantics(
    collection: "AtomisticFrameCollection",
) -> SourceFieldSemantics:
    """Infer the normalized field meanings, honoring explicit source metadata."""
    explicit = collection.metadata.get("source_field_semantics")
    if isinstance(explicit, Mapping):
        payload = dict(explicit)
        payload.setdefault("schema", SOURCE_FIELD_SEMANTICS_SCHEMA)
        return SourceFieldSemantics.from_dict(payload)

    velocity_source = collection.provenance.velocity_source
    if collection.velocities is None:
        velocity_frame = VelocityFrame.UNAVAILABLE
    elif velocity_source == "finite_difference":
        velocity_frame = VelocityFrame.FINITE_DIFFERENCE_NORMALIZED_CARTESIAN
    elif velocity_source == "native":
        velocity_frame = VelocityFrame.NORMALIZED_CARTESIAN
    else:
        velocity_frame = VelocityFrame.UNKNOWN

    force_frame = (
        ForceFrame.NORMALIZED_CARTESIAN_COVECTOR
        if collection.forces is not None
        else ForceFrame.UNAVAILABLE
    )
    origin_frame = (
        BoxOriginFrame.ZERO_ORIGIN_CONVENTION
        if np.allclose(collection.origins, 0.0, rtol=0.0, atol=0.0)
        else BoxOriginFrame.LABORATORY_CARTESIAN
    )
    return SourceFieldSemantics(
        position_frame=PositionFrame.CELL_ORIGIN_RELATIVE_CARTESIAN,
        velocity_frame=velocity_frame,
        force_frame=force_frame,
        box_origin_frame=origin_frame,
    )


def resolve_force_admissibility(
    collection: "AtomisticFrameCollection",
    semantics: SourceFieldSemantics,
    *,
    provenance: ForceSourceProvenance | None = None,
) -> ForceAdmissibilityContract:
    """Resolve source-force geometry independently from PMF admissibility."""
    source = provenance
    if source is None:
        raw = collection.metadata.get("force_provenance")
        source = ForceSourceProvenance.from_mapping(raw if isinstance(raw, Mapping) else None)

    reasons: list[str] = []
    if collection.forces is None or not semantics.force_transformable:
        reasons.append("No complete force covector with known normalized frame semantics.")
        return ForceAdmissibilityContract(
            GeometricForceTransformStatus.GENERALIZED_FORCE_UNAVAILABLE,
            PMFForceAdmissibilityStatus.PMF_FORCE_PROVENANCE_UNKNOWN,
            source,
            tuple(reasons),
        )

    geometric = GeometricForceTransformStatus.EXACT_EXTERNAL_AFFINE_COVECTOR
    if (
        source.bias_or_constraint_force is EvidenceState.PRESENT
        or source.stochastic_or_thermostat_force is EvidenceState.PRESENT
    ):
        pmf = PMFForceAdmissibilityStatus.PMF_FORCE_INADMISSIBLE_UNTRACKED_BIAS_OR_CONSTRAINT
        reasons.append(
            "Bias, constraint, stochastic, or thermostat-force contamination is present."
        )
    elif (
        source.physical_force_complete is EvidenceState.ABSENT
        or source.bias_or_constraint_force is EvidenceState.UNKNOWN
        or source.stochastic_or_thermostat_force is EvidenceState.UNKNOWN
        or source.physical_force_complete is EvidenceState.UNKNOWN
    ):
        pmf = PMFForceAdmissibilityStatus.PMF_FORCE_PROVENANCE_UNKNOWN
        reasons.append("Force provenance is insufficient for a thermodynamic PMF claim.")
    else:
        pmf = PMFForceAdmissibilityStatus.PMF_FORCE_ADMISSIBLE
    return ForceAdmissibilityContract(geometric, pmf, source, tuple(reasons))
