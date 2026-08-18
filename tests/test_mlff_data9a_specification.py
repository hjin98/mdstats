from __future__ import annotations

import json
from pathlib import Path

import mdstats


ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"
STAGE = ROOT / "docs" / "specs" / "training_data" / "mlff_data_stage_plan_spec.md"
SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_data9a_integration_qualification_spec.md"
GRAPH = ROOT / "docs" / "arch_manuals" / "mlff_training_data_dependency_graph.json"


def test_data9a_runtime_specification_is_canonical() -> None:
    assert 'version = "0.20.140a0"' in (ROOT / "pyproject.toml").read_text()
    architecture = ARCH.read_text()
    stage = STAGE.read_text()
    specification = SPEC.read_text()
    for required in (
        "MaceDependencyManifest",
        "MaceRuntimeEnvironmentRecord",
        "MaceCliSmokeRecord",
        "e3nn==0.4.4",
        "opt-einsum-fx>=0.1.4",
        "never inserts dependency stubs",
    ):
        assert required in architecture or required in stage or required in specification
    assert "DATA9A remains incomplete" in architecture
    assert "DATA9B remains gated" in stage


def test_data9a_dependency_graph_contains_runtime_qualification_chain() -> None:
    graph = json.loads(GRAPH.read_text())
    nodes = {
        node if isinstance(node, str) else node.get("id") or node.get("name")
        for node in graph["nodes"]
    }
    for required in (
        "MACE_DEPENDENCY_MANIFEST",
        "OFFLINE_MACE_WHEELHOUSE",
        "MACE_RUNTIME_ENVIRONMENT_RECORD",
        "MACE_CLI_SMOKE_RECORD",
    ):
        assert required in nodes


def test_mdstats_declares_packaging_for_version_specifier_validation() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert '"packaging>=23"' in pyproject
