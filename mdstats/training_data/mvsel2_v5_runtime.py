"""Protocol-5 campaign runtime for the single-owner MVSEL2 selector engine.

This module replaces only selection orchestration while G3 still owns REPAIR2
cleanup.  It reuses the established native-forward/checkpoint readers, pairs new
MVSTATE2 checkpoints with authenticated compact rank history, and routes fresh
and resumed selection through one engine.
"""
from __future__ import annotations

import time
from typing import Any, Mapping

from . import mvsel2_hardening_runtime as _legacy_runtime
from ._common import digest
from .mvsel2_selection_engine import (
    build_target_multi_view_selection_plan_v2_engine,
)
from .progress_timing import format_progress_time
from .target_multi_view_selection_history_v2 import (
    TargetMultiViewSelectionHistoryV2,
    decode_target_multi_view_selection_history_v2,
    encode_target_multi_view_selection_history_v2,
)
from .target_multi_view_selection_state_v2 import (
    build_target_multi_view_selection_identity_v2,
    checkpoint_target_multi_view_forward_state_v2,
    write_target_multi_view_selection_checkpoint_v2,
)
from .target_multi_view_selector_v2 import TargetMultiViewSelectorPolicyV2


_HISTORY_KEY_PREFIX = "target_multi_view_selection_history_v2"


def _history_key(domain_id: str, size: int) -> str:
    return f"{_HISTORY_KEY_PREFIX}:{domain_id}:{int(size)}"


def _highest_valid_resume_bundle(
    store: Any,
    coverage_reference: Any,
    forward: Any,
    policy: TargetMultiViewSelectorPolicyV2,
) -> tuple[
    dict[str, Any],
    dict[str, TargetMultiViewSelectionHistoryV2],
    dict[str, Mapping[str, Any]],
]:
    """Return highest valid state plus optional exact history per domain."""

    states: dict[str, Any] = {}
    histories: dict[str, TargetMultiViewSelectionHistoryV2] = {}
    pointers: dict[str, Mapping[str, Any]] = {}
    for reference_domain in coverage_reference.domains:
        domain_id = reference_domain.label_domain_id
        forward_domain = forward.domain(domain_id)
        limit = max(
            size
            for size in policy.target_sizes
            if size <= forward_domain.candidate_count
        )
        identity = build_target_multi_view_selection_identity_v2(
            reference_domain,
            forward_domain,
            dataset_id=coverage_reference.dataset_id,
            selector_policy=policy.to_dict(),
        )
        for size, pointer in _legacy_runtime._checkpoint_rows(store, domain_id):
            if size > limit:
                continue
            try:
                state = _legacy_runtime._restore_checkpoint(
                    pointer,
                    store=store,
                    reference_domain=reference_domain,
                    forward_domain=forward_domain,
                    dataset_id=coverage_reference.dataset_id,
                    selector_policy=policy,
                )
            except Exception as exc:
                print(
                    f"[TARGET-DATA2C-MVSEL2 restart] checkpoint {domain_id}:{size} "
                    f"is unusable ({exc}); trying an earlier checkpoint",
                    flush=True,
                )
                continue
            if state.selected_count != size:
                continue
            states[domain_id] = state
            pointers[domain_id] = pointer

            history_payload = _legacy_runtime._raw_record_payload(
                store, _history_key(domain_id, size)
            )
            if history_payload is not None:
                try:
                    histories[domain_id] = (
                        decode_target_multi_view_selection_history_v2(
                            history_payload,
                            expected_identity_digest=identity.content_digest,
                            expected_selected_order_digest=digest(
                                tuple(int(value) for value in state.selected_order)
                            ),
                            expected_selected_count=size,
                        )
                    )
                except Exception as exc:
                    print(
                        f"[TARGET-DATA2C-MVSEL2 restart] rank history "
                        f"{domain_id}:{size} is unusable ({exc}); "
                        "falling back to one legacy prefix reconstruction",
                        flush=True,
                    )
            break
    return states, histories, pointers


def ensure_target_multi_view_selection_v2(
    core: Any,
    store: Any,
    *,
    cfg: Mapping[str, Any],
    coverage_reference: Any,
    sparse_index: Any,
) -> tuple[Any, dict[str, Any]]:
    """Build/reuse the production MVSEL2 authority through the v5 engine."""

    import mdstats

    policy = TargetMultiViewSelectorPolicyV2()
    forward = _legacy_runtime._native_forward_view(store, sparse_index)
    try:
        existing = store.get_record_optional(
            "target_multi_view_selection_v2",
            mdstats.TargetMultiViewSelectionPlanV2,
        )
    except Exception as exc:
        print(
            f"[TARGET-DATA2C-MVSEL2 restart] stored v2 authority is unavailable "
            f"({exc}); rebuilding",
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
                f"[TARGET-DATA2C-MVSEL2 restart] stored v2 authority failed "
                f"validation ({exc}); rebuilding",
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
    resume_states, resume_histories, resume_pointers = _highest_valid_resume_bundle(
        store,
        coverage_reference,
        forward,
        policy,
    )
    checkpoint_pointers.update(
        {
            f"resume:{domain_id}": pointer
            for domain_id, pointer in resume_pointers.items()
        }
    )

    uid_to_index = {
        domain.label_domain_id: {
            uid: index for index, uid in enumerate(domain.frame_uids)
        }
        for domain in coverage_reference.domains
    }

    def checkpoint(
        reference_domain: Any,
        forward_domain: Any,
        state: Any,
        size: int,
    ) -> None:
        identity = build_target_multi_view_selection_identity_v2(
            reference_domain,
            forward_domain,
            dataset_id=coverage_reference.dataset_id,
            selector_policy=policy.to_dict(),
        )
        frozen = checkpoint_target_multi_view_forward_state_v2(state, identity)
        pointer = write_target_multi_view_selection_checkpoint_v2(
            frozen,
            store.external_record_directory,
        )
        key = (
            f"target_multi_view_selection_state_v2:"
            f"{reference_domain.label_domain_id}:{size}"
        )
        store.put_record(key, pointer)
        checkpoint_pointers[key] = pointer

    def history_checkpoint(
        reference_domain: Any,
        forward_domain: Any,
        history: TargetMultiViewSelectionHistoryV2,
        size: int,
    ) -> None:
        del forward_domain
        domain_id = reference_domain.label_domain_id
        identity = build_target_multi_view_selection_identity_v2(
            reference_domain,
            forward.domain(domain_id),
            dataset_id=coverage_reference.dataset_id,
            selector_policy=policy.to_dict(),
        )
        order = tuple(
            int(uid_to_index[domain_id][entry.frame_uid])
            for entry in history.entries
        )
        record = encode_target_multi_view_selection_history_v2(
            history,
            identity_digest=identity.content_digest,
            selected_order_digest=digest(order),
        )
        key = _history_key(domain_id, size)
        store.put_record(key, record)
        checkpoint_pointers[key] = record

    _, resources = core._target_coverage_query_workers(cfg)
    scope = core.build_stage_resource_scope(
        resources,
        stage_name="TARGET-DATA2C-MVSEL2/MVSTATE2",
        python_workers=1,
        structural_workers=1,
        tree_workers=1,
        blas_threads=1,
    )
    started = time.monotonic()
    with core.stage_resource_scope(scope):
        plan = build_target_multi_view_selection_plan_v2_engine(
            coverage_reference,
            forward,
            policy=policy,
            workers=1,
            checkpoint_callback=checkpoint,
            history_callback=history_checkpoint,
            progress_callback=lambda message: print(
                f"[TARGET-DATA2C-MVSEL2] {message}", flush=True
            ),
            progress_interval_seconds=float(
                core._cfg(
                    cfg,
                    "performance",
                    "progress_interval_seconds",
                    30.0,
                )
            ),
            resume_states=resume_states,
            resume_histories=resume_histories,
        )
    mdstats.validate_target_multi_view_selection_authority_v2(
        plan,
        target_coverage_reference=coverage_reference,
        target_coverage_sparse_index=sparse_index,
        query_workers=1,
    )
    store.put_record("target_multi_view_selection_v2", plan)
    core._ok(
        f"TARGET-DATA2C-MVSEL2 + MVSTATE2 accepted: "
        f"digest={plan.content_digest[:12]}...; "
        f"checkpoints={len(checkpoint_pointers)}; "
        f"elapsed={format_progress_time(time.monotonic() - started)}; "
        "native-forward-runtime=true; rank-history=true; "
        "legacy MVSEL1/MVSTATE-REUSE1 records retained"
    )
    return plan, checkpoint_pointers


def install_campaign_v5_selection(core: Any) -> None:
    """Install the Protocol-5 MVSEL2 selection orchestration authority."""

    def selection(
        store: Any,
        *,
        cfg: Mapping[str, Any],
        coverage_reference: Any,
        sparse_index: Any,
    ):
        return ensure_target_multi_view_selection_v2(
            core,
            store,
            cfg=cfg,
            coverage_reference=coverage_reference,
            sparse_index=sparse_index,
        )

    core._ensure_target_multi_view_selection_v2 = selection
