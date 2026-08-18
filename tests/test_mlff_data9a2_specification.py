from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/training_data/mlff_data9a2_real_mace_realization_spec.md"
ARCH = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"


def test_data9a2_specification_and_release_version() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for required in (
        "MaceConfigRealizationRecord",
        "MaceJobExecutionSmokeRecord",
        "atomic_numbers",
        "heads.<name>.E0s",
        "config_weight",
        "weight_pt",
        "mace_run_train --dry_run",
        "target-head extraction",
        "finite energy, force, and stress",
    ):
        assert required in text
    assert 'version = "0.20.140a0"' in (ROOT / "pyproject.toml").read_text()
    assert "DATA9A2 real-MACE realization is implemented in `0.20.39a0`" in ARCH.read_text()


def test_data9a2_dependency_graph_nodes_and_gate_edges() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    nodes = {node["id"] for node in graph["nodes"]}
    edges = {(edge["from"], edge["to"], edge["type"]) for edge in graph["edges"]}
    assert "MACE_CONFIG_REALIZATION_RECORD" in nodes
    assert "MACE_JOB_EXECUTION_SMOKE_RECORD" in nodes
    assert (
        "MACE_CONFIG_REALIZATION_RECORD",
        "MACE_JOB_EXECUTION_SMOKE_RECORD",
        "execution_requires",
    ) in edges
    assert (
        "MACE_JOB_EXECUTION_SMOKE_RECORD",
        "DATA9A_GATE",
        "requires",
    ) in edges
