from __future__ import annotations

import json
from pathlib import Path

import mdstats


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
MANUAL_PDF = ROOT / "docs/arch_manuals/mlff_training_data_architecture.pdf"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
SPEC = ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.md"
SPEC_PDF = ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.pdf"
PYPROJECT = ROOT / "pyproject.toml"


def test_current_architecture_manual_describes_revision_106_authorities() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "architecture_revision: 106" in text
    for token in (
        "MVSEL2 target order",
        "REPAIR2 repaired master order",
        "MVQUAL prefix qualification",
        "configurable target-size study",
        "0 -> n1 coarse -> n2 short -> n3 final screen",
        "independent frozen TRAIN2 schedule horizon",
        "reconstructible execution cache",
    ):
        assert token in text
    assert "SIZE_STUDY_EPOCH3" not in text


def test_current_cross_cutting_spec_separates_compatibility_and_execution_identity() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "Cross-cutting current-generation invariants",
        "Execution caches, worker scheduling, out-of-core layout",
        "immediately preceding fixed-fidelity generation",
        "current-generation identities",
        "fail closed",
    ):
        assert token in text
    assert "No public runtime object is implemented at MLFF-DATA0" not in text


def test_current_dependency_graph_is_semantic_and_acyclic() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["authority_model"] == "single_generation_current_dependency_architecture"
    assert graph["schema_version"] == 2
    node_ids = {node["id"] for node in graph["nodes"]}
    assert {"COARSE_SCREEN", "SHORT_SCREEN", "FINAL_SCREEN", "FULL_TRAIN2_SCHEDULE"} <= node_ids
    assert not any(node.startswith("SIZE_STUDY_EPOCH") for node in node_ids)

    adjacency = {node_id: set() for node_id in node_ids}
    for edge in graph["edges"]:
        assert edge["from"] in node_ids
        assert edge["to"] in node_ids
        adjacency[edge["from"]].add(edge["to"])

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visited:
            return
        assert node_id not in visiting, f"cycle detected at {node_id}"
        visiting.add(node_id)
        for child in adjacency[node_id]:
            visit(child)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in sorted(node_ids):
        visit(node_id)


def test_current_architecture_publication_and_version_artifacts_exist() -> None:
    assert MANUAL_PDF.stat().st_size > 10_000
    assert SPEC_PDF.stat().st_size > 5_000
    assert f'version = "{mdstats.__version__}"' in PYPROJECT.read_text(encoding="utf-8")
