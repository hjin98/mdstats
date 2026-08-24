"""Atomic staging for authenticated immutable verification artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import errno
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    sha256_file_cached,
    validate_digest,
)


IMMUTABLE_ARTIFACT_STAGE_SCHEMA = "mdstats.immutable-artifact-stage.v1"


@dataclass(frozen=True, slots=True)
class ImmutableArtifactStage:
    source_path: str
    staged_path: str
    source_sha256: str
    method: str

    def __post_init__(self) -> None:
        if self.method not in {"direct", "hardlink", "copy", "existing"}:
            raise TrainingDataInputError("Unsupported immutable artifact staging method.")
        object.__setattr__(
            self, "source_sha256", validate_digest(self.source_sha256, name="source_sha256")
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": IMMUTABLE_ARTIFACT_STAGE_SCHEMA,
            "source_path": self.source_path,
            "staged_path": self.staged_path,
            "source_sha256": self.source_sha256,
            "method": self.method,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ImmutableArtifactStage":
        if payload.get("schema") != IMMUTABLE_ARTIFACT_STAGE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported immutable artifact staging schema.")
        result = cls(
            source_path=str(payload["source_path"]), staged_path=str(payload["staged_path"]),
            source_sha256=str(payload["source_sha256"]), method=str(payload["method"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Immutable artifact staging digest mismatch.")
        return result


def stage_immutable_artifact(
    source_path: str | Path,
    destination_path: str | Path,
    *,
    expected_sha256: str | None = None,
    allow_direct_reference: bool = False,
) -> ImmutableArtifactStage:
    """Prefer direct reference, then hardlink, then copy with atomic publication."""

    source = Path(source_path).expanduser().resolve()
    if not source.is_file():
        raise TrainingDataInputError(f"Immutable staging source is missing: {source!s}.")
    source_sha = sha256_file_cached(source)
    if expected_sha256 is not None and source_sha != validate_digest(expected_sha256, name="expected_sha256"):
        raise TrainingDataInputError("Immutable staging source bytes differ from expected SHA authority.")
    if allow_direct_reference:
        return ImmutableArtifactStage(
            source_path=str(source), staged_path=str(source), source_sha256=source_sha, method="direct"
        )

    destination = Path(destination_path).expanduser().resolve()
    if destination == source:
        return ImmutableArtifactStage(
            source_path=str(source), staged_path=str(source), source_sha256=source_sha, method="direct"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not destination.is_file() or sha256_file_cached(destination) != source_sha:
            raise TrainingDataInputError("Immutable staging destination exists with different bytes.")
        return ImmutableArtifactStage(
            source_path=str(source), staged_path=str(destination), source_sha256=source_sha, method="existing"
        )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    method = "hardlink"
    try:
        temporary.unlink()
        try:
            os.link(source, temporary)
        except OSError as exc:
            if exc.errno not in {errno.EXDEV, errno.EPERM, errno.EACCES, errno.EMLINK, errno.ENOTSUP}:
                raise
            method = "copy"
            shutil.copy2(source, temporary)
        if sha256_file_cached(temporary) != source_sha:
            raise TrainingDataInputError("Immutable staged bytes differ from their source.")
        try:
            # Hard-link publication is an atomic no-clobber create because the
            # attempt-local temporary lives in the destination directory. A
            # concurrent winner is authenticated below; it is never replaced.
            os.link(temporary, destination)
        except FileExistsError:
            if not destination.is_file() or sha256_file_cached(destination) != source_sha:
                raise TrainingDataInputError(
                    "Immutable staging destination was concurrently published with different bytes."
                )
            method = "existing"
    finally:
        temporary.unlink(missing_ok=True)
    if sha256_file_cached(source) != source_sha or sha256_file_cached(destination) != source_sha:
        raise TrainingDataInputError("Immutable source changed during staging.")
    return ImmutableArtifactStage(
        source_path=str(source), staged_path=str(destination), source_sha256=source_sha, method=method
    )


__all__ = [
    "IMMUTABLE_ARTIFACT_STAGE_SCHEMA",
    "ImmutableArtifactStage",
    "stage_immutable_artifact",
]
