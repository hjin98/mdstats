"""NEIGHBOR1 shared exact TARGET-DATA2B/C neighborhood engine.

This module is an execution substrate, not a new scientific coverage authority.
It computes the exact witness-row -> unique candidate-frame relation once using
the frozen TARGET-DATA2B scaled-Euclidean semantics and exposes canonical
witness-oriented CSR suitable for both FEAS1 reduction and MVIDX1 adoption.

Execution knobs such as worker count, query block size, queue depth, and memory
admission never enter cache identity.  Scientific identity is bound to the
candidate-domain ordering, TARGET-DATA2B family identity, witness cardinality,
metric/tolerance semantics, and cache-format version.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from scipy.spatial import cKDTree

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from ._target_coverage_neighborhood import compress_unique_candidate_block
from .resources import StageResourceScope, available_cpu_threads
from .target_coverage import _coverage_array_reference, _validate_array_reference
from .progress_timing import format_progress_fraction, format_progress_time
from .work_queue import DeterministicOrderedReducer, DeterministicWorkQueue, DeterministicWorkQueueSnapshot


TARGET_COVERAGE_EXACT_NEIGHBORHOOD_FAMILY_SCHEMA = "mdstats.target-coverage-exact-neighborhood-family.v1"
TARGET_COVERAGE_EXACT_NEIGHBORHOOD_DOMAIN_SCHEMA = "mdstats.target-coverage-exact-neighborhood-domain.v1"
TARGET_COVERAGE_EXACT_NEIGHBORHOOD_STORE_SCHEMA = "mdstats.target-coverage-exact-neighborhood-store.v1"
TARGET_COVERAGE_EXACT_NEIGHBORHOOD_VERSION = "mdstats.target-data2b-neighbor1.exact-neighborhood.2026-08.v1"
TARGET_COVERAGE_EXACT_NEIGHBORHOOD_PERSISTENCE_VERSION = "mdstats.target-data2b-neighbor1.native-persistence.2026-08.v1"

EXACT_NEIGHBORHOOD_METRIC_TOLERANCE = 1.0e-12
EXACT_NEIGHBORHOOD_DISTANCE_SEMANTICS = (
    "scaled-euclidean-query-ball-point; radius=(local_radius+1e-12*max(1,local_radius))*sqrt(feature_dimension); "
    "row-neighbors-deduplicated-to-candidate-frame; canonical-row-major-candidate-major"
)

_UINT32_MAX = int(np.iinfo(np.uint32).max)


def _canonical_array(values: np.ndarray | Sequence[Any], *, dtype: str, ndim: int, name: str) -> np.ndarray:
    target = np.dtype(dtype).newbyteorder("<")
    array = np.asarray(values, dtype=target)
    if array.ndim != ndim:
        raise TrainingDataInputError(f"NEIGHBOR1 {name} must have {ndim} dimensions.")
    array = np.ascontiguousarray(array, dtype=target)
    array.setflags(write=False)
    return array


def _validate_offsets(offsets: np.ndarray, *, item_count: int, edge_count: int) -> None:
    if offsets.shape != (item_count + 1,):
        raise TrainingDataInputError("NEIGHBOR1 witness_offsets are misaligned.")
    if int(offsets[0]) != 0 or int(offsets[-1]) != edge_count:
        raise TrainingDataInputError("NEIGHBOR1 witness_offsets do not span witness_candidates.")
    if np.any(offsets[1:] < offsets[:-1]):
        raise TrainingDataInputError("NEIGHBOR1 witness_offsets are not monotone.")


def _validate_sorted_unique_rows(offsets: np.ndarray, indices: np.ndarray) -> None:
    for start, stop in zip(offsets[:-1], offsets[1:], strict=True):
        row = indices[int(start):int(stop)]
        if row.size > 1 and np.any(row[1:] <= row[:-1]):
            raise TrainingDataInputError(
                "NEIGHBOR1 witness->candidate rows must be strictly sorted and duplicate-free."
            )


@dataclass(frozen=True, slots=True)
class TargetCoverageExactNeighborhoodFamily:
    """Canonical witness-oriented CSR for one exact TARGET-DATA2B family."""

    label_domain_id: str
    frame_domain_digest: str
    family_id: str
    family_digest: str
    candidate_count: int
    witness_count: int
    witness_offsets: np.ndarray | Sequence[int]
    witness_candidates: np.ndarray | Sequence[int]
    metric_tolerance: float = EXACT_NEIGHBORHOOD_METRIC_TOLERANCE
    distance_semantics: str = EXACT_NEIGHBORHOOD_DISTANCE_SEMANTICS
    authority_version: str = TARGET_COVERAGE_EXACT_NEIGHBORHOOD_VERSION
    _identity_digest_cache: str = field(default="", init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        domain_id = str(self.label_domain_id).strip()
        family_id = str(self.family_id).strip()
        if not domain_id or not family_id:
            raise TrainingDataInputError("NEIGHBOR1 domain/family identity cannot be empty.")
        frame_digest = validate_digest(self.frame_domain_digest, name="frame_domain_digest")
        family_digest = validate_digest(self.family_digest, name="family_digest")
        candidate_count = int(self.candidate_count)
        witness_count = int(self.witness_count)
        if (
            candidate_count < 1
            or witness_count < 1
            or candidate_count > _UINT32_MAX
            or witness_count > _UINT32_MAX
        ):
            raise TrainingDataInputError("NEIGHBOR1 family cardinality exceeds uint32 range.")
        if not math.isclose(
            float(self.metric_tolerance), EXACT_NEIGHBORHOOD_METRIC_TOLERANCE, rel_tol=0.0, abs_tol=0.0
        ):
            raise TrainingDataInputError("NEIGHBOR1 metric tolerance is not the frozen exact value.")
        if str(self.distance_semantics) != EXACT_NEIGHBORHOOD_DISTANCE_SEMANTICS:
            raise TrainingDataInputError("NEIGHBOR1 distance semantics changed.")
        if str(self.authority_version) != TARGET_COVERAGE_EXACT_NEIGHBORHOOD_VERSION:
            raise TrainingDataInputError("Unsupported NEIGHBOR1 cache-format version.")
        offsets = _canonical_array(self.witness_offsets, dtype="<u8", ndim=1, name="witness_offsets")
        candidates = _canonical_array(self.witness_candidates, dtype="<u4", ndim=1, name="witness_candidates")
        edge_count = int(candidates.size)
        _validate_offsets(offsets, item_count=witness_count, edge_count=edge_count)
        if edge_count and int(np.max(candidates)) >= candidate_count:
            raise TrainingDataInputError("NEIGHBOR1 witness candidate index exceeds candidate domain.")
        _validate_sorted_unique_rows(offsets, candidates)
        if np.any(np.diff(offsets.astype(np.int64, copy=False)) <= 0):
            raise TrainingDataInputError("NEIGHBOR1 every witness must retain exact self support.")
        object.__setattr__(self, "label_domain_id", domain_id)
        object.__setattr__(self, "frame_domain_digest", frame_digest)
        object.__setattr__(self, "family_id", family_id)
        object.__setattr__(self, "family_digest", family_digest)
        object.__setattr__(self, "candidate_count", candidate_count)
        object.__setattr__(self, "witness_count", witness_count)
        object.__setattr__(self, "witness_offsets", offsets)
        object.__setattr__(self, "witness_candidates", candidates)
        object.__setattr__(self, "metric_tolerance", float(self.metric_tolerance))
        object.__setattr__(self, "distance_semantics", str(self.distance_semantics))
        object.__setattr__(self, "authority_version", str(self.authority_version))

    @property
    def edge_count(self) -> int:
        return int(len(self.witness_candidates))

    def _identity_payload(self) -> dict[str, Any]:
        # Deliberately excludes all execution-only worker/block/queue settings.
        return {
            "schema": TARGET_COVERAGE_EXACT_NEIGHBORHOOD_FAMILY_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "frame_domain_digest": self.frame_domain_digest,
            "family_id": self.family_id,
            "family_digest": self.family_digest,
            "candidate_count": self.candidate_count,
            "witness_count": self.witness_count,
            "metric_tolerance": self.metric_tolerance,
            "distance_semantics": self.distance_semantics,
            "authority_version": self.authority_version,
        }

    @property
    def identity_digest(self) -> str:
        cached = self._identity_digest_cache
        if not cached:
            cached = digest(self._identity_payload())
            object.__setattr__(self, "_identity_digest_cache", cached)
        return cached

    def _digest_payload(self) -> dict[str, Any]:
        return {
            **self._identity_payload(),
            "identity_digest": self.identity_digest,
            "witness_offsets": _coverage_array_reference(self.witness_offsets),
            "witness_candidates": _coverage_array_reference(self.witness_candidates),
        }

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
        start, stop = int(self.witness_offsets[row]), int(self.witness_offsets[row + 1])
        return self.witness_candidates[start:stop]

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._digest_payload(),
            "witness_offsets": self.witness_offsets.tolist(),
            "witness_candidates": self.witness_candidates.tolist(),
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageExactNeighborhoodFamily":
        if payload.get("schema") != TARGET_COVERAGE_EXACT_NEIGHBORHOOD_FAMILY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported NEIGHBOR1 family schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            frame_domain_digest=str(payload["frame_domain_digest"]),
            family_id=str(payload["family_id"]),
            family_digest=str(payload["family_digest"]),
            candidate_count=int(payload["candidate_count"]),
            witness_count=int(payload["witness_count"]),
            witness_offsets=payload["witness_offsets"],
            witness_candidates=payload["witness_candidates"],
            metric_tolerance=float(payload["metric_tolerance"]),
            distance_semantics=str(payload["distance_semantics"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("identity_digest") not in (None, result.identity_digest):
            raise TrainingDataSerializationError("NEIGHBOR1 family identity digest mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("NEIGHBOR1 family content digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageExactNeighborhoodDomain:
    label_domain_id: str
    frame_domain_digest: str
    candidate_count: int
    families: tuple[TargetCoverageExactNeighborhoodFamily, ...]
    authority_version: str = TARGET_COVERAGE_EXACT_NEIGHBORHOOD_VERSION
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        domain_id = str(self.label_domain_id).strip()
        if not domain_id:
            raise TrainingDataInputError("NEIGHBOR1 label_domain_id cannot be empty.")
        frame_digest = validate_digest(self.frame_domain_digest, name="frame_domain_digest")
        candidate_count = int(self.candidate_count)
        if candidate_count < 1 or candidate_count > _UINT32_MAX:
            raise TrainingDataInputError("NEIGHBOR1 domain candidate_count exceeds uint32 range.")
        families = tuple(self.families)
        if not families:
            raise TrainingDataInputError("NEIGHBOR1 domain requires at least one family.")
        if tuple(item.family_id for item in families) != tuple(sorted(item.family_id for item in families)):
            raise TrainingDataInputError("NEIGHBOR1 domain families must be sorted by family_id.")
        if len({item.family_id for item in families}) != len(families):
            raise TrainingDataInputError("NEIGHBOR1 domain family IDs are duplicated.")
        for item in families:
            if (
                item.label_domain_id != domain_id
                or item.frame_domain_digest != frame_digest
                or item.candidate_count != candidate_count
            ):
                raise TrainingDataInputError("NEIGHBOR1 family/domain lineage mismatch.")
        if str(self.authority_version) != TARGET_COVERAGE_EXACT_NEIGHBORHOOD_VERSION:
            raise TrainingDataInputError("Unsupported NEIGHBOR1 domain version.")
        object.__setattr__(self, "label_domain_id", domain_id)
        object.__setattr__(self, "frame_domain_digest", frame_digest)
        object.__setattr__(self, "candidate_count", candidate_count)
        object.__setattr__(self, "families", families)
        object.__setattr__(self, "authority_version", str(self.authority_version))

    def family(self, family_id: str) -> TargetCoverageExactNeighborhoodFamily:
        for item in self.families:
            if item.family_id == family_id:
                return item
        raise KeyError(family_id)

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_EXACT_NEIGHBORHOOD_DOMAIN_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "frame_domain_digest": self.frame_domain_digest,
            "candidate_count": self.candidate_count,
            "family_content_digests": [item.content_digest for item in self.families],
            "authority_version": self.authority_version,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._digest_payload(),
            "families": [item.to_dict() for item in self.families],
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageExactNeighborhoodDomain":
        if payload.get("schema") != TARGET_COVERAGE_EXACT_NEIGHBORHOOD_DOMAIN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported NEIGHBOR1 domain schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            frame_domain_digest=str(payload["frame_domain_digest"]),
            candidate_count=int(payload["candidate_count"]),
            families=tuple(TargetCoverageExactNeighborhoodFamily.from_dict(item) for item in payload["families"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("family_content_digests") not in (
            None,
            [item.content_digest for item in result.families],
        ):
            raise TrainingDataSerializationError("NEIGHBOR1 domain family-digest mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("NEIGHBOR1 domain content digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageExactNeighborhoodStore:
    """Content-addressed execution cache spanning every TARGET-DATA2B family."""

    dataset_id: str
    target_coverage_reference_digest: str
    domains: tuple[TargetCoverageExactNeighborhoodDomain, ...]
    authority_version: str = TARGET_COVERAGE_EXACT_NEIGHBORHOOD_VERSION
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        dataset_id = str(self.dataset_id).strip()
        if not dataset_id:
            raise TrainingDataInputError("NEIGHBOR1 dataset_id cannot be empty.")
        reference_digest = validate_digest(
            self.target_coverage_reference_digest, name="target_coverage_reference_digest"
        )
        domains = tuple(self.domains)
        if not domains:
            raise TrainingDataInputError("NEIGHBOR1 store requires at least one domain.")
        if tuple(item.label_domain_id for item in domains) != tuple(sorted(item.label_domain_id for item in domains)):
            raise TrainingDataInputError("NEIGHBOR1 domains must be sorted by label_domain_id.")
        if len({item.label_domain_id for item in domains}) != len(domains):
            raise TrainingDataInputError("NEIGHBOR1 domain IDs are duplicated.")
        if str(self.authority_version) != TARGET_COVERAGE_EXACT_NEIGHBORHOOD_VERSION:
            raise TrainingDataInputError("Unsupported NEIGHBOR1 store version.")
        object.__setattr__(self, "dataset_id", dataset_id)
        object.__setattr__(self, "target_coverage_reference_digest", reference_digest)
        object.__setattr__(self, "domains", domains)
        object.__setattr__(self, "authority_version", str(self.authority_version))

    def domain(self, label_domain_id: str) -> TargetCoverageExactNeighborhoodDomain:
        for item in self.domains:
            if item.label_domain_id == label_domain_id:
                return item
        raise KeyError(label_domain_id)

    @property
    def edge_count(self) -> int:
        return int(sum(item.edge_count for domain in self.domains for item in domain.families))

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_EXACT_NEIGHBORHOOD_STORE_SCHEMA,
            "dataset_id": self.dataset_id,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "domain_content_digests": [item.content_digest for item in self.domains],
            "authority_version": self.authority_version,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._digest_payload(),
            "domains": [item.to_dict() for item in self.domains],
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageExactNeighborhoodStore":
        if payload.get("schema") != TARGET_COVERAGE_EXACT_NEIGHBORHOOD_STORE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported NEIGHBOR1 store schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            target_coverage_reference_digest=str(payload["target_coverage_reference_digest"]),
            domains=tuple(TargetCoverageExactNeighborhoodDomain.from_dict(item) for item in payload["domains"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("domain_content_digests") not in (
            None,
            [item.content_digest for item in result.domains],
        ):
            raise TrainingDataSerializationError("NEIGHBOR1 store domain-digest mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("NEIGHBOR1 store content digest mismatch.")
        return result


@dataclass(slots=True)
class ExactNeighborhoodPreparedFamily:
    """Execution-only scaled family/tree state."""

    label_domain_id: str
    frame_domain_digest: str
    family: Any
    candidate_count: int
    values: np.ndarray
    scales: np.ndarray
    frame_indices: np.ndarray
    radii: np.ndarray
    scaled: np.ndarray
    tree: cKDTree
    blocks: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class ExactNeighborhoodBlockResult:
    start: int
    stop: int
    local_rows: np.ndarray
    candidate_indices: np.ndarray
    unique_counts: np.ndarray

    @property
    def edge_count(self) -> int:
        return int(self.candidate_indices.size)


class ExactNeighborhoodCSRStream:
    """Canonical block-ordered CSR stream with disk-backed ragged edge staging."""

    __slots__ = (
        "prepared", "_handle", "_witness_counts", "_edge_count", "_next_start", "_closed"
    )

    def __init__(self, prepared: ExactNeighborhoodPreparedFamily) -> None:
        self.prepared = prepared
        self._handle = tempfile.TemporaryFile(mode="w+b")
        self._witness_counts = np.zeros(len(prepared.scaled), dtype=np.uint64)
        self._edge_count = 0
        self._next_start = 0
        self._closed = False

    @property
    def edge_count(self) -> int:
        return int(self._edge_count)

    @property
    def final_array_memory_bytes(self) -> int:
        """Exact bytes allocated by ``finalize`` for CSR offsets and indices."""

        return int((len(self._witness_counts) + 1) * np.dtype("<u8").itemsize + self._edge_count * np.dtype("<u4").itemsize)

    def append(self, block: ExactNeighborhoodBlockResult) -> None:
        if self._closed:
            raise RuntimeError("NEIGHBOR1 CSR stream is closed.")
        if int(block.start) != self._next_start:
            raise TrainingDataInputError(
                "NEIGHBOR1 CSR stream received a block outside canonical witness order."
            )
        if int(block.stop) <= int(block.start) or int(block.stop) > len(self._witness_counts):
            raise TrainingDataInputError("NEIGHBOR1 CSR stream received an invalid witness block.")
        encoded = np.asarray(block.candidate_indices, dtype="<u4")
        self._handle.write(memoryview(encoded).cast("B"))
        self._witness_counts[block.start:block.stop] = np.asarray(block.unique_counts, dtype=np.uint64)
        self._edge_count += int(encoded.size)
        self._next_start = int(block.stop)

    def finalize(self) -> TargetCoverageExactNeighborhoodFamily:
        if self._closed:
            raise RuntimeError("NEIGHBOR1 CSR stream is already finalized.")
        if self._next_start != len(self._witness_counts):
            raise TrainingDataInputError("NEIGHBOR1 CSR stream finalized before all witnesses were committed.")
        offsets = np.empty(len(self._witness_counts) + 1, dtype="<u8")
        offsets[0] = 0
        np.cumsum(self._witness_counts, dtype=np.uint64, out=offsets[1:])
        if int(offsets[-1]) != self._edge_count:
            raise TrainingDataInputError("NEIGHBOR1 streamed CSR edge count is inconsistent.")
        self._handle.flush()
        self._handle.seek(0)
        candidates = np.fromfile(self._handle, dtype="<u4", count=self._edge_count)
        self.close()
        if candidates.size != self._edge_count:
            raise TrainingDataInputError("NEIGHBOR1 streamed CSR edge payload is truncated.")
        return TargetCoverageExactNeighborhoodFamily(
            label_domain_id=self.prepared.label_domain_id,
            frame_domain_digest=self.prepared.frame_domain_digest,
            family_id=self.prepared.family.family_id,
            family_digest=self.prepared.family.content_digest,
            candidate_count=self.prepared.candidate_count,
            witness_count=len(self.prepared.scaled),
            witness_offsets=offsets,
            witness_candidates=candidates,
        )

    def close(self) -> None:
        if not self._closed:
            self._handle.close()
            self._closed = True

    def __del__(self) -> None:  # pragma: no cover - defensive cleanup
        try:
            self.close()
        except Exception:
            pass


class ExactNeighborhoodEngine:
    """Shared exact cKDTree neighborhood implementation for FEAS1 and MVIDX1."""

    def prepare_family(
        self,
        *,
        label_domain_id: str,
        frame_domain_digest: str,
        family: Any,
        candidate_count: int,
        query_block_size: int,
    ) -> ExactNeighborhoodPreparedFamily:
        values = np.asarray(family.values, dtype=np.float64)
        scales = np.asarray(family.scales, dtype=np.float64)
        frame_indices = np.asarray(family.frame_indices, dtype=np.int64)
        radii = np.asarray(family.local_radii, dtype=np.float64)
        if values.ndim != 2 or scales.shape != (values.shape[1],) or radii.shape != (len(values),):
            raise TrainingDataInputError(
                f"NEIGHBOR1 family {family.family_id!r} has inconsistent TARGET-DATA2B arrays."
            )
        candidate_count = int(candidate_count)
        if candidate_count < 1 or candidate_count > _UINT32_MAX or len(values) > _UINT32_MAX:
            raise TrainingDataInputError("NEIGHBOR1 family cardinality exceeds uint32 range.")
        if np.any(frame_indices < 0) or np.any(frame_indices >= candidate_count):
            raise TrainingDataInputError(
                f"NEIGHBOR1 family {family.family_id!r} has out-of-domain frame indices."
            )
        block_size = max(1, int(query_block_size))
        scaled = values / scales[None, :]
        blocks = tuple(
            (start, min(len(scaled), start + block_size))
            for start in range(0, len(scaled), block_size)
        )
        return ExactNeighborhoodPreparedFamily(
            label_domain_id=str(label_domain_id),
            frame_domain_digest=validate_digest(frame_domain_digest, name="frame_domain_digest"),
            family=family,
            candidate_count=candidate_count,
            values=values,
            scales=scales,
            frame_indices=frame_indices,
            radii=radii,
            scaled=scaled,
            tree=cKDTree(scaled),
            blocks=blocks,
        )

    def query_block(
        self,
        prepared: ExactNeighborhoodPreparedFamily,
        task: tuple[int, int],
        *,
        tree_workers: int,
        context: str | None = None,
    ) -> ExactNeighborhoodBlockResult:
        start, stop = (int(task[0]), int(task[1]))
        if start < 0 or stop <= start or stop > len(prepared.scaled):
            raise TrainingDataInputError("NEIGHBOR1 query block is outside the witness domain.")
        radius_scale = math.sqrt(float(prepared.scaled.shape[1]))
        raw = prepared.tree.query_ball_point(
            prepared.scaled[start:stop],
            r=(
                prepared.radii[start:stop]
                + EXACT_NEIGHBORHOOD_METRIC_TOLERANCE
                * np.maximum(1.0, prepared.radii[start:stop])
            )
            * radius_scale,
            workers=max(1, int(tree_workers)),
            return_sorted=True,
        )
        local_rows, candidates, unique_counts = compress_unique_candidate_block(
            raw,
            frame_indices=prepared.frame_indices,
            row_start=start,
            candidate_count=prepared.candidate_count,
            context=(
                context
                if context is not None
                else f"NEIGHBOR1 family {prepared.family.family_id!r}"
            ),
        )
        # The ragged cKDTree Python objects die here; only compact typed arrays
        # cross the worker boundary.
        return ExactNeighborhoodBlockResult(
            start=start,
            stop=stop,
            local_rows=local_rows,
            candidate_indices=candidates,
            unique_counts=unique_counts,
        )

    @staticmethod
    def open_stream(prepared: ExactNeighborhoodPreparedFamily) -> ExactNeighborhoodCSRStream:
        return ExactNeighborhoodCSRStream(prepared)


@dataclass(frozen=True, slots=True)
class ExactNeighborhoodBuildTelemetry:
    allocated_workers: int
    tree_workers_per_task: int
    max_busy_workers: int
    peak_accounted_memory_bytes: int
    memory_backpressure_events: int
    queue_backpressure_events: int
    family_count: int
    witness_count: int
    edge_count: int
    wall_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "allocated_workers": self.allocated_workers,
            "tree_workers_per_task": self.tree_workers_per_task,
            "max_busy_workers": self.max_busy_workers,
            "peak_accounted_memory_bytes": self.peak_accounted_memory_bytes,
            "memory_backpressure_events": self.memory_backpressure_events,
            "queue_backpressure_events": self.queue_backpressure_events,
            "family_count": self.family_count,
            "witness_count": self.witness_count,
            "edge_count": self.edge_count,
            "wall_seconds": self.wall_seconds,
        }


def _prepared_memory_estimate(family: Any, candidate_count: int) -> int:
    values = np.asarray(family.values)
    witness_count = int(len(family.values))
    feature_count = int(values.shape[1]) if values.ndim == 2 else 1
    scaled = witness_count * feature_count * 8
    tree = 2 * scaled + witness_count * 8
    fixed = witness_count * 8 + max(1, int(candidate_count)) * 0
    return max(1, int(scaled + tree + fixed))


def _block_memory_estimate(prepared: ExactNeighborhoodPreparedFamily, task: tuple[int, int]) -> int:
    rows = max(1, int(task[1]) - int(task[0]))
    features = max(1, int(prepared.scaled.shape[1]))
    return max(64 * 1024, rows * (features * 8 + 64))


def _csr_memory_estimate(family: TargetCoverageExactNeighborhoodFamily) -> int:
    return int(family.witness_offsets.nbytes + family.witness_candidates.nbytes)


def _default_scope(*, workers: int, tree_workers: int) -> StageResourceScope:
    visible = max(1, int(available_cpu_threads()))
    nested = max(1, int(workers) * max(1, int(tree_workers)))
    # The implicit direct-API scope preserves historical host-independent
    # behavior.  Campaign callers pass an explicit StageResourceScope when
    # RAM admission/backpressure is part of the execution contract; a direct
    # scientific call must not fail merely because an unrelated process makes
    # the instantaneous cgroup free-memory snapshot very small.
    return StageResourceScope(
        stage_name="TARGET-DATA2B-NEIGHBOR1",
        cpu_threads_available=max(visible, nested),
        cpu_threads_budget=nested,
        python_workers=max(1, int(workers)),
        tree_workers=max(1, int(tree_workers)),
        blas_threads=1,
        ram_budget_bytes=None,
    )


def build_target_coverage_exact_neighborhood_store(
    target_coverage_reference: Any,
    *,
    global_workers: int = 1,
    query_workers: int = 1,
    query_block_size: int = 512,
    progress_interval_seconds: float = 30.0,
    progress_callback: Callable[[str], None] | None = None,
    resource_scope: StageResourceScope | None = None,
    return_telemetry: bool = False,
) -> TargetCoverageExactNeighborhoodStore | tuple[TargetCoverageExactNeighborhoodStore, ExactNeighborhoodBuildTelemetry]:
    """Build every exact family neighborhood through one PARCORE1 work queue.

    ``global_workers``, ``query_workers``, ``query_block_size`` and progress
    settings are execution-only and are intentionally absent from cache identity.
    When more than one outer worker is active, each cKDTree call uses one native
    worker to preserve single-level parallelism.
    """

    workers = max(1, int(global_workers))
    native_workers = max(1, int(query_workers)) if workers == 1 else 1
    block_size = max(1, int(query_block_size))
    interval = max(0.05, float(progress_interval_seconds))
    explicit_scope = resource_scope is not None
    scope = _default_scope(workers=workers, tree_workers=native_workers) if resource_scope is None else resource_scope
    if int(scope.python_workers) != workers:
        raise TrainingDataInputError("NEIGHBOR1 resource scope python_workers does not match global_workers.")
    if int(scope.tree_workers) != native_workers:
        raise TrainingDataInputError("NEIGHBOR1 resource scope tree_workers does not match single-level tree width.")

    engine = ExactNeighborhoodEngine()
    manifest: list[tuple[int, Any, Any]] = []
    for domain_position, domain in enumerate(target_coverage_reference.domains):
        for family in sorted(domain.families, key=lambda item: item.family_id):
            manifest.append((domain_position, domain, family))
    if not manifest:
        raise TrainingDataInputError("NEIGHBOR1 target coverage reference contains no families.")

    total_witnesses = int(sum(len(family.values) for _, _, family in manifest))
    total_blocks = int(
        sum(math.ceil(len(family.values) / block_size) for _, _, family in manifest)
    )
    started = time.monotonic()
    if progress_callback is not None:
        progress_callback(
            f"status=start; progress={format_progress_fraction(0, total_witnesses)}; "
            f"elapsed=00:00:00; eta=--:--:--; families={len(manifest)}; blocks={total_blocks}; "
            f"global-workers={workers}; tree-workers/task={native_workers}; query-block={block_size}; backend=neighbor1-exact-engine"
        )

    max_pending = max(workers, 2 * workers)
    result_by_job: dict[int, TargetCoverageExactNeighborhoodFamily] = {}
    prepared_by_job: dict[int, ExactNeighborhoodPreparedFamily] = {}
    stream_by_job: dict[int, ExactNeighborhoodCSRStream] = {}
    reducer_by_job: dict[int, DeterministicOrderedReducer] = {}
    next_block_by_job: dict[int, int] = {}
    inflight_blocks_by_job: dict[int, int] = {}
    owners: dict[str, tuple[str, int, tuple[int, int] | None]] = {}
    reservation_by_job: dict[int, str] = {}
    output_reservations: list[str] = []
    next_prepare = 0
    preparing = 0
    rr_cursor = 0
    completed_blocks = 0
    completed_witnesses = 0
    last_progress = started
    final_snapshot: DeterministicWorkQueueSnapshot | None = None

    def prepare_job(job_index: int) -> ExactNeighborhoodPreparedFamily:
        _, domain, family = manifest[job_index]
        return engine.prepare_family(
            label_domain_id=domain.label_domain_id,
            frame_domain_digest=domain.frame_domain_digest,
            family=family,
            candidate_count=len(domain.frame_uids),
            query_block_size=block_size,
        )

    def query_job(prepared: ExactNeighborhoodPreparedFamily, task: tuple[int, int]) -> ExactNeighborhoodBlockResult:
        return engine.query_block(prepared, task, tree_workers=native_workers)

    with DeterministicWorkQueue(
        scope,
        max_ready_tasks=max_pending,
        max_inflight_tasks=max_pending,
        max_completed_tasks=max_pending,
        heartbeat_interval_seconds=interval,
        thread_name_prefix="mdstats-neighbor1",
        manage_resource_scope=explicit_scope,
    ) as queue:

        def buffered_count() -> int:
            return queue.outstanding_tasks + sum(item.buffered_count for item in reducer_by_job.values())

        def can_enqueue() -> bool:
            return queue.can_submit() and buffered_count() < max_pending + 2 * workers

        def submit_prepare(job_index: int) -> bool:
            nonlocal preparing
            if not can_enqueue():
                return False
            _, domain, family = manifest[job_index]
            task_id = f"prepare:{job_index:08d}"
            queue.submit(
                task_id=task_id,
                canonical_order=(job_index, 0, 0),
                function=prepare_job,
                args=(job_index,),
                task_kind="neighbor-family-prepare",
                estimated_memory_bytes=_prepared_memory_estimate(family, len(domain.frame_uids)),
                locality_key=f"{domain.label_domain_id}/{family.family_id}",
            )
            owners[task_id] = ("prepare", job_index, None)
            preparing += 1
            return True

        def submit_block(job_index: int) -> bool:
            prepared = prepared_by_job[job_index]
            position = next_block_by_job[job_index]
            if position >= len(prepared.blocks) or not can_enqueue():
                return False
            task = prepared.blocks[position]
            task_id = f"block:{job_index:08d}:{int(task[0]):012d}"
            queue.submit(
                task_id=task_id,
                canonical_order=(job_index, 1, int(task[0])),
                function=query_job,
                args=(prepared, task),
                task_kind="neighbor-witness-block",
                estimated_memory_bytes=_block_memory_estimate(prepared, task),
                locality_key=f"{prepared.label_domain_id}/{prepared.family.family_id}",
            )
            owners[task_id] = ("block", job_index, task)
            next_block_by_job[job_index] += 1
            inflight_blocks_by_job[job_index] += 1
            return True

        def refill() -> None:
            nonlocal next_prepare, rr_cursor
            if buffered_count() >= max_pending + 2 * workers:
                return
            if not prepared_by_job:
                prep_target = min(workers, len(manifest) - next_prepare + preparing)
            else:
                prep_target = min(max(1, workers // 8), len(manifest) - next_prepare + preparing)
            while next_prepare < len(manifest) and preparing < prep_target and can_enqueue():
                if not submit_prepare(next_prepare):
                    break
                next_prepare += 1
            active_ids = sorted(prepared_by_job)
            while active_ids and can_enqueue():
                scheduled = False
                count = len(active_ids)
                for offset in range(count):
                    pos = (rr_cursor + offset) % count
                    job_index = active_ids[pos]
                    if submit_block(job_index):
                        rr_cursor = (pos + 1) % count
                        scheduled = True
                        break
                if not scheduled:
                    break
                active_ids = sorted(prepared_by_job)
            while (
                next_prepare < len(manifest)
                and can_enqueue()
                and not any(next_block_by_job[j] < len(prepared_by_job[j].blocks) for j in prepared_by_job)
            ):
                if not submit_prepare(next_prepare):
                    break
                next_prepare += 1

        while next_prepare < len(manifest) and queue.outstanding_tasks < workers:
            if not submit_prepare(next_prepare):
                break
            next_prepare += 1

        while len(result_by_job) < len(manifest):
            refill()
            if not queue.has_outstanding_work:
                raise TrainingDataInputError("NEIGHBOR1 scheduler exhausted work before all families completed.")
            timeout = max(0.05, interval - (time.monotonic() - last_progress))
            if not queue.wait_for_completion(timeout=timeout):
                final_snapshot = queue.snapshot()
                if progress_callback is not None:
                    elapsed = max(0.0, time.monotonic() - started)
                    rate = completed_witnesses / elapsed if elapsed > 0.0 else 0.0
                    remaining = max(0, total_witnesses - completed_witnesses)
                    eta = remaining / rate if rate > 0.0 else None
                    progress_callback(
                        f"status=heartbeat; progress={format_progress_fraction(completed_witnesses, total_witnesses)}; "
                        f"elapsed={format_progress_time(elapsed)}; eta={format_progress_time(eta)}; "
                        f"rate={rate:.1f} witness/s; families={len(result_by_job)}/{len(manifest)}; "
                        f"blocks={completed_blocks}/{total_blocks}; workers-busy={final_snapshot.busy_workers}/{final_snapshot.allocated_workers}; "
                        f"pending={final_snapshot.inflight_tasks}; buffered={final_snapshot.completed_tasks}; "
                        f"memory-admitted={final_snapshot.accounted_memory_bytes}/{final_snapshot.memory_budget_bytes}; "
                        f"backpressure={final_snapshot.memory_backpressure_events + final_snapshot.queue_backpressure_events}"
                    )
                last_progress = time.monotonic()
                continue
            completions = queue.drain_completed(dispatch=False)
            for completion in completions:
                kind, job_index, task = owners.pop(completion.task_id)
                if kind == "prepare":
                    preparing -= 1
                    prepared = completion.value
                    prepared_by_job[job_index] = prepared
                    stream_by_job[job_index] = engine.open_stream(prepared)
                    next_block_by_job[job_index] = 0
                    inflight_blocks_by_job[job_index] = 0

                    def commit_block(_key: Any, block_result: ExactNeighborhoodBlockResult, job_index: int = job_index) -> None:
                        stream_by_job[job_index].append(block_result)

                    reducer_by_job[job_index] = DeterministicOrderedReducer(
                        tuple(int(start) for start, _ in prepared.blocks), commit=commit_block
                    )
                    reservation_id = f"neighbor-profile:{job_index:08d}"
                    _, domain, family = manifest[job_index]
                    queue.reserve_memory(
                        reservation_id,
                        _prepared_memory_estimate(family, len(domain.frame_uids)),
                    )
                    reservation_by_job[job_index] = reservation_id
                    queue.dispatch_ready()
                    continue

                inflight_blocks_by_job[job_index] -= 1
                block_result = completion.value
                reducer = reducer_by_job[job_index]
                reducer.push(int(block_result.start), block_result)
                completed_blocks += 1
                completed_witnesses += int(block_result.stop - block_result.start)
                queue.dispatch_ready()
                now = time.monotonic()
                milestone = (
                    completed_blocks == total_blocks
                    or completed_blocks == 1
                    or completed_blocks * 20 // max(1, total_blocks)
                    > (completed_blocks - 1) * 20 // max(1, total_blocks)
                )
                if progress_callback is not None and (milestone or now - last_progress >= interval):
                    final_snapshot = queue.snapshot()
                    elapsed = max(1.0e-12, now - started)
                    rate = completed_witnesses / elapsed
                    remaining = max(0, total_witnesses - completed_witnesses)
                    eta = remaining / rate if rate > 0.0 else None
                    progress_callback(
                        f"status=progress; progress={format_progress_fraction(completed_witnesses, total_witnesses)}; "
                        f"elapsed={format_progress_time(elapsed)}; eta={format_progress_time(eta)}; "
                        f"rate={rate:.1f} witness/s; families={len(result_by_job)}/{len(manifest)}; "
                        f"blocks={completed_blocks}/{total_blocks}; workers-busy={final_snapshot.busy_workers}/{final_snapshot.allocated_workers}; "
                        f"edges={sum(stream.edge_count for stream in stream_by_job.values())}"
                    )
                    last_progress = now

                prepared = prepared_by_job[job_index]
                if (
                    reducer.complete
                    and next_block_by_job[job_index] == len(prepared.blocks)
                    and inflight_blocks_by_job[job_index] == 0
                ):
                    stream = stream_by_job.pop(job_index)
                    output_id = f"neighbor-output:{job_index:08d}"
                    # Admit the exact final CSR allocation before materializing
                    # it from the disk-backed edge stream.  This keeps the
                    # StageResourceScope RAM budget fail-closed.
                    queue.reserve_memory(output_id, stream.final_array_memory_bytes)
                    output_reservations.append(output_id)
                    family_result = stream.finalize()
                    if _csr_memory_estimate(family_result) != stream.final_array_memory_bytes:
                        raise TrainingDataInputError("NEIGHBOR1 final CSR memory accounting changed during materialization.")
                    result_by_job[job_index] = family_result
                    queue.release_memory(reservation_by_job.pop(job_index))
                    del reducer_by_job[job_index]
                    del prepared_by_job[job_index]
                    del next_block_by_job[job_index]
                    del inflight_blocks_by_job[job_index]
            refill()

        final_snapshot = queue.snapshot()
        for reservation_id in output_reservations:
            queue.release_memory(reservation_id)

    domains: list[TargetCoverageExactNeighborhoodDomain] = []
    by_domain: dict[int, list[TargetCoverageExactNeighborhoodFamily]] = {}
    for job_index, (domain_position, _, _) in enumerate(manifest):
        by_domain.setdefault(domain_position, []).append(result_by_job[job_index])
    for domain_position, domain in enumerate(target_coverage_reference.domains):
        families = tuple(sorted(by_domain[domain_position], key=lambda item: item.family_id))
        domains.append(
            TargetCoverageExactNeighborhoodDomain(
                label_domain_id=domain.label_domain_id,
                frame_domain_digest=domain.frame_domain_digest,
                candidate_count=len(domain.frame_uids),
                families=families,
            )
        )
    store = TargetCoverageExactNeighborhoodStore(
        dataset_id=target_coverage_reference.dataset_id,
        target_coverage_reference_digest=target_coverage_reference.content_digest,
        domains=tuple(domains),
    )
    if final_snapshot is None:
        raise TrainingDataInputError("NEIGHBOR1 did not produce final scheduler telemetry.")
    telemetry = ExactNeighborhoodBuildTelemetry(
        allocated_workers=final_snapshot.allocated_workers,
        tree_workers_per_task=native_workers,
        max_busy_workers=final_snapshot.max_busy_workers,
        peak_accounted_memory_bytes=final_snapshot.peak_accounted_memory_bytes,
        memory_backpressure_events=final_snapshot.memory_backpressure_events,
        queue_backpressure_events=final_snapshot.queue_backpressure_events,
        family_count=len(manifest),
        witness_count=total_witnesses,
        edge_count=store.edge_count,
        wall_seconds=time.monotonic() - started,
    )
    if progress_callback is not None:
        progress_callback(
            f"status=complete; progress={format_progress_fraction(total_witnesses, total_witnesses)}; "
            f"elapsed={format_progress_time(telemetry.wall_seconds)}; eta=00:00:00; "
            f"families={len(manifest)}; edges={store.edge_count}; digest={store.content_digest[:12]}..."
        )
    return (store, telemetry) if return_telemetry else store


def validate_target_coverage_exact_neighborhood_store(
    store: TargetCoverageExactNeighborhoodStore,
    *,
    target_coverage_reference: Any,
    verify_geometry: bool = False,
    query_workers: int = 1,
    query_block_size: int = 512,
) -> None:
    """Authenticate cache lineage and optionally rebuild exact geometry."""

    if store.dataset_id != target_coverage_reference.dataset_id:
        raise TrainingDataInputError("NEIGHBOR1 dataset identity mismatch.")
    if store.target_coverage_reference_digest != target_coverage_reference.content_digest:
        raise TrainingDataInputError("NEIGHBOR1 TARGET-DATA2B reference digest mismatch.")
    expected_domains = tuple(sorted(item.label_domain_id for item in target_coverage_reference.domains))
    if tuple(item.label_domain_id for item in store.domains) != expected_domains:
        raise TrainingDataInputError("NEIGHBOR1 cache domain identities changed.")
    engine = ExactNeighborhoodEngine()
    for cached_domain in store.domains:
        reference_domain = target_coverage_reference.domain(cached_domain.label_domain_id)
        if (
            cached_domain.frame_domain_digest != reference_domain.frame_domain_digest
            or cached_domain.candidate_count != len(reference_domain.frame_uids)
        ):
            raise TrainingDataInputError("NEIGHBOR1 cache candidate-domain identity changed.")
        expected_families = tuple(sorted(reference_domain.families, key=lambda item: item.family_id))
        if tuple(item.family_id for item in cached_domain.families) != tuple(item.family_id for item in expected_families):
            raise TrainingDataInputError("NEIGHBOR1 cache family identities changed.")
        for cached, family in zip(cached_domain.families, expected_families, strict=True):
            if cached.family_digest != family.content_digest or cached.witness_count != len(family.values):
                raise TrainingDataInputError(f"NEIGHBOR1 family identity mismatch for {family.family_id!r}.")
            if verify_geometry:
                prepared = engine.prepare_family(
                    label_domain_id=reference_domain.label_domain_id,
                    frame_domain_digest=reference_domain.frame_domain_digest,
                    family=family,
                    candidate_count=len(reference_domain.frame_uids),
                    query_block_size=max(1, int(query_block_size)),
                )
                stream = engine.open_stream(prepared)
                try:
                    for task in prepared.blocks:
                        stream.append(
                            engine.query_block(
                                prepared,
                                task,
                                tree_workers=max(1, int(query_workers)),
                            )
                        )
                    rebuilt = stream.finalize()
                finally:
                    stream.close()
                if rebuilt.content_digest != cached.content_digest:
                    raise TrainingDataInputError(
                        f"NEIGHBOR1 exact geometry mismatch for {family.family_id!r}."
                    )


__all__ = [
    "TARGET_COVERAGE_EXACT_NEIGHBORHOOD_FAMILY_SCHEMA",
    "TARGET_COVERAGE_EXACT_NEIGHBORHOOD_DOMAIN_SCHEMA",
    "TARGET_COVERAGE_EXACT_NEIGHBORHOOD_STORE_SCHEMA",
    "TARGET_COVERAGE_EXACT_NEIGHBORHOOD_VERSION",
    "TARGET_COVERAGE_EXACT_NEIGHBORHOOD_PERSISTENCE_VERSION",
    "EXACT_NEIGHBORHOOD_METRIC_TOLERANCE",
    "EXACT_NEIGHBORHOOD_DISTANCE_SEMANTICS",
    "TargetCoverageExactNeighborhoodFamily",
    "TargetCoverageExactNeighborhoodDomain",
    "TargetCoverageExactNeighborhoodStore",
    "ExactNeighborhoodPreparedFamily",
    "ExactNeighborhoodBlockResult",
    "ExactNeighborhoodCSRStream",
    "ExactNeighborhoodEngine",
    "ExactNeighborhoodBuildTelemetry",
    "build_target_coverage_exact_neighborhood_store",
    "validate_target_coverage_exact_neighborhood_store",
]
