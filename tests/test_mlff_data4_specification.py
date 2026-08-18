from pathlib import Path


def test_data4_specification_tokens_and_status() -> None:
    root = Path(__file__).resolve().parents[1]
    spec = root / "docs/specs/training_data/mlff_data4_raw_features_events_spec.md"
    text = spec.read_text(encoding="utf-8")
    for token in (
        "RawFeatureCatalog",
        "LtaPartitionFeatureCatalog",
        "FullResolutionEventCatalog",
        "PartitionRoleBudgetPolicy",
        "Event detection before thinning",
        "ASE 3.29.0",
        "FeatureCacheManifest",
    ):
        assert token in text


def test_data4_public_exports_are_available() -> None:
    import mdstats

    assert mdstats.MLFF_DATA4_PARSER_VERSION == "0.20.32a0"
    assert callable(mdstats.build_raw_feature_catalog)
    assert callable(mdstats.build_lta_partition_feature_catalog)
    assert callable(mdstats.detect_full_resolution_events)
    assert callable(mdstats.build_data4_feature_bundle)
    assert callable(mdstats.build_vasp_data4_feature_bundle)
    assert callable(mdstats.write_data4_feature_cache)
    assert callable(mdstats.read_data4_feature_cache)


def test_data4_architecture_status() -> None:
    root = Path(__file__).resolve().parents[1]
    arch = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text(encoding="utf-8")
    stage = (root / "docs/specs/training_data/mlff_data_stage_plan_spec.md").read_text(encoding="utf-8")
    assert "MLFF-DATA4 is implemented in `0.20.32a0`" in arch
    assert "## MLFF-DATA4 - implemented in 0.20.32a0" in stage
