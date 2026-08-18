from __future__ import annotations

from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"


def test_target_data2b_public_contract_is_available() -> None:
    policy = mdstats.TargetCoveragePolicy()
    assert policy.coverage_metric == "reference_mass_local_knn"
    assert policy.coverage_threshold == 0.95
    assert policy.coverage_resolution_mass == 1.0 / 128.0
    assert policy.coverage_leave_one_out is True
    assert policy.extent_quantile_alpha == 0.01
    assert policy.include_profile_selection_features is True
    assert policy.require_profile_environment_support is True
    assert callable(mdstats.build_target_coverage_reference)
    assert callable(mdstats.score_target_subset_coverage)
    assert callable(mdstats.assert_nested_coverage_monotonicity)
    assert callable(mdstats.validate_target_coverage_reference_authority)


def test_target_data2b_campaign_restart_contract_is_frozen() -> None:
    assert "target_coverage_reference" in campaign_cli._PREPARE_RECEIPT_RECORD_KEYS
    contract = campaign_cli._prepare_contract_signature()
    assert contract["target_data2b_coverage_version"] == mdstats.TARGET_COVERAGE_VERSION


def test_target_data2b_manual_records_reference_side_semantics_and_gate_boundary() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    required = (
        "## Gate TARGET-DATA2B",
        "reference_mass_local_knn",
        "coverage_threshold = 0.95",
        "coverage_resolution_mass = 1 / 128",
        "coverage_leave_one_out = true",
        "counter runs over the full reference",
        "Distribution fidelity is a distinct diagnostic",
        "TARGET-DATA2C",
    )
    for phrase in required:
        assert phrase in text
