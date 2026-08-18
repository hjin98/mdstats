#!/usr/bin/env python3
"""Qualify PERF-P0 against the frozen complete-corpus PERF-BASE0 oracle."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Callable, Sequence

import numpy as np

import mdstats
from mdstats.training_data._common import canonical_json, digest
from mdstats.training_data.performance_baseline import PerfBase0ArrayReference
from mdstats.training_data.target_coverage import (
    TargetCoverageDomainReference,
    TargetCoverageExtentChannel,
    TargetCoverageFamilyReference,
    TargetCoveragePolicy,
    TargetCoverageReference,
    _local_reference_radii,
    _weighted_quantiles,
)

from benchmark_mlff_perf_base0 import (
    MOBILE_SPECIES,
    SPECIES,
    SPECIES_FEATURE_NAMES,
    SPECIES_SYMBOL,
    TRAINING_FEATURE_NAMES,
    CoverageFamilyResult,
    IngestedCorpus,
    ingest_training,
)

SCHEMA = "mdstats.mlff-perf-p0-benchmark.v1"
CACHE_SCHEMA = "mdstats.mlff-perf-p0-training-cache.v1"


@dataclass(slots=True)
class Measurement:
    wall_seconds: float
    process_cpu_seconds: float
    rss_start_mib: float
    rss_end_mib: float
    rss_peak_mib: float
    rss_increment_mib: float


class _RssMonitor:
    def __init__(self, period_seconds: float = 0.01) -> None:
        self.period_seconds = period_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.start = 0
        self.end = 0
        self.peak = 0

    @staticmethod
    def current_bytes() -> int:
        try:
            for line in Path("/proc/self/status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
        except OSError:
            pass
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024

    def __enter__(self) -> "_RssMonitor":
        self.start = self.current_bytes()
        self.peak = self.start

        def sample() -> None:
            while not self._stop.wait(self.period_seconds):
                self.peak = max(self.peak, self.current_bytes())

        self._thread = threading.Thread(target=sample, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.end = self.current_bytes()
        self.peak = max(self.peak, self.end)
        self._stop.set()
        if self._thread is not None:
            self._thread.join()

    def measurement(self, wall: float, cpu: float) -> Measurement:
        scale = 1024.0 * 1024.0
        return Measurement(
            wall_seconds=wall,
            process_cpu_seconds=cpu,
            rss_start_mib=self.start / scale,
            rss_end_mib=self.end / scale,
            rss_peak_mib=self.peak / scale,
            rss_increment_mib=max(0, self.peak - self.start) / scale,
        )


def _measure(function: Callable[[], Any]) -> tuple[Any, Measurement]:
    with _RssMonitor() as monitor:
        wall_start = time.perf_counter()
        cpu_start = time.process_time()
        result = function()
        cpu = time.process_time() - cpu_start
        wall = time.perf_counter() - wall_start
    return result, monitor.measurement(wall, cpu)


def _cache_paths(root: Path) -> dict[str, Path]:
    return {
        "metadata": root / "metadata.json",
        "features": root / "feature_matrix.npy",
        "source_indices": root / "source_indices.npy",
        "species_values": root / "species_values.npy",
        "species_missing": root / "species_missing_mask.npy",
    }


def _write_cache(root: Path, training: IngestedCorpus) -> None:
    root.mkdir(parents=True, exist_ok=True)
    paths = _cache_paths(root)
    np.save(paths["features"], training.feature_matrix, allow_pickle=False)
    np.save(paths["source_indices"], training.source_indices, allow_pickle=False)
    if training.species_values is None or training.species_missing_mask is None:
        raise ValueError("Training cache lacks species arrays.")
    np.save(paths["species_values"], training.species_values, allow_pickle=False)
    np.save(paths["species_missing"], training.species_missing_mask, allow_pickle=False)
    payload = {
        "schema": CACHE_SCHEMA,
        "frame_uids": list(training.frame_uids),
        "source_frame_counts": list(training.source_frame_counts),
        "atom_count": training.atom_count,
        "array_sha256": {
            name: PerfBase0ArrayReference.from_array(name, np.load(path, allow_pickle=False)).value_sha256
            for name, path in paths.items()
            if name != "metadata"
        },
    }
    paths["metadata"].write_text(canonical_json(payload) + "\n", encoding="utf-8")


def _load_cache(root: Path, *, mmap: bool = False) -> IngestedCorpus:
    paths = _cache_paths(root)
    payload = json.loads(paths["metadata"].read_text(encoding="utf-8"))
    if payload.get("schema") != CACHE_SCHEMA:
        raise ValueError("Unsupported PERF-P0 cache schema.")
    mode = "r" if mmap else None
    return IngestedCorpus(
        frame_uids=tuple(str(value) for value in payload["frame_uids"]),
        feature_matrix=np.load(paths["features"], mmap_mode=mode, allow_pickle=False),
        source_indices=np.load(paths["source_indices"], mmap_mode=mode, allow_pickle=False),
        source_frame_counts=tuple(int(value) for value in payload["source_frame_counts"]),
        atom_count=int(payload["atom_count"]),
        species_values=np.load(paths["species_values"], mmap_mode=mode, allow_pickle=False),
        species_missing_mask=np.load(paths["species_missing"], mmap_mode=mode, allow_pickle=False),
    )


def _legacy_weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    cumulative = np.cumsum(weights[order], dtype=np.float64)
    target = float(q) * float(cumulative[-1])
    index = int(np.searchsorted(cumulative, target, side="left"))
    return float(sorted_values[min(index, sorted_values.size - 1)])


def _legacy_statistics(matrix: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    scales = np.empty(matrix.shape[1], dtype=np.float64)
    quantiles = np.empty((3, matrix.shape[1]), dtype=np.float64)
    for column in range(matrix.shape[1]):
        values = matrix[:, column]
        q25 = _legacy_weighted_quantile(values, weights, 0.25)
        q75 = _legacy_weighted_quantile(values, weights, 0.75)
        scale = q75 - q25
        if not np.isfinite(scale) or scale <= 1.0e-12:
            q01 = _legacy_weighted_quantile(values, weights, 0.01)
            q99 = _legacy_weighted_quantile(values, weights, 0.99)
            scale = q99 - q01
        if not np.isfinite(scale) or scale <= 1.0e-12:
            scale = max(float(np.std(values)), 1.0)
        scales[column] = max(float(scale), 1.0e-12)
        quantiles[:, column] = [
            _legacy_weighted_quantile(values, weights, q)
            for q in (0.01, 0.5, 0.99)
        ]
    return scales, quantiles


def _p0_statistics(matrix: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    scales = np.empty(matrix.shape[1], dtype=np.float64)
    quantiles = np.empty((3, matrix.shape[1]), dtype=np.float64)
    for column in range(matrix.shape[1]):
        observed = _weighted_quantiles(
            matrix[:, column], weights, (0.01, 0.25, 0.5, 0.75, 0.99)
        )
        q01, q25, q50, q75, q99 = (float(value) for value in observed)
        scale = q75 - q25
        if not np.isfinite(scale) or scale <= 1.0e-12:
            scale = q99 - q01
        if not np.isfinite(scale) or scale <= 1.0e-12:
            scale = max(float(np.std(matrix[:, column])), 1.0)
        scales[column] = max(scale, 1.0e-12)
        quantiles[:, column] = (q01, q50, q99)
    return scales, quantiles


def _balanced_source_weights(source_indices: np.ndarray) -> np.ndarray:
    source_indices = np.asarray(source_indices, dtype=np.int64)
    unique, counts = np.unique(source_indices, return_counts=True)
    weights = np.zeros(source_indices.size, dtype=np.float64)
    unit_mass = 1.0 / unique.size
    for source, count in zip(unique, counts, strict=True):
        weights[source_indices == source] = unit_mass / int(count)
    weights /= np.sum(weights, dtype=np.float64)
    return weights


def _definitions(training: IngestedCorpus) -> list[tuple[str, tuple[str, ...], np.ndarray, np.ndarray]]:
    matrix = np.asarray(training.feature_matrix)
    all_rows = np.arange(matrix.shape[0], dtype=np.int64)
    definitions: list[tuple[str, tuple[str, ...], np.ndarray, np.ndarray]] = []
    for family_id, columns in (
        ("target_labels", (0, 1, 3, 4, 5, 12, 13)),
        ("stress_tensor", (6, 7, 8, 9, 10, 11)),
        ("cell_geometry", (14, 15, 16, 17, 18, 19, 20)),
        ("mobile_labels", (27, 28, 29, 30)),
    ):
        column_array = np.asarray(columns, dtype=np.int64)
        definitions.append(
            (
                family_id,
                tuple(TRAINING_FEATURE_NAMES[index] for index in columns),
                all_rows,
                matrix[:, column_array],
            )
        )
    if training.species_values is None or training.species_missing_mask is None:
        raise ValueError("Species arrays are unavailable.")
    species = np.asarray(training.species_values)
    missing = np.asarray(training.species_missing_mask)
    framework_columns: list[int] = []
    framework_names: list[str] = []
    for z in (8, 13, 14):
        base = SPECIES.index(z) * 4
        framework_columns.extend((base + 1, base + 2))
        framework_names.extend(
            (
                f"{SPECIES_SYMBOL[z].lower()}_force_rms_ev_per_angstrom",
                f"{SPECIES_SYMBOL[z].lower()}_force_q99_ev_per_angstrom",
            )
        )
    columns = np.asarray(framework_columns, dtype=np.int64)
    rows = np.flatnonzero(~np.any(missing[:, columns], axis=1))
    definitions.append(
        ("framework_species_forces", tuple(framework_names), rows, species[np.ix_(rows, columns)])
    )
    for z in MOBILE_SPECIES:
        base = SPECIES.index(z) * 4
        columns = np.arange(base, base + 4, dtype=np.int64)
        rows = np.flatnonzero(~np.any(missing[:, columns], axis=1))
        definitions.append(
            (
                f"{SPECIES_SYMBOL[z].lower()}_species_force",
                tuple(SPECIES_FEATURE_NAMES[index] for index in columns),
                rows,
                species[np.ix_(rows, columns)],
            )
        )
    return definitions


def _build_families(
    training: IngestedCorpus,
    *,
    mode: str,
    workers: int,
    block_size: int,
) -> list[CoverageFamilyResult]:
    result: list[CoverageFamilyResult] = []
    weight_cache: dict[str, np.ndarray] = {}
    source_indices = np.asarray(training.source_indices)
    for family_id, names, rows, values in _definitions(training):
        matrix = np.asarray(values, dtype=np.float64)
        if mode == "p0":
            key = digest(
                {
                    "schema": "mdstats.perf-p0-weight-cache-key.v1",
                    "row_sha256": PerfBase0ArrayReference.from_array("rows", rows).value_sha256,
                    "unit_sha256": PerfBase0ArrayReference.from_array(
                        "units", source_indices[rows]
                    ).value_sha256,
                }
            )
            weights = weight_cache.get(key)
            if weights is None:
                weights = _balanced_source_weights(source_indices[rows])
                weight_cache[key] = weights
            scales, quantiles = _p0_statistics(matrix, weights)
            fast_path = True
        else:
            weights = _balanced_source_weights(source_indices[rows])
            scales, quantiles = _legacy_statistics(matrix, weights)
            fast_path = False
        scaled = matrix / scales[None, :]
        radii = _local_reference_radii(
            scaled,
            weights,
            beta=1.0 / 128.0,
            leave_one_out=True,
            block_size=block_size,
            query_workers=workers,
            uniform_fast_path=fast_path,
        )
        result.append(
            CoverageFamilyResult(
                family_id=family_id,
                feature_names=names,
                global_indices=np.asarray(rows, dtype=np.int64),
                values=matrix,
                weights=weights,
                scales=scales,
                scaled=scaled,
                local_radii=radii,
                quantiles=quantiles,
            )
        )
    return result


def _fingerprints(families: Sequence[CoverageFamilyResult]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for family in families:
        prefix = family.family_id
        for name, array in (
            ("frame_indices", family.global_indices),
            ("values", family.values),
            ("weights", family.weights),
            ("scales", family.scales),
            ("local_radii", family.local_radii),
            ("quantiles_q01_q50_q99", family.quantiles),
        ):
            result.append(
                PerfBase0ArrayReference.from_array(f"{prefix}.{name}", array).to_dict()
            )
    return result


def _reference_from_families(
    training: IngestedCorpus,
    families: Sequence[CoverageFamilyResult],
) -> TargetCoverageReference:
    frame_uids = tuple(digest({"frame_uid": value}) for value in training.frame_uids)
    family_records: list[TargetCoverageFamilyReference] = []
    for family in families:
        extents = tuple(
            TargetCoverageExtentChannel(
                feature_name=name,
                feature_index=index,
                lower_reference_quantile=float(family.quantiles[0, index]),
                upper_reference_quantile=float(family.quantiles[2, index]),
            )
            for index, name in enumerate(family.feature_names)
        )
        family_records.append(
            TargetCoverageFamilyReference(
                family_id=family.family_id,
                family_kind="target_label",
                semantic_family=family.family_id,
                required=True,
                metric="scaled_rms_l2",
                fidelity_diagnostic=None,
                feature_names=family.feature_names,
                frame_indices=family.global_indices,
                values=family.values,
                weights=family.weights,
                scales=family.scales,
                local_radii=family.local_radii,
                extent_channels=extents,
                source_evidence_digest="a" * 64,
                notes=("PERF-P0 complete supplied-data persistence fixture.",),
            )
        )
    domain = TargetCoverageDomainReference(
        label_domain_id="lta-target",
        frame_uids=frame_uids,
        families=tuple(family_records),
        strata=(),
        frame_domain_digest=digest({"frame_uids": list(frame_uids)}),
    )
    return TargetCoverageReference(
        dataset_id="lta-perf-p0",
        source_catalog_digest="1" * 64,
        frame_catalog_digest="2" * 64,
        data4_bundle_digest="3" * 64,
        data5_bundle_digest="4" * 64,
        data6_bundle_digest="5" * 64,
        target_data_role_freeze_digest="6" * 64,
        foundation_target_audit_digest="7" * 64,
        policy=TargetCoveragePolicy(),
        domains=(domain,),
    )


def _persistence_measurements(
    training: IngestedCorpus,
    families: Sequence[CoverageFamilyResult],
    root: Path,
) -> dict[str, Any]:
    reference = _reference_from_families(training, families)
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)

    legacy_path = root / "legacy-v1.json"
    (_, legacy_write) = _measure(
        lambda: legacy_path.write_text(
            canonical_json(reference.to_legacy_v1_dict()) + "\n", encoding="utf-8"
        )
    )
    (legacy_restored, legacy_read) = _measure(
        lambda: TargetCoverageReference.from_dict(
            json.loads(legacy_path.read_text(encoding="utf-8"))
        )
    )

    records_root = root / "records"
    (pointer, native_write) = _measure(
        lambda: mdstats.write_target_coverage_native_record(reference, records_root)
    )
    (native_restored, native_read) = _measure(
        lambda: mdstats.read_target_coverage_native_record(
            pointer, root, mmap_threshold_bytes=0
        )
    )
    native_directory = (root / pointer["relative_path"]).parent
    native_bytes = sum(path.stat().st_size for path in native_directory.rglob("*") if path.is_file())
    return {
        "reference_content_digest": reference.content_digest,
        "legacy_v1": {
            "write": asdict(legacy_write),
            "read": asdict(legacy_read),
            "size_bytes": legacy_path.stat().st_size,
            "restored_digest": legacy_restored.content_digest,
        },
        "native_v2": {
            "write": asdict(native_write),
            "read": asdict(native_read),
            "size_bytes": native_bytes,
            "restored_digest": native_restored.content_digest,
            "pointer": pointer,
        },
        "exact_migration": mdstats.compare_target_coverage_references_exact(
            legacy_restored, native_restored
        ).to_dict(),
    }


def _worker(args: argparse.Namespace) -> int:
    training = _load_cache(args.cache_root, mmap=False)
    (families, measurement) = _measure(
        lambda: _build_families(
            training,
            mode=args.worker_mode,
            workers=args.workers,
            block_size=args.radius_block_size,
        )
    )
    payload: dict[str, Any] = {
        "mode": args.worker_mode,
        "measurement": asdict(measurement),
        "family_element_count": sum(item.values.shape[0] for item in families),
        "fingerprints": _fingerprints(families),
        "scientific_digest": digest(_fingerprints(families)),
    }
    if args.worker_mode == "p0" and args.persistence_root is not None:
        payload["persistence"] = _persistence_measurements(
            training, families, args.persistence_root
        )
    args.worker_output.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    return 0


def _run_worker(
    script: Path,
    args: argparse.Namespace,
    mode: str,
    run_index: int,
) -> dict[str, Any]:
    output = args.work_root / f"{mode}-run-{run_index}.json"
    if args.resume and output.is_file():
        return json.loads(output.read_text(encoding="utf-8"))
    command = [
        sys.executable,
        str(script),
        "--worker-mode",
        mode,
        "--worker-output",
        str(output),
        "--cache-root",
        str(args.cache_root),
        "--workers",
        str(args.workers),
        "--radius-block-size",
        str(args.radius_block_size),
    ]
    if mode == "p0" and run_index == 1:
        command.extend(["--persistence-root", str(args.work_root / "persistence")])
    environment = os.environ.copy()
    subprocess.run(command, check=True, env=environment)
    return json.loads(output.read_text(encoding="utf-8"))


def _load_staged_persistence(root: Path) -> dict[str, Any]:
    """Load independently measured persistence operations.

    The staged form is useful on constrained benchmark runners where a single
    process invocation cannot cover family construction plus both persistence
    representations.  Each stage remains an isolated process measurement and
    the final exact migration report authenticates the combined evidence.
    """

    def load(name: str) -> dict[str, Any]:
        return json.loads((root / name).read_text(encoding="utf-8"))

    prepared = load("prepare.json")
    legacy_write = load("legacy-write.json")
    legacy_read = load("legacy-read.json")
    native_write = load("native-write.json")
    native_read = load("native-read.json")
    comparison = load("comparison.json")
    reference_digest = str(prepared["reference_content_digest"])
    observed = {
        reference_digest,
        str(legacy_write["reference_content_digest"]),
        str(legacy_read["restored_digest"]),
        str(native_write["reference_content_digest"]),
        str(native_read["restored_digest"]),
    }
    if len(observed) != 1 or not bool(comparison.get("exact_match")):
        raise ValueError("Staged PERF-P0 persistence evidence is not exact.")
    return {
        "reference_content_digest": reference_digest,
        "legacy_v1": {
            "write": legacy_write["measurement"],
            "read": legacy_read["measurement"],
            "size_bytes": int(legacy_write["size_bytes"]),
            "restored_digest": str(legacy_read["restored_digest"]),
        },
        "native_v2": {
            "write": native_write["measurement"],
            "read": native_read["measurement"],
            "size_bytes": int(native_write["size_bytes"]),
            "restored_digest": str(native_read["restored_digest"]),
            "pointer": native_write["pointer"],
        },
        "exact_migration": comparison,
        "measurement_mode": "isolated-stages",
    }


def _baseline_arrays(path: Path) -> tuple[str, dict[str, dict[str, Any]], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    stage = next(
        item for item in payload["scientific_stages"]
        if item["stage_id"] == "target_data2b_exact_radii"
    )
    return (
        str(stage["content_digest"]),
        {str(item["name"]): item for item in stage["arrays"]},
        next(
            item for item in payload["execution_telemetry"]
            if item["stage_id"] == "target_data2b_exact_radii"
        ),
    )


def _summary(values: Sequence[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "minimum": float(np.min(array)),
        "median": float(np.median(array)),
        "maximum": float(np.max(array)),
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    comparison = payload["comparison"]
    lines = [
        "# MLFF PERF-P0 matched CPU qualification",
        "",
        f"- Source version: `{payload['source_version']}`",
        f"- Target frames: **{payload['target_frames']:,}**",
        f"- Family elements: **{payload['family_element_count']:,}**",
        f"- Exact baseline-array agreement: **{str(comparison['baseline_array_exact']).lower()}**",
        f"- Legacy/P0 scientific digest agreement: **{str(comparison['legacy_p0_exact']).lower()}**",
        "",
        "## Exact family construction",
        "",
        "| Path | Median wall (s) | Range (s) | Median peak RSS (MiB) |",
        "|---|---:|---:|---:|",
    ]
    for key, label in (("legacy", "Pre-P0 exact path"), ("p0", "PERF-P0 exact path")):
        summary = payload["summaries"][key]
        lines.append(
            f"| {label} | {summary['wall_seconds']['median']:.3f} | "
            f"{summary['wall_seconds']['minimum']:.3f}--{summary['wall_seconds']['maximum']:.3f} | "
            f"{summary['rss_peak_mib']['median']:.2f} |"
        )
    lines.extend(
        [
            "",
            f"Matched median wall improvement: **{comparison['matched_wall_improvement_percent']:.2f}%**.",
            "",
            "## Persistence",
            "",
            "| Representation | Write wall (s) | Read wall (s) | Bytes |",
            "|---|---:|---:|---:|",
        ]
    )
    persistence = payload["persistence"]
    for key, label in (("legacy_v1", "Nested JSON v1"), ("native_v2", "Native-array v2")):
        item = persistence[key]
        lines.append(
            f"| {label} | {item['write']['wall_seconds']:.3f} | "
            f"{item['read']['wall_seconds']:.3f} | {item['size_bytes']:,} |"
        )
    lines.extend(
        [
            "",
            "The benchmark ingests the complete supplied target corpus once, then runs each exact construction path in isolated matched processes. Execution settings and telemetry are not part of the scientific digest.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--training-root", type=Path)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--baseline-record", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--work-root", type=Path, default=Path(".perf-p0-work"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--radius-block-size", type=int, default=1024)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--worker-mode", choices=("legacy", "p0"))
    parser.add_argument("--worker-output", type=Path)
    parser.add_argument("--persistence-root", type=Path)
    parser.add_argument("--persistence-evidence-root", type=Path)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.workers = max(1, int(args.workers))
    args.radius_block_size = max(1, int(args.radius_block_size))
    if args.worker_mode is not None:
        if args.worker_output is None:
            raise SystemExit("--worker-output is required in worker mode")
        return _worker(args)
    for name in ("training_root", "baseline_record", "output", "report"):
        if getattr(args, name) is None:
            raise SystemExit(f"--{name.replace('_', '-')} is required")
    args.work_root.mkdir(parents=True, exist_ok=True)
    if not _cache_paths(args.cache_root)["metadata"].is_file():
        paths = tuple(sorted(args.training_root.glob("*.xml")))
        if not paths:
            raise SystemExit("No training XML files found.")
        training = ingest_training(paths, args.training_root)
        _write_cache(args.cache_root, training)
    training_meta = json.loads(_cache_paths(args.cache_root)["metadata"].read_text())

    script = Path(__file__).resolve()
    legacy_runs = [
        _run_worker(script, args, "legacy", index + 1)
        for index in range(max(1, int(args.repeats)))
    ]
    p0_runs = [
        _run_worker(script, args, "p0", index + 1)
        for index in range(max(1, int(args.repeats)))
    ]
    baseline_stage_digest, baseline_arrays, baseline_execution = _baseline_arrays(
        args.baseline_record
    )
    first_p0_arrays = {item["name"]: item for item in p0_runs[0]["fingerprints"]}
    baseline_array_exact = set(first_p0_arrays) == set(baseline_arrays) and all(
        first_p0_arrays[name]["value_sha256"] == baseline_arrays[name]["value_sha256"]
        and first_p0_arrays[name]["dtype"] == baseline_arrays[name]["dtype"]
        and first_p0_arrays[name]["shape"] == baseline_arrays[name]["shape"]
        for name in baseline_arrays
    )
    legacy_p0_exact = all(
        run["scientific_digest"] == legacy_runs[0]["scientific_digest"]
        for run in (*legacy_runs, *p0_runs)
    )
    summaries: dict[str, Any] = {}
    for key, runs in (("legacy", legacy_runs), ("p0", p0_runs)):
        summaries[key] = {
            field: _summary([float(run["measurement"][field]) for run in runs])
            for field in (
                "wall_seconds",
                "process_cpu_seconds",
                "rss_peak_mib",
                "rss_increment_mib",
            )
        }
    legacy_median = summaries["legacy"]["wall_seconds"]["median"]
    p0_median = summaries["p0"]["wall_seconds"]["median"]
    persistence = (
        _load_staged_persistence(args.persistence_evidence_root)
        if args.persistence_evidence_root is not None
        else p0_runs[0]["persistence"]
    )
    payload = {
        "schema": SCHEMA,
        "source_version": mdstats.__version__,
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_frames": len(training_meta["frame_uids"]),
        "target_atoms": int(training_meta["atom_count"]),
        "source_units": len(training_meta["source_frame_counts"]),
        "family_element_count": int(p0_runs[0]["family_element_count"]),
        "workers": args.workers,
        "radius_block_size": args.radius_block_size,
        "baseline": {
            "record": str(args.baseline_record),
            "target_data2b_stage_digest": baseline_stage_digest,
            "execution": baseline_execution,
        },
        "runs": {"legacy": legacy_runs, "p0": p0_runs},
        "summaries": summaries,
        "comparison": {
            "baseline_array_exact": baseline_array_exact,
            "legacy_p0_exact": legacy_p0_exact,
            "legacy_scientific_digest": legacy_runs[0]["scientific_digest"],
            "p0_scientific_digest": p0_runs[0]["scientific_digest"],
            "matched_wall_improvement_percent": 100.0 * (legacy_median - p0_median) / legacy_median,
            "baseline_wall_seconds": baseline_execution["wall_seconds"],
            "p0_median_wall_seconds": p0_median,
        },
        "persistence": persistence,
        "limitations": [
            "This gate covers exact supplied-data TARGET-DATA2B-style label/cell/species families; production DATA6 model-derived families remain unavailable without the authorizing checkpoint and complete campaign bundle.",
            "The process-level benchmark isolates family construction from XML ingestion so pre-P0 and P0 paths receive identical in-memory arrays.",
            "Operating-system scheduling and page-cache state are observed, not forcibly controlled; repeated matched runs bound execution noise.",
        ],
    }
    payload["scientific_digest"] = digest(
        {
            "schema": SCHEMA,
            "target_frames": payload["target_frames"],
            "family_element_count": payload["family_element_count"],
            "array_fingerprints": p0_runs[0]["fingerprints"],
            "persistence_reference_digest": payload["persistence"]["reference_content_digest"],
        }
    )
    payload["execution_digest"] = digest(
        {
            "schema": SCHEMA,
            "workers": args.workers,
            "radius_block_size": args.radius_block_size,
            "summaries": summaries,
        }
    )
    payload["content_digest"] = digest(
        {
            "schema": SCHEMA,
            "scientific_digest": payload["scientific_digest"],
            "execution_digest": payload["execution_digest"],
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(_render_markdown(payload), encoding="utf-8")
    if not baseline_array_exact or not legacy_p0_exact:
        raise SystemExit("PERF-P0 scientific equivalence failed")
    print(json.dumps({
        "output": str(args.output),
        "report": str(args.report),
        "target_frames": payload["target_frames"],
        "family_elements": payload["family_element_count"],
        "wall_improvement_percent": payload["comparison"]["matched_wall_improvement_percent"],
        "scientific_digest": payload["scientific_digest"],
        "execution_digest": payload["execution_digest"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
