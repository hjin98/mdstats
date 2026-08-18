from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
SPEC = ROOT / "docs/specs/training_data/mlff_mvkernel1_sparse_vector_kernels_spec.md"


def test_mvkernel1_release_manual_and_spec_are_synchronized() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "Gate MVKERNEL1 - sparse selector/qualification vector kernels - COMPLETE" in text
    assert "**Next gate.** `REPAIR-PAR1`." in text
    assert "ragged-CSR" in text
    assert "byte-identical telemetry" in text
    assert SPEC.is_file()


def test_mvkernel1_dependency_graph_is_closed() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    node = next(item for item in graph["nodes"] if item["id"] == "MVKERNEL1_VECTOR_SPARSE_KERNELS")
    assert node["implementation_status"] == "implemented_exact_vector_sparse_kernels"
    assert node["implemented_release"] == "0.20.230a0"
    assert node["selector_rank_authority_changed"] is False
    assert node["scientific_authority_change"] is False


def test_mvkernel1_code_retains_exact_reference_oracles() -> None:
    selector = (ROOT / "mdstats/training_data/target_multi_view_selector.py").read_text(encoding="utf-8")
    qualification = (ROOT / "mdstats/training_data/target_multi_view_qualification.py").read_text(encoding="utf-8")
    sparse = (ROOT / "mdstats/training_data/_sparse_vector_kernels.py").read_text(encoding="utf-8")
    assert "_select_and_update_reference" in selector
    assert "_scatter_decrement_pair_exact" in selector
    assert "unsatisfied_required_obligation_count" in selector
    assert "_selector_telemetry_reference" in qualification
    assert "csr_gather_rows" in sparse
    assert "np.bincount" in qualification


def test_mvkernel1_history_records_are_present() -> None:
    assert (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV97.md").is_file()
    assert (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.230a0.md").is_file()
    assert "0.20.230a0" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


def test_mvkernel1_frozen_benchmark_evidence_is_consistent() -> None:
    evidence_path = ROOT / "benchmarks/mlff_mvkernel1_cloud_cpu_mpa0_2026-08-17.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["release"] == "0.20.230a0"
    assert evidence["architecture_revision"] == 97
    assert evidence["acceptance"]["status"] == "PASS"
    assert evidence["acceptance"]["next_gate"] == "REPAIR-PAR1"
    assert evidence["active_foundation"]["family"] == "MACE-MPA-0 medium"
    assert evidence["active_foundation"]["checkpoint_sha256"] == (
        "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638"
    )
    assert evidence["active_foundation"]["mh1_compatible"] is True
    assert evidence["scientific"]["selector_digest"] == (
        "d147d85acd64dd386dcd9b64e1bd534001e1b1a9e1736522b2ffaddbb978b378"
    )
    assert evidence["scientific"]["scale_16384_selector_digest"] == (
        "aaec42fb0c1df6a62ce2286ec5f5b8897bc089d6d31726da89a0461bcd75d608"
    )
    assert evidence["scientific"]["mvqual_telemetry_authority_digest"] == (
        "d51daef220edffd1f9a72676ee5835ed4f0db44d8818b78f3449defcba63894c"
    )
    assert evidence["scientific"]["mvqual_plan_digest"] == (
        "ff8f64607a4835309889cb9b4c1e886959d9e47468a48df07676e0bf32295a80"
    )
    assert evidence["execution"]["selector_4096_2048"]["speedup"] > 1.0
    assert evidence["execution"]["selector_24576_16384"]["speedup"] > 1.0
    assert evidence["execution"]["mvqual_telemetry_16384_8192_6family"]["speedup"] > 10.0
