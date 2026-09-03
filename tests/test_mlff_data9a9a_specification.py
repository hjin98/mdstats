from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/training_data/mlff_data9a9a_production_model_sweep_spec.md"
DATA6_SPEC = ROOT / "docs/specs/training_data/mlff_data6_selection_descriptors_spec.md"
ARCH = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
STAGE = ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.md"
INDEX = ROOT / "docs/specs/training_data/README.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
SMOKE = ROOT / "release/mlff_data9a9a_real_mpa0_restart_smoke.json"


def test_data9a9a_specification_freezes_restart_and_scope() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "MLFF-DATA9A9a",
        "Data6ModelSweepPlan",
        "AtomicModelPredictionManifest",
        "Data6ModelSweepCheckpoint",
        "exact DATA5-authorized",
        "atomic",
        "corruption",
        "resume",
        "DATA9A9b",
        "does not fit DATA7",
    ):
        assert token in text


def test_data6_and_architecture_mark_data9a9a_implemented() -> None:
    data6 = DATA6_SPEC.read_text(encoding="utf-8")
    arch = ARCH.read_text(encoding="utf-8")
    stage = STAGE.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    assert "DATA6 schema v5" in data6
    assert "DATA9A9a" in data6
    assert "DATA9A9a in 0.20.53a0" in arch
    assert "MLFF-DATA9A9a - restartable checkpoint-bound DATA6 model sweep - implemented in 0.20.53a0" in stage
    assert "DATA9A9a restartable checkpoint-bound production DATA6 model sweeps" in index


def test_dependency_graph_contains_restartable_model_sweep_chain() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["schema_version"] == 26
    assert graph["architecture_revision"] == 34
    nodes = {node["id"] for node in graph["nodes"]}
    required = {
        "DATA6_MODEL_SWEEP_EXECUTION_POLICY",
        "DATA6_MODEL_SWEEP_PLAN",
        "DATA6_MODEL_SWEEP_CHECKPOINT",
        "ATOMIC_MODEL_PREDICTION_MANIFEST",
    }
    assert required <= nodes
    edges = {(edge["from"], edge["to"]) for edge in graph["edges"]}
    assert ("OUTER_PARTITION", "DATA6_MODEL_SWEEP_PLAN") in edges
    assert ("DATA6_MODEL_SWEEP_PLAN", "DATA6_MODEL_SWEEP_CHECKPOINT") in edges
    assert ("DATA6_MODEL_SWEEP_CHECKPOINT", "MACE_RAW_DESCRIPTORS") in edges
    assert ("DATA6_MODEL_SWEEP_CHECKPOINT", "ATOMIC_MODEL_PREDICTION_MANIFEST") in edges
    assert ("ATOMIC_MODEL_PREDICTION_MANIFEST", "BLINDED_EVALUATION_PREDICTIONS") in edges


def test_public_runtime_exports_data9a9a_contracts() -> None:
    assert mdstats.MLFF_DATA6_PARSER_VERSION == "0.20.53a0"
    assert mdstats.MLFF_DATA9A9A_VERSION
    assert mdstats.Data6ModelSweepPlan
    assert mdstats.Data6ModelSweepCheckpoint
    assert mdstats.AtomicModelPredictionManifest
    assert callable(mdstats.run_restartable_data6_model_sweep)
    assert callable(mdstats.load_data6_model_sweep_artifacts)


def test_real_mpa0_restart_smoke_is_valid_and_bounded() -> None:
    payload = json.loads(SMOKE.read_text(encoding="utf-8"))
    assert payload["checkpoint_sha256"] == "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638"
    assert payload["source_frame_count"] == 1400
    assert payload["requested_frame_count"] == 1380
    assert payload["completed_after_resume"] == 2
    assert payload["descriptor_shapes"] == [[168, 256], [168, 256]]
    assert payload["prediction_force_shapes"] == [[168, 3], [168, 3]]
    assert payload["status"] == "incomplete"
