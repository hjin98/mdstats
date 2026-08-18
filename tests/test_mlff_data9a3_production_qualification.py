from pathlib import Path
import pytest
import mdstats
from mdstats.training_data._common import digest
from mdstats.training_data.production_qualification import _artifact_digest


def _d(name: str) -> str:
    return digest({"name": name})


def test_production_resource_and_gate_record_round_trip() -> None:
    resource = mdstats.ProductionStageResourceRecord(
        stage="data5_partition_feasibility",
        wall_seconds=1.5,
        peak_rss_mib=20.0,
        output_size_bytes=42,
        notes=("measured",),
    )
    assert mdstats.ProductionStageResourceRecord.from_dict(resource.to_dict()) == resource
    record = mdstats.ProductionCorpusQualificationRecord(
        production_plan_digest=_d("production-plan"),
        dataset_id="bulk-lta",
        expected_source_count=1,
        source_count=1,
        total_frame_count=10,
        normalization_manifest_digest=_d("normalization"),
        reference_manifest_digest=_d("reference"),
        run_evidence_digest=_d("runs"),
        source_catalog_digest=_d("sources"),
        frame_catalog_digest=_d("frames"),
        data4_bundle_digest=_d("data4"),
        data5_bundle_digest=_d("data5"),
        data6_bundle_digest=None,
        data7_bundle_digests=(),
        data8_bundle_digest=None,
        eligible_frame_count=10,
        degraded_frame_count=0,
        rejected_frame_count=0,
        unresolved_strain_frame_count=0,
        duplicate_geometry_group_count=0,
        duplicate_labeled_group_count=0,
        composition_formulas=("AlNaO4Si",),
        target_temperatures_kelvin=(700.0,),
        ensembles=("NVT",),
        strain_class_counts=(("unstrained", 10),),
        feasibility_outcomes=(("supported_with_temporal_blocks_only", 1),),
        independence_grade_counts=(("insufficient_independence", 1),),
        event_type_counts=(("force_threshold", 2),),
        partition_unit_count=4,
        condition_count=1,
        cross_validation_fold_count=3,
        leakage_audit_passed=True,
        profile_extension_coverage_materialized=False,
        foundation_features_materialized=False,
        foundation_residual_e0_materialized=False,
        data8_artifacts_materialized=False,
        replay_corpus_bound=False,
        target_corpus_qualified=True,
        full_data9a_passed=False,
        status=mdstats.ProductionGateStatus.CONDITIONALLY_READY,
        blockers=("production_replay_corpus_not_bound",),
        warnings=("data5_weak_independence_evidence:insufficient_independence",),
        resource_records=(resource,),
    )
    assert mdstats.ProductionCorpusQualificationRecord.from_dict(record.to_dict()) == record


def test_verified_digest_avoids_large_artifact_rehash() -> None:
    class Artifact:
        @property
        def content_digest(self):
            raise AssertionError("large artifact was unexpectedly re-hashed")

    value = _d("verified")
    assert _artifact_digest(Artifact(), value, name="verified") == value
    with pytest.raises(mdstats.TrainingDataInputError):
        _artifact_digest(None, value, name="verified")


def test_data5_uses_indexed_strain_lookup() -> None:
    text = (Path(__file__).resolve().parents[1] / "mdstats/training_data/partition.py").read_text()
    assert "strain_by_uid = {item.frame_uid: item" in text
    assert "strain_record=strain_by_uid[frame.frame_uid]" in text
    assert "next(item for item in frame_catalog.strain_records" not in text


def test_public_data9a3_api_is_exported() -> None:
    assert callable(mdstats.build_production_corpus_qualification_record)
    assert mdstats.MLFF_DATA9A3_PARSER_VERSION == "0.20.55a0"
