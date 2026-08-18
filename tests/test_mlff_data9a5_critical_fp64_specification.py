from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/training_data/mlff_data9a5_critical_fp64_spec.md"
ARCH = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"


def test_data9a5_spec_and_version_are_present() -> None:
    text = SPEC.read_text()
    assert 'version: "0.20.42a0"' in text
    assert "training_force_jacobian_dtype = model" in text
    assert "Python/ASE" in text
    assert 'version = "0.20.140a0"' in (ROOT / "pyproject.toml").read_text()


def test_data9a5_architecture_declares_scope_and_limits() -> None:
    text = ARCH.read_text()
    assert "MLFF-DATA9A5a critical-FP64 execution" in text
    assert "does not audit or reproduce LAMMPS" in text
    assert "second-derivative graph" in text


def test_dependency_graph_binds_critical_precision_gate() -> None:
    graph = json.loads(GRAPH.read_text())
    nodes = {node["id"] for node in graph["nodes"]}
    assert {
        "MACE_CRITICAL_PRECISION_POLICY",
        "MACE_CRITICAL_PRECISION_AUDIT",
        "ASE_MD_STATE_PRECISION_AUDIT",
        "PYTHON_ASE_MACE_EXECUTION",
    } <= nodes
    edges = {(edge["from"], edge["to"], edge["type"]) for edge in graph["edges"]}
    assert (
        "MACE_CRITICAL_PRECISION_AUDIT",
        "DATA9A_GATE",
        "promotion_requires",
    ) in edges
