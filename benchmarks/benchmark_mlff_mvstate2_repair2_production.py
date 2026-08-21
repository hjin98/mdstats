#!/usr/bin/env python3
"""Production-prefix checkpoint/recovery and REPAIR2 qualification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import tempfile
import time

import numpy as np

from mdstats.training_data.target_coverage_sparse_index_store import read_target_coverage_sparse_index_forward_view_native_record
from mdstats.training_data.target_coverage_store import read_target_coverage_native_record
from mdstats.training_data.target_multi_view_repair_v2 import TargetMultiViewRepairPolicyV2, build_target_multi_view_repair_plan_v2
from mdstats.training_data.target_multi_view_selection_state_v2 import (
    build_target_multi_view_selection_identity_v2, checkpoint_target_multi_view_forward_state_v2,
    read_target_multi_view_selection_checkpoint_v2, restore_target_multi_view_forward_state_v2,
    write_target_multi_view_selection_checkpoint_v2,
)
from mdstats.training_data.target_multi_view_selector import TargetMultiViewSelectionEntry, TargetMultiViewSelectionRung
from mdstats.training_data.target_multi_view_selector_v2 import (
    TargetMultiViewSelectionDomainPlanV2, TargetMultiViewSelectionPlanV2, TargetMultiViewSelectorPolicyV2,
    build_target_multi_view_forward_state_v2, score_target_multi_view_candidate_v2, select_target_multi_view_candidate_v2,
)


def _pointer(database: Path, key: str) -> dict[str, object]:
    with sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True) as connection:
        row = connection.execute("SELECT payload FROM records WHERE key=?", (key,)).fetchone()
    if row is None:
        raise RuntimeError(key)
    return json.loads(row[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign_database", type=Path)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--selector-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.campaign_database.resolve().parent
    reference = read_target_coverage_native_record(_pointer(args.campaign_database, "target_coverage_reference"), root)
    forward = read_target_coverage_sparse_index_forward_view_native_record(_pointer(args.campaign_database, "target_coverage_sparse_index"), root)
    rd = reference.domain(args.domain); fd = forward.domain(args.domain)
    order = tuple(int(value) for value in json.loads(args.selector_evidence.read_text())["selected_candidate_order"])
    sizes = (128, 256)
    if len(order) < sizes[-1]:
        raise RuntimeError("selector evidence prefix is too short")
    policy = TargetMultiViewSelectorPolicyV2(target_sizes=sizes)
    state = build_target_multi_view_forward_state_v2(rd, fd, requested_cardinality=sizes[-1])
    entries = []
    rungs = []
    previous = 0
    replay_started = time.perf_counter()
    for rank, candidate in enumerate(order[:sizes[-1]]):
        score = score_target_multi_view_candidate_v2(candidate, fd, state)
        entries.append(TargetMultiViewSelectionEntry(
            rank=rank, frame_uid=rd.frame_uids[candidate], phase="hard_coverage",
            primary_reason="production_prefix_replay", bottleneck_family_id=fd.families[0].family_id,
            hard_obligation_gain=score.hard_obligation_gain, bottleneck_coverage_gain=score.family_coverage_gains[0],
            total_coverage_gain=score.total_coverage_gain, representative_gain=score.representative_gain,
            normalized_diversity=score.sparse_diversity,
            correlation_unit_code=int(fd.candidate_correlation_unit_codes[candidate]),
        ))
        select_target_multi_view_candidate_v2(candidate, fd, state, score=score)
        if rank + 1 in sizes:
            coverage = tuple((item.family_id, item.coverage_mass) for item in state.family_states)
            unsatisfied = tuple(sorted(item.obligation_id for index, item in enumerate(fd.obligations)
                                       if item.required and state.obligation_counts[index] < item.minimum_selected_frames))
            shell = entries[previous:rank + 1]
            rungs.append(TargetMultiViewSelectionRung(
                target_size=rank + 1, materializable=True,
                frame_uids=tuple(item.frame_uid for item in entries), family_coverage=coverage,
                hard_obligations_passed=not unsatisfied, unsatisfied_obligation_ids=unsatisfied,
                hard_coverage_qualified=not unsatisfied and all(value >= 0.95 - 1e-14 for _, value in coverage),
                phase_at_boundary="hard_coverage",
                shell_coverage_gain=float(np.sum([item.total_coverage_gain for item in shell], dtype=np.float64)),
                shell_representative_gain=float(np.sum([item.representative_gain for item in shell], dtype=np.float64)),
            ))
            previous = rank + 1
    replay_seconds = time.perf_counter() - replay_started
    identity = build_target_multi_view_selection_identity_v2(rd, fd, dataset_id=reference.dataset_id, selector_policy=policy.to_dict())
    checkpoint = checkpoint_target_multi_view_forward_state_v2(state, identity)
    with tempfile.TemporaryDirectory(prefix="mvstate2-production-", dir="/tmp") as temporary:
        started = time.perf_counter(); pointer = write_target_multi_view_selection_checkpoint_v2(checkpoint, Path(temporary) / "records"); write_seconds = time.perf_counter() - started
        checkpoint_root = Path(temporary); checkpoint_dir = checkpoint_root / Path(pointer["relative_path"]).parent
        checkpoint_bytes = sum(path.stat().st_size for path in checkpoint_dir.iterdir())
        started = time.perf_counter(); restored = read_target_multi_view_selection_checkpoint_v2(pointer, checkpoint_root); read_seconds = time.perf_counter() - started
        started = time.perf_counter(); restored_state = restore_target_multi_view_forward_state_v2(restored, rd, fd, expected_identity=identity); validate_seconds = time.perf_counter() - started
        assert restored_state.selected_order == state.selected_order
    selection_domain = TargetMultiViewSelectionDomainPlanV2(
        label_domain_id=args.domain, reference_domain_digest=rd.content_digest,
        mvidx1_domain_digest=fd.mvidx1_domain_digest, candidate_count=fd.candidate_count,
        master_order=tuple(entries), rungs=tuple(rungs), phase_a_completed_at=None,
    )
    selection = TargetMultiViewSelectionPlanV2(
        dataset_id=reference.dataset_id, target_coverage_reference_digest=reference.content_digest,
        mvidx1_content_digest=forward.mvidx1_content_digest, policy=policy, domains=(selection_domain,),
    )
    started = time.perf_counter()
    repair = build_target_multi_view_repair_plan_v2(
        reference, forward, selection,
        policy=TargetMultiViewRepairPolicyV2(max_passes_per_shell=2, max_swaps_per_shell=8),
    )
    repair_seconds = time.perf_counter() - started
    payload = {
        "schema": "mdstats.benchmark.mvstate2-repair2-production-prefix.v1",
        "input": {"candidate_count": fd.candidate_count, "family_count": len(fd.families), "forward_edge_count": sum(item.edge_count for item in fd.families), "rungs": sizes},
        "mvstate2": {"selected_count": state.selected_count, "prefix_replay_seconds": replay_seconds, "write_seconds": write_seconds, "read_seconds": read_seconds, "validation_seconds": validate_seconds, "checkpoint_bytes": checkpoint_bytes, "candidate_gain_arrays_persisted": False},
        "repair2": {"seconds": repair_seconds, "total_swaps": repair.domain(args.domain).total_swaps, "inverse_mutation": False, "rung_swap_counts": [len(item.swaps) for item in repair.domain(args.domain).rungs]},
        "gpu_used": False,
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
