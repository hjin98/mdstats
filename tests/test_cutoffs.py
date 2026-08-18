"""Tests for reusable pair-cutoff objects."""

from __future__ import annotations

import pytest

from mdstats import PairCutoff, PairCutoffRegistry


def test_pair_cutoff_canonicalizes_species_order() -> None:
    cutoff = PairCutoff.manual("Si", "O", radius=2.1)
    assert cutoff.atomic_numbers == (8, 14)
    assert cutoff.symbols == ("O", "Si")
    assert cutoff.matches("O", "Si")
    assert cutoff.matches("Si", "O")


def test_registry_coerces_floats_and_rejects_conflicts() -> None:
    registry = PairCutoffRegistry.from_mapping({("Si", "O"): 2.1})
    assert registry.require("O", "Si").radius == pytest.approx(2.1)
    with pytest.raises(ValueError, match="Conflicting"):
        PairCutoffRegistry.from_mapping(
            {
                ("Si", "O"): PairCutoff.manual("Si", "O", radius=2.1),
                ("O", "Si"): PairCutoff.manual("O", "Si", radius=2.2),
            }
        )


def test_pair_cutoff_serialization_round_trip() -> None:
    original = PairCutoff.manual(
        "Na", "O", radius=3.2, source_metadata={"reason": "first shell"}
    )
    restored = PairCutoff.from_dict(original.to_dict())
    assert restored == original


def test_cutoff_registry_and_nested_metadata_are_immutable() -> None:
    cutoff = PairCutoff.manual(
        "Si", "O", radius=2.1, source_metadata={"nested": {"values": [1, 2]}}
    )
    registry = PairCutoffRegistry.from_cutoffs([cutoff])
    with pytest.raises(TypeError):
        registry.cutoffs[(8, 14)] = cutoff  # type: ignore[index]
    with pytest.raises(TypeError):
        cutoff.source_metadata["new"] = 1  # type: ignore[index]
    nested = cutoff.source_metadata["nested"]
    with pytest.raises(TypeError):
        nested["new"] = 1  # type: ignore[index]
