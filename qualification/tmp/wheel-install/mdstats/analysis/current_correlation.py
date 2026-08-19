"""Collective charge currents and ordered positive-lag correlations.

C0 closes the mdstats charge, neutrality, exact-group-partition, cell-provenance,
and immutability contracts. C1 constructs microscopic charge currents and their
total and ordered group correlations. Conductivity integration is intentionally
deferred to C2.

The equilibrium current-correlation framework follows Green (J. Chem. Phys. 22,
398-413, 1954, DOI 10.1063/1.1740082) and Kubo (J. Phys. Soc. Jpn. 12,
570-586, 1957, DOI 10.1143/JPSJ.12.570). The FFT backend reuses the package's
Wiener-Khinchin positive-lag linear-correlation machinery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

import numpy as np
from ase.data import chemical_symbols
from numpy.typing import ArrayLike, NDArray
from scipy.fft import rfft

from ..collection import AtomisticFrameCollection
from ._dynamics_common import (
    DynamicsInputSignature,
    freeze_mapping,
    owned_readonly_array,
    require_bool,
    require_finite_real,
    require_nonnegative_int,
    require_positive_int,
    resolve_analysis_subspace,
)
from ._fft import (
    linear_fft_length,
    positive_lag_correlation_from_spectrum,
    positive_lag_pair_counts,
)
from ._velocity_common import DriftMode, prepare_velocity_inputs
from .selection import SpeciesSelection, resolve_atom_selection

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]
Backend = Literal["auto", "direct", "fft"]
CellMode = Literal["fixed", "variable"]

_C0_CONTRACT_VERSION = "collective-current-contract-v1"
_C1_CONTRACT_VERSION = "ordered-current-correlation-v1"
_CURRENT_UNITS = "e*Angstrom/ps"
_CORRELATION_UNITS = "e^2*Angstrom^2/ps^2"
_CELL_RTOL = 1.0e-10
_CELL_ATOL = 1.0e-12
_RESULT_RTOL = 2.0e-11
_RESULT_ATOL = 5.0e-13


def _as_integer_array(value: ArrayLike, *, name: str) -> IntArray:
    raw = np.asarray(value)
    if raw.ndim == 0 or np.issubdtype(raw.dtype, np.bool_) or not np.issubdtype(
        raw.dtype, np.integer
    ):
        raise TypeError(f"{name} must contain integers.")
    return np.asarray(raw, dtype=np.int64)


def _validate_charge_array(charges: ArrayLike, *, n_atoms: int) -> FloatArray:
    probe = np.asarray(charges, dtype=object)
    if probe.shape != (n_atoms,):
        raise ValueError(
            f"charges has shape {probe.shape}; expected ({n_atoms},)."
        )
    if any(isinstance(value, (bool, np.bool_)) for value in probe.flat):
        raise TypeError("charges must contain real numbers, not booleans.")
    try:
        values = np.asarray(charges, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise TypeError("charges must contain real numbers.") from exc
    if not np.all(np.isfinite(values)):
        raise ValueError("charges must contain only finite values.")
    result = np.array(values, dtype=np.float64, copy=True)
    result[result == 0.0] = 0.0
    return result


def _species_symbols(collection: AtomisticFrameCollection) -> tuple[str, ...]:
    symbols: list[str] = []
    for number in np.asarray(collection.atomic_numbers, dtype=np.int64):
        value = int(number)
        if value < 1 or value >= len(chemical_symbols):
            raise ValueError(f"Unsupported atomic number in collection: {value}.")
        symbols.append(str(chemical_symbols[value]))
    return tuple(symbols)


def _resolve_charges(
    collection: AtomisticFrameCollection,
    *,
    charges: ArrayLike | None,
    species_charges: Mapping[str, float] | None,
) -> tuple[FloatArray, str, Mapping[str, float] | None]:
    if (charges is None) == (species_charges is None):
        raise ValueError("Specify exactly one of charges and species_charges.")

    if charges is not None:
        return _validate_charge_array(charges, n_atoms=collection.n_atoms), "array", None

    if not isinstance(species_charges, Mapping):
        raise TypeError("species_charges must be a mapping from symbols to charges.")
    if len(species_charges) == 0:
        raise ValueError("species_charges must not be empty.")

    symbols = _species_symbols(collection)
    present = set(symbols)
    resolved_mapping: dict[str, float] = {}
    for key, value in species_charges.items():
        if not isinstance(key, str):
            raise TypeError(
                "species_charges keys must be exact chemical-symbol strings; "
                "integer keys are ambiguous."
            )
        if key not in present:
            raise ValueError(
                f"species_charges contains an unknown or unused symbol: {key!r}."
            )
        resolved_mapping[key] = require_finite_real(
            value,
            name=f"species_charges[{key!r}]",
        )

    missing = sorted(present.difference(resolved_mapping))
    if missing:
        raise ValueError(
            "species_charges is missing charges for present species: "
            + ", ".join(missing)
            + "."
        )

    values = np.asarray([resolved_mapping[symbol] for symbol in symbols], dtype=np.float64)
    values[values == 0.0] = 0.0
    return values, "species_map", freeze_mapping(resolved_mapping)


def _resolve_group_partition(
    collection: AtomisticFrameCollection,
    current_atom_indices: IntArray,
    species_groups: Mapping[str, SpeciesSelection] | None,
) -> tuple[tuple[str, ...], Mapping[str, IntArray]]:
    if species_groups is None:
        return (), freeze_mapping({})  # type: ignore[return-value]
    if not isinstance(species_groups, Mapping):
        raise TypeError("species_groups must be a mapping from names to species selections.")
    if len(species_groups) == 0:
        raise ValueError("species_groups must not be empty when supplied.")

    current_set = set(int(index) for index in current_atom_indices)
    names: list[str] = []
    resolved: dict[str, IntArray] = {}
    owner: dict[int, str] = {}

    for raw_name, selection in species_groups.items():
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise ValueError("Every species-group name must be a nonempty string.")
        name = raw_name
        names.append(name)
        selected = resolve_atom_selection(
            collection.atomic_numbers,
            species=selection,
            atom_indices=None,
            selection_name=f"species_group_{name}",
        )
        indices = np.asarray(
            [int(index) for index in current_atom_indices if int(index) in set(selected.tolist())],
            dtype=np.int64,
        )
        if indices.size == 0:
            raise ValueError(
                f"species group {name!r} contains no current-carrying atoms."
            )
        for index in indices:
            canonical = int(index)
            if canonical in owner:
                raise ValueError(
                    f"species groups overlap at atom {canonical}: "
                    f"{owner[canonical]!r} and {name!r}."
                )
            owner[canonical] = name
        resolved[name] = indices

    missing = [index for index in current_atom_indices.tolist() if int(index) not in owner]
    if missing:
        raise ValueError(
            "species_groups does not cover every current-carrying atom; "
            f"missing canonical indices: {missing}."
        )
    if set(owner) != current_set:  # defensive; the loop only admits current atoms.
        raise ValueError("species_groups does not form an exact current-atom partition.")

    frozen = freeze_mapping(resolved)
    return tuple(names), frozen  # type: ignore[return-value]


def _cell_provenance(
    collection: AtomisticFrameCollection,
) -> tuple[CellMode, FloatArray, float | None, BoolArray]:
    cells = np.asarray(collection.cells, dtype=np.float64)
    volumes = np.asarray(collection.volumes, dtype=np.float64)
    if volumes.shape != (collection.n_frames,) or not np.all(np.isfinite(volumes)):
        raise ValueError("Collection cell volumes are invalid.")
    if np.any(volumes <= 0.0):
        raise ValueError("Collection cell volumes must be strictly positive.")
    fixed = bool(
        np.allclose(cells, cells[0], rtol=_CELL_RTOL, atol=_CELL_ATOL)
    )
    fixed_volume = float(volumes[0]) if fixed else None
    if fixed and not np.allclose(
        volumes,
        fixed_volume,
        rtol=_CELL_RTOL,
        atol=_CELL_ATOL,
    ):
        raise ValueError("A fixed cell matrix produced inconsistent cell volumes.")
    pbc = np.asarray(collection.pbc, dtype=np.bool_)
    if pbc.shape != (3,):
        raise ValueError("Collection pbc must have shape (3,).")
    return (
        "fixed" if fixed else "variable",
        np.array(volumes, dtype=np.float64, copy=True),
        fixed_volume,
        np.array(pbc, dtype=np.bool_, copy=True),
    )


def _normalize_group_mapping(
    value: Mapping[str, ArrayLike],
    *,
    group_names: tuple[str, ...],
    n_atoms: int,
    current_atom_indices: IntArray,
) -> Mapping[str, IntArray]:
    if not isinstance(value, Mapping):
        raise TypeError("group_atom_indices must be a mapping.")
    if tuple(value.keys()) != group_names:
        raise ValueError("group_atom_indices keys and order must match group_names.")
    owner: set[int] = set()
    normalized: dict[str, IntArray] = {}
    current_set = set(int(index) for index in current_atom_indices)
    for name in group_names:
        indices = _as_integer_array(value[name], name=f"group_atom_indices[{name!r}]")
        if indices.ndim != 1 or indices.size < 1:
            raise ValueError(f"group {name!r} must contain at least one atom.")
        if np.any(indices < 0) or np.any(indices >= n_atoms):
            raise ValueError(f"group {name!r} contains an out-of-range atom index.")
        if np.unique(indices).size != indices.size:
            raise ValueError(f"group {name!r} contains duplicate atom indices.")
        for index in indices.tolist():
            canonical = int(index)
            if canonical not in current_set:
                raise ValueError(
                    f"group {name!r} contains non-current atom {canonical}."
                )
            if canonical in owner:
                raise ValueError("group_atom_indices contains overlapping groups.")
            owner.add(canonical)
        normalized[name] = np.array(indices, dtype=np.int64, copy=True)
    if owner != current_set:
        raise ValueError("group_atom_indices must exactly partition current_atom_indices.")
    return freeze_mapping(normalized)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class ChargeCurrentResult:
    """Immutable microscopic total and exact-partition group charge currents."""

    times_ps: FloatArray
    total_current: FloatArray
    group_names: tuple[str, ...]
    group_currents: FloatArray | None
    charges_e: FloatArray
    current_atom_indices: IntArray
    group_atom_indices: Mapping[str, IntArray]
    total_charge_e: float
    neutrality_tolerance_e: float
    sample_spacing_ps: float
    pbc: BoolArray
    cell_volumes_a3: FloatArray
    cell_mode: CellMode
    fixed_volume_a3: float | None
    signature: DynamicsInputSignature
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        times = np.asarray(self.times_ps, dtype=np.float64)
        total_current = np.asarray(self.total_current, dtype=np.float64)
        charges = np.asarray(self.charges_e, dtype=np.float64)
        current_indices = _as_integer_array(
            self.current_atom_indices,
            name="current_atom_indices",
        )
        pbc = np.asarray(self.pbc, dtype=np.bool_)
        volumes = np.asarray(self.cell_volumes_a3, dtype=np.float64)
        names = tuple(self.group_names)

        if times.ndim != 1 or times.size < 2:
            raise ValueError("times_ps must be one-dimensional with at least two values.")
        n_frames = int(times.size)
        if not np.all(np.isfinite(times)) or np.any(np.diff(times) <= 0.0):
            raise ValueError("times_ps must be finite and strictly increasing.")
        spacing = require_finite_real(
            self.sample_spacing_ps,
            name="sample_spacing_ps",
            positive=True,
        )
        if not np.allclose(
            np.diff(times), spacing, rtol=1.0e-10, atol=1.0e-14
        ):
            raise ValueError("sample_spacing_ps is inconsistent with times_ps.")
        if total_current.shape != (n_frames, 3) or not np.all(
            np.isfinite(total_current)
        ):
            raise ValueError("total_current must be a finite array with shape (T, 3).")
        if charges.ndim != 1 or charges.size < 1 or not np.all(np.isfinite(charges)):
            raise ValueError("charges_e must be a finite nonempty one-dimensional array.")
        n_atoms = int(charges.size)
        if current_indices.ndim != 1 or current_indices.size < 1:
            raise ValueError("current_atom_indices must be nonempty and one-dimensional.")
        if np.any(current_indices < 0) or np.any(current_indices >= n_atoms):
            raise ValueError("current_atom_indices contains an out-of-range index.")
        if np.unique(current_indices).size != current_indices.size:
            raise ValueError("current_atom_indices must not contain duplicates.")
        expected_current = np.flatnonzero(charges != 0.0).astype(np.int64)
        if not np.array_equal(current_indices, expected_current):
            raise ValueError(
                "current_atom_indices must equal the canonical nonzero-charge atoms."
            )

        tolerance = require_finite_real(
            self.neutrality_tolerance_e,
            name="neutrality_tolerance_e",
            nonnegative=True,
        )
        total_charge = require_finite_real(
            self.total_charge_e,
            name="total_charge_e",
        )
        if not np.isclose(
            total_charge,
            float(np.sum(charges, dtype=np.float64)),
            rtol=0.0,
            atol=max(1.0e-15, 10.0 * np.finfo(np.float64).eps * max(1.0, float(np.sum(np.abs(charges))))),
        ):
            raise ValueError("total_charge_e is inconsistent with charges_e.")
        if abs(total_charge) > tolerance:
            raise ValueError("ChargeCurrentResult violates the neutrality tolerance.")

        if pbc.shape != (3,):
            raise ValueError("pbc must have shape (3,).")
        if volumes.shape != (n_frames,) or not np.all(np.isfinite(volumes)) or np.any(volumes <= 0.0):
            raise ValueError("cell_volumes_a3 must be finite, positive, and have shape (T,).")
        if self.cell_mode not in ("fixed", "variable"):
            raise ValueError("cell_mode must be 'fixed' or 'variable'.")
        fixed_volume = None
        if self.cell_mode == "fixed":
            if self.fixed_volume_a3 is None:
                raise ValueError("fixed_volume_a3 is required for a fixed cell.")
            fixed_volume = require_finite_real(
                self.fixed_volume_a3,
                name="fixed_volume_a3",
                positive=True,
            )
            if not np.allclose(
                volumes, fixed_volume, rtol=_CELL_RTOL, atol=_CELL_ATOL
            ):
                raise ValueError("fixed_volume_a3 is inconsistent with cell_volumes_a3.")
        elif self.fixed_volume_a3 is not None:
            raise ValueError("fixed_volume_a3 must be None for a variable cell.")

        if any(not isinstance(name, str) or not name for name in names):
            raise ValueError("group_names entries must be nonempty strings.")
        if len(set(names)) != len(names):
            raise ValueError("group_names must be unique.")
        groups = _normalize_group_mapping(
            self.group_atom_indices,
            group_names=names,
            n_atoms=n_atoms,
            current_atom_indices=current_indices,
        ) if names else freeze_mapping({})
        group_currents = None if self.group_currents is None else np.asarray(
            self.group_currents,
            dtype=np.float64,
        )
        if names:
            if group_currents is None or group_currents.shape != (n_frames, len(names), 3):
                raise ValueError(
                    "group_currents must have shape (T, G, 3) when groups exist."
                )
            if not np.all(np.isfinite(group_currents)):
                raise ValueError("group_currents must contain only finite values.")
            if not np.allclose(
                np.sum(group_currents, axis=1),
                total_current,
                rtol=_RESULT_RTOL,
                atol=_RESULT_ATOL,
            ):
                raise ValueError("Group currents must sum exactly to total_current.")
        else:
            if group_currents is not None:
                raise ValueError("group_currents must be None when no groups exist.")
            if len(self.group_atom_indices) != 0:
                raise ValueError("group_atom_indices must be empty when no groups exist.")

        if not isinstance(self.signature, DynamicsInputSignature):
            raise TypeError("signature must be a DynamicsInputSignature.")
        if not np.array_equal(self.signature.atom_indices, current_indices):
            raise ValueError("signature atom_indices are inconsistent with current atoms.")
        if not self.signature.subspace.same_physical_subspace(resolve_analysis_subspace()):
            raise ValueError("Charge current signatures must use the full 3D subspace.")
        if self.signature.n_frames != n_frames or not np.array_equal(
            self.signature.frame_times_ps, times
        ):
            raise ValueError("signature frame/time identity is inconsistent with current data.")
        if self.signature.sample_spacing_ps != spacing:
            raise ValueError("signature sample spacing is inconsistent with current data.")

        object.__setattr__(self, "times_ps", owned_readonly_array(times, dtype=np.float64))
        object.__setattr__(self, "total_current", owned_readonly_array(total_current, dtype=np.float64))
        object.__setattr__(self, "group_names", names)
        object.__setattr__(
            self,
            "group_currents",
            None if group_currents is None else owned_readonly_array(group_currents, dtype=np.float64),
        )
        object.__setattr__(self, "charges_e", owned_readonly_array(charges, dtype=np.float64))
        object.__setattr__(self, "current_atom_indices", owned_readonly_array(current_indices, dtype=np.int64))
        object.__setattr__(self, "group_atom_indices", groups)
        object.__setattr__(self, "total_charge_e", total_charge)
        object.__setattr__(self, "neutrality_tolerance_e", tolerance)
        object.__setattr__(self, "sample_spacing_ps", spacing)
        object.__setattr__(self, "pbc", owned_readonly_array(pbc, dtype=np.bool_))
        object.__setattr__(self, "cell_volumes_a3", owned_readonly_array(volumes, dtype=np.float64))
        object.__setattr__(self, "fixed_volume_a3", fixed_volume)
        object.__setattr__(self, "metadata", freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class CurrentCorrelationResult:
    """Immutable total and ordered group positive-lag current correlations."""

    lag_steps: IntArray
    lag_times: FloatArray
    scalar: FloatArray
    components: FloatArray
    tensor: FloatArray | None
    group_names: tuple[str, ...]
    group_scalar: FloatArray | None
    group_tensor: FloatArray | None
    n_origins: IntArray
    backend: Literal["direct", "fft"]
    charges_e: FloatArray
    current_atom_indices: IntArray
    group_atom_indices: Mapping[str, IntArray]
    total_charge_e: float
    neutrality_tolerance_e: float
    pbc: BoolArray
    cell_volumes_a3: FloatArray
    cell_mode: CellMode
    fixed_volume_a3: float | None
    signature: DynamicsInputSignature
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        lags = _as_integer_array(self.lag_steps, name="lag_steps")
        n_origins = _as_integer_array(self.n_origins, name="n_origins")
        lag_times = np.asarray(self.lag_times, dtype=np.float64)
        scalar = np.asarray(self.scalar, dtype=np.float64)
        components = np.asarray(self.components, dtype=np.float64)
        tensor = None if self.tensor is None else np.asarray(self.tensor, dtype=np.float64)
        names = tuple(self.group_names)
        group_scalar = None if self.group_scalar is None else np.asarray(self.group_scalar, dtype=np.float64)
        group_tensor = None if self.group_tensor is None else np.asarray(self.group_tensor, dtype=np.float64)
        charges = np.asarray(self.charges_e, dtype=np.float64)
        current_indices = _as_integer_array(self.current_atom_indices, name="current_atom_indices")
        pbc = np.asarray(self.pbc, dtype=np.bool_)
        volumes = np.asarray(self.cell_volumes_a3, dtype=np.float64)

        if lags.ndim != 1 or lags.size < 1 or np.any(lags < 0) or (
            lags.size > 1 and np.any(np.diff(lags) <= 0)
        ):
            raise ValueError("lag_steps must be nonempty, nonnegative, increasing, and unique.")
        n_lags = int(lags.size)
        if lag_times.shape != (n_lags,) or scalar.shape != (n_lags,) or n_origins.shape != (n_lags,):
            raise ValueError("lag-axis arrays have inconsistent shapes.")
        if components.shape != (n_lags, 3):
            raise ValueError("components must have shape (L, 3).")
        if tensor is not None and tensor.shape != (n_lags, 3, 3):
            raise ValueError("tensor must have shape (L, 3, 3) or None.")
        finite = [lag_times, scalar, components]
        if tensor is not None:
            finite.append(tensor)
        if any(not np.all(np.isfinite(value)) for value in finite):
            raise ValueError("Current correlation contains non-finite values.")
        if np.any(n_origins < 1):
            raise ValueError("Every stored lag must contain at least one origin.")
        if not np.allclose(
            scalar,
            np.sum(components, axis=1),
            rtol=_RESULT_RTOL,
            atol=_RESULT_ATOL,
        ):
            raise ValueError("scalar must equal the sum of Cartesian components.")
        if tensor is not None and not np.allclose(
            components,
            np.diagonal(tensor, axis1=1, axis2=2),
            rtol=_RESULT_RTOL,
            atol=_RESULT_ATOL,
        ):
            raise ValueError("components must equal the tensor diagonal.")
        if self.backend not in ("direct", "fft"):
            raise ValueError("backend must be 'direct' or 'fft'.")

        if any(not isinstance(name, str) or not name for name in names) or len(set(names)) != len(names):
            raise ValueError("group_names must contain unique nonempty strings.")
        n_atoms = int(charges.size)
        groups = _normalize_group_mapping(
            self.group_atom_indices,
            group_names=names,
            n_atoms=n_atoms,
            current_atom_indices=current_indices,
        ) if names else freeze_mapping({})
        if names:
            expected = (n_lags, len(names), len(names))
            if group_scalar is None or group_scalar.shape != expected:
                raise ValueError("group_scalar must have shape (L, G, G).")
            if not np.all(np.isfinite(group_scalar)):
                raise ValueError("group_scalar must contain only finite values.")
            if tensor is None:
                if group_tensor is not None:
                    raise ValueError("group_tensor must be None when tensor is not retained.")
            else:
                expected_tensor = (n_lags, len(names), len(names), 3, 3)
                if group_tensor is None or group_tensor.shape != expected_tensor:
                    raise ValueError("group_tensor must have shape (L, G, G, 3, 3).")
                if not np.all(np.isfinite(group_tensor)):
                    raise ValueError("group_tensor must contain only finite values.")
                if not np.allclose(
                    group_scalar,
                    np.trace(group_tensor, axis1=3, axis2=4),
                    rtol=_RESULT_RTOL,
                    atol=_RESULT_ATOL,
                ):
                    raise ValueError("group_scalar must equal group-tensor traces.")
                if not np.allclose(
                    tensor,
                    np.sum(group_tensor, axis=(1, 2)),
                    rtol=_RESULT_RTOL,
                    atol=_RESULT_ATOL,
                ):
                    raise ValueError("Ordered group tensors must sum to total tensor.")
            if not np.allclose(
                scalar,
                np.sum(group_scalar, axis=(1, 2)),
                rtol=_RESULT_RTOL,
                atol=_RESULT_ATOL,
            ):
                raise ValueError("Ordered group correlations must sum to total scalar.")
        else:
            if group_scalar is not None or group_tensor is not None:
                raise ValueError("Group correlations must be None when no groups exist.")
            if len(self.group_atom_indices) != 0:
                raise ValueError("group_atom_indices must be empty when no groups exist.")

        if charges.ndim != 1 or charges.size < 1 or not np.all(np.isfinite(charges)):
            raise ValueError("charges_e must be finite and one-dimensional.")
        expected_current = np.flatnonzero(charges != 0.0).astype(np.int64)
        if not np.array_equal(current_indices, expected_current):
            raise ValueError("current_atom_indices is inconsistent with charges_e.")
        total_charge = require_finite_real(self.total_charge_e, name="total_charge_e")
        tolerance = require_finite_real(
            self.neutrality_tolerance_e,
            name="neutrality_tolerance_e",
            nonnegative=True,
        )
        if abs(total_charge) > tolerance or not np.isclose(
            total_charge,
            float(np.sum(charges)),
            rtol=0.0,
            atol=max(1.0e-15, 10.0 * np.finfo(np.float64).eps * max(1.0, float(np.sum(np.abs(charges))))),
        ):
            raise ValueError("Charge provenance is inconsistent or non-neutral.")
        if pbc.shape != (3,):
            raise ValueError("pbc must have shape (3,).")
        if volumes.ndim != 1 or volumes.size < 2 or not np.all(np.isfinite(volumes)) or np.any(volumes <= 0.0):
            raise ValueError("cell_volumes_a3 must be finite, positive, and one-dimensional.")
        if self.cell_mode not in ("fixed", "variable"):
            raise ValueError("cell_mode must be 'fixed' or 'variable'.")
        fixed_volume = None
        if self.cell_mode == "fixed":
            if self.fixed_volume_a3 is None:
                raise ValueError("fixed_volume_a3 is required for fixed-cell provenance.")
            fixed_volume = require_finite_real(self.fixed_volume_a3, name="fixed_volume_a3", positive=True)
            if not np.allclose(volumes, fixed_volume, rtol=_CELL_RTOL, atol=_CELL_ATOL):
                raise ValueError("fixed_volume_a3 is inconsistent with cell_volumes_a3.")
        elif self.fixed_volume_a3 is not None:
            raise ValueError("fixed_volume_a3 must be None for variable-cell provenance.")

        if not isinstance(self.signature, DynamicsInputSignature):
            raise TypeError("signature must be a DynamicsInputSignature.")
        if not np.array_equal(self.signature.atom_indices, current_indices):
            raise ValueError("signature atom_indices are inconsistent with current atoms.")
        if not self.signature.subspace.same_physical_subspace(resolve_analysis_subspace()):
            raise ValueError("Current-correlation signatures must use the full 3D subspace.")
        if self.signature.n_frames != volumes.size:
            raise ValueError("signature frame count is inconsistent with volume provenance.")
        spacing = self.signature.sample_spacing_ps
        if spacing is None or not np.allclose(
            lag_times,
            lags.astype(np.float64) * spacing,
            rtol=1.0e-12,
            atol=1.0e-14,
        ):
            raise ValueError("lag_times is inconsistent with lag_steps and signature spacing.")

        object.__setattr__(self, "lag_steps", owned_readonly_array(lags, dtype=np.int64))
        object.__setattr__(self, "lag_times", owned_readonly_array(lag_times, dtype=np.float64))
        object.__setattr__(self, "scalar", owned_readonly_array(scalar, dtype=np.float64))
        object.__setattr__(self, "components", owned_readonly_array(components, dtype=np.float64))
        object.__setattr__(self, "tensor", None if tensor is None else owned_readonly_array(tensor, dtype=np.float64))
        object.__setattr__(self, "group_names", names)
        object.__setattr__(self, "group_scalar", None if group_scalar is None else owned_readonly_array(group_scalar, dtype=np.float64))
        object.__setattr__(self, "group_tensor", None if group_tensor is None else owned_readonly_array(group_tensor, dtype=np.float64))
        object.__setattr__(self, "n_origins", owned_readonly_array(n_origins, dtype=np.int64))
        object.__setattr__(self, "charges_e", owned_readonly_array(charges, dtype=np.float64))
        object.__setattr__(self, "current_atom_indices", owned_readonly_array(current_indices, dtype=np.int64))
        object.__setattr__(self, "group_atom_indices", groups)
        object.__setattr__(self, "total_charge_e", total_charge)
        object.__setattr__(self, "neutrality_tolerance_e", tolerance)
        object.__setattr__(self, "pbc", owned_readonly_array(pbc, dtype=np.bool_))
        object.__setattr__(self, "cell_volumes_a3", owned_readonly_array(volumes, dtype=np.float64))
        object.__setattr__(self, "fixed_volume_a3", fixed_volume)
        object.__setattr__(self, "metadata", freeze_mapping(self.metadata))


def compute_charge_current(
    collection: AtomisticFrameCollection,
    *,
    charges: ArrayLike | None = None,
    species_charges: Mapping[str, float] | None = None,
    species_groups: Mapping[str, SpeciesSelection] | None = None,
    drift_mode: DriftMode | None = None,
    drift_species: SpeciesSelection = None,
    drift_atom_indices: ArrayLike | None = None,
    neutrality_tolerance_e: float = 1.0e-12,
) -> ChargeCurrentResult:
    """Construct a neutral microscopic charge-current time series.

    Charge values are in elementary-charge units and velocities are in
    Angstrom/ps. The returned current is not converted to SI and is not time
    correlated. Conductivity integration belongs to C2.
    """

    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be an AtomisticFrameCollection instance.")
    tolerance = require_finite_real(
        neutrality_tolerance_e,
        name="neutrality_tolerance_e",
        nonnegative=True,
    )
    resolved_charges, charge_source, resolved_species_map = _resolve_charges(
        collection,
        charges=charges,
        species_charges=species_charges,
    )
    total_charge = float(np.sum(resolved_charges, dtype=np.float64))
    if abs(total_charge) > tolerance:
        raise ValueError(
            f"Resolved total charge {total_charge:.16g} e exceeds "
            f"neutrality_tolerance_e={tolerance:.16g}."
        )
    current_indices = np.flatnonzero(resolved_charges != 0.0).astype(np.int64)
    if current_indices.size == 0:
        raise ValueError("At least one atom must have a nonzero resolved charge.")

    inputs = prepare_velocity_inputs(
        collection,
        analysis_name="charge-current construction",
        atom_indices=current_indices,
        weights="uniform",
        drift_mode=drift_mode,
        drift_species=drift_species,
        drift_atom_indices=drift_atom_indices,
    )
    selected_velocities = np.asarray(
        inputs.velocities[:, current_indices, :],
        dtype=np.float64,
    )
    if inputs.drift_velocity is not None:
        selected_velocities = selected_velocities - inputs.drift_velocity[:, None, :]
    selected_charges = resolved_charges[current_indices]
    total_current = np.einsum(
        "tni,n->ti",
        selected_velocities,
        selected_charges,
        optimize=True,
    )
    if not np.all(np.isfinite(total_current)):
        raise ValueError("Resolved total charge current contains non-finite values.")

    group_names, group_indices = _resolve_group_partition(
        collection,
        current_indices,
        species_groups,
    )
    group_currents: FloatArray | None = None
    if group_names:
        local_lookup = {int(atom): local for local, atom in enumerate(current_indices)}
        group_currents = np.empty(
            (collection.n_frames, len(group_names), 3),
            dtype=np.float64,
        )
        for group_position, name in enumerate(group_names):
            canonical = np.asarray(group_indices[name], dtype=np.int64)
            local = np.asarray([local_lookup[int(atom)] for atom in canonical], dtype=np.int64)
            group_currents[:, group_position, :] = np.einsum(
                "tni,n->ti",
                selected_velocities[:, local, :],
                selected_charges[local],
                optimize=True,
            )
        if not np.allclose(
            np.sum(group_currents, axis=1),
            total_current,
            rtol=_RESULT_RTOL,
            atol=_RESULT_ATOL,
        ):
            raise RuntimeError("Internal group-current sum does not reproduce total current.")

    cell_mode, volumes, fixed_volume, pbc = _cell_provenance(collection)
    metadata: dict[str, Any] = {
        "contract_version": _C0_CONTRACT_VERSION,
        "charge_source": charge_source,
        "species_charges": resolved_species_map,
        "current_units": _CURRENT_UNITS,
        "charge_units": "e",
        "velocity_units": "Angstrom/ps",
        "current_atom_indices": current_indices.tolist(),
        "group_names": list(group_names),
        "group_atom_indices": {
            name: np.asarray(group_indices[name], dtype=np.int64).tolist()
            for name in group_names
        },
        "total_charge_e": total_charge,
        "neutrality_tolerance_e": tolerance,
        "drift_mode": drift_mode,
        "drift_atom_indices": (
            None
            if inputs.drift_atom_indices is None
            else inputs.drift_atom_indices.tolist()
        ),
        "cell_mode": cell_mode,
        "fixed_volume_a3": fixed_volume,
        "cell_equivalence_rtol": _CELL_RTOL,
        "cell_equivalence_atol": _CELL_ATOL,
        "pbc": pbc.tolist(),
        "frame_count": collection.n_frames,
        "time_start_ps": float(collection.times[0]),
        "time_end_ps": float(collection.times[-1]),
        "sample_spacing_ps": inputs.sample_spacing_ps,
    }

    return ChargeCurrentResult(
        times_ps=np.asarray(collection.times, dtype=np.float64),
        total_current=total_current,
        group_names=group_names,
        group_currents=group_currents,
        charges_e=resolved_charges,
        current_atom_indices=current_indices,
        group_atom_indices=group_indices,
        total_charge_e=total_charge,
        neutrality_tolerance_e=tolerance,
        sample_spacing_ps=inputs.sample_spacing_ps,
        pbc=pbc,
        cell_volumes_a3=volumes,
        cell_mode=cell_mode,
        fixed_volume_a3=fixed_volume,
        signature=inputs.signature,
        metadata=metadata,
    )


def _direct_current_correlation(
    total_current: FloatArray,
    group_currents: FloatArray | None,
    lags: IntArray,
    *,
    origin_stride: int,
    compute_tensor: bool,
) -> tuple[FloatArray, FloatArray | None, FloatArray | None, FloatArray | None, IntArray]:
    n_lags = int(lags.size)
    components = np.empty((n_lags, 3), dtype=np.float64)
    tensor = np.empty((n_lags, 3, 3), dtype=np.float64) if compute_tensor else None
    n_groups = 0 if group_currents is None else int(group_currents.shape[1])
    group_scalar = (
        None if group_currents is None else np.empty((n_lags, n_groups, n_groups), dtype=np.float64)
    )
    group_tensor = (
        None
        if group_currents is None or not compute_tensor
        else np.empty((n_lags, n_groups, n_groups, 3, 3), dtype=np.float64)
    )
    n_origins = np.empty(n_lags, dtype=np.int64)

    for out, lag_value in enumerate(lags):
        lag = int(lag_value)
        origins = np.arange(0, total_current.shape[0] - lag, origin_stride, dtype=np.int64)
        first = total_current[origins]
        second = total_current[origins + lag]
        count = int(origins.size)
        n_origins[out] = count
        components[out] = np.mean(first * second, axis=0)
        if tensor is not None:
            tensor[out] = np.einsum("oa,ob->ab", first, second, optimize=True) / count

        if group_currents is not None:
            first_groups = group_currents[origins]
            second_groups = group_currents[origins + lag]
            if group_tensor is not None:
                group_tensor[out] = (
                    np.einsum(
                        "oga,ohb->ghab",
                        first_groups,
                        second_groups,
                        optimize=True,
                    )
                    / count
                )
                assert group_scalar is not None
                group_scalar[out] = np.trace(group_tensor[out], axis1=2, axis2=3)
            else:
                assert group_scalar is not None
                group_scalar[out] = (
                    np.einsum(
                        "oga,oha->gh",
                        first_groups,
                        second_groups,
                        optimize=True,
                    )
                    / count
                )

    return components, tensor, group_scalar, group_tensor, n_origins


def _fft_current_correlation(
    total_current: FloatArray,
    group_currents: FloatArray | None,
    lags: IntArray,
    *,
    compute_tensor: bool,
) -> tuple[FloatArray, FloatArray | None, FloatArray | None, FloatArray | None, IntArray, int]:
    n_frames = int(total_current.shape[0])
    max_lag = int(lags[-1])
    n_fft = linear_fft_length(n_frames)
    counts = positive_lag_pair_counts(n_frames, max_lag)
    transformed = rfft(np.moveaxis(total_current, 0, -1), n=n_fft, axis=-1)

    if compute_tensor:
        tensor = np.empty((lags.size, 3, 3), dtype=np.float64)
        for alpha in range(3):
            origin_spectrum = np.conjugate(transformed[alpha])
            for beta in range(3):
                correlation = positive_lag_correlation_from_spectrum(
                    origin_spectrum * transformed[beta],
                    n_fft=n_fft,
                    max_lag=max_lag,
                )
                tensor[:, alpha, beta] = (correlation / counts)[lags]
        components = np.diagonal(tensor, axis1=1, axis2=2).copy()
    else:
        tensor = None
        components = np.empty((lags.size, 3), dtype=np.float64)
        for alpha in range(3):
            correlation = positive_lag_correlation_from_spectrum(
                np.conjugate(transformed[alpha]) * transformed[alpha],
                n_fft=n_fft,
                max_lag=max_lag,
            )
            components[:, alpha] = (correlation / counts)[lags]

    group_scalar: FloatArray | None = None
    group_tensor: FloatArray | None = None
    if group_currents is not None:
        n_groups = int(group_currents.shape[1])
        group_transformed = rfft(
            np.moveaxis(group_currents, 0, -1),
            n=n_fft,
            axis=-1,
        )
        group_scalar = np.empty((lags.size, n_groups, n_groups), dtype=np.float64)
        if compute_tensor:
            group_tensor = np.empty(
                (lags.size, n_groups, n_groups, 3, 3),
                dtype=np.float64,
            )
        for first_group in range(n_groups):
            for second_group in range(n_groups):
                if compute_tensor:
                    assert group_tensor is not None
                    for alpha in range(3):
                        origin_spectrum = np.conjugate(
                            group_transformed[first_group, alpha]
                        )
                        for beta in range(3):
                            correlation = positive_lag_correlation_from_spectrum(
                                origin_spectrum
                                * group_transformed[second_group, beta],
                                n_fft=n_fft,
                                max_lag=max_lag,
                            )
                            group_tensor[
                                :, first_group, second_group, alpha, beta
                            ] = (correlation / counts)[lags]
                    group_scalar[:, first_group, second_group] = np.trace(
                        group_tensor[:, first_group, second_group],
                        axis1=1,
                        axis2=2,
                    )
                else:
                    spectrum = np.sum(
                        np.conjugate(group_transformed[first_group])
                        * group_transformed[second_group],
                        axis=0,
                    )
                    correlation = positive_lag_correlation_from_spectrum(
                        spectrum,
                        n_fft=n_fft,
                        max_lag=max_lag,
                    )
                    group_scalar[:, first_group, second_group] = (
                        correlation / counts
                    )[lags]

    return (
        components,
        tensor,
        group_scalar,
        group_tensor,
        (n_frames - lags).astype(np.int64),
        n_fft,
    )


def _select_correlation_backend(
    backend: Backend,
    *,
    n_frames: int,
    n_lags: int,
    max_lag: int,
    origin_stride: int,
    n_groups: int,
    compute_tensor: bool,
) -> tuple[Literal["direct", "fft"], float, float]:
    if backend not in ("auto", "direct", "fft"):
        raise ValueError("backend must be 'auto', 'direct', or 'fft'.")
    tensor_factor = 9.0 if compute_tensor else 3.0
    pair_factor = 1.0 + float(n_groups * n_groups)
    mean_origins = (n_frames - max_lag / 2.0) / origin_stride
    direct_work = n_lags * mean_origins * tensor_factor * pair_factor
    n_fft = linear_fft_length(n_frames)
    fft_work = n_fft * np.log2(max(2, n_fft)) * tensor_factor * pair_factor
    if backend == "direct":
        return "direct", float(direct_work), float(fft_work)
    if backend == "fft":
        if origin_stride != 1:
            raise ValueError("backend='fft' requires origin_stride == 1.")
        return "fft", float(direct_work), float(fft_work)
    if origin_stride != 1 or n_frames < 64 or direct_work <= 2.0 * fft_work:
        return "direct", float(direct_work), float(fft_work)
    return "fft", float(direct_work), float(fft_work)


def compute_current_correlation(
    current: ChargeCurrentResult,
    *,
    max_lag: int | None = None,
    origin_stride: int = 1,
    lag_stride: int = 1,
    compute_tensor: bool = True,
    backend: Backend = "auto",
) -> CurrentCorrelationResult:
    """Compute raw total and ordered group positive-lag current correlations.

    No mean-current subtraction, detrending, smoothing, or symmetrization is
    performed. Drift removal, when desired, must be selected during charge-
    current construction.
    """

    if not isinstance(current, ChargeCurrentResult):
        raise TypeError("current must be a ChargeCurrentResult.")
    origin_stride = require_positive_int(origin_stride, name="origin_stride")
    lag_stride = require_positive_int(lag_stride, name="lag_stride")
    compute_tensor = require_bool(compute_tensor, name="compute_tensor")
    n_frames = int(current.times_ps.size)
    resolved_max_lag = n_frames // 2 if max_lag is None else require_nonnegative_int(
        max_lag,
        name="max_lag",
    )
    if resolved_max_lag >= n_frames:
        raise ValueError(
            f"max_lag={resolved_max_lag} exceeds the largest available frame lag "
            f"{n_frames - 1}."
        )
    lags = np.arange(0, resolved_max_lag + 1, lag_stride, dtype=np.int64)
    chosen_backend, direct_work, fft_work = _select_correlation_backend(
        backend,
        n_frames=n_frames,
        n_lags=int(lags.size),
        max_lag=resolved_max_lag,
        origin_stride=origin_stride,
        n_groups=len(current.group_names),
        compute_tensor=compute_tensor,
    )

    n_fft: int | None = None
    if chosen_backend == "direct":
        components, tensor, group_scalar, group_tensor, n_origins = (
            _direct_current_correlation(
                np.asarray(current.total_current, dtype=np.float64),
                None
                if current.group_currents is None
                else np.asarray(current.group_currents, dtype=np.float64),
                lags,
                origin_stride=origin_stride,
                compute_tensor=compute_tensor,
            )
        )
    else:
        (
            components,
            tensor,
            group_scalar,
            group_tensor,
            n_origins,
            n_fft,
        ) = _fft_current_correlation(
            np.asarray(current.total_current, dtype=np.float64),
            None
            if current.group_currents is None
            else np.asarray(current.group_currents, dtype=np.float64),
            lags,
            compute_tensor=compute_tensor,
        )
    scalar = np.sum(components, axis=1)
    lag_times = lags.astype(np.float64) * current.sample_spacing_ps

    metadata: dict[str, Any] = {
        "contract_version": _C1_CONTRACT_VERSION,
        "current_contract_version": _C0_CONTRACT_VERSION,
        "current_units": _CURRENT_UNITS,
        "correlation_units": _CORRELATION_UNITS,
        "ordered_group_correlations": bool(current.group_names),
        "mean_current_subtracted": False,
        "group_names": list(current.group_names),
        "requested_backend": backend,
        "chosen_backend": chosen_backend,
        "estimated_direct_work": direct_work,
        "estimated_fft_work": fft_work,
        "fft_length": n_fft,
        "origin_stride": origin_stride,
        "lag_stride": lag_stride,
        "maximum_lag": resolved_max_lag,
        "time_step_ps": current.sample_spacing_ps,
        "cell_mode": current.cell_mode,
        "fixed_volume_a3": current.fixed_volume_a3,
        "pbc": current.pbc.tolist(),
        "total_charge_e": current.total_charge_e,
        "neutrality_tolerance_e": current.neutrality_tolerance_e,
        "source_current_metadata": current.metadata,
    }

    return CurrentCorrelationResult(
        lag_steps=lags,
        lag_times=lag_times,
        scalar=scalar,
        components=components,
        tensor=tensor,
        group_names=current.group_names,
        group_scalar=group_scalar,
        group_tensor=group_tensor,
        n_origins=n_origins,
        backend=chosen_backend,
        charges_e=current.charges_e,
        current_atom_indices=current.current_atom_indices,
        group_atom_indices=current.group_atom_indices,
        total_charge_e=current.total_charge_e,
        neutrality_tolerance_e=current.neutrality_tolerance_e,
        pbc=current.pbc,
        cell_volumes_a3=current.cell_volumes_a3,
        cell_mode=current.cell_mode,
        fixed_volume_a3=current.fixed_volume_a3,
        signature=current.signature,
        metadata=metadata,
    )
