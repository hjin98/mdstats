from __future__ import annotations

import copy
import time
from pathlib import Path

import numpy as np
import pytest

from mdstats.training_data._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
)
from mdstats.training_data.performance_baseline import (
    PERF_BASE0_VERSION,
    PerfBase0ArrayReference,
    PerfBase0ArtifactIdentity,
    PerfBase0CorpusIdentity,
    PerfBase0ExecutionTelemetry,
    PerfBase0JsonReference,
    PerfBase0Record,
    PerfBase0ScientificStage,
    PerfBase0StageMeter,
    assert_perf_base0_scientific_equivalence,
    compare_perf_base0_records,
    read_perf_base0_record,
    write_perf_base0_record,
)


def _telemetry(*, wall: float, measured_at: str = "2026-08-15T12:00:00Z") -> PerfBase0ExecutionTelemetry:
    return PerfBase0ExecutionTelemetry.build(
        stage_id="stage",
        measured_at_utc=measured_at,
        wall_seconds=wall,
        process_cpu_seconds=wall * 1.5,
        rss_start_bytes=100,
        rss_end_bytes=120,
        sampled_peak_rss_bytes=150,
        process_peak_rss_bytes=200,
        temporary_array_bytes=64,
        read_bytes=10,
        write_bytes=20,
        read_characters=30,
        written_characters=40,
        throughput_count=10,
        throughput_unit="items",
        worker_settings={"workers": 2},
        environment={"host": "test"},
    )


def _record(
    *,
    values: np.ndarray | None = None,
    source_version: str = "0.20.178a0",
    created_at: str = "2026-08-15T12:00:00Z",
    wall: float = 2.0,
) -> PerfBase0Record:
    array = np.array([1.0, 2.0, 3.0], dtype=np.float64) if values is None else values
    artifact = PerfBase0ArtifactIdentity(
        logical_path="target/input.dat",
        role="test",
        byte_count=3,
        sha256=digest("abc"),
    )
    corpus = PerfBase0CorpusIdentity.build(
        corpus_id="corpus",
        role="test corpus",
        selection_rule="complete",
        artifacts=(artifact,),
        frame_count=3,
        atom_count=9,
        source_unit_count=1,
        metadata={"a": 1},
    )
    stage = PerfBase0ScientificStage(
        stage_id="stage",
        algorithm_ids=("exact",),
        corpus_digests=(corpus.content_digest,),
        policy_digests=(digest({"policy": 1}),),
        subset_rule="complete",
        arrays=(PerfBase0ArrayReference.from_array("values", array),),
        json_references=(PerfBase0JsonReference.from_value("order", ["b", "a"]),),
    )
    return PerfBase0Record(
        baseline_id="baseline",
        source_version=source_version,
        created_at_utc=created_at,
        authority_status="bounded",
        source_artifacts=(),
        corpora=(corpus,),
        scientific_stages=(stage,),
        execution_telemetry=(_telemetry(wall=wall, measured_at=created_at),),
        limitations=("test limitation",),
    )


def test_array_reference_canonicalizes_endian_and_detects_exact_bytes() -> None:
    native = PerfBase0ArrayReference.from_array("x", np.array([1.0, -0.0, 3.5], dtype=np.float64))
    big_endian = PerfBase0ArrayReference.from_array("x", np.array([1.0, -0.0, 3.5], dtype=">f8"))
    assert native.dtype == "<f8"
    assert big_endian.dtype == "<f8"
    assert native.value_sha256 == big_endian.value_sha256
    changed = PerfBase0ArrayReference.from_array("x", np.array([1.0, 0.0, 3.5], dtype=np.float64))
    assert changed.value_sha256 != native.value_sha256


def test_scientific_digest_excludes_telemetry_and_source_release() -> None:
    reference = _record()
    candidate = _record(
        source_version="0.20.179a0",
        created_at="2026-08-16T01:02:03Z",
        wall=1.0,
    )
    assert reference.scientific_digest == candidate.scientific_digest
    assert reference.execution_digest != candidate.execution_digest
    assert reference.content_digest != candidate.content_digest
    comparison = assert_perf_base0_scientific_equivalence(reference, candidate)
    assert comparison.scientific_match
    assert comparison.performance["stage"]["wall_ratio_candidate_over_reference"] == pytest.approx(0.5)


def test_comparison_detects_scientific_array_change() -> None:
    reference = _record()
    candidate = _record(values=np.array([1.0, 2.0, 4.0]))
    comparison = compare_perf_base0_records(reference, candidate)
    assert not comparison.scientific_match
    assert comparison.mismatches == ("stage_digest_mismatch:stage",)
    with pytest.raises(TrainingDataInputError, match="scientific equivalence failed"):
        assert_perf_base0_scientific_equivalence(reference, candidate)


def test_record_round_trip_and_nested_tamper_fail_closed(tmp_path: Path) -> None:
    record = _record()
    path = write_perf_base0_record(tmp_path / "perf-base0.json", record)
    restored = read_perf_base0_record(path)
    assert restored.content_digest == record.content_digest
    assert restored.to_dict() == record.to_dict()

    payload = copy.deepcopy(record.to_dict())
    payload["scientific_stages"][0]["arrays"][0]["maximum"] = 99.0
    with pytest.raises(TrainingDataSerializationError, match="array-reference digest mismatch"):
        PerfBase0Record.from_dict(payload)

    payload = copy.deepcopy(record.to_dict())
    payload["scientific_stages"][0]["json_references"][0]["value"] = ["a", "b"]
    with pytest.raises(TrainingDataSerializationError, match="JSON-reference value digest mismatch"):
        PerfBase0Record.from_dict(payload)


def test_stage_meter_records_stage_local_telemetry() -> None:
    with PerfBase0StageMeter(
        "meter",
        worker_settings={"workers": 1},
        sample_interval_seconds=0.001,
        environment={"host": "unit-test"},
    ) as meter:
        values = np.arange(1000, dtype=np.float64)
        time.sleep(0.004)
        assert float(np.sum(values)) > 0.0
    telemetry = meter.telemetry(
        throughput_count=1000,
        throughput_unit="values",
        temporary_array_bytes=values.nbytes,
    )
    assert telemetry.stage_id == "meter"
    assert telemetry.wall_seconds > 0.0
    assert telemetry.sampled_peak_rss_bytes >= telemetry.rss_start_bytes
    assert telemetry.worker_settings == {"workers": 1}
    assert telemetry.environment == {"host": "unit-test"}
    assert telemetry.throughput_per_second == pytest.approx(1000 / telemetry.wall_seconds)


def test_public_authority_version_is_frozen() -> None:
    assert PERF_BASE0_VERSION == "mdstats.mlff-perf-base0.2026-08.v1"
