from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/training_data/mlff_data9a3_production_corpus_qualification_spec.md"
ARCH = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"

def test_data9a3_specification_and_release_version() -> None:
    text = SPEC.read_text(encoding="utf-8")
    assert 'version: "0.20.40a0"' in text
    assert "37,632" in text
    assert "supported_with_temporal_blocks_only" in text
    assert "production_replay_corpus_not_bound" in text
    assert 'version = "0.20.140a0"' in (ROOT / "pyproject.toml").read_text()
    assert "MLFF-DATA9A3 production qualification" in ARCH.read_text()
