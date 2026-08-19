"""One-shot isolated worker for per-run MLFF feature tasks."""
from __future__ import annotations

import argparse
import importlib
import os
from pathlib import Path
import pickle
import sys
import traceback


def _contain_native_threads() -> None:
    for key in (
        "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
    ):
        os.environ[key] = "1"
    try:
        from threadpoolctl import threadpool_limits
    except ModuleNotFoundError:
        return
    limiter = threadpool_limits(limits=1)
    limiter.__enter__()
    globals()["_THREADPOOL_LIMITER"] = limiter


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one isolated mdstats feature task.")
    parser.add_argument("--module", required=True)
    parser.add_argument("--function", required=True)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    _contain_native_threads()
    try:
        from ._array_pickle import load_with_array_references
        with args.input.open("rb") as handle:
            task = load_with_array_references(handle)
        function = getattr(importlib.import_module(args.module), args.function)
        result = function(task)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        with temporary.open("wb") as handle:
            pickle.dump(result, handle, protocol=5)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, args.output)
        return 0
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
