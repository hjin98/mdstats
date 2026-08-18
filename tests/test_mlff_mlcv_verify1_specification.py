from pathlib import Path
import mdstats


def test_verify1_public_contract_and_documentation():
    assert mdstats.MLCV_VERIFICATION_POLICY_SCHEMA == "mdstats.mlcv-verification-policy.v1"
    assert mdstats.MLCV_VERIFICATION_RECORD_SCHEMA == "mdstats.mlcv-verification-record.v1"
    assert mdstats.MLCV_LOCKED_TEST_RECORD_SCHEMA == "mdstats.mlcv-locked-test-record.v1"
    assert mdstats.MLCV_PRODUCTION_MODEL_SCHEMA == "mdstats.mlcv-production-model.v1"
    source = Path("mdstats/training_data/campaign_cli.py").read_text()
    manual = Path("docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = Path("docs/specs/training_data/mlff_mlcv_verification_spec.md").read_text()
    assert 'fallback_to_next_qualified_final_seed' in source
    assert 'MlcvPhysicalVerificationAttemptRecord' in source
    assert 'locked_interpolation_test' in source
    assert 'fallback_permitted=False' not in source or 'mlcv_locked_test' in source
    assert 'production_best.model' in source
    assert 'MLCV-VERIFY1 implementation record (`0.20.138a0`)' in manual
    assert 'fold models can never enter this path' in spec
    assert 'No other seed' in source


def test_verify1_config_template_keeps_historical_and_new_fallback_controls():
    source = Path("mdstats/training_data/campaign_cli.py").read_text()
    example = Path("campaign.toml.example").read_text()
    for text in (source, example):
        assert 'fallback_to_next_full_evaluation_candidate = true' in text
        assert 'fallback_to_next_qualified_final_seed = true' in text
