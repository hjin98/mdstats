from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import mdstats
from mdstats.training_data import target_coverage_sparse_index as mvidx
from tests.test_mlff_target_data2b_feas1 import _reference_and_role

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
SPEC = ROOT / "docs/specs/training_data/mlff_mvidx_reuse1_sparse_inversion_spec.md"
EVIDENCE = ROOT / "benchmarks/mlff_mvidx_reuse1_cloud_cpu_mpa0_2026-08-17.json"


def test_mvidx_reuse1_worker_count_is_execution_only() -> None:
    reference, role = _reference_and_role(split_units=True)
    feasibility, neighborhoods = mdstats.build_target_coverage_feasibility_artifacts(
        reference, role, query_workers=1, query_block_size=3, block_workers=2
    )
    indices = [
        mdstats.build_target_coverage_sparse_index(
            reference,
            role,
            feasibility,
            exact_neighborhood_store=neighborhoods,
            query_workers=1,
            global_workers=workers,
        )
        for workers in (1, 2, 3)
    ]
    assert len({item.content_digest for item in indices}) == 1
    for domain0, domain1 in zip(indices[0].domains, indices[-1].domains, strict=True):
        for family0, family1 in zip(domain0.families, domain1.families, strict=True):
            assert np.array_equal(family0.candidate_offsets, family1.candidate_offsets)
            assert np.array_equal(family0.candidate_witnesses, family1.candidate_witnesses)


def test_mvidx_reuse1_vectorized_row_validator_matches_row_semantics() -> None:
    offsets = np.asarray([0, 2, 2, 5, 6], dtype="<u8")
    good = np.asarray([1, 4, 0, 3, 7, 2], dtype="<u4")
    mvidx._validate_sorted_unique_rows(offsets, good, name="test")
    for bad in (
        np.asarray([4, 1, 0, 3, 7, 2], dtype="<u4"),
        np.asarray([1, 4, 0, 0, 7, 2], dtype="<u4"),
    ):
        with pytest.raises(mdstats.TrainingDataInputError, match="strictly sorted"):
            mvidx._validate_sorted_unique_rows(offsets, bad, name="test")


def test_mvidx_reuse1_release_docs_and_evidence_are_retained() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "Gate MVIDX-REUSE1 - stable parallel sparse inversion - COMPLETE" in text
    assert SPEC.is_file() and EVIDENCE.is_file()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["release"] == "0.20.228a0"
    assert evidence["scientific_digest"] == "e408bd25dcc9b3c515a76ba2de505ca272d2243e7f9079f65e279694c987597c"
    assert evidence["acceptance"]["status"] == "PASS"
    assert evidence["acceptance"]["three_lane_speedup"] > 2.0
    assert evidence["acceptance"]["next_gate"] == "COVREF-PAR1"


def test_mvidx_reuse1_dependency_graph_is_closed() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["architecture_revision"] >= 95
    node = next(item for item in graph["nodes"] if item["id"] == "MVIDX_REUSE1_SPARSE_TRANSPOSE")
    assert node["implementation_status"] == "implemented"
    assert node["implemented_release"] == "0.20.228a0"
    assert node["scientific_authority_change"] is False
    assert node["mvidx_scientific_output_digest"] == "e408bd25dcc9b3c515a76ba2de505ca272d2243e7f9079f65e279694c987597c"
