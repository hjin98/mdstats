"""Deterministic geometry, topology, and relaxation helpers for qualification.

These are the small, exact operations qualification needs on *single*
configurations: build one authenticated frame, displace one atom along one axis,
enumerate covalent bonds and their angles, and relax at fixed cell.  The
trajectory-statistics owners in :mod:`mdstats.analysis` answer a different
question (ensemble observables over a collection) and are not duplicated here;
where an established owner does apply - ASE's relaxation algorithms and ASE's
covalent-radius table - it is called rather than reimplemented.  The canonical
``bond_angle`` analysis owner returns aggregate angle distributions and
intentionally discards endpoint identity; protected P7 topology needs a
keyed per-angle observable, so :func:`angle_table` is a narrow adapter over
the canonical periodic vectors, not a second connectivity owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from .._common import TrainingDataInputError
from .errors import QualificationError

_AXIS_INDEX = {"x": 0, "y": 1, "z": 2}


def atoms_for_frame(context: Any, frame_uid: str) -> Any:
    """Materialize one authenticated canonical frame as ASE ``Atoms``."""

    from .._frame_access import ase_atoms_for_frame

    index = context.selected.authorities.frame_array_index
    entry = index.get(str(frame_uid))
    if entry is None:
        raise QualificationError(
            f"Frame {frame_uid!r} is not present in the current authenticated frame index."
        )
    record, frame_data, local_index = entry
    return ase_atoms_for_frame(record, frame_data, local_index)


def labels_for_frame(context: Any, frame_uid: str) -> tuple[float, np.ndarray]:
    """The canonical reference energy/forces already carried by one frame.

    These are the authenticated first-principles labels of the frame itself, not
    a new external reference request: calibration and the locked test compare the
    product against evidence that already exists in a reserved neutral role.
    """

    index = context.selected.authorities.frame_array_index
    entry = index.get(str(frame_uid))
    if entry is None:
        raise QualificationError(
            f"Frame {frame_uid!r} is not present in the current authenticated frame index."
        )
    _record, frame_data, local_index = entry
    energies = frame_data.energies_ev
    forces = frame_data.forces_ev_per_angstrom
    if energies is None or forces is None:
        raise QualificationError(
            f"Frame {frame_uid!r} carries no reference labels, so it cannot serve as "
            "independent evaluation evidence."
        )
    return (
        float(np.asarray(energies, dtype=np.float64)[local_index]),
        np.asarray(forces, dtype=np.float64)[local_index],
    )


def displaced_atoms(atoms: Any, *, atom_index: int, axis: str, amplitude: float) -> Any:
    """One deterministic symmetric displacement mode applied to a copy."""

    if axis not in _AXIS_INDEX:
        raise TrainingDataInputError(f"Unknown displacement axis {axis!r}.")
    moved = atoms.copy()
    positions = np.array(moved.get_positions(), dtype=np.float64)
    if not 0 <= int(atom_index) < positions.shape[0]:
        raise TrainingDataInputError("Displacement atom index is outside the configuration.")
    positions[int(atom_index), _AXIS_INDEX[axis]] += float(amplitude)
    moved.set_positions(positions)
    return moved


def strained_atoms(atoms: Any, magnitude: float) -> Any:
    """Isotropic deterministic strain for periodic systems."""

    strained = atoms.copy()
    cell = np.array(strained.get_cell(), dtype=np.float64)
    fractional = np.array(strained.get_scaled_positions(wrap=False), dtype=np.float64)
    strained.set_cell(cell * (1.0 + float(magnitude)), scale_atoms=False)
    strained.set_scaled_positions(fractional)
    return strained


def minimum_image_delta(delta: np.ndarray, cell: np.ndarray, pbc: np.ndarray) -> np.ndarray:
    """Adapt the canonical general-cell neighbor owner to one frame."""

    from ...analysis._neighbors import minimum_image_vectors

    cell = np.asarray(cell, dtype=np.float64)
    pbc = np.asarray(pbc, dtype=bool)
    if not np.any(pbc) and abs(float(np.linalg.det(cell))) <= 1.0e-12:
        # Nonperiodic ASE structures may carry a zero cell.  There is no image
        # operation to perform, so avoid inventing a physical cell merely for
        # this direct-distance adapter.
        return np.asarray(delta, dtype=np.float64)
    vectors, _distances = minimum_image_vectors(delta, cell=cell, pbc=pbc)
    return np.asarray(vectors, dtype=np.float64)


def displacement_metrics(
    reference: Any,
    candidate: Any,
    *,
    atom_indices: Sequence[int] | None = None,
) -> tuple[float, float]:
    """``(rms, max)`` periodic displacement for an optional protected subset."""

    delta = np.asarray(candidate.get_positions(), dtype=np.float64) - np.asarray(
        reference.get_positions(), dtype=np.float64
    )
    delta = minimum_image_delta(
        delta,
        np.asarray(reference.get_cell(), dtype=np.float64),
        np.asarray(reference.get_pbc(), dtype=bool),
    )
    if atom_indices is not None:
        indices = tuple(int(value) for value in atom_indices)
        if len(set(indices)) != len(indices) or any(
            index < 0 or index >= delta.shape[0] for index in indices
        ):
            raise QualificationError(
                "The displacement metric atom_indices must be unique in-range atoms."
            )
        delta = delta[list(indices)]
    norms = np.sqrt(np.sum(delta * delta, axis=1))
    if norms.size == 0:
        return 0.0, 0.0
    return float(np.sqrt(np.mean(norms**2))), float(np.max(norms))


def bond_table(atoms: Any, *, cutoff_scale: float) -> dict[tuple[int, int], float]:
    """Canonical distance connectivity adapted to one ASE configuration.

    ``mdstats.analysis.atomic_connectivity`` owns cutoff enumeration and the
    general-cell minimum-image calculation.  This function is intentionally a
    narrow single-frame adapter that converts its authenticated edge keys into
    the legacy pair/distance mapping consumed by the P7 geometry reducers.
    """

    from ase.data import covalent_radii

    from ...analysis.atomic_connectivity import DistanceConnectivity, build_atomic_connectivity_state
    from ...analysis.cutoffs import PairCutoff, PairCutoffRegistry
    from ...collection import AtomisticFrameCollection
    from ...provenance import FrameCollectionProvenance

    numbers = np.asarray(atoms.get_atomic_numbers(), dtype=np.int32)
    positions = np.asarray(atoms.get_positions(), dtype=np.float64)
    if positions.shape[0] < 2:
        return {}
    cell = np.asarray(atoms.get_cell(), dtype=np.float64)
    pbc = np.asarray(atoms.get_pbc(), dtype=bool)
    if abs(float(np.linalg.det(cell))) <= 1.0e-12:
        # ASE's nonperiodic Atoms commonly carries a zero cell.  A large
        # synthetic cell preserves direct distances while satisfying the
        # canonical collection's nonsingular-cell invariant; pbc remains false
        # so the synthetic boundary has no physical meaning.
        cell = np.eye(3, dtype=np.float64) * 1.0e6
    fractional = positions @ np.linalg.inv(cell)
    collection = AtomisticFrameCollection(
        frame_semantics="ensemble",
        frame_ids=np.asarray([0], dtype=np.int64),
        atomic_numbers=numbers,
        masses=np.asarray(atoms.get_masses(), dtype=np.float64),
        pbc=pbc,
        steps=None,
        times=None,
        cells=cell.reshape(1, 3, 3),
        origins=np.zeros((1, 3), dtype=np.float64),
        fractional_positions=fractional.reshape(1, len(atoms), 3),
        provenance=FrameCollectionProvenance(
            source_format="ase-structure",
            source_files=(),
            velocity_source="unavailable",
            coordinate_normalization="native_unwrapped_cartesian",
            stress_source=None,
            units_source="ASE canonical geometry adapter",
        ),
    )
    unique_numbers = sorted({int(value) for value in numbers})
    cutoffs = [
        PairCutoff.manual(
            first,
            second,
            radius=float(cutoff_scale)
            * (float(covalent_radii[first]) + float(covalent_radii[second])),
            source_metadata={"owner": "qualification.geometry", "adapter": "canonical.atomic_connectivity"},
        )
        for index, first in enumerate(unique_numbers)
        for second in unique_numbers[index:]
    ]
    state = build_atomic_connectivity_state(
        collection,
        DistanceConnectivity(PairCutoffRegistry.from_cutoffs(cutoffs)),
        frame_index=0,
    )
    result: dict[tuple[int, int], float] = {}
    for endpoint, shift in zip(state.edge_atom_indices, state.edge_image_shifts, strict=True):
        first, second = int(endpoint[0]), int(endpoint[1])
        image = np.asarray(shift, dtype=np.float64) @ cell
        distance = float(np.linalg.norm(positions[second] + image - positions[first]))
        result[(min(first, second), max(first, second))] = distance
    return result


def angle_table(
    atoms: Any, bonds: Mapping[tuple[int, int], float]
) -> dict[tuple[int, int, int], float]:
    """Bond angles in degrees for every connected triplet, centre atom first."""

    neighbours: dict[int, list[int]] = {}
    for first, second in bonds:
        neighbours.setdefault(first, []).append(second)
        neighbours.setdefault(second, []).append(first)
    positions = np.asarray(atoms.get_positions(), dtype=np.float64)
    cell = np.asarray(atoms.get_cell(), dtype=np.float64)
    pbc = np.asarray(atoms.get_pbc(), dtype=bool)
    angles: dict[tuple[int, int, int], float] = {}
    for centre, partners in neighbours.items():
        ordered = sorted(partners)
        for first_index in range(len(ordered) - 1):
            for second_index in range(first_index + 1, len(ordered)):
                left, right = ordered[first_index], ordered[second_index]
                delta = minimum_image_delta(
                    np.array([positions[left] - positions[centre], positions[right] - positions[centre]]),
                    cell,
                    pbc,
                )
                left_norm = float(np.linalg.norm(delta[0]))
                right_norm = float(np.linalg.norm(delta[1]))
                if left_norm <= 0.0 or right_norm <= 0.0:
                    continue
                cosine = float(np.dot(delta[0], delta[1]) / (left_norm * right_norm))
                angles[(centre, left, right)] = float(
                    np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))
                )
    return angles


def paired_statistics(
    reference: Mapping[Any, float], candidate: Mapping[Any, float]
) -> tuple[float, float, int]:
    """``(rmse, max_abs_error, compared_count)`` over shared keys only."""

    shared = sorted(set(reference) & set(candidate))
    if not shared:
        return 0.0, 0.0, 0
    errors = np.asarray([candidate[key] - reference[key] for key in shared], dtype=np.float64)
    return (
        float(np.sqrt(np.mean(errors**2))),
        float(np.max(np.abs(errors))),
        len(shared),
    )


class _QualificationCalculator:
    """Adapter exposing the qualification prediction seam to ASE optimizers."""

    implemented_properties = ("energy", "forces", "free_energy")

    def __init__(self, evaluate: Callable[[Any], tuple[float, np.ndarray]]) -> None:
        self._evaluate = evaluate
        self.results: dict[str, Any] = {}
        self.atoms = None

    # ASE calculator protocol -------------------------------------------------
    def get_property(self, name: str, atoms: Any = None, allow_calculation: bool = True) -> Any:
        if atoms is None:
            raise QualificationError("The qualification calculator requires explicit atoms.")
        energy, forces = self._evaluate(atoms)
        self.results = {"energy": energy, "free_energy": energy, "forces": forces}
        if name not in self.results:
            raise QualificationError(f"Unsupported qualification property {name!r}.")
        return self.results[name]

    def get_potential_energy(self, atoms: Any = None, force_consistent: bool = False) -> float:
        return float(self.get_property("energy", atoms))

    def get_forces(self, atoms: Any = None) -> np.ndarray:
        return np.asarray(self.get_property("forces", atoms), dtype=np.float64)

    def get_stress(self, atoms: Any = None) -> np.ndarray:  # pragma: no cover - unused
        raise NotImplementedError

    def calculation_required(self, atoms: Any, quantities: Sequence[str]) -> bool:
        return True

    def check_state(self, atoms: Any, tol: float = 1.0e-15) -> list[str]:
        return ["positions"]


@dataclass(frozen=True, slots=True)
class RelaxationOutcome:
    relaxed: Any
    steps: int
    converged: bool
    final_maximum_force: float
    reason: str


def relax_fixed_cell(
    atoms: Any,
    evaluate: Callable[[Any], tuple[float, np.ndarray]],
    *,
    maximum_steps: int,
    force_convergence: float,
) -> RelaxationOutcome:
    """Deterministic fixed-cell relaxation through ASE's FIRE optimizer.

    The cell is held fixed on purpose: variable-cell relaxation is a different
    scientific claim and is not part of the accepted qualification design.
    """

    from ase.optimize import FIRE

    working = atoms.copy()
    working.calc = _QualificationCalculator(evaluate)
    optimizer = FIRE(working, logfile=None)
    reason = "converged"
    try:
        optimizer.run(fmax=float(force_convergence), steps=int(maximum_steps))
    except Exception as exc:  # noqa: BLE001 - the reason is qualification evidence
        reason = f"relaxation_failed: {type(exc).__name__}: {exc}"
        forces = np.zeros((len(working), 3), dtype=np.float64)
        return RelaxationOutcome(
            relaxed=working,
            steps=int(getattr(optimizer, "nsteps", 0)),
            converged=False,
            final_maximum_force=float("nan"),
            reason=reason,
        )
    _energy, forces = evaluate(working)
    maximum_force = float(np.max(np.sqrt(np.sum(np.asarray(forces) ** 2, axis=1)))) if len(working) else 0.0
    converged = maximum_force <= float(force_convergence)
    if not converged:
        reason = "step_budget_exhausted"
    working.calc = None
    return RelaxationOutcome(
        relaxed=working,
        steps=int(getattr(optimizer, "nsteps", 0)),
        converged=converged,
        final_maximum_force=maximum_force,
        reason=reason,
    )


__all__ = [
    "RelaxationOutcome",
    "angle_table",
    "atoms_for_frame",
    "bond_table",
    "displaced_atoms",
    "displacement_metrics",
    "labels_for_frame",
    "minimum_image_delta",
    "paired_statistics",
    "relax_fixed_cell",
    "strained_atoms",
]
