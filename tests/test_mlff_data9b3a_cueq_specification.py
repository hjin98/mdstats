from __future__ import annotations

import json
from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/training_data/mlff_data9b3a_cueq_campaign_spec.md"
GUIDE = ROOT / "docs/guides/mlff_campaign_cli_user_guide.md"
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
STAGE = ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
EXAMPLE = ROOT / "campaign.toml.example"


def test_data9b3a_version_and_documented_surface() -> None:
    assert campaign_cli.MLFF_DATA9B3_VERSION == "0.20.99a0"
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (SPEC, GUIDE, MANUAL, STAGE, EXAMPLE)
    )
    for token in (
        "MLFF-DATA9B3A",
        "MaceAccelerationPolicy",
        "MaceAccelerationProbe",
        '[acceleration]',
        'backend = "cueq"',
        "only_cueq = false",
        "enable_cueq",
        "real model smoke",
        "silent fallback",
        "DATA6",
        "DATA8",
        "checkpoint evaluation",
        "bounded NVE verification",
    ):
        assert token in text


def test_data9b3a_dependency_graph_contract() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["schema_version"] == 26
    assert graph["architecture_revision"] == 34
    nodes = {node["id"] for node in graph["nodes"]}
    assert {"MACE_ACCELERATION_POLICY", "MACE_ACCELERATION_PROBE"} <= nodes
    edges = {(edge["from"], edge["to"], edge["type"]) for edge in graph["edges"]}
    assert (
        "CAMPAIGN_CLI_CONFIGURATION",
        "MACE_ACCELERATION_POLICY",
        "source_identity_requires",
    ) in edges
    assert (
        "MACE_ACCELERATION_POLICY",
        "TRAINING_PROTOCOL_IDENTITY",
        "source_identity_requires",
    ) in edges
    assert (
        "MACE_ACCELERATION_PROBE",
        "CAMPAIGN_PREFLIGHT_RECORD",
        "promotion_requires",
    ) in edges
    assert (
        "MACE_ACCELERATION_POLICY",
        "BOUNDED_DEPLOYMENT_VERIFICATION",
        "execution_requires",
    ) in edges
