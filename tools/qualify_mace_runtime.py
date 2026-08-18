#!/usr/bin/env python3
"""Create and qualify an offline MACE 0.3.16 runtime for MLFF-DATA9A."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mdstats.training_data import (
    MaceRuntimeInstallPolicy,
    create_mace_runtime_environment,
    discover_mace_dependency_artifacts,
    run_mace_cli_smoke,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True, type=Path)
    parser.add_argument("--mace-source", required=True, type=Path)
    parser.add_argument("--mace-archive", required=True, type=Path)
    parser.add_argument("--ase-archive", required=True, type=Path)
    parser.add_argument("--wheelhouse", type=Path)
    parser.add_argument("--build-tool", action="append", default=[], type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--recreate", action="store_true")
    parser.add_argument("--allow-index", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    dependencies = () if args.wheelhouse is None else discover_mace_dependency_artifacts(args.wheelhouse)
    record = create_mace_runtime_environment(
        args.environment,
        mace_source_root=args.mace_source,
        mace_archive=args.mace_archive,
        ase_archive=args.ase_archive,
        dependency_artifacts=dependencies,
        build_tool_artifacts=tuple(args.build_tool),
        policy=MaceRuntimeInstallPolicy(
            system_site_packages=True,
            inherit_base_python_paths=True,
            offline=not args.allow_index,
            force_recreate=args.recreate,
        ),
    )
    smoke = run_mace_cli_smoke(record)
    payload = {"environment": record.to_dict(), "cli_smoke": smoke.to_dict()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps({
        "qualified_for_cli_smoke": record.qualified_for_cli_smoke,
        "cli_smoke_passed": smoke.passed,
        "missing_requirements": list(record.missing_requirement_texts),
        "output": str(args.output.resolve()),
    }, indent=2, sort_keys=True))
    return 0 if smoke.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
