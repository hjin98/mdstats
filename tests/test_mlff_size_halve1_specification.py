from __future__ import annotations

import json
from pathlib import Path

import mdstats


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_size_halve1_release_authorities_and_public_surface_are_synchronized() -> None:
    assert mdstats.__version__ == "0.20.187a0"
    assert mdstats.TARGET_DATA_LADDER_VERSION == "mdstats.target-data2c.ladder.2026-08.v3"
    assert mdstats.TARGET_SIZE_CONVERGENCE_VERSION == "mdstats.target-data2d.size-convergence.2026-08.v2"
    assert mdstats.TARGET_SIZE_TRAINING_EVIDENCE_SCHEMA == "mdstats.target-size-training-evidence.v3"
    assert mdstats.TARGET_PRODUCTION_CORPUS_VERSION == "mdstats.target-data2e.production-corpus.2026-08.v2"
    assert hasattr(mdstats, "with_stage_b0_evidence")
    assert hasattr(mdstats, "build_eval2_coarse_size_study_target_role")


def test_size_halve1_policy_defaults_encode_3_10_30_and_hard_coverage_only() -> None:
    policy = mdstats.TargetSizeConvergencePolicy()
    assert policy.min_coverage_qualifiers == 3
    assert policy.coarse_training_epochs == 3
    assert policy.max_coarse_training_candidates == 4
    assert policy.coarse_target_monitor_configurations == 256
    assert policy.short_training_epochs == 10
    assert policy.max_short_training_candidates == 2
    assert policy.final_training_epochs == 30
    assert policy.coarse_practical_equivalence_mev_per_a == policy.practical_equivalence_mev_per_a


def test_size_halve1_manual_spec_examples_and_graph_are_current() -> None:
    root = _root()
    manual = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (root / "docs/specs/training_data/mlff_size_halve1_target_size_revision_spec.md").read_text()
    readme = (root / "README.md").read_text()
    changelog = (root / "CHANGELOG.md").read_text()
    example = (root / "campaign.toml.example").read_text()
    embedded = (root / "mdstats/training_data/campaign_cli.py").read_text()
    graph = json.loads((root / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    nodes = {item["id"]: item for item in graph["nodes"]}

    assert "revision 54" in manual
    assert "retain every qualifying rung" in manual
    assert "Stage B0" in manual and "3/10/30" in manual
    assert "SIZE-FIDELITY1" in manual and "PERF-P2R" in manual
    assert "Class C - scientific correction" in manual
    assert "**Gate:** `SIZE-HALVE1`" in spec
    assert "coverage is now a hard" in spec.lower() and "admissibility" in spec.lower()
    assert "boundary" in spec and "RNG" in spec
    assert "**Authority class:** C" in spec
    assert "SIZE-FIDELITY1" in spec and "provisional defaults" in spec
    assert "`mdstats 0.20.182a0`" in readme and "`mdstats 0.20.184a0`" in readme
    assert changelog.startswith("## 0.20.187a0 - 2026-08-15")
    for text in (example, embedded):
        assert "coarse_training_epochs = 3" in text
        assert "max_coarse_training_candidates = 4" in text
        assert "coarse_target_monitor_configurations = 256" in text
        assert "max_short_training_candidates = 2" in text
    assert graph["architecture_revision"] == 54
    assert graph["schema_version"] == 36
    assert nodes["SIZE_HALVE1_TARGET_SIZE_CORRECTION"]["implementation_status"] == "implemented"
    assert nodes["SIZE_HALVE1_TARGET_SIZE_CORRECTION"]["authority_class"] == "C"
    assert nodes["PERF_P2_LAZY_TARGET_LADDER_V2"]["current_status"] == "historical_superseded"
    assert nodes["SIZE_FIDELITY1_COARSE_SCREEN_CALIBRATION"]["implementation_status"] == "implemented_deferred_final_gpu_qualification"
    assert nodes["PERF_P2R_SUCCESSIVE_FIDELITY_EXECUTION"]["implementation_status"] == "implemented_cpu_control_plane_deferred_final_gpu_qualification"


def test_historical_perf_p2_spec_is_explicitly_superseded_not_rewritten() -> None:
    spec = (_root() / "docs/specs/training_data/mlff_perf_p2_lazy_target_ladder_spec.md").read_text()
    assert "Release:** `mdstats 0.20.181a0`" in spec
    assert "Supersession notice" in spec
    assert "historical specification" in spec
    assert "TARGET-DATA2C v3 full-ladder authority" in spec


def test_size_halve1_markdown_documents_exist_before_pdf_render() -> None:
    root = _root()
    for path in (
        root / "docs/specs/training_data/mlff_size_halve1_target_size_revision_spec.md",
        root / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV48.md",
        root / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.182a0.md",
    ):
        assert path.is_file(), path
        assert path.stat().st_size > 2_000, path
