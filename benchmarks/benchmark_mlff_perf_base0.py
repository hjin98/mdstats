#!/usr/bin/env python3
"""Build the frozen PERF-BASE0 CPU/numerical oracle on supplied LTA data.

The benchmark intentionally exercises production exact kernels while keeping
host-dependent telemetry outside the scientific digest.  It does not fabricate
foundation-model, GPU, TRAIN2, or EVAL2 evidence when their model/runtime inputs
are absent.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import ase
from ase import Atoms
from ase.io import iread
from scipy.spatial import cKDTree

import mdstats
from mdstats.training_data._common import canonical_json, digest
from mdstats.training_data.performance_baseline import (
    PerfBase0ArrayReference,
    PerfBase0ArtifactIdentity,
    PerfBase0CorpusIdentity,
    PerfBase0JsonReference,
    PerfBase0Record,
    PerfBase0ScientificStage,
    PerfBase0StageMeter,
    render_perf_base0_markdown,
    write_perf_base0_record,
)
from mdstats.training_data.raw_features import minimum_image_displacements
from mdstats.training_data.selection import _fps_order_matrix
from mdstats.training_data.target_coverage import (
    TargetCoveragePolicy,
    _local_reference_radii,
    _robust_scales,
    _weighted_quantile,
)


SPECIES = (3, 8, 11, 13, 14, 19)
SPECIES_SYMBOL = {3: "Li", 8: "O", 11: "Na", 13: "Al", 14: "Si", 19: "K"}
MOBILE_SPECIES = (3, 11, 19)
TRAINING_FEATURE_NAMES = (
    "energy_per_atom_ev",
    "force_component_rms_ev_per_angstrom",
    "force_norm_mean_ev_per_angstrom",
    "force_norm_q90_ev_per_angstrom",
    "force_norm_q99_ev_per_angstrom",
    "force_norm_max_ev_per_angstrom",
    "stress_xx_ev_per_angstrom3",
    "stress_yy_ev_per_angstrom3",
    "stress_zz_ev_per_angstrom3",
    "stress_yz_ev_per_angstrom3",
    "stress_xz_ev_per_angstrom3",
    "stress_xy_ev_per_angstrom3",
    "pressure_ev_per_angstrom3",
    "stress_von_mises_ev_per_angstrom3",
    "volume_per_atom_angstrom3",
    "cell_a_angstrom",
    "cell_b_angstrom",
    "cell_c_angstrom",
    "cell_alpha_degree",
    "cell_beta_degree",
    "cell_gamma_degree",
    "fraction_li",
    "fraction_o",
    "fraction_na",
    "fraction_al",
    "fraction_si",
    "fraction_k",
    "mobile_fraction",
    "mobile_force_rms_ev_per_angstrom",
    "mobile_force_q99_ev_per_angstrom",
    "mobile_force_max_ev_per_angstrom",
)
SPECIES_FEATURE_NAMES = tuple(
    f"{SPECIES_SYMBOL[z].lower()}_{suffix}"
    for z in SPECIES
    for suffix in (
        "fraction",
        "force_rms_ev_per_angstrom",
        "force_q99_ev_per_angstrom",
        "force_max_ev_per_angstrom",
    )
)
REPLAY_FEATURE_NAMES = (
    "atom_count",
    "species_count",
    "atomic_number_mean",
    "atomic_number_std",
    "atomic_number_min",
    "atomic_number_max",
    "energy_per_atom_ev",
    "force_component_rms_ev_per_angstrom",
    "force_norm_mean_ev_per_angstrom",
    "force_norm_q99_ev_per_angstrom",
    "force_norm_max_ev_per_angstrom",
    "pressure_ev_per_angstrom3",
    "stress_von_mises_ev_per_angstrom3",
    "volume_per_atom_angstrom3",
    "periodic_axis_count",
)
BENCHMARK_POLICY = {
    "schema": "mdstats.perf-base0-lta-benchmark-policy.v1",
    "training_feature_names": list(TRAINING_FEATURE_NAMES),
    "species_feature_names": list(SPECIES_FEATURE_NAMES),
    "replay_feature_names": list(REPLAY_FEATURE_NAMES),
    "training_parser": "ase.io.iread(format=vasp-xml,index=:)",
    "replay_parser": "ase.io.iread(format=extxyz,index=:)",
    "correlation_unit": "one source file",
    "correlation_weighting": "equal mass per source file, then equal mass per valid frame",
    "coverage_beta": 1.0 / 128.0,
    "coverage_leave_one_out": True,
    "coverage_extent_quantiles": [0.01, 0.5, 0.99],
    "fps_tie_tolerance": 1.0e-12,
    "array_authority": "canonical little-endian C-order bytes",
}
BENCHMARK_POLICY_DIGEST = digest(BENCHMARK_POLICY)


@dataclass(slots=True)
class IngestedCorpus:
    frame_uids: tuple[str, ...]
    feature_matrix: np.ndarray
    source_indices: np.ndarray
    source_frame_counts: tuple[int, ...]
    atom_count: int
    species_values: np.ndarray | None = None
    species_missing_mask: np.ndarray | None = None
    split_names: tuple[str, ...] = ()


@dataclass(slots=True)
class CoverageFamilyResult:
    family_id: str
    feature_names: tuple[str, ...]
    global_indices: np.ndarray
    values: np.ndarray
    weights: np.ndarray
    scales: np.ndarray
    scaled: np.ndarray
    local_radii: np.ndarray
    quantiles: np.ndarray


def _von_mises(stress: np.ndarray) -> float:
    sxx, syy, szz, syz, sxz, sxy = np.asarray(stress, dtype=np.float64).reshape(6)
    value = 0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
    value += 3.0 * (sxy**2 + sxz**2 + syz**2)
    return float(math.sqrt(max(0.0, value)))


def _cell_lengths_angles(atoms: Atoms) -> tuple[np.ndarray, np.ndarray]:
    cell = np.asarray(atoms.cell.array, dtype=np.float64)
    lengths = np.linalg.norm(cell, axis=1)
    if np.any(lengths <= 0.0):
        raise ValueError("Encountered non-positive cell length.")
    a, b, c = cell
    angles = np.degrees(
        np.arccos(
            np.clip(
                np.array(
                    [
                        np.dot(b, c) / (lengths[1] * lengths[2]),
                        np.dot(a, c) / (lengths[0] * lengths[2]),
                        np.dot(a, b) / (lengths[0] * lengths[1]),
                    ],
                    dtype=np.float64,
                ),
                -1.0,
                1.0,
            )
        )
    )
    return lengths, angles


def _force_statistics(forces: np.ndarray) -> tuple[float, float, float, float, float]:
    matrix = np.asarray(forces, dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=1)
    return (
        float(np.sqrt(np.mean(matrix * matrix, dtype=np.float64))),
        float(np.mean(norms, dtype=np.float64)),
        float(np.quantile(norms, 0.90)),
        float(np.quantile(norms, 0.99)),
        float(np.max(norms)),
    )


def _training_frame_features(atoms: Atoms) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    atom_count = len(atoms)
    if atoms.calc is None:
        raise ValueError("VASP XML frame has no calculator results.")
    energy = float(atoms.get_potential_energy())
    forces = np.asarray(atoms.get_forces(), dtype=np.float64)
    stress = np.asarray(atoms.get_stress(voigt=True), dtype=np.float64)
    lengths, angles = _cell_lengths_angles(atoms)
    volume = float(atoms.get_volume())
    force_component_rms, force_mean, force_q90, force_q99, force_max = _force_statistics(forces)
    numbers = np.asarray(atoms.numbers, dtype=np.int64)
    fractions = np.array([np.count_nonzero(numbers == z) / atom_count for z in SPECIES], dtype=np.float64)
    mobile_mask = np.isin(numbers, np.asarray(MOBILE_SPECIES, dtype=np.int64))
    if not np.any(mobile_mask):
        raise ValueError("LTA target frame contains no Li/Na/K mobile species.")
    mobile_rms, _, _, mobile_q99, mobile_max = _force_statistics(forces[mobile_mask])
    feature = np.array(
        [
            energy / atom_count,
            force_component_rms,
            force_mean,
            force_q90,
            force_q99,
            force_max,
            *stress.tolist(),
            -float(np.mean(stress[:3], dtype=np.float64)),
            _von_mises(stress),
            volume / atom_count,
            *lengths.tolist(),
            *angles.tolist(),
            *fractions.tolist(),
            float(np.mean(mobile_mask)),
            mobile_rms,
            mobile_q99,
            mobile_max,
        ],
        dtype=np.float64,
    )
    if feature.shape != (len(TRAINING_FEATURE_NAMES),) or np.any(~np.isfinite(feature)):
        raise ValueError("Training feature extraction produced invalid values.")

    species_values = np.full((len(SPECIES), 4), np.nan, dtype=np.float64)
    species_missing = np.ones((len(SPECIES), 4), dtype=np.bool_)
    for row, z in enumerate(SPECIES):
        mask = numbers == z
        if not np.any(mask):
            continue
        rms, _, _, q99, maximum = _force_statistics(forces[mask])
        species_values[row] = (float(np.mean(mask)), rms, q99, maximum)
        species_missing[row] = False
    return feature, species_values.reshape(-1), species_missing.reshape(-1)


def ingest_training(paths: Sequence[Path], root: Path) -> IngestedCorpus:
    uids: list[str] = []
    features: list[np.ndarray] = []
    species_values: list[np.ndarray] = []
    species_missing: list[np.ndarray] = []
    source_indices: list[int] = []
    source_counts: list[int] = []
    atom_count = 0
    for source_index, path in enumerate(paths):
        count = 0
        relative = path.relative_to(root).as_posix()
        for frame_index, atoms in enumerate(iread(path, index=":", format="vasp-xml")):
            feature, per_species, missing = _training_frame_features(atoms)
            uids.append(f"{relative}#{frame_index:06d}")
            features.append(feature)
            species_values.append(per_species)
            species_missing.append(missing)
            source_indices.append(source_index)
            count += 1
            atom_count += len(atoms)
        if count == 0:
            raise ValueError(f"Training source contains no frames: {path!s}")
        source_counts.append(count)
    matrix = np.asarray(features, dtype=np.float64)
    species_matrix = np.asarray(species_values, dtype=np.float64)
    missing_matrix = np.asarray(species_missing, dtype=np.bool_)
    return IngestedCorpus(
        frame_uids=tuple(uids),
        feature_matrix=matrix,
        source_indices=np.asarray(source_indices, dtype=np.int32),
        source_frame_counts=tuple(source_counts),
        atom_count=atom_count,
        species_values=species_matrix,
        species_missing_mask=missing_matrix,
    )


def _replay_frame_features(atoms: Atoms) -> np.ndarray:
    numbers = np.asarray(atoms.numbers, dtype=np.int64)
    forces = np.asarray(atoms.arrays["REF_forces"], dtype=np.float64)
    stress = np.asarray(atoms.info["REF_stress"], dtype=np.float64).reshape(6)
    energy = float(atoms.info["REF_energy"])
    force_component_rms, force_mean, _, force_q99, force_max = _force_statistics(forces)
    volume = float(abs(np.linalg.det(np.asarray(atoms.cell.array, dtype=np.float64))))
    atom_count = len(atoms)
    result = np.array(
        [
            atom_count,
            len(np.unique(numbers)),
            float(np.mean(numbers, dtype=np.float64)),
            float(np.std(numbers, dtype=np.float64)),
            int(np.min(numbers)),
            int(np.max(numbers)),
            energy / atom_count,
            force_component_rms,
            force_mean,
            force_q99,
            force_max,
            -float(np.mean(stress[:3], dtype=np.float64)),
            _von_mises(stress),
            volume / atom_count,
            int(np.count_nonzero(atoms.pbc)),
        ],
        dtype=np.float64,
    )
    if np.any(~np.isfinite(result)):
        raise ValueError("Replay feature extraction produced invalid values.")
    return result


def ingest_replay(paths: Sequence[Path], root: Path) -> IngestedCorpus:
    uids: list[str] = []
    features: list[np.ndarray] = []
    source_indices: list[int] = []
    source_counts: list[int] = []
    split_names: list[str] = []
    atom_count = 0
    for source_index, path in enumerate(paths):
        count = 0
        relative = path.relative_to(root).as_posix()
        split_name = path.stem.removeprefix("replay_")
        split_names.append(split_name)
        for frame_index, atoms in enumerate(iread(path, index=":", format="extxyz")):
            uids.append(f"{relative}#{frame_index:06d}")
            features.append(_replay_frame_features(atoms))
            source_indices.append(source_index)
            count += 1
            atom_count += len(atoms)
        if count == 0:
            raise ValueError(f"Replay source contains no frames: {path!s}")
        source_counts.append(count)
    return IngestedCorpus(
        frame_uids=tuple(uids),
        feature_matrix=np.asarray(features, dtype=np.float64),
        source_indices=np.asarray(source_indices, dtype=np.int32),
        source_frame_counts=tuple(source_counts),
        atom_count=atom_count,
        split_names=tuple(split_names),
    )


def _balanced_source_weights(source_indices: np.ndarray) -> np.ndarray:
    source_indices = np.asarray(source_indices, dtype=np.int64)
    unique, counts = np.unique(source_indices, return_counts=True)
    if unique.size == 0:
        raise ValueError("Cannot weight an empty family.")
    per_unit_mass = 1.0 / unique.size
    weights = np.zeros(source_indices.size, dtype=np.float64)
    for source, count in zip(unique, counts, strict=True):
        weights[source_indices == source] = per_unit_mass / int(count)
    weights /= np.sum(weights, dtype=np.float64)
    return weights


def _family(
    family_id: str,
    feature_names: Sequence[str],
    global_indices: np.ndarray,
    values: np.ndarray,
    source_indices: np.ndarray,
    *,
    workers: int,
    block_size: int,
) -> CoverageFamilyResult:
    rows = np.asarray(global_indices, dtype=np.int64)
    matrix = np.asarray(values, dtype=np.float64)
    weights = _balanced_source_weights(np.asarray(source_indices, dtype=np.int64)[rows])
    scales = _robust_scales(matrix, weights, minimum=1.0e-12)
    scaled = matrix / scales[None, :]
    radii = _local_reference_radii(
        scaled,
        weights,
        beta=1.0 / 128.0,
        leave_one_out=True,
        block_size=block_size,
        query_workers=workers,
    )
    quantiles = np.empty((3, matrix.shape[1]), dtype=np.float64)
    for column in range(matrix.shape[1]):
        quantiles[:, column] = [
            _weighted_quantile(matrix[:, column], weights, q) for q in (0.01, 0.5, 0.99)
        ]
    return CoverageFamilyResult(
        family_id=family_id,
        feature_names=tuple(feature_names),
        global_indices=rows,
        values=matrix,
        weights=weights,
        scales=scales,
        scaled=scaled,
        local_radii=radii,
        quantiles=quantiles,
    )


def build_realistic_families(
    training: IngestedCorpus,
    *,
    workers: int,
    block_size: int,
) -> list[CoverageFamilyResult]:
    matrix = training.feature_matrix
    all_rows = np.arange(matrix.shape[0], dtype=np.int64)
    definitions = [
        (
            "target_labels",
            (0, 1, 3, 4, 5, 12, 13),
        ),
        ("stress_tensor", (6, 7, 8, 9, 10, 11)),
        ("cell_geometry", (14, 15, 16, 17, 18, 19, 20)),
        ("mobile_labels", (27, 28, 29, 30)),
    ]
    result = [
        _family(
            family_id,
            tuple(TRAINING_FEATURE_NAMES[index] for index in columns),
            all_rows,
            matrix[:, np.asarray(columns, dtype=np.int64)],
            training.source_indices,
            workers=workers,
            block_size=block_size,
        )
        for family_id, columns in definitions
    ]
    assert training.species_values is not None
    assert training.species_missing_mask is not None
    species_matrix = training.species_values
    missing = training.species_missing_mask

    framework_columns: list[int] = []
    framework_names: list[str] = []
    for species_row, z in enumerate((8, 13, 14)):
        base = SPECIES.index(z) * 4
        framework_columns.extend((base + 1, base + 2))
        framework_names.extend(
            (
                f"{SPECIES_SYMBOL[z].lower()}_force_rms_ev_per_angstrom",
                f"{SPECIES_SYMBOL[z].lower()}_force_q99_ev_per_angstrom",
            )
        )
    framework_column_array = np.asarray(framework_columns, dtype=np.int64)
    framework_valid = ~np.any(missing[:, framework_column_array], axis=1)
    framework_rows = np.flatnonzero(framework_valid)
    result.append(
        _family(
            "framework_species_forces",
            tuple(framework_names),
            framework_rows,
            species_matrix[np.ix_(framework_rows, framework_column_array)],
            training.source_indices,
            workers=workers,
            block_size=block_size,
        )
    )
    for z in MOBILE_SPECIES:
        base = SPECIES.index(z) * 4
        columns = np.arange(base, base + 4, dtype=np.int64)
        valid = ~np.any(missing[:, columns], axis=1)
        rows = np.flatnonzero(valid)
        result.append(
            _family(
                f"{SPECIES_SYMBOL[z].lower()}_species_force",
                tuple(SPECIES_FEATURE_NAMES[index] for index in columns),
                rows,
                species_matrix[np.ix_(rows, columns)],
                training.source_indices,
                workers=workers,
                block_size=block_size,
            )
        )
    return result


def _coverage_reports(
    families: Sequence[CoverageFamilyResult],
    selected_global_order: Sequence[int],
    rung_sizes: Sequence[int],
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for rung_size in rung_sizes:
        selected_set = set(int(value) for value in selected_global_order[:rung_size])
        family_reports: list[dict[str, Any]] = []
        for family in families:
            representative_rows = np.asarray(
                [row for row, global_index in enumerate(family.global_indices) if int(global_index) in selected_set],
                dtype=np.int64,
            )
            if representative_rows.size == 0:
                covered_mass = 0.0
                extent_failures = list(family.feature_names)
            else:
                tree = cKDTree(family.scaled[representative_rows])
                distances, _ = tree.query(family.scaled, k=1, workers=1)
                normalized = np.asarray(distances, dtype=np.float64) / math.sqrt(family.scaled.shape[1])
                covered = normalized <= family.local_radii + 1.0e-12 * np.maximum(
                    1.0, family.local_radii
                )
                covered_mass = float(np.sum(family.weights[covered], dtype=np.float64))
                selected_values = family.values[representative_rows]
                extent_failures = []
                for column, feature_name in enumerate(family.feature_names):
                    if float(np.min(selected_values[:, column])) > family.quantiles[0, column] + 1.0e-12:
                        extent_failures.append(f"{feature_name}:lower")
                    if float(np.max(selected_values[:, column])) < family.quantiles[2, column] - 1.0e-12:
                        extent_failures.append(f"{feature_name}:upper")
            family_reports.append(
                {
                    "family_id": family.family_id,
                    "reference_elements": int(family.values.shape[0]),
                    "representative_elements": int(representative_rows.size),
                    "covered_reference_mass": covered_mass,
                    "coverage_passed_0.95": covered_mass + 1.0e-12 >= 0.95,
                    "extent_failures": extent_failures,
                }
            )
        reports.append(
            {
                "rung_size": int(rung_size),
                "minimum_family_coverage": min(item["covered_reference_mass"] for item in family_reports),
                "all_family_coverage_passed_0.95": all(
                    item["coverage_passed_0.95"] for item in family_reports
                ),
                "all_family_extent_passed": all(not item["extent_failures"] for item in family_reports),
                "families": family_reports,
            }
        )
    return reports


def _file_identities(paths: Iterable[Path], root: Path, *, role: str) -> tuple[PerfBase0ArtifactIdentity, ...]:
    return tuple(
        PerfBase0ArtifactIdentity.from_file(
            path,
            logical_path=path.relative_to(root).as_posix(),
            role=role,
        )
        for path in sorted(paths)
    )


def _source_artifact(path: Path | None, logical_path: str, role: str) -> PerfBase0ArtifactIdentity | None:
    if path is None:
        return None
    return PerfBase0ArtifactIdentity.from_file(path, logical_path=logical_path, role=role)


def _compact_reference(corpus_digest: str, workers: int) -> tuple[PerfBase0ScientificStage, int]:
    uids = ("u03", "u01", "u04", "u00", "u02", "u05")
    points = np.array(
        [
            [0.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
            [1.0, 1.0],
            [0.25, 0.75],
            [0.75, 0.25],
        ],
        dtype=np.float64,
    )
    weights = np.array([1, 2, 1, 3, 2, 1], dtype=np.float64)
    weights /= np.sum(weights)
    scales = _robust_scales(points, weights, minimum=1.0e-12)
    scaled = points / scales[None, :]
    radii_serial = _local_reference_radii(
        scaled,
        weights,
        beta=0.25,
        leave_one_out=True,
        block_size=3,
        query_workers=1,
    )
    radii_workers = _local_reference_radii(
        scaled,
        weights,
        beta=0.25,
        leave_one_out=True,
        block_size=3,
        query_workers=workers,
    )
    order = _fps_order_matrix(uids, scaled, (), 1.0e-12, limit=len(uids))
    stage = PerfBase0ScientificStage(
        stage_id="compact_regression",
        algorithm_ids=(
            "mdstats.target_coverage._robust_scales.v1",
            "mdstats.target_coverage._local_reference_radii.exact",
            "mdstats.selection._fps_order_matrix.exact-incremental",
        ),
        corpus_digests=(corpus_digest,),
        policy_digests=(BENCHMARK_POLICY_DIGEST,),
        subset_rule="complete six-point deterministic synthetic corpus",
        arrays=(
            PerfBase0ArrayReference.from_array("points", points),
            PerfBase0ArrayReference.from_array("weights", weights),
            PerfBase0ArrayReference.from_array("scales", scales),
            PerfBase0ArrayReference.from_array("local_radii_workers_1", radii_serial),
            PerfBase0ArrayReference.from_array("local_radii_workers_n", radii_workers),
        ),
        json_references=(
            PerfBase0JsonReference.from_value("frame_uids", list(uids)),
            PerfBase0JsonReference.from_value("fps_order", order),
            PerfBase0JsonReference.from_value(
                "worker_invariance",
                {
                    "query_workers": workers,
                    "array_equal": bool(np.array_equal(radii_serial, radii_workers)),
                    "maximum_absolute_difference": float(np.max(np.abs(radii_serial - radii_workers))),
                },
            ),
        ),
        notes=("Compact old/new exact byte and decision oracle.",),
    )
    return stage, int(points.shape[0])


def _adversarial_reference(corpus_digest: str, workers: int) -> tuple[PerfBase0ScientificStage, int]:
    duplicate_points = np.array(
        [[0.0, 0.0], [0.0, 0.0], [1.0, 0.0], [1.0, 0.0], [0.5, 0.0], [0.5, 1.0e-13]],
        dtype=np.float64,
    )
    nonuniform_weights = np.array([0.04, 0.16, 0.08, 0.24, 0.18, 0.30], dtype=np.float64)
    duplicate_radii = _local_reference_radii(
        duplicate_points,
        nonuniform_weights,
        beta=0.25,
        leave_one_out=True,
        block_size=2,
        query_workers=workers,
    )
    tie_uids = ("tie-b", "tie-a", "tie-d", "tie-c", "near-z", "near-y")
    tie_points = np.array(
        [
            [-1.0, 0.0],
            [1.0, 0.0],
            [0.0, -1.0],
            [0.0, 1.0],
            [0.0, 1.0 + 4.0e-13],
            [0.0, -1.0 - 4.0e-13],
        ],
        dtype=np.float64,
    )
    tie_order = _fps_order_matrix(tie_uids, tie_points, (), 1.0e-12, limit=len(tie_uids))
    missing_values = np.array(
        [
            [1.0, 0.0, 4.0],
            [2.0, 3.0, 0.0],
            [3.0, 0.0, 6.0],
            [4.0, 5.0, 7.0],
        ],
        dtype=np.float64,
    )
    missing_mask = np.array(
        [
            [False, True, False],
            [False, False, True],
            [False, True, False],
            [False, False, False],
        ],
        dtype=np.bool_,
    )
    family_membership = np.flatnonzero(~np.any(missing_mask[:, (0, 2)], axis=1)).astype(np.int64)
    cell = np.array([[10.0, 0.0, 0.0], [2.0, 9.0, 0.0], [0.0, 1.0, 8.0]], dtype=np.float64)
    mic = minimum_image_displacements(
        np.array([[0.95, 0.95, 0.95], [0.0, 0.5, 0.5]], dtype=np.float64),
        np.array([[0.05, 0.05, 0.05], [1.0, 0.5, 0.5]], dtype=np.float64),
        cell=cell,
        pbc=np.array([True, True, False], dtype=np.bool_),
    )
    stage = PerfBase0ScientificStage(
        stage_id="adversarial_geometry_statistics",
        algorithm_ids=(
            "mdstats.target_coverage._local_reference_radii.exact",
            "mdstats.selection._fps_order_matrix.exact-incremental",
            "mdstats.raw_features.minimum_image_displacements.v1",
        ),
        corpus_digests=(corpus_digest,),
        policy_digests=(BENCHMARK_POLICY_DIGEST,),
        subset_rule="complete frozen adversarial duplicate/tie/weight/mask/triclinic-MIC corpus",
        arrays=(
            PerfBase0ArrayReference.from_array("duplicate_points", duplicate_points),
            PerfBase0ArrayReference.from_array("nonuniform_weights", nonuniform_weights),
            PerfBase0ArrayReference.from_array("duplicate_local_radii", duplicate_radii),
            PerfBase0ArrayReference.from_array("tie_points", tie_points),
            PerfBase0ArrayReference.from_array("missing_values_zero_filled", missing_values),
            PerfBase0ArrayReference.from_array("missing_mask", missing_mask),
            PerfBase0ArrayReference.from_array("family_membership", family_membership),
            PerfBase0ArrayReference.from_array("triclinic_mic_displacements", mic),
        ),
        json_references=(
            PerfBase0JsonReference.from_value("tie_uids", list(tie_uids)),
            PerfBase0JsonReference.from_value("tie_fps_order", tie_order),
            PerfBase0JsonReference.from_value(
                "adversarial_cases",
                [
                    "duplicate feature points",
                    "exact and near distance ties",
                    "nonuniform correlation-unit weights",
                    "missing-family masks",
                    "triclinic periodic/nonperiodic edge displacements",
                ],
            ),
        ),
    )
    return stage, int(duplicate_points.shape[0] + tie_points.shape[0] + missing_values.shape[0] + 4)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-root", type=Path, required=True)
    parser.add_argument("--replay-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--dependencies-archive", type=Path)
    parser.add_argument("--training-archive", type=Path)
    parser.add_argument("--replay-archive", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--radius-block-size", type=int, default=1024)
    parser.add_argument("--fps-limit", type=int, default=1024)
    parser.add_argument("--baseline-id", default="lta-perf-base0-cloud-cpu-2026-08-15")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    training_root = args.training_root.resolve()
    replay_root = args.replay_root.resolve()
    workers = max(1, int(args.workers))
    block_size = max(1, int(args.radius_block_size))
    fps_limit = max(1, int(args.fps_limit))

    training_paths = tuple(sorted(training_root.glob("*.xml")))
    replay_primary_paths = tuple(
        replay_root / name
        for name in ("replay_train.extxyz", "replay_monitor.extxyz", "replay_outliers.extxyz")
    )
    if not training_paths or any(not path.is_file() for path in replay_primary_paths):
        raise SystemExit("Training XML files or authoritative replay split files are missing.")
    replay_all_paths = tuple(sorted(path for path in replay_root.iterdir() if path.is_file()))

    telemetry = []
    with PerfBase0StageMeter(
        "input_identity",
        worker_settings={"sha256_workers": 1},
    ) as meter:
        training_artifacts = _file_identities(training_paths, training_root, role="target_vasp_xml")
        replay_artifacts = _file_identities(replay_all_paths, replay_root, role="replay_package_artifact")
        source_artifacts = tuple(
            item
            for item in (
                _source_artifact(args.source_archive, "source/mdstats-source-package.zip", "source_package"),
                _source_artifact(args.dependencies_archive, "source/dependencies.tar.gz", "dependency_bundle"),
                _source_artifact(args.training_archive, "source/training_LTA.tar.gz", "target_archive"),
                _source_artifact(args.replay_archive, "source/LTA_replay.zip", "replay_archive"),
            )
            if item is not None
        )
    identity_count = len(training_artifacts) + len(replay_artifacts) + len(source_artifacts)
    telemetry.append(
        meter.telemetry(
            throughput_count=identity_count,
            throughput_unit="artifacts",
            events=("SHA-256 byte identity; paths normalized relative to corpus roots",),
        )
    )

    with PerfBase0StageMeter(
        "training_ingest",
        worker_settings={"parser_processes": 1, "parser_threads": 1},
    ) as meter:
        training = ingest_training(training_paths, training_root)
    training_temp = (
        training.feature_matrix.nbytes
        + training.source_indices.nbytes
        + (0 if training.species_values is None else training.species_values.nbytes)
        + (0 if training.species_missing_mask is None else training.species_missing_mask.nbytes)
    )
    telemetry.append(
        meter.telemetry(
            throughput_count=len(training.frame_uids),
            throughput_unit="frames",
            temporary_array_bytes=training_temp,
            events=("Sequential ASE VASP-XML streaming parse",),
        )
    )

    with PerfBase0StageMeter(
        "replay_ingest",
        worker_settings={"parser_processes": 1, "parser_threads": 1},
    ) as meter:
        replay = ingest_replay(replay_primary_paths, replay_root)
    replay_temp = replay.feature_matrix.nbytes + replay.source_indices.nbytes
    telemetry.append(
        meter.telemetry(
            throughput_count=len(replay.frame_uids),
            throughput_unit="frames",
            temporary_array_bytes=replay_temp,
            events=("Sequential ASE ExtXYZ streaming parse of train/monitor/outlier split",),
        )
    )

    target_corpus = PerfBase0CorpusIdentity.build(
        corpus_id="lta_target_complete",
        role="realistic complete target-development source corpus",
        selection_rule="all frames from all 27 supplied LTA VASP XML files; no frame subsampling",
        artifacts=training_artifacts,
        frame_count=len(training.frame_uids),
        atom_count=training.atom_count,
        source_unit_count=len(training_paths),
        metadata={
            "feature_policy_digest": BENCHMARK_POLICY_DIGEST,
            "source_frame_counts": list(training.source_frame_counts),
            "species_atomic_numbers": list(SPECIES),
        },
    )
    replay_summary_path = replay_root / "replay_summary.json"
    replay_summary = json.loads(replay_summary_path.read_text(encoding="utf-8"))
    replay_corpus = PerfBase0CorpusIdentity.build(
        corpus_id="lta_replay_authoritative_splits",
        role="replay train/monitor/outlier materialization with complete supplied provenance package",
        selection_rule="all frames from replay_train, replay_monitor, and replay_outliers; package identities include every supplied replay artifact",
        artifacts=replay_artifacts,
        frame_count=len(replay.frame_uids),
        atom_count=replay.atom_count,
        source_unit_count=len(replay_primary_paths),
        metadata={
            "source_frame_counts": list(replay.source_frame_counts),
            "split_names": list(replay.split_names),
            "summary": replay_summary,
        },
    )
    synthetic_policy_bytes = canonical_json(BENCHMARK_POLICY).encode("utf-8")
    synthetic_artifact = PerfBase0ArtifactIdentity(
        logical_path="synthetic/perf-base0-fixtures.json",
        role="deterministic generated fixture specification",
        byte_count=len(synthetic_policy_bytes),
        sha256=digest(BENCHMARK_POLICY),
    )
    synthetic_corpus = PerfBase0CorpusIdentity.build(
        corpus_id="perf_base0_compact_adversarial",
        role="compact deterministic and adversarial numerical regression corpus",
        selection_rule="complete in-code fixture; no random generation",
        artifacts=(synthetic_artifact,),
        frame_count=26,
        atom_count=0,
        source_unit_count=1,
        metadata={"benchmark_policy": BENCHMARK_POLICY},
    )

    stages: list[PerfBase0ScientificStage] = []
    stages.append(
        PerfBase0ScientificStage(
            stage_id="input_identity",
            algorithm_ids=("sha256-streamed-file-bytes",),
            corpus_digests=(
                target_corpus.content_digest,
                replay_corpus.content_digest,
                synthetic_corpus.content_digest,
            ),
            policy_digests=(BENCHMARK_POLICY_DIGEST,),
            subset_rule="complete supplied source, target, replay, dependency artifact inventory",
            json_references=(
                PerfBase0JsonReference.from_value(
                    "source_artifacts", [item.to_dict() for item in source_artifacts]
                ),
                PerfBase0JsonReference.from_value(
                    "target_artifacts", [item.to_dict() for item in training_artifacts]
                ),
                PerfBase0JsonReference.from_value(
                    "replay_artifacts", [item.to_dict() for item in replay_artifacts]
                ),
            ),
        )
    )
    assert training.species_values is not None
    assert training.species_missing_mask is not None
    stages.append(
        PerfBase0ScientificStage(
            stage_id="training_ingest",
            algorithm_ids=(f"ase-{ase.__version__}", "perf-base0-lta-label-summary.v1"),
            corpus_digests=(target_corpus.content_digest,),
            policy_digests=(BENCHMARK_POLICY_DIGEST,),
            subset_rule=f"complete {len(training_paths)}-file LTA target corpus",
            arrays=(
                PerfBase0ArrayReference.from_array("frame_feature_matrix", training.feature_matrix),
                PerfBase0ArrayReference.from_array(
                    "species_feature_values_zero_filled",
                    np.where(training.species_missing_mask, 0.0, training.species_values),
                ),
                PerfBase0ArrayReference.from_array("species_missing_mask", training.species_missing_mask),
                PerfBase0ArrayReference.from_array("source_indices", training.source_indices),
            ),
            json_references=(
                PerfBase0JsonReference.from_value("frame_uids", list(training.frame_uids)),
                PerfBase0JsonReference.from_value("feature_names", list(TRAINING_FEATURE_NAMES)),
                PerfBase0JsonReference.from_value("species_feature_names", list(SPECIES_FEATURE_NAMES)),
                PerfBase0JsonReference.from_value(
                    "source_frame_counts", list(training.source_frame_counts)
                ),
            ),
            notes=("Feature summaries retain target labels, stress, cell, composition, and species-resolved force tails.",),
        )
    )
    stages.append(
        PerfBase0ScientificStage(
            stage_id="replay_ingest",
            algorithm_ids=("ase-extxyz-reader", "perf-base0-replay-label-summary.v1"),
            corpus_digests=(replay_corpus.content_digest,),
            policy_digests=(BENCHMARK_POLICY_DIGEST,),
            subset_rule="complete authoritative replay train/monitor/outlier split materialization",
            arrays=(
                PerfBase0ArrayReference.from_array("replay_feature_matrix", replay.feature_matrix),
                PerfBase0ArrayReference.from_array("replay_source_indices", replay.source_indices),
            ),
            json_references=(
                PerfBase0JsonReference.from_value("replay_frame_uids", list(replay.frame_uids)),
                PerfBase0JsonReference.from_value("replay_feature_names", list(REPLAY_FEATURE_NAMES)),
                PerfBase0JsonReference.from_value("replay_summary", replay_summary),
            ),
        )
    )

    with PerfBase0StageMeter(
        "compact_regression",
        worker_settings={"ckdtree_query_workers": workers},
    ) as meter:
        compact_stage, compact_count = _compact_reference(synthetic_corpus.content_digest, workers)
    telemetry.append(
        meter.telemetry(
            throughput_count=compact_count,
            throughput_unit="reference_elements",
            temporary_array_bytes=sum(item.byte_count for item in compact_stage.arrays),
        )
    )
    stages.append(compact_stage)

    with PerfBase0StageMeter(
        "adversarial_geometry_statistics",
        worker_settings={"ckdtree_query_workers": workers},
    ) as meter:
        adversarial_stage, adversarial_count = _adversarial_reference(
            synthetic_corpus.content_digest, workers
        )
    telemetry.append(
        meter.telemetry(
            throughput_count=adversarial_count,
            throughput_unit="adversarial_elements",
            temporary_array_bytes=sum(item.byte_count for item in adversarial_stage.arrays),
        )
    )
    stages.append(adversarial_stage)

    with PerfBase0StageMeter(
        "target_data2b_exact_radii",
        worker_settings={
            "ckdtree_query_workers": workers,
            "row_block_size": block_size,
            "coverage_beta": 1.0 / 128.0,
            "leave_one_out": True,
        },
    ) as meter:
        families = build_realistic_families(training, workers=workers, block_size=block_size)
    family_element_count = sum(item.values.shape[0] for item in families)
    maximum_family_temp = max(
        item.values.nbytes
        + item.scaled.nbytes
        + item.weights.nbytes
        + item.local_radii.nbytes
        for item in families
    )
    telemetry.append(
        meter.telemetry(
            throughput_count=family_element_count,
            throughput_unit="family-elements",
            temporary_array_bytes=maximum_family_temp,
            events=(
                "Exact cKDTree neighbor order and exact weighted cumulative mass",
                "Temporary bytes report retained major NumPy arrays; SciPy internal tree/query allocation is reflected by sampled RSS",
            ),
        )
    )
    family_arrays: list[PerfBase0ArrayReference] = []
    family_catalog: list[dict[str, Any]] = []
    for family in families:
        prefix = family.family_id
        family_arrays.extend(
            (
                PerfBase0ArrayReference.from_array(f"{prefix}.frame_indices", family.global_indices),
                PerfBase0ArrayReference.from_array(f"{prefix}.values", family.values),
                PerfBase0ArrayReference.from_array(f"{prefix}.weights", family.weights),
                PerfBase0ArrayReference.from_array(f"{prefix}.scales", family.scales),
                PerfBase0ArrayReference.from_array(f"{prefix}.local_radii", family.local_radii),
                PerfBase0ArrayReference.from_array(f"{prefix}.quantiles_q01_q50_q99", family.quantiles),
            )
        )
        family_catalog.append(
            {
                "family_id": family.family_id,
                "feature_names": list(family.feature_names),
                "element_count": int(family.values.shape[0]),
                "feature_count": int(family.values.shape[1]),
                "source_unit_count": int(np.unique(training.source_indices[family.global_indices]).size),
            }
        )
    target_policy = TargetCoveragePolicy()
    stages.append(
        PerfBase0ScientificStage(
            stage_id="target_data2b_exact_radii",
            algorithm_ids=(
                "mdstats.target_coverage._robust_scales.v1",
                "mdstats.target_coverage._weighted_quantile.mergesort",
                "mdstats.target_coverage._local_reference_radii.TARGET-DATA2B-PERF1",
            ),
            corpus_digests=(target_corpus.content_digest,),
            policy_digests=(target_policy.policy_digest, BENCHMARK_POLICY_DIGEST),
            subset_rule=(
                "complete target corpus for target/stress/cell/mobile/framework-force families; "
                "complete valid-frame subsets for Li/Na/K species-force families; no reference subsampling"
            ),
            arrays=tuple(family_arrays),
            json_references=(
                PerfBase0JsonReference.from_value("family_catalog", family_catalog),
                PerfBase0JsonReference.from_value("family_order", [item.family_id for item in families]),
            ),
            notes=(
                "This realistic CPU oracle covers exact TARGET-DATA2B statistics/radii on label/cell/species families derivable from supplied labels.",
                "DATA6 structural descriptors and foundation residual families are unavailable without the MH-1 checkpoint and campaign DATA4-DATA6 authorities.",
            ),
        )
    )

    full_weights = _balanced_source_weights(training.source_indices)
    full_scales = _robust_scales(training.feature_matrix, full_weights, minimum=1.0e-12)
    fused = training.feature_matrix / full_scales[None, :]
    fused /= math.sqrt(float(fused.shape[1]))
    fps_limit = min(fps_limit, fused.shape[0])
    rung_sizes = tuple(
        sorted(
            set(
                min(fps_limit, value)
                for value in (128, 256, 512, 1024, fps_limit)
                if min(fps_limit, value) > 0
            )
        )
    )
    with PerfBase0StageMeter(
        "target_data2c_exact_fps",
        worker_settings={
            "fps_processes": 1,
            "blas_threads_observed_in_environment": True,
            "coverage_query_workers": 1,
            "fps_limit": fps_limit,
        },
    ) as meter:
        fps_order_uids = _fps_order_matrix(
            training.frame_uids,
            fused,
            (),
            1.0e-12,
            limit=fps_limit,
        )
        uid_to_index = {uid: index for index, uid in enumerate(training.frame_uids)}
        fps_order_indices = np.asarray([uid_to_index[uid] for uid in fps_order_uids], dtype=np.int64)
        coverage_reports = _coverage_reports(families, fps_order_indices, rung_sizes)
    fps_temp = fused.nbytes + full_scales.nbytes + training.feature_matrix.shape[0] * 9
    telemetry.append(
        meter.telemetry(
            throughput_count=fps_limit,
            throughput_unit="selections",
            temporary_array_bytes=fps_temp,
            events=(
                "Exact incremental maximin FPS; UID lexical tie break",
                "Bounded prefix only; complete 37k ordering intentionally not materialized for PERF-BASE0",
            ),
        )
    )
    stages.append(
        PerfBase0ScientificStage(
            stage_id="target_data2c_exact_fps",
            algorithm_ids=(
                "mdstats.selection._fps_order_matrix.exact-incremental",
                "mdstats.target_coverage._score_family-nearest-selected-equivalent",
            ),
            corpus_digests=(target_corpus.content_digest,),
            policy_digests=(target_policy.policy_digest, BENCHMARK_POLICY_DIGEST),
            subset_rule=(
                f"complete {len(training.frame_uids)}-frame fused target-label/cell matrix; "
                f"exact deterministic FPS prefix K={fps_limit}; nested rungs={list(rung_sizes)}"
            ),
            arrays=(
                PerfBase0ArrayReference.from_array("fused_feature_scales", full_scales),
                PerfBase0ArrayReference.from_array("fused_feature_matrix", fused),
                PerfBase0ArrayReference.from_array("fps_order_indices", fps_order_indices),
            ),
            json_references=(
                PerfBase0JsonReference.from_value("fps_order_uids", fps_order_uids),
                PerfBase0JsonReference.from_value("coverage_reports", coverage_reports),
                PerfBase0JsonReference.from_value("rung_sizes", list(rung_sizes)),
            ),
            notes=(
                "This is an exact bounded production FPS-kernel oracle, not a substitute for the unavailable DATA2C mandatory-quota plan.",
                "Coverage reports use the frozen exact local radii from the realistic TARGET-DATA2B-style family subset.",
            ),
        )
    )

    record = PerfBase0Record(
        baseline_id=args.baseline_id,
        source_version=mdstats.__version__,
        created_at_utc=telemetry[0].measured_at_utc,
        authority_status="bounded",
        source_artifacts=source_artifacts,
        corpora=(synthetic_corpus, target_corpus, replay_corpus),
        scientific_stages=tuple(stages),
        execution_telemetry=tuple(telemetry),
        unavailable_stages=(
            "TARGET-DATA2B production DATA6 structural/foundation-residual families",
            "TARGET-DATA2C mandatory-quota and exhaustive ladder authority",
            "DATA6 foundation descriptors, predictions, difficulty, recovery, and GPU telemetry",
            "DATA7 complete production selection authority",
            "DATA8 campaign bundle materialization authority",
            "TRAIN2 checkpoint/continuation timing and identities",
            "EVAL2 checkpoint inference, metric, and decision timing",
        ),
        limitations=(
            "No MACE-MH-1 checkpoint was supplied, so foundation-model scientific outputs are not inferred or fabricated.",
            "The cloud host is CPU-only and cgroup-limited; no GPU memory, OOM, DATA6 inference, training, or evaluation telemetry is available.",
            "The realistic FPS authority is a deterministic exact K-bounded prefix over label/cell/composition summaries, because the campaign DATA6 fused descriptor table is not present.",
            "Source XML and replay bytes are fully authenticated; all target and authoritative replay split frames are ingested without frame subsampling.",
            "Operating-system page-cache state is observed rather than forcibly controlled; process CPU time and exact byte identities accompany wall time.",
        ),
    )
    write_perf_base0_record(args.output, record)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_perf_base0_markdown(record), encoding="utf-8")
    # Fail closed by reading the just-written record through the public parser.
    from mdstats.training_data.performance_baseline import read_perf_base0_record

    restored = read_perf_base0_record(args.output)
    if restored.content_digest != record.content_digest:
        raise SystemExit("PERF-BASE0 record round-trip digest mismatch.")
    print(json.dumps({
        "output": str(args.output),
        "report": str(args.report),
        "scientific_digest": record.scientific_digest,
        "execution_digest": record.execution_digest,
        "content_digest": record.content_digest,
        "target_frames": len(training.frame_uids),
        "replay_frames": len(replay.frame_uids),
        "fps_limit": fps_limit,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
