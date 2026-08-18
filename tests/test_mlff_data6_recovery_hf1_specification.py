from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import mdstats
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]


def test_data6_recovery_hf1_release_graph_and_runtime_import() -> None:
    assert mdstats.__version__ == "0.20.209a0"
    assert campaign_cli.np is np
    graph = json.loads(
        (ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text()
    )
    assert graph["architecture_revision"] == 76
    assert graph["schema_version"] == 58
    nodes = {node["id"]: node for node in graph["nodes"]}
    node = nodes["DATA6_RECOVERY_HF1_NUMPY_IMPORT"]
    assert node["implemented_version"] == "0.20.195a0"
    assert node["scientific_identity_changed"] is False
    assert node["selection_identity_changed"] is False
    assert node["acceleration_policy_changed"] is False


def test_data6_recovery_hf1_documentation_is_synchronized() -> None:
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (ROOT / "docs/specs/training_data/mlff_data6_recovery_hf1_spec.md").read_text()
    patch = (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.195a0.md").read_text()
    note = (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV62.md").read_text()
    combined = manual + spec + patch + note
    for token in (
        "DATA6-RECOVERY-HF1",
        "np.linspace",
        "import numpy as np",
        "NameError",
        "scientific",
    ):
        assert token in combined
