from __future__ import annotations

import json
from fractions import Fraction

import pytest

from mdstats.analysis import (
    PeriodicBarycentricPlacement,
    PeriodicBarycentricResourceError,
    PeriodicBarycentricResources,
    build_periodic_barycentric_placement,
)
from tests.test_net_symmetry_discovery import collided_view, diamond_view


def test_exact_barycentric_placement_is_reusable_and_serializable() -> None:
    view = diamond_view()
    placement = build_periodic_barycentric_placement(view, anchor_atom_index=0)

    assert placement.coordinates == (
        (Fraction(0), Fraction(0), Fraction(0)),
        (Fraction(-1, 4), Fraction(-1, 4), Fraction(-1, 4)),
    )
    assert placement.collision_free
    assert placement.periodic_net_view_digest == view.digest

    payload = json.loads(json.dumps(placement.to_dict()))
    restored = PeriodicBarycentricPlacement.from_dict(payload, view=view)
    assert restored == placement


def test_barycentric_collision_is_recorded_without_being_silently_accepted() -> None:
    placement = build_periodic_barycentric_placement(collided_view())
    assert not placement.collision_free
    assert placement.collision_atom_pairs


def test_barycentric_resource_limits_are_transactional() -> None:
    with pytest.raises(PeriodicBarycentricResourceError, match="max_vertices"):
        build_periodic_barycentric_placement(
            diamond_view(),
            resources=PeriodicBarycentricResources(max_vertices=1),
        )
