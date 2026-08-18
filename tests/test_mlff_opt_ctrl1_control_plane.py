from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import threading

import pytest

from mdstats.training_data import campaign_cli
from mdstats.training_data import training_parallel
import mdstats.training_data._common as common
import mdstats.training_data.data8_bundle as data8_bundle


class _TinyRecord:
    def __init__(self, value: int):
        self.value = int(value)

    def to_dict(self):
        return {"schema": "tiny.v1", "value": self.value}

    @classmethod
    def from_dict(cls, payload):
        return cls(int(payload["value"]))


def test_campaign_store_reuses_one_connection_per_thread(tmp_path: Path) -> None:
    store = campaign_cli.CampaignStore(tmp_path / ".mdstats" / "campaign.sqlite3")
    first = store._connect()
    store.set_meta("x", 1)
    assert store._connect() is first

    worker_ids: list[int] = []

    def worker() -> None:
        worker_ids.append(id(store._connect()))
        assert store.get_meta("x") == 1

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    assert worker_ids
    assert worker_ids[0] != id(first)


def test_optional_record_fetch_is_one_select_and_one_decode(tmp_path: Path) -> None:
    store = campaign_cli.CampaignStore(tmp_path / ".mdstats" / "campaign.sqlite3")
    store.put_record("tiny", _TinyRecord(7))
    statements: list[str] = []
    db = store._connect()
    db.set_trace_callback(statements.append)
    try:
        restored = store.get_record_optional("tiny", _TinyRecord)
    finally:
        db.set_trace_callback(None)
    assert restored is not None and restored.value == 7
    selects = [
        statement
        for statement in statements
        if statement.lstrip().upper().startswith("SELECT PAYLOAD FROM RECORDS")
    ]
    assert len(selects) == 1
    assert store.get_record_optional("missing", _TinyRecord) is None


def test_put_records_batches_one_sqlite_transaction(tmp_path: Path) -> None:
    store = campaign_cli.CampaignStore(tmp_path / ".mdstats" / "campaign.sqlite3")
    statements: list[str] = []
    db = store._connect()
    db.set_trace_callback(statements.append)
    try:
        store.put_records({"a": _TinyRecord(1), "b": _TinyRecord(2)})
    finally:
        db.set_trace_callback(None)
    assert store.get_record("a", _TinyRecord).value == 1
    assert store.get_record("b", _TinyRecord).value == 2
    assert sum(stmt.strip().upper() == "COMMIT" for stmt in statements) == 1


def test_sha256_receipt_survives_process_cache_reset_and_invalidates_on_stat_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt_db = tmp_path / ".mdstats" / "hash-receipts.sqlite3"
    common.configure_sha256_receipt_store(receipt_db)
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"stable artifact")
    common._sha256_file_for_identity.cache_clear()
    common._SHA256_HASHED_IN_PROCESS.clear()
    expected = common.sha256_file_cached(path)
    assert receipt_db.is_file()

    # Simulate a fresh process-local hash cache. The durable receipt should be
    # enough to authenticate the same strong stat identity without reading bytes.
    common._sha256_file_for_identity.cache_clear()
    common._SHA256_HASHED_IN_PROCESS.clear()

    def forbidden_hash(*args, **kwargs):
        raise AssertionError("file bytes were re-hashed despite a durable receipt")

    monkeypatch.setattr(common, "_sha256_file_for_identity", forbidden_hash)
    assert common.sha256_file_cached(path) == expected

    # Changing the file changes size/mtime/ctime identity, so the old receipt is
    # not reusable and a fresh hash would be required.
    path.write_bytes(b"changed artifact with different size")
    with pytest.raises(AssertionError, match="re-hashed"):
        common.sha256_file_cached(path)


def test_gpu_telemetry_prefers_nvml_and_falls_back_to_nvidia_smi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nvml_sample = training_parallel.GpuTelemetrySample(
        sampled_monotonic=1.0,
        device_index=0,
        utilization_percent=41.0,
        used_bytes=3,
        total_bytes=10,
    )
    monkeypatch.setattr(
        training_parallel, "_query_gpu_telemetry_nvml", lambda index: nvml_sample
    )
    monkeypatch.setattr(
        training_parallel,
        "_query_gpu_telemetry_nvidia_smi",
        lambda index: (_ for _ in ()).throw(AssertionError("fallback should not run")),
    )
    assert training_parallel.query_gpu_telemetry("cuda:0") is nvml_sample

    fallback = training_parallel.GpuTelemetrySample(
        sampled_monotonic=2.0,
        device_index=0,
        utilization_percent=12.0,
        used_bytes=4,
        total_bytes=10,
    )
    monkeypatch.setattr(training_parallel, "_query_gpu_telemetry_nvml", lambda index: None)
    monkeypatch.setattr(
        training_parallel, "_query_gpu_telemetry_nvidia_smi", lambda index: fallback
    )
    assert training_parallel.query_gpu_telemetry("cuda") is fallback
    assert training_parallel.query_gpu_telemetry("cpu") is None


def test_post_calibration_inference_gpu_polling_is_sparse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    sample = training_parallel.GpuTelemetrySample(1.0, 0, 10.0, 1, 10)
    monkeypatch.setattr(
        campaign_cli,
        "query_gpu_telemetry",
        lambda device: calls.append(device) or sample,
    )
    policy = SimpleNamespace(monitor_interval_seconds=2.0)
    cfg = {
        "execution": {
            "parallel_inference_post_calibration_monitor_interval_seconds": 30.0
        }
    }
    calibrated = SimpleNamespace(gpu_calibrated=True)
    value, last = campaign_cli._maybe_query_inference_gpu_telemetry(
        cfg=cfg,
        policy=policy,
        controller=calibrated,
        device="cuda:0",
        active_jobs=2,
        now=100.0,
        last_sample_monotonic=0.0,
    )
    assert value is sample and last == 100.0
    value, last = campaign_cli._maybe_query_inference_gpu_telemetry(
        cfg=cfg,
        policy=policy,
        controller=calibrated,
        device="cuda:0",
        active_jobs=2,
        now=110.0,
        last_sample_monotonic=last,
    )
    assert value is None and last == 100.0
    value, last = campaign_cli._maybe_query_inference_gpu_telemetry(
        cfg=cfg,
        policy=policy,
        controller=calibrated,
        device="cuda:0",
        active_jobs=2,
        now=131.0,
        last_sample_monotonic=last,
    )
    assert value is sample and last == 131.0
    assert calls == ["cuda:0", "cuda:0"]

    # During the one-time calibration, retain the original high-frequency cadence.
    uncalibrated = SimpleNamespace(gpu_calibrated=False)
    value, _ = campaign_cli._maybe_query_inference_gpu_telemetry(
        cfg=cfg,
        policy=policy,
        controller=uncalibrated,
        device="cuda:0",
        active_jobs=1,
        now=134.0,
        last_sample_monotonic=131.0,
    )
    assert value is sample


def test_replay_weight_scaling_streams_extxyz_frames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ase import Atoms
    from ase.io import iread as real_iread, read, write
    import ase.io

    source = tmp_path / "replay.extxyz"
    target = tmp_path / "weighted.extxyz"
    frames = []
    for index in range(4):
        atoms = Atoms("LiO", positions=[[0, 0, 0], [1.5, 0, 0]], cell=[8, 8, 8], pbc=True)
        atoms.info["config_weight"] = float(index + 1)
        frames.append(atoms)
    write(source, frames, format="extxyz")

    yielded = 0

    def streaming_iread(*args, **kwargs):
        nonlocal yielded
        for atoms in real_iread(*args, **kwargs):
            yielded += 1
            yield atoms

    monkeypatch.setattr(ase.io, "iread", streaming_iread)
    original_writer = data8_bundle._write_extxyz_high_precision

    def checking_writer(handle, images):
        assert not isinstance(images, (list, tuple))
        return original_writer(handle, images)

    monkeypatch.setattr(data8_bundle, "_write_extxyz_high_precision", checking_writer)
    data8_bundle._scale_extxyz_configuration_weights(source, target, scale=2.5)
    observed = read(target, index=":", format="extxyz")
    assert yielded == 4
    assert [atoms.info["config_weight"] for atoms in observed] == pytest.approx(
        [2.5, 5.0, 7.5, 10.0]
    )
