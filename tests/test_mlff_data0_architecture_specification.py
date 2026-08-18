from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"
MANUAL_PDF = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.pdf"
GRAPH = ROOT / "docs" / "arch_manuals" / "mlff_training_data_dependency_graph.json"
SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_data_stage_plan_spec.md"
SPEC_PDF = ROOT / "docs" / "specs" / "training_data" / "mlff_data_stage_plan_spec.pdf"
PYPROJECT = ROOT / "pyproject.toml"


def test_mlff_data0_manual_freezes_core_contracts() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    for token in (
        "MLFF-DATA0",
        "fold_checkpoint_monitor_k",
        "PartitionFeasibilityReport",
        "AtomicReferenceIdentifiabilityReport",
        "AtomicReferenceFitRecord",
        "geometry_fingerprint",
        "label_payload_digest",
        "FeatureMetricPolicyTemplate",
        "FoldFeatureMetricFit",
        "SelectionBudgetPolicy",
        "TrainingObjectivePolicy",
        "CheckpointMetricPolicy",
        "TrainingProtocolIdentity",
        "MaceCheckpointControlPolicy",
        "MaceExposureRealizationRecord",
        "NATIVE_TARGET_LAST_WITH_EXTERNAL_CONSTRAINT_AUDIT",
        "NATIVE_MACE_FIXED",
        "TrainingDifficultyFeatureCatalog",
        "BlindedEvaluationPredictionCatalog",
        "CalibrationApplicabilityDomain",
        "ProtocolFreezeRecord",
        "sealed_evaluation_bundle",
        "append-only role inheritance",
        "CandidateAdmissibilityDecision",
        "mace-torch==0.3.16",
        "real_pt_data_ratio_threshold",
        "Reviews* **124**",
        "13681-13714",
    ):
        assert token in text
    for prohibited in (
        "rotating_inner_crossfit",
        "Rotating inner cross-fit",
        "test_file: target_test.xyz",
        "E0s: fold_or_final_fit_record",
        "POST_FREEZE_EVALUATION_BUNDLE",
        "## Supported training-only modes",
    ):
        assert prohibited not in text


def test_mlff_data0_stage_spec_freezes_protocol_and_evidence_separation() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "No public runtime object is implemented at MLFF-DATA0",
        "mdstats core has no mandatory MACE",
        "Cross-validation SHALL train one fresh model",
        "Cross-validation SHALL be bound to the complete `TrainingProtocolIdentity`",
        "A held-out evaluation fold SHALL NOT control stopping",
        "Locked tests SHALL NOT affect",
        "The first MACE adapter SHALL support one target label domain",
        "The first adapter SHALL support only `NATIVE_MACE_FIXED`",
        "MACE 0.3.16 uses the last validation head",
        "real_pt_data_ratio_threshold",
        "CalibrationApplicabilityDomain",
        "public placeholder before its specification",
    ):
        assert token in text


def test_mlff_data0_dependency_graph_is_acyclic_and_has_forbidden_edges() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["branch"] == "MLFF-DATA"
    assert graph["architecture_revision"] == 34
    assert graph["documentation_gate"] == "MLFF-DATA0"
    assert graph["schema_version"] == 26

    node_ids = {node["id"] for node in graph["nodes"]}
    assert len(node_ids) == len(graph["nodes"])
    required_nodes = {
        "PARTITION_FEASIBILITY_REPORT",
        "MATERIAL_PROFILE_IDENTITY",
        "ATOM_GROUP_CATALOG",
        "CONDITION_AXIS_CATALOG",
        "INDEPENDENCE_AXIS_CATALOG",
        "SELECTION_FEATURE_CATALOGS",
        "PROFILE_EVENT_CATALOGS",
        "LTA_PROFILE_EXTENSION",
        "OBSERVABLE_ANALYSIS_RECIPE",
        "OBSERVABLE_COLLECTION_IDENTITIES",
        "TRAJECTORY_GENERATION_IDENTITIES",
        "OBSERVABLE_VALIDATION_ACTIVATION_RECORD",
        "OBSERVABLE_RESULT_IDENTITIES",
        "OBSERVABLE_VALIDATION_EVIDENCE",
        "LOCKED_TEST_OBSERVABLE_EVIDENCE",
        "OBSERVABLE_COMPARISON_POLICY",
        "OBSERVABLE_COMPARISON_RESULT",
        "OBSERVABLE_ACCEPTANCE_DECISION",
        "THERMOMECHANICAL_VALIDATION_RECIPES",
        "MACE_RAW_DESCRIPTORS",
        "FOLD_TRAINING_DIFFICULTY_FEATURES",
        "FEATURE_METRIC_POLICY_TEMPLATE",
        "FOLD_FEATURE_METRIC_FITS",
        "FINAL_FEATURE_METRIC_FIT",
        "SELECTION_BUDGET_POLICY",
        "TRAINING_OBJECTIVE_POLICY",
        "CHECKPOINT_METRIC_POLICY",
        "TRAINING_PROTOCOL_IDENTITY",
        "MACE_CHECKPOINT_CONTROL_POLICY",
        "MACE_EXPOSURE_REALIZATION_RECORD",
        "PROTOCOL_FREEZE_RECORD",
        "SEALED_EVALUATION_BUNDLE",
        "EVALUATION_ACTIVATION_DECISION",
        "CALIBRATION_APPLICABILITY_DOMAIN",
        "CALIBRATION_TRANSFER_DECISION",
        "MACE_DEPLOYMENT_EXPORT_POLICY",
        "MACE_INFERENCE_COMPARISON",
        "MACE_DEPLOYMENT_ARTIFACT",
    }
    assert required_nodes <= node_ids

    adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    edge_pairs: set[tuple[str, str]] = set()
    for edge in graph["edges"]:
        assert edge["from"] in node_ids
        assert edge["to"] in node_ids
        adjacency[edge["from"]].add(edge["to"])
        edge_pairs.add((edge["from"], edge["to"]))

    temporary: set[str] = set()
    permanent: set[str] = set()

    def visit(node: str) -> None:
        if node in permanent:
            return
        assert node not in temporary, f"cycle detected at {node}"
        temporary.add(node)
        for child in adjacency[node]:
            visit(child)
        temporary.remove(node)
        permanent.add(node)

    for node_id in sorted(node_ids):
        visit(node_id)

    locked_forbidden = {
        "FOLD_LOCAL_TRANSFORMS",
        "FOLD_FEATURE_METRIC_FITS",
        "FOLD_ATOMIC_REFERENCE_FITS",
        "FOLD_TRAINING_DIFFICULTY_FEATURES",
        "FOLD_LOCAL_SELECTIONS",
        "FINAL_FEATURE_TRANSFORM",
        "FINAL_FEATURE_METRIC_FIT",
        "FINAL_ATOMIC_REFERENCE_FIT",
        "FINAL_TRAINING_DIFFICULTY_FEATURES",
        "FINAL_SELECTION_MASTER_ORDER",
        "TRAINING_PROTOCOL_IDENTITY",
        "CHECKPOINT_SELECTION_DECISION",
        "UNCERTAINTY_CALIBRATION",
        "ACQUISITION_DECISIONS",
    }
    for source in ("LOCKED_INTERPOLATION_TEST", "LOCKED_CHALLENGE_TESTS"):
        assert not any((source, target) in edge_pairs for target in locked_forbidden)

    assert ("PARTITION_ROLE_BUDGET_POLICY", "PARTITION_FEASIBILITY_REPORT") in edge_pairs
    assert ("PARTITION_FEASIBILITY_REPORT", "OUTER_PARTITION") in edge_pairs
    assert ("TRAINING_PROTOCOL_IDENTITY", "CROSS_VALIDATION_JOB_FAMILY") in edge_pairs
    assert ("REPLAY_PLAN", "TRAINING_PROTOCOL_IDENTITY") in edge_pairs
    assert ("MACE_EXPOSURE_REALIZATION_RECORD", "CHECKPOINT_SELECTION_DECISION") in edge_pairs
    assert ("TRAINED_COMMITTEE", "PROTOCOL_FREEZE_RECORD") in edge_pairs
    assert ("SEALED_EVALUATION_BUNDLE", "EVALUATION_ACTIVATION_DECISION") in edge_pairs
    assert ("CALIBRATION_APPLICABILITY_DOMAIN", "CALIBRATION_TRANSFER_DECISION") in edge_pairs
    assert ("CALIBRATION_TRANSFER_DECISION", "ACQUISITION_DECISIONS") in edge_pairs
    assert ("MATERIAL_PROFILE_IDENTITY", "SELECTION_FEATURE_CATALOGS") in edge_pairs
    assert ("ATOM_GROUP_CATALOG", "SELECTION_FEATURE_CATALOGS") in edge_pairs
    assert ("LTA_PROFILE_EXTENSION", "OPTIONAL_PROFILE_EXTENSION_PROVIDER") in edge_pairs
    assert ("OPTIONAL_PROFILE_EXTENSION_PROVIDER", "PROFILE_SELECTION_FEATURE_CATALOGS") in edge_pairs
    assert ("PROFILE_SELECTION_FEATURE_CATALOGS", "SELECTION_FEATURE_CATALOGS") in edge_pairs
    assert ("OBSERVABLE_ANALYSIS_RECIPE", "OBSERVABLE_VALIDATION_EVIDENCE") in edge_pairs
    assert ("OBSERVABLE_COLLECTION_IDENTITIES", "OBSERVABLE_VALIDATION_EVIDENCE") in edge_pairs
    assert ("TRAJECTORY_GENERATION_IDENTITIES", "OBSERVABLE_VALIDATION_EVIDENCE") in edge_pairs
    assert ("OBSERVABLE_COMPARISON_POLICY", "OBSERVABLE_VALIDATION_ACTIVATION_RECORD") in edge_pairs
    assert ("OBSERVABLE_VALIDATION_ACTIVATION_RECORD", "OBSERVABLE_VALIDATION_EVIDENCE") in edge_pairs
    assert ("OBSERVABLE_VALIDATION_EVIDENCE", "OBSERVABLE_COMPARISON_RESULT") in edge_pairs
    assert ("OBSERVABLE_COMPARISON_POLICY", "OBSERVABLE_COMPARISON_RESULT") in edge_pairs
    assert ("OBSERVABLE_COMPARISON_RESULT", "OBSERVABLE_ACCEPTANCE_DECISION") in edge_pairs
    assert ("OBSERVABLE_VALIDATION_EVIDENCE", "LOCKED_TEST_OBSERVABLE_EVIDENCE") in edge_pairs
    assert ("OBSERVABLE_VALIDATION_EVIDENCE", "OBSERVABLE_COMPARISON_POLICY") not in edge_pairs

    optional = {
        (edge["from"], edge["to"])
        for edge in graph["edges"]
        if edge["type"] == "optional_enrichment"
    }
    assert ("LTA_PROFILE_EXTENSION", "OPTIONAL_PROFILE_EXTENSION_PROVIDER") in optional
    assert ("OPTIONAL_PROFILE_EXTENSION_PROVIDER", "PROFILE_PARTITION_FEATURE_CATALOGS") in optional
    assert ("PROFILE_PARTITION_FEATURE_CATALOGS", "PARTITION_CRITICAL_PROFILE_FEATURES") in optional
    assert ("OPTIONAL_PROFILE_EXTENSION_PROVIDER", "PROFILE_SELECTION_FEATURE_CATALOGS") in optional
    assert ("PROFILE_SELECTION_FEATURE_CATALOGS", "SELECTION_FEATURE_CATALOGS") in optional


def test_mlff_data0_stage_order_is_canonical() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    positions = [text.index(f"## MLFF-DATA{i} -") for i in range(1, 12)]
    assert positions == sorted(positions)
    assert text.index("## MLFF-DATA4 -") < text.index("## MLFF-DATA5 -")
    assert text.index("## MLFF-DATA5 -") < text.index("## MLFF-DATA6 -")
    assert text.index("## MLFF-DATA6 -") < text.index("## MLFF-DATA7 -")
    assert text.index("## MLFF-DATA8 -") < text.index("## MLFF-DATA9 -")


def test_mlff_data0_record_contract_keeps_frame_facts_policy_independent() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    frame_section = text.split("## Frame facts", 1)[1].split("## Decision records", 1)[0]
    fields = frame_section.split("```text", 1)[1].split("```", 1)[0].lower()
    for forbidden_field in (
        "eligibility_state",
        "partition_role",
        "selection_reason",
        "exposure",
        "acquisition",
    ):
        assert forbidden_field not in fields
    for required_field in (
        "geometry_fingerprint",
        "label_payload_digest",
        "labeled_configuration_fingerprint",
    ):
        assert required_field in fields


def test_locked_tests_are_operationally_sealed_in_manual() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    bundle = text.split("## Separated development, calibration, and evaluation artifacts", 1)[1].split(
        "## Explicit E0 serialization", 1
    )[0]
    development = bundle.split("development_bundle/", 1)[1].split("calibration_bundle/", 1)[0]
    assert "target_test.xyz" not in development
    assert "target_test.xyz" in bundle
    assert "ProtocolFreezeRecord" in bundle
    assert "EVALUATION_ACTIVATION" not in development


def test_strain_and_mace_runtime_contracts_are_explicit() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    strain = text.split("## Strain tensor", 1)[1].split("## Hierarchical condition schemas", 1)[0]
    assert "ASE stores the three lattice vectors" in strain
    assert "\\left(\\mathbf H_0^{-1}\\mathbf H_t\\right)^T" in strain
    assert "nonsymmetric shear" in strain
    replay = text.split("## MACE checkpoint-control policy", 1)[1].split("## Exposure diagnostic", 1)[0]
    assert "last" in replay
    assert "retention of every evaluation checkpoint" in replay
    assert "fail closed" in replay


def test_mlff_data0_pdf_and_version_artifacts_exist() -> None:
    assert MANUAL_PDF.stat().st_size > 10_000
    assert SPEC_PDF.stat().st_size > 5_000
    assert 'version = "0.20.140a0"' in PYPROJECT.read_text(encoding="utf-8")
