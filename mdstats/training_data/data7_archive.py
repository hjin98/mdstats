"""Compact, memory-mappable persistence for large DATA7 preparation bundles.

DATA7 contains a dense transformed-frame matrix and one training-weight record
per frame.  The current archive schema stores every large numerical payload as
an uncompressed ``.npy`` member and keeps JSON limited to lineage and member
metadata.  Because ZIP_STORED members are byte-contiguous, the fitted-frame
matrix can be memory-mapped directly from the archive without extraction.

Legacy schema-v1 archives remain readable.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
from typing import Any, Iterable, Mapping
import zipfile

import numpy as np

from ._common import canonical_json, sha256_file_cached
from .data7_bundle import Data7PreparationBundle
from .feature_metric import (
    FITTED_FEATURE_BLOCK_SCHEMA,
    FITTED_FEATURE_METRIC_SCHEMA,
    MLFF_DATA7_PARSER_VERSION,
    MLFF_DATA7_V63_PARSER_VERSION,
    MLFF_DATA7_LEGACY_PARSER_VERSION,
    TRANSFORMED_FRAME_FEATURE_TABLE_SCHEMA,
    FeatureFitDomain,
    FeatureMetricPolicyTemplate,
    FittedFeatureBlockMetric,
    FittedFeatureMetric,
    TransformedFrameFeatureTable,
)
from .objectives import (
    TRAINING_WEIGHT_CATALOG_SCHEMA,
    CheckpointMetricPolicy,
    ConfigurationWeightPolicy,
    FrameTrainingWeight,
    FrameTrainingWeightTable,
    TrainingObjectivePolicy,
    TrainingWeightCatalog,
)
from .reference_fit import AtomicReferenceFitRecord
from .selection import SelectionCoverageReport, TrainingSelectionPlan

DATA7_ARCHIVE_MANIFEST_SCHEMA = "mdstats.data7-archive-manifest.v3"
DATA7_ARCHIVE_MANIFEST_V2_SCHEMA = "mdstats.data7-archive-manifest.v2"
DATA7_ARCHIVE_MANIFEST_LEGACY_SCHEMA = "mdstats.data7-archive-manifest.v1"
_DATA7_MATRIX_MEMBER = "fitted-frame-features.npy"
_DATA7_WEIGHTS_MEMBER = "training-weights.jsonl"
_DATA7_WEIGHT_CONFIGURATION_MEMBER = "training-weights/configuration.npy"
_DATA7_WEIGHT_ENERGY_MEMBER = "training-weights/energy.npy"
_DATA7_WEIGHT_FORCES_MEMBER = "training-weights/forces.npy"
_DATA7_WEIGHT_STRESS_MEMBER = "training-weights/stress.npy"
_DATA7_WEIGHT_REASONS_MEMBER = "training-weights/reasons.jsonl"
_DATA7_MANIFEST_MEMBER = "manifest.json"
_LOCAL_FILE_HEADER = struct.Struct("<IHHHHHIIIHH")
_LOCAL_FILE_SIGNATURE = 0x04034B50


class _SequentialHashingWriter:
    """Non-seekable ZIP sink that hashes final bytes in one pass.

    ``zipfile`` uses data descriptors when the destination is non-seekable, so
    local headers are never rewritten and the streaming digest is the digest of
    the final archive rather than of an intermediate byte sequence.
    """

    def __init__(self, handle: Any):
        self._handle = handle
        self._digest = hashlib.sha256()
        self._position = 0

    def write(self, payload: bytes | bytearray | memoryview) -> int:
        view = memoryview(payload)
        written = self._handle.write(view)
        self._digest.update(view[:written])
        self._position += int(written)
        return int(written)

    def tell(self) -> int:
        return self._position

    def flush(self) -> None:
        self._handle.flush()

    def seekable(self) -> bool:
        return False

    def writable(self) -> bool:
        return True

    def hexdigest(self) -> str:
        return self._digest.hexdigest()


class Data7ArchiveError(RuntimeError):
    """Raised when a DATA7 archive is incomplete, corrupt, or inconsistent."""


def sha256_file(path: Path) -> str:
    return sha256_file_cached(path)


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o600 << 16
    return info


def _write_jsonl_member(
    archive: zipfile.ZipFile,
    name: str,
    values: Iterable[Any],
) -> int:
    count = 0
    with archive.open(_zip_info(name), "w", force_zip64=True) as handle:
        for value in values:
            handle.write((canonical_json(value.to_dict()) + "\n").encode("utf-8"))
            count += 1
    return count


def _write_reason_codes_member(
    archive: zipfile.ZipFile,
    name: str,
    reason_codes: Iterable[Iterable[str]],
) -> int:
    count = 0
    with archive.open(_zip_info(name), "w", force_zip64=True) as handle:
        for row in reason_codes:
            handle.write(
                (canonical_json(list(row)) + "\n").encode("utf-8")
            )
            count += 1
    return count


def _write_npy_member(
    archive: zipfile.ZipFile,
    name: str,
    array: np.ndarray,
) -> tuple[tuple[int, ...], str]:
    contiguous = np.ascontiguousarray(array)
    with archive.open(_zip_info(name), "w", force_zip64=True) as handle:
        np.save(handle, contiguous, allow_pickle=False)
    return tuple(int(value) for value in contiguous.shape), contiguous.dtype.str


def _block_member_name(index: int, kind: str) -> str:
    return f"feature-blocks/{index:04d}-{kind}.npy"


def _block_manifest(index: int, metric: FittedFeatureBlockMetric) -> dict[str, Any]:
    projection = np.asarray(metric.projection, dtype=np.float64)
    if projection.size == 0:
        projection = np.empty((0, len(metric.input_feature_names)), dtype=np.float64)
    return {
        "schema": FITTED_FEATURE_BLOCK_SCHEMA,
        "content_digest": metric.content_digest,
        "block_name": metric.block_name,
        "input_feature_names": list(metric.input_feature_names),
        "center_member": _block_member_name(index, "center"),
        "center_shape": [len(metric.center)],
        "center_dtype": np.dtype(np.float64).str,
        "scale_member": _block_member_name(index, "scale"),
        "scale_shape": [len(metric.scale)],
        "scale_dtype": np.dtype(np.float64).str,
        "projection_member": _block_member_name(index, "projection"),
        "projection_shape": list(projection.shape),
        "projection_dtype": projection.dtype.str,
        "output_dimension": metric.output_dimension,
        "weight_factor": metric.weight_factor,
        "policy_digest": metric.policy_digest,
    }


def _manifest_for_bundle(bundle: Data7PreparationBundle) -> dict[str, Any]:
    metric = bundle.fitted_metric
    table = metric.frame_feature_table
    weights = bundle.training_weights
    return {
        "schema": DATA7_ARCHIVE_MANIFEST_SCHEMA,
        "bundle_content_digest": bundle.content_digest,
        "dataset_id": bundle.dataset_id,
        "source_catalog_digest": bundle.source_catalog_digest,
        "frame_catalog_digest": bundle.frame_catalog_digest,
        "data4_bundle_digest": bundle.data4_bundle_digest,
        "data5_bundle_digest": bundle.data5_bundle_digest,
        "data6_bundle_digest": bundle.data6_bundle_digest,
        "domain": bundle.domain.to_dict(),
        "fitted_metric": {
            "schema": FITTED_FEATURE_METRIC_SCHEMA,
            "parser_version": MLFF_DATA7_PARSER_VERSION,
            "content_digest": metric.content_digest,
            "domain": metric.domain.to_dict(),
            "policy": metric.policy.to_dict(),
            "data4_bundle_digest": metric.data4_bundle_digest,
            "data6_bundle_digest": metric.data6_bundle_digest,
            "block_metrics": [
                _block_manifest(index, item)
                for index, item in enumerate(metric.block_metrics)
            ],
            "frame_feature_table": {
                "schema": TRANSFORMED_FRAME_FEATURE_TABLE_SCHEMA,
                "content_digest": table.content_digest,
                "frame_uids": list(table.frame_uids),
                "member": _DATA7_MATRIX_MEMBER,
                "shape": list(table.values.shape),
                "dtype": table.values.dtype.str,
            },
        },
        "atomic_reference_fit": bundle.atomic_reference_fit.to_dict(),
        "training_weights": {
            "schema": TRAINING_WEIGHT_CATALOG_SCHEMA,
            "content_digest": weights.content_digest,
            "domain": weights.domain.to_dict(),
            "objective_policy": weights.objective_policy.to_dict(),
            "configuration_policy": weights.configuration_policy.to_dict(),
            "data4_bundle_digest": weights.data4_bundle_digest,
            "data5_bundle_digest": weights.data5_bundle_digest,
            "frame_uids": list(weights.records.frame_uids),
            "configuration_member": _DATA7_WEIGHT_CONFIGURATION_MEMBER,
            "energy_member": _DATA7_WEIGHT_ENERGY_MEMBER,
            "forces_member": _DATA7_WEIGHT_FORCES_MEMBER,
            "stress_member": _DATA7_WEIGHT_STRESS_MEMBER,
            "reasons_member": _DATA7_WEIGHT_REASONS_MEMBER,
            "record_count": len(weights.records),
        },
        "checkpoint_metric_policy": bundle.checkpoint_metric_policy.to_dict(),
        "selection_plan": bundle.selection_plan.to_dict(),
        "coverage_report": bundle.coverage_report.to_dict(),
        "notes": list(bundle.notes),
    }


def write_data7_archive(
    bundle: Data7PreparationBundle,
    path: str | Path,
) -> str:
    """Atomically write a compact DATA7 archive and return its file SHA-256."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.tmp-", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        manifest = _manifest_for_bundle(bundle)
        with temporary.open("wb") as raw_handle:
            hashing_handle = _SequentialHashingWriter(raw_handle)
            with zipfile.ZipFile(
                hashing_handle,
                mode="w",
                compression=zipfile.ZIP_STORED,
                allowZip64=True,
                strict_timestamps=True,
            ) as archive:
                shape, dtype = _write_npy_member(
                    archive,
                    _DATA7_MATRIX_MEMBER,
                    bundle.fitted_metric.frame_feature_table.values,
                )
                table_meta = manifest["fitted_metric"]["frame_feature_table"]
                if list(shape) != table_meta["shape"] or dtype != table_meta["dtype"]:
                    raise Data7ArchiveError("DATA7 matrix changed while writing.")

                for index, metric in enumerate(bundle.fitted_metric.block_metrics):
                    center = np.asarray(metric.center, dtype=np.float64)
                    scale = np.asarray(metric.scale, dtype=np.float64)
                    projection = np.asarray(metric.projection, dtype=np.float64)
                    if projection.size == 0:
                        projection = np.empty(
                            (0, len(metric.input_feature_names)), dtype=np.float64
                        )
                    _write_npy_member(archive, _block_member_name(index, "center"), center)
                    _write_npy_member(archive, _block_member_name(index, "scale"), scale)
                    _write_npy_member(
                        archive, _block_member_name(index, "projection"), projection
                    )

                weight_table = bundle.training_weights.records
                if not isinstance(weight_table, FrameTrainingWeightTable):
                    weight_table = FrameTrainingWeightTable.from_records(
                        tuple(weight_table)
                    )
                _write_npy_member(
                    archive,
                    _DATA7_WEIGHT_CONFIGURATION_MEMBER,
                    weight_table.configuration_weights,
                )
                _write_npy_member(
                    archive,
                    _DATA7_WEIGHT_ENERGY_MEMBER,
                    weight_table.energy_weights,
                )
                _write_npy_member(
                    archive,
                    _DATA7_WEIGHT_FORCES_MEMBER,
                    weight_table.forces_weights,
                )
                _write_npy_member(
                    archive,
                    _DATA7_WEIGHT_STRESS_MEMBER,
                    weight_table.stress_weights,
                )
                count = _write_reason_codes_member(
                    archive,
                    _DATA7_WEIGHT_REASONS_MEMBER,
                    weight_table.reason_codes,
                )
                if count != manifest["training_weights"]["record_count"]:
                    raise Data7ArchiveError(
                        "DATA7 training-weight count changed while writing."
                    )
                archive.writestr(
                    _zip_info(_DATA7_MANIFEST_MEMBER),
                    canonical_json(manifest).encode("utf-8") + b"\n",
                )
            hashing_handle.flush()
            os.fsync(raw_handle.fileno())
            archive_sha256 = hashing_handle.hexdigest()
        os.replace(temporary, destination)
        return archive_sha256
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _safe_member_names(archive: zipfile.ZipFile) -> set[str]:
    names: set[str] = set()
    for info in archive.infolist():
        member = Path(info.filename)
        if member.is_absolute() or ".." in member.parts:
            raise Data7ArchiveError("DATA7 archive contains an unsafe member path.")
        if info.filename in names:
            raise Data7ArchiveError("DATA7 archive contains duplicate members.")
        names.add(info.filename)
    return names


def _read_weights(
    archive: zipfile.ZipFile,
    member: str,
    expected_count: int,
) -> tuple[FrameTrainingWeight, ...]:
    result: list[FrameTrainingWeight] = []
    with archive.open(member, "r") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise Data7ArchiveError(
                    f"Invalid DATA7 training-weight JSON at line {line_number}."
                ) from exc
            result.append(FrameTrainingWeight.from_dict(payload))
    if len(result) != int(expected_count):
        raise Data7ArchiveError(
            "DATA7 training-weight record count does not match the manifest."
        )
    return tuple(result)


def _read_reason_codes(
    archive: zipfile.ZipFile,
    member: str,
    expected_count: int,
) -> tuple[tuple[str, ...], ...]:
    result: list[tuple[str, ...]] = []
    with archive.open(member, "r") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise Data7ArchiveError(
                    f"Invalid DATA7 training-weight reason JSON at line {line_number}."
                ) from exc
            if not isinstance(payload, list):
                raise Data7ArchiveError(
                    "DATA7 training-weight reason row must be a JSON list."
                )
            result.append(tuple(str(value) for value in payload))
    if len(result) != int(expected_count):
        raise Data7ArchiveError(
            "DATA7 training-weight reason count does not match the manifest."
        )
    return tuple(result)


def _read_npy_member(archive: zipfile.ZipFile, member: str) -> np.ndarray:
    with archive.open(member, "r") as handle:
        return np.load(handle, allow_pickle=False)


def _npy_memmap_from_stored_member(
    archive_path: Path,
    archive: zipfile.ZipFile,
    member: str,
) -> np.ndarray:
    info = archive.getinfo(member)
    if info.compress_type != zipfile.ZIP_STORED:
        return _read_npy_member(archive, member)
    with archive_path.open("rb") as handle:
        handle.seek(info.header_offset)
        header = handle.read(_LOCAL_FILE_HEADER.size)
        if len(header) != _LOCAL_FILE_HEADER.size:
            raise Data7ArchiveError("DATA7 ZIP member header is truncated.")
        fields = _LOCAL_FILE_HEADER.unpack(header)
        if fields[0] != _LOCAL_FILE_SIGNATURE:
            raise Data7ArchiveError("DATA7 ZIP member header signature is invalid.")
        name_length, extra_length = int(fields[-2]), int(fields[-1])
        npy_start = info.header_offset + _LOCAL_FILE_HEADER.size + name_length + extra_length
        handle.seek(npy_start)
        version = np.lib.format.read_magic(handle)
        if version == (1, 0):
            shape, fortran_order, dtype = np.lib.format.read_array_header_1_0(handle)
        elif version in {(2, 0), (3, 0)}:
            shape, fortran_order, dtype = np.lib.format.read_array_header_2_0(handle)
        else:
            raise Data7ArchiveError(f"Unsupported DATA7 NPY version {version!r}.")
        data_offset = handle.tell()
    return np.memmap(
        archive_path,
        mode="r",
        dtype=dtype,
        offset=data_offset,
        shape=shape,
        order="F" if fortran_order else "C",
    )


def _metric_from_v2_manifest(
    archive_path: Path,
    archive: zipfile.ZipFile,
    metric_meta: Mapping[str, Any],
    table: TransformedFrameFeatureTable,
    *,
    authenticated: bool,
) -> FittedFeatureMetric:
    block_metrics: list[FittedFeatureBlockMetric] = []
    for block_meta in metric_meta["block_metrics"]:
        member_loader = (
            lambda member: _npy_memmap_from_stored_member(
                archive_path, archive, member
            )
            if authenticated
            else _read_npy_member(archive, member)
        )
        center = member_loader(str(block_meta["center_member"]))
        scale = member_loader(str(block_meta["scale_member"]))
        projection = member_loader(str(block_meta["projection_member"]))
        if list(center.shape) != list(block_meta["center_shape"]):
            raise Data7ArchiveError("DATA7 block-center shape mismatch.")
        if list(scale.shape) != list(block_meta["scale_shape"]):
            raise Data7ArchiveError("DATA7 block-scale shape mismatch.")
        if list(projection.shape) != list(block_meta["projection_shape"]):
            raise Data7ArchiveError("DATA7 block-projection shape mismatch.")
        if authenticated:
            metric = FittedFeatureBlockMetric._from_authenticated_arrays(
                block_name=str(block_meta["block_name"]),
                input_feature_names=tuple(
                    str(value) for value in block_meta["input_feature_names"]
                ),
                center=center,
                scale=scale,
                projection=projection,
                output_dimension=int(block_meta["output_dimension"]),
                weight_factor=float(block_meta["weight_factor"]),
                policy_digest=str(block_meta["policy_digest"]),
                content_digest=str(block_meta["content_digest"]),
            )
        else:
            metric = FittedFeatureBlockMetric(
                block_name=str(block_meta["block_name"]),
                input_feature_names=tuple(
                    str(value) for value in block_meta["input_feature_names"]
                ),
                center=center,
                scale=scale,
                projection=projection,
                output_dimension=int(block_meta["output_dimension"]),
                weight_factor=float(block_meta["weight_factor"]),
                policy_digest=str(block_meta["policy_digest"]),
            )
            if metric.content_digest != str(block_meta["content_digest"]):
                raise Data7ArchiveError("DATA7 fitted-feature block digest mismatch.")
        block_metrics.append(metric)
    metric = FittedFeatureMetric(
        domain=FeatureFitDomain.from_dict(metric_meta["domain"]),
        policy=FeatureMetricPolicyTemplate.from_dict(metric_meta["policy"]),
        data4_bundle_digest=str(metric_meta["data4_bundle_digest"]),
        data6_bundle_digest=str(metric_meta["data6_bundle_digest"]),
        block_metrics=tuple(block_metrics),
        frame_features=table,
    )
    parser_version = str(metric_meta.get("parser_version", MLFF_DATA7_PARSER_VERSION))
    if parser_version not in {
        MLFF_DATA7_PARSER_VERSION,
        MLFF_DATA7_V63_PARSER_VERSION,
        MLFF_DATA7_LEGACY_PARSER_VERSION,
    }:
        raise Data7ArchiveError("Unsupported DATA7 fitted-metric parser version.")
    object.__setattr__(metric, "_serialization_parser_version", parser_version)
    return metric


def read_data7_archive(
    path: str | Path,
    *,
    expected_sha256: str | None = None,
) -> Data7PreparationBundle:
    """Read and scientifically verify a compact DATA7 archive."""

    archive_path = Path(path)
    if expected_sha256 is not None and sha256_file(archive_path) != expected_sha256:
        raise Data7ArchiveError("DATA7 archive checksum mismatch.")
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            names = _safe_member_names(archive)
            required = {
                _DATA7_MANIFEST_MEMBER,
                _DATA7_MATRIX_MEMBER,
            }
            if not required.issubset(names):
                raise Data7ArchiveError("DATA7 archive is missing required members.")
            manifest = json.loads(archive.read(_DATA7_MANIFEST_MEMBER))
            schema = manifest.get("schema")
            if schema not in {
                DATA7_ARCHIVE_MANIFEST_SCHEMA,
                DATA7_ARCHIVE_MANIFEST_V2_SCHEMA,
                DATA7_ARCHIVE_MANIFEST_LEGACY_SCHEMA,
            }:
                raise Data7ArchiveError("Unsupported DATA7 archive manifest schema.")
            table_meta = manifest["fitted_metric"]["frame_feature_table"]
            values = _npy_memmap_from_stored_member(
                archive_path, archive, str(table_meta["member"])
            )
            expected_shape = tuple(int(v) for v in table_meta["shape"])
            expected_dtype = str(table_meta["dtype"])
            if values.shape != expected_shape or values.dtype.str != expected_dtype:
                raise Data7ArchiveError("DATA7 fitted-frame matrix metadata mismatch.")
            if expected_sha256 is not None:
                table = TransformedFrameFeatureTable._from_authenticated_arrays(
                    frame_uids=tuple(str(v) for v in table_meta["frame_uids"]),
                    values=values,
                    content_digest=str(table_meta["content_digest"]),
                )
            else:
                table = TransformedFrameFeatureTable(
                    frame_uids=tuple(str(v) for v in table_meta["frame_uids"]),
                    values=values,
                )
                if table.content_digest != str(table_meta["content_digest"]):
                    raise Data7ArchiveError("DATA7 fitted-frame matrix digest mismatch.")

            metric_meta = manifest["fitted_metric"]
            if schema in {
                DATA7_ARCHIVE_MANIFEST_SCHEMA,
                DATA7_ARCHIVE_MANIFEST_V2_SCHEMA,
            }:
                dynamic_members = {
                    str(block[key])
                    for block in metric_meta["block_metrics"]
                    for key in (
                        "center_member",
                        "scale_member",
                        "projection_member",
                    )
                }
                if not dynamic_members.issubset(names):
                    raise Data7ArchiveError(
                        "DATA7 archive is missing fitted-feature array members."
                    )
                metric = _metric_from_v2_manifest(
                    archive_path,
                    archive,
                    metric_meta,
                    table,
                    authenticated=expected_sha256 is not None,
                )
            else:
                metric = FittedFeatureMetric(
                    domain=FeatureFitDomain.from_dict(metric_meta["domain"]),
                    policy=FeatureMetricPolicyTemplate.from_dict(metric_meta["policy"]),
                    data4_bundle_digest=str(metric_meta["data4_bundle_digest"]),
                    data6_bundle_digest=str(metric_meta["data6_bundle_digest"]),
                    block_metrics=tuple(
                        FittedFeatureBlockMetric.from_dict(item)
                        for item in metric_meta["block_metrics"]
                    ),
                    frame_features=table,
                )
                parser_version = str(metric_meta.get("parser_version", MLFF_DATA7_PARSER_VERSION))
                if parser_version not in {
                    MLFF_DATA7_PARSER_VERSION,
                    MLFF_DATA7_V63_PARSER_VERSION,
                    MLFF_DATA7_LEGACY_PARSER_VERSION,
                }:
                    raise Data7ArchiveError("Unsupported DATA7 fitted-metric parser version.")
                object.__setattr__(metric, "_serialization_parser_version", parser_version)
            if metric.content_digest != str(metric_meta["content_digest"]):
                raise Data7ArchiveError("DATA7 fitted-metric digest mismatch.")

            weight_meta = manifest["training_weights"]
            if schema == DATA7_ARCHIVE_MANIFEST_SCHEMA:
                weight_members = {
                    str(weight_meta["configuration_member"]),
                    str(weight_meta["energy_member"]),
                    str(weight_meta["forces_member"]),
                    str(weight_meta["stress_member"]),
                    str(weight_meta["reasons_member"]),
                }
                if not weight_members.issubset(names):
                    raise Data7ArchiveError(
                        "DATA7 archive is missing columnar training-weight members."
                    )
                weight_table = FrameTrainingWeightTable._from_authenticated_arrays(
                    frame_uids=tuple(str(v) for v in weight_meta["frame_uids"]),
                    configuration_weights=_npy_memmap_from_stored_member(
                        archive_path, archive, str(weight_meta["configuration_member"])
                    ),
                    energy_weights=_npy_memmap_from_stored_member(
                        archive_path, archive, str(weight_meta["energy_member"])
                    ),
                    forces_weights=_npy_memmap_from_stored_member(
                        archive_path, archive, str(weight_meta["forces_member"])
                    ),
                    stress_weights=_npy_memmap_from_stored_member(
                        archive_path, archive, str(weight_meta["stress_member"])
                    ),
                    reason_codes=_read_reason_codes(
                        archive,
                        str(weight_meta["reasons_member"]),
                        int(weight_meta["record_count"]),
                    ),
                )
                weight_records = weight_table
            else:
                records_member = str(weight_meta["records_member"])
                if records_member not in names:
                    raise Data7ArchiveError(
                        "DATA7 archive is missing legacy training weights."
                    )
                weight_records = _read_weights(
                    archive,
                    records_member,
                    int(weight_meta["record_count"]),
                )
            weights = TrainingWeightCatalog(
                domain=FeatureFitDomain.from_dict(weight_meta["domain"]),
                objective_policy=TrainingObjectivePolicy.from_dict(
                    weight_meta["objective_policy"]
                ),
                configuration_policy=ConfigurationWeightPolicy.from_dict(
                    weight_meta["configuration_policy"]
                ),
                data4_bundle_digest=str(weight_meta["data4_bundle_digest"]),
                data5_bundle_digest=str(weight_meta["data5_bundle_digest"]),
                records=weight_records,
            )
            if expected_sha256 is not None and schema == DATA7_ARCHIVE_MANIFEST_SCHEMA:
                object.__setattr__(
                    weights,
                    "_content_digest_cache",
                    str(weight_meta["content_digest"]),
                )
            elif weights.content_digest != str(weight_meta["content_digest"]):
                raise Data7ArchiveError("DATA7 training-weight digest mismatch.")

            bundle = Data7PreparationBundle(
                dataset_id=str(manifest["dataset_id"]),
                source_catalog_digest=str(manifest["source_catalog_digest"]),
                frame_catalog_digest=str(manifest["frame_catalog_digest"]),
                data4_bundle_digest=str(manifest["data4_bundle_digest"]),
                data5_bundle_digest=str(manifest["data5_bundle_digest"]),
                data6_bundle_digest=str(manifest["data6_bundle_digest"]),
                domain=FeatureFitDomain.from_dict(manifest["domain"]),
                fitted_metric=metric,
                atomic_reference_fit=AtomicReferenceFitRecord.from_dict(
                    manifest["atomic_reference_fit"]
                ),
                training_weights=weights,
                checkpoint_metric_policy=CheckpointMetricPolicy.from_dict(
                    manifest["checkpoint_metric_policy"]
                ),
                selection_plan=TrainingSelectionPlan.from_dict(
                    manifest["selection_plan"]
                ),
                coverage_report=SelectionCoverageReport.from_dict(
                    manifest["coverage_report"]
                ),
                notes=tuple(str(v) for v in manifest.get("notes", ())),
            )
            parser_version = str(manifest.get("parser_version", MLFF_DATA7_PARSER_VERSION))
            if parser_version not in {
                MLFF_DATA7_PARSER_VERSION,
                MLFF_DATA7_V63_PARSER_VERSION,
                MLFF_DATA7_LEGACY_PARSER_VERSION,
            }:
                raise Data7ArchiveError("Unsupported DATA7 bundle parser version.")
            object.__setattr__(bundle, "_serialization_parser_version", parser_version)
            if bundle.content_digest != str(manifest["bundle_content_digest"]):
                raise Data7ArchiveError("DATA7 bundle scientific digest mismatch.")
            return bundle
    except (OSError, zipfile.BadZipFile, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, Data7ArchiveError):
            raise
        raise Data7ArchiveError(f"Cannot read DATA7 archive {archive_path}.") from exc
