from __future__ import annotations

import inspect
from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli


def test_dyn_verify2_is_public_and_versioned() -> None:
    assert mdstats.__version__ == "0.20.180a0"
    assert hasattr(mdstats, "DynVerifyPolicy")
    assert hasattr(mdstats, "DynVerifyCampaignRecord")
    assert "dyn-verify2.2026-08.v1" in mdstats.DYN_VERIFY_IMPLEMENTATION_VERSION
    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "arch_manuals" / "mlff_training_data_architecture.md").read_text(encoding="utf-8")
    assert "DYN-VERIFY2 is implemented in `mdstats 0.20.175a0`" in text
    assert "Implementation status (`0.20.175a0`): complete" in text


def test_relax_hands_passing_candidates_to_deployed_dyn_gate() -> None:
    relax_source = inspect.getsource(campaign_cli._command_verify_train2_relax)
    dyn_source = inspect.getsource(campaign_cli._command_verify_train2_dyn)
    assert "_command_verify_train2_dyn" in relax_source
    assert "run_lammps_mliap_dynamics_case" in dyn_source
    assert "mliap_artifact_path" in dyn_source
    assert "expected_executable_sha256" in dyn_source


def test_dyn_stage_c_binds_physical_evidence_back_to_target_size_funnel() -> None:
    source = inspect.getsource(campaign_cli._finalize_train2_dyn) + inspect.getsource(campaign_cli._dyn_stage_c_training_evidence)
    assert "with_stage_c_evidence" in source
    assert "physical_qualification_passed" in source
    assert "physical_qualification_digest" in source
    assert "_ensure_target_production_corpus_decision" in source


def test_generated_default_contains_frozen_dyn_protocol() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "campaign.toml.example").read_text(encoding="utf-8")
    for literal in (
        "dyn_base_configurations = 2",
        "dyn_temperatures_kelvin = [300.0, 800.0]",
        "dyn_timestep_fs = 0.5",
        "dyn_nvt_steps = 400",
        "dyn_nve_steps = 2000",
        "dyn_maximum_energy_drift_ev_per_atom_per_ps = 0.026",
        "dyn_persistent_damage_samples = 10",
    ):
        assert literal in text
