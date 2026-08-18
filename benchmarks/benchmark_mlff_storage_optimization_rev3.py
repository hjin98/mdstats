"""Reproducible constant-factor benchmarks for the MLFF rev3 storage redesign."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import statistics
import tempfile
import time
from typing import Callable

import numpy as np

from mdstats.training_data.production_model_sweep import _atomic_npy


def _sha256_file_uncached(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def _old_write_then_hash(path: Path, array: np.ndarray) -> str:
    temporary = path.with_name(f".{path.name}.old-{os.getpid()}")
    with temporary.open("wb") as handle:
        np.save(handle, array, allow_pickle=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return _sha256_file_uncached(path)


def _median_seconds(call: Callable[[], object], repeats: int = 5) -> float:
    values: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        call()
        values.append(time.perf_counter() - start)
    return float(statistics.median(values))


def _npz_access(path: Path, members: tuple[str, ...]) -> tuple[int, float]:
    start = time.perf_counter()
    with np.load(path, allow_pickle=False) as archive:
        arrays = tuple(np.asarray(archive[name]) for name in members)
    elapsed = time.perf_counter() - start
    return int(sum(array.nbytes for array in arrays)), float(elapsed)


def main() -> None:
    rng = np.random.default_rng(20260805)
    production_frames = 36_759
    shard_size = 128
    atom_count = 168
    descriptor_dimension = 256

    with tempfile.TemporaryDirectory(prefix="mdstats-mlff-opt-bench-") as raw:
        root = Path(raw)

        write_array = rng.normal(size=(4096, 1024)).astype(np.float64)
        old_path = root / "old.npy"
        new_path = root / "new.npy"
        old_seconds = _median_seconds(lambda: _old_write_then_hash(old_path, write_array))
        new_seconds = _median_seconds(lambda: _atomic_npy(new_path, write_array))
        if _sha256_file_uncached(old_path) != _sha256_file_uncached(new_path):
            raise RuntimeError("old/new NPY byte identities differ")

        descriptor_count = shard_size * atom_count
        species_count = 5
        descriptor_path = root / "descriptor-shard.npz"
        np.savez(
            descriptor_path,
            descriptor_offsets=np.arange(
                0, descriptor_count + 1, atom_count, dtype=np.int64
            ),
            descriptor_values=rng.normal(
                size=(descriptor_count, descriptor_dimension)
            ).astype(np.float32),
            summary_global_mean=rng.normal(
                size=(shard_size, descriptor_dimension)
            ).astype(np.float64),
            summary_global_std=np.abs(
                rng.normal(size=(shard_size, descriptor_dimension))
            ).astype(np.float64),
            summary_species_atomic_numbers=np.arange(
                1, species_count + 1, dtype=np.int32
            ),
            summary_species_present=np.ones(
                (shard_size, species_count), dtype=np.bool_
            ),
            summary_species_mean=rng.normal(
                size=(shard_size, species_count, descriptor_dimension)
            ).astype(np.float32),
        )
        with np.load(descriptor_path, allow_pickle=False) as archive:
            all_members = tuple(archive.files)
        summary_members = (
            "summary_global_mean",
            "summary_global_std",
            "summary_species_atomic_numbers",
            "summary_species_present",
            "summary_species_mean",
        )
        all_nbytes, all_seconds = _npz_access(descriptor_path, all_members)
        summary_nbytes, summary_seconds = _npz_access(
            descriptor_path, summary_members
        )

        matrix_bytes = production_frames * 1400 * np.dtype(np.float64).itemsize
        missing_bytes = production_frames * 1400 * np.dtype(np.bool_).itemsize
        old_sidecar_count = production_frames * 2
        new_sidecar_count = 2 * (
            (production_frames + shard_size - 1) // shard_size
        )

        result = {
            "schema": "mdstats.mlff-storage-optimization-benchmark.v1",
            "production_profile": {
                "frames": production_frames,
                "artifact_shard_size": shard_size,
                "atom_count": atom_count,
                "descriptor_dimension": descriptor_dimension,
            },
            "data6_file_count": {
                "legacy_descriptor_plus_prediction_sidecars": old_sidecar_count,
                "sharded_descriptor_plus_prediction_files": new_sidecar_count,
                "reduction_factor": old_sidecar_count / new_sidecar_count,
            },
            "one_pass_npy_write": {
                "array_mib": write_array.nbytes / 2**20,
                "legacy_write_then_reread_hash_median_seconds": old_seconds,
                "write_and_hash_once_median_seconds": new_seconds,
                "speedup": old_seconds / new_seconds,
                "byte_identical": True,
            },
            "selective_descriptor_shard_read": {
                "shard_file_mib": descriptor_path.stat().st_size / 2**20,
                "legacy_all_member_materialized_mib": all_nbytes / 2**20,
                "summary_only_materialized_mib": summary_nbytes / 2**20,
                "materialized_byte_reduction_factor": all_nbytes / summary_nbytes,
                "legacy_all_member_seconds": all_seconds,
                "summary_only_seconds": summary_seconds,
                "single_run_speedup": all_seconds / summary_seconds,
            },
            "data7_universal_matrix_memory": {
                "values_matrix_mib": matrix_bytes / 2**20,
                "missing_mask_mib": missing_bytes / 2**20,
                "legacy_three_value_matrix_copies_plus_mask_mib": (
                    3 * matrix_bytes + missing_bytes
                )
                / 2**20,
                "preallocated_two_value_matrices_plus_mask_upper_bound_mib": (
                    2 * matrix_bytes + missing_bytes
                )
                / 2**20,
                "estimated_peak_reduction_mib": matrix_bytes / 2**20,
            },
        }
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
