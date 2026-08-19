#!/usr/bin/env python3
"""Fresh-process deterministic-control worker for TRAIN2 repeatability diagnostics."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import traceback


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--structures", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--dtype", required=True)
    parser.add_argument("--repeat-count", required=True, type=int)
    parser.add_argument("--force-threshold", required=True, type=float)
    return parser


def _write(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = _parser().parse_args()
    output = Path(args.output)
    try:
        # CUBLAS_WORKSPACE_CONFIG is injected by the parent before this process starts.
        import torch

        torch.use_deterministic_algorithms(True)
        torch.set_deterministic_debug_mode("error")
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True

        from ase.io import read
        from mdstats.training_data.acceleration import (
            MaceAccelerationParityPolicy,
            diagnose_training_acceleration_repeatability,
        )

        structures = read(args.structures, index=":", format="extxyz")
        policy_payload = json.loads(Path(args.policy).read_text(encoding="utf-8"))
        policy = MaceAccelerationParityPolicy.from_dict(policy_payload)
        record = diagnose_training_acceleration_repeatability(
            training_model_path=args.model,
            training_head=args.head,
            structures=structures,
            device=args.device,
            dtype=args.dtype,
            parity_policy=policy,
            repeat_count=args.repeat_count,
            force_threshold=args.force_threshold,
        )
        _write(output, {
            "status": "completed",
            "repeatability": record.to_dict(),
            "deterministic_runtime": {
                "torch_deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
                "torch_deterministic_debug_mode": int(torch.get_deterministic_debug_mode()),
                "cudnn_deterministic": bool(torch.backends.cudnn.deterministic),
                "cudnn_benchmark": bool(torch.backends.cudnn.benchmark),
                "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
            },
        })
        return 0
    except Exception as exc:
        _write(output, {
            "status": "unsupported_or_failed",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback_tail": traceback.format_exc()[-4000:],
            "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        })
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
