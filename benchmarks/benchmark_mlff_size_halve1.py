#!/usr/bin/env python3
"""CPU-testable SIZE-HALVE1 work-exposure and policy-coverage analysis.

This is deliberately not a MACE/GPU performance benchmark. It enumerates the
exact 3/10/30 structure-epoch exposure envelope implied by the current policy
and records the execution limitations that must be closed by SIZE-FIDELITY1
and PERF-P2R.
"""
from __future__ import annotations

import argparse
from itertools import combinations
import json
import os
from pathlib import Path
import platform
import time
from typing import Any

import mdstats
from mdstats.training_data._common import canonical_json, digest

SCHEMA = "mdstats.mlff-size-halve1-exposure-analysis.v1"
DEFAULT_SIZES = (128, 256, 512, 1024, 2048, 4096, 8192)


def _host() -> dict[str, Any]:
    cpu = "unknown"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    def read(path: str) -> str | None:
        try:
            return Path(path).read_text().strip()
        except OSError:
            return None
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu_model": cpu,
        "logical_cpus": os.cpu_count(),
        "cgroup_cpu_max": read("/sys/fs/cgroup/cpu.max"),
        "cgroup_memory_max": read("/sys/fs/cgroup/memory.max"),
    }


def _exposure(a: tuple[int, ...], s4: tuple[int, ...], s2: tuple[int, ...]) -> int:
    return 3 * sum(a) + 7 * sum(s4) + 20 * sum(s2)


def _envelope(a: tuple[int, ...]) -> dict[str, Any]:
    keep4 = min(4, len(a))
    candidates: list[tuple[int, tuple[int, ...], tuple[int, ...]]] = []
    for s4 in combinations(a, keep4):
        for s2 in combinations(s4, 2):
            candidates.append((_exposure(a, s4, s2), s4, s2))
    best = min(candidates, key=lambda item: item[0])
    worst = max(candidates, key=lambda item: item[0])
    full = 30 * sum(a)
    def pack(item: tuple[int, tuple[int, ...], tuple[int, ...]]) -> dict[str, Any]:
        work, s4, s2 = item
        return {
            "structure_epoch_exposure": work,
            "reduction_percent_vs_all_to_30": 100.0 * (1.0 - work / full),
            "epoch3_survivors": list(s4),
            "epoch10_finalists": list(s2),
        }
    return {
        "coverage_qualified_sizes": list(a),
        "qualifier_count": len(a),
        "all_to_30_structure_epoch_exposure": full,
        "best_case": pack(best),
        "worst_case": pack(worst),
    }


def _render(payload: dict[str, Any]) -> str:
    p = payload["policy"]
    lines = [
        "---",
        'title: "MLFF SIZE-HALVE1 Work-Exposure and Optimization-Coverage Analysis"',
        'subtitle: "CPU-testable planning evidence for the corrected 3/10/30 target-size funnel"',
        'author: "mdstats project"',
        f'date: "{payload["created_at_utc"][:10]}"',
        "geometry: margin=0.8in",
        "toc: true",
        "toc-depth: 2",
        "numbersections: true",
        "fontsize: 10pt",
        "---",
        "",
        "# Scope",
        "",
        "This report evaluates the corrected target-size funnel without claiming MACE/GPU training performance. Coverage is hard admission only; all qualified sizes enter the 3-epoch screen. The exposure model is exact for structure-epoch counts under the frozen 3/10/30 policy, but it is not a wall-time model.",
        "",
        "# Frozen funnel",
        "",
        "$$",
        "N_{\\mathrm{eligible}} \\xrightarrow{3\\ \\mathrm{epochs}} \\le 4 \\xrightarrow{10\\ \\mathrm{epochs}} 2 \\xrightarrow{30\\ \\mathrm{epochs}} 1.",
        "$$",
        "",
        f"Policy digest: `{payload['policy_digest']}`.",
        "",
        "The target structure-epoch exposure proxy is",
        "",
        "$$",
        "W = 3\\sum_{i\\in A}K_i + 7\\sum_{i\\in S_4}K_i + 20\\sum_{i\\in S_2}K_i,",
        "$$",
        "",
        "relative to",
        "",
        "$$",
        "W_{\\mathrm{full}} = 30\\sum_{i\\in A}K_i.",
        "$$",
        "",
        "# Exposure envelope",
        "",
        "The table enumerates monotone suffixes of the default nested ladder, from the minimum three qualifiers through all seven. `Best` means the smallest permitted survivors continue; `worst` means the largest permitted survivors continue.",
        "",
        "| Qualifiers | Eligible sizes | Best reduction | Worst reduction |",
        "|---:|---|---:|---:|",
    ]
    for row in payload["exposure_envelopes"]:
        sizes = ", ".join(map(str, row["coverage_qualified_sizes"]))
        lines.append(
            f"| {row['qualifier_count']} | {sizes} | {row['best_case']['reduction_percent_vs_all_to_30']:.2f}% | {row['worst_case']['reduction_percent_vs_all_to_30']:.2f}% |"
        )
    seven = payload["exposure_envelopes"][-1]
    lines += [
        "",
        "With all seven default sizes admitted, the exposure reduction is bounded between "
        f"**{seven['worst_case']['reduction_percent_vs_all_to_30']:.2f}%** and "
        f"**{seven['best_case']['reduction_percent_vs_all_to_30']:.2f}%**, depending on which sizes survive. This wide range is why PERF-P2R must benchmark both unfavorable large-size-survivor and favorable small-size-survivor cases rather than report one convenient path.",
        "",
        "# Required qualification additions",
        "",
        "1. **SIZE-FIDELITY1 before performance promotion.** Exhaustively continue all hard-coverage qualifiers to 30 epochs for multiple screening seeds; retrospectively test epoch-3 top-four and epoch-10 top-two recall of the eventual 30-epoch winner/finalists.",
        "2. **Coarse-monitor calibration.** Compare the fixed coarse role against the full development role at epoch 3 and choose the smallest monitor that preserves promotion decisions up to practical equivalence. The current 256-frame setting is provisional.",
        "3. **Early-equivalence calibration.** Calibrate the coarse practical-equivalence width from real trajectory/seed variability. A tied largest boundary is preserved within its band so bounded-ladder nonconvergence remains observable.",
        "4. **Sampler-aware continuation.** Exact 3->10->30 continuation must include DataLoader/sampler/worker ordering state or prove deterministic epoch-boundary reconstruction, in addition to model, optimizer/scheduler, and global RNG state.",
        "5. **Worst-case performance matrix.** PERF-P2R must cover 3, 4, 5, 6, and 7 admitted sizes and both small-survivor and large-survivor extremes, plus single- and multi-GPU resource regimes where available.",
        "6. **Fuse execution, not authority.** Boundary evaluation may run in the same process as training to avoid checkpoint reload only when it emits the same separate EVAL2 scientific evidence. Shared graph/preprocessing caches and nested prefix manifests must remain byte/array equivalent.",
        "7. **Checkpoint-I/O control.** Full restart authority is mandatory at epochs 3, 10, and 30. Additional recovery checkpoints may use a bounded execution-only cadence and may be reclaimed after immutable elimination evidence is frozen.",
        "",
        "# Environment and limitation",
        "",
        f"This analysis ran under `{payload['host']['cpu_model']}` with cgroup CPU limit `{payload['host']['cgroup_cpu_max']}` and memory limit `{payload['host']['cgroup_memory_max']}`. No authorizing MACE runtime/checkpoint or GPU was available. Therefore no epoch-3/10/30 wall-time, GPU-utilization, VRAM, or survivor-fidelity claim is made here.",
        "",
        "# References",
        "",
        "The staged budget-allocation pattern is related to successive-halving and Hyperband, but mdstats keeps its own deterministic scientific metrics, hard coverage gate, exact continuation, and provenance contract.",
        "",
        "1. Kevin Jamieson and Ameet Talwalkar, *Non-stochastic Best Arm Identification and Hyperparameter Optimization*, PMLR 51, 2016. [PMLR article](https://proceedings.mlr.press/v51/jamieson16.html).",
        "2. Lisha Li, Kevin Jamieson, Giulia DeSalvo, Afshin Rostamizadeh, and Ameet Talwalkar, *Hyperband: A Novel Bandit-Based Approach to Hyperparameter Optimization*, JMLR 18(185), 2018. [JMLR article](https://www.jmlr.org/papers/v18/16-558.html).",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    policy = mdstats.TargetSizeConvergencePolicy()
    envelopes = [_envelope(DEFAULT_SIZES[-n:]) for n in range(3, 8)]
    policy_payload = policy.to_dict() if hasattr(policy, "to_dict") else {
        "min_coverage_qualifiers": policy.min_coverage_qualifiers,
        "coarse_training_epochs": policy.coarse_training_epochs,
        "max_coarse_training_candidates": policy.max_coarse_training_candidates,
        "coarse_target_monitor_configurations": policy.coarse_target_monitor_configurations,
        "short_training_epochs": policy.short_training_epochs,
        "max_short_training_candidates": policy.max_short_training_candidates,
        "final_training_epochs": policy.final_training_epochs,
        "coarse_practical_equivalence_mev_per_a": policy.coarse_practical_equivalence_mev_per_a,
        "practical_equivalence_mev_per_a": policy.practical_equivalence_mev_per_a,
        "screening_optimizer_seed": policy.screening_optimizer_seed,
    }
    payload = {
        "schema": SCHEMA,
        "source_version": mdstats.__version__,
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": _host(),
        "default_target_sizes": list(DEFAULT_SIZES),
        "policy": policy_payload,
        "policy_digest": digest(policy_payload),
        "exposure_envelopes": envelopes,
        "authorizing_mace_runtime_available": False,
        "claims": {
            "structure_epoch_exposure": "exact_for_frozen_funnel",
            "wall_time": "not_claimed",
            "gpu_performance": "not_claimed",
            "coarse_screen_fidelity": "pending_SIZE-FIDELITY1",
        },
    }
    payload["content_digest"] = digest({k: v for k, v in payload.items() if k != "created_at_utc"})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    args.report.write_text(_render(payload), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "report": str(args.report), "content_digest": payload["content_digest"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
