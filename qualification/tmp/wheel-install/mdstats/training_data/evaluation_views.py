"""Immutable, pre-indexed evaluation dataset views for MLFF checkpoint metrics.

OPT-EVAL3 separates Python/ASE label extraction from repeated metric reduction.  A
view is reconstructable execution evidence: it is keyed by the authenticated
monitor bytes plus the label/condition policy, and never replaces the source
monitor artifact.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Any, Sequence
import os

import numpy as np
from ase.data import chemical_symbols
from ase.stress import full_3x3_to_voigt_6_stress

from ._common import TrainingDataInputError, digest

EVALUATION_DATASET_VIEW_SCHEMA = "mdstats.evaluation-dataset-view.v1"
EVALUATION_DATASET_VIEW_POLICY_VERSION = "mdstats.mlff-opt-eval3.view.2026-08.v1"


@dataclass(frozen=True)
class EvaluationDatasetView:
    configuration_count: int
    atom_counts: np.ndarray
    force_offsets: np.ndarray
    reference_energies: np.ndarray
    reference_forces: np.ndarray
    atomic_numbers: np.ndarray
    focus_atomic_numbers: tuple[int, ...]
    focus_local_indices: tuple[tuple[np.ndarray, ...], ...]
    condition_labels: tuple[str, ...]
    condition_ids: np.ndarray
    reference_stresses: np.ndarray
    stress_present: np.ndarray

    def __post_init__(self) -> None:
        count = int(self.configuration_count)
        if count <= 0:
            raise TrainingDataInputError("Evaluation dataset is empty.")
        if self.atom_counts.shape != (count,) or np.any(self.atom_counts <= 0):
            raise TrainingDataInputError("Invalid evaluation atom-count array.")
        if self.force_offsets.shape != (count + 1,):
            raise TrainingDataInputError("Invalid evaluation force-offset array.")
        if int(self.force_offsets[0]) != 0 or np.any(np.diff(self.force_offsets) <= 0):
            raise TrainingDataInputError("Evaluation force offsets must be strictly increasing.")
        total_atoms = int(self.force_offsets[-1])
        if self.reference_forces.shape != (total_atoms, 3):
            raise TrainingDataInputError("Invalid evaluation reference-force array.")
        if self.atomic_numbers.shape != (total_atoms,):
            raise TrainingDataInputError("Invalid evaluation atomic-number array.")
        if self.reference_energies.shape != (count,):
            raise TrainingDataInputError("Invalid evaluation energy array.")
        if self.condition_ids.shape != (count,):
            raise TrainingDataInputError("Invalid evaluation condition-id array.")
        if self.reference_stresses.shape != (count, 6) or self.stress_present.shape != (count,):
            raise TrainingDataInputError("Invalid evaluation stress arrays.")
        if np.any(~np.isfinite(self.reference_energies)) or np.any(~np.isfinite(self.reference_forces)):
            raise TrainingDataInputError("Evaluation reference labels must be finite.")
        if np.any(~np.isfinite(self.reference_stresses[self.stress_present])):
            raise TrainingDataInputError("Evaluation reference stresses must be finite.")
        if len(self.focus_local_indices) != len(self.focus_atomic_numbers):
            raise TrainingDataInputError("Evaluation focus-index metadata is inconsistent.")
        if any(len(per_frame) != count for per_frame in self.focus_local_indices):
            raise TrainingDataInputError("Evaluation focus-index frame count is inconsistent.")

    @property
    def total_atom_count(self) -> int:
        return int(self.force_offsets[-1])

    @property
    def content_digest(self) -> str:
        # Array bytes are already bound to the authenticated source monitor used to
        # build/cache this view.  This digest documents only the immutable shape and
        # reduction policy identity, not a second scientific artifact identity.
        return digest(
            {
                "schema": EVALUATION_DATASET_VIEW_SCHEMA,
                "configuration_count": self.configuration_count,
                "total_atom_count": self.total_atom_count,
                "focus_atomic_numbers": list(self.focus_atomic_numbers),
                "condition_labels": list(self.condition_labels),
            }
        )


def build_evaluation_dataset_view(
    atoms_list: Sequence[Any],
    *,
    energy_key: str,
    forces_key: str,
    stress_key: str,
    focus_atomic_numbers: Sequence[int],
    condition_keys: Sequence[str],
) -> EvaluationDatasetView:
    """Extract labels and reduction metadata from ASE objects exactly once."""

    if not atoms_list:
        raise TrainingDataInputError("Evaluation dataset is empty.")
    count = len(atoms_list)
    atom_counts = np.asarray([len(atoms) for atoms in atoms_list], dtype=np.int64)
    if np.any(atom_counts <= 0):
        raise TrainingDataInputError("Evaluation configurations must contain atoms.")
    offsets = np.zeros(count + 1, dtype=np.int64)
    offsets[1:] = np.cumsum(atom_counts, dtype=np.int64)
    total_atoms = int(offsets[-1])
    energies = np.empty(count, dtype=np.float64)
    forces = np.empty((total_atoms, 3), dtype=np.float64)
    numbers = np.empty(total_atoms, dtype=np.int32)
    stresses = np.zeros((count, 6), dtype=np.float64)
    stress_present = np.zeros(count, dtype=np.bool_)
    condition_tuples: list[tuple[str, ...]] = []

    for index, atoms in enumerate(atoms_list):
        if energy_key not in atoms.info or forces_key not in atoms.arrays:
            raise TrainingDataInputError(
                "Evaluation dataset is missing required energy or force labels."
            )
        start = int(offsets[index])
        stop = int(offsets[index + 1])
        energies[index] = float(atoms.info[energy_key])
        reference_forces = np.asarray(atoms.arrays[forces_key], dtype=np.float64)
        if reference_forces.shape != (len(atoms), 3):
            raise TrainingDataInputError("Reference force labels must have shape (n_atoms, 3).")
        forces[start:stop] = reference_forces
        atomic_numbers = np.asarray(atoms.numbers, dtype=np.int32)
        if atomic_numbers.shape != (len(atoms),):
            raise TrainingDataInputError("Invalid evaluation atomic-number labels.")
        numbers[start:stop] = atomic_numbers
        if stress_key in atoms.info:
            reference_stress = np.asarray(atoms.info[stress_key], dtype=np.float64).reshape(-1)
            if reference_stress.shape != (6,):
                raise TrainingDataInputError("Reference stress labels must contain six Voigt components.")
            if np.any(~np.isfinite(reference_stress)):
                raise TrainingDataInputError("Reference stress labels must be finite.")
            stresses[index] = reference_stress
            stress_present[index] = True
        if condition_keys:
            condition_tuples.append(
                tuple(str(atoms.info.get(key, f"missing:{key}")) for key in condition_keys)
            )

    if np.any(~np.isfinite(energies)) or np.any(~np.isfinite(forces)):
        raise TrainingDataInputError("Evaluation reference energy/force labels must be finite.")

    if condition_keys:
        unique_conditions = tuple(sorted(set(condition_tuples)))
        condition_index = {value: index for index, value in enumerate(unique_conditions)}
        condition_ids = np.asarray([condition_index[value] for value in condition_tuples], dtype=np.int32)
        condition_labels = tuple("|".join(value) for value in unique_conditions)
    else:
        condition_ids = np.full(count, -1, dtype=np.int32)
        condition_labels = ()

    focus_local_indices: list[tuple[np.ndarray, ...]] = []
    for atomic_number in focus_atomic_numbers:
        per_frame: list[np.ndarray] = []
        for index in range(count):
            start = int(offsets[index])
            stop = int(offsets[index + 1])
            local = np.flatnonzero(numbers[start:stop] == int(atomic_number)).astype(np.int32)
            local.setflags(write=False)
            per_frame.append(local)
        focus_local_indices.append(tuple(per_frame))

    # Make the cached contract genuinely immutable.  Consumers create prediction
    # arrays separately and never mutate these source/reference buffers.
    arrays = (atom_counts, offsets, energies, forces, numbers, condition_ids, stresses, stress_present)
    for array in arrays:
        array.setflags(write=False)

    return EvaluationDatasetView(
        configuration_count=count,
        atom_counts=atom_counts,
        force_offsets=offsets,
        reference_energies=energies,
        reference_forces=forces,
        atomic_numbers=numbers,
        focus_atomic_numbers=tuple(int(value) for value in focus_atomic_numbers),
        focus_local_indices=tuple(focus_local_indices),
        condition_labels=condition_labels,
        condition_ids=condition_ids,
        reference_stresses=stresses,
        stress_present=stress_present,
    )


def metrics_from_prediction_view(
    view: EvaluationDatasetView,
    predictions: Sequence[Any],
    *,
    combined_energy_weight: float,
    combined_force_weight: float,
    combined_stress_weight: float,
) -> dict[str, Any]:
    """Pre-indexed metric reduction preserving the pre-OPT-EVAL3 definitions."""

    if len(predictions) != view.configuration_count:
        raise TrainingDataInputError("Prediction count does not match the evaluation dataset.")
    energy_abs_sum = 0.0
    force_squared_sum = 0.0
    force_component_count = 0
    stress_squared_sum = 0.0
    stress_component_count = 0
    focus_sse = np.zeros(len(view.focus_atomic_numbers), dtype=np.float64)
    focus_components = np.zeros(len(view.focus_atomic_numbers), dtype=np.int64)
    condition_sse = np.zeros(len(view.condition_labels), dtype=np.float64)
    condition_components = np.zeros(len(view.condition_labels), dtype=np.int64)
    worst_configuration_force_rmse = 0.0

    for index, prediction in enumerate(predictions):
        atom_count = int(view.atom_counts[index])
        start = int(view.force_offsets[index])
        stop = int(view.force_offsets[index + 1])
        predicted_energy = float(prediction.energy_ev)
        if not np.isfinite(predicted_energy):
            raise TrainingDataInputError("Predicted energies must be finite.")
        energy_abs_sum += abs(predicted_energy - float(view.reference_energies[index])) / atom_count

        predicted_force = np.asarray(prediction.forces_ev_per_angstrom, dtype=np.float64)
        if predicted_force.shape != (atom_count, 3):
            raise TrainingDataInputError("Predicted and reference force shapes differ.")
        if np.any(~np.isfinite(predicted_force)):
            raise TrainingDataInputError("Predicted forces must be finite.")
        error = predicted_force - view.reference_forces[start:stop]
        error_squared_sum = float(np.sum(error * error, dtype=np.float64))
        force_squared_sum += error_squared_sum
        force_component_count += int(error.size)

        for focus_index, per_frame_indices in enumerate(view.focus_local_indices):
            selected_indices = per_frame_indices[index]
            if selected_indices.size:
                selected = error[selected_indices]
                focus_sse[focus_index] += float(np.sum(selected * selected, dtype=np.float64))
                focus_components[focus_index] += int(selected.size)

        if view.condition_labels:
            condition_id = int(view.condition_ids[index])
            condition_sse[condition_id] += error_squared_sum
            condition_components[condition_id] += int(error.size)
        else:
            worst_configuration_force_rmse = max(
                worst_configuration_force_rmse,
                float(np.sqrt(error_squared_sum / int(error.size))),
            )

        if bool(view.stress_present[index]):
            if prediction.stress_ev_per_angstrom3 is None:
                raise TrainingDataInputError(
                    "Evaluation labels include stress but the model did not return stress."
                )
            predicted_stress = full_3x3_to_voigt_6_stress(
                np.asarray(prediction.stress_ev_per_angstrom3, dtype=np.float64)
            ).reshape(-1)
            if predicted_stress.shape != (6,) or np.any(~np.isfinite(predicted_stress)):
                raise TrainingDataInputError("Predicted and reference stress shapes differ.")
            stress_error = predicted_stress - view.reference_stresses[index]
            stress_squared_sum += float(np.sum(stress_error * stress_error, dtype=np.float64))
            stress_component_count += int(stress_error.size)

    if force_component_count == 0:
        raise TrainingDataInputError("Evaluation dataset contains no force components.")
    energy_mae = float(energy_abs_sum / view.configuration_count)
    force_rmse = float(np.sqrt(force_squared_sum / force_component_count))
    stress_rmse = (
        None
        if stress_component_count == 0
        else float(np.sqrt(stress_squared_sum / stress_component_count))
    )
    focus_metrics = tuple(
        (
            chemical_symbols[atomic_number],
            float(np.sqrt(focus_sse[index] / focus_components[index])),
        )
        for index, atomic_number in enumerate(view.focus_atomic_numbers)
        if int(focus_components[index]) > 0
    )
    condition_metrics = tuple(
        (
            label,
            float(np.sqrt(condition_sse[index] / condition_components[index])),
        )
        for index, label in enumerate(view.condition_labels)
        if int(condition_components[index]) > 0
    )
    worst_force_rmse = (
        max(value for _, value in condition_metrics)
        if condition_metrics
        else worst_configuration_force_rmse
    )

    combined = (
        float(combined_energy_weight) * energy_mae
        + float(combined_force_weight) * force_rmse
        + float(combined_stress_weight) * (0.0 if stress_rmse is None else stress_rmse)
    )
    return {
        "configuration_count": view.configuration_count,
        "energy_mae_ev_per_atom": energy_mae,
        "force_component_rmse_ev_per_angstrom": force_rmse,
        "focus_force_rmse_ev_per_angstrom": tuple(focus_metrics),
        "stress_rmse_ev_per_angstrom3": stress_rmse,
        "worst_condition_force_rmse_ev_per_angstrom": worst_force_rmse,
        "condition_force_rmse_ev_per_angstrom": condition_metrics,
        "combined_loss": combined,
    }


_VIEW_CACHE: "OrderedDict[tuple[Any, ...], tuple[EvaluationDatasetView, int]]" = OrderedDict()
_VIEW_CACHE_LOCK = RLock()
_VIEW_CACHE_BYTES = 0
_VIEW_CACHE_MAX_BYTES = max(
    0, int(os.environ.get("MDSTATS_MLFF_EVALUATION_VIEW_CACHE_BYTES", str(512 * 1024**2)))
)


def _view_resident_bytes(view: EvaluationDatasetView) -> int:
    return max(
        1,
        sum(
            int(array.nbytes)
            for array in (
                view.atom_counts,
                view.force_offsets,
                view.reference_energies,
                view.reference_forces,
                view.atomic_numbers,
                view.condition_ids,
                view.reference_stresses,
                view.stress_present,
            )
        )
        + sum(len(value) for value in view.condition_labels)
        + sum(int(indices.nbytes) for per_frame in view.focus_local_indices for indices in per_frame),
    )


def evaluation_view_cache_key(
    source_identity: Any,
    *,
    energy_key: str,
    forces_key: str,
    stress_key: str,
    focus_atomic_numbers: Sequence[int],
    condition_keys: Sequence[str],
) -> tuple[Any, ...]:
    return (
        EVALUATION_DATASET_VIEW_POLICY_VERSION,
        source_identity,
        str(energy_key),
        str(forces_key),
        str(stress_key),
        tuple(int(value) for value in focus_atomic_numbers),
        tuple(str(value) for value in condition_keys),
    )


def cached_evaluation_dataset_view(
    source_identity: Any,
    atoms_list: Sequence[Any],
    *,
    energy_key: str,
    forces_key: str,
    stress_key: str,
    focus_atomic_numbers: Sequence[int],
    condition_keys: Sequence[str],
) -> EvaluationDatasetView:
    """Return one immutable label/reduction view per authenticated monitor/policy."""

    global _VIEW_CACHE_BYTES
    key = evaluation_view_cache_key(
        source_identity,
        energy_key=energy_key,
        forces_key=forces_key,
        stress_key=stress_key,
        focus_atomic_numbers=focus_atomic_numbers,
        condition_keys=condition_keys,
    )
    with _VIEW_CACHE_LOCK:
        cached = _VIEW_CACHE.get(key)
        if cached is not None:
            _VIEW_CACHE.move_to_end(key)
            return cached[0]
        view = build_evaluation_dataset_view(
            atoms_list,
            energy_key=energy_key,
            forces_key=forces_key,
            stress_key=stress_key,
            focus_atomic_numbers=focus_atomic_numbers,
            condition_keys=condition_keys,
        )
        resident_bytes = _view_resident_bytes(view)
        if _VIEW_CACHE_MAX_BYTES <= 0 or resident_bytes > _VIEW_CACHE_MAX_BYTES:
            return view
        _VIEW_CACHE[key] = (view, resident_bytes)
        _VIEW_CACHE_BYTES += resident_bytes
        while _VIEW_CACHE and _VIEW_CACHE_BYTES > _VIEW_CACHE_MAX_BYTES:
            _, (_, removed_bytes) = _VIEW_CACHE.popitem(last=False)
            _VIEW_CACHE_BYTES -= removed_bytes
        return view


def clear_evaluation_dataset_view_cache() -> None:
    global _VIEW_CACHE_BYTES
    with _VIEW_CACHE_LOCK:
        _VIEW_CACHE.clear()
        _VIEW_CACHE_BYTES = 0


__all__ = [
    "EVALUATION_DATASET_VIEW_SCHEMA",
    "EVALUATION_DATASET_VIEW_POLICY_VERSION",
    "EvaluationDatasetView",
    "build_evaluation_dataset_view",
    "metrics_from_prediction_view",
    "cached_evaluation_dataset_view",
    "clear_evaluation_dataset_view_cache",
]
