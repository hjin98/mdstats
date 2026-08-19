"""Immutable frame catalogs and DATA3 builders."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from mdstats.collection import AtomisticFrameCollection
from .resources import isolated_process_map
from .progress_timing import format_progress_fraction
from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .conditions import (
    TemperatureConditionCatalog,
    TemperatureTargetEvidence,
    build_temperature_condition,
)
from .eligibility import (
    FrameEligibilityCatalog,
    FrameEligibilityDecision,
    FrameEligibilityPolicy,
    assess_frame_eligibility,
)
from .identity import (
    DuplicateDetectionCatalog,
    FrameIdentity,
    GeometryFingerprintPolicy,
    LabelFingerprintPolicy,
    build_duplicate_detection_catalog,
    frame_uid,
    geometry_fingerprint,
    label_payload_digest,
    labeled_configuration_fingerprint,
    source_occurrence_signature,
)
from .strain import (
    FrameStrainRecord,
    ReferenceCellCatalog,
    ReferenceCellPolicy,
    StrainPolicy,
    build_reference_cell_catalog,
    compute_frame_strain,
)

FRAME_DATA_SCHEMA = "mdstats.training-frame-data.v1"
TRAINING_FRAME_RECORD_SCHEMA = "mdstats.training-frame-record.v1"
TRAINING_FRAME_CATALOG_SCHEMA = "mdstats.training-frame-catalog.v1"
MLFF_DATA3_PARSER_VERSION = "0.20.31a0"

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
Int32Array = NDArray[np.int32]
BoolArray = NDArray[np.bool_]


def _immutable_array(value: ArrayLike, *, dtype: np.dtype[Any]) -> np.ndarray:
    """Return an immutable C-order array, preserving read-only memory maps."""

    result = np.asarray(value, dtype=dtype, order="C")
    if result.flags.writeable or not result.flags.c_contiguous:
        result = np.array(result, dtype=dtype, copy=True, order="C")
        result.setflags(write=False)
    return result


def _optional_array(
    value: ArrayLike | None, *, dtype: np.dtype[Any], name: str
) -> np.ndarray | None:
    if value is None:
        return None
    return _immutable_array(value, dtype=dtype)


@dataclass(frozen=True, slots=True)
class FrameData:
    """Normalized source-independent frame arrays used by the DATA3 builder."""

    source_frame_indices: IntArray
    frame_ids: IntArray
    steps: IntArray | None
    times_ps: FloatArray | None
    atomic_numbers: Int32Array
    pbc: BoolArray
    cells_angstrom: FloatArray
    fractional_positions: FloatArray
    energies_ev: FloatArray | None
    forces_ev_per_angstrom: FloatArray | None
    stresses_ev_per_angstrom3: FloatArray | None
    temperatures_kelvin: FloatArray | None
    scf_iteration_limit_reached: tuple[bool | None, ...]

    def __post_init__(self) -> None:
        source_indices = np.asarray(self.source_frame_indices, dtype=np.int64)
        frame_ids = np.asarray(self.frame_ids, dtype=np.int64)
        numbers = np.asarray(self.atomic_numbers, dtype=np.int32)
        pbc = np.asarray(self.pbc, dtype=np.bool_)
        cells = np.asarray(self.cells_angstrom, dtype=np.float64)
        positions = np.asarray(self.fractional_positions, dtype=np.float64)
        if source_indices.ndim != 1 or frame_ids.shape != source_indices.shape:
            raise TrainingDataInputError(
                "source_frame_indices and frame_ids must be aligned one-dimensional arrays."
            )
        n_frames = source_indices.size
        if n_frames == 0 or len(set(int(v) for v in source_indices)) != n_frames:
            raise TrainingDataInputError(
                "FrameData requires non-empty unique source_frame_indices."
            )
        if np.any(source_indices < 0):
            raise TrainingDataInputError("source_frame_indices must be nonnegative.")
        if numbers.ndim != 1 or numbers.size == 0 or np.any(numbers <= 0):
            raise TrainingDataInputError("atomic_numbers must be a positive vector.")
        if pbc.shape != (3,):
            raise TrainingDataInputError("pbc must have shape (3,).")
        if cells.shape != (n_frames, 3, 3) or np.any(~np.isfinite(cells)):
            raise TrainingDataInputError("cells_angstrom must have shape (n_frames, 3, 3).")
        if positions.shape != (n_frames, numbers.size, 3) or np.any(~np.isfinite(positions)):
            raise TrainingDataInputError(
                "fractional_positions must have shape (n_frames, n_atoms, 3)."
            )
        for name, value, shape in (
            ("steps", self.steps, (n_frames,)),
            ("times_ps", self.times_ps, (n_frames,)),
            ("energies_ev", self.energies_ev, (n_frames,)),
            (
                "forces_ev_per_angstrom",
                self.forces_ev_per_angstrom,
                (n_frames, numbers.size, 3),
            ),
            (
                "stresses_ev_per_angstrom3",
                self.stresses_ev_per_angstrom3,
                (n_frames, 3, 3),
            ),
            ("temperatures_kelvin", self.temperatures_kelvin, (n_frames,)),
        ):
            if value is not None and np.asarray(value).shape != shape:
                raise TrainingDataInputError(
                    f"{name} has shape {np.asarray(value).shape}, expected {shape}."
                )
        if len(self.scf_iteration_limit_reached) != n_frames:
            raise TrainingDataInputError(
                "SCF-limit flags must align with the frame axis."
            )
        for name, value, dtype in (
            ("source_frame_indices", source_indices, np.dtype(np.int64)),
            ("frame_ids", frame_ids, np.dtype(np.int64)),
            ("atomic_numbers", numbers, np.dtype(np.int32)),
            ("pbc", pbc, np.dtype(np.bool_)),
            ("cells_angstrom", cells, np.dtype(np.float64)),
            ("fractional_positions", positions, np.dtype(np.float64)),
        ):
            object.__setattr__(
                self, name, _immutable_array(value, dtype=dtype)
            )
        for name, dtype in (
            ("steps", np.int64),
            ("times_ps", np.float64),
            ("energies_ev", np.float64),
            ("forces_ev_per_angstrom", np.float64),
            ("stresses_ev_per_angstrom3", np.float64),
            ("temperatures_kelvin", np.float64),
        ):
            object.__setattr__(
                self,
                name,
                _optional_array(getattr(self, name), dtype=np.dtype(dtype), name=name),
            )
        object.__setattr__(
            self,
            "scf_iteration_limit_reached",
            tuple(
                None if value is None else bool(value)
                for value in self.scf_iteration_limit_reached
            ),
        )

    @classmethod
    def _from_authenticated_arrays(
        cls,
        *,
        source_frame_indices: ArrayLike,
        frame_ids: ArrayLike,
        steps: ArrayLike | None,
        times_ps: ArrayLike | None,
        atomic_numbers: ArrayLike,
        pbc: ArrayLike,
        cells_angstrom: ArrayLike,
        fractional_positions: ArrayLike,
        energies_ev: ArrayLike | None,
        forces_ev_per_angstrom: ArrayLike | None,
        stresses_ev_per_angstrom3: ArrayLike | None,
        temperatures_kelvin: ArrayLike | None,
        scf_iteration_limit_reached: Sequence[bool | None],
        expected_n_frames: int,
        expected_n_atoms: int,
    ) -> "FrameData":
        """Restore arrays already authenticated by the frame-cache layer.

        The public constructor remains strict for untrusted inputs.  Cache
        restoration has already verified every member's SHA-256, dtype, shape,
        and immutable origin, so repeating full finite/uniqueness scans would
        add several whole-array passes without adding a new trust boundary.
        """

        n_frames = int(expected_n_frames)
        n_atoms = int(expected_n_atoms)
        arrays: dict[str, np.ndarray | None] = {
            "source_frame_indices": _immutable_array(source_frame_indices, dtype=np.dtype(np.int64)),
            "frame_ids": _immutable_array(frame_ids, dtype=np.dtype(np.int64)),
            "steps": _optional_array(steps, dtype=np.dtype(np.int64), name="steps"),
            "times_ps": _optional_array(times_ps, dtype=np.dtype(np.float64), name="times_ps"),
            "atomic_numbers": _immutable_array(atomic_numbers, dtype=np.dtype(np.int32)),
            "pbc": _immutable_array(pbc, dtype=np.dtype(np.bool_)),
            "cells_angstrom": _immutable_array(cells_angstrom, dtype=np.dtype(np.float64)),
            "fractional_positions": _immutable_array(fractional_positions, dtype=np.dtype(np.float64)),
            "energies_ev": _optional_array(energies_ev, dtype=np.dtype(np.float64), name="energies_ev"),
            "forces_ev_per_angstrom": _optional_array(forces_ev_per_angstrom, dtype=np.dtype(np.float64), name="forces_ev_per_angstrom"),
            "stresses_ev_per_angstrom3": _optional_array(stresses_ev_per_angstrom3, dtype=np.dtype(np.float64), name="stresses_ev_per_angstrom3"),
            "temperatures_kelvin": _optional_array(temperatures_kelvin, dtype=np.dtype(np.float64), name="temperatures_kelvin"),
        }
        expected_shapes = {
            "source_frame_indices": (n_frames,),
            "frame_ids": (n_frames,),
            "steps": (n_frames,),
            "times_ps": (n_frames,),
            "atomic_numbers": (n_atoms,),
            "pbc": (3,),
            "cells_angstrom": (n_frames, 3, 3),
            "fractional_positions": (n_frames, n_atoms, 3),
            "energies_ev": (n_frames,),
            "forces_ev_per_angstrom": (n_frames, n_atoms, 3),
            "stresses_ev_per_angstrom3": (n_frames, 3, 3),
            "temperatures_kelvin": (n_frames,),
        }
        for name, expected in expected_shapes.items():
            value = arrays[name]
            if value is not None and value.shape != expected:
                raise TrainingDataInputError(
                    f"Authenticated {name} has shape {value.shape}, expected {expected}."
                )
        flags = tuple(
            None if value is None else bool(value)
            for value in scf_iteration_limit_reached
        )
        if len(flags) != n_frames:
            raise TrainingDataInputError(
                "Authenticated SCF-limit flags do not align with frame count."
            )
        result = object.__new__(cls)
        for name, value in arrays.items():
            object.__setattr__(result, name, value)
        object.__setattr__(result, "scf_iteration_limit_reached", flags)
        return result

    @property
    def n_frames(self) -> int:
        return int(self.source_frame_indices.size)

    @property
    def n_atoms(self) -> int:
        return int(self.atomic_numbers.size)

    @classmethod
    def from_collection(
        cls,
        collection: AtomisticFrameCollection,
        *,
        source_frame_indices: ArrayLike | None = None,
        energies_ev: ArrayLike | None = None,
        scf_iteration_limit_reached: Sequence[bool | None] | None = None,
    ) -> "FrameData":
        n_frames = collection.n_frames
        source_indices = (
            np.arange(n_frames, dtype=np.int64)
            if source_frame_indices is None
            else np.asarray(source_frame_indices, dtype=np.int64)
        )
        energy = collection.potential_energies if energies_ev is None else energies_ev
        return cls(
            source_frame_indices=source_indices,
            frame_ids=collection.frame_ids,
            steps=collection.steps,
            times_ps=collection.times,
            atomic_numbers=collection.atomic_numbers,
            pbc=collection.pbc,
            cells_angstrom=collection.cells,
            fractional_positions=collection.fractional_positions,
            energies_ev=None if energy is None else np.asarray(energy, dtype=np.float64),
            forces_ev_per_angstrom=collection.forces,
            stresses_ev_per_angstrom3=collection.stresses,
            temperatures_kelvin=collection.temperatures,
            scf_iteration_limit_reached=(
                tuple(None for _ in range(n_frames))
                if scf_iteration_limit_reached is None
                else tuple(scf_iteration_limit_reached)
            ),
        )


@dataclass(frozen=True, slots=True)
class TrainingFrameRecord:
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
    label_domain_id: str
    selected_energy_channel: str
    energy_present: bool
    forces_present: bool
    stress_present: bool
    instantaneous_temperature_kelvin: float | None
    temperature_condition_digest: str
    geometry_fingerprint: str
    label_payload_digest: str
    labeled_configuration_fingerprint: str
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in (
            "frame_uid",
            "source_identity_signature",
            "source_occurrence_signature",
            "atomic_numbers_digest",
            "temperature_condition_digest",
            "geometry_fingerprint",
            "label_payload_digest",
            "labeled_configuration_fingerprint",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.source_frame_index < 0 or self.atom_count <= 0:
            raise TrainingDataInputError("Frame indices and atom count are invalid.")
        if not self.run_id.strip() or not self.label_domain_id.strip() or not self.selected_energy_channel.strip():
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
    def identity(self) -> FrameIdentity:
        return FrameIdentity(
            frame_uid=self.frame_uid,
            geometry_fingerprint=self.geometry_fingerprint,
            label_payload_digest=self.label_payload_digest,
            labeled_configuration_fingerprint=self.labeled_configuration_fingerprint,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_FRAME_RECORD_SCHEMA,
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
            "label_domain_id": self.label_domain_id,
            "selected_energy_channel": self.selected_energy_channel,
            "energy_present": self.energy_present,
            "forces_present": self.forces_present,
            "stress_present": self.stress_present,
            "instantaneous_temperature_kelvin": self.instantaneous_temperature_kelvin,
            "temperature_condition_digest": self.temperature_condition_digest,
            "geometry_fingerprint": self.geometry_fingerprint,
            "label_payload_digest": self.label_payload_digest,
            "labeled_configuration_fingerprint": self.labeled_configuration_fingerprint,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingFrameRecord":
        if payload.get("schema") != TRAINING_FRAME_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported training-frame-record schema.")
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
            cell_matrix_angstrom=tuple(tuple(float(v) for v in row) for row in payload["cell_matrix_angstrom"]),
            cell_volume_angstrom3=float(payload["cell_volume_angstrom3"]),
            label_domain_id=str(payload["label_domain_id"]),
            selected_energy_channel=str(payload["selected_energy_channel"]),
            energy_present=bool(payload["energy_present"]),
            forces_present=bool(payload["forces_present"]),
            stress_present=bool(payload["stress_present"]),
            instantaneous_temperature_kelvin=(
                None if payload.get("instantaneous_temperature_kelvin") is None
                else float(payload["instantaneous_temperature_kelvin"])
            ),
            temperature_condition_digest=str(payload["temperature_condition_digest"]),
            geometry_fingerprint=str(payload["geometry_fingerprint"]),
            label_payload_digest=str(payload["label_payload_digest"]),
            labeled_configuration_fingerprint=str(payload["labeled_configuration_fingerprint"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Training-frame-record digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TrainingFrameCatalog:
    dataset_id: str
    source_catalog_digest: str
    geometry_policy_digest: str
    label_policy_digest: str
    eligibility_policy_digest: str
    reference_cell_catalog: ReferenceCellCatalog
    temperature_conditions: TemperatureConditionCatalog
    frames: tuple[TrainingFrameRecord, ...]
    eligibility: FrameEligibilityCatalog
    strain_records: tuple[FrameStrainRecord, ...]
    duplicates: DuplicateDetectionCatalog
    parser_version: str = MLFF_DATA3_PARSER_VERSION
    notes: tuple[str, ...] = ()
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)
    _by_frame_uid: dict[str, TrainingFrameRecord] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in (
            "source_catalog_digest",
            "geometry_policy_digest",
            "label_policy_digest",
            "eligibility_policy_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        frames = tuple(sorted(self.frames, key=lambda item: (item.run_id, item.source_frame_index)))
        if len({item.frame_uid for item in frames}) != len(frames):
            raise TrainingDataInputError("Duplicate frame UIDs in frame catalog.")
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

    def frame(self, frame_uid: str) -> TrainingFrameRecord:
        """Return one immutable frame record by occurrence UID."""

        try:
            return self._by_frame_uid[frame_uid]
        except KeyError:
            raise KeyError(frame_uid) from None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_FRAME_CATALOG_SCHEMA,
            "dataset_id": self.dataset_id,
            "source_catalog_digest": self.source_catalog_digest,
            "geometry_policy_digest": self.geometry_policy_digest,
            "label_policy_digest": self.label_policy_digest,
            "eligibility_policy_digest": self.eligibility_policy_digest,
            "reference_cell_catalog": self.reference_cell_catalog.to_dict(),
            "temperature_conditions": self.temperature_conditions.to_dict(),
            "frames": [item.to_dict() for item in self.frames],
            "eligibility": self.eligibility.to_dict(),
            "strain_records": [item.to_dict() for item in self.strain_records],
            "duplicates": self.duplicates.to_dict(),
            "parser_version": self.parser_version,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingFrameCatalog":
        if payload.get("schema") != TRAINING_FRAME_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported training-frame-catalog schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            source_catalog_digest=str(payload["source_catalog_digest"]),
            geometry_policy_digest=str(payload["geometry_policy_digest"]),
            label_policy_digest=str(payload["label_policy_digest"]),
            eligibility_policy_digest=str(payload["eligibility_policy_digest"]),
            reference_cell_catalog=ReferenceCellCatalog.from_dict(payload["reference_cell_catalog"]),
            temperature_conditions=TemperatureConditionCatalog.from_dict(payload["temperature_conditions"]),
            frames=tuple(TrainingFrameRecord.from_dict(v) for v in payload.get("frames", ())),
            eligibility=FrameEligibilityCatalog.from_dict(payload["eligibility"]),
            strain_records=tuple(FrameStrainRecord.from_dict(v) for v in payload.get("strain_records", ())),
            duplicates=DuplicateDetectionCatalog.from_dict(payload["duplicates"]),
            parser_version=str(payload.get("parser_version", MLFF_DATA3_PARSER_VERSION)),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Training-frame-catalog digest mismatch.")
        return result


def _label_at(array: np.ndarray | None, index: int) -> Any:
    if array is None:
        return None
    value = array[index]
    if np.isscalar(value):
        return float(value)
    return value


def _composition_counts(numbers: np.ndarray) -> dict[str, int]:
    try:
        from ase.data import chemical_symbols  # type: ignore
    except ModuleNotFoundError:
        # DATA3 source-independent tests use atomic numbers only; source validation
        # falls back to atom count when ASE symbol data are unavailable.
        return {}
    result: dict[str, int] = {}
    for number in numbers:
        symbol = chemical_symbols[int(number)]
        result[symbol] = result.get(symbol, 0) + 1
    return result



def _build_training_frame_records_for_run(task: tuple[Any, ...]) -> tuple[str, tuple[TrainingFrameRecord, ...], tuple[FrameEligibilityDecision, ...], tuple[FrameStrainRecord, ...]]:
    (
        run_id, source, data, temperature_condition, reference,
        geometry_active, label_active, eligibility_active, strain_active,
    ) = task
    records: list[TrainingFrameRecord] = []
    eligibility_decisions: list[FrameEligibilityDecision] = []
    strain_records: list[FrameStrainRecord] = []
    derivative_digest = source.electronic_structure.derivative_convention.content_digest
    occurrence_signature = source_occurrence_signature(
        run_id=source.run_id,
        source_locator=source.source_locator,
        source_identity_signature=source.source_identity_signature,
    )
    label_domain = source.label_domain_id
    if label_domain is None:
        raise TrainingDataInputError(f"Source {run_id!r} has no resolved label domain.")
    atomic_digest = digest(data.atomic_numbers.tolist())
    assertions = dict(source.assertions)
    for local_index in range(data.n_frames):
        source_index = int(data.source_frame_indices[local_index])
        uid = frame_uid(occurrence_signature, source_index)
        energy = _label_at(data.energies_ev, local_index)
        forces = _label_at(data.forces_ev_per_angstrom, local_index)
        stress = _label_at(data.stresses_ev_per_angstrom3, local_index)
        geometry_digest = geometry_fingerprint(
            data.atomic_numbers,
            data.pbc,
            data.cells_angstrom[local_index],
            data.fractional_positions[local_index],
            policy=geometry_active,
        )
        label_digest = label_payload_digest(
            label_domain_id=label_domain,
            selected_energy_channel=source.selected_energy.source_name,
            energy_ev=energy,
            forces_ev_per_angstrom=forces,
            stress_ev_per_angstrom3=stress,
            derivative_convention_digest=derivative_digest,
            policy=label_active,
        )
        combined = labeled_configuration_fingerprint(geometry_digest, label_digest)
        cell = np.asarray(data.cells_angstrom[local_index], dtype=np.float64)
        temperature = _label_at(data.temperatures_kelvin, local_index)
        if temperature is not None and not np.isfinite(float(temperature)):
            temperature = None
        record = TrainingFrameRecord(
            frame_uid=uid,
            run_id=run_id,
            source_identity_signature=source.source_identity_signature,
            source_occurrence_signature=occurrence_signature,
            source_frame_index=source_index,
            source_frame_id=int(data.frame_ids[local_index]),
            step=None if data.steps is None else int(data.steps[local_index]),
            time_ps=None if data.times_ps is None else float(data.times_ps[local_index]),
            atom_count=data.n_atoms,
            atomic_numbers_digest=atomic_digest,
            pbc=tuple(bool(v) for v in data.pbc),
            cell_matrix_angstrom=tuple(tuple(float(v) for v in row) for row in cell),
            cell_volume_angstrom3=float(np.linalg.det(cell)),
            label_domain_id=label_domain,
            selected_energy_channel=source.selected_energy.source_name,
            energy_present=energy is not None,
            forces_present=forces is not None,
            stress_present=stress is not None,
            instantaneous_temperature_kelvin=temperature,
            temperature_condition_digest=temperature_condition.content_digest,
            geometry_fingerprint=geometry_digest,
            label_payload_digest=label_digest,
            labeled_configuration_fingerprint=combined,
        )
        records.append(record)
        eligibility_decisions.append(
            assess_frame_eligibility(
                frame_record=record,
                atomic_numbers=data.atomic_numbers,
                fractional_positions=data.fractional_positions[local_index],
                cell=cell,
                energy_ev=energy,
                forces_ev_per_angstrom=forces,
                stress_ev_per_angstrom3=stress,
                scf_iteration_limit_reached=data.scf_iteration_limit_reached[local_index],
                source_quality_status=source.quality_assessment_status.value,
                source_quality_outcome=source.quality_outcome,
                policy=eligibility_active,
            )
        )
        strain_records.append(
            compute_frame_strain(
                frame_uid=uid,
                current_cell_angstrom=cell,
                reference=reference,
                ensemble=source.ensemble,
                assertions=assertions,
                policy=strain_active,
            )
        )
    return run_id, tuple(records), tuple(eligibility_decisions), tuple(strain_records)


def build_training_frame_catalog(
    source_catalog: Any,
    frame_data_by_run: Mapping[str, FrameData],
    *,
    temperature_targets_by_run: Mapping[str, TemperatureTargetEvidence] | None = None,
    explicit_reference_cells_by_group: Mapping[str, ArrayLike] | None = None,
    geometry_policy: GeometryFingerprintPolicy | None = None,
    label_policy: LabelFingerprintPolicy | None = None,
    eligibility_policy: FrameEligibilityPolicy | None = None,
    reference_cell_policy: ReferenceCellPolicy | None = None,
    strain_policy: StrainPolicy | None = None,
    parallel_workers: int = 1,
    progress_callback: Callable[[str], None] | None = None,
) -> TrainingFrameCatalog:
    """Build DATA3 records from a DATA2 source catalog and normalized arrays."""

    geometry_active = GeometryFingerprintPolicy() if geometry_policy is None else geometry_policy
    label_active = LabelFingerprintPolicy() if label_policy is None else label_policy
    eligibility_active = FrameEligibilityPolicy() if eligibility_policy is None else eligibility_policy
    reference_active = ReferenceCellPolicy() if reference_cell_policy is None else reference_cell_policy
    strain_active = StrainPolicy() if strain_policy is None else strain_policy
    source_map = {item.run_id: item for item in source_catalog.sources}
    if set(source_map) != set(frame_data_by_run):
        raise TrainingDataInputError(
            "frame_data_by_run keys must exactly match source-catalog run IDs."
        )
    targets = {} if temperature_targets_by_run is None else dict(temperature_targets_by_run)

    for run_id, source in source_map.items():
        data = frame_data_by_run[run_id]
        if data.n_frames != source.frame_count:
            raise TrainingDataInputError(
                f"Frame count mismatch for {run_id!r}: {data.n_frames} != {source.frame_count}."
            )
        if data.n_atoms != source.composition.atom_count:
            raise TrainingDataInputError(
                f"Atom count mismatch for {run_id!r}: {data.n_atoms} != {source.composition.atom_count}."
            )
        counts = _composition_counts(data.atomic_numbers)
        if counts and counts != source.composition.as_dict():
            raise TrainingDataInputError(f"Composition mismatch for {run_id!r}.")
        if np.any(data.source_frame_indices >= source.frame_count):
            raise TrainingDataInputError(f"Source-frame index exceeds source count for {run_id!r}.")

    temperature_records = []
    for run_id, source in source_map.items():
        data = frame_data_by_run[run_id]
        target = targets.get(run_id, TemperatureTargetEvidence())
        temperature_records.append(
            build_temperature_condition(
                run_id=run_id,
                source_identity_signature=source.source_identity_signature,
                ensemble=source.ensemble,
                instantaneous_temperatures_kelvin=data.temperatures_kelvin,
                target_start_kelvin=target.target_start_kelvin,
                target_end_kelvin=target.target_end_kelvin,
                target_evidence=target.evidence,
            )
        )
    temperature_catalog = TemperatureConditionCatalog(tuple(temperature_records))

    reference_catalog = build_reference_cell_catalog(
        source_catalog.sources,
        cells_by_run={run_id: data.cells_angstrom for run_id, data in frame_data_by_run.items()},
        explicit_cells_by_group=explicit_reference_cells_by_group,
        policy=reference_active,
    )

    records: list[TrainingFrameRecord] = []
    eligibility_decisions: list[FrameEligibilityDecision] = []
    strain_records: list[FrameStrainRecord] = []
    ordered_run_ids = sorted(source_map)
    tasks: list[tuple[Any, ...]] = []
    for run_id in ordered_run_ids:
        source = source_map[run_id]
        data = frame_data_by_run[run_id]
        temperature_condition = temperature_catalog.for_run(run_id)
        resolution = reference_catalog.resolution_for_run(run_id)
        reference = (
            None
            if resolution.reference_cell_id is None
            else reference_catalog.record(resolution.reference_cell_id)
        )
        tasks.append((
            run_id, source, data, temperature_condition, reference,
            geometry_active, label_active, eligibility_active, strain_active,
        ))

    workers = max(1, min(int(parallel_workers), len(tasks))) if tasks else 1
    completed = 0
    if workers == 1:
        results = map(_build_training_frame_records_for_run, tasks)
        for run_id, run_records, run_decisions, run_strains in results:
            records.extend(run_records)
            eligibility_decisions.extend(run_decisions)
            strain_records.extend(run_strains)
            completed += 1
            if progress_callback is not None:
                progress_callback(
                    f"status=item-complete; progress={format_progress_fraction(completed, len(tasks))}; item={run_id}; frames={len(run_records):,}; workers=1"
                )
    else:
        for result in isolated_process_map(__name__, "_build_training_frame_records_for_run", tasks, workers=workers):
            run_id, run_records, run_decisions, run_strains = result
            records.extend(run_records)
            eligibility_decisions.extend(run_decisions)
            strain_records.extend(run_strains)
            completed += 1
            if progress_callback is not None:
                progress_callback(
                    f"status=item-complete; progress={format_progress_fraction(completed, len(tasks))}; item={run_id}; frames={len(run_records):,}; workers={workers}"
                )

    duplicate_catalog = build_duplicate_detection_catalog(
        records,
        source_frame_counts={item.run_id: item.frame_count for item in source_catalog.sources},
    )
    return TrainingFrameCatalog(
        dataset_id=source_catalog.dataset_id,
        source_catalog_digest=source_catalog.content_digest,
        geometry_policy_digest=geometry_active.policy_digest,
        label_policy_digest=label_active.policy_digest,
        eligibility_policy_digest=eligibility_active.policy_digest,
        reference_cell_catalog=reference_catalog,
        temperature_conditions=temperature_catalog,
        frames=tuple(records),
        eligibility=FrameEligibilityCatalog(
            policy_digest=eligibility_active.policy_digest,
            decisions=tuple(eligibility_decisions),
        ),
        strain_records=tuple(strain_records),
        duplicates=duplicate_catalog,
        notes=(
            "DATA3 contains source frame facts, eligibility, conditions, and strain only; statistical partitioning begins in DATA5.",
        ),
    )


def _control_value(run_controls: Any, name: str) -> Any:
    value = run_controls.effective_value(name)
    return run_controls.explicit_value(name) if value is None else value


def build_vasp_training_frame_catalog(
    source_catalog: Any,
    *,
    base_directory: str | Path = ".",
    strict: bool = True,
    **kwargs: Any,
) -> TrainingFrameCatalog:
    """Build DATA3 directly from the VASP sources bound by a DATA2 catalog."""

    from mdstats.io import read_vasp_frames, read_vasp_run_controls

    frame_data: dict[str, FrameData] = {}
    targets: dict[str, TemperatureTargetEvidence] = {}
    base = Path(base_directory)
    for source in source_catalog.sources:
        path = Path(source.source_locator)
        if not path.is_absolute():
            path = base / path
        bundle = read_vasp_run_controls(path)
        if bundle.source_identity.signature != source.source_identity_signature:
            raise TrainingDataInputError(
                f"Source identity changed for {source.run_id!r}."
            )
        if bundle.signature != source.source_control_bundle_signature:
            raise TrainingDataInputError(
                f"Source control bundle changed for {source.run_id!r}."
            )
        channel = bundle.energy_catalog.channel(source.selected_energy.source_name)
        if channel is None:
            raise TrainingDataInputError(
                f"Selected energy channel is absent for {source.run_id!r}."
            )
        collection = read_vasp_frames(
            path,
            strict=strict,
            assess_quality=False,
            assess_stationarity=False,
            assess_admissibility=False,
        )
        frame_data[source.run_id] = FrameData.from_collection(
            collection,
            source_frame_indices=np.arange(collection.n_frames, dtype=np.int64),
            energies_ev=channel.as_array(),
            scf_iteration_limit_reached=bundle.numerical_quality_controls.scf_iteration_limit_reached,
        )
        tebeg = _control_value(bundle.run_controls, "TEBEG")
        teend = _control_value(bundle.run_controls, "TEEND")
        targets[source.run_id] = TemperatureTargetEvidence(
            target_start_kelvin=None if tebeg is None else float(tebeg),
            target_end_kelvin=None if teend is None else float(teend),
            evidence="VASP effective/explicit TEBEG and TEEND",
        )
    if "temperature_targets_by_run" in kwargs:
        raise TrainingDataInputError(
            "build_vasp_training_frame_catalog derives temperature targets from VASP controls."
        )
    return build_training_frame_catalog(
        source_catalog,
        frame_data,
        temperature_targets_by_run=targets,
        **kwargs,
    )
