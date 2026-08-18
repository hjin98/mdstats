"""Authenticated model-state-only capsules for completed MACE checkpoints.

STOR2 deliberately preserves the original checkpoint identity while replacing
nonselected optimizer-bearing checkpoint bytes with a smaller artifact that can
still participate in exact checkpoint evaluation.  Capsules are *not* restart
checkpoints: optimizer/scheduler/EMA continuation state is intentionally absent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json
import os
import time

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .tensor_hashing import update_hasher_with_tensor_bytes

EVALUATION_STATE_CAPSULE_FILE_SCHEMA = "mdstats.mace-evaluation-state-capsule-file.v1"
EVALUATION_STATE_CAPSULE_RECORD_SCHEMA = "mdstats.mace-evaluation-state-capsule-record.v1"
EVALUATION_STATE_CAPSULE_CONTRACT = "mace-0.3.16-model-state-only.v1"


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def model_state_sha256(state: Mapping[str, Any]) -> str:
    """Hash an ordered tensor state independently of torch serialization bytes."""

    hasher = hashlib.sha256()
    for key in sorted(state):
        value = state[key]
        if not hasattr(value, "detach") or not hasattr(value, "shape"):
            raise TrainingDataInputError(
                f"Evaluation capsule model state contains unsupported non-tensor value: {key}."
            )
        tensor = value.detach().cpu().contiguous()
        hasher.update(key.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(str(tensor.dtype).encode("ascii"))
        hasher.update(b"\0")
        hasher.update(json.dumps(tuple(int(v) for v in tensor.shape)).encode("ascii"))
        hasher.update(b"\0")
        try:
            update_hasher_with_tensor_bytes(hasher, tensor)
        except Exception as exc:
            raise TrainingDataInputError(
                f"Could not hash evaluation capsule tensor state: {key}."
            ) from exc
        hasher.update(b"\xff")
    return hasher.hexdigest()


def _torch_load(path: Path) -> Any:
    try:
        import torch
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise TrainingDataInputError(
            "Evaluation-state capsules require the optional torch package."
        ) from exc
    try:
        return torch.load(path, map_location="cpu", weights_only=False, mmap=True)
    except (TypeError, RuntimeError, ValueError):
        try:
            return torch.load(path, map_location="cpu", weights_only=False)
        except TypeError:  # pragma: no cover - older torch
            return torch.load(path, map_location="cpu")


@dataclass(frozen=True, slots=True)
class EvaluationStateCapsuleRecord:
    run_plan_digest: str
    source_checkpoint_sha256: str
    source_checkpoint_epoch: int
    source_checkpoint_size_bytes: int
    capsule_path: str
    capsule_sha256: str
    capsule_size_bytes: int
    model_state_sha256: str
    mace_config_sha256: str
    reconstruction_contract: str = EVALUATION_STATE_CAPSULE_CONTRACT
    verified_exact_model_state: bool = True
    created_at_utc: str = ""

    def __post_init__(self) -> None:
        for name in (
            "run_plan_digest",
            "source_checkpoint_sha256",
            "capsule_sha256",
            "model_state_sha256",
            "mace_config_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.source_checkpoint_epoch < 0:
            raise TrainingDataInputError("Evaluation capsule epoch must be nonnegative.")
        if self.source_checkpoint_size_bytes <= 0 or self.capsule_size_bytes <= 0:
            raise TrainingDataInputError("Evaluation capsule byte counts must be positive.")
        if not self.capsule_path.strip():
            raise TrainingDataInputError("Evaluation capsule path must be non-empty.")
        if self.reconstruction_contract != EVALUATION_STATE_CAPSULE_CONTRACT:
            raise TrainingDataInputError("Unsupported evaluation capsule reconstruction contract.")
        if not self.verified_exact_model_state:
            raise TrainingDataInputError("Unverified evaluation capsules are not admissible.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": EVALUATION_STATE_CAPSULE_RECORD_SCHEMA,
            "run_plan_digest": self.run_plan_digest,
            "source_checkpoint_sha256": self.source_checkpoint_sha256,
            "source_checkpoint_epoch": self.source_checkpoint_epoch,
            "source_checkpoint_size_bytes": self.source_checkpoint_size_bytes,
            "capsule_path": self.capsule_path,
            "capsule_sha256": self.capsule_sha256,
            "capsule_size_bytes": self.capsule_size_bytes,
            "model_state_sha256": self.model_state_sha256,
            "mace_config_sha256": self.mace_config_sha256,
            "reconstruction_contract": self.reconstruction_contract,
            "verified_exact_model_state": self.verified_exact_model_state,
            "created_at_utc": self.created_at_utc,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    @property
    def saved_bytes(self) -> int:
        return max(0, int(self.source_checkpoint_size_bytes) - int(self.capsule_size_bytes))

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EvaluationStateCapsuleRecord":
        if payload.get("schema") != EVALUATION_STATE_CAPSULE_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported evaluation-state capsule schema.")
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]),
            source_checkpoint_sha256=str(payload["source_checkpoint_sha256"]),
            source_checkpoint_epoch=int(payload["source_checkpoint_epoch"]),
            source_checkpoint_size_bytes=int(payload["source_checkpoint_size_bytes"]),
            capsule_path=str(payload["capsule_path"]),
            capsule_sha256=str(payload["capsule_sha256"]),
            capsule_size_bytes=int(payload["capsule_size_bytes"]),
            model_state_sha256=str(payload["model_state_sha256"]),
            mace_config_sha256=str(payload["mace_config_sha256"]),
            reconstruction_contract=str(payload.get("reconstruction_contract", "")),
            verified_exact_model_state=bool(payload.get("verified_exact_model_state", False)),
            created_at_utc=str(payload.get("created_at_utc", "")),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Evaluation-state capsule digest mismatch.")
        return result


def capsule_file_payload(
    *,
    run_plan_digest: str,
    source_checkpoint_sha256: str,
    source_checkpoint_epoch: int,
    source_checkpoint_size_bytes: int,
    model_state: Mapping[str, Any],
    model_state_digest: str,
    mace_config_sha256: str,
) -> dict[str, Any]:
    return {
        "schema": EVALUATION_STATE_CAPSULE_FILE_SCHEMA,
        "contract": EVALUATION_STATE_CAPSULE_CONTRACT,
        "run_plan_digest": validate_digest(run_plan_digest, name="run_plan_digest"),
        "source_checkpoint_sha256": validate_digest(
            source_checkpoint_sha256, name="source_checkpoint_sha256"
        ),
        "source_checkpoint_epoch": int(source_checkpoint_epoch),
        "source_checkpoint_size_bytes": int(source_checkpoint_size_bytes),
        "model_state_sha256": validate_digest(model_state_digest, name="model_state_sha256"),
        "mace_config_sha256": validate_digest(mace_config_sha256, name="mace_config_sha256"),
        "model": dict(model_state),
    }


def write_capsule_file_atomic(path: str | Path, payload: Mapping[str, Any]) -> tuple[str, int]:
    try:
        import torch
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError(
            "Evaluation-state capsules require the optional torch package."
        ) from exc
    destination = Path(path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.name}.{os.getpid()}.{time.time_ns()}.tmp"
    )
    try:
        torch.save(dict(payload), temporary)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return _sha256_file(destination), destination.stat().st_size


def load_validated_capsule_payload(
    record: EvaluationStateCapsuleRecord,
    path: str | Path,
    *,
    expected_run_plan_digest: str | None = None,
    expected_checkpoint_sha256: str | None = None,
    expected_epoch: int | None = None,
    expected_config_sha256: str | None = None,
) -> Mapping[str, Any]:
    source = Path(path).resolve()
    if not source.is_file():
        raise TrainingDataInputError(f"Evaluation-state capsule is missing: {source}.")
    if _sha256_file(source) != record.capsule_sha256:
        raise TrainingDataInputError("Evaluation-state capsule bytes changed after recording.")
    if source.stat().st_size != record.capsule_size_bytes:
        raise TrainingDataInputError("Evaluation-state capsule byte count changed after recording.")
    if expected_run_plan_digest is not None and record.run_plan_digest != expected_run_plan_digest:
        raise TrainingDataInputError("Evaluation-state capsule run lineage mismatch.")
    if expected_checkpoint_sha256 is not None and record.source_checkpoint_sha256 != expected_checkpoint_sha256:
        raise TrainingDataInputError("Evaluation-state capsule source checkpoint mismatch.")
    if expected_epoch is not None and record.source_checkpoint_epoch != int(expected_epoch):
        raise TrainingDataInputError("Evaluation-state capsule epoch mismatch.")
    if expected_config_sha256 is not None and record.mace_config_sha256 != expected_config_sha256:
        raise TrainingDataInputError("Evaluation-state capsule DATA8 config mismatch.")

    payload = _torch_load(source)
    if not isinstance(payload, Mapping):
        raise TrainingDataInputError("Evaluation-state capsule payload is not a mapping.")
    if payload.get("schema") != EVALUATION_STATE_CAPSULE_FILE_SCHEMA:
        raise TrainingDataInputError("Unsupported evaluation-state capsule file schema.")
    if payload.get("contract") != EVALUATION_STATE_CAPSULE_CONTRACT:
        raise TrainingDataInputError("Unsupported evaluation-state capsule file contract.")
    fields = {
        "run_plan_digest": record.run_plan_digest,
        "source_checkpoint_sha256": record.source_checkpoint_sha256,
        "source_checkpoint_epoch": record.source_checkpoint_epoch,
        "source_checkpoint_size_bytes": record.source_checkpoint_size_bytes,
        "model_state_sha256": record.model_state_sha256,
        "mace_config_sha256": record.mace_config_sha256,
    }
    for key, value in fields.items():
        if payload.get(key) != value:
            raise TrainingDataInputError(
                f"Evaluation-state capsule metadata mismatch: {key}."
            )
    state = payload.get("model")
    if not isinstance(state, Mapping):
        raise TrainingDataInputError("Evaluation-state capsule does not contain a model state.")
    if model_state_sha256(state) != record.model_state_sha256:
        raise TrainingDataInputError("Evaluation-state capsule model-state digest mismatch.")
    return payload
