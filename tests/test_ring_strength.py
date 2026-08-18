from __future__ import annotations

import json
from pathlib import Path

import pytest

from mdstats.analysis import (
    AtomicEdgeKey,
    EdgeIncidencePlacementDomain,
    FrameworkTopology,
    PrimitiveRingOptions,
    RingPlacement,
    RingStrengthCatalog,
    RingStrengthDomain,
    RingStrengthInputError,
    RingStrengthResources,
    RingStrengthResult,
    RingStrengthStatus,
    build_primitive_ring_index,
    build_ring_strength_catalog,
    build_ring_strength_workspace,
    classify_ring_strength,
    enumerate_primitive_rings,
    ring_placement_support,
)
from tests.test_primitive_ring_cancellation import (
    ZERO,
    direct_topology,
    options,
    rp,
    weak_primitive_fixture,
)


def test_weak_fixture_is_certified_by_depth_one_incidence_domain() -> None:
    _, index, rings4, ring6 = weak_primitive_fixture()
    target = rp(index, ring6.key, ZERO)
    domain = RingStrengthDomain(
        target_ring_key=ring6.key,
        max_component_size=5,
        placement_domain=EdgeIncidencePlacementDomain(1),
    )

    result = classify_ring_strength(index, target, domain)

    assert result.status is RingStrengthStatus.WEAK_CERTIFIED
    assert result.witness is not None
    assert result.witness.component_placements == tuple(
        sorted(rp(index, ring.key, ZERO) for ring in rings4)
    )
    workspace = build_ring_strength_workspace(index, target, domain)
    assert len(workspace.candidate_placements) == 3
    assert result.candidate_set_digest == workspace.candidate_set_digest
    assert result.diagnostics.achieved_incidence_depth == 1
    assert result.diagnostics.truncation_reason is None


def test_simple_square_is_strong_in_the_declared_domain() -> None:
    topology = direct_topology(
        4,
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3),
            AtomicEdgeKey(0, 3),
        ),
    )
    catalog = enumerate_primitive_rings(topology, options=options())
    index = build_primitive_ring_index(catalog)
    ring = catalog.rings[0]
    domain = RingStrengthDomain(
        ring.key,
        max_component_size=3,
        placement_domain=EdgeIncidencePlacementDomain(2),
    )

    result = classify_ring_strength(
        index,
        rp(index, ring.key, ZERO),
        domain,
    )

    assert ring.size == 4
    assert result.status is RingStrengthStatus.STRONG_IN_DOMAIN
    workspace = build_ring_strength_workspace(
        index, rp(index, ring.key, ZERO), domain
    )
    assert workspace.candidate_placements == ()
    assert result.witness is None
    # The incidence component closed early, so the full requested finite domain
    # is nevertheless exhausted and certified.
    assert result.diagnostics.achieved_incidence_depth == 2


def test_common_translation_preserves_strength_and_witness() -> None:
    _, index, _, ring6 = weak_primitive_fixture()
    domain = RingStrengthDomain(
        ring6.key,
        max_component_size=5,
        placement_domain=EdgeIncidencePlacementDomain(1),
    )
    translation = (4, -3, 2)
    zero = classify_ring_strength(index, rp(index, ring6.key, ZERO), domain)
    moved = classify_ring_strength(index, rp(index, ring6.key, translation), domain)

    assert zero.status is moved.status is RingStrengthStatus.WEAK_CERTIFIED
    assert zero.witness is not None and moved.witness is not None
    assert tuple(
        placement.image_shift for placement in moved.witness.component_placements
    ) == tuple(
        tuple(a + b for a, b in zip(placement.image_shift, translation, strict=True))
        for placement in zero.witness.component_placements
    )
    moved_target = ring_placement_support(index, moved.target_placement)
    zero_target = ring_placement_support(index, zero.target_placement)
    assert {
        (edge.edge_key, edge.anchor_shift) for edge in moved_target.edge_instances
    } == {
        (
            edge.edge_key,
            tuple(a + b for a, b in zip(edge.anchor_shift, translation, strict=True)),
        )
        for edge in zero_target.edge_instances
    }


def test_lower_open_or_truncated_primitive_source_is_unresolved() -> None:
    topology = direct_topology(
        7,
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3),
            AtomicEdgeKey(3, 4),
            AtomicEdgeKey(4, 5),
            AtomicEdgeKey(0, 5),
            AtomicEdgeKey(0, 6),
            AtomicEdgeKey(2, 6),
            AtomicEdgeKey(4, 6),
        ),
    )
    catalog = enumerate_primitive_rings(
        topology,
        options=PrimitiveRingOptions(min_ring_size=4, max_ring_size=8),
    )
    index = build_primitive_ring_index(catalog)
    ring6 = next(ring for ring in catalog.rings if ring.size == 6)
    domain = RingStrengthDomain(
        ring6.key,
        max_component_size=5,
        placement_domain=EdgeIncidencePlacementDomain(1),
    )

    result = classify_ring_strength(index, rp(index, ring6.key, ZERO), domain)

    assert result.status is RingStrengthStatus.UNRESOLVED_SOURCE_INCOMPLETE
    assert result.diagnostics.source_complete is False
    assert "lower-closed" in (result.diagnostics.source_issue or "")
    workspace = build_ring_strength_workspace(
        index, rp(index, ring6.key, ZERO), domain
    )
    assert workspace.candidate_placements == ()


def test_resource_cutoff_is_transactional_unresolved_status() -> None:
    _, index, _, ring6 = weak_primitive_fixture()
    domain = RingStrengthDomain(
        ring6.key,
        max_component_size=5,
        placement_domain=EdgeIncidencePlacementDomain(1),
    )
    resources = RingStrengthResources(
        max_candidate_placements=1,
        max_search_nodes=100,
        max_support_terms=100,
    )

    result = classify_ring_strength(
        index,
        rp(index, ring6.key, ZERO),
        domain,
        resources=resources,
    )

    assert result.status is RingStrengthStatus.UNRESOLVED_TRUNCATED
    assert result.witness is None
    assert result.diagnostics.truncation_reason == "max_candidate_placements exceeded"
    workspace = build_ring_strength_workspace(
        index,
        rp(index, ring6.key, ZERO),
        domain,
        resources=resources,
    )
    assert len(workspace.candidate_placements) == 1
    assert result.candidate_set_digest == workspace.candidate_set_digest


def test_domain_and_target_constraints_are_enforced() -> None:
    _, index, rings4, ring6 = weak_primitive_fixture()
    with pytest.raises(RingStrengthInputError, match="strictly smaller"):
        classify_ring_strength(
            index,
            rp(index, ring6.key, ZERO),
            RingStrengthDomain(
                ring6.key,
                max_component_size=6,
                placement_domain=EdgeIncidencePlacementDomain(1),
            ),
        )

    with pytest.raises(RingStrengthInputError, match="must match"):
        classify_ring_strength(
            index,
            rp(index, ring6.key, ZERO),
            RingStrengthDomain(
                rings4[0].key,
                max_component_size=3,
                placement_domain=EdgeIncidencePlacementDomain(1),
            ),
        )


def test_result_and_catalog_serialization_are_source_validated() -> None:
    _, index, _, ring6 = weak_primitive_fixture()
    domain = RingStrengthDomain(
        ring6.key,
        max_component_size=5,
        placement_domain=EdgeIncidencePlacementDomain(2),
    )
    result = classify_ring_strength(index, rp(index, ring6.key, ZERO), domain)
    restored = RingStrengthResult.from_dict(result.to_dict(), index=index)
    assert restored == result

    catalog = build_ring_strength_catalog(index, (domain,))
    restored_catalog = RingStrengthCatalog.from_dict(catalog.to_dict(), index=index)
    assert restored_catalog == catalog

    other_topology = direct_topology(
        3,
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(0, 2)),
    )
    other_catalog = enumerate_primitive_rings(other_topology, options=options())
    other_index = build_primitive_ring_index(other_catalog)
    with pytest.raises(Exception, match="another"):
        RingStrengthResult.from_dict(result.to_dict(), index=other_index)


def test_na_lta_depth_one_strength_ground_gate() -> None:
    payload = json.loads(
        (Path(__file__).parent / "data" / "na_lta_framework_topology.json").read_text()
    )
    topology = FrameworkTopology.from_dict(payload)
    catalog = enumerate_primitive_rings(
        topology,
        options=PrimitiveRingOptions(max_ring_size=8),
    )
    index = build_primitive_ring_index(catalog)
    domains = tuple(
        RingStrengthDomain(
            ring.key,
            max_component_size=ring.size - 1,
            placement_domain=EdgeIncidencePlacementDomain(1),
        )
        for ring in catalog.rings
    )

    strength = build_ring_strength_catalog(index, domains)
    counts: dict[tuple[int, RingStrengthStatus], int] = {}
    for ring, result in zip(catalog.rings, strength.results, strict=True):
        counts[(ring.size, result.status)] = counts.get(
            (ring.size, result.status), 0
        ) + 1

    assert counts == {
        (4, RingStrengthStatus.STRONG_IN_DOMAIN): 36,
        (6, RingStrengthStatus.WEAK_CERTIFIED): 24,
        (6, RingStrengthStatus.STRONG_IN_DOMAIN): 16,
        (8, RingStrengthStatus.STRONG_IN_DOMAIN): 6,
    }
    assert sum(len(result.witness.component_placements) for result in strength.results if result.witness) == 72


def _recompute_payload_digest(payload: dict) -> None:
    import hashlib

    canonical = dict(payload)
    canonical.pop("digest", None)
    payload["digest"] = hashlib.sha256(
        json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def test_persistent_strength_result_excludes_workspace_and_reverifies_witness() -> None:
    _, index, _, ring6 = weak_primitive_fixture()
    domain = RingStrengthDomain(
        ring6.key,
        max_component_size=5,
        placement_domain=EdgeIncidencePlacementDomain(1),
    )
    result = classify_ring_strength(index, rp(index, ring6.key, ZERO), domain)
    payload = json.loads(json.dumps(result.to_dict()))

    assert "candidate_placements" not in payload
    workspace = build_ring_strength_workspace(
        index, rp(index, ring6.key, ZERO), domain
    )
    assert workspace.candidate_placements
    assert workspace.candidate_set_digest == result.candidate_set_digest

    payload["witness"]["component_placements"][0]["image_shift"] = [9, 0, 0]
    _recompute_payload_digest(payload)
    with pytest.raises(Exception, match="witness fails"):
        RingStrengthResult.from_dict(payload, index=index)


def test_gf2_memory_guard_returns_unresolved_status() -> None:
    _, index, _, ring6 = weak_primitive_fixture()
    domain = RingStrengthDomain(
        ring6.key,
        max_component_size=5,
        placement_domain=EdgeIncidencePlacementDomain(1),
    )
    resources = RingStrengthResources(
        max_candidate_placements=100,
        max_search_nodes=100,
        max_support_terms=100,
        max_matrix_bits=1,
        max_provenance_bits=1,
    )
    result = classify_ring_strength(
        index,
        rp(index, ring6.key, ZERO),
        domain,
        resources=resources,
    )
    assert result.status is RingStrengthStatus.UNRESOLVED_TRUNCATED
    assert "max_matrix_bits" in (result.diagnostics.truncation_reason or "")
