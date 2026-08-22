"""Quota-interleaved deterministic training selection for MLFF-DATA7."""

from __future__ import annotations

from dataclasses import dataclass, field
import heapq
from typing import Any, Mapping, Sequence

import numpy as np

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .feature_metric import FittedFeatureMetric, FeatureFitDomain
from .material_profiles import focus_atomic_numbers

SELECTION_BUDGET_POLICY_SCHEMA = "mdstats.selection-budget-policy.v1"
SELECTION_MASTER_ENTRY_SCHEMA = "mdstats.selection-master-entry.v1"
SELECTION_LADDER_LEVEL_SCHEMA = "mdstats.selection-ladder-level.v1"
TRAINING_SELECTION_PLAN_SCHEMA = "mdstats.training-selection-plan.v1"
SELECTION_COVERAGE_LEVEL_SCHEMA = "mdstats.selection-coverage-level.v2"
SELECTION_COVERAGE_REPORT_SCHEMA = "mdstats.selection-coverage-report.v1"
SELECTION_BUDGET_POLICY_VERSION = "mdstats.mlff-data7.selection-budget.2026-07.v1"

_CATEGORIES = ("representative", "species_environment", "rare_event", "metric_fps", "difficulty")


@dataclass(frozen=True, slots=True)
class SelectionBudgetPolicy:
    target_sizes: tuple[int, ...]
    representative_fraction: float = 0.35
    species_environment_fraction: float = 0.25
    rare_event_fraction: float = 0.15
    metric_fps_fraction: float = 0.15
    difficulty_fraction: float = 0.10
    fps_tie_tolerance: float = 1.0e-12
    policy_version: str = SELECTION_BUDGET_POLICY_VERSION

    def __post_init__(self) -> None:
        sizes = tuple(int(v) for v in self.target_sizes)
        if not sizes or any(v <= 0 for v in sizes) or any(b <= a for a, b in zip(sizes, sizes[1:])):
            raise TrainingDataInputError("Selection target sizes must be positive and strictly increasing.")
        fractions = tuple(float(getattr(self, f"{name}_fraction")) for name in _CATEGORIES)
        if any(not np.isfinite(v) or v < 0.0 for v in fractions) or sum(fractions) <= 0.0:
            raise TrainingDataInputError("Selection category fractions are invalid.")
        total = sum(fractions)
        for name, value in zip(_CATEGORIES, fractions, strict=True):
            object.__setattr__(self, f"{name}_fraction", value / total)
        if not np.isfinite(self.fps_tie_tolerance) or self.fps_tie_tolerance <= 0.0:
            raise TrainingDataInputError("fps_tie_tolerance must be positive and finite.")
        object.__setattr__(self, "target_sizes", sizes)

    @property
    def fractions(self) -> dict[str, float]:
        return {name: float(getattr(self, f"{name}_fraction")) for name in _CATEGORIES}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SELECTION_BUDGET_POLICY_SCHEMA, "policy_version": self.policy_version,
            "target_sizes": list(self.target_sizes), **{f"{name}_fraction": self.fractions[name] for name in _CATEGORIES},
            "fps_tie_tolerance": self.fps_tie_tolerance,
        }

    @property
    def policy_digest(self) -> str: return digest(self._payload())
    def to_dict(self) -> dict[str, Any]: return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SelectionBudgetPolicy":
        if payload.get("schema") != SELECTION_BUDGET_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported selection-budget policy schema.")
        result = cls(
            target_sizes=tuple(int(v) for v in payload["target_sizes"]),
            representative_fraction=float(payload["representative_fraction"]),
            species_environment_fraction=float(payload["species_environment_fraction"]),
            rare_event_fraction=float(payload["rare_event_fraction"]),
            metric_fps_fraction=float(payload["metric_fps_fraction"]),
            difficulty_fraction=float(payload["difficulty_fraction"]),
            fps_tie_tolerance=float(payload["fps_tie_tolerance"]), policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Selection-budget policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class SelectionMasterEntry:
    rank: int
    frame_uid: str
    primary_reason: str
    reason_codes: tuple[str, ...]
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.rank < 0: raise TrainingDataInputError("Selection rank must be nonnegative.")
        object.__setattr__(self, "frame_uid", validate_digest(self.frame_uid, name="frame_uid"))
        if not self.primary_reason.strip(): raise TrainingDataInputError("Selection reason must be non-empty.")
        object.__setattr__(self, "reason_codes", tuple(sorted(set((self.primary_reason, *(str(v) for v in self.reason_codes))))))

    def to_dict(self) -> dict[str, Any]:
        payload = {"schema": SELECTION_MASTER_ENTRY_SCHEMA, "rank": self.rank, "frame_uid": self.frame_uid, "primary_reason": self.primary_reason, "reason_codes": list(self.reason_codes)}
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SelectionMasterEntry":
        if payload.get("schema") != SELECTION_MASTER_ENTRY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported selection-master-entry schema.")
        result = cls(rank=int(payload["rank"]), frame_uid=str(payload["frame_uid"]), primary_reason=str(payload["primary_reason"]), reason_codes=tuple(str(v) for v in payload["reason_codes"]))
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]): raise TrainingDataSerializationError("Selection-master-entry digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class SelectionLadderLevel:
    target_size: int
    frame_uids: tuple[str, ...]
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        frames = tuple(validate_digest(v, name="frame_uid") for v in self.frame_uids)
        if self.target_size != len(frames) or len(set(frames)) != len(frames):
            raise TrainingDataInputError("Selection ladder level size is inconsistent.")
        object.__setattr__(self, "frame_uids", frames)

    def to_dict(self) -> dict[str, Any]:
        payload = {"schema": SELECTION_LADDER_LEVEL_SCHEMA, "target_size": self.target_size, "frame_uids": list(self.frame_uids)}
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SelectionLadderLevel":
        if payload.get("schema") != SELECTION_LADDER_LEVEL_SCHEMA: raise TrainingDataSerializationError("Unsupported selection-ladder schema.")
        result = cls(target_size=int(payload["target_size"]), frame_uids=tuple(str(v) for v in payload["frame_uids"]))
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]): raise TrainingDataSerializationError("Selection-ladder digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TrainingSelectionPlan:
    domain: FeatureFitDomain
    metric_digest: str
    data4_bundle_digest: str
    data6_bundle_digest: str
    policy: SelectionBudgetPolicy
    mandatory_anchor_count: int
    master_order: tuple[SelectionMasterEntry, ...]
    ladder_levels: tuple[SelectionLadderLevel, ...]
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("metric_digest", "data4_bundle_digest", "data6_bundle_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        order = tuple(self.master_order); levels = tuple(self.ladder_levels)
        if tuple(item.rank for item in order) != tuple(range(len(order))) or len({item.frame_uid for item in order}) != len(order):
            raise TrainingDataInputError("Selection master order must have contiguous ranks and unique frames.")
        if self.mandatory_anchor_count < 0 or self.mandatory_anchor_count > len(order): raise TrainingDataInputError("Mandatory anchor count is invalid.")
        if tuple(item.target_size for item in levels) != self.policy.target_sizes: raise TrainingDataInputError("Selection ladder does not match target sizes.")
        for level in levels:
            if level.frame_uids != tuple(item.frame_uid for item in order[: level.target_size]):
                raise TrainingDataInputError("Selection ladder levels must be strict master-order prefixes.")
        object.__setattr__(self, "master_order", order); object.__setattr__(self, "ladder_levels", levels)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_SELECTION_PLAN_SCHEMA, "domain": self.domain.to_dict(), "metric_digest": self.metric_digest,
            "data4_bundle_digest": self.data4_bundle_digest, "data6_bundle_digest": self.data6_bundle_digest,
            "policy": self.policy.to_dict(), "mandatory_anchor_count": self.mandatory_anchor_count,
            "master_order": [item.to_dict() for item in self.master_order], "ladder_levels": [item.to_dict() for item in self.ladder_levels],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached
    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingSelectionPlan":
        if payload.get("schema") != TRAINING_SELECTION_PLAN_SCHEMA: raise TrainingDataSerializationError("Unsupported training-selection-plan schema.")
        result = cls(
            domain=FeatureFitDomain.from_dict(payload["domain"]), metric_digest=str(payload["metric_digest"]),
            data4_bundle_digest=str(payload["data4_bundle_digest"]), data6_bundle_digest=str(payload["data6_bundle_digest"]),
            policy=SelectionBudgetPolicy.from_dict(payload["policy"]), mandatory_anchor_count=int(payload["mandatory_anchor_count"]),
            master_order=tuple(SelectionMasterEntry.from_dict(item) for item in payload["master_order"]),
            ladder_levels=tuple(SelectionLadderLevel.from_dict(item) for item in payload["ladder_levels"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest): raise TrainingDataSerializationError("Training-selection-plan digest mismatch.")
        return result


def _scaled_feature_matrix(
    vectors: np.ndarray,
    missing: np.ndarray | None = None,
) -> np.ndarray:
    """Robustly scale a dense feature matrix for deterministic maximin selection."""

    X = np.asarray(vectors, dtype=np.float64)
    if X.ndim != 2 or X.shape[0] == 0:
        raise TrainingDataInputError("Selection feature matrix must be non-empty and two-dimensional.")
    absent = np.zeros(X.shape, dtype=np.bool_) if missing is None else np.asarray(missing, dtype=np.bool_)
    if absent.shape != X.shape:
        raise TrainingDataInputError("Selection feature and missing-mask shapes disagree.")
    # Compute all robust column statistics in compiled NumPy kernels.  The
    # former Python loop performed three filtered allocations and percentile
    # passes per column; group-aware selection may call this for hundreds of
    # columns across several structural groups.
    observed = np.where(absent, np.nan, X)
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        with np.errstate(invalid="ignore"):
            center = np.nanmedian(observed, axis=0)
            quartiles = np.nanpercentile(observed, (25.0, 75.0), axis=0)
    center = np.where(np.isfinite(center), center, 0.0)
    width = quartiles[1] - quartiles[0]
    scale = np.where(np.isfinite(width) & (width > 1.0e-12), width, 1.0)
    return (np.where(absent, center[None, :], X) - center[None, :]) / scale[None, :]


def _update_min_squared_distances(
    X: np.ndarray,
    selected: np.ndarray,
    current: np.ndarray,
    *,
    memory_budget_bytes: int = 64 * 1024 * 1024,
) -> None:
    """Update nearest-selected squared distances with bounded temporary memory."""

    if selected.size == 0:
        return
    Y = np.asarray(selected, dtype=np.float64)
    if Y.ndim == 1:
        Y = Y[None, :]
    if Y.ndim != 2 or Y.shape[1] != X.shape[1]:
        raise TrainingDataInputError("Maximin update vectors have inconsistent dimensions.")
    y_norm = np.einsum("ij,ij->i", Y, Y)
    bytes_per_row = max(8, 8 * Y.shape[0])
    rows = max(1, min(X.shape[0], memory_budget_bytes // bytes_per_row))
    for first in range(0, X.shape[0], rows):
        last = min(X.shape[0], first + rows)
        block = X[first:last]
        distances = (
            np.einsum("ij,ij->i", block, block)[:, None]
            + y_norm[None, :]
            - 2.0 * (block @ Y.T)
        )
        np.maximum(distances, 0.0, out=distances)
        current[first:last] = np.minimum(current[first:last], np.min(distances, axis=1))


def _update_min_squared_distances_precomputed(
    X: np.ndarray,
    row_norm_squared: np.ndarray,
    selected: np.ndarray,
    selected_norm_squared: np.ndarray,
    current: np.ndarray,
    *,
    memory_budget_bytes: int = 64 * 1024 * 1024,
) -> None:
    """Update nearest-selected squared distances using immutable row norms.

    PERF-P1 keeps the selector matrix immutable and computes its row norms once.
    This helper preserves the existing FP64 distance expression while avoiding
    the repeated ``einsum`` over every candidate row at every FPS iteration.
    """

    if selected.size == 0:
        return
    Y = np.asarray(selected, dtype=np.float64)
    if Y.ndim == 1:
        Y = Y[None, :]
    if Y.ndim != 2 or Y.shape[1] != X.shape[1]:
        raise TrainingDataInputError("Maximin update vectors have inconsistent dimensions.")
    x_norm = np.asarray(row_norm_squared, dtype=np.float64)
    y_norm = np.asarray(selected_norm_squared, dtype=np.float64).reshape(-1)
    if x_norm.shape != (X.shape[0],) or y_norm.shape != (Y.shape[0],):
        raise TrainingDataInputError("Maximin row-norm workspace is misaligned.")
    bytes_per_row = max(8, 8 * Y.shape[0])
    rows = max(1, min(X.shape[0], int(memory_budget_bytes) // bytes_per_row))
    for first in range(0, X.shape[0], rows):
        last = min(X.shape[0], first + rows)
        distances = (
            x_norm[first:last, None]
            + y_norm[None, :]
            - 2.0 * (X[first:last] @ Y.T)
        )
        np.maximum(distances, 0.0, out=distances)
        current[first:last] = np.minimum(current[first:last], np.min(distances, axis=1))


def _centroid_squared_distances_bounded(
    X: np.ndarray,
    centroid: np.ndarray,
    *,
    memory_budget_bytes: int = 64 * 1024 * 1024,
) -> np.ndarray:
    """Return exact current-path centroid distances without a full ``X-c`` copy.

    The algebraically equivalent row-norm/matvec form can perturb last-bit
    rounding on some BLAS implementations.  PERF-P1 therefore preserves the
    established subtraction-plus-``einsum`` numerical authority in bounded row
    blocks while removing the full-width temporary matrix.
    """

    values = np.asarray(X, dtype=np.float64)
    center = np.asarray(centroid, dtype=np.float64)
    if values.ndim != 2 or center.shape != (values.shape[1],):
        raise TrainingDataInputError("Centroid distance workspace is misaligned.")
    result = np.empty(values.shape[0], dtype=np.float64)
    bytes_per_row = max(8, 8 * values.shape[1])
    rows = max(1, min(values.shape[0], int(memory_budget_bytes) // bytes_per_row))
    for first in range(0, values.shape[0], rows):
        last = min(values.shape[0], first + rows)
        delta = values[first:last] - center[None, :]
        result[first:last] = np.einsum("ij,ij->i", delta, delta)
    return result


@dataclass(slots=True)
class ExactFPSState:
    """Mutable execution workspace for deterministic exact FP64 FPS.

    The selector matrix and row norms are immutable during a run.  Only the
    selected masks/ranks, nearest-selected distances, and selected order evolve.
    The class is an execution helper: none of its storage choices enter a
    scientific record or content digest.
    """

    frame_uids: tuple[str, ...]
    matrix: np.ndarray
    tolerance: float
    row_norm_squared: np.ndarray
    lexical_uid_rank: np.ndarray
    selected_mask: np.ndarray
    selected_rank: np.ndarray
    min_squared_distance: np.ndarray
    selected_order: list[int]

    @classmethod
    def from_matrix(
        cls,
        frame_uids: Sequence[str],
        matrix: np.ndarray,
        tolerance: float,
    ) -> "ExactFPSState":
        uids = tuple(str(uid) for uid in frame_uids)
        X = np.asarray(matrix, dtype=np.float64)
        tol = float(tolerance)
        if X.ndim != 2 or X.shape[0] != len(uids) or np.any(~np.isfinite(X)):
            raise TrainingDataInputError(
                "Farthest-point selection requires one finite feature row per frame."
            )
        if not np.isfinite(tol) or tol <= 0.0:
            raise TrainingDataInputError("Farthest-point tie tolerance must be positive and finite.")
        row_norm = np.einsum("ij,ij->i", X, X)
        lexical_order = np.argsort(np.asarray(uids, dtype=str), kind="stable")
        lexical_rank = np.empty(len(uids), dtype=np.int64)
        lexical_rank[lexical_order] = np.arange(len(uids), dtype=np.int64)
        return cls(
            frame_uids=uids,
            matrix=X,
            tolerance=tol,
            row_norm_squared=row_norm,
            lexical_uid_rank=lexical_rank,
            selected_mask=np.zeros(len(uids), dtype=np.bool_),
            selected_rank=np.full(len(uids), -1, dtype=np.int64),
            min_squared_distance=np.full(len(uids), np.inf, dtype=np.float64),
            selected_order=[],
        )

    def seed_indices(self, indices: Sequence[int]) -> None:
        """Seed an existing deterministic prefix and initialize FPS distance state."""

        unique: list[int] = []
        seen: set[int] = set()
        for raw in indices:
            index = int(raw)
            if index < 0 or index >= len(self.frame_uids):
                raise TrainingDataInputError("Farthest-point seed index is out of range.")
            if index not in seen:
                seen.add(index)
                unique.append(index)
        if not unique:
            return
        if self.selected_order:
            raise TrainingDataInputError("ExactFPSState can only be seeded while empty.")
        rows = np.asarray(unique, dtype=np.int64)
        self.selected_mask[rows] = True
        self.selected_rank[rows] = np.arange(len(rows), dtype=np.int64)
        self.selected_order.extend(unique)
        _update_min_squared_distances_precomputed(
            self.matrix,
            self.row_norm_squared,
            self.matrix[rows],
            self.row_norm_squared[rows],
            self.min_squared_distance,
        )
        self.min_squared_distance[self.selected_mask] = 0.0

    def append_index(self, index: int) -> None:
        """Append one unselected row and update the persistent nearest state."""

        row = int(index)
        if row < 0 or row >= len(self.frame_uids):
            raise TrainingDataInputError("Farthest-point selected index is out of range.")
        if self.selected_mask[row]:
            raise TrainingDataInputError("Farthest-point selection attempted to reuse a selected row.")
        self.selected_mask[row] = True
        self.selected_rank[row] = len(self.selected_order)
        self.selected_order.append(row)
        _update_min_squared_distances_precomputed(
            self.matrix,
            self.row_norm_squared,
            self.matrix[row],
            self.row_norm_squared[row : row + 1],
            self.min_squared_distance,
        )
        self.min_squared_distance[self.selected_mask] = 0.0

    def _lexical_first(self, indices: np.ndarray) -> int:
        if indices.size == 0:
            raise TrainingDataInputError("Farthest-point tie set is unexpectedly empty.")
        ranks = self.lexical_uid_rank[indices]
        return int(indices[int(np.argmin(ranks))])

    def append_centroid_seed(self) -> int:
        """Append the current deterministic centroid-farthest seed."""

        if self.selected_order:
            raise TrainingDataInputError("Centroid FPS seeding is only valid for an empty state.")
        centroid = np.mean(self.matrix, axis=0)
        squared = _centroid_squared_distances_bounded(self.matrix, centroid)
        scores = np.sqrt(squared)
        best_score = float(np.max(scores))
        tied = np.flatnonzero(np.abs(scores - best_score) <= self.tolerance)
        best = self._lexical_first(tied)
        self.append_index(best)
        return best

    def continue_fps(self, additional_limit: int) -> list[int]:
        """Append up to ``additional_limit`` exact FPS rows and return their indices."""

        requested = max(0, int(additional_limit))
        start = len(self.selected_order)
        capacity = len(self.frame_uids) - start
        requested = min(requested, capacity)
        if requested == 0:
            return []
        if not self.selected_order:
            self.append_centroid_seed()
        while len(self.selected_order) - start < requested and np.any(~self.selected_mask):
            available = np.flatnonzero(~self.selected_mask)
            scores = np.sqrt(self.min_squared_distance[available])
            best_score = float(np.max(scores))
            tied = available[np.abs(scores - best_score) <= self.tolerance]
            self.append_index(self._lexical_first(tied))
        return list(self.selected_order[start : start + requested])


def _fps_order(
    frame_uids: Sequence[str],
    vector_by_uid: Mapping[str, np.ndarray],
    initial: Sequence[str],
    tolerance: float,
    *,
    limit: int | None = None,
) -> list[str]:
    """Return a bounded exact farthest-point queue in ``O(N K d)`` time.

    The former implementation recomputed the distance from every remaining
    candidate to every selected point at every iteration, yielding cubic
    growth when a full 36k-frame ordering was constructed.  Incremental
    nearest-distance updates preserve exact maximin semantics while the queue
    is bounded to the largest requested selection ladder.
    """

    uids = tuple(dict.fromkeys(str(uid) for uid in frame_uids))
    if not uids:
        return []
    target = len(uids) if limit is None else min(max(0, int(limit)), len(uids))
    if target == 0:
        return []
    try:
        X = np.vstack([np.asarray(vector_by_uid[uid], dtype=np.float64) for uid in uids])
    except KeyError as exc:
        raise TrainingDataInputError(f"Missing fitted feature vector for frame {exc.args[0]!r}.") from exc
    if X.ndim != 2 or np.any(~np.isfinite(X)):
        raise TrainingDataInputError("Farthest-point selection requires finite two-dimensional features.")
    return _fps_order_matrix(
        uids,
        X,
        initial,
        tolerance,
        limit=target,
    )


def _fps_order_matrix(
    frame_uids: Sequence[str],
    matrix: np.ndarray,
    initial: Sequence[str],
    tolerance: float,
    *,
    limit: int | None = None,
) -> list[str]:
    """Bounded exact FPS over an already assembled frame matrix.

    DATA7 already owns a dense transformed-feature table.  Accepting that
    matrix directly avoids rebuilding a UID-to-vector dictionary and another
    ``vstack`` copy before the O(N K d) selection kernel.
    """

    uids = tuple(str(uid) for uid in frame_uids)
    X = np.asarray(matrix, dtype=np.float64)
    target = len(uids) if limit is None else min(max(0, int(limit)), len(uids))
    if target == 0:
        return []
    uid_to_index = {uid: index for index, uid in enumerate(uids)}
    initial_indices = [uid_to_index[uid] for uid in dict.fromkeys(initial) if uid in uid_to_index]
    state = ExactFPSState.from_matrix(uids, X, tolerance)
    state.seed_indices(initial_indices)
    return [uids[index] for index in state.continue_fps(target)]


def _environment_fps_frames(environments: list[Any], *, limit: int) -> list[str]:
    """Select environment-diverse frames from frame-level environment summaries.

    Selection ultimately chooses frames, not atoms.  The previous routine ran
    farthest-point sampling over every atom and continued until every atomic
    environment had been ordered, which can be millions of candidates.  This
    implementation aggregates the available atomic environments once per frame
    (mean and standard deviation after robust imputation) and then runs bounded
    exact FPS over at most one vector per frame.
    """

    if not environments or limit <= 0:
        return []
    by_frame: dict[str, list[Any]] = {}
    for item in environments:
        by_frame.setdefault(item.frame_uid, []).append(item)
    all_vectors = np.asarray([item.vector for item in environments], dtype=np.float64)
    all_missing = np.asarray([item.missing_mask for item in environments], dtype=np.bool_)
    scaled = _scaled_feature_matrix(all_vectors, all_missing)
    rows_by_frame: dict[str, list[int]] = {}
    for index, item in enumerate(environments):
        rows_by_frame.setdefault(item.frame_uid, []).append(index)
    uids = tuple(sorted(rows_by_frame))
    vectors: dict[str, np.ndarray] = {}
    for uid in uids:
        values = scaled[np.asarray(rows_by_frame[uid], dtype=np.int64)]
        vectors[uid] = np.concatenate((np.mean(values, axis=0), np.std(values, axis=0)))
    return _fps_order(uids, vectors, (), 1.0e-12, limit=limit)


def _frame_group_queue(
    catalog: Any,
    domain_frames: set[str],
    group_id: str,
    *,
    limit: int,
    selected_rows: np.ndarray | None = None,
    selected_columns: np.ndarray | None = None,
) -> list[str]:
    """Build a group-diversity queue directly from the columnar DATA6 table.

    Callers that evaluate several atom groups from the same catalog can pass
    preindexed rows/columns.  This avoids rescanning all ``N`` frame UIDs and
    all ``P`` feature names once per group (formerly ``O(G*(N+P))`` setup).
    """

    table = catalog.frame_descriptor_table
    if selected_columns is None:
        prefix = f"group:{group_id}:"
        selected_columns = np.fromiter(
            (
                index
                for index, name in enumerate(table.feature_names)
                if name.startswith(prefix)
            ),
            dtype=np.int64,
        )
    else:
        selected_columns = np.asarray(selected_columns, dtype=np.int64)
    if selected_columns.size == 0:
        return []
    if selected_rows is None:
        selected_rows = np.fromiter(
            (
                index
                for index, uid in enumerate(table.frame_uids)
                if uid in domain_frames
            ),
            dtype=np.int64,
        )
    else:
        selected_rows = np.asarray(selected_rows, dtype=np.int64)
    if selected_rows.size == 0:
        return []
    uids = tuple(table.frame_uids[int(index)] for index in selected_rows)
    values = np.asarray(
        table.values[np.ix_(selected_rows, selected_columns)], dtype=np.float64
    )
    masks = np.asarray(
        table.missing_mask[np.ix_(selected_rows, selected_columns)],
        dtype=np.bool_,
    )
    Z = _scaled_feature_matrix(values, masks)
    vector_by_uid = {uid: Z[index] for index, uid in enumerate(uids)}
    return _fps_order(uids, vector_by_uid, (), 1.0e-12, limit=limit)


def _atomic_species_queue(data6_bundle: Any, domain: FeatureFitDomain, *, limit: int) -> list[str]:
    domain_frames = set(domain.frame_uids)
    result: list[str] = []
    seen: set[str] = set()

    def extend(values: Sequence[str]) -> None:
        for uid in values:
            if uid not in seen:
                seen.add(uid)
                result.append(uid)
                if len(result) >= limit:
                    return

    priority_group_ids: tuple[str, ...] = ()
    plan = getattr(data6_bundle, "phase_geometry_profile_plan", None)
    if plan is not None:
        priority_group_ids = tuple(plan.priority_group_ids)
    for catalog in data6_bundle.universal_structural_features:
        table = catalog.frame_descriptor_table
        if not len(table):
            continue
        selected_rows = np.fromiter(
            (
                index
                for index, uid in enumerate(table.frame_uids)
                if uid in domain_frames
            ),
            dtype=np.int64,
        )
        columns_by_group: dict[str, list[int]] = {}
        for column, name in enumerate(table.feature_names):
            if not name.startswith("group:") or name.count(":") < 2:
                continue
            columns_by_group.setdefault(name.split(":", 2)[1], []).append(column)
        group_order = tuple(dict.fromkeys(
            (*priority_group_ids, *(
                group_id
                for group_id in sorted(columns_by_group)
                if group_id.startswith("element_Z")
            ))
        ))
        for group_id in group_order:
            extend(_frame_group_queue(
                catalog,
                domain_frames,
                group_id,
                limit=limit,
                selected_rows=selected_rows,
                selected_columns=np.asarray(columns_by_group.get(group_id, ()), dtype=np.int64),
            ))
            if len(result) >= limit:
                return result
    if result:
        return result

    profile_catalogs = tuple(getattr(data6_bundle, "profile_selection_features", ()))
    if not profile_catalogs and getattr(data6_bundle, "lta_selection_features", None) is not None:
        from .profile_extensions import wrap_lta_selection_features
        profile_catalogs = (wrap_lta_selection_features(
            data6_bundle.lta_selection_features, data4_bundle_digest=data6_bundle.data4_bundle_digest
        ),)
    environments_by_species: dict[int, list[Any]] = {}
    for extension in profile_catalogs:
        if extension.extension_id == "lta" and extension.stage.value == "selection":
            catalog = extension.as_lta_selection()
            for uid in sorted(domain_frames):
                for item in catalog.environments_for_frame(uid):
                    environments_by_species.setdefault(item.atomic_number, []).append(item)
        else:
            for item in extension.atomic_environment_descriptors():
                if item.frame_uid in domain_frames:
                    environments_by_species.setdefault(item.atomic_number, []).append(item)
    for atomic_number in sorted(environments_by_species):
        extend(_environment_fps_frames(
            environments_by_species[atomic_number],
            limit=limit,
        ))
        if len(result) >= limit:
            break
    return result


def _difficulty_queue(
    data4_bundle: Any,
    data6_bundle: Any,
    domain: FeatureFitDomain,
    *,
    limit: int,
) -> list[str]:
    catalog = data6_bundle.training_difficulty_for_domain(domain)
    if catalog is not None and tuple(catalog.domain.frame_uids) != tuple(domain.frame_uids):
        raise TrainingDataInputError("DATA6 difficulty-domain identity matches but frame membership differs.")
    if catalog is None or limit <= 0:
        return []
    available_species = tuple(sorted({
        error.atomic_number
        for item in catalog.records
        for error in item.species_force_errors
    }))
    focus_species = set(focus_atomic_numbers(
        getattr(data4_bundle, "material_profile_contracts", None), available_species
    ))

    def key(item: Any) -> tuple[float, str]:
        focus_error = max((
            value.component_rmse_ev_per_angstrom
            for value in item.species_force_errors
            if value.atomic_number in focus_species
        ), default=0.0)
        score = item.force_component_rmse_ev_per_angstrom + focus_error + item.absolute_energy_error_per_atom_ev
        return (-float(score), item.frame_uid)

    return [item.frame_uid for item in heapq.nsmallest(min(limit, len(catalog.records)), catalog.records, key=key)]


def _smallest_lexicographic_distance_indices(
    squared: np.ndarray,
    uids: Sequence[str],
    take: int,
) -> np.ndarray:
    """Return the exact ``lexsort((uid, squared))[:take]`` prefix efficiently.

    ``np.lexsort`` orders all candidates and costs ``O(N log N)`` even when
    only the first bounded selection ladder is needed.  Partitioning locates
    the boundary in expected ``O(N)`` work; only the retained prefix and any
    exact boundary ties are sorted.
    """

    values = np.asarray(squared, dtype=np.float64).reshape(-1)
    count = len(values)
    take = min(max(0, int(take)), count)
    if take == 0:
        return np.empty((0,), dtype=np.int64)
    uid_array = np.asarray(tuple(str(uid) for uid in uids), dtype=str)
    if uid_array.shape != (count,):
        raise TrainingDataInputError("Distance UID ordering is misaligned.")
    if take == count:
        return np.lexsort((uid_array, values)).astype(np.int64, copy=False)
    threshold = float(np.partition(values, take - 1)[take - 1])
    below = np.flatnonzero(values < threshold)
    tied = np.flatnonzero(values == threshold)
    needed = take - len(below)
    if needed < 0:
        # Defensive fallback for nonstandard floating comparisons.
        return np.lexsort((uid_array, values))[:take].astype(np.int64, copy=False)
    if needed:
        tied = tied[np.argsort(uid_array[tied], kind="stable")[:needed]]
        chosen = np.concatenate((below, tied))
    else:
        chosen = below
    order = np.lexsort((uid_array[chosen], values[chosen]))
    return chosen[order].astype(np.int64, copy=False)


def build_training_selection_plan(
    data4_bundle: Any, data5_bundle: Any, data6_bundle: Any, metric: FittedFeatureMetric,
    *, policy: SelectionBudgetPolicy,
) -> TrainingSelectionPlan:
    domain = metric.domain
    candidates = tuple(domain.frame_uids)
    selection_limit = policy.target_sizes[-1]
    if selection_limit > len(candidates):
        raise TrainingDataInputError("Largest selection size exceeds the training domain.")
    candidate_set = set(candidates)
    units = tuple(data5_bundle.unit_catalog.unit(unit_id) for unit_id in domain.unit_ids)
    unit_by_frame = {
        uid: unit
        for unit in units
        for uid in unit.frame_uids
    }
    by_condition: dict[str, list[str]] = {}
    for uid in candidates:
        by_condition.setdefault(unit_by_frame[uid].condition.condition_id, []).append(uid)
    mandatory = [min(values) for _, values in sorted(by_condition.items())]
    mandatory_set = set(mandatory)
    if policy.target_sizes[0] < len(mandatory):
        raise TrainingDataInputError("Smallest target size is below mandatory condition coverage.")
    feature_table = metric.frame_feature_table
    candidate_positions = np.fromiter(
        (feature_table.index_for_uid(uid) for uid in candidates),
        dtype=np.int64,
        count=len(candidates),
    )
    candidate_matrix = feature_table.values[candidate_positions]
    candidate_index_by_uid = {uid: index for index, uid in enumerate(candidates)}

    representative: list[str] = []
    representative_seen: set[str] = set()
    for _, values in sorted(by_condition.items()):
        local_indices = np.fromiter(
            (candidate_index_by_uid[uid] for uid in values),
            dtype=np.int64,
            count=len(values),
        )
        matrix = candidate_matrix[local_indices]
        centroid = np.mean(matrix, axis=0)
        take = min(selection_limit, len(values))
        delta = matrix - centroid
        squared = np.einsum("ij,ij->i", delta, delta)
        # ``heapq.nsmallest`` previously called ``np.linalg.norm`` once per
        # Python UID.  Compute all distances in one compiled pass and use a
        # deterministic lexicographic tie-break equivalent to (distance, UID).
        order = _smallest_lexicographic_distance_indices(squared, values, take)
        for local_index in order:
            uid = values[int(local_index)]
            if uid not in mandatory_set and uid not in representative_seen:
                representative_seen.add(uid)
                representative.append(uid)
                if len(representative) >= selection_limit:
                    break
        if len(representative) >= selection_limit:
            break

    species = _atomic_species_queue(data6_bundle, domain, limit=selection_limit)
    rare: list[str] = []
    rare_seen: set[str] = set()

    def add_rare(uid: str) -> None:
        if uid in candidate_set and uid not in rare_seen and len(rare) < selection_limit:
            rare_seen.add(uid)
            rare.append(uid)

    for event in data4_bundle.events.events:
        add_rare(event.anchor_frame_uid)
        for uid in event.protected_frame_uids:
            add_rare(uid)
    for catalog in data6_bundle.universal_structural_features:
        for event in catalog.events:
            add_rare(event.previous_frame_uid)
            add_rare(event.current_frame_uid)
    difficulty = _difficulty_queue(data4_bundle, data6_bundle, domain, limit=selection_limit)
    fps = _fps_order_matrix(
        candidates,
        candidate_matrix,
        mandatory,
        policy.fps_tie_tolerance,
        limit=selection_limit,
    )
    queues = {
        "representative": representative,
        "species_environment": species,
        "rare_event": rare,
        "metric_fps": fps,
        "difficulty": difficulty,
    }
    selected = list(mandatory)
    selected_set = set(mandatory)
    reasons = {uid: {"mandatory_condition_anchor"} for uid in mandatory}
    primary_by_uid = {uid: "mandatory_condition_anchor" for uid in mandatory}
    counts = {name: 0 for name in _CATEGORIES}
    cursors = {name: 0 for name in _CATEGORIES}
    fractions = policy.fractions
    fallback_iter = iter(sorted(candidate_set - selected_set))

    while len(selected) < selection_limit:
        available: list[tuple[float, str]] = []
        for name in _CATEGORIES:
            queue = queues[name]
            while cursors[name] < len(queue) and queue[cursors[name]] in selected_set:
                cursors[name] += 1
            if cursors[name] < len(queue):
                target = fractions[name] * max(1, len(selected) - len(mandatory) + 1)
                available.append((target - counts[name], name))
        if not available:
            fallback = next((uid for uid in fallback_iter if uid not in selected_set), None)
            if fallback is None:
                raise TrainingDataInputError("Selection queues exhausted before the requested ladder size.")
            selected.append(fallback)
            selected_set.add(fallback)
            reasons.setdefault(fallback, set()).add("stable_uid_fallback")
            primary_by_uid[fallback] = "stable_uid_fallback"
            continue
        best_deficit = max(value for value, _ in available)
        name = min(name for value, name in available if abs(value - best_deficit) <= 1.0e-12)
        uid = queues[name][cursors[name]]
        cursors[name] += 1
        if uid not in selected_set:
            selected.append(uid)
            selected_set.add(uid)
            counts[name] += 1
            reasons.setdefault(uid, set()).add(name)
            primary_by_uid[uid] = name

    category_membership = {name: set(queue) for name, queue in queues.items()}
    for uid in selected:
        for name, members in category_membership.items():
            if uid in members:
                reasons.setdefault(uid, set()).add(name)
    order = tuple(
        SelectionMasterEntry(
            rank=index,
            frame_uid=uid,
            primary_reason=primary_by_uid[uid],
            reason_codes=tuple(reasons[uid]),
        )
        for index, uid in enumerate(selected)
    )
    levels = tuple(SelectionLadderLevel(size, tuple(selected[:size])) for size in policy.target_sizes)
    return TrainingSelectionPlan(
        domain=domain, metric_digest=metric.content_digest, data4_bundle_digest=data4_bundle.content_digest,
        data6_bundle_digest=data6_bundle.content_digest, policy=policy, mandatory_anchor_count=len(mandatory),
        master_order=order, ladder_levels=levels,
    )


def build_prescribed_training_selection_plan(
    data4_bundle: Any,
    data6_bundle: Any,
    metric: FittedFeatureMetric,
    *,
    policy: SelectionBudgetPolicy,
    frame_uids: Sequence[str],
    authority_reason: str = "upstream_authenticated_prefix",
) -> TrainingSelectionPlan:
    """Build DATA7 selection from an authenticated upstream master prefix.

    This is intentionally narrower than :func:`build_training_selection_plan`: it
    performs no second ranking or qualification.  The caller owns the upstream
    order (REPAIR2 in the target-size v5 workflow), and DATA7 only authenticates
    that every requested ladder level is a strict prefix of that order and lies
    inside the final-development domain.
    """

    domain = metric.domain
    ordered = tuple(str(uid) for uid in frame_uids)
    if not authority_reason.strip():
        raise TrainingDataInputError("Prescribed selection authority reason must be non-empty.")
    if len(ordered) != len(set(ordered)):
        raise TrainingDataInputError("Prescribed selection prefix contains duplicate frames.")
    required = int(policy.target_sizes[-1])
    if len(ordered) != required:
        raise TrainingDataInputError(
            "Prescribed selection prefix must contain exactly the largest requested target size."
        )
    domain_frames = set(domain.frame_uids)
    unknown = tuple(uid for uid in ordered if uid not in domain_frames)
    if unknown:
        raise TrainingDataInputError(
            "Prescribed selection prefix contains frames outside the DATA7 domain: "
            + ", ".join(unknown[:4])
        )
    order = tuple(
        SelectionMasterEntry(
            rank=index,
            frame_uid=uid,
            primary_reason=authority_reason,
            reason_codes=(authority_reason,),
        )
        for index, uid in enumerate(ordered)
    )
    levels = tuple(
        SelectionLadderLevel(size, ordered[:size]) for size in policy.target_sizes
    )
    return TrainingSelectionPlan(
        domain=domain,
        metric_digest=metric.content_digest,
        data4_bundle_digest=data4_bundle.content_digest,
        data6_bundle_digest=data6_bundle.content_digest,
        policy=policy,
        mandatory_anchor_count=0,
        master_order=order,
        ladder_levels=levels,
    )


@dataclass(frozen=True, slots=True)
class SelectionCoverageLevel:
    target_size: int
    represented_condition_count: int
    represented_environment_classes: tuple[str, ...]
    protected_event_fraction: float
    candidate_to_selected_distance_quantiles: tuple[tuple[str, float], ...]
    maximum_covering_radius: float
    selected_neighbor_distance_quantiles: tuple[tuple[str, float], ...]
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.target_size <= 0 or self.represented_condition_count <= 0: raise TrainingDataInputError("Coverage level counts are invalid.")
        for name in ("protected_event_fraction", "maximum_covering_radius"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0: raise TrainingDataInputError("Coverage metrics must be finite and nonnegative.")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "represented_environment_classes", tuple(sorted(set(str(v) for v in self.represented_environment_classes))))
        object.__setattr__(self, "candidate_to_selected_distance_quantiles", tuple((str(k), float(v)) for k, v in self.candidate_to_selected_distance_quantiles))
        object.__setattr__(self, "selected_neighbor_distance_quantiles", tuple((str(k), float(v)) for k, v in self.selected_neighbor_distance_quantiles))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": SELECTION_COVERAGE_LEVEL_SCHEMA, "target_size": self.target_size,
            "represented_condition_count": self.represented_condition_count,
            "represented_environment_classes": list(self.represented_environment_classes),
            "protected_event_fraction": self.protected_event_fraction,
            "candidate_to_selected_distance_quantiles": dict(self.candidate_to_selected_distance_quantiles),
            "maximum_covering_radius": self.maximum_covering_radius,
            "selected_neighbor_distance_quantiles": dict(self.selected_neighbor_distance_quantiles),
        }
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SelectionCoverageLevel":
        if payload.get("schema") != SELECTION_COVERAGE_LEVEL_SCHEMA:
            raise TrainingDataSerializationError("Unsupported selection-coverage-level schema.")
        result = cls(
            target_size=int(payload["target_size"]),
            represented_condition_count=int(payload["represented_condition_count"]),
            represented_environment_classes=tuple(str(v) for v in payload.get("represented_environment_classes", ())),
            protected_event_fraction=float(payload["protected_event_fraction"]),
            candidate_to_selected_distance_quantiles=tuple((str(k), float(v)) for k, v in payload["candidate_to_selected_distance_quantiles"].items()),
            maximum_covering_radius=float(payload["maximum_covering_radius"]),
            selected_neighbor_distance_quantiles=tuple((str(k), float(v)) for k, v in payload["selected_neighbor_distance_quantiles"].items()),
        )
        expected = result.to_dict()["content_digest"]
        if payload.get("content_digest") not in (None, expected):
            raise TrainingDataSerializationError("Selection-coverage-level digest mismatch.")
        return result



@dataclass(frozen=True, slots=True)
class SelectionCoverageReport:
    selection_plan_digest: str
    metric_digest: str
    levels: tuple[SelectionCoverageLevel, ...]
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "selection_plan_digest", validate_digest(self.selection_plan_digest, name="selection_plan_digest"))
        object.__setattr__(self, "metric_digest", validate_digest(self.metric_digest, name="metric_digest"))
        levels = tuple(self.levels)
        if not levels: raise TrainingDataInputError("Coverage report requires levels.")
        object.__setattr__(self, "levels", levels)

    def _payload(self) -> dict[str, Any]:
        return {"schema": SELECTION_COVERAGE_REPORT_SCHEMA, "selection_plan_digest": self.selection_plan_digest, "metric_digest": self.metric_digest, "levels": [item.to_dict() for item in self.levels]}
    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached
    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SelectionCoverageReport":
        if payload.get("schema") != SELECTION_COVERAGE_REPORT_SCHEMA: raise TrainingDataSerializationError("Unsupported selection-coverage-report schema.")
        result = cls(selection_plan_digest=str(payload["selection_plan_digest"]), metric_digest=str(payload["metric_digest"]), levels=tuple(SelectionCoverageLevel.from_dict(item) for item in payload["levels"]))
        if payload.get("content_digest") not in (None, result.content_digest): raise TrainingDataSerializationError("Selection-coverage-report digest mismatch.")
        return result


def _quantiles(values: Sequence[float] | np.ndarray) -> tuple[tuple[str, float], ...]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        return (("q50", 0.0), ("q90", 0.0), ("q95", 0.0))
    quantiles = np.quantile(array, (0.50, 0.90, 0.95))
    return tuple(
        (name, float(value))
        for name, value in zip(("q50", "q90", "q95"), quantiles, strict=True)
    )


def _selected_neighbor_distances(X: np.ndarray) -> np.ndarray:
    if X.shape[0] <= 1:
        return np.empty((0,), dtype=np.float64)
    squared = (
        np.einsum("ij,ij->i", X, X)[:, None]
        + np.einsum("ij,ij->i", X, X)[None, :]
        - 2.0 * (X @ X.T)
    )
    np.maximum(squared, 0.0, out=squared)
    np.fill_diagonal(squared, np.inf)
    return np.sqrt(np.min(squared, axis=1))


def _pairwise_squared_distances(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """Return a numerically clipped squared-distance block.

    This helper keeps the coverage implementation columnar and lets the
    selected-neighbor matrix be extended once per newly added ladder block.
    The historical implementation rebuilt the complete ``K x K`` matrix from
    scratch at every ladder level, giving ``O(sum(K_level**2 * d))`` work.
    """

    left = np.asarray(left, dtype=np.float64)
    right = np.asarray(right, dtype=np.float64)
    squared = (
        np.einsum("ij,ij->i", left, left)[:, None]
        + np.einsum("ij,ij->i", right, right)[None, :]
        - 2.0 * (left @ right.T)
    )
    np.maximum(squared, 0.0, out=squared)
    return squared


def _extend_selected_neighbor_matrix(
    selected_matrix: np.ndarray,
    squared_distances: np.ndarray,
    previous: int,
    current: int,
) -> None:
    """Populate only the newly exposed rows/columns of a selected matrix.

    Every selected pair is evaluated exactly once over the full ladder.  The
    total work is therefore ``O(K_max**2 * d)`` rather than repeating a dense
    pair calculation independently for each requested ladder size.
    """

    if current <= previous:
        return
    new = selected_matrix[previous:current]
    within = _pairwise_squared_distances(new, new)
    np.fill_diagonal(within, np.inf)
    squared_distances[previous:current, previous:current] = within
    if previous:
        cross = _pairwise_squared_distances(selected_matrix[:previous], new)
        squared_distances[:previous, previous:current] = cross
        squared_distances[previous:current, :previous] = cross.T


def _extend_selected_neighbor_minima(
    selected_matrix: np.ndarray,
    selected_neighbor_min_squared: np.ndarray,
    previous: int,
    current: int,
    *,
    memory_budget_bytes: int = 256 * 1024 * 1024,
) -> None:
    """Extend exact nearest-other-selected state without retaining ``K x K``.

    All previous-new and new-new pairs are evaluated.  Only each selected
    point's nearest squared distance is persistent, reducing DATA7 ladder state
    from ``O(K^2)`` to ``O(K)`` while bounded temporary blocks cap peak memory.
    """

    values = np.asarray(selected_matrix, dtype=np.float64)
    minima = np.asarray(selected_neighbor_min_squared, dtype=np.float64)
    previous = int(previous)
    current = int(current)
    if values.ndim != 2 or minima.shape != (values.shape[0],):
        raise TrainingDataInputError("Selected-neighbor persistent state is misaligned.")
    if previous < 0 or current < previous or current > values.shape[0]:
        raise TrainingDataInputError("Selected-neighbor ladder bounds are invalid.")
    if current <= previous:
        return
    budget = max(8, int(memory_budget_bytes))
    new = values[previous:current]
    new_count = len(new)

    if new_count > 1:
        rows_per_block = max(1, min(new_count, budget // max(8, 8 * new_count)))
        for local_first in range(0, new_count, rows_per_block):
            local_last = min(new_count, local_first + rows_per_block)
            within = _pairwise_squared_distances(new[local_first:local_last], new)
            local_rows = np.arange(local_last - local_first, dtype=np.int64)
            within[local_rows, local_first + local_rows] = np.inf
            np.minimum(
                minima[previous + local_first : previous + local_last],
                np.min(within, axis=1),
                out=minima[previous + local_first : previous + local_last],
            )

    if previous:
        rows_per_block = max(1, min(previous, budget // max(8, 8 * new_count)))
        new_minimum = minima[previous:current]
        for first in range(0, previous, rows_per_block):
            last = min(previous, first + rows_per_block)
            cross = _pairwise_squared_distances(values[first:last], new)
            np.minimum(minima[first:last], np.min(cross, axis=1), out=minima[first:last])
            np.minimum(new_minimum, np.min(cross, axis=0), out=new_minimum)


def build_selection_coverage_report(
    data4_bundle: Any,
    data5_bundle: Any,
    data6_bundle: Any,
    metric: FittedFeatureMetric,
    plan: TrainingSelectionPlan,
) -> SelectionCoverageReport:
    candidate_uids = tuple(plan.domain.frame_uids)
    feature_table = metric.frame_feature_table
    candidate_positions = np.fromiter(
        (feature_table.index_for_uid(uid) for uid in candidate_uids),
        dtype=np.int64,
        count=len(candidate_uids),
    )
    candidate_matrix = feature_table.values[candidate_positions]
    candidate_index_by_uid = {
        uid: index for index, uid in enumerate(candidate_uids)
    }
    units = tuple(
        data5_bundle.unit_catalog.unit(unit_id)
        for unit_id in plan.domain.unit_ids
    )
    unit_by_frame = {uid: unit for unit in units for uid in unit.frame_uids}
    protected = set(data4_bundle.events.protected_frame_uids) & set(candidate_uids)
    profile_catalogs = tuple(getattr(data6_bundle, "profile_selection_features", ()))
    if not profile_catalogs and getattr(data6_bundle, "lta_selection_features", None) is not None:
        from .profile_extensions import wrap_lta_selection_features
        profile_catalogs = (wrap_lta_selection_features(
            data6_bundle.lta_selection_features, data4_bundle_digest=data6_bundle.data4_bundle_digest
        ),)

    selected_order = tuple(item.frame_uid for item in plan.master_order)
    labels_by_frame: dict[str, set[str]] = {}
    for extension in profile_catalogs:
        # Coverage consumes only the bounded selected ladder.  Query the
        # provider adapter per selected frame so compact providers can recover
        # labels from aggregate evidence without scanning or retaining every
        # atomic environment in the candidate corpus.
        for uid in selected_order:
            labels = extension.environment_class_labels({uid})
            if labels:
                labels_by_frame.setdefault(uid, set()).update(labels)

    selected_positions = np.fromiter(
        (candidate_index_by_uid[uid] for uid in selected_order),
        dtype=np.int64,
        count=len(selected_order),
    )
    selected_matrix = candidate_matrix[selected_positions]
    candidate_min_squared = np.full(len(candidate_uids), np.inf, dtype=np.float64)
    selected_neighbor_min_squared = np.full(len(selected_order), np.inf, dtype=np.float64)
    previous = 0
    chosen: set[str] = set()
    represented_conditions: set[str] = set()
    represented_classes: set[str] = set()
    protected_chosen_count = 0
    levels: list[SelectionCoverageLevel] = []
    for ladder in plan.ladder_levels:
        current = ladder.target_size
        new_uids = selected_order[previous:current]
        _update_min_squared_distances(
            candidate_matrix,
            selected_matrix[previous:current],
            candidate_min_squared,
        )
        _extend_selected_neighbor_minima(
            selected_matrix,
            selected_neighbor_min_squared,
            previous,
            current,
        )
        for uid in new_uids:
            chosen.add(uid)
            represented_conditions.add(
                unit_by_frame[uid].condition.condition_id
            )
            represented_classes.update(labels_by_frame.get(uid, ()))
            if uid in protected:
                protected_chosen_count += 1
        previous = current
        candidate_distances = np.sqrt(candidate_min_squared)
        neighbor = (
            np.empty((0,), dtype=np.float64)
            if current <= 1
            else np.sqrt(selected_neighbor_min_squared[:current])
        )
        levels.append(SelectionCoverageLevel(
            target_size=current,
            represented_condition_count=len(represented_conditions),
            represented_environment_classes=tuple(sorted(represented_classes)),
            protected_event_fraction=(
                1.0
                if not protected
                else protected_chosen_count / len(protected)
            ),
            candidate_to_selected_distance_quantiles=_quantiles(candidate_distances),
            maximum_covering_radius=float(np.max(candidate_distances)),
            selected_neighbor_distance_quantiles=_quantiles(neighbor),
        ))
    return SelectionCoverageReport(
        selection_plan_digest=plan.content_digest,
        metric_digest=metric.content_digest,
        levels=tuple(levels),
    )
