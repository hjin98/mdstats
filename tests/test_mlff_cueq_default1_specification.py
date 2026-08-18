from __future__ import annotations

import json
from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]


def test_cueq_default1_release_and_generated_policy() -> None:
    assert tuple(int(v) for v in mdstats.__version__.split("a",1)[0].split(".")) >= (0, 20, 209)
    text = campaign_cli._config_template(
        workspace="work", training_root="training", foundation_model="mace-mh-1.model",
        replay_train="replay_train.xyz", replay_monitor="replay_monitor.xyz",
    )
    assert 'backend = "e3nn"' in text
    assert 'training_backend = "cueq"' in text
    assert 'only_cueq = false' in text


def test_cueq_default1_documentation_and_graph() -> None:
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["architecture_revision"] >= 76
    assert graph["schema_version"] >= 58
    nodes = {node["id"]: node for node in graph["nodes"]}
    node = nodes["CUEQ_DEFAULT1_TRAINING_DEFAULT_POLICY"]
    assert node["implemented_version"] == "0.20.193a0"
    assert node["source_backend_default"] == "e3nn"
    assert node["training_backend_default"] == "cueq"
    assert node["source_cueq_execution_authorized_by_default"] is False
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (ROOT / "docs/specs/training_data/mlff_cueq_train_default1_policy_migration_spec.md").read_text()
    patch = (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.193a0.md").read_text()
    for token in ("CUEQ-DEFAULT1", 'training_backend = "cueq"', "TrainingAccelerationRealizationRecord.v1", "silent fallback"):
        assert token in manual + spec + patch


def test_foundation_config_contract_freezes_both_acceleration_phases() -> None:
    payload = campaign_cli._foundation_configuration_contract({
        "foundation": {"family": "mace_mh_1", "head": "omat_pbe"},
        "acceleration": {"backend": "e3nn", "training_backend": "cueq", "only_cueq": False, "require_available": True},
    })
    assert payload["schema"] == "mdstats.mlff-foundation-config-contract.v2"
    assert payload["source_backend"] == "e3nn"
    assert payload["training_backend"] == "cueq"
    assert payload["phase_separated"] is True
