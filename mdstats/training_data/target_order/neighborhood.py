"""NEIGHBOR1: the one exact candidate-witness neighborhood relation.

Restored from the mature shared engine (carrier ``3937881e`` blobs ``d678062b``
and the packed-v2 store) and rebound to the single exact ``P_train`` domain.
The relation is D2 section 3.5 exactly::

    A_m(w, c) = 1  <=>  d_m(w, c) <= r_m(w) + 1e-12 * max(1, r_m(w))

realized as a cKDTree ball query on ``x / s`` with radius
``(r + 1e-12*max(1, r)) * sqrt(d)``, witness rows deduplicated to candidate
frames in canonical row-major/candidate-major order.  The normal prepared path
constructs it once, inside the shared FEAS1 pass; MVIDX adopts the published
product.  Execution-only state (workers, blocks, queue, staging paths) never
enters identity.

Persistence keeps the final accepted OOC capabilities: edges stream to an
attempt-owned temporary file, finalization copies through bounded scratch after
disk admission, per-family CSR is packed into two shared roots so mapped file
descriptors are O(1) in family count, and publication is create-or-verify.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.spatial import cKDTree

from .._common import TrainingDataInputError, digest, validate_digest
from .artifact_store import (
    PublishedArtifact,
    TargetOrderArtifactStoreError,
    array_reference,
    close_memmap,
    packed_slice,
    publish_artifact_directory,
    read_manifest,
    read_packed,
    root_memmap,
    write_packed,
)

NEIGHBOR1_FAMILY_SCHEMA = "mdstats.target-coverage-exact-neighborhood-family.v2"
NEIGHBOR1_STORE_SCHEMA = "mdstats.target-coverage-exact-neighborhood-store.v2"
NEIGHBOR1_ARTIFACT_SCHEMA = "mdstats.target-coverage-exact-neighborhood-artifact.v2"
NEIGHBOR1_VERSION = "mdstats.target-order.neighbor1.exact-neighborhood.v1"

EXACT_NEIGHBORHOOD_METRIC_TOLERANCE = 1.0e-12
EXACT_NEIGHBORHOOD_DISTANCE_SEMANTICS = (
    "scaled-euclidean-query-ball-point; radius=(local_radius+1e-12*max(1,local_radius))*sqrt(feature_dimension); "
    "row-neighbors-deduplicated-to-candidate-frame; canonical-row-major-candidate-major"
)

_UINT32_MAX = int(np.iinfo(np.uint32).max)
_FINALIZE_COPY_CHUNK_BYTES = 8 * 1024 * 1024
_FINALIZE_MIN_ADMISSION_BYTES = 64 * 1024


def compress_unique_candidate_block(
    raw_neighbors: Sequence[Any],
    *,
    frame_indices: np.ndarray,
    row_start: int,
    candidate_count: int,
    context: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Canonical local-row/candidate pairs and per-row unique counts.

    Pairs are sorted by local witness row then candidate frame, exactly the
    historical per-row ``np.unique`` order that FEAS1 FP64 reductions rely on.
    Every witness must retain its own frame (self support).
    """

    block_rows = len(raw_neighbors)
    if block_rows == 0:
        empty = np.empty(0, dtype=np.int64)
        return empty, empty, empty
    raw_counts = np.fromiter((len(item) for item in raw_neighbors), dtype=np.int64, count=block_rows)
    if int(np.sum(raw_counts, dtype=np.int64)) <= 0:
        raise TrainingDataInputError(f"{context} neighborhood block contains an unsupported witness.")
    flat = np.concatenate(raw_neighbors).astype(np.int64, copy=False)
    if np.any(flat < 0) or np.any(flat >= len(frame_indices)):
        raise TrainingDataInputError(f"{context} neighborhood query returned an out-of-domain row.")
    local_rows = np.repeat(np.arange(block_rows, dtype=np.int64), raw_counts)
    keys = local_rows * np.int64(candidate_count) + frame_indices[flat]
    unique_keys = np.unique(keys)
    unique_rows = unique_keys // np.int64(candidate_count)
    unique_candidates = unique_keys % np.int64(candidate_count)
    unique_counts = np.bincount(unique_rows, minlength=block_rows).astype(np.int64, copy=False)
    own_keys = np.arange(block_rows, dtype=np.int64) * np.int64(candidate_count) + frame_indices[
        row_start:row_start + block_rows
    ]
    positions = np.searchsorted(unique_keys, own_keys)
    if np.any(positions >= unique_keys.size) or not np.all(unique_keys[np.minimum(positions, unique_keys.size - 1)] == own_keys):
        raise TrainingDataInputError(f"{context} self-support consistency failed.")
    return unique_rows, unique_candidates, unique_counts


def _canonical_csr(values: np.ndarray | Sequence[Any], *, dtype: str, name: str) -> np.ndarray:
    array = np.ascontiguousarray(np.asarray(values, dtype=np.dtype(dtype).newbyteorder("<")))
    if array.ndim != 1:
        raise TrainingDataInputError(f"NEIGHBOR1 {name} must be one-dimensional.")
    array.setflags(write=False)
    return array


def _validate_csr(offsets: np.ndarray, candidates: np.ndarray, *, witness_count: int, candidate_count: int) -> None:
    edge_count = int(candidates.size)
    if offsets.shape != (witness_count + 1,) or int(offsets[0]) != 0 or int(offsets[-1]) != edge_count:
        raise TrainingDataInputError("NEIGHBOR1 witness offsets do not span the candidate edges.")
    if np.any(np.diff(offsets.astype(np.int64, copy=False)) <= 0):
        raise TrainingDataInputError("NEIGHBOR1 every witness must retain exact self support.")
    if edge_count and int(np.max(candidates)) >= candidate_count:
        raise TrainingDataInputError("NEIGHBOR1 witness candidate index exceeds the candidate domain.")
    if edge_count > 1:
        chunk = 8 * 1024 * 1024
        for start in range(0, edge_count - 1, chunk):
            stop = min(edge_count - 1, start + chunk)
            bad = np.flatnonzero(candidates[start + 1:stop + 1] <= candidates[start:stop])
            if bad.size == 0:
                continue
            positions = bad.astype(np.int64) + start + 1
            rows = np.searchsorted(offsets, positions, side="left")
            valid = rows < len(offsets)
            boundary = np.zeros(positions.size, dtype=np.bool_)
            boundary[valid] = offsets[rows[valid]] == positions[valid]
            if np.any(~boundary):
                raise TrainingDataInputError("NEIGHBOR1 witness->candidate rows must be strictly sorted and unique.")


@dataclass(frozen=True, slots=True, eq=False)
class TargetCoverageExactNeighborhoodFamily:
    """Canonical witness-oriented CSR for one reference family."""

    family_id: str
    family_digest: str
    candidate_count: int
    witness_count: int
    witness_offsets: np.ndarray | Sequence[int]
    witness_candidates: np.ndarray | Sequence[int]
    validate: bool = field(default=True, repr=False, compare=False)
    #: Identities of file-authenticated packed slices; recomputed when absent.
    array_references: Mapping[str, Mapping[str, Any]] | None = field(default=None, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not str(self.family_id).strip():
            raise TrainingDataInputError("NEIGHBOR1 family identity cannot be empty.")
        object.__setattr__(self, "family_digest", validate_digest(self.family_digest, name="family_digest"))
        candidate_count = int(self.candidate_count)
        witness_count = int(self.witness_count)
        if not (1 <= candidate_count <= _UINT32_MAX and 1 <= witness_count <= _UINT32_MAX):
            raise TrainingDataInputError("NEIGHBOR1 family cardinality exceeds uint32 range.")
        offsets = _canonical_csr(self.witness_offsets, dtype="<u8", name="witness_offsets")
        candidates = _canonical_csr(self.witness_candidates, dtype="<u4", name="witness_candidates")
        if self.validate:
            _validate_csr(offsets, candidates, witness_count=witness_count, candidate_count=candidate_count)
        object.__setattr__(self, "candidate_count", candidate_count)
        object.__setattr__(self, "witness_count", witness_count)
        object.__setattr__(self, "witness_offsets", offsets)
        object.__setattr__(self, "witness_candidates", candidates)

    @property
    def edge_count(self) -> int:
        return int(len(self.witness_candidates))

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": NEIGHBOR1_FAMILY_SCHEMA,
            "authority_version": NEIGHBOR1_VERSION,
            "metric_tolerance": EXACT_NEIGHBORHOOD_METRIC_TOLERANCE,
            "distance_semantics": EXACT_NEIGHBORHOOD_DISTANCE_SEMANTICS,
            "family_id": self.family_id,
            "family_digest": self.family_digest,
            "candidate_count": self.candidate_count,
            "witness_count": self.witness_count,
            "witness_offsets": self._reference("witness_offsets"),
            "witness_candidates": self._reference("witness_candidates"),
        }

    def _reference(self, name: str) -> dict[str, Any]:
        supplied = None if self.array_references is None else self.array_references.get(name)
        return dict(supplied) if supplied is not None else array_reference(getattr(self, name))

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def witness_candidate_indices(self, witness_index: int) -> np.ndarray:
        row = int(witness_index)
        if row < 0 or row >= self.witness_count:
            raise IndexError(row)
        return self.witness_candidates[int(self.witness_offsets[row]):int(self.witness_offsets[row + 1])]


@dataclass(frozen=True, slots=True, eq=False)
class TargetCoverageExactNeighborhoodStore:
    """The shared NEIGHBOR1 product of one reference generation."""

    dataset_id: str
    target_coverage_reference_digest: str
    frame_domain_digest: str
    candidate_count: int
    families: tuple[TargetCoverageExactNeighborhoodFamily, ...]
    _family_by_id: Mapping[str, TargetCoverageExactNeighborhoodFamily] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("target_coverage_reference_digest", "frame_domain_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        families = tuple(self.families)
        if not families or tuple(item.family_id for item in families) != tuple(sorted(item.family_id for item in families)):
            raise TrainingDataInputError("NEIGHBOR1 families must be non-empty and sorted by family_id.")
        if len({item.family_id for item in families}) != len(families):
            raise TrainingDataInputError("NEIGHBOR1 family IDs are duplicated.")
        if any(item.candidate_count != int(self.candidate_count) for item in families):
            raise TrainingDataInputError("NEIGHBOR1 family/candidate domain mismatch.")
        object.__setattr__(self, "candidate_count", int(self.candidate_count))
        object.__setattr__(self, "families", families)
        object.__setattr__(self, "_family_by_id", {item.family_id: item for item in families})

    def family(self, family_id: str) -> TargetCoverageExactNeighborhoodFamily:
        try:
            return self._family_by_id[family_id]
        except KeyError:
            raise KeyError(family_id) from None

    @property
    def edge_count(self) -> int:
        return int(sum(item.edge_count for item in self.families))

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": NEIGHBOR1_STORE_SCHEMA,
            "authority_version": NEIGHBOR1_VERSION,
            "dataset_id": self.dataset_id,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "frame_domain_digest": self.frame_domain_digest,
            "candidate_count": self.candidate_count,
            "family_content_digests": [item.content_digest for item in self.families],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached


@dataclass(frozen=True, slots=True)
class StagedNeighborhoodFamily:
    """Closed file-backed CSR awaiting packing (attempt-owned)."""

    family_id: str
    family_digest: str
    candidate_count: int
    witness_count: int
    edge_count: int
    witness_offsets_path: Path
    witness_candidates_path: Path
    content_digest: str


@dataclass(slots=True)
class PreparedNeighborhoodFamily:
    """Execution-only scaled family/tree state."""

    family: Any
    candidate_count: int
    frame_indices: np.ndarray
    radii: np.ndarray
    scaled: np.ndarray
    tree: cKDTree
    blocks: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class NeighborhoodBlockResult:
    start: int
    stop: int
    local_rows: np.ndarray
    candidate_indices: np.ndarray
    unique_counts: np.ndarray


def prepare_neighborhood_family(family: Any, *, candidate_count: int, query_block_size: int) -> PreparedNeighborhoodFamily:
    values = np.asarray(family.values, dtype=np.float64)
    scales = np.asarray(family.scales, dtype=np.float64)
    frame_indices = np.asarray(family.frame_indices, dtype=np.int64)
    radii = np.asarray(family.local_radii, dtype=np.float64)
    if values.ndim != 2 or scales.shape != (values.shape[1],) or radii.shape != (len(values),):
        raise TrainingDataInputError(f"NEIGHBOR1 family {family.family_id!r} has inconsistent reference arrays.")
    if np.any(frame_indices < 0) or np.any(frame_indices >= int(candidate_count)):
        raise TrainingDataInputError(f"NEIGHBOR1 family {family.family_id!r} has out-of-domain frame indices.")
    scaled = values / scales[None, :]
    block = max(1, int(query_block_size))
    return PreparedNeighborhoodFamily(
        family=family,
        candidate_count=int(candidate_count),
        frame_indices=frame_indices,
        radii=radii,
        scaled=scaled,
        tree=cKDTree(scaled),
        blocks=tuple((start, min(len(scaled), start + block)) for start in range(0, len(scaled), block)),
    )


def query_neighborhood_block(
    prepared: PreparedNeighborhoodFamily, task: tuple[int, int], *, tree_workers: int, context: str | None = None
) -> NeighborhoodBlockResult:
    start, stop = int(task[0]), int(task[1])
    if start < 0 or stop <= start or stop > len(prepared.scaled):
        raise TrainingDataInputError("NEIGHBOR1 query block is outside the witness domain.")
    raw = prepared.tree.query_ball_point(
        prepared.scaled[start:stop],
        r=(
            prepared.radii[start:stop]
            + EXACT_NEIGHBORHOOD_METRIC_TOLERANCE * np.maximum(1.0, prepared.radii[start:stop])
        )
        * math.sqrt(float(prepared.scaled.shape[1])),
        workers=max(1, int(tree_workers)),
        return_sorted=True,
    )
    local_rows, candidates, counts = compress_unique_candidate_block(
        raw,
        frame_indices=prepared.frame_indices,
        row_start=start,
        candidate_count=prepared.candidate_count,
        context=context or f"NEIGHBOR1 family {prepared.family.family_id!r}",
    )
    return NeighborhoodBlockResult(start, stop, local_rows, candidates, counts)


class NeighborhoodCSRStream:
    """Canonical CSR stream with disk-backed edge staging and bounded finalization."""

    __slots__ = ("prepared", "_handle", "_witness_counts", "_edge_count", "_next_start", "_closed", "_directory")

    def __init__(self, prepared: PreparedNeighborhoodFamily, *, directory: Path) -> None:
        self.prepared = prepared
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)
        self._handle = tempfile.TemporaryFile(mode="w+b", dir=self._directory)
        self._witness_counts = np.zeros(len(prepared.scaled), dtype=np.uint64)
        self._edge_count = 0
        self._next_start = 0
        self._closed = False

    @property
    def edge_count(self) -> int:
        return int(self._edge_count)

    @property
    def final_array_storage_bytes(self) -> int:
        return int((len(self._witness_counts) + 1) * 8 + self._edge_count * 4)

    @property
    def finalization_memory_bytes(self) -> int:
        return max(_FINALIZE_MIN_ADMISSION_BYTES, min(self._edge_count * 4, _FINALIZE_COPY_CHUNK_BYTES))

    def append(self, block: NeighborhoodBlockResult) -> None:
        if self._closed:
            raise RuntimeError("NEIGHBOR1 CSR stream is closed.")
        if int(block.start) != self._next_start or int(block.stop) > len(self._witness_counts):
            raise TrainingDataInputError("NEIGHBOR1 CSR stream received a block outside canonical witness order.")
        encoded = np.asarray(block.candidate_indices, dtype="<u4")
        self._handle.write(memoryview(encoded).cast("B"))
        self._witness_counts[block.start:block.stop] = np.asarray(block.unique_counts, dtype=np.uint64)
        self._edge_count += int(encoded.size)
        self._next_start = int(block.stop)

    def _named_path(self, suffix: str) -> Path:
        fd, name = tempfile.mkstemp(prefix="neighbor1-final-", suffix=suffix, dir=self._directory)
        os.close(fd)
        path = Path(name)
        path.unlink()
        return path

    def finalize_staged(self) -> StagedNeighborhoodFamily:
        """Materialize named file-backed CSR after disk admission; never partial."""

        if self._closed:
            raise RuntimeError("NEIGHBOR1 CSR stream is already finalized.")
        if self._next_start != len(self._witness_counts):
            raise TrainingDataInputError("NEIGHBOR1 CSR stream finalized before all witnesses were committed.")
        if self._edge_count <= 0:
            raise TrainingDataInputError("NEIGHBOR1 streamed CSR contains no candidate edges.")
        required = self.final_array_storage_bytes
        safety = max(1 * 1024**3, int(math.ceil(required * 0.05)))
        free = int(shutil.disk_usage(self._directory).free)
        if free < required + safety:
            raise TrainingDataInputError(
                "NEIGHBOR1 out-of-core finalization requires approximately "
                f"{required / 1024**3:.1f} GiB plus {safety / 1024**3:.1f} GiB safety headroom, "
                f"but only {free / 1024**3:.1f} GiB is free under {self._directory}."
            )
        outputs: list[Path] = []
        try:
            offsets_path = self._named_path("-witness-offsets.npy")
            outputs.append(offsets_path)
            offsets = np.lib.format.open_memmap(
                offsets_path, mode="w+", dtype="<u8", shape=(len(self._witness_counts) + 1,)
            )
            offsets[0] = 0
            np.cumsum(self._witness_counts, dtype=np.uint64, out=offsets[1:])
            offsets.flush()
            if int(offsets[-1]) != self._edge_count:
                raise TrainingDataInputError("NEIGHBOR1 streamed CSR edge count is inconsistent.")
            close_memmap(offsets)
            del offsets
            candidates_path = self._named_path("-witness-candidates.npy")
            outputs.append(candidates_path)
            candidates = np.lib.format.open_memmap(candidates_path, mode="w+", dtype="<u4", shape=(self._edge_count,))
            self._handle.flush()
            self._handle.seek(0)
            chunk_items = max(1, _FINALIZE_COPY_CHUNK_BYTES // 4)
            cursor = 0
            while cursor < self._edge_count:
                count = min(chunk_items, self._edge_count - cursor)
                chunk = np.fromfile(self._handle, dtype="<u4", count=count)
                if chunk.size != count:
                    raise TrainingDataInputError("NEIGHBOR1 streamed CSR edge payload is truncated.")
                candidates[cursor:cursor + count] = chunk
                cursor += count
            candidates.flush()
            close_memmap(candidates)
            del candidates
            self.close()
            family = TargetCoverageExactNeighborhoodFamily(
                family_id=self.prepared.family.family_id,
                family_digest=self.prepared.family.content_digest,
                candidate_count=self.prepared.candidate_count,
                witness_count=len(self.prepared.scaled),
                witness_offsets=np.load(offsets_path, mmap_mode="r", allow_pickle=False),
                witness_candidates=np.load(candidates_path, mmap_mode="r", allow_pickle=False),
            )
            staged = StagedNeighborhoodFamily(
                family_id=family.family_id,
                family_digest=family.family_digest,
                candidate_count=family.candidate_count,
                witness_count=family.witness_count,
                edge_count=family.edge_count,
                witness_offsets_path=offsets_path,
                witness_candidates_path=candidates_path,
                content_digest=family.content_digest,
            )
            close_memmap(family.witness_offsets)
            close_memmap(family.witness_candidates)
            return staged
        except BaseException:
            self.close()
            for path in outputs:
                path.unlink(missing_ok=True)
            raise

    def close(self) -> None:
        if not self._closed:
            self._handle.close()
            self._closed = True

    def __del__(self) -> None:  # pragma: no cover - defensive cleanup
        try:
            self.close()
        except Exception:
            pass


def pack_staged_neighborhood_families(
    staged_families: Sequence[StagedNeighborhoodFamily], *, directory: Path
) -> tuple[TargetCoverageExactNeighborhoodFamily, ...]:
    """Pack closed family files into two shared mappings (O(1) mapped FDs)."""

    staged = tuple(staged_families)
    directory = Path(directory)
    total_offsets = sum(item.witness_count + 1 for item in staged)
    total_edges = sum(item.edge_count for item in staged)
    offsets_path = directory / f"neighbor1-packed-{os.getpid()}-{id(staged)}-offsets.npy"
    candidates_path = directory / f"neighbor1-packed-{os.getpid()}-{id(staged)}-candidates.npy"
    packed_offsets = np.lib.format.open_memmap(offsets_path, mode="w+", dtype="<u8", shape=(total_offsets,))
    packed_candidates = np.lib.format.open_memmap(candidates_path, mode="w+", dtype="<u4", shape=(total_edges,))
    slices: list[tuple[StagedNeighborhoodFamily, int, int, int, int]] = []
    try:
        offset_cursor = 0
        edge_cursor = 0
        for item in staged:
            source_offsets = np.load(item.witness_offsets_path, mmap_mode="r", allow_pickle=False)
            source_candidates = np.load(item.witness_candidates_path, mmap_mode="r", allow_pickle=False)
            try:
                offset_stop = offset_cursor + item.witness_count + 1
                edge_stop = edge_cursor + item.edge_count
                packed_offsets[offset_cursor:offset_stop] = source_offsets
                packed_candidates[edge_cursor:edge_stop] = source_candidates
                slices.append((item, offset_cursor, offset_stop, edge_cursor, edge_stop))
                offset_cursor, edge_cursor = offset_stop, edge_stop
            finally:
                close_memmap(source_offsets)
                close_memmap(source_candidates)
            item.witness_offsets_path.unlink(missing_ok=True)
            item.witness_candidates_path.unlink(missing_ok=True)
        packed_offsets.flush()
        packed_candidates.flush()
        close_memmap(packed_offsets)
        close_memmap(packed_candidates)
        packed_offsets = np.load(offsets_path, mmap_mode="r", allow_pickle=False)
        packed_candidates = np.load(candidates_path, mmap_mode="r", allow_pickle=False)
        families = []
        for item, offset_start, offset_stop, edge_start, edge_stop in slices:
            family = TargetCoverageExactNeighborhoodFamily(
                family_id=item.family_id,
                family_digest=item.family_digest,
                candidate_count=item.candidate_count,
                witness_count=item.witness_count,
                witness_offsets=packed_offsets[offset_start:offset_stop],
                witness_candidates=packed_candidates[edge_start:edge_stop],
                validate=False,
            )
            if family.content_digest != item.content_digest:
                raise TrainingDataInputError(f"NEIGHBOR1 packed family digest changed for {item.family_id!r}.")
            families.append(family)
        return tuple(families)
    except BaseException:
        close_memmap(packed_offsets)
        close_memmap(packed_candidates)
        offsets_path.unlink(missing_ok=True)
        candidates_path.unlink(missing_ok=True)
        raise


def write_exact_neighborhood_store(destination: Path, store: TargetCoverageExactNeighborhoodStore) -> PublishedArtifact:
    def write(directory: Path) -> Mapping[str, Any]:
        offsets, offset_slices = write_packed(
            directory, "packed-witness-offsets.npy", [item.witness_offsets for item in store.families], dtype="<u8"
        )
        candidates, candidate_slices = write_packed(
            directory, "packed-witness-candidates.npy", [item.witness_candidates for item in store.families], dtype="<u4"
        )
        return {
            "schema": NEIGHBOR1_ARTIFACT_SCHEMA,
            "content_digest": store.content_digest,
            "dataset_id": store.dataset_id,
            "target_coverage_reference_digest": store.target_coverage_reference_digest,
            "frame_domain_digest": store.frame_domain_digest,
            "candidate_count": store.candidate_count,
            "packed_arrays": {"witness_offsets": offsets, "witness_candidates": candidates},
            "families": [
                {
                    "family_id": item.family_id,
                    "family_digest": item.family_digest,
                    "witness_count": item.witness_count,
                    "edge_count": item.edge_count,
                    "content_digest": item.content_digest,
                    "array_slices": {
                        "witness_offsets": offset_slices[position],
                        "witness_candidates": candidate_slices[position],
                    },
                }
                for position, item in enumerate(store.families)
            ],
        }

    return publish_artifact_directory(
        destination,
        schema=NEIGHBOR1_ARTIFACT_SCHEMA,
        write=write,
        verify_existing=lambda path, _manifest: None,
    )


def read_exact_neighborhood_store(directory: Path) -> TargetCoverageExactNeighborhoodStore:
    manifest = read_manifest(directory, schema=NEIGHBOR1_ARTIFACT_SCHEMA)
    roots: dict[str, np.memmap] = {}
    try:
        for name in ("witness_offsets", "witness_candidates"):
            roots[name] = read_packed(Path(directory), manifest["packed_arrays"][name], label=f"NEIGHBOR1 {name}")
        cursors = {name: 0 for name in roots}
        families = []
        for payload in manifest["families"]:
            arrays = {}
            for name in roots:
                descriptor = payload["array_slices"][name]
                arrays[name] = packed_slice(roots[name], descriptor, label=f"NEIGHBOR1 {name}", cursor=cursors[name])
                cursors[name] = int(descriptor["stop"])
            family = TargetCoverageExactNeighborhoodFamily(
                family_id=str(payload["family_id"]),
                family_digest=str(payload["family_digest"]),
                candidate_count=int(manifest["candidate_count"]),
                witness_count=int(payload["witness_count"]),
                witness_offsets=arrays["witness_offsets"],
                witness_candidates=arrays["witness_candidates"],
                validate=False,
                array_references={
                    name: payload["array_slices"][name]["array_reference"] for name in roots
                },
            )
            if family.content_digest != payload["content_digest"] or family.edge_count != int(payload["edge_count"]):
                raise TargetOrderArtifactStoreError("NEIGHBOR1 family content identity mismatch.")
            families.append(family)
        if any(cursors[name] != int(roots[name].size) for name in roots):
            raise TargetOrderArtifactStoreError("NEIGHBOR1 packed arrays carry unreferenced data.")
        store = TargetCoverageExactNeighborhoodStore(
            dataset_id=str(manifest["dataset_id"]),
            target_coverage_reference_digest=str(manifest["target_coverage_reference_digest"]),
            frame_domain_digest=str(manifest["frame_domain_digest"]),
            candidate_count=int(manifest["candidate_count"]),
            families=tuple(families),
        )
    except BaseException:
        for root in roots.values():
            close_memmap(root)
        raise
    if store.content_digest != manifest["content_digest"]:
        raise TargetOrderArtifactStoreError("NEIGHBOR1 store content identity mismatch.")
    return store


def validate_exact_neighborhood_store(store: TargetCoverageExactNeighborhoodStore, reference: Any) -> None:
    """Authenticate lineage of an adopted NEIGHBOR1 product (no geometry replay)."""

    if (
        store.target_coverage_reference_digest != reference.content_digest
        or store.frame_domain_digest != reference.frame_domain_digest
        or store.candidate_count != reference.candidate_count
    ):
        raise TrainingDataInputError("NEIGHBOR1 reference lineage mismatch.")
    if tuple(item.family_id for item in store.families) != tuple(item.family_id for item in reference.families):
        raise TrainingDataInputError("NEIGHBOR1 family identities changed.")
    for cached, family in zip(store.families, reference.families, strict=True):
        if cached.family_digest != family.content_digest or cached.witness_count != len(family.values):
            raise TrainingDataInputError(f"NEIGHBOR1 family identity mismatch for {family.family_id!r}.")


__all__ = [
    "EXACT_NEIGHBORHOOD_DISTANCE_SEMANTICS",
    "EXACT_NEIGHBORHOOD_METRIC_TOLERANCE",
    "NeighborhoodBlockResult",
    "NeighborhoodCSRStream",
    "PreparedNeighborhoodFamily",
    "StagedNeighborhoodFamily",
    "TargetCoverageExactNeighborhoodFamily",
    "TargetCoverageExactNeighborhoodStore",
    "compress_unique_candidate_block",
    "pack_staged_neighborhood_families",
    "prepare_neighborhood_family",
    "query_neighborhood_block",
    "read_exact_neighborhood_store",
    "root_memmap",
    "validate_exact_neighborhood_store",
    "write_exact_neighborhood_store",
]
