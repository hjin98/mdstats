"""The external reference boundary: request identity, import, authentication.

P7 owns *which* configurations need independent reference evidence, under which
protocol, and how a supplied bundle is matched back to them.  It does not run
DFT, and it never manufactures a reference it does not have: an unsatisfied
request produces ``waiting_for_reference`` with an actionable request bundle on
disk, which is a truthful incomplete state rather than a verdict.

Bounded deterministic analytic references are legitimate *below* this boundary
for functional testing; a production scientific qualification supplies real
external references generated under the exact frozen request/protocol identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
import json

import numpy as np

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .errors import QualificationError, QualificationLineageError
from .geometry import atoms_for_frame, displaced_atoms, strained_atoms
from .plan import PhysicalValidationPlan

REFERENCE_REQUEST_SCHEMA = "mdstats.qualification-reference-request.v1"
REFERENCE_BUNDLE_SCHEMA = "mdstats.qualification-reference-bundle.v1"

REFERENCE_REQUEST_FILENAME = "reference-request.json"
REFERENCE_BUNDLE_FILENAME = "reference-bundle.json"

#: Rounding used only for *identity*, never for physics: it makes a geometry
#: identity stable across text round-trips an external code performs.
_IDENTITY_DECIMALS = 8


def geometry_identity(atoms: Any, *, frame_uid: str, mode: str) -> str:
    """Exact identity of one requested geometry."""

    return digest(
        {
            "frame_uid": str(frame_uid),
            "mode": str(mode),
            "numbers": [int(v) for v in atoms.get_atomic_numbers()],
            "cell": np.round(np.asarray(atoms.get_cell(), dtype=np.float64), _IDENTITY_DECIMALS).tolist(),
            "pbc": [bool(v) for v in atoms.get_pbc()],
            "positions": np.round(
                np.asarray(atoms.get_positions(), dtype=np.float64), _IDENTITY_DECIMALS
            ).tolist(),
        }
    )


def mode_name(atom_index: int, axis: str, amplitude: float) -> str:
    return f"disp:a{int(atom_index)}:{axis}:{float(amplitude):+.6f}"


BASE_MODE = "base"
RELAXED_MODE = "relaxed"


def strain_mode_name(magnitude: float) -> str:
    return f"strain:iso:{float(magnitude):+.6f}"


@dataclass(frozen=True, slots=True)
class ReferenceGeometryRequest:
    frame_uid: str
    mode: str
    geometry_identity: str
    atom_count: int

    def __post_init__(self) -> None:
        for name in ("frame_uid", "mode"):
            value = str(getattr(self, name)).strip()
            if not value:
                raise TrainingDataInputError(f"Reference request requires {name}.")
            object.__setattr__(self, name, value)
        object.__setattr__(
            self,
            "geometry_identity",
            validate_digest(self.geometry_identity, name="geometry_identity"),
        )
        count = int(self.atom_count)
        if count <= 0:
            raise TrainingDataInputError("Reference request requires a positive atom count.")
        object.__setattr__(self, "atom_count", count)

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_uid": self.frame_uid,
            "mode": self.mode,
            "geometry_identity": self.geometry_identity,
            "atom_count": self.atom_count,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReferenceGeometryRequest":
        return cls(
            frame_uid=str(payload["frame_uid"]),
            mode=str(payload["mode"]),
            geometry_identity=str(payload["geometry_identity"]),
            atom_count=int(payload["atom_count"]),
        )


@dataclass(frozen=True, slots=True)
class PhysicalReferenceRequest:
    """The exact independent evidence this qualification needs and lacks."""

    protocol_identity: str
    physical_plan_digest: str
    geometries: tuple[ReferenceGeometryRequest, ...]

    def __post_init__(self) -> None:
        protocol = str(self.protocol_identity).strip()
        if not protocol:
            raise TrainingDataInputError(
                "A physical reference request requires an explicit reference protocol "
                "identity; unlabelled external evidence cannot be authenticated."
            )
        object.__setattr__(self, "protocol_identity", protocol)
        object.__setattr__(
            self,
            "physical_plan_digest",
            validate_digest(self.physical_plan_digest, name="physical_plan_digest"),
        )
        geometries = tuple(self.geometries)
        if not geometries:
            raise TrainingDataInputError("A reference request requires at least one geometry.")
        identities = [item.geometry_identity for item in geometries]
        if len(set(identities)) != len(identities):
            raise TrainingDataInputError("Reference request geometries must be unique.")
        object.__setattr__(self, "geometries", geometries)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": REFERENCE_REQUEST_SCHEMA,
            "protocol_identity": self.protocol_identity,
            "physical_plan_digest": self.physical_plan_digest,
            "geometries": [item.to_dict() for item in self.geometries],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PhysicalReferenceRequest":
        if payload.get("schema") != REFERENCE_REQUEST_SCHEMA:
            raise TrainingDataSerializationError("Unsupported reference-request schema.")
        result = cls(
            protocol_identity=str(payload["protocol_identity"]),
            physical_plan_digest=str(payload["physical_plan_digest"]),
            geometries=tuple(
                ReferenceGeometryRequest.from_dict(item) for item in payload["geometries"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Reference-request digest mismatch.")
        return result


def build_physical_reference_request(
    context: Any,
    plan: PhysicalValidationPlan,
    *,
    protocol_identity: str,
    include_relaxed: bool,
) -> PhysicalReferenceRequest:
    """Enumerate every geometry the frozen physical plan needs a reference for."""

    geometries: list[ReferenceGeometryRequest] = []
    for base in plan.bases:
        atoms = atoms_for_frame(context, base.frame_uid)
        geometries.append(
            ReferenceGeometryRequest(
                frame_uid=base.frame_uid,
                mode=BASE_MODE,
                geometry_identity=geometry_identity(atoms, frame_uid=base.frame_uid, mode=BASE_MODE),
                atom_count=len(atoms),
            )
        )
        if include_relaxed:
            geometries.append(
                ReferenceGeometryRequest(
                    frame_uid=base.frame_uid,
                    mode=RELAXED_MODE,
                    geometry_identity=geometry_identity(
                        atoms, frame_uid=base.frame_uid, mode=RELAXED_MODE
                    ),
                    atom_count=len(atoms),
                )
            )
        for atom_index, axis, amplitude in base.modes():
            moved = displaced_atoms(atoms, atom_index=atom_index, axis=axis, amplitude=amplitude)
            name = mode_name(atom_index, axis, amplitude)
            geometries.append(
                ReferenceGeometryRequest(
                    frame_uid=base.frame_uid,
                    mode=name,
                    geometry_identity=geometry_identity(moved, frame_uid=base.frame_uid, mode=name),
                    atom_count=len(moved),
                )
            )
        for magnitude in plan.strain_magnitudes:
            strained = strained_atoms(atoms, magnitude)
            name = strain_mode_name(magnitude)
            geometries.append(
                ReferenceGeometryRequest(
                    frame_uid=base.frame_uid,
                    mode=name,
                    geometry_identity=geometry_identity(
                        strained, frame_uid=base.frame_uid, mode=name
                    ),
                    atom_count=len(strained),
                )
            )
    return PhysicalReferenceRequest(
        protocol_identity=protocol_identity,
        physical_plan_digest=plan.content_digest,
        geometries=tuple(geometries),
    )


@dataclass(frozen=True, slots=True)
class ReferenceObservation:
    geometry_identity: str
    energy_ev: float
    forces_ev_per_angstrom: tuple[tuple[float, float, float], ...]
    relaxed_positions_angstrom: tuple[tuple[float, float, float], ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "geometry_identity",
            validate_digest(self.geometry_identity, name="geometry_identity"),
        )
        energy = float(self.energy_ev)
        if not np.isfinite(energy):
            raise QualificationLineageError("A reference energy must be finite.")
        object.__setattr__(self, "energy_ev", energy)
        forces = np.asarray(self.forces_ev_per_angstrom, dtype=np.float64)
        if forces.ndim != 2 or forces.shape[1] != 3 or not np.all(np.isfinite(forces)):
            raise QualificationLineageError("Reference forces must be a finite (n, 3) array.")
        object.__setattr__(self, "forces_ev_per_angstrom", tuple(tuple(row) for row in forces.tolist()))
        if self.relaxed_positions_angstrom is not None:
            relaxed = np.asarray(self.relaxed_positions_angstrom, dtype=np.float64)
            if relaxed.shape != forces.shape or not np.all(np.isfinite(relaxed)):
                raise QualificationLineageError(
                    "Reference relaxed positions must match the configuration shape."
                )
            object.__setattr__(
                self, "relaxed_positions_angstrom", tuple(tuple(row) for row in relaxed.tolist())
            )

    @property
    def forces(self) -> np.ndarray:
        return np.asarray(self.forces_ev_per_angstrom, dtype=np.float64)

    @property
    def relaxed_positions(self) -> np.ndarray | None:
        if self.relaxed_positions_angstrom is None:
            return None
        return np.asarray(self.relaxed_positions_angstrom, dtype=np.float64)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "geometry_identity": self.geometry_identity,
            "energy_ev": self.energy_ev,
            "forces_ev_per_angstrom": [list(row) for row in self.forces_ev_per_angstrom],
        }
        if self.relaxed_positions_angstrom is not None:
            payload["relaxed_positions_angstrom"] = [
                list(row) for row in self.relaxed_positions_angstrom
            ]
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReferenceObservation":
        return cls(
            geometry_identity=str(payload["geometry_identity"]),
            energy_ev=float(payload["energy_ev"]),
            forces_ev_per_angstrom=tuple(
                tuple(float(v) for v in row) for row in payload["forces_ev_per_angstrom"]
            ),
            relaxed_positions_angstrom=(
                None
                if payload.get("relaxed_positions_angstrom") is None
                else tuple(
                    tuple(float(v) for v in row) for row in payload["relaxed_positions_angstrom"]
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class AuthenticatedReferenceBundle:
    """Supplied external evidence, matched one-to-one with a frozen request."""

    request_digest: str
    protocol_identity: str
    observations: Mapping[str, ReferenceObservation]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "request_digest", validate_digest(self.request_digest, name="request_digest")
        )
        object.__setattr__(self, "protocol_identity", str(self.protocol_identity))

    @property
    def content_digest(self) -> str:
        return digest(
            {
                "schema": REFERENCE_BUNDLE_SCHEMA,
                "request_digest": self.request_digest,
                "protocol_identity": self.protocol_identity,
                "observations": [
                    self.observations[key].to_dict() for key in sorted(self.observations)
                ],
            }
        )

    def observation(self, geometry: str) -> ReferenceObservation:
        try:
            return self.observations[str(geometry)]
        except KeyError:
            raise QualificationLineageError(
                f"Reference bundle is missing geometry {str(geometry)[:12]}..."
            ) from None


def reference_request_path(root: Path) -> Path:
    return Path(root) / REFERENCE_REQUEST_FILENAME


def reference_bundle_path(root: Path) -> Path:
    return Path(root) / REFERENCE_BUNDLE_FILENAME


def publish_reference_request(root: Path, request: PhysicalReferenceRequest) -> Path:
    """Write the actionable request an operator (or a DFT pipeline) fulfils."""

    from ..target_size_execution import publish_immutable_json_create_or_verify

    path = reference_request_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    publish_immutable_json_create_or_verify(
        path, request.to_dict(), deserializer=PhysicalReferenceRequest.from_dict
    )
    return path


def load_reference_bundle(
    root: Path, request: PhysicalReferenceRequest
) -> AuthenticatedReferenceBundle | None:
    """Authenticate a supplied bundle against the exact frozen request.

    A partial, mismatched, or wrong-protocol bundle is a hard lineage failure
    rather than a partial pass: qualification either has the independent
    evidence its plan asked for or it does not.
    """

    path = reference_bundle_path(root)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise QualificationLineageError(
            f"External reference bundle at {path!s} is not readable JSON."
        ) from exc
    if payload.get("schema") != REFERENCE_BUNDLE_SCHEMA:
        raise QualificationLineageError("Unsupported external reference-bundle schema.")
    if str(payload.get("protocol_identity")) != request.protocol_identity:
        raise QualificationLineageError(
            "External reference bundle was produced under a different reference "
            "protocol than the frozen request; it cannot be matched."
        )
    if str(payload.get("request_digest")) != request.content_digest:
        raise QualificationLineageError(
            "External reference bundle does not bind the exact frozen physical "
            "reference request."
        )
    observations = {
        str(item["geometry_identity"]): ReferenceObservation.from_dict(item)
        for item in payload.get("observations", ())
    }
    required = {item.geometry_identity for item in request.geometries}
    missing = sorted(required - set(observations))
    extra = sorted(set(observations) - required)
    if missing or extra:
        raise QualificationLineageError(
            "External reference bundle does not match the frozen request geometry "
            f"set ({len(missing)} missing, {len(extra)} unexpected)."
        )
    for item in request.geometries:
        observed = observations[item.geometry_identity]
        if observed.forces.shape[0] != item.atom_count:
            raise QualificationLineageError(
                "External reference geometry has a different atom count than requested."
            )
    return AuthenticatedReferenceBundle(
        request_digest=request.content_digest,
        protocol_identity=request.protocol_identity,
        observations=observations,
    )


def write_reference_bundle(
    root: Path,
    request: PhysicalReferenceRequest,
    observations: Sequence[ReferenceObservation],
) -> Path:
    """Supply externally computed reference evidence for a frozen request."""

    path = reference_bundle_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": REFERENCE_BUNDLE_SCHEMA,
        "request_digest": request.content_digest,
        "protocol_identity": request.protocol_identity,
        "observations": [item.to_dict() for item in observations],
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


__all__ = [
    "BASE_MODE",
    "REFERENCE_BUNDLE_FILENAME",
    "REFERENCE_BUNDLE_SCHEMA",
    "REFERENCE_REQUEST_FILENAME",
    "REFERENCE_REQUEST_SCHEMA",
    "RELAXED_MODE",
    "AuthenticatedReferenceBundle",
    "PhysicalReferenceRequest",
    "ReferenceGeometryRequest",
    "ReferenceObservation",
    "build_physical_reference_request",
    "geometry_identity",
    "load_reference_bundle",
    "mode_name",
    "strain_mode_name",
    "publish_reference_request",
    "reference_bundle_path",
    "reference_request_path",
    "write_reference_bundle",
]
