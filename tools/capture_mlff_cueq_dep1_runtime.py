#!/usr/bin/env python3
"""Capture the CUEQ-DEP1 accelerator runtime record without backend fallback."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mdstats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--supplied-artifact", action="append", default=[], type=Path)
    parser.add_argument("--require-oeq", action="store_true")
    args = parser.parse_args()
    record = mdstats.capture_cueq_dep1_runtime(
        policy=mdstats.CueqDep1Policy(require_oeq=bool(args.require_oeq)),
        supplied_artifacts=tuple(args.supplied_artifact),
    )
    mdstats.write_cueq_dep1_runtime(args.output, record)
    print(f"CUEQ-DEP1 passed={record.passed} digest={record.content_digest}")
    if record.blocking_reasons:
        print("blocking_reasons=" + ",".join(record.blocking_reasons))
    return 0 if record.passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
