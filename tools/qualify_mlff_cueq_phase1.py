#!/usr/bin/env python3
"""Build CUEQ-PHASE1 paired-training qualification evidence.

This tool is intentionally evidence-only.  It does not launch GPU training.
FINAL-GPU1 supplies the release-matched CUEQ-DEP1 runtime plus trajectory
records produced by the paired short/full e3nn-vs-pure-CuEq campaign.
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


def _pair(args: argparse.Namespace) -> int:
    policy = mdstats.CueqPhase1Policy(short_epoch_budget=args.short_epochs)
    reference = mdstats.CueqPhase1TrajectoryRecord.from_dict(_read(args.reference))
    candidate = mdstats.CueqPhase1TrajectoryRecord.from_dict(_read(args.candidate))
    pair = mdstats.CueqPhase1PairedAssessment(policy=policy, reference=reference, candidate=candidate)
    _write(args.output, pair.to_dict())
    return 0 if pair.passed else 2


def _qualify(args: argparse.Namespace) -> int:
    runtime = mdstats.CueqDep1RuntimeRecord.from_dict(_read(args.runtime))
    policy = mdstats.CueqPhase1Policy(short_epoch_budget=args.short_epochs)
    short = tuple(mdstats.CueqPhase1PairedAssessment.from_dict(_read(path)) for path in args.short_pair)
    full = tuple(mdstats.CueqPhase1PairedAssessment.from_dict(_read(path)) for path in args.full_pair)
    record = mdstats.build_cueq_phase1_qualification(
        runtime=runtime, short_pairs=short, full_pairs=full, policy=policy
    )
    _write(args.output, record.to_dict())
    return 0 if record.passed else 2


def _deferred(args: argparse.Namespace) -> int:
    runtime = mdstats.CueqDep1RuntimeRecord.from_dict(_read(args.runtime))
    record = mdstats.build_cueq_phase1_qualification(
        runtime=runtime,
        policy=mdstats.CueqPhase1Policy(short_epoch_budget=args.short_epochs),
    )
    _write(args.output, record.to_dict())
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    pair = sub.add_parser("pair", help="compare one e3nn/CuEq trajectory pair")
    pair.add_argument("--reference", type=Path, required=True)
    pair.add_argument("--candidate", type=Path, required=True)
    pair.add_argument("--short-epochs", type=int, default=8)
    pair.add_argument("--output", type=Path, required=True)
    pair.set_defaults(func=_pair)

    qual = sub.add_parser("qualify", help="assemble final short+full gate evidence")
    qual.add_argument("--runtime", type=Path, required=True)
    qual.add_argument("--short-pair", type=Path, action="append", default=[], required=True)
    qual.add_argument("--full-pair", type=Path, action="append", default=[], required=True)
    qual.add_argument("--short-epochs", type=int, default=8)
    qual.add_argument("--output", type=Path, required=True)
    qual.set_defaults(func=_qualify)

    deferred = sub.add_parser("deferred", help="write the current fail-closed/deferred gate state")
    deferred.add_argument("--runtime", type=Path, required=True)
    deferred.add_argument("--short-epochs", type=int, default=8)
    deferred.add_argument("--output", type=Path, required=True)
    deferred.set_defaults(func=_deferred)
    return p


def main() -> int:
    args = parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
