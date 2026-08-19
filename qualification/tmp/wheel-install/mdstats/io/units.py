"""LAMMPS-to-internal unit conversions."""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import UnitConversionError

# CODATA-compatible exact/standard conversion constants.
EV_J = 1.602176634e-19
ANGSTROM_M = 1.0e-10
AMU_KG = 1.66053906660e-27
KCAL_PER_MOL_TO_EV = 0.0433641153087705
PA_TO_EV_PER_A3 = 1.0 / 160_217_663_400.0


@dataclass(frozen=True, slots=True)
class UnitConversion:
    """Multipliers from one LAMMPS unit style to mdstats internal units."""

    length: float
    time: float
    velocity: float
    force: float
    energy: float
    pressure: float
    mass: float


_UNIT_TABLE: dict[str, UnitConversion] = {
    # Å, ps, eV, bar, g/mol.
    "metal": UnitConversion(
        length=1.0,
        time=1.0,
        velocity=1.0,
        force=1.0,
        energy=1.0,
        pressure=1.0e5 * PA_TO_EV_PER_A3,
        mass=1.0,
    ),
    # Å, fs, kcal/mol, atm, g/mol.
    "real": UnitConversion(
        length=1.0,
        time=1.0e-3,
        velocity=1.0e3,
        force=KCAL_PER_MOL_TO_EV,
        energy=KCAL_PER_MOL_TO_EV,
        pressure=101_325.0 * PA_TO_EV_PER_A3,
        mass=1.0,
    ),
    # m, s, J, Pa, kg.
    "si": UnitConversion(
        length=1.0e10,
        time=1.0e12,
        velocity=1.0e-2,
        force=(1.0 / EV_J) / 1.0e10,
        energy=1.0 / EV_J,
        pressure=PA_TO_EV_PER_A3,
        mass=1.0 / AMU_KG,
    ),
}


def get_lammps_unit_conversion(style: str) -> UnitConversion:
    """Return conversion factors for a supported LAMMPS unit style."""
    key = style.strip().lower()
    try:
        return _UNIT_TABLE[key]
    except KeyError as exc:
        supported = ", ".join(sorted(_UNIT_TABLE))
        raise UnitConversionError(
            f"Unsupported LAMMPS unit style {style!r}; supported styles: "
            f"{supported}. Reduced Lennard-Jones units are intentionally not "
            "accepted because no unique physical conversion exists."
        ) from exc
