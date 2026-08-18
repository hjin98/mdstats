"""Persistent label-independent prediction artifacts for checkpoint evaluation.

OPT-EVAL2 separates expensive model inference from cheap reference-label/metric
reduction.  Prediction cache identities deliberately exclude reference labels and
metric thresholds, while binding the model/head, geometry order, dtype, device,
acceleration backend, and the critical-precision execution contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import json
import os
import tempfile
import threading
from typing import Any, Mapping, Sequence

import numpy as np

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    sha256_file_cached,
    validate_digest,
)
from .model_features import AtomicModelPrediction

EVALUATION_PREDICTION_KEY_SCHEMA = "mdstats.evaluation-prediction-key.v2"
EVALUATION_PREDICTION_KEY_V1_SCHEMA = "mdstats.evaluation-prediction-key.v1"
EVALUATION_PREDICTION_ARTIFACT_SCHEMA = "mdstats.evaluation-prediction-artifact.v1"
EVALUATION_PREDICTION_NUMERICAL_CONTRACT = "mdstats.mace-evaluation-prediction.2026-08.v1"
EVALUATION_PREDICTION_COVERAGE_SCHEMA = "mdstats.evaluation-prediction-coverage.v1"
_COVERAGE_LOCK = threading.RLock()


def geometry_order_digest(geometry_identities: Sequence[str]) -> str:
    """Digest an ordered geometry identity sequence independently of labels."""

    values = tuple(str(value) for value in geometry_identities)
    if not values:
        raise TrainingDataInputError("Prediction geometry identity sequence cannot be empty.")
    if any(not value.strip() for value in values):
        raise TrainingDataInputError("Prediction geometry identities must be non-empty.")
    return digest(
        {
            "schema": "mdstats.evaluation-geometry-order.v1",
            "configuration_count": len(values),
            "geometry_identities": list(values),
        }
    )


@dataclass(frozen=True, slots=True)
class EvaluationPredictionKey:
    model_sha256: str
    head_name: str | None
    geometry_order_digest: str
    configuration_count: int
    default_dtype: str
    device: str
    acceleration_policy_digest: str
    foundation_inference_digest: str | None = None
    numerical_contract: str = EVALUATION_PREDICTION_NUMERICAL_CONTRACT
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_sha256", validate_digest(self.model_sha256, name="model_sha256"))
        object.__setattr__(
            self,
            "geometry_order_digest",
            validate_digest(self.geometry_order_digest, name="geometry_order_digest"),
        )
        object.__setattr__(
            self,
            "acceleration_policy_digest",
            validate_digest(self.acceleration_policy_digest, name="acceleration_policy_digest"),
        )
        head = None if self.head_name in (None, "") else str(self.head_name)
        object.__setattr__(self, "head_name", head)
        if self.foundation_inference_digest is not None:
            object.__setattr__(
                self,
                "foundation_inference_digest",
                validate_digest(self.foundation_inference_digest, name="foundation_inference_digest"),
            )
        if int(self.configuration_count) <= 0:
            raise TrainingDataInputError("Prediction configuration_count must be positive.")
        object.__setattr__(self, "configuration_count", int(self.configuration_count))
        if self.default_dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("Prediction dtype must be float32 or float64.")
        if not str(self.device).strip() or not str(self.numerical_contract).strip():
            raise TrainingDataInputError("Prediction device/numerical contract must be non-empty.")

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": (
                EVALUATION_PREDICTION_KEY_SCHEMA
                if self.foundation_inference_digest is not None
                else EVALUATION_PREDICTION_KEY_V1_SCHEMA
            ),
            "model_sha256": self.model_sha256,
            "head_name": self.head_name,
            "geometry_order_digest": self.geometry_order_digest,
            "configuration_count": self.configuration_count,
            "default_dtype": self.default_dtype,
            "device": self.device,
            "acceleration_policy_digest": self.acceleration_policy_digest,
            "numerical_contract": self.numerical_contract,
        }
        if self.foundation_inference_digest is not None:
            payload["foundation_inference_digest"] = self.foundation_inference_digest
        return payload

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EvaluationPredictionKey":
        if payload.get("schema") not in {EVALUATION_PREDICTION_KEY_SCHEMA, EVALUATION_PREDICTION_KEY_V1_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported evaluation-prediction key schema.")
        result = cls(
            model_sha256=str(payload["model_sha256"]),
            head_name=None if payload.get("head_name") in (None, "") else str(payload["head_name"]),
            geometry_order_digest=str(payload["geometry_order_digest"]),
            configuration_count=int(payload["configuration_count"]),
            default_dtype=str(payload["default_dtype"]),
            device=str(payload["device"]),
            acceleration_policy_digest=str(payload["acceleration_policy_digest"]),
            foundation_inference_digest=(None if payload.get("foundation_inference_digest") in (None, "") else str(payload["foundation_inference_digest"])),
            numerical_contract=str(payload.get("numerical_contract", EVALUATION_PREDICTION_NUMERICAL_CONTRACT)),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Evaluation-prediction key digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class EvaluationPredictionArtifact:
    key: EvaluationPredictionKey
    relative_path: str
    file_sha256: str
    total_atom_count: int
    force_dtype: str
    stress_present_count: int
    source_kind: str
    source_digest: str | None = None
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        path = Path(self.relative_path)
        if path.is_absolute() or ".." in path.parts or not self.relative_path.strip():
            raise TrainingDataInputError("Evaluation prediction artifact path must be safe and relative.")
        object.__setattr__(self, "file_sha256", validate_digest(self.file_sha256, name="file_sha256"))
        if self.source_digest is not None:
            object.__setattr__(self, "source_digest", validate_digest(self.source_digest, name="source_digest"))
        if int(self.total_atom_count) <= 0:
            raise TrainingDataInputError("Prediction artifact total atom count must be positive.")
        object.__setattr__(self, "total_atom_count", int(self.total_atom_count))
        if np.dtype(self.force_dtype).kind != "f":
            raise TrainingDataInputError("Prediction artifact force dtype must be floating point.")
        count = int(self.stress_present_count)
        if count < 0 or count > self.key.configuration_count:
            raise TrainingDataInputError("Prediction artifact stress count is invalid.")
        object.__setattr__(self, "stress_present_count", count)
        if not str(self.source_kind).strip():
            raise TrainingDataInputError("Prediction artifact source kind must be non-empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": EVALUATION_PREDICTION_ARTIFACT_SCHEMA,
            "key": self.key.to_dict(),
            "relative_path": self.relative_path,
            "file_sha256": self.file_sha256,
            "total_atom_count": self.total_atom_count,
            "force_dtype": self.force_dtype,
            "stress_present_count": self.stress_present_count,
            "source_kind": self.source_kind,
            "source_digest": self.source_digest,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EvaluationPredictionArtifact":
        if payload.get("schema") != EVALUATION_PREDICTION_ARTIFACT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported evaluation-prediction artifact schema.")
        result = cls(
            key=EvaluationPredictionKey.from_dict(payload["key"]),
            relative_path=str(payload["relative_path"]),
            file_sha256=str(payload["file_sha256"]),
            total_atom_count=int(payload["total_atom_count"]),
            force_dtype=str(payload["force_dtype"]),
            stress_present_count=int(payload["stress_present_count"]),
            source_kind=str(payload.get("source_kind", "model_inference")),
            source_digest=None if payload.get("source_digest") is None else str(payload["source_digest"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Evaluation-prediction artifact digest mismatch.")
        return result


def prediction_key(
    *,
    model_sha256: str,
    head_name: str | None,
    geometry_identities: Sequence[str],
    default_dtype: str,
    device: str,
    acceleration_policy_digest: str,
    foundation_inference_digest: str | None = None,
) -> EvaluationPredictionKey:
    values = tuple(str(value) for value in geometry_identities)
    return EvaluationPredictionKey(
        model_sha256=model_sha256,
        head_name=head_name,
        geometry_order_digest=geometry_order_digest(values),
        configuration_count=len(values),
        default_dtype=default_dtype,
        device=device,
        acceleration_policy_digest=acceleration_policy_digest,
        foundation_inference_digest=foundation_inference_digest,
    )



def _coverage_identity_payload(key: EvaluationPredictionKey) -> dict[str, Any]:
    return {
        "schema": EVALUATION_PREDICTION_COVERAGE_SCHEMA,
        "model_sha256": key.model_sha256,
        "head_name": key.head_name,
        "default_dtype": key.default_dtype,
        "device": key.device,
        "acceleration_policy_digest": key.acceleration_policy_digest,
        "numerical_contract": key.numerical_contract,
        **({"foundation_inference_digest": key.foundation_inference_digest} if key.foundation_inference_digest is not None else {}),
    }


def _coverage_index_path(root_directory: str | Path, key: EvaluationPredictionKey) -> Path:
    root = Path(root_directory).resolve()
    token = digest(_coverage_identity_payload(key))
    return root / "coverage" / token[:2] / f"{token}.json"


def _update_coverage_index(
    root_directory: str | Path,
    key: EvaluationPredictionKey,
    geometry_identities: Sequence[str],
    artifact: EvaluationPredictionArtifact,
) -> None:
    values = tuple(str(value) for value in geometry_identities)
    if len(values) != key.configuration_count:
        raise TrainingDataInputError("Coverage geometry count does not match prediction key.")
    path = _coverage_index_path(root_directory, key)
    with _COVERAGE_LOCK:
        entries: list[dict[str, Any]] = []
        if path.is_file():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if payload.get("identity") == _coverage_identity_payload(key):
                    entries = [dict(item) for item in payload.get("entries", ())]
            except Exception:
                entries = []
        entry = {
            "prediction_key_digest": key.content_digest,
            "prediction_artifact_digest": artifact.content_digest,
            "geometry_identities": list(values),
        }
        entries = [item for item in entries if item.get("prediction_key_digest") != key.content_digest]
        entries.append(entry)
        entries.sort(key=lambda item: str(item.get("prediction_key_digest", "")))
        payload = {
            "schema": EVALUATION_PREDICTION_COVERAGE_SCHEMA,
            "identity": _coverage_identity_payload(key),
            "entries": entries,
        }
        _atomic_json(path, payload)


def _coverage_entries(
    root_directory: str | Path,
    template_key: EvaluationPredictionKey,
) -> tuple[tuple[EvaluationPredictionKey, tuple[str, ...]], ...]:
    path = _coverage_index_path(root_directory, template_key)
    if not path.is_file():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != EVALUATION_PREDICTION_COVERAGE_SCHEMA:
            return ()
        if payload.get("identity") != _coverage_identity_payload(template_key):
            return ()
        result = []
        for item in payload.get("entries", ()):
            geometries = tuple(str(value) for value in item.get("geometry_identities", ()))
            if not geometries:
                continue
            key = prediction_key(
                model_sha256=template_key.model_sha256,
                head_name=template_key.head_name,
                geometry_identities=geometries,
                default_dtype=template_key.default_dtype,
                device=template_key.device,
                acceleration_policy_digest=template_key.acceleration_policy_digest,
                foundation_inference_digest=template_key.foundation_inference_digest,
            )
            if key.content_digest != item.get("prediction_key_digest"):
                continue
            result.append((key, geometries))
        return tuple(result)
    except Exception:
        return ()


def load_evaluation_prediction_coverage(
    root_directory: str | Path,
    *,
    model_sha256: str,
    head_name: str | None,
    geometry_identities: Sequence[str],
    default_dtype: str,
    device: str,
    acceleration_policy_digest: str,
    foundation_inference_digest: str | None = None,
) -> tuple[AtomicModelPrediction, ...] | None:
    """Compose authenticated prediction shards for an arbitrary ordered subset.

    EVAL-MF1 stores each newly-added monitor delta as an ordinary immutable
    prediction artifact.  This index lets a later nested round reconstruct the
    cumulative prefix without repeating inference on previously covered frames.
    """

    requested = tuple(str(value) for value in geometry_identities)
    if not requested:
        raise TrainingDataInputError("Prediction coverage request cannot be empty.")
    template = prediction_key(
        model_sha256=model_sha256,
        head_name=head_name,
        geometry_identities=requested,
        default_dtype=default_dtype,
        device=device,
        acceleration_policy_digest=acceleration_policy_digest,
        foundation_inference_digest=foundation_inference_digest,
    )
    exact = load_evaluation_prediction_artifact(root_directory, template)
    if exact is not None:
        return exact[1]
    wanted = set(requested)
    found: dict[str, AtomicModelPrediction] = {}
    for shard_key, shard_geometries in _coverage_entries(root_directory, template):
        if not wanted.intersection(shard_geometries):
            continue
        loaded = load_evaluation_prediction_artifact(root_directory, shard_key)
        if loaded is None:
            continue
        _, predictions = loaded
        for geometry, prediction in zip(shard_geometries, predictions):
            if geometry in wanted and geometry not in found:
                found[geometry] = prediction
        if len(found) == len(wanted):
            break
    if len(found) != len(wanted):
        return None
    return tuple(found[geometry] for geometry in requested)


def evaluation_prediction_coverage_has(
    root_directory: str | Path,
    *,
    model_sha256: str,
    head_name: str | None,
    geometry_identities: Sequence[str],
    default_dtype: str,
    device: str,
    acceleration_policy_digest: str,
    foundation_inference_digest: str | None = None,
) -> bool:
    requested = tuple(str(value) for value in geometry_identities)
    if not requested:
        return False
    template = prediction_key(
        model_sha256=model_sha256,
        head_name=head_name,
        geometry_identities=requested,
        default_dtype=default_dtype,
        device=device,
        acceleration_policy_digest=acceleration_policy_digest,
        foundation_inference_digest=foundation_inference_digest,
    )
    if evaluation_prediction_cache_has(root_directory, template):
        return True
    wanted = set(requested)
    covered: set[str] = set()
    for shard_key, shard_geometries in _coverage_entries(root_directory, template):
        overlap = wanted.intersection(shard_geometries)
        if not overlap:
            continue
        if load_evaluation_prediction_artifact_record(root_directory, shard_key) is None:
            continue
        covered.update(overlap)
        if covered == wanted:
            return True
    return False

def _artifact_paths(root_directory: str | Path, key: EvaluationPredictionKey) -> tuple[Path, Path]:
    root = Path(root_directory).resolve()
    token = key.content_digest
    directory = root / token[:2]
    return directory / f"{token}.json", directory / f"{token}.npz"


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        temporary.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _atomic_npz(path: Path, **arrays: np.ndarray) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        with temporary.open("wb") as handle:
            np.savez(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        file_sha = sha256_file_cached(temporary)
        os.replace(temporary, path)
        return file_sha
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def write_evaluation_prediction_artifact(
    root_directory: str | Path,
    key: EvaluationPredictionKey,
    predictions: Sequence[AtomicModelPrediction],
    *,
    source_kind: str,
    source_digest: str | None = None,
    geometry_identities: Sequence[str] | None = None,
) -> EvaluationPredictionArtifact:
    values = tuple(predictions)
    if len(values) != key.configuration_count:
        raise TrainingDataInputError("Prediction artifact count does not match its cache key.")
    if not values:
        raise TrainingDataInputError("Prediction artifact cannot be empty.")
    energies = np.asarray([float(item.energy_ev) for item in values], dtype=np.float64)
    force_arrays = [np.ascontiguousarray(item.forces_ev_per_angstrom) for item in values]
    if any(array.ndim != 2 or array.shape[1] != 3 or array.shape[0] <= 0 for array in force_arrays):
        raise TrainingDataInputError("Prediction force arrays must have shape (n_atoms, 3).")
    if any(np.any(~np.isfinite(array)) for array in force_arrays) or np.any(~np.isfinite(energies)):
        raise TrainingDataInputError("Prediction artifact contains non-finite energy/force values.")
    force_dtype = np.result_type(*(array.dtype for array in force_arrays))
    if force_dtype.kind != "f":
        force_dtype = np.dtype(np.float64)
    force_arrays = [np.ascontiguousarray(array, dtype=force_dtype) for array in force_arrays]
    offsets = np.zeros(len(force_arrays) + 1, dtype=np.int64)
    offsets[1:] = np.cumsum([array.shape[0] for array in force_arrays], dtype=np.int64)
    forces = np.concatenate(force_arrays, axis=0)
    stress_present = np.asarray(
        [item.stress_ev_per_angstrom3 is not None for item in values], dtype=np.bool_
    )
    stresses = np.zeros((len(values), 3, 3), dtype=np.float64)
    for index, item in enumerate(values):
        if item.stress_ev_per_angstrom3 is not None:
            stress = np.asarray(item.stress_ev_per_angstrom3, dtype=np.float64)
            if stress.shape != (3, 3) or np.any(~np.isfinite(stress)):
                raise TrainingDataInputError("Prediction stress must be a finite 3x3 tensor.")
            stresses[index] = stress
    metadata_path, data_path = _artifact_paths(root_directory, key)
    file_sha = _atomic_npz(
        data_path,
        energies=energies,
        force_offsets=offsets,
        force_values=forces,
        stress_present=stress_present,
        stresses=stresses,
    )
    root = Path(root_directory).resolve()
    artifact = EvaluationPredictionArtifact(
        key=key,
        relative_path=data_path.relative_to(root).as_posix(),
        file_sha256=file_sha,
        total_atom_count=int(offsets[-1]),
        force_dtype=np.dtype(force_dtype).name,
        stress_present_count=int(np.count_nonzero(stress_present)),
        source_kind=source_kind,
        source_digest=source_digest,
    )
    _atomic_json(metadata_path, artifact.to_dict())
    if geometry_identities is not None:
        _update_coverage_index(root_directory, key, geometry_identities, artifact)
    return artifact


def load_evaluation_prediction_artifact_record(
    root_directory: str | Path,
    key: EvaluationPredictionKey,
) -> EvaluationPredictionArtifact | None:
    """Authenticate cache metadata and prediction bytes without materializing arrays."""

    metadata_path, expected_data_path = _artifact_paths(root_directory, key)
    if not metadata_path.is_file() or not expected_data_path.is_file():
        return None
    try:
        artifact = EvaluationPredictionArtifact.from_dict(
            json.loads(metadata_path.read_text(encoding="utf-8"))
        )
        if artifact.key.content_digest != key.content_digest:
            return None
        root = Path(root_directory).resolve()
        data_path = (root / artifact.relative_path).resolve()
        if data_path != expected_data_path.resolve() or not data_path.is_file():
            return None
        if sha256_file_cached(data_path) != artifact.file_sha256:
            return None
        return artifact
    except Exception:
        return None


def load_evaluation_prediction_artifact(
    root_directory: str | Path,
    key: EvaluationPredictionKey,
) -> tuple[EvaluationPredictionArtifact, tuple[AtomicModelPrediction, ...]] | None:
    artifact = load_evaluation_prediction_artifact_record(root_directory, key)
    if artifact is None:
        return None
    try:
        root = Path(root_directory).resolve()
        data_path = (root / artifact.relative_path).resolve()
        with np.load(data_path, allow_pickle=False) as payload:
            energies = np.asarray(payload["energies"], dtype=np.float64)
            offsets = np.asarray(payload["force_offsets"], dtype=np.int64)
            forces = np.asarray(payload["force_values"])
            stress_present = np.asarray(payload["stress_present"], dtype=np.bool_)
            stresses = np.asarray(payload["stresses"], dtype=np.float64)
        count = key.configuration_count
        if (
            energies.shape != (count,)
            or offsets.shape != (count + 1,)
            or stress_present.shape != (count,)
            or stresses.shape != (count, 3, 3)
            or offsets[0] != 0
            or np.any(np.diff(offsets) <= 0)
            or int(offsets[-1]) != forces.shape[0]
            or forces.ndim != 2
            or forces.shape[1] != 3
            or forces.dtype.name != artifact.force_dtype
            or int(offsets[-1]) != artifact.total_atom_count
            or int(np.count_nonzero(stress_present)) != artifact.stress_present_count
            or np.any(~np.isfinite(energies))
            or np.any(~np.isfinite(forces))
            or np.any(~np.isfinite(stresses[stress_present]))
        ):
            return None
        predictions: list[AtomicModelPrediction] = []
        for index in range(count):
            start = int(offsets[index])
            stop = int(offsets[index + 1])
            predictions.append(
                AtomicModelPrediction(
                    energy_ev=float(energies[index]),
                    forces_ev_per_angstrom=np.asarray(forces[start:stop]).copy(),
                    stress_ev_per_angstrom3=(
                        np.asarray(stresses[index]).copy()
                        if bool(stress_present[index])
                        else None
                    ),
                )
            )
        return artifact, tuple(predictions)
    except Exception:
        return None


def evaluation_prediction_cache_has(
    root_directory: str | Path,
    key: EvaluationPredictionKey,
) -> bool:
    """Return True for an authenticated artifact without materializing prediction arrays."""

    return load_evaluation_prediction_artifact_record(root_directory, key) is not None


__all__ = [
    "EVALUATION_PREDICTION_KEY_SCHEMA",
    "EVALUATION_PREDICTION_ARTIFACT_SCHEMA",
    "EVALUATION_PREDICTION_NUMERICAL_CONTRACT",
    "EVALUATION_PREDICTION_COVERAGE_SCHEMA",
    "EvaluationPredictionKey",
    "EvaluationPredictionArtifact",
    "geometry_order_digest",
    "prediction_key",
    "write_evaluation_prediction_artifact",
    "load_evaluation_prediction_artifact_record",
    "load_evaluation_prediction_artifact",
    "evaluation_prediction_cache_has",
    "load_evaluation_prediction_coverage",
    "evaluation_prediction_coverage_has",
]
