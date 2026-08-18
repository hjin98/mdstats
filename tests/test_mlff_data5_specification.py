from pathlib import Path


def test_data5_specification_contains_normative_contracts() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "docs/specs/training_data/mlff_data5_partition_roles_spec.md").read_text(encoding="utf-8")
    for token in (
        "PartitionFeasibilityReport",
        "PartitionIndependenceReport",
        "CrossValidationFold",
        "BlindingBoundaryCatalog",
        "LeakageAuditReport",
        "Event detection before thinning",
        "held-out evaluation units never control early stopping",
        "ASE 3.29.0",
    ):
        assert token in text


def test_data5_public_exports_are_available() -> None:
    import mdstats

    assert mdstats.MLFF_DATA5_PARSER_VERSION == "0.20.33a0"
    assert callable(mdstats.build_partition_unit_catalog)
    assert callable(mdstats.assess_partition_feasibility)
    assert callable(mdstats.build_outer_partitions)
    assert callable(mdstats.build_cross_validation_plans)
    assert callable(mdstats.build_data5_partition_bundle)
    assert callable(mdstats.audit_partition_leakage)


def test_data5_architecture_status() -> None:
    root = Path(__file__).resolve().parents[1]
    arch = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text(encoding="utf-8")
    stage = (root / "docs/specs/training_data/mlff_data_stage_plan_spec.md").read_text(encoding="utf-8")
    assert "MLFF-DATA5 is implemented in `0.20.33a0`" in arch
    assert "## MLFF-DATA5 - implemented in 0.20.33a0" in stage
