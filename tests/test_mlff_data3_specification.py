from pathlib import Path


def test_data3_specification_and_architecture_status() -> None:
    root = Path(__file__).resolve().parents[1]
    spec = root / "docs/specs/training_data/mlff_data3_frame_conditions_spec.md"
    text = spec.read_text(encoding="utf-8")
    for token in (
        "FrameData",
        "geometry_fingerprint",
        "label_payload_digest",
        "FrameEligibilityDecision",
        "TemperatureConditionRecord",
        "ReferenceCellCatalog",
        "deformation gradient",
        "non-symmetric engineering shear",
    ):
        assert token in text


def test_data3_public_exports_are_available() -> None:
    import mdstats

    assert mdstats.MLFF_DATA3_PARSER_VERSION == "0.20.31a0"
    assert callable(mdstats.build_training_frame_catalog)
    assert callable(mdstats.build_vasp_training_frame_catalog)
    assert callable(mdstats.source_occurrence_signature)
    assert callable(mdstats.compute_frame_strain)
