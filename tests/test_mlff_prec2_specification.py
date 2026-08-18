from __future__ import annotations

import json
from pathlib import Path


def test_prec2_architecture_and_specification_are_closed() -> None:
    root = Path(__file__).resolve().parents[1]
    manual = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text(encoding="utf-8")
    spec = (root / "docs/specs/training_data/mlff_staged_precision_profiles_spec.md").read_text(encoding="utf-8")
    graph = json.loads((root / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text(encoding="utf-8"))
    assert "PREC2 - in-process staged precision execution and restart correctness - implemented in 0.20.109a0" in manual
    assert "PREC2 - in-process transition and exact restart - implemented in 0.20.109a0" in spec
    assert "latest-only authenticated companion" in manual
    assert "real MACE 0.3.16" in manual
    assert "no fabricated real-CuEq execution evidence is claimed" in manual
    assert "The post-0.20.105 evaluation, precision, and storage implementation roadmap is complete." in manual
    assert graph["schema_version"] == 26
    assert graph["architecture_revision"] == 34
    node_ids = {node["id"] for node in graph["nodes"]}
    assert "PRECISION_RUNTIME_COMPANION" in node_ids
