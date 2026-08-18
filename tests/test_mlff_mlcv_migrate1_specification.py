from pathlib import Path
import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_mlcv_migrate1_release_and_architecture_gate_closed():
    assert mdstats.__version__ == '0.20.140a0'
    assert 'version = "0.20.140a0"' in (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    manual = (ROOT / 'docs/arch_manuals/mlff_training_data_architecture.md').read_text(encoding='utf-8')
    assert 'MLCV-MIGRATE1 implementation record (`0.20.139a0`)' in manual
    assert 'MLCV replay-degradation semantic correction (`0.20.140a0`)' in manual
    assert 'mlcv_nested_cv' in manual
    assert 'The nine-gate conventional-CV correction is complete.' in manual


def test_mlcv_migrate1_spec_exists_and_names_migration_invariants():
    spec = ROOT / 'docs/specs/training_data/mlff_mlcv_migration_spec.md'
    assert spec.is_file()
    text = spec.read_text(encoding='utf-8')
    for token in (
        'mlcv_nested_cv', 'adaptive_topk', 'lifecycle authority',
        'top-five', 'protocol freeze', 'historical', 'restart', 'storage',
    ):
        assert token in text
