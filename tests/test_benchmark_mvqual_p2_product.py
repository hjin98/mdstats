from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


_MODULE_PATH = Path(__file__).resolve().parents[1] / "benchmarks" / "benchmark_mvqual_p2_product.py"
_SPEC = importlib.util.spec_from_file_location("benchmark_mvqual_p2_product", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_p2_meter_status_parser_ignores_nonnumeric_rows(tmp_path: Path) -> None:
    path = tmp_path / "status"
    path.write_text(
        "Name:\tpython\nVmRSS:\t12345 kB\nVmSwap:\t0 kB\nvoluntary_ctxt_switches:\t88\n",
        encoding="utf-8",
    )
    assert _MODULE._read_colon_ints_tolerant(path) == {
        "VmRSS": 12345,
        "VmSwap": 0,
        "voluntary_ctxt_switches": 88,
    }


def test_p2_meter_attaches_execution_telemetry(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "run.json"
    path.write_text(json.dumps({"schema": "test"}), encoding="utf-8")
    telemetry = SimpleNamespace(to_dict=lambda: {"wall_seconds": 12.5, "report_count": 15})
    monkeypatch.setattr(
        _MODULE._p2,
        "last_mvqual_p2_execution_telemetry",
        lambda: telemetry,
    )

    _MODULE._attach_p2_telemetry(path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["p2_execution"] == {"wall_seconds": 12.5, "report_count": 15}
