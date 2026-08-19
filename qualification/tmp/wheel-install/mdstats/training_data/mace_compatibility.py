"""Version-locked MACE compatibility and loader-realization contracts."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field as dataclass_field
from functools import wraps
from importlib import metadata
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Iterator, Mapping
import hashlib
import logging
import re
import sys
import warnings

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)

MACE_COMPATIBILITY_POLICY_SCHEMA = "mdstats.mace-compatibility-policy.v1"
MACE_SOURCE_PROBE_SCHEMA = "mdstats.mace-source-probe.v1"
MACE_CHECKPOINT_CONTROL_POLICY_SCHEMA = "mdstats.mace-checkpoint-control-policy.v1"
MACE_LOADER_DRY_RUN_SCHEMA = "mdstats.mace-loader-dry-run.v1"
MACE_COMPATIBILITY_POLICY_VERSION = "mdstats.mlff-data8.mace-compatibility.2026-07.v1"

MACE_SELECTED_HEAD_COMPATIBILITY_POLICY_SCHEMA = "mdstats.mace-selected-head-compatibility-policy.v1"
MACE_MH1_SELECTED_HEAD_SHIM_VERSION = "mdstats.mh1-selected-head-reconstruction.2026-08.v1"


@dataclass(frozen=True, slots=True)
class MaceSelectedHeadCompatibilityPolicy:
    """Version-guarded selected-head reconstruction policy for MH1-EXTRACT1.

    MACE 0.3.16 can lose the MH-1 first-layer edge projection metadata while
    reconstructing a single selected head.  Its helper also constructs the new
    module in Torch's ambient default dtype.  mdstats permits one narrow
    compatibility correction: restore the serialized first-layer edge-projection
    intent when the exact affected architecture is detected, and always preserve
    the source floating dtype during reconstruction.
    """

    package_name: str = "mace-torch"
    affected_package_version: str = "0.3.16"
    affected_model_class: str = "ScaleShiftMACE"
    affected_first_interaction_class: str = "RealAgnosticResidualNonLinearInteractionBlock"
    inferred_attribute: str = "use_edge_irreps_first"
    inferred_value: bool = True
    preserve_source_dtype: bool = True
    shim_version: str = MACE_MH1_SELECTED_HEAD_SHIM_VERSION
    serialization_schema: str = MACE_SELECTED_HEAD_COMPATIBILITY_POLICY_SCHEMA

    def __post_init__(self) -> None:
        if self.package_name != "mace-torch" or self.affected_package_version != "0.3.16":
            raise TrainingDataInputError("MH1-EXTRACT1 is version-guarded to mace-torch==0.3.16.")
        for name in (
            "affected_model_class",
            "affected_first_interaction_class",
            "inferred_attribute",
            "shim_version",
            "serialization_schema",
        ):
            if not str(getattr(self, name)).strip():
                raise TrainingDataInputError(f"Selected-head compatibility {name} must be non-empty.")
        if self.serialization_schema != MACE_SELECTED_HEAD_COMPATIBILITY_POLICY_SCHEMA:
            raise TrainingDataInputError("Unsupported selected-head compatibility policy schema.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "package_name": self.package_name,
            "affected_package_version": self.affected_package_version,
            "affected_model_class": self.affected_model_class,
            "affected_first_interaction_class": self.affected_first_interaction_class,
            "inferred_attribute": self.inferred_attribute,
            "inferred_value": self.inferred_value,
            "preserve_source_dtype": self.preserve_source_dtype,
            "shim_version": self.shim_version,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceSelectedHeadCompatibilityPolicy":
        if payload.get("schema") != MACE_SELECTED_HEAD_COMPATIBILITY_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported selected-head compatibility policy schema.")
        result = cls(
            package_name=str(payload["package_name"]),
            affected_package_version=str(payload["affected_package_version"]),
            affected_model_class=str(payload["affected_model_class"]),
            affected_first_interaction_class=str(payload["affected_first_interaction_class"]),
            inferred_attribute=str(payload["inferred_attribute"]),
            inferred_value=bool(payload["inferred_value"]),
            preserve_source_dtype=bool(payload["preserve_source_dtype"]),
            shim_version=str(payload["shim_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Selected-head compatibility policy digest mismatch.")
        return result



class MaceExposureBackend(str, Enum):
    NATIVE_MACE_FIXED = "native_mace_fixed"
    CUSTOM_EPOCH_RESAMPLE = "custom_epoch_resample"
    MULTI_JOB_RESAMPLE = "multi_job_resample"
    FINAL_REFIT = "final_refit"


class MaceCheckpointControlMode(str, Enum):
    NATIVE_TARGET_LAST_WITH_EXTERNAL_CONSTRAINT_AUDIT = (
        "native_target_last_with_external_constraint_audit"
    )


@dataclass(frozen=True, slots=True)
class MaceCompatibilityPolicy:
    package_name: str = "mace-torch"
    package_version: str = "0.3.16"
    release_tag: str = "v0.3.16"
    release_commit: str = "4d2da09"
    run_train_source_url: str = (
        "https://raw.githubusercontent.com/ACEsuit/mace/v0.3.16/mace/cli/run_train.py"
    )
    train_source_url: str = (
        "https://raw.githubusercontent.com/ACEsuit/mace/v0.3.16/mace/tools/train.py"
    )
    multihead_source_url: str = (
        "https://raw.githubusercontent.com/ACEsuit/mace/v0.3.16/mace/tools/multihead_tools.py"
    )
    policy_version: str = MACE_COMPATIBILITY_POLICY_VERSION

    def __post_init__(self) -> None:
        if self.package_name != "mace-torch" or self.package_version != "0.3.16":
            raise TrainingDataInputError(
                "The first DATA8 adapter is locked to mace-torch==0.3.16."
            )
        for name in (
            "release_tag",
            "release_commit",
            "run_train_source_url",
            "train_source_url",
            "multihead_source_url",
            "policy_version",
        ):
            if not str(getattr(self, name)).strip():
                raise TrainingDataInputError(f"{name} must be non-empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_COMPATIBILITY_POLICY_SCHEMA,
            "package_name": self.package_name,
            "package_version": self.package_version,
            "release_tag": self.release_tag,
            "release_commit": self.release_commit,
            "run_train_source_url": self.run_train_source_url,
            "train_source_url": self.train_source_url,
            "multihead_source_url": self.multihead_source_url,
            "policy_version": self.policy_version,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceCompatibilityPolicy":
        if payload.get("schema") != MACE_COMPATIBILITY_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE compatibility schema.")
        result = cls(
            package_name=str(payload["package_name"]),
            package_version=str(payload["package_version"]),
            release_tag=str(payload["release_tag"]),
            release_commit=str(payload["release_commit"]),
            run_train_source_url=str(payload["run_train_source_url"]),
            train_source_url=str(payload["train_source_url"]),
            multihead_source_url=str(payload["multihead_source_url"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MACE compatibility digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceSourceProbe:
    policy_digest: str
    run_train_sha256: str
    train_sha256: str
    multihead_sha256: str
    pt_head_sorted_first: bool
    target_validation_head_is_last: bool
    native_checkpoint_uses_last_validation_head: bool
    implicit_target_duplication_present: bool
    dry_run_supported: bool
    save_all_checkpoints_supported: bool
    fixed_file_adapter_supported: bool
    evidence_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "policy_digest",
            "run_train_sha256",
            "train_sha256",
            "multihead_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        expected = (
            self.pt_head_sorted_first
            and self.target_validation_head_is_last
            and self.native_checkpoint_uses_last_validation_head
            and self.implicit_target_duplication_present
            and self.dry_run_supported
            and self.save_all_checkpoints_supported
        )
        if self.fixed_file_adapter_supported != expected:
            raise TrainingDataInputError("MACE source-probe support state is inconsistent.")
        object.__setattr__(self, "evidence_notes", tuple(str(v) for v in self.evidence_notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_SOURCE_PROBE_SCHEMA,
            "policy_digest": self.policy_digest,
            "run_train_sha256": self.run_train_sha256,
            "train_sha256": self.train_sha256,
            "multihead_sha256": self.multihead_sha256,
            "pt_head_sorted_first": self.pt_head_sorted_first,
            "target_validation_head_is_last": self.target_validation_head_is_last,
            "native_checkpoint_uses_last_validation_head": self.native_checkpoint_uses_last_validation_head,
            "implicit_target_duplication_present": self.implicit_target_duplication_present,
            "dry_run_supported": self.dry_run_supported,
            "save_all_checkpoints_supported": self.save_all_checkpoints_supported,
            "fixed_file_adapter_supported": self.fixed_file_adapter_supported,
            "evidence_notes": list(self.evidence_notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceSourceProbe":
        if payload.get("schema") != MACE_SOURCE_PROBE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE source-probe schema.")
        result = cls(
            policy_digest=str(payload["policy_digest"]),
            run_train_sha256=str(payload["run_train_sha256"]),
            train_sha256=str(payload["train_sha256"]),
            multihead_sha256=str(payload["multihead_sha256"]),
            pt_head_sorted_first=bool(payload["pt_head_sorted_first"]),
            target_validation_head_is_last=bool(payload["target_validation_head_is_last"]),
            native_checkpoint_uses_last_validation_head=bool(payload["native_checkpoint_uses_last_validation_head"]),
            implicit_target_duplication_present=bool(payload["implicit_target_duplication_present"]),
            dry_run_supported=bool(payload["dry_run_supported"]),
            save_all_checkpoints_supported=bool(payload["save_all_checkpoints_supported"]),
            fixed_file_adapter_supported=bool(payload["fixed_file_adapter_supported"]),
            evidence_notes=tuple(str(v) for v in payload.get("evidence_notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE source-probe digest mismatch.")
        return result


def probe_mace_source_texts(
    run_train_text: str,
    train_text: str,
    multihead_text: str,
    *,
    policy: MaceCompatibilityPolicy | None = None,
) -> MaceSourceProbe:
    """Verify the exact v0.3.16 behaviors required by the fixed-file adapter."""

    active = MaceCompatibilityPolicy() if policy is None else policy
    run_digest = hashlib.sha256(run_train_text.encode("utf-8")).hexdigest()
    train_digest = hashlib.sha256(train_text.encode("utf-8")).hexdigest()
    multi_digest = hashlib.sha256(multihead_text.encode("utf-8")).hexdigest()
    pt_first = bool(
        re.search(
            r"heads\s*=\s*sorted\(heads,\s*key=lambda\s+x:\s*-1000\s+if\s+x\s*==\s*[\"']pt_head[\"']\s+else\s+0\)",
            run_train_text,
        )
    )
    last_valid = "consider only the last head for the checkpoint" in train_text
    duplication = (
        "real_pt_data_ratio_threshold" in run_train_text
        and "head_config.collections.train +=" in run_train_text
    )
    dry_run = "if args.dry_run" in run_train_text
    save_all = "save_all_checkpoints=args.save_all_checkpoints" in run_train_text and "if save_all_checkpoints" in train_text
    pt_prepare = "def prepare_pt_head" in multihead_text and "pt_valid_file" in multihead_text
    target_last = pt_first and pt_prepare
    supported = pt_first and target_last and last_valid and duplication and dry_run and save_all
    return MaceSourceProbe(
        policy_digest=active.policy_digest,
        run_train_sha256=run_digest,
        train_sha256=train_digest,
        multihead_sha256=multi_digest,
        pt_head_sorted_first=pt_first,
        target_validation_head_is_last=target_last,
        native_checkpoint_uses_last_validation_head=last_valid,
        implicit_target_duplication_present=duplication,
        dry_run_supported=dry_run,
        save_all_checkpoints_supported=save_all,
        fixed_file_adapter_supported=supported,
        evidence_notes=(
            "Source-text probes are semantic locks, not a substitute for an installed MACE dry run.",
        ),
    )


def probe_mace_source_tree(
    root: str | Path,
    *,
    policy: MaceCompatibilityPolicy | None = None,
) -> MaceSourceProbe:
    source = Path(root)
    paths = (
        source / "mace" / "cli" / "run_train.py",
        source / "mace" / "tools" / "train.py",
        source / "mace" / "tools" / "multihead_tools.py",
    )
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise TrainingDataInputError(
            "MACE source tree is incomplete: " + ", ".join(missing)
        )
    texts = tuple(path.read_text(encoding="utf-8") for path in paths)
    return probe_mace_source_texts(*texts, policy=policy)


@dataclass(frozen=True, slots=True)
class MaceCheckpointControlPolicy:
    mode: MaceCheckpointControlMode = (
        MaceCheckpointControlMode.NATIVE_TARGET_LAST_WITH_EXTERNAL_CONSTRAINT_AUDIT
    )
    target_head_name: str = "target_head"
    replay_head_name: str = "pt_head"
    save_all_checkpoints: bool = True
    native_patience: int = 1000000
    require_target_last_validation_head: bool = True
    require_external_checkpoint_audit: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", MaceCheckpointControlMode(self.mode))
        if not self.target_head_name.strip() or not self.replay_head_name.strip():
            raise TrainingDataInputError("MACE head names must be non-empty.")
        if self.target_head_name == self.replay_head_name:
            raise TrainingDataInputError("Target and replay heads must differ.")
        if not self.save_all_checkpoints or not self.require_external_checkpoint_audit:
            raise TrainingDataInputError(
                "The initial DATA8 adapter requires save-all plus external audit."
            )
        if self.native_patience <= 0:
            raise TrainingDataInputError("native_patience must be positive.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_CHECKPOINT_CONTROL_POLICY_SCHEMA,
            "mode": self.mode.value,
            "target_head_name": self.target_head_name,
            "replay_head_name": self.replay_head_name,
            "save_all_checkpoints": self.save_all_checkpoints,
            "native_patience": self.native_patience,
            "require_target_last_validation_head": self.require_target_last_validation_head,
            "require_external_checkpoint_audit": self.require_external_checkpoint_audit,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceCheckpointControlPolicy":
        if payload.get("schema") != MACE_CHECKPOINT_CONTROL_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported checkpoint-control schema.")
        result = cls(
            mode=MaceCheckpointControlMode(payload["mode"]),
            target_head_name=str(payload["target_head_name"]),
            replay_head_name=str(payload["replay_head_name"]),
            save_all_checkpoints=bool(payload["save_all_checkpoints"]),
            native_patience=int(payload["native_patience"]),
            require_target_last_validation_head=bool(payload["require_target_last_validation_head"]),
            require_external_checkpoint_audit=bool(payload["require_external_checkpoint_audit"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Checkpoint-control digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceLoaderDryRun:
    compatibility_probe_digest: str
    exposure_backend: MaceExposureBackend
    target_head_name: str
    replay_head_name: str | None
    head_order: tuple[str, ...]
    validation_head_order: tuple[str, ...]
    native_checkpoint_head: str
    target_train_count_exported: int
    target_train_count_effective: int
    replay_train_count_exported: int
    replay_train_count_effective: int
    real_pt_data_ratio_threshold: float
    implicit_target_duplication_factor: int
    target_validation_count: int
    replay_validation_count: int
    dry_run_command: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "compatibility_probe_digest", validate_digest(self.compatibility_probe_digest, name="compatibility_probe_digest"))
        object.__setattr__(self, "exposure_backend", MaceExposureBackend(self.exposure_backend))
        if self.exposure_backend is not MaceExposureBackend.NATIVE_MACE_FIXED:
            raise TrainingDataInputError("DATA8 supports only NATIVE_MACE_FIXED.")
        if not self.head_order or self.native_checkpoint_head != self.validation_head_order[-1]:
            raise TrainingDataInputError("Native checkpoint head must be the last validation head.")
        for name in (
            "target_train_count_exported",
            "target_train_count_effective",
            "replay_train_count_exported",
            "replay_train_count_effective",
            "implicit_target_duplication_factor",
            "target_validation_count",
            "replay_validation_count",
        ):
            if int(getattr(self, name)) < 0:
                raise TrainingDataInputError(f"{name} must be nonnegative.")
        if self.implicit_target_duplication_factor < 1:
            raise TrainingDataInputError("Duplication factor must be at least one.")
        if self.target_train_count_effective != self.target_train_count_exported * self.implicit_target_duplication_factor:
            raise TrainingDataInputError("Effective target count is inconsistent.")
        if self.replay_train_count_effective != self.replay_train_count_exported:
            raise TrainingDataInputError("Replay count must remain unchanged in the v0.3.16 model.")
        if self.real_pt_data_ratio_threshold < 0.0:
            raise TrainingDataInputError("Replay-ratio threshold must be nonnegative.")
        object.__setattr__(self, "dry_run_command", tuple(str(v) for v in self.dry_run_command))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_LOADER_DRY_RUN_SCHEMA,
            "compatibility_probe_digest": self.compatibility_probe_digest,
            "exposure_backend": self.exposure_backend.value,
            "target_head_name": self.target_head_name,
            "replay_head_name": self.replay_head_name,
            "head_order": list(self.head_order),
            "validation_head_order": list(self.validation_head_order),
            "native_checkpoint_head": self.native_checkpoint_head,
            "target_train_count_exported": self.target_train_count_exported,
            "target_train_count_effective": self.target_train_count_effective,
            "replay_train_count_exported": self.replay_train_count_exported,
            "replay_train_count_effective": self.replay_train_count_effective,
            "real_pt_data_ratio_threshold": self.real_pt_data_ratio_threshold,
            "implicit_target_duplication_factor": self.implicit_target_duplication_factor,
            "target_validation_count": self.target_validation_count,
            "replay_validation_count": self.replay_validation_count,
            "dry_run_command": list(self.dry_run_command),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceLoaderDryRun":
        if payload.get("schema") != MACE_LOADER_DRY_RUN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported loader-dry-run schema.")
        result = cls(
            compatibility_probe_digest=str(payload["compatibility_probe_digest"]),
            exposure_backend=MaceExposureBackend(payload["exposure_backend"]),
            target_head_name=str(payload["target_head_name"]),
            replay_head_name=None if payload.get("replay_head_name") is None else str(payload["replay_head_name"]),
            head_order=tuple(str(v) for v in payload["head_order"]),
            validation_head_order=tuple(str(v) for v in payload["validation_head_order"]),
            native_checkpoint_head=str(payload["native_checkpoint_head"]),
            target_train_count_exported=int(payload["target_train_count_exported"]),
            target_train_count_effective=int(payload["target_train_count_effective"]),
            replay_train_count_exported=int(payload["replay_train_count_exported"]),
            replay_train_count_effective=int(payload["replay_train_count_effective"]),
            real_pt_data_ratio_threshold=float(payload["real_pt_data_ratio_threshold"]),
            implicit_target_duplication_factor=int(payload["implicit_target_duplication_factor"]),
            target_validation_count=int(payload["target_validation_count"]),
            replay_validation_count=int(payload["replay_validation_count"]),
            dry_run_command=tuple(str(v) for v in payload["dry_run_command"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Loader-dry-run digest mismatch.")
        return result


def emulate_mace_v0316_loader_dry_run(
    *,
    compatibility_probe: MaceSourceProbe,
    target_train_count: int,
    target_validation_count: int,
    replay_train_count: int = 0,
    replay_validation_count: int = 0,
    real_pt_data_ratio_threshold: float = 0.1,
    checkpoint_policy: MaceCheckpointControlPolicy | None = None,
    config_path: str = "mace_config.yaml",
) -> MaceLoaderDryRun:
    if not compatibility_probe.fixed_file_adapter_supported:
        raise TrainingDataInputError("MACE source probe does not support the fixed-file adapter.")
    active = MaceCheckpointControlPolicy() if checkpoint_policy is None else checkpoint_policy
    if target_train_count <= 0 or target_validation_count <= 0:
        raise TrainingDataInputError("Target train and validation counts must be positive.")
    if replay_train_count < 0 or replay_validation_count < 0:
        raise TrainingDataInputError("Replay counts must be nonnegative.")
    if real_pt_data_ratio_threshold < 0.0:
        raise TrainingDataInputError("real_pt_data_ratio_threshold must be nonnegative.")
    if replay_train_count:
        ratio = target_train_count / replay_train_count
        factor = 1
        if ratio < real_pt_data_ratio_threshold:
            if ratio <= 0.0:
                raise TrainingDataInputError("Target/replay ratio is undefined.")
            factor += int(real_pt_data_ratio_threshold / ratio)
        head_order = (active.replay_head_name, active.target_head_name)
        valid_order = (active.replay_head_name, active.target_head_name)
        replay_head = active.replay_head_name
    else:
        factor = 1
        head_order = (active.target_head_name,)
        valid_order = (active.target_head_name,)
        replay_head = None
    return MaceLoaderDryRun(
        compatibility_probe_digest=compatibility_probe.content_digest,
        exposure_backend=MaceExposureBackend.NATIVE_MACE_FIXED,
        target_head_name=active.target_head_name,
        replay_head_name=replay_head,
        head_order=head_order,
        validation_head_order=valid_order,
        native_checkpoint_head=active.target_head_name,
        target_train_count_exported=int(target_train_count),
        target_train_count_effective=int(target_train_count) * factor,
        replay_train_count_exported=int(replay_train_count),
        replay_train_count_effective=int(replay_train_count),
        real_pt_data_ratio_threshold=float(real_pt_data_ratio_threshold),
        implicit_target_duplication_factor=factor,
        target_validation_count=int(target_validation_count),
        replay_validation_count=int(replay_validation_count),
        dry_run_command=("mace_run_train", "--config", str(config_path), "--dry_run"),
    )


# ---------------------------------------------------------------------------
# Runtime warning compatibility handling
# ---------------------------------------------------------------------------

MACE_RUNTIME_COMPATIBILITY_SCHEMA = "mdstats.mace-runtime-compatibility.v2"
MACE_TORCHSCRIPT_DEPRECATION_CODE = "mace_legacy_torchscript_deprecation"

_TORCHSCRIPT_MESSAGE = re.compile(
    r"^`torch\.jit\.(?P<api>[A-Za-z_][A-Za-z0-9_]*)` is deprecated\. "
    r"Please switch to `torch\.(?:compile|export)`(?: or `torch\.export`)?\.$"
)
_ACTIVE_CAPTURE: ContextVar["_CaptureState | None"] = ContextVar(
    "mdstats_mace_warning_capture", default=None
)
_EMITTED_SIGNATURES: set[tuple[Any, ...]] = set()
_EMITTED_LOCK = Lock()
_CAMPAIGN_CAPTURE_LOCK = Lock()
_CAMPAIGN_CAPTURE_STATE: "_CaptureState | None" = None


class _CapturedLogState:
    __slots__ = ("records", "lock")

    def __init__(self) -> None:
        self.records: list[logging.LogRecord] = []
        self.lock = Lock()

    def add(self, record: logging.LogRecord) -> None:
        with self.lock:
            self.records.append(record)


class MaceRuntimeCompatibilityWarning(FutureWarning):
    """One consolidated warning for an observed legacy MACE TorchScript path."""


def _distribution_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _torch_version() -> str | None:
    try:
        import torch

        return str(torch.__version__)
    except Exception:  # pragma: no cover - broken optional runtime
        return None


def _torchscript_api(item: warnings.WarningMessage) -> str | None:
    if not issubclass(item.category, DeprecationWarning):
        return None
    match = _TORCHSCRIPT_MESSAGE.fullmatch(str(item.message))
    if match is None:
        return None
    normalized = str(Path(item.filename)).replace("\\", "/")
    if "/torch/jit/" not in normalized:
        return None
    return f"torch.jit.{match.group('api')}"


def _replay_warning(item: warnings.WarningMessage) -> None:
    warnings.warn_explicit(
        message=item.message,
        category=item.category,
        filename=item.filename,
        lineno=item.lineno,
        source=getattr(item, "source", None),
    )


def _upstream_warning_origin(item: warnings.WarningMessage) -> str | None:
    """Return the upstream family for warnings that mdstats may condense.

    The classification is intentionally narrow: warnings must originate in the
    installed MACE/PyTorch packages, except for the well-known TorchScript AST
    warning which is emitted through Python's stdlib ``ast.py`` while TorchScript
    is compiling a MACE module.  Unrelated application/library warnings are
    replayed unchanged.
    """

    normalized = str(Path(item.filename)).replace("\\", "/")
    lowered = normalized.lower()
    if "/site-packages/mace/" in lowered or "/mace/" in lowered:
        return "mace"
    if "/site-packages/torch/" in lowered or "/torch/" in lowered:
        return "torch"
    if Path(normalized).name == "ast.py" and str(item.message).startswith(
        "The TorchScript type system doesn't support"
    ):
        return "torch"
    return None


def _upstream_log_origin(record: logging.LogRecord) -> str | None:
    """Return the upstream family for WARNING+ logging records to condense.

    MACE 0.3.x uses the root logger for several compatibility messages, so the
    logger name alone is insufficient.  The emitting source pathname is the
    primary authority; logger-name matching is an additive fallback for package
    loggers.  INFO/DEBUG records are never intercepted.
    """

    if int(record.levelno) < logging.WARNING:
        return None
    normalized = str(Path(getattr(record, "pathname", ""))).replace("\\", "/")
    lowered = normalized.lower()
    logger_name = str(getattr(record, "name", "")).lower()
    if "/mace/" in lowered or logger_name == "mace" or logger_name.startswith("mace."):
        return "mace"
    if "/torch/" in lowered or logger_name == "torch" or logger_name.startswith("torch."):
        return "torch"
    return None


def _compact_log_source(record: logging.LogRecord, origin: str) -> str:
    normalized = str(Path(getattr(record, "pathname", ""))).replace("\\", "/")
    marker = f"/{origin}/"
    lowered = normalized.lower()
    index = lowered.rfind(marker)
    if index >= 0:
        return normalized[index + 1 :]
    return Path(normalized).name or "<unknown>"


def _compact_message_text(message: str) -> str:
    message = " ".join(str(message).split())
    if message.startswith("To copy construct from a tensor, it is recommended"):
        return "tensor-copy construction warning"
    if message.startswith("The TorchScript type system doesn't support instance-level annotations"):
        return "TorchScript instance-annotation warning"
    if "TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD" in message and "weights_only=False" in message:
        return "TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD forces weights_only=False"
    if message.startswith("Default dtype ") and " does not match model dtype " in message and "converting models to" in message:
        return message
    return message


def _logging_fingerprint(record: logging.LogRecord, origin: str) -> tuple[str, str, str, str]:
    return (
        origin,
        f"logging.{logging.getLevelName(record.levelno)}",
        _compact_log_source(record, origin),
        _compact_message_text(record.getMessage()),
    )


@contextmanager
def _capture_upstream_logging() -> Iterator[_CapturedLogState]:
    """Capture/suppress MACE/PyTorch WARNING logs for one outer warning domain.

    Python warning interception and logging are separate mechanisms.  This scope
    installs a temporary LogRecord factory so package/root-logger warnings are
    recorded, and temporarily intercepts ``Logger.handle`` so matching WARNING+
    records cannot leak through either existing or newly installed handlers.
    Non-MACE/non-PyTorch log records preserve the original logging path unchanged.
    """

    state = _CapturedLogState()
    previous_factory = logging.getLogRecordFactory()
    previous_handle = logging.Logger.handle

    def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = previous_factory(*args, **kwargs)
        if _upstream_log_origin(record) is not None:
            state.add(record)
        return record

    def handle(logger: logging.Logger, record: logging.LogRecord) -> None:
        if _upstream_log_origin(record) is not None:
            return
        previous_handle(logger, record)

    logging.setLogRecordFactory(factory)
    logging.Logger.handle = handle  # type: ignore[assignment]
    try:
        yield state
    finally:
        logging.Logger.handle = previous_handle  # type: ignore[assignment]
        logging.setLogRecordFactory(previous_factory)


def _compact_warning_source(item: warnings.WarningMessage, origin: str) -> str:
    normalized = str(Path(item.filename)).replace("\\", "/")
    marker = f"/{origin}/"
    lowered = normalized.lower()
    index = lowered.rfind(marker)
    if index >= 0:
        return normalized[index + 1 :]
    return Path(normalized).name


def _compact_warning_message(item: warnings.WarningMessage) -> str:
    api = _torchscript_api(item)
    if api is not None:
        return f"{api} deprecated"
    return _compact_message_text(str(item.message))


def _warning_fingerprint(item: warnings.WarningMessage, origin: str) -> tuple[str, str, str, str]:
    return (
        origin,
        item.category.__name__,
        _compact_warning_source(item, origin),
        _compact_warning_message(item),
    )


@dataclass(frozen=True, slots=True)
class MaceRuntimeCompatibilityRecord:
    """Observed compatibility evidence from one outer MACE warning scope."""

    operations: tuple[str, ...]
    torch_version: str | None
    mace_version: str | None
    torchscript_apis: tuple[str, ...]
    raw_warning_count: int
    warning_codes: tuple[str, ...]
    upstream_warning_count: int = 0
    upstream_warning_groups: tuple[tuple[str, str, str, str, int], ...] = ()
    schema: str = MACE_RUNTIME_COMPATIBILITY_SCHEMA

    @property
    def legacy_torchscript_observed(self) -> bool:
        return bool(self.torchscript_apis)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "operations": list(self.operations),
            "torch_version": self.torch_version,
            "mace_version": self.mace_version,
            "torchscript_apis": list(self.torchscript_apis),
            "raw_warning_count": self.raw_warning_count,
            "warning_codes": list(self.warning_codes),
            "upstream_warning_count": self.upstream_warning_count,
            "upstream_warning_groups": [
                {
                    "origin": origin,
                    "category": category,
                    "source": source,
                    "message": message,
                    "count": count,
                }
                for origin, category, source, message, count in self.upstream_warning_groups
            ],
            "legacy_torchscript_observed": self.legacy_torchscript_observed,
        }


@dataclass(slots=True)
class _CaptureState:
    operations: set[str]
    record: MaceRuntimeCompatibilityRecord | None = None
    operation_lock: Lock = dataclass_field(default_factory=Lock, repr=False)

    def add_operation(self, operation: str) -> None:
        with self.operation_lock:
            self.operations.add(operation)

    def operation_snapshot(self) -> tuple[str, ...]:
        with self.operation_lock:
            return tuple(sorted(self.operations))


class MaceRuntimeCompatibilityCapture:
    """Handle yielded by :func:`mace_runtime_warning_scope`."""

    __slots__ = ("_state",)

    def __init__(self, state: _CaptureState) -> None:
        self._state = state

    @property
    def record(self) -> MaceRuntimeCompatibilityRecord:
        record = self._state.record
        if record is None:
            raise RuntimeError("MACE runtime compatibility record is available after the scope exits.")
        return record


def format_mace_runtime_compatibility_summary(record: MaceRuntimeCompatibilityRecord) -> str:
    """Return the one-line normalized summary for a captured warning domain."""
    operations = ", ".join(record.operations)
    runtime = (
        f"PyTorch {record.torch_version or 'unknown'} / "
        f"mace-torch {record.mace_version or 'unknown'}"
    )
    groups = []
    for origin, category, source, message, count in record.upstream_warning_groups:
        groups.append(f"{count}x {origin}:{category} [{source}] {message}")
    detail = "; ".join(groups)
    if len(detail) > 1800:
        detail = detail[:1797] + "..."
    legacy = (
        f"mdstats observed {record.raw_warning_count} legacy TorchScript deprecation warning(s) "
        if record.raw_warning_count
        else "mdstats observed upstream runtime warnings "
    )
    return (
        legacy
        + f"during {operations}; condensed {record.upstream_warning_count} total MACE/PyTorch "
        + f"warning(s) into {len(record.upstream_warning_groups)} unique group(s): {detail}. "
        + f"Runtime: {runtime}. Non-MACE/non-PyTorch warnings were preserved."
    )


def _emit_once(record: MaceRuntimeCompatibilityRecord) -> None:
    if not record.upstream_warning_groups:
        return
    signature = (
        record.torch_version,
        record.mace_version,
        tuple(group[:4] for group in record.upstream_warning_groups),
    )
    with _EMITTED_LOCK:
        if signature in _EMITTED_SIGNATURES:
            return
        _EMITTED_SIGNATURES.add(signature)
    warnings.warn(
        format_mace_runtime_compatibility_summary(record),
        MaceRuntimeCompatibilityWarning,
        stacklevel=4,
    )


@contextmanager
def mace_runtime_warning_scope(
    operation: str,
    *,
    emit_consolidated_warning: bool = True,
    campaign_wide: bool = False,
) -> Iterator[MaceRuntimeCompatibilityCapture]:
    """Capture and consolidate exact upstream TorchScript deprecations.

    Scopes may be nested.  Only the outermost scope owns warning interception;
    nested operation names are merged into the resulting record.
    """

    normalized_operation = str(operation).strip()
    if not normalized_operation:
        raise ValueError("operation must be a non-empty string.")

    active = _ACTIVE_CAPTURE.get()
    if active is not None:
        active.add_operation(normalized_operation)
        yield MaceRuntimeCompatibilityCapture(active)
        return

    # A campaign-wide owner is additionally visible to worker threads whose
    # ContextVar context does not inherit the main-thread active capture.
    global _CAMPAIGN_CAPTURE_STATE
    with _CAMPAIGN_CAPTURE_LOCK:
        process_active = _CAMPAIGN_CAPTURE_STATE
        if process_active is not None:
            if campaign_wide:
                raise RuntimeError("A campaign-wide MACE warning domain is already active.")
            process_active.add_operation(normalized_operation)
    if process_active is not None:
        yield MaceRuntimeCompatibilityCapture(process_active)
        return

    state = _CaptureState(operations={normalized_operation})
    owns_campaign_domain = bool(campaign_wide)
    if owns_campaign_domain:
        with _CAMPAIGN_CAPTURE_LOCK:
            if _CAMPAIGN_CAPTURE_STATE is not None:
                raise RuntimeError("A campaign-wide MACE warning domain is already active.")
            _CAMPAIGN_CAPTURE_STATE = state
    token = _ACTIVE_CAPTURE.set(state)
    captured: list[warnings.WarningMessage]
    pending_error: tuple[type[BaseException], BaseException, Any] | None = None
    log_state: _CapturedLogState
    try:
        with _capture_upstream_logging() as log_state, warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter("always", DeprecationWarning)
            # Two high-volume UserWarning families are emitted repeatedly while
            # MACE constructs/converts calculators (especially CuEq/TorchScript
            # qualification).  Force only these known upstream families through
            # the capture layer so they can be grouped, without changing the
            # caller's filtering semantics for unrelated UserWarnings.
            warnings.filterwarnings(
                "always",
                message=r"^To copy construct from a tensor, it is recommended",
                category=UserWarning,
            )
            warnings.filterwarnings(
                "always",
                message=r"^The TorchScript type system doesn't support instance-level annotations",
                category=UserWarning,
            )
            try:
                yield MaceRuntimeCompatibilityCapture(state)
            except BaseException:
                pending_error = sys.exc_info()  # type: ignore[assignment]
            finally:
                captured = list(observed)
    finally:
        _ACTIVE_CAPTURE.reset(token)
        if owns_campaign_domain:
            with _CAMPAIGN_CAPTURE_LOCK:
                if _CAMPAIGN_CAPTURE_STATE is state:
                    _CAMPAIGN_CAPTURE_STATE = None

    apis: list[str] = []
    unrelated: list[warnings.WarningMessage] = []
    grouped: dict[tuple[str, str, str, str], int] = {}
    upstream_count = 0
    for item in captured:
        api = _torchscript_api(item)
        if api is not None:
            apis.append(api)
        origin = _upstream_warning_origin(item)
        if origin is None:
            unrelated.append(item)
            continue
        fingerprint = _warning_fingerprint(item, origin)
        grouped[fingerprint] = grouped.get(fingerprint, 0) + 1
        upstream_count += 1

    for log_record in log_state.records:
        origin = _upstream_log_origin(log_record)
        if origin is None:
            continue
        fingerprint = _logging_fingerprint(log_record, origin)
        grouped[fingerprint] = grouped.get(fingerprint, 0) + 1
        upstream_count += 1

    unique_apis = tuple(sorted(set(apis)))
    upstream_groups = tuple(
        (*fingerprint, count)
        for fingerprint, count in sorted(grouped.items(), key=lambda value: value[0])
    )
    warning_codes: list[str] = []
    if unique_apis:
        # Preserve the historical public compatibility code exactly. Broader
        # upstream warning aggregation is exposed through the additive
        # ``upstream_warning_*`` fields instead of changing this tuple.
        warning_codes.append(MACE_TORCHSCRIPT_DEPRECATION_CODE)
    record = MaceRuntimeCompatibilityRecord(
        operations=state.operation_snapshot(),
        torch_version=_torch_version(),
        mace_version=_distribution_version("mace-torch"),
        torchscript_apis=unique_apis,
        raw_warning_count=len(apis),
        warning_codes=tuple(warning_codes),
        upstream_warning_count=upstream_count,
        upstream_warning_groups=upstream_groups,
    )
    state.record = record

    warning_processing_error: BaseException | None = None
    try:
        for item in unrelated:
            _replay_warning(item)
        if emit_consolidated_warning:
            _emit_once(record)
    except BaseException as error:
        warning_processing_error = error

    if pending_error is not None:
        _, error, traceback = pending_error
        if warning_processing_error is not None and hasattr(error, "add_note"):
            error.add_note(
                "A warning raised while mdstats was processing MACE runtime "
                f"compatibility evidence: {warning_processing_error!r}"
            )
        raise error.with_traceback(traceback)
    if warning_processing_error is not None:
        raise warning_processing_error


def mace_runtime_warning_handled(operation: str):
    """Decorate one synchronous MACE operation with the compatibility scope."""

    normalized_operation = str(operation).strip()
    if not normalized_operation:
        raise ValueError("operation must be a non-empty string.")

    def decorator(function: Any) -> Any:
        @wraps(function)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            with mace_runtime_warning_scope(normalized_operation):
                return function(*args, **kwargs)

        return wrapped

    return decorator
