from __future__ import annotations

import json
from pathlib import Path

import mdstats


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_size_fidelity1_release_and_public_authority_are_synchronized() -> None:
    assert mdstats.__version__ >= "0.20.209a0"
    assert mdstats.SIZE_FIDELITY_VERSION == "mdstats.size-fidelity1.coarse-screen-calibration.2026-08.v1"
    for name in (
        "SizeFidelityCalibrationPolicy",
        "SizeFidelityExecutionPlan",
        "SizeFidelityMetric",
        "SizeFidelityCandidateAssessment",
        "SizeFidelityQualificationReport",
        "build_size_fidelity_execution_plan",
        "build_size_fidelity_qualification",
        "validate_size_fidelity_qualification",
    ):
        assert hasattr(mdstats, name)


def test_size_fidelity1_manual_spec_graph_and_historical_release_are_preserved() -> None:
    root = _root()
    manual = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (root / "docs/specs/training_data/mlff_size_fidelity1_coarse_screen_calibration_spec.md").read_text()
    graph = json.loads((root / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    nodes = {item["id"]: item for item in graph["nodes"]}
    changelog = (root / "CHANGELOG.md").read_text()
    readme = (root / "README.md").read_text()

    assert "revision 59" in manual
    assert "SIZE-FIDELITY1.2 - hard survivor-recall authority" in manual
    assert "both eventual 30-epoch target finalists" in manual
    assert "scientifically open but implementation-complete" in manual
    assert "**Authority implementation release:** `mdstats 0.20.183a0`" in spec
    assert "monitor metrics **must** be derived from full-role prediction authority" in spec
    assert "Spearman correlation is **diagnostic only**" in spec
    assert "Jamieson" in spec and "Spearman" in spec and "Batatia" in spec
    assert graph["architecture_revision"] >= 76
    assert graph["schema_version"] >= 58
    node = nodes["SIZE_FIDELITY1_COARSE_SCREEN_CALIBRATION"]
    assert node["implementation_status"] == "implemented_deferred_final_gpu_qualification"
    assert node["implemented_version"] == "0.20.183a0"
    assert "epoch10_recall_of_both_30_epoch_target_finalists_equals_1" in node["hard_requirements"]
    assert "## 0.20.209a0 - 2026-08-16" in changelog
    assert "`mdstats 0.20.184a0` introduces **FINAL-GPU1**" in readme


def test_size_fidelity1_markdown_sources_exist_before_pdf_render() -> None:
    root = _root()
    for path in (
        root / "docs/specs/training_data/mlff_size_fidelity1_coarse_screen_calibration_spec.md",
        root / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV49.md",
        root / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.183a0.md",
    ):
        assert path.is_file(), path
        assert path.stat().st_size > 2_000, path
