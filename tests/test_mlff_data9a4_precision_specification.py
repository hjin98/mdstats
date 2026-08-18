from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/training_data/mlff_data9a4_precision_and_production_realization_spec.md"


def test_data9a4_precision_specification_and_release_version() -> None:
    text = SPEC.read_text(encoding="utf-8")
    assert "float32" in text and "float64" in text
    assert "MaceModelPrecisionRecord" in text
    assert "MacePrecisionTransitionRecord" in text
    assert "version = \"0.20.140a0\"" in (ROOT / "pyproject.toml").read_text()


def test_architecture_and_stage_plan_bind_precision_to_protocol() -> None:
    architecture = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    plan = (ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.md").read_text()
    assert "MLFF-DATA9A4 selectable MACE precision" in architecture
    assert "MLFF-DATA9A4 - selectable precision implemented" in plan
    assert "mixed floating" in architecture.lower()
