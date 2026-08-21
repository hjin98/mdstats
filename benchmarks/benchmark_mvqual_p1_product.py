#!/usr/bin/env python3
"""P1 product meter using the M5 contract with corrected Linux RSS parsing.

The M5 benchmark remains the authority for the product acceptance schema.  This
thin execution wrapper fixes only its Linux ``/proc`` integer parser so VmRSS
and VmSwap sampling survive unrelated nonnumeric status rows.  Child repeats
re-enter this wrapper, so both repetitions use the corrected sampler.
"""

from __future__ import annotations

from pathlib import Path

import benchmark_mvqual_mem1_m5 as _m5


def _read_colon_ints_tolerant(path: Path) -> dict[str, int] | None:
    """Parse integer-leading ``key: value`` rows and ignore all other rows."""

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


def main() -> int:
    _m5._read_colon_ints = _read_colon_ints_tolerant
    args = _m5._parser().parse_args()
    if int(args.repeats) < 2 and args._single_run_output is None:
        raise SystemExit("P1 product qualification requires at least two repetitions")
    if float(args.timeout_seconds) <= 0.0:
        raise SystemExit("--timeout-seconds must be positive")
    if int(args.sparse_max_edges) < 1:
        raise SystemExit("--sparse-max-edges must be positive")
    if args._single_run_output is not None:
        return _m5._single_run(args)

    # M5's aggregate launcher intentionally re-executes its own __file__. Point
    # that execution-only locator at this wrapper so child runs retain the RSS
    # parser fix without copying the M5 benchmark implementation.
    original_file = _m5.__file__
    _m5.__file__ = __file__
    try:
        return _m5._aggregate(args)
    finally:
        _m5.__file__ = original_file


if __name__ == "__main__":
    raise SystemExit(main())
