"""Deep ``vasprun.xml`` control and energy reconstruction for Stage 11E-ENS0."""

from __future__ import annotations

from dataclasses import dataclass
import warnings
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping
import xml.etree.ElementTree as ET

import numpy as np

from .xml_recovery import (
    InterruptedXmlWarning,
    classify_xml_parse_error,
)
from .source_controls import (
    CompanionFileRecord,
    CompanionFileState,
    ControlAuthority,
    FrameEnergyCatalog,
    FrameEnergyChannel,
    NumericalMDQualityControls,
    SimulationControlBundleManifest,
    SimulationRunControls,
    SourceControlError,
    SourceControlSerializationError,
    SourceControlValue,
    SourceTrajectoryBundleIdentity,
    UserLabelDiagnostic,
    file_sha256,
)

VASP_RUN_CONTROLS_SCHEMA = "mdstats.vasp-run-controls.v1"
VASP_SOURCE_CONTROL_BUNDLE_SCHEMA = "mdstats.vasp-source-control-bundle.v1"
VASP_CONTROL_SEMANTICS_VERSION = "vasp-wiki-controls-2026-08-04.v2"

_STANDARD_COMPANIONS: tuple[tuple[str, str], ...] = (
    ("explicit_input", "INCAR"),
    ("initial_structure", "POSCAR"),
    ("final_structure", "CONTCAR"),
    ("text_output", "OUTCAR"),
    ("ionic_summary", "OSZICAR"),
    ("coordinate_trajectory", "XDATCAR"),
    ("thermostat_bias_report", "REPORT"),
    ("constraint_definition", "ICONST"),
    ("bias_potential", "PENALTYPOT"),
    ("metadynamics_hills", "HILLSPOT"),
)

_INTERRUPTED_WARNING_KEYS: set[tuple[str, str, str]] = set()

_ENERGY_ROLES = {
    "e_fr_energy": "electronic_free_energy",
    "e_0_energy": "electronic_zero_smearing_extrapolation",
    "e_wo_entrp": "electronic_energy_without_entropy",
    "kinetic": "ionic_kinetic_energy",
    "nosepot": "nose_thermostat_potential_energy",
    "nosekinetic": "nose_thermostat_kinetic_energy",
    "lattice kinetic": "lattice_kinetic_energy",
    "total": "source_reported_total_energy",
}


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


def _parse_scalar(text: str, value_type: str | None) -> Any:
    raw = text.strip()
    kind = None if value_type is None else value_type.strip().lower()
    if kind == "string":
        return raw
    if kind == "logical":
        normalized = raw.upper()
        if normalized in {"T", ".TRUE.", "TRUE"}:
            return True
        if normalized in {"F", ".FALSE.", "FALSE"}:
            return False
        return raw
    if kind == "int":
        try:
            return int(raw)
        except ValueError:
            return raw
    try:
        if any(marker in raw.lower() for marker in (".", "e", "d")):
            return float(raw.replace("D", "E").replace("d", "e"))
        return int(raw)
    except ValueError:
        return raw


def _parse_control_element(element: ET.Element) -> Any:
    raw = (element.text or "").strip()
    value_type = element.attrib.get("type")
    if value_type is not None and value_type.strip().lower() == "string":
        return raw
    parts = raw.split()
    if element.tag == "v" or len(parts) > 1:
        return tuple(_parse_scalar(part, value_type) for part in parts)
    return _parse_scalar(raw, value_type)


def _walk_controls(
    container: ET.Element,
    *,
    authority: ControlAuthority,
    root_name: str,
) -> tuple[SourceControlValue, ...]:
    records: list[SourceControlValue] = []
    occurrences: dict[str, int] = {}

    def visit(element: ET.Element, path: tuple[str, ...]) -> None:
        if element.tag == "separator":
            name = element.attrib.get("name", "separator").strip() or "separator"
            child_path = (*path, name)
        else:
            child_path = path
        if element.tag in {"i", "v"} and element.attrib.get("name"):
            name = element.attrib["name"].strip()
            key = name.upper()
            occurrence = occurrences.get(key, 0)
            occurrences[key] = occurrence + 1
            records.append(
                SourceControlValue(
                    name=name,
                    value=_parse_control_element(element),
                    raw_text=(element.text or "").strip(),
                    value_type=element.attrib.get("type"),
                    authority=authority,
                    section_path=child_path,
                    occurrence=occurrence,
                )
            )
        for child in list(element):
            visit(child, child_path)

    visit(container, (root_name,))
    return tuple(records)


def _control_lookup(records: tuple[SourceControlValue, ...], name: str) -> Any:
    key = name.upper()
    matches = [record.value for record in records if record.name.upper() == key]
    return None if not matches else matches[-1]


def _coerce_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, tuple):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def _coerce_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool) or isinstance(value, tuple):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _coerce_float_tuple(value: Any) -> tuple[float, ...] | None:
    if value is None:
        return None
    values = value if isinstance(value, tuple) else (value,)
    try:
        result = tuple(float(item) for item in values)
    except (TypeError, ValueError):
        return None
    return result if all(np.isfinite(item) for item in result) else None


def _parse_varray(element: ET.Element | None) -> np.ndarray | None:
    if element is None:
        return None
    rows: list[list[float]] = []
    for vector in element.findall("v"):
        try:
            values = [float(value) for value in (vector.text or "").split()]
        except ValueError:
            return None
        if len(values) != 3:
            return None
        rows.append(values)
    if not rows:
        return None
    return np.asarray(rows, dtype=np.float64)


def _extract_atom_information(
    atominfo: ET.Element,
) -> tuple[tuple[str, ...], np.ndarray | None]:
    atoms_set = atominfo.find("array[@name='atoms']/set")
    types_set = atominfo.find("array[@name='atomtypes']/set")
    if atoms_set is None:
        return (), None
    symbols: list[str] = []
    type_indices: list[int] = []
    for record in list(atoms_set):
        cells = [(cell.text or "").strip() for cell in record.findall("c")]
        if not cells:
            return (), None
        symbols.append(cells[0])
        try:
            type_indices.append(int(cells[1]))
        except (IndexError, ValueError):
            type_indices.append(-1)
    if types_set is None:
        return tuple(symbols), None
    type_masses: dict[int, float] = {}
    for index, record in enumerate(list(types_set), start=1):
        cells = [(cell.text or "").strip() for cell in record.findall("c")]
        try:
            type_masses[index] = float(cells[2])
        except (IndexError, ValueError):
            return tuple(symbols), None
    try:
        masses = np.asarray([type_masses[index] for index in type_indices], dtype=np.float64)
    except KeyError:
        masses = None
    return tuple(symbols), masses


def _extract_paw_datasets(atominfo: ET.Element) -> tuple[tuple[str, str], ...]:
    types_set = atominfo.find("array[@name='atomtypes']/set")
    if types_set is None:
        return ()
    result: list[tuple[str, str]] = []
    for record in list(types_set):
        cells = [(cell.text or "").strip() for cell in record.findall("c")]
        if len(cells) >= 5:
            result.append((cells[1], cells[4]))
    return tuple(result)


def _extract_kpoint_metadata(
    element: ET.Element,
) -> tuple[int | None, str | None, tuple[tuple[str, Any], ...]]:
    generation: dict[str, Any] = {}
    gen = element.find("generation")
    if gen is not None:
        for item in list(gen):
            name = item.attrib.get("name", item.tag)
            generation[name] = _parse_scalar(
                (item.text or ""), item.attrib.get("type")
            )
    vectors: list[tuple[float, ...]] = []
    weights: list[tuple[float, ...]] = []
    for varray, target in (
        (element.find("varray[@name='kpointlist']"), vectors),
        (element.find("varray[@name='weights']"), weights),
    ):
        if varray is not None:
            for vector in varray.findall("v"):
                try:
                    target.append(
                        tuple(float(value) for value in (vector.text or "").split())
                    )
                except ValueError:
                    continue
    payload = None
    if vectors or weights or generation:
        payload = _digest(
            {
                "generation": generation,
                "kpoints": vectors,
                "weights": weights,
            }
        )
    return (
        None if not vectors else len(vectors),
        payload,
        tuple(generation.items()),
    )


def _manifest(
    primary: Path,
    companion_files: Mapping[str, str | Path] | None,
) -> SimulationControlBundleManifest:
    records: list[CompanionFileRecord] = [
        CompanionFileRecord(
            role="primary_trajectory",
            file_name=primary.name,
            state=CompanionFileState.PRESENT_AND_BOUND,
            sha256=file_sha256(primary),
            size_bytes=primary.stat().st_size,
        )
    ]
    overrides = {str(role): Path(path) for role, path in (companion_files or {}).items()}
    for role, file_name in _STANDARD_COMPANIONS:
        path = overrides.pop(role, None)
        if path is not None and path.exists() and path.is_file():
            records.append(
                CompanionFileRecord(
                    role=role,
                    file_name=path.name,
                    state=CompanionFileState.PRESENT_AND_BOUND,
                    sha256=file_sha256(path),
                    size_bytes=path.stat().st_size,
                )
            )
        else:
            records.append(
                CompanionFileRecord(
                    role=role,
                    file_name=file_name if path is None else path.name,
                    state=CompanionFileState.NOT_PROVIDED,
                )
            )
    for role, path in sorted(overrides.items()):
        state = (
            CompanionFileState.PRESENT_AND_BOUND
            if path.exists() and path.is_file()
            else CompanionFileState.NOT_PROVIDED
        )
        records.append(
            CompanionFileRecord(
                role=role,
                file_name=path.name,
                state=state,
                sha256=file_sha256(path) if state is CompanionFileState.PRESENT_AND_BOUND else None,
                size_bytes=path.stat().st_size if state is CompanionFileState.PRESENT_AND_BOUND else None,
            )
        )
    return SimulationControlBundleManifest(tuple(records))


@dataclass(frozen=True, slots=True)
class VaspRunControls:
    """Exact explicit and effective VASP controls without ensemble inference."""

    source_program: str
    source_program_version: str | None
    source_program_subversion: str | None
    control_semantics_version: str
    explicit_controls: tuple[SourceControlValue, ...]
    effective_controls: tuple[SourceControlValue, ...]
    user_labels: tuple[UserLabelDiagnostic, ...]
    control_source_precedence: tuple[str, ...] = (
        "effective_parameters_for_realized_values",
        "explicit_incar_for_input_provenance",
    )

    def __post_init__(self) -> None:
        if not self.source_program:
            raise SourceControlError("source_program must be non-empty.")
        object.__setattr__(self, "explicit_controls", tuple(self.explicit_controls))
        object.__setattr__(self, "effective_controls", tuple(self.effective_controls))
        object.__setattr__(self, "user_labels", tuple(self.user_labels))
        object.__setattr__(
            self, "control_source_precedence", tuple(self.control_source_precedence)
        )

    def effective_value(self, name: str, default: Any = None) -> Any:
        value = _control_lookup(self.effective_controls, name)
        return default if value is None else value

    def explicit_value(self, name: str, default: Any = None) -> Any:
        value = _control_lookup(self.explicit_controls, name)
        return default if value is None else value

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": VASP_RUN_CONTROLS_SCHEMA,
            "source_program": self.source_program,
            "source_program_version": self.source_program_version,
            "source_program_subversion": self.source_program_subversion,
            "control_semantics_version": self.control_semantics_version,
            "explicit_controls": [item.to_dict() for item in self.explicit_controls],
            "effective_controls": [item.to_dict() for item in self.effective_controls],
            "user_labels": [item.to_dict() for item in self.user_labels],
            "control_source_precedence": list(self.control_source_precedence),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "VaspRunControls":
        if payload.get("schema") != VASP_RUN_CONTROLS_SCHEMA:
            raise SourceControlSerializationError("Unsupported VASP run-controls schema.")
        result = cls(
            source_program=str(payload["source_program"]),
            source_program_version=(
                None
                if payload.get("source_program_version") is None
                else str(payload["source_program_version"])
            ),
            source_program_subversion=(
                None
                if payload.get("source_program_subversion") is None
                else str(payload["source_program_subversion"])
            ),
            control_semantics_version=str(payload["control_semantics_version"]),
            explicit_controls=tuple(
                SourceControlValue.from_dict(item)
                for item in payload.get("explicit_controls", ())
            ),
            effective_controls=tuple(
                SourceControlValue.from_dict(item)
                for item in payload.get("effective_controls", ())
            ),
            user_labels=tuple(
                UserLabelDiagnostic.from_dict(item)
                for item in payload.get("user_labels", ())
            ),
            control_source_precedence=tuple(
                str(item) for item in payload.get("control_source_precedence", ())
            ),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError("VASP run-controls signature mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class VaspSourceControlBundle:
    """Complete Stage-11E-ENS0 output for one ``vasprun.xml`` source."""

    source_identity: SourceTrajectoryBundleIdentity
    manifest: SimulationControlBundleManifest
    run_controls: VaspRunControls
    energy_catalog: FrameEnergyCatalog
    numerical_quality_controls: NumericalMDQualityControls

    def _payload(self, *, include_energy_values: bool) -> dict[str, Any]:
        return {
            "schema": VASP_SOURCE_CONTROL_BUNDLE_SCHEMA,
            "source_identity": self.source_identity.to_dict(),
            "manifest": self.manifest.to_dict(),
            "run_controls": self.run_controls.to_dict(),
            "energy_catalog": self.energy_catalog.to_dict(
                include_values=include_energy_values
            ),
            "numerical_quality_controls": self.numerical_quality_controls.to_dict(),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload(include_energy_values=False))

    def to_dict(self, *, include_energy_values: bool = True) -> dict[str, Any]:
        return {
            **self._payload(include_energy_values=include_energy_values),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "VaspSourceControlBundle":
        if payload.get("schema") != VASP_SOURCE_CONTROL_BUNDLE_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported VASP source-control-bundle schema."
            )
        result = cls(
            source_identity=SourceTrajectoryBundleIdentity.from_dict(
                payload["source_identity"]
            ),
            manifest=SimulationControlBundleManifest.from_dict(payload["manifest"]),
            run_controls=VaspRunControls.from_dict(payload["run_controls"]),
            energy_catalog=FrameEnergyCatalog.from_dict(payload["energy_catalog"]),
            numerical_quality_controls=NumericalMDQualityControls.from_dict(
                payload["numerical_quality_controls"]
            ),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "VASP source-control-bundle signature mismatch."
            )
        return result


@dataclass(slots=True)
class _VaspXmlSupplement:
    potim_fs: float | None
    per_atom_masses: np.ndarray | None
    velocities: list[np.ndarray | None]
    kinetic_energies: list[float | None]
    total_energies: list[float | None]
    temperatures: list[float | None]


@dataclass(slots=True)
class _VaspXmlParseResult:
    bundle: VaspSourceControlBundle
    supplement: _VaspXmlSupplement
    atom_symbols: tuple[str, ...] = ()
    paw_datasets: tuple[tuple[str, str], ...] = ()
    kpoint_count: int | None = None
    kpoint_payload_sha256: str | None = None
    kpoint_generation: tuple[tuple[str, Any], ...] = ()


def _parse_vasp_xml(
    filename: str | Path,
    *,
    companion_files: Mapping[str, str | Path] | None = None,
) -> _VaspXmlParseResult:
    path = Path(filename)
    if not path.is_file():
        raise SourceControlError(f"VASP XML source does not exist: {path!s}.")

    manifest = _manifest(path, companion_files)
    generator: dict[str, str] = {}
    explicit_controls: tuple[SourceControlValue, ...] = ()
    effective_controls: tuple[SourceControlValue, ...] = ()
    atom_symbols: tuple[str, ...] = ()
    masses: np.ndarray | None = None
    paw_datasets: tuple[tuple[str, str], ...] = ()
    kpoint_count: int | None = None
    kpoint_payload_sha256: str | None = None
    kpoint_generation: tuple[tuple[str, Any], ...] = ()
    velocities: list[np.ndarray | None] = []
    energy_values: dict[str, list[float | None]] = {}
    temperatures: list[float | None] = []
    scf_counts: list[int] = []
    position_count = cell_count = force_count = stress_count = 0
    coordinate_hasher = hashlib.sha256()
    parse_complete = True
    parse_warning: str | None = None
    open_calculation_element: ET.Element | None = None
    recovered_unclosed_ionic_step = False
    discarded_incomplete_ionic_tail = False

    def consume_calculation(
        calculation: ET.Element,
        *,
        require_critical_payload: bool,
    ) -> bool:
        nonlocal position_count, cell_count, force_count, stress_count

        structure = calculation.find("structure")
        positions = _parse_varray(
            None if structure is None else structure.find("varray[@name='positions']")
        )
        basis = _parse_varray(
            None
            if structure is None
            else structure.find("crystal/varray[@name='basis']")
        )
        expected_atoms = None if not atom_symbols else len(atom_symbols)
        positions_valid = (
            positions is not None
            and (expected_atoms is None or positions.shape == (expected_atoms, 3))
            and bool(np.all(np.isfinite(positions)))
        )
        basis_valid = (
            basis is not None
            and basis.shape == (3, 3)
            and bool(np.all(np.isfinite(basis)))
            and float(np.linalg.det(basis)) > 0.0
        )
        force_array = _parse_varray(calculation.find("varray[@name='forces']"))
        force_valid = (
            force_array is not None
            and (expected_atoms is None or force_array.shape == (expected_atoms, 3))
            and bool(np.all(np.isfinite(force_array)))
        )

        current: dict[str, float] = {}
        energy = calculation.find("energy")
        if energy is not None:
            for item in energy.findall("i"):
                name = item.attrib.get("name", "").strip()
                if not name or item.text is None:
                    continue
                try:
                    current[name] = float(item.text)
                except ValueError:
                    continue

        critical_energy_names = {"e_fr_energy", "e_0_energy", "e_wo_entrp"}
        critical_energy_present = any(
            name in current and np.isfinite(current[name])
            for name in critical_energy_names
        )
        if require_critical_payload and not (
            positions_valid
            and basis_valid
            and force_valid
            and critical_energy_present
        ):
            return False

        frame_index = len(scf_counts)
        scf_counts.append(len(calculation.findall("scstep")))
        if positions_valid:
            position_count += 1
            contiguous = np.ascontiguousarray(positions, dtype=np.float64)
            coordinate_hasher.update(b"positions")
            coordinate_hasher.update(str(contiguous.shape).encode("ascii"))
            coordinate_hasher.update(contiguous.tobytes())
        if basis_valid:
            cell_count += 1
            contiguous = np.ascontiguousarray(basis, dtype=np.float64)
            coordinate_hasher.update(b"basis")
            coordinate_hasher.update(contiguous.tobytes())

        velocity = _parse_varray(
            None if structure is None else structure.find("varray[@name='velocities']")
        )
        if (
            velocity is not None
            and expected_atoms is not None
            and velocity.shape != (expected_atoms, 3)
        ):
            velocity = None
        velocities.append(velocity)
        if force_valid:
            force_count += 1
        stress_array = _parse_varray(calculation.find("varray[@name='stress']"))
        if stress_array is not None and stress_array.shape == (3, 3):
            stress_count += 1

        for values in energy_values.values():
            values.append(None)
        for name, value in current.items():
            if name not in energy_values:
                energy_values[name] = [None] * frame_index + [value]
            else:
                energy_values[name][-1] = value
        temperatures.append(current.get("temperature", current.get("temp")))
        return True

    try:
        for event, element in ET.iterparse(path, events=("start", "end")):
            if event == "start":
                if element.tag == "calculation":
                    open_calculation_element = element
                continue
            if element.tag == "generator":
                generator = {
                    item.attrib.get("name", "").strip().lower(): (item.text or "").strip()
                    for item in element.findall("i")
                    if item.attrib.get("name")
                }
                element.clear()
            elif element.tag == "incar":
                explicit_controls = _walk_controls(
                    element,
                    authority=ControlAuthority.EXPLICIT_INPUT,
                    root_name="incar",
                )
                element.clear()
            elif element.tag == "parameters":
                effective_controls = _walk_controls(
                    element,
                    authority=ControlAuthority.EFFECTIVE_PARAMETER,
                    root_name="parameters",
                )
                element.clear()
            elif element.tag == "atominfo":
                atom_symbols, masses = _extract_atom_information(element)
                paw_datasets = _extract_paw_datasets(element)
                element.clear()
            elif element.tag == "kpoints":
                (
                    kpoint_count,
                    kpoint_payload_sha256,
                    kpoint_generation,
                ) = _extract_kpoint_metadata(element)
                element.clear()
            elif element.tag == "calculation":
                consume_calculation(element, require_critical_payload=False)
                element.clear()
                open_calculation_element = None
    except ET.ParseError as exc:
        diagnostic = classify_xml_parse_error(path, exc)
        if not diagnostic.recoverable_trailing_interruption:
            raise SourceControlError(f"Could not parse VASP XML {path!s}: {exc}.") from exc
        parse_complete = False
        parse_warning = diagnostic.summary
        if open_calculation_element is not None:
            recovered_unclosed_ionic_step = consume_calculation(
                open_calculation_element,
                require_critical_payload=True,
            )
            discarded_incomplete_ionic_tail = not recovered_unclosed_ionic_step

    frame_count = len(scf_counts)
    if not parse_complete:
        missing: list[str] = []
        if not explicit_controls and not effective_controls:
            missing.append("VASP control blocks")
        if not atom_symbols:
            missing.append("atom identities")
        if frame_count == 0:
            missing.append("a complete ionic calculation")
        if missing:
            raise SourceControlError(
                f"Interrupted VASP XML {path!s} is ambiguous because it lacks "
                + ", ".join(missing)
                + f"; parser diagnostic: {parse_warning}."
            )
        tail_note = (
            "including one final calculation whose closing XML tag was missing"
            if recovered_unclosed_ionic_step
            else "the incomplete final calculation was ignored"
            if discarded_incomplete_ionic_tail
            else "only trailing closing XML tags were missing"
        )
        primary = manifest.by_role("primary_trajectory")
        warning_key = (
            str(path.resolve()),
            "" if primary is None or primary.sha256 is None else primary.sha256,
            str(parse_warning),
        )
        if warning_key not in _INTERRUPTED_WARNING_KEYS:
            _INTERRUPTED_WARNING_KEYS.add(warning_key)
            warnings.warn(
                f"Recovered {frame_count} complete ionic step(s) from interrupted VASP XML "
                f"{path!s}; {tail_note}. {parse_warning}",
                InterruptedXmlWarning,
                stacklevel=2,
            )
    channels = tuple(
        FrameEnergyChannel(
            source_name=name,
            semantic_role=_ENERGY_ROLES.get(name.lower(), "source_specific_energy"),
            units="eV",
            values=tuple(values),
        )
        for name, values in energy_values.items()
    )
    energy_catalog = FrameEnergyCatalog(frame_count=frame_count, channels=channels)

    user_comment_value = _control_lookup(explicit_controls, "SYSTEM")
    if user_comment_value is None:
        user_comment_value = _control_lookup(effective_controls, "SYSTEM")
    user_labels = (
        ()
        if user_comment_value is None
        else (
            UserLabelDiagnostic(source_name="SYSTEM", value=str(user_comment_value)),
        )
    )
    run_controls = VaspRunControls(
        source_program=generator.get("program", "vasp"),
        source_program_version=generator.get("version"),
        source_program_subversion=generator.get("subversion"),
        control_semantics_version=VASP_CONTROL_SEMANTICS_VERSION,
        explicit_controls=explicit_controls,
        effective_controls=effective_controls,
        user_labels=user_labels,
    )

    def effective(name: str) -> Any:
        return run_controls.effective_value(name)

    def explicit(name: str) -> Any:
        return run_controls.explicit_value(name)

    nelm = _coerce_int(effective("NELM"))
    limit_reached = tuple(
        None if nelm is None else count >= nelm for count in scf_counts
    )
    requested_steps = _coerce_int(effective("NSW"))
    output_stride = 1 if requested_steps == frame_count and frame_count > 0 else None
    quality = NumericalMDQualityControls(
        potim_fs=_coerce_float(effective("POTIM")),
        requested_ionic_steps=requested_steps,
        present_ionic_steps=frame_count,
        ionic_output_stride=output_stride,
        ediff_ev=_coerce_float(effective("EDIFF")),
        nelm=nelm,
        nelmin=_coerce_int(effective("NELMIN")),
        algo=_coerce_str(explicit("ALGO")),
        ialgo=_coerce_int(effective("IALGO")),
        prec_explicit=_coerce_str(explicit("PREC")),
        prec_effective=_coerce_str(effective("PREC")),
        lreal_explicit=explicit("LREAL"),
        lreal_effective=effective("LREAL"),
        ropt=_coerce_float_tuple(effective("ROPT")),
        encut_ev=_coerce_float(effective("ENCUT") or explicit("ENCUT")),
        isym=_coerce_int(effective("ISYM")),
        scf_iteration_counts=tuple(scf_counts),
        scf_iteration_limit_reached=limit_reached,
        positions_complete=position_count == frame_count,
        cells_complete=cell_count == frame_count,
        forces_complete=force_count == frame_count,
        stresses_complete=stress_count == frame_count,
        native_velocity_frame_count=sum(value is not None for value in velocities),
        energy_channel_completeness=tuple(
            (item.source_name, item.completeness_fraction)
            for item in energy_catalog.channels
        ),
        source_parse_complete=parse_complete,
        source_parse_warning=parse_warning,
        discarded_incomplete_ionic_tail=discarded_incomplete_ionic_tail,
        recovered_unclosed_ionic_step=recovered_unclosed_ionic_step,
    )

    atom_identity_sha256 = (
        None if not atom_symbols else _digest(list(atom_symbols))
    )
    potim = quality.potim_fs
    frame_axis_sha256 = _digest(
        {
            "frame_indices": list(range(frame_count)),
            "potim_fs": potim,
        }
    )
    primary_record = manifest.by_role("primary_trajectory")
    if primary_record is None or primary_record.sha256 is None:
        raise SourceControlError("Primary VASP source was not bound in the manifest.")
    source_identity = SourceTrajectoryBundleIdentity(
        source_format="vasp-vasprun-xml",
        primary_file_name=path.name,
        primary_sha256=primary_record.sha256,
        primary_size_bytes=path.stat().st_size,
        source_program=run_controls.source_program,
        source_program_version=run_controls.source_program_version,
        atom_count=None if not atom_symbols else len(atom_symbols),
        ionic_step_count=frame_count,
        atom_identity_sha256=atom_identity_sha256,
        coordinate_payload_sha256=(
            None if position_count == 0 and cell_count == 0 else coordinate_hasher.hexdigest()
        ),
        frame_axis_sha256=frame_axis_sha256,
        companion_manifest_signature=manifest.signature,
    )
    bundle = VaspSourceControlBundle(
        source_identity=source_identity,
        manifest=manifest,
        run_controls=run_controls,
        energy_catalog=energy_catalog,
        numerical_quality_controls=quality,
    )
    supplement = _VaspXmlSupplement(
        potim_fs=quality.potim_fs,
        per_atom_masses=masses,
        velocities=velocities,
        kinetic_energies=list(
            energy_catalog.channel("kinetic").values
            if energy_catalog.channel("kinetic") is not None
            else [None] * frame_count
        ),
        total_energies=list(
            energy_catalog.channel("total").values
            if energy_catalog.channel("total") is not None
            else [None] * frame_count
        ),
        temperatures=temperatures,
    )
    return _VaspXmlParseResult(
        bundle=bundle,
        supplement=supplement,
        atom_symbols=atom_symbols,
        paw_datasets=paw_datasets,
        kpoint_count=kpoint_count,
        kpoint_payload_sha256=kpoint_payload_sha256,
        kpoint_generation=kpoint_generation,
    )


def read_vasp_run_controls(
    filename: str | Path,
    *,
    companion_files: Mapping[str, str | Path] | None = None,
) -> VaspSourceControlBundle:
    """Reconstruct Stage-11E-ENS0 evidence from one ``vasprun.xml``.

    The function does not infer the ensemble.  In particular, ``SYSTEM`` is
    retained only as a :class:`UserLabelDiagnostic` with ``comment_only``
    authority.  Stage 11E-ENS1 consumes the exact controls produced here.
    """

    return _parse_vasp_xml(filename, companion_files=companion_files).bundle


__all__ = [
    "VASP_CONTROL_SEMANTICS_VERSION",
    "VASP_RUN_CONTROLS_SCHEMA",
    "VASP_SOURCE_CONTROL_BUNDLE_SCHEMA",
    "VaspRunControls",
    "VaspSourceControlBundle",
    "read_vasp_run_controls",
]
