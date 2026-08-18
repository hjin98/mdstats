from __future__ import annotations

import json
from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]


def test_repeatability_diag2_historical_release_manual_and_graph_are_preserved() -> None:
    assert mdstats.__version__ >= "0.20.217a0"
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    note = (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV84.md").read_text()
    spec = (ROOT / "docs/specs/training_data/mlff_cueq_train_repeatability_diagnostic_refinement_spec.md").read_text()
    assert "Revision 84 historical gate: CUEQ-REPEAT1-DIAG2" in manual
    assert "isolated deterministic-control subprocess" in manual
    assert "mdstats 0.20.217a0" in note
    assert "non-authorizing" in spec
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    nodes = {node["id"]: node for node in graph["nodes"]}
    gate = nodes["CUEQ_TRAIN2_REPEATABILITY_DIAGNOSTIC_REFINEMENT"]
    assert gate["repeat_count"] == 10
    assert gate["authorizing"] is False
    assert gate["deterministic_subprocess"] is True
