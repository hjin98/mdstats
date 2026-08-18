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
    assert mdstats.__version__ == "0.20.239a0"
    text = MANUAL.read_text(encoding="utf-8")
    assert "architecture_revision: 103" in text
    assert 'release: "mdstats 0.20.239a0"' in text
    assert "# Part VI - Performance and execution architecture" in text
    assert "# Part VII - Current implementation status and frozen forward gates" in text
    assert "## Context retrieval index" in text
    assert not (ROOT / "mlff_training_data_architecture.md").exists()
    assert not (ROOT / "mlff_training_data_dependency_graph.json").exists()


def test_doc_arch1_manual_is_deterministically_assembled_from_numbered_sources():
    order = [
        "00_front_matter.md", "10_foundations.md", "20_data_contracts.md",
        "30_statistical_design.md", "40_training_evaluation.md",
        "50_target_multiview.md", "60_execution_performance.md",
        "70_status_and_gates.md", "80_ownership_and_decisions.md",
        "90_references.md",
    ]
    expected = "\n\n".join((CHAPTERS / name).read_text(encoding="utf-8").rstrip() for name in order) + "\n"
    assert MANUAL.read_text(encoding="utf-8") == expected
    assert len(MANUAL.read_text(encoding="utf-8").splitlines()) < 4000


def test_doc_arch1_frozen_performance_program_and_shared_neighborhood_contract():
    text = MANUAL.read_text(encoding="utf-8")
    for gate in (
        "PERFBASE1", "PARCORE1", "NEIGHBOR1", "MVIDX-REUSE1", "COVREF-PAR1",
        "MVKERNEL1", "REPAIR-PAR1", "MVQUAL-PAR1", "AUDIT-EVAL-PERF1",
        "REPLAY-PERF1", "CAMPAIGN-PERF-QUAL1", "MVSTATE-REUSE1",
    ):
        assert gate in text
    assert "ExactNeighborhoodEngine" in text
    assert "MVIDX1 SHALL reuse the exact neighborhood output produced by FEAS1" in text
    assert "worker count, query block size" in text.lower()
    assert "stable parallel sparse inversion" in text
    assert "P_{\\mathrm{outer}}\\times P_{\\mathrm{native}}" in text
    assert "workers-busy" not in text  # prose uses implementation-neutral busy/allocated naming
    assert "busy/allocated workers" in text


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
    assert revisions[-1] == 103
    assert "NEIGHBOR1" in REV_INDEX.read_text()
    assert "0.20.239a0" in REL_INDEX.read_text()
    assert (ROOT / "docs/history/mlff/LINEAGE.md").is_file()
    assert (ROOT / "docs/history/mlff/manual_snapshots/mlff_training_data_architecture_rev090_full.md").is_file()


def test_doc_arch1_graph_and_directory_ownership_are_current():
    graph = json.loads(GRAPH.read_text())
    assert graph["architecture_revision"] == 103
    assert graph["schema_version"] == 83
    node_ids = {node["id"] for node in graph["nodes"]}
    for node in (
        "DOC_ARCH1_MANUAL_RESTRUCTURE_PERFORMANCE_ROADMAP",
        "PERFBASE1_CAMPAIGN_BASELINES", "PARCORE1_DETERMINISTIC_WORK_QUEUE",
        "NEIGHBOR1_SHARED_EXACT_ENGINE", "MVIDX_REUSE1_SPARSE_TRANSPOSE",
        "COVREF_PAR1_GLOBAL_BLOCK_QUEUE", "MVKERNEL1_VECTOR_SPARSE_KERNELS",
        "REPAIR_PAR1_PROPOSAL_QUEUE", "MVQUAL_PAR1_GLOBAL_SCORING_QUEUE",
        "AUDIT_EVAL_PERF1_CPU_KERNELS", "REPLAY_PERF1_INDEX_CACHE", "CAMPAIGN_PERF_QUAL1_CLOSURE",
        "MVSTATE_REUSE1_SELECTOR_REPAIR_HANDOFF",
    ):
        assert node in node_ids
    root_names = {p.name for p in ROOT.iterdir() if p.is_file()}
    assert not any(name.startswith("ARCHITECTURE_NOTES_") for name in root_names)
    assert not any(name.startswith("PATCH_NOTES_") for name in root_names)
    assert "FINAL_GPU1_WORKSTATION_RUNBOOK.md" not in root_names
    assert (ROOT / "docs/guides/mlff_final_gpu1_workstation_runbook.md").is_file()


def test_doc_arch1_manual_hash_is_stable_under_current_bytes():
    digest = hashlib.sha256(MANUAL.read_bytes()).hexdigest()
    assert len(digest) == 64
