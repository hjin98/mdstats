"""Reference-cell resolution and finite strain reconstruction for MLFF-DATA3."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)

REFERENCE_CELL_POLICY_SCHEMA = "mdstats.reference-cell-policy.v1"
REFERENCE_CELL_RECORD_SCHEMA = "mdstats.reference-cell-record.v1"
REFERENCE_CELL_RESOLUTION_SCHEMA = "mdstats.reference-cell-resolution.v1"
REFERENCE_CELL_CATALOG_SCHEMA = "mdstats.reference-cell-catalog.v1"
STRAIN_POLICY_SCHEMA = "mdstats.frame-strain-policy.v1"
FRAME_STRAIN_RECORD_SCHEMA = "mdstats.frame-strain-record.v1"

REFERENCE_CELL_POLICY_VERSION = "mdstats.mlff-data3.reference-cell.2026-07.v1"
STRAIN_POLICY_VERSION = "mdstats.mlff-data3.strain.2026-07.v1"

FloatArray = NDArray[np.float64]


def _matrix(value: ArrayLike, *, name: str) -> FloatArray:
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (3, 3) or np.any(~np.isfinite(result)):
        raise TrainingDataInputError(f"{name} must be a finite 3 x 3 matrix.")
    return result


def _tuple_matrix(value: ArrayLike) -> tuple[tuple[float, float, float], ...]:
    array = _matrix(value, name="matrix")
    return tuple(tuple(float(v) for v in row) for row in array)


def _positive(value: float, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise TrainingDataInputError(f"{name} must be finite and positive.")
    return result


class ReferenceCellResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


class ReferenceCellResolutionMode(str, Enum):
    EXPLICIT_CELL = "explicit_cell"
    EXPLICIT_REFERENCE_RUN = "explicit_reference_run"
    ASSERTED_UNSTRAINED_RUN = "asserted_unstrained_run"
    COMPATIBLE_CONSENSUS = "compatible_consensus"
    IMPLICIT_SELF_REFERENCE = "implicit_self_reference"
    UNRESOLVED = "unresolved"


class TensorStrainClass(str, Enum):
    UNSTRAINED = "unstrained"
    HYDROSTATIC = "hydrostatic"
    ORTHORHOMBIC_OR_DEVIATORIC = "orthorhombic_or_deviatoric"
    SHEAR = "shear"
    MIXED = "mixed"
    UNRESOLVED = "unresolved"


class StrainContextClass(str, Enum):
    IMPOSED_OR_STATIC = "imposed_or_static"
    VARIABLE_CELL_FLUCTUATION = "variable_cell_fluctuation"
    UNRESOLVED = "unresolved"


class AssertionVerificationStatus(str, Enum):
    VERIFIED = "verified"
    MISMATCH = "mismatch"
    NOT_PROVIDED = "not_provided"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class ReferenceCellPolicy:
    reference_frame_index: int = 0
    constant_cell_rtol: float = 1.0e-8
    constant_cell_atol_angstrom: float = 1.0e-8
    allow_variable_reference_run: bool = False
    policy_version: str = REFERENCE_CELL_POLICY_VERSION

    def __post_init__(self) -> None:
        if isinstance(self.reference_frame_index, bool) or self.reference_frame_index < 0:
            raise TrainingDataInputError("reference_frame_index must be nonnegative.")
        object.__setattr__(
            self, "constant_cell_rtol", _positive(self.constant_cell_rtol, name="constant_cell_rtol")
        )
        object.__setattr__(
            self,
            "constant_cell_atol_angstrom",
            _positive(self.constant_cell_atol_angstrom, name="constant_cell_atol_angstrom"),
        )
        if not self.policy_version.strip():
            raise TrainingDataInputError("policy_version must be non-empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": REFERENCE_CELL_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "reference_frame_index": self.reference_frame_index,
            "constant_cell_rtol": self.constant_cell_rtol,
            "constant_cell_atol_angstrom": self.constant_cell_atol_angstrom,
            "allow_variable_reference_run": self.allow_variable_reference_run,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReferenceCellPolicy":
        if payload.get("schema") != REFERENCE_CELL_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported reference-cell policy schema.")
        result = cls(
            reference_frame_index=int(payload["reference_frame_index"]),
            constant_cell_rtol=float(payload["constant_cell_rtol"]),
            constant_cell_atol_angstrom=float(payload["constant_cell_atol_angstrom"]),
            allow_variable_reference_run=bool(payload["allow_variable_reference_run"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Reference-cell policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ReferenceCellRecord:
    reference_cell_id: str
    reference_group: str
    resolution_mode: ReferenceCellResolutionMode
    source_run_id: str | None
    source_frame_index: int | None
    cell_matrix_angstrom: tuple[tuple[float, float, float], ...]
    determinant_angstrom3: float
    policy_digest: str
    notes: tuple[str, ...] = ()
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "reference_cell_id", validate_digest(self.reference_cell_id, name="reference_cell_id"))
        object.__setattr__(self, "resolution_mode", ReferenceCellResolutionMode(self.resolution_mode))
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        matrix = _tuple_matrix(self.cell_matrix_angstrom)
        object.__setattr__(self, "cell_matrix_angstrom", matrix)
        det = float(np.linalg.det(np.asarray(matrix, dtype=np.float64)))
        if det <= 0.0 or not np.isfinite(det):
            raise TrainingDataInputError("Reference cell must be right-handed with positive volume.")
        if not np.isclose(det, self.determinant_angstrom3, rtol=1e-12, atol=1e-12):
            raise TrainingDataInputError("Reference-cell determinant is inconsistent.")
        object.__setattr__(self, "determinant_angstrom3", det)
        object.__setattr__(self, "notes", tuple(str(item) for item in self.notes))

    @classmethod
    def create(
        cls,
        *,
        reference_group: str,
        resolution_mode: ReferenceCellResolutionMode,
        source_run_id: str | None,
        source_frame_index: int | None,
        cell_matrix_angstrom: ArrayLike,
        policy_digest: str,
        notes: Sequence[str] = (),
    ) -> "ReferenceCellRecord":
        cell = _matrix(cell_matrix_angstrom, name="cell_matrix_angstrom")
        det = float(np.linalg.det(cell))
        identifier = digest(
            {
                "schema": "mdstats.reference-cell-id.v1",
                "reference_group": reference_group,
                "cell_matrix_angstrom": cell.tolist(),
                "policy_digest": policy_digest,
            }
        )
        return cls(
            reference_cell_id=identifier,
            reference_group=reference_group,
            resolution_mode=resolution_mode,
            source_run_id=source_run_id,
            source_frame_index=source_frame_index,
            cell_matrix_angstrom=_tuple_matrix(cell),
            determinant_angstrom3=det,
            policy_digest=policy_digest,
            notes=tuple(notes),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": REFERENCE_CELL_RECORD_SCHEMA,
            "reference_cell_id": self.reference_cell_id,
            "reference_group": self.reference_group,
            "resolution_mode": self.resolution_mode.value,
            "source_run_id": self.source_run_id,
            "source_frame_index": self.source_frame_index,
            "cell_matrix_angstrom": [list(row) for row in self.cell_matrix_angstrom],
            "determinant_angstrom3": self.determinant_angstrom3,
            "policy_digest": self.policy_digest,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(payload)
            object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReferenceCellRecord":
        if payload.get("schema") != REFERENCE_CELL_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported reference-cell-record schema.")
        result = cls(
            reference_cell_id=str(payload["reference_cell_id"]),
            reference_group=str(payload["reference_group"]),
            resolution_mode=ReferenceCellResolutionMode(payload["resolution_mode"]),
            source_run_id=None if payload.get("source_run_id") is None else str(payload["source_run_id"]),
            source_frame_index=None if payload.get("source_frame_index") is None else int(payload["source_frame_index"]),
            cell_matrix_angstrom=tuple(tuple(float(v) for v in row) for row in payload["cell_matrix_angstrom"]),
            determinant_angstrom3=float(payload["determinant_angstrom3"]),
            policy_digest=str(payload["policy_digest"]),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Reference-cell-record digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ReferenceCellResolution:
    run_id: str
    reference_group: str | None
    status: ReferenceCellResolutionStatus
    mode: ReferenceCellResolutionMode
    reference_cell_id: str | None
    reasons: tuple[str, ...]
    policy_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", ReferenceCellResolutionStatus(self.status))
        object.__setattr__(self, "mode", ReferenceCellResolutionMode(self.mode))
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        if self.reference_cell_id is not None:
            object.__setattr__(self, "reference_cell_id", validate_digest(self.reference_cell_id, name="reference_cell_id"))
        if self.status is ReferenceCellResolutionStatus.RESOLVED and self.reference_cell_id is None:
            raise TrainingDataInputError("Resolved reference-cell assignment needs an ID.")
        if self.status is ReferenceCellResolutionStatus.UNRESOLVED and self.reference_cell_id is not None:
            raise TrainingDataInputError("Unresolved reference-cell assignment cannot have an ID.")
        object.__setattr__(self, "reasons", tuple(str(v) for v in self.reasons))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": REFERENCE_CELL_RESOLUTION_SCHEMA,
            "run_id": self.run_id,
            "reference_group": self.reference_group,
            "status": self.status.value,
            "mode": self.mode.value,
            "reference_cell_id": self.reference_cell_id,
            "reasons": list(self.reasons),
            "policy_digest": self.policy_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReferenceCellResolution":
        if payload.get("schema") != REFERENCE_CELL_RESOLUTION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported reference-cell-resolution schema.")
        result = cls(
            run_id=str(payload["run_id"]),
            reference_group=None if payload.get("reference_group") is None else str(payload["reference_group"]),
            status=ReferenceCellResolutionStatus(payload["status"]),
            mode=ReferenceCellResolutionMode(payload["mode"]),
            reference_cell_id=None if payload.get("reference_cell_id") is None else str(payload["reference_cell_id"]),
            reasons=tuple(str(v) for v in payload.get("reasons", ())),
            policy_digest=str(payload["policy_digest"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Reference-cell-resolution digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ReferenceCellCatalog:
    policy_digest: str
    records: tuple[ReferenceCellRecord, ...]
    resolutions: tuple[ReferenceCellResolution, ...]
    _record_by_id: dict[str, ReferenceCellRecord] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _resolution_by_run: dict[str, ReferenceCellResolution] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _content_digest_cache: str | None = field(
        default=None, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        records = tuple(sorted(self.records, key=lambda item: item.reference_cell_id))
        resolutions = tuple(sorted(self.resolutions, key=lambda item: item.run_id))
        if len({item.reference_cell_id for item in records}) != len(records):
            raise TrainingDataInputError("Duplicate reference-cell IDs.")
        if len({item.run_id for item in resolutions}) != len(resolutions):
            raise TrainingDataInputError("Duplicate run resolutions.")
        known = {item.reference_cell_id for item in records}
        if any(item.reference_cell_id not in known for item in resolutions if item.reference_cell_id is not None):
            raise TrainingDataInputError("Reference-cell resolution points to an unknown record.")
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "resolutions", resolutions)
        object.__setattr__(
            self, "_record_by_id", {item.reference_cell_id: item for item in records}
        )
        object.__setattr__(
            self, "_resolution_by_run", {item.run_id: item for item in resolutions}
        )

    def record(self, reference_cell_id: str) -> ReferenceCellRecord:
        try:
            return self._record_by_id[reference_cell_id]
        except KeyError:
            raise KeyError(reference_cell_id) from None

    def resolution_for_run(self, run_id: str) -> ReferenceCellResolution:
        try:
            return self._resolution_by_run[run_id]
        except KeyError:
            raise KeyError(run_id) from None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": REFERENCE_CELL_CATALOG_SCHEMA,
            "policy_digest": self.policy_digest,
            "records": [item.to_dict() for item in self.records],
            "resolutions": [item.to_dict() for item in self.resolutions],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(payload)
            object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReferenceCellCatalog":
        if payload.get("schema") != REFERENCE_CELL_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported reference-cell-catalog schema.")
        result = cls(
            policy_digest=str(payload["policy_digest"]),
            records=tuple(ReferenceCellRecord.from_dict(v) for v in payload.get("records", ())),
            resolutions=tuple(ReferenceCellResolution.from_dict(v) for v in payload.get("resolutions", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Reference-cell-catalog digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class StrainPolicy:
    unstrained_norm_tolerance: float = 1.0e-7
    hydrostatic_deviatoric_tolerance: float = 1.0e-6
    orthorhombic_offdiagonal_tolerance: float = 1.0e-6
    shear_diagonal_tolerance: float = 1.0e-6
    shear_hydrostatic_tolerance: float = 1.0e-6
    assertion_magnitude_tolerance: float = 5.0e-4
    policy_version: str = STRAIN_POLICY_VERSION

    def __post_init__(self) -> None:
        for name in (
            "unstrained_norm_tolerance",
            "hydrostatic_deviatoric_tolerance",
            "orthorhombic_offdiagonal_tolerance",
            "shear_diagonal_tolerance",
            "shear_hydrostatic_tolerance",
            "assertion_magnitude_tolerance",
        ):
            object.__setattr__(self, name, _positive(getattr(self, name), name=name))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": STRAIN_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "unstrained_norm_tolerance": self.unstrained_norm_tolerance,
            "hydrostatic_deviatoric_tolerance": self.hydrostatic_deviatoric_tolerance,
            "orthorhombic_offdiagonal_tolerance": self.orthorhombic_offdiagonal_tolerance,
            "shear_diagonal_tolerance": self.shear_diagonal_tolerance,
            "shear_hydrostatic_tolerance": self.shear_hydrostatic_tolerance,
            "assertion_magnitude_tolerance": self.assertion_magnitude_tolerance,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StrainPolicy":
        if payload.get("schema") != STRAIN_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported strain-policy schema.")
        result = cls(
            unstrained_norm_tolerance=float(payload["unstrained_norm_tolerance"]),
            hydrostatic_deviatoric_tolerance=float(payload["hydrostatic_deviatoric_tolerance"]),
            orthorhombic_offdiagonal_tolerance=float(payload["orthorhombic_offdiagonal_tolerance"]),
            shear_diagonal_tolerance=float(payload["shear_diagonal_tolerance"]),
            shear_hydrostatic_tolerance=float(payload["shear_hydrostatic_tolerance"]),
            assertion_magnitude_tolerance=float(payload["assertion_magnitude_tolerance"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Strain-policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class FrameStrainRecord:
    frame_uid: str
    reference_cell_id: str | None
    policy_digest: str
    status: str
    tensor_class: TensorStrainClass
    context_class: StrainContextClass
    deformation_gradient: tuple[tuple[float, float, float], ...] | None
    rotation_matrix: tuple[tuple[float, float, float], ...] | None
    right_stretch: tuple[tuple[float, float, float], ...] | None
    linear_strain: tuple[tuple[float, float, float], ...] | None
    green_lagrange_strain: tuple[tuple[float, float, float], ...] | None
    logarithmic_strain: tuple[tuple[float, float, float], ...] | None
    volume_ratio: float | None
    rotation_angle_radians: float | None
    principal_logarithmic_strains: tuple[float, float, float] | None
    hydrostatic_logarithmic_strain: float | None
    deviatoric_norm: float | None
    engineering_shear: tuple[float, float, float] | None
    assertion_status: AssertionVerificationStatus
    assertion_reasons: tuple[str, ...]
    failure_reasons: tuple[str, ...]
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "frame_uid", validate_digest(self.frame_uid, name="frame_uid"))
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        if self.reference_cell_id is not None:
            object.__setattr__(self, "reference_cell_id", validate_digest(self.reference_cell_id, name="reference_cell_id"))
        object.__setattr__(self, "tensor_class", TensorStrainClass(self.tensor_class))
        object.__setattr__(self, "context_class", StrainContextClass(self.context_class))
        object.__setattr__(self, "assertion_status", AssertionVerificationStatus(self.assertion_status))
        object.__setattr__(self, "assertion_reasons", tuple(str(v) for v in self.assertion_reasons))
        object.__setattr__(self, "failure_reasons", tuple(str(v) for v in self.failure_reasons))

    def _payload(self) -> dict[str, Any]:
        def matrix(value: Any) -> Any:
            return None if value is None else [list(row) for row in value]
        return {
            "schema": FRAME_STRAIN_RECORD_SCHEMA,
            "frame_uid": self.frame_uid,
            "reference_cell_id": self.reference_cell_id,
            "policy_digest": self.policy_digest,
            "status": self.status,
            "tensor_class": self.tensor_class.value,
            "context_class": self.context_class.value,
            "deformation_gradient": matrix(self.deformation_gradient),
            "rotation_matrix": matrix(self.rotation_matrix),
            "right_stretch": matrix(self.right_stretch),
            "linear_strain": matrix(self.linear_strain),
            "green_lagrange_strain": matrix(self.green_lagrange_strain),
            "logarithmic_strain": matrix(self.logarithmic_strain),
            "volume_ratio": self.volume_ratio,
            "rotation_angle_radians": self.rotation_angle_radians,
            "principal_logarithmic_strains": None if self.principal_logarithmic_strains is None else list(self.principal_logarithmic_strains),
            "hydrostatic_logarithmic_strain": self.hydrostatic_logarithmic_strain,
            "deviatoric_norm": self.deviatoric_norm,
            "engineering_shear": None if self.engineering_shear is None else list(self.engineering_shear),
            "assertion_status": self.assertion_status.value,
            "assertion_reasons": list(self.assertion_reasons),
            "failure_reasons": list(self.failure_reasons),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(payload)
            object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameStrainRecord":
        if payload.get("schema") != FRAME_STRAIN_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported frame-strain-record schema.")
        def matrix(name: str) -> Any:
            value = payload.get(name)
            return None if value is None else tuple(tuple(float(v) for v in row) for row in value)
        result = cls(
            frame_uid=str(payload["frame_uid"]),
            reference_cell_id=None if payload.get("reference_cell_id") is None else str(payload["reference_cell_id"]),
            policy_digest=str(payload["policy_digest"]),
            status=str(payload["status"]),
            tensor_class=TensorStrainClass(payload["tensor_class"]),
            context_class=StrainContextClass(payload["context_class"]),
            deformation_gradient=matrix("deformation_gradient"),
            rotation_matrix=matrix("rotation_matrix"),
            right_stretch=matrix("right_stretch"),
            linear_strain=matrix("linear_strain"),
            green_lagrange_strain=matrix("green_lagrange_strain"),
            logarithmic_strain=matrix("logarithmic_strain"),
            volume_ratio=None if payload.get("volume_ratio") is None else float(payload["volume_ratio"]),
            rotation_angle_radians=None if payload.get("rotation_angle_radians") is None else float(payload["rotation_angle_radians"]),
            principal_logarithmic_strains=None if payload.get("principal_logarithmic_strains") is None else tuple(float(v) for v in payload["principal_logarithmic_strains"]),
            hydrostatic_logarithmic_strain=None if payload.get("hydrostatic_logarithmic_strain") is None else float(payload["hydrostatic_logarithmic_strain"]),
            deviatoric_norm=None if payload.get("deviatoric_norm") is None else float(payload["deviatoric_norm"]),
            engineering_shear=None if payload.get("engineering_shear") is None else tuple(float(v) for v in payload["engineering_shear"]),
            assertion_status=AssertionVerificationStatus(payload["assertion_status"]),
            assertion_reasons=tuple(str(v) for v in payload.get("assertion_reasons", ())),
            failure_reasons=tuple(str(v) for v in payload.get("failure_reasons", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Frame-strain-record digest mismatch.")
        return result


def _cells_constant(cells: np.ndarray, policy: ReferenceCellPolicy) -> bool:
    if cells.ndim != 3 or cells.shape[1:] != (3, 3):
        raise TrainingDataInputError("cells must have shape (n_frames, 3, 3).")
    return bool(np.allclose(cells, cells[0], rtol=policy.constant_cell_rtol, atol=policy.constant_cell_atol_angstrom))


def _assertion_map(source: Any) -> dict[str, Any]:
    return dict(source.assertions)


def _asserted_unstrained(source: Any) -> bool:
    assertions = _assertion_map(source)
    value = str(assertions.get("intended_strain_class", "")).strip().lower()
    if value in {"unstrained", "none", "reference"}:
        return True
    return bool(assertions.get("is_reference_cell", False))


def build_reference_cell_catalog(
    sources: Sequence[Any],
    *,
    cells_by_run: Mapping[str, ArrayLike],
    explicit_cells_by_group: Mapping[str, ArrayLike] | None = None,
    policy: ReferenceCellPolicy | None = None,
) -> ReferenceCellCatalog:
    active = ReferenceCellPolicy() if policy is None else policy
    explicit = {} if explicit_cells_by_group is None else dict(explicit_cells_by_group)
    source_map = {item.run_id: item for item in sources}
    arrays = {run_id: np.asarray(value, dtype=np.float64) for run_id, value in cells_by_run.items()}
    if set(source_map) != set(arrays):
        missing = sorted(set(source_map) - set(arrays))
        extra = sorted(set(arrays) - set(source_map))
        raise TrainingDataInputError(f"Cell-run mapping mismatch; missing={missing}, extra={extra}.")

    records_by_key: dict[tuple[str, str], ReferenceCellRecord] = {}
    resolutions: list[ReferenceCellResolution] = []
    # A reference run can serve many strained siblings.  Cell constancy is a
    # run property; evaluate it once instead of rescanning every frame for each
    # sibling (formerly O(S * N_ref) for S references to one trajectory).
    constant_cell_by_run = {
        run_id: _cells_constant(cells, active)
        for run_id, cells in arrays.items()
    }

    def register(
        group: str,
        mode: ReferenceCellResolutionMode,
        cell: np.ndarray,
        run_id: str | None,
        frame_index: int | None,
        notes: Sequence[str] = (),
    ) -> ReferenceCellRecord:
        record = ReferenceCellRecord.create(
            reference_group=group,
            resolution_mode=mode,
            source_run_id=run_id,
            source_frame_index=frame_index,
            cell_matrix_angstrom=cell,
            policy_digest=active.policy_digest,
            notes=notes,
        )
        records_by_key[(group, record.reference_cell_id)] = record
        return record

    groups: dict[str, list[Any]] = {}
    for source in sources:
        if source.reference_group is not None:
            groups.setdefault(source.reference_group, []).append(source)
    unknown_explicit = sorted(set(explicit) - set(groups))
    if unknown_explicit:
        raise TrainingDataInputError(
            "Explicit reference cells name unknown groups: "
            + ", ".join(unknown_explicit)
        )

    group_defaults: dict[str, ReferenceCellRecord] = {}
    for group, members in groups.items():
        if group in explicit:
            group_defaults[group] = register(
                group, ReferenceCellResolutionMode.EXPLICIT_CELL,
                _matrix(explicit[group], name=f"explicit cell {group}"), None, None,
            )
            continue
        asserted = [item for item in members if _asserted_unstrained(item)]
        candidates = asserted if asserted else [item for item in members if item.reference_run_id is None]
        candidate_cells: list[tuple[Any, np.ndarray]] = []
        for item in candidates:
            cells = arrays[item.run_id]
            if active.reference_frame_index >= cells.shape[0]:
                continue
            if not constant_cell_by_run[item.run_id] and not active.allow_variable_reference_run:
                continue
            candidate_cells.append((item, cells[active.reference_frame_index]))
        if len(candidate_cells) == 1:
            item, cell = candidate_cells[0]
            mode = ReferenceCellResolutionMode.ASSERTED_UNSTRAINED_RUN if asserted else ReferenceCellResolutionMode.COMPATIBLE_CONSENSUS
            group_defaults[group] = register(group, mode, cell, item.run_id, active.reference_frame_index)
        elif len(candidate_cells) > 1:
            first = candidate_cells[0][1]
            if all(np.allclose(cell, first, rtol=active.constant_cell_rtol, atol=active.constant_cell_atol_angstrom) for _, cell in candidate_cells[1:]):
                group_defaults[group] = register(
                    group, ReferenceCellResolutionMode.COMPATIBLE_CONSENSUS, first,
                    candidate_cells[0][0].run_id, active.reference_frame_index,
                    notes=("Equivalent constant cells from multiple unstrained candidates.",),
                )

    for source in sources:
        group = source.reference_group
        if group is None:
            # A fixed-cell trajectory with no declared cross-run strain
            # relationship has an unambiguous local baseline: its selected
            # reference frame.  Previously every such ordinary production run
            # was marked unresolved, even though only intentionally strained
            # siblings need an external reference_group/reference_run_id.
            cells = arrays[source.run_id]
            if active.reference_frame_index >= cells.shape[0]:
                resolutions.append(ReferenceCellResolution(
                    run_id=source.run_id, reference_group=None,
                    status=ReferenceCellResolutionStatus.UNRESOLVED,
                    mode=ReferenceCellResolutionMode.UNRESOLVED,
                    reference_cell_id=None,
                    reasons=("Reference frame index exceeds the source run.",),
                    policy_digest=active.policy_digest,
                ))
                continue
            if not constant_cell_by_run[source.run_id] and not active.allow_variable_reference_run:
                resolutions.append(ReferenceCellResolution(
                    run_id=source.run_id, reference_group=None,
                    status=ReferenceCellResolutionStatus.UNRESOLVED,
                    mode=ReferenceCellResolutionMode.UNRESOLVED,
                    reference_cell_id=None,
                    reasons=(
                        "No reference_group was declared and the source has variable cells under a constant-cell policy.",
                    ),
                    policy_digest=active.policy_digest,
                ))
                continue
            implicit_group = f"__mdstats_self_reference__:{source.run_id}"
            record = register(
                implicit_group,
                ReferenceCellResolutionMode.IMPLICIT_SELF_REFERENCE,
                cells[active.reference_frame_index],
                source.run_id,
                active.reference_frame_index,
                notes=(
                    "Implicit per-run baseline used because no cross-run reference_group was declared.",
                ),
            )
            resolutions.append(ReferenceCellResolution(
                run_id=source.run_id,
                reference_group=None,
                status=ReferenceCellResolutionStatus.RESOLVED,
                mode=ReferenceCellResolutionMode.IMPLICIT_SELF_REFERENCE,
                reference_cell_id=record.reference_cell_id,
                reasons=(),
                policy_digest=active.policy_digest,
            ))
            continue
        if group in explicit:
            record = group_defaults[group]
            resolutions.append(ReferenceCellResolution(
                run_id=source.run_id, reference_group=group,
                status=ReferenceCellResolutionStatus.RESOLVED,
                mode=ReferenceCellResolutionMode.EXPLICIT_CELL,
                reference_cell_id=record.reference_cell_id,
                reasons=(), policy_digest=active.policy_digest,
            ))
            continue
        if source.reference_run_id is not None:
            reference_source = source_map.get(source.reference_run_id)
            if reference_source is None:
                resolutions.append(ReferenceCellResolution(
                    run_id=source.run_id, reference_group=group,
                    status=ReferenceCellResolutionStatus.UNRESOLVED,
                    mode=ReferenceCellResolutionMode.UNRESOLVED,
                    reference_cell_id=None,
                    reasons=(f"Unknown reference_run_id {source.reference_run_id!r}.",),
                    policy_digest=active.policy_digest,
                ))
                continue
            if reference_source.reference_group != group:
                resolutions.append(ReferenceCellResolution(
                    run_id=source.run_id, reference_group=group,
                    status=ReferenceCellResolutionStatus.UNRESOLVED,
                    mode=ReferenceCellResolutionMode.UNRESOLVED,
                    reference_cell_id=None,
                    reasons=(
                        f"reference_run_id {source.reference_run_id!r} belongs to "
                        f"reference_group {reference_source.reference_group!r}, not {group!r}.",
                    ),
                    policy_digest=active.policy_digest,
                ))
                continue
            cells = arrays[reference_source.run_id]
            if active.reference_frame_index >= cells.shape[0]:
                reason = "Reference frame index exceeds the reference run."
            elif not constant_cell_by_run[reference_source.run_id] and not active.allow_variable_reference_run:
                reason = "Reference run has variable cells under a constant-cell policy."
            else:
                record = register(
                    group, ReferenceCellResolutionMode.EXPLICIT_REFERENCE_RUN,
                    cells[active.reference_frame_index], reference_source.run_id,
                    active.reference_frame_index,
                )
                resolutions.append(ReferenceCellResolution(
                    run_id=source.run_id, reference_group=group,
                    status=ReferenceCellResolutionStatus.RESOLVED,
                    mode=ReferenceCellResolutionMode.EXPLICIT_REFERENCE_RUN,
                    reference_cell_id=record.reference_cell_id,
                    reasons=(), policy_digest=active.policy_digest,
                ))
                continue
            resolutions.append(ReferenceCellResolution(
                run_id=source.run_id, reference_group=group,
                status=ReferenceCellResolutionStatus.UNRESOLVED,
                mode=ReferenceCellResolutionMode.UNRESOLVED,
                reference_cell_id=None, reasons=(reason,),
                policy_digest=active.policy_digest,
            ))
            continue
        record = group_defaults.get(group)
        if record is None:
            resolutions.append(ReferenceCellResolution(
                run_id=source.run_id, reference_group=group,
                status=ReferenceCellResolutionStatus.UNRESOLVED,
                mode=ReferenceCellResolutionMode.UNRESOLVED,
                reference_cell_id=None,
                reasons=("No unique compatible reference cell could be resolved.",),
                policy_digest=active.policy_digest,
            ))
        else:
            resolutions.append(ReferenceCellResolution(
                run_id=source.run_id, reference_group=group,
                status=ReferenceCellResolutionStatus.RESOLVED,
                mode=record.resolution_mode,
                reference_cell_id=record.reference_cell_id,
                reasons=(), policy_digest=active.policy_digest,
            ))

    return ReferenceCellCatalog(
        policy_digest=active.policy_digest,
        records=tuple(records_by_key.values()),
        resolutions=tuple(resolutions),
    )


def _polar_decomposition(deformation: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    left, singular, right_t = np.linalg.svd(deformation)
    rotation = left @ right_t
    if np.linalg.det(rotation) < 0.0:
        left = left.copy()
        left[:, -1] *= -1.0
        singular = singular.copy()
        singular[-1] *= -1.0
        rotation = left @ right_t
    if np.linalg.det(rotation) <= 0.0 or np.any(singular <= 0.0):
        raise TrainingDataInputError("Deformation does not admit a proper positive polar decomposition.")
    right = right_t.T
    stretch = right @ np.diag(singular) @ right_t
    logarithmic = right @ np.diag(np.log(singular)) @ right_t
    return rotation, stretch, logarithmic


def _tensor_class(logarithmic: np.ndarray, policy: StrainPolicy) -> TensorStrainClass:
    norm = float(np.linalg.norm(logarithmic))
    if norm <= policy.unstrained_norm_tolerance:
        return TensorStrainClass.UNSTRAINED
    hydro = float(np.trace(logarithmic) / 3.0)
    deviatoric = logarithmic - hydro * np.eye(3)
    dev_norm = float(np.linalg.norm(deviatoric))
    scale = max(1.0, norm)
    if dev_norm <= policy.hydrostatic_deviatoric_tolerance * scale:
        return TensorStrainClass.HYDROSTATIC
    off = deviatoric - np.diag(np.diag(deviatoric))
    off_norm = float(np.linalg.norm(off))
    diag_norm = float(np.linalg.norm(np.diag(deviatoric)))
    if off_norm <= policy.orthorhombic_offdiagonal_tolerance * scale:
        return TensorStrainClass.ORTHORHOMBIC_OR_DEVIATORIC
    shear_diag_limit = max(
        policy.shear_diagonal_tolerance * scale,
        0.10 * off_norm,
    )
    if (
        diag_norm <= shear_diag_limit
        and abs(hydro) <= policy.shear_hydrostatic_tolerance * scale
    ):
        return TensorStrainClass.SHEAR
    return TensorStrainClass.MIXED


def _rotation_angle(rotation: np.ndarray) -> float:
    cosine = float(np.clip((np.trace(rotation) - 1.0) / 2.0, -1.0, 1.0))
    return float(np.arccos(cosine))


def _assertion_status(
    assertions: Mapping[str, Any],
    *,
    tensor_class: TensorStrainClass,
    volume_ratio: float,
    principal: np.ndarray,
    engineering_shear: tuple[float, float, float],
    policy: StrainPolicy,
) -> tuple[AssertionVerificationStatus, tuple[str, ...]]:
    intended_class = assertions.get("intended_strain_class")
    intended_volume = assertions.get("intended_volume_change")
    intended_magnitude = assertions.get("intended_strain_magnitude")
    if intended_class is None and intended_volume is None and intended_magnitude is None:
        return AssertionVerificationStatus.NOT_PROVIDED, ()
    reasons: list[str] = []
    if intended_class is not None:
        normalized = str(intended_class).strip().lower().replace("-", "_")
        aliases = {
            "none": TensorStrainClass.UNSTRAINED.value,
            "orthorhombic": TensorStrainClass.ORTHORHOMBIC_OR_DEVIATORIC.value,
            "deviatoric": TensorStrainClass.ORTHORHOMBIC_OR_DEVIATORIC.value,
            "engineering_shear": TensorStrainClass.SHEAR.value,
        }
        expected = aliases.get(normalized, normalized)
        if expected != tensor_class.value:
            reasons.append(f"intended_strain_class={intended_class!r} but calculated {tensor_class.value!r}.")
    if intended_volume is not None:
        try:
            expected_volume = float(intended_volume)
            if abs((volume_ratio - 1.0) - expected_volume) > policy.assertion_magnitude_tolerance:
                reasons.append("intended_volume_change does not match calculated volume ratio.")
        except (TypeError, ValueError):
            reasons.append("intended_volume_change is not numerical.")
    if intended_magnitude is not None:
        try:
            expected = abs(float(intended_magnitude))
            if tensor_class is TensorStrainClass.SHEAR:
                actual = max(abs(v) for v in engineering_shear)
            elif tensor_class is TensorStrainClass.HYDROSTATIC:
                actual = abs(volume_ratio - 1.0)
            else:
                actual = float(np.max(np.abs(principal)))
            if abs(actual - expected) > policy.assertion_magnitude_tolerance:
                reasons.append("intended_strain_magnitude does not match calculated strain.")
        except (TypeError, ValueError):
            reasons.append("intended_strain_magnitude is not numerical.")
    return (
        (AssertionVerificationStatus.VERIFIED if not reasons else AssertionVerificationStatus.MISMATCH),
        tuple(reasons),
    )


def compute_frame_strain(
    *,
    frame_uid: str,
    current_cell_angstrom: ArrayLike,
    reference: ReferenceCellRecord | None,
    ensemble: str,
    assertions: Mapping[str, Any] | None = None,
    policy: StrainPolicy | None = None,
) -> FrameStrainRecord:
    active = StrainPolicy() if policy is None else policy
    if reference is None:
        return FrameStrainRecord(
            frame_uid=frame_uid,
            reference_cell_id=None,
            policy_digest=active.policy_digest,
            status="unresolved",
            tensor_class=TensorStrainClass.UNRESOLVED,
            context_class=StrainContextClass.UNRESOLVED,
            deformation_gradient=None,
            rotation_matrix=None,
            right_stretch=None,
            linear_strain=None,
            green_lagrange_strain=None,
            logarithmic_strain=None,
            volume_ratio=None,
            rotation_angle_radians=None,
            principal_logarithmic_strains=None,
            hydrostatic_logarithmic_strain=None,
            deviatoric_norm=None,
            engineering_shear=None,
            assertion_status=AssertionVerificationStatus.UNRESOLVED,
            assertion_reasons=(),
            failure_reasons=("Reference cell is unresolved.",),
        )
    try:
        current = _matrix(current_cell_angstrom, name="current_cell_angstrom")
        reference_cell = np.asarray(reference.cell_matrix_angstrom, dtype=np.float64)
        if np.linalg.det(current) <= 0.0:
            raise TrainingDataInputError("Current cell is not right-handed with positive volume.")
        deformation = (np.linalg.solve(reference_cell, current)).T
        volume_ratio = float(np.linalg.det(deformation))
        if not np.isfinite(volume_ratio) or volume_ratio <= 0.0:
            raise TrainingDataInputError("Deformation gradient has nonpositive determinant.")
        rotation, stretch, logarithmic = _polar_decomposition(deformation)
        identity = np.eye(3)
        linear = 0.5 * (deformation + deformation.T) - identity
        green = 0.5 * (deformation.T @ deformation - identity)
        principal = np.linalg.eigvalsh(logarithmic)
        hydro = float(np.trace(logarithmic) / 3.0)
        dev_norm = float(np.linalg.norm(logarithmic - hydro * identity))
        engineering = (
            float(2.0 * logarithmic[0, 1]),
            float(2.0 * logarithmic[1, 2]),
            float(2.0 * logarithmic[2, 0]),
        )
        tensor_class = _tensor_class(logarithmic, active)
        assertion_status, assertion_reasons = _assertion_status(
            {} if assertions is None else assertions,
            tensor_class=tensor_class,
            volume_ratio=volume_ratio,
            principal=principal,
            engineering_shear=engineering,
            policy=active,
        )
        ensemble_lower = ensemble.lower()
        context = (
            StrainContextClass.VARIABLE_CELL_FLUCTUATION
            if any(token in ensemble_lower for token in ("npt", "nph", "isothermal_isobaric", "isobaric"))
            and not (assertions or {}).get("intended_strain_class")
            else StrainContextClass.IMPOSED_OR_STATIC
        )
        return FrameStrainRecord(
            frame_uid=frame_uid,
            reference_cell_id=reference.reference_cell_id,
            policy_digest=active.policy_digest,
            status="resolved",
            tensor_class=tensor_class,
            context_class=context,
            deformation_gradient=_tuple_matrix(deformation),
            rotation_matrix=_tuple_matrix(rotation),
            right_stretch=_tuple_matrix(stretch),
            linear_strain=_tuple_matrix(linear),
            green_lagrange_strain=_tuple_matrix(green),
            logarithmic_strain=_tuple_matrix(logarithmic),
            volume_ratio=volume_ratio,
            rotation_angle_radians=_rotation_angle(rotation),
            principal_logarithmic_strains=tuple(float(v) for v in principal),
            hydrostatic_logarithmic_strain=hydro,
            deviatoric_norm=dev_norm,
            engineering_shear=engineering,
            assertion_status=assertion_status,
            assertion_reasons=assertion_reasons,
            failure_reasons=(),
        )
    except (np.linalg.LinAlgError, TrainingDataInputError) as exc:
        return FrameStrainRecord(
            frame_uid=frame_uid,
            reference_cell_id=reference.reference_cell_id,
            policy_digest=active.policy_digest,
            status="unresolved",
            tensor_class=TensorStrainClass.UNRESOLVED,
            context_class=StrainContextClass.UNRESOLVED,
            deformation_gradient=None,
            rotation_matrix=None,
            right_stretch=None,
            linear_strain=None,
            green_lagrange_strain=None,
            logarithmic_strain=None,
            volume_ratio=None,
            rotation_angle_radians=None,
            principal_logarithmic_strains=None,
            hydrostatic_logarithmic_strain=None,
            deviatoric_norm=None,
            engineering_shear=None,
            assertion_status=AssertionVerificationStatus.UNRESOLVED,
            assertion_reasons=(),
            failure_reasons=(f"{type(exc).__name__}: {exc}",),
        )
