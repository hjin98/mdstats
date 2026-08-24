"""Execution, evaluation, aggregation, committee, and freeze records for MLFF-DATA9B2.

The module keeps long-running external work auditable and restartable without
making scientific acceptance implicit.  It can supervise one MACE run, evaluate
saved checkpoints against immutable monitor artifacts, aggregate protocol-
matched fold/seed evidence, export target heads, and freeze the chosen protocol.
Locked evaluation remains inactive until an explicit activation decision exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence
from collections import OrderedDict
from threading import RLock
from copy import deepcopy

import numpy as np

from ._common import (
    sha256_file_cached,
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
    validate_serialized_digest,
)
from .campaign_control import (
    CandidateCheckpointCatalog,
    CheckpointFileRecord,
    CheckpointMetricRecord,
    CheckpointSelectionRecord,
    TrainingCampaignPlan,
    TrainingCampaignRunPlan,
    inventory_mace_checkpoints,
)
from .critical_precision import (
    CRITICAL_PRECISION_POLICY_ENVIRONMENT_VARIABLE,
    MaceCriticalPrecisionPolicy,
    activate_mace_critical_precision_policy,
    install_mace_critical_fp64_patch,
)
from .acceleration import MaceAccelerationPolicy, MaceAccelerationKernelMode
from .foundation import FoundationPotentialIdentity, FoundationInferenceIdentity
from .adaptive_stop import (
    ADAPTIVE_STOP_POLICY_ENVIRONMENT_VARIABLE,
    ADAPTIVE_STOP_STATE_PATH_ENVIRONMENT_VARIABLE,
    AdaptiveTrainingStopState,
)
from .mace_export import MaceExtxyzArtifact
from .mace_compatibility import mace_runtime_warning_handled
from .checkpoint_capsule import (
    EvaluationStateCapsuleRecord,
    capsule_file_payload,
    load_validated_capsule_payload,
    model_state_sha256,
    write_capsule_file_atomic,
)
from .replay import ReplayFileArtifact, ReplayLabelMode
from .protocol import MaceJobArtifact, MaceJobKind, SealedEvaluationArtifact, TrainingMode
from .production_qualification import ProductionCorpusQualificationRecord, ProductionGateStatus
from .mlcv_monitors import write_mlcv_diagnostic_history

_CANCELLATION_POLL_SECONDS = 1.0

TRAINING_EXECUTION_POLICY_SCHEMA = "mdstats.training-execution-policy.v2"
TRAINING_EXECUTION_POLICY_LEGACY_SCHEMA = "mdstats.training-execution-policy.v1"
TRAINING_RUN_ATTEMPT_SCHEMA = "mdstats.training-run-attempt.v1"
TRAINING_RUN_EXECUTION_SCHEMA = "mdstats.training-run-execution.v1"
CHECKPOINT_EVALUATION_POLICY_SCHEMA = "mdstats.checkpoint-evaluation-policy.v8"
CHECKPOINT_EVALUATION_POLICY_LEGACY_V7_SCHEMA = "mdstats.checkpoint-evaluation-policy.v7"
CHECKPOINT_EVALUATION_POLICY_LEGACY_V6_SCHEMA = "mdstats.checkpoint-evaluation-policy.v6"
CHECKPOINT_EVALUATION_POLICY_LEGACY_V5_SCHEMA = "mdstats.checkpoint-evaluation-policy.v5"
CHECKPOINT_EVALUATION_POLICY_LEGACY_V4_SCHEMA = "mdstats.checkpoint-evaluation-policy.v4"
CHECKPOINT_EVALUATION_POLICY_LEGACY_V3_SCHEMA = "mdstats.checkpoint-evaluation-policy.v3"
CHECKPOINT_EVALUATION_POLICY_LEGACY_V2_SCHEMA = "mdstats.checkpoint-evaluation-policy.v2"
CHECKPOINT_EVALUATION_POLICY_LEGACY_SCHEMA = "mdstats.checkpoint-evaluation-policy.v1"
INFERENCE_EXECUTION_PLAN_SCHEMA = "mdstats.inference-execution-plan.v2"
INFERENCE_EXECUTION_PLAN_LEGACY_SCHEMA = "mdstats.inference-execution-plan.v1"
MODEL_DATASET_METRIC_RECORD_SCHEMA = "mdstats.model-dataset-metric-record.v1"
CHECKPOINT_EVALUATION_RECORD_SCHEMA = "mdstats.checkpoint-evaluation-record.v3"
CHECKPOINT_EVALUATION_RECORD_LEGACY_V2_SCHEMA = "mdstats.checkpoint-evaluation-record.v2"
CHECKPOINT_EVALUATION_RECORD_LEGACY_SCHEMA = "mdstats.checkpoint-evaluation-record.v1"
PROTOCOL_VARIANT_AGGREGATE_SCHEMA = "mdstats.protocol-variant-aggregate.v1"
PROTOCOL_FAMILY_AGGREGATE_SCHEMA = "mdstats.protocol-family-aggregate.v1"
LEARNING_CURVE_RECORD_SCHEMA = "mdstats.learning-curve-record.v1"
PROTOCOL_COMPARISON_RECORD_SCHEMA = "mdstats.protocol-comparison-record.v1"
COMMITTEE_EXPORT_POLICY_SCHEMA = "mdstats.committee-export-policy.v1"
COMMITTEE_MEMBER_RECORD_SCHEMA = "mdstats.committee-member-record.v1"
COMMITTEE_IDENTITY_SCHEMA = "mdstats.committee-identity.v1"
PROTOCOL_FREEZE_RECORD_SCHEMA = "mdstats.protocol-freeze-record.v1"
EVALUATION_ACTIVATION_DECISION_SCHEMA = "mdstats.evaluation-activation-decision.v1"
VERIFICATION_MODEL_RECORD_SCHEMA = "mdstats.verification-model-record.v1"
AVAILABLE_MODEL_VERIFICATION_SET_SCHEMA = "mdstats.available-model-verification-set.v1"
MLFF_DATA9B2_VERSION = "0.20.57a0"


def _sha256_file(path: Path) -> str:
    return sha256_file_cached(path)


MACE_CHECKPOINT_MODEL_CACHE_SCHEMA = "mdstats.mace-checkpoint-model-cache.v2"
MACE_CHECKPOINT_MODEL_CACHE_LEGACY_SCHEMA = "mdstats.mace-checkpoint-model-cache.v1"
MACE_CHECKPOINT_MODEL_EXPORT_CONTRACT = "mace-0.3.16-direct-state-restore.v2"
MACE_CHECKPOINT_MODEL_LEGACY_EXPORT_CONTRACT = "mace-0.3.16-restart-export.v1"


def _load_torch_payload(path: Path) -> Any:
    try:
        import torch
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise TrainingDataInputError(
            "MACE checkpoint inspection requires the optional torch package."
        ) from exc
    try:
        # Modern PyTorch can memory-map zip-format checkpoints.  MACE checkpoints
        # also contain optimizer/scheduler state that evaluation does not touch;
        # mmap avoids eagerly faulting all of those tensors into RAM merely to
        # restore ``checkpoint["model"]``.
        return torch.load(path, map_location="cpu", weights_only=False, mmap=True)
    except (TypeError, RuntimeError, ValueError):
        try:
            return torch.load(path, map_location="cpu", weights_only=False)
        except TypeError:  # pragma: no cover - older torch compatibility
            try:
                return torch.load(path, map_location="cpu")
            except Exception as exc:
                raise TrainingDataInputError(
                    f"Could not deserialize MACE candidate bytes: {path!s}."
                ) from exc
        except Exception as exc:
            raise TrainingDataInputError(
                f"Could not deserialize MACE candidate bytes: {path!s}."
            ) from exc
    except Exception as exc:
        raise TrainingDataInputError(
            f"Could not deserialize MACE candidate bytes: {path!s}."
        ) from exc


def _is_deployable_mace_model_payload(payload: Any) -> bool:
    return bool(
        hasattr(payload, "to")
        and hasattr(payload, "parameters")
        and hasattr(payload, "state_dict")
    )


def _is_mace_training_checkpoint_payload(payload: Any) -> bool:
    return bool(
        isinstance(payload, Mapping)
        and isinstance(payload.get("model"), Mapping)
        and "optimizer" in payload
        and "lr_scheduler" in payload
    )


def _validated_cached_checkpoint_model(
    model_path: Path,
    sidecar_path: Path,
    *,
    checkpoint_sha256: str,
    config_sha256: str,
) -> bool:
    if not model_path.is_file() or not sidecar_path.is_file():
        return False
    try:
        payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
        if payload.get("schema") not in {
            MACE_CHECKPOINT_MODEL_CACHE_SCHEMA,
            MACE_CHECKPOINT_MODEL_CACHE_LEGACY_SCHEMA,
        }:
            return False
        if payload.get("export_contract") not in {
            MACE_CHECKPOINT_MODEL_EXPORT_CONTRACT,
            MACE_CHECKPOINT_MODEL_LEGACY_EXPORT_CONTRACT,
        }:
            return False
        if payload.get("checkpoint_sha256") != checkpoint_sha256:
            return False
        if payload.get("config_sha256") != config_sha256:
            return False
        if payload.get("model_sha256") != _sha256_file(model_path):
            return False
        return _is_deployable_mace_model_payload(_load_torch_payload(model_path))
    except Exception:
        return False



def _bool_config(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _training_whole_model_path(cache_root: Path, name: str) -> Path | None:
    """Return the stable whole-model artifact emitted by the completed MACE run."""

    candidate = cache_root.parent / "models" / f"{name}.model"
    return candidate if candidate.is_file() else None


def _floating_state_dtypes(state: Mapping[str, Any]) -> frozenset[str]:
    """Return floating dtypes present in a checkpoint/model state dictionary."""

    values: set[str] = set()
    for value in state.values():
        is_floating = bool(getattr(value, "is_floating_point", lambda: False)())
        if is_floating:
            values.add(str(value.dtype).removeprefix("torch."))
    return frozenset(values)


def _uniform_floating_state_dtype(state: Mapping[str, Any]) -> str | None:
    """Return the unique FP32/FP64 dtype when the complete state is uniform."""

    values = _floating_state_dtypes(state)
    if len(values) != 1 or next(iter(values), None) not in {"float32", "float64"}:
        return None
    return next(iter(values))


def _checkpoint_execution_dtype(
    state: Mapping[str, Any], config_payload: Mapping[str, Any]
) -> str | None:
    """Resolve the MACE execution dtype without requiring uniform floating buffers.

    A MACE model's learned-model dtype is defined by its parameters.  Its state
    dictionary may nevertheless contain floating buffers in the other qualified
    precision (for example FP64 bookkeeping/reference buffers in an FP32 model).
    Raw checkpoints do not distinguish parameters from buffers, so a uniform state
    is authoritative when available; otherwise the immutable DATA8 ``default_dtype``
    is the qualified source of truth for an FP32/FP64 mixed-buffer state.
    """

    values = _floating_state_dtypes(state)
    if not values or not values.issubset({"float32", "float64"}):
        return None
    if len(values) == 1:
        return next(iter(values))
    configured = str(config_payload.get("default_dtype", "")).strip().lower()
    if configured in {"float32", "float64"} and configured in values:
        return configured
    return None


def _state_dict_structure_compatible(model: Any, state: Mapping[str, Any]) -> bool:
    """Require exact state keys/shapes/dtypes so load_state_dict cannot cast silently."""

    try:
        current = model.state_dict()
        if set(current) != set(state):
            return False
        for key, value in current.items():
            other = state[key]
            if getattr(value, "shape", None) != getattr(other, "shape", None):
                return False
            if getattr(value, "dtype", None) != getattr(other, "dtype", None):
                return False
        return True
    except Exception:
        return False


def _state_dict_exactly_matches(model: Any, state: Mapping[str, Any]) -> bool:
    """Return whether a model already carries exactly the checkpoint tensor state."""

    if not _state_dict_structure_compatible(model, state):
        return False
    try:
        current = model.state_dict()
        for key, value in current.items():
            other = state[key]
            if hasattr(value, "device") and str(value.device) != "cpu":
                value = value.detach().cpu()
            if hasattr(other, "device") and str(other.device) != "cpu":
                other = other.detach().cpu()
            if hasattr(value, "equal"):
                if not bool(value.equal(other)):
                    return False
            elif value != other:
                return False
        return True
    except Exception:
        return False


def _restore_checkpoint_into_template(
    template_path: Path,
    checkpoint_payload: Mapping[str, Any],
    config_payload: Mapping[str, Any],
    *,
    allow_dtype_cast: bool = False,
) -> tuple[Any, bool] | None:
    """Restore one MACE checkpoint state into a completed-run architecture template.

    MACE 0.3.16 checkpoints contain only ``state_dict`` data.  The stable whole
    model written at the end of training supplies the architecture.  When training
    used CuEquivariance or OpenEquivariance, MACE saves the final whole model after
    converting it back to e3nn; reproduce the inverse/forward conversion around
    ``load_state_dict`` so checkpoint parameter names match exactly.

    ``None`` means this configuration is not yet qualified for the direct path and
    the caller must use the legacy restart-export subprocess.
    """

    # LoRA checkpoints contain adapter modules while the completed whole model has
    # merged weights. Reconstructing that architecture requires the training setup,
    # so keep the legacy path for now rather than guessing.
    if _bool_config(config_payload.get("lora")):
        return None

    model = _load_torch_payload(template_path)
    if not _is_deployable_mace_model_payload(model):
        return None
    state = checkpoint_payload.get("model")
    if not isinstance(state, Mapping):
        return None
    # Do not require every floating state tensor to share one dtype.  MACE may
    # legitimately carry FP32 learned parameters together with FP64 floating
    # buffers.  Exact per-key dtype compatibility below is the correctness gate.
    # Uniform states retain the historical optional whole-model cast path.
    checkpoint_dtype = _uniform_floating_state_dtype(state)
    template_dtype = _uniform_floating_state_dtype(model.state_dict())
    if (
        checkpoint_dtype is not None
        and template_dtype is not None
        and template_dtype != checkpoint_dtype
    ):
        if not allow_dtype_cast:
            return None
        try:
            import torch
            model = model.to(dtype=torch.float32 if checkpoint_dtype == "float32" else torch.float64)
        except Exception:
            return None

    enable_cueq = _bool_config(config_payload.get("enable_cueq"))
    only_cueq = _bool_config(config_payload.get("only_cueq"))
    enable_oeq = _bool_config(config_payload.get("enable_oeq")) and not enable_cueq
    conversion_device = str(config_payload.get("device", "cpu") or "cpu")

    try:
        # The conversion functions use PyTorch FX and therefore share the same
        # process-wide lock as MACECalculator's guarded conversion path.
        from .model_features import _MACE_ACCELERATOR_CONVERSION_LOCK

        template_matches = False
        if enable_cueq and not only_cueq:
            from mace.cli.convert_e3nn_cueq import run as to_training_backend
            from mace.cli.convert_cueq_e3nn import run as to_deployable_backend

            with _MACE_ACCELERATOR_CONVERSION_LOCK:
                model = to_training_backend(deepcopy(model), device=conversion_device)
            if not _state_dict_structure_compatible(model, state):
                return None
            template_matches = _state_dict_exactly_matches(model, state)
            if not template_matches:
                model.load_state_dict(state, strict=True)
            with _MACE_ACCELERATOR_CONVERSION_LOCK:
                model = to_deployable_backend(deepcopy(model), device=conversion_device)
        elif enable_oeq:
            from mace.cli.convert_e3nn_oeq import run as to_training_backend
            from mace.cli.convert_oeq_e3nn import run as to_deployable_backend

            with _MACE_ACCELERATOR_CONVERSION_LOCK:
                model = to_training_backend(deepcopy(model), device=conversion_device)
            if not _state_dict_structure_compatible(model, state):
                return None
            template_matches = _state_dict_exactly_matches(model, state)
            if not template_matches:
                model.load_state_dict(state, strict=True)
            with _MACE_ACCELERATOR_CONVERSION_LOCK:
                model = to_deployable_backend(deepcopy(model), device=conversion_device)
        else:
            if not _state_dict_structure_compatible(model, state):
                return None
            template_matches = _state_dict_exactly_matches(model, state)
            if not template_matches:
                model.load_state_dict(state, strict=True)
        return model.to("cpu"), template_matches
    except (ImportError, ModuleNotFoundError):
        return None
    except Exception:
        # A strict state mismatch or unsupported conversion means this MACE
        # configuration is outside the qualified direct-restoration envelope.
        # Preserve correctness by falling back to the old restart-export path.
        return None


def _write_checkpoint_model_cache(
    model: Any,
    *,
    cached_model: Path,
    cached_sidecar: Path,
    checkpoint: CheckpointFileRecord,
    config_sha256: str,
    reconstruction_method: str,
    elapsed_seconds: float,
) -> Path:
    import torch

    temporary_target = cached_model.with_name(
        f".{cached_model.stem}.{os.getpid()}.{time.time_ns()}.model"
    )
    torch.save(model, temporary_target)
    os.replace(temporary_target, cached_model)
    sidecar_payload = {
        "schema": MACE_CHECKPOINT_MODEL_CACHE_SCHEMA,
        "export_contract": MACE_CHECKPOINT_MODEL_EXPORT_CONTRACT,
        "checkpoint_sha256": checkpoint.sha256,
        "checkpoint_epoch": checkpoint.epoch,
        "config_sha256": config_sha256,
        "model_sha256": _sha256_file(cached_model),
        "model_size_bytes": cached_model.stat().st_size,
        "reconstruction_method": reconstruction_method,
        "materialization_elapsed_seconds": float(elapsed_seconds),
    }
    temporary_sidecar = cached_sidecar.with_name(
        f".{cached_sidecar.stem}.{os.getpid()}.{time.time_ns()}.json"
    )
    temporary_sidecar.write_text(
        json.dumps(sidecar_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary_sidecar, cached_sidecar)
    return cached_model


def _deployable_state_dicts_equal(first: Any, second: Any) -> bool:
    try:
        left = first.state_dict()
        right = second.state_dict()
        if set(left) != set(right):
            return False
        for key in left:
            a = left[key].detach().cpu() if hasattr(left[key], "detach") else left[key]
            b = right[key].detach().cpu() if hasattr(right[key], "detach") else right[key]
            if getattr(a, "shape", None) != getattr(b, "shape", None):
                return False
            if getattr(a, "dtype", None) != getattr(b, "dtype", None):
                return False
            if hasattr(a, "equal"):
                if not bool(a.equal(b)):
                    return False
            elif a != b:
                return False
        return True
    except Exception:
        return False


@mace_runtime_warning_handled("MACE checkpoint compaction")
def create_mace_evaluation_state_capsule(
    checkpoint: CheckpointFileRecord,
    checkpoint_path: str | Path,
    *,
    mace_config_path: str | Path,
    cache_directory: str | Path,
    capsule_path: str | Path,
    allow_checkpoint_dtype_template_cast: bool = False,
) -> EvaluationStateCapsuleRecord:
    """Create and independently validate a STOR2 model-state-only capsule.

    The original optimizer-bearing checkpoint is never modified by this function.
    A caller may delete it only after this record has been durably committed.
    """

    source = Path(checkpoint_path).resolve()
    config = Path(mace_config_path).resolve()
    cache_root = Path(cache_directory).resolve()
    destination = Path(capsule_path).resolve()
    if not source.is_file() or _sha256_file(source) != checkpoint.sha256:
        raise TrainingDataInputError(
            "Checkpoint bytes required for STOR2 compaction do not match inventory."
        )
    if not config.is_file():
        raise TrainingDataInputError("Immutable DATA8 MACE configuration is missing.")
    raw_payload = _load_torch_payload(source)
    if not _is_mace_training_checkpoint_payload(raw_payload):
        raise TrainingDataInputError(
            "STOR2 compaction supports qualified optimizer-bearing MACE training checkpoints only."
        )
    state = raw_payload.get("model")
    if not isinstance(state, Mapping):
        raise TrainingDataInputError("MACE checkpoint does not contain a model state mapping.")
    state_digest = model_state_sha256(state)
    config_sha = _sha256_file(config)

    try:
        import yaml
        loaded = yaml.safe_load(config.read_text(encoding="utf-8"))
    except Exception as exc:
        raise TrainingDataInputError("Could not parse immutable DATA8 MACE config for STOR2.") from exc
    if not isinstance(loaded, dict):
        raise TrainingDataInputError("DATA8 MACE configuration must be a mapping.")
    name = str(loaded.get("name", "")).strip()
    if not name:
        raise TrainingDataInputError("DATA8 MACE configuration does not define a model name.")
    template = _training_whole_model_path(cache_root, name)
    if template is None:
        raise TrainingDataInputError(
            "STOR2 cannot compact this checkpoint because the completed whole-model architecture template is missing."
        )

    restored_raw = _restore_checkpoint_into_template(
        template, raw_payload, loaded,
        allow_dtype_cast=allow_checkpoint_dtype_template_cast,
    )
    if restored_raw is None:
        raise TrainingDataInputError(
            "STOR2 direct reconstruction is unsupported for this MACE checkpoint layout; raw checkpoint retained."
        )
    raw_model, _ = restored_raw

    payload = capsule_file_payload(
        run_plan_digest=checkpoint.run_plan_digest,
        source_checkpoint_sha256=checkpoint.sha256,
        source_checkpoint_epoch=checkpoint.epoch,
        source_checkpoint_size_bytes=checkpoint.size_bytes,
        model_state=state,
        model_state_digest=state_digest,
        mace_config_sha256=config_sha,
    )
    capsule_sha, capsule_size = write_capsule_file_atomic(destination, payload)
    if capsule_size >= checkpoint.size_bytes:
        destination.unlink(missing_ok=True)
        raise TrainingDataInputError(
            "STOR2 model-state capsule would not reduce storage; raw checkpoint retained."
        )
    record = EvaluationStateCapsuleRecord(
        run_plan_digest=checkpoint.run_plan_digest,
        source_checkpoint_sha256=checkpoint.sha256,
        source_checkpoint_epoch=checkpoint.epoch,
        source_checkpoint_size_bytes=checkpoint.size_bytes,
        capsule_path=str(destination),
        capsule_sha256=capsule_sha,
        capsule_size_bytes=capsule_size,
        model_state_sha256=state_digest,
        mace_config_sha256=config_sha,
        verified_exact_model_state=True,
        created_at_utc=_utc_now(),
    )
    try:
        compact_payload = load_validated_capsule_payload(
            record, destination,
            expected_run_plan_digest=checkpoint.run_plan_digest,
            expected_checkpoint_sha256=checkpoint.sha256,
            expected_epoch=checkpoint.epoch,
            expected_config_sha256=config_sha,
        )
        restored_compact = _restore_checkpoint_into_template(
            template, compact_payload, loaded,
            allow_dtype_cast=allow_checkpoint_dtype_template_cast,
        )
        if restored_compact is None or not _deployable_state_dicts_equal(
            raw_model, restored_compact[0]
        ):
            raise TrainingDataInputError(
                "STOR2 capsule reconstruction did not reproduce the original deployable model state exactly."
            )
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    if _sha256_file(source) != checkpoint.sha256:
        destination.unlink(missing_ok=True)
        raise TrainingDataInputError(
            "STOR2 compaction observed a changed source checkpoint; capsule discarded."
        )
    return record


@mace_runtime_warning_handled("MACE checkpoint materialization")
def materialize_mace_checkpoint_model(
    checkpoint: CheckpointFileRecord,
    checkpoint_path: str | Path,
    *,
    mace_config_path: str | Path,
    job_working_directory: str | Path,
    cache_directory: str | Path,
    wrapper_path: str | Path | None = None,
    environment: Mapping[str, str] | None = None,
    timeout_seconds: float = 3600.0,
    allow_checkpoint_dtype_template_cast: bool = False,
    evaluation_state_capsule: EvaluationStateCapsuleRecord | None = None,
) -> Path:
    """Return a deployable whole-model serialization for one exact checkpoint.

    MACE 0.3.16 ``*.pt`` epoch checkpoints contain state dictionaries for the
    model, optimizer, and scheduler.  ``MACECalculator`` and ``select_head``
    require a serialized ``torch.nn.Module`` instead.  For raw checkpoints this
    helper first restores the state directly into the completed run's whole-model
    architecture template.  This avoids re-entering MACE training initialization.
    The qualified mdstats MACE training-wrapper restart/export remains a fail-safe
    fallback for configurations outside the direct-restoration envelope. Existing
    whole-model candidates are returned unchanged.
    """

    from .inference_parallel import (
        mark_inference_workload_started,
        report_inference_worker_phase,
    )

    materialization_started = time.monotonic()

    # Checkpoint authentication is the first expensive per-candidate operation:
    # it hashes and deserializes a potentially multi-gigabyte artifact.  Start
    # telemetry here so model reconstruction/loading is represented even when
    # the eventual batched inference is comparatively fast.
    mark_inference_workload_started("authenticating checkpoint artifact")
    source = Path(checkpoint_path).resolve()
    config = Path(mace_config_path).resolve()
    job_root = Path(job_working_directory).resolve()
    cache_root = Path(cache_directory).resolve()
    if not config.is_file():
        raise TrainingDataInputError("Immutable DATA8 MACE configuration is missing.")
    if not job_root.is_dir():
        raise TrainingDataInputError("Immutable DATA8 MACE job directory is missing.")

    report_inference_worker_phase("reading checkpoint payload")
    source_expected_sha256 = checkpoint.sha256
    if evaluation_state_capsule is None:
        if not source.is_file() or _sha256_file(source) != checkpoint.sha256:
            raise TrainingDataInputError(
                "Checkpoint bytes required for model reconstruction do not match inventory."
            )
        payload = _load_torch_payload(source)
        if _is_deployable_mace_model_payload(payload):
            return source
        if not _is_mace_training_checkpoint_payload(payload):
            raise TrainingDataInputError(
                "Candidate is neither a deployable MACE model nor a qualified MACE "
                "training checkpoint containing model/optimizer/lr_scheduler state."
            )
    else:
        source_expected_sha256 = evaluation_state_capsule.capsule_sha256
        payload = load_validated_capsule_payload(
            evaluation_state_capsule,
            source,
            expected_run_plan_digest=checkpoint.run_plan_digest,
            expected_checkpoint_sha256=checkpoint.sha256,
            expected_epoch=checkpoint.epoch,
            expected_config_sha256=_sha256_file(config),
        )

    try:
        import yaml
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise TrainingDataInputError(
            "MACE checkpoint reconstruction requires PyYAML."
        ) from exc
    try:
        loaded = yaml.safe_load(config.read_text(encoding="utf-8"))
    except Exception as exc:
        raise TrainingDataInputError("Could not parse the immutable DATA8 MACE config.") from exc
    if not isinstance(loaded, dict):
        raise TrainingDataInputError("DATA8 MACE configuration must be a mapping.")
    name = str(loaded.get("name", "")).strip()
    if not name:
        raise TrainingDataInputError("DATA8 MACE configuration does not define a model name.")
    try:
        seed = int(loaded["seed"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TrainingDataInputError("DATA8 MACE configuration does not define an integer seed.") from exc

    cache_root.mkdir(parents=True, exist_ok=True)
    config_sha256 = _sha256_file(config)
    stem = f"checkpoint-{checkpoint.sha256[:20]}"
    cached_model = cache_root / f"{stem}.model"
    cached_sidecar = cache_root / f"{stem}.json"
    report_inference_worker_phase("checking deployable-model cache")
    if _validated_cached_checkpoint_model(
        cached_model,
        cached_sidecar,
        checkpoint_sha256=checkpoint.sha256,
        config_sha256=config_sha256,
    ):
        return cached_model

    report_inference_worker_phase("checking completed training model template")
    template = _training_whole_model_path(cache_root, name)
    if template is not None:
        report_inference_worker_phase("restoring checkpoint weights directly")
        restored = _restore_checkpoint_into_template(
            template, payload, loaded,
            allow_dtype_cast=allow_checkpoint_dtype_template_cast,
        )
        if restored is not None:
            direct_model, template_matches = restored
            if template_matches:
                report_inference_worker_phase(
                    "reusing completed training model directly "
                    f"({time.monotonic() - materialization_started:.2f}s)"
                )
                return template.resolve()
            report_inference_worker_phase("writing direct checkpoint-model cache")
            result = _write_checkpoint_model_cache(
                direct_model,
                cached_model=cached_model,
                cached_sidecar=cached_sidecar,
                checkpoint=checkpoint,
                config_sha256=config_sha256,
                reconstruction_method="direct_state_restore",
                elapsed_seconds=time.monotonic() - materialization_started,
            )
            if _sha256_file(source) != source_expected_sha256:
                result.unlink(missing_ok=True)
                cached_sidecar.unlink(missing_ok=True)
                raise TrainingDataInputError(
                    "Direct checkpoint restoration changed the original restart checkpoint; "
                    "the derived model was discarded."
                )
            report_inference_worker_phase(
                "direct checkpoint restoration complete "
                f"({time.monotonic() - materialization_started:.2f}s)"
            )
            return result

    if evaluation_state_capsule is not None:
        raise TrainingDataInputError(
            "Evaluation-state capsule could not be restored through the qualified direct path; "
            "the source raw checkpoint is required for this unsupported layout."
        )

    report_inference_worker_phase("direct restoration unavailable; using legacy restart export")
    executable = str(wrapper_path or shutil.which("mdstats-mace-train") or "")
    if not executable:
        raise TrainingDataInputError(
            "Qualified mdstats-mace-train wrapper is unavailable for checkpoint reconstruction."
        )
    timeout = float(timeout_seconds)
    if not np.isfinite(timeout) or timeout <= 0.0:
        raise TrainingDataInputError("Checkpoint reconstruction timeout must be positive.")

    staging = Path(tempfile.mkdtemp(prefix=f".{stem}-", dir=cache_root))
    checkpoints_dir = staging / "checkpoints"
    model_dir = staging / "models"
    log_dir = staging / "logs"
    results_dir = staging / "results"
    for directory in (checkpoints_dir, model_dir, log_dir, results_dir):
        directory.mkdir(parents=True, exist_ok=True)
    qualified_checkpoint = checkpoints_dir / f"{name}_run-{seed}_epoch-{checkpoint.epoch}.pt"
    # Never hard-link a restart checkpoint into the reconstruction sandbox.
    # MACE may rewrite or replace the selected checkpoint while finalizing its
    # export; a hard link would mutate the campaign's restart-critical bytes.
    shutil.copy2(source, qualified_checkpoint)

    derived = dict(loaded)
    checkpoint_state_dtype = _checkpoint_execution_dtype(payload["model"], loaded)
    if checkpoint_state_dtype is None:
        present = sorted(_floating_state_dtypes(payload["model"]))
        raise TrainingDataInputError(
            "Checkpoint model state does not carry a qualified FP32/FP64 execution dtype "
            f"consistent with immutable DATA8 default_dtype; floating state dtypes={present!r}."
        )
    derived.update(
        {
            "default_dtype": checkpoint_state_dtype,
            "model_dir": str(model_dir),
            "checkpoints_dir": str(checkpoints_dir),
            "log_dir": str(log_dir),
            "results_dir": str(results_dir),
            "restart_latest": True,
            "max_num_epochs": int(checkpoint.epoch) + 1,
            "save_cpu": True,
            "keep_checkpoints": True,
            "plot": False,
            "wandb": False,
            # A selected SWA snapshot is still an ordinary model state dict.
            # Load it through the stage-one path in the isolated checkpoint root
            # so MACE does not require a second, unrelated stage-one snapshot.
            "swa": False,
            "distributed": False,
        }
    )
    heads = derived.get("heads")
    if isinstance(heads, Mapping) and heads:
        derived["skip_evaluate_heads"] = ",".join(str(value) for value in heads)
    derived_config = staging / "checkpoint-export.yaml"
    derived_config.write_text(
        yaml.safe_dump(derived, sort_keys=True), encoding="utf-8"
    )
    stdout_path = staging / "export.stdout.log"
    stderr_path = staging / "export.stderr.log"
    command = (executable, "--config", str(derived_config))
    merged_env = dict(os.environ)
    if environment is not None:
        merged_env.update({str(key): str(value) for key, value in environment.items()})
    merged_env["MDSTATS_MACE_RESTART_EPOCH"] = str(checkpoint.epoch)
    merged_env.setdefault("PYTHONHASHSEED", str(seed))
    report_inference_worker_phase("reconstructing deployable MACE model")
    try:
        with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
            completed = subprocess.run(
                command,
                cwd=job_root,
                env=merged_env,
                stdout=stdout_handle,
                stderr=stderr_handle,
                check=False,
                timeout=timeout,
            )
    except subprocess.TimeoutExpired as exc:
        tail = stderr_path.read_text(encoding="utf-8", errors="replace")[-2000:]
        shutil.rmtree(staging, ignore_errors=True)
        raise TrainingDataInputError(
            "Timed out while reconstructing a deployable MACE model from the "
            f"selected checkpoint. Last stderr:\n{tail}"
        ) from exc

    produced = model_dir / f"{name}.model"
    if completed.returncode != 0 or not produced.is_file():
        tail = stderr_path.read_text(encoding="utf-8", errors="replace")[-4000:]
        shutil.rmtree(staging, ignore_errors=True)
        raise TrainingDataInputError(
            "MACE checkpoint reconstruction failed. Last stderr:\n" + tail
        )
    report_inference_worker_phase("validating reconstructed MACE model")
    produced_payload = _load_torch_payload(produced)
    if not _is_deployable_mace_model_payload(produced_payload):
        shutil.rmtree(staging, ignore_errors=True)
        raise TrainingDataInputError(
            "MACE checkpoint reconstruction did not produce a deployable model object."
        )
    del produced_payload

    temporary_target = cache_root / f".{stem}.{os.getpid()}.model"
    shutil.move(str(produced), temporary_target)
    os.replace(temporary_target, cached_model)
    sidecar_payload = {
        "schema": MACE_CHECKPOINT_MODEL_CACHE_SCHEMA,
        "export_contract": MACE_CHECKPOINT_MODEL_EXPORT_CONTRACT,
        "checkpoint_sha256": checkpoint.sha256,
        "checkpoint_epoch": checkpoint.epoch,
        "config_sha256": config_sha256,
        "model_sha256": _sha256_file(cached_model),
        "model_size_bytes": cached_model.stat().st_size,
        "reconstruction_method": "legacy_restart_export",
        "materialization_elapsed_seconds": float(time.monotonic() - materialization_started),
    }
    temporary_sidecar = cache_root / f".{stem}.{os.getpid()}.json"
    temporary_sidecar.write_text(
        json.dumps(sidecar_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary_sidecar, cached_sidecar)
    shutil.rmtree(staging, ignore_errors=True)
    if _sha256_file(source) != source_expected_sha256:
        cached_model.unlink(missing_ok=True)
        cached_sidecar.unlink(missing_ok=True)
        raise TrainingDataInputError(
            "Checkpoint reconstruction changed the original restart checkpoint; "
            "the derived model was discarded."
        )
    report_inference_worker_phase(
        "legacy checkpoint reconstruction complete "
        f"({time.monotonic() - materialization_started:.2f}s)"
    )
    return cached_model


def remove_materialized_mace_checkpoint_model(path: str | Path) -> None:
    """Remove one reconstructable checkpoint-model cache entry, if present."""

    model = Path(path).resolve()
    if not model.name.startswith("checkpoint-") or model.suffix != ".model":
        return
    sidecar = model.with_suffix(".json")
    model.unlink(missing_ok=True)
    sidecar.unlink(missing_ok=True)
    try:
        model.parent.rmdir()
    except OSError:
        pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _contained(root: Path, relative: str, *, name: str) -> Path:
    if not relative.strip():
        raise TrainingDataInputError(f"{name} must be non-empty.")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise TrainingDataInputError(f"{name} escapes its declared root.") from exc
    return candidate


def _finite_nonnegative(value: float, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise TrainingDataInputError(f"{name} must be finite and nonnegative.")
    return result


class TrainingRunState(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    INTERRUPTED = "interrupted"


class EvaluationActivationOutcome(str, Enum):
    ACTIVATED = "activated"
    REJECTED = "rejected"


class VerificationEvidenceLevel(str, Enum):
    COMPLETE_VARIANT = "complete_variant"
    PARTIAL_CROSS_VALIDATION = "partial_cross_validation"
    SINGLE_MODEL = "single_model"


@dataclass(frozen=True, slots=True)
class TrainingExecutionPolicy:
    required_wrapper: str = "mdstats-mace-train"
    max_attempts: int = 2
    timeout_seconds: float | None = None
    terminate_grace_seconds: float = 30.0
    resume_latest_on_retry: bool = True
    require_checkpoint_on_success: bool = True
    checkpoint_glob: str = "*epoch*.pt"
    runtime_layout_version: str = "data8-job-cwd.v1"
    environment_allowlist: tuple[str, ...] = (
        "PATH",
        "PYTHONPATH",
        "CUDA_VISIBLE_DEVICES",
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
    )
    _serialization_schema: str = field(
        default=TRAINING_EXECUTION_POLICY_SCHEMA,
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if not self.required_wrapper.strip() or self.required_wrapper == "mace_run_train":
            raise TrainingDataInputError("DATA9B2 requires the precision-aware mdstats MACE wrapper.")
        if self.max_attempts <= 0:
            raise TrainingDataInputError("Training execution max_attempts must be positive.")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0.0:
            raise TrainingDataInputError("Training timeout must be positive when present.")
        if self.terminate_grace_seconds <= 0.0:
            raise TrainingDataInputError("Termination grace period must be positive.")
        if not self.checkpoint_glob.strip():
            raise TrainingDataInputError("Checkpoint glob must be non-empty.")
        if not self.runtime_layout_version.strip():
            raise TrainingDataInputError("Training runtime-layout version must be non-empty.")
        allowlist = tuple(sorted(set(str(v) for v in self.environment_allowlist if str(v))))
        object.__setattr__(self, "environment_allowlist", allowlist)

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": self._serialization_schema,
            "required_wrapper": self.required_wrapper,
            "max_attempts": self.max_attempts,
            "timeout_seconds": self.timeout_seconds,
            "terminate_grace_seconds": self.terminate_grace_seconds,
            "resume_latest_on_retry": self.resume_latest_on_retry,
            "require_checkpoint_on_success": self.require_checkpoint_on_success,
            "checkpoint_glob": self.checkpoint_glob,
            "environment_allowlist": list(self.environment_allowlist),
        }
        if self._serialization_schema == TRAINING_EXECUTION_POLICY_SCHEMA:
            payload["runtime_layout_version"] = self.runtime_layout_version
        return payload

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingExecutionPolicy":
        if payload.get("schema") not in {TRAINING_EXECUTION_POLICY_SCHEMA, TRAINING_EXECUTION_POLICY_LEGACY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported training-execution policy schema.")
        result = cls(
            required_wrapper=str(payload["required_wrapper"]),
            max_attempts=int(payload["max_attempts"]),
            timeout_seconds=None if payload.get("timeout_seconds") is None else float(payload["timeout_seconds"]),
            terminate_grace_seconds=float(payload["terminate_grace_seconds"]),
            resume_latest_on_retry=bool(payload["resume_latest_on_retry"]),
            require_checkpoint_on_success=bool(payload["require_checkpoint_on_success"]),
            checkpoint_glob=str(payload["checkpoint_glob"]),
            runtime_layout_version=str(payload.get("runtime_layout_version", "legacy-run-cwd.v1")),
            environment_allowlist=tuple(str(v) for v in payload.get("environment_allowlist", ())),
        )
        if payload.get("schema") == TRAINING_EXECUTION_POLICY_LEGACY_SCHEMA:
            object.__setattr__(
                result,
                "_serialization_schema",
                TRAINING_EXECUTION_POLICY_LEGACY_SCHEMA,
            )
        validate_serialized_digest(
            payload,
            digest_field="policy_digest",
            current_digest=result.policy_digest,
            error_message="Training-execution policy digest mismatch.",
        )
        return result


@dataclass(frozen=True, slots=True)
class TrainingRunAttemptRecord:
    run_plan_digest: str
    attempt_index: int
    execution_policy_digest: str
    command: tuple[str, ...]
    command_digest: str
    working_directory: str
    config_sha256: str
    environment_digest: str
    started_at_utc: str
    finished_at_utc: str
    elapsed_seconds: float
    state: TrainingRunState
    return_code: int | None
    stdout_relative_path: str
    stdout_sha256: str
    stderr_relative_path: str
    stderr_sha256: str
    failure_reason: str | None = None
    scientific_failure_code: str | None = None
    scientific_failure_evidence_digest: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "run_plan_digest",
            "execution_policy_digest",
            "command_digest",
            "config_sha256",
            "environment_digest",
            "stdout_sha256",
            "stderr_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.attempt_index <= 0 or not self.command:
            raise TrainingDataInputError("Training attempt requires a positive index and command.")
        object.__setattr__(self, "state", TrainingRunState(self.state))
        object.__setattr__(self, "elapsed_seconds", _finite_nonnegative(self.elapsed_seconds, name="elapsed_seconds"))
        if self.state is TrainingRunState.SUCCEEDED:
            if self.return_code != 0 or self.failure_reason is not None:
                raise TrainingDataInputError("Successful training attempt cannot carry failure evidence.")
        elif not self.failure_reason:
            raise TrainingDataInputError("Failed or timed-out training attempt requires a reason.")
        scientific_code = (
            None if self.scientific_failure_code is None else str(self.scientific_failure_code)
        )
        scientific_digest = self.scientific_failure_evidence_digest
        if (scientific_code is None) != (scientific_digest is None):
            raise TrainingDataInputError(
                "Scientific training-failure classification requires both code and authenticated evidence digest."
            )
        if scientific_code is not None:
            from .train2_runtime import TRAIN2_NUMERICAL_FAILURE_CODES

            if self.state is TrainingRunState.SUCCEEDED:
                raise TrainingDataInputError("Successful training attempt cannot carry scientific failure evidence.")
            if scientific_code not in TRAIN2_NUMERICAL_FAILURE_CODES:
                raise TrainingDataInputError("Unsupported scientific training-failure code.")
            object.__setattr__(
                self,
                "scientific_failure_evidence_digest",
                validate_digest(scientific_digest, name="scientific_failure_evidence_digest"),
            )
            object.__setattr__(self, "scientific_failure_code", scientific_code)

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": TRAINING_RUN_ATTEMPT_SCHEMA,
            "run_plan_digest": self.run_plan_digest,
            "attempt_index": self.attempt_index,
            "execution_policy_digest": self.execution_policy_digest,
            "command": list(self.command),
            "command_digest": self.command_digest,
            "working_directory": self.working_directory,
            "config_sha256": self.config_sha256,
            "environment_digest": self.environment_digest,
            "started_at_utc": self.started_at_utc,
            "finished_at_utc": self.finished_at_utc,
            "elapsed_seconds": self.elapsed_seconds,
            "state": self.state.value,
            "return_code": self.return_code,
            "stdout_relative_path": self.stdout_relative_path,
            "stdout_sha256": self.stdout_sha256,
            "stderr_relative_path": self.stderr_relative_path,
            "stderr_sha256": self.stderr_sha256,
            "failure_reason": self.failure_reason,
        }
        # Keep historical v1 attempt digests byte-identical when no scientific
        # failure classification exists.  The optional fields are emitted only
        # for positively identified TRAIN2 numerical failures.
        if self.scientific_failure_code is not None:
            payload["scientific_failure_code"] = self.scientific_failure_code
            payload["scientific_failure_evidence_digest"] = (
                self.scientific_failure_evidence_digest
            )
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingRunAttemptRecord":
        if payload.get("schema") != TRAINING_RUN_ATTEMPT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported training-run-attempt schema.")
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]),
            attempt_index=int(payload["attempt_index"]),
            execution_policy_digest=str(payload["execution_policy_digest"]),
            command=tuple(str(v) for v in payload["command"]),
            command_digest=str(payload["command_digest"]),
            working_directory=str(payload["working_directory"]),
            config_sha256=str(payload["config_sha256"]),
            environment_digest=str(payload["environment_digest"]),
            started_at_utc=str(payload["started_at_utc"]),
            finished_at_utc=str(payload["finished_at_utc"]),
            elapsed_seconds=float(payload["elapsed_seconds"]),
            state=TrainingRunState(payload["state"]),
            return_code=None if payload.get("return_code") is None else int(payload["return_code"]),
            stdout_relative_path=str(payload["stdout_relative_path"]),
            stdout_sha256=str(payload["stdout_sha256"]),
            stderr_relative_path=str(payload["stderr_relative_path"]),
            stderr_sha256=str(payload["stderr_sha256"]),
            failure_reason=None if payload.get("failure_reason") is None else str(payload["failure_reason"]),
            scientific_failure_code=(
                None
                if payload.get("scientific_failure_code") is None
                else str(payload["scientific_failure_code"])
            ),
            scientific_failure_evidence_digest=(
                None
                if payload.get("scientific_failure_evidence_digest") is None
                else str(payload["scientific_failure_evidence_digest"])
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Training-run-attempt digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TrainingRunExecutionRecord:
    run_plan_digest: str
    mace_job_artifact_digest: str
    execution_policy_digest: str
    attempts: tuple[TrainingRunAttemptRecord, ...]
    state: TrainingRunState
    successful_attempt_index: int | None
    checkpoint_catalog: CandidateCheckpointCatalog | None

    def __post_init__(self) -> None:
        for name in ("run_plan_digest", "mace_job_artifact_digest", "execution_policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        object.__setattr__(self, "state", TrainingRunState(self.state))
        attempts = tuple(self.attempts)
        if not attempts:
            raise TrainingDataInputError("Training execution record requires at least one attempt.")
        if tuple(v.attempt_index for v in attempts) != tuple(range(1, len(attempts) + 1)):
            raise TrainingDataInputError("Training attempt indices must be contiguous and one-based.")
        if any(v.run_plan_digest != self.run_plan_digest for v in attempts):
            raise TrainingDataInputError("Training attempt lineage mismatch.")
        if any(v.execution_policy_digest != self.execution_policy_digest for v in attempts):
            raise TrainingDataInputError("Training attempt policy lineage mismatch.")
        if self.state is TrainingRunState.SUCCEEDED:
            if self.successful_attempt_index is None or self.checkpoint_catalog is None:
                raise TrainingDataInputError("Successful execution requires attempt and checkpoint catalog.")
            if attempts[self.successful_attempt_index - 1].state is not TrainingRunState.SUCCEEDED:
                raise TrainingDataInputError("Successful attempt index does not reference a successful attempt.")
            if self.checkpoint_catalog.run_plan_digest != self.run_plan_digest:
                raise TrainingDataInputError("Checkpoint catalog lineage mismatch.")
        elif self.successful_attempt_index is not None or self.checkpoint_catalog is not None:
            raise TrainingDataInputError("Unsuccessful execution cannot carry successful checkpoint evidence.")
        object.__setattr__(self, "attempts", attempts)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_RUN_EXECUTION_SCHEMA,
            "run_plan_digest": self.run_plan_digest,
            "mace_job_artifact_digest": self.mace_job_artifact_digest,
            "execution_policy_digest": self.execution_policy_digest,
            "attempts": [v.to_dict() for v in self.attempts],
            "state": self.state.value,
            "successful_attempt_index": self.successful_attempt_index,
            "checkpoint_catalog": None if self.checkpoint_catalog is None else self.checkpoint_catalog.to_dict(),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingRunExecutionRecord":
        if payload.get("schema") != TRAINING_RUN_EXECUTION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported training-run-execution schema.")
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]),
            mace_job_artifact_digest=str(payload["mace_job_artifact_digest"]),
            execution_policy_digest=str(payload["execution_policy_digest"]),
            attempts=tuple(TrainingRunAttemptRecord.from_dict(v) for v in payload["attempts"]),
            state=TrainingRunState(payload["state"]),
            successful_attempt_index=None if payload.get("successful_attempt_index") is None else int(payload["successful_attempt_index"]),
            checkpoint_catalog=None if payload.get("checkpoint_catalog") is None else CandidateCheckpointCatalog.from_dict(payload["checkpoint_catalog"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Training-run-execution digest mismatch.")
        return result


def _write_mlcv_run_diagnostics_if_available(
    *, job_root: Path, run_root: Path, result_dir: Path, job: MaceJobArtifact,
) -> None:
    """Render MLCV-MON1 histories from persisted MACE metrics only.

    The presence of ``target_training_diagnostic.xyz`` distinguishes new
    MLCV-MON1 materializations from historical DATA8 jobs.  Reporting is
    intentionally best-effort for old/mock wrappers that do not emit a MACE
    JSONL metric file; production MACE runs do.
    """

    if not (job_root / "target_training_diagnostic.xyz").is_file():
        return
    metric_paths = tuple(sorted(result_dir.glob("*_train.txt")))
    if not metric_paths:
        return
    diagnostics = run_root / "diagnostics"
    diagnostics.mkdir(parents=True, exist_ok=True)
    merged = diagnostics / "persisted_mace_metrics.jsonl"
    with merged.open("w", encoding="utf-8") as handle:
        for path in metric_paths:
            text = path.read_text(encoding="utf-8", errors="replace")
            handle.write(text)
            if text and not text.endswith("\n"):
                handle.write("\n")
    stop_epoch = None
    stop_reason = None
    replay_foundation_light = None
    state_path = run_root / "adaptive_training_stop.json"
    if state_path.is_file():
        try:
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            stop_epoch = payload.get("stop_epoch")
            stop_reason = payload.get("stop_reason")
            replay_foundation_light = payload.get("foundation_replay_light_force_rmse_ev_per_angstrom")
        except Exception:
            pass
    stop_policy = job.protocol.adaptive_stop_policy
    target_threshold = 0.030 if stop_policy is None else float(stop_policy.maximum_target_force_rmse_ev_per_angstrom)
    replay_budget = target_threshold
    target_fraction = 0.80
    replay_factor = 1.20
    if stop_policy is not None:
        resolved_budget = getattr(stop_policy, "replay_degradation_budget_force_rmse_ev_per_angstrom", None)
        if resolved_budget is None:
            resolved_budget = stop_policy.maximum_replay_force_rmse_ev_per_angstrom
        if resolved_budget is not None:
            replay_budget = float(resolved_budget)
        target_fraction = float(stop_policy.target_stop_fraction)
        replay_factor = float(stop_policy.replay_stop_multiplier)
    write_mlcv_diagnostic_history(
        merged, diagnostics,
        target_head_name=(stop_policy.target_head_name if stop_policy is not None else "target_head"),
        replay_head_name=(stop_policy.replay_head_name if stop_policy is not None else "pt_head"),
        full_target_threshold=target_threshold,
        replay_degradation_budget=replay_budget,
        replay_foundation_light_rmse=(None if replay_foundation_light is None else float(replay_foundation_light)),
        target_success_fraction=target_fraction,
        replay_exhaustion_factor=replay_factor,
        stop_epoch=None if stop_epoch is None else int(stop_epoch),
        stop_reason=None if stop_reason is None else str(stop_reason),
    )


def _classify_train2_numerical_failure(
    checkpoint_directory: Path,
    failure_reason: str | None,
    *,
    environment: Mapping[str, str] | None,
) -> tuple[str, str] | None:
    """Read explicit TRAIN2 numerical-failure evidence, never stderr text.

    A generic non-zero exit is scientific evidence only when the launched
    process carried an authenticated TRAIN2 runtime plan, the runtime persisted
    a content-addressed numerical-failure record bound to that exact plan, and
    the raw checkpoint named by the record is still byte-identical.  A stale or
    foreign sidecar is therefore a lineage/input failure, not scientific
    evidence.
    """

    if failure_reason is None or not failure_reason.startswith("nonzero_exit:"):
        return None
    from .train2_runtime import (
        TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE,
        Train2RuntimePlan,
        load_train2_numerical_failure,
    )

    raw_plan = None if environment is None else environment.get(TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE)
    if raw_plan is None:
        return None
    try:
        runtime_plan = Train2RuntimePlan.from_dict(json.loads(raw_plan))
    except Exception as exc:
        raise TrainingDataInputError(
            "TRAIN2 runtime-plan environment is invalid while classifying a numerical failure."
        ) from exc

    record = load_train2_numerical_failure(checkpoint_directory)
    if record is None:
        return None
    expected_identity = {
        "plan_digest": runtime_plan.content_digest,
        "training_protocol_digest": runtime_plan.training_protocol_digest,
        "optimizer_policy_digest": runtime_plan.optimizer_policy_digest,
        "budget_policy_digest": runtime_plan.budget_policy.policy_digest,
        "lr_policy_digest": runtime_plan.learning_rate_policy.policy_digest,
        "execution_epoch_limit": int(runtime_plan.execution_epoch_limit),
    }
    observed_identity = {
        "plan_digest": record.plan_digest,
        "training_protocol_digest": record.training_protocol_digest,
        "optimizer_policy_digest": record.optimizer_policy_digest,
        "budget_policy_digest": record.budget_policy_digest,
        "lr_policy_digest": record.lr_policy_digest,
        "execution_epoch_limit": int(record.execution_epoch_limit),
    }
    if observed_identity != expected_identity:
        raise TrainingDataInputError(
            "TRAIN2 numerical-failure sidecar belongs to a different runtime plan."
        )
    raw = checkpoint_directory / record.raw_checkpoint_name
    if not raw.is_file() or _sha256_file(raw) != record.raw_checkpoint_sha256:
        raise TrainingDataInputError(
            "TRAIN2 numerical-failure sidecar references a missing or changed raw checkpoint."
        )
    return (record.failure_code, record.content_digest)


def _classify_nonretryable_training_failure(
    stdout_path: Path, stderr_path: Path, failure_reason: str | None
) -> str | None:
    """Return a deterministic failure class when retrying cannot change authority.

    Child-process policy/schema/lineage errors are persisted in the normal
    attempt record but terminate the per-run retry loop immediately. Transient
    GPU/process/I/O exits remain retryable.
    """
    if failure_reason is None or not failure_reason.startswith("nonzero_exit:"):
        return None
    chunks: list[str] = []
    for path in (stderr_path, stdout_path):
        try:
            data = path.read_bytes()[-1024 * 1024 :]
            chunks.append(data.decode("utf-8", errors="replace"))
        except OSError:
            continue
    text = "\n".join(chunks)
    markers = (
        ("MDSTATS_NONRETRYABLE", "policy_or_authority_preflight"),
        ("TrainingDataInputError:", "deterministic_input_or_lineage"),
        ("TrainingDataSerializationError:", "deterministic_schema_or_digest"),
    )
    for marker, classification in markers:
        if marker in text:
            return f"nonretryable:{classification}:{failure_reason}"
    return None


def execute_training_run(
    run_plan: TrainingCampaignRunPlan,
    job: MaceJobArtifact,
    *,
    data8_root: str | Path,
    execution_root: str | Path,
    checkpoint_directory: str | Path,
    policy: TrainingExecutionPolicy = TrainingExecutionPolicy(),
    environment: Mapping[str, str] | None = None,
    wrapper_path: str | Path | None = None,
    prior_record: TrainingRunExecutionRecord | None = None,
    progress_callback: Callable[[int, float, Path, Path], None] | None = None,
    progress_interval_seconds: float = 60.0,
    stop_requested: Callable[[], bool] | None = None,
    allow_successful_continuation: bool = False,
) -> TrainingRunExecutionRecord:
    """Execute one campaign run with bounded retry and immutable attempt logs.

    The function is intentionally synchronous.  A retry adds MACE's
    ``--restart_latest`` flag when the policy allows it.  Existing successful
    evidence is returned only after checkpoint hashes are re-inventoried.
    """

    if progress_interval_seconds <= 0.0:
        raise TrainingDataInputError("Training progress interval must be positive.")
    if run_plan.mace_job_artifact_digest != job.content_digest:
        raise TrainingDataInputError("Campaign run does not match the supplied DATA8 job.")
    if run_plan.execution_wrapper != policy.required_wrapper:
        raise TrainingDataInputError("Campaign execution wrapper does not match execution policy.")
    root = Path(data8_root).resolve()
    run_root = Path(execution_root).resolve()
    checkpoints = Path(checkpoint_directory).resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    checkpoints.mkdir(parents=True, exist_ok=True)
    job_root = _contained(root, job.relative_directory, name="DATA8 job directory")
    config_path = _contained(root, job.config_relative_path, name="MACE config path")
    if config_path.parent != job_root:
        raise TrainingDataInputError("DATA8 MACE config is not located in its declared job directory.")
    if not config_path.is_file() or _sha256_file(config_path) != job.config_sha256:
        raise TrainingDataInputError("DATA8 MACE config is missing or has changed.")

    # DATA8 configurations intentionally use paths relative to the immutable
    # job directory (for example ../../shared/foundation/... and local target
    # extxyz files).  Production outputs, however, belong in the mutable run
    # directory.  Run MACE from the DATA8 job directory so every frozen input
    # path resolves exactly as it did in preflight, while overriding all output
    # directories to the run root.
    model_dir = run_root / "models"
    log_dir = run_root / "logs"
    result_dir = run_root / "results"
    for directory in (model_dir, log_dir, result_dir, checkpoints):
        directory.mkdir(parents=True, exist_ok=True)

    if prior_record is not None:
        if prior_record.run_plan_digest != run_plan.content_digest:
            raise TrainingDataInputError("Prior execution record belongs to a different run.")
        if prior_record.execution_policy_digest != policy.policy_digest:
            raise TrainingDataInputError("Prior execution record uses a different policy.")
        if prior_record.state is TrainingRunState.SUCCEEDED:
            catalog = inventory_mace_checkpoints(run_plan, checkpoints, pattern=policy.checkpoint_glob)
            if catalog.content_digest != prior_record.checkpoint_catalog.content_digest:
                raise TrainingDataInputError("Successful execution checkpoint bytes changed after recording.")
            if not allow_successful_continuation:
                return prior_record

    attempts = [] if prior_record is None else list(prior_record.attempts)

    def consumed_attempts() -> int:
        # User/disk interruptions are continuation points, not scientific or
        # runtime failures.  They remain audited but do not consume the bounded
        # failure-retry budget.
        return sum(
            1 for item in attempts
            if item.state is not TrainingRunState.INTERRUPTED
            and not (allow_successful_continuation and item.state is TrainingRunState.SUCCEEDED)
        )

    if consumed_attempts() >= policy.max_attempts:
        raise TrainingDataInputError("Training execution has exhausted its maximum attempts.")

    executable = str(wrapper_path or shutil.which(policy.required_wrapper) or "")
    if not executable:
        raise TrainingDataInputError(f"Required training wrapper is unavailable: {policy.required_wrapper}.")
    if Path(executable).name != policy.required_wrapper:
        raise TrainingDataInputError("Resolved executable name does not match required wrapper.")

    merged_env = dict(os.environ)
    if environment is not None:
        merged_env.update({str(k): str(v) for k, v in environment.items()})
    # PREC3 binds the wrapper runtime to the immutable DATA8 critical-precision
    # policy.  Missing explicit schedules still carry the historical FP64 policy
    # through the optimizer identity, so no legacy behavior is changed here.
    merged_env[CRITICAL_PRECISION_POLICY_ENVIRONMENT_VARIABLE] = json.dumps(
        job.protocol.optimizer_policy.critical_precision_policy.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    )
    if job.protocol.adaptive_stop_policy is not None:
        merged_env[ADAPTIVE_STOP_POLICY_ENVIRONMENT_VARIABLE] = json.dumps(
            job.protocol.adaptive_stop_policy.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
        )
        merged_env[ADAPTIVE_STOP_STATE_PATH_ENVIRONMENT_VARIABLE] = str(
            (run_root / "adaptive_training_stop.json").resolve()
        )
    else:
        merged_env.pop(ADAPTIVE_STOP_POLICY_ENVIRONMENT_VARIABLE, None)
        merged_env.pop(ADAPTIVE_STOP_STATE_PATH_ENVIRONMENT_VARIABLE, None)
    # Python hash randomization is fixed before the nested MACE interpreter is
    # launched.  MACE itself receives the same run seed through DATA8.
    merged_env.setdefault("PYTHONHASHSEED", str(run_plan.seed))
    env_evidence = {key: merged_env.get(key) for key in policy.environment_allowlist}
    environment_digest = digest({"schema": "mdstats.training-environment.v1", "values": env_evidence})

    while consumed_attempts() < policy.max_attempts:
        attempt_index = len(attempts) + 1
        command = [
            executable,
            "--config", str(config_path),
            "--model_dir", str(model_dir),
            "--checkpoints_dir", str(checkpoints),
            "--log_dir", str(log_dir),
            "--results_dir", str(result_dir),
        ]
        if policy.resume_latest_on_retry:
            # A previous CLI can be interrupted after MACE has written a
            # checkpoint but before mdstats persists the attempt record.  In
            # that case this invocation starts at attempt index one, yet must
            # still resume rather than overwrite hours of completed training.
            checkpoint_paths = tuple(
                item for item in checkpoints.rglob("*.pt") if item.is_file()
            )
            if checkpoint_paths:
                if job.protocol.adaptive_stop_policy is not None:
                    adaptive_state_path = run_root / "adaptive_training_stop.json"
                    if not adaptive_state_path.is_file():
                        raise TrainingDataInputError(
                            "Adaptive training checkpoints exist without adaptive_training_stop.json; "
                            "exact restart is refused rather than losing already-computed monitor evidence."
                        )
                    try:
                        adaptive_state = AdaptiveTrainingStopState.from_dict(
                            json.loads(adaptive_state_path.read_text(encoding="utf-8"))
                        )
                    except Exception as exc:
                        raise TrainingDataInputError(
                            f"Adaptive training restart state is invalid: {type(exc).__name__}: {exc}"
                        ) from exc
                    if adaptive_state.policy_digest != job.protocol.adaptive_stop_policy.policy_digest:
                        raise TrainingDataInputError(
                            "Adaptive training restart state belongs to a different stop policy; exact restart is refused."
                        )
                restart_epoch = None
                resolved_precision = job.protocol.resolved_precision_schedule
                if resolved_precision is not None and len(resolved_precision.stages) > 1:
                    from .precision_runtime import (
                        PrecisionRuntimePlan,
                        latest_resumable_precision_epoch,
                    )
                    runtime_plan = PrecisionRuntimePlan(
                        job_manifest_path=str(job_root / "job_manifest.json"),
                        job_digest=job.content_digest,
                        protocol_digest=job.protocol.content_digest,
                        optimizer_policy_digest=job.protocol.optimizer_policy.policy_digest,
                        schedule=resolved_precision,
                        checkpoints_dir=str(checkpoints),
                    )
                    restart_epoch = latest_resumable_precision_epoch(checkpoints, runtime_plan)
                    if restart_epoch is None:
                        raise TrainingDataInputError(
                            "Staged training checkpoints exist without an exact-continuation precision companion."
                        )
                else:
                    epoch_regex = re.compile(r"(?:epoch[-_]?)(\d+)", re.IGNORECASE)
                    restart_epochs = [
                        int(match.group(1))
                        for item in checkpoint_paths
                        if (match := epoch_regex.search(item.name)) is not None
                    ]
                    if not restart_epochs:
                        raise TrainingDataInputError(
                            "Restart checkpoints exist, but none carry a qualified epoch number."
                        )
                    restart_epoch = max(restart_epochs)
                command.append("--restart_latest")
                merged_env["MDSTATS_MACE_RESTART_EPOCH"] = str(int(restart_epoch))
            else:
                merged_env.pop("MDSTATS_MACE_RESTART_EPOCH", None)
        command_tuple = tuple(command)
        command_digest = digest({"schema": "mdstats.training-command.v1", "argv": list(command_tuple)})
        stdout_path = run_root / f"attempt-{attempt_index:02d}.stdout.log"
        stderr_path = run_root / f"attempt-{attempt_index:02d}.stderr.log"
        started = _utc_now()
        start_clock = time.monotonic()
        last_progress_callback = start_clock
        state = TrainingRunState.FAILED
        return_code: int | None = None
        failure_reason: str | None = None
        active_process_path = run_root / "active_process.json"
        process: subprocess.Popen[bytes] | None = None
        try:
            with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
                process = subprocess.Popen(
                    command_tuple,
                    cwd=job_root,
                    env=merged_env,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    start_new_session=(os.name == "posix"),
                )
                _write_json_atomic(
                    active_process_path,
                    {
                        "schema": "mdstats.training-active-process.v1",
                        "pid": int(process.pid),
                        "run_plan_digest": run_plan.content_digest,
                        "execution_policy_digest": policy.policy_digest,
                        "started_at_utc": started,
                        "working_directory": str(job_root),
                    },
                )
                deadline = (
                    None
                    if policy.timeout_seconds is None
                    else start_clock + policy.timeout_seconds
                )
                while True:
                    now = time.monotonic()
                    if stop_requested is not None and bool(stop_requested()):
                        state = TrainingRunState.INTERRUPTED
                        failure_reason = "interrupted"
                        if os.name == "posix":
                            try:
                                os.killpg(process.pid, signal.SIGTERM)
                            except ProcessLookupError:
                                pass
                        else:  # pragma: no cover - Windows fallback
                            process.terminate()
                        try:
                            process.wait(timeout=policy.terminate_grace_seconds)
                        except subprocess.TimeoutExpired:
                            if os.name == "posix":
                                try:
                                    os.killpg(process.pid, signal.SIGKILL)
                                except ProcessLookupError:
                                    pass
                            else:  # pragma: no cover - Windows fallback
                                process.kill()
                            process.wait()
                        return_code = process.returncode
                        break
                    if deadline is not None and now >= deadline:
                        state = TrainingRunState.TIMED_OUT
                        failure_reason = "timeout"
                        if os.name == "posix":
                            try:
                                os.killpg(process.pid, signal.SIGTERM)
                            except ProcessLookupError:
                                pass
                        else:  # pragma: no cover - Windows fallback
                            process.terminate()
                        try:
                            process.wait(timeout=policy.terminate_grace_seconds)
                        except subprocess.TimeoutExpired:
                            if os.name == "posix":
                                try:
                                    os.killpg(process.pid, signal.SIGKILL)
                                except ProcessLookupError:
                                    pass
                            else:  # pragma: no cover - Windows fallback
                                process.kill()
                            process.wait()
                        return_code = None
                        break
                    wait_seconds = progress_interval_seconds
                    if stop_requested is not None:
                        wait_seconds = min(wait_seconds, _CANCELLATION_POLL_SECONDS)
                    if deadline is not None:
                        wait_seconds = min(wait_seconds, max(0.01, deadline - now))
                    try:
                        return_code = int(process.wait(timeout=wait_seconds))
                        break
                    except subprocess.TimeoutExpired:
                        callback_clock = time.monotonic()
                        if (
                            progress_callback is not None
                            and callback_clock - last_progress_callback
                            >= progress_interval_seconds
                        ):
                            stdout_handle.flush()
                            stderr_handle.flush()
                            progress_callback(
                                attempt_index,
                                callback_clock - start_clock,
                                stdout_path,
                                stderr_path,
                            )
                            last_progress_callback = callback_clock
            if state not in {TrainingRunState.TIMED_OUT, TrainingRunState.INTERRUPTED}:
                if return_code == 0:
                    state = TrainingRunState.SUCCEEDED
                else:
                    failure_reason = f"nonzero_exit:{return_code}"
        except OSError as exc:
            state = TrainingRunState.FAILED
            failure_reason = f"launch_error:{type(exc).__name__}:{exc}"
        finally:
            active_process_path.unlink(missing_ok=True)
        elapsed = time.monotonic() - start_clock
        finished = _utc_now()
        if not stdout_path.exists():
            stdout_path.write_bytes(b"")
        if not stderr_path.exists():
            stderr_path.write_bytes(b"")
        scientific_failure = _classify_train2_numerical_failure(
            checkpoints, failure_reason, environment=merged_env
        )
        scientific_failure_code = None
        scientific_failure_evidence_digest = None
        if scientific_failure is not None:
            scientific_failure_code, scientific_failure_evidence_digest = scientific_failure
            failure_reason = f"scientific_failure:{scientific_failure_code}:{failure_reason}"
        else:
            nonretryable_reason = _classify_nonretryable_training_failure(
                stdout_path, stderr_path, failure_reason
            )
            if nonretryable_reason is not None:
                failure_reason = nonretryable_reason
        attempt = TrainingRunAttemptRecord(
            run_plan_digest=run_plan.content_digest,
            attempt_index=attempt_index,
            execution_policy_digest=policy.policy_digest,
            command=command_tuple,
            command_digest=command_digest,
            working_directory=str(job_root),
            config_sha256=job.config_sha256,
            environment_digest=environment_digest,
            started_at_utc=started,
            finished_at_utc=finished,
            elapsed_seconds=elapsed,
            state=state,
            return_code=return_code,
            stdout_relative_path=stdout_path.name,
            stdout_sha256=_sha256_file(stdout_path),
            stderr_relative_path=stderr_path.name,
            stderr_sha256=_sha256_file(stderr_path),
            failure_reason=failure_reason,
            scientific_failure_code=scientific_failure_code,
            scientific_failure_evidence_digest=scientific_failure_evidence_digest,
        )
        attempts.append(attempt)
        # Keep MLCV diagnostic curves useful for interrupted/failed attempts as
        # well as successful training. The renderer consumes only already
        # persisted MACE metrics and performs no model inference.
        _write_mlcv_run_diagnostics_if_available(
            job_root=job_root, run_root=run_root, result_dir=result_dir, job=job
        )
        if state is not TrainingRunState.SUCCEEDED:
            interim = TrainingRunExecutionRecord(
                run_plan_digest=run_plan.content_digest,
                mace_job_artifact_digest=job.content_digest,
                execution_policy_digest=policy.policy_digest,
                attempts=tuple(attempts),
                state=state,
                successful_attempt_index=None,
                checkpoint_catalog=None,
            )
            _write_json_atomic(run_root / "training_execution.json", interim.to_dict())
            if state is TrainingRunState.INTERRUPTED:
                return interim
            if failure_reason is not None and (
                failure_reason.startswith("nonretryable:")
                or failure_reason.startswith("scientific_failure:")
            ):
                return interim
        if state is TrainingRunState.SUCCEEDED:
            catalog = inventory_mace_checkpoints(run_plan, checkpoints, pattern=policy.checkpoint_glob)
            if policy.require_checkpoint_on_success and not catalog.checkpoints:
                raise TrainingDataInputError("Training command succeeded but produced no candidate checkpoint.")
            record = TrainingRunExecutionRecord(
                run_plan_digest=run_plan.content_digest,
                mace_job_artifact_digest=job.content_digest,
                execution_policy_digest=policy.policy_digest,
                attempts=tuple(attempts),
                state=TrainingRunState.SUCCEEDED,
                successful_attempt_index=attempt_index,
                checkpoint_catalog=catalog,
            )
            _write_json_atomic(run_root / "training_execution.json", record.to_dict())
            return record
        if consumed_attempts() < policy.max_attempts:
            continue

    record = TrainingRunExecutionRecord(
        run_plan_digest=run_plan.content_digest,
        mace_job_artifact_digest=job.content_digest,
        execution_policy_digest=policy.policy_digest,
        attempts=tuple(attempts),
        state=attempts[-1].state,
        successful_attempt_index=None,
        checkpoint_catalog=None,
    )
    _write_json_atomic(run_root / "training_execution.json", record.to_dict())
    return record


@dataclass(frozen=True, slots=True)
class CheckpointEvaluationPolicy:
    target_head_name: str = "target_head"
    replay_head_name: str = "pt_head"
    replay_baseline_head_name: str | None = "pt_head"
    foundation_potential_identity: FoundationPotentialIdentity | None = None
    foundation_inference_identity: FoundationInferenceIdentity | None = None
    energy_key: str = "REF_energy"
    forces_key: str = "REF_forces"
    stress_key: str = "REF_stress"
    focus_atomic_numbers: tuple[int, ...] = (3, 11, 19)
    condition_keys: tuple[str, ...] = ("composition", "temperature", "strain")
    replay_metric: str = "force_rmse"
    replay_baseline_floor: float = 1.0e-6
    combined_energy_weight: float = 1.0
    combined_force_weight: float = 1.0
    combined_stress_weight: float = 1.0
    device: str = "cpu"
    default_dtype: str = "float32"
    batch_size: int = 8
    cache_monitor_datasets: bool = True
    cache_replay_baseline: bool = True
    evaluate_foundation_on_target: bool = False
    acceleration_policy: MaceAccelerationPolicy = field(default_factory=MaceAccelerationPolicy)
    acceleration_realization_digest: str | None = None
    resolved_acceleration_kernel_mode: str | None = None
    # None preserves the historical critical-FP64 evaluation identity.  PREC3
    # passes an explicit profile-bound policy for canonical single/double/refine.
    critical_precision_policy: MaceCriticalPrecisionPolicy | None = None
    # Runtime fields remain readable for historical/API compatibility, but are
    # excluded from the canonical v8 scientific identity. Active campaign
    # execution is owned by InferenceExecutionPlan.
    _legacy_serialized_payload: dict[str, Any] | None = field(
        default=None, init=False, repr=False, compare=False
    )

    @property
    def active_critical_precision_policy(self) -> MaceCriticalPrecisionPolicy:
        return MaceCriticalPrecisionPolicy() if self.critical_precision_policy is None else self.critical_precision_policy

    def __post_init__(self) -> None:
        if not self.target_head_name.strip() or not self.replay_head_name.strip() or not self.energy_key.strip() or not self.forces_key.strip():
            raise TrainingDataInputError("Checkpoint evaluation keys and target head must be non-empty.")
        if self.replay_metric not in {"force_rmse", "combined_loss", "energy_force_stress"}:
            raise TrainingDataInputError("Unsupported replay evaluation metric.")
        if self.replay_baseline_floor <= 0.0:
            raise TrainingDataInputError("Replay baseline floor must be positive.")
        if self.default_dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("Unsupported evaluation dtype.")
        if int(self.batch_size) <= 0:
            raise TrainingDataInputError("Checkpoint evaluation batch_size must be positive.")
        object.__setattr__(self, "batch_size", int(self.batch_size))
        focus = tuple(sorted(set(int(v) for v in self.focus_atomic_numbers)))
        if any(v <= 0 for v in focus):
            raise TrainingDataInputError("Focus atomic numbers must be positive.")
        object.__setattr__(self, "focus_atomic_numbers", focus)
        object.__setattr__(self, "condition_keys", tuple(str(v) for v in self.condition_keys if str(v)))
        for name in ("combined_energy_weight", "combined_force_weight", "combined_stress_weight"):
            if float(getattr(self, name)) < 0.0:
                raise TrainingDataInputError("Combined metric weights must be nonnegative.")
        potential = self.foundation_potential_identity
        inference = self.foundation_inference_identity
        if (potential is None) != (inference is None):
            raise TrainingDataInputError(
                "Checkpoint evaluation foundation potential/inference identities must be both present or both absent."
            )
        if potential is not None:
            if self.replay_baseline_head_name not in (None, ""):
                raise TrainingDataInputError(
                    "Canonical checkpoint evaluation derives the source foundation head from FoundationPotentialIdentity; "
                    "replay_baseline_head_name is legacy-only."
                )
            if inference.foundation_potential_digest != potential.canonical_content_digest:
                raise TrainingDataInputError("Checkpoint evaluation foundation inference/potential identities disagree.")
            if inference.default_dtype != self.default_dtype:
                raise TrainingDataInputError("Checkpoint evaluation foundation inference dtype disagrees with evaluation dtype.")
            if inference.backend != self.acceleration_policy.backend.value:
                raise TrainingDataInputError("Checkpoint evaluation foundation inference backend disagrees with acceleration policy.")
        if (self.acceleration_realization_digest is None) != (self.resolved_acceleration_kernel_mode is None):
            raise TrainingDataInputError(
                "Checkpoint evaluation acceleration realization digest/mode must be both present or both absent."
            )
        if self.acceleration_realization_digest is not None:
            object.__setattr__(self, "acceleration_realization_digest", validate_digest(self.acceleration_realization_digest, name="acceleration_realization_digest"))
            mode = MaceAccelerationKernelMode(str(self.resolved_acceleration_kernel_mode))
            if mode is MaceAccelerationKernelMode.CUEQ_UNRESOLVED:
                raise TrainingDataInputError("Checkpoint evaluation cannot bind unresolved CuEq inference.")
            if mode.backend is not self.acceleration_policy.backend:
                raise TrainingDataInputError("Checkpoint evaluation acceleration realization/backend mismatch.")
            if self.foundation_inference_identity is not None and self.foundation_inference_identity.resolved_kernel_mode != mode.value:
                raise TrainingDataInputError("Checkpoint evaluation foundation inference kernel mode disagrees with frozen acceleration realization.")
            object.__setattr__(self, "resolved_acceleration_kernel_mode", mode.value)

    @property
    def foundation_identity_bound(self) -> bool:
        return self.foundation_potential_identity is not None

    @property
    def source_foundation_head_name(self) -> str | None:
        if self.foundation_potential_identity is not None:
            return self.foundation_potential_identity.foundation_head
        return self.replay_baseline_head_name

    @property
    def foundation_inference_digest(self) -> str | None:
        return None if self.foundation_inference_identity is None else self.foundation_inference_identity.content_digest

    def _payload(self) -> dict[str, Any]:
        explicit_precision = self.critical_precision_policy is not None
        payload = {
            "schema": CHECKPOINT_EVALUATION_POLICY_SCHEMA,
            "target_head_name": self.target_head_name,
            "replay_head_name": self.replay_head_name,
            "replay_baseline_head_name": self.replay_baseline_head_name,
            "energy_key": self.energy_key,
            "forces_key": self.forces_key,
            "stress_key": self.stress_key,
            "focus_atomic_numbers": list(self.focus_atomic_numbers),
            "condition_keys": list(self.condition_keys),
            "replay_metric": self.replay_metric,
            "replay_baseline_floor": self.replay_baseline_floor,
            "combined_energy_weight": self.combined_energy_weight,
            "combined_force_weight": self.combined_force_weight,
            "combined_stress_weight": self.combined_stress_weight,
            "device": self.device,
            "default_dtype": self.default_dtype,
            "acceleration_policy": self.acceleration_policy.to_dict(),
        }
        if self.evaluate_foundation_on_target:
            payload["evaluate_foundation_on_target"] = True
        if explicit_precision:
            payload["critical_precision_policy"] = self.critical_precision_policy.to_dict()
        if self.acceleration_realization_digest is not None:
            payload["acceleration_realization_digest"] = self.acceleration_realization_digest
            payload["resolved_acceleration_kernel_mode"] = self.resolved_acceleration_kernel_mode
        if self.foundation_identity_bound:
            payload.pop("replay_baseline_head_name", None)
            payload["foundation_potential_identity"] = self.foundation_potential_identity.to_dict()
            payload["foundation_inference_identity"] = self.foundation_inference_identity.to_dict()
        return payload

    @property
    def policy_digest(self) -> str:
        payload = self._legacy_serialized_payload
        return digest(self._payload() if payload is None else payload)

    def to_dict(self) -> dict[str, Any]:
        payload = self._legacy_serialized_payload
        return {**(self._payload() if payload is None else payload), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CheckpointEvaluationPolicy":
        if payload.get("schema") not in {
            CHECKPOINT_EVALUATION_POLICY_SCHEMA,
            CHECKPOINT_EVALUATION_POLICY_LEGACY_V7_SCHEMA,
            CHECKPOINT_EVALUATION_POLICY_LEGACY_V6_SCHEMA,
            CHECKPOINT_EVALUATION_POLICY_LEGACY_V5_SCHEMA,
            CHECKPOINT_EVALUATION_POLICY_LEGACY_V4_SCHEMA,
            CHECKPOINT_EVALUATION_POLICY_LEGACY_V3_SCHEMA,
            CHECKPOINT_EVALUATION_POLICY_LEGACY_V2_SCHEMA,
            CHECKPOINT_EVALUATION_POLICY_LEGACY_SCHEMA,
        }:
            raise TrainingDataSerializationError("Unsupported checkpoint-evaluation policy schema.")
        result = cls(
            target_head_name=str(payload["target_head_name"]),
            replay_head_name=str(payload["replay_head_name"]),
            replay_baseline_head_name=(
                None
                if payload.get("schema") in {CHECKPOINT_EVALUATION_POLICY_SCHEMA, CHECKPOINT_EVALUATION_POLICY_LEGACY_V7_SCHEMA}
                and payload.get("foundation_potential_identity") is not None
                else ("pt_head" if "replay_baseline_head_name" not in payload else (None if payload.get("replay_baseline_head_name") in (None, "") else str(payload["replay_baseline_head_name"])))
            ),
            foundation_potential_identity=(None if payload.get("foundation_potential_identity") is None else FoundationPotentialIdentity.from_dict(payload["foundation_potential_identity"])),
            foundation_inference_identity=(None if payload.get("foundation_inference_identity") is None else FoundationInferenceIdentity.from_dict(payload["foundation_inference_identity"])),
            energy_key=str(payload["energy_key"]),
            forces_key=str(payload["forces_key"]),
            stress_key=str(payload["stress_key"]),
            focus_atomic_numbers=tuple(int(v) for v in payload.get("focus_atomic_numbers", ())),
            condition_keys=tuple(str(v) for v in payload.get("condition_keys", ())),
            replay_metric=str(payload["replay_metric"]),
            replay_baseline_floor=float(payload["replay_baseline_floor"]),
            combined_energy_weight=float(payload["combined_energy_weight"]),
            combined_force_weight=float(payload["combined_force_weight"]),
            combined_stress_weight=float(payload["combined_stress_weight"]),
            device=str(payload["device"]),
            default_dtype=str(payload["default_dtype"]),
            batch_size=(
                int(payload.get("batch_size", 8))
                if payload.get("schema") in {CHECKPOINT_EVALUATION_POLICY_SCHEMA, CHECKPOINT_EVALUATION_POLICY_LEGACY_V7_SCHEMA, CHECKPOINT_EVALUATION_POLICY_LEGACY_V6_SCHEMA, CHECKPOINT_EVALUATION_POLICY_LEGACY_V5_SCHEMA, CHECKPOINT_EVALUATION_POLICY_LEGACY_V4_SCHEMA, CHECKPOINT_EVALUATION_POLICY_LEGACY_V3_SCHEMA}
                else 1
            ),
            cache_monitor_datasets=bool(payload.get("cache_monitor_datasets", True)),
            cache_replay_baseline=bool(payload.get("cache_replay_baseline", True)),
            evaluate_foundation_on_target=bool(payload.get("evaluate_foundation_on_target", False)),
            acceleration_policy=(
                MaceAccelerationPolicy()
                if payload.get("acceleration_policy") is None
                else MaceAccelerationPolicy.from_dict(payload["acceleration_policy"])
            ),
            acceleration_realization_digest=(None if payload.get("acceleration_realization_digest") is None else str(payload["acceleration_realization_digest"])),
            resolved_acceleration_kernel_mode=(None if payload.get("resolved_acceleration_kernel_mode") is None else str(payload["resolved_acceleration_kernel_mode"])),
            critical_precision_policy=(
                None
                if payload.get("critical_precision_policy") is None
                else MaceCriticalPrecisionPolicy.from_dict(payload["critical_precision_policy"])
            ),
        )
        expected_digest = result.policy_digest
        if payload.get("schema") == CHECKPOINT_EVALUATION_POLICY_LEGACY_V7_SCHEMA:
            legacy_payload = dict(payload)
            legacy_payload.pop("policy_digest", None)
            expected_digest = digest(legacy_payload)
        elif payload.get("schema") == CHECKPOINT_EVALUATION_POLICY_LEGACY_V6_SCHEMA:
            legacy_payload = dict(payload)
            legacy_payload.pop("policy_digest", None)
            expected_digest = digest(legacy_payload)
        elif payload.get("schema") == CHECKPOINT_EVALUATION_POLICY_LEGACY_V5_SCHEMA:
            expected_digest = digest({
                "schema": CHECKPOINT_EVALUATION_POLICY_LEGACY_V5_SCHEMA,
                "target_head_name": result.target_head_name,
                "replay_head_name": result.replay_head_name,
                "replay_baseline_head_name": result.replay_baseline_head_name,
                "energy_key": result.energy_key, "forces_key": result.forces_key, "stress_key": result.stress_key,
                "focus_atomic_numbers": list(result.focus_atomic_numbers),
                "condition_keys": list(result.condition_keys),
                "replay_metric": result.replay_metric, "replay_baseline_floor": result.replay_baseline_floor,
                "combined_energy_weight": result.combined_energy_weight,
                "combined_force_weight": result.combined_force_weight,
                "combined_stress_weight": result.combined_stress_weight,
                "device": result.device, "default_dtype": result.default_dtype, "batch_size": result.batch_size,
                "cache_monitor_datasets": bool(result.cache_monitor_datasets),
                "cache_replay_baseline": bool(result.cache_replay_baseline),
                "acceleration_policy": result.acceleration_policy.to_dict(),
                **({"evaluate_foundation_on_target": True} if result.evaluate_foundation_on_target else {}),
                "critical_precision_policy": result.critical_precision_policy.to_dict(),
            })
        elif payload.get("schema") == CHECKPOINT_EVALUATION_POLICY_LEGACY_V4_SCHEMA:
            expected_digest = digest(
                {
                    "schema": CHECKPOINT_EVALUATION_POLICY_LEGACY_V4_SCHEMA,
                    "target_head_name": result.target_head_name,
                    "replay_head_name": result.replay_head_name,
                    "replay_baseline_head_name": result.replay_baseline_head_name,
                    "energy_key": result.energy_key,
                    "forces_key": result.forces_key,
                    "stress_key": result.stress_key,
                    "focus_atomic_numbers": list(result.focus_atomic_numbers),
                    "condition_keys": list(result.condition_keys),
                    "replay_metric": result.replay_metric,
                    "replay_baseline_floor": result.replay_baseline_floor,
                    "combined_energy_weight": result.combined_energy_weight,
                    "combined_force_weight": result.combined_force_weight,
                    "combined_stress_weight": result.combined_stress_weight,
                    "device": result.device,
                    "default_dtype": result.default_dtype,
                    "batch_size": result.batch_size,
                    "cache_monitor_datasets": bool(result.cache_monitor_datasets),
                    "cache_replay_baseline": bool(result.cache_replay_baseline),
                    "acceleration_policy": result.acceleration_policy.to_dict(),
                    "evaluate_foundation_on_target": True,
                }
            )
        if payload.get("schema") == CHECKPOINT_EVALUATION_POLICY_LEGACY_V3_SCHEMA:
            expected_digest = digest(
                {
                    "schema": CHECKPOINT_EVALUATION_POLICY_LEGACY_V3_SCHEMA,
                    "target_head_name": result.target_head_name,
                    "replay_head_name": result.replay_head_name,
                    "replay_baseline_head_name": result.replay_baseline_head_name,
                    "energy_key": result.energy_key,
                    "forces_key": result.forces_key,
                    "stress_key": result.stress_key,
                    "focus_atomic_numbers": list(result.focus_atomic_numbers),
                    "condition_keys": list(result.condition_keys),
                    "replay_metric": result.replay_metric,
                    "replay_baseline_floor": result.replay_baseline_floor,
                    "combined_energy_weight": result.combined_energy_weight,
                    "combined_force_weight": result.combined_force_weight,
                    "combined_stress_weight": result.combined_stress_weight,
                    "device": result.device,
                    "default_dtype": result.default_dtype,
                    "batch_size": result.batch_size,
                    "cache_monitor_datasets": bool(result.cache_monitor_datasets),
                    "cache_replay_baseline": bool(result.cache_replay_baseline),
                    "acceleration_policy": result.acceleration_policy.to_dict(),
                }
            )
        elif payload.get("schema") == CHECKPOINT_EVALUATION_POLICY_LEGACY_V2_SCHEMA:
            expected_digest = digest(
                {
                    "schema": CHECKPOINT_EVALUATION_POLICY_LEGACY_V2_SCHEMA,
                    "target_head_name": result.target_head_name,
                    "replay_head_name": result.replay_head_name,
                    "replay_baseline_head_name": result.replay_baseline_head_name,
                    "energy_key": result.energy_key,
                    "forces_key": result.forces_key,
                    "stress_key": result.stress_key,
                    "focus_atomic_numbers": list(result.focus_atomic_numbers),
                    "condition_keys": list(result.condition_keys),
                    "replay_metric": result.replay_metric,
                    "replay_baseline_floor": result.replay_baseline_floor,
                    "combined_energy_weight": result.combined_energy_weight,
                    "combined_force_weight": result.combined_force_weight,
                    "combined_stress_weight": result.combined_stress_weight,
                    "device": result.device,
                    "default_dtype": result.default_dtype,
                    "acceleration_policy": result.acceleration_policy.to_dict(),
                }
            )
        elif payload.get("schema") == CHECKPOINT_EVALUATION_POLICY_LEGACY_SCHEMA:
            expected_digest = digest(
                {
                    "schema": CHECKPOINT_EVALUATION_POLICY_LEGACY_SCHEMA,
                    "target_head_name": result.target_head_name,
                    "replay_head_name": result.replay_head_name,
                    "replay_baseline_head_name": result.replay_baseline_head_name,
                    "energy_key": result.energy_key,
                    "forces_key": result.forces_key,
                    "stress_key": result.stress_key,
                    "focus_atomic_numbers": list(result.focus_atomic_numbers),
                    "condition_keys": list(result.condition_keys),
                    "replay_metric": result.replay_metric,
                    "replay_baseline_floor": result.replay_baseline_floor,
                    "combined_energy_weight": result.combined_energy_weight,
                    "combined_force_weight": result.combined_force_weight,
                    "combined_stress_weight": result.combined_stress_weight,
                    "device": result.device,
                    "default_dtype": result.default_dtype,
                }
            )
        if payload.get("policy_digest") not in (None, expected_digest):
            raise TrainingDataSerializationError("Checkpoint-evaluation policy digest mismatch.")
        if payload.get("schema") != CHECKPOINT_EVALUATION_POLICY_SCHEMA:
            legacy_payload = dict(payload)
            legacy_payload.pop("policy_digest", None)
            object.__setattr__(result, "_legacy_serialized_payload", legacy_payload)
        return result


@dataclass(frozen=True, slots=True)
class InferenceExecutionPlan:
    """Resolved runtime choices kept outside scientific evaluation identity."""

    batch_policy: str = "fixed"
    selected_batch_size: int = 8
    maximum_batch_size: int = 8
    selected_concurrent_model_jobs: int = 1
    cpu_fraction: float = 0.90
    ram_fraction: float = 0.80
    gpu_memory_fraction: float = 0.90
    graph_cache_enabled: bool = True
    monitor_cache_enabled: bool = True
    prediction_cache_enabled: bool = True
    rationale: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        policy = str(self.batch_policy).strip().lower()
        if policy not in {"auto", "fixed"}:
            raise TrainingDataInputError("Inference batch_policy must be 'auto' or 'fixed'.")
        selected = int(self.selected_batch_size)
        maximum = int(self.maximum_batch_size)
        jobs = int(self.selected_concurrent_model_jobs)
        fractions = (
            float(self.cpu_fraction),
            float(self.ram_fraction),
            float(self.gpu_memory_fraction),
        )
        if (
            selected <= 0 or maximum <= 0 or selected > maximum or jobs <= 0
            or any(not math.isfinite(value) or not 0.0 < value <= 1.0 for value in fractions)
        ):
            raise TrainingDataInputError(
                "Inference batch sizes and selected concurrency must be positive and ordered."
            )
        object.__setattr__(self, "batch_policy", policy)
        object.__setattr__(self, "selected_batch_size", selected)
        object.__setattr__(self, "maximum_batch_size", maximum)
        object.__setattr__(self, "selected_concurrent_model_jobs", jobs)
        object.__setattr__(self, "cpu_fraction", fractions[0])
        object.__setattr__(self, "ram_fraction", fractions[1])
        object.__setattr__(self, "gpu_memory_fraction", fractions[2])
        object.__setattr__(
            self, "rationale", tuple(str(value) for value in self.rationale if str(value))
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": INFERENCE_EXECUTION_PLAN_SCHEMA,
            "batch_policy": self.batch_policy,
            "selected_batch_size": self.selected_batch_size,
            "maximum_batch_size": self.maximum_batch_size,
            "selected_concurrent_model_jobs": self.selected_concurrent_model_jobs,
            "cpu_fraction": self.cpu_fraction,
            "ram_fraction": self.ram_fraction,
            "gpu_memory_fraction": self.gpu_memory_fraction,
            "graph_cache_enabled": bool(self.graph_cache_enabled),
            "monitor_cache_enabled": bool(self.monitor_cache_enabled),
            "prediction_cache_enabled": bool(self.prediction_cache_enabled),
            "rationale": list(self.rationale),
        }

    @property
    def execution_digest(self) -> str:
        return digest(self._payload())

    @property
    def content_digest(self) -> str:
        return self.execution_digest

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "execution_digest": self.execution_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "InferenceExecutionPlan":
        schema = payload.get("schema")
        if schema == INFERENCE_EXECUTION_PLAN_LEGACY_SCHEMA:
            # V1 is validated against its exact historical wire semantics in
            # this owning migration path.  Removed runtime hints are deliberately
            # not reintroduced as authorities; the rebuilt v2 plan retains only
            # the still-supported choices and records the migration rationale.
            legacy_payload = {
                "schema": INFERENCE_EXECUTION_PLAN_LEGACY_SCHEMA,
                "batch_policy": str(payload["batch_policy"]),
                "selected_batch_size": int(payload["selected_batch_size"]),
                "maximum_batch_size": int(payload["maximum_batch_size"]),
                "concurrent_model_jobs": int(payload.get("concurrent_model_jobs", 1)),
                "use_cuda_streams": bool(payload.get("use_cuda_streams", False)),
                "host_ram_budget_bytes": (
                    None
                    if payload.get("host_ram_budget_bytes") is None
                    else int(payload["host_ram_budget_bytes"])
                ),
                "graph_cache_enabled": bool(payload.get("graph_cache_enabled", True)),
                "monitor_cache_enabled": bool(payload.get("monitor_cache_enabled", True)),
                "compatible_profile_digest": (
                    None
                    if payload.get("compatible_profile_digest") is None
                    else str(payload["compatible_profile_digest"])
                ),
                "rationale": [str(value) for value in payload.get("rationale", ())],
            }
            if payload.get("execution_digest") != digest(legacy_payload):
                raise TrainingDataSerializationError(
                    "Inference-execution plan legacy v1 digest mismatch."
                )
            return cls(
                batch_policy=legacy_payload["batch_policy"],
                selected_batch_size=legacy_payload["selected_batch_size"],
                maximum_batch_size=legacy_payload["maximum_batch_size"],
                selected_concurrent_model_jobs=legacy_payload["concurrent_model_jobs"],
                graph_cache_enabled=legacy_payload["graph_cache_enabled"],
                monitor_cache_enabled=legacy_payload["monitor_cache_enabled"],
                prediction_cache_enabled=True,
                rationale=tuple(legacy_payload["rationale"])
                + ("rebuilt_from_inference_execution_plan_v1",),
            )
        if schema != INFERENCE_EXECUTION_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported inference-execution plan schema.")
        result = cls(
            batch_policy=str(payload["batch_policy"]),
            selected_batch_size=int(payload["selected_batch_size"]),
            maximum_batch_size=int(payload["maximum_batch_size"]),
            selected_concurrent_model_jobs=int(
                payload.get("selected_concurrent_model_jobs", 1)
            ),
            cpu_fraction=float(payload.get("cpu_fraction", 0.90)),
            ram_fraction=float(payload.get("ram_fraction", 0.80)),
            gpu_memory_fraction=float(payload.get("gpu_memory_fraction", 0.90)),
            graph_cache_enabled=bool(payload.get("graph_cache_enabled", True)),
            monitor_cache_enabled=bool(payload.get("monitor_cache_enabled", True)),
            prediction_cache_enabled=bool(payload.get("prediction_cache_enabled", True)),
            rationale=tuple(str(value) for value in payload.get("rationale", ())),
        )
        if payload.get("execution_digest") != result.execution_digest:
            raise TrainingDataSerializationError("Inference-execution plan digest mismatch.")
        return result


def _legacy_inference_execution_plan(
    policy: CheckpointEvaluationPolicy,
) -> InferenceExecutionPlan:
    """Isolate compatibility for callers predating explicit execution plans."""

    batch_size = max(1, int(policy.batch_size))
    return InferenceExecutionPlan(
        batch_policy="fixed",
        selected_batch_size=batch_size,
        maximum_batch_size=batch_size,
        graph_cache_enabled=True,
        monitor_cache_enabled=bool(policy.cache_monitor_datasets),
        prediction_cache_enabled=bool(policy.cache_replay_baseline),
        rationale=("legacy_checkpoint_evaluation_api",),
    )


def _path_cache_identity(path: Path, expected_sha256: str) -> tuple[str, int, int, int, str]:
    resolved = path.resolve()
    stat = resolved.stat()
    return (
        str(resolved),
        int(stat.st_size),
        int(stat.st_mtime_ns),
        int(getattr(stat, "st_ino", 0)),
        validate_digest(expected_sha256, name="monitor_sha256"),
    )


_MONITOR_ATOMS_CACHE: "OrderedDict[tuple[str, int, int, int, str], tuple[tuple[Any, ...], int]]" = OrderedDict()
_MONITOR_ATOMS_CACHE_BYTES = 0
_MONITOR_ATOMS_CACHE_LOCK = RLock()
_MONITOR_ATOMS_CACHE_MAX_BYTES = max(
    0, int(os.environ.get("MDSTATS_MLFF_MONITOR_CACHE_BYTES", str(512 * 1024**2)))
)


def _atoms_tuple_resident_bytes(values: Sequence[Any]) -> int:
    """Return a conservative byte estimate for a parsed monitor dataset."""

    total = 0
    for atoms in values:
        seen: set[int] = set()
        for array in getattr(atoms, "arrays", {}).values():
            candidate = np.asarray(array)
            identity = id(candidate)
            if identity not in seen:
                total += int(candidate.nbytes)
                seen.add(identity)
        cell = np.asarray(getattr(atoms, "cell", ()), dtype=np.float64)
        total += int(cell.nbytes)
        for value in getattr(atoms, "info", {}).values():
            if isinstance(value, np.ndarray):
                total += int(value.nbytes)
            elif isinstance(value, (str, bytes)):
                total += len(value)
            else:
                total += 64
        total += 512
    return max(total, 1)


def _monitor_atoms_cache_clear() -> None:
    global _MONITOR_ATOMS_CACHE_BYTES
    with _MONITOR_ATOMS_CACHE_LOCK:
        _MONITOR_ATOMS_CACHE.clear()
        _MONITOR_ATOMS_CACHE_BYTES = 0


def _as_atoms_tuple_cached(
    identity: tuple[str, int, int, int, str],
) -> tuple[Any, ...]:
    """Load an extxyz monitor through a byte-budgeted authenticated LRU."""

    global _MONITOR_ATOMS_CACHE_BYTES
    with _MONITOR_ATOMS_CACHE_LOCK:
        cached = _MONITOR_ATOMS_CACHE.get(identity)
        if cached is not None:
            _MONITOR_ATOMS_CACHE.move_to_end(identity)
            return cached[0]
        # Keep the first authenticated parse inside the lock. Parallel checkpoint
        # evaluations otherwise decode the same multi-GB monitor simultaneously,
        # defeating the 80% RAM envelope before the LRU can be populated.
        from ase.io import read

        path = Path(identity[0])
        result = read(path, index=":", format="extxyz")
        values = tuple(result if isinstance(result, list) else [result])
        resident_bytes = _atoms_tuple_resident_bytes(values)
        # Monitor atoms remain calculator-free and are copied by prediction providers.
        if (
            _MONITOR_ATOMS_CACHE_MAX_BYTES <= 0
            or resident_bytes > _MONITOR_ATOMS_CACHE_MAX_BYTES
        ):
            return values
        previous = _MONITOR_ATOMS_CACHE.pop(identity, None)
        if previous is not None:
            _MONITOR_ATOMS_CACHE_BYTES -= previous[1]
        _MONITOR_ATOMS_CACHE[identity] = (values, resident_bytes)
        _MONITOR_ATOMS_CACHE_BYTES += resident_bytes
        while (
            _MONITOR_ATOMS_CACHE
            and _MONITOR_ATOMS_CACHE_BYTES > _MONITOR_ATOMS_CACHE_MAX_BYTES
        ):
            _, (_, removed_bytes) = _MONITOR_ATOMS_CACHE.popitem(last=False)
            _MONITOR_ATOMS_CACHE_BYTES -= removed_bytes
    return values


# Preserve the cache-control surface used by tests and long-lived applications.
_as_atoms_tuple_cached.cache_clear = _monitor_atoms_cache_clear  # type: ignore[attr-defined]


def _as_atoms_list(
    path: Path,
    *,
    expected_sha256: str | None = None,
    use_cache: bool = True,
) -> tuple[Any, ...]:
    from ase.io import read

    if use_cache and expected_sha256 is not None:
        return _as_atoms_tuple_cached(_path_cache_identity(path, expected_sha256))
    result = read(path, index=":", format="extxyz")
    return tuple(result if isinstance(result, list) else [result])


def _is_memory_exhaustion(exc: BaseException) -> bool:
    message = str(exc).lower()
    return any(
        marker in message
        for marker in (
            "out of memory",
            "cannot allocate memory",
            "cuda error: memory allocation",
            "cublas_status_alloc_failed",
        )
    )



@mace_runtime_warning_handled("checkpoint prediction")
def _predict_model_on_atoms(
    model_path: Path,
    atoms_list: Sequence[Any],
    *,
    head: str | None,
    policy: CheckpointEvaluationPolicy,
    execution_plan: InferenceExecutionPlan | None = None,
    provider: Any | None = None,
    geometry_identities: Sequence[str] | None = None,
    graph_cache_directory: str | Path | None = None,
) -> tuple[Any, ...]:
    """Run only model inference; reference labels and metric policy are irrelevant."""

    from .inference_parallel import mark_inference_workload_started

    mark_inference_workload_started()
    if not atoms_list:
        raise TrainingDataInputError("Evaluation dataset is empty.")
    if provider is None:
        # The critical-FP64 patch belongs to MACE calculator construction.  A
        # caller-supplied provider is already constructed/qualified (the staged
        # campaign path uses MaceCalculatorProvider.from_model_path, which installs
        # the patch itself).  Avoid re-importing/re-patching MACE for every batch
        # when a private provider is intentionally being reused.
        activate_mace_critical_precision_policy(policy.active_critical_precision_policy)
        from .model_features import MaceCalculatorProvider

        calculator_kwargs = (
            dict(policy.acceleration_policy.calculator_kwargs())
            if policy.resolved_acceleration_kernel_mode is None
            else dict(
                MaceAccelerationKernelMode(
                    policy.resolved_acceleration_kernel_mode
                ).calculator_kwargs()
            )
        )
        if head is not None:
            calculator_kwargs["head"] = head
        provider = MaceCalculatorProvider.from_model_path(
            model_path,
            device=policy.device,
            default_dtype=policy.default_dtype,
            critical_precision_policy=policy.active_critical_precision_policy,
            **calculator_kwargs,
        )
    else:
        provider.set_head(head)
    from .model_features import (
        MACE_ADAPTER_VERSION,
        MaceCalculatorProvider,
        StaticInferenceRuntimeAuthority,
        StaticInferenceRuntimeProfile,
        StaticMaceInferenceExecutor,
    )

    active_execution = (
        _legacy_inference_execution_plan(policy)
        if execution_plan is None
        else execution_plan
    )
    runtime_authority = None
    runtime_profile_path = None
    provider_factory = None
    if active_execution.batch_policy == "auto":
        from .resources import detect_system_resources

        try:
            resources = detect_system_resources(
                cpu_fraction=active_execution.cpu_fraction,
                ram_fraction=active_execution.ram_fraction,
                gpu_memory_fraction=active_execution.gpu_memory_fraction,
                device=policy.device,
            )
        except ValueError as exc:
            raise TrainingDataInputError(str(exc)) from exc
        if resources.ram_budget_bytes is None:
            raise TrainingDataInputError(
                "Automatic static inference requires live host-RAM telemetry."
            )
        uses_cuda = str(policy.device).startswith("cuda")
        if uses_cuda and resources.gpu.budget_bytes is None:
            raise TrainingDataInputError(
                "Automatic static inference requires live VRAM telemetry."
            )
        provider_identity = getattr(provider, "checkpoint_identity", None)
        model_identity = getattr(provider_identity, "content_digest", None)
        if model_identity is None:
            model_identity = _sha256_file(model_path)
        workload_shape_digest = digest(
            {
                "atom_counts": [int(len(value)) for value in atoms_list],
                "configuration_count": len(atoms_list),
            }
        )
        compatibility = StaticInferenceRuntimeAuthority.compatibility_key(
            {
                "adapter_version": MACE_ADAPTER_VERSION,
                "model_identity": model_identity,
                "device": str(policy.device),
                "default_dtype": str(policy.default_dtype),
                "head": None if head is None else str(head),
                "acceleration_policy_digest": getattr(
                    policy.acceleration_policy, "policy_digest", None
                ),
                "resolved_acceleration_kernel_mode": policy.resolved_acceleration_kernel_mode,
                "critical_precision_policy_digest": getattr(
                    policy.active_critical_precision_policy, "policy_digest", None
                ),
                "graph_cache_enabled": bool(
                    active_execution.graph_cache_enabled
                    and graph_cache_directory is not None
                ),
                "cpu_threads_available": resources.cpu_threads_available,
                "gpu_name": resources.gpu.device_name,
                "gpu_total_bytes": resources.gpu.total_bytes,
                "workload_shape_digest": workload_shape_digest,
            }
        )
        compatible_profile = None
        if graph_cache_directory is not None:
            runtime_profile_path = (
                Path(graph_cache_directory).resolve().parent
                / "static-inference-runtime-profiles"
                / f"{compatibility}.json"
            )
            compatible_profile = StaticInferenceRuntimeProfile.load_compatible(
                runtime_profile_path, compatibility_digest=compatibility
            )
        runtime_authority = StaticInferenceRuntimeAuthority(
            compatibility_digest=compatibility,
            maximum_batch_size=min(
                int(active_execution.maximum_batch_size), len(atoms_list)
            ),
            maximum_concurrent_model_jobs=int(
                active_execution.selected_concurrent_model_jobs
            ),
            live_ram_budget_bytes=int(resources.ram_budget_bytes),
            live_vram_budget_bytes=(
                resources.gpu.budget_bytes if uses_cuda else None
            ),
            cold_start_batch_size=int(active_execution.selected_batch_size),
            compatible_profile=compatible_profile,
        )
        private_calculator_kwargs = dict(
            policy.acceleration_policy.calculator_kwargs()
            if policy.resolved_acceleration_kernel_mode is None
            else MaceAccelerationKernelMode(
                policy.resolved_acceleration_kernel_mode
            ).calculator_kwargs()
        )
        if head is not None:
            private_calculator_kwargs["head"] = head

        def provider_factory() -> Any:
            return MaceCalculatorProvider.from_model_path(
                model_path,
                device=policy.device,
                default_dtype=policy.default_dtype,
                critical_precision_policy=policy.active_critical_precision_policy,
                **private_calculator_kwargs,
            )
    executor = StaticMaceInferenceExecutor(
        provider,
        batch_size=max(
            1,
            min(
                (
                    active_execution.maximum_batch_size
                    if runtime_authority is not None
                    else active_execution.selected_batch_size
                ),
                len(atoms_list),
            ),
        ),
        graph_cache_directory=(
            graph_cache_directory if active_execution.graph_cache_enabled else None
        ),
        runtime_authority=runtime_authority,
        concurrent_model_jobs=active_execution.selected_concurrent_model_jobs,
        device=policy.device,
        provider_factory=provider_factory,
    )
    result = executor.predict(atoms_list, geometry_identities=geometry_identities)
    if runtime_authority is not None and runtime_profile_path is not None:
        try:
            runtime_authority.profile().write_atomic(runtime_profile_path)
        except TrainingDataInputError:
            # The run remains valid when conservative live telemetry declines to
            # persist a reusable point; the next invocation calibrates again.
            pass
    return result


def _predict_model_on_monitor(
    model_path: Path,
    atoms_list: Sequence[Any],
    *,
    head: str | None,
    policy: CheckpointEvaluationPolicy,
    execution_plan: InferenceExecutionPlan | None = None,
    provider: Any | None = None,
    geometry_identities: Sequence[str] = (),
    graph_cache_directory: str | Path | None,
) -> tuple[Any, ...]:
    """Invoke the OPT-EVAL3 prediction surface with legacy test/provider tolerance."""

    try:
        return _predict_model_on_atoms(
            model_path,
            atoms_list,
            head=head,
            policy=policy,
            execution_plan=execution_plan,
            provider=provider,
            geometry_identities=geometry_identities,
            graph_cache_directory=graph_cache_directory,
        )
    except TypeError as exc:
        message = str(exc)
        if "unexpected keyword" not in message and "geometry_identities" not in message:
            raise
        return _predict_model_on_atoms(
            model_path, atoms_list, head=head, policy=policy, provider=provider
        )


def _metrics_from_predictions(
    atoms_list: Sequence[Any],
    predictions: Sequence[Any],
    *,
    policy: CheckpointEvaluationPolicy,
    view: Any | None = None,
) -> dict[str, Any]:
    """Reduce immutable predictions through the OPT-EVAL3 vectorized view.

    Callers that do not have an authenticated monitor identity may omit ``view``;
    the same immutable representation is then built ephemerally. Campaign
    evaluation supplies a cached view so repeated checkpoints never re-extract
    labels/conditions from ASE objects.
    """

    from .evaluation_views import (
        build_evaluation_dataset_view,
        metrics_from_prediction_view,
    )

    active_view = view
    if active_view is None:
        active_view = build_evaluation_dataset_view(
            atoms_list,
            energy_key=policy.energy_key,
            forces_key=policy.forces_key,
            stress_key=policy.stress_key,
            focus_atomic_numbers=policy.focus_atomic_numbers,
            condition_keys=policy.condition_keys,
        )
    return metrics_from_prediction_view(
        active_view,
        predictions,
        combined_energy_weight=policy.combined_energy_weight,
        combined_force_weight=policy.combined_force_weight,
        combined_stress_weight=policy.combined_stress_weight,
    )


@mace_runtime_warning_handled("checkpoint evaluation")
def _evaluate_model_on_atoms(
    model_path: Path,
    atoms_list: Sequence[Any],
    *,
    head: str | None,
    policy: CheckpointEvaluationPolicy,
    provider: Any | None = None,
) -> dict[str, Any]:
    predictions = _predict_model_on_atoms(
        model_path,
        atoms_list,
        head=head,
        policy=policy,
        provider=provider,
    )
    return _metrics_from_predictions(atoms_list, predictions, policy=policy)


# Durable prediction artifacts are the cache authority. The lock only provides
# single-flight foundation prediction/import publication within this process.
_BASELINE_METRIC_CACHE_LOCK = RLock()


def _evaluation_prediction_key(
    *,
    model_sha256: str,
    head: str | None,
    geometry_identities: Sequence[str],
    policy: CheckpointEvaluationPolicy,
    foundation_inference_digest: str | None = None,
) -> Any:
    from .evaluation_predictions import prediction_key

    return prediction_key(
        model_sha256=model_sha256,
        head_name=head,
        geometry_identities=geometry_identities,
        default_dtype=policy.default_dtype,
        device=policy.device,
        acceleration_policy_digest=policy.acceleration_policy.policy_digest,
        foundation_inference_digest=foundation_inference_digest,
    )


def _cached_evaluation_predictions(
    cache_directory: str | Path | None,
    *,
    model_sha256: str,
    head: str | None,
    geometry_identities: Sequence[str],
    policy: CheckpointEvaluationPolicy,
    foundation_baseline: bool = False,
) -> tuple[Any | None, tuple[Any, ...] | None]:
    if cache_directory is None:
        return None, None
    from .evaluation_predictions import (
        load_evaluation_prediction_artifact,
        load_evaluation_prediction_coverage,
    )

    key = _evaluation_prediction_key(
        model_sha256=model_sha256,
        head=head,
        geometry_identities=geometry_identities,
        policy=policy,
        foundation_inference_digest=(policy.foundation_inference_digest if foundation_baseline else None),
    )
    loaded = load_evaluation_prediction_artifact(cache_directory, key)
    if loaded is not None:
        artifact, predictions = loaded
        return artifact, predictions
    predictions = load_evaluation_prediction_coverage(
        cache_directory,
        model_sha256=model_sha256,
        head_name=head,
        geometry_identities=geometry_identities,
        default_dtype=policy.default_dtype,
        device=policy.device,
        acceleration_policy_digest=policy.acceleration_policy.policy_digest,
        foundation_inference_digest=(policy.foundation_inference_digest if foundation_baseline else None),
    )
    if predictions is None:
        return None, None
    # A composed nested-round coverage set does not correspond to one preexisting
    # artifact. Finalization will publish a cumulative artifact if useful.
    return None, predictions


def _persist_evaluation_predictions(
    cache_directory: str | Path | None,
    *,
    model_sha256: str,
    head: str | None,
    geometry_identities: Sequence[str],
    policy: CheckpointEvaluationPolicy,
    predictions: Sequence[Any],
    source_kind: str,
    source_digest: str | None = None,
    foundation_baseline: bool = False,
) -> Any | None:
    if cache_directory is None:
        return None
    from .evaluation_predictions import write_evaluation_prediction_artifact

    key = _evaluation_prediction_key(
        model_sha256=model_sha256,
        head=head,
        geometry_identities=geometry_identities,
        policy=policy,
        foundation_inference_digest=(policy.foundation_inference_digest if foundation_baseline else None),
    )
    return write_evaluation_prediction_artifact(
        cache_directory,
        key,
        predictions,
        source_kind=source_kind,
        source_digest=source_digest,
        geometry_identities=geometry_identities,
    )


def checkpoint_prediction_cache_complete(
    cache_directory: str | Path,
    *,
    checkpoint_sha256: str,
    target_geometry_identities: Sequence[str],
    policy: CheckpointEvaluationPolicy,
    replay_geometry_identities: Sequence[str] | None = None,
) -> bool:
    """Return whether all candidate predictions needed by one evaluation are durable.

    This check is label-independent.  It allows a stale metric record to be
    rebuilt after a reference-label or metric-policy change without requiring
    the raw checkpoint or reconstructing a deployable MACE model.
    """

    from .evaluation_predictions import evaluation_prediction_coverage_has

    if not evaluation_prediction_coverage_has(
        cache_directory,
        model_sha256=checkpoint_sha256,
        head_name=policy.target_head_name,
        geometry_identities=target_geometry_identities,
        default_dtype=policy.default_dtype,
        device=policy.device,
        acceleration_policy_digest=policy.acceleration_policy.policy_digest,
    ):
        return False
    if replay_geometry_identities is None:
        return True
    return evaluation_prediction_coverage_has(
        cache_directory,
        model_sha256=checkpoint_sha256,
        head_name=policy.replay_head_name,
        geometry_identities=replay_geometry_identities,
        default_dtype=policy.default_dtype,
        device=policy.device,
        acceleration_policy_digest=policy.acceleration_policy.policy_digest,
    )


def _data6_foundation_predictions(
    prediction_manifest: Any | None,
    prediction_root: str | Path | None,
    frame_uids: Sequence[str],
    *,
    baseline_sha256: str,
    head: str | None,
    policy: CheckpointEvaluationPolicy,
) -> tuple[tuple[Any, ...], str] | None:
    """Load authenticated DATA6 foundation predictions under exact source identity."""

    if prediction_manifest is None or prediction_root is None:
        return None
    checkpoint = prediction_manifest.checkpoint_identity
    metadata = dict(checkpoint.metadata)
    if policy.foundation_identity_bound:
        potential = policy.foundation_potential_identity
        inference = policy.foundation_inference_identity
        assert potential is not None and inference is not None
        if not getattr(checkpoint, "foundation_bound", False):
            return None
        if (
            baseline_sha256 != potential.sha256
            or checkpoint.checkpoint_sha256 != potential.sha256
            or str(getattr(checkpoint, "foundation_head", "")) != potential.foundation_head
            or getattr(checkpoint, "foundation_potential_digest", None) != potential.canonical_content_digest
            or getattr(checkpoint, "foundation_inference_digest", None) != inference.content_digest
            or head != potential.foundation_head
        ):
            return None
    else:
        if getattr(checkpoint, "foundation_bound", False):
            # A canonical DATA6 artifact must never be down-cast into a legacy
            # head-blind baseline authority.
            return None
        if head is not None or checkpoint.checkpoint_sha256 != baseline_sha256:
            return None
    if (
        checkpoint.default_dtype != policy.default_dtype
        or checkpoint.device != policy.device
        or metadata.get("acceleration_policy_digest") != policy.acceleration_policy.policy_digest
    ):
        return None
    try:
        from .production_model_sweep import read_atomic_model_prediction

        values = tuple(
            read_atomic_model_prediction(prediction_manifest, prediction_root, frame_uid)
            for frame_uid in frame_uids
        )
    except (KeyError, TrainingDataSerializationError, TrainingDataInputError):
        return None
    source_digest = digest(
        {
            "schema": "mdstats.evaluation-foundation-data6-source.v2" if policy.foundation_identity_bound else "mdstats.evaluation-foundation-data6-source.v1",
            "prediction_manifest_digest": prediction_manifest.content_digest,
            "frame_uids": list(frame_uids),
            **({"foundation_inference_digest": policy.foundation_inference_digest} if policy.foundation_identity_bound else {}),
        }
    )
    return values, source_digest


def _pseudolabel_foundation_predictions(
    training_replay_monitor_path: str | Path | None,
    training_replay_monitor_artifact: ReplayFileArtifact | None,
    evaluation_replay_monitor_artifact: ReplayFileArtifact | None,
    *,
    baseline_sha256: str,
    head: str | None,
    policy: CheckpointEvaluationPolicy,
    use_dataset_cache: bool | None = None,
    configuration_indices: Sequence[int] | None = None,
) -> tuple[tuple[Any, ...], str] | None:
    """Treat authenticated foundation pseudolabels as persisted foundation predictions."""

    if (
        training_replay_monitor_path is None
        or training_replay_monitor_artifact is None
        or evaluation_replay_monitor_artifact is None
        or training_replay_monitor_artifact.label_mode is not ReplayLabelMode.FOUNDATION_PSEUDOLABEL
        or training_replay_monitor_artifact.configuration_count != evaluation_replay_monitor_artifact.configuration_count
        or training_replay_monitor_artifact.geometry_identities != evaluation_replay_monitor_artifact.geometry_identities
    ):
        return None
    if policy.foundation_identity_bound:
        potential = policy.foundation_potential_identity
        inference = policy.foundation_inference_identity
        assert potential is not None and inference is not None
        if (
            baseline_sha256 != potential.sha256
            or head != potential.foundation_head
            or not training_replay_monitor_artifact.is_head_qualified_foundation_lineage
            or training_replay_monitor_artifact.foundation_label_generator_identity_digest != inference.content_digest
        ):
            return None
    else:
        if (
            head is not None
            or training_replay_monitor_artifact.is_head_qualified_foundation_lineage
            or training_replay_monitor_artifact.foundation_checkpoint_digest != baseline_sha256
        ):
            return None
    path = Path(training_replay_monitor_path).resolve()
    if not path.is_file() or _sha256_file(path) != training_replay_monitor_artifact.sha256:
        return None
    atoms_list = _as_atoms_list(
        path,
        expected_sha256=training_replay_monitor_artifact.sha256,
        use_cache=(
            policy.cache_monitor_datasets
            if use_dataset_cache is None
            else bool(use_dataset_cache)
        ),
    )
    from ase.stress import voigt_6_to_full_3x3_stress
    from .model_features import AtomicModelPrediction

    selected_indices = (
        tuple(range(len(atoms_list)))
        if configuration_indices is None
        else tuple(int(value) for value in configuration_indices)
    )
    if any(value < 0 or value >= len(atoms_list) for value in selected_indices):
        return None
    predictions: list[Any] = []
    for index in selected_indices:
        atoms = atoms_list[index]
        if (
            training_replay_monitor_artifact.energy_key not in atoms.info
            or training_replay_monitor_artifact.forces_key not in atoms.arrays
        ):
            return None
        stress_value = None
        if training_replay_monitor_artifact.stress_key in atoms.info:
            stress = np.asarray(
                atoms.info[training_replay_monitor_artifact.stress_key], dtype=np.float64
            ).reshape(-1)
            if stress.size == 6:
                stress_value = np.asarray(voigt_6_to_full_3x3_stress(stress), dtype=np.float64)
            elif stress.size == 9:
                stress_value = stress.reshape(3, 3)
            else:
                return None
        predictions.append(
            AtomicModelPrediction(
                energy_ev=float(atoms.info[training_replay_monitor_artifact.energy_key]),
                forces_ev_per_angstrom=np.asarray(
                    atoms.arrays[training_replay_monitor_artifact.forces_key]
                ).copy(),
                stress_ev_per_angstrom3=stress_value,
            )
        )
    return tuple(predictions), training_replay_monitor_artifact.content_digest

def _replay_scalar(metrics: Mapping[str, Any], policy: CheckpointEvaluationPolicy) -> float:
    if policy.replay_metric == "force_rmse":
        return float(metrics["force_component_rmse_ev_per_angstrom"])
    if policy.replay_metric == "combined_loss":
        return float(metrics["combined_loss"])
    energy = float(metrics["energy_mae_ev_per_atom"])
    force = float(metrics["force_component_rmse_ev_per_angstrom"])
    stress = 0.0 if metrics["stress_rmse_ev_per_angstrom3"] is None else float(metrics["stress_rmse_ev_per_angstrom3"])
    return math.sqrt(energy * energy + force * force + stress * stress)


@dataclass(frozen=True, slots=True)
class ModelDatasetMetricRecord:
    """Complete model accuracy on one immutable labelled dataset."""

    configuration_count: int
    energy_mae_ev_per_atom: float
    force_component_rmse_ev_per_angstrom: float
    focus_force_rmse_ev_per_angstrom: tuple[tuple[str, float], ...] = ()
    stress_rmse_ev_per_angstrom3: float | None = None
    worst_condition_force_rmse_ev_per_angstrom: float = 0.0
    condition_force_rmse_ev_per_angstrom: tuple[tuple[str, float], ...] = ()
    combined_loss: float = 0.0

    def __post_init__(self) -> None:
        if int(self.configuration_count) <= 0:
            raise TrainingDataInputError("Model-dataset metric count must be positive.")
        object.__setattr__(self, "configuration_count", int(self.configuration_count))
        for name in (
            "energy_mae_ev_per_atom",
            "force_component_rmse_ev_per_angstrom",
            "worst_condition_force_rmse_ev_per_angstrom",
            "combined_loss",
        ):
            object.__setattr__(
                self, name, _finite_nonnegative(getattr(self, name), name=name)
            )
        if self.stress_rmse_ev_per_angstrom3 is not None:
            object.__setattr__(
                self,
                "stress_rmse_ev_per_angstrom3",
                _finite_nonnegative(
                    self.stress_rmse_ev_per_angstrom3,
                    name="stress_rmse_ev_per_angstrom3",
                ),
            )
        object.__setattr__(
            self,
            "focus_force_rmse_ev_per_angstrom",
            tuple(sorted((str(k), _finite_nonnegative(v, name=f"focus_force_rmse[{k}]") or 0.0) for k, v in self.focus_force_rmse_ev_per_angstrom)),
        )
        object.__setattr__(
            self,
            "condition_force_rmse_ev_per_angstrom",
            tuple(sorted((str(k), _finite_nonnegative(v, name=f"condition_force_rmse[{k}]") or 0.0) for k, v in self.condition_force_rmse_ev_per_angstrom)),
        )

    @classmethod
    def from_metrics(cls, metrics: Mapping[str, Any]) -> "ModelDatasetMetricRecord":
        return cls(
            configuration_count=int(metrics["configuration_count"]),
            energy_mae_ev_per_atom=float(metrics["energy_mae_ev_per_atom"]),
            force_component_rmse_ev_per_angstrom=float(metrics["force_component_rmse_ev_per_angstrom"]),
            focus_force_rmse_ev_per_angstrom=tuple((str(k), float(v)) for k, v in metrics.get("focus_force_rmse_ev_per_angstrom", ())),
            stress_rmse_ev_per_angstrom3=(None if metrics.get("stress_rmse_ev_per_angstrom3") is None else float(metrics["stress_rmse_ev_per_angstrom3"])),
            worst_condition_force_rmse_ev_per_angstrom=float(metrics["worst_condition_force_rmse_ev_per_angstrom"]),
            condition_force_rmse_ev_per_angstrom=tuple((str(k), float(v)) for k, v in metrics.get("condition_force_rmse_ev_per_angstrom", ())),
            combined_loss=float(metrics["combined_loss"]),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MODEL_DATASET_METRIC_RECORD_SCHEMA,
            "configuration_count": self.configuration_count,
            "energy_mae_ev_per_atom": self.energy_mae_ev_per_atom,
            "force_component_rmse_ev_per_angstrom": self.force_component_rmse_ev_per_angstrom,
            "focus_force_rmse_ev_per_angstrom": dict(self.focus_force_rmse_ev_per_angstrom),
            "stress_rmse_ev_per_angstrom3": self.stress_rmse_ev_per_angstrom3,
            "worst_condition_force_rmse_ev_per_angstrom": self.worst_condition_force_rmse_ev_per_angstrom,
            "condition_force_rmse_ev_per_angstrom": dict(self.condition_force_rmse_ev_per_angstrom),
            "combined_loss": self.combined_loss,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ModelDatasetMetricRecord":
        if payload.get("schema") != MODEL_DATASET_METRIC_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported model-dataset metric schema.")
        result = cls(
            configuration_count=int(payload["configuration_count"]),
            energy_mae_ev_per_atom=float(payload["energy_mae_ev_per_atom"]),
            force_component_rmse_ev_per_angstrom=float(payload["force_component_rmse_ev_per_angstrom"]),
            focus_force_rmse_ev_per_angstrom=tuple((str(k), float(v)) for k, v in payload.get("focus_force_rmse_ev_per_angstrom", {}).items()),
            stress_rmse_ev_per_angstrom3=(None if payload.get("stress_rmse_ev_per_angstrom3") is None else float(payload["stress_rmse_ev_per_angstrom3"])),
            worst_condition_force_rmse_ev_per_angstrom=float(payload["worst_condition_force_rmse_ev_per_angstrom"]),
            condition_force_rmse_ev_per_angstrom=tuple((str(k), float(v)) for k, v in payload.get("condition_force_rmse_ev_per_angstrom", {}).items()),
            combined_loss=float(payload["combined_loss"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Model-dataset metric digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CheckpointEvaluationRecord:
    run_plan_digest: str
    checkpoint_sha256: str
    evaluation_policy_digest: str
    target_monitor_artifact_digest: str
    target_monitor_sha256: str
    replay_monitor_artifact_digest: str | None
    replay_monitor_sha256: str | None
    candidate_model_path: str
    candidate_model_sha256: str
    replay_baseline_model_path: str | None
    replay_baseline_model_sha256: str | None
    target_configuration_count: int
    replay_configuration_count: int
    condition_force_rmse_ev_per_angstrom: tuple[tuple[str, float], ...]
    metric_record: CheckpointMetricRecord
    target_candidate_metrics: ModelDatasetMetricRecord | None = None
    target_foundation_metrics: ModelDatasetMetricRecord | None = None
    replay_candidate_metrics: ModelDatasetMetricRecord | None = None
    replay_foundation_metrics: ModelDatasetMetricRecord | None = None
    target_candidate_prediction_digest: str | None = None
    target_foundation_prediction_digest: str | None = None
    replay_candidate_prediction_digest: str | None = None
    replay_foundation_prediction_digest: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "run_plan_digest",
            "checkpoint_sha256",
            "evaluation_policy_digest",
            "target_monitor_artifact_digest",
            "target_monitor_sha256",
            "candidate_model_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in (
            "replay_monitor_artifact_digest",
            "replay_monitor_sha256",
            "replay_baseline_model_sha256",
            "target_candidate_prediction_digest",
            "target_foundation_prediction_digest",
            "replay_candidate_prediction_digest",
            "replay_foundation_prediction_digest",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        if self.target_configuration_count <= 0 or self.replay_configuration_count < 0:
            raise TrainingDataInputError("Evaluation configuration counts are invalid.")
        if self.metric_record.run_plan_digest != self.run_plan_digest:
            raise TrainingDataInputError("Evaluation metric lineage mismatch.")
        if self.metric_record.checkpoint_sha256 != self.checkpoint_sha256:
            raise TrainingDataInputError("Evaluation checkpoint lineage mismatch.")
        conditions = tuple((str(k), _finite_nonnegative(v, name="condition_force_rmse")) for k, v in self.condition_force_rmse_ev_per_angstrom)
        object.__setattr__(self, "condition_force_rmse_ev_per_angstrom", conditions)
        if self.target_candidate_metrics is not None:
            if self.target_candidate_metrics.configuration_count != self.target_configuration_count:
                raise TrainingDataInputError("Target candidate metric count mismatch.")
            if not math.isclose(self.target_candidate_metrics.force_component_rmse_ev_per_angstrom, self.metric_record.force_component_rmse_ev_per_angstrom or 0.0, rel_tol=1.0e-12, abs_tol=1.0e-15):
                raise TrainingDataInputError("Target candidate metrics disagree with checkpoint metric record.")
        if self.target_foundation_metrics is not None and self.target_foundation_metrics.configuration_count != self.target_configuration_count:
            raise TrainingDataInputError("Target foundation metric count mismatch.")
        replay_metrics = (self.replay_candidate_metrics, self.replay_foundation_metrics)
        if any(value is not None for value in replay_metrics) and not all(value is not None for value in replay_metrics):
            raise TrainingDataInputError("Replay candidate/foundation metrics must be stored together.")
        if self.replay_candidate_metrics is not None:
            if self.replay_configuration_count <= 0:
                raise TrainingDataInputError("Replay metric records require a non-empty replay dataset.")
            if self.replay_candidate_metrics.configuration_count != self.replay_configuration_count or self.replay_foundation_metrics.configuration_count != self.replay_configuration_count:
                raise TrainingDataInputError("Replay model metric counts mismatch.")

    @property
    def has_complete_model_comparison(self) -> bool:
        target_complete = self.target_candidate_metrics is not None and self.target_foundation_metrics is not None
        replay_complete = self.replay_configuration_count == 0 or (
            self.replay_candidate_metrics is not None and self.replay_foundation_metrics is not None
        )
        return bool(target_complete and replay_complete)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CHECKPOINT_EVALUATION_RECORD_SCHEMA,
            "run_plan_digest": self.run_plan_digest,
            "checkpoint_sha256": self.checkpoint_sha256,
            "evaluation_policy_digest": self.evaluation_policy_digest,
            "target_monitor_artifact_digest": self.target_monitor_artifact_digest,
            "target_monitor_sha256": self.target_monitor_sha256,
            "replay_monitor_artifact_digest": self.replay_monitor_artifact_digest,
            "replay_monitor_sha256": self.replay_monitor_sha256,
            "candidate_model_path": self.candidate_model_path,
            "candidate_model_sha256": self.candidate_model_sha256,
            "replay_baseline_model_path": self.replay_baseline_model_path,
            "replay_baseline_model_sha256": self.replay_baseline_model_sha256,
            "target_configuration_count": self.target_configuration_count,
            "replay_configuration_count": self.replay_configuration_count,
            "condition_force_rmse_ev_per_angstrom": dict(self.condition_force_rmse_ev_per_angstrom),
            "metric_record": self.metric_record.to_dict(),
            "target_candidate_metrics": None if self.target_candidate_metrics is None else self.target_candidate_metrics.to_dict(),
            "target_foundation_metrics": None if self.target_foundation_metrics is None else self.target_foundation_metrics.to_dict(),
            "replay_candidate_metrics": None if self.replay_candidate_metrics is None else self.replay_candidate_metrics.to_dict(),
            "replay_foundation_metrics": None if self.replay_foundation_metrics is None else self.replay_foundation_metrics.to_dict(),
            "target_candidate_prediction_digest": self.target_candidate_prediction_digest,
            "target_foundation_prediction_digest": self.target_foundation_prediction_digest,
            "replay_candidate_prediction_digest": self.replay_candidate_prediction_digest,
            "replay_foundation_prediction_digest": self.replay_foundation_prediction_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CheckpointEvaluationRecord":
        schema = payload.get("schema")
        if schema not in {
            CHECKPOINT_EVALUATION_RECORD_SCHEMA,
            CHECKPOINT_EVALUATION_RECORD_LEGACY_V2_SCHEMA,
            CHECKPOINT_EVALUATION_RECORD_LEGACY_SCHEMA,
        }:
            raise TrainingDataSerializationError("Unsupported checkpoint-evaluation-record schema.")
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]),
            checkpoint_sha256=str(payload["checkpoint_sha256"]),
            evaluation_policy_digest=str(payload["evaluation_policy_digest"]),
            target_monitor_artifact_digest=str(payload["target_monitor_artifact_digest"]),
            target_monitor_sha256=str(payload["target_monitor_sha256"]),
            replay_monitor_artifact_digest=None if payload.get("replay_monitor_artifact_digest") is None else str(payload["replay_monitor_artifact_digest"]),
            replay_monitor_sha256=None if payload.get("replay_monitor_sha256") is None else str(payload["replay_monitor_sha256"]),
            candidate_model_path=str(payload["candidate_model_path"]),
            candidate_model_sha256=str(payload["candidate_model_sha256"]),
            replay_baseline_model_path=None if payload.get("replay_baseline_model_path") is None else str(payload["replay_baseline_model_path"]),
            replay_baseline_model_sha256=None if payload.get("replay_baseline_model_sha256") is None else str(payload["replay_baseline_model_sha256"]),
            target_configuration_count=int(payload["target_configuration_count"]),
            replay_configuration_count=int(payload["replay_configuration_count"]),
            condition_force_rmse_ev_per_angstrom=tuple((str(k), float(v)) for k, v in payload.get("condition_force_rmse_ev_per_angstrom", {}).items()),
            metric_record=CheckpointMetricRecord.from_dict(payload["metric_record"]),
            target_candidate_metrics=(None if payload.get("target_candidate_metrics") is None else ModelDatasetMetricRecord.from_dict(payload["target_candidate_metrics"])),
            target_foundation_metrics=(None if payload.get("target_foundation_metrics") is None else ModelDatasetMetricRecord.from_dict(payload["target_foundation_metrics"])),
            replay_candidate_metrics=(None if payload.get("replay_candidate_metrics") is None else ModelDatasetMetricRecord.from_dict(payload["replay_candidate_metrics"])),
            replay_foundation_metrics=(None if payload.get("replay_foundation_metrics") is None else ModelDatasetMetricRecord.from_dict(payload["replay_foundation_metrics"])),
            target_candidate_prediction_digest=(None if payload.get("target_candidate_prediction_digest") is None else str(payload["target_candidate_prediction_digest"])),
            target_foundation_prediction_digest=(None if payload.get("target_foundation_prediction_digest") is None else str(payload["target_foundation_prediction_digest"])),
            replay_candidate_prediction_digest=(None if payload.get("replay_candidate_prediction_digest") is None else str(payload["replay_candidate_prediction_digest"])),
            replay_foundation_prediction_digest=(None if payload.get("replay_foundation_prediction_digest") is None else str(payload["replay_foundation_prediction_digest"])),
        )
        observed_digest = payload.get("content_digest")
        expected = result.content_digest
        if schema != CHECKPOINT_EVALUATION_RECORD_SCHEMA:
            legacy_payload = dict(payload)
            legacy_payload.pop("content_digest", None)
            expected = digest(legacy_payload)
        if observed_digest not in (None, expected):
            # Legacy nested metric migration may change the canonical current digest.
            legacy_payload = dict(payload)
            legacy_payload.pop("content_digest", None)
            if observed_digest != digest(legacy_payload):
                raise TrainingDataSerializationError("Checkpoint-evaluation record digest mismatch.")
        return result


@dataclass(slots=True)
class PreparedCheckpointEvaluation:
    """CPU-prepared immutable inputs for one checkpoint evaluation.

    This runtime-only object deliberately carries authenticated monitor objects,
    immutable metric views, and any already durable prediction artifacts.  It is
    not serialized into campaign state.  OPT-EVAL4 uses it to keep checkpoint
    I/O/monitor parsing ahead of accelerator inference without sharing mutable
    calculators between workers.
    """

    run_plan: TrainingCampaignRunPlan
    checkpoint: CheckpointFileRecord
    candidate_model_path: Path
    calculator_model_path: Path | None
    candidate_checkpoint_available: bool
    evaluation_state_capsule: EvaluationStateCapsuleRecord | None
    target_monitor_path: Path
    target_monitor_artifact: MaceExtxyzArtifact
    target_atoms: tuple[Any, ...]
    target_geometry_identities: tuple[str, ...]
    target_configuration_indices: tuple[int, ...]
    target_view: Any
    policy: CheckpointEvaluationPolicy
    execution_plan: InferenceExecutionPlan
    prediction_cache_directory: Path | None
    graph_cache_directory: Path | None
    baseline_model_path: Path | None
    baseline_sha256: str | None
    foundation_prediction_manifest: Any | None
    foundation_prediction_root: Path | None
    target_candidate_artifact: Any | None
    target_candidate_predictions: tuple[Any, ...] | None
    target_candidate_cache_hit: bool
    target_foundation_artifact: Any | None
    target_foundation_predictions: tuple[Any, ...] | None
    target_foundation_cache_hit: bool
    replay_monitor_path: Path | None = None
    replay_monitor_artifact: ReplayFileArtifact | None = None
    training_replay_monitor_artifact: ReplayFileArtifact | None = None
    training_replay_monitor_path: Path | None = None
    replay_lineage_artifact: ReplayFileArtifact | None = None
    replay_atoms: tuple[Any, ...] | None = None
    replay_geometry_identities: tuple[str, ...] | None = None
    replay_configuration_indices: tuple[int, ...] | None = None
    replay_view: Any | None = None
    replay_candidate_artifact: Any | None = None
    replay_candidate_predictions: tuple[Any, ...] | None = None
    replay_candidate_cache_hit: bool = False
    replay_foundation_artifact: Any | None = None
    replay_foundation_predictions: tuple[Any, ...] | None = None
    replay_foundation_cache_hit: bool = False
    target_only_evaluation_authorized: bool = False

    @property
    def requires_candidate_inference(self) -> bool:
        return bool(
            self.target_candidate_predictions is None
            or (
                self.replay_monitor_artifact is not None
                and self.replay_candidate_predictions is None
            )
        )

    @property
    def requires_foundation_inference(self) -> bool:
        return bool(
            (
                self.policy.evaluate_foundation_on_target
                and self.target_foundation_predictions is None
            )
            or (
                self.replay_monitor_artifact is not None
                and self.replay_foundation_predictions is None
            )
        )

    @property
    def requires_model_inference(self) -> bool:
        return self.requires_candidate_inference or self.requires_foundation_inference


@dataclass(slots=True)
class CheckpointEvaluationPredictionBundle:
    """Prediction-stage output consumed by CPU metric/persistence finalization."""

    target_candidate_predictions: tuple[Any, ...]
    target_candidate_artifact: Any | None
    target_foundation_predictions: tuple[Any, ...] | None
    target_foundation_artifact: Any | None
    replay_candidate_predictions: tuple[Any, ...] | None
    replay_candidate_artifact: Any | None
    replay_foundation_predictions: tuple[Any, ...] | None
    replay_foundation_artifact: Any | None


def _optional_cache_path(value: str | Path | None) -> Path | None:
    return None if value is None else Path(value).resolve()


def prepare_mace_checkpoint_evaluation(
    run_plan: TrainingCampaignRunPlan,
    checkpoint: CheckpointFileRecord,
    *,
    candidate_model_path: str | Path,
    target_monitor_path: str | Path,
    calculator_model_path: str | Path | None = None,
    evaluation_state_capsule: EvaluationStateCapsuleRecord | None = None,
    target_monitor_artifact: MaceExtxyzArtifact,
    policy: CheckpointEvaluationPolicy = CheckpointEvaluationPolicy(),
    execution_plan: InferenceExecutionPlan | None = None,
    replay_monitor_path: str | Path | None = None,
    replay_monitor_artifact: ReplayFileArtifact | None = None,
    training_replay_monitor_artifact: ReplayFileArtifact | None = None,
    training_replay_monitor_path: str | Path | None = None,
    replay_baseline_model_path: str | Path | None = None,
    prediction_cache_directory: str | Path | None = None,
    graph_cache_directory: str | Path | None = None,
    foundation_prediction_manifest: Any | None = None,
    foundation_prediction_root: str | Path | None = None,
    target_configuration_indices: Sequence[int] | None = None,
    replay_configuration_indices: Sequence[int] | None = None,
    allow_target_monitor_override: bool = False,
    allow_replay_without_training_lineage: bool = False,
    allow_target_only_evaluation: bool = False,
) -> PreparedCheckpointEvaluation:
    """Authenticate/load monitor inputs without constructing accelerator models.

    OPT-EVAL4 executes this stage in CPU preparation workers.  Cheap foundation
    reuse from DATA6 or frozen replay pseudolabels is resolved here so cache-only
    evaluations never occupy an accelerator slot.
    """

    from .inference_parallel import report_inference_worker_phase
    from .evaluation_views import cached_evaluation_dataset_view

    report_inference_worker_phase("authenticating evaluation artifacts")
    active_execution = (
        _legacy_inference_execution_plan(policy)
        if execution_plan is None
        else execution_plan
    )
    candidate = Path(candidate_model_path).resolve()
    calculator_model = (
        None if calculator_model_path is None else Path(calculator_model_path).resolve()
    )
    target = Path(target_monitor_path).resolve()
    candidate_checkpoint_available = candidate.is_file()
    if candidate_checkpoint_available:
        if evaluation_state_capsule is None:
            if _sha256_file(candidate) != checkpoint.sha256:
                raise TrainingDataInputError("Candidate model bytes do not match checkpoint inventory.")
        else:
            if (
                evaluation_state_capsule.run_plan_digest != checkpoint.run_plan_digest
                or evaluation_state_capsule.source_checkpoint_sha256 != checkpoint.sha256
                or evaluation_state_capsule.source_checkpoint_epoch != checkpoint.epoch
                or _sha256_file(candidate) != evaluation_state_capsule.capsule_sha256
            ):
                raise TrainingDataInputError(
                    "Candidate evaluation-state capsule does not match checkpoint inventory."
                )
    if (
        target_monitor_artifact.content_digest != run_plan.target_monitor_artifact_digest
        and not allow_target_monitor_override
    ):
        raise TrainingDataInputError("Target monitor artifact lineage does not match campaign run.")
    if allow_target_only_evaluation:
        if not allow_target_monitor_override:
            raise TrainingDataInputError(
                "Target-only evaluation authorization is reserved for an explicit target-monitor override."
            )
        if any(
            value is not None
            for value in (
                replay_monitor_path,
                replay_monitor_artifact,
                training_replay_monitor_artifact,
                training_replay_monitor_path,
                replay_configuration_indices,
            )
        ):
            raise TrainingDataInputError(
                "Target-only evaluation cannot also carry replay monitor inputs."
            )
    if not target.is_file() or _sha256_file(target) != target_monitor_artifact.sha256:
        raise TrainingDataInputError("Target monitor bytes do not match the frozen artifact.")

    def normalized_indices(values: Sequence[int] | None, count: int, *, name: str) -> tuple[int, ...]:
        if values is None:
            return tuple(range(count))
        result = tuple(int(value) for value in values)
        if not result:
            raise TrainingDataInputError(f"{name} configuration subset cannot be empty.")
        if any(value < 0 or value >= count for value in result):
            raise TrainingDataInputError(f"{name} configuration subset is out of range.")
        if len(set(result)) != len(result):
            raise TrainingDataInputError(f"{name} configuration subset contains duplicate indices.")
        return result

    report_inference_worker_phase("loading target monitor")
    target_all_atoms = tuple(
        _as_atoms_list(
            target,
            expected_sha256=target_monitor_artifact.sha256,
            use_cache=active_execution.monitor_cache_enabled,
        )
    )
    if len(target_all_atoms) != target_monitor_artifact.configuration_count:
        raise TrainingDataInputError("Target monitor configuration count changed after materialization.")
    target_indices = normalized_indices(
        target_configuration_indices, len(target_all_atoms), name="Target monitor"
    )
    target_atoms = tuple(target_all_atoms[index] for index in target_indices)
    target_geometry_identities = tuple(
        target_monitor_artifact.frame_uids[index] for index in target_indices
    )
    target_view = cached_evaluation_dataset_view(
        f"{_path_cache_identity(target, target_monitor_artifact.sha256)}:subset:{digest({'indices': list(target_indices)})}",
        target_atoms,
        energy_key=policy.energy_key,
        forces_key=policy.forces_key,
        stress_key=policy.stress_key,
        focus_atomic_numbers=policy.focus_atomic_numbers,
        condition_keys=policy.condition_keys,
    )

    prediction_cache = (
        _optional_cache_path(prediction_cache_directory)
        if active_execution.prediction_cache_enabled
        else None
    )
    graph_cache = (
        _optional_cache_path(graph_cache_directory)
        if active_execution.graph_cache_enabled
        else None
    )
    foundation_root = _optional_cache_path(foundation_prediction_root)

    target_candidate_artifact, target_candidate_predictions = _cached_evaluation_predictions(
        prediction_cache,
        model_sha256=checkpoint.sha256,
        head=policy.target_head_name,
        geometry_identities=target_geometry_identities,
        policy=policy,
    )
    target_candidate_cache_hit = target_candidate_predictions is not None

    baseline = (
        None
        if replay_baseline_model_path is None
        else Path(replay_baseline_model_path).resolve()
    )
    baseline_sha = None
    if baseline is not None:
        if not baseline.is_file():
            raise TrainingDataInputError("Foundation baseline model is missing.")
        baseline_sha = _sha256_file(baseline)
        if policy.foundation_identity_bound:
            potential = policy.foundation_potential_identity
            assert potential is not None
            if baseline_sha != potential.sha256:
                raise TrainingDataInputError(
                    "Foundation baseline model bytes disagree with the canonical FoundationPotentialIdentity."
                )
            if policy.source_foundation_head_name != potential.foundation_head:
                raise TrainingDataInputError("Foundation baseline head disagrees with canonical foundation identity.")

    target_foundation_artifact = None
    target_foundation_predictions = None
    target_foundation_cache_hit = False
    if policy.evaluate_foundation_on_target:
        if baseline is None or baseline_sha is None:
            raise TrainingDataInputError(
                "Foundation-on-target comparison requires replay_baseline_model_path."
            )
        target_foundation_artifact, target_foundation_predictions = _cached_evaluation_predictions(
            prediction_cache,
            model_sha256=baseline_sha,
            head=policy.source_foundation_head_name,
            geometry_identities=target_geometry_identities,
            policy=policy,
            foundation_baseline=True,
        )
        target_foundation_cache_hit = target_foundation_predictions is not None
        if target_foundation_predictions is None:
            # This import is CPU/I/O-only and common to every checkpoint.  Resolve
            # it during preparation so no accelerator slot is consumed when DATA6
            # already contains the required foundation outputs.
            with _BASELINE_METRIC_CACHE_LOCK:
                target_foundation_artifact, target_foundation_predictions = _cached_evaluation_predictions(
                    prediction_cache,
                    model_sha256=baseline_sha,
                    head=policy.source_foundation_head_name,
                    geometry_identities=target_geometry_identities,
                    policy=policy,
                    foundation_baseline=True,
                )
                if target_foundation_predictions is None:
                    data6_source = _data6_foundation_predictions(
                        foundation_prediction_manifest,
                        foundation_root,
                        target_geometry_identities,
                        baseline_sha256=baseline_sha,
                        head=policy.source_foundation_head_name,
                        policy=policy,
                    )
                    if data6_source is not None:
                        report_inference_worker_phase(
                            "reusing DATA6 foundation predictions on LTA target monitor"
                        )
                        target_foundation_predictions, source_digest = data6_source
                        target_foundation_artifact = _persist_evaluation_predictions(
                            prediction_cache,
                            model_sha256=baseline_sha,
                            head=policy.source_foundation_head_name,
                            geometry_identities=target_geometry_identities,
                            policy=policy,
                            predictions=target_foundation_predictions,
                            source_kind="data6_foundation_prediction_manifest",
                            source_digest=source_digest,
                            foundation_baseline=True,
                        )

    replay = None
    replay_atoms = None
    replay_geometry_identities = None
    replay_indices = None
    replay_view = None
    lineage_artifact = None
    training_replay_path = (
        None
        if training_replay_monitor_path is None
        else Path(training_replay_monitor_path).resolve()
    )
    replay_candidate_artifact = None
    replay_candidate_predictions = None
    replay_candidate_cache_hit = False
    replay_foundation_artifact = None
    replay_foundation_predictions = None
    replay_foundation_cache_hit = False

    replay_evaluation_required = bool(
        replay_monitor_artifact is not None
        or (
            run_plan.replay_monitor_artifact_digest is not None
            and not allow_target_only_evaluation
        )
    )
    if replay_evaluation_required:
        if replay_monitor_path is None or replay_monitor_artifact is None or baseline is None or baseline_sha is None:
            raise TrainingDataInputError(
                "Replay evaluation requires an evaluation monitor and foundation baseline model."
            )
        if run_plan.replay_monitor_artifact_digest is None:
            if not allow_replay_without_training_lineage:
                raise TrainingDataInputError(
                    "This run has no training replay lineage; explicit full-replay evaluation authorization is required."
                )
            if replay_monitor_artifact.label_mode is not ReplayLabelMode.TRUE_DFT:
                raise TrainingDataInputError(
                    "Replay evaluation without training lineage requires independent true DFT labels."
                )
            lineage_artifact = replay_monitor_artifact
        else:
            lineage_artifact = training_replay_monitor_artifact or replay_monitor_artifact
            if lineage_artifact.content_digest != run_plan.replay_monitor_artifact_digest:
                raise TrainingDataInputError("Training replay monitor artifact lineage does not match campaign run.")
            if replay_monitor_artifact.content_digest != lineage_artifact.content_digest:
                if replay_monitor_artifact.label_mode is not ReplayLabelMode.TRUE_DFT:
                    raise TrainingDataInputError(
                        "An evaluation-only replay override must carry independent true DFT labels."
                    )
                if (
                    replay_monitor_artifact.configuration_count != lineage_artifact.configuration_count
                    or replay_monitor_artifact.geometry_identities != lineage_artifact.geometry_identities
                ):
                    raise TrainingDataInputError(
                        "Evaluation true-label replay monitor must preserve training replay geometry and order."
                    )
        replay = Path(replay_monitor_path).resolve()
        if not replay.is_file() or _sha256_file(replay) != replay_monitor_artifact.sha256:
            raise TrainingDataInputError("Replay monitor bytes do not match the evaluation artifact.")
        report_inference_worker_phase("loading evaluation replay monitor")
        replay_all_atoms = tuple(
            _as_atoms_list(
                replay,
                expected_sha256=replay_monitor_artifact.sha256,
                use_cache=active_execution.monitor_cache_enabled,
            )
        )
        if len(replay_all_atoms) != replay_monitor_artifact.configuration_count:
            raise TrainingDataInputError("Replay monitor configuration count changed after materialization.")
        replay_indices = normalized_indices(
            replay_configuration_indices, len(replay_all_atoms), name="Replay monitor"
        )
        replay_atoms = tuple(replay_all_atoms[index] for index in replay_indices)
        replay_geometry_identities = tuple(
            replay_monitor_artifact.geometry_identities[index] for index in replay_indices
        )
        replay_view = cached_evaluation_dataset_view(
            f"{_path_cache_identity(replay, replay_monitor_artifact.sha256)}:subset:{digest({'indices': list(replay_indices)})}",
            replay_atoms,
            energy_key=policy.energy_key,
            forces_key=policy.forces_key,
            stress_key=policy.stress_key,
            focus_atomic_numbers=policy.focus_atomic_numbers,
            condition_keys=policy.condition_keys,
        )
        replay_candidate_artifact, replay_candidate_predictions = _cached_evaluation_predictions(
            prediction_cache,
            model_sha256=checkpoint.sha256,
            head=policy.replay_head_name,
            geometry_identities=replay_geometry_identities,
            policy=policy,
        )
        replay_candidate_cache_hit = replay_candidate_predictions is not None
        replay_foundation_artifact, replay_foundation_predictions = _cached_evaluation_predictions(
            prediction_cache,
            model_sha256=baseline_sha,
            head=policy.source_foundation_head_name,
            geometry_identities=replay_geometry_identities,
            policy=policy,
            foundation_baseline=True,
        )
        replay_foundation_cache_hit = replay_foundation_predictions is not None
        if replay_foundation_predictions is None:
            # Frozen foundation pseudolabels are already prediction data; import
            # them in CPU preparation rather than scheduling a redundant model.
            with _BASELINE_METRIC_CACHE_LOCK:
                replay_foundation_artifact, replay_foundation_predictions = _cached_evaluation_predictions(
                    prediction_cache,
                    model_sha256=baseline_sha,
                    head=policy.source_foundation_head_name,
                    geometry_identities=replay_geometry_identities,
                    policy=policy,
                    foundation_baseline=True,
                )
                if replay_foundation_predictions is None:
                    pseudo_source = _pseudolabel_foundation_predictions(
                        training_replay_path,
                        lineage_artifact,
                        replay_monitor_artifact,
                        baseline_sha256=baseline_sha,
                        head=policy.source_foundation_head_name,
                        policy=policy,
                        use_dataset_cache=active_execution.monitor_cache_enabled,
                        configuration_indices=replay_indices,
                    )
                    if pseudo_source is not None:
                        report_inference_worker_phase(
                            "reusing frozen replay pseudolabels as foundation predictions"
                        )
                        replay_foundation_predictions, source_digest = pseudo_source
                        replay_foundation_artifact = _persist_evaluation_predictions(
                            prediction_cache,
                            model_sha256=baseline_sha,
                            head=policy.source_foundation_head_name,
                            geometry_identities=replay_geometry_identities,
                            policy=policy,
                            predictions=replay_foundation_predictions,
                            source_kind="foundation_pseudolabel_replay",
                            source_digest=source_digest,
                            foundation_baseline=True,
                        )

    prepared = PreparedCheckpointEvaluation(
        run_plan=run_plan,
        checkpoint=checkpoint,
        candidate_model_path=candidate,
        calculator_model_path=calculator_model,
        candidate_checkpoint_available=candidate_checkpoint_available,
        evaluation_state_capsule=evaluation_state_capsule,
        target_monitor_path=target,
        target_monitor_artifact=target_monitor_artifact,
        target_atoms=target_atoms,
        target_geometry_identities=target_geometry_identities,
        target_configuration_indices=target_indices,
        target_view=target_view,
        policy=policy,
        execution_plan=active_execution,
        prediction_cache_directory=prediction_cache,
        graph_cache_directory=graph_cache,
        baseline_model_path=baseline,
        baseline_sha256=baseline_sha,
        foundation_prediction_manifest=foundation_prediction_manifest,
        foundation_prediction_root=foundation_root,
        target_candidate_artifact=target_candidate_artifact,
        target_candidate_predictions=target_candidate_predictions,
        target_candidate_cache_hit=target_candidate_cache_hit,
        target_foundation_artifact=target_foundation_artifact,
        target_foundation_predictions=target_foundation_predictions,
        target_foundation_cache_hit=target_foundation_cache_hit,
        replay_monitor_path=replay,
        replay_monitor_artifact=replay_monitor_artifact,
        training_replay_monitor_artifact=training_replay_monitor_artifact,
        training_replay_monitor_path=training_replay_path,
        replay_lineage_artifact=lineage_artifact,
        replay_atoms=replay_atoms,
        replay_geometry_identities=replay_geometry_identities,
        replay_configuration_indices=replay_indices,
        replay_view=replay_view,
        replay_candidate_artifact=replay_candidate_artifact,
        replay_candidate_predictions=replay_candidate_predictions,
        replay_candidate_cache_hit=replay_candidate_cache_hit,
        replay_foundation_artifact=replay_foundation_artifact,
        replay_foundation_predictions=replay_foundation_predictions,
        replay_foundation_cache_hit=replay_foundation_cache_hit,
        target_only_evaluation_authorized=allow_target_only_evaluation,
    )
    if prepared.requires_candidate_inference and not candidate_checkpoint_available:
        raise TrainingDataInputError(
            "Candidate checkpoint bytes are unavailable and the required persistent prediction artifact is missing."
        )
    return prepared


def run_prepared_mace_checkpoint_inference(
    prepared: PreparedCheckpointEvaluation,
    *,
    calculator_model_path: str | Path | None = None,
    candidate_provider: Any | None = None,
) -> CheckpointEvaluationPredictionBundle:
    """Run only missing model predictions for one CPU-prepared evaluation.

    Foundation calculators remain private to this invocation.  ``candidate_provider``
    may supply one PERF-P5-qualified unaccelerated model shell for serial checkpoint
    evaluation; the next exact same-architecture state is loaded only after strict
    key/shape/dtype/class validation.  Accelerated/compiled providers reject this
    reuse path.  Independent concurrent workers must never share one mutable shell.
    """

    from .inference_parallel import (
        mark_inference_workload_started,
        report_inference_worker_phase,
    )
    from .model_features import MaceCalculatorProvider

    policy = prepared.policy
    active_calculator_model = (
        Path(calculator_model_path).resolve()
        if calculator_model_path is not None
        else (
            prepared.calculator_model_path
            if prepared.calculator_model_path is not None
            else prepared.candidate_model_path
        )
    )

    target_candidate_artifact = prepared.target_candidate_artifact
    target_candidate_predictions = prepared.target_candidate_predictions
    target_foundation_artifact = prepared.target_foundation_artifact
    target_foundation_predictions = prepared.target_foundation_predictions
    replay_candidate_artifact = prepared.replay_candidate_artifact
    replay_candidate_predictions = prepared.replay_candidate_predictions
    replay_foundation_artifact = prepared.replay_foundation_artifact
    replay_foundation_predictions = prepared.replay_foundation_predictions

    active_candidate_provider: Any | None = candidate_provider
    candidate_shell_supplied = candidate_provider is not None
    baseline_provider: Any | None = None

    def require_candidate_provider(head: str | None) -> Any:
        nonlocal active_candidate_provider
        if not active_calculator_model.is_file():
            raise TrainingDataInputError("Deployable MACE model for checkpoint evaluation is missing.")
        if active_candidate_provider is None:
            mark_inference_workload_started("loading candidate MACE model / accelerator conversion")
            candidate_kwargs = (
                dict(policy.acceleration_policy.calculator_kwargs())
                if policy.resolved_acceleration_kernel_mode is None
                else dict(MaceAccelerationKernelMode(policy.resolved_acceleration_kernel_mode).calculator_kwargs())
            )
            if head is not None:
                candidate_kwargs["head"] = head
            active_candidate_provider = MaceCalculatorProvider.from_model_path(
                active_calculator_model,
                device=policy.device,
                default_dtype=policy.default_dtype,
                critical_precision_policy=policy.active_critical_precision_policy,
                **candidate_kwargs,
            )
        else:
            if candidate_shell_supplied:
                expected_model_sha = _sha256_file(active_calculator_model)
                identity = active_candidate_provider.checkpoint_identity
                if identity.checkpoint_sha256 != expected_model_sha:
                    report_inference_worker_phase("loading compatible checkpoint state into evaluation shell")
                    active_candidate_provider.load_compatible_model_state(
                        active_calculator_model,
                        expected_sha256=expected_model_sha,
                    )
            active_candidate_provider.set_head(head)
        return active_candidate_provider

    def require_baseline_provider(head: str | None) -> Any:
        nonlocal baseline_provider
        baseline = prepared.baseline_model_path
        if baseline is None or not baseline.is_file():
            raise TrainingDataInputError("Foundation baseline model is missing.")
        if baseline_provider is None:
            mark_inference_workload_started("loading foundation MACE model / accelerator conversion")
            baseline_kwargs = (
                dict(policy.acceleration_policy.calculator_kwargs())
                if policy.resolved_acceleration_kernel_mode is None
                else dict(MaceAccelerationKernelMode(policy.resolved_acceleration_kernel_mode).calculator_kwargs())
            )
            if head is not None:
                baseline_kwargs["head"] = head
            baseline_provider = MaceCalculatorProvider.from_model_path(
                baseline,
                device=policy.device,
                default_dtype=policy.default_dtype,
                critical_precision_policy=policy.active_critical_precision_policy,
                foundation_potential_identity=policy.foundation_potential_identity,
                foundation_inference_identity=policy.foundation_inference_identity,
                **baseline_kwargs,
            )
        else:
            baseline_provider.set_head(head)
        return baseline_provider

    if target_candidate_predictions is None:
        report_inference_worker_phase("GPU inference: candidate target monitor")
        target_candidate_predictions = _predict_model_on_monitor(
            active_calculator_model,
            prepared.target_atoms,
            head=policy.target_head_name,
            policy=policy,
            execution_plan=prepared.execution_plan,
            provider=require_candidate_provider(policy.target_head_name),
            geometry_identities=prepared.target_geometry_identities,
            graph_cache_directory=prepared.graph_cache_directory,
        )

    if policy.evaluate_foundation_on_target and target_foundation_predictions is None:
        if prepared.baseline_sha256 is None:
            raise TrainingDataInputError("Foundation baseline identity is unavailable.")
        # Foundation inference is shared by all checkpoint tasks.  Hold the
        # single-flight lock across the one genuine model evaluation and durable
        # publication so followers immediately become cache hits.
        with _BASELINE_METRIC_CACHE_LOCK:
            target_foundation_artifact, target_foundation_predictions = _cached_evaluation_predictions(
                prepared.prediction_cache_directory,
                model_sha256=prepared.baseline_sha256,
                head=policy.source_foundation_head_name,
                geometry_identities=prepared.target_geometry_identities,
                policy=policy,
                foundation_baseline=True,
            )
            if target_foundation_predictions is None:
                report_inference_worker_phase("GPU inference: foundation target monitor")
                target_foundation_predictions = _predict_model_on_monitor(
                    prepared.baseline_model_path,
                    prepared.target_atoms,
                    head=policy.source_foundation_head_name,
                    policy=policy,
                    execution_plan=prepared.execution_plan,
                    provider=require_baseline_provider(policy.source_foundation_head_name),
                    geometry_identities=prepared.target_geometry_identities,
                    graph_cache_directory=prepared.graph_cache_directory,
                )
                target_foundation_artifact = _persist_evaluation_predictions(
                    prepared.prediction_cache_directory,
                    model_sha256=prepared.baseline_sha256,
                    head=policy.source_foundation_head_name,
                    geometry_identities=prepared.target_geometry_identities,
                    policy=policy,
                    predictions=target_foundation_predictions,
                    source_kind="model_inference",
                    foundation_baseline=True,
                )

    if prepared.replay_monitor_artifact is not None:
        if prepared.replay_atoms is None:
            raise TrainingDataInputError("Prepared replay monitor is unavailable.")
        if replay_candidate_predictions is None:
            report_inference_worker_phase("GPU inference: candidate replay monitor")
            replay_candidate_predictions = _predict_model_on_monitor(
                active_calculator_model,
                prepared.replay_atoms,
                head=policy.replay_head_name,
                policy=policy,
                execution_plan=prepared.execution_plan,
                provider=require_candidate_provider(policy.replay_head_name),
                geometry_identities=prepared.replay_geometry_identities,
                graph_cache_directory=prepared.graph_cache_directory,
            )
        if replay_foundation_predictions is None:
            if prepared.baseline_sha256 is None:
                raise TrainingDataInputError("Foundation baseline identity is unavailable.")
            with _BASELINE_METRIC_CACHE_LOCK:
                replay_foundation_artifact, replay_foundation_predictions = _cached_evaluation_predictions(
                    prepared.prediction_cache_directory,
                    model_sha256=prepared.baseline_sha256,
                    head=policy.source_foundation_head_name,
                    geometry_identities=prepared.replay_geometry_identities,
                    policy=policy,
                    foundation_baseline=True,
                )
                if replay_foundation_predictions is None:
                    report_inference_worker_phase("GPU inference: foundation replay monitor")
                    replay_foundation_predictions = _predict_model_on_monitor(
                        prepared.baseline_model_path,
                        prepared.replay_atoms,
                        head=policy.source_foundation_head_name,
                        policy=policy,
                        execution_plan=prepared.execution_plan,
                        provider=require_baseline_provider(policy.source_foundation_head_name),
                        geometry_identities=prepared.replay_geometry_identities,
                        graph_cache_directory=prepared.graph_cache_directory,
                    )
                    replay_foundation_artifact = _persist_evaluation_predictions(
                        prepared.prediction_cache_directory,
                        model_sha256=prepared.baseline_sha256,
                        head=policy.source_foundation_head_name,
                        geometry_identities=prepared.replay_geometry_identities,
                        policy=policy,
                        predictions=replay_foundation_predictions,
                        source_kind="model_inference",
                        foundation_baseline=True,
                    )

    if target_candidate_predictions is None:
        raise TrainingDataInputError("Candidate target predictions are unavailable after inference stage.")
    return CheckpointEvaluationPredictionBundle(
        target_candidate_predictions=target_candidate_predictions,
        target_candidate_artifact=target_candidate_artifact,
        target_foundation_predictions=target_foundation_predictions,
        target_foundation_artifact=target_foundation_artifact,
        replay_candidate_predictions=replay_candidate_predictions,
        replay_candidate_artifact=replay_candidate_artifact,
        replay_foundation_predictions=replay_foundation_predictions,
        replay_foundation_artifact=replay_foundation_artifact,
    )


def finalize_prepared_mace_checkpoint_evaluation(
    prepared: PreparedCheckpointEvaluation,
    predictions: CheckpointEvaluationPredictionBundle,
) -> CheckpointEvaluationRecord:
    """Persist fresh candidate predictions and reduce metrics on CPU."""

    from .inference_parallel import report_inference_worker_phase

    report_inference_worker_phase("CPU finalization: prediction persistence and metrics")
    policy = prepared.policy
    target_candidate_artifact = predictions.target_candidate_artifact
    if target_candidate_artifact is None:
        target_candidate_artifact = _persist_evaluation_predictions(
            prepared.prediction_cache_directory,
            model_sha256=prepared.checkpoint.sha256,
            head=policy.target_head_name,
            geometry_identities=prepared.target_geometry_identities,
            policy=policy,
            predictions=predictions.target_candidate_predictions,
            source_kind="model_inference",
        )
    target_metrics = _metrics_from_predictions(
        prepared.target_atoms,
        predictions.target_candidate_predictions,
        policy=policy,
        view=prepared.target_view,
    )

    target_foundation_metrics_raw = None
    target_foundation_artifact = predictions.target_foundation_artifact
    if policy.evaluate_foundation_on_target:
        if predictions.target_foundation_predictions is None:
            raise TrainingDataInputError("Foundation target predictions are unavailable after inference stage.")
        if target_foundation_artifact is None and prepared.baseline_sha256 is not None:
            target_foundation_artifact = _persist_evaluation_predictions(
                prepared.prediction_cache_directory,
                model_sha256=prepared.baseline_sha256,
                head=policy.source_foundation_head_name,
                geometry_identities=prepared.target_geometry_identities,
                policy=policy,
                predictions=predictions.target_foundation_predictions,
                source_kind="model_inference",
                foundation_baseline=True,
            )
        target_foundation_metrics_raw = _metrics_from_predictions(
            prepared.target_atoms,
            predictions.target_foundation_predictions,
            policy=policy,
            view=prepared.target_view,
        )

    replay_evaluation_digest = None
    replay_training_lineage_digest = None
    replay_sha = None
    replay_count = 0
    baseline_metric = None
    candidate_metric = None
    degradation = None
    baseline_replay_metrics_raw = None
    candidate_replay_metrics_raw = None
    replay_candidate_artifact = predictions.replay_candidate_artifact
    replay_foundation_artifact = predictions.replay_foundation_artifact

    if prepared.replay_monitor_artifact is not None:
        if prepared.replay_atoms is None or prepared.replay_view is None or prepared.replay_lineage_artifact is None:
            raise TrainingDataInputError("Prepared replay evaluation inputs are incomplete.")
        if predictions.replay_candidate_predictions is None or predictions.replay_foundation_predictions is None:
            raise TrainingDataInputError("Replay predictions are unavailable after inference stage.")
        if replay_candidate_artifact is None:
            replay_candidate_artifact = _persist_evaluation_predictions(
                prepared.prediction_cache_directory,
                model_sha256=prepared.checkpoint.sha256,
                head=policy.replay_head_name,
                geometry_identities=prepared.replay_geometry_identities,
                policy=policy,
                predictions=predictions.replay_candidate_predictions,
                source_kind="model_inference",
            )
        if replay_foundation_artifact is None and prepared.baseline_sha256 is not None:
            replay_foundation_artifact = _persist_evaluation_predictions(
                prepared.prediction_cache_directory,
                model_sha256=prepared.baseline_sha256,
                head=policy.source_foundation_head_name,
                geometry_identities=prepared.replay_geometry_identities,
                policy=policy,
                predictions=predictions.replay_foundation_predictions,
                source_kind="model_inference",
                foundation_baseline=True,
            )
        candidate_replay_metrics_raw = _metrics_from_predictions(
            prepared.replay_atoms,
            predictions.replay_candidate_predictions,
            policy=policy,
            view=prepared.replay_view,
        )
        baseline_replay_metrics_raw = _metrics_from_predictions(
            prepared.replay_atoms,
            predictions.replay_foundation_predictions,
            policy=policy,
            view=prepared.replay_view,
        )
        baseline_metric = _replay_scalar(baseline_replay_metrics_raw, policy)
        candidate_metric = _replay_scalar(candidate_replay_metrics_raw, policy)
        if prepared.replay_monitor_artifact.label_mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL:
            degradation = None
        else:
            degradation = max(0.0, candidate_metric - baseline_metric) / max(
                baseline_metric, policy.replay_baseline_floor
            )
        replay_evaluation_digest = prepared.replay_monitor_artifact.content_digest
        replay_training_lineage_digest = prepared.replay_lineage_artifact.content_digest
        replay_sha = prepared.replay_monitor_artifact.sha256
        replay_count = len(prepared.replay_atoms)

    metric_record = CheckpointMetricRecord(
        run_plan_digest=prepared.run_plan.content_digest,
        checkpoint_sha256=prepared.checkpoint.sha256,
        target_monitor_artifact_digest=prepared.target_monitor_artifact.content_digest,
        energy_mae_ev_per_atom=target_metrics["energy_mae_ev_per_atom"],
        force_component_rmse_ev_per_angstrom=target_metrics["force_component_rmse_ev_per_angstrom"],
        focus_force_rmse_ev_per_angstrom=target_metrics["focus_force_rmse_ev_per_angstrom"],
        stress_rmse_ev_per_angstrom3=target_metrics["stress_rmse_ev_per_angstrom3"],
        worst_condition_force_rmse_ev_per_angstrom=target_metrics["worst_condition_force_rmse_ev_per_angstrom"],
        target_combined_loss=target_metrics["combined_loss"],
        replay_monitor_artifact_digest=replay_training_lineage_digest,
        replay_baseline_metric=baseline_metric,
        replay_candidate_metric=candidate_metric,
        replay_degradation_fraction=degradation,
        replay_label_mode=(
            None
            if prepared.replay_monitor_artifact is None
            else prepared.replay_monitor_artifact.label_mode
        ),
        evaluation_notes=(
            f"evaluation_policy:{policy.policy_digest}",
            "evaluation_pipeline:prepared-inference-finalize-v1",
            "prediction_metrics:label_independent_cache_v1",
            "evaluation_view:immutable_preindexed_v1",
            *(("evaluation_scope:authorized_target_only",) if prepared.target_only_evaluation_authorized else ()),
            *(("monitor_graph_cache:stable_shards_v1",) if prepared.graph_cache_directory is not None else ()),
            f"target_candidate_prediction_cache:{'hit' if prepared.target_candidate_cache_hit else 'miss'}",
            *((f"target_foundation_prediction_cache:{'hit' if prepared.target_foundation_cache_hit else 'miss'}",) if target_foundation_metrics_raw is not None else ()),
            *((f"replay_candidate_prediction_cache:{'hit' if prepared.replay_candidate_cache_hit else 'miss'}",) if candidate_replay_metrics_raw is not None else ()),
            *((f"replay_foundation_prediction_cache:{'hit' if prepared.replay_foundation_cache_hit else 'miss'}",) if baseline_replay_metrics_raw is not None else ()),
            *(("target_comparison:foundation_and_candidate",) if target_foundation_metrics_raw is not None else ()),
            *((f"target_candidate_prediction_source:{target_candidate_artifact.source_kind}",) if target_candidate_artifact is not None else ()),
            *((f"target_foundation_prediction_source:{target_foundation_artifact.source_kind}",) if target_foundation_artifact is not None else ()),
            *((f"replay_candidate_prediction_source:{replay_candidate_artifact.source_kind}",) if replay_candidate_artifact is not None else ()),
            *((f"replay_foundation_prediction_source:{replay_foundation_artifact.source_kind}",) if replay_foundation_artifact is not None else ()),
            *(("replay_labels:evaluation_true_dft_override",)
              if prepared.replay_monitor_artifact is not None
              and prepared.training_replay_monitor_artifact is not None
              and prepared.replay_monitor_artifact.content_digest
              != prepared.training_replay_monitor_artifact.content_digest
              else ()),
            *(("replay_role:foundation_pseudolabel_regularization_diagnostic",)
              if prepared.replay_monitor_artifact is not None
              and prepared.replay_monitor_artifact.label_mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL
              else ()),
        ),
    )
    return CheckpointEvaluationRecord(
        run_plan_digest=prepared.run_plan.content_digest,
        checkpoint_sha256=prepared.checkpoint.sha256,
        evaluation_policy_digest=policy.policy_digest,
        target_monitor_artifact_digest=prepared.target_monitor_artifact.content_digest,
        target_monitor_sha256=prepared.target_monitor_artifact.sha256,
        replay_monitor_artifact_digest=replay_evaluation_digest,
        replay_monitor_sha256=replay_sha,
        candidate_model_path=str(prepared.candidate_model_path),
        candidate_model_sha256=prepared.checkpoint.sha256,
        replay_baseline_model_path=(
            None if prepared.baseline_model_path is None else str(prepared.baseline_model_path)
        ),
        replay_baseline_model_sha256=prepared.baseline_sha256,
        target_configuration_count=target_metrics["configuration_count"],
        replay_configuration_count=replay_count,
        condition_force_rmse_ev_per_angstrom=target_metrics["condition_force_rmse_ev_per_angstrom"],
        metric_record=metric_record,
        target_candidate_metrics=ModelDatasetMetricRecord.from_metrics(target_metrics),
        target_foundation_metrics=(
            None
            if target_foundation_metrics_raw is None
            else ModelDatasetMetricRecord.from_metrics(target_foundation_metrics_raw)
        ),
        replay_candidate_metrics=(
            None
            if candidate_replay_metrics_raw is None
            else ModelDatasetMetricRecord.from_metrics(candidate_replay_metrics_raw)
        ),
        replay_foundation_metrics=(
            None
            if baseline_replay_metrics_raw is None
            else ModelDatasetMetricRecord.from_metrics(baseline_replay_metrics_raw)
        ),
        target_candidate_prediction_digest=(
            None if target_candidate_artifact is None else target_candidate_artifact.content_digest
        ),
        target_foundation_prediction_digest=(
            None if target_foundation_artifact is None else target_foundation_artifact.content_digest
        ),
        replay_candidate_prediction_digest=(
            None if replay_candidate_artifact is None else replay_candidate_artifact.content_digest
        ),
        replay_foundation_prediction_digest=(
            None if replay_foundation_artifact is None else replay_foundation_artifact.content_digest
        ),
    )


def evaluate_mace_checkpoint(
    run_plan: TrainingCampaignRunPlan,
    checkpoint: CheckpointFileRecord,
    *,
    candidate_model_path: str | Path,
    target_monitor_path: str | Path,
    calculator_model_path: str | Path | None = None,
    target_monitor_artifact: MaceExtxyzArtifact,
    policy: CheckpointEvaluationPolicy = CheckpointEvaluationPolicy(),
    execution_plan: InferenceExecutionPlan | None = None,
    replay_monitor_path: str | Path | None = None,
    replay_monitor_artifact: ReplayFileArtifact | None = None,
    training_replay_monitor_artifact: ReplayFileArtifact | None = None,
    training_replay_monitor_path: str | Path | None = None,
    replay_baseline_model_path: str | Path | None = None,
    prediction_cache_directory: str | Path | None = None,
    graph_cache_directory: str | Path | None = None,
    foundation_prediction_manifest: Any | None = None,
    foundation_prediction_root: str | Path | None = None,
    target_configuration_indices: Sequence[int] | None = None,
    replay_configuration_indices: Sequence[int] | None = None,
) -> CheckpointEvaluationRecord:
    """Compatibility wrapper for the OPT-EVAL4 staged evaluation contract.

    Direct API callers retain the historical synchronous behavior.  The campaign
    CLI invokes the three stages independently so CPU preparation/finalization can
    overlap accelerator inference across different checkpoints.
    """

    prepared = prepare_mace_checkpoint_evaluation(
        run_plan,
        checkpoint,
        candidate_model_path=candidate_model_path,
        calculator_model_path=calculator_model_path,
        target_monitor_path=target_monitor_path,
        target_monitor_artifact=target_monitor_artifact,
        policy=policy,
        execution_plan=execution_plan,
        replay_monitor_path=replay_monitor_path,
        replay_monitor_artifact=replay_monitor_artifact,
        training_replay_monitor_artifact=training_replay_monitor_artifact,
        training_replay_monitor_path=training_replay_monitor_path,
        replay_baseline_model_path=replay_baseline_model_path,
        prediction_cache_directory=prediction_cache_directory,
        graph_cache_directory=graph_cache_directory,
        foundation_prediction_manifest=foundation_prediction_manifest,
        foundation_prediction_root=foundation_prediction_root,
        target_configuration_indices=target_configuration_indices,
        replay_configuration_indices=replay_configuration_indices,
    )
    prediction_bundle = run_prepared_mace_checkpoint_inference(
        prepared,
        calculator_model_path=calculator_model_path,
    )
    return finalize_prepared_mace_checkpoint_evaluation(prepared, prediction_bundle)

def bind_checkpoint_evaluation_replay_provenance(
    record: CheckpointEvaluationRecord,
    label_mode: ReplayLabelMode | str | None,
    *,
    training_replay_monitor_artifact_digest: str | None = None,
) -> CheckpointEvaluationRecord:
    """Bind replay-label provenance and frozen training lineage to cached evaluations.

    ``CheckpointEvaluationRecord.replay_monitor_artifact_digest`` identifies the
    replay bytes actually evaluated.  With a true-label override this is
    intentionally different from the pseudo-label replay artifact frozen into
    the campaign run.  ``CheckpointMetricRecord.replay_monitor_artifact_digest``
    is the admissibility lineage and therefore must remain bound to the frozen
    *training* replay artifact.  Supplying ``training_replay_monitor_artifact_digest``
    migrates 0.20.95a0 records that accidentally stored the evaluation-only
    true-label digest in both places; no model inference is repeated.

    For foundation-generated pseudo-labels the historical relative degradation
    fraction is discarded because it divides by the foundation model's near-zero
    self-error.  The absolute candidate disagreement is retained as a
    regularization diagnostic.
    """

    if record.replay_monitor_artifact_digest is None:
        return record
    mode = ReplayLabelMode.UNSPECIFIED if label_mode is None else ReplayLabelMode(label_mode)
    metric = record.metric_record
    training_lineage_digest = (
        metric.replay_monitor_artifact_digest
        if training_replay_monitor_artifact_digest is None
        else validate_digest(
            training_replay_monitor_artifact_digest,
            name="training_replay_monitor_artifact_digest",
        )
    )
    degradation = (
        None
        if mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL
        else metric.replay_degradation_fraction
    )
    notes = tuple(
        dict.fromkeys(
            (
                *metric.evaluation_notes,
                f"replay_label_mode:{mode.value}",
                *(
                    ("replay_role:foundation_pseudolabel_regularization_diagnostic",)
                    if mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL
                    else ()
                ),
            )
        )
    )
    updated_metric = replace(
        metric,
        replay_monitor_artifact_digest=training_lineage_digest,
        replay_label_mode=mode,
        replay_degradation_fraction=degradation,
        evaluation_notes=notes,
    )
    if updated_metric == metric:
        return record
    return replace(record, metric_record=updated_metric)


@dataclass(frozen=True, slots=True)
class ProtocolVariantAggregate:
    campaign_plan_digest: str
    protocol_family_digest: str
    protocol_variant_digest: str
    training_mode: TrainingMode
    selection_size: int
    seed: int
    primary_metric_name: str
    fold_run_plan_digests: tuple[str, ...]
    fold_selection_record_digests: tuple[str, ...]
    fold_primary_metric_values: tuple[float, ...]
    final_run_plan_digest: str
    final_selection_record_digest: str
    mean_fold_primary_metric: float
    standard_deviation_fold_primary_metric: float
    worst_fold_primary_metric: float

    def __post_init__(self) -> None:
        for name in ("campaign_plan_digest", "protocol_family_digest", "protocol_variant_digest", "final_run_plan_digest", "final_selection_record_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        object.__setattr__(self, "training_mode", TrainingMode(self.training_mode))
        for values, name in ((self.fold_run_plan_digests, "fold_run_plan_digest"), (self.fold_selection_record_digests, "fold_selection_record_digest")):
            for value in values:
                validate_digest(value, name=name)
        if not (
            len(self.fold_primary_metric_values)
            == len(self.fold_run_plan_digests)
            == len(self.fold_selection_record_digests)
        ):
            raise TrainingDataInputError("Protocol variant aggregate fold evidence is inconsistent.")
        for name in ("mean_fold_primary_metric", "standard_deviation_fold_primary_metric", "worst_fold_primary_metric"):
            object.__setattr__(self, name, _finite_nonnegative(getattr(self, name), name=name))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PROTOCOL_VARIANT_AGGREGATE_SCHEMA,
            "campaign_plan_digest": self.campaign_plan_digest,
            "protocol_family_digest": self.protocol_family_digest,
            "protocol_variant_digest": self.protocol_variant_digest,
            "training_mode": self.training_mode.value,
            "selection_size": self.selection_size,
            "seed": self.seed,
            "primary_metric_name": self.primary_metric_name,
            "fold_run_plan_digests": list(self.fold_run_plan_digests),
            "fold_selection_record_digests": list(self.fold_selection_record_digests),
            "fold_primary_metric_values": list(self.fold_primary_metric_values),
            "final_run_plan_digest": self.final_run_plan_digest,
            "final_selection_record_digest": self.final_selection_record_digest,
            "mean_fold_primary_metric": self.mean_fold_primary_metric,
            "standard_deviation_fold_primary_metric": self.standard_deviation_fold_primary_metric,
            "worst_fold_primary_metric": self.worst_fold_primary_metric,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProtocolVariantAggregate":
        if payload.get("schema") != PROTOCOL_VARIANT_AGGREGATE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported protocol-variant aggregate schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            protocol_family_digest=str(payload["protocol_family_digest"]),
            protocol_variant_digest=str(payload["protocol_variant_digest"]),
            training_mode=TrainingMode(payload["training_mode"]),
            selection_size=int(payload["selection_size"]),
            seed=int(payload["seed"]),
            primary_metric_name=str(payload["primary_metric_name"]),
            fold_run_plan_digests=tuple(str(v) for v in payload["fold_run_plan_digests"]),
            fold_selection_record_digests=tuple(str(v) for v in payload["fold_selection_record_digests"]),
            fold_primary_metric_values=tuple(float(v) for v in payload["fold_primary_metric_values"]),
            final_run_plan_digest=str(payload["final_run_plan_digest"]),
            final_selection_record_digest=str(payload["final_selection_record_digest"]),
            mean_fold_primary_metric=float(payload["mean_fold_primary_metric"]),
            standard_deviation_fold_primary_metric=float(payload["standard_deviation_fold_primary_metric"]),
            worst_fold_primary_metric=float(payload["worst_fold_primary_metric"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Protocol-variant aggregate digest mismatch.")
        return result


def aggregate_protocol_variant(
    campaign: TrainingCampaignPlan,
    run_selections: Mapping[str, CheckpointSelectionRecord],
    selected_metrics: Mapping[str, CheckpointMetricRecord],
    *,
    protocol_variant_digest: str,
) -> ProtocolVariantAggregate:
    runs = list(
        campaign.runs_for_protocol_variant_digest(protocol_variant_digest)
    )
    if not runs:
        raise TrainingDataInputError("Protocol variant is not present in campaign.")
    final = [v for v in runs if v.kind is MaceJobKind.FINAL_DEVELOPMENT]
    folds = sorted((v for v in runs if v.kind is MaceJobKind.CROSS_VALIDATION_FOLD), key=lambda v: int(v.fold_index))
    if len(final) != 1:
        raise TrainingDataInputError("Protocol variant requires exactly one final-development run.")
    all_runs = folds + final
    selections: dict[str, CheckpointSelectionRecord] = {}
    metrics: dict[str, CheckpointMetricRecord] = {}
    for run in all_runs:
        selection = run_selections.get(run.content_digest)
        metric = selected_metrics.get(run.content_digest)
        if selection is None or metric is None:
            raise TrainingDataInputError("Protocol variant aggregation is missing run selection or metric evidence.")
        if selection.run_plan_digest != run.content_digest or metric.run_plan_digest != run.content_digest:
            raise TrainingDataInputError("Protocol variant evidence lineage mismatch.")
        if selection.selected_checkpoint_sha256 != metric.checkpoint_sha256:
            raise TrainingDataInputError("Selected metric does not belong to selected checkpoint.")
        selections[run.content_digest] = selection
        metrics[run.content_digest] = metric
    evidence_runs = folds if folds else final
    first_selection = selections[evidence_runs[0].content_digest]
    first_decision = next(
        v for v in first_selection.decisions
        if v.checkpoint_sha256 == first_selection.selected_checkpoint_sha256
    )
    primary_name = first_decision.primary_metric_name
    values = []
    for run in evidence_runs:
        selection = selections[run.content_digest]
        selected_decision = next(
            v for v in selection.decisions
            if v.checkpoint_sha256 == selection.selected_checkpoint_sha256
        )
        if selected_decision.primary_metric_name != primary_name:
            raise TrainingDataInputError("Protocol checkpoint primary metrics differ.")
        values.append(float(selection.selected_primary_metric_value))
    array = np.asarray(values, dtype=float)
    return ProtocolVariantAggregate(
        campaign_plan_digest=campaign.content_digest,
        protocol_family_digest=runs[0].protocol_family_digest,
        protocol_variant_digest=runs[0].protocol_variant_digest,
        training_mode=runs[0].training_mode,
        selection_size=runs[0].selection_size,
        seed=runs[0].seed,
        primary_metric_name=primary_name,
        fold_run_plan_digests=tuple(v.content_digest for v in folds),
        fold_selection_record_digests=tuple(selections[v.content_digest].content_digest for v in folds),
        fold_primary_metric_values=(tuple(values) if folds else ()),
        final_run_plan_digest=final[0].content_digest,
        final_selection_record_digest=selections[final[0].content_digest].content_digest,
        mean_fold_primary_metric=float(np.mean(array)),
        standard_deviation_fold_primary_metric=float(np.std(array, ddof=0)),
        worst_fold_primary_metric=float(np.max(array)),
    )


@dataclass(frozen=True, slots=True)
class ProtocolFamilyAggregate:
    campaign_plan_digest: str
    protocol_family_digest: str
    training_mode: TrainingMode
    selection_size: int
    primary_metric_name: str
    variant_aggregate_digests: tuple[str, ...]
    seeds: tuple[int, ...]
    seed_mean_fold_metrics: tuple[float, ...]
    mean_cross_validated_metric: float
    between_seed_standard_deviation: float
    worst_seed_metric: float

    def __post_init__(self) -> None:
        for name in ("campaign_plan_digest", "protocol_family_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for value in self.variant_aggregate_digests:
            validate_digest(value, name="variant_aggregate_digest")
        object.__setattr__(self, "training_mode", TrainingMode(self.training_mode))
        if not self.seeds or len(self.seeds) != len(self.seed_mean_fold_metrics):
            raise TrainingDataInputError("Protocol family aggregate requires complete seed evidence.")
        if len(set(self.seeds)) != len(self.seeds):
            raise TrainingDataInputError("Protocol family seeds must be unique.")
        for name in ("mean_cross_validated_metric", "between_seed_standard_deviation", "worst_seed_metric"):
            object.__setattr__(self, name, _finite_nonnegative(getattr(self, name), name=name))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PROTOCOL_FAMILY_AGGREGATE_SCHEMA,
            "campaign_plan_digest": self.campaign_plan_digest,
            "protocol_family_digest": self.protocol_family_digest,
            "training_mode": self.training_mode.value,
            "selection_size": self.selection_size,
            "primary_metric_name": self.primary_metric_name,
            "variant_aggregate_digests": list(self.variant_aggregate_digests),
            "seeds": list(self.seeds),
            "seed_mean_fold_metrics": list(self.seed_mean_fold_metrics),
            "mean_cross_validated_metric": self.mean_cross_validated_metric,
            "between_seed_standard_deviation": self.between_seed_standard_deviation,
            "worst_seed_metric": self.worst_seed_metric,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProtocolFamilyAggregate":
        if payload.get("schema") != PROTOCOL_FAMILY_AGGREGATE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported protocol-family aggregate schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            protocol_family_digest=str(payload["protocol_family_digest"]),
            training_mode=TrainingMode(payload["training_mode"]),
            selection_size=int(payload["selection_size"]),
            primary_metric_name=str(payload["primary_metric_name"]),
            variant_aggregate_digests=tuple(str(v) for v in payload["variant_aggregate_digests"]),
            seeds=tuple(int(v) for v in payload["seeds"]),
            seed_mean_fold_metrics=tuple(float(v) for v in payload["seed_mean_fold_metrics"]),
            mean_cross_validated_metric=float(payload["mean_cross_validated_metric"]),
            between_seed_standard_deviation=float(payload["between_seed_standard_deviation"]),
            worst_seed_metric=float(payload["worst_seed_metric"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Protocol-family aggregate digest mismatch.")
        return result


def aggregate_protocol_family(variants: Sequence[ProtocolVariantAggregate]) -> ProtocolFamilyAggregate:
    if not variants:
        raise TrainingDataInputError("Protocol family aggregation requires variants.")
    family = variants[0].protocol_family_digest
    campaign = variants[0].campaign_plan_digest
    mode = variants[0].training_mode
    size = variants[0].selection_size
    primary = variants[0].primary_metric_name
    if any(v.protocol_family_digest != family or v.campaign_plan_digest != campaign for v in variants):
        raise TrainingDataInputError("Protocol family aggregate mixes lineage.")
    if any(v.training_mode is not mode or v.selection_size != size or v.primary_metric_name != primary for v in variants):
        raise TrainingDataInputError("Protocol family aggregate mixes incompatible protocol settings.")
    ordered = sorted(variants, key=lambda v: v.seed)
    if len({v.seed for v in ordered}) != len(ordered):
        raise TrainingDataInputError("Protocol family aggregate contains duplicate seed evidence.")
    values = np.asarray([v.mean_fold_primary_metric for v in ordered], dtype=float)
    return ProtocolFamilyAggregate(
        campaign_plan_digest=campaign,
        protocol_family_digest=family,
        training_mode=mode,
        selection_size=size,
        primary_metric_name=primary,
        variant_aggregate_digests=tuple(v.content_digest for v in ordered),
        seeds=tuple(v.seed for v in ordered),
        seed_mean_fold_metrics=tuple(float(v) for v in values),
        mean_cross_validated_metric=float(np.mean(values)),
        between_seed_standard_deviation=float(np.std(values, ddof=0)),
        worst_seed_metric=float(np.max(values)),
    )


@dataclass(frozen=True, slots=True)
class LearningCurveRecord:
    campaign_plan_digest: str
    training_mode: TrainingMode
    primary_metric_name: str
    family_aggregate_digests: tuple[str, ...]
    selection_sizes: tuple[int, ...]
    mean_cross_validated_metrics: tuple[float, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "campaign_plan_digest", validate_digest(self.campaign_plan_digest, name="campaign_plan_digest"))
        object.__setattr__(self, "training_mode", TrainingMode(self.training_mode))
        for value in self.family_aggregate_digests:
            validate_digest(value, name="family_aggregate_digest")
        if not self.selection_sizes or tuple(sorted(self.selection_sizes)) != self.selection_sizes:
            raise TrainingDataInputError("Learning curve sizes must be non-empty and sorted.")
        if len(self.selection_sizes) != len(self.mean_cross_validated_metrics):
            raise TrainingDataInputError("Learning curve points are incomplete.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LEARNING_CURVE_RECORD_SCHEMA,
            "campaign_plan_digest": self.campaign_plan_digest,
            "training_mode": self.training_mode.value,
            "primary_metric_name": self.primary_metric_name,
            "family_aggregate_digests": list(self.family_aggregate_digests),
            "selection_sizes": list(self.selection_sizes),
            "mean_cross_validated_metrics": list(self.mean_cross_validated_metrics),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LearningCurveRecord":
        if payload.get("schema") != LEARNING_CURVE_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported learning-curve schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            training_mode=TrainingMode(payload["training_mode"]),
            primary_metric_name=str(payload["primary_metric_name"]),
            family_aggregate_digests=tuple(str(v) for v in payload["family_aggregate_digests"]),
            selection_sizes=tuple(int(v) for v in payload["selection_sizes"]),
            mean_cross_validated_metrics=tuple(float(v) for v in payload["mean_cross_validated_metrics"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Learning-curve digest mismatch.")
        return result


def build_learning_curve(families: Sequence[ProtocolFamilyAggregate], *, training_mode: TrainingMode) -> LearningCurveRecord:
    selected = sorted((v for v in families if v.training_mode is TrainingMode(training_mode)), key=lambda v: v.selection_size)
    if not selected:
        raise TrainingDataInputError("No protocol families exist for requested learning curve.")
    if len({v.selection_size for v in selected}) != len(selected):
        raise TrainingDataInputError("Learning curve has duplicate selection sizes.")
    if len({v.campaign_plan_digest for v in selected}) != 1 or len({v.primary_metric_name for v in selected}) != 1:
        raise TrainingDataInputError("Learning curve families are not protocol-comparable.")
    return LearningCurveRecord(
        campaign_plan_digest=selected[0].campaign_plan_digest,
        training_mode=TrainingMode(training_mode),
        primary_metric_name=selected[0].primary_metric_name,
        family_aggregate_digests=tuple(v.content_digest for v in selected),
        selection_sizes=tuple(v.selection_size for v in selected),
        mean_cross_validated_metrics=tuple(v.mean_cross_validated_metric for v in selected),
    )


@dataclass(frozen=True, slots=True)
class ProtocolComparisonRecord:
    campaign_plan_digest: str
    candidate_family_aggregate_digests: tuple[str, ...]
    primary_metric_name: str
    selected_protocol_family_digest: str
    selected_family_aggregate_digest: str
    selected_training_mode: TrainingMode
    selected_selection_size: int
    ranking: tuple[tuple[str, float], ...]
    comparison_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("campaign_plan_digest", "selected_protocol_family_digest", "selected_family_aggregate_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for value in self.candidate_family_aggregate_digests:
            validate_digest(value, name="candidate_family_aggregate_digest")
        object.__setattr__(self, "selected_training_mode", TrainingMode(self.selected_training_mode))
        if not self.ranking:
            raise TrainingDataInputError("Protocol comparison requires a ranking.")
        for key, value in self.ranking:
            validate_digest(key, name="ranked_protocol_family_digest")
            _finite_nonnegative(value, name="ranked_metric")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PROTOCOL_COMPARISON_RECORD_SCHEMA,
            "campaign_plan_digest": self.campaign_plan_digest,
            "candidate_family_aggregate_digests": list(self.candidate_family_aggregate_digests),
            "primary_metric_name": self.primary_metric_name,
            "selected_protocol_family_digest": self.selected_protocol_family_digest,
            "selected_family_aggregate_digest": self.selected_family_aggregate_digest,
            "selected_training_mode": self.selected_training_mode.value,
            "selected_selection_size": self.selected_selection_size,
            "ranking": dict(self.ranking),
            "comparison_notes": list(self.comparison_notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProtocolComparisonRecord":
        if payload.get("schema") != PROTOCOL_COMPARISON_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported protocol-comparison schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            candidate_family_aggregate_digests=tuple(str(v) for v in payload["candidate_family_aggregate_digests"]),
            primary_metric_name=str(payload["primary_metric_name"]),
            selected_protocol_family_digest=str(payload["selected_protocol_family_digest"]),
            selected_family_aggregate_digest=str(payload["selected_family_aggregate_digest"]),
            selected_training_mode=TrainingMode(payload["selected_training_mode"]),
            selected_selection_size=int(payload["selected_selection_size"]),
            ranking=tuple((str(k), float(v)) for k, v in payload["ranking"].items()),
            comparison_notes=tuple(str(v) for v in payload.get("comparison_notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Protocol-comparison digest mismatch.")
        return result


def compare_protocol_families(families: Sequence[ProtocolFamilyAggregate]) -> ProtocolComparisonRecord:
    if not families:
        raise TrainingDataInputError("Protocol comparison requires at least one family.")
    if len({v.campaign_plan_digest for v in families}) != 1 or len({v.primary_metric_name for v in families}) != 1:
        raise TrainingDataInputError("Protocol comparison mixes campaign or primary metric identity.")
    ordered = sorted(families, key=lambda v: (v.mean_cross_validated_metric, v.worst_seed_metric, v.protocol_family_digest))
    selected = ordered[0]
    notes = (
        ("single_configured_family_no_cross_protocol_comparison",)
        if len(ordered) == 1
        else ("deterministic_mean_then_worst_then_digest",)
    )
    return ProtocolComparisonRecord(
        campaign_plan_digest=selected.campaign_plan_digest,
        candidate_family_aggregate_digests=tuple(v.content_digest for v in sorted(families, key=lambda x: x.protocol_family_digest)),
        primary_metric_name=selected.primary_metric_name,
        selected_protocol_family_digest=selected.protocol_family_digest,
        selected_family_aggregate_digest=selected.content_digest,
        selected_training_mode=selected.training_mode,
        selected_selection_size=selected.selection_size,
        ranking=tuple((v.protocol_family_digest, v.mean_cross_validated_metric) for v in ordered),
        comparison_notes=notes,
    )


@dataclass(frozen=True, slots=True)
class CommitteeExportPolicy:
    target_head_name: str = "target_head"
    required_wrapper: str = "mdstats-mace-select-head"
    target_device: str = "cpu"
    minimum_members: int = 2

    def __post_init__(self) -> None:
        if not self.target_head_name.strip() or not self.required_wrapper.strip():
            raise TrainingDataInputError("Committee export head and wrapper must be non-empty.")
        if self.required_wrapper == "mace_select_head":
            raise TrainingDataInputError("Committee export requires mdstats precision wrapper.")
        if self.minimum_members <= 0:
            raise TrainingDataInputError("Committee minimum members must be positive.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": COMMITTEE_EXPORT_POLICY_SCHEMA,
            "target_head_name": self.target_head_name,
            "required_wrapper": self.required_wrapper,
            "target_device": self.target_device,
            "minimum_members": self.minimum_members,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CommitteeExportPolicy":
        if payload.get("schema") != COMMITTEE_EXPORT_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported committee-export policy schema.")
        result = cls(
            target_head_name=str(payload["target_head_name"]),
            required_wrapper=str(payload["required_wrapper"]),
            target_device=str(payload["target_device"]),
            minimum_members=int(payload["minimum_members"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Committee-export policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CommitteeMemberRecord:
    protocol_family_digest: str
    seed: int
    final_run_plan_digest: str
    checkpoint_selection_record_digest: str
    source_checkpoint_path: str
    source_checkpoint_sha256: str
    target_head_name: str
    exported_model_path: str
    exported_model_sha256: str
    byte_size: int

    def __post_init__(self) -> None:
        for name in ("protocol_family_digest", "final_run_plan_digest", "checkpoint_selection_record_digest", "source_checkpoint_sha256", "exported_model_sha256"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.seed < 0 or self.byte_size <= 0 or not self.target_head_name.strip():
            raise TrainingDataInputError("Committee member metadata are invalid.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": COMMITTEE_MEMBER_RECORD_SCHEMA,
            "protocol_family_digest": self.protocol_family_digest,
            "seed": self.seed,
            "final_run_plan_digest": self.final_run_plan_digest,
            "checkpoint_selection_record_digest": self.checkpoint_selection_record_digest,
            "source_checkpoint_path": self.source_checkpoint_path,
            "source_checkpoint_sha256": self.source_checkpoint_sha256,
            "target_head_name": self.target_head_name,
            "exported_model_path": self.exported_model_path,
            "exported_model_sha256": self.exported_model_sha256,
            "byte_size": self.byte_size,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CommitteeMemberRecord":
        if payload.get("schema") != COMMITTEE_MEMBER_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported committee-member schema.")
        result = cls(
            protocol_family_digest=str(payload["protocol_family_digest"]),
            seed=int(payload["seed"]),
            final_run_plan_digest=str(payload["final_run_plan_digest"]),
            checkpoint_selection_record_digest=str(payload["checkpoint_selection_record_digest"]),
            source_checkpoint_path=str(payload["source_checkpoint_path"]),
            source_checkpoint_sha256=str(payload["source_checkpoint_sha256"]),
            target_head_name=str(payload["target_head_name"]),
            exported_model_path=str(payload["exported_model_path"]),
            exported_model_sha256=str(payload["exported_model_sha256"]),
            byte_size=int(payload["byte_size"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Committee-member digest mismatch.")
        return result


def _export_target_head_model(
    source_model: Path,
    output: Path,
    *,
    target_head_name: str,
    target_device: str,
    wrapper_path: str | Path | None,
    required_wrapper: str,
    failure_prefix: str,
) -> None:
    """Export one target head atomically.

    A per-run model can now be published while the rest of campaign evaluation
    is still running.  Always stage the new bytes beside the destination and
    ``os.replace`` only after successful serialization so an interrupted export
    cannot leave a truncated deployment model or destroy a previously valid one.
    """

    payload = _load_torch_payload(source_model)
    heads_value = getattr(payload, "heads", ())
    if isinstance(heads_value, str):
        heads = (heads_value,)
    else:
        try:
            heads = tuple(str(value) for value in heads_value)
        except TypeError:
            heads = ()
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, staged_name = tempfile.mkstemp(
        prefix=f".{output.stem}-", suffix=output.suffix or ".model", dir=output.parent
    )
    os.close(fd)
    staged = Path(staged_name)
    staged.unlink(missing_ok=True)
    try:
        if len(heads) == 1:
            # There is no head ambiguity.  MACE's select_head utility intentionally
            # rejects single-head models, so move the sole model to the requested
            # deployment device and serialize it directly.
            try:
                model = payload.to(target_device)
                import torch

                torch.save(model, staged)
            except Exception as exc:
                raise TrainingDataInputError(
                    f"{failure_prefix} failed while serializing the sole MACE head."
                ) from exc
        else:
            if len(heads) == 0:
                raise TrainingDataInputError(
                    f"{failure_prefix} could not determine the serialized model head set."
                )
            if target_head_name not in heads:
                raise TrainingDataInputError(
                    f"{failure_prefix} requested head {target_head_name!r}, but the model "
                    f"provides {list(heads)!r}."
                )
            in_process_error: Exception | None = None
            try:
                import torch
                from mace.tools.scripts_utils import remove_pt_head

                # ``mace_select_head`` changes the global default dtype while it
                # reconstructs the single-head architecture. Reproduce that exact
                # semantic locally, then restore the caller's dtype immediately.
                previous_dtype = torch.get_default_dtype()
                try:
                    parameter = next(payload.parameters())
                    torch.set_default_dtype(parameter.dtype)
                    model = remove_pt_head(payload, target_head_name)
                    model = model.to(target_device)
                    torch.save(model, staged)
                finally:
                    torch.set_default_dtype(previous_dtype)
            except Exception as exc:
                in_process_error = exc
                staged.unlink(missing_ok=True)

            if not staged.is_file():
                executable = str(wrapper_path or shutil.which(required_wrapper) or "")
                if not executable or Path(executable).name != required_wrapper:
                    detail = "" if in_process_error is None else f" In-process error: {in_process_error}"
                    raise TrainingDataInputError(
                        "Qualified target-head selection wrapper is unavailable." + detail
                    )
                command = (
                    executable,
                    "--head_name",
                    target_head_name,
                    "--target_device",
                    target_device,
                    "--output_file",
                    str(staged),
                    str(source_model),
                )
                completed = subprocess.run(
                    command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
                )
                if completed.returncode != 0 or not staged.is_file():
                    detail = "" if in_process_error is None else f" In-process error: {in_process_error}"
                    raise TrainingDataInputError(
                        f"{failure_prefix} failed: "
                        + completed.stderr.decode("utf-8", errors="replace")[-1000:]
                        + detail
                    )
        if not staged.is_file() or staged.stat().st_size <= 0:
            raise TrainingDataInputError(f"{failure_prefix} produced an empty model artifact.")
        os.replace(staged, output)
    finally:
        staged.unlink(missing_ok=True)


def _export_target_head_model_with_dtype(
    source_model: Path,
    output: Path,
    *,
    target_head_name: str,
    target_device: str,
    wrapper_path: str | Path | None,
    required_wrapper: str,
    failure_prefix: str,
    deployment_dtype: str | None,
) -> None:
    """Export a target head and optionally enforce its deployment dtype.

    ``deployment_dtype=None`` preserves the historical byte path.  Explicit
    precision profiles route the extracted head through the existing exact
    MACE deployment converter so a refine checkpoint selected from the FP32
    stage still produces a uniformly FP64 deployment artifact.
    """

    if deployment_dtype is None:
        _export_target_head_model(
            source_model, output,
            target_head_name=target_head_name,
            target_device=target_device,
            wrapper_path=wrapper_path,
            required_wrapper=required_wrapper,
            failure_prefix=failure_prefix,
        )
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, intermediate_name = tempfile.mkstemp(
        prefix=f".{output.stem}-head-", suffix=output.suffix or ".model", dir=output.parent
    )
    os.close(fd)
    intermediate = Path(intermediate_name)
    intermediate.unlink(missing_ok=True)
    try:
        _export_target_head_model(
            source_model, intermediate,
            target_head_name=target_head_name,
            target_device=target_device,
            wrapper_path=wrapper_path,
            required_wrapper=required_wrapper,
            failure_prefix=failure_prefix,
        )
        from .mace_deployment import MaceDeploymentExportPolicy, export_mace_deployment_artifact

        export_mace_deployment_artifact(
            intermediate,
            output.parent,
            deployment_dtype=str(deployment_dtype),
            filename=output.name,
            target_head=target_head_name,
            policy=MaceDeploymentExportPolicy(
                deployment_dtype=str(deployment_dtype),
                require_inference_probe=False,
            ),
            overwrite=True,
        )
    finally:
        intermediate.unlink(missing_ok=True)


@mace_runtime_warning_handled("MACE MLCV target-head export")
def export_target_head_model_artifact(
    source_model_path: str | Path,
    output_path: str | Path,
    *,
    target_head_name: str = "target_head",
    target_device: str = "cpu",
    wrapper_path: str | Path | None = None,
    required_wrapper: str = "mdstats-mace-select-head",
    deployment_dtype: str | None = None,
) -> tuple[str, int]:
    """Export one already-authorized MLCV target-head model atomically.

    Selection/checkpoint authority is intentionally checked by the MLCV layer;
    this helper only transforms an authenticated deployable MACE model into the
    exact target-head deployment artifact and returns its byte identity.
    """
    source = Path(source_model_path).resolve()
    output = Path(output_path).resolve()
    if not source.is_file():
        raise TrainingDataInputError("MLCV target-head export source model is missing.")
    _export_target_head_model_with_dtype(
        source, output,
        target_head_name=target_head_name,
        target_device=target_device,
        wrapper_path=wrapper_path,
        required_wrapper=required_wrapper,
        failure_prefix="MLCV target-head export",
        deployment_dtype=deployment_dtype,
    )
    return _sha256_file(output), output.stat().st_size


@mace_runtime_warning_handled("MACE target-head committee export")
def export_target_head_member(
    run_plan: TrainingCampaignRunPlan,
    selection: CheckpointSelectionRecord,
    source_checkpoint_path: str | Path,
    output_path: str | Path,
    *,
    source_model_path: str | Path | None = None,
    policy: CommitteeExportPolicy = CommitteeExportPolicy(),
    wrapper_path: str | Path | None = None,
    deployment_dtype: str | None = None,
) -> CommitteeMemberRecord:
    if run_plan.kind is not MaceJobKind.FINAL_DEVELOPMENT:
        raise TrainingDataInputError("Committee members must come from final-development runs.")
    if selection.run_plan_digest != run_plan.content_digest:
        raise TrainingDataInputError("Committee selection does not belong to final run.")
    source = Path(source_checkpoint_path).resolve()
    model_source = source if source_model_path is None else Path(source_model_path).resolve()
    output = Path(output_path).resolve()
    if not source.is_file() or _sha256_file(source) != selection.selected_checkpoint_sha256:
        raise TrainingDataInputError("Committee source checkpoint bytes do not match selection.")
    if not model_source.is_file():
        raise TrainingDataInputError("Deployable source model for target-head export is missing.")
    _export_target_head_model_with_dtype(
        model_source,
        output,
        target_head_name=policy.target_head_name,
        target_device=policy.target_device,
        wrapper_path=wrapper_path,
        required_wrapper=policy.required_wrapper,
        failure_prefix="Target-head export",
        deployment_dtype=deployment_dtype,
    )
    return CommitteeMemberRecord(
        protocol_family_digest=run_plan.protocol_family_digest,
        seed=run_plan.seed,
        final_run_plan_digest=run_plan.content_digest,
        checkpoint_selection_record_digest=selection.content_digest,
        source_checkpoint_path=str(source),
        source_checkpoint_sha256=selection.selected_checkpoint_sha256,
        target_head_name=policy.target_head_name,
        exported_model_path=str(output),
        exported_model_sha256=_sha256_file(output),
        byte_size=output.stat().st_size,
    )


@dataclass(frozen=True, slots=True)
class VerificationModelRecord:
    protocol_family_digest: str
    protocol_variant_digest: str
    training_mode: TrainingMode
    selection_size: int
    seed: int
    run_plan_digest: str
    run_id: str
    kind: MaceJobKind
    fold_index: int | None
    checkpoint_selection_record_digest: str
    source_checkpoint_path: str
    source_checkpoint_sha256: str
    target_head_name: str
    exported_model_path: str
    exported_model_sha256: str
    byte_size: int

    def __post_init__(self) -> None:
        for name in (
            "protocol_family_digest",
            "protocol_variant_digest",
            "run_plan_digest",
            "checkpoint_selection_record_digest",
            "source_checkpoint_sha256",
            "exported_model_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        object.__setattr__(self, "training_mode", TrainingMode(self.training_mode))
        object.__setattr__(self, "kind", MaceJobKind(self.kind))
        if not self.run_id.strip() or not self.target_head_name.strip():
            raise TrainingDataInputError("Verification model identifiers must be non-empty.")
        if self.selection_size <= 0 or self.seed < 0 or self.byte_size <= 0:
            raise TrainingDataInputError("Verification model metadata are invalid.")
        if self.kind is MaceJobKind.CROSS_VALIDATION_FOLD:
            if self.fold_index is None or self.fold_index < 0:
                raise TrainingDataInputError("Fold verification model requires a nonnegative fold index.")
        elif self.fold_index is not None:
            raise TrainingDataInputError("Final verification model cannot carry a fold index.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": VERIFICATION_MODEL_RECORD_SCHEMA,
            "protocol_family_digest": self.protocol_family_digest,
            "protocol_variant_digest": self.protocol_variant_digest,
            "training_mode": self.training_mode.value,
            "selection_size": self.selection_size,
            "seed": self.seed,
            "run_plan_digest": self.run_plan_digest,
            "run_id": self.run_id,
            "kind": self.kind.value,
            "fold_index": self.fold_index,
            "checkpoint_selection_record_digest": self.checkpoint_selection_record_digest,
            "source_checkpoint_path": self.source_checkpoint_path,
            "source_checkpoint_sha256": self.source_checkpoint_sha256,
            "target_head_name": self.target_head_name,
            "exported_model_path": self.exported_model_path,
            "exported_model_sha256": self.exported_model_sha256,
            "byte_size": self.byte_size,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "VerificationModelRecord":
        if payload.get("schema") != VERIFICATION_MODEL_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported verification-model schema.")
        result = cls(
            protocol_family_digest=str(payload["protocol_family_digest"]),
            protocol_variant_digest=str(payload["protocol_variant_digest"]),
            training_mode=TrainingMode(payload["training_mode"]),
            selection_size=int(payload["selection_size"]),
            seed=int(payload["seed"]),
            run_plan_digest=str(payload["run_plan_digest"]),
            run_id=str(payload["run_id"]),
            kind=MaceJobKind(payload["kind"]),
            fold_index=None if payload.get("fold_index") is None else int(payload["fold_index"]),
            checkpoint_selection_record_digest=str(payload["checkpoint_selection_record_digest"]),
            source_checkpoint_path=str(payload["source_checkpoint_path"]),
            source_checkpoint_sha256=str(payload["source_checkpoint_sha256"]),
            target_head_name=str(payload["target_head_name"]),
            exported_model_path=str(payload["exported_model_path"]),
            exported_model_sha256=str(payload["exported_model_sha256"]),
            byte_size=int(payload["byte_size"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Verification-model digest mismatch.")
        return result


@mace_runtime_warning_handled("MACE target-head verification export")
def export_target_head_verification_model(
    run_plan: TrainingCampaignRunPlan,
    selection: CheckpointSelectionRecord,
    source_checkpoint_path: str | Path,
    output_path: str | Path,
    *,
    source_model_path: str | Path | None = None,
    policy: CommitteeExportPolicy = CommitteeExportPolicy(minimum_members=1),
    wrapper_path: str | Path | None = None,
    deployment_dtype: str | None = None,
) -> VerificationModelRecord:
    if selection.run_plan_digest != run_plan.content_digest:
        raise TrainingDataInputError("Verification selection does not belong to the run.")
    source = Path(source_checkpoint_path).resolve()
    model_source = source if source_model_path is None else Path(source_model_path).resolve()
    output = Path(output_path).resolve()
    if not source.is_file() or _sha256_file(source) != selection.selected_checkpoint_sha256:
        raise TrainingDataInputError("Verification source checkpoint bytes do not match selection.")
    if not model_source.is_file():
        raise TrainingDataInputError("Deployable source model for verification export is missing.")
    _export_target_head_model_with_dtype(
        model_source,
        output,
        target_head_name=policy.target_head_name,
        target_device=policy.target_device,
        wrapper_path=wrapper_path,
        required_wrapper=policy.required_wrapper,
        failure_prefix="Target-head verification export",
        deployment_dtype=deployment_dtype,
    )
    return VerificationModelRecord(
        protocol_family_digest=run_plan.protocol_family_digest,
        protocol_variant_digest=run_plan.protocol_variant_digest,
        training_mode=run_plan.training_mode,
        selection_size=run_plan.selection_size,
        seed=run_plan.seed,
        run_plan_digest=run_plan.content_digest,
        run_id=run_plan.run_id,
        kind=run_plan.kind,
        fold_index=run_plan.fold_index,
        checkpoint_selection_record_digest=selection.content_digest,
        source_checkpoint_path=str(source),
        source_checkpoint_sha256=selection.selected_checkpoint_sha256,
        target_head_name=policy.target_head_name,
        exported_model_path=str(output),
        exported_model_sha256=_sha256_file(output),
        byte_size=output.stat().st_size,
    )


@dataclass(frozen=True, slots=True)
class AvailableModelVerificationSet:
    campaign_plan_digest: str
    available_execution_digest: str
    selected_protocol_family_digest: str
    selected_protocol_variant_digest: str
    training_mode: TrainingMode
    selection_size: int
    seed: int
    evidence_level: VerificationEvidenceLevel
    expected_cross_validation_folds: int
    completed_cross_validation_folds: tuple[int, ...]
    final_development_completed: bool
    completed_run_plan_digests: tuple[str, ...]
    missing_run_plan_digests: tuple[str, ...]
    evidence_run_plan_digests: tuple[str, ...]
    primary_metric_name: str
    primary_metric_values: tuple[float, ...]
    mean_primary_metric: float
    worst_primary_metric: float
    members: tuple[VerificationModelRecord, ...]
    warnings: tuple[str, ...]
    created_at_utc: str

    def __post_init__(self) -> None:
        for name in (
            "campaign_plan_digest",
            "available_execution_digest",
            "selected_protocol_family_digest",
            "selected_protocol_variant_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        object.__setattr__(self, "training_mode", TrainingMode(self.training_mode))
        object.__setattr__(self, "evidence_level", VerificationEvidenceLevel(self.evidence_level))
        folds = tuple(sorted(set(int(value) for value in self.completed_cross_validation_folds)))
        if any(value < 0 for value in folds):
            raise TrainingDataInputError("Completed fold indices must be nonnegative.")
        object.__setattr__(self, "completed_cross_validation_folds", folds)
        if self.expected_cross_validation_folds < 0 or len(folds) > self.expected_cross_validation_folds:
            raise TrainingDataInputError("Available-model fold coverage is invalid.")
        for values, name in (
            (self.completed_run_plan_digests, "completed_run_plan_digest"),
            (self.missing_run_plan_digests, "missing_run_plan_digest"),
            (self.evidence_run_plan_digests, "evidence_run_plan_digest"),
        ):
            for value in values:
                validate_digest(value, name=name)
        if set(self.completed_run_plan_digests) & set(self.missing_run_plan_digests):
            raise TrainingDataInputError("Completed and missing verification runs overlap.")
        if len(self.primary_metric_values) != len(self.evidence_run_plan_digests) or not self.primary_metric_values:
            raise TrainingDataInputError("Available-model metric evidence is incomplete.")
        for value in self.primary_metric_values:
            _finite_nonnegative(value, name="primary_metric_value")
        _finite_nonnegative(self.mean_primary_metric, name="mean_primary_metric")
        _finite_nonnegative(self.worst_primary_metric, name="worst_primary_metric")
        members = tuple(sorted(self.members, key=lambda value: (value.kind.value, -1 if value.fold_index is None else value.fold_index, value.run_id)))
        if not members or {value.run_plan_digest for value in members} != set(self.completed_run_plan_digests):
            raise TrainingDataInputError("Verification members do not exactly cover completed selected runs.")
        if any(value.protocol_variant_digest != self.selected_protocol_variant_digest for value in members):
            raise TrainingDataInputError("Verification members mix protocol variants.")
        object.__setattr__(self, "members", members)
        complete = bool(
            self.final_development_completed
            and len(folds) == self.expected_cross_validation_folds
            and not self.missing_run_plan_digests
        )
        if self.evidence_level is VerificationEvidenceLevel.COMPLETE_VARIANT and not complete:
            raise TrainingDataInputError("Complete-variant evidence does not cover the full variant.")
        if self.evidence_level is VerificationEvidenceLevel.PARTIAL_CROSS_VALIDATION and len(folds) < 2:
            raise TrainingDataInputError("Partial cross-validation requires at least two completed folds.")
        if self.evidence_level is VerificationEvidenceLevel.SINGLE_MODEL and len(folds) >= 2:
            raise TrainingDataInputError("Single-model evidence cannot contain two or more completed folds.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": AVAILABLE_MODEL_VERIFICATION_SET_SCHEMA,
            "campaign_plan_digest": self.campaign_plan_digest,
            "available_execution_digest": self.available_execution_digest,
            "selected_protocol_family_digest": self.selected_protocol_family_digest,
            "selected_protocol_variant_digest": self.selected_protocol_variant_digest,
            "training_mode": self.training_mode.value,
            "selection_size": self.selection_size,
            "seed": self.seed,
            "evidence_level": self.evidence_level.value,
            "expected_cross_validation_folds": self.expected_cross_validation_folds,
            "completed_cross_validation_folds": list(self.completed_cross_validation_folds),
            "final_development_completed": self.final_development_completed,
            "completed_run_plan_digests": list(self.completed_run_plan_digests),
            "missing_run_plan_digests": list(self.missing_run_plan_digests),
            "evidence_run_plan_digests": list(self.evidence_run_plan_digests),
            "primary_metric_name": self.primary_metric_name,
            "primary_metric_values": list(self.primary_metric_values),
            "mean_primary_metric": self.mean_primary_metric,
            "worst_primary_metric": self.worst_primary_metric,
            "members": [value.to_dict() for value in self.members],
            "warnings": list(self.warnings),
            "created_at_utc": self.created_at_utc,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AvailableModelVerificationSet":
        if payload.get("schema") != AVAILABLE_MODEL_VERIFICATION_SET_SCHEMA:
            raise TrainingDataSerializationError("Unsupported available-model verification-set schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            available_execution_digest=str(payload["available_execution_digest"]),
            selected_protocol_family_digest=str(payload["selected_protocol_family_digest"]),
            selected_protocol_variant_digest=str(payload["selected_protocol_variant_digest"]),
            training_mode=TrainingMode(payload["training_mode"]),
            selection_size=int(payload["selection_size"]),
            seed=int(payload["seed"]),
            evidence_level=VerificationEvidenceLevel(payload["evidence_level"]),
            expected_cross_validation_folds=int(payload["expected_cross_validation_folds"]),
            completed_cross_validation_folds=tuple(int(value) for value in payload["completed_cross_validation_folds"]),
            final_development_completed=bool(payload["final_development_completed"]),
            completed_run_plan_digests=tuple(str(value) for value in payload["completed_run_plan_digests"]),
            missing_run_plan_digests=tuple(str(value) for value in payload["missing_run_plan_digests"]),
            evidence_run_plan_digests=tuple(str(value) for value in payload["evidence_run_plan_digests"]),
            primary_metric_name=str(payload["primary_metric_name"]),
            primary_metric_values=tuple(float(value) for value in payload["primary_metric_values"]),
            mean_primary_metric=float(payload["mean_primary_metric"]),
            worst_primary_metric=float(payload["worst_primary_metric"]),
            members=tuple(VerificationModelRecord.from_dict(value) for value in payload["members"]),
            warnings=tuple(str(value) for value in payload.get("warnings", ())),
            created_at_utc=str(payload["created_at_utc"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Available-model verification-set digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CommitteeIdentity:
    campaign_plan_digest: str
    protocol_family_digest: str
    protocol_comparison_record_digest: str
    export_policy_digest: str
    members: tuple[CommitteeMemberRecord, ...]

    def __post_init__(self) -> None:
        for name in ("campaign_plan_digest", "protocol_family_digest", "protocol_comparison_record_digest", "export_policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        members = tuple(sorted(self.members, key=lambda v: v.seed))
        if not members or len({v.seed for v in members}) != len(members):
            raise TrainingDataInputError("Committee members must have unique seeds.")
        if any(v.protocol_family_digest != self.protocol_family_digest for v in members):
            raise TrainingDataInputError("Committee member protocol-family mismatch.")
        if len({v.exported_model_sha256 for v in members}) != len(members):
            raise TrainingDataInputError("Committee members must have distinct exported model bytes.")
        object.__setattr__(self, "members", members)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": COMMITTEE_IDENTITY_SCHEMA,
            "campaign_plan_digest": self.campaign_plan_digest,
            "protocol_family_digest": self.protocol_family_digest,
            "protocol_comparison_record_digest": self.protocol_comparison_record_digest,
            "export_policy_digest": self.export_policy_digest,
            "members": [v.to_dict() for v in self.members],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CommitteeIdentity":
        if payload.get("schema") != COMMITTEE_IDENTITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported committee-identity schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            protocol_family_digest=str(payload["protocol_family_digest"]),
            protocol_comparison_record_digest=str(payload["protocol_comparison_record_digest"]),
            export_policy_digest=str(payload["export_policy_digest"]),
            members=tuple(CommitteeMemberRecord.from_dict(v) for v in payload["members"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Committee-identity digest mismatch.")
        return result


def build_committee_identity(
    campaign: TrainingCampaignPlan,
    comparison: ProtocolComparisonRecord,
    members: Sequence[CommitteeMemberRecord],
    *,
    policy: CommitteeExportPolicy = CommitteeExportPolicy(),
) -> CommitteeIdentity:
    if comparison.campaign_plan_digest != campaign.content_digest:
        raise TrainingDataInputError("Protocol comparison does not belong to campaign.")
    members_tuple = tuple(members)
    if len(members_tuple) < policy.minimum_members:
        raise TrainingDataInputError("Committee does not meet minimum member count.")
    required_seeds = {
        run.seed
        for run in campaign.runs
        if run.protocol_family_digest == comparison.selected_protocol_family_digest
        and run.kind is MaceJobKind.FINAL_DEVELOPMENT
    }
    member_seeds = {v.seed for v in members_tuple}
    if member_seeds != required_seeds:
        raise TrainingDataInputError(
            "Committee seed coverage does not match the selected protocol family."
        )
    return CommitteeIdentity(
        campaign_plan_digest=campaign.content_digest,
        protocol_family_digest=comparison.selected_protocol_family_digest,
        protocol_comparison_record_digest=comparison.content_digest,
        export_policy_digest=policy.policy_digest,
        members=members_tuple,
    )


@dataclass(frozen=True, slots=True)
class ProtocolFreezeRecord:
    production_qualification_digest: str
    campaign_plan_digest: str
    source_catalog_digest: str
    frame_catalog_digest: str
    data5_bundle_digest: str
    protocol_comparison_record_digest: str
    selected_protocol_family_digest: str
    selected_family_aggregate_digest: str
    committee_identity_digest: str
    committee_member_model_sha256: tuple[str, ...]
    final_checkpoint_selection_record_digests: tuple[str, ...]
    frozen_at_utc: str

    def __post_init__(self) -> None:
        for name in (
            "production_qualification_digest",
            "campaign_plan_digest",
            "source_catalog_digest",
            "frame_catalog_digest",
            "data5_bundle_digest",
            "protocol_comparison_record_digest",
            "selected_protocol_family_digest",
            "selected_family_aggregate_digest",
            "committee_identity_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for values, name in ((self.committee_member_model_sha256, "committee_member_model_sha256"), (self.final_checkpoint_selection_record_digests, "final_checkpoint_selection_record_digest")):
            for value in values:
                validate_digest(value, name=name)
        if not self.committee_member_model_sha256 or len(set(self.committee_member_model_sha256)) != len(self.committee_member_model_sha256):
            raise TrainingDataInputError("Protocol freeze requires distinct committee model identities.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PROTOCOL_FREEZE_RECORD_SCHEMA,
            "production_qualification_digest": self.production_qualification_digest,
            "campaign_plan_digest": self.campaign_plan_digest,
            "source_catalog_digest": self.source_catalog_digest,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "protocol_comparison_record_digest": self.protocol_comparison_record_digest,
            "selected_protocol_family_digest": self.selected_protocol_family_digest,
            "selected_family_aggregate_digest": self.selected_family_aggregate_digest,
            "committee_identity_digest": self.committee_identity_digest,
            "committee_member_model_sha256": list(self.committee_member_model_sha256),
            "final_checkpoint_selection_record_digests": list(self.final_checkpoint_selection_record_digests),
            "frozen_at_utc": self.frozen_at_utc,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProtocolFreezeRecord":
        if payload.get("schema") != PROTOCOL_FREEZE_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported protocol-freeze schema.")
        result = cls(
            production_qualification_digest=str(payload["production_qualification_digest"]),
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            source_catalog_digest=str(payload["source_catalog_digest"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            data5_bundle_digest=str(payload["data5_bundle_digest"]),
            protocol_comparison_record_digest=str(payload["protocol_comparison_record_digest"]),
            selected_protocol_family_digest=str(payload["selected_protocol_family_digest"]),
            selected_family_aggregate_digest=str(payload["selected_family_aggregate_digest"]),
            committee_identity_digest=str(payload["committee_identity_digest"]),
            committee_member_model_sha256=tuple(str(v) for v in payload["committee_member_model_sha256"]),
            final_checkpoint_selection_record_digests=tuple(str(v) for v in payload["final_checkpoint_selection_record_digests"]),
            frozen_at_utc=str(payload["frozen_at_utc"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Protocol-freeze digest mismatch.")
        return result


def freeze_training_protocol(
    qualification: ProductionCorpusQualificationRecord,
    campaign: TrainingCampaignPlan,
    comparison: ProtocolComparisonRecord,
    selected_family: ProtocolFamilyAggregate,
    committee: CommitteeIdentity,
    final_selections: Sequence[CheckpointSelectionRecord],
) -> ProtocolFreezeRecord:
    if qualification.status is not ProductionGateStatus.PASSED or not qualification.full_data9a_passed:
        raise TrainingDataInputError("Protocol freeze requires a passed full DATA9A qualification.")
    if campaign.production_qualification_digest != qualification.content_digest:
        raise TrainingDataInputError("Campaign and production qualification lineage mismatch.")
    if comparison.campaign_plan_digest != campaign.content_digest or committee.campaign_plan_digest != campaign.content_digest:
        raise TrainingDataInputError("Protocol comparison or committee belongs to another campaign.")
    if comparison.selected_protocol_family_digest != selected_family.protocol_family_digest:
        raise TrainingDataInputError("Selected family aggregate does not match comparison.")
    if comparison.selected_family_aggregate_digest != selected_family.content_digest:
        raise TrainingDataInputError("Selected family aggregate digest mismatch.")
    if committee.protocol_family_digest != comparison.selected_protocol_family_digest:
        raise TrainingDataInputError("Committee protocol family does not match selected comparison.")
    selection_digests = tuple(sorted(v.content_digest for v in final_selections))
    member_selection_digests = tuple(sorted(v.checkpoint_selection_record_digest for v in committee.members))
    if selection_digests != member_selection_digests:
        raise TrainingDataInputError("Final selection evidence does not exactly match committee members.")
    return ProtocolFreezeRecord(
        production_qualification_digest=qualification.content_digest,
        campaign_plan_digest=campaign.content_digest,
        source_catalog_digest=qualification.source_catalog_digest,
        frame_catalog_digest=qualification.frame_catalog_digest,
        data5_bundle_digest=qualification.data5_bundle_digest,
        protocol_comparison_record_digest=comparison.content_digest,
        selected_protocol_family_digest=comparison.selected_protocol_family_digest,
        selected_family_aggregate_digest=selected_family.content_digest,
        committee_identity_digest=committee.content_digest,
        committee_member_model_sha256=tuple(v.exported_model_sha256 for v in committee.members),
        final_checkpoint_selection_record_digests=selection_digests,
        frozen_at_utc=_utc_now(),
    )


@dataclass(frozen=True, slots=True)
class EvaluationActivationDecision:
    protocol_freeze_record_digest: str
    committee_identity_digest: str
    sealed_evaluation_artifact_digests: tuple[str, ...]
    outcome: EvaluationActivationOutcome
    activated_at_utc: str | None
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "protocol_freeze_record_digest", validate_digest(self.protocol_freeze_record_digest, name="protocol_freeze_record_digest"))
        object.__setattr__(self, "committee_identity_digest", validate_digest(self.committee_identity_digest, name="committee_identity_digest"))
        for value in self.sealed_evaluation_artifact_digests:
            validate_digest(value, name="sealed_evaluation_artifact_digest")
        object.__setattr__(self, "outcome", EvaluationActivationOutcome(self.outcome))
        reasons = tuple(sorted(set(str(v) for v in self.rejection_reasons)))
        if self.outcome is EvaluationActivationOutcome.ACTIVATED:
            if self.activated_at_utc is None or reasons:
                raise TrainingDataInputError("Activated evaluation cannot carry rejection reasons.")
        else:
            if self.activated_at_utc is not None or not reasons:
                raise TrainingDataInputError("Rejected evaluation activation requires reasons.")
        object.__setattr__(self, "rejection_reasons", reasons)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": EVALUATION_ACTIVATION_DECISION_SCHEMA,
            "protocol_freeze_record_digest": self.protocol_freeze_record_digest,
            "committee_identity_digest": self.committee_identity_digest,
            "sealed_evaluation_artifact_digests": list(self.sealed_evaluation_artifact_digests),
            "outcome": self.outcome.value,
            "activated_at_utc": self.activated_at_utc,
            "rejection_reasons": list(self.rejection_reasons),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EvaluationActivationDecision":
        if payload.get("schema") != EVALUATION_ACTIVATION_DECISION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported evaluation-activation schema.")
        result = cls(
            protocol_freeze_record_digest=str(payload["protocol_freeze_record_digest"]),
            committee_identity_digest=str(payload["committee_identity_digest"]),
            sealed_evaluation_artifact_digests=tuple(str(v) for v in payload["sealed_evaluation_artifact_digests"]),
            outcome=EvaluationActivationOutcome(payload["outcome"]),
            activated_at_utc=None if payload.get("activated_at_utc") is None else str(payload["activated_at_utc"]),
            rejection_reasons=tuple(str(v) for v in payload.get("rejection_reasons", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Evaluation-activation digest mismatch.")
        return result


def activate_sealed_evaluation(
    freeze: ProtocolFreezeRecord,
    committee: CommitteeIdentity,
    artifacts: Sequence[SealedEvaluationArtifact],
) -> EvaluationActivationDecision:
    reasons: list[str] = []
    if freeze.committee_identity_digest != committee.content_digest:
        reasons.append("committee_identity_mismatch")
    if not artifacts:
        reasons.append("no_sealed_evaluation_artifacts")
    for artifact in artifacts:
        if artifact.materialized:
            reasons.append("sealed_artifact_already_materialized")
        if artifact.activation_requirement != "ProtocolFreezeRecord":
            reasons.append("unexpected_activation_requirement")
        if artifact.frame_catalog_digest != freeze.frame_catalog_digest:
            reasons.append("frame_catalog_lineage_mismatch")
        if artifact.data5_bundle_digest != freeze.data5_bundle_digest:
            reasons.append("data5_lineage_mismatch")
    if reasons:
        return EvaluationActivationDecision(
            protocol_freeze_record_digest=freeze.content_digest,
            committee_identity_digest=committee.content_digest,
            sealed_evaluation_artifact_digests=tuple(v.content_digest for v in artifacts),
            outcome=EvaluationActivationOutcome.REJECTED,
            activated_at_utc=None,
            rejection_reasons=tuple(reasons),
        )
    return EvaluationActivationDecision(
        protocol_freeze_record_digest=freeze.content_digest,
        committee_identity_digest=committee.content_digest,
        sealed_evaluation_artifact_digests=tuple(v.content_digest for v in artifacts),
        outcome=EvaluationActivationOutcome.ACTIVATED,
        activated_at_utc=_utc_now(),
        rejection_reasons=(),
    )


__all__ = [
    "TRAINING_EXECUTION_POLICY_SCHEMA",
    "TRAINING_RUN_ATTEMPT_SCHEMA",
    "TRAINING_RUN_EXECUTION_SCHEMA",
    "CHECKPOINT_EVALUATION_POLICY_SCHEMA",
    "CHECKPOINT_EVALUATION_RECORD_SCHEMA",
    "PROTOCOL_VARIANT_AGGREGATE_SCHEMA",
    "PROTOCOL_FAMILY_AGGREGATE_SCHEMA",
    "LEARNING_CURVE_RECORD_SCHEMA",
    "PROTOCOL_COMPARISON_RECORD_SCHEMA",
    "COMMITTEE_EXPORT_POLICY_SCHEMA",
    "COMMITTEE_MEMBER_RECORD_SCHEMA",
    "COMMITTEE_IDENTITY_SCHEMA",
    "PROTOCOL_FREEZE_RECORD_SCHEMA",
    "EVALUATION_ACTIVATION_DECISION_SCHEMA",
    "VERIFICATION_MODEL_RECORD_SCHEMA",
    "AVAILABLE_MODEL_VERIFICATION_SET_SCHEMA",
    "MLFF_DATA9B2_VERSION",
    "TrainingRunState",
    "EvaluationActivationOutcome",
    "VerificationEvidenceLevel",
    "TrainingExecutionPolicy",
    "TrainingRunAttemptRecord",
    "TrainingRunExecutionRecord",
    "CheckpointEvaluationPolicy",
    "CheckpointEvaluationRecord",
    "ProtocolVariantAggregate",
    "ProtocolFamilyAggregate",
    "LearningCurveRecord",
    "ProtocolComparisonRecord",
    "CommitteeExportPolicy",
    "CommitteeMemberRecord",
    "VerificationModelRecord",
    "AvailableModelVerificationSet",
    "CommitteeIdentity",
    "ProtocolFreezeRecord",
    "EvaluationActivationDecision",
    "execute_training_run",
    "evaluate_mace_checkpoint",
    "bind_checkpoint_evaluation_replay_provenance",
    "aggregate_protocol_variant",
    "aggregate_protocol_family",
    "build_learning_curve",
    "compare_protocol_families",
    "export_target_head_member",
    "export_target_head_verification_model",
    "build_committee_identity",
    "freeze_training_protocol",
    "activate_sealed_evaluation",
]
