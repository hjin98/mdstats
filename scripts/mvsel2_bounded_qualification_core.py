#!/usr/bin/env python3
"""Qualification-only launcher for the frozen REV8 core engine.

The historical core engine is kept byte-for-byte in
``mvsel2_bounded_qualification_engine.py``.  This launcher supplies one
fail-closed compatibility shim: when a production campaign has authenticated
MVSTATE2 rung checkpoints but lacks the final ``target_multi_view_selection_v2``
record, reconstruct only the lightweight selection-plan view needed by the
qualifier from those checkpoints.  No production record is written and no
selector search is rerun.

The recovery path is deliberately metadata-streaming.  It authenticates each
checkpoint pointer, manifest, and complete bundle SHA, but loads only the small
``selected_order`` and ``obligation_counts`` arrays needed to reconstruct the
plan view.  Full family-multiplicity state remains on disk; the normal REV8
LQ2/LQ3 checks still exercise the production checkpoint deserializer where a
full state restore is materially required.
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


def _compact_checkpoint_metadata(
    pointer: Mapping[str, Any],
    *,
    root: Path,
    expected_identity: Any,
    expected_size: int,
    expected_family_count: int,
) -> dict[str, Any]:
    """Authenticate one MVSTATE2 checkpoint without materializing full state."""

    from mdstats.training_data._common import digest, sha256_file_cached
    from mdstats.training_data.target_coverage import _validate_array_reference
    from mdstats.training_data.target_multi_view_selection_state_v2 import (
        MVSTATE2_PERSISTENCE_VERSION,
        MVSTATE2_POINTER_SCHEMA,
        MVSTATE2_SCHEMA,
        TargetMultiViewSelectionIdentityV2,
    )

    if (
        pointer.get("schema") != MVSTATE2_POINTER_SCHEMA
        or pointer.get("persistence_version") != MVSTATE2_PERSISTENCE_VERSION
    ):
        raise RuntimeError("MVSTATE2 recovery encountered an unsupported checkpoint pointer")
    unsigned_pointer = {key: value for key, value in pointer.items() if key != "pointer_digest"}
    if pointer.get("pointer_digest") != digest(unsigned_pointer):
        raise RuntimeError("MVSTATE2 recovery pointer digest mismatch")

    root = root.resolve()
    relative = Path(str(pointer.get("relative_path", "")))
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("MVSTATE2 recovery pointer escapes campaign root")
    manifest_path = (root / relative).resolve()
    if root not in manifest_path.parents or not manifest_path.is_file():
        raise RuntimeError("MVSTATE2 recovery manifest is missing")
    if sha256_file_cached(manifest_path) != pointer.get("sha256"):
        raise RuntimeError("MVSTATE2 recovery manifest SHA mismatch")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise RuntimeError("MVSTATE2 recovery manifest is not an object")
    if (
        manifest.get("schema") != MVSTATE2_SCHEMA
        or manifest.get("persistence_version") != MVSTATE2_PERSISTENCE_VERSION
    ):
        raise RuntimeError("MVSTATE2 recovery manifest schema mismatch")
    unsigned_manifest = {
        key: value for key, value in manifest.items() if key != "manifest_digest"
    }
    if manifest.get("manifest_digest") != digest(unsigned_manifest):
        raise RuntimeError("MVSTATE2 recovery manifest digest mismatch")
    if manifest.get("content_digest") != pointer.get("content_digest"):
        raise RuntimeError("MVSTATE2 recovery content digest mismatch")

    identity = TargetMultiViewSelectionIdentityV2(**manifest["identity"])
    if identity.content_digest != manifest.get("identity_digest"):
        raise RuntimeError("MVSTATE2 recovery identity digest mismatch")
    if identity != expected_identity:
        raise RuntimeError("MVSTATE2 recovery scientific identity mismatch")
    if int(manifest.get("selected_count", -1)) != int(expected_size):
        raise RuntimeError("MVSTATE2 recovery selected-count mismatch")

    family_coverage_mass = tuple(float(value) for value in manifest["family_coverage_mass"])
    if len(family_coverage_mass) != int(expected_family_count):
        raise RuntimeError("MVSTATE2 recovery family cardinality mismatch")
    if any(
        not np.isfinite(value) or value < -5.0e-13 or value > 1.0 + 5.0e-13
        for value in family_coverage_mass
    ):
        raise RuntimeError("MVSTATE2 recovery family coverage is invalid")

    bundle_info = manifest.get("array_bundle")
    if not isinstance(bundle_info, Mapping):
        raise RuntimeError("MVSTATE2 recovery array bundle descriptor is missing")
    bundle_path = (manifest_path.parent / str(bundle_info.get("relative_path", ""))).resolve()
    if bundle_path.parent != manifest_path.parent or not bundle_path.is_file():
        raise RuntimeError("MVSTATE2 recovery array bundle is missing")
    if bundle_path.stat().st_size != int(bundle_info.get("size_bytes", -1)):
        raise RuntimeError("MVSTATE2 recovery array bundle size mismatch")
    # This streams the complete file through the hash cache and authenticates
    # all arrays without faulting every array into the Python process.
    if sha256_file_cached(bundle_path) != bundle_info.get("sha256"):
        raise RuntimeError("MVSTATE2 recovery array bundle SHA mismatch")

    descriptors = manifest.get("arrays")
    if not isinstance(descriptors, Mapping):
        raise RuntimeError("MVSTATE2 recovery array descriptors are missing")
    compact: dict[str, np.ndarray] = {}
    with np.load(bundle_path, allow_pickle=False) as bundle:
        for key in ("selected_order", "obligation_counts"):
            descriptor = descriptors.get(key)
            if not isinstance(descriptor, Mapping):
                raise RuntimeError(f"MVSTATE2 recovery descriptor missing: {key}")
            bundle_key = str(descriptor.get("bundle_key", ""))
            if bundle_key not in bundle.files:
                raise RuntimeError(f"MVSTATE2 recovery array missing: {key}")
            value = np.asarray(bundle[bundle_key])
            _validate_array_reference(descriptor.get("array_reference"), value, name=key)
            compact[key] = np.ascontiguousarray(value)

    selected = np.asarray(compact["selected_order"], dtype=np.int64)
    obligation_counts = np.asarray(compact["obligation_counts"], dtype=np.int64)
    if selected.shape != (int(expected_size),):
        raise RuntimeError("MVSTATE2 recovery selected-order shape mismatch")

    return {
        "identity": identity,
        "selected_order": selected,
        "obligation_counts": obligation_counts,
        "family_coverage_mass": family_coverage_mass,
        "unsatisfied_required_obligation_count": int(
            manifest.get("unsatisfied_required_obligation_count", -1)
        ),
        "content_digest": str(manifest.get("content_digest", "")),
        "bundle_size_bytes": int(bundle_info["size_bytes"]),
    }


def _recover_plan_payload(connection: sqlite3.Connection) -> dict[str, Any]:
    global _RECOVERY

    from mdstats.training_data.target_coverage_store import read_target_coverage_native_record
    from mdstats.training_data.target_coverage_sparse_index_store import (
        read_target_coverage_sparse_index_forward_view_native_record,
    )
    from mdstats.training_data.target_multi_view_selection_state_v2 import (
        build_target_multi_view_selection_identity_v2,
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
        materializable = tuple(
            size for size in policy.target_sizes if size <= forward_domain.candidate_count
        )
        if not materializable:
            raise RuntimeError(
                f"MVSTATE2 recovery has no materializable rung for domain {domain_id}"
            )
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
        compact_by_size: dict[int, dict[str, Any]] = {}
        for size in materializable:
            compact_by_size[size] = _compact_checkpoint_metadata(
                rows[size],
                root=root,
                expected_identity=expected_identity,
                expected_size=size,
                expected_family_count=len(forward_domain.families),
            )

        top_size = materializable[-1]
        top = np.asarray(compact_by_size[top_size]["selected_order"], dtype=np.int64)
        if np.any(top < 0) or np.any(top >= int(forward_domain.candidate_count)):
            raise RuntimeError(f"MVSTATE2 recovery top selected prefix is invalid for {domain_id}")
        if np.unique(top).size != top.size:
            raise RuntimeError(f"MVSTATE2 recovery top selected prefix has duplicates for {domain_id}")
        for size in materializable[:-1]:
            selected = np.asarray(compact_by_size[size]["selected_order"], dtype=np.int64)
            if not np.array_equal(selected, top[:size]):
                raise RuntimeError(
                    f"MVSTATE2 recovery prefixes are not nested for {domain_id}:{size}"
                )

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
                correlation_unit_code=int(
                    forward_domain.candidate_correlation_unit_codes[int(candidate)]
                ),
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
            compact = compact_by_size[size]
            selected = np.asarray(compact["selected_order"], dtype=np.int64)
            coverage = tuple(
                sorted(
                    (
                        str(family.family_id),
                        min(1.0, max(0.0, float(mass))),
                    )
                    for family, mass in zip(
                        forward_domain.families,
                        compact["family_coverage_mass"],
                        strict=True,
                    )
                )
            )
            obligation_counts = np.asarray(compact["obligation_counts"], dtype=np.int64)
            if obligation_counts.shape != (len(forward_domain.obligations),):
                raise RuntimeError(
                    f"MVSTATE2 recovery obligation shape mismatch for {domain_id}:{size}"
                )
            if np.any(obligation_counts < 0):
                raise RuntimeError(
                    f"MVSTATE2 recovery obligation count is negative for {domain_id}:{size}"
                )
            unsatisfied = tuple(
                sorted(
                    str(item.obligation_id)
                    for index, item in enumerate(forward_domain.obligations)
                    if item.required
                    and int(obligation_counts[index]) < int(item.minimum_selected_frames)
                )
            )
            if len(unsatisfied) != int(compact["unsatisfied_required_obligation_count"]):
                raise RuntimeError(
                    f"MVSTATE2 recovery obligation state mismatch for {domain_id}:{size}"
                )
            qualified = not unsatisfied and all(
                value >= policy.coverage_threshold - policy.gain_tie_tolerance
                for _family_id, value in coverage
            )
            rungs.append(
                TargetMultiViewSelectionRung(
                    target_size=size,
                    materializable=True,
                    frame_uids=tuple(
                        reference_domain.frame_uids[int(candidate)] for candidate in selected
                    ),
                    family_coverage=coverage,
                    hard_obligations_passed=not unsatisfied,
                    unsatisfied_obligation_ids=unsatisfied,
                    hard_coverage_qualified=qualified,
                    phase_at_boundary=(
                        "representative_fill" if qualified else "hard_coverage"
                    ),
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
            "metadata_streaming": True,
            "checkpoint_bundle_sizes_bytes": {
                str(size): int(compact_by_size[size]["bundle_size_bytes"])
                for size in materializable
            },
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
        "full_checkpoint_state_materialized_for_recovery": False,
    }
    print(
        "[REV8 authority] final MVSEL2 plan record absent; using authenticated "
        "nested MVSTATE2 checkpoint authority with metadata-streaming recovery; "
        f"plan_digest={plan.content_digest[:12]}...",
        flush=True,
    )
    return plan.to_dict()


def _record_ro(connection: sqlite3.Connection, key: str) -> dict[str, Any]:
    try:
        return _ORIGINAL_RECORD_RO(connection, key)
    except RuntimeError as exc:
        if (
            key != "target_multi_view_selection_v2"
            or "missing production campaign record" not in str(exc)
        ):
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
# The frozen engine constructs its worker subprocess command from ``__file__``.
# Route that worker back through this launcher so the same fail-closed authority
# recovery shim applies in worker mode as in supervisor mode.
engine.__file__ = __file__


if __name__ == "__main__":
    raise SystemExit(engine.main())
