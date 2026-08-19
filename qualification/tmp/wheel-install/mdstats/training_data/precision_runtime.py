"""Live staged-precision execution support for qualified MACE 0.3.16 training.

PREC2 owns the in-process precision-stage boundary.  The immutable DATA8 job
manifest remains the source of truth; this module only realizes its already
resolved schedule.  Runtime state is deliberately narrow and version-locked to
MACE 0.3.16 so an upstream training-loop change fails closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import hashlib
import json
import os
import re
import tempfile

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .precision_schedule import ResolvedPrecisionSchedule

PRECISION_RUNTIME_COMPANION_SCHEMA = "mdstats.mace-precision-runtime-companion.v1"
PRECISION_STAGE_TRANSITION_SCHEMA = "mdstats.mace-precision-stage-transition.v1"
PRECISION_RUNTIME_COMPANION_NAME = ".mdstats-precision-latest.state"
PRECISION_TRANSITION_PREFIX = "mdstats-precision-transition-epoch-"
SUPPORTED_STAGED_MACE_VERSION = "0.3.16"


def _dtype_name(dtype: Any) -> str:
    return str(dtype).removeprefix("torch.")


def _torch_dtype(name: str, torch: Any) -> Any:
    if name == "float32":
        return torch.float32
    if name == "float64":
        return torch.float64
    raise TrainingDataInputError(f"Unsupported staged-training dtype {name!r}.")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def _atomic_torch_save(path: Path, payload: Any) -> None:
    import torch

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(fd)
    try:
        torch.save(payload, temp_name)
        with open(temp_name, "rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def _state_inventory(items: Iterable[tuple[str, Any]]) -> tuple[tuple[str, str, tuple[int, ...], int], ...]:
    result: list[tuple[str, str, tuple[int, ...], int]] = []
    for name, tensor in items:
        if not hasattr(tensor, "is_floating_point") or not tensor.is_floating_point():
            continue
        result.append((str(name), _dtype_name(tensor.dtype), tuple(int(v) for v in tensor.shape), int(tensor.numel())))
    return tuple(result)


def model_dtype_inventory(model: Any) -> dict[str, Any]:
    params = _state_inventory(model.named_parameters())
    buffers = _state_inventory(model.named_buffers())
    return {
        "parameters": [list(v[:2]) + [list(v[2]), v[3]] for v in params],
        "buffers": [list(v[:2]) + [list(v[2]), v[3]] for v in buffers],
    }


def _walk_floating_tensors(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    try:
        import torch
    except Exception:  # pragma: no cover - torch is required by callers
        return ()
    if isinstance(value, torch.Tensor):
        if value.is_floating_point():
            yield prefix, value
        return
    if isinstance(value, Mapping):
        for key in sorted(value, key=lambda item: str(item)):
            child = f"{prefix}.{key}" if prefix else str(key)
            yield from _walk_floating_tensors(value[key], child)
        return
    if isinstance(value, (tuple, list)):
        for index, item in enumerate(value):
            child = f"{prefix}[{index}]"
            yield from _walk_floating_tensors(item, child)


def optimizer_dtype_inventory(optimizer: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for state_index, state in enumerate(optimizer.state.values()):
        for _, tensor in _walk_floating_tensors(state, f"state[{state_index}]"):
            key = _dtype_name(tensor.dtype)
            counts[key] = counts.get(key, 0) + int(tensor.numel())
    return dict(sorted(counts.items()))


def ema_dtype_inventory(ema: Any | None) -> dict[str, int]:
    if ema is None:
        return {}
    counts: dict[str, int] = {}
    for _, tensor in _walk_floating_tensors(ema.state_dict(), "ema"):
        key = _dtype_name(tensor.dtype)
        counts[key] = counts.get(key, 0) + int(tensor.numel())
    return dict(sorted(counts.items()))


def _inventory_digest(*, model: Any, optimizer: Any, ema: Any | None, lrs: Sequence[float]) -> str:
    return digest(
        {
            "schema": "mdstats.precision-runtime-state-inventory.v1",
            "model": model_dtype_inventory(model),
            "optimizer": optimizer_dtype_inventory(optimizer),
            "ema": ema_dtype_inventory(ema),
            "lrs": [float(v) for v in lrs],
        }
    )


def _cast_nested_floating(value: Any, *, dtype: Any, device_by_parameter: bool = False) -> Any:
    import torch

    if isinstance(value, torch.Tensor):
        return value.to(dtype=dtype) if value.is_floating_point() else value
    if isinstance(value, dict):
        for key, item in list(value.items()):
            value[key] = _cast_nested_floating(item, dtype=dtype, device_by_parameter=device_by_parameter)
        return value
    if isinstance(value, list):
        for index, item in enumerate(value):
            value[index] = _cast_nested_floating(item, dtype=dtype, device_by_parameter=device_by_parameter)
        return value
    if isinstance(value, tuple):
        return tuple(_cast_nested_floating(item, dtype=dtype, device_by_parameter=device_by_parameter) for item in value)
    return value


def _optimizer_to_dtype(optimizer: Any, *, dtype: Any) -> None:
    for state in optimizer.state.values():
        _cast_nested_floating(state, dtype=dtype)


def _scale_scheduler_lr_state(lr_scheduler: Any, *, factor: float) -> None:
    if factor <= 0.0:
        raise TrainingDataInputError("Precision-stage learning-rate scale must be positive.")
    scheduler = getattr(lr_scheduler, "lr_scheduler", lr_scheduler)
    for name in ("base_lrs", "_last_lr", "min_lrs"):
        values = getattr(scheduler, name, None)
        if isinstance(values, list):
            setattr(scheduler, name, [float(v) * factor for v in values])


def _model_parameter_dtype(model: Any) -> Any:
    for parameter in model.parameters():
        if parameter.is_floating_point():
            return parameter.dtype
    raise TrainingDataInputError("Staged MACE model contains no floating parameters.")


def cast_batch_to_model_dtype(batch: Any, model: Any) -> Any:
    """Cast only floating batch tensors to the active model dtype."""

    dtype = _model_parameter_dtype(model)
    if not hasattr(batch, "apply"):
        return batch

    def convert(tensor: Any) -> Any:
        if hasattr(tensor, "is_floating_point") and tensor.is_floating_point():
            return tensor.to(dtype=dtype)
        return tensor

    return batch.apply(convert)


@dataclass(frozen=True, slots=True)
class PrecisionRuntimePlan:
    job_manifest_path: str
    job_digest: str
    protocol_digest: str
    optimizer_policy_digest: str
    schedule: ResolvedPrecisionSchedule
    checkpoints_dir: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "job_digest", validate_digest(self.job_digest, name="job_digest"))
        object.__setattr__(self, "protocol_digest", validate_digest(self.protocol_digest, name="protocol_digest"))
        object.__setattr__(self, "optimizer_policy_digest", validate_digest(self.optimizer_policy_digest, name="optimizer_policy_digest"))

    @property
    def staged(self) -> bool:
        return len(self.schedule.stages) > 1

    @property
    def schedule_digest(self) -> str:
        return self.schedule.content_digest

    def stage_index_for_epoch(self, epoch: int) -> int:
        for index, stage in enumerate(self.schedule.stages):
            if stage.start_epoch <= epoch < stage.stop_epoch:
                return index
        raise TrainingDataInputError(f"Epoch {epoch} lies outside the resolved precision schedule.")

    def stage_index_for_completed_epoch(self, epoch: int) -> int:
        return self.stage_index_for_epoch(epoch)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "mdstats.precision-runtime-plan.v1",
            "job_manifest_path": self.job_manifest_path,
            "job_digest": self.job_digest,
            "protocol_digest": self.protocol_digest,
            "optimizer_policy_digest": self.optimizer_policy_digest,
            "schedule": self.schedule.to_dict(),
            "checkpoints_dir": self.checkpoints_dir,
        }


_ACTIVE_PLAN: PrecisionRuntimePlan | None = None
_RESTART_COMPANION: dict[str, Any] | None = None
_TRANSITION_APPLIED: set[int] = set()
_BATCH_PATCH_INSTALLED = False
_CHECKPOINT_PATCH_INSTALLED = False
_EMA_PATCH_INSTALLED = False


def _argument_value(argv: Sequence[str], name: str) -> str | None:
    for index, token in enumerate(argv):
        if token == name:
            return None if index + 1 >= len(argv) else argv[index + 1]
        prefix = name + "="
        if token.startswith(prefix):
            return token[len(prefix):]
    return None


def _set_argument(argv: list[str], name: str, value: str) -> None:
    for index, token in enumerate(argv):
        if token == name:
            if index + 1 >= len(argv):
                argv.append(value)
            else:
                argv[index + 1] = value
            return
        if token.startswith(name + "="):
            argv[index] = f"{name}={value}"
            return
    argv.extend((name, value))


def load_precision_runtime_plan(config_path: str | Path, *, checkpoints_dir: str | Path | None = None) -> PrecisionRuntimePlan | None:
    config = Path(config_path).expanduser().resolve()
    manifest = config.parent / "job_manifest.json"
    if not manifest.is_file():
        return None
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    protocol = payload.get("protocol")
    if not isinstance(protocol, Mapping):
        raise TrainingDataInputError("DATA8 job manifest is missing its training protocol.")
    schedule_payload = protocol.get("resolved_precision_schedule")
    if schedule_payload is None:
        return None
    schedule = ResolvedPrecisionSchedule.from_dict(schedule_payload)
    optimizer = protocol.get("optimizer_policy")
    if not isinstance(optimizer, Mapping):
        raise TrainingDataInputError("DATA8 protocol is missing optimizer identity.")
    job_digest = str(payload.get("content_digest", ""))
    protocol_digest = str(protocol.get("content_digest", ""))
    optimizer_digest = str(optimizer.get("policy_digest", ""))
    return PrecisionRuntimePlan(
        job_manifest_path=str(manifest),
        job_digest=job_digest,
        protocol_digest=protocol_digest,
        optimizer_policy_digest=optimizer_digest,
        schedule=schedule,
        checkpoints_dir=None if checkpoints_dir is None else str(Path(checkpoints_dir).expanduser().resolve()),
    )


def companion_path(checkpoints_dir: str | Path) -> Path:
    return Path(checkpoints_dir).expanduser().resolve() / PRECISION_RUNTIME_COMPANION_NAME


def _load_companion(path: Path, *, plan: PrecisionRuntimePlan, map_location: Any = "cpu") -> dict[str, Any]:
    import torch

    if not path.is_file():
        raise TrainingDataInputError(f"Staged restart companion is missing: {path!s}.")
    payload = torch.load(path, map_location=map_location, weights_only=False)
    if not isinstance(payload, Mapping) or payload.get("schema") != PRECISION_RUNTIME_COMPANION_SCHEMA:
        raise TrainingDataSerializationError("Unsupported staged-restart companion schema.")
    if payload.get("job_digest") != plan.job_digest or payload.get("protocol_digest") != plan.protocol_digest:
        raise TrainingDataInputError("Staged-restart companion belongs to a different DATA8 protocol.")
    if payload.get("schedule_digest") != plan.schedule_digest:
        raise TrainingDataInputError("Staged-restart companion schedule changed.")
    epoch = int(payload["epoch"])
    stage_index = plan.stage_index_for_completed_epoch(epoch)
    if int(payload["stage_index"]) != stage_index:
        raise TrainingDataInputError("Staged-restart companion stage index is inconsistent.")
    expected_dtype = plan.schedule.stages[stage_index].dtype
    if str(payload["stage_dtype"]) != expected_dtype:
        raise TrainingDataInputError("Staged-restart companion dtype is inconsistent.")
    return dict(payload)


def latest_resumable_precision_epoch(checkpoints_dir: str | Path, plan: PrecisionRuntimePlan) -> int | None:
    if not plan.staged:
        return None
    path = companion_path(checkpoints_dir)
    if not path.is_file():
        return None
    payload = _load_companion(path, plan=plan, map_location="cpu")
    epoch = int(payload["epoch"])
    regex = re.compile(r"(?:epoch[-_]?)" + re.escape(str(epoch)) + r"(?:_swa)?\.pt$", re.IGNORECASE)
    if not any(item.is_file() and regex.search(item.name) for item in Path(checkpoints_dir).rglob("*.pt")):
        raise TrainingDataInputError(
            "The latest staged-restart companion has no matching raw MACE checkpoint."
        )
    return epoch


def configure_precision_runtime_from_argv(argv: list[str]) -> PrecisionRuntimePlan | None:
    """Resolve DATA8 precision runtime and set restart construction dtype."""

    global _ACTIVE_PLAN, _RESTART_COMPANION
    config_value = _argument_value(argv, "--config")
    if config_value is None:
        _ACTIVE_PLAN = None
        _RESTART_COMPANION = None
        return None
    checkpoint_value = _argument_value(argv, "--checkpoints_dir")
    if checkpoint_value is None:
        try:
            import yaml
            config_payload = yaml.safe_load(Path(config_value).read_text(encoding="utf-8")) or {}
        except Exception:
            config_payload = {}
        checkpoint_value = str(config_payload.get("checkpoints_dir", "./checkpoints"))
        candidate = Path(checkpoint_value).expanduser()
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        checkpoint_value = str(candidate.resolve())
    plan = load_precision_runtime_plan(config_value, checkpoints_dir=checkpoint_value)
    _ACTIVE_PLAN = plan
    _RESTART_COMPANION = None
    if plan is None or not plan.staged:
        return plan
    if checkpoint_value is None:
        raise TrainingDataInputError("Staged MACE execution requires an explicit checkpoints directory.")
    restart_value = os.environ.get("MDSTATS_MACE_RESTART_EPOCH")
    if "--restart_latest" in argv:
        if restart_value is None:
            raise TrainingDataInputError("Staged restart requires MDSTATS_MACE_RESTART_EPOCH.")
        expected_epoch = int(restart_value)
        payload = _load_companion(companion_path(checkpoint_value), plan=plan, map_location="cpu")
        if int(payload["epoch"]) != expected_epoch:
            raise TrainingDataInputError(
                f"Staged restart expects epoch {expected_epoch}, but companion records epoch {payload['epoch']}."
            )
        _RESTART_COMPANION = payload
        stage_index = plan.stage_index_for_completed_epoch(expected_epoch)
        _set_argument(argv, "--default_dtype", plan.schedule.stages[stage_index].dtype)
    else:
        _set_argument(argv, "--default_dtype", plan.schedule.stages[0].dtype)
    return plan


def _checkpoint_for_epoch(checkpoint_handler: Any, epoch: int) -> Path | None:
    try:
        path = Path(checkpoint_handler.io.directory) / checkpoint_handler.io._get_checkpoint_filename(
            epoch, checkpoint_handler.io.swa_start
        )
    except Exception:
        return None
    return path if path.is_file() else None


def persist_precision_runtime_companion(
    *,
    model: Any,
    optimizer: Any,
    lr_scheduler: Any,
    ema: Any | None,
    checkpoint_handler: Any,
    epoch: int,
    rank: int = 0,
) -> None:
    """Atomically persist only the latest exact-continuation companion state."""

    plan = _ACTIVE_PLAN
    if plan is None or not plan.staged or int(rank) != 0:
        return
    raw = _checkpoint_for_epoch(checkpoint_handler, int(epoch))
    if raw is None:
        return
    stage_index = plan.stage_index_for_completed_epoch(int(epoch))
    expected_dtype = plan.schedule.stages[stage_index].dtype
    actual_dtype = _dtype_name(_model_parameter_dtype(model))
    if actual_dtype != expected_dtype:
        raise TrainingDataInputError(
            f"Completed epoch {epoch} has model dtype {actual_dtype}, expected {expected_dtype}."
        )
    live_parameters = [parameter.detach().cpu().clone() for parameter in model.parameters()]
    ema_state = None
    if plan.schedule.preserve_ema_state:
        if ema is None:
            raise TrainingDataInputError("Staged precision protocol requires EMA state preservation.")
        ema_state = ema.state_dict()
        ema_state = {
            "decay": ema_state["decay"],
            "num_updates": ema_state["num_updates"],
            "shadow_params": [item.detach().cpu().clone() for item in ema_state["shadow_params"]],
            "collected_params": None
            if ema_state["collected_params"] is None
            else [item.detach().cpu().clone() for item in ema_state["collected_params"]],
        }
    payload = {
        "schema": PRECISION_RUNTIME_COMPANION_SCHEMA,
        "job_digest": plan.job_digest,
        "protocol_digest": plan.protocol_digest,
        "optimizer_policy_digest": plan.optimizer_policy_digest,
        "schedule_digest": plan.schedule_digest,
        "epoch": int(epoch),
        "stage_index": int(stage_index),
        "stage_dtype": expected_dtype,
        "live_parameters": live_parameters,
        "ema_state": ema_state,
        "optimizer_lrs": [float(group["lr"]) for group in optimizer.param_groups],
        "scheduler_state": lr_scheduler.state_dict(),
        "raw_checkpoint_name": raw.name,
        "state_inventory_digest": _inventory_digest(
            model=model,
            optimizer=optimizer,
            ema=ema,
            lrs=[float(group["lr"]) for group in optimizer.param_groups],
        ),
    }
    _atomic_torch_save(companion_path(checkpoint_handler.io.directory), payload)


def restore_restart_companion_into_ema(ema: Any, parameters: Sequence[Any]) -> None:
    """Restore live parameters and EMA state after MACE loaded its raw checkpoint."""

    payload = _RESTART_COMPANION
    plan = _ACTIVE_PLAN
    if payload is None or plan is None or not plan.staged:
        return
    live = payload.get("live_parameters")
    if not isinstance(live, list) or len(live) != len(parameters):
        raise TrainingDataInputError("Staged-restart live-parameter companion is incomplete.")
    for target, source in zip(parameters, live):
        if tuple(target.shape) != tuple(source.shape):
            raise TrainingDataInputError("Staged-restart live parameter shape mismatch.")
        target.data.copy_(source.to(device=target.device, dtype=target.dtype))
    if plan.schedule.preserve_ema_state:
        state = payload.get("ema_state")
        if not isinstance(state, Mapping):
            raise TrainingDataInputError("Staged-restart EMA companion is missing.")
        ema.load_state_dict(dict(state))


def _install_ema_restart_patch() -> None:
    global _EMA_PATCH_INSTALLED
    if _EMA_PATCH_INSTALLED:
        return
    from torch_ema import ExponentialMovingAverage

    original = ExponentialMovingAverage.__init__
    if getattr(original, "_mdstats_precision_runtime", False):
        _EMA_PATCH_INSTALLED = True
        return

    def patched(self: Any, parameters: Iterable[Any], decay: float, use_num_updates: bool = True) -> None:
        parameter_list = list(parameters)
        original(self, parameter_list, decay, use_num_updates)
        restore_restart_companion_into_ema(self, parameter_list)

    setattr(patched, "_mdstats_precision_runtime", True)
    ExponentialMovingAverage.__init__ = patched  # type: ignore[assignment]
    _EMA_PATCH_INSTALLED = True


def _install_batch_cast_patch() -> None:
    global _BATCH_PATCH_INSTALLED
    if _BATCH_PATCH_INSTALLED:
        return
    import importlib

    module = importlib.import_module("mace.tools.train")
    original_train_one_epoch = module.train_one_epoch
    original_evaluate = module.evaluate

    class CastingLoader:
        def __init__(self, loader: Any, model: Any):
            self._loader = loader
            self._model = model
        def __iter__(self):
            for batch in self._loader:
                yield cast_batch_to_model_dtype(batch, self._model)
        def __len__(self):
            return len(self._loader)
        def __getattr__(self, name: str) -> Any:
            return getattr(self._loader, name)

    def train_one_epoch(*args: Any, **kwargs: Any) -> Any:
        model = kwargs.get("model", args[0] if args else None)
        loader = kwargs.get("data_loader")
        if loader is None and len(args) > 2:
            loader = args[2]
        if model is not None and loader is not None:
            wrapped = CastingLoader(loader, model)
            if "data_loader" in kwargs:
                kwargs["data_loader"] = wrapped
            else:
                args = tuple(wrapped if index == 2 else item for index, item in enumerate(args))
        return original_train_one_epoch(*args, **kwargs)

    def evaluate(*args: Any, **kwargs: Any) -> Any:
        model = kwargs.get("model", args[0] if args else None)
        loader = kwargs.get("data_loader")
        if loader is None and len(args) > 2:
            loader = args[2]
        if model is not None and loader is not None:
            wrapped = CastingLoader(loader, model)
            if "data_loader" in kwargs:
                kwargs["data_loader"] = wrapped
            else:
                args = tuple(wrapped if index == 2 else item for index, item in enumerate(args))
        return original_evaluate(*args, **kwargs)

    module.train_one_epoch = train_one_epoch
    module.evaluate = evaluate
    _BATCH_PATCH_INSTALLED = True


def _install_checkpoint_selection_patch() -> None:
    global _CHECKPOINT_PATCH_INSTALLED
    if _CHECKPOINT_PATCH_INSTALLED:
        return
    import importlib

    checkpoint_module = importlib.import_module("mace.tools.checkpoint")
    cls = checkpoint_module.CheckpointIO
    original = cls._get_latest_checkpoint_path

    def patched(self: Any, swa: Any) -> Any:
        plan = _ACTIVE_PLAN
        if plan is None or not plan.staged or bool(swa):
            return original(self, swa)
        payload = _RESTART_COMPANION
        if payload is None:
            return original(self, swa)
        epoch = int(payload["epoch"])
        candidates = []
        for path in self._list_file_paths():
            info = self._parse_checkpoint_path(path)
            if info is not None and info.tag == self.tag and not info.swa and info.epochs == epoch:
                candidates.append(info.path)
        if len(candidates) != 1:
            raise RuntimeError(
                f"Expected exactly one staged restart checkpoint for epoch {epoch}, found {len(candidates)}."
            )
        return candidates[0]

    cls._get_latest_checkpoint_path = patched  # type: ignore[assignment]
    _CHECKPOINT_PATCH_INSTALLED = True


@dataclass(frozen=True, slots=True)
class MacePrecisionStageTransitionRecord:
    job_digest: str
    protocol_digest: str
    optimizer_policy_digest: str
    schedule_digest: str
    source_stage_index: int
    destination_stage_index: int
    boundary_epoch: int
    boundary_update: int | None
    source_dtype: str
    destination_dtype: str
    learning_rates_before: tuple[float, ...]
    learning_rates_after: tuple[float, ...]
    scheduler_class: str
    model_class: str
    backend_identity: str
    pre_model_inventory: Mapping[str, Any]
    post_model_inventory: Mapping[str, Any]
    pre_optimizer_inventory: Mapping[str, int]
    post_optimizer_inventory: Mapping[str, int]
    pre_ema_inventory: Mapping[str, int]
    post_ema_inventory: Mapping[str, int]
    pre_state_inventory_digest: str
    post_state_inventory_digest: str
    source_checkpoint_sha256: str | None
    source_companion_sha256: str | None

    def __post_init__(self) -> None:
        for name in (
            "job_digest", "protocol_digest", "optimizer_policy_digest", "schedule_digest",
            "pre_state_inventory_digest", "post_state_inventory_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in ("source_checkpoint_sha256", "source_companion_sha256"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PRECISION_STAGE_TRANSITION_SCHEMA,
            "job_digest": self.job_digest,
            "protocol_digest": self.protocol_digest,
            "optimizer_policy_digest": self.optimizer_policy_digest,
            "schedule_digest": self.schedule_digest,
            "source_stage_index": self.source_stage_index,
            "destination_stage_index": self.destination_stage_index,
            "boundary_epoch": self.boundary_epoch,
            "boundary_update": self.boundary_update,
            "source_dtype": self.source_dtype,
            "destination_dtype": self.destination_dtype,
            "learning_rates_before": list(self.learning_rates_before),
            "learning_rates_after": list(self.learning_rates_after),
            "scheduler_class": self.scheduler_class,
            "model_class": self.model_class,
            "backend_identity": self.backend_identity,
            "pre_model_inventory": self.pre_model_inventory,
            "post_model_inventory": self.post_model_inventory,
            "pre_optimizer_inventory": dict(self.pre_optimizer_inventory),
            "post_optimizer_inventory": dict(self.post_optimizer_inventory),
            "pre_ema_inventory": dict(self.pre_ema_inventory),
            "post_ema_inventory": dict(self.post_ema_inventory),
            "pre_state_inventory_digest": self.pre_state_inventory_digest,
            "post_state_inventory_digest": self.post_state_inventory_digest,
            "source_checkpoint_sha256": self.source_checkpoint_sha256,
            "source_companion_sha256": self.source_companion_sha256,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MacePrecisionStageTransitionRecord":
        if payload.get("schema") != PRECISION_STAGE_TRANSITION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported precision-stage transition schema.")
        result = cls(
            job_digest=str(payload["job_digest"]), protocol_digest=str(payload["protocol_digest"]),
            optimizer_policy_digest=str(payload["optimizer_policy_digest"]), schedule_digest=str(payload["schedule_digest"]),
            source_stage_index=int(payload["source_stage_index"]), destination_stage_index=int(payload["destination_stage_index"]),
            boundary_epoch=int(payload["boundary_epoch"]), boundary_update=None if payload.get("boundary_update") is None else int(payload["boundary_update"]),
            source_dtype=str(payload["source_dtype"]), destination_dtype=str(payload["destination_dtype"]),
            learning_rates_before=tuple(float(v) for v in payload["learning_rates_before"]),
            learning_rates_after=tuple(float(v) for v in payload["learning_rates_after"]),
            scheduler_class=str(payload["scheduler_class"]), model_class=str(payload["model_class"]),
            backend_identity=str(payload["backend_identity"]),
            pre_model_inventory=dict(payload["pre_model_inventory"]), post_model_inventory=dict(payload["post_model_inventory"]),
            pre_optimizer_inventory={str(k): int(v) for k, v in payload["pre_optimizer_inventory"].items()},
            post_optimizer_inventory={str(k): int(v) for k, v in payload["post_optimizer_inventory"].items()},
            pre_ema_inventory={str(k): int(v) for k, v in payload["pre_ema_inventory"].items()},
            post_ema_inventory={str(k): int(v) for k, v in payload["post_ema_inventory"].items()},
            pre_state_inventory_digest=str(payload["pre_state_inventory_digest"]), post_state_inventory_digest=str(payload["post_state_inventory_digest"]),
            source_checkpoint_sha256=None if payload.get("source_checkpoint_sha256") is None else str(payload["source_checkpoint_sha256"]),
            source_companion_sha256=None if payload.get("source_companion_sha256") is None else str(payload["source_companion_sha256"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Precision-stage transition digest mismatch.")
        return result


def transition_record_path(checkpoints_dir: str | Path, boundary_epoch: int) -> Path:
    return Path(checkpoints_dir).expanduser().resolve() / f"{PRECISION_TRANSITION_PREFIX}{boundary_epoch}.json"


def apply_precision_stage_boundary(
    *,
    model: Any,
    optimizer: Any,
    lr_scheduler: Any,
    ema: Any | None,
    loss_fn: Any,
    epoch: int,
    distributed_model: Any | None = None,
    swa: Any | None = None,
) -> MacePrecisionStageTransitionRecord | None:
    """Promote all qualified live training state when ``epoch`` enters a new stage."""

    import torch

    plan = _ACTIVE_PLAN
    if plan is None or not plan.staged:
        return None
    if distributed_model is not None:
        raise TrainingDataInputError("PREC2 staged precision does not qualify distributed/DDP training.")
    if swa is not None:
        raise TrainingDataInputError("PREC2 staged precision does not qualify SWA training.")
    destination_index = plan.stage_index_for_epoch(int(epoch))
    if destination_index == 0:
        return None
    destination = plan.schedule.stages[destination_index]
    if int(epoch) != destination.start_epoch:
        return None
    if destination_index in _TRANSITION_APPLIED:
        return None
    source = plan.schedule.stages[destination_index - 1]
    actual_source = _dtype_name(_model_parameter_dtype(model))
    if actual_source == destination.dtype:
        _TRANSITION_APPLIED.add(destination_index)
        return None
    if actual_source != source.dtype:
        raise TrainingDataInputError(
            f"Precision transition expected source dtype {source.dtype}, observed {actual_source}."
        )
    if plan.schedule.preserve_ema_state and ema is None:
        raise TrainingDataInputError("Staged precision transition requires EMA state preservation.")
    checkpoint_dir = getattr(getattr(globals().get("_ACTIVE_CHECKPOINT_HANDLER", None), "io", None), "directory", None)
    # The handler is supplied to persistence hooks; infer its path from the plan here.
    checkpoint_dir = plan.checkpoints_dir or checkpoint_dir
    source_checkpoint_sha = None
    source_companion_sha = None
    if checkpoint_dir is not None and int(epoch) > 0:
        comp = companion_path(checkpoint_dir)
        if not comp.is_file():
            raise TrainingDataInputError(
                "Precision transition requires the authenticated continuation companion from the preceding epoch."
            )
        comp_payload = _load_companion(comp, plan=plan, map_location="cpu")
        if int(comp_payload["epoch"]) != int(epoch) - 1:
            raise TrainingDataInputError("Precision transition companion is not from the preceding epoch.")
        source_companion_sha = _sha256_file(comp)
        raw_name = str(comp_payload.get("raw_checkpoint_name", ""))
        raw = Path(checkpoint_dir) / raw_name
        if not raw.is_file():
            raise TrainingDataInputError("Precision transition source checkpoint is missing.")
        source_checkpoint_sha = _sha256_file(raw)

    lrs_before = tuple(float(group["lr"]) for group in optimizer.param_groups)
    pre_model = model_dtype_inventory(model)
    pre_optimizer = optimizer_dtype_inventory(optimizer)
    pre_ema = ema_dtype_inventory(ema)
    pre_digest = _inventory_digest(model=model, optimizer=optimizer, ema=ema, lrs=lrs_before)

    target_dtype = _torch_dtype(destination.dtype, torch)
    model.to(dtype=target_dtype)
    if hasattr(loss_fn, "to"):
        loss_fn.to(dtype=target_dtype)
    _optimizer_to_dtype(optimizer, dtype=target_dtype)
    if ema is not None:
        ema.to(dtype=target_dtype)
    torch.set_default_dtype(target_dtype)

    factor = float(destination.learning_rate_scale)
    if factor != 1.0:
        for group in optimizer.param_groups:
            group["lr"] = float(group["lr"]) * factor
        _scale_scheduler_lr_state(lr_scheduler, factor=factor)
    lrs_after = tuple(float(group["lr"]) for group in optimizer.param_groups)

    post_model = model_dtype_inventory(model)
    post_optimizer = optimizer_dtype_inventory(optimizer)
    post_ema = ema_dtype_inventory(ema)
    post_digest = _inventory_digest(model=model, optimizer=optimizer, ema=ema, lrs=lrs_after)
    for inventory_name, inventory in (("optimizer", post_optimizer), ("EMA", post_ema)):
        stale = [name for name, count in inventory.items() if count > 0 and name != destination.dtype]
        if stale:
            raise TrainingDataInputError(
                f"Precision transition left stale floating {inventory_name} state: {stale}."
            )
    for group_name in ("parameters", "buffers"):
        stale = [row[1] for row in post_model[group_name] if row[1] != destination.dtype]
        if stale:
            raise TrainingDataInputError(
                f"Precision transition left stale model {group_name}: {sorted(set(stale))}."
            )

    backend = type(model).__module__ + "." + type(model).__qualname__
    boundary_update = destination.start_update
    record = MacePrecisionStageTransitionRecord(
        job_digest=plan.job_digest,
        protocol_digest=plan.protocol_digest,
        optimizer_policy_digest=plan.optimizer_policy_digest,
        schedule_digest=plan.schedule_digest,
        source_stage_index=destination_index - 1,
        destination_stage_index=destination_index,
        boundary_epoch=int(epoch),
        boundary_update=None if boundary_update is None else int(boundary_update),
        source_dtype=source.dtype,
        destination_dtype=destination.dtype,
        learning_rates_before=lrs_before,
        learning_rates_after=lrs_after,
        scheduler_class=type(lr_scheduler).__module__ + "." + type(lr_scheduler).__qualname__,
        model_class=type(model).__module__ + "." + type(model).__qualname__,
        backend_identity=backend,
        pre_model_inventory=pre_model,
        post_model_inventory=post_model,
        pre_optimizer_inventory=pre_optimizer,
        post_optimizer_inventory=post_optimizer,
        pre_ema_inventory=pre_ema,
        post_ema_inventory=post_ema,
        pre_state_inventory_digest=pre_digest,
        post_state_inventory_digest=post_digest,
        source_checkpoint_sha256=source_checkpoint_sha,
        source_companion_sha256=source_companion_sha,
    )
    if checkpoint_dir is not None:
        target = transition_record_path(checkpoint_dir, int(epoch))
        if target.is_file():
            existing = MacePrecisionStageTransitionRecord.from_dict(json.loads(target.read_text(encoding="utf-8")))
            if existing.content_digest != record.content_digest:
                raise TrainingDataInputError("Existing precision-transition receipt disagrees with repeated transition.")
        else:
            _atomic_json(target, record.to_dict())
    _TRANSITION_APPLIED.add(destination_index)
    return record


def install_mace_precision_runtime_patches() -> None:
    """Install the qualified MACE 0.3.16 staged-runtime hooks."""

    plan = _ACTIVE_PLAN
    if plan is None or not plan.staged:
        return
    try:
        import mace
    except Exception as exc:  # pragma: no cover
        raise TrainingDataInputError("Staged precision runtime requires MACE.") from exc
    version = str(getattr(mace, "__version__", ""))
    if version != SUPPORTED_STAGED_MACE_VERSION:
        raise TrainingDataInputError(
            f"PREC2 is qualified only for MACE {SUPPORTED_STAGED_MACE_VERSION}; observed {version or 'unknown'}."
        )
    _install_ema_restart_patch()
    _install_batch_cast_patch()
    _install_checkpoint_selection_patch()


__all__ = [
    "PRECISION_RUNTIME_COMPANION_SCHEMA",
    "PRECISION_STAGE_TRANSITION_SCHEMA",
    "PrecisionRuntimePlan",
    "MacePrecisionStageTransitionRecord",
    "load_precision_runtime_plan",
    "configure_precision_runtime_from_argv",
    "install_mace_precision_runtime_patches",
    "apply_precision_stage_boundary",
    "persist_precision_runtime_companion",
    "latest_resumable_precision_epoch",
    "companion_path",
    "transition_record_path",
    "model_dtype_inventory",
    "optimizer_dtype_inventory",
    "ema_dtype_inventory",
    "cast_batch_to_model_dtype",
]
