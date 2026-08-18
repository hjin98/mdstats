from __future__ import annotations

import json
from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]


def test_hf2_historical_release_manual_and_graph_are_preserved() -> None:
    assert "mdstats 0.20.215a0" in (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV82.md").read_text()
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (ROOT / "docs/specs/training_data/mlff_cueq_train_default1_fp32_ceiling_hotfix_spec.md").read_text()
    assert "Revision 82 historical gate: CUEQ-DEFAULT1-HF2" in manual
    assert "Fmax=8.911e-6" in manual
    assert "atol = 1e-5" in spec
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    nodes = {node["id"]: node for node in graph["nodes"]}
    gate = nodes["CUEQ_DEFAULT1_HF2_TRAIN2_FP32_PARITY_CEILING"]
    assert gate["training_float32_atol"] == 1.0e-5
    assert gate["source_float32_atol"] == 1.0e-6
    assert gate["adaptive_tolerance_widening_allowed"] is False
