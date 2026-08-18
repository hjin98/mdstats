from pathlib import Path


def test_data6_specification_contains_normative_contracts() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "docs/specs/training_data/mlff_data6_selection_descriptors_spec.md").read_text(encoding="utf-8")
    for token in (
        "ProfileFeatureCatalog",
        "Data6ModelSweepPlan",
        "AtomicModelPredictionManifest",
        "ModelCheckpointIdentity",
        "MaceDescriptorManifest",
        "TrainingDifficultyFeatureCatalog",
        "BlindedEvaluationPredictionCatalog",
        "locked test",
        "training domain",
        "ASE 3.29.0",
    ):
        assert token in text


def test_data6_public_exports_are_available() -> None:
    import mdstats

    assert mdstats.MLFF_DATA6_PARSER_VERSION == "0.20.53a0"
    assert callable(mdstats.build_lta_selection_feature_catalog)
    assert callable(mdstats.build_mace_descriptor_manifest)
    assert callable(mdstats.build_training_difficulty_feature_catalog)
    assert callable(mdstats.build_blinded_evaluation_prediction_catalog)
    assert callable(mdstats.build_data6_feature_bundle)


def test_data6_architecture_status() -> None:
    root = Path(__file__).resolve().parents[1]
    arch = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text(encoding="utf-8")
    stage = (root / "docs/specs/training_data/mlff_data_stage_plan_spec.md").read_text(encoding="utf-8")
    assert "MLFF-DATA6 is implemented in `0.20.34a0`" in arch
    assert "## MLFF-DATA6 - implemented in 0.20.34a0" in stage
