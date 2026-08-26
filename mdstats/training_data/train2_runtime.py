"""TRAIN2B deterministic fixed-budget MACE runtime.

This module is deliberately small and source-qualified around MACE 0.3.16.  It
owns the per-optimizer-update LR trajectory and the latest-only continuation
companion required for a screen-boundary checkpoint to resume exactly onto
its original full-horizon trajectory.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import io
import json
import math
import os
from pathlib import Path
import random
import time
from typing import Any, Mapping, Sequence

import numpy as np

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .tensor_hashing import tensor_bytes_copy, update_hasher_with_tensor_bytes
from .train2_policy import TrainingBudgetPolicy, LearningRateSchedulePolicy

TRAIN2_RUNTIME_PLAN_SCHEMA = "mdstats.train2-runtime-plan.v1"
TRAIN2_RUNTIME_SUMMARY_SCHEMA = "mdstats.train2-runtime-summary.v1"
TRAIN2_RUNTIME_COMPANION_SCHEMA = "mdstats.train2-runtime-companion.v1"
TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE = "MDSTATS_TRAIN2_RUNTIME_PLAN"
TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE = "MDSTATS_TRAIN2_TRUE_REPLAY_PATH"
TRAIN2_TRUE_REPLAY_LOG_HEAD = "train2_true_replay"
TRAIN2_RUNTIME_SUMMARY_FILENAME = "train2_runtime.json"
TRAIN2_RUNTIME_COMPANION_FILENAME = "train2_runtime.pt"
TRAIN2_RUNTIME_HISTORY_FILENAME = "train2_history.jsonl"
TRAIN2_PERSISTENCE_TELEMETRY_FILENAME = "train2_persistence.jsonl"
TRAIN2_NUMERICAL_FAILURE_SCHEMA = "mdstats.train2-numerical-failure.v1"
TRAIN2_NUMERICAL_FAILURE_FILENAME = "train2_numerical_failure.json"
TRAIN2_NUMERICAL_FAILURE_CODES = frozenset({
    "train_nonfinite_model_state",
    "train_nonfinite_ema_state",
})

_ACTIVE_RUNTIME: "_Train2Runtime | None" = None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _atomic_torch_save(path: Path, payload: Mapping[str, Any]) -> None:
    import torch

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save(dict(payload), tmp)
    os.replace(tmp, path)


class Train2NumericalFailure(RuntimeError):
    """Positive TRAIN2 candidate-specific numerical failure signal.

    This exception is never inferred from child stderr.  The runtime writes an
    authenticated sidecar first; campaign execution recognizes only that
    machine-readable record.
    """

    def __init__(self, code: str, reason: str) -> None:
        if code not in TRAIN2_NUMERICAL_FAILURE_CODES:
            raise ValueError(f"Unsupported TRAIN2 numerical failure code: {code!r}")
        self.failure_code = str(code)
        self.reason = str(reason)
        super().__init__(f"{self.failure_code}: {self.reason}")


@dataclass(frozen=True, slots=True)
class Train2NumericalFailureRecord:
    failure_code: str
    reason: str
    failed_epoch: int
    completed_updates: int
    planned_updates: int
    execution_epoch_limit: int
    plan_digest: str
    training_protocol_digest: str
    optimizer_policy_digest: str
    budget_policy_digest: str
    lr_policy_digest: str
    raw_checkpoint_name: str
    raw_checkpoint_sha256: str

    def __post_init__(self) -> None:
        if self.failure_code not in TRAIN2_NUMERICAL_FAILURE_CODES:
            raise TrainingDataInputError("Unsupported TRAIN2 numerical-failure code.")
        if not self.reason.strip():
            raise TrainingDataInputError("TRAIN2 numerical-failure reason cannot be empty.")
        if int(self.failed_epoch) < 0:
            raise TrainingDataInputError("TRAIN2 numerical-failure epoch must be nonnegative.")
        if int(self.completed_updates) <= 0 or int(self.planned_updates) <= 0:
            raise TrainingDataInputError("TRAIN2 numerical-failure update counts must be positive.")
        if int(self.completed_updates) > int(self.planned_updates):
            raise TrainingDataInputError("TRAIN2 numerical-failure completed updates exceed the frozen budget.")
        if int(self.execution_epoch_limit) <= 0:
            raise TrainingDataInputError("TRAIN2 numerical-failure execution epoch limit must be positive.")
        for name in (
            "plan_digest",
            "training_protocol_digest",
            "optimizer_policy_digest",
            "budget_policy_digest",
            "lr_policy_digest",
            "raw_checkpoint_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if not Path(self.raw_checkpoint_name).name == self.raw_checkpoint_name:
            raise TrainingDataInputError("TRAIN2 numerical-failure raw checkpoint name is invalid.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAIN2_NUMERICAL_FAILURE_SCHEMA,
            "failure_code": self.failure_code,
            "reason": self.reason,
            "failed_epoch": int(self.failed_epoch),
            "completed_updates": int(self.completed_updates),
            "planned_updates": int(self.planned_updates),
            "execution_epoch_limit": int(self.execution_epoch_limit),
            "plan_digest": self.plan_digest,
            "training_protocol_digest": self.training_protocol_digest,
            "optimizer_policy_digest": self.optimizer_policy_digest,
            "budget_policy_digest": self.budget_policy_digest,
            "lr_policy_digest": self.lr_policy_digest,
            "raw_checkpoint_name": self.raw_checkpoint_name,
            "raw_checkpoint_sha256": self.raw_checkpoint_sha256,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Train2NumericalFailureRecord":
        if payload.get("schema") != TRAIN2_NUMERICAL_FAILURE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TRAIN2 numerical-failure schema.")
        result = cls(
            failure_code=str(payload["failure_code"]),
            reason=str(payload["reason"]),
            failed_epoch=int(payload["failed_epoch"]),
            completed_updates=int(payload["completed_updates"]),
            planned_updates=int(payload["planned_updates"]),
            execution_epoch_limit=int(payload["execution_epoch_limit"]),
            plan_digest=str(payload["plan_digest"]),
            training_protocol_digest=str(payload["training_protocol_digest"]),
            optimizer_policy_digest=str(payload["optimizer_policy_digest"]),
            budget_policy_digest=str(payload["budget_policy_digest"]),
            lr_policy_digest=str(payload["lr_policy_digest"]),
            raw_checkpoint_name=str(payload["raw_checkpoint_name"]),
            raw_checkpoint_sha256=str(payload["raw_checkpoint_sha256"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TRAIN2 numerical-failure digest mismatch.")
        return result


def load_train2_numerical_failure(
    checkpoint_directory: str | Path,
) -> Train2NumericalFailureRecord | None:
    path = Path(checkpoint_directory).resolve() / TRAIN2_NUMERICAL_FAILURE_FILENAME
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise TrainingDataSerializationError(
            f"TRAIN2 numerical-failure sidecar is unreadable: {type(exc).__name__}: {exc}"
        ) from exc
    return Train2NumericalFailureRecord.from_dict(payload)


def _tensors_are_finite(values: Sequence[Any]) -> bool:
    import torch

    return all(bool(torch.isfinite(value).all().item()) for value in values)


def _tensor_bytes(tensor: Any) -> bytes:
    return tensor_bytes_copy(tensor)


def _tensor_state_digest(values: Sequence[Any], *, schema: str) -> str:
    h = hashlib.sha256()
    h.update(schema.encode("utf-8"))
    for item in values:
        value = item.detach().cpu().contiguous()
        h.update(str(value.dtype).encode("utf-8"))
        h.update(repr(tuple(value.shape)).encode("utf-8"))
        update_hasher_with_tensor_bytes(h, value)
    return h.hexdigest()


def _checkpoint_for_epoch(directory: Path, epoch: int) -> Path:
    matches = []
    for item in directory.glob("*.pt"):
        name = item.name
        if f"epoch-{int(epoch)}" in name or f"epoch_{int(epoch)}" in name:
            matches.append(item)
    if len(matches) != 1:
        raise TrainingDataInputError(
            f"TRAIN2 expected exactly one raw checkpoint for durable epoch {epoch}; found {len(matches)}."
        )
    return matches[0]


def _encode_torch_rng_state(state: Any) -> str:
    return base64.b64encode(_tensor_bytes(state)).decode("ascii")


def _decode_torch_rng_state(text: str) -> Any:
    import torch

    raw = base64.b64decode(text.encode("ascii"))
    return torch.tensor(list(raw), dtype=torch.uint8)


def _capture_rng_state() -> dict[str, Any]:
    import torch

    py = random.getstate()
    np_state = np.random.get_state()
    result: dict[str, Any] = {
        "python": {
            "version": int(py[0]),
            "state": [int(v) for v in py[1]],
            "gauss": py[2],
        },
        "numpy": {
            "bit_generator": str(np_state[0]),
            "state": [int(v) for v in np_state[1].tolist()],
            "pos": int(np_state[2]),
            "has_gauss": int(np_state[3]),
            "cached_gaussian": float(np_state[4]),
        },
        "torch_cpu": _encode_torch_rng_state(torch.get_rng_state()),
        "torch_cuda": [],
    }
    if torch.cuda.is_available():
        result["torch_cuda"] = [_encode_torch_rng_state(v) for v in torch.cuda.get_rng_state_all()]
    return result


def _restore_rng_state(payload: Mapping[str, Any]) -> None:
    import torch

    py = payload.get("python")
    np_state = payload.get("numpy")
    if not isinstance(py, Mapping) or not isinstance(np_state, Mapping):
        raise TrainingDataSerializationError("TRAIN2 continuation RNG state is incomplete.")
    random.setstate((int(py["version"]), tuple(int(v) for v in py["state"]), py.get("gauss")))
    np.random.set_state((
        str(np_state["bit_generator"]),
        np.asarray(np_state["state"], dtype=np.uint32),
        int(np_state["pos"]),
        int(np_state["has_gauss"]),
        float(np_state["cached_gaussian"]),
    ))
    torch.set_rng_state(_decode_torch_rng_state(str(payload["torch_cpu"])))
    cuda_states = payload.get("torch_cuda", [])
    if cuda_states:
        if not torch.cuda.is_available():
            raise TrainingDataInputError(
                "TRAIN2 continuation carries CUDA RNG state but CUDA is unavailable."
            )
        restored = [_decode_torch_rng_state(str(v)) for v in cuda_states]
        if len(restored) != torch.cuda.device_count():
            raise TrainingDataInputError(
                "TRAIN2 continuation CUDA RNG-state count differs from the current device count."
            )
        torch.cuda.set_rng_state_all(restored)


@dataclass(frozen=True, slots=True)
class Train2RuntimePlan:
    """Runtime-only realization of the frozen TRAIN2 budget/LR authorities."""

    training_protocol_digest: str
    optimizer_policy_digest: str
    budget_policy: TrainingBudgetPolicy
    learning_rate_policy: LearningRateSchedulePolicy
    structures_per_epoch: int
    replay_monitor_enabled: bool = False
    target_head_name: str = "target_head"
    replay_head_name: str = "pt_head"
    true_replay_monitor_sha256: str | None = None
    execution_epoch_limit: int | None = None
    serialization_schema: str = field(default=TRAIN2_RUNTIME_PLAN_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != TRAIN2_RUNTIME_PLAN_SCHEMA:
            raise TrainingDataInputError("Unsupported TRAIN2 runtime-plan schema.")
        object.__setattr__(self, "training_protocol_digest", validate_digest(self.training_protocol_digest, name="training_protocol_digest"))
        object.__setattr__(self, "optimizer_policy_digest", validate_digest(self.optimizer_policy_digest, name="optimizer_policy_digest"))
        structures = int(self.structures_per_epoch)
        if structures <= 0:
            raise TrainingDataInputError("TRAIN2 structures_per_epoch must be positive.")
        object.__setattr__(self, "structures_per_epoch", structures)
        target_head = str(self.target_head_name).strip()
        replay_head = str(self.replay_head_name).strip()
        if not target_head or not replay_head or target_head == replay_head:
            raise TrainingDataInputError("TRAIN2 runtime head identities are invalid.")
        object.__setattr__(self, "target_head_name", target_head)
        object.__setattr__(self, "replay_head_name", replay_head)
        if self.replay_monitor_enabled:
            if self.true_replay_monitor_sha256 is None:
                raise TrainingDataInputError("TRAIN2 replay monitoring requires the TRUE_DFT replay artifact SHA256.")
            object.__setattr__(
                self, "true_replay_monitor_sha256",
                validate_digest(self.true_replay_monitor_sha256, name="true_replay_monitor_sha256"),
            )
        elif self.true_replay_monitor_sha256 is not None:
            raise TrainingDataInputError("TRAIN2 replay artifact identity is invalid when replay monitoring is disabled.")
        limit = self.budget_policy.planned_epochs if self.execution_epoch_limit is None else int(self.execution_epoch_limit)
        if limit <= 0 or limit > self.budget_policy.planned_epochs:
            raise TrainingDataInputError("TRAIN2 execution_epoch_limit must lie inside the frozen epoch budget.")
        object.__setattr__(self, "execution_epoch_limit", limit)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "training_protocol_digest": self.training_protocol_digest,
            "optimizer_policy_digest": self.optimizer_policy_digest,
            "budget_policy": self.budget_policy.to_dict(),
            "learning_rate_policy": self.learning_rate_policy.to_dict(),
            "structures_per_epoch": int(self.structures_per_epoch),
            "replay_monitor_enabled": bool(self.replay_monitor_enabled),
            "target_head_name": self.target_head_name,
            "replay_head_name": self.replay_head_name,
            "true_replay_monitor_sha256": self.true_replay_monitor_sha256,
            "execution_epoch_limit": int(self.execution_epoch_limit),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Train2RuntimePlan":
        if payload.get("schema") != TRAIN2_RUNTIME_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TRAIN2 runtime-plan schema.")
        result = cls(
            training_protocol_digest=str(payload["training_protocol_digest"]),
            optimizer_policy_digest=str(payload["optimizer_policy_digest"]),
            budget_policy=TrainingBudgetPolicy.from_dict(payload["budget_policy"]),
            learning_rate_policy=LearningRateSchedulePolicy.from_dict(payload["learning_rate_policy"]),
            structures_per_epoch=int(payload["structures_per_epoch"]),
            replay_monitor_enabled=bool(payload.get("replay_monitor_enabled", False)),
            target_head_name=str(payload.get("target_head_name", "target_head")),
            replay_head_name=str(payload.get("replay_head_name", "pt_head")),
            true_replay_monitor_sha256=(None if payload.get("true_replay_monitor_sha256") is None else str(payload["true_replay_monitor_sha256"])),
            execution_epoch_limit=int(payload["execution_epoch_limit"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TRAIN2 runtime-plan digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class Train2RuntimeSummary:
    plan_digest: str
    training_protocol_digest: str
    optimizer_policy_digest: str
    budget_policy_digest: str
    lr_policy_digest: str
    planned_epochs: int
    execution_epoch_limit: int
    updates_per_epoch: int
    planned_updates: int
    structures_per_epoch: int
    planned_structures_presented: int
    completed_epochs: int
    completed_updates: int
    structures_presented: int
    last_update_index: int
    normalized_progress: float
    instantaneous_learning_rate: float
    phase: str
    raw_checkpoint_epoch: int
    raw_checkpoint_sha256: str
    optimizer_state_digest: str
    live_parameter_digest: str
    ema_state_digest: str | None
    rng_state_digest: str
    group_base_learning_rates: tuple[float, ...]
    complete_budget: bool

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAIN2_RUNTIME_SUMMARY_SCHEMA,
            "plan_digest": self.plan_digest,
            "training_protocol_digest": self.training_protocol_digest,
            "optimizer_policy_digest": self.optimizer_policy_digest,
            "budget_policy_digest": self.budget_policy_digest,
            "lr_policy_digest": self.lr_policy_digest,
            "planned_epochs": self.planned_epochs,
            "execution_epoch_limit": self.execution_epoch_limit,
            "updates_per_epoch": self.updates_per_epoch,
            "planned_updates": self.planned_updates,
            "structures_per_epoch": self.structures_per_epoch,
            "planned_structures_presented": self.planned_structures_presented,
            "completed_epochs": self.completed_epochs,
            "completed_updates": self.completed_updates,
            "structures_presented": self.structures_presented,
            "last_update_index": self.last_update_index,
            "normalized_progress": self.normalized_progress,
            "instantaneous_learning_rate": self.instantaneous_learning_rate,
            "phase": self.phase,
            "raw_checkpoint_epoch": self.raw_checkpoint_epoch,
            "raw_checkpoint_sha256": self.raw_checkpoint_sha256,
            "optimizer_state_digest": self.optimizer_state_digest,
            "live_parameter_digest": self.live_parameter_digest,
            "ema_state_digest": self.ema_state_digest,
            "rng_state_digest": self.rng_state_digest,
            "group_base_learning_rates": list(self.group_base_learning_rates),
            "complete_budget": self.complete_budget,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Train2RuntimeSummary":
        if payload.get("schema") != TRAIN2_RUNTIME_SUMMARY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TRAIN2 runtime-summary schema.")
        result = cls(
            plan_digest=str(payload["plan_digest"]),
            training_protocol_digest=str(payload["training_protocol_digest"]),
            optimizer_policy_digest=str(payload["optimizer_policy_digest"]),
            budget_policy_digest=str(payload["budget_policy_digest"]),
            lr_policy_digest=str(payload["lr_policy_digest"]),
            planned_epochs=int(payload["planned_epochs"]),
            execution_epoch_limit=int(payload["execution_epoch_limit"]),
            updates_per_epoch=int(payload["updates_per_epoch"]),
            planned_updates=int(payload["planned_updates"]),
            structures_per_epoch=int(payload["structures_per_epoch"]),
            planned_structures_presented=int(payload["planned_structures_presented"]),
            completed_epochs=int(payload["completed_epochs"]),
            completed_updates=int(payload["completed_updates"]),
            structures_presented=int(payload["structures_presented"]),
            last_update_index=int(payload["last_update_index"]),
            normalized_progress=float(payload["normalized_progress"]),
            instantaneous_learning_rate=float(payload["instantaneous_learning_rate"]),
            phase=str(payload["phase"]),
            raw_checkpoint_epoch=int(payload["raw_checkpoint_epoch"]),
            raw_checkpoint_sha256=str(payload["raw_checkpoint_sha256"]),
            optimizer_state_digest=str(payload["optimizer_state_digest"]),
            live_parameter_digest=str(payload["live_parameter_digest"]),
            ema_state_digest=None if payload.get("ema_state_digest") is None else str(payload["ema_state_digest"]),
            rng_state_digest=str(payload["rng_state_digest"]),
            group_base_learning_rates=tuple(float(v) for v in payload["group_base_learning_rates"]),
            complete_budget=bool(payload["complete_budget"]),
        )
        for name in ("plan_digest", "training_protocol_digest", "optimizer_policy_digest", "budget_policy_digest", "lr_policy_digest", "raw_checkpoint_sha256", "optimizer_state_digest", "live_parameter_digest", "rng_state_digest"):
            validate_digest(getattr(result, name), name=name)
        if result.ema_state_digest is not None:
            validate_digest(result.ema_state_digest, name="ema_state_digest")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TRAIN2 runtime-summary digest mismatch.")
        return result


class _Train2Runtime:
    def __init__(
        self,
        plan: Train2RuntimePlan,
        *,
        model: Any,
        optimizer: Any,
        lr_scheduler: Any,
        ema: Any | None,
        train_loader: Any,
        current_epoch: int,
        checkpoint_handler: Any,
        logger_path: str,
        rank: int,
    ) -> None:
        self.plan = plan
        self.model = model
        self.optimizer = optimizer
        self.lr_scheduler = lr_scheduler
        self.ema = ema
        self.train_loader = train_loader
        self.current_epoch = int(current_epoch)
        if self.current_epoch > int(plan.execution_epoch_limit):
            raise TrainingDataInputError(
                "TRAIN2 continuation epoch exceeds its active execution boundary; "
                "refusing to perform another optimizer update."
            )
        self.checkpoint_directory = Path(checkpoint_handler.io.directory).resolve()
        self.logger_path = Path(logger_path).resolve()
        self.rank = int(rank)
        self.updates_per_epoch = int(len(train_loader))
        if self.updates_per_epoch <= 0:
            raise TrainingDataInputError("TRAIN2 requires a non-empty training loader.")
        self.planned_updates = self.updates_per_epoch * int(plan.budget_policy.planned_epochs)
        self.structures_per_epoch = int(plan.structures_per_epoch)
        self.planned_structures = self.structures_per_epoch * int(plan.budget_policy.planned_epochs)
        if self.planned_updates < 2:
            raise TrainingDataInputError("TRAIN2 requires at least two planned optimizer updates.")
        self.summary_path = self.checkpoint_directory / TRAIN2_RUNTIME_SUMMARY_FILENAME
        self.companion_path = self.checkpoint_directory / TRAIN2_RUNTIME_COMPANION_FILENAME
        self.history_path = self.checkpoint_directory / TRAIN2_RUNTIME_HISTORY_FILENAME
        self.persistence_telemetry_path = (
            self.checkpoint_directory / TRAIN2_PERSISTENCE_TELEMETRY_FILENAME
        )
        self.numerical_failure_path = (
            self.checkpoint_directory / TRAIN2_NUMERICAL_FAILURE_FILENAME
        )
        self.completed_updates = self.current_epoch * self.updates_per_epoch
        self.group_base_lrs: tuple[float, ...]
        self._metric_offset = 0
        self._epoch_metrics: list[dict[str, Any]] = []
        if self.current_epoch > 0:
            self._restore_continuation()
        else:
            base = float(plan.learning_rate_policy.base_learning_rate)
            bases = []
            for group in optimizer.param_groups:
                lr = float(group.get("lr", base))
                if not math.isfinite(lr) or lr <= 0.0:
                    raise TrainingDataInputError("TRAIN2 optimizer parameter-group LR is invalid.")
                if not math.isclose(lr, base, rel_tol=1.0e-12, abs_tol=1.0e-15):
                    raise TrainingDataInputError(
                        "TRAIN2 v1 requires every optimizer parameter group to start at the frozen base learning rate."
                    )
                bases.append(lr)
            self.group_base_lrs = tuple(bases)
        self._disable_native_scheduler()
        self._install_optimizer_step()
        if self.logger_path.is_file():
            self._metric_offset = self.logger_path.stat().st_size

    def _disable_native_scheduler(self) -> None:
        def no_step(*args: Any, **kwargs: Any) -> None:
            del args, kwargs
            return None
        self.lr_scheduler.step = no_step

    def _install_optimizer_step(self) -> None:
        original = self.optimizer.step
        if getattr(original, "_mdstats_train2_runtime", False):
            raise TrainingDataInputError("TRAIN2 optimizer step is already runtime-patched.")

        def patched_step(*args: Any, **kwargs: Any) -> Any:
            u = int(self.completed_updates)
            if u >= self.planned_updates:
                raise TrainingDataInputError("TRAIN2 attempted an optimizer update beyond its frozen budget.")
            multiplier = self.plan.learning_rate_policy.multiplier(u / (self.planned_updates - 1))
            for group, base_lr in zip(self.optimizer.param_groups, self.group_base_lrs):
                group["lr"] = float(base_lr) * multiplier
            result = original(*args, **kwargs)
            self.completed_updates += 1
            return result

        setattr(patched_step, "_mdstats_train2_runtime", True)
        self.optimizer.step = patched_step

    def _restore_continuation(self) -> None:
        import torch

        if not self.companion_path.is_file() or not self.summary_path.is_file():
            raise TrainingDataInputError(
                "TRAIN2 restart checkpoint exists without its exact-continuation runtime companion."
            )
        summary = Train2RuntimeSummary.from_dict(json.loads(self.summary_path.read_text(encoding="utf-8")))
        # The execution_epoch_limit is a pause boundary, not part of the
        # scientific full-horizon trajectory.  A screen-boundary companion
        # therefore has a different runtime-plan digest from its full-horizon
        # continuation.
        # Every schedule-defining authority must nevertheless remain byte-identical.
        if summary.training_protocol_digest != self.plan.training_protocol_digest:
            raise TrainingDataInputError("TRAIN2 restart companion belongs to a different training protocol.")
        if summary.optimizer_policy_digest != self.plan.optimizer_policy_digest:
            raise TrainingDataInputError("TRAIN2 restart companion belongs to a different optimizer policy.")
        if summary.budget_policy_digest != self.plan.budget_policy.policy_digest:
            raise TrainingDataInputError("TRAIN2 restart companion belongs to a different training-budget policy.")
        if summary.lr_policy_digest != self.plan.learning_rate_policy.policy_digest:
            raise TrainingDataInputError("TRAIN2 restart companion belongs to a different LR-schedule policy.")
        if summary.planned_epochs != self.plan.budget_policy.planned_epochs:
            raise TrainingDataInputError("TRAIN2 restart companion changed the frozen epoch horizon.")
        if summary.structures_per_epoch != self.structures_per_epoch or summary.planned_structures_presented != self.planned_structures:
            raise TrainingDataInputError("TRAIN2 restart companion changed the frozen structures-presented horizon.")
        expected_completed = self.current_epoch * self.updates_per_epoch
        if summary.completed_epochs != self.current_epoch or summary.completed_updates != expected_completed:
            raise TrainingDataInputError(
                "TRAIN2 restart companion does not match the checkpointed epoch/update boundary."
            )
        raw_epoch = self.current_epoch - 1
        raw = _checkpoint_for_epoch(self.checkpoint_directory, raw_epoch)
        if summary.raw_checkpoint_epoch != raw_epoch or summary.raw_checkpoint_sha256 != _sha256(raw):
            raise TrainingDataInputError("TRAIN2 raw restart checkpoint changed after companion persistence.")
        payload = torch.load(self.companion_path, map_location="cpu", weights_only=False)
        if not isinstance(payload, Mapping) or payload.get("schema") != TRAIN2_RUNTIME_COMPANION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TRAIN2 continuation companion schema.")
        if int(payload.get("epoch", -1)) != raw_epoch:
            raise TrainingDataSerializationError("TRAIN2 continuation companion epoch identity mismatch.")
        if payload.get("training_protocol_digest") != self.plan.training_protocol_digest:
            raise TrainingDataSerializationError("TRAIN2 continuation companion protocol identity mismatch.")
        if payload.get("optimizer_policy_digest") != self.plan.optimizer_policy_digest:
            raise TrainingDataSerializationError("TRAIN2 continuation companion optimizer-policy identity mismatch.")
        if payload.get("budget_policy_digest") != self.plan.budget_policy.policy_digest:
            raise TrainingDataSerializationError("TRAIN2 continuation companion budget-policy identity mismatch.")
        if payload.get("lr_policy_digest") != self.plan.learning_rate_policy.policy_digest:
            raise TrainingDataSerializationError("TRAIN2 continuation companion LR-policy identity mismatch.")
        if int(payload.get("planned_updates", -1)) != self.planned_updates or int(payload.get("updates_per_epoch", -1)) != self.updates_per_epoch:
            raise TrainingDataSerializationError("TRAIN2 continuation companion update geometry changed across restart.")
        if int(payload.get("structures_per_epoch", -1)) != self.structures_per_epoch or int(payload.get("planned_structures_presented", -1)) != self.planned_structures:
            raise TrainingDataSerializationError("TRAIN2 continuation companion structures-presented geometry changed across restart.")
        if payload.get("raw_checkpoint_sha256") != summary.raw_checkpoint_sha256:
            raise TrainingDataSerializationError("TRAIN2 continuation companion checkpoint digest mismatch.")
        live = payload.get("live_parameters")
        parameters = list(self.model.parameters())
        if not isinstance(live, list) or len(live) != len(parameters):
            raise TrainingDataSerializationError("TRAIN2 live-parameter continuation state is incomplete.")
        for target, source in zip(parameters, live):
            if tuple(target.shape) != tuple(source.shape):
                raise TrainingDataSerializationError("TRAIN2 live-parameter continuation shape mismatch.")
            target.data.copy_(source.to(device=target.device, dtype=target.dtype))
        if self.ema is not None:
            state = payload.get("ema_state")
            if not isinstance(state, Mapping):
                raise TrainingDataSerializationError("TRAIN2 EMA continuation state is missing.")
            self.ema.load_state_dict(dict(state))
        elif payload.get("ema_state") is not None:
            raise TrainingDataInputError("TRAIN2 companion carries EMA state but the resumed run disabled EMA.")
        self.group_base_lrs = tuple(float(v) for v in payload.get("group_base_learning_rates", ()))
        if len(self.group_base_lrs) != len(self.optimizer.param_groups):
            raise TrainingDataSerializationError("TRAIN2 parameter-group LR continuation state is incomplete.")
        for base_lr in self.group_base_lrs:
            if not math.isclose(
                base_lr, self.plan.learning_rate_policy.base_learning_rate,
                rel_tol=1.0e-12, abs_tol=1.0e-15,
            ):
                raise TrainingDataSerializationError(
                    "TRAIN2 continuation changed the frozen optimizer base learning rate."
                )
        _restore_rng_state(payload["rng_state"])
        self.completed_updates = expected_completed

    def _read_new_metrics(self, epoch: int) -> tuple[float | None, dict[str, float]]:
        if not self.logger_path.is_file():
            return None, {}
        losses: list[float] = []
        validation: dict[str, float] = {}
        with self.logger_path.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(self._metric_offset)
            for line in handle:
                try:
                    item = json.loads(line)
                except Exception:
                    continue
                if item.get("epoch") != int(epoch):
                    continue
                if item.get("mode") == "opt" and item.get("loss") is not None:
                    value = float(item["loss"])
                    if math.isfinite(value):
                        losses.append(value)
                elif item.get("mode") == "eval" and item.get("rmse_f") is not None:
                    value = float(item["rmse_f"])
                    if math.isfinite(value):
                        validation[str(item.get("head", "unknown"))] = value
            self._metric_offset = handle.tell()
        return (None if not losses else float(sum(losses) / len(losses))), validation

    def _record_numerical_failure(
        self, *, code: str, reason: str, epoch: int, raw_checkpoint: Path
    ) -> None:
        record = Train2NumericalFailureRecord(
            failure_code=code,
            reason=reason,
            failed_epoch=int(epoch),
            completed_updates=int(self.completed_updates),
            planned_updates=int(self.planned_updates),
            execution_epoch_limit=int(self.plan.execution_epoch_limit),
            plan_digest=self.plan.content_digest,
            training_protocol_digest=self.plan.training_protocol_digest,
            optimizer_policy_digest=self.plan.optimizer_policy_digest,
            budget_policy_digest=self.plan.budget_policy.policy_digest,
            lr_policy_digest=self.plan.learning_rate_policy.policy_digest,
            raw_checkpoint_name=raw_checkpoint.name,
            raw_checkpoint_sha256=_sha256(raw_checkpoint),
        )
        existing = load_train2_numerical_failure(self.checkpoint_directory)
        if existing is not None and existing.content_digest != record.content_digest:
            raise TrainingDataInputError(
                "TRAIN2 numerical-failure sidecar already records different scientific evidence."
            )
        _atomic_json(self.numerical_failure_path, record.to_dict())
        raise Train2NumericalFailure(code, reason)

    def persist_epoch(self, *, epoch: int) -> Train2RuntimeSummary | None:
        import torch

        if self.rank != 0:
            return None
        epoch = int(epoch)
        completed_epochs = epoch + 1
        expected_updates = completed_epochs * self.updates_per_epoch
        if self.completed_updates != expected_updates:
            raise TrainingDataInputError(
                f"TRAIN2 epoch {epoch} completed {self.completed_updates} optimizer updates; expected {expected_updates}."
            )
        raw = _checkpoint_for_epoch(self.checkpoint_directory, epoch)
        persistence_started = time.perf_counter()
        clone_started = time.perf_counter()
        live_parameters = [parameter.detach().cpu().clone() for parameter in self.model.parameters()]
        ema_state = None
        ema_digest = None
        if self.ema is not None:
            state = self.ema.state_dict()
            ema_state = {
                "decay": state["decay"],
                "num_updates": state["num_updates"],
                "shadow_params": [item.detach().cpu().clone() for item in state["shadow_params"]],
                "collected_params": None if state["collected_params"] is None else [item.detach().cpu().clone() for item in state["collected_params"]],
            }
            ema_values = list(ema_state["shadow_params"])
            if ema_state["collected_params"] is not None:
                ema_values.extend(ema_state["collected_params"])
        if not _tensors_are_finite(live_parameters):
            self._record_numerical_failure(
                code="train_nonfinite_model_state",
                reason=(
                    f"TRAIN2 live model state became non-finite at durable epoch {completed_epochs}."
                ),
                epoch=epoch,
                raw_checkpoint=raw,
            )
        if self.ema is not None and not _tensors_are_finite(ema_values):
            self._record_numerical_failure(
                code="train_nonfinite_ema_state",
                reason=(
                    f"TRAIN2 EMA state became non-finite at durable epoch {completed_epochs}."
                ),
                epoch=epoch,
                raw_checkpoint=raw,
            )
        clone_seconds = time.perf_counter() - clone_started

        state_hash_started = time.perf_counter()
        if self.ema is not None:
            ema_digest = _tensor_state_digest(ema_values, schema="mdstats.train2-ema-state.v1")
        rng_state = _capture_rng_state()
        rng_digest = digest(rng_state)
        last_update = self.completed_updates - 1
        progress = last_update / (self.planned_updates - 1)
        instantaneous_lr = self.plan.learning_rate_policy.learning_rate_for_update(last_update, self.planned_updates)
        phase = self.plan.learning_rate_policy.phase(progress)
        checkpoint_hash_started = time.perf_counter()
        checkpoint_sha = _sha256(raw)
        checkpoint_hash_seconds = time.perf_counter() - checkpoint_hash_started
        live_digest = _tensor_state_digest(live_parameters, schema="mdstats.train2-live-parameters.v1")
        state_hash_seconds = time.perf_counter() - state_hash_started - checkpoint_hash_seconds
        optimizer_state_digest = digest({
            "schema": "mdstats.train2-optimizer-state-reference.v1",
            "raw_checkpoint_sha256": checkpoint_sha,
            "training_protocol_digest": self.plan.training_protocol_digest,
            "optimizer_policy_digest": self.plan.optimizer_policy_digest,
            "completed_updates": self.completed_updates,
        })
        companion = {
            "schema": TRAIN2_RUNTIME_COMPANION_SCHEMA,
            "plan_digest": self.plan.content_digest,
            "training_protocol_digest": self.plan.training_protocol_digest,
            "optimizer_policy_digest": self.plan.optimizer_policy_digest,
            "budget_policy_digest": self.plan.budget_policy.policy_digest,
            "lr_policy_digest": self.plan.learning_rate_policy.policy_digest,
            "epoch": epoch,
            "completed_updates": self.completed_updates,
            "planned_updates": self.planned_updates,
            "updates_per_epoch": self.updates_per_epoch,
            "structures_per_epoch": self.structures_per_epoch,
            "structures_presented": completed_epochs * self.structures_per_epoch,
            "planned_structures_presented": self.planned_structures,
            "raw_checkpoint_name": raw.name,
            "raw_checkpoint_sha256": checkpoint_sha,
            "live_parameters": live_parameters,
            "ema_state": ema_state,
            "rng_state": rng_state,
            "group_base_learning_rates": list(self.group_base_lrs),
        }
        companion_write_started = time.perf_counter()
        _atomic_torch_save(self.companion_path, companion)
        companion_write_seconds = time.perf_counter() - companion_write_started
        summary = Train2RuntimeSummary(
            plan_digest=self.plan.content_digest,
            training_protocol_digest=self.plan.training_protocol_digest,
            optimizer_policy_digest=self.plan.optimizer_policy_digest,
            budget_policy_digest=self.plan.budget_policy.policy_digest,
            lr_policy_digest=self.plan.learning_rate_policy.policy_digest,
            planned_epochs=self.plan.budget_policy.planned_epochs,
            execution_epoch_limit=int(self.plan.execution_epoch_limit),
            updates_per_epoch=self.updates_per_epoch,
            planned_updates=self.planned_updates,
            structures_per_epoch=self.structures_per_epoch,
            planned_structures_presented=self.planned_structures,
            completed_epochs=completed_epochs,
            completed_updates=self.completed_updates,
            structures_presented=completed_epochs * self.structures_per_epoch,
            last_update_index=last_update,
            normalized_progress=progress,
            instantaneous_learning_rate=instantaneous_lr,
            phase=phase,
            raw_checkpoint_epoch=epoch,
            raw_checkpoint_sha256=checkpoint_sha,
            optimizer_state_digest=optimizer_state_digest,
            live_parameter_digest=live_digest,
            ema_state_digest=ema_digest,
            rng_state_digest=rng_digest,
            group_base_learning_rates=self.group_base_lrs,
            complete_budget=(completed_epochs == self.plan.budget_policy.planned_epochs),
        )
        summary_write_started = time.perf_counter()
        _atomic_json(self.summary_path, summary.to_dict())
        summary_write_seconds = time.perf_counter() - summary_write_started
        loss, validation = self._read_new_metrics(epoch)
        history = {
            "schema": "mdstats.train2-epoch-history.v1",
            "plan_digest": self.plan.content_digest,
            "training_protocol_digest": self.plan.training_protocol_digest,
            "optimizer_policy_digest": self.plan.optimizer_policy_digest,
            "budget_policy_digest": self.plan.budget_policy.policy_digest,
            "lr_policy_digest": self.plan.learning_rate_policy.policy_digest,
            "execution_epoch_limit": int(self.plan.execution_epoch_limit),
            "epoch": epoch,
            "completed_epochs": completed_epochs,
            "completed_updates": self.completed_updates,
            "planned_updates": self.planned_updates,
            "structures_presented": completed_epochs * self.structures_per_epoch,
            "planned_structures_presented": self.planned_structures,
            "normalized_progress": progress,
            "phase": phase,
            "instantaneous_learning_rate": instantaneous_lr,
            "mean_training_loss": loss,
            "validation_force_rmse_ev_per_angstrom": validation,
            "raw_checkpoint_sha256": checkpoint_sha,
            "runtime_summary_digest": summary.content_digest,
        }
        with self.history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(history, sort_keys=True, separators=(",", ":")) + "\n")
        persistence_telemetry = {
            "schema": "mdstats.train2-persistence-telemetry.v1",
            "epoch": epoch,
            "raw_checkpoint_size_bytes": int(raw.stat().st_size),
            "companion_size_bytes": int(self.companion_path.stat().st_size),
            "clone_seconds": float(clone_seconds),
            "state_hash_seconds": float(max(0.0, state_hash_seconds)),
            "raw_checkpoint_hash_seconds": float(checkpoint_hash_seconds),
            "companion_write_seconds": float(companion_write_seconds),
            "summary_write_seconds": float(summary_write_seconds),
            "total_persistence_seconds": float(time.perf_counter() - persistence_started),
            "hash_transport": "python-buffer-protocol-chunked-v1",
        }
        with self.persistence_telemetry_path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(persistence_telemetry, sort_keys=True, separators=(",", ":"))
                + "\n"
            )
        return summary

    def should_pause_after_epoch(self, epoch: int) -> bool:
        return int(epoch) + 1 >= int(self.plan.execution_epoch_limit)


def runtime_plan_from_environment() -> Train2RuntimePlan | None:
    raw = os.environ.get(TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE)
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except Exception as exc:
        raise TrainingDataInputError(f"TRAIN2 runtime environment is invalid JSON: {exc}") from exc
    return Train2RuntimePlan.from_dict(payload)


def prepare_train2_true_replay_validation_loader(model: Any, valid_loaders: Mapping[str, Any]) -> dict[str, Any]:
    """Inject the authenticated TRUE_DFT replay monitor with no control authority."""

    plan = runtime_plan_from_environment()
    if plan is None or not plan.replay_monitor_enabled:
        return dict(valid_loaders)
    raw_path = os.environ.get(TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE)
    if not raw_path:
        raise TrainingDataInputError("TRAIN2 replay monitoring is enabled but its TRUE_DFT monitor path is missing.")
    path = Path(raw_path).expanduser().resolve()
    if not path.is_file() or _sha256(path) != plan.true_replay_monitor_sha256:
        raise TrainingDataInputError("TRAIN2 TRUE_DFT replay monitor bytes are missing or changed.")
    if not valid_loaders:
        raise TrainingDataInputError("TRAIN2 cannot construct a replay diagnostic loader without a target validation loader.")
    heads = [str(value) for value in getattr(model, "heads", ())]
    if plan.replay_head_name not in heads:
        raise TrainingDataInputError(
            f"TRAIN2 replay head {plan.replay_head_name!r} is absent from model heads {heads!r}."
        )
    from .adaptive_stop import _validation_loader_from_extxyz
    loader = _validation_loader_from_extxyz(
        model, valid_loaders, path=path, dataset_head=plan.replay_head_name
    )
    return {TRAIN2_TRUE_REPLAY_LOG_HEAD: loader, **dict(valid_loaders)}


def activate_train2_runtime(
    *,
    model: Any,
    optimizer: Any,
    lr_scheduler: Any,
    ema: Any | None,
    train_loader: Any,
    current_epoch: int,
    max_num_epochs: int,
    checkpoint_handler: Any,
    logger_path: str,
    swa: Any | None,
    rank: int,
) -> bool:
    global _ACTIVE_RUNTIME
    plan = runtime_plan_from_environment()
    if plan is None:
        return False
    if swa is not None:
        raise TrainingDataInputError("TRAIN2B forbids MACE SWA because it carries a competing LR/loss schedule.")
    if int(max_num_epochs) != plan.budget_policy.planned_epochs:
        raise TrainingDataInputError("TRAIN2 runtime max_num_epochs differs from the frozen training budget.")
    if _ACTIVE_RUNTIME is not None:
        raise TrainingDataInputError("TRAIN2 runtime was activated twice in one MACE process.")
    _ACTIVE_RUNTIME = _Train2Runtime(
        plan,
        model=model,
        optimizer=optimizer,
        lr_scheduler=lr_scheduler,
        ema=ema,
        train_loader=train_loader,
        current_epoch=current_epoch,
        checkpoint_handler=checkpoint_handler,
        logger_path=logger_path,
        rank=rank,
    )
    return True


def persist_train2_runtime_epoch(*, epoch: int) -> None:
    if _ACTIVE_RUNTIME is not None:
        _ACTIVE_RUNTIME.persist_epoch(epoch=epoch)


def train2_runtime_should_pause_after_epoch(epoch: int) -> bool:
    return bool(_ACTIVE_RUNTIME is not None and _ACTIVE_RUNTIME.should_pause_after_epoch(epoch))


def validate_train2_runtime_continuation_artifacts(
    checkpoint_directory: str | Path,
    *,
    training_protocol_digest: str,
    optimizer_policy_digest: str,
    budget_policy: TrainingBudgetPolicy,
    learning_rate_policy: LearningRateSchedulePolicy,
    structures_per_epoch: int,
) -> Train2RuntimeSummary:
    """Authenticate durable TRAIN2 state before a campaign decides to resume it.

    The pause limit is intentionally excluded: a survivor may restore a
    boundary companion under a later execution limit while retaining the same
    scientific budget and LR trajectory.
    """

    import torch

    root = Path(checkpoint_directory).resolve()
    summary = load_train2_runtime_summary(root)
    expected_structures = int(structures_per_epoch)
    if expected_structures <= 0:
        raise TrainingDataInputError("TRAIN2 continuation structures-per-epoch must be positive.")
    expected_updates = int(summary.updates_per_epoch) * int(budget_policy.planned_epochs)
    expected_presented = expected_structures * int(budget_policy.planned_epochs)
    if (
        summary.training_protocol_digest != training_protocol_digest
        or summary.optimizer_policy_digest != optimizer_policy_digest
        or summary.budget_policy_digest != budget_policy.policy_digest
        or summary.lr_policy_digest != learning_rate_policy.policy_digest
        or summary.planned_epochs != int(budget_policy.planned_epochs)
        or summary.planned_updates != expected_updates
        or summary.structures_per_epoch != expected_structures
        or summary.planned_structures_presented != expected_presented
        or summary.completed_updates != summary.completed_epochs * summary.updates_per_epoch
        or summary.structures_presented != summary.completed_epochs * expected_structures
        or summary.last_update_index != summary.completed_updates - 1
    ):
        raise TrainingDataInputError("TRAIN2 runtime summary is incompatible with its frozen continuation authority.")
    if summary.completed_epochs <= 0 or summary.completed_epochs > summary.planned_epochs:
        raise TrainingDataInputError("TRAIN2 runtime summary has an invalid completed epoch.")
    raw = _checkpoint_for_epoch(root, int(summary.completed_epochs) - 1)
    if summary.raw_checkpoint_epoch != int(summary.completed_epochs) - 1 or summary.raw_checkpoint_sha256 != _sha256(raw):
        raise TrainingDataInputError("TRAIN2 runtime summary does not authenticate its latest raw checkpoint.")
    companion_path = root / TRAIN2_RUNTIME_COMPANION_FILENAME
    if not companion_path.is_file():
        raise TrainingDataInputError("TRAIN2 restart checkpoint exists without its exact-continuation runtime companion.")
    try:
        payload = torch.load(companion_path, map_location="cpu", weights_only=False)
    except Exception as exc:
        raise TrainingDataSerializationError(
            "TRAIN2 continuation companion cannot be read as authenticated runtime state."
        ) from exc
    if not isinstance(payload, Mapping) or payload.get("schema") != TRAIN2_RUNTIME_COMPANION_SCHEMA:
        raise TrainingDataSerializationError("Unsupported TRAIN2 continuation companion schema.")
    if (
        int(payload.get("epoch", -1)) != summary.raw_checkpoint_epoch
        or payload.get("training_protocol_digest") != training_protocol_digest
        or payload.get("optimizer_policy_digest") != optimizer_policy_digest
        or payload.get("budget_policy_digest") != budget_policy.policy_digest
        or payload.get("lr_policy_digest") != learning_rate_policy.policy_digest
        or int(payload.get("completed_updates", -1)) != summary.completed_updates
        or int(payload.get("planned_updates", -1)) != summary.planned_updates
        or int(payload.get("updates_per_epoch", -1)) != summary.updates_per_epoch
        or int(payload.get("structures_per_epoch", -1)) != expected_structures
        or int(payload.get("structures_presented", -1)) != summary.structures_presented
        or int(payload.get("planned_structures_presented", -1)) != summary.planned_structures_presented
        or payload.get("raw_checkpoint_sha256") != summary.raw_checkpoint_sha256
        or Path(str(payload.get("raw_checkpoint_name", ""))).name != raw.name
    ):
        raise TrainingDataSerializationError("TRAIN2 continuation companion disagrees with its runtime summary.")
    if not isinstance(payload.get("live_parameters"), list) or not isinstance(payload.get("rng_state"), Mapping):
        raise TrainingDataSerializationError("TRAIN2 continuation companion state is incomplete.")
    return summary


def load_train2_runtime_summary(checkpoint_directory: str | Path) -> Train2RuntimeSummary:
    path = Path(checkpoint_directory).resolve() / TRAIN2_RUNTIME_SUMMARY_FILENAME
    if not path.is_file():
        raise TrainingDataInputError(f"TRAIN2 runtime summary is missing: {path}")
    return Train2RuntimeSummary.from_dict(json.loads(path.read_text(encoding="utf-8")))


def build_train2_runtime_plan(
    job: Any, *, execution_epoch_limit: int | None = None,
    true_replay_monitor_sha256: str | None = None,
) -> Train2RuntimePlan:
    protocol = job.protocol
    if protocol.training_budget_policy is None or protocol.learning_rate_schedule_policy is None:
        raise TrainingDataInputError("TRAIN2 runtime requires a TRAIN2 protocol.")
    return Train2RuntimePlan(
        training_protocol_digest=protocol.content_digest,
        optimizer_policy_digest=protocol.optimizer_policy.policy_digest,
        budget_policy=protocol.training_budget_policy,
        learning_rate_policy=protocol.learning_rate_schedule_policy,
        structures_per_epoch=(
            int(job.loader_dry_run.target_train_count_effective)
            + int(job.loader_dry_run.replay_train_count_effective)
        ),
        replay_monitor_enabled=bool(protocol.checkpoint_admissibility_policy.replay_enabled),
        target_head_name=protocol.checkpoint_control_policy.target_head_name,
        replay_head_name=protocol.checkpoint_control_policy.replay_head_name,
        true_replay_monitor_sha256=true_replay_monitor_sha256,
        execution_epoch_limit=execution_epoch_limit,
    )


__all__ = [
    "TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE",
    "TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE",
    "TRAIN2_TRUE_REPLAY_LOG_HEAD",
    "TRAIN2_RUNTIME_PLAN_SCHEMA",
    "TRAIN2_RUNTIME_SUMMARY_SCHEMA",
    "Train2RuntimePlan",
    "Train2RuntimeSummary",
    "build_train2_runtime_plan",
    "runtime_plan_from_environment",
    "prepare_train2_true_replay_validation_loader",
    "activate_train2_runtime",
    "persist_train2_runtime_epoch",
    "train2_runtime_should_pause_after_epoch",
    "validate_train2_runtime_continuation_artifacts",
    "load_train2_runtime_summary",
]
