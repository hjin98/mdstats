"""Prepare-owned construction of the one complete target-training order.

This is the single orchestration of the accepted chain

    exact P_train -> TargetCoverageReference -> canonical obligations
    -> shared FEAS1/NEIGHBOR1 -> MVIDX -> MVSEL2 -> configured REPAIR2
    -> exact reconstruction -> complete order -> independent MVQUAL

beneath ``prepare``.  Every expensive product is an immutable create-or-verify
artifact under ``<prepared root>/target-order/`` keyed by the exact identity of
its scientific parents, so an interrupted ``prepare`` resumes from the last
published stage and from authenticated MVSTATE2 checkpoints.  None of these
objects is current: the returned :class:`TargetOrderPreparation` becomes
meaningful only when the prepared generation that names it is adopted through
``CampaignStore``.  Attempt scratch is attempt-owned and removed on exit;
checkpoints are build-owned, mutated only by the holder of the same-build
single-flight fence, and removed once the build result is published.
Worker counts are execution-only and never enter an identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

from .._common import TrainingDataInputError, TrainingDataSerializationError, digest
from ..persistence import artifact_publication_lock
from ..progress_timing import format_progress_time
from ..resources import StageResourceScope, available_cpu_threads, available_memory_bytes, process_rss_bytes
from .artifact_store import (
    TargetOrderArtifactStoreError,
    publish_artifact_directory,
    read_manifest,
)
from .coverage_reference import (
    TargetCoveragePolicy,
    TargetCoverageReference,
    build_target_coverage_reference,
    read_target_coverage_reference,
    write_target_coverage_reference,
)
from .engine import run_selection
from .feasibility import (
    STATE_CAPACITY_INFEASIBLE,
    TargetCoverageFeasibilityPolicy,
    TargetCoverageFeasibilityReport,
    build_target_coverage_feasibility_report,
    build_target_coverage_geometry,
    read_target_coverage_geometry,
    write_target_coverage_geometry,
)
from .kernels import preflight_native_workers
from .obligations import TargetMembershipObligationAuthority, build_canonical_obligation_authority
from .qualification import MVQUAL_VERSION, TargetMembershipQualificationPlan, build_membership_qualification
from .repair import TargetMultiViewRepairPlan, TargetMultiViewRepairPolicy, build_repair_plan, validate_repair_plan
from .selector import (
    TargetMultiViewSelectionPlan,
    TargetMultiViewSelectorPolicy,
    build_forward_state,
    reconstruct_forward_state,
)
from .sparse_index import (
    build_target_coverage_sparse_index,
    read_target_coverage_sparse_forward_view,
    write_target_coverage_sparse_index,
)
from .state import prune_checkpoints, restore_latest_checkpoint, selection_identity, write_selection_checkpoint

TARGET_ORDER_PREPARATION_SCHEMA = "mdstats.target-order-preparation.v1"
TARGET_ORDER_BUILD_SCHEMA = "mdstats.target-order-build.v1"
TARGET_ORDER_ROOT_NAME = "target-order"
#: Continuation checkpoints bound the recomputation after an interruption.
CHECKPOINT_INTERVAL_RANKS = 2048


@dataclass(frozen=True, slots=True)
class TargetOrderPreparation:
    """Compact prepared component naming one completed target-order build."""

    build_identity: str
    dataset_id: str
    population_digest: str
    split_digest: str
    target_coverage_reference_digest: str
    obligation_authority_digest: str
    feasibility_report_digest: str
    mvidx_content_digest: str
    selection_plan_digest: str
    repair_plan_digest: str
    qualification_plan_digest: str
    configured_sizes: tuple[int, ...]
    training_order_digest: str
    artifact_paths: tuple[tuple[str, str], ...]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_ORDER_PREPARATION_SCHEMA,
            "build_identity": self.build_identity,
            "dataset_id": self.dataset_id,
            "population_digest": self.population_digest,
            "split_digest": self.split_digest,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "obligation_authority_digest": self.obligation_authority_digest,
            "feasibility_report_digest": self.feasibility_report_digest,
            "mvidx_content_digest": self.mvidx_content_digest,
            "selection_plan_digest": self.selection_plan_digest,
            "repair_plan_digest": self.repair_plan_digest,
            "qualification_plan_digest": self.qualification_plan_digest,
            "configured_sizes": list(self.configured_sizes),
            "training_order_digest": self.training_order_digest,
            "artifact_paths": dict(self.artifact_paths),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetOrderPreparation":
        if payload.get("schema") != TARGET_ORDER_PREPARATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported target-order preparation schema.")
        result = cls(
            **{
                name: str(payload[name])
                for name in (
                    "build_identity",
                    "dataset_id",
                    "population_digest",
                    "split_digest",
                    "target_coverage_reference_digest",
                    "obligation_authority_digest",
                    "feasibility_report_digest",
                    "mvidx_content_digest",
                    "selection_plan_digest",
                    "repair_plan_digest",
                    "qualification_plan_digest",
                    "training_order_digest",
                )
            },
            configured_sizes=tuple(int(v) for v in payload["configured_sizes"]),
            artifact_paths=tuple(sorted((str(k), str(v)) for k, v in payload["artifact_paths"].items())),
        )
        if payload.get("content_digest") != result.content_digest:
            raise TrainingDataSerializationError("Target-order preparation digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetOrderBuild:
    """The authenticated build products ``prepare`` projects into P2."""

    preparation: TargetOrderPreparation
    obligation_authority: TargetMembershipObligationAuthority
    feasibility_report: TargetCoverageFeasibilityReport
    selection_plan: TargetMultiViewSelectionPlan
    repair_plan: TargetMultiViewRepairPlan
    qualification: TargetMembershipQualificationPlan
    frame_uids: tuple[str, ...]
    reused: bool = False


def training_order_digest(frame_uids: Sequence[str]) -> str:
    return digest({"schema": "mdstats.target-order-frame-uids.v1", "frame_uids": list(frame_uids)})


def target_order_root(prepared_root: Path) -> Path:
    return Path(prepared_root) / TARGET_ORDER_ROOT_NAME


def target_order_method_identity() -> dict[str, Any]:
    """Frozen numerical method identity shared by every build identity."""

    return {
        "coverage_policy": TargetCoveragePolicy().to_dict(),
        "feasibility_policy": TargetCoverageFeasibilityPolicy().to_dict(),
        "selector_policy": TargetMultiViewSelectorPolicy().to_dict(),
        "repair_policy": TargetMultiViewRepairPolicy().to_dict(),
        "qualification_version": MVQUAL_VERSION,
    }


def target_order_build_identity(
    *,
    population_digest: str,
    split_digest: str,
    raw_feature_catalog_digest: str,
    structural_input_identity: str,
    training_order_policy: str,
    hard_support_obligations: Sequence[Any],
    configured_sizes: Sequence[int],
) -> str:
    return digest(
        {
            "schema": "mdstats.target-order-build-identity.v1",
            "population_digest": population_digest,
            "split_digest": split_digest,
            "raw_feature_catalog_digest": raw_feature_catalog_digest,
            "structural_input_identity": structural_input_identity,
            "training_order_policy": training_order_policy,
            "hard_support_obligations": [item.to_dict() for item in hard_support_obligations],
            "configured_sizes": [int(v) for v in configured_sizes],
            "method": target_order_method_identity(),
        }
    )


def _say(progress: Callable[[str], None] | None, message: str) -> None:
    if progress is not None:
        progress(message)


def _relative(root: Path, path: Path) -> str:
    return str(Path(path).resolve().relative_to(Path(root).resolve()))


def _read_build(directory: Path, root: Path) -> TargetOrderBuild:
    manifest = read_manifest(directory, schema=TARGET_ORDER_BUILD_SCHEMA)
    try:
        preparation = TargetOrderPreparation.from_dict(manifest["preparation"])
        build = TargetOrderBuild(
            preparation=preparation,
            obligation_authority=TargetMembershipObligationAuthority.from_dict(manifest["obligation_authority"]),
            feasibility_report=TargetCoverageFeasibilityReport.from_dict(manifest["feasibility_report"]),
            selection_plan=TargetMultiViewSelectionPlan.from_dict(manifest["selection_plan"]),
            repair_plan=TargetMultiViewRepairPlan.from_dict(manifest["repair_plan"]),
            qualification=TargetMembershipQualificationPlan.from_dict(manifest["qualification"]),
            frame_uids=tuple(str(v) for v in manifest["frame_uids"]),
            reused=True,
        )
    except (KeyError, TypeError, ValueError, TrainingDataInputError, TrainingDataSerializationError) as exc:
        raise TargetOrderArtifactStoreError(f"Target-order build record is invalid: {exc}") from exc
    record = build.preparation
    if (
        manifest.get("content_digest") != record.content_digest
        or record.obligation_authority_digest != build.obligation_authority.content_digest
        or record.feasibility_report_digest != build.feasibility_report.content_digest
        or record.selection_plan_digest != build.selection_plan.content_digest
        or record.repair_plan_digest != build.repair_plan.content_digest
        or record.qualification_plan_digest != build.qualification.content_digest
        or record.training_order_digest != training_order_digest(build.frame_uids)
        or _relative(root, directory) != dict(record.artifact_paths)["build"]
    ):
        raise TargetOrderArtifactStoreError("Target-order build record does not bind its evidence.")
    return build


def prepare_target_training_order(
    *,
    prepared_root: Path,
    population: Any,
    split: Any,
    training_order_policy: str,
    hard_support_obligations: Sequence[Any],
    configured_sizes: Sequence[int],
    raw_feature_catalog: Any,
    structural_input_identity: str,
    structural_catalog_factory: Callable[[], Any],
    workers: int = 1,
    resource_scope: StageResourceScope | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> TargetOrderBuild:
    """Build or reuse the complete ``pi_train`` for exact ``P_train``."""

    sizes = tuple(int(v) for v in configured_sizes)
    workers = max(1, int(workers))
    root = target_order_root(prepared_root)
    build_identity = target_order_build_identity(
        population_digest=population.content_digest,
        split_digest=split.content_digest,
        raw_feature_catalog_digest=raw_feature_catalog.content_digest,
        structural_input_identity=structural_input_identity,
        training_order_policy=training_order_policy,
        hard_support_obligations=hard_support_obligations,
        configured_sizes=sizes,
    )
    build_directory = root / "builds" / build_identity
    # Cheap unlocked fast path: a build becomes visible only through one
    # atomic rename, so an existing directory is complete or corrupt.
    if build_directory.is_dir():
        return _reuse_build(build_directory, root, build_identity, progress_callback)
    # Same-build single-flight fence.  Checkpoint roots are keyed by the
    # scientific build identity, so exactly one attempt may mutate them.  The
    # fence is execution-only (never part of an identity), is released by the
    # OS if the holder dies, and does not serialize different build identities.
    # It is adjacent to, and distinct from, the build publication lock.
    with artifact_publication_lock(root / "builds" / f"{build_identity}.prepare"):
        if build_directory.is_dir():
            return _reuse_build(build_directory, root, build_identity, progress_callback)
        (root / "attempts").mkdir(parents=True, exist_ok=True)
        scratch = Path(tempfile.mkdtemp(prefix="attempt-", dir=root / "attempts"))
        started = time.monotonic()
        try:
            return _build(
                root=root,
                scratch=scratch,
                build_identity=build_identity,
                population=population,
                split=split,
                training_order_policy=training_order_policy,
                hard_support_obligations=hard_support_obligations,
                sizes=sizes,
                raw_feature_catalog=raw_feature_catalog,
                structural_input_identity=structural_input_identity,
                structural_catalog_factory=structural_catalog_factory,
                workers=workers,
                resource_scope=resource_scope,
                progress=progress_callback,
            )
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
            _say(progress_callback, f"status=complete; elapsed={format_progress_time(time.monotonic() - started)}")


def _read_published(reader: Callable[[Path], Any], directory: Path) -> Any:
    """Read a published stage product; corruption fails closed, untouched."""

    try:
        return reader(directory)
    except (TargetOrderArtifactStoreError, TrainingDataInputError) as exc:
        raise TargetOrderArtifactStoreError(
            f"Published target-order artifact at {directory} fails authentication ({exc}); "
            "prepare does not replace immutable published content."
        ) from exc


def _reuse_build(
    build_directory: Path, root: Path, build_identity: str, progress: Callable[[str], None] | None
) -> TargetOrderBuild:
    """Authenticate a published build; a corrupt one fails closed, untouched."""

    build = _read_published(lambda directory: _read_build(directory, root), build_directory)
    _say(progress, f"status=reused; build={build_identity[:12]}")
    return build


def _build(
    *,
    root: Path,
    scratch: Path,
    build_identity: str,
    population: Any,
    split: Any,
    training_order_policy: str,
    hard_support_obligations: Sequence[Any],
    sizes: tuple[int, ...],
    raw_feature_catalog: Any,
    structural_input_identity: str,
    structural_catalog_factory: Callable[[], Any],
    workers: int,
    resource_scope: StageResourceScope | None,
    progress: Callable[[str], None] | None,
) -> TargetOrderBuild:
    coverage_policy = TargetCoveragePolicy()
    reference_directory = root / "reference" / digest(
        {
            "population_digest": population.content_digest,
            "split_digest": split.content_digest,
            "raw_feature_catalog_digest": raw_feature_catalog.content_digest,
            "structural_input_identity": structural_input_identity,
            "policy": coverage_policy.to_dict(),
        }
    )
    reference: TargetCoverageReference | None = None
    if reference_directory.is_dir():
        reference = _read_published(read_target_coverage_reference, reference_directory)
        if reference.split_digest != split.content_digest:
            raise TargetOrderArtifactStoreError(
                f"Published target coverage reference at {reference_directory} does not bind the exact split."
            )
    if reference is None:
        _say(progress, "stage=structural-selector-inputs; status=start")
        structural_catalog = structural_catalog_factory()
        # Stage RAM accounting: the budget is derived from available memory while
        # process RSS already carries everything resident before this stage, so
        # both are recorded and the stage's incremental demand is the comparable
        # quantity.
        rss_before = process_rss_bytes()
        _say(
            progress,
            "stage=target-coverage-reference; status=start; "
            f"process_rss_bytes={rss_before}; mem_available_bytes={available_memory_bytes()}",
        )
        # COVREF-PAR1: single-level radius-block parallelism (one cKDTree
        # worker per lane) under the stage CPU budget; execution-only.
        reference = build_target_coverage_reference(
            dataset_id=population.dataset_id,
            population=population,
            split=split,
            raw_feature_catalog=raw_feature_catalog,
            structural_catalog=structural_catalog,
            policy=coverage_policy,
            query_workers=1,
            execution_scope=None
            if workers == 1
            else StageResourceScope(
                stage_name="TARGET-ORDER-COVREF",
                cpu_threads_available=int(
                    available_cpu_threads() if resource_scope is None else resource_scope.cpu_threads_available
                ),
                cpu_threads_budget=int(workers if resource_scope is None else resource_scope.cpu_threads_budget),
                python_workers=workers,
                tree_workers=1,
                blas_threads=1,
                ram_budget_bytes=None if resource_scope is None else resource_scope.ram_budget_bytes,
            ),
            progress_callback=progress,
        )
        del structural_catalog
        rss_after = process_rss_bytes()
        _say(
            progress,
            "stage=target-coverage-reference; status=released; "
            f"process_rss_bytes={rss_after}; mem_available_bytes={available_memory_bytes()}; "
            f"stage_incremental_rss_bytes={None if rss_before is None or rss_after is None else rss_after - rss_before}",
        )
        write_target_coverage_reference(reference_directory, reference)
    _say(progress, f"stage=target-coverage-reference; families={len(reference.families)}; frames={reference.candidate_count}")

    authority = build_canonical_obligation_authority(
        reference,
        population,
        training_order_policy=training_order_policy,
        hard_support_obligations=hard_support_obligations,
    )
    _say(progress, f"stage=canonical-obligations; obligations={len(authority.obligations)}")

    feas_policy = TargetCoverageFeasibilityPolicy()
    geometry_directory = root / "geometry" / digest(
        {"target_coverage_reference_digest": reference.content_digest, "policy": feas_policy.to_dict()}
    )
    geometry = None
    if geometry_directory.is_dir():
        geometry = _read_published(read_target_coverage_geometry, geometry_directory)
        if geometry.neighborhoods.target_coverage_reference_digest != reference.content_digest:
            raise TargetOrderArtifactStoreError(
                f"Published FEAS1/NEIGHBOR1 geometry at {geometry_directory} does not bind the reference."
            )
    if geometry is None:
        _say(progress, "stage=FEAS1-NEIGHBOR1; status=start")
        built = build_target_coverage_geometry(
            reference,
            build_directory=scratch / "geometry",
            policy=feas_policy,
            global_workers=workers,
            progress_callback=progress,
        )
        write_target_coverage_geometry(geometry_directory, built)
        del built
        shutil.rmtree(scratch / "geometry", ignore_errors=True)
        geometry = read_target_coverage_geometry(geometry_directory)
    feasibility = build_target_coverage_feasibility_report(reference, geometry, authority, configured_ceiling=sizes[-1])
    if feasibility.terminal_state == STATE_CAPACITY_INFEASIBLE:
        raise TrainingDataInputError(
            "FEAS1 proves the accepted membership method infeasible within the configured ceiling "
            f"N_max={sizes[-1]}: at least {feasibility.k_min_lower_bound} frames are required "
            f"(coverage bound {feasibility.coverage_cardinality_lower_bound}, obligation bound "
            f"{feasibility.obligation_lower_bound}). Increase target_size_power_max; thresholds and minima are not relaxed."
        )
    _say(progress, f"stage=FEAS1; state={feasibility.terminal_state}; k_min_lower_bound={feasibility.k_min_lower_bound}")

    mvidx_directory = root / "mvidx" / digest(
        {"neighborhood_digest": geometry.neighborhoods.content_digest, "obligation_authority_digest": authority.content_digest}
    )
    forward = None
    if mvidx_directory.is_dir():
        forward = _read_published(read_target_coverage_sparse_forward_view, mvidx_directory)
    if forward is None:
        _say(progress, "stage=MVIDX; status=start")
        index = build_target_coverage_sparse_index(
            reference,
            geometry.neighborhoods,
            authority,
            workers=workers,
            resource_scope=resource_scope,
            out_of_core_directory=scratch / "mvidx",
            progress_callback=progress,
        )
        write_target_coverage_sparse_index(mvidx_directory, index)
        del index
        shutil.rmtree(scratch / "mvidx", ignore_errors=True)
        forward = read_target_coverage_sparse_forward_view(mvidx_directory)
    neighborhood_digest = geometry.neighborhoods.content_digest
    del geometry

    policy = TargetMultiViewSelectorPolicy()
    nmax = sizes[-1]
    candidate_count = int(forward.candidate_count)
    if nmax > candidate_count:
        raise TrainingDataInputError(f"Exact P_train has {candidate_count} frames; configured N_max={nmax}.")
    base_state = build_forward_state(reference, forward)
    preflight = preflight_native_workers(forward, base_state, max_workers=workers)
    selector_workers = preflight.effective_workers
    _say(progress, f"stage=MVSEL2-preflight; {preflight.summary()}")

    pure_identity = selection_identity(
        reference_digest=reference.content_digest,
        mvidx_digest=forward.mvidx_content_digest,
        selector_policy_digest=policy.policy_digest,
        configured_sizes=sizes,
    )
    pure_checkpoints = root / "checkpoints" / pure_identity

    def pure_checkpoint(state: Any, entries: Sequence[Any], rungs: Sequence[Any], phase_a: int | None) -> None:
        published = write_selection_checkpoint(
            pure_checkpoints, identity=pure_identity, state=state, entries=entries, rungs=rungs, phase_a_completed_at=phase_a
        )
        prune_checkpoints(pure_checkpoints, keep=published.directory)

    restored = restore_latest_checkpoint(pure_checkpoints, reference, forward, expected_identity=pure_identity, maximum_selected=nmax)
    _say(progress, f"stage=MVSEL2; resume={0 if restored is None else restored.state.selected_count}; N_max={nmax}")
    pure = run_selection(
        reference,
        forward,
        policy,
        stop=nmax,
        state=base_state if restored is None else restored.state,
        entries=() if restored is None else restored.entries,
        rungs=() if restored is None else restored.rungs,
        phase_a_completed_at=None if restored is None else restored.phase_a_completed_at,
        rung_sizes=sizes,
        record_entries_through=nmax,
        workers=selector_workers,
        checkpoint=pure_checkpoint,
        checkpoint_interval=CHECKPOINT_INTERVAL_RANKS,
        progress_callback=progress,
    )
    selection = TargetMultiViewSelectionPlan(
        target_coverage_reference_digest=reference.content_digest,
        mvidx_content_digest=forward.mvidx_content_digest,
        policy=policy,
        configured_sizes=sizes,
        entries=tuple(pure.entries),
        rungs=tuple(pure.rungs),
        phase_a_completed_at=pure.phase_a_completed_at,
    )

    _say(progress, f"stage=REPAIR2; status=start; width={selector_workers}")
    # REPAIR2 evaluates the same qualified row primitive as MVSEL2, so the
    # metered preflight width is the one execution-width authority for both.
    repair = build_repair_plan(
        reference, forward, selection, workers=selector_workers, resource_scope=resource_scope, progress_callback=progress
    )
    validate_repair_plan(repair, selection)
    candidate_by_uid = {uid: index for index, uid in enumerate(reference.frame_uids)}
    repaired = [candidate_by_uid[uid] for uid in repair.repaired_prefix]
    if repair.total_swaps:
        # D2 9.5: every pre-repair continuation cache is stale; replay the
        # repaired prefix from primitive sparse authority.
        continuation = reconstruct_forward_state(reference, forward, repaired)
    else:
        continuation = pure.state
    if continuation.selected_order != repaired:
        raise TrainingDataInputError("Post-repair continuation state does not match the repaired prefix.")

    suffix_identity = selection_identity(
        reference_digest=reference.content_digest,
        mvidx_digest=forward.mvidx_content_digest,
        selector_policy_digest=policy.policy_digest,
        configured_sizes=sizes,
        repair_plan_digest=repair.content_digest,
    )
    suffix_checkpoints = root / "checkpoints" / suffix_identity

    def suffix_checkpoint(state: Any, entries: Sequence[Any], rungs: Sequence[Any], phase_a: int | None) -> None:
        published = write_selection_checkpoint(suffix_checkpoints, identity=suffix_identity, state=state)
        prune_checkpoints(suffix_checkpoints, keep=published.directory)

    resumed = restore_latest_checkpoint(suffix_checkpoints, reference, forward, expected_identity=suffix_identity)
    if resumed is not None and resumed.state.selected_order[:nmax] == repaired:
        continuation = resumed.state
    _say(progress, f"stage=MVSEL2-suffix; resume={continuation.selected_count}; complete={candidate_count}")
    suffix = run_selection(
        reference,
        forward,
        policy,
        stop=candidate_count,
        state=continuation,
        workers=selector_workers,
        checkpoint=suffix_checkpoint,
        checkpoint_interval=CHECKPOINT_INTERVAL_RANKS,
        progress_callback=progress,
    )
    order = tuple(reference.frame_uids[index] for index in suffix.state.selected_order)
    if len(order) != candidate_count or order[:nmax] != repair.repaired_prefix:
        raise TrainingDataInputError("The complete target-training order does not extend the repaired prefix.")

    _say(progress, "stage=MVQUAL; status=start")
    qualification = build_membership_qualification(
        reference, authority, forward, {size: order[:size] for size in sizes}, workers=workers, resource_scope=resource_scope
    )
    _say(progress, f"stage=MVQUAL; qualified_sizes={list(qualification.qualified_sizes)}")

    build_directory = root / "builds" / build_identity
    preparation = TargetOrderPreparation(
        build_identity=build_identity,
        dataset_id=population.dataset_id,
        population_digest=population.content_digest,
        split_digest=split.content_digest,
        target_coverage_reference_digest=reference.content_digest,
        obligation_authority_digest=authority.content_digest,
        feasibility_report_digest=feasibility.content_digest,
        mvidx_content_digest=forward.mvidx_content_digest,
        selection_plan_digest=selection.content_digest,
        repair_plan_digest=repair.content_digest,
        qualification_plan_digest=qualification.content_digest,
        configured_sizes=sizes,
        training_order_digest=training_order_digest(order),
        artifact_paths=(
            ("build", _relative(root, build_directory)),
            ("geometry", _relative(root, geometry_directory)),
            ("mvidx", _relative(root, mvidx_directory)),
            ("reference", _relative(root, reference_directory)),
        ),
    )
    build = TargetOrderBuild(
        preparation=preparation,
        obligation_authority=authority,
        feasibility_report=feasibility,
        selection_plan=selection,
        repair_plan=repair,
        qualification=qualification,
        frame_uids=order,
    )

    def write(_directory: Path) -> Mapping[str, Any]:
        return {
            "schema": TARGET_ORDER_BUILD_SCHEMA,
            "content_digest": preparation.content_digest,
            "neighborhood_digest": neighborhood_digest,
            "preparation": preparation.to_dict(),
            "obligation_authority": authority.to_dict(),
            "feasibility_report": feasibility.to_dict(),
            "selection_plan": selection.to_dict(),
            "repair_plan": repair.to_dict(),
            "qualification": qualification.to_dict(),
            "frame_uids": list(order),
        }

    publish_artifact_directory(
        build_directory,
        schema=TARGET_ORDER_BUILD_SCHEMA,
        write=write,
        verify_existing=lambda path, _manifest: _read_build(path, root),
    )
    # Build-owned continuation state is no longer needed once the build
    # result is published; nothing current ever referenced it.
    shutil.rmtree(pure_checkpoints, ignore_errors=True)
    shutil.rmtree(suffix_checkpoints, ignore_errors=True)
    _say(
        progress,
        f"stage=published; build={build_identity[:12]}; swaps={repair.total_swaps}; "
        f"phase_a_completed_at={selection.phase_a_completed_at}; selector_workers={selector_workers}; "
        f"pure={pure.telemetry.to_dict()}; suffix={suffix.telemetry.to_dict()}",
    )
    return build


def target_order_protected_paths(prepared_root: Path, preparation: TargetOrderPreparation) -> set[Path]:
    """Artifact directories a prepared generation naming ``preparation`` requires."""

    root = target_order_root(prepared_root)
    return {root / relative for _name, relative in preparation.artifact_paths}


__all__ = [
    "TARGET_ORDER_PREPARATION_SCHEMA",
    "TargetOrderBuild",
    "TargetOrderPreparation",
    "prepare_target_training_order",
    "target_order_build_identity",
    "target_order_method_identity",
    "target_order_protected_paths",
    "target_order_root",
    "training_order_digest",
]
