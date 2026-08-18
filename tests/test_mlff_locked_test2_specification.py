from __future__ import annotations

import inspect
from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli


def test_locked_test2_is_public_versioned_and_documented() -> None:
    assert mdstats.__version__ == "0.20.180a0"
    assert mdstats.LOCKED_TEST2_VERSION == "0.20.177a0"
    assert hasattr(mdstats, "LockedTest2Policy")
    assert hasattr(mdstats, "LockedTest2ActivationRecord")
    assert hasattr(mdstats, "LockedTest2ResultRecord")
    assert hasattr(mdstats, "LockedTest2ProductionModelRecord")
    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "arch_manuals" / "mlff_training_data_architecture.md").read_text(encoding="utf-8")
    assert "LOCKED-TEST2/final production publication is implemented in `mdstats 0.20.177a0`" in text
    assert "Implementation status (`0.20.177a0`): complete" in text


def test_locked_test2_is_strictly_post_select2_and_has_no_alternative_selection_path() -> None:
    select_source = inspect.getsource(campaign_cli._command_verify_train2_select2)
    locked_source = inspect.getsource(campaign_cli._command_verify_train2_locked_test)
    assert "_command_verify_train2_locked_test" in select_source
    assert "_command_verify_train2_select2" not in locked_source
    assert "with_stage_c_evidence" not in locked_source
    assert "fallback_to_next" not in locked_source
    assert "replay" not in str(inspect.signature(mdstats.build_locked_test2_result)).lower()


def test_locked_test2_freezes_before_inference_and_never_rematerializes_after_activation() -> None:
    source = inspect.getsource(campaign_cli._command_verify_train2_locked_test)
    assert source.index('existing_activation =') < source.index('_materialize_train2_locked_test_artifact')
    assert 'if existing_activation is None:' in source
    assert '_validate_existing_locked_test2_activation' in source
    helper = inspect.getsource(campaign_cli._validate_existing_locked_test2_activation)
    assert '_sha256(locked_path)' in helper
    assert 'Refusing rematerialization' in helper


def test_locked_test2_publishes_exact_frozen_mace_and_mliap_only_after_pass() -> None:
    source = inspect.getsource(campaign_cli._command_verify_train2_locked_test)
    assert 'if not result.passed:' in source
    assert 'production_best.model' in source
    assert 'production_best-mliap_lammps.pt' in source
    assert '_atomic_copy_file(target_model, published_target)' in source
    assert '_atomic_copy_file(mliap_model, published_mliap)' in source
    assert 'StageState.COMPLETE' in source
    assert 'StageState.FAILED' in source


def test_generated_and_example_configs_explain_locked_policy_inheritance() -> None:
    root = Path(__file__).resolve().parents[1]
    example = (root / "campaign.toml.example").read_text(encoding="utf-8")
    cli = (root / "mdstats" / "training_data" / "campaign_cli.py").read_text(encoding="utf-8")
    for text in (example, cli):
        assert "TRAIN2 LOCKED-TEST2" in text
        assert "locked_maximum_target_force_rmse_ev_per_angstrom" in text
