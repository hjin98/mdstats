"""Reader for custom trajectories made from concatenated VASP MD CONTCAR files.

The individual restart records follow the VASP POSCAR/CONTCAR layout.  The
multi-record framing convention is an mdstats workflow: a watcher archives each
complete CONTCAR and zero-padded snapshots are concatenated in chronological
order.  Native Cartesian ion velocities are mandatory.  This reader never
falls back to finite-difference velocity reconstruction.

VASP format references
----------------------
- VASP Wiki, ``CONTCAR`` (https://vasp.at/wiki/CONTCAR): an MD restart
  contains structure, ion velocities, and predictor-corrector state.
- VASP Wiki, ``POSCAR`` (https://vasp.at/wiki/POSCAR): lattice/position
  scaling, optional lattice velocities, Cartesian CONTCAR velocity blocks in
  Angstrom/fs, and predictor-corrector section ordering.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, TextIO

import numpy as np
from ase.data import atomic_masses, atomic_numbers
from numpy.typing import NDArray

from ..collection import AtomisticFrameCollection
from ..exceptions import (
    InconsistentVaspRecordError,
    MissingNativeVelocityError,
    MissingPositionError,
    MissingTimeError,
    TruncatedVaspRecordError,
    VaspContcarTrajectoryError,
)
from ..preprocess.normalize import normalize_raw_frame_collection
from ..semantics import FrameSemantics
from .common import RawFrameCollection, open_text_auto


class VaspContcarTrajectoryWarning(UserWarning):
    """Warning for recoverable custom-CONTCAR trajectory inconsistencies."""


@dataclass(slots=True)
class _ContcarMDRecord:
    """One completely parsed VASP MD CONTCAR restart record."""

    comment: str
    symbols: tuple[str, ...]
    counts: NDArray[np.int64]
    cell: NDArray[np.float64]
    fractional_positions: NDArray[np.float64]
    velocities_angstrom_per_ps: NDArray[np.float64]
    coordinate_mode: str
    selective_dynamics: bool
    lattice_velocity_block_present: bool
    predictor_initialization_state: int
    embedded_potim_fs: float
    predictor_array_count: int


class _LineReader:
    """Line-numbered text reader with section-aware diagnostics."""

    def __init__(self, handle: TextIO, source: str | Path) -> None:
        self.handle = handle
        self.source = str(source)
        self.line_number = 0

    def read_optional(self) -> str | None:
        line = self.handle.readline()
        if line == "":
            return None
        self.line_number += 1
        return line.rstrip("\r\n")

    def read_required(self, *, record_index: int, section: str) -> str:
        line = self.read_optional()
        if line is None:
            raise TruncatedVaspRecordError(
                self.message(
                    record_index,
                    section,
                    "reached end of file before the record was complete",
                    line_number=self.line_number + 1,
                )
            )
        return line

    def message(
        self,
        record_index: int,
        section: str,
        detail: str,
        *,
        line_number: int | None = None,
    ) -> str:
        line = self.line_number if line_number is None else line_number
        return (
            f"{self.source} record {record_index + 1}, line {line}: "
            f"{section}: {detail}."
        )


def _float_token(token: str) -> float:
    return float(token.replace("D", "E").replace("d", "e"))


def _parse_floats(
    line: str,
    *,
    count: int | None,
    minimum: int | None,
    reader: _LineReader,
    record_index: int,
    section: str,
) -> NDArray[np.float64]:
    tokens = line.split()
    if count is not None and len(tokens) != count:
        raise VaspContcarTrajectoryError(
            reader.message(
                record_index,
                section,
                f"expected {count} numeric values, observed {len(tokens)}",
            )
        )
    if minimum is not None and len(tokens) < minimum:
        raise VaspContcarTrajectoryError(
            reader.message(
                record_index,
                section,
                f"expected at least {minimum} numeric values, observed {len(tokens)}",
            )
        )
    try:
        values = np.asarray([_float_token(token) for token in tokens], dtype=np.float64)
    except ValueError as exc:
        raise VaspContcarTrajectoryError(
            reader.message(record_index, section, "encountered a nonnumeric value")
        ) from exc
    if not np.all(np.isfinite(values)):
        raise VaspContcarTrajectoryError(
            reader.message(record_index, section, "encountered a non-finite value")
        )
    return values


def _parse_ints(
    line: str,
    *,
    reader: _LineReader,
    record_index: int,
    section: str,
) -> NDArray[np.int64]:
    tokens = line.split()
    if not tokens:
        raise VaspContcarTrajectoryError(
            reader.message(record_index, section, "expected one or more integers")
        )
    try:
        values = np.asarray([int(token) for token in tokens], dtype=np.int64)
    except ValueError as exc:
        raise VaspContcarTrajectoryError(
            reader.message(record_index, section, "encountered a non-integer value")
        ) from exc
    return values


def _parse_vector(
    line: str,
    *,
    reader: _LineReader,
    record_index: int,
    section: str,
) -> NDArray[np.float64]:
    tokens = line.split()
    if len(tokens) < 3:
        raise VaspContcarTrajectoryError(
            reader.message(
                record_index,
                section,
                f"expected at least 3 numeric values, observed {len(tokens)}",
            )
        )
    try:
        values = np.asarray(
            [_float_token(token) for token in tokens[:3]], dtype=np.float64
        )
    except ValueError as exc:
        raise VaspContcarTrajectoryError(
            reader.message(record_index, section, "encountered a nonnumeric vector")
        ) from exc
    if not np.all(np.isfinite(values)):
        raise VaspContcarTrajectoryError(
            reader.message(record_index, section, "encountered a non-finite vector")
        )
    return values


def _parse_scale_and_cell(
    reader: _LineReader,
    *,
    record_index: int,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    scale_line = reader.read_required(record_index=record_index, section="scale")
    scale_values = _parse_floats(
        scale_line,
        count=None,
        minimum=1,
        reader=reader,
        record_index=record_index,
        section="scale",
    )
    if scale_values.size not in {1, 3}:
        raise VaspContcarTrajectoryError(
            reader.message(
                record_index,
                "scale",
                "expected one universal scale or three Cartesian component scales",
            )
        )

    raw_cell = np.stack(
        [
            _parse_vector(
                reader.read_required(
                    record_index=record_index, section=f"lattice vector {axis + 1}"
                ),
                reader=reader,
                record_index=record_index,
                section=f"lattice vector {axis + 1}",
            )
            for axis in range(3)
        ]
    )
    raw_volume = float(abs(np.linalg.det(raw_cell)))
    if not np.isfinite(raw_volume) or raw_volume <= 0.0:
        raise VaspContcarTrajectoryError(
            reader.message(record_index, "lattice", "cell is singular or malformed")
        )

    if scale_values.size == 1:
        scale = float(scale_values[0])
        if scale == 0.0:
            raise VaspContcarTrajectoryError(
                reader.message(record_index, "scale", "universal scale cannot be zero")
            )
        if scale < 0.0:
            uniform = (abs(scale) / raw_volume) ** (1.0 / 3.0)
        else:
            uniform = scale
        cartesian_scale = np.full(3, uniform, dtype=np.float64)
    else:
        if np.any(scale_values <= 0.0):
            raise VaspContcarTrajectoryError(
                reader.message(
                    record_index,
                    "scale",
                    "three Cartesian component scales must all be positive",
                )
            )
        cartesian_scale = np.asarray(scale_values, dtype=np.float64)

    cell = raw_cell * cartesian_scale[None, :]
    volume = float(abs(np.linalg.det(cell)))
    if not np.isfinite(volume) or volume <= 0.0:
        raise VaspContcarTrajectoryError(
            reader.message(record_index, "lattice", "scaled cell is singular")
        )
    return cell, cartesian_scale


def _parse_symbols_counts_and_positions(
    reader: _LineReader,
    *,
    record_index: int,
    cell: NDArray[np.float64],
    cartesian_scale: NDArray[np.float64],
) -> tuple[
    tuple[str, ...],
    NDArray[np.int64],
    NDArray[np.float64],
    str,
    bool,
]:
    species_line = reader.read_required(record_index=record_index, section="species names")
    species_tokens = species_line.split()
    if not species_tokens:
        raise VaspContcarTrajectoryError(
            reader.message(record_index, "species names", "line is empty")
        )
    try:
        [int(token) for token in species_tokens]
    except ValueError:
        pass
    else:
        raise VaspContcarTrajectoryError(
            reader.message(
                record_index,
                "species names",
                "VASP-4 counts-only records are unsupported; explicit species names are required",
            )
        )

    symbols: list[str] = []
    for token in species_tokens:
        symbol = token[0].upper() + token[1:].lower()
        if symbol not in atomic_numbers or atomic_numbers[symbol] <= 0:
            raise VaspContcarTrajectoryError(
                reader.message(
                    record_index,
                    "species names",
                    f"unknown chemical symbol {token!r}",
                )
            )
        symbols.append(symbol)

    counts_line = reader.read_required(record_index=record_index, section="species counts")
    counts = _parse_ints(
        counts_line,
        reader=reader,
        record_index=record_index,
        section="species counts",
    )
    if counts.size != len(symbols):
        raise VaspContcarTrajectoryError(
            reader.message(
                record_index,
                "species counts",
                "number of counts does not match number of species names",
            )
        )
    if np.any(counts <= 0):
        raise VaspContcarTrajectoryError(
            reader.message(record_index, "species counts", "all counts must be positive")
        )
    n_atoms = int(np.sum(counts))

    mode_line = reader.read_required(
        record_index=record_index, section="position coordinate mode"
    )
    selective = mode_line.lstrip().lower().startswith("s")
    if selective:
        mode_line = reader.read_required(
            record_index=record_index, section="position coordinate mode"
        )
    stripped_mode = mode_line.lstrip()
    if not stripped_mode:
        raise VaspContcarTrajectoryError(
            reader.message(record_index, "position coordinate mode", "line is empty")
        )
    cartesian = stripped_mode[0] in "CcKk"
    coordinate_mode = "cartesian" if cartesian else "direct"

    coordinates = np.empty((n_atoms, 3), dtype=np.float64)
    for atom_index in range(n_atoms):
        line = reader.read_required(
            record_index=record_index,
            section=f"position {atom_index + 1} of {n_atoms}",
        )
        tokens = line.split()
        minimum = 6 if selective else 3
        if len(tokens) < minimum:
            raise VaspContcarTrajectoryError(
                reader.message(
                    record_index,
                    f"position {atom_index + 1} of {n_atoms}",
                    f"expected at least {minimum} fields, observed {len(tokens)}",
                )
            )
        coordinates[atom_index] = _parse_vector(
            line,
            reader=reader,
            record_index=record_index,
            section=f"position {atom_index + 1} of {n_atoms}",
        )
        if selective:
            flags = [token.upper() for token in tokens[3:6]]
            if any(flag not in {"T", "F"} for flag in flags):
                raise VaspContcarTrajectoryError(
                    reader.message(
                        record_index,
                        f"position {atom_index + 1} of {n_atoms}",
                        "selective-dynamics flags must be T or F",
                    )
                )

    if cartesian:
        cartesian_positions = coordinates * cartesian_scale[None, :]
        try:
            inverse_cell = np.linalg.inv(cell)
        except np.linalg.LinAlgError as exc:  # defensive; checked above
            raise VaspContcarTrajectoryError(
                reader.message(record_index, "lattice", "cell cannot be inverted")
            ) from exc
        fractional = cartesian_positions @ inverse_cell
    else:
        fractional = coordinates

    return tuple(symbols), counts, fractional, coordinate_mode, selective


def _parse_lattice_velocity_block(
    reader: _LineReader,
    *,
    record_index: int,
) -> None:
    initialization = reader.read_required(
        record_index=record_index, section="lattice-velocity initialization state"
    )
    values = _parse_ints(
        initialization,
        reader=reader,
        record_index=record_index,
        section="lattice-velocity initialization state",
    )
    if values.size != 1:
        raise VaspContcarTrajectoryError(
            reader.message(
                record_index,
                "lattice-velocity initialization state",
                "expected exactly one integer",
            )
        )
    for axis in range(3):
        _parse_vector(
            reader.read_required(
                record_index=record_index,
                section=f"lattice velocity {axis + 1} of 3",
            ),
            reader=reader,
            record_index=record_index,
            section=f"lattice velocity {axis + 1} of 3",
        )
    for axis in range(3):
        _parse_vector(
            reader.read_required(
                record_index=record_index,
                section=f"repeated lattice vector {axis + 1} of 3",
            ),
            reader=reader,
            record_index=record_index,
            section=f"repeated lattice vector {axis + 1} of 3",
        )


def _parse_native_velocity_block(
    reader: _LineReader,
    *,
    record_index: int,
    n_atoms: int,
    mode_line: str,
) -> NDArray[np.float64]:
    stripped = mode_line.lstrip()
    is_cartesian = not stripped or stripped[0] in "CcKk"
    if not is_cartesian:
        raise MissingNativeVelocityError(
            reader.message(
                record_index,
                "ionic velocity mode",
                "only the native Cartesian CONTCAR velocity block is supported",
            )
        )

    velocities = np.empty((n_atoms, 3), dtype=np.float64)
    for atom_index in range(n_atoms):
        line = reader.read_required(
            record_index=record_index,
            section=f"ionic velocity {atom_index + 1} of {n_atoms}",
        )
        try:
            velocities[atom_index] = _parse_vector(
                line,
                reader=reader,
                record_index=record_index,
                section=f"ionic velocity {atom_index + 1} of {n_atoms}",
            )
        except VaspContcarTrajectoryError as exc:
            raise MissingNativeVelocityError(str(exc)) from exc

    # VASP writes Cartesian CONTCAR velocities in Angstrom/fs.  mdstats stores
    # Cartesian velocities in Angstrom/ps, so the exact unit conversion is 1000.
    return velocities * 1.0e3


def _parse_predictor_corrector_block(
    reader: _LineReader,
    *,
    record_index: int,
    n_atoms: int,
) -> tuple[int, float, int]:
    separator = reader.read_required(
        record_index=record_index, section="predictor-corrector separator"
    )
    if separator.strip():
        raise TruncatedVaspRecordError(
            reader.message(
                record_index,
                "predictor-corrector separator",
                "expected a blank line after the ionic velocity block",
            )
        )

    initialization_line = reader.read_required(
        record_index=record_index, section="predictor-corrector initialization state"
    )
    initialization_values = _parse_ints(
        initialization_line,
        reader=reader,
        record_index=record_index,
        section="predictor-corrector initialization state",
    )
    if initialization_values.size != 1:
        raise VaspContcarTrajectoryError(
            reader.message(
                record_index,
                "predictor-corrector initialization state",
                "expected exactly one integer",
            )
        )
    initialization_state = int(initialization_values[0])

    potim_line = reader.read_required(
        record_index=record_index, section="embedded POTIM"
    )
    potim_values = _parse_floats(
        potim_line,
        count=1,
        minimum=None,
        reader=reader,
        record_index=record_index,
        section="embedded POTIM",
    )
    potim_fs = float(potim_values[0])
    if potim_fs <= 0.0:
        raise VaspContcarTrajectoryError(
            reader.message(record_index, "embedded POTIM", "value must be positive")
        )

    thermostat_line = reader.read_required(
        record_index=record_index, section="predictor-corrector thermostat state"
    )
    _parse_floats(
        thermostat_line,
        count=4,
        minimum=None,
        reader=reader,
        record_index=record_index,
        section="predictor-corrector thermostat state",
    )

    # The watcher-defined format is intentionally narrow: it concatenates the
    # complete VASP MD restart records observed in the supplied data, whose
    # predictor section contains three N x 3 arrays.  They are validated and
    # consumed for framing but are not exposed as forces or accelerations.
    predictor_array_count = 3
    for array_index in range(predictor_array_count):
        for atom_index in range(n_atoms):
            _parse_vector(
                reader.read_required(
                    record_index=record_index,
                    section=(
                        f"predictor array {array_index + 1} of 3, "
                        f"atom {atom_index + 1} of {n_atoms}"
                    ),
                ),
                reader=reader,
                record_index=record_index,
                section=(
                    f"predictor array {array_index + 1} of 3, "
                    f"atom {atom_index + 1} of {n_atoms}"
                ),
            )
    return initialization_state, potim_fs, predictor_array_count


def _parse_record(
    reader: _LineReader,
    *,
    record_index: int,
    comment: str,
) -> _ContcarMDRecord:
    cell, cartesian_scale = _parse_scale_and_cell(reader, record_index=record_index)
    symbols, counts, positions, coordinate_mode, selective = (
        _parse_symbols_counts_and_positions(
            reader,
            record_index=record_index,
            cell=cell,
            cartesian_scale=cartesian_scale,
        )
    )
    n_atoms = int(np.sum(counts))

    velocity_mode_line = reader.read_required(
        record_index=record_index, section="ionic velocity mode"
    )
    lattice_velocity_present = velocity_mode_line.lstrip().lower().startswith("l")
    if lattice_velocity_present:
        _parse_lattice_velocity_block(reader, record_index=record_index)
        velocity_mode_line = reader.read_required(
            record_index=record_index, section="ionic velocity mode"
        )

    velocities = _parse_native_velocity_block(
        reader,
        record_index=record_index,
        n_atoms=n_atoms,
        mode_line=velocity_mode_line,
    )
    initialization, potim_fs, predictor_array_count = _parse_predictor_corrector_block(
        reader,
        record_index=record_index,
        n_atoms=n_atoms,
    )
    return _ContcarMDRecord(
        comment=comment,
        symbols=symbols,
        counts=counts,
        cell=cell,
        fractional_positions=positions,
        velocities_angstrom_per_ps=velocities,
        coordinate_mode=coordinate_mode,
        selective_dynamics=selective,
        lattice_velocity_block_present=lattice_velocity_present,
        predictor_initialization_state=initialization,
        embedded_potim_fs=potim_fs,
        predictor_array_count=predictor_array_count,
    )


def _iter_contcar_trajectory_records(
    handle: TextIO,
    *,
    source: str | Path,
):
    reader = _LineReader(handle, source)
    record_index = 0
    while True:
        comment = reader.read_optional()
        if comment is None:
            return
        yield _parse_record(reader, record_index=record_index, comment=comment)
        record_index += 1


def _resolve_masses(
    symbols: tuple[str, ...],
    counts: NDArray[np.int64],
    mass_map: Mapping[str, float] | None,
) -> tuple[NDArray[np.float64], str]:
    normalized_map: dict[str, float] = {}
    if mass_map is not None:
        for key, value in mass_map.items():
            symbol = str(key)
            symbol = symbol[0].upper() + symbol[1:].lower()
            mass = float(value)
            if symbol not in atomic_numbers or not np.isfinite(mass) or mass <= 0.0:
                raise ValueError(
                    "mass_map keys must be valid element symbols and values must "
                    "be finite positive masses in atomic mass units."
                )
            normalized_map[symbol] = mass

    per_species: list[float] = []
    overridden_symbols: set[str] = set()
    for symbol in symbols:
        if symbol in normalized_map:
            per_species.append(normalized_map[symbol])
            overridden_symbols.add(symbol)
        else:
            per_species.append(float(atomic_masses[atomic_numbers[symbol]]))
    masses = np.concatenate(
        [np.full(int(count), mass, dtype=np.float64) for count, mass in zip(counts, per_species, strict=True)]
    )
    if mass_map is None:
        source = "ASE standard atomic masses"
    elif overridden_symbols == set(symbols):
        source = "explicit mass_map"
    else:
        source = "explicit mass_map with ASE fallback"
    return masses, source


def read_vasp_contcar_trajectory(
    filename: str | Path,
    *,
    start: int | None,
    stop: int | None,
    stride: int,
    timestep_fs: float | None,
    strict: bool,
    mass_map: Mapping[str, float] | None,
) -> AtomisticFrameCollection:
    """Read the watcher-generated concatenated VASP MD CONTCAR format."""
    if timestep_fs is None:
        raise MissingTimeError(
            "vasp-contcar-trajectory has no authoritative saved-frame time axis. "
            "Supply timestep_fs explicitly."
        )
    timestep = float(timestep_fs)
    if not np.isfinite(timestep) or timestep <= 0.0:
        raise MissingTimeError("timestep_fs must be finite and positive.")
    if isinstance(stride, bool) or not isinstance(stride, int) or stride <= 0:
        raise ValueError("stride must be a positive integer.")
    start_index = 0 if start is None else start
    if isinstance(start_index, bool) or not isinstance(start_index, int) or start_index < 0:
        raise ValueError("start must be a nonnegative integer or None.")
    if stop is not None and (
        isinstance(stop, bool) or not isinstance(stop, int) or stop < 0
    ):
        raise ValueError("stop must be a nonnegative integer or None.")
    if stop is not None and stop <= start_index:
        raise MissingPositionError("Frame selection produced an empty trajectory.")

    selected: list[_ContcarMDRecord] = []
    selected_indices: list[int] = []
    reference_symbols: tuple[str, ...] | None = None
    reference_counts: NDArray[np.int64] | None = None
    embedded_potim: list[float] = []
    source_count = 0

    with open_text_auto(filename) as handle:
        for source_index, record in enumerate(
            _iter_contcar_trajectory_records(handle, source=filename)
        ):
            source_count += 1
            if reference_symbols is None:
                reference_symbols = record.symbols
                reference_counts = record.counts.copy()
            elif record.symbols != reference_symbols or not np.array_equal(
                record.counts, reference_counts
            ):
                raise InconsistentVaspRecordError(
                    f"{filename!s} record {source_index + 1}: species names, counts, "
                    "or atom ordering changed across records."
                )
            embedded_potim.append(record.embedded_potim_fs)
            if source_index >= start_index and (
                stop is None or source_index < stop
            ) and (source_index - start_index) % stride == 0:
                selected.append(record)
                selected_indices.append(source_index)

    if source_count == 0:
        raise MissingPositionError(f"No CONTCAR records found in {filename!s}.")
    if not selected:
        raise MissingPositionError("Frame selection produced an empty trajectory.")
    assert reference_symbols is not None
    assert reference_counts is not None

    potim_array = np.asarray(embedded_potim, dtype=np.float64)
    reference_potim = float(potim_array[0])
    potim_constant = bool(
        np.allclose(potim_array, reference_potim, rtol=1.0e-12, atol=1.0e-12)
    )
    if not potim_constant:
        message = "Embedded POTIM changes across concatenated CONTCAR records"
        if strict:
            raise InconsistentVaspRecordError(message + ".")
        warnings.warn(message + ".", VaspContcarTrajectoryWarning, stacklevel=2)

    ratio = timestep / reference_potim
    nearest_stride = int(round(ratio))
    implied_save_stride: int | None
    if nearest_stride >= 1 and np.isclose(ratio, nearest_stride, rtol=1.0e-8, atol=1.0e-10):
        implied_save_stride = nearest_stride
    else:
        implied_save_stride = None
        warnings.warn(
            "timestep_fs is not an integer multiple of the embedded POTIM. "
            "The explicit saved-frame timestep remains authoritative.",
            VaspContcarTrajectoryWarning,
            stacklevel=2,
        )

    symbols_per_atom = tuple(
        symbol
        for symbol, count in zip(reference_symbols, reference_counts, strict=True)
        for _ in range(int(count))
    )
    numbers = np.asarray([atomic_numbers[symbol] for symbol in symbols_per_atom], dtype=np.int32)
    masses, mass_source = _resolve_masses(reference_symbols, reference_counts, mass_map)
    n_frames = len(selected)

    raw = RawFrameCollection(
        frame_ids=np.arange(n_frames, dtype=np.int64),
        source_ids=None,
        source_type_ids=None,
        atomic_numbers=np.broadcast_to(numbers, (n_frames, numbers.size)).copy(),
        masses=np.broadcast_to(masses, (n_frames, masses.size)).copy(),
        steps=None,
        times=np.asarray(selected_indices, dtype=np.float64) * timestep * 1.0e-3,
        cells=np.stack([record.cell for record in selected]),
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        pbc=np.ones(3, dtype=np.bool_),
        coordinate_kind="wrapped_fractional",
        coordinates=np.stack([record.fractional_positions for record in selected]),
        image_flags=None,
        velocities=np.stack(
            [record.velocities_angstrom_per_ps for record in selected]
        ),
        forces=None,
        stresses=None,
        scalar_pressures=None,
        temperatures=None,
        potential_energies=None,
        kinetic_energies=None,
        total_energies=None,
        source_units="VASP CONTCAR: Angstrom, Angstrom/fs, fs",
        metadata={
            "vasp_input_format": "vasp-contcar-trajectory",
            "custom_format": True,
            "creation_workflow": "watch complete CONTCAR snapshots, then concatenate zero-padded files",
            "source_frame_count": source_count,
            "selected_frame_count": n_frames,
            "selected_source_record_indices": tuple(selected_indices),
            "saved_frame_timestep_fs": timestep,
            "time_source": "explicit timestep_fs",
            "time_origin": "first CONTCAR record in concatenated stream",
            "source_step_labels_available": False,
            "velocity_block_required": True,
            "velocity_units_in_file": "angstrom/fs",
            "velocity_conversion_to_internal": 1000.0,
            "predictor_corrector_present": True,
            "predictor_array_count": 3,
            "embedded_potim_fs": reference_potim,
            "embedded_potim_constant": potim_constant,
            "implied_save_stride": implied_save_stride,
            "lattice_velocity_block_present": any(
                record.lattice_velocity_block_present for record in selected
            ),
            "selective_dynamics_present": any(
                record.selective_dynamics for record in selected
            ),
            "position_coordinate_modes": tuple(
                sorted({record.coordinate_mode for record in selected})
            ),
            "mass_source": mass_source,
            "species_names": reference_symbols,
            "species_counts": tuple(int(value) for value in reference_counts),
        },
    )

    # Native velocities are mandatory for this source.  Disabling reconstruction
    # here is an invariant, not a user preference, so malformed data can never be
    # converted into a seemingly valid finite-difference VACF input.
    return normalize_raw_frame_collection(
        raw,
        frame_semantics=FrameSemantics.TRAJECTORY,
        source_format="vasp-contcar-trajectory",
        source_files=(filename,),
        units_source="VASP CONTCAR: Angstrom, Angstrom/fs converted to Angstrom/ps, fs",
        stress_source=None,
        reconstruct_missing_velocities=False,
    )
