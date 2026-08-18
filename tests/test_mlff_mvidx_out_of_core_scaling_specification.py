from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
SPEC = ROOT / "docs/specs/training_data/mlff_mvidx_out_of_core_scaling_spec.md"


def test_mvidx_ooc_release_metadata_and_forward_gate() -> None:
    assert mdstats.__version__ >= "0.20.238a0"
    text = MANUAL.read_text(encoding="utf-8")
    assert '0.20.238a0' in (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
    assert "architecture_revision: 103" in text
    assert "Multi-billion-edge MVIDX out-of-core hardening" in text
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["architecture_revision"] == 103
    assert graph["schema_version"] == 83
    assert graph["next_gate"] == "FINAL_GPU1_DEFERRED_RELEASE_QUALIFICATION"


def test_mvidx_ooc_spec_freezes_exact_execution_contract() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "byte-identical",
        "NPY memmap",
        "bounded",
        "hard-linked",
        "disk",
        "FINAL-GPU1",
    ):
        assert token in text
    source = (ROOT / "mdstats/training_data/target_coverage_sparse_index.py").read_text(encoding="utf-8")
    assert "_csr_inverse_out_of_core" in source
    assert "_MVIDX_OUT_OF_CORE_MIN_OUTPUT_BYTES" in source
    store = (ROOT / "mdstats/training_data/target_coverage_sparse_index_store.py").read_text(encoding="utf-8")
    assert "_whole_npy_memmap_source" in store


def test_mvidx_ooc_qualification_record_binds_reported_failure_and_fix() -> None:
    q = json.loads(
        (ROOT / "release/qualification_logs/MLFF_MVIDX_OOC_SCALING_QUALIFICATION_0.20.238a0.json").read_text(
            encoding="utf-8"
        )
    )
    assert q["status"] == "PASS_EXACT_EQUIVALENCE_SCALING_HARDENING"
    assert q["scientific_authority_change"] is False
    assert q["incident"]["total_exact_edges"] == 9_505_021_522
    assert q["incident"]["in_memory_estimate_bytes"] > q["incident"]["stage_ram_budget_bytes"]
    assert q["resolution"]["total_inverse_uint32_payload_gib"] > 35.0
    assert q["tests"]["target_data2_original_authority"]["passed"] == 111
    assert q["next_gate"] == "FINAL_GPU1_DEFERRED_RELEASE_QUALIFICATION"
