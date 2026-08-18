"""Stage-C0A1 periodic lattice-basis gauge and source-contract audit."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping

import numpy as np

from ..collection import AtomisticFrameCollection
from .contracts import (
    COORDINATE_CONTRACT_DIGEST_ALGORITHM,
    SOURCE_COORDINATE_CONTRACT_SCHEMA,
    ForceAdmissibilityContract,
    ForceSourceProvenance,
    ReferenceCellDefinition,
    SourceFieldSemantics,
    infer_source_field_semantics,
    resolve_force_admissibility,
)

PERIODIC_LATTICE_GAUGE_SCHEMA = "mdstats.periodic-lattice-gauge.v1"


class LatticeGaugeError(ValueError):
    """Base exception for periodic lattice-gauge validation."""


class CellHandednessError(LatticeGaugeError):
    """Raised when source-cell handedness changes or violates policy."""


class UnsupportedBasisChangeError(LatticeGaugeError):
    """Raised when a detected unimodular relabeling is not enabled."""


class LatticeBasisContinuityError(LatticeGaugeError):
    """Raised when cell identity cannot be continued safely."""


class LatticeGaugeFrameStatus(str, Enum):
    REFERENCE = "reference"
    CONTINUOUS_REPORTED_BASIS = "continuous_reported_basis"
    RECONCILED_UNIMODULAR_BASIS = "reconciled_unimodular_basis"


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


def _matrix_float_tuple(value: object) -> tuple[tuple[float, float, float], ...]:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (3, 3) or not np.all(np.isfinite(array)):
        raise LatticeGaugeError("Cell matrices must be finite 3x3 arrays.")
    return tuple(tuple(float(item) for item in row) for row in array)


def _matrix_int_tuple(value: object) -> tuple[tuple[int, int, int], ...]:
    array = np.asarray(value, dtype=np.int64)
    if array.shape != (3, 3):
        raise LatticeGaugeError("Gauge matrices must have shape (3, 3).")
    return tuple(tuple(int(item) for item in row) for row in array)


def _relative_matrix_difference(first: np.ndarray, second: np.ndarray) -> float:
    denominator = max(float(np.linalg.norm(first)), np.finfo(np.float64).tiny)
    return float(np.linalg.norm(second - first) / denominator)


def _source_digest(collection: AtomisticFrameCollection) -> str:
    hasher = hashlib.sha256()
    for value in (
        np.asarray(collection.frame_ids, dtype="<i8"),
        np.asarray(collection.pbc, dtype=np.uint8),
        np.asarray(collection.cells, dtype="<f8"),
        np.asarray(collection.origins, dtype="<f8"),
    ):
        hasher.update(str(value.shape).encode("ascii"))
        hasher.update(value.tobytes(order="C"))
    hasher.update(collection.frame_semantics.value.encode("ascii"))
    return hasher.hexdigest()


@dataclass(frozen=True, slots=True)
class LatticeGaugeOptions:
    determinant_tolerance: float = 1.0e-12
    condition_number_limit: float = 1.0e12
    continuity_relative_tolerance: float = 0.25
    integer_matrix_tolerance: float = 5.0e-2
    reconciliation_residual_tolerance: float = 5.0e-2
    reconcile_unimodular: bool = False
    require_right_handed: bool = False

    def __post_init__(self) -> None:
        for name in (
            "determinant_tolerance",
            "condition_number_limit",
            "continuity_relative_tolerance",
            "integer_matrix_tolerance",
            "reconciliation_residual_tolerance",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise LatticeGaugeError(f"{name} must be finite and positive.")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "reconcile_unimodular", bool(self.reconcile_unimodular))
        object.__setattr__(self, "require_right_handed", bool(self.require_right_handed))

    def to_dict(self) -> dict[str, Any]:
        return {
            "determinant_tolerance": self.determinant_tolerance,
            "condition_number_limit": self.condition_number_limit,
            "continuity_relative_tolerance": self.continuity_relative_tolerance,
            "integer_matrix_tolerance": self.integer_matrix_tolerance,
            "reconciliation_residual_tolerance": self.reconciliation_residual_tolerance,
            "reconcile_unimodular": self.reconcile_unimodular,
            "require_right_handed": self.require_right_handed,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LatticeGaugeOptions":
        return cls(
            determinant_tolerance=float(payload["determinant_tolerance"]),
            condition_number_limit=float(payload["condition_number_limit"]),
            continuity_relative_tolerance=float(
                payload["continuity_relative_tolerance"]
            ),
            integer_matrix_tolerance=float(payload["integer_matrix_tolerance"]),
            reconciliation_residual_tolerance=float(
                payload["reconciliation_residual_tolerance"]
            ),
            reconcile_unimodular=bool(payload["reconcile_unimodular"]),
            require_right_handed=bool(payload["require_right_handed"]),
        )


@dataclass(frozen=True, slots=True)
class LatticeGaugeFrame:
    frame_index: int
    comparison_frame_index: int
    status: LatticeGaugeFrameStatus
    reported_cell: tuple[tuple[float, float, float], ...]
    gauged_cell: tuple[tuple[float, float, float], ...]
    gauge_matrix: tuple[tuple[int, int, int], ...]
    determinant: float
    handedness: int
    condition_number: float
    direct_relative_change: float
    gauged_relative_change: float
    integer_candidate_residual: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "comparison_frame_index": self.comparison_frame_index,
            "status": self.status.value,
            "reported_cell": [list(row) for row in self.reported_cell],
            "gauged_cell": [list(row) for row in self.gauged_cell],
            "gauge_matrix": [list(row) for row in self.gauge_matrix],
            "determinant": self.determinant,
            "handedness": self.handedness,
            "condition_number": self.condition_number,
            "direct_relative_change": self.direct_relative_change,
            "gauged_relative_change": self.gauged_relative_change,
            "integer_candidate_residual": self.integer_candidate_residual,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LatticeGaugeFrame":
        return cls(
            frame_index=int(payload["frame_index"]),
            comparison_frame_index=int(payload["comparison_frame_index"]),
            status=LatticeGaugeFrameStatus(payload["status"]),
            reported_cell=_matrix_float_tuple(payload["reported_cell"]),
            gauged_cell=_matrix_float_tuple(payload["gauged_cell"]),
            gauge_matrix=_matrix_int_tuple(payload["gauge_matrix"]),
            determinant=float(payload["determinant"]),
            handedness=int(payload["handedness"]),
            condition_number=float(payload["condition_number"]),
            direct_relative_change=float(payload["direct_relative_change"]),
            gauged_relative_change=float(payload["gauged_relative_change"]),
            integer_candidate_residual=(
                None
                if payload.get("integer_candidate_residual") is None
                else float(payload["integer_candidate_residual"])
            ),
        )


@dataclass(frozen=True, slots=True)
class PeriodicLatticeGauge:
    source_digest: str
    frame_semantics: str
    periodic_axes: tuple[bool, bool, bool]
    handedness: int
    frames: tuple[LatticeGaugeFrame, ...]
    options: LatticeGaugeOptions
    signature: str = ""

    def __post_init__(self) -> None:
        if len(self.source_digest) != 64:
            raise LatticeGaugeError("source_digest must be SHA-256.")
        if len(self.periodic_axes) != 3:
            raise LatticeGaugeError("periodic_axes must have length three.")
        if self.handedness not in {-1, 1}:
            raise LatticeGaugeError("handedness must be -1 or 1.")
        if not self.frames:
            raise LatticeGaugeError("A lattice gauge requires at least one frame.")
        payload = self._payload(include_signature=False)
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise LatticeGaugeError("Lattice-gauge signature is inconsistent.")
        object.__setattr__(self, "signature", expected)

    @property
    def reconciled_frame_count(self) -> int:
        return sum(
            frame.status is LatticeGaugeFrameStatus.RECONCILED_UNIMODULAR_BASIS
            for frame in self.frames
        )

    def gauged_cell(self, frame_index: int) -> np.ndarray:
        if frame_index < 0 or frame_index >= len(self.frames):
            raise IndexError("frame_index is outside the lattice gauge.")
        return np.asarray(self.frames[frame_index].gauged_cell, dtype=np.float64)

    def gauge_matrix(self, frame_index: int) -> np.ndarray:
        if frame_index < 0 or frame_index >= len(self.frames):
            raise IndexError("frame_index is outside the lattice gauge.")
        return np.asarray(self.frames[frame_index].gauge_matrix, dtype=np.int64)

    def _payload(self, *, include_signature: bool) -> dict[str, Any]:
        payload = {
            "schema": PERIODIC_LATTICE_GAUGE_SCHEMA,
            "digest_algorithm": COORDINATE_CONTRACT_DIGEST_ALGORITHM,
            "source_digest": self.source_digest,
            "frame_semantics": self.frame_semantics,
            "periodic_axes": list(self.periodic_axes),
            "handedness": self.handedness,
            "frames": [frame.to_dict() for frame in self.frames],
            "options": self.options.to_dict(),
        }
        if include_signature:
            payload["signature"] = self.signature
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(include_signature=True)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PeriodicLatticeGauge":
        if payload.get("schema") != PERIODIC_LATTICE_GAUGE_SCHEMA:
            raise LatticeGaugeError("Unsupported periodic-lattice-gauge schema.")
        options_payload = payload.get("options")
        frame_payload = payload.get("frames")
        if not isinstance(options_payload, Mapping) or not isinstance(frame_payload, list):
            raise LatticeGaugeError("Incomplete periodic-lattice-gauge payload.")
        return cls(
            source_digest=str(payload["source_digest"]),
            frame_semantics=str(payload["frame_semantics"]),
            periodic_axes=tuple(bool(value) for value in payload["periodic_axes"]),
            handedness=int(payload["handedness"]),
            frames=tuple(LatticeGaugeFrame.from_dict(value) for value in frame_payload),
            options=LatticeGaugeOptions.from_dict(options_payload),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class SourceCoordinateContract:
    source_digest: str
    semantics: SourceFieldSemantics
    lattice_gauge: PeriodicLatticeGauge
    force_admissibility: ForceAdmissibilityContract
    reference_cell: ReferenceCellDefinition | None = None
    signature: str = ""

    def __post_init__(self) -> None:
        if self.source_digest != self.lattice_gauge.source_digest:
            raise LatticeGaugeError("Source and lattice-gauge digests disagree.")
        payload = self._payload(include_signature=False)
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise LatticeGaugeError("Source-coordinate-contract signature is inconsistent.")
        object.__setattr__(self, "signature", expected)

    def _payload(self, *, include_signature: bool) -> dict[str, Any]:
        payload = {
            "schema": SOURCE_COORDINATE_CONTRACT_SCHEMA,
            "digest_algorithm": COORDINATE_CONTRACT_DIGEST_ALGORITHM,
            "source_digest": self.source_digest,
            "semantics": self.semantics.to_dict(),
            "lattice_gauge": self.lattice_gauge.to_dict(),
            "force_admissibility": self.force_admissibility.to_dict(),
            "reference_cell": (
                None if self.reference_cell is None else self.reference_cell.to_dict()
            ),
        }
        if include_signature:
            payload["signature"] = self.signature
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(include_signature=True)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceCoordinateContract":
        if payload.get("schema") != SOURCE_COORDINATE_CONTRACT_SCHEMA:
            raise LatticeGaugeError("Unsupported source-coordinate-contract schema.")
        semantics_payload = payload.get("semantics")
        gauge_payload = payload.get("lattice_gauge")
        force_payload = payload.get("force_admissibility")
        if not all(isinstance(value, Mapping) for value in (
            semantics_payload, gauge_payload, force_payload
        )):
            raise LatticeGaugeError("Incomplete source-coordinate-contract payload.")
        reference_payload = payload.get("reference_cell")
        if reference_payload is not None and not isinstance(reference_payload, Mapping):
            raise LatticeGaugeError("Invalid reference-cell payload.")
        return cls(
            source_digest=str(payload["source_digest"]),
            semantics=SourceFieldSemantics.from_dict(semantics_payload),
            lattice_gauge=PeriodicLatticeGauge.from_dict(gauge_payload),
            force_admissibility=ForceAdmissibilityContract.from_dict(force_payload),
            reference_cell=(
                None
                if reference_payload is None
                else ReferenceCellDefinition.from_dict(reference_payload)
            ),
            signature=str(payload.get("signature", "")),
        )


def build_periodic_lattice_gauge(
    collection: AtomisticFrameCollection,
    *,
    options: LatticeGaugeOptions | None = None,
) -> PeriodicLatticeGauge:
    """Validate source-cell identity and optionally reconcile exact basis relabelings.

    Trajectories are compared sequentially.  Independent ensembles are compared
    against frame zero so no temporal ordering is invented.
    """
    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be an AtomisticFrameCollection.")
    active = options or LatticeGaugeOptions()
    cells = np.asarray(collection.cells, dtype=np.float64)
    determinants = np.linalg.det(cells)
    if np.any(np.abs(determinants) <= active.determinant_tolerance):
        frame = int(np.flatnonzero(np.abs(determinants) <= active.determinant_tolerance)[0])
        raise LatticeGaugeError(
            f"Cell at frame {frame} is singular within Stage-C0 tolerance."
        )
    handedness = np.sign(determinants).astype(np.int8)
    if active.require_right_handed and handedness[0] < 0:
        raise CellHandednessError("Stage-C0 policy requires right-handed cells.")
    conditions = np.linalg.cond(cells)
    if np.any(~np.isfinite(conditions) | (conditions > active.condition_number_limit)):
        invalid_condition = ~np.isfinite(conditions) | (
            conditions > active.condition_number_limit
        )
        frame = int(np.flatnonzero(invalid_condition)[0])
        raise LatticeGaugeError(
            f"Cell at frame {frame} exceeds the condition-number limit."
        )

    identity = np.eye(3, dtype=np.int64)
    gauged_cells: list[np.ndarray] = [cells[0].copy()]
    records: list[LatticeGaugeFrame] = [
        LatticeGaugeFrame(
            frame_index=0,
            comparison_frame_index=0,
            status=LatticeGaugeFrameStatus.REFERENCE,
            reported_cell=_matrix_float_tuple(cells[0]),
            gauged_cell=_matrix_float_tuple(cells[0]),
            gauge_matrix=_matrix_int_tuple(identity),
            determinant=float(determinants[0]),
            handedness=int(handedness[0]),
            condition_number=float(conditions[0]),
            direct_relative_change=0.0,
            gauged_relative_change=0.0,
            integer_candidate_residual=None,
        )
    ]

    for frame_index in range(1, collection.n_frames):
        comparison_index = frame_index - 1 if collection.is_trajectory else 0
        comparison = gauged_cells[comparison_index]
        current = cells[frame_index]
        direct = _relative_matrix_difference(comparison, current)
        if direct <= active.continuity_relative_tolerance:
            gauge = identity
            gauged = current.copy()
            status = LatticeGaugeFrameStatus.CONTINUOUS_REPORTED_BASIS
            integer_residual = None
            gauged_change = direct
        else:
            candidate_real = comparison @ np.linalg.inv(current)
            candidate = np.rint(candidate_real).astype(np.int64)
            candidate_scale = max(float(np.linalg.norm(candidate_real)), 1.0)
            integer_residual = float(
                np.linalg.norm(candidate_real - candidate) / candidate_scale
            )
            candidate_det = int(round(float(np.linalg.det(candidate))))
            candidate_gauged = candidate @ current
            gauged_change = _relative_matrix_difference(comparison, candidate_gauged)
            is_unimodular = abs(candidate_det) == 1
            is_integer = integer_residual <= active.integer_matrix_tolerance
            is_continuous = (
                gauged_change <= active.continuity_relative_tolerance
                and gauged_change <= active.reconciliation_residual_tolerance
            )
            if is_unimodular and is_integer and is_continuous:
                if not active.reconcile_unimodular:
                    raise UnsupportedBasisChangeError(
                        "Detected a nontrivial unimodular basis relabeling at "
                        f"frame {frame_index}; enable reconcile_unimodular to "
                        "apply it explicitly."
                    )
                gauge = candidate
                gauged = candidate_gauged
                status = LatticeGaugeFrameStatus.RECONCILED_UNIMODULAR_BASIS
            else:
                if handedness[frame_index] != handedness[0]:
                    raise CellHandednessError(
                        "Cell handedness changes at frame "
                        f"{frame_index} without a certifiable unimodular reconciliation."
                    )
                raise LatticeBasisContinuityError(
                    "Cell basis/deformation continuity is unresolved at frame "
                    f"{frame_index}: direct_relative_change={direct:.6g}, "
                    f"integer_candidate_residual={integer_residual:.6g}, "
                    f"gauged_relative_change={gauged_change:.6g}."
                )
        gauged_cells.append(gauged)
        records.append(
            LatticeGaugeFrame(
                frame_index=frame_index,
                comparison_frame_index=comparison_index,
                status=status,
                reported_cell=_matrix_float_tuple(current),
                gauged_cell=_matrix_float_tuple(gauged),
                gauge_matrix=_matrix_int_tuple(gauge),
                determinant=float(determinants[frame_index]),
                handedness=int(handedness[frame_index]),
                condition_number=float(conditions[frame_index]),
                direct_relative_change=direct,
                gauged_relative_change=gauged_change,
                integer_candidate_residual=integer_residual,
            )
        )

    return PeriodicLatticeGauge(
        source_digest=_source_digest(collection),
        frame_semantics=collection.frame_semantics.value,
        periodic_axes=tuple(bool(value) for value in collection.pbc),
        handedness=int(handedness[0]),
        frames=tuple(records),
        options=active,
    )


def reference_cell_from_source_frame(
    collection: AtomisticFrameCollection,
    lattice_gauge: PeriodicLatticeGauge,
    *,
    frame_index: int,
    tolerance: float = 1.0e-12,
) -> ReferenceCellDefinition:
    if lattice_gauge.source_digest != _source_digest(collection):
        raise LatticeGaugeError("The lattice gauge is not bound to this collection.")
    if frame_index < 0 or frame_index >= collection.n_frames:
        raise IndexError("frame_index is outside the source collection.")
    return ReferenceCellDefinition(
        source_kind="selected_source_frame",
        matrix=_matrix_float_tuple(lattice_gauge.gauged_cell(frame_index)),
        periodic_axes=tuple(bool(value) for value in collection.pbc),
        selected_frame_index=int(frame_index),
        handedness=0,
        determinant=0.0,
        condition_number=0.0,
        basis_gauge_signature=lattice_gauge.signature,
        tolerance=tolerance,
    )


def prepare_source_coordinate_contract(
    collection: AtomisticFrameCollection,
    *,
    semantics: SourceFieldSemantics | None = None,
    force_provenance: ForceSourceProvenance | None = None,
    lattice_options: LatticeGaugeOptions | None = None,
    reference_cell: ReferenceCellDefinition | None = None,
    reference_frame_index: int | None = None,
) -> SourceCoordinateContract:
    """Build the complete Stage-C0A1 contract without performing registration."""
    resolved_semantics = semantics or infer_source_field_semantics(collection)
    resolved_semantics.require_positions("Stage-C0 source audit")
    lattice_gauge = build_periodic_lattice_gauge(collection, options=lattice_options)
    if reference_cell is not None and reference_frame_index is not None:
        raise ValueError("Supply reference_cell or reference_frame_index, not both.")
    resolved_reference = reference_cell
    if reference_frame_index is not None:
        resolved_reference = reference_cell_from_source_frame(
            collection,
            lattice_gauge,
            frame_index=reference_frame_index,
        )
    if resolved_reference is not None:
        if resolved_reference.periodic_axes != tuple(bool(value) for value in collection.pbc):
            raise LatticeGaugeError(
                "Reference-cell periodic axes disagree with the source collection."
            )
        if resolved_reference.handedness != lattice_gauge.handedness:
            raise CellHandednessError(
                "Reference-cell and source-cell handedness disagree."
            )
    force_contract = resolve_force_admissibility(
        collection,
        resolved_semantics,
        provenance=force_provenance,
    )
    return SourceCoordinateContract(
        source_digest=lattice_gauge.source_digest,
        semantics=resolved_semantics,
        lattice_gauge=lattice_gauge,
        force_admissibility=force_contract,
        reference_cell=resolved_reference,
    )
