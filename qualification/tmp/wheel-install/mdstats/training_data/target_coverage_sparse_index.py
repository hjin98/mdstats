"""TARGET-DATA2C-MVIDX1 exact sparse multi-view coverage substrate.

This module turns the frozen TARGET-DATA2B geometric coverage authority into
content-addressable sparse adjacency that later selector/repair gates can query
incrementally.  It deliberately does *not* select target frames.

Scientific arrays:

* each required feature family owns witness->candidate CSR-equivalent arrays;
* the exact inverse candidate->witness adjacency is persisted independently;
* hard extent, stratum, and correlation-interval obligations are represented by
  one bidirectional sparse obligation table;
* candidate correlation-unit codes are frozen for later provenance balancing.

Execution-only query worker/block settings never enter scientific digests.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import math
from pathlib import Path
import time
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from scipy.sparse import csr_matrix


from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from ._sparse_vector_kernels import csr_gather_rows
from .target_coverage import _coverage_array_reference, _validate_array_reference
from .target_coverage_exact_neighborhood import (
    TargetCoverageExactNeighborhoodFamily,
    TargetCoverageExactNeighborhoodStore,
    build_target_coverage_exact_neighborhood_store,
    validate_target_coverage_exact_neighborhood_store,
)
from .target_coverage_feasibility import validate_target_coverage_feasibility_authority
from .resources import StageResourceScope, available_cpu_threads
from .progress_timing import (
    ProgressRateTracker,
    format_progress_fraction,
    format_progress_timing_fields,
)
from .work_queue import DeterministicWorkQueue


TARGET_COVERAGE_SPARSE_INDEX_POLICY_SCHEMA = "mdstats.target-coverage-sparse-index-policy.v1"
TARGET_COVERAGE_SPARSE_FAMILY_SCHEMA = "mdstats.target-coverage-sparse-family-index.v1"
TARGET_COVERAGE_HARD_OBLIGATION_SCHEMA = "mdstats.target-coverage-hard-obligation.v1"
TARGET_COVERAGE_SPARSE_DOMAIN_SCHEMA = "mdstats.target-coverage-sparse-domain-index.v1"
TARGET_COVERAGE_SPARSE_INDEX_SCHEMA = "mdstats.target-coverage-sparse-index.v1"
TARGET_COVERAGE_SPARSE_INDEX_VERSION = "mdstats.target-data2c-mvidx1.coverage-index.2026-08.v1"
TARGET_COVERAGE_SPARSE_INDEX_PERSISTENCE_VERSION = "mdstats.target-data2c-mvidx1.native-persistence.2026-08.v1"

_UINT32_MAX = int(np.iinfo(np.uint32).max)
_INT32_MAX = int(np.iinfo(np.int32).max)
_TOLERANCE = 1.0e-12
_MIB = 1024 ** 2
_MVIDX_OUT_OF_CORE_MIN_OUTPUT_BYTES = 8 * _MIB
_MVIDX_OUT_OF_CORE_TASK_ADMISSION_BYTES = 768 * _MIB
_MVIDX_OUT_OF_CORE_CHUNK_SCRATCH_BYTES = 384 * _MIB
_MVIDX_VALIDATION_CHUNK_EDGES = 8 * 1024 * 1024
_NATIVE_RESTORE_TOKEN = object()


def _canonical_array(
    values: np.ndarray | Sequence[Any], *, dtype: str, ndim: int, name: str
) -> np.ndarray:
    target = np.dtype(dtype).newbyteorder("<")
    array = np.asarray(values, dtype=target)
    if array.ndim != ndim:
        raise TrainingDataInputError(f"TARGET-DATA2C-MVIDX1 {name} must have {ndim} dimensions.")
    array = np.ascontiguousarray(array, dtype=target)
    array.setflags(write=False)
    return array


def _validate_offsets(offsets: np.ndarray, *, item_count: int, edge_count: int, name: str) -> None:
    if offsets.shape != (item_count + 1,):
        raise TrainingDataInputError(f"TARGET-DATA2C-MVIDX1 {name} offsets are misaligned.")
    if int(offsets[0]) != 0 or int(offsets[-1]) != edge_count:
        raise TrainingDataInputError(f"TARGET-DATA2C-MVIDX1 {name} offsets do not span the edge array.")
    if np.any(offsets[1:] < offsets[:-1]):
        raise TrainingDataInputError(f"TARGET-DATA2C-MVIDX1 {name} offsets are not monotone.")


def _validate_sorted_unique_rows(offsets: np.ndarray, indices: np.ndarray, *, name: str) -> None:
    """Validate strict within-row ordering with bounded temporary memory.

    The predicate is identical to the historical per-row and MVKERNEL1
    vectorized validators.  Large file-backed MVIDX arrays can contain hundreds
    of millions of edges, so adjacent comparisons are evaluated in bounded
    edge chunks.  Only positions that actually violate monotonicity are tested
    against CSR row boundaries; cross-row pairs remain ignored exactly.
    """

    edge_count = int(indices.size)
    if edge_count < 2:
        return
    pair_count = edge_count - 1
    chunk = max(1, int(_MVIDX_VALIDATION_CHUNK_EDGES))
    for start in range(0, pair_count, chunk):
        stop = min(pair_count, start + chunk)
        bad = np.flatnonzero(indices[start + 1 : stop + 1] <= indices[start:stop])
        if bad.size == 0:
            continue
        positions = bad.astype(np.int64, copy=False) + int(start) + 1
        boundary_rows = np.searchsorted(offsets, positions, side="left")
        is_boundary = np.zeros(positions.size, dtype=np.bool_)
        valid = boundary_rows < len(offsets)
        if np.any(valid):
            is_boundary[valid] = offsets[boundary_rows[valid]] == positions[valid]
        if np.any(~is_boundary):
            raise TrainingDataInputError(
                f"TARGET-DATA2C-MVIDX1 {name} rows must be strictly sorted and duplicate-free."
            )


def _inline_array_payload(array: np.ndarray) -> list[Any]:
    return array.tolist()


@dataclass(frozen=True, slots=True)
class TargetCoverageSparseIndexPolicy:
    """Frozen MVIDX1 scientific/index-layout policy."""

    required_families_only: bool = True
    metric_tolerance: float = _TOLERANCE
    candidate_index_dtype: str = "<u4"
    witness_index_dtype: str = "<u4"
    offset_dtype: str = "<u8"
    authority_version: str = TARGET_COVERAGE_SPARSE_INDEX_VERSION

    def __post_init__(self) -> None:
        if not self.required_families_only:
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 v1 indexes required families only.")
        if not math.isclose(float(self.metric_tolerance), _TOLERANCE, rel_tol=0.0, abs_tol=0.0):
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 v1 freezes metric_tolerance at 1e-12.")
        if self.candidate_index_dtype != "<u4" or self.witness_index_dtype != "<u4" or self.offset_dtype != "<u8":
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 v1 freezes uint32 indices and uint64 offsets.")
        if self.authority_version != TARGET_COVERAGE_SPARSE_INDEX_VERSION:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-MVIDX1 authority version.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_SPARSE_INDEX_POLICY_SCHEMA,
            "required_families_only": self.required_families_only,
            "metric_tolerance": float(self.metric_tolerance),
            "candidate_index_dtype": self.candidate_index_dtype,
            "witness_index_dtype": self.witness_index_dtype,
            "offset_dtype": self.offset_dtype,
            "authority_version": self.authority_version,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageSparseIndexPolicy":
        if payload.get("schema") != TARGET_COVERAGE_SPARSE_INDEX_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVIDX1 policy schema.")
        result = cls(
            required_families_only=bool(payload["required_families_only"]),
            metric_tolerance=float(payload["metric_tolerance"]),
            candidate_index_dtype=str(payload["candidate_index_dtype"]),
            witness_index_dtype=str(payload["witness_index_dtype"]),
            offset_dtype=str(payload["offset_dtype"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVIDX1 policy digest mismatch.")
        return result


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
    _native_restore_token: InitVar[object | None] = None
    _native_array_references: InitVar[Mapping[str, Mapping[str, Any]] | None] = None
    _array_references: Mapping[str, Mapping[str, Any]] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(
        self,
        _native_restore_token: object | None,
        _native_array_references: Mapping[str, Mapping[str, Any]] | None,
    ) -> None:
        if not self.family_id.strip():
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 family_id cannot be empty.")
        family_digest = validate_digest(self.family_digest, name="family_digest")
        candidate_count = int(self.candidate_count)
        witness_count = int(self.witness_count)
        if candidate_count < 1 or witness_count < 1 or candidate_count > _UINT32_MAX or witness_count > _UINT32_MAX:
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 family cardinality exceeds v1 index range.")
        witness_offsets = _canonical_array(self.witness_offsets, dtype="<u8", ndim=1, name="witness_offsets")
        witness_candidates = _canonical_array(self.witness_candidates, dtype="<u4", ndim=1, name="witness_candidates")
        candidate_offsets = _canonical_array(self.candidate_offsets, dtype="<u8", ndim=1, name="candidate_offsets")
        candidate_witnesses = _canonical_array(self.candidate_witnesses, dtype="<u4", ndim=1, name="candidate_witnesses")
        edge_count = len(witness_candidates)
        if len(candidate_witnesses) != edge_count:
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 forward/inverse edge counts disagree.")
        _validate_offsets(witness_offsets, item_count=witness_count, edge_count=edge_count, name="witness")
        _validate_offsets(candidate_offsets, item_count=candidate_count, edge_count=edge_count, name="candidate")
        trusted_native_restore = _native_restore_token is _NATIVE_RESTORE_TOKEN
        if trusted_native_restore:
            if not isinstance(_native_array_references, Mapping):
                raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 native restore lacks array identities.")
            names = (
                "witness_offsets",
                "witness_candidates",
                "candidate_offsets",
                "candidate_witnesses",
            )
            if any(not isinstance(_native_array_references.get(name), Mapping) for name in names):
                raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 native restore array identities are incomplete.")
            references = {name: dict(_native_array_references[name]) for name in names}
        else:
            if edge_count and (
                int(np.max(witness_candidates)) >= candidate_count
                or int(np.max(candidate_witnesses)) >= witness_count
            ):
                raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 sparse family index contains out-of-range edges.")
            _validate_sorted_unique_rows(witness_offsets, witness_candidates, name="witness-to-candidate")
            _validate_sorted_unique_rows(candidate_offsets, candidate_witnesses, name="candidate-to-witness")
            references = {
                "witness_offsets": _coverage_array_reference(witness_offsets),
                "witness_candidates": _coverage_array_reference(witness_candidates),
                "candidate_offsets": _coverage_array_reference(candidate_offsets),
                "candidate_witnesses": _coverage_array_reference(candidate_witnesses),
            }
        object.__setattr__(self, "family_digest", family_digest)
        object.__setattr__(self, "candidate_count", candidate_count)
        object.__setattr__(self, "witness_count", witness_count)
        object.__setattr__(self, "witness_offsets", witness_offsets)
        object.__setattr__(self, "witness_candidates", witness_candidates)
        object.__setattr__(self, "candidate_offsets", candidate_offsets)
        object.__setattr__(self, "candidate_witnesses", candidate_witnesses)
        object.__setattr__(self, "_array_references", references)

    @classmethod
    def _from_validated_native(
        cls,
        *,
        array_references: Mapping[str, Mapping[str, Any]],
        **values: Any,
    ) -> "TargetCoverageSparseFamilyIndex":
        """Construct from arrays already authenticated by the native store."""

        return cls(
            **values,
            _native_restore_token=_NATIVE_RESTORE_TOKEN,
            _native_array_references=array_references,
        )

    @property
    def edge_count(self) -> int:
        return len(self.witness_candidates)

    @property
    def array_references(self) -> Mapping[str, Mapping[str, Any]]:
        return self._array_references

    def witness_candidate_indices(self, witness_index: int) -> np.ndarray:
        row = int(witness_index)
        if row < 0 or row >= self.witness_count:
            raise IndexError(row)
        start, stop = int(self.witness_offsets[row]), int(self.witness_offsets[row + 1])
        return self.witness_candidates[start:stop]

    def candidate_witness_indices(self, candidate_index: int) -> np.ndarray:
        row = int(candidate_index)
        if row < 0 or row >= self.candidate_count:
            raise IndexError(row)
        start, stop = int(self.candidate_offsets[row]), int(self.candidate_offsets[row + 1])
        return self.candidate_witnesses[start:stop]

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_SPARSE_FAMILY_SCHEMA,
            "family_id": self.family_id,
            "family_digest": self.family_digest,
            "candidate_count": self.candidate_count,
            "witness_count": self.witness_count,
            "edge_count": self.edge_count,
            "array_references": {name: dict(value) for name, value in sorted(self._array_references.items())},
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TargetCoverageSparseFamilyIndex):
            return NotImplemented
        return self.content_digest == other.content_digest

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._digest_payload(),
            "array_encoding": "inline-json-v1",
            "witness_offsets": _inline_array_payload(self.witness_offsets),
            "witness_candidates": _inline_array_payload(self.witness_candidates),
            "candidate_offsets": _inline_array_payload(self.candidate_offsets),
            "candidate_witnesses": _inline_array_payload(self.candidate_witnesses),
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageSparseFamilyIndex":
        if payload.get("schema") != TARGET_COVERAGE_SPARSE_FAMILY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVIDX1 family schema.")
        if payload.get("array_encoding") not in (None, "inline-json-v1"):
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVIDX1 inline array encoding.")
        result = cls(
            family_id=str(payload["family_id"]),
            family_digest=str(payload["family_digest"]),
            candidate_count=int(payload["candidate_count"]),
            witness_count=int(payload["witness_count"]),
            witness_offsets=payload["witness_offsets"],
            witness_candidates=payload["witness_candidates"],
            candidate_offsets=payload["candidate_offsets"],
            candidate_witnesses=payload["candidate_witnesses"],
        )
        references = payload.get("array_references")
        if isinstance(references, Mapping):
            for name in result._array_references:
                supplied = references.get(name)
                if not isinstance(supplied, Mapping):
                    raise TrainingDataSerializationError(f"TARGET-DATA2C-MVIDX1 family lacks {name} identity.")
                _validate_array_reference(supplied, getattr(result, name), name=f"MVIDX1 {name}")
        if int(payload.get("edge_count", result.edge_count)) != result.edge_count:
            raise TrainingDataSerializationError("TARGET-DATA2C-MVIDX1 family edge count mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVIDX1 family digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageHardObligation:
    obligation_id: str
    obligation_kind: str
    minimum_selected_frames: int
    required: bool
    reason_code: str
    family_id: str | None = None
    feature_name: str | None = None
    source_id: str | None = None

    def __post_init__(self) -> None:
        if not self.obligation_id.strip() or not self.obligation_kind.strip() or not self.reason_code.strip():
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 hard obligation identity is invalid.")
        if self.obligation_kind not in {"extent_lower", "extent_upper", "stratum", "correlation_interval"}:
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 hard obligation kind is invalid.")
        if int(self.minimum_selected_frames) < 1:
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 hard obligation minimum must be positive.")
        object.__setattr__(self, "minimum_selected_frames", int(self.minimum_selected_frames))
        for name in ("family_id", "feature_name", "source_id"):
            value = getattr(self, name)
            if value is not None and not str(value).strip():
                raise TrainingDataInputError(f"TARGET-DATA2C-MVIDX1 obligation {name} cannot be empty when supplied.")

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_COVERAGE_HARD_OBLIGATION_SCHEMA,
            "obligation_id": self.obligation_id,
            "obligation_kind": self.obligation_kind,
            "minimum_selected_frames": self.minimum_selected_frames,
            "required": self.required,
            "reason_code": self.reason_code,
            "family_id": self.family_id,
            "feature_name": self.feature_name,
            "source_id": self.source_id,
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageHardObligation":
        if payload.get("schema") != TARGET_COVERAGE_HARD_OBLIGATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVIDX1 obligation schema.")
        result = cls(
            obligation_id=str(payload["obligation_id"]),
            obligation_kind=str(payload["obligation_kind"]),
            minimum_selected_frames=int(payload["minimum_selected_frames"]),
            required=bool(payload["required"]),
            reason_code=str(payload["reason_code"]),
            family_id=None if payload.get("family_id") is None else str(payload["family_id"]),
            feature_name=None if payload.get("feature_name") is None else str(payload["feature_name"]),
            source_id=None if payload.get("source_id") is None else str(payload["source_id"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVIDX1 obligation digest mismatch.")
        return result


@dataclass(frozen=True, slots=True, eq=False)
class TargetCoverageSparseDomainIndex:
    label_domain_id: str
    frame_domain_digest: str
    candidate_count: int
    families: tuple[TargetCoverageSparseFamilyIndex, ...]
    obligations: tuple[TargetCoverageHardObligation, ...]
    obligation_offsets: np.ndarray | Sequence[int]
    obligation_candidates: np.ndarray | Sequence[int]
    candidate_obligation_offsets: np.ndarray | Sequence[int]
    candidate_obligations: np.ndarray | Sequence[int]
    correlation_unit_ids: tuple[str, ...]
    candidate_correlation_unit_codes: np.ndarray | Sequence[int]
    _family_by_id: Mapping[str, TargetCoverageSparseFamilyIndex] = field(default_factory=dict, init=False, repr=False, compare=False)
    _obligation_by_id: Mapping[str, int] = field(default_factory=dict, init=False, repr=False, compare=False)
    _array_references: Mapping[str, Mapping[str, Any]] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.label_domain_id.strip():
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 domain label cannot be empty.")
        frame_digest = validate_digest(self.frame_domain_digest, name="frame_domain_digest")
        candidate_count = int(self.candidate_count)
        if candidate_count < 1 or candidate_count > _UINT32_MAX:
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 candidate count exceeds v1 index range.")
        families = tuple(sorted(self.families, key=lambda item: item.family_id))
        if not families or len({item.family_id for item in families}) != len(families):
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 domain requires unique required-family indices.")
        if any(item.candidate_count != candidate_count for item in families):
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 family candidate domains disagree.")
        obligations = tuple(sorted(self.obligations, key=lambda item: item.obligation_id))
        if not obligations or len({item.obligation_id for item in obligations}) != len(obligations):
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 domain requires unique hard obligations.")
        obligation_offsets = _canonical_array(self.obligation_offsets, dtype="<u8", ndim=1, name="obligation_offsets")
        obligation_candidates = _canonical_array(self.obligation_candidates, dtype="<u4", ndim=1, name="obligation_candidates")
        candidate_obligation_offsets = _canonical_array(self.candidate_obligation_offsets, dtype="<u8", ndim=1, name="candidate_obligation_offsets")
        candidate_obligations = _canonical_array(self.candidate_obligations, dtype="<u4", ndim=1, name="candidate_obligations")
        unit_codes = _canonical_array(self.candidate_correlation_unit_codes, dtype="<u4", ndim=1, name="candidate_correlation_unit_codes")
        edge_count = len(obligation_candidates)
        if len(candidate_obligations) != edge_count:
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 obligation forward/inverse edge counts disagree.")
        _validate_offsets(obligation_offsets, item_count=len(obligations), edge_count=edge_count, name="obligation")
        _validate_offsets(candidate_obligation_offsets, item_count=candidate_count, edge_count=edge_count, name="candidate-obligation")
        if edge_count and (
            int(np.max(obligation_candidates)) >= candidate_count
            or int(np.max(candidate_obligations)) >= len(obligations)
        ):
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 obligation index contains out-of-range edges.")
        _validate_sorted_unique_rows(obligation_offsets, obligation_candidates, name="obligation-to-candidate")
        _validate_sorted_unique_rows(candidate_obligation_offsets, candidate_obligations, name="candidate-to-obligation")
        units = tuple(validate_digest(item, name="correlation_unit_id") for item in self.correlation_unit_ids)
        if not units or len(set(units)) != len(units) or tuple(sorted(units)) != units:
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 correlation-unit IDs must be sorted unique digests.")
        if unit_codes.shape != (candidate_count,) or int(np.max(unit_codes)) >= len(units):
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 candidate correlation-unit codes are invalid.")
        refs = {
            "obligation_offsets": _coverage_array_reference(obligation_offsets),
            "obligation_candidates": _coverage_array_reference(obligation_candidates),
            "candidate_obligation_offsets": _coverage_array_reference(candidate_obligation_offsets),
            "candidate_obligations": _coverage_array_reference(candidate_obligations),
            "candidate_correlation_unit_codes": _coverage_array_reference(unit_codes),
        }
        object.__setattr__(self, "frame_domain_digest", frame_digest)
        object.__setattr__(self, "candidate_count", candidate_count)
        object.__setattr__(self, "families", families)
        object.__setattr__(self, "obligations", obligations)
        object.__setattr__(self, "obligation_offsets", obligation_offsets)
        object.__setattr__(self, "obligation_candidates", obligation_candidates)
        object.__setattr__(self, "candidate_obligation_offsets", candidate_obligation_offsets)
        object.__setattr__(self, "candidate_obligations", candidate_obligations)
        object.__setattr__(self, "correlation_unit_ids", units)
        object.__setattr__(self, "candidate_correlation_unit_codes", unit_codes)
        object.__setattr__(self, "_family_by_id", {item.family_id: item for item in families})
        object.__setattr__(self, "_obligation_by_id", {item.obligation_id: i for i, item in enumerate(obligations)})
        object.__setattr__(self, "_array_references", refs)

    @property
    def obligation_edge_count(self) -> int:
        return len(self.obligation_candidates)

    @property
    def array_references(self) -> Mapping[str, Mapping[str, Any]]:
        return self._array_references

    def family(self, family_id: str) -> TargetCoverageSparseFamilyIndex:
        try:
            return self._family_by_id[family_id]
        except KeyError:
            raise KeyError(family_id) from None

    def obligation_index(self, obligation_id: str) -> int:
        try:
            return self._obligation_by_id[obligation_id]
        except KeyError:
            raise KeyError(obligation_id) from None

    def obligation_candidate_indices(self, obligation_index: int) -> np.ndarray:
        row = int(obligation_index)
        if row < 0 or row >= len(self.obligations):
            raise IndexError(row)
        start, stop = int(self.obligation_offsets[row]), int(self.obligation_offsets[row + 1])
        return self.obligation_candidates[start:stop]

    def candidate_obligation_indices(self, candidate_index: int) -> np.ndarray:
        row = int(candidate_index)
        if row < 0 or row >= self.candidate_count:
            raise IndexError(row)
        start, stop = int(self.candidate_obligation_offsets[row]), int(self.candidate_obligation_offsets[row + 1])
        return self.candidate_obligations[start:stop]

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_SPARSE_DOMAIN_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "frame_domain_digest": self.frame_domain_digest,
            "candidate_count": self.candidate_count,
            "family_digests": [item.content_digest for item in self.families],
            "obligations": [item.to_dict() for item in self.obligations],
            "correlation_unit_ids": list(self.correlation_unit_ids),
            "obligation_edge_count": self.obligation_edge_count,
            "array_references": {name: dict(value) for name, value in sorted(self._array_references.items())},
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TargetCoverageSparseDomainIndex):
            return NotImplemented
        return self.content_digest == other.content_digest

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._digest_payload(),
            "families": [item.to_dict() for item in self.families],
            "array_encoding": "inline-json-v1",
            "obligation_offsets": _inline_array_payload(self.obligation_offsets),
            "obligation_candidates": _inline_array_payload(self.obligation_candidates),
            "candidate_obligation_offsets": _inline_array_payload(self.candidate_obligation_offsets),
            "candidate_obligations": _inline_array_payload(self.candidate_obligations),
            "candidate_correlation_unit_codes": _inline_array_payload(self.candidate_correlation_unit_codes),
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageSparseDomainIndex":
        if payload.get("schema") != TARGET_COVERAGE_SPARSE_DOMAIN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVIDX1 domain schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            frame_domain_digest=str(payload["frame_domain_digest"]),
            candidate_count=int(payload["candidate_count"]),
            families=tuple(TargetCoverageSparseFamilyIndex.from_dict(item) for item in payload["families"]),
            obligations=tuple(TargetCoverageHardObligation.from_dict(item) for item in payload["obligations"]),
            obligation_offsets=payload["obligation_offsets"],
            obligation_candidates=payload["obligation_candidates"],
            candidate_obligation_offsets=payload["candidate_obligation_offsets"],
            candidate_obligations=payload["candidate_obligations"],
            correlation_unit_ids=tuple(str(item) for item in payload["correlation_unit_ids"]),
            candidate_correlation_unit_codes=payload["candidate_correlation_unit_codes"],
        )
        references = payload.get("array_references")
        if isinstance(references, Mapping):
            for name in result._array_references:
                supplied = references.get(name)
                if not isinstance(supplied, Mapping):
                    raise TrainingDataSerializationError(f"TARGET-DATA2C-MVIDX1 domain lacks {name} identity.")
                _validate_array_reference(supplied, getattr(result, name), name=f"MVIDX1 {name}")
        if payload.get("family_digests") not in (None, [item.content_digest for item in result.families]):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVIDX1 domain family-digest mismatch.")
        if int(payload.get("obligation_edge_count", result.obligation_edge_count)) != result.obligation_edge_count:
            raise TrainingDataSerializationError("TARGET-DATA2C-MVIDX1 obligation edge-count mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVIDX1 domain digest mismatch.")
        return result


@dataclass(frozen=True, slots=True, eq=False)
class TargetCoverageSparseIndex:
    dataset_id: str
    target_coverage_reference_digest: str
    target_data_role_freeze_digest: str
    target_coverage_feasibility_digest: str
    policy: TargetCoverageSparseIndexPolicy
    domains: tuple[TargetCoverageSparseDomainIndex, ...]
    authority_version: str = TARGET_COVERAGE_SPARSE_INDEX_VERSION
    _domain_by_id: Mapping[str, TargetCoverageSparseDomainIndex] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.dataset_id.strip():
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 dataset_id cannot be empty.")
        reference_digest = validate_digest(self.target_coverage_reference_digest, name="target_coverage_reference_digest")
        role_digest = validate_digest(self.target_data_role_freeze_digest, name="target_data_role_freeze_digest")
        feasibility_digest = validate_digest(self.target_coverage_feasibility_digest, name="target_coverage_feasibility_digest")
        domains = tuple(sorted(self.domains, key=lambda item: item.label_domain_id))
        if not domains or len({item.label_domain_id for item in domains}) != len(domains):
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 requires unique domain indices.")
        if self.authority_version != TARGET_COVERAGE_SPARSE_INDEX_VERSION:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-MVIDX1 index authority version.")
        object.__setattr__(self, "target_coverage_reference_digest", reference_digest)
        object.__setattr__(self, "target_data_role_freeze_digest", role_digest)
        object.__setattr__(self, "target_coverage_feasibility_digest", feasibility_digest)
        object.__setattr__(self, "domains", domains)
        object.__setattr__(self, "_domain_by_id", {item.label_domain_id: item for item in domains})

    def domain(self, label_domain_id: str) -> TargetCoverageSparseDomainIndex:
        try:
            return self._domain_by_id[label_domain_id]
        except KeyError:
            raise KeyError(label_domain_id) from None

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_SPARSE_INDEX_SCHEMA,
            "dataset_id": self.dataset_id,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "target_data_role_freeze_digest": self.target_data_role_freeze_digest,
            "target_coverage_feasibility_digest": self.target_coverage_feasibility_digest,
            "policy": self.policy.to_dict(),
            "domain_digests": [item.content_digest for item in self.domains],
            "authority_version": self.authority_version,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TargetCoverageSparseIndex):
            return NotImplemented
        return self.content_digest == other.content_digest

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._digest_payload(),
            "domains": [item.to_dict() for item in self.domains],
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageSparseIndex":
        if payload.get("schema") != TARGET_COVERAGE_SPARSE_INDEX_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVIDX1 index schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            target_coverage_reference_digest=str(payload["target_coverage_reference_digest"]),
            target_data_role_freeze_digest=str(payload["target_data_role_freeze_digest"]),
            target_coverage_feasibility_digest=str(payload["target_coverage_feasibility_digest"]),
            policy=TargetCoverageSparseIndexPolicy.from_dict(payload["policy"]),
            domains=tuple(TargetCoverageSparseDomainIndex.from_dict(item) for item in payload["domains"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("domain_digests") not in (None, [item.content_digest for item in result.domains]):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVIDX1 domain-digest mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVIDX1 index digest mismatch.")
        return result


def _csr_inverse(
    row_offsets: np.ndarray,
    row_columns: np.ndarray,
    *,
    row_count: int,
    column_count: int,
    workers: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """Return exact column->row CSR-equivalent arrays from row->column CSR.

    MVIDX-REUSE1 deliberately keeps each individual transpose single-threaded
    and parallelizes independent families/obligation tables at the outer queue.
    SciPy's compiled CSR->CSC conversion is a deterministic counting transpose;
    no atomics or floating-point reductions participate in scientific output.
    """

    edge_count = len(row_columns)
    if column_count > _INT32_MAX or row_count > _INT32_MAX:
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 v1 sparse transpose requires cardinalities below int32 range.")
    data = np.ones(edge_count, dtype=np.uint8)
    matrix = csr_matrix(
        (data, row_columns.view(np.int32), np.asarray(row_offsets, dtype=np.int64)),
        shape=(row_count, column_count),
    )
    inverse = matrix.tocsc(copy=True)
    # csr->csc emits sorted source-row indices for canonical CSR input.  Keep
    # the explicit sort as a fail-safe against backend/version differences.
    inverse.sort_indices()
    offsets = np.asarray(inverse.indptr, dtype="<u8")
    rows = np.asarray(inverse.indices, dtype="<u4")
    offsets.setflags(write=False)
    rows.setflags(write=False)
    return offsets, rows

def _out_of_core_chunk_row_stop(
    row_offsets: np.ndarray,
    *,
    row_start: int,
    row_count: int,
    maximum_edges: int,
) -> int:
    """Return the next canonical row boundary for one bounded transpose chunk."""

    if row_start >= row_count:
        return row_count
    edge_start = int(row_offsets[row_start])
    target = edge_start + max(1, int(maximum_edges))
    stop = int(np.searchsorted(row_offsets, target, side="right") - 1)
    stop = max(row_start + 1, min(row_count, stop))
    return stop


def _csr_inverse_out_of_core(
    row_offsets: np.ndarray,
    row_columns: np.ndarray,
    *,
    row_count: int,
    column_count: int,
    output_path: str | Path,
    chunk_scratch_bytes: int = _MVIDX_OUT_OF_CORE_CHUNK_SCRATCH_BYTES,
) -> tuple[np.ndarray, np.ndarray]:
    """Return exact CSC-equivalent arrays with file-backed inverse indices.

    This is the large-scale MVIDX path.  The final ``candidate_witnesses``
    payload is created directly as an NPY memmap, while deterministic SciPy
    counting transposes are performed on ascending source-row chunks.  For each
    candidate column, chunk-local source rows are appended in ascending chunk
    order, which is byte-identical to the full canonical CSR->CSC transpose.
    Floating-point arithmetic is not involved.
    """

    edge_count = int(len(row_columns))
    if column_count > _INT32_MAX or row_count > _INT32_MAX:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVIDX1 v1 sparse transpose requires cardinalities below int32 range."
        )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    # One bounded-memory O(E) pass establishes final canonical column offsets.
    # ``np.bincount`` may promote integer inputs internally, so never hand it
    # the complete multi-hundred-million-edge uint32 memmap at once.
    counts = np.zeros(int(column_count), dtype=np.uint64)
    count_chunk_edges = max(1, int(chunk_scratch_bytes) // 16)
    for edge_start in range(0, edge_count, count_chunk_edges):
        edge_stop = min(edge_count, edge_start + count_chunk_edges)
        counts += np.bincount(
            row_columns[edge_start:edge_stop], minlength=int(column_count)
        ).astype(np.uint64, copy=False)
    offsets = np.empty(int(column_count) + 1, dtype="<u8")
    offsets[0] = 0
    np.cumsum(counts, dtype=np.uint64, out=offsets[1:])
    if int(offsets[-1]) != edge_count:
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 out-of-core transpose edge count mismatch.")

    rows = np.lib.format.open_memmap(
        destination, mode="w+", dtype="<u4", shape=(edge_count,)
    )
    written = np.zeros(int(column_count), dtype=np.uint64)

    # Conservative scratch accounting: SciPy owns uint8 CSR/CSC data plus one
    # int32 CSC index payload and temporary counting workspace.  Sixteen bytes
    # per chunk edge leaves headroom for allocator/backend variation.
    maximum_chunk_edges = max(1, int(chunk_scratch_bytes) // 16)
    row_start = 0
    try:
        while row_start < int(row_count):
            row_stop = _out_of_core_chunk_row_stop(
                row_offsets,
                row_start=row_start,
                row_count=int(row_count),
                maximum_edges=maximum_chunk_edges,
            )
            edge_start = int(row_offsets[row_start])
            edge_stop = int(row_offsets[row_stop])
            local_edge_count = edge_stop - edge_start
            if local_edge_count > 0:
                local_offsets = (
                    np.asarray(row_offsets[row_start : row_stop + 1], dtype=np.int64) - edge_start
                )
                local_columns = row_columns[edge_start:edge_stop].view(np.int32)
                data = np.ones(local_edge_count, dtype=np.uint8)
                matrix = csr_matrix(
                    (data, local_columns, local_offsets),
                    shape=(row_stop - row_start, int(column_count)),
                )
                inverse = matrix.tocsc(copy=True)
                inverse.sort_indices()
                local_counts = np.diff(inverse.indptr).astype(np.uint64, copy=False)
                nonempty = np.flatnonzero(local_counts)
                for column in nonempty:
                    column = int(column)
                    src_start = int(inverse.indptr[column])
                    src_stop = int(inverse.indptr[column + 1])
                    dst_start = int(offsets[column] + written[column])
                    dst_stop = dst_start + (src_stop - src_start)
                    np.add(
                        inverse.indices[src_start:src_stop],
                        np.uint32(row_start),
                        out=rows[dst_start:dst_stop],
                        casting="unsafe",
                    )
                written += local_counts
                # Bound dirty file-backed pages before the next large chunk.
                rows.flush()
                del inverse, matrix, data, local_offsets, local_columns, local_counts, nonempty
            row_start = row_stop
    except Exception:
        try:
            rows.flush()
        finally:
            del rows
            destination.unlink(missing_ok=True)
        raise

    if not np.array_equal(written, counts):
        del rows
        destination.unlink(missing_ok=True)
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 out-of-core transpose fill mismatch.")
    rows.flush()
    offsets.setflags(write=False)
    rows.setflags(write=False)
    return offsets, rows


def _family_uses_out_of_core_inverse(
    neighborhood: TargetCoverageExactNeighborhoodFamily,
    *,
    out_of_core_directory: str | Path | None,
) -> bool:
    return (
        out_of_core_directory is not None
        and int(neighborhood.edge_count) * np.dtype("<u4").itemsize
        >= _MVIDX_OUT_OF_CORE_MIN_OUTPUT_BYTES
    )


def _build_family_sparse_index_from_neighborhood(
    family: Any,
    neighborhood: TargetCoverageExactNeighborhoodFamily,
    *,
    candidate_count: int,
    inverse_workers: int = 1,
    inverse_output_path: str | Path | None = None,
    inverse_chunk_scratch_bytes: int = _MVIDX_OUT_OF_CORE_CHUNK_SCRATCH_BYTES,
) -> TargetCoverageSparseFamilyIndex:
    """Adopt authenticated NEIGHBOR1 forward CSR and build the exact inverse.

    ``inverse_output_path`` is execution-only.  When supplied, the inverse edge
    payload is built out-of-core into that NPY member while preserving the same
    canonical candidate->witness arrays and scientific digest.
    """

    if neighborhood.family_id != family.family_id or neighborhood.family_digest != family.content_digest:
        raise TrainingDataInputError(
            f"TARGET-DATA2C-MVIDX1 NEIGHBOR1 family identity mismatch for {family.family_id!r}."
        )
    if neighborhood.candidate_count != int(candidate_count) or neighborhood.witness_count != len(family.values):
        raise TrainingDataInputError(
            f"TARGET-DATA2C-MVIDX1 NEIGHBOR1 cardinality mismatch for {family.family_id!r}."
        )
    witness_offsets = np.asarray(neighborhood.witness_offsets, dtype="<u8")
    witness_candidates = np.asarray(neighborhood.witness_candidates, dtype="<u4")
    if inverse_output_path is None:
        candidate_offsets, candidate_witnesses = _csr_inverse(
            witness_offsets,
            witness_candidates,
            row_count=neighborhood.witness_count,
            column_count=candidate_count,
            workers=inverse_workers,
        )
    else:
        candidate_offsets, candidate_witnesses = _csr_inverse_out_of_core(
            witness_offsets,
            witness_candidates,
            row_count=neighborhood.witness_count,
            column_count=candidate_count,
            output_path=inverse_output_path,
            chunk_scratch_bytes=inverse_chunk_scratch_bytes,
        )
    return TargetCoverageSparseFamilyIndex(
        family_id=family.family_id,
        family_digest=family.content_digest,
        candidate_count=candidate_count,
        witness_count=neighborhood.witness_count,
        witness_offsets=witness_offsets,
        witness_candidates=witness_candidates,
        candidate_offsets=candidate_offsets,
        candidate_witnesses=candidate_witnesses,
    )

def _role_domain_units(role_domain: Any, frame_uids: Sequence[str]) -> tuple[tuple[str, ...], np.ndarray, list[np.ndarray]]:
    index_by_uid = {uid: i for i, uid in enumerate(frame_uids)}
    unit_members: dict[str, np.ndarray] = {}
    seen = np.zeros(len(frame_uids), dtype=np.bool_)
    for interval in role_domain.development_intervals:
        unit_id = validate_digest(interval.unit_id, name="development_interval_unit_id")
        rows = np.asarray(sorted(index_by_uid[uid] for uid in interval.frame_uids if uid in index_by_uid), dtype=np.int64)
        if rows.size == 0:
            raise TrainingDataInputError(
                f"TARGET-DATA2C-MVIDX1 development interval {unit_id[:12]} has no candidate frame."
            )
        if np.any(seen[rows]):
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 development correlation intervals overlap.")
        seen[rows] = True
        unit_members[unit_id] = rows
    if not np.all(seen):
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 development correlation intervals do not cover the candidate domain.")
    unit_ids = tuple(sorted(unit_members))
    code_by_unit = {unit_id: code for code, unit_id in enumerate(unit_ids)}
    codes = np.empty(len(frame_uids), dtype="<u4")
    members: list[np.ndarray] = []
    for unit_id in unit_ids:
        rows = unit_members[unit_id]
        codes[rows] = code_by_unit[unit_id]
        members.append(rows)
    codes.setflags(write=False)
    return unit_ids, codes, members


def _obligation_rows(
    domain: Any,
    role_domain: Any,
) -> tuple[tuple[TargetCoverageHardObligation, ...], list[np.ndarray], tuple[str, ...], np.ndarray]:
    n = len(domain.frame_uids)
    rows: list[tuple[TargetCoverageHardObligation, np.ndarray]] = []

    for stratum in domain.strata:
        candidates = np.asarray(sorted(set(int(v) for v in stratum.frame_indices)), dtype=np.int64)
        if candidates.size < int(stratum.minimum_selected_frames) or np.any(candidates < 0) or np.any(candidates >= n):
            raise TrainingDataInputError(f"TARGET-DATA2C-MVIDX1 stratum {stratum.stratum_id!r} is invalid.")
        rows.append((
            TargetCoverageHardObligation(
                obligation_id=f"stratum:{stratum.stratum_id}",
                obligation_kind="stratum",
                minimum_selected_frames=int(stratum.minimum_selected_frames),
                required=bool(stratum.required),
                reason_code=f"mandatory_{stratum.stratum_kind}" if stratum.required else f"diagnostic_{stratum.stratum_kind}",
                source_id=stratum.stratum_id,
            ),
            candidates,
        ))

    for family in sorted((item for item in domain.families if item.required), key=lambda item: item.family_id):
        values = np.asarray(family.values, dtype=np.float64)
        frame_indices = np.asarray(family.frame_indices, dtype=np.int64)
        for channel in family.extent_channels:
            feature = int(channel.feature_index)
            column = values[:, feature]
            lower_rows = np.flatnonzero(column <= float(channel.lower_reference_quantile) + _TOLERANCE)
            upper_rows = np.flatnonzero(column >= float(channel.upper_reference_quantile) - _TOLERANCE)
            for side, element_rows in (("lower", lower_rows), ("upper", upper_rows)):
                candidates = np.unique(frame_indices[element_rows])
                if candidates.size == 0:
                    raise TrainingDataInputError(
                        f"TARGET-DATA2C-MVIDX1 extent obligation {family.family_id}:{channel.feature_name}:{side} has no support."
                    )
                rows.append((
                    TargetCoverageHardObligation(
                        obligation_id=f"extent:{family.family_id}:{channel.feature_name}:{side}",
                        obligation_kind=f"extent_{side}",
                        minimum_selected_frames=1,
                        required=True,
                        reason_code=f"mandatory_extent_{side}",
                        family_id=family.family_id,
                        feature_name=channel.feature_name,
                        source_id=family.content_digest,
                    ),
                    np.asarray(candidates, dtype=np.int64),
                ))

    unit_ids, unit_codes, unit_members = _role_domain_units(role_domain, domain.frame_uids)
    for unit_id, candidates in zip(unit_ids, unit_members, strict=True):
        rows.append((
            TargetCoverageHardObligation(
                obligation_id=f"correlation_interval:{unit_id}",
                obligation_kind="correlation_interval",
                minimum_selected_frames=1,
                required=True,
                reason_code="mandatory_correlation_interval",
                source_id=unit_id,
            ),
            candidates,
        ))

    rows.sort(key=lambda item: item[0].obligation_id)
    ids = [item[0].obligation_id for item in rows]
    if not rows or len(ids) != len(set(ids)):
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 hard obligation IDs are empty or duplicated.")
    return tuple(item[0] for item in rows), [item[1] for item in rows], unit_ids, unit_codes


def _build_obligation_sparse_index(
    domain: Any,
    role_domain: Any,
    *,
    inverse_workers: int = 1,
) -> tuple[
    tuple[TargetCoverageHardObligation, ...],
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    tuple[str, ...],
    np.ndarray,
]:
    obligations, rows, unit_ids, unit_codes = _obligation_rows(domain, role_domain)
    counts = np.asarray([len(row) for row in rows], dtype=np.uint64)
    offsets = np.empty(len(rows) + 1, dtype="<u8")
    offsets[0] = 0
    np.cumsum(counts, dtype=np.uint64, out=offsets[1:])
    candidates = np.concatenate([np.asarray(row, dtype="<u4") for row in rows]) if rows else np.empty(0, dtype="<u4")
    candidate_offsets, candidate_obligations = _csr_inverse(
        offsets,
        candidates,
        row_count=len(obligations),
        column_count=len(domain.frame_uids),
        workers=inverse_workers,
    )
    return obligations, offsets, candidates, candidate_offsets, candidate_obligations, unit_ids, unit_codes



def _mvidx_resource_scope(workers: int) -> StageResourceScope:
    available = available_cpu_threads()
    allocated = max(1, min(int(workers), int(available)))
    return StageResourceScope(
        stage_name="TARGET-DATA2C-MVIDX-REUSE1",
        cpu_threads_available=int(available),
        cpu_threads_budget=int(allocated),
        python_workers=int(allocated),
        structural_workers=1,
        tree_workers=1,
        blas_threads=1,
        pytorch_cpu_workers=1,
        # Direct API default: no transient host-derived hard RAM ceiling.
        # Campaign execution supplies an explicit bounded scope.
        ram_budget_bytes=None,
    )


def _family_build_memory_estimate(
    neighborhood: TargetCoverageExactNeighborhoodFamily,
    *,
    out_of_core: bool = False,
    out_of_core_admission_bytes: int = _MVIDX_OUT_OF_CORE_TASK_ADMISSION_BYTES,
) -> int:
    if out_of_core:
        # The final inverse edge array is file-backed.  Admission therefore
        # covers bounded SciPy chunk scratch, validation workspace, and O(C)
        # counters rather than the complete edge payload.
        candidate_bytes = (int(neighborhood.candidate_count) + 1) * 32
        return max(1, int(out_of_core_admission_bytes) + candidate_bytes)
    # In-memory path: persistent inverse indices plus temporary SciPy
    # data/index arrays and vectorized validation workspace.
    edge_bytes = int(neighborhood.edge_count) * 18
    offset_bytes = (int(neighborhood.candidate_count) + 1) * 16
    return max(1, edge_bytes + offset_bytes)


def _build_domain_sparse_components(
    domain: Any,
    role_domain: Any,
    neighborhoods: TargetCoverageExactNeighborhoodStore,
    *,
    inverse_workers: int,
    progress_callback: Callable[[str], None] | None,
    resource_scope: StageResourceScope | None = None,
    out_of_core_directory: str | Path | None = None,
    progress_interval_seconds: float = 30.0,
) -> tuple[
    tuple[TargetCoverageSparseFamilyIndex, ...],
    tuple[TargetCoverageHardObligation, ...],
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    tuple[str, ...],
    np.ndarray,
]:
    required = tuple(sorted((item for item in domain.families if item.required), key=lambda item: item.family_id))
    cached_domain = neighborhoods.domain(domain.label_domain_id)
    workers = max(1, min(int(inverse_workers), len(required) + 1))

    ooc_root = None if out_of_core_directory is None else Path(out_of_core_directory)
    if ooc_root is not None:
        ooc_root.mkdir(parents=True, exist_ok=True)
    ooc_admission_bytes = int(_MVIDX_OUT_OF_CORE_TASK_ADMISSION_BYTES)
    if resource_scope is not None and resource_scope.ram_budget_bytes is not None:
        budget = max(1, int(resource_scope.ram_budget_bytes))
        # Large inversions are I/O/memory-bandwidth heavy.  Reserve enough
        # anonymous scratch for at most eight simultaneous OOC transposes; the
        # deterministic queue may admit fewer when other work is resident.
        lane_budget = max(1, min(int(workers), 8))
        ooc_admission_bytes = min(
            ooc_admission_bytes,
            max(1, budget // lane_budget),
            budget,
        )
    ooc_chunk_scratch_bytes = max(8 * _MIB, min(
        int(_MVIDX_OUT_OF_CORE_CHUNK_SCRATCH_BYTES),
        max(1, ooc_admission_bytes // 2),
    ))
    ooc_chunk_scratch_bytes = min(ooc_chunk_scratch_bytes, max(1, ooc_admission_bytes))

    def build_family(position: int, family: Any) -> TargetCoverageSparseFamilyIndex:
        cached_family = cached_domain.family(family.family_id)
        use_ooc = _family_uses_out_of_core_inverse(
            cached_family, out_of_core_directory=ooc_root
        )
        output_path = None
        if use_ooc:
            output_path = ooc_root / (
                f"domain-{domain.label_domain_id}-family-{position:04d}-"
                f"{family.content_digest[:16]}-candidate-witnesses.npy"
            )
        return _build_family_sparse_index_from_neighborhood(
            family,
            cached_family,
            candidate_count=len(domain.frame_uids),
            inverse_workers=1,
            inverse_output_path=output_path,
            inverse_chunk_scratch_bytes=ooc_chunk_scratch_bytes,
        )

    if workers == 1:
        family_indices = tuple(build_family(position, family) for position, family in enumerate(required))
        obligation_result = _build_obligation_sparse_index(domain, role_domain, inverse_workers=1)
        return (family_indices, *obligation_result)

    if resource_scope is None:
        scope = _mvidx_resource_scope(workers)
    else:
        if int(resource_scope.python_workers) < workers:
            raise TrainingDataInputError(
                "TARGET-DATA2C-MVIDX-REUSE1 resource scope has fewer Python workers than requested."
            )
        scope = StageResourceScope(
            stage_name=resource_scope.stage_name,
            cpu_threads_available=resource_scope.cpu_threads_available,
            cpu_threads_budget=resource_scope.cpu_threads_budget,
            python_workers=workers,
            structural_workers=1,
            tree_workers=1,
            blas_threads=1,
            pytorch_cpu_workers=1,
            gpu_jobs=resource_scope.gpu_jobs,
            ram_budget_bytes=resource_scope.ram_budget_bytes,
        )
    results: dict[tuple[str, str], Any] = {}
    with DeterministicWorkQueue(
        scope,
        max_ready_tasks=max(1, 2 * workers),
        max_inflight_tasks=max(1, 2 * workers),
        max_completed_tasks=max(1, 2 * workers),
        heartbeat_interval_seconds=30.0,
        thread_name_prefix="mdstats-mvidx-reuse1",
    ) as queue:
        expected = len(required) + 1
        total_edges = sum(
            int(cached_domain.family(family.family_id).edge_count) for family in required
        )
        completed_edges = 0
        started = time.monotonic()
        last_report = started
        tracker = ProgressRateTracker(
            completed=0,
            started_at=started,
            minimum_recent_window_seconds=max(1.0, float(progress_interval_seconds)),
        )

        def consume_completion(completion: Any) -> None:
            nonlocal completed_edges
            if completion.canonical_order[0] == 0:
                family = required[int(completion.canonical_order[1])]
                results[("family", family.family_id)] = completion.value
                completed_edges += int(cached_domain.family(family.family_id).edge_count)
            else:
                results[("obligations", "0")] = completion.value

        def submit_family(position: int) -> None:
            family = required[position]
            cached_family = cached_domain.family(family.family_id)
            use_ooc = _family_uses_out_of_core_inverse(
                cached_family, out_of_core_directory=ooc_root
            )
            queue.submit(
                task_id=f"family-{position:06d}-{family.family_id}",
                canonical_order=(0, position),
                function=build_family,
                args=(position, family),
                task_kind=("mvidx-family-inverse-ooc" if use_ooc else "mvidx-family-inverse"),
                estimated_memory_bytes=_family_build_memory_estimate(
                    cached_family,
                    out_of_core=use_ooc,
                    out_of_core_admission_bytes=ooc_admission_bytes,
                ),
                locality_key=f"{domain.label_domain_id}:{family.family_id}",
            )

        next_submit = 0
        obligation_submitted = False
        while queue.snapshot().finished_tasks < expected:
            # PARCORE1 queues are deliberately bounded.  Feed work only while
            # ready capacity exists, then drain completed work before refilling.
            # This keeps 100+ family MVIDX domains bounded without turning a
            # temporary producer/consumer imbalance into a fatal queue-full error.
            while next_submit < len(required) and queue.can_submit():
                submit_family(next_submit)
                next_submit += 1
            if next_submit >= len(required) and not obligation_submitted and queue.can_submit():
                queue.submit(
                    task_id="hard-obligations",
                    canonical_order=(1, 0),
                    function=_build_obligation_sparse_index,
                    args=(domain, role_domain),
                    kwargs={"inverse_workers": 1},
                    task_kind="mvidx-obligation-inverse",
                    estimated_memory_bytes=max(1, len(domain.frame_uids) * 32),
                    locality_key=f"{domain.label_domain_id}:obligations",
                )
                obligation_submitted = True

            queue.wait_for_completion(timeout=max(0.1, float(progress_interval_seconds)))
            for completion in queue.drain_completed():
                consume_completion(completion)
            now = time.monotonic()
            snapshot = queue.snapshot()
            if progress_callback is not None and (
                now - last_report >= float(progress_interval_seconds)
                or snapshot.finished_tasks >= expected
            ):
                timing = tracker.snapshot(
                    completed=min(completed_edges, total_edges), total=max(1, total_edges), now=now
                )
                progress_callback(
                    f"status=running; domain={domain.label_domain_id}; "
                    f"progress={format_progress_fraction(snapshot.finished_tasks, expected)}; "
                    f"{format_progress_timing_fields(elapsed_seconds=timing.elapsed_seconds, eta_seconds=timing.eta_seconds, recent_rate=timing.recent_rate, average_rate=timing.average_rate, rate_unit='edge/s')}; "
                    f"busy={snapshot.busy_workers}/{snapshot.allocated_workers}; "
                    f"ram-accounted={snapshot.inflight_memory_bytes + snapshot.completed_memory_bytes + snapshot.reserved_memory_bytes}; "
                    f"ram-budget={snapshot.memory_budget_bytes if snapshot.memory_budget_bytes is not None else 'unbounded'}"
                )
                last_report = now
        for completion in queue.drain_completed():
            consume_completion(completion)
        snapshot = queue.snapshot()
        if next_submit != len(required) or not obligation_submitted or queue.has_outstanding_work:
            raise RuntimeError(
                "MVIDX-REUSE1 bounded producer/consumer queue did not drain exactly."
            )

    family_indices = tuple(results[("family", family.family_id)] for family in required)
    obligation_result = results[("obligations", "0")]
    if progress_callback is not None:
        ooc_families = sum(
            _family_uses_out_of_core_inverse(
                cached_domain.family(family.family_id), out_of_core_directory=ooc_root
            )
            for family in required
        )
        progress_callback(
            f"status=complete; domain={domain.label_domain_id}; phase=MVIDX-REUSE1-sparse-inversion; "
            f"workers={workers}; max-busy={snapshot.max_busy_workers}; "
            f"families={len(required)}; out-of-core-families={ooc_families}; geometry=skipped"
        )
    return (family_indices, *obligation_result)

def build_target_coverage_sparse_index(
    target_coverage_reference: Any,
    target_data_role_freeze: Any,
    target_coverage_feasibility: Any,
    *,
    policy: TargetCoverageSparseIndexPolicy | None = None,
    exact_neighborhood_store: TargetCoverageExactNeighborhoodStore | None = None,
    query_workers: int = 1,
    query_block_size: int = 512,
    global_workers: int | None = None,
    resource_scope: StageResourceScope | None = None,
    out_of_core_directory: str | Path | None = None,
    progress_interval_seconds: float = 30.0,
    progress_callback: Callable[[str], None] | None = None,
) -> TargetCoverageSparseIndex:
    """Build exact TARGET-DATA2C-MVIDX1 sparse scientific evidence."""

    active = TargetCoverageSparseIndexPolicy() if policy is None else policy
    workers = int(query_workers)
    block = int(query_block_size)
    interval = float(progress_interval_seconds)
    requested_inverse_workers = int(workers if global_workers is None else global_workers)
    if requested_inverse_workers < 1:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVIDX1 global_workers must be positive when supplied."
        )
    inverse_workers = requested_inverse_workers
    if workers < 1 or block < 1 or interval <= 0.0:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVIDX1 query_workers/query_block_size/progress_interval_seconds must be positive."
        )
    validate_target_coverage_feasibility_authority(
        target_coverage_feasibility,
        target_coverage_reference=target_coverage_reference,
        target_data_role_freeze=target_data_role_freeze,
    )
    if target_coverage_reference.dataset_id != target_data_role_freeze.dataset_id:
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 dataset identity mismatch.")
    if target_coverage_reference.target_data_role_freeze_digest != target_data_role_freeze.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 TARGET-DATA2A lineage mismatch.")
    if target_coverage_feasibility.target_coverage_reference_digest != target_coverage_reference.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 FEAS1/reference lineage mismatch.")

    neighborhoods = exact_neighborhood_store
    if neighborhoods is None:
        outer_workers = max(1, int(workers if global_workers is None else global_workers))
        tree_workers = workers if outer_workers == 1 else 1
        if progress_callback is not None:
            progress_callback(
                f"status=cache-miss; phase=NEIGHBOR1-forward-CSR-rebuild; "
                f"global-workers={outer_workers}; tree-workers/task={tree_workers}"
            )
        neighborhoods = build_target_coverage_exact_neighborhood_store(
            target_coverage_reference,
            global_workers=outer_workers,
            query_workers=tree_workers,
            query_block_size=block,
            progress_interval_seconds=interval,
            progress_callback=(
                None if progress_callback is None else lambda message: progress_callback(f"NEIGHBOR1: {message}")
            ),
        )
    validate_target_coverage_exact_neighborhood_store(
        neighborhoods, target_coverage_reference=target_coverage_reference, verify_geometry=False
    )

    domains: list[TargetCoverageSparseDomainIndex] = []
    for domain in target_coverage_reference.domains:
        role_domain = target_data_role_freeze.domain(domain.label_domain_id)
        if set(domain.frame_uids) != set(role_domain.size_development_frame_uids):
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 coverage/role frame-domain mismatch.")
        required = tuple(sorted((item for item in domain.families if item.required), key=lambda item: item.family_id))
        if progress_callback is not None:
            edge_count = sum(
                neighborhoods.domain(domain.label_domain_id).family(family.family_id).edge_count
                for family in required
            )
            progress_callback(
                f"status=cache-hit; domain={domain.label_domain_id}; phase=NEIGHBOR1-forward-CSR; families={len(required)}; "
                f"edges={edge_count}; geometry=skipped; inverse-workers={inverse_workers}"
            )
        (
            family_indices,
            obligations,
            obligation_offsets,
            obligation_candidates,
            candidate_obligation_offsets,
            candidate_obligations,
            unit_ids,
            unit_codes,
        ) = _build_domain_sparse_components(
            domain,
            role_domain,
            neighborhoods,
            inverse_workers=inverse_workers,
            progress_callback=progress_callback,
            resource_scope=resource_scope,
            out_of_core_directory=out_of_core_directory,
            progress_interval_seconds=interval,
        )
        domains.append(
            TargetCoverageSparseDomainIndex(
                label_domain_id=domain.label_domain_id,
                frame_domain_digest=domain.frame_domain_digest,
                candidate_count=len(domain.frame_uids),
                families=tuple(family_indices),
                obligations=obligations,
                obligation_offsets=obligation_offsets,
                obligation_candidates=obligation_candidates,
                candidate_obligation_offsets=candidate_obligation_offsets,
                candidate_obligations=candidate_obligations,
                correlation_unit_ids=unit_ids,
                candidate_correlation_unit_codes=unit_codes,
            )
        )
    return TargetCoverageSparseIndex(
        dataset_id=target_coverage_reference.dataset_id,
        target_coverage_reference_digest=target_coverage_reference.content_digest,
        target_data_role_freeze_digest=target_data_role_freeze.content_digest,
        target_coverage_feasibility_digest=target_coverage_feasibility.content_digest,
        policy=active,
        domains=tuple(domains),
    )


def _expected_inverse(
    offsets: np.ndarray,
    columns: np.ndarray,
    *,
    row_count: int,
    column_count: int,
) -> tuple[np.ndarray, np.ndarray]:
    return _csr_inverse(offsets, columns, row_count=row_count, column_count=column_count)


def validate_target_coverage_sparse_index_authority(
    index: TargetCoverageSparseIndex,
    *,
    target_coverage_reference: Any,
    target_data_role_freeze: Any,
    target_coverage_feasibility: Any,
    policy: TargetCoverageSparseIndexPolicy | None = None,
    verify_geometry: bool = False,
    query_workers: int = 1,
    query_block_size: int = 512,
) -> None:
    """Validate lineage and exact sparse invariants.

    ``verify_geometry=True`` rebuilds exact family neighborhoods and is intended
    for qualification/sampled-production checks.  Ordinary restart validation
    trusts content-addressed arrays bound to the unchanged TARGET-DATA2B family
    digests and verifies forward/inverse consistency without repeating KD-tree
    work.
    """

    active = TargetCoverageSparseIndexPolicy() if policy is None else policy
    if index.dataset_id != target_coverage_reference.dataset_id or index.dataset_id != target_data_role_freeze.dataset_id:
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 dataset identity mismatch.")
    if index.target_coverage_reference_digest != target_coverage_reference.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 reference digest mismatch.")
    if index.target_data_role_freeze_digest != target_data_role_freeze.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 role-freeze digest mismatch.")
    if index.target_coverage_feasibility_digest != target_coverage_feasibility.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 FEAS1 digest mismatch.")
    if index.policy.policy_digest != active.policy_digest:
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 policy digest mismatch.")
    validate_target_coverage_feasibility_authority(
        target_coverage_feasibility,
        target_coverage_reference=target_coverage_reference,
        target_data_role_freeze=target_data_role_freeze,
    )
    expected_ids = tuple(sorted(item.label_domain_id for item in target_coverage_reference.domains))
    if tuple(item.label_domain_id for item in index.domains) != expected_ids:
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 domain identities changed.")

    rebuilt_neighborhoods = None
    if verify_geometry:
        outer_workers = max(1, int(query_workers))
        rebuilt_neighborhoods = build_target_coverage_exact_neighborhood_store(
            target_coverage_reference,
            global_workers=outer_workers,
            query_workers=(max(1, int(query_workers)) if outer_workers == 1 else 1),
            query_block_size=max(1, int(query_block_size)),
        )

    for domain_index in index.domains:
        reference_domain = target_coverage_reference.domain(domain_index.label_domain_id)
        role_domain = target_data_role_freeze.domain(domain_index.label_domain_id)
        if domain_index.frame_domain_digest != reference_domain.frame_domain_digest:
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 frame-domain digest mismatch.")
        required = tuple(sorted((item for item in reference_domain.families if item.required), key=lambda item: item.family_id))
        if tuple(item.family_id for item in domain_index.families) != tuple(item.family_id for item in required):
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 required-family identities changed.")
        for family_index, family in zip(domain_index.families, required, strict=True):
            if family_index.family_digest != family.content_digest:
                raise TrainingDataInputError(f"TARGET-DATA2C-MVIDX1 family digest mismatch for {family.family_id!r}.")
            offsets, witnesses = _expected_inverse(
                family_index.witness_offsets,
                family_index.witness_candidates,
                row_count=family_index.witness_count,
                column_count=family_index.candidate_count,
            )
            if not np.array_equal(offsets, family_index.candidate_offsets) or not np.array_equal(witnesses, family_index.candidate_witnesses):
                raise TrainingDataInputError(f"TARGET-DATA2C-MVIDX1 forward/inverse adjacency mismatch for {family.family_id!r}.")
            if verify_geometry:
                assert rebuilt_neighborhoods is not None
                rebuilt = rebuilt_neighborhoods.domain(domain_index.label_domain_id).family(family.family_id)
                if (
                    not np.array_equal(rebuilt.witness_offsets, family_index.witness_offsets)
                    or not np.array_equal(rebuilt.witness_candidates, family_index.witness_candidates)
                ):
                    raise TrainingDataInputError(
                        f"TARGET-DATA2C-MVIDX1 geometric adjacency mismatch for {family.family_id!r}."
                    )

        (
            obligations,
            obligation_offsets,
            obligation_candidates,
            candidate_obligation_offsets,
            candidate_obligations,
            unit_ids,
            unit_codes,
        ) = _build_obligation_sparse_index(reference_domain, role_domain)
        if [item.to_dict() for item in obligations] != [item.to_dict() for item in domain_index.obligations]:
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 hard-obligation metadata mismatch.")
        for expected, actual, name in (
            (obligation_offsets, domain_index.obligation_offsets, "obligation_offsets"),
            (obligation_candidates, domain_index.obligation_candidates, "obligation_candidates"),
            (candidate_obligation_offsets, domain_index.candidate_obligation_offsets, "candidate_obligation_offsets"),
            (candidate_obligations, domain_index.candidate_obligations, "candidate_obligations"),
            (unit_codes, domain_index.candidate_correlation_unit_codes, "candidate_correlation_unit_codes"),
        ):
            if not np.array_equal(expected, actual):
                raise TrainingDataInputError(f"TARGET-DATA2C-MVIDX1 {name} mismatch.")
        if unit_ids != domain_index.correlation_unit_ids:
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 correlation-unit identity mismatch.")


def indexed_family_covered_mask(
    family_index: TargetCoverageSparseFamilyIndex,
    selected_candidate_indices: Sequence[int],
) -> np.ndarray:
    selected = np.asarray(tuple(int(v) for v in selected_candidate_indices), dtype=np.int64)
    if selected.size and (np.any(selected < 0) or np.any(selected >= family_index.candidate_count)):
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 selected candidate index is outside the domain.")
    if selected.size != np.unique(selected).size:
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 selected candidate indices must be unique.")
    covered = np.zeros(family_index.witness_count, dtype=np.bool_)
    if selected.size:
        witnesses, _ = csr_gather_rows(
            family_index.candidate_offsets, family_index.candidate_witnesses, selected
        )
        covered[np.asarray(witnesses, dtype=np.int64)] = True
    return covered


def indexed_family_covered_mass(
    family_index: TargetCoverageSparseFamilyIndex,
    witness_weights: Sequence[float] | np.ndarray,
    selected_candidate_indices: Sequence[int],
) -> float:
    weights = np.asarray(witness_weights, dtype=np.float64)
    if weights.shape != (family_index.witness_count,) or np.any(~np.isfinite(weights)) or np.any(weights < 0.0):
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 witness weights are invalid.")
    covered = indexed_family_covered_mask(family_index, selected_candidate_indices)
    return float(np.sum(weights[covered], dtype=np.float64))


def indexed_family_marginal_gain(
    family_index: TargetCoverageSparseFamilyIndex,
    witness_weights: Sequence[float] | np.ndarray,
    covered_witness_mask: Sequence[bool] | np.ndarray,
    candidate_index: int,
) -> float:
    weights = np.asarray(witness_weights, dtype=np.float64)
    covered = np.asarray(covered_witness_mask, dtype=np.bool_)
    if weights.shape != (family_index.witness_count,) or covered.shape != (family_index.witness_count,):
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 marginal-gain inputs are misaligned.")
    witnesses = family_index.candidate_witness_indices(int(candidate_index))
    return float(np.sum(weights[witnesses][~covered[witnesses]], dtype=np.float64))


def indexed_obligation_selected_counts(
    domain_index: TargetCoverageSparseDomainIndex,
    selected_candidate_indices: Sequence[int],
) -> np.ndarray:
    selected = np.asarray(tuple(int(v) for v in selected_candidate_indices), dtype=np.int64)
    if selected.size and (np.any(selected < 0) or np.any(selected >= domain_index.candidate_count)):
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 selected candidate index is outside the domain.")
    if selected.size != np.unique(selected).size:
        raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 selected candidate indices must be unique.")
    if not selected.size:
        return np.zeros(len(domain_index.obligations), dtype=np.int64)
    obligation_indices, _ = csr_gather_rows(
        domain_index.candidate_obligation_offsets, domain_index.candidate_obligations, selected
    )
    return np.bincount(
        np.asarray(obligation_indices, dtype=np.int64),
        minlength=len(domain_index.obligations),
    ).astype(np.int64, copy=False)
