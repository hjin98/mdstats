"""Internal frame-array access shared by DATA6 providers."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from ._common import TrainingDataInputError


def build_frame_array_index(
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
) -> dict[str, tuple[Any, Any, int]]:
    """Map frame UID to (record, FrameData, local frame index)."""

    result: dict[str, tuple[Any, Any, int]] = {}
    by_run: dict[str, dict[int, int]] = {}
    for run_id, frame_data in frame_data_by_run.items():
        source_indices = np.asarray(frame_data.source_frame_indices, dtype=np.int64)
        mapping = {int(value): index for index, value in enumerate(source_indices)}
        if len(mapping) != source_indices.size:
            raise TrainingDataInputError(
                f"FrameData for run {run_id!r} contains duplicate source indices."
            )
        by_run[str(run_id)] = mapping
    for record in frame_catalog.frames:
        if record.frame_uid in result:
            raise TrainingDataInputError("Frame catalog contains duplicate frame UIDs.")
        try:
            frame_data = frame_data_by_run[record.run_id]
            local_index = by_run[record.run_id][record.source_frame_index]
        except KeyError as exc:
            raise TrainingDataInputError(
                f"Frame arrays are missing for {record.run_id}:{record.source_frame_index}."
            ) from exc
        result[record.frame_uid] = (record, frame_data, local_index)
    return result


def ase_atoms_for_frame(record: Any, frame_data: Any, local_index: int):
    """Materialize one ASE Atoms object without attaching reference labels."""

    try:
        from ase import Atoms
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
        raise TrainingDataInputError("ASE is required to materialize model inputs.") from exc

    cell = np.asarray(frame_data.cells_angstrom[local_index], dtype=np.float64)
    fractional = np.asarray(
        frame_data.fractional_positions[local_index], dtype=np.float64
    )
    atoms = Atoms(
        numbers=np.asarray(frame_data.atomic_numbers, dtype=np.int32),
        scaled_positions=fractional,
        cell=cell,
        pbc=np.asarray(frame_data.pbc, dtype=np.bool_),
    )
    atoms.info["frame_uid"] = record.frame_uid
    atoms.info["run_id"] = record.run_id
    atoms.info["source_frame_index"] = int(record.source_frame_index)
    return atoms
