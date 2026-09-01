"""Shared crash-safe publication primitives for target-size execution.

Provides unified advisory-locked, atomic create-or-verify publication for
immutable raw bytes (ExtXYZ, model checkpoints) and typed content-addressed
JSON artifacts, as well as atomic replacement for mutable pointers.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)


def _lock_file_path(path: Path) -> Path:
    """Deterministic advisory lock file path adjacent to target."""
    return path.parent / f".{path.name}.lock"


def _fsync_parent_directory(path: Path) -> None:
    """Persist a completed rename in the destination directory entry."""

    try:
        fd = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    except OSError:
        # Some supported filesystems do not permit directory fsync.  The file
        # itself has still been flushed and the rename remains atomic.
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class _FileLock:
    """Context manager for advisory flock on a lock file."""

    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self._fd: int | None = None

    def __enter__(self) -> _FileLock:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(
            str(self.lock_path), os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o644
        )
        fcntl.flock(self._fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None


def artifact_publication_lock(destination: str | Path) -> "_FileLock":
    """Advisory exclusive lock guarding one destination path's publication.

    Content-addressed records publish through create-or-verify byte equality
    and need no external lock.  An artifact produced by a *non-deterministic*
    serializer - a full PyTorch model pickle, for instance - cannot be compared
    byte-for-byte across two independent builds, so concurrent builders of the
    same logical artifact must be serialized instead. This exposes the same
    lock this module already uses, so there is one advisory-lock implementation.
    """

    return _FileLock(_lock_file_path(Path(destination)))


def publish_immutable_bytes_create_or_verify(
    destination: str | Path,
    raw_bytes: bytes,
    *,
    expected_sha256: str | None = None,
) -> str:
    """Atomically publish immutable bytes with create-or-verify semantics.

    Writes to an attempt-local temporary file, flushes/fsyncs, acquires an
    advisory lock on the destination, and atomically moves the file into
    place if absent, or verifies SHA-256 byte equality if already present.

    Returns the verified SHA-256 hex digest of the published bytes.
    """
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    computed_sha = hashlib.sha256(raw_bytes).hexdigest()
    if expected_sha256 is not None:
        valid_expected = validate_digest(expected_sha256, name="expected_sha256")
        if computed_sha != valid_expected:
            raise TrainingDataInputError(
                f"Published bytes SHA-256 {computed_sha} does not match expected {valid_expected}."
            )

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=dest.parent,
            prefix=f".tmp_{dest.name}_",
            delete=False,
        ) as tmp:
            tmp.write(raw_bytes)
            tmp.flush()
            os.fsync(tmp.fileno())
            temp_path = Path(tmp.name)

        with _FileLock(_lock_file_path(dest)):
            if dest.is_file():
                existing_sha = hashlib.sha256(dest.read_bytes()).hexdigest()
                if existing_sha != computed_sha:
                    raise TrainingDataInputError(
                        f"Conflicting immutable bytes already exist at {dest}: "
                        f"existing SHA {existing_sha} != published SHA {computed_sha}."
                    )
                # Existing file is identical; remove temp
                if temp_path is not None and temp_path.exists():
                    temp_path.unlink(missing_ok=True)
                    temp_path = None
                return existing_sha

            # Destination does not exist; atomically place temp file
            os.replace(str(temp_path), str(dest))
            _fsync_parent_directory(dest)
            temp_path = None
            return computed_sha
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def publish_immutable_json_create_or_verify(
    destination: str | Path,
    payload: Mapping[str, Any],
    *,
    deserializer: Callable[[Mapping[str, Any]], Any] | None = None,
) -> Any:
    """Atomically publish an immutable JSON record with create-or-verify semantics.

    Writes to an attempt-local temporary file, flushes/fsyncs, validates the
    temp file through ``deserializer`` if provided, acquires an advisory lock,
    and atomically moves into place or verifies semantic content digest equality.
    """
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    raw_text = json.dumps(payload, indent=2, sort_keys=True)

    obj_to_return: Any = payload
    expected_digest = digest(payload)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=dest.parent,
            prefix=f".tmp_{dest.name}_",
            delete=False,
        ) as tmp:
            tmp.write(raw_text)
            tmp.flush()
            os.fsync(tmp.fileno())
            temp_path = Path(tmp.name)

        # Validate the fully written attempt-local file, rather than merely
        # reusing the in-memory mapping that produced it.  This keeps the
        # publication contract honest if serialization or the temp-file path
        # is ever changed independently of the caller payload.
        if deserializer is not None:
            try:
                temp_dict = json.loads(temp_path.read_text(encoding="utf-8"))
                if not isinstance(temp_dict, Mapping):
                    raise TrainingDataSerializationError(
                        "Serialized typed JSON payload must be an object."
                    )
                obj_to_return = deserializer(temp_dict)
                expected_digest = str(getattr(obj_to_return, "content_digest", ""))
                if not expected_digest:
                    expected_digest = digest(temp_dict)
            except Exception as exc:
                raise TrainingDataSerializationError(
                    f"Failed to deserialize temporary payload before publishing to {dest}: {exc}"
                ) from exc

        with _FileLock(_lock_file_path(dest)):
            if dest.is_file():
                try:
                    existing_dict = json.loads(dest.read_text(encoding="utf-8"))
                    if deserializer is not None:
                        existing_obj = deserializer(existing_dict)
                        existing_digest = str(getattr(existing_obj, "content_digest", ""))
                        if not existing_digest:
                            existing_digest = digest(existing_dict)
                    else:
                        existing_obj = existing_dict
                        existing_digest = digest(existing_dict)
                except Exception as exc:
                    raise TrainingDataInputError(
                        f"Existing record at {dest} is corrupted or invalid: {exc}"
                    ) from exc

                if existing_digest != expected_digest:
                    raise TrainingDataInputError(
                        f"Conflicting immutable record already exists at {dest}: "
                        f"existing digest {existing_digest} != published digest {expected_digest}."
                    )
                if temp_path is not None and temp_path.exists():
                    temp_path.unlink(missing_ok=True)
                    temp_path = None
                return existing_obj

            os.replace(str(temp_path), str(dest))
            _fsync_parent_directory(dest)
            temp_path = None
            return obj_to_return
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def publish_mutable_json_atomic(
    destination: str | Path,
    payload: Mapping[str, Any],
) -> None:
    """Atomically replace a mutable pointer JSON file (e.g. current_head.json)."""
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    raw_text = json.dumps(payload, indent=2, sort_keys=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=dest.parent,
            prefix=f".tmp_{dest.name}_",
            delete=False,
        ) as tmp:
            tmp.write(raw_text)
            tmp.flush()
            os.fsync(tmp.fileno())
            temp_path = Path(tmp.name)

        with _FileLock(_lock_file_path(dest)):
            os.replace(str(temp_path), str(dest))
            _fsync_parent_directory(dest)
        temp_path = None
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def publish_mutable_bytes_atomic(
    destination: str | Path,
    raw_bytes: bytes,
) -> None:
    """Atomically replace a mutable binary companion/checkpoint file."""

    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=dest.parent,
            prefix=f".tmp_{dest.name}_",
            delete=False,
        ) as tmp:
            tmp.write(raw_bytes)
            tmp.flush()
            os.fsync(tmp.fileno())
            temp_path = Path(tmp.name)

        with _FileLock(_lock_file_path(dest)):
            os.replace(str(temp_path), str(dest))
            _fsync_parent_directory(dest)
        temp_path = None
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


__all__ = [
    "publish_immutable_bytes_create_or_verify",
    "publish_immutable_json_create_or_verify",
    "publish_mutable_bytes_atomic",
    "publish_mutable_json_atomic",
]
