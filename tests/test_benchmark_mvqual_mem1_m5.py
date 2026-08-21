from __future__ import annotations

import importlib.util
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parents[1] / "benchmarks" / "benchmark_mvqual_mem1_m5.py"
_SPEC = importlib.util.spec_from_file_location("benchmark_mvqual_mem1_m5", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_completed_sizes_are_canonical_and_grouped() -> None:
    values = [
        {"selector": "mv", "target_size": 512},
        {"selector": "legacy", "target_size": 128},
        {"selector": "mv", "target_size": 128},
        {"selector": "mv", "target_size": 512},
    ]
    assert _MODULE._completed_sizes(values) == {
        "legacy": [128],
        "mv": [128, 512],
    }


def test_product_identity_requires_exact_product_envelope() -> None:
    class Args:
        expected_candidate_count = 36_408
        expected_family_count = 165
        expected_forward_edge_count = 9_505_021_522

    run = {
        "input": {
            "sparse_index": {
                "domains": [
                    {
                        "candidate_count": 36_408,
                        "family_count": 165,
                        "forward_edge_count": 9_505_021_522,
                    }
                ]
            }
        }
    }
    assert _MODULE._product_identity_matches(run, Args())
    run["input"]["sparse_index"]["domains"][0]["forward_edge_count"] -= 1
    assert not _MODULE._product_identity_matches(run, Args())


def test_dict_delta_handles_proc_and_swap_counters() -> None:
    assert _MODULE._dict_delta(
        {"read_bytes": 10, "write_bytes": 2},
        {"read_bytes": 14, "write_bytes": 9},
    ) == {"read_bytes": 4, "write_bytes": 7}
    assert _MODULE._dict_delta(None, {"read_bytes": 1}) is None
