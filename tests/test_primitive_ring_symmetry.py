from __future__ import annotations

import json

import pytest

from mdstats.analysis import (
    PrimitiveRingSymmetryIndex,
    PrimitiveRingSymmetrySerializationError,
    RingPlacement,
    build_periodic_net_symmetry,
    build_primitive_ring_symmetry_index,
)
from tests.test_net_symmetry import build_index, triangle_fixture


def test_core_symmetry_and_ring_action_have_separate_persistent_ownership() -> None:
    topology, view, rotation, reflection = triangle_fixture()
    ring_index = build_index(topology)
    symmetry = build_periodic_net_symmetry(view, (rotation, reflection))
    ring_symmetry = build_primitive_ring_symmetry_index(
        view, symmetry, ring_index
    )

    assert "ring_keys" not in symmetry.to_dict()
    assert ring_symmetry.periodic_net_symmetry_digest == symmetry.digest
    assert ring_symmetry.primitive_ring_catalog_digest == ring_index.catalog_digest
    assert ring_symmetry.action_table[0][0].target_ring_position == 0

    payload = json.loads(json.dumps(ring_symmetry.to_dict()))
    restored = PrimitiveRingSymmetryIndex.from_dict(
        payload,
        view=view,
        symmetry=symmetry,
        ring_index=ring_index,
    )
    assert restored == ring_symmetry


def test_ring_symmetry_maps_translated_placements_and_rejects_wrong_group() -> None:
    topology, view, rotation, reflection = triangle_fixture()
    ring_index = build_index(topology)
    symmetry = build_periodic_net_symmetry(view, (rotation, reflection))
    ring_symmetry = build_primitive_ring_symmetry_index(
        view, symmetry, ring_index
    )
    placement = RingPlacement(
        view.source_graph_digest,
        ring_symmetry.ring_keys[0],
        (3, -2, 1),
    )
    mapped = ring_symmetry.map_placement(symmetry, 0, placement)
    assert mapped == placement

    identity_only = build_periodic_net_symmetry(view, ())
    with pytest.raises(Exception, match="does not own"):
        ring_symmetry.map_placement(identity_only, 0, placement)

    payload = ring_symmetry.to_dict()
    with pytest.raises(PrimitiveRingSymmetrySerializationError, match="another symmetry"):
        PrimitiveRingSymmetryIndex.from_dict(
            payload,
            view=view,
            symmetry=identity_only,
            ring_index=ring_index,
        )
