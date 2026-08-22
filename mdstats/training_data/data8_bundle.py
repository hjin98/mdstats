"""DATA8 fixed-file MACE/replay artifact orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping, Sequence
import ast
import hashlib
import json
import os
import shutil
import uuid

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest, sha256_file_cached
from .feature_metric import FeatureFitDomainKind
from .adaptive_stop import AdaptiveTrainingStopPolicy
from .train2_policy import (
    TrainingBudgetPolicy, LearningRateSchedulePolicy, CheckpointAdmissibilityPolicy,
    CheckpointSelectionPolicy, validate_train2_policy_set,
)
from .reference_fit import AtomicReferenceFitMode
from .mace_compatibility import (
    MaceCheckpointControlPolicy,
    MaceCompatibilityPolicy,
    MaceLoaderDryRun,
    MaceSourceProbe,
    emulate_mace_v0316_loader_dry_run,
)
from .mace_export import (
    MaceExtxyzArtifact,
    MaceExtxyzPolicy,
    _write_extxyz_high_precision,
    write_mace_extxyz_artifact,
)
from .acceleration import MaceAccelerationKernelMode
from .foundation import foundation_identity_matches_lineage, inspect_mace_foundation
from .mace_head_extraction import MaceSelectedHeadQualificationRecord
from .protocol import (
    FoundationCheckpointIdentity,
    MaceJobArtifact,
    MaceJobKind,
    MaceOptimizerPolicy,
    SealedEvaluationArtifact,
    TrainingMode,
    TrainingProtocolIdentity,
)
from .replay import ReplayMode, ReplayPreparationPlan, ReplayFileArtifact, inspect_replay_extxyz
from .online_monitor import (
    OnlineMonitorPolicy, OnlineMonitorRecord, build_target_online_monitor,
    build_replay_online_monitor, materialize_replay_online_monitor,
)
from .partition import OuterRole
from .mlcv_roles import MlcvRoleCatalog, build_mlcv_role_catalog
from .mlcv_monitors import (
    MlcvMonitorPolicy, MlcvMonitorCatalog, MlcvRunMonitorRecord,
    build_run_monitor_record, build_replay_monitor_record, write_replay_light_subset,
)

DATA8_PREPARATION_BUNDLE_SCHEMA = "mdstats.data8-preparation-bundle.v5"
DATA8_PREPARATION_BUNDLE_V4_SCHEMA = "mdstats.data8-preparation-bundle.v4"
DATA8_PREPARATION_BUNDLE_V3_SCHEMA = "mdstats.data8-preparation-bundle.v3"
DATA8_PREPARATION_BUNDLE_V2_SCHEMA = "mdstats.data8-preparation-bundle.v2"
DATA8_PREPARATION_BUNDLE_V1_SCHEMA = "mdstats.data8-preparation-bundle.v1"
MLFF_DATA8_PARSER_VERSION = "0.20.132a0"
MLFF_DATA8_PRE_MLCV_MON1_PARSER_VERSION = "0.20.131a0"
MLFF_DATA8_PRE_MLCV_ROLE1_PARSER_VERSION = "0.20.126a0"
MLFF_DATA8_PRE_ADAPT_EVAL1_PARSER_VERSION = "0.20.124a0"
MLFF_DATA8_PRE_ADAPT_STOP1_PARSER_VERSION = "0.20.123a0"
MLFF_DATA8_PRE_ADAPT_MON1_PARSER_VERSION = "0.20.66a0"
MLFF_DATA8_LEGACY_PARSER_VERSION = "0.20.39a0"


def _sha256_file(path: Path) -> str:
    return sha256_file_cached(path)



DATA8_FIXED_FILE_CACHE_SCHEMA = "mdstats.perf-p2r-data8-fixed-file-cache.v1"
DATA8_FIXED_FILE_RECIPE_SCHEMA = "mdstats.perf-p2r-data8-fixed-file-recipe.v1"


def _atomic_link_or_copy_file(source: Path, destination: Path) -> None:
    """Populate one execution-cache consumer without changing scientific bytes."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}"
    )
    temporary.unlink(missing_ok=True)
    try:
        try:
            os.link(source, temporary)
        except OSError:
            shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _data8_fixed_file_recipe(
    *,
    dataset_id: str,
    role: str,
    frame_uids: Sequence[str],
    frame_catalog: Any,
    data7_bundle: Any | None,
    policy: MaceExtxyzPolicy,
    training_weights: Any | None,
    configuration_weight_scale: float,
    config_type_by_frame: Mapping[str, str] | None,
) -> dict[str, Any]:
    frames = tuple(str(v) for v in frame_uids)
    config_type_digest = None
    if config_type_by_frame is not None:
        config_type_digest = digest({
            "schema": "mdstats.perf-p2r-config-type-map.v1",
            "records": [
                [uid, str(config_type_by_frame[uid])]
                for uid in frames
                if uid in config_type_by_frame
            ],
        })
    return {
        "schema": DATA8_FIXED_FILE_RECIPE_SCHEMA,
        "dataset_id": str(dataset_id),
        "role": str(role),
        "frame_catalog_digest": str(frame_catalog.content_digest),
        "data7_bundle_digest": (
            None if data7_bundle is None else str(data7_bundle.content_digest)
        ),
        "policy_digest": str(policy.policy_digest),
        "training_weights_digest": (
            None if training_weights is None else str(training_weights.content_digest)
        ),
        "configuration_weight_scale_hex": float(configuration_weight_scale).hex(),
        "config_type_digest": config_type_digest,
        "frame_uids": list(frames),
    }


def _load_valid_data8_fixed_file_cache(
    cache_directory: Path,
    *,
    recipe: Mapping[str, Any],
    recipe_digest: str,
) -> MaceExtxyzArtifact | None:
    metadata_path = cache_directory / "cache.json"
    artifact_path = cache_directory / "artifact.xyz"
    sidecar_path = cache_directory / "artifact.xyz.manifest.json"
    if not metadata_path.is_file() or not artifact_path.is_file() or not sidecar_path.is_file():
        return None
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        if payload.get("schema") != DATA8_FIXED_FILE_CACHE_SCHEMA:
            return None
        if payload.get("recipe_digest") != recipe_digest or payload.get("recipe") != dict(recipe):
            return None
        artifact = MaceExtxyzArtifact.from_dict(payload["artifact"])
        if artifact.relative_path != "artifact.xyz":
            return None
        if artifact.sidecar_relative_path != "artifact.xyz.manifest.json":
            return None
        if _sha256_file(artifact_path) != artifact.sha256:
            return None
        if _sha256_file(sidecar_path) != artifact.sidecar_sha256:
            return None
        return artifact
    except Exception:
        return None


def _write_or_reuse_data8_extxyz_artifact(
    output_directory: str | Path,
    *,
    dataset_id: str,
    role: str,
    filename: str,
    frame_uids: Sequence[str],
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    data7_bundle: Any | None = None,
    policy: MaceExtxyzPolicy | None = None,
    training_weights: Any | None = None,
    configuration_weight_scale: float = 1.0,
    config_type_by_frame: Mapping[str, str] | None = None,
    frame_array_index: Mapping[str, tuple[Any, Any, int]] | None = None,
    shared_cache_directory: str | Path | None = None,
) -> MaceExtxyzArtifact:
    """Write one DATA8 ExtXYZ artifact, optionally through an authenticated cache.

    The cache key contains every input that can affect fixed-file bytes or the
    sidecar. Cache location and hard-link/copy realization are execution-only.
    A cache hit reconstructs the same path-local :class:`MaceExtxyzArtifact`
    identity that a fresh write would produce.
    """

    active_policy = MaceExtxyzPolicy() if policy is None else policy
    if shared_cache_directory is None:
        return write_mace_extxyz_artifact(
            output_directory,
            dataset_id=dataset_id,
            role=role,
            filename=filename,
            frame_uids=frame_uids,
            frame_catalog=frame_catalog,
            frame_data_by_run=frame_data_by_run,
            data7_bundle=data7_bundle,
            policy=active_policy,
            training_weights=training_weights,
            configuration_weight_scale=configuration_weight_scale,
            config_type_by_frame=config_type_by_frame,
            frame_array_index=frame_array_index,
        )

    recipe = _data8_fixed_file_recipe(
        dataset_id=dataset_id,
        role=role,
        frame_uids=frame_uids,
        frame_catalog=frame_catalog,
        data7_bundle=data7_bundle,
        policy=active_policy,
        training_weights=training_weights,
        configuration_weight_scale=configuration_weight_scale,
        config_type_by_frame=config_type_by_frame,
    )
    recipe_digest = digest(recipe)
    cache_root = Path(shared_cache_directory).resolve()
    cache_directory = cache_root / recipe_digest[:2] / recipe_digest
    cached = _load_valid_data8_fixed_file_cache(
        cache_directory, recipe=recipe, recipe_digest=recipe_digest
    )
    if cached is None:
        cache_directory.parent.mkdir(parents=True, exist_ok=True)
        staging = cache_directory.parent / (
            f".{recipe_digest}.tmp-{os.getpid()}-{uuid.uuid4().hex}"
        )
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=False)
        try:
            built = write_mace_extxyz_artifact(
                staging,
                dataset_id=dataset_id,
                role=role,
                filename="artifact.xyz",
                frame_uids=frame_uids,
                frame_catalog=frame_catalog,
                frame_data_by_run=frame_data_by_run,
                data7_bundle=data7_bundle,
                policy=active_policy,
                training_weights=training_weights,
                configuration_weight_scale=configuration_weight_scale,
                config_type_by_frame=config_type_by_frame,
                frame_array_index=frame_array_index,
            )
            metadata = {
                "schema": DATA8_FIXED_FILE_CACHE_SCHEMA,
                "recipe": recipe,
                "recipe_digest": recipe_digest,
                "artifact": built.to_dict(),
            }
            metadata_path = staging / "cache.json"
            with metadata_path.open("w", encoding="utf-8") as handle:
                json.dump(metadata, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.rename(staging, cache_directory)
            except OSError:
                # A concurrent process may have won the content-addressed race.
                # Never trust it implicitly: remove our staging tree and validate
                # the winning generation through the same authenticated path.
                shutil.rmtree(staging, ignore_errors=True)
            cached = _load_valid_data8_fixed_file_cache(
                cache_directory, recipe=recipe, recipe_digest=recipe_digest
            )
            if cached is None:
                raise TrainingDataInputError(
                    "PERF-P2R DATA8 fixed-file cache could not be validated after population."
                )
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    root = Path(output_directory).resolve()
    target = root / filename
    sidecar = target.with_suffix(target.suffix + ".manifest.json")
    _atomic_link_or_copy_file(cache_directory / "artifact.xyz", target)
    _atomic_link_or_copy_file(
        cache_directory / "artifact.xyz.manifest.json", sidecar
    )
    return MaceExtxyzArtifact(
        role=cached.role,
        relative_path=str(target.relative_to(root)),
        sha256=cached.sha256,
        configuration_count=cached.configuration_count,
        frame_uids=cached.frame_uids,
        atomic_numbers=cached.atomic_numbers,
        policy_digest=cached.policy_digest,
        sidecar_relative_path=str(sidecar.relative_to(root)),
        sidecar_sha256=cached.sidecar_sha256,
        sidecar_digest=cached.sidecar_digest,
    )


def _python_literal(value: Any) -> str:
    """Return a deterministic Python literal accepted by MACE v0.3.16.

    The MACE v0.3.16 ConfigArgParse schema declares ``atomic_numbers``,
    ``heads``, and per-head ``E0s`` as strings and applies
    :func:`ast.literal_eval` after parsing.  Native YAML sequences/mappings are
    therefore not equivalent to the required scalar strings.
    """

    if isinstance(value, Mapping):
        items = value.items()
        rendered = ", ".join(
            f"{_python_literal(key)}: {_python_literal(item)}" for key, item in items
        )
        result = "{" + rendered + "}"
    elif isinstance(value, (tuple, list)):
        rendered = ", ".join(_python_literal(item) for item in value)
        if isinstance(value, tuple):
            suffix = "," if len(value) == 1 else ""
            result = "(" + rendered + suffix + ")"
        else:
            result = "[" + rendered + "]"
    elif isinstance(value, (str, int, float, bool)) or value is None:
        result = repr(value)
    else:
        raise TrainingDataInputError(
            f"Unsupported value in MACE Python-literal serialization: {type(value).__name__}."
        )
    try:
        ast.literal_eval(result)
    except (SyntaxError, ValueError) as exc:  # pragma: no cover - defensive
        raise TrainingDataInputError("Generated MACE Python literal is invalid.") from exc
    return result


def _scale_extxyz_configuration_weights(
    source: Path,
    target: Path,
    *,
    scale: float,
) -> None:
    """Copy an extxyz file while realizing a fixed-file head weight."""

    if scale <= 0.0:
        raise TrainingDataInputError("Replay configuration-weight scale must be positive.")
    try:
        from ase.io import iread
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required to stage weighted replay files.") from exc

    def weighted_stream():
        for atoms in iread(source, index=":", format="extxyz"):
            base = float(atoms.info.get("config_weight", 1.0))
            atoms.info["config_weight"] = base * float(scale)
            yield atoms

    temporary = target.with_suffix(target.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            _write_extxyz_high_precision(handle, weighted_stream())
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _frames_for_units(data5_bundle: Any, unit_ids: Sequence[str]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                uid
                for unit_id in unit_ids
                for uid in data5_bundle.unit_catalog.unit(unit_id).frame_uids
            }
        )
    )


def _copy_replay_plan(plan: ReplayPreparationPlan, root: Path) -> ReplayPreparationPlan:
    if plan.mode is ReplayMode.NONE:
        return plan
    if not plan.ready_for_fixed_file_training:
        raise TrainingDataInputError(
            "DATA8 fixed-file jobs require local replay train and monitor files. "
            "Resolve MP_SHORTCUT to PRESELECTED before building jobs."
        )
    replay_dir = root / "shared" / "replay"
    replay_dir.mkdir(parents=True, exist_ok=True)
    train_target = replay_dir / "replay_train.xyz"
    monitor_target = replay_dir / "replay_monitor.xyz"
    _scale_extxyz_configuration_weights(
        Path(plan.train_artifact.path),
        train_target,
        scale=plan.head_weight,
    )
    shutil.copy2(plan.monitor_artifact.path, monitor_target)
    return ReplayPreparationPlan(
        mode=plan.mode,
        train_artifact=inspect_replay_extxyz(
            train_target,
            label_mode=plan.train_artifact.label_mode,
            foundation_checkpoint_digest=plan.train_artifact.foundation_checkpoint_digest,
            foundation_label_generator_identity_digest=plan.train_artifact.foundation_label_generator_identity_digest,
        ),
        monitor_artifact=inspect_replay_extxyz(
            monitor_target,
            label_mode=plan.monitor_artifact.label_mode,
            foundation_checkpoint_digest=plan.monitor_artifact.foundation_checkpoint_digest,
            foundation_label_generator_identity_digest=plan.monitor_artifact.foundation_label_generator_identity_digest,
        ),
        source_replay_path=plan.source_replay_path,
        requested_train_count=plan.requested_train_count,
        filtering_type=plan.filtering_type,
        subselect=plan.subselect,
        seed=plan.seed,
        head_weight=plan.head_weight,
        target_weight=plan.target_weight,
        selection_command=plan.selection_command,
        retention_policy=plan.retention_policy,
    )


def _stage_foundation_checkpoint(identity: FoundationCheckpointIdentity, root: Path) -> FoundationCheckpointIdentity:
    source = Path(identity.reference)
    if not source.is_file():
        raise TrainingDataInputError(f"Foundation checkpoint does not exist: {source!s}.")
    target_dir = root / "shared" / "foundation"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    shutil.copy2(source, target)
    if _sha256_file(target) != identity.sha256:
        raise TrainingDataInputError("Staged foundation checkpoint digest mismatch.")
    # Preserve the complete generalized foundation identity when staging;
    # only the location changes.  Reconstructing from the historical four
    # fields would discard architecture/head-table evidence introduced by
    # MH1-ID1.
    return replace(identity, reference=str(target.relative_to(root)))


def _stage_selected_head_training_checkpoint(
    qualification: MaceSelectedHeadQualificationRecord,
    foundation: FoundationCheckpointIdentity,
    root: Path,
) -> tuple[str, str]:
    """Stage the parity-qualified single-head executable used by MACE training.

    Scientific lineage remains attached to ``foundation``.  The derived file is
    an execution artifact authenticated by EXTRACT1 and must never replace the
    source potential identity.
    """

    canonical = foundation.canonicalized()
    extraction = qualification.extraction
    if not qualification.training_qualified:
        raise TrainingDataInputError("Selected-head foundation is not training-qualified.")
    if extraction.source_potential_digest != canonical.canonical_content_digest:
        raise TrainingDataInputError("Selected-head qualification belongs to a different source potential/head.")
    if extraction.source_checkpoint_sha256 != canonical.sha256:
        raise TrainingDataInputError("Selected-head qualification source SHA differs from the scientific foundation.")
    if extraction.source_head != canonical.foundation_head:
        raise TrainingDataInputError("Selected-head qualification source head differs from the scientific foundation.")
    source = Path(extraction.derived_checkpoint_reference)
    if not source.is_file():
        raise TrainingDataInputError(f"Qualified selected-head checkpoint does not exist: {source!s}.")
    if _sha256_file(source) != extraction.derived_checkpoint_sha256:
        raise TrainingDataInputError("Qualified selected-head checkpoint digest mismatch.")
    inspection = inspect_mace_foundation(source)
    if inspection.available_heads != (canonical.foundation_head,):
        raise TrainingDataInputError(
            "Qualified selected-head executable must expose exactly the selected source head; "
            f"observed {inspection.available_heads}."
        )
    if inspection.model_dtype != extraction.derived_model_dtype:
        raise TrainingDataInputError("Qualified selected-head executable dtype changed after EXTRACT1.")
    target_dir = root / "shared" / "foundation" / "selected_head"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    shutil.copy2(source, target)
    if _sha256_file(target) != extraction.derived_checkpoint_sha256:
        raise TrainingDataInputError("Staged selected-head checkpoint digest mismatch.")
    return str(target.relative_to(root)), extraction.derived_checkpoint_sha256


def _mace_config(
    *,
    job_name: str,
    job_dir: Path,
    target_train: MaceExtxyzArtifact,
    target_valid: MaceExtxyzArtifact,
    data7_bundle: Any,
    foundation: FoundationCheckpointIdentity,
    training_foundation_reference: str | None,
    bundle_root: Path,
    replay_plan: ReplayPreparationPlan,
    replay_valid_artifact: ReplayFileArtifact | None,
    optimizer: MaceOptimizerPolicy,
    checkpoint: MaceCheckpointControlPolicy,
    real_pt_data_ratio_threshold: float,
    extxyz_policy: MaceExtxyzPolicy,
) -> dict[str, Any]:
    target_train_path = target_train.relative_path
    target_valid_path = target_valid.relative_path
    fitted_e0s = {
        int(z): float(value)
        for z, value in data7_bundle.atomic_reference_fit.reference_energies_ev
    }
    target_atomic_numbers = set(int(z) for z in target_train.atomic_numbers)
    replay_atomic_numbers = (
        set()
        if replay_plan.train_artifact is None
        else set(int(z) for z in replay_plan.train_artifact.atomic_numbers)
    )
    global_atomic_numbers = tuple(sorted(target_atomic_numbers | replay_atomic_numbers))
    missing_e0 = sorted(target_atomic_numbers - set(fitted_e0s))
    if missing_e0:
        raise TrainingDataInputError(
            f"Explicit E0 mapping is missing target atomic numbers: {missing_e0}."
        )

    # MACE v0.3.16 supports a distinct element table on each head.  Without
    # this field the target head inherits the top-level target/replay union and
    # then incorrectly requires target E0s for replay-only species.  Keep the
    # global union for model construction, but bind target_head to the elements
    # actually present in its files.  MACE's multi-head array construction then
    # performs the intended zero-padding for elements absent from this head.
    e0s = fitted_e0s
    target_head = {
        "train_file": target_train_path,
        "valid_file": target_valid_path,
        "atomic_numbers": _python_literal(sorted(target_atomic_numbers)),
        "E0s": _python_literal(e0s),
        "energy_key": extxyz_policy.energy_key,
        "forces_key": extxyz_policy.forces_key,
        "stress_key": extxyz_policy.stress_key,
    }
    config: dict[str, Any] = {
        "name": job_name,
        "seed": optimizer.seed,
        "foundation_model": str(
            Path("../..")
            / (foundation.reference if training_foundation_reference is None else training_foundation_reference)
        ),
        "foundation_head": foundation.foundation_head,
        "multiheads_finetuning": replay_plan.mode is not ReplayMode.NONE,
        "heads": None,
        "atomic_numbers": _python_literal(list(global_atomic_numbers)),
        "energy_key": extxyz_policy.energy_key,
        "forces_key": extxyz_policy.forces_key,
        "stress_key": extxyz_policy.stress_key,
        "energy_weight": data7_bundle.training_weights.objective_policy.energy_weight,
        "forces_weight": data7_bundle.training_weights.objective_policy.forces_weight,
        "stress_weight": data7_bundle.training_weights.objective_policy.stress_weight,
        "loss": "universal",
        "lr": optimizer.learning_rate,
        "force_mh_ft_lr": True,
        "batch_size": optimizer.batch_size,
        "valid_batch_size": optimizer.valid_batch_size,
        "num_workers": optimizer.num_workers,
        "max_num_epochs": optimizer.max_num_epochs,
        "eval_interval": optimizer.eval_interval,
        "ema": optimizer.ema,
        "ema_decay": optimizer.ema_decay,
        "amsgrad": optimizer.amsgrad,
        "weight_decay": optimizer.weight_decay,
        "clip_grad": optimizer.clip_grad,
        "default_dtype": optimizer.default_dtype,
        "device": optimizer.device,
        **(
            {
                **optimizer.acceleration_policy.training_config(),
                "enable_oeq": False,
            }
            if optimizer.resolved_acceleration_kernel_mode is None
            else {
                "enable_cueq": MaceAccelerationKernelMode(optimizer.resolved_acceleration_kernel_mode)
                is not MaceAccelerationKernelMode.E3NN,
                "enable_oeq": MaceAccelerationKernelMode(optimizer.resolved_acceleration_kernel_mode)
                is MaceAccelerationKernelMode.CUEQ_OEQ_HYBRID,
                "only_cueq": bool(optimizer.acceleration_policy.only_cueq),
            }
        ),
        "save_all_checkpoints": checkpoint.save_all_checkpoints,
        "patience": checkpoint.native_patience,
        "real_pt_data_ratio_threshold": real_pt_data_ratio_threshold,
        "plot": False,
    }
    if replay_plan.mode is not ReplayMode.NONE:
        # The explicit pt_head entry supplies the replay key specification. MACE
        # v0.3.16 replaces its remaining contents through prepare_pt_head().
        heads = {
            checkpoint.target_head_name: target_head,
            checkpoint.replay_head_name: {
            "energy_key": replay_plan.train_artifact.energy_key,
            "forces_key": replay_plan.train_artifact.forces_key,
            "stress_key": replay_plan.train_artifact.stress_key,
            },
        }
        config.update(
            {
                "pt_train_file": str(Path("../..") / Path(replay_plan.train_artifact.path).relative_to(bundle_root)),
                "pt_valid_file": str(
                    Path("../..")
                    / Path(
                        (replay_plan.monitor_artifact if replay_valid_artifact is None else replay_valid_artifact).path
                    ).relative_to(bundle_root)
                ),
            }
        )
    else:
        heads = {checkpoint.target_head_name: target_head}
    config["heads"] = _python_literal(heads)
    return config


@dataclass(frozen=True, slots=True)
class Data8PreparationBundle:
    dataset_id: str
    source_catalog_digest: str
    frame_catalog_digest: str
    data5_bundle_digest: str
    compatibility_policy: MaceCompatibilityPolicy
    compatibility_probe: MaceSourceProbe
    replay_plan: ReplayPreparationPlan
    jobs: tuple[MaceJobArtifact, ...]
    target_artifacts: tuple[MaceExtxyzArtifact, ...]
    fold_evaluation_artifacts: tuple[MaceExtxyzArtifact, ...]
    sealed_outer_evaluations: tuple[SealedEvaluationArtifact, ...]
    output_directory: str
    online_monitor_policy: OnlineMonitorPolicy | None = None
    target_online_monitor: OnlineMonitorRecord | None = None
    replay_online_monitor: OnlineMonitorRecord | None = None
    online_replay_monitor_artifact: ReplayFileArtifact | None = None
    full_target_evaluation_artifact: MaceExtxyzArtifact | None = None
    mlcv_role_catalog: MlcvRoleCatalog | None = None
    mlcv_monitor_catalog: MlcvMonitorCatalog | None = None
    replay_full_validation_artifact: ReplayFileArtifact | None = None
    notes: tuple[str, ...] = ()
    _serialization_parser_version: str = field(
        default=MLFF_DATA8_PARSER_VERSION, init=False, repr=False, compare=False
    )
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("source_catalog_digest", "frame_catalog_digest", "data5_bundle_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.compatibility_probe.policy_digest != self.compatibility_policy.policy_digest:
            raise TrainingDataInputError("DATA8 compatibility policy/probe mismatch.")
        if not self.compatibility_probe.fixed_file_adapter_supported:
            raise TrainingDataInputError("DATA8 requires a passing fixed-file MACE source probe.")
        jobs = tuple(sorted(self.jobs, key=lambda item: (item.kind.value, -1 if item.fold_index is None else item.fold_index)))
        if not jobs or len({item.job_id for item in jobs}) != len(jobs):
            raise TrainingDataInputError("DATA8 requires unique MACE jobs.")
        if any(item.protocol.replay_plan_digest != (None if self.replay_plan.mode is ReplayMode.NONE else self.replay_plan.content_digest) for item in jobs):
            raise TrainingDataInputError("DATA8 job/replay lineage mismatch.")
        if self.mlcv_monitor_catalog is not None:
            if self.mlcv_role_catalog is None:
                raise TrainingDataInputError("MLCV-MON1 DATA8 bundles require ROLE1 authority.")
            if self.mlcv_monitor_catalog.role_catalog_digest != self.mlcv_role_catalog.content_digest:
                raise TrainingDataInputError("DATA8 MLCV monitor/role catalog mismatch.")
            if self.replay_full_validation_artifact is None or self.online_replay_monitor_artifact is None:
                raise TrainingDataInputError("MLCV-MON1 requires full and lightweight TRUE_DFT replay artifacts.")
            if self.replay_full_validation_artifact.label_mode.value != "true_dft" or self.online_replay_monitor_artifact.label_mode.value != "true_dft":
                raise TrainingDataInputError("MLCV replay validation artifacts must carry TRUE_DFT labels.")
            replay_record = self.mlcv_monitor_catalog.replay
            if self.replay_full_validation_artifact.content_digest != replay_record.full_artifact_digest:
                raise TrainingDataInputError("DATA8 replay-full artifact/catalog lineage mismatch.")
            if self.online_replay_monitor_artifact.geometry_identities != replay_record.light_geometry_identities:
                raise TrainingDataInputError("DATA8 replay-light artifact/catalog membership mismatch.")
            for job in jobs:
                record = self.mlcv_monitor_catalog.run(job.job_id)
                def _matching(role: str, membership: tuple[str, ...]):
                    matches = [
                        artifact for artifact in self.target_artifacts
                        if artifact.role == role and artifact.frame_uids == membership
                    ]
                    return matches[0] if matches else None
                light = _matching("target_checkpoint_monitor", record.target_light_frame_uids)
                full = _matching("target_checkpoint_full", record.target_full_frame_uids)
                diagnostic = _matching("target_training_diagnostic", record.training_diagnostic_frame_uids)
                if light is None or full is None or diagnostic is None:
                    raise TrainingDataInputError(f"MLCV-MON1 target artifacts are incomplete for {job.job_id}.")
                if light.frame_uids != record.target_light_frame_uids or full.frame_uids != record.target_full_frame_uids:
                    raise TrainingDataInputError(f"MLCV target monitor membership mismatch for {job.job_id}.")
                if diagnostic.frame_uids != record.training_diagnostic_frame_uids:
                    raise TrainingDataInputError(f"MLCV training-diagnostic membership mismatch for {job.job_id}.")
                observed_protocol = (
                    job.protocol.online_monitor_policy_digest,
                    job.protocol.target_online_monitor_record_digest,
                    job.protocol.replay_online_monitor_record_digest,
                    job.protocol.replay_valid_artifact_digest,
                )
                expected_protocol = (
                    self.mlcv_monitor_catalog.policy.policy_digest,
                    record.content_digest,
                    replay_record.content_digest,
                    self.online_replay_monitor_artifact.content_digest,
                )
                if observed_protocol != expected_protocol:
                    raise TrainingDataInputError(f"MLCV job/monitor lineage mismatch for {job.job_id}.")
        elif self.online_monitor_policy is not None:
            # Historical ADAPT-MON1 common-monitor bundles remain readable.
            if self.target_online_monitor is None or self.replay_online_monitor is None or self.online_replay_monitor_artifact is None:
                raise TrainingDataInputError("ADAPT-MON1 DATA8 bundles require target/replay monitor evidence and a true replay artifact.")
            if self.target_online_monitor.policy_digest != self.online_monitor_policy.policy_digest or self.replay_online_monitor.policy_digest != self.online_monitor_policy.policy_digest:
                raise TrainingDataInputError("DATA8 online-monitor record/policy mismatch.")
            if self.online_replay_monitor_artifact.label_mode.value != "true_dft":
                raise TrainingDataInputError("DATA8 online replay monitor must carry true DFT labels.")
            if self.online_replay_monitor_artifact.geometry_identities != self.replay_online_monitor.selected_identities:
                raise TrainingDataInputError("DATA8 replay monitor artifact membership disagrees with monitor evidence.")
            target_monitor_artifacts = tuple(item for item in self.target_artifacts if item.role == "target_checkpoint_monitor")
            if not target_monitor_artifacts or any(item.frame_uids != self.target_online_monitor.selected_identities for item in target_monitor_artifacts):
                raise TrainingDataInputError("DATA8 target monitor artifacts are not the common ADAPT-MON1 membership.")
            expected_protocol = (
                self.online_monitor_policy.policy_digest,
                self.target_online_monitor.content_digest,
                self.replay_online_monitor.content_digest,
                self.online_replay_monitor_artifact.content_digest,
            )
            for job in jobs:
                observed_protocol = (
                    job.protocol.online_monitor_policy_digest,
                    job.protocol.target_online_monitor_record_digest,
                    job.protocol.replay_online_monitor_record_digest,
                    job.protocol.replay_valid_artifact_digest,
                )
                if observed_protocol != expected_protocol:
                    raise TrainingDataInputError("DATA8 job/online-monitor lineage mismatch.")
            if self.full_target_evaluation_artifact is not None:
                full_members = set(self.full_target_evaluation_artifact.frame_uids)
                if self.full_target_evaluation_artifact.role != "common_full_target_evaluation":
                    raise TrainingDataInputError("DATA8 full target evaluation artifact has the wrong role.")
                if not set(self.target_online_monitor.selected_identities).issubset(full_members):
                    raise TrainingDataInputError("Online target monitor is not a subset of the full target evaluation domain.")
        if self.mlcv_role_catalog is not None:
            if self.mlcv_role_catalog.data5_bundle_digest != self.data5_bundle_digest:
                raise TrainingDataInputError("DATA8 MLCV role catalog belongs to a different DATA5 bundle.")
            if self.mlcv_role_catalog.label_domain_id == "":
                raise TrainingDataInputError("DATA8 MLCV role catalog lacks label-domain identity.")
        object.__setattr__(self, "jobs", jobs)
        object.__setattr__(self, "target_artifacts", tuple(self.target_artifacts))
        object.__setattr__(self, "fold_evaluation_artifacts", tuple(self.fold_evaluation_artifacts))
        object.__setattr__(self, "sealed_outer_evaluations", tuple(self.sealed_outer_evaluations))
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": DATA8_PREPARATION_BUNDLE_SCHEMA,
            "parser_version": self._serialization_parser_version,
            "dataset_id": self.dataset_id,
            "source_catalog_digest": self.source_catalog_digest,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "compatibility_policy": self.compatibility_policy.to_dict(),
            "compatibility_probe": self.compatibility_probe.to_dict(),
            "replay_plan": self.replay_plan.to_dict(),
            "jobs": [item.to_dict() for item in self.jobs],
            "target_artifacts": [item.to_dict() for item in self.target_artifacts],
            "fold_evaluation_artifacts": [item.to_dict() for item in self.fold_evaluation_artifacts],
            "sealed_outer_evaluations": [item.to_dict() for item in self.sealed_outer_evaluations],
            "output_directory": self.output_directory,
            "online_monitor_policy": None if self.online_monitor_policy is None else self.online_monitor_policy.to_dict(),
            "target_online_monitor": None if self.target_online_monitor is None else self.target_online_monitor.to_dict(),
            "replay_online_monitor": None if self.replay_online_monitor is None else self.replay_online_monitor.to_dict(),
            "online_replay_monitor_artifact": None if self.online_replay_monitor_artifact is None else self.online_replay_monitor_artifact.to_dict(),
            "full_target_evaluation_artifact": None if self.full_target_evaluation_artifact is None else self.full_target_evaluation_artifact.to_dict(),
            "mlcv_role_catalog": None if self.mlcv_role_catalog is None else self.mlcv_role_catalog.to_dict(),
            "mlcv_monitor_catalog": None if self.mlcv_monitor_catalog is None else self.mlcv_monitor_catalog.to_dict(),
            "replay_full_validation_artifact": None if self.replay_full_validation_artifact is None else self.replay_full_validation_artifact.to_dict(),
            "notes": list(self.notes),
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
        cached = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Data8PreparationBundle":
        if payload.get("schema") not in {DATA8_PREPARATION_BUNDLE_SCHEMA, DATA8_PREPARATION_BUNDLE_V4_SCHEMA, DATA8_PREPARATION_BUNDLE_V3_SCHEMA, DATA8_PREPARATION_BUNDLE_V2_SCHEMA, DATA8_PREPARATION_BUNDLE_V1_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported DATA8 bundle schema.")
        if payload.get("parser_version") not in (
            None,
            MLFF_DATA8_PARSER_VERSION,
            MLFF_DATA8_PRE_MLCV_MON1_PARSER_VERSION,
            MLFF_DATA8_PRE_MLCV_ROLE1_PARSER_VERSION,
            MLFF_DATA8_PRE_ADAPT_EVAL1_PARSER_VERSION,
            MLFF_DATA8_PRE_ADAPT_STOP1_PARSER_VERSION,
            MLFF_DATA8_PRE_ADAPT_MON1_PARSER_VERSION,
            MLFF_DATA8_LEGACY_PARSER_VERSION,
        ):
            raise TrainingDataSerializationError("Unsupported DATA8 parser version.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            source_catalog_digest=str(payload["source_catalog_digest"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            data5_bundle_digest=str(payload["data5_bundle_digest"]),
            compatibility_policy=MaceCompatibilityPolicy.from_dict(payload["compatibility_policy"]),
            compatibility_probe=MaceSourceProbe.from_dict(payload["compatibility_probe"]),
            replay_plan=ReplayPreparationPlan.from_dict(payload["replay_plan"]),
            jobs=tuple(MaceJobArtifact.from_dict(item) for item in payload["jobs"]),
            target_artifacts=tuple(MaceExtxyzArtifact.from_dict(item) for item in payload["target_artifacts"]),
            fold_evaluation_artifacts=tuple(MaceExtxyzArtifact.from_dict(item) for item in payload["fold_evaluation_artifacts"]),
            sealed_outer_evaluations=tuple(SealedEvaluationArtifact.from_dict(item) for item in payload["sealed_outer_evaluations"]),
            output_directory=str(payload["output_directory"]),
            online_monitor_policy=None if payload.get("online_monitor_policy") is None else OnlineMonitorPolicy.from_dict(payload["online_monitor_policy"]),
            target_online_monitor=None if payload.get("target_online_monitor") is None else OnlineMonitorRecord.from_dict(payload["target_online_monitor"]),
            replay_online_monitor=None if payload.get("replay_online_monitor") is None else OnlineMonitorRecord.from_dict(payload["replay_online_monitor"]),
            online_replay_monitor_artifact=None if payload.get("online_replay_monitor_artifact") is None else ReplayFileArtifact.from_dict(payload["online_replay_monitor_artifact"]),
            full_target_evaluation_artifact=None if payload.get("full_target_evaluation_artifact") is None else MaceExtxyzArtifact.from_dict(payload["full_target_evaluation_artifact"]),
            mlcv_role_catalog=None if payload.get("mlcv_role_catalog") is None else MlcvRoleCatalog.from_dict(payload["mlcv_role_catalog"]),
            mlcv_monitor_catalog=None if payload.get("mlcv_monitor_catalog") is None else MlcvMonitorCatalog.from_dict(payload["mlcv_monitor_catalog"]),
            replay_full_validation_artifact=None if payload.get("replay_full_validation_artifact") is None else ReplayFileArtifact.from_dict(payload["replay_full_validation_artifact"]),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("parser_version") is not None:
            object.__setattr__(
                result,
                "_serialization_parser_version",
                str(payload["parser_version"]),
            )
        schema = payload.get("schema")
        if schema in {DATA8_PREPARATION_BUNDLE_V1_SCHEMA, DATA8_PREPARATION_BUNDLE_V2_SCHEMA, DATA8_PREPARATION_BUNDLE_V3_SCHEMA}:
            legacy_payload = {key: value for key, value in payload.items() if key != "content_digest"}
            if payload.get("content_digest") not in (None, digest(legacy_payload)):
                raise TrainingDataSerializationError("Legacy DATA8 bundle digest mismatch.")
        elif payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("DATA8 bundle digest mismatch.")
        return result


def build_data8_preparation_bundle(
    source_catalog: Any,
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    data5_bundle: Any,
    data7_bundles: Sequence[Any],
    *,
    output_directory: str | Path,
    foundation_checkpoint: FoundationCheckpointIdentity,
    selected_head_qualification: MaceSelectedHeadQualificationRecord | None = None,
    compatibility_probe: MaceSourceProbe,
    compatibility_policy: MaceCompatibilityPolicy | None = None,
    replay_plan: ReplayPreparationPlan | None = None,
    online_monitor_policy: OnlineMonitorPolicy | None = None,
    true_replay_monitor_artifact: ReplayFileArtifact | None = None,
    adaptive_stop_policy: AdaptiveTrainingStopPolicy | None = None,
    training_budget_policy: TrainingBudgetPolicy | None = None,
    learning_rate_schedule_policy: LearningRateSchedulePolicy | None = None,
    checkpoint_admissibility_policy: CheckpointAdmissibilityPolicy | None = None,
    checkpoint_selection_policy: CheckpointSelectionPolicy | None = None,
    optimizer_policy: MaceOptimizerPolicy | None = None,
    checkpoint_control_policy: MaceCheckpointControlPolicy | None = None,
    extxyz_policy: MaceExtxyzPolicy | None = None,
    real_pt_data_ratio_threshold: float = 0.0,
    selection_size: int | None = None,
    target_size_evaluation_frame_uids: Sequence[str] | None = None,
    require_foundation_residual_e0: bool = True,
    cross_validation_plans: Sequence[Any] | None = None,
    frame_array_index: Mapping[str, tuple[Any, Any, int]] | None = None,
    shared_fixed_file_cache_directory: str | Path | None = None,
) -> Data8PreparationBundle:
    active_compat = MaceCompatibilityPolicy() if compatibility_policy is None else compatibility_policy
    active_replay = ReplayPreparationPlan(mode=ReplayMode.NONE) if replay_plan is None else replay_plan
    active_optimizer = MaceOptimizerPolicy() if optimizer_policy is None else optimizer_policy
    active_checkpoint = MaceCheckpointControlPolicy() if checkpoint_control_policy is None else checkpoint_control_policy
    if adaptive_stop_policy is not None:
        if online_monitor_policy is None:
            raise TrainingDataInputError("ADAPT-STOP1 requires ADAPT-MON1 online-monitor evidence.")
        if active_optimizer.eval_interval != 1:
            raise TrainingDataInputError("ADAPT-STOP1 requires eval_interval=1.")
        if adaptive_stop_policy.max_num_epochs != active_optimizer.max_num_epochs:
            raise TrainingDataInputError("ADAPT-STOP1 epoch ceiling disagrees with optimizer policy.")
    train2_active = validate_train2_policy_set(
        budget=training_budget_policy,
        learning_rate=learning_rate_schedule_policy,
        admissibility=checkpoint_admissibility_policy,
        selection=checkpoint_selection_policy,
    )
    if train2_active and adaptive_stop_policy is not None:
        raise TrainingDataInputError(
            "TRAIN2 policy authority and historical AdaptiveTrainingStopPolicy are mutually exclusive."
        )
    if train2_active:
        if online_monitor_policy is None:
            raise TrainingDataInputError("TRAIN2 DATA8 requires authenticated online monitor evidence.")
        if active_optimizer.eval_interval != 1:
            raise TrainingDataInputError("TRAIN2 requires eval_interval=1.")
        if training_budget_policy.planned_epochs != active_optimizer.max_num_epochs:
            raise TrainingDataInputError("TRAIN2 epoch budget disagrees with optimizer policy.")
        if abs(learning_rate_schedule_policy.base_learning_rate - active_optimizer.learning_rate) > 1e-18:
            raise TrainingDataInputError("TRAIN2 base LR disagrees with optimizer policy.")
    active_extxyz = MaceExtxyzPolicy() if extxyz_policy is None else extxyz_policy
    if compatibility_probe.policy_digest != active_compat.policy_digest or not compatibility_probe.fixed_file_adapter_supported:
        raise TrainingDataInputError("The MACE compatibility probe does not match the active DATA8 lock.")
    if real_pt_data_ratio_threshold < 0.0:
        raise TrainingDataInputError("real_pt_data_ratio_threshold must be nonnegative.")
    bundles = tuple(data7_bundles)
    if not bundles:
        raise TrainingDataInputError("DATA8 requires final and fold DATA7 bundles.")
    domains = {item.domain.label_domain_id for item in bundles}
    if len(domains) != 1:
        raise TrainingDataInputError("One DATA8 MACE bundle may contain exactly one target label domain.")
    label_domain_id = next(iter(domains))
    if any(item.data5_bundle_digest != data5_bundle.content_digest for item in bundles):
        raise TrainingDataInputError("DATA8 DATA7/DATA5 lineage mismatch.")
    final_bundles = [item for item in bundles if item.domain.kind is FeatureFitDomainKind.FINAL_DEVELOPMENT]
    if len(final_bundles) != 1:
        raise TrainingDataInputError("DATA8 requires exactly one final-development DATA7 bundle.")
    fold_bundles = sorted(
        (item for item in bundles if item.domain.kind is FeatureFitDomainKind.CROSS_VALIDATION_TRAINING),
        key=lambda item: item.domain.fold_index,
    )
    plans = (
        tuple(data5_bundle.cross_validation_plans)
        if cross_validation_plans is None
        else tuple(cross_validation_plans)
    )
    matching_plans = [
        item for item in plans if item.label_domain_id == label_domain_id
    ]
    if plans:
        if len(matching_plans) != 1:
            raise TrainingDataInputError(
                "DATA8 requires exactly one cross-validation plan for its label domain."
            )
        cv_plan = matching_plans[0]
        if {item.domain.fold_index for item in fold_bundles} != {item.fold_index for item in cv_plan.folds}:
            raise TrainingDataInputError("DATA8 requires one DATA7 bundle for every cross-validation fold.")
    else:
        cv_plan = None
        if fold_bundles:
            raise TrainingDataInputError(
                "Final-only DATA8 materialization cannot contain cross-validation DATA7 bundles."
            )

    mlcv_role_catalog = build_mlcv_role_catalog(
        data5_bundle,
        label_domain_id,
        replay_plan=active_replay,
        true_replay_validation_artifact=true_replay_monitor_artifact,
        cross_validation_plan=cv_plan,
    )

    root = Path(output_directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    staged_foundation = _stage_foundation_checkpoint(foundation_checkpoint, root)
    training_foundation_reference = None
    training_foundation_sha256 = None
    if selected_head_qualification is not None:
        training_foundation_reference, training_foundation_sha256 = _stage_selected_head_training_checkpoint(
            selected_head_qualification, staged_foundation, root
        )
    elif staged_foundation.inspection_state == "inspected" and len(staged_foundation.available_heads) > 1:
        raise TrainingDataInputError(
            "Inspected multi-head foundations require a parity-qualified selected-head training executable."
        )
    local_replay = _copy_replay_plan(active_replay, root)
    # MLCV-MON1 supersedes the common ADAPT-MON1 target monitor for newly
    # materialized campaigns.  Historical fields remain optional in the DATA8
    # schema so old evidence is still readable.
    target_online_record = None
    replay_online_record = None
    online_replay_artifact = None
    replay_full_validation_artifact = None
    mlcv_monitor_policy = None
    replay_monitor_record = None
    if online_monitor_policy is not None:
        if true_replay_monitor_artifact is None:
            raise TrainingDataInputError(
                "MLCV-MON1 production preparation requires an independent TRUE_DFT replay validation source."
            )
        if true_replay_monitor_artifact.label_mode.value != "true_dft":
            raise TrainingDataInputError("MLCV-MON1 replay validation source must carry TRUE_DFT labels.")
        mlcv_monitor_policy = MlcvMonitorPolicy(
            target_light_configurations=online_monitor_policy.target_configurations,
            replay_light_configurations=online_monitor_policy.replay_configurations,
            training_diagnostic_configurations=online_monitor_policy.training_diagnostic_configurations,
            seed=online_monitor_policy.seed,
        )
        replay_full_path = root / "shared" / "replay" / "full_true_replay_validation.xyz"
        replay_full_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(true_replay_monitor_artifact.path, replay_full_path)
        replay_full_validation_artifact = inspect_replay_extxyz(
            replay_full_path, label_mode=true_replay_monitor_artifact.label_mode,
            foundation_checkpoint_digest=true_replay_monitor_artifact.foundation_checkpoint_digest,
        )
        replay_monitor_record = build_replay_monitor_record(
            replay_full_validation_artifact, mlcv_monitor_policy
        )
        online_replay_artifact = write_replay_light_subset(
            replay_full_validation_artifact, replay_monitor_record,
            root / "shared" / "replay" / "light_true_replay_validation.xyz",
        )
    if require_foundation_residual_e0:
        for item in bundles:
            fit = item.atomic_reference_fit
            if fit.policy.fit_mode is not AtomicReferenceFitMode.FOUNDATION_RESIDUAL:
                raise TrainingDataInputError(
                    "Foundation fine-tuning requires checkpoint-bound residual E0 fits; "
                    "from-scratch total-energy E0 fits are not accepted."
                )
            if not foundation_identity_matches_lineage(
                foundation_checkpoint,
                foundation_identity_digest=fit.foundation_identity_digest,
                legacy_checkpoint_digest=fit.foundation_checkpoint_digest,
            ):
                raise TrainingDataInputError("DATA7 residual E0 fit is bound to a different foundation potential/head.")
    training_mode = TrainingMode.NAIVE_FINE_TUNING if local_replay.mode is ReplayMode.NONE else TrainingMode.MULTIHEAD_REPLAY
    artifacts: list[MaceExtxyzArtifact] = []
    evaluation_artifacts: list[MaceExtxyzArtifact] = []
    jobs: list[MaceJobArtifact] = []

    outer = data5_bundle.outer_partition_for_domain(label_domain_id)
    full_outer_monitor_frames = _frames_for_units(
        data5_bundle, outer.units_for(OuterRole.OUTER_MONITOR)
    )
    target_size_evaluation_frames = (
        None
        if target_size_evaluation_frame_uids is None
        else tuple(str(uid) for uid in target_size_evaluation_frame_uids)
    )
    if target_size_evaluation_frames is not None:
        development_frames = set(
            _frames_for_units(data5_bundle, outer.units_for(OuterRole.DEVELOPMENT))
        )
        if (
            not target_size_evaluation_frames
            or len(target_size_evaluation_frames) != len(set(target_size_evaluation_frames))
            or any(uid not in development_frames for uid in target_size_evaluation_frames)
        ):
            raise TrainingDataInputError(
                "Target-size candidate evaluation cohort must be a non-empty unique subset of DATA2A development."
            )
    full_target_evaluation_artifact = None
    if online_monitor_policy is not None:
        (root / "shared" / "target").mkdir(parents=True, exist_ok=True)
        full_target_evaluation_artifact = _write_or_reuse_data8_extxyz_artifact(
            root,
            dataset_id=frame_catalog.dataset_id,
            role="common_full_target_evaluation",
            filename="shared/target/full_target_evaluation.xyz",
            frame_uids=full_outer_monitor_frames,
            frame_catalog=frame_catalog,
            frame_data_by_run=frame_data_by_run,
            data7_bundle=None,
            policy=active_extxyz,
            frame_array_index=frame_array_index,
            shared_cache_directory=shared_fixed_file_cache_directory,
        )
    locked_frames = _frames_for_units(data5_bundle, outer.units_for(OuterRole.LOCKED_INTERPOLATION_TEST))
    sealed = (
        SealedEvaluationArtifact(
            role="locked_interpolation_test",
            label_domain_id=label_domain_id,
            frame_uids=locked_frames,
            frame_catalog_digest=frame_catalog.content_digest,
            data5_bundle_digest=data5_bundle.content_digest,
        ),
    )

    # ``target_full_frames`` is the complete checkpoint-selection domain.  It is
    # D_full for the final-development run and V_i_full for a CV fold.  The
    # lightweight subset is constructed only after the concrete training
    # membership is known, so its training-diagnostic monitor can be bound to
    # the exact DATA7 ladder realization as well.
    final_target_frames = (
        full_outer_monitor_frames
        if target_size_evaluation_frames is None
        else target_size_evaluation_frames
    )
    final_target_role = (
        "target_final_validation"
        if target_size_evaluation_frames is None
        else "target_size_candidate_development_complement"
    )
    job_specs: list[tuple[MaceJobKind, int | None, Any, tuple[str, ...], str, tuple[str, ...] | None]] = [
        (MaceJobKind.FINAL_DEVELOPMENT, None, final_bundles[0], final_target_frames, final_target_role, None)
    ]
    for bundle in fold_bundles:
        assert cv_plan is not None
        fold = cv_plan.folds[bundle.domain.fold_index]
        target_full = _frames_for_units(data5_bundle, fold.checkpoint_monitor_unit_ids)
        evaluation = _frames_for_units(data5_bundle, fold.evaluation_unit_ids)
        job_specs.append((
            MaceJobKind.CROSS_VALIDATION_FOLD, bundle.domain.fold_index, bundle,
            target_full, "target_checkpoint_selection", evaluation,
        ))

    mlcv_run_monitor_records: list[MlcvRunMonitorRecord] = []
    for kind, fold_index, data7, target_full_frames, target_statistical_role, evaluation_frames in job_specs:
        job_id = "final" if fold_index is None else f"fold_{fold_index:02d}"
        job_dir = root / "jobs" / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        levels = {item.target_size: item for item in data7.selection_plan.ladder_levels}
        chosen_size = max(levels) if selection_size is None else int(selection_size)
        if chosen_size not in levels:
            raise TrainingDataInputError(
                f"Requested DATA8 selection size {chosen_size} is not present in the DATA7 ladder {sorted(levels)}."
            )
        selected_frames = levels[chosen_size].frame_uids
        if kind is MaceJobKind.FINAL_DEVELOPMENT and target_size_evaluation_frames is not None:
            if set(selected_frames) & set(target_size_evaluation_frames):
                raise TrainingDataInputError(
                    "Target-size candidate training and development-complement evaluation overlap."
                )
        if local_replay.train_artifact is not None:
            target_geometry = {frame_catalog.frame(uid).geometry_fingerprint for uid in selected_frames}
            overlap = target_geometry & set(local_replay.train_artifact.geometry_identities)
            if overlap:
                raise TrainingDataInputError("Target training and replay training contain exact duplicate geometries.")
            if online_replay_artifact is not None:
                monitor_overlap = target_geometry & set(online_replay_artifact.geometry_identities)
                if monitor_overlap:
                    raise TrainingDataInputError(
                        "Target training and true-label online replay monitoring contain exact duplicate geometries."
                    )
        train_artifact = _write_or_reuse_data8_extxyz_artifact(
            job_dir,
            dataset_id=frame_catalog.dataset_id,
            role="target_train",
            filename="target_train.xyz",
            frame_uids=selected_frames,
            frame_catalog=frame_catalog,
            frame_data_by_run=frame_data_by_run,
            data7_bundle=data7,
            policy=active_extxyz,
            training_weights=data7.training_weights,
            configuration_weight_scale=(
                local_replay.target_weight
                if local_replay.mode is not ReplayMode.NONE
                else 1.0
            ),
            frame_array_index=frame_array_index,
            shared_cache_directory=shared_fixed_file_cache_directory,
        )
        monitor_record = None
        if mlcv_monitor_policy is not None:
            target_full_parent_digest = digest({
                "schema": "mdstats.mlcv-target-full-parent.v1",
                "data5_bundle_digest": data5_bundle.content_digest,
                "job_id": job_id,
                "statistical_role": target_statistical_role,
                "frame_uids": list(target_full_frames),
            })
            training_parent_digest = digest({
                "schema": "mdstats.mlcv-training-parent.v1",
                "data7_bundle_digest": data7.content_digest,
                "selection_size": chosen_size,
                "frame_uids": list(selected_frames),
            })
            monitor_record = build_run_monitor_record(
                job_id=job_id, kind=kind, fold_index=fold_index,
                target_statistical_role=target_statistical_role,
                target_full_frame_uids=target_full_frames,
                training_frame_uids=selected_frames, frame_catalog=frame_catalog,
                policy=mlcv_monitor_policy,
                target_full_parent_digest=target_full_parent_digest,
                training_parent_digest=training_parent_digest,
            )
            mlcv_run_monitor_records.append(monitor_record)
            monitor_frames = monitor_record.target_light_frame_uids
        else:
            monitor_frames = target_full_frames

        valid_artifact = _write_or_reuse_data8_extxyz_artifact(
            job_dir,
            dataset_id=frame_catalog.dataset_id,
            role="target_checkpoint_monitor",
            filename="target_valid.xyz",
            frame_uids=monitor_frames,
            frame_catalog=frame_catalog,
            frame_data_by_run=frame_data_by_run,
            data7_bundle=(None if kind is MaceJobKind.FINAL_DEVELOPMENT else data7),
            policy=active_extxyz,
            frame_array_index=frame_array_index,
            shared_cache_directory=shared_fixed_file_cache_directory,
        )
        artifacts.extend((train_artifact, valid_artifact))
        if monitor_record is not None:
            full_checkpoint_artifact = _write_or_reuse_data8_extxyz_artifact(
                job_dir, dataset_id=frame_catalog.dataset_id,
                role="target_checkpoint_full", filename="target_checkpoint_full.xyz",
                frame_uids=monitor_record.target_full_frame_uids,
                frame_catalog=frame_catalog, frame_data_by_run=frame_data_by_run,
                data7_bundle=(None if kind is MaceJobKind.FINAL_DEVELOPMENT else data7),
                policy=active_extxyz,
                frame_array_index=frame_array_index,
                shared_cache_directory=shared_fixed_file_cache_directory,
            )
            training_diagnostic_artifact = _write_or_reuse_data8_extxyz_artifact(
                job_dir, dataset_id=frame_catalog.dataset_id,
                role="target_training_diagnostic", filename="target_training_diagnostic.xyz",
                frame_uids=monitor_record.training_diagnostic_frame_uids,
                frame_catalog=frame_catalog, frame_data_by_run=frame_data_by_run,
                data7_bundle=data7, policy=active_extxyz,
                frame_array_index=frame_array_index,
                shared_cache_directory=shared_fixed_file_cache_directory,
            )
            artifacts.extend((full_checkpoint_artifact, training_diagnostic_artifact))
        evaluation_artifact = None
        if evaluation_frames is not None:
            evaluation_artifact = _write_or_reuse_data8_extxyz_artifact(
                job_dir,
                dataset_id=frame_catalog.dataset_id,
                role="cross_validation_evaluation",
                filename="fold_evaluation.xyz",
                frame_uids=evaluation_frames,
                frame_catalog=frame_catalog,
                frame_data_by_run=frame_data_by_run,
                data7_bundle=data7,
                policy=active_extxyz,
                frame_array_index=frame_array_index,
                shared_cache_directory=shared_fixed_file_cache_directory,
            )
            evaluation_artifacts.append(evaluation_artifact)

        config = _mace_config(
            job_name=f"{frame_catalog.dataset_id}_{job_id}",
            job_dir=job_dir,
            target_train=train_artifact,
            target_valid=valid_artifact,
            data7_bundle=data7,
            foundation=staged_foundation,
            training_foundation_reference=training_foundation_reference,
            bundle_root=root,
            replay_plan=local_replay,
            replay_valid_artifact=online_replay_artifact,
            optimizer=active_optimizer,
            checkpoint=active_checkpoint,
            real_pt_data_ratio_threshold=real_pt_data_ratio_threshold,
            extxyz_policy=active_extxyz,
        )
        config_path = job_dir / "mace_config.yaml"
        if yaml is None:
            raise TrainingDataInputError("PyYAML is required to emit MACE configuration files.")
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        command_path = job_dir / "run_mace.sh"
        command_path.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "SCRIPT_DIR=\"$(cd -- \"$(dirname -- \"$0\")\" && pwd)\"\n"
            "cd \"$SCRIPT_DIR\"\n"
            "mdstats-mace-train --config mace_config.yaml\n",
            encoding="utf-8",
        )
        command_path.chmod(0o755)
        dry_run = emulate_mace_v0316_loader_dry_run(
            compatibility_probe=compatibility_probe,
            target_train_count=train_artifact.configuration_count,
            target_validation_count=valid_artifact.configuration_count,
            replay_train_count=local_replay.train_count,
            replay_validation_count=(
                local_replay.monitor_count
                if online_replay_artifact is None
                else online_replay_artifact.configuration_count
            ),
            real_pt_data_ratio_threshold=real_pt_data_ratio_threshold,
            checkpoint_policy=active_checkpoint,
            config_path=str(config_path),
        )
        resolved_precision_schedule = None
        if active_optimizer.precision_schedule_policy is not None:
            effective_per_epoch = (
                dry_run.target_train_count_effective + dry_run.replay_train_count_effective
            )
            updates_per_epoch = max(1, effective_per_epoch // active_optimizer.batch_size)
            resolved_precision_schedule = active_optimizer.precision_schedule_policy.resolve(
                max_num_epochs=active_optimizer.max_num_epochs,
                updates_per_epoch=updates_per_epoch,
                require_update_floor=True,
            )
        protocol = TrainingProtocolIdentity(
            training_mode=training_mode,
            foundation_checkpoint=staged_foundation,
            compatibility_probe_digest=compatibility_probe.content_digest,
            data7_bundle_digest=data7.content_digest,
            target_train_artifact_digest=train_artifact.content_digest,
            target_valid_artifact_digest=valid_artifact.content_digest,
            replay_plan_digest=None if local_replay.mode is ReplayMode.NONE else local_replay.content_digest,
            training_objective_policy_digest=data7.training_weights.objective_policy.policy_digest,
            configuration_weight_policy_digest=data7.training_weights.configuration_policy.policy_digest,
            checkpoint_metric_policy_digest=data7.checkpoint_metric_policy.policy_digest,
            checkpoint_control_policy=active_checkpoint,
            optimizer_policy=active_optimizer,
            selection_size=chosen_size,
            real_pt_data_ratio_threshold=real_pt_data_ratio_threshold,
            resolved_precision_schedule=resolved_precision_schedule,
            online_monitor_policy_digest=(
                None if mlcv_monitor_policy is None else mlcv_monitor_policy.policy_digest
            ),
            target_online_monitor_record_digest=(
                None if monitor_record is None else monitor_record.content_digest
            ),
            replay_online_monitor_record_digest=(
                None if replay_monitor_record is None else replay_monitor_record.content_digest
            ),
            replay_valid_artifact_digest=None if online_replay_artifact is None else online_replay_artifact.content_digest,
            adaptive_stop_policy=adaptive_stop_policy,
            training_budget_policy=training_budget_policy,
            learning_rate_schedule_policy=learning_rate_schedule_policy,
            checkpoint_admissibility_policy=checkpoint_admissibility_policy,
            checkpoint_selection_policy=checkpoint_selection_policy,
            selected_head_qualification_digest=(
                None if selected_head_qualification is None else selected_head_qualification.content_digest
            ),
            training_foundation_checkpoint_reference=training_foundation_reference,
            training_foundation_checkpoint_sha256=training_foundation_sha256,
        )
        job = MaceJobArtifact(
            job_id=job_id,
            kind=kind,
            fold_index=fold_index,
            relative_directory=str(job_dir.relative_to(root)),
            config_relative_path=str(config_path.relative_to(root)),
            config_sha256=_sha256_file(config_path),
            command_relative_path=str(command_path.relative_to(root)),
            command_sha256=_sha256_file(command_path),
            target_train_artifact_digest=train_artifact.content_digest,
            target_valid_artifact_digest=valid_artifact.content_digest,
            fold_evaluation_artifact_digest=None if evaluation_artifact is None else evaluation_artifact.content_digest,
            replay_plan_digest=None if local_replay.mode is ReplayMode.NONE else local_replay.content_digest,
            protocol=protocol,
            loader_dry_run=dry_run,
        )
        jobs.append(job)
        (job_dir / "job_manifest.json").write_text(
            json.dumps(job.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
        )

    mlcv_monitor_catalog = None
    if mlcv_monitor_policy is not None:
        if replay_monitor_record is None:
            raise TrainingDataInputError("MLCV-MON1 replay monitor record was not constructed.")
        mlcv_monitor_catalog = MlcvMonitorCatalog(
            role_catalog_digest=mlcv_role_catalog.content_digest,
            policy=mlcv_monitor_policy,
            runs=tuple(mlcv_run_monitor_records),
            replay=replay_monitor_record,
        )

    bundle = Data8PreparationBundle(
        dataset_id=frame_catalog.dataset_id,
        source_catalog_digest=source_catalog.content_digest,
        frame_catalog_digest=frame_catalog.content_digest,
        data5_bundle_digest=data5_bundle.content_digest,
        compatibility_policy=active_compat,
        compatibility_probe=compatibility_probe,
        replay_plan=local_replay,
        jobs=tuple(jobs),
        target_artifacts=tuple(artifacts),
        fold_evaluation_artifacts=tuple(evaluation_artifacts),
        sealed_outer_evaluations=sealed,
        output_directory=str(root),
        online_monitor_policy=online_monitor_policy,
        target_online_monitor=target_online_record,
        replay_online_monitor=replay_online_record,
        online_replay_monitor_artifact=online_replay_artifact,
        full_target_evaluation_artifact=full_target_evaluation_artifact,
        mlcv_role_catalog=mlcv_role_catalog,
        mlcv_monitor_catalog=mlcv_monitor_catalog,
        replay_full_validation_artifact=replay_full_validation_artifact,
        notes=(
            "DATA8 emits fixed-file MACE artifacts only; it does not execute training or activate locked tests.",
            "Cross-validation evaluation XYZ files are excluded from every MACE training configuration.",
            "MLCV-MON1 uses V_i_light for fold MACE validation and D_light for final-run MACE validation; complete V_i_full/D_full domains are materialized separately.",
            "TRUE_DFT replay validation is materialized as R_light for per-epoch MACE validation and R_full for later authoritative selection.",
            "Target training-diagnostic monitors are materialized from gradient-training membership and carry no selection authority.",
            "Foundation and replay resources are staged under shared/ and every MACE config uses relocatable relative paths.",
            f"Selected DATA7 ladder size: {max(final_bundles[0].selection_plan.ladder_levels, key=lambda item: item.target_size).target_size if selection_size is None else selection_size}.",
        ),
    )
    (root / "data8_bundle.json").write_text(
        json.dumps(bundle.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
    )
    (root / "mlcv_role_catalog.json").write_text(
        json.dumps(mlcv_role_catalog.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if mlcv_monitor_catalog is not None:
        (root / "mlcv_monitor_catalog.json").write_text(
            json.dumps(mlcv_monitor_catalog.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return bundle
