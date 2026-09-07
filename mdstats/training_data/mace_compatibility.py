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
import json
import logging
import math
import os
import re
import sys
import warnings

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)

MACE_COMPATIBILITY_POLICY_SCHEMA = "mdstats.mace-compatibility-policy.v2"
MACE_SOURCE_PROBE_SCHEMA = "mdstats.mace-source-probe.v2"
MACE_COMPATIBILITY_POLICY_LEGACY_SCHEMA = "mdstats.mace-compatibility-policy.v1"
MACE_SOURCE_PROBE_LEGACY_SCHEMA = "mdstats.mace-source-probe.v1"
MACE_CHECKPOINT_CONTROL_POLICY_SCHEMA = "mdstats.mace-checkpoint-control-policy.v1"
MACE_LOADER_DRY_RUN_SCHEMA = "mdstats.mace-loader-dry-run.v1"
MACE_COMPATIBILITY_POLICY_VERSION = "mdstats.mlff-data8.mace-compatibility.2026-09.v2"

# This revision is an execution identity, not a second method registry.  It is
# carried by the existing MACE compatibility/currentness owners and by the
# process-local launch authority below.  A new value must invalidate evidence
# whose actual loader/loss semantics may differ from the current wrapper.
MACE_EXECUTION_SEMANTICS_VERSION = "mdstats.mace-execution-semantics.2026-09.v1"
MACE_REPLAY_FORCE_MH_FT_LR = True
MACE_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD = 0.0
MACE_EXECUTION_AUTHORITY_SCHEMA = "mdstats.mace-execution-authority.v1"
MACE_EXECUTION_EVIDENCE_SCHEMA = "mdstats.mace-execution-evidence.v1"
MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE = "MDSTATS_MACE_EXECUTION_AUTHORITY"

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
    execution_semantics_version: str | None = MACE_EXECUTION_SEMANTICS_VERSION
    serialization_schema: str = MACE_COMPATIBILITY_POLICY_SCHEMA
    _historical_payload: dict[str, Any] | None = dataclass_field(
        default=None, init=False, repr=False, compare=False
    )
    _historical_policy_digest: str | None = dataclass_field(
        default=None, init=False, repr=False, compare=False
    )

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
        if self.serialization_schema == MACE_COMPATIBILITY_POLICY_SCHEMA:
            if self.execution_semantics_version != MACE_EXECUTION_SEMANTICS_VERSION:
                raise TrainingDataInputError(
                    "MACE compatibility policy carries an unsupported execution "
                    "semantics revision."
                )
        elif self.serialization_schema == MACE_COMPATIBILITY_POLICY_LEGACY_SCHEMA:
            if self.execution_semantics_version is not None:
                raise TrainingDataInputError(
                    "Historical MACE compatibility records cannot carry current "
                    "execution semantics."
                )
        else:
            raise TrainingDataInputError("Unsupported MACE compatibility schema.")

    def _payload(self) -> dict[str, Any]:
        if self._historical_payload is not None:
            return dict(self._historical_payload)
        return {
            "schema": self.serialization_schema,
            "package_name": self.package_name,
            "package_version": self.package_version,
            "release_tag": self.release_tag,
            "release_commit": self.release_commit,
            "run_train_source_url": self.run_train_source_url,
            "train_source_url": self.train_source_url,
            "multihead_source_url": self.multihead_source_url,
            "policy_version": self.policy_version,
            "execution_semantics_version": self.execution_semantics_version,
        }

    @property
    def policy_digest(self) -> str:
        if self._historical_policy_digest is not None:
            return self._historical_policy_digest
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        if self._historical_payload is not None:
            return {
                **self._historical_payload,
                "policy_digest": self.policy_digest,
            }
        return {**self._payload(), "policy_digest": self.policy_digest}

    @property
    def current_execution_compatible(self) -> bool:
        """Whether this readable record can authorize current MACE execution."""

        return (
            self.serialization_schema == MACE_COMPATIBILITY_POLICY_SCHEMA
            and self.execution_semantics_version == MACE_EXECUTION_SEMANTICS_VERSION
            and self.policy_version == MACE_COMPATIBILITY_POLICY_VERSION
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceCompatibilityPolicy":
        schema = payload.get("schema")
        if schema not in {
            MACE_COMPATIBILITY_POLICY_SCHEMA,
            MACE_COMPATIBILITY_POLICY_LEGACY_SCHEMA,
        }:
            raise TrainingDataSerializationError("Unsupported MACE compatibility schema.")
        if schema == MACE_COMPATIBILITY_POLICY_LEGACY_SCHEMA:
            expected_keys = {
                "schema",
                "package_name",
                "package_version",
                "release_tag",
                "release_commit",
                "run_train_source_url",
                "train_source_url",
                "multihead_source_url",
                "policy_version",
                "policy_digest",
            }
            if set(payload) != expected_keys:
                raise TrainingDataSerializationError(
                    "Historical MACE compatibility record has an unexpected serialized shape."
                )
            historical_payload = {
                key: value for key, value in payload.items() if key != "policy_digest"
            }
            expected_digest = digest(historical_payload)
            if payload["policy_digest"] != expected_digest:
                raise TrainingDataSerializationError(
                    "Historical MACE compatibility digest mismatch."
                )
            result = cls(
                package_name=str(payload["package_name"]),
                package_version=str(payload["package_version"]),
                release_tag=str(payload["release_tag"]),
                release_commit=str(payload["release_commit"]),
                run_train_source_url=str(payload["run_train_source_url"]),
                train_source_url=str(payload["train_source_url"]),
                multihead_source_url=str(payload["multihead_source_url"]),
                policy_version=str(payload["policy_version"]),
                execution_semantics_version=None,
                serialization_schema=MACE_COMPATIBILITY_POLICY_LEGACY_SCHEMA,
            )
            object.__setattr__(result, "_historical_payload", historical_payload)
            object.__setattr__(result, "_historical_policy_digest", expected_digest)
            return result
        result = cls(
            package_name=str(payload["package_name"]),
            package_version=str(payload["package_version"]),
            release_tag=str(payload["release_tag"]),
            release_commit=str(payload["release_commit"]),
            run_train_source_url=str(payload["run_train_source_url"]),
            train_source_url=str(payload["train_source_url"]),
            multihead_source_url=str(payload["multihead_source_url"]),
            policy_version=str(payload["policy_version"]),
            execution_semantics_version=str(payload["execution_semantics_version"]),
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
    multihead_forced_universal_loss_present: bool = False
    multihead_lr_ema_override_present: bool = False
    target_per_head_drop_last_present: bool = False
    target_distributed_sampler_drop_last_present: bool = False
    target_combined_loader_drop_last_present: bool = False
    dry_run_supported: bool = False
    save_all_checkpoints_supported: bool = False
    fixed_file_adapter_supported: bool = False
    evidence_notes: tuple[str, ...] = ()
    serialization_schema: str = MACE_SOURCE_PROBE_SCHEMA
    _historical_payload: dict[str, Any] | None = dataclass_field(
        default=None, init=False, repr=False, compare=False
    )
    _historical_content_digest: str | None = dataclass_field(
        default=None, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in (
            "policy_digest",
            "run_train_sha256",
            "train_sha256",
            "multihead_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.serialization_schema == MACE_SOURCE_PROBE_SCHEMA:
            expected = (
                self.pt_head_sorted_first
                and self.target_validation_head_is_last
                and self.native_checkpoint_uses_last_validation_head
                and self.implicit_target_duplication_present
                and self.multihead_forced_universal_loss_present
                and self.multihead_lr_ema_override_present
                and self.target_per_head_drop_last_present
                and self.target_distributed_sampler_drop_last_present
                and self.target_combined_loader_drop_last_present
                and self.dry_run_supported
                and self.save_all_checkpoints_supported
            )
        elif self.serialization_schema == MACE_SOURCE_PROBE_LEGACY_SCHEMA:
            # The pre-repair probe did not qualify the four execution behaviors
            # repaired in this lineage.  Its support bit is checked only against
            # the historical fields; it is never promoted to current evidence.
            expected = (
                self.pt_head_sorted_first
                and self.target_validation_head_is_last
                and self.native_checkpoint_uses_last_validation_head
                and self.implicit_target_duplication_present
                and self.dry_run_supported
                and self.save_all_checkpoints_supported
            )
        else:
            raise TrainingDataInputError("Unsupported MACE source-probe schema.")
        if self.fixed_file_adapter_supported != expected:
            raise TrainingDataInputError("MACE source-probe support state is inconsistent.")
        object.__setattr__(self, "evidence_notes", tuple(str(v) for v in self.evidence_notes))

    def _payload(self) -> dict[str, Any]:
        if self._historical_payload is not None:
            return dict(self._historical_payload)
        return {
            "schema": self.serialization_schema,
            "policy_digest": self.policy_digest,
            "run_train_sha256": self.run_train_sha256,
            "train_sha256": self.train_sha256,
            "multihead_sha256": self.multihead_sha256,
            "pt_head_sorted_first": self.pt_head_sorted_first,
            "target_validation_head_is_last": self.target_validation_head_is_last,
            "native_checkpoint_uses_last_validation_head": self.native_checkpoint_uses_last_validation_head,
            "implicit_target_duplication_present": self.implicit_target_duplication_present,
            "multihead_forced_universal_loss_present": self.multihead_forced_universal_loss_present,
            "multihead_lr_ema_override_present": self.multihead_lr_ema_override_present,
            "target_per_head_drop_last_present": self.target_per_head_drop_last_present,
            "target_distributed_sampler_drop_last_present": self.target_distributed_sampler_drop_last_present,
            "target_combined_loader_drop_last_present": self.target_combined_loader_drop_last_present,
            "dry_run_supported": self.dry_run_supported,
            "save_all_checkpoints_supported": self.save_all_checkpoints_supported,
            "fixed_file_adapter_supported": self.fixed_file_adapter_supported,
            "evidence_notes": list(self.evidence_notes),
        }

    @property
    def content_digest(self) -> str:
        if self._historical_content_digest is not None:
            return self._historical_content_digest
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        if self._historical_payload is not None:
            return {
                **self._historical_payload,
                "content_digest": self.content_digest,
            }
        return {**self._payload(), "content_digest": self.content_digest}

    @property
    def current_execution_compatible(self) -> bool:
        """Whether this readable probe qualifies the repaired execution seam."""

        return (
            self.serialization_schema == MACE_SOURCE_PROBE_SCHEMA
            and self.multihead_forced_universal_loss_present
            and self.multihead_lr_ema_override_present
            and self.target_per_head_drop_last_present
            and self.target_distributed_sampler_drop_last_present
            and self.target_combined_loader_drop_last_present
            and self.fixed_file_adapter_supported
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceSourceProbe":
        schema = payload.get("schema")
        if schema not in {MACE_SOURCE_PROBE_SCHEMA, MACE_SOURCE_PROBE_LEGACY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported MACE source-probe schema.")
        if schema == MACE_SOURCE_PROBE_LEGACY_SCHEMA:
            expected_keys = {
                "schema",
                "policy_digest",
                "run_train_sha256",
                "train_sha256",
                "multihead_sha256",
                "pt_head_sorted_first",
                "target_validation_head_is_last",
                "native_checkpoint_uses_last_validation_head",
                "implicit_target_duplication_present",
                "dry_run_supported",
                "save_all_checkpoints_supported",
                "fixed_file_adapter_supported",
                "evidence_notes",
                "content_digest",
            }
            if set(payload) != expected_keys:
                raise TrainingDataSerializationError(
                    "Historical MACE source-probe record has an unexpected serialized shape."
                )
            historical_payload = {
                key: value for key, value in payload.items() if key != "content_digest"
            }
            expected_digest = digest(historical_payload)
            if payload["content_digest"] != expected_digest:
                raise TrainingDataSerializationError(
                    "Historical MACE source-probe digest mismatch."
                )
            result = cls(
                policy_digest=str(payload["policy_digest"]),
                run_train_sha256=str(payload["run_train_sha256"]),
                train_sha256=str(payload["train_sha256"]),
                multihead_sha256=str(payload["multihead_sha256"]),
                pt_head_sorted_first=bool(payload["pt_head_sorted_first"]),
                target_validation_head_is_last=bool(
                    payload["target_validation_head_is_last"]
                ),
                native_checkpoint_uses_last_validation_head=bool(
                    payload["native_checkpoint_uses_last_validation_head"]
                ),
                implicit_target_duplication_present=bool(
                    payload["implicit_target_duplication_present"]
                ),
                dry_run_supported=bool(payload["dry_run_supported"]),
                save_all_checkpoints_supported=bool(
                    payload["save_all_checkpoints_supported"]
                ),
                fixed_file_adapter_supported=bool(
                    payload["fixed_file_adapter_supported"]
                ),
                evidence_notes=tuple(
                    str(v) for v in payload.get("evidence_notes", ())
                ),
                serialization_schema=MACE_SOURCE_PROBE_LEGACY_SCHEMA,
            )
            object.__setattr__(result, "_historical_payload", historical_payload)
            object.__setattr__(result, "_historical_content_digest", expected_digest)
            return result
        result = cls(
            policy_digest=str(payload["policy_digest"]),
            run_train_sha256=str(payload["run_train_sha256"]),
            train_sha256=str(payload["train_sha256"]),
            multihead_sha256=str(payload["multihead_sha256"]),
            pt_head_sorted_first=bool(payload["pt_head_sorted_first"]),
            target_validation_head_is_last=bool(payload["target_validation_head_is_last"]),
            native_checkpoint_uses_last_validation_head=bool(payload["native_checkpoint_uses_last_validation_head"]),
            implicit_target_duplication_present=bool(payload["implicit_target_duplication_present"]),
            multihead_forced_universal_loss_present=bool(
                payload["multihead_forced_universal_loss_present"]
            ),
            multihead_lr_ema_override_present=bool(
                payload["multihead_lr_ema_override_present"]
            ),
            target_per_head_drop_last_present=bool(
                payload["target_per_head_drop_last_present"]
            ),
            target_distributed_sampler_drop_last_present=bool(
                payload["target_distributed_sampler_drop_last_present"]
            ),
            target_combined_loader_drop_last_present=bool(
                payload["target_combined_loader_drop_last_present"]
            ),
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
    """Verify the exact v0.3.16 behaviors required by current execution.

    The probe deliberately records the upstream defects that the qualified
    wrapper is allowed to repair.  A future source shape that removes or moves
    one of those branches is not silently treated as equivalent: the wrapper
    must be requalified against that source first.
    """

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
    forced_universal = bool(
        re.search(
            r"if\s+args\.multiheads_finetuning\s*:.*?"
            r"args\.loss\s*=\s*[\"']universal[\"']",
            run_train_text,
            flags=re.DOTALL,
        )
    )
    lr_ema_override = bool(
        re.search(
            r"if\s+not\s+args\.force_mh_ft_lr\s*:.*?"
            r"args\.lr\s*=\s*0\.0001.*?"
            r"args\.ema\s*=\s*True.*?"
            r"args\.ema_decay\s*=\s*0\.99999",
            run_train_text,
            flags=re.DOTALL,
        )
    )
    per_head_drop_last = bool(
        re.search(
            r"train_loader_head\s*=.*?drop_last\s*=\s*\(\s*not\s+args\.lbfgs\s*\)",
            run_train_text,
            flags=re.DOTALL,
        )
    )
    distributed_sampler_drop_last = bool(
        re.search(
            r"DistributedSampler\(.*?drop_last\s*=\s*\(\s*not\s+args\.lbfgs\s*\)",
            run_train_text,
            flags=re.DOTALL,
        )
    )
    combined_drop_last = bool(
        re.search(
            r"train_loader\s*=.*?drop_last\s*=\s*\(\s*train_sampler\s+is\s+None\s+and\s+not\s+args\.lbfgs\s*\)",
            run_train_text,
            flags=re.DOTALL,
        )
    )
    dry_run = "if args.dry_run" in run_train_text
    save_all = "save_all_checkpoints=args.save_all_checkpoints" in run_train_text and "if save_all_checkpoints" in train_text
    pt_prepare = "def prepare_pt_head" in multihead_text and "pt_valid_file" in multihead_text
    target_last = pt_first and pt_prepare
    supported = (
        pt_first
        and target_last
        and last_valid
        and duplication
        and forced_universal
        and lr_ema_override
        and per_head_drop_last
        and distributed_sampler_drop_last
        and combined_drop_last
        and dry_run
        and save_all
    )
    return MaceSourceProbe(
        policy_digest=active.policy_digest,
        run_train_sha256=run_digest,
        train_sha256=train_digest,
        multihead_sha256=multi_digest,
        pt_head_sorted_first=pt_first,
        target_validation_head_is_last=target_last,
        native_checkpoint_uses_last_validation_head=last_valid,
        implicit_target_duplication_present=duplication,
        multihead_forced_universal_loss_present=forced_universal,
        multihead_lr_ema_override_present=lr_ema_override,
        target_per_head_drop_last_present=per_head_drop_last,
        target_distributed_sampler_drop_last_present=distributed_sampler_drop_last,
        target_combined_loader_drop_last_present=combined_drop_last,
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


def mace_frame_uid_set_digest(frame_uids: Any) -> str:
    """Digest an unordered, duplicate-free set of exported frame UIDs."""

    values = tuple(str(value) for value in frame_uids)
    if any(not value.strip() or value == "None" for value in values):
        raise TrainingDataInputError(
            "MACE execution frame identity requires non-empty UID values."
        )
    if not values or len(set(values)) != len(values):
        raise TrainingDataInputError(
            "MACE execution frame identity requires a unique non-empty UID set."
        )
    return digest({"frame_uids": sorted(values)})


def _execution_integer(
    value: Any,
    *,
    name: str,
    minimum: int,
) -> int:
    """Require a JSON-number integer without silently truncating a float."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TrainingDataInputError(f"MACE execution authority {name} must be an integer.")
    if not math.isfinite(float(value)):
        raise TrainingDataInputError(
            f"MACE execution authority {name} must be finite."
        )
    result = int(value)
    if result != value or result < minimum:
        qualifier = "positive" if minimum > 0 else "nonnegative"
        raise TrainingDataInputError(
            f"MACE execution authority {name} must be a {qualifier} integer."
        )
    return result


def _normalize_mace_execution_authority(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the process-local execution transport without trusting it."""

    if payload.get("schema") != MACE_EXECUTION_AUTHORITY_SCHEMA:
        raise TrainingDataInputError(
            "Unsupported MACE execution-authority schema."
        )
    if payload.get("execution_semantics_version") != MACE_EXECUTION_SEMANTICS_VERSION:
        raise TrainingDataInputError(
            "MACE execution authority carries an unsupported semantics revision."
        )
    role = str(payload.get("role", ""))
    if role not in {"target_size", "post_selection"}:
        raise TrainingDataInputError("MACE execution authority role is unsupported.")
    config_digest = validate_digest(
        str(payload.get("config_digest", "")), name="config_digest"
    )
    method_identity_digest = payload.get("method_identity_digest")
    if method_identity_digest is not None:
        method_identity_digest = validate_digest(
            str(method_identity_digest), name="method_identity_digest"
        )
    loss_family = str(payload.get("loss_family", ""))
    if loss_family != MACE_EXECUTABLE_LOSS_FAMILY:
        raise TrainingDataInputError(
            "MACE execution authority must request the native weighted loss family."
        )
    learning_rate = float(payload.get("learning_rate"))
    if not math.isfinite(learning_rate) or learning_rate <= 0.0:
        raise TrainingDataInputError("MACE execution authority LR is invalid.")
    ema = payload.get("ema")
    if not isinstance(ema, bool):
        raise TrainingDataInputError("MACE execution authority EMA flag is invalid.")
    ema_decay = payload.get("ema_decay")
    if ema:
        if ema_decay is None:
            raise TrainingDataInputError(
                "MACE execution authority requires EMA decay when EMA is enabled."
            )
        ema_decay = float(ema_decay)
        if not math.isfinite(ema_decay) or not 0.0 < ema_decay < 1.0:
            raise TrainingDataInputError("MACE execution authority EMA decay is invalid.")
    else:
        ema_decay = None
    multihead = payload.get("multiheads_finetuning")
    if not isinstance(multihead, bool):
        raise TrainingDataInputError(
            "MACE execution authority multihead flag is invalid."
        )
    force_mh_ft_lr = payload.get("force_mh_ft_lr")
    ratio_threshold = payload.get("real_pt_data_ratio_threshold")
    if multihead:
        if force_mh_ft_lr is not MACE_REPLAY_FORCE_MH_FT_LR:
            raise TrainingDataInputError(
                "Replay execution must explicitly force its authenticated LR/EMA."
            )
        if ratio_threshold is None or not math.isclose(
            float(ratio_threshold),
            MACE_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD,
            rel_tol=0.0,
            abs_tol=0.0,
        ):
            raise TrainingDataInputError(
                "Replay execution must explicitly disable MACE target duplication."
            )
        ratio_threshold = float(ratio_threshold)
    else:
        force_mh_ft_lr = None
        ratio_threshold = None
    target_count = _execution_integer(
        payload.get("target_train_count"), name="target count", minimum=1
    )
    replay_count = _execution_integer(
        payload.get("replay_train_count", 0), name="replay count", minimum=0
    )
    if multihead and replay_count <= 0:
        raise TrainingDataInputError(
            "Replay execution authority requires a non-empty replay training set."
        )
    batch_size = _execution_integer(
        payload.get("batch_size"), name="batch size", minimum=1
    )
    target_updates = payload.get("target_updates_per_epoch")
    if role == "target_size":
        target_updates = _execution_integer(
            target_updates, name="target updates per epoch", minimum=1
        )
        if replay_count != 0:
            raise TrainingDataInputError(
                "Target-size execution authority cannot carry replay samples."
            )
        if payload.get("target_drop_last") is not False:
            raise TrainingDataInputError(
                "Target-size execution authority requires drop_last=False."
            )
        if payload.get("distributed_allowed") is not False:
            raise TrainingDataInputError(
                "Target-size execution authority must forbid distributed samplers."
            )
    else:
        target_updates = (
            None
            if target_updates is None
            else _execution_integer(
                target_updates, name="target updates per epoch", minimum=1
            )
        )
        if payload.get("target_drop_last") is not None:
            raise TrainingDataInputError(
                "Post-selection execution authority cannot claim target-size loader semantics."
            )
    for name in ("target_frame_uid_set_digest", "replay_frame_uid_set_digest"):
        value = payload.get(name)
        if value is not None:
            payload_value = validate_digest(str(value), name=name)
        else:
            payload_value = None
        # The local variable is assigned into the normalized payload below.
        if name == "target_frame_uid_set_digest":
            target_uid_digest = payload_value
        else:
            replay_uid_digest = payload_value
    source_probe_digest = payload.get("source_probe_digest")
    if source_probe_digest is not None:
        source_probe_digest = validate_digest(
            str(source_probe_digest), name="source_probe_digest"
        )
    distributed_allowed = payload.get("distributed_allowed")
    if not isinstance(distributed_allowed, bool):
        raise TrainingDataInputError(
            "MACE execution authority distributed_allowed flag is invalid."
        )
    target_head_name = str(payload.get("target_head_name", "target_head"))
    replay_head_name = str(payload.get("replay_head_name", "pt_head"))
    if not target_head_name.strip() or not replay_head_name.strip():
        raise TrainingDataInputError("MACE execution authority head names are invalid.")
    result: dict[str, Any] = {
        "schema": MACE_EXECUTION_AUTHORITY_SCHEMA,
        "execution_semantics_version": MACE_EXECUTION_SEMANTICS_VERSION,
        "role": role,
        "config_digest": config_digest,
        "method_identity_digest": method_identity_digest,
        "loss_family": loss_family,
        "learning_rate": learning_rate,
        "ema": ema,
        "ema_decay": ema_decay,
        "multiheads_finetuning": multihead,
        "force_mh_ft_lr": force_mh_ft_lr,
        "real_pt_data_ratio_threshold": ratio_threshold,
        "target_train_count": target_count,
        "replay_train_count": replay_count,
        # This is deliberately fixed: replay balancing is never implemented by
        # silently duplicating target frames.
        "target_duplication_factor": 1,
        "batch_size": batch_size,
        "target_updates_per_epoch": target_updates,
        "target_drop_last": (
            False if role == "target_size" else None
        ),
        "distributed_allowed": distributed_allowed,
        "target_frame_uid_set_digest": target_uid_digest,
        "replay_frame_uid_set_digest": replay_uid_digest,
        "target_head_name": target_head_name,
        "replay_head_name": replay_head_name,
        "source_probe_digest": source_probe_digest,
    }
    if "resolved_evidence" in payload and payload["resolved_evidence"] is not None:
        evidence = payload["resolved_evidence"]
        if not isinstance(evidence, Mapping):
            raise TrainingDataInputError(
                "MACE execution authority resolved evidence is not an object."
            )
        evidence = dict(evidence)
        if evidence.get("schema") != MACE_EXECUTION_EVIDENCE_SCHEMA:
            raise TrainingDataInputError(
                "Unsupported MACE execution-evidence schema."
            )
        evidence_digest = evidence.get("evidence_digest")
        if evidence_digest is None:
            raise TrainingDataInputError(
                "MACE execution evidence is missing its content digest."
            )
        observed_digest = digest(
            {key: value for key, value in evidence.items() if key != "evidence_digest"}
        )
        if str(evidence_digest) != observed_digest:
            raise TrainingDataInputError(
                "MACE execution evidence content digest mismatch."
            )
        result["resolved_evidence"] = evidence
    return result


def build_mace_execution_authority(**kwargs: Any) -> dict[str, Any]:
    """Build the authenticated process-local MACE execution transport."""

    payload = {
        "schema": MACE_EXECUTION_AUTHORITY_SCHEMA,
        "execution_semantics_version": MACE_EXECUTION_SEMANTICS_VERSION,
        **kwargs,
    }
    return _normalize_mace_execution_authority(payload)


def mace_execution_authority_from_environment(
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any] | None:
    """Load and validate the launch authority, or return ``None`` for ordinary MACE."""

    source = os.environ if environ is None else environ
    raw = source.get(MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE)
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except Exception as exc:
        raise TrainingDataInputError(
            "MACE execution authority is not valid JSON."
        ) from exc
    if not isinstance(payload, Mapping):
        raise TrainingDataInputError("MACE execution authority must be a JSON object.")
    return _normalize_mace_execution_authority(payload)


def mace_execution_authority_to_environment(
    authority: Mapping[str, Any],
) -> str:
    """Validate and serialize one launch authority for a child process."""

    normalized = _normalize_mace_execution_authority(authority)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"))


def record_mace_execution_evidence(
    authority: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Attach validated resolved facts to the existing launch authority."""

    normalized = _normalize_mace_execution_authority(authority)
    resolved = {
        "schema": MACE_EXECUTION_EVIDENCE_SCHEMA,
        "execution_semantics_version": MACE_EXECUTION_SEMANTICS_VERSION,
        **dict(evidence),
    }
    for name in (
        "loss_family",
        "loss_class",
        "learning_rate",
        "ema",
        "ema_decay",
        "multiheads_finetuning",
        "force_mh_ft_lr",
        "real_pt_data_ratio_threshold",
        "target_train_count",
        "replay_train_count",
        "target_duplication_factor",
        "target_batch_size",
        "target_updates_per_epoch",
        "target_drop_last",
        "distributed",
        "target_frame_uid_set_digest",
        "replay_frame_uid_set_digest",
        "combined_train_count",
    ):
        if name not in resolved:
            raise TrainingDataInputError(
                f"MACE execution evidence is missing {name}."
            )
    if resolved["loss_family"] != normalized["loss_family"]:
        raise TrainingDataInputError("Resolved MACE loss family differs from authority.")
    if resolved["loss_class"] != "mace.modules.loss.WeightedEnergyForcesStressLoss":
        raise TrainingDataInputError(
            "Resolved MACE loss class is not the native weighted stress loss."
        )
    if not math.isclose(
        float(resolved["learning_rate"]),
        float(normalized["learning_rate"]),
        rel_tol=0.0,
        abs_tol=0.0,
    ):
        raise TrainingDataInputError("Resolved MACE learning rate differs from authority.")
    if bool(resolved["ema"]) != bool(normalized["ema"]):
        raise TrainingDataInputError("Resolved MACE EMA flag differs from authority.")
    resolved_ema_decay = resolved["ema_decay"]
    if normalized["ema"]:
        if resolved_ema_decay is None or not math.isclose(
            float(resolved_ema_decay),
            float(normalized["ema_decay"]),
            rel_tol=0.0,
            abs_tol=0.0,
        ):
            raise TrainingDataInputError("Resolved MACE EMA decay differs from authority.")
    elif resolved_ema_decay is not None:
        raise TrainingDataInputError("Resolved MACE EMA decay is present while EMA is disabled.")
    if bool(resolved["multiheads_finetuning"]) != bool(
        normalized["multiheads_finetuning"]
    ):
        raise TrainingDataInputError(
            "Resolved MACE multihead mode differs from authority."
        )
    if normalized["multiheads_finetuning"]:
        if resolved["force_mh_ft_lr"] is not True:
            raise TrainingDataInputError("Resolved MACE replay LR/EMA forcing is disabled.")
        if float(resolved["real_pt_data_ratio_threshold"]) != float(
            normalized["real_pt_data_ratio_threshold"]
        ):
            raise TrainingDataInputError("Resolved MACE replay ratio threshold differs from authority.")
    elif resolved["force_mh_ft_lr"] is not None or resolved["real_pt_data_ratio_threshold"] is not None:
        raise TrainingDataInputError("Non-replay MACE evidence carries replay controls.")
    if int(resolved["target_train_count"]) != normalized["target_train_count"]:
        raise TrainingDataInputError(
            "Resolved MACE target count differs from authority."
        )
    if int(resolved["replay_train_count"]) != normalized["replay_train_count"]:
        raise TrainingDataInputError(
            "Resolved MACE replay count differs from authority."
        )
    if int(resolved["target_duplication_factor"]) != 1:
        raise TrainingDataInputError(
            "Resolved MACE execution reports forbidden target duplication."
        )
    if int(resolved["target_batch_size"]) != normalized["batch_size"]:
        raise TrainingDataInputError("Resolved MACE batch size differs from authority.")
    if normalized["role"] == "target_size":
        if int(resolved["target_updates_per_epoch"]) != int(
            normalized["target_updates_per_epoch"]
        ):
            raise TrainingDataInputError(
                "Resolved target-size update geometry differs from authority."
            )
        if resolved["target_drop_last"] is not False or resolved["distributed"] is not False:
            raise TrainingDataInputError(
                "Resolved target-size loader retained truncating or distributed semantics."
            )
    elif resolved["target_updates_per_epoch"] is not None or resolved["target_drop_last"] is not None:
        raise TrainingDataInputError(
            "Post-selection MACE evidence carries target-size loader semantics."
        )
    for name in ("target_frame_uid_set_digest", "replay_frame_uid_set_digest"):
        expected = normalized.get(name)
        observed = resolved[name]
        if expected is not None and observed != expected:
            raise TrainingDataInputError(
                f"Resolved MACE {name} differs from authority."
            )
    if int(resolved["combined_train_count"]) != int(
        normalized["target_train_count"] + normalized["replay_train_count"]
    ):
        raise TrainingDataInputError(
            "Resolved MACE combined training count differs from authority."
        )
    resolved["source_probe_digest"] = normalized.get("source_probe_digest")
    resolved["authority_config_digest"] = normalized["config_digest"]
    resolved["evidence_digest"] = digest(resolved)
    normalized["resolved_evidence"] = resolved
    return _normalize_mace_execution_authority(normalized)


def mace_execution_evidence_from_environment(
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any] | None:
    """Return the resolved evidence carried by the current child process."""

    authority = mace_execution_authority_from_environment(environ)
    if authority is None:
        return None
    evidence = authority.get("resolved_evidence")
    return None if evidence is None else dict(evidence)


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
    real_pt_data_ratio_threshold: float = MACE_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD,
    checkpoint_policy: MaceCheckpointControlPolicy | None = None,
    config_path: str = "mace_config.yaml",
) -> MaceLoaderDryRun:
    if not compatibility_probe.current_execution_compatible:
        raise TrainingDataInputError(
            "MACE source probe is historical or does not support the current fixed-file execution seam."
        )
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


# ---------------------------------------------------------------------------
# Canonical configuration -> pinned MACE executable configuration
# ---------------------------------------------------------------------------
#
# mdstats stores candidate/post-selection configuration as typed JSON-safe
# scientific data: ``atomic_numbers`` is a list of integers, ``E0s`` and the P5
# ``heads`` mapping are dictionaries, and ``radial_MLP`` is a list.  The pinned
# MACE 0.3.16 parser declares every one of those options as a scalar
# ``type=str`` action and interprets the string itself later with
# ``ast.literal_eval``.  Handing configargparse a YAML list or mapping fails
# before MACE training logic runs.
#
# These helpers are the one representation boundary between the canonical typed
# values and that external syntax.  They never change a canonical value or its
# digest; they only decide how it is spelled in the generated ``--config`` file.

#: Canonical architecture fields that are mdstats metadata and must never reach
#: the MACE command line.  ``heads`` here is the internal architecture head list
#: (``["target_head"]``); MACE's ``--heads`` is an unrelated dataset-head
#: mapping owned by the P5 multihead configuration.
MACE_ARCHITECTURE_INTERNAL_KEYS = frozenset({"schema", "heads"})

#: Canonical architecture fields that are real MACE training arguments.
MACE_ARCHITECTURE_EXTERNAL_KEYS = frozenset(
    {
        "model",
        "r_max",
        "num_radial_basis",
        "num_cutoff_basis",
        "max_ell",
        "interaction",
        "interaction_first",
        "num_interactions",
        "hidden_irreps",
        "edge_irreps",
        "num_channels",
        "max_L",
        "MLP_irreps",
        "radial_MLP",
        "radial_type",
        "pair_repulsion",
        "distance_transform",
        "apply_cutoff",
        "correlation",
        "gate",
        "use_reduced_cg",
        "use_so3",
        "use_edge_irreps_first",
        "use_agnostic_product",
        "use_embedding_readout",
        "use_last_readout_only",
        "embedding_specs",
        "avg_num_neighbors",
        "scaling",
        "mean",
        "std",
        "loss",
    }
)

#: The one executable MACE loss family for every current mdstats training path.
#:
#: MACE's ``UniversalLoss`` cannot represent the declared mdstats weighting
#: contract: its per-config property weights scale residuals *inside* a Huber
#: evaluation, so they are not linearly equivalent to global objective
#: coefficients, and it never consumes ``config_weight`` at all.  The weighted
#: energy+force+stress loss does: its native reductions multiply by
#: ``ref.weight`` and the local property weight linearly and apply the global
#: coefficients once, outside.
#:
#: The family is method identity, not formatting: the optimization meaning of a
#: checkpoint depends on it, so a checkpoint trained under a different family is
#: not a prefix or equivalent of a corrected trajectory.  Model construction is
#: unaffected -- pinned MACE derives ``compute_stress`` for both ``stress`` and
#: ``universal`` and ``compute_virials`` for neither -- so reconstruction and
#: EVAL2 semantics are preserved across the correction.
MACE_EXECUTABLE_LOSS_FAMILY = "stress"


#: Architecture fields whose canonical value is structured and whose pinned
#: parser action is scalar ``type=str``.
MACE_ARCHITECTURE_LITERAL_KEYS = frozenset({"radial_MLP"})

#: Top-level configuration fields whose pinned parser action is scalar
#: ``type=str`` while the canonical value is structured.
MACE_EXECUTABLE_LITERAL_KEYS = ("atomic_numbers", "E0s", "heads")


def mace_atomic_numbers_literal(value: Any) -> str:
    """Spell a canonical atomic-number sequence for MACE's ``ast.literal_eval``."""

    try:
        numbers = sorted({int(item) for item in value})
    except (TypeError, ValueError) as exc:
        raise TrainingDataInputError(
            "MACE atomic_numbers must be a sequence of integers."
        ) from exc
    if not numbers:
        raise TrainingDataInputError("MACE atomic_numbers must be non-empty.")
    return repr(numbers)


def mace_e0s_literal(value: Any) -> str:
    """Spell a canonical E0 mapping for MACE's ``ast.literal_eval``.

    MACE indexes the evaluated mapping by the integer atomic numbers of its own
    ``AtomicNumberTable``, so the emitted literal is keyed by ``int`` even
    though the canonical JSON-safe mapping is keyed by the decimal string.
    """

    if isinstance(value, str):
        # ``average``/``foundation``/``estimated`` and JSON paths are already
        # the scalar spelling MACE expects.
        return value
    if not isinstance(value, Mapping):
        raise TrainingDataInputError("MACE E0s must be a mapping or a MACE keyword.")
    try:
        energies = {int(key): float(item) for key, item in value.items()}
    except (TypeError, ValueError) as exc:
        raise TrainingDataInputError(
            "MACE E0s must map atomic numbers to finite energies."
        ) from exc
    if not energies:
        raise TrainingDataInputError("MACE E0s must be non-empty.")
    return repr({z: energies[z] for z in sorted(energies)})


def mace_scalar_sequence_literal(value: Any, *, name: str) -> str:
    """Spell a canonical scalar sequence (e.g. ``radial_MLP``) as a literal."""

    if isinstance(value, str):
        return value
    try:
        items = list(value)
    except TypeError as exc:
        raise TrainingDataInputError(f"MACE {name} must be a sequence.") from exc
    for item in items:
        if not isinstance(item, (int, float, str)) or isinstance(item, bool):
            raise TrainingDataInputError(
                f"MACE {name} must contain only numeric or string literals."
            )
    return repr(items)


def mace_heads_literal(value: Any) -> str:
    """Spell the canonical MACE dataset-head mapping as one scalar literal.

    MACE evaluates ``--heads`` with ``ast.literal_eval`` and then consumes each
    head's ``atomic_numbers``/``E0s`` exactly as it consumes the top-level ones,
    so those nested values are scalar literals too.
    """

    if isinstance(value, str):
        return value
    if not isinstance(value, Mapping):
        raise TrainingDataInputError("MACE heads must be a mapping.")
    heads: dict[str, dict[str, Any]] = {}
    for head_name in sorted(str(key) for key in value):
        head = value[head_name]
        if not isinstance(head, Mapping):
            raise TrainingDataInputError(
                f"MACE head {head_name!r} must be a mapping."
            )
        encoded: dict[str, Any] = {}
        for field_name in sorted(str(key) for key in head):
            field_value = head[field_name]
            if field_name == "atomic_numbers":
                encoded[field_name] = mace_atomic_numbers_literal(field_value)
            elif field_name == "E0s":
                encoded[field_name] = mace_e0s_literal(field_value)
            else:
                encoded[field_name] = field_value
        heads[head_name] = encoded
    if not heads:
        raise TrainingDataInputError("MACE heads must be non-empty.")
    return repr(heads)


def project_mace_architecture_arguments(
    architecture: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Project a canonical MACE architecture into MACE command-line arguments.

    Only fields that are genuine MACE training arguments are emitted; internal
    mdstats metadata is dropped by name rather than by accident.  A canonical
    ``None`` means "no override", which the pinned parser expresses through its
    own default, so those fields are omitted instead of feeding a YAML null to a
    scalar action.  An unrecognized architecture field fails here rather than
    leaking into the dependency.
    """

    if not architecture:
        return {}
    if not isinstance(architecture, Mapping):
        raise TrainingDataInputError("MACE architecture must be a mapping.")
    unknown = sorted(
        str(key)
        for key in architecture
        if str(key) not in MACE_ARCHITECTURE_EXTERNAL_KEYS
        and str(key) not in MACE_ARCHITECTURE_INTERNAL_KEYS
    )
    if unknown:
        raise TrainingDataInputError(
            "MACE architecture carries fields with no declared executable "
            f"projection: {unknown}."
        )
    projected: dict[str, Any] = {}
    for key in sorted(str(key) for key in architecture):
        if key in MACE_ARCHITECTURE_INTERNAL_KEYS:
            continue
        value = architecture[key]
        if value is None:
            continue
        if key in MACE_ARCHITECTURE_LITERAL_KEYS:
            projected[key] = mace_scalar_sequence_literal(value, name=key)
        else:
            projected[key] = value
    return projected


def encode_mace_executable_configuration(
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Spell the structured top-level fields of a MACE run configuration.

    Values that are already scalars pass through untouched; only the fields the
    pinned parser declares as scalar ``type=str`` while mdstats keeps them
    structured are re-spelled.
    """

    encoded = dict(config)
    if "atomic_numbers" in encoded:
        encoded["atomic_numbers"] = mace_atomic_numbers_literal(
            encoded["atomic_numbers"]
        )
    if "E0s" in encoded:
        encoded["E0s"] = mace_e0s_literal(encoded["E0s"])
    if "heads" in encoded:
        encoded["heads"] = mace_heads_literal(encoded["heads"])
    return encoded
