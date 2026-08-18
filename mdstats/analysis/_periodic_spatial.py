"""Private periodic broad phase for continuous lifted AABB supports.

The linked-cell decomposition adapts the classical neighbor-search idea of
Quentrec and Brot (1973) to bounded extended objects.  Unlike an atomic minimum-
image list, every candidate retains an explicit relative lattice image.

This module is query-agnostic: it returns conservative periodic AABB-overlap
candidates and never assigns scientific meaning such as intersection, linking,
penetration, or tile overlap.

Reference
---------
B. Quentrec and C. Brot, J. Comput. Phys. 13, 430-432 (1973),
doi:10.1016/0021-9991(73)90046-6.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import itertools
import json
from numbers import Integral
from typing import Any, Iterable, Mapping, Sequence, TypeAlias

from ._periodic_graph import LatticeShift, coerce_lattice_shift

RationalVector3: TypeAlias = tuple[Fraction, Fraction, Fraction]

_PERIODIC_SPATIAL_SCHEMA = "mdstats.periodic-spatial-candidates.v1"
_PERIODIC_SPATIAL_DIGEST = "sha256-canonical-json-v1"


class PeriodicSpatialError(ValueError):
    """Base exception for periodic extended-object candidate generation."""


class PeriodicSpatialInputError(PeriodicSpatialError):
    """Raised when supports or resource declarations are malformed."""


class PeriodicSpatialResourceError(PeriodicSpatialError):
    """Raised before a declared broad-phase resource bound is exceeded."""


class PeriodicSpatialMethod(str, Enum):
    """Periodic support candidate-generation methods."""

    AUTO = "auto"
    DIRECT = "direct"
    LINKED_CELL = "linked-cell"


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) <= 0:
        raise PeriodicSpatialInputError(f"{name} must be a positive integer.")
    return int(value)


def _fraction_payload(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _floor(value: Fraction) -> int:
    return value.numerator // value.denominator


def _ceil(value: Fraction) -> int:
    negated = -value
    return -(negated.numerator // negated.denominator)


def _negate_shift(shift: LatticeShift) -> LatticeShift:
    return (-shift[0], -shift[1], -shift[2])


def _canonical_self_shift(shift: LatticeShift) -> LatticeShift:
    for value in shift:
        if value < 0:
            return _negate_shift(shift)
        if value > 0:
            return shift
    return shift


@dataclass(frozen=True, slots=True)
class PeriodicAabbSupport:
    """One bounded continuous lifted support in fractional coordinates."""

    object_id: int
    lower: RationalVector3
    upper: RationalVector3

    def __post_init__(self) -> None:
        if isinstance(self.object_id, bool) or not isinstance(self.object_id, Integral):
            raise PeriodicSpatialInputError("object_id must be a nonnegative integer.")
        object_id = int(self.object_id)
        if object_id < 0:
            raise PeriodicSpatialInputError("object_id must be a nonnegative integer.")
        lower = tuple(Fraction(value) for value in self.lower)
        upper = tuple(Fraction(value) for value in self.upper)
        if len(lower) != 3 or len(upper) != 3:
            raise PeriodicSpatialInputError("AABB bounds must contain three components.")
        if any(lo > hi for lo, hi in zip(lower, upper, strict=True)):
            raise PeriodicSpatialInputError("AABB lower bounds must not exceed upper bounds.")
        object.__setattr__(self, "object_id", object_id)
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)

    @classmethod
    def from_points(
        cls,
        object_id: int,
        points: Iterable[Sequence[Any]],
        *,
        inflation: Sequence[Any] = (0, 0, 0),
    ) -> "PeriodicAabbSupport":
        point_values = [tuple(Fraction(value) for value in point) for point in points]
        if not point_values or any(len(point) != 3 for point in point_values):
            raise PeriodicSpatialInputError(
                "points must contain at least one three-component point."
            )
        margin = tuple(Fraction(value) for value in inflation)
        if len(margin) != 3 or any(value < 0 for value in margin):
            raise PeriodicSpatialInputError(
                "inflation must contain three nonnegative values."
            )
        lower = tuple(
            min(point[axis] for point in point_values) - margin[axis]
            for axis in range(3)
        )
        upper = tuple(
            max(point[axis] for point in point_values) + margin[axis]
            for axis in range(3)
        )
        return cls(object_id=object_id, lower=lower, upper=upper)

    def translated(self, shift: LatticeShift) -> "PeriodicAabbSupport":
        image = coerce_lattice_shift(shift, name="shift")
        return PeriodicAabbSupport(
            self.object_id,
            tuple(self.lower[axis] + image[axis] for axis in range(3)),
            tuple(self.upper[axis] + image[axis] for axis in range(3)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "lower": [_fraction_payload(value) for value in self.lower],
            "upper": [_fraction_payload(value) for value in self.upper],
        }


@dataclass(frozen=True, slots=True, order=True)
class PeriodicImageCandidate:
    """Canonical undirected pair of objects with an explicit relative image."""

    object_i: int
    object_j: int
    image_shift: LatticeShift

    def __post_init__(self) -> None:
        if any(
            isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0
            for value in (self.object_i, self.object_j)
        ):
            raise PeriodicSpatialInputError("Candidate object IDs must be nonnegative integers.")
        i = int(self.object_i)
        j = int(self.object_j)
        try:
            shift = coerce_lattice_shift(self.image_shift, name="image_shift")
        except ValueError as exc:
            raise PeriodicSpatialInputError(str(exc)) from exc
        if i > j:
            i, j = j, i
            shift = _negate_shift(shift)
        if i == j:
            if shift == (0, 0, 0):
                raise PeriodicSpatialInputError(
                    "The zero-image self pair is not a periodic object candidate."
                )
            shift = _canonical_self_shift(shift)
        object.__setattr__(self, "object_i", i)
        object.__setattr__(self, "object_j", j)
        object.__setattr__(self, "image_shift", shift)

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_i": self.object_i,
            "object_j": self.object_j,
            "image_shift": list(self.image_shift),
        }


@dataclass(frozen=True, slots=True)
class PeriodicSpatialResources:
    """Transactional limits for extended-object broad-phase construction."""

    max_objects: int = 16384
    max_translation_images: int = 4096
    max_image_placements: int = 2_000_000
    max_candidate_checks: int = 20_000_000
    max_candidates: int = 2_000_000
    max_bin_insertions: int = 5_000_000
    max_grid_subdivisions: int = 32
    direct_candidate_check_limit: int = 250_000

    def __post_init__(self) -> None:
        for name in (
            "max_objects",
            "max_translation_images",
            "max_image_placements",
            "max_candidate_checks",
            "max_candidates",
            "max_bin_insertions",
            "max_grid_subdivisions",
            "direct_candidate_check_limit",
        ):
            object.__setattr__(self, name, _positive_int(getattr(self, name), name=name))


@dataclass(frozen=True, slots=True, eq=False)
class PeriodicSpatialCandidateSet:
    """Deterministic conservative candidate set for one support collection."""

    source_digest: str
    supports_digest: str
    method: PeriodicSpatialMethod
    translation_stencil: tuple[LatticeShift, ...]
    candidates: tuple[PeriodicImageCandidate, ...]
    grid_subdivisions: int | None
    image_placement_count: int
    bin_insertion_count: int
    candidate_check_count: int
    canonical_schema_version: str = _PERIODIC_SPATIAL_SCHEMA
    digest_algorithm: str = _PERIODIC_SPATIAL_DIGEST
    digest: str = ""

    def __post_init__(self) -> None:
        if any(not isinstance(value, str) or len(value) != 64 for value in (self.source_digest, self.supports_digest)):
            raise PeriodicSpatialInputError("Spatial source digests must be SHA-256 values.")
        method = PeriodicSpatialMethod(self.method)
        stencil = tuple(sorted({coerce_lattice_shift(item, name="translation_stencil") for item in self.translation_stencil}))
        candidates = tuple(sorted(set(self.candidates)))
        if any(not isinstance(item, PeriodicImageCandidate) for item in candidates):
            raise PeriodicSpatialInputError("candidates must be PeriodicImageCandidate records.")
        grid = self.grid_subdivisions
        if grid is not None:
            grid = _positive_int(grid, name="grid_subdivisions")
        for name in ("image_placement_count", "bin_insertion_count", "candidate_check_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
                raise PeriodicSpatialInputError(f"{name} must be a nonnegative integer.")
            object.__setattr__(self, name, int(value))
        if self.canonical_schema_version != _PERIODIC_SPATIAL_SCHEMA or self.digest_algorithm != _PERIODIC_SPATIAL_DIGEST:
            raise PeriodicSpatialInputError("Unsupported periodic spatial candidate schema.")
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "translation_stencil", stencil)
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "grid_subdivisions", grid)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise PeriodicSpatialInputError("Stored periodic spatial digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PeriodicSpatialCandidateSet) and self.digest == other.digest

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "source_digest": self.source_digest,
            "supports_digest": self.supports_digest,
            "method": self.method.value,
            "translation_stencil": [list(item) for item in self.translation_stencil],
            "candidates": [item.to_dict() for item in self.candidates],
            "grid_subdivisions": self.grid_subdivisions,
            "image_placement_count": self.image_placement_count,
            "bin_insertion_count": self.bin_insertion_count,
            "candidate_check_count": self.candidate_check_count,
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)


def _supports_digest(supports: Sequence[PeriodicAabbSupport]) -> str:
    return _digest({"supports": [support.to_dict() for support in supports]})


def _validate_supports(
    supports: Sequence[PeriodicAabbSupport], resources: PeriodicSpatialResources
) -> tuple[PeriodicAabbSupport, ...]:
    values = tuple(supports)
    if not values or any(not isinstance(item, PeriodicAabbSupport) for item in values):
        raise PeriodicSpatialInputError("supports must contain PeriodicAabbSupport records.")
    if len(values) > resources.max_objects:
        raise PeriodicSpatialResourceError("Support count exceeded max_objects.")
    ids = tuple(item.object_id for item in values)
    if ids != tuple(range(len(values))):
        raise PeriodicSpatialInputError(
            "Support object IDs must be the dense ordered range 0..N-1."
        )
    return values


def _global_translation_stencil(
    supports: Sequence[PeriodicAabbSupport], resources: PeriodicSpatialResources
) -> tuple[LatticeShift, ...]:
    global_lower = tuple(min(item.lower[axis] for item in supports) for axis in range(3))
    global_upper = tuple(max(item.upper[axis] for item in supports) for axis in range(3))
    ranges = []
    for axis in range(3):
        lower = _ceil(global_lower[axis] - global_upper[axis])
        upper = _floor(global_upper[axis] - global_lower[axis])
        ranges.append(range(lower, upper + 1))
    stencil = tuple(itertools.product(*ranges))
    if len(stencil) > resources.max_translation_images:
        raise PeriodicSpatialResourceError(
            "Complete translation stencil exceeded max_translation_images."
        )
    return tuple(coerce_lattice_shift(item, name="translation_stencil") for item in stencil)


def _overlap(left: PeriodicAabbSupport, right: PeriodicAabbSupport, shift: LatticeShift) -> bool:
    return all(
        left.lower[axis] <= right.upper[axis] + shift[axis]
        and right.lower[axis] + shift[axis] <= left.upper[axis]
        for axis in range(3)
    )


def _direct_candidates(
    supports: Sequence[PeriodicAabbSupport],
    stencil: Sequence[LatticeShift],
    resources: PeriodicSpatialResources,
) -> tuple[tuple[PeriodicImageCandidate, ...], int]:
    checks = 0
    candidates: set[PeriodicImageCandidate] = set()
    for i, left in enumerate(supports):
        for j in range(i, len(supports)):
            right = supports[j]
            for shift in stencil:
                if i == j and shift == (0, 0, 0):
                    continue
                checks += 1
                if checks > resources.max_candidate_checks:
                    raise PeriodicSpatialResourceError(
                        "Direct broad phase exceeded max_candidate_checks."
                    )
                if _overlap(left, right, shift):
                    candidates.add(PeriodicImageCandidate(i, j, shift))
                    if len(candidates) > resources.max_candidates:
                        raise PeriodicSpatialResourceError(
                            "Periodic candidate count exceeded max_candidates."
                        )
    return tuple(sorted(candidates)), checks


def _bins_touched(support: PeriodicAabbSupport, subdivisions: int) -> tuple[tuple[int, int, int], ...]:
    ranges = []
    for axis in range(3):
        lower = _floor(support.lower[axis] * subdivisions)
        upper = _floor(support.upper[axis] * subdivisions)
        ranges.append(range(lower, upper + 1))
    return tuple(itertools.product(*ranges))


def _linked_candidates_for_grid(
    supports: Sequence[PeriodicAabbSupport],
    stencil: Sequence[LatticeShift],
    subdivisions: int,
    resources: PeriodicSpatialResources,
) -> tuple[tuple[PeriodicImageCandidate, ...], int, int]:
    left_bins: dict[tuple[int, int, int], list[int]] = {}
    right_bins: dict[tuple[int, int, int], list[tuple[int, LatticeShift]]] = {}
    insertions = 0
    for support in supports:
        bins = _bins_touched(support, subdivisions)
        insertions += len(bins)
        if insertions > resources.max_bin_insertions:
            raise PeriodicSpatialResourceError(
                "Linked-cell broad phase exceeded max_bin_insertions."
            )
        for key in bins:
            left_bins.setdefault(key, []).append(support.object_id)
    for support in supports:
        for shift in stencil:
            translated = support.translated(shift)
            bins = _bins_touched(translated, subdivisions)
            insertions += len(bins)
            if insertions > resources.max_bin_insertions:
                raise PeriodicSpatialResourceError(
                    "Linked-cell broad phase exceeded max_bin_insertions."
                )
            for key in bins:
                right_bins.setdefault(key, []).append((support.object_id, shift))

    raw: set[PeriodicImageCandidate] = set()
    checks = 0
    for key in sorted(set(left_bins).intersection(right_bins)):
        for i in left_bins[key]:
            for j, shift in right_bins[key]:
                if i == j and shift == (0, 0, 0):
                    continue
                checks += 1
                if checks > resources.max_candidate_checks:
                    raise PeriodicSpatialResourceError(
                        "Linked-cell broad phase exceeded max_candidate_checks."
                    )
                try:
                    raw.add(PeriodicImageCandidate(i, j, shift))
                except PeriodicSpatialInputError:  # zero self guarded above
                    continue
    candidates = tuple(
        candidate
        for candidate in sorted(raw)
        if _overlap(
            supports[candidate.object_i],
            supports[candidate.object_j],
            candidate.image_shift,
        )
    )
    if len(candidates) > resources.max_candidates:
        raise PeriodicSpatialResourceError(
            "Periodic candidate count exceeded max_candidates."
        )
    return candidates, insertions, checks


def build_periodic_overlap_candidates(
    supports: Sequence[PeriodicAabbSupport],
    *,
    source_digest: str,
    method: PeriodicSpatialMethod = PeriodicSpatialMethod.AUTO,
    resources: PeriodicSpatialResources | None = None,
) -> PeriodicSpatialCandidateSet:
    """Build a complete conservative periodic AABB-overlap candidate set."""

    if not isinstance(source_digest, str) or len(source_digest) != 64:
        raise PeriodicSpatialInputError("source_digest must be a SHA-256 digest.")
    active = resources or PeriodicSpatialResources()
    if not isinstance(active, PeriodicSpatialResources):
        raise PeriodicSpatialInputError("resources must be PeriodicSpatialResources.")
    values = _validate_supports(supports, active)
    selected = PeriodicSpatialMethod(method)
    stencil = _global_translation_stencil(values, active)
    image_placements = len(values) * len(stencil)
    if image_placements > active.max_image_placements:
        raise PeriodicSpatialResourceError(
            "Periodic image placement count exceeded max_image_placements."
        )
    direct_estimate = (len(values) * (len(values) + 1) // 2) * len(stencil)
    if selected is PeriodicSpatialMethod.AUTO:
        selected = (
            PeriodicSpatialMethod.DIRECT
            if direct_estimate <= active.direct_candidate_check_limit
            else PeriodicSpatialMethod.LINKED_CELL
        )

    if selected is PeriodicSpatialMethod.DIRECT:
        candidates, checks = _direct_candidates(values, stencil, active)
        grid = None
        insertions = 0
    else:
        grid_options: list[int] = []
        value = 1
        while value <= active.max_grid_subdivisions:
            grid_options.append(value)
            value *= 2
        best: tuple[int, int, int, int, tuple[PeriodicImageCandidate, ...]] | None = None
        last_error: PeriodicSpatialResourceError | None = None
        for subdivisions in grid_options:
            try:
                candidate_values, insertion_count, check_count = _linked_candidates_for_grid(
                    values, stencil, subdivisions, active
                )
            except PeriodicSpatialResourceError as exc:
                last_error = exc
                continue
            score = insertion_count + check_count
            record = (
                score,
                check_count,
                insertion_count,
                subdivisions,
                candidate_values,
            )
            if best is None or record[:4] < best[:4]:
                best = record
        if best is None:
            raise last_error or PeriodicSpatialResourceError(
                "No linked-cell grid satisfies the declared resources."
            )
        _, checks, insertions, grid, candidates = best

    return PeriodicSpatialCandidateSet(
        source_digest=source_digest,
        supports_digest=_supports_digest(values),
        method=selected,
        translation_stencil=tuple(stencil),
        candidates=tuple(candidates),
        grid_subdivisions=grid,
        image_placement_count=image_placements,
        bin_insertion_count=insertions,
        candidate_check_count=checks,
    )
