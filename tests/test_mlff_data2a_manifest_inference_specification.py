from __future__ import annotations

import json
from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/training_data/mlff_data2a_manifest_inference_gate_spec.md"
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
STAGE = ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
EXAMPLE = ROOT / "campaign.toml.example"


def test_data2a_version_public_api_and_documented_contract() -> None:
    assert mdstats.__version__ == "0.20.140a0"
    assert campaign_cli.MLFF_DATA9B3_VERSION == "0.20.99a0"
    assert callable(mdstats.infer_training_manifest_metadata)
    policy = mdstats.ManifestInferencePolicy()
    assert policy.filename_values_at_or_above_one_are_percent is True
    text = "\n".join(path.read_text(encoding="utf-8") for path in (SPEC, MANUAL, STAGE, EXAMPLE))
    for token in (
        "MLFF-DATA2A",
        "ManifestInferencePolicy",
        "ManifestInferenceResult",
        "fixed-cell",
        "right-polar",
        "hydro+5",
        "hydro+0.05",
        "reference_run_id",
        "--refresh-inferences",
        "manifest approval",
    ):
        assert token in text


def test_data2a_dependency_graph_requires_verified_promotion_before_approval() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["schema_version"] == 26
    assert graph["architecture_revision"] == 34
    nodes = {node["id"] for node in graph["nodes"]}
    assert {
        "FILENAME_STRAIN_CANDIDATE",
        "MANIFEST_INFERENCE_POLICY",
        "REVIEW_MANIFEST_INFERENCE_RESULT",
        "VERIFIED_STRAIN_RELATIONSHIP",
    } <= nodes
    edges = {(edge["from"], edge["to"], edge["type"]) for edge in graph["edges"]}
    assert (
        "VERIFIED_STRAIN_RELATIONSHIP",
        "REVIEW_MANIFEST_INFERENCE_RESULT",
        "promotion_requires",
    ) in edges
    assert (
        "REVIEW_MANIFEST_INFERENCE_RESULT",
        "CAMPAIGN_MANIFEST_APPROVAL",
        "promotion_requires",
    ) in edges
    assert (
        "VERIFIED_STRAIN_RELATIONSHIP",
        "REFERENCE_CELL",
        "execution_requires",
    ) in edges
