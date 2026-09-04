"""One crash-durable publication boundary for storage-native records.

Archive replacement and restore are durability/recovery features: a terminal
receipt that outlives a power loss must never authenticate bytes that did not.
Every storage-owned publication therefore goes through this single owner, which
implements the accepted repository ordering:

``write/stage -> flush + fsync content -> atomic publish -> persist parent
directory entry -> authenticate published bytes -> publish dependent record``.

The directory-entry step reuses the repository's existing
:func:`fsync_parent_directory` primitive rather than a divergent local
implementation, and degrades conservatively (the content flush and the atomic
rename still hold) on a filesystem that refuses a directory fsync.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ..target_size_execution.persistence import fsync_parent_directory

#: Chunk size for streaming digests; also bounds peak memory during
#: authentication of a large archive blob.
DIGEST_CHUNK_BYTES = 4 * 1024 * 1024


class StorageDurabilityError(RuntimeError):
    """A storage record could not be durably published or authenticated."""


def sha256_file(path: str | os.PathLike[str], *, limit_bytes: int | None = None) -> str:
    """Streaming SHA-256 of one regular file, without following symlinks twice.

    ``limit_bytes`` fails closed when a file is longer than the caller admitted,
    so a corrupt or tampered source cannot be read unboundedly.
    """

    candidate = Path(path)
    hasher = hashlib.sha256()
    read = 0
    with candidate.open("rb") as handle:
        while True:
            chunk = handle.read(DIGEST_CHUNK_BYTES)
            if not chunk:
                break
            read += len(chunk)
            if limit_bytes is not None and read > int(limit_bytes):
                raise StorageDurabilityError(
                    f"file exceeds its admitted size bound while hashing: {candidate}"
                )
            hasher.update(chunk)
    return hasher.hexdigest()


#: Below this size the receipt round-trip costs more than simply hashing the
#: bytes.  Measured on the S4 fixture (`benchmarks/benchmark_mlff_storage_io_reset.py`):
#: at 1 MiB members the receipt path was ~20x *slower* than a direct hash, while
#: at 32 MiB members a reused receipt was ~1.6x faster than rehashing.  The
#: threshold keeps the acceleration where it pays and out of the way where it
#: does not.
RECEIPT_ACCELERATION_MINIMUM_BYTES = 8 * 1024 * 1024


def accelerated_sha256(path: str | os.PathLike[str]) -> str:
    """SHA-256 of one artifact the owner has declared immutable.

    Large artifacts reuse the campaign's stat-keyed SHA-256 receipt cache, the
    accepted acceleration owner for immutable hashing. A receipt is an
    optimization and never an authority: a stat-identity mismatch forces a
    fresh byte hash, and a stale value can only make a later authentication
    step fail loudly, never make a wrong archive look right. Small artifacts
    are hashed directly, because the receipt round-trip costs more than the
    read it would avoid.

    Authentication of untrusted or freshly published bytes deliberately does
    *not* go through here - see :func:`sha256_file`.
    """

    try:
        size = Path(path).stat().st_size
    except OSError:
        size = 0
    if int(size) < RECEIPT_ACCELERATION_MINIMUM_BYTES:
        return sha256_file(path)
    from .._common import sha256_file_cached

    return sha256_file_cached(path)


def parallel_digests(
    paths: Sequence[str | os.PathLike[str]], *, workers: int, accelerated: bool = True
) -> dict[str, str]:
    """Hash several immutable artifacts with bounded I/O concurrency.

    I/O concurrency is controlled independently of CPU worker count so a
    storage scan cannot create a metadata or hash thundering herd.  One worker
    means a plain sequential pass, which is what a small inventory should do.
    """

    digest_for = accelerated_sha256 if accelerated else sha256_file
    targets = [os.fspath(item) for item in paths]
    limit = max(1, int(workers))
    if limit == 1 or len(targets) < 2:
        return {item: digest_for(item) for item in targets}
    # The workers inherit this call's execution context, so a hash fan-out
    # started by an observational report stays observational and cannot write an
    # acceleration receipt from a worker thread.
    from .._observation import ObservationalThreadPoolExecutor

    with ObservationalThreadPoolExecutor(
        max_workers=min(limit, len(targets))
    ) as pool:
        return dict(zip(targets, pool.map(digest_for, targets)))


def canonical_digest(payload: Mapping[str, Any]) -> str:
    """Digest of one canonically serialized storage record."""

    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def durable_publish_bytes(
    destination: str | os.PathLike[str],
    writer: Callable[[Any], None],
    *,
    expected_sha256: str | None = None,
    on_published: Callable[[], None] | None = None,
) -> tuple[str, int]:
    """Stage, flush, fsync, atomically publish, and authenticate opaque bytes.

    ``writer`` receives an open binary file object for the staging file, so a
    large archive blob is streamed rather than materialized in memory.  The
    published bytes are re-read from their canonical path afterwards: a digest
    computed only from what was written cannot detect a filesystem that lost or
    altered the publication.

    The atomic replace is the moment the canonical name starts resolving to the
    new bytes; everything after it - parent fsync, re-read, digest comparison -
    can fail while that transition stands.  A caller cannot recover the fact
    afterwards either: the target may have pre-existed, or another actor may
    have republished it, so *observing* a file there proves nothing about this
    invocation.  ``on_published`` is therefore invoked exactly once, immediately
    after this call's ``os.replace`` succeeds and before any later step can
    raise, and never at all if the replace did not happen.
    """

    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".staging", dir=target.parent
    )
    staging = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            writer(stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staging, target)
        staging = None  # type: ignore[assignment]
        if on_published is not None:
            on_published()
        fsync_parent_directory(target)
    finally:
        if staging is not None:
            Path(staging).unlink(missing_ok=True)
    observed = sha256_file(target)
    if expected_sha256 is not None and observed != str(expected_sha256):
        raise StorageDurabilityError(
            f"published bytes at {target} do not authenticate against the expected digest"
        )
    return observed, int(target.stat().st_size)


def durable_publish_json(
    destination: str | os.PathLike[str],
    payload: Mapping[str, Any],
    *,
    on_published: Callable[[], None] | None = None,
) -> str:
    """Durably publish one storage-native JSON record and authenticate it.

    The record is re-read and re-parsed from its canonical path before this
    function returns, so a caller that publishes a dependent terminal receipt
    afterwards knows the record it depends on is durable and readable.

    That reparse is one more step that can fail *after* the record is already
    canonical, so this forwards the lower-level publication signal rather than
    hiding it behind its own success: ``on_published`` fires at the atomic
    replace, not at return.
    """

    body = dict(payload)
    encoded = (
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")

    def _write(stream: Any) -> None:
        stream.write(encoded)

    durable_publish_bytes(destination, _write, on_published=on_published)
    target = Path(destination)
    reloaded = json.loads(target.read_text(encoding="utf-8"))
    if reloaded != body:
        raise StorageDurabilityError(
            f"published storage record at {target} does not reproduce its payload"
        )
    return canonical_digest(body)


def durable_append_jsonl(destination: str | os.PathLike[str], payload: Mapping[str, Any]) -> str:
    """Append one authenticated JSONL event and fsync it.

    ``O_APPEND`` keeps an audit/journal stream append-only, so a later
    invocation cannot rewrite an earlier record of what a storage operation did.
    """

    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    body = dict(payload)
    body.pop("event_digest", None)
    event_digest = canonical_digest(body)
    body["event_digest"] = event_digest
    encoded = (
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")
    created = not target.exists()
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if created:
        fsync_parent_directory(target)
    return event_digest


def durable_unlink(
    path: str | os.PathLike[str],
    *,
    dir_fd: int | None = None,
    missing_ok: bool = True,
    on_unlinked: Callable[[], None] | None = None,
) -> None:
    """Unlink one file and persist the directory entry removal.

    Hot reclamation after an authenticated archive is a recovery-relevant
    deletion: the promise that a restart observes either the hot member or the
    catalog's account of it depends on the removal reaching the directory.

    ``on_unlinked`` reports one fact and only one: *this* call's unlink syscall
    succeeded.  It fires immediately afterwards, before the parent fsync that
    can still fail, and it does not fire for a target that was already absent
    under ``missing_ok`` - a name that was gone before this call was never
    removed by it, and crediting the caller for it would attribute someone
    else's deletion to this execution.
    """

    target = Path(path)
    if dir_fd is not None:
        try:
            os.unlink(target.name, dir_fd=dir_fd)
        except FileNotFoundError:
            if not missing_ok:
                raise
        else:
            if on_unlinked is not None:
                on_unlinked()
        os.fsync(dir_fd)
    else:
        try:
            target.unlink()
        except FileNotFoundError:
            if not missing_ok:
                raise
        else:
            if on_unlinked is not None:
                on_unlinked()
        fsync_parent_directory(target)


__all__ = [
    "DIGEST_CHUNK_BYTES",
    "RECEIPT_ACCELERATION_MINIMUM_BYTES",
    "StorageDurabilityError",
    "accelerated_sha256",
    "canonical_digest",
    "durable_append_jsonl",
    "durable_publish_bytes",
    "durable_publish_json",
    "durable_unlink",
    "parallel_digests",
    "sha256_file",
]
