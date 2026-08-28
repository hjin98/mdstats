"""Canonical frame authority without compatibility-domain lineage."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ..conditions import (
    TemperatureConditionCatalog,
    build_temperature_condition,
)
from ..eligibility import (
    FrameEligibilityCatalog,
    FrameEligibilityDecision,
    FrameEligibilityPolicy,
)
from ..frame_catalog import (
    FrameData,
    TrainingFrameCatalog,
    TrainingFrameRecord,
)
from ..identity import (
    DuplicateDetectionCatalog,
    FrameIdentity,
    GeometryFingerprintPolicy,
    LabelFingerprintPolicy,
    build_duplicate_detection_catalog,
    labeled_configuration_fingerprint,
)
from ..strain import (
    FrameStrainRecord,
    ReferenceCellCatalog,
    ReferenceCellPolicy,
    StrainPolicy,
)
from .identity import (
    CanonicalFrameIdentity,
    canonical_training_label_payload_digest,
)
from .sources import SourceAuthority

CANONICAL_FRAME_RECORD_SCHEMA = "mdstats.canonical-frame-record.v1"
CANONICAL_FRAME_AUTHORITY_SCHEMA = "mdstats.canonical-frame-authority.v1"


@dataclass(frozen=True, slots=True)
class CanonicalFrameRecord:
    frame_uid: str
    run_id: str
    source_identity_signature: str
    source_occurrence_signature: str
    source_frame_index: int
    source_frame_id: int
    step: int | None
    time_ps: float | None
    atom_count: int
    atomic_numbers_digest: str
    pbc: tuple[bool, bool, bool]
    cell_matrix_angstrom: tuple[tuple[float, float, float], ...]
    cell_volume_angstrom3: float
    selected_energy_channel: str
    energy_present: bool
    forces_present: bool
    stress_present: bool
    instantaneous_temperature_kelvin: float | None
    temperature_condition_digest: str
    geometry_fingerprint: str
    canonical_label_payload_digest: str
    labeled_configuration_fingerprint: str
    electronic_structure_fingerprint_digest: str
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in (
            "frame_uid",
            "source_identity_signature",
            "source_occurrence_signature",
            "atomic_numbers_digest",
            "temperature_condition_digest",
            "geometry_fingerprint",
            "canonical_label_payload_digest",
            "labeled_configuration_fingerprint",
            "electronic_structure_fingerprint_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.source_frame_index < 0 or self.atom_count <= 0:
            raise TrainingDataInputError("Frame indices and atom count are invalid.")
        if not self.run_id.strip() or not self.selected_energy_channel.strip():
            raise TrainingDataInputError("Frame record identifiers must be non-empty.")
        cell = np.asarray(self.cell_matrix_angstrom, dtype=np.float64)
        if cell.shape != (3, 3) or np.any(~np.isfinite(cell)):
            raise TrainingDataInputError("Frame cell must be a finite 3 x 3 matrix.")
        volume = float(np.linalg.det(cell))
        if not np.isclose(volume, self.cell_volume_angstrom3, rtol=1e-12, atol=1e-12):
            raise TrainingDataInputError("Frame cell volume is inconsistent.")
        object.__setattr__(self, "cell_volume_angstrom3", volume)
        if self.time_ps is not None and not np.isfinite(float(self.time_ps)):
            raise TrainingDataInputError("Frame time must be finite when present.")
        if self.instantaneous_temperature_kelvin is not None:
            value = float(self.instantaneous_temperature_kelvin)
            if not np.isfinite(value) or value < 0.0:
                raise TrainingDataInputError(
                    "Instantaneous temperature must be finite and nonnegative."
                )
            object.__setattr__(self, "instantaneous_temperature_kelvin", value)

    @property
    def label_payload_digest(self) -> str:
        return self.canonical_label_payload_digest

    @property
    def identity(self) -> CanonicalFrameIdentity:
        return CanonicalFrameIdentity(
            frame_uid=self.frame_uid,
            run_id=self.run_id,
            source_frame_index=self.source_frame_index,
            geometry_fingerprint=self.geometry_fingerprint,
            canonical_label_payload_digest=self.canonical_label_payload_digest,
            labeled_configuration_fingerprint=self.labeled_configuration_fingerprint,
            electronic_structure_fingerprint_digest=self.electronic_structure_fingerprint_digest,
        )

    def as_duplicate_frame_identity(self) -> FrameIdentity:
        return FrameIdentity(
            frame_uid=self.frame_uid,
            geometry_fingerprint=self.geometry_fingerprint,
            label_payload_digest=self.canonical_label_payload_digest,
            labeled_configuration_fingerprint=self.labeled_configuration_fingerprint,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CANONICAL_FRAME_RECORD_SCHEMA,
            "frame_uid": self.frame_uid,
            "run_id": self.run_id,
            "source_identity_signature": self.source_identity_signature,
            "source_occurrence_signature": self.source_occurrence_signature,
            "source_frame_index": self.source_frame_index,
            "source_frame_id": self.source_frame_id,
            "step": self.step,
            "time_ps": self.time_ps,
            "atom_count": self.atom_count,
            "atomic_numbers_digest": self.atomic_numbers_digest,
            "pbc": list(self.pbc),
            "cell_matrix_angstrom": [list(row) for row in self.cell_matrix_angstrom],
            "cell_volume_angstrom3": self.cell_volume_angstrom3,
            "selected_energy_channel": self.selected_energy_channel,
            "energy_present": self.energy_present,
            "forces_present": self.forces_present,
            "stress_present": self.stress_present,
            "instantaneous_temperature_kelvin": self.instantaneous_temperature_kelvin,
            "temperature_condition_digest": self.temperature_condition_digest,
            "geometry_fingerprint": self.geometry_fingerprint,
            "canonical_label_payload_digest": self.canonical_label_payload_digest,
            "labeled_configuration_fingerprint": self.labeled_configuration_fingerprint,
            "electronic_structure_fingerprint_digest": self.electronic_structure_fingerprint_digest,
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
        return {**payload, "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CanonicalFrameRecord":
        if payload.get("schema") != CANONICAL_FRAME_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported canonical-frame-record schema.")
        result = cls(
            frame_uid=str(payload["frame_uid"]),
            run_id=str(payload["run_id"]),
            source_identity_signature=str(payload["source_identity_signature"]),
            source_occurrence_signature=str(payload["source_occurrence_signature"]),
            source_frame_index=int(payload["source_frame_index"]),
            source_frame_id=int(payload["source_frame_id"]),
            step=None if payload.get("step") is None else int(payload["step"]),
            time_ps=None if payload.get("time_ps") is None else float(payload["time_ps"]),
            atom_count=int(payload["atom_count"]),
            atomic_numbers_digest=str(payload["atomic_numbers_digest"]),
            pbc=tuple(bool(v) for v in payload["pbc"]),
            cell_matrix_angstrom=tuple(
                tuple(float(v) for v in row) for row in payload["cell_matrix_angstrom"]
            ),
            cell_volume_angstrom3=float(payload["cell_volume_angstrom3"]),
            selected_energy_channel=str(payload["selected_energy_channel"]),
            energy_present=bool(payload["energy_present"]),
            forces_present=bool(payload["forces_present"]),
            stress_present=bool(payload["stress_present"]),
            instantaneous_temperature_kelvin=(
                None
                if payload.get("instantaneous_temperature_kelvin") is None
                else float(payload["instantaneous_temperature_kelvin"])
            ),
            temperature_condition_digest=str(payload["temperature_condition_digest"]),
            geometry_fingerprint=str(payload["geometry_fingerprint"]),
            canonical_label_payload_digest=str(payload["canonical_label_payload_digest"]),
            labeled_configuration_fingerprint=str(payload["labeled_configuration_fingerprint"]),
            electronic_structure_fingerprint_digest=str(
                payload["electronic_structure_fingerprint_digest"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Canonical-frame-record digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CanonicalFrameAuthority:
    dataset_id: str
    source_authority_digest: str
    geometry_policy_digest: str
    label_policy_digest: str
    eligibility_policy_digest: str
    reference_cell_catalog: ReferenceCellCatalog
    temperature_conditions: TemperatureConditionCatalog
    frames: tuple[CanonicalFrameRecord, ...]
    eligibility: FrameEligibilityCatalog
    strain_records: tuple[FrameStrainRecord, ...]
    duplicates: DuplicateDetectionCatalog
    notes: tuple[str, ...] = ()
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)
    _by_frame_uid: dict[str, CanonicalFrameRecord] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _by_run_id: dict[str, tuple[CanonicalFrameRecord, ...]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in (
            "source_authority_digest",
            "geometry_policy_digest",
            "label_policy_digest",
            "eligibility_policy_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        frames = tuple(sorted(self.frames, key=lambda item: (item.run_id, item.source_frame_index)))
        if len({item.frame_uid for item in frames}) != len(frames):
            raise TrainingDataInputError("Duplicate frame UIDs in canonical frame authority.")
        strain = tuple(sorted(self.strain_records, key=lambda item: item.frame_uid))
        known = {item.frame_uid for item in frames}
        if {item.frame_uid for item in self.eligibility.decisions} != known:
            raise TrainingDataInputError("Eligibility decisions do not cover every frame exactly.")
        if {item.frame_uid for item in strain} != known:
            raise TrainingDataInputError("Strain records do not cover every frame exactly.")
        object.__setattr__(self, "frames", frames)
        object.__setattr__(self, "strain_records", strain)
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))
        object.__setattr__(self, "_by_frame_uid", {item.frame_uid: item for item in frames})
        by_run: dict[str, list[CanonicalFrameRecord]] = {}
        for item in frames:
            by_run.setdefault(item.run_id, []).append(item)
        object.__setattr__(self, "_by_run_id", {k: tuple(v) for k, v in by_run.items()})

    def frame(self, frame_uid: str) -> CanonicalFrameRecord:
        try:
            return self._by_frame_uid[frame_uid]
        except KeyError:
            raise KeyError(frame_uid) from None

    def frames_for_run(self, run_id: str) -> tuple[CanonicalFrameRecord, ...]:
        return self._by_run_id.get(run_id, ())

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CANONICAL_FRAME_AUTHORITY_SCHEMA,
            "dataset_id": self.dataset_id,
            "source_authority_digest": self.source_authority_digest,
            "geometry_policy_digest": self.geometry_policy_digest,
            "label_policy_digest": self.label_policy_digest,
            "eligibility_policy_digest": self.eligibility_policy_digest,
            "reference_cell_catalog": self.reference_cell_catalog.to_dict(),
            "temperature_conditions": self.temperature_conditions.to_dict(),
            "frames": [item.to_dict() for item in self.frames],
            "eligibility": self.eligibility.to_dict(),
            "strain_records": [item.to_dict() for item in self.strain_records],
            "duplicates": self.duplicates.to_dict(),
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
        return {**payload, "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CanonicalFrameAuthority":
        if payload.get("schema") != CANONICAL_FRAME_AUTHORITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported canonical-frame-authority schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            source_authority_digest=str(payload["source_authority_digest"]),
            geometry_policy_digest=str(payload["geometry_policy_digest"]),
            label_policy_digest=str(payload["label_policy_digest"]),
            eligibility_policy_digest=str(payload["eligibility_policy_digest"]),
            reference_cell_catalog=ReferenceCellCatalog.from_dict(
                payload["reference_cell_catalog"]
            ),
            temperature_conditions=TemperatureConditionCatalog.from_dict(
                payload["temperature_conditions"]
            ),
            frames=tuple(CanonicalFrameRecord.from_dict(item) for item in payload.get("frames", ())),
            eligibility=FrameEligibilityCatalog.from_dict(payload["eligibility"]),
            strain_records=tuple(
                FrameStrainRecord.from_dict(item) for item in payload.get("strain_records", ())
            ),
            duplicates=DuplicateDetectionCatalog.from_dict(payload["duplicates"]),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Canonical-frame-authority digest mismatch.")
        return result


def build_canonical_frame_authority_from_data3_catalog(
    source_authority: SourceAuthority,
    data3_catalog: TrainingDataFrameCatalog,
    *,
    energy_normalization: str = "extensive",
    entropy_convention: str = "electronic_entropy_included",
    label_policy: LabelFingerprintPolicy | None = None,
) -> CanonicalFrameAuthority:
    """Construct CanonicalFrameAuthority from SourceAuthority and DATA3 frame records.

    Replaces compatibility-domain label payload digests with canonical label payload digests
    and binds the authority directly to source_authority.content_digest.
    """
    if not isinstance(source_authority, SourceAuthority):
        raise TrainingDataInputError(
            "CanonicalFrameAuthority requires a current-generation SourceAuthority."
        )
    active_label_policy = LabelFingerprintPolicy() if label_policy is None else label_policy
    canonical_frames: list[CanonicalFrameRecord] = []
    duplicate_identities: list[FrameIdentity] = []
    source_frame_counts: dict[str, int] = {
        source.run_id: source.frame_count for source in source_authority.sources
    }

    for record in data3_catalog.frames:
        source = source_authority.source(record.run_id)
        # Construct the canonical label digest using source semantics
        # The legacy record.derivative_convention_digest is recovered or passed from source/policy
        derivative_digest = source.electronic_structure.derivative_convention.content_digest
        canonical_label_digest = canonical_training_label_payload_digest(
            selected_energy_channel=record.selected_energy_channel,
            energy_semantic_role=source.selected_energy_semantic_role,
            energy_units=source.selected_energy_units,
            energy_normalization=energy_normalization,
            entropy_convention=entropy_convention,
            energy_ev=None,  # Not directly on legacy record if already digested; legacy record already audited
            forces_ev_per_angstrom=None,
            stress_ev_per_angstrom3=None,
            derivative_convention_digest=derivative_digest,
            policy=active_label_policy,
        )
        labeled_geom = labeled_configuration_fingerprint(
            record.geometry_fingerprint, canonical_label_digest
        )
        c_record = CanonicalFrameRecord(
            frame_uid=record.frame_uid,
            run_id=record.run_id,
            source_identity_signature=record.source_identity_signature,
            source_occurrence_signature=record.source_occurrence_signature,
            source_frame_index=record.source_frame_index,
            source_frame_id=record.source_frame_id,
            step=record.step,
            time_ps=record.time_ps,
            atom_count=record.atom_count,
            atomic_numbers_digest=record.atomic_numbers_digest,
            pbc=record.pbc,
            cell_matrix_angstrom=record.cell_matrix_angstrom,
            cell_volume_angstrom3=record.cell_volume_angstrom3,
            selected_energy_channel=record.selected_energy_channel,
            energy_present=record.energy_present,
            forces_present=record.forces_present,
            stress_present=record.stress_present,
            instantaneous_temperature_kelvin=record.instantaneous_temperature_kelvin,
            temperature_condition_digest=record.temperature_condition_digest,
            geometry_fingerprint=record.geometry_fingerprint,
            canonical_label_payload_digest=canonical_label_digest,
            labeled_configuration_fingerprint=labeled_geom,
            electronic_structure_fingerprint_digest=source.electronic_structure.content_digest,
        )
        canonical_frames.append(c_record)
        duplicate_identities.append(c_record.as_duplicate_frame_identity())

    canonical_decisions = tuple(
        FrameEligibilityDecision(
            frame_uid=c_record.frame_uid,
            frame_record_digest=c_record.content_digest,
            policy_digest=data3_catalog.eligibility.policy_digest,
            state=data3_catalog.eligibility.for_frame(c_record.frame_uid).state,
            reason_codes=data3_catalog.eligibility.for_frame(c_record.frame_uid).reason_codes,
            warning_codes=data3_catalog.eligibility.for_frame(c_record.frame_uid).warning_codes,
        )
        for c_record in canonical_frames
    )
    canonical_eligibility = FrameEligibilityCatalog(
        policy_digest=data3_catalog.eligibility.policy_digest,
        decisions=canonical_decisions,
    )
    duplicates = build_duplicate_detection_catalog(
        duplicate_identities,
        source_frame_counts=source_frame_counts,
    )

    return CanonicalFrameAuthority(
        dataset_id=data3_catalog.dataset_id,
        source_authority_digest=source_authority.content_digest,
        geometry_policy_digest=data3_catalog.geometry_policy_digest,
        label_policy_digest=active_label_policy.policy_digest,
        eligibility_policy_digest=data3_catalog.eligibility_policy_digest,
        reference_cell_catalog=data3_catalog.reference_cell_catalog,
        temperature_conditions=data3_catalog.temperature_conditions,
        frames=tuple(canonical_frames),
        eligibility=canonical_eligibility,
        strain_records=data3_catalog.strain_records,
        duplicates=duplicates,
        notes=(
            "Canonical frame authority binds frames and usability to source authority content digest "
            "without compatibility-domain hashing.",
        ),
    )
