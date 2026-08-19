#!/usr/bin/env python3
"""Qualification-only launcher for the frozen REV8 core engine.

The historical core engine is kept byte-for-byte in
``mvsel2_bounded_qualification_engine.py``.  This launcher supplies one
fail-closed compatibility shim: when a production campaign has authenticated
MVSTATE2 rung checkpoints but lacks the final ``target_multi_view_selection_v2``
record, reconstruct only the lightweight selection-plan view needed by the
qualifier from those checkpoints.  No production record is written and no
selector search is rerun.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping

import numpy as np

import mvsel2_bounded_qualification_engine as engine

_RECOVERY: dict[str, Any] | None = None
_ORIGINAL_RECORD_RO = engine._record_ro
_ORIGINAL_JSON_DUMP = engine.json_dump


def _database_path(connection: sqlite3.Connection) -> Path:
    for _sequence, name, filename in connection.execute("PRAGMA database_list"):
        if str(name) == "main" and str(filename):
            return Path(str(filename)).resolve()
    raise RuntimeError("cannot resolve qualification SQLite database path")


def _checkpoint_rows_all(connection: sqlite3.Connection) -> dict[str, dict[int, dict[str, Any]]]:
    prefix = "target_multi_view_selection_state_v2:"
    rows = connection.execute(
        "SELECT key,payload FROM records WHERE key LIKE ?", (prefix + "%",)
    ).fetchall()
    result: dict[str, dict[int, dict[str, Any]]] = {}
    for key, encoded in rows:
        text = str(key)
        try:
            remainder = text[len(prefix):]
            domain, size_text = remainder.rsplit(":", 1)
            size = int(size_text)
            payload = json.loads(str(encoded))
        except Exception:
            continue
        if isinstance(payload, dict):
            result.setdefault(domain, {})[size] = payload
    return result


def _recover_plan_payload(connection: sqlite3.Connection) -> dict[str, Any]:
    global _RECOVERY

    from mdstats.training_data.target_coverage_store import read_target_coverage_native_record
    from mdstats.training_data.target_coverage_sparse_index_store import (
        read_target_coverage_sparse_index_forward_view_native_record,
    )
    from mdstats.training_data.target_multi_view_selection_state_v2 import (
        build_target_multi_view_selection_identity_v2,
        read_target_multi_view_selection_checkpoint_v2,
    )
    from mdstats.training_data.target_multi_view_selector import (
        TargetMultiViewSelectionEntry,
        TargetMultiViewSelectionRung,
    )
    from mdstats.training_data.target_multi_view_selector_v2 import (
        TargetMultiViewSelectionDomainPlanV2,
        TargetMultiViewSelectionPlanV2,
        TargetMultiViewSelectorPolicyV2,
    )

    database = _database_path(connection)
    root = database.parent
    reference_pointer = _ORIGINAL_RECORD_RO(connection, "target_coverage_reference")
    sparse_pointer = _ORIGINAL_RECORD_RO(connection, "target_coverage_sparse_index")
    reference = read_target_coverage_native_record(reference_pointer, root)
    forward = read_target_coverage_sparse_index_forward_view_native_record(sparse_pointer, root)
    policy = TargetMultiViewSelectorPolicyV2()
    rows_by_domain = _checkpoint_rows_all(connection)
    domains: list[TargetMultiViewSelectionDomainPlanV2] = []
    recovery_domains: dict[str, Any] = {}

    for reference_domain in reference.domains:
        domain_id = str(reference_domain.label_domain_id)
        forward_domain = forward.domain(domain_id)
        rows = rows_by_domain.get(domain_id, {})
        materializable = tuple(size for size in policy.target_sizes if size <= forward_domain.candidate_count)
        if not materializable:
            raise RuntimeError(f"MVSTATE2 recovery has no materializable rung for domain {domain_id}")
        missing = tuple(size for size in materializable if size not in rows)
        if missing:
            raise RuntimeError(
                "final MVSEL2 plan record is absent and MVSTATE2 recovery is "
                f"incomplete for {domain_id}; missing checkpoints={missing}"
            )

        expected_identity = build_target_multi_view_selection_identity_v2(
            reference_domain,
            forward_domain,
            dataset_id=reference.dataset_id,
            selector_policy=policy.to_dict(),
        )
        checkpoints: dict[int, Any] = {}
        for size in materializable:
            checkpoint = read_target_multi_view_selection_checkpoint_v2(rows[size], root)
            if checkpoint.identity != expected_identity:
                raise RuntimeError(f"MVSTATE2 recovery identity mismatch for {domain_id}:{size}")
            selected = np.asarray(checkpoint.selected_order, dtype=np.int64)
            if selected.shape != (size,):
                raise RuntimeError(f"MVSTATE2 recovery cardinality mismatch for {domain_id}:{size}")
            if np.any(selected < 0) or np.any(selected >= int(forward_domain.candidate_count)) or np.unique(selected).size != selected.size:
                raise RuntimeError(f"MVSTATE2 recovery selected prefix is invalid for {domain_id}:{size}")
            checkpoints[size] = checkpoint

        top_size = materializable[-1]
        top = np.asarray(checkpoints[top_size].selected_order, dtype=np.int64)
        for size in materializable[:-1]:
            selected = np.asarray(checkpoints[size].selected_order, dtype=np.int64)
            if not np.array_equal(selected, top[:size]):
                raise RuntimeError(f"MVSTATE2 recovery prefixes are not nested for {domain_id}:{size}")

        entries = tuple(
            TargetMultiViewSelectionEntry(
                rank=rank,
                frame_uid=reference_domain.frame_uids[int(candidate)],
                phase="hard_coverage",
                primary_reason="mvstate2_recovered_authority",
                bottleneck_family_id=None,
                hard_obligation_gain=0,
                bottleneck_coverage_gain=0.0,
                total_coverage_gain=0.0,
                representative_gain=0.0,
                normalized_diversity=0.0,
                correlation_unit_code=int(forward_domain.candidate_correlation_unit_codes[int(candidate)]),
            )
            for rank, candidate in enumerate(top)
        )

        rungs: list[TargetMultiViewSelectionRung] = []
        for size in policy.target_sizes:
            if size > int(forward_domain.candidate_count):
                rungs.append(
                    TargetMultiViewSelectionRung(
                        target_size=size,
                        materializable=False,
                        unavailable_reason=(
                            f"authorized_pool_has_{forward_domain.candidate_count}_frames_below_required_{size}"
                        ),
                    )
                )
                continue
            checkpoint = checkpoints[size]
            selected = np.asarray(checkpoint.selected_order, dtype=np.int64)
            coverage = tuple(sorted(
                (str(family.family_id), min(1.0, max(0.0, float(mass))))
                for family, mass in zip(
                    forward_domain.families,
                    checkpoint.family_coverage_mass,
                    strict=True,
                )
            ))
            obligation_counts = np.asarray(checkpoint.obligation_counts, dtype=np.int64)
            if obligation_counts.shape != (len(forward_domain.obligations),):
                raise RuntimeError(f"MVSTATE2 recovery obligation shape mismatch for {domain_id}:{size}")
            unsatisfied = tuple(sorted(
                str(item.obligation_id)
                for index, item in enumerate(forward_domain.obligations)
                if item.required and int(obligation_counts[index]) < int(item.minimum_selected_frames)
            ))
            if len(unsatisfied) != int(checkpoint.unsatisfied_required_obligation_count):
                raise RuntimeError(f"MVSTATE2 recovery obligation state mismatch for {domain_id}:{size}")
            qualified = not unsatisfied and all(
                value >= policy.coverage_threshold - policy.gain_tie_tolerance
                for _family_id, value in coverage
            )
            rungs.append(
                TargetMultiViewSelectionRung(
                    target_size=size,
                    materializable=True,
                    frame_uids=tuple(reference_domain.frame_uids[int(candidate)] for candidate in selected),
                    family_coverage=coverage,
                    hard_obligations_passed=not unsatisfied,
                    unsatisfied_obligation_ids=unsatisfied,
                    hard_coverage_qualified=qualified,
                    phase_at_boundary="representative_fill" if qualified else "hard_coverage",
                    shell_coverage_gain=0.0,
                    shell_representative_gain=0.0,
                )
            )

        domain_plan = TargetMultiViewSelectionDomainPlanV2(
            label_domain_id=domain_id,
            reference_domain_digest=reference_domain.content_digest,
            mvidx1_domain_digest=forward_domain.mvidx1_domain_digest,
            candidate_count=int(forward_domain.candidate_count),
            master_order=entries,
            rungs=tuple(rungs),
            phase_a_completed_at=None,
        )
        domains.append(domain_plan)
        recovery_domains[domain_id] = {
            "checkpoint_sizes": materializable,
            "top_checkpoint": top_size,
            "nested_prefixes": True,
            "identity_digest": expected_identity.content_digest,
        }

    plan = TargetMultiViewSelectionPlanV2(
        dataset_id=reference.dataset_id,
        target_coverage_reference_digest=reference.content_digest,
        mvidx1_content_digest=forward.mvidx1_content_digest,
        policy=policy,
        domains=tuple(domains),
    )
    _RECOVERY = {
        "source": "MVSTATE2_RECOVERED",
        "reason": "missing target_multi_view_selection_v2 production record",
        "plan_content_digest": plan.content_digest,
        "domains": recovery_domains,
        "production_database": str(database),
        "production_mutated": False,
        "selector_search_rerun": False,
    }
    print(
        "[REV8 authority] final MVSEL2 plan record absent; using authenticated "
        "nested MVSTATE2 checkpoint authority; "
        f"plan_digest={plan.content_digest[:12]}...",
        flush=True,
    )
    return plan.to_dict()


def _record_ro(connection: sqlite3.Connection, key: str) -> dict[str, Any]:
    try:
        return _ORIGINAL_RECORD_RO(connection, key)
    except RuntimeError as exc:
        if key != "target_multi_view_selection_v2" or "missing production campaign record" not in str(exc):
            raise
        return _recover_plan_payload(connection)


def _json_dump(path: Path, payload: Mapping[str, Any]) -> None:
    if _RECOVERY is not None and Path(path).name == "worker.json":
        enriched = dict(payload)
        enriched["selection_authority_source"] = _RECOVERY["source"]
        enriched["selection_authority_recovery"] = _RECOVERY
        payload = enriched
    _ORIGINAL_JSON_DUMP(path, payload)


engine._record_ro = _record_ro
engine.json_dump = _json_dump


if __name__ == "__main__":
    raise SystemExit(engine.main())
