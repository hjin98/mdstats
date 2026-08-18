from __future__ import annotations

import inspect
from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"
EXAMPLE = ROOT / "campaign.toml.example"


def test_relax_verify1_release_manual_and_public_api_are_current():
    text = MANUAL.read_text(encoding="utf-8")
    assert mdstats.__version__ == "0.20.180a0"
    assert "RELAX-VERIFY1 is implemented in `mdstats 0.20.174a0`" in text
    assert "Implementation status (`0.20.174a0`): complete" in text
    assert "0.03 eV/A" in text
    assert "protected-group RMS displacement" in text
    assert mdstats.RelaxVerifyPolicy is not None
    assert mdstats.build_relax_base_set is not None
    assert mdstats.assess_relaxed_geometry is not None


def test_generated_and_example_configs_freeze_relax_policy():
    source = inspect.getsource(campaign_cli)
    example = EXAMPLE.read_text(encoding="utf-8")
    for token in (
        "relax_base_configurations = 4",
        'relax_optimizer = "FIRE"',
        "relax_force_convergence_ev_per_angstrom = 0.03",
        "relax_maximum_steps = 500",
        'relax_topology_group_ids = ["framework"]',
        "relax_topology_cutoff_scale = 1.20",
        "relax_rms_displacement_tolerance_angstrom = 0.15",
        "relax_max_displacement_tolerance_angstrom = 0.40",
        "relax_bond_rmse_tolerance_angstrom = 0.08",
        "relax_angle_rmse_tolerance_degrees = 8.0",
        'relax_reference_extxyz = ""',
        'relax_reference_protocol_digest = ""',
    ):
        assert token in source
        assert token in example


def test_relax_policy_defaults_match_frozen_first_release_contract():
    policy = campaign_cli._relax_verify_policy({"verification": {}})
    assert policy.maximum_base_configurations == 4
    assert policy.optimizer == "FIRE"
    assert policy.force_convergence_ev_per_angstrom == 0.03
    assert policy.maximum_steps == 500
    assert policy.fixed_cell is True
    assert policy.topology_group_ids == ("framework",)
    assert policy.topology_cutoff_scale == 1.20
    assert policy.rms_displacement_tolerance_angstrom == 0.15
    assert policy.max_displacement_tolerance_angstrom == 0.40
    assert policy.bond_rmse_tolerance_angstrom == 0.08
    assert policy.bond_max_error_tolerance_angstrom == 0.20
    assert policy.angle_rmse_tolerance_degrees == 8.0
    assert policy.angle_max_error_tolerance_degrees == 20.0
    assert policy.require_exact_topology is True


def test_train2_pes_hands_only_qualified_candidates_to_relax_gate():
    pes_source = inspect.getsource(campaign_cli._command_verify_train2_pes)
    relax_source = inspect.getsource(campaign_cli._command_verify_train2_relax)
    assert "_command_verify_train2_relax" in pes_source
    assert "eligible_pes = tuple(record for record in pes.run_records if record.passed)" in relax_source
    assert "collect_relax_reference_from_vasp" in relax_source
    assert "DYN-VERIFY2" in relax_source
