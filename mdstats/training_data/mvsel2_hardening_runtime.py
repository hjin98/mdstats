"""Campaign-runtime integration for the MVSEL2 hardening workplan.

The module is intentionally an orchestration shim: it does not redefine the
frozen selector or repair science.  It switches production v2 execution to the
native forward-only MVIDX reader, restores the highest valid MVSTATE2 prefix for
interrupted selection, and reuses pure-selector checkpoints in REPAIR2 only
until the first accepted repair divergence.
"""

from __future__ import annotations

import json
import time
from typing import Any, Mapping

import numpy as np

from ._common import TrainingDataInputError
from .progress_timing import format_progress_time
from .target_coverage_sparse_index_store import (
    TARGET_COVERAGE_SPARSE_INDEX_NATIVE_POINTER_SCHEMA,
    read_target_coverage_sparse_index_forward_view_native_record,
)
from .target_multi_view_selection_state_v2 import (
    build_target_multi_view_selection_identity_v2,
    checkpoint_target_multi_view_forward_state_v2,
    read_target_multi_view_selection_checkpoint_v2,
    restore_target_multi_view_forward_state_v2,
    write_target_multi_view_selection_checkpoint_v2,
)
from .target_multi_view_selector_v2 import (
    TargetMultiViewSelectorPolicyV2,
    score_target_multi_view_candidate_v2,
    select_target_multi_view_candidate_v2,
    deselect_target_multi_view_candidate_v2,
)
from .target_multi_view_selector_v2_resume import (
    build_target_multi_view_selection_plan_v2_resumable,
    preserve_checkpoint_float_history_v2,
)
from . import target_multi_view_repair_v2 as _repair


def _raw_record_payload(store: Any, key: str) -> Mapping[str, Any] | None:
    row = store._connect().execute(
        "SELECT payload FROM records WHERE key = ?", (str(key),)
    ).fetchone()
    if row is None:
        return None
    payload = json.loads(str(row[0]))
    return payload if isinstance(payload, Mapping) else None


def _native_forward_view(store: Any, full_sparse_index: Any) -> Any:
    """Open the persisted MVIDX1 forward arrays without inverse mappings."""

    rows = store._connect().execute(
        "SELECT key, payload FROM records WHERE class_name = ? ORDER BY updated_utc DESC",
        ("TargetCoverageSparseIndex",),
    ).fetchall()
    for _key, encoded in rows:
        try:
            pointer = json.loads(str(encoded))
        except Exception:
            continue
        if not isinstance(pointer, Mapping):
            continue
        if pointer.get("schema") != TARGET_COVERAGE_SPARSE_INDEX_NATIVE_POINTER_SCHEMA:
            continue
        if pointer.get("content_digest") != full_sparse_index.content_digest:
            continue
        return read_target_coverage_sparse_index_forward_view_native_record(
            pointer, store.path.parent
        )
    raise TrainingDataInputError(
        "TARGET-DATA2C-MVSEL2 requires the persisted native MVIDX1 pointer; "
        "no compatible forward-only record was found."
    )


def _checkpoint_rows(store: Any, domain_id: str) -> list[tuple[int, Mapping[str, Any]]]:
    prefix = f"target_multi_view_selection_state_v2:{domain_id}:"
    rows = store._connect().execute(
        "SELECT key, payload FROM records WHERE key LIKE ?", (prefix + "%",)
    ).fetchall()
    result: list[tuple[int, Mapping[str, Any]]] = []
    for key, encoded in rows:
        try:
            size = int(str(key).rsplit(":", 1)[1])
            payload = json.loads(str(encoded))
        except Exception:
            continue
        if isinstance(payload, Mapping):
            result.append((size, payload))
    return sorted(result, key=lambda item: item[0], reverse=True)


def _restore_checkpoint(
    pointer: Mapping[str, Any],
    *,
    store: Any,
    reference_domain: Any,
    forward_domain: Any,
    dataset_id: str,
    selector_policy: TargetMultiViewSelectorPolicyV2,
) -> Any:
    expected = build_target_multi_view_selection_identity_v2(
        reference_domain,
        forward_domain,
        dataset_id=dataset_id,
        selector_policy=selector_policy.to_dict(),
    )
    checkpoint = read_target_multi_view_selection_checkpoint_v2(
        pointer, store.path.parent
    )
    state = restore_target_multi_view_forward_state_v2(
        checkpoint,
        reference_domain,
        forward_domain,
        expected_identity=expected,
    )
    return preserve_checkpoint_float_history_v2(checkpoint, state)


def _highest_valid_resume_states(
    store: Any,
    coverage_reference: Any,
    forward: Any,
    policy: TargetMultiViewSelectorPolicyV2,
) -> tuple[dict[str, Any], dict[str, Mapping[str, Any]]]:
    states: dict[str, Any] = {}
    pointers: dict[str, Mapping[str, Any]] = {}
    for reference_domain in coverage_reference.domains:
        forward_domain = forward.domain(reference_domain.label_domain_id)
        limit = max(
            size for size in policy.target_sizes if size <= forward_domain.candidate_count
        )
        for size, pointer in _checkpoint_rows(store, reference_domain.label_domain_id):
            if size > limit:
                continue
            try:
                state = _restore_checkpoint(
                    pointer,
                    store=store,
                    reference_domain=reference_domain,
                    forward_domain=forward_domain,
                    dataset_id=coverage_reference.dataset_id,
                    selector_policy=policy,
                )
            except Exception as exc:
                print(
                    f"[TARGET-DATA2C-MVSEL2 restart] checkpoint {reference_domain.label_domain_id}:{size} "
                    f"is unusable ({exc}); trying an earlier checkpoint",
                    flush=True,
                )
                continue
            if state.selected_count != size:
                continue
            states[reference_domain.label_domain_id] = state
            pointers[reference_domain.label_domain_id] = pointer
            break
    return states, pointers


def _all_valid_rung_states(
    store: Any,
    coverage_reference: Any,
    forward: Any,
    policy: TargetMultiViewSelectorPolicyV2,
) -> dict[str, dict[int, Any]]:
    result: dict[str, dict[int, Any]] = {}
    allowed_sizes = set(policy.target_sizes)
    for reference_domain in coverage_reference.domains:
        forward_domain = forward.domain(reference_domain.label_domain_id)
        by_size: dict[int, Any] = {}
        for size, pointer in _checkpoint_rows(store, reference_domain.label_domain_id):
            if size not in allowed_sizes or size > forward_domain.candidate_count:
                continue
            try:
                state = _restore_checkpoint(
                    pointer,
                    store=store,
                    reference_domain=reference_domain,
                    forward_domain=forward_domain,
                    dataset_id=coverage_reference.dataset_id,
                    selector_policy=policy,
                )
            except Exception:
                continue
            if state.selected_count == size:
                by_size[size] = state
        result[reference_domain.label_domain_id] = by_size
    return result


def _ensure_target_multi_view_selection_v2(
    core: Any,
    store: Any,
    *,
    cfg: Mapping[str, Any],
    coverage_reference: Any,
    sparse_index: Any,
) -> tuple[Any, dict[str, Any]]:
    import mdstats

    policy = TargetMultiViewSelectorPolicyV2()
    forward = _native_forward_view(store, sparse_index)
    try:
        existing = store.get_record_optional(
            "target_multi_view_selection_v2", mdstats.TargetMultiViewSelectionPlanV2
        )
    except Exception as exc:
        print(
            f"[TARGET-DATA2C-MVSEL2 restart] stored v2 authority is unavailable ({exc}); rebuilding",
            flush=True,
        )
        existing = None
    if existing is not None:
        try:
            mdstats.validate_target_multi_view_selection_authority_v2(
                existing,
                target_coverage_reference=coverage_reference,
                target_coverage_sparse_index=sparse_index,
                query_workers=1,
            )
        except Exception as exc:
            print(
                f"[TARGET-DATA2C-MVSEL2 restart] stored v2 authority failed validation ({exc}); rebuilding",
                flush=True,
            )
        else:
            core._ok(
                f"TARGET-DATA2C-MVSEL2 reused: digest={existing.content_digest[:12]}...; "
                "legacy MVSEL1 records retained"
            )
            return existing, {}

    core._print_header("TARGET-DATA2C-MVSEL2 exact forward/lazy selector")
    checkpoint_pointers: dict[str, Any] = {}
    resume_states, resume_pointers = _highest_valid_resume_states(
        store, coverage_reference, forward, policy
    )
    checkpoint_pointers.update({
        f"resume:{domain_id}": pointer for domain_id, pointer in resume_pointers.items()
    })

    def checkpoint(reference_domain: Any, forward_domain: Any, state: Any, size: int) -> None:
        identity = build_target_multi_view_selection_identity_v2(
            reference_domain,
            forward_domain,
            dataset_id=coverage_reference.dataset_id,
            selector_policy=policy.to_dict(),
        )
        frozen = checkpoint_target_multi_view_forward_state_v2(state, identity)
        pointer = write_target_multi_view_selection_checkpoint_v2(
            frozen, store.external_record_directory
        )
        key = (
            f"target_multi_view_selection_state_v2:{reference_domain.label_domain_id}:{size}"
        )
        store.put_record(key, pointer)
        checkpoint_pointers[key] = pointer

    workers, resources = core._target_coverage_query_workers(cfg)
    scope = core.build_stage_resource_scope(
        resources,
        stage_name="TARGET-DATA2C-MVSEL2/MVSTATE2",
        python_workers=max(1, workers),
        structural_workers=1,
        tree_workers=1,
        blas_threads=1,
    )
    started = time.monotonic()
    with core.stage_resource_scope(scope):
        plan = build_target_multi_view_selection_plan_v2_resumable(
            coverage_reference,
            forward,
            policy=policy,
            workers=max(1, workers),
            checkpoint_callback=checkpoint,
            progress_callback=lambda message: print(
                f"[TARGET-DATA2C-MVSEL2] {message}", flush=True
            ),
            progress_interval_seconds=float(
                core._cfg(cfg, "performance", "progress_interval_seconds", 30.0)
            ),
            resume_states=resume_states,
        )
    mdstats.validate_target_multi_view_selection_authority_v2(
        plan,
        target_coverage_reference=coverage_reference,
        target_coverage_sparse_index=sparse_index,
        query_workers=1,
    )
    store.put_record("target_multi_view_selection_v2", plan)
    core._ok(
        f"TARGET-DATA2C-MVSEL2 + MVSTATE2 accepted: digest={plan.content_digest[:12]}...; "
        f"checkpoints={len(checkpoint_pointers)}; "
        f"elapsed={format_progress_time(time.monotonic() - started)}; "
        "native-forward-runtime=true; legacy MVSEL1/MVSTATE-REUSE1 records retained"
    )
    return plan, checkpoint_pointers


def _build_repair_from_checkpoints(
    coverage_reference: Any,
    forward: Any,
    selection_plan: Any,
    *,
    policy: _repair.TargetMultiViewRepairPolicyV2,
    checkpoint_states: Mapping[str, Mapping[int, Any]],
    progress_callback: Any | None = None,
) -> _repair.TargetMultiViewRepairPlanV2:
    domains: list[_repair.TargetMultiViewRepairDomainPlanV2] = []
    for reference_domain in coverage_reference.domains:
        started = time.monotonic()
        forward_domain = forward.domain(reference_domain.label_domain_id)
        selection_domain = selection_plan.domain(reference_domain.label_domain_id)
        uid_to_candidate = {
            uid: index for index, uid in enumerate(reference_domain.frame_uids)
        }
        order = [uid_to_candidate[item.frame_uid] for item in selection_domain.master_order]
        state = _repair.build_target_multi_view_forward_state_v2(
            reference_domain, forward_domain
        )
        previous_size = 0
        rungs: list[Any] = []
        scratch = _repair._RepairProposalScratchV2(forward_domain)
        diverged = False
        proposal_count = 0
        restore_count = 0
        for base_rung in selection_domain.rungs:
            size = int(base_rung.target_size)
            if not base_rung.materializable:
                rungs.append(_repair.TargetMultiViewRepairRung(
                    target_size=size,
                    materializable=False,
                    active_shell_start=previous_size,
                    unavailable_reason=base_rung.unavailable_reason or "unavailable_in_mvsel2",
                ))
                continue
            shell_start = previous_size
            restored_this_rung = False
            if not diverged:
                candidate_state = checkpoint_states.get(
                    reference_domain.label_domain_id, {}
                ).get(size)
                if candidate_state is not None:
                    expected = tuple(order[:size])
                    if tuple(candidate_state.selected_order) == expected:
                        state = candidate_state
                        restored_this_rung = True
                        restore_count += 1
            if not restored_this_rung:
                for rank in range(previous_size, size):
                    candidate = order[rank]
                    score = score_target_multi_view_candidate_v2(
                        candidate, forward_domain, state
                    )
                    select_target_multi_view_candidate_v2(
                        candidate, forward_domain, state, score=score
                    )
            shell_size = size - shell_start
            initial_zero = sum(
                _repair._removal_metrics(order[rank], forward_domain, state)[0]
                <= policy.unique_coverage_tolerance
                for rank in range(shell_start, size)
            )
            accepted: list[Any] = []
            for pass_index in range(policy.max_passes_per_shell):
                changed = False
                while len(accepted) < policy.max_swaps_per_shell:
                    removals: list[tuple[int, int, float, float]] = []
                    for rank in range(shell_start, size):
                        candidate = order[rank]
                        unique, loss = _repair._removal_metrics(
                            candidate, forward_domain, state
                        )
                        if (
                            unique <= policy.unique_coverage_tolerance
                            and _repair._hard_safe(candidate, forward_domain, state)
                        ):
                            removals.append((rank, candidate, unique, loss))
                    removals.sort(key=lambda row: (
                        row[3],
                        -int(state.correlation_unit_counts[int(
                            forward_domain.candidate_correlation_unit_codes[row[1]]
                        )]),
                        reference_domain.frame_uids[row[1]],
                    ))
                    best = None
                    for removal in removals[: policy.removal_shortlist_limit]:
                        proposal_count += 1
                        proposal = _repair._proposal(
                            reference_domain,
                            forward_domain,
                            state,
                            removal,
                            policy,
                            scratch,
                        )
                        if proposal is not None:
                            best = _repair._better(
                                best,
                                proposal,
                                reference_domain,
                                policy.gain_tie_tolerance,
                            )
                    if best is None:
                        break
                    rank = int(best["rank"])
                    removed = int(best["removed"])
                    replacement = int(best["replacement"])
                    future = next(
                        (
                            index
                            for index in range(size, len(order))
                            if order[index] == replacement
                        ),
                        -1,
                    )
                    displaced = None
                    if future >= size:
                        order[future] = removed
                        displaced = future
                    order[rank] = replacement
                    deselect_target_multi_view_candidate_v2(
                        removed, forward_domain, state
                    )
                    accepted_score = score_target_multi_view_candidate_v2(
                        replacement, forward_domain, state
                    )
                    select_target_multi_view_candidate_v2(
                        replacement,
                        forward_domain,
                        state,
                        score=accepted_score,
                    )
                    diverged = True
                    before = best["before"]
                    after = best["after"]
                    accepted.append(_repair.TargetMultiViewRepairSwap(
                        target_size=size,
                        pass_index=pass_index,
                        swap_index=len(accepted),
                        rank=rank,
                        removed_frame_uid=reference_domain.frame_uids[removed],
                        replacement_frame_uid=reference_domain.frame_uids[replacement],
                        removed_unique_coverage=best["unique"],
                        removed_representative_loss=best["loss"],
                        hard_deficit_before=before[0],
                        hard_deficit_after=after[0],
                        minimum_coverage_before=before[1],
                        minimum_coverage_after=after[1],
                        total_coverage_before=before[2],
                        total_coverage_after=after[2],
                        representative_utility_before=before[3],
                        representative_utility_after=after[3],
                        unit_balance_before=before[4],
                        unit_balance_after=after[4],
                        bottleneck_family_id=best["bottleneck"],
                        displaced_future_rank=displaced,
                    ))
                    changed = True
                if not changed:
                    break
            coverage = tuple(
                (item.family_id, min(1.0, max(0.0, item.coverage_mass)))
                for item in state.family_states
            )
            unsatisfied = tuple(sorted(
                item.obligation_id
                for index, item in enumerate(forward_domain.obligations)
                if item.required
                and int(state.obligation_counts[index])
                < int(item.minimum_selected_frames)
            ))
            for family_id, value in coverage:
                if (
                    value + policy.gain_tie_tolerance
                    < dict(base_rung.family_coverage)[family_id]
                ):
                    raise TrainingDataInputError(
                        "TARGET-DATA2C-REPAIR2 same-N coverage regressed below MVSEL2."
                    )
            if base_rung.hard_obligations_passed and unsatisfied:
                raise TrainingDataInputError(
                    "TARGET-DATA2C-REPAIR2 hard obligations regressed below MVSEL2."
                )
            rungs.append(_repair.TargetMultiViewRepairRung(
                target_size=size,
                materializable=True,
                active_shell_start=shell_start,
                frame_uids=tuple(
                    reference_domain.frame_uids[candidate] for candidate in order[:size]
                ),
                family_coverage=coverage,
                hard_obligations_passed=not unsatisfied,
                unsatisfied_obligation_ids=unsatisfied,
                hard_coverage_qualified=(
                    not unsatisfied
                    and all(
                        value
                        >= selection_plan.policy.coverage_threshold
                        - policy.gain_tie_tolerance
                        for _, value in coverage
                    )
                ),
                swaps=tuple(accepted),
                zero_unique_shell_fraction=(
                    0.0 if not shell_size else initial_zero / shell_size
                ),
            ))
            if progress_callback is not None:
                progress_callback(
                    f"status=rung; progress={size}/{selection_domain.rungs[-1].target_size}; "
                    f"elapsed={format_progress_time(time.monotonic() - started)}; eta=--:--:--; "
                    f"domain={reference_domain.label_domain_id}; target_size={size}; "
                    f"active_shell_start={shell_start}; swaps={len(accepted)}; "
                    f"proposals={proposal_count}; proposal_full_state_copies=0; "
                    f"mvstate2_restore_count={restore_count}; "
                    f"selected_prefix_state_mode={'post_divergence_carried_state' if diverged else ('mvstate2' if restored_this_rung else 'selected_prefix_forward_replay')}; "
                    f"inverse_mutation=false"
                )
            previous_size = size
        domains.append(_repair.TargetMultiViewRepairDomainPlanV2(
            label_domain_id=reference_domain.label_domain_id,
            reference_domain_digest=reference_domain.content_digest,
            mvidx1_domain_digest=forward_domain.mvidx1_domain_digest,
            selection_domain_digest=selection_domain.content_digest,
            candidate_count=forward_domain.candidate_count,
            repaired_master_order=tuple(
                reference_domain.frame_uids[candidate] for candidate in order
            ),
            rungs=tuple(rungs),
            total_swaps=sum(len(rung.swaps) for rung in rungs),
        ))
    return _repair.TargetMultiViewRepairPlanV2(
        dataset_id=coverage_reference.dataset_id,
        target_coverage_reference_digest=coverage_reference.content_digest,
        mvidx1_content_digest=forward.mvidx1_content_digest,
        target_multi_view_selection_v2_digest=selection_plan.content_digest,
        policy=policy,
        domains=tuple(domains),
    )


def _ensure_target_multi_view_repair_v2(
    core: Any,
    store: Any,
    *,
    cfg: Mapping[str, Any],
    coverage_reference: Any,
    sparse_index: Any,
    selection_plan: Any,
) -> Any:
    import mdstats

    policy = _repair.TargetMultiViewRepairPolicyV2()
    try:
        existing = store.get_record_optional(
            "target_multi_view_repair_v2", mdstats.TargetMultiViewRepairPlanV2
        )
    except Exception as exc:
        print(
            f"[TARGET-DATA2C-REPAIR2 restart] stored v2 authority is unavailable ({exc}); rebuilding",
            flush=True,
        )
        existing = None
    if existing is not None:
        try:
            mdstats.validate_target_multi_view_repair_authority_v2(
                existing,
                target_coverage_reference=coverage_reference,
                target_coverage_sparse_index=sparse_index,
                target_multi_view_selection=selection_plan,
            )
        except Exception as exc:
            print(
                f"[TARGET-DATA2C-REPAIR2 restart] stored v2 authority failed validation ({exc}); rebuilding",
                flush=True,
            )
        else:
            core._ok(
                f"TARGET-DATA2C-REPAIR2 reused: digest={existing.content_digest[:12]}..."
            )
            return existing

    core._print_header("TARGET-DATA2C-REPAIR2 forward-state active-shell repair")
    forward = _native_forward_view(store, sparse_index)
    selector_policy = selection_plan.policy
    checkpoint_states = _all_valid_rung_states(
        store, coverage_reference, forward, selector_policy
    )
    repair_workers, resources = core._target_coverage_query_workers(cfg)
    scope = core.build_stage_resource_scope(
        resources,
        stage_name="TARGET-DATA2C-REPAIR2",
        python_workers=max(1, repair_workers),
        structural_workers=1,
        tree_workers=1,
        blas_threads=1,
    )
    started = time.monotonic()
    with core.stage_resource_scope(scope):
        plan = _build_repair_from_checkpoints(
            coverage_reference,
            forward,
            selection_plan,
            policy=policy,
            checkpoint_states=checkpoint_states,
            progress_callback=lambda message: print(
                f"[TARGET-DATA2C-REPAIR2] {message}", flush=True
            ),
        )
    mdstats.validate_target_multi_view_repair_authority_v2(
        plan,
        target_coverage_reference=coverage_reference,
        target_coverage_sparse_index=sparse_index,
        target_multi_view_selection=selection_plan,
    )
    store.put_record("target_multi_view_repair_v2", plan)
    core._ok(
        f"TARGET-DATA2C-REPAIR2 accepted: digest={plan.content_digest[:12]}...; "
        f"elapsed={format_progress_time(time.monotonic() - started)}; "
        "native-forward-runtime=true; proposal_full_state_copies=0"
    )
    return plan


def install_campaign_hardening(core: Any) -> None:
    """Install only the two v2 orchestration overrides into campaign core."""

    def selection(store: Any, *, cfg: Mapping[str, Any], coverage_reference: Any, sparse_index: Any):
        return _ensure_target_multi_view_selection_v2(
            core,
            store,
            cfg=cfg,
            coverage_reference=coverage_reference,
            sparse_index=sparse_index,
        )

    def repair(
        store: Any,
        *,
        cfg: Mapping[str, Any],
        coverage_reference: Any,
        sparse_index: Any,
        selection_plan: Any,
    ):
        return _ensure_target_multi_view_repair_v2(
            core,
            store,
            cfg=cfg,
            coverage_reference=coverage_reference,
            sparse_index=sparse_index,
            selection_plan=selection_plan,
        )

    core._ensure_target_multi_view_selection_v2 = selection
    core._ensure_target_multi_view_repair_v2 = repair
