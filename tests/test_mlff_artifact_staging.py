from __future__ import annotations

import errno
from pathlib import Path
import threading

import pytest

from mdstats.training_data._common import sha256_file_cached
from mdstats.training_data.artifact_staging import (
    ImmutableArtifactStage,
    stage_immutable_artifact,
)


def test_immutable_staging_direct_hardlink_and_roundtrip(tmp_path: Path) -> None:
    source = tmp_path / "source.pt"
    source.write_bytes(b"immutable-model-bytes")
    direct = stage_immutable_artifact(source, tmp_path / "unused.pt", allow_direct_reference=True)
    linked = stage_immutable_artifact(
        source, tmp_path / "stage" / "model.pt", expected_sha256=sha256_file_cached(source)
    )
    assert direct.method == "direct" and Path(direct.staged_path) == source
    assert linked.method in {"hardlink", "copy"}
    assert Path(linked.staged_path).read_bytes() == source.read_bytes()
    assert ImmutableArtifactStage.from_dict(linked.to_dict()) == linked


def test_immutable_staging_copy_fallback_and_failure_cleanup(tmp_path: Path, monkeypatch) -> None:
    import mdstats.training_data.artifact_staging as staging

    source = tmp_path / "source.pt"
    source.write_bytes(b"immutable-model-bytes")

    real_link = staging.os.link

    def cross_device(source_path, destination_path, *args, **kwargs):
        if Path(source_path) == source:
            raise OSError(errno.EXDEV, "cross-device link")
        return real_link(source_path, destination_path, *args, **kwargs)

    monkeypatch.setattr(staging.os, "link", cross_device)
    destination = tmp_path / "stage" / "model.pt"
    receipt = stage_immutable_artifact(source, destination)
    assert receipt.method == "copy"
    assert destination.read_bytes() == source.read_bytes()
    assert not tuple(destination.parent.glob("*.tmp"))


def test_immutable_staging_refuses_existing_different_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source.pt"
    destination = tmp_path / "model.pt"
    source.write_bytes(b"source")
    destination.write_bytes(b"other")
    with pytest.raises(Exception, match="different bytes"):
        stage_immutable_artifact(source, destination)
    assert destination.read_bytes() == b"other"


def test_simultaneous_identical_publishers_converge_without_clobber(tmp_path: Path) -> None:
    source = tmp_path / "source.pt"
    destination = tmp_path / "stage" / "model.pt"
    source.write_bytes(b"same")
    barrier = threading.Barrier(2)
    results = []
    failures = []

    def publish() -> None:
        try:
            barrier.wait(timeout=2.0)
            results.append(stage_immutable_artifact(source, destination))
        except BaseException as exc:
            failures.append(exc)

    threads = [threading.Thread(target=publish) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=3.0)
    assert not failures
    assert len(results) == 2
    assert destination.read_bytes() == b"same"
    assert {result.method for result in results} <= {"hardlink", "copy", "existing"}


def test_simultaneous_different_publishers_never_replace_winner(tmp_path: Path) -> None:
    first = tmp_path / "first.pt"
    second = tmp_path / "second.pt"
    destination = tmp_path / "stage" / "model.pt"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    barrier = threading.Barrier(2)
    outcomes = []

    def publish(source: Path) -> None:
        try:
            barrier.wait(timeout=2.0)
            outcomes.append(stage_immutable_artifact(source, destination))
        except BaseException as exc:
            outcomes.append(exc)

    threads = [
        threading.Thread(target=publish, args=(first,)),
        threading.Thread(target=publish, args=(second,)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=3.0)
    assert sum(isinstance(value, ImmutableArtifactStage) for value in outcomes) == 1
    assert sum(isinstance(value, Exception) for value in outcomes) == 1
    accepted = destination.read_bytes()
    assert accepted in {b"first", b"second"}
    assert destination.read_bytes() == accepted
    assert not tuple(destination.parent.glob("*.tmp"))
