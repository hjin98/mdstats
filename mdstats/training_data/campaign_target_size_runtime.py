"""Current production target-size orchestration for `prepare` and `select-target-size`.

This module is the only production orchestration for target-size work after the
runtime cutover.  It owns *sequencing* and nothing scientific: candidate
qualification, the split, training and evaluation order, reducer advancement,
candidate realization, materialization, TRAIN2 continuation, EVAL2 reduction,
immutable publication, and crash replay all remain with their accepted P1, P2,
and P3 owners.  What lives here is the call order between those owners and the
campaign store, plus the process launcher that gives one candidate rung to MACE.

The division of labour between the two public commands is deliberate and
enforced:

``prepare`` reconstructs the current scientific substrate - P1 source and frame
authority, the neutral statistical base, the P2 experiment definition, and the
one common preparation - all of which are deterministic and independent of any
candidate size.  It cannot select ``N``, run the reducer, train a candidate, or
rank anything, and there is no code path here by which it could.

``select-target-size`` owns the screen.  It reconciles the existing P3 root
before scheduling anything new, derives the active matrix from the authenticated
reducer state, executes only the surviving cells through P3 owners, publishes
through P3, reconciles, and CAS-adopts the exact reconciled head - repeating
only while the P2 reducer says the experiment is nonterminal.

Expensive numerical work has exactly one seam, below the accepted owner
boundary: :class:`TargetSizeBoundaryTrainer` produces the TRAIN2 runtime summary
for one rung.  Everything above it - configuration parsing, authority
construction, materialization validation, provider and checkpoint
authentication, publication, reconciliation, and adoption - is real production
code in every invocation.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence
import json
import os
import shutil
import subprocess
import sys
import time

from ._common import TrainingDataError, TrainingDataInputError
from .campaign_target_size_paths import (
    TARGET_SIZE_EXECUTION_ROOT_NAME,
    target_size_execution_root,
    target_size_execution_root_locator,
)
from .precision_runtime import MACE_RESTART_EPOCH_ENVIRONMENT_VARIABLE


class TargetSizeRuntimeError(TrainingDataError):
    """The current target-size runtime cannot proceed."""


# ---------------------------------------------------------------------------
# Current scientific authority construction (shared by both commands)
# ---------------------------------------------------------------------------


def resolve_neutral_partition_policy(cfg: Mapping[str, Any]) -> Any:
    """Map the campaign ``[partition]`` namespace onto the P1 partition policy.

    This is configuration translation only.  Every value comes from the same
    ``[partition]`` keys the rest of the campaign already exposes, and every
    unset key keeps the accepted P1 default, so the neutral substrate's own
    policy remains the authority on what these settings mean.
    """

    import mdstats
    from ._campaign_cli_core import _cfg
    from .neutral_substrate import NeutralPartitionPolicy, NeutralRoleBudget

    defaults = NeutralRoleBudget()
    policy_defaults = NeutralPartitionPolicy()
    block_defaults = policy_defaults.block_policy
    explicit_block = _cfg(cfg, "partition", "explicit_block_length_frames", None)
    return NeutralPartitionPolicy(
        role_budget=NeutralRoleBudget(
            development_minimum_independent_units=int(
                _cfg(
                    cfg,
                    "partition",
                    "development_minimum_independent_units",
                    defaults.development_minimum_independent_units,
                )
            ),
            outer_monitor_minimum_independent_units=int(
                _cfg(
                    cfg,
                    "partition",
                    "outer_monitor_minimum_independent_units",
                    defaults.outer_monitor_minimum_independent_units,
                )
            ),
            calibration_minimum_independent_units=int(
                _cfg(
                    cfg,
                    "partition",
                    "calibration_minimum_independent_units",
                    defaults.calibration_minimum_independent_units,
                )
            ),
            locked_interpolation_test_minimum_independent_units=int(
                _cfg(
                    cfg,
                    "partition",
                    "locked_interpolation_test_minimum_independent_units",
                    defaults.locked_interpolation_test_minimum_independent_units,
                )
            ),
            purge_units_between_roles=int(
                _cfg(
                    cfg,
                    "partition",
                    "purge_units_between_roles",
                    defaults.purge_units_between_roles,
                )
            ),
            allow_calibration_deferral=bool(
                _cfg(
                    cfg,
                    "partition",
                    "allow_calibration_deferral",
                    defaults.allow_calibration_deferral,
                )
            ),
        ),
        block_policy=mdstats.CompleteFrameBlockPolicy(
            minimum_block_frames=int(
                _cfg(
                    cfg,
                    "partition",
                    "minimum_block_frames",
                    block_defaults.minimum_block_frames,
                )
            ),
            explicit_block_length_frames=(
                None if explicit_block is None else int(explicit_block)
            ),
        ),
        minimum_units_per_condition_for_full_outer_roles=int(
            _cfg(
                cfg,
                "partition",
                "minimum_units_per_condition_for_full_outer_roles",
                policy_defaults.minimum_units_per_condition_for_full_outer_roles,
            )
        ),
    )


#: Canonical-frame construction runs in one-shot worker processes, so it pays a
#: roughly fixed interpreter/task-serialization cost before any per-run work.
#: Measured on the repository benchmark
#: (``benchmarks/benchmark_mlff_p4_authority_reconstruction.py``) that cost only
#: repays itself once the corpus is materially larger than this; below it the
#: parallel plan is a real slowdown, so small campaigns stay serial.
CANONICAL_FRAME_PARALLEL_ATOM_FRAME_FLOOR = 8192


def _canonical_frame_worker_ceiling(atom_frames: int) -> int | None:
    """Bound canonical-frame workers by the work actually available."""

    if int(atom_frames) < CANONICAL_FRAME_PARALLEL_ATOM_FRAME_FLOOR:
        return 1
    return None


@contextmanager
def _authority_stage(label: str) -> Any:
    """Report begin/end of one post-DATA4 authority-construction stage.

    Purely diagnostic.  Nothing emitted here participates in any scientific
    digest, persisted campaign state, generation identity, replay identity, or
    result schema; it exists so the expensive phase after DATA4 restoration is
    observable rather than silent.
    """

    from .progress_timing import format_progress_time

    print(f"[authority] {label}; status=start", flush=True)
    started = time.monotonic()
    try:
        yield
    finally:
        print(
            f"[authority] {label}; status=complete; "
            f"elapsed={format_progress_time(time.monotonic() - started)}",
            flush=True,
        )


@dataclass(frozen=True, slots=True)
class CurrentTargetSizeAuthorities:
    """One complete P1/P2/P3-common authority bundle for a generation.

    ``prepare`` builds this from live source inputs through the accepted owners
    and publishes it as an immutable prepared generation.  Every later command
    obtains the same bundle by loading that published generation, so a
    downstream command never reinterprets live source bytes it does not own and
    never pays O(dataset) reconstruction to establish currentness.
    """

    manifest: Any
    source_catalog: Any
    source_authority: Any
    frame_authority: Any
    feature_evidence: Any
    neutral_base: Any
    split_exclusion: Any
    aggregate: Any
    common: Any
    frame_catalog: Any
    frame_data_by_run: Mapping[str, Any]
    frame_array_index: Mapping[str, Any]
    frame_records: tuple[Mapping[str, Any], ...] = ()

    @property
    def components(self) -> dict[str, Any]:
        """Publishable prepared components, keyed by prepared-manifest name."""

        return {
            "manifest": self.manifest,
            "source_catalog": self.source_catalog,
            "frame_catalog": self.frame_catalog,
            "source_authority": self.source_authority,
            "frame_authority": self.frame_authority,
            "feature_evidence": self.feature_evidence,
            "neutral_base": self.neutral_base,
            "split_exclusion": self.split_exclusion,
            "aggregate": self.aggregate,
            "common": self.common,
        }

    @property
    def identity(self) -> dict[str, str]:
        return {
            "frame_authority_digest": self.frame_authority.content_digest,
            "neutral_statistical_base_digest": self.neutral_base.content_digest,
            "split_exclusion_digest": self.split_exclusion.content_digest,
            "policy_digest": self.aggregate.policy.content_digest,
            "experiment_definition_digest": self.aggregate.definition.content_digest,
            "aggregate_digest": self.aggregate.content_digest,
        }


def build_prepared_target_size_substrate(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    data4: Any | None = None,
) -> CurrentTargetSizeAuthorities:
    """Build the P1 -> P2 -> P3-common chain through its owners.

    This is the **prepare-only** construction boundary.  It performs fresh P1
    authentication against the real source files and is the single place where
    live inputs are interpreted.  No downstream command may call it, directly or
    as a fallback: a missing or corrupt prepared generation fails closed with
    guidance to run `prepare`, because silently rebuilding the substrate under a
    generation that already owns immutable evidence would rebind that evidence
    to a scientific state nobody accepted.

    ``data4`` may be supplied when the caller has just constructed and validated
    the bundle in this same invocation, so cold preparation does not persist a
    sharded DATA4 record and immediately restore it again.
    """

    import mdstats
    from ._campaign_cli_core import (
        _ensure_manifest,
        _load_or_rebuild_frame_data,
        _path_cfg,
        _resolve_feature_worker_count,
    )
    from ._frame_access import build_frame_array_index
    from .neutral_substrate import (
        authenticate_vasp_source_authority,
        authenticated_vasp_temperature_targets,
        build_canonical_frame_authority,
        build_neutral_feature_evidence_from_data4_bundle,
        build_neutral_split_exclusion_evidence,
        build_neutral_statistical_base,
        build_source_authority_from_data2_catalog,
    )
    from .target_size_execution import (
        build_target_size_common_preparation,
        resolve_target_size_common_training_policy,
    )
    from .target_size_experiment import (
        build_target_size_statistical_aggregate,
        resolve_target_size_policy_from_config,
    )

    training_root = _path_cfg(cfg, paths, "training_root")
    if training_root is None:
        raise TargetSizeRuntimeError(
            "The current target-size runtime requires [data].training_root."
        )
    manifest = _ensure_manifest(cfg, paths, approve=False)
    source_catalog = store.get_record(
        "source_catalog", mdstats.TrainingDataSourceCatalog
    )
    if data4 is None:
        data4 = store.get_record("data4", mdstats.Data4FeatureBundle)
    frame_catalog = store.get_record("frame_catalog", mdstats.TrainingFrameCatalog)

    with _authority_stage("P1 source authority"):
        source_authority = build_source_authority_from_data2_catalog(
            source_catalog, manifest=manifest
        )
    # Fresh P1 authentication is mandatory and independent of how the
    # normalized payload is acquired: it re-proves source identity, control
    # interpretation, companion bindings, the ensemble certificate and its
    # value, and the selected energy channel name/units/semantic role against
    # the actual files, without reading a single frame.
    with _authority_stage("P1 source authentication"):
        authenticated = authenticate_vasp_source_authority(
            source_authority, base_directory=training_root
        )
    # One normalized-frame acquisition per invocation.  Canonical-frame
    # construction and common preparation both consume this exact mapping, so
    # a warm cache performs no source frame read at all and a rebuild performs
    # exactly one read per source.
    with _authority_stage("normalized frame data"):
        frame_data_by_run, frame_records = _load_or_rebuild_frame_data(
            cfg, paths, source_catalog
        )
    with _authority_stage("P1 canonical frame authority"):
        canonical_atom_frames = sum(
            int(data.n_frames) * int(data.n_atoms)
            for data in frame_data_by_run.values()
        )
        canonical_workers, canonical_resources = _resolve_feature_worker_count(
            cfg,
            run_count=len(frame_data_by_run),
            estimated_bytes_per_worker=384 * 1024**2,
            reserved_bytes=sum(
                int(data.n_frames) for data in frame_data_by_run.values()
            )
            * 8192,
            startup_sensitive=True,
            maximum_workers=_canonical_frame_worker_ceiling(canonical_atom_frames),
        )
        print(
            f"[canonical frames] resource plan: {canonical_workers} isolated run "
            f"worker(s); {canonical_resources.summary()}",
            flush=True,
        )
        frame_authority = build_canonical_frame_authority(
            source_authority,
            frame_data_by_run,
            temperature_targets_by_run=authenticated_vasp_temperature_targets(
                authenticated
            ),
            parallel_workers=canonical_workers,
            progress_callback=lambda message: print(
                f"[canonical frames] {message}", flush=True
            ),
        )
    with _authority_stage("neutral statistical substrate"):
        feature_evidence = build_neutral_feature_evidence_from_data4_bundle(
            source_authority, frame_authority, data4
        )
        neutral_base = build_neutral_statistical_base(
            source_authority,
            frame_authority,
            feature_evidence,
            policy=resolve_neutral_partition_policy(cfg),
        )
        split_exclusion = build_neutral_split_exclusion_evidence(
            frame_authority, neutral_base
        )
    with _authority_stage("P2 target-size aggregate"):
        aggregate = build_target_size_statistical_aggregate(
            frame_authority,
            neutral_base,
            policy=resolve_target_size_policy_from_config(cfg),
        )
    with _authority_stage("P3 common preparation"):
        frame_array_index = build_frame_array_index(frame_catalog, frame_data_by_run)
        # The configured [objective] reaches the screen through the same
        # resolver post-selection uses; target-size preparation never falls back
        # to library defaults that merely happen to agree with it.
        common = build_target_size_common_preparation(
            aggregate,
            frame_catalog=frame_catalog,
            frame_data_by_run=frame_data_by_run,
            frame_array_index=frame_array_index,
            policy=resolve_target_size_common_training_policy(cfg),
        )
    return CurrentTargetSizeAuthorities(
        manifest=manifest,
        source_catalog=source_catalog,
        source_authority=source_authority,
        frame_authority=frame_authority,
        feature_evidence=feature_evidence,
        neutral_base=neutral_base,
        split_exclusion=split_exclusion,
        aggregate=aggregate,
        common=common,
        frame_catalog=frame_catalog,
        frame_data_by_run=frame_data_by_run,
        frame_array_index=frame_array_index,
        frame_records=frame_records,
    )


def load_prepared_target_size_generation(
    cfg: Mapping[str, Any], paths: Any, store: Any, revision: Any
) -> CurrentTargetSizeAuthorities:
    """Load the immutable prepared generation bound to ``revision``.

    This is the one canonical downstream consumption owner.  It authenticates
    the published components against the exact manifest the campaign store
    binds, then rebuilds only the cheap derived index that P3 materialization
    needs.  It performs no source parsing, no DATA4 restore, and no P1/P2/P3
    reconstruction, and it never falls back to the prepare builder.
    """

    from ._frame_access import build_frame_array_index
    from .campaign_prepared_generation import (
        PreparedGenerationConfigurationError,
        PreparedGenerationError,
        PreparedGenerationMissingError,
        load_prepared_frame_data,
        load_prepared_generation_components,
        read_prepared_generation_manifest,
    )

    state = revision.state
    manifest_digest = state.prepared_manifest_digest
    if manifest_digest is None:
        raise PreparedGenerationMissingError(
            f"Canonical target-size generation {state.generation} was prepared by an "
            "earlier implementation that persisted only scientific identities and no "
            "immutable prepared substrate. It is not reinterpreted or retrofitted "
            "from live sources. Run `prepare` once to bind a fresh generation; the "
            "existing screen evidence stays historical under its own generation."
        )
    manifest = read_prepared_generation_manifest(paths, manifest_digest)
    # Preparation-owned configuration is checked before anything is loaded. It
    # is a pure config projection, so it costs nothing, and mixing a changed
    # preparation policy into an already published generation would silently
    # reinterpret evidence that was accepted under the old one.
    changed = manifest.changed_preparation_configuration(cfg)
    if changed:
        raise PreparedGenerationConfigurationError(
            "The preparation-owned configuration changed after canonical generation "
            f"{state.generation} was prepared ({', '.join(changed)}). Run `prepare` to "
            "bind a fresh canonical generation; prior evidence is never reinterpreted "
            "under a changed preparation policy."
        )
    components = load_prepared_generation_components(paths, manifest)
    frame_data_by_run = load_prepared_frame_data(
        paths, manifest, components["source_catalog"]
    )
    frame_catalog = components["frame_catalog"]
    frame_array_index = build_frame_array_index(frame_catalog, frame_data_by_run)
    authorities = CurrentTargetSizeAuthorities(
        manifest=components["manifest"],
        source_catalog=components["source_catalog"],
        source_authority=components["source_authority"],
        frame_authority=components["frame_authority"],
        feature_evidence=components["feature_evidence"],
        neutral_base=components["neutral_base"],
        split_exclusion=components["split_exclusion"],
        aggregate=components["aggregate"],
        common=components["common"],
        frame_catalog=frame_catalog,
        frame_data_by_run=frame_data_by_run,
        frame_array_index=frame_array_index,
        frame_records=manifest.frame_records,
    )
    observed = authorities.identity
    for name, value in observed.items():
        if getattr(state, name) != value:
            raise PreparedGenerationError(
                "The prepared scientific substrate published for this campaign "
                f"generation does not match the identity the campaign store binds "
                f"({name}). This is durable-state corruption; run `prepare` to bind a "
                "fresh canonical generation rather than reinterpreting the old one."
            )
    if state.common_preparation_digest != authorities.common.content_digest:
        raise PreparedGenerationError(
            "The prepared common preparation does not match the digest the campaign "
            "store binds for this canonical generation."
        )
    return authorities


def load_prepared_target_size_definition(
    cfg: Mapping[str, Any], paths: Any, store: Any, revision: Any
) -> Any:
    """Read and authenticate only the P2 experiment definition for ``revision``.

    Manual selection needs only this definition to authenticate qualified candidate
    sizes and exact T_N membership identity. It performs zero frame-data loading,
    zero index construction, and zero P3 preparation.
    """

    from .campaign_prepared_generation import (
        PreparedGenerationConfigurationError,
        PreparedGenerationError,
        PreparedGenerationMissingError,
        load_prepared_target_size_definition as _load_prepared_definition,
        read_prepared_generation_manifest,
    )

    state = revision.state
    manifest_digest = state.prepared_manifest_digest
    if manifest_digest is None:
        raise PreparedGenerationMissingError(
            f"Canonical target-size generation {state.generation} was prepared by an "
            "earlier implementation that persisted only scientific identities and no "
            "immutable prepared substrate. It is not reinterpreted or retrofitted "
            "from live sources. Run `prepare` once to bind a fresh generation; the "
            "existing screen evidence stays historical under its own generation."
        )
    manifest = read_prepared_generation_manifest(paths, manifest_digest)
    changed = manifest.changed_preparation_configuration(cfg)
    if changed:
        raise PreparedGenerationConfigurationError(
            "The preparation-owned configuration changed after canonical generation "
            f"{state.generation} was prepared ({', '.join(changed)}). Run `prepare` to "
            "bind a fresh canonical generation; prior evidence is never reinterpreted "
            "under a changed preparation policy."
        )
    aggregate_digest = manifest.component_digests.get("aggregate")
    if aggregate_digest is None:
        raise PreparedGenerationError("Manifest missing 'aggregate' component digest.")
    expected_aggregate = manifest.scientific_identity.get("aggregate_digest")
    if (
        state.aggregate_digest is not None
        and expected_aggregate is not None
        and expected_aggregate != state.aggregate_digest
    ):
        raise PreparedGenerationError(
            "The prepared aggregate component does not match the digest the campaign "
            "store binds for this canonical generation."
        )
    definition = _load_prepared_definition(paths, manifest)
    if (
        state.experiment_definition_digest is not None
        and definition.content_digest != state.experiment_definition_digest
    ):
        raise PreparedGenerationError(
            "The prepared experiment definition does not match the digest the "
            "campaign store binds for this canonical generation."
        )
    return definition


current_target_size_execution_root = target_size_execution_root
current_target_size_execution_root_locator = target_size_execution_root_locator


# ---------------------------------------------------------------------------
# The one expensive-work seam: executing a single candidate rung
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TargetSizeRungRequest:
    """Everything a TRAIN2 rung needs, already authenticated by P3 owners."""

    plan: Any
    trajectory: Any
    materialization: Any
    materialization_directory: Path
    checkpoint_directory: Path
    start_epoch: int
    optimizer_policy: Any


class TargetSizeBoundaryTrainer(Protocol):
    """Execute one candidate rung and return its TRAIN2 runtime summary.

    This is the only accepted substitution point for expensive numerical work.
    It sits strictly below the owner boundary: the trajectory, materialization,
    rung plan, predecessor continuation, and checkpoint workspace handed to it
    were all produced and validated by real P3 owners, and everything it returns
    is re-authenticated by ``bind_target_size_boundary_state`` before it can
    become evidence.
    """

    def __call__(self, request: TargetSizeRungRequest) -> Any:
        ...


_MACE_CONFIG_PASSTHROUGH_KEYS = (
    "name",
    "seed",
    "atomic_numbers",
    "E0s",
    "energy_key",
    "forces_key",
    "stress_key",
    "lr",
    "loss",
    "energy_weight",
    "forces_weight",
    "stress_weight",
    "batch_size",
    "valid_batch_size",
    "num_workers",
    "max_num_epochs",
    "ema",
    "ema_decay",
    "amsgrad",
    "weight_decay",
    "clip_grad",
    "default_dtype",
    "device",
    "compute_avg_num_neighbors",
    "multiheads_finetuning",
)

#: The one canonical P3 dataset-head namespace.  It is the name of the model
#: head MACE actually builds, so real TRAIN2 and EVAL2 reconstruction agree.
TARGET_SIZE_MACE_HEAD_NAME = "target_head"


def mace_run_configuration(target_size_config: Mapping[str, Any]) -> dict[str, Any]:
    """Translate the canonical P3 candidate configuration into MACE arguments.

    P3 owns the scientific description of a candidate run - exact membership
    files, the common E0 mapping, the frozen optimizer policy, and the
    architecture.  MACE's command line expects its own key names and its own
    scalar-literal spelling, so this adapter renames, projects, and re-spells
    without deciding anything: no value here is computed, defaulted, or
    overridden, and the canonical configuration is left untouched.
    """

    from .mace_compatibility import (
        encode_mace_executable_configuration,
        project_mace_architecture_arguments,
    )
    from .target_size_execution import TARGET_SIZE_MACE_CONFIG_SCHEMA

    if target_size_config.get("schema") != TARGET_SIZE_MACE_CONFIG_SCHEMA:
        raise TargetSizeRuntimeError(
            "Candidate MACE configuration does not carry the accepted P3 schema."
        )
    config: dict[str, Any] = {
        key: target_size_config[key]
        for key in _MACE_CONFIG_PASSTHROUGH_KEYS
        if key in target_size_config
    }
    config["train_file"] = target_size_config["target_train_file"]
    config["valid_file"] = target_size_config["target_valid_file"]
    if bool(target_size_config.get("multiheads_finetuning")):
        raise TargetSizeRuntimeError(
            "P3 target-size screening is one-head scratch training; multihead "
            "fine-tuning is not an admissible candidate configuration."
        )
    if config.get("compute_avg_num_neighbors") is not False:
        raise TargetSizeRuntimeError(
            "Candidate MACE configuration must disable MACE's candidate-local "
            "average-neighbor recomputation; the common preparation owns that "
            "normalization."
        )
    # Without an explicit dataset-head mapping pinned MACE falls back to its
    # own ``Default`` namespace and builds a differently named head from the
    # one the canonical configuration reconstructs.  The mapping projected here
    # is the canonical P3 target dataset mapping itself, not the internal
    # architecture head list.
    multi_head = target_size_config.get("multi_head")
    if not isinstance(multi_head, Mapping) or set(multi_head) != {
        TARGET_SIZE_MACE_HEAD_NAME
    }:
        raise TargetSizeRuntimeError(
            "Candidate MACE configuration must expose exactly the "
            f"{TARGET_SIZE_MACE_HEAD_NAME!r} target dataset head."
        )
    config["heads"] = {
        name: dict(head) for name, head in multi_head.items()
    }
    for key, value in project_mace_architecture_arguments(
        target_size_config.get("mace_architecture")
    ).items():
        # The architecture is canonicalized by the model-feature owner; it never
        # overrides an optimizer or data key the candidate configuration set.
        config.setdefault(key, value)
    try:
        return encode_mace_executable_configuration(config)
    except TrainingDataInputError as exc:
        raise TargetSizeRuntimeError(
            f"Candidate MACE configuration cannot be spelled for MACE: {exc}"
        ) from exc


@dataclass(frozen=True, slots=True)
class MaceTargetSizeBoundaryTrainer:
    """Production rung executor: run MACE through the qualified wrapper.

    The wrapper is the same qualified ``mdstats-mace-train`` entry point the
    rest of the campaign uses, so critical-precision policy, warning handling,
    and the TRAIN2 runtime hooks are all active.  The rung plan travels in the
    environment exactly as it does for ordinary campaign training, which is what
    makes exact completed-epoch continuation work.
    """

    wrapper_path: Path
    environment: Mapping[str, str] | None = None
    timeout_seconds: float | None = None

    def __call__(self, request: TargetSizeRungRequest) -> Any:
        import mdstats

        run_root = request.checkpoint_directory.parent
        model_dir = run_root / "models"
        log_dir = run_root / "logs"
        result_dir = run_root / "results"
        for directory in (
            model_dir,
            log_dir,
            result_dir,
            request.checkpoint_directory,
        ):
            directory.mkdir(parents=True, exist_ok=True)

        source = json.loads(
            (
                request.materialization_directory
                / request.materialization.mace_config_relative_path
            ).read_text(encoding="utf-8")
        )
        run_config = mace_run_configuration(source)
        config_path = run_root / "mace_run_config.yaml"
        config_path.write_text(
            json.dumps(run_config, indent=2, sort_keys=True), encoding="utf-8"
        )

        authority = None
        # Production P3 materializations always carry these authenticated
        # fields.  The parser-boundary probe intentionally supplies only the
        # config-file seam, so it remains a parser test rather than an
        # incomplete training-authority test.
        if all(
            hasattr(request.materialization, name)
            for name in ("target_train_artifact", "mace_config_digest")
        ) and hasattr(request.trajectory, "candidate_training_protocol_digest"):
            from .mace_compatibility import (
                MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE,
                build_mace_execution_authority,
                mace_frame_uid_set_digest,
                mace_execution_authority_to_environment,
            )

            target_artifact = request.materialization.target_train_artifact
            target_uid_digest = None
            if hasattr(target_artifact, "frame_uids"):
                target_uid_digest = mace_frame_uid_set_digest(target_artifact.frame_uids)
            configured_ema = bool(run_config["ema"])
            authority = build_mace_execution_authority(
                role="target_size",
                config_digest=request.materialization.mace_config_digest,
                method_identity_digest=request.trajectory.candidate_training_protocol_digest,
                loss_family=run_config["loss"],
                learning_rate=float(run_config["lr"]),
                ema=configured_ema,
                ema_decay=(
                    None if not configured_ema else float(run_config["ema_decay"])
                ),
                multiheads_finetuning=False,
                force_mh_ft_lr=None,
                real_pt_data_ratio_threshold=None,
                target_train_count=int(request.trajectory.realization.target_train_count),
                replay_train_count=0,
                batch_size=int(request.trajectory.realization.batch_size),
                target_updates_per_epoch=int(
                    request.trajectory.realization.updates_per_epoch
                ),
                target_drop_last=False,
                distributed_allowed=False,
                target_frame_uid_set_digest=target_uid_digest,
                replay_frame_uid_set_digest=None,
                target_head_name="target_head",
                replay_head_name="pt_head",
            )

        environment = dict(os.environ)
        environment.update(dict(self.environment or {}))
        # This transport is derived after the authenticated materialization and
        # intentionally overrides any ambient/injected value.
        if authority is not None:
            environment[MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE] = (
                mace_execution_authority_to_environment(authority)
            )
        environment[mdstats.TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE] = json.dumps(
            request.plan.to_dict(), sort_keys=True, separators=(",", ":")
        )
        environment["PYTHONHASHSEED"] = str(int(request.trajectory.optimizer_seed))
        # The qualified wrapper verifies the raw checkpoint epoch MACE actually
        # loaded against the epoch this launcher intended to continue from, so
        # that intent has to travel with the launch.  ``start_epoch`` is the
        # authenticated *completed*-epoch predecessor boundary supplied by P3,
        # while TRAIN2's raw MACE checkpoint epochs are zero-based; hence the
        # -1.  A fresh rung has no predecessor continuation authority at all, so
        # an ambient or injected value is cleared rather than inherited.
        if request.start_epoch > 0:
            environment[MACE_RESTART_EPOCH_ENVIRONMENT_VARIABLE] = str(
                int(request.start_epoch) - 1
            )
        else:
            environment.pop(MACE_RESTART_EPOCH_ENVIRONMENT_VARIABLE, None)
        command = [
            str(self.wrapper_path),
            "--config",
            str(config_path),
            "--model_dir",
            str(model_dir),
            "--checkpoints_dir",
            str(request.checkpoint_directory),
            "--log_dir",
            str(log_dir),
            "--results_dir",
            str(result_dir),
        ]
        if request.start_epoch > 0:
            command.append("--restart_latest")
        completed = subprocess.run(
            command,
            cwd=str(request.materialization_directory),
            env=environment,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise TargetSizeRuntimeError(
                "Candidate TRAIN2 rung failed for "
                f"n={request.trajectory.target_size} "
                f"seed={request.trajectory.optimizer_seed} "
                f"boundary={request.plan.execution_epoch_limit}: "
                f"exit status {completed.returncode}. Logs: {log_dir}"
            )
        return mdstats.load_train2_runtime_summary(request.checkpoint_directory)


# ---------------------------------------------------------------------------
# `prepare`: reconstruct the current substrate; never select N
# ---------------------------------------------------------------------------


def _changed_preparation_inputs(
    cfg: Mapping[str, Any], paths: Any, store: Any
) -> tuple[str, ...]:
    """Human-readable reasons the stored catalog no longer describes the inputs.

    ``prepare`` owns input change detection because it is the only command
    permitted to interpret live sources at all.  The comparison is made from
    identities the campaign already persisted -- the approved manifest digest
    the DATA2 catalog was built against, and each source's own byte-identity
    and control signatures -- so nothing here is a second freshness authority,
    a modification-time heuristic, or a new registry.  An empty result means
    the stored lower-level catalog may be reused; a non-empty one routes to the
    existing catalog reconstruction owner, which re-applies every source,
    quality, and approval rule.
    """

    import mdstats
    from ._campaign_cli_core import _ensure_manifest, _path_cfg
    from .neutral_substrate import (
        build_source_authority_from_data2_catalog,
        changed_vasp_source_identities,
    )

    training_root = _path_cfg(cfg, paths, "training_root")
    if training_root is None:
        return ()
    try:
        source_catalog = store.get_record(
            "source_catalog", mdstats.TrainingDataSourceCatalog
        )
    except TrainingDataError:
        # An unreadable catalog is not a source change; the owner that needs it
        # reports it precisely.
        return ()
    manifest = _ensure_manifest(cfg, paths, approve=False)
    reasons: list[str] = []
    if source_catalog.manifest_digest != manifest.content_digest:
        reasons.append(
            "the approved training manifest is no longer the one DATA2 was built "
            f"from ({source_catalog.manifest_digest[:12]}... -> "
            f"{manifest.content_digest[:12]}...)"
        )
    else:
        source_authority = build_source_authority_from_data2_catalog(
            source_catalog, manifest=manifest
        )
        changed = changed_vasp_source_identities(
            source_authority, base_directory=training_root
        )
        if changed:
            reasons.append(
                "source or companion bytes changed for "
                + ", ".join(repr(run_id) for run_id in changed)
            )
    return tuple(reasons)


def execute_current_prepare(args: Any) -> int:
    """Rebuild the current target-size scientific substrate.

    This performs, resumes, or reuses the destructive generation cutover and
    then binds the reconstructed P1/P2 identities plus the one common
    preparation.  It deliberately stops there: no candidate is selected,
    trained, materialized, or ranked, and the P2 reducer is not advanced.
    """

    from ._campaign_cli_core import (
        CampaignStore,
        StageState,
        _ensure_manifest,
        _load_config,
        _mark_stage,
        _ok,
        _prepare_catalog,
        _print_header,
        _prepare_single_source_replay,
        _replay_topology_preflight,
        _require_stage_complete,
    )
    from .campaign_prepared_generation import (
        preparation_configuration_identity,
        publish_prepared_generation,
    )
    from .campaign_target_size_cutover import ensure_current_target_size_authorities
    from .campaign_target_size_state import ensure_target_size_campaign_revision
    from .campaign_target_size_view import (
        write_current_target_size_result_view,
        write_target_size_result_view,
    )

    cfg, paths = _load_config(args.config)
    store = CampaignStore(paths.state_db)
    _require_stage_complete(store, paths, "doctor")
    # Cheap canonical configuration/topology validation first.  A conflicting
    # replay selector, a malformed exact split domain, a mixed replay
    # interface, or a replay declaration incompatible with the resolved
    # training mode is knowable here, and must not cost a full target-source
    # rebuild, a replay-wide parse, or a model load before it is reported.
    _replay_topology_preflight(cfg, paths)
    refresh_inferences = bool(getattr(args, "refresh_inferences", False))
    if bool(getattr(args, "approve_manifest", False)):
        # Approval is an operator gate on the exact reviewed manifest digest and
        # is recorded here, before any preparation stage is opened.  Continuing
        # in the same invocation is the explicit `--continue-after-approval`
        # opt-in; otherwise this returns without constructing P1/P2 authorities.
        _print_header("Approving the reviewed training manifest")
        manifest = _ensure_manifest(
            cfg, paths, approve=True, refresh_inferences=refresh_inferences
        )
        _ok(
            f"approved manifest {paths.manifest} "
            f"({len(manifest.runs)} runs; digest {manifest.content_digest[:12]}...)"
        )
        if not bool(getattr(args, "continue_after_approval", False)):
            print(
                "Approval recorded. Next: run `prepare` (no flags) to build the "
                "current target-size scientific substrate.",
                flush=True,
            )
            return 0
    _print_header("Preparing the current target-size scientific substrate")
    _mark_stage(
        store,
        paths,
        "prepare",
        StageState.RUNNING,
        "rebuilding the current P1/P2 substrate and common preparation",
    )
    prepared_data4 = None
    try:
        # The currentness token is captured *before* the expensive construction
        # whose result depends on it. Adoption is fenced against exactly this
        # token, so a competing prepare that publishes a different generation
        # while this one builds cannot be superseded by a stale snapshot that
        # merely finished later.
        expected_start = ensure_target_size_campaign_revision(store).expectation()
        if bool(getattr(args, "rebuild_catalog", False)) or not store.has_record("data5"):
            prepared_data4 = _prepare_catalog(
                cfg,
                paths,
                store,
                approve_manifest=False,
                refresh_inferences=refresh_inferences,
            )["data4"]
        else:
            changed = _changed_preparation_inputs(cfg, paths, store)
            if changed:
                # `prepare` is the only command that may interpret live inputs,
                # so it is the only place a genuine input change can be turned
                # into a fresh generation. Routing it through the existing
                # catalog owner keeps every source/approval rule in force: a
                # malformed or unapproved change still fails there.
                _ok(
                    "preparation inputs changed ("
                    + "; ".join(changed)
                    + "); rebuilding the lower-level catalog through its owner"
                )
                prepared_data4 = _prepare_catalog(
                    cfg,
                    paths,
                    store,
                    approve_manifest=False,
                    refresh_inferences=refresh_inferences,
                )["data4"]
            else:
                _ok(
                    "lower-level source, frame, and feature inputs are unchanged and "
                    "will be re-validated by the current P1 owners"
                )
        authorities = build_prepared_target_size_substrate(
            cfg, paths, store, data4=prepared_data4
        )
        # Publish before adopt: every immutable component and normalized frame
        # member exists and authenticates before the campaign store is asked to
        # make this generation current. An interruption here leaves unreachable
        # content, never a current generation with a missing dependency.
        prepared_manifest = publish_prepared_generation(
            paths,
            components=authorities.components,
            frame_records=authorities.frame_records,
            scientific_identity=authorities.identity,
            preparation_configuration=preparation_configuration_identity(cfg),
        )
        revision = ensure_current_target_size_authorities(
            store,
            authorities.identity,
            common_preparation_digest=authorities.common.content_digest,
            prepared_manifest_digest=prepared_manifest.content_digest,
            expected_start=expected_start,
        )
    except Exception as exc:
        _mark_stage(store, paths, "prepare", StageState.FAILED, str(exc))
        raise
    # Public `prepare` coordinates two *independent* preparation owners; it does
    # not merge them into one scientific generation.  Replay runs after the
    # target-size substrate is bound, so the replay foundation provider is only
    # ever acquired once the earlier prepare-owned model-scale provider has
    # reached its final consumer and been retired.  A replay failure here makes
    # public prepare incomplete without rolling back the independently valid
    # target-size generation.
    try:
        _prepare_single_source_replay(cfg, paths, store)
    except Exception as exc:
        _mark_stage(
            store,
            paths,
            "prepare",
            StageState.FAILED,
            f"replay preparation failed after the target-size generation was "
            f"published (target-size science remains valid): {exc}",
        )
        raise
    _ok(
        "current target-size substrate is bound: canonical generation "
        f"{revision.state.generation}; "
        f"experiment={revision.state.experiment_definition_digest[:12]}...; "
        f"common preparation={authorities.common.content_digest[:12]}..."
    )
    print(
        "`prepare` does not select a target size. The candidate ladder "
        f"{list(authorities.aggregate.definition.qualified_candidate_sizes)} is a "
        "configured experiment definition. `prepare` decides nothing about N: run "
        "`select-target-size <N>` to choose the provisional downstream target size, "
        "or `select-target-size --auto` to run the optional paired-seed diagnostic "
        "first and adopt its recommendation.",
        flush=True,
    )
    # An unchanged generation carrying a complete diagnostic is a legitimate
    # no-op, not a failure. The derived view is a rendering of whatever the
    # campaign state already says, so it is written by the owner that can render
    # that state -- the diagnostic exposure path when a diagnostic is complete,
    # the in-progress writer otherwise. Campaign scientific state is never
    # altered to suit a file.
    view_path = paths.results / "target-size-state.json"
    if revision.state.auto_diagnostic is not None:
        write_current_target_size_result_view(
            cfg, paths, store, path=view_path, expected_revision=revision
        )
    else:
        write_target_size_result_view(view_path, revision)
    _mark_stage(
        store,
        paths,
        "prepare",
        StageState.COMPLETE,
        f"current target-size substrate bound at generation {revision.state.generation}",
    )
    print(
        "Next: `select-target-size <N>` (or `select-target-size --auto`).",
        flush=True,
    )
    return 0


# ---------------------------------------------------------------------------
# `select-target-size`: the provisional target-design entrypoint
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _ScreenContext:
    cfg: Mapping[str, Any]
    paths: Any
    store: Any
    authorities: CurrentTargetSizeAuthorities
    aggregate: Any
    schedule: Any
    context: Any
    optimizer_policy: Any
    correlation_blocks: Mapping[str, str]
    extxyz_policy: Any
    root: Path
    window: Any
    authority: Any
    trainer: TargetSizeBoundaryTrainer
    inference_evaluator: Callable[..., Any] | None


def _bulk_roots(root: Path) -> dict[str, Path]:
    """Campaign-owned bulk roots, all inside the protected execution root."""

    roots = {
        "materialization": root / "bulk" / "materializations",
        "snapshot": root / "bulk" / "snapshots",
        "evaluation": root / "bulk" / "evaluations",
        "train2": root / "bulk" / "train2",
    }
    for path in roots.values():
        path.mkdir(parents=True, exist_ok=True)
    return roots


def build_screen_context(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    revision: Any,
    *,
    trainer: TargetSizeBoundaryTrainer | None = None,
    inference_evaluator: Callable[..., Any] | None = None,
) -> _ScreenContext:
    """Construct the complete P3 screen context for the current generation."""

    from ._campaign_cli_core import (
        _ensure_local_wrappers,
        _optimizer_policy,
        _cfg,
    )
    from .mace_export import MaceExtxyzPolicy
    from .target_size_execution import (
        TargetSizeExecutionResolver,
        TargetSizeRestartAuthority,
        build_target_size_execution_context,
        build_target_size_screen_schedule,
        resolve_target_size_optimizer_normalization_policy,
        initialize_target_size_screen,
        target_size_population_correlation_blocks,
    )

    authorities = load_prepared_target_size_generation(cfg, paths, store, revision)
    aggregate = authorities.aggregate
    definition = aggregate.definition
    schedule = build_target_size_screen_schedule(
        definition.policy.fidelity_epochs,
        normalization_policy=resolve_target_size_optimizer_normalization_policy(cfg),
    )
    seeds = tuple(definition.policy.optimizer_seeds)
    optimizer_policy = _optimizer_policy(
        cfg,
        seed=int(seeds[0]),
        num_workers=int(_cfg(cfg, "training", "num_workers", 0)),
        paths=paths,
        planned_epochs=int(schedule.n3),
    )
    context = build_target_size_execution_context(
        definition,
        authorities.common,
        schedule,
        seed_neutral_optimizer_policy=optimizer_policy,
    )
    aggregate = aggregate.with_reducer_state(
        context.bind(definition, aggregate.reducer_state)
    )
    root = current_target_size_execution_root(paths, revision.state.generation)
    root.mkdir(parents=True, exist_ok=True)
    window = initialize_target_size_screen(
        root, aggregate, context, authorities.common
    )
    blocks = target_size_population_correlation_blocks(
        aggregate, authorities.split_exclusion
    )
    extxyz_policy = MaceExtxyzPolicy()
    authority = TargetSizeRestartAuthority(
        aggregate=aggregate,
        context=context,
        common=authorities.common,
        schedule=schedule,
        seed_neutral_optimizer_policy=optimizer_policy,
        canonical_frame_authority=authorities.frame_authority,
        frame_catalog=authorities.frame_catalog,
        frame_data_by_run=authorities.frame_data_by_run,
        frame_array_index=authorities.frame_array_index,
        correlation_blocks=blocks,
        extxyz_policy=extxyz_policy,
        eval2_policy=context.eval2_metric_policy_digest,
        resolver=TargetSizeExecutionResolver(root),
        bulk_roots=_bulk_roots(root),
        # P3 owns this seam: a forward override is admitted only when the
        # caller actually supplied one, so ordinary production still requires a
        # pinned MACE state dict and refuses any reconstruction fallback.
        allow_forward_override=inference_evaluator is not None,
    )
    if trainer is None:
        trainer = MaceTargetSizeBoundaryTrainer(
            wrapper_path=_ensure_local_wrappers(paths)["mdstats-mace-train"]
        )
    return _ScreenContext(
        cfg=cfg,
        paths=paths,
        store=store,
        authorities=authorities,
        aggregate=aggregate,
        schedule=schedule,
        context=context,
        optimizer_policy=optimizer_policy,
        correlation_blocks=blocks,
        extxyz_policy=extxyz_policy,
        root=root,
        window=window,
        authority=authority,
        trainer=trainer,
        inference_evaluator=inference_evaluator,
    )


def _discard_unaccepted_first_rung_materialization(
    screen: _ScreenContext,
    materialization_directory: Path,
    *,
    target_size: int,
    optimizer_seed: int,
    boundary: int,
) -> None:
    """Remove first-rung attempt scratch, and only ever attempt scratch.

    The caller has already established that this cell needs work, but deleting
    a durable parent graph would be unrecoverable, so the accepted-progress
    check is repeated here rather than assumed.  If any authenticated progress
    exists for this cell the directory is left untouched and the ordinary
    recovery owner keeps authority over it.
    """

    if not materialization_directory.exists():
        return
    resolver = screen.authority.resolver
    progress_path = resolver.progress_path(
        screen.window.content_digest, int(boundary), int(target_size), int(optimizer_seed)
    )
    if progress_path.exists():
        raise TargetSizeRuntimeError(
            "A first-rung cell with accepted durable progress reached fresh "
            "execution; its materialization is accepted evidence and is owned "
            "by boundary recovery, not by a new attempt."
        )
    shutil.rmtree(materialization_directory)


def _execute_candidate_cell(
    screen: _ScreenContext, *, target_size: int, optimizer_seed: int, boundary: int, state: Any
) -> Any:
    """Run one candidate cell, fencing first-rung scratch by logical cell.

    The first-rung materialization directory is the deterministic identity of a
    logical ``(target_size, optimizer_seed)`` cell.  Its adjacent advisory lock
    is an execution fence, not scientific state: it serializes cleanup,
    materialization, checkpoint creation, and accepted-progress publication for
    that one cell, and the kernel releases it if the writer dies.  A waiter
    re-authenticates durable progress after acquiring the fence before it can
    remove or recreate any scratch.
    """

    boundary_index = screen.schedule.fidelity_epochs.index(int(boundary))
    if boundary_index != 0:
        return _execute_candidate_cell_unlocked(
            screen,
            target_size=target_size,
            optimizer_seed=optimizer_seed,
            boundary=boundary,
            state=state,
        )

    from dataclasses import replace as _replace

    from .target_size_execution import (
        build_target_size_candidate_trajectory,
        derive_active_boundary_requirements,
        recover_authenticated_boundary_progress,
    )
    from .target_size_execution.persistence import artifact_publication_lock

    optimizer = _replace(screen.optimizer_policy, seed=int(optimizer_seed))
    trajectory = build_target_size_candidate_trajectory(
        screen.aggregate.definition,
        screen.context,
        screen.authorities.common,
        screen.schedule,
        target_size=int(target_size),
        optimizer_policy=optimizer,
        optimizer_seed=int(optimizer_seed),
    )
    materialization_directory = (
        screen.authority.bulk_root("materialization") / trajectory.content_digest
    )
    cell = (int(target_size), int(optimizer_seed))
    requirements = derive_active_boundary_requirements(
        screen.aggregate.definition, state
    )
    if (
        requirements is None
        or int(requirements[0]) != int(boundary)
        or cell not in tuple(requirements[2])
    ):
        raise TargetSizeRuntimeError(
            "The first-rung cell is not part of the exact active P2 boundary matrix."
        )
    with artifact_publication_lock(materialization_directory):
        recovered = recover_authenticated_boundary_progress(
            screen.root,
            screen.window,
            screen.authority,
            boundary_epoch=int(boundary),
            active_keys=requirements[2],
        )
        if cell in recovered:
            return recovered[cell]
        return _execute_candidate_cell_unlocked(
            screen,
            target_size=int(target_size),
            optimizer_seed=int(optimizer_seed),
            boundary=int(boundary),
            state=state,
        )


def _execute_candidate_cell_unlocked(
    screen: _ScreenContext, *, target_size: int, optimizer_seed: int, boundary: int, state: Any
) -> Any:
    """Run one surviving ``(N, seed)`` cell through the real P3 owners."""

    from dataclasses import replace as _replace

    from ._campaign_cli_core import _ok
    from .eval2 import Eval2NumericalEvaluationError
    from .target_size_execution import (
        TargetSizeContinuationRequest,
        bind_target_size_boundary_state,
        build_target_size_candidate_trajectory,
        build_target_size_cell_completion_record,
        build_target_size_eval2_role,
        materialize_target_size_candidate,
        project_target_size_candidate_preparation,
        promote_target_size_boundary_snapshot,
        record_candidate_boundary_outcome,
        resolve_target_size_candidate_for_resume,
        run_target_size_direct_boundary_inference,
        run_target_size_eval2_reduction,
        target_size_boundary_metric_from_eval2_record,
        target_size_rung_plan,
        translate_target_size_eval2_failure,
        write_target_size_evaluation_artifact,
    )

    authorities = screen.authorities
    definition = screen.aggregate.definition
    schedule = screen.schedule
    boundary_index = schedule.fidelity_epochs.index(int(boundary))
    materialization_root = screen.authority.bulk_root("materialization")

    if boundary_index == 0:
        optimizer = _replace(screen.optimizer_policy, seed=int(optimizer_seed))
        trajectory = build_target_size_candidate_trajectory(
            definition,
            screen.context,
            authorities.common,
            schedule,
            target_size=int(target_size),
            optimizer_policy=optimizer,
            optimizer_seed=int(optimizer_seed),
        )
        projection = project_target_size_candidate_preparation(
            authorities.common, definition, int(target_size)
        )
        materialization_directory = (
            materialization_root / trajectory.content_digest
        )
        # A first rung reached here has no authenticated accepted progress: the
        # recovery owner reuses accepted cells and only genuinely missing ones
        # arrive at TRAIN2/EVAL2.  Anything a previously interrupted attempt
        # left in this directory is therefore unaccepted attempt scratch, not
        # durable scientific authority.
        #
        # It has to be discarded rather than verified.  The trajectory digest
        # that names this path deliberately excludes execution-only launch
        # settings, while the immutable MACE configuration records the values
        # the attempt actually launched with.  So after a crash, a scientifically
        # identical retry under a different worker count or harness-validation
        # batch width would address the same path with different bytes and be
        # rejected by immutable create-or-verify -- turning a resource edit into
        # an unrecoverable screen.  Accepted materializations are never reached
        # by this branch, and create-or-verify stays strict for them.
        _discard_unaccepted_first_rung_materialization(
            screen,
            materialization_directory,
            target_size=int(target_size),
            optimizer_seed=int(optimizer_seed),
            boundary=int(boundary),
        )
        materialization_directory.mkdir(parents=True, exist_ok=True)
        materialization = materialize_target_size_candidate(
            trajectory,
            projection,
            authorities.common,
            canonical_frame_authority=authorities.frame_authority,
            frame_catalog=authorities.frame_catalog,
            frame_data_by_run=authorities.frame_data_by_run,
            output_directory=materialization_directory,
            optimizer_policy=optimizer,
            extxyz_policy=screen.extxyz_policy,
            frame_array_index=authorities.frame_array_index,
            mace_architecture=authorities.common.realized_mace_architecture,
        )
        checkpoint_directory = (
            screen.authority.bulk_root("train2")
            / trajectory.content_digest
            / f"boundary_{int(boundary)}"
        )
        # The first rung has no accepted predecessor: before the first
        # authenticated boundary exists there is no continuation authority at
        # all, and this directory is uncommitted owner-local attempt scratch.
        # Whatever a previously interrupted attempt left behind is scratch too,
        # and it must not be able to authenticate as this attempt's durable
        # boundary state -- a partial checkpoint or a stale runtime summary is
        # not science because of where it sits. Accepted evidence lives in the
        # immutable snapshot root, which this never touches, and later rungs
        # continue from there rather than from here.
        if checkpoint_directory.exists():
            shutil.rmtree(checkpoint_directory)
        checkpoint_directory.mkdir(parents=True, exist_ok=True)
        start_epoch = 0
        predecessor_continuation = None
    else:
        resolved = resolve_target_size_candidate_for_resume(
            screen.root,
            screen.authority,
            boundary_epoch=int(boundary),
            target_size=int(target_size),
            optimizer_seed=int(optimizer_seed),
            state=state,
        )
        trajectory = resolved.trajectory
        optimizer = resolved.optimizer_policy
        materialization = resolved.materialization
        materialization_directory = Path(materialization.output_directory)
        checkpoint_directory = resolved.checkpoint_directory
        start_epoch = int(resolved.start_epoch)
        predecessor_continuation = TargetSizeContinuationRequest(
            trajectory_digest=trajectory.content_digest,
            predecessor_boundary_epoch=int(
                schedule.fidelity_epochs[boundary_index - 1]
            ),
        )

    planned_rung = target_size_rung_plan(
        trajectory, schedule, boundary_epoch=int(boundary)
    )
    summary = screen.trainer(
        TargetSizeRungRequest(
            plan=planned_rung,
            trajectory=trajectory,
            materialization=materialization,
            materialization_directory=materialization_directory,
            checkpoint_directory=checkpoint_directory,
            start_epoch=start_epoch,
            optimizer_policy=optimizer,
        )
    )
    boundary_state = bind_target_size_boundary_state(
        trajectory, schedule, summary, checkpoint_directory=checkpoint_directory
    )
    snapshot = promote_target_size_boundary_snapshot(
        trajectory,
        boundary_state,
        checkpoint_directory=checkpoint_directory,
        snapshot_root=screen.authority.bulk_root("snapshot"),
    )
    evaluation_size = int(definition.policy.evaluation_sizes[boundary_index])
    evaluation_directory = (
        screen.authority.bulk_root("evaluation") / f"boundary_{int(boundary)}"
    )
    evaluation_directory.mkdir(parents=True, exist_ok=True)
    evaluation_artifact = write_target_size_evaluation_artifact(
        evaluation_directory,
        definition=definition,
        evaluation_size=evaluation_size,
        canonical_frame_authority=authorities.frame_authority,
        frame_catalog=authorities.frame_catalog,
        frame_data_by_run=authorities.frame_data_by_run,
        policy=screen.extxyz_policy,
        frame_array_index=authorities.frame_array_index,
    )
    role = build_target_size_eval2_role(
        trajectory=trajectory,
        boundary_state=snapshot,
        definition=definition,
        schedule=schedule,
        correlation_blocks=screen.correlation_blocks,
        evaluation_data=evaluation_artifact,
    )
    prediction_evidence = run_target_size_direct_boundary_inference(
        trajectory=trajectory,
        materialization=materialization,
        boundary_state=snapshot,
        role=role,
        evaluation_data=evaluation_artifact,
        canonical_frame_authority=authorities.frame_authority,
        definition=definition,
        context=screen.context,
        common=authorities.common,
        schedule=schedule,
        optimizer_policy=optimizer,
        extxyz_policy=screen.extxyz_policy,
        frame_catalog=authorities.frame_catalog,
        frame_data_by_run=authorities.frame_data_by_run,
        frame_array_index=authorities.frame_array_index,
        materialization_directory=materialization_directory,
        snapshot_root=screen.authority.bulk_root("snapshot"),
        evaluation_directory=evaluation_directory,
        inference_evaluator=screen.inference_evaluator,
    )
    # An authenticated EVAL2 numerical failure is *evidence*: it eliminates that
    # candidate through the reducer's own rule.  Reducing once and dispatching on
    # the result is what makes the P3 failure-completion path reachable at all;
    # reducing eagerly and only then asking for an outcome turned a typed
    # scientific result back into an execution crash that ended the screen.
    common_arguments = dict(
        window=screen.window,
        trajectory=trajectory,
        materialization=materialization,
        boundary_snapshot=snapshot,
        eval2_role=role,
        evaluation_data=evaluation_artifact,
        prediction_evidence=prediction_evidence,
        planned_rung=planned_rung,
        predecessor_continuation=predecessor_continuation,
        schedule=schedule,
    )
    try:
        metric_record = run_target_size_eval2_reduction(
            role,
            evaluation_artifact,
            prediction_evidence,
            root_directory=evaluation_directory,
        )
    except Eval2NumericalEvaluationError as error:
        outcome = translate_target_size_eval2_failure(role, error)
        metric_record = None
        failure_record = error
        completion_record = build_target_size_cell_completion_record(
            kind="eval2_failure",
            outcome=outcome,
            failure_record=error,
            definition=definition,
            checkpoint_directory=checkpoint_directory,
            **common_arguments,
        )
        _ok(
            f"boundary {boundary}: candidate N={int(target_size)} seed "
            f"{int(optimizer_seed)} recorded an authenticated EVAL2 numerical "
            f"failure ({outcome.kind.value}); it is eliminated, not retried"
        )
    else:
        failure_record = None
        outcome = target_size_boundary_metric_from_eval2_record(role, metric_record)
        completion_record = build_target_size_cell_completion_record(
            outcome=outcome,
            eval2_metric_record=metric_record,
            definition=definition,
            checkpoint_directory=checkpoint_directory,
            **common_arguments,
        )
    record_candidate_boundary_outcome(
        screen.root,
        screen.window,
        trajectory,
        completion_record,
        materialization=materialization,
        boundary_snapshot=snapshot,
        eval2_role=role,
        evaluation_data=evaluation_artifact,
        prediction_evidence=prediction_evidence,
        eval2_metric_record=metric_record,
        failure_record=failure_record,
        planned_rung=planned_rung,
        predecessor_continuation=predecessor_continuation,
        restart_authority=screen.authority,
    )
    return completion_record


def execute_current_select_target_size(
    args: Any,
    *,
    trainer: TargetSizeBoundaryTrainer | None = None,
    inference_evaluator: Callable[..., Any] | None = None,
) -> int:
    """Establish or revise the current provisional target training design.

    Three operations, one design.  ``select-target-size <N>`` merges a qualified
    candidate into the ordered collection and performs no candidate training or
    EVAL2 work at all.  ``select-target-size --auto`` runs or reuses the optional
    automatic screen and merges its recommendation through the same owner.
    ``select-target-size --reset`` clears the collection.  None of them freezes
    anything: the design stays mutable until ``cross-validate`` admits it whole.
    """

    from ._campaign_cli_core import CampaignStore, _load_config
    from .campaign_target_size_selection import resolve_provisional_horizons

    cfg, paths = _load_config(args.config)
    store = CampaignStore(paths.state_db)
    if bool(getattr(args, "reset", False)):
        return _execute_target_size_reset(cfg, paths, store)
    horizons = resolve_provisional_horizons(
        cfg,
        cv_max_num_epochs=getattr(args, "horizon_cv", None),
        production_max_num_epochs=getattr(args, "horizon", None),
    )
    if bool(getattr(args, "auto", False)):
        return _execute_auto_target_size_diagnostic(
            cfg,
            paths,
            store,
            horizons,
            trainer=trainer,
            inference_evaluator=inference_evaluator,
        )
    return _execute_manual_target_size_proposal(
        cfg, paths, store, int(getattr(args, "target_size")), horizons
    )


def _refresh_target_size_view(cfg: Any, paths: Any, store: Any, revision: Any) -> None:
    """Rebuild the derived result view after a proposal/freeze change."""

    from .campaign_target_size_view import write_selection_target_size_result_view

    write_selection_target_size_result_view(
        paths.results / "target-size-state.json", revision
    )


def _selection_baseline(state: Any) -> tuple[Any, ...]:
    """The exact selection state a long-running auto install may write over.

    Append, replace-in-place, reset and freeze all change it, so any of them
    beats a diagnostic that started before them.  Nothing else does: publishing
    unrelated screen evidence must not invalidate the operator's design.
    """

    return (
        tuple(entry.content_digest for entry in state.provisional_entries),
        None
        if state.frozen_entries is None
        else tuple(entry.content_digest for entry in state.frozen_entries),
    )


def _report_design(revision: Any, *, reused_diagnostic: bool | None = None) -> None:
    """Render the complete resulting provisional design, in selection order."""

    from ._campaign_cli_core import _ok

    entries = revision.state.provisional_entries
    _ok(
        f"provisional target-size design: {len(entries)} selected size(s)"
        if entries
        else "provisional target-size design: no size selected"
    )
    for index, entry in enumerate(entries, start=1):
        print(
            f"  [{index}] N = {entry.n_provisional} "
            f"(source: {entry.selection_source}); "
            f"T_provisional = pi_train[:{entry.n_provisional}] identity "
            f"{entry.membership_digest[:12]}...; CV horizon "
            f"{entry.cv_max_num_epochs} epoch(s); production horizon "
            f"{entry.production_max_num_epochs} epoch(s)",
            flush=True,
        )
    if reused_diagnostic is not None:
        _ok(
            "reused the existing automatic diagnostic; no screening jobs were rerun"
            if reused_diagnostic
            else "recorded new automatic diagnostic evidence"
        )
    print(
        "Frozen: no. Run `select-target-size` again to add or revise a size, "
        "`select-target-size --reset` to clear the design, or `cross-validate` "
        "to freeze it.",
        flush=True,
    )


def _execute_target_size_reset(cfg: Any, paths: Any, store: Any) -> int:
    """`select-target-size --reset`: clear the provisional design, nothing else.

    It is pre-freeze only and performs no numerical work whatsoever.  The
    prepared generation and any valid automatic-diagnostic evidence survive: the
    operator is saying "I have not chosen yet", not "discard the expensive
    screen I already paid for".
    """

    from ._campaign_cli_core import _ok, _print_header
    from .campaign_target_size_cutover import require_current_target_size_runtime
    from .campaign_target_size_selection import commit_target_size_reset

    _print_header("Target-size selection - clearing the provisional design")
    revision = require_current_target_size_runtime(store)
    revision = commit_target_size_reset(store, revision)
    _refresh_target_size_view(cfg, paths, store, revision)
    _ok(
        "the provisional target-size design is empty; the prepared generation and "
        "any automatic diagnostic evidence are unchanged"
    )
    _report_design(revision)
    return 0


def _execute_manual_target_size_proposal(
    cfg: Any, paths: Any, store: Any, target_size: int, horizons: Any
) -> int:
    """`select-target-size <N>`: the primary explicit-selection interface.

    It reaches the real prepared-generation and P2 training-order owners to
    authenticate the exact membership of ``N``, and it runs no candidate
    training and no EVAL2 evaluation whatsoever.  The automatic screen is not
    consulted, required, or synthesized: a campaign that never ran it selects
    exactly the same way as one that did.
    """

    from ._campaign_cli_core import _print_header
    from .campaign_target_size_cutover import require_current_target_size_runtime
    from .campaign_target_size_selection import (
        build_target_size_proposal,
        commit_target_size_proposal,
    )
    from .campaign_target_size_state import SELECTION_SOURCE_MANUAL

    _print_header("Target-size selection - provisional downstream design")
    revision = require_current_target_size_runtime(store)
    definition = load_prepared_target_size_definition(cfg, paths, store, revision)
    proposal = build_target_size_proposal(
        definition,
        target_size=int(target_size),
        selection_source=SELECTION_SOURCE_MANUAL,
        horizons=horizons,
    )
    revision = commit_target_size_proposal(store, revision, proposal)
    _refresh_target_size_view(cfg, paths, store, revision)
    _report_design(revision)
    return 0


def _install_recommendation(
    cfg: Any,
    paths: Any,
    store: Any,
    *,
    baseline: tuple[str | None, str | None],
    horizons: Any,
    reused: bool,
) -> int:
    """Adopt the current authenticated recommendation as the provisional choice.

    The installation is conditional on the selection state the invocation
    started from.  An automatic diagnostic can run for hours; if a human made an
    explicit choice, or ``cross-validate`` froze the design, while it was
    running, the newer decision wins.  The diagnostic evidence and its report are
    still committed and reusable - only the stale proposal update is dropped.
    """

    from ._campaign_cli_core import _ok
    from .campaign_target_size_cutover import require_current_target_size_runtime
    from .campaign_target_size_report import write_auto_diagnostic_report
    from .campaign_target_size_selection import (
        build_target_size_proposal,
        commit_target_size_proposal,
    )
    from .campaign_target_size_state import SELECTION_SOURCE_AUTO_RECOMMENDATION
    from .campaign_target_size_view import (
        expose_current_target_size_auto_diagnostic,
    )

    validated = expose_current_target_size_auto_diagnostic(cfg, paths, store)
    report_path = write_auto_diagnostic_report(paths, validated)
    _report_auto_diagnostic(validated)
    _ok(f"portable diagnostic report: {report_path}")

    revision = validated.revision
    state = revision.state
    if not validated.has_recommendation:
        # A completed diagnostic with no recommendation is a successful
        # execution of the diagnostic operation. It commits evidence only: no
        # proposal field is touched, so any previously valid proposal survives.
        print(
            "No recommendation was established, so the provisional design was left "
            "unchanged. A qualified candidate can still be chosen explicitly with "
            "`select-target-size <N>`.",
            flush=True,
        )
        return 0
    if _selection_baseline(state) != baseline:
        print(
            f"Recommendation N = {validated.recommended_target_size} was computed but "
            "not installed: the current target-size selection state changed while the "
            "diagnostic was running. The diagnostic evidence and its report are "
            "committed and reusable. Rerun `select-target-size --auto` to install it "
            "against the current design without retraining.",
            flush=True,
        )
        return 0
    proposal = build_target_size_proposal(
        validated.authorities.aggregate.definition,
        target_size=int(validated.recommended_target_size),
        selection_source=SELECTION_SOURCE_AUTO_RECOMMENDATION,
        horizons=horizons,
        auto_diagnostic_digest=validated.projection.content_digest,
    )
    revision = commit_target_size_proposal(store, revision, proposal)
    _refresh_target_size_view(cfg, paths, store, revision)
    _report_design(revision, reused_diagnostic=reused)
    return 0


def _refresh_screen_revision(store: Any, revision: Any) -> Any:
    """Re-read the campaign head before a long-gap screen transition.

    An automatic diagnostic holds no lock across hours of training, and the
    operator is free to revise their provisional choice while it runs. Screen
    evidence and the operator's design are orthogonal, so a proposal change must
    not make the screen's own compare-and-set stale and destroy the work in
    flight. Anything that is *not* orthogonal - a replaced generation or a
    different execution attempt - still fails closed here.
    """

    from .campaign_target_size_state import (
        TargetSizeCampaignConflictError,
        load_target_size_campaign_revision,
    )

    current = load_target_size_campaign_revision(store)
    if current is None:  # pragma: no cover - an open screen implies a head
        return revision
    if (
        current.state.generation != revision.state.generation
        or current.state.attempt != revision.state.attempt
        or current.state.regime is not revision.state.regime
    ):
        raise TargetSizeCampaignConflictError(
            "The target-size campaign generation or execution attempt changed while "
            "the automatic diagnostic was running; this screen no longer owns the "
            "campaign.",
            conflict_kind="stale_generation",
        )
    return current


def _execute_auto_target_size_diagnostic(
    cfg: Any,
    paths: Any,
    store: Any,
    horizons: Any,
    *,
    trainer: TargetSizeBoundaryTrainer | None = None,
    inference_evaluator: Callable[..., Any] | None = None,
) -> int:
    """`select-target-size --auto`: run or reuse the optional automatic screen."""

    from ._campaign_cli_core import (
        StageState,
        _mark_stage,
        _ok,
        _print_header,
    )
    from .campaign_target_size_adoption import (
        adopt_reconciled_execution_head,
        reconcile_and_adopt_target_size_head,
    )
    from .campaign_target_size_cutover import require_current_target_size_runtime
    from .campaign_target_size_selection import require_unfrozen
    from .campaign_target_size_state import (
        TargetSizeCampaignState,
        TargetSizeLifecycle,
        TargetSizeRegime,
        TargetSizeTransitionKind,
        commit_target_size_campaign_transition,
    )
    from .campaign_target_size_diagnostic import commit_auto_diagnostic
    from .campaign_target_size_view import write_target_size_result_view
    from .target_size_execution import (
        build_complete_boundary_batch,
        commit_target_size_boundary_batch,
        derive_active_boundary_requirements,
        recover_authenticated_boundary_progress,
    )

    revision = require_current_target_size_runtime(store)
    # One rule, one message: after admission neither form of the command may
    # change the design.
    require_unfrozen(revision.state)
    # The exact selection state this invocation intends to update. Expensive
    # diagnostic execution proceeds independently of it; installation does not.
    baseline = _selection_baseline(revision.state)

    if revision.state.lifecycle is TargetSizeLifecycle.DIAGNOSTIC_COMPLETE:
        # Warm path. A complete diagnostic for this scientific/execution
        # identity is authenticated and reused; no trainer or evaluator is
        # constructed, so zero TRAIN2/EVAL2 work is reachable from here.
        _print_header("Automatic target-size diagnostic - reusing existing evidence")
        return _install_recommendation(
            cfg, paths, store, baseline=baseline, horizons=horizons, reused=True
        )

    _print_header("Automatic target-size diagnostic - controlled configurable fidelity")
    print(
        "Epoch is a controlled variable during this operation: only the exact "
        "configured screen boundary checkpoints contribute to ranking. This is a "
        "short-horizon diagnostic and it freezes nothing.",
        flush=True,
    )
    screen = build_screen_context(
        cfg,
        paths,
        store,
        revision,
        trainer=trainer,
        inference_evaluator=inference_evaluator,
    )
    _mark_stage(
        store,
        paths,
        "target_size_selection",
        StageState.RUNNING,
        f"screening canonical generation {revision.state.generation}",
    )
    state = screen.aggregate.reducer_state
    head = None
    try:
        revision = commit_target_size_campaign_transition(
            store,
            kind=TargetSizeTransitionKind.OPEN_ATTEMPT,
            expected=revision.expectation(),
            successor=TargetSizeCampaignState(
                regime=TargetSizeRegime.CURRENT,
                generation=revision.state.generation,
                lifecycle=TargetSizeLifecycle.SCREEN_ACTIVE,
                attempt=screen.window.content_digest,
                frame_authority_digest=revision.state.frame_authority_digest,
                neutral_statistical_base_digest=(
                    revision.state.neutral_statistical_base_digest
                ),
                split_exclusion_digest=revision.state.split_exclusion_digest,
                policy_digest=revision.state.policy_digest,
                experiment_definition_digest=(
                    revision.state.experiment_definition_digest
                ),
                aggregate_digest=revision.state.aggregate_digest,
                prepared_manifest_digest=revision.state.prepared_manifest_digest,
                execution_context_digest=screen.context.content_digest,
                common_preparation_digest=screen.authorities.common.content_digest,
                screen_window_digest=screen.window.content_digest,
                execution_root=current_target_size_execution_root_locator(
                    paths, revision.state.generation
                ),
                adopted_execution_head_digest=(
                    revision.state.adopted_execution_head_digest
                ),
                adopted_reducer_state_digest=(
                    revision.state.adopted_reducer_state_digest
                ),
                # An interrupted diagnostic never destroys a provisional
                # design the operator already made.
                provisional_entries=revision.state.provisional_entries,
            ),
        ).revision

        # Always reconcile the existing root before scheduling anything new.
        revision, head = reconcile_and_adopt_target_size_head(
            store, revision, root=screen.root, authority=screen.authority
        )
        if head is not None:
            state = head.post_state
            _ok(
                "reconciled existing screen evidence: head="
                f"{head.content_digest[:12]}...; status={state.status.value}"
            )

        while not state.is_terminal:
            requirements = derive_active_boundary_requirements(
                screen.aggregate.definition, state
            )
            if requirements is None:
                break
            boundary, _evaluation_size, keys = requirements
            # An interrupted boundary leaves accepted per-cell evidence behind
            # without advancing the reducer, so the whole boundary is still
            # active on restart.  Active is not the same claim as unexecuted:
            # anything already published is authenticated here and reused, and
            # only genuinely missing cells reach the scientific owners.
            completion_by_key = recover_authenticated_boundary_progress(
                screen.root,
                screen.window,
                screen.authority,
                boundary_epoch=int(boundary),
                active_keys=keys,
            )
            if completion_by_key:
                _ok(
                    f"boundary {boundary}: recovered "
                    f"{len(completion_by_key)} authenticated completed "
                    f"(N, optimizer seed) cells from durable progress"
                )
            print(
                f"Boundary {boundary}: executing "
                f"{len(keys) - len(completion_by_key)} of {len(keys)} surviving "
                f"(N, optimizer seed) cells.",
                flush=True,
            )
            for size, seed in keys:
                cell = (int(size), int(seed))
                if cell in completion_by_key:
                    continue
                completion_by_key[cell] = _execute_candidate_cell(
                    screen,
                    target_size=int(size),
                    optimizer_seed=int(seed),
                    boundary=int(boundary),
                    state=state,
                )
            # Exact P2 order, whatever mix of recovered and freshly executed
            # cells produced it.
            completion_records = [
                completion_by_key[(int(size), int(seed))] for size, seed in keys
            ]
            batch = build_complete_boundary_batch(
                screen.aggregate.definition, state, completion_records
            )
            head = commit_target_size_boundary_batch(
                screen.root, screen.aggregate.definition, state, batch
            )
            revision = adopt_reconciled_execution_head(
                store, _refresh_screen_revision(store, revision), head
            )
            state = head.post_state
            _ok(
                f"boundary {boundary} committed: head={head.content_digest[:12]}...; "
                f"status={state.status.value}"
            )

        if state.is_terminal and head is not None:
            # The terminal head, its reducer digest, and the derived diagnostic
            # are one claim, committed together.
            revision = commit_auto_diagnostic(
                store,
                _refresh_screen_revision(store, revision),
                head,
                definition=screen.aggregate.definition,
            )
    except Exception as exc:
        _mark_stage(
            store, paths, "target_size_selection", StageState.FAILED, str(exc)
        )
        raise

    if not state.is_terminal:
        write_target_size_result_view(
            paths.results / "target-size-state.json",
            revision,
            resolver=screen.authority.resolver,
        )
        _mark_stage(
            store,
            paths,
            "target_size_selection",
            StageState.WAITING,
            f"reducer status {state.status.value}",
        )
        print(
            f"The automatic diagnostic is operationally resumable: reducer status "
            f"{state.status.value}. Re-run `select-target-size --auto` to continue. "
            "Any provisional choice you already made is unchanged.",
            flush=True,
        )
        return 0

    _mark_stage(
        store,
        paths,
        "target_size_selection",
        StageState.COMPLETE,
        f"reducer status {state.status.value}",
    )
    return _install_recommendation(
        cfg, paths, store, baseline=baseline, horizons=horizons, reused=False
    )


def report_current_target_size_auto_diagnostic(
    cfg: Any,
    paths: Any,
    store: Any,
    *,
    expected_revision: Any | None = None,
) -> Any:
    """Authoritative exposure-time entrypoint for CLI diagnostic reporting.

    This function re-establishes CampaignStore currentness and executes the full
    canonical P1/P2/P3 validation chain immediately before emitting stdout.
    """

    from .campaign_target_size_view import (
        expose_current_target_size_auto_diagnostic,
    )

    validated = expose_current_target_size_auto_diagnostic(
        cfg, paths, store, expected_revision=expected_revision
    )
    _report_auto_diagnostic(validated)
    return validated


def _report_auto_diagnostic(validated_result: Any) -> None:
    from .target_size_experiment import (
        CONFIGURED_CEILING_NONCONVERGENCE_REASON_CODE,
    )
    from .campaign_target_size_diagnostic import (
        TargetSizeDiagnosticProjectionError,
        ValidatedTargetSizeAutoDiagnostic,
    )

    if not isinstance(validated_result, ValidatedTargetSizeAutoDiagnostic):
        raise TargetSizeDiagnosticProjectionError(
            "Diagnostic reporting requires a ValidatedTargetSizeAutoDiagnostic established "
            f"from the current CampaignStore revision, not {type(validated_result).__name__}."
        )
    diagnostic = validated_result.projection
    if diagnostic.has_recommendation:
        print(
            "Automatic diagnostic recommendation: N = "
            f"{diagnostic.recommended_target_size}. This is short-horizon evidence, "
            "not a frozen selection.",
            flush=True,
        )
        if (
            CONFIGURED_CEILING_NONCONVERGENCE_REASON_CODE
            in diagnostic.terminal_reason_codes
        ):
            print(
                "Warning: the configured practical ceiling is the best evaluated "
                "permitted size; target-size convergence was not demonstrated within "
                "the configured ladder. The recommendation is budget-limited rather "
                "than convergence-limited.",
                flush=True,
            )
        other = tuple(
            code
            for code in diagnostic.terminal_reason_codes
            if code != CONFIGURED_CEILING_NONCONVERGENCE_REASON_CODE
        )
        if other:
            print(f"Diagnostic notes: {', '.join(other)}.", flush=True)
    else:
        print(
            "The automatic diagnostic completed without a recommendation: "
            f"{diagnostic.reducer_status}; "
            f"{', '.join(diagnostic.terminal_reason_codes) or 'no further candidates'}. "
            "This is a diagnostic conclusion, not a campaign-terminal failure.",
            flush=True,
        )


__all__ = [
    "CurrentTargetSizeAuthorities",
    "TARGET_SIZE_EXECUTION_ROOT_NAME",
    "TargetSizeRuntimeError",
    "MaceTargetSizeBoundaryTrainer",
    "TargetSizeBoundaryTrainer",
    "TargetSizeRungRequest",
    "build_prepared_target_size_substrate",
    "load_prepared_target_size_generation",
    "load_prepared_target_size_definition",
    "build_screen_context",
    "execute_current_prepare",
    "execute_current_select_target_size",
    "mace_run_configuration",
    "report_current_target_size_auto_diagnostic",
    "resolve_neutral_partition_policy",
    "current_target_size_execution_root",
    "current_target_size_execution_root_locator",
]
