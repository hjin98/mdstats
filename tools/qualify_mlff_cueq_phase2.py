#!/usr/bin/env python3
"""Build CUEQ-PHASE2 selected-head source-execution qualification evidence.

This tool is evidence-only and never launches GPU work. FINAL-GPU1 supplies a
release-matched positive CUEQ-DEP1 runtime plus one or more development-corpus
path assessments produced by original-MH-1/e3nn versus derived-single-head/CuEq
execution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mdstats


def _read(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected JSON object: {path}")
    return payload


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _assess(args: argparse.Namespace) -> int:
    payload = _read(args.assessment)
    record = mdstats.CueqPhase2PathAssessment.from_dict(payload)
    _write(args.output, record.to_dict())
    return 0 if record.passed else 2


def _qualify(args: argparse.Namespace) -> int:
    runtime = mdstats.CueqDep1RuntimeRecord.from_dict(_read(args.runtime))
    assessments = tuple(mdstats.CueqPhase2PathAssessment.from_dict(_read(path)) for path in args.assessment)
    record = mdstats.build_cueq_phase2_qualification(runtime=runtime, assessments=assessments)
    _write(args.output, record.to_dict())
    return 0 if record.passed else 2


def _deferred(args: argparse.Namespace) -> int:
    runtime = mdstats.CueqDep1RuntimeRecord.from_dict(_read(args.runtime))
    record = mdstats.build_cueq_phase2_qualification(runtime=runtime)
    _write(args.output, record.to_dict())
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    assess = sub.add_parser("assess", help="validate/normalize one path-assessment JSON record")
    assess.add_argument("--assessment", type=Path, required=True)
    assess.add_argument("--output", type=Path, required=True)
    assess.set_defaults(func=_assess)

    qual = sub.add_parser("qualify", help="assemble final CUEQ-PHASE2 gate evidence")
    qual.add_argument("--runtime", type=Path, required=True)
    qual.add_argument("--assessment", type=Path, action="append", required=True)
    qual.add_argument("--output", type=Path, required=True)
    qual.set_defaults(func=_qualify)

    deferred = sub.add_parser("deferred", help="write the current fail-closed/deferred phase-2 state")
    deferred.add_argument("--runtime", type=Path, required=True)
    deferred.add_argument("--output", type=Path, required=True)
    deferred.set_defaults(func=_deferred)
    return p


def main() -> int:
    args = parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
