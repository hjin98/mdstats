from pathlib import Path


def test_data8_specification_contains_required_contracts() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "docs/specs/training_data/mlff_data8_mace_artifacts_spec.md").read_text(encoding="utf-8")
    required = (
        "MaceExtxyzArtifact",
        "ReplayPreparationPlan",
        "TrainingProtocolIdentity",
        "MaceCheckpointControlPolicy",
        "MaceLoaderDryRun",
        "SealedEvaluationArtifact",
        "NATIVE_MACE_FIXED",
        "mace-torch==0.3.16",
        "locked interpolation test",
    )
    for item in required:
        assert item in text
