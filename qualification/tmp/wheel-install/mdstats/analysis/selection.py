"""Atom-selection utilities shared by trajectory-analysis modules."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from ase.data import atomic_numbers as ase_atomic_numbers
from numpy.typing import ArrayLike, NDArray

IntArray = NDArray[np.int64]
Species = str | int
SpeciesSelection = Species | Sequence[Species] | None


def _atomic_number(value: Species) -> int:
    """Convert an element symbol or atomic number to a validated integer."""
    if isinstance(value, (bool, np.bool_)):
        raise ValueError("Boolean values are not valid atomic species.")

    if isinstance(value, str):
        symbol = value.strip()
        if symbol not in ase_atomic_numbers:
            raise ValueError(f"Unknown chemical symbol: {value!r}.")
        return int(ase_atomic_numbers[symbol])

    if isinstance(value, (int, np.integer)):
        number = int(value)
        if number < 1 or number > 118:
            raise ValueError(
                f"Atomic number {number} is outside the supported range 1..118."
            )
        return number

    raise TypeError(
        "Species entries must be chemical symbols or integer atomic numbers; "
        f"received {type(value).__name__}."
    )


def resolve_atom_selection(
    atomic_numbers: NDArray[np.integer],
    *,
    species: SpeciesSelection = None,
    atom_indices: ArrayLike | None = None,
    selection_name: str = "atom",
) -> IntArray:
    """Resolve a species or explicit-index selection to canonical atom indices.

    Parameters
    ----------
    atomic_numbers
        One-dimensional atomic-number array in canonical trajectory order.
    species
        One symbol/atomic number or a sequence of symbols/atomic numbers.
    atom_indices
        One-dimensional integer indices or a Boolean mask of length ``N``.
    selection_name
        Label used in diagnostic messages.

    Returns
    -------
    numpy.ndarray
        A one-dimensional ``int64`` array of selected canonical indices.

    Notes
    -----
    ``species`` and ``atom_indices`` are mutually exclusive. Explicit integer
    indices preserve user order; species selections return canonical order.
    """
    numbers = np.asarray(atomic_numbers)
    if numbers.ndim != 1:
        raise ValueError("atomic_numbers must be a one-dimensional array.")
    n_atoms = int(numbers.size)

    if species is not None and atom_indices is not None:
        raise ValueError(
            f"{selection_name}_species and {selection_name}_indices are "
            "mutually exclusive."
        )

    if atom_indices is not None:
        raw = np.asarray(atom_indices)
        if raw.ndim != 1:
            raise ValueError(f"{selection_name}_indices must be one-dimensional.")

        if np.issubdtype(raw.dtype, np.bool_):
            if raw.shape != (n_atoms,):
                raise ValueError(
                    f"Boolean {selection_name}_indices mask has shape {raw.shape}; "
                    f"expected ({n_atoms},)."
                )
            indices = np.flatnonzero(raw).astype(np.int64, copy=False)
        elif np.issubdtype(raw.dtype, np.integer):
            indices = raw.astype(np.int64, copy=False)
        else:
            raise TypeError(
                f"{selection_name}_indices must contain integers or booleans."
            )

        if indices.size == 0:
            raise ValueError(f"{selection_name} selection is empty.")
        if np.any(indices < 0) or np.any(indices >= n_atoms):
            bad = int(indices[(indices < 0) | (indices >= n_atoms)][0])
            raise IndexError(
                f"{selection_name} index {bad} is outside the valid range "
                f"0..{n_atoms - 1}."
            )
        if np.unique(indices).size != indices.size:
            raise ValueError(f"{selection_name}_indices contains duplicate entries.")
        return np.array(indices, dtype=np.int64, copy=True)

    if species is None:
        return np.arange(n_atoms, dtype=np.int64)

    if isinstance(species, (str, int, np.integer)) and not isinstance(
        species, (bool, np.bool_)
    ):
        requested = [_atomic_number(species)]
    elif isinstance(species, Sequence):
        if len(species) == 0:
            raise ValueError(f"{selection_name}_species is empty.")
        requested = [_atomic_number(item) for item in species]
    else:
        raise TypeError(
            f"{selection_name}_species must be a symbol, atomic number, or sequence."
        )

    requested_numbers = np.unique(np.asarray(requested, dtype=np.int32))
    indices = np.flatnonzero(np.isin(numbers, requested_numbers)).astype(np.int64)
    if indices.size == 0:
        labels = ", ".join(str(item) for item in requested)
        raise ValueError(
            f"{selection_name} selection matched no atoms for species: {labels}."
        )
    return indices
