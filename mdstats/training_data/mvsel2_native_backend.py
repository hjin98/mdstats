"""Private exact native execution backend for MVSEL2 Phase-B family scoring.

The scientific authority remains the Python MVSEL2 selector/oracle. This module
qualifies and exposes only the hardware execution primitive used to sum existing
authenticated forward CSR rows against the reconstructible FP64 witness-term
cache.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ._common import TrainingDataInputError

try:
    from mdstats import _mvsel2_native as _native
except Exception as exc:  # optional compiled backend
    _native = None
    _IMPORT_ERROR: BaseException | None = exc
else:
    _IMPORT_ERROR = None


@dataclass(frozen=True, slots=True)
class MVSEL2NativeBackendStatus:
    available: bool
    qualified: bool
    openmp: bool
    max_threads: int
    reason: str | None = None


_QUALIFIED_STATUS: MVSEL2NativeBackendStatus | None = None


def _qualification_fixture() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    lengths = (
        1,
        2,
        7,
        8,
        9,
        15,
        16,
        31,
        63,
        127,
        128,
        129,
        255,
        256,
        257,
        511,
        512,
        513,
        1024,
        1582,
        2047,
    )
    term_count = max(lengths) + 17
    index = np.arange(term_count, dtype=np.float64)
    # Nonnegative, nonuniform values exercise low-order FP64 behavior while
    # remaining inside the representative-term domain.
    terms = (
        (index + 1.0) / (term_count + 3.0)
        + np.ldexp((index % 29.0) + 1.0, -45)
    ).astype(np.float64, copy=False)

    offsets = np.empty(len(lengths) + 1, dtype=np.uint64)
    offsets[0] = 0
    rows: list[np.ndarray] = []
    cursor = 0
    for position, length in enumerate(lengths):
        # Keep every row sorted/unique like authenticated MVIDX1 CSR while
        # varying the selected term pattern across pairwise boundaries.
        row = np.arange(length, dtype=np.uint32)
        if position % 2:
            row = (row + np.uint32(position)).astype(np.uint32, copy=False)
        rows.append(row)
        cursor += length
        offsets[position + 1] = cursor
    witnesses = np.concatenate(rows).astype(np.uint32, copy=False)
    candidates = np.arange(len(lengths), dtype=np.uint32)
    return offsets, witnesses, terms, candidates


def _expected_scores(
    offsets: np.ndarray,
    witnesses: np.ndarray,
    terms: np.ndarray,
    candidates: np.ndarray,
) -> np.ndarray:
    result = np.empty(len(candidates), dtype=np.float64)
    for position, candidate_value in enumerate(candidates):
        candidate = int(candidate_value)
        start = int(offsets[candidate])
        stop = int(offsets[candidate + 1])
        result[position] = np.sum(
            terms[witnesses[start:stop]],
            dtype=np.float64,
        )
    return result


def _bitwise_equal(left: np.ndarray, right: np.ndarray) -> bool:
    return bool(
        np.array_equal(
            np.asarray(left, dtype=np.float64).view(np.uint64),
            np.asarray(right, dtype=np.float64).view(np.uint64),
        )
    )


def qualify_mvsel2_native_backend_v2() -> MVSEL2NativeBackendStatus:
    """Qualify native row reduction against the NumPy scientific oracle once."""

    global _QUALIFIED_STATUS
    if _QUALIFIED_STATUS is not None:
        return _QUALIFIED_STATUS
    if _native is None:
        reason = (
            "native extension is unavailable"
            if _IMPORT_ERROR is None
            else f"native extension import failed: {_IMPORT_ERROR}"
        )
        _QUALIFIED_STATUS = MVSEL2NativeBackendStatus(
            available=False,
            qualified=False,
            openmp=False,
            max_threads=1,
            reason=reason,
        )
        return _QUALIFIED_STATUS

    try:
        offsets, witnesses, terms, candidates = _qualification_fixture()
        expected = _expected_scores(offsets, witnesses, terms, candidates)
        actual = np.empty_like(expected)
        edges = int(
            _native.score_family_batch(
                offsets,
                witnesses,
                terms,
                candidates,
                actual,
                1,
            )
        )
        expected_edges = sum(
            int(offsets[int(candidate) + 1] - offsets[int(candidate)])
            for candidate in candidates
        )
        if edges != expected_edges or not _bitwise_equal(actual, expected):
            raise RuntimeError(
                "serial native FP64 reduction is not bitwise identical to NumPy"
            )

        openmp = bool(_native.openmp_enabled())
        max_threads = max(1, int(_native.max_threads()))
        if openmp and max_threads >= 2:
            parallel = np.empty_like(expected)
            parallel_edges = int(
                _native.score_family_batch(
                    offsets,
                    witnesses,
                    terms,
                    candidates,
                    parallel,
                    2,
                )
            )
            if parallel_edges != expected_edges or not _bitwise_equal(
                parallel, expected
            ):
                raise RuntimeError(
                    "parallel native FP64 reduction is not bitwise identical to NumPy"
                )
    except Exception as exc:
        _QUALIFIED_STATUS = MVSEL2NativeBackendStatus(
            available=True,
            qualified=False,
            openmp=False,
            max_threads=1,
            reason=f"native backend qualification failed: {exc}",
        )
        return _QUALIFIED_STATUS

    _QUALIFIED_STATUS = MVSEL2NativeBackendStatus(
        available=True,
        qualified=True,
        openmp=openmp,
        max_threads=max_threads,
        reason=None,
    )
    return _QUALIFIED_STATUS


def phase_b_execution_backend_v2(workers: int) -> str:
    workers = int(workers)
    if workers < 1:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 worker count must be positive."
        )
    if workers == 1:
        # Preserve the proven G4b product path as the serial baseline. Native
        # serial scoring remains independently qualified and testable.
        return "python-numpy"

    status = qualify_mvsel2_native_backend_v2()
    if not status.available or not status.qualified:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 workers>1 requires the qualified native "
            f"backend; {status.reason or 'backend unavailable'}. Build the "
            "extension in place before running the parallel selector."
        )
    if not status.openmp:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 native backend was built without OpenMP; "
            "workers>1 is unavailable."
        )
    return "native-openmp"


def score_family_candidate_batch_v2(
    offsets: Any,
    witnesses: Any,
    terms: Any,
    candidates: Any,
    *,
    workers: int,
) -> tuple[np.ndarray, int]:
    """Score one family for independent candidate rows through native buffers."""

    workers = int(workers)
    status = qualify_mvsel2_native_backend_v2()
    if not status.available or not status.qualified:
        raise TrainingDataInputError(
            f"TARGET-DATA2C-MVSEL2 native backend is not qualified: {status.reason}"
        )
    if workers > 1 and not status.openmp:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 native backend has no OpenMP support."
        )

    offsets_array = np.asarray(offsets)
    witnesses_array = np.asarray(witnesses)
    terms_array = np.asarray(terms)
    candidates_array = np.ascontiguousarray(candidates, dtype=np.uint32)

    if (
        offsets_array.ndim != 1
        or offsets_array.dtype != np.dtype(np.uint64)
        or not offsets_array.flags.c_contiguous
    ):
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 native offsets must be contiguous uint64."
        )
    if (
        witnesses_array.ndim != 1
        or witnesses_array.dtype != np.dtype(np.uint32)
        or not witnesses_array.flags.c_contiguous
    ):
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 native witnesses must be contiguous uint32."
        )
    if (
        terms_array.ndim != 1
        or terms_array.dtype != np.dtype(np.float64)
        or not terms_array.flags.c_contiguous
    ):
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVSEL2 native terms must be contiguous float64."
        )

    output = np.empty(len(candidates_array), dtype=np.float64)
    try:
        edges = int(
            _native.score_family_batch(
                offsets_array,
                witnesses_array,
                terms_array,
                candidates_array,
                output,
                workers,
            )
        )
    except Exception as exc:
        raise TrainingDataInputError(
            f"TARGET-DATA2C-MVSEL2 native family scoring failed: {exc}"
        ) from exc
    return output, edges
