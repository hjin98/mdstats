"""Shared MVSEL2/REPAIR2 campaign I/O and orchestration helpers.

Scientific selector execution is owned by :mod:`mvsel2_selection_engine` and
scientific repair execution is owned by :mod:`target_multi_view_repair_v2`.
This module deliberately contains no candidate scoring, repair proposal,
selection mutation, or per-rung repair loop.  It only opens persisted forward
MVIDX1 state, authenticates MVSTATE2 records, invokes the canonical REPAIR2
owner, persists the resulting authority, and installs the campaign repair seam.
"""
from __future__ import annotations

import json
import time
from typing import Any, Mapping

from ._common import TrainingDataInputError
from .progress_timing import format_progress_time
from .target_coverage_sparse_index_store import (
    TARGET_COVERAGE_SPARSE_INDEX_NATIVE_POINTER_SCHEMA,
    read_target_coverage_sparse_index_forward_view_native_record,
)
from .target_multi_view_selection_state_v2 import (
    build_target_multi_view_selection_identity_v2,
    read_target_multi_view_selection_checkpoint_v2,
    restore_target_multi_view_forward_state_v2,
)
from .target_multi_view_selector_v2 import TargetMultiViewSelectorPolicyV2
from .target_multi_view_selector_v2_resume import preserve_checkpoint_float_history_v2
from . import target_multi_view_repair_v2 as _repair


def _raw_record_payload(store: Any, key: str) -> Mapping[str, Any] | None:
    """Return one raw JSON record for small execution-only companion records."""

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


def _checkpoint_rows(
    store: Any, domain_id: str
) -> list[tuple[int, Mapping[str, Any]]]:
    """List MVSTATE2 pointers newest-cardinality first for one label domain."""

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
    """Authenticate and restore one compact MVSTATE2 selector checkpoint."""

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
    """Compatibility helper for consumers that still request state-only resume."""

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
                    f"[TARGET-DATA2C-MVSEL2 restart] checkpoint "
                    f"{reference_domain.label_domain_id}:{size} is unusable "
                    f"({exc}); trying an earlier checkpoint",
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
    """Read valid rung states for compatibility diagnostics, not repair science.

    Production G3 no longer consumes this mapping.  The helper remains only for
    focused compatibility tests and can be removed once those tests migrate.
    """

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


def _build_repair_from_checkpoints(
    coverage_reference: Any,
    forward: Any,
    selection_plan: Any,
    *,
    policy: _repair.TargetMultiViewRepairPolicyV2,
    checkpoint_states: Mapping[str, Mapping[int, Any]],
    progress_callback: Any | None = None,
) -> _repair.TargetMultiViewRepairPlanV2:
    """Compatibility facade delegating all repair science to the canonical owner.

    The former implementation contained a second complete REPAIR2 loop.  G3
    removes that authority.  Selector checkpoints are intentionally ignored at
    this compatibility seam because the current canonical continuation hook
    cannot consume a pure-selector rung without skipping that rung's active
    shell.  Rank-zero forward replay is exact and fail-closed; checkpoint reuse
    can be reintroduced only inside the canonical owner after an equivalence
    proof.
    """

    del checkpoint_states

    wrapped_progress = None
    if progress_callback is not None:
        def wrapped_progress(message: str) -> None:
            progress_callback(f"{message}; mvstate2_restore_count=0")

    return _repair.build_target_multi_view_repair_plan_v2(
        coverage_reference,
        forward,
        selection_plan,
        policy=policy,
        workers=1,
        progress_callback=wrapped_progress,
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
    """Build/reuse production REPAIR2 through its single scientific owner."""

    import mdstats

    policy = _repair.TargetMultiViewRepairPolicyV2()
    try:
        existing = store.get_record_optional(
            "target_multi_view_repair_v2", mdstats.TargetMultiViewRepairPlanV2
        )
    except Exception as exc:
        print(
            f"[TARGET-DATA2C-REPAIR2 restart] stored v2 authority is unavailable "
            f"({exc}); rebuilding",
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
                f"[TARGET-DATA2C-REPAIR2 restart] stored v2 authority failed "
                f"validation ({exc}); rebuilding",
                flush=True,
            )
        else:
            core._ok(
                f"TARGET-DATA2C-REPAIR2 reused: digest={existing.content_digest[:12]}..."
            )
            return existing

    core._print_header("TARGET-DATA2C-REPAIR2 forward-state active-shell repair")
    forward = _native_forward_view(store, sparse_index)
    repair_workers, resources = core._target_coverage_query_workers(cfg)
    scope = core.build_stage_resource_scope(
        resources,
        stage_name="TARGET-DATA2C-REPAIR2",
        python_workers=1,
        structural_workers=1,
        tree_workers=1,
        blas_threads=1,
    )
    started = time.monotonic()
    with core.stage_resource_scope(scope):
        plan = _repair.build_target_multi_view_repair_plan_v2(
            coverage_reference,
            forward,
            selection_plan,
            policy=policy,
            workers=max(1, int(repair_workers)),
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
        "native-forward-runtime=true; proposal_full_state_copies=0; "
        "repair_science_owner=target_multi_view_repair_v2; "
        "repair_checkpoint_reuse=false"
    )
    return plan


def install_campaign_hardening(core: Any) -> None:
    """Install only the G3 REPAIR2 orchestration seam into campaign core."""

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

    core._ensure_target_multi_view_repair_v2 = repair
