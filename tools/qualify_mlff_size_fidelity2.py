#!/usr/bin/env python3
"""Assemble and validate the FINAL-GPU1 SIZE-FIDELITY2 qualification record."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mdstats


def _read(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-plan", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, action="append", required=True,
                        help="One SIZE-FIDELITY2 checkpoint JSON; repeat for the complete matrix.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    plan = mdstats.SizeFidelity2ExecutionPlan.from_dict(_read(args.execution_plan))
    checkpoints = tuple(mdstats.SizeFidelity2Checkpoint.from_dict(_read(path)) for path in args.checkpoint)
    report = mdstats.build_size_fidelity2_qualification(
        plan, checkpoints, gpu_qualification_status="passed"
    )
    mdstats.validate_size_fidelity2_qualification(report, execution_plan=plan)
    _write(args.output, report.to_dict())
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
