from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


_BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"
if str(_BENCHMARKS) not in sys.path:
    sys.path.insert(0, str(_BENCHMARKS))
_MODULE_PATH = _BENCHMARKS / "benchmark_mvqual_p1_product.py"
_SPEC = importlib.util.spec_from_file_location("benchmark_mvqual_p1_product", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_tolerant_proc_parser_keeps_numeric_status_rows(tmp_path: Path) -> None:
    status = tmp_path / "status"
    status.write_text(
        "Name:\tpython\n"
        "VmRSS:\t12345 kB\n"
        "VmSwap:\t0 kB\n"
        "Cpus_allowed:\tffff,ffff\n"
        "Threads:\t9\n",
        encoding="utf-8",
    )

    assert _MODULE._read_colon_ints_tolerant(status) == {
        "VmRSS": 12345,
        "VmSwap": 0,
        "Threads": 9,
    }


def test_tolerant_proc_parser_returns_none_for_missing_file(tmp_path: Path) -> None:
    assert _MODULE._read_colon_ints_tolerant(tmp_path / "missing") is None
