from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/training_data/mlff_data9a5_deployment_artifact_spec.md"
ARCH = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
PLAN = ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.md"


def test_deployment_closure_spec_and_release_version_are_present() -> None:
    text = SPEC.read_text()
    assert 'version: "0.20.43a0"' in text
    assert "downstream runtime owns" in text
    assert "float32-to-float64 promotion does not restore" in text
    assert 'version = "0.20.140a0"' in (ROOT / "pyproject.toml").read_text()


def test_architecture_and_stage_plan_keep_lammps_outside_mdstats_scope() -> None:
    architecture = ARCH.read_text()
    plan = PLAN.read_text()
    assert "does not audit or reproduce LAMMPS" in architecture
    assert "LAMMPS is a downstream consumer" in plan
    assert "MLFF-DATA9A6 - observable ownership bridge implemented in 0.20.44a0" in plan
    assert "MLFF-DATA9A7a - material-profile and atom-group contracts" in plan
    assert "MLFF-DATA9A7e - cross-system qualification" in plan
    assert "MLFF-DATA9A9b - production DATA6--DATA8 materialization - implemented in 0.20.54a0" in plan
