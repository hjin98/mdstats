from __future__ import annotations

import inspect
from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"
EXAMPLE = ROOT / "campaign.toml.example"


def test_pes_verify1_release_manual_and_public_api_are_current():
    text = MANUAL.read_text(encoding="utf-8")
    assert mdstats.__version__ == "0.20.180a0"
    assert "PES-VERIFY1 is implemented in `mdstats 0.20.173a0`" in text
    assert "Implementation status (`0.20.173a0`): complete" in text
    assert "centered side increments" in text
    assert "all-generated-modes hard gate" in text
    assert mdstats.PESVerifyPolicy is not None
    assert mdstats.build_pes_probe_set is not None
    assert mdstats.assess_pes_model is not None


def test_generated_and_example_configs_freeze_pes_policy():
    source = inspect.getsource(campaign_cli)
    example = EXAMPLE.read_text(encoding="utf-8")
    for token in (
        "pes_base_configurations = 4",
        "pes_modes_per_base = 4",
        "pes_displacement_amplitude_angstrom = 0.04",
        "pes_strain_amplitude = 0.01",
        "pes_projected_force_atol_ev_per_angstrom = 0.05",
        "pes_force_stiffness_atol_ev_per_angstrom2 = 0.50",
        "pes_energy_curvature_atol_ev_per_angstrom2 = 0.50",
        'pes_reference_extxyz = ""',
        'pes_reference_protocol_digest = ""',
    ):
        assert token in source
        assert token in example


def test_pes_policy_defaults_match_frozen_first_release_contract():
    policy = campaign_cli._pes_verify_policy({"verification": {}})
    assert policy.maximum_base_configurations == 4
    assert policy.maximum_modes_per_base == 4
    assert policy.displacement_amplitude_angstrom == 0.04
    assert policy.strain_amplitude == 0.01
    assert policy.projected_force_atol_ev_per_angstrom == 0.05
    assert policy.projected_force_rtol == 0.25
    assert policy.force_stiffness_atol_ev_per_angstrom2 == 0.50
    assert policy.energy_curvature_atol_ev_per_angstrom2 == 0.50
    assert policy.require_all_modes is True


def test_train2_verify_dispatches_deploy_then_pes():
    source = inspect.getsource(campaign_cli.command_verify)
    assert "_current_train2_deploy_authority" in source
    assert "_command_verify_train2_deploy" in source
    assert "_command_verify_train2_pes" in source
    pes_source = inspect.getsource(campaign_cli._command_verify_train2_pes)
    assert "collect_pes_reference_from_vasp" in pes_source
    assert "prediction_payload_from_mace_view" in pes_source
    assert "_command_verify_train2_relax" in pes_source
