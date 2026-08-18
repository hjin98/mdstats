from __future__ import annotations

import json
from pathlib import Path

import mdstats
from mdstats.training_data import acceleration, campaign_cli

ROOT = Path(__file__).resolve().parents[1]


def test_diag3_historical_release_manual_graph_and_schema_are_preserved() -> None:
    assert mdstats.__version__ >= "0.20.218a0"
    assert acceleration.TRAINING_ACCELERATION_REPEATABILITY_DIAGNOSTIC_SCHEMA.endswith(".v2")
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    note = (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV85.md").read_text()
    spec = (ROOT / "docs/specs/training_data/mlff_cueq_train_repeatability_diagnostic_allpairs_spec.md").read_text()
    assert "Revision 85 historical gate: CUEQ-REPEAT1-DIAG3" in manual
    assert "45` e3nn-self" in note
    assert "100 cross-backend" in spec
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    nodes = {node["id"]: node for node in graph["nodes"]}
    gate = nodes["CUEQ_TRAIN2_REPEATABILITY_DIAGNOSTIC_ALLPAIRS"]
    assert gate["post_warmup_repeat_count"] == 10
    assert gate["cross_pair_count"] == 100
    assert gate["authorizing"] is False
