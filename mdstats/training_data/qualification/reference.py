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

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence
import json

import numpy as np

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    json_value,
    validate_digest,
)
from .errors import QualificationError, QualificationLineageError
from .geometry import atoms_for_frame, displaced_atoms, strained_atoms
from .plan import PhysicalValidationPlan
from .stress import (
    ExternalStressProvenance,
    canonical_stress_tensor,
    canonicalize_external_stress,
)

REFERENCE_REQUEST_SCHEMA = "mdstats.qualification-reference-request.v1"
REFERENCE_BUNDLE_SCHEMA = "mdstats.qualification-reference-bundle.v1"

REFERENCE_REQUEST_FILENAME = "reference-request.json"
REFERENCE_BUNDLE_FILENAME = "reference-bundle.json"
REFERENCE_BUNDLE_LOCATOR_SCHEMA = "mdstats.qualification-reference-bundle-locator.v1"

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
    # Candidate-independent requests may identify exact geometries for which a
    # stress observation is mandatory.  Model-specific applicability is still
    # re-established by the physical component; this field is the explicit
    # external-evidence contract when the frozen request already knows the
    # stress channel is required.
    stress_required_geometry_identities: tuple[str, ...] = ()

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
        stress_ids = tuple(
            validate_digest(str(value), name="stress_required_geometry_identity")
            for value in self.stress_required_geometry_identities
        )
        if len(set(stress_ids)) != len(stress_ids):
            raise TrainingDataInputError(
                "Reference request stress geometries must be unique."
            )
        unknown = set(stress_ids) - set(identities)
        if unknown:
            raise TrainingDataInputError(
                "Reference request stress geometries must be members of its geometry set."
            )
        object.__setattr__(self, "stress_required_geometry_identities", stress_ids)

    @property
    def required_stress_geometry_identities(self) -> tuple[str, ...]:
        """Alias used by callers that describe the same external contract."""

        return self.stress_required_geometry_identities

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": REFERENCE_REQUEST_SCHEMA,
            "protocol_identity": self.protocol_identity,
            "physical_plan_digest": self.physical_plan_digest,
            "geometries": [item.to_dict() for item in self.geometries],
            "stress_required_geometry_identities": list(
                self.stress_required_geometry_identities
            ),
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
            stress_required_geometry_identities=tuple(
                payload.get("stress_required_geometry_identities", ())
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
    stress_required: bool = False,
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
    # An explicit policy requirement is a candidate-independent external
    # contract.  Applicability derived from each published member is checked
    # again by the physical reducer, so a default-false policy cannot suppress
    # an actually trained/applicable channel.
    # ``PhysicalValidationPlan`` intentionally does not carry the mutable
    # specification object.  The caller passes the already frozen policy fact;
    # member-scoped applicability is still re-established by the reducer.
    stress_ids: tuple[str, ...] = () if not bool(stress_required) else tuple(
        item.geometry_identity
        for item in geometries
        if np.all(
            np.asarray(
                atoms_for_frame(context, item.frame_uid).get_pbc(), dtype=bool
            )
        )
    )
    return PhysicalReferenceRequest(
        protocol_identity=protocol_identity,
        physical_plan_digest=plan.content_digest,
        geometries=tuple(geometries),
        stress_required_geometry_identities=stress_ids,
    )


@dataclass(frozen=True, slots=True)
class ReferenceObservation:
    geometry_identity: str
    energy_ev: float
    forces_ev_per_angstrom: tuple[tuple[float, float, float], ...]
    relaxed_positions_angstrom: tuple[tuple[float, float, float], ...] | None = None
    stress_ev_per_angstrom3: tuple[tuple[float, float, float], ...] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    # ``stress_source_value`` is retained alongside the canonical tensor so
    # load-time authentication can replay the exact conversion rather than
    # trusting a declaration about units/sign/order after the fact.
    stress_source_value: Any | None = None
    stress_provenance: ExternalStressProvenance | Mapping[str, Any] | None = None

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
        if self.stress_ev_per_angstrom3 is not None:
            provenance = self.stress_provenance
            if provenance is None:
                provenance = ExternalStressProvenance.canonical_inline()
            elif not isinstance(provenance, ExternalStressProvenance):
                provenance = ExternalStressProvenance.from_dict(provenance)
            source = self.stress_source_value
            if provenance.source_declared:
                # Explicitly declared source values are imported through the
                # canonical owner.  The legacy field name is retained for
                # compatibility, but a GPa/bar/virial value is never first
                # interpreted as canonical and then converted a second time.
                if source is None:
                    raise QualificationLineageError(
                        "Declared external reference stress must carry the raw source "
                        "value; canonical stress cannot be converted a second time."
                    )
                try:
                    replayed = canonicalize_external_stress(source, provenance)
                except Exception as exc:  # noqa: BLE001 - boundary becomes lineage failure
                    raise QualificationLineageError(
                        "Reference stress source/provenance cannot be authenticated."
                    ) from exc
                stress = replayed
            else:
                stress = canonical_stress_tensor(self.stress_ev_per_angstrom3)
                if source is None:
                    source = stress
            if not np.all(np.isfinite(stress)):
                raise QualificationLineageError(
                    "Reference stress canonicalization produced a nonfinite tensor."
                )
            object.__setattr__(
                self,
                "stress_ev_per_angstrom3",
                tuple(tuple(float(value) for value in row) for row in stress.tolist()),
            )
            object.__setattr__(
                self,
                "stress_source_value",
                json_value(np.asarray(source, dtype=np.float64).tolist()),
            )
            object.__setattr__(self, "stress_provenance", provenance)
        elif self.stress_source_value is not None or self.stress_provenance is not None:
            raise QualificationLineageError(
                "Reference stress provenance cannot exist without a canonical stress value."
            )
        object.__setattr__(self, "metadata", json_value(dict(self.metadata)))

    @classmethod
    def from_external_stress(
        cls,
        *,
        geometry_identity: str,
        energy_ev: float,
        forces_ev_per_angstrom: tuple[tuple[float, float, float], ...],
        stress_value: Any,
        stress_provenance: ExternalStressProvenance | Mapping[str, Any],
        relaxed_positions_angstrom: tuple[tuple[float, float, float], ...] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "ReferenceObservation":
        """Build an observation by importing a raw, explicitly described stress."""

        provenance = (
            stress_provenance
            if isinstance(stress_provenance, ExternalStressProvenance)
            else ExternalStressProvenance.from_dict(stress_provenance)
        )
        # Pass the raw source through the constructor once.  The constructor
        # owns the single canonicalization call; precomputing here would make
        # the external value look as though it had been normalized twice.
        raw = np.asarray(stress_value, dtype=np.float64)
        raw_value = json_value(raw.tolist())
        return cls(
            geometry_identity=geometry_identity,
            energy_ev=energy_ev,
            forces_ev_per_angstrom=forces_ev_per_angstrom,
            relaxed_positions_angstrom=relaxed_positions_angstrom,
            stress_ev_per_angstrom3=raw_value,
            metadata={} if metadata is None else metadata,
            stress_source_value=raw_value,
            stress_provenance=provenance,
        )

    @property
    def forces(self) -> np.ndarray:
        return np.asarray(self.forces_ev_per_angstrom, dtype=np.float64)

    @property
    def relaxed_positions(self) -> np.ndarray | None:
        if self.relaxed_positions_angstrom is None:
            return None
        return np.asarray(self.relaxed_positions_angstrom, dtype=np.float64)

    @property
    def stress(self) -> np.ndarray | None:
        if self.stress_ev_per_angstrom3 is None:
            return None
        return np.asarray(self.stress_ev_per_angstrom3, dtype=np.float64)

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
        if self.stress_ev_per_angstrom3 is not None:
            payload["stress_ev_per_angstrom3"] = [
                list(row) for row in self.stress_ev_per_angstrom3
            ]
            payload["stress_source_value"] = json_value(self.stress_source_value)
            payload["stress_provenance"] = self.stress_provenance.to_dict()
        if self.metadata:
            payload["metadata"] = json_value(self.metadata)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReferenceObservation":
        if payload.get("stress_ev_per_angstrom3") is not None and payload.get(
            "stress_provenance"
        ) is None:
            raise QualificationLineageError(
                "Persisted reference stress is missing its source provenance."
            )
        result = cls(
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
            stress_ev_per_angstrom3=(
                None
                if payload.get("stress_ev_per_angstrom3") is None
                else tuple(
                    tuple(float(v) for v in row)
                    for row in payload["stress_ev_per_angstrom3"]
                )
            ),
            metadata=dict(payload.get("metadata", {})),
            stress_source_value=payload.get("stress_source_value"),
            stress_provenance=(
                None
                if payload.get("stress_provenance") is None
                else ExternalStressProvenance.from_dict(payload["stress_provenance"])
            ),
        )
        # Source/provenance is the canonicalization authority, but the
        # serialized canonical tensor is still part of the immutable evidence
        # representation. Replaying the source and silently discarding a
        # changed canonical field would let a tampered object retain its old
        # content identity.
        serialized_stress = payload.get("stress_ev_per_angstrom3")
        if serialized_stress is not None:
            try:
                stored = np.asarray(serialized_stress, dtype=np.float64)
                canonical = np.asarray(result.stress, dtype=np.float64)
            except (TypeError, ValueError) as exc:
                raise TrainingDataSerializationError(
                    "Persisted reference stress is not a numeric canonical tensor."
                ) from exc
            if stored.shape != canonical.shape or not np.array_equal(stored, canonical):
                raise TrainingDataSerializationError(
                    "Persisted canonical reference stress disagrees with its "
                    "authenticated source/provenance replay."
                )
        return result


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
        protocol = str(self.protocol_identity).strip()
        if not protocol:
            raise QualificationLineageError(
                "An authenticated reference bundle requires an explicit protocol identity."
            )
        object.__setattr__(self, "protocol_identity", protocol)
        observations = {str(key): value for key, value in dict(self.observations).items()}
        if set(observations) != {
            observation.geometry_identity for observation in observations.values()
        }:
            raise QualificationLineageError(
                "Reference bundle observation keys must match their geometry identities."
            )
        object.__setattr__(self, "observations", observations)

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

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": REFERENCE_BUNDLE_SCHEMA,
            "request_digest": self.request_digest,
            "protocol_identity": self.protocol_identity,
            "observations": [
                self.observations[key].to_dict() for key in sorted(self.observations)
            ],
        }
        return {**payload, "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AuthenticatedReferenceBundle":
        if payload.get("schema") != REFERENCE_BUNDLE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported reference-bundle schema.")
        observations = {
            str(item["geometry_identity"]): ReferenceObservation.from_dict(item)
            for item in payload.get("observations", ())
        }
        result = cls(
            request_digest=str(payload["request_digest"]),
            protocol_identity=str(payload["protocol_identity"]),
            observations=observations,
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Reference-bundle digest mismatch.")
        return result

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


def reference_bundle_object_path(root: Path, bundle_digest: str) -> Path:
    """Content-addressed immutable object path for one reference bundle."""

    value = validate_digest(bundle_digest, name="bundle_digest")
    return Path(root) / "reference-bundles" / value[:2] / f"{value}.json"


def publish_reference_request(root: Path, request: PhysicalReferenceRequest) -> Path:
    """Write the actionable request an operator (or a DFT pipeline) fulfils."""

    from ..target_size_execution import publish_immutable_json_create_or_verify

    if request.protocol_identity == "external-reference-protocol-unset":
        raise QualificationError(
            "The placeholder external-reference protocol cannot be published for "
            "production qualification."
        )
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
    schema = payload.get("schema")
    if schema not in (REFERENCE_BUNDLE_LOCATOR_SCHEMA, REFERENCE_BUNDLE_SCHEMA):
        raise QualificationLineageError("Unsupported external reference-bundle schema.")
    # Authenticate the mutable locator's lineage before opening its object.
    # This prevents an old valid object from becoming current under a changed
    # request or reference method.
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
    if schema == REFERENCE_BUNDLE_LOCATOR_SCHEMA:
        bundle_digest = validate_digest(payload.get("bundle_digest", ""), name="bundle_digest")
        relative = Path(str(payload.get("object_path", "")))
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise QualificationLineageError(
                "External reference bundle locator points outside its reference root."
            )
        object_path = Path(root) / relative
        expected_path = reference_bundle_object_path(root, bundle_digest)
        if object_path != expected_path:
            raise QualificationLineageError(
                "External reference bundle locator does not point to its content-addressed object."
            )
        if not object_path.is_file():
            raise QualificationLineageError(
                "External reference bundle locator refers to a missing immutable object."
            )
        try:
            object_payload = json.loads(object_path.read_text(encoding="utf-8"))
            bundle = AuthenticatedReferenceBundle.from_dict(object_payload)
        except (
            OSError,
            ValueError,
            KeyError,
            TrainingDataInputError,
            TrainingDataSerializationError,
            QualificationError,
        ) as exc:
            raise QualificationLineageError(
                "External reference bundle immutable object is corrupt or unauthenticated."
            ) from exc
        if bundle.content_digest != bundle_digest:
            raise QualificationLineageError(
                "External reference bundle object digest does not match its locator."
            )
        if bundle.request_digest != request.content_digest or bundle.protocol_identity != request.protocol_identity:
            raise QualificationLineageError(
                "External reference bundle immutable object does not bind the frozen request/protocol."
            )
        mirrored = payload.get("observations")
        if mirrored is not None and mirrored != object_payload.get("observations"):
            raise QualificationLineageError(
                "External reference bundle locator content differs from its immutable object; "
                "the frozen request geometry set cannot be authenticated."
            )
        if payload.get("content_digest") not in (None, bundle.content_digest):
            raise QualificationLineageError(
                "External reference bundle locator digest does not match its immutable object."
            )
    else:
        # An inline JSON record is mutable and therefore cannot be accepted as
        # revision-11 production evidence.  It must be republished through the
        # immutable object/locator owner below.
        raise QualificationLineageError(
            "External reference bundle is a legacy mutable inline record; republish it "
            "through the authenticated immutable reference-bundle owner."
        )
    observations = dict(bundle.observations)
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
    for identity in request.stress_required_geometry_identities:
        observed = observations[identity]
        if observed.stress is None:
            raise QualificationLineageError(
                "The authenticated reference bundle is missing stress for a geometry "
                "whose exact request requires it."
            )
        if (
            observed.stress_provenance is None
            or not observed.stress_provenance.source_declared
            or observed.stress_source_value is None
        ):
            raise QualificationLineageError(
                "Required reference stress is present without an authenticated source "
                "representation."
            )
    return bundle


def write_reference_bundle(
    root: Path,
    request: PhysicalReferenceRequest,
    observations: Sequence[ReferenceObservation],
) -> Path:
    """Supply externally computed reference evidence for a frozen request."""

    from ..target_size_execution import (
        publish_immutable_json_create_or_verify,
        publish_mutable_json_atomic,
    )

    if request.protocol_identity == "external-reference-protocol-unset":
        raise QualificationError(
            "The placeholder external-reference protocol cannot publish reference evidence."
        )
    supplied = tuple(observations)
    identities = [str(item.geometry_identity) for item in supplied]
    required = {item.geometry_identity for item in request.geometries}
    observed = set(identities)
    if len(identities) != len(observed) or observed != required:
        missing = sorted(required - observed)
        extra = sorted(observed - required)
        raise QualificationLineageError(
            "Reference observations must cover the exact frozen request geometry "
            f"set before publication ({len(missing)} missing, {len(extra)} unexpected)."
        )
    by_identity = {item.geometry_identity: item for item in supplied}
    for item in request.geometries:
        observation = by_identity[item.geometry_identity]
        if observation.forces.shape[0] != item.atom_count:
            raise QualificationLineageError(
                "Reference observations must preserve the frozen request atom count."
            )
        if item.mode == RELAXED_MODE and observation.relaxed_positions is None:
            raise QualificationLineageError(
                "The frozen relaxed reference geometry is missing; it cannot be "
                "published as a complete reference bundle."
            )
        if item.geometry_identity in request.stress_required_geometry_identities:
            if observation.stress is None:
                raise QualificationLineageError(
                    "The exact reference request requires stress for every listed "
                    "geometry; publication cannot omit it."
                )
            if (
                observation.stress_provenance is None
                or not observation.stress_provenance.source_declared
                or observation.stress_source_value is None
            ):
                raise QualificationLineageError(
                    "Required reference stress must carry explicit source units, sign, "
                    "order, and canonicalization provenance."
                )
        elif observation.stress is not None and (
            observation.stress_provenance is None
            or not observation.stress_provenance.source_declared
            or observation.stress_source_value is None
        ):
            raise QualificationLineageError(
                "Any supplied external reference stress must carry explicit source "
                "provenance; a canonical tensor alone is not publishable evidence."
            )
    bundle = AuthenticatedReferenceBundle(
        request_digest=request.content_digest,
        protocol_identity=request.protocol_identity,
        observations=by_identity,
    )
    object_path = reference_bundle_object_path(root, bundle.content_digest)
    publish_immutable_json_create_or_verify(
        object_path,
        bundle.to_dict(),
        deserializer=AuthenticatedReferenceBundle.from_dict,
    )
    locator = {
        "schema": REFERENCE_BUNDLE_LOCATOR_SCHEMA,
        "request_digest": bundle.request_digest,
        "protocol_identity": bundle.protocol_identity,
        "bundle_digest": bundle.content_digest,
        "content_digest": bundle.content_digest,
        "object_path": str(object_path.relative_to(Path(root))),
        # Operator-visible mirrors are authenticated against the immutable
        # object on every load; they are never the source of scientific truth.
        "observations": bundle.to_dict()["observations"],
    }
    path = reference_bundle_path(root)
    publish_mutable_json_atomic(path, locator)
    return path


__all__ = [
    "BASE_MODE",
    "REFERENCE_BUNDLE_FILENAME",
    "REFERENCE_BUNDLE_LOCATOR_SCHEMA",
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
    "reference_bundle_object_path",
    "reference_request_path",
    "write_reference_bundle",
]
