"""MVIDX1: exact sparse representation of NEIGHBOR1 plus canonical obligations.

Restored from TARGET-DATA2C-MVIDX1 (carrier ``3937881e`` blobs ``b9567fa5``,
the packed native-persistence v2 store and the forward-only view) and rebound
to one exact ``P_train`` domain.  MVIDX is representation, not a semantic
owner: family witness->candidate rows are adopted byte-for-byte from the
authenticated shared NEIGHBOR1 product (never re-queried), the candidate->
witness inverse is a deterministic counting transpose, and obligation
incidence is copied from the canonical obligation authority.

Large inverse payloads are built out-of-core with bounded chunk scratch.
Persistence packs every family array into four shared roots, and the
forward-only restore used by MVSEL2/REPAIR2 maps only the two candidate-
oriented roots, so mapped descriptors stay O(1) in family count.  An artifact
without the packed layout is rejected as obsolete reconstructible cache.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
import shutil
import time
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from scipy.sparse import csr_matrix

from .._common import TrainingDataInputError, digest, validate_digest
from ..resources import StageResourceScope, available_cpu_threads
from ..work_queue import DeterministicWorkQueue
from ._sparse_vector_kernels import csr_gather_rows
from .artifact_store import (
    PublishedArtifact,
    TargetOrderArtifactStoreError,
    array_reference,
    close_memmap,
    packed_slice,
    publish_artifact_directory,
    read_manifest,
    read_npy,
    read_packed,
    write_npy,
    write_packed,
)

MVIDX_POLICY_SCHEMA = "mdstats.target-coverage-sparse-index-policy.v2"
MVIDX_SCHEMA = "mdstats.target-coverage-sparse-index.v2"
MVIDX_ARTIFACT_SCHEMA = "mdstats.target-coverage-sparse-index-artifact.v3"
MVIDX_VERSION = "mdstats.target-order.mvidx1.sparse-index.v1"

_INT32_MAX = int(np.iinfo(np.int32).max)
_MIB = 1024 ** 2
_OOC_MIN_OUTPUT_BYTES = 8 * _MIB
_OOC_TASK_ADMISSION_BYTES = 768 * _MIB
_OOC_CHUNK_SCRATCH_BYTES = 384 * _MIB


def _readonly(values: Any, *, dtype: str, name: str) -> np.ndarray:
    array = np.ascontiguousarray(np.asarray(values, dtype=np.dtype(dtype).newbyteorder("<")))
    if array.ndim != 1:
        raise TrainingDataInputError(f"MVIDX {name} must be one-dimensional.")
    array.setflags(write=False)
    return array


def _check_offsets(offsets: np.ndarray, *, items: int, edges: int, name: str) -> None:
    if offsets.shape != (items + 1,) or int(offsets[0]) != 0 or int(offsets[-1]) != edges:
        raise TrainingDataInputError(f"MVIDX {name} offsets do not span their edges.")
    if np.any(offsets[1:] < offsets[:-1]):
        raise TrainingDataInputError(f"MVIDX {name} offsets are not monotone.")


@dataclass(frozen=True, slots=True)
class SparseObligation:
    """Representation of one canonical obligation (ID and effective minimum)."""

    obligation_id: str
    minimum_selected_frames: int

    def to_dict(self) -> dict[str, Any]:
        return {"obligation_id": self.obligation_id, "minimum_selected_frames": int(self.minimum_selected_frames)}


@dataclass(frozen=True, slots=True, eq=False)
class TargetCoverageSparseFamilyIndex:
    family_id: str
    family_digest: str
    candidate_count: int
    witness_count: int
    witness_offsets: np.ndarray | Sequence[int]
    witness_candidates: np.ndarray | Sequence[int]
    candidate_offsets: np.ndarray | Sequence[int]
    candidate_witnesses: np.ndarray | Sequence[int]
    array_references: Mapping[str, Mapping[str, Any]] | None = field(default=None, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "family_digest", validate_digest(self.family_digest, name="family_digest"))
        for name, dtype in (
            ("witness_offsets", "<u8"),
            ("witness_candidates", "<u4"),
            ("candidate_offsets", "<u8"),
            ("candidate_witnesses", "<u4"),
        ):
            object.__setattr__(self, name, _readonly(getattr(self, name), dtype=dtype, name=name))
        edges = len(self.witness_candidates)
        if len(self.candidate_witnesses) != edges:
            raise TrainingDataInputError("MVIDX forward/inverse edge counts disagree.")
        _check_offsets(self.witness_offsets, items=int(self.witness_count), edges=edges, name="witness")
        _check_offsets(self.candidate_offsets, items=int(self.candidate_count), edges=edges, name="candidate")

    @property
    def edge_count(self) -> int:
        return len(self.witness_candidates)

    def _reference(self, name: str) -> dict[str, Any]:
        supplied = None if self.array_references is None else self.array_references.get(name)
        return dict(supplied) if supplied is not None else array_reference(getattr(self, name))

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(
                {
                    "schema": "mdstats.target-coverage-sparse-family-index.v2",
                    "family_id": self.family_id,
                    "family_digest": self.family_digest,
                    "candidate_count": int(self.candidate_count),
                    "witness_count": int(self.witness_count),
                    "edge_count": self.edge_count,
                    "array_references": {
                        name: self._reference(name)
                        for name in ("candidate_offsets", "candidate_witnesses", "witness_candidates", "witness_offsets")
                    },
                }
            )
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def witness_candidate_indices(self, witness_index: int) -> np.ndarray:
        row = int(witness_index)
        return self.witness_candidates[int(self.witness_offsets[row]):int(self.witness_offsets[row + 1])]

    def candidate_witness_indices(self, candidate_index: int) -> np.ndarray:
        row = int(candidate_index)
        if row < 0 or row >= int(self.candidate_count):
            raise IndexError(row)
        return self.candidate_witnesses[int(self.candidate_offsets[row]):int(self.candidate_offsets[row + 1])]


@dataclass(frozen=True, slots=True, eq=False)
class TargetCoverageSparseIndex:
    """The single-domain MVIDX1 product."""

    dataset_id: str
    target_coverage_reference_digest: str
    neighborhood_digest: str
    obligation_authority_digest: str
    frame_domain_digest: str
    candidate_count: int
    families: tuple[TargetCoverageSparseFamilyIndex, ...]
    obligations: tuple[SparseObligation, ...]
    obligation_offsets: np.ndarray | Sequence[int]
    obligation_candidates: np.ndarray | Sequence[int]
    candidate_obligation_offsets: np.ndarray | Sequence[int]
    candidate_obligations: np.ndarray | Sequence[int]
    correlation_unit_ids: tuple[str, ...]
    candidate_correlation_unit_codes: np.ndarray | Sequence[int]
    _family_by_id: Mapping[str, TargetCoverageSparseFamilyIndex] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in (
            "target_coverage_reference_digest",
            "neighborhood_digest",
            "obligation_authority_digest",
            "frame_domain_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        families = tuple(self.families)
        if not families or tuple(item.family_id for item in families) != tuple(sorted(item.family_id for item in families)):
            raise TrainingDataInputError("MVIDX families must be non-empty and canonically ordered.")
        obligations = tuple(self.obligations)
        if not obligations or tuple(item.obligation_id for item in obligations) != tuple(
            sorted(item.obligation_id for item in obligations)
        ):
            raise TrainingDataInputError("MVIDX obligations must be non-empty and canonically ordered.")
        for name, dtype in (
            ("obligation_offsets", "<u8"),
            ("obligation_candidates", "<u4"),
            ("candidate_obligation_offsets", "<u8"),
            ("candidate_obligations", "<u4"),
            ("candidate_correlation_unit_codes", "<u4"),
        ):
            object.__setattr__(self, name, _readonly(getattr(self, name), dtype=dtype, name=name))
        edges = len(self.obligation_candidates)
        _check_offsets(self.obligation_offsets, items=len(obligations), edges=edges, name="obligation")
        _check_offsets(self.candidate_obligation_offsets, items=int(self.candidate_count), edges=edges, name="candidate-obligation")
        units = tuple(validate_digest(value, name="correlation_unit_id") for value in self.correlation_unit_ids)
        if not units or units != tuple(sorted(set(units))):
            raise TrainingDataInputError("MVIDX correlation-unit IDs must be sorted unique digests.")
        codes = self.candidate_correlation_unit_codes
        if codes.shape != (int(self.candidate_count),) or int(np.max(codes)) >= len(units):
            raise TrainingDataInputError("MVIDX candidate correlation-unit codes are invalid.")
        if any(int(item.candidate_count) != int(self.candidate_count) for item in families):
            raise TrainingDataInputError("MVIDX family candidate domains disagree.")
        object.__setattr__(self, "candidate_count", int(self.candidate_count))
        object.__setattr__(self, "families", families)
        object.__setattr__(self, "obligations", obligations)
        object.__setattr__(self, "correlation_unit_ids", units)
        object.__setattr__(self, "_family_by_id", {item.family_id: item for item in families})

    def family(self, family_id: str) -> TargetCoverageSparseFamilyIndex:
        return self._family_by_id[family_id]

    def candidate_obligation_indices(self, candidate_index: int) -> np.ndarray:
        row = int(candidate_index)
        return self.candidate_obligations[
            int(self.candidate_obligation_offsets[row]):int(self.candidate_obligation_offsets[row + 1])
        ]

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(
                {
                    "schema": MVIDX_SCHEMA,
                    "authority_version": MVIDX_VERSION,
                    "dataset_id": self.dataset_id,
                    "target_coverage_reference_digest": self.target_coverage_reference_digest,
                    "neighborhood_digest": self.neighborhood_digest,
                    "obligation_authority_digest": self.obligation_authority_digest,
                    "frame_domain_digest": self.frame_domain_digest,
                    "candidate_count": self.candidate_count,
                    "family_digests": [item.content_digest for item in self.families],
                    "obligations": [item.to_dict() for item in self.obligations],
                    "correlation_unit_ids": list(self.correlation_unit_ids),
                    "array_references": {
                        name: array_reference(getattr(self, name))
                        for name in (
                            "candidate_correlation_unit_codes",
                            "candidate_obligation_offsets",
                            "candidate_obligations",
                            "obligation_candidates",
                            "obligation_offsets",
                        )
                    },
                }
            )
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached


@dataclass(frozen=True, slots=True)
class TargetCoverageSparseForwardFamilyView:
    family_id: str
    family_digest: str
    mvidx_family_digest: str
    candidate_count: int
    witness_count: int
    candidate_offsets: np.ndarray
    candidate_witnesses: np.ndarray

    @property
    def edge_count(self) -> int:
        return len(self.candidate_witnesses)

    def candidate_witness_indices(self, candidate_index: int) -> np.ndarray:
        row = int(candidate_index)
        if row < 0 or row >= self.candidate_count:
            raise IndexError(row)
        return self.candidate_witnesses[int(self.candidate_offsets[row]):int(self.candidate_offsets[row + 1])]


@dataclass(frozen=True, slots=True)
class TargetCoverageSparseForwardView:
    """Candidate-oriented projection used by MVSEL2/REPAIR2 (no inverse roots)."""

    dataset_id: str
    mvidx_content_digest: str
    frame_domain_digest: str
    candidate_count: int
    families: tuple[TargetCoverageSparseForwardFamilyView, ...]
    obligations: tuple[SparseObligation, ...]
    candidate_obligation_offsets: np.ndarray
    candidate_obligations: np.ndarray
    correlation_unit_ids: tuple[str, ...]
    candidate_correlation_unit_codes: np.ndarray
    _family_by_id: Mapping[str, TargetCoverageSparseForwardFamilyView] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "_family_by_id", {item.family_id: item for item in self.families})

    def family(self, family_id: str) -> TargetCoverageSparseForwardFamilyView:
        return self._family_by_id[family_id]

    def candidate_obligation_indices(self, candidate_index: int) -> np.ndarray:
        row = int(candidate_index)
        if row < 0 or row >= self.candidate_count:
            raise IndexError(row)
        return self.candidate_obligations[
            int(self.candidate_obligation_offsets[row]):int(self.candidate_obligation_offsets[row + 1])
        ]


def sparse_forward_view(index: TargetCoverageSparseIndex) -> TargetCoverageSparseForwardView:
    return TargetCoverageSparseForwardView(
        dataset_id=index.dataset_id,
        mvidx_content_digest=index.content_digest,
        frame_domain_digest=index.frame_domain_digest,
        candidate_count=index.candidate_count,
        families=tuple(
            TargetCoverageSparseForwardFamilyView(
                family_id=item.family_id,
                family_digest=item.family_digest,
                mvidx_family_digest=item.content_digest,
                candidate_count=item.candidate_count,
                witness_count=item.witness_count,
                candidate_offsets=item.candidate_offsets,
                candidate_witnesses=item.candidate_witnesses,
            )
            for item in index.families
        ),
        obligations=index.obligations,
        candidate_obligation_offsets=index.candidate_obligation_offsets,
        candidate_obligations=index.candidate_obligations,
        correlation_unit_ids=index.correlation_unit_ids,
        candidate_correlation_unit_codes=index.candidate_correlation_unit_codes,
    )


def csr_inverse(row_offsets: np.ndarray, row_columns: np.ndarray, *, row_count: int, column_count: int) -> tuple[np.ndarray, np.ndarray]:
    """Exact column->row CSR from row->column CSR (deterministic counting transpose)."""

    if column_count > _INT32_MAX or row_count > _INT32_MAX:
        raise TrainingDataInputError("MVIDX sparse transpose requires cardinalities below int32 range.")
    matrix = csr_matrix(
        (np.ones(len(row_columns), dtype=np.uint8), np.asarray(row_columns).view(np.int32), np.asarray(row_offsets, dtype=np.int64)),
        shape=(int(row_count), int(column_count)),
    )
    inverse = matrix.tocsc(copy=True)
    inverse.sort_indices()
    return np.asarray(inverse.indptr, dtype="<u8"), np.asarray(inverse.indices, dtype="<u4")


def _csr_inverse_out_of_core(
    row_offsets: np.ndarray,
    row_columns: np.ndarray,
    *,
    row_count: int,
    column_count: int,
    output_path: Path,
    chunk_scratch_bytes: int,
) -> tuple[np.ndarray, np.ndarray]:
    """File-backed inverse with bounded chunk scratch, byte-identical to :func:`csr_inverse`."""

    edge_count = int(len(row_columns))
    counts = np.zeros(int(column_count), dtype=np.uint64)
    chunk_edges = max(1, int(chunk_scratch_bytes) // 16)
    for start in range(0, edge_count, chunk_edges):
        counts += np.bincount(row_columns[start:start + chunk_edges], minlength=int(column_count)).astype(np.uint64)
    offsets = np.empty(int(column_count) + 1, dtype="<u8")
    offsets[0] = 0
    np.cumsum(counts, dtype=np.uint64, out=offsets[1:])
    rows = np.lib.format.open_memmap(output_path, mode="w+", dtype="<u4", shape=(edge_count,))
    written = np.zeros(int(column_count), dtype=np.uint64)
    row_start = 0
    try:
        while row_start < int(row_count):
            target = int(row_offsets[row_start]) + chunk_edges
            row_stop = max(row_start + 1, min(int(row_count), int(np.searchsorted(row_offsets, target, side="right") - 1)))
            edge_start, edge_stop = int(row_offsets[row_start]), int(row_offsets[row_stop])
            if edge_stop > edge_start:
                local = csr_matrix(
                    (
                        np.ones(edge_stop - edge_start, dtype=np.uint8),
                        np.asarray(row_columns[edge_start:edge_stop]).view(np.int32),
                        np.asarray(row_offsets[row_start:row_stop + 1], dtype=np.int64) - edge_start,
                    ),
                    shape=(row_stop - row_start, int(column_count)),
                ).tocsc(copy=True)
                local.sort_indices()
                local_counts = np.diff(local.indptr).astype(np.uint64)
                for column in np.flatnonzero(local_counts):
                    column = int(column)
                    source = slice(int(local.indptr[column]), int(local.indptr[column + 1]))
                    destination = int(offsets[column] + written[column])
                    np.add(
                        local.indices[source],
                        np.uint32(row_start),
                        out=rows[destination:destination + (source.stop - source.start)],
                        casting="unsafe",
                    )
                written += local_counts
                rows.flush()
            row_start = row_stop
        if not np.array_equal(written, counts):
            raise TrainingDataInputError("MVIDX out-of-core transpose fill mismatch.")
        rows.flush()
    except BaseException:
        close_memmap(rows)
        del rows
        output_path.unlink(missing_ok=True)
        raise
    close_memmap(rows)
    del rows
    offsets.setflags(write=False)
    return offsets, np.load(output_path, mmap_mode="r", allow_pickle=False)


def _obligation_incidence(authority: Any) -> tuple[tuple[SparseObligation, ...], np.ndarray, np.ndarray]:
    obligations = tuple(
        SparseObligation(item.obligation_id, item.minimum_count) for item in authority.obligations
    )
    counts = np.asarray([item.candidate_indices.size for item in authority.obligations], dtype=np.uint64)
    offsets = np.empty(len(obligations) + 1, dtype="<u8")
    offsets[0] = 0
    np.cumsum(counts, dtype=np.uint64, out=offsets[1:])
    candidates = np.concatenate([np.asarray(item.candidate_indices, dtype="<u4") for item in authority.obligations])
    return obligations, offsets, candidates


def build_target_coverage_sparse_index(
    reference: Any,
    neighborhoods: Any,
    authority: Any,
    *,
    workers: int = 1,
    resource_scope: StageResourceScope | None = None,
    out_of_core_directory: Path | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> TargetCoverageSparseIndex:
    """Adopt NEIGHBOR1 and canonical obligations into exact sparse incidence."""

    if neighborhoods.target_coverage_reference_digest != reference.content_digest:
        raise TrainingDataInputError("MVIDX NEIGHBOR1/reference lineage mismatch.")
    if authority.target_coverage_reference_digest != reference.content_digest:
        raise TrainingDataInputError("MVIDX obligation/reference lineage mismatch.")
    for cached, family in zip(neighborhoods.families, reference.families, strict=True):
        if cached.family_id != family.family_id or cached.family_digest != family.content_digest:
            raise TrainingDataInputError("MVIDX NEIGHBOR1 family identity mismatch.")
    candidate_count = reference.candidate_count
    ooc_root = None if out_of_core_directory is None else Path(out_of_core_directory)
    if ooc_root is not None:
        ooc_root.mkdir(parents=True, exist_ok=True)
        required = sum(item.edge_count for item in neighborhoods.families) * 4
        safety = max(1 * 1024**3, int(math.ceil(required * 0.05)))
        free = int(shutil.disk_usage(ooc_root).free)
        if free < required + safety:
            raise TrainingDataInputError(
                f"MVIDX out-of-core inverse requires approximately {required / 1024**3:.1f} GiB plus "
                f"{safety / 1024**3:.1f} GiB safety headroom, but only {free / 1024**3:.1f} GiB is free under {ooc_root}."
            )
    width = max(1, min(int(workers), len(neighborhoods.families)))
    admission = _OOC_TASK_ADMISSION_BYTES
    if resource_scope is not None and resource_scope.ram_budget_bytes is not None:
        admission = min(admission, max(1, int(resource_scope.ram_budget_bytes) // width))
    chunk_scratch = max(8 * _MIB, min(_OOC_CHUNK_SCRATCH_BYTES, max(1, admission // 2)))

    def invert(position: int) -> TargetCoverageSparseFamilyIndex:
        cached = neighborhoods.families[position]
        use_ooc = ooc_root is not None and cached.edge_count * 4 >= _OOC_MIN_OUTPUT_BYTES
        if use_ooc:
            offsets, witnesses = _csr_inverse_out_of_core(
                cached.witness_offsets,
                cached.witness_candidates,
                row_count=cached.witness_count,
                column_count=candidate_count,
                output_path=ooc_root / f"mvidx-family-{position:05d}-{cached.family_digest[:16]}-inverse.npy",
                chunk_scratch_bytes=chunk_scratch,
            )
        else:
            offsets, witnesses = csr_inverse(
                cached.witness_offsets, cached.witness_candidates, row_count=cached.witness_count, column_count=candidate_count
            )
        return TargetCoverageSparseFamilyIndex(
            family_id=cached.family_id,
            family_digest=cached.family_digest,
            candidate_count=candidate_count,
            witness_count=cached.witness_count,
            witness_offsets=cached.witness_offsets,
            witness_candidates=cached.witness_candidates,
            candidate_offsets=offsets,
            candidate_witnesses=witnesses,
        )

    started = time.monotonic()
    indices: list[TargetCoverageSparseFamilyIndex | None] = [None] * len(neighborhoods.families)
    if width == 1:
        for position in range(len(indices)):
            indices[position] = invert(position)
    else:
        scope = resource_scope
        if scope is None or int(scope.python_workers) != width:
            base = resource_scope
            scope = StageResourceScope(
                stage_name="TARGET-ORDER-MVIDX",
                cpu_threads_available=int(available_cpu_threads() if base is None else base.cpu_threads_available),
                cpu_threads_budget=int(width if base is None else base.cpu_threads_budget),
                python_workers=width,
                tree_workers=1,
                blas_threads=1,
                ram_budget_bytes=None if base is None else base.ram_budget_bytes,
            )
        with DeterministicWorkQueue(
            scope,
            max_ready_tasks=max(1, 2 * width),
            max_inflight_tasks=max(1, 2 * width),
            max_completed_tasks=max(1, 2 * width),
            thread_name_prefix="mdstats-mvidx",
            manage_resource_scope=resource_scope is None,
        ) as queue:
            next_submit = 0
            done = 0
            while done < len(indices):
                while next_submit < len(indices) and queue.can_submit():
                    cached = neighborhoods.families[next_submit]
                    use_ooc = ooc_root is not None and cached.edge_count * 4 >= _OOC_MIN_OUTPUT_BYTES
                    queue.submit(
                        task_id=f"mvidx-family-{next_submit:06d}",
                        canonical_order=(next_submit,),
                        function=invert,
                        args=(next_submit,),
                        task_kind="mvidx-family-inverse-ooc" if use_ooc else "mvidx-family-inverse",
                        estimated_memory_bytes=(
                            admission + (candidate_count + 1) * 32 if use_ooc else cached.edge_count * 18 + (candidate_count + 1) * 16
                        ),
                    )
                    next_submit += 1
                queue.wait_for_completion()
                for completion in queue.drain_completed():
                    indices[int(completion.canonical_order[0])] = completion.value
                    done += 1
    obligations, obligation_offsets, obligation_candidates = _obligation_incidence(authority)
    candidate_obligation_offsets, candidate_obligations = csr_inverse(
        obligation_offsets, obligation_candidates, row_count=len(obligations), column_count=candidate_count
    )
    unit_ids = tuple(sorted(set(reference.correlation_unit_ids)))
    code_by_unit = {unit: code for code, unit in enumerate(unit_ids)}
    codes = np.asarray([code_by_unit[unit] for unit in reference.correlation_unit_ids], dtype="<u4")
    index = TargetCoverageSparseIndex(
        dataset_id=reference.dataset_id,
        target_coverage_reference_digest=reference.content_digest,
        neighborhood_digest=neighborhoods.content_digest,
        obligation_authority_digest=authority.content_digest,
        frame_domain_digest=reference.frame_domain_digest,
        candidate_count=candidate_count,
        families=tuple(item for item in indices if item is not None),
        obligations=obligations,
        obligation_offsets=obligation_offsets,
        obligation_candidates=obligation_candidates,
        candidate_obligation_offsets=candidate_obligation_offsets,
        candidate_obligations=candidate_obligations,
        correlation_unit_ids=unit_ids,
        candidate_correlation_unit_codes=codes,
    )
    if progress_callback is not None:
        progress_callback(
            f"status=complete; families={len(index.families)}; edges={sum(item.edge_count for item in index.families)}; "
            f"obligations={len(obligations)}; workers={width}; geometry=adopted; elapsed={time.monotonic() - started:.1f}s"
        )
    return index


def indexed_family_covered_mass(family: Any, weights: Any, selected_candidate_indices: Sequence[int]) -> float:
    """MVIDX cross-check mass (secondary evidence only)."""

    selected = np.asarray(tuple(int(v) for v in selected_candidate_indices), dtype=np.int64)
    covered = np.zeros(int(family.witness_count), dtype=np.bool_)
    if selected.size:
        witnesses, _ = csr_gather_rows(family.candidate_offsets, family.candidate_witnesses, selected)
        covered[np.asarray(witnesses, dtype=np.int64)] = True
    return float(np.sum(np.asarray(weights, dtype=np.float64)[covered], dtype=np.float64))


_FAMILY_ROOTS = (
    ("witness_offsets", "<u8"),
    ("witness_candidates", "<u4"),
    ("candidate_offsets", "<u8"),
    ("candidate_witnesses", "<u4"),
)
_DOMAIN_ARRAYS = (
    "obligation_offsets",
    "obligation_candidates",
    "candidate_obligation_offsets",
    "candidate_obligations",
    "candidate_correlation_unit_codes",
)


def write_target_coverage_sparse_index(destination: Path, index: TargetCoverageSparseIndex) -> PublishedArtifact:
    def write(directory: Path) -> Mapping[str, Any]:
        packed: dict[str, Any] = {}
        slices: dict[str, list[dict[str, Any]]] = {}
        for name, dtype in _FAMILY_ROOTS:
            packed[name], slices[name] = write_packed(
                directory, f"packed-{name.replace('_', '-')}.npy", [getattr(item, name) for item in index.families], dtype=dtype
            )
        return {
            "schema": MVIDX_ARTIFACT_SCHEMA,
            "content_digest": index.content_digest,
            "dataset_id": index.dataset_id,
            "target_coverage_reference_digest": index.target_coverage_reference_digest,
            "neighborhood_digest": index.neighborhood_digest,
            "obligation_authority_digest": index.obligation_authority_digest,
            "frame_domain_digest": index.frame_domain_digest,
            "candidate_count": index.candidate_count,
            "obligations": [item.to_dict() for item in index.obligations],
            "correlation_unit_ids": list(index.correlation_unit_ids),
            "packed_family_arrays": packed,
            "families": [
                {
                    "family_id": item.family_id,
                    "family_digest": item.family_digest,
                    "witness_count": item.witness_count,
                    "edge_count": item.edge_count,
                    "content_digest": item.content_digest,
                    "array_slices": {name: slices[name][position] for name, _ in _FAMILY_ROOTS},
                }
                for position, item in enumerate(index.families)
            ],
            "arrays": {
                name: write_npy(directory, f"{name.replace('_', '-')}.npy", getattr(index, name)) for name in _DOMAIN_ARRAYS
            },
        }

    return publish_artifact_directory(
        destination,
        schema=MVIDX_ARTIFACT_SCHEMA,
        write=write,
        verify_existing=lambda path, _manifest: None,
    )


def _restore_families(directory: Path, manifest: Mapping[str, Any], names: Sequence[str]) -> tuple[dict[str, np.memmap], list[dict[str, np.ndarray]]]:
    if not isinstance(manifest.get("packed_family_arrays"), Mapping):
        raise TargetOrderArtifactStoreError(
            "MVIDX per-family persistence is not descriptor bounded; rebuild the reconstructible index."
        )
    roots = {name: read_packed(directory, manifest["packed_family_arrays"][name], label=f"MVIDX {name}") for name in names}
    cursors = {name: 0 for name in names}
    arrays: list[dict[str, np.ndarray]] = []
    try:
        for payload in manifest["families"]:
            member: dict[str, np.ndarray] = {}
            for name in names:
                descriptor = payload["array_slices"][name]
                member[name] = packed_slice(roots[name], descriptor, label=f"MVIDX {name}", cursor=cursors[name])
                cursors[name] = int(descriptor["stop"])
            arrays.append(member)
        if any(cursors[name] != int(roots[name].size) for name in names):
            raise TargetOrderArtifactStoreError("MVIDX packed arrays carry unreferenced trailing data.")
    except BaseException:
        for root in roots.values():
            close_memmap(root)
        raise
    return roots, arrays


def read_target_coverage_sparse_index(directory: Path) -> TargetCoverageSparseIndex:
    directory = Path(directory)
    manifest = read_manifest(directory, schema=MVIDX_ARTIFACT_SCHEMA)
    _, members = _restore_families(directory, manifest, [name for name, _ in _FAMILY_ROOTS])
    families = []
    for payload, member in zip(manifest["families"], members, strict=True):
        family = TargetCoverageSparseFamilyIndex(
            family_id=str(payload["family_id"]),
            family_digest=str(payload["family_digest"]),
            candidate_count=int(manifest["candidate_count"]),
            witness_count=int(payload["witness_count"]),
            array_references={name: payload["array_slices"][name]["array_reference"] for name, _ in _FAMILY_ROOTS},
            **member,
        )
        if family.content_digest != payload["content_digest"]:
            raise TargetOrderArtifactStoreError("MVIDX family content identity mismatch.")
        families.append(family)
    arrays = {name: read_npy(directory, manifest["arrays"][name], label=f"MVIDX {name}") for name in _DOMAIN_ARRAYS}
    index = TargetCoverageSparseIndex(
        dataset_id=str(manifest["dataset_id"]),
        target_coverage_reference_digest=str(manifest["target_coverage_reference_digest"]),
        neighborhood_digest=str(manifest["neighborhood_digest"]),
        obligation_authority_digest=str(manifest["obligation_authority_digest"]),
        frame_domain_digest=str(manifest["frame_domain_digest"]),
        candidate_count=int(manifest["candidate_count"]),
        families=tuple(families),
        obligations=tuple(SparseObligation(str(v["obligation_id"]), int(v["minimum_selected_frames"])) for v in manifest["obligations"]),
        correlation_unit_ids=tuple(manifest["correlation_unit_ids"]),
        **arrays,
    )
    if index.content_digest != manifest["content_digest"]:
        raise TargetOrderArtifactStoreError("MVIDX content identity mismatch.")
    return index


def read_target_coverage_sparse_forward_view(directory: Path) -> TargetCoverageSparseForwardView:
    """Restore only the candidate-oriented roots MVSEL2/REPAIR2 consume."""

    directory = Path(directory)
    manifest = read_manifest(directory, schema=MVIDX_ARTIFACT_SCHEMA)
    _, members = _restore_families(directory, manifest, ["candidate_offsets", "candidate_witnesses"])
    families = tuple(
        TargetCoverageSparseForwardFamilyView(
            family_id=str(payload["family_id"]),
            family_digest=str(payload["family_digest"]),
            mvidx_family_digest=str(payload["content_digest"]),
            candidate_count=int(manifest["candidate_count"]),
            witness_count=int(payload["witness_count"]),
            candidate_offsets=member["candidate_offsets"],
            candidate_witnesses=member["candidate_witnesses"],
        )
        for payload, member in zip(manifest["families"], members, strict=True)
    )
    return TargetCoverageSparseForwardView(
        dataset_id=str(manifest["dataset_id"]),
        mvidx_content_digest=str(manifest["content_digest"]),
        frame_domain_digest=str(manifest["frame_domain_digest"]),
        candidate_count=int(manifest["candidate_count"]),
        families=families,
        obligations=tuple(SparseObligation(str(v["obligation_id"]), int(v["minimum_selected_frames"])) for v in manifest["obligations"]),
        candidate_obligation_offsets=read_npy(directory, manifest["arrays"]["candidate_obligation_offsets"], label="MVIDX candidate_obligation_offsets"),
        candidate_obligations=read_npy(directory, manifest["arrays"]["candidate_obligations"], label="MVIDX candidate_obligations"),
        correlation_unit_ids=tuple(manifest["correlation_unit_ids"]),
        candidate_correlation_unit_codes=read_npy(directory, manifest["arrays"]["candidate_correlation_unit_codes"], label="MVIDX candidate_correlation_unit_codes"),
    )


__all__ = [
    "SparseObligation",
    "TargetCoverageSparseFamilyIndex",
    "TargetCoverageSparseForwardFamilyView",
    "TargetCoverageSparseForwardView",
    "TargetCoverageSparseIndex",
    "build_target_coverage_sparse_index",
    "csr_inverse",
    "indexed_family_covered_mass",
    "read_target_coverage_sparse_forward_view",
    "read_target_coverage_sparse_index",
    "sparse_forward_view",
    "write_target_coverage_sparse_index",
]
