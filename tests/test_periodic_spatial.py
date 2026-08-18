from __future__ import annotations

from fractions import Fraction

import pytest

from mdstats.analysis._periodic_spatial import (
    PeriodicAabbSupport,
    PeriodicImageCandidate,
    PeriodicSpatialMethod,
    PeriodicSpatialResourceError,
    PeriodicSpatialResources,
    build_periodic_overlap_candidates,
)


def _supports() -> tuple[PeriodicAabbSupport, ...]:
    return (
        PeriodicAabbSupport.from_points(
            0,
            ((Fraction(1, 10), Fraction(1, 10), 0), (Fraction(9, 10), Fraction(2, 10), 0)),
        ),
        PeriodicAabbSupport.from_points(
            1,
            ((Fraction(1, 2), Fraction(0), 0), (Fraction(3, 5), Fraction(4, 10), 0)),
        ),
        PeriodicAabbSupport.from_points(
            2,
            ((Fraction(11, 10), Fraction(1, 10), 0), (Fraction(12, 10), Fraction(2, 10), 0)),
        ),
    )


def test_direct_and_linked_cell_return_identical_periodic_candidates() -> None:
    direct = build_periodic_overlap_candidates(
        _supports(), source_digest="a" * 64, method=PeriodicSpatialMethod.DIRECT
    )
    linked = build_periodic_overlap_candidates(
        _supports(), source_digest="a" * 64, method=PeriodicSpatialMethod.LINKED_CELL
    )

    assert direct.candidates == linked.candidates
    assert direct.translation_stencil == linked.translation_stencil
    assert linked.grid_subdivisions is not None
    assert PeriodicImageCandidate(0, 1, (0, 0, 0)) in direct.candidates
    assert PeriodicImageCandidate(0, 2, (-1, 0, 0)) in direct.candidates


def test_self_images_are_preserved_and_sign_canonicalized() -> None:
    support = PeriodicAabbSupport(0, (Fraction(0), 0, 0), (Fraction(1), 0, 0))
    result = build_periodic_overlap_candidates(
        (support,), source_digest="b" * 64, method=PeriodicSpatialMethod.DIRECT
    )
    assert result.candidates == (PeriodicImageCandidate(0, 0, (1, 0, 0)),)
    assert PeriodicImageCandidate(0, 0, (-1, 0, 0)) == PeriodicImageCandidate(
        0, 0, (1, 0, 0)
    )


def test_inflated_supports_cover_distance_style_queries() -> None:
    supports = (
        PeriodicAabbSupport.from_points(0, ((0, 0, 0),), inflation=(Fraction(1, 5),) * 3),
        PeriodicAabbSupport.from_points(1, ((Fraction(13, 10), 0, 0),), inflation=(Fraction(1, 5),) * 3),
    )
    result = build_periodic_overlap_candidates(
        supports, source_digest="c" * 64, method=PeriodicSpatialMethod.DIRECT
    )
    assert PeriodicImageCandidate(0, 1, (-1, 0, 0)) in result.candidates


def test_resource_limits_fail_before_unbounded_image_work() -> None:
    supports = (
        PeriodicAabbSupport(0, (-5, -5, -5), (5, 5, 5)),
        PeriodicAabbSupport(1, (0, 0, 0), (1, 1, 1)),
    )
    with pytest.raises(PeriodicSpatialResourceError, match="translation stencil"):
        build_periodic_overlap_candidates(
            supports,
            source_digest="d" * 64,
            resources=PeriodicSpatialResources(max_translation_images=10),
        )
