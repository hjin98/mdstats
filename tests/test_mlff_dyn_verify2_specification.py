from __future__ import annotations

import inspect
from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli


def test_dyn_verify2_is_public_and_versioned() -> None:
    assert mdstats.__version__ == "0.20.242a0"
    assert hasattr(mdstats, "DynVerifyPolicy")
    assert hasattr(mdstats, "DynVerifyCampaignRecord")
    assert "dyn-verify2.2026-08.v1" in mdstats.DYN_VERIFY_IMPLEMENTATION_VERSION


def test_relax_hands_passing_candidates_to_deployed_dyn_gate() -> None:
    relax_source = inspect.getsource(campaign_cli._command_verify_train2_relax)
    dyn_source = inspect.getsource(campaign_cli._command_verify_train2_dyn)
    assert "_command_verify_train2_dyn" in relax_source
    assert "simulate_lammps_mliap_dynamics_case" in dyn_source
    assert "reduce_lammps_mliap_dynamics_case" in dyn_source
    assert "mliap_artifact_path" in dyn_source
    assert "expected_executable_sha256" in dyn_source


def test_dyn_is_post_selection_only_and_cannot_mutate_target_size() -> None:
    finalize = inspect.getsource(campaign_cli._finalize_train2_dyn)
    dyn_source = inspect.getsource(campaign_cli._command_verify_train2_dyn)
    assert "post-selection production verification only" in finalize
    assert "_load_verified_target_size_study_authority" in finalize
    assert "_command_verify_train2_select2" in finalize
    combined = finalize + dyn_source
    assert "with_stage_c_evidence" not in combined
    assert "_ensure_target_production_corpus_decision" not in combined
    assert "attach_epoch_" not in combined


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
