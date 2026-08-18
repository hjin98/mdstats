from __future__ import annotations

from dataclasses import replace
import json
from fractions import Fraction
from pathlib import Path

import pytest

from mdstats.analysis.framework_topology import FrameworkTopology
from mdstats.analysis.lta_natural_tiling import (
    LtaNaturalTilingGate,
    LtaNaturalTilingGateStatus,
    LtaNaturalTilingInputError,
    LtaNaturalTilingResourceError,
    LtaNaturalTilingResources,
    LtaTileSignature,
    certify_lta_natural_tiling,
)


@pytest.fixture(scope="module")
def lta_topology() -> FrameworkTopology:
    payload = json.loads(
        (Path(__file__).parent / "data" / "na_lta_framework_topology.json").read_text()
    )
    return FrameworkTopology.from_dict(payload)


@pytest.fixture(scope="module")
def lta_gate(lta_topology: FrameworkTopology) -> LtaNaturalTilingGate:
    return certify_lta_natural_tiling(lta_topology)


def test_lta_gate_certifies_expected_natural_tiling(lta_gate: LtaNaturalTilingGate) -> None:
    assert lta_gate.status is LtaNaturalTilingGateStatus.CERTIFIED
    assert lta_gate.certified
    assert lta_gate.selected_faces_stable
    assert lta_gate.tiling_stable
    assert lta_gate.expected_lta_match
    expected = (("4^6", 6), ("4^6.6^8", 2), ("4^12.6^8.8^6", 2))
    for observation in lta_gate.observations:
        assert tuple(
            (item.signature.symbol, item.count)
            for item in observation.tile_multiplicities
        ) == expected
        assert observation.reduced_multiplicity_ratio == (3, 1, 1)
        assert observation.cell_counts == (48, 96, 58, 10)
        assert observation.symmetry_order == 96
        assert observation.symmetry_preserved


def test_lta_bound_rebuilds_are_stable_but_k12_adds_nonfaces(
    lta_gate: LtaNaturalTilingGate,
) -> None:
    at_8, at_10, at_12 = lta_gate.observations
    assert at_8.ring_counts == ((4, 36), (6, 40), (8, 6))
    assert at_10.ring_counts == at_8.ring_counts
    assert at_12.ring_counts == ((4, 36), (6, 40), (8, 6), (12, 32))
    assert at_8.selected_face_counts == at_10.selected_face_counts == at_12.selected_face_counts
    assert at_12.selected_face_counts == ((4, 36), (6, 16), (8, 6))
    assert not at_8.excluded_strong_nonplanar_key_digests
    assert not at_10.excluded_strong_nonplanar_key_digests
    assert len(at_12.excluded_strong_nonplanar_key_digests) == 32
    assert len({item.complex_scientific_key for item in lta_gate.observations}) == 1


def test_lta_convex_partition_closes_exactly(lta_gate: LtaNaturalTilingGate) -> None:
    expected_volumes = tuple(
        sorted(
            (Fraction(1, 256),) * 6
            + (Fraction(61, 768),) * 2
            + (Fraction(157, 384),) * 2
        )
    )
    for observation in lta_gate.observations:
        assert observation.partition_total_fractional_volume == 1
        assert tuple(sorted(observation.tile_fractional_volumes)) == expected_volumes
        assert observation.partition_pair_candidate_count == 122
        assert observation.partition_axis_test_count == 564


def test_lta_full_group_is_certified_from_exact_generators(
    lta_gate: LtaNaturalTilingGate,
) -> None:
    for observation in lta_gate.observations:
        assert observation.symmetry_preserved
        assert observation.symmetry_composition_check_count == 3800


def test_lta_tile_signature_is_canonical() -> None:
    signature = LtaTileSignature(((4, 12), (6, 8), (8, 6)))
    assert signature.symbol == "4^12.6^8.8^6"
    assert LtaTileSignature.from_dict(signature.to_dict()) == signature
    with pytest.raises(LtaNaturalTilingInputError):
        LtaTileSignature(((6, 8), (4, 12)))


def test_lta_gate_requires_ground_bounds(lta_topology: FrameworkTopology) -> None:
    with pytest.raises(LtaNaturalTilingInputError, match="exactly"):
        certify_lta_natural_tiling(lta_topology, bounds=(8, 10))


def test_lta_resource_preflight_is_transactional(lta_topology: FrameworkTopology) -> None:
    with pytest.raises(LtaNaturalTilingResourceError, match="max_bounds"):
        certify_lta_natural_tiling(
            lta_topology,
            resources=LtaNaturalTilingResources(max_bounds=2),
        )


def test_lta_gate_digest_rejects_tampering(lta_gate: LtaNaturalTilingGate) -> None:
    with pytest.raises(LtaNaturalTilingInputError, match="digest"):
        replace(lta_gate, digest="0" * 64)


