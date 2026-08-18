"""ASE-backed readers for static structures and independent frame ensembles."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from ase import Atoms, units as ase_units
from ase.data import atomic_numbers as symbol_to_number
from ase.io import read as ase_read
from ase.io.formats import UnknownFileTypeError, filetype
from ase.stress import voigt_6_to_full_3x3_stress

from ..collection import AtomisticFrameCollection
from ..exceptions import CoordinateFormatError, IncompleteFieldError, InvalidCellError
from ..preprocess.normalize import normalize_raw_frame_collection
from ..semantics import FrameSemantics
from .common import RawFrameCollection


def _atomic_number(value: str | int) -> int:
    if isinstance(value, bool):
        raise TypeError("Boolean values are not valid atomic species.")
    if isinstance(value, str):
        try:
            return int(symbol_to_number[value])
        except KeyError as exc:
            raise ValueError(f"Unknown chemical symbol {value!r}.") from exc
    number = int(value)
    if number <= 0:
        raise ValueError("Atomic numbers must be positive.")
    return number


def _guess_structure_format(filename: str | Path, explicit: str | None) -> str | None:
    if explicit is not None:
        return explicit
    path = Path(filename)
    basename = path.name.upper()
    if basename in {"POSCAR", "CONTCAR"}:
        return "vasp"
    if path.suffix.lower() == ".cif":
        return "cif"
    if path.suffix.lower() in {".data", ".lmp", ".lammps"}:
        return "lammps-data"
    try:
        return filetype(path, read=True, guess=True)
    except (UnknownFileTypeError, OSError):
        return None


def _reader_options(
    *,
    resolved_format: str | None,
    type_map: Mapping[int, str | int] | None,
    lammps_units: str,
    atom_style: str | None,
    reader_kwargs: Mapping[str, Any] | None,
) -> dict[str, Any]:
    kwargs = dict(reader_kwargs or {})
    if resolved_format == "lammps-data":
        if type_map is not None:
            if "Z_of_type" in kwargs:
                raise ValueError(
                    "Specify either type_map or reader_kwargs['Z_of_type']."
                )
            kwargs["Z_of_type"] = {
                int(type_id): _atomic_number(species)
                for type_id, species in type_map.items()
            }
        kwargs.setdefault("units", lammps_units)
        if atom_style is not None:
            kwargs.setdefault("atom_style", atom_style)
    elif type_map is not None:
        raise ValueError("type_map is only valid for format='lammps-data'.")
    return kwargs


def _extract_optional_results(
    atoms: Atoms,
) -> tuple[np.ndarray | None, np.ndarray | None, float | None]:
    """Return stored forces, stress, and potential energy without calculating."""
    calculator = atoms.calc
    results = {} if calculator is None else getattr(calculator, "results", {})

    forces = None
    if "forces" in results:
        forces = np.asarray(results["forces"], dtype=np.float64)

    stress = None
    if "stress" in results:
        raw_stress = np.asarray(results["stress"], dtype=np.float64)
        if raw_stress.shape == (6,):
            stress = voigt_6_to_full_3x3_stress(raw_stress)
        elif raw_stress.shape == (3, 3):
            stress = raw_stress
        else:
            raise CoordinateFormatError(
                "Stored ASE stress must have shape (6,) or (3, 3); "
                f"received {raw_stress.shape}."
            )

    energy = None
    if "energy" in results:
        energy = float(results["energy"])
    elif "free_energy" in results:
        energy = float(results["free_energy"])
    return forces, stress, energy


def _consolidate_optional(
    values: list[np.ndarray | float | None],
    *,
    name: str,
    strict: bool,
) -> np.ndarray | None:
    present = [value is not None for value in values]
    if all(present):
        return np.asarray(values, dtype=np.float64)
    if not any(present):
        return None
    if strict:
        raise IncompleteFieldError(
            f"{name} is available for only some independent frames."
        )
    return None


def _validate_cell(atoms: Atoms, source: str) -> np.ndarray:
    cell = np.asarray(atoms.cell.array, dtype=np.float64)
    if cell.shape != (3, 3) or not np.all(np.isfinite(cell)):
        raise InvalidCellError(f"{source} does not define a finite 3x3 cell.")
    if abs(float(np.linalg.det(cell))) <= 1.0e-12:
        raise InvalidCellError(
            f"{source} requires a full-rank cell. Assign a simulation box "
            "before reading a nonperiodic cluster."
        )
    return cell


def _build_structure_collection(
    frames: list[Atoms],
    *,
    source_files: tuple[str | Path, ...],
    resolved_formats: tuple[str | None, ...],
    pbc: bool | Sequence[bool] | None,
    strict: bool,
    metadata: Mapping[str, Any] | None,
) -> AtomisticFrameCollection:
    if not frames:
        raise CoordinateFormatError("No structures were selected.")

    cells: list[np.ndarray] = []
    scaled_positions: list[np.ndarray] = []
    numbers: list[np.ndarray] = []
    masses: list[np.ndarray] = []
    velocities: list[np.ndarray | None] = []
    forces: list[np.ndarray | None] = []
    stresses: list[np.ndarray | None] = []
    energies: list[float | None] = []
    ids: list[np.ndarray | None] = []
    types: list[np.ndarray | None] = []

    reference_pbc: np.ndarray | None = None
    for frame_index, atoms in enumerate(frames):
        if pbc is not None:
            atoms = atoms.copy()
            atoms.set_pbc(pbc)
        current_pbc = np.asarray(atoms.pbc, dtype=np.bool_)
        if reference_pbc is None:
            reference_pbc = current_pbc
        elif not np.array_equal(current_pbc, reference_pbc):
            raise CoordinateFormatError(
                f"PBC flags differ in independent frame {frame_index}."
            )

        cells.append(_validate_cell(atoms, f"Frame {frame_index}"))
        scaled_positions.append(
            np.asarray(atoms.get_scaled_positions(wrap=False), dtype=np.float64)
        )
        numbers.append(np.asarray(atoms.numbers, dtype=np.int32))
        masses.append(np.asarray(atoms.get_masses(), dtype=np.float64))

        velocity = None
        if "momenta" in atoms.arrays:
            ase_velocity = atoms.get_velocities()
            if ase_velocity is not None:
                velocity = (
                    np.asarray(ase_velocity, dtype=np.float64)
                    * float(ase_units.fs)
                    * 1000.0
                )
        velocities.append(velocity)

        force, stress, energy = _extract_optional_results(atoms)
        forces.append(force)
        stresses.append(stress)
        energies.append(energy)
        ids.append(
            np.asarray(atoms.arrays["id"], dtype=np.int64)
            if "id" in atoms.arrays
            else None
        )
        types.append(
            np.asarray(atoms.arrays["type"], dtype=np.int32)
            if "type" in atoms.arrays
            else None
        )

    assert reference_pbc is not None

    def stack_optional_vectors(values: list[np.ndarray | None], name: str):
        result = _consolidate_optional(values, name=name, strict=strict)
        return None if result is None else np.asarray(result, dtype=np.float64)

    source_ids = _consolidate_optional(ids, name="atom IDs", strict=strict)
    if source_ids is not None:
        source_ids = np.asarray(source_ids, dtype=np.int64)
    source_types = _consolidate_optional(types, name="atom types", strict=strict)
    if source_types is not None:
        source_types = np.asarray(source_types, dtype=np.int32)

    raw = RawFrameCollection(
        source_ids=source_ids,
        source_type_ids=source_types,
        atomic_numbers=np.stack(numbers),
        masses=np.stack(masses),
        frame_ids=np.arange(len(frames), dtype=np.int64),
        steps=None,
        times=None,
        cells=np.stack(cells),
        origins=np.zeros((len(frames), 3), dtype=np.float64),
        pbc=reference_pbc,
        coordinate_kind="unwrapped_fractional",
        coordinates=np.stack(scaled_positions),
        velocities=stack_optional_vectors(velocities, "velocities"),
        forces=stack_optional_vectors(forces, "forces"),
        stresses=stack_optional_vectors(stresses, "stresses"),
        potential_energies=_consolidate_optional(
            energies, name="potential energies", strict=strict
        ),
        source_units="ASE",
        metadata={
            "static_structure": len(frames) == 1,
            "independent_frames": True,
            "ase_formats": resolved_formats,
            **dict(metadata or {}),
        },
    )

    return normalize_raw_frame_collection(
        raw,
        frame_semantics=FrameSemantics.ENSEMBLE,
        source_format=(
            "ase-structure" if len(frames) == 1 else "ase-structure-collection"
        ),
        source_files=source_files,
        units_source="ASE internal units normalized to mdstats units",
        stress_source=(
            "ASE stored calculator stress" if raw.stresses is not None else None
        ),
        reconstruct_missing_velocities=False,
    )


def read_structure(
    filename: str | Path,
    *,
    format: str | None = None,
    index: int = 0,
    type_map: Mapping[int, str | int] | None = None,
    lammps_units: str = "metal",
    atom_style: str | None = None,
    pbc: bool | Sequence[bool] | None = None,
    reader_kwargs: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> AtomisticFrameCollection:
    """Read one static structure as a one-frame independent ensemble."""
    if isinstance(index, bool) or not isinstance(index, int):
        raise TypeError("index must be an integer selecting one configuration.")
    resolved_format = _guess_structure_format(filename, format)
    kwargs = _reader_options(
        resolved_format=resolved_format,
        type_map=type_map,
        lammps_units=lammps_units,
        atom_style=atom_style,
        reader_kwargs=reader_kwargs,
    )
    atoms = ase_read(str(filename), index=index, format=resolved_format, **kwargs)
    if not isinstance(atoms, Atoms):
        raise CoordinateFormatError(
            "read_structure() must resolve to exactly one ASE Atoms object."
        )
    return _build_structure_collection(
        [atoms],
        source_files=(filename,),
        resolved_formats=(resolved_format,),
        pbc=pbc,
        strict=True,
        metadata=metadata,
    )


def read_structure_collection(
    filenames: Sequence[str | Path],
    *,
    format: str | None = None,
    indices: int | Sequence[int] = 0,
    type_map: Mapping[int, str | int] | None = None,
    lammps_units: str = "metal",
    atom_style: str | None = None,
    pbc: bool | Sequence[bool] | None = None,
    reader_kwargs: Mapping[str, Any] | None = None,
    strict: bool = True,
    metadata: Mapping[str, Any] | None = None,
) -> AtomisticFrameCollection:
    """Read one configuration from each file as an independent ensemble.

    Every selected frame must have the same atom count, canonical species order,
    masses, and PBC flags. Cells and coordinates may vary by frame. This fixed-
    population constraint is appropriate for sampled configurations of one
    physical system and for later clustering or rare-event selection.
    """
    paths = tuple(Path(path) for path in filenames)
    if not paths:
        raise ValueError("filenames must contain at least one path.")
    if isinstance(indices, (int, np.integer)) and not isinstance(indices, bool):
        selected_indices = [int(indices)] * len(paths)
    else:
        selected_indices = [int(value) for value in indices]  # type: ignore[arg-type]
        if len(selected_indices) != len(paths):
            raise ValueError("indices must have the same length as filenames.")

    frames: list[Atoms] = []
    formats: list[str | None] = []
    for path, index in zip(paths, selected_indices, strict=True):
        resolved_format = _guess_structure_format(path, format)
        kwargs = _reader_options(
            resolved_format=resolved_format,
            type_map=type_map,
            lammps_units=lammps_units,
            atom_style=atom_style,
            reader_kwargs=reader_kwargs,
        )
        atoms = ase_read(str(path), index=index, format=resolved_format, **kwargs)
        if not isinstance(atoms, Atoms):
            raise CoordinateFormatError(
                f"{path!s} index {index} did not resolve to one ASE Atoms object."
            )
        frames.append(atoms)
        formats.append(resolved_format)

    return _build_structure_collection(
        frames,
        source_files=paths,
        resolved_formats=tuple(formats),
        pbc=pbc,
        strict=strict,
        metadata=metadata,
    )
