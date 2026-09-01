from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"
GRAPH = ROOT / "docs" / "arch_manuals" / "mlff_training_data_dependency_graph.json"
EVAL_SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_eval_mf_successive_halving_spec.md"
PREC_SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_staged_precision_profiles_spec.md"
STOR_SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_storage_management_spec.md"
STOR2_EVIDENCE = ROOT / "release" / "mlff_stor2_checkpoint_compaction_qualification.json"
STOR3_EVIDENCE = ROOT / "release" / "mlff_stor3_safe_reclamation_qualification.json"
STOR4_EVIDENCE = ROOT / "release" / "mlff_stor4_manual_reclamation_qualification.json"
STOR5_EVIDENCE = ROOT / "release" / "mlff_stor5_archive_deduplication_qualification.json"


def test_eval_precision_storage_roadmap_is_recorded_in_binding_order() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    roadmap = text[text.index("# Post-0.20.105 campaign evaluation, staged-precision, and storage-management roadmap"): ]
    positions = [roadmap.index(f"`{token}`") for token in (
        "EVAL-MF1",
        "EVAL-MF2",
        "PREC1",
        "PREC2",
        "PREC3",
        "STOR1",
        "STOR2",
        "STOR3",
        "STOR4",
        "STOR5",
    )]
    assert positions == sorted(positions)
    assert "EVAL-MF2 - conservative survivor control, diagnostics, and default migration - implemented in 0.20.107a0" in text
    assert "`PREC1` in 0.20.108a0" in text
    assert "The post-0.20.105 evaluation, precision, and storage implementation roadmap is complete." in text
    assert "STOR3 - automatic lifecycle-safe reclamation - implemented in 0.20.114a0" in text
    assert "STOR4 - manual tiered reclamation with capability-loss reporting - implemented in 0.20.115a0" in text
    assert "STOR1 - campaign storage accounting and ownership boundary - implemented in 0.20.111a0" in text
    assert "STOR2 - lossless completed-checkpoint compaction - implemented in 0.20.113a0" in text




def test_staged_precision_plan_records_profiles_and_refine_defaults() -> None:
    text = PREC_SPEC.read_text(encoding="utf-8")
    for token in (
        "`refine`: float64 preparation/foundation, staged float32 -> float64 training",
        "80% of epochs in float32",
        "20% of epochs in float64",
        "24 FP32 and 6 FP64",
        "learning-rate scale `0.5`",
        "15,000 FP64 gradient updates",
        "optimizer, scheduler, and EMA state preserved",
        "inside a live training process",
        "plain `init` still generates `single`",
    ):
        assert token in text


def test_storage_plan_protects_external_inputs_production_and_diagnostics() -> None:
    text = STOR_SPEC.read_text(encoding="utf-8")
    for token in (
        "external\n   directories is read-only",
        "Final selected production models are retained by default",
        "selected production checkpoint is retained by default",
        "Diagnostic text records, logs, training histories",
        "fail-closed under ambiguous ownership",
        "evaluation capsules",
    ):
        assert token in text


def test_dependency_graph_revision_34_contains_eval_precision_storage_nodes() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["schema_version"] == 26
    assert graph["architecture_revision"] == 34
    nodes = {node["id"] for node in graph["nodes"]}
    for node in (
        "NESTED_CHECKPOINT_EVALUATION_PLAN",
        "PARTIAL_CHECKPOINT_PREDICTION_COVERAGE",
        "FULL_FIDELITY_FINALIST_EVALUATION",
        "CAMPAIGN_PRECISION_PROFILE",
        "STAGED_TRAINING_PRECISION_POLICY",
        "PRECISION_STAGE_EXECUTION_PLAN",
        "PRECISION_STAGE_TRANSITION_RECORD",
        "STAGED_PRECISION_QUALIFICATION_RECORD",
        "CAMPAIGN_ARTIFACT_OWNERSHIP_CATALOG",
        "CAMPAIGN_STORAGE_REPORT",
        "CHECKPOINT_EVALUATION_CAPSULE",
        "TIERED_STORAGE_RECLAMATION_PLAN",
        "CAMPAIGN_CLEANUP_MANIFEST",
        "LIFECYCLE_SAFE_RECLAMATION_POLICY",
        "IMMUTABLE_CONTENT_STORE",
        "COLD_ARCHIVE_MANIFEST",
        "COLD_ARCHIVE_RESTORE_RECEIPT",
    ):
        assert node in nodes
    stor4 = next(node for node in graph["nodes"] if node["id"] == "TIERED_STORAGE_RECLAMATION_PLAN")
    assert stor4["implementation_status"] == "implemented"
    assert stor4["implemented_version"] == "0.20.115a0"
    assert stor4["archive_apply_requires"] == "verified COLD_ARCHIVE_MANIFEST"


def test_stor2_real_mace_qualification_records_exact_equivalence_and_savings() -> None:
    payload = json.loads(STOR2_EVIDENCE.read_text(encoding="utf-8"))
    assert payload["schema"] == "mdstats.mlff-stor2-qualification.v1"
    assert payload["runtime_version"] == "0.20.113a0"
    assert payload["architecture_revision"] == 31
    assert payload["backend"] == "e3nn"
    assert payload["verified_exact_model_state"] is True
    assert payload["energy_force_stress_exact_equal"] is True
    assert all(value == 0.0 for value in payload["energy_force_stress_max_abs_difference"].values())
    assert payload["capsule_size_bytes"] < payload["source_checkpoint_size_bytes"]
    assert payload["saved_bytes"] > 0
    assert payload["selected_raw_checkpoint_retained_by_policy"] is True
    assert payload["cueq_runtime_qualified_in_this_gate"] is False


def test_stor3_qualification_records_safe_scope_and_low_disk_ordering() -> None:
    payload = json.loads(STOR3_EVIDENCE.read_text(encoding="utf-8"))
    assert payload["schema"] == "mdstats.mlff-stor3-qualification.v1"
    assert payload["runtime_version"] == "0.20.114a0"
    assert payload["architecture_revision"] == 32
    assert payload["capability_loss"] == []
    assert payload["external_inputs_touched"] is False
    assert payload["scientific_prediction_caches_touched"] is False
    assert payload["selected_production_checkpoint_touched"] is False
    assert payload["low_disk_safe_reclamation_precedes_training_interruption"] is True
    assert payload["cleanup_manifest_append_only"] is True


def test_stor4_qualification_records_manual_tiers_and_protections() -> None:
    payload = json.loads(STOR4_EVIDENCE.read_text(encoding="utf-8"))
    assert payload["schema"] == "mdstats.mlff-stor4-qualification.v1"
    assert payload["runtime_version"] == "0.20.115a0"
    assert payload["architecture_revision"] == 33
    assert payload["tiers"] == ["safe", "cache", "recompute", "compact", "archive"]
    assert payload["consequential_tiers_require_apply"] is True
    assert payload["archive_apply_blocked_until_stor5"] is True
    assert payload["external_inputs_touched"] is False
    assert payload["production_models_touched"] is False
    assert payload["selected_production_checkpoint_touched"] is False
    assert payload["diagnostic_logs_touched"] is False
    assert payload["manual_manifest_records_capability_loss"] is True


def test_stor5_qualification_records_reversible_archive_and_deduplication() -> None:
    payload = json.loads(STOR5_EVIDENCE.read_text(encoding="utf-8"))
    assert payload["schema"] == "mdstats.mlff-stor5-qualification.v1"
    assert payload["runtime_version"] == "0.20.116a0"
    assert payload["architecture_revision"] == 34
    assert payload["deduplication"]["exact_duplicate_hardlink_equal"] is True
    assert payload["archive"]["verified_before_hot_deletion"] is True
    assert payload["archive"]["restore_exact_sha256"] is True
    assert payload["archive"]["corruption_detection_qualified"] is True
    assert payload["security"]["external_inputs_touched"] is False
    assert payload["security"]["production_models_touched"] is False
