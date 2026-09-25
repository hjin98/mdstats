from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "run_mlff_cueq_c10_stage_c_preflight.py"
spec = importlib.util.spec_from_file_location("c10_preflight", MODULE_PATH)
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_canonical_json_digest_is_order_independent():
    a = {"b": 2, "a": [1, {"z": 3}]}
    b = {"a": [1, {"z": 3}], "b": 2}
    assert hashlib.sha256(m.canonical_json_bytes(a)).hexdigest() == hashlib.sha256(
        m.canonical_json_bytes(b)
    ).hexdigest()


def test_selected_gpu_apps_filters_to_selected_uuid():
    gpu = "NVIDIA GeForce RTX 3090, GPU-AAA, 555.1, 24576, 24000"
    apps = "100, python, 1024, GPU-BBB\n200, python, 2048, GPU-AAA"
    assert m._selected_gpu_apps(gpu, apps) == [
        {
            "pid": "200",
            "process_name": "python",
            "used_gpu_memory_mib": "2048",
            "gpu_uuid": "GPU-AAA",
        }
    ]


def test_source_relations_remain_accepted_parent_values():
    assert m.SOURCE_RELATIONS["cv_checkpoint_target_force_rmse_ev_per_angstrom"] == 0.045
    assert m.SOURCE_RELATIONS["cv_outer_target_force_rmse_ev_per_angstrom"] == 0.045
    assert m.SOURCE_RELATIONS["production_checkpoint_target_force_rmse_ev_per_angstrom"] == 0.030
    assert m.SOURCE_RELATIONS["replay_degradation_hard_budget_ev_per_angstrom"] == 0.030


def test_risk_binding_is_frozen_instance_choice():
    assert m.RISK_BINDING == {
        "eta_NI": 0.09,
        "q_cat": 0.09,
        "n_triplets": 300,
        "n_eval_triplets": 300,
        "simultaneous_confidence": 0.95,
        "per_statement_alpha": 0.0125,
    }
