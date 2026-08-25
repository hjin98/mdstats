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
    edge_pairs = {(edge["from"], edge["to"], edge["type"]) for edge in graph["edges"]}
    for screen in ("COARSE_SCREEN", "SHORT_SCREEN", "FINAL_SCREEN"):
        assert ("FULL_TRAIN2_SCHEDULE", screen, "identity_requires") in edge_pairs

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


def test_current_architecture_retains_independent_data_and_evaluation_invariants() -> None:
    text = MANUAL.read_text(encoding="utf-8")

    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    adjacency: dict[str, set[str]] = {}
    for edge in graph["edges"]:
        adjacency.setdefault(edge["from"], set()).add(edge["to"])

    def reaches(source: str, target: str) -> bool:
        pending = [source]
        seen: set[str] = set()
        while pending:
            current = pending.pop()
            if current == target:
                return True
            if current in seen:
                continue
            seen.add(current)
            pending.extend(adjacency.get(current, ()))
        return False

    # Revision 106 expresses canonical DATA-stage order as a semantic current
    # graph rather than retired numeric node/schema metadata.
    for source, target in (
        ("SOURCE_LABEL_EVIDENCE", "ELIGIBLE_CONDITIONED_FRAMES"),
        ("ELIGIBLE_CONDITIONED_FRAMES", "DATA7_FITTED_SELECTION_INPUTS"),
        ("DATA7_FITTED_SELECTION_INPUTS", "DOMAIN_REPAIRED_MASTER_ORDER"),
        ("DOMAIN_REPAIRED_MASTER_ORDER", "PREFIX_QUALIFICATION_EVIDENCE"),
        ("PREFIX_QUALIFICATION_EVIDENCE", "TARGET_SIZE_DECISION"),
        ("TARGET_SIZE_DECISION", "FROZEN_TRAINING_PROTOCOL"),
        ("FROZEN_TRAINING_PROTOCOL", "FINAL_COMMITTEE"),
    ):
        assert reaches(source, target), f"missing canonical current path {source} -> {target}"

    frame_section = text.split("### Source and frame facts", 1)[1].split(
        "### Decision, policy, fitted, and realization families", 1
    )[0].lower()
    assert (
        "does **not** own eligibility, statistical role, target membership, target size, "
        "training exposure, calibration, or acquisition state."
    ) in frame_section
    identity_section = text.split("## Geometry, label, and labeled-configuration identities", 1)[1].split(
        "## Electronic-structure label domains", 1
    )[0]
    for required_field in (
        "geometry_fingerprint",
        "label_payload_digest",
        "labeled_configuration_fingerprint",
    ):
        assert required_field in identity_section

    sealed = text.split("## Sealed evaluation and deployment", 1)[1].split(
        "## Calibration and uncertainty lineage", 1
    )[0]
    assert "ProtocolFreezeRecord" in text
    assert "development/training/checkpoint processes cannot inspect it" in sealed
    assert "Locked evidence cannot retroactively alter" in sealed

    checkpoint_policy = text.split("## Checkpoint metrics and constrained choice", 1)[1].split(
        "## MACE adapter and runtime lock", 1
    )[0]
    assert "checkpoint" in checkpoint_policy.lower()
    assert "fails closed" in checkpoint_policy


def test_current_architecture_publication_and_version_artifacts_exist() -> None:
    assert MANUAL_PDF.stat().st_size > 10_000
    assert SPEC_PDF.stat().st_size > 5_000
    assert f'version = "{mdstats.__version__}"' in PYPROJECT.read_text(encoding="utf-8")
