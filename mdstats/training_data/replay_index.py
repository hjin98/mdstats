"""REPLAY-PERF1 source-bound ExtXYZ byte index and deterministic frame access.

The index is reconstructible execution state.  It is bound to the exact replay
source bytes and the already-authenticated ReplaySourceArtifact, but worker/
chunk choices never enter scientific identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence, TYPE_CHECKING
import json
import os
import tempfile

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    sha256_file_cached,
    validate_digest,
)

if TYPE_CHECKING:  # pragma: no cover
    from .replay import ReplaySourceArtifact

REPLAY_SOURCE_INDEX_SCHEMA = "mdstats.replay-source-index.v1"
REPLAY_SOURCE_INDEX_RECEIPT_SCHEMA = "mdstats.replay-source-index-receipt.v1"
EXTXYZ_SOURCE_INDEX_SCHEMA = "mdstats.extxyz-source-index.v1"
EXTXYZ_SOURCE_INDEX_RECEIPT_SCHEMA = "mdstats.extxyz-source-index-receipt.v1"
DEFAULT_REPLAY_INDEX_PARSE_CHUNK_SIZE = 128


@dataclass(frozen=True, slots=True)
class ExtxyzSourceIndex:
    """Reconstructible byte index for one authenticated immutable ExtXYZ file."""

    source_path: str
    source_sha256: str
    source_artifact_digest: str
    file_size_bytes: int
    frame_offsets: tuple[int, ...]
    frame_lengths: tuple[int, ...]
    atom_counts: tuple[int, ...]
    serialization_schema: str = EXTXYZ_SOURCE_INDEX_SCHEMA

    def __post_init__(self) -> None:
        if self.serialization_schema != EXTXYZ_SOURCE_INDEX_SCHEMA:
            raise TrainingDataInputError("Unsupported ExtXYZ source-index schema.")
        object.__setattr__(self, "source_sha256", validate_digest(self.source_sha256, name="source_sha256"))
        object.__setattr__(
            self, "source_artifact_digest",
            validate_digest(self.source_artifact_digest, name="source_artifact_digest"),
        )
        offsets = tuple(int(value) for value in self.frame_offsets)
        lengths = tuple(int(value) for value in self.frame_lengths)
        counts = tuple(int(value) for value in self.atom_counts)
        if not offsets or not (len(offsets) == len(lengths) == len(counts)):
            raise TrainingDataInputError("ExtXYZ source index arrays are empty or inconsistent.")
        previous_end = 0
        for position, (offset, length, count) in enumerate(zip(offsets, lengths, counts, strict=True)):
            if offset < 0 or length <= 0 or count <= 0:
                raise TrainingDataInputError(f"ExtXYZ source index frame {position} is invalid.")
            if position and offset < previous_end:
                raise TrainingDataInputError("ExtXYZ source index frame ranges overlap or are out of order.")
            previous_end = offset + length
        size = int(self.file_size_bytes)
        if size <= 0 or previous_end > size:
            raise TrainingDataInputError("ExtXYZ source index extends beyond its non-empty source file.")
        object.__setattr__(self, "frame_offsets", offsets)
        object.__setattr__(self, "frame_lengths", lengths)
        object.__setattr__(self, "atom_counts", counts)
        object.__setattr__(self, "file_size_bytes", size)

    @property
    def configuration_count(self) -> int:
        return len(self.frame_offsets)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "source_sha256": self.source_sha256,
            "source_artifact_digest": self.source_artifact_digest,
            "file_size_bytes": self.file_size_bytes,
            "frame_offsets": list(self.frame_offsets),
            "frame_lengths": list(self.frame_lengths),
            "atom_counts": list(self.atom_counts),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(), "source_path": self.source_path,
            "configuration_count": self.configuration_count,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ExtxyzSourceIndex":
        if payload.get("schema") != EXTXYZ_SOURCE_INDEX_SCHEMA:
            raise TrainingDataSerializationError("Unsupported ExtXYZ source-index schema.")
        result = cls(
            source_path=str(payload["source_path"]), source_sha256=str(payload["source_sha256"]),
            source_artifact_digest=str(payload["source_artifact_digest"]),
            file_size_bytes=int(payload["file_size_bytes"]),
            frame_offsets=tuple(int(value) for value in payload["frame_offsets"]),
            frame_lengths=tuple(int(value) for value in payload["frame_lengths"]),
            atom_counts=tuple(int(value) for value in payload["atom_counts"]),
        )
        if payload.get("configuration_count") not in (None, result.configuration_count):
            raise TrainingDataSerializationError("ExtXYZ source-index configuration count mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("ExtXYZ source-index digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ReplaySourceIndex:
    """Byte-level frame index for one immutable replay ExtXYZ source."""

    source_path: str
    source_sha256: str
    source_artifact_digest: str
    source_index_digest: str
    file_size_bytes: int
    frame_offsets: tuple[int, ...]
    frame_lengths: tuple[int, ...]
    atom_counts: tuple[int, ...]
    serialization_schema: str = REPLAY_SOURCE_INDEX_SCHEMA

    def __post_init__(self) -> None:
        if self.serialization_schema != REPLAY_SOURCE_INDEX_SCHEMA:
            raise TrainingDataInputError("Unsupported replay source-index schema.")
        object.__setattr__(self, "source_sha256", validate_digest(self.source_sha256, name="source_sha256"))
        object.__setattr__(
            self,
            "source_artifact_digest",
            validate_digest(self.source_artifact_digest, name="source_artifact_digest"),
        )
        object.__setattr__(
            self,
            "source_index_digest",
            validate_digest(self.source_index_digest, name="source_index_digest"),
        )
        offsets = tuple(int(v) for v in self.frame_offsets)
        lengths = tuple(int(v) for v in self.frame_lengths)
        natoms = tuple(int(v) for v in self.atom_counts)
        if not offsets or not (len(offsets) == len(lengths) == len(natoms)):
            raise TrainingDataInputError("Replay source index arrays are empty or inconsistent.")
        if int(self.file_size_bytes) <= 0:
            raise TrainingDataInputError("Replay source index file size must be positive.")
        previous_end = 0
        for index, (offset, length, count) in enumerate(zip(offsets, lengths, natoms, strict=True)):
            if offset < 0 or length <= 0 or count <= 0:
                raise TrainingDataInputError(f"Replay source index frame {index} is invalid.")
            if index and offset < previous_end:
                raise TrainingDataInputError("Replay source index frame ranges overlap or are out of order.")
            previous_end = offset + length
        if previous_end > int(self.file_size_bytes):
            raise TrainingDataInputError("Replay source index extends beyond the source file.")
        object.__setattr__(self, "frame_offsets", offsets)
        object.__setattr__(self, "frame_lengths", lengths)
        object.__setattr__(self, "atom_counts", natoms)
        object.__setattr__(self, "file_size_bytes", int(self.file_size_bytes))

    @property
    def configuration_count(self) -> int:
        return len(self.frame_offsets)

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "source_sha256": self.source_sha256,
            "source_artifact_digest": self.source_artifact_digest,
            "source_index_digest": self.source_index_digest,
            "file_size_bytes": self.file_size_bytes,
            "frame_offsets": list(self.frame_offsets),
            "frame_lengths": list(self.frame_lengths),
            "atom_counts": list(self.atom_counts),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._identity_payload(),
            "source_path": self.source_path,
            "configuration_count": self.configuration_count,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReplaySourceIndex":
        if payload.get("schema") != REPLAY_SOURCE_INDEX_SCHEMA:
            raise TrainingDataSerializationError("Unsupported replay source-index schema.")
        result = cls(
            source_path=str(payload["source_path"]),
            source_sha256=str(payload["source_sha256"]),
            source_artifact_digest=str(payload["source_artifact_digest"]),
            source_index_digest=str(payload["source_index_digest"]),
            file_size_bytes=int(payload["file_size_bytes"]),
            frame_offsets=tuple(int(v) for v in payload["frame_offsets"]),
            frame_lengths=tuple(int(v) for v in payload["frame_lengths"]),
            atom_counts=tuple(int(v) for v in payload["atom_counts"]),
        )
        if payload.get("configuration_count") not in (None, result.configuration_count):
            raise TrainingDataSerializationError("Replay source-index configuration count mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Replay source-index digest mismatch.")
        return result


def _scan_extxyz_frame_ranges(path: Path) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    offsets: list[int] = []
    lengths: list[int] = []
    atom_counts: list[int] = []
    with path.open("rb") as handle:
        while True:
            start = handle.tell()
            line = handle.readline()
            if not line:
                break
            if not line.strip():
                # ASE tolerates whitespace between frames.  It is not part of
                # the indexed frame payload and therefore need not be parsed.
                continue
            try:
                natoms = int(line.strip())
            except ValueError as exc:
                raise TrainingDataInputError(
                    f"Replay ExtXYZ frame at byte {start} does not start with an integer atom count."
                ) from exc
            if natoms <= 0:
                raise TrainingDataInputError(f"Replay ExtXYZ frame at byte {start} has non-positive atom count.")
            if not handle.readline():
                raise TrainingDataInputError("Replay ExtXYZ source ended before a frame comment line.")
            for _ in range(natoms):
                if not handle.readline():
                    raise TrainingDataInputError("Replay ExtXYZ source ended inside an atom table.")
            end = handle.tell()
            offsets.append(start)
            lengths.append(end - start)
            atom_counts.append(natoms)
    if not offsets:
        raise TrainingDataInputError("Replay ExtXYZ source contains no indexable configurations.")
    return tuple(offsets), tuple(lengths), tuple(atom_counts)


def _index_receipt_path(cache_directory: str | Path) -> Path:
    return Path(cache_directory).expanduser().resolve() / "replay-source-index.json"


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_extxyz_source_index(index: ExtxyzSourceIndex) -> None:
    source_path = Path(index.source_path).expanduser().resolve()
    if not source_path.is_file():
        raise TrainingDataInputError(f"ExtXYZ source file does not exist: {source_path!s}.")
    if int(source_path.stat().st_size) != index.file_size_bytes:
        raise TrainingDataInputError("ExtXYZ source index file-size authority differs from the source bytes.")
    if sha256_file_cached(source_path) != index.source_sha256:
        raise TrainingDataInputError("ExtXYZ source bytes differ from the authenticated index authority.")


def build_extxyz_source_index(
    source_path: str | Path,
    *,
    source_sha256: str,
    source_artifact_digest: str,
    cache_directory: str | Path | None = None,
) -> ExtxyzSourceIndex:
    """Load or atomically build a generic authenticated immutable ExtXYZ index."""

    path = Path(source_path).expanduser().resolve()
    expected_sha = validate_digest(source_sha256, name="source_sha256")
    artifact_digest = validate_digest(source_artifact_digest, name="source_artifact_digest")
    if not path.is_file() or sha256_file_cached(path) != expected_sha:
        raise TrainingDataInputError("ExtXYZ source bytes are missing or differ from their authority.")
    receipt = None
    if cache_directory is not None:
        receipt = Path(cache_directory).expanduser().resolve() / "extxyz-source-index.json"
    if receipt is not None and receipt.is_file():
        try:
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            if payload.get("schema") == EXTXYZ_SOURCE_INDEX_RECEIPT_SCHEMA:
                loaded = ExtxyzSourceIndex.from_dict(payload["index"])
                rebound = ExtxyzSourceIndex(
                    source_path=str(path), source_sha256=loaded.source_sha256,
                    source_artifact_digest=loaded.source_artifact_digest,
                    file_size_bytes=loaded.file_size_bytes, frame_offsets=loaded.frame_offsets,
                    frame_lengths=loaded.frame_lengths, atom_counts=loaded.atom_counts,
                )
                if rebound.source_artifact_digest != artifact_digest:
                    raise TrainingDataInputError("ExtXYZ source artifact identity changed.")
                validate_extxyz_source_index(rebound)
                return rebound
        except Exception:
            pass
    offsets, lengths, counts = _scan_extxyz_frame_ranges(path)
    result = ExtxyzSourceIndex(
        source_path=str(path), source_sha256=expected_sha,
        source_artifact_digest=artifact_digest, file_size_bytes=int(path.stat().st_size),
        frame_offsets=offsets, frame_lengths=lengths, atom_counts=counts,
    )
    validate_extxyz_source_index(result)
    if receipt is not None:
        _atomic_json(
            receipt, {"schema": EXTXYZ_SOURCE_INDEX_RECEIPT_SCHEMA, "index": result.to_dict()}
        )
    return result


def validate_replay_source_index(source: "ReplaySourceArtifact", index: ReplaySourceIndex) -> None:
    source_path = Path(source.path).expanduser().resolve()
    if index.source_sha256 != source.sha256:
        raise TrainingDataInputError("Replay source index SHA authority differs from the replay source artifact.")
    if index.source_artifact_digest != source.content_digest:
        raise TrainingDataInputError("Replay source index artifact authority differs from the replay source artifact.")
    if index.source_index_digest != source.source_index_digest:
        raise TrainingDataInputError("Replay source index geometry-order authority differs from the replay source artifact.")
    if index.configuration_count != source.configuration_count:
        raise TrainingDataInputError("Replay source index frame count differs from the replay source artifact.")
    if tuple(index.atom_counts) and len(index.atom_counts) != source.configuration_count:
        raise TrainingDataInputError("Replay source index atom-count cardinality is invalid.")
    if not source_path.is_file():
        raise TrainingDataInputError(f"Replay source file does not exist: {source_path!s}.")
    stat = source_path.stat()
    if int(stat.st_size) != index.file_size_bytes:
        raise TrainingDataInputError("Replay source index file-size authority differs from the replay source bytes.")
    if sha256_file_cached(source_path) != source.sha256:
        raise TrainingDataInputError("Replay source bytes differ from their authenticated source artifact.")


def build_replay_source_index(
    source: "ReplaySourceArtifact",
    cache_directory: str | Path | None = None,
) -> ReplaySourceIndex:
    """Load or build the exact byte index for ``source``.

    The persisted cache is invalidated only by source/artifact identity.  Chunk
    size and later materialization worker choices are deliberately absent from
    the index identity.
    """

    source_path = Path(source.path).expanduser().resolve()
    if not source_path.is_file():
        raise TrainingDataInputError(f"Replay source file does not exist: {source_path!s}.")
    if sha256_file_cached(source_path) != source.sha256:
        raise TrainingDataInputError("Replay source bytes differ from their authenticated source artifact.")

    receipt = None if cache_directory is None else _index_receipt_path(cache_directory)
    if receipt is not None and receipt.is_file():
        try:
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            if payload.get("schema") == REPLAY_SOURCE_INDEX_RECEIPT_SCHEMA:
                loaded = ReplaySourceIndex.from_dict(payload["index"])
                rebound = ReplaySourceIndex(
                    source_path=str(source_path),
                    source_sha256=loaded.source_sha256,
                    source_artifact_digest=loaded.source_artifact_digest,
                    source_index_digest=loaded.source_index_digest,
                    file_size_bytes=loaded.file_size_bytes,
                    frame_offsets=loaded.frame_offsets,
                    frame_lengths=loaded.frame_lengths,
                    atom_counts=loaded.atom_counts,
                )
                validate_replay_source_index(source, rebound)
                return rebound
        except Exception:
            # Reconstructible execution state: stale/corrupt receipts are simply
            # rebuilt from authenticated source bytes.
            pass

    offsets, lengths, atom_counts = _scan_extxyz_frame_ranges(source_path)
    result = ReplaySourceIndex(
        source_path=str(source_path),
        source_sha256=source.sha256,
        source_artifact_digest=source.content_digest,
        source_index_digest=source.source_index_digest,
        file_size_bytes=int(source_path.stat().st_size),
        frame_offsets=offsets,
        frame_lengths=lengths,
        atom_counts=atom_counts,
    )
    validate_replay_source_index(source, result)
    if receipt is not None:
        _atomic_json(receipt, {"schema": REPLAY_SOURCE_INDEX_RECEIPT_SCHEMA, "index": result.to_dict()})
    return result


def replay_source_indices_for_identities(
    source: "ReplaySourceArtifact",
    identities: Iterable[str],
) -> tuple[int, ...]:
    requested = set(str(v) for v in identities)
    mapping = {identity: index for index, identity in enumerate(source.geometry_identities)}
    missing = requested - mapping.keys()
    if missing:
        raise TrainingDataInputError(f"Replay indexed materialization requested {len(missing)} unknown geometries.")
    return tuple(sorted(mapping[value] for value in requested))


def _normalize_indices(count: int, source_indices: Sequence[int] | None) -> tuple[int, ...]:
    if source_indices is None:
        return tuple(range(count))
    values = tuple(int(v) for v in source_indices)
    if any(v < 0 or v >= count for v in values):
        raise TrainingDataInputError("Replay indexed source selection is out of bounds.")
    if any(a >= b for a, b in zip(values, values[1:])):
        raise TrainingDataInputError("Replay indexed source selection must be strictly increasing and unique.")
    return values


def _contiguous_groups(indices: Sequence[int], *, maximum_frames: int) -> Iterator[tuple[int, ...]]:
    if maximum_frames <= 0:
        raise TrainingDataInputError("Replay indexed parse chunk size must be positive.")
    current: list[int] = []
    previous: int | None = None
    for value in indices:
        if current and (value != (previous or 0) + 1 or len(current) >= maximum_frames):
            yield tuple(current)
            current = []
        current.append(value)
        previous = value
    if current:
        yield tuple(current)


def iter_indexed_extxyz_frames(
    index: ExtxyzSourceIndex,
    *,
    source_indices: Sequence[int] | None = None,
    chunk_size: int = DEFAULT_REPLAY_INDEX_PARSE_CHUNK_SIZE,
) -> Iterator[tuple[int, Any]]:
    """Yield exact requested frames in deterministic source-index order."""

    validate_extxyz_source_index(index)
    requested = _normalize_indices(index.configuration_count, source_indices)
    if not requested:
        return
    try:
        from ase.io import read
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for indexed ExtXYZ parsing.") from exc
    source_path = Path(index.source_path).expanduser().resolve()
    with source_path.open("rb") as handle:
        for group in _contiguous_groups(requested, maximum_frames=int(chunk_size)):
            first, last = group[0], group[-1]
            start = index.frame_offsets[first]
            end = index.frame_offsets[last] + index.frame_lengths[last]
            handle.seek(start)
            payload = handle.read(end - start)
            try:
                text = payload.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise TrainingDataInputError("ExtXYZ indexed payload is not valid UTF-8.") from exc
            parsed = read(StringIO(text), index=":", format="extxyz")
            frames = parsed if isinstance(parsed, list) else [parsed]
            if len(frames) != len(group):
                raise TrainingDataInputError("ExtXYZ indexed chunk parser returned the wrong frame count.")
            for source_index, atoms in zip(group, frames, strict=True):
                if len(atoms) != index.atom_counts[source_index]:
                    raise TrainingDataInputError("ExtXYZ indexed frame atom count differs from the byte index.")
                yield source_index, atoms


def iter_indexed_replay_frames(
    source: "ReplaySourceArtifact",
    index: ReplaySourceIndex,
    *,
    source_indices: Sequence[int] | None = None,
    chunk_size: int = DEFAULT_REPLAY_INDEX_PARSE_CHUNK_SIZE,
) -> Iterator[tuple[int, Any]]:
    """Yield ASE frames for exact source indices without scanning unrelated frames.

    Contiguous requested frames are parsed as bounded chunks.  Sparse requests
    seek directly to indexed frame payloads.  Yield order is always increasing
    source index, independent of chunk size.
    """

    validate_replay_source_index(source, index)
    generic = ExtxyzSourceIndex(
        source_path=str(Path(source.path).expanduser().resolve()),
        source_sha256=index.source_sha256,
        source_artifact_digest=index.source_artifact_digest,
        file_size_bytes=index.file_size_bytes,
        frame_offsets=index.frame_offsets,
        frame_lengths=index.frame_lengths,
        atom_counts=index.atom_counts,
    )
    yield from iter_indexed_extxyz_frames(
        generic, source_indices=source_indices, chunk_size=chunk_size
    )


__all__ = [
    "DEFAULT_REPLAY_INDEX_PARSE_CHUNK_SIZE",
    "EXTXYZ_SOURCE_INDEX_RECEIPT_SCHEMA",
    "EXTXYZ_SOURCE_INDEX_SCHEMA",
    "REPLAY_SOURCE_INDEX_RECEIPT_SCHEMA",
    "REPLAY_SOURCE_INDEX_SCHEMA",
    "ExtxyzSourceIndex",
    "ReplaySourceIndex",
    "build_extxyz_source_index",
    "build_replay_source_index",
    "iter_indexed_extxyz_frames",
    "iter_indexed_replay_frames",
    "replay_source_indices_for_identities",
    "validate_extxyz_source_index",
    "validate_replay_source_index",
]
