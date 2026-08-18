#!/usr/bin/env python3
"""Build FINAL-GPU1 legacy-vs-MV TARGET-DATA2C learning-control evidence."""
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    row = sub.add_parser("row", help="Create one paired same-N/same-seed learning-control row.")
    row.add_argument("--target-size", type=int, required=True)
    row.add_argument("--optimizer-seed", type=int, required=True)
    row.add_argument("--legacy-score-mev-per-a", type=float, required=True)
    row.add_argument("--mv-score-mev-per-a", type=float, required=True)
    row.add_argument("--equivalence-mev-per-a", type=float, required=True)
    row.add_argument("--common-training-protocol-digest", required=True)
    row.add_argument("--legacy-evaluation-digest", required=True)
    row.add_argument("--mv-evaluation-digest", required=True)
    row.add_argument("--output", type=Path, required=True)

    assemble = sub.add_parser("assemble", help="Assemble the authoritative FINAL-GPU1 learning-control report.")
    assemble.add_argument("--qualification", type=Path, required=True,
                          help="Frozen TARGET-DATA2C-MVQUAL1 qualification JSON.")
    assemble.add_argument("--row", type=Path, action="append", required=True)
    assemble.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "row":
        record = mdstats.TargetMultiViewLearningControlRow(
            target_size=args.target_size,
            optimizer_seed=args.optimizer_seed,
            legacy_target_force_score_mev_per_a=args.legacy_score_mev_per_a,
            mv_target_force_score_mev_per_a=args.mv_score_mev_per_a,
            practical_equivalence_mev_per_a=args.equivalence_mev_per_a,
            common_training_protocol_digest=args.common_training_protocol_digest,
            legacy_evaluation_digest=args.legacy_evaluation_digest,
            mv_evaluation_digest=args.mv_evaluation_digest,
        )
        _write(args.output, record.to_dict())
        print(json.dumps(record.to_dict(), indent=2, sort_keys=True))
        return 0 if record.passed else 3

    qualification = mdstats.TargetMultiViewQualificationPlan.from_dict(_read(args.qualification))
    rows = tuple(mdstats.TargetMultiViewLearningControlRow.from_dict(_read(path)) for path in args.row)
    report = mdstats.TargetMultiViewLearningControlReport(
        dataset_id=qualification.dataset_id,
        target_multi_view_qualification_digest=qualification.content_digest,
        control_target_sizes=qualification.learning_control_target_sizes,
        rows=rows,
        gpu_qualification_status="passed",
    )
    _write(args.output, report.to_dict())
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
