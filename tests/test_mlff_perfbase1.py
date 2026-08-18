from __future__ import annotations

import copy
from pathlib import Path

import pytest

import mdstats
from mdstats.training_data._common import digest
from mdstats.training_data.performance_baseline import PerfBase0ArtifactIdentity


def _trial(label: str, workers: int, repeat: int, *, wall: float = 2.0, output: str | None = None):
    out = digest("same-output") if output is None else output
    return mdstats.PerfBase1Trial.build(
        workload_id="work",
        schedule_label=label,
        repeat_index=repeat,
        requested_workers=workers,
        allocated_workers=workers,
        measured_at_utc="2026-08-17T12:00:00Z",
        wall_seconds=wall,
        process_cpu_seconds=wall * workers * 0.75,
        rss_start_bytes=100,
        rss_end_bytes=120,
        sampled_peak_rss_bytes=130,
        process_peak_rss_bytes=140,
        persisted_bytes=10,
        temporary_array_bytes=20,
        scientific_output_digest=out,
        counters={"edges": 100},
        queue={"observed": workers > 1, "max_busy_workers": workers},
        worker_settings={"workers": workers},
        environment={"host": "unit"},
    )


def _record(tmp_path: Path) -> mdstats.PerfBase1Record:
    source = tmp_path / "model.pt"
    source.write_bytes(b"model")
    artifact = PerfBase0ArtifactIdentity.from_file(
        source, logical_path="inputs/model.pt", role="active_foundation_checkpoint"
    )
    trials = (
        _trial("serial", 1, 0, wall=2.0),
        _trial("serial", 1, 1, wall=2.2),
        _trial("auto", 3, 0, wall=0.9),
        _trial("auto", 3, 1, wall=1.0),
    )
    workload = mdstats.PerfBase1Workload(
        workload_id="work",
        workload_kind="synthetic",
        corpus_digests=(digest("corpus"),),
        policy_digests=(digest("policy"),),
        scientific_output_digest=trials[0].scientific_output_digest,
        throughput_unit="edges",
        trials=trials,
    )
    return mdstats.PerfBase1Record(
        baseline_id="baseline",
        source_version="0.20.225a0",
        created_at_utc="2026-08-17T12:00:00Z",
        foundation_family="mace-mpa-0",
        foundation_variant="medium",
        foundation_model_sha256=artifact.sha256,
        source_artifacts=(artifact,),
        workloads=(workload,),
    )


def test_perfbase1_is_public_and_round_trips(tmp_path: Path) -> None:
    assert mdstats.PERFBASE1_VERSION == "mdstats.mlff-perfbase1.2026-08.v1"
    record = _record(tmp_path)
    path = mdstats.write_perfbase1_record(tmp_path / "perfbase1.json", record)
    restored = mdstats.read_perfbase1_record(path)
    assert restored.to_dict() == record.to_dict()
    assert restored.scientific_digest == record.scientific_digest
    assert restored.execution_digest == record.execution_digest
    summary = restored.workloads[0].schedule_summary()
    assert summary["serial"]["allocated_workers"] == 1
    assert summary["auto"]["allocated_workers"] == 3
    assert 0.0 < summary["serial"]["wall_cv"] < 0.2


def test_perfbase1_rejects_scientific_drift_across_worker_counts() -> None:
    with pytest.raises(mdstats.TrainingDataInputError, match="scientific output drift"):
        mdstats.PerfBase1Workload(
            workload_id="work",
            workload_kind="synthetic",
            corpus_digests=(digest("corpus"),),
            policy_digests=(digest("policy"),),
            scientific_output_digest=digest("same-output"),
            throughput_unit="edges",
            trials=(
                _trial("serial", 1, 0),
                _trial("auto", 3, 0, output=digest("changed-output")),
            ),
        )


def test_perfbase1_scientific_digest_excludes_timing(tmp_path: Path) -> None:
    first = _record(tmp_path)
    payload = copy.deepcopy(first.to_dict())
    payload["workloads"][0]["trials"][0]["wall_seconds"] = 99.0
    payload["workloads"][0]["trials"][0]["process_cpu_seconds"] = 74.25
    payload["workloads"][0]["trials"][0]["effective_cpu_cores"] = 0.75
    payload["workloads"][0]["trials"][0]["assigned_lane_occupancy"] = 0.75
    for key in ("content_digest", "execution_digest"):
        payload.pop(key, None)
    payload["workloads"][0].pop("content_digest", None)
    payload["workloads"][0]["trials"][0].pop("content_digest", None)
    second = mdstats.PerfBase1Record.from_dict(payload)
    assert first.scientific_digest == second.scientific_digest
    assert first.execution_digest != second.execution_digest


def test_perfbase1_model_identity_is_foundation_generic(tmp_path: Path) -> None:
    record = _record(tmp_path)
    payload = record.to_dict()
    payload["foundation_family"] = "mace-mh-1"
    payload["foundation_variant"] = "omat_pbe"
    for key in ("content_digest", "scientific_digest", "execution_digest"):
        payload.pop(key, None)
    mh1 = mdstats.PerfBase1Record.from_dict(payload)
    assert mh1.foundation_family == "mace-mh-1"
    assert mh1.foundation_variant == "omat_pbe"
    assert mh1.scientific_digest != record.scientific_digest
