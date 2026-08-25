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
        == "mdstats.size-fidelity1.coarse-screen-calibration.target-size-v5.2026-08.v2"
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


def test_size_fidelity1_current_spec_matches_fixed_runtime_generation() -> None:
    root = _root()
    spec = (root / "docs/specs/training_data/mlff_size_fidelity1_calibration_spec.md").read_text()
    stage11 = json.loads((root / "docs/arch_manuals/stage11_dependency_graph.json").read_text())
    node = {item["id"]: item for item in stage11["nodes"]}[
        "SIZE_FIDELITY1_COARSE_SCREEN_CALIBRATION"
    ]

    assert "current normative calibration contract for the fixed target-size-v5 runtime" in spec
    assert "coarse endpoint candidates:        3, 4, 5" in spec
    assert "short-screen endpoint:             10" in spec
    assert "full/final reference endpoint:     30" in spec
    assert "eventual 30-epoch target finalists" in spec
    assert "Spearman rank correlation" in spec
    assert "diagnostic only" in spec
    assert "(1,3,10)/n" not in spec
    assert "CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1" not in spec
    assert node["authority_version"] == mdstats.SIZE_FIDELITY_VERSION
    assert node["current_schema_generation"] == "target-size-v5 v2"
    assert node["implementation_status"] == "implemented_deferred_final_gpu_qualification"
    assert node["calibrates"] == [
        "coarse_epoch_candidates",
        "coarse_monitor_configuration_candidates",
        "coarse_equivalence_candidates_mev_per_a",
    ]
    assert "coarse_finalist_recall_meets_configured_threshold" in node["hard_requirements"]
    assert "short_finalist_recall_meets_configured_threshold" in node["hard_requirements"]
    assert "winner_recall_equals_1" not in node["hard_requirements"]


def test_current_campaign_example_does_not_advertise_ignored_or_retired_size_controls() -> None:
    root = _root()
    config = tomllib.loads((root / "campaign.toml.example").read_text())
    size_cfg = config["target_data"]["size_convergence"]
    for key in (
        "fidelity_epochs",
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
