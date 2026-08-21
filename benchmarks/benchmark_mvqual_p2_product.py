#!/usr/bin/env python3
"""P2 product meter layered on the accepted M5 qualification contract."""
from __future__ import annotations

import json
from pathlib import Path

import benchmark_mvqual_mem1_m5 as _m5
from mdstats.training_data import mvqual_p2_runtime as _p2


def _read_colon_ints_tolerant(path: Path) -> dict[str, int] | None:
    try:
        result: dict[str, int] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if ":" not in line:
                continue
            key, raw = line.split(":", 1)
            parts = raw.strip().split()
            if not parts:
                continue
            try:
                value = int(parts[0])
            except ValueError:
                continue
            result[key.strip()] = value
        return result
    except OSError:
        return None


def _attach_p2_telemetry(path: Path) -> None:
    telemetry = _p2.last_mvqual_p2_execution_telemetry()
    if telemetry is None or not path.is_file():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["p2_execution"] = telemetry.to_dict()
    _m5._atomic_write_json(path, payload)


def main() -> int:
    _m5._read_colon_ints = _read_colon_ints_tolerant
    original_single_run = _m5._single_run

    def single_run_with_p2(args):
        result = original_single_run(args)
        if result == 0 and args._single_run_output is not None:
            _attach_p2_telemetry(Path(args._single_run_output))
        return result

    _m5._single_run = single_run_with_p2
    args = _m5._parser().parse_args()
    if int(args.repeats) < 2 and args._single_run_output is None:
        raise SystemExit("P2 product qualification requires at least two repetitions")
    if float(args.timeout_seconds) <= 0.0:
        raise SystemExit("--timeout-seconds must be positive")
    if int(args.sparse_max_edges) < 1:
        raise SystemExit("--sparse-max-edges must be positive")
    if args._single_run_output is not None:
        return _m5._single_run(args)

    # M5 re-executes its own file for each bounded child. Point that execution
    # locator at this wrapper so both child runs retain P2 telemetry and the RSS
    # parser fix without copying the M5 implementation.
    original_file = _m5.__file__
    _m5.__file__ = __file__
    try:
        return _m5._aggregate(args)
    finally:
        _m5.__file__ = original_file


if __name__ == "__main__":
    raise SystemExit(main())
