from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import threading

import pytest

from mdstats.training_data import campaign_cli
from mdstats.training_data import training_parallel
import mdstats.training_data._common as common


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
