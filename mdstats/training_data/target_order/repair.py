"""REPAIR2: configured-shell repair of the one master order (D2 section 9).

Restored from ``target_multi_view_repair_v2`` (carrier ``3937881e``) and
rebound to one exact ``P_train`` domain, canonical obligations and the current
configured ladder.  At shell ``[N_{i-1}, N_i)`` only zero-unique, hard-safe
active-shell members may be removed; the exact pre-removal replacement
frontier is built once per unchanged state and removal-dependent terms are
evaluated over that frontier in exact batches.  Accepted swaps mutate the
forward state by exact deselect/select, inherit the removed rank, and displace
a future occurrence of the replacement inside the configured master order.
Lower configured prefixes are immutable.

Frontier primitives (hard gain, first canonical bottleneck family, coverage
gains) are the MVSEL2 primitives from :mod:`selector`; there is no second
definition.

Execution.  Every candidate-indexed quantity is evaluated by
:class:`_StateBatch` over the existing MVIDX forward CSR arrays.  Full-row FP64
sums go through the already-qualified pairwise row reduction
(``native.score_family_candidate_batch`` at width > 1, the identical NumPy row
reduction at width 1), and masked reductions keep the canonical compacted
association by delegating exactly those rows that own a masked witness to the
scalar owner below.  Removal-dependent terms are expressed as a per-witness
patch of the state's base term vector, so ``|shortlist|`` proposals need one
batched sweep each instead of one Python task per candidate.  The batch object
is created per unchanged repair state; an accepted swap discards it, which is
how every state-dependent array is invalidated.  The scalar functions
``removal_metrics``, ``_representative_after_removal`` and
``_diversity_after_removal`` remain the D2 formula oracle used by the
equivalence tests.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from .._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from ..progress_timing import format_progress_time
from ..resources import StageResourceScope
from .native import mvsel2_execution_backend, score_family_candidate_batch
from .selector import (
    TargetMultiViewForwardState,
    TargetMultiViewSelectionPlan,
    bottleneck_family_index,
    build_forward_state,
    deselect_candidate,
    family_coverage_gain,
    hard_gain,
    native_row,
    prefix_digest,
    score_candidate,
    select_candidate,
    total_coverage_gain,
    unsatisfied_obligation_ids,
)

REPAIR2_VERSION = "mdstats.target-order.repair2.configured-shell.v2"
REPAIR2_POLICY_SCHEMA = "mdstats.target-multi-view-repair-policy.v3"
REPAIR2_SWAP_SCHEMA = "mdstats.target-multi-view-repair-swap.v2"
REPAIR2_RUNG_SCHEMA = "mdstats.target-multi-view-repair-rung.v3"
REPAIR2_PLAN_SCHEMA = "mdstats.target-multi-view-repair-plan.v3"

Objective = tuple[int, float, float, float, int]


@dataclass(frozen=True, slots=True)
class TargetMultiViewRepairPolicy:
    """Frozen REPAIR2 policy (D2 sections 9.1-9.4)."""

    unique_coverage_tolerance: float = 1.0e-14
    gain_tie_tolerance: float = 1.0e-14
    max_passes_per_shell: int = 2
    max_swaps_per_shell: int = 32
    removal_shortlist_limit: int = 64
    authority_version: str = REPAIR2_VERSION

    def __post_init__(self) -> None:
        if (
            float(self.unique_coverage_tolerance) != 1.0e-14
            or float(self.gain_tie_tolerance) != 1.0e-14
            or int(self.max_passes_per_shell) != 2
            or int(self.max_swaps_per_shell) != 32
            or int(self.removal_shortlist_limit) != 64
        ):
            raise TrainingDataInputError("REPAIR2 freezes its tolerances and per-shell limits.")
        if self.authority_version != REPAIR2_VERSION:
            raise TrainingDataInputError("Unsupported REPAIR2 policy version.")

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": REPAIR2_POLICY_SCHEMA,
            "unique_coverage_tolerance": self.unique_coverage_tolerance,
            "gain_tie_tolerance": self.gain_tie_tolerance,
            "max_passes_per_shell": self.max_passes_per_shell,
            "max_swaps_per_shell": self.max_swaps_per_shell,
            "removal_shortlist_limit": self.removal_shortlist_limit,
            "active_shell_only": True,
            "replacement_rank_inheritance": True,
            "strict_no_coverage_regression": True,
            "authority_version": self.authority_version,
        }
        return {**payload, "policy_digest": digest(payload)}

    @property
    def policy_digest(self) -> str:
        return str(self.to_dict()["policy_digest"])

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewRepairPolicy":
        if payload.get("schema") != REPAIR2_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported REPAIR2 policy schema.")
        result = cls(authority_version=str(payload["authority_version"]))
        if payload.get("policy_digest") != result.policy_digest:
            raise TrainingDataSerializationError("REPAIR2 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewRepairSwap:
    target_size: int
    pass_index: int
    swap_index: int
    rank: int
    removed_frame_uid: str
    replacement_frame_uid: str
    removed_unique_coverage: float
    removed_representative_loss: float
    objective_before: Objective
    objective_after: Objective
    bottleneck_family_id: str
    displaced_future_rank: int | None = None

    def __post_init__(self) -> None:
        if not 0 <= int(self.rank) < int(self.target_size) or int(self.pass_index) < 0 or int(self.swap_index) < 0:
            raise TrainingDataInputError("REPAIR2 swap rank/index is invalid.")
        validate_digest(self.removed_frame_uid, name="removed_frame_uid")
        validate_digest(self.replacement_frame_uid, name="replacement_frame_uid")
        if self.removed_frame_uid == self.replacement_frame_uid:
            raise TrainingDataInputError("REPAIR2 swap must exchange distinct frames.")
        if int(self.objective_after[0]) > int(self.objective_before[0]):
            raise TrainingDataInputError("REPAIR2 swap increased the hard deficit.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": REPAIR2_SWAP_SCHEMA,
            "target_size": int(self.target_size),
            "pass_index": int(self.pass_index),
            "swap_index": int(self.swap_index),
            "rank": int(self.rank),
            "removed_frame_uid": self.removed_frame_uid,
            "replacement_frame_uid": self.replacement_frame_uid,
            "removed_unique_coverage": float(self.removed_unique_coverage),
            "removed_representative_loss": float(self.removed_representative_loss),
            "objective_before": _objective_payload(self.objective_before),
            "objective_after": _objective_payload(self.objective_after),
            "bottleneck_family_id": self.bottleneck_family_id,
            "displaced_future_rank": self.displaced_future_rank,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewRepairSwap":
        if payload.get("schema") != REPAIR2_SWAP_SCHEMA:
            raise TrainingDataSerializationError("Unsupported REPAIR2 swap schema.")
        return cls(
            target_size=int(payload["target_size"]),
            pass_index=int(payload["pass_index"]),
            swap_index=int(payload["swap_index"]),
            rank=int(payload["rank"]),
            removed_frame_uid=str(payload["removed_frame_uid"]),
            replacement_frame_uid=str(payload["replacement_frame_uid"]),
            removed_unique_coverage=float(payload["removed_unique_coverage"]),
            removed_representative_loss=float(payload["removed_representative_loss"]),
            objective_before=_objective_from_payload(payload["objective_before"]),
            objective_after=_objective_from_payload(payload["objective_after"]),
            bottleneck_family_id=str(payload["bottleneck_family_id"]),
            displaced_future_rank=None if payload.get("displaced_future_rank") is None else int(payload["displaced_future_rank"]),
        )


def _objective_payload(value: Objective) -> list[Any]:
    return [int(value[0]), float(value[1]), float(value[2]), float(value[3]), int(value[4])]


def _objective_from_payload(value: Sequence[Any]) -> Objective:
    return (int(value[0]), float(value[1]), float(value[2]), float(value[3]), int(value[4]))


@dataclass(frozen=True, slots=True)
class TargetMultiViewRepairRung:
    target_size: int
    active_shell_start: int
    frame_uids_digest: str
    family_coverage: tuple[tuple[str, float], ...]
    unsatisfied_obligation_ids: tuple[str, ...]
    swaps: tuple[TargetMultiViewRepairSwap, ...]
    zero_unique_shell_fraction: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": REPAIR2_RUNG_SCHEMA,
            "target_size": int(self.target_size),
            "active_shell_start": int(self.active_shell_start),
            "frame_uids_digest": self.frame_uids_digest,
            "family_coverage": [[k, float(v)] for k, v in self.family_coverage],
            "unsatisfied_obligation_ids": list(self.unsatisfied_obligation_ids),
            "swaps": [item.to_dict() for item in self.swaps],
            "zero_unique_shell_fraction": float(self.zero_unique_shell_fraction),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewRepairRung":
        if payload.get("schema") != REPAIR2_RUNG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported REPAIR2 rung schema.")
        return cls(
            target_size=int(payload["target_size"]),
            active_shell_start=int(payload["active_shell_start"]),
            frame_uids_digest=str(payload["frame_uids_digest"]),
            family_coverage=tuple((str(v[0]), float(v[1])) for v in payload["family_coverage"]),
            unsatisfied_obligation_ids=tuple(str(v) for v in payload["unsatisfied_obligation_ids"]),
            swaps=tuple(TargetMultiViewRepairSwap.from_dict(v) for v in payload["swaps"]),
            zero_unique_shell_fraction=float(payload["zero_unique_shell_fraction"]),
        )


@dataclass(frozen=True, slots=True)
class TargetMultiViewRepairPlan:
    """Repair trace and the repaired configured prefix through ``N_max``."""

    selection_plan_digest: str
    policy: TargetMultiViewRepairPolicy
    repaired_prefix: tuple[str, ...]
    rungs: tuple[TargetMultiViewRepairRung, ...]

    @property
    def total_swaps(self) -> int:
        return sum(len(item.swaps) for item in self.rungs)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": REPAIR2_PLAN_SCHEMA,
            "selection_plan_digest": self.selection_plan_digest,
            "policy": self.policy.to_dict(),
            "repaired_prefix": list(self.repaired_prefix),
            "rungs": [item.to_dict() for item in self.rungs],
        }
        return {**payload, "content_digest": digest(payload)}

    @property
    def content_digest(self) -> str:
        return str(self.to_dict()["content_digest"])

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewRepairPlan":
        if payload.get("schema") != REPAIR2_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported REPAIR2 plan schema.")
        result = cls(
            selection_plan_digest=str(payload["selection_plan_digest"]),
            policy=TargetMultiViewRepairPolicy.from_dict(payload["policy"]),
            repaired_prefix=tuple(str(v) for v in payload["repaired_prefix"]),
            rungs=tuple(TargetMultiViewRepairRung.from_dict(v) for v in payload["rungs"]),
        )
        if payload.get("content_digest") != result.content_digest:
            raise TrainingDataSerializationError("REPAIR2 plan digest mismatch.")
        return result


# --- exact objective and removal metrics -------------------------------------


def hard_deficit(forward: Any, state: TargetMultiViewForwardState) -> int:
    return int(
        sum(
            max(0, int(item.minimum_selected_frames) - int(state.obligation_counts[index]))
            for index, item in enumerate(forward.obligations)
        )
    )


def representative_utility(state: TargetMultiViewForwardState) -> float:
    """``U_rep = sum_m sum_w omega_m(w) H_{n_m(w)}`` recomputed from multiplicities."""

    total = 0.0
    for family_state in state.family_states:
        multiplicity = np.asarray(family_state.multiplicity, dtype=np.int64)
        if multiplicity.size == 0:
            continue
        maximum = int(np.max(multiplicity))
        harmonic = np.zeros(maximum + 1, dtype=np.float64)
        if maximum:
            harmonic[1:] = np.cumsum(1.0 / np.arange(1, maximum + 1, dtype=np.float64), dtype=np.float64)
        total += float(np.sum(family_state.weights * harmonic[multiplicity], dtype=np.float64))
    return total


def objective(forward: Any, state: TargetMultiViewForwardState, utility: float | None = None) -> Objective:
    coverage = [float(item.coverage_mass) for item in state.family_states]
    counts = state.correlation_unit_counts.astype(np.int64)
    return (
        hard_deficit(forward, state),
        min(coverage),
        float(np.sum(coverage, dtype=np.float64)),
        representative_utility(state) if utility is None else float(utility),
        -int(np.dot(counts, counts)),
    )


def strictly_better(before: Objective, after: Objective, tolerance: float) -> bool:
    if after[0] != before[0]:
        return after[0] < before[0]
    for old, new in zip(before[1:4], after[1:4], strict=True):
        if new > old + tolerance:
            return True
        if new < old - tolerance:
            return False
    return after[4] > before[4]


def removal_metrics(candidate: int, forward: Any, state: TargetMultiViewForwardState) -> tuple[float, float]:
    """Unique covered mass and exact representative loss of one selected member."""

    unique = 0.0
    loss = 0.0
    for family, family_state in zip(forward.families, state.family_states, strict=True):
        witnesses = native_row(family.candidate_witness_indices(candidate))
        if witnesses.size == 0:
            continue
        multiplicity = family_state.multiplicity[witnesses].astype(np.float64, copy=False)
        if np.any(multiplicity < 1.0):
            raise TrainingDataInputError("REPAIR2 selected witness multiplicity underflow.")
        weights = family_state.weights[witnesses]
        unique_mask = multiplicity == 1.0
        if np.any(unique_mask):
            unique += float(np.sum(weights[unique_mask], dtype=np.float64))
        loss += float(np.sum(weights / multiplicity, dtype=np.float64))
    return unique, loss


def hard_safe(candidate: int, forward: Any, state: TargetMultiViewForwardState) -> bool:
    """Removal cannot increase the deficit of any canonical obligation."""

    for index in native_row(forward.candidate_obligation_indices(candidate)):
        if int(state.obligation_counts[int(index)]) <= int(forward.obligations[int(index)].minimum_selected_frames):
            return False
    return True


class _RemovalMarks:
    """Epoch-stamped witness membership of one hypothetical removal (no state copy)."""

    __slots__ = ("_marks", "_epoch")

    def __init__(self, forward: Any) -> None:
        self._marks = tuple(np.zeros(int(family.witness_count), dtype=np.uint32) for family in forward.families)
        self._epoch = 0

    def mark(self, forward: Any, removed: int) -> None:
        self._epoch += 1
        if self._epoch >= np.iinfo(np.uint32).max:
            for marks in self._marks:
                marks.fill(0)
            self._epoch = 1
        for marks, family in zip(self._marks, forward.families, strict=True):
            witnesses = native_row(family.candidate_witness_indices(removed))
            if witnesses.size:
                marks[witnesses] = self._epoch

    def shared(self, family_index: int, witnesses: np.ndarray) -> np.ndarray:
        return self._marks[family_index][witnesses] == self._epoch


def _representative_after_removal(candidate: int, forward: Any, state: TargetMultiViewForwardState, marks: _RemovalMarks) -> float:
    total = 0.0
    for family_index, (family, family_state) in enumerate(zip(forward.families, state.family_states, strict=True)):
        witnesses = native_row(family.candidate_witness_indices(candidate))
        if witnesses.size == 0:
            continue
        multiplicity = family_state.multiplicity[witnesses].astype(np.float64, copy=False)
        shared = marks.shared(family_index, witnesses)
        if np.any(shared) and np.any(multiplicity[shared] < 2.0):
            raise TrainingDataInputError("REPAIR2 zero-unique removal invariant failed.")
        total += float(
            np.sum(family_state.weights[witnesses] / (multiplicity - shared.astype(np.float64) + 1.0), dtype=np.float64)
        )
    return total


def _diversity_after_removal(candidate: int, forward: Any, state: TargetMultiViewForwardState, marks: _RemovalMarks) -> float:
    values: list[float] = []
    for family_index, (family, family_state) in enumerate(zip(forward.families, state.family_states, strict=True)):
        witnesses = native_row(family.candidate_witness_indices(candidate))
        if witnesses.size == 0:
            continue
        multiplicity = family_state.multiplicity[witnesses].astype(np.int64, copy=True)
        multiplicity[marks.shared(family_index, witnesses)] -= 1
        if np.any(multiplicity < 0):
            raise TrainingDataInputError("REPAIR2 diversity multiplicity underflow.")
        values.append(float(np.mean(1.0 / (1.0 + multiplicity), dtype=np.float64)))
    return 0.0 if not values else float(np.mean(values, dtype=np.float64))


# --- batched exact execution over one unchanged repair state ------------------


def _candidate_array(candidates: Any) -> np.ndarray:
    """Canonically ordered contiguous candidate vector for the row primitive."""

    return np.ascontiguousarray(candidates, dtype=np.uint32)


class _StateBatch:
    """Exact batched candidate evaluation bound to one unchanged repair state.

    Full-row FP64 reductions are bitwise equal to
    ``np.sum(terms[row], dtype=np.float64)`` in both execution paths, which is
    exactly what the native backend qualification certifies.  Masked reductions
    (uncovered coverage mass, uniquely covered mass) keep the canonical
    compacted association: the batch only proves which rows own no masked
    witness -- an exact integer indicator count -- and delegates the remaining
    rows to the scalar owner.
    """

    def __init__(self, forward: Any, state: TargetMultiViewForwardState, *, workers: int) -> None:
        self.forward = forward
        self.state = state
        self.workers = max(1, int(workers))
        self.native = self.workers > 1 and mvsel2_execution_backend(self.workers) == "native-openmp"
        self._arrays: dict[tuple[str, int], np.ndarray] = {}

    # -- per-family state arrays (built once per unchanged state) -------------

    def _family(self, index: int) -> tuple[Any, Any]:
        return self.forward.families[index], self.state.family_states[index]

    def _array(self, kind: str, index: int) -> np.ndarray:
        key = (kind, index)
        cached = self._arrays.get(key)
        if cached is not None:
            return cached
        _, family_state = self._family(index)
        weights = np.ascontiguousarray(family_state.weights, dtype=np.float64)
        if kind == "multiplicity":
            value = family_state.multiplicity.astype(np.float64)
        elif kind == "weights":
            value = weights
        else:
            multiplicity = self._array("multiplicity", index)
            if kind == "unit":
                value = np.ones_like(multiplicity)
            elif kind == "representative":
                value = np.divide(weights, multiplicity + 1.0, dtype=np.float64)
            elif kind == "diversity":
                value = np.divide(1.0, multiplicity + 1.0, dtype=np.float64)
            elif kind == "loss":
                # ``w/n`` is the exact removal-loss term.  Entries at ``n == 0``
                # are unreachable for a selected row and stay at zero so no
                # division warning or non-finite value can enter a reduction.
                value = np.zeros_like(weights)
                np.divide(weights, multiplicity, out=value, where=multiplicity > 0.0)
            elif kind == "near_unique":
                value = (multiplicity <= 1.0).astype(np.float64)
            elif kind == "uncovered":
                value = (multiplicity == 0.0).astype(np.float64)
            else:  # pragma: no cover - internal guard
                raise TrainingDataInputError(f"Unknown REPAIR2 batch array {kind!r}.")
        value = np.ascontiguousarray(value, dtype=np.float64)
        self._arrays[key] = value
        return value

    # -- row primitives -------------------------------------------------------

    def row_sums(self, index: int, terms: np.ndarray, candidates: np.ndarray) -> np.ndarray:
        """Bitwise ``np.sum(terms[row(c)], dtype=np.float64)`` per candidate row."""

        family, _ = self._family(index)
        if self.native and candidates.size:
            values, _ = score_family_candidate_batch(
                family.candidate_offsets, family.candidate_witnesses, terms, candidates, workers=self.workers
            )
            return values
        offsets = family.candidate_offsets
        witnesses = family.candidate_witnesses
        values = np.empty(candidates.size, dtype=np.float64)
        for position in range(candidates.size):
            candidate = int(candidates[position])
            start = int(offsets[candidate])
            stop = int(offsets[candidate + 1])
            values[position] = np.sum(terms[witnesses[start:stop]], dtype=np.float64)
        return values

    def row_lengths(self, index: int, candidates: np.ndarray) -> np.ndarray:
        family, _ = self._family(index)
        offsets = np.asarray(family.candidate_offsets)
        selected = candidates.astype(np.int64, copy=False)
        return (offsets[selected + 1] - offsets[selected]).astype(np.int64, copy=False)

    def _row(self, index: int, candidate: int) -> np.ndarray:
        family, _ = self._family(index)
        return native_row(family.candidate_witness_indices(int(candidate)))

    def _forbid_shared(self, index: int, forbidden: np.ndarray, candidates: np.ndarray, message: str) -> None:
        """Fail closed exactly when an evaluated row owns a forbidden witness."""

        terms = np.zeros_like(self._array("multiplicity", index))
        terms[forbidden] = 1.0
        counts = self.row_sums(index, terms, candidates)
        if counts.size and float(np.max(counts)) > 0.0:
            raise TrainingDataInputError(message)

    # -- removal metrics over selected rows ----------------------------------

    def removal_metrics_many(self, candidates: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Exact :func:`removal_metrics` for many selected candidates."""

        candidates = _candidate_array(candidates)
        unique = np.zeros(candidates.size, dtype=np.float64)
        loss = np.zeros(candidates.size, dtype=np.float64)
        for index in range(len(self.forward.families)):
            _, family_state = self._family(index)
            if family_state.weights.size == 0 or candidates.size == 0:
                continue
            nonempty = self.row_lengths(index, candidates) > 0
            if not bool(np.any(nonempty)):
                continue
            near = self.row_sums(index, self._array("near_unique", index), candidates)
            plain = nonempty & (near == 0.0)
            if bool(np.any(plain)):
                loss[plain] += self.row_sums(index, self._array("loss", index), candidates)[plain]
            multiplicity = self._array("multiplicity", index)
            weights = family_state.weights
            for position in np.flatnonzero(nonempty & (near > 0.0)):
                row = self._row(index, int(candidates[position]))
                values = multiplicity[row]
                if bool(np.any(values < 1.0)):
                    raise TrainingDataInputError("REPAIR2 selected witness multiplicity underflow.")
                mask = values == 1.0
                if bool(np.any(mask)):
                    unique[position] += float(np.sum(weights[row][mask], dtype=np.float64))
                loss[position] += float(np.sum(weights[row] / values, dtype=np.float64))
        return unique, loss

    # -- coverage gains -------------------------------------------------------

    def family_coverage_gain_many(self, candidates: np.ndarray, index: int) -> np.ndarray:
        """Exact :func:`selector.family_coverage_gain` mass for many candidates."""

        candidates = _candidate_array(candidates)
        gains = np.zeros(candidates.size, dtype=np.float64)
        _, family_state = self._family(index)
        if family_state.weights.size == 0 or candidates.size == 0:
            return gains
        uncovered = self._array("uncovered", index)
        if not bool(np.any(uncovered)):
            return gains
        counts = self.row_sums(index, uncovered, candidates)
        for position in np.flatnonzero(counts > 0.0):
            gains[position] = family_coverage_gain(int(candidates[position]), index, self.forward, self.state)[0]
        return gains

    def total_coverage_gain_many(self, candidates: np.ndarray) -> np.ndarray:
        """Exact :func:`selector.total_coverage_gain` total for many candidates."""

        candidates = _candidate_array(candidates)
        family_count = len(self.forward.families)
        matrix = np.zeros((candidates.size, family_count), dtype=np.float64)
        for index in range(family_count):
            matrix[:, index] = self.family_coverage_gain_many(candidates, index)
        totals = np.empty(candidates.size, dtype=np.float64)
        for position in range(candidates.size):
            totals[position] = np.sum(matrix[position], dtype=np.float64)
        return totals

    # -- removal-dependent frontier terms ------------------------------------

    def _after_removal_sums(
        self,
        index: int,
        kind: str,
        numerator: str,
        removed: int,
        candidates: np.ndarray,
        *,
        guard: float,
        message: str,
    ) -> np.ndarray:
        """Row sums of one term vector with the removed row's witnesses patched.

        A witness shared with ``removed`` loses one multiplicity, so its term
        denominator becomes ``n`` instead of ``n + 1`` while every other witness
        keeps the state's base term.  The divisions use the same FP64 operands
        the scalar owner divides, so the patched row sums are bitwise equal.
        """

        terms = self._array(kind, index)
        multiplicity = self._array("multiplicity", index)
        row = self._row(index, int(removed))
        if row.size == 0:
            return self.row_sums(index, terms, candidates)
        forbidden = row[multiplicity[row] < guard]
        if forbidden.size:
            self._forbid_shared(index, forbidden, candidates, message)
        denominator = multiplicity[row]
        saved = terms[row].copy()
        patched = np.zeros(row.size, dtype=np.float64)
        np.divide(self._array(numerator, index)[row], denominator, out=patched, where=denominator > 0.0)
        terms[row] = patched
        try:
            return self.row_sums(index, terms, candidates)
        finally:
            terms[row] = saved

    def representative_after_removal_many(self, candidates: np.ndarray, removed: int) -> np.ndarray:
        """Exact :func:`_representative_after_removal` for many candidates."""

        candidates = _candidate_array(candidates)
        total = np.zeros(candidates.size, dtype=np.float64)
        for index in range(len(self.forward.families)):
            _, family_state = self._family(index)
            if family_state.weights.size == 0 or candidates.size == 0:
                continue
            nonempty = self.row_lengths(index, candidates) > 0
            if not bool(np.any(nonempty)):
                continue
            values = self._after_removal_sums(
                index, "representative", "weights", int(removed), candidates,
                guard=2.0, message="REPAIR2 zero-unique removal invariant failed.",
            )
            total[nonempty] += values[nonempty]
        return total

    def diversity_after_removal_many(self, candidates: np.ndarray, removed: int) -> np.ndarray:
        """Exact :func:`_diversity_after_removal` for many candidates."""

        candidates = _candidate_array(candidates)
        family_count = len(self.forward.families)
        matrix = np.full((candidates.size, family_count), np.nan, dtype=np.float64)
        for index in range(family_count):
            _, family_state = self._family(index)
            if family_state.weights.size == 0 or candidates.size == 0:
                continue
            lengths = self.row_lengths(index, candidates)
            nonempty = lengths > 0
            if not bool(np.any(nonempty)):
                continue
            values = self._after_removal_sums(
                index, "diversity", "unit", int(removed), candidates,
                guard=1.0, message="REPAIR2 diversity multiplicity underflow.",
            )
            matrix[nonempty, index] = values[nonempty] / lengths[nonempty].astype(np.float64)
        result = np.empty(candidates.size, dtype=np.float64)
        for position in range(candidates.size):
            finite = matrix[position][np.isfinite(matrix[position])]
            result[position] = 0.0 if finite.size == 0 else float(np.mean(finite, dtype=np.float64))
        return result


def _best_relative_mask(values: np.ndarray, tolerance: float) -> np.ndarray:
    """Array form of :func:`selector.filter_best_relative`."""

    if values.size <= 1:
        return np.ones(values.size, dtype=np.bool_)
    return values >= float(np.max(values)) - float(tolerance)


# --- replacement frontier -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Frontier:
    """Pre-removal replacement frontier shared by one unchanged repair state."""

    utility_before: float
    before: Objective
    bottleneck: int
    candidates: np.ndarray


def _build_frontier(
    forward: Any,
    state: TargetMultiViewForwardState,
    selector_policy: Any,
    tolerance: float,
    batch: _StateBatch,
) -> _Frontier | None:
    available = _candidate_array(np.flatnonzero(state.available))
    if available.size == 0:
        return None
    utility = representative_utility(state)
    before = objective(forward, state, utility)
    candidates = available
    if before[0] > 0:
        gains = np.asarray([hard_gain(int(c), forward, state) for c in candidates], dtype=np.int64)
        candidates = candidates[gains == int(np.max(gains))]
    bottleneck = bottleneck_family_index(state, selector_policy)
    candidates = candidates[_best_relative_mask(batch.family_coverage_gain_many(candidates, bottleneck), tolerance)]
    candidates = candidates[_best_relative_mask(batch.total_coverage_gain_many(candidates), tolerance)]
    return _Frontier(utility, before, bottleneck, candidates)


def _proposal(
    reference: Any,
    forward: Any,
    state: TargetMultiViewForwardState,
    removal: tuple[int, int, float, float],
    frontier: _Frontier,
    batch: _StateBatch,
    tolerance: float,
) -> dict[str, Any] | None:
    rank, removed, unique, loss = removal
    removed_unit = int(forward.candidate_correlation_unit_codes[removed])
    codes = np.asarray(forward.candidate_correlation_unit_codes)[frontier.candidates.astype(np.int64)].astype(
        np.int64, copy=False
    )
    counts = np.asarray(state.correlation_unit_counts).astype(np.int64)
    hypothetical = counts[codes] - (codes == removed_unit).astype(np.int64)
    candidates = frontier.candidates[hypothetical == int(np.min(hypothetical))]
    representative = batch.representative_after_removal_many(candidates, removed)
    keep = _best_relative_mask(representative, tolerance)
    candidates, representative = candidates[keep], representative[keep]
    keep = _best_relative_mask(batch.diversity_after_removal_many(candidates, removed), tolerance)
    candidates, representative = candidates[keep], representative[keep]
    position = min(range(candidates.size), key=lambda index: reference.frame_uids[int(candidates[index])])
    replacement = int(candidates[position])
    gains, _, _ = total_coverage_gain(replacement, forward, state)
    coverage_after = [min(1.0, float(item.coverage_mass) + float(g)) for item, g in zip(state.family_states, gains, strict=True)]
    before = frontier.before
    replacement_unit = int(forward.candidate_correlation_unit_codes[replacement])
    balance = before[4]
    if replacement_unit != removed_unit:
        balance = before[4] + 2 * (
            int(state.correlation_unit_counts[removed_unit]) - int(state.correlation_unit_counts[replacement_unit]) - 1
        )
    after: Objective = (
        max(0, before[0] - hard_gain(replacement, forward, state)),
        float(min(coverage_after)),
        float(sum(coverage_after)),
        float(frontier.utility_before - loss + float(representative[position])),
        balance,
    )
    if any(new + tolerance < float(old.coverage_mass) for old, new in zip(state.family_states, coverage_after, strict=True)):
        return None
    if not strictly_better(before, after, tolerance):
        return None
    return {
        "rank": rank, "removed": removed, "replacement": replacement, "unique": unique, "loss": loss,
        "before": before, "after": after, "bottleneck": state.family_states[frontier.bottleneck].family_id,
    }


def _preferred(left: dict[str, Any] | None, right: dict[str, Any], reference: Any, tolerance: float) -> dict[str, Any]:
    if left is None or strictly_better(left["after"], right["after"], tolerance):
        return right
    if strictly_better(right["after"], left["after"], tolerance):
        return left
    key = lambda item: (item["loss"], item["rank"], reference.frame_uids[item["removed"]], reference.frame_uids[item["replacement"]])  # noqa: E731
    return left if key(left) <= key(right) else right


def _best_proposal(
    reference: Any,
    forward: Any,
    state: TargetMultiViewForwardState,
    shortlist: Sequence[tuple[int, int, float, float]],
    frontier: _Frontier,
    batch: _StateBatch,
    tolerance: float,
) -> dict[str, Any] | None:
    """Evaluate immutable proposals and reduce in canonical shortlist order.

    Each shortlist entry is one batched sweep over the shared frontier, so
    execution width lives inside the qualified row primitive and there is no
    completion order, worker count or task boundary left to perturb the
    reduction.
    """

    best: dict[str, Any] | None = None
    for removal in shortlist:
        proposal = _proposal(reference, forward, state, removal, frontier, batch, tolerance)
        if proposal is not None:
            best = _preferred(best, proposal, reference, tolerance)
    return best


# --- configured-shell repair --------------------------------------------------


def build_repair_plan(
    reference: Any,
    forward: Any,
    selection: TargetMultiViewSelectionPlan,
    *,
    policy: TargetMultiViewRepairPolicy | None = None,
    workers: int = 1,
    resource_scope: StageResourceScope | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> TargetMultiViewRepairPlan:
    """Repair every configured shell of the pure MVSEL2 master order."""

    policy = policy or TargetMultiViewRepairPolicy()
    if int(workers) < 1:
        raise TrainingDataInputError("REPAIR2 workers must be positive.")
    if selection.mvidx_content_digest != forward.mvidx_content_digest:
        raise TrainingDataInputError("REPAIR2 selection/MVIDX lineage mismatch.")
    # Execution-only: the stage resource owner caps the row-primitive width.
    width = int(workers) if resource_scope is None else min(int(workers), int(resource_scope.cpu_threads_budget))
    width = max(1, width)
    tolerance = float(policy.gain_tie_tolerance)
    candidate_by_uid = {uid: index for index, uid in enumerate(reference.frame_uids)}
    order = [candidate_by_uid[uid] for uid in selection.master_order]
    state = build_forward_state(reference, forward, validate=False)
    previous = 0
    rungs: list[TargetMultiViewRepairRung] = []
    started = time.monotonic()
    for base in selection.rungs:
        size = int(base.target_size)
        for rank in range(previous, size):
            select_candidate(order[rank], forward, state, score=score_candidate(order[rank], forward, state))
        shell = range(previous, size)
        initial_zero = 0
        measured_initial = False
        # Execution-only stage telemetry for current-envelope resource evidence.
        proposals = 0
        frontier_max = 0
        shortlist_max = 0
        # One batch object per unchanged repair state; an accepted swap drops it,
        # which is how every state-dependent array is invalidated.
        batch: _StateBatch | None = None
        shell_candidates = _candidate_array([])
        accepted: list[TargetMultiViewRepairSwap] = []
        for pass_index in range(policy.max_passes_per_shell):
            changed = False
            while len(accepted) < policy.max_swaps_per_shell:
                if batch is None:
                    batch = _StateBatch(forward, state, workers=width)
                    shell_candidates = _candidate_array([order[r] for r in shell])
                shell_unique, shell_loss = batch.removal_metrics_many(shell_candidates)
                if not measured_initial:
                    initial_zero = int(np.count_nonzero(shell_unique <= policy.unique_coverage_tolerance))
                    measured_initial = True
                removals: list[tuple[int, int, float, float]] = []
                for position, rank in enumerate(shell):
                    candidate = order[rank]
                    unique = float(shell_unique[position])
                    if unique <= policy.unique_coverage_tolerance and hard_safe(candidate, forward, state):
                        removals.append((rank, candidate, unique, float(shell_loss[position])))
                removals.sort(
                    key=lambda row: (
                        row[3],
                        -int(state.correlation_unit_counts[int(forward.candidate_correlation_unit_codes[row[1]])]),
                        reference.frame_uids[row[1]],
                    )
                )
                shortlist = removals[: policy.removal_shortlist_limit]
                shortlist_max = max(shortlist_max, len(shortlist))
                best = None
                if shortlist:
                    frontier = _build_frontier(forward, state, selection.policy, tolerance, batch)
                    if frontier is not None:
                        frontier_max = max(frontier_max, int(frontier.candidates.size))
                        proposals += len(shortlist)
                        best = _best_proposal(reference, forward, state, shortlist, frontier, batch, tolerance)
                if best is None:
                    break
                rank, removed, replacement = int(best["rank"]), int(best["removed"]), int(best["replacement"])
                displaced = next((index for index in range(size, len(order)) if order[index] == replacement), None)
                if displaced is not None:
                    order[displaced] = removed
                order[rank] = replacement
                deselect_candidate(removed, forward, state)
                select_candidate(replacement, forward, state, score=score_candidate(replacement, forward, state))
                batch = None
                accepted.append(
                    TargetMultiViewRepairSwap(
                        target_size=size,
                        pass_index=pass_index,
                        swap_index=len(accepted),
                        rank=rank,
                        removed_frame_uid=reference.frame_uids[removed],
                        replacement_frame_uid=reference.frame_uids[replacement],
                        removed_unique_coverage=float(best["unique"]),
                        removed_representative_loss=float(best["loss"]),
                        objective_before=best["before"],
                        objective_after=best["after"],
                        bottleneck_family_id=str(best["bottleneck"]),
                        displaced_future_rank=displaced,
                    )
                )
                changed = True
            if not changed:
                break
        coverage = tuple((item.family_id, min(1.0, max(0.0, item.coverage_mass))) for item in state.family_states)
        unsatisfied = unsatisfied_obligation_ids(forward, state)
        base_coverage = dict(base.family_coverage)
        if any(value + tolerance < base_coverage[family_id] for family_id, value in coverage):
            raise TrainingDataInputError("REPAIR2 same-N coverage regressed below MVSEL2.")
        if base.hard_obligations_passed and unsatisfied:
            raise TrainingDataInputError("REPAIR2 hard obligations regressed below MVSEL2.")
        rungs.append(
            TargetMultiViewRepairRung(
                target_size=size,
                active_shell_start=previous,
                frame_uids_digest=prefix_digest([reference.frame_uids[c] for c in order[:size]]),
                family_coverage=coverage,
                unsatisfied_obligation_ids=unsatisfied,
                swaps=tuple(accepted),
                zero_unique_shell_fraction=0.0 if size == previous else initial_zero / (size - previous),
            )
        )
        if progress_callback is not None:
            progress_callback(
                f"status=rung; progress={size}/{selection.configured_sizes[-1]}; "
                f"elapsed={format_progress_time(time.monotonic() - started)}; target_size={size}; "
                f"active_shell_start={previous}; swaps={len(accepted)}; zero_unique={initial_zero}; "
                f"width={width}; backend={'native-openmp' if width > 1 else 'python-numpy'}; "
                f"proposals={proposals}; frontier_max={frontier_max}; shortlist_max={shortlist_max}"
            )
        previous = size
    return TargetMultiViewRepairPlan(
        selection_plan_digest=selection.content_digest,
        policy=policy,
        repaired_prefix=tuple(reference.frame_uids[c] for c in order),
        rungs=tuple(rungs),
    )


def validate_repair_plan(plan: TargetMultiViewRepairPlan, selection: TargetMultiViewSelectionPlan) -> None:
    """Structural nesting/rank-inheritance checks against the pure selector plan."""

    if plan.selection_plan_digest != selection.content_digest:
        raise TrainingDataInputError("REPAIR2 selector lineage mismatch.")
    if tuple(item.target_size for item in plan.rungs) != selection.configured_sizes:
        raise TrainingDataInputError("REPAIR2 rungs do not match the configured ladder.")
    if len(plan.repaired_prefix) != selection.configured_sizes[-1] or len(set(plan.repaired_prefix)) != len(plan.repaired_prefix):
        raise TrainingDataInputError("REPAIR2 repaired prefix is not a unique configured prefix.")
    previous = 0
    for rung in plan.rungs:
        if rung.active_shell_start != previous:
            raise TrainingDataInputError("REPAIR2 shell boundaries are invalid.")
        if rung.frame_uids_digest != prefix_digest(plan.repaired_prefix[: rung.target_size]):
            raise TrainingDataInputError("REPAIR2 rung prefix identity mismatch.")
        previous = rung.target_size


__all__ = [
    "REPAIR2_VERSION",
    "TargetMultiViewRepairPlan",
    "TargetMultiViewRepairPolicy",
    "TargetMultiViewRepairRung",
    "TargetMultiViewRepairSwap",
    "build_repair_plan",
    "hard_deficit",
    "hard_safe",
    "objective",
    "removal_metrics",
    "representative_utility",
    "strictly_better",
    "validate_repair_plan",
]
