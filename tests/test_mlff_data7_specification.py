from pathlib import Path


def test_data7_specification_contains_normative_contracts() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "docs/specs/training_data/mlff_data7_fitted_metrics_selection_spec.md").read_text(encoding="utf-8")
    for token in (
        "FeatureFitDomain",
        "FittedFeatureMetric",
        "AtomicReferenceFitRecord",
        "TrainingObjectivePolicy",
        "CheckpointMetricPolicy",
        "SelectionBudgetPolicy",
        "TrainingSelectionPlan",
        "SelectionCoverageReport",
        "locked test",
        "ASE 3.29.0",
    ):
        assert token in text


def test_data7_public_exports_are_available() -> None:
    import mdstats

    assert mdstats.MLFF_DATA7_PARSER_VERSION == "0.20.64a0"
    assert callable(mdstats.build_feature_fit_domains)
    assert callable(mdstats.fit_feature_metric)
    assert callable(mdstats.fit_atomic_reference_energies)
    assert callable(mdstats.build_training_weight_catalog)
    assert callable(mdstats.build_training_selection_plan)
    assert callable(mdstats.build_data7_preparation_bundle)


def test_data7_architecture_status() -> None:
    root = Path(__file__).resolve().parents[1]
    arch = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text(encoding="utf-8")
    stage = (root / "docs/specs/training_data/mlff_data_stage_plan_spec.md").read_text(encoding="utf-8")
    assert "MLFF-DATA7 is implemented in `0.20.35a0`" in arch
    assert "## MLFF-DATA7 - implemented in 0.20.35a0" in stage
