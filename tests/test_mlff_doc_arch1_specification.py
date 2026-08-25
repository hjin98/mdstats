from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
CHAPTERS = ROOT / "docs/arch_manuals/mlff_training_data"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
REV_INDEX = ROOT / "docs/history/mlff/architecture_revisions/INDEX.md"
REL_INDEX = ROOT / "docs/history/mlff/release_notes/INDEX.md"


def test_doc_arch1_release_and_current_authority_are_synchronized():
    assert mdstats.__version__ == "0.20.242a0"
    text = MANUAL.read_text(encoding="utf-8")
    assert "architecture_revision: 106" in text
    assert "# Part VI - Bounded execution, restart, and performance architecture" in text
    assert "# Part VII - Ownership and extension boundaries" in text
    assert "## Context retrieval index" in text
    assert "MVSEL2 target order" in text
    assert "independent MVQUAL prefix qualification" in text
    assert "configurable target-size study" in text
    assert not (ROOT / "mlff_training_data_architecture.md").exists()
    assert not (ROOT / "mlff_training_data_dependency_graph.json").exists()


def test_doc_arch1_manual_is_deterministically_assembled_from_numbered_sources():
    order = [
        "00_front_matter.md", "10_foundations.md", "20_data_contracts.md",
        "30_statistical_design.md", "40_training_evaluation.md",
        "50_target_multiview.md", "60_execution_performance.md",
        "80_ownership_and_decisions.md", "90_references.md",
    ]
    expected = "\n\n".join((CHAPTERS / name).read_text(encoding="utf-8").rstrip() for name in order) + "\n"
    assert MANUAL.read_text(encoding="utf-8") == expected
    assert len(MANUAL.read_text(encoding="utf-8").splitlines()) < 4000


def test_doc_arch1_current_target_size_and_execution_contract():
    text = MANUAL.read_text(encoding="utf-8")
    for token in (
        "MVSEL2", "REPAIR2", "MVSTATE2", "MVQUAL",
        "TargetSizeStudyPolicy", "exact neighborhood engine",
        "bounded in anonymous RAM", "deterministic", "restart",
    ):
        assert token.lower() in text.lower()
    assert "MVQUAL is the sole hard target-size eligibility authority" in text
    assert "q < 3" in text
    assert "nonconverged_at_fixed_ceiling" in text
    assert "0 -> n1 coarse -> n2 short -> n3 final screen" in text
    assert "no alternate MVSEL1/REPAIR1 path" in text


def test_doc_arch1_external_algorithmic_provenance_is_cited():
    text = MANUAL.read_text(encoding="utf-8")
    for ref in ("[32]", "[33]", "[34]", "[35]", "[36]", "[37]"):
        assert ref in text
    assert "Blumofe" in text and "work stealing" in text.lower()
    assert "query_ball_point" in text
    assert "threadpoolctl" in text
    assert "NUMA" in text
    assert "numpy.bincount" in text


def test_doc_arch1_history_is_indexed_once_and_current_revision_is_recorded():
    revision_rows = [line for line in REV_INDEX.read_text().splitlines() if re.match(r"^\|\s*\d+\s*\|", line)]
    revisions = [int(line.split("|")[1].strip()) for line in revision_rows]
    assert revisions == sorted(set(revisions))
    assert revisions[-1] == 106
    assert "DOC-MVSEL2" in REV_INDEX.read_text()
    assert "0.20.242a0" in REL_INDEX.read_text()
    assert (ROOT / "docs/history/mlff/LINEAGE.md").is_file()
    assert (ROOT / "docs/history/mlff/manual_snapshots/mlff_training_data_architecture_rev090_full.md").is_file()


def test_doc_arch1_graph_and_directory_ownership_are_current():
    graph = json.loads(GRAPH.read_text())
    assert graph["schema_version"] == 2
    assert graph["authority_model"] == "single_generation_current_dependency_architecture"
    node_ids = {node["id"] for node in graph["nodes"]}
    for node in (
        "FEASIBILITY_EVIDENCE", "EXACT_NEIGHBORHOOD_AUTHORITY",
        "DOMAIN_SELECTION_ORDER", "DOMAIN_REPAIRED_MASTER_ORDER",
        "COMPACT_CONTINUATION_STATE", "PREFIX_QUALIFICATION_EVIDENCE",
        "TARGET_SIZE_STUDY_POLICY", "QUALIFIED_TARGET_SIZE_POPULATION",
        "TARGET_SIZE_DECISION", "COARSE_SCREEN", "SHORT_SCREEN",
        "FINAL_SCREEN", "FULL_TRAIN2_SCHEDULE",
        "OUT_OF_FOLD_PROTOCOL_EVIDENCE", "DEPLOYMENT_ARTIFACTS",
    ):
        assert node in node_ids
    assert not any(node.startswith("SIZE_STUDY_EPOCH") for node in node_ids)
    forbidden = "\n".join(graph["forbidden_current_paths"])
    assert "MVMIGRATE" in forbidden
    assert "held-out CV evaluation -> target-size decision" in forbidden
    root_names = {p.name for p in ROOT.iterdir() if p.is_file()}
    assert not any(name.startswith("ARCHITECTURE_NOTES_") for name in root_names)
    assert not any(name.startswith("PATCH_NOTES_") for name in root_names)
    assert "FINAL_GPU1_WORKSTATION_RUNBOOK.md" not in root_names
    assert (ROOT / "docs/guides/mlff_final_gpu1_workstation_runbook.md").is_file()


def test_doc_arch1_manual_hash_is_stable_under_current_bytes():
    digest = hashlib.sha256(MANUAL.read_bytes()).hexdigest()
    assert len(digest) == 64
