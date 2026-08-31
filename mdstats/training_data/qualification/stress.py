"""Canonical stress conversion for qualification evidence.

Stress is an optional product capability, but when it is present it must have
one unambiguous identity.  This module is the narrow conversion owner used by
provider, reference, and deployed-runtime adapters: tensors are stored as a
symmetric ``xx, xy, xz / xy, yy, yz / xz, yz, zz`` matrix in
``eV/A^3``.  Thermodynamic pressure values (for example LAMMPS ``bar``) are
already intensive and are converted directly; an extensive virial is converted
by :func:`canonical_stress_from_virial`, which requires the instantaneous
periodic-cell volume.  The sign argument is explicit because calculator virial
and thermodynamic stress conventions are not universal.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from .errors import QualificationError

EV_PER_ANGSTROM3_TO_GPA = 160.21766208
BAR_TO_GPA = 1.0e-4
CANONICAL_STRESS_UNITS = "ev_per_angstrom3"
CANONICAL_VOIGT_ORDER = ("xx", "yy", "zz", "xy", "yz", "xz")
INSTANTANEOUS_CELL_VOLUME_SOURCE = "instantaneous_periodic_cell"

#: LAMMPS thermo pressure under ``units metal`` is reported in bar.  This is a
#: property of the source, not of any output preference, so it is fixed here
#: rather than passed in by a caller who could get it wrong.
LAMMPS_METAL_PRESSURE_UNITS = "bar"

#: LAMMPS thermo pressure is positive in compression; the canonical ASE/MACE
#: Cauchy stress this evidence contract uses is positive in tension.  The
#: conversion between them is a fact about those two conventions, so it is
#: fixed here and is deliberately not an operator-tunable default.
LAMMPS_PRESSURE_TO_CANONICAL_STRESS_SIGN = -1.0

#: The named component order LAMMPS thermo exposes for the pressure tensor.
LAMMPS_PRESSURE_COMPONENTS = ("pxx", "pyy", "pzz", "pxy", "pyz", "pxz")


def normalize_stress_units(units: str) -> str:
    """Normalize the finite set of supported stress-unit spellings."""

    unit_name = str(units).strip().lower().replace(" ", "")
    if unit_name in {
        CANONICAL_STRESS_UNITS,
        "ev/angstrom^3",
        "ev/angstrom3",
        "ev/a^3",
        "ev/a3",
    }:
        return CANONICAL_STRESS_UNITS
    if unit_name in {"gpa", "gigapascal", "gigapascals"}:
        return "gpa"
    if unit_name in {"bar", "bars"}:
        return "bar"
    raise QualificationError(
        f"Unsupported stress units {units!r}; expected {CANONICAL_STRESS_UNITS!r}, GPa, or bar."
    )


def canonical_stress_tensor(
    value: Any,
    *,
    units: str = CANONICAL_STRESS_UNITS,
    voigt_order: Sequence[str] = CANONICAL_VOIGT_ORDER,
    sign: float = 1.0,
) -> np.ndarray:
    """Return one finite canonical 3x3 stress tensor.

    Accepted inputs are a 3x3 tensor or a six-component Voigt vector.  The
    conversion is deliberately strict: callers must name noncanonical units
    and ordering rather than silently relying on a calculator default.
    """

    raw = np.asarray(value, dtype=np.float64)
    if raw.shape == (3, 3):
        tensor = raw.copy()
        # Stress is symmetric in this evidence contract.  Rejecting rather
        # than averaging preserves a provider's ordering/convention mistake.
        if not np.allclose(tensor, tensor.T, rtol=0.0, atol=1.0e-12):
            raise QualificationError("Stress tensor must be symmetric in the canonical contract.")
    elif raw.shape == (6,):
        order = tuple(str(item).lower() for item in voigt_order)
        if set(order) != set(CANONICAL_VOIGT_ORDER) or len(order) != 6:
            raise QualificationError(
                "Stress Voigt order must contain xx, yy, zz, xy, yz, and xz exactly once."
            )
        values = {name: float(raw[index]) for index, name in enumerate(order)}
        tensor = np.array(
            [
                [values["xx"], values["xy"], values["xz"]],
                [values["xy"], values["yy"], values["yz"]],
                [values["xz"], values["yz"], values["zz"]],
            ],
            dtype=np.float64,
        )
    else:
        raise QualificationError("Stress must be a 3x3 tensor or six-component Voigt vector.")
    if not np.all(np.isfinite(tensor)):
        raise QualificationError("Stress must contain only finite values.")
    unit_name = normalize_stress_units(units)
    if unit_name == CANONICAL_STRESS_UNITS:
        factor = 1.0
    elif unit_name == "gpa":
        factor = 1.0 / EV_PER_ANGSTROM3_TO_GPA
    elif unit_name == "bar":
        factor = BAR_TO_GPA / EV_PER_ANGSTROM3_TO_GPA
    sign_value = float(sign)
    if not np.isfinite(sign_value) or sign_value == 0.0:
        raise QualificationError("Stress sign must be finite and nonzero.")
    return np.asarray(tensor * factor * sign_value, dtype=np.float64)


def canonical_stress_from_lammps_metal_pressure(
    components: Any,
    *,
    voigt_order: Sequence[str] = CANONICAL_VOIGT_ORDER,
) -> np.ndarray:
    """Convert LAMMPS ``units metal`` thermo pressure to canonical stress.

    This is the one place the LAMMPS source convention is stated, because both
    halves of it are facts about LAMMPS rather than choices: the thermo values
    are pressure in **bar**, and pressure is positive in compression while the
    canonical ASE/MACE Cauchy stress used throughout this evidence contract is
    positive in tension.  Passing those numbers through the generic converter
    with caller-supplied units and sign is exactly how a factor-10,000 unit
    error and an inverted sign get in, so no caller is offered that choice.
    """

    return canonical_stress_tensor(
        np.asarray(components, dtype=np.float64),
        units=LAMMPS_METAL_PRESSURE_UNITS,
        voigt_order=voigt_order,
        sign=LAMMPS_PRESSURE_TO_CANONICAL_STRESS_SIGN,
    )


def canonical_stress_from_virial(
    virial: Any,
    *,
    volume_angstrom3: float,
    virial_units: str = "ev",
    voigt_order: Sequence[str] = CANONICAL_VOIGT_ORDER,
    sign: float = 1.0,
) -> np.ndarray:
    """Convert an extensive virial to the canonical intensive stress tensor.

    ``volume_angstrom3`` is deliberately mandatory: a virial without the
    instantaneous cell volume cannot be compared between strained or changing
    cells.  Virials are currently accepted in eV, while their tensor shape,
    ordering, finiteness, and sign are checked by the common tensor owner.
    """

    volume = float(volume_angstrom3)
    if not np.isfinite(volume) or volume <= 0.0:
        raise QualificationError("Stress conversion requires a finite positive cell volume.")
    unit_name = str(virial_units).strip().lower()
    if unit_name not in {"ev", "electronvolt", "electronvolts"}:
        raise QualificationError(
            f"Unsupported virial units {virial_units!r}; expected eV."
        )
    return canonical_stress_tensor(
        np.asarray(virial, dtype=np.float64) / volume,
        units=CANONICAL_STRESS_UNITS,
        voigt_order=voigt_order,
        sign=sign,
    )


def stress_of(prediction: Any) -> np.ndarray | None:
    """Extract an already-canonical stress tensor from a provider prediction."""

    value = getattr(prediction, "stress_ev_per_angstrom3", None)
    if value is None:
        return None
    return canonical_stress_tensor(value)


__all__ = [
    "BAR_TO_GPA",
    "LAMMPS_METAL_PRESSURE_UNITS",
    "LAMMPS_PRESSURE_COMPONENTS",
    "LAMMPS_PRESSURE_TO_CANONICAL_STRESS_SIGN",
    "CANONICAL_STRESS_UNITS",
    "CANONICAL_VOIGT_ORDER",
    "EV_PER_ANGSTROM3_TO_GPA",
    "INSTANTANEOUS_CELL_VOLUME_SOURCE",
    "canonical_stress_from_lammps_metal_pressure",
    "canonical_stress_from_virial",
    "canonical_stress_tensor",
    "normalize_stress_units",
    "stress_of",
]
