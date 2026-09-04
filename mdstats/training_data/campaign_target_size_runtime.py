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
import subprocess
import sys
import time

from ._common import TrainingDataError, TrainingDataInputError
from .campaign_target_size_paths import (
    TARGET_SIZE_EXECUTION_ROOT_NAME,
    target_size_execution_root,
    target_size_execution_root_locator,
)


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
    from .target_size_execution import build_target_size_common_preparation
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
        common = build_target_size_common_preparation(
            aggregate,
            frame_catalog=frame_catalog,
            frame_data_by_run=frame_data_by_run,
            frame_array_index=frame_array_index,
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

        environment = dict(os.environ)
        environment.update(dict(self.environment or {}))
        environment[mdstats.TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE] = json.dumps(
            request.plan.to_dict(), sort_keys=True, separators=(",", ":")
        )
        environment["PYTHONHASHSEED"] = str(int(request.trajectory.optimizer_seed))
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
        _atomic_json,
        _ensure_manifest,
        _load_config,
        _mark_stage,
        _ok,
        _prepare_catalog,
        _print_header,
        _require_stage_complete,
    )
    from .campaign_prepared_generation import (
        preparation_configuration_identity,
        publish_prepared_generation,
    )
    from .campaign_target_size_cutover import ensure_current_target_size_authorities
    from .campaign_target_size_view import write_target_size_result_view

    cfg, paths = _load_config(args.config)
    store = CampaignStore(paths.state_db)
    _require_stage_complete(store, paths, "doctor")
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
        if bool(getattr(args, "rebuild_catalog", False)) or not store.has_record("data5"):
            prepared_data4 = _prepare_catalog(
                cfg,
                paths,
                store,
                approve_manifest=False,
                refresh_inferences=refresh_inferences,
            )["data4"]
        else:
            _ok(
                "lower-level source, frame, and feature inputs are present and will be "
                "re-validated by the current P1 owners"
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
        )
    except Exception as exc:
        _mark_stage(store, paths, "prepare", StageState.FAILED, str(exc))
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
        "configured experiment definition, and the paired-seed screen that decides "
        "N is owned by `select-target-size`.",
        flush=True,
    )
    _atomic_json(
        paths.results / "target-size-state.json",
        write_target_size_result_view(
            paths.results / "target-size-state.json", revision
        ),
    )
    _mark_stage(
        store,
        paths,
        "prepare",
        StageState.COMPLETE,
        f"current target-size substrate bound at generation {revision.state.generation}",
    )
    print("Next: `select-target-size`.", flush=True)
    return 0


# ---------------------------------------------------------------------------
# `select-target-size`: the only current screening entrypoint
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
        initialize_target_size_screen,
        target_size_population_correlation_blocks,
    )

    authorities = load_prepared_target_size_generation(cfg, paths, store, revision)
    aggregate = authorities.aggregate
    definition = aggregate.definition
    schedule = build_target_size_screen_schedule(definition.policy.fidelity_epochs)
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


def _execute_candidate_cell(
    screen: _ScreenContext, *, target_size: int, optimizer_seed: int, boundary: int, state: Any
) -> Any:
    """Run one surviving ``(N, seed)`` cell through the real P3 owners."""

    from dataclasses import replace as _replace

    from .target_size_execution import (
        TargetSizeContinuationRequest,
        bind_target_size_boundary_state,
        build_target_size_candidate_trajectory,
        build_target_size_cell_completion_record,
        build_target_size_eval2_role,
        evaluate_target_size_boundary,
        materialize_target_size_candidate,
        project_target_size_candidate_preparation,
        promote_target_size_boundary_snapshot,
        record_candidate_boundary_outcome,
        resolve_target_size_candidate_for_resume,
        run_target_size_direct_boundary_inference,
        run_target_size_eval2_reduction,
        target_size_rung_plan,
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
    metric_record = run_target_size_eval2_reduction(
        role,
        evaluation_artifact,
        prediction_evidence,
        root_directory=evaluation_directory,
    )
    outcome = evaluate_target_size_boundary(
        role,
        evaluation_artifact,
        prediction_evidence,
        root_directory=evaluation_directory,
    )
    completion_record = build_target_size_cell_completion_record(
        window=screen.window,
        trajectory=trajectory,
        materialization=materialization,
        boundary_snapshot=snapshot,
        eval2_role=role,
        evaluation_data=evaluation_artifact,
        outcome=outcome,
        prediction_evidence=prediction_evidence,
        eval2_metric_record=metric_record,
        planned_rung=planned_rung,
        predecessor_continuation=predecessor_continuation,
        schedule=schedule,
        definition=definition,
        checkpoint_directory=checkpoint_directory,
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
    """Run or resume the complete current paired-seed target-size screen."""

    from ._campaign_cli_core import (
        CampaignStore,
        StageState,
        _load_config,
        _mark_stage,
        _ok,
        _print_header,
    )
    from .campaign_target_size_adoption import (
        adopt_reconciled_execution_head,
        reconcile_and_adopt_target_size_head,
    )
    from .campaign_target_size_cutover import require_current_target_size_runtime
    from .campaign_target_size_state import (
        TargetSizeCampaignState,
        TargetSizeLifecycle,
        TargetSizeRegime,
        TargetSizeTransitionKind,
        commit_target_size_campaign_transition,
        load_target_size_campaign_revision,
    )
    from .campaign_target_size_terminal import (
        commit_terminal_projection,
        load_validated_target_size_terminal_result,
        validate_terminal_projection,
    )
    from .campaign_target_size_view import write_target_size_result_view
    from .target_size_execution import (
        TargetSizeExecutionResolver,
        build_complete_boundary_batch,
        commit_target_size_boundary_batch,
        derive_active_boundary_requirements,
    )

    cfg, paths = _load_config(args.config)
    store = CampaignStore(paths.state_db)
    revision = require_current_target_size_runtime(store)
    if revision.state.lifecycle in (
        TargetSizeLifecycle.TERMINAL_SELECTED,
        TargetSizeLifecycle.TERMINAL_SCIENTIFIC_FAILURE,
    ):
        from .campaign_target_size_view import (
            write_current_target_size_result_view,
        )

        write_current_target_size_result_view(
            cfg, paths, store, expected_revision=revision
        )
        report_current_target_size_terminal_state(
            cfg, paths, store, expected_revision=revision
        )
        return 0

    _print_header("Target-size selection - controlled configurable fidelity")
    print(
        "Epoch is a controlled variable during this operation: only the exact "
        "configured screen boundary checkpoints contribute to ranking.",
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
            print(
                f"Boundary {boundary}: executing {len(keys)} surviving "
                f"(N, optimizer seed) cells.",
                flush=True,
            )
            completion_records = []
            for size, seed in keys:
                completion_records.append(
                    _execute_candidate_cell(
                        screen,
                        target_size=int(size),
                        optimizer_seed=int(seed),
                        boundary=int(boundary),
                        state=state,
                    )
                )
            batch = build_complete_boundary_batch(
                screen.aggregate.definition, state, completion_records
            )
            head = commit_target_size_boundary_batch(
                screen.root, screen.aggregate.definition, state, batch
            )
            revision = adopt_reconciled_execution_head(store, revision, head)
            state = head.post_state
            _ok(
                f"boundary {boundary} committed: head={head.content_digest[:12]}...; "
                f"status={state.status.value}"
            )

        if state.is_terminal and head is not None:
            # The terminal head, its reducer digest, and the derived selection
            # are one claim, committed together.
            revision = commit_terminal_projection(
                store, revision, head, definition=screen.aggregate.definition
            )
    except Exception as exc:
        _mark_stage(
            store, paths, "target_size_selection", StageState.FAILED, str(exc)
        )
        raise

    from .campaign_target_size_view import (
        write_current_target_size_result_view,
        write_nonterminal_target_size_result_view,
    )

    if state.is_terminal:
        write_current_target_size_result_view(
            cfg, paths, store, expected_revision=revision
        )
        _mark_stage(
            store,
            paths,
            "target_size_selection",
            StageState.COMPLETE,
            f"reducer status {state.status.value}",
        )
        report_current_target_size_terminal_state(
            cfg, paths, store, expected_revision=revision
        )
    else:
        write_nonterminal_target_size_result_view(
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
            f"Target-size screen is operationally resumable: reducer status "
            f"{state.status.value}. Re-run `select-target-size` to continue.",
            flush=True,
        )
    return 0


def report_current_target_size_terminal_state(
    cfg: Any,
    paths: Any,
    store: Any,
    *,
    expected_revision: Any | None = None,
) -> Any:
    """Authoritative exposure-time entrypoint for CLI terminal reporting.

    This function re-establishes CampaignStore currentness and executes the full
    canonical P1/P2/P3 validation chain immediately before emitting stdout.
    """

    from .campaign_target_size_view import (
        expose_current_target_size_terminal_result,
    )

    validated = expose_current_target_size_terminal_result(
        cfg, paths, store, expected_revision=expected_revision
    )
    _report_terminal_state(validated)
    return validated


def _report_terminal_state(validated_result: Any) -> None:
    from .campaign_target_size_terminal import (
        TargetSizeTerminalProjectionError,
        ValidatedTargetSizeTerminalResult,
    )

    if not isinstance(validated_result, ValidatedTargetSizeTerminalResult):
        raise TargetSizeTerminalProjectionError(
            "Terminal state reporting requires a ValidatedTargetSizeTerminalResult established "
            f"from the current CampaignStore revision, not {type(validated_result).__name__}."
        )
    terminal = validated_result.projection
    if terminal.is_selection:
        print(
            f"Target size is already selected and frozen: N={terminal.selected_target_size}.",
            flush=True,
        )
    else:
        print(
            "Target-size selection is scientifically terminal: "
            f"{terminal.reducer_status}; "
            f"{', '.join(terminal.terminal_reason_codes) or 'no further candidates'}.",
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
    "build_screen_context",
    "execute_current_prepare",
    "execute_current_select_target_size",
    "mace_run_configuration",
    "report_current_target_size_terminal_state",
    "resolve_neutral_partition_policy",
    "current_target_size_execution_root",
    "current_target_size_execution_root_locator",
]
