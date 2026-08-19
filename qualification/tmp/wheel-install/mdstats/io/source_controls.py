"""Source-control and named energy-channel records for Stage 11E-ENS0.

The records in this module are source-program agnostic.  Source adapters retain
exact input names, precedence, units, completeness, and immutable source
identity without inferring an ensemble or thermodynamic admissibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Protocol, runtime_checkable

import numpy as np

SOURCE_TRAJECTORY_BUNDLE_IDENTITY_SCHEMA = (
    "mdstats.source-trajectory-bundle-identity.v1"
)
SIMULATION_CONTROL_BUNDLE_MANIFEST_SCHEMA = (
    "mdstats.simulation-control-bundle-manifest.v1"
)
SOURCE_CONTROL_VALUE_SCHEMA = "mdstats.source-control-value.v1"
FRAME_ENERGY_CHANNEL_SCHEMA = "mdstats.frame-energy-channel.v1"
FRAME_ENERGY_CATALOG_SCHEMA = "mdstats.frame-energy-catalog.v1"
NUMERICAL_MD_QUALITY_CONTROLS_SCHEMA = "mdstats.numerical-md-quality-controls.v1"
SOURCE_CONTROL_DIGEST_ALGORITHM = "sha256-canonical-json-v1"


class SourceControlError(ValueError):
    """Base error for immutable source-control records."""


class SourceControlSerializationError(SourceControlError):
    """Raised when a serialized source-control record is invalid."""


class CompanionFileState(str, Enum):
    PRESENT_AND_BOUND = "present_and_bound"
    KNOWN_ABSENT = "known_absent"
    NOT_APPLICABLE = "not_applicable"
    NOT_PROVIDED = "not_provided"
    REQUIRED_MISSING = "required_missing"


class ControlAuthority(str, Enum):
    EXPLICIT_INPUT = "explicit_input"
    EFFECTIVE_PARAMETER = "effective_parameter"
    COMMENT_ONLY = "comment_only"


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


def file_sha256(path: str | Path) -> str:
    """Return a SHA-256 digest of exact file bytes."""

    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        result = float(value)
        if not np.isfinite(result):
            raise SourceControlError("Control metadata contains a non-finite value.")
        return result
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, Mapping):
        return {
            str(key): _json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    raise SourceControlError(f"Unsupported metadata value {type(value).__name__}.")


def _tuple_value(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_tuple_value(item) for item in value)
    if isinstance(value, dict):
        return tuple(
            (str(key), _tuple_value(item))
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        )
    return value


@dataclass(frozen=True, slots=True)
class SourceTrajectoryBundleIdentity:
    """Bind source bytes, atom order, coordinates, and frame axis to one run."""

    source_format: str
    primary_file_name: str
    primary_sha256: str
    primary_size_bytes: int
    source_program: str | None
    source_program_version: str | None
    atom_count: int | None
    ionic_step_count: int
    atom_identity_sha256: str | None
    coordinate_payload_sha256: str | None
    frame_axis_sha256: str
    companion_manifest_signature: str

    def __post_init__(self) -> None:
        if not self.source_format:
            raise SourceControlError("source_format must be non-empty.")
        if not self.primary_file_name:
            raise SourceControlError("primary_file_name must be non-empty.")
        if len(self.primary_sha256) != 64:
            raise SourceControlError("primary_sha256 must be a SHA-256 hex digest.")
        if self.primary_size_bytes < 0:
            raise SourceControlError("primary_size_bytes must be nonnegative.")
        if self.ionic_step_count < 0:
            raise SourceControlError("ionic_step_count must be nonnegative.")
        if self.atom_count is not None and self.atom_count < 0:
            raise SourceControlError("atom_count must be nonnegative when present.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SOURCE_TRAJECTORY_BUNDLE_IDENTITY_SCHEMA,
            "digest_algorithm": SOURCE_CONTROL_DIGEST_ALGORITHM,
            "source_format": self.source_format,
            "primary_file_name": self.primary_file_name,
            "primary_sha256": self.primary_sha256,
            "primary_size_bytes": self.primary_size_bytes,
            "source_program": self.source_program,
            "source_program_version": self.source_program_version,
            "atom_count": self.atom_count,
            "ionic_step_count": self.ionic_step_count,
            "atom_identity_sha256": self.atom_identity_sha256,
            "coordinate_payload_sha256": self.coordinate_payload_sha256,
            "frame_axis_sha256": self.frame_axis_sha256,
            "companion_manifest_signature": self.companion_manifest_signature,
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> "SourceTrajectoryBundleIdentity":
        if payload.get("schema") != SOURCE_TRAJECTORY_BUNDLE_IDENTITY_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported source-trajectory-bundle-identity schema."
            )
        result = cls(
            source_format=str(payload["source_format"]),
            primary_file_name=str(payload["primary_file_name"]),
            primary_sha256=str(payload["primary_sha256"]),
            primary_size_bytes=int(payload["primary_size_bytes"]),
            source_program=(
                None if payload.get("source_program") is None else str(payload["source_program"])
            ),
            source_program_version=(
                None
                if payload.get("source_program_version") is None
                else str(payload["source_program_version"])
            ),
            atom_count=(
                None if payload.get("atom_count") is None else int(payload["atom_count"])
            ),
            ionic_step_count=int(payload["ionic_step_count"]),
            atom_identity_sha256=(
                None
                if payload.get("atom_identity_sha256") is None
                else str(payload["atom_identity_sha256"])
            ),
            coordinate_payload_sha256=(
                None
                if payload.get("coordinate_payload_sha256") is None
                else str(payload["coordinate_payload_sha256"])
            ),
            frame_axis_sha256=str(payload["frame_axis_sha256"]),
            companion_manifest_signature=str(payload["companion_manifest_signature"]),
        )
        expected = payload.get("signature")
        if expected is not None and expected != result.signature:
            raise SourceControlSerializationError(
                "Source trajectory bundle signature does not match its payload."
            )
        return result


@dataclass(frozen=True, slots=True)
class CompanionFileRecord:
    role: str
    file_name: str
    state: CompanionFileState
    sha256: str | None = None
    size_bytes: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", CompanionFileState(self.state))
        if not self.role or not self.file_name:
            raise SourceControlError("Companion file role and name must be non-empty.")
        if self.state is CompanionFileState.PRESENT_AND_BOUND:
            if self.sha256 is None or self.size_bytes is None:
                raise SourceControlError(
                    "present_and_bound companion files require digest and size."
                )
        if self.size_bytes is not None and self.size_bytes < 0:
            raise SourceControlError("Companion file size must be nonnegative.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "file_name": self.file_name,
            "state": self.state.value,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CompanionFileRecord":
        return cls(
            role=str(payload["role"]),
            file_name=str(payload["file_name"]),
            state=CompanionFileState(payload["state"]),
            sha256=None if payload.get("sha256") is None else str(payload["sha256"]),
            size_bytes=(
                None if payload.get("size_bytes") is None else int(payload["size_bytes"])
            ),
        )


@dataclass(frozen=True, slots=True)
class SimulationControlBundleManifest:
    """Classify primary and companion control artifacts without assuming absence."""

    records: tuple[CompanionFileRecord, ...]

    def __post_init__(self) -> None:
        records = tuple(sorted(self.records, key=lambda item: (item.role, item.file_name)))
        if len({(item.role, item.file_name) for item in records}) != len(records):
            raise SourceControlError("Companion manifest contains duplicate records.")
        object.__setattr__(self, "records", records)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SIMULATION_CONTROL_BUNDLE_MANIFEST_SCHEMA,
            "records": [record.to_dict() for record in self.records],
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> "SimulationControlBundleManifest":
        if payload.get("schema") != SIMULATION_CONTROL_BUNDLE_MANIFEST_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported simulation-control-bundle-manifest schema."
            )
        result = cls(
            records=tuple(
                CompanionFileRecord.from_dict(item) for item in payload.get("records", ())
            )
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Simulation control manifest signature mismatch."
            )
        return result

    def by_role(self, role: str) -> CompanionFileRecord | None:
        return next((item for item in self.records if item.role == role), None)


@dataclass(frozen=True, slots=True)
class SourceControlValue:
    """One exact source tag with typed value and source precedence."""

    name: str
    value: Any
    raw_text: str
    value_type: str | None
    authority: ControlAuthority
    section_path: tuple[str, ...]
    occurrence: int = 0

    def __post_init__(self) -> None:
        if not self.name:
            raise SourceControlError("Control name must be non-empty.")
        object.__setattr__(self, "authority", ControlAuthority(self.authority))
        object.__setattr__(self, "section_path", tuple(str(item) for item in self.section_path))
        if self.occurrence < 0:
            raise SourceControlError("Control occurrence must be nonnegative.")
        object.__setattr__(self, "value", _tuple_value(_json_value(self.value)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SOURCE_CONTROL_VALUE_SCHEMA,
            "name": self.name,
            "value": _json_value(self.value),
            "raw_text": self.raw_text,
            "value_type": self.value_type,
            "authority": self.authority.value,
            "section_path": list(self.section_path),
            "occurrence": self.occurrence,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceControlValue":
        if payload.get("schema") not in (None, SOURCE_CONTROL_VALUE_SCHEMA):
            raise SourceControlSerializationError("Unsupported source-control-value schema.")
        return cls(
            name=str(payload["name"]),
            value=payload.get("value"),
            raw_text=str(payload.get("raw_text", "")),
            value_type=(
                None if payload.get("value_type") is None else str(payload["value_type"])
            ),
            authority=ControlAuthority(payload["authority"]),
            section_path=tuple(str(item) for item in payload.get("section_path", ())),
            occurrence=int(payload.get("occurrence", 0)),
        )


@dataclass(frozen=True, slots=True)
class UserLabelDiagnostic:
    source_name: str
    value: str
    authority: ControlAuthority = ControlAuthority.COMMENT_ONLY
    notes: tuple[str, ...] = (
        "Retained as a user comment; excluded from ensemble and method inference.",
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "authority", ControlAuthority(self.authority))
        object.__setattr__(self, "notes", tuple(str(item) for item in self.notes))
        if self.authority is not ControlAuthority.COMMENT_ONLY:
            raise SourceControlError("User labels must have comment_only authority.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "value": self.value,
            "authority": self.authority.value,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "UserLabelDiagnostic":
        return cls(
            source_name=str(payload["source_name"]),
            value=str(payload.get("value", "")),
            authority=ControlAuthority(payload.get("authority", "comment_only")),
            notes=tuple(str(item) for item in payload.get("notes", ())),
        )


@runtime_checkable
class SimulationRunControls(Protocol):
    """Source-general Stage-11E-ENS0 control-record interface."""

    source_program: str
    source_program_version: str | None
    control_semantics_version: str

    @property
    def signature(self) -> str: ...

    def effective_value(self, name: str, default: Any = None) -> Any: ...

    def explicit_value(self, name: str, default: Any = None) -> Any: ...

    def to_dict(self) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class FrameEnergyChannel:
    """One exact per-ionic-frame energy channel from the source."""

    source_name: str
    semantic_role: str
    units: str
    values: tuple[float | None, ...]
    source_path: str = "calculation/energy"

    def __post_init__(self) -> None:
        if not self.source_name or not self.units:
            raise SourceControlError("Energy channel name and units must be non-empty.")
        normalized: list[float | None] = []
        for value in self.values:
            if value is None:
                normalized.append(None)
            else:
                result = float(value)
                if not np.isfinite(result):
                    raise SourceControlError(
                        f"Energy channel {self.source_name!r} contains a non-finite value."
                    )
                normalized.append(result)
        object.__setattr__(self, "values", tuple(normalized))

    @property
    def frame_count(self) -> int:
        return len(self.values)

    @property
    def present_count(self) -> int:
        return sum(value is not None for value in self.values)

    @property
    def completeness_fraction(self) -> float:
        return 1.0 if not self.values else self.present_count / len(self.values)

    @property
    def complete(self) -> bool:
        return self.present_count == len(self.values)

    @property
    def values_sha256(self) -> str:
        return _digest(list(self.values))

    def as_array(self, *, missing_value: float = np.nan) -> np.ndarray:
        result = np.asarray(
            [missing_value if value is None else value for value in self.values],
            dtype=np.float64,
        )
        result.setflags(write=False)
        return result

    def to_dict(self, *, include_values: bool = True) -> dict[str, Any]:
        payload = {
            "schema": FRAME_ENERGY_CHANNEL_SCHEMA,
            "source_name": self.source_name,
            "semantic_role": self.semantic_role,
            "units": self.units,
            "source_path": self.source_path,
            "frame_count": self.frame_count,
            "present_count": self.present_count,
            "completeness_fraction": self.completeness_fraction,
            "values_sha256": self.values_sha256,
        }
        if include_values:
            payload["values"] = list(self.values)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameEnergyChannel":
        if payload.get("schema") not in (None, FRAME_ENERGY_CHANNEL_SCHEMA):
            raise SourceControlSerializationError("Unsupported frame-energy-channel schema.")
        if "values" not in payload:
            raise SourceControlSerializationError(
                "Frame-energy-channel reconstruction requires values."
            )
        result = cls(
            source_name=str(payload["source_name"]),
            semantic_role=str(payload["semantic_role"]),
            units=str(payload["units"]),
            source_path=str(payload.get("source_path", "calculation/energy")),
            values=tuple(payload["values"]),
        )
        if payload.get("values_sha256") not in (None, result.values_sha256):
            raise SourceControlSerializationError("Energy-channel value digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class FrameEnergyCatalog:
    """Exact named per-frame energy channels without a generic-energy collapse."""

    frame_count: int
    channels: tuple[FrameEnergyChannel, ...]
    source_units: str = "eV"

    def __post_init__(self) -> None:
        if self.frame_count < 0:
            raise SourceControlError("Frame energy catalog count must be nonnegative.")
        channels = tuple(sorted(self.channels, key=lambda item: item.source_name))
        if len({item.source_name for item in channels}) != len(channels):
            raise SourceControlError("Frame energy catalog has duplicate channel names.")
        if any(item.frame_count != self.frame_count for item in channels):
            raise SourceControlError(
                "Every energy channel must align with the catalog frame count."
            )
        object.__setattr__(self, "channels", channels)

    def channel(self, source_name: str) -> FrameEnergyChannel | None:
        return next((item for item in self.channels if item.source_name == source_name), None)

    @property
    def channel_names(self) -> tuple[str, ...]:
        return tuple(item.source_name for item in self.channels)

    def _signature_payload(self) -> dict[str, Any]:
        return {
            "schema": FRAME_ENERGY_CATALOG_SCHEMA,
            "frame_count": self.frame_count,
            "source_units": self.source_units,
            "channels": [item.to_dict(include_values=False) for item in self.channels],
        }

    @property
    def signature(self) -> str:
        return _digest(self._signature_payload())

    def to_dict(self, *, include_values: bool = True) -> dict[str, Any]:
        return {
            "schema": FRAME_ENERGY_CATALOG_SCHEMA,
            "frame_count": self.frame_count,
            "source_units": self.source_units,
            "channels": [
                item.to_dict(include_values=include_values) for item in self.channels
            ],
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameEnergyCatalog":
        if payload.get("schema") != FRAME_ENERGY_CATALOG_SCHEMA:
            raise SourceControlSerializationError("Unsupported frame-energy-catalog schema.")
        result = cls(
            frame_count=int(payload["frame_count"]),
            source_units=str(payload.get("source_units", "eV")),
            channels=tuple(
                FrameEnergyChannel.from_dict(item) for item in payload.get("channels", ())
            ),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError("Frame energy catalog signature mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class NumericalMDQualityControls:
    """Source controls and traces needed by later STAT quality evaluation."""

    potim_fs: float | None
    requested_ionic_steps: int | None
    present_ionic_steps: int
    ionic_output_stride: int | None
    ediff_ev: float | None
    nelm: int | None
    nelmin: int | None
    algo: str | None
    ialgo: int | None
    prec_explicit: str | None
    prec_effective: str | None
    lreal_explicit: Any
    lreal_effective: Any
    ropt: tuple[float, ...] | None
    encut_ev: float | None
    isym: int | None
    scf_iteration_counts: tuple[int, ...]
    scf_iteration_limit_reached: tuple[bool | None, ...]
    positions_complete: bool
    cells_complete: bool
    forces_complete: bool
    stresses_complete: bool
    native_velocity_frame_count: int
    energy_channel_completeness: tuple[tuple[str, float], ...]
    source_parse_complete: bool = True
    source_parse_warning: str | None = None
    discarded_incomplete_ionic_tail: bool = False
    recovered_unclosed_ionic_step: bool = False

    def __post_init__(self) -> None:
        if self.present_ionic_steps < 0:
            raise SourceControlError("present_ionic_steps must be nonnegative.")
        if len(self.scf_iteration_counts) != self.present_ionic_steps:
            raise SourceControlError("SCF trace must align with ionic steps.")
        if len(self.scf_iteration_limit_reached) != self.present_ionic_steps:
            raise SourceControlError("SCF status trace must align with ionic steps.")
        if self.native_velocity_frame_count < 0:
            raise SourceControlError("native_velocity_frame_count must be nonnegative.")
        object.__setattr__(
            self,
            "energy_channel_completeness",
            tuple(sorted((str(name), float(value)) for name, value in self.energy_channel_completeness)),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": NUMERICAL_MD_QUALITY_CONTROLS_SCHEMA,
            "potim_fs": self.potim_fs,
            "requested_ionic_steps": self.requested_ionic_steps,
            "present_ionic_steps": self.present_ionic_steps,
            "ionic_output_stride": self.ionic_output_stride,
            "ediff_ev": self.ediff_ev,
            "nelm": self.nelm,
            "nelmin": self.nelmin,
            "algo": self.algo,
            "ialgo": self.ialgo,
            "prec_explicit": self.prec_explicit,
            "prec_effective": self.prec_effective,
            "lreal_explicit": _json_value(self.lreal_explicit),
            "lreal_effective": _json_value(self.lreal_effective),
            "ropt": None if self.ropt is None else list(self.ropt),
            "encut_ev": self.encut_ev,
            "isym": self.isym,
            "scf_iteration_counts": list(self.scf_iteration_counts),
            "scf_iteration_limit_reached": list(self.scf_iteration_limit_reached),
            "positions_complete": self.positions_complete,
            "cells_complete": self.cells_complete,
            "forces_complete": self.forces_complete,
            "stresses_complete": self.stresses_complete,
            "native_velocity_frame_count": self.native_velocity_frame_count,
            "energy_channel_completeness": {
                name: value for name, value in self.energy_channel_completeness
            },
            "source_parse_complete": self.source_parse_complete,
            "source_parse_warning": self.source_parse_warning,
            "discarded_incomplete_ionic_tail": self.discarded_incomplete_ionic_tail,
            "recovered_unclosed_ionic_step": self.recovered_unclosed_ionic_step,
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "NumericalMDQualityControls":
        if payload.get("schema") != NUMERICAL_MD_QUALITY_CONTROLS_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported numerical-MD-quality-controls schema."
            )
        result = cls(
            potim_fs=None if payload.get("potim_fs") is None else float(payload["potim_fs"]),
            requested_ionic_steps=(
                None
                if payload.get("requested_ionic_steps") is None
                else int(payload["requested_ionic_steps"])
            ),
            present_ionic_steps=int(payload["present_ionic_steps"]),
            ionic_output_stride=(
                None
                if payload.get("ionic_output_stride") is None
                else int(payload["ionic_output_stride"])
            ),
            ediff_ev=None if payload.get("ediff_ev") is None else float(payload["ediff_ev"]),
            nelm=None if payload.get("nelm") is None else int(payload["nelm"]),
            nelmin=None if payload.get("nelmin") is None else int(payload["nelmin"]),
            algo=None if payload.get("algo") is None else str(payload["algo"]),
            ialgo=None if payload.get("ialgo") is None else int(payload["ialgo"]),
            prec_explicit=(
                None if payload.get("prec_explicit") is None else str(payload["prec_explicit"])
            ),
            prec_effective=(
                None if payload.get("prec_effective") is None else str(payload["prec_effective"])
            ),
            lreal_explicit=_tuple_value(payload.get("lreal_explicit")),
            lreal_effective=_tuple_value(payload.get("lreal_effective")),
            ropt=None if payload.get("ropt") is None else tuple(float(v) for v in payload["ropt"]),
            encut_ev=None if payload.get("encut_ev") is None else float(payload["encut_ev"]),
            isym=None if payload.get("isym") is None else int(payload["isym"]),
            scf_iteration_counts=tuple(int(v) for v in payload.get("scf_iteration_counts", ())),
            scf_iteration_limit_reached=tuple(
                None if v is None else bool(v)
                for v in payload.get("scf_iteration_limit_reached", ())
            ),
            positions_complete=bool(payload["positions_complete"]),
            cells_complete=bool(payload["cells_complete"]),
            forces_complete=bool(payload["forces_complete"]),
            stresses_complete=bool(payload["stresses_complete"]),
            native_velocity_frame_count=int(payload["native_velocity_frame_count"]),
            energy_channel_completeness=tuple(
                (str(name), float(value))
                for name, value in payload.get("energy_channel_completeness", {}).items()
            ),
            source_parse_complete=bool(payload.get("source_parse_complete", True)),
            source_parse_warning=(
                None if payload.get("source_parse_warning") is None
                else str(payload["source_parse_warning"])
            ),
            discarded_incomplete_ionic_tail=bool(
                payload.get("discarded_incomplete_ionic_tail", False)
            ),
            recovered_unclosed_ionic_step=bool(
                payload.get("recovered_unclosed_ionic_step", False)
            ),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Numerical MD quality-control signature mismatch."
            )
        return result
