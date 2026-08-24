from __future__ import annotations

import errno
from pathlib import Path

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

    def cross_device(*args, **kwargs):
        raise OSError(errno.EXDEV, "cross-device link")

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
