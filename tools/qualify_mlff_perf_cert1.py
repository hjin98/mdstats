#!/usr/bin/env python3
"""Assemble, validate, or emit a deferred PERF-CERT1 qualification record.

The tool never launches GPU work.  FINAL-GPU1 owns positive accelerator
execution; this command only consumes content-addressed gate/profile evidence
and applies the PERF-CERT1 release authority.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mdstats


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _upstream(phase1_path: Path, phase2_path: Path):
    phase1 = mdstats.CueqPhase1QualificationRecord.from_dict(_load(phase1_path))
    phase2 = mdstats.CueqPhase2QualificationRecord.from_dict(_load(phase2_path))
    return phase1, phase2


def _build(args: argparse.Namespace, *, include_profiles: bool) -> mdstats.PerfCert1QualificationRecord:
    phase1, phase2 = _upstream(args.phase1, args.phase2)
    baseline = None
    candidates = ()
    if include_profiles:
        baseline = mdstats.PerfCert1ProfileRecord.from_dict(_load(args.baseline))
        candidates = tuple(mdstats.PerfCert1ProfileRecord.from_dict(_load(path)) for path in args.candidate)
    return mdstats.build_perf_cert1_qualification(
        phase1=phase1,
        phase2=phase2,
        baseline=baseline,
        candidates=candidates,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    deferred = sub.add_parser("deferred", help="Emit a fail-closed deferred record without profile evidence.")
    deferred.add_argument("--phase1", type=Path, required=True)
    deferred.add_argument("--phase2", type=Path, required=True)
    deferred.add_argument("--output", type=Path, required=True)

    assemble = sub.add_parser("assemble", help="Assemble PERF-CERT1 from final profile evidence.")
    assemble.add_argument("--phase1", type=Path, required=True)
    assemble.add_argument("--phase2", type=Path, required=True)
    assemble.add_argument("--baseline", type=Path, required=True)
    assemble.add_argument("--candidate", type=Path, action="append", required=True)
    assemble.add_argument("--output", type=Path, required=True)

    validate = sub.add_parser("validate", help="Validate an existing PERF-CERT1 qualification record.")
    validate.add_argument("--input", type=Path, required=True)
    validate.add_argument("--output", type=Path)

    args = parser.parse_args()
    if args.command == "validate":
        record = mdstats.PerfCert1QualificationRecord.from_dict(_load(args.input))
        payload = record.to_dict()
        if args.output is not None:
            _write(args.output, payload)
    elif args.command == "deferred":
        record = _build(args, include_profiles=False)
        payload = record.to_dict()
        _write(args.output, payload)
    else:
        record = _build(args, include_profiles=True)
        payload = record.to_dict()
        _write(args.output, payload)

    print(json.dumps(payload, indent=2, sort_keys=True))
    # Deferred records are valid evidence and therefore not a CLI error.  A
    # final assembled certification returns 2 when it fails its gate.
    if args.command == "assemble" and not record.passed:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
