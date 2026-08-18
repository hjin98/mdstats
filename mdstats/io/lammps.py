"""Reader for native text LAMMPS custom-dump frame collections."""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from ase.data import atomic_masses, atomic_numbers as symbol_to_number

from ..exceptions import (
    CoordinateFormatError,
    IncompleteFieldError,
    MissingPositionError,
    MissingTimeError,
    UnitConversionError,
)
from ..preprocess.normalize import normalize_raw_frame_collection
from ..collection import AtomisticFrameCollection
from ..semantics import FrameSemantics, coerce_frame_semantics
from .common import RawFrameCollection, open_text_auto
from .units import UnitConversion, get_lammps_unit_conversion


@dataclass(slots=True)
class _DumpFrame:
    step: int
    time: float | None
    units: str | None
    cell: np.ndarray
    origin: np.ndarray
    pbc: np.ndarray
    columns: tuple[str, ...]
    values: dict[str, list[str]]
    box_kind: str


@dataclass(slots=True)
class _LogData:
    units: str | None
    timestep: float | None
    thermo: dict[int, dict[str, float]]


def _next_nonempty(iterator: Iterable[str]) -> str:
    for line in iterator:
        if line.strip():
            return line.rstrip("\n")
    raise EOFError


def _is_boundary_token(token: str) -> bool:
    return len(token) == 2 and all(character in "pfsm" for character in token)


def _parse_box(
    header: str, rows: list[str]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    tokens = header.split()[3:]
    numeric = [list(map(float, row.split())) for row in rows]

    if "abc" in tokens:
        if any(len(row) != 4 for row in numeric):
            raise CoordinateFormatError(
                "General triclinic BOX BOUNDS requires four values per row."
            )
        cell = np.asarray([row[:3] for row in numeric], dtype=np.float64)
        origin = np.asarray([row[3] for row in numeric], dtype=np.float64)
        boundary = [token for token in tokens if _is_boundary_token(token)]
        if len(boundary) == 3:
            pbc = np.asarray([token == "pp" for token in boundary], dtype=np.bool_)
        else:
            pbc = np.ones(3, dtype=np.bool_)
            warnings.warn(
                "General triclinic dump header does not record boundary flags; "
                "assuming periodic boundaries in all directions.",
                stacklevel=3,
            )
        return cell, origin, pbc, "general_triclinic"

    restricted = all(name in tokens for name in ("xy", "xz", "yz"))
    boundary = [token for token in tokens if _is_boundary_token(token)]
    if len(boundary) != 3:
        raise CoordinateFormatError(
            "LAMMPS BOX BOUNDS header must include three boundary-style tokens."
        )
    pbc = np.asarray([token == "pp" for token in boundary], dtype=np.bool_)

    if restricted:
        if any(len(row) < 3 for row in numeric):
            raise CoordinateFormatError(
                "Restricted triclinic BOX BOUNDS requires three values per row."
            )
        xlo_bound, xhi_bound, xy = numeric[0][:3]
        ylo_bound, yhi_bound, xz = numeric[1][:3]
        zlo_bound, zhi_bound, yz = numeric[2][:3]

        xlo = xlo_bound - min(0.0, xy, xz, xy + xz)
        xhi = xhi_bound - max(0.0, xy, xz, xy + xz)
        ylo = ylo_bound - min(0.0, yz)
        yhi = yhi_bound - max(0.0, yz)
        zlo, zhi = zlo_bound, zhi_bound

        cell = np.asarray(
            [
                [xhi - xlo, 0.0, 0.0],
                [xy, yhi - ylo, 0.0],
                [xz, yz, zhi - zlo],
            ],
            dtype=np.float64,
        )
        origin = np.asarray([xlo, ylo, zlo], dtype=np.float64)
        return cell, origin, pbc, "restricted_triclinic"

    if any(len(row) < 2 for row in numeric):
        raise CoordinateFormatError(
            "Orthogonal BOX BOUNDS requires two values per row."
        )
    lower = np.asarray([row[0] for row in numeric], dtype=np.float64)
    upper = np.asarray([row[1] for row in numeric], dtype=np.float64)
    cell = np.diag(upper - lower).astype(np.float64)
    return cell, lower, pbc, "orthogonal"


def _read_dump_frames(
    filename: str | Path,
    *,
    start: int | None = None,
    stop: int | None = None,
    stride: int = 1,
) -> tuple[list[_DumpFrame], int]:
    """Stream selected LAMMPS dump frames without materializing discarded tables.

    Positive ``start``/``stop`` and ``stride`` are applied while scanning the
    file.  Negative slice endpoints retain Python slice semantics by falling
    back to post-selection after reading all frames.  Even in streaming mode
    frame headers are scanned to preserve the exact source frame count.
    """
    if stride <= 0:
        raise ValueError("stride must be a positive integer.")
    post_select = (start is not None and int(start) < 0) or (stop is not None and int(stop) < 0)
    first = 0 if start is None else int(start)
    last = None if stop is None else int(stop)

    frames: list[_DumpFrame] = []
    source_frame_count = 0
    with open_text_auto(filename) as handle:
        iterator = iter(handle)
        while True:
            try:
                header = _next_nonempty(iterator)
            except EOFError:
                break
            if header.strip() != "ITEM: TIMESTEP":
                raise CoordinateFormatError(
                    f"Expected 'ITEM: TIMESTEP', found {header!r}."
                )
            frame_index = source_frame_count
            source_frame_count += 1
            selected = post_select or (
                frame_index >= first
                and (last is None or frame_index < last)
                and (frame_index - first) % stride == 0
            )
            try:
                step = int(_next_nonempty(iterator).strip())
                header = _next_nonempty(iterator)
            except (EOFError, ValueError) as exc:
                raise CoordinateFormatError("Malformed LAMMPS timestep block.") from exc

            time: float | None = None
            frame_units: str | None = None
            while header.startswith("ITEM: ") and header not in {
                "ITEM: NUMBER OF ATOMS",
            }:
                if header == "ITEM: TIME":
                    time = float(_next_nonempty(iterator).strip())
                elif header == "ITEM: UNITS":
                    frame_units = _next_nonempty(iterator).strip().lower()
                else:
                    break
                header = _next_nonempty(iterator)

            if header != "ITEM: NUMBER OF ATOMS":
                raise CoordinateFormatError(
                    f"Expected 'ITEM: NUMBER OF ATOMS' at step {step}, "
                    f"found {header!r}."
                )
            try:
                n_atoms = int(_next_nonempty(iterator).strip())
                box_header = _next_nonempty(iterator)
            except (EOFError, ValueError) as exc:
                raise CoordinateFormatError(
                    f"Malformed atom count at step {step}."
                ) from exc
            if n_atoms < 1:
                raise CoordinateFormatError(
                    f"Invalid atom count {n_atoms} at step {step}."
                )
            if not box_header.startswith("ITEM: BOX BOUNDS"):
                raise CoordinateFormatError(
                    f"Expected BOX BOUNDS at step {step}, found {box_header!r}."
                )
            box_rows = [_next_nonempty(iterator) for _ in range(3)]
            if selected:
                cell, origin, pbc, box_kind = _parse_box(box_header, box_rows)
            else:
                cell = origin = pbc = None
                box_kind = "discarded"

            atom_header = _next_nonempty(iterator)
            if not atom_header.startswith("ITEM: ATOMS "):
                raise CoordinateFormatError(
                    f"Expected atom table at step {step}, found {atom_header!r}."
                )
            columns = tuple(atom_header.split()[2:])
            if len(columns) != len(set(columns)):
                raise CoordinateFormatError(
                    f"Duplicate atom-table column at step {step}."
                )
            values = {column: [] for column in columns} if selected else None
            for atom_row in range(n_atoms):
                try:
                    line = _next_nonempty(iterator)
                except EOFError as exc:
                    raise CoordinateFormatError(
                        f"Unexpected end of file in atom table at step {step}."
                    ) from exc
                if not selected:
                    continue
                fields = line.split()
                if len(fields) != len(columns):
                    raise CoordinateFormatError(
                        f"Atom row {atom_row} at step {step} contains "
                        f"{len(fields)} fields; expected {len(columns)}."
                    )
                assert values is not None
                for column, value in zip(columns, fields, strict=True):
                    values[column].append(value)

            if selected:
                assert values is not None
                assert cell is not None and origin is not None and pbc is not None
                frames.append(
                    _DumpFrame(
                        step=step,
                        time=time,
                        units=frame_units,
                        cell=cell,
                        origin=origin,
                        pbc=pbc,
                        columns=columns,
                        values=values,
                        box_kind=box_kind,
                    )
                )

    if post_select:
        frames = frames[slice(start, stop, stride)]
    if not frames:
        if source_frame_count == 0:
            raise MissingPositionError(f"No LAMMPS frames found in {filename!s}.")
        raise MissingPositionError("Frame selection produced an empty trajectory.")
    return frames, source_frame_count


def _parse_lammps_log(filename: str | Path | None) -> _LogData:
    if filename is None:
        return _LogData(units=None, timestep=None, thermo={})

    with open_text_auto(filename) as handle:
        lines = handle.readlines()

    units: str | None = None
    timestep: float | None = None
    units_pattern = re.compile(r"^\s*units\s*(?:=\s*)?(\w+)\s*(?:#.*)?$", re.I)
    timestep_pattern = re.compile(
        r"^\s*timestep\s*(?:=\s*)?([-+0-9.eEdD]+)\s*(?:#.*)?$", re.I
    )
    for line in lines:
        if match := units_pattern.match(line):
            units = match.group(1).lower()
        if match := timestep_pattern.match(line):
            timestep = float(match.group(1).replace("D", "E").replace("d", "e"))

    thermo: dict[int, dict[str, float]] = {}
    index = 0
    while index < len(lines):
        header = lines[index].split()
        if not header or header[0].lower() != "step" or len(header) < 2:
            index += 1
            continue
        index += 1
        while index < len(lines):
            fields = lines[index].split()
            if len(fields) != len(header):
                break
            try:
                numbers = [
                    float(field.replace("D", "E").replace("d", "e")) for field in fields
                ]
            except ValueError:
                break
            step = int(round(numbers[0]))
            thermo[step] = {
                name.lower(): value for name, value in zip(header, numbers, strict=True)
            }
            index += 1
        index += 1

    return _LogData(units=units, timestep=timestep, thermo=thermo)


def _complete_triplet(
    columns: set[str], triplet: tuple[str, str, str], *, required: bool = False
) -> bool:
    count = sum(column in columns for column in triplet)
    if 0 < count < 3:
        raise CoordinateFormatError(
            f"Partial vector triplet present: {' '.join(triplet)}."
        )
    if required and count == 0:
        raise CoordinateFormatError(
            f"Required vector triplet absent: {' '.join(triplet)}."
        )
    return count == 3


def _float_columns(frame: _DumpFrame, names: tuple[str, str, str]) -> np.ndarray:
    try:
        return np.column_stack(
            [np.asarray(frame.values[name], dtype=np.float64) for name in names]
        )
    except ValueError as exc:
        raise CoordinateFormatError(
            f"Non-numeric value in columns {' '.join(names)} at step {frame.step}."
        ) from exc


def _resolve_coordinate_group(
    frame: _DumpFrame,
) -> tuple[str, np.ndarray, np.ndarray | None]:
    columns = set(frame.columns)
    groups = (
        ("unwrapped_fractional", ("xsu", "ysu", "zsu")),
        ("unwrapped_cartesian", ("xu", "yu", "zu")),
        ("wrapped_fractional", ("xs", "ys", "zs")),
        ("wrapped_cartesian", ("x", "y", "z")),
    )
    # Reject partial coordinate groups even when another complete group exists.
    for _, names in groups:
        _complete_triplet(columns, names)
    selected: tuple[str, tuple[str, str, str]] | None = None
    for kind, names in groups:
        if all(name in columns for name in names):
            selected = (kind, names)
            break
    if selected is None:
        raise MissingPositionError(
            f"No supported coordinate triplet at LAMMPS step {frame.step}."
        )

    image_names = ("ix", "iy", "iz")
    have_images = _complete_triplet(columns, image_names)
    images = (
        np.column_stack(
            [np.asarray(frame.values[name], dtype=np.int64) for name in image_names]
        )
        if have_images and selected[0].startswith("wrapped")
        else None
    )
    return selected[0], _float_columns(frame, selected[1]), images


def _resolve_units(
    explicit: str | None,
    dump_units: set[str],
    log_units: str | None,
) -> tuple[str, str]:
    candidates = [value for value in (explicit, log_units) if value is not None]
    candidates.extend(sorted(dump_units))
    normalized = {value.lower() for value in candidates}
    if len(normalized) > 1:
        raise UnitConversionError(
            f"Conflicting LAMMPS unit styles were supplied or detected: "
            f"{sorted(normalized)}."
        )
    if not normalized:
        raise UnitConversionError(
            "LAMMPS unit style is unknown. Supply units= or provide a log/dump "
            "that records the units command."
        )
    style = normalized.pop()
    if explicit is not None:
        source = "explicit argument"
    elif dump_units:
        source = "dump ITEM: UNITS"
    else:
        source = "LAMMPS log"
    return style, source


def _map_atomic_numbers(
    frame: _DumpFrame,
    type_map: dict[int, str | int] | None,
) -> tuple[np.ndarray, np.ndarray | None]:
    columns = set(frame.columns)
    source_types: np.ndarray | None = None
    if "type" in columns:
        source_types = np.asarray(frame.values["type"], dtype=np.int32)

    if "element" in columns:
        try:
            numbers = np.asarray(
                [symbol_to_number[symbol] for symbol in frame.values["element"]],
                dtype=np.int32,
            )
        except KeyError as exc:
            raise CoordinateFormatError(
                f"Unknown element symbol {exc.args[0]!r} at step {frame.step}."
            ) from exc
        if type_map is not None and source_types is not None:
            mapped = _numbers_from_type_ids(source_types, type_map, frame.step)
            if not np.array_equal(numbers, mapped):
                raise CoordinateFormatError(
                    f"element and type_map disagree at step {frame.step}."
                )
        return numbers, source_types

    if source_types is None:
        raise CoordinateFormatError(
            "LAMMPS atom table must contain either 'element' or 'type'."
        )
    if type_map is None:
        raise CoordinateFormatError(
            "A type_map is required because the LAMMPS dump contains numeric "
            "types but no element column."
        )
    return _numbers_from_type_ids(source_types, type_map, frame.step), source_types


def _numbers_from_type_ids(
    type_ids: np.ndarray,
    type_map: dict[int, str | int],
    step: int,
) -> np.ndarray:
    output = np.empty(type_ids.shape, dtype=np.int32)
    for index, type_id in enumerate(type_ids):
        try:
            value = type_map[int(type_id)]
        except KeyError as exc:
            raise CoordinateFormatError(
                f"No species mapping for LAMMPS type {type_id} at step {step}."
            ) from exc
        if isinstance(value, str):
            try:
                output[index] = symbol_to_number[value]
            except KeyError as exc:
                raise CoordinateFormatError(
                    f"Unknown element symbol {value!r} in type_map."
                ) from exc
        else:
            output[index] = int(value)
    return output


def _resolve_masses(
    frame: _DumpFrame,
    numbers: np.ndarray,
    source_types: np.ndarray | None,
    mass_map: dict[int, float] | None,
    conversion: UnitConversion,
) -> np.ndarray:
    if "mass" in frame.columns:
        try:
            return np.asarray(frame.values["mass"], dtype=np.float64) * conversion.mass
        except ValueError as exc:
            raise CoordinateFormatError(
                f"Non-numeric mass at step {frame.step}."
            ) from exc
    if mass_map is not None:
        if source_types is None:
            raise CoordinateFormatError(
                "mass_map requires a numeric LAMMPS type column."
            )
        try:
            return (
                np.asarray(
                    [mass_map[int(type_id)] for type_id in source_types],
                    dtype=np.float64,
                )
                * conversion.mass
            )
        except KeyError as exc:
            raise CoordinateFormatError(
                f"No mass mapping for LAMMPS type {exc.args[0]}."
            ) from exc
    return np.asarray(atomic_masses[numbers], dtype=np.float64)


def _thermo_field(
    steps: np.ndarray,
    thermo: dict[int, dict[str, float]],
    aliases: tuple[str, ...],
    *,
    strict: bool,
    name: str,
) -> np.ndarray | None:
    values: list[float | None] = []
    seen = False
    for step in steps:
        row = thermo.get(int(step), {})
        value = next((row[key] for key in aliases if key in row), None)
        seen = seen or value is not None
        values.append(value)
    if not seen:
        return None
    if any(value is None for value in values):
        message = f"Thermo field {name!r} is unavailable for some selected frames."
        if strict:
            raise IncompleteFieldError(message)
        warnings.warn(message + " Omitting the incomplete field.", stacklevel=3)
        return None
    return np.asarray(values, dtype=np.float64)


def _rotation_restricted_to_general(cell: np.ndarray) -> np.ndarray:
    """Return the orthogonal map from LAMMPS restricted to general axes.

    For row-vector cells, QR decomposition of ``cell.T`` gives
    ``cell_general = cell_restricted @ rotation.T``.  Column vectors and
    second-order tensors are therefore mapped with ``rotation``.
    """
    rotation, upper = np.linalg.qr(np.asarray(cell, dtype=np.float64).T)
    for axis in range(3):
        if upper[axis, axis] < 0.0:
            rotation[:, axis] *= -1.0
            upper[axis, :] *= -1.0
    return rotation


def read_lammps_frames(
    dump_file: str,
    *,
    log_file: str | None = None,
    units: str | None = None,
    timestep: float | None = None,
    type_map: dict[int, str | int] | None = None,
    mass_map: dict[int, float] | None = None,
    start: int | None = None,
    stop: int | None = None,
    stride: int = 1,
    reconstruct_velocities: bool = True,
    frame_semantics: FrameSemantics | str = FrameSemantics.TRAJECTORY,
    strict: bool = True,
) -> AtomisticFrameCollection:
    """Read and normalize a LAMMPS native text custom dump.

    ``frame_semantics="trajectory"`` preserves time order, unwraps coordinates,
    and reconstructs missing velocities when requested. ``"ensemble"`` treats
    selected dump frames as independent samples, wraps each frame separately,
    discards velocities, and does not require a physical timestep.

    Parameters
    ----------
    timestep
        Integration timestep in the selected LAMMPS unit style.  It is used
        only when neither ``ITEM: TIME`` nor a complete thermo ``Time`` column
        is available.
    type_map
        Mapping from numeric LAMMPS types to element symbols or atomic numbers.
        It is unnecessary when an ``element`` column is present.
    mass_map
        Optional numeric type-to-mass mapping in the LAMMPS source mass unit.
        Standard elemental masses are used otherwise.
    """
    if stride <= 0:
        raise ValueError("stride must be a positive integer.")
    semantics = coerce_frame_semantics(frame_semantics)

    frames, source_frame_count = _read_dump_frames(
        dump_file, start=start, stop=stop, stride=stride
    )

    log = _parse_lammps_log(log_file)
    dump_units = {frame.units for frame in frames if frame.units is not None}
    style, units_source = _resolve_units(units, dump_units, log.units)
    conversion = get_lammps_unit_conversion(style)

    n_atoms = len(frames[0].values[frames[0].columns[0]])
    pbc = frames[0].pbc
    coordinate_kind: str | None = None
    ids_list: list[np.ndarray] = []
    types_list: list[np.ndarray | None] = []
    numbers_list: list[np.ndarray] = []
    masses_list: list[np.ndarray] = []
    coordinate_list: list[np.ndarray] = []
    image_list: list[np.ndarray | None] = []
    velocity_list: list[np.ndarray | None] = []
    force_list: list[np.ndarray | None] = []
    cells: list[np.ndarray] = []
    origins: list[np.ndarray] = []

    for frame in frames:
        current_n = len(frame.values[frame.columns[0]])
        if current_n != n_atoms:
            raise CoordinateFormatError(
                f"Atom count changed from {n_atoms} to {current_n} at step {frame.step}."
            )
        if not np.array_equal(frame.pbc, pbc):
            raise CoordinateFormatError(
                f"Periodic-boundary flags changed at step {frame.step}."
            )
        if "id" not in frame.columns:
            raise CoordinateFormatError(
                f"LAMMPS atom IDs are required at step {frame.step}."
            )
        try:
            ids = np.asarray(frame.values["id"], dtype=np.int64)
        except ValueError as exc:
            raise CoordinateFormatError(
                f"Non-integer atom ID at step {frame.step}."
            ) from exc

        kind, coordinates, images = _resolve_coordinate_group(frame)
        if coordinate_kind is None:
            coordinate_kind = kind
        elif kind != coordinate_kind:
            raise CoordinateFormatError(
                f"Coordinate representation changed from {coordinate_kind} to "
                f"{kind} at step {frame.step}."
            )

        numbers, source_types = _map_atomic_numbers(frame, type_map)
        masses = _resolve_masses(frame, numbers, source_types, mass_map, conversion)

        columns = set(frame.columns)
        have_velocity = _complete_triplet(columns, ("vx", "vy", "vz"))
        have_force = _complete_triplet(columns, ("fx", "fy", "fz"))
        velocities = (
            _float_columns(frame, ("vx", "vy", "vz")) * conversion.velocity
            if have_velocity
            else None
        )
        forces = (
            _float_columns(frame, ("fx", "fy", "fz")) * conversion.force
            if have_force
            else None
        )

        if kind.endswith("cartesian"):
            coordinates = coordinates * conversion.length
        cells.append(frame.cell * conversion.length)
        origins.append(frame.origin * conversion.length)
        ids_list.append(ids)
        types_list.append(source_types)
        numbers_list.append(numbers)
        masses_list.append(masses)
        coordinate_list.append(coordinates)
        image_list.append(images)
        velocity_list.append(velocities)
        force_list.append(forces)

    def consolidate_optional_vectors(
        values: list[np.ndarray | None], name: str
    ) -> np.ndarray | None:
        present = [value is not None for value in values]
        if all(present):
            return np.stack([value for value in values if value is not None])
        if not any(present):
            return None
        message = f"{name} are present in only some selected LAMMPS frames."
        if strict:
            raise IncompleteFieldError(message)
        warnings.warn(message + " Omitting the incomplete field.", stacklevel=2)
        return None

    if semantics is FrameSemantics.TRAJECTORY:
        native_velocities = consolidate_optional_vectors(velocity_list, "Velocities")
        image_flags = consolidate_optional_vectors(image_list, "Image flags")
    else:
        native_velocities = (
            np.stack([value for value in velocity_list if value is not None])
            if all(value is not None for value in velocity_list)
            else None
        )
        image_flags = None
    forces = consolidate_optional_vectors(force_list, "Forces")

    steps = np.asarray([frame.step for frame in frames], dtype=np.int64)
    dump_times = [frame.time for frame in frames]
    if all(value is not None for value in dump_times):
        times = np.asarray(dump_times, dtype=np.float64) * conversion.time
        time_source = "dump ITEM: TIME"
    else:
        thermo_time = _thermo_field(
            steps, log.thermo, ("time",), strict=strict, name="Time"
        )
        if thermo_time is not None:
            times = thermo_time * conversion.time
            time_source = "LAMMPS thermo Time"
        else:
            source_timestep = timestep if timestep is not None else log.timestep
            if source_timestep is None:
                if semantics is FrameSemantics.ENSEMBLE:
                    times = None
                    time_source = "unavailable for independent ensemble"
                elif len(frames) == 1:
                    times = np.zeros(1, dtype=np.float64)
                    time_source = "single-frame default time"
                else:
                    raise MissingTimeError(
                        "Physical frame times are unavailable. Supply timestep=, "
                        "write ITEM: TIME, or provide a log with a Time column or "
                        "echoed timestep command."
                    )
            else:
                times = steps.astype(np.float64) * source_timestep * conversion.time
                time_source = (
                    "explicit timestep"
                    if timestep is not None
                    else "LAMMPS log timestep"
                )

    temperatures = _thermo_field(
        steps, log.thermo, ("temp",), strict=strict, name="temperature"
    )
    potential = _thermo_field(
        steps,
        log.thermo,
        ("poteng", "pe", "epair"),
        strict=strict,
        name="potential energy",
    )
    kinetic = _thermo_field(
        steps, log.thermo, ("kineng", "ke"), strict=strict, name="kinetic energy"
    )
    total = _thermo_field(
        steps,
        log.thermo,
        ("toteng", "etotal"),
        strict=strict,
        name="total energy",
    )
    scalar_pressure = _thermo_field(
        steps, log.thermo, ("press",), strict=strict, name="pressure"
    )
    if potential is not None:
        potential *= conversion.energy
    if kinetic is not None:
        kinetic *= conversion.energy
    if total is not None:
        total *= conversion.energy
    if scalar_pressure is not None:
        scalar_pressure *= conversion.pressure

    pressure_components = []
    for key in ("pxx", "pyy", "pzz", "pxy", "pxz", "pyz"):
        pressure_components.append(
            _thermo_field(steps, log.thermo, (key,), strict=strict, name=key)
        )
    if all(component is not None for component in pressure_components):
        pxx, pyy, pzz, pxy, pxz, pyz = pressure_components
        pressure_tensor = np.empty((len(frames), 3, 3), dtype=np.float64)
        pressure_tensor[:, 0, 0] = pxx
        pressure_tensor[:, 1, 1] = pyy
        pressure_tensor[:, 2, 2] = pzz
        pressure_tensor[:, 0, 1] = pressure_tensor[:, 1, 0] = pxy
        pressure_tensor[:, 0, 2] = pressure_tensor[:, 2, 0] = pxz
        pressure_tensor[:, 1, 2] = pressure_tensor[:, 2, 1] = pyz
        # LAMMPS reports compression-positive pressure; normalize to
        # tensile-positive continuum stress.
        stresses = -pressure_tensor * conversion.pressure
        if any(frame.box_kind == "general_triclinic" for frame in frames):
            for frame_index, frame in enumerate(frames):
                if frame.box_kind == "general_triclinic":
                    rotation = _rotation_restricted_to_general(
                        frame.cell * conversion.length
                    )
                    stresses[frame_index] = (
                        rotation @ stresses[frame_index] @ rotation.T
                    )
            stress_source = (
                "LAMMPS thermo pressure tensor rotated to general triclinic axes"
            )
        else:
            stress_source = "LAMMPS thermo pressure tensor"
    elif any(component is not None for component in pressure_components):
        message = "Only part of the LAMMPS pressure tensor is available."
        if strict:
            raise IncompleteFieldError(message)
        warnings.warn(message + " Omitting stress tensors.", stacklevel=2)
        stresses = None
        stress_source = None
    else:
        stresses = None
        stress_source = None

    # Numeric type IDs are optional when an element column is used.
    source_type_ids = (
        np.stack([value for value in types_list if value is not None])
        if all(value is not None for value in types_list)
        else None
    )

    raw = RawFrameCollection(
        frame_ids=np.arange(len(frames), dtype=np.int64),
        source_ids=np.stack(ids_list),
        source_type_ids=source_type_ids,
        atomic_numbers=np.stack(numbers_list),
        masses=np.stack(masses_list),
        steps=steps,
        times=None if times is None else np.asarray(times, dtype=np.float64),
        cells=np.stack(cells),
        origins=np.stack(origins),
        pbc=np.asarray(pbc, dtype=np.bool_),
        coordinate_kind=coordinate_kind,  # type: ignore[arg-type]
        coordinates=np.stack(coordinate_list),
        image_flags=image_flags,
        velocities=native_velocities,
        forces=forces,
        stresses=stresses,
        scalar_pressures=scalar_pressure,
        temperatures=temperatures,
        potential_energies=potential,
        kinetic_energies=kinetic,
        total_energies=total,
        source_units=style,
        metadata={
            "time_source": time_source,
            "lammps_unit_style": style,
            "source_frame_count": int(source_frame_count),
            "selected_frame_count": len(frames),
            "box_kinds": tuple(frame.box_kind for frame in frames),
        },
    )

    source_files = (dump_file,) if log_file is None else (dump_file, log_file)
    return normalize_raw_frame_collection(
        raw,
        frame_semantics=semantics,
        source_format="lammps-custom-dump",
        source_files=source_files,
        units_source=units_source,
        stress_source=stress_source,
        reconstruct_missing_velocities=reconstruct_velocities,
    )
