"""One descriptor-authenticated owner for executable full-model artifact bytes.

A full PyTorch model file is executable serialized content: ``torch.load``
reconstructs arbitrary objects from it.  Authenticating such a file by
``lstat``-ing a pathname and then opening that pathname again is two namespace
resolutions, and anything that can swap the entry between them is trusted
instead of the bytes that were hashed.

This module is therefore the repository's single answer to "may these bytes be
deserialized?".  P5 publication (write and create-or-verify), read-only status,
and P7 deployment intake all descend from an already-authenticated campaign
anchor through :func:`~.storage.trust.open_directory_nofollow`, open the leaf
with ``O_NOFOLLOW``, prove its kind with ``fstat`` on the opened descriptor,
and stream size/SHA-256 from that same descriptor.  When a downstream library
insists on a pathname, :func:`stage_authenticated_model` copies the bytes from
the trusted descriptor into owner-private scratch, fsyncs and re-hashes the
copy, and execution proceeds from the copy - never from the original name.

It carries no stage semantics and no product identity: what a correct digest
*means* belongs to the P5 model-publication owner.
"""

from __future__ import annotations

import errno
import hashlib
import os
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterator

from ._common import TrainingDataInputError, validate_digest
from .storage.trust import NamespaceAmbiguity, open_directory_nofollow

#: Streaming chunk for descriptor-relative hashing of large model pickles.
_CHUNK_BYTES = 1024 * 1024


class ModelArtifactTrustError(TrainingDataInputError):
    """A model artifact's path, kind, size or bytes could not be authenticated."""


def normalize_relative_artifact_path(value: str, *, name: str = "model_relative_path") -> str:
    """Validate one root-relative, confined, normalized POSIX artifact path.

    Rejects absolute paths, ``..`` traversal, empty or ``.`` components, and
    backslash separators.  Confinement is a property of the *stored* locator,
    checked once here, so every descent below can assume the components are
    ordinary names.
    """

    text = str(value).strip()
    if not text:
        raise ModelArtifactTrustError(f"{name} must be a non-empty relative path.")
    if "\\" in text:
        raise ModelArtifactTrustError(f"{name} must use POSIX separators.")
    pure = PurePosixPath(text)
    if pure.is_absolute():
        raise ModelArtifactTrustError(f"{name} must be relative to the campaign model root.")
    parts = pure.parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise ModelArtifactTrustError(
            f"{name} must be normalized and may never escape the campaign model root."
        )
    return pure.as_posix()


@dataclass(frozen=True, slots=True)
class AuthenticatedModelArtifact:
    """What a successful authentication proved about one model file."""

    relative_path: str
    size_bytes: int
    sha256: str


@contextmanager
def open_model_artifact_descriptor(
    anchor: str | os.PathLike[str], relative_path: str
) -> Iterator[int]:
    """Open one confined artifact leaf as a regular file, no-follow, from ``anchor``.

    ``anchor`` is the already-owned campaign directory the relative path is
    resolved beneath (``CampaignPaths.models`` for a P5 product).  Every
    intermediate component is opened relative to the previously opened
    directory descriptor, so a symlink or special node planted anywhere on the
    way refuses the descent instead of redirecting it.
    """

    relative = normalize_relative_artifact_path(relative_path)
    parts = PurePosixPath(relative).parts
    anchor_path = Path(anchor)
    try:
        root_fd = os.open(
            str(anchor_path),
            os.O_RDONLY
            | os.O_DIRECTORY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as exc:
        raise ModelArtifactTrustError(
            f"The campaign model root {anchor_path!s} could not be opened as a plain "
            f"directory ({exc.strerror})."
        ) from exc
    open_fds = [root_fd]
    try:
        for component in parts[:-1]:
            try:
                open_fds.append(open_directory_nofollow(component, dir_fd=open_fds[-1]))
            except FileNotFoundError as exc:
                raise ModelArtifactTrustError(
                    f"Model artifact path component {component!r} of {relative!r} is absent."
                ) from exc
            except NamespaceAmbiguity as exc:
                raise ModelArtifactTrustError(
                    f"Model artifact path component {component!r} of {relative!r} is not a "
                    f"plain directory: {exc}"
                ) from exc
        flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
            | getattr(os, "O_CLOEXEC", 0)
        )
        try:
            leaf_fd = os.open(parts[-1], flags, dir_fd=open_fds[-1])
        except FileNotFoundError as exc:
            raise ModelArtifactTrustError(
                f"Model artifact {relative!r} is absent beneath {anchor_path!s}."
            ) from exc
        except OSError as exc:
            if exc.errno in (errno.ELOOP, errno.EMLINK):
                raise ModelArtifactTrustError(
                    f"Model artifact {relative!r} is a symbolic link; a published model "
                    "is never reached through a substituted entry."
                ) from exc
            raise ModelArtifactTrustError(
                f"Model artifact {relative!r} could not be opened ({exc.strerror})."
            ) from exc
        try:
            if not stat.S_ISREG(os.fstat(leaf_fd).st_mode):
                raise ModelArtifactTrustError(
                    f"Model artifact {relative!r} is not a regular file."
                )
            yield leaf_fd
        finally:
            try:
                os.close(leaf_fd)
            except OSError:
                pass
    finally:
        for handle in reversed(open_fds):
            try:
                os.close(handle)
            except OSError:
                pass


def _digest_descriptor(fd: int) -> tuple[int, str]:
    """Stream size and SHA-256 from one already-authenticated descriptor."""

    os.lseek(fd, 0, os.SEEK_SET)
    hasher = hashlib.sha256()
    total = 0
    while True:
        chunk = os.read(fd, _CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        hasher.update(chunk)
    return total, hasher.hexdigest()


def authenticate_model_artifact(
    anchor: str | os.PathLike[str],
    relative_path: str,
    *,
    expected_sha256: str,
    expected_size_bytes: int,
) -> AuthenticatedModelArtifact:
    """Prove one confined model leaf is exactly the recorded bytes, or fail closed."""

    expected_digest = validate_digest(str(expected_sha256), name="model_sha256")
    expected_size = int(expected_size_bytes)
    if expected_size <= 0:
        raise ModelArtifactTrustError("A published model records a positive byte count.")
    relative = normalize_relative_artifact_path(relative_path)
    with open_model_artifact_descriptor(anchor, relative) as fd:
        size, observed = _digest_descriptor(fd)
    if size != expected_size:
        raise ModelArtifactTrustError(
            f"Published model {relative!r} is {size} bytes; the record binds "
            f"{expected_size}. The product is not authenticated."
        )
    if observed != expected_digest:
        raise ModelArtifactTrustError(
            f"Published model {relative!r} bytes changed after publication "
            f"(observed {observed[:12]}..., recorded {expected_digest[:12]}...); "
            "a mutated product is never consumed."
        )
    return AuthenticatedModelArtifact(
        relative_path=relative, size_bytes=size, sha256=observed
    )


def read_model_artifact_identity(
    anchor: str | os.PathLike[str], relative_path: str
) -> AuthenticatedModelArtifact:
    """Observe one confined leaf's actual size/SHA without an expectation."""

    relative = normalize_relative_artifact_path(relative_path)
    with open_model_artifact_descriptor(anchor, relative) as fd:
        size, observed = _digest_descriptor(fd)
    return AuthenticatedModelArtifact(
        relative_path=relative, size_bytes=size, sha256=observed
    )


@contextmanager
def stage_authenticated_model(
    anchor: str | os.PathLike[str],
    relative_path: str,
    *,
    expected_sha256: str,
    expected_size_bytes: int,
    scratch_directory: str | os.PathLike[str],
    filename: str = "staged.model",
) -> Iterator[Path]:
    """Copy authenticated bytes into private scratch and yield that trusted path.

    Downstream libraries (``torch.load``, the MACE exporter, LAMMPS) want a
    pathname.  Handing them the original name would reopen it and undo the
    descriptor authentication, so the authenticated descriptor is copied once
    into owner-private scratch, fsynced, and re-hashed before anything executes
    it.  The staged copy is removed when the block exits.
    """

    expected_digest = validate_digest(str(expected_sha256), name="model_sha256")
    expected_size = int(expected_size_bytes)
    if Path(filename).name != filename or not filename.strip():
        raise ModelArtifactTrustError("A staged model filename must be one basename.")
    scratch = Path(scratch_directory)
    scratch.mkdir(parents=True, exist_ok=True)
    staged = scratch / filename
    hasher = hashlib.sha256()
    total = 0
    with open_model_artifact_descriptor(anchor, relative_path) as fd:
        os.lseek(fd, 0, os.SEEK_SET)
        with staged.open("wb") as sink:
            while True:
                chunk = os.read(fd, _CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                hasher.update(chunk)
                sink.write(chunk)
            sink.flush()
            os.fsync(sink.fileno())
    try:
        if total != expected_size or hasher.hexdigest() != expected_digest:
            raise ModelArtifactTrustError(
                f"Staging {relative_path!r} did not reproduce the recorded product "
                "bytes; nothing is deserialized from an unauthenticated copy."
            )
        restaged = hashlib.sha256(staged.read_bytes()).hexdigest()
        if restaged != expected_digest:
            raise ModelArtifactTrustError(
                "The staged private copy does not authenticate; execution is refused."
            )
        yield staged
    finally:
        staged.unlink(missing_ok=True)


def _open_or_create_directory(name: str, *, dir_fd: int) -> int:
    """Open one child directory no-follow, creating it if it is absent."""

    try:
        return open_directory_nofollow(name, dir_fd=dir_fd)
    except FileNotFoundError:
        pass
    except NamespaceAmbiguity as exc:
        raise ModelArtifactTrustError(
            f"Publication path component {name!r} is not a plain directory: {exc}"
        ) from exc
    try:
        os.mkdir(name, 0o755, dir_fd=dir_fd)
    except FileExistsError:
        pass
    except OSError as exc:
        raise ModelArtifactTrustError(
            f"Publication path component {name!r} could not be created ({exc.strerror})."
        ) from exc
    else:
        # Directory creation is part of durability, not only containment: the
        # new directory *entry* must survive a crash before any pointer names
        # a file inside it.
        try:
            os.fsync(dir_fd)
        except OSError:
            pass
    try:
        return open_directory_nofollow(name, dir_fd=dir_fd)
    except (FileNotFoundError, NamespaceAmbiguity) as exc:
        raise ModelArtifactTrustError(
            f"Publication path component {name!r} could not be authenticated after "
            f"creation: {exc}"
        ) from exc


@contextmanager
def open_publication_directory(
    anchor: str | os.PathLike[str], relative_directory: str, *, create: bool = False
) -> Iterator[int]:
    """Descend (optionally creating) a confined directory chain beneath ``anchor``.

    The write side uses exactly the trust discipline the read side does: a
    pre-planted ``models/production`` symlink cannot redirect product bytes out
    of the campaign model root, because every component is opened no-follow
    relative to the previously authenticated descriptor.
    """

    anchor_path = Path(anchor)
    anchor_path.mkdir(parents=True, exist_ok=True)
    try:
        root_fd = os.open(
            str(anchor_path),
            os.O_RDONLY
            | os.O_DIRECTORY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as exc:
        raise ModelArtifactTrustError(
            f"The campaign model root {anchor_path!s} could not be opened as a plain "
            f"directory ({exc.strerror})."
        ) from exc
    open_fds = [root_fd]
    try:
        text = str(relative_directory).strip()
        parts = () if not text else PurePosixPath(
            normalize_relative_artifact_path(text, name="publication_relative_directory")
        ).parts
        for component in parts:
            if create:
                open_fds.append(_open_or_create_directory(component, dir_fd=open_fds[-1]))
            else:
                try:
                    open_fds.append(open_directory_nofollow(component, dir_fd=open_fds[-1]))
                except FileNotFoundError as exc:
                    raise ModelArtifactTrustError(
                        f"Publication directory component {component!r} is absent."
                    ) from exc
                except NamespaceAmbiguity as exc:
                    raise ModelArtifactTrustError(
                        f"Publication directory component {component!r} is not a plain "
                        f"directory: {exc}"
                    ) from exc
        yield open_fds[-1]
    finally:
        for handle in reversed(open_fds):
            try:
                os.close(handle)
            except OSError:
                pass


def place_immutable_file(directory_fd: int, temporary_name: str, final_name: str) -> None:
    """Publish one durable file entry create-once, never overwriting.

    ``os.link`` gives no-clobber placement with no window in which the final
    name exists but is not the complete file; ``os.replace`` is deliberately
    unavailable to immutable model evidence.  The private temp is unlinked
    afterwards, and the containing directory entry is fsynced so a crash cannot
    lose the name a pointer is about to reference.
    """

    try:
        os.link(temporary_name, final_name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
    except FileExistsError:
        raise
    except OSError as exc:
        raise ModelArtifactTrustError(
            f"Immutable model artifact {final_name!r} could not be placed "
            f"({exc.strerror})."
        ) from exc
    try:
        os.fsync(directory_fd)
    except OSError:
        pass


def authenticate_descriptor_leaf(
    directory_fd: int,
    name: str,
    *,
    expected_sha256: str | None = None,
    expected_size_bytes: int | None = None,
) -> AuthenticatedModelArtifact:
    """Authenticate one leaf relative to an already-authenticated directory fd."""

    if Path(name).name != name or not str(name).strip():
        raise ModelArtifactTrustError("A model artifact leaf must be one basename.")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        fd = os.open(name, flags, dir_fd=directory_fd)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise ModelArtifactTrustError(
            f"Model artifact {name!r} could not be opened no-follow ({exc.strerror})."
        ) from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ModelArtifactTrustError(f"Model artifact {name!r} is not a regular file.")
        size, observed = _digest_descriptor(fd)
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
    if expected_size_bytes is not None and size != int(expected_size_bytes):
        raise ModelArtifactTrustError(
            f"Model artifact {name!r} is {size} bytes; {int(expected_size_bytes)} expected."
        )
    if expected_sha256 is not None and observed != validate_digest(
        str(expected_sha256), name="model_sha256"
    ):
        raise ModelArtifactTrustError(
            f"Model artifact {name!r} does not carry the expected bytes."
        )
    return AuthenticatedModelArtifact(relative_path=name, size_bytes=size, sha256=observed)


__all__ = [
    "AuthenticatedModelArtifact",
    "ModelArtifactTrustError",
    "authenticate_descriptor_leaf",
    "authenticate_model_artifact",
    "normalize_relative_artifact_path",
    "open_model_artifact_descriptor",
    "open_publication_directory",
    "place_immutable_file",
    "read_model_artifact_identity",
    "stage_authenticated_model",
]
