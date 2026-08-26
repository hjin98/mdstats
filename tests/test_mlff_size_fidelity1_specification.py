from __future__ import annotations

import json
from pathlib import Path
import tomllib

import mdstats


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_size_fidelity1_release_and_public_authority_are_synchronized() -> None:
    assert mdstats.__version__ == "0.20.242a0"
    assert (
        mdstats.SIZE_FIDELITY_VERSION
        == "mdstats.size-fidelity1.coarse-screen-calibration.flexible-fidelity.2026-08.v4"
    )
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


def test_size_fidelity1_current_spec_matches_configurable_runtime_generation() -> None:
    root = _root()
    spec = (root / "docs/specs/training_data/mlff_size_fidelity1_calibration_spec.md").read_text()
    graph = json.loads((root / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    node_ids = {item["id"] for item in graph["nodes"]}

    assert "current normative calibration contract for the flexible-fidelity target-size runtime" in spec
    assert "coarse endpoint candidates:        3, 4, 5" in spec
    assert "short-screen endpoint:             n2" in spec
    assert "final-screen endpoint:             n3" in spec
    assert "full reference endpoint:           n" in spec
    assert "eventual full-reference target finalists" in spec
    assert "Spearman rank correlation" in spec
    assert "diagnostic only" in spec
    assert "`0 < n1 < n2 < n3` and `n > 0`" in spec
    assert "screen `(1, 3, 10)` with production/reference `30`" in spec
    assert {"COARSE_SCREEN", "SHORT_SCREEN", "FINAL_SCREEN", "FULL_TRAIN2_SCHEDULE"} <= node_ids
    assert not any(node.startswith("SIZE_STUDY_EPOCH") for node in node_ids)


def test_current_campaign_example_does_not_advertise_ignored_or_retired_size_controls() -> None:
    root = _root()
    config = tomllib.loads((root / "campaign.toml.example").read_text())
    size_cfg = config["target_data"]["size_convergence"]
    for key in (
        "coarse_training_epochs",
        "short_training_epochs",
        "final_training_epochs",
        "screening_optimizer_seed",
        "ladder_exponents",
        "minimum_materializable_rungs",
        "reserve_required_strata",
        "reserve_correlation_intervals",
        "fps_tie_tolerance",
        "min_coverage_qualifiers",
        "max_coarse_training_candidates",
        "coarse_target_monitor_configurations",
        "max_short_training_candidates",
    ):
        assert key not in size_cfg
    assert size_cfg["fidelity_epochs"] == [1, 3, 10]
    assert config["training"]["max_num_epochs"] == 30


def test_size_fidelity1_current_and_historical_sources_are_preserved() -> None:
    root = _root()
    for path in (
        root / "docs/specs/training_data/mlff_size_fidelity1_calibration_spec.md",
        root / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV49.md",
        root / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.183a0.md",
    ):
        assert path.is_file(), path
        assert path.stat().st_size > 2_000, path
